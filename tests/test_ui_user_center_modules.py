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

from v24_app.ui_modules import build_user_center_sections


class UIUserCenterModuleTests(unittest.TestCase):
    def test_build_user_center_sections_requires_all_actions(self) -> None:
        with self.assertRaises(RuntimeError):
            build_user_center_sections(actions={})

    def test_build_user_center_sections_layout(self) -> None:
        required_keys = [
            "analyze_selected",
            "analyze_all",
            "show_coverage_monitor",
            "show_ops_daily_report",
            "show_ops_weekly_trend",
            "export_current_report",
            "export_all_report",
            "settle_selected_result",
            "show_recent_settlements",
            "show_handicap_monitor",
            "export_handicap_shadow_report",
            "export_accuracy_decomposition_report",
            "show_model_training_overview",
            "show_xgb_status",
            "train_xgb_now",
            "show_play_model_status",
            "train_play_models",
            "show_ensemble_weight_status",
            "calibrate_ensemble_weights",
            "show_play_threshold_status",
            "calibrate_play_thresholds",
            "calibrate_thresholds_by_decomposition",
            "calibrate_layered_filter_thresholds",
            "run_threshold_coverage_guardrail",
            "show_bayes_calibration_status",
            "calibrate_bayes_calibration",
            "show_play_model_policy_status",
            "calibrate_play_model_policy",
            "run_ensemble_backtest",
            "run_play_model_backtest",
            "run_high_accuracy_strategy_backtest",
            "export_play_model_takeover_gate_audit_report",
            "export_c1_availability_template",
            "import_c1_availability_snapshots",
            "sync_c1_availability_sources",
            "show_c1_availability_provider_status",
            "open_c1_release_guard_history",
            "run_c1_shadow_comparison",
            "run_c1_release_review",
            "open_c1_formal_recommendations",
            "open_c1_release_allowlist",
            "open_c1_workbench",
        ]
        actions = {key: (lambda: None) for key in required_keys}
        sections = build_user_center_sections(actions=actions)

        # Phase 5 重构：6组 → 3组
        self.assertEqual(len(sections), 3)

        # 组名验证
        titles = [s[0] for s in sections]
        self.assertEqual(titles[0], "分析与结算")
        self.assertEqual(titles[1], "模型与校准")
        self.assertEqual(titles[2], "C1 管理")

        # 第0组：分析与结算 — 首个按钮是"分析选中"
        self.assertEqual(sections[0][1][0][0], "分析选中")

        # 第0组：包含"录入赛果"（原结算组）
        group0_labels = [btn[0] for btn in sections[0][1]]
        self.assertIn("录入赛果", group0_labels)
        self.assertIn("让球专项看板", group0_labels)
        self.assertIn("导出让球14天日报", group0_labels)

        # 第1组：模型与校准 — 包含训练和校准功能
        group1_labels = [btn[0] for btn in sections[1][1]]
        self.assertIn("模型总览", group1_labels)
        self.assertIn("训练XGB", group1_labels)
        self.assertIn("校准权重", group1_labels)
        self.assertIn("高准策略", group1_labels)

        # 第2组：C1管理 — 末尾是"打开C1工作台"
        self.assertEqual(sections[2][1][-1][0], "打开C1工作台")
        group2_labels = [btn[0] for btn in sections[2][1]]
        self.assertIn("放行门控审计", group2_labels)
        self.assertIn("运行C1对照", group2_labels)


if __name__ == "__main__":
    unittest.main()
