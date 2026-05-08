from __future__ import annotations

import csv
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

from c1.data import TEMPLATE_COLUMNS, build_availability_template_rows, export_availability_template_csv
from v24_app.core import AppMatch


class C1AvailabilityTemplateTests(unittest.TestCase):
    def make_test_root(self) -> Path:
        base_dir = PROJECT_ROOT / "data" / "tmp_c1_availability_template_tests"
        base_dir.mkdir(parents=True, exist_ok=True)
        path = base_dir / f"case_{uuid.uuid4().hex}"
        path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def sample_match(self) -> AppMatch:
        return AppMatch(
            home_team="A",
            away_team="B",
            league="Friendly",
            match_time="19:35",
            match_date="2026-04-03",
            odds_home=1.88,
            odds_draw=3.35,
            odds_away=4.1,
            handicap_line=-0.5,
            opening_odds_home=1.84,
            opening_odds_draw=3.4,
            opening_odds_away=4.25,
            return_rate=0.92,
            kelly_home=0.95,
            kelly_draw=0.94,
            kelly_away=0.98,
            source="live:titan",
            source_id="2965321",
        )

    def test_build_template_rows_preserves_match_identity(self) -> None:
        rows = build_availability_template_rows([self.sample_match()])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["match_id"], "2026-04-03|Friendly|A|B")
        self.assertEqual(rows[0]["source_id"], "2965321")
        self.assertEqual(rows[0]["home_team"], "A")
        self.assertEqual(rows[0]["away_team"], "B")

    def test_export_template_csv_writes_expected_header(self) -> None:
        output_dir = self.make_test_root()
        output_path = output_dir / "availability_template.csv"
        export_availability_template_csv(output_path, build_availability_template_rows([self.sample_match()]))
        with output_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(reader.fieldnames, TEMPLATE_COLUMNS)
            rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["match_id"], "2026-04-03|Friendly|A|B")


if __name__ == "__main__":
    unittest.main()
