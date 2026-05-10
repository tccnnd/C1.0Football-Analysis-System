from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.training_samples import (
    STATSBOMB_REVIEW_FEATURE_ORDER,
    build_statsbomb_review_training_samples,
    export_statsbomb_review_training_samples,
)


def _settlement() -> dict:
    return {
        "match_id": "m1",
        "timestamp": "2024-04-14 17:30",
        "match_date": "2024-04-14",
        "match_time": "17:30",
        "league": "1. Bundesliga",
        "home_team": "Bayer Leverkusen",
        "away_team": "Werder Bremen",
        "home_goals": 5,
        "away_goals": 0,
        "is_correct": False,
        "handicap_is_correct": True,
        "ou_is_correct": False,
        "prediction_confidence": 0.72,
        "market_entropy_score": 0.31,
        "handicap_margin_score": 0.44,
        "statsbomb_source_match_id": 3895302,
        "high_accuracy_strategy_items": [{"is_hit": False}, {"is_hit": True}],
        "statsbomb_event_summary": {
            "event_count": 4223,
            "first_goal_minute": 25,
            "last_goal_minute": 89,
            "team_stats": {
                "Bayer Leverkusen": {
                    "xg": 4.02,
                    "shots": 19,
                    "shots_on_target": 11,
                    "passes": 640,
                    "carries": 520,
                    "pressures": 140,
                    "fouls_committed": 8,
                    "yellow_cards": 1,
                    "red_cards": 0,
                },
                "Werder Bremen": {
                    "xg": 0.28,
                    "shots": 8,
                    "shots_on_target": 2,
                    "passes": 390,
                    "carries": 310,
                    "pressures": 210,
                    "fouls_committed": 14,
                    "yellow_cards": 3,
                    "red_cards": 1,
                },
            },
        },
    }


class StatsBombReviewTrainingSamplesTests(unittest.TestCase):
    def test_builds_review_training_sample_without_pre_match_feature_leakage(self) -> None:
        samples, summary = build_statsbomb_review_training_samples([_settlement(), {"match_id": "missing"}])

        self.assertEqual(summary["sample_count"], 1)
        self.assertEqual(summary["skipped_missing_statsbomb"], 1)
        sample = samples[0]
        features = sample["features"]
        self.assertEqual(set(features), set(STATSBOMB_REVIEW_FEATURE_ORDER))
        self.assertEqual(sample["labels"]["prediction_miss"], 1)
        self.assertEqual(sample["labels"]["handicap_miss"], 0)
        self.assertEqual(sample["labels"]["ou_miss"], 1)
        self.assertAlmostEqual(features["xg_diff"], 3.74)
        self.assertEqual(features["shot_diff"], 11.0)
        self.assertEqual(features["high_strategy_count"], 2.0)
        self.assertEqual(features["high_strategy_miss_count"], 1.0)
        self.assertEqual(sample["meta"]["statsbomb_source_match_id"], 3895302)

    def test_export_writes_review_training_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = export_statsbomb_review_training_samples(root, [_settlement()])
            payload = json.loads((root / "data" / "state" / "statsbomb_review_training_samples.json").read_text(encoding="utf-8"))

        self.assertEqual(result["sample_count"], 1)
        self.assertEqual(payload["purpose"], "post_match_review_error_attribution")
        self.assertIn("must not be used as pre-match", payload["leakage_note"])
        self.assertEqual(len(payload["items"]), 1)


if __name__ == "__main__":
    unittest.main()
