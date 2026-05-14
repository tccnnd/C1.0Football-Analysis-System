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

from v24_app.ai_dashboard import (
    build_statsbomb_event_proxy_review_samples_message,
    build_statsbomb_event_proxy_review_text,
    build_statsbomb_review_training_action_feedback,
    build_statsbomb_review_training_action_rows,
    build_statsbomb_review_training_feedback_rows,
    build_statsbomb_review_training_quality_export_message,
    build_video_review_evidence_gap_action_rows,
    build_video_review_evidence_gap_batch_plan_export_message,
    build_video_review_evidence_gap_batch_plan_filename,
    build_video_review_evidence_gap_batch_plan_lines,
    build_video_review_evidence_gap_feedback,
    build_video_review_evidence_gap_feedback_rows,
)


class AIDashboardStatsBombEventProxyTests(unittest.TestCase):
    def test_video_review_evidence_gap_action_rows_only_include_missing_evidence(self) -> None:
        rows = build_video_review_evidence_gap_action_rows(
            [
                {
                    "match_id": "video-ready",
                    "match_date": "2026-05-14",
                    "league": "League A",
                    "home_team": "Alpha",
                    "away_team": "Bravo",
                    "video_review": {"video": {"source_type": "external_reference", "url": "https://example.com/replay"}},
                },
                {
                    "match_id": "event-proxy-ready",
                    "match_date": "2026-05-15",
                    "league": "League A",
                    "home_team": "Charlie",
                    "away_team": "Delta",
                    "statsbomb_event_summary": {"event_count": 1000},
                },
                {
                    "match_id": "sample-proxy-ready",
                    "match_date": "2026-05-16",
                    "league": "League B",
                    "home_team": "Echo",
                    "away_team": "Foxtrot",
                },
                {
                    "match_id": "missing-evidence",
                    "match_date": "2026-05-17",
                    "league": "League B",
                    "home_team": "Golf",
                    "away_team": "Hotel",
                },
            ],
            {
                "items": [
                    {
                        "meta": {
                            "source": "statsbomb_event_sandbox",
                            "match_id": "sample-proxy-ready",
                        }
                    }
                ]
            },
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["match_id"], "missing-evidence")
        self.assertEqual(rows[0]["action_key"], "bind_external_reference")
        self.assertIn("优先绑定合法回放链接", rows[0]["body"])
        self.assertIn("低置信复盘", rows[0]["body"])
        self.assertIn("priority_score", rows[0])

    def test_video_review_evidence_gap_action_rows_prioritize_high_value_misses(self) -> None:
        rows = build_video_review_evidence_gap_action_rows(
            [
                {
                    "match_id": "recent-normal",
                    "match_date": "2026-05-20",
                    "league": "League B",
                    "home_team": "Recent",
                    "away_team": "Normal",
                },
                {
                    "match_id": "high-conf-miss",
                    "match_date": "2026-05-18",
                    "league": "FIFA World Cup",
                    "home_team": "High",
                    "away_team": "Miss",
                    "is_correct": False,
                    "prediction_confidence": 0.72,
                },
                {
                    "match_id": "strategy-miss",
                    "match_date": "2026-05-19",
                    "league": "League A",
                    "home_team": "Strategy",
                    "away_team": "Miss",
                    "high_accuracy_strategy_items": [{"is_hit": False, "confidence": 0.71}],
                    "strategy_allowlist_decision": "allow",
                },
            ]
        )

        self.assertEqual([row["match_id"] for row in rows], ["high-conf-miss", "strategy-miss", "recent-normal"])
        self.assertGreater(rows[0]["priority_score"], rows[1]["priority_score"])
        self.assertEqual(rows[0]["priority_label"], "P1")
        self.assertIn("高置信1X2失误", rows[0]["priority_reasons"])
        self.assertIn("重点赛事", rows[0]["priority_reasons"])
        self.assertIn("优先级 P1", rows[0]["body"])

    def test_video_review_evidence_gap_batch_plan_filename_is_stable(self) -> None:
        self.assertEqual(
            build_video_review_evidence_gap_batch_plan_filename(datetime(2026, 5, 14, 12, 3, 4)),
            "video_review_evidence_gap_batch_plan_20260514_120304.md",
        )

    def test_video_review_evidence_gap_batch_plan_lines_include_priority_and_boundaries(self) -> None:
        rows = build_video_review_evidence_gap_action_rows(
            [
                {
                    "match_id": "high-conf-miss",
                    "match_date": "2026-05-18",
                    "league": "FIFA World Cup",
                    "home_team": "High",
                    "away_team": "Miss",
                    "is_correct": False,
                    "prediction_confidence": 0.72,
                },
                {
                    "match_id": "strategy-miss",
                    "match_date": "2026-05-19",
                    "league": "League A",
                    "home_team": "Strategy",
                    "away_team": "Miss",
                    "high_accuracy_strategy_items": [{"is_hit": False, "confidence": 0.71}],
                    "strategy_allowlist_decision": "allow",
                },
            ],
            limit=2,
        )

        text = "\n".join(
            build_video_review_evidence_gap_batch_plan_lines(
                rows,
                generated_at=datetime(2026, 5, 14, 12, 0, 0),
            )
        )

        self.assertIn("Total Gap Rows: 2", text)
        self.assertIn("| P1 | 72 | 2026-05-18 | FIFA World Cup | High vs Miss | high-conf-miss |", text)
        self.assertIn("高置信1X2失误", text)
        self.assertIn("重点赛事", text)
        self.assertIn("优先绑定合法回放链接", text)
        self.assertIn("legal replay links only", text)
        self.assertIn("no auto video download", text)
        self.assertIn("post-match review evidence only", text)
        self.assertIn("pre-match features", text)

    def test_video_review_evidence_gap_batch_plan_lines_handle_empty_rows(self) -> None:
        text = "\n".join(
            build_video_review_evidence_gap_batch_plan_lines(
                [],
                generated_at=datetime(2026, 5, 14, 12, 0, 0),
            )
        )

        self.assertIn("Total Gap Rows: 0", text)
        self.assertIn("当前没有待处理证据缺口", text)
        self.assertIn("legal replay links only", text)

    def test_video_review_evidence_gap_batch_plan_export_message_summarizes_path(self) -> None:
        text = build_video_review_evidence_gap_batch_plan_export_message(
            Path("reports/video_review_evidence_gap_batch_plan_20260514_120304.md"),
            [{"match_id": "gap-1"}, {"match_id": "gap-2"}],
        )

        self.assertIn("复盘证据缺口批次计划已导出", text)
        self.assertIn("video_review_evidence_gap_batch_plan_20260514_120304.md", text)
        self.assertIn("待处理: 2 场", text)
        self.assertIn("不自动下载视频", text)

    def test_video_review_evidence_gap_feedback_tracks_external_reference_resolution(self) -> None:
        feedback = build_video_review_evidence_gap_feedback(
            {
                "match_id": "gap-1",
                "match_date": "2026-05-18",
                "league": "League C",
                "home_team": "India",
                "away_team": "Juliet",
            },
            {"ok": True, "review": {"review_id": "vr-gap-1"}},
            source_name="FIFA+ Archive",
        )

        self.assertEqual(feedback["action_key"], "bind_external_reference")
        self.assertEqual(feedback["match_id"], "gap-1")
        self.assertEqual(feedback["before_kind"], "missing_evidence")
        self.assertEqual(feedback["after_kind"], "external_reference")
        self.assertEqual(feedback["outcome"], "resolved")
        self.assertEqual(feedback["tone"], "good")
        self.assertEqual(feedback["source_name"], "FIFA+ Archive")
        self.assertEqual(feedback["review_id"], "vr-gap-1")

    def test_video_review_evidence_gap_feedback_rows_format_history(self) -> None:
        rows = build_video_review_evidence_gap_feedback_rows(
            [
                {
                    "occurred_at": "2026-05-14 12:00:00",
                    "title": "League C | India vs Juliet",
                    "outcome": "resolved",
                    "summary_text": "missing_evidence->external_reference",
                    "source_name": "FIFA+ Archive",
                    "review_id": "vr-gap-1",
                    "next_recommendation": "annotate events",
                    "tone": "good",
                }
            ]
        )

        self.assertEqual(rows[0]["tone"], "good")
        self.assertIn("resolved", rows[0]["title"])
        self.assertIn("FIFA+ Archive", rows[0]["body"])
        self.assertIn("annotate events", rows[0]["body"])

    def test_review_training_quality_export_message_summarizes_report(self) -> None:
        text = build_statsbomb_review_training_quality_export_message(
            Path("reports/statsbomb_review_training_quality_20260514_120000.md"),
            {"status": "attention", "sample_count": 18, "issue_count": 2},
            3,
        )

        self.assertIn("StatsBomb/Event Proxy 样本质量报告已导出", text)
        self.assertIn("质量状态: attention", text)
        self.assertIn("样本: 18", text)
        self.assertIn("问题数: 2", text)
        self.assertIn("修复记录: 3", text)

    def test_review_training_action_feedback_summarizes_quality_delta(self) -> None:
        feedback = build_statsbomb_review_training_action_feedback(
            "build_statsbomb_review_samples",
            {
                "status": "blocked",
                "sample_count": 0,
                "issue_count": 2,
                "issues": [{"code": "statsbomb_review_samples_missing"}],
            },
            {
                "status": "attention",
                "sample_count": 18,
                "issue_count": 1,
                "issues": [{"code": "statsbomb_review_sample_count_low", "recommendation": "继续补样本"}],
            },
            {"ok": True, "message": "done"},
        )

        self.assertEqual(feedback["outcome"], "improved")
        self.assertEqual(feedback["tone"], "good")
        self.assertEqual(feedback["sample_delta"], 18)
        self.assertEqual(feedback["issue_delta"], -1)
        self.assertIn("blocked->attention", feedback["summary_text"])
        self.assertEqual(feedback["next_recommendation"], "继续补样本")

    def test_review_training_action_feedback_supports_recovery_rebuild(self) -> None:
        feedback = build_statsbomb_review_training_action_feedback(
            "recover_results_rebuild_samples",
            {"status": "attention", "sample_count": 8, "issue_count": 2, "issues": []},
            {"status": "healthy", "sample_count": 24, "issue_count": 0, "issues": []},
            {"ok": True, "message": "result recovery completed"},
        )

        self.assertEqual(feedback["outcome"], "improved")
        self.assertEqual(feedback["after_status"], "healthy")
        self.assertEqual(feedback["sample_delta"], 16)
        self.assertEqual(feedback["next_recommendation"], "质量已恢复健康，可进入回测/训练稳定性验证。")

    def test_review_training_action_feedback_marks_failed_and_queued(self) -> None:
        quality = {"status": "attention", "sample_count": 10, "issue_count": 1, "issues": []}
        failed = build_statsbomb_review_training_action_feedback(
            "build_statsbomb_review_samples",
            quality,
            quality,
            {"ok": False, "message": "boom"},
        )
        queued = build_statsbomb_review_training_action_feedback(
            "recover_results",
            quality,
            quality,
            {"ok": True, "queued": True},
        )

        self.assertEqual(failed["outcome"], "failed")
        self.assertEqual(failed["tone"], "bad")
        self.assertEqual(queued["outcome"], "queued")
        self.assertEqual(queued["tone"], "neutral")

    def test_review_training_feedback_rows_format_recent_records(self) -> None:
        rows = build_statsbomb_review_training_feedback_rows(
            [
                {
                    "occurred_at": "2026-05-14 12:00:00",
                    "action_key": "build_statsbomb_review_samples",
                    "outcome": "improved",
                    "summary_text": "samples 0->18",
                    "after_issue_codes": ["statsbomb_review_sample_count_low"],
                    "next_recommendation": "继续补样本",
                    "tone": "good",
                }
            ]
        )

        self.assertEqual(rows[0]["tone"], "good")
        self.assertIn("build_statsbomb_review_samples", rows[0]["title"])
        self.assertIn("samples 0->18", rows[0]["body"])
        self.assertIn("继续补样本", rows[0]["body"])

    def test_review_training_action_rows_map_issues_to_executable_actions(self) -> None:
        rows = build_statsbomb_review_training_action_rows(
            {
                "status": "blocked",
                "sample_count": 0,
                "issues": [
                    {
                        "code": "prediction_miss_skewed",
                        "severity": "warning",
                        "message": "标签偏斜",
                        "recommendation": "补齐弱类别样本",
                    },
                    {
                        "code": "statsbomb_review_samples_missing",
                        "severity": "blocking",
                        "message": "样本为空",
                        "recommendation": "生成复盘样本",
                    },
                    {
                        "code": "statsbomb_review_features_missing",
                        "severity": "warning",
                        "message": "缺少特征",
                        "recommendation": "重建特征",
                    },
                ],
            }
        )

        self.assertEqual(rows[0]["action_key"], "build_statsbomb_review_samples")
        self.assertEqual(rows[0]["tone"], "danger")
        self.assertIn("点击后会重建 StatsBomb/Event Proxy", rows[0]["body"])
        self.assertEqual(rows[1]["action_key"], "recover_results")
        self.assertIn("回收后再生成事件代理复盘样本", rows[1]["body"])
        self.assertEqual(len({row["action_key"] for row in rows}), len(rows))

    def test_review_training_action_rows_offer_backtest_when_healthy(self) -> None:
        rows = build_statsbomb_review_training_action_rows(
            {
                "status": "healthy",
                "sample_count": 42,
                "issues": [],
            }
        )

        self.assertEqual(rows[0]["action_key"], "run_high_accuracy_strategy_backtest")
        self.assertEqual(rows[0]["tone"], "good")
        self.assertIn("42", rows[0]["body"])

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
