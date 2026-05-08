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

from c1.data import C1AvailabilityStore
from c1.runtime import C1ShadowRunner, run_shadow_comparison_for_legacy_matches
from v24_app.core import AppMatch


class C1AvailabilityStoreTests(unittest.TestCase):
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

    def test_store_import_and_resolve_by_match_id(self) -> None:
        state_dir = self.make_test_root("tmp_c1_availability_store_tests")
        store = C1AvailabilityStore(PROJECT_ROOT, state_dir=state_dir)
        result = store.import_rows(
            [
                {
                    "match_id": "2026-04-03|Friendly|A|B",
                    "source_id": "2965321",
                    "match_date": "2026-04-03",
                    "league": "Friendly",
                    "home_team": "A",
                    "away_team": "B",
                    "home_availability_known": True,
                    "away_availability_known": True,
                    "home_absent_count": 2,
                    "away_absent_count": 0,
                    "lineup_freshness_hours": 1.5,
                }
            ],
            replace=True,
        )
        self.assertEqual(result["imported_rows"], 1)
        resolved = store.resolve_for_match(self.sample_match())
        self.assertEqual(str(resolved.get("source_id")), "2965321")
        self.assertEqual(str(resolved.get("home_absent_count")), "2")

    def test_comparison_uses_availability_store_resolution(self) -> None:
        state_dir = self.make_test_root("tmp_c1_availability_store_cmp_tests")
        audit_dir = self.make_test_root("tmp_c1_availability_store_cmp_audit_tests")
        report_dir = self.make_test_root("tmp_c1_availability_store_cmp_report_tests")
        store = C1AvailabilityStore(PROJECT_ROOT, state_dir=state_dir)
        store.import_rows(
            [
                {
                    "match_id": "2026-04-03|Friendly|A|B",
                    "home_availability_known": True,
                    "away_availability_known": True,
                    "lineup_freshness_hours": 1.0,
                    "home_absent_count": 3,
                    "home_key_absent_count": 2,
                    "away_absent_count": 0,
                    "away_key_absent_count": 0,
                }
            ],
            replace=True,
        )
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
            availability_store=store,
            created_at="2026-04-03 22:40:00",
        )
        self.assertEqual(result.total_matches, 1)
        row = result.rows[0]
        self.assertNotIn("LINEUP_UNKNOWN", row.governance_reason_codes)
        self.assertTrue(Path(result.json_report).exists())
        payload = json.loads(Path(result.json_report).read_text(encoding="utf-8"))
        self.assertEqual(payload["total_matches"], 1)

    def test_save_and_load_sync_status(self) -> None:
        state_dir = self.make_test_root("tmp_c1_availability_store_sync_tests")
        store = C1AvailabilityStore(PROJECT_ROOT, state_dir=state_dir)
        store.save_sync_status(
            {
                "last_sync_at": "2026-04-07 14:30:00",
                "total_rows": 80,
                "total_keys": 240,
                "failed_providers": 0,
            }
        )
        loaded = store.load_sync_status()
        self.assertEqual(str(loaded.get("last_sync_at")), "2026-04-07 14:30:00")
        self.assertEqual(int(loaded.get("total_rows", 0)), 80)


if __name__ == "__main__":
    unittest.main()
