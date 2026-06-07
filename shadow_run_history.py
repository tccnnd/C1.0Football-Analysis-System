"""
历史数据 Shadow Run：V24 vs C1.0 预测对比

从 foot MySQL 历史数据中取样，构造 AppMatch，
同时运行 V24 和 C1.0（含 foot 信号增强），
输出对比报告到 reports/shadow_history/

用法：
    python shadow_run_history.py                    # 默认取 50 场
    python shadow_run_history.py --limit 200        # 取 200 场
    python shadow_run_history.py --limit 200 --no-foot  # 不启用 foot 信号
    python shadow_run_history.py --date 2020-03-01  # 指定起始日期
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from c1.audit.calibration_drift import build_calibration_drift_report, normalize_probabilities


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _safe_float(v, default=0.0):
    try:
        return float(v) if v not in (None, "") else default
    except Exception:
        return default


def _normalize_side(v):
    m = {"home":"home","draw":"draw","away":"away",
         "主胜":"home","平局":"draw","客胜":"away",
         "主":"home","平":"draw","客":"away"}
    return m.get(str(v or "").strip().lower(), "")


# ── 从 foot MySQL 取历史比赛 ──────────────────────────────────────────────────

def fetch_history_matches(limit: int, since_date: str, league_filter: list[str] = None, *, foot_native_only: bool = False, until_date: str | None = None) -> list[dict]:
    """从 foot MySQL 取有完整赔率数据的历史比赛

    foot_native_only=True 时仅取 foot 原生数据（排除 football-data.co.uk 导入的 fdu_ 行），
    因为只有 foot 原生数据带有亚赔明细等可驱动治理冲突的信号。
    until_date 提供时作为 MatchDate 的上界（< until_date），用于按时间窗口采样。
    """
    import os
    import pymysql, pymysql.cursors
    password = os.environ.get("FOOT_MYSQL_PASSWORD")
    if not password:
        raise RuntimeError("FOOT_MYSQL_PASSWORD is required for foot MySQL shadow runs")
    conn = pymysql.connect(
        host="127.0.0.1", port=3306,
        user="root",
        password=password,
        database="foot",
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
    )
    cur = conn.cursor()
    # 亚赔用公司名（Crown/Bet365），欧赔用数字 ID（81=伟德，281=Bet365）
    sql = """
        SELECT
            mh.Id, mh.MainTeamId, mh.GuestTeamId,
            DATE(mh.MatchDate) AS match_date,
            TIME(mh.MatchDate) AS match_time,
            mh.MainTeamGoals, mh.GuestTeamGoals,
            l.Name AS league_name,
            ah.SLetBall AS asia_s_let_ball,
            ah.ELetBall AS asia_e_let_ball,
            ah.Sp3 AS asia_sp3, ah.Sp0 AS asia_sp0,
            ah.Ep3 AS asia_ep3, ah.Ep0 AS asia_ep0,
            eh.Sp3 AS euro_sp3, eh.Sp1 AS euro_sp1, eh.Sp0 AS euro_sp0,
            eh.Ep3 AS euro_ep3, eh.Ep1 AS euro_ep1, eh.Ep0 AS euro_ep0
        FROM t_match_his mh
        INNER JOIN t_league l ON l.Id = mh.LeagueId
        INNER JOIN t_euro_his eh ON eh.MatchId = mh.Id AND eh.CompId IN ('81', '281')
        LEFT JOIN t_asia_his ah ON ah.MatchId = mh.Id AND ah.CompId IN ('Crown', 'Bet365')
        WHERE mh.MainTeamGoals >= 0
          AND mh.MatchDate >= %s
          AND eh.Ep3 > 1.0 AND eh.Ep0 > 1.0
    """
    args = [since_date]
    if until_date:
        sql += " AND mh.MatchDate < %s"
        args.append(until_date)
    if foot_native_only:
        sql += " AND mh.Id NOT LIKE 'fdu_%%'"
    if league_filter:
        placeholders = ",".join(["%s"] * len(league_filter))
        sql += f" AND l.Name IN ({placeholders})"
        args.extend(league_filter)
    sql += " ORDER BY mh.MatchDate DESC LIMIT %s"
    args.append(limit)
    cur.execute(sql, tuple(args))
    rows = cur.fetchall()
    conn.close()
    print(f"  从 foot MySQL 取到 {len(rows)} 场历史比赛")
    return [dict(r) for r in rows]


# ── 构造 AppMatch ─────────────────────────────────────────────────────────────

def build_app_match(row: dict):
    """把 foot 历史记录转换为 V24 AppMatch"""
    from v24_app.core import AppMatch

    # 从亚赔反推欧式赔率（用欧赔数据）
    odds_home = _safe_float(row.get("euro_ep3"), 2.20)
    odds_draw = _safe_float(row.get("euro_ep1"), 3.10)
    odds_away = _safe_float(row.get("euro_ep0"), 2.80)
    opening_home = _safe_float(row.get("euro_sp3"), odds_home)
    opening_draw = _safe_float(row.get("euro_sp1"), odds_draw)
    opening_away = _safe_float(row.get("euro_sp0"), odds_away)

    # 确保赔率合法
    if min(odds_home, odds_draw, odds_away) <= 1.0:
        odds_home, odds_draw, odds_away = 2.20, 3.10, 2.80

    match_date = str(row.get("match_date", "2020-01-01"))
    match_time = str(row.get("match_time", "20:00"))[:5]
    if len(match_time) != 5 or ":" not in match_time:
        match_time = "20:00"

    return AppMatch(
        home_team=str(row["MainTeamId"]),
        away_team=str(row["GuestTeamId"]),
        league=str(row.get("league_name", "未知联赛")),
        match_time=match_time,
        match_date=match_date,
        odds_home=odds_home,
        odds_draw=odds_draw,
        odds_away=odds_away,
        opening_odds_home=opening_home,
        opening_odds_draw=opening_draw,
        opening_odds_away=opening_away,
        handicap_line=_safe_float(row.get("asia_e_let_ball"), 0.0),
        return_rate=0.93,
        source="foot_history",
        source_id=str(row["Id"]),
    )


# ── 实际结果判断 ──────────────────────────────────────────────────────────────

def actual_result(row: dict) -> str:
    """从历史数据得出实际结果"""
    hg = row.get("MainTeamGoals", -1)
    ag = row.get("GuestTeamGoals", -1)
    if hg < 0 or ag < 0:
        return "unknown"
    if hg > ag:
        return "home"
    if hg < ag:
        return "away"
    return "draw"


# ── 单场 shadow run ───────────────────────────────────────────────────────────

def run_one_match(
    row: dict,
    v24_predictor,
    shadow_runner,
    enable_foot: bool,
) -> dict | None:
    """对单场比赛运行 V24 + C1.0，返回对比结果"""
    try:
        match = build_app_match(row)
    except Exception as e:
        return {"error": f"build_app_match: {e}", "match_id": str(row.get("Id", ""))}

    # V24 预测
    try:
        v24_pred = v24_predictor(match)
    except Exception as e:
        return {"error": f"v24_predict: {e}", "match_id": match.match_id}

    # C1.0 shadow run（含 foot 信号）
    try:
        from c1.runtime.legacy_bridge import run_shadow_for_legacy_match
        from c1.data import C1AvailabilityStore

        store = C1AvailabilityStore(PROJECT_ROOT)
        extra_fields = store.resolve_for_match(match)

        # 注入 foot 信号
        if enable_foot:
            try:
                from c1.features.foot_features import enrich_with_foot_signals
                v24_side_hint = _normalize_side(v24_pred.get("recommendation", ""))
                extra_fields = enrich_with_foot_signals(
                    {
                        **extra_fields,
                        "home_team": match.home_team,
                        "away_team": match.away_team,
                        "match_date": match.match_date,
                        "match_id": str(row["Id"]),
                        "odds_home": match.odds_home,
                        "odds_draw": match.odds_draw,
                        "odds_away": match.odds_away,
                        "opening_odds_home": match.opening_odds_home,
                        "opening_odds_draw": match.opening_odds_draw,
                        "opening_odds_away": match.opening_odds_away,
                        "handicap_line": match.handicap_line,
                    },
                    predicted_side=v24_side_hint,
                )
            except Exception:
                pass  # foot 增强失败不影响主流程

        shadow = run_shadow_for_legacy_match(
            project_root=PROJECT_ROOT,
            match=match,
            runner=shadow_runner,
            extra_fields=extra_fields,
            governance_state={},
            context={},
            enable_xgboost=True,
            enable_lightgbm=True,
        )
    except Exception as e:
        return {"error": f"c1_shadow: {e}", "match_id": match.match_id}

    # 提取结果
    v24_side = _normalize_side(v24_pred.get("recommendation", ""))
    v24_probabilities = normalize_probabilities(v24_pred.get("probabilities")) or {}
    c1_side = str(shadow.inference_result.predicted_side)
    c1_probabilities = normalize_probabilities(shadow.inference_result.raw_probabilities) or {}
    gov_action = str(shadow.governance_decision.action)
    reason_codes = [str(c) for c in shadow.governance_decision.reason_codes]
    tags = [str(t) for t in shadow.governance_decision.tags]
    gate_statuses = {}
    if isinstance(shadow.governance_decision.trace, dict):
        gate_statuses = shadow.governance_decision.trace.get("gate_statuses", {})

    actual = actual_result(row)
    v24_correct = (v24_side == actual) if actual != "unknown" else None
    c1_correct  = (c1_side  == actual) if actual != "unknown" else None

    foot_available = bool(extra_fields.get("foot_signals_available")) if enable_foot else False
    foot_asia_dir  = extra_fields.get("foot_asia_direction", -1) if enable_foot else -1
    foot_conflict  = bool(extra_fields.get("foot_euro_asia_conflict", False)) if enable_foot else False
    foot_agreement = _safe_float(extra_fields.get("foot_model_agreement"), 0.5) if enable_foot else 0.5

    return {
        "match_id": str(row["Id"]),
        "match_label": f"{match.home_team} vs {match.away_team}",
        "league": match.league,
        "match_date": match.match_date,
        "actual": actual,
        "score": f"{row.get('MainTeamGoals','-')}-{row.get('GuestTeamGoals','-')}",
        # V24
        "v24_side": v24_side,
        "v24_confidence": _safe_float(v24_pred.get("confidence"), 0.0),
        "v24_probabilities": {key: round(value, 6) for key, value in v24_probabilities.items()},
        "v24_correct": v24_correct,
        # C1.0
        "c1_side": c1_side,
        "c1_confidence": _safe_float(shadow.inference_result.confidence, 0.0),
        "c1_probabilities": {key: round(value, 6) for key, value in c1_probabilities.items()},
        "c1_correct": c1_correct,
        # Governance
        "governance_action": gov_action,
        "reason_codes": reason_codes,
        "tags": tags,
        "gate_statuses": gate_statuses,
        "foot_model_agreement": foot_agreement,
        "foot_model_confirmed": "foot_model_confirmed" in tags,
        "foot_model_weak": "foot_model_weak_agreement" in tags,
        "foot_model_critical": "foot_model_critical_disagreement" in tags,
        # 分析维度
        "side_diverged": bool(v24_side and c1_side and v24_side != c1_side),
        "confidence_gap": round(
            _safe_float(shadow.inference_result.confidence) - _safe_float(v24_pred.get("confidence")), 4
        ),
        "foot_signals_available": foot_available,
        "foot_asia_direction": foot_asia_dir,
        "foot_euro_asia_conflict": foot_conflict,
    }


# ── 汇总统计 ──────────────────────────────────────────────────────────────────

def build_report(results: list[dict], enable_foot: bool) -> dict:
    valid = [r for r in results if "error" not in r]
    errors = [r for r in results if "error" in r]
    known = [r for r in valid if r["actual"] != "unknown"]

    gov_counts = Counter(r["governance_action"] for r in valid)
    reason_counts = Counter(c for r in valid for c in r["reason_codes"])
    diverged = [r for r in valid if r["side_diverged"]]

    # 准确率（仅有实际结果的场次）
    v24_hits = sum(1 for r in known if r["v24_correct"])
    c1_hits  = sum(1 for r in known if r["c1_correct"])
    n_known  = len(known)

    # 按 governance action 分组的准确率
    acc_by_action: dict[str, dict] = defaultdict(lambda: {"v24":0,"c1":0,"n":0})
    for r in known:
        a = r["governance_action"]
        acc_by_action[a]["n"] += 1
        if r["v24_correct"]: acc_by_action[a]["v24"] += 1
        if r["c1_correct"]:  acc_by_action[a]["c1"]  += 1

    # foot 信号统计
    foot_stats = {}
    if enable_foot:
        foot_avail = [r for r in valid if r["foot_signals_available"]]
        foot_confirmed = [r for r in foot_avail if r["foot_model_confirmed"]]
        foot_weak = [r for r in foot_avail if r["foot_model_weak"]]
        foot_critical = [r for r in foot_avail if r["foot_model_critical"]]
        foot_conflict = [r for r in foot_avail if r["foot_euro_asia_conflict"]]

        def acc(lst):
            k = [r for r in lst if r["actual"] != "unknown"]
            if not k: return None
            return {
                "v24": sum(1 for r in k if r["v24_correct"]) / len(k),
                "c1":  sum(1 for r in k if r["c1_correct"])  / len(k),
                "n": len(k),
            }

        foot_stats = {
            "available": len(foot_avail),
            "confirmed_count": len(foot_confirmed),
            "weak_count": len(foot_weak),
            "critical_count": len(foot_critical),
            "conflict_count": len(foot_conflict),
            "confirmed_accuracy": acc(foot_confirmed),
            "weak_accuracy": acc(foot_weak),
            "critical_accuracy": acc(foot_critical),
            "conflict_accuracy": acc(foot_conflict),
        }

    # 治理分离度：APPROVE 组准确率 - DOWNGRADE 组准确率（验收门槛 >= 0.05）
    approve_acc = None
    downgrade_acc = None
    block_acc = None
    approve_n = acc_by_action.get("APPROVE", {}).get("n", 0)
    downgrade_n = acc_by_action.get("DOWNGRADE", {}).get("n", 0)
    block_n = acc_by_action.get("BLOCK", {}).get("n", 0)
    if approve_n:
        approve_acc = acc_by_action["APPROVE"]["c1"] / approve_n
    if downgrade_n:
        downgrade_acc = acc_by_action["DOWNGRADE"]["c1"] / downgrade_n
    if block_n:
        block_acc = acc_by_action["BLOCK"]["c1"] / block_n
    governance_separation = None
    if approve_acc is not None and downgrade_acc is not None:
        governance_separation = approve_acc - downgrade_acc
    approve_rate = (approve_n / n_known) if n_known else None
    calibration_drift = build_calibration_drift_report(known)

    return {
        "total": len(results),
        "valid": len(valid),
        "errors": len(errors),
        "known_outcome": n_known,
        "governance_counts": dict(gov_counts),
        "top_reason_codes": dict(reason_counts.most_common(10)),
        "diverged_count": len(diverged),
        "v24_accuracy": round(v24_hits / n_known, 4) if n_known else None,
        "c1_accuracy":  round(c1_hits  / n_known, 4) if n_known else None,
        "governance_separation": round(governance_separation, 4) if governance_separation is not None else None,
        "approve_accuracy": round(approve_acc, 4) if approve_acc is not None else None,
        "downgrade_accuracy": round(downgrade_acc, 4) if downgrade_acc is not None else None,
        "block_accuracy": round(block_acc, 4) if block_acc is not None else None,
        "approve_rate": round(approve_rate, 4) if approve_rate is not None else None,
        "approve_n": approve_n,
        "downgrade_n": downgrade_n,
        "block_n": block_n,
        "accuracy_by_governance": {
            k: {
                "v24": round(v["v24"]/v["n"], 4) if v["n"] else None,
                "c1":  round(v["c1"] /v["n"], 4) if v["n"] else None,
                "n": v["n"],
            }
            for k, v in acc_by_action.items()
        },
        "foot_stats": foot_stats,
        "calibration_drift": calibration_drift,
    }


# ── 报告输出 ──────────────────────────────────────────────────────────────────

def write_reports(results: list[dict], report: dict, enable_foot: bool) -> tuple[str, str]:
    report_dir = PROJECT_ROOT / "reports" / "shadow_history"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = report_dir / f"shadow_history_{stamp}.json"
    json_path.write_text(
        json.dumps({"summary": report, "rows": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Markdown
    md_path = report_dir / f"shadow_history_{stamp}.md"
    lines = [
        "# Shadow Run 历史数据对比报告",
        "",
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 总场次: {report['total']}  有效: {report['valid']}  有结果: {report['known_outcome']}",
        f"- foot 信号: {'启用' if enable_foot else '禁用'}",
        "",
        "## Governance 决策分布",
        "",
    ]
    for action, cnt in sorted(report["governance_counts"].items()):
        lines.append(f"- {action}: {cnt}")

    lines += ["", "## 准确率对比", ""]
    v24_acc = report["v24_accuracy"]
    c1_acc  = report["c1_accuracy"]
    n = report["known_outcome"]
    lines.append(f"| 系统 | 准确率 | 场次 |")
    lines.append(f"|------|--------|------|")
    lines.append(f"| V24  | {v24_acc:.1%} | {n} |" if v24_acc else "| V24 | N/A | - |")
    lines.append(f"| C1.0 | {c1_acc:.1%} | {n} |" if c1_acc else "| C1.0 | N/A | - |")

    drift = report.get("calibration_drift", {}) if isinstance(report.get("calibration_drift"), dict) else {}
    drift_models = drift.get("models", {}) if isinstance(drift.get("models"), dict) else {}
    if drift_models:
        lines += ["", "## 校准漂移", ""]
        lines.append("| 系统 | 样本 | ECE | Brier | Logloss | 平均置信度 | 实际命中率 | Gap |")
        lines.append("|------|------|-----|-------|---------|------------|------------|-----|")
        for label, key in (("V24", "v24"), ("C1.0", "c1")):
            item = drift_models.get(key, {}) if isinstance(drift_models.get(key), dict) else {}
            def pct(value):
                return "N/A" if value is None else f"{float(value):.1%}"
            lines.append(
                f"| {label} | {item.get('count', 0)} | {pct(item.get('ece'))} | "
                f"{item.get('brier', 'N/A')} | {item.get('logloss', 'N/A')} | "
                f"{pct(item.get('avg_confidence'))} | {pct(item.get('avg_actual_rate'))} | "
                f"{pct(item.get('calibration_gap'))} |"
            )

    lines += ["", "### 按 Governance 动作分组准确率", ""]
    lines.append("| 动作 | V24 准确率 | C1.0 准确率 | 场次 |")
    lines.append("|------|-----------|------------|------|")
    for action, acc in sorted(report["accuracy_by_governance"].items()):
        v = f"{acc['v24']:.1%}" if acc["v24"] is not None else "N/A"
        c = f"{acc['c1']:.1%}"  if acc["c1"]  is not None else "N/A"
        lines.append(f"| {action} | {v} | {c} | {acc['n']} |")

    lines += ["", "## Top 10 Reason Codes", ""]
    for code, cnt in report["top_reason_codes"].items():
        lines.append(f"- {code}: {cnt}")

    if enable_foot and report.get("foot_stats"):
        fs = report["foot_stats"]
        lines += ["", "## foot 信号统计", ""]
        lines.append(f"- 有 foot 信号: {fs['available']}")
        lines.append(f"- foot_model_confirmed: {fs['confirmed_count']}")
        lines.append(f"- foot_model_weak: {fs['weak_count']}")
        lines.append(f"- foot_model_critical: {fs['critical_count']}")
        lines.append(f"- 欧亚冲突: {fs['conflict_count']}")
        lines += ["", "### foot 信号分组准确率", ""]
        lines.append("| 分组 | V24 准确率 | C1.0 准确率 | 场次 |")
        lines.append("|------|-----------|------------|------|")
        for label, key in [
            ("foot_confirmed", "confirmed_accuracy"),
            ("foot_weak", "weak_accuracy"),
            ("foot_critical", "critical_accuracy"),
            ("欧亚冲突", "conflict_accuracy"),
        ]:
            acc = fs.get(key)
            if acc:
                v = f"{acc['v24']:.1%}" if acc["v24"] is not None else "N/A"
                c = f"{acc['c1']:.1%}"  if acc["c1"]  is not None else "N/A"
                lines.append(f"| {label} | {v} | {c} | {acc['n']} |")

    lines += ["", "## 预测分歧场次", ""]
    diverged = [r for r in results if r.get("side_diverged")]
    lines.append(f"共 {len(diverged)} 场 V24 与 C1.0 预测方向不同：")
    lines.append("")
    lines.append("| 比赛 | 日期 | V24 | C1.0 | 实际 | Governance | foot 信号 |")
    lines.append("|------|------|-----|------|------|-----------|---------|")
    for r in diverged[:30]:
        foot_tag = ""
        if r.get("foot_model_confirmed"): foot_tag = "✅confirmed"
        elif r.get("foot_model_weak"):    foot_tag = "⚠️weak"
        elif r.get("foot_model_critical"):foot_tag = "🔴critical"
        elif r.get("foot_euro_asia_conflict"): foot_tag = "⚡conflict"
        lines.append(
            f"| {r['match_label']} | {r['match_date']} | {r['v24_side']} | "
            f"{r['c1_side']} | {r['actual']} | {r['governance_action']} | {foot_tag} |"
        )

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return str(md_path), str(json_path)


# ── 主函数 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="历史数据 Shadow Run")
    parser.add_argument("--limit",   type=int, default=50,           help="取样场次数（默认 50）")
    parser.add_argument("--date",    type=str, default="2019-01-01", help="起始日期（默认 2019-01-01）")
    parser.add_argument("--until",   type=str, default="",           help="截止日期（不含），用于按时间窗口采样")
    parser.add_argument("--no-foot", action="store_true",            help="禁用 foot 信号增强")
    parser.add_argument("--leagues", type=str, default="",           help="联赛过滤（逗号分隔，如 英超,西甲,法甲）")
    parser.add_argument("--foot-native-only", action="store_true",   help="仅取 foot 原生数据（排除 fdu_ 导入），用于治理信号验证")
    parser.add_argument(
        "--acceptance", action="store_true",
        help="验收模式：强制 signal-bearing 采样（排除 fdu_），并对 foot 信号覆盖率与治理门槛做验收判定。"
             " 用于 c1_primary 切换前的正式 shadow run。",
    )
    parser.add_argument(
        "--min-foot-coverage", type=float, default=0.60,
        help="验收模式下要求的最低 foot 信号覆盖率（默认 0.60）。低于此值则判定样本不足以评估治理。",
    )
    args = parser.parse_args()

    enable_foot = not args.no_foot
    # 验收模式：治理指标只有在 signal-bearing 数据上才有意义。
    # 历史教训：默认 DESC 采样会命中 2021-2025 的 fdu_ 导入（无 foot 信号表），
    # 导致 0 DOWNGRADE / separation 塌陷，得出错误的"未达标"结论。
    # 因此验收模式强制排除 fdu_，并禁止关闭 foot 信号。
    foot_native_only = args.foot_native_only or args.acceptance
    if args.acceptance:
        if args.no_foot:
            print("  ❌ 验收模式不能与 --no-foot 同用：治理验收必须启用 foot 信号。")
            sys.exit(2)
        enable_foot = True
        if args.limit < 1000:
            print(f"  ⚠️ 验收模式建议 --limit >= 1000（当前 {args.limit}），样本过小会使分离度不稳定。")
    league_filter = [l.strip() for l in args.leagues.split(",") if l.strip()] if args.leagues else []

    print(f"\n{'='*60}")
    print(f"  历史数据 Shadow Run")
    print(f"  场次: {args.limit}  起始: {args.date}  foot信号: {'启用' if enable_foot else '禁用'}")
    if league_filter:
        print(f"  联赛过滤: {league_filter}")
    print(f"{'='*60}\n")

    # 1. 取历史数据
    print("1. 从 foot MySQL 取历史比赛...")
    try:
        rows = fetch_history_matches(args.limit, args.date, league_filter, foot_native_only=foot_native_only, until_date=(args.until or None))
    except Exception as e:
        print(f"  ❌ 数据库连接失败: {e}")
        print("  请确认 MySQL 服务正在运行（MySQL84 服务）")
        sys.exit(1)

    if not rows:
        print("  ❌ 未找到符合条件的比赛")
        sys.exit(1)

    # 2. 初始化 V24 和 C1.0
    print("2. 初始化预测引擎...")
    from v24_app.core import predict_match as v24_predict, _RATINGS_CACHE
    # 清除 V24 评分缓存，强制重新加载（使用 foot ELO 评分）
    for pool in _RATINGS_CACHE:
        _RATINGS_CACHE[pool] = {"signature": None, "ratings": {}}
    from c1.runtime.shadow import C1ShadowRunner
    shadow_runner = C1ShadowRunner(PROJECT_ROOT)
    print("  ✅ V24 + C1.0 初始化完成（ELO 缓存已清除）")

    # 3. 逐场运行
    print(f"3. 运行 {len(rows)} 场对比...")
    results = []
    t0 = time.time()

    # 并行执行（线程池，受 MySQL 连接数限制取 4 线程）
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(run_one_match, row, v24_predict, shadow_runner, enable_foot): i
            for i, row in enumerate(rows)
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
            done = len(results)
            if done % 10 == 0 or done == len(rows):
                elapsed = time.time() - t0
                rate = done / max(elapsed, 0.1)
                print(f"  {done}/{len(rows)}  {elapsed:.0f}s  {rate:.1f} 场/s", end="\r")
    print()

    # 4. 汇总
    print("4. 生成报告...")
    report = build_report(results, enable_foot)
    md_path, json_path = write_reports(results, report, enable_foot)

    # 5. 打印摘要
    print(f"\n{'='*60}")
    print(f"  Shadow Run 完成")
    print(f"{'='*60}")
    print(f"  总场次: {report['total']}  有效: {report['valid']}  有结果: {report['known_outcome']}")
    print(f"  分歧场次: {report['diverged_count']}")
    print()
    print(f"  Governance 分布:")
    for action, cnt in sorted(report["governance_counts"].items()):
        pct = cnt / max(report["valid"], 1)
        print(f"    {action:<12} {cnt:>4}  ({pct:.1%})")
    print()
    if report["v24_accuracy"] is not None:
        v24_acc = report["v24_accuracy"]
        c1_acc  = report["c1_accuracy"]
        delta   = c1_acc - v24_acc
        print(f"  准确率（{report['known_outcome']} 场有结果）:")
        print(f"    V24 : {v24_acc:.1%}")
        print(f"    C1.0: {c1_acc:.1%}  ({delta:+.1%})")
    print()
    # 治理分离度门槛报告
    sep = report.get("governance_separation")
    appr_acc = report.get("approve_accuracy")
    down_acc = report.get("downgrade_accuracy")
    appr_rate = report.get("approve_rate")
    print(f"  治理分离度 (APPROVE acc - DOWNGRADE acc, 门槛 >= 5%):")
    print(f"    APPROVE  : acc={'N/A' if appr_acc is None else f'{appr_acc:.1%}'}  n={report.get('approve_n')}  rate={'N/A' if appr_rate is None else f'{appr_rate:.1%}'}")
    print(f"    DOWNGRADE: acc={'N/A' if down_acc is None else f'{down_acc:.1%}'}  n={report.get('downgrade_n')}")
    print(f"    BLOCK    : n={report.get('block_n')}")
    if sep is not None:
        flag = "达标" if sep >= 0.05 else "未达标"
        print(f"    separation = {sep:+.1%}  [{flag}]")
    else:
        print(f"    separation = N/A (APPROVE 或 DOWNGRADE 组为空)")
    print()
    print(f"  Top Reason Codes:")
    for code, cnt in list(report["top_reason_codes"].items())[:5]:
        print(f"    {code:<40} {cnt}")
    if enable_foot and report.get("foot_stats"):
        fs = report["foot_stats"]
        print()
        print(f"  foot 信号:")
        print(f"    有信号: {fs['available']}/{report['valid']}")
        print(f"    confirmed: {fs['confirmed_count']}  weak: {fs['weak_count']}  critical: {fs['critical_count']}")
        print(f"    欧亚冲突: {fs['conflict_count']}")
    print()

    # ── 验收判定（仅 --acceptance 模式）──────────────────────────────────────
    # 固化样本约束：治理/准确率验收必须在 signal-bearing 数据上进行，
    # 且 foot 信号覆盖率必须足够，否则判定为"样本不足，结论无效"。
    acceptance_failed = False
    if args.acceptance:
        print(f"{'='*60}")
        print(f"  验收判定 (c1_primary 切换前置门槛)")
        print(f"{'='*60}")
        coverage = 0.0
        valid_n = max(report.get("valid", 0), 1)
        if report.get("foot_stats"):
            coverage = report["foot_stats"].get("available", 0) / valid_n
        cov_ok = coverage >= args.min_foot_coverage
        print(f"  [1] foot 信号覆盖率: {coverage:.1%} (要求 >= {args.min_foot_coverage:.0%})  "
              f"{'PASS' if cov_ok else 'FAIL（样本不足以评估治理）'}")

        sep_val = report.get("governance_separation")
        sep_ok = sep_val is not None and sep_val >= 0.05
        sep_str = "N/A" if sep_val is None else f"{sep_val:+.1%}"
        print(f"  [2] 治理分离度: {sep_str} (要求 >= 5%)  {'PASS' if sep_ok else 'FAIL'}")

        c1_acc = report.get("c1_accuracy")
        v24_acc = report.get("v24_accuracy")
        acc_ok = c1_acc is not None and v24_acc is not None and c1_acc >= v24_acc
        print(f"  [3] 准确率: C1={'N/A' if c1_acc is None else f'{c1_acc:.1%}'} "
              f"vs V24={'N/A' if v24_acc is None else f'{v24_acc:.1%}'} (要求 C1 >= V24)  "
              f"{'PASS' if acc_ok else 'FAIL（accuracy 硬阻断）'}")

        all_ok = cov_ok and sep_ok and acc_ok
        print()
        if not cov_ok:
            print("  结论: 样本不满足覆盖率要求 —— 本次结果不可用于验收。")
            acceptance_failed = True
        elif all_ok:
            print("  结论: 全部前置门槛达标。注意：是否切换 c1_primary 仍由人工决策，")
            print("        本脚本不修改 runtime_mode.yaml。")
        else:
            print("  结论: 验收未通过，保持 formal_list_default。")
            acceptance_failed = True
        print()

    print(f"  报告已保存:")
    print(f"    Markdown: {md_path}")
    print(f"    JSON    : {json_path}")

    if acceptance_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
