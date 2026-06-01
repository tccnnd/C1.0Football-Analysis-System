"""
Backtest Engine

Evaluates betting strategies against historical data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from c1.strategy.schema import BettingStrategy, StrategyResult, StrategyMetrics


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _calculate_sharpe_ratio(returns: list[float], risk_free_rate: float = 0.02) -> float:
    """Calculate Sharpe ratio from returns."""
    if len(returns) < 2:
        return 0.0
    
    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    std_dev = math.sqrt(variance)
    
    if std_dev == 0:
        return 0.0
    
    return (mean_return - risk_free_rate) / std_dev


def _calculate_max_drawdown(returns: list[float]) -> float:
    """Calculate maximum drawdown from returns."""
    if not returns:
        return 0.0
    
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    
    for ret in returns:
        cumulative += ret
        if cumulative > peak:
            peak = cumulative
        drawdown = peak - cumulative
        if drawdown > max_dd:
            max_dd = drawdown
    
    return max_dd


def _calculate_confidence_calibration(results: list[StrategyResult]) -> dict[str, float]:
    """Calculate confidence calibration metrics."""
    if not results:
        return {}
    
    # Group by confidence bins
    bins = {
        "0.0-0.2": [],
        "0.2-0.4": [],
        "0.4-0.6": [],
        "0.6-0.8": [],
        "0.8-1.0": [],
    }
    
    for result in results:
        conf = result.predicted_confidence
        if conf < 0.2:
            bins["0.0-0.2"].append(result)
        elif conf < 0.4:
            bins["0.2-0.4"].append(result)
        elif conf < 0.6:
            bins["0.4-0.6"].append(result)
        elif conf < 0.8:
            bins["0.6-0.8"].append(result)
        else:
            bins["0.8-1.0"].append(result)
    
    calibration = {}
    for bin_name, bin_results in bins.items():
        if not bin_results:
            continue
        
        wins = sum(1 for r in bin_results if r.actual_outcome == "WIN")
        total = len(bin_results)
        actual_rate = wins / total if total > 0 else 0.0
        
        calibration[bin_name] = round(actual_rate, 4)
    
    return calibration


@dataclass(slots=True)
class BacktestConfig:
    """Backtest configuration."""
    
    strategy: BettingStrategy
    min_odds: float = 1.01
    max_odds: float = 100.0
    risk_free_rate: float = 0.02


class BacktestRunner:
    """Runs backtest on historical data."""
    
    def __init__(self, config: BacktestConfig) -> None:
        self.config = config
        self.results: list[StrategyResult] = []
    
    def add_result(self, result: StrategyResult) -> None:
        """Add a backtest result."""
        self.results.append(result)
    
    def add_results(self, results: list[StrategyResult]) -> None:
        """Add multiple backtest results."""
        self.results.extend(results)
    
    def calculate_metrics(self) -> StrategyMetrics:
        """Calculate performance metrics."""
        if not self.results:
            return StrategyMetrics(
                strategy_name=self.config.strategy.name,
                play_type=self.config.strategy.play_type,
                sample_size=0,
                total_bets=0,
                winning_bets=0,
                losing_bets=0,
                void_bets=0,
                hit_rate=0.0,
                total_stake=0.0,
                total_pnl=0.0,
                roi=0.0,
                ev_per_bet=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
            )
        
        # Count outcomes
        winning_bets = sum(1 for r in self.results if r.actual_outcome == "WIN")
        losing_bets = sum(1 for r in self.results if r.actual_outcome == "LOSS")
        void_bets = sum(1 for r in self.results if r.actual_outcome == "VOID")
        total_bets = len(self.results)
        
        # Calculate basic metrics
        hit_rate = winning_bets / (winning_bets + losing_bets) if (winning_bets + losing_bets) > 0 else 0.0
        total_stake = sum(r.stake for r in self.results)
        total_pnl = sum(r.pnl for r in self.results)
        roi = total_pnl / total_stake if total_stake > 0 else 0.0
        
        # Calculate advanced metrics
        ev_per_bet = sum(r.predicted_ev * r.stake for r in self.results) / total_stake if total_stake > 0 else 0.0
        
        # Calculate Sharpe ratio
        returns = [r.roi for r in self.results]
        sharpe_ratio = _calculate_sharpe_ratio(returns, self.config.risk_free_rate)
        
        # Calculate max drawdown
        max_drawdown = _calculate_max_drawdown(returns)
        
        # Calculate confidence calibration
        confidence_calibration = _calculate_confidence_calibration(self.results)
        
        return StrategyMetrics(
            strategy_name=self.config.strategy.name,
            play_type=self.config.strategy.play_type,
            sample_size=total_bets,
            total_bets=total_bets,
            winning_bets=winning_bets,
            losing_bets=losing_bets,
            void_bets=void_bets,
            hit_rate=round(hit_rate, 4),
            total_stake=round(total_stake, 2),
            total_pnl=round(total_pnl, 2),
            roi=round(roi, 4),
            ev_per_bet=round(ev_per_bet, 4),
            sharpe_ratio=round(sharpe_ratio, 4),
            max_drawdown=round(max_drawdown, 4),
            confidence_calibration=confidence_calibration,
        )
    
    def filter_by_strategy(self) -> list[StrategyResult]:
        """Filter results by strategy criteria."""
        filtered = []
        
        for result in self.results:
            # Check play type
            if result.play_type != self.config.strategy.play_type:
                continue
            
            # Check confidence
            if result.predicted_confidence < self.config.strategy.min_confidence:
                continue
            
            # Check EV
            if result.predicted_ev < self.config.strategy.min_ev:
                continue
            
            # Check odds
            if result.odds < self.config.min_odds or result.odds > self.config.max_odds:
                continue
            
            filtered.append(result)
        
        return filtered
    
    def get_summary(self) -> dict[str, Any]:
        """Get summary of backtest results."""
        metrics = self.calculate_metrics()
        
        return {
            "strategy_name": metrics.strategy_name,
            "play_type": metrics.play_type,
            "sample_size": metrics.sample_size,
            "total_bets": metrics.total_bets,
            "winning_bets": metrics.winning_bets,
            "losing_bets": metrics.losing_bets,
            "void_bets": metrics.void_bets,
            "hit_rate": metrics.hit_rate,
            "total_stake": metrics.total_stake,
            "total_pnl": metrics.total_pnl,
            "roi": metrics.roi,
            "ev_per_bet": metrics.ev_per_bet,
            "sharpe_ratio": metrics.sharpe_ratio,
            "max_drawdown": metrics.max_drawdown,
            "confidence_calibration": metrics.confidence_calibration,
        }
