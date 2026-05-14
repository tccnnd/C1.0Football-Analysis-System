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

from v24_app.ai_dashboard import (
    build_statsbomb_event_proxy_review_samples_message,
    build_statsbomb_event_proxy_review_text,
)


class AIDashboardStatsBombEventProxyTests(unittest.TestCase):
    def test_review_samples_message_includes_quality_and_repair_guidance(self) -> None:
        text = build_statsbomb_event_proxy_review_samples_message(
            {
                "generated_sample_count": 12,
                "skipped_reasons": {"missing_statsbomb": 2, "unknown_label": 1},
                "output_path": "data/state/statsbomb_review_training_samples.json",
            },
            {
                "status": "attention",
                "issue_count": 2,
                "label_rows": [
                    {
                        "label": "1X2错因标签",
                        "value": "8/12",
                        "detail": "hit=4 | miss=8 | miss_rate=66.7%",
                    }
                ],
                "weight_rows": [
                    {
                        "label": "终结波动",
                        "value": "1.35",
                        "detail": "仅用于Evaluation Agent错因排序",
                    }
                ],
                "issues": [
                    {
                        "code": "xgb_label_class_missing",
                        "severity": "warning",
                        "message": "补平局/客胜弱类别",
                        "recommendation": "补齐弱类别样本",
                    },
                    {
                        "code": "statsbomb_review_samples_missing",
                        "severity": "blocking",
                        "message": "先补样本",
                        "recommendation": "生成事件代理复盘样本",
                    },
                ],
                "leakage_note": "仅赛后使用，不能进入赛前特征",
            },
        )

        self.assertIn("样本: 12", text)
        self.assertIn("质量状态: attention | issues=2", text)
        self.assertIn("标签分布:", text)
        self.assertIn("1X2错因标签: 8/12", text)
        self.assertIn("事件错因权重:", text)
        self.assertIn("终结波动: 1.35", text)
        self.assertLess(text.index("先补样本"), text.index("补平局/客胜弱类别"))
        self.assertIn("仅赛后使用，不能进入赛前特征", text)

    def test_missing_event_summary_returns_fallback_guidance(self) -> None:
        text = build_statsbomb_event_proxy_review_text(
            {
                "match_id": "m-missing",
                "home_team": "Alpha",
                "away_team": "Bravo",
            }
        )

        self.assertIn("StatsBomb 事件代理复盘", text)
        self.assertIn("暂无事件代理数据", text)
        self.assertIn("不进入赛前预测特征", text)

    def test_event_summary_builds_proxy_review_without_pre_match_leakage(self) -> None:
        text = build_statsbomb_event_proxy_review_text(
            {
                "match_id": "m1",
                "home_team": "Bayer Leverkusen",
                "away_team": "Werder Bremen",
                "statsbomb_source_match_id": 3895302,
                "statsbomb_event_summary": {
                    "event_count": 4223,
                    "first_goal_minute": 25,
                    "last_goal_minute": 89,
                    "team_stats": {
                        "Bayer Leverkusen": {
                            "xg": 4.02,
                            "shots": 19,
                            "shots_on_target": 11,
                        },
                        "Werder Bremen": {
                            "xg": 0.28,
                            "shots": 8,
                            "shots_on_target": 2,
                        },
                    },
                },
            }
        )

        self.assertIn("source_type=event_proxy", text)
        self.assertIn("source_match_id: 3895302", text)
        self.assertIn("medium / events=4223", text)
        self.assertIn("Bayer Leverkusen 4.02 vs Werder Bremen 0.28 / diff 3.74", text)
        self.assertIn("射门: Bayer Leverkusen 19 vs Werder Bremen 8", text)
        self.assertIn("first=25 / last=89", text)
        self.assertIn("不进入赛前预测特征", text)


if __name__ == "__main__":
    unittest.main()
