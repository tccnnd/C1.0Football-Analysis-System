from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app import core


class CorePlayThresholdBucketTuningTests(unittest.TestCase):
    def test_calibrate_play_thresholds_by_settlement_now(self) -> None:
        settlements: list[dict] = []
        for _ in range(20):
            settlements.append(
                {
                    "is_correct": False,
                    "prediction_confidence": 0.70,
                    "handicap_is_correct": True,
                    "handicap_confidence": 0.55,
                    "total_goals_is_correct": True,
                    "total_goals_confidence": 0.20,
                    "score_is_correct": False,
                    "score_confidence": 0.12,
                }
            )
        for _ in range(8):
            settlements[_]["is_correct"] = True

        current_thresholds = {
            "1x2": 0.56,
            "handicap": 0.56,
            "total_goals": 0.18,
            "score": 0.10,
            "htft": 0.18,
        }

        with (
            patch("v24_app.core.get_recent_settlements", return_value=settlements),
            patch("v24_app.core._current_play_thresholds", return_value=current_thresholds),
            patch("v24_app.core.get_play_threshold_status", return_value={"thresholds": current_thresholds}),
            patch("v24_app.core._save_play_threshold_report") as save_mock,
        ):
            result = core.calibrate_play_thresholds_by_settlement_now(
                write_report=False,
                min_samples=10,
                weak_ev_bias=-0.08,
                strong_ev_bias=0.08,
                step=0.02,
            )

        self.assertTrue(save_mock.called)
        self.assertTrue(result["calibrated"])
        self.assertGreater(float(result["thresholds"]["1x2"]), 0.56)
        self.assertLess(float(result["thresholds"]["handicap"]), 0.56)
        self.assertEqual(result["metrics"]["htft"]["reason"], "insufficient_samples")

    def test_calibrate_layered_filter_thresholds_now(self) -> None:
        settlements: list[dict] = []
        for _ in range(12):
            settlements.append(
                {
                    "league": "弱联赛",
                    "is_correct": False,
                    "prediction_confidence": 0.62,
                    "handicap_is_correct": True,
                    "handicap_confidence": 0.72,
                }
            )
        current_thresholds = {
            "1x2": 0.56,
            "handicap": 0.56,
            "total_goals": 0.18,
            "score": 0.10,
            "htft": 0.18,
        }

        with (
            patch("v24_app.core.get_recent_settlements", return_value=settlements),
            patch("v24_app.core._current_play_thresholds", return_value=current_thresholds),
            patch(
                "v24_app.core.get_play_threshold_status",
                return_value={
                    "updated_at": "now",
                    "mode": "bucket_tuned",
                    "thresholds": current_thresholds,
                    "metrics": {},
                    "validation": {},
                },
            ),
            patch("v24_app.core._save_play_threshold_report") as save_mock,
        ):
            result = core.calibrate_layered_filter_thresholds_now(min_samples=8)

        self.assertTrue(result["calibrated"])
        self.assertGreaterEqual(result["league_rule_count"], 1)
        weak_rule = result["layered_filter"]["league_play"]["弱联赛"]["1x2"]
        self.assertTrue(weak_rule["blocked"])
        self.assertGreater(float(weak_rule["min_threshold"]), 0.56)
        self.assertTrue(save_mock.called)

    def test_run_high_accuracy_strategy_backtest_selects_best_strategy(self) -> None:
        settlements: list[dict] = []
        for index in range(20):
            settlements.append(
                {
                    "match_id": f"2026-04-{index + 1:02d}|测试联赛|A|B",
                    "match_date": f"2026-04-{index + 1:02d}",
                    "league": "测试联赛",
                    "is_correct": index < 10,
                    "prediction_confidence": 0.55,
                    "handicap_is_correct": True,
                    "handicap_confidence": 0.72,
                    "total_goals_is_correct": index < 8,
                    "total_goals_confidence": 0.22,
                }
            )

        with (
            patch("v24_app.core.get_recent_settlements", return_value=settlements),
            patch("v24_app.core._xgb_market_strategy_records", return_value=[]),
            patch("v24_app.core._save_high_accuracy_strategy_report") as save_mock,
            patch("v24_app.core.get_high_accuracy_strategy_status", return_value={"enabled": True}),
        ):
            result = core.run_high_accuracy_strategy_backtest(
                min_samples=12,
                min_coverage=0.10,
                min_league_samples=12,
                write_report=False,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["strategy"]["play_type"], "handicap")
        self.assertGreaterEqual(float(result["strategy"]["accuracy"]), 0.99)
        self.assertTrue(save_mock.called)

    def test_settle_high_accuracy_strategy_results_marks_hits(self) -> None:
        result = core._settle_high_accuracy_strategy_results(
            {
                "high_accuracy_strategy": {
                    "enabled": True,
                    "active_matches": [
                        {
                            "role": "primary",
                            "play_type": "market_1x2",
                            "scope": "global",
                            "scope_value": "all",
                            "pick": "主胜",
                            "confidence": 0.72,
                            "min_confidence": 0.70,
                            "backtest_accuracy": 0.78,
                            "backtest_samples": 120,
                            "layer": {"data_layer": "historical_market"},
                        },
                        {
                            "role": "backup",
                            "play_type": "ou",
                            "scope": "global",
                            "scope_value": "all",
                            "pick": "小2.5",
                            "confidence": 0.54,
                            "min_confidence": 0.52,
                            "backtest_accuracy": 0.63,
                            "backtest_samples": 27,
                            "layer": {"data_layer": "app_settlement"},
                        },
                    ],
                }
            },
            result="主胜",
            total_goals=2,
            actual_score="1-1",
            handicap_result="-1 让负",
            ou_result="小2.5",
        )

        self.assertEqual(result["active_count"], 2)
        self.assertEqual(result["hit_count"], 2)
        self.assertEqual(result["summary"], "2/2")
        self.assertTrue(all(item["is_hit"] for item in result["items"]))


if __name__ == "__main__":
    unittest.main()
