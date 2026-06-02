"""
foot (Go) MySQL 桥接层

从 foot 项目的 MySQL 数据库读取分析信号，转换为 C1.0 Feature Layer 可用的格式。

设计原则：
- 只读，不写入 foot 数据库
- 连接失败时优雅降级（返回空信号，不抛异常）
- 所有查询带超时保护
- 结果可缓存，避免频繁查询
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import yaml

from .foot_schema import (
    FootAnalyResult,
    FootAsiaHis,
    FootBFBattle,
    FootBFJin,
    FootBFScore,
    FootEuroHis,
    FootLeague,
    FootMatchLast,
    FootMatchSignals,
)

logger = logging.getLogger(__name__)

_DEFAULT_CFG_PATH = Path(__file__).resolve().parents[1] / "configs" / "foot_bridge_cfg.yaml"


# ── 配置加载 ──────────────────────────────────────────────────────────────────

def _load_cfg(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or _DEFAULT_CFG_PATH
    try:
        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception as exc:
        logger.warning("foot_bridge: 配置加载失败 %s: %s", cfg_path, exc)
        return {}


def _mysql_dsn(cfg: dict[str, Any]) -> str:
    """从配置构建 PyMySQL 连接参数，支持环境变量替换。

    密码解析为 fail-closed：当配置使用 ${ENV_VAR} 语法但环境变量未设置时，
    返回空密码而不是硬编码 fallback，避免凭据泄漏到源码。
    连接将因空密码而失败，由调用方优雅降级。
    """
    import os
    mysql = cfg.get("mysql", {})
    password = str(mysql.get("password", ""))
    # 支持 ${ENV_VAR} 语法（fail-closed：未设置时为空，不使用硬编码 fallback）
    if password.startswith("${") and password.endswith("}"):
        env_key = password[2:-1]
        password = os.environ.get(env_key, "")
        if not password:
            logger.warning(
                "foot_bridge: 环境变量 %s 未设置，MySQL 密码为空。"
                "请设置 %s 以启用 foot 桥接。",
                env_key,
                env_key,
            )
    return {
        "host": str(mysql.get("host", "127.0.0.1")),
        "port": int(mysql.get("port", 3306)),
        "user": str(mysql.get("user", "root")),
        "password": password,
        "database": str(mysql.get("database", "foot")),
        "charset": str(mysql.get("charset", "utf8mb4")),
        "connect_timeout": int(mysql.get("connect_timeout", 10)),
        "cursorclass": None,  # 由调用方设置
    }


# ── 连接管理 ──────────────────────────────────────────────────────────────────

class FootDBConnection:
    """轻量级 MySQL 连接包装，支持上下文管理器"""

    def __init__(self, dsn_params: dict[str, Any]) -> None:
        self._params = dict(dsn_params)
        self._conn: Any = None

    def __enter__(self) -> "FootDBConnection":
        try:
            import pymysql
            import pymysql.cursors
            params = dict(self._params)
            params["cursorclass"] = pymysql.cursors.DictCursor
            self._conn = pymysql.connect(**params)
        except ImportError:
            raise RuntimeError(
                "pymysql 未安装。请运行: pip install pymysql\n"
                "如果不需要 foot 桥接，可在 foot_bridge_cfg.yaml 中设置 bridge.enabled: false"
            )
        return self

    def __exit__(self, *_: Any) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def query(self, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
        if self._conn is None:
            return []
        with self._conn.cursor() as cursor:
            cursor.execute(sql, args)
            return list(cursor.fetchall())


# ── 简单内存缓存 ──────────────────────────────────────────────────────────────

class _SimpleCache:
    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[datetime, Any]] = {}

    def get(self, key: str) -> Any:
        if self._ttl <= 0:
            return None
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if datetime.now() - ts > timedelta(seconds=self._ttl):
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if self._ttl > 0:
            self._store[key] = (datetime.now(), value)

    def clear(self) -> None:
        self._store.clear()


# ── 核心桥接类 ────────────────────────────────────────────────────────────────

class FootBridge:
    """
    foot MySQL 桥接器。

    用法：
        bridge = FootBridge()
        signals = bridge.get_signals_for_match(
            main_team_id="曼城",
            guest_team_id="利物浦",
            match_date="2026-05-29",
        )
        features = signals.as_feature_dict
    """

    def __init__(self, cfg_path: Path | None = None) -> None:
        self._cfg = _load_cfg(cfg_path)
        bridge_cfg = self._cfg.get("bridge", {})
        self._enabled: bool = bool(bridge_cfg.get("enabled", True))
        self._analy_days: int = int(bridge_cfg.get("analy_result_days", 3))
        self._match_days: int = int(bridge_cfg.get("match_days", 2))
        ttl = int(bridge_cfg.get("cache_ttl_seconds", 300))
        self._cache = _SimpleCache(ttl_seconds=ttl)
        self._dsn = _mysql_dsn(self._cfg)
        odds_cfg = self._cfg.get("odds_companies", {})
        self._c1_refer_asia: str = str(odds_cfg.get("c1_refer_asia", "18"))
        self._default_refer_asia: str = str(odds_cfg.get("default_refer_asia", "18"))
        euro_cfg = odds_cfg.get("euro", {})
        self._euro_weide: str = str(euro_cfg.get("weide", "81"))
        self._euro_888: str = str(euro_cfg.get("sport888", "616"))
        self._euro_interwetten: str = str(euro_cfg.get("interwetten", "104"))
        asia_cfg = odds_cfg.get("asia", {})
        self._asia_multi_ids: list[str] = [
            str(v) for v in asia_cfg.values() if v
        ]

    # ── 公开接口 ──────────────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._enabled

    def ping(self) -> dict[str, Any]:
        """测试数据库连接，返回状态报告"""
        if not self._enabled:
            return {"status": "disabled", "message": "foot_bridge 已在配置中禁用"}
        try:
            with FootDBConnection(self._dsn) as db:
                rows = db.query("SELECT COUNT(*) AS cnt FROM t_match_last")
                cnt = rows[0]["cnt"] if rows else 0
            return {
                "status": "ok",
                "match_last_count": cnt,
                "host": self._dsn.get("host"),
                "database": self._dsn.get("database"),
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def get_signals_for_match(
        self,
        main_team_id: str,
        guest_team_id: str,
        match_date: str,
        match_id: Optional[str] = None,
    ) -> FootMatchSignals:
        """
        主入口：根据主客队和日期获取 foot 信号聚合体。

        优先用 match_id 精确查询，否则按队名+日期模糊匹配。
        连接失败时返回空信号（error 字段非空），不抛异常。
        """
        if not self._enabled:
            return FootMatchSignals(
                match_id=match_id or "",
                match_date=None,
                main_team_id=main_team_id,
                guest_team_id=guest_team_id,
                league_id="",
                error="foot_bridge disabled",
            )

        cache_key = f"signals:{match_id or ''}:{main_team_id}:{guest_team_id}:{match_date}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            result = self._fetch_signals(main_team_id, guest_team_id, match_date, match_id)
        except Exception as exc:
            logger.warning("foot_bridge: 获取信号失败 %s vs %s: %s", main_team_id, guest_team_id, exc)
            result = FootMatchSignals(
                match_id=match_id or "",
                match_date=None,
                main_team_id=main_team_id,
                guest_team_id=guest_team_id,
                league_id="",
                error=str(exc),
            )

        self._cache.set(cache_key, result)
        return result

    def get_today_analy_results(
        self,
        al_flags: Optional[list[str]] = None,
    ) -> list[FootAnalyResult]:
        """获取今日（及近 N 天）的分析结果列表"""
        if not self._enabled:
            return []
        cache_key = f"analy:{','.join(al_flags or [])}:{datetime.now().strftime('%Y%m%d%H')}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            results = self._fetch_analy_results(al_flags)
        except Exception as exc:
            logger.warning("foot_bridge: 获取分析结果失败: %s", exc)
            results = []
        self._cache.set(cache_key, results)
        return results

    def get_match_by_teams(
        self,
        main_team_id: str,
        guest_team_id: str,
        match_date: str,
    ) -> Optional[FootMatchLast]:
        """按队名+日期查找比赛"""
        if not self._enabled:
            return None
        try:
            with FootDBConnection(self._dsn) as db:
                return self._query_match_last(db, main_team_id, guest_team_id, match_date)
        except Exception as exc:
            logger.warning("foot_bridge: 查询比赛失败: %s", exc)
            return None

    def clear_cache(self) -> None:
        self._cache.clear()

    # ── 内部查询方法 ──────────────────────────────────────────────────────────

    def _fetch_signals(
        self,
        main_team_id: str,
        guest_team_id: str,
        match_date: str,
        match_id: Optional[str],
    ) -> FootMatchSignals:
        """从 MySQL 拉取并聚合所有信号"""
        with FootDBConnection(self._dsn) as db:
            # 1. 找到比赛记录
            match = None
            if match_id:
                match = self._query_match_by_id(db, match_id)
            if match is None:
                match = self._query_match_last(db, main_team_id, guest_team_id, match_date)
            if match is None:
                return FootMatchSignals(
                    match_id=match_id or "",
                    match_date=None,
                    main_team_id=main_team_id,
                    guest_team_id=guest_team_id,
                    league_id="",
                    error="match_not_found",
                )

            mid = match.id
            signals = FootMatchSignals(
                match_id=mid,
                match_date=match.match_date,
                main_team_id=match.main_team_id,
                guest_team_id=match.guest_team_id,
                league_id=match.league_id,
                fetched_at=datetime.now().isoformat(),
            )

            # 2. 联赛名称
            league = self._query_league(db, match.league_id)
            if league:
                signals.league_name = league.name

            # 3. 亚赔信号
            self._fill_asia_signals(db, mid, signals)

            # 4. 欧赔信号
            self._fill_euro_signals(db, mid, signals)

            # 5. 基本面信号（积分榜+对战+近期）
            self._fill_fundamental_signals(db, mid, match, signals)

            # 6. 模型结论信号
            self._fill_model_signals(db, mid, signals)

            return signals

    def _fill_asia_signals(
        self, db: FootDBConnection, match_id: str, signals: FootMatchSignals
    ) -> None:
        """填充亚赔方向信号（复现 AsiaDirectionMulti 逻辑）"""
        rows = db.query(
            "SELECT CompId, SLetBall, ELetBall, Sp3, Sp0, Ep3, Ep0 FROM t_asia_his WHERE MatchId = %s",
            (match_id,),
        )
        if not rows:
            return

        # 取参考公司的即时盘数据
        ref_row = next((r for r in rows if str(r.get("CompId", "")) == self._default_refer_asia), None)
        if ref_row:
            signals.asia_let_ball_instant = float(ref_row.get("ELetBall") or 0)
            signals.asia_let_ball_opening = float(ref_row.get("SLetBall") or 0)
            signals.asia_let_ball_move = signals.asia_let_ball_instant - signals.asia_let_ball_opening

        # 多公司方向共识
        main_count = 0
        guest_count = 0
        total = 0
        for r in rows:
            asia = FootAsiaHis(
                id="", match_id=match_id,
                comp_id=str(r.get("CompId", "")),
                s_let_ball=float(r.get("SLetBall") or 0),
                e_let_ball=float(r.get("ELetBall") or 0),
                sp3=float(r.get("Sp3") or 0),
                sp0=float(r.get("Sp0") or 0),
                ep3=float(r.get("Ep3") or 0),
                ep0=float(r.get("Ep0") or 0),
            )
            d = asia.asia_direction
            if d == 3:
                main_count += 1
            elif d == 0:
                guest_count += 1
            total += 1

        if total > 0:
            diff = main_count - guest_count
            if diff > 1:
                signals.asia_direction = 3
            elif diff < -1:
                signals.asia_direction = 0
            signals.asia_direction_consensus = abs(diff) / total

    def _fill_euro_signals(
        self, db: FootDBConnection, match_id: str, signals: FootMatchSignals
    ) -> None:
        """填充欧赔方向信号（复现 EuroDirection + A1 逻辑）"""
        rows = db.query(
            "SELECT CompId, Sp3, Sp1, Sp0, Ep3, Ep1, Ep0 FROM t_euro_his WHERE MatchId = %s AND CompId IN (%s, %s)",
            (match_id, self._euro_weide, self._euro_888),
        )
        if len(rows) < 2:
            return

        e81 = next((r for r in rows if str(r.get("CompId")) == self._euro_weide), None)
        e616 = next((r for r in rows if str(r.get("CompId")) == self._euro_888), None)
        if not e81 or not e616:
            return

        # 复现 EuroDirection 逻辑
        e81_ep3_small = float(e81.get("Ep3") or 0) <= float(e81.get("Sp3") or 0)
        e81_ep0_small = float(e81.get("Ep0") or 0) <= float(e81.get("Sp0") or 0)
        e616_ep3_small = float(e616.get("Ep3") or 0) <= float(e616.get("Sp3") or 0)
        e616_ep0_small = float(e616.get("Ep0") or 0) <= float(e616.get("Sp0") or 0)

        if e616_ep3_small and e81_ep3_small and float(e616.get("Ep3") or 0) <= float(e81.get("Ep3") or 0):
            signals.euro_direction = 3
        elif e616_ep0_small and e81_ep0_small and float(e616.get("Ep0") or 0) <= float(e81.get("Ep0") or 0):
            signals.euro_direction = 0

        # A1 核心：欧亚方向相反 = 冲突信号
        if signals.euro_direction != -1 and signals.asia_direction != -1:
            signals.euro_asia_conflict = (signals.euro_direction != signals.asia_direction)

    def _fill_fundamental_signals(
        self,
        db: FootDBConnection,
        match_id: str,
        match: FootMatchLast,
        signals: FootMatchSignals,
    ) -> None:
        """填充基本面信号（复现 C1Service 的积分榜+对战+近期逻辑）"""
        main_id = match.main_team_id
        guest_id = match.guest_team_id

        # ── 积分榜排名差 ──
        score_rows = db.query(
            """
            SELECT TeamId, Type, Ranking, MatchCount
            FROM t_b_f_score
            WHERE MatchId = %s AND TeamId IN (%s, %s)
            """,
            (match_id, main_id, guest_id),
        )
        main_zong = next(
            (r for r in score_rows if r.get("TeamId") == main_id and r.get("Type") == "总"), None
        )
        guest_zong = next(
            (r for r in score_rows if r.get("TeamId") == guest_id and r.get("Type") == "总"), None
        )
        if main_zong and guest_zong:
            mc = int(main_zong.get("MatchCount") or 0)
            gc = int(guest_zong.get("MatchCount") or 0)
            if mc >= 8 and gc >= 8:
                signals.ranking_diff = float(
                    int(main_zong.get("Ranking") or 0) - int(guest_zong.get("Ranking") or 0)
                )

        # ── 近期对战历史（最近 4 场）──
        battle_rows = db.query(
            """
            SELECT BattleMainTeamId, BattleGuestTeamId,
                   BattleMainTeamGoals, BattleGuestTeamGoals
            FROM t_b_f_battle
            WHERE MatchId = %s
            ORDER BY BattleMatchDate DESC
            LIMIT 4
            """,
            (match_id,),
        )
        main_win = 0
        guest_win = 0
        for r in battle_rows:
            bmid = r.get("BattleMainTeamId")
            bgid = r.get("BattleGuestTeamId")
            bmg = int(r.get("BattleMainTeamGoals") or 0)
            bgg = int(r.get("BattleGuestTeamGoals") or 0)
            if bmid == main_id and bmg > bgg:
                main_win += 1
            if bgid == main_id and bgg > bmg:
                main_win += 1
            if bmid == guest_id and bmg > bgg:
                guest_win += 1
            if bgid == guest_id and bgg > bmg:
                guest_win += 1
        total_battles = main_win + guest_win
        if total_battles > 0:
            signals.h2h_main_win_rate = main_win / total_battles

        # ── 近期战绩（最近 4 场）──
        match_date_str = match.match_date.strftime("%Y-%m-%d") if match.match_date else "2099-01-01"
        jin_main = db.query(
            """
            SELECT HomeTeam, GuestTeam, HomeScore, GuestScore
            FROM t_b_f_jin
            WHERE HomeTeam = %s OR GuestTeam = %s
            ORDER BY MatchTimeStr DESC LIMIT 4
            """,
            (main_id, main_id),
        )
        jin_guest = db.query(
            """
            SELECT HomeTeam, GuestTeam, HomeScore, GuestScore
            FROM t_b_f_jin
            WHERE HomeTeam = %s OR GuestTeam = %s
            ORDER BY MatchTimeStr DESC LIMIT 4
            """,
            (guest_id, guest_id),
        )

        def _win_rate(rows: list[dict], team_id: str) -> float:
            wins = 0
            for r in rows:
                try:
                    hs = int(r.get("HomeScore") or 0)
                    gs = int(r.get("GuestScore") or 0)
                except (ValueError, TypeError):
                    continue
                if r.get("HomeTeam") == team_id and hs > gs:
                    wins += 1
                elif r.get("GuestTeam") == team_id and gs > hs:
                    wins += 1
            return wins / len(rows) if rows else 0.0

        signals.recent_main_win_rate = _win_rate(jin_main, main_id)
        signals.recent_guest_win_rate = _win_rate(jin_guest, guest_id)

        # ── C1 BF 让球（简化版，取亚赔参考公司）──
        asia_ref = db.query(
            "SELECT ELetBall FROM t_asia_his WHERE MatchId = %s AND CompId = %s LIMIT 1",
            (match_id, self._c1_refer_asia),
        )
        if asia_ref:
            instant_lb = float(asia_ref[0].get("ELetBall") or 0)
            # BF 让球 = ranking_diff 贡献 + h2h 贡献 + recent 贡献（简化）
            bf_let_ball = 0.0
            if signals.ranking_diff != 0:
                bf_let_ball += 0.25 * (abs(signals.ranking_diff) / 5.0) * (
                    1 if signals.ranking_diff < 0 else -1
                )
            if main_win > guest_win:
                bf_let_ball += 0.25
            elif guest_win > main_win:
                bf_let_ball -= 0.25
            if signals.recent_main_win_rate > signals.recent_guest_win_rate + 0.2:
                bf_let_ball += 0.25
            elif signals.recent_guest_win_rate > signals.recent_main_win_rate + 0.2:
                bf_let_ball -= 0.25
            signals.c1_my_let_ball = round(bf_let_ball, 3)
            signals.c1_let_ball_diff = round(bf_let_ball - instant_lb, 3)

    def _fill_model_signals(
        self, db: FootDBConnection, match_id: str, signals: FootMatchSignals
    ) -> None:
        """填充 foot 各模型的结论信号"""
        rows = db.query(
            """
            SELECT AlFlag, PreResult, HitCount, TOVoid
            FROM t_analy_result
            WHERE MatchId = %s AND TOVoid = 0
            """,
            (match_id,),
        )
        model_signals: dict[str, int] = {}
        for r in rows:
            flag = str(r.get("AlFlag") or "")
            pre = int(r.get("PreResult") or -1)
            if flag and pre in (0, 1, 3):
                model_signals[flag] = pre

        signals.model_signals = model_signals

        if not model_signals:
            return

        # 计算多模型共识
        from collections import Counter
        counts = Counter(model_signals.values())
        most_common = counts.most_common(1)
        if most_common:
            top_result, top_count = most_common[0]
            signals.model_consensus = top_result
            signals.model_consensus_count = top_count
            # 有任意两个模型方向不同 = 冲突
            signals.model_conflict = len(counts) > 1

    def _fetch_analy_results(
        self, al_flags: Optional[list[str]]
    ) -> list[FootAnalyResult]:
        """获取近期分析结果列表"""
        cutoff = (datetime.now() - timedelta(days=self._analy_days)).strftime("%Y-%m-%d")
        sql = """
            SELECT Id, MatchId, MatchDate, AlFlag, AlSeq,
                   PreResult, Result, HitCount, THitCount,
                   LetBall, SLetBall, MyLetBall, TOVoid, TOVoidDesc
            FROM t_analy_result
            WHERE MatchDate >= %s
        """
        args: list[Any] = [cutoff]
        if al_flags:
            placeholders = ",".join(["%s"] * len(al_flags))
            sql += f" AND AlFlag IN ({placeholders})"
            args.extend(al_flags)
        sql += " ORDER BY MatchDate DESC LIMIT 500"

        with FootDBConnection(self._dsn) as db:
            rows = db.query(sql, tuple(args))

        results = []
        for r in rows:
            md_raw = r.get("MatchDate")
            md = md_raw if isinstance(md_raw, datetime) else None
            results.append(FootAnalyResult(
                id=str(r.get("Id") or ""),
                match_id=str(r.get("MatchId") or ""),
                match_date=md,
                al_flag=str(r.get("AlFlag") or ""),
                al_seq=str(r.get("AlSeq") or ""),
                pre_result=int(r.get("PreResult") or -1),
                result=str(r.get("Result") or ""),
                hit_count=int(r.get("HitCount") or 0),
                t_hit_count=int(r.get("THitCount") or 0),
                let_ball=float(r.get("LetBall") or 0),
                s_let_ball=float(r.get("SLetBall") or 0),
                my_let_ball=float(r.get("MyLetBall") or 0),
                to_void=bool(r.get("TOVoid")),
                to_void_desc=str(r.get("TOVoidDesc") or ""),
            ))
        return results

    def _query_match_by_id(
        self, db: FootDBConnection, match_id: str
    ) -> Optional[FootMatchLast]:
        rows = db.query(
            "SELECT * FROM t_match_last WHERE Id = %s LIMIT 1", (match_id,)
        )
        if not rows:
            rows = db.query(
                "SELECT * FROM t_match_his WHERE Id = %s LIMIT 1", (match_id,)
            )
        return self._row_to_match(rows[0]) if rows else None

    def _query_match_last(
        self,
        db: FootDBConnection,
        main_team_id: str,
        guest_team_id: str,
        match_date: str,
    ) -> Optional[FootMatchLast]:
        """按队名+日期查找，先查临时表再查历史表"""
        sql = """
            SELECT * FROM t_match_last
            WHERE MainTeamId = %s AND GuestTeamId = %s
              AND DATE(MatchDate) = %s
            LIMIT 1
        """
        rows = db.query(sql, (main_team_id, guest_team_id, match_date))
        if not rows:
            sql = sql.replace("t_match_last", "t_match_his")
            rows = db.query(sql, (main_team_id, guest_team_id, match_date))
        return self._row_to_match(rows[0]) if rows else None

    def _query_league(
        self, db: FootDBConnection, league_id: str
    ) -> Optional[FootLeague]:
        rows = db.query(
            "SELECT Id, Name FROM t_league WHERE Id = %s LIMIT 1", (league_id,)
        )
        if not rows:
            return None
        r = rows[0]
        return FootLeague(id=str(r.get("Id") or ""), name=str(r.get("Name") or ""))

    @staticmethod
    def _row_to_match(r: dict[str, Any]) -> FootMatchLast:
        md_raw = r.get("MatchDate")
        md = md_raw if isinstance(md_raw, datetime) else None
        dd_raw = r.get("DataDate")
        dd = dd_raw if isinstance(dd_raw, datetime) else None
        return FootMatchLast(
            id=str(r.get("Id") or ""),
            match_date=md,
            league_id=str(r.get("LeagueId") or ""),
            main_team_id=str(r.get("MainTeamId") or ""),
            guest_team_id=str(r.get("GuestTeamId") or ""),
            main_team_goals=int(r.get("MainTeamGoals") or -1),
            guest_team_goals=int(r.get("GuestTeamGoals") or -1),
            data_date=dd,
        )


# ── 全局单例 ──────────────────────────────────────────────────────────────────

_global_bridge: Optional[FootBridge] = None


def get_foot_bridge(cfg_path: Optional[Path] = None) -> FootBridge:
    """获取全局 FootBridge 单例"""
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = FootBridge(cfg_path)
    return _global_bridge


def get_foot_signals(
    main_team_id: str,
    guest_team_id: str,
    match_date: str,
    match_id: Optional[str] = None,
) -> FootMatchSignals:
    """便捷函数：获取单场比赛的 foot 信号"""
    return get_foot_bridge().get_signals_for_match(
        main_team_id=main_team_id,
        guest_team_id=guest_team_id,
        match_date=match_date,
        match_id=match_id,
    )
