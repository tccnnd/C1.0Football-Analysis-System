"""
Recommendation Feed

Formats recommendations for UI and external systems.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from c1.audit import C1AuditStore


class RecommendationFeed:
    """Generates recommendation feeds from decisions."""
    
    def __init__(self, audit_store: C1AuditStore) -> None:
        self.audit_store = audit_store
    
    def generate_feed(
        self,
        output_path: str | Path | None = None,
        filter_action: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Generate recommendation feed.
        
        Args:
            output_path: Optional path to save feed as JSON
            filter_action: Filter by governance action (e.g., "APPROVE")
            limit: Maximum number of recommendations
        
        Returns:
            List of recommendation items
        """
        decisions = self.audit_store.read_governance_decisions(limit=limit)
        
        recommendations = []
        for decision in decisions:
            # Filter by governance action if specified
            governance_action = decision.get("governance_decision", {}).get("action", "")
            if filter_action and governance_action != filter_action:
                continue
            
            # Format recommendation
            rec = self._format_recommendation(decision)
            if rec:
                recommendations.append(rec)
        
        # Save to file if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(recommendations, f, ensure_ascii=False, indent=2)
        
        return recommendations
    
    def _format_recommendation(self, decision: dict[str, Any]) -> dict[str, Any] | None:
        """Format a single recommendation."""
        match_id = decision.get("match_id", "")
        if not match_id:
            return None
        
        translation_result = decision.get("translation_result", {})
        translation_items = translation_result.get("items", [])
        
        # Filter to items with selections
        recommendations = []
        for item in translation_items:
            if not item.get("selection"):
                continue
            
            rec = {
                "play": item.get("play", ""),
                "selection": item.get("selection", ""),
                "confidence": item.get("confidence", 0.0),
                "status": item.get("status", ""),
                "rationale": item.get("rationale", []),
                "tags": item.get("tags", []),
            }
            recommendations.append(rec)
        
        if not recommendations:
            return None
        
        # Get metadata
        feature_snapshot = decision.get("feature_snapshot", {})
        prediction_snapshot = decision.get("prediction_snapshot", {})
        governance_decision = decision.get("governance_decision", {})
        
        return {
            "match_id": match_id,
            "created_at": decision.get("created_at", ""),
            "metadata": {
                "home_rating": feature_snapshot.get("fields", {}).get("home_rating"),
                "away_rating": feature_snapshot.get("fields", {}).get("away_rating"),
                "confidence": prediction_snapshot.get("confidence", 0.0),
                "predicted_side": prediction_snapshot.get("predicted_side", ""),
                "governance_action": governance_decision.get("action", ""),
                "reason_codes": governance_decision.get("reason_codes", []),
            },
            "recommendations": recommendations,
        }
    
    def generate_feed_jsonl(
        self,
        output_path: str | Path,
        filter_action: str | None = None,
        limit: int | None = None,
    ) -> int:
        """
        Generate recommendation feed in JSONL format.
        
        Args:
            output_path: Path to save feed as JSONL
            filter_action: Filter by governance action
            limit: Maximum number of recommendations
        
        Returns:
            Number of recommendations written
        """
        decisions = self.audit_store.read_governance_decisions(limit=limit)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for decision in decisions:
                # Filter by governance action if specified
                governance_action = decision.get("governance_decision", {}).get("action", "")
                if filter_action and governance_action != filter_action:
                    continue
                
                # Format recommendation
                rec = self._format_recommendation(decision)
                if rec:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    count += 1
        
        return count
    
    def get_active_recommendations(
        self,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get only active recommendations (APPROVE status).
        
        Args:
            limit: Maximum number of recommendations
        
        Returns:
            List of active recommendations
        """
        return self.generate_feed(filter_action="APPROVE", limit=limit)
    
    def get_downgraded_recommendations(
        self,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get downgraded recommendations (DOWNGRADE status).
        
        Args:
            limit: Maximum number of recommendations
        
        Returns:
            List of downgraded recommendations
        """
        return self.generate_feed(filter_action="DOWNGRADE", limit=limit)
    
    def get_high_confidence_recommendations(
        self,
        min_confidence: float = 0.70,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get high confidence recommendations.
        
        Args:
            min_confidence: Minimum confidence threshold
            limit: Maximum number of recommendations
        
        Returns:
            List of high confidence recommendations
        """
        decisions = self.audit_store.read_governance_decisions(limit=limit)
        
        recommendations = []
        for decision in decisions:
            prediction_snapshot = decision.get("prediction_snapshot", {})
            confidence = prediction_snapshot.get("confidence", 0.0)
            
            if confidence >= min_confidence:
                rec = self._format_recommendation(decision)
                if rec:
                    recommendations.append(rec)
        
        return recommendations
    
    def get_summary(self, limit: int | None = None) -> dict[str, Any]:
        """
        Get summary of recommendations.
        
        Args:
            limit: Maximum number of decisions to analyze
        
        Returns:
            Summary statistics
        """
        decisions = self.audit_store.read_governance_decisions(limit=limit)
        
        total_decisions = len(decisions)
        total_recommendations = 0
        by_play_type = {}
        by_status = {}
        by_governance_action = {}
        
        for decision in decisions:
            translation_items = decision.get("translation_result", {}).get("items", [])
            
            for item in translation_items:
                if item.get("selection"):
                    total_recommendations += 1
                    
                    # Count by play type
                    play_type = item.get("play", "unknown")
                    by_play_type[play_type] = by_play_type.get(play_type, 0) + 1
                    
                    # Count by status
                    status = item.get("status", "unknown")
                    by_status[status] = by_status.get(status, 0) + 1
            
            # Count by governance action
            governance_action = decision.get("governance_decision", {}).get("action", "unknown")
            by_governance_action[governance_action] = by_governance_action.get(governance_action, 0) + 1
        
        return {
            "total_decisions": total_decisions,
            "total_recommendations": total_recommendations,
            "avg_recommendations_per_decision": (
                total_recommendations / total_decisions if total_decisions > 0 else 0.0
            ),
            "by_play_type": by_play_type,
            "by_status": by_status,
            "by_governance_action": by_governance_action,
        }
