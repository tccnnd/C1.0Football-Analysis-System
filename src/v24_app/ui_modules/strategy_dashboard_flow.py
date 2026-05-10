from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Mapping, Sequence


ROLE_LABELS = {
    "primary": "\u4e3b\u7b56\u7565",
    "backup": "\u5907\u9009",
    "observe": "\u89c2\u5bdf",
}
PLAY_LABELS = {
    "market_1x2": "\u5e02\u573a\u80dc\u5e73\u8d1f",
    "1x2": "\u80dc\u5e73\u8d1f",
    "handicap": "\u8ba9\u7403",
    "ou": "\u5927\u5c0f\u7403",
    "total_goals": "\u603b\u8fdb\u7403",
    "score": "\u6bd4\u5206",
}
DATA_LAYER_LABELS = {
    "historical_market": "\u5386\u53f2\u5e02\u573a",
    "app_settlement": "APP \u7ed3\u7b97",
    "jc_stratified_market": "\u7ade\u5f69\u5206\u5c42",
}
SCOPE_LABELS = {
    "global": "\u5168\u5c40",
    "league": "\u8054\u8d5b",
    "jc_bucket": "\u7ade\u5f69\u7a33\u5b9a\u6876",
}
ADMISSION_DECISION_LABELS = {
    "allow": "\u6b63\u5f0f\u653e\u884c",
    "observe": "\u89c2\u5bdf",
    "block": "\u963b\u65ad",
}
ADMISSION_FILTER_LABELS = {
    "all": "\u5168\u90e8",
    "allow": "\u6b63\u5f0f\u653e\u884c",
    "observe": "\u89c2\u5bdf",
    "block": "\u963b\u65ad",
}
ADMISSION_ACTION_LABELS = {
    "FORMAL_ALLOW": "\u6b63\u5f0f\u653e\u884c",
    "OBSERVE_ONLY": "\u4ec5\u89c2\u5bdf",
    "BLOCK": "\u963b\u65ad",
    "allow": "\u6b63\u5f0f\u653e\u884c",
    "release": "\u6b63\u5f0f\u653e\u884c",
    "observe": "\u4ec5\u89c2\u5bdf",
    "block": "\u963b\u65ad",
}
ADMISSION_REASON_LABELS = {
    "strategy_not_calibrated": "\u9ad8\u51c6\u7b56\u7565\u5c1a\u672a\u6821\u51c6",
    "high_accuracy_strategy_active": "\u547d\u4e2d\u6b63\u5f0f\u9ad8\u51c6\u7b56\u7565",
    "high_accuracy_strategy_count_below_policy": "\u9ad8\u51c6\u7b56\u7565\u6570\u91cf\u4f4e\u4e8e\u5f53\u524d\u51c6\u5165\u95e8\u69db",
    "no_official_high_accuracy_strategy": "\u672a\u547d\u4e2d\u6b63\u5f0f\u9ad8\u51c6\u7b56\u7565",
    "breaker_shadow_observation": "\u65ad\u8def\u89c2\u5bdf\u7b56\u7565\u547d\u4e2d\uff0c\u4ecd\u9700\u590d\u6838",
    "risk_high": "\u98ce\u9669\u7b49\u7ea7\u4e3a\u9ad8\u98ce\u9669",
    "risk_medium": "\u98ce\u9669\u7b49\u7ea7\u4e3a\u4e2d\u98ce\u9669",
    "risk_medium_policy_watch": "\u5f53\u524d\u95e8\u69db\u5c06\u4e2d\u98ce\u9669\u964d\u4e3a\u89c2\u5bdf",
    "risk_low": "\u98ce\u9669\u7b49\u7ea7\u4e3a\u4f4e\u98ce\u9669",
    "confidence_block": "\u7f6e\u4fe1\u5ea6\u4f4e\u4e8e\u963b\u65ad\u7ebf",
    "confidence_watch": "\u7f6e\u4fe1\u5ea6\u4f4e\u4e8e\u6b63\u5f0f\u653e\u884c\u7ebf",
    "no_single_play_passed": "\u6682\u65e0\u5355\u73a9\u6cd5\u901a\u8fc7\u95e8\u69db",
    "agent_replay_policy_watch": "Agent Replay \u663e\u793a\u5f53\u524d\u98ce\u9669\u4fe1\u53f7\u4e0e\u5386\u53f2\u5931\u8bef\u5f3a\u76f8\u5173",
}
PRE_MATCH_REVIEW_CHECKLIST = (
    "\u786e\u8ba4\u9996\u53d1\u3001\u4f24\u505c\u3001\u8f6e\u6362\u4e0e\u4e34\u573a\u540d\u5355\u6ca1\u6709\u53cd\u5411\u53d8\u5316\u3002",
    "\u786e\u8ba4\u76d8\u53e3/\u8d54\u7387\u4e34\u573a\u65b9\u5411\u6ca1\u6709\u6301\u7eed\u80cc\u79bb\u6a21\u578b\u65b9\u5411\u3002",
    "\u786e\u8ba4\u98ce\u9669\u7b49\u7ea7\u3001\u7f6e\u4fe1\u5ea6\u3001\u7b56\u7565\u51c6\u5165\u4ecd\u7ef4\u6301\u6b63\u5f0f\u653e\u884c\u3002",
    "\u786e\u8ba4\u9ad8\u51c6\u7b56\u7565\u672a\u88ab\u65ad\u8def\u5668\u6682\u505c\uff0c\u5f71\u5b50\u6062\u590d\u672a\u88ab\u8bef\u5f53\u6b63\u5f0f\u653e\u884c\u3002",
    "\u786e\u8ba4\u8d5b\u524d\u9884\u6d4b\u5feb\u7167\u5df2\u7ecf\u4fdd\u5b58\uff0c\u8d5b\u540e\u53ef\u56de\u6536\u8d5b\u679c\u3002",
    "\u8d5b\u540e\u5f55\u5165\u6bd4\u5206\u5e76\u8fdb\u5165\u590d\u76d8\uff0c\u66f4\u65b0\u771f\u5b9e\u547d\u4e2d\u53cd\u9988\u3002",
)


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "y"}:
        return True
    if text in {"0", "false", "no", "off", "n"}:
        return False
    return default


def _pct(value: object, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}%}"
    except (TypeError, ValueError):
        return "-"


def _label(labels: Mapping[str, str], value: object) -> str:
    key = str(value or "").strip()
    return labels.get(key, key or "-")


def _field(value: object, name: str, default: object = "-") -> object:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _row_match(row: object) -> object:
    return _field(row, "match", {})


def _row_prediction(row: object) -> Mapping[str, object]:
    return _as_mapping(_field(row, "prediction", {}))


def _strategy_admission(prediction: Mapping[str, object]) -> Mapping[str, object]:
    return _as_mapping(prediction.get("strategy_admission"))


def _row_match_id(match: object) -> str:
    direct = _text(_field(match, "match_id", ""), "")
    if direct:
        return direct
    return "|".join(
        [
            _text(_field(match, "match_date"), ""),
            _text(_field(match, "league"), ""),
            _text(_field(match, "home_team"), ""),
            _text(_field(match, "away_team"), ""),
        ]
    ).strip("|")


def _settlement_match_id(item: Mapping[str, object]) -> str:
    direct = _text(item.get("match_id"), "")
    if direct:
        return direct
    return "|".join(
        [
            _text(item.get("match_date"), ""),
            _text(item.get("league"), ""),
            _text(item.get("home_team"), ""),
            _text(item.get("away_team"), ""),
        ]
    ).strip("|")


def _allowlist_marker(prediction: Mapping[str, object], snapshot: Mapping[str, object]) -> Mapping[str, object]:
    marker = _as_mapping(prediction.get("strategy_allowlist"))
    if marker:
        return marker
    marker = _as_mapping(snapshot.get("strategy_allowlist"))
    if marker:
        return marker
    snapshot_prediction = _as_mapping(snapshot.get("prediction"))
    return _as_mapping(snapshot_prediction.get("strategy_allowlist"))


def _admission_decision(admission: Mapping[str, object]) -> str:
    decision = str(admission.get("decision") or "").strip()
    return decision if decision in {"allow", "observe", "block"} else "observe"


def _text(value: object, default: str = "-") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _md_cell(value: object) -> str:
    return _text(value).replace("|", "/").replace("\n", " ")


def _risk_text(value: object) -> str:
    text = _text(value, "")
    upper = text.upper()
    if "HIGH" in upper or "\u9ad8" in text:
        return "\u9ad8\u98ce\u9669"
    if "MEDIUM" in upper or "\u4e2d" in text:
        return "\u4e2d\u98ce\u9669"
    if "LOW" in upper or "\u4f4e" in text:
        return "\u4f4e\u98ce\u9669"
    return text or "-"


def _admission_label(admission: Mapping[str, object]) -> str:
    decision = str(admission.get("decision") or "").strip()
    return _text(admission.get("label") or ADMISSION_DECISION_LABELS.get(decision))


def _admission_reason_label(value: object) -> str:
    key = _text(value, "")
    return ADMISSION_REASON_LABELS.get(key, key)


def _admission_reasons(admission: Mapping[str, object], *, limit: int = 6) -> str:
    reasons = admission.get("reasons", [])
    if not isinstance(reasons, list) or not reasons:
        return "-"
    try:
        count = max(0, int(limit))
    except (TypeError, ValueError):
        count = 6
    items = [_admission_reason_label(item) for item in reasons[:count]]
    return "\uff1b".join(item for item in items if item) or "-"


def format_strategy_admission_label(admission: Mapping[str, object] | object) -> str:
    return _admission_label(_as_mapping(admission))


def format_strategy_admission_action(admission: Mapping[str, object] | object) -> str:
    resolved = _as_mapping(admission)
    action = _text(resolved.get("action"), "")
    return ADMISSION_ACTION_LABELS.get(action, action or "-")


def format_strategy_admission_reasons(admission: Mapping[str, object] | object, *, limit: int = 6) -> str:
    return _admission_reasons(_as_mapping(admission), limit=limit)


def format_strategy_admission_pick(admission: Mapping[str, object] | object) -> str:
    resolved = _as_mapping(admission)
    play = _label(PLAY_LABELS, resolved.get("top_play"))
    pick = _text(resolved.get("top_pick"))
    confidence = _pct(resolved.get("top_confidence"))
    if play == "-" and pick == "-":
        return "-"
    return f"{play} {pick} / {confidence}"


def format_strategy_admission_thresholds(admission: Mapping[str, object] | object) -> str:
    resolved = _as_mapping(admission)
    if not resolved:
        return "-"
    active_count = _safe_int(resolved.get("active_count"))
    active_min = max(1, _safe_int(resolved.get("active_strategy_min"), 1))
    medium_policy = "\u5141\u8bb8" if _safe_bool(resolved.get("medium_risk_allowed"), True) else "\u89c2\u5bdf"
    high_policy = "\u5141\u8bb8" if _safe_bool(resolved.get("high_risk_allowed"), False) else "\u963b\u65ad"
    return (
        f"\u7f6e\u4fe1 {_pct(resolved.get('confidence'))} / "
        f"\u653e\u884c\u7ebf {_pct(resolved.get('min_confidence'))} / "
        f"\u963b\u65ad\u7ebf {_pct(resolved.get('block_confidence'))}\uff1b"
        f"\u9ad8\u51c6 {active_count}/{active_min}\uff1b"
        f"\u4e2d\u98ce\u9669{medium_policy}\uff1b\u9ad8\u98ce\u9669{high_policy}"
    )


def format_strategy_admission_replay_guard(admission: Mapping[str, object] | object) -> str:
    resolved = _as_mapping(admission)
    guard = _as_mapping(resolved.get("agent_replay_guard"))
    if not guard:
        return "-"
    if not _safe_bool(guard.get("applied")):
        agent_names = guard.get("agent_names") if isinstance(guard.get("agent_names"), list) else []
        if not agent_names:
            return "-"
        return f"未触发降级 | 当前Agent: {', '.join(str(item) for item in agent_names)}"
    top_agent = _text(guard.get("top_agent"))
    prediction_rate = guard.get("top_prediction_miss_rate")
    handicap_rate = guard.get("top_handicap_miss_rate")
    parts = [f"触发观察降级 | Agent {top_agent}"]
    if prediction_rate is not None:
        parts.append(f"胜平负历史失误 {_pct(prediction_rate)}")
    if handicap_rate is not None:
        parts.append(f"让球历史失误 {_pct(handicap_rate)}")
    actions = guard.get("actions") if isinstance(guard.get("actions"), list) else []
    if actions:
        parts.append(f"动作 {', '.join(str(item) for item in actions[:3])}")
    return "；".join(parts)


def compute_strategy_admission_counts(rows: Sequence[object] | object) -> dict[str, int]:
    counts = {"all": 0, "allow": 0, "observe": 0, "block": 0}
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return counts
    for row in rows:
        prediction = _row_prediction(row)
        if not prediction:
            continue
        counts["all"] += 1
        counts[_admission_decision(_strategy_admission(prediction))] += 1
    return counts


def filter_strategy_admission_rows(rows: Sequence[object] | object, selected_filter: object = "all") -> list[object]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return []
    selected = str(selected_filter or "all").strip()
    if selected not in ADMISSION_FILTER_LABELS:
        selected = next((key for key, label in ADMISSION_FILTER_LABELS.items() if label == selected), "all")
    if selected == "all":
        return list(rows)
    return [
        row
        for row in rows
        if _admission_decision(_strategy_admission(_row_prediction(row))) == selected
    ]


def build_strategy_release_pool_rows(
    rows: Sequence[object] | object,
    *,
    snapshots: Mapping[str, object] | object = None,
    settlements: Sequence[Mapping[str, object]] | object = None,
) -> list[dict[str, object]]:
    snapshot_map = snapshots if isinstance(snapshots, Mapping) else {}
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    settled_ids = {_settlement_match_id(item) for item in settlement_items if _settlement_match_id(item)}
    pool: list[dict[str, object]] = []
    for row in select_strategy_allowlist_rows(rows):
        match = _row_match(row)
        prediction = _row_prediction(row)
        admission = _strategy_admission(prediction)
        match_id = _row_match_id(match)
        snapshot = _as_mapping(snapshot_map.get(match_id)) if match_id else {}
        marker = _allowlist_marker(prediction, snapshot)
        exported = bool(_text(marker.get("file"), ""))
        snapshot_saved = bool(snapshot)
        settled = bool(match_id and match_id in settled_ids)
        pool.append(
            {
                "match_id": match_id,
                "match": match,
                "prediction": prediction,
                "admission": admission,
                "title": f"{_text(_field(match, 'league'))} | {_text(_field(match, 'home_team'))} vs {_text(_field(match, 'away_team'))}",
                "kickoff": f"{_text(_field(match, 'match_date'))} {_text(_field(match, 'match_time'))}",
                "recommendation": _text(prediction.get("recommendation")),
                "confidence_text": _pct(prediction.get("confidence")),
                "risk_text": _risk_text(prediction.get("risk_level")),
                "candidate_text": format_strategy_admission_pick(marker if marker else admission),
                "reason_text": format_strategy_admission_reasons(marker if marker else admission, limit=4),
                "export_status": "\u5df2\u5bfc\u51fa" if exported else "\u672a\u5bfc\u51fa",
                "allowlist_file": _text(marker.get("file")),
                "exported_at": _text(marker.get("exported_at")),
                "snapshot_status": "\u5df2\u4fdd\u5b58" if snapshot_saved else "\u7f3a\u5feb\u7167",
                "settlement_status": "\u5df2\u56de\u6536" if settled else "\u5f85\u56de\u6536",
                "ready_for_recovery": bool(snapshot_saved and not settled),
            }
        )
    return pool


def build_strategy_release_recovery_alerts(snapshot_rows: Sequence[Mapping[str, object]] | object, *, limit: int = 5) -> dict[str, object]:
    if not isinstance(snapshot_rows, Sequence) or isinstance(snapshot_rows, (str, bytes)):
        return {"count": 0, "rows": [], "summary": "\u6682\u65e0\u6b63\u5f0f\u653e\u884c\u5f85\u56de\u6536\u63d0\u9192"}
    alerts: list[dict[str, str]] = []
    for item in snapshot_rows:
        if not isinstance(item, Mapping):
            continue
        allowlist = _as_mapping(item.get("strategy_allowlist"))
        if not allowlist:
            continue
        if _text(item.get("status")) != "\u5f85\u56de\u6536":
            continue
        match = _as_mapping(item.get("match"))
        prediction = _as_mapping(item.get("prediction"))
        title = (
            f"\u5f85\u56de\u6536 | {_text(match.get('league'))} | "
            f"{_text(match.get('home_team'))} vs {_text(match.get('away_team'))}"
        )
        body = (
            f"\u5f00\u8d5b: {_text(match.get('match_date'))} {_text(match.get('match_time'))}\n"
            f"\u63a8\u8350: {_text(prediction.get('recommendation'))} | \u7f6e\u4fe1 {_pct(prediction.get('confidence'))} | \u98ce\u9669 {_risk_text(prediction.get('risk_level'))}\n"
            f"\u6e05\u5355: {_text(allowlist.get('file'))} | \u5bfc\u51fa\u65f6\u95f4: {_text(allowlist.get('exported_at'))}\n"
            f"\u5019\u9009: {format_strategy_admission_pick(allowlist)}"
        )
        alerts.append({"title": title, "body": body})
    try:
        max_rows = max(0, int(limit))
    except (TypeError, ValueError):
        max_rows = 5
    count = len(alerts)
    return {
        "count": count,
        "rows": alerts[:max_rows],
        "summary": f"\u6709 {count} \u573a\u6b63\u5f0f\u653e\u884c\u5df2\u8fdb\u5165\u5f85\u56de\u6536" if count else "\u6682\u65e0\u6b63\u5f0f\u653e\u884c\u5f85\u56de\u6536\u63d0\u9192",
    }


def _allowlist_sort_key(row: object) -> tuple[str, str, str, str, float]:
    match = _row_match(row)
    prediction = _row_prediction(row)
    return (
        _text(_field(match, "match_date")),
        _text(_field(match, "match_time")),
        _text(_field(match, "league")),
        _text(_field(match, "home_team")),
        -_safe_float(prediction.get("confidence")),
    )


def _strategy_pool(status: Mapping[str, object]) -> list[Mapping[str, object]]:
    return [item for item in _as_list(status.get("strategy_pool")) if isinstance(item, Mapping)]


def _strategy_layer(item: Mapping[str, object]) -> Mapping[str, object]:
    return _as_mapping(item.get("layer"))


def _strategy_stability(item: Mapping[str, object]) -> Mapping[str, object]:
    return _as_mapping(item.get("stability"))


def _known_strategy_settlement_items(settlements: Sequence[Mapping[str, object]]) -> list[tuple[Mapping[str, object], Mapping[str, object]]]:
    rows: list[tuple[Mapping[str, object], Mapping[str, object]]] = []
    for settlement in settlements:
        if not isinstance(settlement, Mapping):
            continue
        for item in _as_list(settlement.get("high_accuracy_strategy_items")):
            if isinstance(item, Mapping):
                rows.append((settlement, item))
    return rows


def build_high_accuracy_strategy_settlement_summary(settlements: Sequence[Mapping[str, object]]) -> dict[str, object]:
    rows = _known_strategy_settlement_items(settlements)
    known = [item for _settlement, item in rows if item.get("is_hit") is not None]
    official = [item for item in known if not bool(item.get("is_shadow"))]
    shadow = [item for item in known if bool(item.get("is_shadow"))]
    hits = sum(1 for item in known if item.get("is_hit") is True)
    misses = sum(1 for item in known if item.get("is_hit") is False)
    unknown = len(rows) - len(known)
    hit_rate = hits / len(known) if known else None
    official_hits = sum(1 for item in official if item.get("is_hit") is True)
    shadow_hits = sum(1 for item in shadow if item.get("is_hit") is True)
    return {
        "active_count": len(rows),
        "official_count": len(official),
        "official_hit_count": official_hits,
        "shadow_count": len(shadow),
        "shadow_hit_count": shadow_hits,
        "known_count": len(known),
        "hit_count": hits,
        "miss_count": misses,
        "unknown_count": unknown,
        "hit_rate": hit_rate,
        "hit_rate_text": _pct(hit_rate) if hit_rate is not None else "-",
        "summary_text": f"{hits}/{len(known)}" if known else "-",
        "official_summary_text": f"{official_hits}/{len(official)}" if official else "-",
        "shadow_summary_text": f"{shadow_hits}/{len(shadow)}" if shadow else "-",
    }


ERROR_ATTRIBUTION_LABELS = {
    "data_missing": "\u6570\u636e\u7f3a\u5931",
    "high_confidence_miss": "\u9ad8\u7f6e\u4fe1\u5931\u8bef",
    "historical_gap": "\u5386\u53f2\u56de\u6d4b\u4e0e\u5b9e\u76d8\u80cc\u79bb",
    "jc_wilson_breach": "JC\u8dcc\u7834Wilson",
    "jc_odds_drift": "JC\u8d54\u7387\u6f02\u79fb",
    "jc_confidence_drift": "JC\u7f6e\u4fe1\u6f02\u79fb",
    "jc_live_downgraded": "JC\u7a33\u5b9a\u6876\u964d\u7ea7",
    "statsbomb_xg_against_pick": "StatsBomb xG\u53cd\u5411",
    "statsbomb_finishing_variance": "StatsBomb\u7ec8\u7ed3\u504f\u5dee",
    "statsbomb_event_control_gap": "StatsBomb\u573a\u9762\u52a3\u52bf",
    "small_sample": "\u6837\u672c\u4e0d\u8db3",
    "shadow_observation": "\u89c2\u5bdf\u7b56\u7565\u5931\u8bef",
    "unknown": "\u672a\u5b9a\u4e49\u9519\u56e0",
}


def _pick_side(value: object) -> str:
    text = _text(value, "").upper()
    if text in {"HOME", "HOME_WIN", "H", "1"} or "HOME" in text:
        return "home"
    if text in {"AWAY", "AWAY_WIN", "A", "2"} or "AWAY" in text:
        return "away"
    if "\u4e3b" in text:
        return "home"
    if "\u5ba2" in text:
        return "away"
    return ""


def _actual_side(value: object) -> str:
    text = _text(value, "").upper()
    if text in {"HOME", "HOME_WIN", "H", "1"} or "HOME" in text:
        return "home"
    if text in {"AWAY", "AWAY_WIN", "A", "2"} or "AWAY" in text:
        return "away"
    if text in {"DRAW", "D", "X"} or "DRAW" in text:
        return "draw"
    if "\u4e3b" in text:
        return "home"
    if "\u5ba2" in text:
        return "away"
    if "\u5e73" in text:
        return "draw"
    return ""


def _statsbomb_team_stats(settlement: Mapping[str, object]) -> tuple[Mapping[str, object], Mapping[str, object], str, str]:
    summary = _as_mapping(settlement.get("statsbomb_event_summary"))
    team_stats = _as_mapping(summary.get("team_stats"))
    home = _text(settlement.get("home_team"), "")
    away = _text(settlement.get("away_team"), "")
    home_stats = _as_mapping(team_stats.get(home))
    away_stats = _as_mapping(team_stats.get(away))
    if (not home_stats or not away_stats) and len(team_stats) >= 2:
        names = list(team_stats.keys())
        if not home_stats:
            home = _text(names[0], home)
            home_stats = _as_mapping(team_stats.get(names[0]))
        if not away_stats:
            away = _text(names[1], away)
            away_stats = _as_mapping(team_stats.get(names[1]))
    return home_stats, away_stats, home, away


def _statsbomb_event_evidence(settlement: Mapping[str, object], item: Mapping[str, object]) -> dict[str, object]:
    home_stats, away_stats, home, away = _statsbomb_team_stats(settlement)
    if not home_stats or not away_stats:
        return {"codes": [], "body": "", "available": False}
    home_xg = _safe_float(home_stats.get("xg"))
    away_xg = _safe_float(away_stats.get("xg"))
    home_shots = _safe_int(home_stats.get("shots"))
    away_shots = _safe_int(away_stats.get("shots"))
    home_goals = _safe_int(home_stats.get("goals"), _safe_int(settlement.get("home_goals")))
    away_goals = _safe_int(away_stats.get("goals"), _safe_int(settlement.get("away_goals")))
    pick_side = _pick_side(item.get("pick"))
    actual_side = _actual_side(item.get("actual"))
    codes: list[str] = []
    if item.get("is_hit") is False and pick_side in {"home", "away"}:
        picked_xg = home_xg if pick_side == "home" else away_xg
        opponent_xg = away_xg if pick_side == "home" else home_xg
        picked_shots = home_shots if pick_side == "home" else away_shots
        opponent_shots = away_shots if pick_side == "home" else home_shots
        if picked_xg + 0.25 < opponent_xg:
            codes.append("statsbomb_xg_against_pick")
        if picked_xg >= opponent_xg + 0.35 and actual_side and actual_side != pick_side:
            codes.append("statsbomb_finishing_variance")
        if picked_xg + 0.15 < opponent_xg and picked_shots + 4 <= opponent_shots:
            codes.append("statsbomb_event_control_gap")
    body = (
        f"StatsBomb: xG {home} {home_xg:.2f} - {away_xg:.2f} {away} | "
        f"\u5c04\u95e8 {home_shots}-{away_shots} | \u8fdb\u7403 {home_goals}-{away_goals}"
    )
    return {"codes": codes, "body": body, "available": True}


def _side_from_margin(value: float, *, threshold: float = 0.0) -> str:
    if value > threshold:
        return "home"
    if value < -threshold:
        return "away"
    return "draw"


def _pct_text_to_float(value: object) -> float | None:
    text = str(value or "").strip()
    if not text or text == "-":
        return None
    if text.endswith("%"):
        text = text[:-1]
        try:
            return float(text) / 100.0
        except (TypeError, ValueError):
            return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return number


def _statsbomb_baseline_summary(baseline: Mapping[str, object] | object) -> Mapping[str, object]:
    resolved = _as_mapping(baseline)
    return _as_mapping(resolved.get("summary"))


def build_statsbomb_event_review_summary(
    settlements: Sequence[Mapping[str, object]] | object,
    baseline: Mapping[str, object] | object | None = None,
    *,
    limit: int = 8,
) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    rows: list[dict[str, object]] = []
    xg_aligned = 0
    shot_aligned = 0
    finishing_variance = 0
    control_gap = 0
    xg_totals: list[float] = []
    event_counts: list[int] = []

    for settlement in settlement_items:
        home_stats, away_stats, home, away = _statsbomb_team_stats(settlement)
        if not home_stats or not away_stats:
            continue
        home_goals = _safe_int(home_stats.get("goals"), _safe_int(settlement.get("home_goals")))
        away_goals = _safe_int(away_stats.get("goals"), _safe_int(settlement.get("away_goals")))
        home_xg = _safe_float(home_stats.get("xg"))
        away_xg = _safe_float(away_stats.get("xg"))
        home_shots = _safe_int(home_stats.get("shots"))
        away_shots = _safe_int(away_stats.get("shots"))
        summary = _as_mapping(settlement.get("statsbomb_event_summary"))
        event_count = _safe_int(summary.get("event_count"))
        score_winner = _side_from_margin(float(home_goals - away_goals))
        xg_winner = _side_from_margin(home_xg - away_xg, threshold=0.25)
        shot_winner = _side_from_margin(float(home_shots - away_shots), threshold=2.0)
        xg_ok = xg_winner == score_winner
        shot_ok = shot_winner == score_winner
        variance = xg_winner != "draw" and xg_winner != score_winner
        gap = abs(home_xg - away_xg) >= 0.35 and abs(home_shots - away_shots) >= 4
        xg_aligned += 1 if xg_ok else 0
        shot_aligned += 1 if shot_ok else 0
        finishing_variance += 1 if variance else 0
        control_gap += 1 if gap else 0
        xg_totals.append(home_xg + away_xg)
        event_counts.append(event_count)
        diagnosis: list[str] = []
        if variance:
            diagnosis.append("\u7ec8\u7ed3\u6ce2\u52a8")
        if gap and not xg_ok:
            diagnosis.append("\u573a\u9762\u4e0e\u8d5b\u679c\u80cc\u79bb")
        if xg_ok and shot_ok:
            diagnosis.append("\u4e8b\u4ef6\u652f\u6301\u8d5b\u679c")
        if not diagnosis:
            diagnosis.append("\u5747\u52bf\u6216\u4f4e\u5dee\u5f02")
        diagnosis_text = "\u3001".join(diagnosis)
        rows.append(
            {
                "title": f"{settlement.get('league') or '-'} | {home or '-'} vs {away or '-'}",
                "body": (
                    f"xG {home or '-'} {home_xg:.2f} - {away_xg:.2f} {away or '-'} | "
                    f"\u5c04\u95e8 {home_shots}-{away_shots} | \u6bd4\u5206 {home_goals}-{away_goals}\n"
                    f"\u5224\u5b9a: {diagnosis_text} | \u4e8b\u4ef6 {event_count}"
                ),
                "xg_aligned": xg_ok,
                "shot_aligned": shot_ok,
                "finishing_variance": variance,
                "control_gap": gap,
                "xg_margin": round(home_xg - away_xg, 4),
                "event_count": event_count,
            }
        )

    sample_count = len(rows)
    baseline_summary = _statsbomb_baseline_summary(baseline or {})
    baseline_match_count = _safe_int(baseline_summary.get("match_count"))
    baseline_xg_alignment = baseline_summary.get("xg_alignment_rate") or "-"
    baseline_variance = baseline_summary.get("finishing_variance_rate") or "-"
    xg_alignment_rate = xg_aligned / sample_count if sample_count else None
    variance_rate = finishing_variance / sample_count if sample_count else None
    baseline_variance_value = _pct_text_to_float(baseline_variance)
    status = "no_event_data"
    if sample_count:
        status = "review_ready"
        if baseline_variance_value is not None and variance_rate is not None and variance_rate > baseline_variance_value + 0.08:
            status = "variance_watch"
        elif control_gap:
            status = "control_gap_watch"
    rows.sort(
        key=lambda row: (
            not bool(row.get("finishing_variance")),
            not bool(row.get("control_gap")),
            -abs(_safe_float(row.get("xg_margin"))),
            str(row.get("title") or ""),
        )
    )
    return {
        "status": status,
        "sample_count": sample_count,
        "xg_aligned": xg_aligned,
        "xg_alignment_rate": xg_alignment_rate,
        "xg_alignment_rate_text": _pct(xg_alignment_rate) if xg_alignment_rate is not None else "-",
        "shot_aligned": shot_aligned,
        "shot_alignment_rate_text": _pct(shot_aligned / sample_count) if sample_count else "-",
        "finishing_variance_count": finishing_variance,
        "finishing_variance_rate": variance_rate,
        "finishing_variance_rate_text": _pct(variance_rate) if variance_rate is not None else "-",
        "control_gap_count": control_gap,
        "avg_xg_total": round(sum(xg_totals) / sample_count, 4) if sample_count else 0.0,
        "avg_event_count": round(sum(event_counts) / sample_count, 2) if sample_count else 0.0,
        "baseline_match_count": baseline_match_count,
        "baseline_xg_alignment_rate": baseline_xg_alignment,
        "baseline_finishing_variance_rate": baseline_variance,
        "leakage_note": "\u8be5\u6a21\u5757\u4ec5\u7528\u4e8e\u8d5b\u540e\u590d\u76d8\uff0c\u4e0d\u53c2\u4e0e\u8d5b\u524d\u9884\u6d4b\u8f93\u5165\u3002",
        "rows": rows[: max(0, int(limit))],
        "summary_text": (
            f"\u6837\u672c {sample_count} | xG\u5bf9\u9f50 {(_pct(xg_alignment_rate) if xg_alignment_rate is not None else '-')} | "
            f"\u7ec8\u7ed3\u6ce2\u52a8 {finishing_variance} | \u57fa\u7ebf {baseline_match_count}\u573a"
        ),
    }


def _statsbomb_memory_items(memory: Mapping[str, object] | object) -> list[Mapping[str, object]]:
    payload = _as_mapping(memory)
    items = _as_list(payload.get("items"))
    return [item for item in items if isinstance(item, Mapping)]


def _statsbomb_memory_query_tags(
    error_attribution: Mapping[str, object] | object,
    event_review: Mapping[str, object] | object,
) -> list[str]:
    attribution = _as_mapping(error_attribution)
    reason_counts = _as_mapping(attribution.get("reason_counts"))
    review = _as_mapping(event_review)
    has_statsbomb_signal = (
        _safe_int(review.get("sample_count")) > 0
        or _safe_int(reason_counts.get("statsbomb_finishing_variance")) > 0
        or _safe_int(reason_counts.get("statsbomb_event_control_gap")) > 0
        or _safe_int(reason_counts.get("statsbomb_xg_against_pick")) > 0
    )
    if not has_statsbomb_signal:
        return []
    tags: list[str] = ["statsbomb_post_match_review"]
    if _safe_int(reason_counts.get("statsbomb_finishing_variance")) or _safe_int(review.get("finishing_variance_count")):
        tags.extend(["statsbomb_finishing_variance", "xg_result_divergence"])
    if _safe_int(reason_counts.get("statsbomb_event_control_gap")) or _safe_int(review.get("control_gap_count")):
        tags.append("event_control_gap")
    if _safe_int(reason_counts.get("statsbomb_xg_against_pick")):
        tags.append("xg_direction_failed")
    if _safe_int(attribution.get("miss_count")):
        tags.append("strategy_miss")
    deduped: list[str] = []
    for tag in tags:
        if tag not in deduped:
            deduped.append(tag)
    return deduped


def build_statsbomb_fewshot_memory_summary(
    error_attribution: Mapping[str, object] | object,
    event_review: Mapping[str, object] | object,
    memory: Mapping[str, object] | object | None = None,
    *,
    limit: int = 3,
) -> dict[str, object]:
    items = _statsbomb_memory_items(memory or {})
    query_tags = _statsbomb_memory_query_tags(error_attribution, event_review)
    rows: list[dict[str, object]] = []
    for item in items:
        labels = _as_mapping(item.get("labels"))
        tags = [str(tag) for tag in _as_list(labels.get("tags"))]
        matched = [tag for tag in query_tags if tag in tags]
        if not matched:
            continue
        features = _as_mapping(item.get("features"))
        meta = _as_mapping(item.get("meta"))
        score = len(matched) * 10
        if labels.get("is_hit") is False and "strategy_miss" in query_tags:
            score += 4
        if "statsbomb_finishing_variance" in matched:
            score += 3
        if "event_control_gap" in matched:
            score += 2
        rows.append(
            {
                "id": item.get("id") or "-",
                "score": score,
                "matched_tags": matched,
                "title": f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}",
                "body": (
                    f"{labels.get('simulated_pick') or '-'} -> {labels.get('actual') or '-'} | "
                    f"{'命中' if labels.get('is_hit') is True else '未命中'} | "
                    f"{labels.get('root_cause') or '-'} | xG差 {float(_safe_float(features.get('xg_margin'), 0.0) or 0.0):+.2f}"
                ),
                "completion": item.get("completion") or "-",
                "tags": tags,
            }
        )
    rows.sort(key=lambda row: (-_safe_int(row.get("score")), str(row.get("title") or "")))
    limited = rows[: max(0, int(limit))]
    memory_summary = _as_mapping(_as_mapping(memory or {}).get("summary"))
    return {
        "status": "ready" if items else "missing",
        "sample_count": len(items),
        "matched_count": len(rows),
        "query_tags": query_tags,
        "baseline_match_count": _safe_int(memory_summary.get("baseline_match_count")),
        "rows": limited,
        "summary_text": f"记忆库 {len(items)} | 命中 {len(rows)} | 标签 {', '.join(query_tags[:4])}",
        "leakage_note": _as_mapping(memory or {}).get("leakage_note")
        or "These few-shot samples use post-match event data and must not be used as pre-match prediction features.",
    }


def build_statsbomb_fewshot_memory_monitor(
    memory: Mapping[str, object] | object | None = None,
    current_memory_summary: Mapping[str, object] | object | None = None,
    *,
    required_tags: Sequence[str] | None = None,
    limit: int = 8,
) -> dict[str, object]:
    items = _statsbomb_memory_items(memory or {})
    current = _as_mapping(current_memory_summary)
    required = list(
        required_tags
        or (
            "statsbomb_finishing_variance",
            "event_control_gap",
            "xg_result_divergence",
            "shot_result_divergence",
            "xg_direction_failed",
            "strategy_miss",
            "strategy_hit",
        )
    )
    tag_counts: dict[str, int] = {}
    root_counts: dict[str, int] = {}
    miss_count = 0
    hit_count = 0
    for item in items:
        labels = _as_mapping(item.get("labels"))
        if labels.get("is_hit") is False:
            miss_count += 1
        elif labels.get("is_hit") is True:
            hit_count += 1
        root = str(labels.get("root_cause") or "").strip()
        if root:
            root_counts[root] = root_counts.get(root, 0) + 1
        for tag in [str(tag) for tag in _as_list(labels.get("tags"))]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    covered_tags = [tag for tag in required if _safe_int(tag_counts.get(tag)) > 0]
    missing_tags = [tag for tag in required if _safe_int(tag_counts.get(tag)) <= 0]
    coverage_rate = len(covered_tags) / len(required) if required else None
    tag_rows = [
        {
            "title": f"{tag} | {_safe_int(count)}",
            "body": f"标签 {tag} 覆盖 {_safe_int(count)} 个历史复盘样本。",
            "tag": tag,
            "count": _safe_int(count),
        }
        for tag, count in sorted(tag_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))
    ]
    root_rows = [
        {
            "title": f"{root} | {_safe_int(count)}",
            "body": f"根因 {root} 覆盖 {_safe_int(count)} 个历史复盘样本。",
            "root_cause": root,
            "count": _safe_int(count),
        }
        for root, count in sorted(root_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))
    ]
    matched_count = _safe_int(current.get("matched_count"))
    query_tags = [str(tag) for tag in _as_list(current.get("query_tags"))]
    status = "missing"
    if items:
        status = "active_match" if matched_count else "ready"
        if not query_tags:
            status = "standby"
    return {
        "status": status,
        "sample_count": len(items),
        "hit_count": hit_count,
        "miss_count": miss_count,
        "tag_count": len(tag_counts),
        "root_cause_count": len(root_counts),
        "covered_tags": covered_tags,
        "missing_tags": missing_tags,
        "coverage_rate": coverage_rate,
        "coverage_rate_text": _pct(coverage_rate) if coverage_rate is not None else "-",
        "current_matched_count": matched_count,
        "current_query_tags": query_tags,
        "tag_rows": tag_rows[: max(0, int(limit))],
        "root_rows": root_rows[: max(0, int(limit))],
        "summary_text": (
            f"样本 {len(items)} | 标签覆盖 {(_pct(coverage_rate) if coverage_rate is not None else '-')} | "
            f"当前命中 {matched_count} | 缺口 {len(missing_tags)}"
        ),
        "leakage_note": _as_mapping(memory or {}).get("leakage_note")
        or "These few-shot samples use post-match event data and must not be used as pre-match prediction features.",
    }


def build_statsbomb_fewshot_memory_quality_alerts(
    monitor: Mapping[str, object] | object | None = None,
    *,
    min_samples: int = 20,
    concentration_threshold: float = 0.65,
) -> dict[str, object]:
    data = _as_mapping(monitor)
    sample_count = _safe_int(data.get("sample_count"))
    current_matched_count = _safe_int(data.get("current_matched_count"))
    current_query_tags = [str(tag) for tag in _as_list(data.get("current_query_tags"))]
    missing_tags = [str(tag) for tag in _as_list(data.get("missing_tags"))]
    tag_rows = [_as_mapping(row) for row in _as_list(data.get("tag_rows"))]
    root_rows = [_as_mapping(row) for row in _as_list(data.get("root_rows"))]
    alerts: list[dict[str, str]] = []
    memory_tags: list[str] = []
    score_delta = 0

    if sample_count <= 0:
        alerts.append(
            {
                "title": "建立StatsBomb复盘记忆库",
                "body": "当前没有可用的赛后事件 few-shot 样本，Evaluation Agent 只能依赖规则归因，建议先沉淀已结束比赛的复盘样本。",
                "tag": "statsbomb_memory_missing",
            }
        )
        memory_tags.append("statsbomb_memory_missing")
        score_delta -= 4
    elif sample_count < max(1, int(min_samples)):
        alerts.append(
            {
                "title": "补充StatsBomb复盘样本",
                "body": f"当前 few-shot 记忆样本 {sample_count} 条，低于 {max(1, int(min_samples))} 条观察线，建议优先补充高置信失误和冷门场次。",
                "tag": "statsbomb_memory_low_sample",
            }
        )
        memory_tags.append("statsbomb_memory_low_sample")
        score_delta -= 3

    if sample_count > 0 and missing_tags:
        alerts.append(
            {
                "title": "补齐复盘标签缺口",
                "body": f"缺少 {', '.join(missing_tags[:5])} 等标签样本，后续复盘需要覆盖这些根因，避免 few-shot 记忆偏科。",
                "tag": "statsbomb_memory_tag_gap",
            }
        )
        memory_tags.append("statsbomb_memory_tag_gap")
        score_delta -= 2

    if sample_count > 0 and current_query_tags and current_matched_count <= 0:
        alerts.append(
            {
                "title": "补充当前错因相似样本",
                "body": f"当前复盘查询标签为 {', '.join(current_query_tags[:5])}，但历史记忆没有命中相似案例，建议赛后优先导出这一类 few-shot 样本。",
                "tag": "statsbomb_memory_no_current_match",
            }
        )
        memory_tags.append("statsbomb_memory_no_current_match")
        score_delta -= 3

    root_total = sum(_safe_int(row.get("count")) for row in root_rows)
    if sample_count >= 5 and root_total > 0 and root_rows:
        top_root = root_rows[0]
        top_root_count = _safe_int(top_root.get("count"))
        root_share = top_root_count / root_total if root_total else 0.0
        if root_share >= max(0.0, min(1.0, float(concentration_threshold))):
            alerts.append(
                {
                    "title": "降低复盘根因集中度",
                    "body": f"根因 {top_root.get('root_cause') or '-'} 占 few-shot 记忆 {root_share:.1%}，建议补充其他错因类型，避免 Evaluation Agent 过度套用单一解释。",
                    "tag": "statsbomb_memory_concentrated",
                }
            )
            memory_tags.append("statsbomb_memory_concentrated")
            score_delta -= 2

    diagnostic_tag_rows = [
        row
        for row in tag_rows
        if str(row.get("tag") or "") not in {"statsbomb_post_match_review", "strategy_miss", "strategy_hit"}
    ]
    tag_total = sum(_safe_int(row.get("count")) for row in diagnostic_tag_rows)
    if sample_count >= 5 and tag_total > 0 and diagnostic_tag_rows:
        top_tag = diagnostic_tag_rows[0]
        top_tag_count = _safe_int(top_tag.get("count"))
        tag_share = top_tag_count / tag_total if tag_total else 0.0
        if tag_share >= max(0.0, min(1.0, float(concentration_threshold))):
            alerts.append(
                {
                    "title": "降低复盘标签集中度",
                    "body": f"诊断标签 {top_tag.get('tag') or '-'} 占 few-shot 记忆 {tag_share:.1%}，建议补充场面劣势、xG 背离、命中案例等不同标签。",
                    "tag": "statsbomb_memory_tag_concentrated",
                }
            )
            memory_tags.append("statsbomb_memory_tag_concentrated")
            score_delta -= 2

    status = "watch" if alerts else "healthy"
    return {
        "status": status,
        "alert_count": len(alerts),
        "alerts": alerts[:5],
        "memory_tags": memory_tags,
        "score_delta": score_delta,
        "summary_text": f"记忆告警 {len(alerts)} | 样本 {sample_count} | 当前命中 {current_matched_count}",
    }


def _statsbomb_required_backfill_tags(monitor: Mapping[str, object]) -> list[str]:
    tags: list[str] = []
    for source in (monitor.get("current_query_tags"), monitor.get("missing_tags")):
        for tag in _as_list(source):
            tag_text = str(tag).strip()
            if tag_text and tag_text not in tags:
                tags.append(tag_text)
    if not tags:
        tags.extend(
            [
                "strategy_miss",
                "strategy_hit",
                "statsbomb_finishing_variance",
                "event_control_gap",
                "xg_direction_failed",
            ]
        )
    return tags


def _statsbomb_backfill_task_title(tag: str) -> str:
    labels = {
        "strategy_miss": "补充未命中复盘样本",
        "strategy_hit": "补充命中对照样本",
        "statsbomb_finishing_variance": "补充终结波动样本",
        "event_control_gap": "补充场面劣势样本",
        "xg_result_divergence": "补充xG与赛果背离样本",
        "shot_result_divergence": "补充射门与赛果背离样本",
        "xg_direction_failed": "补充xG方向失效样本",
    }
    return labels.get(tag, f"补充 {tag} 样本")


def _statsbomb_baseline_backfill_tags(row: Mapping[str, object]) -> list[str]:
    tags = ["statsbomb_post_match_review"]
    if bool(row.get("finishing_variance")):
        tags.extend(["statsbomb_finishing_variance", "xg_result_divergence"])
    if "xg_aligned_with_score" in row and not bool(row.get("xg_aligned_with_score")):
        tags.extend(["xg_result_divergence", "xg_direction_failed"])
    if "shot_aligned_with_score" in row and not bool(row.get("shot_aligned_with_score")):
        tags.append("shot_result_divergence")
    home_shots = _safe_int(row.get("home_shots"))
    away_shots = _safe_int(row.get("away_shots"))
    goal_margin = _safe_float(row.get("goal_margin"))
    shot_margin = home_shots - away_shots
    if (goal_margin > 0 and shot_margin < -3) or (goal_margin < 0 and shot_margin > 3):
        tags.append("event_control_gap")
    if "xg_aligned_with_score" in row and bool(row.get("xg_aligned_with_score")):
        tags.append("strategy_hit")
    else:
        tags.append("strategy_miss")
    deduped: list[str] = []
    for tag in tags:
        if tag not in deduped:
            deduped.append(tag)
    return deduped


def _statsbomb_settlement_backfill_row(
    settlement: Mapping[str, object],
    tags: Sequence[str],
    *,
    source: str,
    priority_base: int = 0,
) -> dict[str, object]:
    title = f"{settlement.get('match_date') or '-'} | {settlement.get('league') or '-'} | {settlement.get('home_team') or '-'} vs {settlement.get('away_team') or '-'}"
    tag_list = [str(tag) for tag in tags if str(tag)]
    return {
        "source": source,
        "match_id": settlement.get("match_id") or "-",
        "match_date": settlement.get("match_date") or "-",
        "league": settlement.get("league") or "-",
        "title": title,
        "tags": tag_list,
        "priority_score": priority_base,
        "body": f"{title}\n标签: {', '.join(tag_list[:6]) if tag_list else '-'}",
    }


def build_statsbomb_fewshot_backfill_queue(
    monitor: Mapping[str, object] | object | None = None,
    quality: Mapping[str, object] | object | None = None,
    settlements: Sequence[Mapping[str, object]] | object | None = None,
    statsbomb_event_baseline: Mapping[str, object] | object | None = None,
    *,
    limit: int = 8,
) -> dict[str, object]:
    monitor_data = _as_mapping(monitor)
    quality_data = _as_mapping(quality)
    alert_rows = [_as_mapping(alert) for alert in _as_list(quality_data.get("alerts"))]
    required_tags = _statsbomb_required_backfill_tags(monitor_data)
    sample_count = _safe_int(monitor_data.get("sample_count"))
    missing_tags = [str(tag) for tag in _as_list(monitor_data.get("missing_tags"))]
    current_query_tags = [str(tag) for tag in _as_list(monitor_data.get("current_query_tags"))]
    tasks: list[dict[str, object]] = []

    if sample_count <= 0 or any(str(alert.get("tag") or "") == "statsbomb_memory_missing" for alert in alert_rows):
        tasks.append(
            {
                "task": "seed_memory",
                "priority": 100,
                "title": "建立StatsBomb few-shot种子库",
                "target_tags": required_tags,
                "body": "优先从已结束且带 StatsBomb 事件数据的比赛生成基础 few-shot 样本，命中和未命中样本都要覆盖。",
            }
        )
    if any(str(alert.get("tag") or "") == "statsbomb_memory_low_sample" for alert in alert_rows):
        tasks.append(
            {
                "task": "increase_sample_size",
                "priority": 90,
                "title": "扩大StatsBomb few-shot样本数",
                "target_tags": required_tags,
                "body": f"当前样本 {sample_count} 条，优先补充高置信失误、冷门和命中对照样本。",
            }
        )
    if missing_tags:
        for tag in missing_tags[:6]:
            tasks.append(
                {
                    "task": "cover_missing_tag",
                    "priority": 85,
                    "title": _statsbomb_backfill_task_title(tag),
                    "target_tags": [tag],
                    "body": f"记忆库缺少 {tag}，需要从赛后事件复盘中补齐这一类 few-shot 样本。",
                }
            )
    if current_query_tags and _safe_int(monitor_data.get("current_matched_count")) <= 0:
        tasks.append(
            {
                "task": "cover_current_context",
                "priority": 95,
                "title": "补充当前错因相似样本",
                "target_tags": current_query_tags,
                "body": f"当前查询标签 {', '.join(current_query_tags[:6])} 没有命中历史记忆，需要优先补充同类赛后案例。",
            }
        )
    if any(str(alert.get("tag") or "") in {"statsbomb_memory_concentrated", "statsbomb_memory_tag_concentrated"} for alert in alert_rows):
        tasks.append(
            {
                "task": "diversify_memory",
                "priority": 70,
                "title": "分散复盘记忆分布",
                "target_tags": required_tags,
                "body": "当前 few-shot 记忆集中在少数根因或标签，建议补充不同联赛、不同比分结构、不同事件形态的样本。",
            }
        )

    candidate_rows: list[dict[str, object]] = []
    for item in settlements if isinstance(settlements, Sequence) else []:
        if not isinstance(item, Mapping) or not _as_mapping(item.get("statsbomb_event_summary")):
            continue
        attribution = build_strategy_error_attribution_summary([item])
        event_review = build_statsbomb_event_review_summary([item], statsbomb_event_baseline or {})
        tags = _statsbomb_memory_query_tags(attribution, event_review)
        if tags:
            candidate_rows.append(_statsbomb_settlement_backfill_row(item, tags, source="recent_settlement", priority_base=20))

    baseline_items = [
        item
        for item in _as_list(_as_mapping(statsbomb_event_baseline).get("items"))
        if isinstance(item, Mapping)
    ]
    for item in baseline_items:
        tags = _statsbomb_baseline_backfill_tags(item)
        settlement = {
            "match_id": item.get("match_id"),
            "match_date": item.get("match_date"),
            "league": item.get("league"),
            "home_team": item.get("home_team"),
            "away_team": item.get("away_team"),
        }
        candidate_rows.append(_statsbomb_settlement_backfill_row(settlement, tags, source="statsbomb_baseline", priority_base=5))

    target_tag_set = {tag for task in tasks for tag in _as_list(task.get("target_tags"))}
    if not target_tag_set:
        target_tag_set = set(required_tags)
    scored_rows: list[dict[str, object]] = []
    for row in candidate_rows:
        row_tags = {str(tag) for tag in _as_list(row.get("tags"))}
        overlap = sorted(row_tags & target_tag_set)
        if tasks and not overlap:
            continue
        scored = dict(row)
        scored["matched_tags"] = overlap
        scored["priority_score"] = _safe_int(row.get("priority_score")) + len(overlap) * 12
        scored["body"] = f"{row.get('body', '-')}\n命中补样目标: {', '.join(overlap[:6]) if overlap else '-'}"
        scored_rows.append(scored)
    scored_rows.sort(key=lambda row: (-_safe_int(row.get("priority_score")), str(row.get("match_date") or ""), str(row.get("title") or "")))
    tasks.sort(key=lambda row: (-_safe_int(row.get("priority")), str(row.get("title") or "")))
    status = "ready" if tasks else "healthy"
    return {
        "status": status,
        "task_count": len(tasks),
        "candidate_count": len(scored_rows),
        "tasks": tasks[: max(0, int(limit))],
        "candidate_rows": scored_rows[: max(0, int(limit))],
        "summary_text": f"补样任务 {len(tasks)} | 候选 {len(scored_rows)} | 目标标签 {len(target_tag_set)}",
        "leakage_note": "Backfill queue uses post-match StatsBomb event evidence for review memory only; never feed it into pre-match prediction features.",
    }


def build_statsbomb_fewshot_backfill_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_backfill_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_statsbomb_fewshot_backfill_report_lines(
    queue: Mapping[str, object] | object,
    *,
    generated_at: datetime | None = None,
) -> list[str]:
    current = generated_at or datetime.now()
    resolved = _as_mapping(queue)
    tasks = [row for row in _as_list(resolved.get("tasks")) if isinstance(row, Mapping)]
    candidates = [row for row in _as_list(resolved.get("candidate_rows")) if isinstance(row, Mapping)]
    lines = [
        "# StatsBomb Few-shot 补样队列",
        "",
        f"- 生成时间: {current.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 摘要: {resolved.get('summary_text') or '-'}",
        f"- 状态: {resolved.get('status') or '-'}",
        f"- 防泄漏边界: {resolved.get('leakage_note') or '-'}",
        "",
        "## 补样任务",
        "",
        "| 优先级 | 任务 | 目标标签 | 说明 |",
        "| ---: | --- | --- | --- |",
    ]
    if not tasks:
        lines.append("| 0 | 暂无补样任务 | - | 当前 StatsBomb few-shot 记忆覆盖健康。 |")
    for task in tasks:
        target_tags = ", ".join(str(tag) for tag in _as_list(task.get("target_tags"))) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(_safe_int(task.get("priority"))),
                    _md_cell(task.get("title")),
                    _md_cell(target_tags),
                    _md_cell(task.get("body")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 候选比赛",
            "",
            "| 优先级 | 来源 | 日期 | 赛事 | 比赛 | 命中目标 | 标签 |",
            "| ---: | --- | --- | --- | --- | --- | --- |",
        ]
    )
    if not candidates:
        lines.append("| 0 | - | - | - | 暂无候选 | - | - |")
    for row in candidates:
        matched_tags = ", ".join(str(tag) for tag in _as_list(row.get("matched_tags"))) or "-"
        tags = ", ".join(str(tag) for tag in _as_list(row.get("tags"))) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(_safe_int(row.get("priority_score"))),
                    _md_cell(row.get("source")),
                    _md_cell(row.get("match_date")),
                    _md_cell(row.get("league")),
                    _md_cell(row.get("title")),
                    _md_cell(matched_tags),
                    _md_cell(tags),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 复盘执行原则",
            "",
            "- 只从已经完场且具备 StatsBomb 事件证据的比赛生成 few-shot 样本。",
            "- 样本用于 Evaluation Agent 赛后归因和报告增强，不得作为赛前预测特征。",
            "- 每次补样后重新检查标签覆盖率、当前错因命中数和根因集中度。",
            "",
        ]
    )
    return lines


def build_statsbomb_fewshot_draft_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_draft_{current.strftime('%Y%m%d_%H%M%S')}.json"


def build_statsbomb_fewshot_draft_review_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_draft_review_{current.strftime('%Y%m%d_%H%M%S')}.md"


def _statsbomb_baseline_row_key(row: Mapping[str, object]) -> list[str]:
    keys: list[str] = []
    for value in (row.get("match_id"), row.get("source_match_id")):
        text = str(value or "").strip()
        if text and text not in keys:
            keys.append(text)
    title = f"{row.get('match_date') or '-'} | {row.get('league') or '-'} | {row.get('home_team') or '-'} vs {row.get('away_team') or '-'}"
    if title not in keys:
        keys.append(title)
    return keys


def _statsbomb_fewshot_draft_from_baseline_row(
    row: Mapping[str, object],
    candidate: Mapping[str, object],
) -> dict[str, object]:
    score_winner = str(row.get("score_winner") or "").strip().lower()
    if score_winner not in {"home", "away", "draw"}:
        score_winner = _side_from_margin(_safe_float(row.get("goal_margin")))
    xg_winner = str(row.get("xg_winner") or "").strip().lower()
    if xg_winner not in {"home", "away", "draw"}:
        xg_winner = _side_from_margin(_safe_float(row.get("xg_margin")), threshold=0.25)
    simulated_pick = xg_winner if xg_winner in {"home", "away", "draw"} else score_winner
    actual = score_winner if score_winner in {"home", "away", "draw"} else "draw"
    is_hit = simulated_pick == actual
    tags = _statsbomb_baseline_backfill_tags(row)
    root_cause = "event_evidence_aligned" if is_hit else "statsbomb_finishing_variance" if bool(row.get("finishing_variance")) else "event_result_divergence"
    home_xg = _safe_float(row.get("home_xg"))
    away_xg = _safe_float(row.get("away_xg"))
    home_shots = _safe_int(row.get("home_shots"))
    away_shots = _safe_int(row.get("away_shots"))
    shot_margin = _safe_float(row.get("shot_margin"), float(home_shots - away_shots))
    match_title = f"{row.get('home_team') or '-'} vs {row.get('away_team') or '-'}"
    prompt = (
        "请作为 Evaluation Agent 复盘一场使用 StatsBomb 赛后事件的历史案例。\n"
        f"比赛: {row.get('match_date') or '-'} | {row.get('league') or '-'} | {match_title}\n"
        f"比分: {row.get('score') or '-'} | 模拟策略: 按 xG 方向选择 {_statsbomb_side_to_pick(simulated_pick)} | 实际: {_statsbomb_side_to_pick(actual)}\n"
        f"xG: {home_xg:.2f}-{away_xg:.2f} | 射门: {home_shots}-{away_shots} | 草稿目标标签: {', '.join(_as_list(candidate.get('matched_tags'))[:6]) or '-'}"
    )
    if is_hit:
        completion = "结论: 模拟策略命中。StatsBomb 事件方向与赛果一致，可作为 Evaluation Agent 的正向对照复盘样本。"
    else:
        completion = (
            "结论: 模拟策略未命中。StatsBomb 事件显示 xG 或射门质量支持模拟方向但赛果相反，"
            "应优先归因为终结波动、事件与结果背离或 xG 方向失效，不应回灌为赛前预测特征。"
        )
    return {
        "id": f"statsbomb_backfill_draft:{row.get('source_match_id') or row.get('match_id') or candidate.get('match_id') or '-'}",
        "review_status": "draft",
        "draft_note": "Generated from StatsBomb backfill queue. Review manually before merging into official few-shot memory.",
        "prompt": prompt,
        "completion": completion,
        "labels": {
            "simulated_pick": _statsbomb_side_to_pick(simulated_pick),
            "actual": _statsbomb_side_to_pick(actual),
            "is_hit": bool(is_hit),
            "root_cause": root_cause,
            "tags": tags,
        },
        "features": {
            "home_xg": home_xg,
            "away_xg": away_xg,
            "xg_margin": _safe_float(row.get("xg_margin")),
            "home_shots": float(home_shots),
            "away_shots": float(away_shots),
            "shot_margin": shot_margin,
            "event_count": float(_safe_float(row.get("event_count"))),
        },
        "meta": {
            "source": "statsbomb_fewshot_backfill_draft",
            "candidate_source": candidate.get("source") or "-",
            "match_id": row.get("match_id"),
            "source_match_id": row.get("source_match_id"),
            "match_date": row.get("match_date"),
            "league": row.get("league"),
            "season": row.get("season"),
            "home_team": row.get("home_team"),
            "away_team": row.get("away_team"),
            "score": row.get("score"),
            "matched_backfill_tags": [str(tag) for tag in _as_list(candidate.get("matched_tags"))],
        },
    }


def build_statsbomb_fewshot_draft_payload(
    queue: Mapping[str, object] | object,
    statsbomb_event_baseline: Mapping[str, object] | object | None = None,
    *,
    generated_at: datetime | None = None,
    limit: int = 20,
) -> dict[str, object]:
    current = generated_at or datetime.now()
    resolved_queue = _as_mapping(queue)
    baseline_items = [item for item in _as_list(_as_mapping(statsbomb_event_baseline).get("items")) if isinstance(item, Mapping)]
    baseline_index: dict[str, Mapping[str, object]] = {}
    for row in baseline_items:
        for key in _statsbomb_baseline_row_key(row):
            baseline_index[key] = row
    items: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    candidates = [row for row in _as_list(resolved_queue.get("candidate_rows")) if isinstance(row, Mapping)]
    for candidate in candidates:
        lookup_keys = [str(candidate.get("match_id") or "").strip(), str(candidate.get("title") or "").strip()]
        baseline_row = next((baseline_index[key] for key in lookup_keys if key and key in baseline_index), None)
        if not baseline_row:
            skipped.append({"match_id": candidate.get("match_id") or "-", "title": candidate.get("title") or "-", "reason": "missing_baseline_row"})
            continue
        draft = _statsbomb_fewshot_draft_from_baseline_row(baseline_row, candidate)
        draft_id = str(draft.get("id") or "")
        if draft_id in seen_ids:
            continue
        seen_ids.add(draft_id)
        items.append(draft)
        if len(items) >= max(0, int(limit)):
            break
    tag_counts: dict[str, int] = {}
    for item in items:
        labels = _as_mapping(item.get("labels"))
        for tag in _as_list(labels.get("tags")):
            tag_text = str(tag)
            tag_counts[tag_text] = tag_counts.get(tag_text, 0) + 1
    leakage_note = "Draft samples use post-match StatsBomb event data for Evaluation Agent review only; do not use as pre-match prediction features."
    payload = {
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "StatsBomb few-shot backfill queue",
        "purpose": "draft_only_manual_review_required",
        "review_status": "draft",
        "leakage_note": leakage_note,
        "summary": {
            "draft_count": len(items),
            "candidate_count": len(candidates),
            "skipped_count": len(skipped),
            "tag_counts": dict(sorted(tag_counts.items())),
        },
        "backfill_summary": resolved_queue.get("summary_text") or "-",
        "items": items,
        "skipped": skipped,
    }
    payload["validation"] = validate_statsbomb_fewshot_draft_payload(payload)
    return payload


def validate_statsbomb_fewshot_draft_payload(payload: Mapping[str, object] | object) -> dict[str, object]:
    resolved = _as_mapping(payload)
    items = [item for item in _as_list(resolved.get("items")) if isinstance(item, Mapping)]
    issues: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    duplicate_ids: set[str] = set()
    required_top_fields = ("id", "prompt", "completion", "labels", "features", "meta", "review_status")
    required_labels = ("simulated_pick", "actual", "is_hit", "root_cause", "tags")
    required_features = ("home_xg", "away_xg", "xg_margin", "home_shots", "away_shots", "shot_margin", "event_count")
    required_meta = ("match_date", "league", "home_team", "away_team", "score")
    leakage_terms = (
        "pre-match prediction feature",
        "赛前预测特征",
        "用于赛前预测",
        "feed into pre-match",
    )
    tag_counts: dict[str, int] = {}

    for index, item in enumerate(items):
        item_id = str(item.get("id") or f"index:{index}")
        if item_id in seen_ids:
            duplicate_ids.add(item_id)
        seen_ids.add(item_id)
        for field in required_top_fields:
            value = item.get(field)
            if field not in item or value is None or value == "":
                issues.append({"severity": "high", "item_id": item_id, "code": "missing_field", "field": field})
        if str(item.get("review_status") or "") != "draft":
            issues.append({"severity": "medium", "item_id": item_id, "code": "unexpected_review_status", "field": "review_status"})
        labels = _as_mapping(item.get("labels"))
        for field in required_labels:
            value = labels.get(field)
            if field not in labels or value is None or value == "":
                issues.append({"severity": "high", "item_id": item_id, "code": "missing_label", "field": field})
        tags = [str(tag) for tag in _as_list(labels.get("tags")) if str(tag)]
        if not tags:
            issues.append({"severity": "high", "item_id": item_id, "code": "missing_tags", "field": "labels.tags"})
        if "statsbomb_post_match_review" not in tags:
            issues.append({"severity": "high", "item_id": item_id, "code": "missing_post_match_tag", "field": "labels.tags"})
        if "strategy_hit" not in tags and "strategy_miss" not in tags:
            issues.append({"severity": "medium", "item_id": item_id, "code": "missing_hit_miss_tag", "field": "labels.tags"})
        for tag in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        features = _as_mapping(item.get("features"))
        for field in required_features:
            if field not in features:
                issues.append({"severity": "medium", "item_id": item_id, "code": "missing_feature", "field": field})
        meta = _as_mapping(item.get("meta"))
        for field in required_meta:
            if field not in meta or meta.get(field) in {None, ""}:
                issues.append({"severity": "medium", "item_id": item_id, "code": "missing_meta", "field": field})
        combined_text = "\n".join(
            [
                str(item.get("prompt") or ""),
                str(item.get("completion") or ""),
                str(item.get("draft_note") or ""),
            ]
        ).lower()
        for term in leakage_terms:
            if term.lower() in combined_text:
                issues.append({"severity": "medium", "item_id": item_id, "code": "leakage_boundary_mention", "field": "prompt/completion"})
                break

    for item_id in sorted(duplicate_ids):
        issues.append({"severity": "high", "item_id": item_id, "code": "duplicate_id", "field": "id"})
    if not items:
        issues.append({"severity": "medium", "item_id": "-", "code": "empty_draft", "field": "items"})

    high_count = sum(1 for issue in issues if issue.get("severity") == "high")
    medium_count = sum(1 for issue in issues if issue.get("severity") == "medium")
    status = "blocked" if high_count else "review" if medium_count else "ready"
    return {
        "status": status,
        "issue_count": len(issues),
        "high_count": high_count,
        "medium_count": medium_count,
        "tag_counts": dict(sorted(tag_counts.items())),
        "issues": issues[:50],
        "summary_text": f"草稿校验 {status} | 问题 {len(issues)} | high {high_count} | medium {medium_count}",
    }


def _statsbomb_fewshot_item_keys(item: Mapping[str, object]) -> list[str]:
    keys: list[str] = []
    item_id = str(item.get("id") or "").strip()
    if item_id:
        keys.append(f"id:{item_id}")
    meta = _as_mapping(item.get("meta"))
    for field in ("match_id", "source_match_id"):
        value = str(meta.get(field) or "").strip()
        if value:
            keys.append(f"{field}:{value}")
    title = f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}"
    if title.strip():
        keys.append(f"title:{title}")
    deduped: list[str] = []
    for key in keys:
        if key not in deduped:
            deduped.append(key)
    return deduped


def build_statsbomb_fewshot_merge_plan(
    draft_payload: Mapping[str, object] | object,
    existing_memory: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    draft = _as_mapping(draft_payload)
    validation = _as_mapping(draft.get("validation")) or validate_statsbomb_fewshot_draft_payload(draft)
    existing_items = [item for item in _statsbomb_memory_items(existing_memory or {}) if isinstance(item, Mapping)]
    existing_keys: set[str] = set()
    for item in existing_items:
        existing_keys.update(_statsbomb_fewshot_item_keys(item))
    mergeable: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    seen_draft_keys: set[str] = set()
    if _safe_int(validation.get("high_count")) > 0:
        return {
            "status": "blocked",
            "mergeable_count": 0,
            "skipped_count": len(_as_list(draft.get("items"))),
            "existing_count": len(existing_items),
            "mergeable_items": [],
            "skipped_rows": [
                {
                    "id": _as_mapping(item).get("id") or "-",
                    "title": (
                        f"{_as_mapping(_as_mapping(item).get('meta')).get('match_date') or '-'} | "
                        f"{_as_mapping(_as_mapping(item).get('meta')).get('league') or '-'} | "
                        f"{_as_mapping(_as_mapping(item).get('meta')).get('home_team') or '-'} vs "
                        f"{_as_mapping(_as_mapping(item).get('meta')).get('away_team') or '-'}"
                    ),
                    "reason": "validation_high_issues",
                }
                for item in _as_list(draft.get("items"))
                if isinstance(item, Mapping)
            ],
            "validation": validation,
            "summary_text": f"合并计划 blocked | 可合并 0 | 跳过 {len(_as_list(draft.get('items')))} | high {_safe_int(validation.get('high_count'))}",
            "leakage_note": "Merge plan is read-only and does not write to official few-shot memory.",
        }
    for item in [row for row in _as_list(draft.get("items")) if isinstance(row, Mapping)]:
        item_id = str(item.get("id") or "-")
        item_keys = _statsbomb_fewshot_item_keys(item)
        meta = _as_mapping(item.get("meta"))
        title = f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}"
        overlap_existing = sorted(set(item_keys) & existing_keys)
        overlap_draft = sorted(set(item_keys) & seen_draft_keys)
        if overlap_existing:
            skipped.append({"id": item_id, "title": title, "reason": "already_in_memory", "matched_keys": overlap_existing[:3]})
            continue
        if overlap_draft:
            skipped.append({"id": item_id, "title": title, "reason": "duplicate_in_draft", "matched_keys": overlap_draft[:3]})
            continue
        seen_draft_keys.update(item_keys)
        labels = _as_mapping(item.get("labels"))
        mergeable.append(
            {
                "id": item_id,
                "title": title,
                "root_cause": labels.get("root_cause") or "-",
                "tags": [str(tag) for tag in _as_list(labels.get("tags"))],
                "item": item,
            }
        )
    status = "ready" if mergeable and _safe_int(validation.get("medium_count")) == 0 else "review" if mergeable else "empty"
    return {
        "status": status,
        "mergeable_count": len(mergeable),
        "skipped_count": len(skipped),
        "existing_count": len(existing_items),
        "mergeable_items": mergeable,
        "skipped_rows": skipped,
        "validation": validation,
        "summary_text": f"合并计划 {status} | 可合并 {len(mergeable)} | 跳过 {len(skipped)} | 现有 {len(existing_items)}",
        "leakage_note": "Merge plan is read-only and does not write to official few-shot memory.",
    }


def build_statsbomb_fewshot_merge_plan_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_merge_plan_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_statsbomb_fewshot_merge_plan_lines(plan: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(plan)
    validation = _as_mapping(resolved.get("validation"))
    mergeable = [item for item in _as_list(resolved.get("mergeable_items")) if isinstance(item, Mapping)]
    skipped = [item for item in _as_list(resolved.get("skipped_rows")) if isinstance(item, Mapping)]
    lines = [
        "# StatsBomb Few-shot 合并计划",
        "",
        f"- 摘要: {resolved.get('summary_text') or '-'}",
        f"- 状态: {resolved.get('status') or '-'}",
        f"- 校验: {validation.get('summary_text') or '-'}",
        f"- 防泄漏边界: {resolved.get('leakage_note') or '-'}",
        "",
        "## 可合并样本",
        "",
        "| ID | 比赛 | 根因 | 标签 |",
        "| --- | --- | --- | --- |",
    ]
    if not mergeable:
        lines.append("| - | 暂无可合并样本 | - | - |")
    for row in mergeable:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("id")),
                    _md_cell(row.get("title")),
                    _md_cell(row.get("root_cause")),
                    _md_cell(", ".join(str(tag) for tag in _as_list(row.get("tags")))),
                ]
            )
            + " |"
        )
    lines.extend(["", "## 跳过样本", "", "| ID | 比赛 | 原因 | 匹配键 |", "| --- | --- | --- | --- |"])
    if not skipped:
        lines.append("| - | 暂无跳过样本 | - | - |")
    for row in skipped:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("id")),
                    _md_cell(row.get("title")),
                    _md_cell(row.get("reason")),
                    _md_cell(", ".join(str(key) for key in _as_list(row.get("matched_keys")))),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 后续原则",
            "",
            "- 该计划只读，不会写入正式 few-shot 记忆库。",
            "- blocked 状态必须先修复草稿 high 问题。",
            "- review 状态需要人工确认 medium 问题后再合并。",
            "- 合并后必须重新运行记忆覆盖监控和补样队列。",
            "",
        ]
    )
    return lines


def build_statsbomb_fewshot_merge_bundle_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_merge_bundle_{current.strftime('%Y%m%d_%H%M%S')}.json"


def build_statsbomb_fewshot_merge_bundle_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_merge_bundle_review_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_statsbomb_fewshot_merge_bundle(
    plan: Mapping[str, object] | object,
    *,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    current = generated_at or datetime.now()
    resolved = _as_mapping(plan)
    validation = _as_mapping(resolved.get("validation"))
    mergeable = [item for item in _as_list(resolved.get("mergeable_items")) if isinstance(item, Mapping)]
    bundle_items = [_as_mapping(item.get("item")) for item in mergeable if _as_mapping(item.get("item"))]
    status = "blocked"
    if str(resolved.get("status") or "") in {"ready", "review"} and bundle_items:
        status = "pending_manual_apply"
    elif str(resolved.get("status") or "") == "empty":
        status = "empty"
    return {
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "StatsBomb few-shot merge plan",
        "purpose": "manual_apply_bundle",
        "status": status,
        "approval_required": True,
        "write_policy": "read_only_export_no_state_write",
        "leakage_note": "Bundle contains post-match StatsBomb review samples only; applying it must not feed samples into pre-match prediction features.",
        "plan_summary": resolved.get("summary_text") or "-",
        "validation_summary": validation.get("summary_text") or "-",
        "summary": {
            "bundle_count": len(bundle_items),
            "merge_plan_status": resolved.get("status") or "-",
            "skipped_count": _safe_int(resolved.get("skipped_count")),
            "existing_count": _safe_int(resolved.get("existing_count")),
        },
        "items": bundle_items,
        "skipped_rows": [dict(row) for row in _as_list(resolved.get("skipped_rows")) if isinstance(row, Mapping)],
    }


def build_statsbomb_fewshot_merge_bundle_report_lines(bundle: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(bundle)
    summary = _as_mapping(resolved.get("summary"))
    items = [item for item in _as_list(resolved.get("items")) if isinstance(item, Mapping)]
    skipped = [item for item in _as_list(resolved.get("skipped_rows")) if isinstance(item, Mapping)]
    lines = [
        "# StatsBomb Few-shot 合并可应用包",
        "",
        f"- 生成时间: {resolved.get('updated_at') or '-'}",
        f"- 状态: {resolved.get('status') or '-'}",
        f"- 审批要求: {'YES' if resolved.get('approval_required') else 'NO'}",
        f"- 写入策略: {resolved.get('write_policy') or '-'}",
        f"- 计划摘要: {resolved.get('plan_summary') or '-'}",
        f"- 校验摘要: {resolved.get('validation_summary') or '-'}",
        f"- 防泄漏边界: {resolved.get('leakage_note') or '-'}",
        "",
        "## Bundle 摘要",
        "",
        f"- 可应用样本: {_safe_int(summary.get('bundle_count'))}",
        f"- 合并计划状态: {summary.get('merge_plan_status') or '-'}",
        f"- 跳过样本: {_safe_int(summary.get('skipped_count'))}",
        f"- 现有记忆样本: {_safe_int(summary.get('existing_count'))}",
        "",
        "## 可应用样本",
        "",
        "| ID | 比赛 | 根因 | 标签 |",
        "| --- | --- | --- | --- |",
    ]
    if not items:
        lines.append("| - | 暂无可应用样本 | - | - |")
    for item in items:
        labels = _as_mapping(item.get("labels"))
        meta = _as_mapping(item.get("meta"))
        title = f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}"
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(item.get("id")),
                    _md_cell(title),
                    _md_cell(labels.get("root_cause")),
                    _md_cell(", ".join(str(tag) for tag in _as_list(labels.get("tags")))),
                ]
            )
            + " |"
        )
    if skipped:
        lines.extend(["", "## 跳过记录", "", "| ID | 比赛 | 原因 |", "| --- | --- | --- |"])
        for row in skipped[:20]:
            lines.append(
                "| "
                + " | ".join([_md_cell(row.get("id")), _md_cell(row.get("title")), _md_cell(row.get("reason"))])
                + " |"
            )
    lines.extend(
        [
            "",
            "## 应用前检查",
            "",
            "- [ ] 人工确认 bundle 中每条样本都来自赛后事件证据。",
            "- [ ] 人工确认没有 high 级草稿校验问题。",
            "- [ ] 应用前备份正式 few-shot 记忆库。",
            "- [ ] 应用后重新运行记忆监控、补样队列和 Evaluation Agent 相关测试。",
            "",
        ]
    )
    return lines


def build_statsbomb_fewshot_merge_apply_preview_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_merge_apply_preview_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_statsbomb_fewshot_merge_apply_preview(
    bundle: Mapping[str, object] | object,
    existing_memory: Mapping[str, object] | object | None = None,
    *,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    current = generated_at or datetime.now()
    resolved = _as_mapping(bundle)
    items = [item for item in _as_list(resolved.get("items")) if isinstance(item, Mapping)]
    validation = validate_statsbomb_fewshot_draft_payload({"items": items})
    existing_items = [item for item in _statsbomb_memory_items(existing_memory or {}) if isinstance(item, Mapping)]
    existing_keys: set[str] = set()
    for item in existing_items:
        existing_keys.update(_statsbomb_fewshot_item_keys(item))
    append_items: list[Mapping[str, object]] = []
    skipped_rows: list[dict[str, object]] = []
    seen_bundle_keys: set[str] = set()
    for item in items:
        item_id = str(item.get("id") or "-")
        meta = _as_mapping(item.get("meta"))
        title = f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}"
        item_keys = _statsbomb_fewshot_item_keys(item)
        overlap_existing = sorted(set(item_keys) & existing_keys)
        overlap_bundle = sorted(set(item_keys) & seen_bundle_keys)
        if overlap_existing:
            skipped_rows.append({"id": item_id, "title": title, "reason": "already_in_memory", "matched_keys": overlap_existing[:3]})
            continue
        if overlap_bundle:
            skipped_rows.append({"id": item_id, "title": title, "reason": "duplicate_in_bundle", "matched_keys": overlap_bundle[:3]})
            continue
        seen_bundle_keys.update(item_keys)
        append_items.append(item)

    bundle_status = str(resolved.get("status") or "")
    bundle_purpose = str(resolved.get("purpose") or "")
    structural_issues: list[dict[str, object]] = []
    if bundle_purpose != "manual_apply_bundle":
        structural_issues.append({"severity": "high", "code": "unexpected_purpose", "field": "purpose"})
    if bundle_status not in {"pending_manual_apply", "empty"}:
        structural_issues.append({"severity": "high", "code": "unexpected_bundle_status", "field": "status"})
    if resolved.get("approval_required") is not True:
        structural_issues.append({"severity": "high", "code": "approval_not_required", "field": "approval_required"})
    if _safe_int(validation.get("high_count")):
        structural_issues.append({"severity": "high", "code": "sample_validation_high", "field": "items"})

    high_count = _safe_int(validation.get("high_count")) + sum(1 for issue in structural_issues if issue.get("severity") == "high")
    medium_count = _safe_int(validation.get("medium_count")) + sum(1 for issue in structural_issues if issue.get("severity") == "medium")
    if high_count:
        status = "blocked"
    elif append_items:
        status = "ready_for_manual_apply" if medium_count == 0 else "review_required"
    else:
        status = "empty"
    backup_filename = f"statsbomb_sandbox_fewshot_samples.backup_{current.strftime('%Y%m%d_%H%M%S')}.json"
    return {
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "StatsBomb few-shot merge bundle",
        "purpose": "manual_apply_preview",
        "status": status,
        "dry_run": True,
        "approval_required": True,
        "no_state_write": True,
        "leakage_note": resolved.get("leakage_note")
        or "StatsBomb post-match review samples must stay inside Evaluation Agent memory.",
        "backup_filename": backup_filename,
        "summary": {
            "append_count": len(append_items) if not high_count else 0,
            "skipped_count": len(skipped_rows),
            "existing_count": len(existing_items),
            "bundle_count": len(items),
            "high_count": high_count,
            "medium_count": medium_count,
        },
        "validation": validation,
        "structural_issues": structural_issues,
        "append_items": [] if high_count else [dict(item) for item in append_items],
        "skipped_rows": skipped_rows,
    }


def build_statsbomb_fewshot_merge_apply_preview_lines(preview: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(preview)
    summary = _as_mapping(resolved.get("summary"))
    validation = _as_mapping(resolved.get("validation"))
    append_items = [item for item in _as_list(resolved.get("append_items")) if isinstance(item, Mapping)]
    skipped_rows = [item for item in _as_list(resolved.get("skipped_rows")) if isinstance(item, Mapping)]
    structural_issues = [item for item in _as_list(resolved.get("structural_issues")) if isinstance(item, Mapping)]
    lines = [
        "# StatsBomb Few-shot Merge Apply Preview",
        "",
        f"- Generated at: {resolved.get('updated_at') or '-'}",
        f"- Status: {resolved.get('status') or '-'}",
        f"- Dry run: {'YES' if resolved.get('dry_run') else 'NO'}",
        f"- Approval required: {'YES' if resolved.get('approval_required') else 'NO'}",
        f"- No state write: {'YES' if resolved.get('no_state_write') else 'NO'}",
        f"- Backup filename before real apply: {resolved.get('backup_filename') or '-'}",
        f"- Leakage boundary: {resolved.get('leakage_note') or '-'}",
        "",
        "## Summary",
        "",
        f"- Would append: {_safe_int(summary.get('append_count'))}",
        f"- Skipped: {_safe_int(summary.get('skipped_count'))}",
        f"- Existing memory samples: {_safe_int(summary.get('existing_count'))}",
        f"- Bundle samples: {_safe_int(summary.get('bundle_count'))}",
        f"- Validation high/medium: {_safe_int(summary.get('high_count'))} / {_safe_int(summary.get('medium_count'))}",
        f"- Draft validation: {validation.get('summary_text') or '-'}",
        "",
        "## Would Append",
        "",
        "| ID | Match | Root cause | Tags |",
        "| --- | --- | --- | --- |",
    ]
    if not append_items:
        lines.append("| - | No appendable sample | - | - |")
    for item in append_items:
        labels = _as_mapping(item.get("labels"))
        meta = _as_mapping(item.get("meta"))
        title = f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}"
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(item.get("id")),
                    _md_cell(title),
                    _md_cell(labels.get("root_cause")),
                    _md_cell(", ".join(str(tag) for tag in _as_list(labels.get("tags")))),
                ]
            )
            + " |"
        )
    if skipped_rows:
        lines.extend(["", "## Skipped", "", "| ID | Match | Reason | Matched keys |", "| --- | --- | --- | --- |"])
        for row in skipped_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _md_cell(row.get("id")),
                        _md_cell(row.get("title")),
                        _md_cell(row.get("reason")),
                        _md_cell(", ".join(str(key) for key in _as_list(row.get("matched_keys")))),
                    ]
                )
                + " |"
            )
    if structural_issues:
        lines.extend(["", "## Blocking Issues", "", "| Severity | Code | Field |", "| --- | --- | --- |"])
        for issue in structural_issues:
            lines.append(
                "| "
                + " | ".join([_md_cell(issue.get("severity")), _md_cell(issue.get("code")), _md_cell(issue.get("field"))])
                + " |"
            )
    lines.extend(
        [
            "",
            "## Next Manual Checks",
            "",
            "- Confirm every sample is post-match evidence for Evaluation Agent only.",
            "- Confirm the preview status is ready_for_manual_apply or review_required.",
            "- Back up the official few-shot memory before any future real apply operation.",
            "- Re-run memory monitor and Evaluation Agent tests after any future real apply operation.",
            "",
        ]
    )
    return lines


def build_statsbomb_fewshot_merge_apply_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_merge_applied_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_statsbomb_fewshot_merge_apply_result(
    bundle: Mapping[str, object] | object,
    existing_memory: Mapping[str, object] | object | None = None,
    *,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    current = generated_at or datetime.now()
    preview = build_statsbomb_fewshot_merge_apply_preview(bundle, existing_memory or {}, generated_at=current)
    preview_summary = _as_mapping(preview.get("summary"))
    preview_status = str(preview.get("status") or "")
    append_items = [item for item in _as_list(preview.get("append_items")) if isinstance(item, Mapping)]
    if preview_status not in {"ready_for_manual_apply", "review_required"} or not append_items:
        return {
            "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "StatsBomb few-shot merge bundle",
            "purpose": "manual_apply_result",
            "status": "blocked" if preview_status == "blocked" else "empty",
            "preview": preview,
            "summary": {
                "applied_count": 0,
                "existing_count": _safe_int(preview_summary.get("existing_count")),
                "final_count": _safe_int(preview_summary.get("existing_count")),
                "skipped_count": _safe_int(preview_summary.get("skipped_count")),
            },
            "updated_memory": None,
        }

    existing = _as_mapping(existing_memory or {})
    existing_items = [dict(item) for item in _statsbomb_memory_items(existing)]
    approved_items: list[dict[str, object]] = []
    for item in append_items:
        approved = dict(item)
        approved["review_status"] = "approved"
        approved["applied_at"] = current.strftime("%Y-%m-%d %H:%M:%S")
        approved_items.append(approved)
    merged_items = existing_items + approved_items
    tag_counts: dict[str, int] = {}
    hit_count = 0
    miss_count = 0
    for item in merged_items:
        labels = _as_mapping(item.get("labels"))
        if labels.get("is_hit") is True:
            hit_count += 1
        elif labels.get("is_hit") is False:
            miss_count += 1
        for tag in _as_list(labels.get("tags")):
            tag_text = str(tag)
            if tag_text:
                tag_counts[tag_text] = tag_counts.get(tag_text, 0) + 1
    existing_summary = dict(_as_mapping(existing.get("summary")))
    existing_summary.update(
        {
            "sample_count": len(merged_items),
            "tag_counts": dict(sorted(tag_counts.items())),
            "hit_count": hit_count,
            "miss_count": miss_count,
            "last_manual_apply_at": current.strftime("%Y-%m-%d %H:%M:%S"),
            "last_manual_apply_count": len(approved_items),
        }
    )
    leakage_note = (
        str(existing.get("leakage_note") or "")
        or str(_as_mapping(bundle).get("leakage_note") or "")
        or "These few-shot samples use post-match event data and must not be used as pre-match prediction features."
    )
    updated_memory = dict(existing)
    updated_memory.update(
        {
            "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
            "source": existing.get("source") or "StatsBomb few-shot memory with manual merge",
            "purpose": existing.get("purpose") or "evaluation_agent_fewshot_post_match_review",
            "leakage_note": leakage_note,
            "summary": existing_summary,
            "items": merged_items,
            "last_manual_apply": {
                "applied_at": current.strftime("%Y-%m-%d %H:%M:%S"),
                "applied_count": len(approved_items),
                "skipped_count": _safe_int(preview_summary.get("skipped_count")),
                "backup_filename": preview.get("backup_filename") or "-",
            },
        }
    )
    return {
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "StatsBomb few-shot merge bundle",
        "purpose": "manual_apply_result",
        "status": "ready_to_write",
        "preview": preview,
        "summary": {
            "applied_count": len(approved_items),
            "existing_count": len(existing_items),
            "final_count": len(merged_items),
            "skipped_count": _safe_int(preview_summary.get("skipped_count")),
        },
        "updated_memory": updated_memory,
    }


def build_statsbomb_fewshot_merge_apply_report_lines(result: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(result)
    summary = _as_mapping(resolved.get("summary"))
    preview = _as_mapping(resolved.get("preview"))
    lines = [
        "# StatsBomb Few-shot Merge Apply",
        "",
        f"- Applied at: {resolved.get('updated_at') or '-'}",
        f"- Status: {resolved.get('status') or '-'}",
        f"- Preview status: {preview.get('status') or '-'}",
        f"- Applied samples: {_safe_int(summary.get('applied_count'))}",
        f"- Skipped samples: {_safe_int(summary.get('skipped_count'))}",
        f"- Existing samples before apply: {_safe_int(summary.get('existing_count'))}",
        f"- Final memory samples: {_safe_int(summary.get('final_count'))}",
        f"- Backup filename: {preview.get('backup_filename') or '-'}",
        f"- Leakage boundary: {preview.get('leakage_note') or '-'}",
        "",
        "## Applied Items",
        "",
        "| ID | Match | Root cause | Tags |",
        "| --- | --- | --- | --- |",
    ]
    for item in [item for item in _as_list(preview.get("append_items")) if isinstance(item, Mapping)]:
        labels = _as_mapping(item.get("labels"))
        meta = _as_mapping(item.get("meta"))
        title = f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}"
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(item.get("id")),
                    _md_cell(title),
                    _md_cell(labels.get("root_cause")),
                    _md_cell(", ".join(str(tag) for tag in _as_list(labels.get("tags")))),
                ]
            )
            + " |"
        )
    if _safe_int(summary.get("applied_count")) == 0:
        lines.append("| - | No sample was applied | - | - |")
    lines.extend(
        [
            "",
            "## Required Follow-up",
            "",
            "- Re-open the strategy dashboard and confirm the few-shot monitor sample count increased.",
            "- Export the backfill queue again to verify coverage gaps changed as expected.",
            "- Keep this report with the backup file for rollback reference.",
            "",
        ]
    )
    return lines


def build_statsbomb_fewshot_draft_review_lines(payload: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(payload)
    summary = _as_mapping(resolved.get("summary"))
    validation = _as_mapping(resolved.get("validation")) or validate_statsbomb_fewshot_draft_payload(resolved)
    items = [item for item in _as_list(resolved.get("items")) if isinstance(item, Mapping)]
    skipped = [item for item in _as_list(resolved.get("skipped")) if isinstance(item, Mapping)]
    lines = [
        "# StatsBomb Few-shot 草稿审查",
        "",
        f"- 生成时间: {resolved.get('updated_at') or '-'}",
        f"- 草稿数量: {_safe_int(summary.get('draft_count'))}",
        f"- 候选数量: {_safe_int(summary.get('candidate_count'))}",
        f"- 跳过数量: {_safe_int(summary.get('skipped_count'))}",
        f"- 防泄漏边界: {resolved.get('leakage_note') or '-'}",
        f"- 校验摘要: {validation.get('summary_text') or '-'}",
        "",
        "## 质量校验",
        "",
        f"- 状态: {validation.get('status') or '-'}",
        f"- High: {_safe_int(validation.get('high_count'))}",
        f"- Medium: {_safe_int(validation.get('medium_count'))}",
        "",
    ]
    validation_issues = [item for item in _as_list(validation.get("issues")) if isinstance(item, Mapping)]
    if validation_issues:
        lines.extend(["| 严重度 | 样本 | 代码 | 字段 |", "| --- | --- | --- | --- |"])
        for issue in validation_issues[:12]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _md_cell(issue.get("severity")),
                        _md_cell(issue.get("item_id")),
                        _md_cell(issue.get("code")),
                        _md_cell(issue.get("field")),
                    ]
                )
                + " |"
            )
        lines.append("")
    else:
        lines.extend(["未发现结构性问题。", ""])
    lines.extend(
        [
            "## 草稿样本",
            "",
        ]
    )
    if not items:
        lines.extend(["暂无可审查草稿。", ""])
    for item in items:
        labels = _as_mapping(item.get("labels"))
        meta = _as_mapping(item.get("meta"))
        lines.extend(
            [
                f"### {meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}",
                "",
                f"- ID: {item.get('id') or '-'}",
                f"- 状态: {item.get('review_status') or '-'}",
                f"- 模拟/实际: {labels.get('simulated_pick') or '-'} / {labels.get('actual') or '-'}",
                f"- 命中: {labels.get('is_hit')}",
                f"- 根因: {labels.get('root_cause') or '-'}",
                f"- 标签: {', '.join(str(tag) for tag in _as_list(labels.get('tags'))) or '-'}",
                f"- 补样命中标签: {', '.join(str(tag) for tag in _as_list(meta.get('matched_backfill_tags'))) or '-'}",
                "",
                str(item.get("completion") or "-"),
                "",
            ]
        )
    if skipped:
        lines.extend(["## 跳过候选", "", "| Match ID | 比赛 | 原因 |", "| --- | --- | --- |"])
        for item in skipped:
            lines.append(
                "| "
                + " | ".join([_md_cell(item.get("match_id")), _md_cell(item.get("title")), _md_cell(item.get("reason"))])
                + " |"
            )
        lines.append("")
    lines.extend(
        [
            "## 合并前检查",
            "",
            "- [ ] 确认样本来自完场后的 StatsBomb 事件证据。",
            "- [ ] 确认标签、根因和 completion 没有把赛后信息写入赛前预测特征。",
            "- [ ] 确认样本覆盖的是当前缺口标签或当前错因相似案例。",
            "",
        ]
    )
    return lines


def _statsbomb_sandbox_row(row: Mapping[str, object], baseline: Mapping[str, object] | object | None = None) -> dict[str, object]:
    xg_margin = _safe_float(row.get("xg_margin"))
    goal_margin = _safe_int(row.get("goal_margin"))
    diagnosis: list[str] = []
    if bool(row.get("finishing_variance")):
        diagnosis.append("\u7ec8\u7ed3\u6ce2\u52a8")
    if not bool(row.get("xg_aligned_with_score")):
        diagnosis.append("xG\u4e0e\u8d5b\u679c\u80cc\u79bb")
    if not bool(row.get("shot_aligned_with_score")):
        diagnosis.append("\u5c04\u95e8\u4e0e\u8d5b\u679c\u80cc\u79bb")
    if not diagnosis:
        diagnosis.append("\u4e8b\u4ef6\u652f\u6301\u8d5b\u679c")
    diagnosis_text = "\u3001".join(diagnosis)
    return {
        "match_id": row.get("match_id") or "-",
        "match_date": row.get("match_date") or "-",
        "league": row.get("league") or "-",
        "season": row.get("season") or "-",
        "title": f"{row.get('home_team') or '-'} vs {row.get('away_team') or '-'}",
        "score": row.get("score") or "-",
        "xg": f"{_safe_float(row.get('home_xg')):.2f}-{_safe_float(row.get('away_xg')):.2f}",
        "shots": f"{_safe_int(row.get('home_shots'))}-{_safe_int(row.get('away_shots'))}",
        "xg_margin": round(xg_margin, 4),
        "goal_margin": goal_margin,
        "diagnosis": diagnosis_text,
        "event_count": _safe_int(row.get("event_count")),
        "body": (
            f"{row.get('match_date') or '-'} | {row.get('league') or '-'} | {row.get('home_team') or '-'} vs {row.get('away_team') or '-'}\n"
            f"\u6bd4\u5206 {row.get('score') or '-'} | xG {_safe_float(row.get('home_xg')):.2f}-{_safe_float(row.get('away_xg')):.2f} | "
            f"\u5c04\u95e8 {_safe_int(row.get('home_shots'))}-{_safe_int(row.get('away_shots'))} | \u8bca\u65ad {diagnosis_text}"
        ),
        "evaluation_case": build_statsbomb_event_replay_case(row, baseline or {}),
    }


def _statsbomb_side_to_pick(side: object) -> str:
    text = str(side or "").strip().lower()
    if text == "home":
        return "HOME"
    if text == "away":
        return "AWAY"
    if text == "draw":
        return "DRAW"
    return "-"


def _statsbomb_event_summary_from_baseline_row(row: Mapping[str, object]) -> dict[str, object]:
    home = str(row.get("home_team") or "")
    away = str(row.get("away_team") or "")
    return {
        "event_count": _safe_int(row.get("event_count")),
        "team_stats": {
            home: {
                "xg": _safe_float(row.get("home_xg")),
                "shots": _safe_int(row.get("home_shots")),
                "shots_on_target": _safe_int(row.get("home_shots_on_target")),
                "goals": _safe_int(str(row.get("score") or "0-0").split("-", 1)[0]),
            },
            away: {
                "xg": _safe_float(row.get("away_xg")),
                "shots": _safe_int(row.get("away_shots")),
                "shots_on_target": _safe_int(row.get("away_shots_on_target")),
                "goals": _safe_int(str(row.get("score") or "0-0").split("-", 1)[1] if "-" in str(row.get("score") or "") else 0),
            },
        },
    }


def build_statsbomb_event_replay_case(
    row: Mapping[str, object] | object,
    baseline: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    source = _as_mapping(row)
    if not source:
        return {"status": "empty", "body": "-"}
    score_winner = str(source.get("score_winner") or "").strip().lower()
    xg_winner = str(source.get("xg_winner") or "").strip().lower()
    if not score_winner:
        score_winner = _side_from_margin(_safe_float(source.get("goal_margin")))
    if not xg_winner:
        xg_winner = _side_from_margin(_safe_float(source.get("xg_margin")), threshold=0.25)
    simulated_pick = xg_winner if xg_winner in {"home", "away", "draw"} else score_winner
    actual = score_winner if score_winner in {"home", "away", "draw"} else "draw"
    is_hit = simulated_pick == actual
    settlement = {
        "match_id": source.get("match_id"),
        "match_date": source.get("match_date"),
        "league": source.get("league"),
        "home_team": source.get("home_team"),
        "away_team": source.get("away_team"),
        "home_goals": _safe_int(str(source.get("score") or "0-0").split("-", 1)[0]),
        "away_goals": _safe_int(str(source.get("score") or "0-0").split("-", 1)[1] if "-" in str(source.get("score") or "") else 0),
        "statsbomb_event_summary": _statsbomb_event_summary_from_baseline_row(source),
        "high_accuracy_strategy_items": [
            {
                "data_layer": "statsbomb_event_sandbox",
                "play_type": "market_1x2",
                "pick": _statsbomb_side_to_pick(simulated_pick),
                "actual": _statsbomb_side_to_pick(actual),
                "confidence": 0.70 if bool(source.get("finishing_variance")) else 0.62,
                "min_confidence": 0.65,
                "backtest_accuracy": 0.72,
                "backtest_samples": 180,
                "is_hit": is_hit,
            }
        ],
    }
    evaluation = build_strategy_evaluation_agent_summary({"enabled": True}, [settlement], baseline or {})
    attribution = _as_mapping(evaluation.get("error_attribution"))
    event_review = _as_mapping(evaluation.get("statsbomb_event_review"))
    body = (
        f"Evaluation: {evaluation.get('status', '-')} / score {evaluation.get('score', '-')}\n"
        f"\u6a21\u62df\u7b56\u7565: \u6309xG\u65b9\u5411\u9009 {settlement['high_accuracy_strategy_items'][0]['pick']} | "
        f"\u5b9e\u9645 {settlement['high_accuracy_strategy_items'][0]['actual']} | {'\u547d\u4e2d' if is_hit else '\u672a\u547d\u4e2d'}\n"
        f"\u4e3b\u9519\u56e0: {attribution.get('top_reason') or '-'} | \u4e8b\u4ef6\u590d\u76d8: {event_review.get('summary_text') or '-'}"
    )
    recommendations = evaluation.get("recommendations") if isinstance(evaluation.get("recommendations"), list) else []
    if recommendations:
        body = f"{body}\n\u5efa\u8bae: " + " | ".join(str(item.get("title") or "-") for item in recommendations if isinstance(item, Mapping))
    return {
        "status": "hit" if is_hit else "miss",
        "settlement": settlement,
        "evaluation": evaluation,
        "body": body,
    }


def build_statsbomb_event_sandbox_summary(
    baseline: Mapping[str, object] | object,
    *,
    limit: int = 20,
) -> dict[str, object]:
    resolved = _as_mapping(baseline)
    summary = _as_mapping(resolved.get("summary"))
    item_rows = [item for item in _as_list(resolved.get("items")) if isinstance(item, Mapping)]
    variance_rows = [item for item in _as_list(resolved.get("variance_rows")) if isinstance(item, Mapping)]
    competition_profiles = _as_mapping(resolved.get("competition_profiles"))
    bucket_profiles = _as_mapping(resolved.get("xg_margin_buckets"))
    sandbox_rows = [_statsbomb_sandbox_row(item, resolved) for item in item_rows]
    sandbox_rows.sort(
        key=lambda row: (
            "终结波动" not in str(row.get("diagnosis") or ""),
            -abs(_safe_float(row.get("xg_margin"))),
            str(row.get("match_date") or ""),
        )
    )
    competition_rows = [
        {
            "label": str(key),
            "body": (
                f"\u6837\u672c {_safe_int(_as_mapping(value).get('match_count'))} | "
                f"xG\u5bf9\u9f50 {_as_mapping(value).get('xg_alignment_rate') or '-'} | "
                f"\u7ec8\u7ed3\u6ce2\u52a8 {_as_mapping(value).get('finishing_variance_rate') or '-'} | "
                f"\u573a\u5747xG {_safe_float(_as_mapping(value).get('avg_xg_total')):.2f}"
            ),
        }
        for key, value in sorted(competition_profiles.items())
    ]
    bucket_rows = [
        {
            "label": str(key),
            "body": (
                f"\u6837\u672c {_safe_int(_as_mapping(value).get('match_count'))} | "
                f"xG\u5bf9\u9f50 {_as_mapping(value).get('xg_alignment_rate') or '-'} | "
                f"\u5c04\u95e8\u5bf9\u9f50 {_as_mapping(value).get('shot_alignment_rate') or '-'} | "
                f"\u7ec8\u7ed3\u6ce2\u52a8 {_as_mapping(value).get('finishing_variance_rate') or '-'}"
            ),
        }
        for key, value in sorted(bucket_profiles.items())
    ]
    sample_count = _safe_int(summary.get("match_count"), len(item_rows))
    return {
        "status": "ready" if item_rows else "empty",
        "sample_count": sample_count,
        "source": resolved.get("source") or "-",
        "updated_at": resolved.get("updated_at") or "-",
        "summary_text": (
            f"\u6837\u672c {sample_count} | xG\u5bf9\u9f50 {summary.get('xg_alignment_rate') or '-'} | "
            f"\u5c04\u95e8\u5bf9\u9f50 {summary.get('shot_alignment_rate') or '-'} | "
            f"\u7ec8\u7ed3\u6ce2\u52a8 {summary.get('finishing_variance_rate') or '-'}"
        ),
        "leakage_note": resolved.get("leakage_note") or "\u8be5\u6a21\u5757\u4ec5\u7528\u4e8e\u8d5b\u540e\u590d\u76d8\uff0c\u4e0d\u53c2\u4e0e\u8d5b\u524d\u9884\u6d4b\u8f93\u5165\u3002",
        "competition_rows": competition_rows,
        "bucket_rows": bucket_rows,
        "rows": sandbox_rows[: max(0, int(limit))],
        "variance_rows": [_statsbomb_sandbox_row(item, resolved) for item in variance_rows][: max(0, int(limit))],
    }


def build_statsbomb_event_sandbox_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_event_sandbox_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_statsbomb_event_sandbox_report_lines(
    baseline: Mapping[str, object] | object,
    *,
    generated_at: datetime | None = None,
    limit: int = 20,
) -> list[str]:
    current = generated_at or datetime.now()
    sandbox = build_statsbomb_event_sandbox_summary(baseline, limit=limit)
    lines = [
        "# StatsBomb \u5386\u53f2\u4e8b\u4ef6\u590d\u76d8\u6c99\u76d2",
        "",
        f"- \u751f\u6210\u65f6\u95f4: {current.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- \u6570\u636e\u6e90: {sandbox.get('source', '-')}",
        f"- \u57fa\u7ebf\u66f4\u65b0: {sandbox.get('updated_at', '-')}",
        f"- \u6458\u8981: {sandbox.get('summary_text', '-')}",
        f"- \u9632\u6cc4\u6f0f\u8fb9\u754c: {sandbox.get('leakage_note', '-')}",
        "",
        "## \u8d5b\u4e8b\u57fa\u7ebf",
        "",
        "| \u8d5b\u4e8b | \u6458\u8981 |",
        "| --- | --- |",
    ]
    competition_rows = [row for row in _as_list(sandbox.get("competition_rows")) if isinstance(row, Mapping)]
    if competition_rows:
        for row in competition_rows:
            lines.append(f"| {_md_cell(row.get('label'))} | {_md_cell(row.get('body'))} |")
    else:
        lines.append("| - | \u6682\u65e0\u8d5b\u4e8b\u57fa\u7ebf |")
    lines.extend(
        [
            "",
            "## xG\u5dee\u503c\u5206\u6876",
            "",
            "| \u5206\u6876 | \u6458\u8981 |",
            "| --- | --- |",
        ]
    )
    bucket_rows = [row for row in _as_list(sandbox.get("bucket_rows")) if isinstance(row, Mapping)]
    if bucket_rows:
        for row in bucket_rows:
            lines.append(f"| {_md_cell(row.get('label'))} | {_md_cell(row.get('body'))} |")
    else:
        lines.append("| - | \u6682\u65e0xG\u5206\u6876 |")
    lines.extend(
        [
            "",
            "## Evaluation Agent \u6a21\u62df\u590d\u76d8\u6848\u4f8b",
            "",
            "| \u65e5\u671f | \u8d5b\u4e8b | \u5bf9\u9635 | \u6bd4\u5206 | xG | \u8bca\u65ad | Evaluation | \u4e3b\u9519\u56e0 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    rows = [row for row in _as_list(sandbox.get("variance_rows")) if isinstance(row, Mapping)]
    if not rows:
        rows = [row for row in _as_list(sandbox.get("rows")) if isinstance(row, Mapping)]
    if not rows:
        lines.append("| - | - | - | - | - | - | - | - |")
    for row in rows[: max(0, int(limit))]:
        case = _as_mapping(row.get("evaluation_case"))
        evaluation = _as_mapping(case.get("evaluation"))
        attribution = _as_mapping(evaluation.get("error_attribution"))
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("match_date")),
                    _md_cell(row.get("league")),
                    _md_cell(row.get("title")),
                    _md_cell(row.get("score")),
                    _md_cell(row.get("xg")),
                    _md_cell(row.get("diagnosis")),
                    _md_cell(f"{evaluation.get('status', '-')} / {evaluation.get('score', '-')}"),
                    _md_cell(attribution.get("top_reason")),
                ]
            )
            + " |"
        )
    lines.extend(["", "## \u6848\u4f8b\u8be6\u60c5", ""])
    for index, row in enumerate(rows[: max(0, int(limit))], start=1):
        case = _as_mapping(row.get("evaluation_case"))
        lines.extend(
            [
                f"### {index}. {_text(row.get('title'))}",
                "",
                f"- \u65e5\u671f: {_text(row.get('match_date'))}",
                f"- \u8d5b\u4e8b: {_text(row.get('league'))}",
                f"- \u6bd4\u5206 / xG / \u5c04\u95e8: {_text(row.get('score'))} / {_text(row.get('xg'))} / {_text(row.get('shots'))}",
                f"- \u6837\u672c\u8bca\u65ad: {_text(row.get('diagnosis'))}",
                "",
                "```text",
                _text(case.get("body")),
                "```",
                "",
            ]
        )
    return lines


def _strategy_error_codes(settlement: Mapping[str, object], item: Mapping[str, object]) -> list[str]:
    if item.get("is_hit") is None:
        return ["data_missing"]
    if item.get("is_hit") is not False:
        return []
    codes: list[str] = []
    pick = str(item.get("pick") or "").strip()
    actual = str(item.get("actual") or "").strip()
    if not pick or not actual or pick == "-" or actual == "-":
        codes.append("data_missing")
    confidence = _safe_float(item.get("confidence"))
    min_confidence = _safe_float(item.get("min_confidence"))
    if confidence >= max(0.65, min_confidence):
        codes.append("high_confidence_miss")
    backtest_accuracy = _safe_float(item.get("backtest_accuracy") or item.get("accuracy"))
    if backtest_accuracy >= 0.68:
        codes.append("historical_gap")
    sample_count = _safe_int(item.get("backtest_samples") or item.get("sample_count"))
    if sample_count and sample_count < 120:
        codes.append("small_sample")
    if bool(item.get("is_shadow")) or bool(item.get("blocked_by_breaker")):
        codes.append("shadow_observation")
    if _is_jc_bucket_item(item):
        feedback = _as_mapping(item.get("jc_live_feedback"))
        bucket = _as_mapping(item.get("jc_bucket"))
        status = str(feedback.get("status") or "").lower()
        if status == "downgraded" or str(item.get("breaker_status") or "").lower() == "jc_live_downgraded":
            codes.append("jc_live_downgraded")
        wilson = _safe_float(feedback.get("historical_wilson_lower", bucket.get("wilson_lower")))
        live_rate = feedback.get("live_hit_rate")
        if live_rate is not None and _safe_float(live_rate) < wilson:
            codes.append("jc_wilson_breach")
        deviation = feedback.get("deviation")
        if deviation is not None and _safe_float(deviation) <= -0.10:
            codes.append("historical_gap")
        context = _as_mapping(item.get("jc_context"))
        live_odds = context.get("pick_odds")
        historical_odds = bucket.get("avg_pick_odds")
        if live_odds not in (None, "") and historical_odds not in (None, "") and abs(_safe_float(live_odds) - _safe_float(historical_odds)) >= 0.25:
            codes.append("jc_odds_drift")
        historical_confidence = bucket.get("avg_confidence")
        if historical_confidence not in (None, "") and confidence + 0.05 < _safe_float(historical_confidence):
            codes.append("jc_confidence_drift")
    statsbomb_evidence = _statsbomb_event_evidence(settlement, item)
    for code in _as_list(statsbomb_evidence.get("codes")):
        codes.append(str(code))
    if not codes:
        codes.append("unknown")
    deduped: list[str] = []
    for code in codes:
        if code not in deduped:
            deduped.append(code)
    return deduped


def build_strategy_error_attribution_summary(
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    limit: int = 8,
) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    rows: list[dict[str, str]] = []
    counts: dict[str, int] = {}
    miss_count = 0
    unknown_count = 0
    for settlement, item in _known_strategy_settlement_items(settlement_items):
        codes = _strategy_error_codes(settlement, item)
        if item.get("is_hit") is False:
            miss_count += 1
        elif item.get("is_hit") is None:
            unknown_count += 1
        else:
            continue
        for code in codes:
            counts[code] = counts.get(code, 0) + 1
        if item.get("is_hit") is False:
            labels = [ERROR_ATTRIBUTION_LABELS.get(code, code) for code in codes]
            labels_text = "\u3001".join(labels)
            statsbomb_evidence = _statsbomb_event_evidence(settlement, item)
            evidence_body = str(statsbomb_evidence.get("body") or "")
            base_body = (
                f"\u73a9\u6cd5: {_label(PLAY_LABELS, item.get('play_type'))} | \u9884\u6d4b {item.get('pick') or '-'} / \u5b9e\u9645 {item.get('actual') or '-'}\n"
                f"\u9519\u56e0: {labels_text}\n"
                f"\u7f6e\u4fe1: {_pct(item.get('confidence'))} | \u56de\u6d4b {_pct(item.get('backtest_accuracy') or item.get('accuracy'))} | \u6837\u672c {_safe_int(item.get('backtest_samples') or item.get('sample_count'))}"
            )
            if evidence_body:
                base_body = f"{base_body}\n{evidence_body}"
            rows.append(
                {
                    "title": f"{settlement.get('league') or '-'} | {settlement.get('home_team') or '-'} vs {settlement.get('away_team') or '-'}",
                    "body": base_body,
                }
            )
    ranked = sorted(counts.items(), key=lambda item: (-item[1], ERROR_ATTRIBUTION_LABELS.get(item[0], item[0])))
    top_reason = "-"
    if ranked:
        top_reason = f"{ERROR_ATTRIBUTION_LABELS.get(ranked[0][0], ranked[0][0])} {ranked[0][1]}\u6b21"
    return {
        "miss_count": miss_count,
        "unknown_count": unknown_count,
        "reason_counts": dict(ranked),
        "top_reason": top_reason,
        "rows": rows[: max(0, int(limit))],
        "summary_text": f"\u9519\u56e0 {miss_count}\u9879 | \u4e3b\u56e0 {top_reason}",
    }


def build_agent_trace_replay_summary(
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    limit: int = 8,
) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    known = [
        item
        for item in settlement_items
        if isinstance(item.get("supervisor_agent_statuses"), Mapping)
        and (item.get("is_correct") is not None or item.get("handicap_is_correct") is not None)
    ]
    agent_rows: dict[str, dict[str, object]] = {}
    action_counts: dict[str, int] = {}
    for item in known:
        statuses = _as_mapping(item.get("supervisor_agent_statuses"))
        actions = item.get("supervisor_agent_actions") if isinstance(item.get("supervisor_agent_actions"), list) else []
        for action in actions:
            key = str(action)
            action_counts[key] = _safe_int(action_counts.get(key)) + 1
        for agent_name, status_value in statuses.items():
            status = _text(status_value).lower()
            if status not in {"alert", "watch", "blocked"}:
                continue
            name = str(agent_name)
            row = agent_rows.setdefault(
                name,
                {
                    "agent": name,
                    "trigger_count": 0,
                    "alert_count": 0,
                    "watch_count": 0,
                    "blocked_count": 0,
                    "prediction_known": 0,
                    "prediction_miss": 0,
                    "handicap_known": 0,
                    "handicap_miss": 0,
                    "actions": {},
                },
            )
            row["trigger_count"] = _safe_int(row.get("trigger_count")) + 1
            if status == "alert":
                row["alert_count"] = _safe_int(row.get("alert_count")) + 1
            elif status == "watch":
                row["watch_count"] = _safe_int(row.get("watch_count")) + 1
            elif status == "blocked":
                row["blocked_count"] = _safe_int(row.get("blocked_count")) + 1
            if item.get("is_correct") is not None:
                row["prediction_known"] = _safe_int(row.get("prediction_known")) + 1
                row["prediction_miss"] = _safe_int(row.get("prediction_miss")) + (1 if item.get("is_correct") is False else 0)
            if item.get("handicap_is_correct") is not None:
                row["handicap_known"] = _safe_int(row.get("handicap_known")) + 1
                row["handicap_miss"] = _safe_int(row.get("handicap_miss")) + (1 if item.get("handicap_is_correct") is False else 0)
            row_actions = row.get("actions")
            if not isinstance(row_actions, dict):
                row_actions = {}
                row["actions"] = row_actions
            for action in actions:
                key = str(action)
                row_actions[key] = _safe_int(row_actions.get(key)) + 1

    rows: list[dict[str, object]] = []
    for row in agent_rows.values():
        prediction_known = _safe_int(row.get("prediction_known"))
        handicap_known = _safe_int(row.get("handicap_known"))
        prediction_miss_rate = _safe_int(row.get("prediction_miss")) / prediction_known if prediction_known else None
        handicap_miss_rate = _safe_int(row.get("handicap_miss")) / handicap_known if handicap_known else None
        row_actions = row.get("actions") if isinstance(row.get("actions"), dict) else {}
        top_action = "-"
        if row_actions:
            top_action = sorted(row_actions.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))[0][0]
        rows.append(
            {
                **row,
                "prediction_miss_rate": prediction_miss_rate,
                "prediction_miss_rate_text": _pct(prediction_miss_rate),
                "handicap_miss_rate": handicap_miss_rate,
                "handicap_miss_rate_text": _pct(handicap_miss_rate),
                "top_action": top_action,
            }
        )
    rows.sort(
        key=lambda row: (
            -_safe_int(row.get("alert_count")) - _safe_int(row.get("blocked_count")),
            -_safe_float(row.get("prediction_miss_rate"), 0.0),
            -_safe_float(row.get("handicap_miss_rate"), 0.0),
            str(row.get("agent") or ""),
        )
    )
    top_agent = rows[0].get("agent") if rows else "-"
    top_action = "-"
    if action_counts:
        top_action = sorted(action_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))[0][0]
    return {
        "sample_count": len(known),
        "agent_count": len(rows),
        "top_agent": top_agent,
        "top_action": top_action,
        "rows": rows[: max(0, int(limit))],
        "summary_text": f"样本 {len(known)} | 风险Agent {len(rows)} | 最高关联 {top_agent} | 主要动作 {top_action}",
    }


def build_agent_replay_downgrade_backtest_summary(
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    limit: int = 8,
) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    known = [
        item
        for item in settlement_items
        if _safe_bool(item.get("agent_replay_guard_applied"))
        and (item.get("is_correct") is not None or item.get("handicap_is_correct") is not None)
    ]
    by_agent: dict[str, dict[str, object]] = {}
    for item in known:
        agent = _text(item.get("agent_replay_guard_top_agent"), "unknown")
        row = by_agent.setdefault(
            agent,
            {
                "agent": agent,
                "count": 0,
                "prediction_known": 0,
                "prediction_avoided_misses": 0,
                "prediction_opportunity_cost": 0,
                "handicap_known": 0,
                "handicap_avoided_misses": 0,
                "handicap_opportunity_cost": 0,
                "actions": {},
            },
        )
        row["count"] = _safe_int(row.get("count")) + 1
        if item.get("is_correct") is not None:
            row["prediction_known"] = _safe_int(row.get("prediction_known")) + 1
            if item.get("is_correct") is False:
                row["prediction_avoided_misses"] = _safe_int(row.get("prediction_avoided_misses")) + 1
            else:
                row["prediction_opportunity_cost"] = _safe_int(row.get("prediction_opportunity_cost")) + 1
        if item.get("handicap_is_correct") is not None:
            row["handicap_known"] = _safe_int(row.get("handicap_known")) + 1
            if item.get("handicap_is_correct") is False:
                row["handicap_avoided_misses"] = _safe_int(row.get("handicap_avoided_misses")) + 1
            else:
                row["handicap_opportunity_cost"] = _safe_int(row.get("handicap_opportunity_cost")) + 1
        row_actions = row.get("actions") if isinstance(row.get("actions"), dict) else {}
        row["actions"] = row_actions
        actions = item.get("agent_replay_guard_actions") if isinstance(item.get("agent_replay_guard_actions"), list) else []
        for action in actions:
            key = str(action)
            row_actions[key] = _safe_int(row_actions.get(key)) + 1

    rows: list[dict[str, object]] = []
    for row in by_agent.values():
        prediction_known = _safe_int(row.get("prediction_known"))
        handicap_known = _safe_int(row.get("handicap_known"))
        prediction_net = _safe_int(row.get("prediction_avoided_misses")) - _safe_int(row.get("prediction_opportunity_cost"))
        handicap_net = _safe_int(row.get("handicap_avoided_misses")) - _safe_int(row.get("handicap_opportunity_cost"))
        actions = row.get("actions") if isinstance(row.get("actions"), dict) else {}
        top_action = "-"
        if actions:
            top_action = sorted(actions.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))[0][0]
        rows.append(
            {
                **row,
                "prediction_avoid_rate": (
                    _safe_int(row.get("prediction_avoided_misses")) / prediction_known if prediction_known else None
                ),
                "prediction_avoid_rate_text": _pct(_safe_int(row.get("prediction_avoided_misses")) / prediction_known) if prediction_known else "-",
                "prediction_net": prediction_net,
                "handicap_avoid_rate": (
                    _safe_int(row.get("handicap_avoided_misses")) / handicap_known if handicap_known else None
                ),
                "handicap_avoid_rate_text": _pct(_safe_int(row.get("handicap_avoided_misses")) / handicap_known) if handicap_known else "-",
                "handicap_net": handicap_net,
                "top_action": top_action,
            }
        )
    rows.sort(
        key=lambda row: (
            -_safe_int(row.get("prediction_net")) - _safe_int(row.get("handicap_net")),
            -_safe_int(row.get("count")),
            str(row.get("agent") or ""),
        )
    )
    sample_count = len(known)
    prediction_known_total = sum(1 for item in known if item.get("is_correct") is not None)
    prediction_avoided = sum(1 for item in known if item.get("is_correct") is False)
    prediction_cost = sum(1 for item in known if item.get("is_correct") is True)
    handicap_known_total = sum(1 for item in known if item.get("handicap_is_correct") is not None)
    handicap_avoided = sum(1 for item in known if item.get("handicap_is_correct") is False)
    handicap_cost = sum(1 for item in known if item.get("handicap_is_correct") is True)
    net = (prediction_avoided - prediction_cost) + (handicap_avoided - handicap_cost)
    if sample_count < 5:
        recommendation = "collecting"
        recommendation_text = "Agent Replay 降级样本不足，继续观察。"
    elif net > 0:
        recommendation = "keep_guard"
        recommendation_text = "Agent Replay 降级的理论净收益为正，建议继续保留观察降级。"
    elif net < 0:
        recommendation = "review_guard"
        recommendation_text = "Agent Replay 降级机会成本偏高，建议复核触发门槛。"
    else:
        recommendation = "monitor"
        recommendation_text = "Agent Replay 降级收益与成本接近，继续监控。"
    return {
        "sample_count": sample_count,
        "prediction_known": prediction_known_total,
        "prediction_avoided_misses": prediction_avoided,
        "prediction_opportunity_cost": prediction_cost,
        "prediction_net": prediction_avoided - prediction_cost,
        "handicap_known": handicap_known_total,
        "handicap_avoided_misses": handicap_avoided,
        "handicap_opportunity_cost": handicap_cost,
        "handicap_net": handicap_avoided - handicap_cost,
        "net": net,
        "rows": rows[: max(0, int(limit))],
        "recommendation": recommendation,
        "recommendation_text": recommendation_text,
        "summary_text": (
            f"样本 {sample_count} | 1X2避错 {prediction_avoided}/成本 {prediction_cost} | "
            f"让球避错 {handicap_avoided}/成本 {handicap_cost} | 净值 {net:+d}"
        ),
    }


def build_agent_replay_guard_tuning_recommendation(
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    base_min_samples: int = 5,
    base_prediction_miss_threshold: float = 0.55,
    base_handicap_miss_threshold: float = 0.60,
) -> dict[str, object]:
    summary = build_agent_replay_downgrade_backtest_summary(settlements)
    sample_count = _safe_int(summary.get("sample_count"))
    net = _safe_int(summary.get("net"))
    prediction_net = _safe_int(summary.get("prediction_net"))
    handicap_net = _safe_int(summary.get("handicap_net"))
    min_samples = max(3, min(20, _safe_int(base_min_samples, 5)))
    prediction_threshold = max(0.45, min(0.80, _safe_float(base_prediction_miss_threshold, 0.55)))
    handicap_threshold = max(0.45, min(0.85, _safe_float(base_handicap_miss_threshold, 0.60)))
    next_min_samples = min_samples
    next_prediction_threshold = prediction_threshold
    next_handicap_threshold = handicap_threshold
    action = "collect"
    label = "\u7ee7\u7eed\u79ef\u7d2f\u6837\u672c"
    tone = "neutral"
    reasons: list[str] = []

    if sample_count < 8:
        reasons.append(f"Replay Guard \u5df2\u7ed3\u7b97\u6837\u672c {sample_count} \u573a\uff0c\u6682\u4e0d\u6839\u636e\u5c0f\u6837\u672c\u6539\u53d8\u89e6\u53d1\u95e8\u69db\u3002")
    elif net >= 3:
        action = "tighten_guard"
        label = "\u6536\u7d27 Replay Guard"
        tone = "good"
        if prediction_net > 0:
            next_prediction_threshold = max(0.45, prediction_threshold - 0.03)
        if handicap_net > 0:
            next_handicap_threshold = max(0.45, handicap_threshold - 0.03)
        reasons.append(f"Replay Guard \u7406\u8bba\u51c0\u503c {net:+d}\uff0c\u964d\u7ea7\u5e2e\u52a9\u56de\u907f\u7684\u9519\u8bef\u5927\u4e8e\u673a\u4f1a\u6210\u672c\u3002")
    elif net <= -2:
        action = "loosen_guard"
        label = "\u653e\u5bbd Replay Guard"
        tone = "warning"
        next_min_samples = min(20, min_samples + 1)
        next_prediction_threshold = min(0.80, prediction_threshold + 0.03)
        next_handicap_threshold = min(0.85, handicap_threshold + 0.03)
        reasons.append(f"Replay Guard \u7406\u8bba\u51c0\u503c {net:+d}\uff0c\u673a\u4f1a\u6210\u672c\u9ad8\u4e8e\u53ef\u56de\u907f\u9519\u8bef\u3002")
    elif net > 0:
        action = "keep_guard"
        label = "\u4fdd\u6301 Replay Guard"
        tone = "good"
        reasons.append(f"Replay Guard \u51c0\u503c {net:+d}\uff0c\u5df2\u4e3a\u6b63\u4f46\u5c1a\u672a\u8fbe\u5230\u81ea\u52a8\u6536\u7d27\u6761\u4ef6\u3002")
    else:
        action = "monitor"
        label = "\u7ee7\u7eed\u89c2\u5bdf"
        tone = "neutral"
        reasons.append("Replay Guard \u51c0\u503c\u63a5\u8fd1 0\uff0c\u5efa\u8bae\u4fdd\u6301\u73b0\u6709\u95e8\u69db\u5e76\u7ee7\u7eed\u56de\u6536\u8d5b\u679c\u3002")

    next_prediction_threshold = round(next_prediction_threshold, 2)
    next_handicap_threshold = round(next_handicap_threshold, 2)
    policy_update = {
        "agent_replay_guard_enabled": True,
        "agent_replay_min_samples": next_min_samples,
        "agent_replay_prediction_miss_threshold": next_prediction_threshold,
        "agent_replay_handicap_miss_threshold": next_handicap_threshold,
    }
    if action in {"collect", "keep_guard", "monitor"}:
        policy_update = {}
    rows = [
        ("\u52a8\u4f5c", label),
        ("\u56de\u6d4b\u51c0\u503c", f"{net:+d} | 1X2 {prediction_net:+d} / \u8ba9\u7403 {handicap_net:+d}"),
        ("\u6837\u672c", f"{sample_count} \u573a | {summary.get('summary_text', '-')}"),
        ("\u89e6\u53d1\u6837\u672c", f"{min_samples} -> {next_min_samples}"),
        ("\u80dc\u5e73\u8d1f\u5931\u8bef\u7ebf", f"{prediction_threshold:.2f} -> {next_prediction_threshold:.2f}"),
        ("\u8ba9\u7403\u5931\u8bef\u7ebf", f"{handicap_threshold:.2f} -> {next_handicap_threshold:.2f}"),
        ("\u8c03\u6574\u4f9d\u636e", "\n".join(reasons) if reasons else "-"),
    ]
    return {
        "action": action,
        "label": label,
        "tone": tone,
        "sample_count": sample_count,
        "net": net,
        "next_min_samples": next_min_samples,
        "next_prediction_miss_threshold": next_prediction_threshold,
        "next_handicap_miss_threshold": next_handicap_threshold,
        "policy_update": policy_update,
        "reasons": reasons,
        "rows": rows,
        "summary": summary,
    }


def _parse_policy_review_time(value: object) -> datetime | None:
    text = _text(value, "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            try:
                return datetime.strptime(text[:10], fmt)
            except Exception:
                continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _settlement_review_time(item: Mapping[str, object]) -> datetime | None:
    for key in ("settled_at", "timestamp", "updated_at", "match_date"):
        parsed = _parse_policy_review_time(item.get(key))
        if parsed is not None:
            return parsed
    return None


def _policy_effect_settlement_title(item: Mapping[str, object]) -> str:
    league = _text(item.get("league"), "-")
    home = _text(item.get("home_team"), "-")
    away = _text(item.get("away_team"), "-")
    return f"{league} | {home} vs {away}"


def _policy_effect_bool_label(value: object) -> str:
    if value is True:
        return "\u547d\u4e2d"
    if value is False:
        return "\u5931\u8bef"
    return "\u672a\u5224\u5b9a"


def _policy_effect_drag_reasons(item: Mapping[str, object], replay_net_hint: int) -> list[str]:
    reasons: list[str] = []
    decision = str(item.get("strategy_admission_decision") or "").strip()
    if decision == "allow" and item.get("is_correct") is False:
        reasons.append("\u653e\u884c\u540e1X2\u5931\u8bef")
    if decision == "allow" and item.get("handicap_is_correct") is False:
        reasons.append("\u653e\u884c\u540e\u8ba9\u7403\u5931\u8bef")
    if bool(item.get("agent_replay_guard_applied")) and replay_net_hint < 0:
        reasons.append("Replay Guard\u673a\u4f1a\u6210\u672c")
    if bool(item.get("agent_replay_guard_applied")) and replay_net_hint > 0:
        reasons.append("Replay Guard\u56de\u907f\u9519\u8bef")
    return reasons


def _policy_effect_settlement_rows(items: Sequence[Mapping[str, object]], *, limit: int = 20) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    ordered = sorted(
        [item for item in items if isinstance(item, Mapping)],
        key=lambda item: _settlement_review_time(item) or datetime.min,
        reverse=True,
    )
    for item in ordered[: max(0, int(limit))]:
        replay_applied = bool(item.get("agent_replay_guard_applied"))
        replay_agent = _text(item.get("agent_replay_guard_top_agent"), "-")
        replay_net_hint = 0
        if replay_applied:
            if item.get("is_correct") is False:
                replay_net_hint += 1
            elif item.get("is_correct") is True:
                replay_net_hint -= 1
            if item.get("handicap_is_correct") is False:
                replay_net_hint += 1
            elif item.get("handicap_is_correct") is True:
                replay_net_hint -= 1
        drag_reasons = _policy_effect_drag_reasons(item, replay_net_hint)
        drag_score = 0
        if "\u653e\u884c\u540e1X2\u5931\u8bef" in drag_reasons:
            drag_score += 2
        if "\u653e\u884c\u540e\u8ba9\u7403\u5931\u8bef" in drag_reasons:
            drag_score += 1
        if "Replay Guard\u673a\u4f1a\u6210\u672c" in drag_reasons:
            drag_score += abs(replay_net_hint)
        elif replay_net_hint < 0:
            drag_score += abs(replay_net_hint)
        rows.append(
            {
                "match_id": _text(item.get("match_id"), "-"),
                "time": _text(item.get("settled_at") or item.get("timestamp") or item.get("match_date"), "-"),
                "title": _policy_effect_settlement_title(item),
                "league": _text(item.get("league"), "-"),
                "home_team": _text(item.get("home_team"), "-"),
                "away_team": _text(item.get("away_team"), "-"),
                "decision": _text(item.get("strategy_admission_decision"), "-"),
                "prediction_result": _policy_effect_bool_label(item.get("is_correct")),
                "handicap_result": _policy_effect_bool_label(item.get("handicap_is_correct")),
                "replay_guard": "\u89e6\u53d1" if replay_applied else "\u672a\u89e6\u53d1",
                "replay_agent": replay_agent,
                "replay_net_hint": replay_net_hint,
                "drag_score": drag_score,
                "drag_reasons": drag_reasons,
                "drag_reason_text": "\u3001".join(drag_reasons) if drag_reasons else "-",
                "summary": (
                    f"{_policy_effect_settlement_title(item)} | "
                    f"\u51c6\u5165 {_text(item.get('strategy_admission_decision'), '-')} | "
                    f"1X2 {_policy_effect_bool_label(item.get('is_correct'))} | "
                    f"\u8ba9\u7403 {_policy_effect_bool_label(item.get('handicap_is_correct'))} | "
                    f"Replay {'ON' if replay_applied else 'OFF'} {replay_agent}"
                ),
            }
        )
    return rows


def _policy_effect_negative_diagnostics(
    sample_rows: Sequence[Mapping[str, object]],
    *,
    effect_status: str,
    allow_hit_rate: float | None,
    replay_net: int,
) -> dict[str, object]:
    negative_rows = [dict(row) for row in sample_rows if _safe_int(row.get("drag_score")) > 0]
    negative_rows.sort(
        key=lambda row: (
            -_safe_int(row.get("drag_score")),
            _safe_float(row.get("replay_net_hint"), 0.0),
            str(row.get("time") or ""),
        )
    )
    reason_counts: dict[str, int] = {}
    for row in negative_rows:
        for reason in row.get("drag_reasons", []) if isinstance(row.get("drag_reasons"), list) else []:
            key = _text(reason, "-")
            reason_counts[key] = reason_counts.get(key, 0) + 1
    top_reason = "-"
    if reason_counts:
        top_reason = sorted(reason_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))[0][0]
    rollback_recommended = (
        effect_status == "negative"
        and (
            (allow_hit_rate is not None and allow_hit_rate < 0.55)
            or replay_net < 0
            or len(negative_rows) >= 2
        )
    )
    if rollback_recommended:
        action_label = "\u5efa\u8bae\u590d\u6838\u56de\u6eda"
    elif effect_status == "negative":
        action_label = "\u5efa\u8bae\u4eba\u5de5\u590d\u6838"
    else:
        action_label = "\u6682\u65e0\u56de\u6eda\u5efa\u8bae"
    return {
        "top_negative_rows": negative_rows[:5],
        "negative_count": len(negative_rows),
        "negative_reason_counts": reason_counts,
        "top_negative_reason": top_reason,
        "rollback_recommended": rollback_recommended,
        "action_label": action_label,
        "summary_text": (
            f"{action_label} | \u4e3b\u56e0 {top_reason} | "
            f"\u62d6\u7d2f\u6837\u672c {len(negative_rows)} | Replay\u51c0\u503c {replay_net:+d}"
        ),
    }


def _policy_effect_stability_tone(status: str) -> str:
    if status in {"improving", "stable"}:
        return "good"
    if status in {"regression", "volatile"}:
        return "bad"
    if status == "watch":
        return "warning"
    return "neutral"


def _policy_effect_stability_label(status: str) -> str:
    labels = {
        "improving": "\u8d8b\u52bf\u6539\u5584",
        "stable": "\u7a33\u5b9a\u751f\u6548",
        "watch": "\u9700\u89c2\u5bdf",
        "regression": "\u51fa\u73b0\u56de\u9000",
        "volatile": "\u6ce2\u52a8\u8fc7\u5927",
        "collecting": "\u6837\u672c\u79ef\u7d2f\u4e2d",
        "none": "\u6682\u65e0\u7248\u672c",
    }
    return labels.get(status, "\u9700\u89c2\u5bdf")


def _policy_effect_stability_recommendation(status: str) -> str:
    if status == "improving":
        return "\u6700\u8fd1\u7248\u672c\u5448\u6b63\u5411\u6539\u5584\uff0c\u7ee7\u7eed\u6309\u5f53\u524d\u95e8\u69db\u6536\u96c6\u8d5b\u679c\u3002"
    if status == "stable":
        return "\u7b56\u7565\u53c2\u6570\u5df2\u8fdb\u5165\u7a33\u5b9a\u89c2\u5bdf\uff0c\u4e0d\u5efa\u8bae\u9891\u7e41\u518d\u8c03\u53c2\u3002"
    if status == "regression":
        return "\u6700\u65b0\u7248\u672c\u51fa\u73b0\u56de\u9000\uff0c\u4f18\u5148\u590d\u6838\u8d1f\u5411\u6837\u672c\uff0c\u5fc5\u8981\u65f6\u56de\u6eda\u4e0a\u4e00\u7248\u3002"
    if status == "volatile":
        return "\u7248\u672c\u95f4\u547d\u4e2d\u6ce2\u52a8\u504f\u5927\uff0c\u5efa\u8bae\u5ef6\u957f\u89c2\u5bdf\u7a97\u53e3\uff0c\u907f\u514d\u8fde\u7eed\u81ea\u52a8\u6536\u7d27\u6216\u653e\u5bbd\u3002"
    if status == "watch":
        return "\u5df2\u6709\u8d1f\u5411\u4fe1\u53f7\uff0c\u5148\u4fdd\u6301\u89c2\u5bdf\uff0c\u7b49\u5f85\u66f4\u591a\u53ef\u56de\u6536\u6837\u672c\u786e\u8ba4\u3002"
    return "\u5f53\u524d\u6837\u672c\u4e0d\u8db3\uff0c\u6682\u4e0d\u5efa\u8bae\u6839\u636e\u8be5\u76d1\u63a7\u7ed3\u679c\u8c03\u53c2\u3002"


def build_strategy_policy_stability_monitor(policy_effect_review: Mapping[str, object] | object) -> dict[str, object]:
    review = _as_mapping(policy_effect_review)
    rows = [dict(row) for row in _as_list(review.get("rows")) if isinstance(row, Mapping)]
    rows.sort(key=lambda row: _parse_policy_review_time(row.get("updated_at")) or datetime.min)
    evaluated = [
        row
        for row in rows
        if str(row.get("effect_status") or "") != "collecting"
        and row.get("allow_hit_rate") is not None
        and _safe_int(row.get("known_allow_count")) > 0
    ]
    status_counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("effect_status") or "unknown")
        status_counts[key] = status_counts.get(key, 0) + 1

    rates = [_safe_float(row.get("allow_hit_rate")) for row in evaluated]
    deltas = [rates[index] - rates[index - 1] for index in range(1, len(rates))]
    latest = rows[-1] if rows else {}
    latest_status = str(latest.get("effect_status") or "none")
    latest_delta = deltas[-1] if deltas else None
    avg_abs_delta = sum(abs(item) for item in deltas) / len(deltas) if deltas else 0.0
    cumulative_replay_net = sum(_safe_int(row.get("replay_guard_net")) for row in rows)

    negative_streak = 0
    effective_streak = 0
    for row in reversed(rows):
        status = str(row.get("effect_status") or "")
        if status == "negative" and effective_streak == 0:
            negative_streak += 1
            continue
        if status == "effective" and negative_streak == 0:
            effective_streak += 1
            continue
        break

    if not rows:
        stability_status = "none"
    elif len(evaluated) < 2:
        stability_status = "collecting"
    elif negative_streak >= 2 or (latest_status == "negative" and latest_delta is not None and latest_delta <= -0.05):
        stability_status = "regression"
    elif avg_abs_delta >= 0.12 and status_counts.get("negative", 0) and status_counts.get("effective", 0):
        stability_status = "volatile"
    elif effective_streak >= 2 or (latest_status == "effective" and latest_delta is not None and latest_delta >= 0):
        stability_status = "improving"
    elif latest_status == "effective":
        stability_status = "stable"
    elif latest_status == "negative":
        stability_status = "watch"
    else:
        stability_status = "collecting"

    week_groups: dict[str, dict[str, object]] = {}
    for row in rows:
        updated_at = _parse_policy_review_time(row.get("updated_at"))
        if updated_at is None:
            week_label = "\u672a\u77e5\u5468\u671f"
        else:
            iso = updated_at.isocalendar()
            week_label = f"{iso.year}-W{iso.week:02d}"
        bucket = week_groups.setdefault(
            week_label,
            {
                "week": week_label,
                "version_count": 0,
                "sample_count": 0,
                "known_allow_count": 0,
                "allow_hits": 0,
                "replay_guard_net": 0,
                "effective_count": 0,
                "negative_count": 0,
                "collecting_count": 0,
            },
        )
        bucket["version_count"] = _safe_int(bucket.get("version_count")) + 1
        bucket["sample_count"] = _safe_int(bucket.get("sample_count")) + _safe_int(row.get("sample_count"))
        known_allow_count = _safe_int(row.get("known_allow_count"))
        bucket["known_allow_count"] = _safe_int(bucket.get("known_allow_count")) + known_allow_count
        if row.get("allow_hit_rate") is not None and known_allow_count:
            bucket["allow_hits"] = _safe_int(bucket.get("allow_hits")) + round(_safe_float(row.get("allow_hit_rate")) * known_allow_count)
        bucket["replay_guard_net"] = _safe_int(bucket.get("replay_guard_net")) + _safe_int(row.get("replay_guard_net"))
        status = str(row.get("effect_status") or "collecting")
        if status == "effective":
            bucket["effective_count"] = _safe_int(bucket.get("effective_count")) + 1
        elif status == "negative":
            bucket["negative_count"] = _safe_int(bucket.get("negative_count")) + 1
        elif status == "collecting":
            bucket["collecting_count"] = _safe_int(bucket.get("collecting_count")) + 1

    weekly_rows: list[dict[str, object]] = []
    for bucket in week_groups.values():
        known_allow_count = _safe_int(bucket.get("known_allow_count"))
        allow_hits = _safe_int(bucket.get("allow_hits"))
        hit_rate = allow_hits / known_allow_count if known_allow_count else None
        weekly_rows.append(
            {
                **bucket,
                "allow_hit_rate": hit_rate,
                "allow_hit_rate_text": _pct(hit_rate) if hit_rate is not None else "-",
                "title": (
                    f"{bucket.get('week')} | \u7248\u672c {bucket.get('version_count')} | "
                    f"\u547d\u4e2d {allow_hits}/{known_allow_count if known_allow_count else 0}"
                ),
                "body": (
                    f"\u6837\u672c {_safe_int(bucket.get('sample_count'))} | "
                    f"Replay\u51c0\u503c {_safe_int(bucket.get('replay_guard_net')):+d} | "
                    f"\u6b63\u5411 {_safe_int(bucket.get('effective_count'))} / "
                    f"\u8d1f\u5411 {_safe_int(bucket.get('negative_count'))} / "
                    f"\u79ef\u7d2f {_safe_int(bucket.get('collecting_count'))}"
                ),
            }
        )
    weekly_rows.sort(key=lambda row: str(row.get("week") or ""), reverse=True)

    latest_rate_text = _pct(rates[-1]) if rates else "-"
    delta_text = f"{latest_delta:+.1%}" if latest_delta is not None else "-"
    label = _policy_effect_stability_label(stability_status)
    return {
        "status": stability_status,
        "label": label,
        "tone": _policy_effect_stability_tone(stability_status),
        "version_count": len(rows),
        "evaluated_count": len(evaluated),
        "latest_status": latest_status,
        "latest_delta": latest_delta,
        "latest_delta_text": delta_text,
        "avg_abs_delta": avg_abs_delta,
        "avg_abs_delta_text": f"{avg_abs_delta:.1%}" if deltas else "-",
        "latest_allow_hit_rate_text": latest_rate_text,
        "cumulative_replay_net": cumulative_replay_net,
        "negative_streak": negative_streak,
        "effective_streak": effective_streak,
        "status_counts": status_counts,
        "weekly_rows": weekly_rows[:8],
        "recommendation_text": _policy_effect_stability_recommendation(stability_status),
        "summary_text": (
            f"{label} | \u6700\u65b0\u547d\u4e2d {latest_rate_text} | "
            f"\u73af\u6bd4 {delta_text} | \u7248\u672c {len(rows)} | Replay\u7d2f\u8ba1 {cumulative_replay_net:+d}"
        ),
    }


def build_strategy_policy_tuning_guard(
    stability_monitor: Mapping[str, object] | object,
    tuning: Mapping[str, object] | object | None = None,
    *,
    source: str = "",
) -> dict[str, object]:
    monitor = _as_mapping(stability_monitor)
    tuning_payload = _as_mapping(tuning)
    status = str(monitor.get("status") or "none")
    action = str(tuning_payload.get("action") or "").strip()
    source_label = {
        "strategy_allowlist_tuning": "\u653e\u884c\u95e8\u69db",
        "agent_replay_guard_tuning": "Replay Guard",
    }.get(source, "\u7b56\u7565\u8c03\u53c2")
    if status in {"regression", "volatile"}:
        decision = "block"
        label = "\u6682\u505c\u81ea\u52a8\u8c03\u53c2"
        tone = "bad"
        reasons = [
            f"\u7248\u672c\u7a33\u5b9a\u72b6\u6001: {monitor.get('label', '-')}",
            "\u6700\u65b0\u53c2\u6570\u6548\u679c\u5c1a\u672a\u7a33\u5b9a\uff0c\u7ee7\u7eed\u81ea\u52a8\u5199\u5165\u65b0\u53c2\u6570\u53ef\u80fd\u653e\u5927\u56de\u9000\u3002",
            "\u5efa\u8bae\u5148\u67e5\u770b\u751f\u6548\u8be6\u60c5\uff0c\u590d\u6838\u8d1f\u5411\u6837\u672c\uff0c\u5fc5\u8981\u65f6\u56de\u6eda\u4e0a\u4e00\u7248\u3002",
        ]
    elif status == "watch":
        decision = "confirm"
        label = "\u9700\u4eba\u5de5\u786e\u8ba4"
        tone = "warning"
        reasons = [
            f"\u7248\u672c\u7a33\u5b9a\u72b6\u6001: {monitor.get('label', '-')}",
            "\u5df2\u6709\u8d1f\u5411\u4fe1\u53f7\uff0c\u8c03\u53c2\u524d\u9700\u786e\u8ba4\u6837\u672c\u4e0d\u662f\u77ed\u671f\u566a\u58f0\u3002",
        ]
    else:
        decision = "allow"
        label = "\u5141\u8bb8\u8c03\u53c2"
        tone = "good" if status in {"improving", "stable"} else "neutral"
        reasons = [f"\u7248\u672c\u7a33\u5b9a\u72b6\u6001: {monitor.get('label', '-')}"]
    if action:
        reasons.append(f"\u5f85\u5e94\u7528\u52a8\u4f5c: {action}")
    body = "\n".join(str(item) for item in reasons if item)
    return {
        "decision": decision,
        "allowed": decision in {"allow", "confirm"},
        "confirm_required": decision == "confirm",
        "label": label,
        "tone": tone,
        "source": source,
        "source_label": source_label,
        "status": status,
        "action": action or "-",
        "reasons": reasons,
        "body": body,
        "summary_text": f"{source_label}: {label} | {monitor.get('summary_text', '-')}",
    }


def build_strategy_policy_effect_review(
    policy_history: Sequence[Mapping[str, object]] | object,
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    limit: int = 5,
) -> dict[str, object]:
    history_items = [item for item in policy_history if isinstance(item, Mapping)] if isinstance(policy_history, Sequence) else []
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    parsed_history: list[dict[str, object]] = []
    for item in history_items:
        updated_at = _parse_policy_review_time(item.get("updated_at"))
        if updated_at is None:
            continue
        parsed_history.append({**dict(item), "_updated_dt": updated_at})
    parsed_history.sort(key=lambda item: item["_updated_dt"])
    rows: list[dict[str, object]] = []
    previous_hit_rate: float | None = None
    previous_replay_net: int | None = None
    for index, item in enumerate(parsed_history):
        start = item["_updated_dt"]
        end = parsed_history[index + 1]["_updated_dt"] if index + 1 < len(parsed_history) else None
        window_items = []
        for settlement in settlement_items:
            settled_at = _settlement_review_time(settlement)
            if settled_at is None or settled_at < start:
                continue
            if end is not None and settled_at >= end:
                continue
            window_items.append(settlement)
        allowed = [settlement for settlement in window_items if str(settlement.get("strategy_admission_decision") or "").strip() == "allow"]
        known_allowed = [settlement for settlement in allowed if settlement.get("is_correct") is not None]
        allow_hits = sum(1 for settlement in known_allowed if settlement.get("is_correct") is True)
        allow_misses = sum(1 for settlement in known_allowed if settlement.get("is_correct") is False)
        allow_hit_rate = allow_hits / len(known_allowed) if known_allowed else None
        replay_summary = build_agent_replay_downgrade_backtest_summary(window_items)
        sample_rows = _policy_effect_settlement_rows(window_items)
        replay_net = _safe_int(replay_summary.get("net"))
        sample_count = len(known_allowed)
        if sample_count < 3 and _safe_int(replay_summary.get("sample_count")) < 3:
            effect_status = "collecting"
            effect_label = "\u6837\u672c\u79ef\u7d2f\u4e2d"
            tone = "neutral"
        else:
            hit_delta = None if previous_hit_rate is None or allow_hit_rate is None else allow_hit_rate - previous_hit_rate
            replay_delta = None if previous_replay_net is None else replay_net - previous_replay_net
            if (hit_delta is not None and hit_delta >= 0.05) or replay_net > 0 or (replay_delta is not None and replay_delta > 0):
                effect_status = "effective"
                effect_label = "\u6b63\u5411\u751f\u6548"
                tone = "good"
            elif (hit_delta is not None and hit_delta <= -0.05) or replay_net < 0:
                effect_status = "negative"
                effect_label = "\u9700\u8981\u590d\u6838"
                tone = "bad"
            else:
                effect_status = "flat"
                effect_label = "\u65e0\u660e\u663e\u53d8\u5316"
                tone = "warning"
        previous_hit_rate = allow_hit_rate if allow_hit_rate is not None else previous_hit_rate
        previous_replay_net = replay_net
        diagnostics = _policy_effect_negative_diagnostics(
            sample_rows,
            effect_status=effect_status,
            allow_hit_rate=allow_hit_rate,
            replay_net=replay_net,
        )
        source = _text(item.get("source") or item.get("reason"), "-")
        version_id = _text(item.get("version_id"), "-")
        title = f"{effect_label} | {source} | {item.get('updated_at', '-')}"
        body = (
            f"\u7248\u672c {version_id} | \u533a\u95f4\u6837\u672c {len(window_items)} | "
            f"\u653e\u884c {allow_hits}/{len(known_allowed)} ({_pct(allow_hit_rate) if allow_hit_rate is not None else '-'}) | "
            f"\u653e\u884c\u9519\u8bef {allow_misses} | Replay Guard \u51c0\u503c {replay_net:+d} | "
            f"{diagnostics.get('action_label', '-')}"
        )
        rows.append(
            {
                "version_id": version_id,
                "updated_at": item.get("updated_at", "-"),
                "source": source,
                "sample_count": len(window_items),
                "allow_count": len(allowed),
                "known_allow_count": len(known_allowed),
                "allow_hit_rate": allow_hit_rate,
                "allow_hit_rate_text": _pct(allow_hit_rate) if allow_hit_rate is not None else "-",
                "allow_misses": allow_misses,
                "replay_guard_net": replay_net,
                "sample_rows": sample_rows,
                "sample_rows_total": len(window_items),
                "negative_diagnostics": diagnostics,
                "top_negative_rows": diagnostics.get("top_negative_rows", []),
                "rollback_recommended": bool(diagnostics.get("rollback_recommended")),
                "effect_status": effect_status,
                "effect_label": effect_label,
                "tone": tone,
                "title": title,
                "body": body,
            }
        )
    rows.sort(key=lambda row: str(row.get("updated_at") or ""), reverse=True)
    latest = rows[0] if rows else {}
    status_counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("effect_status") or "unknown")
        status_counts[key] = status_counts.get(key, 0) + 1
    full_rows = list(rows)
    stability_monitor = build_strategy_policy_stability_monitor({"rows": full_rows, "history_count": len(parsed_history)})
    return {
        "history_count": len(parsed_history),
        "rows": rows[: max(0, int(limit))],
        "latest_status": latest.get("effect_status", "none") if latest else "none",
        "latest_label": latest.get("effect_label", "\u6682\u65e0\u7248\u672c") if latest else "\u6682\u65e0\u7248\u672c",
        "status_counts": status_counts,
        "stability_monitor": stability_monitor,
        "summary_text": (
            f"\u7248\u672c {len(parsed_history)} | \u6700\u65b0 {latest.get('effect_label', '-') if latest else '-'} | "
            f"\u6b63\u5411 {status_counts.get('effective', 0)} / \u590d\u6838 {status_counts.get('negative', 0)}"
        ),
    }


def build_strategy_evaluation_agent_summary(
    status: Mapping[str, object] | object,
    settlements: Sequence[Mapping[str, object]] | object,
    statsbomb_event_baseline: Mapping[str, object] | object | None = None,
    statsbomb_fewshot_memory: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    settlement_summary = build_high_accuracy_strategy_settlement_summary(settlement_items)
    error_attribution = build_strategy_error_attribution_summary(settlement_items)
    allowlist_summary = build_strategy_allowlist_settlement_summary(settlement_items)
    jc_feedback = build_jc_bucket_feedback_summary(status, settlement_items)
    event_review = build_statsbomb_event_review_summary(settlement_items, statsbomb_event_baseline or {})
    fewshot_memory = build_statsbomb_fewshot_memory_summary(error_attribution, event_review, statsbomb_fewshot_memory or {})
    fewshot_monitor = build_statsbomb_fewshot_memory_monitor(statsbomb_fewshot_memory or {}, fewshot_memory)
    fewshot_quality = build_statsbomb_fewshot_memory_quality_alerts(fewshot_monitor)
    known_count = _safe_int(settlement_summary.get("known_count"))
    hit_rate = settlement_summary.get("hit_rate")
    hit_rate_value = _safe_float(hit_rate, -1.0) if hit_rate is not None else -1.0
    allow_rate = allowlist_summary.get("hit_rate")
    allow_rate_value = _safe_float(allow_rate, -1.0) if allow_rate is not None else -1.0
    reason_counts = _as_mapping(error_attribution.get("reason_counts"))
    jc_status_counts = _as_mapping(jc_feedback.get("status_counts"))
    downgraded_count = _safe_int(jc_status_counts.get("downgraded"))
    watch_count = _safe_int(jc_status_counts.get("watch"))
    high_conf_miss_count = _safe_int(reason_counts.get("high_confidence_miss"))
    historical_gap_count = _safe_int(reason_counts.get("historical_gap"))
    data_missing_count = _safe_int(reason_counts.get("data_missing"))
    statsbomb_against_count = _safe_int(reason_counts.get("statsbomb_xg_against_pick"))
    statsbomb_variance_count = _safe_int(reason_counts.get("statsbomb_finishing_variance"))
    statsbomb_control_gap_count = _safe_int(reason_counts.get("statsbomb_event_control_gap"))
    event_review_sample_count = _safe_int(event_review.get("sample_count"))
    event_review_variance_count = _safe_int(event_review.get("finishing_variance_count"))
    event_review_control_gap_count = _safe_int(event_review.get("control_gap_count"))
    recommendations: list[dict[str, str]] = []
    memory_tags: list[str] = []
    score = 100
    status_text = "healthy"

    if known_count < 5:
        status_text = "collecting"
        score = 55
        recommendations.append(
            {
                "title": "\u7ee7\u7eed\u79ef\u7d2f\u6837\u672c",
                "body": f"\u5df2\u5224\u5b9a\u7b56\u7565\u6837\u672c {known_count} \u9879\uff0c\u6682\u4e0d\u5efa\u8bae\u6839\u636e\u5355\u6b21\u6ce2\u52a8\u8c03\u6574\u95e8\u69db\u3002",
            }
        )
        memory_tags.append("sample_collecting")
    if hit_rate_value >= 0 and hit_rate_value < 0.55:
        status_text = "tighten"
        score -= 25
        recommendations.append(
            {
                "title": "\u6536\u7d27\u7b56\u7565\u51c6\u5165",
                "body": f"\u7b56\u7565\u5b9e\u76d8\u547d\u4e2d {settlement_summary.get('summary_text')}\uff0c\u4f4e\u4e8e 55% \u89c2\u5bdf\u7ebf\uff0c\u5efa\u8bae\u63d0\u9ad8\u6b63\u5f0f\u653e\u884c\u95e8\u69db\u3002",
            }
        )
        memory_tags.append("low_live_hit_rate")
    if allow_rate_value >= 0 and allow_rate_value < 0.55:
        status_text = "tighten"
        score -= 15
        recommendations.append(
            {
                "title": "\u590d\u6838\u653e\u884c\u6e05\u5355",
                "body": f"\u653e\u884c\u547d\u4e2d {allowlist_summary.get('hit_rate_text')}\uff0c\u5efa\u8bae\u964d\u4f4e\u4e2d\u98ce\u9669\u573a\u6b21\u7684\u6b63\u5f0f\u653e\u884c\u6743\u91cd\u3002",
            }
        )
        memory_tags.append("allowlist_underperforming")
    if high_conf_miss_count:
        status_text = "watch" if status_text == "healthy" else status_text
        score -= min(20, high_conf_miss_count * 6)
        recommendations.append(
            {
                "title": "\u6821\u51c6\u7f6e\u4fe1\u5ea6",
                "body": f"\u51fa\u73b0 {high_conf_miss_count} \u9879\u9ad8\u7f6e\u4fe1\u5931\u8bef\uff0c\u5efa\u8bae\u4f18\u5148\u68c0\u67e5\u6982\u7387\u6821\u51c6\u548c\u8d5b\u524d\u98ce\u9669\u62e6\u622a\u3002",
            }
        )
        memory_tags.append("confidence_overstated")
    if historical_gap_count:
        status_text = "watch" if status_text == "healthy" else status_text
        score -= min(18, historical_gap_count * 5)
        recommendations.append(
            {
                "title": "\u68c0\u67e5\u5386\u53f2\u7b56\u7565\u5931\u6548",
                "body": f"\u5386\u53f2\u56de\u6d4b\u4e0e\u5b9e\u76d8\u80cc\u79bb {historical_gap_count} \u9879\uff0c\u5efa\u8bae\u5bf9\u8054\u8d5b/\u8d54\u7387/\u7f6e\u4fe1\u5206\u5c42\u91cd\u65b0\u56de\u6d4b\u3002",
            }
        )
        memory_tags.append("historical_drift")
    if downgraded_count or watch_count:
        status_text = "watch" if status_text == "healthy" else status_text
        score -= downgraded_count * 10 + watch_count * 4
        recommendations.append(
            {
                "title": "\u7ef4\u6301JC\u6876\u89c2\u5bdf",
                "body": f"JC \u7a33\u5b9a\u6876\u964d\u7ea7 {downgraded_count} / \u89c2\u5bdf {watch_count}\uff0c\u672a\u8fbe\u6062\u590d\u6761\u4ef6\u524d\u4e0d\u5efa\u8bae\u6062\u590d\u6b63\u5f0f\u653e\u884c\u3002",
            }
        )
        memory_tags.append("jc_bucket_watch")
    if statsbomb_against_count or statsbomb_control_gap_count:
        status_text = "watch" if status_text == "healthy" else status_text
        score -= min(18, (statsbomb_against_count + statsbomb_control_gap_count) * 5)
        recommendations.append(
            {
                "title": "\u7eb3\u5165\u8d5b\u540e\u4e8b\u4ef6\u8bc1\u636e",
                "body": f"StatsBomb \u663e\u793a xG \u53cd\u5411 {statsbomb_against_count} / \u573a\u9762\u52a3\u52bf {statsbomb_control_gap_count}\uff0c\u5efa\u8bae\u5c06\u5c04\u95e8\u3001xG\u3001\u538b\u8feb\u7b49\u8d5b\u540e\u7279\u5f81\u7eb3\u5165\u9519\u56e0\u8bb0\u5fc6\u3002",
            }
        )
        memory_tags.append("statsbomb_event_gap")
    if statsbomb_variance_count:
        recommendations.append(
            {
                "title": "\u6807\u8bb0\u7ec8\u7ed3\u6ce2\u52a8",
                "body": f"StatsBomb \u8bc6\u522b {statsbomb_variance_count} \u9879 xG \u5360\u4f18\u4f46\u672a\u547d\u4e2d\u7684\u7ec8\u7ed3\u504f\u5dee\uff0c\u8fd9\u7c7b\u4e0d\u5e94\u7b80\u5355\u5f52\u4e3a\u6a21\u578b\u65b9\u5411\u9519\u8bef\u3002",
            }
        )
        memory_tags.append("finishing_variance")
    if event_review_sample_count:
        memory_tags.append("statsbomb_post_match_review")
        if event_review_variance_count or event_review_control_gap_count:
            status_text = "watch" if status_text == "healthy" else status_text
            score -= min(10, event_review_variance_count * 3 + event_review_control_gap_count * 2)
            recommendations.append(
                {
                    "title": "\u5bf9\u7167StatsBomb\u4e8b\u4ef6\u57fa\u7ebf",
                    "body": (
                        f"\u8d5b\u540e\u4e8b\u4ef6\u590d\u76d8 {event_review_sample_count} \u573a\uff0c"
                        f"\u7ec8\u7ed3\u6ce2\u52a8 {event_review_variance_count}\uff0c\u573a\u9762\u5dee\u5f02 {event_review_control_gap_count}\u3002"
                        f"\u5386\u53f2\u57fa\u7ebf {_safe_int(event_review.get('baseline_match_count'))} \u573a\uff0c"
                        f"\u7ec8\u7ed3\u6ce2\u52a8\u7387 {event_review.get('baseline_finishing_variance_rate') or '-'}\u3002"
                    ),
                }
            )
    if _safe_int(fewshot_memory.get("matched_count")):
        memory_tags.append("statsbomb_fewshot_memory")
        recommendations.append(
            {
                "title": "\u53c2\u8003StatsBomb\u5386\u53f2\u590d\u76d8\u8bb0\u5fc6",
                "body": (
                    f"{fewshot_memory.get('summary_text') or '-'}\u3002"
                    "\u5efa\u8bae\u5c06\u76f8\u4f3c\u6848\u4f8b\u4f5c\u4e3a\u590d\u76d8\u8bed\u5883\uff0c\u533a\u5206\u7ec8\u7ed3\u6ce2\u52a8\u3001\u573a\u9762\u52a3\u52bf\u548c\u771f\u6b63\u7684\u8d5b\u524d\u5224\u65ad\u5931\u6548\u3002"
                ),
            }
        )
    if _safe_int(fewshot_quality.get("alert_count")):
        status_text = "watch" if status_text == "healthy" else status_text
        score += _safe_int(fewshot_quality.get("score_delta"))
        for tag in _as_list(fewshot_quality.get("memory_tags")):
            tag_text = str(tag)
            if tag_text and tag_text not in memory_tags:
                memory_tags.append(tag_text)
        alert_priority = {"statsbomb_memory_no_current_match": 0, "statsbomb_memory_tag_gap": 1}
        quality_alerts = sorted(
            [_as_mapping(alert) for alert in _as_list(fewshot_quality.get("alerts"))],
            key=lambda alert: alert_priority.get(str(alert.get("tag") or ""), 5),
        )
        for alert_map in quality_alerts:
            if alert_map:
                recommendations.append(
                    {
                        "title": str(alert_map.get("title") or "StatsBomb记忆质量告警"),
                        "body": str(alert_map.get("body") or "-"),
                    }
                )
    if data_missing_count:
        score -= min(12, data_missing_count * 4)
        recommendations.append(
            {
                "title": "\u4fee\u590d\u8d5b\u679c/\u5feb\u7167\u6570\u636e",
                "body": f"\u5b58\u5728 {data_missing_count} \u9879\u6570\u636e\u7f3a\u5931\uff0c\u9700\u4f18\u5148\u68c0\u67e5\u8d5b\u524d\u5feb\u7167\u548c\u8d5b\u679c\u56de\u6536\u94fe\u8def\u3002",
            }
        )
        memory_tags.append("data_quality_gap")
    if not recommendations:
        recommendations.append(
            {
                "title": "\u7ef4\u6301\u5f53\u524d\u7b56\u7565",
                "body": "\u672a\u53d1\u73b0\u9700\u8981\u6536\u7d27\u7684\u4e3b\u8981\u9519\u56e0\uff0c\u7ee7\u7eed\u6309\u5f53\u524d\u51c6\u5165\u548c\u590d\u76d8\u89c4\u5219\u8fd0\u884c\u3002",
            }
        )
        memory_tags.append("stable")

    score = max(0, min(100, int(round(score))))
    if score < 60 and status_text not in {"tighten", "collecting"}:
        status_text = "watch"
    return {
        "agent": "Evaluation Agent",
        "status": status_text,
        "score": score,
        "summary_text": (
            f"\u6837\u672c {known_count} | \u7b56\u7565\u547d\u4e2d {settlement_summary.get('hit_rate_text')} | "
            f"\u4e3b\u9519\u56e0 {error_attribution.get('top_reason')} | JC {jc_feedback.get('summary_text')}"
        ),
        "settlement_summary": settlement_summary,
        "error_attribution": error_attribution,
        "jc_bucket_feedback": jc_feedback,
        "statsbomb_event_review": event_review,
        "statsbomb_fewshot_memory": fewshot_memory,
        "statsbomb_fewshot_monitor": fewshot_monitor,
        "statsbomb_fewshot_quality": fewshot_quality,
        "recommendations": recommendations[:8],
        "memory_tags": memory_tags,
    }


def _build_high_accuracy_strategy_pool_rows_legacy(status: Mapping[str, object] | object) -> list[dict[str, str]]:
    resolved = _as_mapping(status)
    rows: list[dict[str, str]] = []
    for index, item in enumerate(_strategy_pool(resolved), start=1):
        layer = _strategy_layer(item)
        stability = _strategy_stability(item)
        breaker = _as_mapping(item.get("breaker"))
        role = _label(ROLE_LABELS, item.get("effective_role") or item.get("role"))
        original_role = _label(ROLE_LABELS, item.get("original_role") or item.get("role"))
        if role != original_role:
            role = f"{role}(\u539f{original_role})"
        play = _label(PLAY_LABELS, item.get("play_type"))
        scope = _label(SCOPE_LABELS, item.get("scope"))
        data_layer = _label(DATA_LAYER_LABELS, layer.get("data_layer"))
        breaker_status = "ON" if bool(breaker.get("breaker_on")) else str(breaker.get("status") or "pending").upper()
        title = f"{index}. {role} | {play}"
        jc_bucket = _as_mapping(item.get("jc_bucket"))
        jc_context = _as_mapping(item.get("jc_context"))
        jc_feedback = _as_mapping(item.get("jc_live_feedback"))
        jc_lines: list[str] = []
        if str(layer.get("data_layer") or "") == "jc_stratified_market":
            live_status = str(jc_feedback.get("status") or "pending").upper()
            live_line = (
                f"JC实盘: {_safe_int(jc_feedback.get('live_hit_count'))}/{_safe_int(jc_feedback.get('live_count'))}"
                f" ({_pct(jc_feedback.get('live_hit_rate'))}) | 偏差 {_pct(jc_feedback.get('deviation'))} | 状态 {live_status}"
                if jc_feedback
                else "JC实盘: 待积累赛后样本"
            )
            jc_lines = [
                f"JC稳定桶: {jc_bucket.get('dimension') or item.get('dimension') or '-'} / {jc_bucket.get('bucket') or item.get('scope_value') or '-'}",
                f"JC当前匹配: confidence_bucket={jc_context.get('confidence_bucket') or '-'} | odds_bucket={jc_context.get('odds_bucket') or '-'} | pick_odds={_safe_float(jc_context.get('pick_odds')):.2f}",
            ]
        if str(layer.get("data_layer") or "") == "jc_stratified_market":
            jc_lines.append(live_line)
        body = "\n".join(
            [
                f"\u8303\u56f4: {scope} / {item.get('scope_value') or '-'} | \u6570\u636e\u5c42: {data_layer}",
                f"\u95e8\u69db: {_safe_float(item.get('min_confidence')):.2f} | \u56de\u6d4b: {_pct(item.get('accuracy'))} ({_safe_int(item.get('hit_count'))}/{_safe_int(item.get('sample_count'))})",
                f"Wilson: {_pct(item.get('wilson_lower'))} | \u8986\u76d6: {_pct(item.get('coverage'))} | \u8fb9\u9645: {_safe_float(item.get('edge')):+.1%}",
                f"\u7a33\u5b9a: {'OK' if bool(stability.get('stable')) else 'WATCH'} | \u8bc4\u5206 {_pct(stability.get('stability_score'))} | \u8fd130/90 {_pct(stability.get('recent_30_accuracy'))}/{_pct(stability.get('recent_90_accuracy'))}",
                f"\u65ad\u8def: {breaker_status} | \u8fde\u9519 {_safe_int(breaker.get('miss_streak'))}/{_safe_int(breaker.get('threshold'), 3)} | \u6062\u590d {_safe_int(breaker.get('recovery_streak'))}/{_safe_int(breaker.get('recovery_hits_required'), 2)} | \u8fd1\u671f {_safe_int(breaker.get('hit_count'))}/{_safe_int(breaker.get('known_count'))}",
            ]
            + jc_lines
        )
        rows.append({"title": title, "body": body})
    return rows


def build_high_accuracy_strategy_pool_rows(status: Mapping[str, object] | object) -> list[dict[str, str]]:
    resolved = _as_mapping(status)
    rows: list[dict[str, str]] = []
    for index, item in enumerate(_strategy_pool(resolved), start=1):
        layer = _strategy_layer(item)
        stability = _strategy_stability(item)
        breaker = _as_mapping(item.get("breaker"))
        role = _label(ROLE_LABELS, item.get("effective_role") or item.get("role"))
        original_role = _label(ROLE_LABELS, item.get("original_role") or item.get("role"))
        if role != original_role:
            role = f"{role}(\u539f{original_role})"
        play = _label(PLAY_LABELS, item.get("play_type"))
        scope = _label(SCOPE_LABELS, item.get("scope"))
        data_layer = _label(DATA_LAYER_LABELS, layer.get("data_layer"))
        breaker_status = "ON" if bool(breaker.get("breaker_on")) else str(breaker.get("status") or "pending").upper()
        title = f"{index}. {role} | {play}"
        jc_bucket = _as_mapping(item.get("jc_bucket"))
        jc_context = _as_mapping(item.get("jc_context"))
        jc_feedback = _as_mapping(item.get("jc_live_feedback"))
        jc_calibration = _as_mapping(item.get("jc_auto_calibration"))
        jc_lines: list[str] = []
        if str(layer.get("data_layer") or "") == "jc_stratified_market":
            live_status = str(jc_feedback.get("status") or "pending").upper()
            calibration_thresholds = _as_mapping(jc_calibration.get("thresholds"))
            calibration_line = (
                f"JC\u6821\u51c6: {str(jc_calibration.get('mode') or 'base').upper()} | "
                f"\u6837\u672c>={_safe_int(calibration_thresholds.get('min_samples'), 120)} | "
                f"\u51c6\u786e>={_pct(calibration_thresholds.get('min_accuracy'))} | "
                f"Wilson>={_pct(calibration_thresholds.get('min_wilson'))}"
                if jc_calibration
                else "JC\u6821\u51c6: BASE"
            )
            if jc_feedback:
                live_line = (
                    f"JC\u5b9e\u76d8: {_safe_int(jc_feedback.get('live_hit_count'))}/{_safe_int(jc_feedback.get('live_count'))}"
                    f" ({_pct(jc_feedback.get('live_hit_rate'))}) | \u504f\u5dee {_pct(jc_feedback.get('deviation'))} | \u72b6\u6001 {live_status}"
                )
            else:
                live_line = "JC\u5b9e\u76d8: \u5f85\u79ef\u7d2f\u8d5b\u540e\u6837\u672c"
            jc_lines = [
                f"JC\u7a33\u5b9a\u6876: {jc_bucket.get('dimension') or item.get('dimension') or '-'} / {jc_bucket.get('bucket') or item.get('scope_value') or '-'}",
                f"JC\u5f53\u524d\u5339\u914d: confidence_bucket={jc_context.get('confidence_bucket') or '-'} | odds_bucket={jc_context.get('odds_bucket') or '-'} | pick_odds={_safe_float(jc_context.get('pick_odds')):.2f}",
                live_line,
                calibration_line,
            ]
        body = "\n".join(
            [
                f"\u8303\u56f4: {scope} / {item.get('scope_value') or '-'} | \u6570\u636e\u5c42: {data_layer}",
                f"\u95e8\u69db: {_safe_float(item.get('min_confidence')):.2f} | \u56de\u6d4b: {_pct(item.get('accuracy'))} ({_safe_int(item.get('hit_count'))}/{_safe_int(item.get('sample_count'))})",
                f"Wilson: {_pct(item.get('wilson_lower'))} | \u8986\u76d6: {_pct(item.get('coverage'))} | \u8fb9\u9645: {_safe_float(item.get('edge')):+.1%}",
                f"\u7a33\u5b9a: {'OK' if bool(stability.get('stable')) else 'WATCH'} | \u8bc4\u5206 {_pct(stability.get('stability_score'))} | \u8fd130/90 {_pct(stability.get('recent_30_accuracy'))}/{_pct(stability.get('recent_90_accuracy'))}",
                f"\u65ad\u8def: {breaker_status} | \u8fde\u9519 {_safe_int(breaker.get('miss_streak'))}/{_safe_int(breaker.get('threshold'), 3)} | \u6062\u590d {_safe_int(breaker.get('recovery_streak'))}/{_safe_int(breaker.get('recovery_hits_required'), 2)} | \u8fd1\u671f {_safe_int(breaker.get('hit_count'))}/{_safe_int(breaker.get('known_count'))}",
            ]
            + jc_lines
        )
        rows.append({"title": title, "body": body})
    return rows


def build_high_accuracy_strategy_settlement_rows(
    settlements: Sequence[Mapping[str, object]],
    *,
    limit: int = 8,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for settlement, item in _known_strategy_settlement_items(settlements)[: max(0, int(limit))]:
        hit = item.get("is_hit")
        hit_label = "\u547d\u4e2d" if hit is True else "\u672a\u547d\u4e2d" if hit is False else "\u5f85\u5224\u5b9a"
        shadow_label = "\u89c2\u5bdf" if bool(item.get("is_shadow")) else "\u6b63\u5f0f"
        title = f"{hit_label} | {shadow_label} | {_label(ROLE_LABELS, item.get('role'))} | {_label(PLAY_LABELS, item.get('play_type'))}"
        match_text = (
            f"{settlement.get('league') or '-'} | {settlement.get('home_team') or '-'}"
            f" vs {settlement.get('away_team') or '-'}"
        )
        body = "\n".join(
            [
                match_text,
                f"\u9884\u6d4b: {item.get('pick') or '-'} | \u5b9e\u9645: {item.get('actual') or '-'}",
                f"\u7f6e\u4fe1: {_pct(item.get('confidence'))} / \u95e8\u69db {_safe_float(item.get('min_confidence')):.2f} | \u56de\u6d4b {_pct(item.get('backtest_accuracy'))} ({_safe_int(item.get('backtest_samples'))}\u6837\u672c)",
            ]
        )
        rows.append({"title": title, "body": body})
    return rows


def _jc_bucket_key_from_item(item: Mapping[str, object]) -> str:
    explicit = str(item.get("jc_bucket_key") or "").strip()
    if explicit:
        return explicit
    bucket = _as_mapping(item.get("jc_bucket"))
    dimension = str(bucket.get("dimension") or item.get("dimension") or "").strip()
    bucket_value = str(bucket.get("bucket") or item.get("scope_value") or "").strip()
    if not dimension or not bucket_value:
        return ""
    return f"{dimension}|{bucket_value}"


def _is_jc_bucket_item(item: Mapping[str, object]) -> bool:
    layer = _as_mapping(item.get("layer"))
    return str(item.get("data_layer") or layer.get("data_layer") or "") == "jc_stratified_market" or bool(_as_mapping(item.get("jc_bucket")))


def _jc_bucket_summary_status(
    *,
    live_count: int,
    live_hit_rate: float | None,
    wilson_lower: float,
    miss_streak: int,
    explicit_status: str = "",
) -> str:
    explicit = explicit_status.strip().lower()
    if explicit in {"downgraded", "watch", "healthy", "pending"}:
        return explicit
    if live_count < 5 or live_hit_rate is None:
        return "pending"
    if live_count >= 10 and live_hit_rate < max(0.45, wilson_lower - 0.10):
        return "downgraded"
    if miss_streak >= 3 or live_hit_rate < max(0.45, wilson_lower - 0.05):
        return "watch"
    return "healthy"


def _most_common_text(values: Sequence[object]) -> str:
    counts: dict[str, int] = {}
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        counts[text] = counts.get(text, 0) + 1
    if not counts:
        return "-"
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _avg_float(values: Sequence[object]) -> float | None:
    numbers = [_safe_float(value) for value in values if value not in (None, "")]
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def _jc_bucket_diagnostics(
    *,
    status_text: str,
    live_count: int,
    live_hit_rate: float | None,
    historical_accuracy: float,
    historical_wilson: float,
    deviation: object,
    miss_streak: int,
    live_avg_odds: float | None,
    historical_avg_odds: float | None,
    live_avg_confidence: float | None,
    historical_avg_confidence: float | None,
) -> str:
    reasons: list[str] = []
    deviation_value = _safe_float(deviation) if deviation is not None else None
    if live_count < 10:
        reasons.append("\u5b9e\u76d8\u6837\u672c\u504f\u5c11")
    if live_hit_rate is not None and live_hit_rate < historical_wilson:
        reasons.append("\u5b9e\u76d8\u8dcc\u7834Wilson\u4e0b\u9650")
    if deviation_value is not None and deviation_value <= -0.10:
        reasons.append("\u547d\u4e2d\u7387\u8f83\u5386\u53f2\u660e\u663e\u56de\u843d")
    if miss_streak >= 3:
        reasons.append("\u8fde\u7eed\u672a\u547d\u4e2d")
    if live_avg_odds is not None and historical_avg_odds is not None and abs(live_avg_odds - historical_avg_odds) >= 0.25:
        reasons.append("\u5b9e\u76d8\u8d54\u7387\u4e0e\u5386\u53f2\u5747\u503c\u504f\u79bb")
    if live_avg_confidence is not None and historical_avg_confidence is not None and live_avg_confidence + 0.05 < historical_avg_confidence:
        reasons.append("\u5b9e\u76d8\u7f6e\u4fe1\u4f4e\u4e8e\u5386\u53f2\u5747\u503c")
    if status_text == "healthy" and not reasons:
        reasons.append("\u5b9e\u76d8\u8868\u73b0\u4e0e\u5386\u53f2\u5339\u914d")
    if status_text == "pending" and not reasons:
        reasons.append("\u7b49\u5f85\u66f4\u591a\u8d5b\u540e\u6837\u672c")
    return " | ".join(reasons[:4]) if reasons else "-"


def _jc_recovery_label(
    *,
    status_text: str,
    recovery_status: str,
    recovery_streak: int,
    recovery_required: int,
) -> str:
    required = max(1, int(recovery_required or 1))
    if recovery_status == "eligible":
        return f"\u5df2\u8fbe\u5230\u6062\u590d\u6761\u4ef6 {recovery_streak}/{required}\uff0c\u4fdd\u6301\u89c2\u5bdf"
    if recovery_status == "in_progress":
        return f"\u6062\u590d\u4e2d {recovery_streak}/{required}\uff0c\u7ee7\u7eed\u8bb0\u5f55\u5f71\u5b50\u7ed3\u7b97"
    if recovery_status == "recovered" or status_text == "healthy":
        return "\u6682\u65e0\u6062\u590d\u538b\u529b"
    if status_text in {"watch", "downgraded"}:
        return f"\u672a\u8fbe\u6062\u590d\u6761\u4ef6 0/{required}\uff0c\u9700\u8fde\u7eed\u547d\u4e2d"
    return "\u7b49\u5f85\u66f4\u591a\u8d5b\u540e\u6837\u672c"


def build_jc_bucket_feedback_summary(
    status: Mapping[str, object] | object,
    settlements: Sequence[Mapping[str, object]] | object,
) -> dict[str, object]:
    resolved = _as_mapping(status)
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    buckets: dict[str, dict[str, object]] = {}

    def ensure_bucket(item: Mapping[str, object]) -> dict[str, object] | None:
        if not _is_jc_bucket_item(item):
            return None
        key = _jc_bucket_key_from_item(item)
        if not key:
            return None
        bucket = _as_mapping(item.get("jc_bucket"))
        feedback = _as_mapping(item.get("jc_live_feedback"))
        current = buckets.setdefault(
            key,
            {
                "key": key,
                "dimension": bucket.get("dimension") or item.get("dimension") or "-",
                "bucket": bucket.get("bucket") or item.get("scope_value") or "-",
                "historical_accuracy": feedback.get("historical_accuracy", bucket.get("accuracy", item.get("accuracy", item.get("backtest_accuracy")))),
                "historical_wilson_lower": feedback.get("historical_wilson_lower", bucket.get("wilson_lower", item.get("wilson_lower"))),
                "historical_samples": bucket.get("sample_count", item.get("sample_count", item.get("backtest_samples", 0))),
                "historical_avg_confidence": bucket.get("avg_confidence", item.get("avg_confidence")),
                "historical_avg_pick_odds": bucket.get("avg_pick_odds", item.get("avg_pick_odds")),
                "hits": [],
                "confidence_buckets": [],
                "odds_buckets": [],
                "pick_odds_values": [],
                "confidence_values": [],
                "explicit_status": "",
            },
        )
        if feedback:
            current["explicit_status"] = str(feedback.get("status") or current.get("explicit_status") or "")
            for source_key, target_key in (
                ("historical_accuracy", "historical_accuracy"),
                ("historical_wilson_lower", "historical_wilson_lower"),
                ("live_count", "feedback_live_count"),
                ("live_hit_count", "feedback_live_hit_count"),
                ("live_hit_rate", "feedback_live_hit_rate"),
                ("deviation", "feedback_deviation"),
                ("miss_streak", "feedback_miss_streak"),
                ("recovery_streak", "feedback_recovery_streak"),
                ("recovery_hits_required", "feedback_recovery_hits_required"),
            ):
                if feedback.get(source_key) is not None:
                    current[target_key] = feedback.get(source_key)
            if feedback.get("recovery_status"):
                current["feedback_recovery_status"] = feedback.get("recovery_status")
        for source_key, target_key in (
            ("avg_confidence", "historical_avg_confidence"),
            ("avg_pick_odds", "historical_avg_pick_odds"),
            ("accuracy", "historical_accuracy"),
            ("wilson_lower", "historical_wilson_lower"),
            ("sample_count", "historical_samples"),
        ):
            if current.get(target_key) in (None, "") and bucket.get(source_key) not in (None, ""):
                current[target_key] = bucket.get(source_key)
        return current

    for pool_item in _strategy_pool(resolved):
        ensure_bucket(pool_item)
    for _settlement, item in _known_strategy_settlement_items(settlement_items):
        bucket_row = ensure_bucket(item)
        if bucket_row is None or item.get("is_hit") is None:
            continue
        hits = bucket_row.setdefault("hits", [])
        if isinstance(hits, list):
            hits.append(bool(item.get("is_hit")))
        context = _as_mapping(item.get("jc_context"))
        confidence_buckets = bucket_row.setdefault("confidence_buckets", [])
        odds_buckets = bucket_row.setdefault("odds_buckets", [])
        pick_odds_values = bucket_row.setdefault("pick_odds_values", [])
        confidence_values = bucket_row.setdefault("confidence_values", [])
        if isinstance(confidence_buckets, list) and context.get("confidence_bucket"):
            confidence_buckets.append(context.get("confidence_bucket"))
        if isinstance(odds_buckets, list) and context.get("odds_bucket"):
            odds_buckets.append(context.get("odds_bucket"))
        if isinstance(pick_odds_values, list) and context.get("pick_odds") not in (None, ""):
            pick_odds_values.append(context.get("pick_odds"))
        if isinstance(confidence_values, list) and item.get("confidence") not in (None, ""):
            confidence_values.append(item.get("confidence"))

    rows: list[dict[str, str]] = []
    status_counts = {"healthy": 0, "watch": 0, "downgraded": 0, "pending": 0}
    for bucket in buckets.values():
        hits = bucket.get("hits") if isinstance(bucket.get("hits"), list) else []
        live_count = len(hits) if hits else _safe_int(bucket.get("feedback_live_count"))
        live_hit_count = sum(1 for hit in hits if hit) if hits else _safe_int(bucket.get("feedback_live_hit_count"))
        live_hit_rate = live_hit_count / live_count if live_count else None
        if live_hit_rate is None and bucket.get("feedback_live_hit_rate") is not None:
            live_hit_rate = _safe_float(bucket.get("feedback_live_hit_rate"))
        miss_streak = 0
        if hits:
            for hit in hits:
                if hit:
                    break
                miss_streak += 1
        else:
            miss_streak = _safe_int(bucket.get("feedback_miss_streak"))
        recovery_streak = 0
        if hits:
            for hit in hits:
                if not hit:
                    break
                recovery_streak += 1
        else:
            recovery_streak = _safe_int(bucket.get("feedback_recovery_streak"))
        recovery_required = _safe_int(bucket.get("feedback_recovery_hits_required"), 3)
        recovery_status = str(bucket.get("feedback_recovery_status") or "")
        historical_accuracy = _safe_float(bucket.get("historical_accuracy"))
        historical_wilson = _safe_float(bucket.get("historical_wilson_lower"))
        deviation = live_hit_rate - historical_accuracy if live_hit_rate is not None else bucket.get("feedback_deviation")
        confidence_buckets = bucket.get("confidence_buckets") if isinstance(bucket.get("confidence_buckets"), list) else []
        odds_buckets = bucket.get("odds_buckets") if isinstance(bucket.get("odds_buckets"), list) else []
        live_avg_odds = _avg_float(bucket.get("pick_odds_values") if isinstance(bucket.get("pick_odds_values"), list) else [])
        live_avg_confidence = _avg_float(bucket.get("confidence_values") if isinstance(bucket.get("confidence_values"), list) else [])
        historical_avg_odds = _safe_float(bucket.get("historical_avg_pick_odds")) if bucket.get("historical_avg_pick_odds") not in (None, "") else None
        historical_avg_confidence = _safe_float(bucket.get("historical_avg_confidence")) if bucket.get("historical_avg_confidence") not in (None, "") else None
        status_text = _jc_bucket_summary_status(
            live_count=live_count,
            live_hit_rate=live_hit_rate,
            wilson_lower=historical_wilson,
            miss_streak=miss_streak,
            explicit_status=str(bucket.get("explicit_status") or ""),
        )
        status_counts[status_text] = status_counts.get(status_text, 0) + 1
        recovery_text = _jc_recovery_label(
            status_text=status_text,
            recovery_status=recovery_status,
            recovery_streak=recovery_streak,
            recovery_required=recovery_required,
        )
        diagnostics = _jc_bucket_diagnostics(
            status_text=status_text,
            live_count=live_count,
            live_hit_rate=live_hit_rate,
            historical_accuracy=historical_accuracy,
            historical_wilson=historical_wilson,
            deviation=deviation,
            miss_streak=miss_streak,
            live_avg_odds=live_avg_odds,
            historical_avg_odds=historical_avg_odds,
            live_avg_confidence=live_avg_confidence,
            historical_avg_confidence=historical_avg_confidence,
        )
        rows.append(
            {
                "title": f"{status_text.upper()} | {bucket.get('dimension') or '-'} / {bucket.get('bucket') or '-'}",
                "body": (
                    f"\u5386\u53f2: {_pct(historical_accuracy)} | Wilson {_pct(historical_wilson)} | \u6837\u672c {_safe_int(bucket.get('historical_samples'))}\n"
                    f"\u5b9e\u76d8: {live_hit_count}/{live_count} ({_pct(live_hit_rate)}) | \u504f\u5dee {_pct(deviation)} | \u8fde\u9519 {miss_streak}\n"
                    f"\u5206\u5e03: \u7f6e\u4fe1 {_most_common_text(confidence_buckets)} / \u8d54\u7387 {_most_common_text(odds_buckets)} | \u5747\u8d54 {_safe_float(live_avg_odds):.2f}/{_safe_float(historical_avg_odds):.2f}\n"
                    f"\u8bca\u65ad: {diagnostics}\n"
                    f"\u6062\u590d: {recovery_text}"
                ),
                "status": status_text,
                "live_count": str(live_count),
                "deviation": f"{_safe_float(deviation):.4f}" if deviation is not None else "",
                "diagnostics": diagnostics,
                "recovery_status": recovery_status,
                "recovery_streak": str(recovery_streak),
            }
        )

    priority = {"downgraded": 0, "watch": 1, "pending": 2, "healthy": 3}
    rows.sort(key=lambda row: (priority.get(row.get("status", "pending"), 9), _safe_float(row.get("deviation"), 0.0), -_safe_int(row.get("live_count"))))
    return {
        "total": len(rows),
        "status_counts": status_counts,
        "rows": rows[:8],
        "summary_text": (
            f"\u964d\u7ea7 {status_counts.get('downgraded', 0)} | \u89c2\u5bdf {status_counts.get('watch', 0)} | "
            f"\u5065\u5eb7 {status_counts.get('healthy', 0)} | \u5f85\u6837\u672c {status_counts.get('pending', 0)}"
        ),
    }


def _known_values(items: Sequence[Mapping[str, object]], key: str) -> list[bool]:
    return [bool(item.get(key)) for item in items if isinstance(item, Mapping) and item.get(key) is not None]


def _hit_rate(values: Sequence[bool]) -> float | None:
    if not values:
        return None
    return sum(1 for value in values if value) / len(values)


def _strategy_allowlist_settlements(settlements: Sequence[Mapping[str, object]] | object) -> list[Mapping[str, object]]:
    if not isinstance(settlements, Sequence):
        return []
    return [
        item
        for item in settlements
        if isinstance(item, Mapping) and str(item.get("strategy_allowlist_decision") or "") == "allow"
    ]


def _allowlist_failure_reasons(item: Mapping[str, object]) -> list[str]:
    reasons: list[str] = []
    if item.get("is_correct") is False:
        reasons.append("1X2 \u65b9\u5411\u5931\u8bef")
    if item.get("is_correct") is False and _safe_float(item.get("prediction_confidence")) >= 0.6:
        reasons.append("\u9ad8\u7f6e\u4fe1\u5931\u8bef")
    if item.get("handicap_is_correct") is False:
        reasons.append("\u8ba9\u7403\u5931\u8bef")
    if item.get("ou_is_correct") is False:
        reasons.append("\u5927\u5c0f\u7403\u5931\u8bef")
    active_count = _safe_int(item.get("high_accuracy_strategy_active_count"))
    hit_count = _safe_int(item.get("high_accuracy_strategy_hit_count"))
    if active_count > 0 and hit_count < active_count:
        reasons.append("\u9ad8\u51c6\u7b56\u7565\u672a\u5168\u547d\u4e2d")
    if not reasons:
        reasons.append("\u6682\u65e0\u660e\u663e\u5931\u8d25\u56e0\u5b50")
    return reasons


def build_strategy_allowlist_settlement_summary(settlements: Sequence[Mapping[str, object]] | object) -> dict[str, object]:
    rows = _strategy_allowlist_settlements(settlements)
    official_values = _known_values(rows, "is_correct")
    handicap_values = _known_values(rows, "handicap_is_correct")
    ou_values = _known_values(rows, "ou_is_correct")
    active_total = sum(_safe_int(item.get("high_accuracy_strategy_active_count")) for item in rows)
    active_hits = sum(_safe_int(item.get("high_accuracy_strategy_hit_count")) for item in rows)
    shadow_count = sum(1 for item in rows if _safe_int(item.get("high_accuracy_strategy_shadow_count")) > 0)
    high_conf_misses = sum(
        1
        for item in rows
        if item.get("is_correct") is False and _safe_float(item.get("prediction_confidence")) >= 0.6
    )
    reason_counter: dict[str, int] = {}
    for item in rows:
        if item.get("is_correct") is True:
            continue
        for reason in _allowlist_failure_reasons(item):
            if reason == "\u6682\u65e0\u660e\u663e\u5931\u8d25\u56e0\u5b50":
                continue
            reason_counter[reason] = reason_counter.get(reason, 0) + 1
    top_failure = "-"
    if reason_counter:
        reason, count = sorted(reason_counter.items(), key=lambda pair: (-pair[1], pair[0]))[0]
        top_failure = f"{reason} {count}\u6b21"
    official_rate = _hit_rate(official_values)
    high_strategy_rate = active_hits / active_total if active_total else None
    return {
        "settled_count": len(rows),
        "known_count": len(official_values),
        "hit_count": sum(1 for value in official_values if value),
        "miss_count": sum(1 for value in official_values if not value),
        "hit_rate": official_rate,
        "hit_rate_text": _pct(official_rate) if official_rate is not None else "-",
        "handicap_hit_rate_text": _pct(_hit_rate(handicap_values)) if handicap_values else "-",
        "ou_hit_rate_text": _pct(_hit_rate(ou_values)) if ou_values else "-",
        "high_strategy_summary": f"{active_hits}/{active_total}" if active_total else "-",
        "high_strategy_hit_rate": high_strategy_rate,
        "high_strategy_hit_rate_text": _pct(high_strategy_rate) if high_strategy_rate is not None else "-",
        "shadow_observed_count": shadow_count,
        "high_conf_misses": high_conf_misses,
        "top_failure": top_failure,
        "failure_counts": reason_counter,
    }


def build_strategy_allowlist_settlement_rows(
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    limit: int = 8,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in _strategy_allowlist_settlements(settlements)[: max(0, int(limit))]:
        hit = item.get("is_correct")
        hit_label = "\u547d\u4e2d" if hit is True else "\u5931\u8bef" if hit is False else "\u5f85\u5224\u5b9a"
        title = (
            f"{hit_label} | {item.get('league') or '-'} | "
            f"{item.get('home_team') or '-'} vs {item.get('away_team') or '-'}"
        )
        score = f"{item.get('home_goals', '-')}:{item.get('away_goals', '-')}"
        reasons_text = "\u3001".join(_allowlist_failure_reasons(item))
        body = "\n".join(
            [
                f"\u6e05\u5355: {item.get('strategy_allowlist_file') or '-'} | \u5bfc\u51fa {item.get('strategy_allowlist_exported_at') or '-'}",
                f"\u8d5b\u679c: {score} | \u9884\u6d4b {item.get('predicted') or '-'} | \u7f6e\u4fe1 {_pct(item.get('prediction_confidence'))}",
                f"\u9ad8\u51c6: {item.get('high_accuracy_strategy_summary') or '-'} | \u8ba9\u7403 {item.get('predicted_handicap') or '-'} / {'Y' if item.get('handicap_is_correct') is True else 'N' if item.get('handicap_is_correct') is False else '-'} | \u5927\u5c0f {item.get('predicted_ou') or '-'} / {'Y' if item.get('ou_is_correct') is True else 'N' if item.get('ou_is_correct') is False else '-'}",
                f"\u504f\u5dee: {reasons_text}",
            ]
        )
        rows.append({"title": title, "body": body})
    return rows


def _market_entropy_bucket(item: Mapping[str, object]) -> str:
    level = _text(item.get("market_entropy_level")).upper()
    score = _safe_float(item.get("market_entropy_score"))
    if level == "HIGH" or score >= 0.66:
        return "high"
    if level == "MEDIUM" or score >= 0.38:
        return "medium"
    return "low"


def _market_entropy_bucket_label(bucket: str) -> str:
    return {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}.get(str(bucket or ""), "-")


def _handicap_margin_bucket(item: Mapping[str, object]) -> str:
    level = _text(item.get("handicap_margin_level")).upper()
    score = _safe_float(item.get("handicap_margin_score"))
    if level == "HIGH" or score >= 0.66:
        return "high"
    if level == "MEDIUM" or score >= 0.38:
        return "medium"
    return "low"


def build_handicap_margin_backtest_summary(settlements: Sequence[Mapping[str, object]] | object) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    known = [
        item
        for item in settlement_items
        if item.get("handicap_is_correct") is not None and item.get("handicap_margin_score") is not None
    ]
    buckets: dict[str, dict[str, object]] = {
        "low": {"bucket": "low", "count": 0, "hit_count": 0, "score_sum": 0.0, "signals": {}},
        "medium": {"bucket": "medium", "count": 0, "hit_count": 0, "score_sum": 0.0, "signals": {}},
        "high": {"bucket": "high", "count": 0, "hit_count": 0, "score_sum": 0.0, "signals": {}},
    }
    for item in known:
        bucket = _handicap_margin_bucket(item)
        row = buckets[bucket]
        row["count"] = _safe_int(row.get("count")) + 1
        row["hit_count"] = _safe_int(row.get("hit_count")) + (1 if item.get("handicap_is_correct") is True else 0)
        row["score_sum"] = _safe_float(row.get("score_sum")) + _safe_float(item.get("handicap_margin_score"))
        signal_counts = row.get("signals")
        if not isinstance(signal_counts, dict):
            signal_counts = {}
            row["signals"] = signal_counts
        signals = item.get("handicap_margin_signals") if isinstance(item.get("handicap_margin_signals"), list) else []
        for signal in signals:
            key = str(signal)
            signal_counts[key] = _safe_int(signal_counts.get(key)) + 1

    total = len(known)
    total_hits = sum(_safe_int(row.get("hit_count")) for row in buckets.values())
    overall_accuracy = total_hits / total if total else None
    rows: list[dict[str, object]] = []
    for bucket in ("high", "medium", "low"):
        row = buckets[bucket]
        count = _safe_int(row.get("count"))
        hit_count = _safe_int(row.get("hit_count"))
        miss_count = max(0, count - hit_count)
        hit_rate = hit_count / count if count else None
        avg_score = _safe_float(row.get("score_sum")) / count if count else None
        signal_counts = row.get("signals") if isinstance(row.get("signals"), dict) else {}
        top_signal = "-"
        if signal_counts:
            top_signal = sorted(signal_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))[0][0]
        rows.append(
            {
                "bucket": bucket,
                "label": _market_entropy_bucket_label(bucket),
                "count": count,
                "hit_count": hit_count,
                "miss_count": miss_count,
                "hit_rate": hit_rate,
                "hit_rate_text": _pct(hit_rate),
                "miss_rate_text": _pct(1.0 - hit_rate) if hit_rate is not None else "-",
                "avg_score": avg_score,
                "avg_score_text": _pct(avg_score),
                "top_signal": top_signal,
            }
        )
    high = next((row for row in rows if row.get("bucket") == "high"), {})
    medium = next((row for row in rows if row.get("bucket") == "medium"), {})
    low = next((row for row in rows if row.get("bucket") == "low"), {})
    high_count = _safe_int(high.get("count"))
    high_misses = _safe_int(high.get("miss_count"))
    high_hits = _safe_int(high.get("hit_count"))
    retained_count = _safe_int(medium.get("count")) + _safe_int(low.get("count"))
    retained_hits = _safe_int(medium.get("hit_count")) + _safe_int(low.get("hit_count"))
    retained_accuracy = retained_hits / retained_count if retained_count else None
    high_miss_rate = high_misses / high_count if high_count else None
    overall_miss_rate = 1.0 - overall_accuracy if overall_accuracy is not None else None
    if total < 5:
        recommendation = "collecting"
        recommendation_text = "样本不足，继续积累让球胜差一致性与让球赛果的联动。"
    elif high_count >= 3 and high_miss_rate is not None and overall_miss_rate is not None and high_miss_rate >= overall_miss_rate + 0.12:
        recommendation = "block_high_handicap_margin"
        recommendation_text = "HIGH 冲突场次让球失误明显更高，建议正式放行时过滤让球玩法。"
    elif high_count >= 3 and high_miss_rate is not None and high_miss_rate >= 0.45:
        recommendation = "observe_high_handicap_margin"
        recommendation_text = "HIGH 冲突场次让球失误偏高，建议降级为观察并增加人工复核。"
    else:
        recommendation = "monitor"
        recommendation_text = "暂未证明该过滤能稳定提升让球命中率，继续监控。"
    return {
        "sample_count": total,
        "overall_accuracy": overall_accuracy,
        "overall_accuracy_text": _pct(overall_accuracy),
        "retained_accuracy": retained_accuracy,
        "retained_accuracy_text": _pct(retained_accuracy),
        "avoidable_handicap_misses": high_misses,
        "opportunity_cost": high_hits,
        "high_bucket_count": high_count,
        "high_bucket_miss_rate": high_miss_rate,
        "high_bucket_miss_rate_text": _pct(high_miss_rate),
        "rows": rows,
        "recommendation": recommendation,
        "recommendation_text": recommendation_text,
        "summary_text": (
            f"样本 {total} | 让球全量 {_pct(overall_accuracy)} | 过滤HIGH后 {_pct(retained_accuracy)} | "
            f"可避让球错 {high_misses} / 机会成本 {high_hits}"
        ),
    }


def build_market_entropy_backtest_summary(settlements: Sequence[Mapping[str, object]] | object) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    known = [
        item
        for item in settlement_items
        if item.get("is_correct") is not None and item.get("market_entropy_score") is not None
    ]
    buckets: dict[str, dict[str, object]] = {
        "low": {"bucket": "low", "count": 0, "hit_count": 0, "score_sum": 0.0, "risk_applied": 0, "signals": {}},
        "medium": {"bucket": "medium", "count": 0, "hit_count": 0, "score_sum": 0.0, "risk_applied": 0, "signals": {}},
        "high": {"bucket": "high", "count": 0, "hit_count": 0, "score_sum": 0.0, "risk_applied": 0, "signals": {}},
    }
    for item in known:
        bucket = _market_entropy_bucket(item)
        row = buckets[bucket]
        row["count"] = _safe_int(row.get("count")) + 1
        row["hit_count"] = _safe_int(row.get("hit_count")) + (1 if item.get("is_correct") is True else 0)
        row["score_sum"] = _safe_float(row.get("score_sum")) + _safe_float(item.get("market_entropy_score"))
        row["risk_applied"] = _safe_int(row.get("risk_applied")) + (1 if item.get("market_entropy_risk_applied") else 0)
        signal_counts = row.get("signals")
        if not isinstance(signal_counts, dict):
            signal_counts = {}
            row["signals"] = signal_counts
        signals = item.get("market_entropy_signals") if isinstance(item.get("market_entropy_signals"), list) else []
        for signal in signals:
            key = str(signal)
            signal_counts[key] = _safe_int(signal_counts.get(key)) + 1

    total = len(known)
    total_hits = sum(_safe_int(row.get("hit_count")) for row in buckets.values())
    overall_accuracy = total_hits / total if total else None
    rows: list[dict[str, object]] = []
    for bucket in ("high", "medium", "low"):
        row = buckets[bucket]
        count = _safe_int(row.get("count"))
        hit_count = _safe_int(row.get("hit_count"))
        miss_count = max(0, count - hit_count)
        hit_rate = hit_count / count if count else None
        avg_score = _safe_float(row.get("score_sum")) / count if count else None
        signal_counts = row.get("signals") if isinstance(row.get("signals"), dict) else {}
        top_signal = "-"
        if signal_counts:
            top_signal = sorted(signal_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))[0][0]
        rows.append(
            {
                "bucket": bucket,
                "label": _market_entropy_bucket_label(bucket),
                "count": count,
                "hit_count": hit_count,
                "miss_count": miss_count,
                "hit_rate": hit_rate,
                "hit_rate_text": _pct(hit_rate),
                "miss_rate_text": _pct(1.0 - hit_rate) if hit_rate is not None else "-",
                "avg_score": avg_score,
                "avg_score_text": _pct(avg_score),
                "risk_applied_count": _safe_int(row.get("risk_applied")),
                "top_signal": top_signal,
            }
        )
    high = next((row for row in rows if row.get("bucket") == "high"), {})
    medium = next((row for row in rows if row.get("bucket") == "medium"), {})
    low = next((row for row in rows if row.get("bucket") == "low"), {})
    high_count = _safe_int(high.get("count"))
    high_misses = _safe_int(high.get("miss_count"))
    high_hits = _safe_int(high.get("hit_count"))
    retained_count = _safe_int(medium.get("count")) + _safe_int(low.get("count"))
    retained_hits = _safe_int(medium.get("hit_count")) + _safe_int(low.get("hit_count"))
    retained_accuracy = retained_hits / retained_count if retained_count else None
    high_miss_rate = high_misses / high_count if high_count else None
    overall_miss_rate = 1.0 - overall_accuracy if overall_accuracy is not None else None
    if total < 5:
        recommendation = "collecting"
        recommendation_text = "样本不足，继续记录 MarketEntropy 与赛果联动。"
    elif high_count >= 3 and high_miss_rate is not None and overall_miss_rate is not None and high_miss_rate >= overall_miss_rate + 0.12:
        recommendation = "block_high_entropy"
        recommendation_text = "高熵值场次显著更容易失误，建议正式放行时阻断 HIGH 桶。"
    elif high_count >= 3 and high_miss_rate is not None and high_miss_rate >= 0.45:
        recommendation = "observe_high_entropy"
        recommendation_text = "高熵值场次失误偏高，建议降级为观察并增加人工复核。"
    else:
        recommendation = "monitor"
        recommendation_text = "暂未证明高熵值过滤能显著提升命中率，继续监控。"
    return {
        "sample_count": total,
        "overall_accuracy": overall_accuracy,
        "overall_accuracy_text": _pct(overall_accuracy),
        "retained_accuracy": retained_accuracy,
        "retained_accuracy_text": _pct(retained_accuracy),
        "avoidable_misses": high_misses,
        "opportunity_cost": high_hits,
        "high_bucket_count": high_count,
        "high_bucket_miss_rate": high_miss_rate,
        "high_bucket_miss_rate_text": _pct(high_miss_rate),
        "rows": rows,
        "recommendation": recommendation,
        "recommendation_text": recommendation_text,
        "summary_text": (
            f"样本 {total} | 全量 {_pct(overall_accuracy)} | 过滤HIGH后 {_pct(retained_accuracy)} | "
            f"可避错 {high_misses} / 机会成本 {high_hits}"
        ),
    }


def build_strategy_allowlist_tuning_recommendation(
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    base_min_confidence: float = 0.50,
    base_active_strategy_min: int = 1,
) -> dict[str, object]:
    summary = build_strategy_allowlist_settlement_summary(settlements)
    known_count = _safe_int(summary.get("known_count"))
    hit_rate = summary.get("hit_rate")
    hit_rate_value = _safe_float(hit_rate, 0.0) if hit_rate is not None else None
    high_strategy_rate = summary.get("high_strategy_hit_rate")
    high_strategy_value = _safe_float(high_strategy_rate, 0.0) if high_strategy_rate is not None else None
    high_conf_misses = _safe_int(summary.get("high_conf_misses"))
    reasons: list[str] = []
    next_min_confidence = _safe_float(base_min_confidence)
    next_active_strategy_min = max(1, _safe_int(base_active_strategy_min, 1))
    medium_risk_allowed = True
    risk_policy = "\u5141\u8bb8\u4f4e/\u4e2d\u98ce\u9669\uff0c\u9ad8\u98ce\u9669\u7ee7\u7eed\u963b\u65ad"
    action = "collect"
    label = "\u7ee7\u7eed\u79ef\u7d2f\u6837\u672c"
    tone = "neutral"

    if known_count < 5:
        reasons.append(f"\u653e\u884c\u5df2\u7ed3\u7b97\u6837\u672c\u4ec5 {known_count} \u573a\uff0c\u4e0d\u8db3\u4ee5\u81ea\u52a8\u6539\u95e8\u69db\u3002")
    elif (
        (hit_rate_value is not None and hit_rate_value < 0.55)
        or high_conf_misses >= max(2, known_count // 4)
        or (high_strategy_value is not None and high_strategy_value < 0.60)
    ):
        action = "tighten"
        label = "\u6536\u7d27\u6b63\u5f0f\u653e\u884c"
        tone = "warning"
        if hit_rate_value is not None and hit_rate_value < 0.55:
            reasons.append(f"\u653e\u884c 1X2 \u547d\u4e2d\u7387 {summary.get('hit_rate_text')}\uff0c\u4f4e\u4e8e 55% \u89c2\u5bdf\u7ebf\u3002")
            next_min_confidence += 0.05 if hit_rate_value >= 0.45 else 0.08
        if high_conf_misses >= max(2, known_count // 4):
            reasons.append(f"\u9ad8\u7f6e\u4fe1\u5931\u8bef {high_conf_misses} \u573a\uff0c\u8bf4\u660e\u5f53\u524d\u7f6e\u4fe1\u8fc7\u6ee4\u504f\u677e\u3002")
            next_min_confidence += 0.03
            medium_risk_allowed = False
            risk_policy = "\u4ec5\u5141\u8bb8\u4f4e\u98ce\u9669\uff0c\u4e2d\u98ce\u9669\u964d\u4e3a\u89c2\u5bdf"
        if high_strategy_value is not None and high_strategy_value < 0.60:
            reasons.append(f"\u9ad8\u51c6\u7b56\u7565\u547d\u4e2d {summary.get('high_strategy_summary')}\uff0c\u5efa\u8bae\u589e\u52a0\u6b63\u5f0f\u7b56\u7565\u6570\u8981\u6c42\u3002")
            next_active_strategy_min = max(next_active_strategy_min, 2)
    elif hit_rate_value is not None and hit_rate_value >= 0.70 and (high_strategy_value is None or high_strategy_value >= 0.70):
        action = "hold"
        label = "\u7ef4\u6301\u95e8\u69db"
        tone = "good"
        reasons.append("\u653e\u884c\u547d\u4e2d\u548c\u9ad8\u51c6\u7b56\u7565\u8868\u73b0\u8fbe\u5230\u7a33\u5b9a\u533a\u95f4\uff0c\u6682\u4e0d\u653e\u5bbd\u8986\u76d6\u3002")
    else:
        action = "watch"
        label = "\u5c0f\u5e45\u89c2\u5bdf"
        tone = "neutral"
        reasons.append("\u653e\u884c\u8868\u73b0\u672a\u8fbe\u5230\u653e\u5bbd\u6761\u4ef6\uff0c\u4f46\u4e5f\u672a\u89e6\u53d1\u660e\u663e\u6536\u7d27\u6761\u4ef6\u3002")

    next_min_confidence = round(min(0.78, max(0.45, next_min_confidence)), 2)
    if action in {"collect", "hold", "watch"}:
        next_min_confidence = round(_safe_float(base_min_confidence), 2)

    rows = [
        ("\u52a8\u4f5c", label),
        ("\u6837\u672c", f"{known_count} \u573a | \u653e\u884c\u547d\u4e2d {summary.get('hit_rate_text', '-')}"),
        ("\u6700\u4f4e\u7f6e\u4fe1", f"{_safe_float(base_min_confidence):.2f} -> {next_min_confidence:.2f}"),
        ("\u9ad8\u51c6\u7b56\u7565\u6570", f"{max(1, _safe_int(base_active_strategy_min, 1))} -> {next_active_strategy_min}"),
        ("\u98ce\u9669\u9650\u5236", risk_policy),
        ("\u89e6\u53d1\u539f\u56e0", "\n".join(reasons) if reasons else "-"),
    ]
    return {
        "action": action,
        "label": label,
        "tone": tone,
        "known_count": known_count,
        "next_min_confidence": next_min_confidence,
        "next_active_strategy_min": next_active_strategy_min,
        "medium_risk_allowed": medium_risk_allowed,
        "risk_policy": risk_policy,
        "policy_update": {
            "min_confidence": next_min_confidence,
            "active_strategy_min": next_active_strategy_min,
            "medium_risk_allowed": medium_risk_allowed,
            "high_risk_allowed": False,
        },
        "reasons": reasons,
        "rows": rows,
        "summary": summary,
    }


def select_strategy_allowlist_rows(rows: Sequence[object] | object) -> list[object]:
    if not isinstance(rows, Sequence):
        return []
    allowed: list[object] = []
    for row in rows:
        admission = _strategy_admission(_row_prediction(row))
        if str(admission.get("decision") or "").strip() == "allow":
            allowed.append(row)
    return sorted(allowed, key=_allowlist_sort_key)


def build_strategy_allowlist_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"strategy_allowlist_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_strategy_policy_audit_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"strategy_policy_audit_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_strategy_policy_audit_csv_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"strategy_policy_audit_samples_{current.strftime('%Y%m%d_%H%M%S')}.csv"


def build_strategy_policy_audit_report_lines(
    policy_effect_review: Mapping[str, object] | object,
    *,
    generated_at: datetime | None = None,
) -> list[str]:
    review = _as_mapping(policy_effect_review)
    current = generated_at or datetime.now()
    rows = [row for row in _as_list(review.get("rows")) if isinstance(row, Mapping)]
    stability = _as_mapping(review.get("stability_monitor"))
    tuning_guard = build_strategy_policy_tuning_guard(stability, source="audit")
    lines = [
        "# \u7b56\u7565\u8c03\u53c2\u5ba1\u8ba1\u62a5\u544a",
        "",
        f"- \u751f\u6210\u65f6\u95f4: {current.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- \u7248\u672c\u6570: {review.get('history_count', 0)}",
        f"- \u6700\u65b0\u72b6\u6001: {review.get('latest_label', '-')}",
        f"- \u7248\u672c\u7a33\u5b9a: {stability.get('summary_text', '-')}",
        f"- \u8c03\u53c2\u95e8\u63a7: {tuning_guard.get('summary_text', '-')}",
        f"- \u6458\u8981: {review.get('summary_text', '-')}",
        "",
        "## \u7248\u672c\u7a33\u5b9a\u76d1\u63a7",
        "",
        f"- \u72b6\u6001: {stability.get('label', '-')}",
        f"- \u8bc4\u4f30\u7248\u672c: {stability.get('evaluated_count', 0)} / {stability.get('version_count', 0)}",
        f"- \u6700\u65b0\u547d\u4e2d: {stability.get('latest_allow_hit_rate_text', '-')}",
        f"- \u6700\u65b0\u73af\u6bd4: {stability.get('latest_delta_text', '-')}",
        f"- \u5e73\u5747\u6ce2\u52a8: {stability.get('avg_abs_delta_text', '-')}",
        f"- Replay\u7d2f\u8ba1\u51c0\u503c: {stability.get('cumulative_replay_net', 0):+d}"
        if isinstance(stability.get("cumulative_replay_net"), int)
        else f"- Replay\u7d2f\u8ba1\u51c0\u503c: {stability.get('cumulative_replay_net', 0)}",
        f"- \u5efa\u8bae: {stability.get('recommendation_text', '-')}",
        f"- \u8c03\u53c2\u95e8\u63a7: {tuning_guard.get('label', '-')} / {tuning_guard.get('body', '-')}",
        "",
        "| \u5468\u671f | \u7248\u672c | \u6837\u672c | \u653e\u884c\u547d\u4e2d | Replay\u51c0\u503c | \u6b63\u5411 | \u8d1f\u5411 | \u79ef\u7d2f |",
        "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    weekly_rows = [row for row in _as_list(stability.get("weekly_rows")) if isinstance(row, Mapping)]
    if weekly_rows:
        for row in weekly_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _text(row.get("week"), "-"),
                        str(_safe_int(row.get("version_count"))),
                        str(_safe_int(row.get("sample_count"))),
                        _text(row.get("allow_hit_rate_text"), "-"),
                        f"{_safe_int(row.get('replay_guard_net')):+d}",
                        str(_safe_int(row.get("effective_count"))),
                        str(_safe_int(row.get("negative_count"))),
                        str(_safe_int(row.get("collecting_count"))),
                    ]
                )
                + " |"
            )
    else:
        lines.append("| - | 0 | 0 | - | 0 | 0 | 0 | 0 |")
    lines.extend(
        [
            "",
        "## \u7248\u672c\u6548\u679c\u603b\u89c8",
        "",
        "| \u7248\u672c | \u65f6\u95f4 | \u6765\u6e90 | \u6548\u679c | \u6837\u672c | \u653e\u884c\u547d\u4e2d | Replay\u51c0\u503c | \u56de\u6eda\u5efa\u8bae |",
        "| --- | --- | --- | --- | ---: | --- | ---: | --- |",
        ]
    )
    if not rows:
        lines.extend(["| - | - | - | \u6682\u65e0\u7248\u672c | 0 | - | 0 | - |", ""])
        return lines
    for row in rows:
        diagnostics = _as_mapping(row.get("negative_diagnostics"))
        lines.append(
            "| "
            + " | ".join(
                [
                    _text(row.get("version_id"), "-"),
                    _text(row.get("updated_at"), "-"),
                    _text(row.get("source"), "-"),
                    _text(row.get("effect_label"), "-"),
                    str(_safe_int(row.get("sample_count"))),
                    _text(row.get("allow_hit_rate_text"), "-"),
                    f"{_safe_int(row.get('replay_guard_net')):+d}",
                    _text(diagnostics.get("action_label"), "-"),
                ]
            )
            + " |"
        )
    lines.extend(["", "## \u8d1f\u5411\u7248\u672c\u5b9a\u4f4d", ""])
    for row in rows:
        diagnostics = _as_mapping(row.get("negative_diagnostics"))
        negative_rows = [item for item in _as_list(diagnostics.get("top_negative_rows")) if isinstance(item, Mapping)]
        if not negative_rows and not bool(diagnostics.get("rollback_recommended")):
            continue
        lines.extend(
            [
                f"### {_text(row.get('version_id'), '-')} | {_text(row.get('effect_label'), '-')}",
                "",
                f"- \u8bca\u65ad: {diagnostics.get('summary_text', '-')}",
                f"- \u4e3b\u56e0: {diagnostics.get('top_negative_reason', '-')}",
                f"- \u662f\u5426\u5efa\u8bae\u56de\u6eda: {'YES' if diagnostics.get('rollback_recommended') else 'NO'}",
                "",
                "| \u65f6\u95f4 | \u8d5b\u4e8b | \u51c6\u5165 | 1X2 | \u8ba9\u7403 | Replay | Agent | \u51c0\u503c | \u62d6\u7d2f\u539f\u56e0 |",
                "| --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
            ]
        )
        for sample in negative_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _text(sample.get("time"), "-"),
                        _text(sample.get("title"), "-"),
                        _text(sample.get("decision"), "-"),
                        _text(sample.get("prediction_result"), "-"),
                        _text(sample.get("handicap_result"), "-"),
                        _text(sample.get("replay_guard"), "-"),
                        _text(sample.get("replay_agent"), "-"),
                        f"{_safe_int(sample.get('replay_net_hint')):+d}",
                        _text(sample.get("drag_reason_text"), "-"),
                    ]
                )
                + " |"
            )
        lines.append("")
    lines.extend(["## \u5168\u91cf\u6837\u672c\u660e\u7ec6", ""])
    for row in rows:
        sample_rows = [item for item in _as_list(row.get("sample_rows")) if isinstance(item, Mapping)]
        lines.extend(
            [
                f"### {_text(row.get('version_id'), '-')} | {_text(row.get('updated_at'), '-')}",
                "",
                "| \u65f6\u95f4 | \u8d5b\u4e8b | \u51c6\u5165 | 1X2 | \u8ba9\u7403 | Replay | Agent | \u51c0\u503c | \u5f71\u54cd\u539f\u56e0 |",
                "| --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
            ]
        )
        if not sample_rows:
            lines.append("| - | - | - | - | - | - | - | 0 | - |")
        for sample in sample_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _text(sample.get("time"), "-"),
                        _text(sample.get("title"), "-"),
                        _text(sample.get("decision"), "-"),
                        _text(sample.get("prediction_result"), "-"),
                        _text(sample.get("handicap_result"), "-"),
                        _text(sample.get("replay_guard"), "-"),
                        _text(sample.get("replay_agent"), "-"),
                        f"{_safe_int(sample.get('replay_net_hint')):+d}",
                        _text(sample.get("drag_reason_text"), "-"),
                    ]
                )
                + " |"
            )
        lines.append("")
    return lines


def build_strategy_policy_audit_csv_text(policy_effect_review: Mapping[str, object] | object) -> str:
    review = _as_mapping(policy_effect_review)
    rows = [row for row in _as_list(review.get("rows")) if isinstance(row, Mapping)]
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "version_id",
            "updated_at",
            "source",
            "effect_label",
            "rollback_recommended",
            "match_id",
            "time",
            "match",
            "decision",
            "prediction_result",
            "handicap_result",
            "replay_guard",
            "replay_agent",
            "replay_net_hint",
            "drag_score",
            "drag_reason",
        ]
    )
    for row in rows:
        diagnostics = _as_mapping(row.get("negative_diagnostics"))
        for sample in [item for item in _as_list(row.get("sample_rows")) if isinstance(item, Mapping)]:
            writer.writerow(
                [
                    _text(row.get("version_id"), "-"),
                    _text(row.get("updated_at"), "-"),
                    _text(row.get("source"), "-"),
                    _text(row.get("effect_label"), "-"),
                    "YES" if diagnostics.get("rollback_recommended") else "NO",
                    _text(sample.get("match_id"), "-"),
                    _text(sample.get("time"), "-"),
                    _text(sample.get("title"), "-"),
                    _text(sample.get("decision"), "-"),
                    _text(sample.get("prediction_result"), "-"),
                    _text(sample.get("handicap_result"), "-"),
                    _text(sample.get("replay_guard"), "-"),
                    _text(sample.get("replay_agent"), "-"),
                    _safe_int(sample.get("replay_net_hint")),
                    _safe_int(sample.get("drag_score")),
                    _text(sample.get("drag_reason_text"), "-"),
                ]
            )
    return output.getvalue()


def build_strategy_allowlist_report_lines(
    rows: Sequence[object] | object,
    *,
    generated_at: datetime | None = None,
    settlements: Sequence[Mapping[str, object]] | object | None = None,
) -> list[str]:
    current = generated_at or datetime.now()
    allowed = select_strategy_allowlist_rows(rows)
    lines = [
        "# \u7b56\u7565\u653e\u884c\u6e05\u5355",
        "",
        f"- \u751f\u6210\u65f6\u95f4: {current.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- \u6b63\u5f0f\u653e\u884c\u573a\u6b21: {len(allowed)}",
        "",
    ]
    if not allowed:
        lines.extend(
            [
                "\u5f53\u524d\u6ca1\u6709\u7b56\u7565\u51c6\u5165\u4e3a\u6b63\u5f0f\u653e\u884c\u7684\u573a\u6b21\u3002",
                "",
                "## \u8d5b\u524d\u590d\u6838\u539f\u5219",
                "",
            ]
        )
        lines.extend(f"- [ ] {item}" for item in PRE_MATCH_REVIEW_CHECKLIST)
        return lines

    lines.extend(
        [
            "## \u653e\u884c\u573a\u6b21",
            "",
        ]
    )
    for index, row in enumerate(allowed, start=1):
        match = _row_match(row)
        prediction = _row_prediction(row)
        admission = _strategy_admission(prediction)
        home = _text(_field(match, "home_team"))
        away = _text(_field(match, "away_team"))
        league = _text(_field(match, "league"))
        title = f"### {index}. {league} | {home} vs {away}"
        lines.extend(
            [
                title,
                "",
                "| \u5b57\u6bb5 | \u5185\u5bb9 |",
                "|---|---|",
                f"| \u5f00\u8d5b\u65f6\u95f4 | {_md_cell(_field(match, 'match_date'))} {_md_cell(_field(match, 'match_time'))} |",
                f"| \u6570\u636e\u6e90 | {_md_cell(_field(match, 'source'))} / {_md_cell(_field(match, 'source_id'))} |",
                f"| \u51c6\u5165\u7ed3\u8bba | {_md_cell(_admission_label(admission))} |",
                f"| \u51c6\u5165\u52a8\u4f5c | {_md_cell(format_strategy_admission_action(admission))} |",
                f"| \u63a8\u8350 | {_md_cell(prediction.get('recommendation'))} |",
                f"| \u7f6e\u4fe1\u5ea6 | {_pct(prediction.get('confidence'))} |",
                f"| \u98ce\u9669\u7b49\u7ea7 | {_md_cell(_risk_text(prediction.get('risk_level')))} |",
                f"| \u9ad8\u51c6\u7b56\u7565 | \u6b63\u5f0f {_safe_int(admission.get('active_count'))} / \u89c2\u5bdf {_safe_int(admission.get('shadow_count'))} / \u5355\u73a9\u6cd5 {_safe_int(admission.get('single_play_count'))} |",
                f"| \u5019\u9009\u73a9\u6cd5 | {_md_cell(format_strategy_admission_pick(admission))} |",
                f"| \u51c6\u5165\u539f\u56e0 | {_md_cell(_admission_reasons(admission))} |",
                f"| \u51c6\u5165\u95e8\u69db | {_md_cell(format_strategy_admission_thresholds(admission))} |",
                f"| \u6458\u8981 | {_md_cell(admission.get('summary'))} |",
                "",
                "\u8d5b\u524d\u590d\u6838\u6e05\u5355",
                "",
            ]
        )
        lines.extend(f"- [ ] {item}" for item in PRE_MATCH_REVIEW_CHECKLIST)
        lines.append("")
    error_attribution = build_strategy_error_attribution_summary(settlements or [])
    if _safe_int(error_attribution.get("miss_count")) or _safe_int(error_attribution.get("unknown_count")):
        evaluation_agent = build_strategy_evaluation_agent_summary({}, settlements or [])
        statsbomb_review = build_statsbomb_event_review_summary(settlements or [])
        lines.extend(
            [
                "## \u6700\u8fd1\u590d\u76d8\u9519\u56e0",
                "",
                f"- Evaluation Agent: {evaluation_agent.get('status') or '-'} / {evaluation_agent.get('score') or '-'}",
                f"- \u8bc4\u4f30\u6458\u8981: {evaluation_agent.get('summary_text') or '-'}",
                f"- \u4e3b\u8981\u9519\u56e0: {error_attribution.get('top_reason') or '-'}",
                f"- \u9519\u56e0\u9879: {_safe_int(error_attribution.get('miss_count'))}",
                f"- \u5f85\u5224\u5b9a: {_safe_int(error_attribution.get('unknown_count'))}",
                "",
            ]
        )
        if _safe_int(statsbomb_review.get("sample_count")):
            lines.extend(
                [
                    "### StatsBomb \u8d5b\u540e\u4e8b\u4ef6\u590d\u76d8",
                    "",
                    f"- \u6458\u8981: {statsbomb_review.get('summary_text') or '-'}",
                    f"- xG\u5bf9\u9f50: {statsbomb_review.get('xg_alignment_rate_text') or '-'}",
                    f"- \u7ec8\u7ed3\u6ce2\u52a8: {statsbomb_review.get('finishing_variance_rate_text') or '-'}",
                    f"- \u6ce8\u610f: {statsbomb_review.get('leakage_note') or '-'}",
                    "",
                ]
            )
            for row in statsbomb_review.get("rows", []) if isinstance(statsbomb_review.get("rows"), list) else []:
                if isinstance(row, Mapping):
                    lines.extend([f"- {row.get('title') or '-'}: {_md_cell(row.get('body'))}", ""])
        recommendations = evaluation_agent.get("recommendations", []) if isinstance(evaluation_agent.get("recommendations"), list) else []
        if recommendations:
            lines.extend(["### Evaluation Agent \u5efa\u8bae", ""])
            for item in recommendations[:5]:
                if isinstance(item, Mapping):
                    lines.append(f"- {item.get('title') or '-'}: {item.get('body') or '-'}")
            lines.append("")
        rows_payload = error_attribution.get("rows", []) if isinstance(error_attribution.get("rows"), list) else []
        for row in rows_payload[:5]:
            if not isinstance(row, Mapping):
                continue
            lines.extend(
                [
                    f"### \u9519\u56e0\u6837\u672c: {row.get('title') or '-'}",
                    "",
                    str(row.get("body") or "-"),
                    "",
                ]
            )
    return lines


def build_high_accuracy_strategy_dashboard(
    status: Mapping[str, object] | object,
    settlements: Sequence[Mapping[str, object]] | object,
    policy_history: Sequence[Mapping[str, object]] | object | None = None,
    statsbomb_event_baseline: Mapping[str, object] | object | None = None,
    statsbomb_fewshot_memory: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    resolved = _as_mapping(status)
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    pool = _strategy_pool(resolved)
    validation = _as_mapping(resolved.get("validation"))
    breaker = _as_mapping(resolved.get("breaker"))
    settlement_summary = build_high_accuracy_strategy_settlement_summary(settlement_items)
    error_attribution = build_strategy_error_attribution_summary(settlement_items)
    agent_trace_replay = build_agent_trace_replay_summary(settlement_items)
    agent_replay_downgrade = build_agent_replay_downgrade_backtest_summary(settlement_items)
    agent_replay_guard_tuning = build_agent_replay_guard_tuning_recommendation(settlement_items)
    allowlist_summary = build_strategy_allowlist_settlement_summary(settlement_items)
    allowlist_tuning = build_strategy_allowlist_tuning_recommendation(settlement_items)
    policy_effect_review = build_strategy_policy_effect_review(policy_history or [], settlement_items)
    policy_stability_monitor = _as_mapping(policy_effect_review.get("stability_monitor"))
    policy_tuning_guard = build_strategy_policy_tuning_guard(policy_stability_monitor, source="dashboard")
    market_entropy_backtest = build_market_entropy_backtest_summary(settlement_items)
    handicap_margin_backtest = build_handicap_margin_backtest_summary(settlement_items)
    jc_bucket_feedback = build_jc_bucket_feedback_summary(resolved, settlement_items)
    statsbomb_event_review = build_statsbomb_event_review_summary(settlement_items, statsbomb_event_baseline or {})
    evaluation_agent = build_strategy_evaluation_agent_summary(
        resolved,
        settlement_items,
        statsbomb_event_baseline or {},
        statsbomb_fewshot_memory or {},
    )
    statsbomb_fewshot_monitor = build_statsbomb_fewshot_memory_monitor(
        statsbomb_fewshot_memory or {},
        _as_mapping(evaluation_agent.get("statsbomb_fewshot_memory")),
    )
    statsbomb_backfill_queue = build_statsbomb_fewshot_backfill_queue(
        statsbomb_fewshot_monitor,
        _as_mapping(evaluation_agent.get("statsbomb_fewshot_quality")),
        settlement_items,
        statsbomb_event_baseline or {},
    )
    stable_count = sum(1 for item in pool if bool(_strategy_stability(item).get("stable")))
    primary_count = sum(1 for item in pool if str(item.get("role") or "") == "primary")
    backup_count = sum(1 for item in pool if str(item.get("role") or "") == "backup")
    paused_count = _safe_int(breaker.get("paused_count"))
    known_count = _safe_int(settlement_summary.get("known_count"))
    hit_rate = settlement_summary.get("hit_rate")
    hit_tone = "neutral"
    if known_count:
        hit_tone = "good" if _safe_float(hit_rate) >= 0.6 else "warning"

    metrics = [
        {"label": "\u7b56\u7565\u6c60", "value": str(len(pool)), "tone": "info"},
        {"label": "\u7a33\u5b9a\u7b56\u7565", "value": f"{stable_count}/{len(pool)}", "tone": "good" if stable_count else "warning"},
        {"label": "\u65ad\u8def\u6682\u505c", "value": str(paused_count), "tone": "bad" if paused_count else "good"},
        {
            "label": "\u56de\u6d4b\u8bb0\u5f55",
            "value": str(_safe_int(validation.get("record_count"))),
            "tone": "neutral",
        },
        {"label": "\u771f\u5b9e\u547d\u4e2d", "value": str(settlement_summary.get("hit_rate_text") or "-"), "tone": hit_tone},
        {
            "label": "\u7b56\u7565\u9519\u56e0",
            "value": str(error_attribution.get("top_reason") or "-"),
            "tone": "warning" if _safe_int(error_attribution.get("miss_count")) else "good",
        },
        {
            "label": "Agent Replay",
            "value": str(agent_trace_replay.get("top_agent") or "-"),
            "tone": "warning" if _safe_int(agent_trace_replay.get("agent_count")) else "neutral",
        },
        {
            "label": "Replay Guard",
            "value": str(agent_replay_downgrade.get("net", 0)),
            "tone": "good"
            if _safe_int(agent_replay_downgrade.get("net")) > 0
            else "bad"
            if _safe_int(agent_replay_downgrade.get("net")) < 0
            else "neutral",
        },
        {
            "label": "Replay Tuning",
            "value": str(agent_replay_guard_tuning.get("label") or "-"),
            "tone": str(agent_replay_guard_tuning.get("tone") or "neutral"),
        },
        {
            "label": "\u8c03\u53c2\u751f\u6548",
            "value": str(policy_effect_review.get("latest_label") or "-"),
            "tone": "good"
            if str(policy_effect_review.get("latest_status") or "") == "effective"
            else "bad"
            if str(policy_effect_review.get("latest_status") or "") == "negative"
            else "neutral",
        },
        {
            "label": "\u7248\u672c\u7a33\u5b9a",
            "value": str(policy_stability_monitor.get("label") or "-"),
            "tone": str(policy_stability_monitor.get("tone") or "neutral"),
        },
        {
            "label": "\u8c03\u53c2\u95e8\u63a7",
            "value": str(policy_tuning_guard.get("label") or "-"),
            "tone": str(policy_tuning_guard.get("tone") or "neutral"),
        },
        {
            "label": "Evaluation",
            "value": f"{evaluation_agent.get('status', '-')} / {evaluation_agent.get('score', '-')}",
            "tone": "bad"
            if str(evaluation_agent.get("status") or "") == "tighten"
            else "warning"
            if str(evaluation_agent.get("status") or "") in {"watch", "collecting"}
            else "good",
        },
        {
            "label": "StatsBomb",
            "value": str(statsbomb_event_review.get("summary_text") or "-"),
            "tone": "warning"
            if str(statsbomb_event_review.get("status") or "") in {"variance_watch", "control_gap_watch"}
            else "good"
            if _safe_int(statsbomb_event_review.get("sample_count"))
            else "neutral",
        },
        {
            "label": "SB Memory",
            "value": str(statsbomb_fewshot_monitor.get("summary_text") or "-"),
            "tone": "good"
            if _safe_int(statsbomb_fewshot_monitor.get("current_matched_count"))
            else "warning"
            if str(statsbomb_fewshot_monitor.get("status") or "") == "standby"
            else "neutral",
        },
        {
            "label": "SB Backfill",
            "value": str(statsbomb_backfill_queue.get("summary_text") or "-"),
            "tone": "warning" if _safe_int(statsbomb_backfill_queue.get("task_count")) else "good",
        },
        {
            "label": "JC\u7a33\u5b9a\u6876",
            "value": str(jc_bucket_feedback.get("summary_text") or "-"),
            "tone": "bad"
            if _safe_int(_as_mapping(jc_bucket_feedback.get("status_counts")).get("downgraded"))
            else "warning"
            if _safe_int(_as_mapping(jc_bucket_feedback.get("status_counts")).get("watch"))
            else "good"
            if _safe_int(jc_bucket_feedback.get("total"))
            else "neutral",
        },
        {
            "label": "\u653e\u884c\u547d\u4e2d",
            "value": str(allowlist_summary.get("hit_rate_text") or "-"),
            "tone": "good" if _safe_float(allowlist_summary.get("hit_rate")) >= 0.6 else "warning" if _safe_int(allowlist_summary.get("known_count")) else "neutral",
        },
        {
            "label": "Entropy避险",
            "value": str(market_entropy_backtest.get("retained_accuracy_text") or "-"),
            "tone": "good"
            if str(market_entropy_backtest.get("recommendation") or "") == "block_high_entropy"
            else "warning"
            if str(market_entropy_backtest.get("recommendation") or "") in {"observe_high_entropy", "collecting"}
            else "neutral",
        },
        {
            "label": "Handicap Margin",
            "value": str(handicap_margin_backtest.get("retained_accuracy_text") or "-"),
            "tone": "good"
            if str(handicap_margin_backtest.get("recommendation") or "") == "block_high_handicap_margin"
            else "warning"
            if str(handicap_margin_backtest.get("recommendation") or "") in {"observe_high_handicap_margin", "collecting"}
            else "neutral",
        },
    ]
    validation_rows = [
        (
            "\u6837\u672c\u6765\u6e90",
            f"APP {_safe_int(validation.get('settlement_record_count'))} | \u5386\u53f2\u5e02\u573a {_safe_int(validation.get('historical_record_count'))}",
        ),
        (
            "\u5019\u9009\u7b56\u7565",
            f"{_safe_int(validation.get('candidate_count'))} | \u7a33\u5b9a {_safe_int(validation.get('stable_candidate_count'))}",
        ),
        ("\u65f6\u95f4\u8303\u56f4", f"{validation.get('date_start') or '-'} -> {validation.get('date_end') or '-'}"),
        (
            "\u7ed3\u7b97\u547d\u4e2d",
            f"\u6b63\u5f0f {settlement_summary.get('official_summary_text')} | \u89c2\u5bdf {settlement_summary.get('shadow_summary_text')} | \u672a\u5224\u5b9a {_safe_int(settlement_summary.get('unknown_count'))}",
        ),
    ]
    if not bool(resolved.get("enabled")):
        guidance = [
            {
                "title": "\u7b56\u7565\u6c60\u672a\u542f\u7528",
                "body": "\u9700\u5148\u6267\u884c\u9ad8\u51c6\u7b56\u7565\u56de\u6d4b\uff0c\u751f\u6210\u7b56\u7565\u6c60\u540e\u518d\u8fdb\u884c\u8d5b\u524d\u7b5b\u9009\u3002",
            }
        ]
    else:
        guidance = [
            {
                "title": "\u5206\u5c42\u4f7f\u7528",
                "body": f"\u4e3b\u7b56\u7565 {primary_count} \u6761\uff0c\u5907\u9009 {backup_count} \u6761\u3002\u4e3b\u7b56\u7565\u53ea\u5e94\u5728\u547d\u4e2d\u95e8\u69db\u548c\u98ce\u9669\u8fc7\u6ee4\u540c\u65f6\u901a\u8fc7\u65f6\u751f\u6548\u3002",
            },
            {
                "title": "\u590d\u76d8\u8981\u6c42",
                "body": "\u6bcf\u6b21\u8d5b\u679c\u56de\u6536\u540e\u8981\u89c2\u5bdf\u771f\u5b9e\u547d\u4e2d\u7387\u3002\u82e5\u8fde\u7eed\u672a\u547d\u4e2d\uff0c\u4e0b\u4e00\u6b65\u5e94\u52a0\u65ad\u8def\u5668\u800c\u4e0d\u662f\u7ee7\u7eed\u6269\u5927\u8986\u76d6\u3002",
            },
        ]
        if paused_count:
            guidance.insert(
                0,
                {
                    "title": "\u65ad\u8def\u5668\u5df2\u89e6\u53d1",
                    "body": f"{paused_count} \u6761\u7b56\u7565\u56e0\u771f\u5b9e\u7ed3\u7b97\u8fde\u9519\u5df2\u964d\u4e3a\u89c2\u5bdf\u3002\u7b56\u7565\u4ecd\u4f1a\u8bb0\u5f55\u5f71\u5b50\u7ed3\u7b97\uff0c\u8fde\u7eed\u8fbe\u5230\u6062\u590d\u547d\u4e2d\u8981\u6c42\u540e\u81ea\u52a8\u6062\u590d\u3002",
                },
            )
    return {
        "enabled": bool(resolved.get("enabled")),
        "updated_at": resolved.get("updated_at") or "-",
        "reason": resolved.get("reason") or "-",
        "metrics": metrics,
        "pool_rows": build_high_accuracy_strategy_pool_rows(resolved),
        "settlement_rows": build_high_accuracy_strategy_settlement_rows(settlement_items),
        "error_attribution": error_attribution,
        "agent_trace_replay": agent_trace_replay,
        "agent_replay_downgrade": agent_replay_downgrade,
        "agent_replay_guard_tuning": agent_replay_guard_tuning,
        "evaluation_agent": evaluation_agent,
        "statsbomb_event_review": statsbomb_event_review,
        "statsbomb_fewshot_monitor": statsbomb_fewshot_monitor,
        "statsbomb_backfill_queue": statsbomb_backfill_queue,
        "jc_bucket_feedback": jc_bucket_feedback,
        "allowlist_settlement_rows": build_strategy_allowlist_settlement_rows(settlement_items),
        "validation_rows": validation_rows,
        "guidance_rows": guidance,
        "settlement_summary": settlement_summary,
        "allowlist_settlement_summary": allowlist_summary,
        "allowlist_tuning": allowlist_tuning,
        "policy_effect_review": policy_effect_review,
        "policy_stability_monitor": policy_stability_monitor,
        "policy_tuning_guard": policy_tuning_guard,
        "market_entropy_backtest": market_entropy_backtest,
        "handicap_margin_backtest": handicap_margin_backtest,
    }
