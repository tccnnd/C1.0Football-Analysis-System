from __future__ import annotations

import argparse
import csv
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

from v24_app.training_samples import import_historical_xgb_samples


DEFAULT_SEASONS = [
    "1415",
    "1516",
    "1617",
    "1718",
    "1819",
    "1920",
    "2021",
    "2122",
    "2223",
    "2324",
    "2425",
]
DEFAULT_LEAGUES = {
    "E0": "英超",
    "SP1": "西甲",
    "D1": "德甲",
    "I1": "意甲",
    "F1": "法甲",
}
LEAGUE_STRENGTH = {
    "E0": 1.00,
    "SP1": 0.98,
    "D1": 0.97,
    "I1": 0.96,
    "F1": 0.94,
}
SOURCE_TEMPLATE = "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"


def fetch_csv(url: str, timeout: int = 30) -> list[dict[str, str]]:
    with urlopen(url, timeout=timeout) as response:
        text = response.read().decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(text.splitlines()))


def safe_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def safe_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def convert_date(value: str, season: str) -> str:
    text = str(value or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            dt = datetime.strptime(text, fmt)
            if dt.year < 100:
                dt = dt.replace(year=dt.year + 2000)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue
    raise ValueError(f"Invalid date for {season}: {value!r}")


def first_float(row: dict[str, str], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = safe_float(row.get(key))
        if value is not None and value > 1.0:
            return value
    return None


def convert_row(raw: dict[str, str], season: str, league_code: str, league_name: str) -> dict | None:
    home_team = str(raw.get("HomeTeam") or "").strip()
    away_team = str(raw.get("AwayTeam") or "").strip()
    if not home_team or not away_team:
        return None
    home_goals = safe_int(raw.get("FTHG"))
    away_goals = safe_int(raw.get("FTAG"))
    if home_goals is None or away_goals is None:
        return None

    odds_home = first_float(raw, ("B365H", "AvgH", "MaxH", "PSH", "WHH"))
    odds_draw = first_float(raw, ("B365D", "AvgD", "MaxD", "PSD", "WHD"))
    odds_away = first_float(raw, ("B365A", "AvgA", "MaxA", "PSA", "WHA"))
    if odds_home is None or odds_draw is None or odds_away is None:
        return None

    opening_home = first_float(raw, ("B365H", "AvgH", "MaxH", "PSH")) or 0.0
    opening_draw = first_float(raw, ("B365D", "AvgD", "MaxD", "PSD")) or 0.0
    opening_away = first_float(raw, ("B365A", "AvgA", "MaxA", "PSA")) or 0.0
    closing_home = first_float(raw, ("B365CH", "AvgCH", "MaxCH", "PSCH")) or odds_home
    closing_draw = first_float(raw, ("B365CD", "AvgCD", "MaxCD", "PSCD")) or odds_draw
    closing_away = first_float(raw, ("B365CA", "AvgCA", "MaxCA", "PSCA")) or odds_away

    match_date = convert_date(str(raw.get("Date") or ""), season)
    match_time = str(raw.get("Time") or "00:00").strip() or "00:00"
    handicap_line = safe_float(raw.get("AHCh")) if safe_float(raw.get("AHCh")) is not None else safe_float(raw.get("AHh"))

    return {
        "match_id": f"football-data|{season}|{league_code}|{match_date}|{home_team}|{away_team}",
        "match_date": match_date,
        "match_time": match_time,
        "league": league_name,
        "home_team": home_team,
        "away_team": away_team,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "home_ht_goals": safe_int(raw.get("HTHG")),
        "away_ht_goals": safe_int(raw.get("HTAG")),
        "odds_home": closing_home,
        "odds_draw": closing_draw,
        "odds_away": closing_away,
        "opening_odds_home": opening_home,
        "opening_odds_draw": opening_draw,
        "opening_odds_away": opening_away,
        "handicap_line": handicap_line or 0.0,
        "league_strength": LEAGUE_STRENGTH.get(league_code, 0.92),
        "source": "football-data.co.uk",
        "season": season,
        "league_code": league_code,
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def hit_rate(hits: int, total: int) -> str:
    if total <= 0:
        return "-"
    return f"{hits / total:.1%}"


def build_league_profiles(records: list[dict]) -> dict:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for item in records:
        buckets[str(item.get("league") or "-")].append(item)
    profiles = {}
    for league, rows in sorted(buckets.items()):
        result_counts: Counter = Counter()
        under_count = 0
        total_goals = 0
        for row in rows:
            home_goals = int(row.get("home_goals", 0))
            away_goals = int(row.get("away_goals", 0))
            goals = home_goals + away_goals
            total_goals += goals
            under_count += 1 if goals < 3 else 0
            if home_goals > away_goals:
                result_counts["home"] += 1
            elif home_goals < away_goals:
                result_counts["away"] += 1
            else:
                result_counts["draw"] += 1
        total = len(rows)
        profiles[league] = {
            "matches": total,
            "home_win_rate": hit_rate(result_counts["home"], total),
            "draw_rate": hit_rate(result_counts["draw"], total),
            "away_win_rate": hit_rate(result_counts["away"], total),
            "under_2_5_rate": hit_rate(under_count, total),
            "avg_total_goals": round(total_goals / total, 3) if total else 0.0,
        }
    return {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "football-data.co.uk",
        "matches": len(records),
        "leagues": profiles,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import football-data.co.uk league history into local XGB samples.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--seasons", nargs="*", default=DEFAULT_SEASONS)
    parser.add_argument("--leagues", nargs="*", default=list(DEFAULT_LEAGUES.keys()))
    parser.add_argument("--replace", action="store_true", help="Replace existing xgb_training_samples.json.")
    parser.add_argument("--sync-ratings", action="store_true", help="Sync reconstructed club Elo ratings.")
    args = parser.parse_args()

    records: list[dict] = []
    failures: list[str] = []
    fetched_files = 0
    for season in args.seasons:
        for league_code in args.leagues:
            league_name = DEFAULT_LEAGUES.get(league_code, league_code)
            url = SOURCE_TEMPLATE.format(season=season, league=league_code)
            try:
                rows = fetch_csv(url)
                fetched_files += 1
            except (HTTPError, URLError, OSError) as exc:
                failures.append(f"{season}/{league_code}: {exc}")
                continue
            for row in rows:
                try:
                    converted = convert_row(row, season, league_code, league_name)
                except Exception:
                    converted = None
                if converted is not None:
                    records.append(converted)

    if not records:
        raise SystemExit("No football-data.co.uk records imported.")

    state_dir = args.project_root / "data" / "state"
    history_path = state_dir / "club_match_history.json"
    write_json(
        history_path,
        {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "football-data.co.uk",
            "source_url": "https://www.football-data.co.uk/data.php",
            "items": records,
            "failures": failures,
        },
    )
    write_json(state_dir / "league_profiles.json", build_league_profiles(records))
    imported = import_historical_xgb_samples(
        project_dir=args.project_root,
        input_path=history_path,
        replace=args.replace,
        sync_ratings=args.sync_ratings,
    )

    print(json.dumps(
        {
            "fetched_files": fetched_files,
            "records": len(records),
            "failures": failures,
            "history_path": str(history_path),
            "training_import": imported,
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
