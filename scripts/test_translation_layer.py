#!/usr/bin/env python3
"""
Test the complete translation layer with all 5 play types.
"""

from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from c1.translation import C1TranslationEngine, build_translation_request
from c1.core.schema import FeatureSnapshot, GovernanceDecision
from c1.inference.schema import InferenceResult
from c1.core.reason_codes import DecisionAction


def create_test_feature_snapshot():
    """Create a test feature snapshot."""
    return FeatureSnapshot(
        match_id="test_match_001",
        feature_version="c1.phase5",
        fields={
            "home_rating": 1650.0,
            "away_rating": 1500.0,
            "handicap_line": 0.5,
            "total_goals_line": 2.5,
            "missing_elo_loss": 0.0,
            "info_quality": 0.85,
        },
    )


def create_test_inference_result():
    """Create a test inference result."""
    return InferenceResult(
        match_id="test_match_001",
        model_name="baseline_ensemble",
        raw_probabilities={"home": 0.55, "draw": 0.30, "away": 0.15},
        predicted_side="home",
        confidence=0.70,
        margin=0.25,
        entropy=0.95,
        ev_by_side={"home": 0.15, "draw": -0.05, "away": -0.20},
        components=[],
        metadata={"expected_goals": 2.8},
    )


def create_test_governance_decision():
    """Create a test governance decision."""
    return GovernanceDecision(
        match_id="test_match_001",
        action=DecisionAction.APPROVE,
        allow_output=True,
        shadow_mode=False,
        reasons=[],
        gate_results=[],
        governance_version="c1.phase5",
        reason_codes=[],
    )


def test_translation_engine():
    """Test the translation engine with all 5 play types."""
    print("=" * 80)
    print("TRANSLATION LAYER TEST")
    print("=" * 80)
    print()
    
    # Create test data
    feature_snapshot = create_test_feature_snapshot()
    inference_result = create_test_inference_result()
    governance_decision = create_test_governance_decision()
    
    # Build translation request
    request = build_translation_request(
        match_id="test_match_001",
        feature_snapshot=feature_snapshot,
        inference_result=inference_result,
        governance_decision=governance_decision,
    )
    
    # Create translation engine
    engine = C1TranslationEngine()
    
    # Translate
    print("Translating match...")
    result = engine.translate(request)
    
    print(f"Match ID: {result.match_id}")
    print(f"Governance Action: {result.governance_action}")
    print(f"Translator Version: {result.translator_version}")
    print()
    
    # Check results
    print("Translation Results:")
    print("-" * 80)
    
    play_types = {}
    for item in result.items:
        play_types[item.play] = item
        status = "[OK]" if item.selection else "[NO SELECTION]"
        print(f"{item.play:12} {status:20} selection={item.selection}")
    
    print()
    print("=" * 80)
    print("VALIDATION")
    print("=" * 80)
    print()
    
    # Validate all 5 play types are present
    expected_plays = ["1x2", "handicap", "totals", "htft", "scoreline"]
    all_present = all(play in play_types for play in expected_plays)
    
    print(f"All 5 play types present: {'[OK]' if all_present else '[FAIL]'}")
    for play in expected_plays:
        status = "[OK]" if play in play_types else "[MISSING]"
        print(f"  {play:12} {status}")
    
    print()
    
    # Validate each play type
    print("Play Type Details:")
    print("-" * 80)
    
    all_valid = True
    for play in expected_plays:
        if play not in play_types:
            print(f"{play}: [MISSING]")
            all_valid = False
            continue
        
        item = play_types[play]
        
        # Check required fields
        has_play = item.play == play
        has_status = item.status in ["ACTIVE", "DOWNGRADED", "SHADOW", "BLOCKED"]
        has_confidence = 0.0 <= item.confidence <= 1.0
        has_rationale = len(item.rationale) > 0
        has_evidence = len(item.evidence) > 0
        
        valid = has_play and has_status and has_confidence and has_rationale and has_evidence
        status = "[OK]" if valid else "[FAIL]"
        
        print(f"{play:12} {status}")
        print(f"  status: {item.status}")
        print(f"  selection: {item.selection}")
        print(f"  confidence: {item.confidence:.4f}")
        print(f"  rationale: {', '.join(item.rationale[:2])}")
        print(f"  evidence keys: {', '.join(list(item.evidence.keys())[:3])}")
        print()
        
        if not valid:
            all_valid = False
    
    print("=" * 80)
    if all_valid and all_present:
        print("[OK] TRANSLATION LAYER TEST PASSED")
        print()
        print("Summary:")
        print("  - All 5 play types translated successfully")
        print("  - All items have required fields")
        print("  - All items have valid confidence scores")
        print("  - All items have rationale and evidence")
    else:
        print("[FAIL] TRANSLATION LAYER TEST FAILED")
        print()
        print("Issues:")
        if not all_present:
            print("  - Not all play types present")
        if not all_valid:
            print("  - Some play types missing required fields")
    print("=" * 80)
    
    return all_valid and all_present


if __name__ == "__main__":
    success = test_translation_engine()
    sys.exit(0 if success else 1)
