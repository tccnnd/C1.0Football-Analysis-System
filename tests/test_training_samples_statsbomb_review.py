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
    build_statsbomb_sandbox_fewshot_samples,
    export_statsbomb_review_training_samples,
    export_statsbomb_sandbox_fewshot_samples,
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


def _baseline() -> dict:
    return {
        "summary": {"match_count": 2, "finishing_variance_rate": "50.0%"},
        "items": [
            {
                "match_id": "statsbomb:1",
                "source_match_id": 1,
                "match_date": "2024-06-15",
                "league": "UEFA Euro",
                "season": "2024",
                "home_team": "Spain",
                "away_team": "Croatia",
                "score": "3-0",
                "score_winner": "home",
                "xg_winner": "away",
                "home_xg": 1.12,
                "away_xg": 2.35,
                "xg_margin": -1.23,
                "home_shots": 11,
                "away_shots": 16,
                "shot_margin": -5,
                "xg_aligned_with_score": False,
                "shot_aligned_with_score": False,
                "finishing_variance": True,
                "event_count": 3500,
            },
            {
                "match_id": "statsbomb:2",
                "source_match_id": 2,
                "match_date": "2024-06-16",
                "league": "UEFA Euro",
                "season": "2024",
                "home_team": "Germany",
                "away_team": "Scotland",
                "score": "5-1",
                "score_winner": "home",
                "xg_winner": "home",
                "home_xg": 2.8,
                "away_xg": 0.12,
                "xg_margin": 2.68,
                "home_shots": 19,
                "away_shots": 1,
                "shot_margin": 18,
                "xg_aligned_with_score": True,
                "shot_aligned_with_score": True,
                "finishing_variance": False,
                "event_count": 3600,
            },
        ],
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

    def test_builds_statsbomb_sandbox_fewshot_samples(self) -> None:
        samples, summary = build_statsbomb_sandbox_fewshot_samples(_baseline())

        self.assertEqual(summary["sample_count"], 2)
        self.assertEqual(summary["baseline_match_count"], 2)
        first = samples[0]
        self.assertEqual(first["labels"]["simulated_pick"], "AWAY")
        self.assertEqual(first["labels"]["actual"], "HOME")
        self.assertFalse(first["labels"]["is_hit"])
        self.assertIn("statsbomb_finishing_variance", first["labels"]["tags"])
        self.assertIn("Evaluation Agent", first["prompt"])
        self.assertIn("终结波动", first["completion"])
        self.assertIn("must not be used as pre-match", summary["leakage_note"])

    def test_export_writes_statsbomb_sandbox_fewshot_samples(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = export_statsbomb_sandbox_fewshot_samples(root, _baseline(), limit=1)
            payload = json.loads((root / "data" / "state" / "statsbomb_sandbox_fewshot_samples.json").read_text(encoding="utf-8"))

        self.assertEqual(result["sample_count"], 1)
        self.assertEqual(payload["purpose"], "evaluation_agent_fewshot_post_match_review")
        self.assertEqual(len(payload["items"]), 1)
        self.assertIn("post-match event data", payload["leakage_note"])


if __name__ == "__main__":
    unittest.main()
