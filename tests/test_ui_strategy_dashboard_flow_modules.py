from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.ui_modules import (
    build_high_accuracy_strategy_dashboard,
    build_high_accuracy_strategy_pool_rows,
    build_high_accuracy_strategy_settlement_summary,
)


class UIStrategyDashboardFlowModuleTests(unittest.TestCase):
    def test_strategy_dashboard_summarizes_pool_and_settlements(self) -> None:
        status = {
            "enabled": True,
            "updated_at": "2026-05-09 17:24:22",
            "validation": {
                "record_count": 1200,
                "settlement_record_count": 40,
                "historical_record_count": 1160,
                "candidate_count": 12,
                "stable_candidate_count": 7,
                "date_start": "2024-01-01",
                "date_end": "2026-05-09",
            },
            "breaker": {"paused_count": 1, "threshold": 3, "window": 30},
            "strategy_pool": [
                {
                    "role": "primary",
                    "original_role": "primary",
                    "effective_role": "observe",
                    "scope": "league",
                    "scope_value": "La Liga",
                    "play_type": "market_1x2",
                    "layer": {"data_layer": "historical_market"},
                    "min_confidence": 0.7,
                    "sample_count": 100,
                    "hit_count": 80,
                    "accuracy": 0.8,
                    "coverage": 0.2,
                    "wilson_lower": 0.72,
                    "edge": 0.08,
                    "stability": {"stable": True, "stability_score": 0.81, "recent_30_accuracy": 0.83, "recent_90_accuracy": 0.79},
                    "breaker": {"breaker_on": True, "status": "paused", "miss_streak": 3, "threshold": 3, "hit_count": 0, "known_count": 3},
                },
                {
                    "role": "backup",
                    "scope": "global",
                    "scope_value": "all",
                    "play_type": "handicap",
                    "layer": {"data_layer": "app_settlement"},
                    "min_confidence": 0.75,
                    "sample_count": 40,
                    "hit_count": 23,
                    "accuracy": 0.575,
                    "coverage": 0.04,
                    "wilson_lower": 0.47,
                    "edge": -0.23,
                    "stability": {"stable": True, "stability_score": 0.67, "recent_30_accuracy": 0.56, "recent_90_accuracy": 0.57},
                    "breaker": {"breaker_on": False, "status": "active", "miss_streak": 0, "threshold": 3, "hit_count": 1, "known_count": 2},
                },
            ],
        }
        settlements = [
            {
                "league": "La Liga",
                "home_team": "A",
                "away_team": "B",
                "high_accuracy_strategy_items": [
                    {
                        "role": "primary",
                        "play_type": "market_1x2",
                        "pick": "home",
                        "actual": "home",
                        "confidence": 0.77,
                        "min_confidence": 0.7,
                        "backtest_accuracy": 0.8,
                        "backtest_samples": 100,
                        "is_hit": True,
                    }
                ],
            },
            {
                "league": "La Liga",
                "home_team": "C",
                "away_team": "D",
                "high_accuracy_strategy_items": [
                    {
                        "role": "backup",
                        "play_type": "handicap",
                        "pick": "home -0.5",
                        "actual": "away",
                        "confidence": 0.8,
                        "min_confidence": 0.75,
                        "backtest_accuracy": 0.575,
                        "backtest_samples": 40,
                        "is_hit": False,
                    }
                ],
            },
        ]

        dashboard = build_high_accuracy_strategy_dashboard(status, settlements)

        self.assertTrue(dashboard["enabled"])
        metrics = {item["label"]: item["value"] for item in dashboard["metrics"]}
        self.assertEqual(metrics["\u7b56\u7565\u6c60"], "2")
        self.assertEqual(metrics["\u7a33\u5b9a\u7b56\u7565"], "2/2")
        self.assertEqual(metrics["\u65ad\u8def\u6682\u505c"], "1")
        self.assertEqual(metrics["\u771f\u5b9e\u547d\u4e2d"], "50.0%")
        self.assertIn("APP 40", dashboard["validation_rows"][0][1])
        self.assertEqual(len(dashboard["pool_rows"]), 2)
        self.assertIn("\u89c2\u5bdf(\u539f\u4e3b\u7b56\u7565)", dashboard["pool_rows"][0]["title"])
        self.assertIn("\u65ad\u8def: ON", dashboard["pool_rows"][0]["body"])
        self.assertIn("\u56de\u6d4b: 80.0%", dashboard["pool_rows"][0]["body"])
        self.assertEqual(len(dashboard["settlement_rows"]), 2)
        self.assertIn("\u547d\u4e2d", dashboard["settlement_rows"][0]["title"])
        self.assertIn("\u65ad\u8def\u5668\u5df2\u89e6\u53d1", dashboard["guidance_rows"][0]["title"])

    def test_strategy_pool_rows_handle_missing_status(self) -> None:
        self.assertEqual(build_high_accuracy_strategy_pool_rows({}), [])
        dashboard = build_high_accuracy_strategy_dashboard({"enabled": False, "reason": "not_calibrated"}, [])
        self.assertFalse(dashboard["enabled"])
        self.assertEqual(dashboard["metrics"][0]["value"], "0")
        self.assertIn("\u672a\u542f\u7528", dashboard["guidance_rows"][0]["title"])

    def test_settlement_summary_ignores_unknown_results_for_hit_rate(self) -> None:
        summary = build_high_accuracy_strategy_settlement_summary(
            [
                {"high_accuracy_strategy_items": [{"is_hit": True}, {"is_hit": None}]},
                {"high_accuracy_strategy_items": [{"is_hit": False}]},
            ]
        )
        self.assertEqual(summary["active_count"], 3)
        self.assertEqual(summary["known_count"], 2)
        self.assertEqual(summary["summary_text"], "1/2")
        self.assertEqual(summary["hit_rate_text"], "50.0%")


if __name__ == "__main__":
    unittest.main()
