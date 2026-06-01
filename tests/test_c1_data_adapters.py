from __future__ import annotations

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

from c1.data import adapt_legacy_match
from c1.runtime import C1ShadowRunner, run_shadow_for_legacy_match
from v24_app.core import AppMatch


class C1DataAdapterTests(unittest.TestCase):
    def make_test_root(self) -> Path:
        base_dir = PROJECT_ROOT / "data" / "tmp_c1_data_adapter_tests"
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

    def test_adapt_legacy_match_maps_v24_app_match(self) -> None:
        adapted = adapt_legacy_match(self.sample_match())
        self.assertEqual(adapted.match_id, "2026-04-03|Friendly|A|B")
        self.assertEqual(adapted.raw_fields["market_side"], "home")
        self.assertEqual(adapted.raw_fields["current_odds_home"], 1.88)
        self.assertEqual(adapted.raw_fields["opening_handicap_line"], -0.5)
        self.assertEqual(adapted.metadata["source_id"], "2965321")

    def test_legacy_bridge_runs_shadow_pipeline_from_v24_match(self) -> None:
        audit_dir = self.make_test_root()
        runner = C1ShadowRunner(PROJECT_ROOT, audit_dir=audit_dir)
        result = run_shadow_for_legacy_match(
            project_root=PROJECT_ROOT,
            match=self.sample_match(),
            runner=runner,
            context={"source": "unit"},
            created_at="2026-04-03 21:00:00",
        )
        self.assertEqual(result.match_id, "2026-04-03|Friendly|A|B")
        # Translation layer now emits 5 plays: 1x2 / handicap / totals / htft / scoreline
        self.assertEqual(len(result.translation_result.items), 5)
        self.assertEqual(result.feature_snapshot.fields["source_id"], "2965321")

    def test_adapter_accepts_external_availability_enrichment(self) -> None:
        adapted = adapt_legacy_match(
            self.sample_match(),
            extra_fields={
                "home_availability_known": True,
                "away_availability_known": True,
                "home_absent_count": 2,
                "away_absent_count": 0,
                "home_key_absent_count": 1,
                "away_key_absent_count": 0,
                "lineup_updated_at": "2026-04-03 18:00:00",
                "lineup_freshness_hours": 1.5,
            },
        )
        self.assertTrue(adapted.match_context is not None and adapted.match_context.lineup_known)
        self.assertGreater(adapted.raw_fields["injury_conflict_score"], 0.0)
        self.assertGreater(adapted.raw_fields["team_availability_quality"], 0.0)


if __name__ == "__main__":
    unittest.main()
