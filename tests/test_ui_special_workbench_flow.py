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
    SPECIAL_WORKBENCH_LAYOUT,
    build_data_training_special_section_rows,
    build_review_center_special_summary_rows,
    build_strategy_special_summary_rows,
    build_special_workbench_overview_rows,
    build_special_workbench_sections,
)


class UISpecialWorkbenchFlowTests(unittest.TestCase):
    def test_build_special_workbench_sections_binds_grouped_actions(self) -> None:
        calls: list[str] = []
        action_keys = [
            entry["action_key"]
            for _section_title, entries in SPECIAL_WORKBENCH_LAYOUT
            for entry in entries
        ]
        actions = {key: (lambda key=key: calls.append(key)) for key in action_keys}

        sections = build_special_workbench_sections(actions)

        self.assertEqual([section[0] for section in sections], ["复盘闭环", "策略与接管", "数据与运行"])
        self.assertGreaterEqual(len(sections[0][1]), 5)
        self.assertIn("open_ai_video_review_center_window", action_keys)
        self.assertIn("open_play_model_takeover_gate_audit_history", action_keys)
        self.assertIn("open_strategy_policy_audit_history", action_keys)
        self.assertIn("open_data_center", action_keys)

        first_command = sections[0][1][0]["command"]
        self.assertTrue(callable(first_command))
        first_command()
        self.assertEqual(calls, [sections[0][1][0]["action_key"]])

    def test_build_special_workbench_sections_reports_missing_actions(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Missing special workbench action"):
            build_special_workbench_sections({})

    def test_build_review_center_special_summary_rows_reduces_to_action_cards(self) -> None:
        rows = build_review_center_special_summary_rows(
            video_review_center_summary={"title": "AI视频复盘 | attention", "body": "video body", "tone": "warning"},
            evidence_gap_batch_status={"status": "running", "summary_text": "gap body", "completion_rate": 0.25},
            video_source_coverage={"no_review_evidence_count": 7},
            statsbomb_review_center_summary={"title": "事件代理 | healthy", "body": "proxy body", "tone": "good"},
            statsbomb_review_closure_summary={"title": "闭环 | attention", "body": "closure body", "tone": "warning"},
        )

        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["action_key"], "open_special_workbench")
        self.assertIn("AI视频复盘", rows[1]["title"])
        self.assertEqual(rows[2]["action_key"], "open_video_review_evidence_gap_center_window")
        self.assertIn("当前缺证据 7 场", rows[2]["body"])
        self.assertEqual(rows[3]["action_key"], "open_statsbomb_review_training_center_window")
        self.assertEqual(rows[4]["action_key"], "open_statsbomb_review_training_closure_window")

    def test_build_strategy_special_summary_rows_includes_core_strategy_entries(self) -> None:
        rows = build_strategy_special_summary_rows(
            play_model_policy_status={
                "policy_blocked_by_gate": True,
                "policy": {"scoreline": {"takeover_enabled": True}, "total_goals": {"takeover_enabled": True}},
                "effective_policy": {"scoreline": {"takeover_enabled": False}, "total_goals": {"takeover_enabled": False}},
                "takeover_gate": {"status": "watch"},
                "takeover_gate_audit": {"history_count": 2, "latest_transition": "block->watch", "latest_reason": "total_goals_model_no_uplift"},
            },
            release_recovery_loop={"summary_text": "闭环 2 场 | 待回收 1 场", "ready_for_recovery_count": 1, "alert_count": 2},
            draw_release_guard_tuning={"summary_text": "平局专项诊断 | warning", "reason_text": "sample_count_low", "tone": "warning"},
            accuracy_diagnostics={"sample_count": 12, "overall": "62.5%", "priority": "调高1X2命中率"},
        )

        self.assertEqual(
            [row["action_key"] for row in rows],
            [
                "open_strategy_release_recovery_loop_window",
                "open_play_model_takeover_gate_audit_history",
                "open_play_model_policy_detail_window",
                "open_draw_specialist_backtest_window",
                "open_accuracy_diagnostics",
                "open_strategy_policy_audit_history",
            ],
        )
        self.assertIn("放行回收闭环", rows[0]["title"])
        self.assertIn("历史 2", rows[1]["body"])
        self.assertIn("blocked=True", rows[2]["body"])
        self.assertIn("sample_count_low", rows[3]["body"])
        self.assertIn("样本 12", rows[4]["body"])

    def test_build_special_workbench_overview_rows_summarizes_groups(self) -> None:
        rows = build_special_workbench_overview_rows()

        self.assertEqual(rows[0]["label"], "专项总数")
        self.assertEqual(rows[0]["value"], str(sum(len(entries) for _section_title, entries in SPECIAL_WORKBENCH_LAYOUT)))
        self.assertIn("复盘", rows[1]["label"])
        self.assertIn("策略", rows[2]["label"])
        self.assertIn("数据", rows[3]["label"])
        self.assertIn("/", rows[0]["detail"])


    def test_build_data_training_special_section_rows_exposes_overview_and_jump_entry(self) -> None:
        calls: list[str] = []
        actions = {
            "show_model_training_overview": lambda: calls.append("training"),
            "open_data_center": lambda: calls.append("data"),
        }
        rows = build_data_training_special_section_rows(
            actions,
            coverage_status={
                "training_health": {
                    "status": "attention",
                    "blocking_count": 0,
                    "warning_count": 1,
                    "issues": [
                        {
                            "code": "statsbomb_review_samples_missing",
                            "severity": "warning",
                            "message": "StatsBomb 复盘样本缺失。",
                            "recommendation": "生成复盘样本。",
                        }
                    ],
                    "xgb_trainability": {
                        "sample_count": 128,
                        "min_sample_count": 300,
                        "valid_feature_count": 120,
                        "min_valid_feature_count": 300,
                    },
                    "history_readiness": {
                        "club_match_count": 96,
                        "min_club_match_count": 100,
                        "statsbomb_match_count": 3,
                        "statsbomb_review_sample_count": 0,
                        "statsbomb_review_feature_count": 0,
                    },
                }
            },
            training_gate_status={
                "status": "ready_to_train_play_models",
                "recommended_action": "train_play_models",
                "recommendation": "玩法模型可训练。",
                "xgb": {
                    "trainable": True,
                    "sample_count": 320,
                    "min_sample_count": 300,
                    "valid_feature_count": 300,
                    "min_valid_feature_count": 300,
                    "model_ready": True,
                },
                "play_models": {
                    "trainable_count": 2,
                    "total_count": 2,
                    "ready_count": 1,
                    "all_trainable": True,
                    "all_ready": False,
                },
            },
            data_health_status={
                "data_source": "local",
                "source_health": "来源正常",
                "cache_status": "缓存命中",
                "inventory_rows": [
                    ("cache", "12 files / 1.2 MB / updated 2026-05-17"),
                    ("state", "8 files / 512 KB / updated 2026-05-17"),
                    ("models", "3 files / 3.4 MB / updated 2026-05-17"),
                ],
            },
        )

        self.assertEqual(
            [row["title"] for row in rows],
            [
                "训练健康卡片",
                "优先补数建议",
                "XGB 训练 gate",
                "玩法模型训练 gate",
                "数据文件 / 模型文件 / 缓存健康摘要",
            ],
        )
        self.assertIn("attention", rows[0]["body"])
        self.assertIn("StatsBomb 复盘样本缺失", rows[1]["body"])
        self.assertIn("ready_to_train_play_models", rows[3]["body"])
        self.assertIn("数据源 local", rows[4]["body"])
        for row in rows:
            command = row.get("command")
            self.assertTrue(callable(command))
            command()
        self.assertEqual(calls, ["training", "training", "training", "training", "data"])


if __name__ == "__main__":
    unittest.main()
