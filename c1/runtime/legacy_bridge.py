from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from c1.data import AvailabilityProviderChain, adapt_legacy_match, adapt_legacy_matches, load_elo_ratings, resolve_team_rating
from c1.runtime.shadow import C1ShadowRunResult, C1ShadowRunner


def run_shadow_for_legacy_match(
    *,
    project_root: str | Path,
    match: Any,
    runner: C1ShadowRunner | None = None,
    governance_state: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    extra_fields: Mapping[str, Any] | None = None,
    enable_xgboost: bool = True,
    enable_lightgbm: bool = False,
    created_at: str | None = None,
) -> C1ShadowRunResult:
    project_root = Path(project_root)
    availability_result = AvailabilityProviderChain.from_project_root(project_root).resolve_for_match(match)
    merged_extra_fields = dict(availability_result.record)
    if extra_fields:
        merged_extra_fields.update(dict(extra_fields))
    
    # Load ELO ratings from V24 state and inject into extra_fields
    elo_ratings = load_elo_ratings(project_root)
    home_team = str(getattr(match, "home_team", "")).strip()
    away_team = str(getattr(match, "away_team", "")).strip()
    if home_team and "home_rating" not in merged_extra_fields:
        merged_extra_fields["home_rating"] = resolve_team_rating(home_team, elo_ratings)
    if away_team and "away_rating" not in merged_extra_fields:
        merged_extra_fields["away_rating"] = resolve_team_rating(away_team, elo_ratings)
    
    adapter_output = adapt_legacy_match(match, extra_fields=merged_extra_fields)
    shadow_runner = runner or C1ShadowRunner(project_root)
    merged_context = dict(context or {})
    merged_context.setdefault("legacy_source", adapter_output.source)
    merged_context.update(adapter_output.metadata)
    merged_context["availability_provider"] = availability_result.provider_name
    merged_context["availability_provider_metadata"] = dict(availability_result.metadata)
    return shadow_runner.run_match(
        match_id=adapter_output.match_id,
        raw_fields=adapter_output.raw_fields,
        governance_state=governance_state or {},
        context=merged_context,
        enable_xgboost=enable_xgboost,
        enable_lightgbm=enable_lightgbm,
        created_at=created_at,
    )


def run_shadow_for_legacy_matches(
    *,
    project_root: str | Path,
    matches: list[Any],
    runner: C1ShadowRunner | None = None,
    governance_state: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    extra_fields_by_match_id: Mapping[str, Mapping[str, Any]] | None = None,
    enable_xgboost: bool = True,
    enable_lightgbm: bool = False,
    created_at: str | None = None,
) -> list[C1ShadowRunResult]:
    project_root = Path(project_root)
    shadow_runner = runner or C1ShadowRunner(project_root)
    provider_chain = AvailabilityProviderChain.from_project_root(project_root)
    elo_ratings = load_elo_ratings(project_root)
    results: list[C1ShadowRunResult] = []
    for adapter_output in adapt_legacy_matches(matches, extra_fields_by_match_id=extra_fields_by_match_id):
        availability_result = provider_chain.resolve_for_match(
            {
                "match_id": adapter_output.match_id,
                "source_id": adapter_output.metadata.get("source_id", ""),
                "match_date": adapter_output.raw_fields.get("match_date", ""),
                "league": adapter_output.raw_fields.get("league", ""),
                "home_team": adapter_output.raw_fields.get("home_team", ""),
                "away_team": adapter_output.raw_fields.get("away_team", ""),
            }
        )
        merged_fields = dict(availability_result.record)
        if extra_fields_by_match_id and adapter_output.match_id in extra_fields_by_match_id:
            merged_fields.update(dict(extra_fields_by_match_id[adapter_output.match_id]))
        
        # Inject ELO ratings if not already present
        home_team = str(adapter_output.raw_fields.get("home_team", "")).strip()
        away_team = str(adapter_output.raw_fields.get("away_team", "")).strip()
        if home_team and "home_rating" not in merged_fields:
            merged_fields["home_rating"] = resolve_team_rating(home_team, elo_ratings)
        if away_team and "away_rating" not in merged_fields:
            merged_fields["away_rating"] = resolve_team_rating(away_team, elo_ratings)
        
        if merged_fields:
            adapter_output = adapt_legacy_match(
                {
                    "match_id": adapter_output.match_id,
                    "source": adapter_output.source,
                    "source_id": adapter_output.metadata.get("source_id", ""),
                    "home_team": adapter_output.raw_fields.get("home_team", ""),
                    "away_team": adapter_output.raw_fields.get("away_team", ""),
                    "league": adapter_output.raw_fields.get("league", ""),
                    "match_date": adapter_output.raw_fields.get("match_date", ""),
                    "match_time": adapter_output.raw_fields.get("match_time", ""),
                    "odds_home": adapter_output.raw_fields.get("odds_home", 0.0),
                    "odds_draw": adapter_output.raw_fields.get("odds_draw", 0.0),
                    "odds_away": adapter_output.raw_fields.get("odds_away", 0.0),
                    "handicap_line": adapter_output.raw_fields.get("handicap_line", 0.0),
                    "opening_odds_home": adapter_output.raw_fields.get("opening_odds_home", 0.0),
                    "opening_odds_draw": adapter_output.raw_fields.get("opening_odds_draw", 0.0),
                    "opening_odds_away": adapter_output.raw_fields.get("opening_odds_away", 0.0),
                    "return_rate": adapter_output.raw_fields.get("return_rate", 0.0),
                    "kelly_home": adapter_output.raw_fields.get("kelly_home", 0.0),
                    "kelly_draw": adapter_output.raw_fields.get("kelly_draw", 0.0),
                    "kelly_away": adapter_output.raw_fields.get("kelly_away", 0.0),
                },
                extra_fields=merged_fields,
            )
        merged_context = dict(context or {})
        merged_context.setdefault("legacy_source", adapter_output.source)
        merged_context.update(adapter_output.metadata)
        merged_context["availability_provider"] = availability_result.provider_name
        merged_context["availability_provider_metadata"] = dict(availability_result.metadata)
        results.append(
            shadow_runner.run_match(
                match_id=adapter_output.match_id,
                raw_fields=adapter_output.raw_fields,
                governance_state=governance_state or {},
                context=merged_context,
                enable_xgboost=enable_xgboost,
                enable_lightgbm=enable_lightgbm,
                created_at=created_at,
            )
        )
    return results
