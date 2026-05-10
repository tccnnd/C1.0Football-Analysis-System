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

from plan_statsbomb_import_coverage import build_statsbomb_import_coverage_plan, date_range, main


def _competition(competition_id: int, season_id: int, name: str, season: str) -> dict:
    return {
        "competition_id": competition_id,
        "season_id": season_id,
        "competition_name": name,
        "season_name": season,
        "country_name": "Test",
    }


def _match(match_id: int, date: str, home: str = "A", away: str = "B") -> dict:
    return {
        "match_id": match_id,
        "match_date": date,
        "home_team": {"home_team_name": home},
        "away_team": {"away_team_name": away},
    }


class PlanStatsBombImportCoverageTests(unittest.TestCase):
    def test_build_plan_ranks_competitions_by_settlement_overlap(self) -> None:
        competitions = [
            _competition(1, 10, "Old League", "2020"),
            _competition(2, 20, "Overlap League", "2026"),
        ]
        settlements = [
            {"match_date": "2026-03-29"},
            {"match_date": "2026-03-29"},
            {"match_date": "2026-04-01"},
        ]
        matches = {
            (1, 10): [_match(101, "2020-01-01")],
            (2, 20): [_match(201, "2026-03-29"), _match(202, "2026-04-02")],
        }

        plan = build_statsbomb_import_coverage_plan(
            competitions=competitions,
            settlements=settlements,
            load_matches_fn=lambda competition_id, season_id: matches[(competition_id, season_id)],
        )

        self.assertEqual(plan["settlement_count"], 3)
        self.assertEqual(plan["overlap_competition_count"], 1)
        self.assertEqual(plan["recommendation"], "import_overlap_events")
        self.assertEqual(plan["top_overlap_competitions"][0]["competition_name"], "Overlap League")
        self.assertEqual(plan["top_overlap_competitions"][0]["overlap_settlement_count"], 2)

    def test_build_plan_handles_no_date_overlap(self) -> None:
        plan = build_statsbomb_import_coverage_plan(
            competitions=[_competition(1, 10, "Old League", "2020")],
            settlements=[{"match_date": "2026-03-29"}],
            load_matches_fn=lambda _competition_id, _season_id: [_match(101, "2020-01-01")],
        )

        self.assertEqual(plan["recommendation"], "no_date_overlap")
        self.assertEqual(plan["overlap_competition_count"], 0)
        self.assertTrue(plan["recent_competitions"])

    def test_main_offline_writes_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = root / "data" / "state"
            offline = root / "offline"
            state.mkdir(parents=True)
            (state / "settlements.json").write_text(json.dumps({"items": [{"match_date": "2026-03-29"}]}), encoding="utf-8")
            (offline / "matches" / "2").mkdir(parents=True)
            (offline / "competitions.json").write_text(json.dumps([_competition(2, 20, "Overlap League", "2026")]), encoding="utf-8")
            (offline / "matches" / "2" / "20.json").write_text(json.dumps([_match(201, "2026-03-29")]), encoding="utf-8")

            old_argv = sys.argv
            try:
                sys.argv = ["plan", "--project-root", str(root), "--offline-dir", str(offline)]
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), 0)
            finally:
                sys.argv = old_argv

            payload = json.loads((state / "statsbomb_import_coverage_plan.json").read_text(encoding="utf-8"))

        self.assertEqual(payload["recommendation"], "import_overlap_events")

    def test_date_range_ignores_empty_values(self) -> None:
        self.assertEqual(date_range(["", "2024-01-02", "2024-01-01"]), ("2024-01-01", "2024-01-02"))


if __name__ == "__main__":
    unittest.main()
