"""
End-to-End Export Test

Tests the complete export pipeline combining all exporters.
"""

import json
import tempfile
from pathlib import Path

import pytest

from c1.audit import C1AuditStore
from c1.export.decision_exporter import DecisionExporter
from c1.export.analytics_exporter import AnalyticsExporter
from c1.export.recommendation_feed import RecommendationFeed


class TestExportE2E:
    """End-to-end export tests."""
    
    def test_export_e2e_decision_json(self):
        """Should export decisions as JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            exporter = DecisionExporter(store)
            
            # Export
            output_path = Path(tmpdir) / "decisions.json"
            count = exporter.export_decisions_json(output_path)
            
            # Verify
            assert output_path.exists()
            assert count == 0  # No decisions recorded
    
    def test_export_e2e_decision_jsonl(self):
        """Should export decisions as JSONL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            exporter = DecisionExporter(store)
            
            # Export
            output_path = Path(tmpdir) / "decisions.jsonl"
            count = exporter.export_decisions_jsonl(output_path)
            
            # Verify
            assert output_path.exists()
            assert count == 0  # No decisions recorded
    
    def test_export_e2e_decision_csv(self):
        """Should export decisions as CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            exporter = DecisionExporter(store)
            
            # Export
            output_path = Path(tmpdir) / "decisions.csv"
            count = exporter.export_decisions_csv(output_path)
            
            # Verify - CSV file may not be created if no decisions
            assert count == 0  # No decisions recorded
    
    def test_export_e2e_analytics_daily(self):
        """Should export daily analytics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            exporter = AnalyticsExporter(store)
            
            # Export
            output_path = Path(tmpdir) / "analytics_daily.json"
            count = exporter.export_daily_analytics(output_path)
            
            # Verify
            assert output_path.exists()
            assert count == 0  # No decisions recorded
    
    def test_export_e2e_analytics_summary(self):
        """Should export summary statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            exporter = AnalyticsExporter(store)
            
            # Export
            output_path = Path(tmpdir) / "analytics_summary.json"
            count = exporter.export_summary_statistics(output_path)
            
            # Verify - file may not be created if no decisions
            assert count == 0  # No decisions recorded
    
    def test_export_e2e_recommendation_feed_json(self):
        """Should export recommendation feed as JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            # Export
            output_path = Path(tmpdir) / "recommendations.json"
            recommendations = feed.generate_feed(output_path=output_path)
            
            # Verify
            assert output_path.exists()
            assert recommendations == []
    
    def test_export_e2e_recommendation_feed_jsonl(self):
        """Should export recommendation feed as JSONL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            # Export
            output_path = Path(tmpdir) / "recommendations.jsonl"
            count = feed.generate_feed_jsonl(output_path=output_path)
            
            # Verify
            assert output_path.exists()
            assert count == 0  # No decisions recorded
    
    def test_export_e2e_all_formats(self):
        """Should export in all formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            decision_exporter = DecisionExporter(store)
            analytics_exporter = AnalyticsExporter(store)
            feed = RecommendationFeed(store)
            
            # Export decisions
            decisions_json = Path(tmpdir) / "decisions.json"
            decisions_jsonl = Path(tmpdir) / "decisions.jsonl"
            decisions_csv = Path(tmpdir) / "decisions.csv"
            
            decision_exporter.export_decisions_json(decisions_json)
            decision_exporter.export_decisions_jsonl(decisions_jsonl)
            decision_exporter.export_decisions_csv(decisions_csv)
            
            # Export analytics
            analytics_daily = Path(tmpdir) / "analytics_daily.json"
            analytics_summary = Path(tmpdir) / "analytics_summary.json"
            
            analytics_exporter.export_daily_analytics(analytics_daily)
            analytics_exporter.export_summary_statistics(analytics_summary)
            
            # Export recommendations
            recommendations_json = Path(tmpdir) / "recommendations.json"
            recommendations_jsonl = Path(tmpdir) / "recommendations.jsonl"
            
            feed.generate_feed(output_path=recommendations_json)
            feed.generate_feed_jsonl(output_path=recommendations_jsonl)
            
            # Verify JSON files exist (always created)
            assert decisions_json.exists()
            assert decisions_jsonl.exists()
            assert analytics_daily.exists()
            assert recommendations_json.exists()
            assert recommendations_jsonl.exists()
            # CSV and summary may not be created if no decisions
    
    def test_export_e2e_file_formats(self):
        """Should create valid file formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            exporter = DecisionExporter(store)
            
            # Export JSON
            json_path = Path(tmpdir) / "decisions.json"
            exporter.export_decisions_json(json_path)
            
            # Verify JSON is valid
            with open(json_path) as f:
                data = json.load(f)
                assert isinstance(data, list)
            
            # Export JSONL
            jsonl_path = Path(tmpdir) / "decisions.jsonl"
            exporter.export_decisions_jsonl(jsonl_path)
            
            # Verify JSONL is valid
            with open(jsonl_path) as f:
                lines = f.readlines()
                # Each line should be valid JSON
                for line in lines:
                    if line.strip():
                        json.loads(line)
    
    def test_export_e2e_with_filtering(self):
        """Should support filtering in exports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            # Generate feed with filter
            recommendations = feed.generate_feed(filter_action="APPROVE")
            
            # Verify
            assert recommendations == []
    
    def test_export_e2e_with_limits(self):
        """Should support limits in exports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            exporter = DecisionExporter(store)
            
            # Export with limit
            output_path = Path(tmpdir) / "decisions.json"
            count = exporter.export_decisions_json(output_path, limit=10)
            
            # Verify
            assert count == 0  # No decisions recorded
    
    def test_export_e2e_summary_generation(self):
        """Should generate export summaries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            store = C1AuditStore(tmpdir)
            feed = RecommendationFeed(store)
            
            # Get summary
            summary = feed.get_summary()
            
            # Verify
            assert summary["total_decisions"] == 0
            assert summary["total_recommendations"] == 0
            assert summary["avg_recommendations_per_decision"] == 0.0
            assert isinstance(summary["by_play_type"], dict)
            assert isinstance(summary["by_status"], dict)
            assert isinstance(summary["by_governance_action"], dict)
