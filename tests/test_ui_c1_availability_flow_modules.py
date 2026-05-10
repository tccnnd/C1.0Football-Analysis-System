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
    build_c1_availability_provider_status_lines,
    build_c1_release_guard_report_filename,
    build_c1_release_guard_report_lines,
    build_c1_release_review_availability_guard,
    build_c1_release_review_guard_status_text,
    build_c1_snapshot_import_message_text,
    build_c1_snapshot_import_status_text,
    build_c1_sync_message_text,
    build_c1_sync_status_text,
    build_c1_template_export_message_text,
    build_c1_template_export_status_text,
    should_auto_rerun_shadow_after_import,
    should_auto_rerun_shadow_after_sync,
)


class UIC1AvailabilityFlowModuleTests(unittest.TestCase):
    def test_template_export_texts(self) -> None:
        self.assertEqual(build_c1_template_export_status_text(12), "C1 阵容模板已导出 | 12 行")
        msg = build_c1_template_export_message_text(12, "E:/APP/ELO/reports/a.csv")
        self.assertIn("行数: 12", msg)
        self.assertIn("a.csv", msg)

    def test_import_and_sync_texts(self) -> None:
        self.assertEqual(
            build_c1_snapshot_import_status_text(30, 18),
            "C1 阵容快照已导入 | 行 30 | 键 18",
        )
        import_msg = build_c1_snapshot_import_message_text(
            {"source": "x.csv", "imported_rows": 30, "written_keys": 18, "snapshot_file": "snap.json"}
        )
        self.assertIn("来源: x.csv", import_msg)
        self.assertIn("写入键数: 18", import_msg)
        self.assertEqual(build_c1_sync_status_text(40, 21), "C1 阵容源已同步 | 行 40 | 键 21")
        sync_msg = build_c1_sync_message_text({"total_rows": 40, "total_keys": 21, "snapshot_file": "snap.json"})
        self.assertIn("导入行数: 40", sync_msg)
        self.assertIn("存储: snap.json", sync_msg)

    def test_should_auto_rerun_rules(self) -> None:
        self.assertTrue(should_auto_rerun_shadow_after_import(has_matches=True, imported_rows=1))
        self.assertFalse(should_auto_rerun_shadow_after_import(has_matches=True, imported_rows=0))
        self.assertFalse(should_auto_rerun_shadow_after_import(has_matches=False, imported_rows=5))
        self.assertTrue(should_auto_rerun_shadow_after_sync(has_matches=True))
        self.assertFalse(should_auto_rerun_shadow_after_sync(has_matches=False))

    def test_release_review_guard_blocks_failed_smoke_check(self) -> None:
        guard = build_c1_release_review_availability_guard(
            {
                "quality_failures": 1,
                "quality_warnings": 2,
                "provider_failure_reasons": ["api-football: suspended"],
                "smoke_check": {
                    "status": "fail",
                    "issues": ["provider quality_gate failed"],
                    "release_review_allowed": False,
                },
            }
        )
        self.assertFalse(guard["allowed"])
        self.assertEqual(guard["status"], "fail")
        self.assertIn("provider quality_gate failed", guard["issues"])
        self.assertIn("api-football: suspended", guard["message"])
        self.assertIn("已跳过", guard["message"])
        self.assertIn("阻止", build_c1_release_review_guard_status_text(guard))
        self.assertIn("fail/warn=1/2", build_c1_release_review_guard_status_text(guard))

    def test_release_guard_block_report_lines(self) -> None:
        generated_at = datetime(2026, 5, 11, 10, 30, 5)
        self.assertEqual(
            build_c1_release_guard_report_filename(generated_at),
            "c1_release_guard_block_20260511_103005.md",
        )
        lines = build_c1_release_guard_report_lines(
            {
                "allowed": False,
                "status": "fail",
                "quality_failures": 1,
                "quality_warnings": 0,
                "status_text": "blocked",
                "issues": ["provider quality_gate failed"],
                "message": "sync again",
            },
            matches_count=12,
            generated_at=generated_at,
        )
        payload = "\n".join(lines)
        self.assertIn("C1 Release Review Guard Block", payload)
        self.assertIn("Matches Requested: 12", payload)
        self.assertIn("Quality Fail/Warn: 1/0", payload)
        self.assertIn("provider quality_gate failed", payload)
        self.assertIn("sync again", payload)

    def test_release_review_guard_allows_warn_or_missing_status(self) -> None:
        warn_guard = build_c1_release_review_availability_guard(
            {
                "quality_failures": 0,
                "quality_warnings": 1,
                "smoke_check": {
                    "status": "warn",
                    "issues": ["availability_known_low"],
                    "release_review_allowed": True,
                },
            }
        )
        self.assertTrue(warn_guard["allowed"])
        self.assertEqual(warn_guard["status"], "warn")
        self.assertIn("可运行", build_c1_release_review_guard_status_text(warn_guard))

        missing_guard = build_c1_release_review_availability_guard({})
        self.assertTrue(missing_guard["allowed"])
        self.assertEqual(missing_guard["status"], "missing")

        pass_guard = build_c1_release_review_availability_guard(
            {"smoke_check": {"status": "pass", "release_review_allowed": True}}
        )
        self.assertEqual(build_c1_release_review_guard_status_text(pass_guard), "放行门控: 通过")

    def test_provider_status_lines(self) -> None:
        lines = build_c1_availability_provider_status_lines(
            [
                {
                    "provider_name": "api-football",
                    "status": "ok",
                    "rows": 123,
                    "source_path": "E:/APP/ELO/data/a.csv",
                },
                {
                    "provider_name": "manual",
                    "status": "missing",
                    "rows": 0,
                    "url": "https://example.com",
                },
            ]
        )
        self.assertEqual(lines[0], "C1 阵容源状态")
        self.assertIn("api-football: ok | rows=123", lines[1])
        self.assertIn("https://example.com", lines[2])

    def test_provider_status_lines_with_sync_summary(self) -> None:
        lines = build_c1_availability_provider_status_lines(
            [
                {
                    "provider_name": "__sync_summary__",
                    "is_sync_summary": True,
                    "last_sync_at": "2026-04-07 14:30:00",
                    "total_rows": 80,
                    "total_keys": 240,
                    "failed_providers": 0,
                },
                {
                    "provider_name": "api_football_primary",
                    "status": "ready",
                    "rows": 80,
                    "url": "https://v3.football.api-sports.io",
                    "resolve_enabled": False,
                    "last_sync_status": "imported",
                    "last_imported_rows": 80,
                    "last_written_keys": 240,
                    "fixture_total": 158,
                    "fixture_issue_count": 92,
                    "fixture_limit": 132,
                    "quality_gate": "warn",
                    "quality_score": 0.73,
                    "keyable_rate": 1.0,
                    "availability_known_rate": 0.2,
                    "quality_issues": ["availability_known_low"],
                    "last_sync_at": "2026-04-07 14:30:00",
                },
            ]
        )
        joined = "\n".join(lines)
        self.assertIn("gate=warn", joined)
        self.assertIn("availability_known_low", joined)
        self.assertIn("最近同步: 2026-04-07 14:30:00", joined)
        self.assertIn("上次同步: status=imported | rows=80 | keys=240", joined)
        self.assertIn("API样本: total=158 | issue=92 | limit=132", joined)


if __name__ == "__main__":
    unittest.main()
