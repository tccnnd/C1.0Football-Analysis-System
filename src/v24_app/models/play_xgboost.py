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

from .xgboost_v0 import XGBoostProbabilityModel


class BasePlayXGBoostModel:
    FEATURE_ORDER = XGBoostProbabilityModel.FEATURE_ORDER

    def __init__(
        self,
        project_dir: Path,
        model_slug: str,
        min_train_samples: int = 300,
        retrain_interval_minutes: int = 60,
    ) -> None:
        self.project_dir = project_dir
        self.model_slug = model_slug
        self.min_train_samples = max(30, int(min_train_samples))
        self.retrain_interval = timedelta(minutes=max(5, int(retrain_interval_minutes)))
        self.state_dir = self.project_dir / "data" / "state"
        self.model_dir = self.project_dir / "data" / "models"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.samples_file = self.state_dir / "xgb_training_samples.json"
        self.model_file = self.model_dir / f"{self.model_slug}.json"
        self.meta_file = self.model_dir / f"{self.model_slug}.meta.json"
        self._model: Any = None
        self._model_ready = False
        self._last_train_attempt: datetime | None = None

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _safe_int(value: Any, default: int | None = None) -> int | None:
        try:
            return int(float(value))
        except Exception:
            return default

    def build_estimator(self, num_class: int) -> Any:
        if xgb is None or num_class <= 1:
            return None
        return xgb.XGBClassifier(
            objective="multi:softprob",
            num_class=int(num_class),
            n_estimators=180,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="mlogloss",
            random_state=42,
            tree_method="hist",
        )

    def _load_samples(self) -> list[dict]:
        if not self.samples_file.exists():
            return []
        try:
            payload = json.loads(self.samples_file.read_text(encoding="utf-8"))
        except Exception:
            return []
        items = payload.get("items", [])
        return items if isinstance(items, list) else []

    def _feature_vector(self, feature_map: dict[str, float]) -> list[float]:
        return [self._safe_float(feature_map.get(name, 0.0), default=0.0) for name in self.FEATURE_ORDER]

    def _load_meta(self) -> dict[str, Any]:
        if not self.meta_file.exists():
            return {}
        try:
            payload = json.loads(self.meta_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _is_model_compatible(self, meta: dict[str, Any] | None = None) -> bool:
        payload = meta if isinstance(meta, dict) else self._load_meta()
        feature_order = payload.get("feature_order")
        class_names = payload.get("class_names")
        return bool(isinstance(feature_order, list) and feature_order == self.FEATURE_ORDER and isinstance(class_names, list) and class_names)

    def _label_counter(self, labels: Any) -> dict[int, int]:
        if labels is None:
            return {}
        try:
            return dict(Counter(int(item) for item in labels.tolist()))
        except Exception:
            return {}

    def _can_train(self, labels: Any, sample_size: int, class_count: int, min_samples: int | None = None) -> bool:
        if labels is None or class_count <= 1:
            return False
        threshold = self.min_train_samples if min_samples is None else max(1, int(min_samples))
        if sample_size < threshold:
            return False
        label_keys = set(self._label_counter(labels).keys())
        return len(label_keys) >= min(class_count, 2)

    def _build_dataset(self, samples: list[dict]) -> tuple[Any, Any, dict[str, Any]]:
        raise NotImplementedError

    def _train_from_samples(self, samples: list[dict], min_samples: int | None = None) -> dict[str, Any]:
        if xgb is None or np is None:
            return {"trained": False, "reason": "xgb_or_numpy_missing", "sample_count": len(samples)}

        x_matrix, y_vector, dataset_meta = self._build_dataset(samples)
        class_names = dataset_meta.get("class_names", [])
        usable_count = int(dataset_meta.get("usable_count", 0) or 0)
        if x_matrix is None or y_vector is None or not class_names:
            return {
                "trained": False,
                "reason": str(dataset_meta.get("reason", "no_valid_samples")),
                "sample_count": len(samples),
                "usable_count": usable_count,
            }
        if not self._can_train(y_vector, usable_count, len(class_names), min_samples=min_samples):
            return {
                "trained": False,
                "reason": "insufficient_or_unbalanced_samples",
                "sample_count": len(samples),
                "usable_count": usable_count,
                "label_counts": self._label_counter(y_vector),
                "class_names": class_names,
                "min_samples": self.min_train_samples if min_samples is None else max(1, int(min_samples)),
            }

        model = self.build_estimator(len(class_names))
        if model is None:
            return {"trained": False, "reason": "xgb_or_numpy_missing", "sample_count": len(samples)}

        model.fit(x_matrix, y_vector)
        now = datetime.now()
        label_counts = self._label_counter(y_vector)
        model.save_model(str(self.model_file))
        self.meta_file.write_text(
            json.dumps(
                {
                    "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "sample_count": len(samples),
                    "usable_count": usable_count,
                    "label_counts": label_counts,
                    "feature_order": self.FEATURE_ORDER,
                    "class_names": class_names,
                    "model": self.model_slug,
                    **{key: value for key, value in dataset_meta.items() if key not in {"class_names", "usable_count"}},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self._model = model
        self._model_ready = True
        return {
            "trained": True,
            "reason": "ok",
            "sample_count": len(samples),
            "usable_count": usable_count,
            "label_counts": label_counts,
            "class_names": class_names,
            "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "model_file": str(self.model_file),
        }

    def _load_model(self) -> None:
        if self._model is not None or self._model_ready:
            return
        if xgb is None or not self.model_file.exists():
            return
        meta = self._load_meta()
        class_names = meta.get("class_names", [])
        if not self._is_model_compatible(meta) or not isinstance(class_names, list):
            self._model = None
            self._model_ready = False
            return
        try:
            model = xgb.XGBClassifier(objective="multi:softprob", num_class=len(class_names))
            model.load_model(str(self.model_file))
            self._model = model
            self._model_ready = True
        except Exception:
            self._model = None
            self._model_ready = False

    def _predict_from_features(self, feature_map: dict[str, float]) -> dict[str, Any]:
        meta = self._load_meta()
        class_names = meta.get("class_names", [])
        self._load_model()
        if self._model is None or np is None or not isinstance(class_names, list) or not class_names:
            return {
                "model_ready": False,
                "label": None,
                "confidence": 0.0,
                "probabilities": {},
                "class_names": class_names if isinstance(class_names, list) else [],
            }
        try:
            vector = np.array([self._feature_vector(feature_map)], dtype=float)
            probs = self._model.predict_proba(vector)[0]
        except Exception:
            return {
                "model_ready": False,
                "label": None,
                "confidence": 0.0,
                "probabilities": {},
                "class_names": class_names,
            }
        pairs = {str(class_names[idx]): float(probs[idx]) for idx in range(min(len(class_names), len(probs)))}
        if not pairs:
            return {
                "model_ready": False,
                "label": None,
                "confidence": 0.0,
                "probabilities": {},
                "class_names": class_names,
            }
        label = max(pairs, key=pairs.get)
        return {
            "model_ready": True,
            "label": label,
            "confidence": float(pairs.get(label, 0.0)),
            "probabilities": pairs,
            "class_names": class_names,
            "updated_at": meta.get("updated_at"),
        }

    def predict_from_features(self, feature_map: dict[str, float]) -> dict[str, Any]:
        return self._predict_from_features(feature_map)

    def get_training_status(self) -> dict[str, Any]:
        samples = self._load_samples()
        meta = self._load_meta()
        compatible = self._is_model_compatible(meta) if meta else (not self.model_file.exists())
        return {
            "sample_count": len(samples),
            "min_train_samples": self.min_train_samples,
            "model_exists": self.model_file.exists(),
            "model_ready": bool((self._model_ready or self.model_file.exists()) and compatible),
            "model_compatible": compatible,
            "model_updated_at": meta.get("updated_at"),
            "usable_count": int(meta.get("usable_count", 0) or 0),
            "label_counts": meta.get("label_counts", {}),
            "class_names": meta.get("class_names", []),
            "last_train_attempt": self._last_train_attempt.strftime("%Y-%m-%d %H:%M:%S") if self._last_train_attempt else None,
            "xgboost_available": xgb is not None and np is not None,
            "model": self.model_slug,
        }

    def train_now(self, force_min_samples: int | None = None) -> dict[str, Any]:
        self._last_train_attempt = datetime.now()
        samples = self._load_samples()
        result = self._train_from_samples(samples, min_samples=force_min_samples)
        result["status"] = self.get_training_status()
        return result


class TotalGoalsXGBoostModel(BasePlayXGBoostModel):
    def __init__(self, project_dir: Path, max_total_goals: int = 10) -> None:
        super().__init__(project_dir=project_dir, model_slug="xgb_v1_total_goals", min_train_samples=500)
        self.max_total_goals = max(6, int(max_total_goals))

    def _build_dataset(self, samples: list[dict]) -> tuple[Any, Any, dict[str, Any]]:
        if np is None:
            return None, None, {"reason": "numpy_missing", "class_names": [], "usable_count": 0}
        class_names = [str(goal) for goal in range(self.max_total_goals + 1)]
        x_rows: list[list[float]] = []
        y_rows: list[int] = []
        capped_samples = 0
        for item in samples:
            if not isinstance(item, dict):
                continue
            features = item.get("features")
            meta = item.get("meta")
            if not isinstance(features, dict) or not isinstance(meta, dict):
                continue
            home_goals = self._safe_int(meta.get("home_goals"))
            away_goals = self._safe_int(meta.get("away_goals"))
            if home_goals is None or away_goals is None:
                continue
            total_goals = int(home_goals) + int(away_goals)
            label = min(total_goals, self.max_total_goals)
            if total_goals > self.max_total_goals:
                capped_samples += 1
            x_rows.append(self._feature_vector(features))
            y_rows.append(label)
        if not x_rows:
            return None, None, {"reason": "no_valid_samples", "class_names": class_names, "usable_count": 0}
        return (
            np.array(x_rows, dtype=float),
            np.array(y_rows, dtype=int),
            {
                "class_names": class_names,
                "usable_count": len(x_rows),
                "max_total_goals": self.max_total_goals,
                "capped_samples": capped_samples,
            },
        )


class ScorelineXGBoostModel(BasePlayXGBoostModel):
    def __init__(self, project_dir: Path, top_k: int = 18) -> None:
        super().__init__(project_dir=project_dir, model_slug="xgb_v1_scoreline", min_train_samples=800)
        self.top_k = max(8, int(top_k))

    def _build_dataset(self, samples: list[dict]) -> tuple[Any, Any, dict[str, Any]]:
        if np is None:
            return None, None, {"reason": "numpy_missing", "class_names": [], "usable_count": 0}
        counts: Counter[str] = Counter()
        prepared: list[tuple[dict[str, float], str]] = []
        for item in samples:
            if not isinstance(item, dict):
                continue
            features = item.get("features")
            meta = item.get("meta")
            if not isinstance(features, dict) or not isinstance(meta, dict):
                continue
            home_goals = self._safe_int(meta.get("home_goals"))
            away_goals = self._safe_int(meta.get("away_goals"))
            if home_goals is None or away_goals is None:
                continue
            score_text = f"{int(home_goals)}-{int(away_goals)}"
            prepared.append((features, score_text))
            counts[score_text] += 1
        if not prepared:
            return None, None, {"reason": "no_valid_samples", "class_names": [], "usable_count": 0}
        common_scores = [score for score, _count in counts.most_common(self.top_k)]
        class_names = common_scores + ["OTHER"]
        score_to_index = {score: idx for idx, score in enumerate(common_scores)}
        other_index = len(class_names) - 1
        x_rows: list[list[float]] = []
        y_rows: list[int] = []
        other_samples = 0
        for features, score_text in prepared:
            label = score_to_index.get(score_text, other_index)
            if label == other_index:
                other_samples += 1
            x_rows.append(self._feature_vector(features))
            y_rows.append(label)
        return (
            np.array(x_rows, dtype=float),
            np.array(y_rows, dtype=int),
            {
                "class_names": class_names,
                "usable_count": len(x_rows),
                "top_k": self.top_k,
                "other_samples": other_samples,
            },
        )


def _scoreline_bucket_local(score_text: str | None) -> str:
    text = str(score_text or "").strip()
    if "-" not in text:
        return "volatile"
    common_regular = {
        "0-0",
        "1-0",
        "0-1",
        "1-1",
        "2-0",
        "0-2",
        "2-1",
        "1-2",
        "2-2",
        "3-0",
        "0-3",
        "3-1",
        "1-3",
    }
    if text in common_regular:
        return "regular"
    try:
        home_goals, away_goals = [int(part) for part in text.split("-", 1)]
    except Exception:
        return "volatile"
    total_goals = home_goals + away_goals
    goal_diff = abs(home_goals - away_goals)
    if total_goals <= 3 and goal_diff <= 2 and max(home_goals, away_goals) <= 2:
        return "regular"
    return "volatile"


class VolatileScorelineXGBoostModel(BasePlayXGBoostModel):
    FEATURE_ORDER = BasePlayXGBoostModel.FEATURE_ORDER + [
        "volatile_draw_suppression",
        "volatile_favorite_gap",
        "volatile_attack_sum",
        "volatile_attack_gap",
        "volatile_goal_diff_pressure",
        "volatile_recent_win_gap",
        "volatile_recent_match_load",
        "volatile_kelly_span",
        "volatile_odds_span",
        "volatile_odds_drop_span",
        "volatile_return_pressure",
    ]

    def __init__(self, project_dir: Path, top_k: int = 12) -> None:
        super().__init__(project_dir=project_dir, model_slug="xgb_v1_scoreline_volatile", min_train_samples=400)
        self.top_k = max(6, int(top_k))

    def _augment_features(self, feature_map: dict[str, float]) -> dict[str, float]:
        values = dict(feature_map)
        odds_home = self._safe_float(values.get("odds_home"), default=0.0)
        odds_draw = self._safe_float(values.get("odds_draw"), default=0.0)
        odds_away = self._safe_float(values.get("odds_away"), default=0.0)
        drop_home = abs(self._safe_float(values.get("home_odds_drop"), default=0.0))
        drop_draw = abs(self._safe_float(values.get("draw_odds_drop"), default=0.0))
        drop_away = abs(self._safe_float(values.get("away_odds_drop"), default=0.0))
        kelly_home = self._safe_float(values.get("kelly_home"), default=0.0)
        kelly_draw = self._safe_float(values.get("kelly_draw"), default=0.0)
        kelly_away = self._safe_float(values.get("kelly_away"), default=0.0)
        market_home = self._safe_float(values.get("market_home"), default=0.0)
        market_draw = self._safe_float(values.get("market_draw"), default=0.0)
        market_away = self._safe_float(values.get("market_away"), default=0.0)
        home_goals_for = self._safe_float(values.get("home_recent_goals_for_pg"), default=0.0)
        away_goals_for = self._safe_float(values.get("away_recent_goals_for_pg"), default=0.0)
        home_goal_diff = self._safe_float(values.get("home_recent_goal_diff_pg"), default=0.0)
        away_goal_diff = self._safe_float(values.get("away_recent_goal_diff_pg"), default=0.0)
        return_rate = self._safe_float(values.get("return_rate"), default=0.0)
        values.update(
            {
                "volatile_draw_suppression": round(max(0.0, 0.34 - market_draw), 4),
                "volatile_favorite_gap": round(abs(market_home - market_away), 4),
                "volatile_attack_sum": round(home_goals_for + away_goals_for, 4),
                "volatile_attack_gap": round(abs(home_goals_for - away_goals_for), 4),
                "volatile_goal_diff_pressure": round(
                    abs(home_goal_diff) + abs(away_goal_diff) + abs(self._safe_float(values.get("recent_goal_diff_diff"), default=0.0)),
                    4,
                ),
                "volatile_recent_win_gap": round(
                    abs(
                        self._safe_float(values.get("home_recent_win_rate"), default=0.0)
                        - self._safe_float(values.get("away_recent_win_rate"), default=0.0)
                    ),
                    4,
                ),
                "volatile_recent_match_load": round(
                    self._safe_float(values.get("home_recent_match_count"), default=0.0)
                    + self._safe_float(values.get("away_recent_match_count"), default=0.0),
                    4,
                ),
                "volatile_kelly_span": round(
                    max(kelly_home, kelly_draw, kelly_away) - min(kelly_home, kelly_draw, kelly_away),
                    4,
                ),
                "volatile_odds_span": round(max(odds_home, odds_draw, odds_away) - min(odds_home, odds_draw, odds_away), 4),
                "volatile_odds_drop_span": round(max(drop_home, drop_draw, drop_away), 4),
                "volatile_return_pressure": round(max(0.0, 0.92 - return_rate), 4),
            }
        )
        return values

    def _feature_vector(self, feature_map: dict[str, float]) -> list[float]:
        augmented = self._augment_features(feature_map)
        return [self._safe_float(augmented.get(name, 0.0), default=0.0) for name in self.FEATURE_ORDER]

    def _build_dataset(self, samples: list[dict]) -> tuple[Any, Any, dict[str, Any]]:
        if np is None:
            return None, None, {"reason": "numpy_missing", "class_names": [], "usable_count": 0}
        counts: Counter[str] = Counter()
        prepared: list[tuple[dict[str, float], str]] = []
        skipped_regular = 0
        for item in samples:
            if not isinstance(item, dict):
                continue
            features = item.get("features")
            meta = item.get("meta")
            if not isinstance(features, dict) or not isinstance(meta, dict):
                continue
            home_goals = self._safe_int(meta.get("home_goals"))
            away_goals = self._safe_int(meta.get("away_goals"))
            if home_goals is None or away_goals is None:
                continue
            score_text = f"{int(home_goals)}-{int(away_goals)}"
            if _scoreline_bucket_local(score_text) != "volatile":
                skipped_regular += 1
                continue
            prepared.append((features, score_text))
            counts[score_text] += 1
        if not prepared:
            return None, None, {"reason": "no_volatile_samples", "class_names": [], "usable_count": 0}
        common_scores = [score for score, _count in counts.most_common(self.top_k)]
        class_names = common_scores + ["OTHER"]
        score_to_index = {score: idx for idx, score in enumerate(common_scores)}
        other_index = len(class_names) - 1
        x_rows: list[list[float]] = []
        y_rows: list[int] = []
        other_samples = 0
        for features, score_text in prepared:
            label = score_to_index.get(score_text, other_index)
            if label == other_index:
                other_samples += 1
            x_rows.append(self._feature_vector(features))
            y_rows.append(label)
        return (
            np.array(x_rows, dtype=float),
            np.array(y_rows, dtype=int),
            {
                "class_names": class_names,
                "usable_count": len(x_rows),
                "top_k": self.top_k,
                "other_samples": other_samples,
                "skipped_regular_samples": skipped_regular,
            },
        )
