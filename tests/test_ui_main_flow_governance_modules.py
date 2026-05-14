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
    filter_main_flow_governance_rows,
    build_main_flow_governance_status,
    build_main_flow_governance_status_text,
    summarize_main_flow_governance_statuses,
)


class UIMainFlowGovernanceModuleTests(unittest.TestCase):
    def _allow_prediction(self, *, top_play: str = "market_1x2") -> dict:
        return {
            "strategy_admission": {
                "decision": "allow",
                "label": "\u6b63\u5f0f\u653e\u884c",
                "release_allowed": True,
                "top_play": top_play,
                "top_pick": "home",
                "top_confidence": 0.72,
            }
        }

    def _release_row(self) -> dict:
        return {
            "match_id": "m1",
            "release_allowed": True,
            "governance_action": "APPROVE",
            "release_action": "APPROVE_RELEASE",
            "top_play": "1x2",
            "top_selection": "HOME_WIN",
            "top_confidence": 0.72,
            "primary_reason_code": "OK",
        }

    def test_formal_ready_when_all_gates_pass(self) -> None:
        status = build_main_flow_governance_status(
            prediction=self._allow_prediction(),
            c1_release_row=self._release_row(),
            play_policy_status={"takeover_gate": {"status": "allow", "recommendation": "Stable."}},
            recovery_loop={"health": "good", "health_text": "\u95ed\u73af\u5b8c\u6210", "rows": []},
            match_id="m1",
        )

        self.assertEqual(status["status"], "formal_ready")
        self.assertTrue(status["formal_allowed"])
        self.assertEqual(status["tone"], "good")
        self.assertEqual([item["label"] for item in status["decision_chain"]], ["\u7b56\u7565\u51c6\u5165", "C1\u6cbb\u7406", "\u63a5\u7ba1Gate", "\u590d\u76d8\u95ed\u73af"])

    def test_needs_c1_review_when_strategy_allows_but_c1_is_missing(self) -> None:
        status = build_main_flow_governance_status(
            prediction=self._allow_prediction(),
            c1_release_row={},
            play_policy_status={"takeover_gate": {"status": "allow"}},
            recovery_loop={"health": "good"},
            match_id="m1",
        )

        self.assertEqual(status["status"], "needs_c1_review")
        self.assertFalse(status["formal_allowed"])
        self.assertIn("C1", status["primary_blocker"])
        self.assertEqual(status["decision_chain"][1]["value"], "missing")

    def test_blocks_on_strategy_or_c1_block(self) -> None:
        strategy_blocked = build_main_flow_governance_status(
            prediction={"strategy_admission": {"decision": "block", "label": "\u963b\u65ad"}},
            c1_release_row=self._release_row(),
            play_policy_status={"takeover_gate": {"status": "allow"}},
            recovery_loop={},
            match_id="m1",
        )
        c1_blocked = build_main_flow_governance_status(
            prediction=self._allow_prediction(),
            c1_release_row={"match_id": "m1", "governance_action": "BLOCK", "suggested_action": "\u963b\u65ad"},
            play_policy_status={"takeover_gate": {"status": "allow"}},
            recovery_loop={},
            match_id="m1",
        )

        self.assertEqual(strategy_blocked["status"], "blocked")
        self.assertEqual(c1_blocked["status"], "blocked")
        self.assertFalse(c1_blocked["formal_allowed"])

    def test_takeover_gate_blocks_only_takeover_sensitive_play(self) -> None:
        blocked = build_main_flow_governance_status(
            prediction=self._allow_prediction(top_play="total_goals"),
            c1_release_row={**self._release_row(), "top_play": "totals"},
            play_policy_status={
                "policy_blocked_by_gate": True,
                "takeover_gate": {"status": "block", "recommendation": "Model takeover regressed."},
            },
            recovery_loop={"health": "good"},
            match_id="m1",
        )
        warned_only = build_main_flow_governance_status(
            prediction=self._allow_prediction(top_play="market_1x2"),
            c1_release_row=self._release_row(),
            play_policy_status={
                "policy_blocked_by_gate": True,
                "takeover_gate": {"status": "block", "recommendation": "Model takeover regressed."},
            },
            recovery_loop={"health": "good"},
            match_id="m1",
        )

        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["decision_chain"][2]["value"], "blocked")
        self.assertEqual(warned_only["status"], "formal_ready")
        self.assertEqual(warned_only["decision_chain"][2]["tone"], "warning")

    def test_recovery_loop_blocks_stale_match_release(self) -> None:
        status = build_main_flow_governance_status(
            prediction=self._allow_prediction(),
            c1_release_row=self._release_row(),
            play_policy_status={"takeover_gate": {"status": "allow"}},
            recovery_loop={
                "health": "warning",
                "health_text": "\u9700\u8865\u56de\u6536",
                "rows": [
                    {
                        "match_id": "m1",
                        "loop_status": "\u7f3a\u5feb\u7167",
                        "pending": True,
                        "snapshot_saved": False,
                        "settled": False,
                        "pending_days": 2,
                    }
                ],
            },
            match_id="m1",
        )

        self.assertEqual(status["status"], "needs_recovery")
        self.assertFalse(status["formal_allowed"])
        self.assertEqual(status["decision_chain"][3]["value"], "needs_recovery")

    def test_status_text_and_summary_counts(self) -> None:
        ready = build_main_flow_governance_status(
            prediction=self._allow_prediction(),
            c1_release_row=self._release_row(),
            play_policy_status={"takeover_gate": {"status": "allow"}},
            recovery_loop={"health": "good"},
            match_id="m1",
        )
        pending = build_main_flow_governance_status(
            prediction=self._allow_prediction(),
            c1_release_row={},
            play_policy_status={"takeover_gate": {"status": "allow"}},
            recovery_loop={"health": "good"},
            match_id="m2",
        )

        text = build_main_flow_governance_status_text(ready)
        counts = summarize_main_flow_governance_statuses([ready, pending])

        self.assertIn("Main Flow Governance", text)
        self.assertIn("formal_ready", text)
        self.assertIn("Decision chain", text)
        self.assertEqual(counts["formal_ready"], 1)
        self.assertEqual(counts["needs_c1_review"], 1)

    def test_filter_main_flow_governance_rows(self) -> None:
        rows = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        statuses = {
            "a": {"status": "formal_ready"},
            "b": {"status": "blocked"},
            "c": {"status": "needs_recovery"},
        }

        def status_fn(item: dict) -> dict:
            return statuses[item["id"]]

        self.assertEqual([item["id"] for item in filter_main_flow_governance_rows(rows, "all", status_fn=status_fn)], ["a", "b", "c"])
        self.assertEqual([item["id"] for item in filter_main_flow_governance_rows(rows, "formal_ready", status_fn=status_fn)], ["a"])
        self.assertEqual([item["id"] for item in filter_main_flow_governance_rows(rows, "blocked", status_fn=status_fn)], ["b"])
        self.assertEqual([item["id"] for item in filter_main_flow_governance_rows(rows, "needs_recovery", status_fn=status_fn)], ["c"])


if __name__ == "__main__":
    unittest.main()
