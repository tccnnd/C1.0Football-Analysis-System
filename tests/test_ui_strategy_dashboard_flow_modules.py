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
    build_agent_trace_replay_summary,
    build_agent_replay_downgrade_backtest_summary,
    build_agent_replay_guard_tuning_recommendation,
    build_strategy_policy_effect_review,
    build_handicap_margin_backtest_summary,
    build_market_entropy_backtest_summary,
    build_strategy_evaluation_agent_summary,
    build_strategy_error_attribution_summary,
    build_strategy_allowlist_filename,
    build_strategy_allowlist_report_lines,
    build_strategy_allowlist_settlement_rows,
    build_strategy_allowlist_settlement_summary,
    build_strategy_allowlist_tuning_recommendation,
    build_strategy_policy_audit_csv_text,
    build_strategy_policy_audit_report_lines,
    build_strategy_release_recovery_alerts,
    build_strategy_release_pool_rows,
    compute_strategy_admission_counts,
    filter_strategy_admission_rows,
    format_strategy_admission_label,
    format_strategy_admission_pick,
    format_strategy_admission_reasons,
    format_strategy_admission_replay_guard,
    format_strategy_admission_thresholds,
    select_strategy_allowlist_rows,
)


class UIStrategyDashboardFlowModuleTests(unittest.TestCase):
    def test_strategy_admission_formatters_translate_reason_codes(self) -> None:
        admission = {
            "decision": "observe",
            "top_play": "market_1x2",
            "top_pick": "HOME",
            "top_confidence": 0.62,
            "confidence": 0.62,
            "min_confidence": 0.58,
            "block_confidence": 0.40,
            "active_count": 1,
            "active_strategy_min": 2,
            "medium_risk_allowed": False,
            "high_risk_allowed": False,
            "reasons": ["high_accuracy_strategy_count_below_policy", "risk_medium_policy_watch", "agent_replay_policy_watch"],
            "agent_replay_guard": {
                "applied": True,
                "top_agent": "RiskGuardian",
                "top_prediction_miss_rate": 0.56,
                "top_handicap_miss_rate": 0.67,
                "actions": ["review_handicap_margin_consistency"],
            },
        }

        self.assertEqual(format_strategy_admission_label(admission), "\u89c2\u5bdf")
        self.assertIn("\u9ad8\u51c6\u7b56\u7565\u6570\u91cf\u4f4e\u4e8e\u5f53\u524d\u51c6\u5165\u95e8\u69db", format_strategy_admission_reasons(admission))
        self.assertIn("\u5f53\u524d\u95e8\u69db\u5c06\u4e2d\u98ce\u9669\u964d\u4e3a\u89c2\u5bdf", format_strategy_admission_reasons(admission))
        self.assertIn("Agent Replay", format_strategy_admission_reasons(admission))
        self.assertIn("\u5e02\u573a\u80dc\u5e73\u8d1f HOME / 62.0%", format_strategy_admission_pick(admission))
        self.assertIn("RiskGuardian", format_strategy_admission_replay_guard(admission))
        self.assertIn("让球历史失误 67.0%", format_strategy_admission_replay_guard(admission))
        self.assertIn("\u9ad8\u51c6 1/2", format_strategy_admission_thresholds(admission))
        self.assertIn("\u4e2d\u98ce\u9669\u89c2\u5bdf", format_strategy_admission_thresholds(admission))

    def test_strategy_admission_counts_and_filters_rows(self) -> None:
        rows = [
            {"prediction": {"strategy_admission": {"decision": "allow"}}},
            {"prediction": {"strategy_admission": {"decision": "observe"}}},
            {"prediction": {"strategy_admission": {"decision": "block"}}},
            {"prediction": {"strategy_admission": {"decision": "unknown"}}},
        ]

        counts = compute_strategy_admission_counts(rows)

        self.assertEqual(counts, {"all": 4, "allow": 1, "observe": 2, "block": 1})
        self.assertEqual(len(filter_strategy_admission_rows(rows, "allow")), 1)
        self.assertEqual(len(filter_strategy_admission_rows(rows, "observe")), 2)
        self.assertEqual(len(filter_strategy_admission_rows(rows, "\u963b\u65ad")), 1)
        self.assertEqual(len(filter_strategy_admission_rows(rows, "all")), 4)

    def test_market_entropy_backtest_recommends_high_entropy_block(self) -> None:
        settlements = [
            {"is_correct": False, "market_entropy_level": "HIGH", "market_entropy_score": 0.82, "market_entropy_signals": ["kelly_against_pick"], "market_entropy_risk_applied": True},
            {"is_correct": False, "market_entropy_level": "HIGH", "market_entropy_score": 0.74, "market_entropy_signals": ["odds_velocity_alert"], "market_entropy_risk_applied": True},
            {"is_correct": True, "market_entropy_level": "HIGH", "market_entropy_score": 0.70, "market_entropy_signals": ["odds_step_change"], "market_entropy_risk_applied": True},
            {"is_correct": True, "market_entropy_level": "LOW", "market_entropy_score": 0.12},
            {"is_correct": True, "market_entropy_level": "LOW", "market_entropy_score": 0.18},
            {"is_correct": True, "market_entropy_level": "MEDIUM", "market_entropy_score": 0.45},
        ]

        summary = build_market_entropy_backtest_summary(settlements)

        self.assertEqual(summary["sample_count"], 6)
        self.assertEqual(summary["avoidable_misses"], 2)
        self.assertEqual(summary["opportunity_cost"], 1)
        self.assertEqual(summary["recommendation"], "block_high_entropy")
        high_row = next(row for row in summary["rows"] if row["bucket"] == "high")
        self.assertEqual(high_row["count"], 3)
        self.assertEqual(high_row["miss_count"], 2)
        self.assertIn("kelly_against_pick", {row["top_signal"] for row in summary["rows"]})

    def test_agent_trace_replay_summarizes_risk_agent_misses(self) -> None:
        settlements = [
            {
                "is_correct": False,
                "handicap_is_correct": False,
                "supervisor_agent_statuses": {"MarketEntropy": "alert", "RiskGuardian": "alert"},
                "supervisor_agent_actions": ["manual_market_review", "keep_observation"],
            },
            {
                "is_correct": True,
                "handicap_is_correct": False,
                "supervisor_agent_statuses": {"MarketEntropy": "watch", "RiskGuardian": "watch"},
                "supervisor_agent_actions": ["watch_market_movement"],
            },
            {
                "is_correct": True,
                "handicap_is_correct": True,
                "supervisor_agent_statuses": {"Simulation": "ready"},
                "supervisor_agent_actions": [],
            },
        ]

        summary = build_agent_trace_replay_summary(settlements)

        self.assertEqual(summary["sample_count"], 3)
        self.assertEqual(summary["agent_count"], 2)
        self.assertEqual(summary["top_agent"], "MarketEntropy")
        market_row = next(row for row in summary["rows"] if row["agent"] == "MarketEntropy")
        self.assertEqual(market_row["trigger_count"], 2)
        self.assertEqual(market_row["alert_count"], 1)
        self.assertEqual(market_row["prediction_miss_rate_text"], "50.0%")
        self.assertEqual(market_row["handicap_miss_rate_text"], "100.0%")

    def test_agent_replay_downgrade_backtest_summarizes_avoided_errors(self) -> None:
        settlements = [
            {
                "is_correct": False,
                "handicap_is_correct": False,
                "agent_replay_guard_applied": True,
                "agent_replay_guard_top_agent": "RiskGuardian",
                "agent_replay_guard_actions": ["review_handicap_margin_consistency"],
            },
            {
                "is_correct": False,
                "handicap_is_correct": True,
                "agent_replay_guard_applied": True,
                "agent_replay_guard_top_agent": "RiskGuardian",
                "agent_replay_guard_actions": ["review_handicap_margin_consistency"],
            },
            {
                "is_correct": True,
                "handicap_is_correct": False,
                "agent_replay_guard_applied": True,
                "agent_replay_guard_top_agent": "MarketEntropy",
                "agent_replay_guard_actions": ["manual_market_review"],
            },
            {"is_correct": True, "handicap_is_correct": True, "agent_replay_guard_applied": False},
        ]

        summary = build_agent_replay_downgrade_backtest_summary(settlements)

        self.assertEqual(summary["sample_count"], 3)
        self.assertEqual(summary["prediction_avoided_misses"], 2)
        self.assertEqual(summary["prediction_opportunity_cost"], 1)
        self.assertEqual(summary["handicap_avoided_misses"], 2)
        self.assertEqual(summary["handicap_opportunity_cost"], 1)
        self.assertEqual(summary["net"], 2)
        self.assertEqual(summary["recommendation"], "collecting")
        risk_row = next(row for row in summary["rows"] if row["agent"] == "RiskGuardian")
        self.assertEqual(risk_row["prediction_net"], 2)
        self.assertEqual(risk_row["top_action"], "review_handicap_margin_consistency")

    def test_agent_replay_guard_tuning_tightens_positive_net(self) -> None:
        settlements = [
            {
                "is_correct": False,
                "handicap_is_correct": False,
                "agent_replay_guard_applied": True,
                "agent_replay_guard_top_agent": "RiskGuardian",
            }
            for _ in range(5)
        ] + [
            {
                "is_correct": True,
                "handicap_is_correct": True,
                "agent_replay_guard_applied": True,
                "agent_replay_guard_top_agent": "RiskGuardian",
            }
            for _ in range(3)
        ]

        recommendation = build_agent_replay_guard_tuning_recommendation(settlements)

        self.assertEqual(recommendation["action"], "tighten_guard")
        self.assertEqual(recommendation["policy_update"]["agent_replay_prediction_miss_threshold"], 0.52)
        self.assertEqual(recommendation["policy_update"]["agent_replay_handicap_miss_threshold"], 0.57)

    def test_agent_replay_guard_tuning_loosens_negative_net(self) -> None:
        settlements = [
            {
                "is_correct": False,
                "handicap_is_correct": False,
                "agent_replay_guard_applied": True,
                "agent_replay_guard_top_agent": "RiskGuardian",
            }
            for _ in range(2)
        ] + [
            {
                "is_correct": True,
                "handicap_is_correct": True,
                "agent_replay_guard_applied": True,
                "agent_replay_guard_top_agent": "RiskGuardian",
            }
            for _ in range(6)
        ]

        recommendation = build_agent_replay_guard_tuning_recommendation(settlements)

        self.assertEqual(recommendation["action"], "loosen_guard")
        self.assertEqual(recommendation["policy_update"]["agent_replay_min_samples"], 6)
        self.assertEqual(recommendation["policy_update"]["agent_replay_prediction_miss_threshold"], 0.58)
        self.assertEqual(recommendation["policy_update"]["agent_replay_handicap_miss_threshold"], 0.63)

    def test_strategy_policy_effect_review_tracks_version_windows(self) -> None:
        history = [
            {"version_id": "v1", "updated_at": "2026-05-01 10:00:00", "source": "strategy_allowlist_tuning"},
            {"version_id": "v2", "updated_at": "2026-05-02 10:00:00", "source": "agent_replay_guard_tuning"},
        ]
        settlements = [
            {
                "timestamp": "2026-05-01 12:00:00",
                "strategy_admission_decision": "allow",
                "is_correct": True,
                "agent_replay_guard_applied": False,
            },
            {
                "timestamp": "2026-05-01 13:00:00",
                "strategy_admission_decision": "allow",
                "is_correct": False,
                "agent_replay_guard_applied": False,
            },
            {
                "timestamp": "2026-05-02 12:00:00",
                "strategy_admission_decision": "allow",
                "is_correct": True,
                "handicap_is_correct": False,
                "agent_replay_guard_applied": True,
                "agent_replay_guard_top_agent": "RiskGuardian",
            },
            {
                "timestamp": "2026-05-02 13:00:00",
                "strategy_admission_decision": "allow",
                "is_correct": True,
                "handicap_is_correct": False,
                "agent_replay_guard_applied": True,
                "agent_replay_guard_top_agent": "RiskGuardian",
            },
            {
                "timestamp": "2026-05-02 14:00:00",
                "strategy_admission_decision": "observe",
                "is_correct": False,
                "handicap_is_correct": False,
                "agent_replay_guard_applied": True,
                "agent_replay_guard_top_agent": "RiskGuardian",
            },
        ]

        review = build_strategy_policy_effect_review(history, settlements)

        self.assertEqual(review["history_count"], 2)
        self.assertEqual(review["rows"][0]["version_id"], "v2")
        self.assertEqual(review["rows"][0]["effect_status"], "effective")
        self.assertEqual(review["rows"][0]["allow_hit_rate_text"], "100.0%")
        self.assertIn("Replay Guard", review["rows"][0]["body"])
        self.assertEqual(len(review["rows"][0]["sample_rows"]), 3)
        self.assertEqual(review["rows"][0]["sample_rows"][0]["replay_guard"], "\u89e6\u53d1")
        self.assertIn("RiskGuardian", review["rows"][0]["sample_rows"][0]["summary"])

    def test_strategy_policy_effect_review_pinpoints_negative_drivers(self) -> None:
        history = [
            {"version_id": "v1", "updated_at": "2026-05-01 10:00:00", "source": "strategy_allowlist_tuning"},
            {"version_id": "v2", "updated_at": "2026-05-02 10:00:00", "source": "agent_replay_guard_tuning"},
        ]
        settlements = [
            {
                "timestamp": "2026-05-01 12:00:00",
                "league": "A",
                "home_team": "H1",
                "away_team": "A1",
                "strategy_admission_decision": "allow",
                "is_correct": True,
                "handicap_is_correct": True,
            },
            {
                "timestamp": "2026-05-01 13:00:00",
                "league": "A",
                "home_team": "H2",
                "away_team": "A2",
                "strategy_admission_decision": "allow",
                "is_correct": True,
                "handicap_is_correct": True,
            },
            {
                "timestamp": "2026-05-01 14:00:00",
                "league": "A",
                "home_team": "H3",
                "away_team": "A3",
                "strategy_admission_decision": "allow",
                "is_correct": True,
                "handicap_is_correct": True,
            },
            {
                "timestamp": "2026-05-02 12:00:00",
                "league": "B",
                "home_team": "Bad1",
                "away_team": "X1",
                "strategy_admission_decision": "allow",
                "is_correct": False,
                "handicap_is_correct": False,
                "agent_replay_guard_applied": False,
            },
            {
                "timestamp": "2026-05-02 13:00:00",
                "league": "B",
                "home_team": "Bad2",
                "away_team": "X2",
                "strategy_admission_decision": "allow",
                "is_correct": False,
                "handicap_is_correct": True,
                "agent_replay_guard_applied": False,
            },
            {
                "timestamp": "2026-05-02 14:00:00",
                "league": "B",
                "home_team": "Bad3",
                "away_team": "X3",
                "strategy_admission_decision": "allow",
                "is_correct": False,
                "handicap_is_correct": True,
                "agent_replay_guard_applied": False,
            },
            {
                "timestamp": "2026-05-02 15:00:00",
                "league": "B",
                "home_team": "Cost",
                "away_team": "X4",
                "strategy_admission_decision": "observe",
                "is_correct": True,
                "handicap_is_correct": True,
                "agent_replay_guard_applied": True,
                "agent_replay_guard_top_agent": "RiskGuardian",
            },
        ]

        review = build_strategy_policy_effect_review(history, settlements)
        row = review["rows"][0]

        self.assertEqual(row["version_id"], "v2")
        self.assertEqual(row["effect_status"], "negative")
        self.assertTrue(row["rollback_recommended"])
        self.assertIn("\u5efa\u8bae\u590d\u6838\u56de\u6eda", row["body"])
        self.assertEqual(row["negative_diagnostics"]["top_negative_reason"], "\u653e\u884c\u540e1X2\u5931\u8bef")
        self.assertGreaterEqual(row["top_negative_rows"][0]["drag_score"], 2)
        self.assertIn("Bad1", row["top_negative_rows"][0]["title"])

    def test_strategy_policy_audit_report_exports_review_and_samples(self) -> None:
        history = [
            {"version_id": "v1", "updated_at": "2026-05-01 10:00:00", "source": "strategy_allowlist_tuning"},
        ]
        settlements = [
            {
                "match_id": "m1",
                "timestamp": "2026-05-01 12:00:00",
                "league": "B",
                "home_team": "Bad1",
                "away_team": "X1",
                "strategy_admission_decision": "allow",
                "is_correct": False,
                "handicap_is_correct": False,
                "agent_replay_guard_applied": False,
            }
        ]
        review = build_strategy_policy_effect_review(history, settlements)

        lines = build_strategy_policy_audit_report_lines(review, generated_at=datetime(2026, 5, 3, 9, 0, 0))
        csv_text = build_strategy_policy_audit_csv_text(review)

        report = "\n".join(lines)
        self.assertIn("# \u7b56\u7565\u8c03\u53c2\u5ba1\u8ba1\u62a5\u544a", report)
        self.assertIn("\u7248\u672c\u6548\u679c\u603b\u89c8", report)
        self.assertIn("v1", report)
        self.assertIn("Bad1", report)
        self.assertIn("version_id,updated_at,source", csv_text)
        self.assertIn("m1", csv_text)
        self.assertIn("\u653e\u884c\u540e1X2\u5931\u8bef", csv_text)

    def test_handicap_margin_backtest_recommends_high_conflict_block(self) -> None:
        settlements = [
            {"handicap_is_correct": False, "handicap_margin_level": "HIGH", "handicap_margin_score": 0.82, "handicap_margin_signals": ["handicap_direction_mismatch"]},
            {"handicap_is_correct": False, "handicap_margin_level": "HIGH", "handicap_margin_score": 0.74, "handicap_margin_signals": ["line_too_deep_for_model"]},
            {"handicap_is_correct": True, "handicap_margin_level": "HIGH", "handicap_margin_score": 0.70, "handicap_margin_signals": ["handicap_pick_margin_mismatch"]},
            {"handicap_is_correct": True, "handicap_margin_level": "LOW", "handicap_margin_score": 0.12},
            {"handicap_is_correct": True, "handicap_margin_level": "LOW", "handicap_margin_score": 0.18},
            {"handicap_is_correct": True, "handicap_margin_level": "MEDIUM", "handicap_margin_score": 0.45},
        ]

        summary = build_handicap_margin_backtest_summary(settlements)

        self.assertEqual(summary["sample_count"], 6)
        self.assertEqual(summary["avoidable_handicap_misses"], 2)
        self.assertEqual(summary["opportunity_cost"], 1)
        self.assertEqual(summary["recommendation"], "block_high_handicap_margin")
        high_row = next(row for row in summary["rows"] if row["bucket"] == "high")
        self.assertEqual(high_row["count"], 3)
        self.assertEqual(high_row["miss_count"], 2)
        self.assertIn("handicap_direction_mismatch", {row["top_signal"] for row in summary["rows"]})

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
        self.assertIn("Handicap Margin", metrics)
        self.assertIn("Agent Replay", metrics)
        self.assertIn("Replay Guard", metrics)
        self.assertIn("Replay Tuning", metrics)
        self.assertIn("\u8c03\u53c2\u751f\u6548", metrics)
        self.assertIn("agent_replay_guard_tuning", dashboard)
        self.assertIn("policy_effect_review", dashboard)
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

    def test_strategy_pool_rows_show_jc_bucket_evidence(self) -> None:
        rows = build_high_accuracy_strategy_pool_rows(
            {
                "strategy_pool": [
                    {
                        "role": "primary",
                        "scope": "jc_bucket",
                        "scope_value": "L1 | >=0.65",
                        "dimension": "league_confidence_bucket",
                        "play_type": "market_1x2",
                        "layer": {"data_layer": "jc_stratified_market"},
                        "min_confidence": 0.65,
                        "sample_count": 206,
                        "hit_count": 164,
                        "accuracy": 0.796117,
                        "wilson_lower": 0.757916,
                        "stability": {"stable": True, "stability_score": 0.795, "recent_30_accuracy": 0.733333, "recent_90_accuracy": 0.8},
                        "breaker": {"breaker_on": False, "status": "active"},
                        "jc_bucket": {"dimension": "league_confidence_bucket", "bucket": "L1 | >=0.65"},
                        "jc_context": {"confidence_bucket": ">=0.65", "odds_bucket": "<=1.50", "pick_odds": 1.24},
                        "jc_live_feedback": {
                            "status": "watch",
                            "live_count": 10,
                            "live_hit_count": 7,
                            "live_hit_rate": 0.70,
                            "deviation": -0.0961,
                        },
                        "jc_auto_calibration": {
                            "mode": "cautious",
                            "thresholds": {"min_samples": 160, "min_accuracy": 0.70, "min_wilson": 0.66},
                        },
                    }
                ]
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertIn("\u7ade\u5f69\u7a33\u5b9a\u6876", rows[0]["body"])
        self.assertIn("JC稳定桶: league_confidence_bucket / L1 | >=0.65", rows[0]["body"])
        self.assertIn("pick_odds=1.24", rows[0]["body"])
        self.assertIn("7/10", rows[0]["body"])
        self.assertIn("WATCH", rows[0]["body"])
        self.assertIn("CAUTIOUS", rows[0]["body"])
        self.assertIn("Wilson>=66.0%", rows[0]["body"])

    def test_strategy_dashboard_adds_jc_bucket_feedback_summary(self) -> None:
        status = {
            "enabled": True,
            "strategy_pool": [
                {
                    "role": "primary",
                    "scope": "jc_bucket",
                    "scope_value": "L1 | >=0.65",
                    "dimension": "league_confidence_bucket",
                    "play_type": "market_1x2",
                    "layer": {"data_layer": "jc_stratified_market"},
                    "sample_count": 206,
                    "hit_count": 164,
                    "accuracy": 0.796117,
                    "wilson_lower": 0.757916,
                    "stability": {"stable": True, "stability_score": 0.795},
                    "jc_bucket": {
                        "dimension": "league_confidence_bucket",
                        "bucket": "L1 | >=0.65",
                        "accuracy": 0.796117,
                        "wilson_lower": 0.757916,
                        "sample_count": 206,
                    },
                }
            ],
        }
        settlements = [
            {
                "high_accuracy_strategy_items": [
                    {
                        "data_layer": "jc_stratified_market",
                        "is_hit": False,
                        "jc_bucket": {
                            "dimension": "league_confidence_bucket",
                            "bucket": "L1 | >=0.65",
                        "accuracy": 0.796117,
                        "wilson_lower": 0.757916,
                        "sample_count": 206,
                        "avg_pick_odds": 1.45,
                        "avg_confidence": 0.72,
                    },
                    "confidence": 0.66,
                    "jc_context": {"confidence_bucket": ">=0.65", "odds_bucket": "1.81-2.20", "pick_odds": 1.95},
                }
            ]
        }
            for _ in range(10)
        ]

        dashboard = build_high_accuracy_strategy_dashboard(status, settlements)

        metrics = {item["label"]: item["value"] for item in dashboard["metrics"]}
        self.assertIn("JC\u7a33\u5b9a\u6876", metrics)
        self.assertIn("\u964d\u7ea7 1", metrics["JC\u7a33\u5b9a\u6876"])
        feedback = dashboard["jc_bucket_feedback"]
        self.assertEqual(feedback["status_counts"]["downgraded"], 1)
        self.assertEqual(feedback["rows"][0]["status"], "downgraded")
        self.assertIn("0/10", feedback["rows"][0]["body"])
        self.assertIn("\u8dcc\u7834Wilson", feedback["rows"][0]["body"])
        self.assertIn("\u5747\u8d54 1.95/1.45", feedback["rows"][0]["body"])
        self.assertIn(">=0.65", feedback["rows"][0]["body"])
        self.assertIn("0/3", feedback["rows"][0]["body"])

    def test_strategy_dashboard_shows_jc_recovery_progress(self) -> None:
        status = {
            "enabled": True,
            "strategy_pool": [
                {
                    "role": "primary",
                    "scope": "jc_bucket",
                    "scope_value": "L1 | >=0.65",
                    "dimension": "league_confidence_bucket",
                    "play_type": "market_1x2",
                    "layer": {"data_layer": "jc_stratified_market"},
                    "jc_bucket": {"dimension": "league_confidence_bucket", "bucket": "L1 | >=0.65", "accuracy": 0.80, "wilson_lower": 0.74, "sample_count": 180},
                    "jc_live_feedback": {
                        "status": "watch",
                        "live_count": 17,
                        "live_hit_count": 7,
                        "live_hit_rate": 0.4118,
                        "historical_accuracy": 0.80,
                        "historical_wilson_lower": 0.74,
                        "deviation": -0.3882,
                        "miss_streak": 0,
                        "recovery_streak": 7,
                        "recovery_hits_required": 3,
                        "recovery_status": "eligible",
                    },
                }
            ],
        }

        dashboard = build_high_accuracy_strategy_dashboard(status, [])
        row = dashboard["jc_bucket_feedback"]["rows"][0]

        self.assertEqual(row["status"], "watch")
        self.assertEqual(row["recovery_status"], "eligible")
        self.assertIn("\u5df2\u8fbe\u5230\u6062\u590d\u6761\u4ef6 7/3", row["body"])

    def test_strategy_error_attribution_classifies_jc_miss(self) -> None:
        settlements = [
            {
                "league": "L1",
                "home_team": "A",
                "away_team": "B",
                "high_accuracy_strategy_items": [
                    {
                        "data_layer": "jc_stratified_market",
                        "play_type": "market_1x2",
                        "pick": "HOME",
                        "actual": "AWAY",
                        "confidence": 0.72,
                        "min_confidence": 0.65,
                        "backtest_accuracy": 0.80,
                        "backtest_samples": 206,
                        "is_hit": False,
                        "jc_bucket": {
                            "dimension": "league_confidence_bucket",
                            "bucket": "L1 | >=0.65",
                            "wilson_lower": 0.75,
                            "avg_pick_odds": 1.45,
                            "avg_confidence": 0.80,
                        },
                        "jc_context": {"pick_odds": 1.95},
                        "jc_live_feedback": {
                            "status": "downgraded",
                            "live_hit_rate": 0.30,
                            "historical_wilson_lower": 0.75,
                            "deviation": -0.50,
                        },
                    }
                ],
            }
        ]

        summary = build_strategy_error_attribution_summary(settlements)

        self.assertEqual(summary["miss_count"], 1)
        self.assertIn("high_confidence_miss", summary["reason_counts"])
        self.assertIn("jc_live_downgraded", summary["reason_counts"])
        self.assertIn("jc_odds_drift", summary["reason_counts"])
        self.assertIn("\u9ad8\u7f6e\u4fe1\u5931\u8bef", summary["rows"][0]["body"])

    def test_evaluation_agent_recommends_tightening_on_weak_settlements(self) -> None:
        settlements = [
            {
                "league": "L1",
                "home_team": f"A{index}",
                "away_team": f"B{index}",
                "strategy_allowlist_decision": "allow",
                "is_correct": False,
                "prediction_confidence": 0.72,
                "high_accuracy_strategy_items": [
                    {
                        "data_layer": "jc_stratified_market",
                        "play_type": "market_1x2",
                        "pick": "HOME",
                        "actual": "AWAY",
                        "confidence": 0.72,
                        "min_confidence": 0.65,
                        "backtest_accuracy": 0.80,
                        "backtest_samples": 206,
                        "is_hit": False,
                        "jc_bucket": {"dimension": "league_confidence_bucket", "bucket": "L1 | >=0.65", "wilson_lower": 0.75},
                        "jc_live_feedback": {"status": "downgraded", "live_hit_rate": 0.30, "historical_wilson_lower": 0.75, "deviation": -0.50},
                    }
                ],
            }
            for index in range(5)
        ]

        evaluation = build_strategy_evaluation_agent_summary({"enabled": True}, settlements)

        self.assertEqual(evaluation["agent"], "Evaluation Agent")
        self.assertEqual(evaluation["status"], "tighten")
        self.assertLess(evaluation["score"], 60)
        self.assertIn("confidence_overstated", evaluation["memory_tags"])
        self.assertTrue(any("\u6536\u7d27" in item["title"] for item in evaluation["recommendations"]))

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

        lines_with_review = build_strategy_allowlist_report_lines(
            rows,
            generated_at=datetime(2026, 5, 9, 17, 30, 45),
            settlements=[
                {
                    "league": "L1",
                    "home_team": "A",
                    "away_team": "B",
                    "high_accuracy_strategy_items": [
                        {
                            "play_type": "market_1x2",
                            "pick": "home",
                            "actual": "away",
                            "confidence": 0.72,
                            "min_confidence": 0.65,
                            "backtest_accuracy": 0.8,
                            "backtest_samples": 200,
                            "is_hit": False,
                        }
                    ],
                }
            ],
        )
        payload_with_review = "\n".join(lines_with_review)
        self.assertIn("\u6700\u8fd1\u590d\u76d8\u9519\u56e0", payload_with_review)
        self.assertIn("Evaluation Agent", payload_with_review)
        self.assertIn("\u9ad8\u7f6e\u4fe1\u5931\u8bef", payload_with_review)

    def test_strategy_allowlist_filename_is_timestamped(self) -> None:
        self.assertEqual(
            build_strategy_allowlist_filename(datetime(2026, 5, 9, 17, 30, 45)),
            "strategy_allowlist_20260509_173045.md",
        )

    def test_strategy_release_pool_rows_merge_export_snapshot_and_settlement_state(self) -> None:
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
            match_time="22:00",
            match_date="2026-05-09",
            odds_home=2.0,
            odds_draw=3.1,
            odds_away=3.8,
            source="live",
            source_id="b1",
        )
        rows = [
            {
                "match": match_a,
                "prediction": {
                    "recommendation": "home",
                    "confidence": 0.72,
                    "risk_level": "LOW",
                    "strategy_admission": {"decision": "allow", "top_play": "market_1x2", "top_pick": "home", "top_confidence": 0.76, "reasons": ["high_accuracy_strategy_active"]},
                    "strategy_allowlist": {"decision": "allow", "file": "strategy_allowlist_a.md", "exported_at": "2026-05-09 17:30:45", "top_play": "market_1x2", "top_pick": "home", "top_confidence": 0.76},
                },
            },
            {
                "match": match_b,
                "prediction": {
                    "recommendation": "draw",
                    "confidence": 0.68,
                    "risk_level": "MEDIUM",
                    "strategy_admission": {"decision": "allow", "top_play": "handicap", "top_pick": "draw", "top_confidence": 0.69},
                },
            },
        ]
        snapshots = {match_a.match_id: {"strategy_allowlist": {"decision": "allow", "file": "strategy_allowlist_a.md"}}}
        settlements = [{"match_id": match_a.match_id, "strategy_allowlist_decision": "allow"}]

        pool = build_strategy_release_pool_rows(rows, snapshots=snapshots, settlements=settlements)

        self.assertEqual(len(pool), 2)
        first = pool[0]
        self.assertEqual(first["export_status"], "\u5df2\u5bfc\u51fa")
        self.assertEqual(first["snapshot_status"], "\u5df2\u4fdd\u5b58")
        self.assertEqual(first["settlement_status"], "\u5df2\u56de\u6536")
        self.assertFalse(first["ready_for_recovery"])
        second = pool[1]
        self.assertEqual(second["export_status"], "\u672a\u5bfc\u51fa")
        self.assertEqual(second["snapshot_status"], "\u7f3a\u5feb\u7167")
        self.assertEqual(second["settlement_status"], "\u5f85\u56de\u6536")

    def test_strategy_release_recovery_alerts_only_include_due_allowlist_snapshots(self) -> None:
        snapshots = [
            {
                "status": "\u5f85\u56de\u6536",
                "match": {"match_date": "2026-05-09", "match_time": "21:00", "league": "L1", "home_team": "A", "away_team": "B"},
                "prediction": {"recommendation": "home", "confidence": 0.72, "risk_level": "LOW"},
                "strategy_allowlist": {"file": "strategy_allowlist_a.md", "exported_at": "2026-05-09 17:30:45", "top_play": "market_1x2", "top_pick": "home", "top_confidence": 0.76},
            },
            {
                "status": "\u5f85\u5f00\u8d5b",
                "match": {"league": "L2", "home_team": "C", "away_team": "D"},
                "strategy_allowlist": {"file": "strategy_allowlist_b.md"},
            },
            {
                "status": "\u5f85\u56de\u6536",
                "match": {"league": "L3", "home_team": "E", "away_team": "F"},
                "strategy_allowlist": {},
            },
        ]

        alerts = build_strategy_release_recovery_alerts(snapshots)

        self.assertEqual(alerts["count"], 1)
        self.assertIn("\u6709 1 \u573a", alerts["summary"])
        row = alerts["rows"][0]
        self.assertIn("A vs B", row["title"])
        self.assertIn("strategy_allowlist_a.md", row["body"])

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

    def test_strategy_allowlist_tuning_recommendation_tightens_weak_release_pool(self) -> None:
        settlements = [
            {
                "strategy_allowlist_decision": "allow",
                "is_correct": False,
                "prediction_confidence": 0.71,
                "handicap_is_correct": False,
                "ou_is_correct": True,
                "high_accuracy_strategy_active_count": 1,
                "high_accuracy_strategy_hit_count": 0,
            },
            {
                "strategy_allowlist_decision": "allow",
                "is_correct": False,
                "prediction_confidence": 0.64,
                "handicap_is_correct": True,
                "ou_is_correct": False,
                "high_accuracy_strategy_active_count": 1,
                "high_accuracy_strategy_hit_count": 0,
            },
            {
                "strategy_allowlist_decision": "allow",
                "is_correct": True,
                "prediction_confidence": 0.62,
                "handicap_is_correct": True,
                "ou_is_correct": True,
                "high_accuracy_strategy_active_count": 1,
                "high_accuracy_strategy_hit_count": 1,
            },
            {
                "strategy_allowlist_decision": "allow",
                "is_correct": True,
                "prediction_confidence": 0.58,
                "handicap_is_correct": True,
                "ou_is_correct": True,
                "high_accuracy_strategy_active_count": 1,
                "high_accuracy_strategy_hit_count": 1,
            },
            {
                "strategy_allowlist_decision": "allow",
                "is_correct": False,
                "prediction_confidence": 0.52,
                "handicap_is_correct": False,
                "ou_is_correct": False,
                "high_accuracy_strategy_active_count": 1,
                "high_accuracy_strategy_hit_count": 0,
            },
        ]

        recommendation = build_strategy_allowlist_tuning_recommendation(settlements)

        self.assertEqual(recommendation["action"], "tighten")
        self.assertGreater(recommendation["next_min_confidence"], 0.5)
        self.assertEqual(recommendation["next_active_strategy_min"], 2)
        self.assertFalse(recommendation["medium_risk_allowed"])
        self.assertEqual(recommendation["policy_update"]["active_strategy_min"], 2)
        self.assertIn("\u4ec5\u5141\u8bb8\u4f4e\u98ce\u9669", recommendation["risk_policy"])
        self.assertTrue(recommendation["reasons"])

    def test_strategy_allowlist_tuning_recommendation_waits_for_samples(self) -> None:
        recommendation = build_strategy_allowlist_tuning_recommendation(
            [{"strategy_allowlist_decision": "allow", "is_correct": True}]
        )

        self.assertEqual(recommendation["action"], "collect")
        self.assertEqual(recommendation["next_min_confidence"], 0.5)
        self.assertIn("\u4e0d\u8db3", "\n".join(recommendation["reasons"]))


if __name__ == "__main__":
    unittest.main()
