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
        json.dumps(
            {
                "source": "unit_history",
                "items": [{"match_date": f"2023-01-{(index % 28) + 1:02d}"} for index in range(count)],
            }
        ),
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
        self.assertEqual(status["fact_coverage"]["match_fact"]["available_count"], 5)
        self.assertEqual(status["fact_coverage"]["match_fact"]["target_count"], 5)
        self.assertEqual(status["training_health"]["fact_readiness"]["match_fact_available_count"], 5)

    def test_training_data_coverage_includes_statsbomb_audit(self) -> None:
        settlements = [
            {
                "match_id": "m1",
                "match_date": "2024-04-14",
                "league": "1. Bundesliga",
                "home_team": "Bayer Leverkusen",
                "away_team": "Werder Bremen",
            },
            {
                "match_id": "m2",
                "match_date": "2024-04-14",
                "league": "1. Bundesliga",
                "home_team": "Leverkusen",
                "away_team": "Bremen",
            },
            {
                "match_id": "m3",
                "match_date": "2024-05-01",
                "league": "Other",
                "home_team": "A",
                "away_team": "B",
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "statsbomb_event_summaries.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "source_match_id": "m1",
                                "match_date": "2024-04-14",
                                "league": "1. Bundesliga",
                                "home_team": "Bayer Leverkusen",
                                "away_team": "Werder Bremen",
                            },
                            {
                                "source_match_id": "m9",
                                "match_date": "2024-04-14",
                                "league": "1. Bundesliga",
                                "home_team": "Bayer Leverkusen",
                                "away_team": "Bremen",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (state / "statsbomb_review_training_samples.json").write_text(json.dumps({"items": [], "summary": {}}), encoding="utf-8")
            store = core.StateStore(root)

            with (
                patch("v24_app.core.PROJECT_DIR", root),
                patch("v24_app.core.STATE_STORE", store),
                patch("v24_app.core.get_recent_settlements", return_value=settlements),
            ):
                status = core.get_training_data_coverage_status()

        audit = status["statsbomb_events"]["coverage_audit"]
        self.assertEqual(status["statsbomb_events"]["coverage_gap_count"], 2)
        self.assertEqual(status["statsbomb_events"]["coverage_candidate_count"], 2)
        self.assertEqual(audit["settlement_count"], 3)
        self.assertEqual(audit["exact_match_count"], 1)
        self.assertEqual(audit["candidate_count"], 2)
        self.assertEqual(audit["no_same_date_count"], 1)
        self.assertEqual(audit["same_date_unmatched_count"], 1)

    def test_statsbomb_coverage_matches_known_aliases_with_adjacent_dates(self) -> None:
        settlements = [
            {
                "match_id": "cn-euro-1",
                "match_date": "2024-06-16",
                "league": "欧洲杯",
                "home_team": "西班牙",
                "away_team": "克罗地亚",
            }
        ]
        statsbomb_items = [
            {
                "source_match_id": "sb-euro-1",
                "match_date": "2024-06-15",
                "league": "UEFA Euro",
                "home_team": "Spain",
                "away_team": "Croatia",
            }
        ]

        audit = core._build_statsbomb_coverage_audit(settlements, statsbomb_items)
        index = {}
        for item in statsbomb_items:
            for key in core._statsbomb_coverage_audit_exact_keys(item):
                index[key] = item

        self.assertEqual(audit["exact_match_count"], 1)
        self.assertEqual(audit["coverage_gap_count"], 0)
        self.assertEqual(
            core._match_statsbomb_event_summary(settlements[0], index)["source_match_id"],
            "sb-euro-1",
        )

    def test_training_data_coverage_flags_no_date_overlap(self) -> None:
        settlements = [
            {
                "match_id": "m1",
                "match_date": "2024-04-14",
                "league": "1. Bundesliga",
                "home_team": "Bayer Leverkusen",
                "away_team": "Werder Bremen",
            },
            {
                "match_id": "m2",
                "match_date": "2024-04-15",
                "league": "1. Bundesliga",
                "home_team": "Borussia Dortmund",
                "away_team": "Bayern Munich",
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "league_profiles.json").write_text(json.dumps({"leagues": {"A": {}, "B": {}, "C": {}, "D": {}, "E": {}}}), encoding="utf-8")
            _write_history_payload(state / "club_match_history.json", 100)
            (state / "statsbomb_event_summaries.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "source_match_id": "s1",
                                "match_date": "2024-03-10",
                                "league": "1. Bundesliga",
                                "home_team": "Bayer Leverkusen",
                                "away_team": "Werder Bremen",
                            },
                            {
                                "source_match_id": "s2",
                                "match_date": "2024-03-11",
                                "league": "1. Bundesliga",
                                "home_team": "Borussia Dortmund",
                                "away_team": "Bayern Munich",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (state / "statsbomb_review_training_samples.json").write_text(json.dumps({"items": [], "summary": {}}), encoding="utf-8")
            store = core.StateStore(root)
            store.save_xgb_samples([_xgb_sample(index) for index in range(300)])

            with (
                patch("v24_app.core.PROJECT_DIR", root),
                patch("v24_app.core.STATE_STORE", store),
                patch("v24_app.core.get_recent_settlements", return_value=settlements),
            ):
                status = core.get_training_data_coverage_status()

        audit = status["statsbomb_events"]["coverage_audit"]
        health = status["training_health"]
        codes = {issue["code"] for issue in health["issues"]}
        self.assertEqual(audit["coverage_blocker"], "no_date_overlap")
        self.assertEqual(audit["date_overlap_count"], 0)
        self.assertEqual(audit["date_overlap_ratio"], 0.0)
        self.assertEqual(audit["settlement_date_start"], "2024-04-14")
        self.assertEqual(audit["settlement_date_end"], "2024-04-15")
        self.assertEqual(audit["statsbomb_date_start"], "2024-03-10")
        self.assertEqual(audit["statsbomb_date_end"], "2024-03-11")
        plan = status["statsbomb_events"]["coverage_import_plan"]
        self.assertEqual(plan["status"], "blocked")
        self.assertEqual(plan["action_key"], "import_statsbomb_for_settlement_date_range")
        self.assertEqual(plan["target_date_start"], "2024-04-14")
        self.assertEqual(plan["target_date_end"], "2024-04-15")
        self.assertEqual(plan["source_date_start"], "2024-03-10")
        self.assertEqual(plan["source_date_end"], "2024-03-11")
        fallback = plan["no_overlap_fallback"]
        self.assertEqual(fallback["reason"], "no_date_overlap")
        self.assertFalse(fallback["can_build_current_review_samples"])
        self.assertEqual(fallback["safe_use"], "historical_event_review_memory_only")
        self.assertEqual(fallback["actions"][0]["action_key"], "import_aligned_historical_settlements")
        self.assertIn("statsbomb_date_overlap_missing", codes)

    def test_training_health_is_healthy_when_thresholds_are_met(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "league_profiles.json").write_text(json.dumps({"leagues": {"A": {}, "B": {}, "C": {}, "D": {}, "E": {}}}), encoding="utf-8")
            _write_history_payload(state / "club_match_history.json", 300)
            store = core.StateStore(root)
            store.save_xgb_samples([_xgb_sample(index) for index in range(300)])

            with patch("v24_app.core.PROJECT_DIR", root), patch("v24_app.core.STATE_STORE", store):
                status = core.get_training_data_coverage_status()

        health = status["training_health"]
        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["issue_count"], 0)
        self.assertEqual(health["xgb_trainability"]["valid_feature_ratio"], 1.0)
        self.assertEqual(health["xgb_trainability"]["label_class_count"], 3)
        self.assertEqual(health["fact_readiness"]["match_fact_coverage_ratio"], 1.0)

    def test_training_health_warns_for_fact_layer_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "league_profiles.json").write_text(json.dumps({"leagues": {"A": {}, "B": {}, "C": {}, "D": {}, "E": {}}}), encoding="utf-8")
            store = core.StateStore(root)
            store.save_xgb_samples([_xgb_sample(index) for index in range(300)])

            with patch("v24_app.core.PROJECT_DIR", root), patch("v24_app.core.STATE_STORE", store):
                status = core.get_training_data_coverage_status()

        health = status["training_health"]
        codes = {issue["code"] for issue in health["issues"]}
        self.assertEqual(health["status"], "attention")
        self.assertIn("fact_match_coverage_low", codes)
        self.assertEqual(health["fact_readiness"]["match_fact_available_count"], 0)
        self.assertEqual(health["fact_readiness"]["match_fact_target_count"], 300)

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

    def test_rebuild_league_profiles_from_club_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "club_match_history.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {"match_date": "2024-01-01", "league": "A", "home_goals": 2, "away_goals": 1},
                            {"match_date": "2024-01-02", "league": "A", "home_goals": 0, "away_goals": 0},
                            {"match_date": "2024-01-03", "league": "B", "home_goals": 1, "away_goals": 3},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch("v24_app.core.PROJECT_DIR", root):
                result = core.rebuild_league_profiles_from_club_history()

            payload = json.loads((state / "league_profiles.json").read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["league_profile_count"], 2)
        self.assertEqual(payload["leagues"]["A"]["matches"], 2)
        self.assertEqual(payload["leagues"]["B"]["away_win_rate"], "100.0%")

    def test_repair_training_data_health_builds_statsbomb_review_samples(self) -> None:
        settlement = {
            "match_id": "m1",
            "match_date": "2024-04-14",
            "match_time": "17:30",
            "league": "1. Bundesliga",
            "home_team": "Bayer Leverkusen",
            "away_team": "Werder Bremen",
            "home_goals": 5,
            "away_goals": 0,
            "is_correct": False,
            "handicap_is_correct": True,
            "ou_is_correct": False,
            "statsbomb_event_summary": {
                "event_count": 10,
                "team_stats": {
                    "Bayer Leverkusen": {"xg": 2.1, "shots": 12},
                    "Werder Bremen": {"xg": 0.5, "shots": 5},
                },
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = core.StateStore(root)
            with (
                patch("v24_app.core.PROJECT_DIR", root),
                patch("v24_app.core.STATE_STORE", store),
                patch("v24_app.core.get_recent_settlements", return_value=[settlement]),
            ):
                result = core.repair_training_data_health("build_statsbomb_review_samples")

            payload = json.loads((root / "data" / "state" / "statsbomb_review_training_samples.json").read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["action_key"], "build_statsbomb_review_samples")
        self.assertEqual(payload["summary"]["sample_count"], 1)
        self.assertEqual(result["result"]["sample_count"], 1)
        self.assertEqual(result["generated_sample_count"], 1)
        self.assertEqual(result["skipped_reasons"], {"missing_statsbomb": 0, "unknown_label": 0})
        self.assertTrue(result["output_path"].endswith("statsbomb_review_training_samples.json"))
        self.assertIn("after_status", result)
        self.assertIn("training_gate", result)

    def test_repair_training_data_health_builds_statsbomb_coverage_import_plan(self) -> None:
        settlements = [
            {
                "match_id": "m1",
                "match_date": "2024-04-14",
                "league": "1. Bundesliga",
                "home_team": "Bayer Leverkusen",
                "away_team": "Werder Bremen",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "statsbomb_event_summaries.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "source_match_id": "s1",
                                "match_date": "2024-03-10",
                                "league": "1. Bundesliga",
                                "home_team": "Bayer Leverkusen",
                                "away_team": "Werder Bremen",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            store = core.StateStore(root)

            with (
                patch("v24_app.core.PROJECT_DIR", root),
                patch("v24_app.core.STATE_STORE", store),
                patch("v24_app.core.get_recent_settlements", return_value=settlements),
            ):
                result = core.repair_training_data_health("build_statsbomb_coverage_import_plan")

            payload = json.loads((root / "data" / "state" / "statsbomb_coverage_import_plan.json").read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["action_key"], "build_statsbomb_coverage_import_plan")
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["action_key"], "import_statsbomb_for_settlement_date_range")
        self.assertTrue(result["output_path"].endswith("statsbomb_coverage_import_plan.json"))
        self.assertEqual(result["result"]["target_date_start"], "2024-04-14")
        self.assertEqual(result["result"]["source_date_start"], "2024-03-10")
        self.assertIn("next_step", result["result"])

    def test_repair_training_data_health_executes_statsbomb_coverage_import_plan(self) -> None:
        settlement = {
            "match_id": "m1",
            "match_date": "2024-04-14",
            "match_time": "17:30",
            "league": "1. Bundesliga",
            "home_team": "Bayer Leverkusen",
            "away_team": "Werder Bremen",
            "home_goals": 5,
            "away_goals": 0,
            "is_correct": False,
            "handicap_is_correct": True,
            "ou_is_correct": False,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "settlements.json").write_text(json.dumps({"items": [settlement]}), encoding="utf-8")
            (state / "statsbomb_coverage_import_plan.json").write_text(
                json.dumps(
                    {
                        "status": "blocked",
                        "coverage_blocker": "no_date_overlap",
                        "plan_source": "saved",
                        "plan_path": str(state / "statsbomb_coverage_import_plan.json"),
                        "target_date_start": "2024-04-14",
                        "target_date_end": "2024-04-15",
                        "settlement_date_start": "2024-04-14",
                        "settlement_date_end": "2024-04-15",
                        "next_step": "Import StatsBomb coverage for the settlement date range, then rebuild review samples.",
                        "overlap_competition_count": 1,
                        "top_overlap_competitions": [
                            {
                                "competition_id": 1,
                                "season_id": 10,
                                "competition_name": "Overlap League",
                                "season_name": "2024",
                                "match_count": 1,
                                "overlap_settlement_count": 1,
                                "date_start": "2024-04-14",
                                "date_end": "2024-04-15",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            store = core.StateStore(root)

            def _fake_import_statsbomb_open_data(**kwargs):
                state_dir = Path(kwargs["project_root"]) / "data" / "state"
                summary_path = state_dir / "statsbomb_event_summaries.json"
                summary_path.write_text(
                    json.dumps(
                        {
                            "items": [
                                {
                                    "source_match_id": "s1",
                                    "match_id": "s1",
                                    "match_date": "2024-04-14",
                                    "league": "1. Bundesliga",
                                    "home_team": "Bayer Leverkusen",
                                    "away_team": "Werder Bremen",
                                    "source_url": "https://example.com/statsbomb/s1",
                                    "event_summary": {
                                        "event_count": 10,
                                        "shot_count": 12,
                                        "xg_home": 2.1,
                                        "xg_away": 0.5,
                                    },
                                }
                            ]
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                return {
                    "records": 1,
                    "output_records": 1,
                    "failure_count": 0,
                    "skipped_existing": 0,
                    "summaries_path": str(summary_path),
                    "audit_path": str(state_dir / "statsbomb_import_audit.json"),
                }

            with (
                patch("v24_app.core.PROJECT_DIR", root),
                patch("v24_app.core.STATE_STORE", store),
                patch("v24_app.core.STATSBOMB_EVENT_SUMMARIES_FILE", state / "statsbomb_event_summaries.json"),
                patch("v24_app.core.STATSBOMB_REVIEW_TRAINING_FILE", state / "statsbomb_review_training_samples.json"),
                patch("v24_app.core.import_statsbomb_open_data", side_effect=_fake_import_statsbomb_open_data) as importer,
            ):
                result = core.repair_training_data_health("execute_statsbomb_coverage_import_plan")

            payload = json.loads((root / "data" / "state" / "statsbomb_review_training_samples.json").read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["action_key"], "execute_statsbomb_coverage_import_plan")
        self.assertEqual(result["result"]["plan_source"], "saved")
        self.assertEqual(result["result"]["imported_records"], 1)
        self.assertEqual(result["result"]["sample_count"], 1)
        self.assertEqual(result["generated_sample_count"], 1)
        self.assertEqual(result["result"]["skipped_missing_statsbomb"], 0)
        self.assertEqual(result["result"]["skipped_unknown_label"], 0)
        self.assertTrue(result["output_path"].endswith("statsbomb_review_training_samples.json"))
        self.assertEqual(payload["summary"]["sample_count"], 1)
        self.assertEqual(payload["items"][0]["match_id"], "m1")
        importer.assert_called_once()

    def test_repair_training_data_health_executes_statsbomb_coverage_import_plan_no_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "settlements.json").write_text(json.dumps({"items": [{"match_date": "2026-04-14"}]}), encoding="utf-8")
            (state / "statsbomb_coverage_import_plan.json").write_text(
                json.dumps(
                    {
                        "status": "blocked",
                        "coverage_blocker": "no_date_overlap",
                        "plan_path": str(state / "statsbomb_coverage_import_plan.json"),
                        "target_date_start": "2026-04-14",
                        "target_date_end": "2026-04-15",
                        "settlement_date_start": "2026-04-14",
                        "settlement_date_end": "2026-04-15",
                        "next_step": "No overlap available.",
                        "overlap_competition_count": 0,
                        "top_overlap_competitions": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            store = core.StateStore(root)

            with (
                patch("v24_app.core.PROJECT_DIR", root),
                patch("v24_app.core.STATE_STORE", store),
                patch("v24_app.core.STATSBOMB_EVENT_SUMMARIES_FILE", state / "statsbomb_event_summaries.json"),
                patch("v24_app.core.STATSBOMB_REVIEW_TRAINING_FILE", state / "statsbomb_review_training_samples.json"),
                patch("v24_app.core.import_statsbomb_open_data") as importer,
            ):
                result = core.repair_training_data_health("execute_statsbomb_coverage_import_plan")

        self.assertFalse(result["ok"])
        self.assertEqual(result["result"]["reason"], "no_overlap_competitions")
        self.assertEqual(result["result"]["sample_count"], 0)
        self.assertEqual(result["generated_sample_count"], 0)
        importer.assert_not_called()

    def test_repair_training_data_health_imports_aligned_historical_settlements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "settlements.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "match_id": "current-1",
                                "match_date": "2026-05-18",
                                "home_team": "Current Home",
                                "away_team": "Current Away",
                                "source": "live_settlement",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (state / "statsbomb_event_summaries.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "source_match_id": "s1",
                                "match_id": "s1",
                                "match_date": "2024-04-14",
                                "league": "1. Bundesliga",
                                "home_team": "Bayer Leverkusen",
                                "away_team": "Werder Bremen",
                                "event_summary": {
                                    "event_count": 10,
                                    "shot_count": 12,
                                    "xg_home": 2.1,
                                    "xg_away": 0.5,
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            input_path = state / "aligned_review_settlements.json"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "match_id": "hist-1",
                            "match_date": "2024-04-14",
                            "match_time": "17:30",
                            "league": "1. Bundesliga",
                            "home_team": "Bayer Leverkusen",
                            "away_team": "Werder Bremen",
                            "home_goals": 5,
                            "away_goals": 0,
                            "predicted": "home",
                            "is_correct": True,
                            "statsbomb_source_match_id": "s1",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            store = core.StateStore(root)

            with (
                patch("v24_app.core.PROJECT_DIR", root),
                patch("v24_app.core.STATE_STORE", store),
                patch("v24_app.core.STATSBOMB_EVENT_SUMMARIES_FILE", state / "statsbomb_event_summaries.json"),
                patch("v24_app.core.STATSBOMB_REVIEW_TRAINING_FILE", state / "statsbomb_review_training_samples.json"),
            ):
                result = core.repair_training_data_health(
                    "import_aligned_historical_settlements",
                    input_path=input_path,
                )

            settlements_payload = json.loads((state / "settlements.json").read_text(encoding="utf-8"))
            review_payload = json.loads((state / "statsbomb_review_training_samples.json").read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["action_key"], "import_aligned_historical_settlements")
        self.assertEqual(result["result"]["imported_settlements"], 1)
        self.assertEqual(result["result"]["sample_count"], 1)
        self.assertEqual(result["generated_sample_count"], 1)
        self.assertEqual(result["result"]["skipped_missing_statsbomb"], 1)
        self.assertEqual(result["result"]["skipped_unknown_label"], 0)
        self.assertTrue(result["output_path"].endswith("statsbomb_review_training_samples.json"))
        self.assertEqual(len(settlements_payload["items"]), 2)
        self.assertEqual(settlements_payload["items"][-1]["source"], "historical_review_import")
        self.assertEqual(review_payload["summary"]["sample_count"], 1)
        self.assertEqual(review_payload["items"][0]["match_id"], "hist-1")

    def test_repair_training_data_health_imports_unlabeled_aligned_settlements_as_facts_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "settlements.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "match_id": "current-1",
                                "match_date": "2026-05-18",
                                "home_team": "Current Home",
                                "away_team": "Current Away",
                                "source": "live_settlement",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (state / "statsbomb_event_summaries.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "source_match_id": "s1",
                                "match_id": "s1",
                                "match_date": "2024-04-14",
                                "league": "1. Bundesliga",
                                "home_team": "Bayer Leverkusen",
                                "away_team": "Werder Bremen",
                                "event_summary": {
                                    "event_count": 10,
                                    "shot_count": 12,
                                    "xg_home": 2.1,
                                    "xg_away": 0.5,
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            input_path = state / "aligned_result_facts.json"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "match_id": "hist-fact-1",
                            "match_date": "2024-04-14",
                            "match_time": "17:30",
                            "league": "1. Bundesliga",
                            "home_team": "Bayer Leverkusen",
                            "away_team": "Werder Bremen",
                            "home_goals": 5,
                            "away_goals": 0,
                            "statsbomb_source_match_id": "s1",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            store = core.StateStore(root)

            with (
                patch("v24_app.core.PROJECT_DIR", root),
                patch("v24_app.core.STATE_STORE", store),
                patch("v24_app.core.STATSBOMB_EVENT_SUMMARIES_FILE", state / "statsbomb_event_summaries.json"),
                patch("v24_app.core.STATSBOMB_REVIEW_TRAINING_FILE", state / "statsbomb_review_training_samples.json"),
            ):
                result = core.repair_training_data_health(
                    "import_aligned_historical_settlements",
                    input_path=input_path,
                )

            settlements_payload = json.loads((state / "settlements.json").read_text(encoding="utf-8"))
            review_payload = json.loads((state / "statsbomb_review_training_samples.json").read_text(encoding="utf-8"))

        issue_codes = {
            issue.get("code")
            for issue in result["after"]["training_health"]["issues"]
            if isinstance(issue, dict)
        }
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["imported_settlements"], 1)
        self.assertEqual(result["result"]["imported_unlabeled_settlements"], 1)
        self.assertEqual(result["result"]["imported_labeled_settlements"], 0)
        self.assertEqual(result["generated_sample_count"], 0)
        self.assertEqual(result["result"]["skipped_unknown_label"], 1)
        self.assertEqual(review_payload["summary"]["sample_count"], 0)
        self.assertEqual(settlements_payload["items"][-1]["source"], "historical_result_fact_import")
        self.assertFalse(settlements_payload["items"][-1]["labels_available"])
        self.assertIsNone(result["after"]["statsbomb_events"]["coverage_blocker"])
        self.assertIn("statsbomb_review_samples_missing", issue_codes)

    def test_repair_training_data_health_exports_statsbomb_review_label_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "settlements.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "match_id": "current-1",
                                "match_date": "2026-05-18",
                                "home_team": "Current Home",
                                "away_team": "Current Away",
                                "source": "live_settlement",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (state / "statsbomb_event_summaries.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "source_match_id": "s1",
                                "match_id": "s1",
                                "match_date": "2024-04-14",
                                "league": "1. Bundesliga",
                                "home_team": "Bayer Leverkusen",
                                "away_team": "Werder Bremen",
                                "event_summary": {
                                    "event_count": 10,
                                    "shot_count": 12,
                                    "xg_home": 2.1,
                                    "xg_away": 0.5,
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            input_path = state / "aligned_result_facts.json"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "match_id": "hist-fact-1",
                            "match_date": "2024-04-14",
                            "match_time": "17:30",
                            "league": "1. Bundesliga",
                            "home_team": "Bayer Leverkusen",
                            "away_team": "Werder Bremen",
                            "home_goals": 5,
                            "away_goals": 0,
                            "statsbomb_source_match_id": "s1",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            store = core.StateStore(root)

            with (
                patch("v24_app.core.PROJECT_DIR", root),
                patch("v24_app.core.STATE_STORE", store),
                patch("v24_app.core.STATSBOMB_EVENT_SUMMARIES_FILE", state / "statsbomb_event_summaries.json"),
                patch("v24_app.core.STATSBOMB_REVIEW_TRAINING_FILE", state / "statsbomb_review_training_samples.json"),
            ):
                core.repair_training_data_health("import_aligned_historical_settlements", input_path=input_path)
                result = core.repair_training_data_health("export_statsbomb_review_label_queue")

            queue_payload = json.loads((state / "statsbomb_review_label_queue.json").read_text(encoding="utf-8"))
            queue_csv = (state / "statsbomb_review_label_queue.csv").read_text(encoding="utf-8-sig")

        self.assertTrue(result["ok"])
        self.assertEqual(result["action_key"], "export_statsbomb_review_label_queue")
        self.assertEqual(result["result"]["queue_count"], 1)
        self.assertTrue(result["output_path"].endswith("statsbomb_review_label_queue.json"))
        self.assertTrue(queue_payload["items"][0]["annotation_status"] == "pending")
        self.assertTrue(queue_payload["items"][0]["missing_label_fields"])
        self.assertIn("match_id", queue_csv)
        self.assertIn("missing_label_fields", queue_csv)

    def test_training_model_gate_recommends_xgb_training_when_data_is_ready(self) -> None:
        coverage = {
            "training_health": {
                "status": "healthy",
                "blocking_count": 0,
                "warning_count": 0,
                "xgb_trainability": {
                    "sample_count": 400,
                    "min_sample_count": 300,
                    "valid_feature_count": 400,
                    "min_valid_feature_count": 300,
                },
            },
            "xgb_samples": {"sample_count": 400, "valid_feature_count": 400},
        }
        gate = core.get_training_model_gate_status(
            coverage,
            xgb_status={"model_ready": False, "min_train_samples": 30, "xgboost_available": True},
            play_model_status={},
        )

        self.assertEqual(gate["status"], "ready_to_train_xgb")
        self.assertEqual(gate["recommended_action"], "train_xgb")
        self.assertTrue(gate["xgb"]["trainable"])

    def test_training_model_gate_recommends_play_training_after_xgb_ready(self) -> None:
        coverage = {
            "training_health": {
                "status": "healthy",
                "blocking_count": 0,
                "warning_count": 0,
                "xgb_trainability": {
                    "sample_count": 900,
                    "min_sample_count": 300,
                    "valid_feature_count": 900,
                    "min_valid_feature_count": 300,
                },
            },
            "xgb_samples": {"sample_count": 900, "valid_feature_count": 900},
        }
        play_status = {
            "total_goals": {"usable_count": 900, "min_train_samples": 500, "model_ready": False},
            "scoreline": {"usable_count": 900, "min_train_samples": 800, "model_ready": False},
            "volatile_scoreline": {"usable_count": 900, "min_train_samples": 400, "model_ready": False},
        }
        gate = core.get_training_model_gate_status(
            coverage,
            xgb_status={"model_ready": True, "min_train_samples": 30, "xgboost_available": True},
            play_model_status=play_status,
        )

        self.assertEqual(gate["status"], "ready_to_train_play_models")
        self.assertEqual(gate["recommended_action"], "train_play_models")
        self.assertTrue(gate["play_models"]["all_trainable"])

    def test_training_model_gate_recommends_backtest_when_models_are_ready(self) -> None:
        coverage = {
            "training_health": {
                "status": "healthy",
                "blocking_count": 0,
                "warning_count": 0,
                "xgb_trainability": {
                    "sample_count": 900,
                    "min_sample_count": 300,
                    "valid_feature_count": 900,
                    "min_valid_feature_count": 300,
                },
            },
            "xgb_samples": {"sample_count": 900, "valid_feature_count": 900},
        }
        play_status = {
            "total_goals": {"usable_count": 900, "min_train_samples": 500, "model_ready": True},
            "scoreline": {"usable_count": 900, "min_train_samples": 800, "model_ready": True},
            "volatile_scoreline": {"usable_count": 900, "min_train_samples": 400, "model_ready": True},
        }
        gate = core.get_training_model_gate_status(
            coverage,
            xgb_status={"model_ready": True, "min_train_samples": 30, "xgboost_available": True},
            play_model_status=play_status,
        )

        self.assertEqual(gate["status"], "ready_for_backtest")
        self.assertEqual(gate["recommended_action"], "run_play_model_backtest")

    def test_train_xgb_with_postcheck_writes_followup_report(self) -> None:
        before_gate = {"status": "ready_to_train_xgb", "recommended_action": "train_xgb", "recommendation": "train xgb"}
        after_gate = {
            "status": "ready_to_train_play_models",
            "recommended_action": "train_play_models",
            "recommendation": "train play",
            "xgb": {"trainable": True, "model_ready": True, "sample_count": 400, "min_sample_count": 300, "valid_feature_count": 400, "min_valid_feature_count": 300},
            "play_models": {"trainable_count": 3, "ready_count": 0, "total_count": 3, "items": []},
        }
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp) / "reports"
            with (
                patch("v24_app.core.REPORT_DIR", report_dir),
                patch("v24_app.core.get_training_model_gate_status", side_effect=[before_gate, after_gate]),
                patch("v24_app.core.train_xgb_v0_now", return_value={"trained": True, "reason": "ok", "sample_count": 400, "updated_at": "2026-05-12"}),
            ):
                result = core.train_xgb_v0_with_postcheck_now()

            report_path = Path(result["postcheck"]["report_path"])
            report_text = report_path.read_text(encoding="utf-8")

            self.assertTrue(result["trained"])
            self.assertEqual(result["postcheck"]["status"], "ready_to_train_play_models")
            self.assertFalse(result["auto_backtest"]["executed"])
            self.assertTrue(report_path.exists())
            self.assertIn("Training Follow-up Report", report_text)

    def test_train_play_models_with_backtest_runs_backtest_and_writes_report(self) -> None:
        before_gate = {"status": "ready_to_train_play_models", "recommended_action": "train_play_models", "recommendation": "train play"}
        after_gate = {
            "status": "ready_for_backtest",
            "recommended_action": "run_play_model_backtest",
            "recommendation": "run backtest",
            "xgb": {"trainable": True, "model_ready": True, "sample_count": 900, "min_sample_count": 300, "valid_feature_count": 900, "min_valid_feature_count": 300},
            "play_models": {"trainable_count": 3, "ready_count": 3, "total_count": 3, "items": []},
        }
        train_result = {
            "trained": True,
            "reason": "ok",
            "total_goals": {"reason": "ok", "usable_count": 900},
            "scoreline": {"reason": "ok", "usable_count": 900},
            "volatile_scoreline": {"reason": "ok", "usable_count": 900},
        }
        backtest_result = {
            "ok": True,
            "reason": "ok",
            "report_path": "E:/APP/ELO/reports/play_model_backtest_unit.md",
            "validation": {"sample_count": 100, "date_start": "2025-01-01", "date_end": "2025-12-31"},
            "improvement": {"total_goals_model_delta": 0.02, "score_model_delta": 0.01},
        }
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp) / "reports"
            with (
                patch("v24_app.core.REPORT_DIR", report_dir),
                patch("v24_app.core.get_training_model_gate_status", side_effect=[before_gate, after_gate]),
                patch("v24_app.core.train_play_models_now", return_value=train_result),
                patch("v24_app.core.run_play_model_backtest", return_value=backtest_result) as backtest_spy,
            ):
                result = core.train_play_models_with_backtest_now()

            report_path = Path(result["postcheck"]["report_path"])
            report_text = report_path.read_text(encoding="utf-8")

        backtest_spy.assert_called_once()
        self.assertTrue(result["auto_backtest"]["executed"])
        self.assertTrue(result["auto_backtest"]["ok"])
        self.assertEqual(result["auto_backtest"]["takeover_gate"]["status"], "block")
        self.assertEqual(result["postcheck"]["status"], "ready_for_backtest")
        self.assertTrue(str(report_path).endswith(".md"))
        self.assertIn("Auto Backtest", report_text)
        self.assertIn("Takeover Gate", report_text)
        self.assertIn("play_model_backtest_unit.md", report_text)

    def test_train_play_models_with_backtest_skips_when_training_not_completed(self) -> None:
        before_gate = {"status": "ready_to_train_play_models", "recommended_action": "train_play_models", "recommendation": "train play"}
        after_gate = {"status": "ready_to_train_play_models", "recommended_action": "train_play_models", "recommendation": "train play"}
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp) / "reports"
            with (
                patch("v24_app.core.REPORT_DIR", report_dir),
                patch("v24_app.core.get_training_model_gate_status", side_effect=[before_gate, after_gate]),
                patch("v24_app.core.train_play_models_now", return_value={"trained": False, "reason": "no_model_trained"}),
                patch("v24_app.core.run_play_model_backtest") as backtest_spy,
            ):
                result = core.train_play_models_with_backtest_now()

        backtest_spy.assert_not_called()
        self.assertFalse(result["auto_backtest"]["executed"])
        self.assertEqual(result["auto_backtest"]["reason"], "training_not_completed")


if __name__ == "__main__":
    unittest.main()
