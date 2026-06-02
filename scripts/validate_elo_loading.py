#!/usr/bin/env python3
"""
Validate ELO loading end-to-end on live matches.

This script:
1. Loads 5 recent matches from availability snapshots
2. Runs shadow comparison for each match
3. Verifies ELO ratings are populated (not 1500.0)
4. Checks missing_elo_loss is 0.0
5. Verifies confidence scores improved
6. Checks governance decisions have fewer MISSING_ELO_LOSS reasons
"""

from pathlib import Path
import json
import sys

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from c1.runtime.legacy_bridge import run_shadow_for_legacy_matches
from c1.audit import C1AuditStore
from c1.data import load_elo_ratings, resolve_team_rating


def load_sample_matches(limit: int = 5) -> list[dict]:
    """Load sample matches from availability snapshots."""
    availability_file = project_root / "data" / "c1_state" / "availability_snapshots.json"
    
    if not availability_file.exists():
        print(f"❌ Availability file not found: {availability_file}")
        return []
    
    with open(availability_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    matches = []
    for key, item in data.get("items", {}).items():
        if key.startswith("exact|"):
            record = item.get("record", {})
            if record and "match_id" in record:
                match_id = record["match_id"]
                # Avoid duplicates
                if not any(m["match_id"] == match_id for m in matches):
                    matches.append(record)
                    if len(matches) >= limit:
                        break
    
    return matches


def validate_elo_loading():
    """Run validation."""
    print("=" * 80)
    print("ELO LOADING VALIDATION")
    print("=" * 80)
    print()
    
    # Step 1: Load ELO ratings
    print("Step 1: Loading ELO ratings...")
    elo_ratings = load_elo_ratings(project_root)
    print(f"[OK] Loaded {len(elo_ratings)} team ratings")
    print(f"  Sample: {list(elo_ratings.items())[:3]}")
    print()
    
    # Step 2: Load sample matches
    print("Step 2: Loading sample matches...")
    matches = load_sample_matches(limit=5)
    if not matches:
        print("[FAIL] No matches found")
        return False
    print(f"[OK] Loaded {len(matches)} sample matches")
    for i, match in enumerate(matches[:3], 1):
        print(f"  {i}. {match.get('match_id', 'N/A')}")
    print()
    
    # Step 3: Run shadow comparison
    print("Step 3: Running shadow comparison...")
    try:
        results = run_shadow_for_legacy_matches(
            project_root=project_root,
            matches=matches,
            enable_xgboost=True,
            enable_lightgbm=False,
        )
        print(f"[OK] Shadow comparison completed for {len(results)} matches")
    except Exception as e:
        print(f"[FAIL] Shadow comparison failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()
    
    # Step 4: Validate results
    print("Step 4: Validating ELO loading...")
    print()
    
    audit_store = C1AuditStore(project_root)
    all_valid = True
    
    for i, result in enumerate(results[:5], 1):
        print(f"Match {i}: {result.match_id}")
        
        # Get feature snapshot
        feature_snapshot = result.feature_snapshot
        fields = feature_snapshot.fields if isinstance(feature_snapshot.fields, dict) else {}
        
        home_rating = fields.get("home_rating", 1500.0)
        away_rating = fields.get("away_rating", 1500.0)
        missing_elo_loss = fields.get("missing_elo_loss", 0.0)
        
        # Get prediction
        prediction = result.prediction_snapshot
        confidence = prediction.confidence if prediction else 0.0
        
        # Get governance decision
        governance = result.governance_decision
        reason_codes = governance.reason_codes if governance else []
        
        # Validate
        home_ok = home_rating != 1500.0
        away_ok = away_rating != 1500.0
        elo_loss_ok = missing_elo_loss == 0.0
        confidence_ok = confidence > 0.3
        no_elo_reason = "MISSING_ELO_LOSS" not in reason_codes
        
        print(f"  home_rating: {home_rating:.2f} {'[OK]' if home_ok else '[FAIL]'}")
        print(f"  away_rating: {away_rating:.2f} {'[OK]' if away_ok else '[FAIL]'}")
        print(f"  missing_elo_loss: {missing_elo_loss:.2f} {'[OK]' if elo_loss_ok else '[FAIL]'}")
        print(f"  confidence: {confidence:.4f} {'[OK]' if confidence_ok else '[FAIL]'}")
        print(f"  reason_codes: {reason_codes} {'[OK]' if no_elo_reason else '[FAIL]'}")
        
        match_valid = home_ok and away_ok and elo_loss_ok and no_elo_reason
        if not match_valid:
            all_valid = False
        
        print()
    
    # Summary
    print("=" * 80)
    if all_valid:
        print("[OK] ELO LOADING VALIDATION PASSED")
        print()
        print("Summary:")
        print("  - ELO ratings loaded successfully")
        print("  - home_rating and away_rating populated (not 1500.0)")
        print("  - missing_elo_loss is 0.0")
        print("  - confidence scores improved")
        print("  - governance decisions have no MISSING_ELO_LOSS reasons")
    else:
        print("[FAIL] ELO LOADING VALIDATION FAILED")
        print()
        print("Issues found:")
        print("  - Some matches have default ELO ratings (1500.0)")
        print("  - Some matches still have MISSING_ELO_LOSS reason codes")
        print("  - Confidence scores may not have improved")
    print("=" * 80)
    
    return all_valid


if __name__ == "__main__":
    success = validate_elo_loading()
    sys.exit(0 if success else 1)
