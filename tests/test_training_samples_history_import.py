from __future__ import annotations

import csv
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
            self.assertEqual(result["storage_limit"], 100000)
            self.assertEqual(result["dropped_by_limit"], 0)

    def test_import_accepts_sample_limit_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "history.jsonl"
            input_path.write_text(
                "\n".join(json.dumps(_record(f"m{index}"), ensure_ascii=False) for index in range(3)),
                encoding="utf-8",
            )

            result = import_historical_xgb_samples(
                project_dir=temp_path,
                input_path=input_path,
                replace=True,
                sync_ratings=False,
                sample_limit=2,
            )

            self.assertEqual(result["merged_total"], 3)
            self.assertEqual(result["saved_total"], 2)
            self.assertEqual(result["storage_limit"], 2)
            self.assertEqual(result["dropped_by_limit"], 1)
            self.assertEqual(result["sample_limit_override"], 2)

    def test_import_accepts_jc_results_csv_multirow_header(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "jc_results.csv"
            with input_path.open("w", encoding="utf-8-sig", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["比赛信息-严禁用于赌博", "", "", "竞官方胜平负全套指数"])
                writer.writerow(["有问题咨询反馈交流", "", "", "初胜平负"])
                writer.writerow(
                    [
                        "编号",
                        "年份",
                        "赛事",
                        "比赛时间",
                        "主队",
                        "客队",
                        "半场",
                        "全场",
                        "竞官方初胜",
                        "竞官方初平",
                        "竞官方初负",
                        "竞官方终胜",
                        "竞官方终平",
                        "竞官方终负",
                        "让球数",
                        "竞终胜凯利",
                        "竞终平凯利",
                        "竞终负凯利",
                    ]
                )
                writer.writerow(
                    [
                        "1",
                        "2021",
                        "英超",
                        "01-02 01:30",
                        "埃弗顿",
                        "西汉姆联",
                        "0 - 0",
                        "0 - 1",
                        "1.85",
                        "3.30",
                        "3.40",
                        "1.85",
                        "3.30",
                        "3.38",
                        "-1",
                        "0.80",
                        "0.92",
                        "0.98",
                    ]
                )

            result = import_historical_xgb_samples(
                project_dir=temp_path,
                input_path=input_path,
                replace=True,
                sync_ratings=False,
            )
            payload = json.loads((temp_path / "data" / "state" / "xgb_training_samples.json").read_text(encoding="utf-8"))

            self.assertEqual(result["imported_samples"], 1)
            self.assertEqual(result["date_range"], {"start": "2021-01-02", "end": "2021-01-02"})
            self.assertEqual(result["label_counts"][2], 1)
            self.assertEqual(payload["items"][0]["meta"]["league"], "英超")
            self.assertEqual(payload["items"][0]["meta"]["home_team"], "埃弗顿")
            self.assertEqual(payload["items"][0]["meta"]["away_team"], "西汉姆联")
            self.assertEqual(payload["items"][0]["meta"]["opening_odds_home"], 1.85)
            self.assertEqual(payload["items"][0]["features"]["odds_away"], 3.38)


if __name__ == "__main__":
    unittest.main()
