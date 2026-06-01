"""
Settlement Bridge

Maps V24 settlements to C1 matches and computes actual outcomes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


class SettlementBridge:
    """Bridges V24 settlements to C1 matches."""
    
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.settlements: dict[str, Any] = {}
        self.match_id_map: dict[str, str] = {}
    
    def load_settlements(self) -> int:
        """
        Load settlements from V24 state file.
        
        Returns:
            Number of settlements loaded
        """
        settlement_file = self.project_root / "data" / "state" / "settlements.json"
        
        if not settlement_file.exists():
            return 0
        
        try:
            payload = json.loads(settlement_file.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                self.settlements = payload.get("settlements", {})
            return len(self.settlements)
        except Exception:
            return 0
    
    def build_match_id_map(self, matches: list[dict[str, Any]]) -> int:
        """
        Build mapping from source_id to C1 match_id.
        
        Args:
            matches: List of match records with source_id and match_id
        
        Returns:
            Number of mappings created
        """
        for match in matches:
            source_id = str(match.get("source_id", ""))
            match_id = str(match.get("match_id", ""))
            
            if source_id and match_id:
                self.match_id_map[source_id] = match_id
        
        return len(self.match_id_map)
    
    def get_settlement(self, source_id: str) -> dict[str, Any] | None:
        """
        Get settlement for a source_id.
        
        Args:
            source_id: V24 source ID
        
        Returns:
            Settlement dict or None if not found
        """
        source_id_str = str(source_id)
        
        # Try exact match
        if source_id_str in self.settlements:
            return self.settlements[source_id_str]
        
        # Try numeric match
        try:
            source_id_int = int(source_id_str)
            if source_id_int in self.settlements:
                return self.settlements[source_id_int]
        except (ValueError, TypeError):
            pass
        
        return None
    
    def compute_outcome(
        self,
        settlement: dict[str, Any],
        selection: str,
        play_type: str,
    ) -> str:
        """
        Compute actual outcome from settlement.
        
        Args:
            settlement: Settlement record
            selection: Betting selection (e.g., "HOME_WIN", "1-0")
            play_type: Play type (e.g., "1x2", "scoreline")
        
        Returns:
            "WIN", "LOSS", or "VOID"
        """
        if not settlement:
            return "VOID"
        
        # Get actual result
        home_goals = _safe_float(settlement.get("home_goals"), -1.0)
        away_goals = _safe_float(settlement.get("away_goals"), -1.0)
        
        # If no goals recorded, it's void
        if home_goals < 0 or away_goals < 0:
            return "VOID"
        
        # Determine actual outcome
        if home_goals > away_goals:
            actual_result = "home"
        elif away_goals > home_goals:
            actual_result = "away"
        else:
            actual_result = "draw"
        
        # Check if selection matches actual result
        if play_type == "1x2":
            return self._check_1x2_outcome(selection, actual_result)
        elif play_type == "handicap":
            return self._check_handicap_outcome(selection, home_goals, away_goals)
        elif play_type == "totals":
            return self._check_totals_outcome(selection, home_goals, away_goals)
        elif play_type == "htft":
            return self._check_htft_outcome(selection, settlement)
        elif play_type == "scoreline":
            return self._check_scoreline_outcome(selection, home_goals, away_goals)
        else:
            return "VOID"
    
    def _check_1x2_outcome(self, selection: str, actual_result: str) -> str:
        """Check 1X2 outcome."""
        selection_map = {
            "HOME_WIN": "home",
            "DRAW": "draw",
            "AWAY_WIN": "away",
        }
        
        expected_result = selection_map.get(selection)
        if expected_result == actual_result:
            return "WIN"
        else:
            return "LOSS"
    
    def _check_handicap_outcome(
        self,
        selection: str,
        home_goals: float,
        away_goals: float,
    ) -> str:
        """Check handicap outcome."""
        # For simplicity, assume 0.5 handicap
        # In real implementation, would need to extract line from settlement
        handicap_line = 0.5
        
        adjusted_home = home_goals - handicap_line
        
        if selection == "HOME_HANDICAP":
            if adjusted_home > away_goals:
                return "WIN"
            else:
                return "LOSS"
        elif selection == "AWAY_HANDICAP":
            if away_goals > adjusted_home:
                return "WIN"
            else:
                return "LOSS"
        else:
            return "VOID"
    
    def _check_totals_outcome(
        self,
        selection: str,
        home_goals: float,
        away_goals: float,
    ) -> str:
        """Check totals outcome."""
        # For simplicity, assume 2.5 line
        # In real implementation, would need to extract line from settlement
        total_line = 2.5
        total_goals = home_goals + away_goals
        
        if selection == "OVER":
            if total_goals > total_line:
                return "WIN"
            else:
                return "LOSS"
        elif selection == "UNDER":
            if total_goals < total_line:
                return "WIN"
            else:
                return "LOSS"
        else:
            return "VOID"
    
    def _check_htft_outcome(
        self,
        selection: str,
        settlement: dict[str, Any],
    ) -> str:
        """Check HT/FT outcome."""
        # Get HT and FT results
        ht_home_goals = _safe_float(settlement.get("ht_home_goals"), -1.0)
        ht_away_goals = _safe_float(settlement.get("ht_away_goals"), -1.0)
        ft_home_goals = _safe_float(settlement.get("home_goals"), -1.0)
        ft_away_goals = _safe_float(settlement.get("away_goals"), -1.0)
        
        if ht_home_goals < 0 or ht_away_goals < 0 or ft_home_goals < 0 or ft_away_goals < 0:
            return "VOID"
        
        # Determine HT and FT results
        if ht_home_goals > ht_away_goals:
            ht_result = "HOME"
        elif ht_away_goals > ht_home_goals:
            ht_result = "AWAY"
        else:
            ht_result = "DRAW"
        
        if ft_home_goals > ft_away_goals:
            ft_result = "HOME"
        elif ft_away_goals > ft_home_goals:
            ft_result = "AWAY"
        else:
            ft_result = "DRAW"
        
        expected_outcome = f"{ht_result}/{ft_result}"
        
        if selection == expected_outcome:
            return "WIN"
        else:
            return "LOSS"
    
    def _check_scoreline_outcome(
        self,
        selection: str,
        home_goals: float,
        away_goals: float,
    ) -> str:
        """Check scoreline outcome."""
        expected_score = f"{int(home_goals)}-{int(away_goals)}"
        
        if selection == expected_score:
            return "WIN"
        else:
            return "LOSS"
    
    def get_summary(self) -> dict[str, Any]:
        """Get summary of settlement bridge."""
        return {
            "settlements_loaded": len(self.settlements),
            "match_id_mappings": len(self.match_id_map),
        }
