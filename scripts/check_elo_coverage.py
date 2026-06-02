#!/usr/bin/env python3
import json
from pathlib import Path

# Load both ELO files
elo_file = Path("data/state/elo_ratings.json")
national_file = Path("data/state/national_team_elo_ratings.json")

elo_data = json.loads(elo_file.read_text(encoding="utf-8"))
national_data = json.loads(national_file.read_text(encoding="utf-8"))

elo_teams = set(elo_data.get("ratings", {}).keys())
national_teams = set(national_data.get("ratings", {}).keys())

print(f"Club ELO teams: {len(elo_teams)}")
print(f"National ELO teams: {len(national_teams)}")
print(f"Total ELO teams: {len(elo_teams | national_teams)}")
print()

# Load match data
match_file = Path("data/c1_state/availability_snapshots.json")
match_data = json.loads(match_file.read_text(encoding="utf-8"))

# Extract team names from matches
match_teams = set()
for key, item in match_data.get("items", {}).items():
    record = item.get("record", {})
    if record:
        home = record.get("home_team", "")
        away = record.get("away_team", "")
        if home:
            match_teams.add(home)
        if away:
            match_teams.add(away)

print(f"Match teams: {len(match_teams)}")
print()

# Find coverage
all_elo = elo_teams | national_teams
missing_in_elo = match_teams - all_elo
coverage = (len(match_teams) - len(missing_in_elo)) / len(match_teams) * 100

print(f"ELO coverage: {coverage:.1f}%")
print(f"Teams NOT in ELO: {len(missing_in_elo)}")
print()

# Show some missing teams
print("Sample missing teams:")
for team in sorted(missing_in_elo)[:20]:
    print(f"  - {team}")
