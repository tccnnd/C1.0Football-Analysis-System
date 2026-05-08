from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.ui_modules import (
    adapt_release_review_result,
    adapt_shadow_comparison_result,
    build_release_review_status_text,
    build_shadow_comparison_status_text,
)


class UIC1RuntimeAdaptersModuleTests(unittest.TestCase):
    def test_adapt_shadow_comparison_result(self) -> None:
        row = SimpleNamespace(
            match_id="m1",
            match_label="A vs B",
            v24_recommendation="主胜",
            v24_confidence=0.62,
            c1_predicted_side="HOME_WIN",
            c1_confidence=0.58,
            governance_action="APPROVE",
            suggested_action="可放行",
            primary_reason_code="OK",
            governance_reason_codes=["OK"],
            side_diverged=False,
            near_block=False,
            confidence_gap=0.04,
        )
        adapted = adapt_shadow_comparison_result(
            SimpleNamespace(
                total_matches=1,
                summary={"governance_counts": {"APPROVE": 1}},
                markdown_report="a.md",
                json_report="a.json",
                rows=[row],
            )
        )
        self.assertEqual(adapted["total_matches"], 1)
        self.assertEqual(adapted["rows"][0]["match_id"], "m1")
        self.assertEqual(adapted["rows"][0]["governance_reason_codes"], ["OK"])

    def test_adapt_release_review_result_and_statuses(self) -> None:
        row = SimpleNamespace(
            match_id="m2",
            match_label="C vs D",
            governance_action="OBSERVE",
            release_action="HOLD",
            release_allowed=False,
            primary_reason_code="LINEUP",
            candidate_count=2,
            top_play="1x2",
            top_selection="DRAW",
            top_line=None,
            top_confidence=0.44,
            provider_name="provider",
        )
        adapted = adapt_release_review_result(
            SimpleNamespace(total_matches=1, summary={"release_allowed_count": 0}, rows=[row])
        )
        self.assertEqual(adapted["rows"][0]["match_id"], "m2")
        self.assertFalse(adapted["rows"][0]["release_allowed"])
        self.assertIn("场次 3", build_shadow_comparison_status_text(3, {"APPROVE": 2}))
        self.assertIn("可放行 1", build_release_review_status_text(3, 1))


if __name__ == "__main__":
    unittest.main()
