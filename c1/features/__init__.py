"""C1.0 Feature Layer."""

from .governance_features import (
    build_governance_feature_fields,
    build_governance_feature_snapshot,
    compute_chaos_score,
    compute_info_quality,
    compute_line_move_against_model,
    compute_lineup_freshness_hours,
    compute_missing_elo_loss,
    compute_odds_move_against_model,
)
from .foot_features import (
    enrich_with_foot_signals,
    fetch_foot_signals,
    compute_foot_asia_signal_strength,
    compute_foot_euro_asia_conflict_score,
    compute_foot_fundamental_score,
    compute_foot_model_agreement,
)

__all__ = [
    "compute_info_quality",
    "compute_lineup_freshness_hours",
    "compute_missing_elo_loss",
    "compute_odds_move_against_model",
    "compute_line_move_against_model",
    "compute_chaos_score",
    "build_governance_feature_fields",
    "build_governance_feature_snapshot",
    # foot 信号
    "enrich_with_foot_signals",
    "fetch_foot_signals",
    "compute_foot_asia_signal_strength",
    "compute_foot_euro_asia_conflict_score",
    "compute_foot_fundamental_score",
    "compute_foot_model_agreement",
]

