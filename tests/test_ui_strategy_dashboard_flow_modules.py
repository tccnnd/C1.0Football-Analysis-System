from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.core import AppMatch
from v24_app.ui_modules import (
    build_high_accuracy_strategy_dashboard,
    build_high_accuracy_strategy_pool_rows,
    build_high_accuracy_strategy_settlement_summary,
    build_strategy_allowlist_filename,
    build_strategy_allowlist_report_lines,
    build_strategy_allowlist_settlement_rows,
    build_strategy_allowlist_settlement_summary,
    select_strategy_allowlist_rows,
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

    def test_strategy_allowlist_report_keeps_only_formal_release_rows(self) -> None:
        match_a = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="21:00",
            match_date="2026-05-09",
            odds_home=1.8,
            odds_draw=3.2,
            odds_away=4.0,
            source="live",
            source_id="a1",
        )
        match_b = AppMatch(
            home_team="C",
            away_team="D",
            league="L2",
            match_time="19:30",
            match_date="2026-05-09",
            odds_home=2.0,
            odds_draw=3.1,
            odds_away=3.8,
            source="live",
            source_id="b1",
        )
        match_c = AppMatch(
            home_team="E",
            away_team="F",
            league="L3",
            match_time="18:00",
            match_date="2026-05-09",
            odds_home=2.1,
            odds_draw=3.0,
            odds_away=3.5,
            source="live",
            source_id="c1",
        )
        rows = [
            {
                "match": match_a,
                "prediction": {
                    "recommendation": "home",
                    "confidence": 0.72,
                    "risk_level": "LOW",
                    "strategy_admission": {
                        "decision": "allow",
                        "label": "\u6b63\u5f0f\u653e\u884c",
                        "action": "release",
                        "active_count": 2,
                        "shadow_count": 1,
                        "single_play_count": 1,
                        "top_play": "market_1x2",
                        "top_pick": "home",
                        "top_confidence": 0.76,
                        "summary": "primary strategy passed",
                        "reasons": ["primary_pass", "low_risk"],
                    },
                },
            },
            {
                "match": match_c,
                "prediction": {
                    "recommendation": "away",
                    "confidence": 0.81,
                    "risk_level": "HIGH",
                    "strategy_admission": {"decision": "block", "label": "\u963b\u65ad"},
                },
            },
            {
                "match": match_b,
                "prediction": {
                    "recommendation": "draw",
                    "confidence": 0.68,
                    "risk_level": "MEDIUM",
                    "strategy_admission": {
                        "decision": "allow",
                        "label": "\u6b63\u5f0f\u653e\u884c",
                        "action": "release",
                        "active_count": 1,
                        "shadow_count": 0,
                        "single_play_count": 1,
                        "top_play": "handicap",
                        "top_pick": "draw",
                        "top_confidence": 0.69,
                        "reasons": ["backup_pass"],
                    },
                },
            },
        ]

        selected = select_strategy_allowlist_rows(rows)
        self.assertEqual([item["match"].home_team for item in selected], ["C", "A"])

        lines = build_strategy_allowlist_report_lines(rows, generated_at=datetime(2026, 5, 9, 17, 30, 45))
        payload = "\n".join(lines)
        self.assertIn("# \u7b56\u7565\u653e\u884c\u6e05\u5355", payload)
        self.assertIn("\u6b63\u5f0f\u653e\u884c\u573a\u6b21: 2", payload)
        self.assertIn("C vs D", payload)
        self.assertIn("A vs B", payload)
        self.assertNotIn("E vs F", payload)
        self.assertIn("\u8d5b\u524d\u590d\u6838\u6e05\u5355", payload)
        self.assertIn("\u786e\u8ba4\u9996\u53d1", payload)

    def test_strategy_allowlist_filename_is_timestamped(self) -> None:
        self.assertEqual(
            build_strategy_allowlist_filename(datetime(2026, 5, 9, 17, 30, 45)),
            "strategy_allowlist_20260509_173045.md",
        )

    def test_strategy_allowlist_settlement_summary_tracks_release_quality(self) -> None:
        settlements = [
            {
                "strategy_allowlist_decision": "allow",
                "strategy_allowlist_file": "strategy_allowlist_a.md",
                "strategy_allowlist_exported_at": "2026-05-09 17:30:45",
                "match_date": "2026-05-09",
                "league": "L1",
                "home_team": "A",
                "away_team": "B",
                "home_goals": 2,
                "away_goals": 1,
                "predicted": "home",
                "is_correct": True,
                "prediction_confidence": 0.72,
                "handicap_is_correct": True,
                "ou_is_correct": False,
                "predicted_handicap": "home -0.5",
                "predicted_ou": "over",
                "high_accuracy_strategy_active_count": 2,
                "high_accuracy_strategy_hit_count": 2,
                "high_accuracy_strategy_summary": "2/2",
            },
            {
                "strategy_allowlist_decision": "allow",
                "strategy_allowlist_file": "strategy_allowlist_a.md",
                "strategy_allowlist_exported_at": "2026-05-09 17:30:45",
                "match_date": "2026-05-10",
                "league": "L2",
                "home_team": "C",
                "away_team": "D",
                "home_goals": 0,
                "away_goals": 1,
                "predicted": "home",
                "is_correct": False,
                "prediction_confidence": 0.68,
                "handicap_is_correct": False,
                "ou_is_correct": True,
                "predicted_handicap": "home -0.25",
                "predicted_ou": "under",
                "high_accuracy_strategy_active_count": 1,
                "high_accuracy_strategy_hit_count": 0,
                "high_accuracy_strategy_summary": "0/1",
                "high_accuracy_strategy_shadow_count": 1,
            },
            {"strategy_allowlist_decision": "", "is_correct": False},
        ]

        summary = build_strategy_allowlist_settlement_summary(settlements)

        self.assertEqual(summary["settled_count"], 2)
        self.assertEqual(summary["known_count"], 2)
        self.assertEqual(summary["hit_rate_text"], "50.0%")
        self.assertEqual(summary["high_strategy_summary"], "2/3")
        self.assertEqual(summary["high_conf_misses"], 1)
        self.assertEqual(summary["shadow_observed_count"], 1)
        self.assertIn("1X2", summary["top_failure"])

        rows = build_strategy_allowlist_settlement_rows(settlements)
        self.assertEqual(len(rows), 2)
        self.assertIn("\u547d\u4e2d", rows[0]["title"])
        self.assertIn("strategy_allowlist_a.md", rows[0]["body"])
        self.assertIn("\u9ad8\u7f6e\u4fe1\u5931\u8bef", rows[1]["body"])


if __name__ == "__main__":
    unittest.main()
