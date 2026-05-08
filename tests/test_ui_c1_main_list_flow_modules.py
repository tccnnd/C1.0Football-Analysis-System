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

from v24_app.core import AppMatch
from v24_app.ui_modules import (
    build_c1_mode_status_text,
    build_main_list_sort_key,
    compute_c1_action_counts,
    restore_c1_marks_for_matches,
    should_show_match_for_filter,
)


class _FakeTree:
    def __init__(self) -> None:
        self._rows: dict[str, tuple] = {}
        self.tags: dict[str, tuple] = {}
        self.tag_styles: dict[str, str] = {}

    def exists(self, item_id: str) -> bool:
        return item_id in self._rows

    def item(self, item_id: str, key: str | None = None, **kwargs):
        if kwargs:
            if "values" in kwargs:
                self._rows[item_id] = tuple(kwargs["values"])
            if "tags" in kwargs:
                self.tags[item_id] = tuple(kwargs["tags"])
            return None
        if key == "values":
            return self._rows.get(item_id, ())
        return {}

    def tag_configure(self, tag: str, **kwargs) -> None:
        self.tag_styles[tag] = str(kwargs.get("background"))


class UIC1MainListFlowModuleTests(unittest.TestCase):
    def test_should_show_match_for_filter(self) -> None:
        self.assertTrue(should_show_match_for_filter(selected_filter="全部", action="观察", release_allowed=False))
        self.assertTrue(should_show_match_for_filter(selected_filter="正式建议", action="观察", release_allowed=True))
        self.assertFalse(should_show_match_for_filter(selected_filter="正式建议", action="观察", release_allowed=False))
        self.assertTrue(should_show_match_for_filter(selected_filter="待处理", action="补阵容", release_allowed=False))
        self.assertFalse(should_show_match_for_filter(selected_filter="待处理", action="观察", release_allowed=False))
        self.assertTrue(should_show_match_for_filter(selected_filter="阻断", action="阻断", release_allowed=False))

    def test_sort_key_and_counts_and_mode_text(self) -> None:
        match = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="19:35",
            match_date="2026-04-04",
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.1,
        )
        key = build_main_list_sort_key(
            selected_filter="全部",
            action="观察",
            release_confidence=0.7,
            match=match,
            action_priority_fn=lambda action: {"观察": 4}.get(action, 9),
        )
        self.assertEqual(key[0], 4)
        self.assertEqual(key[1], -0.7)

        counts, pending, formal, total = compute_c1_action_counts(
            matches=[match],
            action_text_by_match_id=lambda _id: "观察",
            release_allowed_ids={match.match_id},
        )
        self.assertEqual(total, 1)
        self.assertEqual(formal, 1)
        self.assertEqual(pending, 0)
        self.assertEqual(counts["观察"], 1)
        self.assertIn("生效放行 2 场", build_c1_mode_status_text(runtime_mode="gate_only", active_allowed_count=2, release_allowed_count=3))
        self.assertIn("仅影子评估 3 场", build_c1_mode_status_text(runtime_mode="shadow", active_allowed_count=2, release_allowed_count=3))

    def test_restore_c1_marks_for_matches(self) -> None:
        match = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="19:35",
            match_date="2026-04-04",
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.1,
        )
        tree = _FakeTree()
        tree._rows[match.match_id] = ("d", "t", "l", "h", "a", "pick", "-", "conf")
        restored = restore_c1_marks_for_matches(
            tree=tree,
            matches=[match],
            c1_comparison_marks={match.match_id: {"suggested_action": "补阵容"}},
            action_text_by_match_id=lambda _id: "补阵容",
        )
        self.assertEqual(restored, 1)
        self.assertEqual(tree.tags[match.match_id], ("c1_pending",))
        self.assertEqual(tree._rows[match.match_id][6], "补阵容")


if __name__ == "__main__":
    unittest.main()
