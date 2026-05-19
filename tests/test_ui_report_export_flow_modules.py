from __future__ import annotations

import sys
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.core import AppMatch
from v24_app.ui_modules import (
    build_dashboard_report_preview_summary,
    build_daily_parlay_repair_loop_trend,
    build_daily_parlay_repair_loop_trend_text,
    build_export_message_text,
    build_export_status_text,
    build_report_filename,
    classify_dashboard_report_file,
    collect_visible_match_ids,
    dashboard_report_type_options,
    filter_dashboard_report_rows,
    list_dashboard_report_files,
    resolve_current_filter,
    select_matches_for_export,
    summarize_dashboard_report_types,
    should_run_pre_export_analysis,
)


class _FakeTree:
    def __init__(self, children: list[str]) -> None:
        self._children = children

    def get_children(self, _item: str) -> list[str]:
        return list(self._children)


class _FakeVar:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value


class UIReportExportFlowModuleTests(unittest.TestCase):
    def test_should_run_pre_export_analysis(self) -> None:
        self.assertTrue(should_run_pre_export_analysis({}))
        self.assertTrue(should_run_pre_export_analysis(None))
        self.assertFalse(should_run_pre_export_analysis({"m1": {"confidence": 0.5}}))

    def test_collect_visible_match_ids(self) -> None:
        self.assertEqual(collect_visible_match_ids(None), set())
        self.assertEqual(collect_visible_match_ids(_FakeTree(["m1", "m2"])), {"m1", "m2"})

    def test_select_matches_for_export(self) -> None:
        match_a = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="19:35",
            match_date="2026-04-04",
            odds_home=1.8,
            odds_draw=3.2,
            odds_away=4.0,
        )
        match_b = AppMatch(
            home_team="C",
            away_team="D",
            league="L2",
            match_time="20:00",
            match_date="2026-04-04",
            odds_home=2.0,
            odds_draw=3.1,
            odds_away=3.8,
        )
        self.assertEqual(len(select_matches_for_export([match_a, match_b], set())), 2)
        selected = select_matches_for_export([match_a, match_b], {match_b.match_id})
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].match_id, match_b.match_id)

    def test_filename_filter_and_messages(self) -> None:
        name = build_report_filename("visible", datetime(2026, 4, 4, 12, 30, 15))
        self.assertEqual(name, "recommendation_report_c1_visible_20260404_123015.md")
        self.assertEqual(resolve_current_filter(None), "全部")
        self.assertEqual(resolve_current_filter(_FakeVar("正式建议")), "正式建议")
        self.assertEqual(resolve_current_filter(_FakeVar("  ")), "全部")
        self.assertEqual(build_export_status_text("r.md"), "报告已导出 | r.md")
        msg = build_export_message_text(
            scope_label="全部赛事",
            match_count=8,
            report_path=Path("E:/APP/ELO/reports/r.md"),
        )
        self.assertIn("范围: 全部赛事", msg)
        self.assertIn("场次: 8", msg)
        self.assertIn("r.md", msg)

    def test_dashboard_report_index_includes_release_loop_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            match_report = report_dir / "ai_match_report_20260510_120000_a_vs_b.md"
            loop_report = report_dir / "strategy_release_recovery_loop_20260510_121000.md"
            repair_loop_report = report_dir / "daily_parlay_repair_loop_20260510_122000.md"
            repair_loop_csv = report_dir / "daily_parlay_repair_loop_20260510_122000.csv"
            ignored = report_dir / "strategy_release_recovery_loop_20260510_121000.json"
            match_report.write_text("match", encoding="utf-8")
            loop_report.write_text("loop", encoding="utf-8")
            repair_loop_report.write_text("repair loop", encoding="utf-8")
            repair_loop_csv.write_text("csv", encoding="utf-8-sig")
            ignored.write_text("{}", encoding="utf-8")
            os.utime(match_report, (1000, 1000))
            os.utime(loop_report, (2000, 2000))
            os.utime(repair_loop_report, (1500, 1500))
            os.utime(repair_loop_csv, (1600, 1600))

            rows = list_dashboard_report_files(report_dir)
            rows_with_csv = list_dashboard_report_files(report_dir, include_csv=True)

        self.assertEqual(len(rows), 3)
        self.assertEqual(len(rows_with_csv), 4)
        self.assertEqual(rows_with_csv[0]["name"], loop_report.name)
        self.assertEqual(rows_with_csv[1]["name"], repair_loop_csv.name)
        self.assertEqual(rows_with_csv[1]["label"], "二串一修复闭环")
        self.assertEqual(rows[0]["name"], loop_report.name)
        self.assertEqual(rows[0]["label"], "\u653e\u884c\u95ed\u73af")
        self.assertEqual(rows[1]["name"], repair_loop_report.name)
        self.assertEqual(rows[1]["label"], "二串一修复闭环")
        self.assertEqual(rows[2]["label"], "\u5355\u573a\u5206\u6790")
        self.assertEqual(classify_dashboard_report_file(Path("daily_parlay_repair_loop_20260514_120000.md")), "二串一修复闭环")
        self.assertEqual(classify_dashboard_report_file(Path("video_review_fewshot_memory_audit_20260514_120000.md")), "AI\u89c6\u9891\u5ba1\u8ba1")
        self.assertEqual(classify_dashboard_report_file(Path("unknown_report.md")), "\u5176\u4ed6\u62a5\u544a")

    def test_dashboard_report_filters_by_type_and_query(self) -> None:
        rows = [
            {"name": "ai_match_report_a.md", "label": "\u5355\u573a\u5206\u6790", "path": Path("reports/ai_match_report_a.md")},
            {"name": "strategy_release_recovery_loop_b.md", "label": "\u653e\u884c\u95ed\u73af", "path": Path("reports/strategy_release_recovery_loop_b.md")},
            {"name": "daily_parlay_repair_loop_c.md", "label": "二串一修复闭环", "path": Path("reports/daily_parlay_repair_loop_c.md")},
            {"name": "strategy_release_recovery_loop_c.md", "label": "\u653e\u884c\u95ed\u73af", "path": Path("reports/strategy_release_recovery_loop_c.md")},
        ]

        summary = summarize_dashboard_report_types(rows)
        options = dashboard_report_type_options(rows)
        filtered = filter_dashboard_report_rows(rows, selected_type="\u653e\u884c\u95ed\u73af", query="loop_c")

        self.assertEqual(summary["\u653e\u884c\u95ed\u73af"], 2)
        self.assertEqual(options[0], "\u5168\u90e8")
        self.assertEqual(options[1], "\u653e\u884c\u95ed\u73af")
        self.assertIn("二串一修复闭环", options)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["name"], "strategy_release_recovery_loop_c.md")

    def test_daily_parlay_repair_report_preview_summary_extracts_md_metrics(self) -> None:
        row = {
            "name": "daily_parlay_repair_loop_20260518_130000.md",
            "label": "二串一修复闭环",
            "updated_at": "2026-05-18 13:00",
            "size_bytes": 1200,
        }
        content = "\n".join(
            [
                "# 二串一修复闭环报告",
                "- 生成时间: 2026-05-18 13:00:00",
                "- 修复队列: 待检查 2 | 待修复 1 | 可自动回收 1",
                "- 审计摘要: 二串一修复审计 3 条",
                "- 来源缺口票据: 1",
                "- 混源票据: 0",
                "- 最新待人工: 1",
                "- 累计复跑新结算: 2",
            ]
        )

        summary = build_dashboard_report_preview_summary(row, content)

        self.assertIn("报告摘要", summary)
        self.assertIn("二串一修复闭环", summary)
        self.assertIn("待修复 1", summary)
        self.assertIn("待人工/复跑: 1 / 2", summary)

    def test_daily_parlay_repair_report_preview_summary_extracts_csv_metrics(self) -> None:
        row = {
            "name": "daily_parlay_repair_loop_20260518_130000.csv",
            "label": "二串一修复闭环",
            "updated_at": "2026-05-18 13:00",
            "size_bytes": 900,
        }
        content = "\n".join(
            [
                "record_type,generated_at,status,action,ticket_id,code,updated_ticket_count,updated_leg_count,recovery_new_settled,recovery_gate_status,queue_blocked_after_repair,message,recommendation",
                "audit,2026-05-18 12:01:00,settled,source_backfill,ticket-1,,1,1,2,healthy,0,checked,ok",
                "queue,,blocked,,ticket-2,parlay_source_traceability_missing,,,,,,Missing source_id,Backfill source_id",
            ]
        )

        summary = build_dashboard_report_preview_summary(row, content)

        self.assertIn("审计记录: 1", summary)
        self.assertIn("队列记录: 1", summary)
        self.assertIn("当前待修复: 1", summary)
        self.assertIn("累计复跑新结算: 2", summary)

    def test_daily_parlay_repair_loop_trend_detects_improvement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            older = report_dir / "daily_parlay_repair_loop_20260518_120000.csv"
            newer = report_dir / "daily_parlay_repair_loop_20260518_130000.csv"
            header = (
                "record_type,generated_at,status,action,ticket_id,code,updated_ticket_count,"
                "updated_leg_count,recovery_new_settled,recovery_gate_status,queue_blocked_after_repair,message,recommendation"
            )
            older.write_text(
                "\n".join(
                    [
                        header,
                        "audit,2026-05-18 12:00:00,blocked,source_backfill,ticket-a,,0,0,0,blocked,3,checked,ok",
                        "queue,,blocked,,ticket-a,parlay_source_traceability_missing,,,,,,Missing source_id,Backfill source_id",
                        "queue,,blocked,,ticket-b,parlay_source_traceability_missing,,,,,,Missing source_id,Backfill source_id",
                        "queue,,blocked,,ticket-c,parlay_mixed_source_ticket,,,,,,Mixed source,Split ticket",
                    ]
                ),
                encoding="utf-8-sig",
            )
            newer.write_text(
                "\n".join(
                    [
                        header,
                        "audit,2026-05-18 13:00:00,settled,source_backfill,ticket-a,,1,1,2,healthy,0,checked,ok",
                        "queue,,blocked,,ticket-b,parlay_source_traceability_missing,,,,,,Missing source_id,Backfill source_id",
                    ]
                ),
                encoding="utf-8-sig",
            )
            os.utime(older, (1000, 1000))
            os.utime(newer, (2000, 2000))
            rows = list_dashboard_report_files(report_dir, include_csv=True)
            trend = build_daily_parlay_repair_loop_trend(rows)
            text = build_daily_parlay_repair_loop_trend_text(trend)

        self.assertEqual(trend["status"], "improving")
        self.assertEqual(trend["metrics"][0]["queue_blocked"], 1)
        self.assertEqual(trend["metrics"][0]["recovery_new_settled"], 2)
        self.assertIn("improving", trend["summary"])
        self.assertIn("improving", text)
        self.assertIn("复跑 2", text)


if __name__ == "__main__":
    unittest.main()
