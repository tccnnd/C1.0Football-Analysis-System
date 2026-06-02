#!/usr/bin/env python3
import json
from pathlib import Path

# Load ELO ratings
elo_file = Path("data/state/elo_ratings.json")
elo_data = json.loads(elo_file.read_text(encoding="utf-8"))
elo_teams = set(elo_data.get("ratings", {}).keys())

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

print(f"ELO teams: {len(elo_teams)}")
print(f"Match teams: {len(match_teams)}")
print()

# Find mismatches
missing_in_elo = match_teams - elo_teams
print(f"Teams in matches but NOT in ELO: {len(missing_in_elo)}")
for team in sorted(missing_in_elo)[:20]:
    print(f"  - {team}")
print()

# Check for similar names
print("Checking for similar names...")
for match_team in sorted(missing_in_elo)[:10]:
    for elo_team in elo_teams:
        if match_team.lower() in elo_team.lower() or elo_team.lower() in match_team.lower():
            print(f"  Match: '{match_team}' <-> ELO: '{elo_team}'")
