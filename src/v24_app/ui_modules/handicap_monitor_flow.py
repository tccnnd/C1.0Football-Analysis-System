from __future__ import annotations

from datetime import datetime, timedelta
from typing import Mapping


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _parse_timestamp(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    candidates = [text]
    if len(text) >= 19:
        candidates.append(text[:19])
    if len(text) >= 10:
        candidates.append(text[:10])
    for candidate in candidates:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(candidate, fmt)
            except Exception:
                continue
    return None


def _normalize_handicap_records(settlements: list[Mapping[str, object]]) -> list[dict]:
    records: list[dict] = []
    for item in settlements:
        if not isinstance(item, Mapping):
            continue
        is_hit = item.get("handicap_is_correct")
        if not isinstance(is_hit, bool):
            continue
        ts = _parse_timestamp(item.get("timestamp"))
        if ts is None:
            continue
        expected_hit = _safe_float(item.get("handicap_confidence"), default=0.0)
        if expected_hit <= 0.0:
            expected_hit = _safe_float(item.get("prediction_confidence"), default=0.0)
        if expected_hit < 0.0 or expected_hit > 1.0:
            expected_hit = 0.0
        records.append(
            {
                "timestamp": ts,
                "date": ts.strftime("%Y-%m-%d"),
                "is_hit": is_hit,
                "expected_hit": expected_hit,
                "line_abs": abs(_safe_float(item.get("handicap_line"), default=0.0)),
            }
        )
    records.sort(key=lambda row: row["timestamp"])
    return records


def _compute_gate_metrics(records: list[dict], breaker_threshold: int = 3) -> dict:
    if not records:
        return {
            "sample_count": 0,
            "hits": 0,
            "hit_rate": 0.0,
            "expected_hit_rate": 0.0,
            "ev_bias": 0.0,
            "losing_streak": 0,
            "breaker_on": False,
            "avg_line_abs": 0.0,
        }

    sample_count = len(records)
    hits = sum(1 for row in records if row["is_hit"])
    hit_rate = hits / sample_count
    expected = [row["expected_hit"] for row in records if row["expected_hit"] > 0.0]
    expected_hit_rate = sum(expected) / len(expected) if expected else 0.0
    losing_streak = 0
    for row in reversed(records):
        if row["is_hit"]:
            break
        losing_streak += 1
    avg_line_abs = sum(float(row["line_abs"]) for row in records) / sample_count
    return {
        "sample_count": sample_count,
        "hits": hits,
        "hit_rate": round(hit_rate, 4),
        "expected_hit_rate": round(expected_hit_rate, 4),
        "ev_bias": round((hit_rate - expected_hit_rate) if expected else 0.0, 4),
        "losing_streak": losing_streak,
        "breaker_on": losing_streak >= max(1, int(breaker_threshold)),
        "avg_line_abs": round(avg_line_abs, 2),
    }


def _line_bucket_rows(records: list[dict]) -> list[dict]:
    buckets = [
        {"label": "|line| <= 0.25", "lo": 0.0, "hi": 0.25, "hits": 0, "total": 0},
        {"label": "0.25 < |line| <= 0.75", "lo": 0.25, "hi": 0.75, "hits": 0, "total": 0},
        {"label": "|line| > 0.75", "lo": 0.75, "hi": None, "hits": 0, "total": 0},
    ]
    for row in records:
        line_abs = float(row["line_abs"])
        for bucket in buckets:
            lo = float(bucket["lo"])
            hi = bucket["hi"]
            if hi is None and line_abs > lo:
                bucket["total"] += 1
                bucket["hits"] += 1 if row["is_hit"] else 0
                break
            if hi is not None and lo < line_abs <= float(hi):
                bucket["total"] += 1
                bucket["hits"] += 1 if row["is_hit"] else 0
                break
            if lo == 0.0 and line_abs <= float(hi):
                bucket["total"] += 1
                bucket["hits"] += 1 if row["is_hit"] else 0
                break
    rows: list[dict] = []
    for bucket in buckets:
        total = int(bucket["total"])
        hits = int(bucket["hits"])
        rows.append(
            {
                "label": str(bucket["label"]),
                "hits": hits,
                "total": total,
                "hit_rate": round((hits / total), 4) if total > 0 else 0.0,
            }
        )
    return rows


def _build_daily_rows(records: list[dict], days: int, now: datetime | None = None) -> list[dict]:
    if days <= 0:
        return []
    end = (now or datetime.now()).date()
    start = end - timedelta(days=days - 1)
    by_date: dict[str, list[dict]] = {}
    for row in records:
        date_text = str(row["date"])
        by_date.setdefault(date_text, []).append(row)

    rows: list[dict] = []
    cursor = start
    while cursor <= end:
        key = cursor.strftime("%Y-%m-%d")
        items = by_date.get(key, [])
        total = len(items)
        hits = sum(1 for item in items if item["is_hit"])
        expected = [float(item["expected_hit"]) for item in items if float(item["expected_hit"]) > 0.0]
        expected_hit = sum(expected) / len(expected) if expected else 0.0
        hit_rate = (hits / total) if total > 0 else 0.0
        rows.append(
            {
                "date": key,
                "hits": hits,
                "total": total,
                "hit_rate": round(hit_rate, 4) if total > 0 else 0.0,
                "expected_hit_rate": round(expected_hit, 4) if expected else 0.0,
                "ev_bias": round((hit_rate - expected_hit), 4) if total > 0 and expected else 0.0,
            }
        )
        cursor += timedelta(days=1)
    return rows


def build_handicap_dashboard_text(
    settlements: list[Mapping[str, object]],
    *,
    window: int = 30,
    breaker_threshold: int = 3,
) -> str:
    records = _normalize_handicap_records(settlements)
    if window > 0:
        records = records[-window:]
    metrics = _compute_gate_metrics(records, breaker_threshold=breaker_threshold)
    if metrics["sample_count"] <= 0:
        return f"让球专项看板: 近{window}场暂无可用样本。"

    lines = [
        f"让球专项看板 (近 {metrics['sample_count']} 场)",
        (
            f"命中率 {float(metrics['hit_rate']):.1%} ({metrics['hits']}/{metrics['sample_count']}) | "
            f"期望命中 {float(metrics['expected_hit_rate']):.1%} | EV偏差 {float(metrics['ev_bias']):+.1%}"
        ),
        f"连败 {metrics['losing_streak']} | 熔断 {'ON' if metrics['breaker_on'] else 'OFF'} | 平均|让球线| {float(metrics['avg_line_abs']):.2f}",
        "",
        "分档表现:",
    ]
    for row in _line_bucket_rows(records):
        lines.append(f"- {row['label']}: {row['hits']}/{row['total']} ({float(row['hit_rate']):.1%})")
    return "\n".join(lines)


def build_handicap_shadow_report_lines(
    settlements: list[Mapping[str, object]],
    *,
    days: int = 14,
    gate_window: int = 30,
    breaker_threshold: int = 3,
    now: datetime | None = None,
) -> list[str]:
    records_all = _normalize_handicap_records(settlements)
    gate_records = records_all[-gate_window:] if gate_window > 0 else records_all
    gate = _compute_gate_metrics(gate_records, breaker_threshold=breaker_threshold)
    daily_rows = _build_daily_rows(records_all, days=max(1, int(days)), now=now)
    line_rows = _line_bucket_rows(gate_records)
    current_time = (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Handicap Shadow Daily Report",
        "",
        f"- Generated At: {current_time}",
        f"- Gate Window: last {max(1, int(gate_window))} settled handicap picks",
        f"- Daily Window: last {max(1, int(days))} days",
        "",
        "## Gate Summary",
        "",
        "| Samples | Hits | Hit Rate | Expected Hit | EV Bias | Losing Streak | Breaker | Avg |line| |",
        "|---:|---:|---:|---:|---:|---:|---|---:|",
        (
            f"| {gate['sample_count']} | {gate['hits']} | {float(gate['hit_rate']):.1%} | "
            f"{float(gate['expected_hit_rate']):.1%} | {float(gate['ev_bias']):+.1%} | "
            f"{gate['losing_streak']} | {'ON' if gate['breaker_on'] else 'OFF'} | {float(gate['avg_line_abs']):.2f} |"
        ),
        "",
        "## Last 14 Days Table",
        "",
        "| Date | Samples | Hits | Hit Rate | Expected Hit | EV Bias |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in daily_rows:
        lines.append(
            f"| {row['date']} | {row['total']} | {row['hits']} | {float(row['hit_rate']):.1%} | "
            f"{float(row['expected_hit_rate']):.1%} | {float(row['ev_bias']):+.1%} |"
        )

    lines.extend(
        [
            "",
            "## Line Buckets (Gate Window)",
            "",
            "| Bucket | Samples | Hits | Hit Rate |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in line_rows:
        lines.append(f"| {row['label']} | {row['total']} | {row['hits']} | {float(row['hit_rate']):.1%} |")

    return lines


def build_handicap_shadow_report_filename(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"handicap_shadow_daily_{timestamp}.md"
