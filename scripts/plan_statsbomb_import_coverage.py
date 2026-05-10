from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from audit_statsbomb_settlement_coverage import items_from_payload, read_json, write_json
from import_statsbomb_open_data import load_competitions, load_matches


MatchLoader = Callable[[int, int], list[dict[str, Any]]]


def date_text(value: object) -> str:
    return str(value or "").strip()[:10]


def date_range(values: list[str]) -> tuple[str | None, str | None]:
    usable = [item for item in values if item]
    return (min(usable), max(usable)) if usable else (None, None)


def settlement_date_counter(settlements: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for item in settlements:
        value = date_text(item.get("match_date"))
        if value:
            counter[value] += 1
    return counter


def summarize_competition_matches(
    competition: dict[str, Any],
    matches: list[dict[str, Any]],
    settlement_dates: Counter[str],
) -> dict[str, Any]:
    match_dates = [date_text(item.get("match_date")) for item in matches if date_text(item.get("match_date"))]
    date_set = set(match_dates)
    overlap_dates = sorted(date for date in date_set if date in settlement_dates)
    overlap_settlement_count = sum(settlement_dates[date] for date in overlap_dates)
    start, end = date_range(match_dates)
    return {
        "competition_id": competition.get("competition_id"),
        "season_id": competition.get("season_id"),
        "competition_name": competition.get("competition_name"),
        "season_name": competition.get("season_name"),
        "country_name": competition.get("country_name"),
        "match_count": len(matches),
        "date_start": start,
        "date_end": end,
        "overlap_date_count": len(overlap_dates),
        "overlap_settlement_count": overlap_settlement_count,
        "overlap_dates": overlap_dates[:20],
        "sample_matches": [
            {
                "match_id": item.get("match_id"),
                "match_date": item.get("match_date"),
                "home_team": (item.get("home_team") or {}).get("home_team_name") if isinstance(item.get("home_team"), dict) else "",
                "away_team": (item.get("away_team") or {}).get("away_team_name") if isinstance(item.get("away_team"), dict) else "",
            }
            for item in matches[:5]
        ],
    }


def build_statsbomb_import_coverage_plan(
    *,
    competitions: list[dict[str, Any]],
    settlements: list[dict[str, Any]],
    load_matches_fn: MatchLoader,
    limit_competitions: int | None = None,
) -> dict[str, Any]:
    settlement_dates = settlement_date_counter(settlements)
    settlement_start, settlement_end = date_range(list(settlement_dates.elements()))
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    requested = competitions[: max(0, int(limit_competitions))] if limit_competitions is not None else list(competitions)

    for competition in requested:
        try:
            competition_id = int(competition.get("competition_id"))
            season_id = int(competition.get("season_id"))
        except Exception:
            failures.append(f"invalid competition ids: {competition}")
            continue
        try:
            matches = load_matches_fn(competition_id, season_id)
        except Exception as exc:
            failures.append(f"{competition_id}/{season_id}: {exc}")
            continue
        rows.append(summarize_competition_matches(competition, matches, settlement_dates))

    rows.sort(
        key=lambda item: (
            -int(item.get("overlap_settlement_count") or 0),
            -int(item.get("overlap_date_count") or 0),
            str(item.get("date_start") or "9999-99-99"),
            str(item.get("competition_name") or ""),
        )
    )
    overlap_rows = [item for item in rows if int(item.get("overlap_settlement_count") or 0) > 0]
    recent_rows = sorted(
        rows,
        key=lambda item: (
            str(item.get("date_end") or ""),
            int(item.get("match_count") or 0),
        ),
        reverse=True,
    )
    recommendation = "import_overlap_events" if overlap_rows else "no_date_overlap"
    return {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "settlement_count": len(settlements),
        "settlement_date_count": len(settlement_dates),
        "settlement_date_start": settlement_start,
        "settlement_date_end": settlement_end,
        "scanned_competitions": len(requested),
        "successful_competitions": len(rows),
        "failure_count": len(failures),
        "failures": failures,
        "overlap_competition_count": len(overlap_rows),
        "top_overlap_competitions": overlap_rows[:20],
        "recent_competitions": recent_rows[:20],
        "recommendation": recommendation,
        "next_action": (
            "Run import_statsbomb_open_data.py for top_overlap_competitions."
            if overlap_rows
            else "StatsBomb Open Data has no date overlap with current settlements; use it for historical review training, and keep app settlements for live strategy backtests."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan which StatsBomb competitions should be imported for settlement coverage.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--offline-dir", type=Path, default=None)
    parser.add_argument("--limit-competitions", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    state_dir = args.project_root / "data" / "state"
    settlements = items_from_payload(read_json(state_dir / "settlements.json"))
    competitions = load_competitions(offline_dir=args.offline_dir, timeout=max(1, int(args.timeout)))

    def loader(competition_id: int, season_id: int) -> list[dict[str, Any]]:
        return load_matches(
            competition_id=competition_id,
            season_id=season_id,
            offline_dir=args.offline_dir,
            timeout=max(1, int(args.timeout)),
        )

    plan = build_statsbomb_import_coverage_plan(
        competitions=competitions,
        settlements=settlements,
        load_matches_fn=loader,
        limit_competitions=args.limit_competitions,
    )
    output_path = args.output or state_dir / "statsbomb_import_coverage_plan.json"
    write_json(output_path, plan)
    text = json.dumps({**plan, "output_path": str(output_path)}, ensure_ascii=False, indent=2)
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        raise SystemExit(f"StatsBomb coverage planning failed: {exc}")
