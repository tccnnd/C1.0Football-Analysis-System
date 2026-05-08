from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Mapping


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _flatten_data_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, Mapping)]
    if isinstance(value, Mapping):
        data = value.get("data")
        if isinstance(data, list):
            return [dict(item) for item in data if isinstance(item, Mapping)]
    return []


def _extract_match_date(raw: Any) -> str:
    if isinstance(raw, Mapping):
        for key in ("date", "starting_at", "startingAt", "utc", "local"):
            text = _text(raw.get(key))
            if text:
                return text.split("T", 1)[0].split(" ", 1)[0]
        return ""
    text = _text(raw)
    if not text:
        return ""
    return text.split("T", 1)[0].split(" ", 1)[0]


def _extract_updated_at(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, Mapping):
            for key in ("updated_at", "last_processed_at", "starting_at", "date"):
                text = _text(value.get(key))
                if text:
                    return text
            continue
        text = _text(value)
        if text:
            return text
    return None


def _infer_location(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("location", "side", "type", "position"):
            side = _text(value.get(key)).lower()
            if side in {"home", "away"}:
                return side
    side = _text(value).lower()
    if side in {"home", "away"}:
        return side
    return ""


def _availability_score(absent_count: int, key_absent_count: int, lineup_known: bool) -> float:
    base = 1.0 if lineup_known else 0.72
    penalty = absent_count * 0.08 + key_absent_count * 0.14
    return round(_clip(base - penalty), 4)


def _collect_sportmonks_participants(item: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    participants = _flatten_data_items(item.get("participants"))
    if not participants and isinstance(item.get("teams"), Mapping):
        teams = item.get("teams") or {}
        home = teams.get("home")
        away = teams.get("away")
        return dict(home) if isinstance(home, Mapping) else {}, dict(away) if isinstance(away, Mapping) else {}
    home: dict[str, Any] = {}
    away: dict[str, Any] = {}
    for participant in participants:
        side = _infer_location(participant.get("meta") or participant)
        if not side:
            side = _infer_location(participant.get("location"))
        if side == "home" and not home:
            home = participant
        elif side == "away" and not away:
            away = participant
    if not home and participants:
        home = participants[0]
    if not away and len(participants) > 1:
        away = participants[1]
    return home, away


def _normalize_sportmonks_item(item: Mapping[str, Any]) -> dict[str, Any]:
    home, away = _collect_sportmonks_participants(item)
    home_id = _text(home.get("id"))
    away_id = _text(away.get("id"))
    lineups = _flatten_data_items(item.get("lineups"))
    sidelined = _flatten_data_items(item.get("sidelined"))

    home_absent = 0
    away_absent = 0
    home_key_absent = 0
    away_key_absent = 0
    for player in sidelined:
        side = _infer_location(player.get("meta") or player)
        team_id = _text(player.get("participant_id") or player.get("team_id") or player.get("player_team_id"))
        if not side:
            if home_id and team_id == home_id:
                side = "home"
            elif away_id and team_id == away_id:
                side = "away"
        is_key = bool(player.get("is_key")) or _text(player.get("importance")).lower() in {"key", "high"}
        if side == "home":
            home_absent += 1
            home_key_absent += 1 if is_key else 0
        elif side == "away":
            away_absent += 1
            away_key_absent += 1 if is_key else 0

    lineup_known = bool(lineups)
    availability_known = lineup_known or bool(sidelined)
    quality = 1.0 if lineup_known else (0.82 if sidelined else 0.0)

    return {
        "source_id": _text(item.get("id") or item.get("fixture_id")),
        "match_date": _extract_match_date(item.get("starting_at") or item.get("date")),
        "league": _text((item.get("league") or {}).get("name") if isinstance(item.get("league"), Mapping) else item.get("league_name")),
        "home_team": _text(home.get("name")),
        "away_team": _text(away.get("name")),
        "lineup_known": lineup_known,
        "lineup_updated_at": _extract_updated_at(item.get("last_processed_at"), item.get("updated_at"), item.get("starting_at")),
        "team_availability_quality": round(quality, 4),
        "injury_conflict_score": round(_clip(abs(home_absent - away_absent) * 0.12 + (home_key_absent + away_key_absent) * 0.08), 4),
        "home_availability_known": availability_known,
        "away_availability_known": availability_known,
        "home_absent_count": home_absent,
        "away_absent_count": away_absent,
        "home_key_absent_count": home_key_absent,
        "away_key_absent_count": away_key_absent,
        "home_availability_score": _availability_score(home_absent, home_key_absent, lineup_known),
        "away_availability_score": _availability_score(away_absent, away_key_absent, lineup_known),
        "provider_kind": "sportmonks",
    }


def normalize_sportmonks_rows(items: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        row = _normalize_sportmonks_item(item)
        if row.get("source_id") or (row.get("match_date") and row.get("home_team") and row.get("away_team")):
            rows.append(row)
    return rows


def _group_api_football_items(items: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in items:
        fixture = item.get("fixture") if isinstance(item.get("fixture"), Mapping) else {}
        fixture_id = _text((fixture or {}).get("id") or item.get("fixture_id") or item.get("match_id"))
        if not fixture_id:
            continue
        bucket = grouped.setdefault(
            fixture_id,
            {
                "fixture_id": fixture_id,
                "fixture": dict(fixture),
                "league": item.get("league") if isinstance(item.get("league"), Mapping) else {},
                "home": {},
                "away": {},
            },
        )
        if not bucket.get("league") and isinstance(item.get("league"), Mapping):
            bucket["league"] = dict(item.get("league") or {})
        side = _infer_location(item.get("meta") or item)
        if not side:
            side = _infer_location(item.get("location"))
        team = item.get("team") if isinstance(item.get("team"), Mapping) else {}
        if not side and isinstance(item.get("teams"), Mapping):
            teams = item.get("teams") or {}
            home = teams.get("home")
            away = teams.get("away")
            if isinstance(home, Mapping) and _text(home.get("id")) and _text(home.get("id")) == _text(team.get("id")):
                side = "home"
            elif isinstance(away, Mapping) and _text(away.get("id")) and _text(away.get("id")) == _text(team.get("id")):
                side = "away"
        if side not in {"home", "away"}:
            if isinstance(item.get("teams"), Mapping):
                teams = item.get("teams") or {}
                home = teams.get("home")
                away = teams.get("away")
                if isinstance(home, Mapping) and not bucket.get("home"):
                    bucket["home"] = {"team": dict(home)}
                if isinstance(away, Mapping) and not bucket.get("away"):
                    bucket["away"] = {"team": dict(away)}
            continue
        bucket[side] = dict(item)
    return grouped


def _normalize_api_football_group(group: Mapping[str, Any]) -> dict[str, Any]:
    home = group.get("home") if isinstance(group.get("home"), Mapping) else {}
    away = group.get("away") if isinstance(group.get("away"), Mapping) else {}
    fixture = group.get("fixture") if isinstance(group.get("fixture"), Mapping) else {}
    league = group.get("league") if isinstance(group.get("league"), Mapping) else {}

    def _lineup_known(item: Mapping[str, Any]) -> bool:
        return bool(item.get("startXI") or item.get("formation") or item.get("players"))

    def _missing_count(item: Mapping[str, Any]) -> tuple[int, int]:
        missing = item.get("missing_players") or item.get("injuries") or []
        if not isinstance(missing, list):
            return 0, 0
        key_missing = 0
        for player in missing:
            if not isinstance(player, Mapping):
                continue
            if bool(player.get("is_key")) or _text(player.get("importance")).lower() in {"key", "high"}:
                key_missing += 1
        return len(missing), key_missing

    def _has_availability(item: Mapping[str, Any]) -> bool:
        if _lineup_known(item):
            return True
        missing = item.get("missing_players") or item.get("injuries") or []
        return isinstance(missing, list) and len(missing) > 0

    home_lineup = _lineup_known(home)
    away_lineup = _lineup_known(away)
    home_known = _has_availability(home)
    away_known = _has_availability(away)
    lineup_known = home_lineup and away_lineup
    home_absent, home_key_absent = _missing_count(home)
    away_absent, away_key_absent = _missing_count(away)
    availability_known = home_known and away_known
    if lineup_known:
        quality = 1.0
    elif home_known or away_known:
        quality = 0.8
    else:
        quality = 0.0

    return {
        "source_id": _text(group.get("fixture_id")),
        "match_date": _extract_match_date(fixture.get("date")),
        "league": _text(league.get("name")),
        "home_team": _text((home.get("team") or {}).get("name") if isinstance(home.get("team"), Mapping) else home.get("team_name")),
        "away_team": _text((away.get("team") or {}).get("name") if isinstance(away.get("team"), Mapping) else away.get("team_name")),
        "lineup_known": lineup_known,
        "lineup_updated_at": _extract_updated_at(home.get("update"), away.get("update"), fixture.get("date")),
        "team_availability_quality": round(quality, 4),
        "injury_conflict_score": round(_clip(abs(home_absent - away_absent) * 0.12 + (home_key_absent + away_key_absent) * 0.08), 4),
        "home_availability_known": home_known,
        "away_availability_known": away_known,
        "home_absent_count": home_absent,
        "away_absent_count": away_absent,
        "home_key_absent_count": home_key_absent,
        "away_key_absent_count": away_key_absent,
        "home_availability_score": _availability_score(home_absent, home_key_absent, home_lineup),
        "away_availability_score": _availability_score(away_absent, away_key_absent, away_lineup),
        "provider_kind": "api_football",
    }


def normalize_api_football_rows(items: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    grouped = _group_api_football_items(items)
    for group in grouped.values():
        row = _normalize_api_football_group(group)
        if row.get("source_id") or (row.get("match_date") and row.get("home_team") and row.get("away_team")):
            rows.append(row)
    return rows


def normalize_provider_rows(provider_kind: str, items: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    kind = _text(provider_kind).lower() or "generic"
    materialized = [dict(item) for item in items if isinstance(item, Mapping)]
    if kind == "sportmonks":
        return normalize_sportmonks_rows(materialized)
    if kind == "api_football":
        return normalize_api_football_rows(materialized)
    return materialized
