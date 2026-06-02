"""
Train XGBoost with xG Features

Retrains XGBoost model with 15 additional xG features from Understat data.
Expected improvement: 75% → 78-80% hit rate at high confidence.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _bootstrap() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    src_dir = base_dir / "src"
    os.chdir(base_dir)
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train XGBoost with xG features for improved accuracy."
    )
    parser.add_argument(
        "--force-min-samples",
        type=int,
        default=None,
        help="Override minimum sample threshold for one-shot training.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show xG feature statistics without training.",
    )
    args = parser.parse_args()

    _bootstrap()

    from v24_app.features.xg_features import get_xg_database

    # Load xG database
    print("Loading xG database...")
    xg_db = get_xg_database()
    print(f"✓ Loaded {xg_db.team_count} teams, {xg_db.total_records} match records")

    if args.dry_run:
        print("\n=== xG Database Summary ===")
        print(f"Teams: {xg_db.team_count}")
        print(f"Total records: {xg_db.total_records}")
        print("\nSample xG features for a match:")
        features = xg_db.build_match_xg_features(
            home_team="曼城",
            away_team="利物浦",
            match_date="2024-01-01",
        )
        for key, value in features.items():
            print(f"  {key}: {value}")
        return

    # Train XGBoost with xG features
    print("\nTraining XGBoost with xG features...")
    from v24_app.core import get_xgb_training_status, train_xgb_with_xg_features

    before = get_xgb_training_status()
    result = train_xgb_with_xg_features(force_min_samples=args.force_min_samples)
    after = get_xgb_training_status()

    output = {
        "before": before,
        "result": result,
        "after": after,
        "xg_stats": {
            "teams": xg_db.team_count,
            "records": xg_db.total_records,
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
