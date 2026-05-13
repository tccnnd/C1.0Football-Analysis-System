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
    build_calibrate_ensemble_apply_message,
    build_calibrate_ensemble_apply_status_text,
    build_ensemble_backtest_apply_status_text,
    build_ensemble_backtest_success_message,
    build_ensemble_weight_status_text,
    build_draw_specialist_backtest_apply_status_text,
    build_draw_specialist_backtest_card_rows,
    build_draw_specialist_backtest_status_text,
    build_model_training_overview_text,
    build_play_model_backtest_apply_status_text,
    build_play_model_backtest_success_message,
    build_play_model_policy_apply_status_text,
    build_play_model_policy_apply_success_message,
    build_play_model_policy_decision_rows,
    build_play_model_policy_status_text,
    build_play_model_takeover_gate_action_rows,
    build_play_model_takeover_gate_audit_rows,
    build_play_model_takeover_gate_rows,
    build_play_model_training_status_text,
    build_play_threshold_apply_status_text,
    build_play_threshold_apply_success_message,
    build_play_threshold_status_text,
    build_train_play_models_apply_message,
    build_train_play_models_apply_status_text,
    build_training_health_action_rows,
    build_training_health_card_rows,
    build_training_health_repair_result_text,
    build_training_model_gate_rows,
    training_health_action_button_text,
)


class UIModelStatusFlowModuleTests(unittest.TestCase):
    def _coverage_with_health(self, status: str, issues: list[dict[str, str]] | None = None) -> dict:
        return {
            "xgb_samples": {"sample_count": 120, "valid_feature_count": 110, "league_count": 2},
            "training_health": {
                "status": status,
                "blocking_count": sum(1 for issue in issues or [] if issue.get("severity") == "blocking"),
                "warning_count": sum(1 for issue in issues or [] if issue.get("severity") == "warning"),
                "issues": issues or [],
                "xgb_trainability": {
                    "sample_count": 120,
                    "min_sample_count": 300,
                    "valid_feature_count": 110,
                    "min_valid_feature_count": 300,
                    "valid_feature_ratio": 0.9167,
                    "min_valid_feature_ratio": 0.95,
                    "label_class_count": 2,
                    "min_label_classes": 3,
                    "min_class_count": 18,
                    "min_required_class_count": 30,
                    "league_count": 2,
                    "min_league_count": 5,
                    "date_start": "2024-01-01",
                    "date_end": "2024-12-31",
                },
                "history_readiness": {
                    "club_match_count": 80,
                    "min_club_match_count": 100,
                    "league_profile_count": 0,
                    "world_cup_match_count": 128,
                    "statsbomb_match_count": 3,
                    "statsbomb_review_sample_count": 0,
                    "statsbomb_review_feature_count": 0,
                },
                "rating_readiness": {
                    "club_team_count": 20,
                    "national_team_count": 8,
                },
            },
        }

    def test_model_training_overview_shows_statsbomb_review_samples(self) -> None:
        text = build_model_training_overview_text(
            xgb_status={},
            play_model_status={},
            ensemble_status={},
            bayes_status={},
            threshold_status={},
            policy_status={},
            coverage_status={
                "xgb_samples": {"sample_count": 10, "valid_feature_count": 9, "league_count": 2},
                "statsbomb_events": {
                    "match_count": 3,
                    "review_sample_count": 2,
                    "review_feature_count": 38,
                    "coverage_gap_count": 4,
                    "coverage_candidate_count": 1,
                },
            },
        )

        self.assertIn("StatsBomb事件: 3 场", text)
        self.assertIn("复盘样本=2", text)
        self.assertIn("覆盖缺口=4", text)
        self.assertIn("候选=1", text)

    def test_model_training_overview_shows_training_health_issues(self) -> None:
        text = build_model_training_overview_text(
            xgb_status={},
            play_model_status={},
            ensemble_status={},
            bayes_status={},
            threshold_status={},
            policy_status={},
            coverage_status={
                "xgb_samples": {"sample_count": 120, "valid_feature_count": 110, "league_count": 2},
                "training_health": {
                    "status": "blocked",
                    "blocking_count": 1,
                    "warning_count": 1,
                    "issues": [
                        {
                            "code": "xgb_sample_count_low",
                            "severity": "blocking",
                            "message": "XGB样本数不足: 120/300",
                            "recommendation": "继续导入历史赛果样本。",
                        },
                        {
                            "code": "xgb_league_coverage_low",
                            "severity": "warning",
                            "message": "XGB联赛覆盖不足: 2/5",
                            "recommendation": "补充不同联赛样本。",
                        },
                    ],
                },
            },
        )

        self.assertIn("训练健康: blocked", text)
        self.assertIn("blocking=1", text)
        self.assertIn("健康问题1: [blocking] XGB样本数不足: 120/300", text)
        self.assertIn("建议: 继续导入历史赛果样本。", text)
        self.assertIn("训练健康卡片", text)
        self.assertIn("优先补数建议", text)
        self.assertIn("训练门槛联动", text)

    def test_training_health_card_rows_show_blocked_status(self) -> None:
        coverage = self._coverage_with_health(
            "blocked",
            [
                {
                    "code": "xgb_sample_count_low",
                    "severity": "blocking",
                    "message": "XGB样本数不足: 120/300",
                    "recommendation": "继续导入历史赛果样本。",
                }
            ],
        )

        cards = build_training_health_card_rows(coverage)
        actions = build_training_health_action_rows(coverage)

        self.assertEqual(cards[0]["label"], "整体状态")
        self.assertEqual(cards[0]["value"], "blocked")
        self.assertEqual(cards[0]["tone"], "danger")
        self.assertIn("训练阻塞", cards[0]["detail"])
        self.assertEqual(cards[1]["tone"], "danger")
        self.assertEqual(actions[0]["tone"], "danger")
        self.assertEqual(actions[0]["value"], "扩大历史赛果样本，优先最近4年主流联赛")
        self.assertEqual(actions[0]["action_key"], "import_historical_samples")
        self.assertEqual(training_health_action_button_text(actions[0]["action_key"]), "导入历史样本")

    def test_training_health_action_rows_show_attention_suggestions(self) -> None:
        coverage = self._coverage_with_health(
            "attention",
            [
                {
                    "code": "xgb_league_coverage_low",
                    "severity": "warning",
                    "message": "XGB联赛覆盖不足: 2/5",
                    "recommendation": "补充不同联赛样本。",
                },
                {
                    "code": "xgb_class_balance_low",
                    "severity": "warning",
                    "message": "XGB最小标签样本偏低: 18/30",
                    "recommendation": "扩大历史样本。",
                },
            ],
        )

        cards = build_training_health_card_rows(coverage)
        actions = build_training_health_action_rows(coverage)

        self.assertEqual(cards[0]["tone"], "warning")
        self.assertIn("需要关注", cards[0]["detail"])
        self.assertTrue(any(row["value"] == "补不同联赛样本" for row in actions))
        self.assertTrue(any(row["value"] == "补平局/客胜等弱类别样本" for row in actions))
        self.assertTrue(any(row["action_key"] == "import_historical_samples" for row in actions))

    def test_training_health_action_rows_show_healthy_next_step(self) -> None:
        coverage = self._coverage_with_health("healthy", [])
        coverage["training_health"]["blocking_count"] = 0
        coverage["training_health"]["warning_count"] = 0

        cards = build_training_health_card_rows(coverage)
        actions = build_training_health_action_rows(coverage)

        self.assertEqual(cards[0]["tone"], "success")
        self.assertIn("可训练", cards[0]["detail"])
        self.assertEqual(actions[0]["tone"], "success")
        self.assertEqual(actions[0]["value"], "进入回测/训练稳定性验证")
        self.assertEqual(actions[0]["action_key"], "run_play_model_backtest")

    def test_training_health_action_rows_limit_to_five(self) -> None:
        coverage = self._coverage_with_health(
            "attention",
            [
                {"code": "xgb_league_coverage_low", "severity": "warning", "message": "m", "recommendation": "r"}
                for _ in range(6)
            ],
        )

        self.assertEqual(len(build_training_health_action_rows(coverage)), 5)

    def test_training_health_repair_result_text(self) -> None:
        text = build_training_health_repair_result_text(
            {
                "action_key": "build_league_profiles",
                "ok": True,
                "before_status": "attention",
                "after_status": "healthy",
                "message": "联赛画像已从俱乐部历史样本生成。",
                "result": {"league_profile_count": 5},
                "training_gate": {"status": "ready_to_train_play_models", "recommendation": "建议训练玩法模型。"},
            }
        )

        self.assertIn("训练健康修复: 完成", text)
        self.assertIn("动作: 生成联赛画像", text)
        self.assertIn("attention -> healthy", text)
        self.assertIn("复检: ready_to_train_play_models", text)

    def test_training_model_gate_rows_expose_training_actions(self) -> None:
        rows = build_training_model_gate_rows(
            {
                "status": "ready_to_train_play_models",
                "recommended_action": "train_play_models",
                "recommendation": "玩法模型样本已达到门槛。",
                "xgb": {
                    "sample_count": 900,
                    "min_sample_count": 300,
                    "valid_feature_count": 900,
                    "min_valid_feature_count": 300,
                    "trainable": True,
                    "model_ready": True,
                },
                "play_models": {
                    "trainable_count": 3,
                    "ready_count": 1,
                    "total_count": 3,
                    "all_trainable": True,
                    "all_ready": False,
                    "items": [
                        {"label": "总进球", "usable_count": 900, "min_train_samples": 500, "trainable": True, "model_ready": True},
                        {"label": "比分", "usable_count": 900, "min_train_samples": 800, "trainable": True, "model_ready": False},
                    ],
                },
            }
        )

        self.assertEqual(rows[0]["action_key"], "train_play_models")
        self.assertEqual(rows[0]["tone"], "success")
        self.assertEqual(rows[2]["action_key"], "train_play_models")
        self.assertEqual(training_health_action_button_text("train_play_models"), "训练玩法模型")

    def test_ensemble_status_and_messages(self) -> None:
        status_text = build_ensemble_weight_status_text(
            {
                "mode": "calibrated",
                "updated_at": "2026-04-04",
                "weights": {"market": 0.3, "elo": 0.3, "poisson": 0.2, "xgboost": 0.2},
                "validation": {"sample_count": 100, "train_sample_count": 500, "date_start": "2024-01-01", "date_end": "2025-12-31"},
                "metrics": {"market": {"logloss": 0.9, "brier": 0.2, "accuracy": 0.51}},
            }
        )
        self.assertIn("Ensemble 权重状态", status_text)
        self.assertIn("验证集/训练集: 100 / 500", status_text)
        self.assertIn("market: logloss=0.9000", status_text)

        result = {"calibrated": True, "reason": "ok", "sample_count": 88, "weights": {"market": 0.31, "xgboost": 0.22}}
        self.assertIn("权重校准完成", build_calibrate_ensemble_apply_status_text(result))
        msg = build_calibrate_ensemble_apply_message(result, status_text)
        self.assertIn("校准结果: 成功", msg)
        self.assertIn("样本数: 88", msg)

        backtest_status = build_ensemble_backtest_apply_status_text(
            {"ok": True, "stage5_improvement": {"accuracy_delta": 0.01, "logloss_delta": -0.02}}
        )
        self.assertIn("回测完成", backtest_status)
        self.assertIn("Stage5 acc +1.00%", backtest_status)
        backtest_msg = build_ensemble_backtest_success_message(
            {
                "validation": {"sample_count": 100, "train_sample_count": 500, "date_start": "2024-01-01", "date_end": "2025-12-31"},
                "default": {"logloss": 0.9, "brier": 0.2, "accuracy": 0.51},
                "calibrated": {"logloss": 0.88, "brier": 0.19, "accuracy": 0.53},
                "league_specific": {"logloss": 0.87, "brier": 0.19, "accuracy": 0.54},
                "stage4_runtime": {"logloss": 0.86, "brier": 0.18, "accuracy": 0.55, "draw_picks": 10, "draw_hit_rate": 0.3},
                "stage5_specialist": {"logloss": 0.85, "brier": 0.18, "accuracy": 0.56, "draw_picks": 12, "draw_hit_rate": 0.35},
                "improvement": {"logloss_delta": -0.02, "brier_delta": -0.01, "accuracy_delta": 0.02},
                "league_improvement": {"logloss_delta": -0.03, "brier_delta": -0.01, "accuracy_delta": 0.03},
                "stage5_improvement": {"logloss_delta": -0.04, "brier_delta": -0.02, "accuracy_delta": 0.04},
                "report_path": "r.md",
            }
        )
        self.assertIn("Ensemble 回测完成", backtest_msg)
        self.assertIn("报告: r.md", backtest_msg)

    def test_play_threshold_and_policy(self) -> None:
        threshold_text = build_play_threshold_status_text(
            {
                "mode": "calibrated",
                "updated_at": "2026-04-04",
                "validation": {"sample_count": 50, "train_sample_count": 200, "date_start": "2025-01-01", "date_end": "2025-12-31"},
                "thresholds": {"1x2": 0.6, "handicap": 0.61, "total_goals": 0.62, "htft": 0.63, "score": 0.64},
                "metrics": {"1x2": {"accuracy": 0.5, "coverage": 0.7}},
            }
        )
        self.assertIn("玩法阈值状态", threshold_text)
        self.assertIn("1x2: threshold=0.60", threshold_text)
        self.assertIn("验证集/训练集: 50 / 200", threshold_text)
        self.assertIn("玩法阈值校准完成", build_play_threshold_apply_status_text({"calibrated": True, "reason": "ok"}))
        self.assertIn(
            "报告: p.md",
            build_play_threshold_apply_success_message({"validation": {"sample_count": 50}, "report_path": "p.md"}, threshold_text),
        )

        policy_status = build_play_model_policy_status_text(
            {
                "updated_at": "2026-04-04",
                "policy": {"scoreline": {"takeover_enabled": True}, "total_goals": {"takeover_enabled": True, "min_confidence": 0.66}},
                "metrics": {"scoreline_best": {"score_hits": 10, "score_covered": 20, "score_accuracy": 0.5, "total_goals_hits": 12, "total_goals_covered": 20, "total_goals_accuracy": 0.6, "combined_hits": 8}},
            }
        )
        self.assertIn("玩法接管策略", policy_status)
        self.assertIn("联合最优", policy_status)
        self.assertIn("Takeover decisions", policy_status)
        self.assertIn("Total Goals takeover: ON", policy_status)
        self.assertIn("玩法接管策略完成", build_play_model_policy_apply_status_text({"calibrated": True, "reason": "ok"}))
        self.assertIn(
            "验证样本: 120",
            build_play_model_policy_apply_success_message({"validation": {"sample_count": 120}}, policy_status),
        )

        decision_rows = build_play_model_policy_decision_rows(
            {
                "policy": {"scoreline": {"takeover_enabled": True}, "total_goals": {"takeover_enabled": False, "min_confidence": 0.26}},
                "metrics": {
                    "total_goals": {
                        "current_accuracy": 0.50,
                        "best": {"accuracy": 0.52, "hits": 52, "covered": 100, "takeover_enabled": True},
                        "uplift": 0.02,
                        "min_required_uplift": 0.03,
                        "reason": "insufficient_calibration_uplift",
                    },
                    "scoreline_best": {"score_hits": 25, "score_covered": 100, "score_accuracy": 0.25, "combined_hits": 77},
                },
            }
        )
        self.assertEqual(decision_rows[0]["title"], "Total Goals takeover: SHADOW")
        self.assertEqual(decision_rows[0]["tone"], "warning")
        self.assertIn("uplift +2.00% / required +3.00%", decision_rows[0]["body"])
        self.assertIn("insufficient_calibration_uplift", decision_rows[0]["body"])
        self.assertEqual(decision_rows[1]["title"], "Scoreline takeover: ON")

    def test_play_model_takeover_gate_rows_and_policy_text(self) -> None:
        gate = {
            "status": "block",
            "mode": "enforced",
            "policy_impact": "formal_takeover_disabled",
            "recommendation": "Do not allow play-model takeover.",
            "metrics": {
                "training_gate_status": "ready_for_backtest",
                "validation_sample_count": 120,
                "min_validation_samples": 300,
                "total_goals_model_delta": 0.02,
                "score_model_delta": -0.04,
            },
            "issues": [
                {
                    "code": "score_model_regression",
                    "severity": "blocking",
                    "message": "Scoreline model delta is below the block threshold.",
                    "recommendation": "Keep scoreline model out of formal takeover.",
                }
            ],
        }

        rows = build_play_model_takeover_gate_rows({"takeover_gate": gate})
        self.assertEqual(rows[0]["title"], "Takeover gate: BLOCK")
        self.assertEqual(rows[0]["tone"], "danger")
        self.assertIn("samples 120/300", rows[0]["body"])
        self.assertEqual(rows[1]["title"], "blocking: score_model_regression")

        policy_text = build_play_model_policy_status_text(
            {
                "updated_at": "2026-04-04",
                "policy": {"scoreline": {"takeover_enabled": True}, "total_goals": {"takeover_enabled": False}},
                "metrics": {},
                "takeover_gate": gate,
            }
        )
        self.assertIn("Takeover gate", policy_text)
        self.assertIn("Takeover gate: BLOCK", policy_text)
        self.assertIn("Do not allow play-model takeover.", policy_text)

    def test_play_model_takeover_gate_action_rows_for_block_watch_allow(self) -> None:
        block_rows = build_play_model_takeover_gate_action_rows(
            {
                "takeover_gate": {
                    "status": "block",
                    "issues": [{"code": "validation_sample_count_low"}, {"code": "score_model_regression"}],
                }
            }
        )
        block_keys = [row["action_key"] for row in block_rows]
        self.assertIn("import_historical_samples", block_keys)
        self.assertIn("pause_scoreline_takeover", block_keys)

        watch_rows = build_play_model_takeover_gate_action_rows(
            {
                "takeover_gate": {
                    "status": "watch",
                    "issues": [{"code": "total_goals_model_no_uplift"}],
                }
            }
        )
        watch_keys = [row["action_key"] for row in watch_rows]
        self.assertIn("continue_shadow_watch", watch_keys)
        self.assertIn("train_play_models", watch_keys)

        allow_rows = build_play_model_takeover_gate_action_rows(
            {
                "takeover_gate": {
                    "status": "allow",
                    "issues": [],
                }
            }
        )
        allow_keys = [row["action_key"] for row in allow_rows]
        self.assertIn("calibrate_play_model_policy", allow_keys)
        self.assertIn("review_formal_takeover", allow_keys)

    def test_play_model_policy_text_shows_raw_effective_and_gate_block(self) -> None:
        policy_text = build_play_model_policy_status_text(
            {
                "updated_at": "2026-04-04",
                "policy": {
                    "scoreline": {"takeover_enabled": True},
                    "total_goals": {"takeover_enabled": True, "min_confidence": 0.31},
                },
                "effective_policy": {
                    "scoreline": {"takeover_enabled": False},
                    "total_goals": {"takeover_enabled": False, "min_confidence": 0.31},
                },
                "policy_blocked_by_gate": True,
                "takeover_gate": {"status": "watch", "recommendation": "Shadow only."},
                "takeover_gate_history_count": 2,
                "takeover_gate_audit": {
                    "history_count": 2,
                    "latest_transition": "block->watch",
                    "latest_reason": "total_goals_model_no_uplift",
                    "latest_validation_sample_count": 320,
                    "latest_total_goals_model_delta": -0.005,
                    "latest_score_model_delta": 0.002,
                    "latest_policy_impact": "formal_takeover_disabled",
                    "latest_report_path": "reports/play.md",
                },
                "takeover_gate_history": [
                    {
                        "status": "watch",
                        "transition": "block->watch",
                        "reason": "total_goals_model_no_uplift",
                        "updated_at": "2026-05-13 11:00:00",
                        "policy_impact": "formal_takeover_disabled",
                        "metrics": {
                            "validation_sample_count": 320,
                            "total_goals_model_delta": -0.005,
                            "score_model_delta": 0.002,
                        },
                        "report_path": "reports/play.md",
                    },
                    {
                        "status": "block",
                        "transition": "none->block",
                        "reason": "validation_sample_count_low",
                        "updated_at": "2026-05-13 10:00:00",
                        "policy_impact": "formal_takeover_disabled",
                    },
                ],
            }
        )

        self.assertIn("Policy gate execution", policy_text)
        self.assertIn("Raw scoreline takeover: enabled=True", policy_text)
        self.assertIn("Effective scoreline takeover: enabled=False", policy_text)
        self.assertIn("Raw total goals takeover: enabled=True", policy_text)
        self.assertIn("Effective total goals takeover: enabled=False", policy_text)
        self.assertIn("Takeover gate audit", policy_text)
        self.assertIn("Takeover gate audit: 2 transition(s)", policy_text)
        self.assertIn("latest block->watch", policy_text)
        self.assertIn("total_goals_delta -0.50%", policy_text)
        self.assertIn("Takeover gate actions", policy_text)
        self.assertIn("action_key=continue_shadow_watch", policy_text)
        self.assertIn("action_key=train_play_models", policy_text)
        self.assertIn("当前接管被守门策略阻断", policy_text)

        rows = build_play_model_policy_decision_rows(
            {
                "policy": {
                    "scoreline": {"takeover_enabled": True},
                    "total_goals": {"takeover_enabled": True, "min_confidence": 0.31},
                },
                "effective_policy": {
                    "scoreline": {"takeover_enabled": False},
                    "total_goals": {"takeover_enabled": False, "min_confidence": 0.31},
                },
            }
        )
        self.assertEqual(rows[0]["title"], "Total Goals takeover: SHADOW")
        self.assertIn("raw takeover True | effective takeover False", rows[0]["body"])
        self.assertEqual(rows[1]["title"], "Scoreline takeover: OFF")
        self.assertIn("raw takeover True | effective takeover False", rows[1]["body"])

        audit_rows = build_play_model_takeover_gate_audit_rows(
            {
                "takeover_gate_history_count": 2,
                "takeover_gate_history": [
                    {
                        "status": "watch",
                        "transition": "block->watch",
                        "reason": "total_goals_model_no_uplift",
                        "updated_at": "2026-05-13 11:00:00",
                        "policy_impact": "formal_takeover_disabled",
                        "metrics": {
                            "validation_sample_count": 320,
                            "total_goals_model_delta": -0.005,
                            "score_model_delta": 0.002,
                        },
                        "report_path": "reports/play.md",
                    },
                    {
                        "status": "block",
                        "transition": "none->block",
                        "reason": "validation_sample_count_low",
                        "updated_at": "2026-05-13 10:00:00",
                        "policy_impact": "formal_takeover_disabled",
                    },
                ],
            }
        )
        self.assertEqual(audit_rows[0]["title"], "Takeover gate audit: 2 transition(s)")
        self.assertEqual(audit_rows[0]["tone"], "warning")
        self.assertIn("latest block->watch", audit_rows[0]["body"])
        self.assertEqual(audit_rows[1]["title"], "Previous gate transition: none->block")

    def test_play_model_training_and_backtest(self) -> None:
        status_text = build_play_model_training_status_text(
            {
                "total_goals": {"model_ready": True, "usable_count": 100, "model_updated_at": "2026-04-04", "class_names": ["2", "3"]},
                "scoreline": {"model_ready": True, "usable_count": 80, "model_updated_at": "2026-04-04", "class_names": ["1-0"]},
                "volatile_scoreline": {"model_ready": False, "usable_count": 20, "model_updated_at": "-", "class_names": ["2-1"]},
            }
        )
        self.assertIn("玩法模型状态", status_text)
        self.assertIn("总进球类别数: 2", status_text)

        train_result = {
            "trained": True,
            "total_goals": {"reason": "ok", "usable_count": 100, "updated_at": "2026-04-04"},
            "scoreline": {"reason": "ok", "usable_count": 80, "updated_at": "2026-04-04"},
            "volatile_scoreline": {"reason": "skip", "usable_count": 20, "updated_at": "-"},
            "auto_backtest": {
                "executed": True,
                "ok": True,
                "reason": "ok",
                "report_path": "play_auto.md",
                "takeover_gate": {"status": "allow", "recommendation": "Backtest is stable enough."},
            },
            "postcheck": {
                "status": "ready_for_backtest",
                "recommendation": "进入稳定性回测。",
                "report_path": "training_followup_play.md",
            },
        }
        self.assertIn("玩法模型完成", build_train_play_models_apply_status_text(train_result))
        self.assertIn("自动回测=完成", build_train_play_models_apply_status_text(train_result))
        train_msg = build_train_play_models_apply_message(train_result, status_text)
        self.assertIn("玩法模型训练: 完成", train_msg)
        self.assertIn("高波动比分: skip", train_msg)
        self.assertIn("训练后复检", train_msg)
        self.assertIn("Takeover gate: allow", train_msg)
        self.assertIn("回测报告: play_auto.md", train_msg)
        self.assertIn("闭环报告: training_followup_play.md", train_msg)

        backtest_result = {
            "ok": True,
            "improvement": {"handicap_shadow_delta": 0.01, "total_goals_model_delta": 0.02, "score_model_delta": 0.03},
            "validation": {"sample_count": 50, "date_start": "2026-01-01", "date_end": "2026-03-01"},
            "metrics": {
                "handicap_baseline": {"accuracy": 0.4},
                "handicap_current": {"accuracy": 0.45},
                "handicap_shadow": {"accuracy": 0.5},
                "total_goals_baseline": {"accuracy": 0.3},
                "total_goals_current": {"accuracy": 0.35},
                "total_goals_model": {"accuracy": 0.38},
                "score_baseline": {"accuracy": 0.1},
                "score_current": {"accuracy": 0.12},
                "score_model": {"accuracy": 0.14},
                "score_volatile_model_volatile": {"accuracy": 0.2, "hits": 2, "total": 10},
            },
            "takeover_gate": {"status": "watch", "mode": "watch_only", "recommendation": "Run another stable backtest."},
            "report_path": "play.md",
        }
        self.assertIn("玩法回测完成", build_play_model_backtest_apply_status_text(backtest_result))
        self.assertIn("gate watch", build_play_model_backtest_apply_status_text(backtest_result))
        backtest_msg = build_play_model_backtest_success_message(backtest_result)
        self.assertIn("玩法回测完成", backtest_msg)
        self.assertIn("报告: play.md", backtest_msg)
        self.assertIn("Takeover gate", backtest_msg)
        self.assertIn("Status: watch", backtest_msg)


    def test_draw_specialist_backtest_text_and_cards(self) -> None:
        result = {
            "ok": True,
            "updated_at": "2026-05-11 12:00:00",
            "validation": {"sample_count": 100, "date_start": "2025-01-01", "date_end": "2025-12-31"},
            "summary": {
                "sample_count": 100,
                "actual_draw_count": 25,
                "actual_draw_rate_text": "25.0%",
                "predicted_draw_count": 10,
                "draw_hit_count": 4,
                "precision_text": "40.0%",
                "recall_text": "16.0%",
                "missed_draw_count": 21,
                "false_positive_count": 6,
                "recommendation": "enable_draw_watch",
                "recommendation_text": "保留博平并观察防平。",
                "guard": {"sample_count": 30, "actual_draw_count": 12, "draw_rate_text": "40.0%", "lift": 0.15, "lift_text": "+15.0%"},
                "takeover": {"sample_count": 10, "precision_text": "40.0%", "recall_text": "16.0%"},
            },
            "draw_release_guard_policy": {
                "enabled": True,
                "min_score": 0.58,
                "weak_odds_buckets": {"<=3.00": {"precision": 0.222222}, ">4.20": {"draw_rate": 0.149425}},
            },
            "report_path": "draw.md",
        }

        status_text = build_draw_specialist_backtest_status_text(result)
        self.assertIn("Draw release guard (watch-only): active=True", status_text)
        self.assertIn("blocked_odds=<=3.00, >4.20", status_text)
        self.assertIn("平局专项诊断", status_text)
        self.assertIn("精确率 40.0%", status_text)
        self.assertIn("报告: draw.md", status_text)
        self.assertIn("平局专项回测完成", build_draw_specialist_backtest_apply_status_text(result))
        rows = build_draw_specialist_backtest_card_rows(result)
        self.assertEqual(rows[2]["title"], "Draw release guard (watch-only)")
        self.assertIn("score_floor=0.58", rows[2]["body"])
        self.assertEqual(rows[0]["tone"], "good")
        self.assertIn("精确 40.0%", rows[0]["title"])


if __name__ == "__main__":
    unittest.main()
