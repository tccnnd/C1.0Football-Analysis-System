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
        self.assertEqual(trace["prompt_version"], "strategy_report_v1")
        self.assertEqual(trace["status"], "alert")
        self.assertEqual(trace["latency_ms"], 123.457)
        self.assertEqual(trace["decision"]["recommendation"], "home")
        self.assertEqual(trace["nodes"][0]["span_id"], "agent-01")
        self.assertEqual(trace["nodes"][0]["parent_id"], "supervisor")
        self.assertEqual(trace["tool_calls"][0]["name"], "manual_market_review")
        self.assertTrue(any(item["ref_id"] == "match_source" for item in trace["evidence_refs"]))
        self.assertTrue(any(item["ref_id"] == "market_entropy" for item in trace["evidence_refs"]))


if __name__ == "__main__":
    unittest.main()
