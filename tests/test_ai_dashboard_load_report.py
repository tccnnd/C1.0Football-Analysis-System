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

from v24_app.ai_dashboard import _build_dashboard_rows, _build_match_load_report, _match_load_failure
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


if __name__ == "__main__":
    unittest.main()
