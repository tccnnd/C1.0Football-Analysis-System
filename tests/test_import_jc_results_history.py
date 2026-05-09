from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from import_jc_results_history import import_jc_results_history


def _row(
    *,
    year: str = "2022",
    issue: str = "周五001",
    league: str = "英超",
    status: str = "完",
    full_score: str = " 2 - 1",
    close_home: str = "1.80 ",
    close_draw: str = "3.40 ",
    close_away: str = "4.10 ",
) -> list[str]:
    row = [""] * 354
    row[0] = "1001"
    row[1] = year
    row[3] = issue
    row[4] = league
    row[5] = "第1轮"
    row[6] = "01-02 19:30"
    row[7] = status
    row[9] = "主队A"
    row[10] = "客队B"
    row[12] = "1 - 0"
    row[13] = full_score
    row[14] = "胜"
    row[15] = "1.95 "
    row[16] = "3.20 "
    row[17] = "3.60 "
    row[18] = close_home
    row[19] = close_draw
    row[20] = close_away
    row[341] = "+1"
    row[344] = "让胜"
    row[345] = "1.55 "
    row[346] = "胜"
    row[347] = "1.80 "
    return row


class ImportJcResultsHistoryTests(unittest.TestCase):
    def test_import_filters_and_normalizes_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "results.csv"
            output_path = temp_path / "history.jsonl"
            audit_path = temp_path / "audit.json"
            with input_path.open("w", encoding="utf-8-sig", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["meta"])
                writer.writerow(["meta"])
                writer.writerow(["编号", "年份"])
                writer.writerow(_row())
                writer.writerow(_row(year="2021", issue="周五002"))
                writer.writerow(_row(year="2022", issue="周五003", status="未"))
                writer.writerow(_row(year="2023", issue="周五004", close_home="", close_draw="", close_away=""))

            audit = import_jc_results_history(
                input_path=input_path,
                output_path=output_path,
                audit_output_path=audit_path,
                start_year=2022,
                end_year=2026,
            )

            records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record["source"], "jc_results_csv")
            self.assertEqual(record["source_row"], 4)
            self.assertEqual(record["match_date"], "2022-01-02")
            self.assertEqual(record["match_time"], "19:30")
            self.assertEqual(record["home_goals"], 2)
            self.assertEqual(record["away_goals"], 1)
            self.assertEqual(record["home_ht_goals"], 1)
            self.assertEqual(record["away_ht_goals"], 0)
            self.assertEqual(record["result"], "胜")
            self.assertEqual(record["odds_home"], 1.8)
            self.assertEqual(record["opening_odds_away"], 3.6)
            self.assertEqual(record["handicap"], 1.0)
            self.assertTrue(str(record["match_id"]).startswith("jc:2022:周五001:"))

            self.assertEqual(audit["raw_rows"], 4)
            self.assertEqual(audit["imported"], 1)
            self.assertEqual(audit["skipped"]["by_year"], 1)
            self.assertEqual(audit["skipped"]["by_status"], 1)
            self.assertEqual(audit["skipped"]["missing_close_odds"], 1)
            self.assertEqual(audit["missing_spf_close"], 1)
            self.assertEqual(json.loads(audit_path.read_text(encoding="utf-8"))["imported"], 1)


if __name__ == "__main__":
    unittest.main()
