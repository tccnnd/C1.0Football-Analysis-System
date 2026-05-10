from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.ui_modules import (
    build_agent_trace_nodes,
    format_agent_trace_detail,
    summarize_supervisor_trace,
)


class UIAgentTraceFlowModuleTests(unittest.TestCase):
    def test_build_agent_trace_nodes_formats_status_and_summary(self) -> None:
        supervisor = {
            "status": "alert",
            "next_actions": ["manual_market_review"],
            "agents": [
                {
                    "name": "DataHunter",
                    "status": "ready",
                    "trigger": "match_loaded",
                    "inputs": {"source": "live:titan"},
                    "outputs": {"history_samples": 3},
                },
                {
                    "name": "MarketEntropy",
                    "status": "alert",
                    "trigger": "market_signal_check",
                    "inputs": {"level": "HIGH"},
                    "outputs": {"signals": ["kelly_against_pick", "odds_velocity_alert"]},
                    "checks": ["entropy level", "Kelly span"],
                    "evidence": {"score": 0.84, "level": "HIGH"},
                    "rationale": "Market pressure is abnormal and requires review.",
                    "actions": ["manual_market_review"],
                },
                {
                    "name": "Simulation",
                    "status": "ready",
                    "trigger": "probability_fusion",
                    "outputs": {"recommendation": "home", "confidence": 0.68},
                },
            ],
        }

        nodes = build_agent_trace_nodes(supervisor)

        self.assertEqual(len(nodes), 3)
        self.assertEqual(nodes[1]["status_label"], "ALERT")
        self.assertEqual(nodes[1]["summary"], "Market pressure is abnormal and requires review.")
        self.assertEqual(nodes[2]["summary"], "pick home")
        self.assertIn("Kelly span", nodes[1]["checks"])
        self.assertEqual(nodes[1]["evidence"]["score"], 0.84)

        detail = format_agent_trace_detail(nodes[1])
        self.assertIn("MarketEntropy / ALERT", detail)
        self.assertIn("kelly_against_pick", detail)
        self.assertIn("checks: entropy level | Kelly span", detail)
        self.assertIn("actions: manual_market_review", detail)

        summary = summarize_supervisor_trace(supervisor)
        self.assertEqual(summary["status"], "alert")
        self.assertEqual(summary["status_counts"]["alert"], 1)
        self.assertEqual(summary["next_actions"], ["manual_market_review"])
        self.assertEqual(summary["agent_actions"], ["manual_market_review"])


if __name__ == "__main__":
    unittest.main()
