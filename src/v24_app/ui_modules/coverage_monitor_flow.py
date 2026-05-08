from __future__ import annotations

from typing import Mapping


def summarize_prediction_coverage(
    *,
    predictions: Mapping[str, Mapping[str, object]],
    formal_count: int = 0,
) -> dict[str, object]:
    analyzed_count = len(predictions)
    if analyzed_count <= 0:
        return {
            "analyzed_count": 0,
            "single_match_count": 0,
            "single_coverage": 0.0,
            "single_pick_count": 0,
            "parlay_match_count": 0,
            "parlay_coverage": 0.0,
            "formal_count": max(0, int(formal_count)),
            "formal_coverage": 0.0,
            "by_play_match_count": {},
            "risk_level": "empty",
            "risk_reasons": ["no_predictions"],
        }

    single_match_count = 0
    parlay_match_count = 0
    single_pick_count = 0
    by_play_sets: dict[str, set[str]] = {}

    for match_id, prediction in predictions.items():
        if not isinstance(prediction, Mapping):
            continue
        single_items = prediction.get("single_play_recommendations", [])
        if not isinstance(single_items, list):
            single_items = []
        parlay_items = prediction.get("parlay_eligible_plays", [])
        if not isinstance(parlay_items, list):
            parlay_items = []

        if single_items:
            single_match_count += 1
        if parlay_items:
            parlay_match_count += 1
        single_pick_count += len(single_items)

        for item in single_items:
            if not isinstance(item, Mapping):
                continue
            play_type = str(item.get("play_type", "")).strip() or "unknown"
            by_play_sets.setdefault(play_type, set()).add(str(match_id))

    single_coverage = single_match_count / analyzed_count
    parlay_coverage = parlay_match_count / analyzed_count
    formal_count = max(0, int(formal_count))
    formal_coverage = min(1.0, formal_count / analyzed_count) if analyzed_count > 0 else 0.0

    risk_reasons: list[str] = []
    risk_level = "ok"
    if single_coverage < 0.28:
        risk_level = "warn"
        risk_reasons.append("single_coverage_low")
    elif single_coverage > 0.88:
        risk_level = "warn"
        risk_reasons.append("single_coverage_high")
    if analyzed_count >= 8 and formal_coverage < 0.10:
        risk_level = "warn"
        risk_reasons.append("formal_coverage_low")
    if analyzed_count >= 8 and single_pick_count / max(single_match_count, 1) > 3.2:
        risk_level = "warn"
        risk_reasons.append("single_picks_too_many")

    by_play_match_count = {key: len(value) for key, value in by_play_sets.items()}
    return {
        "analyzed_count": analyzed_count,
        "single_match_count": single_match_count,
        "single_coverage": round(single_coverage, 4),
        "single_pick_count": single_pick_count,
        "parlay_match_count": parlay_match_count,
        "parlay_coverage": round(parlay_coverage, 4),
        "formal_count": formal_count,
        "formal_coverage": round(formal_coverage, 4),
        "by_play_match_count": by_play_match_count,
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
    }


def build_coverage_status_suffix(summary: Mapping[str, object]) -> str:
    analyzed = int(summary.get("analyzed_count", 0) or 0)
    single_cov = float(summary.get("single_coverage", 0.0) or 0.0)
    formal_cov = float(summary.get("formal_coverage", 0.0) or 0.0)
    risk_level = str(summary.get("risk_level", "ok"))
    if analyzed <= 0:
        return "覆盖率 0% (无预测)"
    flag = "预警" if risk_level == "warn" else "正常"
    return f"覆盖率 {single_cov:.0%} | 正式 {formal_cov:.0%} | {flag}"


def build_coverage_monitor_text(summary: Mapping[str, object]) -> str:
    analyzed = int(summary.get("analyzed_count", 0) or 0)
    single_count = int(summary.get("single_match_count", 0) or 0)
    parlay_count = int(summary.get("parlay_match_count", 0) or 0)
    single_cov = float(summary.get("single_coverage", 0.0) or 0.0)
    parlay_cov = float(summary.get("parlay_coverage", 0.0) or 0.0)
    formal_count = int(summary.get("formal_count", 0) or 0)
    formal_cov = float(summary.get("formal_coverage", 0.0) or 0.0)
    single_pick_count = int(summary.get("single_pick_count", 0) or 0)
    by_play = summary.get("by_play_match_count", {})
    if not isinstance(by_play, Mapping):
        by_play = {}

    lines = [
        "推荐覆盖率监控",
        f"- 已分析: {analyzed}",
        f"- 单关覆盖: {single_count}/{analyzed} ({single_cov:.1%})",
        f"- 二串一覆盖: {parlay_count}/{analyzed} ({parlay_cov:.1%})",
        f"- 正式建议覆盖: {formal_count}/{analyzed} ({formal_cov:.1%})",
        f"- 单关推荐条数: {single_pick_count}",
        "",
        "玩法覆盖:",
    ]
    for play_type in ("1x2", "handicap", "total_goals", "score", "htft"):
        lines.append(f"- {play_type}: {int(by_play.get(play_type, 0) or 0)} 场")

    risk_reasons = summary.get("risk_reasons", [])
    if not isinstance(risk_reasons, list):
        risk_reasons = []
    risk_level = str(summary.get("risk_level", "ok"))
    lines.extend(["", f"状态: {'预警' if risk_level == 'warn' else '正常'}"])
    if risk_reasons:
        lines.append(f"原因: {', '.join(str(item) for item in risk_reasons)}")
    return "\n".join(lines)
