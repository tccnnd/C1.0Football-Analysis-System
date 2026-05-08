from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from c1.data import AvailabilityProviderChain, adapt_legacy_match
from c1.runtime.release import C1ReleaseDecision, C1ReleaseRunner
from c1.runtime.shadow import C1ShadowRunResult


@dataclass(slots=True)
class C1ReleaseRow:
    match_id: str
    match_label: str
    governance_action: str
    release_action: str
    release_allowed: bool
    primary_reason_code: str | None
    candidate_count: int
    top_play: str | None
    top_selection: str | None
    top_line: float | None
    top_confidence: float
    provider_name: str


@dataclass(slots=True)
class C1ReleaseRunResult:
    total_matches: int
    rows: list[C1ReleaseRow]
    summary: dict[str, Any]


def _summarize_release_rows(rows: list[C1ReleaseRow]) -> dict[str, Any]:
    governance_counts: dict[str, int] = {}
    release_counts: dict[str, int] = {}
    provider_counts: dict[str, int] = {}
    release_allowed = 0
    for row in rows:
        governance_counts[row.governance_action] = governance_counts.get(row.governance_action, 0) + 1
        release_counts[row.release_action] = release_counts.get(row.release_action, 0) + 1
        provider_counts[row.provider_name] = provider_counts.get(row.provider_name, 0) + 1
        if row.release_allowed:
            release_allowed += 1
    return {
        "governance_counts": governance_counts,
        "release_counts": release_counts,
        "provider_counts": provider_counts,
        "release_allowed_count": release_allowed,
    }


def _build_release_row(
    match: Any,
    shadow_result: C1ShadowRunResult,
    release_decision: C1ReleaseDecision,
    provider_name: str,
) -> C1ReleaseRow:
    top_candidate = release_decision.candidates[0] if release_decision.candidates else None
    home_team = getattr(match, "home_team", "") or (match.get("home_team") if isinstance(match, Mapping) else "")
    away_team = getattr(match, "away_team", "") or (match.get("away_team") if isinstance(match, Mapping) else "")
    return C1ReleaseRow(
        match_id=shadow_result.match_id,
        match_label=f"{home_team} vs {away_team}",
        governance_action=str(release_decision.governance_action),
        release_action=str(release_decision.release_action),
        release_allowed=bool(release_decision.release_allowed),
        primary_reason_code=release_decision.primary_reason_code,
        candidate_count=len(release_decision.candidates),
        top_play=(top_candidate.play if top_candidate is not None else None),
        top_selection=(top_candidate.selection if top_candidate is not None else None),
        top_line=(top_candidate.line if top_candidate is not None else None),
        top_confidence=(top_candidate.confidence if top_candidate is not None else 0.0),
        provider_name=provider_name,
    )


def run_controlled_release_for_legacy_matches(
    *,
    project_root: str | Path,
    matches: list[Any],
    governance_state: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    extra_fields_by_match_id: Mapping[str, Mapping[str, Any]] | None = None,
    created_at: str | None = None,
) -> C1ReleaseRunResult:
    release_runner = C1ReleaseRunner(project_root)
    provider_chain = AvailabilityProviderChain.from_project_root(project_root)
    rows: list[C1ReleaseRow] = []
    for match in matches:
        match_id = getattr(match, "match_id", "") or (match.get("match_id") if isinstance(match, Mapping) else "")
        availability_result = provider_chain.resolve_for_match(match)
        merged_fields = dict(availability_result.record)
        if match_id and extra_fields_by_match_id and match_id in extra_fields_by_match_id:
            merged_fields.update(dict(extra_fields_by_match_id[match_id]))
        adapter_output = adapt_legacy_match(match, extra_fields=merged_fields)
        merged_context = dict(context or {})
        merged_context.setdefault("legacy_source", adapter_output.source)
        merged_context.update(adapter_output.metadata)
        merged_context["availability_provider"] = availability_result.provider_name
        merged_context["availability_provider_metadata"] = dict(availability_result.metadata)
        shadow_result, release_decision = release_runner.run_match(
            match_id=adapter_output.match_id,
            raw_fields=adapter_output.raw_fields,
            governance_state=governance_state or {},
            context=merged_context,
            created_at=created_at,
        )
        rows.append(
            _build_release_row(
                match=match,
                shadow_result=shadow_result,
                release_decision=release_decision,
                provider_name=availability_result.provider_name,
            )
        )
    return C1ReleaseRunResult(
        total_matches=len(rows),
        rows=rows,
        summary=_summarize_release_rows(rows),
    )
