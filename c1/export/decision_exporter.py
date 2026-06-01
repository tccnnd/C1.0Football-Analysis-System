"""
Decision Exporter

Exports governance decisions, translations, and release decisions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from c1.audit import C1AuditStore


class DecisionExporter:
    """Exports C1 decisions in various formats."""
    
    def __init__(self, audit_store: C1AuditStore) -> None:
        self.audit_store = audit_store
    
    def export_decisions_json(
        self,
        output_path: str | Path,
        limit: int | None = None,
    ) -> int:
        """
        Export decisions to JSON format.
        
        Args:
            output_path: Path to output JSON file
            limit: Maximum number of decisions to export
        
        Returns:
            Number of decisions exported
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        decisions = self.audit_store.read_governance_decisions(limit=limit)
        
        exported = []
        for decision in decisions:
            item = self._format_decision(decision)
            exported.append(item)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(exported, f, ensure_ascii=False, indent=2)
        
        return len(exported)
    
    def export_decisions_jsonl(
        self,
        output_path: str | Path,
        limit: int | None = None,
    ) -> int:
        """
        Export decisions to JSONL format (one JSON per line).
        
        Args:
            output_path: Path to output JSONL file
            limit: Maximum number of decisions to export
        
        Returns:
            Number of decisions exported
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        decisions = self.audit_store.read_governance_decisions(limit=limit)
        
        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for decision in decisions:
                item = self._format_decision(decision)
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                count += 1
        
        return count
    
    def export_decisions_csv(
        self,
        output_path: str | Path,
        limit: int | None = None,
    ) -> int:
        """
        Export decisions to CSV format.
        
        Args:
            output_path: Path to output CSV file
            limit: Maximum number of decisions to export
        
        Returns:
            Number of decisions exported
        """
        import csv
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        decisions = self.audit_store.read_governance_decisions(limit=limit)
        
        if not decisions:
            return 0
        
        # Extract first decision to get field names
        first_item = self._format_decision(decisions[0])
        fieldnames = list(first_item.keys())
        
        count = 0
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for decision in decisions:
                item = self._format_decision(decision)
                # Flatten nested dicts for CSV
                flat_item = self._flatten_dict(item)
                writer.writerow(flat_item)
                count += 1
        
        return count
    
    def _format_decision(self, decision: dict[str, Any]) -> dict[str, Any]:
        """Format a decision for export."""
        feature_snapshot = decision.get("feature_snapshot", {})
        prediction_snapshot = decision.get("prediction_snapshot", {})
        governance_decision = decision.get("governance_decision", {})
        translation_result = decision.get("translation_result", {})
        release_decision = decision.get("release_decision", {})
        
        return {
            "match_id": decision.get("match_id", ""),
            "created_at": decision.get("created_at", ""),
            
            # Features
            "features": {
                "home_rating": feature_snapshot.get("fields", {}).get("home_rating"),
                "away_rating": feature_snapshot.get("fields", {}).get("away_rating"),
                "info_quality": feature_snapshot.get("fields", {}).get("info_quality"),
                "missing_elo_loss": feature_snapshot.get("fields", {}).get("missing_elo_loss"),
            },
            
            # Inference
            "inference": {
                "predicted_side": prediction_snapshot.get("predicted_side"),
                "confidence": prediction_snapshot.get("confidence"),
                "probabilities": prediction_snapshot.get("raw_probabilities", {}),
            },
            
            # Governance
            "governance": {
                "action": governance_decision.get("action"),
                "reason_codes": governance_decision.get("reason_codes", []),
                "tags": governance_decision.get("tags", []),
            },
            
            # Translation
            "translation": {
                "items": [
                    {
                        "play": item.get("play"),
                        "selection": item.get("selection"),
                        "confidence": item.get("confidence"),
                        "status": item.get("status"),
                    }
                    for item in translation_result.get("items", [])
                ]
            },
            
            # Release
            "release": {
                "action": release_decision.get("release_action"),
                "allowed": release_decision.get("release_allowed"),
                "candidates": len(release_decision.get("candidates", [])),
            },
        }
    
    def _flatten_dict(self, d: dict[str, Any], parent_key: str = "", sep: str = "_") -> dict[str, Any]:
        """Flatten nested dictionary for CSV export."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, json.dumps(v)))
            else:
                items.append((new_key, v))
        return dict(items)
