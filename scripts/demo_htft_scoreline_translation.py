#!/usr/bin/env python
"""
Demo script for HT/FT and Scoreline Translation

Tests the new translation modules without requiring yaml module.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Direct imports to avoid yaml dependency
from c1.translation.htft_translator import (
    estimate_ht_probabilities,
    generate_htft_outcomes,
    translate_htft,
)
from c1.translation.scoreline_translator import (
    estimate_expected_goals as estimate_xg,
    filter_score_matrix,
    generate_score_matrix,
    translate_scoreline,
)


def demo_htft_translation():
    """Demo HT/FT translation."""
    print("=" * 70)
    print("HT/FT Translation Demo")
    print("=" * 70)
    
    # Example match: Man United (1756.25) vs Man City (1871.46)
    raw_probs = {"home": 0.30, "draw": 0.25, "away": 0.45}
    confidence = 0.65
    home_rating = 1756.25
    away_rating = 1871.46
    
    print(f"\n1. Input Data:")
    print(f"   FT Probabilities: {raw_probs}")
    print(f"   Model Confidence: {confidence}")
    print(f"   Home Rating: {home_rating}")
    print(f"   Away Rating: {away_rating}")
    
    # Estimate HT probabilities
    ht_probs = estimate_ht_probabilities(
        raw_probs["home"], raw_probs["away"], raw_probs["draw"]
    )
    print(f"\n2. Estimated HT Probabilities:")
    for side, prob in ht_probs.items():
        print(f"   {side.upper()}: {prob:.4f}")
    
    # Generate HT/FT outcomes
    outcomes = generate_htft_outcomes(ht_probs, raw_probs)
    print(f"\n3. HT/FT Outcomes (top 5):")
    sorted_outcomes = sorted(outcomes.items(), key=lambda x: x[1], reverse=True)
    for outcome, prob in sorted_outcomes[:5]:
        print(f"   {outcome}: {prob:.4f}")
    
    # Translate to HT/FT item
    item = translate_htft(
        raw_probabilities=raw_probs,
        confidence=confidence,
        governance_status="ACTIVE",
        home_rating=home_rating,
        away_rating=away_rating,
    )
    
    print(f"\n4. Translation Result:")
    print(f"   Play Type: {item.play}")
    print(f"   Status: {item.status}")
    print(f"   Selection: {item.selection}")
    print(f"   Confidence: {item.confidence}")
    print(f"   Rationale: {item.rationale}")
    print(f"   Tags: {item.tags}")


def demo_scoreline_translation():
    """Demo scoreline translation."""
    print("\n" + "=" * 70)
    print("Scoreline Translation Demo")
    print("=" * 70)
    
    # Example match: Man United (1756.25) vs Man City (1871.46)
    raw_probs = {"home": 0.30, "draw": 0.25, "away": 0.45}
    confidence = 0.65
    home_rating = 1756.25
    away_rating = 1871.46
    
    print(f"\n1. Input Data:")
    print(f"   FT Probabilities: {raw_probs}")
    print(f"   Model Confidence: {confidence}")
    print(f"   Home Rating: {home_rating}")
    print(f"   Away Rating: {away_rating}")
    
    # Estimate expected goals
    home_xg, away_xg = estimate_xg(
        raw_probs["home"], raw_probs["away"], raw_probs["draw"],
        home_rating, away_rating
    )
    print(f"\n2. Estimated Expected Goals:")
    print(f"   Home xG: {home_xg:.4f}")
    print(f"   Away xG: {away_xg:.4f}")
    
    # Generate score matrix
    matrix = generate_score_matrix(home_xg, away_xg, max_goals=5)
    print(f"\n3. Score Matrix Size: {len(matrix)} outcomes")
    
    # Filter score matrix
    filtered = filter_score_matrix(matrix, min_probability=0.02, max_outcomes=10)
    print(f"\n4. Filtered Score Matrix (top 5):")
    sorted_scores = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
    for score, prob in sorted_scores[:5]:
        print(f"   {score[0]}-{score[1]}: {prob:.4f}")
    
    # Translate to scoreline item
    item = translate_scoreline(
        raw_probabilities=raw_probs,
        confidence=confidence,
        governance_status="ACTIVE",
        home_rating=home_rating,
        away_rating=away_rating,
    )
    
    print(f"\n5. Translation Result:")
    print(f"   Play Type: {item.play}")
    print(f"   Status: {item.status}")
    print(f"   Selection: {item.selection}")
    print(f"   Confidence: {item.confidence}")
    print(f"   Rationale: {item.rationale}")
    print(f"   Tags: {item.tags}")


def demo_edge_cases():
    """Demo edge cases."""
    print("\n" + "=" * 70)
    print("Edge Cases Demo")
    print("=" * 70)
    
    # Case 1: Very strong home team
    print(f"\n1. Very Strong Home Team (90% win probability):")
    item = translate_htft(
        raw_probabilities={"home": 0.90, "draw": 0.05, "away": 0.05},
        confidence=0.85,
        governance_status="ACTIVE",
    )
    print(f"   Selection: {item.selection}")
    print(f"   Rationale: {item.rationale}")
    
    # Case 2: Low confidence
    print(f"\n2. Low Model Confidence (0.20):")
    item = translate_htft(
        raw_probabilities={"home": 0.40, "draw": 0.30, "away": 0.30},
        confidence=0.20,
        governance_status="ACTIVE",
        config={"min_confidence": 0.35},
    )
    print(f"   Selection: {item.selection}")
    print(f"   Rationale: {item.rationale}")
    
    # Case 3: Blocked governance
    print(f"\n3. Blocked Governance Status:")
    item = translate_scoreline(
        raw_probabilities={"home": 0.40, "draw": 0.30, "away": 0.30},
        confidence=0.65,
        governance_status="BLOCKED",
    )
    print(f"   Selection: {item.selection}")
    print(f"   Status: {item.status}")
    print(f"   Rationale: {item.rationale}")


def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  C1.0 HT/FT and Scoreline Translation Demo".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    
    try:
        demo_htft_translation()
        demo_scoreline_translation()
        demo_edge_cases()
        
        print("\n" + "=" * 70)
        print("✓ All demos completed successfully!")
        print("=" * 70)
        print("\nSummary:")
        print("  • HT/FT translation: Generates 9 outcomes from FT probabilities")
        print("  • Scoreline translation: Generates score matrix using Poisson")
        print("  • Both support governance status filtering")
        print("  • Both include confidence thresholds and evidence tracking")
        print("\n")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
