from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.ai_dashboard import (
    SmartMatchDashboard,
    _append_statsbomb_review_training_weight_gate_audit_log,
    _load_statsbomb_review_training_weight_gate_audit_log,
    build_statsbomb_event_proxy_review_samples_message,
    build_statsbomb_event_proxy_review_text,
    build_statsbomb_review_training_action_feedback,
    build_statsbomb_review_training_action_rows,
    build_statsbomb_review_training_center_summary,
    build_statsbomb_review_training_feedback_rows,
    build_statsbomb_review_training_quality_export_message,
    build_statsbomb_review_training_weight_gate_audit_record,
    build_statsbomb_review_training_weight_gate_audit_record_from_feedback,
    build_statsbomb_review_training_weight_gate_audit_rows,
    build_statsbomb_review_training_weight_gate_alert_summary,
    build_statsbomb_review_training_weight_gate_alert_lines,
    build_statsbomb_review_training_weight_gate_trend_summary,
    build_statsbomb_review_training_closure_summary,
    build_video_review_evidence_gap_batch_id,
    build_video_review_evidence_gap_batch_record,
    build_video_review_evidence_gap_action_rows,
    build_video_review_evidence_gap_batch_filter_options,
    build_video_review_evidence_gap_batch_filter_result,
    build_video_review_evidence_gap_batch_filter_rows,
    build_video_review_evidence_gap_batch_filter_report_filename,
    build_video_review_evidence_gap_batch_filter_report_lines,
    build_video_review_evidence_gap_batch_filter_report_message,
    build_video_review_evidence_gap_batch_action_rows,
    build_video_review_evidence_gap_batch_plan_export_message,
    build_video_review_evidence_gap_batch_plan_filename,
    build_video_review_evidence_gap_batch_plan_lines,
    build_video_review_evidence_gap_batch_state_with_record,
    build_video_review_evidence_gap_batch_state_with_resolution,
    build_video_review_evidence_gap_batch_status,
    build_video_review_evidence_gap_batch_status_rows,
    build_video_review_evidence_gap_feedback,
    build_video_review_evidence_gap_feedback_rows,
    build_video_review_center_summary,
    build_video_review_center_action_rows,
    build_video_review_evidence_gap_row_key,
    build_video_review_evidence_gap_next_selection_index,
    build_video_review_evidence_gap_quick_open_filters,
    build_video_review_evidence_gap_quick_target_item,
    find_video_review_evidence_gap_row_index,
    collect_video_review_evidence_gap_sample_match_ids,
    find_video_review_evidence_gap_settlement,
)


class AIDashboardStatsBombEventProxyTests(unittest.TestCase):
    def test_video_review_evidence_gap_action_rows_only_include_missing_evidence(self) -> None:
        rows = build_video_review_evidence_gap_action_rows(
            [
                {
                    "match_id": "video-ready",
                    "match_date": "2026-05-14",
                    "league": "League A",
                    "home_team": "Alpha",
                    "away_team": "Bravo",
                    "video_review": {"video": {"source_type": "external_reference", "url": "https://example.com/replay"}},
                },
                {
                    "match_id": "event-proxy-ready",
                    "match_date": "2026-05-15",
                    "league": "League A",
                    "home_team": "Charlie",
                    "away_team": "Delta",
                    "statsbomb_event_summary": {"event_count": 1000},
                },
                {
                    "match_id": "sample-proxy-ready",
                    "match_date": "2026-05-16",
                    "league": "League B",
                    "home_team": "Echo",
                    "away_team": "Foxtrot",
                },
                {
                    "match_id": "missing-evidence",
                    "match_date": "2026-05-17",
                    "league": "League B",
                    "home_team": "Golf",
                    "away_team": "Hotel",
                },
            ],
            {
                "items": [
                    {
                        "meta": {
                            "source": "statsbomb_event_sandbox",
                            "match_id": "sample-proxy-ready",
                        }
                    }
                ]
            },
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["match_id"], "missing-evidence")
        self.assertEqual(rows[0]["action_key"], "bind_external_reference")
        self.assertIn("优先绑定合法回放链接", rows[0]["body"])
        self.assertIn("低置信复盘", rows[0]["body"])
        self.assertIn("priority_score", rows[0])

    def test_video_review_evidence_gap_action_rows_prioritize_high_value_misses(self) -> None:
        rows = build_video_review_evidence_gap_action_rows(
            [
                {
                    "match_id": "recent-normal",
                    "match_date": "2026-05-20",
                    "league": "League B",
                    "home_team": "Recent",
                    "away_team": "Normal",
                },
                {
                    "match_id": "high-conf-miss",
                    "match_date": "2026-05-18",
                    "league": "FIFA World Cup",
                    "home_team": "High",
                    "away_team": "Miss",
                    "is_correct": False,
                    "prediction_confidence": 0.72,
                },
                {
                    "match_id": "strategy-miss",
                    "match_date": "2026-05-19",
                    "league": "League A",
                    "home_team": "Strategy",
                    "away_team": "Miss",
                    "high_accuracy_strategy_items": [{"is_hit": False, "confidence": 0.71}],
                    "strategy_allowlist_decision": "allow",
                },
            ]
        )

        self.assertEqual([row["match_id"] for row in rows], ["high-conf-miss", "strategy-miss", "recent-normal"])
        self.assertGreater(rows[0]["priority_score"], rows[1]["priority_score"])
        self.assertEqual(rows[0]["priority_label"], "P1")
        self.assertIn("高置信1X2失误", rows[0]["priority_reasons"])
        self.assertIn("重点赛事", rows[0]["priority_reasons"])
        self.assertIn("优先级 P1", rows[0]["body"])

    def test_video_review_evidence_gap_batch_plan_filename_is_stable(self) -> None:
        self.assertEqual(
            build_video_review_evidence_gap_batch_id(datetime(2026, 5, 14, 12, 3, 4)),
            "evidence_gap_batch_20260514_120304",
        )
        self.assertEqual(
            build_video_review_evidence_gap_batch_plan_filename(datetime(2026, 5, 14, 12, 3, 4)),
            "video_review_evidence_gap_batch_plan_20260514_120304.md",
        )

    def test_video_review_evidence_gap_batch_plan_lines_include_priority_and_boundaries(self) -> None:
        rows = build_video_review_evidence_gap_action_rows(
            [
                {
                    "match_id": "high-conf-miss",
                    "match_date": "2026-05-18",
                    "league": "FIFA World Cup",
                    "home_team": "High",
                    "away_team": "Miss",
                    "is_correct": False,
                    "prediction_confidence": 0.72,
                },
                {
                    "match_id": "strategy-miss",
                    "match_date": "2026-05-19",
                    "league": "League A",
                    "home_team": "Strategy",
                    "away_team": "Miss",
                    "high_accuracy_strategy_items": [{"is_hit": False, "confidence": 0.71}],
                    "strategy_allowlist_decision": "allow",
                },
            ],
            limit=2,
        )

        text = "\n".join(
            build_video_review_evidence_gap_batch_plan_lines(
                rows,
                generated_at=datetime(2026, 5, 14, 12, 0, 0),
                batch_id="evidence_gap_batch_20260514_120000",
            )
        )

        self.assertIn("Batch ID: evidence_gap_batch_20260514_120000", text)
        self.assertIn("Total Gap Rows: 2", text)
        self.assertIn("| P1 | 72 | 2026-05-18 | FIFA World Cup | High vs Miss | high-conf-miss |", text)
        self.assertIn("高置信1X2失误", text)
        self.assertIn("重点赛事", text)
        self.assertIn("优先绑定合法回放链接", text)
        self.assertIn("legal replay links only", text)
        self.assertIn("no auto video download", text)
        self.assertIn("post-match review evidence only", text)
        self.assertIn("pre-match features", text)

    def test_video_review_evidence_gap_batch_plan_lines_handle_empty_rows(self) -> None:
        text = "\n".join(
            build_video_review_evidence_gap_batch_plan_lines(
                [],
                generated_at=datetime(2026, 5, 14, 12, 0, 0),
            )
        )

        self.assertIn("Total Gap Rows: 0", text)
        self.assertIn("当前没有待处理证据缺口", text)
        self.assertIn("legal replay links only", text)

    def test_video_review_evidence_gap_batch_plan_export_message_summarizes_path(self) -> None:
        text = build_video_review_evidence_gap_batch_plan_export_message(
            Path("reports/video_review_evidence_gap_batch_plan_20260514_120304.md"),
            [{"match_id": "gap-1"}, {"match_id": "gap-2"}],
            {"batch_id": "evidence_gap_batch_20260514_120304"},
        )

        self.assertIn("复盘证据缺口批次计划已导出", text)
        self.assertIn("evidence_gap_batch_20260514_120304", text)
        self.assertIn("video_review_evidence_gap_batch_plan_20260514_120304.md", text)
        self.assertIn("待处理: 2 场", text)
        self.assertIn("不自动下载视频", text)

    def test_video_review_evidence_gap_batch_record_tracks_completion(self) -> None:
        rows = build_video_review_evidence_gap_action_rows(
            [
                {
                    "match_id": "gap-1",
                    "match_date": "2026-05-18",
                    "league": "League C",
                    "home_team": "India",
                    "away_team": "Juliet",
                },
                {
                    "match_id": "gap-2",
                    "match_date": "2026-05-19",
                    "league": "League C",
                    "home_team": "Kilo",
                    "away_team": "Lima",
                },
            ],
            limit=2,
        )
        batch = build_video_review_evidence_gap_batch_record(
            rows,
            Path("reports/plan.md"),
            generated_at=datetime(2026, 5, 14, 12, 0, 0),
            batch_id="evidence_gap_batch_test",
        )
        state = build_video_review_evidence_gap_batch_state_with_record({}, batch)

        status = build_video_review_evidence_gap_batch_status(state)
        self.assertEqual(status["status"], "pending")
        self.assertEqual(status["total_count"], 2)
        self.assertEqual(status["pending_count"], 2)

        updated_state, update = build_video_review_evidence_gap_batch_state_with_resolution(
            state,
            "gap-1",
            evidence_kind="external_reference",
            source_name="FIFA+ Archive",
            review_id="vr-gap-1",
            handled_at=datetime(2026, 5, 14, 13, 0, 0),
        )
        updated_status = build_video_review_evidence_gap_batch_status(updated_state)
        latest_items = updated_state["batches"][0]["items"]

        self.assertEqual(update["updated_count"], 1)
        self.assertEqual(update["batch_ids"], ["evidence_gap_batch_test"])
        self.assertEqual(updated_status["status"], "active")
        self.assertEqual(updated_status["completed_count"], 1)
        self.assertEqual(updated_status["pending_count"], 1)
        resolved_item = next(item for item in latest_items if item["match_id"] == "gap-1")
        pending_item = next(item for item in latest_items if item["match_id"] == "gap-2")
        self.assertEqual(resolved_item["status"], "resolved")
        self.assertEqual(resolved_item["source_name"], "FIFA+ Archive")
        self.assertEqual(resolved_item["evidence_kind"], "external_reference")
        self.assertEqual(pending_item["status"], "pending")

    def test_video_review_evidence_gap_batch_status_rows_show_latest_source(self) -> None:
        batch = {
            "batch_id": "evidence_gap_batch_test",
            "created_at": "2026-05-14 12:00:00",
            "report_path": "reports/plan.md",
            "items": [
                {
                    "match_id": "gap-1",
                    "title": "League C | India vs Juliet",
                    "status": "resolved",
                    "handled_at": "2026-05-14 13:00:00",
                    "source_name": "FIFA+ Archive",
                    "evidence_kind": "external_reference",
                }
            ],
        }

        rows = build_video_review_evidence_gap_batch_status_rows({"batches": [batch]})

        self.assertEqual(rows[0]["tone"], "good")
        self.assertIn("完成率 100%", rows[0]["title"])
        self.assertIn("FIFA+ Archive", rows[0]["body"])
        self.assertIn("external_reference", rows[0]["body"])

    def test_video_review_evidence_gap_batch_filter_options_include_latest_and_filters(self) -> None:
        state = {
            "batches": [
                {
                    "batch_id": "evidence_gap_batch_latest",
                    "items": [{"match_id": "gap-1", "status": "pending"}],
                }
            ]
        }

        options = build_video_review_evidence_gap_batch_filter_options(state)

        self.assertEqual(options["batch_options"][0]["value"], "latest")
        self.assertEqual(options["batch_options"][1]["value"], "all")
        self.assertIn({"label": "未处理", "value": "pending"}, options["status_options"])
        self.assertIn({"label": "P1", "value": "P1"}, options["priority_options"])
        self.assertIn({"label": "事件代理", "value": "event_proxy"}, options["evidence_options"])

    def test_video_review_evidence_gap_batch_filter_result_defaults_to_latest_batch(self) -> None:
        state = {
            "batches": [
                {
                    "batch_id": "latest",
                    "items": [
                        {"match_id": "latest-p1", "title": "Latest P1", "priority_label": "P1", "status": "pending"},
                        {
                            "match_id": "latest-done",
                            "title": "Latest Done",
                            "priority_label": "P2",
                            "status": "resolved",
                            "evidence_kind": "external_reference",
                            "source_name": "FIFA+ Archive",
                            "handled_at": "2026-05-14 13:00:00",
                        },
                    ],
                },
                {
                    "batch_id": "older",
                    "items": [{"match_id": "older-p1", "title": "Older P1", "priority_label": "P1", "status": "pending"}],
                },
            ]
        }

        result = build_video_review_evidence_gap_batch_filter_result(state)

        self.assertEqual([item["match_id"] for item in result["items"]], ["latest-p1", "latest-done"])
        self.assertEqual(result["summary"]["total_count"], 2)
        self.assertEqual(result["summary"]["pending_count"], 1)
        self.assertEqual(result["summary"]["resolved_count"], 1)
        self.assertEqual(result["summary"]["video_count"], 1)
        self.assertEqual(result["summary"]["missing_count"], 1)
        self.assertNotIn("older-p1", [item["match_id"] for item in result["items"]])

    def test_video_review_evidence_gap_batch_filter_result_filters_status_priority_and_evidence(self) -> None:
        state = {
            "batches": [
                {
                    "batch_id": "latest",
                    "items": [
                        {"match_id": "p1-pending", "title": "P1 Pending", "priority_label": "P1", "status": "pending"},
                        {
                            "match_id": "p1-video",
                            "title": "P1 Video",
                            "priority_label": "P1",
                            "status": "resolved",
                            "evidence_kind": "external_reference",
                            "source_name": "FIFA+ Archive",
                        },
                        {
                            "match_id": "p2-event",
                            "title": "P2 Event",
                            "priority_label": "P2",
                            "status": "resolved",
                            "evidence_kind": "statsbomb_event_proxy",
                            "source_name": "StatsBomb/Event Proxy",
                        },
                    ],
                }
            ]
        }

        pending_p1 = build_video_review_evidence_gap_batch_filter_result(
            state,
            status_filter="pending",
            priority_filter="P1",
        )
        video = build_video_review_evidence_gap_batch_filter_result(state, evidence_filter="video")
        event_proxy = build_video_review_evidence_gap_batch_filter_result(state, evidence_filter="event_proxy")

        self.assertEqual([item["match_id"] for item in pending_p1["items"]], ["p1-pending"])
        self.assertEqual([item["match_id"] for item in video["items"]], ["p1-video"])
        self.assertEqual([item["match_id"] for item in event_proxy["items"]], ["p2-event"])

    def test_video_review_evidence_gap_batch_filter_rows_format_table_data(self) -> None:
        result = build_video_review_evidence_gap_batch_filter_result(
            {
                "batches": [
                    {
                        "batch_id": "latest",
                        "report_path": "reports/plan.md",
                        "items": [
                            {
                                "match_id": "p1-video",
                                "title": "P1 Video",
                                "priority_label": "P1",
                                "priority_score": 60,
                                "status": "resolved",
                                "evidence_kind": "external_reference",
                                "source_name": "FIFA+ Archive",
                                "handled_at": "2026-05-14 13:00:00",
                            }
                        ],
                    }
                ]
            }
        )

        rows = build_video_review_evidence_gap_batch_filter_rows(result)

        self.assertEqual(rows[0]["priority"], "P1")
        self.assertEqual(rows[0]["score"], "60")
        self.assertEqual(rows[0]["status"], "已处理")
        self.assertEqual(rows[0]["evidence"], "external_reference")
        self.assertIn("FIFA+ Archive", rows[0]["body"])
        self.assertEqual(rows[0]["tone"], "good")

    def test_video_review_evidence_gap_batch_filter_report_filename_is_stable(self) -> None:
        self.assertEqual(
            build_video_review_evidence_gap_batch_filter_report_filename(datetime(2026, 5, 17, 9, 8, 7)),
            "video_review_evidence_gap_batch_filter_report_20260517_090807.md",
        )

    def test_video_review_evidence_gap_batch_filter_report_lines_include_filters_and_rows(self) -> None:
        result = build_video_review_evidence_gap_batch_filter_result(
            {
                "batches": [
                    {
                        "batch_id": "latest",
                        "items": [
                            {
                                "match_id": "p1-pending",
                                "title": "P1 Pending",
                                "priority_label": "P1",
                                "priority_score": 60,
                                "status": "pending",
                            },
                            {
                                "match_id": "p2-event",
                                "title": "P2 Event",
                                "priority_label": "P2",
                                "priority_score": 35,
                                "status": "resolved",
                                "evidence_kind": "statsbomb_event_proxy",
                                "source_name": "StatsBomb/Event Proxy",
                                "handled_at": "2026-05-17 09:00:00",
                            },
                        ],
                    }
                ]
            },
            batch_filter="latest",
            status_filter="all",
            priority_filter="all",
            evidence_filter="all",
        )

        text = "\n".join(
            build_video_review_evidence_gap_batch_filter_report_lines(
                result,
                generated_at=datetime(2026, 5, 17, 9, 8, 7),
            )
        )

        self.assertIn("Batch Filter: latest", text)
        self.assertIn("Status Filter: all", text)
        self.assertIn("匹配 2 项", text)
        self.assertIn("| P1 | 60 | 未处理 | missing | - | - | p1-pending | P1 Pending |", text)
        self.assertIn("StatsBomb/Event Proxy", text)
        self.assertIn("no auto video download", text)

    def test_video_review_evidence_gap_batch_filter_report_message_summarizes_export(self) -> None:
        result = {"summary": {"summary_text": "匹配 2 项 | 未处理 1 | 已处理 1"}}
        text = build_video_review_evidence_gap_batch_filter_report_message(
            Path("reports/video_review_evidence_gap_batch_filter_report_20260517_090807.md"),
            result,
        )

        self.assertIn("复盘证据缺口批次处理报告已导出", text)
        self.assertIn("video_review_evidence_gap_batch_filter_report_20260517_090807.md", text)
        self.assertIn("匹配 2 项", text)
        self.assertIn("不自动下载视频", text)

    def test_video_review_evidence_gap_batch_action_rows_offer_pending_actions(self) -> None:
        rows = build_video_review_evidence_gap_batch_action_rows(
            {
                "match_id": "gap-1",
                "status": "pending",
                "evidence_kind": "missing",
            }
        )

        keys = [row["action_key"] for row in rows]
        self.assertIn("show_settlement_detail", keys)
        self.assertIn("bind_external_reference", keys)
        self.assertIn("import_local_video", keys)
        self.assertIn("build_statsbomb_review_samples", keys)
        self.assertTrue(all(row["enabled"] for row in rows))

    def test_video_review_evidence_gap_batch_action_rows_limit_resolved_actions(self) -> None:
        rows = build_video_review_evidence_gap_batch_action_rows(
            {
                "match_id": "gap-1",
                "status": "resolved",
                "evidence_kind": "external_reference",
            }
        )

        keys = [row["action_key"] for row in rows]
        self.assertEqual(keys, ["show_settlement_detail", "refresh_batch_status"])
        self.assertTrue(all(row["enabled"] for row in rows))

    def test_video_review_evidence_gap_batch_action_rows_require_selection(self) -> None:
        rows = build_video_review_evidence_gap_batch_action_rows({})

        self.assertEqual(rows[0]["action_key"], "select_gap_item")
        self.assertFalse(rows[0]["enabled"])
        self.assertIn("请先", rows[0]["body"])

    def test_find_video_review_evidence_gap_settlement_matches_id(self) -> None:
        settlement = find_video_review_evidence_gap_settlement(
            [
                {"match_id": "gap-1", "home_team": "India"},
                {"match_id": "gap-2", "home_team": "Kilo"},
            ],
            "gap-2",
        )

        self.assertEqual(settlement["home_team"], "Kilo")
        self.assertIsNone(find_video_review_evidence_gap_settlement([{"match_id": "gap-1"}], "missing"))

    def test_video_review_evidence_gap_batch_resolution_uses_statsbomb_sample_ids(self) -> None:
        batch = build_video_review_evidence_gap_batch_record(
            [
                {
                    "match_id": "sample-gap",
                    "title": "2026-05-18 | League C | India vs Juliet",
                    "priority_label": "P2",
                    "priority_score": 35,
                    "priority_reasons": ["常规缺证据"],
                    "settlement": {"match_id": "sample-gap"},
                }
            ],
            Path("reports/plan.md"),
            batch_id="evidence_gap_batch_test",
            generated_at=datetime(2026, 5, 14, 12, 0, 0),
        )
        state = build_video_review_evidence_gap_batch_state_with_record({}, batch)
        sample_ids = collect_video_review_evidence_gap_sample_match_ids(
            {"items": [{"meta": {"source": "statsbomb_event_sandbox", "match_id": "sample-gap"}}]}
        )

        updated_state, update = build_video_review_evidence_gap_batch_state_with_resolution(
            state,
            sample_ids,
            evidence_kind="statsbomb_event_proxy",
            source_name="StatsBomb/Event Proxy",
            review_id="statsbomb_review_training_samples",
        )

        self.assertEqual(sample_ids, {"sample-gap"})
        self.assertEqual(update["updated_count"], 1)
        self.assertEqual(updated_state["batches"][0]["status"], "completed")
        self.assertEqual(updated_state["batches"][0]["items"][0]["evidence_kind"], "statsbomb_event_proxy")

    def test_video_review_evidence_gap_feedback_tracks_external_reference_resolution(self) -> None:
        feedback = build_video_review_evidence_gap_feedback(
            {
                "match_id": "gap-1",
                "match_date": "2026-05-18",
                "league": "League C",
                "home_team": "India",
                "away_team": "Juliet",
            },
            {"ok": True, "review": {"review_id": "vr-gap-1"}},
            source_name="FIFA+ Archive",
        )

        self.assertEqual(feedback["action_key"], "bind_external_reference")
        self.assertEqual(feedback["match_id"], "gap-1")
        self.assertEqual(feedback["before_kind"], "missing_evidence")
        self.assertEqual(feedback["after_kind"], "external_reference")
        self.assertEqual(feedback["outcome"], "resolved")
        self.assertEqual(feedback["tone"], "good")
        self.assertEqual(feedback["source_name"], "FIFA+ Archive")
        self.assertEqual(feedback["review_id"], "vr-gap-1")

    def test_video_review_evidence_gap_feedback_rows_format_history(self) -> None:
        rows = build_video_review_evidence_gap_feedback_rows(
            [
                {
                    "occurred_at": "2026-05-14 12:00:00",
                    "title": "League C | India vs Juliet",
                    "outcome": "resolved",
                    "summary_text": "missing_evidence->external_reference",
                    "source_name": "FIFA+ Archive",
                    "review_id": "vr-gap-1",
                    "next_recommendation": "annotate events",
                    "tone": "good",
                }
            ]
        )

        self.assertEqual(rows[0]["tone"], "good")
        self.assertIn("resolved", rows[0]["title"])
        self.assertIn("FIFA+ Archive", rows[0]["body"])
        self.assertIn("annotate events", rows[0]["body"])

    def test_review_training_quality_export_message_summarizes_report(self) -> None:
        text = build_statsbomb_review_training_quality_export_message(
            Path("reports/statsbomb_review_training_quality_20260514_120000.md"),
            {
                "status": "attention",
                "sample_count": 18,
                "issue_count": 2,
                "weight_gate": {"mode": "report_only", "enabled": False},
            },
            3,
            gate_audit_count=4,
        )

        self.assertIn("StatsBomb/Event Proxy 样本质量报告已导出", text)
        self.assertIn("质量状态: attention", text)
        self.assertIn("样本: 18", text)
        self.assertIn("问题数: 2", text)
        self.assertIn("权重Gate: report_only", text)
        self.assertIn("修复记录: 3", text)
        self.assertIn("Gate", text)
        self.assertIn("4", text)

    def test_review_training_weight_gate_audit_record_extracts_gate_state(self) -> None:
        record = build_statsbomb_review_training_weight_gate_audit_record(
            "quality_report_export",
            {
                "status": "healthy",
                "sample_count": 49,
                "feature_count": 38,
                "issue_count": 0,
                "signal": {
                    "weight_gate": {
                        "mode": "active",
                        "enabled": True,
                        "reason": "statsbomb_review_quality_healthy",
                    },
                    "active_codes": ["statsbomb_xg_against_pick"],
                    "memory_tags": ["statsbomb_event_proxy"],
                },
            },
            {"message": "exported"},
            report_path=Path("reports/quality.md"),
            occurred_at=datetime(2026, 5, 14, 12, 0, 0),
        )

        self.assertEqual(record["occurred_at"], "2026-05-14 12:00:00")
        self.assertEqual(record["trigger"], "quality_report_export")
        self.assertEqual(record["quality_status"], "healthy")
        self.assertEqual(record["sample_count"], 49)
        self.assertEqual(record["feature_count"], 38)
        self.assertEqual(record["gate_mode"], "active")
        self.assertTrue(record["gate_enabled"])
        self.assertEqual(record["gate_reason"], "statsbomb_review_quality_healthy")
        self.assertEqual(record["active_codes"], ["statsbomb_xg_against_pick"])
        self.assertEqual(record["memory_tags"], ["statsbomb_event_proxy"])
        self.assertEqual(record["message"], "exported")
        self.assertIn("quality.md", record["report_path"])

    def test_review_training_weight_gate_audit_record_from_feedback_uses_after_gate(self) -> None:
        feedback = build_statsbomb_review_training_action_feedback(
            "build_statsbomb_review_samples",
            {
                "status": "blocked",
                "sample_count": 0,
                "issue_count": 1,
                "weight_gate": {"mode": "disabled", "enabled": False},
            },
            {
                "status": "attention",
                "sample_count": 18,
                "feature_count": 10,
                "issue_count": 1,
                "issues": [{"code": "statsbomb_review_sample_count_low"}],
                "signal": {
                    "weight_gate": {
                        "mode": "report_only",
                        "enabled": False,
                        "reason": "statsbomb_review_quality_not_healthy",
                    },
                    "active_codes": ["statsbomb_xg_against_pick"],
                    "memory_tags": ["statsbomb_event_proxy"],
                },
            },
            {"ok": True},
            occurred_at=datetime(2026, 5, 14, 12, 5, 0),
        )
        record = build_statsbomb_review_training_weight_gate_audit_record_from_feedback(
            feedback,
            occurred_at=datetime(2026, 5, 14, 12, 6, 0),
        )

        self.assertEqual(record["trigger"], "build_statsbomb_review_samples")
        self.assertEqual(record["quality_status"], "attention")
        self.assertEqual(record["sample_count"], 18)
        self.assertEqual(record["feature_count"], 10)
        self.assertEqual(record["gate_mode"], "report_only")
        self.assertFalse(record["gate_enabled"])
        self.assertEqual(record["gate_reason"], "statsbomb_review_quality_not_healthy")
        self.assertEqual(record["active_codes"], ["statsbomb_xg_against_pick"])
        self.assertEqual(record["issue_codes"], ["statsbomb_review_sample_count_low"])

    def test_review_training_weight_gate_audit_rows_show_recent_transition(self) -> None:
        rows = build_statsbomb_review_training_weight_gate_audit_rows(
            [
                {
                    "occurred_at": "2026-05-14 12:10:00",
                    "trigger": "quality_report_export",
                    "quality_status": "healthy",
                    "sample_count": 49,
                    "issue_count": 0,
                    "gate_mode": "active",
                    "gate_enabled": True,
                    "gate_reason": "statsbomb_review_quality_healthy",
                    "active_codes": ["statsbomb_xg_against_pick"],
                },
                {
                    "occurred_at": "2026-05-14 12:00:00",
                    "trigger": "build_statsbomb_review_samples",
                    "quality_status": "attention",
                    "sample_count": 18,
                    "issue_count": 1,
                    "gate_mode": "report_only",
                    "gate_enabled": False,
                    "gate_reason": "statsbomb_review_quality_not_healthy",
                },
            ]
        )

        self.assertEqual(rows[0]["tone"], "good")
        self.assertIn("report_only->active", rows[0]["title"])
        self.assertIn("quality=healthy", rows[0]["body"])
        self.assertIn("statsbomb_xg_against_pick", rows[0]["body"])

    def test_review_training_weight_gate_trend_summary_counts_modes(self) -> None:
        summary = build_statsbomb_review_training_weight_gate_trend_summary(
            [
                {
                    "occurred_at": "2026-05-14 12:10:00",
                    "trigger": "quality_report_export",
                    "quality_status": "healthy",
                    "gate_mode": "active",
                    "gate_enabled": True,
                },
                {
                    "occurred_at": "2026-05-14 12:05:00",
                    "trigger": "build_statsbomb_review_samples",
                    "quality_status": "attention",
                    "gate_mode": "report_only",
                    "gate_enabled": False,
                },
                {
                    "occurred_at": "2026-05-14 12:00:00",
                    "trigger": "refresh_review_center",
                    "quality_status": "blocked",
                    "gate_mode": "disabled",
                    "gate_enabled": False,
                },
            ]
        )

        self.assertEqual(summary["status"], "active")
        self.assertEqual(summary["tone"], "good")
        self.assertEqual(summary["active_count"], 1)
        self.assertEqual(summary["report_only_count"], 1)
        self.assertEqual(summary["disabled_count"], 1)
        self.assertEqual(summary["transition_count"], 2)
        self.assertIn("disabled -> report_only -> active", summary["trend_text"])
        self.assertIn("A1/R1/D1", summary["card_rows"][2]["value"])

    def test_review_training_weight_gate_alert_summary_flags_streak_and_regression(self) -> None:
        streak_summary = build_statsbomb_review_training_weight_gate_alert_summary(
            [
                {
                    "occurred_at": "2026-05-14 12:10:00",
                    "trigger": "quality_report_export",
                    "quality_status": "attention",
                    "gate_mode": "report_only",
                    "gate_enabled": False,
                },
                {
                    "occurred_at": "2026-05-14 12:05:00",
                    "trigger": "build_statsbomb_review_samples",
                    "quality_status": "attention",
                    "gate_mode": "disabled",
                    "gate_enabled": False,
                },
                {
                    "occurred_at": "2026-05-14 12:00:00",
                    "trigger": "refresh_review_center",
                    "quality_status": "blocked",
                    "gate_mode": "report_only",
                    "gate_enabled": False,
                },
            ]
        )
        regression_summary = build_statsbomb_review_training_weight_gate_alert_summary(
            [
                {
                    "occurred_at": "2026-05-14 12:15:00",
                    "trigger": "quality_report_export",
                    "quality_status": "attention",
                    "gate_mode": "report_only",
                    "gate_enabled": False,
                },
                {
                    "occurred_at": "2026-05-14 12:10:00",
                    "trigger": "build_statsbomb_review_samples",
                    "quality_status": "healthy",
                    "gate_mode": "active",
                    "gate_enabled": True,
                },
            ]
        )

        self.assertEqual(streak_summary["status"], "blocked")
        self.assertEqual(streak_summary["alert_count"], 2)
        self.assertEqual(streak_summary["blocking_count"], 1)
        self.assertEqual(streak_summary["warning_count"], 1)
        self.assertEqual(streak_summary["non_active_streak"], 3)
        self.assertIn("最近 3 次 gate 都不是 active", streak_summary["body"])
        self.assertIn("gate_non_active_streak", {item["code"] for item in streak_summary["alerts"]})
        self.assertEqual(regression_summary["status"], "attention")
        self.assertEqual(regression_summary["regression_count"], 1)
        self.assertIn("active -> report_only/disabled 回退", regression_summary["body"])
        self.assertIn("gate_active_regression", {item["code"] for item in regression_summary["alerts"]})

    def test_review_training_weight_gate_alert_lines_render_table(self) -> None:
        summary = build_statsbomb_review_training_weight_gate_alert_summary(
            [
                {
                    "occurred_at": "2026-05-14 12:10:00",
                    "trigger": "quality_report_export",
                    "quality_status": "attention",
                    "gate_mode": "report_only",
                    "gate_enabled": False,
                },
                {
                    "occurred_at": "2026-05-14 12:05:00",
                    "trigger": "build_statsbomb_review_samples",
                    "quality_status": "attention",
                    "gate_mode": "disabled",
                    "gate_enabled": False,
                },
                {
                    "occurred_at": "2026-05-14 12:00:00",
                    "trigger": "refresh_review_center",
                    "quality_status": "blocked",
                    "gate_mode": "report_only",
                    "gate_enabled": False,
                },
            ]
        )
        payload = "\n".join(build_statsbomb_review_training_weight_gate_alert_lines(summary))

        self.assertIn("权重Gate告警", payload)
        self.assertIn("gate_non_active_streak", payload)
        self.assertIn("blocking", payload)

    def test_review_training_weight_gate_audit_log_appends_newest_and_caps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "statsbomb_review_weight_gate_audit.json"
            for index in range(3):
                _append_statsbomb_review_training_weight_gate_audit_log(
                    {
                        "occurred_at": f"2026-05-14 12:0{index}:00",
                        "trigger": f"trigger-{index}",
                        "gate_mode": "active" if index == 2 else "report_only",
                    },
                    path=path,
                    limit=2,
                )

            records = _load_statsbomb_review_training_weight_gate_audit_log(path)

        self.assertEqual([record["trigger"] for record in records], ["trigger-2", "trigger-1"])

    def test_export_review_training_quality_report_records_gate_audit(self) -> None:
        class _StatusVar:
            def __init__(self) -> None:
                self.value = ""

            def set(self, value: str) -> None:
                self.value = value

        dashboard = object.__new__(SmartMatchDashboard)
        dashboard.status_var = _StatusVar()
        quality = {
            "status": "healthy",
            "sample_count": 49,
            "feature_count": 38,
            "issue_count": 0,
            "weight_gate": {
                "mode": "active",
                "enabled": True,
                "reason": "statsbomb_review_quality_healthy",
            },
        }
        dashboard._current_statsbomb_review_training_quality = lambda: quality
        with tempfile.TemporaryDirectory() as tmp:
            with patch("v24_app.ai_dashboard.REPORT_DIR", Path(tmp)), patch(
                "v24_app.ai_dashboard._load_statsbomb_review_training_action_feedback_log",
                return_value=[],
            ), patch(
                "v24_app.ai_dashboard._append_statsbomb_review_training_weight_gate_audit_log"
            ) as append_audit, patch(
                "v24_app.ai_dashboard._load_statsbomb_review_training_weight_gate_audit_log",
                return_value=[{"gate_mode": "active"}],
            ), patch("v24_app.ai_dashboard.messagebox.showinfo") as showinfo:
                path = dashboard.export_statsbomb_review_training_quality_report()
                report_payload = path.read_text(encoding="utf-8")

        self.assertTrue(path.name.startswith("statsbomb_review_training_quality_"))
        self.assertIn("权重Gate趋势", report_payload)
        self.assertIn("权重Gate告警", report_payload)
        self.assertIn("quality_report_export", report_payload)
        append_audit.assert_called_once()
        audit = append_audit.call_args.args[0]
        self.assertEqual(audit["trigger"], "quality_report_export")
        self.assertEqual(audit["gate_mode"], "active")
        self.assertTrue(audit["gate_enabled"])
        self.assertIn("quality report exported", audit["message"])
        self.assertIn("Gate", showinfo.call_args.args[1])
        self.assertIn("Gate告警", showinfo.call_args.args[1])

    def test_review_training_action_feedback_summarizes_quality_delta(self) -> None:
        feedback = build_statsbomb_review_training_action_feedback(
            "build_statsbomb_review_samples",
            {
                "status": "blocked",
                "sample_count": 0,
                "issue_count": 2,
                "issues": [{"code": "statsbomb_review_samples_missing"}],
                "weight_gate": {"mode": "disabled", "enabled": False},
            },
            {
                "status": "attention",
                "sample_count": 18,
                "issue_count": 1,
                "issues": [{"code": "statsbomb_review_sample_count_low", "recommendation": "继续补样本"}],
                "weight_gate": {"mode": "report_only", "enabled": False},
            },
            {"ok": True, "message": "done"},
        )

        self.assertEqual(feedback["outcome"], "improved")
        self.assertEqual(feedback["tone"], "good")
        self.assertEqual(feedback["sample_delta"], 18)
        self.assertEqual(feedback["issue_delta"], -1)
        self.assertEqual(feedback["before_weight_gate_mode"], "disabled")
        self.assertEqual(feedback["after_weight_gate_mode"], "report_only")
        self.assertFalse(feedback["after_weight_gate_enabled"])
        self.assertIn("blocked->attention", feedback["summary_text"])
        self.assertIn("gate disabled->report_only", feedback["summary_text"])
        self.assertEqual(feedback["next_recommendation"], "继续补样本")

    def test_review_training_action_feedback_supports_recovery_rebuild(self) -> None:
        feedback = build_statsbomb_review_training_action_feedback(
            "recover_results_rebuild_samples",
            {"status": "attention", "sample_count": 8, "issue_count": 2, "issues": []},
            {"status": "healthy", "sample_count": 24, "issue_count": 0, "issues": []},
            {"ok": True, "message": "result recovery completed"},
        )

        self.assertEqual(feedback["outcome"], "improved")
        self.assertEqual(feedback["after_status"], "healthy")
        self.assertEqual(feedback["sample_delta"], 16)
        self.assertEqual(feedback["next_recommendation"], "质量已恢复健康，可进入回测/训练稳定性验证。")

    def test_review_training_action_feedback_marks_failed_and_queued(self) -> None:
        quality = {"status": "attention", "sample_count": 10, "issue_count": 1, "issues": []}
        failed = build_statsbomb_review_training_action_feedback(
            "build_statsbomb_review_samples",
            quality,
            quality,
            {"ok": False, "message": "boom"},
        )
        queued = build_statsbomb_review_training_action_feedback(
            "recover_results",
            quality,
            quality,
            {"ok": True, "queued": True},
        )

        self.assertEqual(failed["outcome"], "failed")
        self.assertEqual(failed["tone"], "bad")
        self.assertEqual(queued["outcome"], "queued")
        self.assertEqual(queued["tone"], "neutral")

    def test_review_training_feedback_rows_format_recent_records(self) -> None:
        rows = build_statsbomb_review_training_feedback_rows(
            [
                {
                    "occurred_at": "2026-05-14 12:00:00",
                    "action_key": "build_statsbomb_review_samples",
                    "outcome": "improved",
                    "summary_text": "samples 0->18",
                    "weight_gate_change": "disabled->report_only",
                    "after_issue_codes": ["statsbomb_review_sample_count_low"],
                    "next_recommendation": "继续补样本",
                    "tone": "good",
                }
            ]
        )

        self.assertEqual(rows[0]["tone"], "good")
        self.assertIn("build_statsbomb_review_samples", rows[0]["title"])
        self.assertIn("samples 0->18", rows[0]["body"])
        self.assertIn("权重Gate: disabled->report_only", rows[0]["body"])
        self.assertIn("继续补样本", rows[0]["body"])

    def test_review_training_center_summary_compacts_quality_and_repair_state(self) -> None:
        summary = build_statsbomb_review_training_center_summary(
            {
                "status": "attention",
                "sample_count": 18,
                "issue_count": 2,
                "issues": [{"code": "statsbomb_review_sample_count_low", "severity": "warning"}],
            },
            [
                {
                    "occurred_at": "2026-05-17 09:00:00",
                    "action_key": "build_statsbomb_review_samples",
                    "outcome": "improved",
                }
            ],
            [
                {
                    "occurred_at": "2026-05-17 09:10:00",
                    "trigger": "quality_report_export",
                    "gate_mode": "report_only",
                    "gate_enabled": False,
                    "quality_status": "attention",
                },
                {
                    "occurred_at": "2026-05-17 09:05:00",
                    "trigger": "build_statsbomb_review_samples",
                    "gate_mode": "active",
                    "gate_enabled": True,
                    "quality_status": "healthy",
                }
            ],
        )

        self.assertEqual(summary["status"], "attention")
        self.assertEqual(summary["tone"], "warning")
        self.assertEqual(summary["sample_count"], 18)
        self.assertEqual(summary["issue_count"], 2)
        self.assertEqual(summary["repair_count"], 1)
        self.assertEqual(summary["gate_audit_count"], 2)
        self.assertEqual(summary["gate_alert_count"], 3)
        self.assertEqual(summary["gate_trend"]["status"], "report_only")
        self.assertEqual(summary["gate_alert_status"], "attention")
        self.assertIn("事件代理质量", summary["title"])
        self.assertIn("样本 18", summary["body"])
        self.assertIn("2026-05-17 09:00:00", summary["body"])
        self.assertIn("2026-05-17 09:10:00", summary["body"])
        self.assertIn("Gate趋势", summary["body"])
        self.assertIn("Gate告警", summary["body"])

    def test_review_training_closure_summary_tracks_pending_and_resolved_matches(self) -> None:
        review_samples = {
            "items": [
                {"match_id": "m-1"},
                {"match_id": "m-2"},
            ]
        }
        evidence_gap_state = {
            "batches": [
                {
                    "batch_id": "batch-1",
                    "items": [
                        {
                            "match_id": "m-1",
                            "status": "resolved",
                            "handled_at": "2026-05-17 09:10:00",
                            "source_name": "StatsBomb/Event Proxy",
                            "review_id": "review-1",
                            "evidence_kind": "statsbomb_event_proxy",
                        },
                        {
                            "match_id": "m-2",
                            "status": "pending",
                            "handled_at": "",
                            "source_name": "",
                            "review_id": "",
                            "evidence_kind": "",
                        },
                    ],
                }
            ]
        }

        with patch(
            "v24_app.ai_dashboard.build_statsbomb_review_training_quality_summary",
            return_value={"status": "healthy", "sample_count": 2, "issue_count": 0, "card_rows": []},
        ):
            summary = build_statsbomb_review_training_closure_summary(review_samples, evidence_gap_state)

        self.assertEqual(summary["status"], "attention")
        self.assertEqual(summary["tone"], "warning")
        self.assertEqual(summary["sample_count"], 2)
        self.assertEqual(summary["sample_match_count"], 2)
        self.assertEqual(summary["linked_match_count"], 2)
        self.assertEqual(summary["closed_count"], 1)
        self.assertEqual(summary["pending_count"], 1)
        self.assertEqual(summary["unmatched_sample_count"], 0)
        self.assertIn("闭环", summary["title"])
        self.assertIn("已回写 1", summary["body"])
        self.assertGreaterEqual(len(summary["card_rows"]), 4)
        self.assertEqual(summary["rows"][0]["tone"], "warning")

    def test_review_training_closure_summary_is_blocked_without_samples(self) -> None:
        with patch(
            "v24_app.ai_dashboard.build_statsbomb_review_training_quality_summary",
            return_value={"status": "blocked", "sample_count": 0, "issue_count": 1, "card_rows": []},
        ):
            summary = build_statsbomb_review_training_closure_summary({}, {"batches": []})

        self.assertEqual(summary["status"], "blocked")
        self.assertEqual(summary["tone"], "bad")
        self.assertEqual(summary["sample_count"], 0)
        self.assertEqual(summary["sample_match_count"], 0)
        self.assertEqual(summary["closed_count"], 0)
        self.assertEqual(summary["pending_count"], 0)
        self.assertEqual(summary["rows"], [])

    def test_review_training_action_rows_map_issues_to_executable_actions(self) -> None:
        rows = build_statsbomb_review_training_action_rows(
            {
                "status": "blocked",
                "sample_count": 0,
                "issues": [
                    {
                        "code": "prediction_miss_skewed",
                        "severity": "warning",
                        "message": "标签偏斜",
                        "recommendation": "补齐弱类别样本",
                    },
                    {
                        "code": "statsbomb_review_samples_missing",
                        "severity": "blocking",
                        "message": "样本为空",
                        "recommendation": "生成复盘样本",
                    },
                    {
                        "code": "statsbomb_review_features_missing",
                        "severity": "warning",
                        "message": "缺少特征",
                        "recommendation": "重建特征",
                    },
                ],
            }
        )

        self.assertEqual(rows[0]["action_key"], "build_statsbomb_review_samples")
        self.assertEqual(rows[0]["tone"], "danger")
        self.assertIn("点击后会重建 StatsBomb/Event Proxy", rows[0]["body"])
        self.assertEqual(rows[1]["action_key"], "recover_results")
        self.assertIn("回收后再生成事件代理复盘样本", rows[1]["body"])
        self.assertEqual(len({row["action_key"] for row in rows}), len(rows))

    def test_review_training_action_rows_offer_backtest_when_healthy(self) -> None:
        rows = build_statsbomb_review_training_action_rows(
            {
                "status": "healthy",
                "sample_count": 42,
                "issues": [],
            }
        )

        self.assertEqual(rows[0]["action_key"], "run_high_accuracy_strategy_backtest")
        self.assertEqual(rows[0]["tone"], "good")
        self.assertIn("42", rows[0]["body"])

    def test_review_samples_message_includes_quality_and_repair_guidance(self) -> None:
        text = build_statsbomb_event_proxy_review_samples_message(
            {
                "generated_sample_count": 12,
                "skipped_reasons": {"missing_statsbomb": 2, "unknown_label": 1},
                "output_path": "data/state/statsbomb_review_training_samples.json",
            },
            {
                "status": "attention",
                "issue_count": 2,
                "label_rows": [
                    {
                        "label": "1X2错因标签",
                        "value": "8/12",
                        "detail": "hit=4 | miss=8 | miss_rate=66.7%",
                    }
                ],
                "weight_rows": [
                    {
                        "label": "终结波动",
                        "value": "1.35",
                        "detail": "仅用于Evaluation Agent错因排序",
                    }
                ],
                "issues": [
                    {
                        "code": "xgb_label_class_missing",
                        "severity": "warning",
                        "message": "补平局/客胜弱类别",
                        "recommendation": "补齐弱类别样本",
                    },
                    {
                        "code": "statsbomb_review_samples_missing",
                        "severity": "blocking",
                        "message": "先补样本",
                        "recommendation": "生成事件代理复盘样本",
                    },
                ],
                "leakage_note": "仅赛后使用，不能进入赛前特征",
            },
        )

        self.assertIn("样本: 12", text)
        self.assertIn("质量状态: attention | issues=2", text)
        self.assertIn("标签分布:", text)
        self.assertIn("1X2错因标签: 8/12", text)
        self.assertIn("事件错因权重:", text)
        self.assertIn("终结波动: 1.35", text)
        self.assertLess(text.index("先补样本"), text.index("补平局/客胜弱类别"))
        self.assertIn("仅赛后使用，不能进入赛前特征", text)

    def test_missing_event_summary_returns_fallback_guidance(self) -> None:
        text = build_statsbomb_event_proxy_review_text(
            {
                "match_id": "m-missing",
                "home_team": "Alpha",
                "away_team": "Bravo",
            }
        )

        self.assertIn("StatsBomb 事件代理复盘", text)
        self.assertIn("暂无事件代理数据", text)
        self.assertIn("不进入赛前预测特征", text)

    def test_event_summary_builds_proxy_review_without_pre_match_leakage(self) -> None:
        text = build_statsbomb_event_proxy_review_text(
            {
                "match_id": "m1",
                "home_team": "Bayer Leverkusen",
                "away_team": "Werder Bremen",
                "statsbomb_source_match_id": 3895302,
                "statsbomb_event_summary": {
                    "event_count": 4223,
                    "first_goal_minute": 25,
                    "last_goal_minute": 89,
                    "team_stats": {
                        "Bayer Leverkusen": {
                            "xg": 4.02,
                            "shots": 19,
                            "shots_on_target": 11,
                        },
                        "Werder Bremen": {
                            "xg": 0.28,
                            "shots": 8,
                            "shots_on_target": 2,
                        },
                    },
                },
            }
        )

        self.assertIn("source_type=event_proxy", text)
        self.assertIn("source_match_id: 3895302", text)
        self.assertIn("medium / events=4223", text)
        self.assertIn("Bayer Leverkusen 4.02 vs Werder Bremen 0.28 / diff 3.74", text)
        self.assertIn("射门: Bayer Leverkusen 19 vs Werder Bremen 8", text)
        self.assertIn("first=25 / last=89", text)
        self.assertIn("不进入赛前预测特征", text)

    def test_video_review_center_summary_reports_healthy_coverage(self) -> None:
        summary = build_video_review_center_summary(
            {
                "health": {"status": "healthy", "blocking_count": 0, "warning_count": 0},
                "monitor": {"sample_count": 24},
                "card_rows": [{"label": "整体状态", "value": "healthy", "detail": "ok"}],
                "action_rows": [{"title": "进入稳定性复盘", "body": "ready"}],
            },
            {
                "coverage_status": "healthy",
                "total_settled_count": 8,
                "local_video_count": 2,
                "external_reference_count": 3,
                "statsbomb_event_proxy_count": 3,
                "no_review_evidence_count": 0,
            },
        )

        self.assertEqual(summary["status"], "healthy")
        self.assertEqual(summary["tone"], "good")
        self.assertEqual(summary["memory_sample_count"], 24)
        self.assertEqual(summary["resource_closure_status"], "healthy")
        self.assertIn("资源闭环", summary["body"])
        self.assertIn("本地视频 2", summary["body"])
        self.assertIn("外部回放 3", summary["body"])
        self.assertIn("事件代理 3", summary["body"])
        self.assertIn("缺证据 0", summary["body"])

    def test_video_review_center_summary_flags_missing_evidence_as_attention(self) -> None:
        summary = build_video_review_center_summary(
            {
                "health": {"status": "healthy", "blocking_count": 0, "warning_count": 0},
                "monitor": {"sample_count": 12},
                "action_rows": [],
            },
            {
                "coverage_status": "attention",
                "total_settled_count": 10,
                "local_video_count": 1,
                "external_reference_count": 2,
                "statsbomb_event_proxy_count": 5,
                "no_review_evidence_count": 2,
            },
        )

        self.assertEqual(summary["status"], "attention")
        self.assertEqual(summary["tone"], "warning")
        self.assertEqual(summary["no_review_evidence_count"], 2)
        self.assertIn("missing 2/10", summary["summary_text"])
        self.assertIn("缺证据 2", summary["body"])

    def test_video_review_center_summary_blocks_when_memory_or_source_blocked(self) -> None:
        summary = build_video_review_center_summary(
            {
                "health": {"status": "blocked", "blocking_count": 1, "warning_count": 2},
                "monitor": {"sample_count": 1},
                "card_rows": [],
                "action_rows": [{"title": "补样", "body": "扩大样本"}],
            },
            {
                "coverage_status": "healthy",
                "total_settled_count": 4,
                "local_video_count": 1,
                "external_reference_count": 1,
                "statsbomb_event_proxy_count": 2,
                "no_review_evidence_count": 0,
            },
        )

        self.assertEqual(summary["status"], "blocked")
        self.assertEqual(summary["tone"], "bad")
        self.assertEqual(summary["issue_count"], 3)
        self.assertEqual(summary["action_count"], 1)
        self.assertEqual(summary["resource_closure_status"], "blocked")
        self.assertIn("复盘受阻", summary["title"])

    def test_video_review_center_action_rows_prioritize_missing_evidence(self) -> None:
        rows = build_video_review_center_action_rows(
            {
                "monitor": {"sample_count": 4},
                "quality": {"alerts": []},
                "health": {"status": "healthy", "issues": []},
            },
            {
                "coverage_status": "blocked",
                "no_review_evidence_count": 2,
                "total_settled_count": 4,
            },
        )

        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(rows[0]["code"], "video_review_missing_local_video")
        self.assertEqual(rows[0]["action_key"], "open_video_review_evidence_gap_center_window_local_video")
        self.assertIn("缺证据 2", rows[0]["body"])
        self.assertEqual(rows[1]["code"], "video_review_missing_external_reference")
        self.assertEqual(rows[1]["action_key"], "open_video_review_evidence_gap_center_window_external_reference")
        self.assertIn("FIFA+", rows[1]["body"])

    def test_video_review_center_action_rows_map_duplicate_keys_to_audit(self) -> None:
        rows = build_video_review_center_action_rows(
            {
                "monitor": {"sample_count": 3},
                "quality": {"alerts": []},
                "health": {
                    "status": "blocked",
                    "issues": [
                        {
                            "code": "video_memory_duplicate_keys",
                            "recommendation": "Deduplicate official video memory.",
                        }
                    ],
                },
            },
            {"coverage_status": "healthy", "no_review_evidence_count": 0},
        )

        self.assertEqual(rows[0]["code"], "video_memory_duplicate_keys")
        self.assertEqual(rows[0]["action_key"], "export_video_review_fewshot_memory_audit")

    def test_video_review_center_action_rows_show_review_center_when_healthy(self) -> None:
        rows = build_video_review_center_action_rows(
            {
                "monitor": {"sample_count": 12},
                "quality": {"alerts": []},
                "health": {"status": "healthy", "issues": []},
            },
            {"coverage_status": "healthy", "no_review_evidence_count": 0},
        )

        self.assertEqual(rows[0]["code"], "video_memory_ready")
        self.assertEqual(rows[0]["action_key"], "open_review_center")
        self.assertEqual(rows[0]["tone"], "good")

    def test_video_review_evidence_gap_quick_open_filters_focus_local_video(self) -> None:
        filters = build_video_review_evidence_gap_quick_open_filters("local_video")

        self.assertEqual(filters["batch_filter"], "latest")
        self.assertEqual(filters["status_filter"], "pending")
        self.assertEqual(filters["priority_filter"], "P0")
        self.assertEqual(filters["evidence_filter"], "local_video")

    def test_video_review_evidence_gap_quick_open_filters_focus_external_reference(self) -> None:
        filters = build_video_review_evidence_gap_quick_open_filters("external_reference")

        self.assertEqual(filters["batch_filter"], "latest")
        self.assertEqual(filters["status_filter"], "pending")
        self.assertEqual(filters["priority_filter"], "P0")
        self.assertEqual(filters["evidence_filter"], "external_reference")

    def test_video_review_evidence_gap_quick_open_filters_select_matching_batch(self) -> None:
        state = {
            "batches": [
                {
                    "batch_id": "batch-new",
                    "items": [
                        {
                            "match_id": "new-1",
                            "status": "pending",
                            "priority_label": "P2",
                            "evidence_kind": "missing",
                        }
                    ],
                },
                {
                    "batch_id": "batch-old",
                    "items": [
                        {
                            "match_id": "old-1",
                            "status": "pending",
                            "priority_label": "P0",
                            "evidence_kind": "local_video",
                        }
                    ],
                },
            ]
        }

        filters = build_video_review_evidence_gap_quick_open_filters("local_video", state)

        self.assertEqual(filters["batch_filter"], "batch-old")
        self.assertEqual(filters["status_filter"], "pending")
        self.assertEqual(filters["priority_filter"], "P0")
        self.assertEqual(filters["evidence_filter"], "local_video")

    def test_video_review_evidence_gap_quick_target_item_prefers_matching_row(self) -> None:
        state = {
            "batches": [
                {
                    "batch_id": "batch-new",
                    "items": [
                        {
                            "match_id": "new-1",
                            "status": "pending",
                            "priority_label": "P2",
                            "evidence_kind": "missing",
                        }
                    ],
                },
                {
                    "batch_id": "batch-old",
                    "items": [
                        {
                            "match_id": "old-1",
                            "status": "pending",
                            "priority_label": "P0",
                            "evidence_kind": "local_video",
                        },
                        {
                            "match_id": "old-2",
                            "status": "pending",
                            "priority_label": "P0",
                            "evidence_kind": "local_video",
                        },
                    ],
                },
            ]
        }

        item = build_video_review_evidence_gap_quick_target_item(state, "local_video")

        self.assertIsNotNone(item)
        self.assertEqual(item["match_id"], "old-1")
        self.assertEqual(item["batch_id"], "batch-old")

    def test_video_review_evidence_gap_next_selection_index_advances_to_next_pending_row(self) -> None:
        rows = [
            {"batch_id": "batch-1", "match_id": "m-1", "status": "resolved"},
            {"batch_id": "batch-1", "match_id": "m-2", "status": "pending"},
            {"batch_id": "batch-1", "match_id": "m-3", "status": "pending"},
        ]

        self.assertEqual(build_video_review_evidence_gap_next_selection_index(rows, current_index=0), 1)

    def test_video_review_evidence_gap_auto_advance_targets_refreshed_rows_by_key(self) -> None:
        rows_before = [
            {"batch_id": "batch-1", "match_id": "m-1", "status": "pending"},
            {"batch_id": "batch-1", "match_id": "m-2", "status": "pending"},
            {"batch_id": "batch-1", "match_id": "m-3", "status": "pending"},
        ]
        next_index = build_video_review_evidence_gap_next_selection_index(rows_before, current_index=1)
        self.assertEqual(next_index, 2)
        next_key = build_video_review_evidence_gap_row_key(rows_before[next_index])

        rows_after = [
            {"batch_id": "batch-1", "match_id": "m-1", "status": "pending"},
            {"batch_id": "batch-1", "match_id": "m-3", "status": "pending"},
        ]

        self.assertEqual(find_video_review_evidence_gap_row_index(rows_after, next_key), 1)


if __name__ == "__main__":
    unittest.main()
