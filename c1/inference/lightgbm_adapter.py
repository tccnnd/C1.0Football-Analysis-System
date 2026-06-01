"""
C1.0 LightGBM 适配器

加载 data/models/lgbm_c1_match_outcome.txt 模型文件，
用欧赔+亚赔+ELO 特征进行 1X2 预测。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import InferenceComponent, InferenceInput

try:
    import lightgbm as lgb
    import numpy as np
    _LGB_AVAILABLE = True
except ImportError:
    _LGB_AVAILABLE = False


@dataclass(slots=True)
class LightGBMAvailability:
    available: bool
    reason: str


def _safe_float(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "") else d
    except Exception:
        return d


class C1LightGBMAdapter:
    def __init__(self, project_root: str | Path | None = None) -> None:
        self._model = None
        self._meta: dict[str, Any] = {}
        self._elo_ratings: dict[str, float] = {}

        if project_root is None:
            project_root = Path(__file__).resolve().parents[2]
        self._root = Path(project_root)
        self._model_file = self._root / "data" / "models" / "lgbm_c1_match_outcome.txt"
        self._meta_file = self._root / "data" / "models" / "lgbm_c1_match_outcome.meta.json"
        self._elo_file = self._root / "data" / "state" / "foot_elo_ratings.json"

        self._load()

    def _load(self) -> None:
        if not _LGB_AVAILABLE:
            return
        if not self._model_file.exists():
            return
        try:
            self._model = lgb.Booster(model_file=str(self._model_file))
        except Exception:
            self._model = None
            return
        if self._meta_file.exists():
            try:
                self._meta = json.loads(self._meta_file.read_text(encoding="utf-8"))
            except Exception:
                self._meta = {}
        if self._elo_file.exists():
            try:
                data = json.loads(self._elo_file.read_text(encoding="utf-8"))
                self._elo_ratings = data.get("ratings", {})
            except Exception:
                self._elo_ratings = {}

    def get_availability(self) -> LightGBMAvailability:
        if not _LGB_AVAILABLE:
            return LightGBMAvailability(available=False, reason="lightgbm_not_installed")
        if self._model is None:
            return LightGBMAvailability(available=False, reason="model_file_missing")
        return LightGBMAvailability(available=True, reason="ok")

    def infer(self, inference_input: InferenceInput) -> InferenceComponent:
        availability = self.get_availability()
        if not availability.available:
            return InferenceComponent(
                name="lightgbm",
                probabilities={"home": 0.0, "draw": 0.0, "away": 0.0},
                metadata={"available": False, "reason": availability.reason},
            )

        features = self._build_features(inference_input)
        try:
            proba = self._model.predict([features])[0]
            # proba: [home, draw, away]
            home, draw, away = float(proba[0]), float(proba[1]), float(proba[2])
            total = max(home + draw + away, 1e-9)
            probabilities = {
                "home": round(home / total, 6),
                "draw": round(draw / total, 6),
                "away": round(away / total, 6),
            }
        except Exception as e:
            return InferenceComponent(
                name="lightgbm",
                probabilities={"home": 0.0, "draw": 0.0, "away": 0.0},
                metadata={"available": True, "error": str(e)},
            )

        return InferenceComponent(
            name="lightgbm",
            probabilities=probabilities,
            metadata={
                "available": True,
                "model_version": self._meta.get("version", "v1"),
                "test_accuracy": self._meta.get("test_accuracy"),
            },
        )

    def _build_features(self, inp: InferenceInput) -> list[float]:
        """构建与训练时一致的 30 维特征向量"""
        fields = inp.feature_fields or {}
        meta = inp.metadata or {}

        # 欧赔（从 odds 字段）
        esp3 = _safe_float(meta.get("opening_odds_home") or fields.get("opening_odds_home"), inp.odds_home)
        esp1 = _safe_float(meta.get("opening_odds_draw") or fields.get("opening_odds_draw"), inp.odds_draw)
        esp0 = _safe_float(meta.get("opening_odds_away") or fields.get("opening_odds_away"), inp.odds_away)
        eep3 = inp.odds_home
        eep1 = inp.odds_draw
        eep0 = inp.odds_away

        # 欧赔隐含概率
        eh = 1.0 / max(eep3, 1.01)
        ed = 1.0 / max(eep1, 1.01)
        ea = 1.0 / max(eep0, 1.01)
        total = eh + ed + ea
        euro_home_prob = eh / total
        euro_draw_prob = ed / total
        euro_away_prob = ea / total
        euro_overround = total
        euro_return_rate = 1.0 / max(total, 0.01)

        # 欧赔变动
        euro_home_move = (eep3 - esp3) / max(esp3, 1.01)
        euro_draw_move = (eep1 - esp1) / max(esp1, 1.01)
        euro_away_move = (eep0 - esp0) / max(esp0, 1.01)

        # 亚赔（从 foot 信号或 feature_fields）
        aslb = _safe_float(fields.get("foot_asia_let_ball_opening") or fields.get("handicap_line"), 0.0)
        aelb = _safe_float(fields.get("foot_asia_let_ball_instant") or fields.get("handicap_line"), aslb)
        asia_let_ball_move = aelb - aslb
        asp3 = _safe_float(fields.get("asia_sp3"), 0.9)
        asp0 = _safe_float(fields.get("asia_sp0"), 0.9)
        aep3 = _safe_float(fields.get("asia_ep3"), asp3)
        aep0 = _safe_float(fields.get("asia_ep0"), asp0)
        asia_home_move = (aep3 - asp3) / max(asp3, 0.01)
        asia_away_move = (aep0 - asp0) / max(asp0, 0.01)

        # ELO
        home_team = str(fields.get("home_team") or meta.get("home_team") or "")
        away_team = str(fields.get("away_team") or meta.get("away_team") or "")
        home_elo = self._elo_ratings.get(home_team, inp.home_rating)
        away_elo = self._elo_ratings.get(away_team, inp.away_rating)
        elo_diff = home_elo - away_elo
        elo_diff_abs = abs(elo_diff)

        # 综合
        market_balance = abs(euro_home_prob - euro_away_prob)

        return [
            esp3, esp1, esp0, eep3, eep1, eep0,
            euro_home_prob, euro_draw_prob, euro_away_prob,
            euro_overround, euro_return_rate,
            euro_home_move, euro_draw_move, euro_away_move,
            aslb, aelb, asia_let_ball_move,
            asp3, asp0, aep3, aep0,
            asia_home_move, asia_away_move,
            home_elo, away_elo, elo_diff, elo_diff_abs,
            euro_home_prob, euro_away_prob, market_balance,
        ]
