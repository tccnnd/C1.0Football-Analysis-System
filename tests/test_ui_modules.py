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

from v24_app.core import AppMatch
from v24_app.ui_modules import build_analysis_status_text, build_export_report_lines, resolve_final_bindings


class UIModulesTests(unittest.TestCase):
    def test_build_analysis_status_text(self) -> None:
        text = build_analysis_status_text(
            base_status="批量分析完成，共 2 场",
            gate_active=True,
            allowed_count=2,
            active_allowed_count=1,
            parlay_count=3,
        )
        self.assertIn("C1放行 1 场", text)
        self.assertIn("二串一 3 组", text)

    def test_build_export_report_lines(self) -> None:
        match = AppMatch(
            home_team="A",
            away_team="B",
            league="Friendly",
            match_time="19:35",
            match_date="2026-04-04",
            odds_home=1.90,
            odds_draw=3.20,
            odds_away=4.20,
            source="live:titan",
            source_id="2965321",
        )
        prediction = {
            "recommendation": "主胜",
            "handicap_display": "+1 让胜",
            "total_goals_recommendation": "2球",
            "htft_recommendation": "胜/胜",
            "score_recommendation": "1-0",
            "confidence": 0.62,
        }
        lines = build_export_report_lines(
            matches=[match],
            all_match_count=1,
            predictions={match.match_id: prediction},
            c1_marks={match.match_id: {"suggested_action": "可放行", "governance_action": "APPROVE", "primary_reason_code": "OK"}},
            release_gate_pick_fn=lambda _match_id, p: str(p.get("recommendation", "-")),
            predict_match_fn=lambda _m: prediction,
            current_filter="正式建议",
            scope_label="当前筛选视图",
        )
        payload = "\n".join(lines)
        self.assertIn("Current Filter: 正式建议", payload)
        self.assertIn("A vs B", payload)
        self.assertIn("可放行", payload)

    def test_resolve_final_bindings(self) -> None:
        namespace = {
            "_app_mark_text": object(),
            "_app_prediction_summary_fields": object(),
            "_app_format_poisson_block": object(),
            "_app_show_match_details_with_parlays": object(),
            "_app_settle_selected_result": object(),
            "_app_show_recent_settlements_table": object(),
            "_app_analyze_selected_with_parlays": object(),
            "_app_analyze_all_with_parlays": object(),
            "_app_ensemble_weight_status_text": object(),
            "_app_show_ensemble_weight_status": object(),
            "_app_apply_calibrate_ensemble_result": object(),
            "_app_calibrate_ensemble_weights": object(),
            "_app_apply_ensemble_backtest_result_v2": object(),
            "_app_run_ensemble_backtest": object(),
            "_app_apply_play_model_backtest_result_v3": object(),
            "_app_run_play_model_backtest": object(),
            "_app_apply_high_accuracy_strategy_backtest_result": object(),
            "_app_run_high_accuracy_strategy_backtest": object(),
            "_app_play_model_status_text_v3": object(),
            "_app_show_play_model_status_v2": object(),
            "_app_apply_train_play_models_result_v2": object(),
            "_app_train_play_models": object(),
            "_app_play_model_policy_status_text_v4": object(),
            "_app_show_play_model_policy_status_v2": object(),
            "_app_apply_calibrate_play_model_policy_result": object(),
            "_app_calibrate_play_model_policy": object(),
            "_app_play_threshold_status_text": object(),
            "_app_show_play_threshold_status": object(),
            "_app_apply_play_threshold_result": object(),
            "_app_calibrate_play_thresholds": object(),
            "_app_apply_threshold_bucket_tuning_result": object(),
            "_app_calibrate_thresholds_by_decomposition": object(),
            "_app_apply_layered_filter_threshold_result": object(),
            "_app_calibrate_layered_filter_thresholds": object(),
            "_app_apply_threshold_coverage_guardrail_result": object(),
            "_app_run_threshold_coverage_guardrail": object(),
            "_app_bayes_calibration_status_text": object(),
            "_app_show_bayes_calibration_status": object(),
            "_app_apply_bayes_calibration_result": object(),
            "_app_calibrate_bayes_calibration": object(),
            "_app_build_export_report_lines": object(),
            "_app_export_report_for_matches": object(),
            "_app_export_visible_report": object(),
            "_app_export_all_report": object(),
            "_app_export_c1_availability_template": object(),
            "_app_apply_export_c1_availability_template_result": object(),
            "_app_import_c1_availability_snapshots": object(),
            "_app_sync_c1_availability_sources": object(),
            "_app_apply_sync_c1_availability_sources_result": object(),
            "_app_show_c1_availability_provider_status": object(),
            "_app_apply_import_c1_availability_snapshots_result": object(),
            "_app_run_c1_shadow_comparison": object(),
            "_app_apply_c1_shadow_comparison_result": object(),
            "_app_build_c1_rows_from_marks": object(),
            "_app_open_c1_workbench": object(),
            "_app_run_c1_release_review": object(),
            "_app_current_release_row": object(),
            "_app_release_allowed_match_ids": object(),
            "_app_active_release_allowed_match_ids": object(),
            "_app_release_gate_pick_text": object(),
            "_app_format_release_candidate_text": object(),
            "_app_build_formal_release_rows": object(),
            "_app_refresh_release_gate_after_analysis": object(),
            "_app_apply_runtime_mode_default_filter": object(),
            "_app_apply_c1_release_review_result": object(),
            "_app_export_c1_release_allowlist": object(),
            "_app_open_c1_formal_recommendations": object(),
            "_app_open_c1_release_allowlist": object(),
            "_app_show_c1_release_window": object(),
            "_app_show_c1_comparison_window": object(),
            "_app_apply_c1_comparison_to_main_list": object(),
            "_app_export_c1_pending_template": object(),
            "_app_apply_export_c1_pending_template_result": object(),
            "_app_open_user_center_final": object(),
        }
        resolved = resolve_final_bindings(namespace)
        self.assertGreaterEqual(len(resolved), 60)
        self.assertIn("open_user_center", resolved)
        self.assertIn("analyze_selected", resolved)


if __name__ == "__main__":
    unittest.main()
