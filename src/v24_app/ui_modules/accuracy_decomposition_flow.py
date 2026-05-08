from __future__ import annotations

import csv
import io
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Mapping

from c1.data.availability_store import C1AvailabilityStore


_DIMENSION_LABELS = {
    "play_type": "玩法",
    "league": "联赛",
    "lead_time": "预测提前量",
    "lineup": "阵容信息",
}

_PLAY_TYPE_LABELS = {
    "1x2": "胜平负",
    "handicap": "让球",
    "total_goals": "总进球",
    "score": "比分",
    "ou": "大小球",
    "parlay_2": "二串一",
}


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _as_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on", "是"}:
        return True
    if text in {"0", "false", "no", "n", "off", "否"}:
        return False
    return None


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    candidates = [text]
    if len(text) >= 19:
        candidates.append(text[:19])
    for candidate in candidates:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(candidate, fmt)
            except Exception:
                continue
    return None


def _parse_kickoff(match_date: object, match_time: object) -> datetime | None:
    date_text = str(match_date or "").strip()
    time_text = str(match_time or "").strip()
    if not date_text:
        return None
    normalized_time = "00:00"
    if time_text:
        parts = time_text.split(":")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            normalized_time = f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    for fmt in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(f"{date_text} {normalized_time}", fmt)
        except Exception:
            continue
    return None


def _load_market_snapshot_index(project_root: Path) -> dict[str, list[datetime]]:
    snapshot_file = project_root / "data" / "state" / "market_snapshots.json"
    if not snapshot_file.exists():
        return {}
    try:
        payload = json.loads(snapshot_file.read_text(encoding="utf-8"))
    except Exception:
        return {}
    items = payload.get("items", {}) if isinstance(payload, dict) else {}
    if not isinstance(items, dict):
        return {}

    index: dict[str, list[datetime]] = {}
    for record in items.values():
        if not isinstance(record, dict):
            continue
        match = record.get("match", {})
        if not isinstance(match, dict):
            continue
        match_id = str(match.get("match_id", "")).strip()
        if not match_id:
            continue
        saved_at = _parse_datetime(record.get("saved_at"))
        if saved_at is None:
            continue
        index.setdefault(match_id, []).append(saved_at)
    return index


def _resolve_lead_time_bucket(
    *,
    match_id: str,
    match_date: object,
    match_time: object,
    snapshot_index: Mapping[str, list[datetime]],
) -> str:
    kickoff = _parse_kickoff(match_date, match_time)
    if kickoff is None:
        return "unknown"
    saved_points = list(snapshot_index.get(match_id, []))
    if not saved_points:
        return "unknown"

    saved_points.sort()
    selected = None
    for ts in saved_points:
        if ts <= kickoff:
            selected = ts
    if selected is None:
        selected = saved_points[-1]

    lead_hours = (kickoff - selected).total_seconds() / 3600.0
    if lead_hours < 0:
        return "T+after_kickoff"
    if lead_hours <= 1:
        return "T-0~1h"
    if lead_hours <= 3:
        return "T-1~3h"
    if lead_hours <= 12:
        return "T-3~12h"
    return "T-12h+"


def _resolve_lineup_bucket(item: Mapping[str, object], store: C1AvailabilityStore) -> str:
    record = store.resolve_for_match(item)
    if not isinstance(record, dict) or not record:
        return "unknown"
    home_known = _as_bool(record.get("home_availability_known"))
    away_known = _as_bool(record.get("away_availability_known"))
    lineup_known = _as_bool(record.get("lineup_known"))
    freshness = _safe_float(record.get("lineup_freshness_hours"), default=-1.0)

    if (home_known is True and away_known is True) or lineup_known is True:
        if freshness >= 0.0 and freshness <= 6.0:
            return "known_fresh"
        if freshness > 6.0:
            return "known_stale"
        return "known_no_age"
    if home_known is True or away_known is True:
        return "partial_known"
    return "unknown"


def _normalize_expected_hit(primary: object, fallback: object = None) -> float:
    value = _safe_float(primary, default=-1.0)
    if value <= 0.0 or value > 1.0:
        value = _safe_float(fallback, default=-1.0)
    if value <= 0.0 or value > 1.0:
        return 0.0
    return value


def _single_play_records(
    settlements: list[Mapping[str, object]],
    *,
    snapshot_index: Mapping[str, list[datetime]],
    availability_store: C1AvailabilityStore,
) -> list[dict]:
    records: list[dict] = []
    play_specs = (
        ("1x2", "is_correct", "prediction_confidence"),
        ("handicap", "handicap_is_correct", "handicap_confidence"),
        ("total_goals", "total_goals_is_correct", "total_goals_confidence"),
        ("score", "score_is_correct", "score_confidence"),
        ("ou", "ou_is_correct", "ou_confidence"),
    )
    for item in settlements:
        if not isinstance(item, Mapping):
            continue
        match_id = str(item.get("match_id", "")).strip()
        if not match_id:
            continue
        timestamp = str(item.get("timestamp", "")).strip()
        lead_time_bucket = _resolve_lead_time_bucket(
            match_id=match_id,
            match_date=item.get("match_date"),
            match_time=item.get("match_time"),
            snapshot_index=snapshot_index,
        )
        lineup_bucket = _resolve_lineup_bucket(item, availability_store)
        league = str(item.get("league", "")).strip() or "-"
        for play_type, hit_field, confidence_field in play_specs:
            is_hit = _as_bool(item.get(hit_field))
            if is_hit is None:
                continue
            records.append(
                {
                    "category": "single",
                    "play_type": play_type,
                    "bucket_play_type": _PLAY_TYPE_LABELS.get(play_type, play_type),
                    "league": league,
                    "lead_time": lead_time_bucket,
                    "lineup": lineup_bucket,
                    "timestamp": timestamp,
                    "is_hit": is_hit,
                    "expected_hit": _normalize_expected_hit(item.get(confidence_field), item.get("prediction_confidence")),
                }
            )
    return records


def _parlay_records(parlays: list[Mapping[str, object]]) -> list[dict]:
    rows: list[dict] = []
    for item in parlays:
        if not isinstance(item, Mapping):
            continue
        status = str(item.get("status", "")).strip().lower()
        is_hit = _as_bool(item.get("is_hit"))
        if is_hit is None and status in {"won", "lost"}:
            is_hit = status == "won"
        if is_hit is None:
            continue
        timestamp = str(item.get("settled_at") or item.get("created_at") or "").strip()
        rows.append(
            {
                "category": "parlay",
                "play_type": "parlay_2",
                "bucket_play_type": _PLAY_TYPE_LABELS["parlay_2"],
                "league": "混合串关",
                "lead_time": "-",
                "lineup": "-",
                "timestamp": timestamp,
                "is_hit": is_hit,
                "expected_hit": _normalize_expected_hit(item.get("expected_hit")),
            }
        )
    return rows


def _compute_metrics(records: list[dict]) -> dict:
    if not records:
        return {
            "sample_count": 0,
            "hit_count": 0,
            "hit_rate": 0.0,
            "expected_count": 0,
            "expected_hit_rate": 0.0,
            "ev_bias": 0.0,
            "brier": 0.0,
            "logloss": 0.0,
            "losing_streak": 0,
        }

    ordered = sorted(records, key=lambda row: str(row.get("timestamp", "")))
    sample_count = len(ordered)
    hit_count = sum(1 for row in ordered if bool(row.get("is_hit")))
    hit_rate = hit_count / sample_count if sample_count > 0 else 0.0

    expected_values: list[float] = []
    brier_values: list[float] = []
    logloss_values: list[float] = []
    eps = 1e-6
    for row in ordered:
        p = _safe_float(row.get("expected_hit"), default=0.0)
        if p <= 0.0 or p >= 1.0:
            continue
        y = 1.0 if bool(row.get("is_hit")) else 0.0
        expected_values.append(p)
        brier_values.append((p - y) ** 2)
        pc = min(1.0 - eps, max(eps, p))
        logloss_values.append(-(y * math.log(pc) + (1.0 - y) * math.log(1.0 - pc)))

    expected_count = len(expected_values)
    expected_hit_rate = (sum(expected_values) / expected_count) if expected_count > 0 else 0.0
    brier = (sum(brier_values) / expected_count) if expected_count > 0 else 0.0
    logloss = (sum(logloss_values) / expected_count) if expected_count > 0 else 0.0

    losing_streak = 0
    for row in reversed(ordered):
        if bool(row.get("is_hit")):
            break
        losing_streak += 1

    return {
        "sample_count": sample_count,
        "hit_count": hit_count,
        "hit_rate": round(hit_rate, 4),
        "expected_count": expected_count,
        "expected_hit_rate": round(expected_hit_rate, 4),
        "ev_bias": round((hit_rate - expected_hit_rate) if expected_count > 0 else 0.0, 4),
        "brier": round(brier, 4),
        "logloss": round(logloss, 4),
        "losing_streak": losing_streak,
    }


def _dimension_rows(records: list[dict], dimension: str) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for row in records:
        if dimension != "play_type" and row.get("category") != "single":
            continue
        if dimension == "play_type":
            key = str(row.get("bucket_play_type") or row.get("play_type") or "-")
        else:
            key = str(row.get(dimension, "-") or "-")
        groups.setdefault(key, []).append(row)
    rows: list[dict] = []
    for bucket, items in groups.items():
        metrics = _compute_metrics(items)
        rows.append(
            {
                "dimension": dimension,
                "dimension_label": _DIMENSION_LABELS.get(dimension, dimension),
                "bucket": bucket,
                "sample_count": metrics["sample_count"],
                "hit_count": metrics["hit_count"],
                "hit_rate": metrics["hit_rate"],
                "expected_count": metrics["expected_count"],
                "expected_hit_rate": metrics["expected_hit_rate"],
                "ev_bias": metrics["ev_bias"],
                "brier": metrics["brier"],
                "logloss": metrics["logloss"],
                "losing_streak": metrics["losing_streak"],
            }
        )
    rows.sort(key=lambda item: (-int(item["sample_count"]), str(item["bucket"])))
    return rows


def build_accuracy_decomposition_artifacts(
    *,
    project_root: str | Path,
    settlements: list[Mapping[str, object]],
    parlay_settlements: list[Mapping[str, object]],
) -> dict[str, object]:
    root = Path(project_root)
    snapshot_index = _load_market_snapshot_index(root)
    availability_store = C1AvailabilityStore(root)
    records = _single_play_records(
        settlements,
        snapshot_index=snapshot_index,
        availability_store=availability_store,
    ) + _parlay_records(parlay_settlements)

    summary = {
        "single_settlement_count": len(settlements),
        "parlay_settlement_count": len(parlay_settlements),
        "record_count": len(records),
    }
    for key in ("play_type", "league", "lead_time", "lineup"):
        summary[f"bucket_count_{key}"] = 0

    rows: list[dict] = []
    for dimension in ("play_type", "league", "lead_time", "lineup"):
        part = _dimension_rows(records, dimension)
        summary[f"bucket_count_{dimension}"] = len(part)
        rows.extend(part)

    return {"rows": rows, "summary": summary}


def build_accuracy_decomposition_report_lines(rows: list[Mapping[str, object]], summary: Mapping[str, object]) -> list[str]:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Accuracy Decomposition Report",
        "",
        f"- Generated At: {generated_at}",
        f"- Single Settlements: {int(summary.get('single_settlement_count', 0) or 0)}",
        f"- Parlay Settlements: {int(summary.get('parlay_settlement_count', 0) or 0)}",
        f"- Decomposition Records: {int(summary.get('record_count', 0) or 0)}",
        "",
    ]
    if not rows:
        lines.append("No settled samples available.")
        return lines

    dimension_order = ("play_type", "league", "lead_time", "lineup")
    for dimension in dimension_order:
        dimension_rows = [row for row in rows if str(row.get("dimension")) == dimension]
        if not dimension_rows:
            continue
        title = _DIMENSION_LABELS.get(dimension, dimension)
        lines.extend(
            [
                f"## {title}",
                "",
                "| Bucket | Samples | Hits | Hit Rate | Expected Hit | EV Bias | Brier | LogLoss | Losing Streak |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in dimension_rows:
            lines.append(
                f"| {row.get('bucket', '-')} | {int(row.get('sample_count', 0) or 0)} | "
                f"{int(row.get('hit_count', 0) or 0)} | {float(row.get('hit_rate', 0.0) or 0.0):.1%} | "
                f"{float(row.get('expected_hit_rate', 0.0) or 0.0):.1%} | {float(row.get('ev_bias', 0.0) or 0.0):+.1%} | "
                f"{float(row.get('brier', 0.0) or 0.0):.4f} | {float(row.get('logloss', 0.0) or 0.0):.4f} | "
                f"{int(row.get('losing_streak', 0) or 0)} |"
            )
        lines.append("")

    flags = [
        row
        for row in rows
        if int(row.get("sample_count", 0) or 0) >= 8 and float(row.get("ev_bias", 0.0) or 0.0) <= -0.08
    ]
    lines.extend(["## Priority Weak Buckets", ""])
    if not flags:
        lines.append("- No bucket reached weak-threshold (sample>=8 and EV bias<=-8%).")
    else:
        for row in flags[:10]:
            lines.append(
                f"- [{row.get('dimension_label')}] {row.get('bucket')}: "
                f"hit {float(row.get('hit_rate', 0.0) or 0.0):.1%}, "
                f"expected {float(row.get('expected_hit_rate', 0.0) or 0.0):.1%}, "
                f"bias {float(row.get('ev_bias', 0.0) or 0.0):+.1%}, "
                f"samples {int(row.get('sample_count', 0) or 0)}"
            )
    return lines


def build_accuracy_decomposition_csv_text(rows: list[Mapping[str, object]]) -> str:
    fieldnames = [
        "dimension",
        "dimension_label",
        "bucket",
        "sample_count",
        "hit_count",
        "hit_rate",
        "expected_count",
        "expected_hit_rate",
        "ev_bias",
        "brier",
        "logloss",
        "losing_streak",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in fieldnames})
    return buf.getvalue()


def build_accuracy_decomposition_report_filename(now: datetime | None = None) -> str:
    ts = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"accuracy_decomposition_{ts}.md"


def build_accuracy_decomposition_csv_filename(now: datetime | None = None) -> str:
    ts = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"accuracy_decomposition_{ts}.csv"
