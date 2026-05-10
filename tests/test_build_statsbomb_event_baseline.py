from __future__ import annotations

import json
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from build_statsbomb_event_baseline import backfill_tags, build_statsbomb_event_baseline, baseline_row, main


def record(
    *,
    match_id: str = "statsbomb:1",
    home_goals: int = 1,
    away_goals: int = 2,
    home_xg: float = 2.2,
    away_xg: float = 0.8,
) -> dict:
    return {
        "match_id": match_id,
        "source_match_id": int(match_id.split(":")[-1]),
        "match_date": "2024-06-14",
        "league": "UEFA Euro",
        "season": "2024",
        "home_team": "Home",
        "away_team": "Away",
        "home_goals": home_goals,
        "away_goals": away_goals,
        "event_summary": {
            "event_count": 3500,
            "team_stats": {
                "Home": {"xg": home_xg, "shots": 15, "shots_on_target": 5},
                "Away": {"xg": away_xg, "shots": 7, "shots_on_target": 3},
            },
        },
    }


class BuildStatsBombEventBaselineTests(unittest.TestCase):
    def test_baseline_row_detects_finishing_variance(self) -> None:
        row = baseline_row(record())

        assert row is not None
        self.assertEqual(row["score_winner"], "away")
        self.assertEqual(row["xg_winner"], "home")
        self.assertTrue(row["finishing_variance"])
        self.assertAlmostEqual(row["xg_margin"], 1.4)
        self.assertEqual(row["shot_winner"], "home")
        self.assertIn("xg_direction_failed", row["backfill_tags"])
        self.assertEqual(row["backfill_tags"], backfill_tags(row))

    def test_build_baseline_summarizes_competitions_and_buckets(self) -> None:
        baseline = build_statsbomb_event_baseline(
            [
                record(match_id="statsbomb:1"),
                record(match_id="statsbomb:2", home_goals=2, away_goals=0, home_xg=1.8, away_xg=0.6),
            ]
        )

        self.assertEqual(baseline["summary"]["match_count"], 2)
        self.assertEqual(baseline["summary"]["competition_count"], 1)
        self.assertEqual(baseline["summary"]["finishing_variance_rate"], "50.0%")
        self.assertIn("UEFA Euro | 2024", baseline["competition_profiles"])
        self.assertIn("dominant_edge", baseline["xg_margin_buckets"])
        self.assertEqual(len(baseline["variance_rows"]), 1)
        self.assertIn("backfill_tag_index", baseline)
        self.assertIn("xg_direction_failed", baseline["backfill_tag_index"])

    def test_main_writes_baseline_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "statsbomb_event_summaries.json").write_text(
                json.dumps({"items": [record()]}, ensure_ascii=False),
                encoding="utf-8",
            )
            old_argv = sys.argv
            try:
                sys.argv = ["baseline", "--project-root", str(root)]
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), 0)
            finally:
                sys.argv = old_argv
            payload = json.loads((state / "statsbomb_event_baseline.json").read_text(encoding="utf-8"))

        self.assertEqual(payload["summary"]["match_count"], 1)
        self.assertEqual(payload["purpose"], "historical_post_match_event_baseline")


if __name__ == "__main__":
    unittest.main()
