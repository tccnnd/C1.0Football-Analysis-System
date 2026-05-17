from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.core import AppMatch
from v24_app.trace_envelope import TRACE_VERSION, build_prediction_trace_envelope


class TraceEnvelopeTests(unittest.TestCase):
    def test_build_prediction_trace_envelope_normalizes_supervisor_graph(self) -> None:
        match = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="19:35",
            match_date="2026-05-18",
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.1,
            source="live:titan",
            source_id="m1",
        )
        prediction = {
            "match_id": match.match_id,
            "recommendation": "home",
            "confidence": 0.68,
            "risk_level": "HIGH",
            "model": "test-model",
            "ensemble_weights": {"market": 0.35, "elo": 0.30, "poisson": 0.20, "xgboost": 0.15},
            "action_fact_refs": [
                {
                    "action_id": "shot-1",
                    "match_id": match.match_id,
                    "source_event_id": "event-1",
                    "provider": "statsbomb",
                    "schema_version": "action_fact_v1",
                }
            ],
            "market_entropy": {"level": "HIGH", "score": 0.84},
            "supervisor": {
                "status": "alert",
                "decision": {"release_allowed": False, "requires_human_review": True},
                "agents": [
                    {
                        "name": "MarketEntropy",
                        "status": "alert",
                        "trigger": "market_signal_check",
                        "inputs": {"level": "HIGH"},
                        "outputs": {"signals": ["kelly_against_pick"]},
                        "checks": ["entropy level"],
                        "evidence": {"score": 0.84},
                        "rationale": "Market pressure is abnormal.",
                        "actions": ["manual_market_review"],
                    }
                ],
            },
        }

        trace = build_prediction_trace_envelope(
            match=match,
            prediction=prediction,
            started_at=datetime(2026, 5, 18, 10, 0, 0),
            generated_at=datetime(2026, 5, 18, 10, 0, 1),
            latency_ms=123.4567,
        )

        self.assertEqual(trace["trace_version"], TRACE_VERSION)
        self.assertTrue(str(trace["trace_id"]).startswith("trc_"))
        self.assertTrue(str(trace["session_id"]).startswith("ses_"))
        self.assertTrue(str(trace["request_id"]).startswith("req_"))
        self.assertTrue(str(trace["analysis_id"]).startswith("ana_"))
        self.assertEqual(trace["thread_id"], "app:local")
        self.assertEqual(trace["user_id"], "local-user")
        self.assertEqual(trace["workflow_name"], "match-analysis-v1")
        self.assertEqual(trace["workflow_version"], "match_analysis_v1")
        self.assertEqual(trace["match_id"], match.match_id)
        self.assertEqual(trace["input_ref"]["match_id"], match.match_id)
        self.assertTrue(any(item["kind"] == "match_fact" for item in trace["fact_refs"]))
        self.assertTrue(any(item["kind"] == "source_provenance" for item in trace["fact_refs"]))
        self.assertTrue(any(item["kind"] == "action_fact" for item in trace["fact_refs"]))
        self.assertTrue(any(item["kind"] == "action_fact" for item in trace["input_ref"]["fact_refs"]))
        self.assertTrue(any(item["kind"] == "source_provenance" for item in trace["replay_input_ref"]["fact_refs"]))
        self.assertTrue(str(trace["state_snapshot_ref"]).startswith("prediction_snapshot:"))
        self.assertTrue(str(trace["output_ref"]).startswith("prediction_output:trc_"))
        self.assertEqual(trace["prompt_name"], "strategy_report")
        self.assertEqual(trace["prompt_version"], "strategy_report_v1")
        self.assertEqual(trace["model_name"], "test-model")
        self.assertEqual(trace["model_params"]["ensemble_weights"]["market"], 0.35)
        self.assertEqual(trace["status"], "alert")
        self.assertEqual(trace["latency_ms"], 123.457)
        self.assertEqual(trace["ended_at"], "2026-05-18 10:00:01.000000")
        self.assertEqual(trace["token_usage"]["total_tokens"], 0)
        self.assertEqual(trace["cost"]["amount"], 0.0)
        self.assertIn("prediction_trace", trace["tags"])
        self.assertEqual(trace["metadata"]["league"], "L1")
        self.assertEqual(trace["metadata"]["fact_ref_count"], 3)
        self.assertTrue(trace["replayable"])
        self.assertEqual(trace["replay_input_ref"]["state_snapshot_ref"], trace["state_snapshot_ref"])
        self.assertTrue(str(trace["replay_seed"]).startswith("seed_"))
        self.assertEqual(trace["eval_suite_version"], "strategy_eval_v1")
        self.assertEqual(trace["evidence_coverage_ratio"], 1.0)
        self.assertEqual(trace["retrieval_hit_rate"], 1.0)
        self.assertEqual(trace["tool_failure_rate"], 0.0)
        self.assertFalse(trace["hallucination_flag"])
        self.assertTrue(trace["report_grounded_flag"])
        self.assertIn("prediction_confidence", trace["scores"])
        self.assertTrue(any(item["type"] == "agent" for item in trace["observations"]))
        self.assertTrue(any(item["type"] == "tool" for item in trace["observations"]))
        self.assertTrue(any(item["type"] == "retrieval" for item in trace["observations"]))
        self.assertEqual(trace["decision"]["recommendation"], "home")
        self.assertEqual(trace["nodes"][0]["span_id"], "agent-01")
        self.assertEqual(trace["nodes"][0]["parent_id"], "supervisor")
        self.assertEqual(trace["tool_calls"][0]["name"], "manual_market_review")
        self.assertTrue(any(item["ref_id"] == "match_source" for item in trace["evidence_refs"]))
        self.assertTrue(any(item["ref_id"] == "market_entropy" for item in trace["evidence_refs"]))
        self.assertTrue(any(item["kind"] == "fact_ref" for item in trace["evidence_refs"]))

    def test_build_prediction_trace_envelope_preserves_existing_metadata(self) -> None:
        match = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="19:35",
            match_date="2026-05-18",
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.1,
        )
        trace = build_prediction_trace_envelope(
            match=match,
            prediction={
                "recommendation": "draw",
                "trace": {
                    "trace_id": "trc_existing",
                    "session_id": "ses_existing",
                    "prompt_name": "custom_prompt",
                    "prompt_version": "custom_v2",
                    "workflow_version": "custom_workflow_v2",
                    "scores": {"manual_score": {"value": 1.0}},
                    "tags": ["replay"],
                    "replayable": False,
                    "fact_refs": [
                        {
                            "ref_id": "fact_existing",
                            "kind": "match_fact",
                            "schema_version": "match_fact_v1",
                            "match_id": match.match_id,
                        }
                    ],
                },
            },
            generated_at=datetime(2026, 5, 18, 10, 0, 1),
        )

        self.assertEqual(trace["trace_id"], "trc_existing")
        self.assertEqual(trace["session_id"], "ses_existing")
        self.assertEqual(trace["prompt_name"], "custom_prompt")
        self.assertEqual(trace["prompt_version"], "custom_v2")
        self.assertEqual(trace["workflow_version"], "custom_workflow_v2")
        self.assertEqual(trace["scores"]["manual_score"]["value"], 1.0)
        self.assertIn("replay", trace["tags"])
        self.assertFalse(trace["replayable"])
        self.assertTrue(any(item["ref_id"] == "fact_existing" for item in trace["fact_refs"]))


if __name__ == "__main__":
    unittest.main()
