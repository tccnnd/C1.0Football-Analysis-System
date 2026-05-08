from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Mapping


TEMPLATE_COLUMNS = [
    "match_id",
    "source_id",
    "match_date",
    "league",
    "home_team",
    "away_team",
    "home_availability_known",
    "away_availability_known",
    "lineup_updated_at",
    "lineup_freshness_hours",
    "team_availability_quality",
    "injury_conflict_score",
    "home_absent_count",
    "away_absent_count",
    "home_key_absent_count",
    "away_key_absent_count",
    "home_availability_score",
    "away_availability_score",
    "schedule_pressure",
    "weather_risk",
    "environment_safe",
    "notes",
]


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _get_value(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def build_availability_template_rows(matches: Iterable[Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for match in matches:
        rows.append(
            {
                "match_id": _text(_get_value(match, "match_id")),
                "source_id": _text(_get_value(match, "source_id")),
                "match_date": _text(_get_value(match, "match_date")),
                "league": _text(_get_value(match, "league")),
                "home_team": _text(_get_value(match, "home_team")),
                "away_team": _text(_get_value(match, "away_team")),
                "home_availability_known": "",
                "away_availability_known": "",
                "lineup_updated_at": "",
                "lineup_freshness_hours": "",
                "team_availability_quality": "",
                "injury_conflict_score": "",
                "home_absent_count": "",
                "away_absent_count": "",
                "home_key_absent_count": "",
                "away_key_absent_count": "",
                "home_availability_score": "",
                "away_availability_score": "",
                "schedule_pressure": "",
                "weather_risk": "",
                "environment_safe": "",
                "notes": "",
            }
        )
    return rows


def export_availability_template_csv(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TEMPLATE_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _text(row.get(column, "")) for column in TEMPLATE_COLUMNS})
    return output_path
