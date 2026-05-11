from __future__ import annotations

from collections import Counter
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    import numpy as np
except Exception:
    np = None

try:
    import xgboost as xgb
except Exception:
    xgb = None

from .ensemble import EnsembleContext, ModelOutput, ProbabilityTriple
from ..market_features import build_market_intent_feature_map


class XGBoostProbabilityModel:
    """XGBoost v0 probability adapter with online sample warm-up."""

    key = "xgboost"

    FEATURE_ORDER = [
        "market_home",
        "market_draw",
        "market_away",
        "odds_home",
        "odds_draw",
        "odds_away",
        "home_rating",
        "away_rating",
        "rating_diff",
        "rating_gap_abs",
        "league_strength",
        "match_minutes",
        "is_weekend",
        "opening_odds_home",
        "opening_odds_draw",
        "opening_odds_away",
        "return_rate",
        "market_overround",
        "home_odds_drop",
        "draw_odds_drop",
        "away_odds_drop",
        "kelly_home",
        "kelly_draw",
        "kelly_away",
        "kelly_draw_edge",
        "market_balance",
        "home_recent_match_count",
        "away_recent_match_count",
        "home_recent_points_pg",
        "away_recent_points_pg",
        "recent_points_diff",
        "home_recent_goal_diff_pg",
        "away_recent_goal_diff_pg",
        "recent_goal_diff_diff",
        "home_recent_goals_for_pg",
        "away_recent_goals_for_pg",
        "home_recent_win_rate",
        "away_recent_win_rate",
    ]

    def __init__(
        self,
        project_dir: Path,
        min_train_samples: int = 30,
        retrain_interval_minutes: int = 30,
    ) -> None:
        self.project_dir = project_dir
        self.min_train_samples = min_train_samples
        self.retrain_interval = timedelta(minutes=retrain_interval_minutes)
        self.state_dir = self.project_dir / "data" / "state"
        self.model_dir = self.project_dir / "data" / "models"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.samples_file = self.state_dir / "xgb_training_samples.json"
        self.samples_summary_file = self.state_dir / "xgb_training_samples_summary.json"
        self.model_file = self.model_dir / "xgb_v0_match_outcome.json"
        self.meta_file = self.model_dir / "xgb_v0_match_outcome.meta.json"

        self._model: Any = None
        self._model_ready = False
        self._last_train_attempt: datetime | None = None
        self._meta_cache_signature: dict[str, int] | None = None
        self._meta_cache: dict[str, Any] = {}

    @staticmethod
    def build_estimator() -> Any:
        if xgb is None:
            return None
        return xgb.XGBClassifier(
            objective="multi:softprob",
            num_class=3,
            n_estimators=160,
            max_depth=4,
            learning_rate=0.06,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="mlogloss",
            random_state=42,
            tree_method="hist",
        )

    @staticmethod
    def _normalize_probs(probs: ProbabilityTriple) -> ProbabilityTriple:
        home, draw, away = probs
        total = max(home + draw + away, 1e-9)
        return home / total, draw / total, away / total

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _parse_match_minutes(match_time: str) -> float:
        if not match_time or ":" not in match_time:
            return 0.0
        chunks = match_time.split(":")
        if len(chunks) != 2:
            return 0.0
        try:
            hour = int(chunks[0])
            minute = int(chunks[1])
            return float(hour * 60 + minute)
        except Exception:
            return 0.0

    @staticmethod
    def _is_weekend(match_date: str) -> float:
        try:
            date_obj = datetime.strptime(match_date, "%Y-%m-%d")
        except Exception:
            return 0.0
        return 1.0 if date_obj.weekday() >= 5 else 0.0

    def _feature_map(self, context: EnsembleContext) -> dict[str, float]:
        metadata = context.metadata or {}
        market_home, market_draw, market_away = context.market_probs
        rating_diff = context.home_rating - context.away_rating
        feature_map = {
            "market_home": market_home,
            "market_draw": market_draw,
            "market_away": market_away,
            "odds_home": self._safe_float(metadata.get("odds_home"), default=0.0),
            "odds_draw": self._safe_float(metadata.get("odds_draw"), default=0.0),
            "odds_away": self._safe_float(metadata.get("odds_away"), default=0.0),
            "home_rating": context.home_rating,
            "away_rating": context.away_rating,
            "rating_diff": rating_diff,
            "rating_gap_abs": abs(rating_diff),
            "league_strength": context.league_strength,
            "match_minutes": self._parse_match_minutes(str(metadata.get("match_time", ""))),
            "is_weekend": self._is_weekend(str(metadata.get("match_date", ""))),
        }
        feature_map.update(
            build_market_intent_feature_map(
                odds_home=feature_map["odds_home"],
                odds_draw=feature_map["odds_draw"],
                odds_away=feature_map["odds_away"],
                opening_odds_home=metadata.get("opening_odds_home", 0.0),
                opening_odds_draw=metadata.get("opening_odds_draw", 0.0),
                opening_odds_away=metadata.get("opening_odds_away", 0.0),
                return_rate=metadata.get("return_rate", 0.0),
                kelly_home=metadata.get("kelly_home", 0.0),
                kelly_draw=metadata.get("kelly_draw", 0.0),
                kelly_away=metadata.get("kelly_away", 0.0),
            )
        )
        for name in self.FEATURE_ORDER:
            if name in feature_map:
                continue
            feature_map[name] = self._safe_float(metadata.get(name), default=0.0)
        return feature_map

    def _load_meta(self) -> dict[str, Any]:
        signature = self._meta_signature()
        if signature["mtime_ns"] <= 0 or signature["size_bytes"] <= 0:
            self._meta_cache_signature = signature
            self._meta_cache = {}
            return {}
        if self._meta_cache_signature == signature:
            return dict(self._meta_cache)
        try:
            payload = json.loads(self.meta_file.read_text(encoding="utf-8"))
        except Exception:
            self._meta_cache_signature = signature
            self._meta_cache = {}
            return {}
        meta = payload if isinstance(payload, dict) else {}
        self._meta_cache_signature = signature
        self._meta_cache = dict(meta)
        return dict(meta)

    def _meta_signature(self) -> dict[str, int]:
        try:
            stat = self.meta_file.stat()
        except OSError:
            return {"mtime_ns": 0, "size_bytes": 0}
        return {"mtime_ns": int(stat.st_mtime_ns), "size_bytes": int(stat.st_size)}

    def _is_model_compatible(self, meta: dict[str, Any] | None = None) -> bool:
        payload = meta if isinstance(meta, dict) else self._load_meta()
        feature_order = payload.get("feature_order")
        return bool(isinstance(feature_order, list) and feature_order == self.FEATURE_ORDER)

    def _feature_vector(self, feature_map: dict[str, float]) -> list[float]:
        return [self._safe_float(feature_map.get(name, 0.0), default=0.0) for name in self.FEATURE_ORDER]

    def _load_samples(self) -> list[dict]:
        if not self.samples_file.exists():
            return []
        try:
            payload = json.loads(self.samples_file.read_text(encoding="utf-8"))
        except Exception:
            return []
        items = payload.get("items", [])
        return items if isinstance(items, list) else []

    def _samples_signature(self) -> dict[str, int]:
        try:
            stat = self.samples_file.stat()
        except OSError:
            return {"mtime_ns": 0, "size_bytes": 0}
        return {"mtime_ns": int(stat.st_mtime_ns), "size_bytes": int(stat.st_size)}

    def _sample_summary_from_samples(self, samples: list[dict]) -> dict[str, Any]:
        valid_feature_count = 0
        label_counts = {0: 0, 1: 0, 2: 0}
        for item in samples:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("features"), dict):
                valid_feature_count += 1
            try:
                label = int(item.get("label"))
            except Exception:
                continue
            if label in label_counts:
                label_counts[label] += 1
        return {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_file": str(self.samples_file),
            "source_signature": self._samples_signature(),
            "sample_count": len(samples),
            "valid_feature_count": valid_feature_count,
            "label_counts": {str(key): value for key, value in label_counts.items()},
        }

    def _load_sample_summary(self) -> dict[str, Any]:
        summary: dict[str, Any] = {}
        if self.samples_summary_file.exists():
            try:
                payload = json.loads(self.samples_summary_file.read_text(encoding="utf-8"))
                summary = payload if isinstance(payload, dict) else {}
            except Exception:
                summary = {}
        if summary.get("source_signature") == self._samples_signature():
            return summary
        samples = self._load_samples()
        summary = self._sample_summary_from_samples(samples)
        try:
            self.samples_summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        return summary

    def _samples_to_xy(self, samples: list[dict]) -> tuple[Any, Any]:
        if np is None:
            return None, None
        x_rows: list[list[float]] = []
        y_rows: list[int] = []
        for item in samples:
            if not isinstance(item, dict):
                continue
            features = item.get("features")
            label = item.get("label")
            if not isinstance(features, dict):
                continue
            try:
                label_int = int(label)
            except Exception:
                continue
            if label_int not in (0, 1, 2):
                continue
            x_rows.append(self._feature_vector(features))
            y_rows.append(label_int)
        if not x_rows:
            return None, None
        return np.array(x_rows, dtype=float), np.array(y_rows, dtype=int)

    def _label_counter(self, labels: Any) -> dict[int, int]:
        if labels is None:
            return {}
        try:
            return dict(Counter(int(item) for item in labels.tolist()))
        except Exception:
            return {}

    def _can_train(self, labels: Any, sample_size: int, min_samples: int | None = None) -> bool:
        if labels is None:
            return False
        threshold = self.min_train_samples if min_samples is None else max(1, int(min_samples))
        if sample_size < threshold:
            return False
        unique_labels = set(self._label_counter(labels).keys())
        return unique_labels == {0, 1, 2}

    def _train_from_samples(self, samples: list[dict], min_samples: int | None = None) -> dict[str, Any]:
        if xgb is None or np is None:
            return {"trained": False, "reason": "xgb_or_numpy_missing", "sample_count": len(samples)}

        x_matrix, y_vector = self._samples_to_xy(samples)
        if x_matrix is None or y_vector is None:
            return {"trained": False, "reason": "no_valid_samples", "sample_count": len(samples)}
        if not self._can_train(y_vector, len(samples), min_samples=min_samples):
            return {
                "trained": False,
                "reason": "insufficient_or_unbalanced_samples",
                "sample_count": len(samples),
                "label_counts": self._label_counter(y_vector),
                "min_samples": self.min_train_samples if min_samples is None else max(1, int(min_samples)),
            }

        now = datetime.now()
        model = self.build_estimator()
        if model is None:
            return {"trained": False, "reason": "xgb_or_numpy_missing", "sample_count": len(samples)}
        model.fit(x_matrix, y_vector)
        label_counts = self._label_counter(y_vector)
        model.save_model(str(self.model_file))
        meta_payload = {
            "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "sample_count": len(samples),
            "label_counts": label_counts,
            "feature_order": self.FEATURE_ORDER,
            "model": "xgb_v0_match_outcome",
        }
        self.meta_file.write_text(json.dumps(meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._meta_cache_signature = self._meta_signature()
        self._meta_cache = dict(meta_payload)
        self._model = model
        self._model_ready = True
        return {
            "trained": True,
            "reason": "ok",
            "sample_count": len(samples),
            "label_counts": label_counts,
            "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "model_file": str(self.model_file),
        }

    def _maybe_train(self) -> None:
        now = datetime.now()
        if self._last_train_attempt is not None and now - self._last_train_attempt < self.retrain_interval:
            return
        self._last_train_attempt = now
        samples = self._load_samples()
        self._train_from_samples(samples)

    def _load_model(self) -> None:
        if self._model is not None or self._model_ready:
            return
        if xgb is None or not self.model_file.exists():
            return
        meta = self._load_meta()
        if not self._is_model_compatible(meta):
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
        if self._model is None:
            return None
        try:
            vector = np.array([self._feature_vector(feature_map)], dtype=float)
            probs = self._model.predict_proba(vector)[0]
            if len(probs) != 3:
                return None
            return float(probs[0]), float(probs[1]), float(probs[2])
        except Exception:
            return None

    def _fallback_probs(self, context: EnsembleContext, feature_map: dict[str, float]) -> ProbabilityTriple:
        market_home, market_draw, market_away = context.market_probs
        rating_adjust = (context.home_rating - context.away_rating) / 2200.0
        odds_home = feature_map.get("odds_home", 0.0)
        odds_away = feature_map.get("odds_away", 0.0)
        odds_adjust = (odds_away - odds_home) / 40.0 if odds_home > 0 and odds_away > 0 else 0.0

        home = market_home + rating_adjust + odds_adjust
        away = market_away - rating_adjust - odds_adjust
        draw = market_draw + max(0.0, 0.04 - abs(rating_adjust) * 0.5)
        return self._normalize_probs((home, draw, away))

    def get_training_status(self) -> dict[str, Any]:
        summary = self._load_sample_summary()
        label_payload = summary.get("label_counts", {}) if isinstance(summary.get("label_counts"), dict) else {}
        label_counts = {key: int(label_payload.get(str(key), label_payload.get(key, 0)) or 0) for key in (0, 1, 2)}
        meta = self._load_meta()
        model_compatible = self._is_model_compatible(meta) if meta else (not self.model_file.exists())

        return {
            "sample_count": int(summary.get("sample_count", 0) or 0),
            "valid_feature_count": int(summary.get("valid_feature_count", 0) or 0),
            "label_counts": label_counts,
            "min_train_samples": self.min_train_samples,
            "model_exists": self.model_file.exists(),
            "model_ready": bool((self._model_ready or self.model_file.exists()) and model_compatible),
            "model_compatible": model_compatible,
            "model_updated_at": meta.get("updated_at"),
            "last_train_attempt": self._last_train_attempt.strftime("%Y-%m-%d %H:%M:%S") if self._last_train_attempt else None,
            "xgboost_available": xgb is not None and np is not None,
        }

    def train_now(self, force_min_samples: int | None = None) -> dict[str, Any]:
        self._last_train_attempt = datetime.now()
        samples = self._load_samples()
        result = self._train_from_samples(samples, min_samples=force_min_samples)
        result["status"] = self.get_training_status()
        return result

    def predict(self, context: EnsembleContext) -> ModelOutput:
        feature_map = self._feature_map(context)
        self._load_model()
        if self._model is None:
            self._maybe_train()
        probs = self._predict_with_model(feature_map)
        using_fallback = probs is None
        if probs is None:
            probs = self._fallback_probs(context, feature_map)
        probs = self._normalize_probs(probs)
        return ModelOutput(
            key=self.key,
            probabilities=probs,
            metadata={
                "xgb_features": feature_map,
                "xgb_model_ready": self._model_ready,
                "xgb_fallback": using_fallback,
            },
        )
