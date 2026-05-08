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
    C1_TREE_TAG_STYLES,
    build_c1_apply_dialog_text,
    build_c1_apply_status_text,
    configure_c1_tree_tags,
    replace_tree_action_value,
)


class _FakeTree:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def tag_configure(self, tag: str, **kwargs) -> None:
        self.calls.append((tag, str(kwargs.get("background"))))


class UIMainListSyncModuleTests(unittest.TestCase):
    def test_configure_tree_tags(self) -> None:
        tree = _FakeTree()
        configure_c1_tree_tags(tree)
        self.assertEqual(len(tree.calls), len(C1_TREE_TAG_STYLES))
        for tag, color in tree.calls:
            self.assertEqual(color, C1_TREE_TAG_STYLES[tag])

    def test_build_apply_texts(self) -> None:
        buckets = {"可放行": 3, "待处理": 2, "观察": 1, "阻断": 4}
        status = build_c1_apply_status_text(applied=10, buckets=buckets)
        dialog = build_c1_apply_dialog_text(applied=10, buckets=buckets)
        self.assertIn("共 10 场", status)
        self.assertIn("放行 3", status)
        self.assertIn("已应用 10 场", dialog)
        self.assertIn("阻断: 4", dialog)

    def test_replace_tree_action_value(self) -> None:
        self.assertIsNone(replace_tree_action_value("invalid", "可放行"))
        self.assertIsNone(replace_tree_action_value(("a", "b"), "可放行"))
        updated = replace_tree_action_value(
            ("date", "time", "league", "home", "away", "pick", "-", "conf"),
            "阻断",
        )
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(updated[6], "阻断")


if __name__ == "__main__":
    unittest.main()
