from __future__ import annotations

from typing import Mapping


FINAL_BINDING_MANIFEST: tuple[tuple[str, str], ...] = (
    ("_mark_text", "_app_mark_text"),
    ("_prediction_summary_fields", "_app_prediction_summary_fields"),
    ("_format_poisson_block", "_app_format_poisson_block"),
    ("_show_match_details", "_app_show_match_details_with_parlays"),
    ("settle_selected_result", "_app_settle_selected_result"),
    ("show_recent_settlements", "_app_show_recent_settlements_table"),
    ("analyze_selected", "_app_analyze_selected_with_parlays"),
    ("analyze_all", "_app_analyze_all_with_parlays"),
    ("_ensemble_weight_status_text", "_app_ensemble_weight_status_text"),
    ("show_ensemble_weight_status", "_app_show_ensemble_weight_status"),
    ("_apply_calibrate_ensemble_result", "_app_apply_calibrate_ensemble_result"),
    ("calibrate_ensemble_weights", "_app_calibrate_ensemble_weights"),
    ("_apply_ensemble_backtest_result", "_app_apply_ensemble_backtest_result_v2"),
    ("run_ensemble_backtest", "_app_run_ensemble_backtest"),
    ("_apply_play_model_backtest_result", "_app_apply_play_model_backtest_result_v3"),
    ("run_play_model_backtest", "_app_run_play_model_backtest"),
    ("_apply_high_accuracy_strategy_backtest_result", "_app_apply_high_accuracy_strategy_backtest_result"),
    ("run_high_accuracy_strategy_backtest", "_app_run_high_accuracy_strategy_backtest"),
    ("_play_model_status_text", "_app_play_model_status_text_v3"),
    ("show_play_model_status", "_app_show_play_model_status_v2"),
    ("_apply_train_play_models_result", "_app_apply_train_play_models_result_v2"),
    ("train_play_models", "_app_train_play_models"),
    ("_play_model_policy_status_text", "_app_play_model_policy_status_text_v4"),
    ("show_play_model_policy_status", "_app_show_play_model_policy_status_v2"),
    ("_apply_calibrate_play_model_policy_result", "_app_apply_calibrate_play_model_policy_result"),
    ("calibrate_play_model_policy", "_app_calibrate_play_model_policy"),
    ("_play_threshold_status_text", "_app_play_threshold_status_text"),
    ("show_play_threshold_status", "_app_show_play_threshold_status"),
    ("_apply_play_threshold_result", "_app_apply_play_threshold_result"),
    ("calibrate_play_thresholds", "_app_calibrate_play_thresholds"),
    ("_apply_threshold_bucket_tuning_result", "_app_apply_threshold_bucket_tuning_result"),
    ("calibrate_thresholds_by_decomposition", "_app_calibrate_thresholds_by_decomposition"),
    ("_apply_layered_filter_threshold_result", "_app_apply_layered_filter_threshold_result"),
    ("calibrate_layered_filter_thresholds", "_app_calibrate_layered_filter_thresholds"),
    ("_apply_threshold_coverage_guardrail_result", "_app_apply_threshold_coverage_guardrail_result"),
    ("run_threshold_coverage_guardrail", "_app_run_threshold_coverage_guardrail"),
    ("_bayes_calibration_status_text", "_app_bayes_calibration_status_text"),
    ("show_bayes_calibration_status", "_app_show_bayes_calibration_status"),
    ("_apply_bayes_calibration_result", "_app_apply_bayes_calibration_result"),
    ("calibrate_bayes_calibration", "_app_calibrate_bayes_calibration"),
    ("_build_export_report_lines", "_app_build_export_report_lines"),
    ("_export_report_for_matches", "_app_export_report_for_matches"),
    ("export_current_report", "_app_export_visible_report"),
    ("export_all_report", "_app_export_all_report"),
    ("export_c1_availability_template", "_app_export_c1_availability_template"),
    ("_apply_export_c1_availability_template_result", "_app_apply_export_c1_availability_template_result"),
    ("import_c1_availability_snapshots", "_app_import_c1_availability_snapshots"),
    ("sync_c1_availability_sources", "_app_sync_c1_availability_sources"),
    ("_apply_sync_c1_availability_sources_result", "_app_apply_sync_c1_availability_sources_result"),
    ("show_c1_availability_provider_status", "_app_show_c1_availability_provider_status"),
    ("open_c1_release_guard_history", "_app_open_c1_release_guard_history"),
    ("_apply_import_c1_availability_snapshots_result", "_app_apply_import_c1_availability_snapshots_result"),
    ("run_c1_shadow_comparison", "_app_run_c1_shadow_comparison"),
    ("_apply_c1_shadow_comparison_result", "_app_apply_c1_shadow_comparison_result"),
    ("_build_c1_rows_from_marks", "_app_build_c1_rows_from_marks"),
    ("open_c1_workbench", "_app_open_c1_workbench"),
    ("run_c1_release_review", "_app_run_c1_release_review"),
    ("_current_release_row", "_app_current_release_row"),
    ("_release_allowed_match_ids", "_app_release_allowed_match_ids"),
    ("_active_release_allowed_match_ids", "_app_active_release_allowed_match_ids"),
    ("_release_gate_pick_text", "_app_release_gate_pick_text"),
    ("_format_release_candidate_text", "_app_format_release_candidate_text"),
    ("_build_formal_release_rows", "_app_build_formal_release_rows"),
    ("_refresh_release_gate_after_analysis", "_app_refresh_release_gate_after_analysis"),
    ("_apply_runtime_mode_default_filter", "_app_apply_runtime_mode_default_filter"),
    ("_apply_c1_release_review_result", "_app_apply_c1_release_review_result"),
    ("_export_c1_release_allowlist", "_app_export_c1_release_allowlist"),
    ("open_c1_formal_recommendations", "_app_open_c1_formal_recommendations"),
    ("open_c1_release_allowlist", "_app_open_c1_release_allowlist"),
    ("_show_c1_release_window", "_app_show_c1_release_window"),
    ("_show_c1_comparison_window", "_app_show_c1_comparison_window"),
    ("_apply_c1_comparison_to_main_list", "_app_apply_c1_comparison_to_main_list"),
    ("_export_c1_pending_template", "_app_export_c1_pending_template"),
    ("_apply_export_c1_pending_template_result", "_app_apply_export_c1_pending_template_result"),
    ("open_user_center", "_app_open_user_center_final"),
)


def resolve_final_bindings(namespace: Mapping[str, object]) -> dict[str, object]:
    resolved: dict[str, object] = {}
    missing: list[str] = []
    for attr_name, fn_name in FINAL_BINDING_MANIFEST:
        fn = namespace.get(fn_name)
        if fn is None:
            missing.append(fn_name)
            continue
        resolved[attr_name] = fn
    if missing:
        joined = ", ".join(missing[:8])
        raise RuntimeError(f"Missing final binding function(s): {joined}")
    return resolved
