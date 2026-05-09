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

from v24_app import core


class _FakeStateStore:
    def __init__(self, snapshots: dict[str, dict] | None = None) -> None:
        self.snapshots = dict(snapshots or {})
        self.history: dict[str, dict] = {}
        self.market: dict[str, dict] = {}

    def load_prediction_snapshots(self) -> dict[str, dict]:
        return dict(self.snapshots)

    def upsert_prediction_snapshot(self, match_id: str, record: dict, limit: int = 3000) -> None:
        self.snapshots[match_id] = record

    def upsert_analysis_history(self, match_id: str, record: dict, limit: int = 5000) -> None:
        self.history[match_id] = record

    def upsert_market_snapshot(self, snapshot_id: str, record: dict, limit: int = 5000) -> None:
        self.market[snapshot_id] = record


class CoreStrategyAllowlistLinkTests(unittest.TestCase):
    def _match(self) -> core.AppMatch:
        return core.AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="19:35",
            match_date="2026-05-09",
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.1,
            source="live:titan",
            source_id="m1",
        )

    def test_mark_strategy_allowlist_snapshots_persists_pending_review_marker(self) -> None:
        match = self._match()
        prediction = {
            "recommendation": "home",
            "confidence": 0.72,
            "risk_level": "LOW",
            "strategy_admission": {
                "decision": "allow",
                "label": "\u6b63\u5f0f\u653e\u884c",
                "active_count": 2,
                "shadow_count": 0,
                "single_play_count": 1,
                "top_play": "market_1x2",
                "top_pick": "home",
                "top_confidence": 0.76,
                "reasons": ["high_accuracy_strategy_active"],
            },
        }
        fake_store = _FakeStateStore()

        with patch("v24_app.core.STATE_STORE", fake_store):
            summary = core.mark_strategy_allowlist_snapshots(
                [(match, prediction)],
                allowlist_file="strategy_allowlist_20260509_173045.md",
                exported_at=datetime(2026, 5, 9, 17, 30, 45),
            )

        self.assertEqual(summary["marked"], 1)
        self.assertIn(match.match_id, fake_store.snapshots)
        marker = fake_store.snapshots[match.match_id]["strategy_allowlist"]
        self.assertEqual(marker["status"], "pending_settlement")
        self.assertEqual(marker["file"], "strategy_allowlist_20260509_173045.md")
        self.assertEqual(fake_store.snapshots[match.match_id]["prediction"]["strategy_allowlist"]["decision"], "allow")
        self.assertEqual(prediction["strategy_allowlist"]["match_id"], match.match_id)
        self.assertIn(match.match_id, fake_store.history)

    def test_persist_prediction_snapshot_preserves_existing_allowlist_marker(self) -> None:
        match = self._match()
        marker = {
            "status": "pending_settlement",
            "decision": "allow",
            "label": "\u6b63\u5f0f\u653e\u884c",
            "file": "strategy_allowlist_20260509_173045.md",
            "exported_at": "2026-05-09 17:30:45",
        }
        fake_store = _FakeStateStore({match.match_id: {"strategy_allowlist": marker}})
        prediction = {"recommendation": "away", "confidence": 0.61}

        with patch("v24_app.core.STATE_STORE", fake_store):
            core.persist_prediction_snapshot(match, prediction)

        stored = fake_store.snapshots[match.match_id]
        self.assertEqual(stored["strategy_allowlist"]["file"], marker["file"])
        self.assertEqual(stored["prediction"]["strategy_allowlist"]["decision"], "allow")
        self.assertEqual(prediction["strategy_allowlist"]["exported_at"], marker["exported_at"])

    def test_strategy_allowlist_settlement_fields_marks_settled_source(self) -> None:
        fields = core._strategy_allowlist_settlement_fields(
            {
                "strategy_allowlist": {
                    "decision": "allow",
                    "label": "\u6b63\u5f0f\u653e\u884c",
                    "file": "strategy_allowlist_20260509_173045.md",
                    "exported_at": "2026-05-09 17:30:45",
                }
            }
        )

        self.assertEqual(fields["strategy_allowlist_status"], "settled")
        self.assertEqual(fields["strategy_allowlist_decision"], "allow")
        self.assertEqual(fields["strategy_allowlist_file"], "strategy_allowlist_20260509_173045.md")

    def test_strategy_admission_gate_respects_manual_policy(self) -> None:
        with patch(
            "v24_app.core._current_strategy_admission_policy",
            return_value={
                "min_confidence": 0.58,
                "block_confidence": 0.40,
                "active_strategy_min": 2,
                "medium_risk_allowed": False,
                "high_risk_allowed": False,
            },
        ):
            admission = core._strategy_admission_gate(
                risk_level="MEDIUM",
                confidence=0.62,
                high_strategy={
                    "enabled": True,
                    "active_matches": [{"play_type": "market_1x2", "pick": "HOME", "confidence": 0.72}],
                    "active_count": 1,
                },
                play_strategy={"single": [{"play_type": "1x2"}]},
            )

        self.assertEqual(admission["decision"], "observe")
        self.assertIn("high_accuracy_strategy_count_below_policy", admission["reasons"])
        self.assertIn("risk_medium_policy_watch", admission["reasons"])
        self.assertEqual(admission["active_strategy_min"], 2)
        self.assertFalse(admission["medium_risk_allowed"])

    def test_apply_strategy_admission_policy_update_writes_local_policy(self) -> None:
        cache_backup = dict(core._STRATEGY_ADMISSION_POLICY_CACHE)
        with tempfile.TemporaryDirectory() as tmp:
            policy_path = Path(tmp) / "strategy_admission_policy_v1.json"
            try:
                core._STRATEGY_ADMISSION_POLICY_CACHE.update({"mtime": object(), "policy": {}, "report": {}})
                with patch("v24_app.core.STRATEGY_ADMISSION_POLICY_FILE", policy_path):
                    status = core.apply_strategy_admission_policy_update(
                        {"min_confidence": 0.59, "active_strategy_min": 2, "medium_risk_allowed": False},
                        source="unit_test",
                    )

                    self.assertTrue(policy_path.exists())
                    policy = status["policy"]
                    self.assertEqual(policy["min_confidence"], 0.59)
                    self.assertEqual(policy["active_strategy_min"], 2)
                    self.assertFalse(policy["medium_risk_allowed"])
                    self.assertEqual(status["reason"], "unit_test")
            finally:
                core._STRATEGY_ADMISSION_POLICY_CACHE.clear()
                core._STRATEGY_ADMISSION_POLICY_CACHE.update(cache_backup)


if __name__ == "__main__":
    unittest.main()
