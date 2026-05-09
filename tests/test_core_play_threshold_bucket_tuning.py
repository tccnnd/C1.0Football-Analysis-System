from __future__ import annotations

import json
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

    def test_run_jc_stratified_strategy_backtest_ranks_stable_bucket(self) -> None:
        records: list[dict] = []
        for index in range(30):
            records.append(
                {
                    "match_id": f"jc-good-{index}",
                    "match_date": f"2026-01-{(index % 28) + 1:02d}",
                    "year": "2026",
                    "league": "Stable League",
                    "play_type": "market_1x2",
                    "pick_side": "home",
                    "confidence": 0.62,
                    "confidence_bucket": "0.60-0.65",
                    "pick_odds": 1.62,
                    "odds_bucket": "1.51-1.80",
                    "is_hit": index < 24,
                    "sample_source": "jc_results_csv",
                }
            )
        for index in range(30):
            records.append(
                {
                    "match_id": f"jc-bad-{index}",
                    "match_date": f"2026-02-{(index % 28) + 1:02d}",
                    "year": "2026",
                    "league": "Weak League",
                    "play_type": "market_1x2",
                    "pick_side": "away",
                    "confidence": 0.40,
                    "confidence_bucket": "0.38-0.42",
                    "pick_odds": 2.9,
                    "odds_bucket": "2.81-3.50",
                    "is_hit": index < 10,
                    "sample_source": "jc_results_csv",
                }
            )
        records.append({**records[0], "match_id": "other-source", "sample_source": "historical_import"})

        with (
            patch("v24_app.core._xgb_market_strategy_records", return_value=records),
            patch("v24_app.core._save_jc_stratified_strategy_report") as save_mock,
            patch("v24_app.core._write_jc_stratified_strategy_report", return_value="reports/jc.md") as write_mock,
        ):
            result = core.run_jc_stratified_strategy_backtest(min_samples=10)

        self.assertTrue(result["ok"])
        self.assertEqual(result["validation"]["record_count"], 60)
        self.assertEqual(result["validation"]["source_counts"]["jc_results_csv"], 60)
        self.assertEqual(result["best_bucket"]["dimension"], "league")
        self.assertEqual(result["best_bucket"]["bucket"], "Stable League")
        self.assertGreater(float(result["best_bucket"]["accuracy"]), 0.75)
        self.assertTrue(save_mock.called)
        self.assertTrue(write_mock.called)

    def test_high_accuracy_strategy_breaker_pauses_consecutive_misses(self) -> None:
        strategy = {
            "role": "primary",
            "scope": "global",
            "scope_value": "all",
            "play_type": "market_1x2",
            "min_confidence": 0.70,
            "layer": {"data_layer": "historical_market"},
        }
        settlements = [
            {
                "high_accuracy_strategy_items": [
                    {
                        "scope": "global",
                        "scope_value": "all",
                        "play_type": "market_1x2",
                        "min_confidence": 0.70,
                        "data_layer": "historical_market",
                        "is_hit": False,
                    }
                ]
            }
            for _ in range(3)
        ]

        status = core._apply_high_accuracy_strategy_breakers(
            {"enabled": True, "strategy": strategy, "strategy_pool": [strategy]},
            settlements,
        )

        item = status["strategy_pool"][0]
        self.assertTrue(item["breaker"]["breaker_on"])
        self.assertEqual(item["breaker"]["miss_streak"], 3)
        self.assertEqual(item["breaker"]["status"], "paused")
        self.assertEqual(item["effective_role"], "observe")
        self.assertEqual(status["breaker"]["paused_count"], 1)

    def test_high_accuracy_strategy_breaker_requires_recovery_hits(self) -> None:
        strategy = {
            "role": "primary",
            "scope": "global",
            "scope_value": "all",
            "play_type": "market_1x2",
            "min_confidence": 0.70,
            "layer": {"data_layer": "historical_market"},
        }
        misses = [
            {
                "high_accuracy_strategy_items": [
                    {
                        "scope": "global",
                        "scope_value": "all",
                        "play_type": "market_1x2",
                        "min_confidence": 0.70,
                        "data_layer": "historical_market",
                        "is_hit": False,
                        "is_shadow": True,
                    }
                ]
            }
            for _ in range(3)
        ]
        one_recovery_hit = {
            "high_accuracy_strategy_items": [
                {
                    "scope": "global",
                    "scope_value": "all",
                    "play_type": "market_1x2",
                    "min_confidence": 0.70,
                    "data_layer": "historical_market",
                    "is_hit": True,
                    "is_shadow": True,
                }
            ]
        }

        recovering = core._apply_high_accuracy_strategy_breakers(
            {"enabled": True, "strategy": strategy, "strategy_pool": [strategy]},
            misses + [one_recovery_hit],
        )
        recovered = core._apply_high_accuracy_strategy_breakers(
            {"enabled": True, "strategy": strategy, "strategy_pool": [strategy]},
            misses + [one_recovery_hit, one_recovery_hit],
        )

        self.assertTrue(recovering["strategy_pool"][0]["breaker"]["breaker_on"])
        self.assertEqual(recovering["strategy_pool"][0]["breaker"]["status"], "recovering")
        self.assertEqual(recovering["strategy_pool"][0]["breaker"]["recovery_streak"], 1)
        self.assertFalse(recovered["strategy_pool"][0]["breaker"]["breaker_on"])
        self.assertEqual(recovered["strategy_pool"][0]["breaker"]["status"], "recovered")
        self.assertEqual(recovered["strategy_pool"][0]["effective_role"], "primary")

    def test_high_accuracy_strategy_match_respects_breaker(self) -> None:
        strategy = {
            "role": "primary",
            "effective_role": "observe",
            "original_role": "primary",
            "scope": "global",
            "scope_value": "all",
            "play_type": "market_1x2",
            "min_confidence": 0.70,
            "accuracy": 0.80,
            "hit_count": 80,
            "sample_count": 100,
            "breaker": {"breaker_on": True, "miss_streak": 3, "threshold": 3},
        }
        match = core.AppMatch(
            home_team="A",
            away_team="B",
            league="Test League",
            match_time="12:00",
            match_date="2026-05-09",
            odds_home=1.8,
            odds_draw=3.2,
            odds_away=4.2,
        )

        with patch(
            "v24_app.core.get_high_accuracy_strategy_status",
            return_value={"enabled": True, "updated_at": "now", "strategy": strategy, "strategy_pool": [strategy]},
        ):
            result = core._high_accuracy_strategy_match(
                match,
                {"market_probabilities": {"home": 0.80, "draw": 0.10, "away": 0.10}},
                {},
            )

        self.assertFalse(result["active"])
        self.assertEqual(result["reason"], "strategy_breaker_observing")
        self.assertEqual(result["role"], "observe")
        self.assertEqual(result["active_count"], 0)
        self.assertEqual(result["shadow_count"], 1)
        self.assertTrue(result["shadow_matches"][0]["shadow_active"])

    def test_high_accuracy_market_strategy_uses_market_probabilities(self) -> None:
        strategy = {
            "role": "primary",
            "scope": "global",
            "scope_value": "all",
            "play_type": "market_1x2",
            "min_confidence": 0.70,
            "accuracy": 0.80,
            "hit_count": 80,
            "sample_count": 100,
            "breaker": {"breaker_on": False},
        }
        match = core.AppMatch(
            home_team="A",
            away_team="B",
            league="Test League",
            match_time="12:00",
            match_date="2026-05-09",
            odds_home=1.8,
            odds_draw=3.2,
            odds_away=4.2,
        )

        with patch(
            "v24_app.core.get_high_accuracy_strategy_status",
            return_value={"enabled": True, "updated_at": "now", "strategy": strategy, "strategy_pool": [strategy]},
        ):
            result = core._high_accuracy_strategy_match(
                match,
                {"market_probabilities": {"home": 0.80, "draw": 0.10, "away": 0.10}},
                {},
            )

        self.assertTrue(result["active"])
        self.assertEqual(result["active_count"], 1)
        self.assertEqual(result["active_matches"][0]["play_type"], "market_1x2")
        json.dumps(result, ensure_ascii=False)

    def test_high_accuracy_strategy_match_does_not_self_reference_pool(self) -> None:
        strategy = {
            "role": "primary",
            "scope": "global",
            "scope_value": "all",
            "play_type": "market_1x2",
            "min_confidence": 0.70,
            "accuracy": 0.80,
            "hit_count": 80,
            "sample_count": 100,
            "breaker": {"breaker_on": False},
        }
        match = core.AppMatch(
            home_team="A",
            away_team="B",
            league="Test League",
            match_time="12:00",
            match_date="2026-05-09",
            odds_home=1.8,
            odds_draw=3.2,
            odds_away=4.2,
        )

        with patch(
            "v24_app.core.get_high_accuracy_strategy_status",
            return_value={"enabled": True, "updated_at": "now", "strategy": strategy, "strategy_pool": [strategy]},
        ):
            result = core._high_accuracy_strategy_match(
                match,
                {"market_probabilities": {"home": 0.80, "draw": 0.10, "away": 0.10}},
                {},
            )

        self.assertIsNot(result, result["strategy_pool"][0])
        self.assertNotIn("strategy_pool", result["strategy_pool"][0])
        json.dumps({"high_accuracy_strategy": result}, ensure_ascii=False)

    def test_strategy_admission_gate_allows_active_low_risk_strategy(self) -> None:
        admission = core._strategy_admission_gate(
            risk_level="LOW",
            confidence=0.62,
            high_strategy={
                "enabled": True,
                "active_matches": [{"play_type": "market_1x2", "pick": "HOME", "confidence": 0.72}],
                "active_count": 1,
                "summary": "market_1x2 HOME",
            },
            play_strategy={"single": [{"play_type": "1x2"}]},
        )

        self.assertEqual(admission["decision"], "allow")
        self.assertTrue(admission["release_allowed"])
        self.assertEqual(admission["top_play"], "market_1x2")

    def test_strategy_admission_gate_observes_breaker_recovery(self) -> None:
        admission = core._strategy_admission_gate(
            risk_level="LOW",
            confidence=0.62,
            high_strategy={
                "enabled": True,
                "active_matches": [],
                "shadow_matches": [{"play_type": "market_1x2", "pick": "HOME", "confidence": 0.72}],
                "shadow_count": 1,
                "summary": "断路观察 1",
            },
            play_strategy={"single": [{"play_type": "1x2"}]},
        )

        self.assertEqual(admission["decision"], "observe")
        self.assertFalse(admission["release_allowed"])
        self.assertIn("breaker_shadow_observation", admission["reasons"])

    def test_strategy_admission_gate_blocks_high_risk_without_strategy(self) -> None:
        admission = core._strategy_admission_gate(
            risk_level="HIGH",
            confidence=0.36,
            high_strategy={"enabled": True, "active_matches": [], "active_count": 0},
            play_strategy={"single": []},
        )

        self.assertEqual(admission["decision"], "block")
        self.assertTrue(admission["blocked"])
        self.assertIn("risk_high", admission["reasons"])

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

    def test_settle_high_accuracy_strategy_results_records_shadow_without_official_hit(self) -> None:
        result = core._settle_high_accuracy_strategy_results(
            {
                "high_accuracy_strategy": {
                    "enabled": True,
                    "active_matches": [],
                    "shadow_matches": [
                        {
                            "role": "observe",
                            "original_role": "primary",
                            "play_type": "market_1x2",
                            "scope": "global",
                            "scope_value": "all",
                            "pick": "涓昏儨",
                            "confidence": 0.72,
                            "min_confidence": 0.70,
                            "backtest_accuracy": 0.78,
                            "backtest_samples": 120,
                            "layer": {"data_layer": "historical_market"},
                            "data_layer": "historical_market",
                            "breaker": {"breaker_on": True, "status": "recovering"},
                        }
                    ],
                }
            },
            result="涓昏儨",
            total_goals=2,
            actual_score="1-1",
            handicap_result="-1 璁╄礋",
            ou_result="灏?.5",
        )

        self.assertEqual(result["active_count"], 0)
        self.assertEqual(result["hit_count"], 0)
        self.assertEqual(result["shadow_count"], 1)
        self.assertEqual(result["shadow_hit_count"], 1)
        self.assertEqual(result["summary"], "-")
        self.assertEqual(result["shadow_summary"], "1/1")
        self.assertTrue(result["items"][0]["is_shadow"])
        self.assertTrue(result["items"][0]["blocked_by_breaker"])
        self.assertEqual(result["items"][0]["data_layer"], "historical_market")


if __name__ == "__main__":
    unittest.main()
