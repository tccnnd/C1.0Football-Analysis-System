"""
Tests for Audit Store Backtest Integration

Tests recording and reading backtest results and metrics.
"""

import tempfile
from pathlib import Path

import pytest

from c1.audit import C1AuditStore


class TestAuditStoreBacktestResults:
    """Test backtest result recording."""
    
    def test_record_backtest_result(self):
        """Should record backtest result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            
            result = store.record_backtest_result(
                match_id="match_1",
                strategy_name="Test Strategy",
                play_type="1x2",
                selection="HOME_WIN",
                odds=2.0,
                stake=10.0,
                predicted_confidence=0.7,
                predicted_ev=0.1,
                actual_outcome="WIN",
                pnl=10.0,
                roi=1.0,
            )
            
            assert result["record_type"] == "backtest_result"
            assert result["match_id"] == "match_1"
            assert result["strategy_name"] == "Test Strategy"
            assert result["play_type"] == "1x2"
            assert result["selection"] == "HOME_WIN"
            assert result["odds"] == 2.0
            assert result["stake"] == 10.0
            assert result["actual_outcome"] == "WIN"
            assert result["pnl"] == 10.0
            assert result["roi"] == 1.0
    
    def test_record_multiple_backtest_results(self):
        """Should record multiple backtest results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            
            for i in range(3):
                store.record_backtest_result(
                    match_id=f"match_{i}",
                    strategy_name="Test Strategy",
                    play_type="1x2",
                    selection="HOME_WIN",
                    odds=2.0,
                    stake=10.0,
                    predicted_confidence=0.7,
                    predicted_ev=0.1,
                    actual_outcome="WIN" if i < 2 else "LOSS",
                    pnl=10.0 if i < 2 else -10.0,
                    roi=1.0 if i < 2 else -1.0,
                )
            
            results = store.read_backtest_results()
            assert len(results) == 3
    
    def test_read_backtest_results_with_limit(self):
        """Should read backtest results with limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            
            for i in range(5):
                store.record_backtest_result(
                    match_id=f"match_{i}",
                    strategy_name="Test Strategy",
                    play_type="1x2",
                    selection="HOME_WIN",
                    odds=2.0,
                    stake=10.0,
                    predicted_confidence=0.7,
                    predicted_ev=0.1,
                    actual_outcome="WIN",
                    pnl=10.0,
                    roi=1.0,
                )
            
            results = store.read_backtest_results(limit=2)
            assert len(results) == 2
    
    def test_backtest_result_with_tags_and_metadata(self):
        """Should record backtest result with tags and metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            
            result = store.record_backtest_result(
                match_id="match_1",
                strategy_name="Test Strategy",
                play_type="1x2",
                selection="HOME_WIN",
                odds=2.0,
                stake=10.0,
                predicted_confidence=0.7,
                predicted_ev=0.1,
                actual_outcome="WIN",
                pnl=10.0,
                roi=1.0,
                attribution_tags=["backtest", "test"],
                metadata={"source": "test"},
            )
            
            assert result["attribution_tags"] == ["backtest", "test"]
            assert result["metadata"]["source"] == "test"


class TestAuditStoreBacktestMetrics:
    """Test backtest metrics recording."""
    
    def test_record_backtest_metrics(self):
        """Should record backtest metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            
            metrics = store.record_backtest_metrics(
                strategy_name="Test Strategy",
                play_type="1x2",
                sample_size=100,
                total_bets=100,
                winning_bets=60,
                losing_bets=40,
                void_bets=0,
                hit_rate=0.6,
                total_stake=1000.0,
                total_pnl=200.0,
                roi=0.2,
                ev_per_bet=0.02,
                sharpe_ratio=1.5,
                max_drawdown=0.1,
            )
            
            assert metrics["record_type"] == "backtest_metrics"
            assert metrics["strategy_name"] == "Test Strategy"
            assert metrics["play_type"] == "1x2"
            assert metrics["sample_size"] == 100
            assert metrics["total_bets"] == 100
            assert metrics["winning_bets"] == 60
            assert metrics["losing_bets"] == 40
            assert metrics["hit_rate"] == 0.6
            assert metrics["roi"] == 0.2
    
    def test_record_multiple_backtest_metrics(self):
        """Should record multiple backtest metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            
            for i in range(3):
                store.record_backtest_metrics(
                    strategy_name=f"Strategy_{i}",
                    play_type="1x2",
                    sample_size=100,
                    total_bets=100,
                    winning_bets=60,
                    losing_bets=40,
                    void_bets=0,
                    hit_rate=0.6,
                    total_stake=1000.0,
                    total_pnl=200.0,
                    roi=0.2,
                    ev_per_bet=0.02,
                    sharpe_ratio=1.5,
                    max_drawdown=0.1,
                )
            
            metrics_list = store.read_backtest_metrics()
            assert len(metrics_list) == 3
    
    def test_read_backtest_metrics_with_limit(self):
        """Should read backtest metrics with limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            
            for i in range(5):
                store.record_backtest_metrics(
                    strategy_name=f"Strategy_{i}",
                    play_type="1x2",
                    sample_size=100,
                    total_bets=100,
                    winning_bets=60,
                    losing_bets=40,
                    void_bets=0,
                    hit_rate=0.6,
                    total_stake=1000.0,
                    total_pnl=200.0,
                    roi=0.2,
                    ev_per_bet=0.02,
                    sharpe_ratio=1.5,
                    max_drawdown=0.1,
                )
            
            metrics_list = store.read_backtest_metrics(limit=2)
            assert len(metrics_list) == 2
    
    def test_backtest_metrics_with_confidence_calibration(self):
        """Should record backtest metrics with confidence calibration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            
            calibration = {
                "0.0-0.3": 0.25,
                "0.3-0.5": 0.40,
                "0.5-0.7": 0.60,
                "0.7-1.0": 0.80,
            }
            
            metrics = store.record_backtest_metrics(
                strategy_name="Test Strategy",
                play_type="1x2",
                sample_size=100,
                total_bets=100,
                winning_bets=60,
                losing_bets=40,
                void_bets=0,
                hit_rate=0.6,
                total_stake=1000.0,
                total_pnl=200.0,
                roi=0.2,
                ev_per_bet=0.02,
                sharpe_ratio=1.5,
                max_drawdown=0.1,
                confidence_calibration=calibration,
            )
            
            assert metrics["confidence_calibration"] == calibration
    
    def test_backtest_metrics_with_tags_and_metadata(self):
        """Should record backtest metrics with tags and metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            
            metrics = store.record_backtest_metrics(
                strategy_name="Test Strategy",
                play_type="1x2",
                sample_size=100,
                total_bets=100,
                winning_bets=60,
                losing_bets=40,
                void_bets=0,
                hit_rate=0.6,
                total_stake=1000.0,
                total_pnl=200.0,
                roi=0.2,
                ev_per_bet=0.02,
                sharpe_ratio=1.5,
                max_drawdown=0.1,
                attribution_tags=["backtest", "metrics"],
                metadata={"period": "2026-05-01 to 2026-05-31"},
            )
            
            assert metrics["attribution_tags"] == ["backtest", "metrics"]
            assert metrics["metadata"]["period"] == "2026-05-01 to 2026-05-31"


class TestAuditStoreBacktestIntegration:
    """Test backtest integration with audit store."""
    
    def test_record_and_read_backtest_results(self):
        """Should record and read backtest results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            
            # Record results
            for i in range(3):
                store.record_backtest_result(
                    match_id=f"match_{i}",
                    strategy_name="Test Strategy",
                    play_type="1x2",
                    selection="HOME_WIN",
                    odds=2.0,
                    stake=10.0,
                    predicted_confidence=0.7,
                    predicted_ev=0.1,
                    actual_outcome="WIN" if i < 2 else "LOSS",
                    pnl=10.0 if i < 2 else -10.0,
                    roi=1.0 if i < 2 else -1.0,
                )
            
            # Read results
            results = store.read_backtest_results()
            
            assert len(results) == 3
            assert results[0]["match_id"] == "match_0"
            assert results[1]["match_id"] == "match_1"
            assert results[2]["match_id"] == "match_2"
            assert results[2]["actual_outcome"] == "LOSS"
    
    def test_record_and_read_backtest_metrics(self):
        """Should record and read backtest metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            
            # Record metrics
            for i in range(2):
                store.record_backtest_metrics(
                    strategy_name=f"Strategy_{i}",
                    play_type="1x2",
                    sample_size=100,
                    total_bets=100,
                    winning_bets=60,
                    losing_bets=40,
                    void_bets=0,
                    hit_rate=0.6,
                    total_stake=1000.0,
                    total_pnl=200.0,
                    roi=0.2,
                    ev_per_bet=0.02,
                    sharpe_ratio=1.5,
                    max_drawdown=0.1,
                )
            
            # Read metrics
            metrics_list = store.read_backtest_metrics()
            
            assert len(metrics_list) == 2
            assert metrics_list[0]["strategy_name"] == "Strategy_0"
            assert metrics_list[1]["strategy_name"] == "Strategy_1"
    
    def test_backtest_results_and_metrics_separate(self):
        """Should keep backtest results and metrics separate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            
            # Record results
            store.record_backtest_result(
                match_id="match_1",
                strategy_name="Test Strategy",
                play_type="1x2",
                selection="HOME_WIN",
                odds=2.0,
                stake=10.0,
                predicted_confidence=0.7,
                predicted_ev=0.1,
                actual_outcome="WIN",
                pnl=10.0,
                roi=1.0,
            )
            
            # Record metrics
            store.record_backtest_metrics(
                strategy_name="Test Strategy",
                play_type="1x2",
                sample_size=100,
                total_bets=100,
                winning_bets=60,
                losing_bets=40,
                void_bets=0,
                hit_rate=0.6,
                total_stake=1000.0,
                total_pnl=200.0,
                roi=0.2,
                ev_per_bet=0.02,
                sharpe_ratio=1.5,
                max_drawdown=0.1,
            )
            
            # Read both
            results = store.read_backtest_results()
            metrics_list = store.read_backtest_metrics()
            
            assert len(results) == 1
            assert len(metrics_list) == 1
            assert results[0]["record_type"] == "backtest_result"
            assert metrics_list[0]["record_type"] == "backtest_metrics"
