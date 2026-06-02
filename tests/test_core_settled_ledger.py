"""结算账本（settled_ledger）回归测试。

覆盖 TASK 10 的根因：清空 settlements.json 后，被 repair 重建的快照不应被重复结算。
权威幂等来源是 settled_ledger，而非可变且会被裁剪/清空的 settlements 列表。
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app import core
from v24_app.core import AppMatch
from v24_app.storage.state_store import StateStore


class _LedgerStore:
    """轻量内存 StateStore：实现账本契约，模拟 settlements 被清空的场景。"""

    def __init__(self, *, ledger: set[str] | None = None, settlements: list[dict] | None = None) -> None:
        self._ledger: set[str] = set(ledger or set())
        self._settlements: list[dict] = list(settlements or [])
        self.appended: list[dict] = []
        self.popped: list[str] = []

    def load_settlements(self) -> list[dict]:
        return [dict(item) for item in self._settlements]

    def append_settlement(self, record: dict, limit: int = 500) -> None:
        self.appended.append(record)
        self._settlements.append(record)
        mid = str(record.get("match_id") or "")
        if mid:
            self._ledger.add(mid)

    def load_settled_ledger(self) -> set[str]:
        return set(self._ledger)

    def is_settled(self, match_id: str) -> bool:
        return str(match_id or "") in self._ledger

    def mark_settled(self, match_id: str) -> None:
        if match_id:
            self._ledger.add(str(match_id))

    def pop_prediction_snapshot(self, match_id: str) -> dict | None:
        self.popped.append(match_id)
        return {}


class SettledLedgerStateStoreTests(unittest.TestCase):
    """StateStore 账本持久化层的单元测试。"""

    def test_mark_and_query_settled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(Path(tmp))
            self.assertFalse(store.is_settled("m1"))
            store.mark_settled("m1")
            self.assertTrue(store.is_settled("m1"))
            self.assertIn("m1", store.load_settled_ledger())

    def test_mark_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(Path(tmp))
            store.mark_settled("m1")
            store.mark_settled("m1")
            self.assertEqual(store.load_settled_ledger(), {"m1"})

    def test_append_settlement_updates_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(Path(tmp))
            store.append_settlement({"match_id": "m9", "result": "HOME_WIN"})
            self.assertTrue(store.is_settled("m9"))

    def test_ledger_survives_settlements_clear(self) -> None:
        """清空 settlements.json 后账本仍保留，使重复结算可被识别。"""
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(Path(tmp))
            store.append_settlement({"match_id": "m1"})
            # 模拟 settlements 被清空
            store.settlements_file.write_text(
                json.dumps({"items": []}, ensure_ascii=False), encoding="utf-8"
            )
            self.assertEqual(store.load_settlements(), [])
            self.assertTrue(store.is_settled("m1"))


class SettleMatchResultDedupeViaLedgerTests(unittest.TestCase):
    """settle_match_result 在 settlements 被清空但账本仍记录时应跳过重复结算。"""

    def _match(self) -> AppMatch:
        return AppMatch(
            home_team="Alpha FC",
            away_team="Bravo FC",
            league="Friendly League",
            match_time="19:35",
            match_date="2026-05-10",
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.2,
        )

    def test_skips_when_only_ledger_has_match_id(self) -> None:
        match = self._match()
        # settlements 列表为空（已被清空），但账本记录了该比赛
        store = _LedgerStore(ledger={match.match_id}, settlements=[])

        with (
            patch("v24_app.core.STATE_STORE", store),
            patch("v24_app.core.auto_settle_pending_parlays", return_value={"new_settled": 0}) as parlay_mock,
            patch("v24_app.core.enrich_match_from_market_snapshot_store") as enrich_mock,
        ):
            result = core.settle_match_result(match, 1, 0, prediction={"recommendation": "HOME_WIN"})

        self.assertTrue(result["duplicate_skipped"])
        self.assertEqual(result["match_id"], match.match_id)
        self.assertEqual(store.appended, [])  # 未重复结算
        self.assertEqual(store.popped, [match.match_id])  # 快照被清理
        self.assertTrue(parlay_mock.called)
        self.assertFalse(enrich_mock.called)


if __name__ == "__main__":
    unittest.main()
