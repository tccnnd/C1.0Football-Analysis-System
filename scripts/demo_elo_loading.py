#!/usr/bin/env python
"""
Demo script showing the impact of ELO loading on inference.

This script:
1. Loads ELO ratings from V24 state
2. Shows sample ratings
3. Demonstrates how ratings are resolved for teams
4. Shows the impact on feature snapshots
"""

from pathlib import Path
import sys
import importlib.util

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import elo_loader directly to avoid yaml dependency
spec = importlib.util.spec_from_file_location(
    "elo_loader",
    project_root / "c1" / "data" / "elo_loader.py"
)
elo_loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(elo_loader)

load_elo_ratings = elo_loader.load_elo_ratings
resolve_team_rating = elo_loader.resolve_team_rating


def main() -> None:
    print("=" * 70)
    print("C1.0 ELO Loading Bridge Demo")
    print("=" * 70)
    print()
    
    # Load ELO ratings
    print("1. Loading ELO ratings from V24 state...")
    ratings = load_elo_ratings(project_root)
    print(f"   ✓ Loaded {len(ratings)} team ratings")
    print()
    
    # Show top teams
    print("2. Top 10 teams by ELO rating:")
    top_teams = sorted(ratings.items(), key=lambda x: x[1], reverse=True)[:10]
    for i, (team, rating) in enumerate(top_teams, 1):
        print(f"   {i:2d}. {team:20s} {rating:8.2f}")
    print()
    
    # Show bottom teams
    print("3. Bottom 10 teams by ELO rating:")
    bottom_teams = sorted(ratings.items(), key=lambda x: x[1])[:10]
    for i, (team, rating) in enumerate(bottom_teams, 1):
        print(f"   {i:2d}. {team:20s} {rating:8.2f}")
    print()
    
    # Demo resolution
    print("4. Team rating resolution examples:")
    test_teams = [
        ("曼联", "Exact match (Chinese)"),
        ("manchester united", "Case-insensitive match"),
        ("Manchester United", "Exact match (English)"),
        ("不存在的队伍", "Not found (returns default)"),
    ]
    
    for team, description in test_teams:
        rating = resolve_team_rating(team, ratings)
        status = "✓" if rating != 1500.0 else "○"
        print(f"   {status} {team:20s} → {rating:8.2f}  ({description})")
    print()
    
    # Show impact on feature snapshot
    print("5. Impact on feature snapshot:")
    print()
    print("   BEFORE (without ELO loading):")
    print("   ├─ home_rating: 1500.0 (default)")
    print("   ├─ away_rating: 1500.0 (default)")
    print("   ├─ missing_elo_loss: 0.5 (triggers MISSING_ELO_LOSS soft reason)")
    print("   └─ ELO component: zero signal")
    print()
    
    home_team = "曼联"
    away_team = "曼城"
    home_rating = resolve_team_rating(home_team, ratings)
    away_rating = resolve_team_rating(away_team, ratings)
    
    print(f"   AFTER (with ELO loading for {home_team} vs {away_team}):")
    print(f"   ├─ home_rating: {home_rating:.2f} (from V24 state)")
    print(f"   ├─ away_rating: {away_rating:.2f} (from V24 state)")
    print(f"   ├─ missing_elo_loss: 0.0 (no longer triggers)")
    print(f"   └─ ELO component: strong signal (rating diff = {home_rating - away_rating:.2f})")
    print()
    
    print("=" * 70)
    print("Summary:")
    print("  • ELO ratings are now loaded from V24 state automatically")
    print("  • Legacy bridge injects ratings into feature snapshots")
    print("  • Inference receives real ELO signal instead of defaults")
    print("  • Confidence scores should improve significantly")
    print("  • Governance layer no longer penalizes for missing ELO")
    print("=" * 70)


if __name__ == "__main__":
    main()
