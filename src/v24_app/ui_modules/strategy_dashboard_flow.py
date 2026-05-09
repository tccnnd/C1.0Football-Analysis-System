from __future__ import annotations

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


def _pct(value: object, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}%}"
    except (TypeError, ValueError):
        return "-"


def _label(labels: Mapping[str, str], value: object) -> str:
    key = str(value or "").strip()
    return labels.get(key, key or "-")


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
    hits = sum(1 for item in known if item.get("is_hit") is True)
    misses = sum(1 for item in known if item.get("is_hit") is False)
    unknown = len(rows) - len(known)
    hit_rate = hits / len(known) if known else None
    return {
        "active_count": len(rows),
        "known_count": len(known),
        "hit_count": hits,
        "miss_count": misses,
        "unknown_count": unknown,
        "hit_rate": hit_rate,
        "hit_rate_text": _pct(hit_rate) if hit_rate is not None else "-",
        "summary_text": f"{hits}/{len(known)}" if known else "-",
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
                f"\u65ad\u8def: {breaker_status} | \u8fde\u9519 {_safe_int(breaker.get('miss_streak'))}/{_safe_int(breaker.get('threshold'), 3)} | \u8fd1\u671f {_safe_int(breaker.get('hit_count'))}/{_safe_int(breaker.get('known_count'))}",
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
        title = f"{hit_label} | {_label(ROLE_LABELS, item.get('role'))} | {_label(PLAY_LABELS, item.get('play_type'))}"
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
            f"{settlement_summary.get('summary_text')} | \u6d3b\u8dc3 {_safe_int(settlement_summary.get('active_count'))} | \u672a\u5224\u5b9a {_safe_int(settlement_summary.get('unknown_count'))}",
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
                    "body": f"{paused_count} \u6761\u7b56\u7565\u56e0\u771f\u5b9e\u7ed3\u7b97\u8fde\u9519\u5df2\u964d\u4e3a\u89c2\u5bdf\u3002\u9700\u8981\u7b49\u5f85\u65b0\u547d\u4e2d\u6837\u672c\u6216\u91cd\u65b0\u56de\u6d4b\u540e\u518d\u6062\u590d\u3002",
                },
            )
    return {
        "enabled": bool(resolved.get("enabled")),
        "updated_at": resolved.get("updated_at") or "-",
        "reason": resolved.get("reason") or "-",
        "metrics": metrics,
        "pool_rows": build_high_accuracy_strategy_pool_rows(resolved),
        "settlement_rows": build_high_accuracy_strategy_settlement_rows(settlement_items),
        "validation_rows": validation_rows,
        "guidance_rows": guidance,
        "settlement_summary": settlement_summary,
    }
