"""
C1.0 Strategy Module

Provides strategy definition, backtesting, and performance analysis.
"""

from .schema import (
    BettingStrategy,
    StrategyResult,
    StrategyMetrics,
)
from .backtest import BacktestRunner, BacktestConfig

__all__ = [
    "BettingStrategy",
    "StrategyResult",
    "StrategyMetrics",
    "BacktestRunner",
    "BacktestConfig",
]
