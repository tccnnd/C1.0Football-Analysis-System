from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import import_football_data_history as importer


class FootballDataHistoryImportTests(unittest.TestCase):
    def test_default_league_catalog_covers_broad_competitions(self) -> None:
        catalog = importer.league_catalog()
        codes = {str(item["code"]) for item in catalog}

        self.assertGreaterEqual(len(catalog), 20)
        self.assertIn("E0", codes)
        self.assertIn("E1", codes)
        self.assertIn("SP2", codes)
        self.assertIn("D2", codes)
        self.assertIn("N1", codes)
        self.assertIn("P1", codes)
        self.assertTrue(all(float(item["strength"]) > 0 for item in catalog))

    def test_convert_row_uses_expanded_league_strength(self) -> None:
        row = {
            "Date": "16/08/2024",
            "Time": "20:00",
            "HomeTeam": "Home",
            "AwayTeam": "Away",
            "FTHG": "2",
            "FTAG": "1",
            "B365H": "1.80",
            "B365D": "3.40",
            "B365A": "4.50",
            "B365CH": "1.75",
            "B365CD": "3.50",
            "B365CA": "4.80",
        }

        converted = importer.convert_row(row, "2425", "E1", "英冠")

        self.assertIsNotNone(converted)
        assert converted is not None
        self.assertEqual(converted["league"], "英冠")
        self.assertEqual(converted["league_strength"], importer.LEAGUE_STRENGTH["E1"])
        self.assertEqual(converted["odds_home"], 1.75)

    def test_build_import_audit_summarizes_leagues_and_failures(self) -> None:
        records = [
            {"league": "英超", "league_code": "E0", "season": "2425", "match_date": "2024-08-16"},
            {"league": "英冠", "league_code": "E1", "season": "2425", "match_date": "2024-08-17"},
            {"league": "英冠", "league_code": "E1", "season": "2425", "match_date": "2024-08-18"},
        ]

        audit = importer.build_import_audit(
            seasons=["2425"],
            leagues=["E0", "E1", "N1"],
            records=records,
            failures=["2425/N1: HTTP Error 404"],
            fetched_files=2,
        )

        self.assertEqual(audit["expected_files"], 3)
        self.assertEqual(audit["fetched_files"], 2)
        self.assertEqual(audit["missing_files"], 1)
        self.assertEqual(audit["failure_count"], 1)
        self.assertEqual(audit["league_counts"]["英冠"], 2)
        self.assertEqual(audit["date_start"], "2024-08-16")
        self.assertEqual(audit["date_end"], "2024-08-18")


if __name__ == "__main__":
    unittest.main()
