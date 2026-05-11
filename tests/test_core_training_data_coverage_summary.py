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


class CoreTrainingDataCoverageSummaryTests(unittest.TestCase):
    def test_state_items_summary_is_reused_when_source_signature_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "club_match_history.json").write_text(
                json.dumps(
                    {
                        "updated_at": "2026-05-10 17:00:00",
                        "source": "football-data",
                        "items": [
                            {"match_date": "2024-01-02", "home_team": "A"},
                            {"match_date": "2024-01-01", "home_team": "B"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch("v24_app.core.PROJECT_DIR", root):
                summary = core._load_state_items_summary("club_match_history.json", date_key="match_date")
                with patch("v24_app.core._load_state_payload", side_effect=AssertionError("should use summary")):
                    cached = core._load_state_items_summary("club_match_history.json", date_key="match_date")

        self.assertEqual(summary["item_count"], 2)
        self.assertEqual(summary["date_start"], "2024-01-01")
        self.assertEqual(summary["date_end"], "2024-01-02")
        self.assertEqual(cached["source"], "football-data")

    def test_training_data_coverage_uses_history_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "league_profiles.json").write_text(json.dumps({"leagues": {"A": {}, "B": {}}}), encoding="utf-8")
            (state / "club_match_history.json").write_text(
                json.dumps({"items": [{"match_date": "2024-01-01"}, {"match_date": "2024-01-03"}]}),
                encoding="utf-8",
            )
            (state / "world_cup_history.json").write_text(
                json.dumps({"items": [{"date": "2022-11-20", "year": 2022}, {"date": "2018-07-15", "year": 2018}]}),
                encoding="utf-8",
            )
            (state / "statsbomb_event_summaries.json").write_text(
                json.dumps({"items": [{"match_date": "2020-01-01"}]}),
                encoding="utf-8",
            )
            (state / "statsbomb_review_training_samples.json").write_text(
                json.dumps({"items": [{"id": "r1"}], "summary": {"feature_order": ["a", "b"]}}),
                encoding="utf-8",
            )
            store = core.StateStore(root)
            store.save_xgb_samples([{"features": {"x": 1}, "label": 0, "meta": {"match_date": "2024-01-01", "league": "A"}}])

            with patch("v24_app.core.PROJECT_DIR", root), patch("v24_app.core.STATE_STORE", store):
                status = core.get_training_data_coverage_status()

        self.assertEqual(status["xgb_samples"]["sample_count"], 1)
        self.assertEqual(status["club_history"]["match_count"], 2)
        self.assertEqual(status["club_history"]["date_end"], "2024-01-03")
        self.assertEqual(status["club_history"]["league_profile_count"], 2)
        self.assertEqual(status["world_cup_history"]["year_count"], 2)
        self.assertEqual(status["statsbomb_events"]["review_feature_count"], 2)


if __name__ == "__main__":
    unittest.main()
