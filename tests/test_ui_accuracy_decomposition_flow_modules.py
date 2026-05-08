from __future__ import annotations

import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.ui_modules import (
    build_accuracy_decomposition_artifacts,
    build_accuracy_decomposition_csv_text,
    build_accuracy_decomposition_report_lines,
)


class UIAccuracyDecompositionFlowTests(unittest.TestCase):
    def _new_workspace_tempdir(self) -> Path:
        base = PROJECT_ROOT / "data" / "tmp_test_accuracy_decomposition"
        base.mkdir(parents=True, exist_ok=True)
        target = base / f"case_{uuid.uuid4().hex}"
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _prepare_project_root(self, root: Path) -> None:
        (root / "data" / "state").mkdir(parents=True, exist_ok=True)
        (root / "data" / "c1_state").mkdir(parents=True, exist_ok=True)

        market_payload = {
            "items": {
                "source|s1": {
                    "saved_at": "2026-04-07 10:00:00",
                    "match": {"match_id": "m1"},
                }
            }
        }
        (root / "data" / "state" / "market_snapshots.json").write_text(
            json.dumps(market_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        availability_payload = {
            "items": {
                "match|m1": {
                    "saved_at": "2026-04-07 10:05:00",
                    "record": {
                        "match_id": "m1",
                        "match_date": "2026-04-07",
                        "league": "英超",
                        "home_team": "A",
                        "away_team": "B",
                        "home_availability_known": True,
                        "away_availability_known": True,
                        "lineup_freshness_hours": 2.0,
                    },
                }
            }
        }
        (root / "data" / "c1_state" / "availability_snapshots.json").write_text(
            json.dumps(availability_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def test_build_accuracy_decomposition_artifacts(self) -> None:
        root = self._new_workspace_tempdir()
        try:
            self._prepare_project_root(root)
            settlements = [
                {
                    "timestamp": "2026-04-07 22:00:00",
                    "match_id": "m1",
                    "match_date": "2026-04-07",
                    "match_time": "12:00",
                    "league": "英超",
                    "home_team": "A",
                    "away_team": "B",
                    "is_correct": True,
                    "prediction_confidence": 0.70,
                },
                {
                    "timestamp": "2026-04-07 22:05:00",
                    "match_id": "m2",
                    "match_date": "2026-04-07",
                    "match_time": "19:00",
                    "league": "英超",
                    "home_team": "C",
                    "away_team": "D",
                    "is_correct": False,
                    "prediction_confidence": 0.60,
                },
            ]
            parlay_settlements = [
                {
                    "status": "won",
                    "is_hit": True,
                    "expected_hit": 0.25,
                    "settled_at": "2026-04-07 23:00:00",
                }
            ]
            payload = build_accuracy_decomposition_artifacts(
                project_root=root,
                settlements=settlements,
                parlay_settlements=parlay_settlements,
            )
            rows = payload["rows"]
            summary = payload["summary"]
            self.assertEqual(summary["single_settlement_count"], 2)
            self.assertEqual(summary["parlay_settlement_count"], 1)
            self.assertEqual(summary["record_count"], 3)

            play_rows = [row for row in rows if row["dimension"] == "play_type"]
            self.assertTrue(any(row["bucket"] == "胜平负" and row["sample_count"] == 2 for row in play_rows))
            self.assertTrue(any(row["bucket"] == "二串一" and row["sample_count"] == 1 for row in play_rows))

            lead_rows = [row for row in rows if row["dimension"] == "lead_time"]
            self.assertTrue(any(row["bucket"] == "T-1~3h" and row["sample_count"] == 1 for row in lead_rows))
            self.assertTrue(any(row["bucket"] == "unknown" and row["sample_count"] == 1 for row in lead_rows))

            lineup_rows = [row for row in rows if row["dimension"] == "lineup"]
            self.assertTrue(any(row["bucket"] == "known_fresh" and row["sample_count"] == 1 for row in lineup_rows))
            self.assertTrue(any(row["bucket"] == "unknown" and row["sample_count"] == 1 for row in lineup_rows))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_report_and_csv_text(self) -> None:
        rows = [
            {
                "dimension": "play_type",
                "dimension_label": "玩法",
                "bucket": "胜平负",
                "sample_count": 10,
                "hit_count": 6,
                "hit_rate": 0.6,
                "expected_count": 10,
                "expected_hit_rate": 0.55,
                "ev_bias": 0.05,
                "brier": 0.2,
                "logloss": 0.61,
                "losing_streak": 0,
            }
        ]
        summary = {"single_settlement_count": 10, "parlay_settlement_count": 0, "record_count": 10}
        lines = build_accuracy_decomposition_report_lines(rows, summary)
        text = "\n".join(lines)
        self.assertIn("Accuracy Decomposition Report", text)
        self.assertIn("## 玩法", text)
        self.assertIn("胜平负", text)

        csv_text = build_accuracy_decomposition_csv_text(rows)
        self.assertIn("dimension,dimension_label,bucket", csv_text)
        self.assertIn("play_type,玩法,胜平负", csv_text)


if __name__ == "__main__":
    unittest.main()
