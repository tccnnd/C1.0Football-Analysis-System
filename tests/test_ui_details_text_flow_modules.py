from __future__ import annotations

import sys
import unittest
from types import SimpleNamespace
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.core import AppMatch
from v24_app.ui_modules import (
    build_diagnostics_text,
    build_match_details_text,
    build_pending_match_details_text,
    build_poisson_block,
)


class UIDetailsTextFlowModuleTests(unittest.TestCase):
    def test_build_diagnostics_text(self) -> None:
        diagnostics = SimpleNamespace(
            fixture_source_guard=True,
            fixture_page_guard=False,
            cache_fresh=True,
            fetched_at="2026-04-04 12:00:00",
            source="live:titan",
            messages=["ok1", "ok2"],
        )
        text = build_diagnostics_text(
            diagnostics=diagnostics,
            snapshot_migration_report={"total_snapshots": 10, "resolved": 8, "already_bound": 1, "unresolved": 1},
            xgb_status={"sample_count": 120, "valid_feature_count": 110, "label_counts": {0: 40, 1: 30, 2: 50}, "model_ready": True, "model_updated_at": "2026-04-04"},
        )
        self.assertIn("V24 取数诊断", text)
        self.assertIn("fixture_source_guard: 通过", text)
        self.assertIn("fixture_page_guard: 未通过", text)
        self.assertIn("快照迁移", text)
        self.assertIn("labels(主/平/客): 40/30/50", text)

    def test_build_pending_match_details_text(self) -> None:
        match = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="19:35",
            match_date="2026-04-04",
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.1,
        )
        text = build_pending_match_details_text(diagnostics_text="DX", match=match)
        self.assertIn("DX", text)
        self.assertIn("A vs B", text)
        self.assertIn("主胜 1.90", text)

    def test_build_poisson_block_and_match_details_text(self) -> None:
        poisson_block = build_poisson_block(
            {
                "home_lambda": 1.3,
                "away_lambda": 0.9,
                "btts_yes": 0.42,
                "btts_no": 0.58,
                "halftime_probabilities": {"home": 0.33, "draw": 0.44, "away": 0.23},
                "top_scores": [{"score": "1-0", "probability": 0.12}],
                "top_total_goals": [{"goals": 2, "probability": 0.31}],
                "htft_top": [{"label": "胜-胜", "probability": 0.18}],
            }
        )
        self.assertIn("Poisson 分布预测", poisson_block)
        self.assertIn("最可能比分", poisson_block)

        match = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="19:35",
            match_date="2026-04-04",
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.1,
            source="live:titan",
        )
        prediction = {
            "recommendation": "主胜",
            "risk_level": "中",
            "confidence": 0.62,
            "confidence_raw": 0.76,
            "confidence_calibration": {
                "raw_confidence": 0.76,
                "calibrated_confidence": 0.62,
                "scale": 0.82,
                "bin": "b3",
                "bin_sample_count": 42,
            },
            "play_threshold_adjustment": {
                "window": 120,
                "settlement_sample_count": 120,
                "single_gate": {
                    "hit_rate": 0.33,
                    "expected_hit_rate": 0.61,
                    "ev_bias": -0.28,
                    "losing_streak": 2,
                    "breaker_on": False,
                },
                "per_play": {
                    "1x2": {"old": 0.78, "new": 0.78, "delta": 0.0, "reasons": ["ev_bias_very_low"]},
                    "handicap": {"old": 0.75, "new": 0.78, "delta": 0.03, "reasons": ["ev_bias_low"]},
                },
            },
            "expected_goals": 2.34,
            "model": "ensemble",
            "probabilities": {"home": 0.5, "draw": 0.28, "away": 0.22},
            "market_probabilities": {"home": 0.48, "draw": 0.29, "away": 0.23},
            "elo_probabilities": {"home": 0.51, "draw": 0.27, "away": 0.22},
            "poisson_probabilities": {"home": 0.49, "draw": 0.30, "away": 0.21},
            "xgb_probabilities": {"home": 0.47, "draw": 0.31, "away": 0.22},
            "handicap_display": "-0.5 主让",
            "handicap_confidence": 0.56,
            "xgb_fallback": False,
            "xgb_model_ready": True,
            "elo": {"home_rating": 1520.1, "home_score": 61.2, "away_rating": 1498.4, "away_score": 58.7, "rating_diff": 21.7},
            "indices": {"upset_index": 0.11, "stability_index": 0.67, "confidence_index": 0.62},
            "draw_score": 0.34,
            "draw_grade": "B",
            "play_strategy": {
                "single": [{"play_type": "1x2", "pick": "主胜", "confidence": 0.62}],
                "parlay": [{"play_type": "totals", "pick": "2球", "confidence": 0.55}],
                "display_only": [],
            },
        }
        settlement = {
            "home_goals": 2,
            "away_goals": 1,
            "result": "HOME_WIN",
            "predicted": "主胜",
            "is_correct": True,
            "handicap_result": "主让胜",
            "predicted_handicap": "-0.5 主让",
            "handicap_is_correct": True,
            "total_goals": 3,
            "predicted_total_goals": "3球",
            "total_goals_is_correct": True,
            "predicted_score": "2-1",
            "score_is_correct": True,
            "predicted_htft": "胜-胜",
            "home_delta": 8,
            "away_delta": -8,
        }
        text = build_match_details_text(
            diagnostics_text="DX",
            match=match,
            prediction=prediction,
            total_goals_pick="3球",
            total_goals_conf=0.45,
            htft_pick="胜-胜",
            htft_conf=0.21,
            score_pick="2-1",
            score_conf=0.12,
            gated_recommendation="主胜",
            release_row={"release_allowed": True, "release_action": "ALLOW", "top_play": "1x2", "top_selection": "HOME_WIN", "top_confidence": 0.62, "provider_name": "provider"},
            settlement=settlement,
            mark_text_fn=lambda v: "Y" if v else "N",
            poisson_block_text=poisson_block,
        )
        self.assertIn("比赛分析", text)
        self.assertIn("融合概率", text)
        self.assertIn("模型拆解", text)
        self.assertIn("赛果结算", text)
        self.assertIn("C1 放行门控", text)
        self.assertIn("Confidence Calibration", text)
        self.assertIn("Runtime Threshold Guard", text)


if __name__ == "__main__":
    unittest.main()
