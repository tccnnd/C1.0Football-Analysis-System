from __future__ import annotations

import sys
import tempfile
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
    SmartMatchDashboard,
    _append_daily_parlay_snapshot_log,
    _daily_parlay_toolbar_state,
    _load_daily_parlay_snapshot_log,
    _save_daily_parlay_snapshot_log,
)
from v24_app.core import AppMatch


class AIDashboardDailyParlayTests(unittest.TestCase):
    class _StatusVar:
        def __init__(self) -> None:
            self.value = ""

        def set(self, value: str) -> None:
            self.value = value

    class _ParlayStore:
        def __init__(self, tickets: list[dict]) -> None:
            self._tickets = tickets

        def load_parlay_tickets(self) -> list[dict]:
            return self._tickets

    def _match(self, home: str, away: str) -> AppMatch:
        return AppMatch(
            home_team=home,
            away_team=away,
            league="L1",
            match_time="20:00",
            match_date="2026-05-18",
            odds_home=2.1,
            odds_draw=3.2,
            odds_away=3.4,
        )

    def test_daily_parlay_snapshot_refreshes_from_current_rows(self) -> None:
        dashboard = object.__new__(SmartMatchDashboard)
        dashboard._log_event = lambda *args, **kwargs: None
        first = self._match("A", "B")
        second = self._match("C", "D")
        dashboard.rows = [
            DashboardRow(first, {"parlay_eligible_plays": [{"play_type": "1x2", "pick": "home", "confidence": 0.72}]}),
            DashboardRow(second, {"parlay_eligible_plays": [{"play_type": "total_goals", "pick": "over", "confidence": 0.70}]}),
        ]
        active = [
            {
                "ticket_id": "ticket-1",
                "status": "pending",
                "expected_hit": 0.35,
                "mixed": True,
                "legs": [{"match_id": first.match_id}, {"match_id": second.match_id}],
            }
        ]

        with patch("v24_app.ai_dashboard.refresh_parlay_recommendations", return_value=active) as refresh, patch(
            "v24_app.ai_dashboard.get_recent_parlay_settlements",
            return_value=[{"ticket_id": "settled", "status": "won", "is_hit": True}],
        ), patch(
            "v24_app.ai_dashboard.get_parlay_selector_metrics",
            return_value={"ticket_count": 1, "unique_match_count": 2},
        ):
            snapshot = dashboard._daily_parlay_snapshot()

        refresh.assert_called_once()
        self.assertTrue(snapshot["refreshed_from_current"])
        self.assertEqual(snapshot["summary"]["active_count"], 1)
        self.assertEqual(snapshot["summary"]["settled_count"], 1)
        self.assertEqual(snapshot["ticket_rows"][0]["ticket_id"], "ticket-1")

    def test_daily_parlay_snapshot_falls_back_to_saved_active_tickets(self) -> None:
        dashboard = object.__new__(SmartMatchDashboard)
        dashboard._log_event = lambda *args, **kwargs: None
        dashboard.rows = []
        active = [{"ticket_id": "saved", "status": "pending", "expected_hit": 0.31, "legs": []}]

        with patch("v24_app.ai_dashboard.refresh_parlay_recommendations") as refresh, patch(
            "v24_app.ai_dashboard.get_active_parlay_recommendations",
            return_value=active,
        ) as load_active, patch(
            "v24_app.ai_dashboard.get_recent_parlay_settlements",
            return_value=[],
        ), patch(
            "v24_app.ai_dashboard.get_parlay_selector_metrics",
            return_value={"ticket_count": 1},
        ):
            snapshot = dashboard._daily_parlay_snapshot()

        refresh.assert_not_called()
        load_active.assert_called_once()
        self.assertFalse(snapshot["refreshed_from_current"])
        self.assertEqual(snapshot["summary"]["active_count"], 1)
        self.assertEqual(snapshot["ticket_rows"][0]["ticket_id"], "saved")

    def test_daily_parlay_snapshot_log_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily_parlay_snapshot_log.json"
            _append_daily_parlay_snapshot_log({"generated_at": "first", "summary": {"active_count": 1}}, path, limit=2)
            _append_daily_parlay_snapshot_log({"generated_at": "second", "summary": {"active_count": 2}}, path, limit=2)
            _append_daily_parlay_snapshot_log({"generated_at": "third", "summary": {"active_count": 3}}, path, limit=2)

            records = _load_daily_parlay_snapshot_log(path)

        self.assertEqual([record["generated_at"] for record in records], ["third", "second"])
        self.assertEqual(records[0]["summary"]["active_count"], 3)

    def test_daily_parlay_toolbar_state_blocks_export_when_source_health_is_blocked(self) -> None:
        state = _daily_parlay_toolbar_state({"status": "blocked", "tone": "bad", "issue_count": 2}, {})

        self.assertEqual(state["export_state"], "disabled")
        self.assertEqual(state["button_style"], "danger")
        self.assertEqual(state["hint"], "导出已禁用")
        self.assertEqual(state["issue_count"], 2)

    def test_daily_parlay_toolbar_state_keeps_attention_export_confirmable(self) -> None:
        state = _daily_parlay_toolbar_state(
            {},
            {"source_health_status": "attention", "source_health_tone": "warning", "source_health_issue_count": "3"},
        )

        self.assertEqual(state["export_state"], "normal")
        self.assertEqual(state["button_style"], "warning")
        self.assertEqual(state["hint"], "导出需确认")
        self.assertEqual(state["issue_count"], 3)

    def test_daily_parlay_toolbar_state_marks_healthy_export_available(self) -> None:
        state = _daily_parlay_toolbar_state({"status": "healthy", "tone": "good", "issue_count": 0}, {})

        self.assertEqual(state["export_state"], "normal")
        self.assertEqual(state["button_style"], "normal")
        self.assertEqual(state["hint"], "导出可用")

    def test_daily_parlay_repair_queue_snapshot_reads_state_store(self) -> None:
        dashboard = object.__new__(SmartMatchDashboard)
        dashboard._log_event = lambda *args, **kwargs: None
        tickets = [
            {
                "ticket_id": "blocked-1",
                "status": "pending",
                "legs": [{"match_id": "m1", "source": "live:titan", "source_id": "s1"}, {"match_id": "m2"}],
                "settlement_recovery_gate": {
                    "status": "blocked",
                    "code": "parlay_source_traceability_missing",
                    "message": "Missing source/source_id on parlay legs.",
                    "recommendation": "Backfill source and source_id before rerunning recovery.",
                    "source": "live:titan",
                    "source_id": "s1",
                    "leg_count": 2,
                    "missing_source_count": 1,
                    "missing_source_id_count": 1,
                },
            },
            {
                "ticket_id": "ready-1",
                "status": "pending",
                "legs": [
                    {"match_id": "m3", "source": "live:titan", "source_id": "s2"},
                    {"match_id": "m4", "source": "live:titan", "source_id": "s3"},
                ],
                "settlement_recovery_gate": {
                    "status": "ready",
                    "code": "ready",
                    "message": "Parlay ticket is traceable and eligible for automatic settlement.",
                    "recommendation": "Proceed with automatic result recovery.",
                    "source": "live:titan",
                    "source_id": "s2 / s3",
                    "leg_count": 2,
                },
            },
        ]

        with patch("v24_app.ai_dashboard.STATE_STORE", self._ParlayStore(tickets)):
            snapshot = dashboard._daily_parlay_repair_queue_snapshot()

        self.assertEqual(snapshot["summary"]["status"], "attention")
        self.assertEqual(snapshot["summary"]["pending_count"], 2)
        self.assertEqual(snapshot["summary"]["blocked_count"], 1)
        self.assertEqual(snapshot["summary"]["ready_count"], 1)
        self.assertEqual(snapshot["rows"][0]["ticket_id"], "blocked-1")
        self.assertEqual(snapshot["rows"][0]["code"], "parlay_source_traceability_missing")

    def test_export_daily_parlay_report_writes_report_and_snapshot_log(self) -> None:
        dashboard = object.__new__(SmartMatchDashboard)
        dashboard.status_var = self._StatusVar()
        dashboard._log_event = lambda *args, **kwargs: None
        dashboard._daily_parlay_snapshot = lambda: {
            "active_tickets": [
                {
                    "ticket_id": "ticket-1",
                    "status": "pending",
                    "expected_hit": 0.36,
                    "mixed": True,
                    "legs": [
                        {"match_id": "m1", "source": "live:titan", "source_id": "titan-123"},
                        {"match_id": "m2", "source": "live:titan", "source_id": "titan-123"},
                    ],
                }
            ],
            "settled_tickets": [
                {
                    "ticket_id": "won-1",
                    "status": "won",
                    "is_hit": True,
                    "expected_hit": 0.31,
                    "legs": [{"source": "live:titan", "source_id": "titan-123"}],
                }
            ],
            "selector_metrics": {"ticket_count": 1, "unique_match_count": 2},
            "refreshed_from_current": True,
        }

        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp) / "reports"
            log_path = Path(tmp) / "daily_parlay_snapshot_log.json"
            with patch("v24_app.ai_dashboard.REPORT_DIR", report_dir), patch(
                "v24_app.ai_dashboard.DAILY_PARLAY_SNAPSHOT_LOG",
                log_path,
            ), patch("v24_app.ai_dashboard.messagebox.showinfo") as showinfo:
                path = dashboard.export_daily_parlay_report()
            report_payload = path.read_text(encoding="utf-8")
            records = _load_daily_parlay_snapshot_log(log_path)

        self.assertTrue(path.name.startswith("daily_parlay_recommendations_"))
        self.assertIn("每日二串一推荐报告", report_payload)
        self.assertIn("ticket-1", report_payload)
        self.assertIn("won-1", report_payload)
        self.assertIn("live:titan", report_payload)
        self.assertIn("titan-123", report_payload)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source"], "当前分析")
        self.assertEqual(records[0]["summary"]["active_count"], 1)
        self.assertEqual(records[0]["summary"]["source"], "live:titan")
        self.assertEqual(records[0]["summary"]["source_id"], "titan-123")
        self.assertIn("每日二串一报告已导出", dashboard.status_var.value)
        showinfo.assert_called_once()

    def test_export_daily_parlay_report_blocks_when_source_health_is_blocked(self) -> None:
        dashboard = object.__new__(SmartMatchDashboard)
        dashboard.status_var = self._StatusVar()
        dashboard._log_event = lambda *args, **kwargs: None
        dashboard._daily_parlay_snapshot = lambda: {
            "active_tickets": [
                {
                    "ticket_id": "blocked-1",
                    "status": "pending",
                    "legs": [{"match_id": "m1"}, {"match_id": "m2"}],
                }
            ],
            "settled_tickets": [],
            "selector_metrics": {"ticket_count": 1},
            "refreshed_from_current": False,
        }

        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp) / "reports"
            log_path = Path(tmp) / "daily_parlay_snapshot_log.json"
            with patch("v24_app.ai_dashboard.REPORT_DIR", report_dir), patch(
                "v24_app.ai_dashboard.DAILY_PARLAY_SNAPSHOT_LOG",
                log_path,
            ), patch("v24_app.ai_dashboard.messagebox.showwarning") as showwarning, patch(
                "v24_app.ai_dashboard.messagebox.showinfo"
            ) as showinfo:
                result = dashboard.export_daily_parlay_report()
            self.assertIsNone(result)
            self.assertTrue(report_dir.exists())
            self.assertFalse(any(report_dir.iterdir()))
            self.assertFalse(log_path.exists())
            self.assertIn("blocked", dashboard.status_var.value)
            showwarning.assert_called_once()
            showinfo.assert_not_called()

    def test_export_daily_parlay_report_requires_confirmation_for_attention(self) -> None:
        dashboard = object.__new__(SmartMatchDashboard)
        dashboard.status_var = self._StatusVar()
        dashboard._log_event = lambda *args, **kwargs: None
        dashboard._daily_parlay_snapshot = lambda: {
            "active_tickets": [
                {
                    "ticket_id": "attention-1",
                    "status": "pending",
                    "legs": [
                        {"match_id": "m1", "source": "live:titan", "source_id": "titan-123"},
                        {"match_id": "m2", "source": "cache"},
                    ],
                }
            ],
            "settled_tickets": [],
            "selector_metrics": {"ticket_count": 1},
            "refreshed_from_current": True,
        }

        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp) / "reports"
            log_path = Path(tmp) / "daily_parlay_snapshot_log.json"
            with patch("v24_app.ai_dashboard.REPORT_DIR", report_dir), patch(
                "v24_app.ai_dashboard.DAILY_PARLAY_SNAPSHOT_LOG",
                log_path,
            ), patch("v24_app.ai_dashboard.messagebox.askyesno", return_value=True) as askyesno, patch(
                "v24_app.ai_dashboard.messagebox.showinfo"
            ) as showinfo:
                result = dashboard.export_daily_parlay_report()
            report_payload = result.read_text(encoding="utf-8")
            records = _load_daily_parlay_snapshot_log(log_path)
            self.assertIsNotNone(result)
            self.assertTrue(result.exists())
            self.assertTrue(report_dir.exists())
            self.assertEqual(len(records), 1)
            self.assertIn("来源健康", report_payload)
            self.assertIn("attention", dashboard.status_var.value)
            askyesno.assert_called_once()
            showinfo.assert_called_once()

    def test_closes_daily_parlay_snapshots_after_result_recovery(self) -> None:
        dashboard = object.__new__(SmartMatchDashboard)
        dashboard._log_event = lambda *args, **kwargs: None
        snapshot = {
            "generated_at": "2026-05-18 12:30:05",
            "active_tickets": [
                {
                    "ticket_id": "ticket-1",
                    "status": "pending",
                    "legs": [
                        {"match_id": "m1", "source": "live:titan", "source_id": "titan-123"},
                        {"match_id": "m2", "source": "live:titan", "source_id": "titan-123"},
                    ],
                },
                {
                    "ticket_id": "ticket-2",
                    "status": "pending",
                    "legs": [
                        {"match_id": "m3", "source": "live:titan", "source_id": "titan-123"},
                        {"match_id": "m4", "source": "live:titan", "source_id": "titan-123"},
                    ],
                },
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "daily_parlay_snapshot_log.json"
            _save_daily_parlay_snapshot_log([snapshot], log_path)
            with patch("v24_app.ai_dashboard.DAILY_PARLAY_SNAPSHOT_LOG", log_path), patch(
                "v24_app.ai_dashboard.get_recent_parlay_settlements",
                return_value=[{"ticket_id": "ticket-1", "status": "lost", "is_hit": False}],
            ):
                summary = dashboard._close_daily_parlay_snapshots_after_recovery()
            records = _load_daily_parlay_snapshot_log(log_path)

        self.assertEqual(summary["status"], "partial")
        self.assertEqual(summary["newly_settled_ticket_count"], 1)
        self.assertEqual(summary["source"], "live:titan")
        self.assertEqual(summary["source_id"], "titan-123")
        self.assertIn("live:titan", summary["source_summary_text"])
        self.assertEqual(records[0]["parlay_recovery"]["status"], "partial")
        self.assertEqual(records[0]["parlay_recovery"]["matched_ticket_ids"], ["ticket-1"])


if __name__ == "__main__":
    unittest.main()
