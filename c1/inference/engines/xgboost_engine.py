from __future__ import annotations

"""
C1.0 独立 XGBoost 推理引擎

从 V24 的 xgboost_v0.XGBoostProbabilityModel 提取的纯推理副本。
关键点：
- 直接从 data/models/xgb_v0_match_outcome.json 加载训练产物
- FEATURE_ORDER 与 V24 完全一致，保证 shadow 对比有效
- 不包含训练/在线热身/监控副作用（推理层只输出概率）
- xgboost / numpy 缺失或模型不兼容时，回退到与 V24 一致的市场+评分启发式
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import numpy as np
except Exception:  # pragma: no cover - 环境相关
    np = None

try:
    import xgboost as xgb
except Exception:  # pragma: no cover - 环境相关
    xgb = None


ProbabilityTriple = tuple[float, float, float]


# 与 V24 xgboost_v0.XGBoostProbabilityModel.FEATURE_ORDER 严格一致。
# 任何顺序/字段变更都会使已训练模型不兼容，并破坏 shadow 对比。
FEATURE_ORDER = [
    "market_home", "market_draw", "market_away",
    "odds_home", "odds_draw", "odds_away",
    "home_rating", "away_rating", "rating_diff", "rating_gap_abs",
    "league_strength", "match_minutes", "is_weekend",
    "opening_odds_home", "opening_odds_draw", "opening_odds_away",
    "return_rate", "market_overround",
    "home_odds_drop", "draw_odds_drop", "away_odds_drop",
    "kelly_home", "kelly_draw", "kelly_away", "kelly_draw_edge",
    "market_balance",
    "home_recent_match_count", "away_recent_match_count",
    "home_recent_points_pg", "away_recent_points_pg", "recent_points_diff",
    "home_recent_goal_diff_pg", "away_recent_goal_diff_pg", "recent_goal_diff_diff",
    "home_recent_goals_for_pg", "away_recent_goals_for_pg",
    "home_recent_win_rate", "away_recent_win_rate",
]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _normalize(probs: ProbabilityTriple) -> ProbabilityTriple:
    home, draw, away = probs
    total = max(home + draw + away, 1e-9)
    return home / total, draw / total, away / total


def _parse_match_minutes(match_time: str) -> float:
    if not match_time or ":" not in match_time:
        return 0.0
    chunks = match_time.split(":")
    if len(chunks) != 2:
        return 0.0
    try:
        return float(int(chunks[0]) * 60 + int(chunks[1]))
    except Exception:
        return 0.0


def _is_weekend(match_date: str) -> float:
    try:
        return 1.0 if datetime.strptime(match_date, "%Y-%m-%d").weekday() >= 5 else 0.0
    except Exception:
        return 0.0


def _compute_return_rate(oh: float, od: float, oa: float, raw: float = 0.0) -> float:
    if raw > 0.0:
        return raw
    implied = 1.0 / max(oh, 1.01) + 1.0 / max(od, 1.01) + 1.0 / max(oa, 1.01)
    return 1.0 / max(implied, 1e-9)


def _market_intent_features(
    *, odds_home: float, odds_draw: float, odds_away: float,
    opening_odds_home: float = 0.0, opening_odds_draw: float = 0.0, opening_odds_away: float = 0.0,
    return_rate: float = 0.0, kelly_home: float = 0.0, kelly_draw: float = 0.0, kelly_away: float = 0.0,
) -> dict[str, float]:
    """复制 v24_app.market_features.build_market_intent_feature_map（独立化）。"""
    ch = max(_safe_float(odds_home), 1.01)
    cd = max(_safe_float(odds_draw), 1.01)
    ca = max(_safe_float(odds_away), 1.01)
    oh = _safe_float(opening_odds_home)
    od = _safe_float(opening_odds_draw)
    oa = _safe_float(opening_odds_away)
    rate = _compute_return_rate(ch, cd, ca, raw=_safe_float(return_rate))
    ih, idr, ia = 1.0 / ch, 1.0 / cd, 1.0 / ca
    itot = max(ih + idr + ia, 1e-9)
    mh, md, ma = ih / itot, idr / itot, ia / itot
    kh, kd, ka = _safe_float(kelly_home), _safe_float(kelly_draw), _safe_float(kelly_away)
    kelly_draw_edge = ((kh + ka) / 2.0) - kd if min(kh, kd, ka) > 0.0 else 0.0
    return {
        "opening_odds_home": round(oh, 4),
        "opening_odds_draw": round(od, 4),
        "opening_odds_away": round(oa, 4),
        "return_rate": round(rate, 4),
        "market_overround": round(max(0.0, 1.0 - rate), 4),
        "home_odds_drop": round((oh - ch) if oh > 1.0 else 0.0, 4),
        "draw_odds_drop": round((od - cd) if od > 1.0 else 0.0, 4),
        "away_odds_drop": round((oa - ca) if oa > 1.0 else 0.0, 4),
        "kelly_home": round(kh, 4),
        "kelly_draw": round(kd, 4),
        "kelly_away": round(ka, 4),
        "kelly_draw_edge": round(kelly_draw_edge, 4),
        "market_balance": round(1.0 - abs(mh - ma), 4),
    }


class XGBoostInferenceEngine:
    """纯推理引擎：从 JSON 产物加载模型，输出 1X2 概率。无训练副作用。"""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.model_dir = self.project_root / "data" / "models"
        self.model_file = self.model_dir / "xgb_v0_match_outcome.json"
        self.meta_file = self.model_dir / "xgb_v0_match_outcome.meta.json"
        self._model: Any = None
        self._model_ready = False
        self._lock = threading.RLock()

    # ── 元数据 / 兼容性 ─────────────────────────────────────────────
    def _load_meta(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.meta_file.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _is_compatible(self, meta: dict[str, Any] | None = None) -> bool:
        payload = meta if isinstance(meta, dict) else self._load_meta()
        order = payload.get("feature_order")
        return bool(isinstance(order, list) and order == FEATURE_ORDER)

    # ── 特征构建（与 V24 _feature_map 等价）─────────────────────────
    def _feature_map(self, inference_input: "Any") -> dict[str, float]:
        meta = inference_input.feature_fields or {}
        oh = _safe_float(inference_input.odds_home)
        od = _safe_float(inference_input.odds_draw)
        oa = _safe_float(inference_input.odds_away)
        ih = 1.0 / max(oh, 1.01)
        idr = 1.0 / max(od, 1.01)
        ia = 1.0 / max(oa, 1.01)
        itot = max(ih + idr + ia, 1e-9)
        market_home, market_draw, market_away = ih / itot, idr / itot, ia / itot
        rating_diff = inference_input.home_rating - inference_input.away_rating
        feature_map: dict[str, float] = {
            "market_home": market_home,
            "market_draw": market_draw,
            "market_away": market_away,
            "odds_home": oh,
            "odds_draw": od,
            "odds_away": oa,
            "home_rating": inference_input.home_rating,
            "away_rating": inference_input.away_rating,
            "rating_diff": rating_diff,
            "rating_gap_abs": abs(rating_diff),
            "league_strength": inference_input.league_strength,
            "match_minutes": _parse_match_minutes(str(meta.get("match_time", ""))),
            "is_weekend": _is_weekend(str(meta.get("match_date", ""))),
        }
        feature_map.update(_market_intent_features(
            odds_home=oh, odds_draw=od, odds_away=oa,
            opening_odds_home=meta.get("opening_odds_home", 0.0),
            opening_odds_draw=meta.get("opening_odds_draw", 0.0),
            opening_odds_away=meta.get("opening_odds_away", 0.0),
            return_rate=meta.get("return_rate", 0.0),
            kelly_home=meta.get("kelly_home", 0.0),
            kelly_draw=meta.get("kelly_draw", 0.0),
            kelly_away=meta.get("kelly_away", 0.0),
        ))
        for name in FEATURE_ORDER:
            if name not in feature_map:
                feature_map[name] = _safe_float(meta.get(name), default=0.0)
        return feature_map

    def _feature_vector(self, feature_map: dict[str, float]) -> list[float]:
        return [_safe_float(feature_map.get(name, 0.0)) for name in FEATURE_ORDER]


    # ── 模型加载 / 预测 ─────────────────────────────────────────────
    def _load_model(self) -> None:
        with self._lock:
            if self._model is not None or self._model_ready:
                return
            if xgb is None or not self.model_file.exists():
                return
            if not self._is_compatible():
                self._model = None
                self._model_ready = False
                return
            try:
                model = xgb.XGBClassifier(objective="multi:softprob", num_class=3)
                model.load_model(str(self.model_file))
                self._model = model
                self._model_ready = True
            except Exception:
                self._model = None
                self._model_ready = False

    def _predict_with_model(self, feature_map: dict[str, float]) -> ProbabilityTriple | None:
        if np is None:
            return None
        self._load_model()
        with self._lock:
            model = self._model
        if model is None:
            return None
        try:
            vector = np.array([self._feature_vector(feature_map)], dtype=float)
            probs = model.predict_proba(vector)[0]
            if len(probs) != 3:
                return None
            return float(probs[0]), float(probs[1]), float(probs[2])
        except Exception:
            return None

    def _fallback_probs(self, inference_input: "Any", feature_map: dict[str, float]) -> ProbabilityTriple:
        """与 V24 _fallback_probs 等价的启发式回退。"""
        mh = feature_map["market_home"]
        md = feature_map["market_draw"]
        ma = feature_map["market_away"]
        rating_adjust = (inference_input.home_rating - inference_input.away_rating) / 2200.0
        oh = feature_map.get("odds_home", 0.0)
        oa = feature_map.get("odds_away", 0.0)
        odds_adjust = (oa - oh) / 40.0 if oh > 0 and oa > 0 else 0.0
        home = mh + rating_adjust + odds_adjust
        away = ma - rating_adjust - odds_adjust
        draw = md + max(0.0, 0.04 - abs(rating_adjust) * 0.5)
        return _normalize((home, draw, away))

    def predict(self, inference_input: "Any") -> dict[str, Any]:
        """返回 {'probabilities': (h,d,a), 'metadata': {...}}。纯推理，无副作用。"""
        feature_map = self._feature_map(inference_input)
        probs = self._predict_with_model(feature_map)
        using_fallback = probs is None
        if probs is None:
            probs = self._fallback_probs(inference_input, feature_map)
        probs = _normalize(probs)
        return {
            "probabilities": probs,
            "metadata": {
                "xgb_features": feature_map,
                "xgb_model_ready": self._model_ready,
                "xgb_fallback": using_fallback,
            },
        }

    def get_status(self) -> dict[str, Any]:
        meta = self._load_meta()
        compatible = self._is_compatible(meta) if meta else (not self.model_file.exists())
        return {
            "model_exists": self.model_file.exists(),
            "model_ready": bool((self._model_ready or self.model_file.exists()) and compatible),
            "model_compatible": compatible,
            "model_updated_at": meta.get("updated_at"),
            "xgboost_available": xgb is not None and np is not None,
            "feature_count": len(FEATURE_ORDER),
        }
