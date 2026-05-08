from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from c1.audit import C1AuditStore
from c1.data import AvailabilityProviderChain
from v24_app.core import (
    auto_settle_finished_matches,
    calibrate_play_thresholds_by_settlement_now,
    calibrate_play_thresholds_coverage_guardrail_now,
    calibrate_bayes_calibration_now,
    fetch_matches_v24,
    get_gate_metrics,
    get_parlay_selector_metrics,
    get_play_threshold_status,
    get_recent_settlements,
)
from v24_app.ui_modules.handicap_monitor_flow import build_handicap_shadow_report_lines


@dataclass
class SchedulerCycleConfig:
    lookback_days: int = 2
    gate_window: int = 30
    report_days: int = 14
    report_hour: int = 8
    report_minute: int = 5
    force_daily_report: bool = False
    bayes_calibration_enabled: bool = True
    bayes_min_new_settled: int = 1
    bayes_cooldown_hours: int = 6
    force_bayes_calibration: bool = False
    bucket_tuning_enabled: bool = True
    bucket_tuning_min_new_settled: int = 1
    bucket_tuning_cooldown_hours: int = 6
    force_bucket_tuning: bool = False
    coverage_guardrail_enabled: bool = True
    coverage_guardrail_min_new_settled: int = 1
    coverage_guardrail_cooldown_hours: int = 4
    coverage_guardrail_snapshot_limit: int = 240
    coverage_guardrail_min_predictions: int = 12
    force_coverage_guardrail: bool = False
    market_snapshot_enabled: bool = True
    market_snapshot_after_kickoff_minutes: int = 10


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _get_field(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _state_file(project_root: Path) -> Path:
    return project_root / "data" / "state" / "ops_scheduler_state.json"


def _heartbeat_file(project_root: Path) -> Path:
    return project_root / "reports" / "ops_scheduler_heartbeat.json"


def _daily_report_file(project_root: Path, now: datetime) -> Path:
    return project_root / "reports" / f"handicap_shadow_daily_{now.strftime('%Y%m%d')}.md"


def _ops_daily_report_file(project_root: Path, now: datetime) -> Path:
    return project_root / "reports" / f"ops_daily_summary_{now.strftime('%Y%m%d')}.md"


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def should_emit_daily_report(
    *,
    now: datetime,
    last_report_date: str,
    report_hour: int,
    report_minute: int,
    force: bool = False,
) -> bool:
    if force:
        return True
    today = now.strftime("%Y-%m-%d")
    if str(last_report_date or "") == today:
        return False
    trigger = (max(0, min(int(report_hour), 23)), max(0, min(int(report_minute), 59)))
    current = (now.hour, now.minute)
    return current >= trigger


def _parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def should_run_bayes_calibration(
    *,
    now: datetime,
    last_run_at: str,
    new_settled: int,
    min_new_settled: int,
    cooldown_hours: int,
    enabled: bool = True,
    force: bool = False,
) -> tuple[bool, str]:
    if force:
        return True, "forced"
    if not enabled:
        return False, "disabled"
    if int(new_settled) < max(0, int(min_new_settled)):
        return False, "insufficient_new_settled"
    cooldown = max(0, int(cooldown_hours))
    if cooldown <= 0:
        return True, "cooldown_disabled"
    last_dt = _parse_dt(last_run_at)
    if last_dt is None:
        return True, "never_run"
    elapsed_hours = (now - last_dt).total_seconds() / 3600.0
    if elapsed_hours >= float(cooldown):
        return True, "cooldown_elapsed"
    return False, "cooldown_active"


def should_run_coverage_guardrail(
    *,
    now: datetime,
    last_run_at: str,
    new_settled: int,
    min_new_settled: int,
    cooldown_hours: int,
    enabled: bool = True,
    force: bool = False,
) -> tuple[bool, str]:
    if force:
        return True, "forced"
    if not enabled:
        return False, "disabled"
    if int(new_settled) < max(0, int(min_new_settled)):
        return False, "insufficient_new_settled"
    cooldown = max(0, int(cooldown_hours))
    if cooldown <= 0:
        return True, "cooldown_disabled"
    last_dt = _parse_dt(last_run_at)
    if last_dt is None:
        return True, "never_run"
    elapsed_hours = (now - last_dt).total_seconds() / 3600.0
    if elapsed_hours >= float(cooldown):
        return True, "cooldown_elapsed"
    return False, "cooldown_active"


def should_run_bucket_tuning(
    *,
    now: datetime,
    last_run_at: str,
    new_settled: int,
    min_new_settled: int,
    cooldown_hours: int,
    enabled: bool = True,
    force: bool = False,
) -> tuple[bool, str]:
    return should_run_coverage_guardrail(
        now=now,
        last_run_at=last_run_at,
        new_settled=new_settled,
        min_new_settled=min_new_settled,
        cooldown_hours=cooldown_hours,
        enabled=enabled,
        force=force,
    )


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):.1%}"
    except Exception:
        return "0.0%"


def _ops_daily_report_lines(
    *,
    now: datetime,
    heartbeat: dict[str, Any],
    threshold_status: dict[str, Any],
) -> list[str]:
    settle = heartbeat.get("settle", {}) if isinstance(heartbeat, dict) else {}
    gate = heartbeat.get("gate", {}) if isinstance(heartbeat, dict) else {}
    bayes = heartbeat.get("bayes_calibration", {}) if isinstance(heartbeat, dict) else {}
    bucket = heartbeat.get("bucket_tuning", {}) if isinstance(heartbeat, dict) else {}
    guardrail = heartbeat.get("coverage_guardrail", {}) if isinstance(heartbeat, dict) else {}
    market = heartbeat.get("market_snapshots", {}) if isinstance(heartbeat, dict) else {}
    parlay_selector = heartbeat.get("parlay_selector", {}) if isinstance(heartbeat, dict) else {}
    overall = gate.get("overall", {}) if isinstance(gate, dict) else {}
    singles = gate.get("singles", {}) if isinstance(gate, dict) else {}
    parlays = gate.get("parlays", {}) if isinstance(gate, dict) else {}
    thresholds = threshold_status.get("thresholds", {}) if isinstance(threshold_status, dict) else {}

    lines = [
        "# V24 Ops Daily Summary",
        "",
        f"- Generated At: {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- New Settled Singles: {int(heartbeat.get('new_settled', 0) or 0)}",
        f"- New Settled Parlays: {int(heartbeat.get('new_parlay_settled', 0) or 0)}",
        f"- Total Settlement Records: {int(heartbeat.get('settlement_count', 0) or 0)}",
        "",
        "## Gate",
        "",
        f"- Overall: hit {_fmt_pct(overall.get('hit_rate', 0.0))} | expected {_fmt_pct(overall.get('expected_hit_rate', 0.0))} | ev_bias {_fmt_pct(overall.get('ev_bias', 0.0))} | losing_streak {int(overall.get('losing_streak', 0) or 0)} | breaker {bool(overall.get('breaker_on', False))}",
        f"- Singles: hit {_fmt_pct(singles.get('hit_rate', 0.0))} | expected {_fmt_pct(singles.get('expected_hit_rate', 0.0))} | ev_bias {_fmt_pct(singles.get('ev_bias', 0.0))}",
        f"- Parlays: hit {_fmt_pct(parlays.get('hit_rate', 0.0))} | expected {_fmt_pct(parlays.get('expected_hit_rate', 0.0))} | ev_bias {_fmt_pct(parlays.get('ev_bias', 0.0))}",
        "",
        "## Calibrations",
        "",
        f"- Bayes: trigger={bayes.get('trigger', '-')} | calibrated={bool(bayes.get('calibrated', False))} | reason={bayes.get('reason', '-')}",
        f"- Bucket Tuning: trigger={bucket.get('trigger', '-')} | calibrated={bool(bucket.get('calibrated', False))} | reason={bucket.get('reason', '-')}",
        f"- Coverage Guardrail: trigger={guardrail.get('trigger', '-')} | calibrated={bool(guardrail.get('calibrated', False))} | reason={guardrail.get('reason', '-')}",
        "",
        "## Threshold Snapshot",
        "",
        f"- mode: {threshold_status.get('mode', '-')}",
        f"- updated_at: {threshold_status.get('updated_at', '-')}",
        f"- 1x2={float(thresholds.get('1x2', 0) or 0):.2f}, handicap={float(thresholds.get('handicap', 0) or 0):.2f}, total_goals={float(thresholds.get('total_goals', 0) or 0):.2f}, score={float(thresholds.get('score', 0) or 0):.2f}, htft={float(thresholds.get('htft', 0) or 0):.2f}",
        "",
        "## Market Snapshots",
        "",
        f"- enabled={bool(market.get('enabled', False))} | captured={int(market.get('captured', 0) or 0)} | matches={int(market.get('matches', 0) or 0)} | reason={market.get('reason', '-')}",
        "",
        "## Parlay Selector Health",
        "",
        f"- tickets={int(parlay_selector.get('ticket_count', 0) or 0)} | unique_matches={int(parlay_selector.get('unique_match_count', 0) or 0)} | max_exposure={int(parlay_selector.get('max_match_exposure', 0) or 0)} | avg_exposure={float(parlay_selector.get('avg_match_exposure', 0.0) or 0.0):.2f}",
        f"- mixed_ratio={_fmt_pct(parlay_selector.get('mixed_ratio', 0.0))} | avg_expected_hit={_fmt_pct(parlay_selector.get('avg_expected_hit', 0.0))} | max_expected_hit={_fmt_pct(parlay_selector.get('max_expected_hit', 0.0))}",
        f"- risk_flags: high_expected_hit={int(parlay_selector.get('high_expected_hit_count', 0) or 0)}, low_discount={int(parlay_selector.get('low_discount_count', 0) or 0)}, high_upset_leg={int(parlay_selector.get('high_upset_leg_count', 0) or 0)}",
        f"- factors: pair_quality={float(parlay_selector.get('avg_pair_quality_factor', 0.0) or 0.0):.2f}, play_reliability={float(parlay_selector.get('avg_play_reliability_factor', 0.0) or 0.0):.2f}",
    ]

    captured_by_phase = market.get("captured_by_phase", {}) if isinstance(market, dict) else {}
    if isinstance(captured_by_phase, dict) and captured_by_phase:
        lines.append(
            f"- phase_counts: T120={int(captured_by_phase.get('T120', 0) or 0)}, T30={int(captured_by_phase.get('T30', 0) or 0)}, T5={int(captured_by_phase.get('T5', 0) or 0)}"
        )

    settle_items = settle.get("settled_items", []) if isinstance(settle, dict) else []
    if isinstance(settle_items, list) and settle_items:
        lines.extend(["", "## Recent Settled Matches", "", "| Match | Result | Hit |", "|---|---|---|"])
        for item in settle_items[-10:]:
            if not isinstance(item, dict):
                continue
            match_text = f"{_text(item.get('home_team'))} vs {_text(item.get('away_team'))}".strip() or _text(item.get("match_id"))
            lines.append(
                f"| {match_text} | {_text(item.get('result'))} | {str(item.get('is_correct'))} |"
            )
    return lines


def _parse_kickoff(match: Any) -> datetime | None:
    match_date = _text(_get_field(match, "match_date"))
    match_time = _text(_get_field(match, "match_time"))
    if not match_date or not match_time:
        return None
    try:
        return datetime.strptime(f"{match_date} {match_time}", "%Y-%m-%d %H:%M")
    except Exception:
        return None


def _market_snapshot_phases_for_minutes(minutes_to_kickoff: float, after_kickoff_minutes: int) -> list[str]:
    phases: list[str] = []
    if minutes_to_kickoff <= 120:
        phases.append("T120")
    if minutes_to_kickoff <= 30:
        phases.append("T30")
    if minutes_to_kickoff <= 5:
        phases.append("T5")
    if minutes_to_kickoff < -max(0, int(after_kickoff_minutes)):
        return []
    return phases


def capture_pre_match_market_snapshots(
    *,
    project_root: Path,
    now: datetime,
    state: dict[str, Any],
    enabled: bool,
    after_kickoff_minutes: int,
) -> dict[str, Any]:
    if not enabled:
        return {"enabled": False, "captured": 0, "matches": 0, "reason": "disabled"}

    try:
        fetch_result = fetch_matches_v24(strict_today=True)
    except Exception as exc:
        return {"enabled": True, "captured": 0, "matches": 0, "reason": f"fetch_failed:{exc}"}
    matches = list(getattr(fetch_result, "matches", []) or [])
    if not matches:
        return {"enabled": True, "captured": 0, "matches": 0, "reason": "no_matches"}

    audit = C1AuditStore(project_root)
    provider_chain = AvailabilityProviderChain.from_project_root(project_root)
    phase_state_raw = state.get("captured_market_phases", {})
    phase_state = dict(phase_state_raw) if isinstance(phase_state_raw, dict) else {}
    pruned_phase_state: dict[str, str] = {}
    for key, captured_at in phase_state.items():
        captured_dt = _parse_dt(captured_at)
        if captured_dt is None:
            continue
        if (now - captured_dt).days <= 14:
            pruned_phase_state[_text(key)] = captured_dt.strftime("%Y-%m-%d %H:%M:%S")
    phase_state = pruned_phase_state
    captured = 0
    captured_by_phase = {"T120": 0, "T30": 0, "T5": 0}

    for match in matches:
        kickoff = _parse_kickoff(match)
        if kickoff is None:
            continue
        minutes_to_kickoff = (kickoff - now).total_seconds() / 60.0
        phases = _market_snapshot_phases_for_minutes(minutes_to_kickoff, after_kickoff_minutes=after_kickoff_minutes)
        if not phases:
            continue
        availability = provider_chain.resolve_for_match(match)
        for phase in phases:
            match_id = _text(_get_field(match, "match_id"))
            phase_key = f"{match_id}|{phase}"
            if not match_id or phase_key in phase_state:
                continue
            snapshot_payload = {
                "phase": phase,
                "minutes_to_kickoff": round(minutes_to_kickoff, 3),
                "kickoff_at": kickoff.strftime("%Y-%m-%d %H:%M:%S"),
                "league": _text(_get_field(match, "league")),
                "match_date": _text(_get_field(match, "match_date")),
                "match_time": _text(_get_field(match, "match_time")),
                "home_team": _text(_get_field(match, "home_team")),
                "away_team": _text(_get_field(match, "away_team")),
                "source": _text(_get_field(match, "source")),
                "source_id": _text(_get_field(match, "source_id")),
                "odds_home": _safe_float(_get_field(match, "odds_home"), 0.0),
                "odds_draw": _safe_float(_get_field(match, "odds_draw"), 0.0),
                "odds_away": _safe_float(_get_field(match, "odds_away"), 0.0),
                "opening_odds_home": _safe_float(_get_field(match, "opening_odds_home"), 0.0),
                "opening_odds_draw": _safe_float(_get_field(match, "opening_odds_draw"), 0.0),
                "opening_odds_away": _safe_float(_get_field(match, "opening_odds_away"), 0.0),
                "handicap_line": _safe_float(_get_field(match, "handicap_line"), 0.0),
                "return_rate": _safe_float(_get_field(match, "return_rate"), 0.0),
                "kelly_home": _safe_float(_get_field(match, "kelly_home"), 0.0),
                "kelly_draw": _safe_float(_get_field(match, "kelly_draw"), 0.0),
                "kelly_away": _safe_float(_get_field(match, "kelly_away"), 0.0),
                "availability_provider": availability.provider_name,
                "availability_record": dict(availability.record),
            }
            metadata = {
                "provider_name": availability.provider_name,
                "provider_metadata": dict(availability.metadata),
                "capture_mode": "scheduler_premarket",
            }
            audit.record_market_snapshot(
                match_id=match_id,
                phase=phase,
                snapshot=snapshot_payload,
                attribution_tags=["prematch", "scheduler", "market_snapshot"],
                metadata=metadata,
            )
            phase_state[phase_key] = now.strftime("%Y-%m-%d %H:%M:%S")
            captured += 1
            captured_by_phase[phase] = captured_by_phase.get(phase, 0) + 1

    state["captured_market_phases"] = phase_state
    return {
        "enabled": True,
        "captured": captured,
        "captured_by_phase": captured_by_phase,
        "matches": len(matches),
        "provider_chain_size": len(provider_chain.providers),
        "reason": "ok",
    }


def run_scheduler_cycle(project_root: Path, config: SchedulerCycleConfig, now: datetime | None = None) -> dict:
    clock = now or datetime.now()
    root = Path(project_root).resolve()
    state_path = _state_file(root)
    heartbeat_path = _heartbeat_file(root)
    state = _load_state(state_path)

    lookback_days = max(0, min(_safe_int(config.lookback_days, 2), 7))
    gate_window = max(1, min(_safe_int(config.gate_window, 30), 500))
    report_days = max(1, min(_safe_int(config.report_days, 14), 60))

    settle_result = auto_settle_finished_matches(prediction_cache=None, lookback_days=lookback_days)
    new_settled = _safe_int((settle_result or {}).get("new_settled", 0), 0)
    new_parlay_settled = _safe_int((settle_result or {}).get("new_parlay_settled", 0), 0)
    settlements = get_recent_settlements(limit=500)
    gate_metrics = get_gate_metrics(window=gate_window)
    parlay_selector_metrics = get_parlay_selector_metrics(limit=120)

    last_bayes_run_at = str(state.get("last_bayes_calibration_at", ""))
    run_bayes, bayes_trigger_reason = should_run_bayes_calibration(
        now=clock,
        last_run_at=last_bayes_run_at,
        new_settled=new_settled,
        min_new_settled=_safe_int(config.bayes_min_new_settled, 1),
        cooldown_hours=_safe_int(config.bayes_cooldown_hours, 6),
        enabled=bool(config.bayes_calibration_enabled),
        force=bool(config.force_bayes_calibration),
    )
    bayes_result: dict[str, Any] = {
        "calibrated": False,
        "reason": "skipped",
        "trigger": bayes_trigger_reason,
    }
    if run_bayes:
        bayes_result = calibrate_bayes_calibration_now()
        bayes_result["trigger"] = bayes_trigger_reason
        state["last_bayes_calibration_at"] = clock.strftime("%Y-%m-%d %H:%M:%S")
        state["last_bayes_calibration_reason"] = str(bayes_result.get("reason", ""))
        state["last_bayes_calibrated"] = bool(bayes_result.get("calibrated"))

    last_bucket_tuning_at = str(state.get("last_bucket_tuning_at", ""))
    run_bucket_tuning, bucket_tuning_trigger_reason = should_run_bucket_tuning(
        now=clock,
        last_run_at=last_bucket_tuning_at,
        new_settled=new_settled,
        min_new_settled=_safe_int(config.bucket_tuning_min_new_settled, 1),
        cooldown_hours=_safe_int(config.bucket_tuning_cooldown_hours, 6),
        enabled=bool(config.bucket_tuning_enabled),
        force=bool(config.force_bucket_tuning),
    )
    bucket_tuning_result: dict[str, Any] = {
        "calibrated": False,
        "reason": "skipped",
        "trigger": bucket_tuning_trigger_reason,
    }
    if run_bucket_tuning:
        bucket_tuning_result = calibrate_play_thresholds_by_settlement_now(
            limit=500,
            min_samples=18,
            write_report=True,
        )
        bucket_tuning_result["trigger"] = bucket_tuning_trigger_reason
        state["last_bucket_tuning_at"] = clock.strftime("%Y-%m-%d %H:%M:%S")
        state["last_bucket_tuning_reason"] = str(bucket_tuning_result.get("reason", ""))
        state["last_bucket_tuning_calibrated"] = bool(bucket_tuning_result.get("calibrated"))

    last_guardrail_run_at = str(state.get("last_coverage_guardrail_at", ""))
    run_guardrail, guardrail_trigger_reason = should_run_coverage_guardrail(
        now=clock,
        last_run_at=last_guardrail_run_at,
        new_settled=new_settled,
        min_new_settled=_safe_int(config.coverage_guardrail_min_new_settled, 1),
        cooldown_hours=_safe_int(config.coverage_guardrail_cooldown_hours, 4),
        enabled=bool(config.coverage_guardrail_enabled),
        force=bool(config.force_coverage_guardrail),
    )
    coverage_guardrail_result: dict[str, Any] = {
        "calibrated": False,
        "reason": "skipped",
        "trigger": guardrail_trigger_reason,
    }
    if run_guardrail:
        coverage_guardrail_result = calibrate_play_thresholds_coverage_guardrail_now(
            snapshot_limit=max(0, _safe_int(config.coverage_guardrail_snapshot_limit, 240)),
            min_predictions=max(1, _safe_int(config.coverage_guardrail_min_predictions, 12)),
            write_report=True,
        )
        coverage_guardrail_result["trigger"] = guardrail_trigger_reason
        state["last_coverage_guardrail_at"] = clock.strftime("%Y-%m-%d %H:%M:%S")
        state["last_coverage_guardrail_reason"] = str(coverage_guardrail_result.get("reason", ""))
        state["last_coverage_guardrail_calibrated"] = bool(coverage_guardrail_result.get("calibrated"))

    market_snapshot_result = capture_pre_match_market_snapshots(
        project_root=root,
        now=clock,
        state=state,
        enabled=bool(config.market_snapshot_enabled),
        after_kickoff_minutes=_safe_int(config.market_snapshot_after_kickoff_minutes, 10),
    )

    last_report_date = str(state.get("last_daily_report_date", ""))
    should_report = should_emit_daily_report(
        now=clock,
        last_report_date=last_report_date,
        report_hour=config.report_hour,
        report_minute=config.report_minute,
        force=bool(config.force_daily_report),
    )

    daily_report_path: Path | None = None
    ops_daily_report_path: Path | None = None
    if should_report:
        daily_report_path = _daily_report_file(root, clock)
        lines = build_handicap_shadow_report_lines(
            settlements,
            days=report_days,
            gate_window=gate_window,
            breaker_threshold=3,
            now=clock,
        )
        daily_report_path.parent.mkdir(parents=True, exist_ok=True)
        daily_report_path.write_text("\n".join(lines), encoding="utf-8")
        threshold_status = get_play_threshold_status()
        ops_daily_report_path = _ops_daily_report_file(root, clock)
        ops_daily_report_path.write_text(
            "\n".join(
                _ops_daily_report_lines(
                    now=clock,
                    heartbeat={
                        "settle": settle_result,
                        "new_settled": new_settled,
                        "new_parlay_settled": new_parlay_settled,
                        "gate": gate_metrics,
                        "bayes_calibration": bayes_result,
                        "bucket_tuning": bucket_tuning_result,
                        "coverage_guardrail": coverage_guardrail_result,
                        "market_snapshots": market_snapshot_result,
                        "parlay_selector": parlay_selector_metrics,
                        "settlement_count": len(settlements),
                    },
                    threshold_status=threshold_status,
                )
            ),
            encoding="utf-8",
        )
        state["last_daily_report_date"] = clock.strftime("%Y-%m-%d")
        state["last_daily_report_path"] = str(daily_report_path)
        state["last_ops_daily_report_path"] = str(ops_daily_report_path)

    state["updated_at"] = clock.strftime("%Y-%m-%d %H:%M:%S")
    _save_json(state_path, state)

    heartbeat = {
        "updated_at": clock.strftime("%Y-%m-%d %H:%M:%S"),
        "lookback_days": lookback_days,
        "gate_window": gate_window,
        "report_days": report_days,
        "daily_report_emitted": bool(daily_report_path),
        "daily_report_path": str(daily_report_path) if daily_report_path else "",
        "ops_daily_report_emitted": bool(ops_daily_report_path),
        "ops_daily_report_path": str(ops_daily_report_path) if ops_daily_report_path else "",
        "settle": settle_result,
        "new_settled": new_settled,
        "new_parlay_settled": new_parlay_settled,
        "bayes_calibration": bayes_result,
        "bucket_tuning": bucket_tuning_result,
        "coverage_guardrail": coverage_guardrail_result,
        "market_snapshots": market_snapshot_result,
        "parlay_selector": parlay_selector_metrics,
        "gate": gate_metrics,
        "settlement_count": len(settlements),
    }
    _save_json(heartbeat_path, heartbeat)
    return heartbeat
