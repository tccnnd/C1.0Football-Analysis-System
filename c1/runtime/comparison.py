from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from c1.data import C1AvailabilityStore
from c1.runtime.legacy_bridge import run_shadow_for_legacy_match
from c1.runtime.shadow import C1ShadowRunResult, C1ShadowRunner


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _load_v24_core(project_root: Path):
    src_root = project_root / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    return __import__("v24_app.core", fromlist=["fetch_matches_v24", "predict_match"])


def _normalize_v24_side(prediction: dict[str, Any]) -> str:
    recommendation = str(prediction.get("recommendation", "")).strip().lower()
    mapping = {
        "home": "home",
        "draw": "draw",
        "away": "away",
        "主胜": "home",
        "平局": "draw",
        "客胜": "away",
        "涓昏儨": "home",
        "骞冲眬": "draw",
        "瀹㈣儨": "away",
    }
    if recommendation in mapping:
        return mapping[recommendation]
    probabilities = prediction.get("probabilities")
    if isinstance(probabilities, dict):
        ordered = sorted(
            ((str(key), float(value)) for key, value in probabilities.items() if key in {"home", "draw", "away"}),
            key=lambda item: item[1],
            reverse=True,
        )
        if ordered:
            return ordered[0][0]
    return ""


def _extract_translation_item(shadow_result: C1ShadowRunResult, play: str) -> dict[str, Any]:
    for item in shadow_result.translation_result.items:
        if item.play == play:
            return {
                "status": item.status,
                "selection": item.selection,
                "line": item.line,
                "confidence": item.confidence,
                "rationale": list(item.rationale),
            }
    return {
        "status": "MISSING",
        "selection": None,
        "line": None,
        "confidence": 0.0,
        "rationale": [],
    }


@dataclass(slots=True)
class C1ComparisonRow:
    match_id: str
    match_label: str
    v24_source: str
    v24_side: str
    v24_recommendation: str
    v24_confidence: float
    v24_handicap: str
    v24_totals: str
    c1_predicted_side: str
    c1_confidence: float
    governance_action: str
    one_x_two: dict[str, Any]
    handicap: dict[str, Any]
    totals: dict[str, Any]
    side_diverged: bool
    confidence_gap: float
    governance_reason_codes: list[str]
    governance_tags: list[str]
    governance_gate_statuses: dict[str, Any]
    primary_reason_code: str
    near_block: bool
    suggested_action: str


@dataclass(slots=True)
class C1ComparisonRunResult:
    generated_at: str
    total_matches: int
    rows: list[C1ComparisonRow]
    summary: dict[str, Any]
    markdown_report: str
    json_report: str


def _build_summary(rows: list[C1ComparisonRow]) -> dict[str, Any]:
    governance_counts: dict[str, int] = {}
    reason_code_counts: dict[str, int] = {}
    divergence_count = 0
    blocked_count = 0
    near_block_count = 0
    for row in rows:
        governance_counts[row.governance_action] = governance_counts.get(row.governance_action, 0) + 1
        if row.side_diverged:
            divergence_count += 1
        if row.governance_action == "BLOCK":
            blocked_count += 1
        if row.near_block:
            near_block_count += 1
        for code in row.governance_reason_codes:
            reason_code_counts[code] = reason_code_counts.get(code, 0) + 1
    return {
        "governance_counts": governance_counts,
        "reason_code_counts": dict(sorted(reason_code_counts.items(), key=lambda item: (-item[1], item[0]))),
        "side_divergence_count": divergence_count,
        "blocked_count": blocked_count,
        "near_block_count": near_block_count,
    }


def _line_text(item: dict[str, Any]) -> str:
    if item.get("line") is None:
        return ""
    return f" {float(item['line']):+g}"


def _top_reason_codes(summary: dict[str, Any], limit: int = 5) -> list[tuple[str, int]]:
    items = list((summary.get("reason_code_counts") or {}).items())
    return items[:limit]


def _primary_reason_code(shadow_result: C1ShadowRunResult) -> str:
    decision = shadow_result.governance_decision
    if decision.reason_codes:
        return str(decision.reason_codes[0])
    translation_items = shadow_result.translation_result.items
    for item in translation_items:
        if item.rationale:
            return str(item.rationale[0])
    return ""


def _near_block(shadow_result: C1ShadowRunResult) -> bool:
    decision = shadow_result.governance_decision
    if str(decision.action) == "BLOCK":
        return False
    reason_codes = set(str(code) for code in decision.reason_codes)
    if {"CHAOS_RISK_CRITICAL", "CIRCUIT_BREAKER_ACTIVE", "MARKET_DIVERGENCE_HARD", "INJURY_CONFLICT"} & reason_codes:
        return True
    gate_statuses = decision.trace.get("gate_statuses", {}) if isinstance(decision.trace, dict) else {}
    warn_count = sum(1 for status in gate_statuses.values() if str(status) == "WARN")
    hard_count = int(decision.trace.get("hard_reason_count", 0)) if isinstance(decision.trace, dict) else 0
    soft_count = int(decision.trace.get("soft_reason_count", 0)) if isinstance(decision.trace, dict) else 0
    return hard_count == 0 and (warn_count >= 3 or soft_count >= 3)


def _suggested_action(
    *,
    governance_action: str,
    reason_codes: list[str],
    near_block: bool,
    side_diverged: bool,
) -> str:
    reason_code_set = set(reason_codes)
    if governance_action == "BLOCK":
        return "阻断"
    if near_block:
        return "接近阻断"
    if {"LINEUP_UNKNOWN", "LINEUP_STALE", "INFO_QUALITY_LOW", "INFO_QUALITY_CRITICAL"} & reason_code_set:
        return "补阵容"
    if {"MARKET_DIVERGENCE_SOFT", "MARKET_DIVERGENCE_HARD", "HIGH_CONFIDENCE_LOW_INFO"} & reason_code_set:
        return "观察"
    if side_diverged:
        return "复核分歧"
    if governance_action == "DOWNGRADE":
        return "观察"
    if governance_action == "OBSERVE":
        return "观察"
    return "可放行"


def _write_reports(report_dir: Path, result: C1ComparisonRunResult) -> tuple[str, str]:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = _now_stamp()
    md_path = report_dir / f"c1_shadow_comparison_{stamp}.md"
    json_path = report_dir / f"c1_shadow_comparison_{stamp}.json"

    lines = [
        "# C1 Shadow Comparison Report",
        "",
        f"- Generated At: {result.generated_at}",
        f"- Match Count: {result.total_matches}",
        f"- Governance Counts: {result.summary.get('governance_counts', {})}",
        f"- Top Reason Codes: {_top_reason_codes(result.summary)}",
        f"- Side Divergence Count: {result.summary.get('side_divergence_count', 0)}",
        f"- Blocked Count: {result.summary.get('blocked_count', 0)}",
        f"- Near Block Count: {result.summary.get('near_block_count', 0)}",
        "",
        "| Match | V24 1X2 | V24 Handicap | V24 Totals | C1 Side | Governance | Suggested | Primary Reason | C1 1X2 | C1 Handicap | C1 Totals | Diverged | Near Block |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in result.rows:
        lines.append(
            f"| {row.match_label} | {row.v24_recommendation} ({row.v24_confidence:.2%}) | "
            f"{row.v24_handicap or '-'} | {row.v24_totals or '-'} | "
            f"{row.c1_predicted_side} ({row.c1_confidence:.2%}) | {row.governance_action} | {row.suggested_action} | {row.primary_reason_code or '-'} | "
            f"{row.one_x_two.get('selection') or '-'} [{row.one_x_two.get('status')}] | "
            f"{(row.handicap.get('selection') or '-')}{_line_text(row.handicap)} [{row.handicap.get('status')}] | "
            f"{(row.totals.get('selection') or '-')}{_line_text(row.totals)} [{row.totals.get('status')}] | "
            f"{'Y' if row.side_diverged else 'N'} | {'Y' if row.near_block else 'N'} |"
        )
        lines.append(
            f"|  |  |  |  |  |  | tags={','.join(row.governance_tags) or '-'} | "
            f"codes={','.join(row.governance_reason_codes) or '-'} | "
            f"gap={row.confidence_gap:+.4f} | gates={row.governance_gate_statuses} |  |  |  |"
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "generated_at": result.generated_at,
                "total_matches": result.total_matches,
                "summary": result.summary,
                "rows": [asdict(row) for row in result.rows],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return str(md_path), str(json_path)


def run_shadow_comparison_for_legacy_matches(
    *,
    project_root: str | Path,
    matches: list[Any],
    v24_predictor: Callable[[Any], dict[str, Any]] | None = None,
    shadow_runner: C1ShadowRunner | None = None,
    report_dir: str | Path | None = None,
    audit_dir: str | Path | None = None,
    availability_store: C1AvailabilityStore | None = None,
    governance_state: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    enable_xgboost: bool = True,
    enable_lightgbm: bool = False,
    created_at: str | None = None,
) -> C1ComparisonRunResult:
    root = Path(project_root)
    if v24_predictor is None:
        core = _load_v24_core(root)
        v24_predictor = getattr(core, "predict_match")
    runner = shadow_runner or C1ShadowRunner(root, audit_dir=audit_dir)
    store = availability_store or C1AvailabilityStore(root)
    rows: list[C1ComparisonRow] = []

    for match in matches:
        v24_prediction = v24_predictor(match)
        extra_fields = store.resolve_for_match(match)
        shadow_result = run_shadow_for_legacy_match(
            project_root=root,
            match=match,
            runner=runner,
            extra_fields=extra_fields,
            governance_state=governance_state or {},
            context=context or {},
            enable_xgboost=enable_xgboost,
            enable_lightgbm=enable_lightgbm,
            created_at=created_at,
        )
        v24_side = _normalize_v24_side(v24_prediction)
        c1_one_x_two = _extract_translation_item(shadow_result, "1x2")
        c1_handicap = _extract_translation_item(shadow_result, "handicap")
        c1_totals = _extract_translation_item(shadow_result, "totals")
        c1_side = str(shadow_result.inference_result.predicted_side)
        governance_reason_codes = [str(code) for code in shadow_result.governance_decision.reason_codes]
        governance_tags = [str(tag) for tag in shadow_result.governance_decision.tags]
        governance_gate_statuses = (
            dict(shadow_result.governance_decision.trace.get("gate_statuses", {}))
            if isinstance(shadow_result.governance_decision.trace, dict)
            else {}
        )
        side_diverged = bool(v24_side and c1_side and v24_side != c1_side)
        near_block = _near_block(shadow_result)
        governance_action = str(shadow_result.governance_decision.action)
        primary_reason_code = _primary_reason_code(shadow_result)
        rows.append(
            C1ComparisonRow(
                match_id=str(getattr(match, "match_id", "")),
                match_label=f"{getattr(match, 'home_team', '-')} vs {getattr(match, 'away_team', '-')}",
                v24_source=str(getattr(match, "source", "")),
                v24_side=v24_side,
                v24_recommendation=str(v24_prediction.get("recommendation", "")),
                v24_confidence=float(v24_prediction.get("confidence", 0.0)),
                v24_handicap=str(v24_prediction.get("handicap_display") or v24_prediction.get("handicap_recommendation") or ""),
                v24_totals=str(v24_prediction.get("total_goals_recommendation") or v24_prediction.get("ou_recommendation") or ""),
                c1_predicted_side=c1_side,
                c1_confidence=float(shadow_result.inference_result.confidence),
                governance_action=governance_action,
                one_x_two=c1_one_x_two,
                handicap=c1_handicap,
                totals=c1_totals,
                side_diverged=side_diverged,
                confidence_gap=round(float(shadow_result.inference_result.confidence) - float(v24_prediction.get("confidence", 0.0)), 6),
                governance_reason_codes=governance_reason_codes,
                governance_tags=governance_tags,
                governance_gate_statuses=governance_gate_statuses,
                primary_reason_code=primary_reason_code,
                near_block=near_block,
                suggested_action=_suggested_action(
                    governance_action=governance_action,
                    reason_codes=governance_reason_codes,
                    near_block=near_block,
                    side_diverged=side_diverged,
                ),
            )
        )

    generated_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = _build_summary(rows)
    result = C1ComparisonRunResult(
        generated_at=generated_at,
        total_matches=len(rows),
        rows=rows,
        summary=summary,
        markdown_report="",
        json_report="",
    )
    md_path, json_path = _write_reports(
        Path(report_dir) if report_dir is not None else (root / "reports"),
        result,
    )
    result.markdown_report = md_path
    result.json_report = json_path
    return result


def run_shadow_comparison_from_v24_fetch(
    *,
    project_root: str | Path,
    strict_today: bool = True,
    limit: int | None = None,
    report_dir: str | Path | None = None,
    audit_dir: str | Path | None = None,
    availability_store: C1AvailabilityStore | None = None,
    governance_state: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    enable_xgboost: bool = True,
    enable_lightgbm: bool = False,
    created_at: str | None = None,
) -> C1ComparisonRunResult:
    root = Path(project_root)
    core = _load_v24_core(root)
    fetch_result = getattr(core, "fetch_matches_v24")(strict_today=strict_today)
    matches = list(getattr(fetch_result, "matches", []))
    if limit is not None and limit > 0:
        matches = matches[:limit]
    return run_shadow_comparison_for_legacy_matches(
        project_root=root,
        matches=matches,
        v24_predictor=getattr(core, "predict_match"),
        report_dir=report_dir,
        audit_dir=audit_dir,
        availability_store=availability_store,
        governance_state=governance_state,
        context=context,
        enable_xgboost=enable_xgboost,
        enable_lightgbm=enable_lightgbm,
        created_at=created_at,
    )
