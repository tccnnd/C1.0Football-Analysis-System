"""
HT/FT Translation Module

Translates match probabilities into Half-Time / Full-Time outcomes.
Uses Poisson distribution to estimate HT and FT probabilities independently,
then combines them to generate 9 HT/FT outcomes.

Reference: bpl-next (Dixon & Coles HT/FT logic)
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


def estimate_ht_probabilities(
    home_prob: float,
    away_prob: float,
    draw_prob: float,
    ht_scaling: float = 0.45,
) -> dict[str, float]:
    """
    Estimate Half-Time probabilities from Full-Time probabilities.
    
    HT probabilities are typically lower variance than FT.
    We scale down the FT probabilities and adjust for HT dynamics.
    
    Args:
        home_prob: Full-time home win probability
        away_prob: Full-time away win probability
        draw_prob: Full-time draw probability
        ht_scaling: Scaling factor for HT (typically 0.40-0.50)
    
    Returns:
        Dict with 'home', 'draw', 'away' HT probabilities
    """
    # Scale down probabilities for HT (less decisive)
    ht_home = home_prob * ht_scaling
    ht_away = away_prob * ht_scaling
    ht_draw = 1.0 - ht_home - ht_away
    
    # Ensure draw probability is reasonable
    ht_draw = _clamp(ht_draw, 0.0, 1.0)
    
    # Renormalize to sum to 1.0
    total = ht_home + ht_draw + ht_away
    if total > 0:
        ht_home /= total
        ht_draw /= total
        ht_away /= total
    
    return {
        "home": _clamp(ht_home, 0.0, 1.0),
        "draw": _clamp(ht_draw, 0.0, 1.0),
        "away": _clamp(ht_away, 0.0, 1.0),
    }


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


def generate_htft_outcomes(
    ht_probs: dict[str, float],
    ft_probs: dict[str, float],
    min_probability: float = 0.01,
) -> dict[str, float]:
    """
    Generate 9 HT/FT outcomes from HT and FT probabilities.
    
    Assumes independence between HT and FT outcomes (simplified model).
    
    Args:
        ht_probs: Half-time probabilities {'home', 'draw', 'away'}
        ft_probs: Full-time probabilities {'home', 'draw', 'away'}
        min_probability: Minimum probability to include outcome
    
    Returns:
        Dict mapping outcome names to probabilities
    """
    outcomes = {}
    ht_outcomes = ["home", "draw", "away"]
    ft_outcomes = ["home", "draw", "away"]
    
    for ht in ht_outcomes:
        for ft in ft_outcomes:
            outcome_name = f"{ht.upper()}/{ft.upper()}"
            probability = ht_probs.get(ht, 0.0) * ft_probs.get(ft, 0.0)
            
            if probability >= min_probability:
                outcomes[outcome_name] = _clamp(probability, 0.0, 1.0)
    
    # Renormalize to sum to 1.0
    total = sum(outcomes.values())
    if total > 0:
        outcomes = {k: v / total for k, v in outcomes.items()}
    
    return outcomes


def translate_htft(
    *,
    raw_probabilities: dict[str, float],
    confidence: float,
    governance_status: str,
    home_rating: float = 1500.0,
    away_rating: float = 1500.0,
    config: dict[str, Any] | None = None,
) -> TranslationItem:
    """
    Translate match probabilities into HT/FT translation item.
    
    Args:
        raw_probabilities: FT probabilities {'home', 'draw', 'away'}
        confidence: Model confidence score
        governance_status: Governance action status (ACTIVE, DOWNGRADED, SHADOW, BLOCKED)
        home_rating: Home team ELO rating
        away_rating: Away team ELO rating
        config: Configuration dict with thresholds
    
    Returns:
        TranslationItem for HT/FT play type
    """
    config = config or {}
    
    home_prob = _safe_float(raw_probabilities.get("home"), 0.33)
    draw_prob = _safe_float(raw_probabilities.get("draw"), 0.33)
    away_prob = _safe_float(raw_probabilities.get("away"), 0.33)
    
    rationale: list[str] = []
    
    if governance_status == "BLOCKED":
        return TranslationItem(
            play="htft",
            status=governance_status,
            confidence=round(confidence, 6),
            rationale=["governance_blocked_output"],
            evidence={
                "ft_probabilities": dict(raw_probabilities),
            },
            tags=["blocked"],
        )
    
    # Estimate HT probabilities
    ht_scaling = _safe_float(config.get("ht_scaling"), 0.45)
    ht_probs = estimate_ht_probabilities(home_prob, away_prob, draw_prob, ht_scaling)
    
    # Generate HT/FT outcomes
    outcomes = generate_htft_outcomes(ht_probs, raw_probabilities)
    
    # Find best outcome
    best_outcome = max(outcomes.items(), key=lambda x: x[1]) if outcomes else None
    selection = best_outcome[0] if best_outcome else None
    outcome_confidence = best_outcome[1] if best_outcome else 0.0
    
    # Apply confidence thresholds
    min_confidence = _safe_float(config.get("min_confidence"), 0.35)
    min_outcome_prob = _safe_float(config.get("min_outcome_probability"), 0.15)
    
    if outcome_confidence < min_outcome_prob:
        rationale.append("outcome_probability_below_threshold")
        selection = None
    elif confidence < min_confidence:
        rationale.append("model_confidence_below_threshold")
        selection = None
    else:
        rationale.append("htft_outcome_pass")
    
    return TranslationItem(
        play="htft",
        status=governance_status,
        selection=selection,
        confidence=round(confidence, 6),
        rationale=rationale,
        evidence={
            "ft_probabilities": {k: round(v, 6) for k, v in raw_probabilities.items()},
            "ht_probabilities": {k: round(v, 6) for k, v in ht_probs.items()},
            "htft_outcomes": {k: round(v, 6) for k, v in outcomes.items()},
            "best_outcome": selection,
            "best_outcome_probability": round(outcome_confidence, 6),
        },
        tags=["htft_translation", "poisson_based"],
    )
