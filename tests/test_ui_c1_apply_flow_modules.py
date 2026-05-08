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
from v24_app.ui_modules import resolve_selected_prediction_for_details, sync_tree_c1_action_column


class _FakeTree:
    def __init__(self) -> None:
        self._rows: dict[str, tuple] = {}

    def exists(self, item_id: str) -> bool:
        return item_id in self._rows

    def item(self, item_id: str, key: str | None = None, **kwargs):
        if kwargs:
            values = kwargs.get("values")
            if values is not None:
                self._rows[item_id] = tuple(values)
            return None
        if key == "values":
            return self._rows.get(item_id, ())
        return {}


class UIC1ApplyFlowModuleTests(unittest.TestCase):
    def test_sync_tree_c1_action_column(self) -> None:
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
        tree = _FakeTree()
        tree._rows[match_a.match_id] = ("d", "t", "l", "h", "a", "pick", "-", "0.50")
        tree._rows[match_b.match_id] = ("d", "t", "l", "h", "a", "pick", "-", "0.55")
        updated = sync_tree_c1_action_column(
            tree=tree,
            matches=[match_a, match_b],
            action_text_by_match_id=lambda mid: "可放行" if mid == match_a.match_id else "阻断",
        )
        self.assertEqual(updated, 2)
        self.assertEqual(tree._rows[match_a.match_id][6], "可放行")
        self.assertEqual(tree._rows[match_b.match_id][6], "阻断")

    def test_resolve_selected_prediction_for_details(self) -> None:
        match = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="19:35",
            match_date="2026-04-04",
            odds_home=1.8,
            odds_draw=3.2,
            odds_away=4.0,
        )
        self.assertIsNone(
            resolve_selected_prediction_for_details(selected_match=None, predictions={})
        )
        self.assertIsNone(
            resolve_selected_prediction_for_details(
                selected_match=match,
                predictions={match.match_id: "invalid"},
            )
        )
        payload = resolve_selected_prediction_for_details(
            selected_match=match,
            predictions={match.match_id: {"recommendation": "主胜"}},
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        selected, prediction = payload
        self.assertEqual(selected.match_id, match.match_id)
        self.assertEqual(prediction["recommendation"], "主胜")


if __name__ == "__main__":
    unittest.main()
