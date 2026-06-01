from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_ENSEMBLE_WEIGHTS = {
    # Fix 2: 降低市场权重，提高ELO和Poisson的独立判断空间。
    # 旧权重 market=0.35 导致模型严重依赖市场共识，无法找到边际优势。
    # 高准策略本质是找市场定价错误的场次，但模型若是市场的加权平均则无法做到。
    # 新权重：market降至0.25，elo升至0.35，poisson升至0.25，xgboost保持0.15。
    "market":   0.25,
    "elo":      0.35,
    "poisson":  0.25,
    "xgboost":  0.15,
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    prepared = {key: max(_safe_float(value, 0.0), 0.0) for key, value in weights.items()}
    total = sum(prepared.values())
    if total <= 0.0:
        size = max(len(prepared), 1)
        return {key: round(1.0 / size, 6) for key in prepared}
    return {key: round(value / total, 6) for key, value in prepared.items()}


@dataclass(slots=True)
class EnsembleCalibration:
    source_path: str | None
    updated_at: str | None
    mode: str
    weights: dict[str, float]
    league_weights: dict[str, dict[str, Any]] = field(default_factory=dict)

    def weights_for_league(self, league: str | None) -> dict[str, float]:
        if league and league in self.league_weights:
            payload = self.league_weights.get(league, {})
            raw = payload.get("weights", {}) if isinstance(payload, dict) else {}
            if isinstance(raw, dict) and raw:
                return _normalize_weights(
                    {key: _safe_float(raw.get(key), self.weights.get(key, 0.0)) for key in self.weights}
                )
        return dict(self.weights)


def load_ensemble_calibration(project_root: str | Path) -> EnsembleCalibration:
    root = Path(project_root)
    path = root / "data" / "models" / "ensemble_weights_v1.json"
    if not path.exists():
        return EnsembleCalibration(
            source_path=None,
            updated_at=None,
            mode="default",
            weights=_normalize_weights(dict(DEFAULT_ENSEMBLE_WEIGHTS)),
            league_weights={},
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}

    raw_weights = payload.get("weights", {}) if isinstance(payload, dict) else {}
    if not isinstance(raw_weights, dict) or not raw_weights:
        raw_weights = dict(DEFAULT_ENSEMBLE_WEIGHTS)
    raw_league_weights = payload.get("league_weights", {}) if isinstance(payload, dict) else {}
    league_weights = raw_league_weights if isinstance(raw_league_weights, dict) else {}
    return EnsembleCalibration(
        source_path=str(path),
        updated_at=payload.get("updated_at") if isinstance(payload, dict) else None,
        mode=str(payload.get("mode", "default")) if isinstance(payload, dict) else "default",
        weights=_normalize_weights(
            {key: _safe_float(raw_weights.get(key), DEFAULT_ENSEMBLE_WEIGHTS[key]) for key in DEFAULT_ENSEMBLE_WEIGHTS}
        ),
        league_weights=league_weights,
    )

