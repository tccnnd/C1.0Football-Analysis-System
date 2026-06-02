#!/usr/bin/env python3
import json
from pathlib import Path

# Check club_match_history.json
match_file = Path("data/state/club_match_history.json")
if match_file.exists():
    data = json.load(open(match_file, encoding="utf-8"))
    matches = data.get("matches", [])
    print(f"club_match_history.json: {len(matches)} matches")
    if matches:
        print(f"  Sample: {matches[0]}")
else:
    print("club_match_history.json not found")

print()

# Check prediction_snapshots.json
pred_file = Path("data/state/prediction_snapshots.json")
if pred_file.exists():
    data = json.load(open(pred_file, encoding="utf-8"))
    snapshots = data.get("snapshots", [])
    print(f"prediction_snapshots.json: {len(snapshots)} snapshots")
else:
    print("prediction_snapshots.json not found")

print()

# Check settlements.json
settle_file = Path("data/state/settlements.json")
if settle_file.exists():
    data = json.load(open(settle_file, encoding="utf-8"))
    settlements = data.get("settlements", [])
    print(f"settlements.json: {len(settlements)} settlements")
else:
    print("settlements.json not found")
