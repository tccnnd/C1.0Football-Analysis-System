from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.training_samples import build_xgb_samples_from_historical_records, import_historical_xgb_samples


def _record(match_id: str, source: str = "jc_results_csv") -> dict:
    return {
        "match_id": match_id,
        "source": source,
        "match_date": "2026-05-01",
        "match_time": "19:30",
        "league": "英超",
        "home_team": f"主队{match_id}",
        "away_team": f"客队{match_id}",
        "home_goals": 2,
        "away_goals": 1,
        "odds_home": 1.8,
        "odds_draw": 3.4,
        "odds_away": 4.1,
        "opening_odds_home": 1.9,
        "opening_odds_draw": 3.3,
        "opening_odds_away": 3.8,
    }


class TrainingSamplesHistoryImportTests(unittest.TestCase):
    def test_preserves_source_in_sample_meta(self) -> None:
        samples, _, summary = build_xgb_samples_from_historical_records([_record("m1")])

        self.assertEqual(summary["imported_samples"], 1)
        self.assertEqual(samples[0]["meta"]["source"], "jc_results_csv")

    def test_import_reports_saved_total_and_storage_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "history.jsonl"
            input_path.write_text(
                "\n".join(json.dumps(_record(f"m{index}"), ensure_ascii=False) for index in range(2)),
                encoding="utf-8",
            )

            result = import_historical_xgb_samples(
                project_dir=temp_path,
                input_path=input_path,
                replace=True,
                sync_ratings=False,
            )

            self.assertEqual(result["merged_total"], 2)
            self.assertEqual(result["saved_total"], 2)
            self.assertEqual(result["storage_limit"], 50000)
            self.assertEqual(result["dropped_by_limit"], 0)


if __name__ == "__main__":
    unittest.main()
