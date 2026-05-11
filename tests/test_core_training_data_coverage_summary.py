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


def _xgb_sample(index: int, *, with_features: bool = True) -> dict:
    labels = [0, 1, 2]
    leagues = ["A", "B", "C", "D", "E"]
    item = {
        "label": labels[index % len(labels)],
        "meta": {
            "match_date": f"2024-02-{(index % 28) + 1:02d}",
            "league": leagues[index % len(leagues)],
            "source": "unit_history",
        },
    }
    if with_features:
        item["features"] = {"market_home": 0.4, "elo_diff": float(index % 20)}
    return item


def _write_history_payload(path: Path, count: int) -> None:
    path.write_text(
        json.dumps({"items": [{"match_date": f"2023-01-{(index % 28) + 1:02d}"} for index in range(count)]}),
        encoding="utf-8",
    )


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

    def test_training_health_is_healthy_when_thresholds_are_met(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "league_profiles.json").write_text(json.dumps({"leagues": {"A": {}, "B": {}, "C": {}, "D": {}, "E": {}}}), encoding="utf-8")
            _write_history_payload(state / "club_match_history.json", 100)
            store = core.StateStore(root)
            store.save_xgb_samples([_xgb_sample(index) for index in range(300)])

            with patch("v24_app.core.PROJECT_DIR", root), patch("v24_app.core.STATE_STORE", store):
                status = core.get_training_data_coverage_status()

        health = status["training_health"]
        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["issue_count"], 0)
        self.assertEqual(health["xgb_trainability"]["valid_feature_ratio"], 1.0)
        self.assertEqual(health["xgb_trainability"]["label_class_count"], 3)

    def test_training_health_blocks_when_xgb_samples_are_not_trainable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            store = core.StateStore(root)
            store.save_xgb_samples([_xgb_sample(0)])

            with patch("v24_app.core.PROJECT_DIR", root), patch("v24_app.core.STATE_STORE", store):
                status = core.get_training_data_coverage_status()

        health = status["training_health"]
        codes = {issue["code"] for issue in health["issues"]}
        self.assertEqual(health["status"], "blocked")
        self.assertIn("xgb_sample_count_low", codes)
        self.assertIn("xgb_valid_feature_count_low", codes)

    def test_training_health_warns_for_quality_and_coverage_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "league_profiles.json").write_text(json.dumps({"leagues": {}}), encoding="utf-8")
            _write_history_payload(state / "club_match_history.json", 100)
            (state / "statsbomb_event_summaries.json").write_text(
                json.dumps({"items": [{"match_date": "2020-01-01"}]}),
                encoding="utf-8",
            )
            store = core.StateStore(root)
            samples = []
            for index in range(350):
                sample = _xgb_sample(index, with_features=index < 320)
                sample["label"] = 0 if index < 315 else 1 if index < 345 else 2
                sample["meta"]["league"] = "A"
                samples.append(sample)
            store.save_xgb_samples(samples)

            with patch("v24_app.core.PROJECT_DIR", root), patch("v24_app.core.STATE_STORE", store):
                status = core.get_training_data_coverage_status()

        health = status["training_health"]
        codes = {issue["code"] for issue in health["issues"]}
        self.assertEqual(health["status"], "attention")
        self.assertIn("xgb_valid_feature_ratio_low", codes)
        self.assertIn("xgb_class_balance_low", codes)
        self.assertIn("xgb_league_coverage_low", codes)
        self.assertIn("league_profiles_missing", codes)
        self.assertIn("statsbomb_review_samples_missing", codes)

    def test_training_health_warns_when_sample_date_range_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "league_profiles.json").write_text(json.dumps({"leagues": {"A": {}, "B": {}, "C": {}, "D": {}, "E": {}}}), encoding="utf-8")
            _write_history_payload(state / "club_match_history.json", 100)
            store = core.StateStore(root)
            samples = []
            for index in range(300):
                sample = _xgb_sample(index)
                sample["meta"].pop("match_date", None)
                samples.append(sample)
            store.save_xgb_samples(samples)

            with patch("v24_app.core.PROJECT_DIR", root), patch("v24_app.core.STATE_STORE", store):
                status = core.get_training_data_coverage_status()

        health = status["training_health"]
        codes = {issue["code"] for issue in health["issues"]}
        self.assertEqual(health["status"], "attention")
        self.assertIn("xgb_date_range_missing", codes)


if __name__ == "__main__":
    unittest.main()
