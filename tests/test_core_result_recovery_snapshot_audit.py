from __future__ import annotations

import sys
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

from v24_app.core import AppMatch, build_result_recovery_snapshot_audit, serialize_match
from v24_app import core


class CoreResultRecoverySnapshotAuditTests(unittest.TestCase):
    def _snapshot(
        self,
        *,
        home: str,
        match_date: str = "2026-05-09",
        source: str = "live:titan",
        source_id: str = "12345",
        with_prediction: bool = True,
    ) -> dict:
        match = AppMatch(
            home_team=home,
            away_team="Bravo FC",
            league="Friendly League",
            match_time="19:35",
            match_date=match_date,
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.2,
            source=source,
            source_id=source_id,
        )
        record = {"match": serialize_match(match)}
        if with_prediction:
            record["prediction"] = {"recommendation": "主胜", "confidence": 0.62}
        return record

    def test_snapshot_audit_classifies_recovery_readiness(self) -> None:
        snapshots = {
            "recoverable": self._snapshot(home="Recoverable FC", source_id="titan_1"),
            "missing_source": self._snapshot(home="Missing FC", source_id=""),
            "cache_schedule": self._snapshot(home="Cache Schedule FC", source="cache", source_id="2784840"),
            "non_titan": self._snapshot(home="Cache FC", source="cache", source_id="cache_1"),
            "old": self._snapshot(home="Old FC", match_date="2026-05-01", source_id="titan_old"),
            "settled": self._snapshot(home="Settled FC", source_id="titan_settled"),
            "no_prediction": self._snapshot(home="No Prediction FC", source_id="titan_np", with_prediction=False),
            "invalid": {"prediction": {"confidence": 0.1}},
        }
        settlements = [{"match_id": "settled"}]

        audit = build_result_recovery_snapshot_audit(
            snapshots,
            settlements,
            lookback_days=2,
            now=datetime(2026, 5, 10, 12, 0, 0),
        )

        self.assertEqual(audit["total_snapshots"], 8)
        self.assertEqual(audit["already_settled"], 1)
        self.assertEqual(audit["pending"], 5)
        self.assertEqual(audit["recoverable_schedule_id"], 3)
        self.assertEqual(audit["recoverable_titan"], 2)
        self.assertEqual(audit["recoverable_cache_source"], 1)
        self.assertEqual(audit["missing_source_id"], 1)
        self.assertEqual(audit["non_titan_source"], 1)
        self.assertEqual(audit["out_of_window"], 1)
        self.assertEqual(audit["invalid"], 1)
        self.assertEqual(audit["missing_prediction"], 1)
        statuses = {item["match_id"]: item["status"] for item in audit["items"]}
        self.assertEqual(statuses["recoverable"], "recoverable_titan")
        self.assertEqual(statuses["cache_schedule"], "recoverable_cache_schedule")
        self.assertEqual(statuses["missing_source"], "missing_source_id")
        self.assertEqual(statuses["non_titan"], "non_titan_source")

    def test_auto_settle_accepts_fourteen_day_lookback(self) -> None:
        with (
            patch("v24_app.core.backfill_analysis_history_from_prediction_snapshots", return_value={}),
            patch("v24_app.core.repair_prediction_snapshots_from_analysis_history", return_value={"restored": 0}),
            patch("v24_app.core.migrate_prediction_snapshots", return_value={}),
            patch("v24_app.core.MatchFetcherTitan", None),
        ):
            result = core.auto_settle_finished_matches(lookback_days=14)

        self.assertEqual(result["lookback_days"], 14)

    def test_snapshot_result_lookup_classifies_misses(self) -> None:
        self.assertEqual(core.classify_snapshot_result_lookup(None)["reason"], "no_result")
        self.assertEqual(
            core.classify_snapshot_result_lookup({"state_code": "-1", "is_finished": False})["reason"],
            "missing_score",
        )
        self.assertEqual(
            core.classify_snapshot_result_lookup(
                {"state_code": "1", "home_goals": 0, "away_goals": 0, "is_finished": False}
            )["reason"],
            "state_not_finished",
        )
        finished = core.classify_snapshot_result_lookup(
            {"state_code": "-1", "home_goals": 2, "away_goals": 1, "is_finished": True}
        )
        self.assertTrue(finished["is_finished"])
        self.assertEqual(finished["reason"], "finished")

    def test_auto_settle_records_snapshot_result_miss_diagnostics(self) -> None:
        class FakeFetcher:
            def __init__(self, debug: bool = False) -> None:
                self.debug = debug

            def get_recent_finished_matches(self, lookback_days: int = 2) -> list:
                return []

            def get_result_by_schedule_id(self, schedule_id: str) -> dict:
                return {
                    "schedule_id": schedule_id,
                    "state_code": "1",
                    "home_goals": 0,
                    "away_goals": 0,
                    "is_finished": False,
                }

        class FakeStateStore:
            def load_settlements(self) -> list:
                return []

            def load_prediction_snapshots(self) -> dict:
                return snapshots

        today = core.datetime.now().strftime("%Y-%m-%d")
        snapshots = {"miss": self._snapshot(home="Miss FC", match_date=today, source_id="titan_miss")}

        with (
            patch("v24_app.core.backfill_analysis_history_from_prediction_snapshots", return_value={}),
            patch("v24_app.core.repair_prediction_snapshots_from_analysis_history", return_value={"restored": 0}),
            patch("v24_app.core.migrate_prediction_snapshots", return_value={}),
            patch("v24_app.core.MatchFetcherTitan", FakeFetcher),
            patch("v24_app.core.STATE_STORE", FakeStateStore()),
            patch("v24_app.core.auto_settle_pending_parlays", return_value={"new_settled": 0, "items": []}),
            patch("v24_app.core.get_gate_metrics", return_value={}),
        ):
            result = core.auto_settle_finished_matches(lookback_days=14)

        self.assertEqual(result["snapshot_checked"], 1)
        self.assertEqual(result["snapshot_result_hits"], 0)
        self.assertEqual(result["snapshot_result_misses"], 1)
        self.assertEqual(result["snapshot_result_miss_reasons"], {"state_not_finished": 1})
        self.assertEqual(result["snapshot_result_miss_items"][0]["schedule_id"], "titan_miss")

    def test_auto_settle_uses_cache_schedule_id_fallback(self) -> None:
        class FakeFetcher:
            def __init__(self, debug: bool = False) -> None:
                self.debug = debug

            def get_recent_finished_matches(self, lookback_days: int = 2) -> list:
                return []

            def get_result_by_schedule_id(self, schedule_id: str) -> dict:
                return {
                    "schedule_id": schedule_id,
                    "state_code": "-1",
                    "home_goals": 2,
                    "away_goals": 0,
                    "is_finished": True,
                }

        class FakeStateStore:
            def load_settlements(self) -> list:
                return []

            def load_prediction_snapshots(self) -> dict:
                return snapshots

        settled: list[tuple[core.AppMatch, int, int, dict | None]] = []

        def fake_settle(match: core.AppMatch, home_goals: int, away_goals: int, prediction: dict | None = None) -> dict:
            settled.append((match, home_goals, away_goals, prediction))
            return {
                "match_id": match.match_id,
                "home_goals": home_goals,
                "away_goals": away_goals,
                "predicted": (prediction or {}).get("recommendation"),
            }

        today = core.datetime.now().strftime("%Y-%m-%d")
        snapshots = {"cache_hit": self._snapshot(home="Cache Hit FC", match_date=today, source="cache", source_id="2784840")}

        with (
            patch("v24_app.core.backfill_analysis_history_from_prediction_snapshots", return_value={}),
            patch("v24_app.core.repair_prediction_snapshots_from_analysis_history", return_value={"restored": 0}),
            patch("v24_app.core.migrate_prediction_snapshots", return_value={}),
            patch("v24_app.core.MatchFetcherTitan", FakeFetcher),
            patch("v24_app.core.STATE_STORE", FakeStateStore()),
            patch("v24_app.core.settle_match_result", side_effect=fake_settle),
            patch("v24_app.core.auto_settle_pending_parlays", return_value={"new_settled": 0, "items": []}),
            patch("v24_app.core.get_gate_metrics", return_value={}),
        ):
            result = core.auto_settle_finished_matches(lookback_days=14)

        self.assertEqual(result["snapshot_recoverable"], 1)
        self.assertEqual(result["snapshot_recoverable_cache_source"], 1)
        self.assertEqual(result["snapshot_non_titan_source"], 0)
        self.assertEqual(result["snapshot_checked"], 1)
        self.assertEqual(result["snapshot_result_hits"], 1)
        self.assertEqual(result["new_settled"], 1)
        self.assertEqual(result["snapshot_predictions"], 1)
        self.assertEqual(settled[0][0].source, "snapshot:cache:analysisheader")
        self.assertEqual(settled[0][0].source_id, "2784840")
        self.assertEqual(settled[0][3], {"recommendation": "主胜", "confidence": 0.62})


if __name__ == "__main__":
    unittest.main()
