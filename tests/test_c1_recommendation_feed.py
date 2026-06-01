"""
Tests for Recommendation Feed

Tests recommendation feed generation and filtering.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from c1.audit import C1AuditStore
from c1.export.recommendation_feed import RecommendationFeed


class TestRecommendationFeedGeneration:
    """Test recommendation feed generation."""
    
    def test_generate_feed_empty(self):
        """Should generate empty feed when no decisions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            recommendations = feed.generate_feed()
            assert recommendations == []
    
    def test_generate_feed_with_filter(self):
        """Should filter feed by governance action."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            recommendations = feed.generate_feed(filter_action="APPROVE")
            assert recommendations == []
    
    def test_generate_feed_with_limit(self):
        """Should limit feed results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            recommendations = feed.generate_feed(limit=5)
            assert isinstance(recommendations, list)


class TestRecommendationFeedFiltering:
    """Test recommendation feed filtering."""
    
    def test_get_active_recommendations(self):
        """Should get active recommendations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            recommendations = feed.get_active_recommendations()
            assert recommendations == []
    
    def test_get_downgraded_recommendations(self):
        """Should get downgraded recommendations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            recommendations = feed.get_downgraded_recommendations()
            assert recommendations == []
    
    def test_get_high_confidence_recommendations(self):
        """Should get high confidence recommendations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            recommendations = feed.get_high_confidence_recommendations(min_confidence=0.7)
            assert recommendations == []
    
    def test_get_high_confidence_with_custom_threshold(self):
        """Should filter by custom confidence threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            recommendations = feed.get_high_confidence_recommendations(min_confidence=0.5)
            assert isinstance(recommendations, list)


class TestRecommendationFeedExport:
    """Test recommendation feed export."""
    
    def test_generate_feed_json_export(self):
        """Should export feed as JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            output_path = Path(tmpdir) / "recommendations.json"
            recommendations = feed.generate_feed(output_path=output_path)
            
            assert output_path.exists()
    
    def test_generate_feed_jsonl_export(self):
        """Should export feed as JSONL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            output_path = Path(tmpdir) / "recommendations.jsonl"
            count = feed.generate_feed_jsonl(output_path=output_path)
            
            assert output_path.exists()
            assert count == 0


class TestRecommendationFeedSummary:
    """Test recommendation feed summary."""
    
    def test_get_summary_empty(self):
        """Should get summary for empty feed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            summary = feed.get_summary()
            
            assert summary["total_decisions"] == 0
            assert summary["total_recommendations"] == 0
            assert summary["avg_recommendations_per_decision"] == 0.0
            assert summary["by_play_type"] == {}
            assert summary["by_status"] == {}
            assert summary["by_governance_action"] == {}
    
    def test_get_summary_with_data(self):
        """Should get summary with data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            summary = feed.get_summary()
            
            assert isinstance(summary, dict)
            assert "total_decisions" in summary
            assert "total_recommendations" in summary
            assert "avg_recommendations_per_decision" in summary
            assert "by_play_type" in summary
            assert "by_status" in summary
            assert "by_governance_action" in summary


class TestRecommendationFeedFormatting:
    """Test recommendation formatting."""
    
    def test_format_recommendation_empty_decision(self):
        """Should handle empty decision."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            decision = {}
            result = feed._format_recommendation(decision)
            
            assert result is None
    
    def test_format_recommendation_no_selections(self):
        """Should handle decision with no selections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            decision = {
                "match_id": "match_1",
                "translation_result": {"items": []},
            }
            result = feed._format_recommendation(decision)
            
            assert result is None
    
    def test_format_recommendation_with_selections(self):
        """Should format recommendation with selections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            decision = {
                "match_id": "match_1",
                "created_at": "2026-05-27 14:30:00",
                "feature_snapshot": {
                    "fields": {
                        "home_rating": 1500.0,
                        "away_rating": 1600.0,
                    }
                },
                "prediction_snapshot": {
                    "confidence": 0.7,
                    "predicted_side": "away",
                },
                "governance_decision": {
                    "action": "APPROVE",
                    "reason_codes": [],
                },
                "translation_result": {
                    "items": [
                        {
                            "play": "1x2",
                            "selection": "AWAY_WIN",
                            "confidence": 0.7,
                            "status": "ACTIVE",
                            "rationale": ["test"],
                            "tags": [],
                        }
                    ]
                },
            }
            result = feed._format_recommendation(decision)
            
            assert result is not None
            assert result["match_id"] == "match_1"
            assert len(result["recommendations"]) == 1
            assert result["recommendations"][0]["play"] == "1x2"
            assert result["recommendations"][0]["selection"] == "AWAY_WIN"


class TestRecommendationFeedIntegration:
    """Test recommendation feed integration."""
    
    def test_feed_with_audit_store(self):
        """Should work with audit store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            recommendations = feed.generate_feed()
            summary = feed.get_summary()
            
            assert isinstance(recommendations, list)
            assert isinstance(summary, dict)
    
    def test_feed_export_to_file(self):
        """Should export feed to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            output_path = Path(tmpdir) / "feed.json"
            feed.generate_feed(output_path=output_path)
            
            assert output_path.exists()
    
    def test_feed_jsonl_export_to_file(self):
        """Should export feed to JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            output_path = Path(tmpdir) / "feed.jsonl"
            count = feed.generate_feed_jsonl(output_path=output_path)
            
            assert output_path.exists()
            assert count == 0
