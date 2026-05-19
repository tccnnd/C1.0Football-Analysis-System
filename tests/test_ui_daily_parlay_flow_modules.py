from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.ui_modules import (
    apply_daily_parlay_source_backfill,
    build_daily_parlay_empty_state,
    build_daily_parlay_export_message,
    build_daily_parlay_export_guard_text,
    build_daily_parlay_report_filename,
    build_daily_parlay_report_lines,
    build_daily_parlay_repair_audit_record,
    build_daily_parlay_repair_audit_card_rows,
    build_daily_parlay_repair_audit_detail,
    build_daily_parlay_repair_audit_rows,
    build_daily_parlay_repair_audit_summary,
    build_daily_parlay_repair_loop_csv_filename,
    build_daily_parlay_repair_loop_csv_text,
    build_daily_parlay_repair_loop_export_message,
    build_daily_parlay_repair_loop_report_filename,
    build_daily_parlay_repair_loop_report_lines,
    build_daily_parlay_settlement_rows,
    build_daily_parlay_repair_queue_action_hint,
    build_daily_parlay_repair_queue_priority,
    build_daily_parlay_repair_queue_priority_counts,
    build_daily_parlay_repair_queue_rows,
    build_daily_parlay_repair_queue_route_counts,
    build_daily_parlay_repair_queue_summary,
    build_daily_parlay_snapshot,
    build_daily_parlay_snapshot_settlement_closure,
    build_daily_parlay_source_health_card_rows,
    build_daily_parlay_source_health_issue_rows,
    build_daily_parlay_source_health_summary,
    build_daily_parlay_source_backfill_index,
    build_daily_parlay_summary,
    build_daily_parlay_ticket_rows,
    daily_parlay_repair_queue_route_label,
    filter_daily_parlay_repair_queue_rows,
    mark_daily_parlay_split_required,
)


class UIDailyParlayFlowModuleTests(unittest.TestCase):
    def test_builds_summary_and_rows_for_active_tickets(self) -> None:
        active = [
            {
                "ticket_id": "ticket-1",
                "created_at": "2026-05-18 09:00:00",
                "status": "pending",
                "mixed": True,
                "expected_hit": 0.36,
                "legs": [
                    {"play_type": "1x2", "home_team": "A", "away_team": "B", "pick": "home"},
                    {"play_type": "total_goals", "home_team": "C", "away_team": "D", "pick": "over"},
                ],
            }
        ]

        summary = build_daily_parlay_summary(active, [])
        rows = build_daily_parlay_ticket_rows(active)

        self.assertEqual(summary["active_count"], 1)
        self.assertEqual(summary["pending_count"], 1)
        self.assertEqual(summary["mixed_count"], 1)
        self.assertAlmostEqual(summary["avg_expected_hit"], 0.36)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticket_id"], "ticket-1")
        self.assertEqual(rows[0]["status"], "pending")
        self.assertTrue(rows[0]["mixed"])
        self.assertEqual(rows[0]["expected_hit"], 0.36)
        self.assertIn("title", rows[0])
        self.assertIn("body", rows[0])
        self.assertIn("tone", rows[0])

    def test_builds_summary_and_rows_for_settled_tickets(self) -> None:
        settled = [
            {"ticket_id": "lost-1", "status": "lost", "is_hit": False, "expected_hit": 0.28, "settled_at": "2026-05-17 10:00:00"},
            {"ticket_id": "won-1", "status": "won", "is_hit": True, "expected_hit": 0.31, "settled_at": "2026-05-18 10:00:00"},
        ]

        summary = build_daily_parlay_summary([], settled)
        rows = build_daily_parlay_settlement_rows(settled)

        self.assertEqual(summary["settled_count"], 2)
        self.assertEqual(summary["won_count"], 1)
        self.assertEqual(summary["lost_count"], 1)
        self.assertEqual(summary["hit_rate"], 0.5)
        self.assertEqual([row["ticket_id"] for row in rows], ["won-1", "lost-1"])
        self.assertEqual(rows[0]["tone"], "success")
        self.assertEqual(rows[1]["tone"], "danger")

    def test_empty_state(self) -> None:
        empty_summary = build_daily_parlay_summary([], [])
        settled_summary = build_daily_parlay_summary([], [{"ticket_id": "old", "status": "won"}])
        active_summary = build_daily_parlay_summary([{"ticket_id": "active"}], [])

        self.assertTrue(build_daily_parlay_empty_state(empty_summary))
        self.assertTrue(build_daily_parlay_empty_state(settled_summary))
        self.assertEqual(build_daily_parlay_empty_state(active_summary), "")

    def test_dirty_ticket_data_is_tolerated(self) -> None:
        active = [
            None,
            "bad",
            {"ticket_id": None, "expected_hit": "bad", "legs": "bad", "mixed": "yes"},
            {"legs": [object(), {"match_id": "m-1"}], "expected_hit": None},
        ]
        settled = [
            object(),
            {"ticket_id": "settled", "status": "", "is_hit": "bad", "expected_hit": "nan"},
        ]

        summary = build_daily_parlay_summary(active, settled)
        active_rows = build_daily_parlay_ticket_rows(active)
        settled_rows = build_daily_parlay_settlement_rows(settled)

        self.assertEqual(summary["active_count"], 2)
        self.assertEqual(summary["settled_count"], 1)
        self.assertEqual(len(active_rows), 2)
        self.assertEqual(len(settled_rows), 1)
        self.assertEqual(active_rows[0]["expected_hit"], 0.0)
        self.assertIn(active_rows[0]["status"], {"pending", ""})
        self.assertEqual(settled_rows[0]["expected_hit"], 0.0)

    def test_sorting_and_limit_for_active_and_settled_rows(self) -> None:
        active = [
            {"ticket_id": "same-high", "mixed": False, "expected_hit": 0.80, "rank_score": 0.80},
            {"ticket_id": "mixed-low", "mixed": True, "expected_hit": 0.20, "rank_score": 0.20},
            {"ticket_id": "mixed-high", "mixed": True, "expected_hit": 0.50, "rank_score": 0.50},
        ]
        settled = [
            {"ticket_id": "old", "status": "won", "settled_at": "2026-05-16 10:00:00"},
            {"ticket_id": "new", "status": "lost", "settled_at": "2026-05-18 10:00:00"},
            {"ticket_id": "middle", "status": "won", "settled_at": "2026-05-17 10:00:00"},
        ]

        active_rows = build_daily_parlay_ticket_rows(active, limit=2)
        settled_rows = build_daily_parlay_settlement_rows(settled, limit=2)

        self.assertEqual([row["ticket_id"] for row in active_rows], ["mixed-high", "mixed-low"])
        self.assertEqual([row["ticket_id"] for row in settled_rows], ["new", "middle"])

    def test_report_filename_is_deterministic(self) -> None:
        self.assertEqual(
            build_daily_parlay_report_filename(datetime(2026, 5, 18, 12, 30, 5)),
            "daily_parlay_recommendations_20260518_123005.md",
        )

    def test_source_health_is_healthy_when_legs_are_traceable(self) -> None:
        active = [
            {
                "ticket_id": "ticket-1",
                "legs": [
                    {"match_id": "m1", "source": "live:titan", "source_id": "titan-1"},
                    {"match_id": "m2", "source": "live:titan", "source_id": "titan-2"},
                ],
            }
        ]

        health = build_daily_parlay_source_health_summary(active, [])
        cards = build_daily_parlay_source_health_card_rows(health)
        issues = build_daily_parlay_source_health_issue_rows(health)

        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["tone"], "good")
        self.assertEqual(health["issue_count"], 0)
        self.assertEqual(health["metrics"]["source_id_leg_count"], 2)
        self.assertEqual(cards[0]["value"], "healthy")
        self.assertEqual(issues, [])

    def test_source_health_attention_for_missing_source_id_and_mixed_sources(self) -> None:
        active = [
            {
                "ticket_id": "ticket-1",
                "legs": [
                    {"match_id": "m1", "source": "live:titan", "source_id": "titan-1"},
                    {"match_id": "m2", "source": "cache"},
                ],
            }
        ]

        health = build_daily_parlay_source_health_summary(active, [])
        issue_codes = {issue["code"] for issue in health["issues"]}
        issue_rows = build_daily_parlay_source_health_issue_rows(health)

        self.assertEqual(health["status"], "attention")
        self.assertEqual(health["tone"], "warning")
        self.assertIn("parlay_source_id_missing", issue_codes)
        self.assertIn("parlay_mixed_sources", issue_codes)
        self.assertEqual(health["metrics"]["mixed_ticket_count"], 1)
        self.assertTrue(any("source_id" in row["message"] for row in issue_rows))

    def test_source_health_blocked_when_no_leg_is_traceable(self) -> None:
        active = [
            {"ticket_id": "ticket-1", "legs": [{"match_id": "m1"}, {"match_id": "m2"}]},
            {"ticket_id": "ticket-2", "legs": []},
        ]

        health = build_daily_parlay_source_health_summary(active, [])
        issue_codes = {issue["code"] for issue in health["issues"]}

        self.assertEqual(health["status"], "blocked")
        self.assertEqual(health["tone"], "bad")
        self.assertIn("parlay_traceability_blocked", issue_codes)
        self.assertIn("parlay_traceability_gap", issue_codes)
        self.assertGreaterEqual(health["metrics"]["missing_traceability_leg_count"], 1)

    def test_daily_parlay_repair_queue_summary_and_rows(self) -> None:
        tickets = [
            {
                "ticket_id": "ticket-blocked",
                "status": "pending",
                "created_at": "2026-05-18 08:00:00",
                "legs": [
                    {"match_id": "m1", "source": "live:titan", "source_id": "titan-1"},
                    {"match_id": "m2"},
                ],
                "settlement_recovery_gate": {
                    "status": "blocked",
                    "code": "parlay_source_traceability_missing",
                    "message": "Missing source/source_id on parlay legs.",
                    "recommendation": "Backfill source and source_id before rerunning recovery.",
                    "source": "live:titan",
                    "source_id": "titan-1",
                    "leg_count": 2,
                    "missing_source_count": 1,
                    "missing_source_id_count": 1,
                    "mixed_source_count": 0,
                },
            },
            {
                "ticket_id": "ticket-ready",
                "status": "pending",
                "created_at": "2026-05-18 09:00:00",
                "legs": [
                    {"match_id": "m3", "source": "live:titan", "source_id": "titan-2"},
                    {"match_id": "m4", "source": "live:titan", "source_id": "titan-3"},
                ],
                "settlement_recovery_gate": {
                    "status": "ready",
                    "code": "ready",
                    "message": "Parlay ticket is traceable and eligible for automatic settlement.",
                    "recommendation": "Proceed with automatic result recovery.",
                    "source": "live:titan",
                    "source_id": "titan-2 / titan-3",
                    "leg_count": 2,
                    "missing_source_count": 0,
                    "missing_source_id_count": 0,
                    "mixed_source_count": 0,
                },
            },
            {"ticket_id": "ticket-settled", "status": "won"},
        ]

        summary = build_daily_parlay_repair_queue_summary(tickets)
        rows = build_daily_parlay_repair_queue_rows(tickets)

        self.assertEqual(summary["status"], "attention")
        self.assertEqual(summary["pending_count"], 2)
        self.assertEqual(summary["blocked_count"], 1)
        self.assertEqual(summary["ready_count"], 1)
        self.assertEqual(summary["source_issue_count"], 1)
        self.assertEqual(summary["mixed_source_count"], 0)
        self.assertEqual(summary["priority_counts"]["high"], 1)
        self.assertEqual(summary["priority_counts"]["auto_recoverable"], 1)
        self.assertIn("可自动回填", summary["priority_summary_text"])
        self.assertEqual(rows[0]["ticket_id"], "ticket-blocked")
        self.assertEqual(rows[0]["code"], "parlay_source_traceability_missing")
        self.assertEqual(rows[0]["route_type"], "source_backfill")
        self.assertEqual(rows[0]["priority_bucket"], "high")
        self.assertTrue(rows[0]["auto_recoverable"])
        self.assertIn("Backfill source and source_id", rows[0]["body"])
        self.assertEqual(rows[0]["tone"], "danger")
        self.assertEqual(rows[0]["gate"]["status"], "blocked")

    def test_daily_parlay_repair_queue_route_counts_and_filters(self) -> None:
        rows = [
            {
                "ticket_id": "source-1",
                "code": "parlay_source_traceability_missing",
                "missing_source_count": 1,
                "missing_source_id_count": 0,
                "mixed_source_count": 0,
            },
            {
                "ticket_id": "mixed-1",
                "code": "parlay_mixed_sources",
                "missing_source_count": 0,
                "missing_source_id_count": 0,
                "mixed_source_count": 1,
            },
            {
                "ticket_id": "manual-1",
                "code": "other",
                "missing_source_count": 0,
                "missing_source_id_count": 0,
                "mixed_source_count": 0,
            },
        ]

        counts = build_daily_parlay_repair_queue_route_counts(rows)
        source_rows = filter_daily_parlay_repair_queue_rows(rows, "source_backfill")
        mixed_rows = filter_daily_parlay_repair_queue_rows(rows, "mixed_source_split")
        all_rows = filter_daily_parlay_repair_queue_rows(rows, "recovery_failure")

        self.assertEqual(counts["all"], 3)
        self.assertEqual(counts["source_backfill"], 1)
        self.assertEqual(counts["mixed_source_split"], 1)
        self.assertEqual(counts["manual_review"], 1)
        self.assertEqual(source_rows[0]["ticket_id"], "source-1")
        self.assertEqual(mixed_rows[0]["ticket_id"], "mixed-1")
        self.assertEqual([row["ticket_id"] for row in all_rows], ["source-1", "mixed-1", "manual-1"])
        self.assertEqual(daily_parlay_repair_queue_route_label("mixed_source_split"), "混源拆票")

    def test_daily_parlay_repair_queue_action_hints_match_route(self) -> None:
        source_hint = build_daily_parlay_repair_queue_action_hint(
            {
                "code": "parlay_source_traceability_missing",
                "missing_source_count": 1,
                "missing_source_id_count": 1,
                "mixed_source_count": 0,
            }
        )
        mixed_hint = build_daily_parlay_repair_queue_action_hint(
            {
                "code": "parlay_mixed_sources",
                "missing_source_count": 0,
                "missing_source_id_count": 0,
                "mixed_source_count": 1,
            }
        )
        manual_hint = build_daily_parlay_repair_queue_action_hint({"code": "other"})

        self.assertEqual(source_hint["action_key"], "source_backfill")
        self.assertEqual(source_hint["primary_action"], "从快照回填选中")
        self.assertIn("source/source_id", source_hint["message"])
        self.assertEqual(mixed_hint["action_key"], "mixed_source_split")
        self.assertEqual(mixed_hint["primary_action"], "标记需拆票")
        self.assertIn("混源", mixed_hint["route_label"])
        self.assertEqual(manual_hint["action_key"], "manual_review")
        self.assertIn("门禁原文", manual_hint["primary_action"])

    def test_daily_parlay_repair_queue_priority_orders_by_severity_and_time(self) -> None:
        tickets = [
            {
                "ticket_id": "source-new",
                "status": "pending",
                "created_at": "2026-05-18 09:00:00",
                "settlement_recovery_gate": {
                    "status": "blocked",
                    "code": "parlay_source_traceability_missing",
                    "missing_source_count": 1,
                    "missing_source_id_count": 1,
                },
            },
            {
                "ticket_id": "mixed",
                "status": "pending",
                "created_at": "2026-05-18 10:00:00",
                "settlement_recovery_gate": {
                    "status": "blocked",
                    "code": "parlay_mixed_sources",
                    "mixed_source_count": 1,
                },
            },
            {
                "ticket_id": "source-old",
                "status": "pending",
                "created_at": "2026-05-18 08:00:00",
                "settlement_recovery_gate": {
                    "status": "blocked",
                    "code": "parlay_source_traceability_missing",
                    "missing_source_count": 1,
                    "missing_source_id_count": 1,
                },
            },
        ]

        rows = build_daily_parlay_repair_queue_rows(tickets)
        counts = build_daily_parlay_repair_queue_priority_counts(rows)
        mixed_priority = build_daily_parlay_repair_queue_priority(rows[0])

        self.assertEqual([row["ticket_id"] for row in rows], ["mixed", "source-old", "source-new"])
        self.assertEqual(rows[0]["priority_bucket"], "critical")
        self.assertGreater(rows[0]["priority_score"], rows[1]["priority_score"])
        self.assertEqual(counts["critical"], 1)
        self.assertEqual(counts["high"], 2)
        self.assertEqual(counts["auto_recoverable"], 2)
        self.assertEqual(mixed_priority["priority_bucket"], "critical")

    def test_daily_parlay_repair_queue_summary_is_healthy_when_no_blocked_tickets_remain(self) -> None:
        tickets = [
            {
                "ticket_id": "ticket-ready",
                "status": "pending",
                "legs": [
                    {"match_id": "m3", "source": "live:titan", "source_id": "titan-2"},
                    {"match_id": "m4", "source": "live:titan", "source_id": "titan-3"},
                ],
                "settlement_recovery_gate": {
                    "status": "ready",
                    "code": "ready",
                    "message": "Parlay ticket is traceable and eligible for automatic settlement.",
                    "recommendation": "Proceed with automatic result recovery.",
                    "source": "live:titan",
                    "source_id": "titan-2 / titan-3",
                    "leg_count": 2,
                },
            }
        ]

        summary = build_daily_parlay_repair_queue_summary(tickets)
        rows = build_daily_parlay_repair_queue_rows(tickets)

        self.assertEqual(summary["status"], "healthy")
        self.assertEqual(summary["blocked_count"], 0)
        self.assertEqual(summary["ready_count"], 1)
        self.assertEqual(rows, [])

    def test_source_backfill_index_accepts_nested_snapshot_match_payloads(self) -> None:
        refs = [
            {
                "match": {
                    "match_date": "2026-05-18",
                    "league": "L1",
                    "home_team": "A",
                    "away_team": "B",
                    "source": "live:titan",
                    "source_id": "titan-1",
                }
            }
        ]

        index = build_daily_parlay_source_backfill_index(refs)

        self.assertEqual(index["2026-05-18|L1|A|B"]["source"], "live:titan")
        self.assertEqual(index["2026-05-18|L1|A|B"]["source_id"], "titan-1")

    def test_apply_source_backfill_repairs_missing_leg_traceability(self) -> None:
        tickets = [
            {
                "ticket_id": "ticket-blocked",
                "status": "pending",
                "legs": [
                    {"match_id": "m1", "source": "live:titan", "source_id": "titan-1"},
                    {"match_id": "m2"},
                ],
                "settlement_recovery_gate": {
                    "status": "blocked",
                    "code": "parlay_source_traceability_missing",
                },
            }
        ]
        refs = [{"match_id": "m2", "source": "live:titan", "source_id": "titan-2"}]

        result = apply_daily_parlay_source_backfill(
            tickets,
            refs,
            generated_at=datetime(2026, 5, 18, 12, 0, 0),
        )

        self.assertTrue(result["changed"])
        self.assertEqual(result["updated_ticket_count"], 1)
        self.assertEqual(result["updated_leg_count"], 1)
        updated = result["tickets"][0]
        self.assertEqual(updated["legs"][1]["source"], "live:titan")
        self.assertEqual(updated["legs"][1]["source_id"], "titan-2")
        self.assertNotIn("settlement_recovery_gate", updated)
        self.assertEqual(result["queue_summary"]["blocked_count"], 0)

    def test_repair_audit_record_tracks_recovery_result(self) -> None:
        repair_result = {
            "action": "source_backfill",
            "changed": True,
            "target_ticket_id": "ticket-blocked",
            "updated_ticket_count": 1,
            "updated_leg_count": 1,
            "missing_ref_count": 0,
            "summary_text": "source backfill checked 1 ticket(s), updated 1 ticket(s) / 1 leg(s), remaining blocked 0",
            "queue_summary": {"status": "healthy", "blocked_count": 0, "ready_count": 1},
        }
        recovery_result = {
            "new_settled": 1,
            "won": 1,
            "lost": 0,
            "skipped_source_health": 0,
            "manual_review_items": [],
            "gate": {"status": "healthy", "manual_review_count": 0, "summary_text": "parlay settlement gate healthy"},
        }

        audit = build_daily_parlay_repair_audit_record(repair_result, recovery_result)

        self.assertEqual(audit["status"], "settled")
        self.assertEqual(audit["action"], "source_backfill")
        self.assertEqual(audit["recovery_new_settled"], 1)
        self.assertEqual(audit["queue_blocked_after_repair"], 0)
        self.assertEqual(audit["recovery_gate_status"], "healthy")

    def test_repair_audit_summary_rows_and_detail(self) -> None:
        records = [
            {
                "generated_at": "2026-05-18 12:01:00",
                "status": "settled",
                "action": "source_backfill",
                "target_ticket_id": "ticket-1",
                "updated_ticket_count": 1,
                "updated_leg_count": 1,
                "recovery_new_settled": 1,
                "recovery_gate_status": "healthy",
                "queue_blocked_after_repair": 0,
                "repair_summary_text": "source backfill checked 1 ticket(s)",
                "recovery_summary_text": "parlay settlement gate healthy",
            },
            {
                "generated_at": "2026-05-18 12:10:00",
                "status": "error",
                "action": "mark_split_required",
                "target_ticket_id": "ticket-2",
                "updated_ticket_count": 0,
                "updated_leg_count": 0,
                "recovery_new_settled": 0,
                "recovery_gate_status": "blocked",
                "queue_blocked_after_repair": 1,
                "error": "boom",
            },
        ]

        summary = build_daily_parlay_repair_audit_summary(records)
        card_rows = build_daily_parlay_repair_audit_card_rows(records)
        rows = build_daily_parlay_repair_audit_rows(records)
        detail = build_daily_parlay_repair_audit_detail(records[0])

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["settled_count"], 1)
        self.assertEqual(summary["error_count"], 1)
        self.assertEqual(card_rows[0]["label"], "最新修复状态")
        self.assertEqual(card_rows[0]["tone"], "bad")
        self.assertEqual(card_rows[1]["value"], "1")
        self.assertEqual(rows[0]["tone"], "success")
        self.assertEqual(rows[1]["tone"], "danger")
        self.assertIn("recovery_new_settled", detail)
        self.assertIn("source backfill checked 1 ticket(s)", detail)

    def test_repair_loop_report_and_csv_export_payload(self) -> None:
        snapshot = {
            "repair_queue_summary": {
                "pending_count": 2,
                "blocked_count": 1,
                "ready_count": 1,
                "source_issue_count": 1,
                "mixed_source_count": 0,
            },
            "repair_queue_rows": [
                {
                    "ticket_id": "ticket-blocked",
                    "status": "blocked",
                    "code": "parlay_source_traceability_missing",
                    "source": "live:titan",
                    "source_id": "-",
                    "message": "Missing source_id",
                    "recommendation": "Backfill source_id",
                }
            ],
            "repair_audit_summary": {
                "summary_text": "二串一修复审计 1 条",
                "total": 1,
                "latest_blocked_count": 0,
                "recovery_new_settled": 1,
            },
            "repair_audit_records": [
                {
                    "generated_at": "2026-05-18 12:01:00",
                    "status": "settled",
                    "action": "source_backfill",
                    "target_ticket_id": "ticket-blocked",
                    "updated_ticket_count": 1,
                    "updated_leg_count": 1,
                    "recovery_new_settled": 1,
                    "recovery_gate_status": "healthy",
                    "queue_blocked_after_repair": 0,
                    "repair_summary_text": "source backfill checked 1 ticket(s)",
                    "recovery_summary_text": "parlay settlement gate healthy",
                }
            ],
            "repair_audit_rows": [
                {
                    "generated_at": "2026-05-18 12:01:00",
                    "status": "settled",
                    "target_ticket_id": "ticket-blocked",
                    "body": "action=source_backfill | settled=1",
                    "record": {
                        "generated_at": "2026-05-18 12:01:00",
                        "status": "settled",
                        "action": "source_backfill",
                        "target_ticket_id": "ticket-blocked",
                        "updated_ticket_count": 1,
                        "updated_leg_count": 1,
                        "recovery_new_settled": 1,
                        "recovery_gate_status": "healthy",
                        "queue_blocked_after_repair": 0,
                        "repair_summary_text": "source backfill checked 1 ticket(s)",
                        "recovery_summary_text": "parlay settlement gate healthy",
                    },
                }
            ],
        }

        lines = build_daily_parlay_repair_loop_report_lines(snapshot, generated_at=datetime(2026, 5, 18, 13, 0, 0))
        csv_text = build_daily_parlay_repair_loop_csv_text(snapshot)
        message = build_daily_parlay_repair_loop_export_message("report.md", "report.csv", snapshot)

        self.assertEqual(build_daily_parlay_repair_loop_report_filename(datetime(2026, 5, 18, 13, 0, 0)), "daily_parlay_repair_loop_20260518_130000.md")
        self.assertEqual(build_daily_parlay_repair_loop_csv_filename(datetime(2026, 5, 18, 13, 0, 0)), "daily_parlay_repair_loop_20260518_130000.csv")
        self.assertIn("# 二串一修复闭环报告", "\n".join(lines))
        self.assertIn("ticket-blocked", "\n".join(lines))
        self.assertIn("record_type,generated_at,status", csv_text)
        self.assertIn("route_type", csv_text)
        self.assertIn("priority_bucket", csv_text)
        self.assertIn("auto_recoverable", csv_text)
        self.assertIn("high", csv_text)
        self.assertIn("source_backfill", csv_text)
        self.assertIn("audit,2026-05-18 12:01:00,settled", csv_text)
        self.assertIn("queue,", csv_text)
        self.assertIn("Markdown: report.md", message)
        self.assertIn("优先级概览", "\n".join(lines))
        self.assertIn("优先级概览", message)
        self.assertIn("自动分流", "\n".join(lines))
        self.assertIn("自动分流", message)

    def test_mark_split_required_keeps_mixed_ticket_in_manual_queue(self) -> None:
        tickets = [
            {
                "ticket_id": "ticket-mixed",
                "status": "pending",
                "legs": [
                    {"match_id": "m1", "source": "live:titan", "source_id": "titan-1"},
                    {"match_id": "m2", "source": "cache", "source_id": "cache-2"},
                ],
            }
        ]

        result = mark_daily_parlay_split_required(
            tickets,
            "ticket-mixed",
            generated_at=datetime(2026, 5, 18, 12, 0, 0),
        )

        self.assertTrue(result["changed"])
        updated = result["tickets"][0]
        self.assertEqual(updated["manual_review_status"], "split_required")
        self.assertEqual(updated["settlement_recovery_gate"]["status"], "blocked")
        self.assertEqual(result["queue_summary"]["blocked_count"], 1)

    def test_export_guard_text_reflects_source_health(self) -> None:
        snapshot = build_daily_parlay_snapshot(
            [{"ticket_id": "ticket-1", "legs": [{"match_id": "m1"}]}],
            [],
            {},
            generated_at=datetime(2026, 5, 18, 12, 30, 5),
        )
        guard_text = build_daily_parlay_export_guard_text(snapshot)

        self.assertIn("来源健康", guard_text)
        self.assertIn("blocked", guard_text)
        self.assertIn("source_id", guard_text)

    def test_snapshot_and_report_lines_include_export_context(self) -> None:
        active = [
            {
                "ticket_id": "ticket-1",
                "created_at": "2026-05-18 09:00:00",
                "status": "pending",
                "mixed": True,
                "expected_hit": 0.36,
                "legs": [
                    {
                        "play_type": "1x2",
                        "home_team": "A",
                        "away_team": "B",
                        "pick": "home",
                        "source": "live:titan",
                        "source_id": "titan-123",
                    },
                    {
                        "play_type": "total_goals",
                        "home_team": "C",
                        "away_team": "D",
                        "pick": "over",
                        "source": "live:titan",
                        "source_id": "titan-123",
                    },
                ],
            }
        ]
        settled = [
            {
                "ticket_id": "won-1",
                "status": "won",
                "is_hit": True,
                "expected_hit": 0.31,
                "legs": [{"source": "live:titan", "source_id": "titan-123"}],
            }
        ]
        metrics = {"ticket_count": 1, "unique_match_count": 2, "mixed_ratio": 1.0, "low_discount_count": 0}

        snapshot = build_daily_parlay_snapshot(
            active,
            settled,
            metrics,
            generated_at=datetime(2026, 5, 18, 12, 30, 5),
            report_path=Path("reports") / "daily.md",
            source="当前分析",
        )
        lines = build_daily_parlay_report_lines(snapshot)
        payload = "\n".join(lines)

        self.assertEqual(snapshot["generated_at"], "2026-05-18 12:30:05")
        self.assertEqual(snapshot["source"], "当前分析")
        self.assertEqual(snapshot["summary"]["active_count"], 1)
        self.assertEqual(snapshot["selector_metrics"]["unique_match_count"], 2)
        self.assertEqual(snapshot["summary"]["source"], "live:titan")
        self.assertEqual(snapshot["summary"]["source_id"], "titan-123")
        self.assertEqual(snapshot["summary"]["source_health_status"], "healthy")
        self.assertEqual(snapshot["source_health"]["status"], "healthy")
        self.assertEqual(snapshot["source_health"]["issue_count"], 0)
        self.assertEqual(snapshot["ticket_rows"][0]["ticket_id"], "ticket-1")
        self.assertEqual(snapshot["ticket_rows"][0]["source"], "live:titan")
        self.assertEqual(snapshot["ticket_rows"][0]["source_id"], "titan-123")
        self.assertEqual(snapshot["settlement_rows"][0]["source"], "live:titan")
        self.assertEqual(snapshot["settlement_rows"][0]["source_id"], "titan-123")
        self.assertIn("# 每日二串一推荐报告", payload)
        self.assertIn("## 来源健康审计", payload)
        self.assertIn("## 来源问题与建议", payload)
        self.assertIn("healthy", payload)
        self.assertIn("## 今日推荐组合", payload)
        self.assertIn("## 近期二串一结算", payload)
        self.assertIn("## 边界", payload)
        self.assertIn("票据来源", payload)
        self.assertIn("ticket-1", payload)
        self.assertIn("won-1", payload)
        self.assertIn("live:titan", payload)
        self.assertIn("titan-123", payload)
        self.assertIn("当前组合: 1", build_daily_parlay_export_message("daily.md", snapshot))

    def test_snapshot_tolerates_dirty_inputs(self) -> None:
        snapshot = build_daily_parlay_snapshot(
            [None, {"ticket_id": object(), "expected_hit": "nan", "legs": "bad"}],
            object(),
            {"ticket_count": object()},
            generated_at=datetime(2026, 5, 18, 12, 30, 5),
        )
        lines = build_daily_parlay_report_lines(snapshot)

        self.assertEqual(snapshot["summary"]["active_count"], 1)
        self.assertEqual(snapshot["summary"]["settled_count"], 0)
        self.assertEqual(len(snapshot["ticket_rows"]), 1)
        self.assertTrue(lines)

    def test_snapshot_settlement_closure_updates_recovery_state(self) -> None:
        snapshot = build_daily_parlay_snapshot(
            [
                {
                    "ticket_id": "ticket-1",
                    "status": "pending",
                    "expected_hit": 0.36,
                    "legs": [
                        {"match_id": "m1", "source": "live:titan", "source_id": "titan-123"},
                        {"match_id": "m2", "source": "live:titan", "source_id": "titan-123"},
                    ],
                },
                {
                    "ticket_id": "ticket-2",
                    "status": "pending",
                    "expected_hit": 0.24,
                    "legs": [
                        {"match_id": "m3", "source": "live:titan", "source_id": "titan-123"},
                        {"match_id": "m4", "source": "live:titan", "source_id": "titan-123"},
                    ],
                },
            ],
            [],
            {},
            generated_at=datetime(2026, 5, 18, 12, 30, 5),
        )
        closure = build_daily_parlay_snapshot_settlement_closure(
            [snapshot],
            [{"ticket_id": "ticket-1", "status": "won", "is_hit": True, "settled_at": "2026-05-18 23:00:00"}],
            generated_at=datetime(2026, 5, 18, 23, 30, 5),
        )

        summary = closure["summary"]
        updated = closure["records"][0]

        self.assertEqual(summary["status"], "partial")
        self.assertEqual(summary["snapshot_count"], 1)
        self.assertEqual(summary["checked_ticket_count"], 2)
        self.assertEqual(summary["settled_ticket_count"], 1)
        self.assertEqual(summary["newly_settled_ticket_count"], 1)
        self.assertTrue(summary["changed"])
        self.assertEqual(updated["parlay_recovery"]["status"], "partial")
        self.assertEqual(updated["parlay_recovery"]["source"], "live:titan")
        self.assertEqual(updated["parlay_recovery"]["source_id"], "titan-123")
        self.assertIn("live:titan", updated["parlay_recovery"]["source_summary_text"])
        self.assertEqual(updated["parlay_recovery"]["matched_ticket_ids"], ["ticket-1"])
        self.assertEqual(updated["parlay_recovery"]["pending_ticket_ids"], ["ticket-2"])

        second_closure = build_daily_parlay_snapshot_settlement_closure(
            closure["records"],
            [{"ticket_id": "ticket-1", "status": "won", "is_hit": True, "settled_at": "2026-05-18 23:00:00"}],
            generated_at=datetime(2026, 5, 19, 0, 0, 0),
        )
        self.assertFalse(second_closure["summary"]["changed"])
        self.assertEqual(second_closure["summary"]["newly_settled_ticket_count"], 0)


if __name__ == "__main__":
    unittest.main()
