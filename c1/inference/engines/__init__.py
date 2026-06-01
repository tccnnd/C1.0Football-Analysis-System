"""
C1.0 独立推理引擎

这些是从 V24 提取的核心算法副本，使 C1.0 可以独立运行。
"""
from .elo import EloRatingEngine, EloSnapshot, EloUpdate
from .poisson import PoissonScoreEngine, PoissonOutcome
from .dixon_coles import DixonColesEngine, dixon_coles_correction
from .xgboost_engine import XGBoostInferenceEngine, FEATURE_ORDER as XGB_FEATURE_ORDER

__all__ = [
    "EloRatingEngine",
    "EloSnapshot",
    "EloUpdate",
    "PoissonScoreEngine",
    "PoissonOutcome",
    "DixonColesEngine",
    "dixon_coles_correction",
    "XGBoostInferenceEngine",
    "XGB_FEATURE_ORDER",
]
