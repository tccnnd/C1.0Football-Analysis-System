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

from audit_statsbomb_settlement_coverage import build_coverage_audit, main


class AuditStatsBombSettlementCoverageTests(unittest.TestCase):
    def test_build_coverage_audit_counts_exact_and_candidates(self) -> None:
        settlements = [
            {
                "match_id": "2024-04-14|1. Bundesliga|Bayer Leverkusen|Werder Bremen",
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
        statsbomb = [
            {
                "source_match_id": 3895302,
                "match_date": "2024-04-14",
                "league": "1. Bundesliga",
                "home_team": "Bayer Leverkusen",
                "away_team": "Werder Bremen",
            }
        ]

        audit = build_coverage_audit(settlements, statsbomb, min_candidate_score=0.5)

        self.assertEqual(audit["settlement_count"], 3)
        self.assertEqual(audit["statsbomb_match_count"], 1)
        self.assertEqual(audit["exact_match_count"], 1)
        self.assertEqual(audit["candidate_count"], 1)
        self.assertEqual(audit["no_same_date_count"], 1)
        self.assertEqual(audit["candidate_rows"][0]["statsbomb"]["source_match_id"], 3895302)

    def test_build_coverage_audit_reports_no_date_overlap(self) -> None:
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
        statsbomb = [
            {
                "source_match_id": 3895302,
                "match_date": "2024-03-10",
                "league": "1. Bundesliga",
                "home_team": "Bayer Leverkusen",
                "away_team": "Werder Bremen",
            },
            {
                "source_match_id": 3895303,
                "match_date": "2024-03-11",
                "league": "1. Bundesliga",
                "home_team": "Borussia Dortmund",
                "away_team": "Bayern Munich",
            },
        ]

        audit = build_coverage_audit(settlements, statsbomb, min_candidate_score=0.5)

        self.assertEqual(audit["coverage_blocker"], "no_date_overlap")
        self.assertEqual(audit["date_overlap_count"], 0)
        self.assertEqual(audit["date_overlap_ratio"], 0.0)
        self.assertEqual(audit["settlement_date_start"], "2024-04-14")
        self.assertEqual(audit["settlement_date_end"], "2024-04-15")
        self.assertEqual(audit["statsbomb_date_start"], "2024-03-10")
        self.assertEqual(audit["statsbomb_date_end"], "2024-03-11")
        self.assertEqual(audit["recommendation"], "import_statsbomb_for_settlement_date_range")

    def test_main_writes_audit_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = root / "data" / "state"
            state.mkdir(parents=True)
            (state / "settlements.json").write_text(
                json.dumps({"items": [{"match_id": "m1", "match_date": "2024-04-14", "home_team": "A", "away_team": "B"}]}),
                encoding="utf-8",
            )
            (state / "statsbomb_event_summaries.json").write_text(
                json.dumps({"items": [{"source_match_id": 1, "match_date": "2024-04-14", "home_team": "A", "away_team": "B"}]}),
                encoding="utf-8",
            )

            old_argv = sys.argv
            try:
                sys.argv = ["audit", "--project-root", str(root)]
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), 0)
            finally:
                sys.argv = old_argv

            payload = json.loads((state / "statsbomb_settlement_coverage_audit.json").read_text(encoding="utf-8"))

        self.assertEqual(payload["exact_match_count"], 1)


if __name__ == "__main__":
    unittest.main()
