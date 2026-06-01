from __future__ import annotations

from pathlib import Path

from .baseline import BaselineInferenceEngine
from .calibration import load_ensemble_calibration
from .lightgbm_adapter import C1LightGBMAdapter
from .schema import InferenceComponent, InferenceInput, InferenceResult
from .xgb_adapter import C1XGBoostAdapter


def _normalize_probabilities(probabilities: dict[str, float]) -> dict[str, float]:
    home = max(float(probabilities.get("home", 0.0)), 0.0)
    draw = max(float(probabilities.get("draw", 0.0)), 0.0)
    away = max(float(probabilities.get("away", 0.0)), 0.0)
    total = max(home + draw + away, 1e-9)
    return {
        "home": round(home / total, 6),
        "draw": round(draw / total, 6),
        "away": round(away / total, 6),
    }


def _blend_components(components: list[InferenceComponent], weights: dict[str, float]) -> tuple[dict[str, float], dict[str, float]]:
    prepared = {name: max(float(weights.get(name, 0.0)), 0.0) for name in weights}
    total_weight = sum(prepared.values())
    if total_weight <= 0:
        total_weight = 1.0
    effective_weights = {name: round(weight / total_weight, 6) for name, weight in prepared.items()}
    home = 0.0
    draw = 0.0
    away = 0.0
    by_name = {component.name: component for component in components}
    for name, weight in effective_weights.items():
        component = by_name.get(name)
        if component is None:
            continue
        home += float(component.probabilities.get("home", 0.0)) * weight
        draw += float(component.probabilities.get("draw", 0.0)) * weight
        away += float(component.probabilities.get("away", 0.0)) * weight
    return _normalize_probabilities({"home": home, "draw": draw, "away": away}), effective_weights


def _confidence(probabilities: dict[str, float]) -> tuple[str, float, float]:
    ordered = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
    predicted_side = ordered[0][0]
    top = float(ordered[0][1])
    second = float(ordered[1][1]) if len(ordered) > 1 else 0.0
    margin = max(top - second, 0.0)
    # Fix 1: 置信度以 top_prob 为主导，margin 作为小幅修正。
    # 旧公式 0.65*top + 0.35*margin 会系统性压缩置信度约15-20%，
    # 导致高准策略门槛过滤掉大量真正高概率的预测。
    # 新公式：top 占 85%，margin 占 15%，保持置信度与原始概率的线性关系。
    confidence = min(1.0, max(0.0, 0.85 * top + 0.15 * margin))
    return predicted_side, round(confidence, 6), round(margin, 6)


def _entropy(probabilities: dict[str, float]) -> float:
    from math import log2

    value = 0.0
    for item in probabilities.values():
        if item > 0:
            value -= float(item) * log2(float(item))
    return round(value, 6)


def _ev_by_side(probabilities: dict[str, float], inference_input: InferenceInput) -> dict[str, float]:
    odds = {
        "home": float(inference_input.odds_home),
        "draw": float(inference_input.odds_draw),
        "away": float(inference_input.odds_away),
    }
    return {
        side: round(float(probabilities.get(side, 0.0)) * max(odds[side], 1.0) - 1.0, 6)
        for side in ("home", "draw", "away")
    }


class C1InferenceEngine:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.baseline = BaselineInferenceEngine()
        self.xgb = C1XGBoostAdapter(self.project_root)
        self.lightgbm = C1LightGBMAdapter(self.project_root)

    def infer(
        self,
        inference_input: InferenceInput,
        *,
        enable_xgboost: bool = True,
        enable_lightgbm: bool = False,
    ) -> InferenceResult:
        calibration = load_ensemble_calibration(self.project_root)
        weights = calibration.weights_for_league(str(inference_input.feature_fields.get("league", "")))

        baseline = self.baseline.infer(
            inference_input,
            weights={key: weights.get(key, 0.0) for key in ("market", "elo", "poisson")},
        )
        components = list(baseline.components)

        if enable_xgboost:
            xgb_component = self.xgb.infer(inference_input)
            # Fix 3: fallback时排除XGBoost，避免市场信号被重复计算。
            # fallback输出本质上是市场+ELO的线性调整，若仍以15%权重参与
            # ensemble，等于把市场信号计入了两次，放大市场依赖。
            xgb_is_fallback = bool(xgb_component.metadata.get("xgb_fallback", True))
            if not xgb_is_fallback:
                components.append(xgb_component)
            else:
                enable_xgboost = False  # 标记为未实际使用，不加入blend_weights
        if enable_lightgbm:
            lgbm_result = self.lightgbm.infer(inference_input)
            if lgbm_result.metadata.get("available"):
                components.append(lgbm_result)

        blend_weights = {
            "market": weights.get("market", 0.0),
            "elo": weights.get("elo", 0.0),
            "poisson": weights.get("poisson", 0.0),
            "dixon_coles": weights.get("dixon_coles", 0.10),
        }
        if enable_xgboost:
            blend_weights["xgboost"] = weights.get("xgboost", 0.0)
        if enable_lightgbm and any(c.name == "lightgbm" for c in components):
            blend_weights["lightgbm"] = weights.get("lightgbm", weights.get("xgboost", 0.10))

        probabilities, effective_weights = _blend_components(components, blend_weights)
        predicted_side, confidence, margin = _confidence(probabilities)
        return InferenceResult(
            match_id=inference_input.match_id,
            model_name="c1.phase4.inference",
            raw_probabilities=probabilities,
            predicted_side=predicted_side,
            confidence=confidence,
            margin=margin,
            entropy=_entropy(probabilities),
            ev_by_side=_ev_by_side(probabilities, inference_input),
            components=components,
            calibration={
                "mode": calibration.mode,
                "updated_at": calibration.updated_at,
                "source_path": calibration.source_path,
                "weights": effective_weights,
            },
            metadata={
                "expected_goals": baseline.expected_goals,
                "baseline_entropy": baseline.entropy,
                "xgboost_enabled": enable_xgboost,
                "lightgbm_enabled": enable_lightgbm,
            },
        )

