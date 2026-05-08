from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from c1.core.schema import FeatureSnapshot, PredictionSnapshot
from c1.modules.judge import load_governance_config


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "governance_cfg.yaml"
FEATURE_VERSION = "c1.phase2"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _normalize_side(value: Any) -> str:
    text = str(value or "").strip().lower()
    mapping = {
        "home": "home",
        "draw": "draw",
        "away": "away",
        "主": "home",
        "平": "draw",
        "客": "away",
        "主胜": "home",
        "平局": "draw",
        "客胜": "away",
    }
    return mapping.get(text, text)


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _freshness_score(hours: float, cap_hours: float) -> float:
    if hours <= 0:
        return 1.0
    return _clip(1.0 - (hours / max(cap_hours, 1.0)))


def _predicted_side(raw_fields: dict[str, Any], prediction_snapshot: PredictionSnapshot | None) -> str:
    if prediction_snapshot is not None:
        side = _normalize_side(prediction_snapshot.predicted_side)
        if side:
            return side
    return _normalize_side(raw_fields.get("predicted_side"))


def compute_lineup_freshness_hours(raw_fields: dict[str, Any], now: datetime | None = None) -> float:
    direct = raw_fields.get("lineup_freshness_hours")
    if direct not in (None, ""):
        return max(0.0, _safe_float(direct, default=0.0))

    updated_at = _parse_datetime(raw_fields.get("lineup_updated_at"))
    reference = now or datetime.now()
    if updated_at is None:
        return 999.0 if not _safe_bool(raw_fields.get("lineup_known"), default=False) else 24.0
    return max(0.0, (reference - updated_at).total_seconds() / 3600.0)


def compute_hours_to_kickoff(raw_fields: dict[str, Any], now: datetime | None = None) -> float | None:
    match_date = str(raw_fields.get("match_date", "")).strip()
    match_time = str(raw_fields.get("match_time", "")).strip()
    if not match_date:
        return None
    kickoff_text = f"{match_date} {match_time or '00:00'}"
    kickoff = _parse_datetime(kickoff_text)
    if kickoff is None:
        return None
    reference = now or datetime.now()
    return round((kickoff - reference).total_seconds() / 3600.0, 4)


def compute_info_quality(raw_fields: dict[str, Any], config: dict[str, Any]) -> float:
    feature_rules = config.get("feature_rules", {})
    weights = feature_rules.get("info_quality_weights", {})
    cap_hours = _safe_float(feature_rules.get("freshness_hours_cap"), default=24.0)
    lineup_freshness_hours = compute_lineup_freshness_hours(raw_fields)
    freshness = _freshness_score(_safe_float(raw_fields.get("data_freshness_hours"), default=lineup_freshness_hours), cap_hours)
    value = (
        _safe_float(weights.get("context_completeness"), default=0.28) * _clip(_safe_float(raw_fields.get("context_completeness"), default=1.0))
        + _safe_float(weights.get("odds_snapshot_quality"), default=0.24) * _clip(_safe_float(raw_fields.get("odds_snapshot_quality"), default=1.0))
        + _safe_float(weights.get("team_availability_quality"), default=0.18) * _clip(_safe_float(raw_fields.get("team_availability_quality"), default=1.0))
        + _safe_float(weights.get("freshness_score"), default=0.18) * freshness
        + _safe_float(weights.get("source_reliability"), default=0.12) * _clip(_safe_float(raw_fields.get("source_reliability"), default=1.0))
    )
    return round(_clip(value), 4)


def compute_missing_elo_loss(raw_fields: dict[str, Any]) -> float:
    if raw_fields.get("missing_elo_loss") not in (None, ""):
        return round(_clip(_safe_float(raw_fields.get("missing_elo_loss"), default=0.0)), 4)
    has_home = raw_fields.get("home_rating") not in (None, "")
    has_away = raw_fields.get("away_rating") not in (None, "")
    missing_count = int(not has_home) + int(not has_away)
    return round(missing_count / 2.0, 4)


def compute_odds_move_against_model(
    raw_fields: dict[str, Any],
    prediction_snapshot: PredictionSnapshot | None = None,
) -> float:
    side = _predicted_side(raw_fields, prediction_snapshot)
    if not side:
        return 0.0
    opening = _safe_float(raw_fields.get(f"opening_odds_{side}"), default=0.0)
    current = _safe_float(raw_fields.get(f"current_odds_{side}"), default=_safe_float(raw_fields.get(f"odds_{side}"), default=0.0))
    if opening <= 1.0 or current <= 1.0:
        return 0.0
    move = max(0.0, (current - opening) / opening)
    return round(_clip(move), 4)


def compute_line_move_against_model(
    raw_fields: dict[str, Any],
    prediction_snapshot: PredictionSnapshot | None = None,
) -> float:
    side = _predicted_side(raw_fields, prediction_snapshot)
    opening = _safe_float(raw_fields.get("opening_handicap_line"), default=_safe_float(raw_fields.get("opening_line"), default=0.0))
    current = _safe_float(raw_fields.get("current_handicap_line"), default=_safe_float(raw_fields.get("handicap_line"), default=opening))
    if side == "home":
        move = max(0.0, current - opening)
    elif side == "away":
        move = max(0.0, opening - current)
    elif side == "draw":
        move = abs(current - opening)
    else:
        move = 0.0
    normalized = min(move / 0.5, 1.0)
    return round(normalized, 4)


def compute_chaos_score(raw_fields: dict[str, Any], config: dict[str, Any]) -> float:
    feature_rules = config.get("feature_rules", {})
    weights = feature_rules.get("chaos_weights", {})
    lineup_penalty = 1.0 if not _safe_bool(raw_fields.get("lineup_known"), default=False) else 0.0
    value = (
        _safe_float(weights.get("market_divergence"), default=0.24) * _clip(_safe_float(raw_fields.get("market_divergence"), default=0.0))
        + _safe_float(weights.get("odds_move_against_model"), default=0.18) * _clip(_safe_float(raw_fields.get("odds_move_against_model"), default=0.0))
        + _safe_float(weights.get("line_move_against_model"), default=0.16) * _clip(_safe_float(raw_fields.get("line_move_against_model"), default=0.0))
        + _safe_float(weights.get("injury_conflict_score"), default=0.18) * _clip(_safe_float(raw_fields.get("injury_conflict_score"), default=0.0))
        + _safe_float(weights.get("schedule_pressure"), default=0.10) * _clip(_safe_float(raw_fields.get("schedule_pressure"), default=0.0))
        + _safe_float(weights.get("weather_risk"), default=0.08) * _clip(_safe_float(raw_fields.get("weather_risk"), default=0.0))
        + _safe_float(weights.get("lineup_penalty"), default=0.06) * lineup_penalty
    )
    return round(_clip(value), 4)


def build_governance_feature_fields(
    raw_fields: dict[str, Any],
    *,
    prediction_snapshot: PredictionSnapshot | None = None,
    config: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    cfg = config or load_governance_config(DEFAULT_CONFIG_PATH)
    fields = dict(raw_fields)
    lineup_known = _safe_bool(raw_fields.get("lineup_known"), default=False)
    lineup_freshness_hours = compute_lineup_freshness_hours(raw_fields, now=now)
    odds_move_against_model = compute_odds_move_against_model(raw_fields, prediction_snapshot=prediction_snapshot)
    line_move_against_model = compute_line_move_against_model(raw_fields, prediction_snapshot=prediction_snapshot)

    fields["lineup_known"] = lineup_known
    fields["lineup_freshness_hours"] = round(lineup_freshness_hours, 4)
    fields["kickoff_hours_to_match"] = compute_hours_to_kickoff(raw_fields, now=now)
    fields["missing_elo_loss"] = compute_missing_elo_loss(raw_fields)
    fields["odds_move_against_model"] = odds_move_against_model
    fields["line_move_against_model"] = line_move_against_model
    fields["info_quality"] = compute_info_quality(fields, cfg)
    fields["chaos_score"] = compute_chaos_score(fields, cfg)
    fields["market_side"] = _normalize_side(raw_fields.get("market_side"))
    fields["predicted_side"] = _predicted_side(raw_fields, prediction_snapshot)
    fields["environment_safe"] = _safe_bool(raw_fields.get("environment_safe"), default=True)
    fields["injury_conflict_score"] = round(_clip(_safe_float(raw_fields.get("injury_conflict_score"), default=0.0)), 4)
    fields["market_divergence"] = round(_clip(_safe_float(raw_fields.get("market_divergence"), default=0.0)), 4)
    fields["schedule_pressure"] = round(_clip(_safe_float(raw_fields.get("schedule_pressure"), default=0.0)), 4)
    fields["weather_risk"] = round(_clip(_safe_float(raw_fields.get("weather_risk"), default=0.0)), 4)
    return fields


def build_governance_feature_snapshot(
    *,
    match_id: str,
    raw_fields: dict[str, Any],
    prediction_snapshot: PredictionSnapshot | None = None,
    config: dict[str, Any] | None = None,
    source: str = "c1.features.governance",
    created_at: str | None = None,
    now: datetime | None = None,
) -> FeatureSnapshot:
    fields = build_governance_feature_fields(
        raw_fields,
        prediction_snapshot=prediction_snapshot,
        config=config,
        now=now,
    )
    return FeatureSnapshot(
        match_id=match_id,
        feature_version=FEATURE_VERSION,
        fields=fields,
        source=source,
        created_at=created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
