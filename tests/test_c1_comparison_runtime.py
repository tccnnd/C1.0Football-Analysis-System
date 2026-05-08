from __future__ import annotations

import json
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

from c1.runtime import C1ShadowRunner, run_shadow_comparison_for_legacy_matches
from v24_app.core import AppMatch


class C1ComparisonRuntimeTests(unittest.TestCase):
    def make_test_root(self, name: str) -> Path:
        base_dir = PROJECT_ROOT / "data" / name
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
            odds_away=4.10,
            handicap_line=-0.5,
            opening_odds_home=1.84,
            opening_odds_draw=3.40,
            opening_odds_away=4.25,
            return_rate=0.92,
            kelly_home=0.95,
            kelly_draw=0.94,
            kelly_away=0.98,
            source="live:titan",
            source_id="2965321",
        )

    def test_shadow_comparison_generates_reports(self) -> None:
        audit_dir = self.make_test_root("tmp_c1_comparison_audit_tests")
        report_dir = self.make_test_root("tmp_c1_comparison_report_tests")
        runner = C1ShadowRunner(PROJECT_ROOT, audit_dir=audit_dir)

        def stub_predictor(_match: AppMatch) -> dict:
            return {
                "recommendation": "主胜",
                "confidence": 0.66,
                "handicap_display": "-0.5 让胜",
                "total_goals_recommendation": "2球",
                "probabilities": {"home": 0.55, "draw": 0.24, "away": 0.21},
            }

        result = run_shadow_comparison_for_legacy_matches(
            project_root=PROJECT_ROOT,
            matches=[self.sample_match()],
            v24_predictor=stub_predictor,
            shadow_runner=runner,
            report_dir=report_dir,
            created_at="2026-04-03 22:00:00",
        )
        self.assertEqual(result.total_matches, 1)
        self.assertTrue(Path(result.markdown_report).exists())
        self.assertTrue(Path(result.json_report).exists())
        self.assertIn("governance_counts", result.summary)
        self.assertIn("reason_code_counts", result.summary)
        self.assertIn("near_block_count", result.summary)
        self.assertIsInstance(result.rows[0].governance_reason_codes, list)
        self.assertIsInstance(result.rows[0].governance_gate_statuses, dict)
        self.assertTrue(result.rows[0].suggested_action)

        payload = json.loads(Path(result.json_report).read_text(encoding="utf-8"))
        self.assertEqual(payload["total_matches"], 1)
        self.assertEqual(len(payload["rows"]), 1)
        self.assertIn("primary_reason_code", payload["rows"][0])
        self.assertIn("near_block", payload["rows"][0])
        self.assertIn("suggested_action", payload["rows"][0])


if __name__ == "__main__":
    unittest.main()
