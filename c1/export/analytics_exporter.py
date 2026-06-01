"""
Analytics Exporter

Exports aggregated statistics and analytics.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from c1.audit import C1AuditStore


class AnalyticsExporter:
    """Exports analytics and aggregated statistics."""
    
    def __init__(self, audit_store: C1AuditStore) -> None:
        self.audit_store = audit_store
    
    def export_daily_analytics(
        self,
        output_path: str | Path,
        limit: int | None = None,
    ) -> int:
        """
        Export daily analytics summary.
        
        Args:
            output_path: Path to output JSON file
            limit: Maximum number of decisions to analyze
        
        Returns:
            Number of days analyzed
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        decisions = self.audit_store.read_governance_decisions(limit=limit)
        
        # Group by date
        daily_stats = defaultdict(lambda: {
            "total_matches": 0,
            "governance_distribution": defaultdict(int),
            "reason_code_distribution": defaultdict(int),
            "confidence_distribution": defaultdict(int),
            "play_type_distribution": defaultdict(int),
            "release_rate": 0.0,
        })
        
        for decision in decisions:
            created_at = decision.get("created_at", "")
            date = created_at.split(" ")[0] if created_at else "unknown"
            
            stats = daily_stats[date]
            stats["total_matches"] += 1
            
            # Governance distribution
            governance_action = decision.get("governance_decision", {}).get("action", "UNKNOWN")
            stats["governance_distribution"][governance_action] += 1
            
            # Reason code distribution
            reason_codes = decision.get("governance_decision", {}).get("reason_codes", [])
            for code in reason_codes:
                stats["reason_code_distribution"][code] += 1
            
            # Confidence distribution
            confidence = decision.get("prediction_snapshot", {}).get("confidence", 0.0)
            if confidence < 0.3:
                bin_name = "0.0-0.3"
            elif confidence < 0.5:
                bin_name = "0.3-0.5"
            elif confidence < 0.7:
                bin_name = "0.5-0.7"
            else:
                bin_name = "0.7-1.0"
            stats["confidence_distribution"][bin_name] += 1
            
            # Play type distribution
            translation_items = decision.get("translation_result", {}).get("items", [])
            for item in translation_items:
                if item.get("selection"):
                    play_type = item.get("play", "unknown")
                    stats["play_type_distribution"][play_type] += 1
            
            # Release rate
            release_decision = decision.get("release_decision", {})
            if release_decision.get("release_allowed"):
                stats["release_rate"] += 1
        
        # Calculate release rates and convert to regular dicts
        analytics = {}
        for date, stats in sorted(daily_stats.items()):
            total = stats["total_matches"]
            release_rate = stats["release_rate"] / total if total > 0 else 0.0
            
            analytics[date] = {
                "total_matches": total,
                "governance_distribution": dict(stats["governance_distribution"]),
                "reason_code_distribution": dict(stats["reason_code_distribution"]),
                "confidence_distribution": dict(stats["confidence_distribution"]),
                "play_type_distribution": dict(stats["play_type_distribution"]),
                "release_rate": round(release_rate, 4),
            }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analytics, f, ensure_ascii=False, indent=2)
        
        return len(analytics)
    
    def export_summary_statistics(
        self,
        output_path: str | Path,
        limit: int | None = None,
    ) -> int:
        """
        Export overall summary statistics.
        
        Args:
            output_path: Path to output JSON file
            limit: Maximum number of decisions to analyze
        
        Returns:
            1 if successful
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        decisions = self.audit_store.read_governance_decisions(limit=limit)
        
        if not decisions:
            return 0
        
        # Initialize counters
        total_matches = len(decisions)
        governance_dist = defaultdict(int)
        reason_code_dist = defaultdict(int)
        confidence_dist = defaultdict(int)
        play_type_dist = defaultdict(int)
        release_count = 0
        
        confidence_values = []
        
        for decision in decisions:
            # Governance distribution
            governance_action = decision.get("governance_decision", {}).get("action", "UNKNOWN")
            governance_dist[governance_action] += 1
            
            # Reason code distribution
            reason_codes = decision.get("governance_decision", {}).get("reason_codes", [])
            for code in reason_codes:
                reason_code_dist[code] += 1
            
            # Confidence distribution
            confidence = decision.get("prediction_snapshot", {}).get("confidence", 0.0)
            confidence_values.append(confidence)
            
            if confidence < 0.3:
                bin_name = "0.0-0.3"
            elif confidence < 0.5:
                bin_name = "0.3-0.5"
            elif confidence < 0.7:
                bin_name = "0.5-0.7"
            else:
                bin_name = "0.7-1.0"
            confidence_dist[bin_name] += 1
            
            # Play type distribution
            translation_items = decision.get("translation_result", {}).get("items", [])
            for item in translation_items:
                if item.get("selection"):
                    play_type = item.get("play", "unknown")
                    play_type_dist[play_type] += 1
            
            # Release rate
            release_decision = decision.get("release_decision", {})
            if release_decision.get("release_allowed"):
                release_count += 1
        
        # Calculate statistics
        avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
        min_confidence = min(confidence_values) if confidence_values else 0.0
        max_confidence = max(confidence_values) if confidence_values else 0.0
        
        summary = {
            "total_matches": total_matches,
            "release_rate": round(release_count / total_matches, 4) if total_matches > 0 else 0.0,
            "governance_distribution": dict(governance_dist),
            "reason_code_distribution": dict(reason_code_dist),
            "confidence_distribution": dict(confidence_dist),
            "confidence_statistics": {
                "average": round(avg_confidence, 4),
                "minimum": round(min_confidence, 4),
                "maximum": round(max_confidence, 4),
            },
            "play_type_distribution": dict(play_type_dist),
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        return 1
