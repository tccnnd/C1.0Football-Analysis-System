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
            snapshot_migration_report={
                "total_snapshots": 10,
                "resolved": 8,
                "already_bound": 1,
                "unresolved": 1,
                "trace_fact_ref_backfill": {
                    "checked": 24,
                    "updated": 24,
                    "fact_ref_kinds": {"match_fact": 24, "source_provenance": 24},
                },
                "analysis_history_trace_fact_ref_backfill": {
                    "checked": 213,
                    "updated": 213,
                    "fact_ref_kinds": {"match_fact": 213, "source_provenance": 213},
                },
            },
            xgb_status={"sample_count": 120, "valid_feature_count": 110, "label_counts": {0: 40, 1: 30, 2: 50}, "model_ready": True, "model_updated_at": "2026-04-04"},
        )
        self.assertIn("V24 取数诊断", text)
        self.assertIn("fixture_source_guard: 通过", text)
        self.assertIn("fixture_page_guard: 未通过", text)
        self.assertIn("快照迁移", text)
        self.assertIn("Trace Fact 回填", text)
        self.assertIn("Analysis History Trace 回填", text)
        self.assertIn("updated: 213", text)
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
            "market_entropy": {
                "level": "HIGH",
                "score": 0.72,
                "signals": ["market_steam_against_pick", "kelly_against_pick"],
                "odds_slope": {"home": -0.05, "draw": 0.01, "away": 0.08},
                "sequence": {
                    "sample_count": 3,
                    "latest_interval_minutes": 10.0,
                    "latest_velocity": {"home": -0.004, "draw": 0.001, "away": 0.006},
                    "max_step_change": 0.08,
                    "step_side": "away",
                },
                "strongest_steam_side": "away",
                "market_favorite": "home",
                "kelly": {"home": 0.96, "draw": 0.91, "away": 0.88},
                "kelly_span": 0.08,
                "kelly_low_side": "away",
                "pick_side": "home",
                "pick_slope": -0.05,
                "pick_kelly_gap": 0.08,
            },
            "market_entropy_risk": {
                "applied": True,
                "reason": "market_entropy_high",
                "base_risk_level": "LOW",
                "adjusted_risk_level": "HIGH",
            },
            "handicap_margin_consistency": {
                "level": "HIGH",
                "score": 0.79,
                "signals": ["line_too_deep_for_model", "handicap_pick_margin_mismatch"],
                "handicap_line": -1.25,
                "model_margin_goals": 0.10,
                "market_side": "home",
                "model_side": "balanced",
                "model_pick_side": "home",
                "handicap_pick_side": "away",
                "line_depth": 1.25,
                "margin_depth": 0.10,
                "depth_gap": 1.15,
            },
            "supervisor": {
                "status": "alert",
                "decision": {"release_allowed": False, "requires_human_review": True},
                "next_actions": ["manual_market_review", "capture_next_market_snapshot"],
                "agents": [
                    {"name": "DataHunter", "status": "ready", "trigger": "match_loaded", "outputs": {"history_samples": 3}},
                    {
                        "name": "MarketEntropy",
                        "status": "alert",
                        "trigger": "market_signal_check",
                        "outputs": {"signals": ["market_steam_against_pick"]},
                        "rationale": "Market pressure is abnormal and requires review.",
                        "actions": ["manual_market_review"],
                    },
                    {"name": "Simulation", "status": "ready", "trigger": "probability_fusion", "outputs": {"recommendation": "涓昏儨"}},
                    {"name": "RiskGuardian", "status": "alert", "trigger": "risk_overlay", "outputs": {"admission_decision": "observe"}},
                ],
            },
            "draw_score": 0.34,
            "draw_grade": "B",
            "draw_release_guard": {
                "blocked": True,
                "reason": "weak_draw_odds_bucket",
                "weak_score": True,
                "base_takeover": True,
                "odds_bucket": "<=3.00",
                "odds_draw": 2.95,
                "min_score": 0.58,
                "evidence": {
                    "precision": 0.222222,
                    "draw_rate": 0.157895,
                    "lift": -0.075439,
                    "source": "draw_specialist_backtest",
                },
            },
            "play_strategy": {
                "single": [{"play_type": "1x2", "pick": "主胜", "confidence": 0.62}],
                "parlay": [{"play_type": "totals", "pick": "2球", "confidence": 0.55}],
                "display_only": [],
            },
            "strategy_admission": {
                "label": "正式放行",
                "release_allowed": True,
                "active_count": 1,
                "active_strategy_min": 1,
                "shadow_count": 0,
                "confidence": 0.62,
                "min_confidence": 0.50,
                "block_confidence": 0.40,
                "medium_risk_allowed": True,
                "high_risk_allowed": False,
                "top_play": "market_1x2",
                "top_pick": "涓昏儨",
                "top_confidence": 0.62,
                "reasons": ["high_accuracy_strategy_active", "risk_low"],
                "agent_replay_guard": {
                    "applied": True,
                    "top_agent": "RiskGuardian",
                    "top_prediction_miss_rate": 0.60,
                    "top_handicap_miss_rate": 0.80,
                    "actions": ["review_handicap_margin_consistency"],
                },
            },
            "high_accuracy_strategy": {
                "enabled": True,
                "active": True,
                "active_count": 1,
                "play_type": "market_1x2",
                "pick": "HOME",
                "confidence": 0.70,
                "min_confidence": 0.65,
                "backtest_accuracy": 0.796117,
                "backtest_hits": 164,
                "backtest_samples": 206,
                "summary": "market_1x2 HOME",
                "reason": "matched",
                "active_matches": [
                    {
                        "play_type": "market_1x2",
                        "pick": "HOME",
                        "confidence": 0.70,
                        "min_confidence": 0.65,
                        "backtest_accuracy": 0.796117,
                        "backtest_hits": 164,
                        "backtest_samples": 206,
                        "wilson_lower": 0.757916,
                        "layer": {"data_layer": "jc_stratified_market"},
                        "jc_bucket": {
                            "dimension": "league_confidence_bucket",
                            "bucket": "L1 | >=0.65",
                            "accuracy": 0.796117,
                            "hit_count": 164,
                            "sample_count": 206,
                            "wilson_lower": 0.757916,
                            "stability": {"stable": True, "stability_score": 0.795, "recent_30_accuracy": 0.733333},
                        },
                        "jc_context": {"confidence_bucket": ">=0.65", "odds_bucket": "<=1.50", "pick_odds": 1.24},
                    }
                ],
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
        self.assertIn("策略准入白名单", text)
        self.assertIn("正式放行", text)
        self.assertIn("放行解释", text)
        self.assertIn("实盘待反馈", text)
        self.assertIn("\u547d\u4e2d\u6b63\u5f0f\u9ad8\u51c6\u7b56\u7565", text)
        self.assertIn("\u51c6\u5165\u95e8\u69db", text)
        self.assertIn("Agent Replay", text)
        self.assertIn("RiskGuardian", text)
        self.assertIn("\u9ad8\u51c6 1/1", text)
        self.assertIn("Confidence Calibration", text)
        self.assertIn("Runtime Threshold Guard", text)
        self.assertIn("Draw Release Guard", text)
        self.assertIn("release=blocked", text)
        self.assertIn("blocked_odds=<=3.00", text)
        self.assertIn("score_floor=58.0%", text)
        self.assertIn("raw_takeover=True", text)
        self.assertIn("weak_draw_odds_bucket", text)
        self.assertIn("draw_specialist_backtest", text)
        self.assertIn("MarketEntropy", text)
        self.assertIn("Kelly", text)
        self.assertIn("sequence", text)
        self.assertIn("Handicap Margin Consistency", text)
        self.assertIn("line_too_deep_for_model", text)
        self.assertIn("Supervisor / Orchestrator", text)
        self.assertIn("manual_market_review", text)
        self.assertIn("Market pressure is abnormal", text)
        self.assertIn("market_steam_against_pick", text)
        self.assertIn("JC stable bucket", text)
        self.assertIn("L1 | >=0.65", text)
        self.assertIn("Wilson 75.8%", text)


if __name__ == "__main__":
    unittest.main()
