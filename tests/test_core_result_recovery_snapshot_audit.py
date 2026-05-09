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

from v24_app.core import AppMatch, build_result_recovery_snapshot_audit, serialize_match


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

        self.assertEqual(audit["total_snapshots"], 7)
        self.assertEqual(audit["already_settled"], 1)
        self.assertEqual(audit["pending"], 4)
        self.assertEqual(audit["recoverable_titan"], 2)
        self.assertEqual(audit["missing_source_id"], 1)
        self.assertEqual(audit["non_titan_source"], 1)
        self.assertEqual(audit["out_of_window"], 1)
        self.assertEqual(audit["invalid"], 1)
        self.assertEqual(audit["missing_prediction"], 1)
        statuses = {item["match_id"]: item["status"] for item in audit["items"]}
        self.assertEqual(statuses["recoverable"], "recoverable_titan")
        self.assertEqual(statuses["missing_source"], "missing_source_id")
        self.assertEqual(statuses["non_titan"], "non_titan_source")


if __name__ == "__main__":
    unittest.main()
