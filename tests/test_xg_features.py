"""
Tests for xG Features Integration

Verifies xG feature extraction and integration with XGBoost.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from v24_app.features.xg_features import (
    XGDatabase,
    get_xg_database,
    get_match_xg_features,
)


class TestXGDatabase(unittest.TestCase):
    """Test xG database loading and querying."""

    def test_database_loads(self):
        """Should load xG database successfully."""
        db = XGDatabase()
        db.load()
        self.assertGreater(db.team_count, 0)
        self.assertGreater(db.total_records, 0)

    def test_get_team_features(self):
        """Should get team xG features."""
        db = get_xg_database()
        features = db.get_team_features("Manchester City", n=5)
        
        self.assertIn("xg_for_avg", features)
        self.assertIn("xg_against_avg", features)
        self.assertIn("xg_overperform", features)
        self.assertGreater(features["xg_sample_count"], 0)

    def test_build_match_features(self):
        """Should build match xG features."""
        db = get_xg_database()
        features = db.build_match_xg_features(
            home_team="Manchester City",
            away_team="Liverpool",
            match_date="2024-01-01",
        )
        
        # Check all 15 features exist
        expected_features = [
            "home_xg_for_avg5",
            "home_xg_against_avg5",
            "home_xg_overperform5",
            "home_xg_defense_overp5",
            "home_xg_trend5",
            "away_xg_for_avg5",
            "away_xg_against_avg5",
            "away_xg_overperform5",
            "away_xg_defense_overp5",
            "away_xg_trend5",
            "xg_attack_diff",
            "xg_defense_diff",
            "xg_overperform_diff",
            "xg_home_sample_count",
            "xg_away_sample_count",
        ]
        
        for feature in expected_features:
            self.assertIn(feature, features)
            self.assertIsInstance(features[feature], float)

    def test_team_name_normalization(self):
        """Should normalize team names correctly."""
        db = get_xg_database()
        
        # Test English name
        features_en = db.get_team_features("Manchester City", n=5)
        self.assertGreater(features_en["xg_sample_count"], 0)
        
        # Test Chinese name (if mapped)
        features_cn = db.get_team_features("曼城", n=5)
        self.assertGreater(features_cn["xg_sample_count"], 0)

    def test_default_features_for_unknown_team(self):
        """Should return default features for unknown teams."""
        db = get_xg_database()
        features = db.get_team_features("Unknown Team FC", n=5)
        
        self.assertEqual(features["xg_for_avg"], 1.3)
        self.assertEqual(features["xg_against_avg"], 1.3)
        self.assertEqual(features["xg_sample_count"], 0)

    def test_temporal_filtering(self):
        """Should filter records before specified date."""
        db = get_xg_database()
        
        # Get features before 2023-01-01
        features_2022 = db.get_team_features(
            "Manchester City",
            before_date="2023-01-01",
            n=5,
        )
        
        # Get features before 2024-01-01
        features_2023 = db.get_team_features(
            "Manchester City",
            before_date="2024-01-01",
            n=5,
        )
        
        # Both should have data
        self.assertGreater(features_2022["xg_sample_count"], 0)
        self.assertGreater(features_2023["xg_sample_count"], 0)


class TestXGFeaturesConvenience(unittest.TestCase):
    """Test convenience functions."""

    def test_get_match_xg_features(self):
        """Should get match features via convenience function."""
        features = get_match_xg_features(
            home_team="Manchester City",
            away_team="Liverpool",
        )
        
        self.assertIn("home_xg_for_avg5", features)
        self.assertIn("away_xg_for_avg5", features)
        self.assertIn("xg_attack_diff", features)


class TestXGFeaturesIntegration(unittest.TestCase):
    """Test xG features integration with XGBoost model."""

    def test_xgboost_xg_model_feature_order(self):
        """Should have correct feature order with xG features."""
        from v24_app.models.xgboost_xg import XGBoostWithXGModel
        
        # Check that xG features are added
        base_count = 38  # Original feature count
        xg_count = 15    # xG feature count
        
        self.assertEqual(
            len(XGBoostWithXGModel.FEATURE_ORDER),
            base_count + xg_count,
        )
        
        # Check xG features are present
        xg_features = [
            "home_xg_for_avg5",
            "xg_attack_diff",
            "xg_defense_diff",
        ]
        for feature in xg_features:
            self.assertIn(feature, XGBoostWithXGModel.FEATURE_ORDER)

    def test_xgboost_xg_model_default_features(self):
        """Should provide default xG features."""
        from v24_app.models.xgboost_xg import XGBoostWithXGModel
        
        defaults = XGBoostWithXGModel._default_xg_features()
        
        self.assertEqual(len(defaults), 15)
        self.assertEqual(defaults["home_xg_for_avg5"], 1.3)
        self.assertEqual(defaults["xg_attack_diff"], 0.0)


if __name__ == "__main__":
    unittest.main()
