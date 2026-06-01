"""
Scoreline Translation Module

Translates match probabilities into specific scoreline outcomes.
Uses Poisson distribution to estimate goal distributions for each team,
then generates a score matrix and filters by confidence.

Reference: footBayes (Poisson scoreline)
"""

from __future__ import annotations

import math
from typing import Any
from dataclasses import dataclass, field


@dataclass(slots=True)
class TranslationItem:
    play: str
    status: str
    selection: str | None = None
    line: float | None = None
    confidence: float = 0.0
    rationale: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float with default fallback."""
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _clamp(value: float, lower: float, upper: float) -> float:
    """Clamp value between lower and upper bounds."""
    return max(lower, min(upper, value))


def _poisson_pmf(k: int, lambda_: float) -> float:
    """
    Calculate Poisson probability mass function.
    P(X = k) = (e^-λ * λ^k) / k!
    """
    if lambda_ <= 0 or k < 0:
        return 0.0
    try:
        return (math.exp(-lambda_) * (lambda_ ** k)) / math.factorial(k)
    except (OverflowError, ValueError):
        return 0.0


def estimate_expected_goals(
    home_prob: float,
    away_prob: float,
    draw_prob: float,
    home_rating: float = 1500.0,
    away_rating: float = 1500.0,
) -> tuple[float, float]:
    """
    Estimate expected goals for home and away teams.
    
    Uses a simplified model based on win probabilities and ELO ratings.
    
    Args:
        home_prob: Home win probability
        away_prob: Away win probability
        draw_prob: Draw probability
        home_rating: Home team ELO rating
        away_rating: Away team ELO rating
    
    Returns:
        Tuple of (home_expected_goals, away_expected_goals)
    """
    # Base expected goals from probabilities
    # Higher win probability suggests more goals
    base_home_xg = 1.2 + (home_prob - away_prob) * 1.5
    base_away_xg = 1.2 + (away_prob - home_prob) * 1.5
    
    # Adjust for ELO rating difference
    rating_diff = (home_rating - away_rating) / 400.0
    rating_adjustment = rating_diff * 0.3
    
    home_xg = _clamp(base_home_xg + rating_adjustment, 0.3, 4.0)
    away_xg = _clamp(base_away_xg - rating_adjustment, 0.3, 4.0)
    
    return home_xg, away_xg


def generate_score_matrix(
    home_xg: float,
    away_xg: float,
    max_goals: int = 5,
) -> dict[tuple[int, int], float]:
    """
    Generate score matrix using Poisson distribution.
    
    Args:
        home_xg: Home team expected goals
        away_xg: Away team expected goals
        max_goals: Maximum goals per team to consider
    
    Returns:
        Dict mapping (home_goals, away_goals) to probability
    """
    matrix = {}
    
    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            home_prob = _poisson_pmf(home_goals, home_xg)
            away_prob = _poisson_pmf(away_goals, away_xg)
            score_prob = home_prob * away_prob
            
            if score_prob > 0:
                matrix[(home_goals, away_goals)] = score_prob
    
    # Renormalize to sum to 1.0
    total = sum(matrix.values())
    if total > 0:
        matrix = {k: v / total for k, v in matrix.items()}
    
    return matrix


def filter_score_matrix(
    matrix: dict[tuple[int, int], float],
    min_probability: float = 0.02,
    max_outcomes: int = 20,
) -> dict[tuple[int, int], float]:
    """
    Filter score matrix by probability threshold and limit outcomes.
    
    Args:
        matrix: Score matrix from generate_score_matrix
        min_probability: Minimum probability to include
        max_outcomes: Maximum number of outcomes to keep
    
    Returns:
        Filtered score matrix
    """
    # Filter by minimum probability
    filtered = {k: v for k, v in matrix.items() if v >= min_probability}
    
    # Sort by probability and keep top outcomes
    sorted_scores = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
    filtered = dict(sorted_scores[:max_outcomes])
    
    # Renormalize
    total = sum(filtered.values())
    if total > 0:
        filtered = {k: v / total for k, v in filtered.items()}
    
    return filtered


def score_to_selection(home_goals: int, away_goals: int) -> str:
    """
    Convert score to betting selection string.
    
    Args:
        home_goals: Home team goals
        away_goals: Away team goals
    
    Returns:
        Selection string like "2-1" or "0-0"
    """
    return f"{home_goals}-{away_goals}"


def translate_scoreline(
    *,
    raw_probabilities: dict[str, float],
    confidence: float,
    governance_status: str,
    home_rating: float = 1500.0,
    away_rating: float = 1500.0,
    config: dict[str, Any] | None = None,
) -> TranslationItem:
    """
    Translate match probabilities into scoreline translation item.
    
    Args:
        raw_probabilities: FT probabilities {'home', 'draw', 'away'}
        confidence: Model confidence score
        governance_status: Governance action status (ACTIVE, DOWNGRADED, SHADOW, BLOCKED)
        home_rating: Home team ELO rating
        away_rating: Away team ELO rating
        config: Configuration dict with thresholds
    
    Returns:
        TranslationItem for scoreline play type
    """
    config = config or {}
    
    home_prob = _safe_float(raw_probabilities.get("home"), 0.33)
    draw_prob = _safe_float(raw_probabilities.get("draw"), 0.33)
    away_prob = _safe_float(raw_probabilities.get("away"), 0.33)
    
    rationale: list[str] = []
    
    if governance_status == "BLOCKED":
        return TranslationItem(
            play="scoreline",
            status=governance_status,
            confidence=round(confidence, 6),
            rationale=["governance_blocked_output"],
            evidence={
                "ft_probabilities": dict(raw_probabilities),
            },
            tags=["blocked"],
        )
    
    # Estimate expected goals
    home_xg, away_xg = estimate_expected_goals(
        home_prob, away_prob, draw_prob, home_rating, away_rating
    )
    
    # Generate score matrix
    max_goals = int(_safe_float(config.get("max_goals"), 5))
    matrix = generate_score_matrix(home_xg, away_xg, max_goals)
    
    # Filter score matrix
    min_score_prob = _safe_float(config.get("min_score_probability"), 0.02)
    max_outcomes = int(_safe_float(config.get("max_outcomes"), 20))
    filtered_matrix = filter_score_matrix(matrix, min_score_prob, max_outcomes)
    
    # Find best outcome
    best_score = max(filtered_matrix.items(), key=lambda x: x[1]) if filtered_matrix else None
    selection = score_to_selection(best_score[0][0], best_score[0][1]) if best_score else None
    best_score_prob = best_score[1] if best_score else 0.0
    
    # Apply confidence thresholds
    min_confidence = _safe_float(config.get("min_confidence"), 0.35)
    min_outcome_prob = _safe_float(config.get("min_outcome_probability"), 0.08)
    
    if best_score_prob < min_outcome_prob:
        rationale.append("score_probability_below_threshold")
        selection = None
    elif confidence < min_confidence:
        rationale.append("model_confidence_below_threshold")
        selection = None
    else:
        rationale.append("scoreline_outcome_pass")
    
    # Format outcomes for evidence
    outcomes_dict = {
        score_to_selection(score[0], score[1]): round(prob, 6)
        for score, prob in filtered_matrix.items()
    }
    
    return TranslationItem(
        play="scoreline",
        status=governance_status,
        selection=selection,
        confidence=round(confidence, 6),
        rationale=rationale,
        evidence={
            "ft_probabilities": {k: round(v, 6) for k, v in raw_probabilities.items()},
            "home_expected_goals": round(home_xg, 6),
            "away_expected_goals": round(away_xg, 6),
            "score_matrix_size": len(matrix),
            "filtered_outcomes": outcomes_dict,
            "best_score": selection,
            "best_score_probability": round(best_score_prob, 6),
        },
        tags=["scoreline_translation", "poisson_based"],
    )
