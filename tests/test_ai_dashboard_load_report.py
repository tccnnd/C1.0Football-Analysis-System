from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.ai_dashboard import (
    DashboardRow,
    _build_dashboard_rows,
    _build_match_load_report,
    _cache_status_rows,
    _cache_status_summary,
    _cache_status_tone,
    _markdown_report,
    _match_load_failure,
    _source_health_rows,
    _source_health_summary,
)
from v24_app.core import AppMatch


class AIDashboardLoadReportTests(unittest.TestCase):
    def _match(self, home: str, away: str = "B") -> AppMatch:
        return AppMatch(
            home_team=home,
            away_team=away,
            league="Friendly",
            match_time="19:35",
            match_date="2026-05-10",
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.2,
        )

    def test_match_load_failure_keeps_match_context(self) -> None:
        match = self._match("A")

        failure = _match_load_failure(match, "snapshot", ValueError("bad snapshot"))

        self.assertEqual(failure["stage"], "snapshot")
        self.assertEqual(failure["league"], "Friendly")
        self.assertEqual(failure["home"], "A")
        self.assertEqual(failure["away"], "B")
        self.assertIn("bad snapshot", failure["error"])
        self.assertIn("Friendly", failure["match_id"])

    def test_build_dashboard_rows_isolates_prediction_and_snapshot_failures(self) -> None:
        matches = [self._match("A"), self._match("C"), self._match("E")]

        def fake_predict(match: AppMatch) -> dict:
            if match.home_team == "A":
                raise RuntimeError("model failed")
            return {"risk_level": "low", "home": match.home_team}

        def fake_persist(match: AppMatch, prediction: dict) -> None:
            if match.home_team == "C":
                raise ValueError("snapshot failed")

        with (
            patch("v24_app.ai_dashboard.predict_match", side_effect=fake_predict),
            patch("v24_app.ai_dashboard.persist_prediction_snapshot", side_effect=fake_persist),
        ):
            rows, failures = _build_dashboard_rows(matches)

        self.assertEqual([row.match.home_team for row in rows], ["C", "E"])
        self.assertEqual([failure["stage"] for failure in failures], ["predict", "snapshot"])
        self.assertIn("model failed", failures[0]["error"])
        self.assertIn("snapshot failed", failures[1]["error"])

    def test_build_match_load_report_counts_partial_failures(self) -> None:
        failures = [
            {"stage": "predict", "error": "model failed"},
            {"stage": "snapshot", "error": "json failed"},
        ]

        report = _build_match_load_report(
            fetched_count=5,
            row_count=4,
            failures=failures,
            source="live:titan",
            elapsed=1.25,
            source_messages=["source ok"],
        )

        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["fetched_count"], 5)
        self.assertEqual(report["row_count"], 4)
        self.assertEqual(report["failure_count"], 2)
        self.assertEqual(report["predict_failure_count"], 1)
        self.assertEqual(report["snapshot_failure_count"], 1)
        self.assertEqual(report["source_messages"], ["source ok"])
        json.dumps(report, ensure_ascii=False)

    def test_source_health_rows_show_degraded_secondary_source(self) -> None:
        report = _build_match_load_report(
            fetched_count=3,
            row_count=3,
            failures=[],
            source="live:titan",
            source_reports=[
                {"source": "titan", "status": "ready", "raw_count": 3, "valid_count": 3, "coverage": 1.0, "health_score": 100},
                {"source": "500", "status": "empty", "raw_count": 0, "valid_count": 0},
            ],
        )

        rows = _source_health_rows(report)

        self.assertEqual(_source_health_summary(report), "单源支撑 / 1 源异常")
        self.assertEqual(rows[0]["source"], "titan")
        self.assertEqual(rows[0]["tone"], "good")
        self.assertEqual(rows[1]["source"], "500")
        self.assertEqual(rows[1]["tone"], "warning")
        self.assertIn("raw 0 / valid 0", rows[1]["detail"])

    def test_cache_status_summary_marks_fallback_cache(self) -> None:
        report = _build_match_load_report(
            fetched_count=2,
            row_count=2,
            failures=[],
            source="cache_stale",
            cache_exists=True,
            cache_fresh=False,
            cache_date="2026-05-08",
            cache_match_count=2,
            cache_age_days=2,
            force_live=True,
            cache_only=True,
        )

        self.assertEqual(_cache_status_summary(report), "已回退 2026-05-08 / 2 场")
        self.assertEqual(_cache_status_tone(report), "warning")
        rows = dict(_cache_status_rows(report))
        self.assertEqual(rows["缓存日期"], "2026-05-08")
        self.assertEqual(rows["本次强制在线"], "是")
        self.assertEqual(rows["本次读取缓存"], "是")

    def test_build_match_load_report_marks_all_prediction_failures_failed(self) -> None:
        report = _build_match_load_report(
            fetched_count=2,
            row_count=0,
            failures=[
                {"stage": "predict", "error": "one"},
                {"stage": "predict", "error": "two"},
            ],
            source="live:titan",
        )

        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["predict_failure_count"], 2)
        self.assertEqual(report["snapshot_failure_count"], 0)

    def test_markdown_report_includes_market_entropy_and_agent_trace(self) -> None:
        match = self._match("A")
        prediction = {
            "recommendation": "home",
            "confidence": 0.68,
            "risk_level": "HIGH",
            "expected_goals": 2.4,
            "model": "test-model",
            "probabilities": {"home": 0.50, "draw": 0.28, "away": 0.22},
            "market_probabilities": {"home": 0.48, "draw": 0.29, "away": 0.23},
            "elo_probabilities": {"home": 0.51, "draw": 0.27, "away": 0.22},
            "poisson_probabilities": {"home": 0.49, "draw": 0.30, "away": 0.21},
            "xgb_probabilities": {"home": 0.47, "draw": 0.31, "away": 0.22},
            "handicap_probabilities": {"home": 0.44, "draw": 0.28, "away": 0.28},
            "ou_probabilities": {"over": 0.52, "under": 0.48},
            "indices": {"upset_index": 0.30, "stability_index": 0.61, "confidence_index": 0.68, "market_entropy_index": 0.84},
            "market_entropy": {
                "level": "HIGH",
                "score": 0.84,
                "signals": ["kelly_against_pick", "odds_velocity_alert"],
                "odds_slope": {"home": -0.05, "draw": 0.01, "away": 0.08},
                "sequence": {"sample_count": 3, "latest_velocity": {"home": -0.004, "away": 0.006}, "max_step_change": 0.08, "step_side": "away"},
                "strongest_steam_side": "away",
                "market_favorite": "home",
                "kelly": {"home": 0.96, "draw": 0.91, "away": 0.88},
                "kelly_span": 0.08,
                "pick_kelly_gap": 0.08,
            },
            "market_entropy_risk": {"applied": True, "reason": "market_entropy_high"},
            "handicap_margin_consistency": {
                "level": "HIGH",
                "score": 0.82,
                "signals": ["handicap_direction_mismatch"],
                "handicap_line": 0.75,
                "model_margin_goals": 0.60,
                "market_side": "away",
                "model_side": "home",
                "model_pick_side": "home",
                "handicap_pick_side": "away",
                "line_depth": 0.75,
                "margin_depth": 0.60,
                "depth_gap": 0.15,
            },
            "strategy_admission": {
                "release_allowed": False,
                "decision": "observe",
                "reasons": ["risk_high", "agent_replay_policy_watch"],
                "agent_replay_guard": {
                    "applied": True,
                    "top_agent": "RiskGuardian",
                    "top_prediction_miss_rate": 0.56,
                    "top_handicap_miss_rate": 0.67,
                    "actions": ["review_handicap_margin_consistency"],
                },
            },
            "supervisor": {
                "status": "alert",
                "decision": {"release_allowed": False, "requires_human_review": True, "risk_bucket": "high", "market_entropy_level": "HIGH"},
                "next_actions": ["manual_market_review"],
                "agents": [
                    {
                        "name": "MarketEntropy",
                        "status": "alert",
                        "trigger": "market_signal_check",
                        "outputs": {"signals": ["kelly_against_pick"]},
                        "checks": ["entropy level", "Kelly span"],
                        "evidence": {"score": 0.84},
                        "rationale": "Market pressure is abnormal and requires review.",
                        "actions": ["manual_market_review"],
                    },
                    {"name": "RiskGuardian", "status": "alert", "trigger": "risk_overlay", "outputs": {"admission_decision": "observe"}},
                ],
            },
        }

        report = _markdown_report(DashboardRow(match=match, prediction=prediction))

        self.assertIn("MarketEntropy 盘口异常识别", report)
        self.assertIn("kelly_against_pick", report)
        self.assertIn("Handicap Margin Consistency", report)
        self.assertIn("handicap_direction_mismatch", report)
        self.assertIn("Supervisor / Agent Trace", report)
        self.assertIn("manual_market_review", report)
        self.assertIn("MarketEntropy / ALERT", report)
        self.assertIn("Market pressure is abnormal", report)
        self.assertIn("checks: entropy level", report)
        self.assertIn("Agent Replay", report)
        self.assertIn("RiskGuardian", report)


if __name__ == "__main__":
    unittest.main()
