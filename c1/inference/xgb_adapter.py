from __future__ import annotations

from pathlib import Path
from typing import Any

from v24_app.models.ensemble import EnsembleContext
from v24_app.models.xgboost_v0 import XGBoostProbabilityModel

from .schema import InferenceComponent, InferenceInput


def _normalize_probabilities(home: float, draw: float, away: float) -> dict[str, float]:
    total = max(home + draw + away, 1e-9)
    return {
        "home": round(home / total, 6),
        "draw": round(draw / total, 6),
        "away": round(away / total, 6),
    }


class C1XGBoostAdapter:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.model = XGBoostProbabilityModel(self.project_root)

    def infer(self, inference_input: InferenceInput) -> InferenceComponent:
        market_home = 1.0 / max(float(inference_input.odds_home), 1.01)
        market_draw = 1.0 / max(float(inference_input.odds_draw), 1.01)
        market_away = 1.0 / max(float(inference_input.odds_away), 1.01)
        total = max(market_home + market_draw + market_away, 1e-9)
        context = EnsembleContext(
            market_probs=(market_home / total, market_draw / total, market_away / total),
            home_rating=inference_input.home_rating,
            away_rating=inference_input.away_rating,
            market_draw_prob=market_draw / total,
            league_strength=inference_input.league_strength,
            metadata={
                "match_id": inference_input.match_id,
                "odds_home": inference_input.odds_home,
                "odds_draw": inference_input.odds_draw,
                "odds_away": inference_input.odds_away,
                **inference_input.feature_fields,
                **inference_input.metadata,
            },
        )
        output = self.model.predict(context)
        return InferenceComponent(
            name="xgboost",
            probabilities=_normalize_probabilities(*output.probabilities),
            metadata=dict(output.metadata),
        )

    def get_training_status(self) -> dict[str, Any]:
        return self.model.get_training_status()

