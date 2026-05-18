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
    build_auto_settle_popup_message,
    build_auto_settle_status_text,
    should_refresh_after_auto_settle,
)


class UIAutoSettleFlowModuleTests(unittest.TestCase):
    def test_build_auto_settle_status_text(self) -> None:
        text = build_auto_settle_status_text(
            {"lookback_days": 2, "fetched_finished": 15, "new_settled": 4}
        )
        self.assertIn("回看2天", text)
        self.assertIn("完场15", text)
        self.assertIn("新增结算 4", text)

    def test_build_auto_settle_popup_message(self) -> None:
        message = build_auto_settle_popup_message(
            {
                "source": "live:titan",
                "lookback_days": 2,
                "fetched_finished": 15,
                "new_settled": 4,
                "already_settled": 3,
                "skipped": 1,
                "snapshot_checked": 10,
                "snapshot_result_hits": 6,
                "snapshot_result_misses": 4,
                "snapshot_result_miss_reasons": {"no_result": 3, "state_not_finished": 1},
                "snapshot_predictions": 5,
                "analysis_history_backfill": {"snapshot_count": 24, "history_count": 213, "backfilled": 24},
                "analysis_history_trace_fact_ref_backfill": {
                    "checked": 213,
                    "updated": 213,
                    "fact_ref_kinds": {"match_fact": 213, "source_provenance": 213},
                },
                "messages": ["ok1", "ok2"],
            }
        )
        self.assertIn("数据源: live:titan", message)
        self.assertIn("新增结算: 4", message)
        self.assertIn("赛果回查: 检查 10 / 命中 6", message)
        self.assertIn("no_result=3", message)
        self.assertIn("state_not_finished=1", message)
        self.assertIn("历史快照回填", message)
        self.assertIn("历史 Trace 回填", message)
        self.assertIn("updated: 213", message)
        self.assertIn("- ok1", message)

    def test_should_refresh_after_auto_settle(self) -> None:
        self.assertTrue(should_refresh_after_auto_settle(new_settled=1, has_matches=True))
        self.assertFalse(should_refresh_after_auto_settle(new_settled=0, has_matches=True))
        self.assertFalse(should_refresh_after_auto_settle(new_settled=3, has_matches=False))


if __name__ == "__main__":
    unittest.main()
