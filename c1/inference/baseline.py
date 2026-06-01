from __future__ import annotations

from dataclasses import dataclass, field
from math import log2
from typing import Any

# C1.0 独立引擎（不再依赖 v24_app）
from c1.inference.engines.elo import EloRatingEngine
from c1.inference.engines.poisson import PoissonScoreEngine
from c1.inference.engines.dixon_coles import DixonColesEngine

from .schema import InferenceComponent, InferenceInput


# ── 内联的轻量级 ensemble 组件（从 v24_app.models.ensemble 提取）──────────────

@dataclass(frozen=True)
class _EnsembleContext:
    market_probs: tuple[float, float, float]
    home_rating: float
    away_rating: float
    market_draw_prob: float
    league_strength: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class _ModelOutput:
    key: str
    probabilities: tuple[float, float, float]
    metadata: dict[str, Any] = field(default_factory=dict)


class _MarketModel:
    key = "market"
    def predict(self, ctx: _EnsembleContext) -> _ModelOutput:
        return _ModelOutput(key=self.key, probabilities=ctx.market_probs)


class _EloModel:
    key = "elo"
    def __init__(self, engine: EloRatingEngine):
        self.engine = engine
    def predict(self, ctx: _EnsembleContext) -> _ModelOutput:
        snap = self.engine.from_ratings(ctx.home_rating, ctx.away_rating, ctx.market_draw_prob)
        return _ModelOutput(key=self.key, probabilities=(snap.home_win, snap.draw, snap.away_win),
                           metadata={"elo_snapshot": snap})


class _PoissonModel:
    key = "poisson"
    def __init__(self, engine: PoissonScoreEngine):
        self.engine = engine
    def predict(self, ctx: _EnsembleContext) -> _ModelOutput:
        outcome = self.engine.predict(
            home_rating=ctx.home_rating, away_rating=ctx.away_rating,
            market_draw_prob=ctx.market_draw_prob, league_strength=ctx.league_strength,
        )
        return _ModelOutput(key=self.key, probabilities=(outcome.home_win, outcome.draw, outcome.away_win),
                           metadata={"poisson_outcome": outcome})


class _DixonColesModel:
    key = "dixon_coles"
    def __init__(self, engine: DixonColesEngine, poisson_engine: PoissonScoreEngine):
        self.engine = engine
        self.poisson_engine = poisson_engine
    def predict(self, ctx: _EnsembleContext) -> _ModelOutput:
        # 优先使用 xG 数据作为 lambda（更精确）
        xg_home = float(ctx.metadata.get("xg_home_for_avg", 0) or 0)
        xg_away = float(ctx.metadata.get("xg_away_for_avg", 0) or 0)
        xg_home_against = float(ctx.metadata.get("xg_home_against_avg", 0) or 0)
        xg_away_against = float(ctx.metadata.get("xg_away_against_avg", 0) or 0)

        if xg_home > 0 and xg_away > 0:
            # xG 校准：主队 lambda = (主队攻击力 + 客队防守弱点) / 2
            home_lambda = (xg_home + xg_away_against) / 2.0
            away_lambda = (xg_away + xg_home_against) / 2.0
            source = "xg_calibrated"
        else:
            # 降级：用 Poisson 引擎的 ELO 估算
            outcome = self.poisson_engine.predict(
                home_rating=ctx.home_rating, away_rating=ctx.away_rating,
                market_draw_prob=ctx.market_draw_prob, league_strength=ctx.league_strength,
            )
            home_lambda = outcome.home_lambda
            away_lambda = outcome.away_lambda
            source = "elo_fallback"

        probs = self.engine.predict(home_lambda, away_lambda)
        return _ModelOutput(
            key=self.key,
            probabilities=(probs["home"], probs["draw"], probs["away"]),
            metadata={
                "home_lambda": home_lambda,
                "away_lambda": away_lambda,
                "lambda_source": source,
            },
        )


def _norm_triple(probs: tuple[float, float, float]) -> tuple[float, float, float]:
    h, d, a = probs
    t = max(h + d + a, 1e-9)
    return h / t, d / t, a / t


def _blend(models: list, ctx: _EnsembleContext, weights: dict[str, float]):
    """简化的加权融合"""
    outputs = {m.key: m.predict(ctx) for m in models}
    for o in outputs.values():
        o.probabilities = _norm_triple(o.probabilities)
    total_w = sum(max(weights.get(k, 0), 0) for k in outputs)
    if total_w <= 0:
        total_w = 1.0
    eff_w = {k: max(weights.get(k, 0), 0) / total_w for k in outputs}
    h = sum(outputs[k].probabilities[0] * eff_w[k] for k in outputs)
    d = sum(outputs[k].probabilities[1] * eff_w[k] for k in outputs)
    a = sum(outputs[k].probabilities[2] * eff_w[k] for k in outputs)
    return _norm_triple((h, d, a)), outputs, eff_w


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
        self.dixon_coles_engine = DixonColesEngine()
        self._market = _MarketModel()
        self._elo = _EloModel(self.elo_engine)
        self._poisson = _PoissonModel(self.poisson_engine)
        self._dixon_coles = _DixonColesModel(self.dixon_coles_engine, self.poisson_engine)

    def infer(self, inference_input: InferenceInput, weights: dict[str, float]) -> BaselineInferenceOutput:
        market_probs = _base_market_probs(
            inference_input.odds_home,
            inference_input.odds_draw,
            inference_input.odds_away,
        )
        ctx = _EnsembleContext(
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
                # xG 特征传递给 Dixon-Coles 模型
                "xg_home_for_avg": inference_input.feature_fields.get("xg_home_for_avg", 0),
                "xg_away_for_avg": inference_input.feature_fields.get("xg_away_for_avg", 0),
                "xg_home_against_avg": inference_input.feature_fields.get("xg_home_against_avg", 0),
                "xg_away_against_avg": inference_input.feature_fields.get("xg_away_against_avg", 0),
            },
        )
        models = [self._market, self._elo, self._poisson, self._dixon_coles]
        blended, outputs, eff_w = _blend(models, ctx, weights)

        components = [
            InferenceComponent(
                name=name,
                probabilities=_normalize_probabilities(*output.probabilities),
                metadata=dict(output.metadata),
            )
            for name, output in outputs.items()
        ]
        fused = _normalize_probabilities(*blended)
        entropy = 0.0
        for value in fused.values():
            if value > 0:
                entropy -= value * log2(value)
        poisson_output = outputs.get("poisson")
        poisson_meta = poisson_output.metadata.get("poisson_outcome") if poisson_output else None
        expected_goals = 0.0
        if poisson_meta is not None:
            expected_goals = float(getattr(poisson_meta, "home_lambda", 0.0) + getattr(poisson_meta, "away_lambda", 0.0))
        return BaselineInferenceOutput(
            fused_probabilities=fused,
            components=components,
            effective_weights=dict(eff_w),
            expected_goals=round(expected_goals, 4),
            entropy=round(entropy, 6),
        )

