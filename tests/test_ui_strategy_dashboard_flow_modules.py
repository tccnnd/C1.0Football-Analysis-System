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
    build_high_accuracy_live_feedback_summary,
    build_high_accuracy_live_feedback_recovery_validation,
    build_high_accuracy_strategy_pool_rows,
    build_high_accuracy_strategy_settlement_summary,
    build_agent_trace_replay_summary,
    build_agent_replay_downgrade_backtest_summary,
    build_agent_replay_guard_tuning_recommendation,
    build_strategy_policy_effect_review,
    build_strategy_policy_governance_event_summary,
    build_strategy_policy_freeze_alerts,
    build_strategy_trend_tuning_effect_review,
    build_strategy_policy_rollback_effect_review,
    build_strategy_policy_freeze_override_status,
    build_strategy_policy_rollback_preview,
    build_strategy_policy_stability_monitor,
    build_strategy_policy_tuning_guard,
    build_draw_release_guard_policy_tuning_recommendation,
    build_draw_release_guard_tuning_effect_review,
    build_draw_release_guard_rollback_effect_review,
    build_draw_release_guard_freeze_override_status,
    build_draw_release_guard_tuning_guard,
    build_draw_release_guard_review_summary,
    build_handicap_margin_backtest_summary,
    build_market_entropy_backtest_summary,
    build_strategy_evaluation_agent_summary,
    build_strategy_error_attribution_summary,
    build_video_review_fewshot_memory_summary,
    build_video_review_memory_summary,
    build_video_review_fewshot_draft_review_filename,
    build_video_review_fewshot_draft_review_lines,
    build_video_review_fewshot_merge_apply_preview,
    build_video_review_fewshot_merge_apply_preview_filename,
    build_video_review_fewshot_merge_apply_preview_lines,
    build_video_review_fewshot_merge_apply_report_filename,
    build_video_review_fewshot_merge_apply_report_lines,
    build_video_review_fewshot_merge_apply_result,
    build_video_review_fewshot_action_rows,
    build_video_review_fewshot_health_card_rows,
    build_video_review_fewshot_memory_audit_report,
    build_video_review_fewshot_memory_audit_report_filename,
    build_video_review_fewshot_memory_audit_report_lines,
    build_video_review_fewshot_memory_health_summary,
    build_video_review_fewshot_memory_monitor,
    build_video_review_fewshot_memory_quality_alerts,
    build_video_review_fewshot_memory_rollback_preview,
    build_video_review_fewshot_memory_rollback_report_filename,
    build_video_review_fewshot_memory_rollback_report_lines,
    build_video_review_fewshot_merge_bundle,
    build_video_review_fewshot_merge_bundle_filename,
    build_video_review_fewshot_merge_bundle_report_filename,
    build_video_review_fewshot_merge_bundle_report_lines,
    build_video_review_fewshot_merge_plan,
    build_video_review_fewshot_merge_plan_filename,
    build_video_review_fewshot_merge_plan_lines,
    build_video_review_source_coverage_summary,
    build_video_review_resource_closure_summary,
    validate_video_review_fewshot_payload,
    build_statsbomb_fewshot_backfill_queue,
    build_statsbomb_fewshot_backfill_report_filename,
    build_statsbomb_fewshot_backfill_report_lines,
    build_statsbomb_fewshot_draft_filename,
    build_statsbomb_fewshot_draft_payload,
    build_statsbomb_fewshot_draft_review_filename,
    build_statsbomb_fewshot_draft_review_lines,
    build_statsbomb_fewshot_merge_plan,
    build_statsbomb_fewshot_merge_plan_filename,
    build_statsbomb_fewshot_merge_plan_lines,
    build_statsbomb_fewshot_merge_bundle,
    build_statsbomb_fewshot_merge_bundle_filename,
    build_statsbomb_fewshot_merge_bundle_report_filename,
    build_statsbomb_fewshot_merge_bundle_report_lines,
    build_statsbomb_fewshot_merge_apply_preview,
    build_statsbomb_fewshot_merge_apply_preview_filename,
    build_statsbomb_fewshot_merge_apply_preview_lines,
    build_statsbomb_fewshot_merge_apply_report_filename,
    build_statsbomb_fewshot_merge_apply_report_lines,
    build_statsbomb_fewshot_merge_apply_result,
    build_statsbomb_fewshot_memory_rollback_preview,
    build_statsbomb_fewshot_memory_rollback_report_filename,
    build_statsbomb_fewshot_memory_rollback_report_lines,
    build_statsbomb_fewshot_memory_audit_report,
    build_statsbomb_fewshot_memory_audit_report_filename,
    build_statsbomb_fewshot_memory_audit_report_lines,
    build_statsbomb_fewshot_health_driver_summary,
    build_statsbomb_fewshot_memory_health_summary,
    build_statsbomb_fewshot_memory_summary,
    build_statsbomb_fewshot_memory_monitor,
    build_statsbomb_fewshot_memory_quality_alerts,
    build_statsbomb_review_training_quality_summary,
    build_statsbomb_review_training_weight_signal,
    build_statsbomb_review_training_quality_report_filename,
    build_statsbomb_review_training_quality_report_lines,
    validate_statsbomb_fewshot_draft_payload,
    build_statsbomb_event_replay_case,
    build_statsbomb_event_review_summary,
    build_statsbomb_event_sandbox_report_filename,
    build_statsbomb_event_sandbox_report_lines,
    build_statsbomb_event_sandbox_summary,
    build_strategy_allowlist_filename,
    build_strategy_allowlist_report_lines,
    build_strategy_allowlist_settlement_rows,
    build_strategy_allowlist_settlement_summary,
    build_strategy_allowlist_tuning_recommendation,
    build_strategy_policy_audit_csv_text,
    build_strategy_policy_audit_report_lines,
    build_strategy_release_recovery_loop_report_filename,
    build_strategy_release_recovery_loop_report_lines,
    build_strategy_release_recovery_alerts,
    build_strategy_release_recovery_loop,
    build_strategy_release_pool_rows,
    compute_strategy_admission_counts,
    filter_strategy_admission_rows,
    filter_strategy_policy_governance_event_rows,
    format_high_accuracy_strategy_release_explanation,
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

    def test_high_accuracy_release_explanation_includes_feedback_and_breaker_state(self) -> None:
        admission = {
            "label": "正式放行",
            "release_allowed": True,
            "top_play": "market_1x2",
            "top_pick": "HOME",
            "top_confidence": 0.72,
        }
        high_strategy = {
            "enabled": True,
            "summary": "market_1x2 HOME",
            "active_matches": [
                {
                    "role": "primary",
                    "play_type": "market_1x2",
                    "pick": "HOME",
                    "confidence": 0.72,
                    "min_confidence": 0.70,
                    "backtest_accuracy": 0.84,
                    "backtest_hits": 84,
                    "backtest_samples": 100,
                    "layer": {"data_layer": "historical_market"},
                    "breaker": {"status": "pending", "known_count": 0, "miss_streak": 0, "threshold": 3},
                }
            ],
            "shadow_matches": [
                {
                    "role": "observe",
                    "play_type": "handicap",
                    "pick": "HOME -0.5",
                    "confidence": 0.69,
                    "min_confidence": 0.68,
                    "backtest_accuracy": 0.71,
                    "backtest_hits": 71,
                    "backtest_samples": 100,
                    "layer": {"data_layer": "jc_stratified_market"},
                    "breaker": {"status": "paused", "known_count": 3, "hit_count": 0, "recent_hit_rate": 0.0, "miss_streak": 3, "threshold": 3},
                    "jc_live_feedback": {"status": "downgraded", "live_count": 10, "live_hit_count": 4, "live_hit_rate": 0.4, "recovery_status": "blocked"},
                }
            ],
        }

        text = format_high_accuracy_strategy_release_explanation(high_strategy, admission, limit=2)

        self.assertIn("正式放行 / 可放行", text)
        self.assertIn("正式 1 / 观察 1", text)
        self.assertIn("市场胜平负 HOME", text)
        self.assertIn("实盘待反馈", text)
        self.assertIn("实盘 downgraded 4/10 (40.0%)", text)
        self.assertIn("断路 paused", text)

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

    def test_strategy_trend_tuning_effect_review_waits_without_history(self) -> None:
        review = build_strategy_policy_effect_review([], [])

        effect = build_strategy_trend_tuning_effect_review(review)

        self.assertEqual(effect["status"], "collecting")
        self.assertEqual(effect["post_known_count"], 0)
        self.assertEqual(effect["allow_hit_rate_delta_text"], "-")

    def test_strategy_trend_tuning_effect_review_waits_for_post_samples(self) -> None:
        history = [
            {"version_id": "v1", "updated_at": "2026-05-01 10:00:00", "source": "manual"},
            {"version_id": "v2", "updated_at": "2026-05-02 10:00:00", "source": "release_quality_trend"},
        ]
        settlements = [
            {"timestamp": "2026-05-01 11:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-01 12:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-01 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-02 11:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-02 12:00:00", "strategy_admission_decision": "allow", "is_correct": False},
        ]

        effect = build_strategy_trend_tuning_effect_review(build_strategy_policy_effect_review(history, settlements))

        self.assertEqual(effect["status"], "collecting")
        self.assertEqual(effect["latest_source"], "release_quality_trend")
        self.assertEqual(effect["post_known_count"], 2)

    def test_strategy_trend_tuning_effect_review_marks_effective_improvement(self) -> None:
        history = [
            {"version_id": "v1", "updated_at": "2026-05-01 10:00:00", "source": "manual"},
            {"version_id": "v2", "updated_at": "2026-05-02 10:00:00", "source": "release_quality_trend"},
        ]
        settlements = [
            {"timestamp": "2026-05-01 11:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-01 12:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-01 13:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-02 11:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-02 12:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-02 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
        ]

        review = build_strategy_policy_effect_review(history, settlements)
        effect = build_strategy_trend_tuning_effect_review(review)
        dashboard = build_high_accuracy_strategy_dashboard({}, settlements, history)

        self.assertEqual(effect["status"], "effective")
        self.assertEqual(effect["post_allow_hit_rate_text"], "100.0%")
        self.assertEqual(effect["pre_allow_hit_rate_text"], "33.3%")
        self.assertEqual(effect["allow_hit_rate_delta_text"], "66.7%")
        self.assertEqual(dashboard["trend_tuning_effect_review"]["status"], "effective")

    def test_strategy_trend_tuning_effect_review_marks_negative_drop(self) -> None:
        history = [
            {"version_id": "v1", "updated_at": "2026-05-01 10:00:00", "source": "manual"},
            {"version_id": "v2", "updated_at": "2026-05-02 10:00:00", "source": "release_quality_trend"},
        ]
        settlements = [
            {"timestamp": "2026-05-01 11:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-01 12:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-01 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-02 11:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-02 12:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-02 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
        ]

        effect = build_strategy_trend_tuning_effect_review(build_strategy_policy_effect_review(history, settlements))

        self.assertEqual(effect["status"], "negative")
        self.assertEqual(effect["post_allow_hit_rate_text"], "33.3%")
        self.assertEqual(effect["pre_allow_hit_rate_text"], "100.0%")
        self.assertEqual(effect["allow_hit_rate_delta_text"], "-66.7%")
        self.assertTrue(effect["rollback_recommended"])
        self.assertEqual(effect["rollback_candidate_version_id"], "v1")

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

    def test_strategy_policy_stability_monitor_flags_regression(self) -> None:
        history = [
            {"version_id": "v1", "updated_at": "2026-05-01 10:00:00", "source": "strategy_allowlist_tuning"},
            {"version_id": "v2", "updated_at": "2026-05-08 10:00:00", "source": "agent_replay_guard_tuning"},
            {"version_id": "v3", "updated_at": "2026-05-09 10:00:00", "source": "agent_replay_guard_tuning"},
        ]
        settlements = [
            {"timestamp": "2026-05-01 11:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-01 12:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-01 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-08 11:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-08 12:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-08 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-09 11:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-09 12:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-09 13:00:00", "strategy_admission_decision": "allow", "is_correct": False},
        ]

        review = build_strategy_policy_effect_review(history, settlements, limit=10)
        monitor = build_strategy_policy_stability_monitor(review)

        self.assertEqual(review["stability_monitor"]["status"], "regression")
        self.assertEqual(monitor["status"], "regression")
        self.assertEqual(monitor["negative_streak"], 2)
        self.assertIn("\u56de\u9000", monitor["label"])
        self.assertTrue(monitor["weekly_rows"])
        self.assertIn("Replay", monitor["summary_text"])

    def test_strategy_policy_tuning_guard_blocks_unstable_versions(self) -> None:
        guard = build_strategy_policy_tuning_guard(
            {"status": "regression", "label": "\u51fa\u73b0\u56de\u9000", "summary_text": "\u56de\u9000"},
            {"action": "tighten", "policy_update": {"min_confidence": 0.72}},
            source="strategy_allowlist_tuning",
        )

        self.assertFalse(guard["allowed"])
        self.assertEqual(guard["decision"], "block")
        self.assertIn("\u6682\u505c", guard["label"])
        self.assertIn("\u56de\u6eda", guard["body"])

    def test_strategy_policy_tuning_guard_blocks_negative_trend_gate(self) -> None:
        guard = build_strategy_policy_tuning_guard(
            {"status": "stable", "label": "\u7a33\u5b9a\u751f\u6548", "summary_text": "\u7a33\u5b9a"},
            {"action": "tighten", "policy_update": {"min_confidence": 0.72}},
            source="release_quality_trend",
            trend_tuning_effect_review={
                "status": "negative",
                "label": "\u95e8\u63a7\u540e\u56de\u9000",
                "summary_text": "\u540e\u7eed 1/3 (33.3%) | \u524d\u5e8f 3/3 (100.0%)",
                "recommendation_text": "\u5fc5\u8981\u65f6\u56de\u6eda\u4e0a\u4e00\u7248\u3002",
                "rollback_candidate_version_id": "v1",
            },
        )

        self.assertFalse(guard["allowed"])
        self.assertEqual(guard["decision"], "block")
        self.assertEqual(guard["rollback_candidate_version_id"], "v1")
        self.assertTrue(guard["rollback_recommended"])
        self.assertIn("\u95e8\u63a7\u56de\u9000", guard["label"])
        self.assertIn("\u56de\u6eda\u5019\u9009\u7248\u672c: v1", guard["body"])

    def test_strategy_policy_tuning_guard_freezes_after_failed_rollback(self) -> None:
        guard = build_strategy_policy_tuning_guard(
            {"status": "stable", "label": "\u7a33\u5b9a\u751f\u6548", "summary_text": "\u7a33\u5b9a"},
            {"action": "tighten", "policy_update": {"min_confidence": 0.72}},
            source="release_quality_trend",
            rollback_effect_review={
                "status": "negative",
                "label": "\u56de\u6eda\u540e\u4ecd\u56de\u9000",
                "summary_text": "\u56de\u6eda\u540e 1/3 (33.3%) | \u5bf9\u7167 2/3 (66.7%)",
                "recommendation_text": "\u5148\u590d\u6838\u56de\u6eda\u540e\u9519\u8bef\u6837\u672c\u3002",
                "rolled_back_version_id": "v2",
            },
        )

        self.assertFalse(guard["allowed"])
        self.assertEqual(guard["decision"], "freeze")
        self.assertTrue(guard["freeze_active"])
        self.assertTrue(guard["rollback_recommended"])
        self.assertEqual(guard["rollback_candidate_version_id"], "v2")
        self.assertIn("\u51bb\u7ed3\u8c03\u53c2", guard["label"])
        self.assertIn("\u56de\u6eda\u4fee\u590d\u72b6\u6001", guard["body"])

    def test_strategy_policy_tuning_guard_allows_manual_freeze_override_with_confirm(self) -> None:
        guard = build_strategy_policy_tuning_guard(
            {"status": "stable", "label": "\u7a33\u5b9a\u751f\u6548", "summary_text": "\u7a33\u5b9a"},
            {"action": "tighten", "policy_update": {"min_confidence": 0.72}},
            source="release_quality_trend",
            rollback_effect_review={
                "status": "negative",
                "label": "\u56de\u6eda\u540e\u4ecd\u56de\u9000",
                "summary_text": "\u56de\u6eda\u540e 1/3 (33.3%) | \u5bf9\u7167 2/3 (66.7%)",
                "rolled_back_version_id": "v2",
            },
            freeze_override_status={
                "status": "overridden",
                "label": "\u51bb\u7ed3\u5df2\u4eba\u5de5\u89e3\u9664",
                "summary_text": "\u51bb\u7ed3\u5df2\u4eba\u5de5\u89e3\u9664 | \u5ba1\u8ba1 v4",
            },
        )

        self.assertTrue(guard["allowed"])
        self.assertEqual(guard["decision"], "confirm")
        self.assertFalse(guard["freeze_active"])
        self.assertTrue(guard["freeze_override_active"])
        self.assertIn("\u4eba\u5de5\u89e3\u9664", guard["label"])

    def test_strategy_policy_tuning_guard_requires_confirmation_on_watch(self) -> None:
        guard = build_strategy_policy_tuning_guard(
            {"status": "watch", "label": "\u9700\u89c2\u5bdf", "summary_text": "\u89c2\u5bdf"},
            {"action": "tighten_guard"},
            source="agent_replay_guard_tuning",
        )

        self.assertTrue(guard["allowed"])
        self.assertTrue(guard["confirm_required"])
        self.assertEqual(guard["source_label"], "Replay Guard")

    def test_strategy_policy_tuning_guard_requires_confirmation_on_trend_watch(self) -> None:
        guard = build_strategy_policy_tuning_guard(
            {"status": "stable", "label": "\u7a33\u5b9a\u751f\u6548", "summary_text": "\u7a33\u5b9a"},
            {"action": "tighten"},
            source="release_quality_trend",
            trend_tuning_effect_review={
                "status": "watch",
                "label": "\u95e8\u63a7\u540e\u89c2\u5bdf",
                "summary_text": "\u547d\u4e2d\u672a\u660e\u663e\u6539\u5584",
            },
        )

        self.assertTrue(guard["allowed"])
        self.assertTrue(guard["confirm_required"])
        self.assertIn("\u95e8\u63a7\u751f\u6548\u72b6\u6001", guard["body"])

    def test_strategy_policy_rollback_preview_compares_policy_and_effect(self) -> None:
        history = [
            {"version_id": "v1", "updated_at": "2026-05-01 10:00:00", "source": "manual"},
            {"version_id": "v2", "updated_at": "2026-05-02 10:00:00", "source": "release_quality_trend"},
        ]
        settlements = [
            {"timestamp": "2026-05-01 11:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-01 12:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-01 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-02 11:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-02 12:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-02 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
        ]
        latest = {
            "version_id": "v2",
            "updated_at": "2026-05-02 10:00:00",
            "source": "release_quality_trend",
            "policy": {
                "min_confidence": 0.70,
                "active_strategy_min": 2,
                "medium_risk_allowed": False,
                "high_risk_allowed": False,
                "agent_replay_min_samples": 6,
            },
            "previous_policy": {
                "min_confidence": 0.58,
                "active_strategy_min": 1,
                "medium_risk_allowed": True,
                "high_risk_allowed": False,
                "agent_replay_min_samples": 5,
            },
        }
        review = build_strategy_policy_effect_review(history, settlements)

        preview = build_strategy_policy_rollback_preview(latest, latest["policy"], review)

        self.assertTrue(preview["available"])
        self.assertEqual(preview["changed_count"], 4)
        self.assertEqual(preview["loosen_count"], 4)
        self.assertEqual(preview["tighten_count"], 0)
        self.assertIn("\u53d8\u66f4 4 \u9879", preview["impact_text"])
        rows = {row["key"]: row for row in preview["rows"]}
        self.assertEqual(rows["min_confidence"]["summary"], "\u6700\u4f4e\u7f6e\u4fe1: 0.70 -> 0.58 (\u653e\u5bbd)")
        self.assertEqual(preview["effect_rows"][0]["version_id"], "v2")
        self.assertIn("33.3%", preview["effect_rows"][0]["summary"])
        self.assertEqual(preview["effect_rows"][1]["version_id"], "v1")
        self.assertIn("100.0%", preview["effect_rows"][1]["summary"])
        self.assertIn("\u53c2\u6570\u5dee\u5f02", preview["confirm_text"])
        self.assertIn("\u751f\u6548\u5bf9\u6bd4", preview["confirm_text"])

    def test_strategy_policy_rollback_preview_handles_missing_previous_policy(self) -> None:
        preview = build_strategy_policy_rollback_preview({"version_id": "v1", "policy": {"min_confidence": 0.6}})

        self.assertFalse(preview["available"])
        self.assertIn("\u6ca1\u6709\u53ef\u6062\u590d", preview["reason"])

    def test_strategy_policy_rollback_effect_review_waits_without_rollback(self) -> None:
        review = build_strategy_policy_effect_review([], [])

        effect = build_strategy_policy_rollback_effect_review(review)

        self.assertEqual(effect["status"], "collecting")
        self.assertEqual(effect["latest_version_id"], "-")
        self.assertEqual(effect["allow_hit_rate_delta_text"], "-")

    def test_strategy_policy_rollback_effect_review_marks_repair(self) -> None:
        history = [
            {"version_id": "v1", "updated_at": "2026-05-01 10:00:00", "source": "manual"},
            {"version_id": "v2", "updated_at": "2026-05-02 10:00:00", "source": "release_quality_trend"},
            {"version_id": "v3", "updated_at": "2026-05-03 10:00:00", "source": "policy_rollback:v2"},
        ]
        settlements = [
            {"timestamp": "2026-05-01 11:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-01 12:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-01 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-02 11:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-02 12:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-02 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-03 11:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-03 12:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-03 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
        ]

        review = build_strategy_policy_effect_review(history, settlements, limit=10)
        effect = build_strategy_policy_rollback_effect_review(review)
        dashboard = build_high_accuracy_strategy_dashboard({}, settlements, history)

        self.assertEqual(effect["status"], "effective")
        self.assertEqual(effect["latest_version_id"], "v3")
        self.assertEqual(effect["rolled_back_version_id"], "v2")
        self.assertEqual(effect["post_allow_hit_rate_text"], "100.0%")
        self.assertEqual(effect["rolled_back_allow_hit_rate_text"], "33.3%")
        self.assertEqual(effect["allow_hit_rate_delta_text"], "66.7%")
        self.assertIn("\u56de\u6eda\u4fee\u590d\u751f\u6548", effect["summary_text"])
        self.assertEqual(dashboard["rollback_effect_review"]["status"], "effective")

    def test_strategy_policy_rollback_effect_review_marks_failed_repair(self) -> None:
        history = [
            {"version_id": "v1", "updated_at": "2026-05-01 10:00:00", "source": "manual"},
            {"version_id": "v2", "updated_at": "2026-05-02 10:00:00", "source": "release_quality_trend"},
            {"version_id": "v3", "updated_at": "2026-05-03 10:00:00", "source": "policy_rollback:v2"},
        ]
        settlements = [
            {"timestamp": "2026-05-01 11:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-01 12:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-01 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-02 11:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-02 12:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-02 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-03 11:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-03 12:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-03 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
        ]

        effect = build_strategy_policy_rollback_effect_review(build_strategy_policy_effect_review(history, settlements, limit=10))
        dashboard = build_high_accuracy_strategy_dashboard({}, settlements, history)

        self.assertEqual(effect["status"], "negative")
        self.assertEqual(effect["post_allow_hit_rate_text"], "33.3%")
        self.assertEqual(effect["rolled_back_allow_hit_rate_text"], "66.7%")
        self.assertEqual(effect["allow_hit_rate_delta_text"], "-33.3%")
        self.assertEqual(dashboard["policy_tuning_guard"]["decision"], "freeze")
        self.assertTrue(dashboard["policy_tuning_guard"]["freeze_active"])

    def test_strategy_policy_freeze_override_status_tracks_audit_entry(self) -> None:
        rollback_effect = {
            "status": "negative",
            "latest_version_id": "v3",
            "latest_updated_at": "2026-05-03 10:00:00",
            "summary_text": "\u56de\u6eda\u540e\u4ecd\u56de\u9000",
        }
        history = [
            {"version_id": "v3", "updated_at": "2026-05-03 10:00:00", "source": "policy_rollback:v2"},
            {"version_id": "v4", "updated_at": "2026-05-04 10:00:00", "source": "policy_freeze_override:v3"},
        ]

        status = build_strategy_policy_freeze_override_status(history, rollback_effect)

        self.assertEqual(status["status"], "overridden")
        self.assertTrue(status["override_active"])
        self.assertEqual(status["rollback_version_id"], "v3")
        self.assertEqual(status["override_version_id"], "v4")

    def test_strategy_policy_freeze_override_status_waits_for_manual_review(self) -> None:
        rollback_effect = {
            "status": "negative",
            "latest_version_id": "v3",
            "latest_updated_at": "2026-05-03 10:00:00",
        }

        status = build_strategy_policy_freeze_override_status([], rollback_effect)

        self.assertEqual(status["status"], "frozen")
        self.assertFalse(status["override_active"])
        self.assertIn("\u51bb\u7ed3", status["label"])

    def test_strategy_dashboard_uses_freeze_override_to_require_confirmation(self) -> None:
        history = [
            {"version_id": "v1", "updated_at": "2026-05-01 10:00:00", "source": "manual"},
            {"version_id": "v2", "updated_at": "2026-05-02 10:00:00", "source": "release_quality_trend"},
            {"version_id": "v3", "updated_at": "2026-05-03 10:00:00", "source": "policy_rollback:v2"},
            {"version_id": "v4", "updated_at": "2026-05-04 10:00:00", "source": "policy_freeze_override:v3"},
        ]
        settlements = [
            {"timestamp": "2026-05-01 11:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-01 12:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-01 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-02 11:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-02 12:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-02 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-03 11:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-03 12:00:00", "strategy_admission_decision": "allow", "is_correct": False},
            {"timestamp": "2026-05-03 13:00:00", "strategy_admission_decision": "allow", "is_correct": True},
        ]

        dashboard = build_high_accuracy_strategy_dashboard({}, settlements, history)

        self.assertEqual(dashboard["freeze_override_status"]["status"], "overridden")
        self.assertEqual(dashboard["policy_tuning_guard"]["decision"], "confirm")
        self.assertTrue(dashboard["policy_tuning_guard"]["freeze_override_active"])
        self.assertFalse(dashboard["policy_tuning_guard"]["freeze_active"])

    def test_strategy_dashboard_surfaces_policy_governance_events(self) -> None:
        history = [
            {"version_id": "v1", "updated_at": "2026-05-01 10:00:00", "source": "manual"},
            {"version_id": "v2", "updated_at": "2026-05-02 10:00:00", "source": "release_quality_trend"},
            {"version_id": "v3", "updated_at": "2026-05-03 10:00:00", "source": "policy_rollback:v2"},
            {"version_id": "v4", "updated_at": "2026-05-04 10:00:00", "source": "policy_freeze_override:v3"},
        ]
        settlements = [
            {"timestamp": "2026-05-02 11:00:00", "strategy_admission_decision": "allow", "is_correct": True},
            {"timestamp": "2026-05-03 11:00:00", "strategy_admission_decision": "allow", "is_correct": False},
        ]

        dashboard = build_high_accuracy_strategy_dashboard({}, settlements, history)
        governance = dashboard["policy_governance_event_summary"]
        direct = build_strategy_policy_governance_event_summary(dashboard["policy_effect_review"])
        metrics = {item["label"]: item["value"] for item in dashboard["metrics"]}

        self.assertEqual(governance["summary_text"], direct["summary_text"])
        self.assertEqual(governance["trend_gate_count"], 1)
        self.assertEqual(governance["rollback_count"], 1)
        self.assertEqual(governance["freeze_override_count"], 1)
        self.assertIn("\u56de\u6eda 1", metrics["\u6cbb\u7406\u4e8b\u4ef6"])
        self.assertEqual(governance["rows"][0]["event_type"], "freeze_override")
        self.assertEqual(governance["rows"][0]["related_version_id"], "v3")


    def test_strategy_policy_governance_event_filters_rows_by_domain_and_type(self) -> None:
        rows = [
            {"domain": "strategy", "event_type": "rollback", "version_id": "v2"},
            {"domain": "strategy", "event_type": "freeze_override", "version_id": "v3"},
            {"domain": "draw_guard", "event_type": "draw_guard_rollback", "version_id": "dg2"},
            {"domain": "draw_guard", "event_type": "draw_guard_freeze", "version_id": "dg3"},
            {"domain": "draw_guard", "event_type": "draw_guard_freeze_override", "version_id": "dg4"},
        ]

        self.assertEqual(
            [row["event_type"] for row in filter_strategy_policy_governance_event_rows(rows, domain_filter="strategy")],
            ["rollback", "freeze_override"],
        )
        self.assertEqual(
            [row["event_type"] for row in filter_strategy_policy_governance_event_rows(rows, domain_filter="draw_guard")],
            ["draw_guard_rollback", "draw_guard_freeze", "draw_guard_freeze_override"],
        )
        freeze_rows = filter_strategy_policy_governance_event_rows(rows, event_type_filter="draw_guard_freeze_override")
        self.assertEqual(len(freeze_rows), 1)
        self.assertEqual(freeze_rows[0]["version_id"], "dg4")

    def test_strategy_policy_governance_event_summary_recounts_filtered_rows(self) -> None:
        strategy_history = [
            {"version_id": "v1", "updated_at": "2026-05-01 10:00:00", "source": "manual"},
            {"version_id": "v2", "updated_at": "2026-05-02 10:00:00", "source": "release_quality_trend"},
            {"version_id": "v3", "updated_at": "2026-05-03 10:00:00", "source": "policy_rollback:v2"},
            {"version_id": "v4", "updated_at": "2026-05-04 10:00:00", "source": "policy_freeze_override:v3"},
        ]
        draw_history = [
            {"version_id": "dg1", "updated_at": "2026-05-01 10:00:00", "source": "manual"},
            {"version_id": "dg2", "updated_at": "2026-05-02 10:00:00", "source": "draw_release_guard_tuning"},
            {"version_id": "dg3", "updated_at": "2026-05-03 10:00:00", "source": "draw_guard_policy_rollback:dg2"},
            {"version_id": "dg4", "updated_at": "2026-05-04 10:00:00", "source": "draw_guard_freeze_override:dg3"},
        ]
        settlements = [
            {"timestamp": "2026-05-02 11:00:00", "strategy_admission_decision": "allow", "is_correct": True, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-02 12:00:00", "strategy_admission_decision": "allow", "is_correct": False, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-02 13:00:00", "strategy_admission_decision": "allow", "is_correct": False, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-03 11:00:00", "strategy_admission_decision": "allow", "is_correct": False, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-03 12:00:00", "strategy_admission_decision": "allow", "is_correct": False, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-03 13:00:00", "strategy_admission_decision": "allow", "is_correct": True, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
        ]

        review = build_strategy_policy_effect_review(strategy_history, settlements)
        draw_tuning = build_draw_release_guard_tuning_effect_review(draw_history, settlements)
        draw_rollback = build_draw_release_guard_rollback_effect_review(draw_history, settlements)
        draw_freeze = build_draw_release_guard_freeze_override_status(draw_history, draw_rollback)
        draw_guard = build_draw_release_guard_tuning_guard({}, rollback_effect_review=draw_rollback, freeze_override_status=draw_freeze)

        summary = build_strategy_policy_governance_event_summary(
            review,
            draw_release_guard_policy_history=draw_history,
            draw_release_guard_tuning_effect_review=draw_tuning,
            draw_release_guard_rollback_effect_review=draw_rollback,
            draw_release_guard_freeze_override_status=draw_freeze,
            draw_release_guard_tuning_guard=draw_guard,
        )
        strategy_only = build_strategy_policy_governance_event_summary(
            review,
            draw_release_guard_policy_history=draw_history,
            draw_release_guard_tuning_effect_review=draw_tuning,
            draw_release_guard_rollback_effect_review=draw_rollback,
            draw_release_guard_freeze_override_status=draw_freeze,
            draw_release_guard_tuning_guard=draw_guard,
            domain_filter="strategy",
        )
        draw_only = build_strategy_policy_governance_event_summary(
            review,
            draw_release_guard_policy_history=draw_history,
            draw_release_guard_tuning_effect_review=draw_tuning,
            draw_release_guard_rollback_effect_review=draw_rollback,
            draw_release_guard_freeze_override_status=draw_freeze,
            draw_release_guard_tuning_guard=draw_guard,
            domain_filter="draw_guard",
        )
        freeze_only = build_strategy_policy_governance_event_summary(
            review,
            draw_release_guard_policy_history=draw_history,
            draw_release_guard_tuning_effect_review=draw_tuning,
            draw_release_guard_rollback_effect_review=draw_rollback,
            draw_release_guard_freeze_override_status=draw_freeze,
            draw_release_guard_tuning_guard=draw_guard,
            event_type_filter="draw_guard_freeze_override",
        )

        self.assertEqual(summary["event_count"], 8)
        self.assertIn("DrawGuard", summary["summary_text"])
        self.assertEqual(strategy_only["event_count"], 4)
        self.assertTrue(all(row["domain"] == "strategy" for row in strategy_only["rows"]))
        self.assertEqual(draw_only["event_count"], 4)
        self.assertTrue(all(row["domain"] == "draw_guard" for row in draw_only["rows"]))
        self.assertEqual(freeze_only["event_count"], 1)
        self.assertEqual(freeze_only["rows"][0]["event_type"], "draw_guard_freeze_override")

    def test_strategy_policy_freeze_alerts_surface_blocking_and_confirmation_states(self) -> None:
        strategy_freeze = {
            "status": "frozen",
            "label": "strategy freeze",
            "rollback_version_id": "v3",
            "freeze_source": "policy_rollback:v3",
            "related_version_id": "v2",
            "recommended_action": "review rollback version",
        }
        draw_freeze = {
            "status": "frozen",
            "label": "draw guard freeze",
            "rollback_version_id": "dg3",
            "freeze_source": "draw_guard_policy_rollback:dg3",
            "related_version_id": "dg2",
            "recommended_action": "review DrawGuard rollback version",
        }

        alerts = build_strategy_policy_freeze_alerts(strategy_freeze, draw_freeze)
        strategy_alert = next(item for item in alerts["alerts"] if item["family"] == "strategy")
        draw_alert = next(item for item in alerts["alerts"] if item["family"] == "draw_guard")

        self.assertEqual(alerts["count"], 2)
        self.assertTrue(strategy_alert["blocking"])
        self.assertEqual(strategy_alert["tone"], "bad")
        self.assertIn(strategy_freeze["freeze_source"], strategy_alert["body"])
        self.assertIn(strategy_freeze["rollback_version_id"], strategy_alert["body"])
        self.assertIn(strategy_freeze["recommended_action"], strategy_alert["body"])
        self.assertTrue(draw_alert["blocking"])
        self.assertIn("DrawGuard", draw_alert["title"])

        overridden_freeze = {
            "status": "overridden",
            "label": "freeze overridden",
            "rollback_version_id": "v3",
            "override_version_id": "v4",
            "override_source": "policy_freeze_override:v4",
            "freeze_source": "policy_freeze_override:v4",
            "related_version_id": "v2",
            "recommended_action": "confirm manual override record",
        }
        confirm_alerts = build_strategy_policy_freeze_alerts(overridden_freeze, {"status": "inactive"})
        confirm_alert = confirm_alerts["alerts"][0]

        self.assertFalse(confirm_alert["blocking"])
        self.assertEqual(confirm_alert["tone"], "warning")
        self.assertEqual(confirm_alert["state_label"], "需确认")
        self.assertIn("policy_freeze_override:v4", confirm_alert["body"])

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
        self.assertIn("\u7248\u672c\u7a33\u5b9a\u76d1\u63a7", report)
        self.assertIn("\u8c03\u53c2\u95e8\u63a7", report)
        self.assertIn("\u7248\u672c\u6548\u679c\u603b\u89c8", report)
        self.assertIn("v1", report)
        self.assertIn("Bad1", report)
        self.assertIn("version_id,updated_at,source", csv_text)
        self.assertIn("event_type,event_label,related_version_id,governance_description", csv_text)
        self.assertIn("m1", csv_text)
        self.assertIn("allowlist_tuning", csv_text)
        self.assertIn("\u653e\u884c\u540e1X2\u5931\u8bef", csv_text)

    def test_strategy_policy_audit_exports_governance_events_without_samples(self) -> None:
        history = [
            {"version_id": "v1", "updated_at": "2026-05-01 10:00:00", "source": "manual"},
            {"version_id": "v2", "updated_at": "2026-05-02 10:00:00", "source": "release_quality_trend"},
            {"version_id": "v3", "updated_at": "2026-05-03 10:00:00", "source": "policy_rollback:v2"},
            {"version_id": "v4", "updated_at": "2026-05-04 10:00:00", "source": "policy_freeze_override:v3"},
        ]
        settlements = [
            {
                "match_id": "m2",
                "timestamp": "2026-05-02 12:00:00",
                "league": "A",
                "home_team": "Trend",
                "away_team": "Gate",
                "strategy_admission_decision": "allow",
                "is_correct": True,
                "handicap_is_correct": True,
                "agent_replay_guard_applied": True,
            },
            {
                "match_id": "m3",
                "timestamp": "2026-05-03 12:00:00",
                "league": "A",
                "home_team": "Rollback",
                "away_team": "Check",
                "strategy_admission_decision": "allow",
                "is_correct": False,
                "handicap_is_correct": False,
                "agent_replay_guard_applied": False,
            },
        ]

        review = build_strategy_policy_effect_review(history, settlements)
        lines = build_strategy_policy_audit_report_lines(review, generated_at=datetime(2026, 5, 5, 9, 0, 0))
        csv_text = build_strategy_policy_audit_csv_text(review)
        report = "\n".join(lines)

        self.assertIn("\u7b56\u7565\u6cbb\u7406\u4e8b\u4ef6", report)
        self.assertIn("\u8d8b\u52bf\u95e8\u63a7", report)
        self.assertIn("\u53c2\u6570\u56de\u6eda", report)
        self.assertIn("\u89e3\u9664\u51bb\u7ed3", report)
        self.assertIn("policy_rollback:v2", report)
        self.assertIn("policy_freeze_override:v3", report)
        self.assertIn("\u56de\u6eda\u4fee\u590d", report)
        self.assertIn("\u51bb\u7ed3\u89e3\u9664", report)
        self.assertIn("event_type,event_label,related_version_id,governance_description", csv_text)
        self.assertIn("trend_gate", csv_text)
        self.assertIn("rollback", csv_text)
        self.assertIn("freeze_override", csv_text)
        self.assertIn("policy_rollback:v2", csv_text)
        self.assertIn("policy_freeze_override:v3", csv_text)
        self.assertIn(",v3,", csv_text)

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

    def test_draw_release_guard_review_tracks_avoided_false_positive(self) -> None:
        settlements = [
            {"home_goals": 2, "away_goals": 1, "draw_score": 0.61, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00", "draw_release_guard_reason": "weak_draw_odds_bucket"},
            {"home_goals": 0, "away_goals": 1, "draw_score": 0.60, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00", "draw_release_guard_reason": "weak_draw_odds_bucket"},
            {"home_goals": 3, "away_goals": 1, "draw_score": 0.59, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00", "draw_release_guard_reason": "weak_draw_odds_bucket"},
            {"home_goals": 1, "away_goals": 0, "draw_score": 0.64, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "3.01-3.30", "draw_release_guard_reason": "weak_draw_odds_bucket"},
            {"home_goals": 1, "away_goals": 1, "draw_score": 0.62, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00", "draw_release_guard_reason": "weak_draw_odds_bucket"},
            {"home_goals": 0, "away_goals": 0, "draw_score": 0.72, "draw_release_guard_status": "allowed", "draw_release_guard_blocked": False, "draw_release_guard_odds_bucket": "3.31-3.60"},
        ]

        summary = build_draw_release_guard_review_summary(settlements)
        dashboard = build_high_accuracy_strategy_dashboard({"enabled": True}, settlements)

        self.assertEqual(summary["sample_count"], 6)
        self.assertEqual(summary["blocked_count"], 5)
        self.assertEqual(summary["avoided_false_positive"], 4)
        self.assertEqual(summary["missed_draw_hit"], 1)
        self.assertEqual(summary["allowed_draw_hits"], 1)
        self.assertEqual(summary["recommendation"], "keep_draw_guard")
        weak_bucket = next(row for row in summary["rows"] if row["bucket"] == "<=3.00")
        self.assertEqual(weak_bucket["avoid_count"], 3)
        self.assertEqual(weak_bucket["missed_count"], 1)
        self.assertEqual(dashboard["draw_release_guard_review"]["avoided_false_positive"], 4)
        self.assertIn("\u5e73\u5c40\u62e6\u622a", {item["label"] for item in dashboard["metrics"]})

    def test_draw_release_guard_tuning_raises_score_when_true_draw_cost_is_high(self) -> None:
        settlements = [
            {"home_goals": 1, "away_goals": 1, "draw_score": 0.60, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"home_goals": 0, "away_goals": 0, "draw_score": 0.63, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"home_goals": 2, "away_goals": 1, "draw_score": 0.62, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": ">4.20"},
            {"home_goals": 1, "away_goals": 2, "draw_score": 0.59, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": ">4.20"},
            {"home_goals": 3, "away_goals": 2, "draw_score": 0.61, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": ">4.20"},
        ]
        policy = {"policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}, ">4.20": {"source": "unit"}}}}

        tuning = build_draw_release_guard_policy_tuning_recommendation(settlements, policy)
        dashboard = build_high_accuracy_strategy_dashboard({"enabled": True}, settlements, draw_release_guard_policy_status=policy)

        self.assertEqual(tuning["action"], "loosen_guard")
        self.assertEqual(tuning["policy_update"]["min_score"], 0.62)
        self.assertIn("<=3.00", tuning["policy_update"]["weak_odds_buckets"])
        self.assertEqual(dashboard["draw_release_guard_tuning"]["action"], "loosen_guard")
        self.assertIn("\u5e73\u5c40\u8c03\u53c2", {item["label"] for item in dashboard["metrics"]})

    def test_draw_release_guard_tuning_removes_costly_odds_bucket(self) -> None:
        settlements = [
            {"home_goals": 1, "away_goals": 1, "draw_score": 0.60, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"home_goals": 0, "away_goals": 0, "draw_score": 0.62, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"home_goals": 2, "away_goals": 2, "draw_score": 0.64, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"home_goals": 2, "away_goals": 1, "draw_score": 0.66, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": ">4.20"},
            {"home_goals": 1, "away_goals": 0, "draw_score": 0.65, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": ">4.20"},
        ]
        policy = {"policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}, ">4.20": {"source": "unit"}}}}

        tuning = build_draw_release_guard_policy_tuning_recommendation(settlements, policy)

        self.assertEqual(tuning["action"], "loosen_guard")
        self.assertNotIn("<=3.00", tuning["policy_update"]["weak_odds_buckets"])
        self.assertIn(">4.20", tuning["policy_update"]["weak_odds_buckets"])

    def test_draw_release_guard_tuning_effect_marks_effective_after_missed_rate_drops(self) -> None:
        history = [
            {
                "version_id": "dg1",
                "updated_at": "2026-05-01 10:00:00",
                "source": "manual",
                "policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
                "previous_policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
            },
            {
                "version_id": "dg2",
                "updated_at": "2026-05-02 10:00:00",
                "source": "draw_release_guard_tuning",
                "policy": {"enabled": True, "min_score": 0.62, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
                "previous_policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
            },
        ]
        settlements = [
            {"timestamp": "2026-05-01 11:00:00", "home_goals": 1, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-01 12:00:00", "home_goals": 0, "away_goals": 0, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-01 13:00:00", "home_goals": 2, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-02 11:00:00", "home_goals": 2, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-02 12:00:00", "home_goals": 1, "away_goals": 0, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-02 13:00:00", "home_goals": 0, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
        ]

        effect = build_draw_release_guard_tuning_effect_review(history, settlements)
        dashboard = build_high_accuracy_strategy_dashboard(
            {"enabled": True},
            settlements,
            draw_release_guard_policy_history=history,
        )

        self.assertEqual(effect["status"], "effective")
        self.assertEqual(effect["latest_version_id"], "dg2")
        self.assertEqual(effect["post_blocked_count"], 3)
        self.assertEqual(effect["pre_blocked_count"], 3)
        self.assertEqual(effect["missed_rate_delta_text"], "-66.7%")
        self.assertEqual(dashboard["draw_release_guard_tuning_effect"]["status"], "effective")
        self.assertIn("DrawGuard\u751f\u6548", {item["label"] for item in dashboard["metrics"]})

    def test_draw_release_guard_tuning_effect_recommends_rollback_on_regression(self) -> None:
        history = [
            {
                "version_id": "dg1",
                "updated_at": "2026-05-01 10:00:00",
                "source": "manual",
                "policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
                "previous_policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
            },
            {
                "version_id": "dg2",
                "updated_at": "2026-05-02 10:00:00",
                "source": "draw_release_guard_tuning",
                "policy": {"enabled": True, "min_score": 0.54, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
                "previous_policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
            },
        ]
        settlements = [
            {"timestamp": "2026-05-01 11:00:00", "home_goals": 2, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-01 12:00:00", "home_goals": 1, "away_goals": 0, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-01 13:00:00", "home_goals": 0, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-02 11:00:00", "home_goals": 1, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-02 12:00:00", "home_goals": 0, "away_goals": 0, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-02 13:00:00", "home_goals": 2, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
        ]

        effect = build_draw_release_guard_tuning_effect_review(history, settlements)

        self.assertEqual(effect["status"], "negative")
        self.assertTrue(effect["rollback_recommended"])
        self.assertEqual(effect["rollback_candidate_version_id"], "dg2")

    def test_draw_release_guard_tuning_effect_waits_without_history(self) -> None:
        effect = build_draw_release_guard_tuning_effect_review([], [])

        self.assertEqual(effect["status"], "none")
        self.assertEqual(effect["post_blocked_count"], 0)
        self.assertEqual(effect["rows"], [])

    def test_draw_release_guard_rollback_effect_marks_repair_after_missed_rate_drops(self) -> None:
        history = [
            {
                "version_id": "dg1",
                "updated_at": "2026-05-01 10:00:00",
                "source": "manual",
                "policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
                "previous_policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
            },
            {
                "version_id": "dg2",
                "updated_at": "2026-05-02 10:00:00",
                "source": "draw_release_guard_tuning",
                "policy": {"enabled": True, "min_score": 0.54, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
                "previous_policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
            },
            {
                "version_id": "dg3",
                "updated_at": "2026-05-03 10:00:00",
                "source": "draw_guard_policy_rollback:dg2",
                "policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
                "previous_policy": {"enabled": True, "min_score": 0.54, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
            },
        ]
        settlements = [
            {"timestamp": "2026-05-01 11:00:00", "home_goals": 2, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-01 12:00:00", "home_goals": 1, "away_goals": 0, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-01 13:00:00", "home_goals": 0, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-02 11:00:00", "home_goals": 1, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-02 12:00:00", "home_goals": 0, "away_goals": 0, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-02 13:00:00", "home_goals": 2, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-03 11:00:00", "home_goals": 2, "away_goals": 0, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-03 12:00:00", "home_goals": 1, "away_goals": 0, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-03 13:00:00", "home_goals": 0, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
        ]

        effect = build_draw_release_guard_rollback_effect_review(history, settlements)
        dashboard = build_high_accuracy_strategy_dashboard(
            {"enabled": True},
            settlements,
            draw_release_guard_policy_history=history,
        )

        self.assertEqual(effect["status"], "effective")
        self.assertEqual(effect["latest_version_id"], "dg3")
        self.assertEqual(effect["rolled_back_version_id"], "dg2")
        self.assertEqual(effect["missed_rate_delta_text"], "-66.7%")
        self.assertEqual(dashboard["draw_release_guard_rollback_effect"]["status"], "effective")
        self.assertIn("DrawGuard\u56de\u6eda", {item["label"] for item in dashboard["metrics"]})

    def test_draw_release_guard_rollback_effect_waits_without_rollback(self) -> None:
        history = [
            {
                "version_id": "dg1",
                "updated_at": "2026-05-01 10:00:00",
                "source": "manual",
                "policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
                "previous_policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
            }
        ]

        effect = build_draw_release_guard_rollback_effect_review(history, [])

        self.assertEqual(effect["status"], "collecting")
        self.assertEqual(effect["latest_version_id"], "-")
        self.assertEqual(effect["rows"], [])

    def test_draw_release_guard_tuning_guard_freezes_after_failed_rollback(self) -> None:
        rollback_effect = {
            "status": "negative",
            "label": "DrawGuard回滚后仍回退",
            "summary_text": "错过变化 +66.7%",
            "recommendation_text": "先复核回滚后错误样本。",
            "latest_version_id": "dg3",
            "rolled_back_version_id": "dg2",
        }

        guard = build_draw_release_guard_tuning_guard(
            {"action": "loosen_guard", "policy_update": {"min_score": 0.62}},
            rollback_effect_review=rollback_effect,
        )

        self.assertFalse(guard["allowed"])
        self.assertEqual(guard["decision"], "freeze")
        self.assertTrue(guard["freeze_active"])
        self.assertEqual(guard["rollback_candidate_version_id"], "dg2")
        self.assertIn("DrawGuard回滚失败", guard["label"])
        self.assertIn("回滚修复状态", guard["body"])

    def test_draw_release_guard_freeze_override_allows_confirm_after_failed_rollback(self) -> None:
        rollback_effect = {
            "status": "negative",
            "label": "DrawGuard回滚后仍回退",
            "summary_text": "错过变化 +66.7%",
            "latest_version_id": "dg3",
            "latest_updated_at": "2026-05-03 10:00:00",
            "rolled_back_version_id": "dg2",
        }
        history = [
            {"version_id": "dg4", "updated_at": "2026-05-04 10:00:00", "source": "draw_guard_freeze_override:dg3"},
            {"version_id": "dg3", "updated_at": "2026-05-03 10:00:00", "source": "draw_guard_policy_rollback:dg2"},
        ]

        override = build_draw_release_guard_freeze_override_status(history, rollback_effect)
        guard = build_draw_release_guard_tuning_guard(
            {"action": "tighten_guard", "policy_update": {"min_score": 0.54}},
            rollback_effect_review=rollback_effect,
            freeze_override_status=override,
        )

        self.assertEqual(override["status"], "overridden")
        self.assertEqual(override["override_version_id"], "dg4")
        self.assertTrue(guard["allowed"])
        self.assertEqual(guard["decision"], "confirm")
        self.assertTrue(guard["confirm_required"])
        self.assertFalse(guard["freeze_active"])

    def test_strategy_dashboard_freezes_draw_guard_tuning_after_failed_rollback(self) -> None:
        history = [
            {
                "version_id": "dg1",
                "updated_at": "2026-05-01 10:00:00",
                "source": "manual",
                "policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
                "previous_policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
            },
            {
                "version_id": "dg2",
                "updated_at": "2026-05-02 10:00:00",
                "source": "draw_release_guard_tuning",
                "policy": {"enabled": True, "min_score": 0.54, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
                "previous_policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
            },
            {
                "version_id": "dg3",
                "updated_at": "2026-05-03 10:00:00",
                "source": "draw_guard_policy_rollback:dg2",
                "policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
                "previous_policy": {"enabled": True, "min_score": 0.54, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
            },
        ]
        settlements = [
            {"timestamp": "2026-05-02 11:00:00", "home_goals": 2, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-02 12:00:00", "home_goals": 1, "away_goals": 0, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-02 13:00:00", "home_goals": 0, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-03 11:00:00", "home_goals": 1, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-03 12:00:00", "home_goals": 0, "away_goals": 0, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-03 13:00:00", "home_goals": 2, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
        ]

        dashboard = build_high_accuracy_strategy_dashboard(
            {"enabled": True},
            settlements,
            draw_release_guard_policy_history=history,
        )

        self.assertEqual(dashboard["draw_release_guard_rollback_effect"]["status"], "negative")
        self.assertEqual(dashboard["draw_release_guard_freeze_override"]["status"], "frozen")
        self.assertEqual(dashboard["draw_release_guard_tuning_guard"]["decision"], "freeze")
        self.assertFalse(dashboard["draw_release_guard_tuning_guard"]["allowed"])
        self.assertIn("DrawGuard\u95e8\u63a7", {item["label"] for item in dashboard["metrics"]})
        self.assertEqual(dashboard["policy_governance_event_summary"]["draw_guard_freeze_count"], 1)
        self.assertIn("DrawGuard", dashboard["policy_governance_event_summary"]["summary_text"])

    def test_strategy_policy_audit_exports_draw_guard_governance_events(self) -> None:
        draw_history = [
            {
                "version_id": "dg1",
                "updated_at": "2026-05-01 10:00:00",
                "source": "manual",
                "policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
                "previous_policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
            },
            {
                "version_id": "dg2",
                "updated_at": "2026-05-02 10:00:00",
                "source": "draw_release_guard_tuning",
                "policy": {"enabled": True, "min_score": 0.54, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
                "previous_policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
            },
            {
                "version_id": "dg3",
                "updated_at": "2026-05-03 10:00:00",
                "source": "draw_guard_policy_rollback:dg2",
                "policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
                "previous_policy": {"enabled": True, "min_score": 0.54, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
            },
            {
                "version_id": "dg4",
                "updated_at": "2026-05-04 10:00:00",
                "source": "draw_guard_freeze_override:dg3",
                "policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
                "previous_policy": {"enabled": True, "min_score": 0.58, "weak_odds_buckets": {"<=3.00": {"source": "unit"}}},
            },
        ]
        settlements = [
            {"timestamp": "2026-05-02 11:00:00", "home_goals": 2, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-02 12:00:00", "home_goals": 1, "away_goals": 0, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-02 13:00:00", "home_goals": 0, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-03 11:00:00", "home_goals": 1, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-03 12:00:00", "home_goals": 0, "away_goals": 0, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
            {"timestamp": "2026-05-03 13:00:00", "home_goals": 2, "away_goals": 1, "draw_release_guard_status": "blocked", "draw_release_guard_blocked": True, "draw_release_guard_odds_bucket": "<=3.00"},
        ]
        dashboard = build_high_accuracy_strategy_dashboard(
            {"enabled": True},
            settlements,
            draw_release_guard_policy_history=draw_history,
        )
        review = dashboard["policy_effect_review"]
        kwargs = {
            "draw_release_guard_policy_history": draw_history,
            "draw_release_guard_tuning_effect_review": dashboard["draw_release_guard_tuning_effect"],
            "draw_release_guard_rollback_effect_review": dashboard["draw_release_guard_rollback_effect"],
            "draw_release_guard_freeze_override_status": dashboard["draw_release_guard_freeze_override"],
            "draw_release_guard_tuning_guard": dashboard["draw_release_guard_tuning_guard"],
        }

        report = "\n".join(build_strategy_policy_audit_report_lines(review, generated_at=datetime(2026, 5, 5, 9, 0, 0), **kwargs))
        csv_text = build_strategy_policy_audit_csv_text(review, **kwargs)

        self.assertIn("DrawGuard\u56de\u6eda\u4fee\u590d", report)
        self.assertIn("DrawGuard\u53c2\u6570\u56de\u6eda", report)
        self.assertIn("DrawGuard\u89e3\u9664\u51bb\u7ed3", report)
        self.assertIn("draw_guard_policy_rollback:dg2", report)
        self.assertIn("draw_guard_freeze_override:dg3", report)
        self.assertIn("draw_guard_rollback", csv_text)
        self.assertIn("draw_guard_freeze_override", csv_text)
        self.assertIn(",draw_guard,", csv_text)

    def test_high_accuracy_live_feedback_summary_groups_strategy_states(self) -> None:
        status = {
            "enabled": True,
            "runtime_active_count": 2,
            "strategy_pool": [
                {
                    "role": "primary",
                    "scope": "league",
                    "scope_value": "La Liga",
                    "play_type": "market_1x2",
                    "layer": {"data_layer": "historical_market"},
                    "min_confidence": 0.70,
                    "sample_count": 100,
                    "hit_count": 80,
                    "accuracy": 0.80,
                    "wilson_lower": 0.72,
                    "breaker": {"breaker_on": False, "status": "pending", "known_count": 0, "hit_count": 0, "miss_streak": 0, "threshold": 3},
                },
                {
                    "role": "backup",
                    "scope": "global",
                    "scope_value": "all",
                    "play_type": "handicap",
                    "layer": {"data_layer": "app_settlement"},
                    "min_confidence": 0.75,
                    "sample_count": 40,
                    "hit_count": 25,
                    "accuracy": 0.625,
                    "wilson_lower": 0.50,
                    "breaker": {"breaker_on": False, "status": "active", "known_count": 5, "hit_count": 4, "miss_streak": 2, "threshold": 3},
                },
                {
                    "role": "primary",
                    "effective_role": "observe",
                    "scope": "jc_bucket",
                    "scope_value": "L1 | >=0.65",
                    "play_type": "market_1x2",
                    "layer": {"data_layer": "jc_stratified_market"},
                    "min_confidence": 0.65,
                    "sample_count": 206,
                    "hit_count": 164,
                    "accuracy": 0.796117,
                    "wilson_lower": 0.757916,
                    "breaker": {"breaker_on": True, "status": "paused", "known_count": 3, "hit_count": 1, "miss_streak": 3, "threshold": 3},
                    "jc_live_feedback": {"status": "downgraded", "live_count": 3, "live_hit_count": 1, "live_hit_rate": 0.333333, "deviation": -0.25},
                },
                {
                    "role": "primary",
                    "effective_role": "observe",
                    "scope": "league",
                    "scope_value": "Serie A",
                    "play_type": "ou",
                    "layer": {"data_layer": "historical_market"},
                    "min_confidence": 0.68,
                    "sample_count": 60,
                    "hit_count": 39,
                    "accuracy": 0.65,
                    "wilson_lower": 0.52,
                    "breaker": {
                        "breaker_on": True,
                        "status": "recovering",
                        "known_count": 2,
                        "hit_count": 1,
                        "miss_streak": 0,
                        "threshold": 3,
                        "recovery_streak": 1,
                        "recovery_hits_required": 2,
                    },
                },
            ],
        }

        summary = build_high_accuracy_live_feedback_summary(status)

        self.assertEqual(summary["strategy_count"], 4)
        self.assertEqual(summary["runtime_active_count"], 2)
        self.assertEqual(summary["pending_count"], 1)
        self.assertEqual(summary["known_count"], 3)
        self.assertEqual(summary["paused_count"], 1)
        self.assertEqual(summary["recovering_count"], 1)
        self.assertEqual(summary["hit_count"], 6)
        self.assertEqual(summary["feedback_known_count"], 10)
        self.assertIn("待反馈 1", summary["summary_text"])
        self.assertIn("命中 6/10", summary["summary_text"])
        titles = "\n".join(row["title"] for row in summary["rows"])
        bodies = "\n".join(row["body"] for row in summary["rows"])
        self.assertIn("待反馈", titles)
        self.assertIn("实盘反馈", titles)
        self.assertIn("暂停/观察", titles)
        self.assertIn("恢复中", titles)
        self.assertIn("接近断路", bodies)
        self.assertIn("接近恢复", bodies)
        self.assertIn("JC实盘", bodies)

    def test_high_accuracy_live_feedback_recovery_validation_tracks_after_settlement_delta(self) -> None:
        validation = build_high_accuracy_live_feedback_recovery_validation(
            {
                "runtime_active_count": 2,
                "pending_count": 3,
                "feedback_known_count": 5,
                "hit_count": 4,
                "paused_count": 1,
                "recovering_count": 0,
            },
            {
                "runtime_active_count": 3,
                "pending_count": 1,
                "feedback_known_count": 8,
                "hit_count": 6,
                "paused_count": 0,
                "recovering_count": 1,
            },
            new_settled=2,
        )

        self.assertEqual(validation["status"], "verified")
        self.assertEqual(validation["pending_reduced"], 2)
        self.assertEqual(validation["feedback_known_delta"], 3)
        self.assertEqual(validation["hit_delta"], 2)
        self.assertEqual(validation["paused_delta"], -1)
        self.assertIn("\u5df2\u9a8c\u8bc1", validation["summary_text"])
        self.assertIn("\u5f85\u53cd\u9988\u51cf\u5c11 2", validation["summary_text"])
        self.assertEqual(len(validation["rows"]), 3)

        no_feedback = build_high_accuracy_live_feedback_recovery_validation(
            {"pending_count": 1, "feedback_known_count": 2, "hit_count": 1},
            {"pending_count": 1, "feedback_known_count": 2, "hit_count": 1},
            new_settled=1,
        )
        self.assertEqual(no_feedback["status"], "no_strategy_feedback")
        self.assertEqual(no_feedback["tone"], "warning")

    def test_strategy_dashboard_summarizes_pool_and_settlements(self) -> None:
        status = {
            "enabled": True,
            "active": True,
            "breaker_status": "partial_paused",
            "recovery_status": "watch",
            "runtime_active_count": 1,
            "live_feedback_active_count": 1,
            "live_feedback_pending_count": 0,
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
        self.assertIn("partial_paused", metrics["\u7b56\u7565\u72b6\u6001"])
        self.assertEqual(metrics["\u6062\u590d\u72b6\u6001"], "watch")
        self.assertEqual(metrics["\u7b56\u7565\u6c60"], "2")
        self.assertEqual(metrics["\u7a33\u5b9a\u7b56\u7565"], "2/2")
        self.assertEqual(metrics["\u65ad\u8def\u6682\u505c"], "1")
        self.assertIn("\u5b9e\u76d8\u53cd\u9988", metrics)
        self.assertIn("\u5df2\u53cd\u9988 2", metrics["\u5b9e\u76d8\u53cd\u9988"])
        self.assertEqual(metrics["\u771f\u5b9e\u547d\u4e2d"], "50.0%")
        self.assertIn("Handicap Margin", metrics)
        self.assertIn("Agent Replay", metrics)
        self.assertIn("Replay Guard", metrics)
        self.assertIn("Replay Tuning", metrics)
        self.assertIn("\u8c03\u53c2\u751f\u6548", metrics)
        self.assertIn("\u6cbb\u7406\u4e8b\u4ef6", metrics)
        self.assertIn("\u7248\u672c\u7a33\u5b9a", metrics)
        self.assertIn("\u8c03\u53c2\u95e8\u63a7", metrics)
        self.assertIn("agent_replay_guard_tuning", dashboard)
        self.assertIn("policy_effect_review", dashboard)
        self.assertIn("policy_governance_event_summary", dashboard)
        self.assertIn("policy_stability_monitor", dashboard)
        self.assertIn("policy_tuning_guard", dashboard)
        self.assertEqual(dashboard["live_feedback_loop"]["paused_count"], 1)
        self.assertIn("APP 40", dashboard["validation_rows"][0][1])
        self.assertEqual(len(dashboard["pool_rows"]), 2)
        self.assertIn("\u89c2\u5bdf(\u539f\u4e3b\u7b56\u7565)", dashboard["pool_rows"][0]["title"])
        self.assertIn("\u65ad\u8def: ON", dashboard["pool_rows"][0]["body"])
        self.assertIn("\u56de\u6d4b: 80.0%", dashboard["pool_rows"][0]["body"])
        self.assertEqual(len(dashboard["settlement_rows"]), 2)
        self.assertIn("\u547d\u4e2d", dashboard["settlement_rows"][0]["title"])
        self.assertIn("\u65ad\u8def\u5668\u5df2\u89e6\u53d1", dashboard["guidance_rows"][0]["title"])

    def test_strategy_dashboard_keeps_historical_replay_attribution_separate(self) -> None:
        historical_replay = {
            "ok": True,
            "sample_count": 2,
            "match_count": 2,
            "hit_count": 1,
            "miss_count": 1,
            "hit_rate_text": "50.0%",
            "source_counts": {"unit_history": 2},
            "settlements": [
                {
                    "league": "Replay League",
                    "home_team": "A",
                    "away_team": "B",
                    "historical_replay": True,
                    "high_accuracy_strategy_items": [
                        {
                            "role": "primary",
                            "play_type": "market_1x2",
                            "pick": "HOME",
                            "actual": "HOME",
                            "confidence": 0.68,
                            "min_confidence": 0.60,
                            "backtest_accuracy": 0.72,
                            "backtest_samples": 180,
                            "is_hit": True,
                            "historical_replay": True,
                        }
                    ],
                },
                {
                    "league": "Replay League",
                    "home_team": "C",
                    "away_team": "D",
                    "historical_replay": True,
                    "high_accuracy_strategy_items": [
                        {
                            "role": "primary",
                            "play_type": "market_1x2",
                            "pick": "HOME",
                            "actual": "AWAY",
                            "confidence": 0.72,
                            "min_confidence": 0.60,
                            "backtest_accuracy": 0.72,
                            "backtest_samples": 180,
                            "is_hit": False,
                            "historical_replay": True,
                        }
                    ],
                },
            ],
        }

        dashboard = build_high_accuracy_strategy_dashboard(
            {"enabled": True, "strategy_pool": []},
            [],
            historical_replay=historical_replay,
        )

        metrics = {item["label"]: item["value"] for item in dashboard["metrics"]}
        self.assertEqual(metrics["\u771f\u5b9e\u547d\u4e2d"], "-")
        self.assertEqual(metrics["\u5386\u53f2\u56de\u653e"], "2 | 50.0%")
        self.assertEqual(dashboard["historical_strategy_replay"]["sample_count"], 2)
        self.assertEqual(dashboard["historical_error_attribution"]["miss_count"], 1)
        self.assertIn("high_confidence_miss", dashboard["historical_error_attribution"]["reason_counts"])
        self.assertNotIn("data_missing", dashboard["historical_error_attribution"]["reason_counts"])
        self.assertEqual(dashboard["error_attribution"]["miss_count"], 0)

    def test_strategy_pool_rows_handle_missing_status(self) -> None:
        self.assertEqual(build_high_accuracy_strategy_pool_rows({}), [])
        dashboard = build_high_accuracy_strategy_dashboard({"enabled": False, "reason": "not_calibrated"}, [])
        self.assertFalse(dashboard["enabled"])
        metrics = {item["label"]: item["value"] for item in dashboard["metrics"]}
        self.assertEqual(metrics["\u7b56\u7565\u6c60"], "0")
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

    def test_strategy_error_attribution_downranks_small_sample_as_top_reason(self) -> None:
        settlements = []
        for index in range(3):
            settlements.append(
                {
                    "league": "L",
                    "home_team": f"H{index}",
                    "away_team": f"A{index}",
                    "high_accuracy_strategy_items": [
                        {
                            "play_type": "market_1x2",
                            "pick": "HOME",
                            "actual": "AWAY",
                            "confidence": 0.70 if index == 0 else 0.50,
                            "min_confidence": 0.45,
                            "backtest_accuracy": 0.50,
                            "backtest_samples": 40,
                            "is_hit": False,
                        }
                    ],
                }
            )

        summary = build_strategy_error_attribution_summary(settlements)

        self.assertEqual(summary["reason_counts"]["small_sample"], 3)
        self.assertEqual(summary["reason_counts"]["high_confidence_miss"], 1)
        self.assertIn("\u9ad8\u7f6e\u4fe1\u5931\u8bef", summary["top_reason"])

    def test_strategy_error_attribution_uses_statsbomb_event_evidence(self) -> None:
        settlements = [
            {
                "league": "1. Bundesliga",
                "match_date": "2024-04-14",
                "home_team": "Bayer Leverkusen",
                "away_team": "Werder Bremen",
                "statsbomb_event_summary": {
                    "team_stats": {
                        "Bayer Leverkusen": {"xg": 0.72, "shots": 7, "goals": 0},
                        "Werder Bremen": {"xg": 1.48, "shots": 14, "goals": 1},
                    }
                },
                "high_accuracy_strategy_items": [
                    {
                        "play_type": "market_1x2",
                        "pick": "HOME",
                        "actual": "AWAY",
                        "confidence": 0.71,
                        "min_confidence": 0.65,
                        "backtest_accuracy": 0.74,
                        "backtest_samples": 180,
                        "is_hit": False,
                    }
                ],
            }
        ]

        summary = build_strategy_error_attribution_summary(settlements)
        evaluation = build_strategy_evaluation_agent_summary({"enabled": True}, settlements)

        self.assertIn("statsbomb_xg_against_pick", summary["reason_counts"])
        self.assertIn("statsbomb_event_control_gap", summary["reason_counts"])
        self.assertIn("StatsBomb", summary["rows"][0]["body"])
        self.assertIn("statsbomb_event_gap", evaluation["memory_tags"])

    def test_strategy_error_attribution_marks_statsbomb_finishing_variance(self) -> None:
        settlements = [
            {
                "league": "1. Bundesliga",
                "home_team": "Bayer Leverkusen",
                "away_team": "RB Leipzig",
                "statsbomb_event_summary": {
                    "team_stats": {
                        "Bayer Leverkusen": {"xg": 2.10, "shots": 16, "goals": 1},
                        "RB Leipzig": {"xg": 0.92, "shots": 8, "goals": 2},
                    }
                },
                "high_accuracy_strategy_items": [
                    {
                        "play_type": "market_1x2",
                        "pick": "HOME",
                        "actual": "AWAY",
                        "confidence": 0.68,
                        "min_confidence": 0.65,
                        "backtest_accuracy": 0.70,
                        "backtest_samples": 180,
                        "is_hit": False,
                    }
                ],
            }
        ]

        summary = build_strategy_error_attribution_summary(settlements)

        self.assertIn("statsbomb_finishing_variance", summary["reason_counts"])
        self.assertIn("StatsBomb", summary["rows"][0]["body"])

    def test_statsbomb_event_review_compares_settlements_with_baseline(self) -> None:
        settlements = [
            {
                "league": "UEFA Euro",
                "home_team": "Spain",
                "away_team": "Croatia",
                "statsbomb_event_summary": {
                    "event_count": 3500,
                    "team_stats": {
                        "Spain": {"xg": 1.12, "shots": 11, "goals": 3},
                        "Croatia": {"xg": 2.35, "shots": 16, "goals": 0},
                    },
                },
            },
            {
                "league": "UEFA Euro",
                "home_team": "Germany",
                "away_team": "Scotland",
                "statsbomb_event_summary": {
                    "event_count": 3600,
                    "team_stats": {
                        "Germany": {"xg": 2.80, "shots": 19, "goals": 5},
                        "Scotland": {"xg": 0.12, "shots": 1, "goals": 1},
                    },
                },
            },
        ]
        baseline = {
            "summary": {
                "match_count": 53,
                "xg_alignment_rate": "62.3%",
                "finishing_variance_rate": "35.8%",
            }
        }

        review = build_statsbomb_event_review_summary(settlements, baseline)

        self.assertEqual(review["sample_count"], 2)
        self.assertEqual(review["baseline_match_count"], 53)
        self.assertEqual(review["finishing_variance_count"], 1)
        self.assertEqual(review["control_gap_count"], 2)
        self.assertIn("\u8d5b\u540e\u590d\u76d8", review["leakage_note"])
        dashboard = build_high_accuracy_strategy_dashboard({}, settlements, [], baseline)
        self.assertTrue(any(item["label"] == "StatsBomb" for item in dashboard["metrics"]))

    def test_statsbomb_event_sandbox_summarizes_baseline_items(self) -> None:
        baseline = {
            "source": "StatsBomb Open Data",
            "updated_at": "2026-05-10 21:08:21",
            "leakage_note": "post match only",
            "summary": {
                "match_count": 2,
                "xg_alignment_rate": "50.0%",
                "shot_alignment_rate": "50.0%",
                "finishing_variance_rate": "50.0%",
            },
            "competition_profiles": {
                "UEFA Euro | 2024": {
                    "match_count": 2,
                    "xg_alignment_rate": "50.0%",
                    "finishing_variance_rate": "50.0%",
                    "avg_xg_total": 2.9,
                }
            },
            "xg_margin_buckets": {
                "clear_edge": {
                    "match_count": 2,
                    "xg_alignment_rate": "50.0%",
                    "shot_alignment_rate": "50.0%",
                    "finishing_variance_rate": "50.0%",
                }
            },
            "items": [
                {
                    "match_id": "statsbomb:1",
                    "match_date": "2024-06-15",
                    "league": "UEFA Euro",
                    "season": "2024",
                    "home_team": "Spain",
                    "away_team": "Croatia",
                    "score": "3-0",
                    "home_xg": 1.12,
                    "away_xg": 2.35,
                    "home_shots": 11,
                    "away_shots": 16,
                    "xg_margin": -1.23,
                    "goal_margin": 3,
                    "xg_aligned_with_score": False,
                    "shot_aligned_with_score": False,
                    "finishing_variance": True,
                    "event_count": 3500,
                }
            ],
            "variance_rows": [
                {
                    "match_id": "statsbomb:1",
                    "match_date": "2024-06-15",
                    "league": "UEFA Euro",
                    "season": "2024",
                    "home_team": "Spain",
                    "away_team": "Croatia",
                    "score": "3-0",
                    "home_xg": 1.12,
                    "away_xg": 2.35,
                    "home_shots": 11,
                    "away_shots": 16,
                    "xg_margin": -1.23,
                    "goal_margin": 3,
                    "xg_aligned_with_score": False,
                    "shot_aligned_with_score": False,
                    "finishing_variance": True,
                    "event_count": 3500,
                }
            ],
        }

        sandbox = build_statsbomb_event_sandbox_summary(baseline)

        self.assertEqual(sandbox["status"], "ready")
        self.assertEqual(sandbox["sample_count"], 2)
        self.assertEqual(len(sandbox["competition_rows"]), 1)
        self.assertEqual(len(sandbox["bucket_rows"]), 1)
        self.assertIn("终结波动", sandbox["variance_rows"][0]["diagnosis"])
        self.assertIn("Spain vs Croatia", sandbox["variance_rows"][0]["title"])

        self.assertEqual(
            build_statsbomb_event_sandbox_report_filename(datetime(2026, 5, 10, 22, 15, 30)),
            "statsbomb_event_sandbox_20260510_221530.md",
        )
        lines = build_statsbomb_event_sandbox_report_lines(
            baseline,
            generated_at=datetime(2026, 5, 10, 22, 15, 30),
        )
        payload = "\n".join(lines)
        self.assertIn("StatsBomb", payload)
        self.assertIn("Evaluation Agent", payload)
        self.assertIn("Spain vs Croatia", payload)
        self.assertIn("post match only", payload)

    def test_statsbomb_event_replay_case_generates_evaluation_chain(self) -> None:
        row = {
            "match_id": "statsbomb:1",
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
            "home_shots": 11,
            "away_shots": 16,
            "xg_margin": -1.23,
            "goal_margin": 3,
            "xg_aligned_with_score": False,
            "shot_aligned_with_score": False,
            "finishing_variance": True,
            "event_count": 3500,
        }

        case = build_statsbomb_event_replay_case(row, {"summary": {"match_count": 53, "finishing_variance_rate": "35.8%"}})

        self.assertEqual(case["status"], "miss")
        item = case["settlement"]["high_accuracy_strategy_items"][0]
        self.assertEqual(item["pick"], "AWAY")
        self.assertEqual(item["actual"], "HOME")
        evaluation = case["evaluation"]
        self.assertEqual(evaluation["statsbomb_event_review"]["baseline_match_count"], 53)
        self.assertIn("statsbomb_post_match_review", evaluation["memory_tags"])
        self.assertIn("statsbomb_finishing_variance", evaluation["error_attribution"]["reason_counts"])
        self.assertIn("Evaluation:", case["body"])

    def test_evaluation_agent_embeds_statsbomb_event_review(self) -> None:
        settlements = [
            {
                "league": "UEFA Euro",
                "home_team": "Spain",
                "away_team": "Croatia",
                "statsbomb_event_summary": {
                    "event_count": 3500,
                    "team_stats": {
                        "Spain": {"xg": 1.12, "shots": 11, "goals": 3},
                        "Croatia": {"xg": 2.35, "shots": 16, "goals": 0},
                    },
                },
                "high_accuracy_strategy_items": [
                    {
                        "play_type": "market_1x2",
                        "pick": "AWAY",
                        "actual": "HOME",
                        "confidence": 0.70,
                        "min_confidence": 0.65,
                        "backtest_accuracy": 0.72,
                        "backtest_samples": 180,
                        "is_hit": False,
                    }
                ],
            }
        ]

        evaluation = build_strategy_evaluation_agent_summary(
            {"enabled": True},
            settlements,
            {"summary": {"match_count": 53, "finishing_variance_rate": "35.8%"}},
        )

        self.assertEqual(evaluation["statsbomb_event_review"]["sample_count"], 1)
        self.assertIn("statsbomb_post_match_review", evaluation["memory_tags"])
        self.assertTrue(any("StatsBomb" in item["title"] for item in evaluation["recommendations"]))

    def test_video_review_memory_summary_extracts_hypotheses(self) -> None:
        settlements = [
            {
                "match_date": "2026-05-14",
                "league": "Test League",
                "home_team": "Alpha",
                "away_team": "Bravo",
                "video_review": {
                    "agent_review": {
                        "vision_model_status": "offline_visual_evidence_ready",
                        "evidence_level": "high",
                        "evidence_score": 0.82,
                        "event_hypotheses": [
                            {"code": "tempo_shift", "confidence": 0.86, "title": "tempo shifted"},
                            {"code": "set_piece_or_transition_risk", "confidence": 0.72, "title": "margin risk"},
                        ],
                        "recommended_followup": {"code": "annotate_tempo_turning_points"},
                    }
                },
            }
        ]

        memory = build_video_review_memory_summary(settlements)

        self.assertEqual(memory["status"], "ready")
        self.assertEqual(memory["review_count"], 1)
        self.assertEqual(memory["visual_ready_count"], 1)
        self.assertEqual(memory["actionable_count"], 2)
        self.assertEqual(memory["hypothesis_counts"]["tempo_shift"], 1)
        self.assertIn("video_post_match_review", memory["memory_tags"])
        self.assertIn("video_tempo_shift", memory["memory_tags"])
        self.assertIn("AI Video", memory["summary_text"])

    def test_evaluation_agent_uses_video_review_memory(self) -> None:
        settlements = [
            {
                "match_date": "2026-05-14",
                "league": "Test League",
                "home_team": "Alpha",
                "away_team": "Bravo",
                "high_accuracy_strategy_items": [
                    {
                        "play_type": "ou",
                        "pick": "OVER",
                        "actual": "UNDER",
                        "confidence": 0.72,
                        "min_confidence": 0.65,
                        "backtest_accuracy": 0.71,
                        "backtest_samples": 180,
                        "is_hit": False,
                    }
                ],
                "video_review": {
                    "agent_review": {
                        "vision_model_status": "offline_visual_evidence_ready",
                        "evidence_level": "high",
                        "evidence_score": 0.79,
                        "event_hypotheses": [
                            {"code": "tempo_shift", "confidence": 0.83, "title": "tempo shifted"},
                        ],
                        "recommended_followup": {"code": "annotate_tempo_turning_points"},
                    }
                },
            }
        ]

        attribution = build_strategy_error_attribution_summary(settlements)
        evaluation = build_strategy_evaluation_agent_summary({"enabled": True}, settlements)

        self.assertIn("video_tempo_shift", attribution["reason_counts"])
        self.assertIn("AI Video", attribution["rows"][0]["body"])
        self.assertEqual(evaluation["video_review_memory"]["review_count"], 1)
        self.assertIn("video_post_match_review", evaluation["memory_tags"])
        self.assertIn("video_tempo_shift", evaluation["memory_tags"])
        self.assertTrue(any("AI视频" in item["title"] for item in evaluation["recommendations"]))

    def test_video_review_source_coverage_summary_is_healthy_with_video_sources(self) -> None:
        settlements = [
            {
                "match_id": "m-local",
                "match_date": "2026-05-14",
                "league": "FIFA World Cup",
                "home_team": "Alpha",
                "away_team": "Bravo",
                "video_review": {
                    "video": {
                        "source_type": "local_file",
                        "path": "E:/APP/ELO/data/video/local.mp4",
                        "can_extract_frames": True,
                    }
                },
            },
            {
                "match_id": "m-external",
                "match_date": "2026-05-15",
                "league": "Champions Cup",
                "home_team": "Charlie",
                "away_team": "Delta",
                "video_review": {
                    "video": {
                        "source_type": "external_reference",
                        "url": "https://example.com/fifa-plus/archive",
                        "probe_status": "external_reference",
                    },
                    "source_policy": {"mode": "reference_only"},
                },
            },
        ]

        summary = build_video_review_source_coverage_summary(
            settlements,
            video_memory={"summary": {"sample_count": 2}},
        )

        self.assertEqual(summary["coverage_status"], "healthy")
        self.assertEqual(summary["total_settled_count"], 2)
        self.assertEqual(summary["local_video_count"], 1)
        self.assertEqual(summary["external_reference_count"], 1)
        self.assertEqual(summary["statsbomb_event_proxy_count"], 0)
        self.assertEqual(summary["no_review_evidence_count"], 0)
        self.assertEqual(len(summary["rows"]), 4)
        self.assertIn("FIFA+ Archive 当前主要适合世界杯回放", summary["fallback_policy_text"])
        self.assertIn("赛后事件证据只用于复盘归因，不进入赛前预测特征", summary["fallback_policy_text"])
        self.assertIn("视频记忆样本 2 条", summary["fallback_policy_text"])

    def test_video_review_source_coverage_summary_degrades_to_statsbomb_proxy(self) -> None:
        settlements = [
            {
                "match_id": "m-proxy-1",
                "match_date": "2026-05-14",
                "league": "League A",
                "home_team": "Alpha",
                "away_team": "Bravo",
                "statsbomb_event_summary": {
                    "event_count": 1200,
                    "team_stats": {"Alpha": {"xg": 1.1, "shots": 9}, "Bravo": {"xg": 0.8, "shots": 7}},
                },
            },
            {
                "match_id": "m-proxy-2",
                "match_date": "2026-05-15",
                "league": "League A",
                "home_team": "Charlie",
                "away_team": "Delta",
                "statsbomb_event_summary": {
                    "event_count": 900,
                    "team_stats": {"Charlie": {"xg": 0.9, "shots": 8}, "Delta": {"xg": 1.0, "shots": 10}},
                },
            },
            {
                "match_id": "m-proxy-3",
                "match_date": "2026-05-16",
                "league": "League B",
                "home_team": "Echo",
                "away_team": "Foxtrot",
            },
            {
                "match_id": "m-proxy-4",
                "match_date": "2026-05-17",
                "league": "League B",
                "home_team": "Golf",
                "away_team": "Hotel",
            },
        ]
        statsbomb_samples = [
            {
                "meta": {
                    "source": "statsbomb_event_sandbox",
                    "match_id": "m-proxy-3",
                }
            }
        ]

        summary = build_video_review_source_coverage_summary(
            settlements,
            statsbomb_samples=statsbomb_samples,
            video_memory={"rows": [], "summary": {"sample_count": 0}},
        )

        self.assertEqual(summary["coverage_status"], "attention")
        self.assertEqual(summary["total_settled_count"], 4)
        self.assertEqual(summary["local_video_count"], 0)
        self.assertEqual(summary["external_reference_count"], 0)
        self.assertEqual(summary["statsbomb_event_proxy_count"], 3)
        self.assertEqual(summary["no_review_evidence_count"], 1)
        self.assertTrue(any(row["coverage_kind"] == "event_proxy_ready" for row in summary["rows"]))
        self.assertTrue(any("StatsBomb/Event Proxy" in row["title"] for row in summary["rows"]))
        self.assertIn("APP 会降级使用 StatsBomb/Event Proxy", summary["fallback_policy_text"])

    def test_video_review_source_coverage_summary_blocks_on_missing_evidence(self) -> None:
        settlements = [
            {
                "match_id": f"m-missing-{index}",
                "match_date": f"2026-05-{14 + index:02d}",
                "league": "League C",
                "home_team": f"Home{index}",
                "away_team": f"Away{index}",
            }
            for index in range(4)
        ]

        summary = build_video_review_source_coverage_summary(settlements)

        self.assertEqual(summary["coverage_status"], "blocked")
        self.assertEqual(summary["total_settled_count"], 4)
        self.assertEqual(summary["no_review_evidence_count"], 4)
        self.assertEqual(summary["local_video_count"], 0)
        self.assertEqual(summary["external_reference_count"], 0)
        self.assertEqual(summary["statsbomb_event_proxy_count"], 0)
        self.assertTrue(any(row["coverage_kind"] == "missing_evidence" for row in summary["rows"]))
        self.assertTrue(any("缺少复盘证据" in row["title"] for row in summary["rows"]))

    def test_video_review_resource_closure_summary_reports_healthy_attention_and_blocked_states(self) -> None:
        healthy = build_video_review_resource_closure_summary(
            {
                "coverage_status": "healthy",
                "total_settled_count": 4,
                "local_video_count": 1,
                "external_reference_count": 1,
                "statsbomb_event_proxy_count": 2,
                "no_review_evidence_count": 0,
            },
            {"health": {"status": "healthy"}},
        )
        attention = build_video_review_resource_closure_summary(
            {
                "coverage_status": "attention",
                "total_settled_count": 4,
                "local_video_count": 1,
                "external_reference_count": 1,
                "statsbomb_event_proxy_count": 1,
                "no_review_evidence_count": 1,
            },
            {"health": {"status": "healthy"}},
        )
        blocked = build_video_review_resource_closure_summary(
            {
                "coverage_status": "healthy",
                "total_settled_count": 4,
                "local_video_count": 2,
                "external_reference_count": 1,
                "statsbomb_event_proxy_count": 1,
                "no_review_evidence_count": 0,
            },
            {"health": {"status": "blocked"}},
        )

        self.assertEqual(healthy["status"], "healthy")
        self.assertEqual(healthy["tone"], "good")
        self.assertEqual(healthy["action_key"], "open_statsbomb_review_training_closure_window")
        self.assertIn("视频资源闭环", healthy["title"])
        self.assertIn("StatsBomb/Event Proxy", healthy["body"])

        self.assertEqual(attention["status"], "attention")
        self.assertEqual(attention["tone"], "warning")
        self.assertIn("缺证据 1", attention["body"])
        self.assertEqual(attention["action_key"], "open_video_review_evidence_gap_center_window")

        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["tone"], "bad")
        self.assertEqual(blocked["status_label"], "资源闭环受阻")

    def _video_fewshot_item(
        self,
        item_id: str,
        *,
        match_id: str = "m-video",
        review_id: str = "vr-1",
        annotation_id: str = "ann-1",
        source: str = "video_manual_annotation",
        root_cause: str = "video_margin_risk",
    ) -> dict[str, object]:
        return {
            "id": item_id,
            "review_status": "draft",
            "prompt": "review video evidence",
            "completion": "post-match video review memory",
            "labels": {
                "simulated_pick": "HOME",
                "actual": "DRAW",
                "is_hit": False,
                "root_cause": root_cause,
                "tags": ["video_post_match_review", source, "strategy_miss", root_cause],
            },
            "features": {
                "evidence_score": 0.82,
                "review_confidence": 0.80,
                "hypothesis_confidence": 0.78,
                "frame_index": 3.0,
                "timestamp_seconds": 75.0,
            },
            "meta": {
                "source": source,
                "match_id": match_id,
                "review_id": review_id,
                "annotation_id": annotation_id,
                "event_type": "counter_attack",
                "hypothesis_code": "set_piece_or_transition_risk",
                "match_date": "2026-05-14",
                "league": "Test League",
                "home_team": "Alpha",
                "away_team": "Bravo",
                "score": "1-1",
            },
        }

    def test_video_review_fewshot_merge_plan_builds_bundle_and_reports(self) -> None:
        old_item = self._video_fewshot_item("video:old", match_id="old", review_id="vr-old", annotation_id="ann-old")
        new_item = self._video_fewshot_item("video:new", match_id="new", review_id="vr-new", annotation_id="ann-new")
        draft = {
            "updated_at": "2026-05-14 10:00:00",
            "summary": {"sample_count": 2, "manual_annotation_sample_count": 2, "auto_hypothesis_sample_count": 0},
            "leakage_note": "post-match video evidence only",
            "items": [old_item, new_item],
        }
        memory = {"items": [old_item]}

        validation = validate_video_review_fewshot_payload(draft)
        review_lines = build_video_review_fewshot_draft_review_lines(draft)
        plan = build_video_review_fewshot_merge_plan(draft, memory)
        plan_lines = build_video_review_fewshot_merge_plan_lines(plan)
        bundle = build_video_review_fewshot_merge_bundle(plan, generated_at=datetime(2026, 5, 14, 10, 5, 30))
        bundle_lines = build_video_review_fewshot_merge_bundle_report_lines(bundle)

        self.assertEqual(validation["status"], "ready")
        self.assertEqual(plan["status"], "ready")
        self.assertEqual(plan["mergeable_count"], 1)
        self.assertEqual(plan["skipped_count"], 1)
        self.assertTrue(any(row["reason"] == "already_in_memory" for row in plan["skipped_rows"]))
        self.assertEqual(bundle["status"], "pending_manual_apply")
        self.assertEqual(bundle["summary"]["bundle_count"], 1)
        self.assertEqual(bundle["items"][0]["id"], "video:new")
        self.assertEqual(
            build_video_review_fewshot_draft_review_filename(datetime(2026, 5, 14, 10, 5, 30)),
            "video_review_fewshot_draft_review_20260514_100530.md",
        )
        self.assertEqual(
            build_video_review_fewshot_merge_plan_filename(datetime(2026, 5, 14, 10, 5, 30)),
            "video_review_fewshot_merge_plan_20260514_100530.md",
        )
        self.assertEqual(
            build_video_review_fewshot_merge_bundle_filename(datetime(2026, 5, 14, 10, 5, 30)),
            "video_review_fewshot_merge_bundle_20260514_100530.json",
        )
        self.assertEqual(
            build_video_review_fewshot_merge_bundle_report_filename(datetime(2026, 5, 14, 10, 5, 30)),
            "video_review_fewshot_merge_bundle_review_20260514_100530.md",
        )
        self.assertIn("Video Review Few-shot Draft Review", "\n".join(review_lines))
        self.assertIn("video:new", "\n".join(plan_lines))
        self.assertIn("video_manual_annotation", "\n".join(bundle_lines))

    def test_video_review_fewshot_apply_preview_and_result_update_memory(self) -> None:
        old_item = self._video_fewshot_item("video:old", match_id="old", review_id="vr-old", annotation_id="ann-old")
        new_item = self._video_fewshot_item("video:new", match_id="new", review_id="vr-new", annotation_id="ann-new")
        duplicate_new = self._video_fewshot_item("video:new-dupe", match_id="new", review_id="vr-new", annotation_id="ann-new")
        bundle = {
            "purpose": "video_review_manual_apply_bundle",
            "status": "pending_manual_apply",
            "approval_required": True,
            "items": [new_item, old_item, duplicate_new],
        }
        existing = {
            "purpose": "evaluation_agent_video_fewshot_post_match_review",
            "summary": {"sample_count": 1},
            "items": [{**old_item, "review_status": "approved"}],
        }

        preview = build_video_review_fewshot_merge_apply_preview(bundle, existing, generated_at=datetime(2026, 5, 14, 10, 10, 30))
        preview_lines = build_video_review_fewshot_merge_apply_preview_lines(preview)
        result = build_video_review_fewshot_merge_apply_result(
            {**bundle, "items": [new_item]},
            existing,
            generated_at=datetime(2026, 5, 14, 10, 10, 30),
        )
        result_lines = build_video_review_fewshot_merge_apply_report_lines(result)
        updated_memory = result["updated_memory"]

        self.assertEqual(preview["status"], "ready_for_manual_apply")
        self.assertTrue(preview["dry_run"])
        self.assertTrue(preview["no_state_write"])
        self.assertEqual(preview["summary"]["append_count"], 1)
        self.assertEqual(preview["summary"]["skipped_count"], 2)
        self.assertTrue(any(row["reason"] == "already_in_memory" for row in preview["skipped_rows"]))
        self.assertTrue(any(row["reason"] == "duplicate_in_bundle" for row in preview["skipped_rows"]))
        self.assertEqual(result["status"], "ready_to_write")
        self.assertEqual(result["summary"]["applied_count"], 1)
        self.assertEqual(result["summary"]["final_count"], 2)
        self.assertEqual(updated_memory["summary"]["sample_count"], 2)
        self.assertEqual(updated_memory["summary"]["miss_count"], 2)
        self.assertEqual(updated_memory["items"][1]["review_status"], "approved")
        self.assertEqual(
            build_video_review_fewshot_merge_apply_preview_filename(datetime(2026, 5, 14, 10, 10, 30)),
            "video_review_fewshot_merge_apply_preview_20260514_101030.md",
        )
        self.assertEqual(
            build_video_review_fewshot_merge_apply_report_filename(datetime(2026, 5, 14, 10, 10, 30)),
            "video_review_fewshot_merge_applied_20260514_101030.md",
        )
        self.assertIn("Video Review Few-shot Merge Apply Preview", "\n".join(preview_lines))
        self.assertIn("Video Review Few-shot Merge Apply", "\n".join(result_lines))
        self.assertIn("video:new", "\n".join(result_lines))

    def test_video_review_fewshot_memory_audit_flags_gaps_and_duplicates(self) -> None:
        item = {**self._video_fewshot_item("video:1", match_id="m1", review_id="vr-1", annotation_id="ann-1"), "review_status": "approved"}
        duplicate = {**self._video_fewshot_item("video:2", match_id="m1", review_id="vr-1", annotation_id="ann-1"), "review_status": "approved"}
        other = {**self._video_fewshot_item("video:3", match_id="m2", review_id="vr-2", annotation_id="ann-2"), "review_status": "approved"}
        memory = {
            "updated_at": "2026-05-14 10:00:00",
            "purpose": "evaluation_agent_video_fewshot_post_match_review",
            "items": [item, duplicate, other],
            "leakage_note": "post-match video only",
        }

        monitor = build_video_review_fewshot_memory_monitor(
            memory,
            {"matched_count": 0, "query_tags": ["video_tempo_shift"]},
        )
        quality = build_video_review_fewshot_memory_quality_alerts(monitor, min_samples=5, concentration_threshold=0.60)
        health = build_video_review_fewshot_memory_health_summary(monitor, quality, backup_count=0)
        audit = build_video_review_fewshot_memory_audit_report(
            memory,
            monitor,
            quality,
            backup_rows=[],
            operation_rows=[{"name": "video_review_fewshot_merge_applied_20260514_100000.md", "type": "apply", "modified_at": "2026-05-14 10:00:00"}],
            generated_at=datetime(2026, 5, 14, 10, 20, 30),
        )
        lines = build_video_review_fewshot_memory_audit_report_lines(audit)
        payload = "\n".join(lines)

        self.assertEqual(monitor["sample_count"], 3)
        self.assertGreater(monitor["duplicate_key_count"], 0)
        self.assertTrue(any(alert["tag"] == "video_memory_duplicate_keys" for alert in quality["alerts"]))
        self.assertEqual(health["status"], "blocked")
        self.assertTrue(any(issue["code"] == "video_memory_backup_missing" for issue in health["issues"]))
        self.assertEqual(audit["summary"]["duplicate_key_count"], monitor["duplicate_key_count"])
        self.assertEqual(
            build_video_review_fewshot_memory_audit_report_filename(datetime(2026, 5, 14, 10, 20, 30)),
            "video_review_fewshot_memory_audit_20260514_102030.md",
        )
        self.assertIn("Video Review Few-shot Memory Audit", payload)
        self.assertIn("Duplicate Keys", payload)
        self.assertIn("video_memory_duplicate_keys", payload)

    def test_video_review_fewshot_health_cards_flag_duplicate_memory(self) -> None:
        monitor = {
            "sample_count": 3,
            "hit_count": 1,
            "miss_count": 2,
            "tag_count": 2,
            "root_cause_count": 1,
            "source_count": 1,
            "coverage_rate_text": "22.2%",
            "missing_tags": ["video_tempo_shift"],
            "current_matched_count": 0,
            "current_query_tags": ["video_tempo_shift"],
            "duplicate_key_count": 1,
        }
        quality = {
            "alert_count": 1,
            "summary_text": "alerts 1 | score_delta -3",
            "alerts": [{"tag": "video_memory_duplicate_keys", "body": "duplicate identity keys"}],
        }
        health = {
            "status": "blocked",
            "tone": "bad",
            "blocking_count": 1,
            "warning_count": 0,
            "issues": [
                {
                    "code": "video_memory_duplicate_keys",
                    "severity": "blocking",
                    "recommendation": "Deduplicate official video memory.",
                }
            ],
        }

        cards = build_video_review_fewshot_health_card_rows(monitor, quality, health)
        actions = build_video_review_fewshot_action_rows(monitor, quality, health)
        cards_by_label = {str(row["label"]): row for row in cards}

        self.assertEqual(cards_by_label["整体状态"]["tone"], "bad")
        self.assertEqual(cards_by_label["重复键"]["tone"], "bad")
        self.assertEqual(actions[0]["code"], "video_memory_duplicate_keys")
        self.assertIn("重复视频记忆", actions[0]["title"])

    def test_video_review_fewshot_action_rows_map_tag_gaps_to_backfill_advice(self) -> None:
        monitor = {
            "sample_count": 8,
            "hit_count": 3,
            "miss_count": 5,
            "tag_count": 4,
            "root_cause_count": 2,
            "source_count": 2,
            "coverage_rate_text": "55.6%",
            "missing_tags": ["video_tempo_shift", "video_margin_risk"],
            "current_matched_count": 0,
            "current_query_tags": ["video_tempo_shift"],
            "duplicate_key_count": 0,
        }
        quality = {
            "alert_count": 2,
            "summary_text": "alerts 2 | score_delta -2",
            "alerts": [
                {"tag": "video_memory_no_current_match", "body": "current tags have no reviewed memory match"},
                {"tag": "video_memory_tag_gap", "body": "missing required tags"},
            ],
        }
        health = {"status": "attention", "tone": "warning", "blocking_count": 0, "warning_count": 1, "issues": []}

        actions = build_video_review_fewshot_action_rows(monitor, quality, health)
        action_text = "\n".join(str(row.get("title") or "") for row in actions)

        self.assertIn("补当前视频错因标签", action_text)
        self.assertIn("补节奏变化", action_text)
        self.assertIn("让球风险", action_text)

    def test_video_review_fewshot_action_rows_show_ready_when_healthy(self) -> None:
        monitor = {
            "sample_count": 12,
            "hit_count": 6,
            "miss_count": 6,
            "tag_count": 9,
            "root_cause_count": 3,
            "source_count": 2,
            "coverage_rate_text": "100.0%",
            "missing_tags": [],
            "current_matched_count": 2,
            "current_query_tags": ["video_margin_risk"],
            "duplicate_key_count": 0,
        }
        quality = {"alert_count": 0, "summary_text": "alerts 0 | score_delta 0", "alerts": []}
        health = {"status": "healthy", "tone": "good", "blocking_count": 0, "warning_count": 0, "issues": []}

        cards = build_video_review_fewshot_health_card_rows(monitor, quality, health)
        actions = build_video_review_fewshot_action_rows(monitor, quality, health)
        cards_by_label = {str(row["label"]): row for row in cards}

        self.assertEqual(cards_by_label["整体状态"]["tone"], "good")
        self.assertEqual(cards_by_label["错因覆盖"]["tone"], "good")
        self.assertEqual(actions[0]["code"], "video_memory_ready")
        self.assertEqual(actions[0]["tone"], "good")
        self.assertIn("稳定性复盘", actions[0]["title"])

    def test_video_review_fewshot_memory_rollback_preview_validates_backup(self) -> None:
        backup = {
            "updated_at": "2026-05-14 10:00:00",
            "purpose": "evaluation_agent_video_fewshot_post_match_review",
            "items": [
                {**self._video_fewshot_item("video:backup", match_id="m1", review_id="vr-1", annotation_id="ann-1"), "review_status": "approved"}
            ],
            "leakage_note": "post-match video only",
        }
        current = {
            "updated_at": "2026-05-14 11:00:00",
            "purpose": "evaluation_agent_video_fewshot_post_match_review",
            "items": [
                {**self._video_fewshot_item("video:backup", match_id="m1", review_id="vr-1", annotation_id="ann-1"), "review_status": "approved"},
                {**self._video_fewshot_item("video:new", match_id="m2", review_id="vr-2", annotation_id="ann-2"), "review_status": "approved"},
            ],
        }

        preview = build_video_review_fewshot_memory_rollback_preview(
            backup,
            current,
            backup_name="video_review_fewshot_memory.backup_20260514_100000.json",
            generated_at=datetime(2026, 5, 14, 10, 25, 30),
        )
        lines = build_video_review_fewshot_memory_rollback_report_lines(preview)
        blocked = build_video_review_fewshot_memory_rollback_preview({}, current)

        self.assertEqual(preview["status"], "ready_to_restore")
        self.assertEqual(preview["summary"]["backup_count"], 1)
        self.assertEqual(preview["summary"]["current_count"], 2)
        self.assertEqual(preview["summary"]["delta"], -1)
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(
            build_video_review_fewshot_memory_rollback_report_filename(datetime(2026, 5, 14, 10, 25, 30)),
            "video_review_fewshot_memory_rollback_20260514_102530.md",
        )
        self.assertIn("Video Review Few-shot Memory Rollback", "\n".join(lines))
        self.assertIn("ready_to_restore", "\n".join(lines))

    def test_evaluation_agent_uses_video_review_fewshot_memory(self) -> None:
        memory_item = self._video_fewshot_item(
            "video:official",
            match_id="historic-video",
            review_id="vr-historic",
            annotation_id="ann-historic",
        )
        memory = {
            "purpose": "evaluation_agent_video_fewshot_post_match_review",
            "summary": {"sample_count": 1, "manual_annotation_sample_count": 1},
            "items": [{**memory_item, "review_status": "approved"}],
            "leakage_note": "post-match video only",
        }
        error_attribution = {"reason_counts": {"video_margin_risk": 1}, "miss_count": 1}
        current_video = {"review_count": 1, "memory_tags": ["video_margin_risk"]}

        video_memory = build_video_review_fewshot_memory_summary(error_attribution, current_video, memory)
        evaluation = build_strategy_evaluation_agent_summary(
            {"enabled": True},
            [],
            error_attribution=error_attribution,
            video_review_memory=current_video,
            video_review_fewshot_memory=memory,
        )

        self.assertEqual(video_memory["matched_count"], 1)
        self.assertIn("video_margin_risk", video_memory["query_tags"])
        self.assertEqual(evaluation["video_review_fewshot_memory"]["matched_count"], 1)
        self.assertIn("video_review_fewshot_memory", evaluation["memory_tags"])
        self.assertTrue(any("AI" in item["title"] and "视频" in item["title"] for item in evaluation["recommendations"]))

    def test_dashboard_exposes_video_review_fewshot_memory_card(self) -> None:
        memory = {
            "items": [
                {
                    **self._video_fewshot_item("video:official", match_id="historic-video", review_id="vr-historic", annotation_id="ann-historic"),
                    "review_status": "approved",
                }
            ]
        }
        settlements = [
            {
                "match_date": "2026-05-14",
                "league": "Test League",
                "home_team": "Alpha",
                "away_team": "Bravo",
                "high_accuracy_strategy_items": [
                    {"play_type": "market_1x2", "pick": "HOME", "actual": "DRAW", "is_hit": False}
                ],
                "video_review": {
                    "agent_review": {
                        "vision_model_status": "offline_visual_evidence_ready",
                        "evidence_level": "high",
                        "evidence_score": 0.82,
                        "event_hypotheses": [
                            {"code": "set_piece_or_transition_risk", "confidence": 0.84, "title": "margin risk"},
                        ],
                    }
                },
            }
        ]

        dashboard = build_high_accuracy_strategy_dashboard(
            {"enabled": True},
            settlements,
            video_review_fewshot_memory=memory,
        )

        self.assertEqual(dashboard["video_review_fewshot_memory"]["matched_count"], 1)
        self.assertTrue(any(card["label"] == "Video Memory" for card in dashboard["metrics"]))

    def test_evaluation_agent_uses_statsbomb_fewshot_memory(self) -> None:
        settlements = [
            {
                "league": "UEFA Euro",
                "home_team": "Spain",
                "away_team": "Croatia",
                "statsbomb_event_summary": {
                    "event_count": 3500,
                    "team_stats": {
                        "Spain": {"xg": 1.12, "shots": 11, "goals": 3},
                        "Croatia": {"xg": 2.35, "shots": 16, "goals": 0},
                    },
                },
                "high_accuracy_strategy_items": [
                    {
                        "play_type": "market_1x2",
                        "pick": "AWAY",
                        "actual": "HOME",
                        "confidence": 0.70,
                        "min_confidence": 0.65,
                        "backtest_accuracy": 0.72,
                        "backtest_samples": 180,
                        "is_hit": False,
                    }
                ],
            }
        ]
        memory = {
            "leakage_note": "post-match memory only",
            "summary": {"baseline_match_count": 53},
            "items": [
                {
                    "id": "statsbomb_sandbox:1",
                    "completion": "历史案例显示这是终结波动。",
                    "labels": {
                        "is_hit": False,
                        "simulated_pick": "AWAY",
                        "actual": "HOME",
                        "root_cause": "statsbomb_finishing_variance",
                        "tags": ["statsbomb_post_match_review", "strategy_miss", "statsbomb_finishing_variance", "xg_result_divergence"],
                    },
                    "features": {"xg_margin": -1.23},
                    "meta": {
                        "match_date": "2024-06-15",
                        "league": "UEFA Euro",
                        "home_team": "Spain",
                        "away_team": "Croatia",
                    },
                }
            ],
        }
        base_evaluation = build_strategy_evaluation_agent_summary(
            {"enabled": True},
            settlements,
            {"summary": {"match_count": 53, "finishing_variance_rate": "35.8%"}},
        )
        memory_summary = build_statsbomb_fewshot_memory_summary(
            base_evaluation["error_attribution"],
            base_evaluation["statsbomb_event_review"],
            memory,
        )
        evaluation = build_strategy_evaluation_agent_summary(
            {"enabled": True},
            settlements,
            {"summary": {"match_count": 53, "finishing_variance_rate": "35.8%"}},
            memory,
        )

        self.assertEqual(memory_summary["matched_count"], 1)
        self.assertEqual(evaluation["statsbomb_fewshot_memory"]["matched_count"], 1)
        self.assertIn("statsbomb_fewshot_memory", evaluation["memory_tags"])
        self.assertTrue(any("历史复盘记忆" in item["title"] for item in evaluation["recommendations"]))

    def test_statsbomb_review_training_samples_weight_event_proxy_attribution(self) -> None:
        settlements = [
            {
                "league": "UEFA Euro",
                "home_team": "Spain",
                "away_team": "Croatia",
                "statsbomb_event_summary": {
                    "event_count": 3500,
                    "team_stats": {
                        "Spain": {"xg": 1.12, "shots": 11, "goals": 3},
                        "Croatia": {"xg": 2.35, "shots": 16, "goals": 0},
                    },
                },
                "high_accuracy_strategy_items": [
                    {
                        "play_type": "market_1x2",
                        "pick": "AWAY",
                        "actual": "HOME",
                        "confidence": 0.70,
                        "min_confidence": 0.65,
                        "backtest_accuracy": 0.72,
                        "backtest_samples": 180,
                        "is_hit": False,
                    }
                ],
            }
        ]
        review_samples = {
            "leakage_note": "post-match event proxy only",
            "summary": {
                "sample_count": 60,
                "feature_order": ["xg_diff", "shot_diff", "event_count"],
                "label_counts": {
                    "prediction_miss": {"0": 20, "1": 40},
                    "handicap_miss": {"0": 30, "1": 30},
                    "ou_miss": {"0": 28, "1": 32},
                },
            },
            "items": [{} for _ in range(60)],
        }

        signal = build_statsbomb_review_training_weight_signal(review_samples)
        evaluation = build_strategy_evaluation_agent_summary(
            {"enabled": True},
            settlements,
            statsbomb_review_training_samples=review_samples,
        )

        self.assertEqual(signal["status"], "ready")
        self.assertGreater(signal["attribution_weights"]["statsbomb_finishing_variance"], 1.2)
        self.assertEqual(list(evaluation["error_attribution"]["reason_counts"])[0], "statsbomb_finishing_variance")
        self.assertEqual(evaluation["statsbomb_review_training_signal"]["sample_count"], 60)
        self.assertIn("statsbomb_review_training_weighted", evaluation["memory_tags"])
        self.assertTrue(any(item["title"] == "应用StatsBomb事件代理权重" for item in evaluation["recommendations"]))

    def test_statsbomb_review_training_quality_flags_missing_and_skewed_labels(self) -> None:
        missing = build_statsbomb_review_training_quality_summary({})
        skewed = build_statsbomb_review_training_quality_summary(
            {
                "summary": {
                    "sample_count": 30,
                    "feature_order": ["xg_diff", "shot_diff", "event_count"],
                    "label_counts": {"prediction_miss": {"0": 1, "1": 29}},
                },
                "items": [{} for _ in range(30)],
            }
        )

        self.assertEqual(missing["status"], "blocked")
        self.assertTrue(any(issue["code"] == "statsbomb_review_samples_missing" for issue in missing["issues"]))
        self.assertEqual(skewed["status"], "attention")
        self.assertTrue(any(issue["code"] == "prediction_miss_skewed" for issue in skewed["issues"]))
        self.assertEqual(skewed["label_rows"][0]["value"], "29/30")
        self.assertEqual(skewed["weight_rows"][0]["code"], "statsbomb_xg_against_pick")
        self.assertFalse(skewed["signal"]["weight_gate"]["enabled"])
        self.assertEqual(skewed["signal"]["weight_gate"]["mode"], "report_only")
        self.assertEqual(skewed["signal"]["attribution_weights"]["statsbomb_finishing_variance"], 1.0)
        self.assertEqual(skewed["signal"]["active_codes"], [])
        self.assertEqual(missing["signal"]["weight_gate"]["mode"], "disabled")

    def test_statsbomb_review_training_quality_gate_disables_attention_weights_in_evaluation(self) -> None:
        settlements = [
            {
                "league": "1. Bundesliga",
                "home_team": "Bayer Leverkusen",
                "away_team": "RB Leipzig",
                "statsbomb_event_summary": {
                    "team_stats": {
                        "Bayer Leverkusen": {"xg": 2.10, "shots": 16, "goals": 1},
                        "RB Leipzig": {"xg": 0.92, "shots": 8, "goals": 2},
                    }
                },
                "high_accuracy_strategy_items": [
                    {
                        "play_type": "market_1x2",
                        "pick": "HOME",
                        "actual": "AWAY",
                        "confidence": 0.68,
                        "min_confidence": 0.65,
                        "backtest_accuracy": 0.70,
                        "backtest_samples": 180,
                        "is_hit": False,
                    }
                ],
            }
        ]
        skewed_review_samples = {
            "summary": {
                "sample_count": 30,
                "feature_order": ["xg_diff", "shot_diff", "event_count"],
                "label_counts": {
                    "prediction_miss": {"0": 1, "1": 29},
                    "handicap_miss": {"0": 15, "1": 15},
                    "ou_miss": {"0": 15, "1": 15},
                },
            },
            "items": [{} for _ in range(30)],
        }

        evaluation = build_strategy_evaluation_agent_summary(
            {"enabled": True},
            settlements,
            statsbomb_review_training_samples=skewed_review_samples,
        )

        signal = evaluation["statsbomb_review_training_signal"]
        self.assertEqual(signal["weight_gate"]["mode"], "report_only")
        self.assertFalse(signal["weight_gate"]["enabled"])
        self.assertEqual(evaluation["error_attribution"]["rank_weights"]["statsbomb_finishing_variance"], 1.0)
        self.assertNotIn("statsbomb_review_training_weighted", evaluation["memory_tags"])
        self.assertIn("statsbomb_review_training_report_only", evaluation["memory_tags"])
        self.assertTrue(any("StatsBomb" in item["title"] for item in evaluation["recommendations"]))

    def test_statsbomb_review_training_quality_report_filename_is_stable(self) -> None:
        self.assertEqual(
            build_statsbomb_review_training_quality_report_filename(datetime(2026, 5, 14, 11, 20, 30)),
            "statsbomb_review_training_quality_20260514_112030.md",
        )

    def test_statsbomb_review_training_quality_report_lines_cover_blocked_attention_healthy(self) -> None:
        blocked_lines = build_statsbomb_review_training_quality_report_lines(
            build_statsbomb_review_training_quality_summary({})
        )
        attention_lines = build_statsbomb_review_training_quality_report_lines(
            build_statsbomb_review_training_quality_summary(
                {
                    "summary": {
                        "sample_count": 30,
                        "feature_order": ["xg_diff", "shot_diff", "event_count"],
                        "label_counts": {"prediction_miss": {"0": 1, "1": 29}},
                    },
                    "items": [{} for _ in range(30)],
                }
            )
        )
        healthy_lines = build_statsbomb_review_training_quality_report_lines(
            build_statsbomb_review_training_quality_summary(
                {
                    "summary": {
                        "sample_count": 60,
                        "feature_order": ["xg_diff", "shot_diff", "event_count"],
                        "label_counts": {
                            "prediction_miss": {"0": 30, "1": 30},
                            "handicap_miss": {"0": 32, "1": 28},
                            "ou_miss": {"0": 31, "1": 29},
                        },
                    },
                    "items": [{} for _ in range(60)],
                }
            )
        )

        self.assertIn("总体质量状态: blocked", "\n".join(blocked_lines))
        self.assertIn("总体质量状态: attention", "\n".join(attention_lines))
        self.assertIn("总体质量状态: healthy", "\n".join(healthy_lines))
        self.assertIn("仅用于赛后复盘，不进入赛前预测特征", "\n".join(healthy_lines))

    def test_statsbomb_review_training_quality_report_lines_include_labels_weights_issues(self) -> None:
        quality = build_statsbomb_review_training_quality_summary(
            {
                "summary": {
                    "sample_count": 30,
                    "feature_order": ["xg_diff", "shot_diff", "event_count"],
                    "label_counts": {"prediction_miss": {"0": 1, "1": 29}},
                },
                "items": [{} for _ in range(30)],
            }
        )
        payload = "\n".join(build_statsbomb_review_training_quality_report_lines(quality))
        self.assertIn("标签分布（label_rows）", payload)
        self.assertIn("错因权重（weight_rows）", payload)
        self.assertIn("质量问题与建议（issues）", payload)
        self.assertIn("prediction_miss", payload)
        self.assertIn("statsbomb_xg_against_pick", payload)
        self.assertIn("prediction_miss_skewed", payload)

    def test_statsbomb_review_training_quality_report_lines_include_repair_feedback_records(self) -> None:
        quality = build_statsbomb_review_training_quality_summary({})
        feedback_records = [
            {
                "action_key": "expand_validation_samples",
                "outcome": "partial",
                "sample_change": "+18",
                "issue_change": "blocking->warning",
                "next_step": "continue import recent settlements",
            }
        ]
        payload = "\n".join(
            build_statsbomb_review_training_quality_report_lines(
                quality,
                repair_feedback_records=feedback_records,
            )
        )
        self.assertIn("最近修复反馈（repair_feedback_records）", payload)
        self.assertIn("expand_validation_samples", payload)
        self.assertIn("blocking->warning", payload)
        self.assertIn("continue import recent settlements", payload)

    def test_dashboard_exposes_statsbomb_review_training_weight_signal(self) -> None:
        settlements = [
            {
                "league": "UEFA Euro",
                "home_team": "Spain",
                "away_team": "Croatia",
                "statsbomb_event_summary": {
                    "event_count": 3500,
                    "team_stats": {
                        "Spain": {"xg": 1.12, "shots": 11, "goals": 3},
                        "Croatia": {"xg": 2.35, "shots": 16, "goals": 0},
                    },
                },
                "high_accuracy_strategy_items": [
                    {
                        "play_type": "market_1x2",
                        "pick": "AWAY",
                        "actual": "HOME",
                        "confidence": 0.70,
                        "min_confidence": 0.65,
                        "backtest_accuracy": 0.72,
                        "backtest_samples": 180,
                        "is_hit": False,
                    }
                ],
            }
        ]
        review_samples = {
            "summary": {
                "sample_count": 60,
                "feature_order": ["xg_diff", "shot_diff", "event_count"],
                "label_counts": {
                    "prediction_miss": {"0": 20, "1": 40},
                    "handicap_miss": {"0": 30, "1": 30},
                    "ou_miss": {"0": 28, "1": 32},
                },
            },
            "items": [{} for _ in range(60)],
        }

        dashboard = build_high_accuracy_strategy_dashboard(
            {"enabled": True},
            settlements,
            statsbomb_review_training_samples=review_samples,
        )

        self.assertEqual(dashboard["evaluation_agent"]["statsbomb_review_training_signal"]["status"], "ready")
        self.assertTrue(dashboard["evaluation_agent"]["statsbomb_review_training_signal"]["weight_gate"]["enabled"])
        self.assertEqual(dashboard["statsbomb_review_training_quality"]["status"], "healthy")
        self.assertEqual(dashboard["evaluation_agent"]["statsbomb_review_training_quality"]["status"], "healthy")
        self.assertEqual(list(dashboard["error_attribution"]["reason_counts"])[0], "statsbomb_finishing_variance")
        self.assertTrue(any(card["label"] == "StatsBomb权重" for card in dashboard["metrics"]))

    def test_evaluation_agent_accepts_precomputed_dashboard_summaries(self) -> None:
        evaluation = build_strategy_evaluation_agent_summary(
            {"enabled": True},
            [],
            {},
            {},
            settlement_summary={"known_count": 12, "hit_rate": 0.5, "hit_rate_text": "50.0%", "summary_text": "precomputed settlements"},
            error_attribution={
                "top_reason": "precomputed_reason",
                "reason_counts": {"high_confidence_miss": 1},
                "miss_count": 1,
            },
            allowlist_summary={"hit_rate": 0.5, "hit_rate_text": "50.0%"},
            jc_feedback={"summary_text": "precomputed jc", "status_counts": {"watch": 1}},
            event_review={"sample_count": 1, "finishing_variance_count": 1, "control_gap_count": 0, "baseline_match_count": 10},
        )

        self.assertIn("样本 12", evaluation["summary_text"])
        self.assertIn("precomputed_reason", evaluation["summary_text"])
        self.assertEqual(evaluation["settlement_summary"]["summary_text"], "precomputed settlements")
        self.assertEqual(evaluation["jc_bucket_feedback"]["summary_text"], "precomputed jc")
        self.assertEqual(evaluation["statsbomb_event_review"]["sample_count"], 1)

    def test_statsbomb_fewshot_memory_monitor_tracks_coverage_and_gaps(self) -> None:
        memory = {
            "leakage_note": "post-match memory only",
            "items": [
                {
                    "labels": {
                        "is_hit": False,
                        "root_cause": "statsbomb_finishing_variance",
                        "tags": [
                            "statsbomb_post_match_review",
                            "strategy_miss",
                            "statsbomb_finishing_variance",
                            "xg_result_divergence",
                        ],
                    }
                },
                {
                    "labels": {
                        "is_hit": True,
                        "root_cause": "event_evidence_aligned",
                        "tags": [
                            "statsbomb_post_match_review",
                            "strategy_hit",
                            "event_control_gap",
                        ],
                    }
                },
            ],
        }
        current = {"matched_count": 1, "query_tags": ["statsbomb_finishing_variance", "strategy_miss"]}

        monitor = build_statsbomb_fewshot_memory_monitor(memory, current)

        self.assertEqual(monitor["sample_count"], 2)
        self.assertEqual(monitor["hit_count"], 1)
        self.assertEqual(monitor["miss_count"], 1)
        self.assertEqual(monitor["current_matched_count"], 1)
        self.assertEqual(monitor["status"], "active_match")
        self.assertIn("statsbomb_finishing_variance", monitor["covered_tags"])
        self.assertIn("xg_direction_failed", monitor["missing_tags"])
        self.assertEqual(monitor["leakage_note"], "post-match memory only")

    def test_statsbomb_fewshot_memory_quality_alerts_flag_gaps_and_current_miss(self) -> None:
        monitor = {
            "sample_count": 6,
            "current_matched_count": 0,
            "current_query_tags": ["statsbomb_finishing_variance", "strategy_miss"],
            "missing_tags": ["xg_direction_failed"],
            "tag_rows": [
                {"tag": "statsbomb_finishing_variance", "count": 5},
                {"tag": "event_control_gap", "count": 1},
            ],
            "root_rows": [
                {"root_cause": "statsbomb_finishing_variance", "count": 5},
                {"root_cause": "event_control_gap", "count": 1},
            ],
        }

        quality = build_statsbomb_fewshot_memory_quality_alerts(monitor, min_samples=5)

        self.assertEqual(quality["status"], "watch")
        self.assertGreaterEqual(quality["alert_count"], 3)
        self.assertIn("statsbomb_memory_no_current_match", quality["memory_tags"])
        self.assertIn("statsbomb_memory_tag_gap", quality["memory_tags"])

    def test_evaluation_agent_surfaces_statsbomb_memory_quality_alerts(self) -> None:
        settlements = [
            {
                "league": "UEFA Euro",
                "home_team": "Spain",
                "away_team": "Croatia",
                "statsbomb_event_summary": {
                    "team_stats": {
                        "Spain": {"xg": 1.12, "shots": 11, "goals": 3},
                        "Croatia": {"xg": 2.35, "shots": 16, "goals": 0},
                    },
                },
                "high_accuracy_strategy_items": [
                    {
                        "play_type": "market_1x2",
                        "pick": "AWAY",
                        "actual": "HOME",
                        "confidence": 0.70,
                        "min_confidence": 0.65,
                        "backtest_accuracy": 0.72,
                        "backtest_samples": 180,
                        "is_hit": False,
                    }
                ],
            }
        ]
        memory = {
            "items": [
                {
                    "labels": {
                        "is_hit": True,
                        "root_cause": "event_evidence_aligned",
                        "tags": ["strategy_hit"],
                    }
                }
            ],
        }

        evaluation = build_strategy_evaluation_agent_summary({"enabled": True}, settlements, {}, memory)

        self.assertEqual(evaluation["statsbomb_fewshot_monitor"]["current_matched_count"], 0)
        self.assertIn("statsbomb_memory_no_current_match", evaluation["memory_tags"])
        self.assertTrue(any("相似样本" in item["title"] for item in evaluation["recommendations"]))

    def test_statsbomb_fewshot_backfill_queue_builds_tasks_and_candidates(self) -> None:
        monitor = {
            "sample_count": 6,
            "current_matched_count": 0,
            "current_query_tags": ["statsbomb_finishing_variance", "strategy_miss"],
            "missing_tags": ["xg_direction_failed"],
        }
        quality = build_statsbomb_fewshot_memory_quality_alerts(
            {
                **monitor,
                "tag_rows": [{"tag": "statsbomb_finishing_variance", "count": 6}],
                "root_rows": [{"root_cause": "statsbomb_finishing_variance", "count": 6}],
            },
            min_samples=5,
        )
        baseline = {
            "items": [
                {
                    "match_id": "sb1",
                    "match_date": "2024-06-15",
                    "league": "UEFA Euro",
                    "home_team": "Spain",
                    "away_team": "Croatia",
                    "score": "3-0",
                    "home_xg": 1.12,
                    "away_xg": 2.35,
                    "home_shots": 11,
                    "away_shots": 16,
                    "goal_margin": 3,
                    "xg_margin": -1.23,
                    "finishing_variance": True,
                    "xg_aligned_with_score": False,
                    "shot_aligned_with_score": False,
                }
            ]
        }

        queue = build_statsbomb_fewshot_backfill_queue(monitor, quality, [], baseline)

        self.assertEqual(queue["status"], "ready")
        self.assertGreaterEqual(queue["task_count"], 2)
        self.assertGreaterEqual(queue["candidate_count"], 1)
        self.assertEqual(queue["health_status"], "attention")
        self.assertTrue(any(issue["code"] == "sample_count_low" for issue in queue["health_issues"]))
        self.assertIn("sample_count_low", queue["health_issue_codes"])
        self.assertIn("xg_direction_failed", queue["missing_labels"])
        self.assertTrue(queue["current_match_unmatched"])
        self.assertEqual(queue["workflow_status"]["summary"], "backfill_queue_only")
        self.assertTrue(any("xg_direction_failed" in row["matched_tags"] for row in queue["candidate_rows"]))
        self.assertTrue(any("required_tag_gap" in row["matched_health_issues"] for row in queue["candidate_rows"]))
        self.assertGreater(queue["candidate_rows"][0]["repair_score"], 0)
        self.assertTrue(queue["candidate_rows"][0]["repair_reasons"])
        self.assertTrue(queue["candidate_rows"][0]["priority_why"])
        self.assertEqual(queue["candidate_rows"][0]["flow_status"]["draft"], "pending")
        self.assertIn("post-match", queue["leakage_note"])

    def test_statsbomb_fewshot_backfill_queue_ranks_by_repair_value(self) -> None:
        monitor = {
            "sample_count": 3,
            "current_matched_count": 0,
            "current_query_tags": ["xg_direction_failed", "strategy_miss"],
            "missing_tags": ["statsbomb_finishing_variance"],
        }
        quality = {"alert_count": 0, "alerts": []}
        settlements = [
            {
                "match_id": "recent",
                "match_date": "2024-06-20",
                "league": "UEFA Euro",
                "home_team": "Recent",
                "away_team": "Case",
                "statsbomb_event_summary": {
                    "event_count": 3500,
                    "team_stats": {
                        "Recent": {"xg": 0.6, "shots": 7, "goals": 0},
                        "Case": {"xg": 1.5, "shots": 13, "goals": 1},
                    },
                },
                "high_accuracy_strategy_items": [
                    {"play_type": "market_1x2", "pick": "HOME", "actual": "AWAY", "is_hit": False}
                ],
            }
        ]
        baseline = {
            "items": [
                {
                    "match_id": "baseline",
                    "match_date": "2024-06-01",
                    "league": "UEFA Euro",
                    "home_team": "Baseline",
                    "away_team": "Case",
                    "backfill_tags": ["statsbomb_finishing_variance", "xg_result_divergence"],
                }
            ],
            "backfill_tag_index": {"statsbomb_finishing_variance": [0]},
        }

        queue = build_statsbomb_fewshot_backfill_queue(monitor, quality, settlements, baseline, limit=2)

        self.assertEqual(queue["candidate_rows"][0]["match_id"], "recent")
        self.assertGreater(
            queue["candidate_rows"][0]["repair_score"],
            queue["candidate_rows"][1]["repair_score"],
        )
        self.assertTrue(
            any("recent_settlement" in reason for reason in queue["candidate_rows"][0]["repair_reasons"])
        )

    def test_statsbomb_fewshot_backfill_queue_keeps_only_top_candidate_rows(self) -> None:
        monitor = {
            "sample_count": 3,
            "current_matched_count": 0,
            "current_query_tags": [],
            "missing_tags": ["xg_direction_failed"],
        }
        quality = {"alert_count": 0, "alerts": []}
        baseline = {
            "items": [
                {
                    "match_id": f"sb{index}",
                    "match_date": f"2024-06-{index + 1:02d}",
                    "league": "UEFA Euro",
                    "home_team": f"Home{index}",
                    "away_team": f"Away{index}",
                    "home_xg": 1.0,
                    "away_xg": 2.0,
                    "home_shots": 8,
                    "away_shots": 14,
                    "goal_margin": 1,
                    "finishing_variance": True,
                    "xg_aligned_with_score": False,
                    "shot_aligned_with_score": False,
                }
                for index in range(12)
            ]
        }

        queue = build_statsbomb_fewshot_backfill_queue(monitor, quality, [], baseline, limit=3)

        self.assertEqual(queue["candidate_generation"], "full")
        self.assertEqual(queue["candidate_count"], 12)
        self.assertEqual(len(queue["candidate_rows"]), 3)
        self.assertIn("候选 12", queue["summary_text"])
        self.assertEqual([row["match_id"] for row in queue["candidate_rows"]], ["sb0", "sb1", "sb2"])

    def test_statsbomb_fewshot_backfill_queue_uses_baseline_tag_index(self) -> None:
        monitor = {
            "sample_count": 3,
            "current_matched_count": 0,
            "current_query_tags": [],
            "missing_tags": ["xg_direction_failed"],
        }
        quality = {"alert_count": 0, "alerts": []}
        baseline = {
            "backfill_tag_index": {"xg_direction_failed": [1]},
            "items": [
                {
                    "match_id": "irrelevant",
                    "match_date": "2024-06-01",
                    "league": "UEFA Euro",
                    "home_team": "A",
                    "away_team": "B",
                    "backfill_tags": ["strategy_hit"],
                },
                {
                    "match_id": "target",
                    "match_date": "2024-06-02",
                    "league": "UEFA Euro",
                    "home_team": "C",
                    "away_team": "D",
                    "backfill_tags": ["xg_direction_failed", "strategy_miss"],
                },
            ],
        }

        queue = build_statsbomb_fewshot_backfill_queue(monitor, quality, [], baseline, limit=5)

        self.assertEqual(queue["candidate_count"], 1)
        self.assertEqual([row["match_id"] for row in queue["candidate_rows"]], ["target"])
        self.assertIn("xg_direction_failed", queue["candidate_rows"][0]["matched_tags"])

    def test_statsbomb_fewshot_backfill_queue_can_defer_candidates(self) -> None:
        monitor = {
            "sample_count": 3,
            "missing_tags": ["xg_direction_failed"],
            "current_query_tags": [],
            "current_matched_count": 0,
        }
        quality = {"alert_count": 0, "alerts": []}
        baseline = {
            "items": [
                {
                    "match_id": "sb1",
                    "match_date": "2024-06-15",
                    "league": "UEFA Euro",
                    "home_team": "Spain",
                    "away_team": "Croatia",
                    "home_xg": 1.12,
                    "away_xg": 2.35,
                    "home_shots": 11,
                    "away_shots": 16,
                    "goal_margin": 3,
                    "finishing_variance": True,
                    "xg_aligned_with_score": False,
                    "shot_aligned_with_score": False,
                }
            ]
        }

        queue = build_statsbomb_fewshot_backfill_queue(monitor, quality, [], baseline, include_candidates=False)

        self.assertEqual(queue["status"], "ready")
        self.assertEqual(queue["candidate_generation"], "deferred")
        self.assertEqual(queue["candidate_count"], 0)
        self.assertEqual(queue["candidate_rows"], [])
        self.assertGreaterEqual(queue["task_count"], 1)

    def test_statsbomb_fewshot_backfill_report_exports_queue(self) -> None:
        queue = {
            "status": "ready",
            "summary_text": "补样任务 1 | 候选 1 | 目标标签 1",
            "health_summary": "attention | issues 1 | samples 6",
            "health_issues": [{"code": "required_tag_gap", "severity": "medium", "recommendation": "cover missing tags"}],
            "missing_labels": ["xg_direction_failed"],
            "current_query_labels": ["xg_direction_failed", "strategy_miss"],
            "current_match_unmatched": True,
            "workflow_status": {"draft": "pending", "merge": "pending", "apply": "pending", "summary": "backfill_queue_only"},
            "leakage_note": "post-match only",
            "tasks": [
                {
                    "priority": 95,
                    "title": "补充当前错因相似样本",
                    "target_tags": ["xg_direction_failed"],
                    "body": "当前错因没有命中历史记忆。",
                }
            ],
            "candidate_rows": [
                {
                    "priority_score": 41,
                    "repair_score": 88,
                    "priority_why": ["覆盖缺口标签: xg_direction_failed", "当前必需标签缺口，需优先补齐"],
                    "repair_reasons": ["required_tag_gap +25", "missing_tags +35"],
                    "source": "statsbomb_baseline",
                    "match_date": "2024-06-15",
                    "league": "UEFA Euro",
                    "title": "2024-06-15 | UEFA Euro | Spain vs Croatia",
                    "matched_tags": ["xg_direction_failed"],
                    "matched_health_issues": ["required_tag_gap"],
                    "flow_status": {"draft": "pending", "merge": "pending", "apply": "pending", "summary": "backfill_queued_only"},
                    "tags": ["statsbomb_post_match_review", "xg_direction_failed"],
                }
            ],
        }

        lines = build_statsbomb_fewshot_backfill_report_lines(queue, generated_at=datetime(2026, 5, 10, 22, 15, 30))
        payload = "\n".join(lines)

        self.assertEqual(
            build_statsbomb_fewshot_backfill_report_filename(datetime(2026, 5, 10, 22, 15, 30)),
            "statsbomb_fewshot_backfill_20260510_221530.md",
        )
        self.assertIn("StatsBomb Few-shot 补样队列", payload)
        self.assertIn("补充当前错因相似样本", payload)
        self.assertIn("Spain vs Croatia", payload)
        self.assertIn("缺口与健康驱动", payload)
        self.assertIn("当前比赛是否命中历史样本: 否", payload)
        self.assertIn("流程状态: draft=pending | merge=pending | apply=pending", payload)
        self.assertIn("required_tag_gap", payload)
        self.assertIn("覆盖缺口标签: xg_direction_failed", payload)
        self.assertIn("post-match only", payload)

    def test_statsbomb_fewshot_draft_payload_builds_reviewable_samples(self) -> None:
        queue = {
            "summary_text": "补样任务 1 | 候选 1 | 目标标签 1",
            "candidate_rows": [
                {
                    "source": "statsbomb_baseline",
                    "match_id": "sb1",
                    "title": "2024-06-15 | UEFA Euro | Spain vs Croatia",
                    "matched_tags": ["xg_direction_failed"],
                    "matched_health_issues": ["required_tag_gap"],
                    "repair_score": 88,
                    "repair_reasons": ["required_tag_gap +25", "missing_tags +35"],
                    "tags": ["statsbomb_post_match_review", "xg_direction_failed"],
                }
            ],
        }
        baseline = {
            "items": [
                {
                    "match_id": "sb1",
                    "source_match_id": "sb1",
                    "match_date": "2024-06-15",
                    "league": "UEFA Euro",
                    "season": "2024",
                    "home_team": "Spain",
                    "away_team": "Croatia",
                    "score": "3-0",
                    "home_xg": 1.12,
                    "away_xg": 2.35,
                    "home_shots": 11,
                    "away_shots": 16,
                    "goal_margin": 3,
                    "xg_margin": -1.23,
                    "shot_margin": -5,
                    "event_count": 3500,
                    "finishing_variance": True,
                    "xg_aligned_with_score": False,
                    "shot_aligned_with_score": False,
                }
            ]
        }

        payload = build_statsbomb_fewshot_draft_payload(
            queue,
            baseline,
            generated_at=datetime(2026, 5, 10, 22, 15, 30),
        )
        lines = build_statsbomb_fewshot_draft_review_lines(payload)
        review_text = "\n".join(lines)

        self.assertEqual(
            build_statsbomb_fewshot_draft_filename(datetime(2026, 5, 10, 22, 15, 30)),
            "statsbomb_fewshot_draft_20260510_221530.json",
        )
        self.assertEqual(
            build_statsbomb_fewshot_draft_review_filename(datetime(2026, 5, 10, 22, 15, 30)),
            "statsbomb_fewshot_draft_review_20260510_221530.md",
        )
        self.assertEqual(payload["summary"]["draft_count"], 1)
        self.assertEqual(payload["items"][0]["review_status"], "draft")
        self.assertIn("xg_direction_failed", payload["items"][0]["labels"]["tags"])
        self.assertIn("required_tag_gap", payload["items"][0]["meta"]["matched_health_issues"])
        self.assertEqual(payload["items"][0]["meta"]["repair_score"], 88)
        self.assertIn("required_tag_gap +25", payload["items"][0]["meta"]["repair_reasons"])
        self.assertEqual(payload["summary"]["top_repair_score"], 88)
        self.assertEqual(payload["summary"]["health_issue_counts"]["required_tag_gap"], 1)
        self.assertIn("validation", payload)
        self.assertIn("required_tag_gap", review_text)
        self.assertIn("修复评分", review_text)
        self.assertIn("required_tag_gap +25", review_text)
        self.assertIn("StatsBomb Few-shot 草稿审查", review_text)
        self.assertIn("赛前预测特征", review_text)

    def test_statsbomb_fewshot_draft_payload_uses_recent_candidate_without_baseline(self) -> None:
        monitor = {
            "sample_count": 3,
            "current_matched_count": 0,
            "current_query_tags": ["xg_direction_failed", "strategy_miss"],
            "missing_tags": [],
        }
        quality = {"alert_count": 0, "alerts": []}
        settlements = [
            {
                "match_id": "recent",
                "match_date": "2024-06-20",
                "league": "UEFA Euro",
                "home_team": "Recent",
                "away_team": "Case",
                "statsbomb_event_summary": {
                    "event_count": 3500,
                    "team_stats": {
                        "Recent": {"xg": 0.6, "shots": 7, "goals": 0},
                        "Case": {"xg": 1.5, "shots": 13, "goals": 1},
                    },
                },
                "high_accuracy_strategy_items": [
                    {"play_type": "market_1x2", "pick": "HOME", "actual": "AWAY", "is_hit": False}
                ],
            }
        ]
        queue = build_statsbomb_fewshot_backfill_queue(monitor, quality, settlements, {}, limit=2)

        payload = build_statsbomb_fewshot_draft_payload(queue, {}, generated_at=datetime(2026, 5, 10, 22, 15, 30))

        self.assertEqual(payload["summary"]["draft_count"], 1)
        self.assertEqual(payload["summary"]["skipped_count"], 0)
        self.assertEqual(payload["items"][0]["meta"]["match_id"], "recent")
        self.assertEqual(payload["items"][0]["meta"]["candidate_source"], "recent_settlement")
        self.assertGreater(payload["items"][0]["meta"]["repair_score"], 0)
        self.assertIn("recent_settlement +15", payload["items"][0]["meta"]["repair_reasons"])
        self.assertIn("补样优先级", payload["items"][0]["prompt"])

    def test_statsbomb_fewshot_draft_validation_blocks_invalid_samples(self) -> None:
        payload = {
            "items": [
                {
                    "id": "draft:1",
                    "review_status": "draft",
                    "prompt": "review",
                    "completion": "done",
                    "labels": {"simulated_pick": "HOME", "actual": "AWAY", "is_hit": False, "root_cause": "event_result_divergence", "tags": ["strategy_miss"]},
                    "features": {"home_xg": 1.0},
                    "meta": {"match_date": "2024-06-15", "league": "UEFA Euro", "home_team": "Spain", "away_team": "Croatia", "score": "3-0"},
                },
                {
                    "id": "draft:1",
                    "review_status": "final",
                    "prompt": "review",
                    "completion": "done",
                    "labels": {"simulated_pick": "HOME", "actual": "HOME", "is_hit": True, "root_cause": "event_evidence_aligned", "tags": ["statsbomb_post_match_review", "strategy_hit"]},
                    "features": {"home_xg": 1.0, "away_xg": 0.5, "xg_margin": 0.5, "home_shots": 10, "away_shots": 5, "shot_margin": 5, "event_count": 3000},
                    "meta": {"match_date": "2024-06-16", "league": "UEFA Euro", "home_team": "A", "away_team": "B", "score": "1-0"},
                },
            ]
        }

        validation = validate_statsbomb_fewshot_draft_payload(payload)

        self.assertEqual(validation["status"], "blocked")
        self.assertGreater(validation["high_count"], 0)
        self.assertTrue(any(issue["code"] == "duplicate_id" for issue in validation["issues"]))
        self.assertTrue(any(issue["code"] == "missing_post_match_tag" for issue in validation["issues"]))

    def test_statsbomb_fewshot_merge_plan_skips_existing_memory(self) -> None:
        draft_payload = {
            "validation": {"high_count": 0, "medium_count": 1, "summary_text": "草稿校验 review"},
            "items": [
                {
                    "id": "draft:old",
                    "review_status": "draft",
                    "prompt": "review",
                    "completion": "done",
                    "labels": {"simulated_pick": "HOME", "actual": "HOME", "is_hit": True, "root_cause": "event_evidence_aligned", "tags": ["statsbomb_post_match_review", "strategy_hit"]},
                    "features": {"home_xg": 1.0, "away_xg": 0.5, "xg_margin": 0.5, "home_shots": 10, "away_shots": 5, "shot_margin": 5, "event_count": 3000},
                    "meta": {"match_id": "m1", "match_date": "2024-06-15", "league": "UEFA Euro", "home_team": "Spain", "away_team": "Croatia", "score": "3-0"},
                },
                {
                    "id": "draft:new",
                    "review_status": "draft",
                    "prompt": "review",
                    "completion": "done",
                    "labels": {"simulated_pick": "AWAY", "actual": "HOME", "is_hit": False, "root_cause": "statsbomb_finishing_variance", "tags": ["statsbomb_post_match_review", "strategy_miss", "xg_direction_failed"]},
                    "features": {"home_xg": 1.0, "away_xg": 1.5, "xg_margin": -0.5, "home_shots": 10, "away_shots": 15, "shot_margin": -5, "event_count": 3000},
                    "meta": {
                        "match_id": "m2",
                        "match_date": "2024-06-16",
                        "league": "UEFA Euro",
                        "home_team": "A",
                        "away_team": "B",
                        "score": "1-0",
                        "matched_health_issues": ["required_tag_gap"],
                    },
                },
            ],
        }
        memory = {"items": [{"id": "official:1", "meta": {"match_id": "m1", "match_date": "2024-06-15", "league": "UEFA Euro", "home_team": "Spain", "away_team": "Croatia"}}]}

        plan = build_statsbomb_fewshot_merge_plan(draft_payload, memory)
        lines = build_statsbomb_fewshot_merge_plan_lines(plan)
        payload = "\n".join(lines)

        self.assertEqual(plan["status"], "review")
        self.assertEqual(plan["mergeable_count"], 1)
        self.assertEqual(plan["skipped_count"], 1)
        self.assertEqual(plan["mergeable_items"][0]["health_issues"], ["required_tag_gap"])
        self.assertTrue(any(row["reason"] == "already_in_memory" for row in plan["skipped_rows"]))
        self.assertEqual(
            build_statsbomb_fewshot_merge_plan_filename(datetime(2026, 5, 10, 22, 15, 30)),
            "statsbomb_fewshot_merge_plan_20260510_221530.md",
        )
        self.assertIn("StatsBomb Few-shot 合并计划", payload)
        self.assertIn("draft:new", payload)
        self.assertIn("required_tag_gap", payload)

    def test_statsbomb_fewshot_merge_plan_blocks_high_validation(self) -> None:
        draft_payload = {
            "validation": {"high_count": 1, "medium_count": 0, "summary_text": "草稿校验 blocked"},
            "items": [{"id": "draft:bad", "meta": {"home_team": "A"}}],
        }

        plan = build_statsbomb_fewshot_merge_plan(draft_payload, {})

        self.assertEqual(plan["status"], "blocked")
        self.assertEqual(plan["mergeable_count"], 0)

    def test_statsbomb_fewshot_merge_bundle_exports_only_mergeable_items(self) -> None:
        plan = {
            "status": "review",
            "summary_text": "合并计划 review | 可合并 1 | 跳过 1 | 现有 2",
            "skipped_count": 1,
            "existing_count": 2,
            "validation": {"summary_text": "草稿校验 review"},
            "mergeable_items": [
                {
                    "id": "draft:new",
                    "title": "2024-06-16 | UEFA Euro | A vs B",
                    "root_cause": "statsbomb_finishing_variance",
                    "tags": ["statsbomb_post_match_review", "strategy_miss"],
                    "item": {
                        "id": "draft:new",
                        "review_status": "draft",
                        "labels": {"root_cause": "statsbomb_finishing_variance", "tags": ["statsbomb_post_match_review", "strategy_miss"]},
                        "meta": {
                            "match_date": "2024-06-16",
                            "league": "UEFA Euro",
                            "home_team": "A",
                            "away_team": "B",
                            "matched_health_issues": ["required_tag_gap"],
                        },
                    },
                }
            ],
            "skipped_rows": [{"id": "draft:old", "title": "old", "reason": "already_in_memory"}],
        }

        bundle = build_statsbomb_fewshot_merge_bundle(plan, generated_at=datetime(2026, 5, 10, 22, 15, 30))
        lines = build_statsbomb_fewshot_merge_bundle_report_lines(bundle)
        payload = "\n".join(lines)

        self.assertEqual(bundle["status"], "pending_manual_apply")
        self.assertEqual(bundle["summary"]["bundle_count"], 1)
        self.assertEqual(bundle["summary"]["health_issue_counts"]["required_tag_gap"], 1)
        self.assertTrue(bundle["approval_required"])
        self.assertEqual(
            build_statsbomb_fewshot_merge_bundle_filename(datetime(2026, 5, 10, 22, 15, 30)),
            "statsbomb_fewshot_merge_bundle_20260510_221530.json",
        )
        self.assertEqual(
            build_statsbomb_fewshot_merge_bundle_report_filename(datetime(2026, 5, 10, 22, 15, 30)),
            "statsbomb_fewshot_merge_bundle_review_20260510_221530.md",
        )
        self.assertIn("StatsBomb Few-shot 合并可应用包", payload)
        self.assertIn("draft:new", payload)
        self.assertIn("required_tag_gap", payload)

    def test_statsbomb_fewshot_merge_apply_preview_dry_run_checks_duplicates(self) -> None:
        item = {
            "id": "draft:new",
            "review_status": "draft",
            "prompt": "review",
            "completion": "done",
            "labels": {
                "simulated_pick": "HOME",
                "actual": "HOME",
                "is_hit": True,
                "root_cause": "event_evidence_aligned",
                "tags": ["statsbomb_post_match_review", "strategy_hit"],
            },
            "features": {
                "home_xg": 1.0,
                "away_xg": 0.5,
                "xg_margin": 0.5,
                "home_shots": 10,
                "away_shots": 5,
                "shot_margin": 5,
                "event_count": 3000,
            },
            "meta": {
                "match_id": "m2",
                "match_date": "2024-06-16",
                "league": "UEFA Euro",
                "home_team": "A",
                "away_team": "B",
                "score": "1-0",
                "matched_health_issues": ["required_tag_gap"],
            },
        }
        existing = {"items": [{"id": "official:1", "meta": {"match_id": "m1"}}]}
        bundle = {
            "purpose": "manual_apply_bundle",
            "status": "pending_manual_apply",
            "approval_required": True,
            "items": [
                item,
                {**item, "id": "draft:old", "meta": {**item["meta"], "match_id": "m1"}},
                {**item, "id": "draft:dupe"},
            ],
        }

        preview = build_statsbomb_fewshot_merge_apply_preview(bundle, existing, generated_at=datetime(2026, 5, 10, 22, 15, 30))
        lines = build_statsbomb_fewshot_merge_apply_preview_lines(preview)
        payload = "\n".join(lines)

        self.assertEqual(preview["status"], "ready_for_manual_apply")
        self.assertTrue(preview["dry_run"])
        self.assertTrue(preview["no_state_write"])
        self.assertEqual(preview["summary"]["append_count"], 1)
        self.assertEqual(preview["summary"]["skipped_count"], 2)
        self.assertTrue(any(row["reason"] == "already_in_memory" for row in preview["skipped_rows"]))
        self.assertTrue(any(row["reason"] == "duplicate_in_bundle" for row in preview["skipped_rows"]))
        self.assertEqual(
            build_statsbomb_fewshot_merge_apply_preview_filename(datetime(2026, 5, 10, 22, 15, 30)),
            "statsbomb_fewshot_merge_apply_preview_20260510_221530.md",
        )
        self.assertIn("StatsBomb Few-shot Merge Apply Preview", payload)
        self.assertIn("draft:new", payload)

    def test_statsbomb_fewshot_merge_apply_preview_blocks_invalid_bundle(self) -> None:
        preview = build_statsbomb_fewshot_merge_apply_preview(
            {"purpose": "wrong", "status": "ready", "approval_required": False, "items": []},
            {},
        )

        self.assertEqual(preview["status"], "blocked")
        self.assertEqual(preview["summary"]["append_count"], 0)
        self.assertGreater(preview["summary"]["high_count"], 0)

    def test_statsbomb_fewshot_merge_apply_result_builds_updated_memory(self) -> None:
        item = {
            "id": "draft:new",
            "review_status": "draft",
            "prompt": "review",
            "completion": "done",
            "labels": {
                "simulated_pick": "AWAY",
                "actual": "HOME",
                "is_hit": False,
                "root_cause": "statsbomb_finishing_variance",
                "tags": ["statsbomb_post_match_review", "strategy_miss", "xg_direction_failed"],
            },
            "features": {
                "home_xg": 1.0,
                "away_xg": 1.5,
                "xg_margin": -0.5,
                "home_shots": 10,
                "away_shots": 15,
                "shot_margin": -5,
                "event_count": 3000,
            },
            "meta": {
                "match_id": "m2",
                "match_date": "2024-06-16",
                "league": "UEFA Euro",
                "home_team": "A",
                "away_team": "B",
                "score": "1-0",
                "matched_health_issues": ["required_tag_gap"],
            },
        }
        existing = {
            "source": "StatsBomb Open Data event baseline",
            "purpose": "evaluation_agent_fewshot_post_match_review",
            "summary": {"sample_count": 1, "tag_counts": {"strategy_hit": 1}},
            "items": [
                {
                    "id": "official:1",
                    "labels": {"is_hit": True, "tags": ["statsbomb_post_match_review", "strategy_hit"]},
                    "meta": {"match_id": "m1"},
                }
            ],
        }
        bundle = {
            "purpose": "manual_apply_bundle",
            "status": "pending_manual_apply",
            "approval_required": True,
            "items": [item],
        }

        result = build_statsbomb_fewshot_merge_apply_result(bundle, existing, generated_at=datetime(2026, 5, 10, 22, 15, 30))
        lines = build_statsbomb_fewshot_merge_apply_report_lines(result)
        payload = "\n".join(lines)
        updated_memory = result["updated_memory"]

        self.assertEqual(result["status"], "ready_to_write")
        self.assertEqual(result["summary"]["applied_count"], 1)
        self.assertEqual(result["summary"]["final_count"], 2)
        self.assertEqual(result["summary"]["health_issue_counts"]["required_tag_gap"], 1)
        self.assertEqual(updated_memory["summary"]["sample_count"], 2)
        self.assertEqual(updated_memory["summary"]["miss_count"], 1)
        self.assertEqual(updated_memory["last_manual_apply"]["health_issue_counts"]["required_tag_gap"], 1)
        self.assertEqual(updated_memory["items"][1]["review_status"], "approved")
        self.assertEqual(
            build_statsbomb_fewshot_merge_apply_report_filename(datetime(2026, 5, 10, 22, 15, 30)),
            "statsbomb_fewshot_merge_applied_20260510_221530.md",
        )
        self.assertIn("StatsBomb Few-shot Merge Apply", payload)
        self.assertIn("draft:new", payload)
        self.assertIn("required_tag_gap", payload)

    def test_statsbomb_fewshot_memory_rollback_preview_validates_backup(self) -> None:
        backup = {
            "updated_at": "2026-05-10 22:15:30",
            "purpose": "evaluation_agent_fewshot_post_match_review",
            "leakage_note": "post-match only",
            "items": [
                {
                    "id": "official:old",
                    "review_status": "approved",
                    "prompt": "review",
                    "completion": "done",
                    "labels": {
                        "simulated_pick": "HOME",
                        "actual": "HOME",
                        "is_hit": True,
                        "root_cause": "event_evidence_aligned",
                        "tags": ["statsbomb_post_match_review", "strategy_hit"],
                    },
                    "features": {
                        "home_xg": 1.0,
                        "away_xg": 0.5,
                        "xg_margin": 0.5,
                        "home_shots": 10,
                        "away_shots": 5,
                        "shot_margin": 5,
                        "event_count": 3000,
                    },
                    "meta": {
                        "match_id": "m1",
                        "match_date": "2024-06-15",
                        "league": "UEFA Euro",
                        "home_team": "A",
                        "away_team": "B",
                        "score": "1-0",
                    },
                }
            ],
        }
        current = {"updated_at": "2026-05-10 23:00:00", "items": [backup["items"][0], {**backup["items"][0], "id": "official:new", "meta": {**backup["items"][0]["meta"], "match_id": "m2"}}]}

        preview = build_statsbomb_fewshot_memory_rollback_preview(
            backup,
            current,
            backup_name="statsbomb_sandbox_fewshot_samples.backup_20260510_221530.json",
            generated_at=datetime(2026, 5, 10, 23, 30, 0),
        )
        lines = build_statsbomb_fewshot_memory_rollback_report_lines(preview)
        payload = "\n".join(lines)

        self.assertEqual(preview["status"], "ready_to_restore")
        self.assertEqual(preview["summary"]["backup_count"], 1)
        self.assertEqual(preview["summary"]["current_count"], 2)
        self.assertEqual(preview["summary"]["delta"], -1)
        self.assertEqual(
            build_statsbomb_fewshot_memory_rollback_report_filename(datetime(2026, 5, 10, 23, 30, 0)),
            "statsbomb_fewshot_memory_rollback_20260510_233000.md",
        )
        self.assertIn("StatsBomb Few-shot Memory Rollback", payload)
        self.assertIn("ready_to_restore", payload)

    def test_statsbomb_fewshot_memory_rollback_preview_blocks_invalid_backup(self) -> None:
        preview = build_statsbomb_fewshot_memory_rollback_preview({}, {"items": []})

        self.assertEqual(preview["status"], "blocked")
        self.assertGreater(preview["summary"]["high_count"], 0)

    def test_statsbomb_fewshot_memory_audit_report_summarizes_state_and_backups(self) -> None:
        memory = {
            "updated_at": "2026-05-10 22:15:30",
            "leakage_note": "post-match only",
            "last_manual_apply": {"applied_at": "2026-05-10 22:20:00", "applied_count": 2},
            "items": [
                {
                    "labels": {
                        "is_hit": True,
                        "root_cause": "event_evidence_aligned",
                        "tags": ["statsbomb_post_match_review", "strategy_hit"],
                    }
                },
                {
                    "labels": {
                        "is_hit": False,
                        "root_cause": "statsbomb_finishing_variance",
                        "tags": ["statsbomb_post_match_review", "strategy_miss", "xg_direction_failed"],
                    }
                },
            ],
        }
        monitor = build_statsbomb_fewshot_memory_monitor(memory, {})
        quality = build_statsbomb_fewshot_memory_quality_alerts(monitor, min_samples=5)

        audit = build_statsbomb_fewshot_memory_audit_report(
            memory,
            monitor,
            quality,
            backup_rows=[{"name": "statsbomb_sandbox_fewshot_samples.backup_20260510_221530.json", "size": 123, "modified_at": "2026-05-10 22:15:30"}],
            operation_rows=[{"name": "statsbomb_fewshot_merge_applied_20260510_222000.md", "type": "apply", "modified_at": "2026-05-10 22:20:00"}],
            generated_at=datetime(2026, 5, 10, 23, 45, 0),
        )
        lines = build_statsbomb_fewshot_memory_audit_report_lines(audit)
        payload = "\n".join(lines)

        self.assertEqual(audit["status"], "attention")
        self.assertEqual(audit["summary"]["sample_count"], 2)
        self.assertEqual(audit["summary"]["backup_count"], 1)
        self.assertEqual(audit["summary"]["operation_count"], 1)
        self.assertGreater(audit["summary"]["health_issue_count"], 0)
        self.assertEqual(audit["summary"]["last_manual_apply_count"], 2)
        self.assertEqual(
            build_statsbomb_fewshot_memory_audit_report_filename(datetime(2026, 5, 10, 23, 45, 0)),
            "statsbomb_fewshot_memory_audit_20260510_234500.md",
        )
        self.assertIn("StatsBomb Few-shot Memory Audit", payload)
        self.assertIn("Health Issues", payload)
        self.assertIn("statsbomb_sandbox_fewshot_samples.backup_20260510_221530.json", payload)

    def test_statsbomb_fewshot_memory_audit_report_flags_missing_backup(self) -> None:
        memory = {
            "items": [
                {
                    "labels": {
                        "is_hit": True,
                        "root_cause": "event_evidence_aligned",
                        "tags": [
                            "statsbomb_post_match_review",
                            "statsbomb_finishing_variance",
                            "event_control_gap",
                            "xg_result_divergence",
                            "shot_result_divergence",
                            "xg_direction_failed",
                            "strategy_miss",
                            "strategy_hit",
                        ],
                    }
                }
                for _ in range(20)
            ],
        }
        monitor = build_statsbomb_fewshot_memory_monitor(memory, {})
        quality = build_statsbomb_fewshot_memory_quality_alerts(monitor, min_samples=5)

        audit = build_statsbomb_fewshot_memory_audit_report(memory, monitor, quality)

        self.assertEqual(audit["status"], "attention")
        self.assertTrue(any(issue["code"] == "backup_missing" for issue in audit["health_issues"]))

    def test_high_accuracy_dashboard_exposes_statsbomb_backfill_queue(self) -> None:
        memory = {
            "items": [
                {
                    "labels": {
                        "is_hit": True,
                        "root_cause": "event_evidence_aligned",
                        "tags": ["strategy_hit"],
                    }
                }
            ],
        }
        baseline = {
            "items": [
                {
                    "match_id": "sb1",
                    "match_date": "2024-06-15",
                    "league": "UEFA Euro",
                    "home_team": "Spain",
                    "away_team": "Croatia",
                    "score": "3-0",
                    "home_xg": 1.12,
                    "away_xg": 2.35,
                    "home_shots": 11,
                    "away_shots": 16,
                    "goal_margin": 3,
                    "xg_margin": -1.23,
                    "finishing_variance": True,
                    "xg_aligned_with_score": False,
                    "shot_aligned_with_score": False,
                }
            ]
        }

        dashboard = build_high_accuracy_strategy_dashboard({"enabled": True}, [], [], baseline, memory)

        self.assertIn("statsbomb_backfill_queue", dashboard)
        self.assertEqual(dashboard["statsbomb_backfill_queue"]["candidate_generation"], "deferred")
        self.assertEqual(dashboard["statsbomb_backfill_queue"]["candidate_rows"], [])
        self.assertGreaterEqual(dashboard["statsbomb_backfill_queue"]["task_count"], 1)

        full_dashboard = build_high_accuracy_strategy_dashboard(
            {"enabled": True},
            [],
            [],
            baseline,
            memory,
            include_statsbomb_backfill_candidates=True,
        )
        self.assertEqual(full_dashboard["statsbomb_backfill_queue"]["candidate_generation"], "full")
        self.assertGreaterEqual(full_dashboard["statsbomb_backfill_queue"]["candidate_count"], 1)

    def test_high_accuracy_dashboard_exposes_statsbomb_fewshot_monitor(self) -> None:
        memory = {
            "items": [
                {
                    "labels": {
                        "is_hit": False,
                        "root_cause": "statsbomb_finishing_variance",
                        "tags": ["strategy_miss", "statsbomb_finishing_variance"],
                    }
                }
            ],
        }

        dashboard = build_high_accuracy_strategy_dashboard({"enabled": True}, [], [], {}, memory)

        monitor = dashboard["statsbomb_fewshot_monitor"]
        self.assertEqual(monitor["sample_count"], 1)
        self.assertEqual(monitor["miss_count"], 1)
        self.assertIn("statsbomb_finishing_variance", monitor["covered_tags"])

    def test_high_accuracy_dashboard_exposes_statsbomb_fewshot_health_metric(self) -> None:
        memory = {"items": [{"labels": {"is_hit": True, "tags": ["strategy_hit"], "root_cause": "event_evidence_aligned"}}]}

        dashboard = build_high_accuracy_strategy_dashboard({"enabled": True}, [], [], {}, memory)
        metrics = {item["label"]: item for item in dashboard["metrics"]}

        self.assertIn("SB Health", metrics)
        self.assertIn("statsbomb_fewshot_health", dashboard)
        self.assertEqual(dashboard["statsbomb_fewshot_health"]["status"], "attention")
        self.assertTrue(any(issue["code"] == "sample_count_low" for issue in dashboard["statsbomb_fewshot_health"]["issues"]))
        self.assertEqual(metrics["SB Health"]["tone"], "warning")

    def test_statsbomb_fewshot_health_driver_summary_tracks_active_queue_and_apply(self) -> None:
        health = {
            "issues": [
                {
                    "code": "required_tag_gap",
                    "severity": "medium",
                    "title": "Missing tag",
                    "recommendation": "Add tag coverage",
                }
            ]
        }
        queue = {
            "candidate_rows": [
                {"matched_health_issues": ["required_tag_gap", "sample_count_low"]},
                {"matched_health_issues": ["required_tag_gap"]},
            ]
        }
        memory = {
            "last_manual_apply": {
                "health_issue_counts": {
                    "required_tag_gap": 1,
                }
            }
        }

        summary = build_statsbomb_fewshot_health_driver_summary(health, queue, memory)

        self.assertEqual(summary["status"], "attention")
        self.assertEqual(summary["active_driver_counts"]["required_tag_gap"], 1)
        self.assertEqual(summary["backfill_driver_counts"]["required_tag_gap"], 2)
        self.assertEqual(summary["last_apply_driver_counts"]["required_tag_gap"], 1)
        self.assertTrue(any(row["kind"] == "active_issue" for row in summary["rows"]))
        self.assertIn("required_tag_gap", summary["summary_text"])

    def test_high_accuracy_dashboard_exposes_statsbomb_health_drivers(self) -> None:
        memory = {
            "last_manual_apply": {"health_issue_counts": {"required_tag_gap": 1}},
            "items": [
                {
                    "labels": {
                        "is_hit": True,
                        "tags": ["strategy_hit"],
                        "root_cause": "event_evidence_aligned",
                    }
                }
            ],
        }

        dashboard = build_high_accuracy_strategy_dashboard({"enabled": True}, [], [], {}, memory)
        metrics = {item["label"]: item for item in dashboard["metrics"]}

        self.assertIn("SB Drivers", metrics)
        self.assertIn("statsbomb_fewshot_health_drivers", dashboard)
        self.assertIn("required_tag_gap", dashboard["statsbomb_fewshot_health_drivers"]["summary_text"])
        self.assertTrue(dashboard["statsbomb_fewshot_health_drivers"]["rows"])

    def test_statsbomb_fewshot_memory_health_can_ignore_unknown_backup_count(self) -> None:
        monitor = {
            "sample_count": 20,
            "missing_tags": [],
        }
        quality = {"alert_count": 0, "alerts": []}

        health = build_statsbomb_fewshot_memory_health_summary(monitor, quality)

        self.assertEqual(health["status"], "healthy")
        self.assertFalse(any(issue["code"] == "backup_missing" for issue in health["issues"]))

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
                    "statsbomb_event_summary": {
                        "event_count": 3000,
                        "team_stats": {
                            "A": {"xg": 0.5, "shots": 6, "goals": 0},
                            "B": {"xg": 1.8, "shots": 14, "goals": 2},
                        },
                    },
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
        self.assertIn("StatsBomb \u8d5b\u540e\u4e8b\u4ef6\u590d\u76d8", payload_with_review)
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

    def test_strategy_release_recovery_loop_merges_current_snapshot_and_settlement_state(self) -> None:
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
            match_date="2026-05-08",
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
                    "strategy_admission": {"decision": "allow", "top_play": "market_1x2", "top_pick": "home", "top_confidence": 0.76},
                    "strategy_allowlist": {"decision": "allow", "file": "strategy_allowlist_a.md", "exported_at": "2026-05-09 17:30:45"},
                },
            },
            {
                "match": match_b,
                "prediction": {
                    "recommendation": "draw",
                    "confidence": 0.68,
                    "risk_level": "MEDIUM",
                    "strategy_admission": {"decision": "allow", "top_play": "market_1x2", "top_pick": "draw", "top_confidence": 0.69},
                },
            },
        ]
        snapshot_only_id = "snap-only"
        snapshots = {
            match_a.match_id: {
                "match": {"match_date": "2026-05-09", "match_time": "21:00", "league": "L1", "home_team": "A", "away_team": "B"},
                "prediction": {"recommendation": "home", "confidence": 0.72, "risk_level": "LOW"},
                "strategy_allowlist": {"decision": "allow", "file": "strategy_allowlist_a.md", "exported_at": "2026-05-09 17:30:45"},
            },
            snapshot_only_id: {
                "match": {"match_id": snapshot_only_id, "match_date": "2026-05-08", "match_time": "20:00", "league": "L3", "home_team": "E", "away_team": "F"},
                "prediction": {"recommendation": "away", "confidence": 0.66, "risk_level": "LOW"},
                "strategy_allowlist": {"decision": "allow", "file": "strategy_allowlist_snap.md", "exported_at": "2026-05-08 18:00:00"},
            },
        }
        settlements = [
            {
                "match_id": match_a.match_id,
                "strategy_allowlist_decision": "allow",
                "strategy_allowlist_file": "strategy_allowlist_a.md",
                "match_date": "2026-05-09",
                "league": "L1",
                "home_team": "A",
                "away_team": "B",
                "predicted": "home",
                "is_correct": True,
                "prediction_confidence": 0.72,
            },
            {
                "match_id": "settlement-only",
                "strategy_allowlist_decision": "allow",
                "strategy_allowlist_file": "strategy_allowlist_old.md",
                "match_date": "2026-05-07",
                "league": "L4",
                "home_team": "G",
                "away_team": "H",
                "predicted": "home",
                "is_correct": False,
                "prediction_confidence": 0.61,
            },
        ]

        loop = build_strategy_release_recovery_loop(
            rows,
            snapshots=snapshots,
            settlements=settlements,
            now=datetime(2026, 5, 10, 12, 0),
        )

        self.assertEqual(loop["total_release_count"], 4)
        self.assertEqual(loop["settled_count"], 2)
        self.assertEqual(loop["pending_count"], 2)
        self.assertEqual(loop["snapshot_saved_count"], 2)
        self.assertEqual(loop["missing_snapshot_count"], 1)
        self.assertEqual(loop["stale_pending_count"], 2)
        self.assertEqual(loop["ready_for_recovery_count"], 1)
        self.assertEqual(loop["hit_rate_text"], "50.0%")
        self.assertIn("\u7f3a\u5feb\u7167 1", loop["summary_text"])
        statuses = {str(row.get("match_id")): row.get("loop_status") for row in loop["rows"]}
        self.assertEqual(statuses[match_a.match_id], "\u5df2\u56de\u6536")
        self.assertEqual(statuses[match_b.match_id], "\u7f3a\u5feb\u7167")
        self.assertEqual(statuses[snapshot_only_id], "\u8d85\u671f\u5f85\u56de\u6536")

    def test_strategy_release_recovery_loop_report_lines_include_metrics_and_rows(self) -> None:
        loop = {
            "health_text": "\u9700\u8865\u56de\u6536",
            "summary_text": "\u653e\u884c 2 | \u5df2\u56de\u6536 1 | \u5f85\u56de\u6536 1 | \u7f3a\u5feb\u7167 1 | \u8d85\u671f 1 | \u547d\u4e2d 100.0%",
            "total_release_count": 2,
            "exported_count": 2,
            "snapshot_saved_count": 1,
            "settled_count": 1,
            "pending_count": 1,
            "missing_snapshot_count": 1,
            "stale_pending_count": 1,
            "hit_rate_text": "100.0%",
            "settlement_summary": {
                "known_count": 1,
                "hit_rate_text": "100.0%",
                "handicap_hit_rate_text": "-",
                "ou_hit_rate_text": "-",
                "high_strategy_summary": "1/1",
                "top_failure": "-",
            },
            "tuning": {"label": "\u7ee7\u7eed\u79ef\u7d2f\u6837\u672c", "rows": [("\u52a8\u4f5c", "\u7ee7\u7eed\u79ef\u7d2f\u6837\u672c")]},
            "rows": [
                {
                    "loop_status": "\u7f3a\u5feb\u7167",
                    "kickoff": "2026-05-08 22:00",
                    "match": {"league": "L2", "home_team": "C", "away_team": "D"},
                    "recommendation": "draw",
                    "confidence_text": "68.0%",
                    "risk_text": "\u4e2d\u98ce\u9669",
                    "snapshot_status": "\u7f3a\u5feb\u7167",
                    "settlement_status": "\u5f85\u56de\u6536",
                    "pending_days": 2,
                    "allowlist_file": "strategy_allowlist_b.md",
                }
            ],
        }

        filename = build_strategy_release_recovery_loop_report_filename(datetime(2026, 5, 10, 12, 0))
        lines = build_strategy_release_recovery_loop_report_lines(loop, generated_at=datetime(2026, 5, 10, 12, 0))
        payload = "\n".join(lines)

        self.assertEqual(filename, "strategy_release_recovery_loop_20260510_120000.md")
        self.assertIn("\u7b56\u7565\u653e\u884c\u56de\u6536\u95ed\u73af\u62a5\u544a", payload)
        self.assertIn("\u653e\u884c\u603b\u6570", payload)
        self.assertIn("C vs D", payload)
        self.assertIn("strategy_allowlist_b.md", payload)
        self.assertIn("\u7f3a\u5feb\u7167\u573a\u6b21", payload)

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

    def test_strategy_allowlist_tuning_recommendation_uses_historical_replay_pressure(self) -> None:
        recommendation = build_strategy_allowlist_tuning_recommendation(
            [],
            base_min_confidence=0.5,
            historical_replay={"sample_count": 200, "miss_count": 60, "hit_rate": 0.70, "hit_rate_text": "70.0%"},
            historical_error_attribution={
                "miss_count": 60,
                "top_reason": "\u9ad8\u7f6e\u4fe1\u5931\u8bef 50\u6b21",
                "reason_counts": {"high_confidence_miss": 50, "small_sample": 5},
            },
        )

        self.assertEqual(recommendation["action"], "history_watch")
        self.assertTrue(recommendation["historical_pressure"])
        self.assertFalse(recommendation["medium_risk_allowed"])
        self.assertEqual(recommendation["next_min_confidence"], 0.5)
        self.assertEqual(recommendation["historical_sample_count"], 200)
        self.assertTrue(any(label == "\u5386\u53f2\u56de\u653e" and "200" in value for label, value in recommendation["rows"]))


if __name__ == "__main__":
    unittest.main()
