from __future__ import annotations

import math
import json
import re
import shutil
import threading
import tkinter as tk
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .background_tasks import BackgroundTaskCenter, BackgroundTaskRecord
from .core import (
    AppMatch,
    apply_draw_release_guard_policy_update,
    apply_strategy_admission_policy_update,
    auto_settle_finished_matches,
    build_historical_strategy_replay_samples,
    build_result_recovery_snapshot_audit,
    add_video_review_annotation,
    create_video_review,
    create_video_review_reference,
    extract_video_review_frames_now,
    export_play_model_takeover_gate_audit_report as export_play_model_takeover_gate_audit_report_now,
    export_video_review_fewshot_samples_now,
    fetch_matches_v24,
    get_draw_specialist_backtest_status,
    get_draw_release_guard_policy_history,
    get_draw_release_guard_policy_status,
    get_play_model_policy_status,
    get_play_model_training_status,
    get_high_accuracy_strategy_status,
    get_recent_settlements,
    get_video_review_for_match,
    get_video_review_fewshot_memory,
    repair_training_data_health,
    get_result_recovery_runs,
    get_statsbomb_event_baseline,
    get_statsbomb_review_training_samples,
    get_statsbomb_sandbox_fewshot_memory,
    get_strategy_admission_policy_status,
    get_strategy_admission_policy_history,
    invalidate_statsbomb_state_cache,
    load_c1_comparison_marks_cache,
    mark_strategy_allowlist_snapshots,
    persist_prediction_snapshots,
    predict_match,
    record_result_recovery_run,
    rollback_strategy_admission_policy,
    rollback_draw_release_guard_policy,
    run_draw_specialist_backtest,
    run_high_accuracy_strategy_backtest,
    run_play_model_backtest,
    VIDEO_REVIEW_FEWSHOT_MEMORY_FILE,
    STATSBOMB_SANDBOX_FEWSHOT_FILE,
    STATSBOMB_REVIEW_TRAINING_FILE,
    train_play_models_now,
    warmup_prediction_models,
)
from .ui_modules import (
    build_background_task_rows,
    build_background_task_detail_lines,
    build_background_task_group_rows,
    build_background_task_summary,
    build_background_task_stability_cards,
    build_background_task_stability_summary,
    build_high_accuracy_strategy_backtest_message,
    build_high_accuracy_strategy_backtest_status_text,
    build_draw_specialist_backtest_apply_status_text,
    build_draw_specialist_backtest_card_rows,
    build_draw_specialist_backtest_status_text,
    build_draw_specialist_backtest_success_message,
    build_play_model_backtest_apply_status_text,
    build_play_model_backtest_success_message,
    build_play_model_takeover_gate_audit_export_message,
    build_play_model_takeover_gate_audit_export_status_text,
    build_play_model_policy_decision_rows,
    build_play_model_policy_status_text,
    build_play_model_training_status_text,
    build_train_play_models_apply_message,
    build_train_play_models_apply_status_text,
    build_result_recovery_quality_alerts,
    build_result_recovery_review_summary,
    build_result_recovery_run_detail,
    build_result_recovery_run_rows,
    build_result_recovery_run_summary,
    build_result_recovery_strategy_adjustment,
    build_strategy_release_quality_trend,
    build_strategy_release_quality_trend_alerts,
    build_strategy_release_trend_policy_tuning,
    build_agent_trace_nodes,
    mark_stale_result_recovery_runs,
    format_agent_trace_detail,
    build_high_accuracy_strategy_dashboard,
    build_high_accuracy_live_feedback_summary,
    build_high_accuracy_live_feedback_recovery_validation,
    build_strategy_allowlist_settlement_summary,
    build_strategy_allowlist_tuning_recommendation,
    build_statsbomb_event_sandbox_report_filename,
    build_statsbomb_event_sandbox_report_lines,
    build_statsbomb_event_sandbox_summary,
    build_statsbomb_review_training_quality_report_filename,
    build_statsbomb_review_training_quality_report_lines,
    build_statsbomb_review_training_quality_summary,
    build_video_review_source_coverage_summary,
    build_statsbomb_fewshot_backfill_report_filename,
    build_statsbomb_fewshot_backfill_report_lines,
    build_statsbomb_fewshot_draft_filename,
    build_statsbomb_fewshot_draft_payload,
    build_statsbomb_fewshot_draft_review_filename,
    build_statsbomb_fewshot_draft_review_lines,
    build_statsbomb_fewshot_merge_plan,
    build_statsbomb_fewshot_merge_plan_filename,
    build_statsbomb_fewshot_merge_plan_lines,
    build_statsbomb_fewshot_merge_bundle,
    build_statsbomb_fewshot_merge_bundle_filename,
    build_statsbomb_fewshot_merge_bundle_report_filename,
    build_statsbomb_fewshot_merge_bundle_report_lines,
    build_statsbomb_fewshot_merge_apply_preview,
    build_statsbomb_fewshot_merge_apply_preview_filename,
    build_statsbomb_fewshot_merge_apply_preview_lines,
    build_statsbomb_fewshot_merge_apply_report_filename,
    build_statsbomb_fewshot_merge_apply_report_lines,
    build_statsbomb_fewshot_merge_apply_result,
    build_statsbomb_fewshot_memory_rollback_preview,
    build_statsbomb_fewshot_memory_rollback_report_filename,
    build_statsbomb_fewshot_memory_rollback_report_lines,
    build_statsbomb_fewshot_memory_audit_report,
    build_statsbomb_fewshot_memory_audit_report_filename,
    build_statsbomb_fewshot_memory_audit_report_lines,
    build_statsbomb_fewshot_memory_monitor,
    build_statsbomb_fewshot_memory_quality_alerts,
    build_video_review_fewshot_draft_review_filename,
    build_video_review_fewshot_draft_review_lines,
    build_video_review_fewshot_merge_apply_preview,
    build_video_review_fewshot_merge_apply_preview_filename,
    build_video_review_fewshot_merge_apply_preview_lines,
    build_video_review_fewshot_merge_apply_report_filename,
    build_video_review_fewshot_merge_apply_report_lines,
    build_video_review_fewshot_merge_apply_result,
    build_video_review_fewshot_action_rows,
    build_video_review_fewshot_health_card_rows,
    build_video_review_fewshot_memory_audit_report,
    build_video_review_fewshot_memory_audit_report_filename,
    build_video_review_fewshot_memory_audit_report_lines,
    build_video_review_fewshot_memory_health_summary,
    build_video_review_fewshot_memory_monitor,
    build_video_review_fewshot_memory_quality_alerts,
    build_video_review_fewshot_memory_rollback_preview,
    build_video_review_fewshot_memory_rollback_report_filename,
    build_video_review_fewshot_memory_rollback_report_lines,
    build_video_review_fewshot_merge_bundle,
    build_video_review_fewshot_merge_bundle_filename,
    build_video_review_fewshot_merge_bundle_report_filename,
    build_video_review_fewshot_merge_bundle_report_lines,
    build_video_review_fewshot_merge_plan,
    build_video_review_fewshot_merge_plan_filename,
    build_video_review_fewshot_merge_plan_lines,
    build_strategy_allowlist_filename,
    build_strategy_allowlist_report_lines,
    build_strategy_policy_audit_csv_filename,
    build_strategy_policy_audit_csv_text,
    build_strategy_policy_audit_report_filename,
    build_strategy_policy_audit_report_lines,
    build_strategy_policy_effect_review,
    build_strategy_policy_freeze_override_status,
    build_strategy_policy_freeze_alerts,
    build_strategy_policy_governance_event_summary,
    build_strategy_policy_rollback_effect_review,
    build_strategy_policy_rollback_preview,
    build_strategy_trend_tuning_effect_review,
    build_strategy_policy_tuning_guard,
    build_draw_release_guard_rollback_effect_review,
    build_draw_release_guard_freeze_override_status,
    build_draw_release_guard_tuning_guard,
    build_strategy_release_recovery_loop_report_filename,
    build_strategy_release_recovery_loop_report_lines,
    build_strategy_release_recovery_alerts,
    build_strategy_release_recovery_loop,
    build_strategy_release_pool_rows,
    build_c1_rows_from_marks,
    filter_main_flow_governance_rows,
    build_main_flow_governance_status,
    build_main_flow_governance_status_text,
    find_release_row,
    compute_strategy_admission_counts,
    filter_strategy_admission_rows,
    format_high_accuracy_strategy_release_explanation,
    format_strategy_admission_pick,
    format_strategy_admission_reasons,
    format_strategy_admission_replay_guard,
    format_strategy_admission_thresholds,
    dashboard_report_type_options,
    filter_dashboard_report_rows,
    list_dashboard_report_files,
    summarize_dashboard_report_types,
    select_strategy_allowlist_rows,
    summarize_main_flow_governance_statuses,
)


BG = "#070d16"
PANEL = "#0c1420"
PANEL_2 = "#111b29"
SIDEBAR = "#0c111c"
BORDER = "#1c2a3a"
TEXT = "#e8eef8"
MUTED = "#94a3b8"
BLUE = "#4f6ef7"
GREEN = "#54d37c"
YELLOW = "#ffd84d"
RED = "#ef5b57"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports"
SETTINGS_PATH = PROJECT_ROOT / "data" / "state" / "ai_dashboard_settings.json"
STATSBOMB_REVIEW_REPAIR_ACTION_LOG = PROJECT_ROOT / "data" / "state" / "statsbomb_review_repair_action_log.json"
VIDEO_REVIEW_EVIDENCE_GAP_ACTION_LOG = PROJECT_ROOT / "data" / "state" / "video_review_evidence_gap_action_log.json"
VIDEO_REVIEW_EVIDENCE_GAP_BATCH_STATE = PROJECT_ROOT / "data" / "state" / "video_review_evidence_gap_batches.json"


def build_video_review_workflow_action_rows(
    import_review,
    annotate_video_event,
    export_samples,
    preview_merge_bundle,
    apply_memory,
) -> list[dict[str, object]]:
    return [
        {
            "code": "import_selected_video_review",
            "title": "导入所选视频复盘",
            "body": "把当前选中的赛事实例导入复盘中心，建立后续标注上下文。",
            "command": import_review,
        },
        {
            "code": "annotate_video_event",
            "title": "标注视频事件",
            "body": "为已导入的视频复盘补录事件标签与时间点。",
            "command": annotate_video_event,
        },
        {
            "code": "export_video_fewshot_samples",
            "title": "导出 few-shot 样本",
            "body": "生成审查稿、合并计划和可应用包。",
            "command": export_samples,
        },
        {
            "code": "preview_video_merge_bundle",
            "title": "预览合并包",
            "body": "对 bundle 做 dry-run 预览，查看追加和跳过明细。",
            "command": preview_merge_bundle,
        },
        {
            "code": "apply_video_memory",
            "title": "应用视频记忆",
            "body": "把审核通过的 few-shot 样本写入正式视频记忆池并保留备份。",
            "command": apply_memory,
        },
    ]


@dataclass
class DashboardRow:
    match: AppMatch
    prediction: dict


def build_main_flow_governance_issue_detail_text(
    row: DashboardRow,
    governance_status: dict | None = None,
) -> str:
    match = row.match
    pred = row.prediction
    admission = _admission_payload(pred)
    draw_guard_label, _draw_guard_body, _draw_guard_tone = _draw_release_guard_summary(pred)
    lines = [
        f"对阵：{match.home_team} vs {match.away_team}",
        f"联赛：{match.league}",
        f"开赛：{match.match_date} {match.match_time}",
        "",
        "问题上下文",
        f"- 风险等级：{_risk_label(pred.get('risk_level'))}",
        f"- 置信度：{_pct1(pred.get('confidence'))}",
        f"- 推荐策略：{_strategy_text(pred)}",
        f"- 策略准入：{_admission_text(pred)}",
        f"- 主玩法：{str(admission.get('top_play') or '-').strip() or '-'}",
        f"- 主选项：{str(admission.get('top_pick') or '-').strip() or '-'}",
        f"- 平局接管：{draw_guard_label}",
        f"- 比赛模式：{_competition_mode_label(pred)}",
        f"- 评分池：{_rating_pool_label(pred)}",
    ]
    if governance_status:
        lines.extend(["", "治理链路", build_main_flow_governance_status_text(governance_status)])
    return "\n".join(lines)


def _match_load_failure(match: AppMatch, stage: str, exc: Exception) -> dict[str, str]:
    return {
        "stage": stage,
        "match_id": str(getattr(match, "match_id", "-") or "-"),
        "league": str(getattr(match, "league", "-") or "-"),
        "home": str(getattr(match, "home_team", "-") or "-"),
        "away": str(getattr(match, "away_team", "-") or "-"),
        "error": str(exc) or exc.__class__.__name__,
    }


def _build_match_load_report(
    *,
    fetched_count: int,
    row_count: int,
    failures: list[dict[str, str]],
    source: str,
    elapsed: float | None = None,
    source_messages: list[str] | None = None,
    source_reports: list[dict] | None = None,
    cache_exists: bool = False,
    cache_fresh: bool = False,
    cache_date: str = "",
    cache_match_count: int = 0,
    cache_age_days: int | None = None,
    force_live: bool = False,
    cache_only: bool = False,
) -> dict[str, object]:
    predict_failures = sum(1 for item in failures if item.get("stage") == "predict")
    snapshot_failures = sum(1 for item in failures if item.get("stage") == "snapshot")
    status = "partial" if failures and row_count > 0 else "failed" if failures else "ok"
    return {
        "status": status,
        "source": source or "-",
        "fetched_count": max(0, int(fetched_count)),
        "row_count": max(0, int(row_count)),
        "failure_count": len(failures),
        "predict_failure_count": predict_failures,
        "snapshot_failure_count": snapshot_failures,
        "elapsed": elapsed,
        "failures": list(failures),
        "source_messages": list(source_messages or []),
        "source_reports": [dict(item) for item in source_reports or [] if isinstance(item, dict)],
        "cache_exists": bool(cache_exists),
        "cache_fresh": bool(cache_fresh),
        "cache_date": str(cache_date or ""),
        "cache_match_count": max(0, int(cache_match_count or 0)),
        "cache_age_days": cache_age_days,
        "force_live": bool(force_live),
        "cache_only": bool(cache_only),
    }


def _source_health_rows(load_report: dict[str, object] | None) -> list[dict[str, str]]:
    if not isinstance(load_report, dict):
        return []
    reports = load_report.get("source_reports", [])
    if not isinstance(reports, list):
        return []
    rows: list[dict[str, str]] = []
    status_labels = {
        "ready": "\u6b63\u5e38",
        "empty": "\u65e0\u8d5b\u4e8b",
        "error": "\u5931\u8d25",
        "guard_reject": "\u6821\u9a8c\u62d2\u7edd",
    }
    tones = {
        "ready": "good",
        "empty": "warning",
        "error": "bad",
        "guard_reject": "bad",
    }
    for item in reports:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "-")
        raw_count = int(item.get("raw_count", 0) or 0)
        valid_count = int(item.get("valid_count", 0) or 0)
        detail = f"raw {raw_count} / valid {valid_count}"
        if "coverage" in item:
            detail += f" / coverage {_pct1(item.get('coverage'))}"
        if "health_score" in item:
            detail += f" / score {int(item.get('health_score', 0) or 0)}"
        if item.get("error"):
            detail += f" / {item.get('error')}"
        rows.append(
            {
                "source": str(item.get("source") or "-"),
                "status": status_labels.get(status, status),
                "detail": detail,
                "tone": tones.get(status, "neutral"),
            }
        )
    return rows


def _source_health_summary(load_report: dict[str, object] | None) -> str:
    if not isinstance(load_report, dict):
        return "-"
    source = str(load_report.get("source") or "-")
    rows = _source_health_rows(load_report)
    ready = sum(1 for row in rows if row.get("tone") == "good")
    degraded = sum(1 for row in rows if row.get("tone") in {"warning", "bad"})
    if source == "cache_stale":
        return "\u5df2\u56de\u9000\u7f13\u5b58"
    if source == "cache":
        return "\u4f7f\u7528\u5f53\u65e5\u7f13\u5b58"
    if source.startswith("live:hybrid"):
        return f"\u591a\u6e90\u5408\u5e76 {ready} \u53ef\u7528"
    if ready and degraded:
        return f"\u5355\u6e90\u652f\u6491 / {degraded} \u6e90\u5f02\u5e38"
    if ready:
        return f"\u5728\u7ebf\u6e90\u6b63\u5e38 {ready}"
    if rows:
        return "\u5728\u7ebf\u6e90\u4e0d\u53ef\u7528"
    return source


def _cache_status_summary(load_report: dict[str, object] | None) -> str:
    if not isinstance(load_report, dict):
        return "-"
    if not load_report.get("cache_exists"):
        return "\u65e0\u7f13\u5b58"
    cache_date = str(load_report.get("cache_date") or "-")
    match_count = int(load_report.get("cache_match_count", 0) or 0)
    source = str(load_report.get("source") or "")
    if source == "cache_stale":
        return f"\u5df2\u56de\u9000 {cache_date} / {match_count} \u573a"
    if source == "cache":
        return f"\u6b63\u5728\u4f7f\u7528\u5f53\u65e5\u7f13\u5b58 / {match_count} \u573a"
    if load_report.get("cache_fresh"):
        return f"\u5f53\u65e5\u7f13\u5b58\u53ef\u56de\u9000 / {match_count} \u573a"
    age = load_report.get("cache_age_days")
    if isinstance(age, int) and 0 <= age <= 2:
        return f"\u6700\u8fd1\u7f13\u5b58\u53ef\u56de\u9000 {cache_date} / {match_count} \u573a"
    return f"\u7f13\u5b58\u8fc7\u671f {cache_date} / {match_count} \u573a"


def _cache_status_tone(load_report: dict[str, object] | None) -> str:
    if not isinstance(load_report, dict) or not load_report.get("cache_exists"):
        return "warning"
    source = str(load_report.get("source") or "")
    if source == "cache_stale":
        return "warning"
    if source == "cache":
        return "info"
    if load_report.get("cache_fresh"):
        return "good"
    age = load_report.get("cache_age_days")
    if isinstance(age, int) and 0 <= age <= 2:
        return "warning"
    return "bad"


def _cache_status_rows(load_report: dict[str, object] | None) -> list[tuple[str, str]]:
    if not isinstance(load_report, dict):
        return []
    age = load_report.get("cache_age_days")
    age_text = "-" if age is None else f"{age} \u5929"
    return [
        ("\u7f13\u5b58\u72b6\u6001", _cache_status_summary(load_report)),
        ("\u7f13\u5b58\u65e5\u671f", str(load_report.get("cache_date") or "-")),
        ("\u7f13\u5b58\u573a\u6b21", str(int(load_report.get("cache_match_count", 0) or 0))),
        ("\u7f13\u5b58\u5e74\u9f84", age_text),
        ("\u672c\u6b21\u5f3a\u5236\u5728\u7ebf", "\u662f" if load_report.get("force_live") else "\u5426"),
        ("\u672c\u6b21\u8bfb\u53d6\u7f13\u5b58", "\u662f" if load_report.get("cache_only") else "\u5426"),
    ]


def _build_dashboard_rows(matches: list[AppMatch]) -> tuple[list[DashboardRow], list[dict[str, str]]]:
    rows: list[DashboardRow] = []
    failures: list[dict[str, str]] = []
    snapshot_items: list[tuple[AppMatch, dict]] = []
    for match in matches:
        try:
            prediction = predict_match(match)
        except Exception as exc:
            failures.append(_match_load_failure(match, "predict", exc))
            continue
        snapshot_items.append((match, prediction))
        rows.append(DashboardRow(match, prediction))
    if snapshot_items:
        try:
            persist_prediction_snapshots(snapshot_items)
        except Exception as exc:
            failures.append(_match_load_failure(snapshot_items[0][0], "snapshot", exc))
    return rows, failures


def _pct(value: object) -> str:
    try:
        return f"{float(value):.0%}"
    except Exception:
        return "-"


def _pct1(value: object) -> str:
    try:
        return f"{float(value):.1%}"
    except Exception:
        return "-"


def _num(value: object, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def _prob_text(probabilities: dict, key: str) -> str:
    labels = {"home": "\u4e3b\u80dc", "draw": "\u5e73\u5c40", "away": "\u5ba2\u80dc"}
    return f"{labels[key]} {_pct1(probabilities.get(key, 0))}"


def _risk_key(label: object) -> str:
    text = str(label or "").upper()
    if "HIGH" in text or "高" in text:
        return "high"
    if "MEDIUM" in text or "中" in text:
        return "medium"
    return "low"


def _risk_label(label: object) -> str:
    key = _risk_key(label)
    return {"low": "低风险", "medium": "中风险", "high": "高风险"}[key]


def _risk_color(label: object) -> str:
    return {"low": GREEN, "medium": YELLOW, "high": RED}[_risk_key(label)]


def _strategy_text(prediction: dict) -> str:
    pick = str(prediction.get("recommendation") or "-")
    ou = str(prediction.get("ou_recommendation") or "").strip()
    score = str(prediction.get("score_recommendation") or "").strip()
    risk = _risk_key(prediction.get("risk_level"))
    if risk == "high":
        return f"谨慎 / {ou or score or pick}"
    if risk == "medium":
        return f"{pick} / {ou or score or '观察'}"
    return pick


def _admission_payload(prediction: dict) -> dict:
    payload = prediction.get("strategy_admission", {})
    return payload if isinstance(payload, dict) else {}


def _admission_text(prediction: dict) -> str:
    admission = _admission_payload(prediction)
    return str(admission.get("label") or "-")


def _admission_reasons_text(prediction: dict, *, limit: int = 4) -> str:
    return format_strategy_admission_reasons(_admission_payload(prediction), limit=limit)


def _admission_replay_guard_text(prediction: dict) -> str:
    return format_strategy_admission_replay_guard(_admission_payload(prediction))


def _admission_color(prediction: dict) -> str:
    decision = str(_admission_payload(prediction).get("decision") or "")
    if decision == "allow":
        return GREEN
    if decision == "block":
        return RED
    return YELLOW


def _governance_color(status: dict) -> str:
    tone = str(status.get("tone") or "")
    if tone == "good":
        return GREEN
    if tone == "bad":
        return RED
    if tone == "warning":
        return YELLOW
    return MUTED


def _governance_text(status: dict) -> str:
    label = str(status.get("label") or "-").strip()
    return label or "-"


def _c1_suggested_action_priority(action: str) -> int:
    return {
        "\u963b\u65ad": 0,
        "\u63a5\u8fd1\u963b\u65ad": 1,
        "\u8865\u9635\u5bb9": 2,
        "\u89c2\u5bdf": 3,
        "\u53ef\u653e\u884c": 4,
    }.get(str(action or "").strip(), 9)


def _competition_mode_label(prediction: dict) -> str:
    if prediction.get("competition_mode") == "world_cup":
        return "\u4e16\u754c\u676f\u6a21\u5f0f"
    return "\u5e38\u89c4\u6a21\u5f0f"


def _rating_pool_label(prediction: dict) -> str:
    if prediction.get("rating_pool") == "national_team":
        return "\u56fd\u5bb6\u961f ELO"
    return "\u4ff1\u4e50\u90e8 ELO"


def _draw_release_guard_summary(prediction: dict) -> tuple[str, str, str]:
    guard = prediction.get("draw_release_guard") if isinstance(prediction.get("draw_release_guard"), dict) else {}
    if not guard:
        return "\u672a\u63a5\u5165", "\u5f53\u524d\u9884\u6d4b\u6ca1\u6709\u5e73\u5c40\u63a5\u7ba1\u62e6\u622a\u4fe1\u606f\u3002", "neutral"
    odds_bucket = str(guard.get("odds_bucket") or "-")
    reason = str(guard.get("reason") or "-")
    evidence = guard.get("evidence") if isinstance(guard.get("evidence"), dict) else {}
    source = str(evidence.get("source") or "-")
    precision = evidence.get("precision")
    draw_rate = evidence.get("draw_rate")
    lift = evidence.get("lift")
    evidence_text = (
        f"\u5386\u53f2\u8bc1\u636e {source} | precision {_pct1(precision)} | "
        f"draw_rate {_pct1(draw_rate)} | lift {_pct1(lift)}"
        if evidence
        else "\u8be5\u5e73\u8d54\u6876\u6682\u65e0\u5f31\u8bc1\u636e"
    )
    body = (
        f"\u5e73\u8d54\u6876 {odds_bucket} | \u539f\u59cb\u63a5\u7ba1 {'YES' if guard.get('base_takeover') else 'NO'} | "
        f"\u5f31\u6876\u9ad8\u5206 {'YES' if guard.get('weak_score') else 'NO'} | reason {reason}\n"
        f"{evidence_text}"
    )
    if guard.get("blocked"):
        return "\u5df2\u62e6\u622a", body, "bad"
    if guard.get("base_takeover"):
        return "\u5141\u8bb8\u63a5\u7ba1", body, "good"
    if guard.get("weak_score"):
        return "\u5f31\u6876\u89c2\u5bdf", body, "warning"
    return "\u672a\u89e6\u53d1", body, "neutral"


def _draw_release_guard_markdown(prediction: dict) -> str:
    guard = prediction.get("draw_release_guard") if isinstance(prediction.get("draw_release_guard"), dict) else {}
    if not guard:
        return "## Draw Release Guard\n\nNo draw takeover guard data.\n\n"
    label, body, _tone = _draw_release_guard_summary(prediction)
    evidence = guard.get("evidence") if isinstance(guard.get("evidence"), dict) else {}
    return (
        "## Draw Release Guard\n\n"
        "| Item | Value |\n"
        "|---|---|\n"
        f"| Status | {_md_cell(label)} |\n"
        f"| Reason | {_md_cell(guard.get('reason', '-'))} |\n"
        f"| Odds bucket | {_md_cell(guard.get('odds_bucket', '-'))} |\n"
        f"| Draw odds | {_num(guard.get('odds_draw'), 3)} |\n"
        f"| Base takeover | {_md_cell('yes' if guard.get('base_takeover') else 'no')} |\n"
        f"| Weak score | {_md_cell('yes' if guard.get('weak_score') else 'no')} |\n"
        f"| Blocked | {_md_cell('yes' if guard.get('blocked') else 'no')} |\n"
        f"| Min score | {_pct1(guard.get('min_score'))} |\n"
        f"| Evidence source | {_md_cell(evidence.get('source', '-'))} |\n"
        f"| Evidence precision | {_pct1(evidence.get('precision'))} |\n"
        f"| Evidence draw rate | {_pct1(evidence.get('draw_rate'))} |\n"
        f"| Evidence lift | {_pct1(evidence.get('lift'))} |\n\n"
        f"{_md_cell(body)}\n\n"
    )


def _world_cup_notice(prediction: dict) -> str:
    payload = prediction.get("world_cup_mode")
    if not isinstance(payload, dict) or not payload.get("enabled"):
        return ""
    phase_map = {"group": "\u5c0f\u7ec4\u8d5b", "knockout": "\u6dd8\u6c70\u8d5b", "unknown": "\u5f85\u5224\u5b9a"}
    phase = phase_map.get(str(payload.get("phase") or "unknown"), "\u5f85\u5224\u5b9a")
    group_context = payload.get("group_context", {}) if isinstance(payload.get("group_context"), dict) else {}
    pressure_text = _world_cup_group_context_text(group_context)
    cap = _pct1(payload.get("confidence_cap"))
    adjusted = "\u5df2\u964d\u6743" if payload.get("confidence_adjusted") else "\u672a\u89e6\u53d1\u964d\u6743"
    return (
        "\n\n\u4e16\u754c\u676f\u6a21\u5f0f\n"
        f"- \u8d5b\u5236\u9636\u6bb5\uff1a{phase}\n"
        f"- \u7f6e\u4fe1\u4e0a\u9650\uff1a{cap}\uff08{adjusted}\uff09\n"
        "- \u8bc4\u5206\u6c60\uff1a\u56fd\u5bb6\u961f ELO\uff0c\u4e0d\u4e0e\u4ff1\u4e50\u90e8\u8bc4\u5206\u6df7\u7528\u3002\n"
        f"{pressure_text}"
        "- \u56fd\u5bb6\u961f\u6837\u672c\u7a00\u758f\uff0c\u9635\u5bb9\u3001\u8d5b\u7a0b\u5bc6\u5ea6\u548c\u79ef\u5206\u5f62\u52bf\u9700\u8981\u4f18\u5148\u590d\u6838\u3002\n"
        "- \u5c0f\u7ec4\u8d5b\u8981\u5173\u6ce8\u51c0\u80dc\u7403\u548c\u8f6e\u6362\uff0c\u6dd8\u6c70\u8d5b\u8981\u5173\u6ce8\u52a0\u65f6/\u70b9\u7403\u548c\u4fdd\u5b88\u7b56\u7565\u3002"
    )


def _world_cup_group_context_text(context: dict) -> str:
    if not context:
        return "- \u5c0f\u7ec4\u4e0a\u4e0b\u6587\uff1a\u6682\u65e0\u79ef\u5206\u6570\u636e\uff0c\u9700\u8d5b\u524d\u8865\u5145\u3002\n"
    group = str(context.get("group") or "-")
    group_round = int(context.get("round") or 0)
    tags = context.get("pressure_tags", [])
    tag_labels = {
        "final_group_round": "\u5c0f\u7ec4\u672b\u8f6e",
        "points_tight": "\u79ef\u5206\u63a5\u8fd1",
        "asymmetric_motivation": "\u6218\u610f\u4e0d\u5bf9\u79f0",
        "goal_difference_pressure": "\u51c0\u80dc\u7403\u538b\u529b",
    }
    readable_tags = [tag_labels.get(str(tag), str(tag)) for tag in tags if tag]
    tag_text = "\u3001".join(readable_tags) if readable_tags else "\u5f85\u89c2\u5bdf"
    return (
        f"- \u5c0f\u7ec4\u4e0a\u4e0b\u6587\uff1a{group} \u7b2c{group_round or '-'}\u8f6e | "
        f"\u79ef\u5206 {context.get('home_points', '-')}:{context.get('away_points', '-')} | "
        f"\u51c0\u80dc\u7403 {context.get('home_goal_diff', '-')}:{context.get('away_goal_diff', '-')} | "
        f"\u538b\u529b\u6807\u7b7e {tag_text}\n"
    )


def _analysis_report(row: DashboardRow, governance_status: dict | None = None) -> str:
    match = row.match
    pred = row.prediction
    indices = pred.get("indices", {}) if isinstance(pred.get("indices"), dict) else {}
    probs = pred.get("probabilities", {}) if isinstance(pred.get("probabilities"), dict) else {}
    market_probs = pred.get("market_probabilities", {}) if isinstance(pred.get("market_probabilities"), dict) else {}
    risk = _risk_key(pred.get("risk_level"))
    admission = _admission_payload(pred)
    admission_reason_text = _admission_reasons_text(pred, limit=4)
    admission_threshold_text = format_strategy_admission_thresholds(admission)
    admission_replay_text = format_strategy_admission_replay_guard(admission)
    admission_replay_line = f"- Agent Replay\uff1a{admission_replay_text}\n" if admission_replay_text != "-" else ""
    draw_guard_label, draw_guard_body, _draw_guard_tone = _draw_release_guard_summary(pred)
    draw_guard_line = f"- \u5e73\u5c40\u63a5\u7ba1\uff1a{draw_guard_label} | {draw_guard_body}\n"
    governance_block = ""
    if governance_status:
        governance_block = "\n" + build_main_flow_governance_status_text(governance_status) + "\n"

    risk_reason = {
        "high": "\u51b7\u95e8\u6307\u6570\u504f\u9ad8\uff0c\u5e02\u573a\u4e0e\u6a21\u578b\u53ef\u80fd\u5b58\u5728\u660e\u663e\u5206\u6b67\u3002",
        "medium": "\u5b58\u5728\u4e00\u5b9a\u6ce2\u52a8\uff0c\u5efa\u8bae\u964d\u4f4e\u6743\u91cd\u5e76\u7ed3\u5408\u8d5b\u524d\u4fe1\u606f\u590d\u6838\u3002",
        "low": "\u7efc\u5408\u6307\u6807\u76f8\u5bf9\u7a33\u5b9a\uff0c\u76ee\u524d\u6ca1\u6709\u89e6\u53d1\u660e\u663e\u98ce\u9669\u4fe1\u53f7\u3002",
    }[risk]
    market_line = ""
    if market_probs:
        market_line = (
            "\n"
            f"- \u5e02\u573a\u9690\u542b\u6982\u7387\uff1a"
            f"{_prob_text(market_probs, 'home')} / {_prob_text(market_probs, 'draw')} / {_prob_text(market_probs, 'away')}"
        )

    return (
        f"\u5bf9\u9635\uff1a{match.home_team} vs {match.away_team}\n"
        f"\u8054\u8d5b\uff1a{match.league}\n"
        f"\u5f00\u8d5b\uff1a{match.match_date} {match.match_time}\n\n"
        "\u6838\u5fc3\u7ed3\u8bba\n"
        f"- \u63a8\u8350\u7b56\u7565\uff1a{_strategy_text(pred)}\n"
        f"- \u7b56\u7565\u51c6\u5165\uff1a{_admission_text(pred)}\n"
        f"- \u51c6\u5165\u539f\u56e0\uff1a{admission_reason_text}\n"
        f"- \u51c6\u5165\u95e8\u69db\uff1a{admission_threshold_text}\n"
        f"{admission_replay_line}"
        f"{draw_guard_line}"
        f"- \u98ce\u9669\u7b49\u7ea7\uff1a{_risk_label(pred.get('risk_level'))}\n"
        f"- \u7efc\u5408\u7f6e\u4fe1\u5ea6\uff1a{_pct1(pred.get('confidence'))}\n"
        f"- \u9884\u8ba1\u603b\u8fdb\u7403\uff1a{_num(pred.get('expected_goals'))}\n\n"
        f"{governance_block}"
        "\u6982\u7387\u5206\u5e03\n"
        f"- {_prob_text(probs, 'home')} / {_prob_text(probs, 'draw')} / {_prob_text(probs, 'away')}"
        f"{market_line}\n\n"
        "\u73a9\u6cd5\u7ef4\u5ea6\n"
        f"- \u5927\u5c0f\u7403\uff1a{pred.get('ou_recommendation', '-')} ({_pct1(pred.get('ou_confidence'))})\n"
        f"- \u8ba9\u7403\uff1a{pred.get('handicap_recommendation', '-')} ({_pct1(pred.get('handicap_confidence'))})\n"
        f"- \u6bd4\u5206\uff1a{pred.get('score_recommendation', '-')} ({_pct1(pred.get('score_confidence'))})\n"
        f"- \u534a\u5168\u573a\uff1a{pred.get('htft_recommendation', '-')} ({_pct1(pred.get('htft_confidence'))})\n\n"
        "\u98ce\u9669\u89e3\u8bfb\n"
        f"- {risk_reason}\n"
        f"- \u51b7\u95e8\u6307\u6570\uff1a{_pct1(indices.get('upset_index', 0))}\n"
        f"- \u7a33\u5b9a\u6307\u6570\uff1a{_pct1(indices.get('stability_index', 0))}\n"
        f"- \u4fe1\u5fc3\u6307\u6570\uff1a{_pct1(indices.get('confidence_index', 0))}\n\n"
        "\u590d\u6838\u5efa\u8bae\n"
        "- \u8d5b\u524d\u91cd\u70b9\u590d\u6838\u4f24\u505c\u3001\u9996\u53d1\u3001\u76d8\u53e3\u53d8\u5316\u548c\u5e02\u573a\u70ed\u5ea6\u3002\n"
        "- \u82e5\u4e34\u573a\u76d8\u53e3\u4e0e\u6a21\u578b\u65b9\u5411\u6301\u7eed\u80cc\u79bb\uff0c\u5e94\u4e0b\u8c03\u7b56\u7565\u6743\u91cd\u3002"
        f"{_world_cup_notice(pred)}"
    )


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", text, flags=re.UNICODE).strip("_")
    return cleaned[:80] or "match"


def _md_cell(value: object) -> str:
    return str(value if value is not None else "-").replace("|", "/").replace("\n", " ")


def _prob_table(title: str, probabilities: dict) -> str:
    if not isinstance(probabilities, dict) or not probabilities:
        return f"### {title}\n\n暂无数据\n"
    return (
        f"### {title}\n\n"
        "| 主胜 | 平局 | 客胜 |\n"
        "|---:|---:|---:|\n"
        f"| {_pct1(probabilities.get('home', 0))} | {_pct1(probabilities.get('draw', 0))} | {_pct1(probabilities.get('away', 0))} |\n"
    )


def _index_table(indices: dict) -> str:
    return (
        "| 指标 | 数值 |\n"
        "|---|---:|\n"
        f"| 冷门指数 | {_pct1(indices.get('upset_index', 0))} |\n"
        f"| 稳定指数 | {_pct1(indices.get('stability_index', 0))} |\n"
        f"| 信心指数 | {_pct1(indices.get('confidence_index', 0))} |\n"
    )


def _fmt_metric_map(values: object, *, percent: bool = False) -> str:
    if not isinstance(values, dict):
        return "-"
    parts: list[str] = []
    for key in ("home", "draw", "away"):
        if key not in values:
            continue
        value = values.get(key)
        if percent:
            parts.append(f"{key}={_pct1(value)}")
        else:
            parts.append(f"{key}={_num(value, 3)}")
    return " / ".join(parts) if parts else "-"


def _market_entropy_markdown(pred: dict) -> str:
    entropy = pred.get("market_entropy") if isinstance(pred.get("market_entropy"), dict) else {}
    if not entropy:
        return "## 7. MarketEntropy 盘口异常识别\n\n暂无 MarketEntropy 数据。\n\n"
    sequence = entropy.get("sequence") if isinstance(entropy.get("sequence"), dict) else {}
    risk = pred.get("market_entropy_risk") if isinstance(pred.get("market_entropy_risk"), dict) else {}
    signals = entropy.get("signals") if isinstance(entropy.get("signals"), list) else []
    return (
        "## 7. MarketEntropy 盘口异常识别\n\n"
        "| 指标 | 数值 |\n"
        "|---|---:|\n"
        f"| 熵值等级 | {_md_cell(entropy.get('level', '-'))} |\n"
        f"| 熵值评分 | {_pct1(entropy.get('score'))} |\n"
        f"| 风险覆盖 | {_md_cell(risk.get('reason') or ('applied' if risk.get('applied') else 'none'))} |\n"
        f"| 开盘到即时斜率 | {_md_cell(_fmt_metric_map(entropy.get('odds_slope'), percent=True))} |\n"
        f"| 历史样本数 | {_num(sequence.get('sample_count'), 0)} |\n"
        f"| 最近盘口速度 | {_md_cell(_fmt_metric_map(sequence.get('latest_velocity'), percent=True))} |\n"
        f"| 历史最大阶跃 | {_pct1(sequence.get('max_step_change'))} |\n"
        f"| 阶跃方向 | {_md_cell(sequence.get('step_side', '-'))} |\n"
        f"| 最强降赔方向 | {_md_cell(entropy.get('strongest_steam_side', '-'))} |\n"
        f"| 市场热门方向 | {_md_cell(entropy.get('market_favorite', '-'))} |\n"
        f"| Kelly | {_md_cell(_fmt_metric_map(entropy.get('kelly')))} |\n"
        f"| Kelly 跨度 | {_num(entropy.get('kelly_span'), 3)} |\n"
        f"| 推荐侧 Kelly 差 | {_num(entropy.get('pick_kelly_gap'), 3)} |\n"
        f"| 触发信号 | {_md_cell(', '.join(str(item) for item in signals) if signals else '-')} |\n\n"
    )


def _handicap_margin_markdown(pred: dict) -> str:
    signal = pred.get("handicap_margin_consistency") if isinstance(pred.get("handicap_margin_consistency"), dict) else {}
    if not signal:
        return "## Handicap Margin Consistency\n\nNo handicap/model margin consistency data.\n\n"
    signals = signal.get("signals") if isinstance(signal.get("signals"), list) else []
    return (
        "## Handicap Margin Consistency\n\n"
        "| Item | Value |\n"
        "|---|---:|\n"
        f"| Level | {_md_cell(signal.get('level', '-'))} |\n"
        f"| Score | {_pct1(signal.get('score'))} |\n"
        f"| Handicap line | {_num(signal.get('handicap_line'), 2)} |\n"
        f"| Model margin goals | {_num(signal.get('model_margin_goals'), 2)} |\n"
        f"| Market side | {_md_cell(signal.get('market_side', '-'))} |\n"
        f"| Model side | {_md_cell(signal.get('model_side', '-'))} |\n"
        f"| Depth gap | {_num(signal.get('depth_gap'), 2)} |\n"
        f"| Handicap pick side | {_md_cell(signal.get('handicap_pick_side', '-'))} |\n"
        f"| Signals | {_md_cell(', '.join(str(item) for item in signals) if signals else '-')} |\n\n"
    )


def _supervisor_markdown(pred: dict) -> str:
    supervisor = pred.get("supervisor") if isinstance(pred.get("supervisor"), dict) else {}
    if not supervisor:
        return "## 8. Supervisor / Agent Trace\n\n暂无 Supervisor 编排数据。\n\n"
    decision = supervisor.get("decision") if isinstance(supervisor.get("decision"), dict) else {}
    actions = supervisor.get("next_actions") if isinstance(supervisor.get("next_actions"), list) else []
    nodes = build_agent_trace_nodes(supervisor)
    lines = [
        "## 8. Supervisor / Agent Trace",
        "",
        "| 项目 | 结果 |",
        "|---|---|",
        f"| Supervisor 状态 | {_md_cell(supervisor.get('status', '-'))} |",
        f"| 是否允许放行 | {_md_cell('yes' if decision.get('release_allowed') else 'no')} |",
        f"| 是否需要人工复核 | {_md_cell('yes' if decision.get('requires_human_review') else 'no')} |",
        f"| 风险桶 | {_md_cell(decision.get('risk_bucket', '-'))} |",
        f"| MarketEntropy 等级 | {_md_cell(decision.get('market_entropy_level', '-'))} |",
        f"| 下一步动作 | {_md_cell(', '.join(str(item) for item in actions) if actions else '-')} |",
        "",
        "| Agent | 状态 | 触发 | 摘要 |",
        "|---|---|---|---|",
    ]
    for node in nodes:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(node.get("name", "-")),
                    _md_cell(node.get("status_label", "-")),
                    _md_cell(node.get("trigger", "-")),
                    _md_cell(node.get("summary", "-")),
                ]
            )
            + " |"
        )
    lines.extend(["", "### Agent 输入输出摘要", ""])
    for node in nodes:
        lines.extend(
            [
                f"#### {_md_cell(node.get('name', '-'))}",
                "",
                "```text",
                format_agent_trace_detail(node),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def _markdown_report(row: DashboardRow, generated_at: datetime | None = None, governance_status: dict | None = None) -> str:
    now = generated_at or datetime.now()
    match = row.match
    pred = row.prediction
    probs = pred.get("probabilities", {}) if isinstance(pred.get("probabilities"), dict) else {}
    market_probs = pred.get("market_probabilities", {}) if isinstance(pred.get("market_probabilities"), dict) else {}
    elo_probs = pred.get("elo_probabilities", {}) if isinstance(pred.get("elo_probabilities"), dict) else {}
    poisson_probs = pred.get("poisson_probabilities", {}) if isinstance(pred.get("poisson_probabilities"), dict) else {}
    xgb_probs = pred.get("xgb_probabilities", {}) if isinstance(pred.get("xgb_probabilities"), dict) else {}
    handicap_probs = pred.get("handicap_probabilities", {}) if isinstance(pred.get("handicap_probabilities"), dict) else {}
    ou_probs = pred.get("ou_probabilities", {}) if isinstance(pred.get("ou_probabilities"), dict) else {}
    indices = pred.get("indices", {}) if isinstance(pred.get("indices"), dict) else {}
    admission = _admission_payload(pred)
    draw_guard_section = _draw_release_guard_markdown(pred)
    market_entropy_section = _market_entropy_markdown(pred)
    handicap_margin_section = _handicap_margin_markdown(pred)
    supervisor_section = _supervisor_markdown(pred)
    governance_text = build_main_flow_governance_status_text(governance_status) if governance_status else ""
    governance_section = f"## Main Flow Governance\n\n```text\n{governance_text}\n```\n\n" if governance_text else ""
    governance_table_rows = ""
    if governance_status:
        governance_table_rows = (
            f"| \u4e3b\u6d41\u7a0b\u6cbb\u7406 | {_md_cell(governance_status.get('label', '-'))} ({_md_cell(governance_status.get('status', '-'))}) |\n"
            f"| \u6b63\u5f0f\u5efa\u8bae\u53ef\u7528 | {_md_cell('yes' if governance_status.get('formal_allowed') else 'no')} |\n"
        )
    return (
        f"# {match.home_team} vs {match.away_team} \u8d5b\u4e8b\u5206\u6790\u62a5\u544a\n\n"
        "## 1. 基本信息\n\n"
        "| 字段 | 内容 |\n"
        "|---|---|\n"
        f"| 生成时间 | {now.strftime('%Y-%m-%d %H:%M:%S')} |\n"
        f"| 联赛 | {_md_cell(match.league)} |\n"
        f"| 开赛时间 | {_md_cell(match.match_date)} {_md_cell(match.match_time)} |\n"
        f"| 数据源 | {_md_cell(match.source)} |\n"
        f"| 数据 ID | {_md_cell(match.source_id or '-')} |\n\n"
        "## 2. 核心结论\n\n"
        "| 项目 | 结果 |\n"
        "|---|---|\n"
        f"| 推荐策略 | {_md_cell(_strategy_text(pred))} |\n"
        f"| 策略准入 | {_md_cell(_admission_text(pred))} |\n"
        f"| \u51c6\u5165\u539f\u56e0 | {_md_cell(format_strategy_admission_reasons(admission, limit=6))} |\n"
        f"| \u51c6\u5165\u95e8\u69db | {_md_cell(format_strategy_admission_thresholds(admission))} |\n"
        f"| Agent Replay | {_md_cell(format_strategy_admission_replay_guard(admission))} |\n"
        f"{governance_table_rows}"
        f"| Draw Guard | {_md_cell(_draw_release_guard_summary(pred)[0])} |\n"
        f"| 风险等级 | {_md_cell(_risk_label(pred.get('risk_level')))} |\n"
        f"| 综合置信度 | {_pct1(pred.get('confidence'))} |\n"
        f"| 预计总进球 | {_num(pred.get('expected_goals'))} |\n"
        f"| 当前模型 | {_md_cell(pred.get('model', '-'))} |\n\n"
        "## 3. 概率分布\n\n"
        f"{_prob_table('融合概率', probs)}\n"
        f"{_prob_table('市场隐含概率', market_probs)}\n"
        f"{_prob_table('ELO 概率', elo_probs)}\n"
        f"{_prob_table('Poisson 概率', poisson_probs)}\n"
        f"{_prob_table('XGBoost 概率', xgb_probs)}\n"
        "## 4. 玩法维度\n\n"
        "| 玩法 | 推荐 | 置信度 | 补充 |\n"
        "|---|---|---:|---|\n"
        f"| 1X2 | {_md_cell(pred.get('recommendation', '-'))} | {_pct1(pred.get('confidence'))} | 主胜/平局/客胜 |\n"
        f"| 大小球 | {_md_cell(pred.get('ou_recommendation', '-'))} | {_pct1(pred.get('ou_confidence'))} | Over {_pct1(ou_probs.get('over'))} / Under {_pct1(ou_probs.get('under'))} |\n"
        f"| 让球 | {_md_cell(pred.get('handicap_recommendation', '-'))} | {_pct1(pred.get('handicap_confidence'))} | H {_pct1(handicap_probs.get('home'))} / D {_pct1(handicap_probs.get('draw'))} / A {_pct1(handicap_probs.get('away'))} |\n"
        f"| 比分 | {_md_cell(pred.get('score_recommendation', '-'))} | {_pct1(pred.get('score_confidence'))} | 精确比分候选 |\n"
        f"| 半全场 | {_md_cell(pred.get('htft_recommendation', '-'))} | {_pct1(pred.get('htft_confidence'))} | 节奏推演 |\n\n"
        "## 5. 风控指标\n\n"
        f"{_index_table(indices)}\n"
        "## 6. 盘口与市场数据\n\n"
        "| 指标 | 数值 |\n"
        "|---|---:|\n"
        f"| 即时主胜赔率 | {_num(match.odds_home, 3)} |\n"
        f"| 即时平局赔率 | {_num(match.odds_draw, 3)} |\n"
        f"| 即时客胜赔率 | {_num(match.odds_away, 3)} |\n"
        f"| 初盘主胜赔率 | {_num(match.opening_odds_home, 3)} |\n"
        f"| 初盘平局赔率 | {_num(match.opening_odds_draw, 3)} |\n"
        f"| 初盘客胜赔率 | {_num(match.opening_odds_away, 3)} |\n"
        f"| 让球线 | {_num(match.handicap_line, 2)} |\n"
        f"| 返还率 | {_pct1(match.return_rate)} |\n"
        f"| Kelly 主胜 | {_num(match.kelly_home, 3)} |\n"
        f"| Kelly 平局 | {_num(match.kelly_draw, 3)} |\n"
        f"| Kelly 客胜 | {_num(match.kelly_away, 3)} |\n\n"
        "## 7. AI 分析摘要\n\n"
        f"{draw_guard_section}"
        f"{governance_section}"
        f"{market_entropy_section}"
        f"{handicap_margin_section}"
        f"{supervisor_section}"
        f"{_analysis_report(row, governance_status=governance_status)}\n\n"
        "## 8. 复核清单\n\n"
        "- [ ] 复核首发阵容与关键伤停\n"
        "- [ ] 复核临场盘口是否继续偏离模型方向\n"
        "- [ ] 复核市场热度与赔率变化是否一致\n"
        "- [ ] 高风险场次降低策略权重或仅观察\n"
        "- [ ] 赛后回收赛果并进入复盘中心\n"
    )


def _bytes_text(size: int) -> str:
    value = float(max(size, 0))
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def _dir_stats(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    count = 0
    size = 0
    try:
        files = path.rglob("*")
        for item in files:
            try:
                if item.is_file():
                    count += 1
                    size += item.stat().st_size
            except OSError:
                continue
    except OSError:
        return count, size
    return count, size


def _mtime_text(path: Path) -> str:
    try:
        if not path.exists():
            return "-"
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except OSError:
        return "-"


def _load_dashboard_settings() -> dict:
    try:
        if not SETTINGS_PATH.exists():
            return {}
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_dashboard_settings(settings: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_prediction_snapshot_records() -> dict[str, dict]:
    path = PROJECT_ROOT / "data" / "state" / "prediction_snapshots.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    items = payload.get("items", {})
    return items if isinstance(items, dict) else {}


def _parse_match_datetime(match: dict) -> datetime | None:
    date_text = str(match.get("match_date") or "").strip()
    time_text = str(match.get("match_time") or "").strip()
    if not date_text:
        return None
    candidates = []
    if time_text:
        candidates.extend(
            [
                f"{date_text} {time_text}",
                f"{date_text} {time_text[:5]}",
            ]
        )
    candidates.append(date_text)
    for candidate in candidates:
        for fmt in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(candidate, fmt)
            except ValueError:
                continue
    return None


def _snapshot_status(match: dict, now: datetime | None = None) -> str:
    kickoff = _parse_match_datetime(match)
    if kickoff is None:
        return "\u5f85\u590d\u76d8"
    current = now or datetime.now()
    hours_from_kickoff = (current - kickoff).total_seconds() / 3600
    if hours_from_kickoff < 0:
        return "\u5f85\u5f00\u8d5b"
    if hours_from_kickoff <= 3:
        return "\u8fdb\u884c\u4e2d"
    return "\u5f85\u56de\u6536"


def build_statsbomb_event_proxy_review_text(item: dict) -> str:
    summary = item.get("statsbomb_event_summary") if isinstance(item.get("statsbomb_event_summary"), dict) else {}
    if not summary:
        return "\n".join(
            [
                "StatsBomb 事件代理复盘",
                "- 状态: 暂无事件代理数据",
                "- 建议: 若没有视频回放，可优先接入 StatsBomb/事件摘要作为赛后复盘证据。",
                "- 使用边界: 仅用于赛后归因和训练样本复盘，不进入赛前预测特征。",
            ]
        )
    home = str(item.get("home_team") or "home")
    away = str(item.get("away_team") or "away")
    team_stats = summary.get("team_stats") if isinstance(summary.get("team_stats"), dict) else {}
    home_stats = team_stats.get(home) if isinstance(team_stats.get(home), dict) else {}
    away_stats = team_stats.get(away) if isinstance(team_stats.get(away), dict) else {}
    def _as_float(value: object) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    event_count = int(max(0, _as_float(summary.get("event_count"))))
    evidence_level = "medium" if event_count >= 1000 else "low"
    home_xg = _as_float(home_stats.get("xg"))
    away_xg = _as_float(away_stats.get("xg"))
    xg_diff = home_xg - away_xg
    if abs(xg_diff) < 0.3:
        conclusion = "双方机会质量接近，重点复核临门一脚、门将表现或偶发事件。"
    elif xg_diff >= 0.75:
        conclusion = f"{home} 的机会质量明显占优，若预测失误需复核赛前强弱面低估。"
    elif xg_diff <= -0.75:
        conclusion = f"{away} 的机会质量明显占优，若预测失误需复核客队进攻面或主队防守风险。"
    elif xg_diff > 0:
        conclusion = f"{home} 机会质量小幅占优，适合作为赛后归因辅助证据。"
    else:
        conclusion = f"{away} 机会质量小幅占优，适合作为赛后归因辅助证据。"
    source_id = summary.get("source_match_id") or item.get("statsbomb_source_match_id") or "-"
    return "\n".join(
        [
            "StatsBomb 事件代理复盘",
            "- source_type=event_proxy",
            f"- source_match_id: {source_id}",
            f"- 证据强度: {evidence_level} / events={event_count}",
            f"- xG: {home} {_num(home_xg)} vs {away} {_num(away_xg)} / diff {_num(xg_diff)}",
            f"- 射门: {home} {int(_as_float(home_stats.get('shots')))} vs {away} {int(_as_float(away_stats.get('shots')))}",
            f"- 射正: {home} {int(_as_float(home_stats.get('shots_on_target')))} vs {away} {int(_as_float(away_stats.get('shots_on_target')))}",
            f"- 进球时间: first={summary.get('first_goal_minute', '-')} / last={summary.get('last_goal_minute', '-')}",
            f"- 代理结论: {conclusion}",
            "- 使用边界: 仅用于赛后归因和训练样本复盘，不进入赛前预测特征，避免赛果信息泄漏。",
        ]
    )


def build_statsbomb_event_proxy_review_samples_message(result: dict, quality: dict) -> str:
    def _as_int(value: object, default: int = 0) -> int:
        try:
            return int(value if value is not None else default)
        except (TypeError, ValueError):
            return default

    def _first_present(*values: object) -> object:
        for value in values:
            if value is not None and value != "":
                return value
        return None

    def _top_rows(rows: object, limit: int = 3) -> list[str]:
        if not isinstance(rows, list):
            return ["- 暂无"]
        output: list[str] = []
        for row in rows[:limit]:
            if not isinstance(row, dict):
                continue
            label = str(row.get("label") or row.get("code") or "-")
            value = str(row.get("value") or "-")
            detail = str(row.get("detail") or "").strip()
            output.append(f"- {label}: {value}" + (f" ({detail})" if detail else ""))
        return output or ["- 暂无"]

    skipped = result.get("skipped_reasons") if isinstance(result.get("skipped_reasons"), dict) else {}
    sample_count = _as_int(
        _first_present(result.get("generated_sample_count"), result.get("sample_count"), quality.get("sample_count"))
    )
    missing_statsbomb = _as_int(skipped.get("missing_statsbomb"))
    unknown_label = _as_int(skipped.get("unknown_label"))
    output_path = str(result.get("output_path") or "-")
    issues = quality.get("issues") if isinstance(quality.get("issues"), list) else []
    issue_count = _as_int(quality.get("issue_count"), len(issues))
    quality_status = str(quality.get("status") or "-")
    leakage_note = str(
        quality.get("leakage_note")
        or "StatsBomb review training samples use post-match event evidence and must not be used as pre-match prediction features."
    )

    def _issue_rank(issue: object) -> int:
        if not isinstance(issue, dict):
            return 9
        severity = str(issue.get("severity") or "")
        if severity == "blocking":
            return 0
        if severity == "warning":
            return 1
        return 2

    ranked_issues = sorted([issue for issue in issues if isinstance(issue, dict)], key=_issue_rank)
    if ranked_issues:
        recommendation_lines = [
            f"{index}. {issue.get('message') or issue.get('code') or '-'} -> {issue.get('recommendation') or '-'}"
            for index, issue in enumerate(ranked_issues[:3], 1)
        ]
    else:
        recommendation_lines = ["1. 暂无质量问题，可进入回测/训练稳定性验证。"]

    return "\n".join(
        [
            "StatsBomb/Event Proxy 复盘样本已生成",
            "",
            f"样本: {sample_count}",
            f"缺 StatsBomb 事件: {missing_statsbomb}",
            f"未知标签: {unknown_label}",
            f"输出: {output_path}",
            "",
            f"质量状态: {quality_status} | issues={issue_count}",
            "",
            "标签分布:",
            *_top_rows(quality.get("label_rows")),
            "",
            "事件错因权重:",
            *_top_rows(quality.get("weight_rows")),
            "",
            "修复建议:",
            *recommendation_lines,
            "",
            f"泄漏边界: {leakage_note}",
            "该数据仅用于赛后复盘和误差归因，不进入赛前预测特征。",
        ]
    )


def build_statsbomb_review_training_action_rows(quality: dict) -> list[dict[str, object]]:
    issues = quality.get("issues") if isinstance(quality.get("issues"), list) else []
    status = str(quality.get("status") or "blocked")
    sample_count = int(quality.get("sample_count", 0) or 0)
    rows: list[dict[str, object]] = []
    seen: set[str] = set()

    def _append(action_key: str, title: str, body: str, *, tone: str = "neutral", issue_code: str = "") -> None:
        if action_key in seen:
            return
        seen.add(action_key)
        rows.append(
            {
                "action_key": action_key,
                "title": title,
                "body": body,
                "tone": tone,
                "issue_code": issue_code,
                "enabled": True,
            }
        )

    def _issue_rank(issue: dict[str, object]) -> int:
        severity = str(issue.get("severity") or "")
        if severity == "blocking":
            return 0
        if severity == "warning":
            return 1
        return 2

    ranked_issues = sorted([item for item in issues if isinstance(item, dict)], key=_issue_rank)
    for issue in ranked_issues:
        code = str(issue.get("code") or "")
        recommendation = str(issue.get("recommendation") or issue.get("message") or "-")
        severity = str(issue.get("severity") or "")
        tone = "danger" if severity == "blocking" else "warning"
        if code in {"statsbomb_review_samples_missing", "statsbomb_review_sample_count_low", "statsbomb_review_features_missing"}:
            _append(
                "build_statsbomb_review_samples",
                "生成事件代理复盘样本",
                f"{recommendation}\n点击后会重建 StatsBomb/Event Proxy 复盘样本并刷新质量诊断。",
                tone=tone,
                issue_code=code,
            )
        elif code.endswith("_missing") or code.endswith("_skewed"):
            _append(
                "recover_results",
                "回收赛果标签",
                f"{recommendation}\n点击后先回收已完场赛果；回收后再生成事件代理复盘样本。",
                tone=tone,
                issue_code=code,
            )

    if not rows and status == "healthy":
        _append(
            "run_high_accuracy_strategy_backtest",
            "进入策略稳定性回测",
            f"事件代理复盘样本 {sample_count} 条，当前可用于 Evaluation Agent 权重稳定性验证。",
            tone="good",
        )
    if not rows:
        _append(
            "refresh_review_center",
            "刷新复盘质量看板",
            "暂无可自动执行的修复动作；重新读取 StatsBomb/Event Proxy 样本质量。",
            tone="neutral",
        )
    return rows[:4]


def build_statsbomb_review_training_action_feedback(
    action_key: str,
    before_quality: dict,
    after_quality: dict,
    result: dict | None = None,
    *,
    occurred_at: datetime | None = None,
) -> dict[str, object]:
    result_payload = result if isinstance(result, dict) else {}
    before_status = str(before_quality.get("status") or "-")
    after_status = str(after_quality.get("status") or "-")
    before_sample_count = int(before_quality.get("sample_count", 0) or 0)
    after_sample_count = int(after_quality.get("sample_count", 0) or 0)
    before_issue_count = int(before_quality.get("issue_count", len(before_quality.get("issues", []) if isinstance(before_quality.get("issues"), list) else [])) or 0)
    after_issue_count = int(after_quality.get("issue_count", len(after_quality.get("issues", []) if isinstance(after_quality.get("issues"), list) else [])) or 0)
    status_rank = {"healthy": 0, "attention": 1, "blocked": 2}
    before_rank = status_rank.get(before_status, 1)
    after_rank = status_rank.get(after_status, 1)
    ok = bool(result_payload.get("ok", True))
    queued = bool(result_payload.get("queued", False))
    if not ok:
        outcome = "failed"
        tone = "bad"
    elif queued:
        outcome = "queued"
        tone = "neutral"
    elif after_rank < before_rank or after_issue_count < before_issue_count or after_sample_count > before_sample_count:
        outcome = "improved"
        tone = "good"
    elif after_rank > before_rank or after_issue_count > before_issue_count:
        outcome = "worsened"
        tone = "bad"
    else:
        outcome = "unchanged"
        tone = "warning"

    def _issue_codes(quality: dict) -> list[str]:
        issues = quality.get("issues") if isinstance(quality.get("issues"), list) else []
        return [str(item.get("code") or "-") for item in issues[:4] if isinstance(item, dict)]

    sample_delta = after_sample_count - before_sample_count
    issue_delta = after_issue_count - before_issue_count
    summary_text = (
        f"{action_key}: {outcome} | status {before_status}->{after_status} | "
        f"samples {before_sample_count}->{after_sample_count} ({sample_delta:+d}) | "
        f"issues {before_issue_count}->{after_issue_count} ({issue_delta:+d})"
    )
    after_issues = after_quality.get("issues") if isinstance(after_quality.get("issues"), list) else []
    next_recommendation = "-"
    for issue in after_issues:
        if isinstance(issue, dict):
            next_recommendation = str(issue.get("recommendation") or issue.get("message") or "-")
            break
    if outcome == "improved" and after_status == "healthy":
        next_recommendation = "质量已恢复健康，可进入回测/训练稳定性验证。"

    return {
        "action_key": action_key,
        "occurred_at": (occurred_at or datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
        "outcome": outcome,
        "tone": tone,
        "ok": ok,
        "queued": queued,
        "before_status": before_status,
        "after_status": after_status,
        "before_sample_count": before_sample_count,
        "after_sample_count": after_sample_count,
        "sample_delta": sample_delta,
        "before_issue_count": before_issue_count,
        "after_issue_count": after_issue_count,
        "issue_delta": issue_delta,
        "before_issue_codes": _issue_codes(before_quality),
        "after_issue_codes": _issue_codes(after_quality),
        "message": str(result_payload.get("message") or result_payload.get("reason") or ""),
        "summary_text": summary_text,
        "next_recommendation": next_recommendation,
    }


def build_statsbomb_review_training_feedback_rows(records: list[dict] | object, limit: int = 5) -> list[dict[str, object]]:
    if not isinstance(records, list):
        return []
    rows: list[dict[str, object]] = []
    for record in records[: max(0, int(limit))]:
        if not isinstance(record, dict):
            continue
        issue_codes = record.get("after_issue_codes") if isinstance(record.get("after_issue_codes"), list) else []
        issue_text = ", ".join(str(item) for item in issue_codes[:3]) or "-"
        rows.append(
            {
                "title": f"{record.get('occurred_at', '-')} | {record.get('action_key', '-')} | {record.get('outcome', '-')}",
                "body": (
                    f"{record.get('summary_text', '-')}\n"
                    f"剩余问题: {issue_text}\n"
                    f"下一步: {record.get('next_recommendation', '-')}"
                ),
                "tone": str(record.get("tone") or "neutral"),
            }
        )
    return rows


def build_statsbomb_review_training_center_summary(quality: dict | object, records: list[dict] | object) -> dict[str, object]:
    payload = quality if isinstance(quality, dict) else {}
    repair_records = [item for item in records if isinstance(item, dict)] if isinstance(records, list) else []
    status = str(payload.get("status") or "blocked")
    sample_count = int(payload.get("sample_count", 0) or 0)
    issue_count = int(payload.get("issue_count", 0) or 0)
    action_count = len(build_statsbomb_review_training_action_rows(payload))
    tone = "good" if status == "healthy" else "warning" if status == "attention" else "bad"
    latest = repair_records[0] if repair_records else {}
    latest_text = (
        f"{latest.get('occurred_at', '-')} | {latest.get('action_key', '-')} | {latest.get('outcome', '-')}"
        if latest
        else "-"
    )
    return {
        "status": status,
        "tone": tone,
        "sample_count": sample_count,
        "issue_count": issue_count,
        "action_count": action_count,
        "repair_count": len(repair_records),
        "latest_repair": latest_text,
        "title": f"事件代理质量 | {status}",
        "body": (
            f"样本 {sample_count} | 问题 {issue_count} | 可执行动作 {action_count} | 修复记录 {len(repair_records)}\n"
            f"最近修复: {latest_text}"
        ),
    }


def build_video_review_center_summary(
    video_memory_health: dict | object,
    video_source_coverage: dict | object,
) -> dict[str, object]:
    def _as_int(value: object, default: int = 0) -> int:
        try:
            return int(value if value is not None else default)
        except (TypeError, ValueError):
            return default

    def _payload(value: dict | object) -> dict:
        return value if isinstance(value, dict) else {}

    memory_payload = _payload(video_memory_health)
    source_payload = _payload(video_source_coverage)
    health = _payload(memory_payload.get("health"))
    monitor = _payload(memory_payload.get("monitor"))
    card_rows = memory_payload.get("card_rows") if isinstance(memory_payload.get("card_rows"), list) else []
    action_rows = memory_payload.get("action_rows") if isinstance(memory_payload.get("action_rows"), list) else []

    memory_status = str(health.get("status") or "blocked")
    coverage_status = str(source_payload.get("coverage_status") or "blocked")
    statuses = {memory_status, coverage_status}
    if "blocked" in statuses:
        status = "blocked"
    elif "attention" in statuses:
        status = "attention"
    else:
        status = "healthy"

    tone = {"healthy": "good", "attention": "warning", "blocked": "bad"}.get(status, "neutral")
    status_label = {"healthy": "可用", "attention": "需要关注", "blocked": "复盘受阻"}.get(status, status)
    local_count = _as_int(source_payload.get("local_video_count"))
    external_count = _as_int(source_payload.get("external_reference_count"))
    proxy_count = _as_int(source_payload.get("statsbomb_event_proxy_count"))
    missing_count = _as_int(source_payload.get("no_review_evidence_count"))
    settled_count = _as_int(source_payload.get("total_settled_count"))
    memory_sample_count = _as_int(monitor.get("sample_count"))
    blocking_count = _as_int(health.get("blocking_count"))
    warning_count = _as_int(health.get("warning_count"))
    action_count = len([row for row in action_rows if isinstance(row, dict)])
    card_count = len([row for row in card_rows if isinstance(row, dict)])
    issue_count = blocking_count + warning_count

    summary_text = (
        f"memory {memory_status} | source {coverage_status} | "
        f"missing {missing_count}/{settled_count}"
    )
    body = (
        f"记忆 {memory_status} | 来源 {coverage_status} | 已结算 {settled_count}\n"
        f"本地视频 {local_count} | 外部回放 {external_count} | "
        f"事件代理 {proxy_count} | 缺证据 {missing_count}\n"
        f"记忆样本 {memory_sample_count} | 健康问题 {issue_count} | 待处理动作 {action_count}"
    )

    return {
        "status": status,
        "tone": tone,
        "status_label": status_label,
        "summary_text": summary_text,
        "title": f"AI视频复盘 | {status_label}",
        "body": body,
        "memory_status": memory_status,
        "coverage_status": coverage_status,
        "settled_count": settled_count,
        "local_video_count": local_count,
        "external_reference_count": external_count,
        "statsbomb_event_proxy_count": proxy_count,
        "no_review_evidence_count": missing_count,
        "memory_sample_count": memory_sample_count,
        "blocking_count": blocking_count,
        "warning_count": warning_count,
        "issue_count": issue_count,
        "action_count": action_count,
        "card_count": card_count,
    }


def build_video_review_center_action_rows(
    video_memory_health: dict | object,
    video_source_coverage: dict | object,
    *,
    limit: int = 6,
) -> list[dict[str, object]]:
    def _payload(value: dict | object) -> dict:
        return value if isinstance(value, dict) else {}

    def _action_key_for_code(code: str) -> str:
        if code == "video_memory_duplicate_keys":
            return "export_video_review_fewshot_memory_audit"
        if code in {"video_memory_backup_missing"}:
            return "export_video_review_fewshot_memory_audit"
        if code in {"video_memory_missing"}:
            return "preview_video_review_fewshot_merge_bundle"
        if code in {"video_memory_low_samples"}:
            return "export_video_review_fewshot_samples"
        if code in {"video_memory_no_current_match", "video_memory_ready"}:
            return "open_review_center"
        if code in {"video_memory_root_concentration", "video_memory_source_concentration"}:
            return "preview_video_review_fewshot_merge_bundle"
        if code.startswith("gap:"):
            return "open_review_center"
        return "open_ai_video_review_center_window"

    memory_payload = _payload(video_memory_health)
    source_payload = _payload(video_source_coverage)
    monitor = _payload(memory_payload.get("monitor"))
    quality = _payload(memory_payload.get("quality"))
    health = _payload(memory_payload.get("health"))
    memory_rows = build_video_review_fewshot_action_rows(monitor, quality, health, limit=max(0, int(limit)))
    rows: list[dict[str, object]] = []
    seen: set[str] = set()

    missing_evidence_count = int(source_payload.get("no_review_evidence_count", 0) or 0)
    if missing_evidence_count > 0:
        rows.append(
            {
                "code": "video_review_missing_local_video",
                "action_key": "open_video_review_evidence_gap_center_window_local_video",
                "title": "导入本地视频",
                "body": f"当前缺证据 {missing_evidence_count} 场，优先筛到本地视频并导入授权录像，再回到专项中心复核。",
                "priority": 0,
                "tone": "bad",
            }
        )
        rows.append(
            {
                "code": "video_review_missing_external_reference",
                "action_key": "open_video_review_evidence_gap_center_window_external_reference",
                "title": "绑定 FIFA+ 回放",
                "body": f"当前缺证据 {missing_evidence_count} 场，优先绑定 FIFA+ 或其他合法回放链接完成闭环，再回到专项中心复核。",
                "priority": 1,
                "tone": "warning",
            }
        )
        seen.add("video_review_missing_local_video")
        seen.add("video_review_missing_external_reference")

    for row in memory_rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("code") or "")
        if code in seen:
            continue
        seen.add(code)
        enriched = dict(row)
        enriched["action_key"] = _action_key_for_code(code)
        rows.append(enriched)

    if not rows:
        rows.append(
            {
                "code": "video_memory_ready",
                "action_key": "open_review_center",
                "title": "进入稳定性复盘",
                "body": "视频记忆池当前没有阻塞问题，可回到复盘中心继续观察样本导入、证据回收与归因稳定性。",
                "priority": 99,
                "tone": "good",
            }
        )

    def _priority_value(row: dict[str, object]) -> int:
        try:
            return int(row.get("priority", 99))
        except (TypeError, ValueError):
            return 99

    rows.sort(key=lambda row: (_priority_value(row), str(row.get("title") or "")))
    return rows[: max(0, int(limit))]


def build_video_review_evidence_gap_quick_open_filters(
    evidence_filter: str | None = None,
    state: dict | object | None = None,
) -> dict[str, str]:
    kind = str(evidence_filter or "").strip()
    base = {
        "batch_filter": "latest",
        "status_filter": "all",
        "priority_filter": "all",
        "evidence_filter": "all",
    }
    if kind in {"local_video", "external_reference"}:
        base["status_filter"] = "pending"
        base["priority_filter"] = "P0"
        base["evidence_filter"] = kind
        batches = [item for item in ((state.get("batches") if isinstance(state, dict) else []) or []) if isinstance(item, dict)]
        for batch in batches:
            batch_id = str(batch.get("batch_id") or "").strip()
            if not batch_id:
                continue
            result = build_video_review_evidence_gap_batch_filter_result(
                state,
                batch_filter=batch_id,
                status_filter=base["status_filter"],
                priority_filter=base["priority_filter"],
                evidence_filter=base["evidence_filter"],
            )
            items = result.get("items") if isinstance(result, dict) else []
            if isinstance(items, list) and items:
                base["batch_filter"] = batch_id
                return base
        return base
    return base


def build_video_review_evidence_gap_quick_target_item(
    state: dict | object | None,
    evidence_filter: str | None = None,
) -> dict[str, object] | None:
    filters = build_video_review_evidence_gap_quick_open_filters(evidence_filter, state)
    result = build_video_review_evidence_gap_batch_filter_result(
        state if isinstance(state, dict) else {},
        batch_filter=filters["batch_filter"],
        status_filter=filters["status_filter"],
        priority_filter=filters["priority_filter"],
        evidence_filter=filters["evidence_filter"],
    )
    items = result.get("items") if isinstance(result, dict) else []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                return item
    return None


def build_statsbomb_review_training_quality_export_message(path: Path, quality: dict, record_count: int) -> str:
    return "\n".join(
        [
            "StatsBomb/Event Proxy 样本质量报告已导出",
            "",
            f"文件: {path}",
            f"质量状态: {quality.get('status') or '-'}",
            f"样本: {quality.get('sample_count', 0) or 0}",
            f"问题数: {quality.get('issue_count', 0) or 0}",
            f"修复记录: {record_count}",
            "",
            "该报告只描述赛后复盘样本质量，不代表赛前预测结论。",
        ]
    )


def build_video_review_evidence_gap_action_rows(
    settlements: list[dict] | object,
    statsbomb_samples: dict | list | object | None = None,
    *,
    limit: int = 6,
) -> list[dict[str, object]]:
    def _items(value: object) -> list[dict]:
        if isinstance(value, dict):
            for key in ("items", "rows", "settlements"):
                resolved = value.get(key)
                if isinstance(resolved, list):
                    return [item for item in resolved if isinstance(item, dict)]
            return []
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return []

    def _match_id(item: dict) -> str:
        match = item.get("match") if isinstance(item.get("match"), dict) else {}
        meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
        return str(
            item.get("match_id")
            or match.get("match_id")
            or meta.get("match_id")
            or item.get("source_match_id")
            or meta.get("source_match_id")
            or ""
        ).strip()

    def _has_video(settlement: dict) -> bool:
        review = settlement.get("video_review") if isinstance(settlement.get("video_review"), dict) else {}
        video = review.get("video") if isinstance(review.get("video"), dict) else {}
        if not video and isinstance(settlement.get("video"), dict):
            video = settlement.get("video") or {}
        source_policy = review.get("source_policy") if isinstance(review.get("source_policy"), dict) else {}
        source_type = str(video.get("source_type") or "").strip().lower()
        return bool(
            source_type in {"local_file", "local_video", "file", "external_reference"}
            or video.get("path")
            or video.get("url")
            or source_policy.get("mode") == "reference_only"
            or str(video.get("probe_status") or "").strip().lower() == "external_reference"
        )

    def _as_float(value: object) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _is_false(value: object) -> bool:
        if value is False:
            return True
        text = str(value).strip().lower()
        return text in {"false", "0", "miss", "missed", "no", "错", "未命中"}

    def _date_sort_value(value: object) -> float:
        text = str(value or "").strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M"):
            try:
                return datetime.strptime(text, fmt).timestamp()
            except ValueError:
                continue
        return 0.0

    def _priority(settlement: dict) -> tuple[int, list[str]]:
        score = 0
        reasons: list[str] = []
        confidence = max(
            _as_float(settlement.get("prediction_confidence")),
            _as_float(settlement.get("confidence")),
        )
        if _is_false(settlement.get("is_correct")):
            if confidence >= 0.65:
                score += 60
                reasons.append("高置信1X2失误")
            else:
                score += 25
                reasons.append("1X2失误")

        miss_fields = [
            ("handicap_is_correct", "让球"),
            ("ou_is_correct", "大小球"),
            ("total_goals_is_correct", "总进球"),
            ("score_is_correct", "比分"),
        ]
        miss_labels = [label for key, label in miss_fields if _is_false(settlement.get(key))]
        if miss_labels:
            score += min(24, 8 * len(miss_labels))
            reasons.append("多玩法失误: " + "/".join(miss_labels[:3]))

        strategy_items = settlement.get("high_accuracy_strategy_items")
        if isinstance(strategy_items, list):
            missed_items = [
                item
                for item in strategy_items
                if isinstance(item, dict)
                and (_is_false(item.get("is_hit")) or _is_false(item.get("is_correct")))
            ]
            if missed_items:
                score += 35
                max_item_conf = max((_as_float(item.get("confidence")) for item in missed_items), default=0.0)
                if max_item_conf >= 0.65:
                    score += 10
                reasons.append("高准策略失误")

        allowlist_decision = str(settlement.get("strategy_allowlist_decision") or "").strip().lower()
        allowlist_status = str(settlement.get("strategy_allowlist_status") or "").strip().lower()
        if allowlist_decision == "allow" or allowlist_status == "settled" or settlement.get("strategy_allowlist_file"):
            score += 20
            reasons.append("放行策略复盘")

        league_text = str(settlement.get("league") or "").lower()
        important_tokens = (
            "world cup",
            "世界杯",
            "fifa",
            "uefa",
            "euro",
            "champions",
            "premier",
            "la liga",
            "serie a",
            "bundesliga",
            "ligue 1",
        )
        if any(token in league_text for token in important_tokens):
            score += 12
            reasons.append("重点赛事")

        if not reasons:
            reasons.append("常规缺证据")
        return score, reasons

    def _priority_label(score: int) -> str:
        if score >= 90:
            return "P0"
        if score >= 60:
            return "P1"
        if score >= 30:
            return "P2"
        return "P3"

    proxy_ids: set[str] = set()
    for sample in _items(statsbomb_samples):
        meta = sample.get("meta") if isinstance(sample.get("meta"), dict) else {}
        source_text = f"{sample.get('source') or ''} {meta.get('source') or ''}".lower()
        if "statsbomb" in source_text or "event_proxy" in source_text or "event-sandbox" in source_text:
            sample_match_id = _match_id(sample)
            if sample_match_id:
                proxy_ids.add(sample_match_id)

    rows: list[dict[str, object]] = []
    for index, settlement in enumerate(_items(settlements)):
        match_id = _match_id(settlement)
        has_proxy = bool(settlement.get("statsbomb_event_summary")) or bool(match_id and match_id in proxy_ids)
        if _has_video(settlement) or has_proxy:
            continue
        home = str(settlement.get("home_team") or "-")
        away = str(settlement.get("away_team") or "-")
        league = str(settlement.get("league") or "-")
        date_text = str(settlement.get("match_date") or settlement.get("date") or "-")
        title = f"{date_text} | {league} | {home} vs {away}"
        priority_score, priority_reasons = _priority(settlement)
        priority_label = _priority_label(priority_score)
        rows.append(
            {
                "index": index,
                "match_id": match_id,
                "title": title,
                "action_key": "bind_external_reference",
                "tone": "warning",
                "priority_score": priority_score,
                "priority_label": priority_label,
                "priority_reasons": priority_reasons,
                "date_sort": _date_sort_value(date_text),
                "body": (
                    f"优先级 {priority_label} / score {priority_score} | 原因: {', '.join(priority_reasons[:4])}\n"
                    "缺少本地视频、外部回放链接和 StatsBomb/Event Proxy 证据。\n"
                    "优先绑定合法回放链接；如后续补到 StatsBomb 事件摘要，再生成事件代理复盘样本；否则仅保留低置信复盘。"
                ),
                "settlement": settlement,
            }
        )
    rows.sort(
        key=lambda row: (
            -int(row.get("priority_score", 0) or 0),
            -float(row.get("date_sort", 0.0) or 0.0),
            int(row.get("index", 0) or 0),
        )
    )
    for row in rows:
        row.pop("date_sort", None)
    return rows[: max(0, int(limit))]


def build_video_review_evidence_gap_batch_plan_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"video_review_evidence_gap_batch_plan_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_video_review_evidence_gap_batch_id(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"evidence_gap_batch_{current.strftime('%Y%m%d_%H%M%S')}"


def build_video_review_evidence_gap_batch_plan_lines(
    rows: list[dict] | object,
    *,
    generated_at: datetime | None = None,
    batch_id: str | object = "",
) -> list[str]:
    def _clean(value: object) -> str:
        text = str(value if value not in (None, "") else "-").replace("\n", " ").strip()
        return text.replace("|", "\\|") or "-"

    def _row_items(value: object) -> list[dict]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def _suggested_action(priority_label: str) -> str:
        if priority_label in {"P0", "P1"}:
            return "优先绑定合法回放链接，并补关键事件时间点"
        if priority_label == "P2":
            return "补合法回放链接；无回放时转 StatsBomb/Event Proxy 复盘样本"
        return "后置处理；保留低置信复盘或等待事件代理样本"

    generated = generated_at or datetime.now()
    gap_rows = _row_items(rows)
    lines = [
        "# 视频复盘证据缺口批次计划",
        "",
        f"- Generated At: {generated.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Batch ID: {str(batch_id or '-').strip() or '-'}",
        f"- Total Gap Rows: {len(gap_rows)}",
        "- Priority Rule: P0/P1 优先处理高置信 1X2 失误、多玩法失误、高准策略失误、放行策略复盘和重点赛事。",
        "- Source Boundary: use legal replay links only; no auto video download; StatsBomb/Event Proxy is post-match review evidence only and must not enter pre-match features.",
        "",
        "## 处理批次",
        "",
    ]
    if not gap_rows:
        lines.append("- 当前没有待处理证据缺口。")
        return lines

    lines.extend(
        [
            "| 优先级 | 分数 | 日期 | 联赛 | 对阵 | match_id | 原因 | 建议动作 |",
            "| --- | ---: | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in gap_rows:
        settlement = row.get("settlement") if isinstance(row.get("settlement"), dict) else {}
        home = settlement.get("home_team") or "-"
        away = settlement.get("away_team") or "-"
        priority_label = str(row.get("priority_label") or "P3")
        reasons = row.get("priority_reasons") if isinstance(row.get("priority_reasons"), list) else []
        reason_text = ", ".join(str(reason) for reason in reasons[:5]) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    _clean(priority_label),
                    _clean(row.get("priority_score", 0)),
                    _clean(settlement.get("match_date") or settlement.get("date") or "-"),
                    _clean(settlement.get("league") or "-"),
                    _clean(f"{home} vs {away}"),
                    _clean(row.get("match_id") or settlement.get("match_id") or "-"),
                    _clean(reason_text),
                    _clean(_suggested_action(priority_label)),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 执行边界",
            "",
            "- 只绑定合法回放链接或本地授权视频文件，不自动下载第三方视频。",
            "- StatsBomb/Event Proxy 只作为赛后复盘证据，不写入赛前预测特征。",
            "- 处理 P0/P1 后应重新生成视频复盘样本或事件代理复盘样本，再进入记忆合并审计。",
        ]
    )
    return lines


def build_video_review_evidence_gap_batch_plan_export_message(
    path: Path,
    rows: list[dict] | object,
    batch_record: dict | object | None = None,
) -> str:
    count = len(rows) if isinstance(rows, list) else 0
    batch = batch_record if isinstance(batch_record, dict) else {}
    batch_id = str(batch.get("batch_id") or "-")
    return "\n".join(
        [
            "复盘证据缺口批次计划已导出",
            "",
            f"文件: {path}",
            f"批次: {batch_id}",
            f"待处理: {count} 场",
            "",
            "边界: 只使用合法回放链接或授权本地视频；不自动下载视频；StatsBomb/Event Proxy 仅用于赛后复盘。",
        ]
    )


def _recompute_video_review_evidence_gap_batch(batch: dict) -> dict:
    items = [item for item in batch.get("items", []) if isinstance(item, dict)]
    total_count = len(items)
    completed_count = sum(1 for item in items if str(item.get("status") or "") == "resolved")
    pending_count = max(0, total_count - completed_count)
    completion_rate = 1.0 if total_count == 0 else completed_count / total_count
    if pending_count <= 0:
        status = "completed"
    elif completed_count > 0:
        status = "active"
    else:
        status = "pending"
    batch["items"] = items
    batch["total_count"] = total_count
    batch["completed_count"] = completed_count
    batch["pending_count"] = pending_count
    batch["completion_rate"] = round(completion_rate, 4)
    batch["status"] = status
    return batch


def build_video_review_evidence_gap_batch_record(
    rows: list[dict] | object,
    report_path: Path | str,
    *,
    generated_at: datetime | None = None,
    batch_id: str | object = "",
) -> dict[str, object]:
    generated = generated_at or datetime.now()
    resolved_batch_id = str(batch_id or build_video_review_evidence_gap_batch_id(generated)).strip()
    row_items = [item for item in rows if isinstance(item, dict)] if isinstance(rows, list) else []
    batch_items: list[dict[str, object]] = []
    for index, row in enumerate(row_items):
        settlement = row.get("settlement") if isinstance(row.get("settlement"), dict) else {}
        match_id = str(row.get("match_id") or settlement.get("match_id") or "").strip()
        title = str(row.get("title") or "-")
        batch_items.append(
            {
                "index": index,
                "match_id": match_id,
                "title": title,
                "priority_label": str(row.get("priority_label") or "P3"),
                "priority_score": int(row.get("priority_score", 0) or 0),
                "priority_reasons": [
                    str(reason)
                    for reason in (row.get("priority_reasons") if isinstance(row.get("priority_reasons"), list) else [])
                ],
                "status": "pending",
                "created_at": generated.strftime("%Y-%m-%d %H:%M:%S"),
                "handled_at": "",
                "handled_by": "",
                "source_name": "",
                "evidence_kind": "",
                "review_id": "",
            }
        )
    batch = {
        "batch_id": resolved_batch_id,
        "created_at": generated.strftime("%Y-%m-%d %H:%M:%S"),
        "report_path": str(report_path),
        "items": batch_items,
    }
    return _recompute_video_review_evidence_gap_batch(batch)


def build_video_review_evidence_gap_batch_state_with_record(
    state: dict | object,
    batch_record: dict | object,
    *,
    limit: int = 20,
) -> dict[str, object]:
    batch = dict(batch_record) if isinstance(batch_record, dict) else {}
    batches = [item for item in ((state.get("batches") if isinstance(state, dict) else []) or []) if isinstance(item, dict)]
    batch_id = str(batch.get("batch_id") or "").strip()
    if batch_id:
        batches = [item for item in batches if str(item.get("batch_id") or "") != batch_id]
    batches = [batch, *batches] if batch else batches
    batches = [_recompute_video_review_evidence_gap_batch(dict(item)) for item in batches[: max(1, int(limit))]]
    updated_at = str(batch.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return {"schema_version": 1, "updated_at": updated_at, "batches": batches}


def collect_video_review_evidence_gap_sample_match_ids(samples: dict | list | object) -> set[str]:
    def _items(value: object) -> list[dict]:
        if isinstance(value, dict):
            for key in ("items", "rows", "samples"):
                resolved = value.get(key)
                if isinstance(resolved, list):
                    return [item for item in resolved if isinstance(item, dict)]
            return []
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return []

    match_ids: set[str] = set()
    for sample in _items(samples):
        match = sample.get("match") if isinstance(sample.get("match"), dict) else {}
        meta = sample.get("meta") if isinstance(sample.get("meta"), dict) else {}
        match_id = str(
            sample.get("match_id")
            or match.get("match_id")
            or meta.get("match_id")
            or sample.get("source_match_id")
            or meta.get("source_match_id")
            or ""
        ).strip()
        if match_id:
            match_ids.add(match_id)
    return match_ids


def build_video_review_evidence_gap_batch_state_with_resolution(
    state: dict | object,
    match_ids: set[str] | list[str] | tuple[str, ...] | str | object,
    *,
    evidence_kind: str,
    source_name: str = "",
    review_id: str = "",
    handled_by: str = "app_operator",
    handled_at: datetime | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    if isinstance(match_ids, str):
        normalized_ids = {match_ids.strip()} if match_ids.strip() else set()
    elif isinstance(match_ids, (set, list, tuple)):
        normalized_ids = {str(match_id).strip() for match_id in match_ids if str(match_id).strip()}
    else:
        normalized_ids = set()
    batches = [item for item in ((state.get("batches") if isinstance(state, dict) else []) or []) if isinstance(item, dict)]
    handled_text = (handled_at or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    updated_count = 0
    touched_batches: list[str] = []
    touched_match_ids: set[str] = set()
    updated_batches: list[dict] = []
    for batch in batches:
        next_batch = dict(batch)
        next_items: list[dict] = []
        batch_changed = False
        for item in [entry for entry in next_batch.get("items", []) if isinstance(entry, dict)]:
            next_item = dict(item)
            item_match_id = str(next_item.get("match_id") or "").strip()
            if item_match_id in normalized_ids and str(next_item.get("status") or "") != "resolved":
                next_item.update(
                    {
                        "status": "resolved",
                        "handled_at": handled_text,
                        "handled_by": handled_by,
                        "source_name": source_name,
                        "evidence_kind": evidence_kind,
                        "review_id": review_id,
                    }
                )
                updated_count += 1
                batch_changed = True
                touched_match_ids.add(item_match_id)
            next_items.append(next_item)
        next_batch["items"] = next_items
        if batch_changed:
            touched_batches.append(str(next_batch.get("batch_id") or "-"))
        updated_batches.append(_recompute_video_review_evidence_gap_batch(next_batch))
    updated_state = {
        "schema_version": 1,
        "updated_at": handled_text if updated_count else str((state.get("updated_at") if isinstance(state, dict) else "") or ""),
        "batches": updated_batches,
    }
    update = {
        "updated_count": updated_count,
        "batch_ids": touched_batches,
        "match_ids": sorted(touched_match_ids),
        "evidence_kind": evidence_kind,
        "source_name": source_name,
        "review_id": review_id,
        "handled_at": handled_text,
    }
    return updated_state, update


def build_video_review_evidence_gap_batch_status(state: dict | object) -> dict[str, object]:
    batches = [item for item in ((state.get("batches") if isinstance(state, dict) else []) or []) if isinstance(item, dict)]
    if not batches:
        return {
            "status": "no_batch",
            "summary_text": "暂无缺口处理批次",
            "batch_count": 0,
            "total_count": 0,
            "completed_count": 0,
            "pending_count": 0,
            "completion_rate": 0.0,
            "latest_batch": {},
        }
    recomputed = [_recompute_video_review_evidence_gap_batch(dict(batch)) for batch in batches]
    total_count = sum(int(batch.get("total_count", 0) or 0) for batch in recomputed)
    completed_count = sum(int(batch.get("completed_count", 0) or 0) for batch in recomputed)
    pending_count = sum(int(batch.get("pending_count", 0) or 0) for batch in recomputed)
    completion_rate = 1.0 if total_count == 0 else completed_count / total_count
    latest = recomputed[0]
    status = "completed" if pending_count == 0 else "active" if completed_count else "pending"
    return {
        "status": status,
        "summary_text": f"批次 {len(recomputed)} 个 | 已处理 {completed_count}/{total_count} | 待处理 {pending_count}",
        "batch_count": len(recomputed),
        "total_count": total_count,
        "completed_count": completed_count,
        "pending_count": pending_count,
        "completion_rate": round(completion_rate, 4),
        "latest_batch": latest,
    }


def build_video_review_evidence_gap_batch_status_rows(state: dict | object, *, limit: int = 3) -> list[dict[str, object]]:
    batches = [item for item in ((state.get("batches") if isinstance(state, dict) else []) or []) if isinstance(item, dict)]
    if not batches:
        return [
            {
                "title": "暂无缺口批次",
                "body": "导出缺口批次计划后，系统会跟踪绑定回放或生成事件代理样本后的处理进度。",
                "tone": "neutral",
            }
        ]
    rows: list[dict[str, object]] = []
    for batch in [_recompute_video_review_evidence_gap_batch(dict(item)) for item in batches[: max(0, int(limit))]]:
        pending = int(batch.get("pending_count", 0) or 0)
        completed = int(batch.get("completed_count", 0) or 0)
        total = int(batch.get("total_count", 0) or 0)
        rate = float(batch.get("completion_rate", 0) or 0)
        handled_items = [
            item
            for item in batch.get("items", [])
            if isinstance(item, dict) and str(item.get("status") or "") == "resolved"
        ]
        latest_handled = handled_items[-1] if handled_items else {}
        latest_text = (
            f"最近处理: {latest_handled.get('handled_at', '-')} | "
            f"{latest_handled.get('source_name', '-') or '-'} | {latest_handled.get('evidence_kind', '-') or '-'}"
            if latest_handled
            else "最近处理: -"
        )
        rows.append(
            {
                "title": f"{batch.get('batch_id', '-')} | 完成率 {rate:.0%}",
                "body": (
                    f"状态: {batch.get('status', '-')} | 总数 {total} | 已处理 {completed} | 待处理 {pending}\n"
                    f"报告: {batch.get('report_path', '-')}\n"
                    f"{latest_text}"
                ),
                "tone": "good" if pending == 0 else "warning" if completed else "neutral",
            }
        )
    return rows


def build_video_review_evidence_gap_batch_filter_options(state: dict | object) -> dict[str, object]:
    batches = [
        _recompute_video_review_evidence_gap_batch(dict(item))
        for item in ((state.get("batches") if isinstance(state, dict) else []) or [])
        if isinstance(item, dict)
    ]
    batch_options = [
        {"label": "最新批次", "value": "latest"},
        {"label": "全部批次", "value": "all"},
    ]
    for batch in batches:
        batch_id = str(batch.get("batch_id") or "").strip()
        if batch_id:
            pending = int(batch.get("pending_count", 0) or 0)
            total = int(batch.get("total_count", 0) or 0)
            batch_options.append({"label": f"{batch_id} ({pending}/{total} 待处理)", "value": batch_id})
    return {
        "batch_options": batch_options,
        "status_options": [
            {"label": "全部状态", "value": "all"},
            {"label": "未处理", "value": "pending"},
            {"label": "已处理", "value": "resolved"},
        ],
        "priority_options": [
            {"label": "全部优先级", "value": "all"},
            {"label": "P0", "value": "P0"},
            {"label": "P1", "value": "P1"},
            {"label": "P2", "value": "P2"},
            {"label": "P3", "value": "P3"},
        ],
        "evidence_options": [
            {"label": "全部证据", "value": "all"},
            {"label": "缺证据", "value": "missing"},
            {"label": "视频证据", "value": "video"},
            {"label": "事件代理", "value": "event_proxy"},
            {"label": "本地视频", "value": "local_video"},
            {"label": "外部回放", "value": "external_reference"},
            {"label": "StatsBomb/Event Proxy", "value": "statsbomb_event_proxy"},
        ],
    }


def build_video_review_evidence_gap_batch_filter_result(
    state: dict | object,
    *,
    batch_filter: str = "latest",
    status_filter: str = "all",
    priority_filter: str = "all",
    evidence_filter: str = "all",
) -> dict[str, object]:
    def _evidence_kind(item: dict) -> str:
        kind = str(item.get("evidence_kind") or "").strip()
        if kind:
            return kind
        return "missing" if str(item.get("status") or "") != "resolved" else "-"

    def _evidence_matches(kind: str, expected: str) -> bool:
        if expected == "all":
            return True
        if expected == "video":
            return kind in {"local_video", "external_reference"}
        if expected == "event_proxy":
            return kind == "statsbomb_event_proxy"
        return kind == expected

    batches = [
        _recompute_video_review_evidence_gap_batch(dict(item))
        for item in ((state.get("batches") if isinstance(state, dict) else []) or [])
        if isinstance(item, dict)
    ]
    selected_batches: list[dict]
    resolved_batch_filter = str(batch_filter or "latest")
    if resolved_batch_filter == "all":
        selected_batches = batches
    elif resolved_batch_filter == "latest":
        selected_batches = batches[:1]
    else:
        selected_batches = [batch for batch in batches if str(batch.get("batch_id") or "") == resolved_batch_filter]

    selected_items: list[dict[str, object]] = []
    for batch in selected_batches:
        batch_id = str(batch.get("batch_id") or "-")
        for item in [entry for entry in batch.get("items", []) if isinstance(entry, dict)]:
            status = str(item.get("status") or "pending")
            priority = str(item.get("priority_label") or "-")
            evidence_kind = _evidence_kind(item)
            if status_filter != "all" and status != status_filter:
                continue
            if priority_filter != "all" and priority != priority_filter:
                continue
            if not _evidence_matches(evidence_kind, str(evidence_filter or "all")):
                continue
            selected_items.append(
                {
                    "batch_id": batch_id,
                    "match_id": str(item.get("match_id") or "-"),
                    "title": str(item.get("title") or "-"),
                    "priority_label": priority,
                    "priority_score": int(item.get("priority_score", 0) or 0),
                    "priority_reasons": item.get("priority_reasons") if isinstance(item.get("priority_reasons"), list) else [],
                    "status": status,
                    "evidence_kind": evidence_kind,
                    "source_name": str(item.get("source_name") or "-"),
                    "handled_at": str(item.get("handled_at") or "-"),
                    "handled_by": str(item.get("handled_by") or "-"),
                    "review_id": str(item.get("review_id") or "-"),
                    "report_path": str(batch.get("report_path") or "-"),
                }
            )

    pending_count = sum(1 for item in selected_items if item.get("status") != "resolved")
    resolved_count = sum(1 for item in selected_items if item.get("status") == "resolved")
    video_count = sum(1 for item in selected_items if item.get("evidence_kind") in {"local_video", "external_reference"})
    event_proxy_count = sum(1 for item in selected_items if item.get("evidence_kind") == "statsbomb_event_proxy")
    missing_count = sum(1 for item in selected_items if item.get("evidence_kind") == "missing")
    priority_counts = Counter(str(item.get("priority_label") or "-") for item in selected_items)
    return {
        "filters": {
            "batch": resolved_batch_filter,
            "status": status_filter,
            "priority": priority_filter,
            "evidence": evidence_filter,
        },
        "items": selected_items,
        "summary": {
            "total_count": len(selected_items),
            "pending_count": pending_count,
            "resolved_count": resolved_count,
            "video_count": video_count,
            "event_proxy_count": event_proxy_count,
            "missing_count": missing_count,
            "priority_counts": dict(priority_counts),
            "summary_text": (
                f"匹配 {len(selected_items)} 项 | 未处理 {pending_count} | 已处理 {resolved_count} | "
                f"视频 {video_count} | 事件代理 {event_proxy_count} | 缺证据 {missing_count}"
            ),
        },
    }


def build_video_review_evidence_gap_batch_filter_rows(
    filter_result: dict | object,
    *,
    limit: int = 80,
) -> list[dict[str, object]]:
    items = filter_result.get("items") if isinstance(filter_result, dict) else []
    if not isinstance(items, list):
        return []
    rows: list[dict[str, object]] = []
    for item in [entry for entry in items if isinstance(entry, dict)][: max(0, int(limit))]:
        status = str(item.get("status") or "pending")
        evidence = str(item.get("evidence_kind") or "-")
        rows.append(
            {
                "batch_id": str(item.get("batch_id") or "-"),
                "match_id": str(item.get("match_id") or "-"),
                "priority": str(item.get("priority_label") or "-"),
                "score": str(item.get("priority_score") or 0),
                "status": "已处理" if status == "resolved" else "未处理",
                "evidence": evidence,
                "source": str(item.get("source_name") or "-"),
                "handled_at": str(item.get("handled_at") or "-"),
                "title": str(item.get("title") or "-"),
                "body": (
                    f"{item.get('batch_id', '-')} | {item.get('match_id', '-')}\n"
                    f"证据: {evidence} | 来源: {item.get('source_name', '-') or '-'} | 处理时间: {item.get('handled_at', '-') or '-'}"
                ),
                "tone": "good" if status == "resolved" else "warning",
            }
        )
    return rows


def build_video_review_evidence_gap_batch_filter_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"video_review_evidence_gap_batch_filter_report_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_video_review_evidence_gap_batch_filter_report_lines(
    filter_result: dict | object,
    *,
    generated_at: datetime | None = None,
) -> list[str]:
    def _clean(value: object) -> str:
        text = str(value if value not in (None, "") else "-").replace("\n", " ").strip()
        return text.replace("|", "\\|") or "-"

    result = filter_result if isinstance(filter_result, dict) else {}
    filters = result.get("filters") if isinstance(result.get("filters"), dict) else {}
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    rows = build_video_review_evidence_gap_batch_filter_rows(result, limit=500)
    generated = generated_at or datetime.now()
    lines = [
        "# 复盘证据缺口批次处理报告",
        "",
        f"- Generated At: {generated.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Batch Filter: {filters.get('batch', '-')}",
        f"- Status Filter: {filters.get('status', '-')}",
        f"- Priority Filter: {filters.get('priority', '-')}",
        f"- Evidence Filter: {filters.get('evidence', '-')}",
        f"- Summary: {summary.get('summary_text', '-')}",
        "- Boundary: use legal replay links only; no auto video download; StatsBomb/Event Proxy is post-match review evidence only.",
        "",
        "## 明细",
        "",
    ]
    if not rows:
        lines.append("- 当前筛选条件下没有匹配记录。")
        return lines
    lines.extend(
        [
            "| 优先级 | 分数 | 状态 | 证据 | 来源 | 处理时间 | match_id | 场次 |",
            "| --- | ---: | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _clean(row.get("priority")),
                    _clean(row.get("score")),
                    _clean(row.get("status")),
                    _clean(row.get("evidence")),
                    _clean(row.get("source")),
                    _clean(row.get("handled_at")),
                    _clean(row.get("match_id")),
                    _clean(row.get("title")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 处理建议",
            "",
            "- P0/P1 且未处理的记录优先绑定合法外部回放或本地授权视频。",
            "- 无合法视频来源时，优先生成 StatsBomb/Event Proxy 复盘样本并回写批次状态。",
            "- 已处理记录进入视频复盘样本或事件代理样本审计，不进入赛前预测特征。",
        ]
    )
    return lines


def build_video_review_evidence_gap_batch_filter_report_message(path: Path, filter_result: dict | object) -> str:
    summary = filter_result.get("summary") if isinstance(filter_result, dict) and isinstance(filter_result.get("summary"), dict) else {}
    return "\n".join(
        [
            "复盘证据缺口批次处理报告已导出",
            "",
            f"文件: {path}",
            str(summary.get("summary_text") or "-"),
            "",
            "边界: 只使用合法回放链接或授权本地视频；不自动下载视频；事件代理仅用于赛后复盘。",
        ]
    )


def find_video_review_evidence_gap_settlement(settlements: list[dict] | object, match_id: str | object) -> dict | None:
    resolved_id = str(match_id or "").strip()
    if not resolved_id or not isinstance(settlements, list):
        return None
    for settlement in settlements:
        if isinstance(settlement, dict) and str(settlement.get("match_id") or "").strip() == resolved_id:
            return settlement
    return None


def build_video_review_evidence_gap_batch_action_rows(selected_item: dict | object) -> list[dict[str, object]]:
    if not isinstance(selected_item, dict) or not selected_item:
        return [
            {
                "action_key": "select_gap_item",
                "label": "选择记录",
                "enabled": False,
                "tone": "neutral",
                "body": "请先在批次表格中选择一条缺口记录。",
            }
        ]
    status = str(selected_item.get("status") or "pending")
    match_id = str(selected_item.get("match_id") or "").strip()
    has_match_id = bool(match_id and match_id != "-")
    rows: list[dict[str, object]] = [
        {
            "action_key": "show_settlement_detail",
            "label": "场次详情",
            "enabled": has_match_id,
            "tone": "info",
            "body": "在当前窗口查看该场复盘详情和错因上下文。",
        }
    ]
    if status == "resolved":
        rows.append(
            {
                "action_key": "refresh_batch_status",
                "label": "刷新状态",
                "enabled": True,
                "tone": "good",
                "body": "该记录已处理，可刷新批次状态查看最新完成率。",
            }
        )
        return rows
    rows.extend(
        [
            {
                "action_key": "bind_external_reference",
                "label": "绑定外部回放",
                "enabled": has_match_id,
                "tone": "warning",
                "body": "为该场绑定合法回放链接，完成后自动回写批次状态。",
            },
            {
                "action_key": "import_local_video",
                "label": "导入本地视频",
                "enabled": has_match_id,
                "tone": "warning",
                "body": "导入本地授权视频文件，完成后自动回写批次状态。",
            },
            {
                "action_key": "build_statsbomb_review_samples",
                "label": "生成事件代理样本",
                "enabled": True,
                "tone": "info",
                "body": "重建 StatsBomb/Event Proxy 复盘样本，并按 match_id 自动回写命中的批次项。",
            },
        ]
    )
    return rows


def build_video_review_evidence_gap_feedback(
    settlement: dict,
    result: dict | None = None,
    *,
    source_name: str = "",
    occurred_at: datetime | None = None,
) -> dict[str, object]:
    payload = result if isinstance(result, dict) else {}
    review = settlement.get("video_review") if isinstance(settlement.get("video_review"), dict) else {}
    video = review.get("video") if isinstance(review.get("video"), dict) else {}
    if not video and isinstance(settlement.get("video"), dict):
        video = settlement.get("video") or {}
    source_policy = review.get("source_policy") if isinstance(review.get("source_policy"), dict) else {}
    source_type = str(video.get("source_type") or "").strip().lower()
    has_video = bool(
        source_type in {"local_file", "local_video", "file", "external_reference"}
        or video.get("path")
        or video.get("url")
        or source_policy.get("mode") == "reference_only"
        or str(video.get("probe_status") or "").strip().lower() == "external_reference"
    )
    if has_video:
        before_kind = "video_ready"
    elif settlement.get("statsbomb_event_summary"):
        before_kind = "event_proxy_ready"
    else:
        before_kind = "missing_evidence"
    ok = bool(payload.get("ok", True))
    after_kind = "external_reference" if ok else before_kind
    outcome = "resolved" if ok and before_kind == "missing_evidence" else "updated" if ok else "failed"
    review_payload = payload.get("review") if isinstance(payload.get("review"), dict) else {}
    match_id = str(settlement.get("match_id") or "").strip()
    title = (
        f"{settlement.get('match_date') or settlement.get('date') or '-'} | "
        f"{settlement.get('league') or '-'} | "
        f"{settlement.get('home_team') or '-'} vs {settlement.get('away_team') or '-'}"
    )
    return {
        "action_key": "bind_external_reference",
        "occurred_at": (occurred_at or datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
        "match_id": match_id,
        "title": title,
        "before_kind": before_kind,
        "after_kind": after_kind,
        "outcome": outcome,
        "tone": "good" if outcome == "resolved" else "neutral" if outcome == "updated" else "bad",
        "ok": ok,
        "source_name": source_name or str(review_payload.get("source_name") or "-"),
        "review_id": str(review_payload.get("review_id") or "-"),
        "message": str(payload.get("message") or payload.get("reason") or ""),
        "summary_text": f"{title}: {before_kind}->{after_kind} | {outcome}",
        "next_recommendation": (
            "后续可按时间点补充视频事件标注，或导出视频复盘样本。"
            if ok
            else "检查外部回放链接或重新绑定合法视频来源。"
        ),
    }


def build_video_review_evidence_gap_feedback_rows(records: list[dict] | object, limit: int = 5) -> list[dict[str, object]]:
    if not isinstance(records, list):
        return []
    rows: list[dict[str, object]] = []
    for record in records[: max(0, int(limit))]:
        if not isinstance(record, dict):
            continue
        rows.append(
            {
                "title": f"{record.get('occurred_at', '-')} | {record.get('outcome', '-')} | {record.get('title', '-')}",
                "body": (
                    f"{record.get('summary_text', '-')}\n"
                    f"来源: {record.get('source_name', '-')} | review_id: {record.get('review_id', '-')}\n"
                    f"下一步: {record.get('next_recommendation', '-')}"
                ),
                "tone": str(record.get("tone") or "neutral"),
            }
        )
    return rows


def _load_video_review_evidence_gap_feedback_log(
    path: Path = VIDEO_REVIEW_EVIDENCE_GAP_ACTION_LOG,
) -> list[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(payload, dict):
        payload = payload.get("records")
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _append_video_review_evidence_gap_feedback_log(
    record: dict,
    path: Path = VIDEO_REVIEW_EVIDENCE_GAP_ACTION_LOG,
    *,
    limit: int = 50,
) -> None:
    records = [dict(record), *_load_video_review_evidence_gap_feedback_log(path)]
    records = records[: max(1, int(limit))]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps({"records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _load_video_review_evidence_gap_batch_state(
    path: Path = VIDEO_REVIEW_EVIDENCE_GAP_BATCH_STATE,
) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version": 1, "batches": []}
    if not isinstance(payload, dict):
        return {"schema_version": 1, "batches": []}
    batches = payload.get("batches")
    if not isinstance(batches, list):
        payload["batches"] = []
    return payload


def _save_video_review_evidence_gap_batch_state(
    state: dict,
    path: Path = VIDEO_REVIEW_EVIDENCE_GAP_BATCH_STATE,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _record_video_review_evidence_gap_batch_resolution(
    match_ids: set[str] | list[str] | tuple[str, ...] | str | object,
    *,
    evidence_kind: str,
    source_name: str = "",
    review_id: str = "",
    handled_by: str = "app_operator",
) -> dict[str, object]:
    state = _load_video_review_evidence_gap_batch_state()
    updated_state, update = build_video_review_evidence_gap_batch_state_with_resolution(
        state,
        match_ids,
        evidence_kind=evidence_kind,
        source_name=source_name,
        review_id=review_id,
        handled_by=handled_by,
    )
    if int(update.get("updated_count", 0) or 0) > 0:
        _save_video_review_evidence_gap_batch_state(updated_state)
    return update


def _load_statsbomb_review_training_action_feedback_log(
    path: Path = STATSBOMB_REVIEW_REPAIR_ACTION_LOG,
) -> list[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(payload, dict):
        payload = payload.get("records")
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _append_statsbomb_review_training_action_feedback_log(
    record: dict,
    path: Path = STATSBOMB_REVIEW_REPAIR_ACTION_LOG,
    *,
    limit: int = 50,
) -> None:
    records = [dict(record), *_load_statsbomb_review_training_action_feedback_log(path)]
    records = records[: max(1, int(limit))]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps({"records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


class SmartMatchDashboard:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("智能赛事分析系统")
        self.root.geometry("1120x820")
        self.root.minsize(980, 720)
        self.root.configure(bg=BG)

        self.rows: list[DashboardRow] = []
        self.data_source = "-"
        self.last_loaded_at = "-"
        self.last_refresh_seconds: float | None = None
        self.last_load_diagnostics: dict[str, object] = {}
        self.load_failures: list[dict[str, str]] = []
        self.c1_comparison_marks: dict[str, dict] = {}
        self.c1_release_rows: list[dict] = []
        self.play_model_policy_cache: dict[str, object] = {}
        self.strategy_release_recovery_cache: dict[str, object] = {}
        self.governance_filter = "all"
        self.governance_filter_buttons: dict[str, tk.Button] = {}
        self.main_flow_governance_counts: dict[str, int] = {}
        self.main_flow_governance_status_by_match_id: dict[str, dict] = {}
        self.event_log: list[tuple[str, str, str]] = []
        self.current_nav_index = 0
        self.current_view = "home"
        self.result_recovery_running = False
        self.model_warmup_running = False
        self.model_warmup_report: dict[str, object] = {}
        self.pending_statsbomb_review_repair_before_quality: dict[str, object] | None = None
        self.background_tasks = BackgroundTaskCenter(
            max_thread_workers=4,
            max_process_workers=2,
            dispatcher=lambda callback: self.root.after(0, callback),
            history_path=PROJECT_ROOT / "data" / "state" / "background_tasks.json",
            group_limits={"recovery": 1, "backtest": 1, "model": 1, "video": 1},
        )
        self.result_recovery_buttons: list[tk.Button] = []
        self.result_recovery_run_record: dict[str, object] | None = None
        self.show_all_matches = False
        self.admission_filter = "all"
        self.admission_filter_buttons: dict[str, tk.Button] = {}
        self.nav_items: list[tuple[tk.Frame, list[tk.Label]]] = []
        settings = _load_dashboard_settings()
        self.auto_refresh_enabled = tk.BooleanVar(value=bool(settings.get("auto_refresh_enabled", False)))
        self.auto_refresh_interval_min = tk.IntVar(value=max(3, min(int(settings.get("auto_refresh_interval_min", 10) or 10), 120)))
        self.auto_result_recovery_enabled = tk.BooleanVar(value=bool(settings.get("auto_result_recovery_enabled", False)))
        self.auto_result_recovery_interval_min = tk.IntVar(value=max(5, min(int(settings.get("auto_result_recovery_interval_min", 15) or 15), 120)))
        self.result_recovery_lookback_days = max(2, min(int(settings.get("result_recovery_lookback_days", 2) or 2), 14))
        self._auto_refresh_after_id: str | None = None
        self._auto_result_recovery_after_id: str | None = None
        self.status_var = tk.StringVar(value="正在加载赛事数据...")
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.summary_vars = {
            "matches": tk.StringVar(value="0"),
            "reports": tk.StringVar(value="0"),
            "alerts": tk.StringVar(value="0"),
            "hit_rate": tk.StringVar(value="-"),
            "settlements": tk.StringVar(value="0"),
        }

        self._mark_stale_result_recovery_runs()
        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._start_model_warmup()
        self.refresh()
        self._schedule_auto_refresh()
        self._schedule_auto_result_recovery()

    def _on_close(self) -> None:
        try:
            self.background_tasks.shutdown()
        except Exception:
            pass
        self.root.destroy()

    def _build_layout(self) -> None:
        self.shell = tk.Frame(self.root, bg=BG)
        self.shell.pack(fill=tk.BOTH, expand=True)

        self.sidebar = tk.Frame(self.shell, bg=SIDEBAR, width=235)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        self.main = tk.Frame(self.shell, bg=BG)
        self.main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_sidebar()
        self.show_home_overview()

    def _clear_main(self) -> None:
        for child in self.main.winfo_children():
            child.destroy()

    def _page_shell(self, title: str, subtitle: str = "") -> tk.Frame:
        self._clear_main()
        shell = tk.Frame(self.main, bg=BG)
        shell.pack(fill=tk.BOTH, expand=True, padx=22, pady=20)
        tk.Label(shell, text=title, bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 18, "bold")).pack(anchor=tk.W)
        if subtitle:
            tk.Label(shell, text=subtitle, bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 10)).pack(anchor=tk.W, pady=(6, 16))
        return shell

    def _widget_alive(self, name: str) -> bool:
        widget = getattr(self, name, None)
        try:
            return bool(widget is not None and widget.winfo_exists())
        except tk.TclError:
            return False

    def _build_sidebar(self) -> None:
        header = tk.Frame(self.sidebar, bg=SIDEBAR)
        header.pack(fill=tk.X, padx=24, pady=(22, 28))
        tk.Label(header, text="▰", bg=SIDEBAR, fg=TEXT, font=("Microsoft YaHei UI", 18, "bold")).pack(side=tk.LEFT)
        tk.Label(
            header,
            text="智能赛事分析系统",
            bg=SIDEBAR,
            fg=TEXT,
            font=("Microsoft YaHei UI", 13, "bold"),
        ).pack(side=tk.LEFT, padx=(10, 0))

        nav = [
            ("⌂", "首页概览", False),
            ("◇", "赛事分析", True),
            ("◎", "监控中心", False),
            ("▣", "历史报告", False),
            ("♧", "策略库", False),
            ("▤", "数据中心", False),
            ("⚙", "系统设置", False),
        ]
        for index, (icon, text, active) in enumerate(nav):
            command = None
            if index == 0:
                command = self.show_home_overview
            elif index == 1:
                command = self._build_main
            elif index == 2:
                command = self.open_monitor_center
            elif index == 3:
                command = self.open_history_reports
            elif index == 4:
                command = self.open_strategy_library
            elif index == 5:
                command = self.open_data_center
            elif index == 6:
                command = self.open_system_settings
            self._nav_item(index, icon, text, active, command=command)

    def _nav_item(self, index: int, icon: str, text: str, active: bool, command=None) -> None:
        bg = "#4051c8" if active else SIDEBAR
        item = tk.Frame(self.sidebar, bg=bg, height=48)
        item.pack(fill=tk.X, padx=16, pady=4)
        item.pack_propagate(False)
        icon_label = tk.Label(item, text=icon, bg=bg, fg=TEXT, font=("Microsoft YaHei UI", 13))
        icon_label.pack(side=tk.LEFT, padx=(16, 12))
        text_label = tk.Label(item, text=text, bg=bg, fg=TEXT, font=("Microsoft YaHei UI", 11, "bold" if active else "normal"))
        text_label.pack(side=tk.LEFT)
        self.nav_items.append((item, [icon_label, text_label]))
        if command is not None:
            wrapped = lambda: self._select_nav(index, command)
            item.configure(cursor="hand2")
            item.bind("<Button-1>", lambda _event: wrapped())
            for child in item.winfo_children():
                child.configure(cursor="hand2")
                child.bind("<Button-1>", lambda _event: wrapped())

    def _select_nav(self, index: int, command) -> None:
        self.current_nav_index = index
        self._refresh_nav_highlight()
        command()

    def _refresh_nav_highlight(self) -> None:
        for index, (item, labels) in enumerate(self.nav_items):
            active = index == self.current_nav_index
            bg = "#4051c8" if active else SIDEBAR
            item.configure(bg=bg)
            for label in labels:
                label.configure(bg=bg, font=("Microsoft YaHei UI", 11 if label is labels[1] else 13, "bold" if active and label is labels[1] else "normal"))

    def show_home_overview(self) -> None:
        self.current_nav_index = 0
        self.current_view = "home"
        self._refresh_nav_highlight()
        release_alerts = self._release_recovery_alerts()
        content = self._page_shell(
            "\u9996\u9875\u6982\u89c8",
            "\u8d5b\u4e8b\u5206\u6790\u603b\u89c8\u3001\u98ce\u9669\u6458\u8981\u548c\u7cfb\u7edf\u72b6\u6001",
        )

        actions = tk.Frame(content, bg=BG)
        actions.pack(fill=tk.X, pady=(0, 18))
        tk.Button(
            actions,
            text="\u8fdb\u5165\u8d5b\u4e8b\u5206\u6790",
            command=lambda: self._select_nav(1, self._build_main),
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.LEFT)
        tk.Button(
            actions,
            text="\u5237\u65b0\u6570\u636e",
            command=self.refresh,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground=TEXT,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.LEFT, padx=(10, 0))

        cards = tk.Frame(content, bg=BG)
        cards.pack(fill=tk.X, pady=(0, 18))
        self._metric_card(cards, "\u4eca\u65e5\u8d5b\u4e8b", self.summary_vars["matches"], "\u573a", TEXT)
        self._metric_card(cards, "\u98ce\u9669\u9884\u8b66", self.summary_vars["alerts"], "\u6b21", RED)
        self._metric_card(cards, "\u5386\u53f2\u80dc\u7387", self.summary_vars["hit_rate"], "", "#7aa2ff")
        self._metric_card(cards, "\u5386\u53f2\u6837\u672c", self.summary_vars["settlements"], "\u573a", TEXT)

        body = tk.Frame(content, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u7cfb\u7edf\u72b6\u6001", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        for label, value in [
            ("\u6570\u636e\u6e90", self.data_source),
            ("\u6700\u8fd1\u52a0\u8f7d", self.last_loaded_at),
            ("\u6700\u8fd1\u8017\u65f6", f"{self.last_refresh_seconds:.2f}s" if self.last_refresh_seconds is not None else "-"),
            ("\u5e73\u5747\u7f6e\u4fe1\u5ea6", self._average_confidence()),
            ("\u81ea\u52a8\u5237\u65b0", "\u5df2\u5f00\u542f" if self.auto_refresh_enabled.get() else "\u5df2\u5173\u95ed"),
        ]:
            self._kv_row(left, label, value)

        governance_counts = self.main_flow_governance_counts if isinstance(self.main_flow_governance_counts, dict) else {}
        tk.Label(left, text="\u4e3b\u6d41\u7a0b\u6cbb\u7406", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
        for label, value in [
            ("\u6b63\u5f0f\u5efa\u8bae", str(governance_counts.get("formal_ready", 0))),
            ("C1 \u5f85\u5ba1", str(governance_counts.get("needs_c1_review", 0))),
            ("\u963b\u65ad", str(governance_counts.get("blocked", 0))),
            ("\u5f85\u56de\u6536", str(governance_counts.get("needs_recovery", 0))),
        ]:
            self._kv_row(left, label, value)
        self._strategy_row(
            left,
            "\u67e5\u770b\u6b63\u5f0f\u5efa\u8bae",
            "\u76f4\u63a5\u6253\u5f00\u4e3b\u6d41\u7a0b\u6cbb\u7406\u7b5b\u9009\uff0c\u5148\u770b\u53ef\u4ee5\u8fdb\u5165\u6b63\u5f0f\u5efa\u8bae\u7684\u573a\u6b21\u3002",
            command=lambda: self.open_governance_filtered_matches("formal_ready"),
        )

        alert_count = int(release_alerts.get("count", 0) or 0)
        if alert_count:
            tk.Label(left, text="\u653e\u884c\u56de\u6536\u63d0\u9192", bg=PANEL, fg=RED, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
            first_alert = release_alerts.get("rows", [])[0] if isinstance(release_alerts.get("rows"), list) and release_alerts.get("rows") else {}
            body_text = str(first_alert.get("body") or release_alerts.get("summary") or "-") if isinstance(first_alert, dict) else str(release_alerts.get("summary") or "-")
            self._release_recovery_action_card(left, f"\u5f85\u56de\u6536 {alert_count} \u573a\u6b63\u5f0f\u653e\u884c", body_text)

        tk.Label(right, text="\u5feb\u6377\u5165\u53e3", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        shortcuts = [
            ("\u8d5b\u4e8b\u5206\u6790", "\u67e5\u770b\u91cd\u70b9\u8d5b\u4e8b\u3001\u98ce\u9669\u548c\u7f6e\u4fe1\u5ea6\u5206\u5e03", lambda: self._select_nav(1, self._build_main)),
            ("\u4e3b\u6d41\u7a0b\u6cbb\u7406", "\u5148\u770b\u6b63\u5f0f\u5efa\u8bae\uff0c\u518d\u67e5 C1 \u5f85\u5ba1\u548c\u963b\u65ad", lambda: self.open_governance_filtered_matches("formal_ready")),
            ("\u6cbb\u7406\u8be6\u60c5", "\u6e05\u7406 C1 \u5f85\u5ba1\u4e0e\u963b\u65ad\u573a\u6b21\uff0c\u67e5\u770b\u51b3\u7b56\u94fe", self.open_governance_issue_center),
            ("\u590d\u76d8\u4e2d\u5fc3", "\u56de\u6536\u8d5b\u679c\u5e76\u67e5\u770b\u547d\u4e2d\u7387\u4e0e\u9ad8\u7f6e\u4fe1\u5931\u8bef", self.open_review_center),
            ("\u8d5b\u524d\u5feb\u7167", "\u67e5\u770b\u5df2\u4fdd\u5b58\u7684\u8d5b\u524d\u9884\u6d4b\uff0c\u7b49\u5b8c\u573a\u540e\u8fdb\u884c\u590d\u76d8", self.open_snapshot_center),
            ("\u76d1\u63a7\u4e2d\u5fc3", "\u67e5\u770b Agent \u72b6\u6001\u3001\u8fd0\u884c\u65e5\u5fd7\u548c\u8017\u65f6", self.open_monitor_center),
            ("\u6570\u636e\u4e2d\u5fc3", "\u67e5\u770b\u6570\u636e\u6587\u4ef6\u3001\u6a21\u578b\u548c\u7f13\u5b58\u72b6\u6001", self.open_data_center),
        ]
        for title, body_text, command in shortcuts:
            self._shortcut_row(right, title, body_text, command)

    def _build_main(self) -> None:
        self.current_nav_index = 1
        self.current_view = "match_analysis"
        self._refresh_nav_highlight()
        self._clear_main()
        content = tk.Frame(self.main, bg=BG)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=24)

        title = tk.Frame(content, bg=BG)
        title.pack(fill=tk.X)
        tk.Label(title, text="今日概览", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 17, "bold")).pack(side=tk.LEFT)
        tk.Label(title, textvariable=self.date_var, bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 11)).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(
            title,
            text="\u590d\u76d8\u4e2d\u5fc3",
            command=self.open_review_center,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground=TEXT,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=6,
        ).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(
            title,
            text="刷新",
            command=self.refresh,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=6,
        ).pack(side=tk.RIGHT)

        cards = tk.Frame(content, bg=BG)
        cards.pack(fill=tk.X, pady=(22, 18))
        self._metric_card(cards, "分析赛事", self.summary_vars["matches"], "场", TEXT)
        self._metric_card(cards, "生成报告", self.summary_vars["reports"], "份", TEXT)
        self._metric_card(cards, "异常预警", self.summary_vars["alerts"], "次", RED)
        self._metric_card(cards, "胜率（历史）", self.summary_vars["hit_rate"], "", "#7aa2ff")

        workspace = tk.Frame(content, bg=BG)
        workspace.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        matches_card = self._card(workspace)
        matches_card.pack(fill=tk.BOTH, expand=True)
        header = tk.Frame(matches_card, bg=PANEL)
        header.pack(fill=tk.X, padx=18, pady=(16, 8))
        tk.Label(header, text="\u91cd\u70b9\u8d5b\u4e8b", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 14, "bold")).pack(side=tk.LEFT)
        self.match_toggle_var = tk.StringVar(value="\u67e5\u770b\u5168\u90e8 \u203a")
        toggle = tk.Label(header, textvariable=self.match_toggle_var, bg=PANEL, fg="#7692ff", font=("Microsoft YaHei UI", 10, "bold"), cursor="hand2")
        toggle.pack(side=tk.RIGHT)
        toggle.bind("<Button-1>", lambda _event: self._toggle_match_list())

        filter_bar = tk.Frame(matches_card, bg=PANEL)
        filter_bar.pack(fill=tk.X, padx=18, pady=(0, 10))
        tk.Label(filter_bar, text="\u51c6\u5165\u7b5b\u9009", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self.admission_filter_buttons = {}
        for key, label in [
            ("all", "\u5168\u90e8"),
            ("allow", "\u6b63\u5f0f\u653e\u884c"),
            ("observe", "\u89c2\u5bdf"),
            ("block", "\u963b\u65ad"),
        ]:
            button = tk.Button(
                filter_bar,
                text=label,
                command=lambda key=key: self._set_admission_filter(key),
                bg=PANEL_2,
                fg=TEXT,
                activebackground="#172638",
                activeforeground="white",
                relief=tk.FLAT,
                font=("Microsoft YaHei UI", 9, "bold"),
                padx=12,
                pady=5,
            )
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.admission_filter_buttons[key] = button

        governance_filter_bar = tk.Frame(matches_card, bg=PANEL)
        governance_filter_bar.pack(fill=tk.X, padx=18, pady=(0, 10))
        tk.Label(governance_filter_bar, text="\u4e3b\u6d41\u7a0b\u6cbb\u7406", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self.governance_filter_buttons = {}
        for key, label in [
            ("all", "\u5168\u90e8"),
            ("formal_ready", "\u6b63\u5f0f\u5efa\u8bae"),
            ("needs_c1_review", "C1 \u5f85\u5ba1"),
            ("blocked", "\u963b\u65ad"),
            ("needs_recovery", "\u5f85\u56de\u6536"),
            ("observe", "\u89c2\u5bdf"),
        ]:
            button = tk.Button(
                governance_filter_bar,
                text=label,
                command=lambda key=key: self._set_governance_filter(key),
                bg=PANEL_2,
                fg=TEXT,
                activebackground="#172638",
                activeforeground="white",
                relief=tk.FLAT,
                font=("Microsoft YaHei UI", 9, "bold"),
                padx=12,
                pady=5,
            )
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.governance_filter_buttons[key] = button
        self._refresh_governance_filter_buttons(self.main_flow_governance_counts)

        self.match_list_wrap = tk.Frame(matches_card, bg=PANEL, height=510)
        self.match_list_wrap.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 14))
        self.match_list_wrap.pack_propagate(False)
        self.match_canvas = tk.Canvas(self.match_list_wrap, bg=PANEL, bd=0, highlightthickness=0)
        self.match_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.match_scrollbar = tk.Scrollbar(self.match_list_wrap, orient=tk.VERTICAL, command=self.match_canvas.yview)
        self.match_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.match_canvas.configure(yscrollcommand=self.match_scrollbar.set)
        self.match_list = tk.Frame(self.match_canvas, bg=PANEL)
        self.match_canvas_window = self.match_canvas.create_window((0, 0), window=self.match_list, anchor=tk.NW)
        self.match_list.bind("<Configure>", lambda _event: self.match_canvas.configure(scrollregion=self.match_canvas.bbox("all")))
        self.match_canvas.bind("<Configure>", lambda event: self.match_canvas.itemconfigure(self.match_canvas_window, width=event.width))
        self._bind_match_scroll(self.match_canvas)

        charts = tk.Frame(workspace, bg=BG)
        self.risk_chart = self._chart_card(charts, "风险分布")
        self.conf_chart = self._chart_card(charts, "置信度分布")

        self._refresh_matches()
        self._draw_risk_chart()
        self._draw_confidence_chart()

        footer = tk.Label(content, textvariable=self.status_var, bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 9))
        footer.pack(anchor=tk.W, pady=(10, 0))

    def _card(self, parent: tk.Widget, bg: str = PANEL) -> tk.Frame:
        frame = tk.Frame(parent, bg=bg, highlightbackground="#101d2c", highlightthickness=1)
        return frame

    def _metric_card(self, parent: tk.Widget, label: str, value: tk.StringVar, suffix: str, color: str) -> None:
        frame = self._card(parent, PANEL)
        frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 14))
        tk.Label(frame, text=label, bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 11, "bold")).pack(pady=(18, 6))
        line = tk.Frame(frame, bg=PANEL)
        line.pack(pady=(0, 18))
        tk.Label(line, textvariable=value, bg=PANEL, fg=color, font=("Microsoft YaHei UI", 24, "bold")).pack(side=tk.LEFT)
        tk.Label(line, text=suffix, bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 11, "bold")).pack(side=tk.LEFT, padx=(5, 0), pady=(8, 0))

    def _shortcut_row(self, parent: tk.Widget, title: str, body: str, command) -> None:
        frame = tk.Frame(parent, bg=PANEL_2, highlightbackground="#172638", highlightthickness=1)
        frame.pack(fill=tk.X, padx=18, pady=7)
        frame.configure(cursor="hand2")
        tk.Label(frame, text=title, bg=PANEL_2, fg=TEXT, font=("Microsoft YaHei UI", 11, "bold")).pack(anchor=tk.W, padx=14, pady=(10, 3))
        tk.Label(
            frame,
            text=body,
            bg=PANEL_2,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            justify=tk.LEFT,
            wraplength=360,
        ).pack(anchor=tk.W, padx=14, pady=(0, 10))
        frame.bind("<Button-1>", lambda _event: command())
        for child in frame.winfo_children():
            child.configure(cursor="hand2")
            child.bind("<Button-1>", lambda _event: command())

    def _release_recovery_action_card(self, parent: tk.Widget, title: str, body: str) -> None:
        frame = tk.Frame(parent, bg=PANEL_2, highlightbackground="#5f2b2b", highlightthickness=1)
        frame.pack(fill=tk.X, padx=18, pady=7)
        tk.Label(frame, text=title, bg=PANEL_2, fg=RED, font=("Microsoft YaHei UI", 11, "bold")).pack(anchor=tk.W, padx=14, pady=(10, 3))
        tk.Label(
            frame,
            text=body,
            bg=PANEL_2,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            justify=tk.LEFT,
            wraplength=360,
        ).pack(anchor=tk.W, padx=14, pady=(0, 10))
        actions = tk.Frame(frame, bg=PANEL_2)
        actions.pack(fill=tk.X, padx=14, pady=(0, 12))
        recover_button = tk.Button(
            actions,
            text="\u7acb\u5373\u56de\u6536\u8d5b\u679c",
            command=self.run_result_recovery,
            bg=RED,
            fg="white",
            activebackground="#d94a46",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 9, "bold"),
            padx=12,
            pady=5,
        )
        self._register_result_recovery_button(recover_button)
        recover_button.pack(side=tk.LEFT)
        tk.Button(
            actions,
            text="\u67e5\u770b\u5feb\u7167",
            command=self.open_snapshot_center,
            bg=PANEL,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 9, "bold"),
            padx=12,
            pady=5,
        ).pack(side=tk.LEFT, padx=(8, 0))

    def _alert_card(self, parent: tk.Widget, title: str, body: str, *, tone: str = "warning") -> None:
        color = self._tone_color(tone)
        frame = tk.Frame(parent, bg=PANEL_2, highlightbackground=color, highlightthickness=1)
        frame.pack(fill=tk.X, padx=18, pady=7)
        tk.Label(frame, text=title, bg=PANEL_2, fg=color, font=("Microsoft YaHei UI", 11, "bold")).pack(anchor=tk.W, padx=14, pady=(10, 3))
        tk.Label(
            frame,
            text=body,
            bg=PANEL_2,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            justify=tk.LEFT,
            wraplength=360,
        ).pack(anchor=tk.W, padx=14, pady=(0, 10))

    def _register_result_recovery_button(self, button: tk.Button) -> None:
        self.result_recovery_buttons = [
            item for item in self.result_recovery_buttons if self._widget_alive_for(item)
        ]
        self.result_recovery_buttons.append(button)
        button.configure(state=tk.DISABLED if self.result_recovery_running else tk.NORMAL)

    def _set_result_recovery_controls_state(self) -> None:
        state = tk.DISABLED if self.result_recovery_running else tk.NORMAL
        live_buttons: list[tk.Button] = []
        for button in self.result_recovery_buttons:
            if not self._widget_alive_for(button):
                continue
            try:
                button.configure(state=state)
            except tk.TclError:
                continue
            live_buttons.append(button)
        self.result_recovery_buttons = live_buttons

    def _recovery_run_records(self, limit: int = 80) -> list[dict]:
        try:
            return get_result_recovery_runs(limit=limit)
        except Exception:
            return []

    def _recovery_run_summary(self) -> dict[str, object]:
        return build_result_recovery_run_summary(self._recovery_run_records(limit=80))

    def _recovery_quality_alerts(self, limit: int = 80) -> list[dict[str, str]]:
        return build_result_recovery_quality_alerts(self._recovery_run_records(limit=limit))

    def _result_recovery_snapshot_audit(self, lookback_days: int = 2) -> dict[str, object]:
        try:
            return build_result_recovery_snapshot_audit(
                _load_prediction_snapshot_records(),
                get_recent_settlements(limit=0),
                lookback_days=lookback_days,
            )
        except Exception as exc:
            self._log_event("ERROR", f"\u5feb\u7167\u53ef\u56de\u6536\u6027\u5ba1\u8ba1\u5931\u8d25: {exc}")
            return {}

    def _snapshot_audit_metrics(self, audit: dict[str, object]) -> list[tuple[str, str, str]]:
        pending = int(audit.get("pending", 0) or 0)
        recoverable = int(audit.get("recoverable_schedule_id", audit.get("recoverable_titan", 0)) or 0)
        missing_source = int(audit.get("missing_source_id", 0) or 0)
        non_titan = int(audit.get("non_titan_source", 0) or 0)
        out_window = int(audit.get("out_of_window", 0) or 0)
        total = int(audit.get("total_snapshots", 0) or 0)
        return [
            ("\u5f85\u56de\u6536\u5feb\u7167", str(pending), TEXT),
            ("\u53ef\u81ea\u52a8\u56de\u67e5", str(recoverable), GREEN if recoverable else YELLOW),
            ("\u7f3a source_id", str(missing_source), RED if missing_source else GREEN),
            ("\u4e0d\u53ef\u56de\u67e5\u6765\u6e90", str(non_titan), YELLOW if non_titan else GREEN),
            ("\u8d85\u51fa\u56de\u770b", str(out_window), YELLOW if out_window else TEXT),
            ("\u5feb\u7167\u603b\u6570", str(total), "#7aa2ff"),
        ]

    def _recovery_lookback_days(self) -> int:
        return max(2, min(int(getattr(self, "result_recovery_lookback_days", 2) or 2), 14))

    def _set_recovery_lookback_days(self, days: int) -> None:
        allowed = [2, 7, 14]
        value = int(days) if int(days) in allowed else 2
        self.result_recovery_lookback_days = value
        settings = _load_dashboard_settings()
        settings.update(
            {
                "auto_refresh_enabled": bool(self.auto_refresh_enabled.get()),
                "auto_refresh_interval_min": max(3, min(int(self.auto_refresh_interval_min.get()), 120)),
                "auto_result_recovery_enabled": bool(self.auto_result_recovery_enabled.get()),
                "auto_result_recovery_interval_min": max(5, min(int(self.auto_result_recovery_interval_min.get()), 120)),
                "result_recovery_lookback_days": value,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        _save_dashboard_settings(settings)
        self._log_event("INFO", f"\u56de\u6536\u56de\u770b\u7a97\u53e3\u5207\u6362\u4e3a {value} \u5929")
        if getattr(self, "current_view", "") == "recovery_runs":
            self.open_recovery_run_center()
        else:
            self.open_review_center()

    def _lookback_selector(self, parent: tk.Widget) -> None:
        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill=tk.X, pady=(0, 12))
        tk.Label(frame, text="\u56de\u6536\u56de\u770b", bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 10, "bold")).pack(side=tk.LEFT)
        current = self._recovery_lookback_days()
        for days in [2, 7, 14]:
            active = days == current
            tk.Button(
                frame,
                text=f"{days}\u5929",
                command=lambda value=days: self._set_recovery_lookback_days(value),
                bg=BLUE if active else PANEL_2,
                fg="white" if active else TEXT,
                activebackground="#3d5ee7",
                activeforeground="white",
                relief=tk.FLAT,
                font=("Microsoft YaHei UI", 9, "bold"),
                padx=12,
                pady=5,
            ).pack(side=tk.LEFT, padx=(8, 0))

    def _mark_stale_result_recovery_runs(self) -> None:
        try:
            records = get_result_recovery_runs(limit=0)
            result = mark_stale_result_recovery_runs(records, stale_after_minutes=60)
        except Exception as exc:
            self._log_event("ERROR", f"\u56de\u6536\u8fd0\u884c\u8bb0\u5f55\u6821\u9a8c\u5931\u8d25: {exc}")
            return
        updated = result.get("updated", []) if isinstance(result, dict) else []
        if not isinstance(updated, list):
            return
        for item in updated:
            if isinstance(item, dict):
                self._record_result_recovery_run(item)
        if updated:
            self._log_event("WARN", f"\u5df2\u5c06 {len(updated)} \u6761\u8fc7\u671f\u56de\u6536\u8bb0\u5f55\u6807\u8bb0\u4e3a\u4e2d\u65ad")

    def _record_result_recovery_run(self, record: dict[str, object]) -> None:
        try:
            record_result_recovery_run(record)
        except Exception as exc:
            self._log_event("ERROR", f"\u56de\u6536\u8fd0\u884c\u8bb0\u5f55\u5199\u5165\u5931\u8d25: {exc}")

    def _live_feedback_recovery_checkpoint(self) -> dict[str, object]:
        try:
            summary = build_high_accuracy_live_feedback_summary(get_high_accuracy_strategy_status())
        except Exception as exc:
            return {"status": "unavailable", "summary_text": f"\u5b9e\u76d8\u53cd\u9988\u8bfb\u53d6\u5931\u8d25: {exc}"}
        keys = (
            "strategy_count",
            "runtime_active_count",
            "pending_count",
            "known_count",
            "feedback_strategy_count",
            "paused_count",
            "recovering_count",
            "recovered_count",
            "hit_count",
            "feedback_known_count",
            "hit_rate_text",
            "summary_text",
            "tone",
        )
        return {key: summary.get(key) for key in keys}

    def _begin_result_recovery_run_record(self, trigger: str = "manual_ui") -> dict[str, object]:
        now = datetime.now()
        record: dict[str, object] = {
            "run_id": now.strftime("%Y%m%d_%H%M%S_%f"),
            "status": "running",
            "trigger": trigger,
            "source_view": getattr(self, "current_view", "-"),
            "started_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "lookback_days": self._recovery_lookback_days(),
            "prediction_cache_count": len(self.rows),
            "live_feedback_before": self._live_feedback_recovery_checkpoint(),
        }
        if trigger == "statsbomb_review_repair" and isinstance(self.pending_statsbomb_review_repair_before_quality, dict):
            record["statsbomb_review_repair_before_quality"] = dict(self.pending_statsbomb_review_repair_before_quality)
        self.result_recovery_run_record = dict(record)
        self._record_result_recovery_run(record)
        return record

    def _finish_result_recovery_run_record(
        self,
        *,
        status: str,
        elapsed: float,
        result: dict | None = None,
        error: Exception | None = None,
    ) -> None:
        record = dict(self.result_recovery_run_record or {})
        if not record.get("run_id"):
            record = self._begin_result_recovery_run_record()
        result_payload = result if isinstance(result, dict) else {}
        messages = result_payload.get("messages", [])
        if not isinstance(messages, list):
            messages = []
        review_summary = result_payload.get("review_summary")
        if not isinstance(review_summary, dict):
            review_summary = build_result_recovery_review_summary(
                result_payload.get("items", []) if isinstance(result_payload.get("items"), list) else []
            )
        live_feedback_after = self._live_feedback_recovery_checkpoint()
        live_feedback_validation = build_high_accuracy_live_feedback_recovery_validation(
            record.get("live_feedback_before") if isinstance(record.get("live_feedback_before"), dict) else {},
            live_feedback_after,
            new_settled=int(result_payload.get("new_settled", 0) or 0),
        )
        record.update(
            {
                "status": status,
                "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "elapsed_seconds": round(float(elapsed), 4),
                "source": result_payload.get("source", "-"),
                "fetched_finished": int(result_payload.get("fetched_finished", 0) or 0),
                "restored_snapshots": int(result_payload.get("restored_snapshots", 0) or 0),
                "new_settled": int(result_payload.get("new_settled", 0) or 0),
                "new_parlay_settled": int(result_payload.get("new_parlay_settled", 0) or 0),
                "already_settled": int(result_payload.get("already_settled", 0) or 0),
                "skipped": int(result_payload.get("skipped", 0) or 0),
                "snapshot_checked": int(result_payload.get("snapshot_checked", 0) or 0),
                "snapshot_result_hits": int(result_payload.get("snapshot_result_hits", 0) or 0),
                "snapshot_result_misses": int(result_payload.get("snapshot_result_misses", 0) or 0),
                "snapshot_result_miss_reasons": result_payload.get("snapshot_result_miss_reasons", {})
                if isinstance(result_payload.get("snapshot_result_miss_reasons"), dict)
                else {},
                "snapshot_result_miss_items": result_payload.get("snapshot_result_miss_items", [])
                if isinstance(result_payload.get("snapshot_result_miss_items"), list)
                else [],
                "review_summary": review_summary,
                "snapshot_predictions": int(result_payload.get("snapshot_predictions", 0) or 0),
                "snapshot_recoverable": int(result_payload.get("snapshot_recoverable", 0) or 0),
                "snapshot_missing_source_id": int(result_payload.get("snapshot_missing_source_id", 0) or 0),
                "snapshot_out_of_window": int(result_payload.get("snapshot_out_of_window", 0) or 0),
                "snapshot_non_titan_source": int(result_payload.get("snapshot_non_titan_source", 0) or 0),
                "snapshot_audit": result_payload.get("snapshot_audit", {}) if isinstance(result_payload.get("snapshot_audit"), dict) else {},
                "lookback_days": int(result_payload.get("lookback_days", record.get("lookback_days", 2)) or 2),
                "messages": [str(item) for item in messages if item],
                "live_feedback_after": live_feedback_after,
                "live_feedback_validation": live_feedback_validation,
            }
        )
        if error is not None:
            record["error"] = str(error)
        elif status == "success":
            record["error"] = ""
        self.result_recovery_run_record = dict(record)
        self._record_result_recovery_run(record)

    def _chart_card(self, parent: tk.Widget, title: str) -> tk.Canvas:
        frame = self._card(parent, PANEL)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        tk.Label(frame, text=title, bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 14, "bold")).pack(anchor=tk.W, padx=20, pady=(16, 4))
        canvas = tk.Canvas(frame, bg=PANEL, bd=0, highlightthickness=0, height=190)
        canvas.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 14))
        return canvas

    def _start_model_warmup(self) -> None:
        if self.model_warmup_running:
            return
        if str(self.model_warmup_report.get("status") or "") == "ready":
            return
        self.model_warmup_running = True
        self._log_event("INFO", "启动预测模型后台预热")

        def runner() -> None:
            try:
                report = warmup_prediction_models()
            except Exception as exc:
                report = {
                    "status": "error",
                    "ready_count": 0,
                    "total_count": 0,
                    "items": [],
                    "elapsed_seconds": 0.0,
                    "error": str(exc),
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            try:
                self.root.after(0, lambda payload=report: self._finish_model_warmup(payload))
            except Exception:
                self.model_warmup_running = False
                self.model_warmup_report = dict(report)

        threading.Thread(target=runner, daemon=True).start()

    def _finish_model_warmup(self, report: dict[str, object]) -> None:
        self.model_warmup_running = False
        self.model_warmup_report = dict(report)
        ready_count = int(report.get("ready_count", 0) or 0)
        total_count = int(report.get("total_count", 0) or 0)
        elapsed = float(report.get("elapsed_seconds", 0.0) or 0.0)
        status = str(report.get("status") or "-")
        self._log_event("INFO", f"模型预热完成: {status} {ready_count}/{total_count} ({elapsed:.2f}s)")

    def refresh(self, force_live: bool = False, cache_only: bool = False) -> None:
        self._start_model_warmup()
        if cache_only:
            self._log_event("INFO", "\u624b\u52a8\u8bfb\u53d6\u56de\u9000\u7f13\u5b58")
            self.status_var.set("\u6b63\u5728\u8bfb\u53d6\u56de\u9000\u7f13\u5b58...")
        elif force_live:
            self._log_event("INFO", "\u624b\u52a8\u91cd\u8bd5\u5728\u7ebf\u6570\u636e\u6e90")
            self.status_var.set("\u6b63\u5728\u8df3\u8fc7\u7f13\u5b58\u5e76\u91cd\u8bd5\u5728\u7ebf\u6e90...")
        else:
            self._log_event("INFO", "\u5f00\u59cb\u5237\u65b0\u8d5b\u4e8b\u6570\u636e")
            self.status_var.set("正在聚合赛事数据并执行 AI 分析...")
        threading.Thread(target=self._load_worker, args=(force_live, cache_only), daemon=True).start()

    def _schedule_auto_refresh(self) -> None:
        if self._auto_refresh_after_id is not None:
            try:
                self.root.after_cancel(self._auto_refresh_after_id)
            except Exception:
                pass
            self._auto_refresh_after_id = None
        if not self.auto_refresh_enabled.get():
            return
        interval = max(3, min(int(self.auto_refresh_interval_min.get()), 120))
        self.auto_refresh_interval_min.set(interval)
        self._auto_refresh_after_id = self.root.after(interval * 60 * 1000, self._auto_refresh_tick)

    def _auto_refresh_tick(self) -> None:
        self._auto_refresh_after_id = None
        if not self.auto_refresh_enabled.get():
            return
        self._log_event("INFO", "\u81ea\u52a8\u5237\u65b0\u89e6\u53d1")
        self.refresh()
        self._schedule_auto_refresh()

    def _schedule_auto_result_recovery(self) -> None:
        if self._auto_result_recovery_after_id is not None:
            try:
                self.root.after_cancel(self._auto_result_recovery_after_id)
            except Exception:
                pass
            self._auto_result_recovery_after_id = None
        if not self.auto_result_recovery_enabled.get():
            return
        interval = max(5, min(int(self.auto_result_recovery_interval_min.get()), 120))
        self.auto_result_recovery_interval_min.set(interval)
        self._auto_result_recovery_after_id = self.root.after(interval * 60 * 1000, self._auto_result_recovery_tick)

    def _auto_result_recovery_tick(self) -> None:
        self._auto_result_recovery_after_id = None
        if not self.auto_result_recovery_enabled.get():
            return
        if self.result_recovery_running:
            self._schedule_auto_result_recovery()
            return
        self._log_event("INFO", "\u81ea\u52a8\u8d5b\u679c\u56de\u6536\u89e6\u53d1")
        self.run_result_recovery(trigger="auto_timer", show_popup=False)

    def _on_auto_refresh_changed(self) -> None:
        interval = max(3, min(int(self.auto_refresh_interval_min.get()), 120))
        self.auto_refresh_interval_min.set(interval)
        settings = _load_dashboard_settings()
        settings.update(
            {
                "auto_refresh_enabled": bool(self.auto_refresh_enabled.get()),
                "auto_refresh_interval_min": interval,
                "auto_result_recovery_enabled": bool(self.auto_result_recovery_enabled.get()),
                "auto_result_recovery_interval_min": max(5, min(int(self.auto_result_recovery_interval_min.get()), 120)),
                "result_recovery_lookback_days": self._recovery_lookback_days(),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        _save_dashboard_settings(settings)
        self._schedule_auto_refresh()
        if self.auto_refresh_enabled.get():
            self.status_var.set(f"\u81ea\u52a8\u5237\u65b0\u5df2\u5f00\u542f\uff0c\u95f4\u9694 {self.auto_refresh_interval_min.get()} \u5206\u949f")
            self._log_event("INFO", f"\u81ea\u52a8\u5237\u65b0\u5f00\u542f: {self.auto_refresh_interval_min.get()} min")
        else:
            self.status_var.set("\u81ea\u52a8\u5237\u65b0\u5df2\u5173\u95ed")
            self._log_event("INFO", "\u81ea\u52a8\u5237\u65b0\u5173\u95ed")

    def _on_auto_result_recovery_changed(self) -> None:
        interval = max(5, min(int(self.auto_result_recovery_interval_min.get()), 120))
        self.auto_result_recovery_interval_min.set(interval)
        settings = _load_dashboard_settings()
        settings.update(
            {
                "auto_refresh_enabled": bool(self.auto_refresh_enabled.get()),
                "auto_refresh_interval_min": max(3, min(int(self.auto_refresh_interval_min.get()), 120)),
                "auto_result_recovery_enabled": bool(self.auto_result_recovery_enabled.get()),
                "auto_result_recovery_interval_min": interval,
                "result_recovery_lookback_days": self._recovery_lookback_days(),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        _save_dashboard_settings(settings)
        self._schedule_auto_result_recovery()
        if self.auto_result_recovery_enabled.get():
            self.status_var.set(f"\u81ea\u52a8\u8d5b\u679c\u56de\u6536\u5df2\u5f00\u542f\uff0c\u95f4\u9694 {self.auto_result_recovery_interval_min.get()} \u5206\u949f")
            self._log_event("INFO", f"\u81ea\u52a8\u8d5b\u679c\u56de\u6536\u5f00\u542f: {self.auto_result_recovery_interval_min.get()} min")
        else:
            self.status_var.set("\u81ea\u52a8\u8d5b\u679c\u56de\u6536\u5df2\u5173\u95ed")
            self._log_event("INFO", "\u81ea\u52a8\u8d5b\u679c\u56de\u6536\u5173\u95ed")

    def _load_worker(self, force_live: bool = False, cache_only: bool = False) -> None:
        started = time.perf_counter()
        try:
            fetched = fetch_matches_v24(strict_today=True, force_live=force_live, cache_only=cache_only)
        except Exception as exc:
            elapsed = time.perf_counter() - started
            self.last_refresh_seconds = elapsed
            self.root.after(0, lambda exc=exc: self._show_error(exc))
            return

        rows, failures = _build_dashboard_rows(fetched.matches)
        elapsed = time.perf_counter() - started
        report = _build_match_load_report(
            fetched_count=len(fetched.matches),
            row_count=len(rows),
            failures=failures,
            source=fetched.diagnostics.source,
            elapsed=elapsed,
            source_messages=fetched.diagnostics.messages,
            source_reports=fetched.diagnostics.source_reports,
            cache_exists=fetched.diagnostics.cache_exists,
            cache_fresh=fetched.diagnostics.cache_fresh,
            cache_date=fetched.diagnostics.cache_date,
            cache_match_count=fetched.diagnostics.cache_match_count,
            cache_age_days=fetched.diagnostics.cache_age_days,
            force_live=force_live,
            cache_only=cache_only,
        )
        self.root.after(
            0,
            lambda rows=rows, source=fetched.diagnostics.source, elapsed=elapsed, report=report: self._apply_rows(
                rows,
                source,
                elapsed,
                report,
            ),
        )

    def _show_error(self, exc: Exception) -> None:
        self._log_event("ERROR", f"\u52a0\u8f7d\u5931\u8d25: {exc}")
        self.status_var.set(f"加载失败: {exc}")
        messagebox.showerror("加载失败", str(exc))

    def _refresh_governance_context(self) -> None:
        predictions = {row.match.match_id: row.prediction for row in self.rows}
        try:
            marks = load_c1_comparison_marks_cache()
            self.c1_comparison_marks = marks if isinstance(marks, dict) else {}
            self.c1_release_rows = build_c1_rows_from_marks(
                matches=[row.match for row in self.rows],
                marks=self.c1_comparison_marks,
                predictions=predictions,
                action_priority_fn=_c1_suggested_action_priority,
            )
        except Exception as exc:
            self.c1_comparison_marks = {}
            self.c1_release_rows = []
            self._log_event("WARN", f"C1 \u6cbb\u7406\u72b6\u6001\u8bfb\u53d6\u5931\u8d25: {exc}")
        self.play_model_policy_cache = self._play_model_policy_status()
        try:
            loop = self._strategy_release_recovery_loop()
            self.strategy_release_recovery_cache = loop if isinstance(loop, dict) else {}
        except Exception as exc:
            self.strategy_release_recovery_cache = {}
            self._log_event("WARN", f"\u653e\u884c\u56de\u6536\u95ed\u73af\u8bfb\u53d6\u5931\u8d25: {exc}")
        statuses: list[dict] = []
        self.main_flow_governance_status_by_match_id = {}
        for row in self.rows:
            status = self._main_flow_governance_status(row)
            statuses.append(status)
            self.main_flow_governance_status_by_match_id[row.match.match_id] = status
        self.main_flow_governance_counts = summarize_main_flow_governance_statuses(statuses)
        self._refresh_governance_filter_buttons(self.main_flow_governance_counts)

    def _current_release_row(self, match_id: str) -> dict:
        return find_release_row(self.c1_release_rows, match_id)

    def _main_flow_governance_status(self, row: DashboardRow) -> dict:
        cached = getattr(self, "main_flow_governance_status_by_match_id", {}).get(row.match.match_id)
        if isinstance(cached, dict):
            return cached
        return build_main_flow_governance_status(
            prediction=row.prediction,
            c1_release_row=self._current_release_row(row.match.match_id),
            play_policy_status=self.play_model_policy_cache,
            recovery_loop=self.strategy_release_recovery_cache,
            match_id=row.match.match_id,
        )

    def _apply_rows(
        self,
        rows: list[DashboardRow],
        source: str,
        elapsed: float | None = None,
        load_report: dict[str, object] | None = None,
    ) -> None:
        self.rows = rows
        self.data_source = source or "-"
        self.last_loaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_refresh_seconds = elapsed
        self.last_load_diagnostics = dict(load_report or {})
        failures = self.last_load_diagnostics.get("failures", [])
        self.load_failures = list(failures) if isinstance(failures, list) else []
        self.date_var.set(datetime.now().strftime("(%Y-%m-%d)"))
        self._refresh_governance_context()
        self._refresh_metrics()
        if self.current_view == "home":
            self.show_home_overview()
        if self._widget_alive("match_list"):
            self._refresh_matches()
        if self._widget_alive("risk_chart"):
            self._draw_risk_chart()
        if self._widget_alive("conf_chart"):
            self._draw_confidence_chart()
        fetched_count = int(self.last_load_diagnostics.get("fetched_count", len(rows)) or 0)
        failure_count = int(self.last_load_diagnostics.get("failure_count", 0) or 0)
        snapshot_failures = int(self.last_load_diagnostics.get("snapshot_failure_count", 0) or 0)
        log_level = "OK" if failure_count == 0 else "WARN" if rows else "ERROR"
        failure_text = f" | \u5931\u8d25 {failure_count} \u9879" if failure_count else ""
        if elapsed is not None:
            self._log_event(log_level, f"\u5206\u6790\u5b8c\u6210: {len(rows)}/{fetched_count} \u573a | \u6570\u636e\u6e90 {source or '-'} | \u8017\u65f6 {elapsed:.2f}s{failure_text}")
        else:
            self._log_event(log_level, f"\u5206\u6790\u5b8c\u6210: {len(rows)}/{fetched_count} \u573a | \u6570\u636e\u6e90 {source or '-'}{failure_text}")
        if failure_count:
            self.status_var.set(f"\u5df2\u5b8c\u6210 {len(rows)}/{fetched_count} \u573a\u8d5b\u4e8b\u5206\u6790 | \u5931\u8d25 {failure_count} \u9879 | \u5feb\u7167\u5931\u8d25 {snapshot_failures} \u9879")
        else:
            self.status_var.set(f"已完成 {len(rows)} 场赛事分析 | 数据源 {source or '-'}")

    def _refresh_metrics(self) -> None:
        total = len(self.rows)
        alerts = sum(1 for row in self.rows if _risk_key(row.prediction.get("risk_level")) == "high")
        self.summary_vars["matches"].set(str(total))
        report_count = len(list_dashboard_report_files(REPORT_DIR, limit=10000)) if REPORT_DIR.exists() else 0
        self.summary_vars["reports"].set(str(report_count))
        self.summary_vars["alerts"].set(str(alerts))
        self.summary_vars["hit_rate"].set(self._historical_hit_rate())
        self.summary_vars["settlements"].set(str(self._historical_settlement_count()))

    def _historical_hit_rate(self) -> str:
        try:
            settlements = get_recent_settlements(limit=200)
        except Exception:
            return "-"
        hits = 0
        total = 0
        for item in settlements:
            if not isinstance(item, dict):
                continue
            if "is_correct" in item:
                total += 1
                hits += 1 if item.get("is_correct") else 0
        if total == 0:
            return "-"
        return f"{hits / total:.1%}"

    def _historical_settlement_count(self) -> int:
        try:
            return len(get_recent_settlements(limit=0))
        except Exception:
            return 0

    def _toggle_match_list(self) -> None:
        self.show_all_matches = not self.show_all_matches
        self._refresh_matches()

    def _set_admission_filter(self, selected: str) -> None:
        self.admission_filter = selected if selected in {"all", "allow", "observe", "block"} else "all"
        self.show_all_matches = False
        self._refresh_matches()

    def _set_governance_filter(self, selected: str) -> None:
        self.governance_filter = selected if selected in {"all", "formal_ready", "observe", "blocked", "needs_c1_review", "needs_recovery"} else "all"
        self.show_all_matches = False
        self._refresh_matches()

    def open_governance_filtered_matches(self, selected: str = "formal_ready") -> None:
        self.governance_filter = selected if selected in {"all", "formal_ready", "observe", "blocked", "needs_c1_review", "needs_recovery"} else "all"
        self._select_nav(1, self._build_main)

    def _widget_alive_for(self, widget: tk.Widget) -> bool:
        try:
            return bool(widget is not None and widget.winfo_exists())
        except tk.TclError:
            return False

    def _refresh_admission_filter_buttons(self, counts: dict[str, int]) -> None:
        labels = {
            "all": "\u5168\u90e8",
            "allow": "\u6b63\u5f0f\u653e\u884c",
            "observe": "\u89c2\u5bdf",
            "block": "\u963b\u65ad",
        }
        colors = {"all": BLUE, "allow": GREEN, "observe": YELLOW, "block": RED}
        for key, button in getattr(self, "admission_filter_buttons", {}).items():
            if not self._widget_alive_for(button):
                continue
            active = key == self.admission_filter
            button.configure(
                text=f"{labels.get(key, key)} {int(counts.get(key, 0) or 0)}",
                bg=colors.get(key, BLUE) if active else PANEL_2,
                fg="white" if active else TEXT,
                activebackground=colors.get(key, BLUE) if active else "#172638",
            )

    def _refresh_governance_filter_buttons(self, counts: dict[str, int]) -> None:
        labels = {
            "all": "\u5168\u90e8",
            "formal_ready": "\u6b63\u5f0f\u5efa\u8bae",
            "observe": "\u89c2\u5bdf",
            "blocked": "\u963b\u65ad",
            "needs_c1_review": "C1 \u5f85\u5ba1",
            "needs_recovery": "\u5f85\u56de\u6536",
        }
        colors = {
            "all": BLUE,
            "formal_ready": GREEN,
            "observe": YELLOW,
            "blocked": RED,
            "needs_c1_review": YELLOW,
            "needs_recovery": "#7aa2ff",
        }
        for key, button in getattr(self, "governance_filter_buttons", {}).items():
            if not self._widget_alive_for(button):
                continue
            active = key == self.governance_filter
            button.configure(
                text=f"{labels.get(key, key)} {int(counts.get(key, 0) or 0)}",
                bg=colors.get(key, BLUE) if active else PANEL_2,
                fg="white" if active else TEXT,
                activebackground=colors.get(key, BLUE) if active else "#172638",
            )

    def _resize_match_list_area(self, row_count: int) -> None:
        if not self._widget_alive("match_list_wrap"):
            return
        if self.show_all_matches:
            height = 560
        else:
            height = 240 if row_count <= 1 else 360 if row_count == 2 else 510
        self.match_list_wrap.configure(height=height)

    def _bind_match_scroll(self, widget: tk.Widget) -> None:
        widget.bind("<MouseWheel>", self._on_match_mousewheel, add="+")
        for child in widget.winfo_children():
            self._bind_match_scroll(child)

    def _on_match_mousewheel(self, event) -> None:
        if self._widget_alive("match_canvas"):
            delta = int(-1 * (event.delta / 120)) if event.delta else 0
            if delta:
                self.match_canvas.yview_scroll(delta, "units")
            return "break"

    def _bind_canvas_mousewheel(self, widget: tk.Widget, canvas: tk.Canvas) -> None:
        widget.bind("<MouseWheel>", lambda event, target=canvas: self._on_bound_canvas_mousewheel(event, target), add="+")
        for child in widget.winfo_children():
            self._bind_canvas_mousewheel(child, canvas)

    def _on_bound_canvas_mousewheel(self, event, canvas: tk.Canvas) -> str:
        delta = int(-1 * (event.delta / 120)) if event.delta else 0
        if delta:
            canvas.yview_scroll(delta, "units")
        return "break"

    def _refresh_matches(self) -> None:
        for child in self.match_list.winfo_children():
            child.destroy()

        counts = compute_strategy_admission_counts(self.rows)
        self._refresh_admission_filter_buttons(counts)
        filtered_rows = filter_strategy_admission_rows(self.rows, self.admission_filter)
        filtered_rows = filter_main_flow_governance_rows(
            filtered_rows,
            self.governance_filter,
            status_fn=self._main_flow_governance_status,
        )
        ranked = sorted(
            filtered_rows,
            key=lambda row: (
                {"high": 0, "medium": 1, "low": 2}[_risk_key(row.prediction.get("risk_level"))],
                -float(row.prediction.get("confidence", 0) or 0),
            ),
        )
        ranked = ranked if self.show_all_matches else ranked[:3]
        self._resize_match_list_area(len(ranked))
        if hasattr(self, "match_toggle_var"):
            text = "\u6536\u8d77 \u2039" if self.show_all_matches else f"\u67e5\u770b\u5168\u90e8 {len(filtered_rows)} \u203a"
            self.match_toggle_var.set(text)

        if not ranked:
            if self.rows and not filtered_rows:
                tk.Label(
                    self.match_list,
                    text="\u6682\u65e0\u7b26\u5408\u5f53\u524d\u51c6\u5165\u7b5b\u9009\u7684\u8d5b\u4e8b\u3002",
                    bg=PANEL,
                    fg=MUTED,
                    font=("Microsoft YaHei UI", 11),
                ).pack(anchor=tk.W, pady=20)
                if self._widget_alive("match_canvas"):
                    self.match_canvas.configure(scrollregion=self.match_canvas.bbox("all"))
                    self.match_canvas.yview_moveto(0)
                return
            tk.Label(self.match_list, text="暂无通过校验的赛事数据", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 11)).pack(anchor=tk.W, pady=20)
            if self._widget_alive("match_canvas"):
                self.match_canvas.configure(scrollregion=self.match_canvas.bbox("all"))
                self.match_canvas.yview_moveto(0)
            return

        for row in ranked:
            self._match_row(row)
        if self._widget_alive("match_canvas"):
            self.match_canvas.configure(scrollregion=self.match_canvas.bbox("all"))
            self.match_canvas.yview_moveto(0)

    def _match_row(self, row: DashboardRow) -> None:
        match = row.match
        pred = row.prediction
        governance = self._main_flow_governance_status(row)
        frame = tk.Frame(self.match_list, bg=PANEL_2, highlightbackground="#172638", highlightthickness=1)
        frame.pack(fill=tk.X, pady=3)
        frame.configure(cursor="hand2")

        left = tk.Frame(frame, bg=PANEL_2)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=16, pady=6)
        tk.Label(left, text=match.league, bg=PANEL_2, fg="#6d8dff", font=("Microsoft YaHei UI", 8, "bold")).pack(anchor=tk.W)
        tk.Label(left, text=f"{match.home_team} vs {match.away_team}", bg=PANEL_2, fg=TEXT, font=("Microsoft YaHei UI", 11, "bold")).pack(anchor=tk.W, pady=(3, 1))
        tk.Label(left, text=f"开赛时间：{match.match_date} {match.match_time}", bg=PANEL_2, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)

        for title, value, color, width in [
            ("风险等级", _risk_label(pred.get("risk_level")), _risk_color(pred.get("risk_level")), 112),
            ("置信度", _pct(pred.get("confidence")), TEXT, 88),
            ("策略准入", _admission_text(pred), _admission_color(pred), 96),
            ("\u4e3b\u6d41\u7a0b", _governance_text(governance), _governance_color(governance), 126),
            ("推荐策略", _strategy_text(pred), TEXT, 150),
        ]:
            block = tk.Frame(frame, bg=PANEL_2, width=width)
            block.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6), pady=8)
            block.pack_propagate(False)
            tk.Label(block, text=title, bg=PANEL_2, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)
            tk.Label(block, text=value, bg=PANEL_2, fg=color, font=("Microsoft YaHei UI", 12, "bold"), wraplength=width - 8, justify=tk.LEFT).pack(anchor=tk.W, pady=(8, 0))

        self._bind_detail_open(frame, row)

    def _bind_detail_open(self, widget: tk.Widget, row: DashboardRow) -> None:
        widget.bind("<Button-1>", lambda _event: self.open_match_detail(row))
        try:
            widget.configure(cursor="hand2")
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._bind_detail_open(child, row)

    def open_match_detail(self, row: DashboardRow) -> None:
        self.current_view = "match_detail"
        title = f"{row.match.home_team} vs {row.match.away_team}"
        shell = self._page_shell(title, f"{row.match.league}  |  {row.match.match_date} {row.match.match_time}")

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        tk.Button(
            top,
            text="\u8fd4\u56de\u6982\u89c8",
            command=self._build_main,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground=TEXT,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=6,
        ).pack(side=tk.LEFT)
        tk.Button(
            top,
            text="\u4fdd\u5b58\u62a5\u544a",
            command=lambda: self.save_match_report(row),
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=6,
        ).pack(side=tk.RIGHT)

        summary = tk.Frame(shell, bg=BG)
        summary.pack(fill=tk.X, pady=(0, 16))
        pred = row.prediction
        governance = self._main_flow_governance_status(row)
        draw_guard_label, _draw_guard_body, draw_guard_tone = _draw_release_guard_summary(pred)
        for label, value, color in [
            ("\u98ce\u9669\u7b49\u7ea7", _risk_label(pred.get("risk_level")), _risk_color(pred.get("risk_level"))),
            ("策略准入", _admission_text(pred), _admission_color(pred)),
            ("\u4e3b\u6d41\u7a0b", _governance_text(governance), _governance_color(governance)),
            ("\u63a8\u8350\u7b56\u7565", _strategy_text(pred), TEXT),
            ("\u7f6e\u4fe1\u5ea6", _pct1(pred.get("confidence")), "#7aa2ff"),
            ("\u5e73\u5c40\u63a5\u7ba1", draw_guard_label, self._tone_color(draw_guard_tone)),
            ("\u8d5b\u4e8b\u6a21\u5f0f", _competition_mode_label(pred), YELLOW if pred.get("competition_mode") == "world_cup" else TEXT),
            ("\u8bc4\u5206\u6c60", _rating_pool_label(pred), YELLOW if pred.get("rating_pool") == "national_team" else TEXT),
        ]:
            self._detail_metric(summary, label, value, color)

        self._draw_agent_trace_panel(shell, row)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)

        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        tk.Label(left, text="\u6982\u7387\u4e0e\u98ce\u9669", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        self._draw_probability_panel(left, row)

        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(right, text="AI \u5206\u6790\u62a5\u544a", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        text = tk.Text(
            right,
            wrap=tk.WORD,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10),
            padx=16,
            pady=8,
        )
        text.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 14))
        text.insert("1.0", _analysis_report(row, governance_status=governance))
        text.configure(state=tk.DISABLED)

    def _agent_status_color(self, status: object) -> str:
        return {
            "ready": GREEN,
            "completed": GREEN,
            "watch": YELLOW,
            "alert": RED,
            "blocked": RED,
        }.get(str(status or "").lower(), MUTED)

    def _set_agent_trace_detail(
        self,
        detail_widget: tk.Text,
        node: dict,
        node_frames: list[tuple[tk.Frame, dict]],
    ) -> None:
        detail_widget.configure(state=tk.NORMAL)
        detail_widget.delete("1.0", tk.END)
        detail_widget.insert("1.0", format_agent_trace_detail(node))
        detail_widget.configure(state=tk.DISABLED)
        for frame, item in node_frames:
            selected = item is node
            frame.configure(
                highlightbackground=self._agent_status_color(item.get("status")) if selected else "#172638",
                highlightthickness=2 if selected else 1,
            )

    def _draw_agent_trace_panel(self, parent: tk.Widget, row: DashboardRow) -> None:
        supervisor = row.prediction.get("supervisor") if isinstance(row.prediction, dict) else {}
        nodes = build_agent_trace_nodes(supervisor)
        if not nodes:
            return

        frame = self._card(parent, PANEL)
        frame.pack(fill=tk.X, pady=(0, 16))
        header = tk.Frame(frame, bg=PANEL)
        header.pack(fill=tk.X, padx=18, pady=(14, 8))
        tk.Label(
            header,
            text="Agent 思考链路",
            bg=PANEL,
            fg=TEXT,
            font=("Microsoft YaHei UI", 13, "bold"),
        ).pack(side=tk.LEFT)
        supervisor_status = str((supervisor or {}).get("status") or "-") if isinstance(supervisor, dict) else "-"
        actions = (supervisor or {}).get("next_actions") if isinstance(supervisor, dict) else []
        action_text = ", ".join(str(item) for item in actions) if isinstance(actions, list) and actions else "-"
        tk.Label(
            header,
            text=f"Supervisor: {supervisor_status} | next: {action_text}",
            bg=PANEL,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
        ).pack(side=tk.RIGHT)

        node_row = tk.Frame(frame, bg=PANEL)
        node_row.pack(fill=tk.X, padx=18, pady=(0, 8))
        node_frames: list[tuple[tk.Frame, dict]] = []

        for index, node in enumerate(nodes):
            color = self._agent_status_color(node.get("status"))
            checks = node.get("checks") if isinstance(node.get("checks"), list) else []
            actions_for_node = node.get("actions") if isinstance(node.get("actions"), list) else []
            node_frame = tk.Frame(node_row, bg=PANEL_2, highlightbackground="#172638", highlightthickness=1)
            node_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
            node_frame.configure(cursor="hand2")
            tk.Label(
                node_frame,
                text=str(node.get("name") or "-"),
                bg=PANEL_2,
                fg=TEXT,
                font=("Microsoft YaHei UI", 9, "bold"),
                wraplength=120,
            ).pack(anchor=tk.W, padx=10, pady=(8, 2))
            tk.Label(
                node_frame,
                text=str(node.get("status_label") or "-"),
                bg=PANEL_2,
                fg=color,
                font=("Microsoft YaHei UI", 10, "bold"),
            ).pack(anchor=tk.W, padx=10)
            tk.Label(
                node_frame,
                text=str(node.get("summary") or "-"),
                bg=PANEL_2,
                fg=MUTED,
                font=("Microsoft YaHei UI", 8),
                wraplength=120,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, padx=10, pady=(2, 8))
            tk.Label(
                node_frame,
                text=f"checks {len(checks)} | actions {len(actions_for_node)}",
                bg=PANEL_2,
                fg=color if actions_for_node else MUTED,
                font=("Microsoft YaHei UI", 8),
                wraplength=120,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, padx=10, pady=(0, 8))
            node_frames.append((node_frame, node))
            command = lambda item=node: self._set_agent_trace_detail(detail_text, item, node_frames)
            node_frame.bind("<Button-1>", lambda _event, cmd=command: cmd())
            for child in node_frame.winfo_children():
                child.configure(cursor="hand2")
                child.bind("<Button-1>", lambda _event, cmd=command: cmd())
            if index < len(nodes) - 1:
                tk.Label(node_row, text="->", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 12, "bold")).pack(
                    side=tk.LEFT,
                    padx=(0, 6),
                )

        detail_shell = tk.Frame(frame, bg="#0a111c", highlightbackground="#172638", highlightthickness=1)
        detail_shell.pack(fill=tk.X, padx=18, pady=(0, 14))
        detail_text = tk.Text(
            detail_shell,
            height=9,
            wrap=tk.WORD,
            bg="#0a111c",
            fg=TEXT,
            insertbackground=TEXT,
            font=("Consolas", 9),
            relief=tk.FLAT,
            padx=12,
            pady=10,
        )
        detail_scroll = tk.Scrollbar(detail_shell, orient=tk.VERTICAL, command=detail_text.yview)
        detail_text.configure(yscrollcommand=detail_scroll.set)
        detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._set_agent_trace_detail(detail_text, nodes[0], node_frames)

    def save_match_report(self, row: DashboardRow) -> Path:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        name = f"ai_match_report_{now.strftime('%Y%m%d_%H%M%S')}_{_slug(row.match.home_team)}_vs_{_slug(row.match.away_team)}.md"
        path = REPORT_DIR / name
        path.write_text(_markdown_report(row, generated_at=now, governance_status=self._main_flow_governance_status(row)), encoding="utf-8")
        self.status_var.set(f"\u62a5\u544a\u5df2\u4fdd\u5b58: {path.name}")
        messagebox.showinfo("\u4fdd\u5b58\u62a5\u544a", f"\u5df2\u751f\u6210\u62a5\u544a:\n{path}")
        return path

    def open_governance_issue_center(self) -> None:
        self.current_nav_index = 1
        self.current_view = "governance_issue"
        self._refresh_nav_highlight()

        governance_counts = self.main_flow_governance_counts if isinstance(self.main_flow_governance_counts, dict) else {}
        issue_rows: list[tuple[DashboardRow, dict]] = []
        for row in self.rows:
            governance = self._main_flow_governance_status(row)
            if str(governance.get("status") or "") in {"blocked", "needs_c1_review"}:
                issue_rows.append((row, governance))
        issue_rows.sort(
            key=lambda item: (
                0 if str(item[1].get("status") or "") == "blocked" else 1,
                -float(item[0].prediction.get("confidence", 0) or 0),
                item[0].match.match_date,
                item[0].match.match_time,
                item[0].match.home_team,
            )
        )

        shell = self._page_shell("治理详情", "聚焦 C1 待审与阻断场次，查看主阻断、决策链和补齐建议")
        header = tk.Frame(shell, bg=BG)
        header.pack(fill=tk.X)
        tk.Button(
            header,
            text="返回主流程",
            command=self._build_main,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground=TEXT,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=6,
        ).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(
            header,
            text="正式建议",
            command=lambda: self.open_governance_filtered_matches("formal_ready"),
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=6,
        ).pack(side=tk.RIGHT)

        metrics = tk.Frame(shell, bg=BG)
        metrics.pack(fill=tk.X, pady=(0, 16))
        issue_total = int(governance_counts.get("blocked", 0) or 0) + int(governance_counts.get("needs_c1_review", 0) or 0)
        for label, value, color in [
            ("问题场次", str(issue_total), RED if issue_total else GREEN),
            ("阻断", str(governance_counts.get("blocked", 0)), RED if int(governance_counts.get("blocked", 0) or 0) else GREEN),
            ("C1 待审", str(governance_counts.get("needs_c1_review", 0)), YELLOW if int(governance_counts.get("needs_c1_review", 0) or 0) else GREEN),
            ("正式建议", str(governance_counts.get("formal_ready", 0)), GREEN),
        ]:
            self._detail_metric(metrics, label, value, color)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)

        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="问题列表", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
        issue_summary_var = tk.StringVar(value="")
        tk.Label(left, textvariable=issue_summary_var, bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W, padx=18, pady=(0, 10))

        issue_filter = "all"
        filter_bar = tk.Frame(left, bg=PANEL)
        filter_bar.pack(fill=tk.X, padx=18, pady=(0, 10))
        tk.Label(filter_bar, text="筛选", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        issue_filter_buttons: dict[str, tk.Button] = {}

        issue_wrap = tk.Frame(left, bg=PANEL, height=470)
        issue_wrap.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 14))
        issue_wrap.pack_propagate(False)
        issue_canvas = tk.Canvas(issue_wrap, bg=PANEL, bd=0, highlightthickness=0)
        issue_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        issue_scrollbar = tk.Scrollbar(issue_wrap, orient=tk.VERTICAL, command=issue_canvas.yview)
        issue_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        issue_canvas.configure(yscrollcommand=issue_scrollbar.set)
        issue_list = tk.Frame(issue_canvas, bg=PANEL)
        issue_list_window = issue_canvas.create_window((0, 0), window=issue_list, anchor=tk.NW)
        issue_list.bind("<Configure>", lambda _event: issue_canvas.configure(scrollregion=issue_canvas.bbox("all")))
        issue_canvas.bind("<Configure>", lambda event: issue_canvas.itemconfigure(issue_list_window, width=event.width))
        self._bind_canvas_mousewheel(issue_list, issue_canvas)

        tk.Label(right, text="选中详情", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
        selected_var = tk.StringVar(value="请选择左侧问题场次")
        tk.Label(right, textvariable=selected_var, bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W, padx=18, pady=(0, 10))
        action_bar = tk.Frame(right, bg=PANEL)
        action_bar.pack(fill=tk.X, padx=18, pady=(0, 10))
        open_detail_button = tk.Button(
            action_bar,
            text="打开比赛详情",
            command=lambda: None,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground=TEXT,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
            state=tk.DISABLED,
        )
        open_detail_button.pack(side=tk.LEFT)
        tk.Button(
            action_bar,
            text="问题转正式建议",
            command=lambda: self.open_governance_filtered_matches("formal_ready"),
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT, padx=(8, 0))

        detail_text = tk.Text(
            right,
            wrap=tk.WORD,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10),
            padx=16,
            pady=8,
        )
        detail_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 14))

        filtered_rows: list[tuple[DashboardRow, dict]] = []
        selected_index = -1
        row_frames: list[tuple[tk.Frame, DashboardRow, dict]] = []

        def refresh_filter_buttons() -> None:
            labels = {
                "all": "全部问题",
                "needs_c1_review": "仅 C1 待审",
                "blocked": "仅阻断",
            }
            colors = {
                "all": BLUE,
                "needs_c1_review": YELLOW,
                "blocked": RED,
            }
            for key, button in issue_filter_buttons.items():
                active = key == issue_filter
                button.configure(
                    text=f"{labels.get(key, key)}",
                    bg=colors.get(key, BLUE) if active else PANEL_2,
                    fg="white" if active else TEXT,
                    activebackground=colors.get(key, BLUE) if active else "#172638",
                )

        def set_filter(selected: str) -> None:
            nonlocal issue_filter
            issue_filter = selected if selected in {"all", "needs_c1_review", "blocked"} else "all"
            refresh_filter_buttons()
            refresh_issue_list()

        for key, label in [
            ("all", "全部问题"),
            ("needs_c1_review", "C1 待审"),
            ("blocked", "阻断"),
        ]:
            button = tk.Button(
                filter_bar,
                text=label,
                command=lambda key=key: set_filter(key),
                bg=PANEL_2,
                fg=TEXT,
                activebackground="#172638",
                activeforeground="white",
                relief=tk.FLAT,
                font=("Microsoft YaHei UI", 9, "bold"),
                padx=12,
                pady=5,
            )
            button.pack(side=tk.LEFT, padx=(0, 6))
            issue_filter_buttons[key] = button

        def set_selected(index: int) -> None:
            nonlocal selected_index
            if index < 0 or index >= len(filtered_rows):
                return
            selected_index = index
            row, governance = filtered_rows[index]
            selected_var.set(
                f"{governance.get('label', '-')} | {row.match.home_team} vs {row.match.away_team} | {governance.get('primary_blocker', '-')}"
            )
            detail_text.configure(state=tk.NORMAL)
            detail_text.delete("1.0", tk.END)
            detail_text.insert("1.0", build_main_flow_governance_issue_detail_text(row, governance))
            detail_text.configure(state=tk.DISABLED)
            open_detail_button.configure(
                state=tk.NORMAL,
                command=lambda current=row: self.open_match_detail(current),
            )
            for frame, item_row, item_governance in row_frames:
                selected = item_row is row
                frame.configure(
                    highlightbackground=_governance_color(item_governance) if selected else "#172638",
                    highlightthickness=2 if selected else 1,
                )

        def refresh_issue_list() -> None:
            nonlocal filtered_rows, selected_index, row_frames
            for child in issue_list.winfo_children():
                child.destroy()
            row_frames = []
            filtered_rows = [
                item
                for item in issue_rows
                if issue_filter == "all" or str(item[1].get("status") or "") == issue_filter
            ]
            issue_summary_var.set(
                f"匹配 {len(filtered_rows)}/{len(issue_rows)} | 阻断 {int(governance_counts.get('blocked', 0) or 0)} | C1 待审 {int(governance_counts.get('needs_c1_review', 0) or 0)}"
            )

            if not filtered_rows:
                selected_index = -1
                selected_var.set("当前筛选没有问题场次")
                detail_text.configure(state=tk.NORMAL)
                detail_text.delete("1.0", tk.END)
                detail_text.insert("1.0", "当前筛选没有 C1 待审或阻断场次。")
                detail_text.configure(state=tk.DISABLED)
                open_detail_button.configure(state=tk.DISABLED, command=lambda: None)
                tk.Label(
                    issue_list,
                    text="当前筛选没有 C1 待审或阻断场次。",
                    bg=PANEL,
                    fg=MUTED,
                    font=("Microsoft YaHei UI", 11),
                ).pack(anchor=tk.W, pady=18)
                issue_canvas.configure(scrollregion=issue_canvas.bbox("all"))
                issue_canvas.yview_moveto(0)
                return

            for index, (row, governance) in enumerate(filtered_rows):
                color = _governance_color(governance)
                frame = tk.Frame(issue_list, bg=PANEL_2, highlightbackground="#172638", highlightthickness=1)
                frame.pack(fill=tk.X, pady=4)
                frame.configure(cursor="hand2")
                top = tk.Frame(frame, bg=PANEL_2)
                top.pack(fill=tk.X, padx=12, pady=(10, 4))
                tk.Label(
                    top,
                    text=f"{row.match.home_team} vs {row.match.away_team}",
                    bg=PANEL_2,
                    fg=TEXT,
                    font=("Microsoft YaHei UI", 10, "bold"),
                    wraplength=220,
                    justify=tk.LEFT,
                ).pack(anchor=tk.W)
                tk.Label(
                    top,
                    text=f"{row.match.league} | {row.match.match_date} {row.match.match_time}",
                    bg=PANEL_2,
                    fg=MUTED,
                    font=("Microsoft YaHei UI", 8),
                ).pack(anchor=tk.W, pady=(1, 0))
                tk.Label(
                    frame,
                    text=str(governance.get("label") or governance.get("status") or "-"),
                    bg=PANEL_2,
                    fg=color,
                    font=("Microsoft YaHei UI", 9, "bold"),
                ).pack(anchor=tk.W, padx=12)
                tk.Label(
                    frame,
                    text=f"{governance.get('primary_blocker', '-')} | {governance.get('recommendation', '-')}",
                    bg=PANEL_2,
                    fg=TEXT,
                    font=("Microsoft YaHei UI", 9),
                    wraplength=260,
                    justify=tk.LEFT,
                ).pack(anchor=tk.W, padx=12, pady=(4, 10))
                row_frames.append((frame, row, governance))

                def bind_click(widget: tk.Widget, current_index: int = index) -> None:
                    widget.bind("<Button-1>", lambda _event, idx=current_index: set_selected(idx))
                    try:
                        widget.configure(cursor="hand2")
                    except tk.TclError:
                        pass
                    for child in widget.winfo_children():
                        bind_click(child, current_index)

                bind_click(frame)

            issue_canvas.configure(scrollregion=issue_canvas.bbox("all"))
            issue_canvas.yview_moveto(0)
            set_selected(0)

        refresh_filter_buttons()
        refresh_issue_list()

    def open_history_reports(self) -> None:
        self.current_nav_index = 3
        self.current_view = "history"
        self._refresh_nav_highlight()
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_rows = list_dashboard_report_files(REPORT_DIR, limit=200)

        shell = self._page_shell("\u5386\u53f2\u62a5\u544a", f"\u62a5\u544a\u76ee\u5f55: {REPORT_DIR}")

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        filter_box = tk.Frame(left, bg=PANEL)
        filter_box.pack(fill=tk.X, padx=10, pady=(10, 0))
        type_var = tk.StringVar(value="\u5168\u90e8")
        search_var = tk.StringVar(value="")
        type_options = dashboard_report_type_options(report_rows)
        ttk.Combobox(
            filter_box,
            state="readonly",
            textvariable=type_var,
            values=type_options,
            width=18,
        ).pack(fill=tk.X, pady=(0, 8))
        search_entry = tk.Entry(
            filter_box,
            textvariable=search_var,
            bg=PANEL_2,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10),
        )
        search_entry.pack(fill=tk.X)
        summary_text = tk.StringVar(value="")
        tk.Label(filter_box, textvariable=summary_text, bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 9), justify=tk.LEFT).pack(anchor=tk.W, pady=(8, 0))

        listbox = tk.Listbox(
            left,
            bg=PANEL,
            fg=TEXT,
            selectbackground=BLUE,
            selectforeground="white",
            relief=tk.FLAT,
            width=38,
            font=("Microsoft YaHei UI", 10),
            activestyle="none",
        )
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        preview = tk.Text(
            right,
            wrap=tk.WORD,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10),
            padx=16,
            pady=12,
        )
        preview.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        filtered_rows: list[dict[str, object]] = []

        def show_file(index: int) -> None:
            if index < 0 or index >= len(filtered_rows):
                return
            path = filtered_rows[index].get("path")
            if not isinstance(path, Path):
                return
            try:
                content = path.read_text(encoding="utf-8")
            except Exception as exc:
                content = f"\u8bfb\u53d6\u5931\u8d25: {exc}"
            preview.configure(state=tk.NORMAL)
            preview.delete("1.0", tk.END)
            preview.insert("1.0", content)
            preview.configure(state=tk.DISABLED)

        def refresh_report_list(_event=None) -> None:
            nonlocal filtered_rows
            filtered_rows = filter_dashboard_report_rows(
                report_rows,
                selected_type=type_var.get(),
                query=search_var.get(),
            )
            listbox.delete(0, tk.END)
            preview.configure(state=tk.NORMAL)
            preview.delete("1.0", tk.END)
            counts = summarize_dashboard_report_types(filtered_rows)
            count_text = " / ".join(f"{label}:{count}" for label, count in counts.items()) or "-"
            summary_text.set(f"\u5339\u914d {len(filtered_rows)}/{len(report_rows)} | {count_text}")
            for row in filtered_rows:
                path = row.get("path")
                if not isinstance(path, Path):
                    continue
                listbox.insert(tk.END, f"{row.get('updated_at', '-')}  [{row.get('label', '-')}]  {path.name}")
            if filtered_rows:
                listbox.selection_set(0)
                show_file(0)
            else:
                preview.insert("1.0", "\u6682\u65e0\u5339\u914d\u7684\u5386\u53f2\u62a5\u544a\u3002")
                preview.configure(state=tk.DISABLED)

        if report_rows:
            refresh_report_list()
        else:
            summary_text.set("\u5339\u914d 0/0 | -")
            preview.insert("1.0", "\u6682\u65e0\u5386\u53f2\u62a5\u544a\u3002")
            preview.configure(state=tk.DISABLED)

        listbox.bind("<<ListboxSelect>>", lambda _event: show_file(listbox.curselection()[0] if listbox.curselection() else -1))
        type_var.trace_add("write", lambda *_args: refresh_report_list())
        search_var.trace_add("write", lambda *_args: refresh_report_list())

    def open_data_center(self) -> None:
        self.current_nav_index = 5
        self.current_view = "data"
        self._refresh_nav_highlight()
        shell = self._page_shell(
            "\u6570\u636e\u4e2d\u5fc3",
            "\u5f53\u524d\u6570\u636e\u6e90\u3001\u7f13\u5b58\u3001\u6a21\u578b\u72b6\u6001\u548c\u62a5\u544a\u4ea7\u7269",
        )

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        risk_counts = self._risk_counts()
        report_count = len(list_dashboard_report_files(REPORT_DIR, limit=10000)) if REPORT_DIR.exists() else 0
        load_report = self.last_load_diagnostics if isinstance(self.last_load_diagnostics, dict) else {}
        source_health = _source_health_summary(load_report)
        cache_status = _cache_status_summary(load_report)
        cache_tone = _cache_status_tone(load_report)
        metrics = [
            ("\u6570\u636e\u6e90", self.data_source, "#7aa2ff"),
            ("\u6e90\u5065\u5eb7", source_health, GREEN if "\u6b63\u5e38" in source_health or "\u5408\u5e76" in source_health else YELLOW),
            ("\u7f13\u5b58\u56de\u9000", cache_status, self._tone_color(cache_tone)),
            ("\u4eca\u65e5\u8d5b\u4e8b", str(len(self.rows)), TEXT),
            ("\u9ad8\u98ce\u9669", str(risk_counts.get("high", 0)), RED),
            ("\u5386\u53f2\u62a5\u544a", str(report_count), TEXT),
        ]
        for label, value, color in metrics:
            self._detail_metric(top, label, value, color)

        freeze_alerts = build_strategy_policy_freeze_alerts(freeze_override, draw_guard_freeze)
        freeze_cards = [item for item in freeze_alerts.get("alerts", []) if isinstance(item, dict)] if isinstance(freeze_alerts, dict) else []
        if freeze_cards:
            freeze_wrap = tk.Frame(shell, bg=BG)
            freeze_wrap.pack(fill=tk.X, pady=(0, 16))
            tk.Label(freeze_wrap, text="????", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(0, 8))
            freeze_row = tk.Frame(freeze_wrap, bg=BG)
            freeze_row.pack(fill=tk.X)
            for index, alert in enumerate(freeze_cards[:2]):
                column = tk.Frame(freeze_row, bg=BG)
                column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8) if index == 0 else (8, 0))
                self._alert_card(
                    column,
                    str(alert.get("title") or "-"),
                    str(alert.get("body") or "-"),
                    tone=str(alert.get("tone") or "warning"),
                )

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u8fd0\u884c\u72b6\u6001", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        status_rows = [
            ("\u9879\u76ee\u76ee\u5f55", str(PROJECT_ROOT)),
            ("\u6700\u8fd1\u52a0\u8f7d", self.last_loaded_at),
            ("\u6e90\u5065\u5eb7", source_health),
            ("\u7f13\u5b58\u56de\u9000", cache_status),
            ("\u5f53\u524d\u6a21\u578b", self._dominant_model_name()),
            ("\u5e73\u5747\u7f6e\u4fe1\u5ea6", self._average_confidence()),
            ("\u62a5\u544a\u76ee\u5f55", str(REPORT_DIR)),
        ]
        for label, value in status_rows:
            self._kv_row(left, label, value)

        tk.Label(right, text="\u6570\u636e\u6587\u4ef6", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        data_rows = self._data_inventory_rows()
        for label, value in data_rows:
            self._kv_row(right, label, value)

        source_rows = _source_health_rows(load_report)
        if source_rows:
            tk.Label(right, text="\u5728\u7ebf\u6e90\u72b6\u6001", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
            for row in source_rows:
                self._kv_row(right, f"{row.get('source', '-')} / {row.get('status', '-')}", str(row.get("detail") or "-"))

        tk.Label(left, text="\u7f13\u5b58\u56de\u9000", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        for label, value in _cache_status_rows(load_report):
            self._kv_row(left, label, value)

        tk.Button(
            shell,
            text="\u5237\u65b0\u6570\u636e",
            command=self.refresh,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(anchor=tk.E, pady=(14, 0))
        tk.Button(
            shell,
            text="\u91cd\u8bd5\u5728\u7ebf\u6e90",
            command=lambda: self.refresh(force_live=True),
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(anchor=tk.E, pady=(8, 0))
        tk.Button(
            shell,
            text="\u8bfb\u53d6\u7f13\u5b58\u6c60",
            command=lambda: self.refresh(cache_only=True),
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(anchor=tk.E, pady=(8, 0))

    def _dominant_model_name(self) -> str:
        for row in self.rows:
            model = str(row.prediction.get("model") or "").strip()
            if model:
                return model
        return "-"

    def _average_confidence(self) -> str:
        values = [float(row.prediction.get("confidence", 0) or 0) for row in self.rows]
        if not values:
            return "-"
        return f"{sum(values) / len(values):.1%}"

    def _data_inventory_rows(self) -> list[tuple[str, str]]:
        paths = [
            ("cache", PROJECT_ROOT / "data" / "cache"),
            ("state", PROJECT_ROOT / "data" / "state"),
            ("models", PROJECT_ROOT / "data" / "models"),
            ("c1_state", PROJECT_ROOT / "data" / "c1_state"),
            ("reports", REPORT_DIR),
        ]
        rows: list[tuple[str, str]] = []
        for label, path in paths:
            count, size = _dir_stats(path)
            rows.append((label, f"{count} files / {_bytes_text(size)} / updated {_mtime_text(path)}"))

        key_files = [
            ("500_config", PROJECT_ROOT / "config" / "500_config.json"),
            ("settlements", PROJECT_ROOT / "data" / "state" / "settlements.json"),
            ("prediction_snapshots", PROJECT_ROOT / "data" / "state" / "prediction_snapshots.json"),
            ("result_recovery_runs", PROJECT_ROOT / "data" / "state" / "result_recovery_runs.json"),
            ("xgb_model", PROJECT_ROOT / "data" / "models" / "xgb_v0_match_outcome.json"),
        ]
        for label, path in key_files:
            rows.append((label, f"{'OK' if path.exists() else 'missing'} / updated {_mtime_text(path)}"))
        return rows

    def _kv_row(self, parent: tk.Widget, label: str, value: str) -> None:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill=tk.X, padx=18, pady=7)
        tk.Label(row, text=label, bg=PANEL, fg=MUTED, width=18, anchor=tk.W, font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
        tk.Label(row, text=value, bg=PANEL, fg=TEXT, anchor=tk.W, justify=tk.LEFT, wraplength=320, font=("Microsoft YaHei UI", 10, "bold")).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _log_event(self, level: str, message: str) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.event_log.insert(0, (stamp, level, message))
        self.event_log = self.event_log[:200]

    def run_high_accuracy_strategy_backtest_task(self) -> None:
        self._submit_process_task(
            key="high_accuracy_strategy_backtest",
            label="\u9ad8\u51c6\u7b56\u7565\u5386\u53f2\u56de\u6d4b",
            start_status="\u6b63\u5728\u540e\u53f0\u8fdb\u7a0b\u4e2d\u6267\u884c\u9ad8\u51c6\u7b56\u7565\u56de\u6d4b...",
            func=run_high_accuracy_strategy_backtest,
            group="backtest",
            priority=120,
            on_success=self._finish_high_accuracy_strategy_backtest_task,
            error_title="\u9ad8\u51c6\u7b56\u7565\u56de\u6d4b\u5931\u8d25",
        )

    def run_play_model_backtest_task(self) -> None:
        self._submit_process_task(
            key="play_model_backtest",
            label="\u73a9\u6cd5\u6a21\u578b\u5386\u53f2\u56de\u6d4b",
            start_status="\u6b63\u5728\u540e\u53f0\u8fdb\u7a0b\u4e2d\u6267\u884c\u73a9\u6cd5\u6a21\u578b\u56de\u6d4b...",
            func=run_play_model_backtest,
            group="backtest",
            priority=130,
            on_success=self._finish_play_model_backtest_task,
            error_title="\u73a9\u6cd5\u6a21\u578b\u56de\u6d4b\u5931\u8d25",
        )

    def export_play_model_takeover_gate_audit_report(self) -> None:
        self._submit_process_task(
            key="play_model_takeover_gate_audit_export",
            label="\u63a5\u7ba1\u5b88\u95e8\u5ba1\u8ba1\u5bfc\u51fa",
            start_status="\u6b63\u5728\u540e\u53f0\u8fdb\u7a0b\u4e2d\u5bfc\u51fa\u63a5\u7ba1\u5b88\u95e8\u5ba1\u8ba1\u62a5\u544a...",
            func=export_play_model_takeover_gate_audit_report_now,
            group="report",
            priority=115,
            on_success=self._finish_play_model_takeover_gate_audit_export_task,
            error_title="\u63a5\u7ba1\u5b88\u95e8\u5ba1\u8ba1\u5bfc\u51fa\u5931\u8d25",
        )

    def run_draw_specialist_backtest_task(self) -> None:
        self._submit_process_task(
            key="draw_specialist_backtest",
            label="\u5e73\u5c40\u4e13\u9879\u56de\u6d4b",
            start_status="\u6b63\u5728\u540e\u53f0\u8fdb\u7a0b\u4e2d\u56de\u6d4b\u5e73\u5c40\u8bc6\u522b\u80fd\u529b...",
            func=run_draw_specialist_backtest,
            group="backtest",
            priority=128,
            on_success=self._finish_draw_specialist_backtest_task,
            error_title="\u5e73\u5c40\u4e13\u9879\u56de\u6d4b\u5931\u8d25",
        )

    def train_play_models_task(self) -> None:
        self._submit_process_task(
            key="train_play_models",
            label="\u73a9\u6cd5\u6a21\u578b\u8bad\u7ec3",
            start_status="\u6b63\u5728\u540e\u53f0\u8fdb\u7a0b\u4e2d\u8bad\u7ec3\u73a9\u6cd5\u6a21\u578b...",
            func=train_play_models_now,
            group="model",
            priority=160,
            on_success=self._finish_train_play_models_task,
            error_title="\u73a9\u6cd5\u6a21\u578b\u8bad\u7ec3\u5931\u8d25",
        )

    def _submit_process_task(
        self,
        *,
        key: str,
        label: str,
        start_status: str,
        func,
        on_success,
        error_title: str,
        group: str = "model",
        priority: int = 150,
        args: tuple = (),
        kwargs: dict | None = None,
        metadata: dict | None = None,
    ) -> None:
        task = self.background_tasks.submit(
            key=key,
            label=label,
            func=func,
            args=args,
            kwargs=kwargs or {},
            mode="process",
            group=group,
            priority=priority,
            metadata={"group": group, "priority": priority, **dict(metadata or {})},
            on_success=on_success,
            on_error=lambda exc, record: self._finish_process_task_error(error_title, exc, record),
        )
        if task is None:
            message = f"{label}\u5df2\u5728\u540e\u53f0\u8fd0\u884c\uff0c\u8bf7\u5148\u7b49\u5f85\u5f53\u524d\u4efb\u52a1\u5b8c\u6210\u3002"
            self.status_var.set(message)
            self._log_event("INFO", message)
            return
        self.status_var.set(start_status)
        self._log_event("INFO", f"\u5df2\u63d0\u4ea4\u540e\u53f0\u8fdb\u7a0b\u4efb\u52a1: {label} / {task.task_id}")
        if getattr(self, "current_view", "") == "monitor":
            self.open_monitor_center()

    def _finish_process_task_error(self, title: str, exc: BaseException, record: BackgroundTaskRecord) -> None:
        message = f"{title}: {exc}"
        self.status_var.set(message)
        self._log_event("ERROR", f"{message} | {record.task_id}")
        if getattr(self, "current_view", "") == "monitor":
            self.open_monitor_center()
        messagebox.showerror(title, str(exc))

    def _finish_high_accuracy_strategy_backtest_task(self, result: object, record: BackgroundTaskRecord) -> None:
        payload = result if isinstance(result, dict) else {}
        self.status_var.set(build_high_accuracy_strategy_backtest_status_text(payload))
        self._log_event("OK", f"\u9ad8\u51c6\u7b56\u7565\u56de\u6d4b\u5b8c\u6210 | {record.task_id} | {record.elapsed_seconds or 0:.2f}s")
        self.summary_vars["hit_rate"].set(self._historical_hit_rate())
        self._refresh_current_view_after_release_state_change()
        if bool(payload.get("ok")):
            messagebox.showinfo("\u9ad8\u51c6\u7b56\u7565\u56de\u6d4b", build_high_accuracy_strategy_backtest_message(payload))
        else:
            messagebox.showinfo("\u9ad8\u51c6\u7b56\u7565\u56de\u6d4b", f"\u56de\u6d4b\u672a\u5b8c\u6210\n\u539f\u56e0: {payload.get('reason', '-')}")

    def _finish_play_model_backtest_task(self, result: object, record: BackgroundTaskRecord) -> None:
        payload = result if isinstance(result, dict) else {}
        self.status_var.set(build_play_model_backtest_apply_status_text(payload))
        self._log_event("OK", f"\u73a9\u6cd5\u6a21\u578b\u56de\u6d4b\u5b8c\u6210 | {record.task_id} | {record.elapsed_seconds or 0:.2f}s")
        if getattr(self, "current_view", "") == "monitor":
            self.open_monitor_center()
        if bool(payload.get("ok")):
            messagebox.showinfo("\u73a9\u6cd5\u6a21\u578b\u56de\u6d4b", build_play_model_backtest_success_message(payload))
        else:
            messagebox.showinfo("\u73a9\u6cd5\u6a21\u578b\u56de\u6d4b", f"\u56de\u6d4b\u672a\u5b8c\u6210\n\u539f\u56e0: {payload.get('reason', '-')}")

    def _finish_play_model_takeover_gate_audit_export_task(self, result: object, record: BackgroundTaskRecord) -> None:
        payload = result if isinstance(result, dict) else {}
        self.status_var.set(build_play_model_takeover_gate_audit_export_status_text(payload))
        self._log_event("OK", f"\u63a5\u7ba1\u5b88\u95e8\u5ba1\u8ba1\u5bfc\u51fa\u5b8c\u6210 | {record.task_id} | {record.elapsed_seconds or 0:.2f}s")
        if getattr(self, "current_view", "") == "monitor":
            self.open_monitor_center()
        title = "\u63a5\u7ba1\u5b88\u95e8\u5ba1\u8ba1\u62a5\u544a"
        if bool(payload.get("ok")):
            messagebox.showinfo(title, build_play_model_takeover_gate_audit_export_message(payload))
        else:
            messagebox.showwarning(title, build_play_model_takeover_gate_audit_export_message(payload))

    def _finish_draw_specialist_backtest_task(self, result: object, record: BackgroundTaskRecord) -> None:
        payload = result if isinstance(result, dict) else {}
        self.status_var.set(build_draw_specialist_backtest_apply_status_text(payload))
        self._log_event("OK", f"\u5e73\u5c40\u4e13\u9879\u56de\u6d4b\u5b8c\u6210 | {record.task_id} | {record.elapsed_seconds or 0:.2f}s")
        if getattr(self, "current_view", "") == "monitor":
            self.open_monitor_center()
        if bool(payload.get("ok")):
            messagebox.showinfo("\u5e73\u5c40\u4e13\u9879\u56de\u6d4b", build_draw_specialist_backtest_success_message(payload))
        else:
            messagebox.showinfo("\u5e73\u5c40\u4e13\u9879\u56de\u6d4b", f"\u56de\u6d4b\u672a\u5b8c\u6210\n\u539f\u56e0: {payload.get('reason', '-')}")

    def _finish_train_play_models_task(self, result: object, record: BackgroundTaskRecord) -> None:
        payload = result if isinstance(result, dict) else {}
        self.status_var.set(build_train_play_models_apply_status_text(payload))
        self._log_event("OK", f"\u73a9\u6cd5\u6a21\u578b\u8bad\u7ec3\u5b8c\u6210 | {record.task_id} | {record.elapsed_seconds or 0:.2f}s")
        if getattr(self, "current_view", "") == "monitor":
            self.open_monitor_center()
        status_text = build_play_model_training_status_text(get_play_model_training_status())
        messagebox.showinfo("\u73a9\u6cd5\u6a21\u578b\u8bad\u7ec3", build_train_play_models_apply_message(payload, status_text))

    def run_video_review_frame_extraction_task(self, review_id: str | object) -> None:
        resolved_id = str(review_id or "").strip()
        if not resolved_id:
            messagebox.showinfo("\u89c6\u9891\u62bd\u5e27", "\u672a\u627e\u5230\u53ef\u62bd\u5e27\u7684\u89c6\u9891\u590d\u76d8\u8bb0\u5f55\u3002")
            return
        self._submit_process_task(
            key=f"video_review_frames:{resolved_id}",
            label="\u89c6\u9891\u590d\u76d8\u62bd\u5e27",
            start_status=f"\u6b63\u5728\u540e\u53f0\u8fdb\u7a0b\u4e2d\u62bd\u53d6\u89c6\u9891\u590d\u76d8\u5173\u952e\u5e27... {resolved_id}",
            func=extract_video_review_frames_now,
            args=(resolved_id,),
            group="video",
            priority=170,
            metadata={"review_id": resolved_id},
            on_success=self._finish_video_review_frame_extraction_task,
            error_title="\u89c6\u9891\u590d\u76d8\u62bd\u5e27\u5931\u8d25",
        )

    def _finish_video_review_frame_extraction_task(self, result: object, record: BackgroundTaskRecord) -> None:
        payload = result if isinstance(result, dict) else {}
        status = str((payload.get("extraction") if isinstance(payload.get("extraction"), dict) else {}).get("status") or payload.get("reason") or "-")
        frame_count = int(payload.get("frame_count", 0) or 0)
        review_id = str(payload.get("review_id") or (record.metadata or {}).get("review_id") or "-")
        review = payload.get("review") if isinstance(payload.get("review"), dict) else {}
        agent_review = review.get("agent_review") if isinstance(review.get("agent_review"), dict) else {}
        vision_status = str(agent_review.get("vision_model_status") or "-")
        self.status_var.set(f"\u89c6\u9891\u590d\u76d8\u62bd\u5e27: {status} / frames={frame_count} / vision={vision_status}")
        self._log_event("OK", f"\u89c6\u9891\u590d\u76d8\u62bd\u5e27\u5b8c\u6210 | {review_id} | {status} | {record.elapsed_seconds or 0:.2f}s")
        if getattr(self, "current_view", "") == "review":
            self.open_review_center()
        elif getattr(self, "current_view", "") == "monitor":
            self.open_monitor_center()
        title = "\u89c6\u9891\u590d\u76d8\u62bd\u5e27"
        if bool(payload.get("ok")):
            messagebox.showinfo(title, f"\u62bd\u5e27\u5b8c\u6210\n\nreview_id: {review_id}\nframes: {frame_count}\nvision: {vision_status}")
        else:
            messagebox.showwarning(title, f"\u62bd\u5e27\u672a\u5b8c\u6210\n\nreview_id: {review_id}\n\u72b6\u6001: {status}\n\u539f\u56e0: {payload.get('reason', '-')}")

    def _play_model_policy_status(self) -> dict:
        try:
            status = get_play_model_policy_status()
        except Exception as exc:
            self._log_event("ERROR", f"\u73a9\u6cd5\u63a5\u7ba1\u7b56\u7565\u8bfb\u53d6\u5931\u8d25: {exc}")
            return {}
        return status if isinstance(status, dict) else {}

    def open_play_model_policy_detail_window(self) -> None:
        status = self._play_model_policy_status()
        window = tk.Toplevel(self.root)
        window.title("\u73a9\u6cd5\u63a5\u7ba1\u7b56\u7565\u660e\u7ec6")
        window.configure(bg=BG)
        window.geometry("820x560")
        header = tk.Frame(window, bg=BG)
        header.pack(fill=tk.X, padx=16, pady=(14, 8))
        tk.Label(
            header,
            text="\u73a9\u6cd5\u63a5\u7ba1\u7b56\u7565",
            bg=BG,
            fg=TEXT,
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            header,
            text="\u663e\u793a\u603b\u8fdb\u7403\u548c\u6bd4\u5206\u6a21\u578b\u7684\u63a5\u7ba1\u95e8\u69db\u3001\u56de\u6d4b\u8868\u73b0\u548c\u963b\u65ad\u539f\u56e0\u3002",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor=tk.W, pady=(4, 0))
        tk.Button(
            header,
            text="\u5bfc\u51fa\u5b88\u95e8\u5ba1\u8ba1",
            command=self.export_play_model_takeover_gate_audit_report,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(anchor=tk.E, pady=(8, 0))
        frame = tk.Frame(window, bg=PANEL, highlightbackground="#172638", highlightthickness=1)
        frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))
        text = tk.Text(
            frame,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            selectbackground=BLUE,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Consolas", 10),
        )
        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0), pady=12)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 12), pady=12)
        text.insert(tk.END, build_play_model_policy_status_text(status))
        text.configure(state=tk.DISABLED)

    def open_draw_specialist_backtest_window(self) -> None:
        status = get_draw_specialist_backtest_status()
        window = tk.Toplevel(self.root)
        window.title("\u5e73\u5c40\u4e13\u9879\u8bca\u65ad")
        window.configure(bg=BG)
        window.geometry("900x640")
        header = tk.Frame(window, bg=BG)
        header.pack(fill=tk.X, padx=16, pady=(14, 8))
        tk.Label(
            header,
            text="\u5e73\u5c40\u4e13\u9879\u8bca\u65ad",
            bg=BG,
            fg=TEXT,
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(side=tk.LEFT)
        tk.Button(
            header,
            text="\u8fd0\u884c\u56de\u6d4b",
            command=self.run_draw_specialist_backtest_task,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.RIGHT)
        frame = tk.Frame(window, bg=PANEL, highlightbackground="#172638", highlightthickness=1)
        frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))
        text = tk.Text(
            frame,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            selectbackground=BLUE,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Consolas", 10),
        )
        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0), pady=12)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 12), pady=12)
        lines = [build_draw_specialist_backtest_status_text(status)]
        for section_key, section_title in (
            ("score_buckets", "\n\nDraw Score 分层"),
            ("odds_buckets", "\n\n平赔分层"),
            ("handicap_buckets", "\n\n让球线分层"),
            ("expected_goal_buckets", "\n\n预期进球分层"),
            ("market_balance_buckets", "\n\n市场均衡分层"),
        ):
            rows = status.get(section_key, []) if isinstance(status.get(section_key), list) else []
            if rows:
                lines.append(section_title)
                for row in rows[:8]:
                    if isinstance(row, dict):
                        lines.append(
                            f"- {row.get('bucket', '-')}: 样本 {row.get('sample_count', 0)} | 平局率 {row.get('draw_rate_text', '-')} | "
                            f"lift {row.get('lift_text', '-')} | 博平 {row.get('draw_hit_count', 0)}/{row.get('predicted_draw_count', 0)} | "
                            f"召回 {row.get('recall_text', '-')}"
                        )
        missed_rows = status.get("missed_draw_rows", []) if isinstance(status.get("missed_draw_rows"), list) else []
        if missed_rows:
            lines.append("\n\n高分漏判平局")
            for row in missed_rows[:8]:
                if isinstance(row, dict):
                    lines.append(
                        f"- {row.get('match_date', '-')} {row.get('league', '-')} {row.get('home_team', '-')} vs {row.get('away_team', '-')}: "
                        f"pred={row.get('predicted', '-')} draw_score={row.get('draw_score', '-')} draw_prob={row.get('draw_probability', '-')}"
                    )
        false_rows = status.get("false_positive_rows", []) if isinstance(status.get("false_positive_rows"), list) else []
        if false_rows:
            lines.append("\n\n高分误报平局")
            for row in false_rows[:8]:
                if isinstance(row, dict):
                    lines.append(
                        f"- {row.get('match_date', '-')} {row.get('league', '-')} {row.get('home_team', '-')} vs {row.get('away_team', '-')}: "
                        f"score={row.get('score', '-')} draw_score={row.get('draw_score', '-')} draw_prob={row.get('draw_probability', '-')}"
                    )
        text.insert(tk.END, "\n".join(lines))
        text.configure(state=tk.DISABLED)

    def open_background_task_detail_window(self, task_id: str | object) -> None:
        resolved_id = str(task_id or "")
        record = next(
            (item for item in self.background_tasks.snapshot() if str(item.get("task_id") or "") == resolved_id),
            {},
        )
        if not record:
            messagebox.showinfo("\u540e\u53f0\u4efb\u52a1", "\u672a\u627e\u5230\u8be5\u540e\u53f0\u4efb\u52a1\u8bb0\u5f55\u3002")
            return
        window = tk.Toplevel(self.root)
        window.title(f"\u540e\u53f0\u4efb\u52a1\u8be6\u60c5 | {resolved_id}")
        window.configure(bg=BG)
        window.geometry("860x620")
        header = tk.Frame(window, bg=BG)
        header.pack(fill=tk.X, padx=16, pady=(14, 8))
        tk.Label(
            header,
            text=f"{record.get('label', '-')} | {record.get('status', '-')}",
            bg=BG,
            fg=TEXT,
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            header,
            text="\u67e5\u770b\u540e\u53f0\u4efb\u52a1\u7684\u6267\u884c\u8017\u65f6\u3001\u7ed3\u679c\u6458\u8981\u3001metadata \u548c traceback\u3002",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 10),
        ).pack(side=tk.LEFT, anchor=tk.W, pady=(4, 0))
        if str(record.get("status") or "") in {"queued", "running"}:
            tk.Button(
                header,
                text="\u8bf7\u6c42\u53d6\u6d88",
                command=lambda task_id=resolved_id, window=window: self.cancel_background_task(task_id, window),
                bg=RED,
                fg="white",
                activebackground="#d94743",
                activeforeground="white",
                relief=tk.FLAT,
                font=("Microsoft YaHei UI", 10, "bold"),
                padx=14,
                pady=6,
            ).pack(side=tk.RIGHT, padx=(12, 0))
        frame = tk.Frame(window, bg=PANEL, highlightbackground="#172638", highlightthickness=1)
        frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))
        text = tk.Text(
            frame,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            selectbackground=BLUE,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Consolas", 10),
        )
        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0), pady=12)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 12), pady=12)
        text.insert(tk.END, "\n".join(build_background_task_detail_lines(record)))
        text.configure(state=tk.DISABLED)

    def cancel_background_task(self, task_id: str | object, window: tk.Toplevel | None = None) -> None:
        resolved_id = str(task_id or "")
        record = self.background_tasks.cancel_task(resolved_id)
        if record is None:
            messagebox.showinfo("\u540e\u53f0\u4efb\u52a1", "\u672a\u627e\u5230\u8be5\u540e\u53f0\u4efb\u52a1\u8bb0\u5f55\u3002")
            return
        status = str(record.get("status") or "")
        if status == "cancelled":
            message = f"\u4efb\u52a1\u5df2\u53d6\u6d88: {record.get('label', '-')}"
            self._log_event("WARN", f"{message} / {resolved_id}")
            messagebox.showinfo("\u540e\u53f0\u4efb\u52a1", message)
        elif bool((record.get("metadata") if isinstance(record.get("metadata"), dict) else {}).get("cancel_requested")):
            message = "\u4efb\u52a1\u5df2\u5f00\u59cb\u8fd0\u884c\uff0c\u5df2\u8bb0\u5f55\u53d6\u6d88\u8bf7\u6c42\uff0c\u4e0d\u4f1a\u5f3a\u5236\u7ec8\u6b62\u5f53\u524d\u8fdb\u7a0b\u3002"
            self._log_event("WARN", f"\u540e\u53f0\u4efb\u52a1\u53d6\u6d88\u8bf7\u6c42: {resolved_id}")
            messagebox.showwarning("\u540e\u53f0\u4efb\u52a1", message)
        else:
            messagebox.showinfo("\u540e\u53f0\u4efb\u52a1", "\u8be5\u4efb\u52a1\u5df2\u7ed3\u675f\uff0c\u65e0\u9700\u53d6\u6d88\u3002")
        if window is not None and window.winfo_exists():
            window.destroy()
        if getattr(self, "current_view", "") == "monitor":
            self.open_monitor_center()

    def _release_recovery_alerts(self) -> dict[str, object]:
        return build_strategy_release_recovery_alerts(self._pending_snapshot_rows())

    def _refresh_current_view_after_release_state_change(self) -> None:
        self._refresh_metrics()
        view = getattr(self, "current_view", "")
        if view == "home":
            self.show_home_overview()
        elif view == "monitor":
            self.open_monitor_center()
        elif view == "review":
            self.open_review_center()
        elif view == "snapshot":
            self.open_snapshot_center()
        elif view == "strategy":
            self.open_strategy_library()
        elif view == "accuracy":
            self.open_accuracy_diagnostics()
        elif view == "recovery_runs":
            self.open_recovery_run_center()
        elif view == "data":
            self.open_data_center()
        elif view == "match_analysis":
            if self._widget_alive("match_list"):
                self._refresh_matches()
            if self._widget_alive("risk_chart"):
                self._draw_risk_chart()
            if self._widget_alive("conf_chart"):
                self._draw_confidence_chart()

    def open_monitor_center(self) -> None:
        self.current_nav_index = 2
        self.current_view = "monitor"
        self._refresh_nav_highlight()
        release_alerts = self._release_recovery_alerts()
        release_alert_count = int(release_alerts.get("count", 0) or 0)
        recovery_summary = self._recovery_run_summary()
        recovery_quality_alerts = self._recovery_quality_alerts()
        recovery_trend = build_strategy_release_quality_trend(self._recovery_run_records(limit=80))
        recovery_trend_alerts = build_strategy_release_quality_trend_alerts(recovery_trend)
        policy_history = get_strategy_admission_policy_history(limit=20)
        policy_effect_review = build_strategy_policy_effect_review(
            policy_history,
            list(reversed(get_recent_settlements(limit=200))),
        )
        trend_tuning_effect = build_strategy_trend_tuning_effect_review(policy_effect_review)
        rollback_effect = build_strategy_policy_rollback_effect_review(policy_effect_review)
        freeze_override = build_strategy_policy_freeze_override_status(policy_history, rollback_effect)
        policy_tuning_guard = build_strategy_policy_tuning_guard(
            policy_effect_review.get("stability_monitor", {}) if isinstance(policy_effect_review.get("stability_monitor"), dict) else {},
            source="monitor",
            trend_tuning_effect_review=trend_tuning_effect,
            rollback_effect_review=rollback_effect,
            freeze_override_status=freeze_override,
        )
        shell = self._page_shell(
            "\u76d1\u63a7\u4e2d\u5fc3",
            "\u8fd0\u884c\u65e5\u5fd7\u3001\u5206\u6790\u8017\u65f6\u3001\u6570\u636e\u6e90\u548c\u98ce\u9669\u72b6\u6001",
        )
        header = tk.Frame(shell, bg=BG)
        header.pack(fill=tk.X)
        tk.Button(
            header,
            text="\u73a9\u6cd5\u8bad\u7ec3(\u8fdb\u7a0b)",
            command=self.train_play_models_task,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        tk.Button(
            header,
            text="\u73a9\u6cd5\u56de\u6d4b(\u8fdb\u7a0b)",
            command=self.run_play_model_backtest_task,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        tk.Button(
            header,
            text="\u5e73\u5c40\u8bca\u65ad",
            command=self.open_draw_specialist_backtest_window,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        tk.Button(
            header,
            text="\u63a5\u7ba1\u7b56\u7565",
            command=self.open_play_model_policy_detail_window,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        tk.Button(
            header,
            text="\u5bfc\u51fa\u63a5\u7ba1\u5ba1\u8ba1",
            command=self.export_play_model_takeover_gate_audit_report,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        tk.Button(
            header,
            text="\u9ad8\u51c6\u56de\u6d4b(\u8fdb\u7a0b)",
            command=self.run_high_accuracy_strategy_backtest_task,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        tk.Button(
            header,
            text="\u56de\u6536\u8fd0\u884c\u8bb0\u5f55",
            command=self.open_recovery_run_center,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        tk.Button(
            header,
            text="\u5237\u65b0\u8d5b\u4e8b",
            command=self.refresh,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT)
        tk.Button(
            header,
            text="\u91cd\u8bd5\u5728\u7ebf\u6e90",
            command=lambda: self.refresh(force_live=True),
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        tk.Button(
            header,
            text="\u8bfb\u53d6\u7f13\u5b58\u6c60",
            command=lambda: self.refresh(cache_only=True),
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        risk_counts = self._risk_counts()
        load_report = self.last_load_diagnostics if isinstance(self.last_load_diagnostics, dict) else {}
        background_task_history = self.background_tasks.snapshot()
        background_task_snapshot = background_task_history[:10]
        background_task_summary = build_background_task_summary(background_task_snapshot)
        background_queue_state = self.background_tasks.queue_state()
        background_stability = build_background_task_stability_summary(background_task_history)
        play_policy_status = self._play_model_policy_status()
        draw_specialist_status = get_draw_specialist_backtest_status()
        load_failure_count = int(load_report.get("failure_count", 0) or 0)
        snapshot_failure_count = int(load_report.get("snapshot_failure_count", 0) or 0)
        fetched_count = int(load_report.get("fetched_count", len(self.rows)) or 0)
        source_health = _source_health_summary(load_report)
        cache_status = _cache_status_summary(load_report)
        cache_tone = _cache_status_tone(load_report)
        metrics = [
            ("\u6700\u8fd1\u8017\u65f6", f"{self.last_refresh_seconds:.2f}s" if self.last_refresh_seconds is not None else "-"),
            ("\u6570\u636e\u6e90", self.data_source, "#7aa2ff"),
            ("\u6e90\u5065\u5eb7", source_health, GREEN if "\u6b63\u5e38" in source_health or "\u5408\u5e76" in source_health else YELLOW),
            ("\u7f13\u5b58\u56de\u9000", cache_status, self._tone_color(cache_tone)),
            ("\u52a0\u8f7d\u6210\u529f", f"{len(self.rows)}/{fetched_count}", GREEN if load_failure_count == 0 else YELLOW),
            ("\u52a0\u8f7d\u5931\u8d25", str(load_failure_count), RED if load_failure_count else GREEN),
            ("\u5feb\u7167\u5931\u8d25", str(snapshot_failure_count), YELLOW if snapshot_failure_count else GREEN),
            ("\u9884\u8b66", str(risk_counts.get("high", 0)), RED),
            ("\u653e\u884c\u5f85\u56de\u6536", str(release_alert_count), RED if release_alert_count else GREEN),
            ("\u6700\u8fd1\u56de\u6536", str(recovery_summary.get("latest_status_label") or "-"), GREEN if recovery_summary.get("latest_status") == "success" else RED if recovery_summary.get("latest_status") == "failed" else YELLOW),
            ("\u56de\u6536\u65b0\u7ed3\u7b97", str(recovery_summary.get("latest_new_settled", 0)), "#7aa2ff"),
            ("\u56de\u6536\u544a\u8b66", str(len(recovery_quality_alerts)), RED if any(item.get("severity") == "high" for item in recovery_quality_alerts) else YELLOW if recovery_quality_alerts else GREEN),
            ("\u653e\u884c\u8d8b\u52bf", str(len(recovery_trend_alerts)), RED if any(item.get("severity") == "high" for item in recovery_trend_alerts) else YELLOW if recovery_trend_alerts else GREEN),
            ("\u95e8\u63a7\u751f\u6548", str(trend_tuning_effect.get("label") or "-"), self._tone_color(str(trend_tuning_effect.get("tone") or "neutral"))),
            ("\u56de\u6eda\u4fee\u590d", str(rollback_effect.get("label") or "-"), self._tone_color(str(rollback_effect.get("tone") or "neutral"))),
            ("\u51bb\u7ed3\u89e3\u9664", str(freeze_override.get("label") or "-"), self._tone_color(str(freeze_override.get("tone") or "neutral"))),
            ("\u8c03\u53c2\u95e8\u63a7", str(policy_tuning_guard.get("label") or "-"), self._tone_color(str(policy_tuning_guard.get("tone") or "neutral"))),
            ("\u540e\u53f0\u4efb\u52a1", str(background_task_summary.get("running", 0)), YELLOW if int(background_task_summary.get("running", 0) or 0) else GREEN),
            ("\u591a\u8fdb\u7a0b", str(background_task_summary.get("process_running", 0)), "#7aa2ff"),
            (
                "\u540e\u53f0\u5065\u5eb7",
                {"normal": "\u6b63\u5e38", "watch": "\u89c2\u5bdf", "abnormal": "\u5f02\u5e38"}.get(str(background_stability.get("health") or ""), "-"),
                self._tone_color(str(background_stability.get("tone") or "neutral")),
            ),
            (
                "\u961f\u5217\u8d44\u6e90",
                f"T {background_queue_state.get('thread_running', 0)}/{background_queue_state.get('thread_limit', 0)} | P {background_queue_state.get('process_running', 0)}/{background_queue_state.get('process_limit', 0)}",
                "#7aa2ff",
            ),
            (
                "\u5e73\u5c40\u8bca\u65ad",
                str((draw_specialist_status.get("summary") if isinstance(draw_specialist_status.get("summary"), dict) else {}).get("precision_text") or "-"),
                GREEN if bool(draw_specialist_status.get("ok")) else YELLOW,
            ),
        ]
        for label, value, color in metrics:
            self._detail_metric(top, label, value, color)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="Agent \u72b6\u6001", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        supervisor_statuses = [
            str((row.prediction.get("supervisor") or {}).get("status") or "")
            for row in self.rows
            if isinstance(row.prediction.get("supervisor"), dict)
        ]
        supervisor_alerts = sum(1 for status in supervisor_statuses if status in {"alert", "blocked"})
        supervisor_watch = sum(1 for status in supervisor_statuses if status == "watch")
        agent_rows = [
            ("Supervisor", f"alert/block {supervisor_alerts} / watch {supervisor_watch}" if supervisor_statuses else "\u7b49\u5f85\u7f16\u6392"),
            ("DataHunter", f"\u5df2\u63a5\u5165 {len(self.rows)}/{fetched_count} \u573a" if self.rows else "\u7b49\u5f85\u6570\u636e"),
            ("MarketEntropy", f"\u9ad8\u98ce\u9669 {risk_counts.get('high', 0)} / \u4e2d\u98ce\u9669 {risk_counts.get('medium', 0)}"),
            ("Simulation", f"\u5df2\u63a8\u6f14 {len(self.rows)} \u573a"),
            ("RiskGuardian", "\u6b63\u5e38" if risk_counts.get("high", 0) == 0 else "\u89e6\u53d1\u9884\u8b66"),
            ("ReviewLoop", f"\u653e\u884c\u5f85\u56de\u6536 {release_alert_count} \u573a" if release_alert_count else "\u65e0\u5f85\u56de\u6536\u6b63\u5f0f\u653e\u884c"),
            ("StrategyComposer", f"\u62a5\u544a {len(list_dashboard_report_files(REPORT_DIR, limit=10000)) if REPORT_DIR.exists() else 0} \u4efd"),
        ]
        for label, value in agent_rows:
            self._kv_row(left, label, value)

        source_rows = _source_health_rows(load_report)
        if source_rows:
            tk.Label(left, text="\u6570\u636e\u6e90\u5065\u5eb7", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
            for row in source_rows:
                tone = str(row.get("tone") or "neutral")
                title = f"{row.get('source', '-')} / {row.get('status', '-')}"
                body = str(row.get("detail") or "-")
                if tone == "good":
                    self._kv_row(left, title, body)
                else:
                    self._alert_card(left, title, body, tone=tone)

        tk.Label(left, text="\u7f13\u5b58\u56de\u9000", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
        for label, value in _cache_status_rows(load_report):
            self._kv_row(left, label, value)

        if self.load_failures:
            tk.Label(left, text="\u52a0\u8f7d\u5f02\u5e38", bg=PANEL, fg=YELLOW, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
            stage_labels = {"predict": "\u9884\u6d4b", "snapshot": "\u5feb\u7167"}
            for failure in self.load_failures[:3]:
                if not isinstance(failure, dict):
                    continue
                stage = str(failure.get("stage") or "-")
                title = f"{stage_labels.get(stage, stage)}\u5931\u8d25"
                body = (
                    f"{failure.get('league', '-')}: {failure.get('home', '-')} vs {failure.get('away', '-')}\n"
                    f"{failure.get('error', '-')}"
                )
                self._alert_card(left, title, body, tone="bad" if stage == "predict" else "warning")

        if release_alert_count:
            tk.Label(left, text="\u653e\u884c\u56de\u6536\u63d0\u9192", bg=PANEL, fg=RED, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
            rows = release_alerts.get("rows", []) if isinstance(release_alerts.get("rows"), list) else []
            for row in rows:
                if isinstance(row, dict):
                    self._release_recovery_action_card(left, str(row.get("title") or "-"), str(row.get("body") or "-"))

        if recovery_quality_alerts:
            tk.Label(left, text="\u56de\u6536\u8d28\u91cf\u544a\u8b66", bg=PANEL, fg=YELLOW, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
            for alert in recovery_quality_alerts[:3]:
                self._alert_card(left, str(alert.get("title") or "-"), str(alert.get("body") or "-"), tone=str(alert.get("tone") or "warning"))

        if recovery_trend_alerts:
            tk.Label(left, text="\u653e\u884c\u8d8b\u52bf\u544a\u8b66", bg=PANEL, fg=YELLOW, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
            for alert in recovery_trend_alerts[:3]:
                self._alert_card(left, str(alert.get("title") or "-"), str(alert.get("body") or "-"), tone=str(alert.get("tone") or "warning"))

        tuning_decision = str(policy_tuning_guard.get("decision") or "")
        if str(trend_tuning_effect.get("status") or "") == "negative" or tuning_decision in {"block", "freeze"}:
            section_title = "\u8c03\u53c2\u51bb\u7ed3" if tuning_decision == "freeze" else "\u95e8\u63a7\u8d1f\u53cd\u9988"
            tk.Label(left, text=section_title, bg=PANEL, fg=RED, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
            self._alert_card(
                left,
                str(policy_tuning_guard.get("label") or trend_tuning_effect.get("label") or "-"),
                str(policy_tuning_guard.get("body") or trend_tuning_effect.get("summary_text") or "-"),
                tone=str(policy_tuning_guard.get("tone") or trend_tuning_effect.get("tone") or "bad"),
            )
            self._strategy_row(
                left,
                "\u67e5\u770b\u751f\u6548\u660e\u7ec6",
                "\u590d\u6838\u5f53\u524d\u8d1f\u5411\u7248\u672c\u3001\u56de\u6eda\u4fee\u590d\u72b6\u6001\u548c\u653e\u884c\u9519\u8bef\u6837\u672c\u3002",
                command=lambda review=policy_effect_review: self.open_policy_effect_detail_window(review),
            )

        if str(rollback_effect.get("status") or "") in {"effective", "negative", "watch"}:
            tk.Label(left, text="\u56de\u6eda\u4fee\u590d\u8ddf\u8e2a", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
            self._alert_card(
                left,
                str(rollback_effect.get("label") or "-"),
                (
                    f"{rollback_effect.get('summary_text', '-')}\n"
                    f"{rollback_effect.get('recommendation_text', '-')}"
                ),
                tone=str(rollback_effect.get("tone") or "neutral"),
            )
            self._strategy_row(
                left,
                "\u67e5\u770b\u56de\u6eda\u7248\u672c\u6837\u672c",
                "\u5bf9\u6bd4\u56de\u6eda\u540e\u7248\u672c\u548c\u88ab\u56de\u6eda\u7248\u672c\u7684\u653e\u884c\u547d\u4e2d\u4e0e Replay \u51c0\u503c\u3002",
                command=lambda review=policy_effect_review: self.open_policy_effect_detail_window(review),
            )
            if str(freeze_override.get("status") or "") == "frozen":
                self._strategy_row(
                    left,
                    "\u4eba\u5de5\u89e3\u9664\u8c03\u53c2\u51bb\u7ed3",
                    str(freeze_override.get("summary_text") or "-"),
                    command=lambda rollback=rollback_effect, override=freeze_override: self.apply_strategy_policy_freeze_override(rollback, override),
                )

        tk.Label(right, text="\u73a9\u6cd5\u63a5\u7ba1\u7b56\u7565", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        for row in build_play_model_policy_decision_rows(play_policy_status):
            self._alert_card(
                right,
                str(row.get("title") or "-"),
                str(row.get("body") or "-"),
                tone=str(row.get("tone") or "neutral"),
            )
        self._strategy_row(
            right,
            "\u63a5\u7ba1\u7b56\u7565\u660e\u7ec6",
            "\u67e5\u770b\u5b8c\u6574\u95e8\u69db\u3001\u6821\u51c6\u6837\u672c\u548c\u63a5\u7ba1\u539f\u56e0",
            command=self.open_play_model_policy_detail_window,
        )
        self._strategy_row(
            right,
            "\u5bfc\u51fa\u63a5\u7ba1\u5b88\u95e8\u5ba1\u8ba1",
            "\u751f\u6210 Markdown/CSV \u62a5\u544a\uff0c\u7528\u4e8e\u590d\u6838\u63a5\u7ba1 gate \u8f6c\u79fb\u3001\u6837\u672c\u6570\u548c\u6a21\u578b\u589e\u76ca\u3002",
            command=self.export_play_model_takeover_gate_audit_report,
        )

        tk.Label(right, text="\u5e73\u5c40\u4e13\u9879\u8bca\u65ad", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        for row in build_draw_specialist_backtest_card_rows(draw_specialist_status):
            self._alert_card(
                right,
                str(row.get("title") or "-"),
                f"{row.get('body', '-')}\n\u70b9\u51fb\u67e5\u770b\u5e73\u5c40\u5206\u5c42\u8be6\u60c5",
                tone=str(row.get("tone") or "neutral"),
            )
        self._strategy_row(
            right,
            "\u5e73\u5c40\u8bca\u65ad\u660e\u7ec6",
            "\u67e5\u770b\u5e73\u5c40\u7cbe\u786e\u7387\u3001\u53ec\u56de\u7387\u3001\u6f0f\u5224/\u8bef\u62a5\u548c\u5206\u5c42\u8868\u73b0",
            command=self.open_draw_specialist_backtest_window,
        )

        tk.Label(right, text="\u540e\u53f0\u4efb\u52a1", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        tk.Label(right, text="\u7a33\u5b9a\u6027\u9762\u677f", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        for row in build_background_task_stability_cards(background_stability):
            self._alert_card(
                right,
                str(row.get("title") or "-"),
                str(row.get("body") or "-"),
                tone=str(row.get("tone") or "neutral"),
            )

        tk.Label(right, text="\u961f\u5217\u5206\u7ec4", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        group_rows = build_background_task_group_rows(background_queue_state)
        if group_rows:
            for row in group_rows:
                self._alert_card(
                    right,
                    str(row.get("title") or "-"),
                    str(row.get("body") or "-"),
                    tone=str(row.get("tone") or "neutral"),
                )
        else:
            self._kv_row(right, "\u961f\u5217\u5206\u7ec4", "\u6682\u65e0\u540e\u53f0\u4efb\u52a1\u5206\u7ec4")

        tk.Label(right, text="\u6700\u8fd1\u4efb\u52a1", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        task_rows = build_background_task_rows(background_task_snapshot, limit=6)
        if task_rows:
            for row in task_rows:
                task_id = str(row.get("task_id") or "")
                self._strategy_row(
                    right,
                    str(row.get("title") or "-"),
                    f"{row.get('body', '-')}\n\u70b9\u51fb\u67e5\u770b\u4efb\u52a1\u8be6\u60c5",
                    command=lambda task_id=task_id: self.open_background_task_detail_window(task_id),
                )
        else:
            self._kv_row(right, "\u4efb\u52a1\u961f\u5217", "\u6682\u65e0\u540e\u53f0\u4efb\u52a1")

        tk.Label(right, text="\u8fd0\u884c\u65e5\u5fd7", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        logbox = tk.Listbox(
            right,
            bg=PANEL,
            fg=TEXT,
            selectbackground=BLUE,
            selectforeground="white",
            relief=tk.FLAT,
            font=("Consolas", 10),
            activestyle="none",
        )
        logbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        if not self.event_log:
            logbox.insert(tk.END, "no events")
        else:
            for stamp, level, message in self.event_log:
                logbox.insert(tk.END, f"{stamp} [{level}] {message}")

    def open_review_center(self) -> None:
        self.current_view = "review"
        settlements = list(reversed(get_recent_settlements(limit=200)))
        summary = self._settlement_summary(settlements)
        trend = self._settlement_trend_summary(settlements)
        allowlist_summary = build_strategy_allowlist_settlement_summary(settlements)
        allowlist_tuning = build_strategy_allowlist_tuning_recommendation(settlements)
        release_loop = self._strategy_release_recovery_loop(settlements)
        recovery_summary = self._recovery_run_summary()
        lookback_days = self._recovery_lookback_days()
        snapshot_audit = self._result_recovery_snapshot_audit(lookback_days=lookback_days)
        video_memory_health = self._video_review_fewshot_memory_health_context()
        statsbomb_review_quality = build_statsbomb_review_training_quality_summary(get_statsbomb_review_training_samples())
        video_source_coverage = build_video_review_source_coverage_summary(
            settlements,
            statsbomb_samples=get_statsbomb_review_training_samples(),
            video_memory=get_video_review_fewshot_memory(),
        )
        evidence_gap_feedback_rows = build_video_review_evidence_gap_feedback_rows(
            _load_video_review_evidence_gap_feedback_log(),
            limit=2,
        )
        evidence_gap_batch_state = _load_video_review_evidence_gap_batch_state()
        evidence_gap_batch_status = build_video_review_evidence_gap_batch_status(evidence_gap_batch_state)
        statsbomb_repair_records = _load_statsbomb_review_training_action_feedback_log()
        statsbomb_review_center_summary = build_statsbomb_review_training_center_summary(
            statsbomb_review_quality,
            statsbomb_repair_records,
        )
        video_review_center_summary = build_video_review_center_summary(
            video_memory_health,
            video_source_coverage,
        )

        shell = self._page_shell(
            "\u590d\u76d8\u4e2d\u5fc3",
            "\u56de\u6536\u5b8c\u573a\u8d5b\u679c\uff0c\u68c0\u67e5\u547d\u4e2d\u7387\u3001\u73a9\u6cd5\u504f\u5dee\u548c\u9ad8\u7f6e\u4fe1\u5931\u8bef",
        )
        header = tk.Frame(shell, bg=BG)
        header.pack(fill=tk.X)
        tk.Button(
            header,
            text="\u8fd0\u884c\u8bb0\u5f55",
            command=self.open_recovery_run_center,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        tk.Button(
            header,
            text="\u653e\u884c\u95ed\u73af",
            command=self.open_strategy_release_recovery_loop_window,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        recover_button = tk.Button(
            header,
            text="\u56de\u6536\u8d5b\u679c",
            command=self.run_result_recovery,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        )
        self._register_result_recovery_button(recover_button)
        recover_button.pack(side=tk.RIGHT)
        tk.Button(
            header,
            text="\u8d5b\u524d\u5feb\u7167",
            command=self.open_snapshot_center,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        tk.Button(
            header,
            text="\u51c6\u786e\u7387\u8bca\u65ad",
            command=self.open_accuracy_diagnostics,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))

        self._lookback_selector(shell)

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        for label, value, color in [
            ("\u5df2\u7ed3\u7b97", str(summary["total"]), TEXT),
            ("1X2 \u547d\u4e2d", summary["one_x_two"], GREEN),
            ("\u8ba9\u7403\u547d\u4e2d", summary["handicap"], "#7aa2ff"),
            ("\u5927\u5c0f\u7403\u547d\u4e2d", summary["ou"], YELLOW),
            ("\u8fd1\u671f\u56de\u6536\u6210\u529f\u7387", str(recovery_summary.get("recent_success_rate_text") or "-"), GREEN if float(recovery_summary.get("recent_success_rate") or 0) >= 0.8 else YELLOW),
            ("\u5e73\u5747\u56de\u6536\u8017\u65f6", str(recovery_summary.get("avg_elapsed_text") or "-"), "#7aa2ff"),
        ]:
            self._detail_metric(top, label, value, color)

        audit_frame = tk.Frame(shell, bg=BG)
        audit_frame.pack(fill=tk.X, pady=(0, 16))
        for label, value, color in self._snapshot_audit_metrics(snapshot_audit):
            self._detail_metric(audit_frame, label, value, color)

        trend_frame = tk.Frame(shell, bg=BG)
        trend_frame.pack(fill=tk.X, pady=(0, 16))
        for label, value, color in [
            ("\u4e3b\u8981\u504f\u5dee", trend["top_bias"], YELLOW if trend["top_bias"] != "-" else TEXT),
            ("\u6700\u4e0d\u7a33\u5b9a\u73a9\u6cd5", trend["weakest_play"], RED if trend["weakest_play"] != "-" else TEXT),
            ("\u9ad8\u7f6e\u4fe1\u5931\u8bef", str(trend["high_conf_misses"]), RED if trend["high_conf_misses"] else GREEN),
            ("\u8c03\u6743\u91cd\u70b9", trend["priority"], "#7aa2ff"),
        ]:
            self._detail_metric(trend_frame, label, str(value), color)

        allowlist_frame = tk.Frame(shell, bg=BG)
        allowlist_frame.pack(fill=tk.X, pady=(0, 16))
        allowlist_hit_rate = str(allowlist_summary.get("hit_rate_text") or "-")
        allowlist_known = int(allowlist_summary.get("known_count", 0) or 0)
        allowlist_hit_color = TEXT if not allowlist_known else GREEN if float(allowlist_summary.get("hit_rate", 0) or 0) >= 0.6 else YELLOW
        for label, value, color in [
            ("\u653e\u884c\u5df2\u7ed3\u7b97", str(allowlist_summary.get("settled_count", 0)), TEXT),
            ("\u653e\u884c 1X2", allowlist_hit_rate, allowlist_hit_color),
            ("\u653e\u884c\u9ad8\u51c6", str(allowlist_summary.get("high_strategy_summary") or "-"), "#7aa2ff"),
            ("\u653e\u884c\u504f\u5dee", str(allowlist_summary.get("top_failure") or "-"), RED if allowlist_summary.get("top_failure") != "-" else TEXT),
            ("\u8c03\u53c2\u5efa\u8bae", str(allowlist_tuning.get("label") or "-"), self._tone_color(str(allowlist_tuning.get("tone") or "neutral"))),
        ]:
            self._detail_metric(allowlist_frame, label, str(value), color)

        release_loop_frame = tk.Frame(shell, bg=BG)
        release_loop_frame.pack(fill=tk.X, pady=(0, 16))
        for label, value, color in [
            ("\u653e\u884c\u95ed\u73af", str(release_loop.get("health_text") or "-"), self._tone_color(str(release_loop.get("health") or "neutral"))),
            ("\u653e\u884c\u603b\u6570", str(release_loop.get("total_release_count", 0)), TEXT),
            ("\u5df2\u56de\u6536", str(release_loop.get("settled_count", 0)), GREEN),
            ("\u5f85\u56de\u6536", str(release_loop.get("pending_count", 0)), YELLOW if int(release_loop.get("pending_count", 0) or 0) else GREEN),
            ("\u7f3a\u5feb\u7167", str(release_loop.get("missing_snapshot_count", 0)), RED if int(release_loop.get("missing_snapshot_count", 0) or 0) else GREEN),
            ("\u8d85\u671f", str(release_loop.get("stale_pending_count", 0)), RED if int(release_loop.get("stale_pending_count", 0) or 0) else GREEN),
        ]:
            self._detail_metric(release_loop_frame, label, str(value), color)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u6700\u8fd1\u590d\u76d8", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        table_wrap = tk.Frame(left, bg=PANEL)
        table_wrap.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        self._configure_dark_tree_style("Review.Treeview", rowheight=26)
        columns = ("date", "league", "match", "score", "pick", "result", "hit", "confidence")
        review_tree = ttk.Treeview(table_wrap, columns=columns, show="headings", style="Review.Treeview", height=16)
        headings = {
            "date": "\u65e5\u671f",
            "league": "\u8054\u8d5b",
            "match": "\u8d5b\u4e8b",
            "score": "\u6bd4\u5206",
            "pick": "\u9884\u6d4b",
            "result": "\u8d5b\u679c",
            "hit": "1X2",
            "confidence": "\u7f6e\u4fe1",
        }
        widths = {"date": 86, "league": 78, "match": 220, "score": 58, "pick": 62, "result": 62, "hit": 62, "confidence": 64}
        for key in columns:
            review_tree.heading(key, text=headings[key])
            review_tree.column(key, width=widths[key], minwidth=50, stretch=key == "match", anchor=tk.W)
        review_scrollbar = tk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=review_tree.yview)
        review_tree.configure(yscrollcommand=review_scrollbar.set)
        review_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        review_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        for index, item in enumerate(settlements[:80]):
            review_tree.insert("", tk.END, iid=str(index), values=self._settlement_table_values(item))
        if not settlements:
            review_tree.insert("", tk.END, iid="empty", values=("-", "-", "\u6682\u65e0\u590d\u76d8\u7ed3\u7b97\u8bb0\u5f55", "-", "-", "-", "-", "-"))
        review_actions = tk.Frame(left, bg=PANEL)
        review_actions.pack(fill=tk.X, padx=18, pady=(0, 12))
        tk.Button(
            review_actions,
            text="\u5bfc\u5165\u6240\u9009\u89c6\u9891\u590d\u76d8",
            command=lambda: self.import_video_review_for_selection(review_tree, settlements),
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT)
        tk.Button(
            review_actions,
            text="\u7ed1\u5b9a FIFA+ \u56de\u653e\u94fe\u63a5",
            command=lambda: self.import_video_review_reference_for_selection(review_tree, settlements),
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(
            review_actions,
            text="\u6807\u6ce8\u89c6\u9891\u4e8b\u4ef6",
            command=lambda: self.annotate_video_review_for_selection(review_tree, settlements),
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(
            review_actions,
            text="\u5bfc\u51fa\u89c6\u9891\u590d\u76d8\u6837\u672c",
            command=self.export_video_review_fewshot_samples,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(
            review_actions,
            text="\u751f\u6210\u4e8b\u4ef6\u4ee3\u7406\u590d\u76d8\u6837\u672c",
            command=self.export_statsbomb_event_proxy_review_samples,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(
            review_actions,
            text="\u9884\u89c8\u6837\u672c\u5408\u5e76",
            command=self.preview_video_review_fewshot_merge_bundle,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(
            review_actions,
            text="\u5e94\u7528\u89c6\u9891\u8bb0\u5fc6",
            command=self.apply_video_review_fewshot_merge_bundle,
            bg=PANEL_2,
            fg="#fecaca",
            activebackground="#451a1a",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT, padx=(10, 0))
        review_memory_actions = tk.Frame(left, bg=PANEL)
        review_memory_actions.pack(fill=tk.X, padx=18, pady=(0, 12))
        tk.Button(
            review_memory_actions,
            text="\u5ba1\u8ba1\u89c6\u9891\u8bb0\u5fc6",
            command=self.export_video_review_fewshot_memory_audit,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT)
        tk.Button(
            review_memory_actions,
            text="事件代理中心",
            command=self.open_statsbomb_review_training_center_window,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(
            review_memory_actions,
            text="导出缺口批次计划",
            command=self.export_video_review_evidence_gap_batch_plan,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(
            review_memory_actions,
            text="证据缺口中心",
            command=self.open_video_review_evidence_gap_center_window,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(
            review_memory_actions,
            text="\u56de\u6eda\u89c6\u9891\u8bb0\u5fc6",
            command=self.rollback_video_review_fewshot_memory,
            bg=PANEL_2,
            fg="#fecaca",
            activebackground="#451a1a",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT, padx=(10, 0))

        self._strategy_section_title(right, "AI视频复盘")
        self._strategy_row(
            right,
            str(video_review_center_summary.get("title") or "-"),
            str(video_review_center_summary.get("body") or "-"),
            command=self.open_ai_video_review_center_window,
        )
        self._strategy_row(
            right,
            "打开AI视频复盘专项中心",
            "视频记忆健康、视频来源覆盖、补标注/补样建议和视频降级边界集中到专项窗口查看，避免复盘中心继续堆叠过多内容。",
            command=self.open_ai_video_review_center_window,
        )
        self._strategy_section_title(right, "复盘证据缺口行动")
        self._strategy_row(
            right,
            f"缺口批次执行 | {evidence_gap_batch_status.get('status', '-')}",
            (
                f"{evidence_gap_batch_status.get('summary_text', '-')}\n"
                f"完成率: {float(evidence_gap_batch_status.get('completion_rate', 0) or 0):.0%} | "
                f"当前缺证据 {video_source_coverage.get('no_review_evidence_count', 0)} 场"
            ),
            command=self.open_video_review_evidence_gap_center_window,
        )
        self._strategy_row(
            right,
            "打开证据缺口专项中心",
            "批次筛选、P0/P1 优先处理、绑定回放、导入视频、生成事件代理样本和处理报告导出都集中在专项窗口。",
            command=self.open_video_review_evidence_gap_center_window,
        )
        self._strategy_section_title(right, "复盘证据处理记录")
        if evidence_gap_feedback_rows:
            for row in evidence_gap_feedback_rows:
                self._strategy_row(
                    right,
                    str(row.get("title") or "-"),
                    str(row.get("body") or "-"),
                )
        else:
            self._strategy_row(
                right,
                "暂无处理记录",
                "绑定外部回放链接后，会记录 missing_evidence -> external_reference 的变化。",
            )
        self._strategy_section_title(right, "事件代理复盘")
        self._strategy_row(
            right,
            str(statsbomb_review_center_summary.get("title") or "-"),
            str(statsbomb_review_center_summary.get("body") or "-"),
            command=self.open_statsbomb_review_training_center_window,
        )
        self._strategy_row(
            right,
            "打开事件代理专项中心",
            "StatsBomb/Event Proxy 样本质量、可执行修复、修复闭环和质量报告导出都集中在专项窗口。",
            command=self.open_statsbomb_review_training_center_window,
        )

        tk.Label(right, text="\u95ed\u73af\u590d\u76d8", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        detail = tk.Text(
            right,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            height=18,
        )
        detail.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 14))

        def show_settlement_detail(index: int) -> None:
            detail.configure(state=tk.NORMAL)
            detail.delete("1.0", tk.END)
            if not settlements:
                detail.insert(tk.END, "\u6682\u65e0\u5df2\u56de\u6536\u8d5b\u679c\u3002\u7b49\u6bd4\u8d5b\u5b8c\u573a\u540e\uff0c\u70b9\u51fb\u201c\u56de\u6536\u8d5b\u679c\u201d\u751f\u6210\u590d\u76d8\u95ed\u73af\u3002")
            else:
                detail.insert(tk.END, self._settlement_review_text(settlements[index]))
            detail.configure(state=tk.DISABLED)

        if settlements:
            review_tree.selection_set("0")
            review_tree.focus("0")
            show_settlement_detail(0)
        else:
            show_settlement_detail(0)

        def on_settlement_select(_event=None) -> None:
            selection = review_tree.selection()
            if selection and settlements:
                try:
                    show_settlement_detail(int(selection[0]))
                except (TypeError, ValueError):
                    show_settlement_detail(0)

        review_tree.bind("<<TreeviewSelect>>", on_settlement_select)

    def import_video_review_for_selection(self, review_tree: ttk.Treeview, settlements: list[dict]) -> None:
        if not settlements:
            messagebox.showinfo("\u89c6\u9891\u590d\u76d8", "\u5f53\u524d\u6ca1\u6709\u53ef\u7ed1\u5b9a\u7684\u5df2\u7ed3\u7b97\u8d5b\u4e8b\u3002")
            return
        selection = review_tree.selection()
        if not selection:
            messagebox.showinfo("\u89c6\u9891\u590d\u76d8", "\u8bf7\u5148\u9009\u62e9\u4e00\u573a\u590d\u76d8\u8d5b\u4e8b\u3002")
            return
        try:
            settlement = settlements[int(selection[0])]
        except (TypeError, ValueError, IndexError):
            messagebox.showinfo("\u89c6\u9891\u590d\u76d8", "\u9009\u4e2d\u8d5b\u4e8b\u65e0\u6548\uff0c\u8bf7\u91cd\u65b0\u9009\u62e9\u3002")
            return
        self.import_video_review_for_settlement(settlement)

    def import_video_review_for_settlement(self, settlement: dict) -> None:
        path = filedialog.askopenfilename(
            title="\u9009\u62e9\u672c\u5730\u6bd4\u8d5b\u56de\u653e\u6216\u96c6\u9526",
            filetypes=[
                ("\u89c6\u9891\u6587\u4ef6", "*.mp4 *.mkv *.mov *.avi *.webm"),
                ("\u6240\u6709\u6587\u4ef6", "*.*"),
            ],
        )
        if not path:
            return
        result = create_video_review(
            str(settlement.get("match_id") or ""),
            path,
            notes="\u901a\u8fc7 APP \u590d\u76d8\u4e2d\u5fc3\u5bfc\u5165",
            extract_frames=False,
        )
        if not bool(result.get("ok")):
            messagebox.showerror("\u89c6\u9891\u590d\u76d8", f"\u5bfc\u5165\u5931\u8d25: {result.get('reason', '-')}")
            return
        review = result.get("review") if isinstance(result.get("review"), dict) else {}
        frame_plan = review.get("frame_plan") if isinstance(review.get("frame_plan"), list) else []
        try:
            batch_update = _record_video_review_evidence_gap_batch_resolution(
                str(settlement.get("match_id") or ""),
                evidence_kind="local_video",
                source_name="local_file",
                review_id=str(review.get("review_id") or "-"),
            )
        except Exception as exc:
            self._log_event("ERROR", f"复盘证据缺口批次回写失败: {exc}")
        else:
            if int(batch_update.get("updated_count", 0) or 0) > 0:
                self._log_event("OK", f"复盘证据缺口批次已回写: {batch_update.get('updated_count', 0)} 场")
        self.status_var.set(f"\u89c6\u9891\u590d\u76d8\u5df2\u5efa\u7acb: {review.get('review_id', '-')} / \u8ba1\u5212\u62bd\u5e27 {len(frame_plan)}")
        messagebox.showinfo(
            "\u89c6\u9891\u590d\u76d8",
            f"VideoReview Agent \u5df2\u5efa\u7acb\n\nreview_id: {review.get('review_id', '-')}\n\u8ba1\u5212\u62bd\u5e27: {len(frame_plan)}\n\u72b6\u6001: metadata_ready\n\n\u5df2\u63d0\u4ea4\u540e\u53f0\u62bd\u5e27\u4efb\u52a1\u3002",
        )
        self.run_video_review_frame_extraction_task(str(review.get("review_id") or ""))
        self.open_review_center()

    def import_video_review_reference_for_settlement(self, settlement: dict) -> None:
        url = simpledialog.askstring(
            "\u7ed1\u5b9a FIFA+ \u56de\u653e\u94fe\u63a5",
            "\u7c98\u8d34 FIFA+ Archive \u6216\u5176\u4ed6\u5408\u6cd5\u56de\u653e\u94fe\u63a5\uff1a\n\n\u6ce8\uff1a\u672c\u529f\u80fd\u53ea\u4fdd\u5b58\u94fe\u63a5\u4f5c\u4e3a\u590d\u76d8\u8bc1\u636e\uff0c\u4e0d\u81ea\u52a8\u4e0b\u8f7d\u89c6\u9891\u3002",
            parent=self.root,
        )
        if not url:
            return
        source_name = simpledialog.askstring(
            "\u89c6\u9891\u6765\u6e90",
            "\u6765\u6e90\u540d\u79f0\uff08\u9ed8\u8ba4 FIFA+ Archive\uff09\uff1a",
            initialvalue="FIFA+ Archive",
            parent=self.root,
        ) or "FIFA+ Archive"
        result = create_video_review_reference(
            str(settlement.get("match_id") or ""),
            url,
            source_name=source_name,
            notes="\u901a\u8fc7 APP \u590d\u76d8\u4e2d\u5fc3\u7ed1\u5b9a\u5916\u90e8\u56de\u653e\u94fe\u63a5",
        )
        if not bool(result.get("ok")):
            messagebox.showerror("\u89c6\u9891\u590d\u76d8", f"\u7ed1\u5b9a\u5931\u8d25: {result.get('reason', '-')}")
            return
        review = result.get("review") if isinstance(result.get("review"), dict) else {}
        feedback = build_video_review_evidence_gap_feedback(settlement, result, source_name=source_name)
        try:
            _append_video_review_evidence_gap_feedback_log(feedback)
        except Exception as exc:
            self._log_event("ERROR", f"复盘证据缺口处理记录写入失败: {exc}")
        else:
            self._log_event("OK", str(feedback.get("summary_text") or "复盘证据缺口处理已记录"))
        try:
            batch_update = _record_video_review_evidence_gap_batch_resolution(
                str(feedback.get("match_id") or settlement.get("match_id") or ""),
                evidence_kind="external_reference",
                source_name=source_name,
                review_id=str(review.get("review_id") or feedback.get("review_id") or "-"),
            )
        except Exception as exc:
            self._log_event("ERROR", f"复盘证据缺口批次回写失败: {exc}")
        else:
            if int(batch_update.get("updated_count", 0) or 0) > 0:
                self._log_event("OK", f"复盘证据缺口批次已回写: {batch_update.get('updated_count', 0)} 场")
        self.status_var.set(f"\u5916\u90e8\u56de\u653e\u5df2\u7ed1\u5b9a: {review.get('review_id', '-')} / {source_name}")
        messagebox.showinfo(
            "\u89c6\u9891\u590d\u76d8",
            f"\u5df2\u7ed1\u5b9a\u5916\u90e8\u56de\u653e\u94fe\u63a5\n\nreview_id: {review.get('review_id', '-')}\n\u6765\u6e90: {source_name}\n\u72b6\u6001: reference_only\n\n\u540e\u7eed\u53ef\u4f7f\u7528\u201c\u6807\u6ce8\u89c6\u9891\u4e8b\u4ef6\u201d\u6309\u65f6\u95f4\u70b9\u8865\u5145\u590d\u76d8\u8bc1\u636e\u3002",
        )
        self.open_review_center()

    def import_video_review_reference_for_selection(self, review_tree: ttk.Treeview, settlements: list[dict]) -> None:
        if not settlements:
            messagebox.showinfo("\u89c6\u9891\u590d\u76d8", "\u5f53\u524d\u6ca1\u6709\u53ef\u7ed1\u5b9a\u7684\u5df2\u7ed3\u7b97\u8d5b\u4e8b\u3002")
            return
        selection = review_tree.selection()
        if not selection:
            messagebox.showinfo("\u89c6\u9891\u590d\u76d8", "\u8bf7\u5148\u9009\u62e9\u4e00\u573a\u590d\u76d8\u8d5b\u4e8b\u3002")
            return
        try:
            settlement = settlements[int(selection[0])]
        except (TypeError, ValueError, IndexError):
            messagebox.showinfo("\u89c6\u9891\u590d\u76d8", "\u9009\u4e2d\u8d5b\u4e8b\u65e0\u6548\uff0c\u8bf7\u91cd\u65b0\u9009\u62e9\u3002")
            return
        self.import_video_review_reference_for_settlement(settlement)
        return

    def annotate_video_review_for_selection(self, review_tree: ttk.Treeview, settlements: list[dict]) -> None:
        if not settlements:
            messagebox.showinfo("\u89c6\u9891\u6807\u6ce8", "\u5f53\u524d\u6ca1\u6709\u53ef\u6807\u6ce8\u7684\u5df2\u7ed3\u7b97\u8d5b\u4e8b\u3002")
            return
        selection = review_tree.selection()
        if not selection:
            messagebox.showinfo("\u89c6\u9891\u6807\u6ce8", "\u8bf7\u5148\u9009\u62e9\u4e00\u573a\u590d\u76d8\u8d5b\u4e8b\u3002")
            return
        try:
            settlement = settlements[int(selection[0])]
        except (TypeError, ValueError, IndexError):
            messagebox.showinfo("\u89c6\u9891\u6807\u6ce8", "\u9009\u4e2d\u8d5b\u4e8b\u65e0\u6548\uff0c\u8bf7\u91cd\u65b0\u9009\u62e9\u3002")
            return
        video_review = settlement.get("video_review") if isinstance(settlement.get("video_review"), dict) else {}
        if not video_review:
            video_review = get_video_review_for_match(str(settlement.get("match_id") or ""))
        review_id = str(video_review.get("review_id") or "").strip()
        if not review_id:
            messagebox.showinfo("\u89c6\u9891\u6807\u6ce8", "\u8bf7\u5148\u4e3a\u8be5\u573a\u6bd4\u8d5b\u5bfc\u5165\u89c6\u9891\u590d\u76d8\u3002")
            return
        supported = "goal, red_card, set_piece, counter_attack, tempo_shift, penalty, injury, tactical_shift, defensive_error, shot_quality"
        event_type = simpledialog.askstring("\u89c6\u9891\u4e8b\u4ef6", f"\u4e8b\u4ef6\u7c7b\u578b:\n{supported}", parent=self.root)
        if not event_type:
            return
        position = simpledialog.askstring("\u89c6\u9891\u4e8b\u4ef6", "\u4f4d\u7f6e\uff08\u53ef\u9009\uff09\uff1a\u8f93\u5165 f12 \u8868\u793a\u7b2c12\u5e27\uff0c\u6216\u8f93\u5165 75 \u8868\u793a75\u79d2\u3002", parent=self.root)
        note = simpledialog.askstring("\u89c6\u9891\u4e8b\u4ef6", "\u5907\u6ce8\uff08\u53ef\u9009\uff09\uff1a\u4f8b\u5982\u8fdb\u7403\u524d\u8fde\u7eed\u53cd\u51fb\u3001\u9632\u7ebf\u5931\u4f4d\u3002", parent=self.root) or ""
        frame_index = None
        timestamp_seconds = None
        position_text = str(position or "").strip().lower()
        if position_text.startswith("f"):
            try:
                frame_index = int(float(position_text[1:]))
            except (TypeError, ValueError):
                frame_index = None
        elif position_text:
            try:
                timestamp_seconds = float(position_text)
            except (TypeError, ValueError):
                timestamp_seconds = None
        result = add_video_review_annotation(
            review_id,
            event_type=event_type,
            frame_index=frame_index,
            timestamp_seconds=timestamp_seconds,
            note=note,
            created_by="app_operator",
        )
        if not bool(result.get("ok")):
            messagebox.showerror("\u89c6\u9891\u6807\u6ce8", f"\u6807\u6ce8\u5931\u8d25: {result.get('reason', '-')}")
            return
        annotation = result.get("annotation") if isinstance(result.get("annotation"), dict) else {}
        self.status_var.set(f"\u89c6\u9891\u4e8b\u4ef6\u5df2\u6807\u6ce8: {annotation.get('event_label', event_type)}")
        messagebox.showinfo(
            "\u89c6\u9891\u6807\u6ce8",
            f"\u5df2\u5199\u5165 VideoReview Agent\n\n\u7c7b\u578b: {annotation.get('event_label', event_type)}\n\u6807\u6ce8ID: {annotation.get('annotation_id', '-')}\n\n\u8be5\u6807\u6ce8\u5c06\u8fdb\u5165 Evaluation Agent \u8d5b\u540e\u590d\u76d8\u8bb0\u5fc6\u3002",
        )
        self.open_review_center()

    def export_video_review_fewshot_samples(self) -> tuple[Path, Path, Path, Path, Path] | None:
        result = export_video_review_fewshot_samples_now(limit=120)
        output_path = Path(str(result.get("output_path") or ""))
        sample_count = int(result.get("sample_count", 0) or 0)
        manual_count = int(result.get("manual_annotation_sample_count", 0) or 0)
        auto_count = int(result.get("auto_hypothesis_sample_count", 0) or 0)
        if sample_count <= 0:
            self.status_var.set("\u89c6\u9891\u590d\u76d8\u6837\u672c\u6682\u65e0\u53ef\u5bfc\u51fa\u5185\u5bb9")
            messagebox.showinfo("\u89c6\u9891\u590d\u76d8\u6837\u672c", "\u6682\u65e0\u4eba\u5de5\u6807\u6ce8\u6216\u89c6\u9891\u4e8b\u4ef6\u5047\u8bbe\u53ef\u5bfc\u51fa\u3002")
            return None
        try:
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("\u89c6\u9891\u590d\u76d8\u6837\u672c", f"\u8bfb\u53d6\u5bfc\u51fa\u8349\u7a3f\u5931\u8d25:\n{output_path}\n\n{exc}")
            return None
        now = datetime.now()
        memory = get_video_review_fewshot_memory()
        merge_plan = build_video_review_fewshot_merge_plan(payload, memory)
        merge_bundle = build_video_review_fewshot_merge_bundle(merge_plan, generated_at=now)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        review_path = REPORT_DIR / build_video_review_fewshot_draft_review_filename(now)
        plan_path = REPORT_DIR / build_video_review_fewshot_merge_plan_filename(now)
        bundle_path = REPORT_DIR / build_video_review_fewshot_merge_bundle_filename(now)
        bundle_review_path = REPORT_DIR / build_video_review_fewshot_merge_bundle_report_filename(now)
        review_path.write_text("\n".join(build_video_review_fewshot_draft_review_lines(payload)), encoding="utf-8")
        plan_path.write_text("\n".join(build_video_review_fewshot_merge_plan_lines(merge_plan)), encoding="utf-8")
        bundle_path.write_text(json.dumps(merge_bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        bundle_review_path.write_text("\n".join(build_video_review_fewshot_merge_bundle_report_lines(merge_bundle)), encoding="utf-8")
        validation = merge_plan.get("validation", {}) if isinstance(merge_plan.get("validation"), dict) else {}
        validation_text = str(validation.get("summary_text") or "-")
        self.status_var.set(f"\u89c6\u9891\u590d\u76d8\u6837\u672c\u5df2\u5bfc\u51fa: {sample_count} \u6761")
        messagebox.showinfo(
            "\u89c6\u9891\u590d\u76d8\u6837\u672c",
            (
                f"\u5df2\u751f\u6210 Evaluation Agent \u89c6\u9891\u590d\u76d8\u6837\u672c:\n{output_path}\n\n"
                f"\u5ba1\u67e5\u62a5\u544a:\n{review_path}\n\n"
                f"\u5408\u5e76\u8ba1\u5212:\n{plan_path}\n\n"
                f"\u53ef\u5e94\u7528\u5305:\n{bundle_path}\n\n"
                f"\u5305\u5ba1\u67e5:\n{bundle_review_path}\n\n"
                f"\u6837\u672c: {sample_count}\n"
                f"\u4eba\u5de5\u6807\u6ce8: {manual_count}\n"
                f"\u81ea\u52a8\u5047\u8bbe: {auto_count}\n\n"
                f"\u6821\u9a8c: {validation_text}\n\n"
                "\u8be5\u6570\u636e\u4ec5\u7528\u4e8e\u8d5b\u540e\u590d\u76d8\uff0c\u4e0d\u8fdb\u5165\u8d5b\u524d\u9884\u6d4b\u7279\u5f81\u3002"
            ),
        )
        return output_path, review_path, plan_path, bundle_path, bundle_review_path

    def _statsbomb_review_training_action_command(self, action_key: str):
        if action_key in {
            "build_statsbomb_review_samples",
            "recover_results",
            "run_high_accuracy_strategy_backtest",
            "refresh_review_center",
        }:
            return lambda key=action_key: self.run_statsbomb_review_training_action(key)
        return None

    def _current_statsbomb_review_training_quality(self) -> dict:
        return build_statsbomb_review_training_quality_summary(get_statsbomb_review_training_samples())

    def _record_statsbomb_review_training_action_feedback(self, feedback: dict) -> None:
        try:
            _append_statsbomb_review_training_action_feedback_log(feedback)
        except Exception as exc:
            self._log_event("ERROR", f"事件代理修复闭环记录写入失败: {exc}")
            return
        self._log_event("OK", str(feedback.get("summary_text") or "事件代理修复闭环已记录"))

    def _rebuild_statsbomb_review_samples_after_recovery(self, recovery_result: dict) -> str:
        record = self.result_recovery_run_record if isinstance(self.result_recovery_run_record, dict) else {}
        if str(record.get("trigger") or "") != "statsbomb_review_repair":
            return ""
        before_quality = record.get("statsbomb_review_repair_before_quality")
        if not isinstance(before_quality, dict):
            before_quality = self.pending_statsbomb_review_repair_before_quality
        if not isinstance(before_quality, dict):
            before_quality = self._current_statsbomb_review_training_quality()
        try:
            result = repair_training_data_health("build_statsbomb_review_samples")
            if bool(result.get("ok", True)):
                invalidate_statsbomb_state_cache(STATSBOMB_REVIEW_TRAINING_FILE)
                after_quality = self._current_statsbomb_review_training_quality()
            else:
                after_quality = before_quality
        except Exception as exc:
            result = {
                "ok": False,
                "message": f"result recovery completed but StatsBomb review sample rebuild failed: {exc}",
            }
            after_quality = before_quality
        fallback_message = (
            f"result recovery settled {int(recovery_result.get('new_settled', 0) or 0)}; "
            f"rebuilt StatsBomb/Event Proxy review samples"
        )
        result["message"] = str(result.get("message") or fallback_message)
        feedback = build_statsbomb_review_training_action_feedback(
            "recover_results_rebuild_samples",
            before_quality,
            after_quality,
            result,
        )
        self._record_statsbomb_review_training_action_feedback(feedback)
        self.pending_statsbomb_review_repair_before_quality = None
        return f"{feedback.get('summary_text', '-')}\n下一步: {feedback.get('next_recommendation', '-')}"

    def run_statsbomb_review_training_action(self, action_key: str) -> None:
        before_quality = self._current_statsbomb_review_training_quality()
        if action_key == "build_statsbomb_review_samples":
            self.export_statsbomb_event_proxy_review_samples(before_quality=before_quality, action_key=action_key)
            return
        if action_key == "recover_results":
            feedback = build_statsbomb_review_training_action_feedback(
                action_key,
                before_quality,
                before_quality,
                {"ok": True, "queued": True, "message": "result recovery queued"},
            )
            self._record_statsbomb_review_training_action_feedback(feedback)
            self.pending_statsbomb_review_repair_before_quality = dict(before_quality)
            self.run_result_recovery(trigger="statsbomb_review_repair", show_popup=True)
            return
        if action_key == "run_high_accuracy_strategy_backtest":
            feedback = build_statsbomb_review_training_action_feedback(
                action_key,
                before_quality,
                before_quality,
                {"ok": True, "queued": True, "message": "high accuracy backtest queued"},
            )
            self._record_statsbomb_review_training_action_feedback(feedback)
            self.run_high_accuracy_strategy_backtest_task()
            return
        if action_key == "refresh_review_center":
            after_quality = self._current_statsbomb_review_training_quality()
            feedback = build_statsbomb_review_training_action_feedback(action_key, before_quality, after_quality, {"ok": True})
            self._record_statsbomb_review_training_action_feedback(feedback)
            self.open_review_center()

    def export_video_review_evidence_gap_batch_plan(self) -> Path:
        settlements = list(reversed(get_recent_settlements(limit=200)))
        rows = build_video_review_evidence_gap_action_rows(
            settlements,
            get_statsbomb_review_training_samples(),
            limit=20,
        )
        now = datetime.now()
        batch_id = build_video_review_evidence_gap_batch_id(now)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = REPORT_DIR / build_video_review_evidence_gap_batch_plan_filename(now)
        path.write_text(
            "\n".join(build_video_review_evidence_gap_batch_plan_lines(rows, generated_at=now, batch_id=batch_id)),
            encoding="utf-8",
        )
        batch_record = build_video_review_evidence_gap_batch_record(rows, path, generated_at=now, batch_id=batch_id)
        batch_state = build_video_review_evidence_gap_batch_state_with_record(
            _load_video_review_evidence_gap_batch_state(),
            batch_record,
        )
        _save_video_review_evidence_gap_batch_state(batch_state)
        self.status_var.set(f"复盘证据缺口批次计划已导出: {path.name} | {len(rows)} 场")
        messagebox.showinfo(
            "复盘证据缺口批次计划",
            build_video_review_evidence_gap_batch_plan_export_message(path, rows, batch_record),
        )
        return path

    def open_video_review_evidence_gap_center_window(
        self,
        initial_batch_filter: str | None = None,
        initial_status_filter: str | None = None,
        initial_priority_filter: str | None = None,
        initial_evidence_filter: str | None = None,
    ) -> None:
        state = _load_video_review_evidence_gap_batch_state()
        options = build_video_review_evidence_gap_batch_filter_options(state)

        def _options(key: str) -> list[dict]:
            values = options.get(key) if isinstance(options.get(key), list) else []
            return [item for item in values if isinstance(item, dict)]

        def _labels(key: str) -> list[str]:
            return [str(item.get("label") or item.get("value") or "-") for item in _options(key)]

        def _label_for_value(key: str, value: str | None) -> str | None:
            resolved = str(value or "").strip()
            if not resolved:
                return None
            for item in _options(key):
                if str(item.get("value") or "").strip() == resolved:
                    return str(item.get("label") or item.get("value") or "-")
            return None

        def _value_for_label(key: str, label: str) -> str:
            for item in _options(key):
                if str(item.get("label") or item.get("value") or "-") == label:
                    return str(item.get("value") or "all")
            first = _options(key)[0] if _options(key) else {}
            return str(first.get("value") or "all")

        window = tk.Toplevel(self.root)
        window.title("复盘证据缺口专项中心")
        window.geometry("1120x720")
        window.configure(bg=BG)

        shell = tk.Frame(window, bg=BG)
        shell.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        tk.Label(shell, text="复盘证据缺口专项中心", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 15, "bold")).pack(anchor=tk.W)
        summary_var = tk.StringVar(value="-")
        tk.Label(shell, textvariable=summary_var, bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 10)).pack(anchor=tk.W, pady=(4, 12))

        controls = tk.Frame(shell, bg=BG)
        controls.pack(fill=tk.X, pady=(0, 12))
        batch_var = tk.StringVar(value=(_labels("batch_options") or ["最新批次"])[0])
        status_var = tk.StringVar(value=(_labels("status_options") or ["全部状态"])[0])
        priority_var = tk.StringVar(value=(_labels("priority_options") or ["全部优先级"])[0])
        evidence_var = tk.StringVar(value=(_labels("evidence_options") or ["全部证据"])[0])
        initial_batch_label = _label_for_value("batch_options", initial_batch_filter)
        initial_status_label = _label_for_value("status_options", initial_status_filter)
        initial_priority_label = _label_for_value("priority_options", initial_priority_filter)
        initial_evidence_label = _label_for_value("evidence_options", initial_evidence_filter)
        if initial_batch_label:
            batch_var.set(initial_batch_label)
        if initial_status_label:
            status_var.set(initial_status_label)
        if initial_priority_label:
            priority_var.set(initial_priority_label)
        if initial_evidence_label:
            evidence_var.set(initial_evidence_label)

        def _combo(label: str, variable: tk.StringVar, values: list[str]) -> ttk.Combobox:
            wrap = tk.Frame(controls, bg=BG)
            wrap.pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(wrap, text=label, bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)
            combo = ttk.Combobox(wrap, textvariable=variable, values=values, state="readonly", width=22)
            combo.pack(anchor=tk.W)
            return combo

        batch_combo = _combo("批次", batch_var, _labels("batch_options"))
        status_combo = _combo("状态", status_var, _labels("status_options"))
        priority_combo = _combo("优先级", priority_var, _labels("priority_options"))
        evidence_combo = _combo("证据", evidence_var, _labels("evidence_options"))

        table_wrap = tk.Frame(shell, bg=PANEL)
        table_wrap.pack(fill=tk.BOTH, expand=True)
        self._configure_dark_tree_style("EvidenceGapBatch.Treeview", rowheight=27)
        columns = ("priority", "score", "status", "evidence", "source", "handled_at", "match_id", "title")
        tree = ttk.Treeview(table_wrap, columns=columns, show="headings", style="EvidenceGapBatch.Treeview", height=14)
        headings = {
            "priority": "优先级",
            "score": "分数",
            "status": "状态",
            "evidence": "证据",
            "source": "来源",
            "handled_at": "处理时间",
            "match_id": "match_id",
            "title": "场次",
        }
        widths = {
            "priority": 64,
            "score": 54,
            "status": 72,
            "evidence": 132,
            "source": 130,
            "handled_at": 138,
            "match_id": 130,
            "title": 280,
        }
        for key in columns:
            tree.heading(key, text=headings[key])
            tree.column(key, width=widths[key], minwidth=50, stretch=key == "title", anchor=tk.W)
        scrollbar = tk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10, padx=(0, 10))

        detail = tk.Text(
            shell,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            height=7,
        )
        detail.pack(fill=tk.X, pady=(12, 0))
        rows_cache: list[dict[str, object]] = []
        filter_result_cache: dict[str, object] = {}
        action_var = tk.StringVar(value="选择一条记录后可直接绑定当前选中回放或导入当前选中视频。")

        def _selected_row(show_prompt: bool = True) -> dict | None:
            selection = tree.selection()
            if not selection or not rows_cache:
                if show_prompt:
                    messagebox.showinfo("复盘证据缺口批次", "请先选择一条缺口批次记录。")
                return None
            try:
                index = int(selection[0])
            except (TypeError, ValueError):
                if show_prompt:
                    messagebox.showinfo("复盘证据缺口批次", "当前选择无效，请重新选择。")
                return None
            if index < 0 or index >= len(rows_cache):
                if show_prompt:
                    messagebox.showinfo("复盘证据缺口批次", "当前选择无效，请重新选择。")
                return None
            return rows_cache[index]

        def _settlement_for_row(row: dict | None) -> dict | None:
            if not isinstance(row, dict):
                return None
            settlements = list(reversed(get_recent_settlements(limit=300)))
            settlement = find_video_review_evidence_gap_settlement(settlements, str(row.get("match_id") or ""))
            if not settlement:
                messagebox.showinfo(
                    "复盘证据缺口批次",
                    f"未在最近结算记录中找到该场比赛:\n{row.get('match_id', '-')}",
                )
                return None
            return settlement

        def _set_action_text(row: dict | None) -> None:
            actions = build_video_review_evidence_gap_batch_action_rows(row or {})
            enabled = [str(action.get("label") or "-") for action in actions if bool(action.get("enabled"))]
            disabled = [str(action.get("label") or "-") for action in actions if not bool(action.get("enabled"))]
            action_var.set(
                f"当前选中记录可执行: {', '.join(enabled) if enabled else '-'}"
                + (f" | 不可执行: {', '.join(disabled)}" if disabled else "")
            )

        def _show_detail(index: int | None = None) -> None:
            detail.configure(state=tk.NORMAL)
            detail.delete("1.0", tk.END)
            if index is None or index < 0 or index >= len(rows_cache):
                detail.insert(tk.END, "选择一条批次记录查看处理来源、证据类型和报告路径。")
                _set_action_text(None)
            else:
                row = rows_cache[index]
                detail.insert(
                    tk.END,
                    (
                        f"{row.get('title', '-')}\n"
                        f"批次: {row.get('batch_id', '-')}\n"
                        f"match_id: {row.get('match_id', '-')}\n"
                        f"优先级: {row.get('priority', '-')} / score {row.get('score', '-')}\n"
                        f"状态: {row.get('status', '-')} | 证据: {row.get('evidence', '-')} | 来源: {row.get('source', '-')}\n"
                        f"处理时间: {row.get('handled_at', '-')}"
                    ),
                )
                _set_action_text(row)
            detail.configure(state=tk.DISABLED)

        def _refresh(_event=None) -> None:
            nonlocal rows_cache, filter_result_cache
            result = build_video_review_evidence_gap_batch_filter_result(
                _load_video_review_evidence_gap_batch_state(),
                batch_filter=_value_for_label("batch_options", batch_var.get()),
                status_filter=_value_for_label("status_options", status_var.get()),
                priority_filter=_value_for_label("priority_options", priority_var.get()),
                evidence_filter=_value_for_label("evidence_options", evidence_var.get()),
            )
            filter_result_cache = result
            summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
            summary_var.set(str(summary.get("summary_text") or "-"))
            rows_cache = build_video_review_evidence_gap_batch_filter_rows(result, limit=200)
            for item_id in tree.get_children():
                tree.delete(item_id)
            if not rows_cache:
                tree.insert("", tk.END, iid="empty", values=("-", "-", "-", "-", "-", "-", "-", "暂无匹配的缺口批次记录"))
                _show_detail(None)
                return
            for index, row in enumerate(rows_cache):
                tree.insert(
                    "",
                    tk.END,
                    iid=str(index),
                    values=(
                        row.get("priority", "-"),
                        row.get("score", "-"),
                        row.get("status", "-"),
                        row.get("evidence", "-"),
                        row.get("source", "-"),
                        row.get("handled_at", "-"),
                        row.get("match_id", "-"),
                        row.get("title", "-"),
                    ),
            )
            tree.selection_set("0")
            tree.focus("0")
            tree.see("0")
            _show_detail(0)

        for combo in (batch_combo, status_combo, priority_combo, evidence_combo):
            combo.bind("<<ComboboxSelected>>", _refresh)

        tk.Button(
            controls,
            text="刷新",
            command=_refresh,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=5,
        ).pack(side=tk.LEFT, padx=(6, 0), pady=(17, 0))

        def _on_select(_event=None) -> None:
            selection = tree.selection()
            if selection and rows_cache:
                try:
                    _show_detail(int(selection[0]))
                except (TypeError, ValueError):
                    _show_detail(None)

        def _show_selected_settlement_detail() -> None:
            row = _selected_row()
            settlement = _settlement_for_row(row)
            if not settlement:
                return
            detail.configure(state=tk.NORMAL)
            detail.delete("1.0", tk.END)
            detail.insert(tk.END, self._settlement_review_text(settlement))
            detail.configure(state=tk.DISABLED)

        def _bind_selected_external_reference() -> None:
            row = _selected_row()
            settlement = _settlement_for_row(row)
            if not settlement:
                return
            self.import_video_review_reference_for_settlement(settlement)
            _refresh()

        def _import_selected_local_video() -> None:
            row = _selected_row()
            settlement = _settlement_for_row(row)
            if not settlement:
                return
            self.import_video_review_for_settlement(settlement)
            _refresh()

        def _build_event_proxy_samples_for_batch() -> None:
            row = _selected_row()
            if row is None:
                return
            self.export_statsbomb_event_proxy_review_samples()
            _refresh()

        def _export_current_filter_report() -> None:
            result = filter_result_cache or build_video_review_evidence_gap_batch_filter_result(
                _load_video_review_evidence_gap_batch_state(),
                batch_filter=_value_for_label("batch_options", batch_var.get()),
                status_filter=_value_for_label("status_options", status_var.get()),
                priority_filter=_value_for_label("priority_options", priority_var.get()),
                evidence_filter=_value_for_label("evidence_options", evidence_var.get()),
            )
            now = datetime.now()
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            path = REPORT_DIR / build_video_review_evidence_gap_batch_filter_report_filename(now)
            path.write_text(
                "\n".join(build_video_review_evidence_gap_batch_filter_report_lines(result, generated_at=now)),
                encoding="utf-8",
            )
            self.status_var.set(f"复盘证据缺口处理报告已导出: {path.name}")
            messagebox.showinfo(
                "复盘证据缺口处理报告",
                build_video_review_evidence_gap_batch_filter_report_message(path, result),
            )

        action_wrap = tk.Frame(shell, bg=BG)
        action_wrap.pack(fill=tk.X, pady=(10, 0))
        tk.Label(action_wrap, textvariable=action_var, bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W, pady=(0, 8))
        for label, command, color in [
            ("场次详情", _show_selected_settlement_detail, PANEL_2),
            ("绑定当前选中回放", _bind_selected_external_reference, BLUE),
            ("导入当前选中视频", _import_selected_local_video, PANEL_2),
            ("生成事件代理样本", _build_event_proxy_samples_for_batch, PANEL_2),
            ("导出筛选报告", _export_current_filter_report, PANEL_2),
        ]:
            tk.Button(
                action_wrap,
                text=label,
                command=command,
                bg=color,
                fg="white" if color == BLUE else TEXT,
                activebackground="#3d5ee7" if color == BLUE else "#172638",
                activeforeground="white",
                relief=tk.FLAT,
                font=("Microsoft YaHei UI", 10, "bold"),
                padx=14,
                pady=6,
            ).pack(side=tk.LEFT, padx=(0, 10))

        tree.bind("<<TreeviewSelect>>", _on_select)
        _refresh()

    def open_video_review_evidence_gap_batch_filter_window(self) -> None:
        self.open_video_review_evidence_gap_center_window()

    def _run_video_review_evidence_gap_quick_action(self, evidence_filter: str, action_kind: str) -> None:
        state = _load_video_review_evidence_gap_batch_state()
        target = build_video_review_evidence_gap_quick_target_item(state, evidence_filter)
        if not target:
            self.open_video_review_evidence_gap_center_window(**build_video_review_evidence_gap_quick_open_filters(evidence_filter, state))
            return
        settlement = find_video_review_evidence_gap_settlement(
            list(reversed(get_recent_settlements(limit=300))),
            str(target.get("match_id") or ""),
        )
        if not settlement:
            self.open_video_review_evidence_gap_center_window(**build_video_review_evidence_gap_quick_open_filters(evidence_filter, state))
            return
        if action_kind == "bind_external_reference":
            self.import_video_review_reference_for_settlement(settlement)
        elif action_kind == "import_local_video":
            self.import_video_review_for_settlement(settlement)
        else:
            self.open_video_review_evidence_gap_center_window(**build_video_review_evidence_gap_quick_open_filters(evidence_filter, state))

    def open_ai_video_review_center_window(self) -> None:
        settlements = list(reversed(get_recent_settlements(limit=200)))
        video_memory_health = self._video_review_fewshot_memory_health_context()
        statsbomb_samples = get_statsbomb_review_training_samples()
        video_source_coverage = build_video_review_source_coverage_summary(
            settlements,
            statsbomb_samples=statsbomb_samples,
            video_memory=get_video_review_fewshot_memory(),
        )
        summary = build_video_review_center_summary(video_memory_health, video_source_coverage)

        window = tk.Toplevel(self.root)
        window.title("AI视频复盘专项中心")
        window.geometry("1120x740")
        window.configure(bg=BG)

        shell = tk.Frame(window, bg=BG)
        shell.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        header = tk.Frame(shell, bg=BG)
        header.pack(fill=tk.X, pady=(0, 12))
        tk.Label(header, text="AI视频复盘专项中心", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 15, "bold")).pack(side=tk.LEFT)

        def _header_button(label: str, command, *, color: str = PANEL_2) -> None:
            tk.Button(
                header,
                text=label,
                command=command,
                bg=color,
                fg="white" if color == BLUE else TEXT,
                activebackground="#3d5ee7" if color == BLUE else "#172638",
                activeforeground="white",
                relief=tk.FLAT,
                font=("Microsoft YaHei UI", 10, "bold"),
                padx=14,
                pady=6,
            ).pack(side=tk.RIGHT, padx=(8, 0))

        _header_button("刷新", lambda: (window.destroy(), self.open_ai_video_review_center_window()))
        _header_button("审计视频记忆", self.export_video_review_fewshot_memory_audit)
        _header_button("预览样本合并", self.preview_video_review_fewshot_merge_bundle)
        _header_button("导出视频复盘样本", self.export_video_review_fewshot_samples, color=BLUE)

        scroll_wrap = tk.Frame(shell, bg=BG)
        scroll_wrap.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(scroll_wrap, bg=BG, bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(scroll_wrap, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        content = tk.Frame(canvas, bg=BG)
        window_id = canvas.create_window((0, 0), window=content, anchor=tk.NW)
        content.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))

        top = tk.Frame(content, bg=BG)
        top.pack(fill=tk.X, pady=(0, 12))
        for label, value, color in [
            ("复盘状态", str(summary.get("status_label") or summary.get("status") or "-"), self._tone_color(str(summary.get("tone") or "neutral"))),
            ("已结算", str(summary.get("settled_count", 0)), TEXT),
            ("本地视频", str(summary.get("local_video_count", 0)), GREEN if int(summary.get("local_video_count", 0) or 0) else TEXT),
            ("外部回放", str(summary.get("external_reference_count", 0)), "#7aa2ff" if int(summary.get("external_reference_count", 0) or 0) else TEXT),
            ("事件代理", str(summary.get("statsbomb_event_proxy_count", 0)), YELLOW if int(summary.get("statsbomb_event_proxy_count", 0) or 0) else TEXT),
            ("缺证据", str(summary.get("no_review_evidence_count", 0)), RED if int(summary.get("no_review_evidence_count", 0) or 0) else GREEN),
        ]:
            self._detail_metric(top, label, value, color)

        body = tk.Frame(content, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._strategy_section_title(left, "视频记忆健康", first=True)
        self._strategy_row(
            left,
            str(summary.get("title") or "-"),
            str(summary.get("body") or "-"),
        )
        card_rows = video_memory_health.get("card_rows") if isinstance(video_memory_health.get("card_rows"), list) else []
        if card_rows:
            for row in [item for item in card_rows if isinstance(item, dict)][:8]:
                self._strategy_row(
                    left,
                    f"{row.get('label', '-')}: {row.get('value', '-')}",
                    str(row.get("detail") or "-"),
                )
        else:
            self._strategy_row(left, "暂无健康卡片", "当前没有可展示的视频记忆健康明细。")

        self._strategy_section_title(left, "优先补标注/补样", first=False)
        action_rows = build_video_review_center_action_rows(
            video_memory_health,
            video_source_coverage,
        )
        action_command_map = {
            "open_video_review_evidence_gap_center_window_local_video": lambda: self._run_video_review_evidence_gap_quick_action(
                "local_video",
                "import_local_video",
            ),
            "open_video_review_evidence_gap_center_window_external_reference": lambda: self._run_video_review_evidence_gap_quick_action(
                "external_reference",
                "bind_external_reference",
            ),
            "export_video_review_fewshot_samples": self.export_video_review_fewshot_samples,
            "preview_video_review_fewshot_merge_bundle": self.preview_video_review_fewshot_merge_bundle,
            "export_video_review_fewshot_memory_audit": self.export_video_review_fewshot_memory_audit,
            "open_review_center": self.open_review_center,
            "open_ai_video_review_center_window": lambda: (window.destroy(), self.open_ai_video_review_center_window()),
        }
        if action_rows:
            for row in [item for item in action_rows if isinstance(item, dict)][:6]:
                self._strategy_row(
                    left,
                    str(row.get("title") or row.get("code") or "-"),
                    str(row.get("body") or row.get("recommendation") or "-"),
                    command=action_command_map.get(str(row.get("action_key") or "")),
                )
        else:
            self._strategy_row(left, "暂无补样建议", "视频记忆当前没有需要立即处理的补标注/补样动作。")

        self._strategy_section_title(right, "视频来源覆盖", first=True)
        self._strategy_row(
            right,
            f"{video_source_coverage.get('coverage_status', '-')} | settled {video_source_coverage.get('total_settled_count', 0)}",
            (
                f"本地视频 {video_source_coverage.get('local_video_count', 0)} | "
                f"外部回放 {video_source_coverage.get('external_reference_count', 0)} | "
                f"事件代理 {video_source_coverage.get('statsbomb_event_proxy_count', 0)} | "
                f"缺证据 {video_source_coverage.get('no_review_evidence_count', 0)}"
            ),
        )
        coverage_rows = video_source_coverage.get("rows") if isinstance(video_source_coverage.get("rows"), list) else []
        for row in [item for item in coverage_rows if isinstance(item, dict)][:8]:
            self._strategy_row(
                right,
                str(row.get("title") or row.get("label") or "-"),
                str(row.get("body") or row.get("suggestion") or "-"),
            )

        self._strategy_section_title(right, "视频降级策略", first=False)
        self._strategy_row(
            right,
            "合法来源优先",
            str(video_source_coverage.get("fallback_policy_text") or "-"),
        )
        self._strategy_section_title(right, "使用边界", first=False)
        self._strategy_row(
            right,
            "仅用于赛后复盘",
            "本地视频、FIFA+ 回放链接和 StatsBomb/Event Proxy 只作为赛后归因证据，不自动下载受版权保护的视频，也不写入赛前预测特征。",
        )
        self._bind_canvas_mousewheel(content, canvas)

    def open_statsbomb_review_training_center_window(self) -> None:
        quality = self._current_statsbomb_review_training_quality()
        repair_records = _load_statsbomb_review_training_action_feedback_log()
        summary = build_statsbomb_review_training_center_summary(quality, repair_records)

        window = tk.Toplevel(self.root)
        window.title("事件代理专项中心")
        window.geometry("1040x700")
        window.configure(bg=BG)

        shell = tk.Frame(window, bg=BG)
        shell.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        header = tk.Frame(shell, bg=BG)
        header.pack(fill=tk.X, pady=(0, 12))
        tk.Label(header, text="事件代理专项中心", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 15, "bold")).pack(side=tk.LEFT)
        tk.Button(
            header,
            text="导出质量报告",
            command=self.export_statsbomb_review_training_quality_report,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(
            header,
            text="生成事件代理样本",
            command=self.export_statsbomb_event_proxy_review_samples,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(
            header,
            text="刷新",
            command=lambda: (window.destroy(), self.open_statsbomb_review_training_center_window()),
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.RIGHT, padx=(8, 0))

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 12))
        for label, value, color in [
            ("质量状态", str(summary.get("status") or "-"), self._tone_color(str(summary.get("tone") or "neutral"))),
            ("复盘样本", str(summary.get("sample_count", 0)), TEXT),
            ("问题数", str(summary.get("issue_count", 0)), RED if int(summary.get("issue_count", 0) or 0) else GREEN),
            ("修复记录", str(summary.get("repair_count", 0)), "#7aa2ff"),
        ]:
            self._detail_metric(top, label, value, color)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._strategy_section_title(left, "样本质量", first=True)
        card_rows = quality.get("card_rows") if isinstance(quality.get("card_rows"), list) else []
        if card_rows:
            for row in card_rows:
                if isinstance(row, dict):
                    self._strategy_row(
                        left,
                        f"{row.get('label', '-')}: {row.get('value', '-')}",
                        str(row.get("detail") or "-"),
                    )
        else:
            self._strategy_row(left, "暂无质量卡片", "当前没有可展示的 StatsBomb/Event Proxy 质量明细。")

        self._strategy_section_title(left, "质量问题", first=False)
        issues = quality.get("issues") if isinstance(quality.get("issues"), list) else []
        if issues:
            for issue in [item for item in issues if isinstance(item, dict)][:6]:
                self._strategy_row(
                    left,
                    f"{issue.get('severity', '-')}: {issue.get('code', '-')}",
                    f"{issue.get('message', '-')}\n建议: {issue.get('recommendation', '-')}",
                )
        else:
            self._strategy_row(left, "暂无质量问题", "事件代理复盘样本当前没有阻塞项。")

        self._strategy_section_title(right, "可执行修复", first=True)

        def _action_command(action_key: str):
            if action_key == "refresh_review_center":
                return lambda: (window.destroy(), self.open_statsbomb_review_training_center_window())
            return lambda key=action_key: self.run_statsbomb_review_training_action(key)

        for row in build_statsbomb_review_training_action_rows(quality):
            if isinstance(row, dict):
                self._strategy_row(
                    right,
                    str(row.get("title") or "-"),
                    str(row.get("body") or "-"),
                    command=_action_command(str(row.get("action_key") or "")),
                )

        self._strategy_section_title(right, "修复闭环", first=False)
        repair_rows = build_statsbomb_review_training_feedback_rows(repair_records, limit=8)
        if repair_rows:
            for row in repair_rows:
                self._strategy_row(
                    right,
                    str(row.get("title") or "-"),
                    str(row.get("body") or "-"),
                )
        else:
            self._strategy_row(right, "暂无修复记录", "点击修复动作后，会记录动作前后的质量变化。")

        self._strategy_section_title(right, "边界", first=False)
        self._strategy_row(
            right,
            "仅用于赛后复盘",
            "StatsBomb/Event Proxy 样本只进入 Evaluation Agent 复盘与错因归因，不写入赛前预测特征。",
        )

    def export_statsbomb_review_training_quality_report(self) -> Path:
        quality = self._current_statsbomb_review_training_quality()
        repair_records = _load_statsbomb_review_training_action_feedback_log()
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = REPORT_DIR / build_statsbomb_review_training_quality_report_filename(datetime.now())
        path.write_text(
            "\n".join(build_statsbomb_review_training_quality_report_lines(quality, repair_records)),
            encoding="utf-8",
        )
        self.status_var.set(f"事件代理质量报告已导出: {path.name}")
        messagebox.showinfo(
            "事件代理质量报告",
            build_statsbomb_review_training_quality_export_message(path, quality, len(repair_records)),
        )
        return path

    def export_statsbomb_event_proxy_review_samples(
        self,
        before_quality: dict | None = None,
        action_key: str = "build_statsbomb_review_samples",
    ) -> dict | None:
        before_quality = before_quality if isinstance(before_quality, dict) else self._current_statsbomb_review_training_quality()
        try:
            result = repair_training_data_health("build_statsbomb_review_samples")
        except Exception as exc:
            feedback = build_statsbomb_review_training_action_feedback(
                action_key,
                before_quality,
                before_quality,
                {"ok": False, "message": str(exc)},
            )
            self._record_statsbomb_review_training_action_feedback(feedback)
            messagebox.showerror("\u4e8b\u4ef6\u4ee3\u7406\u590d\u76d8", f"\u751f\u6210\u5931\u8d25:\n{exc}")
            return None
        sample_count = int(result.get("generated_sample_count", 0) or 0)
        if not bool(result.get("ok", True)):
            feedback = build_statsbomb_review_training_action_feedback(action_key, before_quality, before_quality, result)
            self._record_statsbomb_review_training_action_feedback(feedback)
            self.status_var.set("\u4e8b\u4ef6\u4ee3\u7406\u590d\u76d8\u6837\u672c\u751f\u6210\u5931\u8d25")
            messagebox.showerror("\u4e8b\u4ef6\u4ee3\u7406\u590d\u76d8", str(result.get("message") or result.get("reason") or "-"))
            return result
        try:
            invalidate_statsbomb_state_cache(STATSBOMB_REVIEW_TRAINING_FILE)
            review_samples = get_statsbomb_review_training_samples()
            quality = build_statsbomb_review_training_quality_summary(review_samples)
        except Exception as exc:
            review_samples = {}
            quality = {
                "status": "attention",
                "issue_count": 1,
                "issues": [
                    {
                        "code": "statsbomb_review_quality_refresh_failed",
                        "severity": "warning",
                        "message": "事件代理复盘质量刷新失败",
                        "recommendation": f"重新打开复盘中心或检查训练样本文件: {exc}",
                    }
                ],
            }
        feedback = build_statsbomb_review_training_action_feedback(action_key, before_quality, quality, result)
        self._record_statsbomb_review_training_action_feedback(feedback)
        batch_update = {"updated_count": 0}
        sample_match_ids = collect_video_review_evidence_gap_sample_match_ids(review_samples)
        if sample_match_ids:
            try:
                batch_update = _record_video_review_evidence_gap_batch_resolution(
                    sample_match_ids,
                    evidence_kind="statsbomb_event_proxy",
                    source_name="StatsBomb/Event Proxy",
                    review_id=str(result.get("output_path") or "statsbomb_review_training_samples"),
                )
            except Exception as exc:
                self._log_event("ERROR", f"复盘证据缺口批次事件代理回写失败: {exc}")
            else:
                if int(batch_update.get("updated_count", 0) or 0) > 0:
                    self._log_event("OK", f"复盘证据缺口批次事件代理已回写: {batch_update.get('updated_count', 0)} 场")
        result["evidence_gap_batch_update"] = batch_update
        quality_status = str(quality.get("status") or "-")
        batch_update_text = f" | 批次回写 {int(batch_update.get('updated_count', 0) or 0)} 场" if int(batch_update.get("updated_count", 0) or 0) else ""
        self.status_var.set(f"\u4e8b\u4ef6\u4ee3\u7406\u590d\u76d8\u6837\u672c\u5df2\u751f\u6210: {sample_count} \u6761 | \u8d28\u91cf {quality_status}{batch_update_text}")
        self.open_review_center()
        messagebox.showinfo(
            "\u4e8b\u4ef6\u4ee3\u7406\u590d\u76d8",
            build_statsbomb_event_proxy_review_samples_message(result, quality),
        )
        return result

    def preview_video_review_fewshot_merge_bundle(self) -> Path | None:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        selected = filedialog.askopenfilename(
            title="Select video review few-shot merge bundle",
            initialdir=str(REPORT_DIR),
            filetypes=[
                ("Video review merge bundle", "video_review_fewshot_merge_bundle_*.json"),
                ("JSON", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not selected:
            return None
        source_path = Path(selected)
        try:
            bundle = json.loads(source_path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("\u89c6\u9891 few-shot \u9884\u89c8", f"\u8bfb\u53d6 bundle \u5931\u8d25:\n{source_path}\n\n{exc}")
            return None
        now = datetime.now()
        preview = build_video_review_fewshot_merge_apply_preview(
            bundle,
            get_video_review_fewshot_memory(),
            generated_at=now,
        )
        preview_path = REPORT_DIR / build_video_review_fewshot_merge_apply_preview_filename(now)
        preview_path.write_text("\n".join(build_video_review_fewshot_merge_apply_preview_lines(preview)), encoding="utf-8")
        summary = preview.get("summary", {}) if isinstance(preview.get("summary"), dict) else {}
        self.status_var.set(
            f"\u89c6\u9891 few-shot preview: {preview.get('status', '-')} | append {summary.get('append_count', 0)} | skipped {summary.get('skipped_count', 0)}"
        )
        messagebox.showinfo(
            "\u89c6\u9891 few-shot \u9884\u89c8",
            (
                f"\u5df2\u751f\u6210 dry-run \u9884\u89c8:\n{preview_path}\n\n"
                f"\u72b6\u6001: {preview.get('status', '-')}\n"
                f"\u5c06\u8ffd\u52a0: {summary.get('append_count', 0)}\n"
                f"\u8df3\u8fc7: {summary.get('skipped_count', 0)}"
            ),
        )
        return preview_path

    def apply_video_review_fewshot_merge_bundle(self) -> tuple[Path, Path | None] | None:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        selected = filedialog.askopenfilename(
            title="Select video review few-shot merge bundle to apply",
            initialdir=str(REPORT_DIR),
            filetypes=[
                ("Video review merge bundle", "video_review_fewshot_merge_bundle_*.json"),
                ("JSON", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not selected:
            return None
        source_path = Path(selected)
        try:
            bundle = json.loads(source_path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("\u89c6\u9891 few-shot \u5e94\u7528", f"\u8bfb\u53d6 bundle \u5931\u8d25:\n{source_path}\n\n{exc}")
            return None
        now = datetime.now()
        result = build_video_review_fewshot_merge_apply_result(
            bundle,
            get_video_review_fewshot_memory(),
            generated_at=now,
        )
        report_path = REPORT_DIR / build_video_review_fewshot_merge_apply_report_filename(now)
        report_path.write_text("\n".join(build_video_review_fewshot_merge_apply_report_lines(result)), encoding="utf-8")
        summary = result.get("summary", {}) if isinstance(result.get("summary"), dict) else {}
        if result.get("status") != "ready_to_write":
            self.status_var.set(f"\u89c6\u9891 few-shot apply blocked: {result.get('status', '-')} | report {report_path.name}")
            messagebox.showwarning(
                "\u89c6\u9891 few-shot \u5e94\u7528",
                f"\u5e94\u7528\u88ab\u963b\u65ad\u6216\u65e0\u53ef\u8ffd\u52a0\u6837\u672c\u3002\n\n\u62a5\u544a:\n{report_path}\n\n\u72b6\u6001: {result.get('status', '-')}",
            )
            return report_path, None
        applied_count = int(summary.get("applied_count", 0) or 0)
        final_count = int(summary.get("final_count", 0) or 0)
        preview = result.get("preview") if isinstance(result.get("preview"), dict) else {}
        backup_name = str(preview.get("backup_filename") or "")
        confirmed = messagebox.askyesno(
            "\u89c6\u9891 few-shot \u5e94\u7528",
            (
                "\u8fd9\u4f1a\u5c06\u5ba1\u6838\u540e\u7684\u8d5b\u540e\u89c6\u9891 few-shot \u6837\u672c\u5199\u5165 Evaluation Agent \u6b63\u5f0f\u89c6\u9891\u8bb0\u5fc6\u6c60\u3002\n\n"
                f"Bundle:\n{source_path}\n\n"
                f"\u5e94\u7528\u6837\u672c: {applied_count}\n"
                f"\u6700\u7ec8\u8bb0\u5fc6\u6837\u672c: {final_count}\n"
                f"\u5907\u4efd\u6587\u4ef6: {backup_name or '-'}\n\n"
                "\u7ee7\u7eed\uff1f"
            ),
        )
        if not confirmed:
            self.status_var.set(f"\u89c6\u9891 few-shot apply cancelled: {report_path.name}")
            return report_path, None
        updated_memory = result.get("updated_memory") if isinstance(result.get("updated_memory"), dict) else None
        if not updated_memory:
            messagebox.showerror("\u89c6\u9891 few-shot \u5e94\u7528", "\u5e94\u7528\u7ed3\u679c\u6ca1\u6709\u751f\u6210\u66f4\u65b0\u540e\u7684\u8bb0\u5fc6 payload\u3002")
            return report_path, None
        VIDEO_REVIEW_FEWSHOT_MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        backup_path: Path | None = None
        if VIDEO_REVIEW_FEWSHOT_MEMORY_FILE.exists():
            backup_path = VIDEO_REVIEW_FEWSHOT_MEMORY_FILE.parent / (
                backup_name or f"{VIDEO_REVIEW_FEWSHOT_MEMORY_FILE.name}.backup_{now.strftime('%Y%m%d_%H%M%S')}.json"
            )
            shutil.copy2(VIDEO_REVIEW_FEWSHOT_MEMORY_FILE, backup_path)
        tmp_path = VIDEO_REVIEW_FEWSHOT_MEMORY_FILE.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(updated_memory, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(VIDEO_REVIEW_FEWSHOT_MEMORY_FILE)
        invalidate_statsbomb_state_cache(VIDEO_REVIEW_FEWSHOT_MEMORY_FILE)
        self.status_var.set(f"\u89c6\u9891 few-shot applied: +{applied_count} | total {final_count}")
        self._refresh_current_view_after_release_state_change()
        messagebox.showinfo(
            "\u89c6\u9891 few-shot \u5e94\u7528",
            f"\u5df2\u5e94\u7528 {applied_count} \u6761\u6837\u672c\u3002\n\n\u8bb0\u5fc6\u6c60:\n{VIDEO_REVIEW_FEWSHOT_MEMORY_FILE}\n\n\u5907\u4efd:\n{backup_path or '-'}\n\n\u62a5\u544a:\n{report_path}",
        )
        return report_path, backup_path

    def rollback_video_review_fewshot_memory(self) -> tuple[Path, Path | None] | None:
        state_dir = VIDEO_REVIEW_FEWSHOT_MEMORY_FILE.parent
        state_dir.mkdir(parents=True, exist_ok=True)
        selected = filedialog.askopenfilename(
            title="Select video review few-shot memory backup",
            initialdir=str(state_dir),
            filetypes=[
                ("Video review few-shot backup", "video_review_fewshot_memory.backup_*.json"),
                ("Video review pre-rollback backup", "video_review_fewshot_memory.pre_rollback_*.json"),
                ("JSON", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not selected:
            return None
        backup_path = Path(selected)
        try:
            backup_payload = json.loads(backup_path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("\u89c6\u9891 few-shot \u56de\u6eda", f"\u8bfb\u53d6\u5907\u4efd\u5931\u8d25:\n{backup_path}\n\n{exc}")
            return None
        current_payload = get_video_review_fewshot_memory()
        now = datetime.now()
        preview = build_video_review_fewshot_memory_rollback_preview(
            backup_payload,
            current_payload,
            backup_name=backup_path.name,
            generated_at=now,
        )
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / build_video_review_fewshot_memory_rollback_report_filename(now)
        report_path.write_text(
            "\n".join(build_video_review_fewshot_memory_rollback_report_lines(preview)),
            encoding="utf-8",
        )
        summary = preview.get("summary", {}) if isinstance(preview.get("summary"), dict) else {}
        if preview.get("status") != "ready_to_restore":
            self.status_var.set(f"\u89c6\u9891 few-shot rollback blocked: {report_path.name}")
            messagebox.showwarning(
                "\u89c6\u9891 few-shot \u56de\u6eda",
                f"\u56de\u6eda\u88ab\u963b\u65ad\u3002\n\n\u62a5\u544a:\n{report_path}\n\n\u72b6\u6001: {preview.get('status', '-')}",
            )
            return report_path, None
        confirmed = messagebox.askyesno(
            "\u89c6\u9891 few-shot \u56de\u6eda",
            (
                "\u8fd9\u4f1a\u7528\u9009\u4e2d\u5907\u4efd\u6062\u590d Evaluation Agent \u89c6\u9891 few-shot \u6b63\u5f0f\u8bb0\u5fc6\u6c60\u3002\n\n"
                f"\u5907\u4efd:\n{backup_path}\n\n"
                f"\u5907\u4efd\u6837\u672c: {summary.get('backup_count', 0)}\n"
                f"\u5f53\u524d\u6837\u672c: {summary.get('current_count', 0)}\n"
                f"\u6062\u590d\u540e\u5dee\u503c: {summary.get('delta', 0)}\n\n"
                "\u7ee7\u7eed\uff1f"
            ),
        )
        if not confirmed:
            self.status_var.set(f"\u89c6\u9891 few-shot rollback cancelled: {report_path.name}")
            return report_path, None
        safety_backup_path: Path | None = None
        if VIDEO_REVIEW_FEWSHOT_MEMORY_FILE.exists():
            safety_backup_path = state_dir / f"video_review_fewshot_memory.pre_rollback_{now.strftime('%Y%m%d_%H%M%S')}.json"
            shutil.copy2(VIDEO_REVIEW_FEWSHOT_MEMORY_FILE, safety_backup_path)
        tmp_path = VIDEO_REVIEW_FEWSHOT_MEMORY_FILE.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(backup_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(VIDEO_REVIEW_FEWSHOT_MEMORY_FILE)
        invalidate_statsbomb_state_cache(VIDEO_REVIEW_FEWSHOT_MEMORY_FILE)
        self.status_var.set(f"\u89c6\u9891 few-shot rollback restored: {summary.get('backup_count', 0)} samples")
        self._refresh_current_view_after_release_state_change()
        messagebox.showinfo(
            "\u89c6\u9891 few-shot \u56de\u6eda",
            f"\u56de\u6eda\u5df2\u5b8c\u6210\u3002\n\n\u6062\u590d\u6765\u6e90:\n{backup_path}\n\n\u5b89\u5168\u5907\u4efd:\n{safety_backup_path or '-'}\n\n\u62a5\u544a:\n{report_path}",
        )
        return report_path, safety_backup_path

    def export_video_review_fewshot_memory_audit(self) -> Path:
        memory = get_video_review_fewshot_memory()
        monitor = build_video_review_fewshot_memory_monitor(memory, {})
        quality = build_video_review_fewshot_memory_quality_alerts(monitor)
        state_dir = VIDEO_REVIEW_FEWSHOT_MEMORY_FILE.parent
        backup_files = sorted(
            list(state_dir.glob("video_review_fewshot_memory.backup_*.json"))
            + list(state_dir.glob("video_review_fewshot_memory.pre_rollback_*.json")),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        backup_rows = [
            {
                "name": path.name,
                "size": path.stat().st_size,
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for path in backup_files[:20]
        ]
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        operation_files = sorted(
            list(REPORT_DIR.glob("video_review_fewshot_merge_applied_*.md"))
            + list(REPORT_DIR.glob("video_review_fewshot_memory_rollback_*.md")),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        operation_rows = [
            {
                "name": path.name,
                "type": "rollback" if "rollback" in path.name else "apply",
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for path in operation_files[:20]
        ]
        now = datetime.now()
        audit = build_video_review_fewshot_memory_audit_report(
            memory,
            monitor,
            quality,
            backup_rows=backup_rows,
            operation_rows=operation_rows,
            generated_at=now,
        )
        path = REPORT_DIR / build_video_review_fewshot_memory_audit_report_filename(now)
        path.write_text("\n".join(build_video_review_fewshot_memory_audit_report_lines(audit)), encoding="utf-8")
        summary = audit.get("summary", {}) if isinstance(audit.get("summary"), dict) else {}
        self.status_var.set(
            f"\u89c6\u9891 few-shot audit: samples {summary.get('sample_count', 0)} | backups {summary.get('backup_count', 0)} | alerts {summary.get('alert_count', 0)}"
        )
        messagebox.showinfo("\u89c6\u9891 few-shot \u5ba1\u8ba1", f"\u5df2\u751f\u6210\u5ba1\u8ba1\u62a5\u544a:\n{path}")
        return path

    def open_recovery_run_center(self) -> None:
        self.current_view = "recovery_runs"
        records = self._recovery_run_records(limit=80)
        summary = build_result_recovery_run_summary(records)
        quality_alerts = build_result_recovery_quality_alerts(records)
        run_rows = build_result_recovery_run_rows(records, limit=50)
        quality_trend = build_strategy_release_quality_trend(records)
        trend_alerts = build_strategy_release_quality_trend_alerts(quality_trend)
        admission_policy = get_strategy_admission_policy_status().get("policy", {})
        trend_tuning = build_strategy_release_trend_policy_tuning(
            quality_trend,
            trend_alerts,
            base_min_confidence=float(admission_policy.get("min_confidence", 0.5) or 0.5) if isinstance(admission_policy, dict) else 0.5,
            base_active_strategy_min=int(admission_policy.get("active_strategy_min", 1) or 1) if isinstance(admission_policy, dict) else 1,
            base_medium_risk_allowed=bool(admission_policy.get("medium_risk_allowed", True)) if isinstance(admission_policy, dict) else True,
        )
        policy_effect_review = build_strategy_policy_effect_review(
            get_strategy_admission_policy_history(limit=20),
            list(reversed(get_recent_settlements(limit=200))),
        )
        trend_tuning_effect = build_strategy_trend_tuning_effect_review(policy_effect_review)
        latest_status = str(summary.get("latest_status") or "")
        lookback_days = self._recovery_lookback_days()
        snapshot_audit = self._result_recovery_snapshot_audit(lookback_days=lookback_days)

        shell = self._page_shell(
            "\u56de\u6536\u8fd0\u884c\u8bb0\u5f55",
            "\u8bb0\u5f55\u6bcf\u6b21\u8d5b\u679c\u56de\u6536\u7684\u5f00\u59cb\u3001\u7ed3\u675f\u3001\u8017\u65f6\u3001\u65b0\u7ed3\u7b97\u548c\u5931\u8d25\u539f\u56e0",
        )

        header = tk.Frame(shell, bg=BG)
        header.pack(fill=tk.X, pady=(0, 16))
        auto_recovery_status = "开启" if self.auto_result_recovery_enabled.get() else "关闭"
        tk.Label(
            header,
            text=f"\u81ea\u52a8\u56de\u6536: {auto_recovery_status} / {self.auto_result_recovery_interval_min.get()}min",
            bg=BG,
            fg=GREEN if self.auto_result_recovery_enabled.get() else MUTED,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(side=tk.LEFT)
        refresh_button = tk.Button(
            header,
            text="\u56de\u6536\u8d5b\u679c",
            command=self.run_result_recovery,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        )
        self._register_result_recovery_button(refresh_button)
        refresh_button.pack(side=tk.RIGHT)
        tk.Button(
            header,
            text="\u5237\u65b0\u8bb0\u5f55",
            command=self.open_recovery_run_center,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        tk.Button(
            header,
            text="\u8fd4\u56de\u590d\u76d8\u4e2d\u5fc3",
            command=self.open_review_center,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))

        self._lookback_selector(shell)

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        for label, value, color in [
            ("\u8bb0\u5f55\u603b\u6570", str(summary.get("total", 0)), TEXT),
            ("\u6700\u8fd1\u72b6\u6001", str(summary.get("latest_status_label") or "-"), GREEN if latest_status == "success" else RED if latest_status == "failed" else YELLOW),
            ("\u8fd1 10 \u6b21\u6210\u529f\u7387", str(summary.get("recent_success_rate_text") or "-"), GREEN if float(summary.get("recent_success_rate") or 0) >= 0.8 else YELLOW),
            ("\u5e73\u5747\u8017\u65f6", str(summary.get("avg_elapsed_text") or "-"), "#7aa2ff"),
            ("\u7d2f\u8ba1\u65b0\u7ed3\u7b97", str(summary.get("total_new_settled", 0)), "#7aa2ff"),
            ("\u5931\u8d25\u6b21\u6570", str(summary.get("failed_count", 0)), RED if int(summary.get("failed_count", 0) or 0) else GREEN),
            ("\u8d28\u91cf\u544a\u8b66", str(len(quality_alerts)), RED if any(item.get("severity") == "high" for item in quality_alerts) else YELLOW if quality_alerts else GREEN),
            ("\u8d8b\u52bf\u544a\u8b66", str(len(trend_alerts)), RED if any(item.get("severity") == "high" for item in trend_alerts) else YELLOW if trend_alerts else GREEN),
        ]:
            self._detail_metric(top, label, value, color)

        audit_frame = tk.Frame(shell, bg=BG)
        audit_frame.pack(fill=tk.X, pady=(0, 16))
        for label, value, color in self._snapshot_audit_metrics(snapshot_audit):
            self._detail_metric(audit_frame, label, value, color)

        trend_metrics = quality_trend.get("metrics", []) if isinstance(quality_trend.get("metrics"), list) else []
        trend_metric_frame = tk.Frame(shell, bg=BG)
        trend_metric_frame.pack(fill=tk.X, pady=(0, 12))
        for metric in trend_metrics[:6]:
            if isinstance(metric, dict):
                self._detail_metric(
                    trend_metric_frame,
                    str(metric.get("label") or "-"),
                    str(metric.get("value") or "-"),
                    self._tone_color(str(metric.get("tone") or "neutral")),
                )

        trend_rows = quality_trend.get("rows", []) if isinstance(quality_trend.get("rows"), list) else []
        trend_card = self._card(shell, PANEL)
        trend_card.pack(fill=tk.X, pady=(0, 16))
        tk.Label(
            trend_card,
            text="\u7b56\u7565\u653e\u884c\u8d28\u91cf\u8d8b\u52bf",
            bg=PANEL,
            fg=TEXT,
            font=("Microsoft YaHei UI", 13, "bold"),
        ).pack(anchor=tk.W, padx=18, pady=(16, 6))
        tk.Label(
            trend_card,
            text=str(quality_trend.get("summary_text") or "-"),
            bg=PANEL,
            fg=MUTED,
            font=("Microsoft YaHei UI", 10),
            wraplength=980,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=18, pady=(0, 8))
        if trend_alerts:
            for alert in trend_alerts[:4]:
                self._alert_card(
                    trend_card,
                    str(alert.get("title") or "-"),
                    str(alert.get("body") or "-"),
                    tone=str(alert.get("tone") or "warning"),
                )
        tuning_reasons = trend_tuning.get("reasons", []) if isinstance(trend_tuning.get("reasons"), list) else []
        tuning_body = "\n".join(str(item) for item in tuning_reasons[:4]) or "-"
        if str(trend_tuning.get("action") or "") == "tighten":
            self._strategy_row(
                trend_card,
                f"\u95e8\u63a7\u8054\u52a8: {trend_tuning.get('label', '-')}",
                tuning_body,
                command=lambda tuning=trend_tuning: self.apply_strategy_allowlist_tuning(tuning),
            )
            tk.Button(
                trend_card,
                text="\u5e94\u7528\u8d8b\u52bf\u95e8\u63a7\u5efa\u8bae",
                command=lambda tuning=trend_tuning: self.apply_strategy_allowlist_tuning(tuning),
                bg=YELLOW,
                fg="#10141f",
                activebackground="#f7c948",
                activeforeground="#10141f",
                relief=tk.FLAT,
                font=("Microsoft YaHei UI", 10, "bold"),
                padx=14,
                pady=7,
            ).pack(anchor=tk.E, padx=18, pady=(0, 12))
        else:
            self._strategy_row(trend_card, f"\u95e8\u63a7\u8054\u52a8: {trend_tuning.get('label', '-')}", tuning_body)
        self._strategy_row(
            trend_card,
            f"\u95e8\u63a7\u751f\u6548\u590d\u76d8: {trend_tuning_effect.get('label', '-')}",
            (
                f"{trend_tuning_effect.get('summary_text', '-')}\n"
                f"{trend_tuning_effect.get('recommendation_text', '-')}"
            ),
            command=lambda review=policy_effect_review: self.open_policy_effect_detail_window(review),
        )
        self._strategy_row(
            trend_card,
            f"\u56de\u6eda\u4fee\u590d\u8ddf\u8e2a: {rollback_effect.get('label', '-')}",
            (
                f"{rollback_effect.get('summary_text', '-')}\n"
                f"{rollback_effect.get('recommendation_text', '-')}"
            ),
            command=lambda review=policy_effect_review: self.open_policy_effect_detail_window(review),
        )
        if trend_rows:
            for row in trend_rows[:3]:
                if isinstance(row, dict):
                    self._strategy_row(trend_card, str(row.get("title") or "-"), str(row.get("body") or "-"))
        else:
            self._strategy_row(trend_card, "\u6682\u65e0\u8d8b\u52bf\u6837\u672c", "\u5b8c\u6210\u591a\u6b21\u8d5b\u679c\u56de\u6536\u540e\uff0c\u8fd9\u91cc\u4f1a\u5c55\u793a\u653e\u884c\u547d\u4e2d\u3001\u5b9e\u76d8\u53cd\u9988\u548c\u65ad\u8def\u6062\u590d\u8d8b\u52bf\u3002")

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u6700\u8fd1\u8fd0\u884c", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        if quality_alerts:
            for alert in quality_alerts[:3]:
                self._alert_card(left, str(alert.get("title") or "-"), str(alert.get("body") or "-"), tone=str(alert.get("tone") or "warning"))
        listbox = tk.Listbox(
            left,
            bg=PANEL,
            fg=TEXT,
            selectbackground=BLUE,
            selectforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10),
            activestyle="none",
        )
        listbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        tk.Label(right, text="\u8fd0\u884c\u8be6\u60c5", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        detail = tk.Text(
            right,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            height=18,
        )
        detail.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 14))
        selected_recovery_record: dict[str, object] = {}
        apply_adjustment_button = tk.Button(
            right,
            text="\u5e94\u7528\u672c\u6b21\u6536\u7d27\u5efa\u8bae",
            command=lambda: self._apply_recovery_strategy_adjustment(selected_recovery_record),
            bg=YELLOW,
            fg="#10141f",
            activebackground="#f7c948",
            activeforeground="#10141f",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=7,
            state=tk.DISABLED,
        )
        apply_adjustment_button.pack(anchor=tk.E, padx=18, pady=(0, 14))

        def show_detail(index: int) -> None:
            detail.configure(state=tk.NORMAL)
            detail.delete("1.0", tk.END)
            selected_recovery_record.clear()
            if not run_rows:
                detail.insert(tk.END, "\u6682\u65e0\u56de\u6536\u8fd0\u884c\u8bb0\u5f55\u3002\u70b9\u51fb\u201c\u56de\u6536\u8d5b\u679c\u201d\u540e\uff0c\u8fd9\u91cc\u4f1a\u4fdd\u7559\u6267\u884c\u8fc7\u7a0b\u548c\u7ed3\u679c\u3002")
            elif index < 0 or index >= len(run_rows):
                record = run_rows[0].get("record", {})
                selected_recovery_record.update(record if isinstance(record, dict) else {})
                detail.insert(tk.END, build_result_recovery_run_detail(record))
            else:
                record = run_rows[index].get("record", {})
                selected_recovery_record.update(record if isinstance(record, dict) else {})
                detail.insert(tk.END, build_result_recovery_run_detail(record))
            detail.configure(state=tk.DISABLED)
            adjustment = self._strategy_adjustment_from_recovery_record(selected_recovery_record)
            apply_adjustment_button.configure(
                state=tk.NORMAL if str(adjustment.get("action") or "") == "tighten" else tk.DISABLED
            )

        for row in run_rows:
            listbox.insert(tk.END, str(row.get("title") or "-"))
        if run_rows:
            listbox.selection_set(0)
            show_detail(0)
        else:
            listbox.insert(tk.END, "\u6682\u65e0\u56de\u6536\u8fd0\u884c\u8bb0\u5f55")
            show_detail(0)

        def on_select(_event=None) -> None:
            selection = listbox.curselection()
            if selection and run_rows:
                show_detail(int(selection[0]))

        listbox.bind("<<ListboxSelect>>", on_select)

    def run_result_recovery(self, trigger: str = "manual_ui", show_popup: bool = True) -> None:
        if self.result_recovery_running:
            message = "\u8d5b\u679c\u56de\u6536\u6b63\u5728\u8fd0\u884c\uff0c\u8bf7\u7b49\u5f53\u524d\u4efb\u52a1\u5b8c\u6210\u3002"
            self.status_var.set(message)
            self._log_event("INFO", message)
            return
        self.result_recovery_running = True
        self._set_result_recovery_controls_state()
        self._begin_result_recovery_run_record(trigger=trigger)
        self.status_var.set("\u6b63\u5728\u56de\u6536\u8d5b\u679c...")
        self._log_event("INFO", f"\u5f00\u59cb\u56de\u6536\u8d5b\u679c: {trigger}")
        prediction_cache = {row.match.match_id: row.prediction for row in self.rows}
        lookback_days = self._recovery_lookback_days()
        if getattr(self, "current_view", "") == "recovery_runs":
            self.open_recovery_run_center()

        task = self.background_tasks.submit(
            key="result_recovery",
            label="\u8d5b\u679c\u81ea\u52a8\u56de\u6536",
            func=auto_settle_finished_matches,
            kwargs={"prediction_cache": prediction_cache, "lookback_days": lookback_days},
            mode="thread",
            group="recovery",
            priority=20,
            max_retries=1,
            metadata={"trigger": trigger, "lookback_days": lookback_days, "group": "recovery", "priority": 20},
            on_success=lambda result, record: self._finish_result_recovery(
                result if isinstance(result, dict) else {},
                float(record.elapsed_seconds or 0.0),
                show_popup=show_popup,
            ),
            on_error=lambda exc, record: self._finish_result_recovery_error(
                exc,
                float(record.elapsed_seconds or 0.0),
                show_popup=show_popup,
            ),
        )
        if task is None:
            self.result_recovery_running = False
            self._set_result_recovery_controls_state()
            message = "\u8d5b\u679c\u56de\u6536\u4efb\u52a1\u5df2\u5728\u540e\u53f0\u961f\u5217\u4e2d\u8fd0\u884c\u3002"
            self.status_var.set(message)
            self._log_event("INFO", message)

    def _finish_result_recovery(self, result: dict, elapsed: float, show_popup: bool = True) -> None:
        new_settled = int(result.get("new_settled", 0) or 0)
        fetched = int(result.get("fetched_finished", 0) or 0)
        restored = int(result.get("restored_snapshots", 0) or 0)
        source = str(result.get("source", "-"))
        self._finish_result_recovery_run_record(status="success", result=result, elapsed=elapsed)
        self.result_recovery_running = False
        self._set_result_recovery_controls_state()
        report_path: Path | None = None
        report_loop: dict[str, object] = {}
        try:
            report_path, report_loop = self._write_strategy_release_recovery_loop_report()
            self._attach_strategy_release_loop_report_to_recovery_run(report_path, report_loop)
        except Exception as exc:
            self._log_event("ERROR", f"\u653e\u884c\u56de\u6536\u95ed\u73af\u62a5\u544a\u81ea\u52a8\u751f\u6210\u5931\u8d25: {exc}")
        report_suffix = f" | \u95ed\u73af\u62a5\u544a {report_path.name}" if report_path is not None else ""
        statsbomb_repair_feedback_text = self._rebuild_statsbomb_review_samples_after_recovery(result)
        message = f"\u8d5b\u679c\u56de\u6536\u5b8c\u6210: \u5b8c\u573a {fetched} | \u4fee\u590d\u5feb\u7167 {restored} | \u65b0\u7ed3\u7b97 {new_settled} | \u6570\u636e\u6e90 {source} | \u8017\u65f6 {elapsed:.2f}s{report_suffix}"
        self.status_var.set(message)
        self._log_event("OK", message)
        self.summary_vars["hit_rate"].set(self._historical_hit_rate())
        self._refresh_current_view_after_release_state_change()
        detail = "\n".join(str(item) for item in result.get("messages", []) if item) or message
        review_summary = build_result_recovery_review_summary(result.get("items", []) if isinstance(result.get("items"), list) else [])
        if int(review_summary.get("settlement_count", 0) or 0) > 0:
            detail = f"{detail}\n\n\u672c\u8f6e\u590d\u76d8:\n{review_summary.get('summary_text') or '-'}"
        live_feedback_validation = (
            self.result_recovery_run_record.get("live_feedback_validation")
            if isinstance(self.result_recovery_run_record, dict)
            and isinstance(self.result_recovery_run_record.get("live_feedback_validation"), dict)
            else {}
        )
        if live_feedback_validation:
            detail = f"{detail}\n\n\u5b9e\u76d8\u53cd\u9988\u9a8c\u8bc1:\n{live_feedback_validation.get('summary_text') or '-'}"
        if report_path is not None:
            detail = f"{detail}\n\n\u653e\u884c\u56de\u6536\u95ed\u73af\u62a5\u544a:\n{report_path}"
        if statsbomb_repair_feedback_text:
            detail = f"{detail}\n\nStatsBomb/Event Proxy 修复闭环:\n{statsbomb_repair_feedback_text}"
        self._schedule_auto_result_recovery()
        if show_popup:
            messagebox.showinfo("\u8d5b\u679c\u56de\u6536", detail)

    def _finish_result_recovery_error(self, exc: Exception, elapsed: float = 0.0, show_popup: bool = True) -> None:
        self._finish_result_recovery_run_record(status="failed", elapsed=elapsed, error=exc)
        self.result_recovery_running = False
        self._set_result_recovery_controls_state()
        self.status_var.set(f"\u8d5b\u679c\u56de\u6536\u5931\u8d25: {exc}")
        self._log_event("ERROR", f"\u8d5b\u679c\u56de\u6536\u5931\u8d25: {exc}")
        self._schedule_auto_result_recovery()
        if show_popup:
            messagebox.showerror("\u8d5b\u679c\u56de\u6536\u5931\u8d25", str(exc))

    def _strategy_adjustment_from_recovery_record(self, record: dict | object) -> dict:
        if not isinstance(record, dict):
            return {}
        review_summary = record.get("review_summary")
        if not isinstance(review_summary, dict):
            return {}
        adjustment = review_summary.get("strategy_adjustment")
        return dict(adjustment) if isinstance(adjustment, dict) else {}

    def _apply_recovery_strategy_adjustment(self, record: dict | object) -> None:
        adjustment = self._strategy_adjustment_from_recovery_record(record)
        if str(adjustment.get("action") or "") != "tighten":
            messagebox.showinfo("\u56de\u6536\u7b56\u7565\u5efa\u8bae", "\u5f53\u524d\u56de\u6536\u8bb0\u5f55\u6ca1\u6709\u53ef\u5e94\u7528\u7684\u6536\u7d27\u5efa\u8bae\u3002")
            return
        if not isinstance(adjustment.get("policy_update"), dict) or not adjustment.get("policy_update"):
            current = get_strategy_admission_policy_status().get("policy", {})
            review_summary = record.get("review_summary") if isinstance(record, dict) else {}
            adjustment = build_result_recovery_strategy_adjustment(
                review_summary if isinstance(review_summary, dict) else {},
                base_min_confidence=float(current.get("min_confidence", 0.5) or 0.5) if isinstance(current, dict) else 0.5,
                base_active_strategy_min=int(current.get("active_strategy_min", 1) or 1) if isinstance(current, dict) else 1,
                base_medium_risk_allowed=bool(current.get("medium_risk_allowed", True)) if isinstance(current, dict) else True,
            )
        self.apply_strategy_allowlist_tuning(adjustment)

    def _settlement_summary(self, settlements: list[dict]) -> dict[str, str | int]:
        return {
            "total": len(settlements),
            "one_x_two": self._hit_rate_text(settlements, "is_correct"),
            "handicap": self._hit_rate_text(settlements, "handicap_is_correct"),
            "ou": self._hit_rate_text(settlements, "ou_is_correct"),
        }

    def open_accuracy_diagnostics(self) -> None:
        self.current_view = "accuracy"
        settlements = list(reversed(get_recent_settlements(limit=200)))
        diagnostics = self._accuracy_diagnostics(settlements)
        shell = self._page_shell(
            "\u51c6\u786e\u7387\u8bca\u65ad",
            "\u6309\u7f6e\u4fe1\u5ea6\u3001\u9884\u6d4b\u65b9\u5411\u3001\u73a9\u6cd5\u548c\u8054\u8d5b\u62c6\u89e3\u5386\u53f2\u547d\u4e2d\u7387",
        )
        header = tk.Frame(shell, bg=BG)
        header.pack(fill=tk.X, pady=(0, 16))
        tk.Button(
            header,
            text="\u8fd4\u56de\u590d\u76d8\u4e2d\u5fc3",
            command=self.open_review_center,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT)

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        for label, value, color in [
            ("\u6837\u672c\u6570", str(diagnostics["sample_count"]), TEXT),
            ("\u603b\u4f53 1X2", diagnostics["overall"], "#7aa2ff"),
            ("\u9ad8\u7f6e\u4fe1 1X2", diagnostics["high_conf"], RED if diagnostics["high_conf_is_weak"] else GREEN),
            ("\u4f18\u5316\u91cd\u70b9", diagnostics["priority"], YELLOW),
        ]:
            self._detail_metric(top, label, str(value), color)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u5206\u5c42\u547d\u4e2d\u7387", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        for title, rows in [
            ("\u7f6e\u4fe1\u5ea6", diagnostics["confidence"]),
            ("\u9884\u6d4b\u65b9\u5411", diagnostics["direction"]),
            ("\u8d5b\u679c\u7c7b\u578b", diagnostics["result"]),
        ]:
            self._strategy_row(left, title, "\n".join(rows) if rows else "\u6682\u65e0\u6837\u672c")

        tk.Label(right, text="\u73a9\u6cd5\u4e0e\u8054\u8d5b", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        self._strategy_row(right, "\u73a9\u6cd5\u547d\u4e2d", "\n".join(diagnostics["plays"]) if diagnostics["plays"] else "\u6682\u65e0\u6837\u672c")
        self._strategy_row(right, "\u8054\u8d5b Top 6", "\n".join(diagnostics["leagues"]) if diagnostics["leagues"] else "\u6682\u65e0\u6837\u672c")
        self._strategy_row(right, "\u8bca\u65ad\u7ed3\u8bba", diagnostics["conclusion"])

    def _accuracy_diagnostics(self, settlements: list[dict]) -> dict[str, object]:
        recent = [item for item in settlements[:200] if isinstance(item, dict)]
        confidence_groups = {
            "\u9ad8\u7f6e\u4fe1 >=60%": lambda item: float(item.get("prediction_confidence", 0) or 0) >= 0.6,
            "\u4e2d\u7f6e\u4fe1 45%-60%": lambda item: 0.45 <= float(item.get("prediction_confidence", 0) or 0) < 0.6,
            "\u4f4e\u7f6e\u4fe1 <45%": lambda item: float(item.get("prediction_confidence", 0) or 0) < 0.45,
        }
        direction_groups = {
            "\u4e3b\u80dc": lambda item: item.get("predicted") == "\u4e3b\u80dc",
            "\u5e73\u5c40": lambda item: item.get("predicted") == "\u5e73\u5c40",
            "\u5ba2\u80dc": lambda item: item.get("predicted") == "\u5ba2\u80dc",
        }
        result_groups = {
            "\u5b9e\u9645\u4e3b\u80dc": lambda item: item.get("result") == "\u4e3b\u80dc",
            "\u5b9e\u9645\u5e73\u5c40": lambda item: item.get("result") == "\u5e73\u5c40",
            "\u5b9e\u9645\u5ba2\u80dc": lambda item: item.get("result") == "\u5ba2\u80dc",
        }
        plays = [
            ("1X2", "is_correct"),
            ("\u8ba9\u7403", "handicap_is_correct"),
            ("\u5927\u5c0f\u7403", "ou_is_correct"),
            ("\u6bd4\u5206", "score_is_correct"),
        ]
        confidence_rows = self._diagnostic_group_rows(recent, confidence_groups, "is_correct")
        direction_rows = self._diagnostic_group_rows(recent, direction_groups, "is_correct")
        result_rows = self._diagnostic_group_rows(recent, result_groups, "is_correct")
        play_rows = [self._diagnostic_row(label, recent, key) for label, key in plays]
        league_rows = self._league_diagnostic_rows(recent)
        high_conf_items = [item for item in recent if confidence_groups["\u9ad8\u7f6e\u4fe1 >=60%"](item)]
        high_conf_rate = self._hit_rate_value(high_conf_items, "is_correct")
        weakest_play = self._weakest_diagnostic(play_rows)
        priority = self._accuracy_priority(high_conf_rate, weakest_play)
        return {
            "sample_count": len(recent),
            "overall": self._hit_rate_text(recent, "is_correct"),
            "high_conf": self._hit_rate_text(high_conf_items, "is_correct"),
            "high_conf_is_weak": high_conf_rate is not None and high_conf_rate < 0.5,
            "priority": priority,
            "confidence": confidence_rows,
            "direction": direction_rows,
            "result": result_rows,
            "plays": play_rows,
            "leagues": league_rows,
            "conclusion": self._accuracy_conclusion(high_conf_rate, weakest_play, confidence_rows, direction_rows),
        }

    def _diagnostic_group_rows(self, items: list[dict], groups: dict[str, object], key: str) -> list[str]:
        rows: list[str] = []
        for label, predicate in groups.items():
            group_items = [item for item in items if predicate(item)]
            rows.append(self._diagnostic_row(label, group_items, key))
        return rows

    def _diagnostic_row(self, label: str, items: list[dict], key: str) -> str:
        values = [bool(item.get(key)) for item in items if item.get(key) is not None]
        if not values:
            return f"{label}: - / 0\u573a"
        rate = sum(1 for value in values if value) / len(values)
        return f"{label}: {rate:.1%} / {len(values)}\u573a"

    def _hit_rate_value(self, items: list[dict], key: str) -> float | None:
        values = [bool(item.get(key)) for item in items if item.get(key) is not None]
        if not values:
            return None
        return sum(1 for value in values if value) / len(values)

    def _league_diagnostic_rows(self, items: list[dict]) -> list[str]:
        buckets: dict[str, list[dict]] = {}
        for item in items:
            league = str(item.get("league") or "-")
            buckets.setdefault(league, []).append(item)
        rows = []
        for league, league_items in sorted(buckets.items(), key=lambda pair: len(pair[1]), reverse=True)[:6]:
            rows.append(self._diagnostic_row(league, league_items, "is_correct"))
        return rows

    def _weakest_diagnostic(self, rows: list[str]) -> str:
        weakest = "-"
        weakest_rate = 2.0
        for row in rows:
            try:
                label, rest = row.split(":", 1)
                rate_text = rest.strip().split("/", 1)[0].strip().rstrip("%")
                rate = float(rate_text) / 100
            except Exception:
                continue
            if rate < weakest_rate:
                weakest_rate = rate
                weakest = label
        return weakest

    def _accuracy_priority(self, high_conf_rate: float | None, weakest_play: str) -> str:
        if high_conf_rate is not None and high_conf_rate < 0.5:
            return "\u91cd\u6821\u51c6\u7f6e\u4fe1\u5ea6"
        if weakest_play == "\u6bd4\u5206":
            return "\u964d\u4f4e\u6bd4\u5206\u6743\u91cd"
        if weakest_play == "\u5927\u5c0f\u7403":
            return "\u4fee\u6b63\u8fdb\u7403\u671f\u671b"
        if weakest_play == "\u8ba9\u7403":
            return "\u590d\u6838\u76d8\u53e3\u6743\u91cd"
        return "\u5206\u8054\u8d5b\u8c03\u6743"

    def _accuracy_conclusion(
        self,
        high_conf_rate: float | None,
        weakest_play: str,
        confidence_rows: list[str],
        direction_rows: list[str],
    ) -> str:
        parts = []
        if high_conf_rate is not None and high_conf_rate < 0.5:
            parts.append("\u9ad8\u7f6e\u4fe1\u6837\u672c\u547d\u4e2d\u7387\u4e0d\u8db3\uff0c\u8bf4\u660e\u5f53\u524d\u7f6e\u4fe1\u5ea6\u8fd8\u6ca1\u6709\u5f62\u6210\u6709\u6548\u7684\u8fc7\u6ee4\u80fd\u529b\u3002")
        if weakest_play != "-":
            parts.append(f"\u6700\u5f31\u73a9\u6cd5\u662f {weakest_play}\uff0c\u5e94\u5148\u964d\u6743\u6216\u6539\u4e3a\u8f85\u52a9\u53c2\u8003\u3002")
        parts.append("\u4e0b\u4e00\u6b65\u5efa\u8bae\u4e0d\u662f\u6269\u5927\u9884\u6d4b\u8f93\u51fa\uff0c\u800c\u662f\u5148\u6309\u5206\u5c42\u7ed3\u679c\u8bbe\u7f6e\u8fc7\u6ee4\u95e8\u69db\u3002")
        return "\n".join(parts)

    def _settlement_trend_summary(self, settlements: list[dict]) -> dict[str, object]:
        recent = settlements[:80]
        if not recent:
            return {
                "top_bias": "-",
                "weakest_play": "-",
                "high_conf_misses": 0,
                "priority": "\u7b49\u5f85\u6837\u672c",
            }

        bias_counter: Counter[str] = Counter()
        for item in recent:
            for tag in self._settlement_bias_tags(item):
                if tag != "\u65e0\u660e\u663e\u504f\u5dee":
                    bias_counter[tag] += 1
        top_bias = "-"
        if bias_counter:
            tag, count = bias_counter.most_common(1)[0]
            top_bias = f"{tag} {count}\u6b21"

        play_keys = [
            ("1X2", "is_correct"),
            ("\u8ba9\u7403", "handicap_is_correct"),
            ("\u5927\u5c0f\u7403", "ou_is_correct"),
            ("\u6bd4\u5206", "score_is_correct"),
        ]
        weakest_play = "-"
        weakest_rate = 1.1
        for label, key in play_keys:
            values = [bool(item.get(key)) for item in recent if isinstance(item, dict) and item.get(key) is not None]
            if not values:
                continue
            rate = sum(1 for value in values if value) / len(values)
            if rate < weakest_rate:
                weakest_rate = rate
                weakest_play = f"{label} {rate:.1%}"

        high_conf_misses = sum(
            1
            for item in recent
            if item.get("is_correct") is False and float(item.get("prediction_confidence", 0) or 0) >= 0.6
        )
        priority = self._trend_priority_text(top_bias, weakest_play, high_conf_misses)
        return {
            "top_bias": top_bias,
            "weakest_play": weakest_play,
            "high_conf_misses": high_conf_misses,
            "priority": priority,
        }

    def _trend_priority_text(self, top_bias: str, weakest_play: str, high_conf_misses: int) -> str:
        if high_conf_misses:
            return "\u964d\u4f4e\u9ad8\u7f6e\u4fe1\u5355\u5411\u6743\u91cd"
        if "\u5927\u5c0f\u7403" in weakest_play or "\u8fdb\u7403" in top_bias:
            return "\u4f18\u5316\u603b\u8fdb\u7403\u671f\u671b"
        if "\u8ba9\u7403" in weakest_play or "\u8ba9\u7403" in top_bias:
            return "\u590d\u6838\u8ba9\u7403\u76d8\u4e00\u81f4\u6027"
        if "\u5e73\u5c40" in top_bias:
            return "\u589e\u52a0\u5e73\u5c40\u4fdd\u62a4"
        if "\u6bd4\u5206" in weakest_play or "\u6bd4\u5206" in top_bias:
            return "\u964d\u4f4e\u7cbe\u786e\u6bd4\u5206\u6743\u91cd"
        return "\u7ef4\u6301\u5f53\u524d\u6743\u91cd"

    def _hit_rate_text(self, settlements: list[dict], key: str) -> str:
        values = [bool(item.get(key)) for item in settlements if isinstance(item, dict) and item.get(key) is not None]
        if not values:
            return "-"
        return f"{sum(1 for value in values if value) / len(values):.1%}"

    def _settlement_line(self, item: dict) -> str:
        hit = "\u547d\u4e2d" if item.get("is_correct") else "\u5931\u8bef"
        prefix = "\u653e\u884c | " if str(item.get("strategy_allowlist_decision") or "") == "allow" else ""
        return (
            f"{prefix}{item.get('match_date', '-')} {item.get('league', '-')} | "
            f"{item.get('home_team', '-')} {item.get('home_goals', '-')}-{item.get('away_goals', '-')} {item.get('away_team', '-')} | "
            f"\u9884\u6d4b {item.get('predicted', '-')} | {hit} | {_pct1(item.get('prediction_confidence'))}"
        )

    def _settlement_table_values(self, item: dict) -> tuple[str, str, str, str, str, str, str, str]:
        hit = "\u547d\u4e2d" if item.get("is_correct") is True else "\u5931\u8bef" if item.get("is_correct") is False else "-"
        match = f"{item.get('home_team', '-')} vs {item.get('away_team', '-')}"
        if str(item.get("strategy_allowlist_decision") or "") == "allow":
            match = f"\u653e\u884c | {match}"
        return (
            str(item.get("match_date") or "-"),
            str(item.get("league") or "-"),
            match,
            f"{item.get('home_goals', '-')}-{item.get('away_goals', '-')}",
            str(item.get("predicted") or "-"),
            str(item.get("result") or "-"),
            hit,
            _pct1(item.get("prediction_confidence")),
        )

    def _hit_label(self, value: object) -> str:
        if value is True:
            return "\u547d\u4e2d"
        if value is False:
            return "\u5931\u8bef"
        return "\u65e0\u9884\u6d4b"

    def _settlement_bias_tags(self, item: dict) -> list[str]:
        tags: list[str] = []
        confidence = float(item.get("prediction_confidence", 0) or 0)
        if item.get("is_correct") is False and confidence >= 0.6:
            tags.append("\u9ad8\u7f6e\u4fe1\u65b9\u5411\u9519\u8bef")
        if item.get("is_correct") is False and item.get("result") == "\u5e73\u5c40":
            tags.append("\u5e73\u5c40\u98ce\u9669\u4f4e\u4f30")
        if item.get("ou_is_correct") is False:
            tags.append("\u8fdb\u7403\u8282\u594f\u504f\u5dee")
        if item.get("handicap_is_correct") is False:
            tags.append("\u8ba9\u7403\u76d8\u504f\u5dee")
        if item.get("score_is_correct") is False and float(item.get("score_confidence", 0) or 0) >= 0.1:
            tags.append("\u6bd4\u5206\u8def\u5f84\u504f\u5dee")
        if not tags:
            tags.append("\u65e0\u660e\u663e\u504f\u5dee")
        return tags

    def _settlement_review_suggestions(self, tags: list[str]) -> list[str]:
        suggestions: list[str] = []
        if "\u9ad8\u7f6e\u4fe1\u65b9\u5411\u9519\u8bef" in tags:
            suggestions.append("\u964d\u4f4e\u7c7b\u4f3c\u573a\u6b21\u7684\u5355\u4e00\u65b9\u5411\u6743\u91cd\uff0c\u4f18\u5148\u68c0\u67e5\u4e34\u573a\u4f24\u505c\u548c\u76d8\u53e3\u80cc\u79bb\u3002")
        if "\u5e73\u5c40\u98ce\u9669\u4f4e\u4f30" in tags:
            suggestions.append("\u589e\u52a0\u5747\u52bf\u6bd4\u8d5b\u7684\u5e73\u5c40\u4fdd\u62a4\u89c4\u5219\uff0c\u5f53\u80dc\u5e73\u8d1f\u6982\u7387\u5dee\u8ddd\u5c0f\u65f6\u81ea\u52a8\u964d\u6743\u3002")
        if "\u8fdb\u7403\u8282\u594f\u504f\u5dee" in tags:
            suggestions.append("\u590d\u6838\u5927\u5c0f\u7403\u6a21\u5757\u7684\u603b\u8fdb\u7403\u671f\u671b\uff0c\u628a\u8054\u8d5b\u8282\u594f\u548c\u8fd1\u671f\u653b\u9632\u72b6\u6001\u52a0\u5165\u6743\u91cd\u3002")
        if "\u8ba9\u7403\u76d8\u504f\u5dee" in tags:
            suggestions.append("\u68c0\u67e5\u8ba9\u7403\u7ebf\u548c\u6a21\u578b\u80dc\u5dee\u7684\u4e00\u81f4\u6027\uff0c\u76d8\u53e3\u4e0e\u6a21\u578b\u76f8\u53cd\u65f6\u6807\u8bb0\u4e3a\u89c2\u671b\u3002")
        if "\u6bd4\u5206\u8def\u5f84\u504f\u5dee" in tags:
            suggestions.append("\u6bd4\u5206\u53ea\u4f5c\u4e3a\u8f85\u52a9\u8def\u5f84\uff0c\u9ad8\u5206\u6563\u573a\u6b21\u4e0d\u5e94\u8f93\u51fa\u8fc7\u5f3a\u7684\u7cbe\u786e\u6bd4\u5206\u7ed3\u8bba\u3002")
        if not suggestions:
            suggestions.append("\u4fdd\u7559\u5f53\u524d\u7b56\u7565\u6743\u91cd\uff0c\u6301\u7eed\u7d2f\u79ef\u6837\u672c\u540e\u518d\u8c03\u6574\u3002")
        return suggestions

    def _settlement_review_text(self, item: dict) -> str:
        tags = self._settlement_bias_tags(item)
        suggestions = self._settlement_review_suggestions(tags)
        actual_score = f"{item.get('home_goals', '-')}-{item.get('away_goals', '-')}"
        video_review = item.get("video_review") if isinstance(item.get("video_review"), dict) else {}
        video_agent = video_review.get("agent_review") if isinstance(video_review.get("agent_review"), dict) else {}
        video_payload = video_review.get("video") if isinstance(video_review.get("video"), dict) else {}
        visual_analysis = video_review.get("visual_analysis") if isinstance(video_review.get("visual_analysis"), dict) else {}
        narrative = video_agent.get("narrative_review") if isinstance(video_agent.get("narrative_review"), dict) else {}
        event_hypotheses = video_agent.get("event_hypotheses") if isinstance(video_agent.get("event_hypotheses"), list) else []
        video_followup = video_agent.get("recommended_followup") if isinstance(video_agent.get("recommended_followup"), dict) else {}
        manual_annotations = video_review.get("manual_annotations") if isinstance(video_review.get("manual_annotations"), list) else []
        video_source_type = str(video_payload.get("source_type") or "local_file")
        video_source_name = str(video_payload.get("source_name") or "-")
        video_url = str(video_payload.get("url") or "")
        video_source_lines = [
            f"- \u6765\u6e90\u7c7b\u578b: {video_source_type}",
            f"- \u6765\u6e90\u540d\u79f0: {video_source_name}",
        ]
        if video_url:
            video_source_lines.append(f"- \u56de\u653e\u94fe\u63a5: {video_url}")
        video_hypothesis_lines = [
            f"- 事件假设: {item.get('code') or '-'} | {_pct1(item.get('confidence'))} | {item.get('title') or '-'}"
            for item in event_hypotheses[:3]
            if isinstance(item, dict)
        ]
        video_annotation_lines = [
            (
                f"- 人工标注: {item.get('event_label') or item.get('event_type') or '-'} | "
                f"frame {item.get('frame_index') if item.get('frame_index') is not None else '-'} | "
                f"{item.get('timestamp_seconds') if item.get('timestamp_seconds') is not None else '-'}s | "
                f"{item.get('note') or '-'}"
            )
            for item in manual_annotations[-5:]
            if isinstance(item, dict)
        ]
        if video_review:
            video_lines = [
                "",
                "AI 视频复盘",
                f"- 状态: {video_agent.get('status') or '-'} / {video_agent.get('vision_model_status') or '-'}",
                f"- 视频: {video_payload.get('filename') or '-'}",
                *video_source_lines,
                f"- 抽帧: {len(video_review.get('frames') or [])} 已生成 / {len(video_review.get('frame_plan') or [])} 计划",
                f"- 视觉证据: {visual_analysis.get('summary_text') or video_agent.get('visual_summary') or '-'}",
                f"- 证据强度: {video_agent.get('evidence_level') or '-'} / {_pct1(video_agent.get('evidence_score'))}",
                f"- 关键帧: {len(visual_analysis.get('key_frames') or []) if isinstance(visual_analysis.get('key_frames'), list) else video_agent.get('key_frame_count') or 0}",
                f"- 复盘结论: {narrative.get('summary_text') or video_agent.get('narrative_summary') or '-'}",
                f"- 处理建议: {video_followup.get('message') or narrative.get('recommendation') or '-'}",
                f"- 预测对齐: {video_agent.get('prediction_alignment') or '-'}",
                f"- 视频归因: {', '.join(video_agent.get('error_causes') or []) if isinstance(video_agent.get('error_causes'), list) else '-'}",
                *video_hypothesis_lines,
                *video_annotation_lines,
            ]
        else:
            video_lines = [
                "",
                "AI 视频复盘",
                "- 暂无本场视频复盘。可导入本地录像/集锦后，由 VideoReview Agent 生成抽帧计划和复盘归因。",
            ]
        statsbomb_proxy_lines = ["", *build_statsbomb_event_proxy_review_text(item).splitlines()]
        allowlist_lines: list[str] = []
        if str(item.get("strategy_allowlist_decision") or "") == "allow":
            allowlist_lines = [
                "",
                "\u7b56\u7565\u653e\u884c\u95ed\u73af",
                f"- \u653e\u884c\u6e05\u5355: {item.get('strategy_allowlist_file') or '-'}",
                f"- \u5bfc\u51fa\u65f6\u95f4: {item.get('strategy_allowlist_exported_at') or '-'}",
                f"- \u653e\u884c\u7ed3\u679c: {self._hit_label(item.get('is_correct'))}",
                f"- \u9ad8\u51c6\u7b56\u7565: {item.get('high_accuracy_strategy_summary') or '-'}",
                f"- \u5f71\u5b50\u89c2\u5bdf: {item.get('high_accuracy_strategy_shadow_summary') or '-'}",
            ]
        lines = [
            "\u8d5b\u524d\u5feb\u7167",
            f"- \u8d5b\u4e8b: {item.get('home_team', '-')} vs {item.get('away_team', '-')}",
            f"- \u8054\u8d5b: {item.get('league', '-')}",
            f"- \u5f00\u8d5b: {item.get('match_date', '-')} {item.get('match_time', '-')}",
            f"- \u9884\u6d4b\u65b9\u5411: {item.get('predicted', '-')}",
            f"- \u7f6e\u4fe1\u5ea6: {_pct1(item.get('prediction_confidence'))}",
            *allowlist_lines,
            "",
            "\u5b9e\u9645\u8d5b\u679c",
            f"- \u6bd4\u5206: {actual_score}",
            f"- \u7ed3\u679c: {item.get('result', '-')}",
            f"- \u603b\u8fdb\u7403: {item.get('total_goals', '-')}",
            "",
            "\u73a9\u6cd5\u547d\u4e2d",
            f"- 1X2: {self._hit_label(item.get('is_correct'))}",
            f"- \u8ba9\u7403: {self._hit_label(item.get('handicap_is_correct'))} | \u9884\u6d4b {item.get('predicted_handicap', '-')} | \u5b9e\u9645 {item.get('handicap_result', '-')}",
            f"- \u5927\u5c0f\u7403: {self._hit_label(item.get('ou_is_correct'))} | \u9884\u6d4b {item.get('predicted_ou', '-')} | \u5b9e\u9645 {item.get('ou_result', '-')}",
            f"- \u6bd4\u5206: {self._hit_label(item.get('score_is_correct'))} | \u9884\u6d4b {item.get('predicted_score', '-')} | \u5b9e\u9645 {actual_score}",
            "",
            "\u504f\u5dee\u6807\u7b7e",
            *[f"- {tag}" for tag in tags],
            "",
            "\u6539\u8fdb\u5efa\u8bae",
            *[f"- {suggestion}" for suggestion in suggestions],
            *video_lines,
            *statsbomb_proxy_lines,
        ]
        return "\n".join(lines)

    def _high_confidence_misses(self, settlements: list[dict]) -> list[dict]:
        misses = [
            item
            for item in settlements
            if isinstance(item, dict)
            and item.get("is_correct") is False
            and float(item.get("prediction_confidence", 0) or 0) >= 0.6
        ]
        return sorted(misses, key=lambda item: float(item.get("prediction_confidence", 0) or 0), reverse=True)

    def _pending_snapshot_rows(self) -> list[dict]:
        snapshots = _load_prediction_snapshot_records()
        settled_ids = {str(item.get("match_id", "")) for item in get_recent_settlements(limit=0) if item.get("match_id")}
        rows: list[dict] = []
        for match_id, record in snapshots.items():
            if str(match_id) in settled_ids or not isinstance(record, dict):
                continue
            match = record.get("match", {})
            prediction = record.get("prediction", {})
            if not isinstance(match, dict) or not isinstance(prediction, dict):
                continue
            rows.append(
                {
                    "match_id": str(match_id),
                    "saved_at": str(record.get("saved_at") or "-"),
                    "match": match,
                    "prediction": prediction,
                    "market_snapshot": record.get("market_snapshot", {}),
                    "strategy_allowlist": self._snapshot_allowlist_payload(record, prediction),
                    "status": _snapshot_status(match),
                }
            )
        return sorted(rows, key=lambda item: str(item.get("saved_at") or ""), reverse=True)

    def _snapshot_allowlist_payload(self, record: dict, prediction: dict) -> dict:
        payload = record.get("strategy_allowlist") if isinstance(record, dict) else {}
        if isinstance(payload, dict) and payload:
            return payload
        payload = prediction.get("strategy_allowlist") if isinstance(prediction, dict) else {}
        return payload if isinstance(payload, dict) else {}

    def _snapshot_line(self, item: dict) -> str:
        match = item.get("match", {}) if isinstance(item.get("match"), dict) else {}
        prediction = item.get("prediction", {}) if isinstance(item.get("prediction"), dict) else {}
        allowlist = item.get("strategy_allowlist", {}) if isinstance(item.get("strategy_allowlist"), dict) else {}
        prefix = "\u653e\u884c\u5f85\u56de\u6536 | " if allowlist else ""
        return (
            f"{prefix}{item.get('status', '-')} | {match.get('match_date', '-')} {match.get('match_time', '-')} | "
            f"{match.get('league', '-')} | {match.get('home_team', '-')} vs {match.get('away_team', '-')} | "
            f"{prediction.get('recommendation', '-')} | {_pct1(prediction.get('confidence'))}"
        )

    def _snapshot_detail_text(self, item: dict) -> str:
        match = item.get("match", {}) if isinstance(item.get("match"), dict) else {}
        prediction = item.get("prediction", {}) if isinstance(item.get("prediction"), dict) else {}
        market = item.get("market_snapshot", {}) if isinstance(item.get("market_snapshot"), dict) else {}
        probs = prediction.get("probabilities", {}) if isinstance(prediction.get("probabilities"), dict) else {}
        indices = prediction.get("indices", {}) if isinstance(prediction.get("indices"), dict) else {}
        admission = _admission_payload(prediction)
        draw_guard_label, draw_guard_body, _draw_guard_tone = _draw_release_guard_summary(prediction)
        allowlist = item.get("strategy_allowlist", {}) if isinstance(item.get("strategy_allowlist"), dict) else {}
        admission_text = ""
        if admission:
            admission_text = (
                "\n\n\u7b56\u7565\u51c6\u5165\n"
                f"- \u7ed3\u8bba: {_admission_text(prediction)}\n"
                f"- \u539f\u56e0: {format_strategy_admission_reasons(admission, limit=5)}\n"
                f"- \u95e8\u69db: {format_strategy_admission_thresholds(admission)}\n"
                f"- \u5019\u9009: {format_strategy_admission_pick(admission)}\n\n"
            )
        allowlist_text = ""
        if allowlist:
            allowlist_text = (
                "\n\n\u7b56\u7565\u653e\u884c\u56de\u6536\n"
                f"- \u72b6\u6001: \u653e\u884c\u5f85\u56de\u6536\n"
                f"- \u6e05\u5355: {allowlist.get('file', '-')}\n"
                f"- \u5bfc\u51fa\u65f6\u95f4: {allowlist.get('exported_at', '-')}\n"
                f"- \u5019\u9009: {format_strategy_admission_pick(allowlist)}\n"
                f"- \u539f\u56e0: {format_strategy_admission_reasons(allowlist, limit=5)}"
            )
        return (
            f"\u5feb\u7167\u65f6\u95f4: {item.get('saved_at', '-')}\n"
            f"\u72b6\u6001: {item.get('status', '-')}\n"
            f"\u8d5b\u4e8b: {match.get('home_team', '-')} vs {match.get('away_team', '-')}\n"
            f"\u8054\u8d5b: {match.get('league', '-')}\n"
            f"\u5f00\u8d5b: {match.get('match_date', '-')} {match.get('match_time', '-')}\n"
            f"\u6765\u6e90: {match.get('source', '-')} / {match.get('source_id', '-')}\n\n"
            f"\u63a8\u8350: {_strategy_text(prediction)}\n"
            f"\u98ce\u9669: {_risk_label(prediction.get('risk_level'))}\n"
            f"\u7f6e\u4fe1\u5ea6: {_pct1(prediction.get('confidence'))}\n"
            f"\u5e73\u5c40\u63a5\u7ba1: {draw_guard_label} | {draw_guard_body.splitlines()[0]}\n"
            f"\u9884\u8ba1\u603b\u8fdb\u7403: {_num(prediction.get('expected_goals'))}\n\n"
            f"{admission_text}"
            f"\u6982\u7387: {_prob_text(probs, 'home')} / {_prob_text(probs, 'draw')} / {_prob_text(probs, 'away')}\n"
            f"\u51b7\u95e8\u6307\u6570: {_pct1(indices.get('upset_index', 0))}\n"
            f"\u7a33\u5b9a\u6307\u6570: {_pct1(indices.get('stability_index', 0))}\n"
            f"\u4fe1\u5fc3\u6307\u6570: {_pct1(indices.get('confidence_index', 0))}\n\n"
            f"\u5927\u5c0f\u7403: {prediction.get('ou_recommendation', '-')} / {_pct1(prediction.get('ou_confidence'))}\n"
            f"\u8ba9\u7403: {prediction.get('handicap_recommendation', '-')} / {_pct1(prediction.get('handicap_confidence'))}\n"
            f"\u6bd4\u5206: {prediction.get('score_recommendation', '-')} / {_pct1(prediction.get('score_confidence'))}\n\n"
            f"\u5feb\u7167\u76d8\u53e3: \u4e3b {market.get('odds_home', match.get('odds_home', '-'))} | "
            f"\u5e73 {market.get('odds_draw', match.get('odds_draw', '-'))} | "
            f"\u5ba2 {market.get('odds_away', match.get('odds_away', '-'))}"
            f"{allowlist_text}"
        )

    def open_snapshot_center(self) -> None:
        self.current_view = "snapshot"
        rows = self._pending_snapshot_rows()
        total = len(rows)
        pending_review = sum(1 for item in rows if item.get("status") == "\u5f85\u56de\u6536")
        allowlist_pending = sum(1 for item in rows if isinstance(item.get("strategy_allowlist"), dict) and item.get("strategy_allowlist"))
        high_risk = sum(
            1
            for item in rows
            if _risk_key((item.get("prediction") or {}).get("risk_level") if isinstance(item.get("prediction"), dict) else "") == "high"
        )
        confidences = [
            float((item.get("prediction") or {}).get("confidence", 0) or 0)
            for item in rows
            if isinstance(item.get("prediction"), dict)
        ]
        avg_conf = f"{(sum(confidences) / len(confidences)):.1%}" if confidences else "-"

        shell = self._page_shell(
            "\u8d5b\u524d\u5feb\u7167",
            "\u4fdd\u7559\u8d5b\u524d\u9884\u6d4b\u3001\u76d8\u53e3\u548c\u98ce\u9669\u72b6\u6001\uff0c\u7b49\u5b8c\u573a\u540e\u56de\u6536\u590d\u76d8",
        )
        header = tk.Frame(shell, bg=BG)
        header.pack(fill=tk.X, pady=(0, 16))
        recover_button = tk.Button(
            header,
            text="\u56de\u6536\u8d5b\u679c",
            command=self.run_result_recovery,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        )
        self._register_result_recovery_button(recover_button)
        recover_button.pack(side=tk.RIGHT)
        tk.Button(
            header,
            text="\u8fd4\u56de\u590d\u76d8\u4e2d\u5fc3",
            command=self.open_review_center,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        for label, value, color in [
            ("\u5feb\u7167\u603b\u6570", str(total), TEXT),
            ("\u5f85\u56de\u6536", str(pending_review), YELLOW if pending_review else GREEN),
            ("\u653e\u884c\u5f85\u56de\u6536", str(allowlist_pending), YELLOW if allowlist_pending else GREEN),
            ("\u9ad8\u98ce\u9669", str(high_risk), RED if high_risk else GREEN),
            ("\u5e73\u5747\u7f6e\u4fe1", avg_conf, "#7aa2ff"),
        ]:
            self._detail_metric(top, label, value, color)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u5f85\u590d\u76d8\u5217\u8868", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        listbox = tk.Listbox(
            left,
            bg=PANEL,
            fg=TEXT,
            selectbackground=BLUE,
            selectforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10),
            activestyle="none",
        )
        listbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        tk.Label(right, text="\u5feb\u7167\u8be6\u60c5", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        detail = tk.Text(
            right,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            height=18,
        )
        detail.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 14))

        def show_detail(index: int) -> None:
            detail.configure(state=tk.NORMAL)
            detail.delete("1.0", tk.END)
            if not rows:
                detail.insert(tk.END, "\u6682\u65e0\u8d5b\u524d\u5feb\u7167\u3002\u5237\u65b0\u8d5b\u4e8b\u540e\uff0c\u7cfb\u7edf\u4f1a\u81ea\u52a8\u4fdd\u5b58\u5f85\u590d\u76d8\u7684\u8d5b\u524d\u9884\u6d4b\u3002")
            else:
                detail.insert(tk.END, self._snapshot_detail_text(rows[index]))
            detail.configure(state=tk.DISABLED)

        for item in rows:
            listbox.insert(tk.END, self._snapshot_line(item))
        if rows:
            listbox.selection_set(0)
            show_detail(0)
        else:
            listbox.insert(tk.END, "\u6682\u65e0\u5f85\u590d\u76d8\u5feb\u7167")
            show_detail(0)

        def on_select(_event=None) -> None:
            selection = listbox.curselection()
            if selection and rows:
                show_detail(int(selection[0]))

        listbox.bind("<<ListboxSelect>>", on_select)

    def export_strategy_allowlist(self) -> Path | None:
        if not self.rows:
            messagebox.showinfo("\u5bfc\u51fa\u653e\u884c\u6e05\u5355", "\u5f53\u524d\u8fd8\u6ca1\u6709\u5df2\u52a0\u8f7d\u7684\u8d5b\u4e8b\u5206\u6790\u7ed3\u679c\u3002")
            return None

        allowed = select_strategy_allowlist_rows(self.rows)
        if not allowed:
            self.status_var.set("\u5f53\u524d\u6ca1\u6709\u6b63\u5f0f\u653e\u884c\u573a\u6b21")
            messagebox.showinfo("\u5bfc\u51fa\u653e\u884c\u6e05\u5355", "\u5f53\u524d\u6ca1\u6709\u7b56\u7565\u51c6\u5165\u4e3a\u6b63\u5f0f\u653e\u884c\u7684\u573a\u6b21\u3002")
            return None

        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        path = REPORT_DIR / build_strategy_allowlist_filename(now)
        recent_settlements = get_recent_settlements(limit=200)
        path.write_text(
            "\n".join(build_strategy_allowlist_report_lines(allowed, generated_at=now, settlements=recent_settlements)),
            encoding="utf-8",
        )
        link_summary = mark_strategy_allowlist_snapshots(
            [(row.match, row.prediction) for row in allowed],
            allowlist_file=path.name,
            exported_at=now,
        )
        marked = int(link_summary.get("marked", 0) or 0)
        self.status_var.set(f"\u653e\u884c\u6e05\u5355\u5df2\u5bfc\u51fa: {path.name} | \u5f85\u56de\u6536 {marked} \u573a")
        self._refresh_current_view_after_release_state_change()
        messagebox.showinfo("\u5bfc\u51fa\u653e\u884c\u6e05\u5355", f"\u5df2\u751f\u6210\u653e\u884c\u6e05\u5355:\n{path}\n\n\u5df2\u63a5\u5165\u590d\u76d8\u56de\u6536: {marked} \u573a")
        return path

    def export_strategy_policy_audit_report(self) -> tuple[Path, Path] | None:
        policy_history = get_strategy_admission_policy_history(limit=50)
        draw_guard_history = get_draw_release_guard_policy_history(limit=50)
        if not policy_history and not draw_guard_history:
            messagebox.showinfo("\u7b56\u7565\u8c03\u53c2\u5ba1\u8ba1", "\u5c1a\u65e0\u53ef\u5bfc\u51fa\u7684\u7b56\u7565\u53c2\u6570\u7248\u672c\u8bb0\u5f55\u3002")
            return None
        settlements = list(reversed(get_recent_settlements(limit=300)))
        status = get_high_accuracy_strategy_status()
        dashboard = build_high_accuracy_strategy_dashboard(
            status,
            settlements,
            policy_history,
            get_statsbomb_event_baseline(),
            get_statsbomb_sandbox_fewshot_memory(),
            None,
            get_draw_release_guard_policy_status(),
            draw_guard_history,
            video_review_fewshot_memory=get_video_review_fewshot_memory(),
            statsbomb_review_training_samples=get_statsbomb_review_training_samples(),
        )
        policy_effect = dashboard.get("policy_effect_review", {}) if isinstance(dashboard.get("policy_effect_review"), dict) else {}
        now = datetime.now()
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        md_path = REPORT_DIR / build_strategy_policy_audit_report_filename(now)
        csv_path = REPORT_DIR / build_strategy_policy_audit_csv_filename(now)
        draw_guard_report_kwargs = {
            "draw_release_guard_policy_history": draw_guard_history,
            "draw_release_guard_tuning_effect_review": dashboard.get("draw_release_guard_tuning_effect", {}),
            "draw_release_guard_rollback_effect_review": dashboard.get("draw_release_guard_rollback_effect", {}),
            "draw_release_guard_freeze_override_status": dashboard.get("draw_release_guard_freeze_override", {}),
            "draw_release_guard_tuning_guard": dashboard.get("draw_release_guard_tuning_guard", {}),
        }
        md_path.write_text(
            "\n".join(build_strategy_policy_audit_report_lines(policy_effect, generated_at=now, **draw_guard_report_kwargs)),
            encoding="utf-8",
        )
        csv_path.write_text(build_strategy_policy_audit_csv_text(policy_effect, **draw_guard_report_kwargs), encoding="utf-8-sig")
        self.status_var.set(f"\u7b56\u7565\u8c03\u53c2\u5ba1\u8ba1\u5df2\u5bfc\u51fa: {md_path.name}")
        messagebox.showinfo(
            "\u7b56\u7565\u8c03\u53c2\u5ba1\u8ba1",
            f"\u5df2\u751f\u6210\u5ba1\u8ba1\u62a5\u544a:\n{md_path}\n\n\u660e\u7ec6CSV:\n{csv_path}",
        )
        return md_path, csv_path

    def export_statsbomb_fewshot_backfill_report(self) -> Path | None:
        settlements = list(reversed(get_recent_settlements(limit=300)))
        dashboard = build_high_accuracy_strategy_dashboard(
            get_high_accuracy_strategy_status(),
            settlements,
            get_strategy_admission_policy_history(limit=20),
            get_statsbomb_event_baseline(),
            get_statsbomb_sandbox_fewshot_memory(),
            include_statsbomb_backfill_candidates=True,
            video_review_fewshot_memory=get_video_review_fewshot_memory(),
            statsbomb_review_training_samples=get_statsbomb_review_training_samples(),
        )
        queue = dashboard.get("statsbomb_backfill_queue", {}) if isinstance(dashboard.get("statsbomb_backfill_queue"), dict) else {}
        now = datetime.now()
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = REPORT_DIR / build_statsbomb_fewshot_backfill_report_filename(now)
        path.write_text(
            "\n".join(build_statsbomb_fewshot_backfill_report_lines(queue, generated_at=now)),
            encoding="utf-8",
        )
        self.status_var.set(f"StatsBomb\u8865\u6837\u961f\u5217\u5df2\u5bfc\u51fa: {path.name}")
        messagebox.showinfo("StatsBomb\u8865\u6837\u961f\u5217", f"\u5df2\u751f\u6210\u8865\u6837\u961f\u5217\u62a5\u544a:\n{path}")
        return path

    def export_statsbomb_fewshot_draft(self) -> tuple[Path, Path, Path, Path, Path] | None:
        settlements = list(reversed(get_recent_settlements(limit=300)))
        baseline = get_statsbomb_event_baseline()
        memory = get_statsbomb_sandbox_fewshot_memory()
        dashboard = build_high_accuracy_strategy_dashboard(
            get_high_accuracy_strategy_status(),
            settlements,
            get_strategy_admission_policy_history(limit=20),
            baseline,
            memory,
            include_statsbomb_backfill_candidates=True,
            video_review_fewshot_memory=get_video_review_fewshot_memory(),
            statsbomb_review_training_samples=get_statsbomb_review_training_samples(),
        )
        queue = dashboard.get("statsbomb_backfill_queue", {}) if isinstance(dashboard.get("statsbomb_backfill_queue"), dict) else {}
        now = datetime.now()
        payload = build_statsbomb_fewshot_draft_payload(queue, baseline, generated_at=now, limit=30)
        merge_plan = build_statsbomb_fewshot_merge_plan(payload, memory)
        merge_bundle = build_statsbomb_fewshot_merge_bundle(merge_plan, generated_at=now)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = REPORT_DIR / build_statsbomb_fewshot_draft_filename(now)
        md_path = REPORT_DIR / build_statsbomb_fewshot_draft_review_filename(now)
        plan_path = REPORT_DIR / build_statsbomb_fewshot_merge_plan_filename(now)
        bundle_path = REPORT_DIR / build_statsbomb_fewshot_merge_bundle_filename(now)
        bundle_review_path = REPORT_DIR / build_statsbomb_fewshot_merge_bundle_report_filename(now)
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text("\n".join(build_statsbomb_fewshot_draft_review_lines(payload)), encoding="utf-8")
        plan_path.write_text("\n".join(build_statsbomb_fewshot_merge_plan_lines(merge_plan)), encoding="utf-8")
        bundle_path.write_text(json.dumps(merge_bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        bundle_review_path.write_text("\n".join(build_statsbomb_fewshot_merge_bundle_report_lines(merge_bundle)), encoding="utf-8")
        draft_count = int((payload.get("summary") or {}).get("draft_count", 0) or 0) if isinstance(payload.get("summary"), dict) else 0
        validation = payload.get("validation", {}) if isinstance(payload.get("validation"), dict) else {}
        validation_text = str(validation.get("summary_text") or "-")
        self.status_var.set(f"StatsBomb few-shot\u8349\u7a3f\u5df2\u5bfc\u51fa: {draft_count} \u6761 | {validation_text} | {merge_bundle.get('status', '-')}")
        messagebox.showinfo(
            "StatsBomb few-shot\u8349\u7a3f",
            f"\u5df2\u751f\u6210\u8349\u7a3fJSON:\n{json_path}\n\n\u5ba1\u67e5\u62a5\u544a:\n{md_path}\n\n\u5408\u5e76\u8ba1\u5212:\n{plan_path}\n\n\u53ef\u5e94\u7528\u5305:\n{bundle_path}\n\n\u5305\u5ba1\u67e5:\n{bundle_review_path}\n\n\u6821\u9a8c: {validation_text}",
        )
        return json_path, md_path, plan_path, bundle_path, bundle_review_path

    def preview_statsbomb_fewshot_merge_bundle(self) -> Path | None:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        selected = filedialog.askopenfilename(
            title="Select StatsBomb few-shot merge bundle",
            initialdir=str(REPORT_DIR),
            filetypes=[
                ("StatsBomb merge bundle", "statsbomb_fewshot_merge_bundle_*.json"),
                ("JSON", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not selected:
            return None
        source_path = Path(selected)
        try:
            bundle = json.loads(source_path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("StatsBomb few-shot preview", f"Failed to read bundle:\n{source_path}\n\n{exc}")
            return None
        now = datetime.now()
        preview = build_statsbomb_fewshot_merge_apply_preview(
            bundle,
            get_statsbomb_sandbox_fewshot_memory(),
            generated_at=now,
        )
        preview_path = REPORT_DIR / build_statsbomb_fewshot_merge_apply_preview_filename(now)
        preview_path.write_text(
            "\n".join(build_statsbomb_fewshot_merge_apply_preview_lines(preview)),
            encoding="utf-8",
        )
        summary = preview.get("summary", {}) if isinstance(preview.get("summary"), dict) else {}
        self.status_var.set(
            f"StatsBomb few-shot preview: {preview.get('status', '-')} | append {summary.get('append_count', 0)} | skipped {summary.get('skipped_count', 0)}"
        )
        messagebox.showinfo(
            "StatsBomb few-shot preview",
            f"Dry-run preview generated:\n{preview_path}\n\nStatus: {preview.get('status', '-')}\nWould append: {summary.get('append_count', 0)}\nSkipped: {summary.get('skipped_count', 0)}",
        )
        return preview_path

    def apply_statsbomb_fewshot_merge_bundle(self) -> tuple[Path, Path | None] | None:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        selected = filedialog.askopenfilename(
            title="Select StatsBomb few-shot merge bundle to apply",
            initialdir=str(REPORT_DIR),
            filetypes=[
                ("StatsBomb merge bundle", "statsbomb_fewshot_merge_bundle_*.json"),
                ("JSON", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not selected:
            return None
        source_path = Path(selected)
        try:
            bundle = json.loads(source_path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("StatsBomb few-shot apply", f"Failed to read bundle:\n{source_path}\n\n{exc}")
            return None
        now = datetime.now()
        result = build_statsbomb_fewshot_merge_apply_result(
            bundle,
            get_statsbomb_sandbox_fewshot_memory(),
            generated_at=now,
        )
        report_path = REPORT_DIR / build_statsbomb_fewshot_merge_apply_report_filename(now)
        report_path.write_text(
            "\n".join(build_statsbomb_fewshot_merge_apply_report_lines(result)),
            encoding="utf-8",
        )
        summary = result.get("summary", {}) if isinstance(result.get("summary"), dict) else {}
        if result.get("status") != "ready_to_write":
            self.status_var.set(f"StatsBomb few-shot apply blocked: {result.get('status', '-')} | report {report_path.name}")
            messagebox.showwarning(
                "StatsBomb few-shot apply",
                f"Apply was blocked or empty.\n\nReport:\n{report_path}\n\nStatus: {result.get('status', '-')}",
            )
            return report_path, None
        applied_count = int(summary.get("applied_count", 0) or 0)
        final_count = int(summary.get("final_count", 0) or 0)
        backup_name = str(((result.get("preview") or {}) if isinstance(result.get("preview"), dict) else {}).get("backup_filename") or "")
        confirmed = messagebox.askyesno(
            "StatsBomb few-shot apply",
            (
                "This will write approved post-match few-shot samples into the official Evaluation Agent memory.\n\n"
                f"Bundle:\n{source_path}\n\n"
                f"Apply samples: {applied_count}\n"
                f"Final memory samples: {final_count}\n"
                f"Backup file: {backup_name or '-'}\n\n"
                "Continue?"
            ),
        )
        if not confirmed:
            self.status_var.set(f"StatsBomb few-shot apply cancelled: {report_path.name}")
            return report_path, None
        updated_memory = result.get("updated_memory") if isinstance(result.get("updated_memory"), dict) else None
        if not updated_memory:
            messagebox.showerror("StatsBomb few-shot apply", "Apply result did not include updated memory payload.")
            return report_path, None
        STATSBOMB_SANDBOX_FEWSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
        backup_path: Path | None = None
        if STATSBOMB_SANDBOX_FEWSHOT_FILE.exists():
            backup_path = STATSBOMB_SANDBOX_FEWSHOT_FILE.parent / (backup_name or f"{STATSBOMB_SANDBOX_FEWSHOT_FILE.name}.backup_{now.strftime('%Y%m%d_%H%M%S')}.json")
            shutil.copy2(STATSBOMB_SANDBOX_FEWSHOT_FILE, backup_path)
        tmp_path = STATSBOMB_SANDBOX_FEWSHOT_FILE.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(updated_memory, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(STATSBOMB_SANDBOX_FEWSHOT_FILE)
        invalidate_statsbomb_state_cache(STATSBOMB_SANDBOX_FEWSHOT_FILE)
        self.status_var.set(f"StatsBomb few-shot applied: +{applied_count} | total {final_count}")
        self._refresh_current_view_after_release_state_change()
        messagebox.showinfo(
            "StatsBomb few-shot apply",
            f"Applied {applied_count} samples.\n\nMemory:\n{STATSBOMB_SANDBOX_FEWSHOT_FILE}\n\nBackup:\n{backup_path or '-'}\n\nReport:\n{report_path}",
        )
        return report_path, backup_path

    def rollback_statsbomb_fewshot_memory(self) -> tuple[Path, Path | None] | None:
        state_dir = STATSBOMB_SANDBOX_FEWSHOT_FILE.parent
        state_dir.mkdir(parents=True, exist_ok=True)
        selected = filedialog.askopenfilename(
            title="Select StatsBomb few-shot memory backup",
            initialdir=str(state_dir),
            filetypes=[
                ("StatsBomb few-shot backup", "statsbomb_sandbox_fewshot_samples.backup_*.json"),
                ("JSON", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not selected:
            return None
        backup_path = Path(selected)
        try:
            backup_payload = json.loads(backup_path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("StatsBomb few-shot rollback", f"Failed to read backup:\n{backup_path}\n\n{exc}")
            return None
        current_payload = get_statsbomb_sandbox_fewshot_memory()
        now = datetime.now()
        preview = build_statsbomb_fewshot_memory_rollback_preview(
            backup_payload,
            current_payload,
            backup_name=backup_path.name,
            generated_at=now,
        )
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / build_statsbomb_fewshot_memory_rollback_report_filename(now)
        report_path.write_text(
            "\n".join(build_statsbomb_fewshot_memory_rollback_report_lines(preview)),
            encoding="utf-8",
        )
        summary = preview.get("summary", {}) if isinstance(preview.get("summary"), dict) else {}
        if preview.get("status") != "ready_to_restore":
            self.status_var.set(f"StatsBomb few-shot rollback blocked: {report_path.name}")
            messagebox.showwarning(
                "StatsBomb few-shot rollback",
                f"Rollback was blocked.\n\nReport:\n{report_path}\n\nStatus: {preview.get('status', '-')}",
            )
            return report_path, None
        confirmed = messagebox.askyesno(
            "StatsBomb few-shot rollback",
            (
                "This will restore the official Evaluation Agent few-shot memory from the selected backup.\n\n"
                f"Backup:\n{backup_path}\n\n"
                f"Backup samples: {summary.get('backup_count', 0)}\n"
                f"Current samples: {summary.get('current_count', 0)}\n"
                f"Restore delta: {summary.get('delta', 0)}\n\n"
                "Continue?"
            ),
        )
        if not confirmed:
            self.status_var.set(f"StatsBomb few-shot rollback cancelled: {report_path.name}")
            return report_path, None
        safety_backup_path: Path | None = None
        if STATSBOMB_SANDBOX_FEWSHOT_FILE.exists():
            safety_backup_path = state_dir / f"statsbomb_sandbox_fewshot_samples.pre_rollback_{now.strftime('%Y%m%d_%H%M%S')}.json"
            shutil.copy2(STATSBOMB_SANDBOX_FEWSHOT_FILE, safety_backup_path)
        tmp_path = STATSBOMB_SANDBOX_FEWSHOT_FILE.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(backup_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(STATSBOMB_SANDBOX_FEWSHOT_FILE)
        invalidate_statsbomb_state_cache(STATSBOMB_SANDBOX_FEWSHOT_FILE)
        self.status_var.set(f"StatsBomb few-shot rolled back: {summary.get('backup_count', 0)} samples")
        self._refresh_current_view_after_release_state_change()
        messagebox.showinfo(
            "StatsBomb few-shot rollback",
            f"Rollback completed.\n\nRestored from:\n{backup_path}\n\nSafety backup:\n{safety_backup_path or '-'}\n\nReport:\n{report_path}",
        )
        return report_path, safety_backup_path

    def export_statsbomb_fewshot_memory_audit(self) -> Path:
        memory = get_statsbomb_sandbox_fewshot_memory()
        monitor = build_statsbomb_fewshot_memory_monitor(memory, {})
        quality = build_statsbomb_fewshot_memory_quality_alerts(monitor)
        state_dir = STATSBOMB_SANDBOX_FEWSHOT_FILE.parent
        backup_files = sorted(
            list(state_dir.glob("statsbomb_sandbox_fewshot_samples.backup_*.json"))
            + list(state_dir.glob("statsbomb_sandbox_fewshot_samples.pre_rollback_*.json")),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        backup_rows = [
            {
                "name": path.name,
                "size": path.stat().st_size,
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for path in backup_files[:20]
        ]
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        operation_files = sorted(
            list(REPORT_DIR.glob("statsbomb_fewshot_merge_applied_*.md"))
            + list(REPORT_DIR.glob("statsbomb_fewshot_memory_rollback_*.md")),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        operation_rows = [
            {
                "name": path.name,
                "type": "rollback" if "rollback" in path.name else "apply",
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for path in operation_files[:20]
        ]
        now = datetime.now()
        audit = build_statsbomb_fewshot_memory_audit_report(
            memory,
            monitor,
            quality,
            backup_rows=backup_rows,
            operation_rows=operation_rows,
            generated_at=now,
        )
        path = REPORT_DIR / build_statsbomb_fewshot_memory_audit_report_filename(now)
        path.write_text("\n".join(build_statsbomb_fewshot_memory_audit_report_lines(audit)), encoding="utf-8")
        summary = audit.get("summary", {}) if isinstance(audit.get("summary"), dict) else {}
        self.status_var.set(
            f"StatsBomb few-shot audit: samples {summary.get('sample_count', 0)} | backups {summary.get('backup_count', 0)} | alerts {summary.get('alert_count', 0)}"
        )
        messagebox.showinfo("StatsBomb few-shot audit", f"Audit report generated:\n{path}")
        return path

    def open_strategy_policy_audit_history(self) -> None:
        self.current_nav_index = 4
        self.current_view = "strategy_audit_history"
        self._refresh_nav_highlight()
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(
            list(REPORT_DIR.glob("strategy_policy_audit_*.md"))
            + list(REPORT_DIR.glob("strategy_policy_audit_samples_*.csv"))
            + list(REPORT_DIR.glob("statsbomb_fewshot_backfill_*.md"))
            + list(REPORT_DIR.glob("statsbomb_fewshot_draft_*.json"))
            + list(REPORT_DIR.glob("statsbomb_fewshot_draft_review_*.md"))
            + list(REPORT_DIR.glob("statsbomb_fewshot_merge_plan_*.md"))
            + list(REPORT_DIR.glob("statsbomb_fewshot_merge_bundle_*.json"))
            + list(REPORT_DIR.glob("statsbomb_fewshot_merge_bundle_review_*.md"))
            + list(REPORT_DIR.glob("statsbomb_fewshot_merge_apply_preview_*.md"))
            + list(REPORT_DIR.glob("statsbomb_fewshot_merge_applied_*.md"))
            + list(REPORT_DIR.glob("statsbomb_fewshot_memory_rollback_*.md"))
            + list(REPORT_DIR.glob("statsbomb_fewshot_memory_audit_*.md"))
            + list(REPORT_DIR.glob("video_review_fewshot_draft_review_*.md"))
            + list(REPORT_DIR.glob("video_review_fewshot_merge_plan_*.md"))
            + list(REPORT_DIR.glob("video_review_fewshot_merge_bundle_*.json"))
            + list(REPORT_DIR.glob("video_review_fewshot_merge_bundle_review_*.md"))
            + list(REPORT_DIR.glob("video_review_fewshot_merge_apply_preview_*.md"))
            + list(REPORT_DIR.glob("video_review_fewshot_merge_applied_*.md"))
            + list(REPORT_DIR.glob("video_review_fewshot_memory_rollback_*.md"))
            + list(REPORT_DIR.glob("video_review_fewshot_memory_audit_*.md")),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        shell = self._page_shell("\u8c03\u53c2\u5ba1\u8ba1\u5386\u53f2", f"\u62a5\u544a\u76ee\u5f55: {REPORT_DIR}")

        header = tk.Frame(shell, bg=BG)
        header.pack(fill=tk.X, pady=(0, 12))
        tk.Button(
            header,
            text="\u8fd4\u56de\u7b56\u7565\u770b\u677f",
            command=self.open_strategy_library,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT)
        tk.Button(
            header,
            text="\u5bfc\u51fa\u65b0\u5ba1\u8ba1",
            command=lambda: (self.export_strategy_policy_audit_report(), self.open_strategy_policy_audit_history()),
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        listbox = tk.Listbox(
            left,
            bg=PANEL,
            fg=TEXT,
            selectbackground=BLUE,
            selectforeground="white",
            relief=tk.FLAT,
            width=46,
            font=("Microsoft YaHei UI", 10),
            activestyle="none",
        )
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        preview = tk.Text(
            right,
            wrap=tk.WORD,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            font=("Consolas", 10),
            padx=16,
            pady=12,
        )
        preview_scroll = tk.Scrollbar(right, orient=tk.VERTICAL, command=preview.yview)
        preview.configure(yscrollcommand=preview_scroll.set)
        preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 0), pady=2)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=2)

        def show_file(index: int) -> None:
            if index < 0 or index >= len(files):
                return
            path = files[index]
            try:
                encoding = "utf-8-sig" if path.suffix.lower() == ".csv" else "utf-8"
                content = path.read_text(encoding=encoding)
            except Exception as exc:
                content = f"\u8bfb\u53d6\u5931\u8d25: {exc}"
            preview.configure(state=tk.NORMAL)
            preview.delete("1.0", tk.END)
            preview.insert("1.0", content)
            preview.configure(state=tk.DISABLED)
            self.status_var.set(f"\u6b63\u5728\u67e5\u770b\u8c03\u53c2\u5ba1\u8ba1: {path.name}")

        for path in files:
            stamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            kind = "CSV" if path.suffix.lower() == ".csv" else "JSON" if path.suffix.lower() == ".json" else "MD"
            listbox.insert(tk.END, f"{stamp}  [{kind}] {path.name}")

        if files:
            listbox.selection_set(0)
            show_file(0)
        else:
            preview.insert("1.0", "\u6682\u65e0\u7b56\u7565\u8c03\u53c2\u5ba1\u8ba1\u62a5\u544a\u3002\u8bf7\u5148\u5728\u7b56\u7565\u770b\u677f\u5bfc\u51fa\u8c03\u53c2\u5ba1\u8ba1\u3002")
            preview.configure(state=tk.DISABLED)

        listbox.bind("<<ListboxSelect>>", lambda _event: show_file(listbox.curselection()[0] if listbox.curselection() else -1))

    def _strategy_toolbar_button(
        self,
        parent: tk.Widget,
        text: str,
        command,
        *,
        primary: bool = False,
        danger: bool = False,
    ) -> None:
        bg = RED if danger else BLUE if primary else PANEL_2
        active = "#d94743" if danger else "#3d5ee7" if primary else "#172638"
        tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg="white" if primary or danger else TEXT,
            activebackground=active,
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(10, 0))

    def _latest_statsbomb_artifact_path(self, patterns: list[str], *, root: Path | None = None) -> Path | None:
        base = root or REPORT_DIR
        if not base.exists():
            return None
        files: list[Path] = []
        for pattern in patterns:
            files.extend(base.glob(pattern))
        if not files:
            return None
        return max(files, key=lambda path: path.stat().st_mtime)

    def _latest_statsbomb_artifact(self, patterns: list[str], *, root: Path | None = None) -> str:
        latest = self._latest_statsbomb_artifact_path(patterns, root=root)
        return latest.name if latest else "-"

    def _statsbomb_json_artifact_summary(self, path: Path | None, kind: str) -> str:
        if not path:
            return "-"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return f"{path.name} | 读取失败: {exc}"
        if not isinstance(payload, dict):
            return f"{path.name} | 格式异常"
        summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
        if kind == "draft":
            validation = payload.get("validation", {}) if isinstance(payload.get("validation"), dict) else {}
            return (
                f"{path.name} | 草稿 {summary.get('draft_count', 0)} / 候选 {summary.get('candidate_count', 0)} | "
                f"校验 {validation.get('status', '-')}"
            )
        if kind == "bundle":
            return (
                f"{path.name} | 状态 {payload.get('status', '-')} | "
                f"可应用 {summary.get('bundle_count', 0)} | 跳过 {summary.get('skipped_count', 0)}"
            )
        return path.name

    def _strategy_workflow_step(
        self,
        parent: tk.Widget,
        index: int,
        title: str,
        status: str,
        body: str,
        command,
        *,
        tone: str = "neutral",
        action_text: str = "执行",
        secondary_text: str | None = None,
        secondary_command=None,
        danger: bool = False,
    ) -> None:
        frame = tk.Frame(parent, bg=PANEL_2, highlightbackground="#172638", highlightthickness=1)
        frame.pack(fill=tk.X, padx=18, pady=5)
        top = tk.Frame(frame, bg=PANEL_2)
        top.pack(fill=tk.X, padx=12, pady=(10, 3))
        tk.Label(
            top,
            text=f"{index}",
            bg=self._tone_color(tone),
            fg=BG,
            font=("Microsoft YaHei UI", 9, "bold"),
            width=3,
        ).pack(side=tk.LEFT)
        tk.Label(top, text=title, bg=PANEL_2, fg=TEXT, font=("Microsoft YaHei UI", 10, "bold")).pack(side=tk.LEFT, padx=(10, 8))
        tk.Label(top, text=status, bg=PANEL_2, fg=self._tone_color(tone), font=("Microsoft YaHei UI", 9, "bold")).pack(side=tk.RIGHT)
        tk.Label(
            frame,
            text=body,
            bg=PANEL_2,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            justify=tk.LEFT,
            wraplength=350,
        ).pack(anchor=tk.W, padx=12, pady=(0, 8))
        actions = tk.Frame(frame, bg=PANEL_2)
        actions.pack(fill=tk.X, padx=12, pady=(0, 10))
        if command:
            tk.Button(
                actions,
                text=action_text,
                command=command,
                bg=RED if danger else PANEL,
                fg="white" if danger else TEXT,
                activebackground="#d94743" if danger else "#172638",
                activeforeground="white",
                relief=tk.FLAT,
                font=("Microsoft YaHei UI", 9, "bold"),
                padx=12,
                pady=4,
            ).pack(side=tk.LEFT)
        if secondary_text and secondary_command:
            tk.Button(
                actions,
                text=secondary_text,
                command=secondary_command,
                bg=PANEL,
                fg=TEXT,
                activebackground="#172638",
                activeforeground="white",
                relief=tk.FLAT,
                font=("Microsoft YaHei UI", 9, "bold"),
                padx=12,
                pady=4,
            ).pack(side=tk.LEFT, padx=(8, 0))

    def _strategy_statsbomb_workflow_panel(self, parent: tk.Widget, dashboard: dict) -> None:
        backfill_queue = dashboard.get("statsbomb_backfill_queue", {}) if isinstance(dashboard.get("statsbomb_backfill_queue"), dict) else {}
        monitor = dashboard.get("statsbomb_fewshot_monitor", {}) if isinstance(dashboard.get("statsbomb_fewshot_monitor"), dict) else {}
        health = dashboard.get("statsbomb_fewshot_health", {}) if isinstance(dashboard.get("statsbomb_fewshot_health"), dict) else {}
        candidate_count = int(backfill_queue.get("candidate_count", 0) or 0)
        task_count = int(backfill_queue.get("task_count", 0) or 0)
        sample_count = int(monitor.get("sample_count", 0) or 0)
        alert_count = int(health.get("issue_count", 0) or 0)
        latest_backfill = self._latest_statsbomb_artifact(["statsbomb_fewshot_backfill_*.md"])
        latest_draft_path = self._latest_statsbomb_artifact_path(["statsbomb_fewshot_draft_*.json"])
        latest_bundle_path = self._latest_statsbomb_artifact_path(["statsbomb_fewshot_merge_bundle_*.json"])
        latest_draft = self._statsbomb_json_artifact_summary(latest_draft_path, "draft")
        latest_bundle = self._statsbomb_json_artifact_summary(latest_bundle_path, "bundle")
        latest_preview = self._latest_statsbomb_artifact(["statsbomb_fewshot_merge_apply_preview_*.md"])
        latest_apply = self._latest_statsbomb_artifact(["statsbomb_fewshot_merge_applied_*.md"])
        latest_audit = self._latest_statsbomb_artifact(["statsbomb_fewshot_memory_audit_*.md"])
        latest_backup = self._latest_statsbomb_artifact(
            ["statsbomb_sandbox_fewshot_samples.backup_*.json", "statsbomb_sandbox_fewshot_samples.pre_rollback_*.json"],
            root=STATSBOMB_SANDBOX_FEWSHOT_FILE.parent,
        )

        self._strategy_section_title(parent, "StatsBomb 补样闭环")
        self._strategy_workflow_step(
            parent,
            1,
            "生成补样队列",
            "待补样" if task_count else "健康",
            f"{backfill_queue.get('summary_text') or '-'}\n最近队列: {latest_backfill}",
            self.export_statsbomb_fewshot_backfill_report,
            tone="warning" if task_count else "good",
            action_text="导出队列",
        )
        self._strategy_workflow_step(
            parent,
            2,
            "候选转草稿",
            "可生成" if candidate_count else "等待候选",
            f"候选 {candidate_count} 场，草稿只进入 Evaluation Agent 赛后记忆。\n最近草稿: {latest_draft}",
            self.export_statsbomb_fewshot_draft,
            tone="info" if candidate_count else "neutral",
            action_text="生成草稿",
        )
        self._strategy_workflow_step(
            parent,
            3,
            "预览合并包",
            "有合并包" if latest_bundle_path else "未生成",
            f"先预览重复、校验和追加数量，再决定是否应用。\n最近合并包: {latest_bundle}\n最近预览: {latest_preview}",
            self.preview_statsbomb_fewshot_merge_bundle,
            tone="info" if latest_bundle_path else "neutral",
            action_text="选择预览",
        )
        self._strategy_workflow_step(
            parent,
            4,
            "应用到记忆库",
            "需确认",
            f"应用会写入官方 Evaluation Agent few-shot 记忆，并自动保留备份。\n最近应用: {latest_apply}",
            self.apply_statsbomb_fewshot_merge_bundle,
            tone="warning",
            action_text="选择应用",
            danger=True,
        )
        self._strategy_workflow_step(
            parent,
            5,
            "审计与回滚",
            "有告警" if alert_count else "可审计",
            f"当前样本 {sample_count} 条，健康问题 {alert_count} 个。\n最近审计: {latest_audit}\n最近备份: {latest_backup}",
            self.export_statsbomb_fewshot_memory_audit,
            tone="warning" if alert_count else "good",
            action_text="生成审计",
            secondary_text="选择回滚",
            secondary_command=self.rollback_statsbomb_fewshot_memory,
        )

    def _configure_dark_tree_style(
        self,
        style_name: str,
        *,
        master: tk.Widget | None = None,
        rowheight: int = 28,
    ) -> None:
        style = ttk.Style(master)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        heading_style = f"{style_name}.Heading"
        style.configure(
            style_name,
            background=PANEL,
            foreground=TEXT,
            fieldbackground=PANEL,
            rowheight=rowheight,
            borderwidth=0,
        )
        style.configure(
            heading_style,
            background=PANEL_2,
            foreground=TEXT,
            fieldbackground=PANEL_2,
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        style.map(
            style_name,
            background=[("selected", BLUE), ("!selected", PANEL)],
            foreground=[("selected", "white"), ("!selected", TEXT)],
            fieldbackground=[("!selected", PANEL)],
        )
        style.map(
            heading_style,
            background=[("active", PANEL_2), ("!active", PANEL_2)],
            foreground=[("active", TEXT), ("!active", TEXT)],
        )

    def _strategy_section_title(self, parent: tk.Widget, text: str, *, first: bool = False) -> None:
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill=tk.X, padx=18, pady=(2 if first else 18, 8))
        tk.Label(wrap, text=text, bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(side=tk.LEFT)
        tk.Frame(wrap, bg=BORDER, height=1).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0), pady=(13, 0))

    def _strategy_metric_grid(self, parent: tk.Widget, metrics: object, *, columns: int = 4) -> None:
        items = [item for item in metrics if isinstance(item, dict)] if isinstance(metrics, list) else []
        column_count = max(1, int(columns))
        for col in range(column_count):
            parent.grid_columnconfigure(col, weight=1, uniform="strategy_metric")
        for index, metric in enumerate(items):
            row_index = index // column_count
            col_index = index % column_count
            frame = self._card(parent, PANEL)
            frame.grid(row=row_index, column=col_index, sticky="ew", padx=(0, 12), pady=(0, 10))
            label = str(metric.get("label") or "-")
            value = str(metric.get("value") or "-")
            color = self._tone_color(str(metric.get("tone") or "neutral"))
            tk.Label(frame, text=label, bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W, padx=14, pady=(12, 3))
            tk.Label(
                frame,
                text=value,
                bg=PANEL,
                fg=color,
                font=("Microsoft YaHei UI", 14, "bold"),
                wraplength=185,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, padx=14, pady=(0, 12))

    def _current_strategy_policy_tuning_guard(self, tuning: dict | object, source: str) -> dict:
        policy_history = get_strategy_admission_policy_history(limit=20)
        settlements = list(reversed(get_recent_settlements(limit=200)))
        status = get_high_accuracy_strategy_status()
        dashboard = build_high_accuracy_strategy_dashboard(
            status,
            settlements,
            policy_history,
            get_statsbomb_event_baseline(),
            get_statsbomb_sandbox_fewshot_memory(),
            video_review_fewshot_memory=get_video_review_fewshot_memory(),
            statsbomb_review_training_samples=get_statsbomb_review_training_samples(),
        )
        monitor = dashboard.get("policy_stability_monitor", {}) if isinstance(dashboard.get("policy_stability_monitor"), dict) else {}
        trend_effect = dashboard.get("trend_tuning_effect_review", {}) if isinstance(dashboard.get("trend_tuning_effect_review"), dict) else {}
        rollback_effect = dashboard.get("rollback_effect_review", {}) if isinstance(dashboard.get("rollback_effect_review"), dict) else {}
        freeze_override = dashboard.get("freeze_override_status", {}) if isinstance(dashboard.get("freeze_override_status"), dict) else {}
        return build_strategy_policy_tuning_guard(
            monitor,
            tuning if isinstance(tuning, dict) else {},
            source=source,
            trend_tuning_effect_review=trend_effect,
            rollback_effect_review=rollback_effect,
            freeze_override_status=freeze_override,
        )

    def _block_strategy_policy_tuning_if_needed(self, tuning: dict | object, source: str) -> dict | None:
        guard = self._current_strategy_policy_tuning_guard(tuning, source)
        if not bool(guard.get("allowed")):
            messagebox.showwarning(
                str(guard.get("source_label") or "\u7b56\u7565\u8c03\u53c2"),
                f"{guard.get('label', '-')}\n\n{guard.get('body', '-')}",
            )
            self.status_var.set(str(guard.get("summary_text") or guard.get("label") or "\u8c03\u53c2\u5df2\u6682\u505c"))
            return None
        return guard

    def _current_draw_release_guard_tuning_guard(self, tuning: dict | object) -> dict:
        draw_guard_history = get_draw_release_guard_policy_history(limit=20)
        settlements = list(reversed(get_recent_settlements(limit=200)))
        rollback_effect = build_draw_release_guard_rollback_effect_review(draw_guard_history, settlements)
        freeze_override = build_draw_release_guard_freeze_override_status(draw_guard_history, rollback_effect)
        return build_draw_release_guard_tuning_guard(
            tuning if isinstance(tuning, dict) else {},
            rollback_effect_review=rollback_effect,
            freeze_override_status=freeze_override,
        )

    def _block_draw_release_guard_tuning_if_needed(self, tuning: dict | object) -> dict | None:
        guard = self._current_draw_release_guard_tuning_guard(tuning)
        if not bool(guard.get("allowed")):
            messagebox.showwarning(
                str(guard.get("source_label") or "DrawGuard\u8c03\u53c2"),
                f"{guard.get('label', '-')}\n\n{guard.get('body', '-')}",
            )
            self.status_var.set(str(guard.get("summary_text") or guard.get("label") or "DrawGuard\u8c03\u53c2\u5df2\u51bb\u7ed3"))
            return None
        return guard

    def apply_strategy_policy_freeze_override(self, rollback_effect: dict | object | None = None, freeze_override: dict | object | None = None) -> None:
        rollback = rollback_effect if isinstance(rollback_effect, dict) else {}
        override = freeze_override if isinstance(freeze_override, dict) else {}
        if not rollback:
            policy_history = get_strategy_admission_policy_history(limit=20)
            settlements = list(reversed(get_recent_settlements(limit=200)))
            review = build_strategy_policy_effect_review(policy_history, settlements)
            rollback = build_strategy_policy_rollback_effect_review(review)
            override = build_strategy_policy_freeze_override_status(policy_history, rollback)
        if str(rollback.get("status") or "") != "negative":
            messagebox.showinfo("\u8c03\u53c2\u51bb\u7ed3", "\u5f53\u524d\u6ca1\u6709\u56de\u6eda\u5931\u8d25\u5bfc\u81f4\u7684\u8c03\u53c2\u51bb\u7ed3\u3002")
            return
        if str(override.get("status") or "") == "overridden":
            messagebox.showinfo("\u8c03\u53c2\u51bb\u7ed3", f"\u51bb\u7ed3\u5df2\u89e3\u9664:\n{override.get('summary_text', '-')}")
            return
        rollback_version = str(rollback.get("latest_version_id") or "-")
        confirm = messagebox.askyesno(
            "\u4eba\u5de5\u89e3\u9664\u8c03\u53c2\u51bb\u7ed3",
            (
                f"\u5c06\u5199\u5165\u4e00\u6761\u5ba1\u8ba1\u8bb0\u5f55\uff0c\u8868\u793a\u5df2\u4eba\u5de5\u590d\u6838\u56de\u6eda\u5931\u8d25\u6837\u672c\u5e76\u5141\u8bb8\u6062\u590d\u8c03\u53c2:\n\n"
                f"{rollback.get('summary_text', '-')}\n\n"
                "\u8fd9\u4e0d\u4f1a\u6539\u53d8\u5f53\u524d\u95e8\u69db\u53c2\u6570\uff0c\u53ea\u4f1a\u5199\u5165 policy_freeze_override \u5ba1\u8ba1\u7248\u672c\u3002\n"
                "\u540e\u7eed\u8c03\u53c2\u4ecd\u9700\u8981\u4eba\u5de5\u786e\u8ba4\u3002"
            ),
        )
        if not confirm:
            return
        status = apply_strategy_admission_policy_update({}, source=f"policy_freeze_override:{rollback_version}")
        version_id = str(status.get("version_id") or "-")
        self.status_var.set(f"\u8c03\u53c2\u51bb\u7ed3\u5df2\u4eba\u5de5\u89e3\u9664: {version_id}")
        messagebox.showinfo("\u8c03\u53c2\u51bb\u7ed3", "\u5df2\u5199\u5165\u89e3\u9664\u51bb\u7ed3\u5ba1\u8ba1\u8bb0\u5f55\uff0c\u540e\u7eed\u8c03\u53c2\u5c06\u8f6c\u4e3a\u4eba\u5de5\u786e\u8ba4\u3002")
        self.open_strategy_library()

    def apply_draw_release_guard_freeze_override(self, rollback_effect: dict | object | None = None, freeze_override: dict | object | None = None) -> None:
        rollback = rollback_effect if isinstance(rollback_effect, dict) else {}
        override = freeze_override if isinstance(freeze_override, dict) else {}
        if not rollback:
            draw_guard_history = get_draw_release_guard_policy_history(limit=20)
            settlements = list(reversed(get_recent_settlements(limit=200)))
            rollback = build_draw_release_guard_rollback_effect_review(draw_guard_history, settlements)
            override = build_draw_release_guard_freeze_override_status(draw_guard_history, rollback)
        if str(rollback.get("status") or "") != "negative":
            messagebox.showinfo("DrawGuard\u51bb\u7ed3", "\u5f53\u524d\u6ca1\u6709 DrawGuard \u56de\u6eda\u5931\u8d25\u5bfc\u81f4\u7684\u8c03\u53c2\u51bb\u7ed3\u3002")
            return
        if str(override.get("status") or "") == "overridden":
            messagebox.showinfo("DrawGuard\u51bb\u7ed3", f"\u51bb\u7ed3\u5df2\u89e3\u9664:\n{override.get('summary_text', '-')}")
            return
        rollback_version = str(rollback.get("latest_version_id") or "-")
        confirm = messagebox.askyesno(
            "\u4eba\u5de5\u89e3\u9664DrawGuard\u51bb\u7ed3",
            (
                f"\u5c06\u5199\u5165\u4e00\u6761 DrawGuard \u5ba1\u8ba1\u8bb0\u5f55\uff0c\u8868\u793a\u5df2\u4eba\u5de5\u590d\u6838\u56de\u6eda\u5931\u8d25\u6837\u672c\u5e76\u5141\u8bb8\u6062\u590d\u8c03\u53c2:\n\n"
                f"{rollback.get('summary_text', '-')}\n\n"
                "\u8fd9\u4e0d\u4f1a\u6539\u53d8\u5f53\u524d DrawGuard \u53c2\u6570\uff0c\u53ea\u4f1a\u5199\u5165 draw_guard_freeze_override \u5ba1\u8ba1\u7248\u672c\u3002\n"
                "\u540e\u7eed DrawGuard \u8c03\u53c2\u4ecd\u9700\u8981\u4eba\u5de5\u786e\u8ba4\u3002"
            ),
        )
        if not confirm:
            return
        status = apply_draw_release_guard_policy_update({}, source=f"draw_guard_freeze_override:{rollback_version}")
        version_id = str(status.get("version_id") or "-")
        self.status_var.set(f"DrawGuard\u8c03\u53c2\u51bb\u7ed3\u5df2\u4eba\u5de5\u89e3\u9664: {version_id}")
        messagebox.showinfo("DrawGuard\u51bb\u7ed3", "\u5df2\u5199\u5165 DrawGuard \u89e3\u9664\u51bb\u7ed3\u5ba1\u8ba1\u8bb0\u5f55\uff0c\u540e\u7eed\u8c03\u53c2\u5c06\u8f6c\u4e3a\u4eba\u5de5\u786e\u8ba4\u3002")
        self.open_strategy_library()

    def apply_strategy_allowlist_tuning(self, tuning: dict | object) -> None:
        if not isinstance(tuning, dict):
            messagebox.showinfo("\u653e\u884c\u95e8\u69db", "\u5f53\u524d\u6ca1\u6709\u53ef\u5e94\u7528\u7684\u95e8\u69db\u5efa\u8bae\u3002")
            return
        if str(tuning.get("action") or "") != "tighten":
            messagebox.showinfo("\u653e\u884c\u95e8\u69db", f"\u5f53\u524d\u5efa\u8bae\u4e3a: {tuning.get('label', '-')}\n\u4e0d\u9700\u8981\u5199\u5165\u65b0\u95e8\u69db\u3002")
            return
        update = tuning.get("policy_update") if isinstance(tuning.get("policy_update"), dict) else {}
        if not update:
            messagebox.showinfo("\u653e\u884c\u95e8\u69db", "\u5efa\u8bae\u4e2d\u6ca1\u6709\u53ef\u5199\u5165\u7684\u95e8\u69db\u53c2\u6570\u3002")
            return
        source_key = str(tuning.get("source") or "strategy_allowlist_tuning")
        if source_key not in {"strategy_allowlist_tuning", "release_quality_trend"}:
            source_key = "strategy_allowlist_tuning"
        guard = self._block_strategy_policy_tuning_if_needed(tuning, source_key)
        if guard is None:
            return
        current = get_strategy_admission_policy_status().get("policy", {})
        reason_text = "\n".join(str(item) for item in tuning.get("reasons", []) if item) if isinstance(tuning.get("reasons"), list) else "-"
        guard_text = f"\n\n\u8c03\u53c2\u95e8\u63a7:\n{guard.get('body', '-')}" if bool(guard.get("confirm_required")) else ""
        confirm = messagebox.askyesno(
            "\u5e94\u7528\u653e\u884c\u95e8\u69db",
            (
                f"\u5c06\u5199\u5165\u672c\u5730\u51c6\u5165\u7b56\u7565:\n\n"
                f"\u6700\u4f4e\u7f6e\u4fe1: {float(current.get('min_confidence', 0.5) or 0.5):.2f} -> {float(update.get('min_confidence', 0.5) or 0.5):.2f}\n"
                f"\u9ad8\u51c6\u7b56\u7565\u6570: {int(current.get('active_strategy_min', 1) or 1)} -> {int(update.get('active_strategy_min', 1) or 1)}\n"
                f"\u4e2d\u98ce\u9669\u653e\u884c: {'ON' if current.get('medium_risk_allowed', True) else 'OFF'} -> {'ON' if update.get('medium_risk_allowed', True) else 'OFF'}\n\n"
                f"\u539f\u56e0:\n{reason_text}\n\n\u786e\u8ba4\u540e\uff0c\u540e\u7eed\u5206\u6790\u4f1a\u6309\u65b0\u95e8\u69db\u5224\u5b9a\u6b63\u5f0f\u653e\u884c\u3002"
                f"{guard_text}"
            ),
        )
        if not confirm:
            return
        status = apply_strategy_admission_policy_update(update, source=source_key)
        policy = status.get("policy", {}) if isinstance(status.get("policy"), dict) else {}
        self.status_var.set(f"\u653e\u884c\u95e8\u69db\u5df2\u5e94\u7528: min={float(policy.get('min_confidence', 0) or 0):.2f}, high_strategy={int(policy.get('active_strategy_min', 1) or 1)}")
        messagebox.showinfo("\u653e\u884c\u95e8\u69db", "\u95e8\u69db\u5df2\u5199\u5165\u672c\u5730\u914d\u7f6e\uff0c\u540e\u7eed\u5206\u6790\u5c06\u6309\u65b0\u51c6\u5165\u7b56\u7565\u6267\u884c\u3002")
        self.open_strategy_library()

    def apply_draw_release_guard_tuning(self, tuning: dict | object) -> None:
        if not isinstance(tuning, dict):
            messagebox.showinfo("\u5e73\u5c40\u8c03\u53c2", "\u5f53\u524d\u6ca1\u6709\u53ef\u5e94\u7528\u7684\u5e73\u5c40\u62e6\u622a\u5efa\u8bae\u3002")
            return
        if str(tuning.get("action") or "") not in {"loosen_guard", "tighten_guard"}:
            messagebox.showinfo("\u5e73\u5c40\u8c03\u53c2", f"\u5f53\u524d\u5efa\u8bae\u4e3a: {tuning.get('label', '-')}\n\u4e0d\u9700\u8981\u5199\u5165\u65b0\u53c2\u6570\u3002")
            return
        update = tuning.get("policy_update") if isinstance(tuning.get("policy_update"), dict) else {}
        if not update:
            messagebox.showinfo("\u5e73\u5c40\u8c03\u53c2", "\u5efa\u8bae\u4e2d\u6ca1\u6709\u53ef\u5199\u5165\u7684\u5e73\u5c40\u62e6\u622a\u53c2\u6570\u3002")
            return
        guard = self._block_draw_release_guard_tuning_if_needed(tuning)
        if guard is None:
            return
        current = get_draw_release_guard_policy_status().get("policy", {})
        current = current if isinstance(current, dict) else {}
        next_buckets = update.get("weak_odds_buckets") if isinstance(update.get("weak_odds_buckets"), dict) else {}
        current_buckets = current.get("weak_odds_buckets") if isinstance(current.get("weak_odds_buckets"), dict) else {}
        reason_text = "\n".join(str(item) for item in tuning.get("reasons", []) if item) if isinstance(tuning.get("reasons"), list) else "-"
        guard_text = f"\n\nDrawGuard\u8c03\u53c2\u95e8\u63a7:\n{guard.get('body', '-')}" if bool(guard.get("confirm_required")) else ""
        confirm = messagebox.askyesno(
            "\u5e94\u7528\u5e73\u5c40\u62e6\u622a\u8c03\u53c2",
            (
                f"\u5c06\u5199\u5165\u672c\u5730\u5e73\u5c40\u62e6\u622a\u7b56\u7565:\n\n"
                f"\u62e6\u622a\u5206\u6570\u7ebf: {float(current.get('min_score', 0.58) or 0.58):.2f} -> {float(update.get('min_score', 0.58) or 0.58):.2f}\n"
                f"\u5f31\u8d54\u7387\u6876: {', '.join(sorted(str(key) for key in current_buckets)) or '-'} -> {', '.join(sorted(str(key) for key in next_buckets)) or '-'}\n\n"
                f"\u539f\u56e0:\n{reason_text}\n\n"
                f"\u786e\u8ba4\u540e\uff0c\u540e\u7eed\u5206\u6790\u4f1a\u6309\u65b0 DrawGuard \u53c2\u6570\u5224\u5b9a\u662f\u5426\u62e6\u622a\u5e73\u5c40\u63a5\u7ba1\u3002"
                f"{guard_text}"
            ),
        )
        if not confirm:
            return
        status = apply_draw_release_guard_policy_update(update, source=str(tuning.get("source") or "draw_release_guard_tuning"))
        policy = status.get("policy", {}) if isinstance(status.get("policy"), dict) else {}
        buckets = policy.get("weak_odds_buckets") if isinstance(policy.get("weak_odds_buckets"), dict) else {}
        self.status_var.set(
            f"\u5e73\u5c40\u62e6\u622a\u53c2\u6570\u5df2\u5e94\u7528: score_floor={float(policy.get('min_score', 0) or 0):.2f}, buckets={', '.join(sorted(str(key) for key in buckets)) or '-'}"
        )
        messagebox.showinfo("\u5e73\u5c40\u8c03\u53c2", "\u5e73\u5c40\u62e6\u622a\u53c2\u6570\u5df2\u5199\u5165\u672c\u5730\u914d\u7f6e\uff0c\u540e\u7eed\u5206\u6790\u5c06\u6309\u65b0\u7b56\u7565\u6267\u884c\u3002")
        self.open_strategy_library()

    def apply_agent_replay_guard_tuning(self, tuning: dict | object) -> None:
        if not isinstance(tuning, dict):
            messagebox.showinfo("Replay Guard", "\u5f53\u524d\u6ca1\u6709\u53ef\u5e94\u7528\u7684 Replay Guard \u5efa\u8bae\u3002")
            return
        if str(tuning.get("action") or "") not in {"tighten_guard", "loosen_guard"}:
            messagebox.showinfo("Replay Guard", f"\u5f53\u524d\u5efa\u8bae\u4e3a: {tuning.get('label', '-')}\n\u4e0d\u9700\u8981\u5199\u5165\u65b0\u53c2\u6570\u3002")
            return
        update = tuning.get("policy_update") if isinstance(tuning.get("policy_update"), dict) else {}
        if not update:
            messagebox.showinfo("Replay Guard", "\u5efa\u8bae\u4e2d\u6ca1\u6709\u53ef\u5199\u5165\u7684 Replay Guard \u53c2\u6570\u3002")
            return
        guard = self._block_strategy_policy_tuning_if_needed(tuning, "agent_replay_guard_tuning")
        if guard is None:
            return
        current = get_strategy_admission_policy_status().get("policy", {})
        reason_text = "\n".join(str(item) for item in tuning.get("reasons", []) if item) if isinstance(tuning.get("reasons"), list) else "-"
        guard_text = f"\n\n\u8c03\u53c2\u95e8\u63a7:\n{guard.get('body', '-')}" if bool(guard.get("confirm_required")) else ""
        confirm = messagebox.askyesno(
            "\u5e94\u7528 Replay Guard \u8c03\u53c2",
            (
                f"\u5c06\u5199\u5165\u672c\u5730 Replay Guard \u51c6\u5165\u53c2\u6570:\n\n"
                f"\u6700\u5c0f\u6837\u672c: {int(current.get('agent_replay_min_samples', 5) or 5)} -> {int(update.get('agent_replay_min_samples', 5) or 5)}\n"
                f"1X2\u5931\u8bef\u7ebf: {float(current.get('agent_replay_prediction_miss_threshold', 0.55) or 0.55):.2f} -> {float(update.get('agent_replay_prediction_miss_threshold', 0.55) or 0.55):.2f}\n"
                f"\u8ba9\u7403\u5931\u8bef\u7ebf: {float(current.get('agent_replay_handicap_miss_threshold', 0.60) or 0.60):.2f} -> {float(update.get('agent_replay_handicap_miss_threshold', 0.60) or 0.60):.2f}\n\n"
                f"\u539f\u56e0:\n{reason_text}\n\n\u786e\u8ba4\u540e\uff0c\u540e\u7eed\u5206\u6790\u4f1a\u6309\u65b0 Replay Guard \u95e8\u69db\u5224\u5b9a\u662f\u5426\u964d\u7ea7\u4e3a\u89c2\u5bdf\u3002"
                f"{guard_text}"
            ),
        )
        if not confirm:
            return
        status = apply_strategy_admission_policy_update(update, source="agent_replay_guard_tuning")
        policy = status.get("policy", {}) if isinstance(status.get("policy"), dict) else {}
        self.status_var.set(
            "Replay Guard \u53c2\u6570\u5df2\u5e94\u7528: "
            f"samples={int(policy.get('agent_replay_min_samples', 5) or 5)}, "
            f"1X2={float(policy.get('agent_replay_prediction_miss_threshold', 0) or 0):.2f}, "
            f"handicap={float(policy.get('agent_replay_handicap_miss_threshold', 0) or 0):.2f}"
        )
        messagebox.showinfo("Replay Guard", "Replay Guard \u8c03\u53c2\u5df2\u5199\u5165\u672c\u5730\u914d\u7f6e\uff0c\u540e\u7eed\u5206\u6790\u5c06\u6309\u65b0\u53c2\u6570\u6267\u884c\u3002")
        self.open_strategy_library()

    def rollback_latest_strategy_policy(self) -> None:
        history = get_strategy_admission_policy_history(limit=1)
        if not history:
            messagebox.showinfo("\u7b56\u7565\u53c2\u6570\u56de\u6eda", "\u5c1a\u65e0\u53ef\u56de\u6eda\u7684\u53c2\u6570\u7248\u672c\u3002")
            return
        latest = history[0]
        previous = latest.get("previous_policy") if isinstance(latest.get("previous_policy"), dict) else {}
        if not previous:
            messagebox.showinfo("\u7b56\u7565\u53c2\u6570\u56de\u6eda", "\u6700\u8fd1\u4e00\u6b21\u8c03\u53c2\u6ca1\u6709\u53ef\u6062\u590d\u7684\u4e0a\u4e00\u7248\u53c2\u6570\u3002")
            return
        policy_effect_review = build_strategy_policy_effect_review(
            get_strategy_admission_policy_history(limit=20),
            list(reversed(get_recent_settlements(limit=200))),
        )
        rollback_preview = build_strategy_policy_rollback_preview(
            latest,
            get_strategy_admission_policy_status().get("policy", {}),
            policy_effect_review,
        )
        if not bool(rollback_preview.get("available")):
            messagebox.showinfo("\u7b56\u7565\u53c2\u6570\u56de\u6eda", str(rollback_preview.get("reason") or "-"))
            return
        confirm = messagebox.askyesno(
            "\u56de\u6eda\u4e0a\u4e00\u7248\u7b56\u7565\u53c2\u6570",
            str(rollback_preview.get("confirm_text") or "-"),
        )
        if not confirm:
            return
        status = rollback_strategy_admission_policy()
        policy = status.get("policy", {}) if isinstance(status.get("policy"), dict) else {}
        self.status_var.set(
            f"\u7b56\u7565\u53c2\u6570\u5df2\u56de\u6eda: min={float(policy.get('min_confidence', 0) or 0):.2f}, "
            f"Replay={int(policy.get('agent_replay_min_samples', 5) or 5)}"
        )
        messagebox.showinfo("\u7b56\u7565\u53c2\u6570\u56de\u6eda", "\u5df2\u6062\u590d\u4e0a\u4e00\u7248\u7b56\u7565\u53c2\u6570\u3002")
        self.open_strategy_library()

    def rollback_latest_draw_guard_policy(self) -> None:
        history = get_draw_release_guard_policy_history(limit=1)
        if not history:
            messagebox.showinfo("DrawGuard\u56de\u6eda", "\u5c1a\u65e0\u53ef\u56de\u6eda\u7684 DrawGuard \u53c2\u6570\u7248\u672c\u3002")
            return
        latest = history[0]
        previous = latest.get("previous_policy") if isinstance(latest.get("previous_policy"), dict) else {}
        if not previous:
            messagebox.showinfo("DrawGuard\u56de\u6eda", "\u6700\u8fd1\u4e00\u6b21 DrawGuard \u8c03\u53c2\u6ca1\u6709\u53ef\u6062\u590d\u7684\u4e0a\u4e00\u7248\u53c2\u6570\u3002")
            return
        current = get_draw_release_guard_policy_status().get("policy", {})
        current = current if isinstance(current, dict) else {}
        current_buckets = current.get("weak_odds_buckets") if isinstance(current.get("weak_odds_buckets"), dict) else {}
        previous_buckets = previous.get("weak_odds_buckets") if isinstance(previous.get("weak_odds_buckets"), dict) else {}
        confirm = messagebox.askyesno(
            "DrawGuard\u56de\u6eda\u4e0a\u4e00\u7248",
            (
                f"\u5c06\u6062\u590d DrawGuard \u4e0a\u4e00\u7248\u53c2\u6570:\n\n"
                f"\u7248\u672c: {latest.get('version_id', '-')}\n"
                f"\u6765\u6e90: {latest.get('source', '-')}\n"
                f"\u5206\u6570\u7ebf: {float(current.get('min_score', 0.58) or 0.58):.2f} -> {float(previous.get('min_score', 0.58) or 0.58):.2f}\n"
                f"\u5f31\u8d54\u7387\u6876: {', '.join(sorted(str(key) for key in current_buckets)) or '-'} -> {', '.join(sorted(str(key) for key in previous_buckets)) or '-'}\n\n"
                "\u786e\u8ba4\u540e\uff0c\u540e\u7eed\u5206\u6790\u5c06\u6309\u56de\u6eda\u540e\u7684 DrawGuard \u53c2\u6570\u6267\u884c\u3002"
            ),
        )
        if not confirm:
            return
        status = rollback_draw_release_guard_policy()
        policy = status.get("policy", {}) if isinstance(status.get("policy"), dict) else {}
        buckets = policy.get("weak_odds_buckets") if isinstance(policy.get("weak_odds_buckets"), dict) else {}
        self.status_var.set(
            f"DrawGuard\u5df2\u56de\u6eda: score_floor={float(policy.get('min_score', 0) or 0):.2f}, buckets={', '.join(sorted(str(key) for key in buckets)) or '-'}"
        )
        messagebox.showinfo("DrawGuard\u56de\u6eda", "DrawGuard \u53c2\u6570\u5df2\u6062\u590d\u4e0a\u4e00\u7248\u3002")
        self.open_strategy_library()

    def open_policy_effect_detail_window(self, policy_effect: dict | object) -> None:
        review = policy_effect if isinstance(policy_effect, dict) else {}
        rows = review.get("rows", []) if isinstance(review.get("rows"), list) else []
        window = tk.Toplevel(self.root)
        window.title("\u53c2\u6570\u751f\u6548\u590d\u76d8\u8be6\u60c5")
        window.configure(bg=BG)
        window.geometry("1080x680")
        header = tk.Frame(window, bg=BG)
        header.pack(fill=tk.X, padx=16, pady=(14, 8))
        tk.Label(
            header,
            text=f"\u53c2\u6570\u751f\u6548\u590d\u76d8 | {review.get('summary_text', '-')}",
            bg=BG,
            fg=TEXT,
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            header,
            text="\u9009\u62e9\u4e0a\u65b9\u7248\u672c\u884c\uff0c\u4e0b\u65b9\u67e5\u770b\u8be5\u53c2\u6570\u751f\u6548\u671f\u95f4\u7684\u5177\u4f53\u8d5b\u4e8b\u6837\u672c\u3002",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor=tk.W, pady=(4, 0))
        diagnostic_bar = tk.Frame(window, bg=PANEL_2, highlightbackground="#172638", highlightthickness=1)
        diagnostic_bar.pack(fill=tk.X, padx=16, pady=(0, 10))
        diagnostic_var = tk.StringVar(value="\u8bf7\u9009\u62e9\u4e00\u4e2a\u53c2\u6570\u7248\u672c\u67e5\u770b\u8bca\u65ad\u3002")
        diagnostic_label = tk.Label(
            diagnostic_bar,
            textvariable=diagnostic_var,
            bg=PANEL_2,
            fg=MUTED,
            font=("Microsoft YaHei UI", 10),
            justify=tk.LEFT,
            wraplength=780,
        )
        diagnostic_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12, pady=9)
        rollback_button = tk.Button(
            diagnostic_bar,
            text="\u56de\u6eda\u4e0a\u4e00\u7248",
            command=lambda: (window.destroy(), self.rollback_latest_strategy_policy()),
            bg=RED,
            fg="white",
            activebackground="#d94743",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=6,
            state=tk.DISABLED,
        )
        rollback_button.pack(side=tk.RIGHT, padx=12, pady=8)

        panes = tk.PanedWindow(window, orient=tk.VERTICAL, bg=BG, sashwidth=5, bd=0)
        panes.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        version_frame = tk.Frame(panes, bg=BG)
        sample_frame = tk.Frame(panes, bg=BG)
        panes.add(version_frame, minsize=180)
        panes.add(sample_frame, minsize=260)

        self._configure_dark_tree_style("PolicyEffect.Treeview", master=window, rowheight=28)

        version_columns = ("version", "time", "source", "status", "samples", "allow", "replay", "action")
        version_tree = ttk.Treeview(version_frame, columns=version_columns, show="headings", style="PolicyEffect.Treeview", height=7)
        headings = {
            "version": "\u7248\u672c",
            "time": "\u8c03\u53c2\u65f6\u95f4",
            "source": "\u6765\u6e90",
            "status": "\u6548\u679c",
            "samples": "\u6837\u672c",
            "allow": "\u653e\u884c\u547d\u4e2d",
            "replay": "Replay\u51c0\u503c",
            "action": "\u5efa\u8bae",
        }
        widths = {"version": 135, "time": 145, "source": 155, "status": 100, "samples": 65, "allow": 95, "replay": 80, "action": 130}
        for col in version_columns:
            version_tree.heading(col, text=headings[col])
            version_tree.column(col, width=widths[col], anchor=tk.W, stretch=True)
        version_scroll = tk.Scrollbar(version_frame, orient=tk.VERTICAL, command=version_tree.yview)
        version_tree.configure(yscrollcommand=version_scroll.set)
        version_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        version_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        sample_columns = ("time", "match", "decision", "prediction", "handicap", "replay", "agent", "net", "reason")
        sample_tree = ttk.Treeview(sample_frame, columns=sample_columns, show="headings", style="PolicyEffect.Treeview", height=13)
        sample_headings = {
            "time": "\u65f6\u95f4",
            "match": "\u8d5b\u4e8b",
            "decision": "\u51c6\u5165",
            "prediction": "1X2",
            "handicap": "\u8ba9\u7403",
            "replay": "Replay",
            "agent": "Agent",
            "net": "\u51c0\u503c\u8d21\u732e",
            "reason": "\u5f71\u54cd\u539f\u56e0",
        }
        sample_widths = {"time": 130, "match": 255, "decision": 70, "prediction": 60, "handicap": 60, "replay": 70, "agent": 105, "net": 70, "reason": 220}
        for col in sample_columns:
            sample_tree.heading(col, text=sample_headings[col])
            sample_tree.column(col, width=sample_widths[col], anchor=tk.W, stretch=True)
        sample_scroll = tk.Scrollbar(sample_frame, orient=tk.VERTICAL, command=sample_tree.yview)
        sample_tree.configure(yscrollcommand=sample_scroll.set)
        sample_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sample_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        row_by_iid: dict[str, dict] = {}
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            iid = str(index)
            row_by_iid[iid] = row
            version_tree.insert(
                "",
                tk.END,
                iid=iid,
                values=(
                    row.get("version_id", "-"),
                    row.get("updated_at", "-"),
                    row.get("source", "-"),
                    row.get("effect_label", "-"),
                    row.get("sample_count", 0),
                    row.get("allow_hit_rate_text", "-"),
                    f"{int(row.get('replay_guard_net', 0) or 0):+d}",
                    (row.get("negative_diagnostics", {}) if isinstance(row.get("negative_diagnostics"), dict) else {}).get("action_label", "-"),
                ),
            )

        def show_samples(row: dict | None) -> None:
            for item in sample_tree.get_children():
                sample_tree.delete(item)
            sample_rows = row.get("sample_rows", []) if isinstance(row, dict) and isinstance(row.get("sample_rows"), list) else []
            diagnostics = row.get("negative_diagnostics", {}) if isinstance(row, dict) and isinstance(row.get("negative_diagnostics"), dict) else {}
            if isinstance(row, dict):
                diagnostic_var.set(str(diagnostics.get("summary_text") or row.get("body") or "-"))
                is_latest = rows and isinstance(rows[0], dict) and row.get("version_id") == rows[0].get("version_id")
                rollback_button.configure(state=tk.NORMAL if is_latest and bool(diagnostics.get("rollback_recommended")) else tk.DISABLED)
            else:
                diagnostic_var.set("\u8bf7\u9009\u62e9\u4e00\u4e2a\u53c2\u6570\u7248\u672c\u67e5\u770b\u8bca\u65ad\u3002")
                rollback_button.configure(state=tk.DISABLED)
            for sample in sample_rows:
                if not isinstance(sample, dict):
                    continue
                sample_tree.insert(
                    "",
                    tk.END,
                    values=(
                        sample.get("time", "-"),
                        sample.get("title", "-"),
                        sample.get("decision", "-"),
                        sample.get("prediction_result", "-"),
                        sample.get("handicap_result", "-"),
                        sample.get("replay_guard", "-"),
                        sample.get("replay_agent", "-"),
                        f"{int(sample.get('replay_net_hint', 0) or 0):+d}",
                        sample.get("drag_reason_text", "-"),
                    ),
                )

        def on_select(_event=None) -> None:
            selected = version_tree.selection()
            show_samples(row_by_iid.get(selected[0]) if selected else None)

        version_tree.bind("<<TreeviewSelect>>", on_select)
        children = version_tree.get_children()
        if children:
            version_tree.selection_set(children[0])
            show_samples(row_by_iid.get(children[0]))

    def open_policy_governance_event_window(
        self,
        policy_effect: dict | object,
        *,
        draw_release_guard_policy_history: list[dict] | object | None = None,
        draw_release_guard_tuning_effect_review: dict | object | None = None,
        draw_release_guard_rollback_effect_review: dict | object | None = None,
        draw_release_guard_freeze_override_status: dict | object | None = None,
        draw_release_guard_tuning_guard: dict | object | None = None,
    ) -> None:
        review = policy_effect if isinstance(policy_effect, dict) else {}
        base_governance = build_strategy_policy_governance_event_summary(
            review,
            draw_release_guard_policy_history=draw_release_guard_policy_history or [],
            draw_release_guard_tuning_effect_review=draw_release_guard_tuning_effect_review,
            draw_release_guard_rollback_effect_review=draw_release_guard_rollback_effect_review,
            draw_release_guard_freeze_override_status=draw_release_guard_freeze_override_status,
            draw_release_guard_tuning_guard=draw_release_guard_tuning_guard,
        )

        def as_text(value: object, default: str = "-") -> str:
            text = str(value if value is not None else "").strip()
            return text or default

        def as_int(value: object) -> int:
            try:
                return int(value or 0)
            except (TypeError, ValueError):
                return 0

        window = tk.Toplevel(self.root)
        window.title("??????")
        window.configure(bg=BG)
        window.geometry("1120x640")
        window.minsize(980, 540)

        header = tk.Frame(window, bg=BG)
        header.pack(fill=tk.X, padx=16, pady=(14, 8))
        title_var = tk.StringVar(value=f"?????? | {base_governance.get('summary_text', '-')}")
        meta_var = tk.StringVar(value=f"{base_governance.get('latest_summary') or '??????'}\n{base_governance.get('filter_summary_text') or '?? ?=?? / ??=?? | ?? 0/0'}")
        tk.Label(
            header,
            textvariable=title_var,
            bg=BG,
            fg=TEXT,
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            header,
            textvariable=meta_var,
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 10),
            wraplength=1040,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 0))

        filter_bar = tk.Frame(window, bg=BG)
        filter_bar.pack(fill=tk.X, padx=16, pady=(0, 10))
        domain_frame = tk.Frame(filter_bar, bg=BG)
        domain_frame.pack(side=tk.LEFT, padx=(0, 12))
        tk.Label(domain_frame, text="???", bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)
        domain_var = tk.StringVar(value="??")
        domain_combo = ttk.Combobox(
            domain_frame,
            state="readonly",
            textvariable=domain_var,
            values=list(base_governance.get("domain_options") or ["??", "strategy", "draw_guard"]),
            width=16,
        )
        domain_combo.pack(anchor=tk.W, pady=(4, 0))

        event_frame = tk.Frame(filter_bar, bg=BG)
        event_frame.pack(side=tk.LEFT)
        tk.Label(event_frame, text="????", bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)
        event_var = tk.StringVar(value="??")
        event_combo = ttk.Combobox(
            event_frame,
            state="readonly",
            textvariable=event_var,
            values=list(base_governance.get("event_type_options") or ["??"]),
            width=24,
        )
        event_combo.pack(anchor=tk.W, pady=(4, 0))

        body = tk.PanedWindow(window, orient=tk.VERTICAL, bg=BG, sashwidth=5, bd=0)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))
        table_frame = tk.Frame(body, bg=BG)
        detail_frame = tk.Frame(body, bg=BG)
        body.add(table_frame, minsize=250)
        body.add(detail_frame, minsize=160)

        self._configure_dark_tree_style("PolicyGovernance.Treeview", master=window, rowheight=28)
        columns = ("time", "version", "event", "source", "related", "effect", "allow", "replay")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="PolicyGovernance.Treeview", height=10)
        headings = {
            "time": "??",
            "version": "??",
            "event": "??",
            "source": "??",
            "related": "????",
            "effect": "??",
            "allow": "????",
            "replay": "Replay??",
        }
        widths = {"time": 145, "version": 110, "event": 110, "source": 190, "related": 105, "effect": 125, "allow": 105, "replay": 85}
        for col in columns:
            tree.heading(col, text=headings[col])
            tree.column(col, width=widths[col], anchor=tk.W, stretch=True)
        scroll = tk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        detail = tk.Text(
            detail_frame,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            height=7,
            padx=12,
            pady=10,
        )
        detail_scroll = tk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=detail.yview)
        detail.configure(yscrollcommand=detail_scroll.set)
        detail.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        row_by_iid: dict[str, dict] = {}

        def show_detail(row: dict | None) -> None:
            if isinstance(row, dict):
                if str(row.get("domain") or "") == "draw_guard":
                    metric_line = (
                        f"DrawGuard样本: {as_int(row.get('sample_count'))} | "
                        f"拦截 {as_int(row.get('draw_guard_blocked_count'))} | "
                        f"避免 {as_text(row.get('draw_guard_avoid_rate_text'))} | "
                        f"错过 {as_text(row.get('draw_guard_missed_rate_text'))}"
                    )
                else:
                    metric_line = (
                        f"样本: {as_int(row.get('sample_count'))} | 已知放行 {as_int(row.get('known_allow_count'))} | "
                        f"Replay净值 {as_int(row.get('replay_guard_net')):+d}"
                    )
                content = (
                    f"{as_text(row.get('summary'))}\n\n"
                    f"领域: {as_text(row.get('domain'))}\n"
                    f"事件类型: {as_text(row.get('event_type'))}\n"
                    f"来源: {as_text(row.get('source'))}\n"
                    f"关联版本: {as_text(row.get('related_version_id'))}\n"
                    f"{metric_line}\n"
                    f"说明: {as_text(row.get('description'))}"
                )
            else:
                content = "暂无匹配的治理事件。"
            detail.configure(state=tk.NORMAL)
            detail.delete("1.0", tk.END)
            detail.insert("1.0", content)
            detail.configure(state=tk.DISABLED)


        def refresh_view(_event=None) -> None:
            summary = build_strategy_policy_governance_event_summary(
                review,
                draw_release_guard_policy_history=draw_release_guard_policy_history or [],
                draw_release_guard_tuning_effect_review=draw_release_guard_tuning_effect_review,
                draw_release_guard_rollback_effect_review=draw_release_guard_rollback_effect_review,
                draw_release_guard_freeze_override_status=draw_release_guard_freeze_override_status,
                draw_release_guard_tuning_guard=draw_release_guard_tuning_guard,
                domain_filter=domain_var.get(),
                event_type_filter=event_var.get(),
            )
            rows = [row for row in summary.get("rows", []) if isinstance(row, dict)] if isinstance(summary.get("rows"), list) else []
            title_var.set(f"?????? | {summary.get('summary_text', '-')}")
            latest_summary = as_text(summary.get("latest_summary"), "??????????") if rows else "??????????"
            meta_var.set(f"{latest_summary}\n{summary.get('filter_summary_text') or '?? ?=?? / ??=?? | ?? 0/0'}")
            tree.delete(*tree.get_children())
            row_by_iid.clear()
            for index, row in enumerate(rows):
                iid = str(index)
                row_by_iid[iid] = row
                tree.insert(
                    "",
                    tk.END,
                    iid=iid,
                    values=(
                        as_text(row.get("updated_at")),
                        as_text(row.get("version_id")),
                        as_text(row.get("event_label")),
                        as_text(row.get("source")),
                        as_text(row.get("related_version_id")),
                        as_text(row.get("effect_label")),
                        as_text(row.get("allow_hit_rate_text")),
                        f"{as_int(row.get('replay_guard_net')):+d}",
                    ),
                )
            if rows:
                tree.selection_set(tree.get_children()[0])
                show_detail(rows[0])
            else:
                show_detail(None)

        def on_select(_event=None) -> None:
            selected = tree.selection()
            show_detail(row_by_iid.get(selected[0]) if selected else None)

        tree.bind("<<TreeviewSelect>>", on_select)
        domain_combo.bind("<<ComboboxSelected>>", refresh_view)
        event_combo.bind("<<ComboboxSelected>>", refresh_view)
        if rows := base_governance.get("rows"):
            refresh_view()
        else:
            refresh_view()


    def open_statsbomb_event_sandbox_window(self) -> None:
        baseline = get_statsbomb_event_baseline()
        sandbox = build_statsbomb_event_sandbox_summary(baseline, limit=60)
        window = tk.Toplevel(self.root)
        window.title("StatsBomb \u5386\u53f2\u4e8b\u4ef6\u590d\u76d8\u6c99\u76d2")
        window.geometry("1180x760")
        window.configure(bg=BG)

        header = tk.Frame(window, bg=BG)
        header.pack(fill=tk.X, padx=18, pady=(16, 10))
        tk.Label(
            header,
            text="StatsBomb \u5386\u53f2\u4e8b\u4ef6\u590d\u76d8\u6c99\u76d2",
            bg=BG,
            fg=TEXT,
            font=("Microsoft YaHei UI", 15, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            header,
            text=f"{sandbox.get('summary_text', '-')}  |  {sandbox.get('leakage_note', '-')}",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 10),
            wraplength=1080,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(5, 0))

        body = tk.Frame(window, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 16))
        top = tk.Frame(body, bg=BG)
        top.pack(fill=tk.X, pady=(0, 12))
        left = self._card(top, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        right = self._card(top, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u8d5b\u4e8b\u57fa\u7ebf", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 11, "bold")).pack(anchor=tk.W, padx=12, pady=(10, 4))
        for row in sandbox.get("competition_rows", []) if isinstance(sandbox.get("competition_rows"), list) else []:
            if isinstance(row, dict):
                tk.Label(
                    left,
                    text=f"{row.get('label', '-')}\n{row.get('body', '-')}",
                    bg=PANEL,
                    fg=MUTED,
                    font=("Microsoft YaHei UI", 9),
                    justify=tk.LEFT,
                    wraplength=510,
                ).pack(anchor=tk.W, padx=12, pady=(2, 8))

        tk.Label(right, text="xG\u5dee\u503c\u5206\u6876", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 11, "bold")).pack(anchor=tk.W, padx=12, pady=(10, 4))
        for row in sandbox.get("bucket_rows", []) if isinstance(sandbox.get("bucket_rows"), list) else []:
            if isinstance(row, dict):
                tk.Label(
                    right,
                    text=f"{row.get('label', '-')}: {row.get('body', '-')}",
                    bg=PANEL,
                    fg=MUTED,
                    font=("Microsoft YaHei UI", 9),
                    justify=tk.LEFT,
                    wraplength=510,
                ).pack(anchor=tk.W, padx=12, pady=(2, 8))

        table_frame = self._card(body, PANEL)
        table_frame.pack(fill=tk.BOTH, expand=True)
        self._configure_dark_tree_style("StatsBombSandbox.Treeview", master=window, rowheight=28)
        columns = ("date", "league", "match", "score", "xg", "shots", "diagnosis", "events")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="StatsBombSandbox.Treeview", height=15)
        headings = {
            "date": "\u65e5\u671f",
            "league": "\u8d5b\u4e8b",
            "match": "\u5bf9\u9635",
            "score": "\u6bd4\u5206",
            "xg": "xG",
            "shots": "\u5c04\u95e8",
            "diagnosis": "\u590d\u76d8\u8bca\u65ad",
            "events": "\u4e8b\u4ef6",
        }
        widths = {"date": 96, "league": 120, "match": 210, "score": 70, "xg": 90, "shots": 80, "diagnosis": 240, "events": 70}
        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths[column], anchor=tk.W, stretch=column in {"match", "diagnosis"})
        tree_scroll = tk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=tree_scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)

        detail = tk.Text(
            body,
            wrap=tk.WORD,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            height=4,
            font=("Microsoft YaHei UI", 10),
            padx=12,
            pady=10,
        )
        detail.pack(fill=tk.X, pady=(12, 0))

        rows = sandbox.get("variance_rows", []) if isinstance(sandbox.get("variance_rows"), list) else []
        if not rows:
            rows = sandbox.get("rows", []) if isinstance(sandbox.get("rows"), list) else []
        row_by_iid: dict[str, dict] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            iid = tree.insert(
                "",
                tk.END,
                values=(
                    row.get("match_date", "-"),
                    row.get("league", "-"),
                    row.get("title", "-"),
                    row.get("score", "-"),
                    row.get("xg", "-"),
                    row.get("shots", "-"),
                    row.get("diagnosis", "-"),
                    row.get("event_count", 0),
                ),
            )
            row_by_iid[iid] = row

        def show_detail(row: dict | None, *, evaluation_only: bool = False) -> None:
            case = row.get("evaluation_case") if isinstance(row, dict) and isinstance(row.get("evaluation_case"), dict) else {}
            sample_body = str((row or {}).get("body") or "\u8bf7\u9009\u62e9\u4e00\u573a\u5386\u53f2\u6837\u672c\u67e5\u770b\u590d\u76d8\u8bca\u65ad\u3002")
            case_body = str(case.get("body") or "")
            content = case_body if evaluation_only and case_body else sample_body
            if case_body and not evaluation_only:
                content = f"{sample_body}\n\nEvaluation Agent \u6a21\u62df\u590d\u76d8\u6848\u4f8b\n{case_body}"
            detail.configure(state=tk.NORMAL)
            detail.delete("1.0", tk.END)
            detail.insert("1.0", content)
            detail.configure(state=tk.DISABLED)

        def on_select(_event=None) -> None:
            selected = tree.selection()
            show_detail(row_by_iid.get(selected[0]) if selected else None)

        def show_selected_evaluation_case() -> None:
            selected = tree.selection()
            row = row_by_iid.get(selected[0]) if selected else None
            show_detail(row, evaluation_only=True)

        def export_sandbox_report() -> None:
            now = datetime.now()
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            path = REPORT_DIR / build_statsbomb_event_sandbox_report_filename(now)
            path.write_text(
                "\n".join(build_statsbomb_event_sandbox_report_lines(baseline, generated_at=now, limit=30)),
                encoding="utf-8",
            )
            self.status_var.set(f"StatsBomb\u590d\u76d8\u6c99\u76d2\u62a5\u544a\u5df2\u5bfc\u51fa: {path.name}")
            messagebox.showinfo("StatsBomb\u6c99\u76d2", f"\u5df2\u751f\u6210\u590d\u76d8\u62a5\u544a:\n{path}")

        tree.bind("<<TreeviewSelect>>", on_select)
        children = tree.get_children()
        if children:
            tree.selection_set(children[0])
            show_detail(row_by_iid.get(children[0]))
        else:
            show_detail(None)
        tk.Button(
            header,
            text="\u751f\u6210Evaluation\u6848\u4f8b",
            command=show_selected_evaluation_case,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=7,
        ).pack(side=tk.RIGHT, pady=(8, 0))
        tk.Button(
            header,
            text="\u5bfc\u51fa\u590d\u76d8\u62a5\u544a",
            command=export_sandbox_report,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10), pady=(8, 0))
        self.status_var.set(f"StatsBomb\u6c99\u76d2: {sandbox.get('summary_text', '-')}")

    def open_strategy_library(self) -> None:
        self.current_nav_index = 4
        self.current_view = "strategy"
        self._refresh_nav_highlight()
        status = get_high_accuracy_strategy_status()
        admission_status = get_strategy_admission_policy_status()
        draw_guard_status = get_draw_release_guard_policy_status()
        admission_policy = admission_status.get("policy", {}) if isinstance(admission_status.get("policy"), dict) else {}
        draw_guard_policy = draw_guard_status.get("policy", {}) if isinstance(draw_guard_status.get("policy"), dict) else {}
        settlements = list(reversed(get_recent_settlements(limit=200)))
        policy_history = get_strategy_admission_policy_history(limit=20)
        draw_guard_history = get_draw_release_guard_policy_history(limit=20)
        release_loop = self._strategy_release_recovery_loop(settlements)
        historical_replay = build_historical_strategy_replay_samples(status, historical_limit=50000, max_samples=1000)
        dashboard = build_high_accuracy_strategy_dashboard(
            status,
            settlements,
            policy_history,
            get_statsbomb_event_baseline(),
            get_statsbomb_sandbox_fewshot_memory(),
            historical_replay,
            draw_guard_status,
            draw_guard_history,
            video_review_fewshot_memory=get_video_review_fewshot_memory(),
            statsbomb_review_training_samples=get_statsbomb_review_training_samples(),
        )
        release_pool_rows = self._strategy_release_pool_rows(settlements, release_loop=release_loop)
        shell = self._page_shell(
            "\u7b56\u7565\u770b\u677f",
            "\u5c55\u793a\u9ad8\u51c6\u7b56\u7565\u6c60\u3001\u56de\u6d4b\u5206\u5c42\u3001\u7a33\u5b9a\u6027\u548c\u771f\u5b9e\u7ed3\u7b97\u53cd\u9988",
        )

        header = tk.Frame(shell, bg=BG)
        header.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            header,
            text=(
                f"\u72b6\u6001: {'ON' if dashboard.get('enabled') else 'OFF'} | \u66f4\u65b0: {dashboard.get('updated_at', '-')} | "
                f"\u51c6\u5165 min={float(admission_policy.get('min_confidence', 0.5) or 0.5):.2f} / "
                f"\u9ad8\u51c6\u6570 {int(admission_policy.get('active_strategy_min', 1) or 1)} / "
                f"\u4e2d\u98ce\u9669 {'ON' if admission_policy.get('medium_risk_allowed', True) else 'OFF'} / "
                f"Replay {int(admission_policy.get('agent_replay_min_samples', 5) or 5)}@"
                f"{float(admission_policy.get('agent_replay_prediction_miss_threshold', 0.55) or 0.55):.2f}/"
                f"{float(admission_policy.get('agent_replay_handicap_miss_threshold', 0.60) or 0.60):.2f} / "
                f"DrawGuard {float(draw_guard_policy.get('min_score', 0.58) or 0.58):.2f}"
            ),
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 10),
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        primary_tools = tk.Frame(shell, bg=BG)
        primary_tools.pack(fill=tk.X, pady=(0, 6))
        self._strategy_toolbar_button(primary_tools, "\u5237\u65b0\u770b\u677f", self.open_strategy_library)
        self._strategy_toolbar_button(primary_tools, "\u8fdb\u7a0b\u9ad8\u51c6\u56de\u6d4b", self.run_high_accuracy_strategy_backtest_task)
        self._strategy_toolbar_button(primary_tools, "\u5bfc\u51fa\u653e\u884c\u6e05\u5355", self.export_strategy_allowlist, primary=True)
        self._strategy_toolbar_button(primary_tools, "\u653e\u884c\u56de\u6536\u95ed\u73af", self.open_strategy_release_recovery_loop_window)
        self._strategy_toolbar_button(
            primary_tools,
            "\u5e94\u7528Replay\u5efa\u8bae",
            lambda tuning=dashboard.get("agent_replay_guard_tuning", {}): self.apply_agent_replay_guard_tuning(tuning),
        )
        self._strategy_toolbar_button(
            primary_tools,
            "\u5e94\u7528\u95e8\u69db\u5efa\u8bae",
            lambda tuning=dashboard.get("allowlist_tuning", {}): self.apply_strategy_allowlist_tuning(tuning),
        )
        self._strategy_toolbar_button(
            primary_tools,
            "\u5e94\u7528\u5e73\u5c40\u8c03\u53c2",
            lambda tuning=dashboard.get("draw_release_guard_tuning", {}): self.apply_draw_release_guard_tuning(tuning),
        )

        audit_tools = tk.Frame(shell, bg=BG)
        audit_tools.pack(fill=tk.X, pady=(0, 12))
        self._strategy_toolbar_button(audit_tools, "\u5ba1\u8ba1\u5386\u53f2", self.open_strategy_policy_audit_history)
        self._strategy_toolbar_button(audit_tools, "\u5bfc\u51fa\u8c03\u53c2\u5ba1\u8ba1", self.export_strategy_policy_audit_report)
        self._strategy_toolbar_button(
            audit_tools,
            "\u6cbb\u7406\u4e8b\u4ef6",
            lambda review=dashboard.get("policy_effect_review", {}), dg_history=draw_guard_history, dg_tuning=dashboard.get("draw_release_guard_tuning_effect", {}), dg_rollback=dashboard.get("draw_release_guard_rollback_effect", {}), dg_freeze=dashboard.get("draw_release_guard_freeze_override", {}), dg_guard=dashboard.get("draw_release_guard_tuning_guard", {}): self.open_policy_governance_event_window(
                review,
                draw_release_guard_policy_history=dg_history,
                draw_release_guard_tuning_effect_review=dg_tuning,
                draw_release_guard_rollback_effect_review=dg_rollback,
                draw_release_guard_freeze_override_status=dg_freeze,
                draw_release_guard_tuning_guard=dg_guard,
            ),
        )
        self._strategy_toolbar_button(audit_tools, "\u89e3\u9664\u8c03\u53c2\u51bb\u7ed3", self.apply_strategy_policy_freeze_override)
        self._strategy_toolbar_button(audit_tools, "\u89e3\u9664DrawGuard\u51bb\u7ed3", self.apply_draw_release_guard_freeze_override)
        self._strategy_toolbar_button(audit_tools, "StatsBomb\u8865\u6837", self.export_statsbomb_fewshot_backfill_report)
        self._strategy_toolbar_button(audit_tools, "StatsBomb\u8349\u7a3f", self.export_statsbomb_fewshot_draft)
        self._strategy_toolbar_button(audit_tools, "StatsBomb\u9884\u89c8", self.preview_statsbomb_fewshot_merge_bundle)
        self._strategy_toolbar_button(audit_tools, "StatsBomb\u5e94\u7528", self.apply_statsbomb_fewshot_merge_bundle, danger=True)
        self._strategy_toolbar_button(audit_tools, "StatsBomb\u56de\u6eda", self.rollback_statsbomb_fewshot_memory, danger=True)
        self._strategy_toolbar_button(audit_tools, "StatsBomb\u5ba1\u8ba1", self.export_statsbomb_fewshot_memory_audit)
        self._strategy_toolbar_button(
            audit_tools,
            "\u751f\u6548\u8be6\u60c5",
            lambda review=dashboard.get("policy_effect_review", {}): self.open_policy_effect_detail_window(review),
        )
        self._strategy_toolbar_button(audit_tools, "StatsBomb\u6837\u672c", self.open_statsbomb_event_sandbox_window)
        self._strategy_toolbar_button(audit_tools, "\u56de\u6edaDrawGuard", self.rollback_latest_draw_guard_policy, danger=True)
        self._strategy_toolbar_button(audit_tools, "\u56de\u6eda\u4e0a\u4e00\u7248", self.rollback_latest_strategy_policy, danger=True)
        tk.Label(
            audit_tools,
            text="\u53c2\u6570\u5ba1\u8ba1\u4e0e\u56de\u6eda",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 10),
        ).pack(side=tk.LEFT)

        scroll_wrap = tk.Frame(shell, bg=BG)
        scroll_wrap.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(scroll_wrap, bg=BG, bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(scroll_wrap, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        content = tk.Frame(canvas, bg=BG)
        window_id = canvas.create_window((0, 0), window=content, anchor=tk.NW)
        content.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))

        top = tk.Frame(content, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        self._strategy_metric_grid(top, dashboard.get("metrics", []), columns=4)

        freeze_alerts = build_strategy_policy_freeze_alerts(
            dashboard.get("freeze_override_status", {}),
            dashboard.get("draw_release_guard_freeze_override", {}),
        )
        freeze_cards = [item for item in freeze_alerts.get("alerts", []) if isinstance(item, dict)] if isinstance(freeze_alerts, dict) else []
        if freeze_cards:
            freeze_wrap = tk.Frame(content, bg=BG)
            freeze_wrap.pack(fill=tk.X, pady=(0, 16))
            tk.Label(freeze_wrap, text="????", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(2, 8))
            freeze_row = tk.Frame(freeze_wrap, bg=BG)
            freeze_row.pack(fill=tk.X)
            for index, alert in enumerate(freeze_cards[:2]):
                column = tk.Frame(freeze_row, bg=BG)
                column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8) if index == 0 else (8, 0))
                self._alert_card(
                    column,
                    str(alert.get("title") or "-"),
                    str(alert.get("body") or "-"),
                    tone=str(alert.get("tone") or "warning"),
                )

        body = tk.Frame(content, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = tk.Frame(body, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = tk.Frame(body, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._strategy_section_title(left, "\u5f53\u524d\u7b56\u7565\u6c60", first=True)
        pool_rows = dashboard.get("pool_rows", [])
        if pool_rows:
            for row in pool_rows:
                if isinstance(row, dict):
                    self._strategy_row(left, str(row.get("title") or "-"), str(row.get("body") or "-"))
        else:
            self._strategy_row(left, "\u6682\u65e0\u53ef\u7528\u7b56\u7565", "\u8bf7\u5148\u6267\u884c\u9ad8\u51c6\u7b56\u7565\u56de\u6d4b\uff0c\u8ba9\u7cfb\u7edf\u4ece\u5386\u53f2\u6837\u672c\u4e2d\u751f\u6210\u7b56\u7565\u6c60\u3002")

        live_feedback_loop = dashboard.get("live_feedback_loop", {}) if isinstance(dashboard.get("live_feedback_loop"), dict) else {}
        self._strategy_section_title(left, "\u9ad8\u51c6\u7b56\u7565\u5b9e\u76d8\u53cd\u9988\u95ed\u73af")
        feedback_rows = live_feedback_loop.get("rows", []) if isinstance(live_feedback_loop.get("rows"), list) else []
        if feedback_rows:
            for row in feedback_rows:
                if isinstance(row, dict):
                    self._strategy_row(left, str(row.get("title") or "-"), str(row.get("body") or "-"))
        else:
            self._strategy_row(
                left,
                "\u6682\u65e0\u5b9e\u76d8\u53cd\u9988\u72b6\u6001",
                "\u7b56\u7565\u6c60\u751f\u6210\u540e\uff0c\u8fd9\u91cc\u4f1a\u8ddf\u8e2a\u5f85\u56de\u6536\u3001\u5df2\u53cd\u9988\u3001\u6682\u505c\u548c\u6062\u590d\u4e2d\u7b56\u7565\u3002",
            )

        jc_feedback = dashboard.get("jc_bucket_feedback", {}) if isinstance(dashboard.get("jc_bucket_feedback"), dict) else {}
        self._strategy_section_title(left, "JC\u7a33\u5b9a\u6876\u5b9e\u76d8\u6392\u540d")
        jc_rows = jc_feedback.get("rows", []) if isinstance(jc_feedback.get("rows"), list) else []
        if jc_rows:
            for row in jc_rows:
                if isinstance(row, dict):
                    self._strategy_row(left, str(row.get("title") or "-"), str(row.get("body") or "-"))
        else:
            self._strategy_row(left, "\u6682\u65e0JC\u6876\u5b9e\u76d8\u7edf\u8ba1", "\u5f53\u7ade\u5f69\u7a33\u5b9a\u6876\u7b56\u7565\u5b8c\u6210\u8d5b\u679c\u56de\u6536\u540e\uff0c\u8fd9\u91cc\u4f1a\u663e\u793a\u5404\u6876\u7684\u5b9e\u76d8\u547d\u4e2d\u3001\u504f\u5dee\u548c\u964d\u7ea7\u72b6\u6001\u3002")

        self._strategy_section_title(left, "\u56de\u6d4b\u4e0e\u6837\u672c")
        for label, value in dashboard.get("validation_rows", []):
            self._strategy_row(left, str(label), str(value))

        self._strategy_section_title(right, "\u771f\u5b9e\u7ed3\u7b97\u53cd\u9988", first=True)
        settlement_rows = dashboard.get("settlement_rows", [])
        if settlement_rows:
            for row in settlement_rows:
                if isinstance(row, dict):
                    self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))
        else:
            self._strategy_row(right, "\u5c1a\u65e0\u547d\u4e2d\u53cd\u9988", "\u8fd1\u671f\u7ed3\u7b97\u4e2d\u8fd8\u6ca1\u6709\u8bb0\u5f55\u5230\u9ad8\u51c6\u7b56\u7565\u547d\u4e2d\u9879\u3002\u540e\u7eed\u8d5b\u679c\u56de\u6536\u540e\u4f1a\u5728\u8fd9\u91cc\u663e\u793a\u3002")

        error_attribution = dashboard.get("error_attribution", {}) if isinstance(dashboard.get("error_attribution"), dict) else {}
        self._strategy_section_title(right, "\u7b56\u7565\u9519\u56e0\u5f52\u7c7b")
        self._strategy_row(
            right,
            f"\u4e3b\u8981\u9519\u56e0: {error_attribution.get('top_reason', '-')}",
            f"\u9519\u56e0\u9879 {error_attribution.get('miss_count', 0)} | \u5f85\u5224\u5b9a {error_attribution.get('unknown_count', 0)}",
        )
        for row in error_attribution.get("rows", []) if isinstance(error_attribution.get("rows"), list) else []:
            if isinstance(row, dict):
                self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))

        historical_replay = dashboard.get("historical_strategy_replay", {}) if isinstance(dashboard.get("historical_strategy_replay"), dict) else {}
        historical_error_attribution = dashboard.get("historical_error_attribution", {}) if isinstance(dashboard.get("historical_error_attribution"), dict) else {}
        source_counts = historical_replay.get("source_counts", {}) if isinstance(historical_replay.get("source_counts"), dict) else {}
        source_text = " / ".join(f"{key}:{value}" for key, value in list(source_counts.items())[:3]) if source_counts else "-"
        self._strategy_section_title(right, "\u5386\u53f2\u7b56\u7565\u56de\u653e\u9519\u56e0")
        if int(historical_replay.get("sample_count") or 0):
            self._strategy_row(
                right,
                f"\u56de\u653e\u6837\u672c: {historical_replay.get('sample_count', 0)} | \u547d\u4e2d {historical_replay.get('hit_rate_text', '-')}",
                (
                    f"\u9519\u56e0\u9879 {historical_error_attribution.get('miss_count', 0)} | "
                    f"\u4e3b\u56e0 {historical_error_attribution.get('top_reason', '-')} | "
                    f"\u6765\u6e90 {source_text}"
                ),
            )
            for row in historical_error_attribution.get("rows", []) if isinstance(historical_error_attribution.get("rows"), list) else []:
                if isinstance(row, dict):
                    self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))
        else:
            self._strategy_row(
                right,
                "\u6682\u65e0\u5386\u53f2\u56de\u653e\u6837\u672c",
                "\u9700\u5148\u751f\u6210\u7b56\u7565\u6c60\uff0c\u5e76\u786e\u4fdd\u5386\u53f2\u5e02\u573a\u6837\u672c\u80fd\u547d\u4e2d\u5f53\u524d\u7b56\u7565\u95e8\u69db\u3002",
            )

        agent_trace_replay = dashboard.get("agent_trace_replay", {}) if isinstance(dashboard.get("agent_trace_replay"), dict) else {}
        self._strategy_section_title(right, "Agent Replay 复盘")
        self._strategy_row(
            right,
            f"最高关联: {agent_trace_replay.get('top_agent', '-')} | {agent_trace_replay.get('summary_text', '-')}",
            f"主要动作: {agent_trace_replay.get('top_action', '-')}",
        )
        for row in agent_trace_replay.get("rows", []) if isinstance(agent_trace_replay.get("rows"), list) else []:
            if isinstance(row, dict):
                self._strategy_row(
                    right,
                    f"{row.get('agent', '-')} | 触发 {row.get('trigger_count', 0)} | alert {row.get('alert_count', 0)} / watch {row.get('watch_count', 0)}",
                    (
                        f"胜平负失误 {row.get('prediction_miss_rate_text', '-')} | "
                        f"让球失误 {row.get('handicap_miss_rate_text', '-')} | "
                        f"主要动作 {row.get('top_action', '-')}"
                    ),
                )

        replay_downgrade = dashboard.get("agent_replay_downgrade", {}) if isinstance(dashboard.get("agent_replay_downgrade"), dict) else {}
        self._strategy_section_title(right, "Agent Replay 降级回测")
        self._strategy_row(
            right,
            f"{replay_downgrade.get('recommendation', '-')}: {replay_downgrade.get('summary_text', '-')}",
            str(replay_downgrade.get("recommendation_text") or "-"),
        )
        for row in replay_downgrade.get("rows", []) if isinstance(replay_downgrade.get("rows"), list) else []:
            if isinstance(row, dict):
                self._strategy_row(
                    right,
                    f"{row.get('agent', '-')} | 样本 {row.get('count', 0)} | 净值 {row.get('prediction_net', 0)}/{row.get('handicap_net', 0)}",
                    (
                        f"1X2避错 {row.get('prediction_avoided_misses', 0)} / 成本 {row.get('prediction_opportunity_cost', 0)} | "
                        f"让球避错 {row.get('handicap_avoided_misses', 0)} / 成本 {row.get('handicap_opportunity_cost', 0)} | "
                        f"主要动作 {row.get('top_action', '-')}"
                    ),
                )

        replay_tuning = dashboard.get("agent_replay_guard_tuning", {}) if isinstance(dashboard.get("agent_replay_guard_tuning"), dict) else {}
        self._strategy_section_title(right, "Replay Guard \u8c03\u53c2\u5efa\u8bae")
        tuning_rows = replay_tuning.get("rows", []) if isinstance(replay_tuning.get("rows"), list) else []
        tuning_body = "\n".join(f"{label}: {value}" for label, value in tuning_rows if isinstance(label, str)) if tuning_rows else "-"
        tuning_net = replay_tuning.get("net", 0)
        self._strategy_row(
            right,
            f"{replay_tuning.get('label', '-')} | \u51c0\u503c {int(tuning_net):+d}" if isinstance(tuning_net, int) else str(replay_tuning.get("label", "-")),
            tuning_body,
        )

        policy_effect = dashboard.get("policy_effect_review", {}) if isinstance(dashboard.get("policy_effect_review"), dict) else {}
        self._strategy_section_title(right, "\u53c2\u6570\u751f\u6548\u590d\u76d8")
        self._strategy_row(
            right,
            str(policy_effect.get("latest_label") or "-"),
            f"{policy_effect.get('summary_text', '-')}\n\u70b9\u51fb\u67e5\u770b\u7248\u672c\u4e0e\u8d5b\u4e8b\u660e\u7ec6",
            command=lambda review=policy_effect: self.open_policy_effect_detail_window(review),
        )
        for row in policy_effect.get("rows", []) if isinstance(policy_effect.get("rows"), list) else []:
            if isinstance(row, dict):
                self._strategy_row(
                    right,
                    str(row.get("title") or "-"),
                    f"{row.get('body', '-')}\n\u70b9\u51fb\u67e5\u770b\u8be5\u7248\u672c\u6837\u672c",
                    command=lambda review=policy_effect: self.open_policy_effect_detail_window(review),
                )

        policy_governance = dashboard.get("policy_governance_event_summary", {}) if isinstance(dashboard.get("policy_governance_event_summary"), dict) else {}
        governance_rows = policy_governance.get("rows", []) if isinstance(policy_governance.get("rows"), list) else []
        governance_command = lambda review=policy_effect, dg_history=draw_guard_history, dg_tuning=dashboard.get("draw_release_guard_tuning_effect", {}), dg_rollback=dashboard.get("draw_release_guard_rollback_effect", {}), dg_freeze=dashboard.get("draw_release_guard_freeze_override", {}), dg_guard=dashboard.get("draw_release_guard_tuning_guard", {}): self.open_policy_governance_event_window(
            review,
            draw_release_guard_policy_history=dg_history,
            draw_release_guard_tuning_effect_review=dg_tuning,
            draw_release_guard_rollback_effect_review=dg_rollback,
            draw_release_guard_freeze_override_status=dg_freeze,
            draw_release_guard_tuning_guard=dg_guard,
        )
        self._strategy_section_title(right, "\u7b56\u7565\u6cbb\u7406\u4e8b\u4ef6")
        self._strategy_row(
            right,
            str(policy_governance.get("summary_text") or "-"),
            f"{policy_governance.get('latest_summary', '-')}\n\u70b9\u51fb\u67e5\u770b\u6cbb\u7406\u4e8b\u4ef6\u660e\u7ec6",
            command=governance_command,
        )
        if governance_rows:
            for row in governance_rows[:5]:
                if isinstance(row, dict):
                    try:
                        replay_net = int(row.get("replay_guard_net", 0) or 0)
                    except (TypeError, ValueError):
                        replay_net = 0
                    self._strategy_row(
                        right,
                        f"{row.get('event_label', '-')} | \u7248\u672c {row.get('version_id', '-')}",
                        (
                            f"\u6765\u6e90: {row.get('source', '-')} | \u5173\u8054 {row.get('related_version_id', '-')}\n"
                            f"\u6548\u679c: {row.get('effect_label', '-')} | \u653e\u884c\u547d\u4e2d {row.get('allow_hit_rate_text', '-')} | "
                            f"Replay\u51c0\u503c {replay_net:+d}\n"
                            f"\u8bf4\u660e: {row.get('description', '-')}"
                        ),
                        command=governance_command,
                    )
        else:
            self._strategy_row(
                right,
                "\u6682\u65e0\u6cbb\u7406\u4e8b\u4ef6",
                "\u8d8b\u52bf\u95e8\u63a7\u3001\u53c2\u6570\u56de\u6eda\u548c\u89e3\u9664\u51bb\u7ed3\u5ba1\u8ba1\u4f1a\u5728\u8fd9\u91cc\u663e\u793a\u3002",
            )

        trend_tuning_effect = dashboard.get("trend_tuning_effect_review", {}) if isinstance(dashboard.get("trend_tuning_effect_review"), dict) else {}
        self._strategy_section_title(right, "\u95e8\u63a7\u5efa\u8bae\u751f\u6548\u8ddf\u8e2a")
        self._strategy_row(
            right,
            str(trend_tuning_effect.get("label") or "-"),
            (
                f"{trend_tuning_effect.get('summary_text', '-')}\n"
                f"{trend_tuning_effect.get('recommendation_text', '-')}"
            ),
            command=lambda review=policy_effect: self.open_policy_effect_detail_window(review),
        )
        for row in trend_tuning_effect.get("rows", []) if isinstance(trend_tuning_effect.get("rows"), list) else []:
            if isinstance(row, dict):
                self._strategy_row(
                    right,
                    str(row.get("title") or "-"),
                    str(row.get("body") or "-"),
                    command=lambda review=policy_effect: self.open_policy_effect_detail_window(review),
                )

        rollback_effect = dashboard.get("rollback_effect_review", {}) if isinstance(dashboard.get("rollback_effect_review"), dict) else {}
        self._strategy_section_title(right, "\u56de\u6eda\u4fee\u590d\u6548\u679c\u8ddf\u8e2a")
        self._strategy_row(
            right,
            str(rollback_effect.get("label") or "-"),
            (
                f"{rollback_effect.get('summary_text', '-')}\n"
                f"{rollback_effect.get('recommendation_text', '-')}"
            ),
            command=lambda review=policy_effect: self.open_policy_effect_detail_window(review),
        )
        for row in rollback_effect.get("rows", []) if isinstance(rollback_effect.get("rows"), list) else []:
            if isinstance(row, dict):
                self._strategy_row(
                    right,
                    str(row.get("title") or "-"),
                    str(row.get("body") or "-"),
                    command=lambda review=policy_effect: self.open_policy_effect_detail_window(review),
                )
        freeze_override = dashboard.get("freeze_override_status", {}) if isinstance(dashboard.get("freeze_override_status"), dict) else {}
        if str(freeze_override.get("status") or "") in {"frozen", "overridden"}:
            self._strategy_row(
                right,
                str(freeze_override.get("label") or "-"),
                str(freeze_override.get("summary_text") or "-"),
                command=lambda rollback=rollback_effect, override=freeze_override: self.apply_strategy_policy_freeze_override(rollback, override),
            )

        stability_monitor = dashboard.get("policy_stability_monitor", {}) if isinstance(dashboard.get("policy_stability_monitor"), dict) else {}
        self._strategy_section_title(right, "\u7248\u672c\u7a33\u5b9a\u76d1\u63a7")
        self._strategy_row(
            right,
            str(stability_monitor.get("summary_text") or "-"),
            str(stability_monitor.get("recommendation_text") or "-"),
            command=lambda review=policy_effect: self.open_policy_effect_detail_window(review),
        )
        for row in stability_monitor.get("weekly_rows", []) if isinstance(stability_monitor.get("weekly_rows"), list) else []:
            if isinstance(row, dict):
                self._strategy_row(
                    right,
                    str(row.get("title") or "-"),
                    str(row.get("body") or "-"),
                    command=lambda review=policy_effect: self.open_policy_effect_detail_window(review),
                )
        tuning_guard = dashboard.get("policy_tuning_guard", {}) if isinstance(dashboard.get("policy_tuning_guard"), dict) else {}
        self._strategy_section_title(right, "\u8c03\u53c2\u95e8\u63a7")
        self._strategy_row(
            right,
            str(tuning_guard.get("summary_text") or "-"),
            str(tuning_guard.get("body") or "-"),
            command=lambda review=policy_effect: self.open_policy_effect_detail_window(review),
        )

        entropy_backtest = dashboard.get("market_entropy_backtest", {}) if isinstance(dashboard.get("market_entropy_backtest"), dict) else {}
        self._strategy_section_title(right, "MarketEntropy 避险回测")
        self._strategy_row(
            right,
            f"{entropy_backtest.get('recommendation', '-')}: {entropy_backtest.get('summary_text', '-')}",
            str(entropy_backtest.get("recommendation_text") or "-"),
        )
        for row in entropy_backtest.get("rows", []) if isinstance(entropy_backtest.get("rows"), list) else []:
            if isinstance(row, dict):
                self._strategy_row(
                    right,
                    f"{row.get('label', '-')} | 样本 {row.get('count', 0)} | 命中 {row.get('hit_rate_text', '-')}",
                    (
                        f"失误率 {row.get('miss_rate_text', '-')} | 平均熵值 {row.get('avg_score_text', '-')} | "
                        f"风险覆盖 {row.get('risk_applied_count', 0)} | 主要信号 {row.get('top_signal', '-')}"
                    ),
                )

        handicap_margin_backtest = dashboard.get("handicap_margin_backtest", {}) if isinstance(dashboard.get("handicap_margin_backtest"), dict) else {}
        self._strategy_section_title(right, "Handicap Margin 回测")
        self._strategy_row(
            right,
            f"{handicap_margin_backtest.get('recommendation', '-')}: {handicap_margin_backtest.get('summary_text', '-')}",
            str(handicap_margin_backtest.get("recommendation_text") or "-"),
        )
        for row in handicap_margin_backtest.get("rows", []) if isinstance(handicap_margin_backtest.get("rows"), list) else []:
            if isinstance(row, dict):
                self._strategy_row(
                    right,
                    f"{row.get('label', '-')} | 样本 {row.get('count', 0)} | 让球命中 {row.get('hit_rate_text', '-')}",
                    (
                        f"让球失误率 {row.get('miss_rate_text', '-')} | 平均分 {row.get('avg_score_text', '-')} | "
                        f"主要信号 {row.get('top_signal', '-')}"
                    ),
                )

        draw_guard_review = dashboard.get("draw_release_guard_review", {}) if isinstance(dashboard.get("draw_release_guard_review"), dict) else {}
        self._strategy_section_title(right, "\u5e73\u5c40\u62e6\u622a\u6548\u679c\u590d\u76d8")
        self._strategy_row(
            right,
            f"{draw_guard_review.get('recommendation', '-')}: {draw_guard_review.get('summary_text', '-')}",
            str(draw_guard_review.get("recommendation_text") or "-"),
        )
        for row in draw_guard_review.get("rows", []) if isinstance(draw_guard_review.get("rows"), list) else []:
            if isinstance(row, dict):
                self._strategy_row(
                    right,
                    f"{row.get('label', '-')} | \u6837\u672c {row.get('count', 0)} | \u62e6\u622a {row.get('blocked_count', 0)}",
                    (
                        f"\u907f\u514d\u5047\u9633 {row.get('avoid_count', 0)} ({row.get('avoid_rate_text', '-')}) | "
                        f"\u9519\u8fc7\u771f\u5e73 {row.get('missed_count', 0)} ({row.get('missed_rate_text', '-')}) | "
                        f"\u5e73\u5c40\u5206 {row.get('avg_draw_score_text', '-')} | \u4e3b\u56e0 {row.get('top_reason', '-')}"
                    ),
                )

        draw_guard_tuning = dashboard.get("draw_release_guard_tuning", {}) if isinstance(dashboard.get("draw_release_guard_tuning"), dict) else {}
        tuning_rows = draw_guard_tuning.get("rows", []) if isinstance(draw_guard_tuning.get("rows"), list) else []
        if tuning_rows:
            tuning_body = "\n".join(f"{label}: {value}" for label, value in tuning_rows if isinstance(label, str))
            self._strategy_row(
                right,
                f"\u5e73\u5c40\u62e6\u622a\u8c03\u53c2: {draw_guard_tuning.get('label', '-')}",
                tuning_body,
                command=lambda tuning=draw_guard_tuning: self.apply_draw_release_guard_tuning(tuning),
            )

        draw_guard_effect = dashboard.get("draw_release_guard_tuning_effect", {}) if isinstance(dashboard.get("draw_release_guard_tuning_effect"), dict) else {}
        self._strategy_row(
            right,
            f"DrawGuard\u751f\u6548\u8ffd\u8e2a: {draw_guard_effect.get('label', '-')}",
            (
                f"{draw_guard_effect.get('summary_text', '-')}\n"
                f"{draw_guard_effect.get('recommendation_text', '-')}"
                + ("\n\u5efa\u8bae\uff1a\u56de\u6eda DrawGuard \u4e0a\u4e00\u7248\u53c2\u6570\u3002" if bool(draw_guard_effect.get("rollback_recommended")) else "")
            ),
            command=self.rollback_latest_draw_guard_policy if bool(draw_guard_effect.get("rollback_recommended")) else None,
        )
        for row in draw_guard_effect.get("rows", []) if isinstance(draw_guard_effect.get("rows"), list) else []:
            if isinstance(row, dict):
                self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))

        draw_guard_rollback = dashboard.get("draw_release_guard_rollback_effect", {}) if isinstance(dashboard.get("draw_release_guard_rollback_effect"), dict) else {}
        self._strategy_row(
            right,
            f"DrawGuard\u56de\u6eda\u4fee\u590d: {draw_guard_rollback.get('label', '-')}",
            (
                f"{draw_guard_rollback.get('summary_text', '-')}\n"
                f"{draw_guard_rollback.get('recommendation_text', '-')}"
            ),
        )
        for row in draw_guard_rollback.get("rows", []) if isinstance(draw_guard_rollback.get("rows"), list) else []:
            if isinstance(row, dict):
                self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))

        draw_guard_freeze = dashboard.get("draw_release_guard_freeze_override", {}) if isinstance(dashboard.get("draw_release_guard_freeze_override"), dict) else {}
        draw_guard_tuning_guard = dashboard.get("draw_release_guard_tuning_guard", {}) if isinstance(dashboard.get("draw_release_guard_tuning_guard"), dict) else {}
        self._strategy_row(
            right,
            f"DrawGuard\u8c03\u53c2\u95e8\u63a7: {draw_guard_tuning_guard.get('label', '-')}",
            str(draw_guard_tuning_guard.get("body") or "-"),
            command=(
                (lambda rollback=draw_guard_rollback, override=draw_guard_freeze: self.apply_draw_release_guard_freeze_override(rollback, override))
                if str(draw_guard_freeze.get("status") or "") == "frozen"
                else None
            ),
        )
        if str(draw_guard_freeze.get("status") or "") in {"frozen", "overridden"}:
            self._strategy_row(
                right,
                str(draw_guard_freeze.get("label") or "-"),
                str(draw_guard_freeze.get("summary_text") or "-"),
                command=lambda rollback=draw_guard_rollback, override=draw_guard_freeze: self.apply_draw_release_guard_freeze_override(rollback, override),
            )

        statsbomb_review = dashboard.get("statsbomb_event_review", {}) if isinstance(dashboard.get("statsbomb_event_review"), dict) else {}
        self._strategy_section_title(right, "StatsBomb \u8d5b\u540e\u4e8b\u4ef6")
        self._strategy_row(
            right,
            str(statsbomb_review.get("summary_text") or "-"),
            (
                f"\u57fa\u7ebf {statsbomb_review.get('baseline_match_count', 0)} \u573a | "
                f"xG\u5bf9\u9f50 {statsbomb_review.get('xg_alignment_rate_text', '-')} / \u57fa\u7ebf {statsbomb_review.get('baseline_xg_alignment_rate', '-')} | "
                f"\u7ec8\u7ed3\u6ce2\u52a8 {statsbomb_review.get('finishing_variance_rate_text', '-')} / \u57fa\u7ebf {statsbomb_review.get('baseline_finishing_variance_rate', '-')}\n"
                f"{statsbomb_review.get('leakage_note', '-')}"
            ),
        )
        for row in statsbomb_review.get("rows", []) if isinstance(statsbomb_review.get("rows"), list) else []:
            if isinstance(row, dict):
                self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))

        evaluation_agent = dashboard.get("evaluation_agent", {}) if isinstance(dashboard.get("evaluation_agent"), dict) else {}
        self._strategy_section_title(right, "Evaluation Agent")
        self._strategy_row(
            right,
            f"{evaluation_agent.get('status', '-')} / score {evaluation_agent.get('score', '-')}",
            str(evaluation_agent.get("summary_text") or "-"),
        )
        statsbomb_review_quality = dashboard.get("statsbomb_review_training_quality", {}) if isinstance(dashboard.get("statsbomb_review_training_quality"), dict) else {}
        self._strategy_section_title(right, "StatsBomb 事件代理样本质量")
        for row in statsbomb_review_quality.get("card_rows", []) if isinstance(statsbomb_review_quality.get("card_rows"), list) else []:
            if isinstance(row, dict):
                self._strategy_row(
                    right,
                    f"{row.get('label', '-')}: {row.get('value', '-')}",
                    str(row.get("detail") or "-"),
                )
        label_rows = statsbomb_review_quality.get("label_rows", []) if isinstance(statsbomb_review_quality.get("label_rows"), list) else []
        if label_rows:
            self._strategy_row(
                right,
                "标签分布",
                "\n".join(
                    f"{row.get('label', '-')}: {row.get('detail', '-')}"
                    for row in label_rows[:3]
                    if isinstance(row, dict)
                ),
            )
        weight_rows = statsbomb_review_quality.get("weight_rows", []) if isinstance(statsbomb_review_quality.get("weight_rows"), list) else []
        if weight_rows:
            self._strategy_row(
                right,
                "事件错因权重",
                "\n".join(
                    f"{row.get('label', '-')}: {row.get('value', '-')}"
                    for row in weight_rows[:3]
                    if isinstance(row, dict)
                ),
            )
        quality_issues = statsbomb_review_quality.get("issues", []) if isinstance(statsbomb_review_quality.get("issues"), list) else []
        if quality_issues:
            self._strategy_row(
                right,
                "质量修复建议",
                "\n".join(
                    str(item.get("recommendation") or item.get("message") or "-")
                    for item in quality_issues[:4]
                    if isinstance(item, dict)
                ),
            )
        for item in evaluation_agent.get("recommendations", []) if isinstance(evaluation_agent.get("recommendations"), list) else []:
            if isinstance(item, dict):
                self._strategy_row(right, str(item.get("title") or "-"), str(item.get("body") or "-"))
        video_fewshot_memory = evaluation_agent.get("video_review_fewshot_memory", {}) if isinstance(evaluation_agent.get("video_review_fewshot_memory"), dict) else {}
        video_memory_rows = video_fewshot_memory.get("rows", []) if isinstance(video_fewshot_memory.get("rows"), list) else []
        if video_memory_rows:
            self._strategy_section_title(right, "AI Video Few-shot \u8bb0\u5fc6")
            self._strategy_row(
                right,
                str(video_fewshot_memory.get("summary_text") or "-"),
                str(video_fewshot_memory.get("leakage_note") or "-"),
            )
            for row in video_memory_rows:
                if isinstance(row, dict):
                    self._strategy_row(right, str(row.get("title") or "-"), f"{row.get('body', '-')}\n{row.get('completion', '-')}")
        video_memory_health = self._video_review_fewshot_memory_health_context(video_fewshot_memory)
        self._strategy_section_title(right, "AI Video 记忆健康")
        for row in video_memory_health.get("card_rows", []) if isinstance(video_memory_health.get("card_rows"), list) else []:
            if isinstance(row, dict):
                self._strategy_row(
                    right,
                    f"{row.get('label', '-')}: {row.get('value', '-')}",
                    str(row.get("detail") or "-"),
                )
        self._strategy_section_title(right, "AI Video 补标注/补样建议")
        self._strategy_row(
            right,
            str(video_memory_health.get("health", {}).get("summary_text") or "-"),
            self._video_review_fewshot_action_text(video_memory_health.get("action_rows")),
        )
        workflow_rows = build_video_review_workflow_action_rows(
            lambda: self.import_video_review_for_selection(review_tree, settlements),
            lambda: self.annotate_video_review_for_selection(review_tree, settlements),
            self.export_video_review_fewshot_samples,
            self.preview_video_review_fewshot_merge_bundle,
            self.apply_video_review_fewshot_merge_bundle,
        )
        self._strategy_section_title(right, "AI Video 建议动作入口")
        for row in workflow_rows:
            if isinstance(row, dict):
                self._strategy_row(
                    right,
                    str(row.get("title") or "-"),
                    str(row.get("body") or "-"),
                    command=row.get("command"),
                )
        fewshot_memory = evaluation_agent.get("statsbomb_fewshot_memory", {}) if isinstance(evaluation_agent.get("statsbomb_fewshot_memory"), dict) else {}
        memory_rows = fewshot_memory.get("rows", []) if isinstance(fewshot_memory.get("rows"), list) else []
        if memory_rows:
            self._strategy_section_title(right, "StatsBomb Few-shot \u8bb0\u5fc6")
            self._strategy_row(
                right,
                str(fewshot_memory.get("summary_text") or "-"),
                str(fewshot_memory.get("leakage_note") or "-"),
            )
            for row in memory_rows:
                if isinstance(row, dict):
                    self._strategy_row(right, str(row.get("title") or "-"), f"{row.get('body', '-')}\n{row.get('completion', '-')}")
        fewshot_monitor = dashboard.get("statsbomb_fewshot_monitor", {}) if isinstance(dashboard.get("statsbomb_fewshot_monitor"), dict) else {}
        try:
            fewshot_monitor_sample_count = int(fewshot_monitor.get("sample_count") or 0)
        except (TypeError, ValueError):
            fewshot_monitor_sample_count = 0
        if fewshot_monitor_sample_count:
            self._strategy_section_title(right, "StatsBomb \u8bb0\u5fc6\u76d1\u63a7")
            self._strategy_row(
                right,
                str(fewshot_monitor.get("summary_text") or "-"),
                (
                    f"\u547d\u4e2d/\u672a\u547d\u4e2d: {fewshot_monitor.get('hit_count', 0)} / {fewshot_monitor.get('miss_count', 0)}\n"
                    f"\u5f53\u524d\u67e5\u8be2\u6807\u7b7e: {', '.join(fewshot_monitor.get('current_query_tags', [])) if isinstance(fewshot_monitor.get('current_query_tags'), list) else '-'}\n"
                    f"\u7f3a\u53e3\u6807\u7b7e: {', '.join(fewshot_monitor.get('missing_tags', [])) if isinstance(fewshot_monitor.get('missing_tags'), list) else '-'}"
                ),
            )
            for row in fewshot_monitor.get("tag_rows", []) if isinstance(fewshot_monitor.get("tag_rows"), list) else []:
                if isinstance(row, dict):
                    self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))
        fewshot_health = dashboard.get("statsbomb_fewshot_health", {}) if isinstance(dashboard.get("statsbomb_fewshot_health"), dict) else {}
        health_issues = fewshot_health.get("issues", []) if isinstance(fewshot_health.get("issues"), list) else []
        if health_issues:
            self._strategy_section_title(right, "StatsBomb \u8bb0\u5fc6\u5065\u5eb7")
            self._strategy_row(
                right,
                str(fewshot_health.get("summary_text") or "-"),
                "\n".join(str(item.get("recommendation") or item.get("title") or "-") for item in health_issues if isinstance(item, dict)),
            )
        health_drivers = dashboard.get("statsbomb_fewshot_health_drivers", {}) if isinstance(dashboard.get("statsbomb_fewshot_health_drivers"), dict) else {}
        driver_rows = health_drivers.get("rows", []) if isinstance(health_drivers.get("rows"), list) else []
        if driver_rows:
            self._strategy_section_title(right, "StatsBomb \u5065\u5eb7\u9a71\u52a8")
            self._strategy_row(
                right,
                str(health_drivers.get("summary_text") or "-"),
                "\u7528\u4e8e\u5224\u65ad\u5f53\u524d few-shot \u8bb0\u5fc6\u7f3a\u53e3\u3001\u8865\u6837\u5019\u9009\u548c\u6700\u8fd1\u5e94\u7528\u662f\u5426\u95ed\u73af\u3002",
            )
            for row in driver_rows[:6]:
                if isinstance(row, dict):
                    self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))
        self._strategy_statsbomb_workflow_panel(right, dashboard)
        fewshot_quality = evaluation_agent.get("statsbomb_fewshot_quality", {}) if isinstance(evaluation_agent.get("statsbomb_fewshot_quality"), dict) else {}
        quality_alerts = fewshot_quality.get("alerts", []) if isinstance(fewshot_quality.get("alerts"), list) else []
        if quality_alerts:
            self._strategy_section_title(right, "StatsBomb \u8bb0\u5fc6\u8d28\u91cf\u544a\u8b66")
            self._strategy_row(
                right,
                str(fewshot_quality.get("summary_text") or "-"),
                str(fewshot_monitor.get("leakage_note") or fewshot_quality.get("leakage_note") or "-"),
            )
            for row in quality_alerts:
                if isinstance(row, dict):
                    self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))
        backfill_queue = dashboard.get("statsbomb_backfill_queue", {}) if isinstance(dashboard.get("statsbomb_backfill_queue"), dict) else {}
        backfill_tasks = backfill_queue.get("tasks", []) if isinstance(backfill_queue.get("tasks"), list) else []
        backfill_candidates = backfill_queue.get("candidate_rows", []) if isinstance(backfill_queue.get("candidate_rows"), list) else []
        if backfill_tasks:
            self._strategy_section_title(right, "StatsBomb \u8865\u6837\u961f\u5217")
            self._strategy_row(
                right,
                str(backfill_queue.get("summary_text") or "-"),
                str(backfill_queue.get("leakage_note") or "-"),
            )
            for row in backfill_tasks[:4]:
                if isinstance(row, dict):
                    self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))
            for row in backfill_candidates[:4]:
                if isinstance(row, dict):
                    self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))

        allowlist_summary = dashboard.get("allowlist_settlement_summary", {}) if isinstance(dashboard.get("allowlist_settlement_summary"), dict) else {}
        self._strategy_section_title(right, "\u653e\u884c\u590d\u76d8\u7edf\u8ba1")
        self._strategy_row(
            right,
            f"\u653e\u884c\u547d\u4e2d: {allowlist_summary.get('hit_rate_text', '-')} | \u6837\u672c {allowlist_summary.get('known_count', 0)}",
            (
                f"\u9ad8\u51c6\u547d\u4e2d: {allowlist_summary.get('high_strategy_summary', '-')} | "
                f"\u8ba9\u7403 {allowlist_summary.get('handicap_hit_rate_text', '-')} | "
                f"\u5927\u5c0f {allowlist_summary.get('ou_hit_rate_text', '-')} | "
                f"\u4e3b\u8981\u504f\u5dee: {allowlist_summary.get('top_failure', '-')}"
            ),
        )
        self._strategy_row(
            right,
            f"\u653e\u884c\u56de\u6536\u95ed\u73af: {release_loop.get('health_text', '-')}",
            (
                f"{release_loop.get('summary_text', '-')}\n"
                f"\u5df2\u5bfc\u51fa {release_loop.get('exported_count', 0)} | "
                f"\u5df2\u7559\u5feb\u7167 {release_loop.get('snapshot_saved_count', 0)} | "
                f"\u53ef\u56de\u6536 {release_loop.get('ready_for_recovery_count', 0)}"
            ),
        )
        allowlist_tuning = dashboard.get("allowlist_tuning", {}) if isinstance(dashboard.get("allowlist_tuning"), dict) else {}
        tuning_rows = allowlist_tuning.get("rows", []) if isinstance(allowlist_tuning.get("rows"), list) else []
        if tuning_rows:
            tuning_body = "\n".join(f"{label}: {value}" for label, value in tuning_rows if isinstance(label, str))
            self._strategy_row(right, f"\u653e\u884c\u95e8\u69db\u5efa\u8bae: {allowlist_tuning.get('label', '-')}", tuning_body)
        allowlist_settlement_rows = dashboard.get("allowlist_settlement_rows", [])
        if allowlist_settlement_rows:
            for row in allowlist_settlement_rows:
                if isinstance(row, dict):
                    self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))

        self._strategy_section_title(right, "\u6b63\u5f0f\u653e\u884c\u5f85\u590d\u76d8\u6c60")
        if release_pool_rows:
            for title, body_text in release_pool_rows:
                self._strategy_row(right, title, body_text)
        else:
            self._strategy_row(
                right,
                "\u6682\u65e0\u6b63\u5f0f\u653e\u884c\u573a\u6b21",
                "\u5237\u65b0\u5e76\u5206\u6790\u8d5b\u4e8b\u540e\uff0c\u7b56\u7565\u51c6\u5165\u4e3a\u6b63\u5f0f\u653e\u884c\u7684\u573a\u6b21\u4f1a\u5728\u8fd9\u91cc\u5f62\u6210\u5f85\u590d\u76d8\u6c60\u3002",
            )

        self._strategy_section_title(right, "\u4f7f\u7528\u5efa\u8bae")
        for row in dashboard.get("guidance_rows", []):
            if isinstance(row, dict):
                self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))

        self._strategy_section_title(right, "当前准入清单")
        admission_rows = self._strategy_admission_rows()
        if admission_rows:
            for title, body_text in admission_rows:
                self._strategy_row(right, title, body_text)
        else:
            self._strategy_row(right, "暂无准入结果", "加载并分析赛事后，这里会显示正式放行、观察和阻断清单。")
        self._bind_canvas_mousewheel(content, canvas)

    def open_strategy_release_recovery_loop_window(self) -> None:
        settlements = list(reversed(get_recent_settlements(limit=300)))
        loop = self._strategy_release_recovery_loop(settlements)
        window = tk.Toplevel(self.root)
        window.title("\u653e\u884c\u56de\u6536\u95ed\u73af")
        window.geometry("1040x620")
        window.minsize(940, 520)
        window.configure(bg=BG)
        window.transient(self.root)

        container = tk.Frame(window, bg=BG)
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        header = tk.Frame(container, bg=BG)
        header.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            header,
            text="\u653e\u884c\u56de\u6536\u95ed\u73af",
            bg=BG,
            fg=TEXT,
            font=("Microsoft YaHei UI", 15, "bold"),
        ).pack(side=tk.LEFT)
        recover_button = tk.Button(
            header,
            text="\u7acb\u5373\u56de\u6536\u8d5b\u679c",
            command=self.run_result_recovery,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=7,
        )
        self._register_result_recovery_button(recover_button)
        recover_button.pack(side=tk.RIGHT)
        tk.Button(
            header,
            text="\u5bfc\u51fa\u62a5\u544a",
            command=self.export_strategy_release_recovery_loop_report,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        tk.Button(
            header,
            text="\u5237\u65b0",
            command=lambda: (window.destroy(), self.open_strategy_release_recovery_loop_window()),
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))

        metric_bar = tk.Frame(container, bg=BG)
        metric_bar.pack(fill=tk.X, pady=(0, 12))
        for label, value, color in [
            ("\u72b6\u6001", str(loop.get("health_text") or "-"), self._tone_color(str(loop.get("health") or "neutral"))),
            ("\u653e\u884c", str(loop.get("total_release_count", 0)), TEXT),
            ("\u5df2\u56de\u6536", str(loop.get("settled_count", 0)), GREEN),
            ("\u5f85\u56de\u6536", str(loop.get("pending_count", 0)), YELLOW if int(loop.get("pending_count", 0) or 0) else GREEN),
            ("\u7f3a\u5feb\u7167", str(loop.get("missing_snapshot_count", 0)), RED if int(loop.get("missing_snapshot_count", 0) or 0) else GREEN),
            ("\u8d85\u671f", str(loop.get("stale_pending_count", 0)), RED if int(loop.get("stale_pending_count", 0) or 0) else GREEN),
            ("\u547d\u4e2d", str(loop.get("hit_rate_text") or "-"), GREEN if float(loop.get("hit_rate") or 0) >= 0.6 else YELLOW),
        ]:
            self._detail_metric(metric_bar, label, str(value), color)

        tk.Label(
            container,
            text=str(loop.get("summary_text") or "-"),
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor=tk.W, pady=(0, 10))

        table_wrap = tk.Frame(container, bg=BG)
        table_wrap.pack(fill=tk.BOTH, expand=True)
        self._configure_dark_tree_style("ReleaseLoop.Treeview", master=window, rowheight=28)
        columns = ("status", "date", "league", "match", "pick", "confidence", "risk", "snapshot", "settlement", "days", "file")
        tree = ttk.Treeview(table_wrap, columns=columns, show="headings", style="ReleaseLoop.Treeview", height=15)
        headings = {
            "status": "\u95ed\u73af\u72b6\u6001",
            "date": "\u5f00\u8d5b",
            "league": "\u8054\u8d5b",
            "match": "\u8d5b\u4e8b",
            "pick": "\u63a8\u8350",
            "confidence": "\u7f6e\u4fe1",
            "risk": "\u98ce\u9669",
            "snapshot": "\u5feb\u7167",
            "settlement": "\u56de\u6536",
            "days": "\u5f85\u56de\u6536",
            "file": "\u6e05\u5355",
        }
        widths = {
            "status": 104,
            "date": 116,
            "league": 92,
            "match": 190,
            "pick": 72,
            "confidence": 64,
            "risk": 72,
            "snapshot": 72,
            "settlement": 72,
            "days": 70,
            "file": 155,
        }
        for key in columns:
            tree.heading(key, text=headings[key], anchor=tk.W)
            tree.column(key, width=widths[key], minwidth=54, anchor=tk.W, stretch=key in {"match", "file"})
        scrollbar = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        rows = loop.get("rows", []) if isinstance(loop.get("rows"), list) else []
        for index, item in enumerate(rows):
            if not isinstance(item, dict):
                continue
            match = item.get("match", {}) if isinstance(item.get("match"), dict) else {}
            match_text = f"{match.get('home_team', '-')} vs {match.get('away_team', '-')}"
            tree.insert(
                "",
                tk.END,
                iid=str(index),
                values=(
                    item.get("loop_status", "-"),
                    item.get("kickoff", "-"),
                    match.get("league", "-"),
                    match_text,
                    item.get("recommendation", "-"),
                    item.get("confidence_text", "-"),
                    item.get("risk_text", "-"),
                    item.get("snapshot_status", "-"),
                    item.get("settlement_status", "-"),
                    f"{item.get('pending_days', 0)}\u5929" if item.get("pending") else "-",
                    item.get("allowlist_file", "-"),
                ),
            )

        if not rows:
            tree.insert("", tk.END, values=("\u6682\u65e0\u653e\u884c\u8bb0\u5f55", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-"))

        footer = tk.Frame(container, bg=BG)
        footer.pack(fill=tk.X, pady=(12, 0))
        tk.Label(
            footer,
            text="\u7f3a\u5feb\u7167\u8868\u793a\u8be5\u653e\u884c\u573a\u6b21\u6ca1\u6709\u53ef\u7528\u7684\u8d5b\u524d\u5feb\u7167\uff1b\u8d85\u671f\u8868\u793a\u5df2\u8fc7\u5f00\u8d5b\u65e5\u4f46\u5c1a\u672a\u56de\u6536\u8d5b\u679c\u3002",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
        ).pack(side=tk.LEFT)
        tk.Button(
            footer,
            text="\u5173\u95ed",
            command=window.destroy,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=7,
        ).pack(side=tk.RIGHT)

    def _write_strategy_release_recovery_loop_report(self, now: datetime | None = None) -> tuple[Path, dict[str, object]]:
        generated_at = now or datetime.now()
        settlements = list(reversed(get_recent_settlements(limit=300)))
        loop = self._strategy_release_recovery_loop(settlements)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = REPORT_DIR / build_strategy_release_recovery_loop_report_filename(generated_at)
        path.write_text(
            "\n".join(build_strategy_release_recovery_loop_report_lines(loop, generated_at=generated_at)),
            encoding="utf-8",
        )
        return path, loop

    def _attach_strategy_release_loop_report_to_recovery_run(self, path: Path, loop: dict[str, object]) -> None:
        record = dict(self.result_recovery_run_record or {})
        if not record.get("run_id"):
            return
        record.update(
            {
                "strategy_release_loop_report": str(path),
                "strategy_release_loop_report_name": path.name,
                "strategy_release_loop_summary": str(loop.get("summary_text") or "-"),
                "strategy_release_loop_health": str(loop.get("health_text") or "-"),
                "strategy_release_loop_pending_count": int(loop.get("pending_count", 0) or 0),
                "strategy_release_loop_stale_pending_count": int(loop.get("stale_pending_count", 0) or 0),
                "strategy_release_loop_missing_snapshot_count": int(loop.get("missing_snapshot_count", 0) or 0),
                "strategy_release_loop_hit_rate_text": str(loop.get("hit_rate_text") or "-"),
            }
        )
        messages = record.get("messages")
        if not isinstance(messages, list):
            messages = []
        record["messages"] = [*messages, f"\u653e\u884c\u56de\u6536\u95ed\u73af\u62a5\u544a: {path.name}"]
        self.result_recovery_run_record = dict(record)
        self._record_result_recovery_run(record)

    def export_strategy_release_recovery_loop_report(self) -> Path:
        path, _loop = self._write_strategy_release_recovery_loop_report()
        self.status_var.set(f"\u653e\u884c\u56de\u6536\u95ed\u73af\u62a5\u544a\u5df2\u5bfc\u51fa | {path.name}")
        messagebox.showinfo("\u653e\u884c\u56de\u6536\u95ed\u73af", f"\u5df2\u5bfc\u51fa\u62a5\u544a\n{path}")
        return path

    def _strategy_release_recovery_loop(self, settlements: list[dict] | None = None) -> dict:
        return build_strategy_release_recovery_loop(
            self.rows,
            snapshots=_load_prediction_snapshot_records(),
            settlements=settlements if settlements is not None else get_recent_settlements(limit=0),
        )

    def _video_review_fewshot_backup_count(self) -> int | None:
        state_dir = VIDEO_REVIEW_FEWSHOT_MEMORY_FILE.parent
        try:
            return len(
                list(state_dir.glob("video_review_fewshot_memory.backup_*.json"))
                + list(state_dir.glob("video_review_fewshot_memory.pre_rollback_*.json"))
            )
        except OSError:
            return None

    def _video_review_fewshot_memory_health_context(self, current_memory_summary: dict | None = None) -> dict[str, object]:
        memory = get_video_review_fewshot_memory()
        monitor = build_video_review_fewshot_memory_monitor(memory, current_memory_summary or {})
        quality = build_video_review_fewshot_memory_quality_alerts(monitor)
        health = build_video_review_fewshot_memory_health_summary(
            monitor,
            quality,
            backup_count=self._video_review_fewshot_backup_count(),
        )
        return {
            "monitor": monitor,
            "quality": quality,
            "health": health,
            "card_rows": build_video_review_fewshot_health_card_rows(monitor, quality, health),
            "action_rows": build_video_review_fewshot_action_rows(monitor, quality, health),
        }

    @staticmethod
    def _video_review_fewshot_card_text(rows: object, *, limit: int = 8) -> str:
        items = [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
        lines: list[str] = []
        for row in items[: max(0, int(limit))]:
            label = str(row.get("label") or "-")
            value = str(row.get("value") or "-")
            detail = str(row.get("detail") or "-")
            lines.append(f"{label}: {value} | {detail}")
        return "\n".join(lines) or "-"

    @staticmethod
    def _video_review_fewshot_action_text(rows: object, *, limit: int = 5) -> str:
        items = [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
        lines: list[str] = []
        for index, row in enumerate(items[: max(0, int(limit))], start=1):
            title = str(row.get("title") or "-")
            body = str(row.get("body") or "-")
            lines.append(f"{index}. {title} | {body}")
        return "\n".join(lines) or "-"

    def _strategy_release_pool_rows(
        self,
        settlements: list[dict] | None = None,
        limit: int = 10,
        release_loop: dict | None = None,
    ) -> list[tuple[str, str]]:
        snapshots = _load_prediction_snapshot_records()
        loop = release_loop if isinstance(release_loop, dict) else self._strategy_release_recovery_loop(settlements)
        pool = loop.get("rows", []) if isinstance(loop.get("rows"), list) else build_strategy_release_pool_rows(
            self.rows,
            snapshots=snapshots,
            settlements=settlements if settlements is not None else get_recent_settlements(limit=0),
        )
        items: list[tuple[str, str]] = []
        for item in pool[: max(0, int(limit))]:
            match_id = str(item.get("match_id") or "")
            snapshot = snapshots.get(match_id) if isinstance(snapshots.get(match_id), dict) else {}
            snapshot_match = snapshot.get("match", {}) if isinstance(snapshot.get("match"), dict) else {}
            live_status = str(item.get("loop_status") or item.get("settlement_status") or "-")
            if live_status != "\u5df2\u56de\u6536":
                current_status = _snapshot_status(snapshot_match) if snapshot_match else "\u7b49\u5f85\u5feb\u7167"
                live_status = str(item.get("loop_status") or ("\u53ef\u56de\u6536" if current_status == "\u5f85\u56de\u6536" else current_status))
            title = f"{live_status} | {item.get('title', '-')}"
            body = (
                f"\u5f00\u8d5b: {item.get('kickoff', '-')}\n"
                f"\u63a8\u8350: {item.get('recommendation', '-')} | \u7f6e\u4fe1 {item.get('confidence_text', '-')} | \u98ce\u9669 {item.get('risk_text', '-')}\n"
                f"\u5bfc\u51fa: {item.get('export_status', '-')} | \u5feb\u7167: {item.get('snapshot_status', '-')} | \u56de\u6536: {live_status} | \u5f85\u56de\u6536 {item.get('pending_days', 0)} \u5929\n"
                f"\u6e05\u5355: {item.get('allowlist_file', '-')} | \u5bfc\u51fa\u65f6\u95f4: {item.get('exported_at', '-')}\n"
                f"\u5019\u9009: {item.get('candidate_text', '-')}\n"
                f"\u539f\u56e0: {item.get('reason_text', '-')}"
            )
            items.append((title, body))
        return items

    def _strategy_row(self, parent: tk.Widget, title: str, body: str, command=None) -> None:
        frame = tk.Frame(parent, bg=PANEL_2, highlightbackground="#172638", highlightthickness=1)
        frame.pack(fill=tk.X, padx=18, pady=6)
        if command:
            frame.configure(cursor="hand2")
            frame.bind("<Button-1>", lambda _event: command())
        title_label = tk.Label(frame, text=title, bg=PANEL_2, fg=TEXT, font=("Microsoft YaHei UI", 11, "bold"))
        title_label.pack(anchor=tk.W, padx=14, pady=(10, 3))
        body_label = tk.Label(
            frame,
            text=body,
            bg=PANEL_2,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            justify=tk.LEFT,
            wraplength=350,
        )
        body_label.pack(anchor=tk.W, padx=14, pady=(0, 10))
        if command:
            title_label.configure(cursor="hand2")
            body_label.configure(cursor="hand2")
            title_label.bind("<Button-1>", lambda _event: command())
            body_label.bind("<Button-1>", lambda _event: command())

    def _strategy_admission_rows(self, limit: int = 12) -> list[tuple[str, str]]:
        order = {"allow": 0, "observe": 1, "block": 2}
        ranked = sorted(
            self.rows,
            key=lambda row: (
                order.get(str(_admission_payload(row.prediction).get("decision") or "observe"), 1),
                -float(row.prediction.get("confidence", 0) or 0),
            ),
        )
        items: list[tuple[str, str]] = []
        for row in ranked[: max(0, int(limit))]:
            admission = _admission_payload(row.prediction)
            reason_text = format_strategy_admission_reasons(admission, limit=4)
            threshold_text = format_strategy_admission_thresholds(admission)
            pick_text = format_strategy_admission_pick(admission)
            replay_guard_text = format_strategy_admission_replay_guard(admission)
            high_explanation = format_high_accuracy_strategy_release_explanation(
                row.prediction.get("high_accuracy_strategy", {}),
                admission,
                limit=2,
            )
            title = f"{_admission_text(row.prediction)} | {row.match.league} | {row.match.home_team} vs {row.match.away_team}"
            body = (
                f"推荐: {_strategy_text(row.prediction)} | 风险 {_risk_label(row.prediction.get('risk_level'))} | 置信 {_pct1(row.prediction.get('confidence'))}\n"
                f"高准正式/观察: {int(admission.get('active_count', 0) or 0)} / {int(admission.get('shadow_count', 0) or 0)} | "
                f"候选 {pick_text}\n"
                f"高准解释: {high_explanation}\n"
                f"原因: {reason_text}\n"
                f"门槛: {threshold_text}"
            )
            if replay_guard_text != "-":
                body += f"\nAgent Replay: {replay_guard_text}"
            items.append((title, body))
        return items

    def open_system_settings(self) -> None:
        self.current_nav_index = 6
        self.current_view = "settings"
        self._refresh_nav_highlight()
        shell = self._page_shell(
            "\u7cfb\u7edf\u8bbe\u7f6e",
            "\u672c\u5730\u8fd0\u884c\u53c2\u6570\u3001\u6570\u636e\u76ee\u5f55\u3001\u62a5\u544a\u76ee\u5f55\u548c\u98ce\u63a7\u9608\u503c\u8bf4\u660e",
        )

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u8fd0\u884c\u53c2\u6570", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 12))
        control = tk.Frame(left, bg=PANEL)
        control.pack(fill=tk.X, padx=18, pady=(0, 12))
        tk.Checkbutton(
            control,
            text="\u542f\u7528\u81ea\u52a8\u5237\u65b0",
            variable=self.auto_refresh_enabled,
            command=self._on_auto_refresh_changed,
            bg=PANEL,
            fg=TEXT,
            selectcolor=PANEL_2,
            activebackground=PANEL,
            activeforeground=TEXT,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(anchor=tk.W)

        interval = tk.Frame(left, bg=PANEL)
        interval.pack(fill=tk.X, padx=18, pady=(0, 16))
        tk.Label(interval, text="\u5237\u65b0\u95f4\u9694\uff08\u5206\u949f\uff09", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
        tk.Spinbox(
            interval,
            from_=3,
            to=120,
            width=6,
            textvariable=self.auto_refresh_interval_min,
            command=self._on_auto_refresh_changed,
            bg=PANEL_2,
            fg=TEXT,
            buttonbackground=PANEL_2,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10),
        ).pack(side=tk.RIGHT)

        recovery_control = tk.Frame(left, bg=PANEL)
        recovery_control.pack(fill=tk.X, padx=18, pady=(4, 12))
        tk.Checkbutton(
            recovery_control,
            text="\u542f\u7528\u81ea\u52a8\u8d5b\u679c\u56de\u6536",
            variable=self.auto_result_recovery_enabled,
            command=self._on_auto_result_recovery_changed,
            bg=PANEL,
            fg=TEXT,
            selectcolor=PANEL_2,
            activebackground=PANEL,
            activeforeground=TEXT,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(anchor=tk.W)

        recovery_interval = tk.Frame(left, bg=PANEL)
        recovery_interval.pack(fill=tk.X, padx=18, pady=(0, 16))
        tk.Label(recovery_interval, text="\u56de\u6536\u95f4\u9694\uff08\u5206\u949f\uff09", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
        tk.Spinbox(
            recovery_interval,
            from_=5,
            to=120,
            width=6,
            textvariable=self.auto_result_recovery_interval_min,
            command=self._on_auto_result_recovery_changed,
            bg=PANEL_2,
            fg=TEXT,
            buttonbackground=PANEL_2,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10),
        ).pack(side=tk.RIGHT)

        for label, value in [
            ("\u5f53\u524d\u6570\u636e\u6e90", self.data_source),
            ("\u6700\u8fd1\u52a0\u8f7d", self.last_loaded_at),
            ("\u6700\u8fd1\u8017\u65f6", f"{self.last_refresh_seconds:.2f}s" if self.last_refresh_seconds is not None else "-"),
            ("\u81ea\u52a8\u8d5b\u679c\u56de\u6536", "\u5f00\u542f" if self.auto_result_recovery_enabled.get() else "\u5173\u95ed"),
            ("\u8d5b\u679c\u56de\u6536\u95f4\u9694", f"{self.auto_result_recovery_interval_min.get()} \u5206\u949f"),
            ("\u9879\u76ee\u76ee\u5f55", str(PROJECT_ROOT)),
            ("\u6570\u636e\u76ee\u5f55", str(PROJECT_ROOT / "data")),
            ("\u62a5\u544a\u76ee\u5f55", str(REPORT_DIR)),
            ("\u8bbe\u7f6e\u6587\u4ef6", str(SETTINGS_PATH)),
        ]:
            self._kv_row(left, label, value)

        tk.Label(right, text="\u98ce\u63a7\u9608\u503c\u8bf4\u660e", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 12))
        settings_rows = [
            ("\u9ad8\u98ce\u9669", "\u51b7\u95e8\u6307\u6570\u9ad8\u6216\u5e02\u573a/\u6a21\u578b\u5206\u6b67\u660e\u663e\u65f6\u89e6\u53d1"),
            ("\u4e2d\u98ce\u9669", "\u6982\u7387\u8fb9\u754c\u4e0d\u6e05\u6216\u7a33\u5b9a\u6027\u4e0d\u8db3\u65f6\u89e6\u53d1"),
            ("\u4f4e\u98ce\u9669", "\u6a21\u578b\u3001\u5e02\u573a\u548c\u7a33\u5b9a\u6307\u6807\u65b9\u5411\u76f8\u5bf9\u4e00\u81f4"),
            ("\u7f6e\u4fe1\u5ea6\u5206\u5c42", "<50% \u89c2\u5bdf\uff0c50%-60% \u4f4e\u6743\u91cd\uff0c60%-70% \u5e38\u89c4\uff0c>70% \u9ad8\u4f18\u5148\u7ea7"),
            ("\u81ea\u52a8\u5237\u65b0", "\u8d5b\u4e8b\u5217\u8868\u5237\u65b0\u4e0e\u8d5b\u679c\u56de\u6536\u5206\u5f00\u63a7\u5236\uff0c\u914d\u7f6e\u4fdd\u5b58\u5230\u672c\u5730"),
            ("\u7248\u672c\u7ba1\u7406", "Git \u5df2\u542f\u7528\uff0c\u6bcf\u4e2a\u529f\u80fd\u70b9\u72ec\u7acb\u63d0\u4ea4"),
        ]
        for label, value in settings_rows:
            self._strategy_row(right, label, value)

        tk.Button(
            shell,
            text="\u7acb\u5373\u5237\u65b0",
            command=self.refresh,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(anchor=tk.E, pady=(14, 0))

    def _detail_metric(self, parent: tk.Widget, label: str, value: str, color: str) -> None:
        frame = self._card(parent, PANEL)
        frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))
        tk.Label(frame, text=label, bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W, padx=14, pady=(12, 3))
        tk.Label(frame, text=value, bg=PANEL, fg=color, font=("Microsoft YaHei UI", 14, "bold"), wraplength=150, justify=tk.LEFT).pack(anchor=tk.W, padx=14, pady=(0, 12))

    def _tone_color(self, tone: str) -> str:
        return {"good": GREEN, "warning": YELLOW, "watch": YELLOW, "bad": RED, "info": "#7aa2ff", "collecting": MUTED, "neutral": TEXT}.get(str(tone or "neutral"), TEXT)

    def _draw_probability_panel(self, parent: tk.Widget, row: DashboardRow) -> None:
        pred = row.prediction
        probs = pred.get("probabilities", {}) if isinstance(pred.get("probabilities"), dict) else {}
        indices = pred.get("indices", {}) if isinstance(pred.get("indices"), dict) else {}
        items = [
            ("\u4e3b\u80dc", probs.get("home", 0), "#7aa2ff"),
            ("\u5e73\u5c40", probs.get("draw", 0), YELLOW),
            ("\u5ba2\u80dc", probs.get("away", 0), GREEN),
            ("\u51b7\u95e8", indices.get("upset_index", 0), RED),
            ("\u7a33\u5b9a", indices.get("stability_index", 0), GREEN),
            ("\u4fe1\u5fc3", indices.get("confidence_index", 0), "#7aa2ff"),
        ]
        for label, value, color in items:
            self._bar_row(parent, label, float(value or 0), color)

        plays = tk.Frame(parent, bg=PANEL)
        plays.pack(fill=tk.X, padx=18, pady=(18, 8))
        draw_guard_label, draw_guard_body, _draw_guard_tone = _draw_release_guard_summary(pred)
        for label, value in [
            ("\u5927\u5c0f\u7403", f"{pred.get('ou_recommendation', '-')}  {_pct1(pred.get('ou_confidence'))}"),
            ("\u8ba9\u7403", f"{pred.get('handicap_recommendation', '-')}  {_pct1(pred.get('handicap_confidence'))}"),
            ("\u53ef\u80fd\u6bd4\u5206", f"{pred.get('score_recommendation', '-')}  {_pct1(pred.get('score_confidence'))}"),
            ("\u534a\u5168\u573a", f"{pred.get('htft_recommendation', '-')}  {_pct1(pred.get('htft_confidence'))}"),
            ("\u5e73\u5c40\u63a5\u7ba1", f"{draw_guard_label}  {draw_guard_body.splitlines()[0]}"),
        ]:
            line = tk.Frame(plays, bg=PANEL)
            line.pack(fill=tk.X, pady=5)
            tk.Label(line, text=label, bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
            tk.Label(line, text=value, bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 10, "bold")).pack(side=tk.RIGHT)

    def _bar_row(self, parent: tk.Widget, label: str, value: float, color: str) -> None:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill=tk.X, padx=18, pady=7)
        tk.Label(row, text=label, bg=PANEL, fg=MUTED, width=8, anchor=tk.W, font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
        canvas = tk.Canvas(row, height=12, bg="#172233", bd=0, highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 10))
        canvas.update_idletasks()
        width = max(canvas.winfo_width(), 180)
        canvas.create_rectangle(0, 0, width, 12, fill="#172233", outline="")
        canvas.create_rectangle(0, 0, max(2, width * max(0.0, min(value, 1.0))), 12, fill=color, outline="")
        tk.Label(row, text=_pct1(value), bg=PANEL, fg=TEXT, width=7, anchor=tk.E, font=("Microsoft YaHei UI", 10, "bold")).pack(side=tk.RIGHT)

    def _risk_counts(self) -> dict[str, int]:
        counts = {"low": 0, "medium": 0, "high": 0}
        for row in self.rows:
            counts[_risk_key(row.prediction.get("risk_level"))] += 1
        return counts

    def _draw_risk_chart(self) -> None:
        c = self.risk_chart
        c.delete("all")
        counts = self._risk_counts()
        total = max(sum(counts.values()), 1)
        cx, cy, radius = 96, 90, 58
        start = 90
        colors = {"low": GREEN, "medium": YELLOW, "high": RED}
        labels = {"low": "低风险", "medium": "中风险", "high": "高风险"}
        for key in ["low", "medium", "high"]:
            extent = 360 * counts[key] / total
            if extent > 0:
                c.create_arc(cx - radius, cy - radius, cx + radius, cy + radius, start=start, extent=-extent, fill=colors[key], outline=PANEL)
            start -= extent
        c.create_oval(cx - 31, cy - 31, cx + 31, cy + 31, fill=PANEL, outline=PANEL)

        y = 42
        for key in ["low", "medium", "high"]:
            c.create_rectangle(205, y + 2, 214, y + 11, fill=colors[key], outline=colors[key])
            pct = counts[key] / total
            c.create_text(225, y + 7, text=f"{labels[key]}   {counts[key]} ({pct:.1%})", fill=TEXT, anchor=tk.W, font=("Microsoft YaHei UI", 10))
            y += 34

    def _draw_confidence_chart(self) -> None:
        c = self.conf_chart
        c.delete("all")
        bins = [0, 0, 0, 0]
        for row in self.rows:
            conf = float(row.prediction.get("confidence", 0) or 0)
            if conf < 0.5:
                bins[0] += 1
            elif conf < 0.6:
                bins[1] += 1
            elif conf < 0.7:
                bins[2] += 1
            else:
                bins[3] += 1

        labels = ["<50%", "50%-60%", "60%-70%", ">70%"]
        left, bottom, top = 42, 150, 30
        max_value = max(max(bins), 1)
        c.create_line(left, top, left, bottom, fill="#263448")
        c.create_line(left, bottom, 360, bottom, fill="#263448")
        for i in range(5):
            y = bottom - i * (bottom - top) / 4
            c.create_line(left, y, 360, y, fill="#152233")
            c.create_text(left - 18, y, text=str(math.ceil(max_value * i / 4)), fill=MUTED, font=("Microsoft YaHei UI", 8))
        for idx, value in enumerate(bins):
            x = 76 + idx * 72
            height = 0 if max_value == 0 else value / max_value * 105
            c.create_rectangle(x, bottom - height, x + 34, bottom, fill=BLUE, outline="#7590ff")
            c.create_text(x + 17, bottom + 18, text=labels[idx], fill=MUTED, font=("Microsoft YaHei UI", 9))


def main() -> None:
    root = tk.Tk()
    SmartMatchDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
