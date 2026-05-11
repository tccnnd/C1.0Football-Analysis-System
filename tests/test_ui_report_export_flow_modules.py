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
            ignored = report_dir / "strategy_release_recovery_loop_20260510_121000.json"
            match_report.write_text("match", encoding="utf-8")
            loop_report.write_text("loop", encoding="utf-8")
            ignored.write_text("{}", encoding="utf-8")
            os.utime(match_report, (1000, 1000))
            os.utime(loop_report, (2000, 2000))

            rows = list_dashboard_report_files(report_dir)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], loop_report.name)
        self.assertEqual(rows[0]["label"], "\u653e\u884c\u95ed\u73af")
        self.assertEqual(rows[1]["label"], "\u5355\u573a\u5206\u6790")
        self.assertEqual(classify_dashboard_report_file(Path("unknown_report.md")), "\u5176\u4ed6\u62a5\u544a")

    def test_dashboard_report_filters_by_type_and_query(self) -> None:
        rows = [
            {"name": "ai_match_report_a.md", "label": "\u5355\u573a\u5206\u6790", "path": Path("reports/ai_match_report_a.md")},
            {"name": "strategy_release_recovery_loop_b.md", "label": "\u653e\u884c\u95ed\u73af", "path": Path("reports/strategy_release_recovery_loop_b.md")},
            {"name": "strategy_release_recovery_loop_c.md", "label": "\u653e\u884c\u95ed\u73af", "path": Path("reports/strategy_release_recovery_loop_c.md")},
        ]

        summary = summarize_dashboard_report_types(rows)
        options = dashboard_report_type_options(rows)
        filtered = filter_dashboard_report_rows(rows, selected_type="\u653e\u884c\u95ed\u73af", query="loop_c")

        self.assertEqual(summary["\u653e\u884c\u95ed\u73af"], 2)
        self.assertEqual(options[0], "\u5168\u90e8")
        self.assertEqual(options[1], "\u653e\u884c\u95ed\u73af")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["name"], "strategy_release_recovery_loop_c.md")


if __name__ == "__main__":
    unittest.main()
