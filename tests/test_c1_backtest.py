"""
Unit tests for backtest engine.
"""

from c1.strategy.schema import BettingStrategy, StrategyResult, build_strategy
from c1.strategy.backtest import BacktestRunner, BacktestConfig


class TestBettingStrategy:
    """Test betting strategy definition."""
    
    def test_build_strategy(self):
        """Should build strategy correctly."""
        strategy = build_strategy(
            name="Conservative 1X2",
            play_type="1x2",
            min_confidence=0.60,
            min_ev=0.05,
            unit_stake=10.0,
        )
        
        assert strategy.name == "Conservative 1X2"
        assert strategy.play_type == "1x2"
        assert strategy.min_confidence == 0.60
        assert strategy.min_ev == 0.05
        assert strategy.unit_stake == 10.0
    
    def test_strategy_defaults(self):
        """Strategy should have sensible defaults."""
        strategy = build_strategy(
            name="Test",
            play_type="1x2",
            min_confidence=0.50,
        )
        
        assert strategy.min_ev == 0.0
        assert strategy.max_odds == 10.0
        assert strategy.unit_stake == 1.0


class TestStrategyResult:
    """Test strategy result."""
    
    def test_create_result(self):
        """Should create result correctly."""
        result = StrategyResult(
            match_id="match_001",
            strategy_name="Test Strategy",
            play_type="1x2",
            selection="HOME_WIN",
            odds=2.50,
            stake=10.0,
            predicted_confidence=0.65,
            predicted_ev=0.15,
            actual_outcome="WIN",
            pnl=15.0,
            roi=1.5,
        )
        
        assert result.match_id == "match_001"
        assert result.actual_outcome == "WIN"
        assert result.pnl == 15.0


class TestBacktestRunner:
    """Test backtest runner."""
    
    def test_add_single_result(self):
        """Should add single result."""
        strategy = build_strategy(
            name="Test",
            play_type="1x2",
            min_confidence=0.50,
        )
        config = BacktestConfig(strategy=strategy)
        runner = BacktestRunner(config)
        
        result = StrategyResult(
            match_id="match_001",
            strategy_name="Test",
            play_type="1x2",
            selection="HOME_WIN",
            odds=2.50,
            stake=10.0,
            predicted_confidence=0.65,
            predicted_ev=0.15,
            actual_outcome="WIN",
            pnl=15.0,
            roi=1.5,
        )
        
        runner.add_result(result)
        assert len(runner.results) == 1
    
    def test_add_multiple_results(self):
        """Should add multiple results."""
        strategy = build_strategy(
            name="Test",
            play_type="1x2",
            min_confidence=0.50,
        )
        config = BacktestConfig(strategy=strategy)
        runner = BacktestRunner(config)
        
        results = [
            StrategyResult(
                match_id=f"match_{i:03d}",
                strategy_name="Test",
                play_type="1x2",
                selection="HOME_WIN",
                odds=2.50,
                stake=10.0,
                predicted_confidence=0.65,
                predicted_ev=0.15,
                actual_outcome="WIN" if i % 2 == 0 else "LOSS",
                pnl=15.0 if i % 2 == 0 else -10.0,
                roi=1.5 if i % 2 == 0 else -1.0,
            )
            for i in range(10)
        ]
        
        runner.add_results(results)
        assert len(runner.results) == 10
    
    def test_calculate_metrics_empty(self):
        """Should handle empty results."""
        strategy = build_strategy(
            name="Test",
            play_type="1x2",
            min_confidence=0.50,
        )
        config = BacktestConfig(strategy=strategy)
        runner = BacktestRunner(config)
        
        metrics = runner.calculate_metrics()
        assert metrics.sample_size == 0
        assert metrics.total_bets == 0
        assert metrics.hit_rate == 0.0
    
    def test_calculate_metrics_single_win(self):
        """Should calculate metrics for single win."""
        strategy = build_strategy(
            name="Test",
            play_type="1x2",
            min_confidence=0.50,
        )
        config = BacktestConfig(strategy=strategy)
        runner = BacktestRunner(config)
        
        result = StrategyResult(
            match_id="match_001",
            strategy_name="Test",
            play_type="1x2",
            selection="HOME_WIN",
            odds=2.50,
            stake=10.0,
            predicted_confidence=0.65,
            predicted_ev=0.15,
            actual_outcome="WIN",
            pnl=15.0,
            roi=1.5,
        )
        
        runner.add_result(result)
        metrics = runner.calculate_metrics()
        
        assert metrics.total_bets == 1
        assert metrics.winning_bets == 1
        assert metrics.losing_bets == 0
        assert metrics.hit_rate == 1.0
        assert metrics.total_stake == 10.0
        assert metrics.total_pnl == 15.0
        assert metrics.roi == 1.5
    
    def test_calculate_metrics_mixed_results(self):
        """Should calculate metrics for mixed results."""
        strategy = build_strategy(
            name="Test",
            play_type="1x2",
            min_confidence=0.50,
        )
        config = BacktestConfig(strategy=strategy)
        runner = BacktestRunner(config)
        
        results = [
            StrategyResult(
                match_id="match_001",
                strategy_name="Test",
                play_type="1x2",
                selection="HOME_WIN",
                odds=2.50,
                stake=10.0,
                predicted_confidence=0.65,
                predicted_ev=0.15,
                actual_outcome="WIN",
                pnl=15.0,
                roi=1.5,
            ),
            StrategyResult(
                match_id="match_002",
                strategy_name="Test",
                play_type="1x2",
                selection="AWAY_WIN",
                odds=3.00,
                stake=10.0,
                predicted_confidence=0.55,
                predicted_ev=0.10,
                actual_outcome="LOSS",
                pnl=-10.0,
                roi=-1.0,
            ),
            StrategyResult(
                match_id="match_003",
                strategy_name="Test",
                play_type="1x2",
                selection="DRAW",
                odds=3.50,
                stake=10.0,
                predicted_confidence=0.50,
                predicted_ev=0.05,
                actual_outcome="WIN",
                pnl=25.0,
                roi=2.5,
            ),
        ]
        
        runner.add_results(results)
        metrics = runner.calculate_metrics()
        
        assert metrics.total_bets == 3
        assert metrics.winning_bets == 2
        assert metrics.losing_bets == 1
        assert abs(metrics.hit_rate - (2.0 / 3.0)) < 0.0001
        assert metrics.total_stake == 30.0
        assert metrics.total_pnl == 30.0
        assert metrics.roi == 1.0
    
    def test_filter_by_strategy(self):
        """Should filter results by strategy criteria."""
        strategy = build_strategy(
            name="Conservative",
            play_type="1x2",
            min_confidence=0.60,
            min_ev=0.10,
        )
        config = BacktestConfig(strategy=strategy)
        runner = BacktestRunner(config)
        
        results = [
            StrategyResult(
                match_id="match_001",
                strategy_name="Conservative",
                play_type="1x2",
                selection="HOME_WIN",
                odds=2.50,
                stake=10.0,
                predicted_confidence=0.70,  # >= 0.60
                predicted_ev=0.15,  # >= 0.10
                actual_outcome="WIN",
                pnl=15.0,
                roi=1.5,
            ),
            StrategyResult(
                match_id="match_002",
                strategy_name="Conservative",
                play_type="1x2",
                selection="AWAY_WIN",
                odds=3.00,
                stake=10.0,
                predicted_confidence=0.50,  # < 0.60
                predicted_ev=0.10,  # >= 0.10
                actual_outcome="LOSS",
                pnl=-10.0,
                roi=-1.0,
            ),
            StrategyResult(
                match_id="match_003",
                strategy_name="Conservative",
                play_type="1x2",
                selection="DRAW",
                odds=3.50,
                stake=10.0,
                predicted_confidence=0.65,  # >= 0.60
                predicted_ev=0.05,  # < 0.10
                actual_outcome="WIN",
                pnl=25.0,
                roi=2.5,
            ),
        ]
        
        runner.add_results(results)
        filtered = runner.filter_by_strategy()
        
        # Only match_001 should pass both criteria
        assert len(filtered) == 1
        assert filtered[0].match_id == "match_001"
    
    def test_get_summary(self):
        """Should generate summary."""
        strategy = build_strategy(
            name="Test",
            play_type="1x2",
            min_confidence=0.50,
        )
        config = BacktestConfig(strategy=strategy)
        runner = BacktestRunner(config)
        
        result = StrategyResult(
            match_id="match_001",
            strategy_name="Test",
            play_type="1x2",
            selection="HOME_WIN",
            odds=2.50,
            stake=10.0,
            predicted_confidence=0.65,
            predicted_ev=0.15,
            actual_outcome="WIN",
            pnl=15.0,
            roi=1.5,
        )
        
        runner.add_result(result)
        summary = runner.get_summary()
        
        assert summary["strategy_name"] == "Test"
        assert summary["play_type"] == "1x2"
        assert summary["sample_size"] == 1
        assert summary["total_bets"] == 1
        assert summary["winning_bets"] == 1
        assert summary["hit_rate"] == 1.0
        assert summary["roi"] == 1.5


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
