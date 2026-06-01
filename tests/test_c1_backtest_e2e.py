"""
End-to-End Backtest Test

Tests the complete backtest pipeline combining settlement bridge with backtest runner.
"""

import tempfile

import pytest

from c1.audit import C1AuditStore
from c1.strategy.backtest import BacktestRunner, BacktestConfig
from c1.strategy.schema import build_strategy, StrategyResult
from c1.strategy.settlement_bridge import SettlementBridge


class TestBacktestE2E:
    """End-to-end backtest tests."""
    
    def test_backtest_e2e_single_match(self):
        """Should run complete backtest for single match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            bridge = SettlementBridge(tmpdir)
            
            # Create strategy
            strategy = build_strategy(
                name="Test Strategy",
                play_type="1x2",
                min_confidence=0.6,
            )
            
            # Create config and runner
            config = BacktestConfig(strategy=strategy)
            runner = BacktestRunner(config)
            
            # Create settlement
            settlement = {"home_goals": 2, "away_goals": 1}
            
            # Compute outcome
            outcome = bridge.compute_outcome(settlement, "HOME_WIN", "1x2")
            assert outcome == "WIN"
            
            # Add result to backtest
            result = StrategyResult(
                match_id="match_1",
                strategy_name=strategy.name,
                play_type=strategy.play_type,
                selection="HOME_WIN",
                odds=2.0,
                stake=10.0,
                predicted_confidence=0.7,
                predicted_ev=0.1,
                actual_outcome=outcome,
                pnl=10.0,
                roi=1.0,
            )
            runner.add_result(result)
            
            # Calculate metrics
            metrics = runner.calculate_metrics()
            
            # Verify
            assert metrics.total_bets == 1
            assert metrics.winning_bets == 1
            assert metrics.hit_rate == 1.0
            assert metrics.total_pnl == 10.0
            
            # Record in audit store
            store.record_backtest_result(
                match_id="match_1",
                strategy_name=strategy.name,
                play_type=strategy.play_type,
                selection="HOME_WIN",
                odds=2.0,
                stake=10.0,
                predicted_confidence=0.7,
                predicted_ev=0.1,
                actual_outcome=outcome,
                pnl=10.0,
                roi=1.0,
            )
            
            # Verify audit record
            results = store.read_backtest_results()
            assert len(results) == 1
            assert results[0]["actual_outcome"] == "WIN"
    
    def test_backtest_e2e_multiple_matches(self):
        """Should run complete backtest for multiple matches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            bridge = SettlementBridge(tmpdir)
            
            # Create strategy
            strategy = build_strategy(
                name="Test Strategy",
                play_type="1x2",
                min_confidence=0.6,
            )
            
            # Create config and runner
            config = BacktestConfig(strategy=strategy)
            runner = BacktestRunner(config)
            
            # Test data
            test_cases = [
                {"settlement": {"home_goals": 2, "away_goals": 1}, "selection": "HOME_WIN", "expected": "WIN"},
                {"settlement": {"home_goals": 1, "away_goals": 1}, "selection": "DRAW", "expected": "WIN"},
                {"settlement": {"home_goals": 1, "away_goals": 2}, "selection": "AWAY_WIN", "expected": "WIN"},
                {"settlement": {"home_goals": 2, "away_goals": 1}, "selection": "AWAY_WIN", "expected": "LOSS"},
            ]
            
            # Process each match
            for i, test_case in enumerate(test_cases):
                settlement = test_case["settlement"]
                selection = test_case["selection"]
                expected_outcome = test_case["expected"]
                
                # Compute outcome
                outcome = bridge.compute_outcome(settlement, selection, "1x2")
                assert outcome == expected_outcome
                
                # Add to backtest
                pnl = 10.0 if outcome == "WIN" else -10.0
                roi = 1.0 if outcome == "WIN" else -1.0
                
                result = StrategyResult(
                    match_id=f"match_{i}",
                    strategy_name=strategy.name,
                    play_type=strategy.play_type,
                    selection=selection,
                    odds=2.0,
                    stake=10.0,
                    predicted_confidence=0.7,
                    predicted_ev=0.1,
                    actual_outcome=outcome,
                    pnl=pnl,
                    roi=roi,
                )
                runner.add_result(result)
                
                # Record in audit store
                store.record_backtest_result(
                    match_id=f"match_{i}",
                    strategy_name=strategy.name,
                    play_type=strategy.play_type,
                    selection=selection,
                    odds=2.0,
                    stake=10.0,
                    predicted_confidence=0.7,
                    predicted_ev=0.1,
                    actual_outcome=outcome,
                    pnl=pnl,
                    roi=roi,
                )
            
            # Calculate metrics
            metrics = runner.calculate_metrics()
            
            # Verify
            assert metrics.total_bets == 4
            assert metrics.winning_bets == 3
            assert metrics.losing_bets == 1
            assert abs(metrics.hit_rate - 0.75) < 0.01
            assert metrics.total_pnl == 20.0
            
            # Verify audit records
            results = store.read_backtest_results()
            assert len(results) == 4
    
    def test_backtest_e2e_all_play_types(self):
        """Should support all 5 play types in backtest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            bridge = SettlementBridge(tmpdir)
            
            # Test all play types
            play_types = [
                ("1x2", "HOME_WIN", {"home_goals": 2, "away_goals": 1}),
                ("handicap", "HOME_HANDICAP", {"home_goals": 2, "away_goals": 1}),
                ("totals", "OVER", {"home_goals": 2, "away_goals": 2}),
                ("htft", "HOME/HOME", {"ht_home_goals": 1, "ht_away_goals": 0, "home_goals": 2, "away_goals": 0}),
                ("scoreline", "2-1", {"home_goals": 2, "away_goals": 1}),
            ]
            
            # Process each play type
            for play_type, selection, settlement in play_types:
                # Compute outcome
                outcome = bridge.compute_outcome(settlement, selection, play_type)
                assert outcome == "WIN"
    
    def test_backtest_e2e_with_metrics_recording(self):
        """Should record backtest metrics in audit store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            bridge = SettlementBridge(tmpdir)
            
            # Create strategy
            strategy = build_strategy(
                name="Test Strategy",
                play_type="1x2",
                min_confidence=0.6,
            )
            
            # Create config and runner
            config = BacktestConfig(strategy=strategy)
            runner = BacktestRunner(config)
            
            # Add multiple results
            for i in range(10):
                settlement = {"home_goals": 2, "away_goals": 1}
                outcome = bridge.compute_outcome(settlement, "HOME_WIN", "1x2")
                
                result = StrategyResult(
                    match_id=f"match_{i}",
                    strategy_name=strategy.name,
                    play_type=strategy.play_type,
                    selection="HOME_WIN",
                    odds=2.0,
                    stake=10.0,
                    predicted_confidence=0.7,
                    predicted_ev=0.1,
                    actual_outcome=outcome,
                    pnl=10.0,
                    roi=1.0,
                )
                runner.add_result(result)
            
            # Calculate metrics
            metrics = runner.calculate_metrics()
            
            # Record metrics in audit store
            store.record_backtest_metrics(
                strategy_name=strategy.name,
                play_type=strategy.play_type,
                sample_size=metrics.sample_size,
                total_bets=metrics.total_bets,
                winning_bets=metrics.winning_bets,
                losing_bets=metrics.losing_bets,
                void_bets=metrics.void_bets,
                hit_rate=metrics.hit_rate,
                total_stake=metrics.total_stake,
                total_pnl=metrics.total_pnl,
                roi=metrics.roi,
                ev_per_bet=metrics.ev_per_bet,
                sharpe_ratio=metrics.sharpe_ratio,
                max_drawdown=metrics.max_drawdown,
                confidence_calibration=metrics.confidence_calibration,
            )
            
            # Verify audit record
            metrics_list = store.read_backtest_metrics()
            assert len(metrics_list) == 1
            assert metrics_list[0]["total_bets"] == 10
            assert metrics_list[0]["winning_bets"] == 10
            assert metrics_list[0]["hit_rate"] == 1.0
    
    def test_backtest_e2e_mixed_outcomes(self):
        """Should handle mixed win/loss outcomes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            bridge = SettlementBridge(tmpdir)
            
            # Create strategy
            strategy = build_strategy(
                name="Test Strategy",
                play_type="1x2",
                min_confidence=0.6,
            )
            
            # Create config and runner
            config = BacktestConfig(strategy=strategy)
            runner = BacktestRunner(config)
            
            # Test cases with mixed outcomes
            test_cases = [
                {"settlement": {"home_goals": 2, "away_goals": 1}, "selection": "HOME_WIN", "expected": "WIN"},
                {"settlement": {"home_goals": 1, "away_goals": 2}, "selection": "HOME_WIN", "expected": "LOSS"},
                {"settlement": {"home_goals": 2, "away_goals": 1}, "selection": "HOME_WIN", "expected": "WIN"},
                {"settlement": {"home_goals": 1, "away_goals": 2}, "selection": "HOME_WIN", "expected": "LOSS"},
                {"settlement": {"home_goals": 2, "away_goals": 1}, "selection": "HOME_WIN", "expected": "WIN"},
            ]
            
            # Process each match
            for i, test_case in enumerate(test_cases):
                settlement = test_case["settlement"]
                selection = test_case["selection"]
                expected_outcome = test_case["expected"]
                
                # Compute outcome
                outcome = bridge.compute_outcome(settlement, selection, "1x2")
                assert outcome == expected_outcome
                
                # Add to backtest
                pnl = 10.0 if outcome == "WIN" else -10.0
                roi = 1.0 if outcome == "WIN" else -1.0
                
                result = StrategyResult(
                    match_id=f"match_{i}",
                    strategy_name="Test Strategy",
                    play_type="1x2",
                    selection=selection,
                    odds=2.0,
                    stake=10.0,
                    predicted_confidence=0.7,
                    predicted_ev=0.1,
                    actual_outcome=outcome,
                    pnl=pnl,
                    roi=roi,
                )
                runner.add_result(result)
                
                # Record in audit store
                store.record_backtest_result(
                    match_id=f"match_{i}",
                    strategy_name="Test Strategy",
                    play_type="1x2",
                    selection=selection,
                    odds=2.0,
                    stake=10.0,
                    predicted_confidence=0.7,
                    predicted_ev=0.1,
                    actual_outcome=outcome,
                    pnl=pnl,
                    roi=roi,
                )
            
            # Calculate metrics
            metrics = runner.calculate_metrics()
            
            # Verify
            assert metrics.total_bets == 5
            assert metrics.winning_bets == 3
            assert metrics.losing_bets == 2
            assert abs(metrics.hit_rate - 0.6) < 0.01
            assert metrics.total_pnl == 10.0
            
            # Verify audit records
            results = store.read_backtest_results()
            assert len(results) == 5
            
            # Verify summary
            summary = runner.get_summary()
            assert summary["total_bets"] == 5
            assert summary["winning_bets"] == 3
            assert summary["losing_bets"] == 2
