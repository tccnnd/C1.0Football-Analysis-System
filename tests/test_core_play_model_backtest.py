from __future__ import annotations

import sys
import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app import core


class PlayModelBacktestTests(unittest.TestCase):
    def tearDown(self) -> None:
        core._PLAY_MODEL_POLICY_CACHE.clear()
        core._PLAY_MODEL_POLICY_CACHE.update({"mtime": None, "policy": None, "report": {}})
        core._DRAW_RELEASE_GUARD_POLICY_CACHE.clear()
        core._DRAW_RELEASE_GUARD_POLICY_CACHE.update(
            {
                "mtime": None,
                "policy": json.loads(json.dumps(core.DEFAULT_DRAW_RELEASE_GUARD_POLICY)),
                "report": {},
            }
        )

    def test_run_play_model_backtest_truncates_large_validation_set(self) -> None:
        validation_items = [
            {
                "meta": {
                    "match_date": f"2025-01-{(index % 28) + 1:02d}",
                    "home_goals": 2,
                    "away_goals": 1,
                    "handicap_line": 0.0,
                }
            }
            for index in range(12)
        ]
        prediction = {
            "handicap_recommendation": "主胜",
            "total_goals_value": 3,
            "score_recommendation": "2-1",
            "poisson": {
                "score_distribution": [{"score": "2-1", "probability": 1.0}],
                "top_total_goals": [{"goals": 3, "probability": 1.0}],
                "top_scores": [{"score": "2-1", "probability": 1.0}],
            },
            "total_goals_model": {"model_ready": True, "label": 3, "confidence": 0.9},
            "scoreline_model": {"model_ready": True, "label": "2-1", "confidence": 0.9},
            "volatile_scoreline_model": {"model_ready": True, "label": "3-2", "confidence": 0.3},
        }

        with patch("v24_app.core._validation_split_samples", return_value=([], validation_items)):
            with patch("v24_app.core._sample_item_prediction", return_value=prediction):
                with patch.object(core.STATE_STORE, "load_xgb_samples", return_value=validation_items):
                    result = core.run_play_model_backtest(max_validation_samples=5, write_report=False)

        self.assertTrue(result["ok"])
        self.assertEqual(result["validation"]["sample_count"], 5)
        self.assertEqual(result["validation"]["original_sample_count"], 12)
        self.assertEqual(result["validation"]["max_validation_samples"], 5)
        self.assertTrue(result["validation"]["truncated"])
        self.assertAlmostEqual(result["validation"]["ratio"], 5 / 12, places=4)

    def test_run_draw_specialist_backtest_tracks_precision_recall_and_buckets(self) -> None:
        validation_items = [
            {
                "match_id": f"draw-{index}",
                "features": {"odds_draw": 3.1 + index * 0.05},
                "meta": {
                    "match_date": f"2025-01-{index + 1:02d}",
                    "league": "Draw League",
                    "home_team": f"H{index}",
                    "away_team": f"A{index}",
                    "home_goals": 1 if index != 2 else 2,
                    "away_goals": 1 if index != 2 else 1,
                    "handicap_line": 0.0,
                },
            }
            for index in range(4)
        ]
        predictions = [
            {
                "recommendation": "平局",
                "draw_score": 0.74,
                "draw_takeover": True,
                "draw_grade": "博平",
                "probabilities": {"home": 0.32, "draw": 0.34, "away": 0.34},
                "draw_signals": {"market_balance": 0.9},
                "expected_goals": 2.1,
            },
            {
                "recommendation": "主胜",
                "draw_score": 0.64,
                "draw_takeover": False,
                "draw_grade": "防平",
                "probabilities": {"home": 0.40, "draw": 0.30, "away": 0.30},
                "draw_signals": {"market_balance": 0.8},
                "expected_goals": 2.3,
            },
            {
                "recommendation": "平局",
                "draw_score": 0.76,
                "draw_takeover": True,
                "draw_grade": "博平",
                "probabilities": {"home": 0.31, "draw": 0.35, "away": 0.34},
                "draw_signals": {"market_balance": 0.85},
                "expected_goals": 2.2,
            },
            {
                "recommendation": "客胜",
                "draw_score": 0.42,
                "draw_takeover": False,
                "draw_grade": "不防平",
                "probabilities": {"home": 0.26, "draw": 0.24, "away": 0.50},
                "draw_signals": {"market_balance": 0.3},
                "expected_goals": 3.1,
            },
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            report_file = Path(tmp_dir) / "draw_specialist_backtest_v1.json"
            with patch.object(core, "DRAW_SPECIALIST_BACKTEST_FILE", report_file):
                with patch("v24_app.core._validation_split_samples", return_value=([], validation_items)):
                    with patch("v24_app.core._sample_item_prediction", side_effect=predictions):
                        with patch.object(core.STATE_STORE, "load_xgb_samples", return_value=validation_items):
                            result = core.run_draw_specialist_backtest(max_validation_samples=10, write_report=False)
                status = core.get_draw_specialist_backtest_status()

        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["sample_count"], 4)
        self.assertEqual(result["summary"]["actual_draw_count"], 3)
        self.assertEqual(result["summary"]["predicted_draw_count"], 2)
        self.assertEqual(result["summary"]["draw_hit_count"], 1)
        self.assertEqual(result["summary"]["precision_text"], "50.0%")
        self.assertEqual(result["summary"]["recall_text"], "33.3%")
        self.assertEqual(result["summary"]["missed_draw_count"], 2)
        self.assertEqual(result["summary"]["false_positive_count"], 1)
        self.assertTrue(result["score_buckets"])
        self.assertEqual(status["summary"]["sample_count"], 4)

    def test_draw_takeover_guard_blocks_high_score_in_weak_low_odds_bucket(self) -> None:
        match = core.AppMatch(
            home_team="H",
            away_team="A",
            league="Draw League",
            match_time="20:00",
            match_date="2026-05-11",
            odds_home=2.45,
            odds_draw=2.95,
            odds_away=2.80,
        )

        takeover, guard = core._draw_takeover_decision(
            match,
            probabilities={"home": 0.35, "draw": 0.34, "away": 0.31},
            draw_score=0.76,
            draw_signals={"market_balance": 0.9, "low_goal": 0.8},
        )

        self.assertFalse(takeover)
        self.assertTrue(guard["base_takeover"])
        self.assertTrue(guard["blocked"])
        self.assertEqual(guard["reason"], "weak_draw_odds_bucket")
        self.assertEqual(guard["odds_bucket"], "<=3.00")
        self.assertEqual(guard["evidence"]["precision"], 0.222222)

    def test_draw_takeover_guard_allows_high_score_in_supported_odds_bucket(self) -> None:
        match = core.AppMatch(
            home_team="H",
            away_team="A",
            league="Draw League",
            match_time="20:00",
            match_date="2026-05-11",
            odds_home=2.45,
            odds_draw=3.20,
            odds_away=2.80,
        )

        takeover, guard = core._draw_takeover_decision(
            match,
            probabilities={"home": 0.35, "draw": 0.34, "away": 0.31},
            draw_score=0.76,
            draw_signals={"market_balance": 0.9, "low_goal": 0.8},
        )

        self.assertTrue(takeover)
        self.assertFalse(guard["blocked"])
        self.assertEqual(guard["odds_bucket"], "3.01-3.30")

    def test_draw_takeover_guard_blocks_high_score_in_weak_long_odds_bucket(self) -> None:
        match = core.AppMatch(
            home_team="H",
            away_team="A",
            league="Draw League",
            match_time="20:00",
            match_date="2026-05-11",
            odds_home=1.80,
            odds_draw=4.35,
            odds_away=4.60,
        )

        takeover, guard = core._draw_takeover_decision(
            match,
            probabilities={"home": 0.38, "draw": 0.31, "away": 0.31},
            draw_score=0.72,
            draw_signals={"market_balance": 0.9, "low_goal": 0.8},
        )

        self.assertFalse(takeover)
        self.assertTrue(guard["base_takeover"])
        self.assertTrue(guard["blocked"])
        self.assertEqual(guard["odds_bucket"], ">4.20")
        self.assertLess(guard["evidence"]["lift"], 0)

    def test_draw_takeover_guard_does_not_mark_blocked_without_base_takeover(self) -> None:
        match = core.AppMatch(
            home_team="H",
            away_team="A",
            league="Draw League",
            match_time="20:00",
            match_date="2026-05-11",
            odds_home=1.55,
            odds_draw=4.35,
            odds_away=6.00,
        )

        takeover, guard = core._draw_takeover_decision(
            match,
            probabilities={"home": 0.63, "draw": 0.20, "away": 0.17},
            draw_score=0.72,
            draw_signals={"market_balance": 0.3, "low_goal": 0.8},
        )

        self.assertFalse(takeover)
        self.assertFalse(guard["base_takeover"])
        self.assertTrue(guard["weak_score"])
        self.assertFalse(guard["blocked"])
        self.assertEqual(guard["reason"], "ok")

    def test_draw_takeover_guard_reads_policy_file_threshold_and_evidence(self) -> None:
        match = core.AppMatch(
            home_team="H",
            away_team="A",
            league="Draw League",
            match_time="20:00",
            match_date="2026-05-11",
            odds_home=2.45,
            odds_draw=2.95,
            odds_away=2.80,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            policy_file = Path(tmp_dir) / "draw_release_guard_policy_v1.json"
            policy_file.write_text(
                json.dumps(
                    {
                        "policy": {
                            "enabled": True,
                            "min_score": 0.80,
                            "weak_odds_buckets": {
                                "<=3.00": {
                                    "precision": 0.111111,
                                    "draw_rate": 0.12,
                                    "lift": -0.10,
                                    "source": "unit_policy",
                                }
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(core, "DRAW_RELEASE_GUARD_POLICY_FILE", policy_file):
                takeover, guard = core._draw_takeover_decision(
                    match,
                    probabilities={"home": 0.35, "draw": 0.34, "away": 0.31},
                    draw_score=0.76,
                    draw_signals={"market_balance": 0.9, "low_goal": 0.8},
                )
                self.assertTrue(takeover)
                self.assertFalse(guard["weak_score"])
                self.assertEqual(guard["min_score"], 0.80)

                takeover, guard = core._draw_takeover_decision(
                    match,
                    probabilities={"home": 0.35, "draw": 0.34, "away": 0.31},
                    draw_score=0.82,
                    draw_signals={"market_balance": 0.9, "low_goal": 0.8},
                )

        self.assertFalse(takeover)
        self.assertTrue(guard["blocked"])
        self.assertEqual(guard["evidence"]["precision"], 0.111111)
        self.assertEqual(guard["evidence"]["source"], "unit_policy")

    def test_total_goals_takeover_requires_material_calibration_uplift(self) -> None:
        validation_items = []
        for index in range(100):
            actual_total = 2 if index < 50 else 3
            model_total = actual_total if index < 52 else 2
            validation_items.append(
                {
                    "meta": {
                        "match_date": f"2025-02-{(index % 28) + 1:02d}",
                        "home_goals": actual_total,
                        "away_goals": 0,
                    },
                    "prediction": {
                        "recommendation": "涓昏儨",
                        "pre_play_model_total_goals_value": 2,
                        "pre_play_model_total_goals_confidence": 0.30,
                        "pre_play_model_score_recommendation": "2-0",
                        "pre_play_model_score_confidence": 0.20,
                        "poisson": {
                            "score_distribution": [{"score": f"{model_total}-0", "probability": 0.9}],
                            "top_total_goals": [{"goals": 2, "probability": 0.30}],
                        },
                        "total_goals_model": {"model_ready": True, "label": model_total, "confidence": 0.9},
                        "scoreline_model": {"model_ready": False},
                        "volatile_scoreline_model": {"model_ready": False},
                    },
                }
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            policy_file = Path(tmp_dir) / "play_model_policy_v1.json"
            history_file = Path(tmp_dir) / "play_model_policy_history_v1.json"
            with patch.object(core, "PLAY_MODEL_POLICY_FILE", policy_file):
                with patch.object(core, "PLAY_MODEL_POLICY_HISTORY_FILE", history_file):
                    with patch("v24_app.core._validation_split_samples", return_value=([], validation_items)):
                        with patch("v24_app.core._sample_item_prediction", side_effect=lambda item: item["prediction"]):
                            with patch.object(core.STATE_STORE, "load_xgb_samples", return_value=validation_items):
                                result = core.calibrate_play_model_policy_now(max_validation_samples=None)

        total_goals_metrics = result["metrics"]["total_goals"]
        self.assertTrue(result["calibrated"])
        self.assertTrue(total_goals_metrics["best"]["takeover_enabled"])
        self.assertEqual(total_goals_metrics["current_accuracy"], 0.5)
        self.assertEqual(total_goals_metrics["best"]["accuracy"], 0.52)
        self.assertEqual(total_goals_metrics["reason"], "insufficient_calibration_uplift")
        self.assertFalse(result["policy"]["total_goals"]["takeover_enabled"])

    def test_total_goals_takeover_requires_holdout_stability(self) -> None:
        validation_items = []
        for index in range(200):
            if index < 100:
                actual_total = 2 if index < 50 else 3
                model_total = actual_total if index < 90 else 2
            else:
                actual_total = 2
                model_total = 3
            validation_items.append(
                {
                    "meta": {
                        "match_date": f"2025-03-{(index % 28) + 1:02d}",
                        "home_goals": actual_total,
                        "away_goals": 0,
                    },
                    "prediction": {
                        "pre_play_model_total_goals_value": 2,
                        "pre_play_model_total_goals_confidence": 0.30,
                        "pre_play_model_score_recommendation": "2-0",
                        "pre_play_model_score_confidence": 0.20,
                        "poisson": {
                            "score_distribution": [{"score": f"{model_total}-0", "probability": 0.9}],
                            "top_total_goals": [{"goals": 2, "probability": 0.30}],
                        },
                        "total_goals_model": {"model_ready": True, "label": model_total, "confidence": 0.9},
                        "scoreline_model": {"model_ready": False},
                        "volatile_scoreline_model": {"model_ready": False},
                    },
                }
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            policy_file = Path(tmp_dir) / "play_model_policy_v1.json"
            history_file = Path(tmp_dir) / "play_model_policy_history_v1.json"
            with patch.object(core, "PLAY_MODEL_POLICY_FILE", policy_file):
                with patch.object(core, "PLAY_MODEL_POLICY_HISTORY_FILE", history_file):
                    with patch("v24_app.core._validation_split_samples", return_value=([], validation_items)):
                        with patch("v24_app.core._sample_item_prediction", side_effect=lambda item: item["prediction"]):
                            with patch.object(core.STATE_STORE, "load_xgb_samples", return_value=validation_items):
                                result = core.calibrate_play_model_policy_now(max_validation_samples=None)

        total_goals_metrics = result["metrics"]["total_goals"]
        holdout_metrics = result["metrics"]["holdout"]
        self.assertTrue(result["calibrated"])
        self.assertEqual(result["validation"]["tuning_sample_count"], 100)
        self.assertEqual(result["validation"]["holdout_sample_count"], 100)
        self.assertTrue(total_goals_metrics["best"]["takeover_enabled"])
        self.assertGreater(total_goals_metrics["uplift"], core.PLAY_MODEL_TOTAL_GOALS_MIN_CALIBRATION_UPLIFT)
        self.assertEqual(total_goals_metrics["reason"], "holdout_regression")
        self.assertLess(holdout_metrics["total_goals_uplift"], 0)
        self.assertFalse(result["policy"]["total_goals"]["takeover_enabled"])

    def test_calibrate_play_model_policy_records_version_history(self) -> None:
        validation_items = []
        for index in range(40):
            validation_items.append(
                {
                    "meta": {
                        "match_date": f"2025-04-{(index % 28) + 1:02d}",
                        "home_goals": 2,
                        "away_goals": 0,
                    },
                    "prediction": {
                        "pre_play_model_total_goals_value": 2,
                        "pre_play_model_total_goals_confidence": 0.30,
                        "pre_play_model_score_recommendation": "2-0",
                        "pre_play_model_score_confidence": 0.20,
                        "poisson": {
                            "score_distribution": [{"score": "2-0", "probability": 0.9}],
                            "top_total_goals": [{"goals": 2, "probability": 0.30}],
                        },
                        "total_goals_model": {"model_ready": True, "label": 2, "confidence": 0.9},
                        "scoreline_model": {"model_ready": True, "label": "2-0", "confidence": 0.9},
                        "volatile_scoreline_model": {"model_ready": False},
                    },
                }
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            policy_file = Path(tmp_dir) / "play_model_policy_v1.json"
            history_file = Path(tmp_dir) / "play_model_policy_history_v1.json"
            policy_file.write_text(
                '{"updated_at":"2026-01-01 00:00:00","policy":{"total_goals":{"takeover_enabled":false,"min_confidence":0.24},"scoreline":{"takeover_enabled":true}}}',
                encoding="utf-8",
            )
            with patch.object(core, "PLAY_MODEL_POLICY_FILE", policy_file):
                with patch.object(core, "PLAY_MODEL_POLICY_HISTORY_FILE", history_file):
                    with patch("v24_app.core._validation_split_samples", return_value=([], validation_items)):
                        with patch("v24_app.core._sample_item_prediction", side_effect=lambda item: item["prediction"]):
                            with patch.object(core.STATE_STORE, "load_xgb_samples", return_value=validation_items):
                                result = core.calibrate_play_model_policy_now(max_validation_samples=None)
                    history = core.get_play_model_policy_history(limit=5)
                    status = core.get_play_model_policy_status()

        self.assertTrue(result["calibrated"])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["version_id"], result["version_id"])
        self.assertEqual(history[0]["source"], "calibration")
        self.assertEqual(history[0]["previous_updated_at"], "2026-01-01 00:00:00")
        self.assertIn("total_goals_reason", history[0]["summary"])
        self.assertEqual(status["version_id"], result["version_id"])
        self.assertTrue(str(status["history_source"]).endswith("play_model_policy_history_v1.json"))


if __name__ == "__main__":
    unittest.main()
