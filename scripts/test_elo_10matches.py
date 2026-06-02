#!/usr/bin/env python3
"""Test ELO loading on 10 matches."""

from pathlib import Path
import json
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from c1.runtime.legacy_bridge import run_shadow_for_legacy_matches
from c1.data import load_elo_ratings

# Load sample matches
availability_file = project_root / "data" / "c1_state" / "availability_snapshots.json"
with open(availability_file, "r", encoding="utf-8") as f:
    data = json.load(f)

matches = []
seen_match_ids = set()
for key, item in data.get("items", {}).items():
    if key.startswith("exact|"):
        record = item.get("record", {})
        if record and "match_id" in record:
            match_id = record["match_id"]
            if match_id not in seen_match_ids:
                matches.append(record)
                seen_match_ids.add(match_id)
                if len(matches) >= 10:
                    break

print(f"Loaded {len(matches)} matches")
print()

# Load ELO ratings
elo_ratings = load_elo_ratings(project_root)
print(f"Loaded {len(elo_ratings)} ELO ratings")
print()

# Run shadow comparison
print("Running shadow comparison...")
try:
    results = run_shadow_for_legacy_matches(
        project_root=project_root,
        matches=matches,
        enable_xgboost=True,
        enable_lightgbm=False,
    )
    print(f"[OK] Completed for {len(results)} matches")
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 80)
print("VALIDATION RESULTS")
print("=" * 80)
print()

# Validate results
passed = 0
failed = 0

for i, result in enumerate(results, 1):
    feature_snapshot = result.feature_snapshot
    fields = feature_snapshot.fields if isinstance(feature_snapshot.fields, dict) else {}
    
    home_rating = fields.get("home_rating", 1500.0)
    away_rating = fields.get("away_rating", 1500.0)
    missing_elo_loss = fields.get("missing_elo_loss", 0.0)
    
    prediction = result.prediction_snapshot
    confidence = prediction.confidence if prediction else 0.0
    
    governance = result.governance_decision
    reason_codes = governance.reason_codes if governance else []
    
    # Validate
    home_ok = home_rating != 1500.0
    away_ok = away_rating != 1500.0
    elo_loss_ok = missing_elo_loss == 0.0
    no_elo_reason = "MISSING_ELO_LOSS" not in reason_codes
    
    match_valid = home_ok and away_ok and elo_loss_ok and no_elo_reason
    
    status = "[OK]" if match_valid else "[FAIL]"
    print(f"{i:2d}. {status} {result.match_id}")
    print(f"    home: {home_rating:7.2f} away: {away_rating:7.2f} conf: {confidence:.4f}")
    
    if match_valid:
        passed += 1
    else:
        failed += 1
        if not home_ok:
            print(f"    [!] home_rating is default (1500.0)")
        if not away_ok:
            print(f"    [!] away_rating is default (1500.0)")
        if not elo_loss_ok:
            print(f"    [!] missing_elo_loss is not 0.0")
        if not no_elo_reason:
            print(f"    [!] has MISSING_ELO_LOSS reason code")

print()
print("=" * 80)
print(f"SUMMARY: {passed} passed, {failed} failed out of {len(results)}")
print("=" * 80)

sys.exit(0 if failed == 0 else 1)
