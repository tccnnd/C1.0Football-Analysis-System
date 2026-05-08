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

import v24_app.ui as ui
from v24_app.core import AppMatch


class _DummyVar:
    def __init__(self, value: str) -> None:
        self._value = value

    def get(self) -> str:
        return self._value


class _DummyApp:
    def __init__(self) -> None:
        self.c1_runtime_mode = "formal_list_default"
        self.matches: list[AppMatch] = []
        self.predictions: dict[str, dict] = {}
        self.c1_comparison_marks: dict[str, dict] = {}
        self.status_var = _DummyVar("批量分析完成，共 1 场")

    def _release_allowed_match_ids(self) -> set[str]:
        return {"m1", "m2"}

    def _active_release_allowed_match_ids(self) -> set[str]:
        return {"m1"}

    def _release_gate_pick_text(self, match_id: str, prediction: dict) -> str:
        return str(prediction.get("recommendation", "-"))


class UISmokeLogicTests(unittest.TestCase):
    def test_build_analysis_status_text(self) -> None:
        app = _DummyApp()
        text = ui._app_build_analysis_status_text(app, app.status_var.get(), parlay_count=3)
        self.assertIn("C1放行 1 场", text)
        self.assertIn("二串一 3 组", text)

    def test_build_export_report_lines(self) -> None:
        app = _DummyApp()
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
        match_id = match.match_id
        app.matches = [match]
        app.predictions = {
            match_id: {
                "recommendation": "主胜",
                "handicap_display": "+1 让胜",
                "total_goals_recommendation": "2球",
                "htft_recommendation": "胜/胜",
                "score_recommendation": "1-0",
                "confidence": 0.62,
            }
        }
        app.c1_comparison_marks = {
            match_id: {
                "suggested_action": "可放行",
                "governance_action": "APPROVE",
                "primary_reason_code": "OK",
            }
        }
        lines = ui._app_build_export_report_lines(app, [match], current_filter="正式建议", scope_label="当前筛选视图")
        joined = "\n".join(lines)
        self.assertIn("Current Filter: 正式建议", joined)
        self.assertIn("A vs B", joined)
        self.assertIn("可放行", joined)
        self.assertIn("APPROVE", joined)


if __name__ == "__main__":
    unittest.main()
