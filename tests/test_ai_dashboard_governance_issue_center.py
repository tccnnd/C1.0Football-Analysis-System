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

from v24_app.ai_dashboard import DashboardRow, build_main_flow_governance_issue_detail_text
from v24_app.core import AppMatch
from v24_app.ui_modules import build_main_flow_governance_status


class AIDashboardGovernanceIssueCenterTests(unittest.TestCase):
    def _match(self) -> AppMatch:
        return AppMatch(
            home_team="Alpha",
            away_team="Beta",
            league="Premier",
            match_time="19:35",
            match_date="2026-05-10",
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.2,
        )

    def _prediction(self) -> dict:
        return {
            "risk_level": "high",
            "confidence": 0.61,
            "recommendation": "home",
            "top_play": "market_1x2",
            "play_type": "market_1x2",
            "strategy_admission": {
                "decision": "allow",
                "label": "正式放行",
                "release_allowed": True,
                "top_play": "market_1x2",
                "top_pick": "home",
            },
        }

    def test_issue_detail_text_includes_governance_chain_and_context(self) -> None:
        row = DashboardRow(match=self._match(), prediction=self._prediction())
        governance = build_main_flow_governance_status(
            prediction=row.prediction,
            c1_release_row={},
            play_policy_status={"takeover_gate": {"status": "allow"}},
            recovery_loop={"health": "good"},
            match_id="m1",
        )

        text = build_main_flow_governance_issue_detail_text(row, governance)

        self.assertIn("对阵：Alpha vs Beta", text)
        self.assertIn("问题上下文", text)
        self.assertIn("主玩法：market_1x2", text)
        self.assertIn("策略准入：正式放行", text)
        self.assertIn("治理链路", text)
        self.assertIn("Main Flow Governance", text)
        self.assertIn("Primary blocker", text)
        self.assertIn("Recommendation", text)


if __name__ == "__main__":
    unittest.main()
