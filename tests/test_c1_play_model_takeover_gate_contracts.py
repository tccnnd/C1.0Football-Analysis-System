from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from c1.data import (
    PlayModelTakeoverGateAuditEntry,
    PlayModelTakeoverGateAuditReport,
    PlayModelTakeoverGateAuditSummary,
    build_play_model_takeover_gate_audit_entry,
    build_play_model_takeover_gate_audit_report,
    build_play_model_takeover_gate_audit_summary,
)


class C1PlayModelTakeoverGateContractTests(unittest.TestCase):
    def test_build_audit_entry_normalizes_history_payload(self) -> None:
        entry = build_play_model_takeover_gate_audit_entry(
            {
                "version_id": "20260518101010_0001",
                "updated_at": "2026-05-18 10:10:10",
                "source": "backtest",
                "previous_status": "block",
                "status": "watch",
                "transition": "block->watch",
                "reason": "total_goals_model_no_uplift",
                "recommendation": "keep shadow mode",
                "policy_impact": "formal_takeover_disabled",
                "blocking_count": "0",
                "warning_count": "1",
                "issue_codes": ["total_goals_model_no_uplift", ""],
                "metrics": {
                    "validation_sample_count": "420",
                    "total_goals_model_delta": "-0.005",
                    "score_model_delta": "0.002",
                },
                "validation": {"sample_count": 400},
                "backtest_ok": "true",
                "backtest_reason": "ok",
                "report_path": "reports/play_model_backtest.md",
            }
        )

        self.assertIsInstance(entry, PlayModelTakeoverGateAuditEntry)
        self.assertEqual(entry.version_id, "20260518101010_0001")
        self.assertEqual(entry.previous_status, "block")
        self.assertEqual(entry.status, "watch")
        self.assertEqual(entry.warning_count, 1)
        self.assertEqual(entry.issue_codes, ["total_goals_model_no_uplift"])
        self.assertEqual(entry.validation_sample_count, 420)
        self.assertAlmostEqual(entry.total_goals_model_delta, -0.005)
        self.assertAlmostEqual(entry.score_model_delta, 0.002)
        self.assertTrue(entry.backtest_ok)

    def test_build_audit_summary_and_report_normalize_exports(self) -> None:
        summary = build_play_model_takeover_gate_audit_summary(
            {
                "history_count": "3",
                "latest_status": "allow",
                "latest_previous_status": "watch",
                "latest_transition": "watch->allow",
                "latest_reason": "stable",
                "latest_updated_at": "2026-05-18 10:11:00",
                "latest_policy_impact": "formal_takeover_allowed",
                "latest_backtest_ok": "yes",
                "latest_validation_sample_count": "500",
                "latest_total_goals_model_delta": "0.015",
                "latest_score_model_delta": "0.004",
                "latest_report_path": "reports/play_model_backtest.md",
            }
        )
        report = build_play_model_takeover_gate_audit_report(
            {
                "updated_at": "2026-05-18 10:12:00",
                "history_count": "3",
                "latest_transition": "watch->allow",
                "latest_reason": "stable",
                "markdown_path": "reports/audit.md",
                "csv_path": "reports/audit.csv",
            }
        )

        self.assertIsInstance(summary, PlayModelTakeoverGateAuditSummary)
        self.assertEqual(summary.history_count, 3)
        self.assertTrue(summary.latest_backtest_ok)
        self.assertEqual(summary.latest_validation_sample_count, 500)
        self.assertAlmostEqual(summary.latest_total_goals_model_delta, 0.015)
        self.assertIsInstance(report, PlayModelTakeoverGateAuditReport)
        self.assertEqual(report.history_count, 3)
        self.assertEqual(report.markdown_path, "reports/audit.md")
        self.assertEqual(report.csv_path, "reports/audit.csv")


if __name__ == "__main__":
    unittest.main()
