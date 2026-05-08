from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import requests


logger = logging.getLogger(__name__)


@dataclass
class MatchTitan:
    home_team: str
    away_team: str
    league: str
    match_time: str
    match_date: str
    odds_home: float
    odds_draw: float
    odds_away: float
    match_id: str
    handicap_line: float = 0.0
    opening_odds_home: float = 0.0
    opening_odds_draw: float = 0.0
    opening_odds_away: float = 0.0
    return_rate: float = 0.0
    kelly_home: float = 0.0
    kelly_draw: float = 0.0
    kelly_away: float = 0.0
    issue_code: str = ""
    state_code: str = ""
    home_goals: int | None = None
    away_goals: int | None = None

    @property
    def is_finished(self) -> bool:
        return self.state_code == "13" and self.home_goals is not None and self.away_goals is not None


class MatchFetcherTitan:
    """Titan007 竞彩数据抓取器（主源）。"""

    def __init__(self, debug: bool = False, cache_duration: int = 600) -> None:
        self.debug = debug
        self.cache_duration = cache_duration
        self.base_url = "https://jc.titan007.com"
        self.schedule_url = f"{self.base_url}/xml/bf_jc.txt"
        self.odds_url = f"{self.base_url}/xml/odds_jc.txt"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/plain,text/html,*/*",
            "Referer": f"{self.base_url}/index.aspx",
        }
        self.session = requests.Session()
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_file(self, name: str) -> Path:
        return self.cache_dir / name

    def _read_cache(self, name: str) -> str | None:
        path = self._cache_file(name)
        if not path.exists():
            return None
        age = datetime.now().timestamp() - path.stat().st_mtime
        if age > self.cache_duration:
            return None
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None

    def _read_cache_stale(self, name: str) -> str | None:
        path = self._cache_file(name)
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None

    def _write_cache(self, name: str, text: str) -> None:
        self._cache_file(name).write_text(text, encoding="utf-8")

    def _fetch_text(self, url: str, cache_name: str) -> str | None:
        cached = self._read_cache(cache_name)
        if cached is not None:
            return cached

        try:
            response = self.session.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            response.encoding = "utf-8"
            text = response.text
            if text:
                self._write_cache(cache_name, text)
                return text
        except Exception as exc:
            if self.debug:
                logger.warning("Titan 请求失败 %s: %s", url, exc)

        # 在线失败时尝试兜底旧缓存
        stale = self._read_cache_stale(cache_name)
        if stale is not None and self.debug:
            logger.info("Titan 在线失败，回退旧缓存: %s", cache_name)
        return stale

    @staticmethod
    def _safe_float(value: str | None, default: float = 0.0) -> float:
        try:
            return float(value) if value not in (None, "") else default
        except Exception:
            return default

    @staticmethod
    def _safe_int(value: str | None, default: int | None = None) -> int | None:
        try:
            if value in (None, ""):
                return default
            return int(str(value).strip())
        except Exception:
            return default

    @staticmethod
    def _repair_text(text: str) -> str:
        if not text:
            return text
        try:
            repaired = text.encode("latin1").decode("utf-8")
            if repaired:
                return repaired
        except Exception:
            pass
        return text

    @staticmethod
    def _pick_name(raw: str) -> str:
        if not raw:
            return ""
        raw = MatchFetcherTitan._repair_text(raw)
        parts = [item.strip() for item in raw.split(",") if item.strip()]
        return parts[0] if parts else raw.strip()

    @staticmethod
    def _parse_datetime_token(token: str) -> tuple[str, str]:
        # 形如: 2026,3,28,01,00,00
        chunks = [item.strip() for item in token.split(",")]
        if len(chunks) < 6:
            return "", ""
        try:
            year = int(chunks[0])
            month_raw = int(chunks[1])
            # Titan 数据源月份按 JS Date 约定为 0-11，需要转成 1-12。
            month = month_raw + 1 if 0 <= month_raw <= 11 else month_raw
            day = int(chunks[2])
            hour = int(chunks[3])
            minute = int(chunks[4])
            dt = datetime(year, month, day, hour, minute)
            return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
        except Exception:
            return "", ""

    def _parse_sclass_map(self, text: str) -> dict[int, str]:
        # section0: sclass 记录，记录之间 "!"，列之间 "^"
        sclass_map: dict[int, str] = {}
        records = [item for item in text.split("!") if item]
        for record in records:
            arr = record.split("^")
            if len(arr) < 4:
                continue
            try:
                sclass_id = int(arr[0])
            except Exception:
                continue
            sclass_map[sclass_id] = self._pick_name(arr[3])
        return sclass_map

    def _parse_schedule(self, text: str, sclass_map: dict[int, str]) -> list[MatchTitan]:
        matches: list[MatchTitan] = []
        records = [item for item in text.split("!") if item]
        for record in records:
            arr = record.split("^")
            if len(arr) < 13:
                continue
            try:
                sid = int(arr[0])
                sclass_id = int(arr[5]) if arr[5] else 0
            except Exception:
                continue
            match_date, match_time = self._parse_datetime_token(arr[1])
            if not match_date or not match_time:
                continue
            issue_code = arr[4].strip() if len(arr) > 4 else ""
            state_code = arr[3].strip() if len(arr) > 3 else ""
            home_goals = self._safe_int(arr[11] if len(arr) > 11 else None, default=None)
            away_goals = self._safe_int(arr[12] if len(arr) > 12 else None, default=None)
            home_team = self._pick_name(arr[8])
            away_team = self._pick_name(arr[10])
            league = sclass_map.get(sclass_id, "")
            if not home_team or not away_team or not league:
                continue
            matches.append(
                MatchTitan(
                    home_team=home_team,
                    away_team=away_team,
                    league=league,
                    match_time=match_time,
                    match_date=match_date,
                    odds_home=0.0,
                    odds_draw=0.0,
                    odds_away=0.0,
                    match_id=str(sid),
                    issue_code=issue_code,
                    state_code=state_code,
                    home_goals=home_goals,
                    away_goals=away_goals,
                )
            )
        return matches

    def _parse_odds(self, text: str) -> dict[str, tuple[float, float, float, float]]:
        # 格式: sId^home_f^draw_f^away_f^goal^home^draw^away
        odds_map: dict[str, tuple[float, float, float, float]] = {}
        records = [item for item in text.split("!") if item]
        for record in records:
            arr = record.split("^")
            if len(arr) < 4:
                continue
            sid = arr[0].strip()
            if not sid:
                continue
            goal = self._safe_float(arr[4] if len(arr) > 4 else "", default=0.0)
            home = self._safe_float(arr[5] if len(arr) > 5 else "", default=0.0)
            draw = self._safe_float(arr[6] if len(arr) > 6 else "", default=0.0)
            away = self._safe_float(arr[7] if len(arr) > 7 else "", default=0.0)
            if min(home, draw, away) <= 0:
                home = self._safe_float(arr[1] if len(arr) > 1 else "", default=0.0)
                draw = self._safe_float(arr[2] if len(arr) > 2 else "", default=0.0)
                away = self._safe_float(arr[3] if len(arr) > 3 else "", default=0.0)
            odds_map[sid] = (home, draw, away, goal)
        return odds_map

    @staticmethod
    def _issue_prefix(issue_code: str) -> str:
        issue_code = (issue_code or "").strip()
        if not issue_code:
            return ""
        return issue_code[:2]

    def _filter_primary_issue(self, matches: list[MatchTitan]) -> list[MatchTitan]:
        """同日若混入多期号，优先保留主期号（避免多出跨期场次）。"""
        if not matches:
            return matches

        bucket: dict[str, list[MatchTitan]] = {}
        for item in matches:
            key = self._issue_prefix(item.issue_code)
            if not key:
                key = "__unknown__"
            bucket.setdefault(key, []).append(item)

        if len(bucket) <= 1:
            return matches

        ordered = sorted(bucket.items(), key=lambda pair: len(pair[1]), reverse=True)
        dominant_key, dominant_items = ordered[0]
        total = len(matches)
        dominant_count = len(dominant_items)

        # 仅在主期号显著占优时启用过滤，避免误删正常比赛。
        if dominant_key != "__unknown__" and dominant_count >= 3 and dominant_count / total >= 0.7:
            if self.debug:
                logger.info(
                    "Titan 期号过滤: %s/%s，保留主期号 %s (%d/%d)",
                    dominant_count,
                    total,
                    dominant_key,
                    dominant_count,
                    total,
                )
            return dominant_items
        return matches

    def _filter_primary_issue_by_date(self, matches: list[MatchTitan]) -> list[MatchTitan]:
        if not matches:
            return []
        grouped: dict[str, list[MatchTitan]] = {}
        for item in matches:
            grouped.setdefault(item.match_date, []).append(item)
        filtered: list[MatchTitan] = []
        for _, items in grouped.items():
            filtered.extend(self._filter_primary_issue(items))
        return filtered

    @staticmethod
    def _parse_match_datetime(match: MatchTitan) -> datetime | None:
        try:
            return datetime.strptime(f"{match.match_date} {match.match_time}", "%Y-%m-%d %H:%M")
        except Exception:
            return None

    @staticmethod
    def _current_issue_window(now: datetime) -> tuple[datetime, datetime]:
        issue_start = now.replace(hour=11, minute=0, second=0, microsecond=0)
        if now < issue_start:
            issue_start = issue_start - timedelta(days=1)
        return issue_start, issue_start + timedelta(days=1)

    def _load_current_matches(self) -> list[MatchTitan]:
        matches = self._load_schedule_matches()
        if not matches:
            return []
        self._fill_odds(matches)

        return [item for item in matches if min(item.odds_home, item.odds_draw, item.odds_away) > 1.0]

    def _load_schedule_matches(self) -> list[MatchTitan]:
        schedule_text = self._fetch_text(self.schedule_url, "titan_bf_jc.txt")
        if not schedule_text:
            return []
        schedule_text = self._repair_text(schedule_text)
        sections = schedule_text.split("$")
        if len(sections) < 2:
            return []
        sclass_map = self._parse_sclass_map(sections[0])
        return self._parse_schedule(sections[1], sclass_map=sclass_map)

    def _load_odds_map(self) -> dict[str, tuple[float, float, float, float]]:
        odds_text = self._fetch_text(self.odds_url, "titan_odds_jc.txt")
        if not odds_text:
            return {}
        odds_text = self._repair_text(odds_text)
        return self._parse_odds(odds_text.split("$")[0] if "$" in odds_text else odds_text)

    def _fill_odds(self, matches: list[MatchTitan]) -> None:
        if not matches:
            return
        odds_map = self._load_odds_map()
        if not odds_map:
            return
        for match in matches:
            odds = odds_map.get(match.match_id)
            if odds is None:
                continue
            match.odds_home, match.odds_draw, match.odds_away, match.handicap_line = odds

    def get_today_matches(self, now: datetime | None = None) -> list[MatchTitan]:
        if self.debug:
            logger.info("获取 Titan007 竞彩赛事...")

        valid_matches = self._load_current_matches()
        if not valid_matches:
            return []

        current = now or datetime.now()
        issue_start, issue_end = self._current_issue_window(current)
        issue_matches: list[MatchTitan] = []
        for item in valid_matches:
            match_dt = self._parse_match_datetime(item)
            if match_dt is None:
                continue
            if issue_start <= match_dt < issue_end:
                issue_matches.append(item)
        if issue_matches:
            return self._filter_primary_issue(issue_matches)

        # 若当天为空，回退最近未来 3 天
        fallback: list[MatchTitan] = []
        now_date = current.date()
        for item in valid_matches:
            try:
                match_date = datetime.strptime(item.match_date, "%Y-%m-%d").date()
            except Exception:
                continue
            if timedelta(days=0) <= (match_date - now_date) <= timedelta(days=3):
                fallback.append(item)
        return self._filter_primary_issue(fallback)

    def get_today_finished_matches(self) -> list[MatchTitan]:
        return self.get_recent_finished_matches(lookback_days=0)

    def get_recent_finished_matches(self, lookback_days: int = 2) -> list[MatchTitan]:
        valid_matches = self._load_schedule_matches()
        if not valid_matches:
            return []
        # 完场回收不依赖赔率，但若赔率可取到仍补齐，便于后续分析与兜底。
        self._fill_odds(valid_matches)
        window_days = max(0, min(int(lookback_days), 7))
        now_date = datetime.now().date()
        start_date = now_date - timedelta(days=window_days)
        scoped: list[MatchTitan] = []
        for item in valid_matches:
            try:
                match_date = datetime.strptime(item.match_date, "%Y-%m-%d").date()
            except Exception:
                continue
            if start_date <= match_date <= now_date:
                scoped.append(item)
        filtered = self._filter_primary_issue_by_date(scoped)
        return [item for item in filtered if item.is_finished]

    @staticmethod
    def _normalize_schedule_id(schedule_id: str) -> str:
        return "".join(ch for ch in str(schedule_id or "") if ch.isdigit())

    def _analysis_header_url(self, schedule_id: str, lang: str = "cn") -> str:
        sid = self._normalize_schedule_id(schedule_id)
        if len(sid) < 3:
            return ""
        return f"https://livestatic.titan007.com/phone/txt/analysisheader/{lang}/{sid[:1]}/{sid[1:3]}/{sid}.txt"

    def get_result_by_schedule_id(self, schedule_id: str) -> dict | None:
        sid = self._normalize_schedule_id(schedule_id)
        if len(sid) < 3:
            return None
        url = self._analysis_header_url(sid, lang="cn")
        if not url:
            return None

        try:
            response = self.session.get(
                url,
                headers={
                    **self.headers,
                    "Accept": "text/plain,*/*",
                    "Referer": f"https://live.titan007.com/detail/{sid}cn.htm",
                },
                timeout=12,
            )
            response.raise_for_status()
            text = response.text.strip()
        except Exception as exc:
            if self.debug:
                logger.warning("Titan analysisheader 请求失败 %s: %s", sid, exc)
            return None

        if not text or "^" not in text:
            return None
        arr = text.split("^")
        if len(arr) < 12:
            return None

        state_code = arr[4].strip()
        home_goals = self._safe_int(arr[10] if len(arr) > 10 else None, default=None)
        away_goals = self._safe_int(arr[11] if len(arr) > 11 else None, default=None)
        try:
            state_int = int(state_code)
        except Exception:
            state_int = None

        is_finished = state_int is not None and state_int < 0 and home_goals is not None and away_goals is not None
        return {
            "schedule_id": sid,
            "state_code": state_code,
            "home_goals": home_goals,
            "away_goals": away_goals,
            "is_finished": is_finished,
        }
