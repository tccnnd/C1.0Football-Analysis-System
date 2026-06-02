"""
XGBoost Model with xG Features

Enhanced XGBoost model that includes 15 xG features from Understat data.
Expected to improve high-confidence prediction accuracy from 75% to 78-80%.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .xgboost_v0 import XGBoostProbabilityModel
from .ensemble import EnsembleContext


class XGBoostWithXGModel(XGBoostProbabilityModel):
    """XGBoost model enhanced with xG features."""

    key = "xgboost_xg"

    # Extended feature order with 15 xG features
    FEATURE_ORDER = XGBoostProbabilityModel.FEATURE_ORDER + [
        # Home team xG features
        "home_xg_for_avg5",
        "home_xg_against_avg5",
        "home_xg_overperform5",
        "home_xg_defense_overp5",
        "home_xg_trend5",
        # Away team xG features
        "away_xg_for_avg5",
        "away_xg_against_avg5",
        "away_xg_overperform5",
        "away_xg_defense_overp5",
        "away_xg_trend5",
        # Differential features (most important)
        "xg_attack_diff",
        "xg_defense_diff",
        "xg_overperform_diff",
        # Data quality indicators
        "xg_home_sample_count",
        "xg_away_sample_count",
    ]

    def __init__(
        self,
        project_dir: Path,
        min_train_samples: int = 30,
        retrain_interval_minutes: int = 30,
    ) -> None:
        super().__init__(
            project_dir=project_dir,
            min_train_samples=min_train_samples,
            retrain_interval_minutes=retrain_interval_minutes,
        )
        # Override file paths for xG-enhanced model
        self.model_file = self.model_dir / "xgb_xg_match_outcome.json"
        self.meta_file = self.model_dir / "xgb_xg_match_outcome.meta.json"

        # Lazy-load xG database
        self._xg_db = None

    @property
    def xg_db(self):
        """Lazy-load xG database."""
        if self._xg_db is None:
            from v24_app.features.xg_features import get_xg_database
            self._xg_db = get_xg_database()
        return self._xg_db

    def _feature_map(self, context: EnsembleContext) -> dict[str, float]:
        """Build feature map with xG features."""
        # Get base features from parent
        feature_map = super()._feature_map(context)

        # Add xG features
        metadata = context.metadata or {}
        home_team = str(metadata.get("home_team", ""))
        away_team = str(metadata.get("away_team", ""))
        match_date = str(metadata.get("match_date", ""))

        if home_team and away_team:
            try:
                xg_features = self.xg_db.build_match_xg_features(
                    home_team=home_team,
                    away_team=away_team,
                    match_date=match_date if match_date else None,
                )
                feature_map.update(xg_features)
            except Exception:
                # If xG features fail, use defaults
                xg_features = self._default_xg_features()
                feature_map.update(xg_features)
        else:
            # No team names available, use defaults
            xg_features = self._default_xg_features()
            feature_map.update(xg_features)

        return feature_map

    @staticmethod
    def _default_xg_features() -> dict[str, float]:
        """Default xG features when data is unavailable."""
        return {
            "home_xg_for_avg5": 1.3,
            "home_xg_against_avg5": 1.3,
            "home_xg_overperform5": 0.0,
            "home_xg_defense_overp5": 0.0,
            "home_xg_trend5": 0.0,
            "away_xg_for_avg5": 1.3,
            "away_xg_against_avg5": 1.3,
            "away_xg_overperform5": 0.0,
            "away_xg_defense_overp5": 0.0,
            "away_xg_trend5": 0.0,
            "xg_attack_diff": 0.0,
            "xg_defense_diff": 0.0,
            "xg_overperform_diff": 0.0,
            "xg_home_sample_count": 0.0,
            "xg_away_sample_count": 0.0,
        }

    @staticmethod
    def build_estimator() -> Any:
        """Build XGBoost estimator with adjusted hyperparameters for more features."""
        try:
            import xgboost as xgb
        except ImportError:
            return None

        # Slightly deeper trees to handle 15 additional features
        return xgb.XGBClassifier(
            objective="multi:softprob",
            num_class=3,
            n_estimators=180,  # Increased from 160
            max_depth=5,       # Increased from 4
            learning_rate=0.05,  # Slightly reduced for stability
            subsample=0.9,
            colsample_bytree=0.85,  # Reduced to prevent overfitting
            eval_metric="mlogloss",
            random_state=42,
            tree_method="hist",
        )
