from __future__ import annotations

from datetime import datetime
from typing import Mapping, Sequence


STATUS_LABELS = {
    "running": "\u8fd0\u884c\u4e2d",
    "success": "\u6210\u529f",
    "failed": "\u5931\u8d25",
    "interrupted": "\u4e2d\u65ad",
}


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pct_text_to_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        number = float(value)
        return number / 100.0 if number > 1 else number
    text = str(value or "").strip()
    if not text or text == "-":
        return None
    try:
        if text.endswith("%"):
            return float(text[:-1].strip()) / 100.0
        number = float(text)
        return number / 100.0 if number > 1 else number
    except ValueError:
        return None


def _pct_text(value: float | None) -> str:
    return f"{value:.1%}" if value is not None else "-"


def _status_label(status: object) -> str:
    key = str(status or "").strip().lower()
    return STATUS_LABELS.get(key, key or "-")


def _elapsed_text(value: object) -> str:
    seconds = _safe_float(value, default=-1.0)
    if seconds < 0:
        return "-"
    return f"{seconds:.2f}s"


def _reason_counts_text(value: object) -> str:
    reasons = value if isinstance(value, Mapping) else {}
    rows = [(str(key), _safe_int(count, 0)) for key, count in reasons.items()]
    rows = [(key, count) for key, count in rows if key and count > 0]
    if not rows:
        return "-"
    return ", ".join(f"{key}={count}" for key, count in sorted(rows))


def _miss_items_text(value: object, limit: int = 5) -> str:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return "- \u65e0"
    rows: list[str] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        teams = f"{raw.get('home_team') or '-'} vs {raw.get('away_team') or '-'}"
        score = f"{raw.get('home_goals')}-{raw.get('away_goals')}"
        rows.append(
            f"- {raw.get('match_date') or '-'} {raw.get('league') or '-'} {teams} | "
            f"reason={raw.get('reason') or '-'} | state={raw.get('state_code') or '-'} | "
            f"score={score} | sid={raw.get('schedule_id') or '-'}"
        )
        if len(rows) >= max(1, int(limit)):
            break
    return "\n".join(rows) if rows else "- \u65e0"


def _hit_stats(items: Sequence[Mapping[str, object]], field: str) -> dict[str, object]:
    known = [item for item in items if item.get(field) is True or item.get(field) is False]
    hits = sum(1 for item in known if item.get(field) is True)
    total = len(known)
    rate = (hits / total) if total else None
    return {
        "hits": hits,
        "total": total,
        "rate": rate,
        "text": f"{hits}/{total} ({rate:.0%})" if rate is not None else "-",
    }


def build_result_recovery_strategy_adjustment(
    review_summary: Mapping[str, object] | object,
    *,
    base_min_confidence: float = 0.50,
    base_active_strategy_min: int = 1,
    base_medium_risk_allowed: bool = True,
) -> dict[str, object]:
    summary = _as_mapping(review_summary)
    settlement_count = _safe_int(summary.get("settlement_count"), 0)
    plays = _as_mapping(summary.get("plays"))
    high_strategy = _as_mapping(summary.get("high_accuracy_strategy"))
    reasons: list[str] = []
    action = "collect"
    label = "\u7ee7\u7eed\u79ef\u7d2f\u6837\u672c"
    tone = "neutral"
    priority = "low"
    next_min_confidence = round(max(0.45, min(0.78, _safe_float(base_min_confidence, 0.50))), 2)
    next_active_strategy_min = max(1, _safe_int(base_active_strategy_min, 1))
    medium_risk_allowed = bool(base_medium_risk_allowed)

    if settlement_count < 3:
        reasons.append(f"\u672c\u8f6e\u53ea\u6709 {settlement_count} \u573a\u65b0\u7ed3\u7b97\uff0c\u6837\u672c\u4e0d\u8db3\uff0c\u6682\u4e0d\u5efa\u8bae\u8c03\u95e8\u69db\u3002")
    else:
        one_x_two = _as_mapping(plays.get("1X2"))
        handicap = _as_mapping(plays.get("\u8ba9\u7403"))
        ou = _as_mapping(plays.get("\u5927\u5c0f\u7403"))
        high_rate = high_strategy.get("rate")
        high_rate_value = _safe_float(high_rate, -1.0) if high_rate is not None else None

        if one_x_two.get("rate") is not None and _safe_float(one_x_two.get("rate"), 0.0) < 0.55:
            reasons.append(f"1X2 \u547d\u4e2d {one_x_two.get('text', '-')}\uff0c\u4f4e\u4e8e 55% \u89c2\u5bdf\u7ebf\uff0c\u5efa\u8bae\u63d0\u9ad8\u653e\u884c\u7f6e\u4fe1\u95e8\u69db\u3002")
            next_min_confidence += 0.05
        if handicap.get("rate") is not None and _safe_float(handicap.get("rate"), 0.0) < 0.50:
            reasons.append(f"\u8ba9\u7403\u547d\u4e2d {handicap.get('text', '-')}\uff0c\u5efa\u8bae\u964d\u4f4e\u8ba9\u7403\u73a9\u6cd5\u6743\u91cd\u3002")
        if ou.get("rate") is not None and _safe_float(ou.get("rate"), 0.0) < 0.50:
            reasons.append(f"\u5927\u5c0f\u7403\u547d\u4e2d {ou.get('text', '-')}\uff0c\u5efa\u8bae\u964d\u4f4e\u5927\u5c0f\u7403\u73a9\u6cd5\u6743\u91cd\u3002")
        if high_rate_value is not None and high_rate_value >= 0 and high_rate_value < 0.60:
            reasons.append(f"\u9ad8\u51c6\u7b56\u7565\u547d\u4e2d {high_strategy.get('text', '-')}\uff0c\u5efa\u8bae\u63d0\u9ad8\u6b63\u5f0f\u7b56\u7565\u6570\u8981\u6c42\u3002")
            next_active_strategy_min = max(next_active_strategy_min, 2)

        if reasons:
            action = "tighten"
            label = "\u5efa\u8bae\u6536\u7d27"
            tone = "warning"
            priority = "high" if len(reasons) >= 2 else "medium"
            if priority == "high":
                medium_risk_allowed = False
        else:
            action = "hold"
            label = "\u7ef4\u6301\u5f53\u524d\u95e8\u69db"
            tone = "good"
            priority = "low"
            reasons.append("\u672c\u8f6e\u4e3b\u8981\u73a9\u6cd5\u672a\u89e6\u53d1\u6536\u7d27\u6761\u4ef6\uff0c\u7ee7\u7eed\u6309\u5f53\u524d\u51c6\u5165\u7b56\u7565\u8fd0\u884c\u3002")

    next_min_confidence = round(min(0.78, max(0.45, next_min_confidence)), 2)
    policy_update = {}
    if action == "tighten":
        policy_update = {
            "min_confidence": next_min_confidence,
            "active_strategy_min": next_active_strategy_min,
            "medium_risk_allowed": medium_risk_allowed,
            "high_risk_allowed": False,
        }
    return {
        "action": action,
        "label": label,
        "tone": tone,
        "priority": priority,
        "next_min_confidence": next_min_confidence,
        "next_active_strategy_min": next_active_strategy_min,
        "medium_risk_allowed": medium_risk_allowed,
        "policy_update": policy_update,
        "reasons": reasons,
        "rows": [
            ("\u52a8\u4f5c", label),
            ("\u4f18\u5148\u7ea7", priority),
            ("\u6700\u4f4e\u7f6e\u4fe1", f"{_safe_float(base_min_confidence, 0.50):.2f} -> {next_min_confidence:.2f}"),
            ("\u9ad8\u51c6\u7b56\u7565\u6570", f"{max(1, _safe_int(base_active_strategy_min, 1))} -> {next_active_strategy_min}"),
            ("\u89e6\u53d1\u539f\u56e0", "\n".join(reasons) if reasons else "-"),
        ],
    }


def build_result_recovery_review_summary(settlements: Sequence[Mapping[str, object]] | object) -> dict[str, object]:
    rows = [item for item in _run_items(settlements) if isinstance(item, Mapping)]
    play_fields = [
        ("1X2", "is_correct"),
        ("\u8ba9\u7403", "handicap_is_correct"),
        ("\u5927\u5c0f\u7403", "ou_is_correct"),
        ("\u603b\u8fdb\u7403", "total_goals_is_correct"),
        ("\u6bd4\u5206", "score_is_correct"),
    ]
    plays = {label: _hit_stats(rows, field) for label, field in play_fields}
    high_total = sum(_safe_int(item.get("high_accuracy_strategy_active_count"), 0) for item in rows)
    high_hits = sum(_safe_int(item.get("high_accuracy_strategy_hit_count"), 0) for item in rows)
    high_rate = (high_hits / high_total) if high_total else None
    allow_rows = [item for item in rows if str(item.get("strategy_allowlist_decision") or "") == "allow"]
    allow_stats = _hit_stats(allow_rows, "is_correct")
    misses: list[dict[str, object]] = []
    for item in rows:
        if item.get("is_correct") is not False:
            continue
        misses.append(
            {
                "match_id": item.get("match_id") or "",
                "match_date": item.get("match_date") or "",
                "league": item.get("league") or "",
                "home_team": item.get("home_team") or "",
                "away_team": item.get("away_team") or "",
                "predicted": item.get("predicted") or "-",
                "result": item.get("result") or "-",
                "confidence": _safe_float(item.get("prediction_confidence"), 0.0),
            }
        )
    misses.sort(key=lambda item: _safe_float(item.get("confidence"), 0.0), reverse=True)
    handicap_label = "\u8ba9\u7403"
    ou_label = "\u5927\u5c0f\u7403"
    lines = [
        f"\u672c\u8f6e\u65b0\u7ed3\u7b97 {len(rows)} \u573a",
        f"1X2 {plays['1X2']['text']}",
        f"{handicap_label} {plays[handicap_label]['text']}",
        f"{ou_label} {plays[ou_label]['text']}",
        f"\u9ad8\u51c6\u7b56\u7565 {high_hits}/{high_total} ({high_rate:.0%})" if high_rate is not None else "\u9ad8\u51c6\u7b56\u7565 -",
        f"\u653e\u884c\u6e05\u5355 1X2 {allow_stats['text']}",
    ]
    summary = {
        "settlement_count": len(rows),
        "plays": plays,
        "high_accuracy_strategy": {
            "hits": high_hits,
            "total": high_total,
            "rate": high_rate,
            "text": f"{high_hits}/{high_total} ({high_rate:.0%})" if high_rate is not None else "-",
        },
        "allowlist": {
            "count": len(allow_rows),
            "one_x_two": allow_stats,
        },
        "top_misses": misses[:5],
        "summary_lines": lines,
        "summary_text": "\n".join(lines),
    }
    summary["strategy_adjustment"] = build_result_recovery_strategy_adjustment(summary)
    return summary


def _review_summary_text(value: object) -> str:
    summary = _as_mapping(value)
    lines = summary.get("summary_lines")
    if isinstance(lines, Sequence) and not isinstance(lines, (str, bytes)):
        text = "\n".join(f"- {line}" for line in lines if line)
    else:
        text = str(summary.get("summary_text") or "").strip()
        text = "\n".join(f"- {line}" for line in text.splitlines() if line)
    misses = summary.get("top_misses")
    miss_lines: list[str] = []
    if isinstance(misses, Sequence) and not isinstance(misses, (str, bytes)):
        for raw in misses:
            if not isinstance(raw, Mapping):
                continue
            teams = f"{raw.get('home_team') or '-'} vs {raw.get('away_team') or '-'}"
            miss_lines.append(
                f"- {raw.get('match_date') or '-'} {raw.get('league') or '-'} {teams} | "
                f"{raw.get('predicted') or '-'} -> {raw.get('result') or '-'} | "
                f"conf={_safe_float(raw.get('confidence'), 0.0):.0%}"
            )
    if miss_lines:
        text = (text + "\n\n\u9ad8\u7f6e\u4fe1\u5931\u8bef\u6837\u4f8b:\n" if text else "\u9ad8\u7f6e\u4fe1\u5931\u8bef\u6837\u4f8b:\n") + "\n".join(miss_lines)
    adjustment = _as_mapping(summary.get("strategy_adjustment"))
    adjustment_reasons = adjustment.get("reasons")
    if adjustment:
        reason_text = ""
        if isinstance(adjustment_reasons, Sequence) and not isinstance(adjustment_reasons, (str, bytes)):
            reason_text = "\n".join(f"- {item}" for item in adjustment_reasons if item)
        if reason_text:
            text = (
                text
                + f"\n\n\u7b56\u7565\u8c03\u6574\u5efa\u8bae: {adjustment.get('label') or '-'}\n"
                + reason_text
            )
    return text or "- \u65e0"


def _parse_timestamp(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def _run_items(records: Sequence[Mapping[str, object]] | object) -> list[Mapping[str, object]]:
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return []
    return [item for item in records if isinstance(item, Mapping)]


def mark_stale_result_recovery_runs(
    records: Sequence[Mapping[str, object]] | object,
    *,
    now: datetime | None = None,
    stale_after_minutes: int = 60,
) -> dict[str, object]:
    rows = _run_items(records)
    current = now or datetime.now()
    threshold_seconds = max(1, int(stale_after_minutes)) * 60
    normalized: list[dict[str, object]] = []
    updated: list[dict[str, object]] = []
    for item in rows:
        record = dict(item)
        if str(record.get("status") or "").lower() == "running":
            started_at = _parse_timestamp(record.get("started_at"))
            if started_at is not None:
                elapsed = max(0.0, (current - started_at).total_seconds())
                if elapsed >= threshold_seconds:
                    record.update(
                        {
                            "status": "interrupted",
                            "finished_at": current.strftime("%Y-%m-%d %H:%M:%S"),
                            "elapsed_seconds": round(elapsed, 4),
                            "error": "\u4e0a\u6b21\u56de\u6536\u672a\u6b63\u5e38\u5b8c\u6210\uff0c\u53ef\u80fd\u662f APP \u5173\u95ed\u6216\u4efb\u52a1\u4e2d\u65ad",
                        }
                    )
                    messages = record.get("messages")
                    if not isinstance(messages, list):
                        messages = []
                    record["messages"] = [*messages, "\u8fd0\u884c\u8bb0\u5f55\u5df2\u81ea\u52a8\u6807\u8bb0\u4e3a\u4e2d\u65ad"]
                    updated.append(dict(record))
        normalized.append(record)
    return {"items": normalized, "updated": updated, "updated_count": len(updated)}


def build_result_recovery_run_summary(records: Sequence[Mapping[str, object]] | object) -> dict[str, object]:
    rows = _run_items(records)
    completed = [item for item in rows if str(item.get("status") or "").lower() in {"success", "failed", "interrupted"}]
    success = [item for item in completed if str(item.get("status") or "").lower() == "success"]
    failed = [item for item in completed if str(item.get("status") or "").lower() in {"failed", "interrupted"}]
    running = [item for item in rows if str(item.get("status") or "").lower() == "running"]
    recent_completed = completed[-10:]
    recent_success = [item for item in recent_completed if str(item.get("status") or "").lower() == "success"]
    elapsed_values = [
        _safe_float(item.get("elapsed_seconds"), default=-1.0)
        for item in completed[-20:]
        if _safe_float(item.get("elapsed_seconds"), default=-1.0) >= 0
    ]
    avg_elapsed = sum(elapsed_values) / len(elapsed_values) if elapsed_values else None
    latest = rows[-1] if rows else {}
    total_new_settled = sum(_safe_int(item.get("new_settled"), 0) for item in completed)
    success_rate = (len(recent_success) / len(recent_completed)) if recent_completed else None
    latest_status = str(latest.get("status") or "-") if latest else "-"
    return {
        "total": len(rows),
        "completed_count": len(completed),
        "success_count": len(success),
        "failed_count": len(failed),
        "running_count": len(running),
        "recent_success_rate": success_rate,
        "recent_success_rate_text": f"{success_rate:.0%}" if success_rate is not None else "-",
        "avg_elapsed_seconds": avg_elapsed,
        "avg_elapsed_text": _elapsed_text(avg_elapsed) if avg_elapsed is not None else "-",
        "total_new_settled": total_new_settled,
        "latest_status": latest_status,
        "latest_status_label": _status_label(latest_status),
        "latest_started_at": str(latest.get("started_at") or "-") if latest else "-",
        "latest_finished_at": str(latest.get("finished_at") or "-") if latest else "-",
        "latest_new_settled": _safe_int(latest.get("new_settled"), 0) if latest else 0,
        "latest_error": str(latest.get("error") or "-") if latest else "-",
    }


def build_strategy_release_quality_trend(
    records: Sequence[Mapping[str, object]] | object,
    *,
    limit: int = 12,
) -> dict[str, object]:
    rows = _run_items(records)
    successful = [item for item in rows if str(item.get("status") or "").lower() == "success"]
    recent = successful[-max(1, int(limit)) :]
    trend_rows: list[dict[str, object]] = []
    release_rates: list[float] = []
    verified_count = 0
    no_feedback_count = 0
    total_new_settled = 0
    total_pending_reduced = 0
    total_feedback_known_delta = 0
    total_hit_delta = 0
    total_paused_delta = 0
    total_recovering_delta = 0

    for item in recent:
        validation = _as_mapping(item.get("live_feedback_validation"))
        validation_status = str(validation.get("status") or "-")
        if validation_status == "verified":
            verified_count += 1
        if validation_status == "no_strategy_feedback":
            no_feedback_count += 1
        hit_rate_text = str(item.get("strategy_release_loop_hit_rate_text") or "-")
        hit_rate = _pct_text_to_float(hit_rate_text)
        if hit_rate is not None:
            release_rates.append(hit_rate)
        new_settled = _safe_int(item.get("new_settled"))
        pending_reduced = max(0, _safe_int(validation.get("pending_reduced")))
        feedback_known_delta = _safe_int(validation.get("feedback_known_delta"))
        hit_delta = _safe_int(validation.get("hit_delta"))
        paused_delta = _safe_int(validation.get("paused_delta"))
        recovering_delta = _safe_int(validation.get("recovering_delta"))
        total_new_settled += new_settled
        total_pending_reduced += pending_reduced
        total_feedback_known_delta += max(0, feedback_known_delta)
        total_hit_delta += max(0, hit_delta)
        total_paused_delta += paused_delta
        total_recovering_delta += recovering_delta
        pending_count = _safe_int(item.get("strategy_release_loop_pending_count"))
        missing_snapshot_count = _safe_int(item.get("strategy_release_loop_missing_snapshot_count"))
        stale_pending_count = _safe_int(item.get("strategy_release_loop_stale_pending_count"))
        trend_rows.append(
            {
                "title": f"{item.get('started_at') or '-'} | 新结算 {new_settled} | 放行命中 {hit_rate_text}",
                "body": (
                    f"实盘反馈: {validation.get('summary_text') or '-'} | "
                    f"待回收 {pending_count} | 缺快照 {missing_snapshot_count} | 超期 {stale_pending_count}"
                ),
                "started_at": item.get("started_at") or "-",
                "new_settled": new_settled,
                "release_hit_rate_text": hit_rate_text,
                "release_hit_rate": hit_rate,
                "live_feedback_status": validation_status,
                "pending_reduced": pending_reduced,
                "feedback_known_delta": feedback_known_delta,
                "hit_delta": hit_delta,
                "paused_delta": paused_delta,
                "recovering_delta": recovering_delta,
                "pending_count": pending_count,
                "missing_snapshot_count": missing_snapshot_count,
                "stale_pending_count": stale_pending_count,
            }
        )

    latest_row = trend_rows[-1] if trend_rows else {}
    first_rate = release_rates[0] if release_rates else None
    latest_rate = release_rates[-1] if release_rates else None
    avg_rate = sum(release_rates) / len(release_rates) if release_rates else None
    rate_delta = latest_rate - first_rate if first_rate is not None and latest_rate is not None and len(release_rates) >= 2 else None
    if not recent:
        status = "collecting"
        tone = "neutral"
        label = "暂无趋势"
    elif len(recent) < 2:
        status = "collecting"
        tone = "neutral"
        label = "样本积累中"
    elif rate_delta is not None and rate_delta <= -0.05:
        status = "watch"
        tone = "warning"
        label = "放行命中走弱"
    elif no_feedback_count >= 2 and total_new_settled > 0:
        status = "watch"
        tone = "warning"
        label = "反馈未同步"
    elif rate_delta is not None and rate_delta >= 0.05 and verified_count:
        status = "improving"
        tone = "good"
        label = "趋势改善"
    elif verified_count:
        status = "stable"
        tone = "good"
        label = "反馈稳定"
    else:
        status = "stable"
        tone = "neutral"
        label = "趋势平稳"
    summary_text = (
        f"{label} | 最近 {len(recent)} 次 | 新结算 {total_new_settled} | "
        f"放行均值 {_pct_text(avg_rate)} | 变化 {_pct_text(rate_delta) if rate_delta is not None else '-'} | "
        f"待反馈减少 {total_pending_reduced} | 实盘样本 +{total_feedback_known_delta}"
    )
    metrics = [
        {"label": "趋势状态", "value": label, "tone": tone},
        {"label": "趋势样本", "value": str(len(recent)), "tone": "info" if recent else "neutral"},
        {"label": "放行均值", "value": _pct_text(avg_rate), "tone": "good" if avg_rate is not None and avg_rate >= 0.6 else "warning" if avg_rate is not None else "neutral"},
        {"label": "最近放行", "value": _pct_text(latest_rate), "tone": "good" if latest_rate is not None and latest_rate >= 0.6 else "warning" if latest_rate is not None else "neutral"},
        {"label": "命中变化", "value": _pct_text(rate_delta) if rate_delta is not None else "-", "tone": "good" if rate_delta is not None and rate_delta >= 0 else "warning" if rate_delta is not None else "neutral"},
        {"label": "新增结算", "value": str(total_new_settled), "tone": "info"},
        {"label": "反馈验证", "value": f"{verified_count}/{len(recent)}", "tone": "good" if verified_count else "warning" if recent else "neutral"},
        {"label": "待反馈减少", "value": str(total_pending_reduced), "tone": "good" if total_pending_reduced else "neutral"},
        {"label": "实盘样本+", "value": str(total_feedback_known_delta), "tone": "good" if total_feedback_known_delta else "neutral"},
        {"label": "暂停变化", "value": f"{total_paused_delta:+d}", "tone": "bad" if total_paused_delta > 0 else "good" if total_paused_delta < 0 else "neutral"},
        {"label": "恢复变化", "value": f"{total_recovering_delta:+d}", "tone": "good" if total_recovering_delta > 0 else "neutral"},
        {"label": "当前待回收", "value": str(latest_row.get("pending_count", 0) if latest_row else 0), "tone": "warning" if _safe_int(latest_row.get("pending_count") if latest_row else 0) else "good"},
    ]
    return {
        "status": status,
        "tone": tone,
        "label": label,
        "sample_count": len(recent),
        "total_new_settled": total_new_settled,
        "avg_release_hit_rate": avg_rate,
        "avg_release_hit_rate_text": _pct_text(avg_rate),
        "latest_release_hit_rate": latest_rate,
        "latest_release_hit_rate_text": _pct_text(latest_rate),
        "release_hit_rate_delta": rate_delta,
        "release_hit_rate_delta_text": _pct_text(rate_delta) if rate_delta is not None else "-",
        "verified_count": verified_count,
        "no_feedback_count": no_feedback_count,
        "total_pending_reduced": total_pending_reduced,
        "total_feedback_known_delta": total_feedback_known_delta,
        "total_hit_delta": total_hit_delta,
        "total_paused_delta": total_paused_delta,
        "total_recovering_delta": total_recovering_delta,
        "latest_pending_count": _safe_int(latest_row.get("pending_count") if latest_row else 0),
        "latest_missing_snapshot_count": _safe_int(latest_row.get("missing_snapshot_count") if latest_row else 0),
        "latest_stale_pending_count": _safe_int(latest_row.get("stale_pending_count") if latest_row else 0),
        "summary_text": summary_text,
        "metrics": metrics,
        "rows": list(reversed(trend_rows)),
    }


def build_strategy_release_quality_trend_alerts(
    trend: Mapping[str, object] | object,
    *,
    min_decline: float = 0.05,
    pending_threshold: int = 3,
) -> list[dict[str, str]]:
    item = _as_mapping(trend)
    alerts: list[dict[str, str]] = []
    sample_count = _safe_int(item.get("sample_count"))
    if sample_count <= 0:
        return alerts

    delta = item.get("release_hit_rate_delta")
    decline = _safe_float(delta, default=0.0) if delta is not None else 0.0
    latest_rate = item.get("latest_release_hit_rate")
    latest_rate_value = _safe_float(latest_rate, default=-1.0) if latest_rate is not None else -1.0
    avg_rate = item.get("avg_release_hit_rate")
    avg_rate_value = _safe_float(avg_rate, default=-1.0) if avg_rate is not None else -1.0
    no_feedback_count = _safe_int(item.get("no_feedback_count"))
    verified_count = _safe_int(item.get("verified_count"))
    total_new_settled = _safe_int(item.get("total_new_settled"))
    latest_pending_count = _safe_int(item.get("latest_pending_count"))
    latest_missing_snapshot_count = _safe_int(item.get("latest_missing_snapshot_count"))
    latest_stale_pending_count = _safe_int(item.get("latest_stale_pending_count"))
    total_paused_delta = _safe_int(item.get("total_paused_delta"))
    total_feedback_known_delta = _safe_int(item.get("total_feedback_known_delta"))

    if delta is not None and decline <= -abs(float(min_decline)):
        alerts.append(
            {
                "severity": "high" if decline <= -0.10 else "medium",
                "title": "放行命中趋势走弱",
                "body": (
                    f"最近 {sample_count} 次放行命中从首期到最近变化 {_pct_text(decline)}，"
                    f"最近命中 {_pct_text(latest_rate_value if latest_rate_value >= 0 else None)}，建议复核放行门槛和高风险过滤。"
                ),
                "tone": "bad" if decline <= -0.10 else "warning",
            }
        )
    if latest_rate_value >= 0 and latest_rate_value < 0.55 and avg_rate_value >= 0:
        alerts.append(
            {
                "severity": "medium",
                "title": "最近放行命中低于观察线",
                "body": f"最近放行命中 {_pct_text(latest_rate_value)}，趋势均值 {_pct_text(avg_rate_value)}。短期不要扩大放行覆盖。",
                "tone": "warning",
            }
        )
    if no_feedback_count >= 2 and total_new_settled > 0:
        alerts.append(
            {
                "severity": "medium",
                "title": "实盘反馈未同步",
                "body": f"最近趋势中有 {no_feedback_count} 次新增结算未推动高准策略反馈变化，需检查策略匹配键、赛果回收和高准策略记录字段。",
                "tone": "warning",
            }
        )
    if total_new_settled > 0 and verified_count == 0 and total_feedback_known_delta <= 0:
        alerts.append(
            {
                "severity": "medium",
                "title": "缺少有效实盘反馈验证",
                "body": f"最近 {sample_count} 次回收累计新增结算 {total_new_settled} 场，但未出现已验证的高准策略反馈变化。",
                "tone": "warning",
            }
        )
    if latest_stale_pending_count > 0:
        alerts.append(
            {
                "severity": "high",
                "title": "放行赛果回收超期",
                "body": f"当前仍有 {latest_stale_pending_count} 场放行记录超期待回收，放行命中率会滞后，优先执行赛果回收。",
                "tone": "bad",
            }
        )
    if latest_pending_count >= max(1, int(pending_threshold)):
        alerts.append(
            {
                "severity": "medium",
                "title": "待回收放行积压",
                "body": f"当前待回收放行 {latest_pending_count} 场，达到阈值 {max(1, int(pending_threshold))}。建议先处理回收再调整策略。",
                "tone": "warning",
            }
        )
    if latest_missing_snapshot_count > 0:
        alerts.append(
            {
                "severity": "medium",
                "title": "放行快照缺失",
                "body": f"当前有 {latest_missing_snapshot_count} 场放行记录缺少赛前快照，后续无法完成标准复盘闭环。",
                "tone": "warning",
            }
        )
    if total_paused_delta > 0:
        alerts.append(
            {
                "severity": "high",
                "title": "暂停策略增加",
                "body": f"最近趋势中暂停策略净增加 {total_paused_delta} 条，说明断路器压力上升，应优先复核错因和盘口过滤。",
                "tone": "bad",
            }
        )
    return alerts


def build_strategy_release_trend_policy_tuning(
    trend: Mapping[str, object] | object,
    alerts: Sequence[Mapping[str, object]] | object = (),
    *,
    base_min_confidence: float = 0.50,
    base_active_strategy_min: int = 1,
    base_medium_risk_allowed: bool = True,
) -> dict[str, object]:
    item = _as_mapping(trend)
    alert_rows = [row for row in alerts if isinstance(row, Mapping)] if isinstance(alerts, Sequence) else []
    sample_count = _safe_int(item.get("sample_count"))
    current_min_confidence = round(max(0.45, min(0.78, _safe_float(base_min_confidence, 0.50))), 2)
    next_min_confidence = current_min_confidence
    current_active_min = max(1, min(3, _safe_int(base_active_strategy_min, 1)))
    next_active_min = current_active_min
    current_medium_allowed = bool(base_medium_risk_allowed)
    next_medium_allowed = current_medium_allowed
    reasons: list[str] = []

    if sample_count < 2:
        reasons.append(f"趋势样本只有 {sample_count} 次，暂不建议根据短期趋势写入新门槛。")
        return {
            "action": "collect",
            "label": "继续积累趋势样本",
            "tone": "neutral",
            "priority": "low",
            "next_min_confidence": next_min_confidence,
            "next_active_strategy_min": next_active_min,
            "medium_risk_allowed": next_medium_allowed,
            "policy_update": {},
            "reasons": reasons,
            "rows": [
                ("动作", "继续积累趋势样本"),
                ("趋势样本", str(sample_count)),
                ("最低置信", f"{current_min_confidence:.2f} -> {next_min_confidence:.2f}"),
                ("高准策略数", f"{current_active_min} -> {next_active_min}"),
                ("中风险放行", "ON" if next_medium_allowed else "OFF"),
            ],
        }
    if not alert_rows:
        reasons.append("当前放行趋势未触发门控告警，维持现有准入参数。")
        return {
            "action": "hold",
            "label": "维持当前门槛",
            "tone": "good",
            "priority": "low",
            "next_min_confidence": next_min_confidence,
            "next_active_strategy_min": next_active_min,
            "medium_risk_allowed": next_medium_allowed,
            "policy_update": {},
            "reasons": reasons,
            "rows": [
                ("动作", "维持当前门槛"),
                ("趋势状态", str(item.get("label") or "-")),
                ("最低置信", f"{current_min_confidence:.2f} -> {next_min_confidence:.2f}"),
                ("高准策略数", f"{current_active_min} -> {next_active_min}"),
                ("中风险放行", "ON" if next_medium_allowed else "OFF"),
            ],
        }

    high_alert_count = sum(1 for row in alert_rows if str(row.get("severity") or "") == "high")
    alert_titles = [str(row.get("title") or "-") for row in alert_rows]
    title_text = " / ".join(alert_titles[:4])
    title_blob = "\n".join(alert_titles)
    if "放行命中趋势走弱" in title_blob:
        delta = item.get("release_hit_rate_delta")
        decline = _safe_float(delta, 0.0) if delta is not None else 0.0
        step = 0.06 if decline <= -0.10 else 0.04
        next_min_confidence += step
        reasons.append(f"放行命中趋势走弱，准入置信建议提高 {step:.2f}。")
    if "最近放行命中低于观察线" in title_blob:
        next_min_confidence += 0.03
        reasons.append("最近放行命中低于观察线，短期不应扩大覆盖。")
    if "实盘反馈未同步" in title_blob or "缺少有效实盘反馈验证" in title_blob:
        next_active_min = max(next_active_min, 2)
        next_medium_allowed = False
        reasons.append("新增结算未稳定转化为高准策略实盘反馈，要求至少 2 条高准策略共同支持，并关闭中风险放行。")
    if "放行赛果回收超期" in title_blob or "待回收放行积压" in title_blob:
        next_medium_allowed = False
        reasons.append("放行回收存在超期或积压，先收紧中风险放行，避免未复盘样本继续扩大。")
    if "放行快照缺失" in title_blob:
        next_medium_allowed = False
        reasons.append("存在放行快照缺失，后续复盘证据不完整，暂不放行中风险场次。")
    if "暂停策略增加" in title_blob:
        paused_delta = _safe_int(item.get("total_paused_delta"))
        next_active_min = max(next_active_min, 3 if paused_delta >= 2 else 2)
        next_min_confidence += 0.03
        next_medium_allowed = False
        reasons.append("暂停策略增加，断路器压力上升，提高高准策略数量要求并收紧置信门槛。")

    next_min_confidence = round(max(0.45, min(0.78, next_min_confidence)), 2)
    next_active_min = max(1, min(3, next_active_min))
    if not reasons:
        reasons.append(f"趋势告警已触发: {title_text}。建议人工复核后再调整。")
    priority = "high" if high_alert_count else "medium"
    policy_update = {
        "min_confidence": next_min_confidence,
        "active_strategy_min": next_active_min,
        "medium_risk_allowed": next_medium_allowed,
        "high_risk_allowed": False,
    }
    return {
        "action": "tighten",
        "label": "趋势告警建议收紧",
        "tone": "bad" if priority == "high" else "warning",
        "priority": priority,
        "source": "release_quality_trend",
        "next_min_confidence": next_min_confidence,
        "next_active_strategy_min": next_active_min,
        "medium_risk_allowed": next_medium_allowed,
        "policy_update": policy_update,
        "reasons": reasons,
        "rows": [
            ("动作", "趋势告警建议收紧"),
            ("触发告警", title_text or "-"),
            ("趋势样本", str(sample_count)),
            ("放行命中", f"{item.get('latest_release_hit_rate_text', '-')} / 均值 {item.get('avg_release_hit_rate_text', '-')}"),
            ("最低置信", f"{current_min_confidence:.2f} -> {next_min_confidence:.2f}"),
            ("高准策略数", f"{current_active_min} -> {next_active_min}"),
            ("中风险放行", f"{'ON' if current_medium_allowed else 'OFF'} -> {'ON' if next_medium_allowed else 'OFF'}"),
        ],
    }


def build_result_recovery_quality_alerts(
    records: Sequence[Mapping[str, object]] | object,
    *,
    failure_streak_threshold: int = 2,
    no_settlement_window: int = 3,
    elapsed_multiplier: float = 2.0,
    min_elapsed_seconds: float = 10.0,
) -> list[dict[str, str]]:
    rows = _run_items(records)
    completed = [item for item in rows if str(item.get("status") or "").lower() in {"success", "failed", "interrupted"}]
    if not completed and rows and str(rows[-1].get("status") or "").lower() == "running":
        return [
            {
                "severity": "info",
                "title": "\u56de\u6536\u4efb\u52a1\u6b63\u5728\u8fd0\u884c",
                "body": f"\u5f00\u59cb\u65f6\u95f4: {rows[-1].get('started_at') or '-'}",
                "tone": "info",
            }
        ]
    if not completed:
        return []

    alerts: list[dict[str, str]] = []
    latest_completed = completed[-1]
    if str(latest_completed.get("status") or "").lower() == "interrupted":
        alerts.append(
            {
                "severity": "high",
                "title": "\u4e0a\u6b21\u56de\u6536\u4efb\u52a1\u4e2d\u65ad",
                "body": str(latest_completed.get("error") or "\u56de\u6536\u672a\u6b63\u5e38\u5b8c\u6210\uff0c\u5efa\u8bae\u91cd\u65b0\u6267\u884c\u56de\u6536\u5e76\u68c0\u67e5\u5feb\u7167\u72b6\u6001\u3002"),
                "tone": "bad",
            }
        )
    failure_streak = 0
    for item in reversed(completed):
        if str(item.get("status") or "").lower() in {"failed", "interrupted"}:
            failure_streak += 1
        else:
            break
    if failure_streak >= max(1, int(failure_streak_threshold)):
        latest = completed[-1]
        alerts.append(
            {
                "severity": "high",
                "title": f"\u8fde\u7eed\u56de\u6536\u5931\u8d25/\u4e2d\u65ad {failure_streak} \u6b21",
                "body": f"\u6700\u8fd1\u9519\u8bef: {latest.get('error') or '-'}",
                "tone": "bad",
            }
        )

    success_runs = [item for item in completed if str(item.get("status") or "").lower() == "success"]
    recent_success = success_runs[-max(1, int(no_settlement_window)) :]
    if len(recent_success) >= max(1, int(no_settlement_window)) and all(_safe_int(item.get("new_settled"), 0) == 0 for item in recent_success):
        total_finished = sum(_safe_int(item.get("fetched_finished"), 0) for item in recent_success)
        total_restored = sum(_safe_int(item.get("restored_snapshots"), 0) for item in recent_success)
        alerts.append(
            {
                "severity": "medium",
                "title": f"\u8fd1 {len(recent_success)} \u6b21\u56de\u6536\u65e0\u65b0\u7ed3\u7b97",
                "body": f"\u671f\u95f4\u5b8c\u573a {total_finished} \u573a\uff0c\u4fee\u590d\u5feb\u7167 {total_restored} \u573a\u3002\u5efa\u8bae\u68c0\u67e5\u5feb\u7167\u7ed1\u5b9a\u548c\u8d5b\u679c\u6e90\u547d\u4e2d\u7387\u3002",
                "tone": "warning",
            }
        )

    elapsed_runs = [item for item in success_runs if _safe_float(item.get("elapsed_seconds"), default=-1.0) >= 0]
    if len(elapsed_runs) >= 4:
        latest = elapsed_runs[-1]
        previous = elapsed_runs[-4:-1]
        baseline = sum(_safe_float(item.get("elapsed_seconds"), 0.0) for item in previous) / len(previous)
        latest_elapsed = _safe_float(latest.get("elapsed_seconds"), 0.0)
        if baseline > 0 and latest_elapsed >= max(float(min_elapsed_seconds), baseline * float(elapsed_multiplier)):
            alerts.append(
                {
                    "severity": "medium",
                    "title": "\u56de\u6536\u8017\u65f6\u5f02\u5e38\u5347\u9ad8",
                    "body": f"\u6700\u8fd1\u8017\u65f6 {_elapsed_text(latest_elapsed)}\uff0c\u524d 3 \u6b21\u5e73\u5747 {_elapsed_text(baseline)}\u3002\u5efa\u8bae\u68c0\u67e5\u8d5b\u679c\u6e90\u54cd\u5e94\u548c\u672c\u5730\u72b6\u6001\u6587\u4ef6\u3002",
                    "tone": "warning",
                }
            )

    if not alerts and str(rows[-1].get("status") or "").lower() == "running":
        alerts.append(
            {
                "severity": "info",
                "title": "\u56de\u6536\u4efb\u52a1\u6b63\u5728\u8fd0\u884c",
                "body": f"\u5f00\u59cb\u65f6\u95f4: {rows[-1].get('started_at') or '-'}",
                "tone": "info",
            }
        )
    return alerts


def build_result_recovery_run_rows(
    records: Sequence[Mapping[str, object]] | object,
    *,
    limit: int = 30,
) -> list[dict[str, object]]:
    rows = list(reversed(_run_items(records)))[0 : max(0, int(limit))]
    result: list[dict[str, object]] = []
    for item in rows:
        status = str(item.get("status") or "-").lower()
        title = (
            f"{_status_label(status)} | {item.get('started_at') or '-'} | "
            f"\u65b0\u589e\u7ed3\u7b97 {_safe_int(item.get('new_settled'), 0)}"
        )
        body = (
            f"\u8017\u65f6: {_elapsed_text(item.get('elapsed_seconds'))} | "
            f"\u5b8c\u573a: {_safe_int(item.get('fetched_finished'), 0)} | "
            f"\u4fee\u590d\u5feb\u7167: {_safe_int(item.get('restored_snapshots'), 0)} | "
            f"\u6765\u6e90: {item.get('source') or '-'}"
        )
        review = _as_mapping(item.get("review_summary"))
        if review:
            summary_lines = review.get("summary_lines")
            if isinstance(summary_lines, Sequence) and not isinstance(summary_lines, (str, bytes)) and summary_lines:
                review_head = str(summary_lines[0])
            else:
                review_head = str(review.get("summary_text") or "-").splitlines()[0]
            body = f"{body}\n\u590d\u76d8: {review_head}"
        live_feedback_validation = _as_mapping(item.get("live_feedback_validation"))
        if live_feedback_validation:
            body = f"{body}\n\u5b9e\u76d8\u53cd\u9988: {live_feedback_validation.get('summary_text') or '-'}"
        if status == "failed":
            body = f"{body}\n\u9519\u8bef: {item.get('error') or '-'}"
        result.append({"title": title, "body": body, "status": status, "record": dict(item)})
    return result


def build_result_recovery_run_detail(record: Mapping[str, object] | object) -> str:
    item = _as_mapping(record)
    result = _as_mapping(item.get("result"))
    messages = item.get("messages")
    if not isinstance(messages, list):
        messages = result.get("messages") if isinstance(result.get("messages"), list) else []
    message_text = "\n".join(f"- {message}" for message in messages if message) or "- \u65e0"
    miss_reasons = item.get("snapshot_result_miss_reasons") or result.get("snapshot_result_miss_reasons")
    miss_items = item.get("snapshot_result_miss_items") or result.get("snapshot_result_miss_items")
    review_summary = item.get("review_summary") or result.get("review_summary")
    release_loop_report = item.get("strategy_release_loop_report") or result.get("strategy_release_loop_report") or "-"
    release_loop_summary = item.get("strategy_release_loop_summary") or result.get("strategy_release_loop_summary") or "-"
    release_loop_health = item.get("strategy_release_loop_health") or result.get("strategy_release_loop_health") or "-"
    release_loop_hit_rate = item.get("strategy_release_loop_hit_rate_text") or result.get("strategy_release_loop_hit_rate_text") or "-"
    live_feedback_validation = _as_mapping(item.get("live_feedback_validation") or result.get("live_feedback_validation"))
    daily_parlay_closure = _as_mapping(item.get("daily_parlay_snapshot_closure") or result.get("daily_parlay_snapshot_closure"))
    parlay_settlement_gate = _as_mapping(item.get("parlay_settlement_gate") or result.get("parlay_settlement_gate"))
    parlay_manual_items = item.get("parlay_manual_review_items") or result.get("parlay_manual_review_items")
    if isinstance(parlay_manual_items, Sequence) and not isinstance(parlay_manual_items, (str, bytes)):
        parlay_manual_detail = "\n".join(
            f"- {row.get('ticket_id') or '-'}: {row.get('code') or '-'} | {row.get('recommendation') or '-'}"
            for row in parlay_manual_items[:5]
            if isinstance(row, Mapping)
        )
    else:
        parlay_manual_detail = ""
    if not parlay_manual_detail:
        parlay_manual_detail = "- 无"
    live_feedback_rows = live_feedback_validation.get("rows")
    if isinstance(live_feedback_rows, Sequence) and not isinstance(live_feedback_rows, (str, bytes)):
        live_feedback_detail = "\n".join(
            f"- {row.get('title') or '-'}: {row.get('body') or '-'}"
            for row in live_feedback_rows
            if isinstance(row, Mapping)
        )
    else:
        live_feedback_detail = ""
    if not live_feedback_detail:
        live_feedback_detail = "- \u65e0"
    return (
        f"\u8fd0\u884c ID: {item.get('run_id') or '-'}\n"
        f"\u72b6\u6001: {_status_label(item.get('status'))}\n"
        f"\u89e6\u53d1: {item.get('trigger') or '-'} / {item.get('source_view') or '-'}\n"
        f"\u5f00\u59cb: {item.get('started_at') or '-'}\n"
        f"\u7ed3\u675f: {item.get('finished_at') or '-'}\n"
        f"\u8017\u65f6: {_elapsed_text(item.get('elapsed_seconds'))}\n"
        f"\u6570\u636e\u6e90: {item.get('source') or result.get('source') or '-'}\n\n"
        f"\u6838\u5fc3\u6307\u6807:\n"
        f"- \u56de\u770b\u5929\u6570: {_safe_int(item.get('lookback_days') or result.get('lookback_days'), 0)}\n"
        f"- \u5b8c\u573a\u573a\u6b21: {_safe_int(item.get('fetched_finished') or result.get('fetched_finished'), 0)}\n"
        f"- \u4fee\u590d\u5feb\u7167: {_safe_int(item.get('restored_snapshots') or result.get('restored_snapshots'), 0)}\n"
        f"- \u65b0\u589e\u7ed3\u7b97: {_safe_int(item.get('new_settled') or result.get('new_settled'), 0)}\n"
        f"- \u65b0\u589e\u4e8c\u4e32\u4e00\u7ed3\u7b97: {_safe_int(item.get('new_parlay_settled') or result.get('new_parlay_settled'), 0)}\n"
        f"- 二串一来源门禁: {parlay_settlement_gate.get('status') or '-'} | "
        f"ready {_safe_int(parlay_settlement_gate.get('ready_ticket_count'), 0)}/"
        f"{_safe_int(parlay_settlement_gate.get('checked_ticket_count'), 0)} | "
        f"manual_review {_safe_int(parlay_settlement_gate.get('manual_review_count'), 0)}\n"
        f"- 二串一来源跳过: {_safe_int(item.get('parlay_skipped_source_health') or result.get('parlay_skipped_source_health'), 0)}\n"
        f"- \u5df2\u7ed3\u7b97\u8df3\u8fc7: {_safe_int(item.get('already_settled') or result.get('already_settled'), 0)}\n"
        f"- \u5176\u4ed6\u8df3\u8fc7: {_safe_int(item.get('skipped') or result.get('skipped'), 0)}\n"
        f"- \u5feb\u7167\u56de\u67e5: {_safe_int(item.get('snapshot_checked') or result.get('snapshot_checked'), 0)} / "
        f"{_safe_int(item.get('snapshot_result_hits') or result.get('snapshot_result_hits'), 0)}\n"
        f"- \u5feb\u7167\u56de\u67e5\u672a\u547d\u4e2d: {_safe_int(item.get('snapshot_result_misses') or result.get('snapshot_result_misses'), 0)}\n"
        f"- \u672a\u547d\u4e2d\u539f\u56e0: {_reason_counts_text(miss_reasons)}\n"
        f"- \u9884\u6d4b\u5feb\u7167\u547d\u4e2d: {_safe_int(item.get('snapshot_predictions') or result.get('snapshot_predictions'), 0)}\n\n"
        f"每日二串一快照闭环:\n"
        f"- 状态: {daily_parlay_closure.get('status') or '-'}\n"
        f"- 摘要: {daily_parlay_closure.get('summary_text') or '-'}\n"
        f"- 来源追溯: {daily_parlay_closure.get('source_summary_text') or '-'}\n"
        f"- 新增闭环票据: {_safe_int(item.get('daily_parlay_snapshot_closed') or daily_parlay_closure.get('newly_settled_ticket_count'), 0)}\n"
        f"- 快照数: {_safe_int(daily_parlay_closure.get('snapshot_count'), 0)}\n\n"
        f"二串一人工修复队列:\n"
        f"{parlay_manual_detail}\n\n"
        f"\u5feb\u7167\u53ef\u56de\u6536\u6027:\n"
        f"- \u53ef\u81ea\u52a8\u56de\u67e5: {_safe_int(item.get('snapshot_recoverable') or result.get('snapshot_recoverable'), 0)}\n"
        f"- \u7f3a source_id: {_safe_int(item.get('snapshot_missing_source_id') or result.get('snapshot_missing_source_id'), 0)}\n"
        f"- \u4e0d\u53ef\u56de\u67e5\u6765\u6e90: {_safe_int(item.get('snapshot_non_titan_source') or result.get('snapshot_non_titan_source'), 0)}\n"
        f"- \u8d85\u51fa\u56de\u770b\u7a97\u53e3: {_safe_int(item.get('snapshot_out_of_window') or result.get('snapshot_out_of_window'), 0)}\n\n"
        f"\u653e\u884c\u56de\u6536\u95ed\u73af:\n"
        f"- \u72b6\u6001: {release_loop_health}\n"
        f"- \u6458\u8981: {release_loop_summary}\n"
        f"- \u547d\u4e2d: {release_loop_hit_rate}\n"
        f"- \u62a5\u544a: {release_loop_report}\n"
        f"- \u5f85\u56de\u6536: {_safe_int(item.get('strategy_release_loop_pending_count') or result.get('strategy_release_loop_pending_count'), 0)}\n"
        f"- \u7f3a\u5feb\u7167: {_safe_int(item.get('strategy_release_loop_missing_snapshot_count') or result.get('strategy_release_loop_missing_snapshot_count'), 0)}\n"
        f"- \u8d85\u671f: {_safe_int(item.get('strategy_release_loop_stale_pending_count') or result.get('strategy_release_loop_stale_pending_count'), 0)}\n\n"
        f"\u5b9e\u76d8\u53cd\u9988\u9a8c\u8bc1:\n"
        f"- \u72b6\u6001: {live_feedback_validation.get('status') or '-'}\n"
        f"- \u6458\u8981: {live_feedback_validation.get('summary_text') or '-'}\n"
        f"{live_feedback_detail}\n\n"
        f"\u672c\u8f6e\u590d\u76d8\u6458\u8981:\n{_review_summary_text(review_summary)}\n\n"
        f"\u672a\u547d\u4e2d\u6837\u4f8b:\n{_miss_items_text(miss_items)}\n\n"
        f"\u9519\u8bef:\n- {item.get('error') or '-'}\n\n"
        f"\u6d88\u606f:\n{message_text}"
    )
