from __future__ import annotations

import csv
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
    build_statsbomb_review_label_queue,
    build_statsbomb_review_training_samples,
    build_statsbomb_sandbox_fewshot_samples,
    build_video_review_fewshot_samples,
    export_statsbomb_review_label_queue,
    export_statsbomb_review_training_samples,
    export_statsbomb_sandbox_fewshot_samples,
    export_video_review_fewshot_samples,
    update_statsbomb_review_label_queue_settlements,
)
from v24_app.core import backfill_statsbomb_review_settlement_labels
from v24_app.storage.state_store import StateStore


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


def _video_review() -> dict:
    return {
        "review_id": "vr-1",
        "match_id": "m-video",
        "match": {
            "match_date": "2026-05-14",
            "league": "Test League",
            "home_team": "Alpha",
            "away_team": "Bravo",
            "score": "1-0",
            "result": "主胜",
        },
        "visual_analysis": {
            "frame_count": 8,
            "usable_frame_count": 8,
        },
        "manual_annotations": [
            {
                "annotation_id": "ann-1",
                "event_type": "counter_attack",
                "event_label": "反击",
                "frame_index": 3,
                "timestamp_seconds": 75,
                "confidence": 0.81,
                "note": "fast break before the goal",
            }
        ],
        "agent_review": {
            "prediction_alignment": "needs_review",
            "evidence_level": "high",
            "evidence_score": 0.82,
            "review_confidence": 0.82,
            "key_frame_count": 4,
            "manual_annotation_count": 1,
            "recommended_followup": {"message": "feed manual video annotations"},
            "event_hypotheses": [
                {"code": "tempo_shift", "confidence": 0.76, "title": "tempo shifted"},
            ],
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

    def test_export_writes_review_label_queue_for_unlabeled_settlement(self) -> None:
        unlabeled = _settlement().copy()
        unlabeled.pop("is_correct")
        unlabeled.pop("handicap_is_correct")
        unlabeled.pop("ou_is_correct")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = export_statsbomb_review_label_queue(root, [unlabeled])
            payload = json.loads((root / "data" / "state" / "statsbomb_review_label_queue.json").read_text(encoding="utf-8"))
            with (root / "data" / "state" / "statsbomb_review_label_queue.csv").open("r", encoding="utf-8-sig", newline="") as fh:
                rows = list(csv.DictReader(fh))

        self.assertEqual(result["queue_count"], 1)
        self.assertEqual(payload["purpose"], "post_match_review_label_annotation_queue")
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(rows[0]["match_id"], "m1")
        self.assertEqual(rows[0]["missing_label_fields"], "is_correct,handicap_is_correct,ou_is_correct")
        self.assertEqual(rows[0]["annotation_status"], "pending")

    def test_builds_review_label_queue_with_partial_status_and_notes(self) -> None:
        partial = _settlement().copy()
        partial.pop("is_correct")
        partial["handicap_is_correct"] = True
        partial["statsbomb_review_notes"] = "needs review"

        rows, summary = build_statsbomb_review_label_queue([partial])

        self.assertEqual(summary["queue_count"], 1)
        self.assertEqual(rows[0]["annotation_status"], "partial")
        self.assertEqual(rows[0]["notes"], "needs review")

    def test_update_review_label_queue_backfills_settlement_and_closes_queue(self) -> None:
        settlement = _settlement().copy()
        settlement.pop("is_correct")
        settlement.pop("handicap_is_correct")
        settlement.pop("ou_is_correct")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = StateStore(root)
            store.save_settlements([settlement])

            update_result = update_statsbomb_review_label_queue_settlements(
                root,
                [
                    {
                        "match_id": "m1",
                        "is_correct": True,
                        "handicap_is_correct": False,
                        "ou_is_correct": True,
                        "notes": "manual backfill",
                    }
                ],
            )
            saved_settlements = store.load_settlements()
            rows, queue_summary = build_statsbomb_review_label_queue(saved_settlements)
            samples, sample_summary = build_statsbomb_review_training_samples(saved_settlements)

        self.assertEqual(update_result["updated_count"], 1)
        self.assertEqual(update_result["updated_match_ids"], ["m1"])
        self.assertEqual(saved_settlements[0]["annotation_status"], "labeled")
        self.assertTrue(saved_settlements[0]["is_correct"])
        self.assertFalse(saved_settlements[0]["handicap_is_correct"])
        self.assertTrue(saved_settlements[0]["ou_is_correct"])
        self.assertEqual(saved_settlements[0]["statsbomb_review_notes"], "manual backfill")
        self.assertEqual(queue_summary["queue_count"], 0)
        self.assertEqual(rows, [])
        self.assertEqual(sample_summary["sample_count"], 1)
        self.assertEqual(len(samples), 1)

    def test_backfill_statsbomb_review_settlement_labels_generates_training_samples(self) -> None:
        settlement = _settlement().copy()
        settlement.pop("is_correct")
        settlement.pop("handicap_is_correct")
        settlement.pop("ou_is_correct")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = StateStore(root)
            store.save_settlements([settlement])

            result = backfill_statsbomb_review_settlement_labels(
                root,
                predictor=lambda match: {
                    "recommendation": "主胜",
                    "confidence": 0.78,
                    "handicap_recommendation": "让胜",
                    "handicap_display": "+0 让胜",
                    "handicap_confidence": 0.61,
                    "ou_recommendation": "大2.5",
                    "ou_confidence": 0.66,
                },
                settlements=[settlement],
            )

            saved_settlements = store.load_settlements()
            rows, queue_summary = build_statsbomb_review_label_queue(saved_settlements)
            samples, sample_summary = build_statsbomb_review_training_samples(saved_settlements)

        self.assertEqual(result["updated_count"], 1)
        self.assertEqual(result["ok"], True)
        self.assertEqual(saved_settlements[0]["predicted"], "主胜")
        self.assertTrue(saved_settlements[0]["is_correct"])
        self.assertTrue(saved_settlements[0]["handicap_is_correct"])
        self.assertTrue(saved_settlements[0]["ou_is_correct"])
        self.assertEqual(saved_settlements[0]["statsbomb_review_label_source"], "current_model_backfill")
        self.assertEqual(queue_summary["queue_count"], 0)
        self.assertEqual(rows, [])
        self.assertEqual(sample_summary["sample_count"], 1)
        self.assertEqual(len(samples), 1)

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

    def test_builds_video_review_fewshot_samples_from_annotations(self) -> None:
        samples, summary = build_video_review_fewshot_samples([_video_review()])

        self.assertEqual(summary["sample_count"], 1)
        self.assertEqual(summary["manual_annotation_sample_count"], 1)
        sample = samples[0]
        self.assertEqual(sample["review_status"], "draft")
        self.assertIn("Evaluation Agent", sample["prompt"])
        self.assertIn("video_post_match_review", sample["labels"]["tags"])
        self.assertIn("video_manual_annotation", sample["labels"]["tags"])
        self.assertIn("video_margin_risk", sample["labels"]["tags"])
        self.assertEqual(sample["labels"]["root_cause"], "video_margin_risk")
        self.assertEqual(sample["features"]["frame_index"], 3.0)
        self.assertEqual(sample["meta"]["annotation_id"], "ann-1")
        self.assertIn("post-match video evidence", summary["leakage_note"])

    def test_export_writes_video_review_fewshot_samples(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = export_video_review_fewshot_samples(root, [_video_review()], limit=5)
            payload = json.loads((root / "data" / "state" / "video_review_fewshot_samples.json").read_text(encoding="utf-8"))

        self.assertEqual(result["sample_count"], 1)
        self.assertEqual(payload["purpose"], "evaluation_agent_video_fewshot_post_match_review")
        self.assertEqual(len(payload["items"]), 1)
        self.assertIn("post-match video evidence", payload["leakage_note"])


if __name__ == "__main__":
    unittest.main()
