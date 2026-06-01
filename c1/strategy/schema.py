"""
Strategy Schema

Defines betting strategy, results, and performance metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BettingStrategy:
    """Betting strategy specification."""
    
    name: str
    play_type: str  # "1x2", "handicap", "totals", "htft", "scoreline"
    min_confidence: float
    min_ev: float = 0.0
    max_odds: float = 10.0
    unit_stake: float = 1.0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StrategyResult:
    """Result of a single bet under a strategy."""
    
    match_id: str
    strategy_name: str
    play_type: str
    selection: str
    odds: float
    stake: float
    predicted_confidence: float
    predicted_ev: float
    actual_outcome: str  # "WIN", "LOSS", "VOID"
    pnl: float  # Profit/Loss
    roi: float  # Return on Investment
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StrategyMetrics:
    """Performance metrics for a strategy."""
    
    strategy_name: str
    play_type: str
    sample_size: int
    
    # Basic metrics
    total_bets: int
    winning_bets: int
    losing_bets: int
    void_bets: int
    
    # Performance metrics
    hit_rate: float  # winning_bets / (winning_bets + losing_bets)
    total_stake: float
    total_pnl: float
    roi: float  # total_pnl / total_stake
    
    # Advanced metrics
    ev_per_bet: float
    sharpe_ratio: float
    max_drawdown: float
    
    # Calibration
    confidence_calibration: dict[str, float] = field(default_factory=dict)
    
    # Metadata
    period_start: str = ""
    period_end: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def build_strategy(
    *,
    name: str,
    play_type: str,
    min_confidence: float,
    min_ev: float = 0.0,
    max_odds: float = 10.0,
    unit_stake: float = 1.0,
    tags: list[str] | None = None,
) -> BettingStrategy:
    """Build a betting strategy."""
    return BettingStrategy(
        name=name,
        play_type=play_type,
        min_confidence=min_confidence,
        min_ev=min_ev,
        max_odds=max_odds,
        unit_stake=unit_stake,
        tags=tags or [],
    )
