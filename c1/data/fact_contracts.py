from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


MATCH_FACT_SCHEMA_VERSION = "match_fact_v1"
ACTION_FACT_SCHEMA_VERSION = "action_fact_v1"
SOURCE_PROVENANCE_SCHEMA_VERSION = "source_provenance_v1"

MATCH_LEVEL_FORBIDDEN_KEYS = {
    "actions",
    "events",
    "event_bundle",
    "statsbomb_events",
    "spadl_actions",
}


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: object, default: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _int_or_none(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _float_or_none(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    text = _text(value).lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return None


def _list_of_dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _provider_ids(value: object, *, provider: str = "", source_id: str = "") -> dict[str, str]:
    if isinstance(value, Mapping):
        return {str(key): str(item) for key, item in value.items() if str(key).strip() and str(item).strip()}
    if provider and source_id:
        return {provider: source_id}
    return {}


def _reject_match_level_events(payload: Mapping[str, Any]) -> None:
    present = sorted(key for key in MATCH_LEVEL_FORBIDDEN_KEYS if key in payload)
    if present:
        raise ValueError(f"MatchFact cannot contain event/action arrays: {', '.join(present)}")


@dataclass(slots=True)
class SourceProvenance:
    provider: str
    source_id: str = ""
    source_version: str = ""
    source_vendor: str = ""
    source_url: str = ""
    ingested_at: str = ""
    raw_payload_ref: str = ""
    schema_version: str = SOURCE_PROVENANCE_SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MatchFact:
    match_id: str
    home_team_id: str
    away_team_id: str
    competition_id: str = ""
    season_id: str = ""
    stage: str = ""
    kickoff_at_utc: str = ""
    status: str = "scheduled"
    provider_match_ids: dict[str, str] = field(default_factory=dict)
    is_neutral: bool | None = None
    has_extratime: bool | None = None
    has_shootout: bool | None = None
    home_formation: str = ""
    away_formation: str = ""
    home_lineup: list[dict[str, Any]] = field(default_factory=list)
    away_lineup: list[dict[str, Any]] = field(default_factory=list)
    referees: list[dict[str, Any]] = field(default_factory=list)
    home_score_ft: int | None = None
    away_score_ft: int | None = None
    home_score_ht: int | None = None
    away_score_ht: int | None = None
    home_score_et: int | None = None
    away_score_et: int | None = None
    home_score_so: int | None = None
    away_score_so: int | None = None
    winning_team_id: str = ""
    odds_open_home: float | None = None
    odds_open_draw: float | None = None
    odds_open_away: float | None = None
    odds_close_home: float | None = None
    odds_close_draw: float | None = None
    odds_close_away: float | None = None
    odds_vendor: str = ""
    market_capture_time: str = ""
    data_freshness_minutes: float | None = None
    source: SourceProvenance | None = None
    schema_version: str = MATCH_FACT_SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        issues: list[str] = []
        if not self.match_id:
            issues.append("missing_match_id")
        if not self.home_team_id:
            issues.append("missing_home_team_id")
        if not self.away_team_id:
            issues.append("missing_away_team_id")
        if self.has_extratime and (self.home_score_et is None or self.away_score_et is None):
            issues.append("missing_extratime_score")
        if self.has_shootout and (self.home_score_so is None or self.away_score_so is None):
            issues.append("missing_shootout_score")
        if self.status == "finished" and (self.home_score_ft is None or self.away_score_ft is None):
            issues.append("missing_final_score")
        if self.winning_team_id and self.home_score_ft is not None and self.away_score_ft is not None:
            if self.home_score_ft > self.away_score_ft and self.winning_team_id != self.home_team_id:
                issues.append("winning_team_mismatch")
            if self.away_score_ft > self.home_score_ft and self.winning_team_id != self.away_team_id:
                issues.append("winning_team_mismatch")
        if not self.provider_match_ids and not (self.source and self.source.source_id):
            issues.append("missing_provider_match_ids")
        return issues

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ActionFact:
    action_id: str
    match_id: str
    seq_no: int
    period: str
    time_seconds: float
    team_id: str
    player_id: str
    action_family: str
    action_type: str
    result: str
    source_event_id: str = ""
    provider: str = ""
    related_player_id: str = ""
    timestamp_utc: str = ""
    bodypart: str = ""
    start_x: float | None = None
    start_y: float | None = None
    end_x: float | None = None
    end_y: float | None = None
    play_direction: str = ""
    is_synthetic: bool = False
    set_piece_type: str = ""
    possession_id: str = ""
    phase_id: str = ""
    score_for: int | None = None
    score_against: int | None = None
    under_pressure: bool | None = None
    qualifiers: dict[str, Any] = field(default_factory=dict)
    raw_payload_ref: str = ""
    schema_version: str = ACTION_FACT_SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        issues: list[str] = []
        for field_name in ("action_id", "match_id", "team_id", "player_id", "action_type", "result"):
            if not getattr(self, field_name):
                issues.append(f"missing_{field_name}")
        if self.seq_no < 0:
            issues.append("negative_seq_no")
        if self.time_seconds < 0:
            issues.append("negative_time_seconds")
        for name in ("start_x", "end_x"):
            value = getattr(self, name)
            if value is not None and not 0.0 <= value <= 120.0:
                issues.append(f"{name}_out_of_range")
        for name in ("start_y", "end_y"):
            value = getattr(self, name)
            if value is not None and not 0.0 <= value <= 80.0:
                issues.append(f"{name}_out_of_range")
        if self.is_synthetic and self.source_event_id:
            issues.append("synthetic_action_has_source_event_id")
        if not self.is_synthetic and not self.source_event_id:
            issues.append("missing_source_event_id")
        return issues

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_source_provenance(payload: Mapping[str, Any] | object) -> SourceProvenance:
    item = _as_mapping(payload)
    provider = _text(item.get("provider"), _text(item.get("source"), ""))
    return SourceProvenance(
        provider=provider,
        source_id=_text(item.get("source_id"), _text(item.get("provider_match_id"), "")),
        source_version=_text(item.get("source_version"), _text(item.get("version"), "")),
        source_vendor=_text(item.get("source_vendor"), provider),
        source_url=_text(item.get("source_url"), _text(item.get("url"), "")),
        ingested_at=_text(item.get("ingested_at"), ""),
        raw_payload_ref=_text(item.get("raw_payload_ref"), ""),
        schema_version=_text(item.get("schema_version"), SOURCE_PROVENANCE_SCHEMA_VERSION),
        metadata=_as_mapping(item.get("metadata")),
    )


def build_match_fact(payload: Mapping[str, Any] | object) -> MatchFact:
    item = _as_mapping(payload)
    _reject_match_level_events(item)
    source_payload = _as_mapping(item.get("source"))
    provider = _text(item.get("provider"), _text(item.get("source_vendor"), _text(source_payload.get("provider"), "")))
    source_id = _text(item.get("source_id"), _text(source_payload.get("source_id"), ""))
    source = build_source_provenance(source_payload or {"provider": provider, "source_id": source_id})
    return MatchFact(
        match_id=_text(item.get("match_id")),
        provider_match_ids=_provider_ids(item.get("provider_match_ids"), provider=provider, source_id=source_id),
        competition_id=_text(item.get("competition_id")),
        season_id=_text(item.get("season_id")),
        stage=_text(item.get("stage")),
        kickoff_at_utc=_text(item.get("kickoff_at_utc")),
        status=_text(item.get("status"), "scheduled"),
        is_neutral=_bool_or_none(item.get("is_neutral")),
        has_extratime=_bool_or_none(item.get("has_extratime")),
        has_shootout=_bool_or_none(item.get("has_shootout")),
        home_team_id=_text(item.get("home_team_id")),
        away_team_id=_text(item.get("away_team_id")),
        home_formation=_text(item.get("home_formation")),
        away_formation=_text(item.get("away_formation")),
        home_lineup=_list_of_dicts(item.get("home_lineup")),
        away_lineup=_list_of_dicts(item.get("away_lineup")),
        referees=_list_of_dicts(item.get("referees")),
        home_score_ft=_int_or_none(item.get("home_score_ft")),
        away_score_ft=_int_or_none(item.get("away_score_ft")),
        home_score_ht=_int_or_none(item.get("home_score_ht")),
        away_score_ht=_int_or_none(item.get("away_score_ht")),
        home_score_et=_int_or_none(item.get("home_score_et")),
        away_score_et=_int_or_none(item.get("away_score_et")),
        home_score_so=_int_or_none(item.get("home_score_so")),
        away_score_so=_int_or_none(item.get("away_score_so")),
        winning_team_id=_text(item.get("winning_team_id")),
        odds_open_home=_float_or_none(item.get("odds_open_home")),
        odds_open_draw=_float_or_none(item.get("odds_open_draw")),
        odds_open_away=_float_or_none(item.get("odds_open_away")),
        odds_close_home=_float_or_none(item.get("odds_close_home")),
        odds_close_draw=_float_or_none(item.get("odds_close_draw")),
        odds_close_away=_float_or_none(item.get("odds_close_away")),
        odds_vendor=_text(item.get("odds_vendor")),
        market_capture_time=_text(item.get("market_capture_time")),
        data_freshness_minutes=_float_or_none(item.get("data_freshness_minutes")),
        source=source,
        schema_version=_text(item.get("schema_version"), MATCH_FACT_SCHEMA_VERSION),
        metadata=_as_mapping(item.get("metadata")),
    )


def build_action_fact(payload: Mapping[str, Any] | object) -> ActionFact:
    item = _as_mapping(payload)
    return ActionFact(
        action_id=_text(item.get("action_id"), _text(item.get("event_id"), "")),
        match_id=_text(item.get("match_id"), _text(item.get("game_id"), "")),
        source_event_id=_text(item.get("source_event_id"), _text(item.get("original_event_id"), "")),
        provider=_text(item.get("provider")),
        seq_no=int(_int_or_none(item.get("seq_no")) or 0),
        period=_text(item.get("period"), _text(item.get("period_id"), "")),
        time_seconds=float(_float_or_none(item.get("time_seconds")) or 0.0),
        timestamp_utc=_text(item.get("timestamp_utc"), _text(item.get("timestamp"), "")),
        team_id=_text(item.get("team_id")),
        player_id=_text(item.get("player_id")),
        related_player_id=_text(item.get("related_player_id")),
        action_family=_text(item.get("action_family")),
        action_type=_text(item.get("action_type"), _text(item.get("type_name"), _text(item.get("type"), ""))),
        result=_text(item.get("result"), _text(item.get("result_name"), _text(item.get("outcome_type"), ""))),
        bodypart=_text(item.get("bodypart"), _text(item.get("bodypart_name"), _text(item.get("body_part"), ""))),
        start_x=_float_or_none(item.get("start_x")),
        start_y=_float_or_none(item.get("start_y")),
        end_x=_float_or_none(item.get("end_x")),
        end_y=_float_or_none(item.get("end_y")),
        play_direction=_text(item.get("play_direction")),
        is_synthetic=bool(_bool_or_none(item.get("is_synthetic")) or False),
        set_piece_type=_text(item.get("set_piece_type")),
        possession_id=_text(item.get("possession_id")),
        phase_id=_text(item.get("phase_id")),
        score_for=_int_or_none(item.get("score_for")),
        score_against=_int_or_none(item.get("score_against")),
        under_pressure=_bool_or_none(item.get("under_pressure")),
        qualifiers=_as_mapping(item.get("qualifiers")),
        raw_payload_ref=_text(item.get("raw_payload_ref")),
        schema_version=_text(item.get("schema_version"), ACTION_FACT_SCHEMA_VERSION),
        metadata=_as_mapping(item.get("metadata")),
    )
