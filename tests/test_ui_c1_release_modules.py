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
from v24_app.ui_modules import (
    build_c1_mark_apply_plan,
    build_c1_rows_from_marks,
    build_formal_release_rows,
    build_release_allowlist_lines,
    classify_suggested_action_for_tree,
    comparison_window_row_values,
    collect_release_allowed_match_ids,
    compute_pending_match_ids,
    filter_comparison_rows,
    filter_release_rows,
    find_release_row,
    format_release_candidate_text,
    release_window_row_values,
    resolve_release_gate_pick,
    summarize_c1_rows,
)


class UIC1ReleaseModuleTests(unittest.TestCase):
    def test_build_c1_rows_from_marks(self) -> None:
        match_a = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="19:35",
            match_date="2026-04-04",
            odds_home=1.8,
            odds_draw=3.3,
            odds_away=4.3,
        )
        match_b = AppMatch(
            home_team="C",
            away_team="D",
            league="L2",
            match_time="20:00",
            match_date="2026-04-04",
            odds_home=2.0,
            odds_draw=3.1,
            odds_away=3.8,
        )
        marks = {
            match_a.match_id: {"suggested_action": "可放行"},
            match_b.match_id: {"suggested_action": "阻断"},
        }
        predictions = {
            match_a.match_id: {"recommendation": "主胜", "confidence": 0.61},
            match_b.match_id: {"recommendation": "客胜", "confidence": 0.57},
        }
        priority = {"阻断": 0, "可放行": 5}
        rows = build_c1_rows_from_marks(
            matches=[match_a, match_b],
            marks=marks,
            predictions=predictions,
            action_priority_fn=lambda action: priority.get(action, 99),
        )
        self.assertEqual(rows[0]["match_id"], match_b.match_id)
        self.assertEqual(rows[1]["match_id"], match_a.match_id)
        self.assertAlmostEqual(float(rows[1]["v24_confidence"]), 0.61)

    def test_summarize_rows_and_release_helpers(self) -> None:
        rows = [
            {
                "match_id": "m1",
                "governance_action": "BLOCK",
                "suggested_action": "阻断",
                "governance_reason_codes": ["INFO_LOW", "MARKET_DIVERGE"],
                "side_diverged": True,
                "near_block": True,
                "release_allowed": False,
            },
            {
                "match_id": "m2",
                "governance_action": "APPROVE",
                "suggested_action": "可放行",
                "governance_reason_codes": ["OK"],
                "side_diverged": False,
                "near_block": False,
                "release_allowed": True,
            },
        ]
        summary = summarize_c1_rows(rows)
        self.assertEqual(summary["governance_counts"]["BLOCK"], 1)
        self.assertEqual(summary["reason_code_counts"]["OK"], 1)
        self.assertEqual(summary["side_divergence_count"], 1)
        self.assertEqual(summary["blocked_count"], 1)
        self.assertEqual(summary["near_block_count"], 1)
        self.assertEqual(find_release_row(rows, "m2")["match_id"], "m2")
        self.assertEqual(collect_release_allowed_match_ids(rows), {"m2"})

    def test_resolve_release_gate_pick(self) -> None:
        prediction = {"recommendation": "主胜"}
        self.assertEqual(
            resolve_release_gate_pick(gate_active=False, prediction=prediction, row={}),
            "主胜",
        )
        self.assertEqual(
            resolve_release_gate_pick(
                gate_active=True,
                prediction=prediction,
                row={"release_allowed": False, "governance_action": "block"},
            ),
            "阻断",
        )
        self.assertEqual(
            resolve_release_gate_pick(
                gate_active=True,
                prediction=prediction,
                row={"release_allowed": False, "primary_reason_code": "LINEUP_MISSING"},
            ),
            "待补阵容",
        )
        self.assertEqual(
            resolve_release_gate_pick(
                gate_active=True,
                prediction=prediction,
                row={"release_allowed": False, "primary_reason_code": "OTHER"},
            ),
            "观察",
        )

    def test_release_candidate_and_formal_rows(self) -> None:
        self.assertEqual(
            format_release_candidate_text({"top_play": "1x2", "top_selection": "DRAW"}),
            "平局",
        )
        self.assertEqual(
            format_release_candidate_text(
                {"top_play": "totals", "top_selection": "OVER", "top_line": ""},
                {"total_goals_value": 2.5},
            ),
            "OVER 2.5",
        )
        self.assertEqual(
            format_release_candidate_text({"top_play": "handicap", "top_selection": "HOME", "top_line": "-0.5"}),
            "HOME -0.5",
        )
        rows = [
            {
                "match_id": "m1",
                "match_label": "A vs B",
                "release_allowed": True,
                "top_play": "1x2",
                "top_selection": "HOME_WIN",
                "top_line": None,
                "top_confidence": 0.62,
                "provider_name": "provider",
                "primary_reason_code": "OK",
                "governance_action": "APPROVE",
                "release_action": "ALLOW",
            },
            {
                "match_id": "m2",
                "match_label": "C vs D",
                "release_allowed": False,
                "top_play": "1x2",
                "top_selection": "DRAW",
                "top_line": None,
                "top_confidence": 0.80,
            },
        ]
        formal = build_formal_release_rows(rows=rows, predictions={})
        self.assertEqual(len(formal), 1)
        self.assertEqual(formal[0]["official_pick"], "主胜")
        self.assertEqual(formal[0]["confidence"], 0.62)

    def test_build_release_allowlist_lines(self) -> None:
        lines = build_release_allowlist_lines(
            allow_rows=[
                {
                    "match_label": "A vs B",
                    "governance_action": "APPROVE",
                    "release_action": "ALLOW",
                    "top_play": "1x2",
                    "top_selection": "HOME_WIN",
                    "top_confidence": 0.66,
                    "provider_name": "provider",
                    "primary_reason_code": "OK",
                }
            ],
            summary={
                "governance_counts": {"APPROVE": 1},
                "release_counts": {"ALLOW": 1},
                "provider_counts": {"provider": 1},
            },
            generated_at=datetime(2026, 4, 4, 12, 30, 0),
        )
        payload = "\n".join(lines)
        self.assertIn("C1 Controlled Release Allowlist", payload)
        self.assertIn("A vs B", payload)
        self.assertIn("66.00%", payload)

    def test_release_and_comparison_filters_and_row_values(self) -> None:
        release_rows = [
            {"match_label": "A vs B", "release_allowed": True, "top_confidence": 0.71},
            {"match_label": "C vs D", "release_allowed": False, "top_confidence": 0.22},
        ]
        self.assertEqual(len(filter_release_rows(release_rows, "全部")), 2)
        self.assertEqual(len(filter_release_rows(release_rows, "可放行")), 1)
        self.assertEqual(len(filter_release_rows(release_rows, "保留")), 1)
        values = release_window_row_values(
            {
                "match_label": "A vs B",
                "governance_action": "APPROVE",
                "release_action": "ALLOW",
                "top_play": "1x2",
                "top_selection": "HOME_WIN",
                "top_confidence": 0.71,
                "provider_name": "provider",
                "primary_reason_code": "OK",
            }
        )
        self.assertEqual(values[0], "A vs B")
        self.assertEqual(values[5], "71.00%")

        comparison_rows = [
            {"suggested_action": "可放行", "match_label": "A vs B"},
            {"suggested_action": "阻断", "match_label": "C vs D"},
            {"suggested_action": "补阵容", "match_label": "E vs F"},
        ]
        self.assertEqual(len(filter_comparison_rows(comparison_rows, "全部")), 3)
        self.assertEqual(len(filter_comparison_rows(comparison_rows, "可放行")), 1)
        self.assertEqual(len(filter_comparison_rows(comparison_rows, "待处理")), 2)
        comparison_values = comparison_window_row_values(
            {
                "match_label": "A vs B",
                "v24_recommendation": "主胜",
                "v24_confidence": 0.66,
                "c1_predicted_side": "HOME_WIN",
                "c1_confidence": 0.61,
                "governance_action": "APPROVE",
                "suggested_action": "可放行",
                "primary_reason_code": "OK",
                "governance_reason_codes": ["OK", "STABLE"],
                "side_diverged": False,
                "near_block": False,
                "confidence_gap": 0.05,
            }
        )
        self.assertEqual(comparison_values[0], "A vs B")
        self.assertIn("66.00%", comparison_values[1])
        self.assertEqual(comparison_values[7], "N")

    def test_pending_ids_and_apply_plan(self) -> None:
        rows = [
            {"match_id": "m1", "suggested_action": "可放行"},
            {"match_id": "m2", "suggested_action": "补阵容"},
            {"match_id": "m3", "suggested_action": "接近阻断"},
            {"match_id": "m4", "suggested_action": "阻断"},
            {"match_id": "m5", "suggested_action": "观察"},
            {"match_id": "", "suggested_action": "阻断"},
        ]
        self.assertEqual(compute_pending_match_ids(rows), {"m2", "m3", "m4"})
        self.assertEqual(classify_suggested_action_for_tree("可放行"), ("c1_pass", "可放行"))
        self.assertEqual(classify_suggested_action_for_tree("补阵容"), ("c1_pending", "待处理"))
        self.assertEqual(classify_suggested_action_for_tree("接近阻断"), ("c1_pending", "待处理"))
        self.assertEqual(classify_suggested_action_for_tree("阻断"), ("c1_block", "阻断"))
        self.assertEqual(classify_suggested_action_for_tree("观察"), ("c1_observe", "观察"))

        marks_by_id, tags_by_id, buckets, applied = build_c1_mark_apply_plan(
            rows=rows,
            exists_fn=lambda match_id: match_id in {"m1", "m2", "m4", "m5"},
        )
        self.assertEqual(applied, 4)
        self.assertEqual(set(marks_by_id.keys()), {"m1", "m2", "m4", "m5"})
        self.assertEqual(tags_by_id["m2"], "c1_pending")
        self.assertEqual(tags_by_id["m4"], "c1_block")
        self.assertEqual(buckets["可放行"], 1)
        self.assertEqual(buckets["待处理"], 1)
        self.assertEqual(buckets["阻断"], 1)
        self.assertEqual(buckets["观察"], 1)


if __name__ == "__main__":
    unittest.main()
