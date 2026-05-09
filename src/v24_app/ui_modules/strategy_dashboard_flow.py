from __future__ import annotations

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
}
SCOPE_LABELS = {
    "global": "\u5168\u5c40",
    "league": "\u8054\u8d5b",
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
        body = "\n".join(
            [
                f"\u8303\u56f4: {scope} / {item.get('scope_value') or '-'} | \u6570\u636e\u5c42: {data_layer}",
                f"\u95e8\u69db: {_safe_float(item.get('min_confidence')):.2f} | \u56de\u6d4b: {_pct(item.get('accuracy'))} ({_safe_int(item.get('hit_count'))}/{_safe_int(item.get('sample_count'))})",
                f"Wilson: {_pct(item.get('wilson_lower'))} | \u8986\u76d6: {_pct(item.get('coverage'))} | \u8fb9\u9645: {_safe_float(item.get('edge')):+.1%}",
                f"\u7a33\u5b9a: {'OK' if bool(stability.get('stable')) else 'WATCH'} | \u8bc4\u5206 {_pct(stability.get('stability_score'))} | \u8fd130/90 {_pct(stability.get('recent_30_accuracy'))}/{_pct(stability.get('recent_90_accuracy'))}",
                f"\u65ad\u8def: {breaker_status} | \u8fde\u9519 {_safe_int(breaker.get('miss_streak'))}/{_safe_int(breaker.get('threshold'), 3)} | \u6062\u590d {_safe_int(breaker.get('recovery_streak'))}/{_safe_int(breaker.get('recovery_hits_required'), 2)} | \u8fd1\u671f {_safe_int(breaker.get('hit_count'))}/{_safe_int(breaker.get('known_count'))}",
            ]
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


def build_strategy_allowlist_report_lines(
    rows: Sequence[object] | object,
    *,
    generated_at: datetime | None = None,
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
    return lines


def build_high_accuracy_strategy_dashboard(
    status: Mapping[str, object] | object,
    settlements: Sequence[Mapping[str, object]] | object,
) -> dict[str, object]:
    resolved = _as_mapping(status)
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    pool = _strategy_pool(resolved)
    validation = _as_mapping(resolved.get("validation"))
    breaker = _as_mapping(resolved.get("breaker"))
    settlement_summary = build_high_accuracy_strategy_settlement_summary(settlement_items)
    allowlist_summary = build_strategy_allowlist_settlement_summary(settlement_items)
    allowlist_tuning = build_strategy_allowlist_tuning_recommendation(settlement_items)
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
            "label": "\u653e\u884c\u547d\u4e2d",
            "value": str(allowlist_summary.get("hit_rate_text") or "-"),
            "tone": "good" if _safe_float(allowlist_summary.get("hit_rate")) >= 0.6 else "warning" if _safe_int(allowlist_summary.get("known_count")) else "neutral",
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
        "allowlist_settlement_rows": build_strategy_allowlist_settlement_rows(settlement_items),
        "validation_rows": validation_rows,
        "guidance_rows": guidance,
        "settlement_summary": settlement_summary,
        "allowlist_settlement_summary": allowlist_summary,
        "allowlist_tuning": allowlist_tuning,
    }
