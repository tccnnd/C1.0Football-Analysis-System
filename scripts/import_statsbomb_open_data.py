from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


SOURCE_NAME = "StatsBomb Open Data"
SOURCE_URL = "https://github.com/statsbomb/open-data"
RAW_BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_json(url: str, timeout: int = 30) -> object:
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def load_competitions(*, offline_dir: Path | None, timeout: int) -> list[dict]:
    if offline_dir is not None:
        payload = read_json(offline_dir / "competitions.json")
    else:
        payload = fetch_json(f"{RAW_BASE_URL}/competitions.json", timeout=timeout)
    return [item for item in payload if isinstance(item, dict)]


def load_matches(*, competition_id: int, season_id: int, offline_dir: Path | None, timeout: int) -> list[dict]:
    if offline_dir is not None:
        payload = read_json(offline_dir / "matches" / str(competition_id) / f"{season_id}.json")
    else:
        payload = fetch_json(f"{RAW_BASE_URL}/matches/{competition_id}/{season_id}.json", timeout=timeout)
    return [item for item in payload if isinstance(item, dict)]


def load_events(*, match_id: int, offline_dir: Path | None, timeout: int) -> list[dict]:
    if offline_dir is not None:
        payload = read_json(offline_dir / "events" / f"{match_id}.json")
    else:
        payload = fetch_json(f"{RAW_BASE_URL}/events/{match_id}.json", timeout=timeout)
    return [item for item in payload if isinstance(item, dict)]


def nested_name(payload: dict, key: str, default: str = "") -> str:
    value = payload.get(key)
    if isinstance(value, dict):
        return str(value.get("name") or default)
    return default


def team_name(event: dict) -> str:
    team = event.get("team")
    if isinstance(team, dict):
        return str(team.get("name") or "")
    return ""


def player_name(event: dict) -> str:
    player = event.get("player")
    if isinstance(player, dict):
        return str(player.get("name") or "")
    return ""


def event_minute(event: dict) -> int | None:
    try:
        return int(event.get("minute"))
    except Exception:
        return None


def event_type(event: dict) -> str:
    raw_type = event.get("type")
    if isinstance(raw_type, dict):
        return str(raw_type.get("name") or "")
    return ""


def stats_template() -> dict:
    return {
        "shots": 0,
        "shots_on_target": 0,
        "goals": 0,
        "xg": 0.0,
        "passes": 0,
        "carries": 0,
        "pressures": 0,
        "fouls_committed": 0,
        "yellow_cards": 0,
        "red_cards": 0,
        "substitutions": 0,
    }


def card_bucket(card_name: str) -> str | None:
    normalized = card_name.lower()
    if "red" in normalized:
        return "red_cards"
    if "yellow" in normalized:
        return "yellow_cards"
    return None


def summarize_events(match: dict, events: list[dict]) -> dict:
    home_team = str(match.get("home_team", {}).get("home_team_name") or "")
    away_team = str(match.get("away_team", {}).get("away_team_name") or "")
    teams = [team for team in (home_team, away_team) if team]
    team_stats: dict[str, dict] = {team: stats_template() for team in teams}
    event_counts: Counter[str] = Counter()
    top_shooters: dict[str, dict] = {}
    goals: list[dict] = []

    for event in events:
        kind = event_type(event)
        if not kind:
            continue
        event_counts[kind] += 1
        current_team = team_name(event)
        if current_team and current_team not in team_stats:
            team_stats[current_team] = stats_template()
        stats = team_stats.get(current_team)

        if kind == "Shot" and stats is not None:
            shot = event.get("shot") if isinstance(event.get("shot"), dict) else {}
            outcome = nested_name(shot, "outcome")
            xg = float(shot.get("statsbomb_xg") or 0.0)
            stats["shots"] += 1
            stats["xg"] = round(float(stats["xg"]) + xg, 4)
            if outcome in {"Goal", "Saved", "Saved To Post", "Post", "Saved Off Target"}:
                stats["shots_on_target"] += 1
            shooter = player_name(event) or "-"
            shooter_key = f"{current_team}|{shooter}"
            row = top_shooters.setdefault(
                shooter_key,
                {"team": current_team, "player": shooter, "shots": 0, "goals": 0, "xg": 0.0},
            )
            row["shots"] += 1
            row["xg"] = round(float(row["xg"]) + xg, 4)
            if outcome == "Goal":
                stats["goals"] += 1
                row["goals"] += 1
                goals.append(
                    {
                        "minute": event_minute(event),
                        "team": current_team,
                        "player": shooter,
                        "xg": round(xg, 4),
                    }
                )
        elif kind == "Pass" and stats is not None:
            stats["passes"] += 1
        elif kind == "Carry" and stats is not None:
            stats["carries"] += 1
        elif kind == "Pressure" and stats is not None:
            stats["pressures"] += 1
        elif kind == "Foul Committed" and stats is not None:
            stats["fouls_committed"] += 1
            foul = event.get("foul_committed") if isinstance(event.get("foul_committed"), dict) else {}
            bucket = card_bucket(nested_name(foul, "card"))
            if bucket:
                stats[bucket] += 1
        elif kind == "Bad Behaviour" and stats is not None:
            behaviour = event.get("bad_behaviour") if isinstance(event.get("bad_behaviour"), dict) else {}
            bucket = card_bucket(nested_name(behaviour, "card"))
            if bucket:
                stats[bucket] += 1
        elif kind == "Substitution" and stats is not None:
            stats["substitutions"] += 1
        elif kind == "Own Goal For" and stats is not None:
            stats["goals"] += 1
            goals.append(
                {
                    "minute": event_minute(event),
                    "team": current_team,
                    "player": player_name(event) or "-",
                    "xg": 0.0,
                }
            )

    for stats in team_stats.values():
        stats["xg"] = round(float(stats["xg"]), 4)

    goal_minutes = [goal["minute"] for goal in goals if goal.get("minute") is not None]
    shooters = sorted(
        top_shooters.values(),
        key=lambda item: (-int(item["shots"]), -float(item["xg"]), str(item["player"])),
    )
    return {
        "event_count": len(events),
        "event_type_counts": dict(event_counts.most_common()),
        "team_stats": dict(sorted(team_stats.items())),
        "goals": sorted(goals, key=lambda item: (item["minute"] is None, item["minute"] or 0, item["team"])),
        "first_goal_minute": min(goal_minutes) if goal_minutes else None,
        "last_goal_minute": max(goal_minutes) if goal_minutes else None,
        "top_shooters": shooters[:10],
    }


def convert_match(match: dict, events: list[dict]) -> dict:
    match_id = int(match.get("match_id"))
    competition = match.get("competition") if isinstance(match.get("competition"), dict) else {}
    season = match.get("season") if isinstance(match.get("season"), dict) else {}
    stage = match.get("competition_stage") if isinstance(match.get("competition_stage"), dict) else {}
    home_team = match.get("home_team") if isinstance(match.get("home_team"), dict) else {}
    away_team = match.get("away_team") if isinstance(match.get("away_team"), dict) else {}
    kick_off = str(match.get("kick_off") or "")

    return {
        "match_id": f"statsbomb:{match_id}",
        "source_match_id": match_id,
        "match_date": str(match.get("match_date") or ""),
        "match_time": kick_off[:5] if kick_off else "",
        "league": str(competition.get("competition_name") or ""),
        "season": str(season.get("season_name") or ""),
        "home_team": str(home_team.get("home_team_name") or ""),
        "away_team": str(away_team.get("away_team_name") or ""),
        "home_goals": match.get("home_score"),
        "away_goals": match.get("away_score"),
        "match_status": str(match.get("match_status") or ""),
        "match_status_360": str(match.get("match_status_360") or ""),
        "stage": str(stage.get("name") or ""),
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "event_summary": summarize_events(match, events),
    }


def filter_competitions(
    competitions: list[dict],
    *,
    competition_id: int | None,
    season_id: int | None,
    limit_competitions: int | None,
) -> list[dict]:
    selected = []
    for item in competitions:
        if competition_id is not None and int(item.get("competition_id", -1)) != competition_id:
            continue
        if season_id is not None and int(item.get("season_id", -1)) != season_id:
            continue
        selected.append(item)
    selected.sort(
        key=lambda item: (
            str(item.get("competition_name") or ""),
            str(item.get("season_name") or ""),
            int(item.get("competition_id", 0)),
            int(item.get("season_id", 0)),
        )
    )
    if limit_competitions is not None:
        return selected[: max(0, int(limit_competitions))]
    return selected


def build_audit(
    *,
    competitions: list[dict],
    records: list[dict],
    failures: list[str],
    event_failures: list[str],
) -> dict:
    competition_counts: Counter[str] = Counter()
    season_counts: Counter[str] = Counter()
    date_values: list[str] = []
    total_events = 0
    for record in records:
        competition_counts[str(record.get("league") or "-")] += 1
        season_counts[str(record.get("season") or "-")] += 1
        if record.get("match_date"):
            date_values.append(str(record.get("match_date")))
        summary = record.get("event_summary") if isinstance(record.get("event_summary"), dict) else {}
        total_events += int(summary.get("event_count") or 0)
    return {
        "updated_at": now_text(),
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "attribution": "Data source: StatsBomb",
        "license_note": "Follow StatsBomb Open Data repository terms and attribution requirements before publishing derived work.",
        "requested_competitions": [
            {
                "competition_id": item.get("competition_id"),
                "season_id": item.get("season_id"),
                "competition_name": item.get("competition_name"),
                "season_name": item.get("season_name"),
            }
            for item in competitions
        ],
        "records": len(records),
        "total_events": total_events,
        "date_start": min(date_values) if date_values else None,
        "date_end": max(date_values) if date_values else None,
        "competition_counts": dict(competition_counts.most_common()),
        "season_counts": dict(season_counts.most_common()),
        "failure_count": len(failures) + len(event_failures),
        "failures": failures,
        "event_failures": event_failures,
    }


def import_statsbomb_open_data(
    *,
    project_root: Path = PROJECT_ROOT,
    offline_dir: Path | None = None,
    competition_id: int | None = None,
    season_id: int | None = None,
    limit_competitions: int | None = None,
    limit_matches: int | None = None,
    timeout: int = 30,
) -> dict:
    competitions = filter_competitions(
        load_competitions(offline_dir=offline_dir, timeout=timeout),
        competition_id=competition_id,
        season_id=season_id,
        limit_competitions=limit_competitions,
    )
    if not competitions:
        raise SystemExit("No StatsBomb competitions matched the requested filters.")

    records: list[dict] = []
    failures: list[str] = []
    event_failures: list[str] = []
    for competition in competitions:
        current_competition_id = int(competition.get("competition_id"))
        current_season_id = int(competition.get("season_id"))
        try:
            matches = load_matches(
                competition_id=current_competition_id,
                season_id=current_season_id,
                offline_dir=offline_dir,
                timeout=timeout,
            )
        except (HTTPError, URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
            failures.append(f"{current_competition_id}/{current_season_id}: {exc}")
            continue

        matches.sort(key=lambda item: (str(item.get("match_date") or ""), int(item.get("match_id") or 0)))
        if limit_matches is not None:
            matches = matches[: max(0, int(limit_matches))]

        for match in matches:
            match_id = int(match.get("match_id"))
            try:
                events = load_events(match_id=match_id, offline_dir=offline_dir, timeout=timeout)
            except (HTTPError, URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
                event_failures.append(f"{match_id}: {exc}")
                events = []
            records.append(convert_match(match, events))

    records.sort(key=lambda item: (str(item.get("match_date") or ""), str(item.get("match_id") or "")))
    if not records:
        raise SystemExit("No StatsBomb matches imported.")

    state_dir = project_root / "data" / "state"
    summaries_path = state_dir / "statsbomb_event_summaries.json"
    audit_path = state_dir / "statsbomb_import_audit.json"
    payload = {
        "updated_at": now_text(),
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "attribution": "Data source: StatsBomb",
        "items": records,
    }
    audit = build_audit(competitions=competitions, records=records, failures=failures, event_failures=event_failures)
    write_json(summaries_path, payload)
    write_json(audit_path, audit)
    return {
        "records": len(records),
        "total_events": audit["total_events"],
        "failure_count": audit["failure_count"],
        "summaries_path": str(summaries_path),
        "audit_path": str(audit_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import StatsBomb Open Data event summaries into local app state.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--offline-dir", type=Path, default=None, help="Optional directory containing StatsBomb data files.")
    parser.add_argument("--competition-id", type=int, default=None)
    parser.add_argument("--season-id", type=int, default=None)
    parser.add_argument("--limit-competitions", type=int, default=None)
    parser.add_argument("--limit-matches", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    result = import_statsbomb_open_data(
        project_root=args.project_root,
        offline_dir=args.offline_dir,
        competition_id=args.competition_id,
        season_id=args.season_id,
        limit_competitions=args.limit_competitions,
        limit_matches=args.limit_matches,
        timeout=max(1, int(args.timeout)),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
