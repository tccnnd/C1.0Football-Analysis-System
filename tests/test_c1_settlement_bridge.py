"""
Tests for Settlement Bridge

Maps V24 settlements to C1 matches and computes actual outcomes.
"""

import json
import tempfile
from pathlib import Path

import pytest

from c1.strategy.settlement_bridge import SettlementBridge


class TestSettlementBridgeLoading:
    """Test settlement loading."""
    
    def test_load_settlements_empty(self):
        """Should handle missing settlement file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = SettlementBridge(tmpdir)
            count = bridge.load_settlements()
            assert count == 0
    
    def test_load_settlements_with_data(self):
        """Should load settlements from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create settlement file
            state_dir = Path(tmpdir) / "data" / "state"
            state_dir.mkdir(parents=True)
            
            settlements = {
                "1": {"home_goals": 2, "away_goals": 1},
                "2": {"home_goals": 1, "away_goals": 1},
            }
            
            settlement_file = state_dir / "settlements.json"
            settlement_file.write_text(json.dumps({"settlements": settlements}))
            
            bridge = SettlementBridge(tmpdir)
            count = bridge.load_settlements()
            
            assert count == 2
            assert bridge.settlements == settlements


class TestSettlementBridgeMapping:
    """Test match ID mapping."""
    
    def test_build_match_id_map_empty(self):
        """Should handle empty matches list."""
        bridge = SettlementBridge(".")
        count = bridge.build_match_id_map([])
        assert count == 0
    
    def test_build_match_id_map_with_matches(self):
        """Should build mapping from matches."""
        bridge = SettlementBridge(".")
        
        matches = [
            {"source_id": "1", "match_id": "match_1"},
            {"source_id": "2", "match_id": "match_2"},
        ]
        
        count = bridge.build_match_id_map(matches)
        
        assert count == 2
        assert bridge.match_id_map["1"] == "match_1"
        assert bridge.match_id_map["2"] == "match_2"


class TestSettlementBridgeRetrieval:
    """Test settlement retrieval."""
    
    def test_get_settlement_not_found(self):
        """Should return None if settlement not found."""
        bridge = SettlementBridge(".")
        settlement = bridge.get_settlement("999")
        assert settlement is None
    
    def test_get_settlement_exact_match(self):
        """Should find settlement by exact match."""
        bridge = SettlementBridge(".")
        bridge.settlements = {
            "1": {"home_goals": 2, "away_goals": 1},
        }
        
        settlement = bridge.get_settlement("1")
        assert settlement == {"home_goals": 2, "away_goals": 1}
    
    def test_get_settlement_numeric_match(self):
        """Should find settlement by numeric match."""
        bridge = SettlementBridge(".")
        bridge.settlements = {
            1: {"home_goals": 2, "away_goals": 1},
        }
        
        settlement = bridge.get_settlement("1")
        assert settlement == {"home_goals": 2, "away_goals": 1}


class TestSettlementBridge1x2Outcome:
    """Test 1X2 outcome computation."""
    
    def test_1x2_home_win(self):
        """Should compute HOME_WIN outcome."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 2, "away_goals": 1}
        
        outcome = bridge.compute_outcome(settlement, "HOME_WIN", "1x2")
        assert outcome == "WIN"
    
    def test_1x2_away_win(self):
        """Should compute AWAY_WIN outcome."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 1, "away_goals": 2}
        
        outcome = bridge.compute_outcome(settlement, "AWAY_WIN", "1x2")
        assert outcome == "WIN"
    
    def test_1x2_draw(self):
        """Should compute DRAW outcome."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 1, "away_goals": 1}
        
        outcome = bridge.compute_outcome(settlement, "DRAW", "1x2")
        assert outcome == "WIN"
    
    def test_1x2_loss(self):
        """Should compute LOSS outcome."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 2, "away_goals": 1}
        
        outcome = bridge.compute_outcome(settlement, "AWAY_WIN", "1x2")
        assert outcome == "LOSS"
    
    def test_1x2_void_missing_goals(self):
        """Should return VOID if goals missing."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": None, "away_goals": 1}
        
        outcome = bridge.compute_outcome(settlement, "HOME_WIN", "1x2")
        assert outcome == "VOID"


class TestSettlementBridgeHandicapOutcome:
    """Test handicap outcome computation."""
    
    def test_handicap_home_win(self):
        """Should compute HOME_HANDICAP win."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 2, "away_goals": 1}
        
        outcome = bridge.compute_outcome(settlement, "HOME_HANDICAP", "handicap")
        assert outcome == "WIN"
    
    def test_handicap_away_win(self):
        """Should compute AWAY_HANDICAP win."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 1, "away_goals": 2}
        
        outcome = bridge.compute_outcome(settlement, "AWAY_HANDICAP", "handicap")
        assert outcome == "WIN"
    
    def test_handicap_loss(self):
        """Should compute handicap loss."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 2, "away_goals": 1}
        
        outcome = bridge.compute_outcome(settlement, "AWAY_HANDICAP", "handicap")
        assert outcome == "LOSS"


class TestSettlementBridgeTotalsOutcome:
    """Test totals outcome computation."""
    
    def test_totals_over(self):
        """Should compute OVER win."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 2, "away_goals": 2}
        
        outcome = bridge.compute_outcome(settlement, "OVER", "totals")
        assert outcome == "WIN"
    
    def test_totals_under(self):
        """Should compute UNDER win."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 1, "away_goals": 1}
        
        outcome = bridge.compute_outcome(settlement, "UNDER", "totals")
        assert outcome == "WIN"
    
    def test_totals_loss(self):
        """Should compute totals loss."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 2, "away_goals": 2}
        
        outcome = bridge.compute_outcome(settlement, "UNDER", "totals")
        assert outcome == "LOSS"


class TestSettlementBridgeHTFTOutcome:
    """Test HT/FT outcome computation."""
    
    def test_htft_home_home(self):
        """Should compute HOME/HOME outcome."""
        bridge = SettlementBridge(".")
        settlement = {
            "ht_home_goals": 1,
            "ht_away_goals": 0,
            "home_goals": 2,
            "away_goals": 0,
        }
        
        outcome = bridge.compute_outcome(settlement, "HOME/HOME", "htft")
        assert outcome == "WIN"
    
    def test_htft_draw_away(self):
        """Should compute DRAW/AWAY outcome."""
        bridge = SettlementBridge(".")
        settlement = {
            "ht_home_goals": 1,
            "ht_away_goals": 1,
            "home_goals": 1,
            "away_goals": 2,
        }
        
        outcome = bridge.compute_outcome(settlement, "DRAW/AWAY", "htft")
        assert outcome == "WIN"
    
    def test_htft_loss(self):
        """Should compute HTFT loss."""
        bridge = SettlementBridge(".")
        settlement = {
            "ht_home_goals": 1,
            "ht_away_goals": 0,
            "home_goals": 2,
            "away_goals": 0,
        }
        
        outcome = bridge.compute_outcome(settlement, "DRAW/AWAY", "htft")
        assert outcome == "LOSS"
    
    def test_htft_void_missing_ht(self):
        """Should return VOID if HT goals missing."""
        bridge = SettlementBridge(".")
        settlement = {
            "ht_home_goals": None,
            "ht_away_goals": 0,
            "home_goals": 2,
            "away_goals": 0,
        }
        
        outcome = bridge.compute_outcome(settlement, "HOME/HOME", "htft")
        assert outcome == "VOID"


class TestSettlementBridgeScorelineOutcome:
    """Test scoreline outcome computation."""
    
    def test_scoreline_exact_match(self):
        """Should compute scoreline win."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 2, "away_goals": 1}
        
        outcome = bridge.compute_outcome(settlement, "2-1", "scoreline")
        assert outcome == "WIN"
    
    def test_scoreline_loss(self):
        """Should compute scoreline loss."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 2, "away_goals": 1}
        
        outcome = bridge.compute_outcome(settlement, "1-0", "scoreline")
        assert outcome == "LOSS"
    
    def test_scoreline_high_score(self):
        """Should handle high scores."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 5, "away_goals": 4}
        
        outcome = bridge.compute_outcome(settlement, "5-4", "scoreline")
        assert outcome == "WIN"


class TestSettlementBridgeEdgeCases:
    """Test edge cases."""
    
    def test_compute_outcome_none_settlement(self):
        """Should return VOID for None settlement."""
        bridge = SettlementBridge(".")
        outcome = bridge.compute_outcome(None, "HOME_WIN", "1x2")
        assert outcome == "VOID"
    
    def test_compute_outcome_unknown_play_type(self):
        """Should return VOID for unknown play type."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 2, "away_goals": 1}
        
        outcome = bridge.compute_outcome(settlement, "HOME_WIN", "unknown")
        assert outcome == "VOID"
    
    def test_compute_outcome_zero_goals(self):
        """Should handle 0-0 scoreline."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 0, "away_goals": 0}
        
        outcome = bridge.compute_outcome(settlement, "DRAW", "1x2")
        assert outcome == "WIN"
    
    def test_compute_outcome_high_score(self):
        """Should handle high scores."""
        bridge = SettlementBridge(".")
        settlement = {"home_goals": 10, "away_goals": 5}
        
        outcome = bridge.compute_outcome(settlement, "HOME_WIN", "1x2")
        assert outcome == "WIN"


class TestSettlementBridgeSummary:
    """Test summary generation."""
    
    def test_get_summary_empty(self):
        """Should return empty summary."""
        bridge = SettlementBridge(".")
        summary = bridge.get_summary()
        
        assert summary["settlements_loaded"] == 0
        assert summary["match_id_mappings"] == 0
    
    def test_get_summary_with_data(self):
        """Should return summary with data."""
        bridge = SettlementBridge(".")
        bridge.settlements = {
            "1": {"home_goals": 2, "away_goals": 1},
            "2": {"home_goals": 1, "away_goals": 1},
        }
        bridge.match_id_map = {
            "1": "match_1",
            "2": "match_2",
        }
        
        summary = bridge.get_summary()
        
        assert summary["settlements_loaded"] == 2
        assert summary["match_id_mappings"] == 2
