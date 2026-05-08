from __future__ import annotations

from dataclasses import dataclass
from math import log2

from v24_app.models.elo_rating import EloRatingEngine
from v24_app.models.ensemble import (
    EloProbabilityModel,
    EnsembleContext,
    MarketProbabilityModel,
    PoissonProbabilityModel,
    WeightedEnsembleEngine,
)
from v24_app.models.poisson import PoissonScoreEngine

from .schema import InferenceComponent, InferenceInput


def _normalize_probabilities(home: float, draw: float, away: float) -> dict[str, float]:
    total = max(home + draw + away, 1e-9)
    return {
        "home": round(home / total, 6),
        "draw": round(draw / total, 6),
        "away": round(away / total, 6),
    }


def _base_market_probs(odds_home: float, odds_draw: float, odds_away: float) -> tuple[float, float, float]:
    home = 1.0 / max(float(odds_home), 1.01)
    draw = 1.0 / max(float(odds_draw), 1.01)
    away = 1.0 / max(float(odds_away), 1.01)
    total = max(home + draw + away, 1e-9)
    return home / total, draw / total, away / total


@dataclass(slots=True)
class BaselineInferenceOutput:
    fused_probabilities: dict[str, float]
    components: list[InferenceComponent]
    effective_weights: dict[str, float]
    expected_goals: float
    entropy: float


class BaselineInferenceEngine:
    def __init__(self) -> None:
        self.elo_engine = EloRatingEngine()
        self.poisson_engine = PoissonScoreEngine()
        self.market_model = MarketProbabilityModel()
        self.elo_model = EloProbabilityModel(self.elo_engine)
        self.poisson_model = PoissonProbabilityModel(self.poisson_engine)

    def infer(self, inference_input: InferenceInput, weights: dict[str, float]) -> BaselineInferenceOutput:
        market_probs = _base_market_probs(
            inference_input.odds_home,
            inference_input.odds_draw,
            inference_input.odds_away,
        )
        context = EnsembleContext(
            market_probs=market_probs,
            home_rating=inference_input.home_rating,
            away_rating=inference_input.away_rating,
            market_draw_prob=market_probs[1],
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
        ensemble = WeightedEnsembleEngine(weights=weights)
        result = ensemble.predict(
            context=context,
            models=[self.market_model, self.elo_model, self.poisson_model],
        )
        components = [
            InferenceComponent(
                name=name,
                probabilities=_normalize_probabilities(*output.probabilities),
                metadata=dict(output.metadata),
            )
            for name, output in result.components.items()
        ]
        fused = _normalize_probabilities(*result.probabilities)
        entropy = 0.0
        for value in fused.values():
            if value > 0:
                entropy -= value * log2(value)
        poisson_output = result.components.get("poisson")
        poisson_meta = poisson_output.metadata.get("poisson_outcome") if poisson_output is not None else None
        expected_goals = 0.0
        if poisson_meta is not None:
            expected_goals = float(getattr(poisson_meta, "home_lambda", 0.0) + getattr(poisson_meta, "away_lambda", 0.0))
        return BaselineInferenceOutput(
            fused_probabilities=fused,
            components=components,
            effective_weights=dict(result.effective_weights),
            expected_goals=round(expected_goals, 4),
            entropy=round(entropy, 6),
        )

