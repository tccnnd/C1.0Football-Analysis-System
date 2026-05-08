from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from c1.audit import C1AuditStore
from c1.core.reason_codes import DecisionAction
from c1.core.schema import FeatureSnapshot, PredictionSnapshot
from c1.features import build_governance_feature_snapshot
from c1.modules.judge import GovernanceJudge, load_governance_config


class C1AuditStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_governance_config(PROJECT_ROOT / "c1" / "configs" / "governance_cfg.yaml")

    def base_raw(self, **overrides):
        payload = {
            "context_completeness": 0.92,
            "odds_snapshot_quality": 0.84,
            "team_availability_quality": 0.72,
            "source_reliability": 0.88,
            "data_freshness_hours": 2,
            "lineup_known": True,
            "lineup_freshness_hours": 3,
            "home_rating": 1520,
            "away_rating": 1490,
            "market_side": "home",
            "market_divergence": 0.04,
            "injury_conflict_score": 0.05,
            "schedule_pressure": 0.10,
            "weather_risk": 0.05,
            "environment_safe": True,
            "opening_odds_home": 1.82,
            "current_odds_home": 1.88,
            "opening_handicap_line": -0.50,
            "current_handicap_line": -0.25,
        }
        payload.update(overrides)
        return payload

    def prediction_snapshot(self) -> PredictionSnapshot:
        return PredictionSnapshot(
            model_name="stage5",
            raw_probabilities={"home": 0.57, "draw": 0.24, "away": 0.19},
            predicted_side="home",
            confidence=0.57,
            created_at="2026-04-03 12:00:00",
            metadata={"source": "unit"},
        )

    def make_test_root(self) -> Path:
        base_dir = PROJECT_ROOT / "data" / "tmp_c1_audit_tests"
        base_dir.mkdir(parents=True, exist_ok=True)
        path = base_dir / f"case_{uuid.uuid4().hex}"
        path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_record_feature_vector_writes_jsonl(self) -> None:
        test_root = self.make_test_root()
        store = C1AuditStore(PROJECT_ROOT, audit_dir=test_root)
        snapshot = FeatureSnapshot(
            match_id="m-audit-1",
            feature_version="c1.phase2",
            fields={"info_quality": 0.8},
            source="unit",
            created_at="2026-04-03 12:00:00",
        )
        store.record_feature_vector(snapshot=snapshot, attribution_tags=["shadow"])
        items = store.read_feature_vectors()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["match_id"], "m-audit-1")
        self.assertEqual(items[0]["feature_snapshot"]["fields"]["info_quality"], 0.8)

    def test_record_prediction_preserves_feature_and_prediction_snapshot(self) -> None:
        test_root = self.make_test_root()
        store = C1AuditStore(PROJECT_ROOT, audit_dir=test_root)
        feature_snapshot = build_governance_feature_snapshot(
            match_id="m-audit-2",
            raw_fields=self.base_raw(),
            prediction_snapshot=self.prediction_snapshot(),
            config=self.config,
            created_at="2026-04-03 12:00:00",
        )
        prediction_snapshot = self.prediction_snapshot()
        store.record_prediction(
            match_id="m-audit-2",
            feature_snapshot=feature_snapshot,
            prediction_snapshot=prediction_snapshot,
            attribution_tags=["comparison", "v24-baseline"],
        )
        items = store.read_predictions()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["prediction_snapshot"]["predicted_side"], "home")
        self.assertIn("feature_snapshot", items[0])
        self.assertEqual(items[0]["attribution_tags"], ["comparison", "v24-baseline"])

    def test_record_governance_decision_preserves_reason_codes(self) -> None:
        test_root = self.make_test_root()
        store = C1AuditStore(PROJECT_ROOT, audit_dir=test_root)
        prediction_snapshot = self.prediction_snapshot()
        feature_snapshot = build_governance_feature_snapshot(
            match_id="m-audit-3",
            raw_fields=self.base_raw(injury_conflict_score=0.92),
            prediction_snapshot=prediction_snapshot,
            config=self.config,
            created_at="2026-04-03 12:00:00",
        )
        judge = GovernanceJudge(config=self.config)
        request_module = __import__("c1.core.schema", fromlist=["GovernanceRequest"])
        decision = judge.evaluate(
            request=request_module.GovernanceRequest(
                match_id="m-audit-3",
                feature_snapshot=feature_snapshot,
                prediction_snapshot=prediction_snapshot,
                governance_state={},
            )
        )
        self.assertEqual(decision.action, DecisionAction.BLOCK)
        store.record_governance_decision(
            match_id="m-audit-3",
            feature_snapshot=feature_snapshot,
            prediction_snapshot=prediction_snapshot,
            governance_decision=decision,
            attribution_tags=["governed"],
            metadata={"run_mode": "shadow"},
        )
        items = store.read_governance_decisions()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["governance_decision"]["action"], "BLOCK")
        self.assertIn("reason_codes", items[0]["governance_decision"])
        self.assertEqual(items[0]["metadata"]["run_mode"], "shadow")

    def test_limit_reads_tail_records(self) -> None:
        test_root = self.make_test_root()
        store = C1AuditStore(PROJECT_ROOT, audit_dir=test_root)
        for idx in range(3):
            snapshot = FeatureSnapshot(
                match_id=f"m-tail-{idx}",
                feature_version="c1.phase2",
                fields={"idx": idx},
                source="unit",
            )
            store.record_feature_vector(snapshot=snapshot)
        tail = store.read_feature_vectors(limit=2)
        self.assertEqual(len(tail), 2)
        self.assertEqual(tail[0]["match_id"], "m-tail-1")
        self.assertEqual(tail[1]["match_id"], "m-tail-2")

    def test_record_market_snapshot_writes_jsonl(self) -> None:
        test_root = self.make_test_root()
        store = C1AuditStore(PROJECT_ROOT, audit_dir=test_root)
        store.record_market_snapshot(
            match_id="m-market-1",
            phase="T30",
            snapshot={"odds_home": 1.88, "odds_draw": 3.25, "odds_away": 4.2},
            attribution_tags=["prematch", "scheduler"],
            metadata={"provider_name": "stored_snapshots"},
        )
        items = store.read_market_snapshots()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["phase"], "T30")
        self.assertEqual(items[0]["snapshot"]["odds_home"], 1.88)
        self.assertEqual(items[0]["metadata"]["provider_name"], "stored_snapshots")


if __name__ == "__main__":
    unittest.main()
