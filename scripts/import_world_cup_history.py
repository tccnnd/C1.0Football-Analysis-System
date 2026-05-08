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

from v24_app.models.elo_rating import EloRatingEngine
from v24_app.storage.state_store import StateStore


YEARS = [
    1930,
    1934,
    1938,
    1950,
    1954,
    1958,
    1962,
    1966,
    1970,
    1974,
    1978,
    1982,
    1986,
    1990,
    1994,
    1998,
    2002,
    2006,
    2010,
    2014,
    2018,
    2022,
]
SOURCE_TEMPLATE = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/{year}/worldcup.json"


def fetch_json(url: str, timeout: int = 30) -> dict:
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_round(value: object) -> str:
    text = str(value or "").strip()
    lower = text.lower()
    if "matchday" in lower:
        return "group"
    if "group" in lower:
        return "group"
    if "round of 16" in lower or "quarter" in lower or "semi" in lower or "final" in lower or "third" in lower:
        return "knockout"
    return "unknown"


def result_label(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def iter_matches(payload: dict, year: int) -> list[dict]:
    rows: list[dict] = []
    for raw in payload.get("matches", []):
        if not isinstance(raw, dict):
            continue
        score = raw.get("score", {})
        ft = score.get("ft") if isinstance(score, dict) else None
        if not isinstance(ft, list) or len(ft) < 2:
            continue
        try:
            home_goals = int(ft[0])
            away_goals = int(ft[1])
        except Exception:
            continue
        row = {
            "year": year,
            "date": str(raw.get("date") or ""),
            "time": str(raw.get("time") or ""),
            "round": str(raw.get("round") or ""),
            "phase": normalize_round(raw.get("round")),
            "group": str(raw.get("group") or ""),
            "home_team": str(raw.get("team1") or ""),
            "away_team": str(raw.get("team2") or ""),
            "home_goals": home_goals,
            "away_goals": away_goals,
            "result": result_label(home_goals, away_goals),
            "total_goals": home_goals + away_goals,
            "ground": str(raw.get("ground") or ""),
        }
        if row["home_team"] and row["away_team"] and row["date"]:
            rows.append(row)
    return rows


def update_elo(rows: list[dict]) -> dict[str, float]:
    engine = EloRatingEngine(base_rating=1500.0, home_advantage=0.0, k_factor=26.0)
    ratings: dict[str, float] = {}
    for row in sorted(rows, key=lambda item: (item["date"], item["year"])):
        home = row["home_team"]
        away = row["away_team"]
        home_before = ratings.get(home, engine.base_rating)
        away_before = ratings.get(away, engine.base_rating)
        update = engine.update_from_result(
            home_rating=home_before,
            away_rating=away_before,
            home_goals=int(row["home_goals"]),
            away_goals=int(row["away_goals"]),
            league_strength=1.0,
        )
        ratings[home] = round(update.home_after, 4)
        ratings[away] = round(update.away_after, 4)
    return dict(sorted(ratings.items(), key=lambda item: item[0]))


def hit_rate_text(hits: int, total: int) -> str:
    if total <= 0:
        return "-"
    return f"{hits / total:.1%}"


def build_profile(rows: list[dict]) -> dict:
    phase_counts: dict[str, Counter] = defaultdict(Counter)
    phase_goal_totals: dict[str, list[int]] = defaultdict(list)
    year_counts: Counter = Counter()
    for row in rows:
        phase = row["phase"]
        phase_counts[phase][row["result"]] += 1
        phase_goal_totals[phase].append(int(row["total_goals"]))
        year_counts[int(row["year"])] += 1

    phases = {}
    for phase, counter in phase_counts.items():
        total = sum(counter.values())
        goals = phase_goal_totals[phase]
        phases[phase] = {
            "matches": total,
            "home_win_rate": hit_rate_text(counter["home"], total),
            "draw_rate": hit_rate_text(counter["draw"], total),
            "away_win_rate": hit_rate_text(counter["away"], total),
            "under_2_5_rate": hit_rate_text(sum(1 for value in goals if value < 3), len(goals)),
            "avg_total_goals": round(sum(goals) / len(goals), 3) if goals else 0.0,
        }

    return {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "openfootball/worldcup.json",
        "source_url": "https://github.com/openfootball/worldcup.json",
        "license": "CC0-1.0",
        "year_range": [min(year_counts), max(year_counts)] if year_counts else [],
        "matches": len(rows),
        "teams": len({row["home_team"] for row in rows} | {row["away_team"] for row in rows}),
        "phases": phases,
        "matches_by_year": dict(sorted(year_counts.items())),
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import historical FIFA World Cup matches into local app state.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--offline-dir", type=Path, default=None, help="Optional directory containing {year}/worldcup.json files.")
    args = parser.parse_args()

    all_rows: list[dict] = []
    failures: list[str] = []
    for year in YEARS:
        try:
            if args.offline_dir:
                payload = json.loads((args.offline_dir / str(year) / "worldcup.json").read_text(encoding="utf-8"))
            else:
                payload = fetch_json(SOURCE_TEMPLATE.format(year=year))
        except (HTTPError, URLError, OSError, json.JSONDecodeError) as exc:
            failures.append(f"{year}: {exc}")
            continue
        all_rows.extend(iter_matches(payload, year))

    if not all_rows:
        raise SystemExit("No World Cup matches imported.")

    state_dir = args.project_root / "data" / "state"
    state = StateStore(args.project_root)
    ratings = update_elo(all_rows)
    state.save_national_team_ratings(ratings)
    write_json(
        state_dir / "world_cup_history.json",
        {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "openfootball/worldcup.json",
            "source_url": "https://github.com/openfootball/worldcup.json",
            "license": "CC0-1.0",
            "items": all_rows,
            "failures": failures,
        },
    )
    write_json(state_dir / "world_cup_profile.json", build_profile(all_rows))

    print(f"Imported matches: {len(all_rows)}")
    print(f"Teams rated: {len(ratings)}")
    print(f"Failures: {len(failures)}")
    print(f"State dir: {state_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
