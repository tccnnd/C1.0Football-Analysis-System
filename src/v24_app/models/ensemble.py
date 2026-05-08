from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .elo_rating import EloRatingEngine
from .poisson import PoissonOutcome, PoissonScoreEngine


ProbabilityTriple = tuple[float, float, float]


@dataclass(frozen=True)
class EnsembleContext:
    market_probs: ProbabilityTriple
    home_rating: float
    away_rating: float
    market_draw_prob: float
    league_strength: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelOutput:
    key: str
    probabilities: ProbabilityTriple
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnsembleOutput:
    probabilities: ProbabilityTriple
    components: dict[str, ModelOutput]
    effective_weights: dict[str, float]


class ProbabilityModel(Protocol):
    key: str

    def predict(self, context: EnsembleContext) -> ModelOutput:
        ...


class MarketProbabilityModel:
    key = "market"

    def predict(self, context: EnsembleContext) -> ModelOutput:
        return ModelOutput(key=self.key, probabilities=context.market_probs)


class EloProbabilityModel:
    key = "elo"

    def __init__(self, engine: EloRatingEngine) -> None:
        self.engine = engine

    def predict(self, context: EnsembleContext) -> ModelOutput:
        snapshot = self.engine.from_ratings(
            home_rating=context.home_rating,
            away_rating=context.away_rating,
            implied_draw=context.market_draw_prob,
        )
        probs = (snapshot.home_win, snapshot.draw, snapshot.away_win)
        return ModelOutput(
            key=self.key,
            probabilities=probs,
            metadata={"elo_snapshot": snapshot},
        )


class PoissonProbabilityModel:
    key = "poisson"

    def __init__(self, engine: PoissonScoreEngine) -> None:
        self.engine = engine

    def predict(self, context: EnsembleContext) -> ModelOutput:
        outcome = self.engine.predict(
            home_rating=context.home_rating,
            away_rating=context.away_rating,
            market_draw_prob=context.market_draw_prob,
            league_strength=context.league_strength,
        )
        probs = (outcome.home_win, outcome.draw, outcome.away_win)
        return ModelOutput(
            key=self.key,
            probabilities=probs,
            metadata={"poisson_outcome": outcome},
        )


class WeightedEnsembleEngine:
    """Lightweight ensemble engine with model-level pluggability."""

    def __init__(self, weights: dict[str, float]) -> None:
        self.weights = dict(weights)

    def set_weights(self, weights: dict[str, float]) -> None:
        self.weights = dict(weights)

    def get_weights(self) -> dict[str, float]:
        return dict(self.weights)

    @staticmethod
    def _normalize_probs(probs: ProbabilityTriple) -> ProbabilityTriple:
        home, draw, away = probs
        total = max(home + draw + away, 1e-9)
        return home / total, draw / total, away / total

    @staticmethod
    def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
        total = sum(max(weight, 0.0) for weight in weights.values())
        if total <= 0:
            return {key: 1.0 / max(len(weights), 1) for key in weights}
        return {key: max(weight, 0.0) / total for key, weight in weights.items()}

    def predict(self, context: EnsembleContext, models: list[ProbabilityModel]) -> EnsembleOutput:
        components: dict[str, ModelOutput] = {}
        weighted_map: dict[str, float] = {}

        for model in models:
            output = model.predict(context)
            output.probabilities = self._normalize_probs(output.probabilities)
            components[output.key] = output
            weighted_map[output.key] = self.weights.get(output.key, 0.0)

        effective_weights = self._normalize_weights(weighted_map)
        blend_home = 0.0
        blend_draw = 0.0
        blend_away = 0.0
        for key, output in components.items():
            w = effective_weights.get(key, 0.0)
            home, draw, away = output.probabilities
            blend_home += home * w
            blend_draw += draw * w
            blend_away += away * w

        probabilities = self._normalize_probs((blend_home, blend_draw, blend_away))
        return EnsembleOutput(
            probabilities=probabilities,
            components=components,
            effective_weights=effective_weights,
        )


def get_poisson_outcome(output: ModelOutput) -> PoissonOutcome | None:
    value = output.metadata.get("poisson_outcome")
    return value if isinstance(value, PoissonOutcome) else None
