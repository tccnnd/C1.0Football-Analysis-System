from __future__ import annotations

from pathlib import Path
from typing import Any

from .schema import InferenceComponent, InferenceInput

# C1.0 独立 XGBoost 引擎：直接从 data/models/*.json 加载训练产物，
# 不再依赖 v24_app.models.xgboost_v0（Phase 7 独立性）。
from .engines.xgboost_engine import XGBoostInferenceEngine


def _normalize_probabilities(home: float, draw: float, away: float) -> dict[str, float]:
    total = max(home + draw + away, 1e-9)
    return {
        "home": round(home / total, 6),
        "draw": round(draw / total, 6),
        "away": round(away / total, 6),
    }


class C1XGBoostAdapter:
    """Inference-layer 适配器，桥接独立 XGBoost 引擎到 InferenceComponent。"""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.engine = XGBoostInferenceEngine(self.project_root)

    def infer(self, inference_input: InferenceInput) -> InferenceComponent:
        output = self.engine.predict(inference_input)
        home, draw, away = output["probabilities"]
        return InferenceComponent(
            name="xgboost",
            probabilities=_normalize_probabilities(home, draw, away),
            metadata=dict(output["metadata"]),
        )

    def get_training_status(self) -> dict[str, Any]:
        return self.engine.get_status()
