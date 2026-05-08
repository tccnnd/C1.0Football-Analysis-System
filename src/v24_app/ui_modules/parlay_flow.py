from __future__ import annotations

from typing import Any, Callable, Mapping


def refresh_parlay_recommendations(
    *,
    matches: list[Any],
    predictions: Mapping[str, dict],
    active_release_allowed_ids: set[str],
    generator_fn: Callable[[list[Any], dict[str, dict], int], list[dict]],
    limit: int = 5,
) -> list[dict]:
    if active_release_allowed_ids:
        candidate_matches = [
            match
            for match in matches
            if str(getattr(match, "match_id", "")) in active_release_allowed_ids
            and str(getattr(match, "match_id", "")) in predictions
        ]
        candidate_predictions = {
            match_id: predictions[match_id]
            for match_id in active_release_allowed_ids
            if match_id in predictions
        }
    else:
        candidate_matches = [
            match for match in matches if str(getattr(match, "match_id", "")) in predictions
        ]
        candidate_predictions = dict(predictions)
    if len(candidate_predictions) < 2:
        return []
    return generator_fn(candidate_matches, candidate_predictions, limit)


def build_parlay_detail_lines(parlays: list[dict], *, limit: int = 5) -> list[str]:
    lines = ["二串一推荐"]
    for index, ticket in enumerate(parlays[:limit], start=1):
        legs = ticket.get("legs", [])
        if not isinstance(legs, list) or len(legs) < 2:
            continue
        leg_a = legs[0]
        leg_b = legs[1]
        lines.append(
            f"{index}. [{leg_a.get('play_type')}] {leg_a.get('home_team')} vs {leg_a.get('away_team')} {leg_a.get('pick')} + "
            f"[{leg_b.get('play_type')}] {leg_b.get('home_team')} vs {leg_b.get('away_team')} {leg_b.get('pick')} | "
            f"组合命中率 {float(ticket.get('expected_hit', 0) or 0):.1%}"
        )
        raw = ticket.get("expected_hit_raw")
        if raw is not None:
            lines.append(
                f"   校准说明: raw={float(raw or 0):.1%}, 折扣={float(ticket.get('correlation_discount', 1.0) or 1.0):.2f}, "
                f"质量={float(ticket.get('pair_quality_factor', 1.0) or 1.0):.2f}, "
                f"可靠度={float(ticket.get('play_reliability_factor', 1.0) or 1.0):.2f}"
            )
    return lines if len(lines) > 1 else []
