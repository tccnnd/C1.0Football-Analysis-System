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

from v24_app.ui_modules import SPECIAL_WORKBENCH_LAYOUT, build_special_workbench_sections


class UISpecialWorkbenchFlowTests(unittest.TestCase):
    def test_build_special_workbench_sections_binds_grouped_actions(self) -> None:
        calls: list[str] = []
        action_keys = [
            entry["action_key"]
            for _section_title, entries in SPECIAL_WORKBENCH_LAYOUT
            for entry in entries
        ]
        actions = {key: (lambda key=key: calls.append(key)) for key in action_keys}

        sections = build_special_workbench_sections(actions)

        self.assertEqual([section[0] for section in sections], ["复盘闭环", "策略与接管", "数据与运行"])
        self.assertGreaterEqual(len(sections[0][1]), 5)
        self.assertIn("open_ai_video_review_center_window", action_keys)
        self.assertIn("open_play_model_takeover_gate_audit_history", action_keys)
        self.assertIn("open_data_center", action_keys)

        first_command = sections[0][1][0]["command"]
        self.assertTrue(callable(first_command))
        first_command()
        self.assertEqual(calls, [sections[0][1][0]["action_key"]])

    def test_build_special_workbench_sections_reports_missing_actions(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Missing special workbench action"):
            build_special_workbench_sections({})


if __name__ == "__main__":
    unittest.main()
