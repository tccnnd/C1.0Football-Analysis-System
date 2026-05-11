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
    build_play_model_training_status_text,
    build_play_threshold_apply_status_text,
    build_play_threshold_apply_success_message,
    build_play_threshold_status_text,
    build_train_play_models_apply_message,
    build_train_play_models_apply_status_text,
)


class UIModelStatusFlowModuleTests(unittest.TestCase):
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
                "statsbomb_events": {"match_count": 3, "review_sample_count": 2, "review_feature_count": 38},
            },
        )

        self.assertIn("StatsBomb事件: 3 场", text)
        self.assertIn("复盘样本=2", text)

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
        }
        self.assertIn("玩法模型完成", build_train_play_models_apply_status_text(train_result))
        train_msg = build_train_play_models_apply_message(train_result, status_text)
        self.assertIn("玩法模型训练: 完成", train_msg)
        self.assertIn("高波动比分: skip", train_msg)

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
            "report_path": "play.md",
        }
        self.assertIn("玩法回测完成", build_play_model_backtest_apply_status_text(backtest_result))
        backtest_msg = build_play_model_backtest_success_message(backtest_result)
        self.assertIn("玩法回测完成", backtest_msg)
        self.assertIn("报告: play.md", backtest_msg)


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
        self.assertIn("Draw release guard: active=True", status_text)
        self.assertIn("blocked_odds=<=3.00, >4.20", status_text)
        self.assertIn("平局专项诊断", status_text)
        self.assertIn("精确率 40.0%", status_text)
        self.assertIn("报告: draw.md", status_text)
        self.assertIn("平局专项回测完成", build_draw_specialist_backtest_apply_status_text(result))
        rows = build_draw_specialist_backtest_card_rows(result)
        self.assertEqual(rows[2]["title"], "Draw release guard")
        self.assertIn("score_floor=0.58", rows[2]["body"])
        self.assertEqual(rows[0]["tone"], "good")
        self.assertIn("精确 40.0%", rows[0]["title"])


if __name__ == "__main__":
    unittest.main()
