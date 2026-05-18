from __future__ import annotations

import json
import hashlib
import re
import shutil
import subprocess
import threading
import time
import csv
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from itertools import product
from math import log, log2, sqrt
from pathlib import Path
from typing import Any, Iterable

from .models.elo_rating import EloRatingEngine
from .models.ensemble import (
    EloProbabilityModel,
    EnsembleContext,
    MarketProbabilityModel,
    PoissonProbabilityModel,
    WeightedEnsembleEngine,
    get_poisson_outcome,
)
from .models.poisson import PoissonScoreEngine
from .models.play_xgboost import ScorelineXGBoostModel, TotalGoalsXGBoostModel, VolatileScorelineXGBoostModel
from .models.xgboost_v0 import XGBoostProbabilityModel
from .models.bayesian_calibration import calibrate_three_way_probabilities
from .orchestrator import build_supervisor_orchestration
from .storage.state_store import StateStore
from .trace_envelope import build_prediction_trace_envelope
from .training_samples import (
    build_recent_form_feature_map,
    build_team_histories_from_state,
    export_statsbomb_review_training_samples,
    export_video_review_fewshot_samples,
    import_historical_xgb_samples,
)

try:
    from .data_sources.match_fetcher_titan import MatchFetcherTitan
except Exception:
    MatchFetcherTitan = None

try:
    from .data_sources.match_fetcher_500 import MatchFetcher500
except Exception:
    MatchFetcher500 = None

try:
    from .data_sources.market_intent_500 import MarketIntentFetcher500
except Exception:
    MarketIntentFetcher500 = None


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent.parent
CACHE_FILE = PROJECT_DIR / "data" / "cache" / "500_matches_today.json"
REPORT_DIR = PROJECT_DIR / "reports"
VIDEO_REVIEW_DIR = PROJECT_DIR / "data" / "video_reviews"
VIDEO_REVIEW_FILE = PROJECT_DIR / "data" / "state" / "video_reviews.json"
VIDEO_REVIEW_FEWSHOT_FILE = PROJECT_DIR / "data" / "state" / "video_review_fewshot_samples.json"
VIDEO_REVIEW_FEWSHOT_MEMORY_FILE = PROJECT_DIR / "data" / "state" / "video_review_fewshot_memory.json"
STATSBOMB_EVENT_SUMMARIES_FILE = PROJECT_DIR / "data" / "state" / "statsbomb_event_summaries.json"
STATSBOMB_EVENT_BASELINE_FILE = PROJECT_DIR / "data" / "state" / "statsbomb_event_baseline.json"
STATSBOMB_SANDBOX_FEWSHOT_FILE = PROJECT_DIR / "data" / "state" / "statsbomb_sandbox_fewshot_samples.json"
STATSBOMB_REVIEW_TRAINING_FILE = PROJECT_DIR / "data" / "state" / "statsbomb_review_training_samples.json"
_STATSBOMB_STATE_JSON_CACHE: dict[Path, tuple[tuple[int, int], dict]] = {}
ENSEMBLE_WEIGHTS_FILE = PROJECT_DIR / "data" / "models" / "ensemble_weights_v1.json"
PLAY_THRESHOLDS_FILE = PROJECT_DIR / "data" / "models" / "play_thresholds_v1.json"
PLAY_MODEL_POLICY_FILE = PROJECT_DIR / "data" / "models" / "play_model_policy_v1.json"
PLAY_MODEL_POLICY_HISTORY_FILE = PROJECT_DIR / "data" / "models" / "play_model_policy_history_v1.json"
PLAY_MODEL_TAKEOVER_GATE_HISTORY_FILE = PROJECT_DIR / "data" / "models" / "play_model_takeover_gate_history_v1.json"
DRAW_SPECIALIST_BACKTEST_FILE = PROJECT_DIR / "data" / "models" / "draw_specialist_backtest_v1.json"
DRAW_RELEASE_GUARD_POLICY_FILE = PROJECT_DIR / "data" / "models" / "draw_release_guard_policy_v1.json"
DRAW_RELEASE_GUARD_POLICY_HISTORY_FILE = PROJECT_DIR / "data" / "models" / "draw_release_guard_policy_history_v1.json"
BAYES_CALIBRATION_FILE = PROJECT_DIR / "data" / "models" / "bayes_calibration_v1.json"
HIGH_ACCURACY_STRATEGY_FILE = PROJECT_DIR / "data" / "models" / "high_accuracy_strategy_v1.json"
JC_STRATIFIED_STRATEGY_FILE = PROJECT_DIR / "data" / "models" / "jc_stratified_strategy_backtest_v1.json"
STRATEGY_ADMISSION_POLICY_FILE = PROJECT_DIR / "data" / "models" / "strategy_admission_policy_v1.json"
STRATEGY_ADMISSION_POLICY_HISTORY_FILE = PROJECT_DIR / "data" / "models" / "strategy_admission_policy_history_v1.json"
HIGH_ACCURACY_STRATEGY_BREAKER_THRESHOLD = 3
HIGH_ACCURACY_STRATEGY_BREAKER_WINDOW = 30
HIGH_ACCURACY_STRATEGY_RECOVERY_HITS = 2
JC_BUCKET_LIVE_FEEDBACK_WINDOW = 120
JC_BUCKET_LIVE_PENDING_SAMPLES = 5
JC_BUCKET_LIVE_DOWNGRADE_SAMPLES = 10
JC_BUCKET_RECOVERY_REQUIRED_HITS = 3
JC_STRATEGY_CALIBRATION_MIN_LIVE_BUCKETS = 2
STRATEGY_ADMISSION_MIN_CONFIDENCE = 0.50
STRATEGY_ADMISSION_BLOCK_CONFIDENCE = 0.40
JC_STRATIFIED_MIN_RUNTIME_SAMPLES = 120
JC_STRATIFIED_MIN_RUNTIME_ACCURACY = 0.68
JC_STRATIFIED_MIN_RUNTIME_WILSON = 0.64
JC_STRATIFIED_MIN_STABILITY_SCORE = 0.0
DEFAULT_STRATEGY_ADMISSION_POLICY = {
    "min_confidence": STRATEGY_ADMISSION_MIN_CONFIDENCE,
    "block_confidence": STRATEGY_ADMISSION_BLOCK_CONFIDENCE,
    "active_strategy_min": 1,
    "medium_risk_allowed": True,
    "high_risk_allowed": False,
    "agent_replay_guard_enabled": True,
    "agent_replay_min_samples": 5,
    "agent_replay_prediction_miss_threshold": 0.55,
    "agent_replay_handicap_miss_threshold": 0.60,
}


LEAGUE_STRENGTH = {
    "英超": 1.00,
    "西甲": 0.98,
    "德甲": 0.97,
    "意甲": 0.96,
    "法甲": 0.94,
    "中超": 0.88,
    "日职联": 0.90,
    "美职联": 0.89,
    "欧冠": 1.02,
    "欧联": 0.98,
}
WORLD_CUP_LEAGUE_KEYWORDS = (
    "世界杯",
    "世界盃",
    "world cup",
    "fifa world cup",
    "worldcup",
)
WORLD_CUP_CONFIDENCE_CAP = 0.56

ELO_ENGINE = EloRatingEngine()
POISSON_ENGINE = PoissonScoreEngine()
MARKET_MODEL = MarketProbabilityModel()
ELO_MODEL = EloProbabilityModel(ELO_ENGINE)
POISSON_MODEL = PoissonProbabilityModel(POISSON_ENGINE)
XGBOOST_MODEL = XGBoostProbabilityModel(PROJECT_DIR)
TOTAL_GOALS_MODEL = TotalGoalsXGBoostModel(PROJECT_DIR)
SCORELINE_MODEL = ScorelineXGBoostModel(PROJECT_DIR)
VOLATILE_SCORELINE_MODEL = VolatileScorelineXGBoostModel(PROJECT_DIR)
DEFAULT_ENSEMBLE_WEIGHTS = {
    "market": 0.35,
    "elo": 0.30,
    "poisson": 0.20,
    "xgboost": 0.15,
}
DEFAULT_PLAY_THRESHOLDS = {
    "1x2": 0.56,
    "handicap": 0.56,
    "total_goals": 0.18,
    "score": 0.10,
    "htft": 0.18,
}
PLAY_THRESHOLD_RANGE = {
    "1x2": (0.45, 0.78),
    "handicap": (0.45, 0.78),
    "total_goals": (0.12, 0.40),
    "score": (0.06, 0.28),
    "htft": (0.12, 0.40),
}
DEFAULT_PLAY_POLICY = {
    "1x2": {"single_enabled": True, "parlay_enabled": True, "display_enabled": True, "priority": 1},
    "handicap": {"single_enabled": True, "parlay_enabled": True, "display_enabled": True, "priority": 2},
    "total_goals": {"single_enabled": True, "parlay_enabled": True, "display_enabled": True, "priority": 3},
    "htft": {"single_enabled": True, "parlay_enabled": False, "display_enabled": True, "priority": 4},
    "score": {"single_enabled": False, "parlay_enabled": False, "display_enabled": True, "priority": 5},
}
DEFAULT_PLAY_MODEL_POLICY = {
    "total_goals": {
        "takeover_enabled": False,
        "min_confidence": 0.24,
    },
    "scoreline": {
        "takeover_enabled": True,
        "regular_same_outcome_min_confidence": 0.07,
        "regular_cross_outcome_enabled": True,
        "regular_cross_outcome_min_confidence": 0.11,
        "volatile_same_outcome_min_confidence": 0.13,
        "volatile_cross_outcome_enabled": False,
        "volatile_cross_outcome_min_confidence": 0.17,
    },
}
PLAY_MODEL_TOTAL_GOALS_MIN_CALIBRATION_UPLIFT = 0.03
PLAY_MODEL_TOTAL_GOALS_MIN_HOLDOUT_UPLIFT = 0.0
PLAY_MODEL_SCORELINE_MAX_HOLDOUT_REGRESSION = 0.03
PLAY_MODEL_POLICY_HOLDOUT_RATIO = 0.25
PLAY_MODEL_POLICY_MIN_HOLDOUT_ROWS = 100
PLAY_MODEL_TAKEOVER_GATE_MIN_VALIDATION_SAMPLES = 300
PLAY_MODEL_TAKEOVER_GATE_TOTAL_GOALS_MIN_DELTA = 0.0
PLAY_MODEL_TAKEOVER_GATE_TOTAL_GOALS_BLOCK_DELTA = -0.02
PLAY_MODEL_TAKEOVER_GATE_SCORE_MIN_DELTA = -0.01
PLAY_MODEL_TAKEOVER_GATE_SCORE_BLOCK_DELTA = -0.03
DEFAULT_DRAW_RELEASE_GUARD_POLICY = {
    "enabled": True,
    "min_score": 0.58,
    "weak_odds_buckets": {
        "<=3.00": {
            "precision": 0.222222,
            "draw_rate": 0.157895,
            "lift": -0.075439,
            "source": "draw_specialist_backtest_20260511_112806",
        },
        ">4.20": {
            "precision": None,
            "draw_rate": 0.149425,
            "lift": -0.083908,
            "source": "draw_specialist_backtest_20260511_112806",
        },
    },
}
DEFAULT_BAYES_CALIBRATION = {
    "enabled": True,
    "prior_source": "market",
    "prior_strength": 24.0,
    "model_strength": 56.0,
    "uncertainty_gain": 0.55,
    "draw_bias_scale": 0.18,
    "min_probability": 0.02,
}
LEAGUE_WEIGHT_MIN_VALIDATION_SAMPLES = 120
BAYES_LEAGUE_MIN_VALIDATION_SAMPLES = 260
ENSEMBLE_ENGINE = WeightedEnsembleEngine(
    weights=DEFAULT_ENSEMBLE_WEIGHTS
)
STATE_STORE = StateStore(PROJECT_DIR)
_RECENT_FORM_CACHE: dict[str, object] = {
    "signature": None,
    "team_histories": {},
}
_RECENT_FORM_CACHE_VERSION = 1
_RECENT_FORM_CACHE_LOCK = threading.RLock()
_RATINGS_CACHE: dict[str, dict[str, object]] = {
    "club": {"signature": None, "ratings": {}},
    "national_team": {"signature": None, "ratings": {}},
}
_ENSEMBLE_WEIGHT_CACHE: dict[str, object] = {
    "mtime": None,
    "weights": dict(DEFAULT_ENSEMBLE_WEIGHTS),
    "report": {},
}
_PLAY_THRESHOLD_CACHE: dict[str, object] = {
    "mtime": None,
    "thresholds": dict(DEFAULT_PLAY_THRESHOLDS),
    "report": {},
}
_PLAY_MODEL_POLICY_CACHE: dict[str, object] = {
    "mtime": None,
    "policy": json.loads(json.dumps(DEFAULT_PLAY_MODEL_POLICY)),
    "report": {},
}
_DRAW_RELEASE_GUARD_POLICY_CACHE: dict[str, object] = {
    "mtime": None,
    "policy": json.loads(json.dumps(DEFAULT_DRAW_RELEASE_GUARD_POLICY)),
    "report": {},
}
_BAYES_CALIBRATION_CACHE: dict[str, object] = {
    "mtime": None,
    "config": dict(DEFAULT_BAYES_CALIBRATION),
    "report": {},
}
_STRATEGY_ADMISSION_POLICY_CACHE: dict[str, object] = {
    "mtime": None,
    "policy": dict(DEFAULT_STRATEGY_ADMISSION_POLICY),
    "report": {},
}
_CONFIDENCE_CALIBRATION_CACHE: dict[str, object] = {
    "settlement_mtime": None,
    "profile": {},
}
_LIVE_PLAY_THRESHOLD_CACHE: dict[str, object] = {
    "cache_key": None,
    "thresholds": {},
    "meta": {},
}
_RECENT_SETTLEMENTS_CACHE: dict[tuple[object, ...], list[dict]] = {}
_MARKET_SNAPSHOT_RECORD_CACHE: dict[str, object] = {
    "signature": None,
    "items": {},
}
_HIGH_ACCURACY_STRATEGY_STATUS_CACHE: dict[str, object] = {
    "cache_key": None,
    "status": {},
}
_JC_BUCKET_LIVE_FEEDBACK_CACHE: dict[str, object] = {
    "cache_key": None,
    "feedback": {},
}


def _path_signature(path: Path) -> tuple[int, int]:
    try:
        stat = path.stat()
        return int(stat.st_mtime_ns), int(stat.st_size)
    except OSError:
        return 0, 0


def _state_store_path_signature(attribute: str) -> tuple[int, int] | None:
    path = getattr(STATE_STORE, attribute, None)
    return _path_signature(path) if isinstance(path, Path) else None


def _recent_settlements_signature(limit: int) -> tuple[object, ...] | None:
    settlements_signature = _state_store_path_signature("settlements_file")
    history_signature = _state_store_path_signature("analysis_history_file")
    if settlements_signature is None or history_signature is None:
        return None
    return (
        int(limit),
        id(STATE_STORE),
        id(get_recent_settlements),
        settlements_signature,
        history_signature,
        _path_signature(VIDEO_REVIEW_FILE),
        _path_signature(STATSBOMB_EVENT_SUMMARIES_FILE),
    )


def _copy_dict_rows(rows: Iterable[dict]) -> list[dict]:
    return [dict(item) for item in rows if isinstance(item, dict)]


@dataclass
class AppMatch:
    home_team: str
    away_team: str
    league: str
    match_time: str
    match_date: str
    odds_home: float
    odds_draw: float
    odds_away: float
    handicap_line: float = 0.0
    opening_odds_home: float = 0.0
    opening_odds_draw: float = 0.0
    opening_odds_away: float = 0.0
    return_rate: float = 0.0
    kelly_home: float = 0.0
    kelly_draw: float = 0.0
    kelly_away: float = 0.0
    source: str = "unknown"
    source_id: str = ""
    competition_group: str = ""
    group_round: int = 0
    home_points: int | None = None
    away_points: int | None = None
    home_goal_diff: int | None = None
    away_goal_diff: int | None = None
    home_group_rank: int | None = None
    away_group_rank: int | None = None

    @property
    def match_id(self) -> str:
        return f"{self.match_date}|{self.league}|{self.home_team}|{self.away_team}"


@dataclass
class FetchDiagnostics:
    source: str = "none"
    fixture_source_guard: bool = False
    fixture_page_guard: bool = False
    cache_fresh: bool = False
    cache_exists: bool = False
    cache_date: str = ""
    cache_match_count: int = 0
    cache_age_days: int | None = None
    fetched_at: str = ""
    messages: list[str] = field(default_factory=list)
    source_reports: list[dict] = field(default_factory=list)

    def add(self, message: str) -> None:
        self.messages.append(message)


@dataclass
class FetchResult:
    matches: list[AppMatch]
    diagnostics: FetchDiagnostics


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except Exception:
        return None


def _safe_int(value: object, default: int | None = None) -> int | None:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except Exception:
        return default


def _text_quality(text: str) -> float:
    if not text:
        return 0.0
    useful = 0
    for char in text:
        if "\u4e00" <= char <= "\u9fff" or char.isascii():
            useful += 1
    return useful / max(len(text), 1)


def normalize_text(value: object) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    original_quality = _text_quality(text)
    try:
        repaired = text.encode("gbk", errors="ignore").decode("utf-8", errors="ignore").strip()
    except Exception:
        repaired = text

    if repaired and _text_quality(repaired) > original_quality:
        text = repaired

    return text.replace("\xa0", " ").strip()


def is_world_cup_match(match: AppMatch) -> bool:
    league = normalize_text(getattr(match, "league", "")).lower()
    return any(keyword in league for keyword in WORLD_CUP_LEAGUE_KEYWORDS)


def _rating_pool_file_signature(pool: str) -> dict[str, object]:
    attribute = "national_team_ratings_file" if pool == "national_team" else "ratings_file"
    path = getattr(STATE_STORE, attribute, None)
    if path is None:
        return {"source_file": "", "mtime_ns": 0, "size_bytes": 0}
    if isinstance(path, Path):
        signature = _state_file_signature(path)
        return {"source_file": str(path), **signature}
    try:
        resolved_path = Path(str(path))
        signature = _state_file_signature(resolved_path)
        return {"source_file": str(resolved_path), **signature}
    except Exception:
        return {"source_file": str(path), "mtime_ns": 0, "size_bytes": 0}


def _load_ratings_for_pool(pool: str) -> dict[str, float]:
    cache = _RATINGS_CACHE.setdefault(pool, {"signature": None, "ratings": {}})
    signature = _rating_pool_file_signature(pool)
    cached_ratings = cache.get("ratings")
    if cache.get("signature") == signature and isinstance(cached_ratings, dict):
        return {str(team): float(value) for team, value in cached_ratings.items()}

    ratings = STATE_STORE.load_national_team_ratings() if pool == "national_team" else STATE_STORE.load_ratings()
    normalized = {str(team): float(value) for team, value in ratings.items()}
    cache["signature"] = signature
    cache["ratings"] = dict(normalized)
    return dict(normalized)


def _save_ratings_for_pool(pool: str, ratings: dict[str, float]) -> None:
    normalized = {str(team): float(value) for team, value in ratings.items()}
    if pool == "national_team":
        STATE_STORE.save_national_team_ratings(normalized)
    else:
        STATE_STORE.save_ratings(normalized)
    cache = _RATINGS_CACHE.setdefault(pool, {"signature": None, "ratings": {}})
    cache["signature"] = _rating_pool_file_signature(pool)
    cache["ratings"] = dict(normalized)


def _load_match_ratings(match: AppMatch) -> dict[str, float]:
    return _load_ratings_for_pool(_rating_pool_name(match))


def _save_match_ratings(match: AppMatch, ratings: dict[str, float]) -> None:
    _save_ratings_for_pool(_rating_pool_name(match), ratings)


def _rating_pool_name(match: AppMatch) -> str:
    return "national_team" if is_world_cup_match(match) else "club"


def _world_cup_phase_hint(match: AppMatch) -> str:
    league = normalize_text(getattr(match, "league", ""))
    if any(text in league for text in ("淘汰", "1/8", "八分之一", "半决赛", "决赛")):
        return "knockout"
    if any(text in league for text in ("小组", "分组", "group")):
        return "group"
    return "unknown"


def _apply_world_cup_overlay(match: AppMatch, prediction: dict) -> dict:
    if not is_world_cup_match(match) or not isinstance(prediction, dict):
        return prediction

    adjusted = dict(prediction)
    raw_confidence = _safe_float(adjusted.get("confidence"), default=0.0)
    capped_confidence = min(raw_confidence, WORLD_CUP_CONFIDENCE_CAP)
    confidence_adjusted = capped_confidence < raw_confidence
    if confidence_adjusted:
        adjusted["confidence"] = round(capped_confidence, 4)

    original_model = str(adjusted.get("model") or "")
    adjusted["model"] = f"{original_model}+WorldCupMode" if original_model else "WorldCupMode"
    adjusted["competition_mode"] = "world_cup"
    adjusted["rating_pool"] = "national_team"
    adjusted["world_cup_mode"] = {
        "enabled": True,
        "phase": _world_cup_phase_hint(match),
        "group_context": _world_cup_group_context(match),
        "confidence_cap": WORLD_CUP_CONFIDENCE_CAP,
        "confidence_adjusted": confidence_adjusted,
        "notes": [
            "世界杯赛事使用独立提示，不与普通联赛样本直接混用。",
            "国家队样本稀疏，阵容、赛程和赛制权重应高于俱乐部联赛。",
            "小组赛需关注积分形势，淘汰赛需关注加时/点球和保守策略。",
        ],
    }
    return adjusted


def _world_cup_group_context(match: AppMatch) -> dict[str, object]:
    home_points = getattr(match, "home_points", None)
    away_points = getattr(match, "away_points", None)
    home_goal_diff = getattr(match, "home_goal_diff", None)
    away_goal_diff = getattr(match, "away_goal_diff", None)
    group_round = int(getattr(match, "group_round", 0) or 0)
    context = {
        "group": normalize_text(getattr(match, "competition_group", "")),
        "round": group_round,
        "home_points": home_points,
        "away_points": away_points,
        "home_goal_diff": home_goal_diff,
        "away_goal_diff": away_goal_diff,
        "home_group_rank": getattr(match, "home_group_rank", None),
        "away_group_rank": getattr(match, "away_group_rank", None),
        "pressure_tags": [],
    }
    tags: list[str] = []
    if group_round >= 3:
        tags.append("final_group_round")
    if isinstance(home_points, int) and isinstance(away_points, int):
        if abs(home_points - away_points) <= 1:
            tags.append("points_tight")
        if max(home_points, away_points) >= 4 and min(home_points, away_points) <= 1:
            tags.append("asymmetric_motivation")
    if isinstance(home_goal_diff, int) and isinstance(away_goal_diff, int) and abs(home_goal_diff - away_goal_diff) >= 3:
        tags.append("goal_difference_pressure")
    context["pressure_tags"] = tags
    return context


def _looks_like_match_time(value: str) -> bool:
    return len(value) == 5 and value[2] == ":" and value[:2].isdigit() and value[3:].isdigit()


def _looks_like_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _has_readable_name(text: str) -> bool:
    text = normalize_text(text)
    return len(text) >= 2 and _text_quality(text) >= 0.75


def _to_app_match(raw: object, source: str) -> AppMatch | None:
    if raw is None:
        return None

    if hasattr(raw, "home_team"):
        home_team = normalize_text(getattr(raw, "home_team", ""))
        away_team = normalize_text(getattr(raw, "away_team", ""))
        league = normalize_text(getattr(raw, "league", ""))
        match_time = normalize_text(getattr(raw, "match_time", ""))
        match_date = normalize_text(getattr(raw, "match_date", ""))
        odds_home = _safe_float(getattr(raw, "odds_home", None))
        odds_draw = _safe_float(getattr(raw, "odds_draw", None))
        odds_away = _safe_float(getattr(raw, "odds_away", None))
        handicap_line = _safe_float(getattr(raw, "handicap_line", 0.0), default=0.0)
        opening_odds_home = _safe_float(getattr(raw, "opening_odds_home", 0.0), default=0.0)
        opening_odds_draw = _safe_float(getattr(raw, "opening_odds_draw", 0.0), default=0.0)
        opening_odds_away = _safe_float(getattr(raw, "opening_odds_away", 0.0), default=0.0)
        return_rate = _safe_float(getattr(raw, "return_rate", 0.0), default=0.0)
        kelly_home = _safe_float(getattr(raw, "kelly_home", 0.0), default=0.0)
        kelly_draw = _safe_float(getattr(raw, "kelly_draw", 0.0), default=0.0)
        kelly_away = _safe_float(getattr(raw, "kelly_away", 0.0), default=0.0)
        source_id = normalize_text(getattr(raw, "match_id", ""))
        competition_group = normalize_text(getattr(raw, "competition_group", ""))
        group_round = _optional_int(getattr(raw, "group_round", None)) or 0
        home_points = _optional_int(getattr(raw, "home_points", None))
        away_points = _optional_int(getattr(raw, "away_points", None))
        home_goal_diff = _optional_int(getattr(raw, "home_goal_diff", None))
        away_goal_diff = _optional_int(getattr(raw, "away_goal_diff", None))
        home_group_rank = _optional_int(getattr(raw, "home_group_rank", None))
        away_group_rank = _optional_int(getattr(raw, "away_group_rank", None))
    elif isinstance(raw, dict):
        home_team = normalize_text(raw.get("home_team", ""))
        away_team = normalize_text(raw.get("away_team", ""))
        league = normalize_text(raw.get("league", ""))
        match_time = normalize_text(raw.get("match_time", ""))
        match_date = normalize_text(raw.get("match_date", ""))
        odds_home = _safe_float(raw.get("odds_home"))
        odds_draw = _safe_float(raw.get("odds_draw"))
        odds_away = _safe_float(raw.get("odds_away"))
        handicap_line = _safe_float(raw.get("handicap_line"), default=0.0)
        opening_odds_home = _safe_float(raw.get("opening_odds_home"), default=0.0)
        opening_odds_draw = _safe_float(raw.get("opening_odds_draw"), default=0.0)
        opening_odds_away = _safe_float(raw.get("opening_odds_away"), default=0.0)
        return_rate = _safe_float(raw.get("return_rate"), default=0.0)
        kelly_home = _safe_float(raw.get("kelly_home"), default=0.0)
        kelly_draw = _safe_float(raw.get("kelly_draw"), default=0.0)
        kelly_away = _safe_float(raw.get("kelly_away"), default=0.0)
        source_id = normalize_text(raw.get("source_id", "") or raw.get("match_source_id", ""))
        competition_group = normalize_text(raw.get("competition_group", ""))
        group_round = _optional_int(raw.get("group_round")) or 0
        home_points = _optional_int(raw.get("home_points"))
        away_points = _optional_int(raw.get("away_points"))
        home_goal_diff = _optional_int(raw.get("home_goal_diff"))
        away_goal_diff = _optional_int(raw.get("away_goal_diff"))
        home_group_rank = _optional_int(raw.get("home_group_rank"))
        away_group_rank = _optional_int(raw.get("away_group_rank"))
    else:
        return None

    if not _has_readable_name(home_team) or not _has_readable_name(away_team):
        return None
    if not _has_readable_name(league):
        return None
    if not _looks_like_match_time(match_time):
        return None
    if not _looks_like_date(match_date):
        return None
    if min(odds_home, odds_draw, odds_away) <= 1.0:
        return None

    return AppMatch(
        home_team=home_team,
        away_team=away_team,
        league=league,
        match_time=match_time,
        match_date=match_date,
        odds_home=odds_home,
        odds_draw=odds_draw,
        odds_away=odds_away,
        handicap_line=handicap_line,
        opening_odds_home=opening_odds_home,
        opening_odds_draw=opening_odds_draw,
        opening_odds_away=opening_odds_away,
        return_rate=return_rate,
        kelly_home=kelly_home,
        kelly_draw=kelly_draw,
        kelly_away=kelly_away,
        source=source,
        source_id=source_id,
        competition_group=competition_group,
        group_round=group_round,
        home_points=home_points,
        away_points=away_points,
        home_goal_diff=home_goal_diff,
        away_goal_diff=away_goal_diff,
        home_group_rank=home_group_rank,
        away_group_rank=away_group_rank,
    )


def _app_match_from_payload(payload: dict, source: str) -> AppMatch | None:
    if not isinstance(payload, dict):
        return None
    home_team = normalize_text(payload.get("home_team", ""))
    away_team = normalize_text(payload.get("away_team", ""))
    league = normalize_text(payload.get("league", ""))
    match_time = normalize_text(payload.get("match_time", ""))
    match_date = normalize_text(payload.get("match_date", ""))
    if not _has_readable_name(home_team) or not _has_readable_name(away_team) or not _has_readable_name(league):
        return None
    if not _looks_like_match_time(match_time) or not _looks_like_date(match_date):
        return None

    odds_home = _safe_float(payload.get("odds_home"), default=2.20)
    odds_draw = _safe_float(payload.get("odds_draw"), default=3.10)
    odds_away = _safe_float(payload.get("odds_away"), default=2.80)
    handicap_line = _safe_float(payload.get("handicap_line"), default=0.0)
    opening_odds_home = _safe_float(payload.get("opening_odds_home"), default=0.0)
    opening_odds_draw = _safe_float(payload.get("opening_odds_draw"), default=0.0)
    opening_odds_away = _safe_float(payload.get("opening_odds_away"), default=0.0)
    return_rate = _safe_float(payload.get("return_rate"), default=0.0)
    kelly_home = _safe_float(payload.get("kelly_home"), default=0.0)
    kelly_draw = _safe_float(payload.get("kelly_draw"), default=0.0)
    kelly_away = _safe_float(payload.get("kelly_away"), default=0.0)
    competition_group = normalize_text(payload.get("competition_group", ""))
    group_round = _optional_int(payload.get("group_round")) or 0
    home_points = _optional_int(payload.get("home_points"))
    away_points = _optional_int(payload.get("away_points"))
    home_goal_diff = _optional_int(payload.get("home_goal_diff"))
    away_goal_diff = _optional_int(payload.get("away_goal_diff"))
    home_group_rank = _optional_int(payload.get("home_group_rank"))
    away_group_rank = _optional_int(payload.get("away_group_rank"))
    if min(odds_home, odds_draw, odds_away) <= 1.0:
        odds_home, odds_draw, odds_away = 2.20, 3.10, 2.80

    return AppMatch(
        home_team=home_team,
        away_team=away_team,
        league=league,
        match_time=match_time,
        match_date=match_date,
        odds_home=odds_home,
        odds_draw=odds_draw,
        odds_away=odds_away,
        handicap_line=handicap_line,
        opening_odds_home=opening_odds_home,
        opening_odds_draw=opening_odds_draw,
        opening_odds_away=opening_odds_away,
        return_rate=return_rate,
        kelly_home=kelly_home,
        kelly_draw=kelly_draw,
        kelly_away=kelly_away,
        source=source,
        source_id=normalize_text(payload.get("source_id", "")),
        competition_group=competition_group,
        group_round=group_round,
        home_points=home_points,
        away_points=away_points,
        home_goal_diff=home_goal_diff,
        away_goal_diff=away_goal_diff,
        home_group_rank=home_group_rank,
        away_group_rank=away_group_rank,
    )


def _snapshot_lookup_key(match_date: str, league: str, home_team: str, away_team: str) -> tuple[str, str, str, str]:
    return (
        normalize_text(match_date),
        normalize_text(league),
        normalize_text(home_team),
        normalize_text(away_team),
    )


def _snapshot_lookup_team_key(match_date: str, home_team: str, away_team: str) -> tuple[str, str, str]:
    return (
        normalize_text(match_date),
        normalize_text(home_team),
        normalize_text(away_team),
    )


def _snapshot_result_schedule_id(source: object, source_id: object) -> str:
    resolved_source = normalize_text(source).lower()
    resolved_id = normalize_text(source_id)
    if not resolved_id:
        return ""
    if "titan" in resolved_source:
        return resolved_id
    if resolved_source in {"cache", "cache_stale"} and resolved_id.isdigit() and len(resolved_id) >= 5:
        return resolved_id
    return ""


def _market_snapshot_exact_key(match_date: str, league: str, home_team: str, away_team: str) -> str:
    return "exact|" + "|".join(
        [
            normalize_text(match_date),
            normalize_text(league),
            normalize_text(home_team),
            normalize_text(away_team),
        ]
    )


def _market_snapshot_team_key(match_date: str, home_team: str, away_team: str) -> str:
    return "team|" + "|".join(
        [
            normalize_text(match_date),
            normalize_text(home_team),
            normalize_text(away_team),
        ]
    )


def _market_snapshot_source_key(source_id: str) -> str:
    return f"source|{normalize_text(source_id)}"


def _market_snapshot_fields_from_match(match: AppMatch) -> dict[str, float]:
    return {
        "odds_home": round(_safe_float(match.odds_home, default=0.0), 4),
        "odds_draw": round(_safe_float(match.odds_draw, default=0.0), 4),
        "odds_away": round(_safe_float(match.odds_away, default=0.0), 4),
        "handicap_line": round(_safe_float(match.handicap_line, default=0.0), 4),
        "opening_odds_home": round(_safe_float(match.opening_odds_home, default=0.0), 4),
        "opening_odds_draw": round(_safe_float(match.opening_odds_draw, default=0.0), 4),
        "opening_odds_away": round(_safe_float(match.opening_odds_away, default=0.0), 4),
        "return_rate": round(_safe_float(match.return_rate, default=0.0), 4),
        "kelly_home": round(_safe_float(match.kelly_home, default=0.0), 4),
        "kelly_draw": round(_safe_float(match.kelly_draw, default=0.0), 4),
        "kelly_away": round(_safe_float(match.kelly_away, default=0.0), 4),
    }


def _has_market_snapshot_fields(match: AppMatch) -> bool:
    fields = _market_snapshot_fields_from_match(match)
    return any(value > 0.0 for value in fields.values())


def _has_market_enrichment_fields(match: AppMatch) -> bool:
    fields = _market_snapshot_fields_from_match(match)
    return any(
        fields.get(name, 0.0) > 0.0
        for name in (
            "opening_odds_home",
            "opening_odds_draw",
            "opening_odds_away",
            "return_rate",
            "kelly_home",
            "kelly_draw",
            "kelly_away",
        )
    )


def _apply_market_snapshot_fields(match: AppMatch, fields: dict) -> bool:
    if not isinstance(fields, dict):
        return False
    changed = False
    for name in (
        "opening_odds_home",
        "opening_odds_draw",
        "opening_odds_away",
        "return_rate",
        "kelly_home",
        "kelly_draw",
        "kelly_away",
    ):
        current = _safe_float(getattr(match, name, 0.0), default=0.0)
        incoming = _safe_float(fields.get(name), default=0.0)
        if current <= 0.0 and incoming > 0.0:
            setattr(match, name, incoming)
            changed = True
    return changed


def persist_market_snapshot(match: AppMatch) -> int:
    if not isinstance(match, AppMatch) or not _has_market_snapshot_fields(match):
        return 0
    saved = 0
    record = {
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "match": {
            "match_id": match.match_id,
            "source_id": normalize_text(match.source_id),
            "match_date": match.match_date,
            "match_time": match.match_time,
            "league": match.league,
            "home_team": match.home_team,
            "away_team": match.away_team,
            "source": match.source,
        },
        "market": _market_snapshot_fields_from_match(match),
    }
    keys = [
        _market_snapshot_exact_key(match.match_date, match.league, match.home_team, match.away_team),
        _market_snapshot_team_key(match.match_date, match.home_team, match.away_team),
    ]
    source_id = normalize_text(match.source_id)
    if source_id:
        keys.insert(0, _market_snapshot_source_key(source_id))
    for snapshot_id in keys:
        STATE_STORE.upsert_market_snapshot(snapshot_id, record)
        saved += 1
    return saved


def persist_market_snapshots(matches: Iterable[AppMatch]) -> int:
    rows = [match for match in matches if isinstance(match, AppMatch) and _has_market_snapshot_fields(match)]
    if not rows:
        return 0
    try:
        items = STATE_STORE.load_market_snapshots()
    except Exception:
        items = {}
    if not isinstance(items, dict):
        items = {}
    saved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = 0
    for match in rows:
        record = _market_snapshot_record_for_match(match, saved_at=saved_at)
        for snapshot_id in _market_snapshot_keys_for_match(match):
            merged = _merge_market_snapshot_record(items.get(snapshot_id), record)
            _ordered_upsert(items, snapshot_id, merged, limit=5000)
            total += 1
    if total:
        STATE_STORE.save_market_snapshots(items)
        _MARKET_SNAPSHOT_RECORD_CACHE["signature"] = _state_store_path_signature("market_snapshots_file")
        _MARKET_SNAPSHOT_RECORD_CACHE["items"] = items
    return total


def _ordered_upsert(items: dict[str, dict], key: str, record: dict, *, limit: int) -> None:
    if key in items:
        del items[key]
    items[key] = record
    if len(items) > limit:
        overflow = len(items) - limit
        stale_keys = list(items.keys())[:overflow]
        for stale_key in stale_keys:
            items.pop(stale_key, None)


def _market_snapshot_record_for_match(match: AppMatch, *, saved_at: str) -> dict:
    return {
        "saved_at": saved_at,
        "match": {
            "match_id": match.match_id,
            "source_id": normalize_text(match.source_id),
            "match_date": match.match_date,
            "match_time": match.match_time,
            "league": match.league,
            "home_team": match.home_team,
            "away_team": match.away_team,
            "source": match.source,
        },
        "market": _market_snapshot_fields_from_match(match),
    }


def _merge_market_snapshot_record(existing: dict | None, record: dict) -> dict:
    history: list[dict] = []
    if isinstance(existing, dict):
        existing_history = existing.get("history")
        if isinstance(existing_history, list):
            history.extend(item for item in existing_history if isinstance(item, dict))
        else:
            existing_market = existing.get("market")
            if isinstance(existing_market, dict):
                history.append(
                    {
                        "saved_at": str(existing.get("saved_at") or ""),
                        "market": dict(existing_market),
                    }
                )
    market = record.get("market")
    if isinstance(market, dict):
        history.append(
            {
                "saved_at": str(record.get("saved_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                "market": dict(market),
            }
        )
    deduped: dict[str, dict] = {}
    for item in history:
        key = f"{item.get('saved_at', '')}|{json.dumps(item.get('market', {}), sort_keys=True, ensure_ascii=False)}"
        deduped[key] = item
    merged = dict(record)
    merged["history"] = list(deduped.values())[-48:]
    return merged


def _market_snapshot_keys_for_match(match: AppMatch) -> list[str]:
    keys = [
        _market_snapshot_exact_key(match.match_date, match.league, match.home_team, match.away_team),
        _market_snapshot_team_key(match.match_date, match.home_team, match.away_team),
    ]
    source_id = normalize_text(match.source_id)
    if source_id:
        keys.insert(0, _market_snapshot_source_key(source_id))
    return keys


def enrich_match_from_market_snapshot_store(match: AppMatch) -> bool:
    if not isinstance(match, AppMatch) or _has_market_enrichment_fields(match):
        return False
    items = STATE_STORE.load_market_snapshots()
    candidates: list[str] = []
    source_id = normalize_text(match.source_id)
    if source_id:
        candidates.append(_market_snapshot_source_key(source_id))
    candidates.append(_market_snapshot_exact_key(match.match_date, match.league, match.home_team, match.away_team))
    candidates.append(_market_snapshot_team_key(match.match_date, match.home_team, match.away_team))
    for key in candidates:
        record = items.get(key)
        if not isinstance(record, dict):
            continue
        market = record.get("market")
        if _apply_market_snapshot_fields(match, market):
            return True
    return False


def enrich_matches_from_market_snapshot_store(matches: list[AppMatch], diagnostics: FetchDiagnostics | None = None) -> int:
    enriched = 0
    for match in matches:
        if enrich_match_from_market_snapshot_store(match):
            enriched += 1
    if diagnostics is not None and enriched > 0:
        diagnostics.add(f"赛前市场快照回填成功: {enriched} 场。")
    return enriched


def dedupe_matches(matches: Iterable[AppMatch]) -> list[AppMatch]:
    unique: dict[str, AppMatch] = {}
    for match in matches:
        unique[match.match_id] = match
    return list(unique.values())


def _serialize_raw_matches(raw_matches: Iterable[object]) -> list[dict]:
    serialized_matches: list[dict] = []
    for raw in raw_matches:
        serialized_matches.append(
            {
                "home_team": getattr(raw, "home_team", ""),
                "away_team": getattr(raw, "away_team", ""),
                "league": getattr(raw, "league", ""),
                "match_time": getattr(raw, "match_time", ""),
                "match_date": getattr(raw, "match_date", ""),
                "odds_home": getattr(raw, "odds_home", 0),
                "odds_draw": getattr(raw, "odds_draw", 0),
                "odds_away": getattr(raw, "odds_away", 0),
                "handicap_line": getattr(raw, "handicap_line", 0.0),
                "opening_odds_home": getattr(raw, "opening_odds_home", 0.0),
                "opening_odds_draw": getattr(raw, "opening_odds_draw", 0.0),
                "opening_odds_away": getattr(raw, "opening_odds_away", 0.0),
                "return_rate": getattr(raw, "return_rate", 0.0),
                "kelly_home": getattr(raw, "kelly_home", 0.0),
                "kelly_draw": getattr(raw, "kelly_draw", 0.0),
                "kelly_away": getattr(raw, "kelly_away", 0.0),
                "source_id": getattr(raw, "source_id", "") or getattr(raw, "match_id", ""),
            }
        )
    return serialized_matches


def save_matches_cache(matches: Iterable[AppMatch], *, source: str = "live") -> int:
    serialized_matches = _serialize_raw_matches(matches)
    if not serialized_matches:
        return 0
    payload = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
        "matches": serialized_matches,
    }
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = CACHE_FILE.with_suffix(CACHE_FILE.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(CACHE_FILE)
    return len(serialized_matches)


def _compute_live_source_health_score(*, raw_count: int, valid_count: int, merged_count: int) -> int:
    raw = max(0, int(raw_count))
    valid = max(0, int(valid_count))
    merged = max(0, int(merged_count))
    if raw <= 0 or valid <= 0 or merged <= 0:
        return 0
    valid_rate = _clamp(valid / max(raw, 1), 0.0, 1.0)
    coverage_rate = _clamp(valid / max(merged, 1), 0.0, 1.0)
    score = (valid_rate * 0.55 + coverage_rate * 0.45) * 100.0
    return int(round(score))


def load_cached_payload() -> tuple[dict | None, FetchDiagnostics]:
    diagnostics = FetchDiagnostics(source="cache")
    diagnostics.cache_exists = CACHE_FILE.exists()
    diagnostics.fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not CACHE_FILE.exists():
        diagnostics.add("本地缓存不存在。")
        return None, diagnostics

    try:
        payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        diagnostics.add(f"本地缓存读取失败: {exc}")
        return None, diagnostics

    cache_date = normalize_text(payload.get("date", ""))
    cache_matches = payload.get("matches", [])
    diagnostics.cache_date = cache_date
    diagnostics.cache_match_count = len(cache_matches) if isinstance(cache_matches, list) else 0
    today = datetime.now().strftime("%Y-%m-%d")
    if _looks_like_date(cache_date):
        diagnostics.cache_age_days = (datetime.now().date() - datetime.strptime(cache_date, "%Y-%m-%d").date()).days
    diagnostics.cache_fresh = cache_date == today
    if diagnostics.cache_fresh:
        diagnostics.add("发现当日缓存，可作为有效赛事源。")
    else:
        diagnostics.add(f"缓存日期不是今天: {cache_date or '空'}")

    return payload, diagnostics


def fixture_page_guard_from_items(items: list[dict], source: str) -> tuple[list[AppMatch], list[str]]:
    matches: list[AppMatch] = []
    messages: list[str] = []

    for item in items:
        match = _to_app_match(item, source=source)
        if match is not None:
            matches.append(match)

    if not matches:
        messages.append("页面校验失败: 没有解析出任何有效赛事。")
        return [], messages

    filtered = len(items) - len(matches)
    if filtered > 0:
        messages.append(f"页面校验过滤了 {filtered} 条异常赛事。")
    else:
        messages.append("页面校验通过: 赛事字段完整且可读。")

    return dedupe_matches(matches), messages


def _enrich_matches_with_market_intent(matches: list[AppMatch], diagnostics: FetchDiagnostics) -> None:
    if not matches or MarketIntentFetcher500 is None:
        return
    try:
        fetcher = MarketIntentFetcher500(PROJECT_DIR, debug=False)
        enriched = int(fetcher.enrich_matches(matches))
        if enriched > 0:
            diagnostics.add(f"500 市场意图补强成功: {enriched} 场已补开赔/返还率/凯利。")
        else:
            diagnostics.add("500 市场意图补强未命中任何赛事。")
    except Exception as exc:
        diagnostics.add(f"500 市场意图补强失败: {exc}")


def _persist_market_snapshots_with_diagnostics(matches: list[AppMatch], diagnostics: FetchDiagnostics) -> None:
    saved = persist_market_snapshots(matches)
    if saved > 0:
        diagnostics.add(f"赛前市场快照已落盘: {saved} 条索引。")


def fetch_matches_v24(strict_today: bool = True, force_live: bool = False, cache_only: bool = False) -> FetchResult:
    diagnostics = FetchDiagnostics(
        source="none",
        fetched_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    payload, cache_diagnostics = load_cached_payload()
    diagnostics.cache_exists = cache_diagnostics.cache_exists
    diagnostics.cache_fresh = cache_diagnostics.cache_fresh
    diagnostics.cache_date = cache_diagnostics.cache_date
    diagnostics.cache_match_count = cache_diagnostics.cache_match_count
    diagnostics.cache_age_days = cache_diagnostics.cache_age_days
    diagnostics.messages.extend(cache_diagnostics.messages)
    cache_date_text = normalize_text(payload.get("date", "")) if payload else ""

    fallback_cache_matches: list[AppMatch] = []
    fallback_cache_messages: list[str] = []
    fallback_cache_source = "cache"
    if payload and payload.get("matches"):
        cache_age_days = diagnostics.cache_age_days
        cache_can_fallback = diagnostics.cache_fresh or (
            strict_today and cache_age_days is not None and 0 <= cache_age_days <= 2
        )
        if cache_can_fallback:
            fallback_cache_source = "cache" if diagnostics.cache_fresh else "cache_stale"
            fallback_cache_matches, fallback_cache_messages = fixture_page_guard_from_items(
                payload.get("matches", []),
                source=fallback_cache_source,
            )
            if fallback_cache_matches:
                if diagnostics.cache_fresh:
                    diagnostics.add(f"检测到当日缓存({cache_date_text})，在线源不可用时可回退。")
                else:
                    diagnostics.add(f"检测到可回退缓存({cache_date_text})，若在线源不可用将自动启用。")

    def try_cache_fallback(reason: str) -> FetchResult | None:
        if not fallback_cache_matches:
            return None
        diagnostics.fixture_source_guard = True
        diagnostics.fixture_page_guard = True
        diagnostics.source = fallback_cache_source
        diagnostics.messages.extend(fallback_cache_messages)
        enrich_matches_from_market_snapshot_store(fallback_cache_matches, diagnostics)
        _enrich_matches_with_market_intent(fallback_cache_matches, diagnostics)
        _persist_market_snapshots_with_diagnostics(fallback_cache_matches, diagnostics)
        cache_label = "当日缓存" if fallback_cache_source == "cache" else "最近缓存"
        diagnostics.add(
            f"{reason}，已回退到{cache_label}({cache_date_text})，共 {len(fallback_cache_matches)} 场。"
        )
        return FetchResult(matches=fallback_cache_matches, diagnostics=diagnostics)

    if cache_only:
        diagnostics.add("手动读取回退缓存: 本次不访问在线源。")
        fallback_result = try_cache_fallback("手动读取回退缓存")
        if fallback_result is not None:
            return fallback_result
        diagnostics.add("没有可用回退缓存，无法完成缓存读取。")
        return FetchResult(matches=[], diagnostics=diagnostics)

    if payload and payload.get("matches"):
        if force_live:
            diagnostics.add("手动重试在线源: 本次跳过缓存优先读取。")
        elif strict_today and not diagnostics.cache_fresh:
            diagnostics.add("fixture_source_guard 拒绝使用过期缓存。")
        else:
            diagnostics.add("当日缓存已准备为回退池，本次仍优先尝试在线源。")

    fetchers: list[tuple[str, object]] = []
    if MatchFetcherTitan is not None:
        fetchers.append(("titan", MatchFetcherTitan(debug=False)))
    if MatchFetcher500 is not None:
        fetchers.append(("500", MatchFetcher500(debug=False)))

    if not fetchers:
        diagnostics.add("未加载到任何在线抓取器。")
        fallback_result = try_cache_fallback("主数据源不可用")
        if fallback_result is not None:
            return fallback_result
        return FetchResult(matches=[], diagnostics=diagnostics)

    source_reports: list[dict] = []
    live_all_matches: list[AppMatch] = []
    for source_name, fetcher in fetchers:
        try:
            raw_matches = fetcher.get_today_matches()
        except Exception as exc:
            diagnostics.add(f"{source_name} 在线抓取失败: {exc}")
            source_reports.append(
                {"source": source_name, "status": "error", "raw_count": 0, "valid_count": 0, "error": str(exc)}
            )
            continue

        serialized_matches = _serialize_raw_matches(raw_matches)
        raw_count = len(serialized_matches)
        if raw_count <= 0:
            diagnostics.add(f"{source_name} 在线抓取未返回任何赛事。")
            source_reports.append({"source": source_name, "status": "empty", "raw_count": 0, "valid_count": 0})
            continue

        diagnostics.fixture_source_guard = True
        matches, messages = fixture_page_guard_from_items(
            serialized_matches,
            source=f"live:{source_name}",
        )
        for message in messages:
            diagnostics.add(f"{source_name}: {message}")
        if not matches:
            diagnostics.add(f"{source_name} 在线赛事未通过页面字段校验。")
            source_reports.append(
                {"source": source_name, "status": "guard_reject", "raw_count": raw_count, "valid_count": 0}
            )
            continue

        source_reports.append(
            {"source": source_name, "status": "ready", "raw_count": raw_count, "valid_count": len(matches)}
        )
        live_all_matches.extend(matches)

    diagnostics.source_reports = [dict(item) for item in source_reports]

    if live_all_matches:
        merged_matches = dedupe_matches(live_all_matches)
        merged_count = len(merged_matches)
        ready_reports = [item for item in source_reports if str(item.get("status")) == "ready"]
        for item in ready_reports:
            raw_count = int(item.get("raw_count", 0))
            valid_count = int(item.get("valid_count", 0))
            coverage = _clamp(valid_count / max(merged_count, 1), 0.0, 1.0)
            score = _compute_live_source_health_score(
                raw_count=raw_count,
                valid_count=valid_count,
                merged_count=merged_count,
            )
            item["coverage"] = round(coverage, 4)
            item["health_score"] = score

        ready_reports.sort(
            key=lambda item: (
                -int(item.get("health_score", 0)),
                -int(item.get("valid_count", 0)),
                str(item.get("source", "")),
            )
        )
        primary_source = str(ready_reports[0].get("source", "")) if ready_reports else "unknown"
        diagnostics.fixture_page_guard = True
        diagnostics.source = f"live:{primary_source}" if len(ready_reports) <= 1 else f"live:hybrid(primary={primary_source})"
        diagnostics.source_reports = [dict(item) for item in source_reports]

        for item in ready_reports:
            diagnostics.add(
                "源健康[{source}]: raw={raw} valid={valid} coverage={coverage:.1%} score={score}".format(
                    source=item.get("source", "-"),
                    raw=int(item.get("raw_count", 0)),
                    valid=int(item.get("valid_count", 0)),
                    coverage=float(item.get("coverage", 0.0) or 0.0),
                    score=int(item.get("health_score", 0)),
                )
            )
        for item in source_reports:
            status = str(item.get("status", ""))
            if status in {"ready", ""}:
                continue
            diagnostics.add(
                f"源状态[{item.get('source', '-')}] {status}: raw={int(item.get('raw_count', 0))} valid={int(item.get('valid_count', 0))}"
            )

        max_single_valid = max((int(item.get("valid_count", 0)) for item in ready_reports), default=0)
        if merged_count > max_single_valid:
            diagnostics.add(f"多源合并增益: +{merged_count - max_single_valid} 场（合并后 {merged_count} 场）")
        else:
            diagnostics.add(f"多源合并完成: {merged_count} 场（无新增去重增益）")

        enrich_matches_from_market_snapshot_store(merged_matches, diagnostics)
        _enrich_matches_with_market_intent(merged_matches, diagnostics)
        _persist_market_snapshots_with_diagnostics(merged_matches, diagnostics)
        try:
            cached_count = save_matches_cache(merged_matches, source=diagnostics.source)
            if cached_count > 0:
                diagnostics.cache_exists = True
                diagnostics.cache_fresh = True
                diagnostics.cache_date = datetime.now().strftime("%Y-%m-%d")
                diagnostics.cache_match_count = cached_count
                diagnostics.cache_age_days = 0
                diagnostics.add(f"在线源成功后已更新本地赛事回退缓存: {cached_count} 场。")
        except Exception as exc:
            diagnostics.add(f"本地赛事回退缓存写入失败: {exc}")
        return FetchResult(matches=merged_matches, diagnostics=diagnostics)

    fallback_result = try_cache_fallback("所有在线源均不可用")
    if fallback_result is not None:
        return fallback_result
    return FetchResult(matches=[], diagnostics=diagnostics)


def _normalize_probs(home: float, draw: float, away: float) -> tuple[float, float, float]:
    total = max(home + draw + away, 1e-9)
    return home / total, draw / total, away / total


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(value, high))


def _strength_score(rating: float) -> float:
    return _clamp((rating - 1300.0) / 4.0, 0.0, 100.0)


def _distribution_entropy(probs: tuple[float, float, float]) -> float:
    entropy = 0.0
    for prob in probs:
        p = max(prob, 1e-12)
        entropy -= p * log2(p)
    return entropy / log2(3.0)


def _market_entropy_side_label(side: str) -> str:
    return {"home": "home", "draw": "draw", "away": "away"}.get(str(side or ""), "-")


def _market_snapshot_candidate_keys(match: AppMatch) -> list[str]:
    keys: list[str] = []
    source_id = normalize_text(match.source_id)
    if source_id:
        keys.append(_market_snapshot_source_key(source_id))
    keys.append(_market_snapshot_exact_key(match.match_date, match.league, match.home_team, match.away_team))
    keys.append(_market_snapshot_team_key(match.match_date, match.home_team, match.away_team))
    return keys


def _normalize_market_history_point(item: object, *, fallback_saved_at: object = "") -> dict | None:
    if not isinstance(item, dict):
        return None
    market = item.get("market") if isinstance(item.get("market"), dict) else item
    if not isinstance(market, dict):
        return None
    point = {
        "saved_at": normalize_text(item.get("saved_at") or fallback_saved_at),
        "odds_home": round(_safe_float(market.get("odds_home"), default=0.0), 4),
        "odds_draw": round(_safe_float(market.get("odds_draw"), default=0.0), 4),
        "odds_away": round(_safe_float(market.get("odds_away"), default=0.0), 4),
        "kelly_home": round(_safe_float(market.get("kelly_home"), default=0.0), 4),
        "kelly_draw": round(_safe_float(market.get("kelly_draw"), default=0.0), 4),
        "kelly_away": round(_safe_float(market.get("kelly_away"), default=0.0), 4),
        "return_rate": round(_safe_float(market.get("return_rate"), default=0.0), 4),
    }
    if not any(point.get(name, 0.0) > 0.0 for name in ("odds_home", "odds_draw", "odds_away")):
        return None
    return point


def _market_snapshot_history_for_match(match: AppMatch) -> list[dict]:
    if not isinstance(match, AppMatch):
        return []
    try:
        signature = _path_signature(STATE_STORE.market_snapshots_file)
        if _MARKET_SNAPSHOT_RECORD_CACHE.get("signature") == signature:
            items = _MARKET_SNAPSHOT_RECORD_CACHE.get("items", {})
        else:
            items = STATE_STORE.load_market_snapshots()
            _MARKET_SNAPSHOT_RECORD_CACHE["signature"] = signature
            _MARKET_SNAPSHOT_RECORD_CACHE["items"] = items
    except Exception:
        return []
    if not isinstance(items, dict):
        return []
    points: list[dict] = []
    for key in _market_snapshot_candidate_keys(match):
        record = items.get(key)
        if not isinstance(record, dict):
            continue
        history = record.get("history")
        if isinstance(history, list):
            for item in history:
                point = _normalize_market_history_point(item, fallback_saved_at=record.get("saved_at"))
                if point is not None:
                    points.append(point)
        point = _normalize_market_history_point(record, fallback_saved_at=record.get("saved_at"))
        if point is not None:
            points.append(point)
    deduped: dict[str, dict] = {}
    for point in points:
        key = "|".join(
            [
                str(point.get("saved_at") or ""),
                f"{_safe_float(point.get('odds_home'), 0.0):.4f}",
                f"{_safe_float(point.get('odds_draw'), 0.0):.4f}",
                f"{_safe_float(point.get('odds_away'), 0.0):.4f}",
            ]
        )
        deduped[key] = point
    return sorted(
        deduped.values(),
        key=lambda point: _parse_datetime_text(point.get("saved_at")) or datetime.min,
    )


def _market_entropy_sequence_metrics(history_points: object, current: dict[str, float], kelly: dict[str, float]) -> dict:
    points: list[dict] = []
    if isinstance(history_points, list):
        for item in history_points:
            point = _normalize_market_history_point(item)
            if point is not None:
                points.append(point)
    points.append(
        {
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "odds_home": round(_safe_float(current.get("home"), default=0.0), 4),
            "odds_draw": round(_safe_float(current.get("draw"), default=0.0), 4),
            "odds_away": round(_safe_float(current.get("away"), default=0.0), 4),
            "kelly_home": round(_safe_float(kelly.get("home"), default=0.0), 4),
            "kelly_draw": round(_safe_float(kelly.get("draw"), default=0.0), 4),
            "kelly_away": round(_safe_float(kelly.get("away"), default=0.0), 4),
        }
    )
    deduped: dict[str, dict] = {}
    for point in points:
        key = "|".join(
            [
                str(point.get("saved_at") or ""),
                f"{_safe_float(point.get('odds_home'), 0.0):.4f}",
                f"{_safe_float(point.get('odds_draw'), 0.0):.4f}",
                f"{_safe_float(point.get('odds_away'), 0.0):.4f}",
            ]
        )
        deduped[key] = point
    points = sorted(
        deduped.values(),
        key=lambda point: _parse_datetime_text(point.get("saved_at")) or datetime.min,
    )
    if len(points) < 2:
        return {
            "sample_count": len(points),
            "latest_interval_minutes": 0.0,
            "latest_velocity": {},
            "max_abs_velocity_per_minute": 0.0,
            "max_step_change": 0.0,
            "step_side": "-",
        }

    latest_velocity: dict[str, float] = {}
    max_abs_velocity = 0.0
    max_step_change = 0.0
    step_side = "-"
    latest_interval_minutes = 0.0
    sides = {"home": "odds_home", "draw": "odds_draw", "away": "odds_away"}
    for index in range(1, len(points)):
        prev = points[index - 1]
        curr = points[index]
        prev_dt = _parse_datetime_text(prev.get("saved_at"))
        curr_dt = _parse_datetime_text(curr.get("saved_at"))
        interval = 0.0
        if prev_dt is not None and curr_dt is not None:
            interval = max((curr_dt - prev_dt).total_seconds() / 60.0, 1.0)
        if index == len(points) - 1:
            latest_interval_minutes = round(interval, 3)
        for side, field_name in sides.items():
            prev_value = _safe_float(prev.get(field_name), default=0.0)
            curr_value = _safe_float(curr.get(field_name), default=0.0)
            if prev_value <= 1.0 or curr_value <= 1.0:
                continue
            change = (prev_value - curr_value) / max(prev_value, 1e-9)
            if abs(change) > abs(max_step_change):
                max_step_change = change
                step_side = side
            velocity = change / interval if interval > 0 else 0.0
            if index == len(points) - 1:
                latest_velocity[side] = round(velocity, 5)
            max_abs_velocity = max(max_abs_velocity, abs(velocity))
    return {
        "sample_count": len(points),
        "latest_interval_minutes": latest_interval_minutes,
        "latest_velocity": latest_velocity,
        "max_abs_velocity_per_minute": round(max_abs_velocity, 5),
        "max_step_change": round(max_step_change, 4),
        "step_side": _market_entropy_side_label(step_side),
    }


def build_market_entropy_signal(
    match: AppMatch,
    *,
    recommendation_key: str = "",
    recommendation_confidence: float = 0.0,
    history_points: list[dict] | None = None,
) -> dict:
    current = {
        "home": _safe_float(match.odds_home, default=0.0),
        "draw": _safe_float(match.odds_draw, default=0.0),
        "away": _safe_float(match.odds_away, default=0.0),
    }
    opening = {
        "home": _safe_float(match.opening_odds_home, default=0.0),
        "draw": _safe_float(match.opening_odds_draw, default=0.0),
        "away": _safe_float(match.opening_odds_away, default=0.0),
    }
    kelly = {
        "home": _safe_float(match.kelly_home, default=0.0),
        "draw": _safe_float(match.kelly_draw, default=0.0),
        "away": _safe_float(match.kelly_away, default=0.0),
    }
    valid_current = {side: value for side, value in current.items() if value > 1.0}
    valid_opening = {
        side: value
        for side, value in opening.items()
        if value > 1.0 and current.get(side, 0.0) > 1.0
    }
    valid_kelly = {side: value for side, value in kelly.items() if value > 0.0}
    implied_probs: dict[str, float] = {}
    if len(valid_current) == 3:
        implied = {side: 1.0 / max(value, 1.01) for side, value in current.items()}
        total = max(sum(implied.values()), 1e-9)
        implied_probs = {side: round(value / total, 4) for side, value in implied.items()}
    market_favorite = max(implied_probs, key=implied_probs.get) if implied_probs else "-"
    odds_slope: dict[str, float] = {}
    for side, open_value in valid_opening.items():
        odds_slope[side] = round((open_value - current[side]) / max(open_value, 1e-9), 4)
    strongest_steam_side = max(odds_slope, key=odds_slope.get) if odds_slope else "-"
    max_abs_slope = max((abs(value) for value in odds_slope.values()), default=0.0)
    sequence_metrics = _market_entropy_sequence_metrics(history_points or [], current, kelly)
    max_abs_velocity = _safe_float(sequence_metrics.get("max_abs_velocity_per_minute"), default=0.0)
    max_step_change = abs(_safe_float(sequence_metrics.get("max_step_change"), default=0.0))
    kelly_span = max(valid_kelly.values()) - min(valid_kelly.values()) if len(valid_kelly) == 3 else 0.0
    kelly_avg = sum(valid_kelly.values()) / len(valid_kelly) if valid_kelly else 0.0
    kelly_deviation = max((abs(value - kelly_avg) for value in valid_kelly.values()), default=0.0)
    kelly_low_side = min(valid_kelly, key=valid_kelly.get) if valid_kelly else "-"
    pick_key = recommendation_key if recommendation_key in {"home", "draw", "away"} else ""
    pick_slope = odds_slope.get(pick_key, 0.0) if pick_key else 0.0
    pick_kelly_gap = (valid_kelly.get(pick_key, 0.0) - min(valid_kelly.values())) if pick_key and valid_kelly else 0.0

    signals: list[str] = []
    slope_score = _clamp(max_abs_slope / 0.08)
    velocity_score = _clamp(max_abs_velocity / 0.006)
    history_step_score = _clamp(max_step_change / 0.08)
    kelly_score = _clamp(max(0.0, kelly_span - 0.03) / 0.09)
    conflict_score = 0.0
    if pick_key and recommendation_confidence >= 0.55 and pick_slope <= -0.04:
        conflict_score = max(conflict_score, _clamp(abs(pick_slope) / 0.08))
        signals.append("pick_odds_drifting_out")
    if pick_key and strongest_steam_side in {"home", "draw", "away"} and strongest_steam_side != pick_key and odds_slope.get(strongest_steam_side, 0.0) >= 0.04:
        conflict_score = max(conflict_score, _clamp(odds_slope.get(strongest_steam_side, 0.0) / 0.08))
        signals.append("market_steam_against_pick")
    if pick_key and pick_kelly_gap >= 0.05:
        conflict_score = max(conflict_score, _clamp(pick_kelly_gap / 0.12))
        signals.append("kelly_against_pick")
    if max_abs_slope >= 0.06:
        signals.append("odds_step_change")
    elif max_abs_slope >= 0.035:
        signals.append("odds_slope_watch")
    if max_abs_velocity >= 0.006:
        signals.append("odds_velocity_alert")
    elif max_abs_velocity >= 0.003:
        signals.append("odds_velocity_watch")
    if max_step_change >= 0.07:
        signals.append("odds_history_step_alert")
    elif max_step_change >= 0.04:
        signals.append("odds_history_step_watch")
    if kelly_span >= 0.08:
        signals.append("kelly_span_alert")
    elif kelly_span >= 0.05:
        signals.append("kelly_span_watch")
    if market_favorite != "-" and pick_key and market_favorite != pick_key and recommendation_confidence >= 0.60:
        conflict_score = max(conflict_score, 0.45)
        signals.append("market_favorite_mismatch")

    score = _clamp(
        0.25 * slope_score
        + 0.18 * velocity_score
        + 0.12 * history_step_score
        + 0.25 * kelly_score
        + 0.20 * conflict_score
    )
    if score >= 0.66:
        level = "HIGH"
    elif score >= 0.38:
        level = "MEDIUM"
    else:
        level = "LOW"
    return {
        "score": round(score, 4),
        "level": level,
        "signals": signals,
        "odds_slope": odds_slope,
        "max_abs_odds_slope": round(max_abs_slope, 4),
        "sequence": sequence_metrics,
        "strongest_steam_side": _market_entropy_side_label(strongest_steam_side),
        "market_favorite": _market_entropy_side_label(market_favorite),
        "pick_side": _market_entropy_side_label(pick_key),
        "pick_slope": round(pick_slope, 4),
        "kelly": {side: round(value, 4) for side, value in kelly.items()},
        "kelly_span": round(kelly_span, 4),
        "kelly_deviation": round(kelly_deviation, 4),
        "kelly_low_side": _market_entropy_side_label(kelly_low_side),
        "pick_kelly_gap": round(pick_kelly_gap, 4),
        "return_rate": round(_safe_float(match.return_rate, default=0.0), 4),
        "implied_probabilities": implied_probs,
    }


def _edge_side_from_margin(value: float, *, threshold: float = 0.20) -> str:
    if value > threshold:
        return "home"
    if value < -threshold:
        return "away"
    return "balanced"


def _market_side_from_handicap_line(handicap_line: float, *, threshold: float = 0.25) -> str:
    line = _safe_float(handicap_line, default=0.0)
    if line < -threshold:
        return "home"
    if line > threshold:
        return "away"
    return "balanced"


def build_handicap_margin_consistency_signal(
    match: AppMatch,
    *,
    model_margin_goals: float,
    probabilities: dict | None = None,
    handicap_probabilities: dict | None = None,
    recommendation_key: str = "",
    handicap_pick_key: str = "",
) -> dict:
    handicap_line = _safe_float(getattr(match, "handicap_line", 0.0), default=0.0)
    model_margin = _safe_float(model_margin_goals, default=0.0)
    market_side = _market_side_from_handicap_line(handicap_line)
    model_side = _edge_side_from_margin(model_margin)
    handicap_pick_side = handicap_pick_key if handicap_pick_key in {"home", "draw", "away"} else "-"
    model_pick_side = recommendation_key if recommendation_key in {"home", "draw", "away"} else model_side
    line_depth = abs(handicap_line)
    margin_depth = abs(model_margin)
    depth_gap = line_depth - margin_depth

    signals: list[str] = []
    direction_score = 0.0
    depth_score = 0.0
    pick_score = 0.0

    if market_side in {"home", "away"} and model_side in {"home", "away"} and market_side != model_side:
        signals.append("handicap_direction_mismatch")
        direction_score = 1.0
    elif market_side in {"home", "away"} and model_side == "balanced" and line_depth >= 0.75:
        signals.append("line_strong_but_model_balanced")
        direction_score = 0.70
    elif market_side == "balanced" and model_side in {"home", "away"} and margin_depth >= 0.75:
        signals.append("model_edge_not_priced")
        direction_score = 0.55

    if line_depth >= 0.75 and margin_depth <= max(0.35, line_depth - 0.55):
        signals.append("line_too_deep_for_model")
        depth_score = max(depth_score, _clamp((line_depth - margin_depth) / 1.20))
    if margin_depth >= 0.75 and line_depth <= max(0.25, margin_depth - 0.55):
        signals.append("model_margin_stronger_than_line")
        depth_score = max(depth_score, _clamp((margin_depth - line_depth) / 1.20))

    if handicap_pick_side in {"home", "away"} and model_side in {"home", "away"} and handicap_pick_side != model_side:
        signals.append("handicap_pick_margin_mismatch")
        pick_score = max(pick_score, 0.55)
    if model_pick_side in {"home", "away"} and model_side in {"home", "away"} and model_pick_side != model_side:
        signals.append("model_pick_margin_mismatch")
        pick_score = max(pick_score, 0.40)

    probs = probabilities if isinstance(probabilities, dict) else {}
    handicap_probs = handicap_probabilities if isinstance(handicap_probabilities, dict) else {}
    if model_side in {"home", "away"} and probs:
        opposite = "away" if model_side == "home" else "home"
        prob_gap = _safe_float(probs.get(model_side), default=0.0) - _safe_float(probs.get(opposite), default=0.0)
        if prob_gap < 0.08 and margin_depth >= 0.55:
            signals.append("margin_probability_gap_weak")
            pick_score = max(pick_score, 0.35)
    if handicap_pick_side in {"home", "away"} and handicap_probs:
        draw_prob = _safe_float(handicap_probs.get("draw"), default=0.0)
        pick_prob = _safe_float(handicap_probs.get(handicap_pick_side), default=0.0)
        if pick_prob - draw_prob < 0.06 and line_depth >= 0.75:
            signals.append("handicap_pick_edge_thin")
            pick_score = max(pick_score, 0.30)

    score = _clamp(0.45 * direction_score + 0.38 * depth_score + 0.17 * pick_score)
    if "handicap_direction_mismatch" in signals and (
        "handicap_pick_margin_mismatch" in signals or line_depth >= 0.75
    ):
        score = max(score, 0.70)
    if score >= 0.66:
        level = "HIGH"
    elif score >= 0.38:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "score": round(score, 4),
        "level": level,
        "signals": signals,
        "handicap_line": round(handicap_line, 4),
        "model_margin_goals": round(model_margin, 4),
        "market_side": market_side,
        "model_side": model_side,
        "model_pick_side": model_pick_side,
        "handicap_pick_side": handicap_pick_side,
        "line_depth": round(line_depth, 4),
        "margin_depth": round(margin_depth, 4),
        "depth_gap": round(depth_gap, 4),
    }


def _market_entropy_risk_overlay(base_risk_level: object, market_entropy: dict | None) -> dict:
    entropy = market_entropy if isinstance(market_entropy, dict) else {}
    base_bucket = _risk_bucket_from_label(base_risk_level)
    entropy_level = str(entropy.get("level") or "LOW").upper()
    entropy_score = _safe_float(entropy.get("score"), default=0.0)
    signals = entropy.get("signals") if isinstance(entropy.get("signals"), list) else []
    adjusted = base_risk_level
    applied = False
    reason = ""

    if entropy_level == "HIGH" and signals and base_bucket != "high":
        adjusted = "HIGH"
        applied = True
        reason = "market_entropy_high"
    elif entropy_level == "MEDIUM" and signals and base_bucket == "low":
        adjusted = "MEDIUM"
        applied = True
        reason = "market_entropy_medium"

    return {
        "applied": applied,
        "base_risk_level": base_risk_level,
        "adjusted_risk_level": adjusted,
        "entropy_level": entropy_level,
        "entropy_score": round(entropy_score, 4),
        "reason": reason,
    }


def _model_distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(abs(a[i] - b[i]) for i in range(3)) / 2.0


def _risk_level_from_upset(upset_index: float) -> str:
    if upset_index >= 0.66:
        return "高"
    if upset_index >= 0.45:
        return "中"
    return "低"


def _result_label(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "主胜"
    if home_goals < away_goals:
        return "客胜"
    return "平局"


def _result_to_label(result: str) -> int | None:
    mapping = {"主胜": 0, "平局": 1, "客胜": 2}
    return mapping.get(result)


def _ou_result_label(total_goals: int, line: float = 2.5) -> str:
    return f"大{line}" if total_goals > line else f"小{line}"


def _extract_ou_prediction(prediction: dict | None, line: float = 2.5) -> tuple[str | None, float | None]:
    if not prediction:
        return None, None

    direct_pick = prediction.get("ou_recommendation")
    if direct_pick:
        return str(direct_pick), _safe_float(prediction.get("ou_confidence"), default=0.0)

    poisson = prediction.get("poisson") or {}
    over_prob = _safe_float(poisson.get("over_2_5"), default=0.0)
    under_prob = _safe_float(poisson.get("under_2_5"), default=max(0.0, 1.0 - over_prob))
    pick = f"大{line}" if over_prob >= under_prob else f"小{line}"
    confidence = max(over_prob, under_prob)
    return pick, confidence


def _format_total_goals_label(total_goals: int | None) -> str:
    if total_goals is None:
        return "-"
    return f"{int(total_goals)}球"


def _extract_total_goals_prediction(prediction: dict | None) -> tuple[str | None, int | None, float | None]:
    if not prediction:
        return None, None, None

    total_goals_value = prediction.get("total_goals_value")
    if total_goals_value is not None:
        try:
            parsed_total = int(total_goals_value)
        except Exception:
            parsed_total = None
        if parsed_total is not None:
            return (
                _format_total_goals_label(parsed_total),
                parsed_total,
                _safe_float(prediction.get("total_goals_confidence"), default=0.0),
            )

    direct_pick = prediction.get("total_goals_recommendation")
    if direct_pick:
        direct_text = str(direct_pick).strip()
        parsed_total = None
        if direct_text.endswith("球"):
            try:
                parsed_total = int(direct_text[:-1])
            except Exception:
                parsed_total = None
        return direct_text, parsed_total, _safe_float(prediction.get("total_goals_confidence"), default=0.0)

    poisson = prediction.get("poisson") or {}
    top_total_goals = poisson.get("top_total_goals") or []
    if top_total_goals:
        first = top_total_goals[0]
        try:
            parsed_total = int(first.get("goals"))
        except Exception:
            parsed_total = None
        return (
            _format_total_goals_label(parsed_total) if parsed_total is not None else None,
            parsed_total,
            _safe_float(first.get("probability"), default=0.0),
        )

    expected_goals = prediction.get("expected_goals")
    if expected_goals is not None:
        parsed_total = max(0, int(round(_safe_float(expected_goals), 0)))
        return _format_total_goals_label(parsed_total), parsed_total, None

    return None, None, None


def _extract_score_prediction(prediction: dict | None) -> tuple[str | None, float | None]:
    if not prediction:
        return None, None

    direct_pick = prediction.get("score_recommendation")
    if direct_pick:
        return str(direct_pick), _safe_float(prediction.get("score_confidence"), default=0.0)

    poisson = prediction.get("poisson") or {}
    top_scores = poisson.get("top_scores") or []
    if top_scores:
        first = top_scores[0]
        return str(first.get("score", "")) or None, _safe_float(first.get("probability"), default=0.0)

    return None, None


def _best_score_for_total_goals(
    score_distribution: list[dict] | None,
    total_goals: int | None,
    outcome_key: str | None = None,
) -> dict | None:
    if total_goals is None or not isinstance(score_distribution, list):
        return None
    primary: list[dict] = []
    fallback: list[dict] = []
    for item in score_distribution:
        if not isinstance(item, dict):
            continue
        score_text = str(item.get("score", "")).strip()
        if "-" not in score_text:
            continue
        try:
            home_goals, away_goals = [int(part) for part in score_text.split("-", 1)]
        except Exception:
            continue
        if home_goals + away_goals != int(total_goals):
            continue
        if outcome_key and _score_outcome_key(score_text) == outcome_key:
            primary.append(item)
        fallback.append(item)
    if primary:
        return max(primary, key=lambda entry: _safe_float(entry.get("probability"), default=0.0))
    if fallback:
        return max(fallback, key=lambda entry: _safe_float(entry.get("probability"), default=0.0))
    return None


def _extract_htft_prediction(prediction: dict | None) -> tuple[str | None, float | None]:
    if not prediction:
        return None, None

    direct_pick = prediction.get("htft_recommendation")
    if direct_pick:
        return str(direct_pick), _safe_float(prediction.get("htft_confidence"), default=0.0)

    poisson = prediction.get("poisson") or {}
    htft_top = poisson.get("htft_top") or []
    if htft_top:
        first = htft_top[0]
        label = str(first.get("label", "")).strip()
        return label or None, _safe_float(first.get("probability"), default=0.0)

    return None, None


def _format_handicap_line(handicap_line: float) -> str:
    line = _safe_float(handicap_line, default=0.0)
    if abs(line - round(line)) < 1e-9:
        text = str(int(round(line)))
    else:
        text = f"{line:.2f}".rstrip("0").rstrip(".")
    if not text.startswith("-"):
        text = f"+{text}"
    return text


def _handicap_outcome_key(home_goals: int, away_goals: int, handicap_line: float) -> str:
    adjusted_home = float(home_goals) + _safe_float(handicap_line, default=0.0)
    adjusted_away = float(away_goals)
    if adjusted_home > adjusted_away:
        return "home"
    if adjusted_home < adjusted_away:
        return "away"
    return "draw"


def _handicap_label_from_key(key: str) -> str:
    mapping = {"home": "让胜", "draw": "让平", "away": "让负"}
    return mapping.get(key, "-")


def _format_handicap_display(handicap_line: float, key: str) -> str:
    return f"{_format_handicap_line(handicap_line)} {_handicap_label_from_key(key)}"


def _score_outcome_key(score_text: str) -> str | None:
    if "-" not in score_text:
        return None
    try:
        home_goals, away_goals = [int(part) for part in score_text.split("-", 1)]
    except Exception:
        return None
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def _htft_label_from_key(key: str) -> str:
    mapping = {"home": "胜", "draw": "平", "away": "负"}
    left, right = key.split("_", 1)
    return f"{mapping.get(left, '-')} / {mapping.get(right, '-')}"


def _extract_handicap_prediction(prediction: dict | None) -> tuple[str | None, str | None, float | None]:
    if not prediction:
        return None, None, None

    direct_display = prediction.get("handicap_display")
    direct_pick = prediction.get("handicap_recommendation")
    if direct_pick:
        return (
            str(direct_display or direct_pick),
            str(direct_pick),
            _safe_float(prediction.get("handicap_confidence"), default=0.0),
        )

    return None, None, None


def _build_parlay_leg(
    match: AppMatch,
    play_type: str,
    pick: str,
    confidence: float,
    *,
    prediction: dict | None = None,
) -> dict:
    indices = prediction.get("indices", {}) if isinstance(prediction, dict) else {}
    upset_index = _safe_float(indices.get("upset_index"), default=0.5)
    stability_index = _safe_float(indices.get("stability_index"), default=0.5)
    confidence_index = _safe_float(
        indices.get("confidence_index"),
        default=_safe_float((prediction or {}).get("confidence"), default=0.5),
    )
    return {
        "match_id": match.match_id,
        "match_date": match.match_date,
        "match_time": match.match_time,
        "league": match.league,
        "competition_group": match.competition_group,
        "group_round": match.group_round,
        "home_points": match.home_points,
        "away_points": match.away_points,
        "home_goal_diff": match.home_goal_diff,
        "away_goal_diff": match.away_goal_diff,
        "home_group_rank": match.home_group_rank,
        "away_group_rank": match.away_group_rank,
        "home_team": match.home_team,
        "away_team": match.away_team,
        "play_type": play_type,
        "pick": pick,
        "confidence": round(_safe_float(confidence, default=0.0), 4),
        "upset_index": round(_clamp(upset_index), 4),
        "stability_index": round(_clamp(stability_index), 4),
        "confidence_index": round(_clamp(confidence_index), 4),
    }


def _calibrate_parlay_leg_confidence(play_type: str, confidence: float) -> float:
    play = str(play_type or "").strip().lower()
    raw = _clamp(_safe_float(confidence, default=0.0), 0.01, 0.99)
    shrink_map = {
        "1x2": 0.92,
        "handicap": 0.82,
        "total_goals": 0.74,
        "htft": 0.80,
        "score": 0.68,
    }
    floor_map = {
        "1x2": 0.05,
        "handicap": 0.05,
        "total_goals": 0.05,
        "htft": 0.03,
        "score": 0.02,
    }
    cap_map = {
        "1x2": 0.90,
        "handicap": 0.88,
        "total_goals": 0.72,
        "htft": 0.80,
        "score": 0.60,
    }
    shrink = _safe_float(shrink_map.get(play), default=0.86)
    calibrated = 0.5 + (raw - 0.5) * shrink
    floor = _safe_float(floor_map.get(play), default=0.05)
    cap = _safe_float(cap_map.get(play), default=0.88)
    return _clamp(calibrated, floor, cap)


def _parlay_correlation_discount(leg_a: dict, leg_b: dict) -> float:
    play_a = str(leg_a.get("play_type") or "").strip().lower()
    play_b = str(leg_b.get("play_type") or "").strip().lower()
    discount = 1.0
    if play_a == play_b:
        same_play_discount = {
            "1x2": 0.90,
            "handicap": 0.86,
            "total_goals": 0.88,
            "htft": 0.80,
            "score": 0.72,
        }
        discount *= _safe_float(same_play_discount.get(play_a), default=0.90)
    league_a = normalize_text(leg_a.get("league", ""))
    league_b = normalize_text(leg_b.get("league", ""))
    if league_a and league_a == league_b:
        discount *= 0.95
    date_a = normalize_text(leg_a.get("match_date", ""))
    date_b = normalize_text(leg_b.get("match_date", ""))
    time_a = normalize_text(leg_a.get("match_time", ""))
    time_b = normalize_text(leg_b.get("match_time", ""))
    if date_a and date_a == date_b and time_a and time_a == time_b:
        discount *= 0.97
    return _clamp(discount, 0.55, 1.0)


def _parlay_pair_quality_factor(leg_a: dict, leg_b: dict) -> float:
    upset_avg = (
        _safe_float(leg_a.get("upset_index"), default=0.5)
        + _safe_float(leg_b.get("upset_index"), default=0.5)
    ) / 2.0
    stability_avg = (
        _safe_float(leg_a.get("stability_index"), default=0.5)
        + _safe_float(leg_b.get("stability_index"), default=0.5)
    ) / 2.0
    confidence_index_avg = (
        _safe_float(leg_a.get("confidence_index"), default=0.5)
        + _safe_float(leg_b.get("confidence_index"), default=0.5)
    ) / 2.0
    factor = 0.88
    factor += (stability_avg - 0.5) * 0.22
    factor += (confidence_index_avg - 0.5) * 0.12
    factor -= (upset_avg - 0.5) * 0.26
    return _clamp(factor, 0.72, 1.18)


def _recent_play_reliability_factor(play_type: str, settlements: list[dict]) -> dict[str, float | int]:
    normalized_play = str(play_type or "").strip().lower()
    score_keys = {
        "1x2": "is_correct",
        "handicap": "handicap_is_correct",
        "total_goals": "total_goals_is_correct",
        "score": "score_is_correct",
    }
    score_key = score_keys.get(normalized_play)
    if not score_key:
        return {"factor": 1.0, "sample_count": 0, "posterior_hit_rate": 0.5}

    rows: list[bool] = []
    for item in settlements:
        if not isinstance(item, dict):
            continue
        value = item.get(score_key)
        if isinstance(value, bool):
            rows.append(value)
    sample_count = len(rows)
    if sample_count <= 0:
        return {"factor": 1.0, "sample_count": 0, "posterior_hit_rate": 0.5}

    hits = sum(1 for item in rows if item)
    prior_mean = 0.50
    prior_strength = 18.0
    posterior = (hits + prior_mean * prior_strength) / (sample_count + prior_strength)
    factor = _clamp(0.84 + (posterior - 0.5) * 0.90, 0.74, 1.12)
    return {
        "factor": round(factor, 4),
        "sample_count": sample_count,
        "posterior_hit_rate": round(posterior, 4),
    }


def _settlement_mtime() -> float:
    try:
        return float(STATE_STORE.settlements_file.stat().st_mtime)
    except Exception:
        return 0.0


def _confidence_calibration_profile() -> dict[str, Any]:
    mtime = _settlement_mtime()
    if _CONFIDENCE_CALIBRATION_CACHE.get("settlement_mtime") == mtime:
        cached_profile = _CONFIDENCE_CALIBRATION_CACHE.get("profile")
        if isinstance(cached_profile, dict):
            return cached_profile

    bins = [
        {"name": "b0", "low": 0.00, "high": 0.50, "default_scale": 1.00},
        {"name": "b1", "low": 0.50, "high": 0.56, "default_scale": 0.88},
        {"name": "b2", "low": 0.56, "high": 0.62, "default_scale": 0.74},
        {"name": "b3", "low": 0.62, "high": 0.68, "default_scale": 0.70},
        {"name": "b4", "low": 0.68, "high": 0.74, "default_scale": 0.66},
        {"name": "b5", "low": 0.74, "high": 1.01, "default_scale": 0.70},
    ]
    settlements = STATE_STORE.load_settlements()
    recent_rows = settlements[-400:] if len(settlements) > 400 else list(settlements)
    resolved: list[dict[str, float | int | str]] = []
    for item in bins:
        low = _safe_float(item.get("low"), 0.0)
        high = _safe_float(item.get("high"), 1.01)
        default_scale = _safe_float(item.get("default_scale"), 0.80)
        values: list[tuple[float, bool]] = []
        for row in recent_rows:
            if not isinstance(row, dict):
                continue
            hit = row.get("is_correct")
            conf = _safe_float(row.get("prediction_confidence"), default=0.0)
            if not isinstance(hit, bool):
                continue
            if conf < low or conf >= high:
                continue
            values.append((conf, hit))
        n = len(values)
        if n <= 0:
            scale = default_scale
            avg_conf = 0.0
            hit_rate = 0.0
        else:
            avg_conf = sum(value for value, _ in values) / n
            hit_rate = sum(1 for _, hit in values if hit) / n
            ratio = (hit_rate / avg_conf) if avg_conf > 0 else default_scale
            if n >= 20:
                scale = _clamp(ratio, 0.55, 1.0)
            elif n >= 8:
                scale = _clamp(default_scale * 0.7 + ratio * 0.3, 0.55, 1.0)
            else:
                scale = _clamp(default_scale, 0.55, 1.0)
        resolved.append(
            {
                "name": str(item.get("name") or ""),
                "low": round(low, 4),
                "high": round(high, 4),
                "sample_count": n,
                "avg_confidence": round(avg_conf, 4),
                "hit_rate": round(hit_rate, 4),
                "scale": round(scale, 4),
            }
        )

    profile = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sample_count": len(recent_rows),
        "bins": resolved,
    }
    _CONFIDENCE_CALIBRATION_CACHE["settlement_mtime"] = mtime
    _CONFIDENCE_CALIBRATION_CACHE["profile"] = profile
    return profile


def _calibrate_recommendation_confidence(raw_confidence: float) -> tuple[float, dict[str, Any]]:
    raw = _clamp(_safe_float(raw_confidence, 0.0), 0.01, 0.99)
    profile = _confidence_calibration_profile()
    bins = profile.get("bins", []) if isinstance(profile, dict) else []
    selected_bin: dict[str, Any] | None = None
    for item in bins:
        if not isinstance(item, dict):
            continue
        low = _safe_float(item.get("low"), 0.0)
        high = _safe_float(item.get("high"), 1.01)
        if low <= raw < high:
            selected_bin = item
            break
    if not selected_bin:
        selected_bin = {"name": "fallback", "scale": 0.80, "sample_count": 0}
    scale = _clamp(_safe_float(selected_bin.get("scale"), 0.80), 0.55, 1.0)
    calibrated = _clamp(raw * scale, 0.03, 0.92)
    meta = {
        "raw_confidence": round(raw, 4),
        "calibrated_confidence": round(calibrated, 4),
        "scale": round(scale, 4),
        "bin": str(selected_bin.get("name", "-")),
        "bin_sample_count": int(selected_bin.get("sample_count", 0) or 0),
    }
    return calibrated, meta


def _current_play_policy() -> dict[str, dict]:
    return {
        key: dict(value) for key, value in DEFAULT_PLAY_POLICY.items() if isinstance(value, dict)
    }


def _parlay_leg_candidates(matches: list[AppMatch], predictions: dict[str, dict]) -> list[dict]:
    candidates: list[dict] = []
    min_conf_map = {
        "1x2": 0.58,
        "handicap": 0.60,
        "total_goals": 0.30,
        "htft": 0.34,
        "score": 0.18,
    }
    for match in matches:
        prediction = predictions.get(match.match_id)
        if not isinstance(prediction, dict):
            continue
        eligible_plays = prediction.get("parlay_eligible_plays", [])
        if not isinstance(eligible_plays, list):
            continue
        for item in eligible_plays:
            if not isinstance(item, dict):
                continue
            leg = _build_parlay_leg(
                match,
                str(item.get("play_type") or "-"),
                str(item.get("pick") or "-"),
                _safe_float(item.get("confidence"), default=0.0),
                prediction=prediction,
            )
            if leg["pick"] == "-":
                continue
            play_key = str(leg.get("play_type", "")).strip().lower()
            min_conf = _safe_float(min_conf_map.get(play_key), default=0.58)
            if _safe_float(leg.get("confidence"), default=0.0) < min_conf:
                continue
            candidates.append(leg)
    return candidates


def _select_diversified_parlay_pairs(
    ranked_pairs: list[dict],
    *,
    limit: int,
    min_expected_hit: float,
    max_match_exposure: int = 2,
    max_leg_upset: float = 0.64,
    allow_fallback_fill: bool = True,
) -> list[dict]:
    target = max(0, int(limit))
    if target <= 0:
        return []
    picked_ids: set[str] = set()
    match_exposure: dict[str, int] = defaultdict(int)
    selected: list[dict] = []

    for item in ranked_pairs:
        if len(selected) >= target:
            break
        ticket_id = str(item.get("ticket_id", ""))
        if not ticket_id or ticket_id in picked_ids:
            continue
        expected_hit = _safe_float(item.get("expected_hit"), default=0.0)
        if expected_hit < min_expected_hit and len(selected) >= min(2, target):
            continue
        if _safe_float(item.get("max_leg_upset"), default=0.5) > max_leg_upset and len(selected) >= min(3, target):
            continue
        if _safe_float(item.get("correlation_discount"), default=1.0) < 0.82 and len(selected) >= min(3, target):
            continue
        legs = item.get("legs", [])
        if not isinstance(legs, list) or len(legs) != 2:
            continue
        leg_match_ids = [str(legs[0].get("match_id", "")), str(legs[1].get("match_id", ""))]
        if any(not value for value in leg_match_ids):
            continue
        if any(match_exposure[mid] >= max_match_exposure for mid in leg_match_ids):
            continue
        selected.append(item)
        picked_ids.add(ticket_id)
        for mid in leg_match_ids:
            match_exposure[mid] += 1

    if len(selected) >= target or not allow_fallback_fill:
        return selected

    for item in ranked_pairs:
        if len(selected) >= target:
            break
        ticket_id = str(item.get("ticket_id", ""))
        if not ticket_id or ticket_id in picked_ids:
            continue
        selected.append(item)
        picked_ids.add(ticket_id)
    return selected


def _parlay_ticket_id(leg_a: dict, leg_b: dict) -> str:
    left = f"{leg_a['match_id']}|{leg_a['play_type']}|{leg_a['pick']}"
    right = f"{leg_b['match_id']}|{leg_b['play_type']}|{leg_b['pick']}"
    ordered = sorted([left, right])
    return f"2串1|{ordered[0]}||{ordered[1]}"


def _parse_datetime_text(value: object) -> datetime | None:
    text = normalize_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue
    return None


def _is_pending_ticket_fresh(ticket: dict, *, now: datetime) -> bool:
    if str(ticket.get("status", "")) != "pending":
        return False
    created_at = _parse_datetime_text(ticket.get("created_at"))
    if created_at is not None and (now - created_at).days >= 2:
        return False
    legs = ticket.get("legs", [])
    if not isinstance(legs, list) or not legs:
        return False
    leg_datetimes: list[datetime] = []
    for leg in legs:
        if not isinstance(leg, dict):
            continue
        match_date = normalize_text(leg.get("match_date"))
        match_time = normalize_text(leg.get("match_time"))
        leg_dt = _parse_datetime_text(f"{match_date} {match_time}".strip())
        if leg_dt is not None:
            leg_datetimes.append(leg_dt)
    if leg_datetimes and max(leg_datetimes) < now.replace(hour=0, minute=0, second=0, microsecond=0):
        return False
    return True


def generate_mix_parlay_recommendations(
    matches: list[AppMatch],
    predictions: dict[str, dict],
    limit: int = 5,
) -> list[dict]:
    candidates = _parlay_leg_candidates(matches, predictions)
    if len(candidates) < 2:
        return []
    recent_settlements = STATE_STORE.load_settlements()
    recent_window = recent_settlements[-240:] if len(recent_settlements) > 240 else list(recent_settlements)
    play_reliability_cache: dict[str, dict[str, float | int]] = {}

    ranked_pairs: list[dict] = []
    for index, leg_a in enumerate(candidates):
        for leg_b in candidates[index + 1 :]:
            if leg_a["match_id"] == leg_b["match_id"]:
                continue
            leg_a_calibrated = _calibrate_parlay_leg_confidence(
                str(leg_a.get("play_type") or ""),
                _safe_float(leg_a.get("confidence"), 0.0),
            )
            leg_b_calibrated = _calibrate_parlay_leg_confidence(
                str(leg_b.get("play_type") or ""),
                _safe_float(leg_b.get("confidence"), 0.0),
            )
            raw_combined_probability = _safe_float(leg_a["confidence"], 0.0) * _safe_float(leg_b["confidence"], 0.0)
            correlation_discount = _parlay_correlation_discount(leg_a, leg_b)
            combined_probability = leg_a_calibrated * leg_b_calibrated * correlation_discount
            pair_quality_factor = _parlay_pair_quality_factor(leg_a, leg_b)
            play_a = str(leg_a.get("play_type") or "").strip().lower()
            play_b = str(leg_b.get("play_type") or "").strip().lower()
            if play_a not in play_reliability_cache:
                play_reliability_cache[play_a] = _recent_play_reliability_factor(play_a, recent_window)
            if play_b not in play_reliability_cache:
                play_reliability_cache[play_b] = _recent_play_reliability_factor(play_b, recent_window)
            rel_a = play_reliability_cache[play_a]
            rel_b = play_reliability_cache[play_b]
            play_reliability_factor = (
                _safe_float(rel_a.get("factor"), default=1.0)
                + _safe_float(rel_b.get("factor"), default=1.0)
            ) / 2.0
            mixed = leg_a["play_type"] != leg_b["play_type"]
            rank_score = combined_probability * (1.05 if mixed else 1.0) * pair_quality_factor * play_reliability_factor
            ranked_pairs.append(
                {
                    "ticket_id": _parlay_ticket_id(leg_a, leg_b),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "pending",
                    "kind": "parlay_2",
                    "mixed": mixed,
                    "legs": [
                        {**leg_a, "calibrated_confidence": round(leg_a_calibrated, 4)},
                        {**leg_b, "calibrated_confidence": round(leg_b_calibrated, 4)},
                    ],
                    "expected_hit": round(combined_probability, 4),
                    "expected_hit_raw": round(raw_combined_probability, 4),
                    "correlation_discount": round(correlation_discount, 4),
                    "pair_quality_factor": round(pair_quality_factor, 4),
                    "play_reliability_factor": round(play_reliability_factor, 4),
                    "play_reliability_sample_count": int(
                        min(
                            int(rel_a.get("sample_count", 0) or 0),
                            int(rel_b.get("sample_count", 0) or 0),
                        )
                    ),
                    "max_leg_upset": round(
                        max(
                            _safe_float(leg_a.get("upset_index"), default=0.5),
                            _safe_float(leg_b.get("upset_index"), default=0.5),
                        ),
                        4,
                    ),
                    "rank_score": round(rank_score, 4),
                    "display": (
                        f"{leg_a['home_team']} vs {leg_a['away_team']} {leg_a['pick']} + "
                        f"{leg_b['home_team']} vs {leg_b['away_team']} {leg_b['pick']}"
                    ),
                }
            )

    ranked_pairs.sort(
        key=lambda item: (
            0 if item["mixed"] else 1,
            -item["rank_score"],
            -item["expected_hit"],
            item["ticket_id"],
        )
    )
    top_expected_hit = _safe_float(ranked_pairs[0].get("expected_hit"), default=0.0) if ranked_pairs else 0.0
    min_expected_hit = _clamp(max(0.08, top_expected_hit * 0.55), 0.08, 0.26)
    selected = _select_diversified_parlay_pairs(
        ranked_pairs,
        limit=max(0, limit),
        min_expected_hit=min_expected_hit,
        max_match_exposure=2,
        max_leg_upset=0.64,
    )
    if not selected:
        return []

    existing = STATE_STORE.load_parlay_tickets()
    now = datetime.now()
    settled_index: dict[str, dict] = {}
    pending_index: dict[str, dict] = {}
    for item in existing:
        if not isinstance(item, dict):
            continue
        ticket_id = str(item.get("ticket_id", ""))
        if not ticket_id:
            continue
        status = str(item.get("status", ""))
        if status in {"won", "lost"}:
            settled_index[ticket_id] = item
            continue
        if _is_pending_ticket_fresh(item, now=now):
            pending_index[ticket_id] = item

    for ticket in selected:
        pending_index[ticket["ticket_id"]] = ticket

    pending_pool = list(pending_index.values())
    pending_pool.sort(
        key=lambda item: (
            0 if bool(item.get("mixed")) else 1,
            -_safe_float(item.get("rank_score"), 0.0),
            -_safe_float(item.get("expected_hit"), 0.0),
            str(item.get("ticket_id", "")),
        )
    )
    pending_final = _select_diversified_parlay_pairs(
        pending_pool,
        limit=60,
        min_expected_hit=0.0,
        max_match_exposure=2,
        max_leg_upset=0.70,
        allow_fallback_fill=False,
    )
    merged = sorted(
        [*settled_index.values(), *pending_final],
        key=lambda item: (str(item.get("created_at", "")), str(item.get("ticket_id", ""))),
    )
    STATE_STORE.save_parlay_tickets(merged)
    return selected


def get_active_parlay_recommendations(limit: int = 10) -> list[dict]:
    items = STATE_STORE.load_parlay_tickets()
    now = datetime.now()
    settled_index: dict[str, dict] = {}
    pending_index: dict[str, dict] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        ticket_id = str(item.get("ticket_id", ""))
        if not ticket_id:
            continue
        status = str(item.get("status", ""))
        if status in {"won", "lost"}:
            settled_index[ticket_id] = item
            continue
        if _is_pending_ticket_fresh(item, now=now):
            pending_index[ticket_id] = item

    pending_pool = list(pending_index.values())
    pending_pool.sort(
        key=lambda item: (
            0 if bool(item.get("mixed")) else 1,
            -_safe_float(item.get("rank_score"), 0.0),
            -_safe_float(item.get("expected_hit"), 0.0),
            str(item.get("ticket_id", "")),
        )
    )
    pending_final = _select_diversified_parlay_pairs(
        pending_pool,
        limit=max(60, max(1, int(limit))),
        min_expected_hit=0.0,
        max_match_exposure=2,
        max_leg_upset=0.70,
        allow_fallback_fill=False,
    )

    normalized = sorted(
        [*settled_index.values(), *pending_final],
        key=lambda item: (str(item.get("created_at", "")), str(item.get("ticket_id", ""))),
    )
    normalized_ids = {str(item.get("ticket_id", "")) for item in normalized}
    original_ids = {str(item.get("ticket_id", "")) for item in items if isinstance(item, dict)}
    if normalized_ids != original_ids or len(normalized) != len(items):
        STATE_STORE.save_parlay_tickets(normalized)

    pending_final.sort(
        key=lambda item: (
            0 if bool(item.get("mixed")) else 1,
            -_safe_float(item.get("rank_score"), 0.0),
            -_safe_float(item.get("expected_hit"), 0.0),
            str(item.get("ticket_id", "")),
        )
    )
    return pending_final[: max(0, limit)]


def _settlement_hit_by_play_type(settlement: dict, play_type: str) -> bool | None:
    mapping = {
        "1x2": settlement.get("is_correct"),
        "handicap": settlement.get("handicap_is_correct"),
        "total_goals": settlement.get("total_goals_is_correct"),
        "score": settlement.get("score_is_correct"),
    }
    value = mapping.get(play_type)
    return value if isinstance(value, bool) else None


def auto_settle_pending_parlays() -> dict:
    tickets = STATE_STORE.load_parlay_tickets()
    if not tickets:
        return {"new_settled": 0, "won": 0, "lost": 0, "items": []}

    settlement_map: dict[str, dict] = {}
    for item in STATE_STORE.load_settlements():
        match_id = str(item.get("match_id", ""))
        if match_id:
            settlement_map[match_id] = item

    changed = False
    summary = {"new_settled": 0, "won": 0, "lost": 0, "items": []}
    for ticket in tickets:
        if not isinstance(ticket, dict) or ticket.get("status") != "pending":
            continue

        legs = ticket.get("legs", [])
        if not isinstance(legs, list) or not legs:
            continue

        any_loss = False
        all_resolved = True
        leg_results: list[dict] = []
        for leg in legs:
            if not isinstance(leg, dict):
                all_resolved = False
                continue
            settlement = settlement_map.get(str(leg.get("match_id", "")))
            hit = _settlement_hit_by_play_type(settlement or {}, str(leg.get("play_type", ""))) if settlement else None
            leg_results.append(
                {
                    "match_id": leg.get("match_id"),
                    "play_type": leg.get("play_type"),
                    "pick": leg.get("pick"),
                    "resolved": hit is not None,
                    "is_hit": hit,
                }
            )
            if hit is False:
                any_loss = True
            if hit is None:
                all_resolved = False

        if not any_loss and not all_resolved:
            continue

        ticket["status"] = "won" if all_resolved and not any_loss else "lost"
        ticket["settled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ticket["is_hit"] = ticket["status"] == "won"
        ticket["leg_results"] = leg_results
        summary["new_settled"] += 1
        summary["won"] += 1 if ticket["status"] == "won" else 0
        summary["lost"] += 1 if ticket["status"] == "lost" else 0
        summary["items"].append(ticket)
        changed = True

    if changed:
        STATE_STORE.save_parlay_tickets(tickets)
    return summary


def get_recent_parlay_settlements(limit: int = 20) -> list[dict]:
    items = STATE_STORE.load_parlay_tickets()
    settled = [item for item in items if isinstance(item, dict) and item.get("status") in {"won", "lost"}]
    settled.sort(key=lambda item: str(item.get("settled_at", item.get("created_at", ""))))
    if limit <= 0:
        return settled
    return settled[-limit:]


def _gate_metrics_from_records(records: list[dict], breaker_threshold: int = 3) -> dict:
    normalized: list[dict] = []
    for item in records:
        is_hit = item.get("is_hit")
        if not isinstance(is_hit, bool):
            continue
        normalized.append(
            {
                "timestamp": str(item.get("timestamp", "")),
                "is_hit": is_hit,
                "expected_hit": _safe_float(item.get("expected_hit"), default=0.0),
            }
        )

    if not normalized:
        return {
            "sample_count": 0,
            "hit_rate": 0.0,
            "expected_hit_rate": 0.0,
            "ev_bias": 0.0,
            "losing_streak": 0,
            "breaker_on": False,
        }

    ordered = sorted(normalized, key=lambda item: item["timestamp"])
    sample_count = len(ordered)
    hit_rate = sum(1 for item in ordered if item["is_hit"]) / sample_count
    expected_values = [item["expected_hit"] for item in ordered if item["expected_hit"] > 0]
    expected_hit_rate = (sum(expected_values) / len(expected_values)) if expected_values else 0.0
    losing_streak = 0
    for item in reversed(ordered):
        if item["is_hit"]:
            break
        losing_streak += 1
    return {
        "sample_count": sample_count,
        "hit_rate": round(hit_rate, 4),
        "expected_hit_rate": round(expected_hit_rate, 4),
        "ev_bias": round((hit_rate - expected_hit_rate) if expected_values else 0.0, 4),
        "losing_streak": losing_streak,
        "breaker_on": losing_streak >= breaker_threshold,
    }


def get_gate_metrics(window: int = 20) -> dict:
    single_items = [
        {
            "timestamp": item.get("timestamp"),
            "is_hit": item.get("is_correct"),
            "expected_hit": item.get("prediction_confidence"),
        }
        for item in get_recent_settlements(limit=window)
    ]
    parlay_items = [
        {
            "timestamp": item.get("settled_at") or item.get("created_at"),
            "is_hit": item.get("is_hit"),
            "expected_hit": item.get("expected_hit"),
        }
        for item in get_recent_parlay_settlements(limit=window)
    ]
    overall_items = (single_items + parlay_items)[-max(0, window) :]
    singles = _gate_metrics_from_records(single_items)
    parlays = _gate_metrics_from_records(parlay_items)
    overall = _gate_metrics_from_records(overall_items)
    return {
        "singles": singles,
        "parlays": parlays,
        "overall": overall,
    }


def get_parlay_selector_metrics(limit: int = 120) -> dict:
    tickets = get_active_parlay_recommendations(limit=max(1, int(limit)))
    if not tickets:
        return {
            "ticket_count": 0,
            "unique_match_count": 0,
            "max_match_exposure": 0,
            "avg_match_exposure": 0.0,
            "mixed_ratio": 0.0,
            "avg_expected_hit": 0.0,
            "max_expected_hit": 0.0,
            "high_expected_hit_count": 0,
            "low_discount_count": 0,
            "high_upset_leg_count": 0,
            "avg_pair_quality_factor": 0.0,
            "avg_play_reliability_factor": 0.0,
        }

    match_exposure: dict[str, int] = defaultdict(int)
    expected_hits: list[float] = []
    pair_quality_values: list[float] = []
    reliability_values: list[float] = []
    mixed_count = 0
    high_expected_hit_count = 0
    low_discount_count = 0
    high_upset_leg_count = 0

    for ticket in tickets:
        if not isinstance(ticket, dict):
            continue
        legs = ticket.get("legs", [])
        if isinstance(legs, list):
            for leg in legs:
                if not isinstance(leg, dict):
                    continue
                match_id = str(leg.get("match_id", ""))
                if match_id:
                    match_exposure[match_id] += 1
        if bool(ticket.get("mixed")):
            mixed_count += 1
        expected_hit = _safe_float(ticket.get("expected_hit"), default=0.0)
        expected_hits.append(expected_hit)
        if expected_hit >= 0.40:
            high_expected_hit_count += 1
        if _safe_float(ticket.get("correlation_discount"), default=1.0) < 0.82:
            low_discount_count += 1
        if _safe_float(ticket.get("max_leg_upset"), default=0.0) > 0.64:
            high_upset_leg_count += 1
        pair_quality_values.append(_safe_float(ticket.get("pair_quality_factor"), default=1.0))
        reliability_values.append(_safe_float(ticket.get("play_reliability_factor"), default=1.0))

    ticket_count = len(tickets)
    exposure_values = list(match_exposure.values())
    max_match_exposure = max(exposure_values) if exposure_values else 0
    avg_match_exposure = (sum(exposure_values) / len(exposure_values)) if exposure_values else 0.0
    avg_expected_hit = (sum(expected_hits) / len(expected_hits)) if expected_hits else 0.0
    max_expected_hit = max(expected_hits) if expected_hits else 0.0
    avg_pair_quality_factor = (sum(pair_quality_values) / len(pair_quality_values)) if pair_quality_values else 0.0
    avg_play_reliability_factor = (sum(reliability_values) / len(reliability_values)) if reliability_values else 0.0

    return {
        "ticket_count": ticket_count,
        "unique_match_count": len(match_exposure),
        "max_match_exposure": max_match_exposure,
        "avg_match_exposure": round(avg_match_exposure, 4),
        "mixed_ratio": round((mixed_count / ticket_count) if ticket_count > 0 else 0.0, 4),
        "avg_expected_hit": round(avg_expected_hit, 4),
        "max_expected_hit": round(max_expected_hit, 4),
        "high_expected_hit_count": high_expected_hit_count,
        "low_discount_count": low_discount_count,
        "high_upset_leg_count": high_upset_leg_count,
        "avg_pair_quality_factor": round(avg_pair_quality_factor, 4),
        "avg_play_reliability_factor": round(avg_play_reliability_factor, 4),
    }


def _safe_model_dir() -> None:
    ENSEMBLE_WEIGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    return ENSEMBLE_ENGINE._normalize_weights(weights)


def _ensemble_weights_mtime() -> float | None:
    try:
        return ENSEMBLE_WEIGHTS_FILE.stat().st_mtime
    except Exception:
        return None


def _load_ensemble_weight_report() -> dict:
    mtime = _ensemble_weights_mtime()
    if mtime is not None and _ENSEMBLE_WEIGHT_CACHE.get("mtime") == mtime:
        cached_report = _ENSEMBLE_WEIGHT_CACHE.get("report")
        if isinstance(cached_report, dict):
            return cached_report
    if not ENSEMBLE_WEIGHTS_FILE.exists():
        report = {
            "updated_at": None,
            "mode": "default",
            "weights": dict(DEFAULT_ENSEMBLE_WEIGHTS),
            "default_weights": dict(DEFAULT_ENSEMBLE_WEIGHTS),
            "metrics": {},
            "validation": {},
        }
        _ENSEMBLE_WEIGHT_CACHE["mtime"] = None
        _ENSEMBLE_WEIGHT_CACHE["weights"] = dict(DEFAULT_ENSEMBLE_WEIGHTS)
        _ENSEMBLE_WEIGHT_CACHE["report"] = report
        return report
    try:
        report = json.loads(ENSEMBLE_WEIGHTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        report = {}
    if not isinstance(report, dict):
        report = {}
    weights = report.get("weights")
    if not isinstance(weights, dict):
        weights = dict(DEFAULT_ENSEMBLE_WEIGHTS)
        report["weights"] = weights
    report.setdefault("default_weights", dict(DEFAULT_ENSEMBLE_WEIGHTS))
    report.setdefault("mode", "calibrated")
    report.setdefault("metrics", {})
    report.setdefault("validation", {})
    report.setdefault("league_weights", {})
    _ENSEMBLE_WEIGHT_CACHE["mtime"] = mtime
    _ENSEMBLE_WEIGHT_CACHE["weights"] = _normalize_weights(
        {key: float(value) for key, value in weights.items() if key in DEFAULT_ENSEMBLE_WEIGHTS}
    )
    _ENSEMBLE_WEIGHT_CACHE["report"] = report
    return report


def get_ensemble_weight_status() -> dict:
    report = _load_ensemble_weight_report()
    weights = report.get("weights")
    normalized = _normalize_weights(
        {key: float(value) for key, value in (weights or {}).items() if key in DEFAULT_ENSEMBLE_WEIGHTS}
    )
    return {
        "updated_at": report.get("updated_at"),
        "mode": report.get("mode", "default"),
        "weights": normalized,
        "default_weights": dict(DEFAULT_ENSEMBLE_WEIGHTS),
        "metrics": report.get("metrics", {}),
        "validation": report.get("validation", {}),
        "league_weights": report.get("league_weights", {}),
    }


def _current_ensemble_weights() -> dict[str, float]:
    status = get_ensemble_weight_status()
    weights = status.get("weights", {})
    if not isinstance(weights, dict) or not weights:
        return dict(DEFAULT_ENSEMBLE_WEIGHTS)
    return _normalize_weights({key: float(weights.get(key, 0.0)) for key in DEFAULT_ENSEMBLE_WEIGHTS})


def _ensemble_weights_for_league(league: str) -> dict[str, float]:
    status = get_ensemble_weight_status()
    league_weights = status.get("league_weights", {})
    league_key = normalize_text(league)
    if isinstance(league_weights, dict):
        league_payload = league_weights.get(league_key)
        if isinstance(league_payload, dict):
            weights = league_payload.get("weights", {})
            if isinstance(weights, dict) and weights:
                return _normalize_weights({key: float(weights.get(key, 0.0)) for key in DEFAULT_ENSEMBLE_WEIGHTS})
    return _current_ensemble_weights()


def _save_ensemble_weight_report(report: dict) -> None:
    if not isinstance(report, dict):
        return
    _safe_model_dir()
    ENSEMBLE_WEIGHTS_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _ENSEMBLE_WEIGHT_CACHE["mtime"] = _ensemble_weights_mtime()
    _ENSEMBLE_WEIGHT_CACHE["report"] = report
    _ENSEMBLE_WEIGHT_CACHE["weights"] = dict(report.get("weights", DEFAULT_ENSEMBLE_WEIGHTS))


def _sample_sort_key(item: dict) -> tuple[str, str, str]:
    meta = item.get("meta") if isinstance(item, dict) else {}
    if not isinstance(meta, dict):
        meta = {}
    return (
        normalize_text(meta.get("match_date", "")),
        normalize_text(meta.get("match_time", "00:00")),
        normalize_text(item.get("match_id", "")),
    )


def _sample_to_context(item: dict) -> EnsembleContext | None:
    if not isinstance(item, dict):
        return None
    features = item.get("features")
    meta = item.get("meta")
    if not isinstance(features, dict) or not isinstance(meta, dict):
        return None
    market_home = _safe_float(features.get("market_home"), default=0.0)
    market_draw = _safe_float(features.get("market_draw"), default=0.0)
    market_away = _safe_float(features.get("market_away"), default=0.0)
    home_rating = _safe_float(features.get("home_rating"), default=ELO_ENGINE.base_rating)
    away_rating = _safe_float(features.get("away_rating"), default=ELO_ENGINE.base_rating)
    league_strength = _safe_float(features.get("league_strength"), default=0.92)
    metadata = {
        "match_id": normalize_text(item.get("match_id", "")),
        "match_date": normalize_text(meta.get("match_date", "")),
        "match_time": normalize_text(meta.get("match_time", "")),
        "league": normalize_text(meta.get("league", "")),
        "home_team": normalize_text(meta.get("home_team", "")),
        "away_team": normalize_text(meta.get("away_team", "")),
        "odds_home": _safe_float(features.get("odds_home"), default=0.0),
        "odds_draw": _safe_float(features.get("odds_draw"), default=0.0),
        "odds_away": _safe_float(features.get("odds_away"), default=0.0),
        "opening_odds_home": _safe_float(meta.get("opening_odds_home"), default=_safe_float(features.get("opening_odds_home"), default=0.0)),
        "opening_odds_draw": _safe_float(meta.get("opening_odds_draw"), default=_safe_float(features.get("opening_odds_draw"), default=0.0)),
        "opening_odds_away": _safe_float(meta.get("opening_odds_away"), default=_safe_float(features.get("opening_odds_away"), default=0.0)),
        "return_rate": _safe_float(meta.get("return_rate"), default=_safe_float(features.get("return_rate"), default=0.0)),
        "kelly_home": _safe_float(meta.get("kelly_home"), default=_safe_float(features.get("kelly_home"), default=0.0)),
        "kelly_draw": _safe_float(meta.get("kelly_draw"), default=_safe_float(features.get("kelly_draw"), default=0.0)),
        "kelly_away": _safe_float(meta.get("kelly_away"), default=_safe_float(features.get("kelly_away"), default=0.0)),
    }
    for name in XGBOOST_MODEL.FEATURE_ORDER:
        if name in metadata:
            continue
        metadata[name] = _safe_float(features.get(name), default=0.0)
    return EnsembleContext(
        market_probs=(market_home, market_draw, market_away),
        home_rating=home_rating,
        away_rating=away_rating,
        market_draw_prob=market_draw,
        league_strength=league_strength,
        metadata=metadata,
    )


def _model_log_loss(probability: float) -> float:
    return -log(max(min(probability, 1.0 - 1e-12), 1e-12))


def _probs_from_feature_map(feature_map: dict[str, float]) -> tuple[float, float, float]:
    return (
        _safe_float(feature_map.get("market_home"), default=0.0),
        _safe_float(feature_map.get("market_draw"), default=0.0),
        _safe_float(feature_map.get("market_away"), default=0.0),
    )


def _finalize_component_metrics(metrics: dict[str, dict[str, float]]) -> tuple[dict[str, dict[str, float | int]], dict[str, float]]:
    model_scores: dict[str, float] = {}
    finalized_metrics: dict[str, dict[str, float | int]] = {}
    for key, bucket in metrics.items():
        count = int(bucket["count"])
        if count <= 0:
            finalized_metrics[key] = {"logloss": 0.0, "brier": 0.0, "accuracy": 0.0, "count": 0}
            model_scores[key] = DEFAULT_ENSEMBLE_WEIGHTS[key]
            continue
        avg_logloss = bucket["logloss_sum"] / count
        avg_brier = bucket["brier_sum"] / count
        avg_accuracy = bucket["accuracy_sum"] / count
        finalized_metrics[key] = {
            "logloss": round(avg_logloss, 6),
            "brier": round(avg_brier, 6),
            "accuracy": round(avg_accuracy, 6),
            "count": count,
        }
        model_scores[key] = 1.0 / max(avg_logloss, 1e-6)
    return finalized_metrics, model_scores


def _weights_from_model_scores(
    model_scores: dict[str, float],
    base_blend: float,
    min_weight: float,
    max_weight: float,
) -> dict[str, float]:
    score_weights = _normalize_weights(model_scores)
    blend_ratio = max(0.0, min(base_blend, 1.0))
    blended_weights = {
        key: DEFAULT_ENSEMBLE_WEIGHTS[key] * blend_ratio + score_weights.get(key, 0.0) * (1.0 - blend_ratio)
        for key in DEFAULT_ENSEMBLE_WEIGHTS
    }
    clipped_weights = {
        key: max(min_weight, min(max_weight, float(value)))
        for key, value in blended_weights.items()
    }
    return _normalize_weights(clipped_weights)


def _collect_component_metrics_from_rows(rows: list[dict]) -> tuple[dict[str, dict[str, float | int]], dict[str, float]]:
    metrics: dict[str, dict[str, float]] = {
        key: {"logloss_sum": 0.0, "brier_sum": 0.0, "accuracy_sum": 0.0, "count": 0.0}
        for key in DEFAULT_ENSEMBLE_WEIGHTS
    }
    for row in rows:
        label = row.get("label")
        components = row.get("components", {})
        if label not in (0, 1, 2) or not isinstance(components, dict):
            continue
        for key, probs in components.items():
            if key not in metrics:
                continue
            normalized = _normalize_probs(float(probs[0]), float(probs[1]), float(probs[2]))
            prob_true = normalized[int(label)]
            one_hot = [1.0 if idx == label else 0.0 for idx in range(3)]
            brier = sum((float(normalized[idx]) - one_hot[idx]) ** 2 for idx in range(3)) / 3.0
            metrics[key]["logloss_sum"] += _model_log_loss(prob_true)
            metrics[key]["brier_sum"] += brier
            metrics[key]["accuracy_sum"] += 1.0 if normalized.index(max(normalized)) == label else 0.0
            metrics[key]["count"] += 1.0
    return _finalize_component_metrics(metrics)


def _build_league_weight_overrides(
    rows: list[dict],
    base_blend: float,
    min_weight: float,
    max_weight: float,
    min_samples: int = LEAGUE_WEIGHT_MIN_VALIDATION_SAMPLES,
) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        league = normalize_text(row.get("league", ""))
        if not league:
            continue
        grouped.setdefault(league, []).append(row)

    overrides: dict[str, dict] = {}
    for league, league_rows in grouped.items():
        if len(league_rows) < max(30, int(min_samples)):
            continue
        metrics, model_scores = _collect_component_metrics_from_rows(league_rows)
        weights = _weights_from_model_scores(model_scores, base_blend, min_weight, max_weight)
        dates = [row.get("match_date") for row in league_rows if row.get("match_date")]
        overrides[league] = {
            "weights": weights,
            "metrics": metrics,
            "sample_count": len(league_rows),
            "date_start": min(dates) if dates else None,
            "date_end": max(dates) if dates else None,
        }
    return overrides


def calibrate_ensemble_weights_now(
    validation_ratio: float = 0.20,
    min_validation_samples: int = 1000,
    base_blend: float = 0.35,
    min_weight: float = 0.08,
    max_weight: float = 0.55,
) -> dict:
    samples = STATE_STORE.load_xgb_samples()
    ordered = [item for item in samples if isinstance(item, dict) and isinstance(item.get("features"), dict)]
    ordered.sort(key=_sample_sort_key)
    sample_count = len(ordered)
    if sample_count < 300:
        return {
            "calibrated": False,
            "reason": "insufficient_samples",
            "sample_count": sample_count,
            "weights": _current_ensemble_weights(),
            "status": get_ensemble_weight_status(),
        }

    validation_count = max(int(sample_count * max(0.05, min(validation_ratio, 0.5))), int(min_validation_samples))
    validation_count = min(max(validation_count, 90), sample_count // 2 if sample_count >= 180 else sample_count)
    if validation_count <= 0 or sample_count - validation_count < 90:
        return {
            "calibrated": False,
            "reason": "split_too_small",
            "sample_count": sample_count,
            "weights": _current_ensemble_weights(),
            "status": get_ensemble_weight_status(),
        }

    train_items = ordered[:-validation_count]
    validation_items = ordered[-validation_count:]
    xgb_model = None
    xgb_reason = "ok"
    train_result = None
    try:
        x_matrix, y_vector = XGBOOST_MODEL._samples_to_xy(train_items)
        if x_matrix is None or y_vector is None:
            xgb_reason = "no_training_matrix"
        elif not XGBOOST_MODEL._can_train(y_vector, len(train_items), min_samples=90):
            xgb_reason = "insufficient_or_unbalanced_train"
        else:
            xgb_model = XGBOOST_MODEL.build_estimator()
            if xgb_model is None:
                xgb_reason = "xgb_unavailable"
            else:
                xgb_model.fit(x_matrix, y_vector)
                train_result = {
                    "train_sample_count": len(train_items),
                    "train_label_counts": XGBOOST_MODEL._label_counter(y_vector),
                }
    except Exception as exc:
        xgb_reason = f"xgb_validation_train_failed:{exc}"
        xgb_model = None

    component_rows, extra = _build_validation_component_rows(train_items, validation_items)
    finalized_metrics, model_scores = _collect_component_metrics_from_rows(component_rows)
    blend_ratio = max(0.0, min(base_blend, 1.0))
    calibrated_weights = _weights_from_model_scores(model_scores, blend_ratio, min_weight, max_weight)
    league_overrides = _build_league_weight_overrides(
        component_rows,
        base_blend=blend_ratio,
        min_weight=min_weight,
        max_weight=max_weight,
    )

    validation_meta = [item.get("meta", {}) for item in validation_items if isinstance(item.get("meta"), dict)]
    validation_dates = [normalize_text(meta.get("match_date", "")) for meta in validation_meta if normalize_text(meta.get("match_date", ""))]
    report = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "league_calibrated" if league_overrides else "calibrated",
        "weights": calibrated_weights,
        "default_weights": dict(DEFAULT_ENSEMBLE_WEIGHTS),
        "metrics": finalized_metrics,
        "validation": {
            "sample_count": len(validation_items),
            "train_sample_count": len(train_items),
            "ratio": round(validation_count / max(sample_count, 1), 4),
            "date_start": min(validation_dates) if validation_dates else None,
            "date_end": max(validation_dates) if validation_dates else None,
            "base_blend": round(blend_ratio, 4),
            "min_weight": round(min_weight, 4),
            "max_weight": round(max_weight, 4),
            "xgb_validation_reason": extra.get("xgb_validation_reason", xgb_reason),
            "league_override_count": len(league_overrides),
        },
        "league_weights": league_overrides,
    }
    if train_result:
        report["validation"]["train_label_counts"] = train_result.get("train_label_counts", {})

    _save_ensemble_weight_report(report)
    ENSEMBLE_ENGINE.set_weights(calibrated_weights)
    return {
        "calibrated": True,
        "reason": "ok",
        "sample_count": sample_count,
        "weights": calibrated_weights,
        "metrics": finalized_metrics,
        "validation": report["validation"],
        "status": get_ensemble_weight_status(),
    }


def _validation_split_samples(
    validation_ratio: float = 0.20,
    min_validation_samples: int = 1000,
) -> tuple[list[dict], list[dict]]:
    samples = STATE_STORE.load_xgb_samples()
    ordered = [item for item in samples if isinstance(item, dict) and isinstance(item.get("features"), dict)]
    ordered.sort(key=_sample_sort_key)
    sample_count = len(ordered)
    if sample_count <= 0:
        return [], []
    validation_count = max(int(sample_count * max(0.05, min(validation_ratio, 0.5))), int(min_validation_samples))
    validation_count = min(max(validation_count, 90), sample_count // 2 if sample_count >= 180 else sample_count)
    if validation_count <= 0 or sample_count - validation_count < 90:
        return [], []
    return ordered[:-validation_count], ordered[-validation_count:]


def _build_validation_component_rows(
    train_items: list[dict],
    validation_items: list[dict],
) -> tuple[list[dict], dict]:
    xgb_model = None
    xgb_reason = "ok"
    try:
        x_matrix, y_vector = XGBOOST_MODEL._samples_to_xy(train_items)
        if x_matrix is None or y_vector is None:
            xgb_reason = "no_training_matrix"
        elif not XGBOOST_MODEL._can_train(y_vector, len(train_items), min_samples=90):
            xgb_reason = "insufficient_or_unbalanced_train"
        else:
            xgb_model = XGBOOST_MODEL.build_estimator()
            if xgb_model is None:
                xgb_reason = "xgb_unavailable"
            else:
                xgb_model.fit(x_matrix, y_vector)
    except Exception as exc:
        xgb_reason = f"xgb_validation_train_failed:{exc}"
        xgb_model = None

    rows: list[dict] = []
    for item in validation_items:
        context = _sample_to_context(item)
        if context is None:
            continue
        features = item.get("features", {})
        meta = item.get("meta", {}) if isinstance(item.get("meta"), dict) else {}
        try:
            label = int(item.get("label"))
        except Exception:
            continue
        if label not in (0, 1, 2):
            continue
        components: dict[str, tuple[float, float, float]] = {
            "market": _normalize_probs(*_probs_from_feature_map(features)),
            "elo": _normalize_probs(*ELO_MODEL.predict(context).probabilities),
            "poisson": _normalize_probs(*POISSON_MODEL.predict(context).probabilities),
        }
        if xgb_model is not None:
            try:
                vector = [float(features.get(name, 0.0)) for name in XGBOOST_MODEL.FEATURE_ORDER]
                probs = xgb_model.predict_proba([vector])[0]
                components["xgboost"] = _normalize_probs(float(probs[0]), float(probs[1]), float(probs[2]))
            except Exception:
                components["xgboost"] = _normalize_probs(*_probs_from_feature_map(features))
                xgb_reason = "xgb_validation_predict_failed"
        else:
            components["xgboost"] = _normalize_probs(*_probs_from_feature_map(features))

        rows.append(
            {
                "label": label,
                "components": components,
                "match_id": item.get("match_id"),
                "match_date": normalize_text(meta.get("match_date", "")),
                "match_time": normalize_text(meta.get("match_time", "")),
                "league": normalize_text(meta.get("league", "")),
                "home_team": normalize_text(meta.get("home_team", "")),
                "away_team": normalize_text(meta.get("away_team", "")),
            }
        )
    return rows, {"xgb_validation_reason": xgb_reason}


def _evaluate_ensemble_scheme(rows: list[dict], weights: dict[str, float]) -> dict:
    normalized_weights = _normalize_weights({key: float(weights.get(key, 0.0)) for key in DEFAULT_ENSEMBLE_WEIGHTS})
    count = 0
    logloss_sum = 0.0
    brier_sum = 0.0
    accuracy_sum = 0.0
    for row in rows:
        label = row.get("label")
        components = row.get("components", {})
        if label not in (0, 1, 2) or not isinstance(components, dict):
            continue
        blend_home = 0.0
        blend_draw = 0.0
        blend_away = 0.0
        for key, probs in components.items():
            if key not in normalized_weights:
                continue
            home, draw, away = probs
            weight = normalized_weights.get(key, 0.0)
            blend_home += float(home) * weight
            blend_draw += float(draw) * weight
            blend_away += float(away) * weight
        probs = _normalize_probs(blend_home, blend_draw, blend_away)
        prob_true = probs[int(label)]
        one_hot = [1.0 if idx == label else 0.0 for idx in range(3)]
        brier = sum((float(probs[idx]) - one_hot[idx]) ** 2 for idx in range(3)) / 3.0
        logloss_sum += _model_log_loss(prob_true)
        brier_sum += brier
        accuracy_sum += 1.0 if probs.index(max(probs)) == label else 0.0
        count += 1
    if count <= 0:
        return {"logloss": 0.0, "brier": 0.0, "accuracy": 0.0, "count": 0, "weights": normalized_weights}
    return {
        "logloss": round(logloss_sum / count, 6),
        "brier": round(brier_sum / count, 6),
        "accuracy": round(accuracy_sum / count, 6),
        "count": count,
        "weights": normalized_weights,
    }


def _evaluate_league_aware_scheme(
    rows: list[dict],
    global_weights: dict[str, float],
    league_weights: dict[str, dict],
) -> dict:
    normalized_global = _normalize_weights({key: float(global_weights.get(key, 0.0)) for key in DEFAULT_ENSEMBLE_WEIGHTS})
    count = 0
    logloss_sum = 0.0
    brier_sum = 0.0
    accuracy_sum = 0.0
    league_hits = 0
    for row in rows:
        label = row.get("label")
        components = row.get("components", {})
        league = normalize_text(row.get("league", ""))
        if label not in (0, 1, 2) or not isinstance(components, dict):
            continue
        league_payload = league_weights.get(league, {}) if isinstance(league_weights, dict) else {}
        weights = league_payload.get("weights", {}) if isinstance(league_payload, dict) else {}
        normalized_weights = normalized_global
        if isinstance(weights, dict) and weights:
            normalized_weights = _normalize_weights({key: float(weights.get(key, 0.0)) for key in DEFAULT_ENSEMBLE_WEIGHTS})
            league_hits += 1
        blend_home = 0.0
        blend_draw = 0.0
        blend_away = 0.0
        for key, probs in components.items():
            if key not in normalized_weights:
                continue
            weight = normalized_weights.get(key, 0.0)
            blend_home += float(probs[0]) * weight
            blend_draw += float(probs[1]) * weight
            blend_away += float(probs[2]) * weight
        probs = _normalize_probs(blend_home, blend_draw, blend_away)
        prob_true = probs[int(label)]
        one_hot = [1.0 if idx == label else 0.0 for idx in range(3)]
        brier = sum((float(probs[idx]) - one_hot[idx]) ** 2 for idx in range(3)) / 3.0
        logloss_sum += _model_log_loss(prob_true)
        brier_sum += brier
        accuracy_sum += 1.0 if probs.index(max(probs)) == label else 0.0
        count += 1
    if count <= 0:
        return {"logloss": 0.0, "brier": 0.0, "accuracy": 0.0, "count": 0, "league_hits": 0, "weights": normalized_global}
    return {
        "logloss": round(logloss_sum / count, 6),
        "brier": round(brier_sum / count, 6),
        "accuracy": round(accuracy_sum / count, 6),
        "count": count,
        "league_hits": league_hits,
        "weights": normalized_global,
    }


def _evaluate_prediction_scheme_from_payloads(
    validation_items: list[dict],
    probability_field: str,
) -> dict:
    count = 0
    logloss_sum = 0.0
    brier_sum = 0.0
    accuracy_sum = 0.0
    draw_picks = 0
    draw_hits = 0
    for item in validation_items:
        prediction = _sample_item_prediction(item)
        if not isinstance(prediction, dict):
            continue
        probabilities = prediction.get(probability_field)
        if not isinstance(probabilities, dict):
            continue
        try:
            label = int(item.get("label"))
        except Exception:
            continue
        if label not in (0, 1, 2):
            continue
        probs = _normalize_probs(
            _safe_float(probabilities.get("home"), default=0.0),
            _safe_float(probabilities.get("draw"), default=0.0),
            _safe_float(probabilities.get("away"), default=0.0),
        )
        prob_true = probs[int(label)]
        one_hot = [1.0 if idx == label else 0.0 for idx in range(3)]
        brier = sum((float(probs[idx]) - one_hot[idx]) ** 2 for idx in range(3)) / 3.0
        prediction_idx = probs.index(max(probs))
        if prediction_idx == 1:
            draw_picks += 1
            if label == 1:
                draw_hits += 1
        logloss_sum += _model_log_loss(prob_true)
        brier_sum += brier
        accuracy_sum += 1.0 if prediction_idx == label else 0.0
        count += 1
    if count <= 0:
        return {
            "logloss": 0.0,
            "brier": 0.0,
            "accuracy": 0.0,
            "count": 0,
            "draw_picks": 0,
            "draw_hit_rate": 0.0,
        }
    return {
        "logloss": round(logloss_sum / count, 6),
        "brier": round(brier_sum / count, 6),
        "accuracy": round(accuracy_sum / count, 6),
        "count": count,
        "draw_picks": draw_picks,
        "draw_hit_rate": round(draw_hits / max(draw_picks, 1), 6),
    }


def _collect_bayes_validation_rows(validation_items: list[dict]) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    sample_dates: list[str] = []
    for item in validation_items:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        if label not in (0, 1, 2):
            continue
        prediction = _sample_item_prediction(item)
        if not isinstance(prediction, dict):
            continue
        pre_probs = prediction.get("pre_bayes_probabilities")
        if not isinstance(pre_probs, dict):
            pre_probs = prediction.get("probabilities")
        market_probs = prediction.get("market_probabilities")
        if not isinstance(pre_probs, dict) or not isinstance(market_probs, dict):
            continue
        normalized_pre = _normalize_probs(
            _safe_float(pre_probs.get("home"), default=0.0),
            _safe_float(pre_probs.get("draw"), default=0.0),
            _safe_float(pre_probs.get("away"), default=0.0),
        )
        normalized_market = _normalize_probs(
            _safe_float(market_probs.get("home"), default=0.0),
            _safe_float(market_probs.get("draw"), default=0.0),
            _safe_float(market_probs.get("away"), default=0.0),
        )
        meta = item.get("meta")
        rows.append(
            {
                "label": int(label),
                "league": normalize_text(meta.get("league", "")) if isinstance(meta, dict) else "",
                "pre_bayes_probabilities": {
                    "home": normalized_pre[0],
                    "draw": normalized_pre[1],
                    "away": normalized_pre[2],
                },
                "market_probabilities": {
                    "home": normalized_market[0],
                    "draw": normalized_market[1],
                    "away": normalized_market[2],
                },
            }
        )
        if isinstance(meta, dict):
            date_text = normalize_text(meta.get("match_date", ""))
            if date_text:
                sample_dates.append(date_text)
    extra = {
        "sample_count": len(rows),
        "date_start": min(sample_dates) if sample_dates else None,
        "date_end": max(sample_dates) if sample_dates else None,
    }
    return rows, extra


def _evaluate_bayes_config(rows: list[dict], candidate_config: dict) -> dict:
    logloss_sum = 0.0
    brier_sum = 0.0
    accuracy_sum = 0.0
    draw_picks = 0
    draw_hits = 0
    count = 0
    key_order = ("home", "draw", "away")
    for item in rows:
        label = item.get("label")
        pre_probs = item.get("pre_bayes_probabilities")
        market_probs = item.get("market_probabilities")
        if label not in (0, 1, 2) or not isinstance(pre_probs, dict) or not isinstance(market_probs, dict):
            continue
        calibrated, _meta = calibrate_three_way_probabilities(
            model_probabilities=pre_probs,
            market_probabilities=market_probs,
            config=candidate_config,
        )
        calibrated_tuple = (
            _safe_float(calibrated.get("home"), default=0.0),
            _safe_float(calibrated.get("draw"), default=0.0),
            _safe_float(calibrated.get("away"), default=0.0),
        )
        predicted_idx = int(max(range(3), key=lambda idx: calibrated_tuple[idx]))
        prob_true = calibrated_tuple[int(label)]
        one_hot = [1.0 if idx == label else 0.0 for idx in range(3)]
        brier = sum((calibrated_tuple[idx] - one_hot[idx]) ** 2 for idx in range(3)) / 3.0
        logloss_sum += _model_log_loss(prob_true)
        brier_sum += brier
        accuracy_sum += 1.0 if predicted_idx == label else 0.0
        if key_order[predicted_idx] == "draw":
            draw_picks += 1
            if int(label) == 1:
                draw_hits += 1
        count += 1
    if count <= 0:
        return {
            "count": 0,
            "logloss": 0.0,
            "brier": 0.0,
            "accuracy": 0.0,
            "draw_picks": 0,
            "draw_hit_rate": 0.0,
        }
    return {
        "count": count,
        "logloss": round(logloss_sum / count, 6),
        "brier": round(brier_sum / count, 6),
        "accuracy": round(accuracy_sum / count, 6),
        "draw_picks": draw_picks,
        "draw_hit_rate": round(draw_hits / max(draw_picks, 1), 6),
    }


def _bayes_candidate_grid(current_config: dict) -> list[dict]:
    current_min_prob = round(_safe_float(current_config.get("min_probability"), default=0.02), 3)
    min_probability_grid = sorted({0.0, 0.01, 0.02, current_min_prob})
    candidates: list[dict] = []
    for prior_source, prior_strength, model_strength, uncertainty_gain, draw_bias_scale, min_probability in product(
        ("market", "uniform"),
        (12.0, 20.0, 28.0, 36.0),
        (44.0, 56.0, 72.0),
        (0.0, 0.35, 0.55),
        (0.0, 0.12, 0.24),
        min_probability_grid,
    ):
        candidates.append(
            {
                "enabled": True,
                "prior_source": prior_source,
                "prior_strength": float(prior_strength),
                "model_strength": float(model_strength),
                "uncertainty_gain": float(uncertainty_gain),
                "draw_bias_scale": float(draw_bias_scale),
                "min_probability": float(min_probability),
            }
        )
    candidates.append(dict(current_config))
    return candidates


def _bayes_search_best(rows: list[dict], current_config: dict) -> tuple[dict, dict, dict, int]:
    baseline_metrics = _evaluate_bayes_config(rows, current_config)
    best_config = dict(current_config)
    best_metrics = dict(baseline_metrics)
    evaluated = 0
    for candidate in _bayes_candidate_grid(current_config):
        metrics = _evaluate_bayes_config(rows, candidate)
        evaluated += 1
        candidate_score = (
            float(metrics.get("logloss", 1.0)),
            float(metrics.get("brier", 1.0)),
            -float(metrics.get("accuracy", 0.0)),
        )
        best_score = (
            float(best_metrics.get("logloss", 1.0)),
            float(best_metrics.get("brier", 1.0)),
            -float(best_metrics.get("accuracy", 0.0)),
        )
        if candidate_score < best_score:
            best_config = _normalize_bayes_calibration_config(candidate)
            best_metrics = metrics
    return _normalize_bayes_calibration_config(best_config), baseline_metrics, best_metrics, evaluated


def _bayes_improvement_metrics(baseline_metrics: dict, best_metrics: dict) -> tuple[dict, bool]:
    logloss_delta = round(float(baseline_metrics.get("logloss", 0.0)) - float(best_metrics.get("logloss", 0.0)), 6)
    brier_delta = round(float(baseline_metrics.get("brier", 0.0)) - float(best_metrics.get("brier", 0.0)), 6)
    accuracy_delta = round(float(best_metrics.get("accuracy", 0.0)) - float(baseline_metrics.get("accuracy", 0.0)), 6)
    improved = (
        logloss_delta > 0.0001
        or brier_delta > 0.0001
        or (logloss_delta >= 0.0 and brier_delta >= 0.0 and accuracy_delta > 0.0005)
    )
    return {
        "logloss_delta": logloss_delta,
        "brier_delta": brier_delta,
        "accuracy_delta": accuracy_delta,
    }, improved


def _build_bayes_league_overrides(rows: list[dict], global_config: dict) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = {}
    for item in rows:
        league = normalize_text(item.get("league", ""))
        if not league:
            continue
        grouped.setdefault(league, []).append(item)
    overrides: dict[str, dict] = {}
    for league, league_rows in grouped.items():
        if len(league_rows) < int(BAYES_LEAGUE_MIN_VALIDATION_SAMPLES):
            continue
        league_best_config, league_baseline, league_best, evaluated = _bayes_search_best(
            rows=league_rows,
            current_config=global_config,
        )
        league_improvement, improved = _bayes_improvement_metrics(league_baseline, league_best)
        overrides[league] = {
            "enabled": bool(improved),
            "sample_count": len(league_rows),
            "config": league_best_config if improved else dict(global_config),
            "metrics": {
                "baseline": league_baseline,
                "best": league_best if improved else league_baseline,
                "improvement": league_improvement,
                "search": {"evaluated": evaluated},
            },
        }
    return overrides


def calibrate_bayes_calibration_now(
    validation_ratio: float = 0.20,
    min_validation_samples: int = 800,
) -> dict:
    train_items, validation_items = _validation_split_samples(
        validation_ratio=validation_ratio,
        min_validation_samples=min_validation_samples,
    )
    if not train_items or not validation_items:
        return {
            "calibrated": False,
            "reason": "insufficient_validation_split",
            "status": get_bayes_calibration_status(),
        }
    rows, extra = _collect_bayes_validation_rows(validation_items)
    if not rows:
        return {
            "calibrated": False,
            "reason": "no_valid_rows",
            "status": get_bayes_calibration_status(),
        }

    current_config = _current_bayes_calibration_config()
    best_config, baseline_metrics, best_metrics, evaluated = _bayes_search_best(
        rows=rows,
        current_config=current_config,
    )
    improvement, should_update = _bayes_improvement_metrics(baseline_metrics, best_metrics)
    if not should_update:
        best_config = dict(current_config)
        best_metrics = dict(baseline_metrics)
    league_overrides = _build_bayes_league_overrides(
        rows=rows,
        global_config=best_config if should_update else current_config,
    )

    report = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "calibrated" if should_update else "observed",
        "config": _normalize_bayes_calibration_config(best_config),
        "league_overrides": league_overrides,
        "metrics": {
            "baseline": baseline_metrics,
            "best": best_metrics,
            "improvement": improvement,
            "search": {
                "evaluated": evaluated,
            },
            "league_override_count": sum(
                1 for payload in league_overrides.values() if isinstance(payload, dict) and payload.get("enabled")
            ),
        },
        "validation": {
            "sample_count": int(extra.get("sample_count", len(rows))),
            "train_sample_count": len(train_items),
            "ratio": round(len(validation_items) / max(len(train_items) + len(validation_items), 1), 4),
            "date_start": extra.get("date_start"),
            "date_end": extra.get("date_end"),
        },
    }
    _save_bayes_calibration_report(report)
    return {
        "calibrated": should_update,
        "reason": "ok" if should_update else "no_significant_improvement",
        "validation": report["validation"],
        "metrics": report["metrics"],
        "config": report["config"],
        "league_overrides": league_overrides,
        "status": get_bayes_calibration_status(),
    }


def _play_thresholds_mtime() -> float | None:
    try:
        return PLAY_THRESHOLDS_FILE.stat().st_mtime
    except Exception:
        return None


def _load_play_threshold_report() -> dict:
    mtime = _play_thresholds_mtime()
    if mtime is not None and _PLAY_THRESHOLD_CACHE.get("mtime") == mtime:
        cached = _PLAY_THRESHOLD_CACHE.get("report")
        if isinstance(cached, dict):
            return cached
    if not PLAY_THRESHOLDS_FILE.exists():
        report = {
            "updated_at": None,
            "mode": "default",
            "thresholds": dict(DEFAULT_PLAY_THRESHOLDS),
            "metrics": {},
            "validation": {},
        }
        _PLAY_THRESHOLD_CACHE["mtime"] = None
        _PLAY_THRESHOLD_CACHE["thresholds"] = dict(DEFAULT_PLAY_THRESHOLDS)
        _PLAY_THRESHOLD_CACHE["report"] = report
        return report
    try:
        report = json.loads(PLAY_THRESHOLDS_FILE.read_text(encoding="utf-8"))
    except Exception:
        report = {}
    if not isinstance(report, dict):
        report = {}
    thresholds = report.get("thresholds")
    if not isinstance(thresholds, dict):
        thresholds = dict(DEFAULT_PLAY_THRESHOLDS)
        report["thresholds"] = thresholds
    report.setdefault("mode", "calibrated")
    report.setdefault("metrics", {})
    report.setdefault("validation", {})
    _PLAY_THRESHOLD_CACHE["mtime"] = mtime
    _PLAY_THRESHOLD_CACHE["thresholds"] = {
        key: float(thresholds.get(key, DEFAULT_PLAY_THRESHOLDS[key]))
        for key in DEFAULT_PLAY_THRESHOLDS
    }
    _PLAY_THRESHOLD_CACHE["report"] = report
    return report


def get_play_threshold_status() -> dict:
    report = _load_play_threshold_report()
    thresholds = report.get("thresholds", {})
    normalized = {
        key: float(thresholds.get(key, DEFAULT_PLAY_THRESHOLDS[key]))
        for key in DEFAULT_PLAY_THRESHOLDS
    }
    return {
        "updated_at": report.get("updated_at"),
        "mode": report.get("mode", "default"),
        "thresholds": normalized,
        "default_thresholds": dict(DEFAULT_PLAY_THRESHOLDS),
        "metrics": report.get("metrics", {}),
        "validation": report.get("validation", {}),
        "layered_filter": report.get("layered_filter", {}),
    }


def _current_play_thresholds() -> dict[str, float]:
    status = get_play_threshold_status()
    thresholds = status.get("thresholds", {})
    if not isinstance(thresholds, dict):
        return dict(DEFAULT_PLAY_THRESHOLDS)
    return {key: float(thresholds.get(key, DEFAULT_PLAY_THRESHOLDS[key])) for key in DEFAULT_PLAY_THRESHOLDS}


def _current_layered_filter_gates() -> dict:
    status = get_play_threshold_status()
    gates = status.get("layered_filter", {}) if isinstance(status, dict) else {}
    if not isinstance(gates, dict):
        return {}
    return gates if gates.get("enabled") else {}


def _layered_gate_for_play(
    *,
    match: AppMatch,
    play_type: str,
    confidence: float,
    threshold: float,
) -> tuple[bool, float, dict]:
    gates = _current_layered_filter_gates()
    if not gates:
        resolved_threshold = _safe_float(threshold, default=0.0)
        return _safe_float(confidence, default=0.0) >= resolved_threshold, resolved_threshold, {}

    league_key = normalize_text(match.league)
    play_key = normalize_text(play_type)
    global_play = gates.get("global_play", {}) if isinstance(gates.get("global_play"), dict) else {}
    league_play = gates.get("league_play", {}) if isinstance(gates.get("league_play"), dict) else {}
    candidates: list[dict] = []
    global_rule = global_play.get(play_key) if isinstance(global_play, dict) else None
    league_rules = league_play.get(league_key) if isinstance(league_play, dict) else None
    league_rule = league_rules.get(play_key) if isinstance(league_rules, dict) else None
    if isinstance(global_rule, dict):
        candidates.append({**global_rule, "scope": "global_play", "league": ""})
    if isinstance(league_rule, dict):
        candidates.append({**league_rule, "scope": "league_play", "league": league_key})

    resolved_threshold = _safe_float(threshold, default=0.0)
    blocked = False
    reasons: list[str] = []
    applied_rules: list[dict] = []
    for rule in candidates:
        min_threshold = _safe_float(rule.get("min_threshold"), default=resolved_threshold)
        resolved_threshold = max(resolved_threshold, min_threshold)
        if bool(rule.get("blocked")):
            blocked = True
        reason = normalize_text(rule.get("reason", ""))
        if reason:
            reasons.append(reason)
        applied_rules.append(
            {
                "scope": rule.get("scope", "-"),
                "league": rule.get("league", ""),
                "play_type": play_key,
                "min_threshold": round(min_threshold, 4),
                "blocked": bool(rule.get("blocked")),
                "sample_count": int(rule.get("sample_count", 0) or 0),
                "hit_rate": round(_safe_float(rule.get("hit_rate"), default=0.0), 4),
                "ev_bias": round(_safe_float(rule.get("ev_bias"), default=0.0), 4),
                "reason": reason or "-",
            }
        )

    resolved_threshold = round(_clamp(resolved_threshold, 0.0, 0.99), 4)
    passed = (not blocked) and _safe_float(confidence, default=0.0) >= resolved_threshold
    meta = {
        "threshold": resolved_threshold,
        "base_threshold": round(_safe_float(threshold, default=0.0), 4),
        "confidence": round(_safe_float(confidence, default=0.0), 4),
        "blocked": blocked,
        "reasons": reasons,
        "rules": applied_rules,
    }
    return passed, resolved_threshold, meta


def _runtime_dynamic_play_thresholds(base_thresholds: dict[str, float], *, window: int = 120) -> tuple[dict[str, float], dict[str, Any]]:
    normalized_base = {
        key: float(base_thresholds.get(key, DEFAULT_PLAY_THRESHOLDS[key]))
        for key in DEFAULT_PLAY_THRESHOLDS
    }
    threshold_mtime = _play_thresholds_mtime()
    cache_key = (
        round(_settlement_mtime(), 3),
        round(float(threshold_mtime or 0.0), 3),
        tuple((key, round(value, 4)) for key, value in sorted(normalized_base.items())),
        int(window),
    )
    if _LIVE_PLAY_THRESHOLD_CACHE.get("cache_key") == cache_key:
        cached_thresholds = _LIVE_PLAY_THRESHOLD_CACHE.get("thresholds")
        cached_meta = _LIVE_PLAY_THRESHOLD_CACHE.get("meta")
        if isinstance(cached_thresholds, dict) and isinstance(cached_meta, dict):
            return dict(cached_thresholds), dict(cached_meta)

    settlements = get_recent_settlements(limit=max(0, int(window)))
    observed = _collect_settlement_play_metrics(settlements)
    gate_records = [
        {
            "timestamp": item.get("timestamp"),
            "is_hit": item.get("is_correct"),
            "expected_hit": item.get("prediction_confidence"),
        }
        for item in settlements
        if isinstance(item, dict)
    ]
    single_gate = _gate_metrics_from_records(gate_records, breaker_threshold=4)
    losing_streak = int(single_gate.get("losing_streak", 0) or 0)
    breaker_on = bool(single_gate.get("breaker_on"))

    adjusted = dict(normalized_base)
    per_play: dict[str, dict[str, Any]] = {}

    for play_name, old_threshold in normalized_base.items():
        item = observed.get(play_name, {}) if isinstance(observed, dict) else {}
        sample_count = int(item.get("sample_count", 0) or 0)
        hit_rate = _safe_float(item.get("hit_rate"), default=0.0)
        expected_hit_rate = _safe_float(item.get("expected_hit_rate"), default=0.0)
        ev_bias = _safe_float(item.get("ev_bias"), default=0.0)
        delta = 0.0
        reasons: list[str] = []

        if sample_count >= 24 and play_name != "htft":
            if ev_bias <= -0.20:
                delta += 0.05
                reasons.append("ev_bias_very_low")
            elif ev_bias <= -0.14:
                delta += 0.04
                reasons.append("ev_bias_low")
            elif ev_bias <= -0.10:
                delta += 0.03
                reasons.append("ev_bias_low")
            elif ev_bias <= -0.06:
                delta += 0.02
                reasons.append("ev_bias_weak")
            elif ev_bias <= -0.03:
                delta += 0.01
                reasons.append("ev_bias_slight")
            elif sample_count >= 48 and ev_bias >= 0.14:
                delta -= 0.02
                reasons.append("ev_bias_strong_positive")
            elif sample_count >= 36 and ev_bias >= 0.08:
                delta -= 0.01
                reasons.append("ev_bias_positive")

            if expected_hit_rate > 0.0 and (expected_hit_rate - hit_rate) >= 0.18:
                delta += 0.01
                reasons.append("calibration_gap")

        if breaker_on or losing_streak >= 5:
            if play_name in {"1x2", "handicap"}:
                delta += 0.02
                reasons.append("breaker_hard")
            elif play_name in {"total_goals", "score", "htft"}:
                delta += 0.01
                reasons.append("breaker_soft")
        elif losing_streak >= 3 and play_name in {"1x2", "handicap"}:
            delta += 0.01
            reasons.append("losing_streak")

        min_thr, max_thr = PLAY_THRESHOLD_RANGE.get(play_name, (0.0, 1.0))
        new_threshold = round(_clamp(old_threshold + delta, min_thr, max_thr), 2)
        adjusted[play_name] = new_threshold
        per_play[play_name] = {
            "old": round(old_threshold, 2),
            "new": new_threshold,
            "delta": round(new_threshold - old_threshold, 2),
            "sample_count": sample_count,
            "hit_rate": round(hit_rate, 4),
            "expected_hit_rate": round(expected_hit_rate, 4),
            "ev_bias": round(ev_bias, 4),
            "reasons": reasons,
        }

    meta = {
        "window": int(window),
        "settlement_sample_count": len(settlements),
        "single_gate": {
            "sample_count": int(single_gate.get("sample_count", 0) or 0),
            "hit_rate": round(_safe_float(single_gate.get("hit_rate"), default=0.0), 4),
            "expected_hit_rate": round(_safe_float(single_gate.get("expected_hit_rate"), default=0.0), 4),
            "ev_bias": round(_safe_float(single_gate.get("ev_bias"), default=0.0), 4),
            "losing_streak": losing_streak,
            "breaker_on": breaker_on,
        },
        "per_play": per_play,
    }
    _LIVE_PLAY_THRESHOLD_CACHE["cache_key"] = cache_key
    _LIVE_PLAY_THRESHOLD_CACHE["thresholds"] = dict(adjusted)
    _LIVE_PLAY_THRESHOLD_CACHE["meta"] = dict(meta)
    return adjusted, meta


def _save_play_threshold_report(report: dict) -> None:
    if not isinstance(report, dict):
        return
    if "layered_filter" not in report:
        existing = _load_play_threshold_report()
        layered_filter = existing.get("layered_filter") if isinstance(existing, dict) else None
        if isinstance(layered_filter, dict) and layered_filter:
            report["layered_filter"] = layered_filter
    _safe_model_dir()
    PLAY_THRESHOLDS_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _PLAY_THRESHOLD_CACHE["mtime"] = _play_thresholds_mtime()
    _PLAY_THRESHOLD_CACHE["report"] = report
    _PLAY_THRESHOLD_CACHE["thresholds"] = dict(report.get("thresholds", DEFAULT_PLAY_THRESHOLDS))


def _play_model_policy_mtime() -> float | None:
    try:
        return PLAY_MODEL_POLICY_FILE.stat().st_mtime
    except Exception:
        return None


def _load_play_model_policy_report() -> dict:
    mtime = _play_model_policy_mtime()
    if _PLAY_MODEL_POLICY_CACHE.get("mtime") == mtime and _PLAY_MODEL_POLICY_CACHE.get("report"):
        return dict(_PLAY_MODEL_POLICY_CACHE.get("report", {}))
    if not PLAY_MODEL_POLICY_FILE.exists():
        report = {
            "updated_at": None,
            "mode": "default",
            "policy": json.loads(json.dumps(DEFAULT_PLAY_MODEL_POLICY)),
            "validation": {},
            "metrics": {},
        }
        _PLAY_MODEL_POLICY_CACHE["mtime"] = None
        _PLAY_MODEL_POLICY_CACHE["policy"] = json.loads(json.dumps(DEFAULT_PLAY_MODEL_POLICY))
        _PLAY_MODEL_POLICY_CACHE["report"] = report
        return report
    try:
        report = json.loads(PLAY_MODEL_POLICY_FILE.read_text(encoding="utf-8"))
    except Exception:
        report = {}
    if not isinstance(report, dict):
        report = {}
    policy = report.get("policy")
    if not isinstance(policy, dict):
        policy = json.loads(json.dumps(DEFAULT_PLAY_MODEL_POLICY))
        report["policy"] = policy
    report.setdefault("mode", "calibrated")
    report.setdefault("validation", {})
    report.setdefault("metrics", {})
    _PLAY_MODEL_POLICY_CACHE["mtime"] = mtime
    _PLAY_MODEL_POLICY_CACHE["policy"] = json.loads(json.dumps(policy))
    _PLAY_MODEL_POLICY_CACHE["report"] = report
    return report


def _save_play_model_policy_report(report: dict) -> None:
    if not isinstance(report, dict):
        return
    _safe_model_dir()
    PLAY_MODEL_POLICY_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _PLAY_MODEL_POLICY_CACHE["mtime"] = _play_model_policy_mtime()
    _PLAY_MODEL_POLICY_CACHE["policy"] = json.loads(json.dumps(report.get("policy", DEFAULT_PLAY_MODEL_POLICY)))
    _PLAY_MODEL_POLICY_CACHE["report"] = report


def _load_play_model_policy_history_entries() -> list[dict]:
    if not PLAY_MODEL_POLICY_HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(PLAY_MODEL_POLICY_HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items if isinstance(item, dict)]


def _write_play_model_policy_history_entries(items: list[dict]) -> None:
    PLAY_MODEL_POLICY_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": items[-200:],
    }
    PLAY_MODEL_POLICY_HISTORY_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_play_model_policy_history(*, limit: int = 20) -> list[dict]:
    items = _load_play_model_policy_history_entries()
    items.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("version_id") or "")), reverse=True)
    if limit <= 0:
        return items
    return items[: max(0, int(limit))]


def _load_play_model_takeover_gate_history_entries() -> list[dict]:
    if not PLAY_MODEL_TAKEOVER_GATE_HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(PLAY_MODEL_TAKEOVER_GATE_HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items if isinstance(item, dict)]


def _write_play_model_takeover_gate_history_entries(items: list[dict]) -> None:
    PLAY_MODEL_TAKEOVER_GATE_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": items[-300:],
    }
    PLAY_MODEL_TAKEOVER_GATE_HISTORY_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_play_model_takeover_gate_history(*, limit: int = 20) -> list[dict]:
    items = _load_play_model_takeover_gate_history_entries()
    items.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("version_id") or "")), reverse=True)
    if limit <= 0:
        return items
    return items[: max(0, int(limit))]


def _summarize_play_model_takeover_gate_history(items: list[dict]) -> dict:
    if not items:
        return {
            "history_count": 0,
            "latest_status": None,
            "latest_transition": None,
            "latest_reason": None,
            "latest_updated_at": None,
        }
    latest = items[0]
    metrics = latest.get("metrics", {}) if isinstance(latest.get("metrics"), dict) else {}
    validation = latest.get("validation", {}) if isinstance(latest.get("validation"), dict) else {}
    return {
        "history_count": len(items),
        "latest_status": latest.get("status"),
        "latest_previous_status": latest.get("previous_status"),
        "latest_transition": latest.get("transition"),
        "latest_reason": latest.get("reason"),
        "latest_updated_at": latest.get("updated_at"),
        "latest_policy_impact": latest.get("policy_impact"),
        "latest_backtest_ok": bool(latest.get("backtest_ok")),
        "latest_validation_sample_count": int(
            metrics.get("validation_sample_count", validation.get("sample_count", 0)) or 0
        ),
        "latest_total_goals_model_delta": _safe_float(metrics.get("total_goals_model_delta"), 0.0),
        "latest_score_model_delta": _safe_float(metrics.get("score_model_delta"), 0.0),
        "latest_report_path": latest.get("report_path"),
    }


def _write_play_model_takeover_gate_audit_markdown(
    history_items: list[dict],
    summary: dict,
    report_path: Path,
) -> None:
    lines = [
        "# Play Model Takeover Gate Audit Report",
        "",
        f"- Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- History Count: {int(summary.get('history_count', len(history_items)) or 0)}",
        f"- Latest Transition: {summary.get('latest_transition') or '-'}",
        f"- Latest Status: {summary.get('latest_status') or '-'}",
        f"- Latest Reason: {summary.get('latest_reason') or '-'}",
        f"- Latest Updated At: {summary.get('latest_updated_at') or '-'}",
        "",
        "| Updated At | Transition | Status | Reason | Samples | TotalGoals Delta | Score Delta | Policy Impact | Backtest | Report |",
        "|---|---|---|---|---:|---:|---:|---|---|---|",
    ]
    for item in history_items:
        if not isinstance(item, dict):
            continue
        metrics = item.get("metrics", {}) if isinstance(item.get("metrics"), dict) else {}
        validation = item.get("validation", {}) if isinstance(item.get("validation"), dict) else {}
        sample_count = int(metrics.get("validation_sample_count", validation.get("sample_count", 0)) or 0)
        total_delta = _safe_float(metrics.get("total_goals_model_delta"), 0.0)
        score_delta = _safe_float(metrics.get("score_model_delta"), 0.0)
        lines.append(
            "| "
            + f"{item.get('updated_at') or '-'} | "
            + f"{item.get('transition') or '-'} | "
            + f"{item.get('status') or '-'} | "
            + f"{item.get('reason') or '-'} | "
            + f"{sample_count} | "
            + f"{total_delta:+.2%} | "
            + f"{score_delta:+.2%} | "
            + f"{item.get('policy_impact') or '-'} | "
            + f"{'ok' if bool(item.get('backtest_ok')) else 'not_ok'} | "
            + f"{item.get('report_path') or '-'} |"
        )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _write_play_model_takeover_gate_audit_csv(history_items: list[dict], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "version_id",
                "updated_at",
                "previous_status",
                "status",
                "transition",
                "reason",
                "policy_impact",
                "blocking_count",
                "warning_count",
                "issue_codes",
                "validation_sample_count",
                "total_goals_model_delta",
                "score_model_delta",
                "backtest_ok",
                "backtest_reason",
                "report_path",
            ],
        )
        writer.writeheader()
        for item in history_items:
            if not isinstance(item, dict):
                continue
            metrics = item.get("metrics", {}) if isinstance(item.get("metrics"), dict) else {}
            validation = item.get("validation", {}) if isinstance(item.get("validation"), dict) else {}
            writer.writerow(
                {
                    "version_id": item.get("version_id"),
                    "updated_at": item.get("updated_at"),
                    "previous_status": item.get("previous_status"),
                    "status": item.get("status"),
                    "transition": item.get("transition"),
                    "reason": item.get("reason"),
                    "policy_impact": item.get("policy_impact"),
                    "blocking_count": int(item.get("blocking_count", 0) or 0),
                    "warning_count": int(item.get("warning_count", 0) or 0),
                    "issue_codes": ",".join(
                        str(code) for code in item.get("issue_codes", []) if str(code).strip()
                    ),
                    "validation_sample_count": int(metrics.get("validation_sample_count", validation.get("sample_count", 0)) or 0),
                    "total_goals_model_delta": round(_safe_float(metrics.get("total_goals_model_delta"), 0.0), 6),
                    "score_model_delta": round(_safe_float(metrics.get("score_model_delta"), 0.0), 6),
                    "backtest_ok": bool(item.get("backtest_ok")),
                    "backtest_reason": item.get("backtest_reason"),
                    "report_path": item.get("report_path"),
                }
            )


def export_play_model_takeover_gate_audit_report(*, limit: int = 200) -> dict:
    history_items = get_play_model_takeover_gate_history(limit=0)
    if limit > 0:
        history_items = history_items[: int(limit)]
    summary = _summarize_play_model_takeover_gate_history(history_items)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    markdown_path = REPORT_DIR / f"play_model_takeover_gate_audit_{timestamp}.md"
    csv_path = REPORT_DIR / f"play_model_takeover_gate_audit_{timestamp}.csv"
    _write_play_model_takeover_gate_audit_markdown(history_items, summary, markdown_path)
    _write_play_model_takeover_gate_audit_csv(history_items, csv_path)

    report = _load_play_model_policy_report()
    report["takeover_gate_audit_report"] = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "history_count": int(summary.get("history_count", len(history_items)) or 0),
        "latest_transition": summary.get("latest_transition"),
        "latest_reason": summary.get("latest_reason"),
        "markdown_path": str(markdown_path),
        "csv_path": str(csv_path),
    }
    _save_play_model_policy_report(report)
    return {
        "ok": True,
        "history_count": int(summary.get("history_count", len(history_items)) or 0),
        "summary": summary,
        "markdown_path": str(markdown_path),
        "csv_path": str(csv_path),
    }


def _append_play_model_takeover_gate_history_entry(
    gate: dict,
    previous_gate: dict | None,
    backtest_result: dict,
    *,
    source: str = "backtest",
) -> None:
    if not isinstance(gate, dict):
        return
    current_status = normalize_text(gate.get("status"))
    if current_status not in {"block", "watch", "allow"}:
        return
    previous = previous_gate if isinstance(previous_gate, dict) else {}
    previous_status = normalize_text(previous.get("status"))
    if previous_status == current_status:
        return
    history_items = _load_play_model_takeover_gate_history_entries()
    updated_at = str(gate.get("updated_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    version_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(history_items) + 1:04d}"
    issues = gate.get("issues", []) if isinstance(gate.get("issues"), list) else []
    history_items.append(
        {
            "version_id": version_id,
            "updated_at": updated_at,
            "source": str(source or "backtest"),
            "previous_status": previous_status or None,
            "status": current_status,
            "transition": f"{previous_status or 'none'}->{current_status}",
            "reason": str(gate.get("reason") or "-"),
            "recommendation": str(gate.get("recommendation") or "-"),
            "policy_impact": str(gate.get("policy_impact") or "-"),
            "blocking_count": int(gate.get("blocking_count", 0) or 0),
            "warning_count": int(gate.get("warning_count", 0) or 0),
            "issue_codes": [
                str(item.get("code") or "-")
                for item in issues
                if isinstance(item, dict)
            ],
            "metrics": json.loads(json.dumps(gate.get("metrics", {}) if isinstance(gate.get("metrics"), dict) else {})),
            "validation": json.loads(json.dumps(backtest_result.get("validation", {}) if isinstance(backtest_result.get("validation"), dict) else {})),
            "improvement": json.loads(json.dumps(backtest_result.get("improvement", {}) if isinstance(backtest_result.get("improvement"), dict) else {})),
            "backtest_ok": bool(backtest_result.get("ok")),
            "backtest_reason": str(backtest_result.get("reason") or "-"),
            "report_path": backtest_result.get("report_path"),
        }
    )
    _write_play_model_takeover_gate_history_entries(history_items)


def _append_play_model_policy_history_entry(report: dict, previous_report: dict | None, *, source: str = "calibration") -> None:
    if not isinstance(report, dict):
        return
    previous = previous_report if isinstance(previous_report, dict) else {}
    history_items = _load_play_model_policy_history_entries()
    version_id = str(report.get("version_id") or f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(history_items) + 1:04d}")
    updated_at = str(report.get("updated_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    metrics = report.get("metrics", {}) if isinstance(report.get("metrics"), dict) else {}
    total_goals = metrics.get("total_goals", {}) if isinstance(metrics.get("total_goals"), dict) else {}
    scoreline = metrics.get("scoreline", {}) if isinstance(metrics.get("scoreline"), dict) else {}
    history_items.append(
        {
            "version_id": version_id,
            "updated_at": updated_at,
            "source": str(source or "calibration"),
            "mode": report.get("mode", "calibrated"),
            "policy": json.loads(json.dumps(report.get("policy", DEFAULT_PLAY_MODEL_POLICY))),
            "previous_policy": json.loads(json.dumps(previous.get("policy", DEFAULT_PLAY_MODEL_POLICY))),
            "previous_updated_at": previous.get("updated_at"),
            "validation": json.loads(json.dumps(report.get("validation", {}))),
            "summary": {
                "total_goals_takeover_enabled": bool(total_goals.get("takeover_enabled")),
                "total_goals_reason": str(total_goals.get("reason") or "-"),
                "total_goals_uplift": total_goals.get("uplift"),
                "total_goals_holdout_uplift": total_goals.get("holdout_uplift"),
                "scoreline_takeover_enabled": bool(scoreline.get("takeover_enabled")),
                "scoreline_reason": str(scoreline.get("reason") or "-"),
                "scoreline_holdout_delta": scoreline.get("holdout_delta"),
            },
        }
    )
    _write_play_model_policy_history_entries(history_items)


def apply_play_model_takeover_gate_to_policy(policy: dict | None, takeover_gate: dict | None) -> dict:
    """Return the play-model policy after takeover-gate execution constraints."""
    effective = json.loads(json.dumps(DEFAULT_PLAY_MODEL_POLICY))
    if isinstance(policy, dict):
        for key, value in policy.items():
            if key in effective and isinstance(value, dict):
                effective[key].update(value)
    gate_status = normalize_text((takeover_gate or {}).get("status") if isinstance(takeover_gate, dict) else "")
    if gate_status in {"block", "watch"}:
        effective.setdefault("total_goals", {})["takeover_enabled"] = False
        effective.setdefault("scoreline", {})["takeover_enabled"] = False
    return effective


def _play_model_policy_blocked_by_gate(policy: dict | None, effective_policy: dict | None, takeover_gate: dict | None) -> bool:
    gate_status = normalize_text((takeover_gate or {}).get("status") if isinstance(takeover_gate, dict) else "")
    if gate_status not in {"block", "watch"}:
        return False
    raw = policy if isinstance(policy, dict) else {}
    effective = effective_policy if isinstance(effective_policy, dict) else {}
    for key in ("total_goals", "scoreline"):
        raw_item = raw.get(key, {}) if isinstance(raw.get(key), dict) else {}
        effective_item = effective.get(key, {}) if isinstance(effective.get(key), dict) else {}
        if bool(raw_item.get("takeover_enabled")) and not bool(effective_item.get("takeover_enabled")):
            return True
    return False


def get_play_model_policy_status() -> dict:
    report = _load_play_model_policy_report()
    policy = report.get("policy", {})
    normalized = json.loads(json.dumps(DEFAULT_PLAY_MODEL_POLICY))
    if isinstance(policy, dict):
        for key, value in policy.items():
            if key in normalized and isinstance(value, dict):
                normalized[key].update(value)
    takeover_gate = report.get("takeover_gate", {}) if isinstance(report.get("takeover_gate"), dict) else {}
    effective_policy = apply_play_model_takeover_gate_to_policy(normalized, takeover_gate)
    policy_blocked_by_gate = _play_model_policy_blocked_by_gate(normalized, effective_policy, takeover_gate)
    takeover_gate_history = get_play_model_takeover_gate_history(limit=0)
    takeover_gate_history_recent = takeover_gate_history[:5]
    return {
        "updated_at": report.get("updated_at"),
        "version_id": report.get("version_id", "-"),
        "mode": report.get("mode", "default"),
        "policy": normalized,
        "effective_policy": effective_policy,
        "policy_blocked_by_gate": policy_blocked_by_gate,
        "validation": report.get("validation", {}),
        "metrics": report.get("metrics", {}),
        "takeover_gate": takeover_gate,
        "last_backtest": report.get("last_backtest", {}),
        "takeover_gate_audit": _summarize_play_model_takeover_gate_history(takeover_gate_history),
        "takeover_gate_history": takeover_gate_history_recent,
        "takeover_gate_history_count": len(takeover_gate_history),
        "takeover_gate_audit_report": report.get("takeover_gate_audit_report", {}),
        "source": str(PLAY_MODEL_POLICY_FILE),
        "history_source": str(PLAY_MODEL_POLICY_HISTORY_FILE),
        "takeover_gate_history_source": str(PLAY_MODEL_TAKEOVER_GATE_HISTORY_FILE),
    }


def _load_state_payload(filename: str) -> dict:
    path = PROJECT_DIR / "data" / "state" / filename
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _state_payload_items(payload: dict) -> list[dict]:
    items = payload.get("items", []) if isinstance(payload, dict) else []
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _history_date_range(items: list[dict], date_key: str) -> tuple[str | None, str | None]:
    dates = [normalize_text(item.get(date_key, "")) for item in items if normalize_text(item.get(date_key, ""))]
    return (min(dates), max(dates)) if dates else (None, None)


def _state_file_signature(path: Path) -> dict[str, int]:
    try:
        stat = path.stat()
    except OSError:
        return {"mtime_ns": 0, "size_bytes": 0}
    return {"mtime_ns": int(stat.st_mtime_ns), "size_bytes": int(stat.st_size)}


def _state_summary_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}_summary.json")


def _load_state_items_summary(filename: str, *, date_key: str, year_key: str | None = None) -> dict:
    path = PROJECT_DIR / "data" / "state" / filename
    current_signature = _state_file_signature(path)
    summary_path = _state_summary_path(path)
    if summary_path.exists():
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload.get("source_signature") == current_signature:
                return payload
        except Exception:
            pass

    payload = _load_state_payload(filename)
    items = _state_payload_items(payload)
    date_start, date_end = _history_date_range(items, date_key)
    years: list[int] = []
    if year_key:
        years = sorted(
            {
                int(item.get(year_key))
                for item in items
                if isinstance(item.get(year_key), int) or str(item.get(year_key, "")).isdigit()
            }
        )
    summary = {
        "updated_at": payload.get("updated_at"),
        "source": payload.get("source"),
        "source_file": str(path),
        "source_signature": current_signature,
        "item_count": len(items),
        "date_start": date_start,
        "date_end": date_end,
    }
    if year_key:
        summary.update(
            {
                "year_start": min(years) if years else None,
                "year_end": max(years) if years else None,
                "year_count": len(years),
            }
        )
    try:
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return summary


TRAINING_HEALTH_MIN_XGB_SAMPLES = 300
TRAINING_HEALTH_MIN_VALID_FEATURES = 300
TRAINING_HEALTH_MIN_VALID_FEATURE_RATIO = 0.95
TRAINING_HEALTH_MIN_LABEL_CLASSES = 3
TRAINING_HEALTH_MIN_CLASS_COUNT = 30
TRAINING_HEALTH_MIN_LEAGUES = 5
TRAINING_HEALTH_MIN_CLUB_HISTORY = 100
TRAINING_HEALTH_MIN_MATCH_FACT_COVERAGE_RATIO = 0.80
TRAINING_HEALTH_MIN_SOURCE_PROVENANCE_RATIO = 0.80


def _int_count_mapping(payload: object) -> dict[str, int]:
    if not isinstance(payload, dict):
        return {}
    counts: dict[str, int] = {}
    for key, value in payload.items():
        try:
            count = int(value or 0)
        except Exception:
            continue
        counts[str(key)] = count
    return counts


def _training_health_issue(code: str, severity: str, message: str, recommendation: str) -> dict[str, str]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "recommendation": recommendation,
    }


def _ratio(numerator: int | float, denominator: int | float) -> float:
    try:
        denominator_value = float(denominator)
        if denominator_value <= 0:
            return 0.0
        return round(max(0.0, min(float(numerator) / denominator_value, 1.0)), 4)
    except Exception:
        return 0.0


def _statsbomb_action_fact_summary(items: list[dict]) -> dict:
    event_match_count = 0
    event_count = 0
    source_complete_count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        event_summary = item.get("event_summary", {}) if isinstance(item.get("event_summary"), dict) else {}
        item_event_count = int(_safe_int(event_summary.get("event_count"), 0) or 0)
        if item_event_count > 0:
            event_match_count += 1
            event_count += item_event_count
        if normalize_text(item.get("source", "")) or normalize_text(item.get("source_url", "")) or normalize_text(item.get("source_match_id", "")):
            source_complete_count += 1
    return {
        "event_match_count": event_match_count,
        "event_count": event_count,
        "source_complete_count": source_complete_count,
    }


def _prediction_trace_fact_ref_summary() -> dict:
    try:
        snapshots = STATE_STORE.load_prediction_snapshots()
    except Exception:
        snapshots = {}
    if not isinstance(snapshots, dict):
        return {
            "snapshot_count": 0,
            "trace_count": 0,
            "match_fact_trace_count": 0,
            "action_fact_trace_count": 0,
            "source_provenance_trace_count": 0,
            "trace_fact_ref_coverage_ratio": 0.0,
        }
    items_payload = snapshots.get("items")
    if isinstance(items_payload, dict):
        records = [item for item in items_payload.values() if isinstance(item, dict)]
    elif isinstance(items_payload, list):
        records = [item for item in items_payload if isinstance(item, dict)]
    else:
        records = [item for item in snapshots.values() if isinstance(item, dict)]
    trace_count = 0
    match_fact_trace_count = 0
    action_fact_trace_count = 0
    source_provenance_trace_count = 0
    for record in records:
        prediction = record.get("prediction", {}) if isinstance(record.get("prediction"), dict) else {}
        trace = prediction.get("trace") if isinstance(prediction.get("trace"), dict) else record.get("trace")
        if not isinstance(trace, dict):
            continue
        trace_count += 1
        fact_refs = trace.get("fact_refs") if isinstance(trace.get("fact_refs"), list) else []
        kinds = {
            str(item.get("kind") or "")
            for item in fact_refs
            if isinstance(item, dict)
        }
        if "match_fact" in kinds:
            match_fact_trace_count += 1
        if "action_fact" in kinds:
            action_fact_trace_count += 1
        if "source_provenance" in kinds:
            source_provenance_trace_count += 1
    snapshot_count = len(records)
    return {
        "snapshot_count": snapshot_count,
        "trace_count": trace_count,
        "match_fact_trace_count": match_fact_trace_count,
        "action_fact_trace_count": action_fact_trace_count,
        "source_provenance_trace_count": source_provenance_trace_count,
        "trace_fact_ref_coverage_ratio": _ratio(match_fact_trace_count, snapshot_count),
    }


def _build_fact_layer_coverage(
    *,
    xgb_samples: dict,
    club_history: dict,
    world_cup_history: dict,
    statsbomb_events: dict,
    statsbomb_items: list[dict],
) -> dict:
    sample_count = int(xgb_samples.get("sample_count", 0) or 0)
    club_match_count = int(club_history.get("match_count", 0) or 0)
    world_cup_match_count = int(world_cup_history.get("match_count", 0) or 0)
    statsbomb_match_count = int(statsbomb_events.get("match_count", 0) or 0)
    action_summary = _statsbomb_action_fact_summary(statsbomb_items)

    match_fact_available_count = club_match_count + world_cup_match_count + statsbomb_match_count
    match_fact_target_count = max(sample_count, match_fact_available_count)
    action_fact_match_count = int(action_summary.get("event_match_count", 0) or 0)
    action_fact_event_count = int(action_summary.get("event_count", 0) or 0)
    source_target_count = match_fact_available_count + action_fact_match_count
    club_source_count = club_match_count if club_history.get("source") else 0
    world_cup_source_count = world_cup_match_count if world_cup_history.get("source") else 0
    statsbomb_source_count = int(action_summary.get("source_complete_count", 0) or 0)
    source_complete_count = club_source_count + world_cup_source_count + statsbomb_source_count + action_fact_match_count
    trace_fact_refs = _prediction_trace_fact_ref_summary()

    return {
        "match_fact": {
            "available_count": match_fact_available_count,
            "target_count": match_fact_target_count,
            "coverage_ratio": _ratio(match_fact_available_count, match_fact_target_count),
            "club_history_count": club_match_count,
            "world_cup_history_count": world_cup_match_count,
            "statsbomb_match_count": statsbomb_match_count,
            "min_coverage_ratio": TRAINING_HEALTH_MIN_MATCH_FACT_COVERAGE_RATIO,
        },
        "action_fact": {
            "available_match_count": action_fact_match_count,
            "target_match_count": statsbomb_match_count,
            "coverage_ratio": _ratio(action_fact_match_count, statsbomb_match_count),
            "event_count": action_fact_event_count,
            "source": "statsbomb_event_summaries",
        },
        "source_provenance": {
            "complete_count": source_complete_count,
            "target_count": source_target_count,
            "coverage_ratio": _ratio(source_complete_count, source_target_count),
            "min_coverage_ratio": TRAINING_HEALTH_MIN_SOURCE_PROVENANCE_RATIO,
        },
        "trace_fact_refs": trace_fact_refs,
    }


def _build_training_health_diagnostics(
    *,
    xgb_samples: dict,
    club_history: dict,
    world_cup_history: dict,
    statsbomb_events: dict,
    rating_pools: dict,
    fact_coverage: dict | None = None,
) -> dict:
    issues: list[dict[str, str]] = []

    sample_count = int(xgb_samples.get("sample_count", 0) or 0)
    valid_feature_count = int(xgb_samples.get("valid_feature_count", 0) or 0)
    valid_feature_ratio = valid_feature_count / sample_count if sample_count > 0 else 0.0
    label_counts = _int_count_mapping(xgb_samples.get("label_counts", {}))
    present_label_counts = [count for count in label_counts.values() if count > 0]
    label_class_count = len(present_label_counts)
    min_class_count = min(present_label_counts) if present_label_counts else 0
    league_count = int(xgb_samples.get("league_count", 0) or 0)
    date_start = xgb_samples.get("date_start")
    date_end = xgb_samples.get("date_end")
    has_date_range = bool(date_start and date_end)

    if sample_count < TRAINING_HEALTH_MIN_XGB_SAMPLES:
        issues.append(
            _training_health_issue(
                "xgb_sample_count_low",
                "blocking",
                f"XGB样本数不足: {sample_count}/{TRAINING_HEALTH_MIN_XGB_SAMPLES}",
                "继续导入历史赛果样本，优先补齐最近赛季和主流联赛。",
            )
        )
    if valid_feature_count < TRAINING_HEALTH_MIN_VALID_FEATURES:
        issues.append(
            _training_health_issue(
                "xgb_valid_feature_count_low",
                "blocking",
                f"XGB有效特征样本不足: {valid_feature_count}/{TRAINING_HEALTH_MIN_VALID_FEATURES}",
                "检查样本特征生成链路，确保导入样本都带有完整features字段。",
            )
        )
    if sample_count > 0 and valid_feature_ratio < TRAINING_HEALTH_MIN_VALID_FEATURE_RATIO:
        issues.append(
            _training_health_issue(
                "xgb_valid_feature_ratio_low",
                "warning",
                f"XGB有效特征比例偏低: {valid_feature_ratio:.1%}",
                "清理无特征样本或重新生成缺失特征，避免训练集噪声扩大。",
            )
        )
    if label_class_count < TRAINING_HEALTH_MIN_LABEL_CLASSES:
        issues.append(
            _training_health_issue(
                "xgb_label_class_missing",
                "warning",
                f"XGB标签类别覆盖不足: {label_class_count}/{TRAINING_HEALTH_MIN_LABEL_CLASSES}",
                "补充主胜、平局、客胜三类都有结果的历史样本。",
            )
        )
    if present_label_counts and min_class_count < TRAINING_HEALTH_MIN_CLASS_COUNT:
        issues.append(
            _training_health_issue(
                "xgb_class_balance_low",
                "warning",
                f"XGB最小标签样本偏低: {min_class_count}/{TRAINING_HEALTH_MIN_CLASS_COUNT}",
                "扩大历史样本或在训练时降低小样本类别的过拟合风险。",
            )
        )
    if league_count < TRAINING_HEALTH_MIN_LEAGUES:
        issues.append(
            _training_health_issue(
                "xgb_league_coverage_low",
                "warning",
                f"XGB联赛覆盖不足: {league_count}/{TRAINING_HEALTH_MIN_LEAGUES}",
                "优先补充不同联赛样本，避免策略只适配单一赛事环境。",
            )
        )
    if not has_date_range:
        issues.append(
            _training_health_issue(
                "xgb_date_range_missing",
                "warning",
                "XGB样本缺少可用日期范围",
                "确保导入样本meta.match_date可解析，便于时间切分与回测。",
            )
        )

    club_match_count = int(club_history.get("match_count", 0) or 0)
    league_profile_count = int(club_history.get("league_profile_count", 0) or 0)
    if club_match_count < TRAINING_HEALTH_MIN_CLUB_HISTORY:
        issues.append(
            _training_health_issue(
                "club_history_low",
                "warning",
                f"俱乐部历史样本不足: {club_match_count}/{TRAINING_HEALTH_MIN_CLUB_HISTORY}",
                "继续扩充联赛历史数据，用于球队状态和联赛画像特征。",
            )
        )
    if club_match_count > 0 and league_profile_count <= 0:
        issues.append(
            _training_health_issue(
                "league_profiles_missing",
                "warning",
                "已存在俱乐部历史，但缺少联赛画像",
                "生成league_profiles，补齐不同联赛的进球、节奏和主场基准。",
            )
        )

    statsbomb_match_count = int(statsbomb_events.get("match_count", 0) or 0)
    statsbomb_review_sample_count = int(statsbomb_events.get("review_sample_count", 0) or 0)
    statsbomb_coverage_gap_count = int(statsbomb_events.get("coverage_gap_count", 0) or 0)
    statsbomb_coverage_candidate_count = int(statsbomb_events.get("coverage_candidate_count", 0) or 0)
    if statsbomb_match_count > 0 and statsbomb_review_sample_count <= 0:
        issues.append(
            _training_health_issue(
                "statsbomb_review_samples_missing",
                "warning",
                f"StatsBomb事件存在，但复盘训练样本为0（覆盖缺口 {statsbomb_coverage_gap_count}，候选 {statsbomb_coverage_candidate_count}）",
                f"将事件摘要转成复盘训练样本，优先补齐覆盖缺口 {statsbomb_coverage_gap_count} 个并复核候选 {statsbomb_coverage_candidate_count} 个。",
            )
        )

    fact_coverage = fact_coverage if isinstance(fact_coverage, dict) else {}
    match_fact = fact_coverage.get("match_fact", {}) if isinstance(fact_coverage.get("match_fact"), dict) else {}
    action_fact = fact_coverage.get("action_fact", {}) if isinstance(fact_coverage.get("action_fact"), dict) else {}
    source_provenance = fact_coverage.get("source_provenance", {}) if isinstance(fact_coverage.get("source_provenance"), dict) else {}
    trace_fact_refs = fact_coverage.get("trace_fact_refs", {}) if isinstance(fact_coverage.get("trace_fact_refs"), dict) else {}
    match_fact_ratio = _safe_float(match_fact.get("coverage_ratio"), 0.0)
    match_fact_target_count = int(match_fact.get("target_count", 0) or 0)
    action_fact_ratio = _safe_float(action_fact.get("coverage_ratio"), 0.0)
    action_fact_target_count = int(action_fact.get("target_match_count", 0) or 0)
    source_provenance_ratio = _safe_float(source_provenance.get("coverage_ratio"), 0.0)
    source_provenance_target_count = int(source_provenance.get("target_count", 0) or 0)
    if sample_count >= TRAINING_HEALTH_MIN_XGB_SAMPLES and match_fact_target_count > 0 and match_fact_ratio < TRAINING_HEALTH_MIN_MATCH_FACT_COVERAGE_RATIO:
        issues.append(
            _training_health_issue(
                "fact_match_coverage_low",
                "warning",
                f"MatchFact coverage is low: {match_fact_ratio:.1%}",
                "Materialize MatchFact rows for XGB/history samples before formal model training.",
            )
        )
    if action_fact_target_count > 0 and action_fact_ratio < 1.0:
        issues.append(
            _training_health_issue(
                "fact_action_coverage_low",
                "warning",
                f"ActionFact coverage is incomplete: {action_fact_ratio:.1%}",
                "Convert StatsBomb event summaries into canonical ActionFact sidecars.",
            )
        )
    if source_provenance_target_count > 0 and source_provenance_ratio < TRAINING_HEALTH_MIN_SOURCE_PROVENANCE_RATIO:
        issues.append(
            _training_health_issue(
                "fact_source_provenance_low",
                "warning",
                f"SourceProvenance completeness is low: {source_provenance_ratio:.1%}",
                "Backfill provider/source_id/source_version for fact-layer rows.",
            )
        )

    has_blocking = any(issue.get("severity") == "blocking" for issue in issues)
    status = "blocked" if has_blocking else "attention" if issues else "healthy"
    return {
        "status": status,
        "issue_count": len(issues),
        "blocking_count": sum(1 for issue in issues if issue.get("severity") == "blocking"),
        "warning_count": sum(1 for issue in issues if issue.get("severity") == "warning"),
        "issues": issues,
        "xgb_trainability": {
            "sample_count": sample_count,
            "min_sample_count": TRAINING_HEALTH_MIN_XGB_SAMPLES,
            "valid_feature_count": valid_feature_count,
            "min_valid_feature_count": TRAINING_HEALTH_MIN_VALID_FEATURES,
            "valid_feature_ratio": round(valid_feature_ratio, 4),
            "min_valid_feature_ratio": TRAINING_HEALTH_MIN_VALID_FEATURE_RATIO,
            "label_counts": label_counts,
            "label_class_count": label_class_count,
            "min_label_classes": TRAINING_HEALTH_MIN_LABEL_CLASSES,
            "min_class_count": min_class_count,
            "min_required_class_count": TRAINING_HEALTH_MIN_CLASS_COUNT,
            "league_count": league_count,
            "min_league_count": TRAINING_HEALTH_MIN_LEAGUES,
            "date_start": date_start,
            "date_end": date_end,
            "has_date_range": has_date_range,
        },
        "history_readiness": {
            "club_match_count": club_match_count,
            "min_club_match_count": TRAINING_HEALTH_MIN_CLUB_HISTORY,
            "club_date_start": club_history.get("date_start"),
            "club_date_end": club_history.get("date_end"),
            "league_profile_count": league_profile_count,
            "world_cup_match_count": int(world_cup_history.get("match_count", 0) or 0),
            "world_cup_year_start": world_cup_history.get("year_start"),
            "world_cup_year_end": world_cup_history.get("year_end"),
            "world_cup_year_count": int(world_cup_history.get("year_count", 0) or 0),
            "statsbomb_match_count": statsbomb_match_count,
            "statsbomb_review_sample_count": statsbomb_review_sample_count,
            "statsbomb_review_feature_count": int(statsbomb_events.get("review_feature_count", 0) or 0),
        },
        "rating_readiness": {
            "club_team_count": int(rating_pools.get("club_team_count", 0) or 0),
            "national_team_count": int(rating_pools.get("national_team_count", 0) or 0),
            "club_ready": int(rating_pools.get("club_team_count", 0) or 0) > 0,
            "national_ready": int(rating_pools.get("national_team_count", 0) or 0) > 0,
        },
        "fact_readiness": {
            "match_fact_available_count": int(match_fact.get("available_count", 0) or 0),
            "match_fact_target_count": match_fact_target_count,
            "match_fact_coverage_ratio": round(match_fact_ratio, 4),
            "min_match_fact_coverage_ratio": TRAINING_HEALTH_MIN_MATCH_FACT_COVERAGE_RATIO,
            "action_fact_match_count": int(action_fact.get("available_match_count", 0) or 0),
            "action_fact_target_match_count": action_fact_target_count,
            "action_fact_coverage_ratio": round(action_fact_ratio, 4),
            "action_fact_event_count": int(action_fact.get("event_count", 0) or 0),
            "source_provenance_complete_count": int(source_provenance.get("complete_count", 0) or 0),
            "source_provenance_target_count": source_provenance_target_count,
            "source_provenance_ratio": round(source_provenance_ratio, 4),
            "trace_snapshot_count": int(trace_fact_refs.get("snapshot_count", 0) or 0),
            "trace_fact_ref_coverage_ratio": _safe_float(trace_fact_refs.get("trace_fact_ref_coverage_ratio"), 0.0),
        },
    }


def get_training_data_coverage_status() -> dict:
    try:
        xgb_summary = STATE_STORE.load_xgb_samples_summary()
    except Exception:
        samples = STATE_STORE.load_xgb_samples()
        valid_samples = [item for item in samples if isinstance(item, dict) and isinstance(item.get("features"), dict)]
        sample_label_counts: dict[str, int] = {}
        for item in samples:
            if not isinstance(item, dict):
                continue
            try:
                label = str(int(item.get("label")))
                sample_label_counts[label] = sample_label_counts.get(label, 0) + 1
            except Exception:
                pass
        sample_meta = [item.get("meta", {}) for item in valid_samples if isinstance(item.get("meta"), dict)]
        sample_dates = [normalize_text(meta.get("match_date", "")) for meta in sample_meta if normalize_text(meta.get("match_date", ""))]
        sample_leagues = sorted({normalize_text(meta.get("league", "")) for meta in sample_meta if normalize_text(meta.get("league", ""))})
        xgb_summary = {
            "sample_count": len(samples),
            "valid_feature_count": len(valid_samples),
            "label_counts": sample_label_counts,
            "date_start": min(sample_dates) if sample_dates else None,
            "date_end": max(sample_dates) if sample_dates else None,
            "league_count": len(sample_leagues),
            "league_examples": sample_leagues[:8],
        }

    club_summary = _load_state_items_summary("club_match_history.json", date_key="match_date")
    world_cup_summary = _load_state_items_summary("world_cup_history.json", date_key="date", year_key="year")

    league_profile_payload = _load_state_payload("league_profiles.json")
    league_profiles = league_profile_payload.get("leagues", {})
    league_profile_count = len(league_profiles) if isinstance(league_profiles, dict) else 0

    statsbomb_payload = _load_state_payload("statsbomb_event_summaries.json")
    statsbomb_summary_items = _state_payload_items(statsbomb_payload)
    statsbomb_summary = _load_state_items_summary("statsbomb_event_summaries.json", date_key="match_date")
    statsbomb_review_payload = _load_state_payload("statsbomb_review_training_samples.json")
    statsbomb_review_items = _state_payload_items(statsbomb_review_payload)
    statsbomb_review_summary = statsbomb_review_payload.get("summary", {}) if isinstance(statsbomb_review_payload.get("summary"), dict) else {}
    statsbomb_coverage_audit = _build_statsbomb_coverage_audit(
        get_recent_settlements(limit=0),
        statsbomb_summary_items,
    )

    club_ratings = STATE_STORE.load_ratings()
    national_team_ratings = STATE_STORE.load_national_team_ratings()
    fact_coverage = _build_fact_layer_coverage(
        xgb_samples={
            "sample_count": int(xgb_summary.get("sample_count", 0) or 0),
        },
        club_history={
            "match_count": int(club_summary.get("item_count", 0) or 0),
            "source": club_summary.get("source"),
        },
        world_cup_history={
            "match_count": int(world_cup_summary.get("item_count", 0) or 0),
            "source": world_cup_summary.get("source"),
        },
        statsbomb_events={
            "match_count": int(statsbomb_summary.get("item_count", 0) or 0),
        },
        statsbomb_items=statsbomb_summary_items,
    )
    coverage = {
        "xgb_samples": {
            "sample_count": int(xgb_summary.get("sample_count", 0) or 0),
            "valid_feature_count": int(xgb_summary.get("valid_feature_count", 0) or 0),
            "label_counts": _int_count_mapping(xgb_summary.get("label_counts", {})),
            "date_start": xgb_summary.get("date_start"),
            "date_end": xgb_summary.get("date_end"),
            "league_count": int(xgb_summary.get("league_count", 0) or 0),
            "league_examples": xgb_summary.get("league_examples", [])[:8] if isinstance(xgb_summary.get("league_examples"), list) else [],
            "summary_source": str(getattr(STATE_STORE, "xgb_samples_summary_file", "")),
        },
        "club_history": {
            "match_count": int(club_summary.get("item_count", 0) or 0),
            "date_start": club_summary.get("date_start"),
            "date_end": club_summary.get("date_end"),
            "updated_at": club_summary.get("updated_at"),
            "source": club_summary.get("source"),
            "league_profile_count": league_profile_count,
            "summary_source": str(_state_summary_path(PROJECT_DIR / "data" / "state" / "club_match_history.json")),
        },
        "world_cup_history": {
            "match_count": int(world_cup_summary.get("item_count", 0) or 0),
            "date_start": world_cup_summary.get("date_start"),
            "date_end": world_cup_summary.get("date_end"),
            "updated_at": world_cup_summary.get("updated_at"),
            "source": world_cup_summary.get("source"),
            "year_start": world_cup_summary.get("year_start"),
            "year_end": world_cup_summary.get("year_end"),
            "year_count": int(world_cup_summary.get("year_count", 0) or 0),
            "summary_source": str(_state_summary_path(PROJECT_DIR / "data" / "state" / "world_cup_history.json")),
        },
        "statsbomb_events": {
            "match_count": int(statsbomb_summary.get("item_count", 0) or 0),
            "date_start": statsbomb_summary.get("date_start"),
            "date_end": statsbomb_summary.get("date_end"),
            "updated_at": statsbomb_summary.get("updated_at"),
            "source": statsbomb_summary.get("source"),
            "review_sample_count": len(statsbomb_review_items),
            "review_updated_at": statsbomb_review_payload.get("updated_at"),
            "review_feature_count": len(statsbomb_review_summary.get("feature_order", [])) if isinstance(statsbomb_review_summary.get("feature_order"), list) else 0,
            "coverage_audit": statsbomb_coverage_audit,
            "coverage_gap_count": int(statsbomb_coverage_audit.get("coverage_gap_count", 0) or 0),
            "coverage_candidate_count": int(statsbomb_coverage_audit.get("candidate_count", 0) or 0),
            "summary_source": str(_state_summary_path(PROJECT_DIR / "data" / "state" / "statsbomb_event_summaries.json")),
        },
        "rating_pools": {
            "club_team_count": len(club_ratings),
            "national_team_count": len(national_team_ratings),
        },
        "fact_coverage": fact_coverage,
    }
    coverage["training_health"] = _build_training_health_diagnostics(
        xgb_samples=coverage["xgb_samples"],
        club_history=coverage["club_history"],
        world_cup_history=coverage["world_cup_history"],
        statsbomb_events=coverage["statsbomb_events"],
        rating_pools=coverage["rating_pools"],
        fact_coverage=coverage["fact_coverage"],
    )
    return coverage


def _rate_text(hits: int, total: int) -> str:
    if total <= 0:
        return "-"
    return f"{hits / total:.1%}"


def _build_league_profiles_from_history_items(items: list[dict]) -> dict:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        league = normalize_text(item.get("league", "")) or "-"
        buckets[league].append(item)

    profiles: dict[str, dict] = {}
    for league, rows in sorted(buckets.items()):
        result_counts: Counter[str] = Counter()
        total_goals = 0
        under_count = 0
        date_values: list[str] = []
        for row in rows:
            home_goals = int(_safe_int(row.get("home_goals"), 0) or 0)
            away_goals = int(_safe_int(row.get("away_goals"), 0) or 0)
            goals = home_goals + away_goals
            total_goals += goals
            under_count += 1 if goals < 3 else 0
            if home_goals > away_goals:
                result_counts["home"] += 1
            elif home_goals < away_goals:
                result_counts["away"] += 1
            else:
                result_counts["draw"] += 1
            match_date = normalize_text(row.get("match_date", ""))
            if match_date:
                date_values.append(match_date)
        total = len(rows)
        profiles[league] = {
            "matches": total,
            "home_win_rate": _rate_text(result_counts["home"], total),
            "draw_rate": _rate_text(result_counts["draw"], total),
            "away_win_rate": _rate_text(result_counts["away"], total),
            "under_2_5_rate": _rate_text(under_count, total),
            "avg_total_goals": round(total_goals / total, 3) if total else 0.0,
            "date_start": min(date_values) if date_values else None,
            "date_end": max(date_values) if date_values else None,
        }
    return {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "club_match_history",
        "matches": len(items),
        "leagues": profiles,
    }


def rebuild_league_profiles_from_club_history() -> dict:
    payload = _load_state_payload("club_match_history.json")
    items = _state_payload_items(payload)
    if not items:
        return {
            "ok": False,
            "reason": "club_history_missing",
            "message": "未找到可用于生成联赛画像的俱乐部历史样本。",
            "match_count": 0,
            "league_profile_count": 0,
        }
    profile_payload = _build_league_profiles_from_history_items(items)
    path = PROJECT_DIR / "data" / "state" / "league_profiles.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "reason": "ok",
        "message": "联赛画像已从俱乐部历史样本生成。",
        "match_count": len(items),
        "league_profile_count": len(profile_payload.get("leagues", {})),
        "output_path": str(path),
    }


def _play_model_gate_items(play_model_status: dict) -> list[dict]:
    items: list[dict] = []
    for key, label in (
        ("total_goals", "总进球"),
        ("scoreline", "比分"),
        ("volatile_scoreline", "高波动比分"),
    ):
        status = play_model_status.get(key, {}) if isinstance(play_model_status.get(key), dict) else {}
        usable_count = int(status.get("usable_count", status.get("sample_count", 0)) or 0)
        min_train_samples = int(status.get("min_train_samples", 0) or 0)
        items.append(
            {
                "key": key,
                "label": label,
                "usable_count": usable_count,
                "min_train_samples": min_train_samples,
                "trainable": usable_count >= max(1, min_train_samples),
                "model_ready": bool(status.get("model_ready")),
                "model_updated_at": status.get("model_updated_at"),
            }
        )
    return items


def get_training_model_gate_status(
    coverage_status: dict | None = None,
    *,
    xgb_status: dict | None = None,
    play_model_status: dict | None = None,
) -> dict:
    coverage = coverage_status if isinstance(coverage_status, dict) else get_training_data_coverage_status()
    health = coverage.get("training_health", {}) if isinstance(coverage.get("training_health"), dict) else {}
    trainability = health.get("xgb_trainability", {}) if isinstance(health.get("xgb_trainability"), dict) else {}
    xgb = xgb_status if isinstance(xgb_status, dict) else get_xgb_training_status()
    play = play_model_status if isinstance(play_model_status, dict) else get_play_model_training_status()

    sample_count = int(trainability.get("sample_count", coverage.get("xgb_samples", {}).get("sample_count", 0) if isinstance(coverage.get("xgb_samples"), dict) else 0) or 0)
    valid_feature_count = int(trainability.get("valid_feature_count", coverage.get("xgb_samples", {}).get("valid_feature_count", 0) if isinstance(coverage.get("xgb_samples"), dict) else 0) or 0)
    min_sample_count = max(
        int(trainability.get("min_sample_count", TRAINING_HEALTH_MIN_XGB_SAMPLES) or TRAINING_HEALTH_MIN_XGB_SAMPLES),
        int(xgb.get("min_train_samples", 0) or 0),
    )
    min_valid_feature_count = int(trainability.get("min_valid_feature_count", TRAINING_HEALTH_MIN_VALID_FEATURES) or TRAINING_HEALTH_MIN_VALID_FEATURES)
    blocking_count = int(health.get("blocking_count", 0) or 0)
    xgb_available = bool(xgb.get("xgboost_available", True))
    xgb_trainable = (
        blocking_count <= 0
        and xgb_available
        and sample_count >= min_sample_count
        and valid_feature_count >= min_valid_feature_count
    )
    play_items = _play_model_gate_items(play)
    play_trainable_count = sum(1 for item in play_items if item.get("trainable"))
    play_ready_count = sum(1 for item in play_items if item.get("model_ready"))
    play_all_trainable = bool(play_items) and play_trainable_count == len(play_items)
    play_all_ready = bool(play_items) and play_ready_count == len(play_items)
    xgb_ready = bool(xgb.get("model_ready"))

    if blocking_count > 0 or not xgb_available:
        gate_status = "blocked"
        recommended_action = "fix_training_data"
        recommendation = "训练数据仍有阻塞项，先继续修复样本或特征。"
    elif xgb_trainable and not xgb_ready:
        gate_status = "ready_to_train_xgb"
        recommended_action = "train_xgb"
        recommendation = "训练样本已达到门槛，建议先训练主胜平负XGB。"
    elif xgb_ready and play_all_trainable and not play_all_ready:
        gate_status = "ready_to_train_play_models"
        recommended_action = "train_play_models"
        recommendation = "玩法模型样本已达到门槛，建议训练总进球、比分和高波动比分模型。"
    elif xgb_ready and play_all_ready:
        gate_status = "ready_for_backtest"
        recommended_action = "run_play_model_backtest"
        recommendation = "模型已就绪，建议进入玩法模型稳定性回测。"
    else:
        gate_status = "collecting"
        recommended_action = "collect_more_samples"
        recommendation = "部分玩法模型仍未达到训练门槛，继续积累或补齐样本。"

    return {
        "status": gate_status,
        "recommended_action": recommended_action,
        "recommendation": recommendation,
        "health_status": health.get("status"),
        "blocking_count": blocking_count,
        "warning_count": int(health.get("warning_count", 0) or 0),
        "xgb": {
            "sample_count": sample_count,
            "min_sample_count": min_sample_count,
            "valid_feature_count": valid_feature_count,
            "min_valid_feature_count": min_valid_feature_count,
            "trainable": xgb_trainable,
            "model_ready": xgb_ready,
            "xgboost_available": xgb_available,
            "model_updated_at": xgb.get("model_updated_at"),
        },
        "play_models": {
            "trainable_count": play_trainable_count,
            "ready_count": play_ready_count,
            "total_count": len(play_items),
            "all_trainable": play_all_trainable,
            "all_ready": play_all_ready,
            "items": play_items,
        },
    }


def _play_model_takeover_gate_issue(code: str, severity: str, message: str, recommendation: str) -> dict:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "recommendation": recommendation,
    }


def evaluate_play_model_takeover_gate(
    backtest_result: dict | None = None,
    *,
    training_gate: dict | None = None,
) -> dict:
    """Return a watch-only allow/watch/block decision for play-model takeover."""
    backtest = backtest_result if isinstance(backtest_result, dict) else {}
    gate = training_gate if isinstance(training_gate, dict) else get_training_model_gate_status()
    validation = backtest.get("validation", {}) if isinstance(backtest.get("validation"), dict) else {}
    improvement = backtest.get("improvement", {}) if isinstance(backtest.get("improvement"), dict) else {}
    sample_count = int(validation.get("sample_count", 0) or 0)
    total_goals_delta = _safe_float(improvement.get("total_goals_model_delta"), 0.0)
    score_delta = _safe_float(improvement.get("score_model_delta"), 0.0)
    training_gate_status = normalize_text(gate.get("status"))
    ok = bool(backtest.get("ok"))

    issues: list[dict] = []
    if training_gate_status and training_gate_status != "ready_for_backtest":
        issues.append(
            _play_model_takeover_gate_issue(
                "training_gate_not_ready",
                "blocking",
                f"Training gate is {training_gate_status}, not ready_for_backtest.",
                "Finish the model training gate before allowing formal takeover.",
            )
        )
    if not ok:
        issues.append(
            _play_model_takeover_gate_issue(
                "play_model_backtest_not_ok",
                "blocking",
                f"Play-model backtest is not OK: {backtest.get('reason') or 'not_run'}.",
                "Run a successful play-model backtest before allowing takeover.",
            )
        )
    if sample_count < PLAY_MODEL_TAKEOVER_GATE_MIN_VALIDATION_SAMPLES:
        issues.append(
            _play_model_takeover_gate_issue(
                "validation_sample_count_low",
                "blocking",
                f"Validation samples {sample_count}/{PLAY_MODEL_TAKEOVER_GATE_MIN_VALIDATION_SAMPLES}.",
                "Expand the validation history before allowing model takeover.",
            )
        )
    if total_goals_delta < PLAY_MODEL_TAKEOVER_GATE_TOTAL_GOALS_BLOCK_DELTA:
        issues.append(
            _play_model_takeover_gate_issue(
                "total_goals_model_regression",
                "blocking",
                f"Total-goals model delta {total_goals_delta:+.2%} is below the block threshold.",
                "Keep total-goals model in shadow mode and retrain or recalibrate it.",
            )
        )
    elif total_goals_delta < PLAY_MODEL_TAKEOVER_GATE_TOTAL_GOALS_MIN_DELTA:
        issues.append(
            _play_model_takeover_gate_issue(
                "total_goals_model_no_uplift",
                "warning",
                f"Total-goals model delta {total_goals_delta:+.2%} has no positive uplift.",
                "Keep observing total-goals model stability before takeover.",
            )
        )
    if score_delta < PLAY_MODEL_TAKEOVER_GATE_SCORE_BLOCK_DELTA:
        issues.append(
            _play_model_takeover_gate_issue(
                "score_model_regression",
                "blocking",
                f"Scoreline model delta {score_delta:+.2%} is below the block threshold.",
                "Keep scoreline model out of formal takeover and review feature quality.",
            )
        )
    elif score_delta < PLAY_MODEL_TAKEOVER_GATE_SCORE_MIN_DELTA:
        issues.append(
            _play_model_takeover_gate_issue(
                "score_model_margin_thin",
                "warning",
                f"Scoreline model delta {score_delta:+.2%} is below the watch threshold.",
                "Use scoreline model as shadow evidence until the margin improves.",
            )
        )

    blocking_count = sum(1 for item in issues if item.get("severity") == "blocking")
    warning_count = sum(1 for item in issues if item.get("severity") == "warning")
    if blocking_count:
        status = "block"
        recommendation = "Do not allow play-model takeover; keep current policy in shadow/watch mode."
    elif warning_count:
        status = "watch"
        recommendation = "Allow analysis visibility only; require another stable backtest before formal takeover."
    else:
        status = "allow"
        recommendation = "Backtest is stable enough for policy calibration or guarded takeover review."
    formal_takeover_allowed = status == "allow"

    return {
        "status": status,
        "mode": "enforced",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reason": issues[0]["code"] if issues else "stable_backtest",
        "recommendation": recommendation,
        "issues": issues,
        "blocking_count": blocking_count,
        "warning_count": warning_count,
        "metrics": {
            "training_gate_status": training_gate_status or "-",
            "validation_sample_count": sample_count,
            "min_validation_samples": PLAY_MODEL_TAKEOVER_GATE_MIN_VALIDATION_SAMPLES,
            "total_goals_model_delta": round(total_goals_delta, 6),
            "min_total_goals_model_delta": PLAY_MODEL_TAKEOVER_GATE_TOTAL_GOALS_MIN_DELTA,
            "block_total_goals_model_delta": PLAY_MODEL_TAKEOVER_GATE_TOTAL_GOALS_BLOCK_DELTA,
            "score_model_delta": round(score_delta, 6),
            "min_score_model_delta": PLAY_MODEL_TAKEOVER_GATE_SCORE_MIN_DELTA,
            "block_score_model_delta": PLAY_MODEL_TAKEOVER_GATE_SCORE_BLOCK_DELTA,
        },
        "policy_impact": "formal_takeover_allowed" if formal_takeover_allowed else "formal_takeover_disabled",
        "enforcement": {
            "formal_takeover_allowed": formal_takeover_allowed,
            "effective_policy_required": True,
        },
    }


def _save_play_model_takeover_gate_snapshot(gate: dict, backtest_result: dict) -> None:
    if not isinstance(gate, dict):
        return
    report = _load_play_model_policy_report()
    previous_gate = report.get("takeover_gate", {}) if isinstance(report.get("takeover_gate"), dict) else {}
    report["takeover_gate"] = json.loads(json.dumps(gate))
    report["last_backtest"] = {
        "updated_at": gate.get("updated_at"),
        "ok": bool(backtest_result.get("ok")),
        "reason": backtest_result.get("reason"),
        "validation": json.loads(json.dumps(backtest_result.get("validation", {}))),
        "improvement": json.loads(json.dumps(backtest_result.get("improvement", {}))),
        "report_path": backtest_result.get("report_path"),
    }
    _save_play_model_policy_report(report)
    _append_play_model_takeover_gate_history_entry(gate, previous_gate, backtest_result)


def repair_training_data_health(action_key: str, *, input_path: Path | str | None = None) -> dict:
    action = normalize_text(action_key)
    before = get_training_data_coverage_status()
    result: dict[str, object]
    if action == "import_historical_samples":
        if input_path is None:
            raise ValueError("input_path is required for import_historical_samples")
        result = import_historical_xgb_samples(
            project_dir=PROJECT_DIR,
            input_path=Path(input_path),
            replace=False,
            sync_ratings=True,
        )
        message = f"历史样本导入完成: 新增 {int(result.get('imported_samples', 0) or 0)} 条，保存 {int(result.get('saved_total', 0) or 0)} 条。"
    elif action == "rebuild_xgb_from_club_history":
        history_path = PROJECT_DIR / "data" / "state" / "club_match_history.json"
        if not history_path.exists():
            result = {
                "ok": False,
                "reason": "club_history_missing",
                "message": "club_match_history.json 不存在，无法重建XGB样本。",
            }
            message = str(result["message"])
        else:
            result = import_historical_xgb_samples(
                project_dir=PROJECT_DIR,
                input_path=history_path,
                replace=False,
                sync_ratings=True,
            )
            message = f"已从俱乐部历史重建XGB样本: 导入 {int(result.get('imported_samples', 0) or 0)} 条。"
    elif action == "build_league_profiles":
        result = rebuild_league_profiles_from_club_history()
        message = str(result.get("message") or "-")
    elif action == "build_statsbomb_review_samples":
        settlements = get_recent_settlements(limit=0)
        result = export_statsbomb_review_training_samples(
            project_dir=PROJECT_DIR,
            settlements=settlements,
        )
        message = f"StatsBomb复盘样本已生成: {int(result.get('sample_count', 0) or 0)} 条。"
    else:
        raise ValueError(f"Unsupported training data repair action: {action_key}")

    after = get_training_data_coverage_status()
    training_gate = get_training_model_gate_status(after)
    return {
        "action_key": action,
        "ok": bool(result.get("ok", True)) if isinstance(result, dict) else True,
        "message": message,
        "result": result,
        "generated_sample_count": int(result.get("sample_count", 0) or 0) if isinstance(result, dict) else 0,
        "skipped_reasons": {
            "missing_statsbomb": int(result.get("skipped_missing_statsbomb", 0) or 0) if isinstance(result, dict) else 0,
            "unknown_label": int(result.get("skipped_unknown_label", 0) or 0) if isinstance(result, dict) else 0,
        },
        "output_path": str(result.get("output_path", "")) if isinstance(result, dict) else "",
        "before_status": (before.get("training_health") or {}).get("status") if isinstance(before.get("training_health"), dict) else None,
        "after_status": (after.get("training_health") or {}).get("status") if isinstance(after.get("training_health"), dict) else None,
        "after": after,
        "training_gate": training_gate,
    }


def _current_play_model_policy(*, effective: bool = True) -> dict:
    status = get_play_model_policy_status()
    key = "effective_policy" if effective else "policy"
    return status.get(key, json.loads(json.dumps(DEFAULT_PLAY_MODEL_POLICY)))


def _bayes_calibration_mtime() -> float | None:
    try:
        return BAYES_CALIBRATION_FILE.stat().st_mtime
    except Exception:
        return None


def _normalize_bayes_calibration_config(config: dict | None) -> dict[str, float | str | bool]:
    normalized = dict(DEFAULT_BAYES_CALIBRATION)
    if not isinstance(config, dict):
        return normalized
    normalized["enabled"] = bool(config.get("enabled", DEFAULT_BAYES_CALIBRATION["enabled"]))
    normalized["prior_source"] = str(config.get("prior_source", DEFAULT_BAYES_CALIBRATION["prior_source"])).strip() or "market"
    normalized["prior_strength"] = max(1.0, _safe_float(config.get("prior_strength"), default=24.0))
    normalized["model_strength"] = max(1.0, _safe_float(config.get("model_strength"), default=56.0))
    normalized["uncertainty_gain"] = _clamp(_safe_float(config.get("uncertainty_gain"), default=0.55), 0.0, 2.0)
    normalized["draw_bias_scale"] = _clamp(_safe_float(config.get("draw_bias_scale"), default=0.18), 0.0, 2.0)
    normalized["min_probability"] = _clamp(_safe_float(config.get("min_probability"), default=0.02), 0.0, 0.32)
    return normalized


def _load_bayes_calibration_report() -> dict:
    mtime = _bayes_calibration_mtime()
    if _BAYES_CALIBRATION_CACHE.get("mtime") == mtime and _BAYES_CALIBRATION_CACHE.get("report"):
        return dict(_BAYES_CALIBRATION_CACHE.get("report", {}))
    if not BAYES_CALIBRATION_FILE.exists():
        report = {
            "updated_at": None,
            "mode": "default",
            "config": dict(DEFAULT_BAYES_CALIBRATION),
            "league_overrides": {},
            "metrics": {},
            "validation": {},
        }
        _BAYES_CALIBRATION_CACHE["mtime"] = None
        _BAYES_CALIBRATION_CACHE["config"] = dict(DEFAULT_BAYES_CALIBRATION)
        _BAYES_CALIBRATION_CACHE["report"] = report
        return report
    try:
        report = json.loads(BAYES_CALIBRATION_FILE.read_text(encoding="utf-8"))
    except Exception:
        report = {}
    if not isinstance(report, dict):
        report = {}
    config = _normalize_bayes_calibration_config(report.get("config"))
    report["config"] = config
    league_overrides = report.get("league_overrides")
    normalized_overrides: dict[str, dict] = {}
    if isinstance(league_overrides, dict):
        for league_key, payload in league_overrides.items():
            if not isinstance(league_key, str) or not isinstance(payload, dict):
                continue
            normalized_overrides[normalize_text(league_key)] = {
                **payload,
                "enabled": bool(payload.get("enabled", False)),
                "config": _normalize_bayes_calibration_config(payload.get("config")),
            }
    report["league_overrides"] = normalized_overrides
    report.setdefault("mode", "calibrated")
    report.setdefault("metrics", {})
    report.setdefault("validation", {})
    _BAYES_CALIBRATION_CACHE["mtime"] = mtime
    _BAYES_CALIBRATION_CACHE["config"] = dict(config)
    _BAYES_CALIBRATION_CACHE["report"] = report
    return report


def get_bayes_calibration_status() -> dict:
    report = _load_bayes_calibration_report()
    config = _normalize_bayes_calibration_config(report.get("config"))
    league_overrides = report.get("league_overrides", {})
    active_override_count = 0
    if isinstance(league_overrides, dict):
        active_override_count = sum(
            1 for payload in league_overrides.values() if isinstance(payload, dict) and payload.get("enabled")
        )
    return {
        "updated_at": report.get("updated_at"),
        "mode": report.get("mode", "default"),
        "config": config,
        "league_overrides": league_overrides if isinstance(league_overrides, dict) else {},
        "league_override_count": active_override_count,
        "default_config": dict(DEFAULT_BAYES_CALIBRATION),
        "metrics": report.get("metrics", {}),
        "validation": report.get("validation", {}),
    }


def _current_bayes_calibration_config(league: str | None = None) -> dict[str, float | str | bool]:
    status = get_bayes_calibration_status()
    config = status.get("config", {})
    if not isinstance(config, dict):
        config = dict(DEFAULT_BAYES_CALIBRATION)
    normalized_global = _normalize_bayes_calibration_config(config)
    league_key = normalize_text(league or "")
    if league_key:
        overrides = status.get("league_overrides", {})
        if isinstance(overrides, dict):
            payload = overrides.get(league_key)
            if isinstance(payload, dict) and bool(payload.get("enabled")):
                override_config = payload.get("config")
                if isinstance(override_config, dict):
                    return _normalize_bayes_calibration_config(override_config)
    return normalized_global


def _save_bayes_calibration_report(report: dict) -> None:
    if not isinstance(report, dict):
        return
    _safe_model_dir()
    BAYES_CALIBRATION_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _BAYES_CALIBRATION_CACHE["mtime"] = _bayes_calibration_mtime()
    _BAYES_CALIBRATION_CACHE["report"] = dict(report)
    _BAYES_CALIBRATION_CACHE["config"] = _normalize_bayes_calibration_config(report.get("config"))


def _sample_item_to_match(item: dict) -> AppMatch | None:
    if not isinstance(item, dict):
        return None
    features = item.get("features")
    meta = item.get("meta")
    if not isinstance(features, dict) or not isinstance(meta, dict):
        return None
    match_date = normalize_text(meta.get("match_date", ""))
    match_time = normalize_text(meta.get("match_time", "")) or "00:00"
    league = normalize_text(meta.get("league", ""))
    home_team = normalize_text(meta.get("home_team", ""))
    away_team = normalize_text(meta.get("away_team", ""))
    if not match_date or not league or not home_team or not away_team:
        return None
    return AppMatch(
        home_team=home_team,
        away_team=away_team,
        league=league,
        match_time=match_time,
        match_date=match_date,
        odds_home=_safe_float(features.get("odds_home"), default=2.2),
        odds_draw=_safe_float(features.get("odds_draw"), default=3.1),
        odds_away=_safe_float(features.get("odds_away"), default=2.8),
        handicap_line=_safe_float(meta.get("handicap_line"), default=0.0),
        opening_odds_home=_safe_float(meta.get("opening_odds_home"), default=_safe_float(features.get("opening_odds_home"), default=0.0)),
        opening_odds_draw=_safe_float(meta.get("opening_odds_draw"), default=_safe_float(features.get("opening_odds_draw"), default=0.0)),
        opening_odds_away=_safe_float(meta.get("opening_odds_away"), default=_safe_float(features.get("opening_odds_away"), default=0.0)),
        return_rate=_safe_float(meta.get("return_rate"), default=_safe_float(features.get("return_rate"), default=0.0)),
        kelly_home=_safe_float(meta.get("kelly_home"), default=_safe_float(features.get("kelly_home"), default=0.0)),
        kelly_draw=_safe_float(meta.get("kelly_draw"), default=_safe_float(features.get("kelly_draw"), default=0.0)),
        kelly_away=_safe_float(meta.get("kelly_away"), default=_safe_float(features.get("kelly_away"), default=0.0)),
        source="historical:sample",
        source_id=normalize_text(item.get("match_id", "")),
    )


def _sample_item_prediction(item: dict) -> dict | None:
    match = _sample_item_to_match(item)
    if match is None:
        return None
    features = item.get("features", {})
    recent_form = {
        key: _safe_float(features.get(key), default=0.0)
        for key in XGBOOST_MODEL.FEATURE_ORDER
        if key.startswith("home_recent_") or key.startswith("away_recent_") or key.startswith("recent_")
    }
    return _predict_match_with_inputs(
        match=match,
        home_rating=_safe_float(features.get("home_rating"), default=ELO_ENGINE.base_rating),
        away_rating=_safe_float(features.get("away_rating"), default=ELO_ENGINE.base_rating),
        league_strength=_safe_float(features.get("league_strength"), default=0.92),
        recent_form_features=recent_form,
    )


def _actual_htft_label_from_meta(meta: dict) -> str | None:
    if not isinstance(meta, dict):
        return None
    home_ht = _safe_int(meta.get("home_ht_goals"))
    away_ht = _safe_int(meta.get("away_ht_goals"))
    home_ft = _safe_int(meta.get("home_goals"))
    away_ft = _safe_int(meta.get("away_goals"))
    if None in {home_ht, away_ht, home_ft, away_ft}:
        return None
    first_half = _result_label(int(home_ht), int(away_ht))
    full_time = _result_label(int(home_ft), int(away_ft))
    mapping = {"主胜": "胜", "平局": "平", "客胜": "负", "涓昏儨": "胜", "骞冲眬": "平", "瀹㈣儨": "负"}
    return f"{mapping.get(first_half, '-')} / {mapping.get(full_time, '-')}"


def _collect_play_observations(validation_items: list[dict]) -> tuple[dict[str, list[dict]], dict]:
    observations = {key: [] for key in DEFAULT_PLAY_THRESHOLDS}
    skipped = 0
    for item in validation_items:
        prediction = _sample_item_prediction(item)
        meta = item.get("meta", {}) if isinstance(item.get("meta"), dict) else {}
        if not isinstance(prediction, dict) or not isinstance(meta, dict):
            skipped += 1
            continue
        home_goals = _safe_int(meta.get("home_goals"))
        away_goals = _safe_int(meta.get("away_goals"))
        if home_goals is None or away_goals is None:
            skipped += 1
            continue
        result = _result_label(int(home_goals), int(away_goals))
        predicted_handicap_display, predicted_handicap_label, handicap_confidence = _extract_handicap_prediction(prediction)
        handicap_result_label = _handicap_label_from_key(
            _handicap_outcome_key(int(home_goals), int(away_goals), _safe_float(meta.get("handicap_line"), default=0.0))
        )
        total_goals_pick, total_goals_value, total_goals_confidence = _extract_total_goals_prediction(prediction)
        score_pick, score_confidence = _extract_score_prediction(prediction)
        htft_pick, htft_confidence = _extract_htft_prediction(prediction)
        actual_score = f"{int(home_goals)}-{int(away_goals)}"
        actual_htft = _actual_htft_label_from_meta(meta)

        observations["1x2"].append(
            {
                "confidence": _safe_float(prediction.get("confidence"), default=0.0),
                "is_hit": bool(prediction.get("recommendation") == result),
            }
        )
        observations["handicap"].append(
            {
                "confidence": _safe_float(handicap_confidence, default=0.0),
                "is_hit": bool(predicted_handicap_label == handicap_result_label) if predicted_handicap_label else False,
            }
        )
        observations["total_goals"].append(
            {
                "confidence": _safe_float(total_goals_confidence, default=0.0),
                "is_hit": bool(total_goals_value == int(home_goals) + int(away_goals)) if total_goals_value is not None else False,
            }
        )
        observations["score"].append(
            {
                "confidence": _safe_float(score_confidence, default=0.0),
                "is_hit": bool(score_pick == actual_score) if score_pick else False,
            }
        )
        if actual_htft:
            observations["htft"].append(
                {
                    "confidence": _safe_float(htft_confidence, default=0.0),
                    "is_hit": bool(htft_pick == actual_htft) if htft_pick else False,
                }
            )
    return observations, {"skipped": skipped}


def _select_play_threshold(
    play_name: str,
    observations: list[dict],
    default_threshold: float,
    min_selected: int = 120,
    min_coverage: float = 0.12,
) -> dict:
    cleaned = [
        {
            "confidence": _safe_float(item.get("confidence"), default=0.0),
            "is_hit": bool(item.get("is_hit")),
        }
        for item in observations
        if isinstance(item, dict)
    ]
    total = len(cleaned)
    if total <= 0:
        return {
            "threshold": default_threshold,
            "accuracy": 0.0,
            "coverage": 0.0,
            "selected": 0,
            "reason": "no_observations",
        }
    candidates = sorted({round(item["confidence"], 2) for item in cleaned})
    if round(default_threshold, 2) not in candidates:
        candidates.append(round(default_threshold, 2))
        candidates.sort()

    baseline_selected = [item for item in cleaned if item["confidence"] >= default_threshold]
    baseline_accuracy = (
        sum(1 for item in baseline_selected if item["is_hit"]) / len(baseline_selected)
        if baseline_selected else 0.0
    )
    best = {
        "threshold": float(default_threshold),
        "accuracy": baseline_accuracy,
        "coverage": len(baseline_selected) / total if total else 0.0,
        "selected": len(baseline_selected),
        "reason": "default",
    }
    for threshold in candidates:
        selected = [item for item in cleaned if item["confidence"] >= threshold]
        selected_count = len(selected)
        coverage = selected_count / total if total else 0.0
        if selected_count < min_selected or coverage < min_coverage:
            continue
        accuracy = sum(1 for item in selected if item["is_hit"]) / selected_count
        if accuracy > best["accuracy"] + 1e-9 or (
            abs(accuracy - best["accuracy"]) <= 1e-9 and coverage > best["coverage"] + 1e-9
        ) or (
            abs(accuracy - best["accuracy"]) <= 1e-9
            and abs(coverage - best["coverage"]) <= 1e-9
            and threshold > best["threshold"]
        ):
            best = {
                "threshold": float(threshold),
                "accuracy": accuracy,
                "coverage": coverage,
                "selected": selected_count,
                "reason": "optimized",
            }
    return {
        "threshold": round(float(best["threshold"]), 2),
        "accuracy": round(float(best["accuracy"]), 6),
        "coverage": round(float(best["coverage"]), 6),
        "selected": int(best["selected"]),
        "reason": best["reason"],
    }


def calibrate_play_thresholds_now(
    validation_ratio: float = 0.20,
    min_validation_samples: int = 1000,
    write_report: bool = True,
) -> dict:
    train_items, validation_items = _validation_split_samples(
        validation_ratio=validation_ratio,
        min_validation_samples=min_validation_samples,
    )
    if not train_items or not validation_items:
        return {
            "calibrated": False,
            "reason": "insufficient_validation_split",
            "status": get_play_threshold_status(),
        }

    observations, extra = _collect_play_observations(validation_items)
    thresholds: dict[str, float] = {}
    metrics: dict[str, dict] = {}
    for play_name, default_threshold in DEFAULT_PLAY_THRESHOLDS.items():
        result = _select_play_threshold(play_name, observations.get(play_name, []), default_threshold)
        thresholds[play_name] = float(result["threshold"])
        metrics[play_name] = {
            "threshold": float(result["threshold"]),
            "accuracy": float(result["accuracy"]),
            "coverage": float(result["coverage"]),
            "selected": int(result["selected"]),
            "total": len(observations.get(play_name, [])),
            "reason": result["reason"],
        }

    dates = [
        normalize_text(item.get("meta", {}).get("match_date", ""))
        for item in validation_items
        if isinstance(item.get("meta"), dict)
    ]
    dates = [item for item in dates if item]
    report = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "calibrated",
        "thresholds": thresholds,
        "metrics": metrics,
        "validation": {
            "sample_count": len(validation_items),
            "train_sample_count": len(train_items),
            "date_start": min(dates) if dates else None,
            "date_end": max(dates) if dates else None,
            "ratio": round(len(validation_items) / max(len(train_items) + len(validation_items), 1), 4),
            "skipped": int(extra.get("skipped", 0)),
        },
    }
    _save_play_threshold_report(report)

    report_path = None
    if write_report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = REPORT_DIR / f"play_thresholds_backtest_{timestamp}.md"
        lines = [
            "# Play Threshold Calibration Report",
            "",
            f"- Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- Validation Samples: {report['validation']['sample_count']}",
            f"- Train Samples: {report['validation']['train_sample_count']}",
            f"- Validation Window: {report['validation']['date_start']} -> {report['validation']['date_end']}",
            "",
            "| Play | Threshold | Accuracy | Coverage | Selected | Total |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for play_name in ("1x2", "handicap", "total_goals", "htft", "score"):
            item = metrics.get(play_name, {})
            lines.append(
                f"| {play_name} | {float(item.get('threshold', 0) or 0):.2f} | {float(item.get('accuracy', 0) or 0):.2%} | {float(item.get('coverage', 0) or 0):.2%} | {int(item.get('selected', 0) or 0)} | {int(item.get('total', 0) or 0)} |"
            )
        report_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "calibrated": True,
        "reason": "ok",
        "thresholds": thresholds,
        "metrics": metrics,
        "validation": report["validation"],
        "report_path": str(report_path) if report_path else None,
        "status": get_play_threshold_status(),
    }


def _collect_settlement_play_metrics(settlements: list[dict]) -> dict[str, dict]:
    specs = {
        "1x2": ("is_correct", "prediction_confidence"),
        "handicap": ("handicap_is_correct", "handicap_confidence"),
        "total_goals": ("total_goals_is_correct", "total_goals_confidence"),
        "score": ("score_is_correct", "score_confidence"),
    }
    metrics: dict[str, dict] = {}
    for play_name, (hit_key, conf_key) in specs.items():
        rows: list[tuple[bool, float]] = []
        for item in settlements:
            if not isinstance(item, dict):
                continue
            hit = item.get(hit_key)
            if not isinstance(hit, bool):
                continue
            confidence = _safe_float(item.get(conf_key), default=0.0)
            if confidence <= 0.0 or confidence > 1.0:
                confidence = _safe_float(item.get("prediction_confidence"), default=0.0)
            if confidence <= 0.0 or confidence > 1.0:
                confidence = 0.0
            rows.append((hit, confidence))
        sample_count = len(rows)
        hit_count = sum(1 for hit, _ in rows if hit)
        hit_rate = (hit_count / sample_count) if sample_count > 0 else 0.0
        expected_values = [confidence for _, confidence in rows if confidence > 0.0]
        confidence_values = [confidence for _, confidence in rows if confidence > 0.0]
        expected_hit_rate = (sum(expected_values) / len(expected_values)) if expected_values else 0.0
        metrics[play_name] = {
            "sample_count": sample_count,
            "hit_count": hit_count,
            "hit_rate": round(hit_rate, 6),
            "expected_count": len(expected_values),
            "expected_hit_rate": round(expected_hit_rate, 6),
            "ev_bias": round((hit_rate - expected_hit_rate) if expected_values else 0.0, 6),
            "confidence_values": confidence_values,
        }

    if "htft" not in metrics:
        metrics["htft"] = {
            "sample_count": 0,
            "hit_count": 0,
            "hit_rate": 0.0,
            "expected_count": 0,
            "expected_hit_rate": 0.0,
            "ev_bias": 0.0,
            "reason": "not_settled",
            "confidence_values": [],
        }
    return metrics


def _settlement_layered_play_records(settlements: list[dict]) -> list[dict]:
    specs = {
        "1x2": ("is_correct", "prediction_confidence"),
        "handicap": ("handicap_is_correct", "handicap_confidence"),
        "total_goals": ("total_goals_is_correct", "total_goals_confidence"),
        "score": ("score_is_correct", "score_confidence"),
        "ou": ("ou_is_correct", "ou_confidence"),
    }
    records: list[dict] = []
    for item in settlements:
        if not isinstance(item, dict):
            continue
        league = normalize_text(item.get("league", "")) or "-"
        fallback_confidence = item.get("prediction_confidence")
        for play_type, (hit_key, conf_key) in specs.items():
            hit = item.get(hit_key)
            if not isinstance(hit, bool):
                continue
            confidence = _safe_float(item.get(conf_key), default=-1.0)
            if confidence <= 0.0 or confidence > 1.0:
                confidence = _safe_float(fallback_confidence, default=0.0)
            records.append(
                {
                    "league": league,
                    "play_type": "total_goals" if play_type == "ou" else play_type,
                    "confidence": _clamp(confidence),
                    "is_hit": bool(hit),
                }
            )
    return records


def _layered_gate_rule_from_rows(
    rows: list[dict],
    *,
    play_type: str,
    base_threshold: float,
    min_samples: int,
    weak_hit_rate: float,
    weak_ev_bias: float,
    block_hit_rate: float,
    block_ev_bias: float,
) -> dict | None:
    sample_count = len(rows)
    if sample_count < min_samples:
        return None
    hit_count = sum(1 for row in rows if bool(row.get("is_hit")))
    hit_rate = hit_count / max(sample_count, 1)
    expected_values = [_safe_float(row.get("confidence"), default=0.0) for row in rows]
    expected_hit_rate = sum(expected_values) / max(len(expected_values), 1)
    ev_bias = hit_rate - expected_hit_rate
    current_threshold = _safe_float(base_threshold, default=DEFAULT_PLAY_THRESHOLDS.get(play_type, 0.0))
    min_thr, max_thr = PLAY_THRESHOLD_RANGE.get(play_type, (0.0, 0.99))
    blocked = False
    raise_steps = 0
    reasons: list[str] = []

    if hit_rate <= block_hit_rate and ev_bias <= block_ev_bias and sample_count >= max(min_samples, 12):
        blocked = True
        raise_steps = 3
        reasons.append("block_weak_layer")
    elif hit_rate <= weak_hit_rate or ev_bias <= weak_ev_bias:
        raise_steps = 2 if ev_bias <= weak_ev_bias - 0.06 else 1
        reasons.append("raise_weak_layer")
    else:
        return None

    min_threshold = round(_clamp(current_threshold + raise_steps * 0.03, min_thr, max_thr), 2)
    return {
        "play_type": play_type,
        "sample_count": sample_count,
        "hit_count": hit_count,
        "hit_rate": round(hit_rate, 6),
        "expected_hit_rate": round(expected_hit_rate, 6),
        "ev_bias": round(ev_bias, 6),
        "base_threshold": round(current_threshold, 2),
        "min_threshold": min_threshold,
        "blocked": blocked,
        "reason": ",".join(reasons),
    }


def calibrate_layered_filter_thresholds_now(
    *,
    limit: int = 500,
    min_samples: int = 8,
    weak_hit_rate: float = 0.42,
    weak_ev_bias: float = -0.08,
    block_hit_rate: float = 0.25,
    block_ev_bias: float = -0.16,
) -> dict:
    settlements = get_recent_settlements(limit=max(0, int(limit)))
    current_thresholds = _current_play_thresholds()
    records = _settlement_layered_play_records(settlements)
    global_play: dict[str, dict] = {}
    league_play: dict[str, dict[str, dict]] = {}

    by_play: dict[str, list[dict]] = defaultdict(list)
    by_league_play: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in records:
        play_type = normalize_text(row.get("play_type", ""))
        league = normalize_text(row.get("league", "")) or "-"
        if play_type not in DEFAULT_PLAY_THRESHOLDS:
            continue
        by_play[play_type].append(row)
        by_league_play[(league, play_type)].append(row)

    for play_type, rows in by_play.items():
        rule = _layered_gate_rule_from_rows(
            rows,
            play_type=play_type,
            base_threshold=_safe_float(current_thresholds.get(play_type), default=DEFAULT_PLAY_THRESHOLDS[play_type]),
            min_samples=max(12, int(min_samples) * 2),
            weak_hit_rate=weak_hit_rate,
            weak_ev_bias=weak_ev_bias,
            block_hit_rate=block_hit_rate,
            block_ev_bias=block_ev_bias,
        )
        if rule is not None:
            global_play[play_type] = rule

    for (league, play_type), rows in by_league_play.items():
        rule = _layered_gate_rule_from_rows(
            rows,
            play_type=play_type,
            base_threshold=_safe_float(current_thresholds.get(play_type), default=DEFAULT_PLAY_THRESHOLDS[play_type]),
            min_samples=int(min_samples),
            weak_hit_rate=weak_hit_rate,
            weak_ev_bias=weak_ev_bias,
            block_hit_rate=block_hit_rate,
            block_ev_bias=block_ev_bias,
        )
        if rule is None:
            continue
        rule["league"] = league
        league_play.setdefault(league, {})[play_type] = rule

    previous = get_play_threshold_status()
    report = {
        "updated_at": previous.get("updated_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": previous.get("mode", "layered_filter"),
        "thresholds": current_thresholds,
        "default_thresholds": previous.get("default_thresholds", dict(DEFAULT_PLAY_THRESHOLDS)),
        "metrics": previous.get("metrics", {}),
        "validation": previous.get("validation", {}),
        "layered_filter": {
            "enabled": True,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "settlement_layers",
            "sample_count": len(settlements),
            "record_count": len(records),
            "min_samples": int(min_samples),
            "weak_hit_rate": round(float(weak_hit_rate), 4),
            "weak_ev_bias": round(float(weak_ev_bias), 4),
            "block_hit_rate": round(float(block_hit_rate), 4),
            "block_ev_bias": round(float(block_ev_bias), 4),
            "global_play": global_play,
            "league_play": league_play,
        },
    }
    _save_play_threshold_report(report)
    return {
        "calibrated": True,
        "reason": "ok",
        "sample_count": len(settlements),
        "record_count": len(records),
        "global_rule_count": len(global_play),
        "league_rule_count": sum(len(item) for item in league_play.values()),
        "layered_filter": report["layered_filter"],
        "status": get_play_threshold_status(),
    }


def _settlement_strategy_records(settlements: list[dict]) -> list[dict]:
    specs = {
        "1x2": ("is_correct", "prediction_confidence", "predicted"),
        "handicap": ("handicap_is_correct", "handicap_confidence", "predicted_handicap"),
        "total_goals": ("total_goals_is_correct", "total_goals_confidence", "predicted_total_goals"),
        "ou": ("ou_is_correct", "ou_confidence", "predicted_ou"),
        "score": ("score_is_correct", "score_confidence", "predicted_score"),
    }
    records: list[dict] = []
    for item in settlements:
        if not isinstance(item, dict):
            continue
        fallback_confidence = _safe_float(item.get("prediction_confidence"), default=0.0)
        for play_type, (hit_key, confidence_key, pick_key) in specs.items():
            hit = item.get(hit_key)
            if not isinstance(hit, bool):
                continue
            confidence = _safe_float(item.get(confidence_key), default=0.0)
            if confidence <= 0.0 or confidence > 1.0:
                confidence = fallback_confidence
            if confidence <= 0.0 or confidence > 1.0:
                continue
            records.append(
                {
                    "match_id": str(item.get("match_id") or ""),
                    "match_date": normalize_text(item.get("match_date") or str(item.get("match_id") or "").split("|", 1)[0]),
                    "league": normalize_text(item.get("league", "")) or "-",
                    "rating_pool": normalize_text(item.get("rating_pool", "")) or "-",
                    "play_type": play_type,
                    "source_play_type": play_type,
                    "pick": normalize_text(item.get(pick_key, "")) or "-",
                    "confidence": round(_clamp(confidence), 4),
                    "is_hit": bool(hit),
                    "return_rate": round(_safe_float(item.get("return_rate"), default=0.0), 4),
                    "handicap_abs": round(abs(_safe_float(item.get("handicap_line"), default=0.0)), 2),
                    "sample_source": "settlement",
                }
            )
    return records


def _xgb_market_strategy_records(limit: int = 50000) -> list[dict]:
    label_to_result = {0: "主胜", 1: "平局", 2: "客胜"}
    key_to_result = {"home": "主胜", "draw": "平局", "away": "客胜"}
    records: list[dict] = []
    samples = STATE_STORE.load_xgb_samples()
    if limit > 0:
        samples = samples[-int(limit):]
    for item in samples:
        if not isinstance(item, dict):
            continue
        features = item.get("features", {}) if isinstance(item.get("features"), dict) else {}
        meta = item.get("meta", {}) if isinstance(item.get("meta"), dict) else {}
        try:
            label = int(item.get("label"))
        except Exception:
            continue
        if label not in label_to_result:
            continue
        probabilities = {
            "home": _safe_float(features.get("market_home"), default=0.0),
            "draw": _safe_float(features.get("market_draw"), default=0.0),
            "away": _safe_float(features.get("market_away"), default=0.0),
        }
        odds_by_side = {
            "home": _safe_float(features.get("odds_home"), default=0.0),
            "draw": _safe_float(features.get("odds_draw"), default=0.0),
            "away": _safe_float(features.get("odds_away"), default=0.0),
        }
        if max(probabilities.values()) <= 0.0:
            continue
        pick_key = max(probabilities, key=probabilities.get)
        confidence = round(_clamp(probabilities[pick_key]), 4)
        match_date = normalize_text(meta.get("match_date", ""))
        records.append(
            {
                "match_id": str(item.get("match_id") or ""),
                "match_date": match_date,
                "year": match_date[:4] if len(match_date) >= 4 else "-",
                "league": normalize_text(meta.get("league", "")) or "-",
                "rating_pool": "club",
                "play_type": "market_1x2",
                "source_play_type": "market_1x2",
                "pick": key_to_result.get(pick_key, "-"),
                "actual": label_to_result[label],
                "pick_side": pick_key,
                "confidence": confidence,
                "confidence_bucket": _confidence_bucket(confidence),
                "is_hit": key_to_result.get(pick_key) == label_to_result[label],
                "pick_odds": round(odds_by_side.get(pick_key, 0.0), 4),
                "odds_bucket": _odds_bucket(odds_by_side.get(pick_key, 0.0)),
                "return_rate": round(_safe_float(meta.get("return_rate"), default=_safe_float(features.get("return_rate"), default=0.0)), 4),
                "handicap_abs": round(abs(_safe_float(meta.get("handicap_line"), default=0.0)), 2),
                "home_team": normalize_text(meta.get("home_team", "")) or "-",
                "away_team": normalize_text(meta.get("away_team", "")) or "-",
                "sample_source": normalize_text(meta.get("source", "")) or "xgb_training_samples",
            }
        )
    return records


def _odds_bucket(value: float | int | str | None) -> str:
    odds = _safe_float(value, default=0.0)
    if odds <= 0.0:
        return "unknown"
    if odds <= 1.50:
        return "<=1.50"
    if odds <= 1.80:
        return "1.51-1.80"
    if odds <= 2.20:
        return "1.81-2.20"
    if odds <= 2.80:
        return "2.21-2.80"
    if odds <= 3.50:
        return "2.81-3.50"
    return ">3.50"


def _confidence_bucket(value: float | int | str | None) -> str:
    confidence = _safe_float(value, default=0.0)
    if confidence <= 0.0:
        return "unknown"
    if confidence < 0.38:
        return "<0.38"
    if confidence < 0.42:
        return "0.38-0.42"
    if confidence < 0.46:
        return "0.42-0.46"
    if confidence < 0.50:
        return "0.46-0.50"
    if confidence < 0.55:
        return "0.50-0.55"
    if confidence < 0.60:
        return "0.55-0.60"
    if confidence < 0.65:
        return "0.60-0.65"
    return ">=0.65"


def _wilson_lower_bound(hits: int, total: int, z: float = 1.28) -> float:
    if total <= 0:
        return 0.0
    phat = hits / total
    denominator = 1.0 + z * z / total
    centre = phat + z * z / (2.0 * total)
    margin = z * sqrt((phat * (1.0 - phat) + z * z / (4.0 * total)) / total)
    return max(0.0, (centre - margin) / denominator)


def _strategy_accuracy(rows: list[dict]) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if bool(row.get("is_hit"))) / len(rows)


def _strategy_stability_from_rows(rows: list[dict]) -> dict:
    ordered = sorted(enumerate(rows), key=lambda item: (normalize_text(item[1].get("match_date", "")), item[0]))
    selected = [item for _, item in ordered]
    total = len(selected)
    if total <= 0:
        return {
            "time_split_ready": False,
            "recent_ready": False,
            "stability_score": 0.0,
            "stable": False,
        }
    midpoint = total // 2
    first_half = selected[:midpoint]
    second_half = selected[midpoint:]
    recent_30 = selected[-30:] if total >= 30 else selected
    recent_90 = selected[-90:] if total >= 90 else selected
    first_accuracy = _strategy_accuracy(first_half) if first_half else _strategy_accuracy(selected)
    second_accuracy = _strategy_accuracy(second_half) if second_half else _strategy_accuracy(selected)
    recent_30_accuracy = _strategy_accuracy(recent_30)
    recent_90_accuracy = _strategy_accuracy(recent_90)
    overall_accuracy = _strategy_accuracy(selected)
    split_gap = abs(first_accuracy - second_accuracy)
    recent_gap = abs(overall_accuracy - recent_30_accuracy)
    worst_window = min(first_accuracy, second_accuracy, recent_30_accuracy, recent_90_accuracy)
    stable = bool(
        total >= 30
        and worst_window >= max(0.45, overall_accuracy - 0.12)
        and split_gap <= 0.18
        and recent_gap <= 0.16
    )
    stability_score = _clamp((worst_window * 0.65) + ((1.0 - min(split_gap, 0.35) / 0.35) * 0.2) + ((1.0 - min(recent_gap, 0.3) / 0.3) * 0.15))
    return {
        "time_split_ready": total >= 30,
        "recent_ready": total >= 30,
        "first_half_accuracy": round(first_accuracy, 6),
        "second_half_accuracy": round(second_accuracy, 6),
        "recent_30_accuracy": round(recent_30_accuracy, 6),
        "recent_90_accuracy": round(recent_90_accuracy, 6),
        "worst_window_accuracy": round(worst_window, 6),
        "split_gap": round(split_gap, 6),
        "recent_gap": round(recent_gap, 6),
        "stability_score": round(stability_score, 6),
        "stable": stable,
    }


def _strategy_layer_from_rows(*, scope: str, play_type: str, rows: list[dict]) -> dict:
    source_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        source_counts[normalize_text(row.get("sample_source", "")) or "unknown"] += 1
    dominant_source = max(source_counts, key=source_counts.get) if source_counts else "unknown"
    if play_type == "market_1x2":
        data_layer = "historical_market"
    elif dominant_source == "settlement":
        data_layer = "app_settlement"
    else:
        data_layer = dominant_source
    return {
        "data_layer": data_layer,
        "scope_layer": "league" if scope == "league" else "global",
        "play_layer": play_type,
        "sample_sources": dict(sorted(source_counts.items())),
    }


def _strategy_candidate_from_rows(
    rows: list[dict],
    *,
    scope: str,
    scope_value: str,
    play_type: str,
    min_confidence: float,
    total_records: int,
    min_samples: int,
    min_coverage: float,
) -> dict | None:
    selected = [
        row
        for row in rows
        if normalize_text(row.get("play_type", "")) == play_type
        and _safe_float(row.get("confidence"), default=0.0) >= min_confidence
    ]
    total = len(selected)
    if total < min_samples:
        return None
    coverage = total / max(total_records, 1)
    if coverage < min_coverage:
        return None
    hits = sum(1 for row in selected if bool(row.get("is_hit")))
    accuracy = hits / max(total, 1)
    avg_confidence = sum(_safe_float(row.get("confidence"), default=0.0) for row in selected) / max(total, 1)
    edge = accuracy - avg_confidence
    stability = _strategy_stability_from_rows(selected)
    layer = _strategy_layer_from_rows(scope=scope, play_type=play_type, rows=selected)
    return {
        "scope": scope,
        "scope_value": scope_value,
        "play_type": play_type,
        "layer": layer,
        "min_confidence": round(min_confidence, 2),
        "sample_count": total,
        "hit_count": hits,
        "accuracy": round(accuracy, 6),
        "coverage": round(coverage, 6),
        "avg_confidence": round(avg_confidence, 6),
        "edge": round(edge, 6),
        "wilson_lower": round(_wilson_lower_bound(hits, total), 6),
        "stability": stability,
    }


def _historical_strategy_record_dimension_values(record: dict) -> dict[str, str]:
    league = normalize_text(record.get("league", "")) or "-"
    year = normalize_text(record.get("year") or normalize_text(record.get("match_date", ""))[:4]) or "-"
    confidence_bucket = normalize_text(record.get("confidence_bucket") or _confidence_bucket(record.get("confidence"))) or "unknown"
    odds_bucket = normalize_text(record.get("odds_bucket") or _odds_bucket(record.get("pick_odds"))) or "unknown"
    pick_side = normalize_text(record.get("pick_side", "")) or "-"
    return {
        "global": "all",
        "year": year,
        "league": league,
        "odds_bucket": odds_bucket,
        "confidence_bucket": confidence_bucket,
        "pick_side": pick_side,
        "league_odds_bucket": f"{league} | {odds_bucket}",
        "league_confidence_bucket": f"{league} | {confidence_bucket}",
    }


def _historical_strategy_record_matches(strategy: dict, record: dict, *, min_confidence: float | None = None) -> bool:
    play_type = normalize_text(strategy.get("play_type", ""))
    if not play_type or normalize_text(record.get("play_type", "")) != play_type:
        return False
    record_confidence = _safe_float(record.get("confidence"), default=0.0)
    strategy_min_confidence = _safe_float(strategy.get("min_confidence"), default=1.0)
    if min_confidence is not None:
        strategy_min_confidence = max(strategy_min_confidence, _safe_float(min_confidence, default=strategy_min_confidence))
    if record_confidence < strategy_min_confidence:
        return False
    scope = normalize_text(strategy.get("scope", "global")) or "global"
    scope_value = normalize_text(strategy.get("scope_value", "all")) or "all"
    if scope == "global":
        return True
    if scope == "league":
        return scope_value == (normalize_text(record.get("league", "")) or "-")
    if scope == "jc_bucket":
        bucket = strategy.get("jc_bucket", {}) if isinstance(strategy.get("jc_bucket"), dict) else {}
        dimension = normalize_text(strategy.get("dimension") or bucket.get("dimension", ""))
        bucket_value = normalize_text(bucket.get("bucket") or scope_value)
        dimension_values = _historical_strategy_record_dimension_values(record)
        return bool(dimension and bucket_value and normalize_text(dimension_values.get(dimension, "")) == bucket_value)
    return False


def _historical_strategy_replay_item(strategy: dict, record: dict) -> dict:
    layer = strategy.get("layer", {}) if isinstance(strategy.get("layer"), dict) else {}
    actual = normalize_text(record.get("actual", ""))
    if not actual and record.get("is_hit") is True:
        actual = normalize_text(record.get("pick", ""))
    bucket = strategy.get("jc_bucket", {}) if isinstance(strategy.get("jc_bucket"), dict) else {}
    return {
        "role": strategy.get("effective_role") or strategy.get("role", "primary"),
        "original_role": strategy.get("original_role") or strategy.get("role", "primary"),
        "play_type": normalize_text(strategy.get("play_type", "")) or normalize_text(record.get("play_type", "")),
        "scope": normalize_text(strategy.get("scope", "global")) or "global",
        "scope_value": normalize_text(strategy.get("scope_value", "all")) or "all",
        "dimension": strategy.get("dimension") or bucket.get("dimension"),
        "data_layer": layer.get("data_layer", "-"),
        "layer": dict(layer),
        "pick": record.get("pick", "-"),
        "actual": actual or "-",
        "confidence": round(_safe_float(record.get("confidence"), default=0.0), 4),
        "min_confidence": round(_safe_float(strategy.get("min_confidence"), default=0.0), 2),
        "backtest_accuracy": strategy.get("accuracy", 0.0),
        "backtest_hits": strategy.get("hit_count", 0),
        "backtest_samples": strategy.get("sample_count", 0),
        "wilson_lower": strategy.get("wilson_lower", 0.0),
        "is_hit": bool(record.get("is_hit")),
        "is_shadow": False,
        "historical_replay": True,
        "sample_source": record.get("sample_source", "-"),
        "pick_side": record.get("pick_side", "-"),
        "pick_odds": record.get("pick_odds"),
        "odds_bucket": record.get("odds_bucket", "unknown"),
        "confidence_bucket": record.get("confidence_bucket", "unknown"),
        "jc_bucket": dict(bucket) if bucket else {},
        "jc_context": {
            "pick_odds": record.get("pick_odds"),
            "confidence_bucket": record.get("confidence_bucket", "unknown"),
            "odds_bucket": record.get("odds_bucket", "unknown"),
        },
    }


def build_historical_strategy_replay_samples(
    status: dict | None = None,
    *,
    historical_limit: int = 50000,
    max_samples: int = 1000,
    min_confidence: float | None = None,
) -> dict:
    resolved = status if isinstance(status, dict) else get_high_accuracy_strategy_status()
    strategy_pool = resolved.get("strategy_pool", []) if isinstance(resolved.get("strategy_pool"), list) else []
    if not strategy_pool and isinstance(resolved.get("strategy"), dict) and resolved.get("strategy"):
        strategy_pool = [resolved["strategy"]]
    strategies = [dict(item) for item in strategy_pool if isinstance(item, dict)]
    if not strategies:
        return {
            "ok": False,
            "reason": "no_strategy_pool",
            "sample_count": 0,
            "match_count": 0,
            "hit_count": 0,
            "miss_count": 0,
            "hit_rate": None,
            "hit_rate_text": "-",
            "settlements": [],
        }

    records = _xgb_market_strategy_records(limit=max(0, int(historical_limit)))
    sample_limit = max(0, int(max_samples))
    settlements: list[dict] = []
    matched_count = 0
    hit_count = 0
    miss_count = 0
    source_counts: dict[str, int] = defaultdict(int)
    strategy_counts: dict[str, int] = defaultdict(int)
    dates: list[str] = []
    for record in reversed(records):
        if sample_limit and matched_count >= sample_limit:
            break
        if not isinstance(record, dict):
            continue
        replay_items: list[dict] = []
        for strategy in strategies:
            if not _historical_strategy_record_matches(strategy, record, min_confidence=min_confidence):
                continue
            replay_items.append(_historical_strategy_replay_item(strategy, record))
            if sample_limit and matched_count + len(replay_items) >= sample_limit:
                break
        if not replay_items:
            continue
        if sample_limit:
            replay_items = replay_items[: max(0, sample_limit - matched_count)]
        if not replay_items:
            continue
        match_date = normalize_text(record.get("match_date", ""))
        if match_date:
            dates.append(match_date)
        for item in replay_items:
            matched_count += 1
            if item.get("is_hit") is True:
                hit_count += 1
            else:
                miss_count += 1
            source_counts[normalize_text(item.get("sample_source", "")) or "unknown"] += 1
            strategy_key = "|".join(
                [
                    normalize_text(item.get("scope", "")) or "global",
                    normalize_text(item.get("scope_value", "")) or "all",
                    normalize_text(item.get("play_type", "")) or "-",
                    normalize_text(item.get("data_layer", "")) or "-",
                    f"{_safe_float(item.get('min_confidence'), default=0.0):.2f}",
                ]
            )
            strategy_counts[strategy_key] += 1
        settlements.append(
            {
                "match_id": str(record.get("match_id") or ""),
                "match_date": match_date,
                "league": normalize_text(record.get("league", "")) or "-",
                "home_team": normalize_text(record.get("home_team", "")) or "-",
                "away_team": normalize_text(record.get("away_team", "")) or "-",
                "is_correct": bool(record.get("is_hit")),
                "historical_replay": True,
                "sample_source": record.get("sample_source", "-"),
                "high_accuracy_strategy_items": replay_items,
            }
        )

    hit_rate = hit_count / matched_count if matched_count else None
    return {
        "ok": bool(matched_count),
        "reason": "ok" if matched_count else "no_replay_match",
        "sample_count": matched_count,
        "match_count": len(settlements),
        "hit_count": hit_count,
        "miss_count": miss_count,
        "hit_rate": round(hit_rate, 6) if hit_rate is not None else None,
        "hit_rate_text": f"{hit_rate:.1%}" if hit_rate is not None else "-",
        "date_start": min(dates) if dates else None,
        "date_end": max(dates) if dates else None,
        "historical_limit": int(historical_limit),
        "max_samples": sample_limit,
        "source_counts": dict(sorted(source_counts.items())),
        "strategy_counts": dict(sorted(strategy_counts.items())),
        "settlements": settlements,
    }


def _write_high_accuracy_strategy_report(result: dict) -> str | None:
    if not result.get("ok"):
        return None
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"high_accuracy_strategy_backtest_{timestamp}.md"
    best = result.get("strategy", {}) if isinstance(result.get("strategy"), dict) else {}
    candidates = result.get("top_candidates", []) if isinstance(result.get("top_candidates"), list) else []
    validation = result.get("validation", {}) if isinstance(result.get("validation"), dict) else {}
    lines = [
        "# High Accuracy Strategy Backtest",
        "",
        f"- Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Settlement Samples: {validation.get('settlement_count', 0)}",
        f"- Strategy Records: {validation.get('record_count', 0)}",
        f"- Settlement Records: {validation.get('settlement_record_count', 0)}",
        f"- Historical Market Records: {validation.get('historical_record_count', 0)}",
        f"- Stable Candidates: {validation.get('stable_candidate_count', 0)} / {validation.get('candidate_count', 0)}",
        f"- Date Window: {validation.get('date_start') or '-'} -> {validation.get('date_end') or '-'}",
        "",
        "## Selected Strategy",
        "",
        f"- Play Type: {best.get('play_type', '-')}",
        f"- Scope: {best.get('scope', '-')} / {best.get('scope_value', '-')}",
        f"- Min Confidence: {float(best.get('min_confidence', 0) or 0):.2f}",
        f"- Backtest Accuracy: {float(best.get('accuracy', 0) or 0):.2%} ({int(best.get('hit_count', 0) or 0)}/{int(best.get('sample_count', 0) or 0)})",
        f"- Coverage: {float(best.get('coverage', 0) or 0):.2%}",
        f"- Wilson Lower: {float(best.get('wilson_lower', 0) or 0):.2%}",
        f"- Edge: {float(best.get('edge', 0) or 0):+.2%}",
        f"- Stability: {float((best.get('stability', {}) if isinstance(best.get('stability'), dict) else {}).get('stability_score', 0) or 0):.2%} | stable={bool((best.get('stability', {}) if isinstance(best.get('stability'), dict) else {}).get('stable', False))}",
        "",
        "## Strategy Pool",
        "",
        "| Role | Layer | Scope | Play | Min Conf | Hits | Total | Accuracy | Stable | Stability |",
        "|---|---|---|---|---:|---:|---:|---:|---|---:|",
    ]
    for item in result.get("strategy_pool", []) if isinstance(result.get("strategy_pool"), list) else []:
        layer = item.get("layer", {}) if isinstance(item.get("layer"), dict) else {}
        stability = item.get("stability", {}) if isinstance(item.get("stability"), dict) else {}
        lines.append(
            f"| {item.get('role', '-')} | {layer.get('data_layer', '-')} | {item.get('scope', '-')}/{item.get('scope_value', '-')} | {item.get('play_type', '-')} | "
            f"{float(item.get('min_confidence', 0) or 0):.2f} | {int(item.get('hit_count', 0) or 0)} | "
            f"{int(item.get('sample_count', 0) or 0)} | {float(item.get('accuracy', 0) or 0):.2%} | "
            f"{bool(stability.get('stable', False))} | {float(stability.get('stability_score', 0) or 0):.2%} |"
        )
    lines.extend([
        "",
        "## Top Candidates",
        "",
        "| Rank | Scope | Play | Min Conf | Hits | Total | Accuracy | Coverage | Wilson Lower | Edge | Stable |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ])
    for index, item in enumerate(candidates[:10], start=1):
        stability = item.get("stability", {}) if isinstance(item.get("stability"), dict) else {}
        lines.append(
            f"| {index} | {item.get('scope', '-')}/{item.get('scope_value', '-')} | {item.get('play_type', '-')} | "
            f"{float(item.get('min_confidence', 0) or 0):.2f} | {int(item.get('hit_count', 0) or 0)} | "
            f"{int(item.get('sample_count', 0) or 0)} | {float(item.get('accuracy', 0) or 0):.2%} | "
            f"{float(item.get('coverage', 0) or 0):.2%} | {float(item.get('wilson_lower', 0) or 0):.2%} | "
            f"{float(item.get('edge', 0) or 0):+.2%} | {bool(stability.get('stable', False))} |"
        )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return str(report_path)


def _jc_stratified_bucket(rows: list[dict], *, dimension: str, bucket: str, min_samples: int) -> dict | None:
    total = len(rows)
    if total < max(1, int(min_samples)):
        return None
    hits = sum(1 for row in rows if bool(row.get("is_hit")))
    accuracy = hits / max(total, 1)
    avg_confidence = sum(_safe_float(row.get("confidence"), default=0.0) for row in rows) / max(total, 1)
    avg_odds = sum(_safe_float(row.get("pick_odds"), default=0.0) for row in rows) / max(total, 1)
    stability = _strategy_stability_from_rows(rows)
    dates = [normalize_text(row.get("match_date", "")) for row in rows if normalize_text(row.get("match_date", ""))]
    source_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        source_counts[normalize_text(row.get("sample_source", "")) or "unknown"] += 1
    return {
        "dimension": dimension,
        "bucket": bucket,
        "sample_count": total,
        "hit_count": hits,
        "accuracy": round(accuracy, 6),
        "avg_confidence": round(avg_confidence, 6),
        "avg_pick_odds": round(avg_odds, 6),
        "edge": round(accuracy - avg_confidence, 6),
        "wilson_lower": round(_wilson_lower_bound(hits, total), 6),
        "date_start": min(dates) if dates else None,
        "date_end": max(dates) if dates else None,
        "stability": stability,
        "sample_sources": dict(sorted(source_counts.items())),
    }


def _jc_stratified_rank_key(item: dict) -> tuple[float, float, float, float, int]:
    stability = item.get("stability", {}) if isinstance(item.get("stability"), dict) else {}
    return (
        1.0 if bool(stability.get("stable", False)) else 0.0,
        float(item.get("wilson_lower", 0.0) or 0.0),
        float(item.get("accuracy", 0.0) or 0.0),
        float(stability.get("stability_score", 0.0) or 0.0),
        int(item.get("sample_count", 0) or 0),
    )


def _save_jc_stratified_strategy_report(report: dict) -> None:
    JC_STRATIFIED_STRATEGY_FILE.parent.mkdir(parents=True, exist_ok=True)
    JC_STRATIFIED_STRATEGY_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def get_jc_stratified_strategy_status() -> dict:
    if not JC_STRATIFIED_STRATEGY_FILE.exists():
        return {
            "enabled": False,
            "updated_at": None,
            "reason": "not_calibrated",
            "validation": {},
            "best_bucket": {},
            "top_buckets": [],
        }
    try:
        payload = json.loads(JC_STRATIFIED_STRATEGY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {
            "enabled": False,
            "updated_at": None,
            "reason": "invalid_report",
            "validation": {},
            "best_bucket": {},
            "top_buckets": [],
        }
    if not isinstance(payload, dict):
        payload = {}
    top_buckets = payload.get("top_buckets", [])
    if not isinstance(top_buckets, list):
        top_buckets = []
    return {
        "enabled": bool(payload.get("ok", False)),
        "updated_at": payload.get("updated_at"),
        "reason": payload.get("reason", "ok"),
        "validation": payload.get("validation", {}) if isinstance(payload.get("validation"), dict) else {},
        "best_bucket": payload.get("best_bucket", {}) if isinstance(payload.get("best_bucket"), dict) else {},
        "top_buckets": top_buckets,
        "report_path": payload.get("report_path"),
    }


def _write_jc_stratified_strategy_report(result: dict) -> str | None:
    if not result.get("ok"):
        return None
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"jc_stratified_strategy_backtest_{timestamp}.md"
    validation = result.get("validation", {}) if isinstance(result.get("validation"), dict) else {}
    best = result.get("best_bucket", {}) if isinstance(result.get("best_bucket"), dict) else {}
    rows = result.get("top_buckets", []) if isinstance(result.get("top_buckets"), list) else []
    lines = [
        "# JC Stratified Strategy Backtest",
        "",
        f"- Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Source: {validation.get('source', '-')}",
        f"- Records: {validation.get('record_count', 0)}",
        f"- Date Window: {validation.get('date_start') or '-'} -> {validation.get('date_end') or '-'}",
        f"- Min Samples: {validation.get('min_samples', 0)}",
        f"- Bucket Count: {validation.get('bucket_count', 0)}",
        f"- Stable Bucket Count: {validation.get('stable_bucket_count', 0)}",
        "",
        "## Best Bucket",
        "",
        f"- Dimension: {best.get('dimension', '-')}",
        f"- Bucket: {best.get('bucket', '-')}",
        f"- Accuracy: {float(best.get('accuracy', 0) or 0):.2%} ({int(best.get('hit_count', 0) or 0)}/{int(best.get('sample_count', 0) or 0)})",
        f"- Wilson Lower: {float(best.get('wilson_lower', 0) or 0):.2%}",
        f"- Avg Confidence: {float(best.get('avg_confidence', 0) or 0):.2%}",
        f"- Avg Pick Odds: {float(best.get('avg_pick_odds', 0) or 0):.2f}",
        f"- Edge: {float(best.get('edge', 0) or 0):+.2%}",
        f"- Stability: {float((best.get('stability', {}) if isinstance(best.get('stability'), dict) else {}).get('stability_score', 0) or 0):.2%}",
        "",
        "## Top Buckets",
        "",
        "| Rank | Dimension | Bucket | Hits | Total | Accuracy | Wilson | Avg Conf | Avg Odds | Stable | Stability |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for index, item in enumerate(rows[:30], start=1):
        stability = item.get("stability", {}) if isinstance(item.get("stability"), dict) else {}
        lines.append(
            f"| {index} | {item.get('dimension', '-')} | {item.get('bucket', '-')} | "
            f"{int(item.get('hit_count', 0) or 0)} | {int(item.get('sample_count', 0) or 0)} | "
            f"{float(item.get('accuracy', 0) or 0):.2%} | {float(item.get('wilson_lower', 0) or 0):.2%} | "
            f"{float(item.get('avg_confidence', 0) or 0):.2%} | {float(item.get('avg_pick_odds', 0) or 0):.2f} | "
            f"{bool(stability.get('stable', False))} | {float(stability.get('stability_score', 0) or 0):.2%} |"
        )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return str(report_path)


def run_jc_stratified_strategy_backtest(
    *,
    historical_limit: int = 50000,
    source: str = "jc_results_csv",
    min_samples: int = 120,
    write_report: bool = True,
) -> dict:
    records = [
        row
        for row in _xgb_market_strategy_records(limit=max(0, int(historical_limit)))
        if normalize_text(row.get("sample_source", "")) == source
    ]
    if not records:
        return {
            "ok": False,
            "reason": "no_jc_strategy_records",
            "validation": {"source": source, "record_count": 0},
            "best_bucket": {},
            "top_buckets": [],
        }

    dimensions: dict[str, Any] = {
        "global": lambda row: "all",
        "year": lambda row: normalize_text(row.get("year", "")) or "-",
        "league": lambda row: normalize_text(row.get("league", "")) or "-",
        "odds_bucket": lambda row: normalize_text(row.get("odds_bucket", "")) or "unknown",
        "confidence_bucket": lambda row: normalize_text(row.get("confidence_bucket", "")) or "unknown",
        "pick_side": lambda row: normalize_text(row.get("pick_side", "")) or "-",
        "league_odds_bucket": lambda row: f"{normalize_text(row.get('league', '')) or '-'} | {normalize_text(row.get('odds_bucket', '')) or 'unknown'}",
        "league_confidence_bucket": lambda row: f"{normalize_text(row.get('league', '')) or '-'} | {normalize_text(row.get('confidence_bucket', '')) or 'unknown'}",
    }
    buckets: list[dict] = []
    for dimension, key_fn in dimensions.items():
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in records:
            grouped[str(key_fn(row))].append(row)
        for bucket, rows in grouped.items():
            item = _jc_stratified_bucket(rows, dimension=dimension, bucket=bucket, min_samples=min_samples)
            if item is not None:
                buckets.append(item)

    if not buckets:
        return {
            "ok": False,
            "reason": "no_bucket_passed_constraints",
            "validation": {"source": source, "record_count": len(records), "min_samples": int(min_samples)},
            "best_bucket": {},
            "top_buckets": [],
        }

    buckets = sorted(buckets, key=_jc_stratified_rank_key, reverse=True)
    dates = [normalize_text(row.get("match_date", "")) for row in records if normalize_text(row.get("match_date", ""))]
    source_counts: dict[str, int] = defaultdict(int)
    for row in records:
        source_counts[normalize_text(row.get("sample_source", "")) or "unknown"] += 1
    stable_count = sum(1 for item in buckets if bool((item.get("stability", {}) if isinstance(item.get("stability"), dict) else {}).get("stable", False)))
    validation = {
        "source": source,
        "record_count": len(records),
        "min_samples": int(min_samples),
        "historical_limit": int(historical_limit),
        "bucket_count": len(buckets),
        "stable_bucket_count": stable_count,
        "date_start": min(dates) if dates else None,
        "date_end": max(dates) if dates else None,
        "source_counts": dict(sorted(source_counts.items())),
    }
    result = {
        "ok": True,
        "reason": "ok",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "validation": validation,
        "best_bucket": buckets[0],
        "top_buckets": buckets[:30],
    }
    result["report_path"] = _write_jc_stratified_strategy_report(result) if write_report else None
    _save_jc_stratified_strategy_report(result)
    return result


def _save_high_accuracy_strategy_report(report: dict) -> None:
    HIGH_ACCURACY_STRATEGY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HIGH_ACCURACY_STRATEGY_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _strategy_admission_policy_mtime() -> float | None:
    try:
        return STRATEGY_ADMISSION_POLICY_FILE.stat().st_mtime
    except OSError:
        return None


def _normalize_strategy_admission_policy(policy: dict | None) -> dict:
    resolved = dict(DEFAULT_STRATEGY_ADMISSION_POLICY)
    if isinstance(policy, dict):
        resolved.update(policy)
    resolved["min_confidence"] = round(
        _clamp(_safe_float(resolved.get("min_confidence"), STRATEGY_ADMISSION_MIN_CONFIDENCE), 0.45, 0.78),
        2,
    )
    resolved["block_confidence"] = round(
        _clamp(
            _safe_float(resolved.get("block_confidence"), STRATEGY_ADMISSION_BLOCK_CONFIDENCE),
            0.25,
            min(0.65, resolved["min_confidence"]),
        ),
        2,
    )
    resolved["active_strategy_min"] = max(1, min(3, int(_safe_int(resolved.get("active_strategy_min"), 1) or 1)))
    resolved["medium_risk_allowed"] = bool(resolved.get("medium_risk_allowed", True))
    resolved["high_risk_allowed"] = bool(resolved.get("high_risk_allowed", False))
    resolved["agent_replay_guard_enabled"] = bool(resolved.get("agent_replay_guard_enabled", True))
    resolved["agent_replay_min_samples"] = max(
        3,
        min(20, int(_safe_int(resolved.get("agent_replay_min_samples"), 5) or 5)),
    )
    resolved["agent_replay_prediction_miss_threshold"] = round(
        _clamp(_safe_float(resolved.get("agent_replay_prediction_miss_threshold"), 0.55), 0.45, 0.80),
        2,
    )
    resolved["agent_replay_handicap_miss_threshold"] = round(
        _clamp(_safe_float(resolved.get("agent_replay_handicap_miss_threshold"), 0.60), 0.45, 0.85),
        2,
    )
    return resolved


def _load_strategy_admission_policy_report() -> dict:
    mtime = _strategy_admission_policy_mtime()
    if _STRATEGY_ADMISSION_POLICY_CACHE.get("mtime") == mtime:
        cached = _STRATEGY_ADMISSION_POLICY_CACHE.get("report")
        if isinstance(cached, dict) and cached:
            return dict(cached)
    if not STRATEGY_ADMISSION_POLICY_FILE.exists():
        report = {
            "mode": "default",
            "updated_at": "-",
            "policy": dict(DEFAULT_STRATEGY_ADMISSION_POLICY),
            "reason": "default_policy",
        }
    else:
        try:
            report = json.loads(STRATEGY_ADMISSION_POLICY_FILE.read_text(encoding="utf-8"))
        except Exception:
            report = {
                "mode": "default",
                "updated_at": "-",
                "policy": dict(DEFAULT_STRATEGY_ADMISSION_POLICY),
                "reason": "read_failed",
            }
    if not isinstance(report, dict):
        report = {"mode": "default", "updated_at": "-", "policy": dict(DEFAULT_STRATEGY_ADMISSION_POLICY)}
    report["enabled"] = bool(report.get("enabled", True))
    report["active"] = bool(report["enabled"])
    report["status"] = "active" if report["enabled"] else "disabled"
    reason_text = normalize_text(report.get("reason", ""))
    if not reason_text or reason_text == "-":
        report["reason"] = "default_policy" if normalize_text(report.get("mode", "")) == "default" else "ok"
    report["policy"] = _normalize_strategy_admission_policy(report.get("policy") if isinstance(report.get("policy"), dict) else {})
    _STRATEGY_ADMISSION_POLICY_CACHE["mtime"] = mtime
    _STRATEGY_ADMISSION_POLICY_CACHE["policy"] = dict(report["policy"])
    _STRATEGY_ADMISSION_POLICY_CACHE["report"] = dict(report)
    return report


def get_strategy_admission_policy_status() -> dict:
    report = _load_strategy_admission_policy_report()
    enabled = bool(report.get("enabled", True))
    return {
        "enabled": enabled,
        "active": bool(enabled),
        "status": str(report.get("status") or ("active" if enabled else "disabled")),
        "mode": report.get("mode", "default"),
        "updated_at": report.get("updated_at", "-"),
        "version_id": report.get("version_id", "-"),
        "reason": report.get("reason", "-"),
        "policy": _normalize_strategy_admission_policy(report.get("policy") if isinstance(report.get("policy"), dict) else {}),
        "source": str(STRATEGY_ADMISSION_POLICY_FILE),
        "history_source": str(STRATEGY_ADMISSION_POLICY_HISTORY_FILE),
    }


def _current_strategy_admission_policy() -> dict:
    return get_strategy_admission_policy_status().get("policy", dict(DEFAULT_STRATEGY_ADMISSION_POLICY))


def _load_strategy_admission_policy_history_entries() -> list[dict]:
    if not STRATEGY_ADMISSION_POLICY_HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(STRATEGY_ADMISSION_POLICY_HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items if isinstance(item, dict)]


def _write_strategy_admission_policy_history_entries(items: list[dict]) -> None:
    STRATEGY_ADMISSION_POLICY_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": items[-200:],
    }
    STRATEGY_ADMISSION_POLICY_HISTORY_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_strategy_admission_policy_history(*, limit: int = 20) -> list[dict]:
    items = _load_strategy_admission_policy_history_entries()
    items.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("version_id") or "")), reverse=True)
    if limit <= 0:
        return items
    return items[: max(0, int(limit))]


def apply_strategy_admission_policy_update(update: dict, *, source: str = "manual") -> dict:
    current = get_strategy_admission_policy_status()
    policy = dict(current.get("policy") if isinstance(current.get("policy"), dict) else DEFAULT_STRATEGY_ADMISSION_POLICY)
    if isinstance(update, dict):
        policy.update(update)
    normalized = _normalize_strategy_admission_policy(policy)
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history_items = _load_strategy_admission_policy_history_entries()
    version_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(history_items) + 1:04d}"
    report = {
        "enabled": True,
        "active": True,
        "status": "active",
        "mode": "manual",
        "updated_at": updated_at,
        "version_id": version_id,
        "reason": str(source or "manual"),
        "policy": normalized,
        "previous_policy": current.get("policy", {}),
    }
    STRATEGY_ADMISSION_POLICY_FILE.parent.mkdir(parents=True, exist_ok=True)
    STRATEGY_ADMISSION_POLICY_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    history_items.append(
        {
            "version_id": version_id,
            "updated_at": updated_at,
            "source": str(source or "manual"),
            "policy": normalized,
            "previous_policy": current.get("policy", {}),
            "update": dict(update) if isinstance(update, dict) else {},
        }
    )
    _write_strategy_admission_policy_history_entries(history_items)
    _STRATEGY_ADMISSION_POLICY_CACHE["mtime"] = _strategy_admission_policy_mtime()
    _STRATEGY_ADMISSION_POLICY_CACHE["policy"] = dict(normalized)
    _STRATEGY_ADMISSION_POLICY_CACHE["report"] = dict(report)
    return get_strategy_admission_policy_status()


def rollback_strategy_admission_policy(*, version_id: str | None = None, source: str = "policy_rollback") -> dict:
    history_items = get_strategy_admission_policy_history(limit=0)
    if not history_items:
        return get_strategy_admission_policy_status()
    target: dict | None = None
    rollback_source = str(source or "policy_rollback")
    if version_id:
        target_entry = next((item for item in history_items if str(item.get("version_id") or "") == str(version_id)), None)
        if isinstance(target_entry, dict):
            policy = target_entry.get("policy")
            if isinstance(policy, dict):
                target = dict(policy)
                rollback_source = f"{rollback_source}:{version_id}"
    else:
        latest = history_items[0]
        previous = latest.get("previous_policy")
        if isinstance(previous, dict):
            target = dict(previous)
            rollback_source = f"{rollback_source}:{latest.get('version_id', '-')}"
    if not target:
        return get_strategy_admission_policy_status()
    return apply_strategy_admission_policy_update(target, source=rollback_source)


def _high_accuracy_strategy_identity(item: dict) -> tuple[str, str, str, str, str]:
    layer = item.get("layer", {}) if isinstance(item.get("layer"), dict) else {}
    data_layer = normalize_text(item.get("data_layer") or layer.get("data_layer") or "-")
    return (
        normalize_text(item.get("scope") or "global"),
        normalize_text(item.get("scope_value") or "all"),
        normalize_text(item.get("play_type") or "-"),
        data_layer,
        f"{_safe_float(item.get('min_confidence'), default=0.0):.2f}",
    )


def _high_accuracy_strategy_breaker_for_item(
    strategy: dict,
    settlements: list[dict],
    *,
    threshold: int = HIGH_ACCURACY_STRATEGY_BREAKER_THRESHOLD,
    window: int = HIGH_ACCURACY_STRATEGY_BREAKER_WINDOW,
    recovery_hits: int = HIGH_ACCURACY_STRATEGY_RECOVERY_HITS,
) -> dict:
    strategy_key = _high_accuracy_strategy_identity(strategy)
    results: list[bool] = []
    for settlement in reversed(settlements):
        if not isinstance(settlement, dict):
            continue
        items = settlement.get("high_accuracy_strategy_items", [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            if _high_accuracy_strategy_identity(item) != strategy_key:
                continue
            hit = item.get("is_hit")
            if hit is None:
                continue
            results.append(bool(hit))
            if len(results) >= max(1, int(window)):
                break
        if len(results) >= max(1, int(window)):
            break

    miss_streak = 0
    for hit in results:
        if hit:
            break
        miss_streak += 1
    recovery_streak = 0
    for hit in results:
        if not hit:
            break
        recovery_streak += 1
    prior_miss_streak = 0
    for hit in results[recovery_streak:]:
        if hit:
            break
        prior_miss_streak += 1

    threshold_value = max(1, int(threshold))
    recovery_value = max(1, int(recovery_hits))
    known_count = len(results)
    hit_count = sum(1 for hit in results if hit)
    miss_count = known_count - hit_count
    breaker_on = bool(
        known_count >= threshold_value
        and (
            miss_streak >= threshold_value
            or (prior_miss_streak >= threshold_value and recovery_streak < recovery_value)
        )
    )
    status_text = "pending"
    if breaker_on and recovery_streak > 0:
        status_text = "recovering"
    elif breaker_on:
        status_text = "paused"
    elif known_count:
        status_text = "recovered" if prior_miss_streak >= threshold_value and recovery_streak >= recovery_value else "active"
    recent_hit_rate = hit_count / known_count if known_count else None
    return {
        "strategy_key": "|".join(strategy_key),
        "status": status_text,
        "breaker_on": breaker_on,
        "threshold": threshold_value,
        "window": max(1, int(window)),
        "recovery_hits_required": recovery_value,
        "known_count": known_count,
        "hit_count": hit_count,
        "miss_count": miss_count,
        "miss_streak": miss_streak,
        "recovery_streak": recovery_streak,
        "prior_miss_streak": prior_miss_streak,
        "recent_hit_rate": round(recent_hit_rate, 4) if recent_hit_rate is not None else None,
    }


def _jc_bucket_key_from_parts(dimension: object, bucket: object) -> str:
    dimension_text = normalize_text(dimension)
    bucket_text = normalize_text(bucket)
    if not dimension_text or not bucket_text:
        return ""
    return f"{dimension_text}|{bucket_text}"


def _jc_bucket_key(item: dict) -> str:
    if not isinstance(item, dict):
        return ""
    explicit = normalize_text(item.get("jc_bucket_key"))
    if explicit:
        return explicit
    bucket = item.get("jc_bucket", {}) if isinstance(item.get("jc_bucket"), dict) else {}
    return _jc_bucket_key_from_parts(
        bucket.get("dimension") or item.get("dimension"),
        bucket.get("bucket") or item.get("scope_value"),
    )


def _jc_bucket_metadata(item: dict) -> dict:
    bucket = item.get("jc_bucket", {}) if isinstance(item.get("jc_bucket"), dict) else {}
    stability = bucket.get("stability", {}) if isinstance(bucket.get("stability"), dict) else {}
    if not stability and isinstance(item.get("stability"), dict):
        stability = item.get("stability", {})
    dimension = bucket.get("dimension") or item.get("dimension")
    bucket_value = bucket.get("bucket") or item.get("scope_value")
    metadata = {
        "dimension": dimension or "-",
        "bucket": bucket_value or "-",
        "accuracy": bucket.get("accuracy", item.get("accuracy", item.get("backtest_accuracy", 0.0))),
        "hit_count": bucket.get("hit_count", item.get("hit_count", item.get("backtest_hits", 0))),
        "sample_count": bucket.get("sample_count", item.get("sample_count", item.get("backtest_samples", 0))),
        "wilson_lower": bucket.get("wilson_lower", item.get("wilson_lower", 0.0)),
        "avg_confidence": bucket.get("avg_confidence", item.get("avg_confidence")),
        "avg_pick_odds": bucket.get("avg_pick_odds", item.get("avg_pick_odds")),
        "stability": dict(stability) if isinstance(stability, dict) else {},
    }
    return metadata


def build_jc_bucket_live_feedback(
    settlements: list[dict] | None = None,
    *,
    limit: int = JC_BUCKET_LIVE_FEEDBACK_WINDOW,
) -> dict[str, dict]:
    use_cache = settlements is None
    cache_key = _recent_settlements_signature(max(0, int(limit))) if use_cache else None
    if use_cache and cache_key is not None and _JC_BUCKET_LIVE_FEEDBACK_CACHE.get("cache_key") == cache_key:
        cached_feedback = _JC_BUCKET_LIVE_FEEDBACK_CACHE.get("feedback")
        if isinstance(cached_feedback, dict):
            return {str(key): dict(value) for key, value in cached_feedback.items() if isinstance(value, dict)}
    if settlements is None:
        try:
            settlements = get_recent_settlements(limit=max(0, int(limit)))
        except Exception:
            settlements = []
    rows_by_key: dict[str, list[dict]] = defaultdict(list)
    metadata_by_key: dict[str, dict] = {}
    for settlement in settlements if isinstance(settlements, list) else []:
        if not isinstance(settlement, dict):
            continue
        items = settlement.get("high_accuracy_strategy_items", [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            layer = item.get("layer", {}) if isinstance(item.get("layer"), dict) else {}
            data_layer = normalize_text(item.get("data_layer") or layer.get("data_layer") or "")
            if data_layer != "jc_stratified_market" and not isinstance(item.get("jc_bucket"), dict):
                continue
            hit = item.get("is_hit")
            if hit is None:
                continue
            key = _jc_bucket_key(item)
            if not key:
                continue
            metadata_by_key[key] = _jc_bucket_metadata(item)
            rows_by_key[key].append(
                {
                    "is_hit": bool(hit),
                    "is_shadow": bool(item.get("is_shadow")),
                    "settled_at": settlement.get("settled_at") or settlement.get("created_at") or settlement.get("match_date"),
                    "match_id": settlement.get("match_id"),
                }
            )

    feedback: dict[str, dict] = {}
    for key, rows in rows_by_key.items():
        known_count = len(rows)
        hit_count = sum(1 for row in rows if row.get("is_hit"))
        live_hit_rate = hit_count / known_count if known_count else None
        recent_10 = rows[-10:]
        recent_30 = rows[-30:]
        recent_10_hit_rate = sum(1 for row in recent_10 if row.get("is_hit")) / len(recent_10) if recent_10 else None
        recent_30_hit_rate = sum(1 for row in recent_30 if row.get("is_hit")) / len(recent_30) if recent_30 else None
        miss_streak = 0
        for row in reversed(rows):
            if row.get("is_hit"):
                break
            miss_streak += 1
        recovery_streak = 0
        for row in reversed(rows):
            if not row.get("is_hit"):
                break
            recovery_streak += 1
        metadata = metadata_by_key.get(key, {})
        historical_accuracy = _safe_float(metadata.get("accuracy"), default=0.0)
        wilson_lower = _safe_float(metadata.get("wilson_lower"), default=0.0)
        downgrade_floor = max(0.45, wilson_lower - 0.10)
        watch_floor = max(0.45, wilson_lower - 0.05)
        recovery_required = max(1, int(JC_BUCKET_RECOVERY_REQUIRED_HITS))
        recovery_recent_ok = bool(recent_10_hit_rate is not None and recent_10_hit_rate >= watch_floor)
        recovery_eligible = bool(recovery_streak >= recovery_required and recovery_recent_ok)
        status = "pending"
        reason = "insufficient_live_samples"
        if known_count >= JC_BUCKET_LIVE_DOWNGRADE_SAMPLES and live_hit_rate is not None and live_hit_rate < downgrade_floor:
            if recovery_eligible:
                status = "watch"
                reason = "shadow_recovery_progress"
            else:
                status = "downgraded"
                reason = "live_rate_below_historical_floor"
        elif known_count >= JC_BUCKET_LIVE_PENDING_SAMPLES:
            if miss_streak >= 3:
                status = "watch"
                reason = "live_miss_streak"
            elif recent_10_hit_rate is not None and recent_10_hit_rate < watch_floor:
                status = "watch"
                reason = "recent_10_below_historical_floor"
            elif live_hit_rate is not None and live_hit_rate < max(0.50, wilson_lower - 0.08):
                status = "watch"
                reason = "live_rate_soft_gap"
            else:
                status = "healthy"
                reason = "live_rate_ok"
        recovery_status = "not_needed"
        if status == "healthy":
            recovery_status = "recovered"
        elif status in {"watch", "downgraded"}:
            if recovery_eligible:
                recovery_status = "eligible"
            elif recovery_streak > 0:
                recovery_status = "in_progress"
            else:
                recovery_status = "blocked"
        deviation = live_hit_rate - historical_accuracy if live_hit_rate is not None else None
        feedback[key] = {
            "jc_bucket_key": key,
            "dimension": metadata.get("dimension", "-"),
            "bucket": metadata.get("bucket", "-"),
            "status": status,
            "reason": reason,
            "live_count": known_count,
            "live_hit_count": hit_count,
            "live_hit_rate": round(live_hit_rate, 4) if live_hit_rate is not None else None,
            "recent_10_hit_rate": round(recent_10_hit_rate, 4) if recent_10_hit_rate is not None else None,
            "recent_30_hit_rate": round(recent_30_hit_rate, 4) if recent_30_hit_rate is not None else None,
            "miss_streak": miss_streak,
            "recovery_streak": recovery_streak,
            "recovery_hits_required": recovery_required,
            "recovery_status": recovery_status,
            "recovery_eligible": recovery_eligible,
            "historical_accuracy": round(historical_accuracy, 4),
            "historical_wilson_lower": round(wilson_lower, 4),
            "deviation": round(deviation, 4) if deviation is not None else None,
            "official_count": sum(1 for row in rows if not row.get("is_shadow")),
            "shadow_count": sum(1 for row in rows if row.get("is_shadow")),
        }
    if use_cache and cache_key is not None:
        _JC_BUCKET_LIVE_FEEDBACK_CACHE["cache_key"] = cache_key
        _JC_BUCKET_LIVE_FEEDBACK_CACHE["feedback"] = {
            str(key): dict(value) for key, value in feedback.items() if isinstance(value, dict)
        }
    return feedback


def build_jc_strategy_auto_calibration(
    status: dict | None = None,
    live_feedback: dict[str, dict] | None = None,
) -> dict:
    if status is None:
        status = get_jc_stratified_strategy_status()
    if live_feedback is None:
        live_feedback = build_jc_bucket_live_feedback(limit=JC_BUCKET_LIVE_FEEDBACK_WINDOW)
    top_buckets = status.get("top_buckets", []) if isinstance(status, dict) and isinstance(status.get("top_buckets"), list) else []
    top_bucket_keys = {
        _jc_bucket_key_from_parts(bucket.get("dimension"), bucket.get("bucket"))
        for bucket in top_buckets
        if isinstance(bucket, dict)
    }
    top_bucket_keys.discard("")
    stable_buckets = [
        bucket
        for bucket in top_buckets
        if isinstance(bucket, dict)
        and bool((bucket.get("stability", {}) if isinstance(bucket.get("stability"), dict) else {}).get("stable", False))
    ]
    known_feedback = [
        item
        for key, item in (live_feedback or {}).items()
        if isinstance(item, dict) and int(_safe_int(item.get("live_count"), 0) or 0) >= JC_BUCKET_LIVE_PENDING_SAMPLES
        and (not top_bucket_keys or str(key) in top_bucket_keys)
    ]
    status_counts: dict[str, int] = defaultdict(int)
    deviations: list[float] = []
    for item in known_feedback:
        status_counts[normalize_text(item.get("status", "pending")) or "pending"] += 1
        if item.get("deviation") is not None:
            deviations.append(_safe_float(item.get("deviation"), default=0.0))
    live_bucket_count = len(known_feedback)
    downgraded_count = int(status_counts.get("downgraded", 0))
    watch_count = int(status_counts.get("watch", 0))
    avg_deviation = sum(deviations) / len(deviations) if deviations else 0.0

    thresholds = {
        "min_samples": JC_STRATIFIED_MIN_RUNTIME_SAMPLES,
        "min_accuracy": JC_STRATIFIED_MIN_RUNTIME_ACCURACY,
        "min_wilson": JC_STRATIFIED_MIN_RUNTIME_WILSON,
        "min_stability_score": JC_STRATIFIED_MIN_STABILITY_SCORE,
        "observe_live_statuses": ["downgraded"],
    }
    mode = "base"
    reason = "default_runtime_thresholds"
    if len(stable_buckets) < 3:
        mode = "cautious"
        reason = "few_stable_historical_buckets"
    if live_bucket_count >= JC_STRATEGY_CALIBRATION_MIN_LIVE_BUCKETS:
        downgrade_rate = downgraded_count / live_bucket_count if live_bucket_count else 0.0
        watch_rate = (watch_count + downgraded_count) / live_bucket_count if live_bucket_count else 0.0
        if downgraded_count >= 2 or downgrade_rate >= 0.25 or avg_deviation <= -0.12:
            mode = "strict"
            reason = "live_feedback_underperforming"
        elif downgraded_count >= 1 or watch_rate >= 0.50 or avg_deviation <= -0.07:
            mode = "cautious"
            reason = "live_feedback_soft_gap"

    if mode == "cautious":
        thresholds.update(
            {
                "min_samples": max(thresholds["min_samples"], 160),
                "min_accuracy": max(thresholds["min_accuracy"], 0.70),
                "min_wilson": max(thresholds["min_wilson"], 0.66),
                "min_stability_score": max(thresholds["min_stability_score"], 0.65),
            }
        )
    elif mode == "strict":
        thresholds.update(
            {
                "min_samples": max(thresholds["min_samples"], 220),
                "min_accuracy": max(thresholds["min_accuracy"], 0.72),
                "min_wilson": max(thresholds["min_wilson"], 0.68),
                "min_stability_score": max(thresholds["min_stability_score"], 0.70),
                "observe_live_statuses": ["watch", "downgraded"],
            }
        )

    return {
        "enabled": True,
        "mode": mode,
        "reason": reason,
        "thresholds": thresholds,
        "stable_bucket_count": len(stable_buckets),
        "live_bucket_count": live_bucket_count,
        "status_counts": dict(sorted(status_counts.items())),
        "avg_deviation": round(avg_deviation, 4),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _apply_high_accuracy_strategy_breakers(status: dict, settlements: list[dict] | None = None) -> dict:
    resolved = dict(status)
    strategy = resolved.get("strategy", {}) if isinstance(resolved.get("strategy"), dict) else {}
    pool = resolved.get("strategy_pool", []) if isinstance(resolved.get("strategy_pool"), list) else []
    if not pool and strategy:
        pool = [{**strategy, "role": "primary"}]
    settlement_items = settlements if isinstance(settlements, list) else []

    augmented_pool: list[dict] = []
    paused_count = 0
    live_feedback_active_count = 0
    pending_count = 0
    recovering_count = 0
    recovered_count = 0
    for item in pool:
        if not isinstance(item, dict):
            continue
        augmented = dict(item)
        breaker = _high_accuracy_strategy_breaker_for_item(augmented, settlement_items)
        original_role = normalize_text(augmented.get("role") or "observe")
        effective_role = "observe" if breaker.get("breaker_on") and original_role in {"primary", "backup"} else original_role
        augmented["original_role"] = original_role
        augmented["effective_role"] = effective_role
        augmented["breaker"] = breaker
        if breaker.get("breaker_on"):
            paused_count += 1
            if str(breaker.get("status") or "") == "recovering":
                recovering_count += 1
        elif int(breaker.get("known_count", 0) or 0) <= 0:
            pending_count += 1
        else:
            live_feedback_active_count += 1
            if str(breaker.get("status") or "") == "recovered":
                recovered_count += 1
        augmented_pool.append(augmented)

    strategy_count = len(augmented_pool)
    enabled = bool(resolved.get("enabled"))
    runtime_active_count = max(0, strategy_count - paused_count) if enabled else 0
    if not enabled:
        breaker_status = "disabled"
        recovery_status = "disabled"
    elif strategy_count <= 0:
        breaker_status = "empty"
        recovery_status = "not_needed"
    elif recovering_count:
        breaker_status = "recovering"
        recovery_status = "in_progress"
    elif paused_count >= strategy_count:
        breaker_status = "paused"
        recovery_status = "blocked"
    elif paused_count:
        breaker_status = "partial_paused"
        recovery_status = "in_progress" if recovering_count else "watch"
    elif live_feedback_active_count:
        breaker_status = "active"
        recovery_status = "recovered" if recovered_count else "not_needed"
    elif pending_count:
        breaker_status = "pending_live_feedback"
        recovery_status = "pending_live_feedback"
    else:
        breaker_status = "active"
        recovery_status = "not_needed"

    if strategy:
        strategy_key = _high_accuracy_strategy_identity(strategy)
        resolved["strategy"] = next(
            (dict(item) for item in augmented_pool if _high_accuracy_strategy_identity(item) == strategy_key),
            dict(strategy),
        )
    resolved["strategy_pool"] = augmented_pool
    resolved["breaker"] = {
        "threshold": HIGH_ACCURACY_STRATEGY_BREAKER_THRESHOLD,
        "window": HIGH_ACCURACY_STRATEGY_BREAKER_WINDOW,
        "strategy_count": strategy_count,
        "active_count": live_feedback_active_count,
        "runtime_active_count": runtime_active_count,
        "pending_count": pending_count,
        "paused_count": paused_count,
        "recovering_count": recovering_count,
        "recovered_count": recovered_count,
        "breaker_on": paused_count > 0,
        "status": breaker_status,
        "recovery_status": recovery_status,
    }
    resolved["active"] = bool(enabled and runtime_active_count > 0)
    resolved["status"] = "active" if resolved["active"] else breaker_status
    resolved["strategy_count"] = strategy_count
    resolved["runtime_active_count"] = runtime_active_count
    resolved["live_feedback_active_count"] = live_feedback_active_count
    resolved["live_feedback_pending_count"] = pending_count
    resolved["paused_count"] = paused_count
    resolved["breaker_status"] = breaker_status
    resolved["breaker_on"] = bool(paused_count > 0)
    resolved["recovery_status"] = recovery_status
    return resolved


def _empty_high_accuracy_strategy_status(reason: str, *, updated_at: object = None) -> dict:
    return {
        "enabled": False,
        "active": False,
        "status": "disabled",
        "updated_at": updated_at,
        "strategy": {},
        "strategy_pool": [],
        "validation": {},
        "top_candidates": [],
        "reason": reason,
        "strategy_count": 0,
        "runtime_active_count": 0,
        "live_feedback_active_count": 0,
        "live_feedback_pending_count": 0,
        "paused_count": 0,
        "breaker_status": "disabled",
        "breaker_on": False,
        "recovery_status": "disabled",
        "breaker": {
            "threshold": HIGH_ACCURACY_STRATEGY_BREAKER_THRESHOLD,
            "window": HIGH_ACCURACY_STRATEGY_BREAKER_WINDOW,
            "strategy_count": 0,
            "active_count": 0,
            "runtime_active_count": 0,
            "pending_count": 0,
            "paused_count": 0,
            "recovering_count": 0,
            "recovered_count": 0,
            "breaker_on": False,
            "status": "disabled",
            "recovery_status": "disabled",
        },
    }


def get_high_accuracy_strategy_status() -> dict:
    recent_signature = _recent_settlements_signature(HIGH_ACCURACY_STRATEGY_BREAKER_WINDOW * 4)
    cache_key = (
        _path_signature(HIGH_ACCURACY_STRATEGY_FILE),
        recent_signature,
    ) if recent_signature is not None else None
    if cache_key is not None and _HIGH_ACCURACY_STRATEGY_STATUS_CACHE.get("cache_key") == cache_key:
        cached_status = _HIGH_ACCURACY_STRATEGY_STATUS_CACHE.get("status")
        if isinstance(cached_status, dict):
            return dict(cached_status)
    if not HIGH_ACCURACY_STRATEGY_FILE.exists():
        return _empty_high_accuracy_strategy_status("not_calibrated")
    try:
        payload = json.loads(HIGH_ACCURACY_STRATEGY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return _empty_high_accuracy_strategy_status("invalid_report")
    if not isinstance(payload, dict):
        payload = {}
    status = {
        "enabled": bool(payload.get("enabled", False)),
        "updated_at": payload.get("updated_at"),
        "strategy": payload.get("strategy", {}) if isinstance(payload.get("strategy"), dict) else {},
        "strategy_pool": payload.get("strategy_pool", []) if isinstance(payload.get("strategy_pool"), list) else [],
        "validation": payload.get("validation", {}) if isinstance(payload.get("validation"), dict) else {},
        "top_candidates": payload.get("top_candidates", []) if isinstance(payload.get("top_candidates"), list) else [],
        "reason": payload.get("reason", "ok"),
    }
    try:
        settlements = get_recent_settlements(limit=HIGH_ACCURACY_STRATEGY_BREAKER_WINDOW * 4)
    except Exception:
        settlements = []
    resolved = _apply_high_accuracy_strategy_breakers(status, settlements)
    if cache_key is not None:
        _HIGH_ACCURACY_STRATEGY_STATUS_CACHE["cache_key"] = cache_key
        _HIGH_ACCURACY_STRATEGY_STATUS_CACHE["status"] = dict(resolved)
    return resolved


def _load_cached_statsbomb_state_json(path: Path) -> dict:
    try:
        stat = path.stat()
    except OSError:
        _STATSBOMB_STATE_JSON_CACHE.pop(path, None)
        return {}
    signature = (int(stat.st_mtime_ns), int(stat.st_size))
    cached = _STATSBOMB_STATE_JSON_CACHE.get(path)
    if cached and cached[0] == signature:
        return cached[1]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        _STATSBOMB_STATE_JSON_CACHE.pop(path, None)
        return {}
    if not isinstance(payload, dict):
        _STATSBOMB_STATE_JSON_CACHE.pop(path, None)
        return {}
    _STATSBOMB_STATE_JSON_CACHE[path] = (signature, payload)
    return payload


def invalidate_statsbomb_state_cache(path: Path | None = None) -> None:
    if path is None:
        _STATSBOMB_STATE_JSON_CACHE.clear()
        return
    _STATSBOMB_STATE_JSON_CACHE.pop(path, None)


def get_statsbomb_event_baseline() -> dict:
    return _load_cached_statsbomb_state_json(STATSBOMB_EVENT_BASELINE_FILE)


def get_statsbomb_sandbox_fewshot_memory() -> dict:
    return _load_cached_statsbomb_state_json(STATSBOMB_SANDBOX_FEWSHOT_FILE)


def get_statsbomb_review_training_samples() -> dict:
    return _load_cached_statsbomb_state_json(STATSBOMB_REVIEW_TRAINING_FILE)


def get_video_review_fewshot_memory() -> dict:
    return _load_cached_statsbomb_state_json(VIDEO_REVIEW_FEWSHOT_MEMORY_FILE)


def _build_high_accuracy_strategy_pool(candidates: list[dict]) -> list[dict]:
    pool: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    def add_item(item: dict) -> None:
        key = (
            normalize_text(item.get("scope", "")),
            normalize_text(item.get("scope_value", "")),
            normalize_text(item.get("play_type", "")),
        )
        if key in seen:
            return
        seen.add(key)
        strategy = dict(item)
        if not pool:
            strategy["role"] = "primary"
        elif float(strategy.get("accuracy", 0.0) or 0.0) >= 0.55 and int(strategy.get("sample_count", 0) or 0) >= 18:
            strategy["role"] = "backup"
        else:
            strategy["role"] = "observe"
        stability = strategy.get("stability", {}) if isinstance(strategy.get("stability"), dict) else {}
        if strategy["role"] == "backup" and not bool(stability.get("stable", False)):
            strategy["role"] = "observe"
        pool.append(strategy)

    for item in candidates:
        add_item(item)
        if len(pool) >= 6:
            break
    present_layers = {
        normalize_text((item.get("layer", {}) if isinstance(item.get("layer"), dict) else {}).get("data_layer", ""))
        for item in pool
    }
    for item in candidates:
        layer = item.get("layer", {}) if isinstance(item.get("layer"), dict) else {}
        data_layer = normalize_text(layer.get("data_layer", ""))
        if data_layer and data_layer not in present_layers:
            add_item(item)
            present_layers.add(data_layer)
        if len(pool) >= 8:
            break
    return pool


def _strategy_layer_summary(candidates: list[dict]) -> dict:
    summary: dict[str, dict[str, int]] = {
        "data_layer": {},
        "scope_layer": {},
        "play_layer": {},
    }
    stable_count = 0
    for item in candidates:
        layer = item.get("layer", {}) if isinstance(item.get("layer"), dict) else {}
        stability = item.get("stability", {}) if isinstance(item.get("stability"), dict) else {}
        if bool(stability.get("stable", False)):
            stable_count += 1
        for key in ("data_layer", "scope_layer", "play_layer"):
            value = normalize_text(layer.get(key, "")) or normalize_text(item.get("play_type", "")) or "-"
            bucket = summary.setdefault(key, {})
            bucket[value] = int(bucket.get(value, 0)) + 1
    summary["stable"] = {"true": stable_count, "false": max(0, len(candidates) - stable_count)}
    return summary


def _market_pick_context(match: AppMatch, prediction: dict) -> dict:
    market_probabilities = prediction.get("market_probabilities", {}) if isinstance(prediction.get("market_probabilities"), dict) else {}
    if market_probabilities:
        pick_key = max(("home", "draw", "away"), key=lambda key: _safe_float(market_probabilities.get(key), default=0.0))
        confidence = _safe_float(market_probabilities.get(pick_key), default=0.0)
    else:
        pick_key = ""
        confidence = 0.0
    pick_odds = {
        "home": _safe_float(match.odds_home, default=0.0),
        "draw": _safe_float(match.odds_draw, default=0.0),
        "away": _safe_float(match.odds_away, default=0.0),
    }.get(pick_key, 0.0)
    league = normalize_text(match.league) or "-"
    year = normalize_text(match.match_date)[:4] if len(normalize_text(match.match_date)) >= 4 else "-"
    confidence_bucket = _confidence_bucket(confidence)
    odds_bucket = _odds_bucket(pick_odds)
    return {
        "pick_key": pick_key,
        "pick": {"home": "涓昏儨", "draw": "骞冲眬", "away": "瀹㈣儨"}.get(pick_key, "-"),
        "confidence": round(_clamp(confidence), 4),
        "pick_odds": round(_safe_float(pick_odds, default=0.0), 4),
        "league": league,
        "year": year,
        "confidence_bucket": confidence_bucket,
        "odds_bucket": odds_bucket,
        "dimension_values": {
            "global": "all",
            "year": year,
            "league": league,
            "odds_bucket": odds_bucket,
            "confidence_bucket": confidence_bucket,
            "pick_side": pick_key or "-",
            "league_odds_bucket": f"{league} | {odds_bucket}",
            "league_confidence_bucket": f"{league} | {confidence_bucket}",
        },
    }


def _jc_bucket_runtime_eligible(bucket: dict, calibration: dict | None = None) -> bool:
    if not isinstance(bucket, dict):
        return False
    stability = bucket.get("stability", {}) if isinstance(bucket.get("stability"), dict) else {}
    thresholds = calibration.get("thresholds", {}) if isinstance(calibration, dict) and isinstance(calibration.get("thresholds"), dict) else {}
    min_samples = max(1, int(_safe_int(thresholds.get("min_samples"), JC_STRATIFIED_MIN_RUNTIME_SAMPLES) or JC_STRATIFIED_MIN_RUNTIME_SAMPLES))
    min_accuracy = _safe_float(thresholds.get("min_accuracy"), default=JC_STRATIFIED_MIN_RUNTIME_ACCURACY)
    min_wilson = _safe_float(thresholds.get("min_wilson"), default=JC_STRATIFIED_MIN_RUNTIME_WILSON)
    min_stability_score = _safe_float(thresholds.get("min_stability_score"), default=JC_STRATIFIED_MIN_STABILITY_SCORE)
    return bool(
        bool(stability.get("stable", False))
        and int(_safe_int(bucket.get("sample_count"), 0) or 0) >= min_samples
        and _safe_float(bucket.get("accuracy"), default=0.0) >= min_accuracy
        and _safe_float(bucket.get("wilson_lower"), default=0.0) >= min_wilson
        and _safe_float(stability.get("stability_score"), default=0.0) >= min_stability_score
    )


def _jc_bucket_min_confidence(bucket: dict) -> float:
    dimension = normalize_text(bucket.get("dimension", ""))
    bucket_text = normalize_text(bucket.get("bucket", ""))
    if "confidence" not in dimension:
        return 0.0
    tail = bucket_text.rsplit("|", 1)[-1].strip()
    if tail.startswith(">="):
        return round(_safe_float(tail[2:], default=0.0), 2)
    if "-" in tail:
        return round(_safe_float(tail.split("-", 1)[0], default=0.0), 2)
    if tail.startswith("<"):
        return 0.0
    return 0.0


def _jc_stratified_runtime_strategies(match: AppMatch, prediction: dict) -> list[dict]:
    status = get_jc_stratified_strategy_status()
    if not bool(status.get("enabled")):
        return []
    context = _market_pick_context(match, prediction)
    dimension_values = context.get("dimension_values", {}) if isinstance(context.get("dimension_values"), dict) else {}
    top_buckets = status.get("top_buckets", []) if isinstance(status.get("top_buckets"), list) else []
    live_feedback = build_jc_bucket_live_feedback(limit=JC_BUCKET_LIVE_FEEDBACK_WINDOW)
    calibration = build_jc_strategy_auto_calibration(status, live_feedback)
    thresholds = calibration.get("thresholds", {}) if isinstance(calibration.get("thresholds"), dict) else {}
    observe_live_statuses = {
        normalize_text(item)
        for item in thresholds.get("observe_live_statuses", ["downgraded"])
        if normalize_text(item)
    }
    strategies: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for bucket in top_buckets:
        if not _jc_bucket_runtime_eligible(bucket, calibration):
            continue
        dimension = normalize_text(bucket.get("dimension", ""))
        bucket_value = normalize_text(bucket.get("bucket", ""))
        if not dimension or (dimension, bucket_value) in seen:
            continue
        if normalize_text(dimension_values.get(dimension, "")) != bucket_value:
            continue
        seen.add((dimension, bucket_value))
        bucket_key = _jc_bucket_key_from_parts(dimension, bucket_value)
        feedback = live_feedback.get(bucket_key, {})
        feedback_status = normalize_text(feedback.get("status", ""))
        breaker_on = bool(feedback_status in observe_live_statuses)
        strategy = {
            "role": "primary" if not strategies else "backup",
            "scope": "jc_bucket",
            "scope_value": bucket_value,
            "dimension": dimension,
            "play_type": "market_1x2",
            "min_confidence": _jc_bucket_min_confidence(bucket),
            "accuracy": bucket.get("accuracy", 0.0),
            "hit_count": bucket.get("hit_count", 0),
            "sample_count": bucket.get("sample_count", 0),
            "wilson_lower": bucket.get("wilson_lower", 0.0),
            "stability": bucket.get("stability", {}) if isinstance(bucket.get("stability"), dict) else {},
            "layer": {
                "data_layer": "jc_stratified_market",
                "scope_layer": dimension,
                "play_layer": "market_1x2",
                "sample_sources": bucket.get("sample_sources", {}),
            },
            "breaker": {
                "breaker_on": breaker_on,
                "status": "jc_live_downgraded" if breaker_on else (feedback_status or "active"),
                "reason": feedback.get("reason"),
            },
            "jc_bucket": bucket,
            "jc_context": context,
            "jc_bucket_key": bucket_key,
            "jc_live_feedback": feedback,
            "jc_auto_calibration": calibration,
            "updated_at": status.get("updated_at"),
        }
        strategies.append(strategy)
    return strategies


def run_high_accuracy_strategy_backtest(
    *,
    limit: int = 500,
    historical_limit: int = 50000,
    min_samples: int = 18,
    min_coverage: float = 0.02,
    min_league_samples: int = 18,
    write_report: bool = True,
) -> dict:
    settlements = get_recent_settlements(limit=max(0, int(limit)))
    settlement_records = _settlement_strategy_records(settlements)
    historical_records = _xgb_market_strategy_records(limit=max(0, int(historical_limit)))
    records = settlement_records + historical_records
    if not records:
        return {"ok": False, "reason": "no_strategy_records", "strategy": {}, "validation": {"settlement_count": len(settlements), "record_count": 0}}

    confidence_grid = {
        "market_1x2": [0.34, 0.38, 0.42, 0.46, 0.50, 0.55, 0.60, 0.65, 0.70],
        "1x2": [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70],
        "handicap": [0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75],
        "total_goals": [0.16, 0.18, 0.20, 0.24, 0.28, 0.32, 0.36],
        "ou": [0.50, 0.51, 0.52, 0.53, 0.54, 0.55],
        "score": [0.08, 0.10, 0.12, 0.15, 0.18, 0.22],
    }
    candidates: list[dict] = []

    def collect_candidates(source_records: list[dict], grids: dict[str, list[float]]) -> None:
        source_total = len(source_records)
        if source_total <= 0:
            return
        for play_type, thresholds in grids.items():
            for threshold in thresholds:
                candidate = _strategy_candidate_from_rows(
                    source_records,
                    scope="global",
                    scope_value="all",
                    play_type=play_type,
                    min_confidence=threshold,
                    total_records=source_total,
                    min_samples=max(1, int(min_samples)),
                    min_coverage=max(0.0, float(min_coverage)),
                )
                if candidate is not None:
                    candidates.append(candidate)

        by_league: dict[str, list[dict]] = defaultdict(list)
        for row in source_records:
            by_league[normalize_text(row.get("league", "")) or "-"].append(row)
        for league, league_rows in by_league.items():
            if len(league_rows) < max(1, int(min_league_samples)):
                continue
            league_coverage = max(0.0, float(min_coverage) / 2.0)
            for play_type, thresholds in grids.items():
                for threshold in thresholds:
                    candidate = _strategy_candidate_from_rows(
                        league_rows,
                        scope="league",
                        scope_value=league,
                        play_type=play_type,
                        min_confidence=threshold,
                        total_records=source_total,
                        min_samples=max(1, int(min_league_samples)),
                        min_coverage=league_coverage,
                    )
                    if candidate is not None:
                        candidates.append(candidate)

    collect_candidates(historical_records, {"market_1x2": confidence_grid["market_1x2"]})
    collect_candidates(
        settlement_records,
        {
            key: value
            for key, value in confidence_grid.items()
            if key != "market_1x2"
        },
    )

    if not candidates:
        return {
            "ok": False,
            "reason": "no_candidate_passed_constraints",
            "strategy": {},
            "validation": {
                "settlement_count": len(settlements),
                "record_count": len(records),
                "settlement_record_count": len(settlement_records),
                "historical_record_count": len(historical_records),
                "min_samples": int(min_samples),
                "min_coverage": round(float(min_coverage), 4),
            },
        }

    candidates = sorted(
        candidates,
        key=lambda item: (
            1.0 if bool((item.get("stability", {}) if isinstance(item.get("stability"), dict) else {}).get("stable", False)) else 0.0,
            float(item.get("accuracy", 0.0)),
            float(item.get("wilson_lower", 0.0)),
            float((item.get("stability", {}) if isinstance(item.get("stability"), dict) else {}).get("stability_score", 0.0)),
            float(item.get("edge", 0.0)),
            int(item.get("sample_count", 0)),
            float(item.get("coverage", 0.0)),
        ),
        reverse=True,
    )
    best = dict(candidates[0])
    strategy_pool = _build_high_accuracy_strategy_pool(candidates)
    layer_summary = _strategy_layer_summary(candidates)
    dates = [normalize_text(row.get("match_date", "")) for row in records if normalize_text(row.get("match_date", ""))]
    validation = {
        "settlement_count": len(settlements),
        "record_count": len(records),
        "settlement_record_count": len(settlement_records),
        "historical_record_count": len(historical_records),
        "date_start": min(dates) if dates else None,
        "date_end": max(dates) if dates else None,
        "historical_limit": int(historical_limit),
        "min_samples": int(min_samples),
        "min_coverage": round(float(min_coverage), 4),
        "min_league_samples": int(min_league_samples),
        "candidate_count": len(candidates),
        "stable_candidate_count": int(layer_summary.get("stable", {}).get("true", 0)),
        "strategy_layers": layer_summary,
    }
    persisted = {
        "enabled": True,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reason": "ok",
        "strategy": best,
        "strategy_pool": strategy_pool,
        "validation": validation,
        "top_candidates": candidates[:10],
    }
    _save_high_accuracy_strategy_report(persisted)
    result = {
        "ok": True,
        "reason": "ok",
        "strategy": best,
        "strategy_pool": strategy_pool,
        "validation": validation,
        "top_candidates": candidates[:10],
        "status": get_high_accuracy_strategy_status(),
    }
    result["report_path"] = _write_high_accuracy_strategy_report(result) if write_report else None
    return result


def _high_accuracy_strategy_match(match: AppMatch, prediction: dict, play_catalog: dict[str, dict]) -> dict:
    status = get_high_accuracy_strategy_status()
    strategy = status.get("strategy", {}) if isinstance(status, dict) else {}
    strategy_pool = status.get("strategy_pool", []) if isinstance(status, dict) else []
    jc_strategy_pool = _jc_stratified_runtime_strategies(match, prediction)
    if not bool(status.get("enabled")) or not isinstance(strategy, dict) or not strategy:
        if not jc_strategy_pool:
            return {"enabled": False, "active": False, "reason": status.get("reason", "not_calibrated") if isinstance(status, dict) else "not_calibrated"}
        status = {"enabled": True, "updated_at": jc_strategy_pool[0].get("updated_at"), "reason": "jc_stratified_runtime"}
        strategy = jc_strategy_pool[0]
        strategy_pool = jc_strategy_pool
        jc_strategy_pool = []
    if not isinstance(strategy_pool, list) or not strategy_pool:
        strategy_pool = [{**strategy, "role": "primary"}]
    strategy_pool = [item for item in strategy_pool if isinstance(item, dict)] + jc_strategy_pool

    def evaluate(item: dict) -> dict:
        result = _high_accuracy_strategy_match_single(
            match=match,
            prediction=prediction,
            play_catalog=play_catalog,
            strategy=item,
            updated_at=status.get("updated_at"),
        )
        return result

    matches = [evaluate(item) for item in strategy_pool if isinstance(item, dict)]
    selected = next((item for item in matches if item.get("active")), matches[0] if matches else evaluate({**strategy, "role": "primary"}))
    primary = dict(selected)
    pool_matches = [dict(item) for item in matches]
    active_matches = [dict(item) for item in matches if item.get("active")]
    shadow_matches = [dict(item) for item in matches if item.get("shadow_active")]
    primary["strategy_pool"] = pool_matches
    primary["active_matches"] = active_matches
    primary["shadow_matches"] = shadow_matches
    primary["active_count"] = len(active_matches)
    primary["shadow_count"] = len(shadow_matches)
    primary["summary"] = (
        " / ".join(f"{item.get('play_type', '-')} {item.get('pick', '-')}" for item in active_matches[:3])
        if active_matches
        else f"断路观察 {len(shadow_matches)}"
        if shadow_matches
        else "未命中"
    )
    return primary


def _high_accuracy_strategy_match_single(
    *,
    match: AppMatch,
    prediction: dict,
    play_catalog: dict[str, dict],
    strategy: dict,
    updated_at: object = None,
) -> dict:
    play_type = normalize_text(strategy.get("play_type", ""))
    if play_type == "ou":
        play_item = {
            "play_type": "ou",
            "pick": prediction.get("ou_recommendation", "-"),
            "confidence": round(_safe_float(prediction.get("ou_confidence"), default=0.0), 4),
            "passed": True,
        }
    elif play_type == "market_1x2":
        market_probabilities = prediction.get("market_probabilities", {}) if isinstance(prediction.get("market_probabilities"), dict) else {}
        key_to_result = {"home": "主胜", "draw": "平局", "away": "客胜"}
        if market_probabilities:
            pick_key = max(("home", "draw", "away"), key=lambda key: _safe_float(market_probabilities.get(key), default=0.0))
            confidence_value = _safe_float(market_probabilities.get(pick_key), default=0.0)
        else:
            pick_key = ""
            confidence_value = 0.0
        play_item = {
            "play_type": "market_1x2",
            "pick": key_to_result.get(pick_key, "-"),
            "confidence": round(confidence_value, 4),
            "passed": confidence_value > 0.0,
        }
    else:
        play_item = play_catalog.get(play_type, {}) if isinstance(play_catalog, dict) else {}
    confidence = _safe_float(play_item.get("confidence"), default=0.0)
    min_confidence = _safe_float(strategy.get("min_confidence"), default=1.0)
    scope = normalize_text(strategy.get("scope", "global"))
    scope_value = normalize_text(strategy.get("scope_value", "all"))
    league = normalize_text(match.league) or "-"
    jc_context: dict = {}
    if scope == "jc_bucket":
        context = _market_pick_context(match, prediction)
        jc_context = context
        dimension = normalize_text(strategy.get("dimension", ""))
        dimension_values = context.get("dimension_values", {}) if isinstance(context.get("dimension_values"), dict) else {}
        scope_ok = bool(dimension and normalize_text(dimension_values.get(dimension, "")) == scope_value)
        if play_type == "market_1x2":
            play_item = {
                "play_type": "market_1x2",
                "pick": context.get("pick", "-"),
                "confidence": context.get("confidence", 0.0),
                "passed": bool(context.get("pick_key")),
            }
            confidence = _safe_float(play_item.get("confidence"), default=0.0)
    else:
        scope_ok = scope != "league" or scope_value == league
    passed = bool(play_item.get("passed", False))
    gate_matched = bool(scope_ok and passed and confidence >= min_confidence)
    active = gate_matched
    reason = "matched" if active else "below_strategy_gate"
    if not scope_ok:
        reason = "league_scope_mismatch"
    elif not passed:
        reason = "play_threshold_blocked"
    breaker = strategy.get("breaker", {}) if isinstance(strategy.get("breaker"), dict) else {}
    shadow_active = bool(breaker.get("breaker_on") and gate_matched)
    if shadow_active:
        active = False
        reason = "strategy_breaker_observing"
    layer = strategy.get("layer", {}) if isinstance(strategy.get("layer"), dict) else {}
    return {
        "enabled": True,
        "active": active,
        "gate_matched": gate_matched,
        "shadow_active": shadow_active,
        "reason": reason,
        "play_type": play_type,
        "pick": play_item.get("pick", "-"),
        "confidence": round(confidence, 4),
        "min_confidence": round(min_confidence, 2),
        "scope": scope,
        "scope_value": scope_value,
        "backtest_accuracy": strategy.get("accuracy", 0.0),
        "backtest_hits": strategy.get("hit_count", 0),
        "backtest_samples": strategy.get("sample_count", 0),
        "wilson_lower": strategy.get("wilson_lower", 0.0),
        "role": strategy.get("effective_role") or strategy.get("role", "primary"),
        "original_role": strategy.get("original_role") or strategy.get("role", "primary"),
        "layer": layer,
        "data_layer": layer.get("data_layer", "-"),
        "breaker": breaker,
        "dimension": strategy.get("dimension"),
        "jc_bucket": strategy.get("jc_bucket") if isinstance(strategy.get("jc_bucket"), dict) else {},
        "jc_context": strategy.get("jc_context") if isinstance(strategy.get("jc_context"), dict) else jc_context,
        "jc_bucket_key": strategy.get("jc_bucket_key") or _jc_bucket_key(strategy),
        "jc_live_feedback": strategy.get("jc_live_feedback") if isinstance(strategy.get("jc_live_feedback"), dict) else {},
        "jc_auto_calibration": strategy.get("jc_auto_calibration") if isinstance(strategy.get("jc_auto_calibration"), dict) else {},
        "updated_at": updated_at,
    }


def _high_accuracy_strategy_actual_for_play(
    *,
    play_type: str,
    result: str,
    total_goals: int,
    actual_score: str,
    handicap_result: str,
    ou_result: str,
) -> object:
    if play_type in {"1x2", "market_1x2"}:
        return result
    if play_type == "handicap":
        return handicap_result
    if play_type == "ou":
        return ou_result
    if play_type == "total_goals":
        return _format_total_goals_label(total_goals)
    if play_type == "score":
        return actual_score
    return None


def _high_accuracy_strategy_hit(play_type: str, pick: object, actual: object) -> bool | None:
    pick_text = normalize_text(pick)
    actual_text = normalize_text(actual)
    if not pick_text or not actual_text:
        return None
    if play_type == "handicap":
        return bool(pick_text == actual_text or pick_text.endswith(actual_text) or actual_text.endswith(pick_text))
    return bool(pick_text == actual_text)


def _settle_high_accuracy_strategy_results(
    prediction: dict | None,
    *,
    result: str,
    total_goals: int,
    actual_score: str,
    handicap_result: str,
    ou_result: str,
) -> dict:
    if not isinstance(prediction, dict):
        return {"items": [], "active_count": 0, "hit_count": 0, "summary": "-"}
    high_strategy = prediction.get("high_accuracy_strategy", {})
    if not isinstance(high_strategy, dict) or not high_strategy.get("enabled"):
        return {"items": [], "active_count": 0, "hit_count": 0, "summary": "-"}
    active_items = high_strategy.get("active_matches", [])
    if not isinstance(active_items, list) or not active_items:
        active_items = [high_strategy] if high_strategy.get("active") else []
    shadow_items = high_strategy.get("shadow_matches", [])
    if not isinstance(shadow_items, list):
        shadow_items = []
    settled_items: list[dict] = []

    def settle_item(item: dict, *, is_shadow: bool) -> dict | None:
        if not isinstance(item, dict):
            return None
        play_type = normalize_text(item.get("play_type", ""))
        actual = _high_accuracy_strategy_actual_for_play(
            play_type=play_type,
            result=result,
            total_goals=total_goals,
            actual_score=actual_score,
            handicap_result=handicap_result,
            ou_result=ou_result,
        )
        is_hit = _high_accuracy_strategy_hit(play_type, item.get("pick"), actual)
        layer = item.get("layer", {}) if isinstance(item.get("layer"), dict) else {}
        breaker = item.get("breaker", {}) if isinstance(item.get("breaker"), dict) else {}
        data_layer = item.get("data_layer") or layer.get("data_layer", "-")
        settled = {
            "role": item.get("role", "-"),
            "original_role": item.get("original_role", item.get("role", "-")),
            "play_type": play_type,
            "scope": item.get("scope", "-"),
            "scope_value": item.get("scope_value", "-"),
            "data_layer": data_layer,
            "pick": item.get("pick", "-"),
            "actual": actual,
            "confidence": round(_safe_float(item.get("confidence"), default=0.0), 4),
            "min_confidence": round(_safe_float(item.get("min_confidence"), default=0.0), 2),
            "backtest_accuracy": item.get("backtest_accuracy", 0.0),
            "backtest_samples": item.get("backtest_samples", 0),
            "is_hit": is_hit,
            "is_shadow": bool(is_shadow),
            "blocked_by_breaker": bool(is_shadow and breaker.get("breaker_on")),
            "breaker_status": breaker.get("status", "-"),
        }
        if normalize_text(data_layer) == "jc_stratified_market" or isinstance(item.get("jc_bucket"), dict):
            jc_bucket = _jc_bucket_metadata(item)
            jc_context = item.get("jc_context", {}) if isinstance(item.get("jc_context"), dict) else {}
            settled.update(
                {
                    "dimension": jc_bucket.get("dimension", item.get("dimension")),
                    "jc_bucket": jc_bucket,
                    "jc_context": {
                        "confidence_bucket": jc_context.get("confidence_bucket"),
                        "odds_bucket": jc_context.get("odds_bucket"),
                        "pick_odds": jc_context.get("pick_odds"),
                    },
                    "jc_bucket_key": _jc_bucket_key(item),
                    "jc_live_feedback": item.get("jc_live_feedback") if isinstance(item.get("jc_live_feedback"), dict) else {},
                    "jc_auto_calibration": item.get("jc_auto_calibration") if isinstance(item.get("jc_auto_calibration"), dict) else {},
                }
            )
        return settled

    for item in active_items:
        settled = settle_item(item, is_shadow=False)
        if settled is not None:
            settled_items.append(settled)
    for item in shadow_items:
        settled = settle_item(item, is_shadow=True)
        if settled is not None:
            settled_items.append(settled)

    official_items = [item for item in settled_items if not item.get("is_shadow")]
    shadow_settled_items = [item for item in settled_items if item.get("is_shadow")]
    hit_count = sum(1 for item in official_items if item.get("is_hit") is True)
    shadow_hit_count = sum(1 for item in shadow_settled_items if item.get("is_hit") is True)
    summary = f"{hit_count}/{len(official_items)}" if official_items else "-"
    shadow_summary = f"{shadow_hit_count}/{len(shadow_settled_items)}" if shadow_settled_items else "-"
    return {
        "items": settled_items,
        "active_count": len(official_items),
        "hit_count": hit_count,
        "shadow_count": len(shadow_settled_items),
        "shadow_hit_count": shadow_hit_count,
        "summary": summary,
        "shadow_summary": shadow_summary,
    }


def _risk_bucket_from_label(label: object) -> str:
    text = normalize_text(label).upper()
    if "HIGH" in text or "楂" in text:
        return "high"
    if "MEDIUM" in text or "MID" in text or "涓" in text:
        return "medium"
    return "low"


def _agent_replay_admission_guard(
    *,
    agent_names: list[str] | None = None,
    actions: list[str] | None = None,
    settlements: list[dict] | None = None,
    min_samples: int = 5,
    prediction_miss_threshold: float = 0.55,
    handicap_miss_threshold: float = 0.60,
) -> dict:
    names = [normalize_text(name) for name in (agent_names or []) if normalize_text(name)]
    action_items = [normalize_text(action) for action in (actions or []) if normalize_text(action)]
    if not names and not action_items:
        return {"applied": False, "decision": "pass", "reason": "", "rows": []}
    if settlements is None:
        try:
            settlement_items = get_recent_settlements(limit=120)
        except Exception:
            settlement_items = []
    else:
        settlement_items = settlements
    rows: list[dict] = []
    for name in names:
        triggered = []
        for item in settlement_items:
            if not isinstance(item, dict):
                continue
            statuses = item.get("supervisor_agent_statuses") if isinstance(item.get("supervisor_agent_statuses"), dict) else {}
            status = normalize_text(statuses.get(name)).lower()
            if status in {"alert", "watch", "blocked"}:
                triggered.append(item)
        prediction_known = [item for item in triggered if item.get("is_correct") is not None]
        handicap_known = [item for item in triggered if item.get("handicap_is_correct") is not None]
        prediction_miss_rate = (
            sum(1 for item in prediction_known if item.get("is_correct") is False) / len(prediction_known)
            if prediction_known
            else None
        )
        handicap_miss_rate = (
            sum(1 for item in handicap_known if item.get("handicap_is_correct") is False) / len(handicap_known)
            if handicap_known
            else None
        )
        sample_count = max(len(prediction_known), len(handicap_known))
        rows.append(
            {
                "agent": name,
                "sample_count": sample_count,
                "prediction_known": len(prediction_known),
                "prediction_miss_rate": round(prediction_miss_rate, 4) if prediction_miss_rate is not None else None,
                "handicap_known": len(handicap_known),
                "handicap_miss_rate": round(handicap_miss_rate, 4) if handicap_miss_rate is not None else None,
            }
        )
    triggered_rows = [
        row
        for row in rows
        if int(row.get("sample_count") or 0) >= max(1, int(min_samples))
        and (
            (
                row.get("prediction_miss_rate") is not None
                and _safe_float(row.get("prediction_miss_rate"), 0.0) >= prediction_miss_threshold
            )
            or (
                row.get("handicap_miss_rate") is not None
                and _safe_float(row.get("handicap_miss_rate"), 0.0) >= handicap_miss_threshold
            )
        )
    ]
    if not triggered_rows:
        return {
            "applied": False,
            "decision": "pass",
            "reason": "",
            "agent_names": names,
            "actions": action_items,
            "rows": rows,
        }
    triggered_rows.sort(
        key=lambda row: (
            -max(
                _safe_float(row.get("prediction_miss_rate"), 0.0),
                _safe_float(row.get("handicap_miss_rate"), 0.0),
            ),
            str(row.get("agent") or ""),
        )
    )
    top = triggered_rows[0]
    return {
        "applied": True,
        "decision": "observe",
        "reason": "agent_replay_policy_watch",
        "agent_names": names,
        "actions": action_items,
        "top_agent": top.get("agent", "-"),
        "top_prediction_miss_rate": top.get("prediction_miss_rate"),
        "top_handicap_miss_rate": top.get("handicap_miss_rate"),
        "rows": rows,
    }


def _strategy_admission_gate(
    *,
    risk_level: object,
    confidence: object,
    high_strategy: dict | None,
    play_strategy: dict | None = None,
    agent_replay_context: dict | None = None,
) -> dict:
    high = high_strategy if isinstance(high_strategy, dict) else {}
    play = play_strategy if isinstance(play_strategy, dict) else {}
    active_matches = high.get("active_matches", []) if isinstance(high.get("active_matches"), list) else []
    shadow_matches = high.get("shadow_matches", []) if isinstance(high.get("shadow_matches"), list) else []
    active_count = len(active_matches) if active_matches else int(high.get("active_count", 0) or 0)
    shadow_count = len(shadow_matches) if shadow_matches else int(high.get("shadow_count", 0) or 0)
    risk_bucket = _risk_bucket_from_label(risk_level)
    confidence_value = _safe_float(confidence, default=0.0)
    single_count = len(play.get("single", [])) if isinstance(play.get("single"), list) else 0
    admission_policy = _current_strategy_admission_policy()
    min_confidence = _safe_float(admission_policy.get("min_confidence"), STRATEGY_ADMISSION_MIN_CONFIDENCE)
    block_confidence = _safe_float(admission_policy.get("block_confidence"), STRATEGY_ADMISSION_BLOCK_CONFIDENCE)
    active_strategy_min = max(1, int(_safe_int(admission_policy.get("active_strategy_min"), 1) or 1))
    medium_risk_allowed = bool(admission_policy.get("medium_risk_allowed", True))
    high_risk_allowed = bool(admission_policy.get("high_risk_allowed", False))
    risk_allowed = (
        risk_bucket == "low"
        or (risk_bucket == "medium" and medium_risk_allowed)
        or (risk_bucket == "high" and high_risk_allowed)
    )
    reasons: list[str] = []

    if not bool(high.get("enabled")):
        reasons.append("strategy_not_calibrated")
    if active_count >= active_strategy_min:
        reasons.append("high_accuracy_strategy_active")
    elif active_count > 0:
        reasons.append("high_accuracy_strategy_count_below_policy")
    else:
        reasons.append("no_official_high_accuracy_strategy")
    if shadow_count > 0:
        reasons.append("breaker_shadow_observation")
    if risk_bucket == "high":
        reasons.append("risk_high")
    elif risk_bucket == "medium":
        reasons.append("risk_medium")
        if not medium_risk_allowed:
            reasons.append("risk_medium_policy_watch")
    else:
        reasons.append("risk_low")
    if confidence_value < block_confidence:
        reasons.append("confidence_block")
    elif confidence_value < min_confidence:
        reasons.append("confidence_watch")
    if single_count <= 0:
        reasons.append("no_single_play_passed")
    replay_context = agent_replay_context if isinstance(agent_replay_context, dict) else {}
    replay_guard_policy = {
        "enabled": bool(admission_policy.get("agent_replay_guard_enabled", True)),
        "min_samples": max(1, int(_safe_int(admission_policy.get("agent_replay_min_samples"), 5) or 5)),
        "prediction_miss_threshold": _safe_float(admission_policy.get("agent_replay_prediction_miss_threshold"), 0.55),
        "handicap_miss_threshold": _safe_float(admission_policy.get("agent_replay_handicap_miss_threshold"), 0.60),
    }
    if replay_guard_policy["enabled"]:
        replay_guard = _agent_replay_admission_guard(
            agent_names=replay_context.get("agent_names") if isinstance(replay_context.get("agent_names"), list) else [],
            actions=replay_context.get("actions") if isinstance(replay_context.get("actions"), list) else [],
            min_samples=int(replay_guard_policy["min_samples"]),
            prediction_miss_threshold=float(replay_guard_policy["prediction_miss_threshold"]),
            handicap_miss_threshold=float(replay_guard_policy["handicap_miss_threshold"]),
        )
    else:
        replay_guard = {
            "applied": False,
            "decision": "pass",
            "reason": "agent_replay_guard_disabled",
            "agent_names": replay_context.get("agent_names") if isinstance(replay_context.get("agent_names"), list) else [],
            "actions": replay_context.get("actions") if isinstance(replay_context.get("actions"), list) else [],
            "rows": [],
        }
    replay_guard["policy"] = dict(replay_guard_policy)
    if replay_guard.get("applied"):
        reasons.append(str(replay_guard.get("reason") or "agent_replay_policy_watch"))

    if active_count >= active_strategy_min and risk_allowed and confidence_value >= min_confidence:
        decision = "allow"
        label = "正式放行"
        action = "FORMAL_ALLOW"
    elif (
        (risk_bucket == "high" and not high_risk_allowed and active_count < active_strategy_min and shadow_count <= 0)
        or (confidence_value < block_confidence and active_count < active_strategy_min)
    ):
        decision = "block"
        label = "阻断"
        action = "BLOCK"
    else:
        decision = "observe"
        label = "观察"
        action = "OBSERVE"

    if decision == "allow" and replay_guard.get("applied"):
        decision = "observe"
        label = "瑙傚療"
        action = "OBSERVE"

    candidate = active_matches[0] if active_matches else shadow_matches[0] if shadow_matches else high
    if not isinstance(candidate, dict):
        candidate = {}
    return {
        "enabled": bool(high.get("enabled")),
        "decision": decision,
        "label": label,
        "action": action,
        "release_allowed": decision == "allow",
        "observe": decision == "observe",
        "blocked": decision == "block",
        "risk_bucket": risk_bucket,
        "confidence": round(confidence_value, 4),
        "min_confidence": min_confidence,
        "block_confidence": block_confidence,
        "active_strategy_min": active_strategy_min,
        "medium_risk_allowed": medium_risk_allowed,
        "high_risk_allowed": high_risk_allowed,
        "agent_replay_policy": replay_guard_policy,
        "active_count": active_count,
        "shadow_count": shadow_count,
        "single_play_count": single_count,
        "top_play": candidate.get("play_type", "-"),
        "top_pick": candidate.get("pick", "-"),
        "top_confidence": round(_safe_float(candidate.get("confidence"), default=0.0), 4),
        "summary": high.get("summary", "-"),
        "reasons": reasons,
        "agent_replay_guard": replay_guard,
    }


def calibrate_play_thresholds_by_settlement_now(
    *,
    limit: int = 500,
    min_samples: int = 18,
    weak_ev_bias: float = -0.08,
    strong_ev_bias: float = 0.08,
    step: float = 0.02,
    max_step_levels: int = 4,
    min_coverage: float = 0.18,
    write_report: bool = True,
) -> dict:
    settlements = get_recent_settlements(limit=max(0, int(limit)))
    if not settlements:
        return {
            "calibrated": False,
            "reason": "no_settlements",
            "thresholds": _current_play_thresholds(),
            "metrics": {},
            "validation": {"source": "settlements", "sample_count": 0},
            "status": get_play_threshold_status(),
        }

    current_thresholds = _current_play_thresholds()
    observed = _collect_settlement_play_metrics(settlements)
    next_thresholds = dict(current_thresholds)
    metrics: dict[str, dict] = {}
    changed_count = 0
    usable_plays = 0

    for play_name, current_threshold in current_thresholds.items():
        item = dict(observed.get(play_name, {}))
        sample_count = int(item.get("sample_count", 0) or 0)
        hit_rate = _safe_float(item.get("hit_rate"), default=0.0)
        expected_hit_rate = _safe_float(item.get("expected_hit_rate"), default=0.0)
        ev_bias = _safe_float(item.get("ev_bias"), default=0.0)
        delta = 0.0
        action = "hold"
        reason = "stable"

        if sample_count < max(1, int(min_samples)):
            reason = "insufficient_samples"
        elif play_name == "htft":
            reason = "not_settled"
        else:
            usable_plays += 1
            if ev_bias <= float(weak_ev_bias):
                severity = max(1, min(int(max_step_levels), 1 + int(abs(ev_bias - weak_ev_bias) / 0.04)))
                delta = float(step) * severity
                action = "raise"
                reason = "negative_ev_bias"
            elif ev_bias >= float(strong_ev_bias):
                delta = -float(step)
                action = "lower"
                reason = "positive_ev_bias"

        min_thr, max_thr = PLAY_THRESHOLD_RANGE.get(play_name, (0.0, 1.0))
        new_threshold = max(float(min_thr), min(float(max_thr), float(current_threshold) + delta))
        confidence_values = [float(value) for value in item.get("confidence_values", []) if _safe_float(value, 0.0) > 0.0]
        if confidence_values and sample_count > 0 and delta > 0.0:
            floor = max(0.0, min(1.0, float(min_coverage)))
            min_selected = max(1, int(sample_count * floor + 0.9999))
            if min_selected < sample_count:
                ordered = sorted(confidence_values)
                coverage_limit = ordered[max(0, len(ordered) - min_selected)]
                new_threshold = min(new_threshold, max(float(current_threshold), float(coverage_limit)))
        new_threshold = round(new_threshold, 2)
        delta_applied = round(new_threshold - float(current_threshold), 2)
        if abs(delta_applied) > 1e-9:
            changed_count += 1

        next_thresholds[play_name] = new_threshold
        coverage = 1.0 if sample_count > 0 else 0.0
        metrics[play_name] = {
            "threshold": new_threshold,
            "old_threshold": round(float(current_threshold), 2),
            "delta": delta_applied,
            "accuracy": round(hit_rate, 6),
            "coverage": coverage,
            "selected": sample_count,
            "total": sample_count,
            "expected_hit_rate": round(expected_hit_rate, 6),
            "ev_bias": round(ev_bias, 6),
            "hit_count": int(item.get("hit_count", 0) or 0),
            "sample_count": sample_count,
            "action": action,
            "reason": reason,
        }

    mode = "bucket_tuned" if changed_count > 0 else "bucket_tuned_no_change"
    report = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "thresholds": next_thresholds,
        "metrics": metrics,
        "validation": {
            "source": "settlements",
            "sample_count": len(settlements),
            "window": int(limit),
            "min_samples": int(min_samples),
            "weak_ev_bias": round(float(weak_ev_bias), 4),
            "strong_ev_bias": round(float(strong_ev_bias), 4),
            "step": round(float(step), 4),
            "min_coverage": round(float(min_coverage), 4),
            "usable_play_count": usable_plays,
            "changed_play_count": changed_count,
        },
    }
    _save_play_threshold_report(report)

    report_path = None
    if write_report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = REPORT_DIR / f"play_thresholds_bucket_tuning_{timestamp}.md"
        lines = [
            "# Play Threshold Bucket Tuning Report",
            "",
            f"- Generated At: {report['updated_at']}",
            f"- Settlements Window: {int(limit)}",
            f"- Settlement Samples: {len(settlements)}",
            f"- Min Samples Per Play: {int(min_samples)}",
            f"- Weak EV Bias Threshold: {float(weak_ev_bias):+.2%}",
            f"- Strong EV Bias Threshold: {float(strong_ev_bias):+.2%}",
            f"- Min Coverage Floor: {float(min_coverage):.1%}",
            f"- Applied Changes: {changed_count}",
            "",
            "| Play | Old | New | Delta | Hit Rate | Expected Hit | EV Bias | Samples | Action | Reason |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ]
        for play_name in ("1x2", "handicap", "total_goals", "score", "htft"):
            item = metrics.get(play_name, {})
            lines.append(
                f"| {play_name} | {float(item.get('old_threshold', 0) or 0):.2f} | {float(item.get('threshold', 0) or 0):.2f} | "
                f"{float(item.get('delta', 0) or 0):+.2f} | {float(item.get('accuracy', 0) or 0):.2%} | "
                f"{float(item.get('expected_hit_rate', 0) or 0):.2%} | {float(item.get('ev_bias', 0) or 0):+.2%} | "
                f"{int(item.get('sample_count', 0) or 0)} | {item.get('action', '-')} | {item.get('reason', '-')} |"
            )
        report_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "calibrated": changed_count > 0,
        "reason": "ok" if changed_count > 0 else "no_significant_bucket_gap",
        "thresholds": next_thresholds,
        "metrics": metrics,
        "validation": report["validation"],
        "report_path": str(report_path) if report_path else None,
        "status": get_play_threshold_status(),
    }


def _load_recent_prediction_records(limit: int = 240) -> list[dict]:
    snapshot_records = STATE_STORE.load_prediction_snapshots()
    rows: list[dict] = []
    for record in snapshot_records.values():
        if not isinstance(record, dict):
            continue
        prediction = record.get("prediction")
        if not isinstance(prediction, dict):
            continue
        rows.append(
            {
                "saved_at": normalize_text(record.get("saved_at", "")),
                "prediction": prediction,
            }
        )
    rows.sort(key=lambda item: str(item.get("saved_at", "")))
    if limit > 0 and len(rows) > limit:
        rows = rows[-limit:]
    return rows


def _simulate_single_coverage_from_predictions(
    rows: list[dict],
    thresholds: dict[str, float],
    play_policy: dict[str, dict],
) -> dict:
    specs = {
        "1x2": ("confidence", None),
        "handicap": ("handicap_confidence", None),
        "total_goals": ("total_goals_confidence", None),
        "score": ("score_confidence", None),
        "htft": ("htft_confidence", None),
    }
    analyzed = len(rows)
    if analyzed <= 0:
        return {
            "analyzed_count": 0,
            "single_match_count": 0,
            "single_coverage": 0.0,
            "single_pick_count": 0,
            "avg_single_picks": 0.0,
            "by_play_match_count": {key: 0 for key in specs},
            "by_play_pick_count": {key: 0 for key in specs},
        }

    single_match_count = 0
    single_pick_count = 0
    by_play_match_ids: dict[str, set[int]] = {key: set() for key in specs}
    by_play_pick_count: dict[str, int] = {key: 0 for key in specs}

    for idx, row in enumerate(rows):
        prediction = row.get("prediction", {})
        if not isinstance(prediction, dict):
            continue
        has_single = False
        for play_name, (confidence_key, _unused) in specs.items():
            policy = play_policy.get(play_name, {}) if isinstance(play_policy, dict) else {}
            if not bool(policy.get("single_enabled", True)):
                continue
            threshold = _safe_float(thresholds.get(play_name), default=DEFAULT_PLAY_THRESHOLDS.get(play_name, 0.0))
            confidence = _safe_float(prediction.get(confidence_key), default=0.0)
            if confidence <= 0.0 or confidence > 1.0:
                continue
            if confidence >= threshold:
                has_single = True
                single_pick_count += 1
                by_play_pick_count[play_name] += 1
                by_play_match_ids[play_name].add(idx)
        if has_single:
            single_match_count += 1

    by_play_match_count = {key: len(value) for key, value in by_play_match_ids.items()}
    single_coverage = single_match_count / analyzed
    avg_single_picks = single_pick_count / analyzed
    return {
        "analyzed_count": analyzed,
        "single_match_count": single_match_count,
        "single_coverage": round(single_coverage, 6),
        "single_pick_count": single_pick_count,
        "avg_single_picks": round(avg_single_picks, 6),
        "by_play_match_count": by_play_match_count,
        "by_play_pick_count": by_play_pick_count,
    }


def _coverage_distance(metrics: dict, target_coverage: float, target_avg_picks: float) -> float:
    coverage = _safe_float(metrics.get("single_coverage"), default=0.0)
    avg_picks = _safe_float(metrics.get("avg_single_picks"), default=0.0)
    return abs(coverage - target_coverage) + 0.35 * abs(avg_picks - target_avg_picks)


def calibrate_play_thresholds_coverage_guardrail_now(
    *,
    snapshot_limit: int = 240,
    min_predictions: int = 12,
    target_min_coverage: float = 0.30,
    target_max_coverage: float = 0.72,
    target_max_avg_picks: float = 1.85,
    step: float = 0.02,
    max_step_levels: int = 4,
    write_report: bool = True,
) -> dict:
    rows = _load_recent_prediction_records(limit=max(0, int(snapshot_limit)))
    if len(rows) < max(1, int(min_predictions)):
        return {
            "calibrated": False,
            "reason": "insufficient_predictions",
            "thresholds": _current_play_thresholds(),
            "validation": {
                "source": "prediction_snapshots",
                "prediction_count": len(rows),
                "min_predictions": int(min_predictions),
            },
            "status": get_play_threshold_status(),
        }

    current_thresholds = _current_play_thresholds()
    play_policy = _current_play_policy()
    baseline = _simulate_single_coverage_from_predictions(rows, current_thresholds, play_policy)
    current_cov = _safe_float(baseline.get("single_coverage"), default=0.0)
    current_avg_picks = _safe_float(baseline.get("avg_single_picks"), default=0.0)

    direction = 0
    reason = "stable"
    if current_cov < float(target_min_coverage):
        direction = -1
        reason = "coverage_too_low"
    elif current_cov > float(target_max_coverage) or current_avg_picks > float(target_max_avg_picks):
        direction = 1
        reason = "coverage_too_high"

    target_cov = (float(target_min_coverage) + float(target_max_coverage)) / 2.0
    target_avg = min(float(target_max_avg_picks), 1.60)
    best = {
        "thresholds": dict(current_thresholds),
        "metrics": baseline,
        "level": 0,
        "distance": _coverage_distance(baseline, target_cov, target_avg),
    }

    candidate_rows: list[dict] = []
    if direction != 0:
        for level in range(1, max(1, int(max_step_levels)) + 1):
            candidate: dict[str, float] = {}
            delta = float(step) * level * direction
            for play_name, value in current_thresholds.items():
                policy = play_policy.get(play_name, {}) if isinstance(play_policy, dict) else {}
                if not bool(policy.get("single_enabled", True)):
                    candidate[play_name] = round(float(value), 2)
                    continue
                lo, hi = PLAY_THRESHOLD_RANGE.get(play_name, (0.0, 1.0))
                adjusted = max(float(lo), min(float(hi), float(value) + delta))
                candidate[play_name] = round(adjusted, 2)
            metrics = _simulate_single_coverage_from_predictions(rows, candidate, play_policy)
            distance = _coverage_distance(metrics, target_cov, target_avg)
            row = {"level": level, "thresholds": candidate, "metrics": metrics, "distance": round(distance, 6)}
            candidate_rows.append(row)

            cov = _safe_float(metrics.get("single_coverage"), default=0.0)
            avg = _safe_float(metrics.get("avg_single_picks"), default=0.0)
            in_band = (cov >= float(target_min_coverage) and cov <= float(target_max_coverage) and avg <= float(target_max_avg_picks))
            if in_band:
                best = {"thresholds": candidate, "metrics": metrics, "level": level, "distance": distance}
                break
            if distance < float(best["distance"]) - 1e-9:
                best = {"thresholds": candidate, "metrics": metrics, "level": level, "distance": distance}

    next_thresholds = dict(best["thresholds"])
    changed = any(abs(_safe_float(next_thresholds.get(k), 0.0) - _safe_float(current_thresholds.get(k), 0.0)) > 1e-9 for k in current_thresholds)

    metrics = {}
    for play_name in current_thresholds:
        metrics[play_name] = {
            "old_threshold": round(float(current_thresholds.get(play_name, 0.0)), 2),
            "threshold": round(float(next_thresholds.get(play_name, 0.0)), 2),
            "delta": round(float(next_thresholds.get(play_name, 0.0)) - float(current_thresholds.get(play_name, 0.0)), 2),
            "match_count": int(best["metrics"].get("by_play_match_count", {}).get(play_name, 0) if isinstance(best["metrics"], dict) else 0),
            "pick_count": int(best["metrics"].get("by_play_pick_count", {}).get(play_name, 0) if isinstance(best["metrics"], dict) else 0),
        }

    report = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "coverage_guardrail",
        "thresholds": next_thresholds,
        "metrics": metrics,
        "validation": {
            "source": "prediction_snapshots",
            "prediction_count": len(rows),
            "target_min_coverage": round(float(target_min_coverage), 4),
            "target_max_coverage": round(float(target_max_coverage), 4),
            "target_max_avg_picks": round(float(target_max_avg_picks), 4),
            "base_single_coverage": round(current_cov, 4),
            "base_avg_single_picks": round(current_avg_picks, 4),
            "final_single_coverage": round(_safe_float(best["metrics"].get("single_coverage"), 0.0), 4),
            "final_avg_single_picks": round(_safe_float(best["metrics"].get("avg_single_picks"), 0.0), 4),
            "direction": direction,
            "reason": reason,
            "selected_level": int(best["level"]),
            "changed_play_count": sum(1 for item in metrics.values() if abs(_safe_float(item.get("delta"), 0.0)) > 1e-9),
        },
    }
    _save_play_threshold_report(report)

    report_path = None
    if write_report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = REPORT_DIR / f"play_thresholds_coverage_guardrail_{timestamp}.md"
        lines = [
            "# Play Threshold Coverage Guardrail Report",
            "",
            f"- Generated At: {report['updated_at']}",
            f"- Prediction Samples: {len(rows)}",
            f"- Baseline Coverage: {current_cov:.2%}",
            f"- Baseline Avg Picks: {current_avg_picks:.2f}",
            f"- Final Coverage: {_safe_float(best['metrics'].get('single_coverage'), 0.0):.2%}",
            f"- Final Avg Picks: {_safe_float(best['metrics'].get('avg_single_picks'), 0.0):.2f}",
            f"- Direction: {direction}",
            f"- Reason: {reason}",
            f"- Selected Level: {int(best['level'])}",
            "",
            "## Threshold Update",
            "",
            "| Play | Old | New | Delta | Match Coverage | Pick Count |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for play_name in ("1x2", "handicap", "total_goals", "score", "htft"):
            item = metrics.get(play_name, {})
            lines.append(
                f"| {play_name} | {float(item.get('old_threshold', 0) or 0):.2f} | {float(item.get('threshold', 0) or 0):.2f} | "
                f"{float(item.get('delta', 0) or 0):+.2f} | {int(item.get('match_count', 0) or 0)} | {int(item.get('pick_count', 0) or 0)} |"
            )
        if candidate_rows:
            lines.extend(
                [
                    "",
                    "## Candidate Levels",
                    "",
                    "| Level | Coverage | Avg Picks | Distance |",
                    "|---:|---:|---:|---:|",
                ]
            )
            for candidate in candidate_rows:
                row_metrics = candidate.get("metrics", {})
                lines.append(
                    f"| {int(candidate.get('level', 0) or 0)} | "
                    f"{_safe_float(row_metrics.get('single_coverage'), 0.0):.2%} | "
                    f"{_safe_float(row_metrics.get('avg_single_picks'), 0.0):.2f} | "
                    f"{_safe_float(candidate.get('distance'), 0.0):.4f} |"
                )
        report_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "calibrated": bool(changed),
        "reason": "ok" if changed else "no_guardrail_change_needed",
        "thresholds": next_thresholds,
        "metrics": metrics,
        "validation": report["validation"],
        "report_path": str(report_path) if report_path else None,
        "status": get_play_threshold_status(),
    }


def run_ensemble_backtest(
    validation_ratio: float = 0.20,
    min_validation_samples: int = 1000,
    write_report: bool = True,
) -> dict:
    train_items, validation_items = _validation_split_samples(
        validation_ratio=validation_ratio,
        min_validation_samples=min_validation_samples,
    )
    if not train_items or not validation_items:
        return {
            "ok": False,
            "reason": "insufficient_validation_split",
        }

    component_rows, extra = _build_validation_component_rows(train_items, validation_items)
    if not component_rows:
        return {
            "ok": False,
            "reason": "no_validation_rows",
        }

    default_metrics = _evaluate_ensemble_scheme(component_rows, DEFAULT_ENSEMBLE_WEIGHTS)
    calibrated_status = get_ensemble_weight_status()
    calibrated_weights = calibrated_status.get("weights", DEFAULT_ENSEMBLE_WEIGHTS)
    league_weights = calibrated_status.get("league_weights", {})
    calibrated_metrics = _evaluate_ensemble_scheme(component_rows, calibrated_weights)
    league_specific_metrics = _evaluate_league_aware_scheme(component_rows, calibrated_weights, league_weights)
    stage4_runtime_metrics = _evaluate_prediction_scheme_from_payloads(validation_items, "ensemble_probabilities")
    stage5_specialist_metrics = _evaluate_prediction_scheme_from_payloads(validation_items, "probabilities")
    improvement = {
        "logloss_delta": round(default_metrics["logloss"] - calibrated_metrics["logloss"], 6),
        "brier_delta": round(default_metrics["brier"] - calibrated_metrics["brier"], 6),
        "accuracy_delta": round(calibrated_metrics["accuracy"] - default_metrics["accuracy"], 6),
    }
    league_improvement = {
        "logloss_delta": round(default_metrics["logloss"] - league_specific_metrics["logloss"], 6),
        "brier_delta": round(default_metrics["brier"] - league_specific_metrics["brier"], 6),
        "accuracy_delta": round(league_specific_metrics["accuracy"] - default_metrics["accuracy"], 6),
    }
    stage5_improvement = {
        "logloss_delta": round(stage4_runtime_metrics["logloss"] - stage5_specialist_metrics["logloss"], 6),
        "brier_delta": round(stage4_runtime_metrics["brier"] - stage5_specialist_metrics["brier"], 6),
        "accuracy_delta": round(stage5_specialist_metrics["accuracy"] - stage4_runtime_metrics["accuracy"], 6),
    }

    dates = [row.get("match_date") for row in component_rows if row.get("match_date")]
    result = {
        "ok": True,
        "reason": "ok",
        "validation": {
            "sample_count": len(component_rows),
            "train_sample_count": len(train_items),
            "date_start": min(dates) if dates else None,
            "date_end": max(dates) if dates else None,
            "ratio": round(len(component_rows) / max(len(train_items) + len(component_rows), 1), 4),
            **extra,
        },
        "default": default_metrics,
        "calibrated": calibrated_metrics,
        "league_specific": league_specific_metrics,
        "stage4_runtime": stage4_runtime_metrics,
        "stage5_specialist": stage5_specialist_metrics,
        "improvement": improvement,
        "league_improvement": league_improvement,
        "stage5_improvement": stage5_improvement,
    }

    report_path = None
    if write_report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = REPORT_DIR / f"ensemble_backtest_{timestamp}.md"
        lines = [
            "# Ensemble Backtest Report",
            "",
            f"- Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- Validation Samples: {result['validation']['sample_count']}",
            f"- Train Samples: {result['validation']['train_sample_count']}",
            f"- Validation Window: {result['validation']['date_start']} -> {result['validation']['date_end']}",
            "",
            "| Scheme | Weights | Logloss | Brier | Accuracy |",
            "|---|---|---:|---:|---:|",
            f"| Default | market={default_metrics['weights']['market']:.1%}, elo={default_metrics['weights']['elo']:.1%}, poisson={default_metrics['weights']['poisson']:.1%}, xgb={default_metrics['weights']['xgboost']:.1%} | {default_metrics['logloss']:.6f} | {default_metrics['brier']:.6f} | {default_metrics['accuracy']:.2%} |",
            f"| Calibrated | market={calibrated_metrics['weights']['market']:.1%}, elo={calibrated_metrics['weights']['elo']:.1%}, poisson={calibrated_metrics['weights']['poisson']:.1%}, xgb={calibrated_metrics['weights']['xgboost']:.1%} | {calibrated_metrics['logloss']:.6f} | {calibrated_metrics['brier']:.6f} | {calibrated_metrics['accuracy']:.2%} |",
            f"| League Aware | global=market {calibrated_metrics['weights']['market']:.1%}, elo {calibrated_metrics['weights']['elo']:.1%}, poisson {calibrated_metrics['weights']['poisson']:.1%}, xgb {calibrated_metrics['weights']['xgboost']:.1%}; overrides={len(league_weights) if isinstance(league_weights, dict) else 0} | {league_specific_metrics['logloss']:.6f} | {league_specific_metrics['brier']:.6f} | {league_specific_metrics['accuracy']:.2%} |",
            f"| Stage4 Runtime | calibrated+league | {stage4_runtime_metrics['logloss']:.6f} | {stage4_runtime_metrics['brier']:.6f} | {stage4_runtime_metrics['accuracy']:.2%} |",
            f"| Stage5 Specialists | calibrated+league+specialists | {stage5_specialist_metrics['logloss']:.6f} | {stage5_specialist_metrics['brier']:.6f} | {stage5_specialist_metrics['accuracy']:.2%} |",
            "",
            "## Improvement",
            "",
            f"- Logloss Delta: {improvement['logloss_delta']:+.6f}",
            f"- Brier Delta: {improvement['brier_delta']:+.6f}",
            f"- Accuracy Delta: {improvement['accuracy_delta']:+.2%}",
            f"- League-Aware Logloss Delta: {league_improvement['logloss_delta']:+.6f}",
            f"- League-Aware Brier Delta: {league_improvement['brier_delta']:+.6f}",
            f"- League-Aware Accuracy Delta: {league_improvement['accuracy_delta']:+.2%}",
            f"- Stage5 Logloss Delta: {stage5_improvement['logloss_delta']:+.6f}",
            f"- Stage5 Brier Delta: {stage5_improvement['brier_delta']:+.6f}",
            f"- Stage5 Accuracy Delta: {stage5_improvement['accuracy_delta']:+.2%}",
            "",
            "## Draw Behavior",
            "",
            f"- Stage4 Draw Picks: {stage4_runtime_metrics['draw_picks']} (hit rate {stage4_runtime_metrics['draw_hit_rate']:.2%})",
            f"- Stage5 Draw Picks: {stage5_specialist_metrics['draw_picks']} (hit rate {stage5_specialist_metrics['draw_hit_rate']:.2%})",
            "",
        ]
        report_path.write_text("\n".join(lines), encoding="utf-8")
    result["report_path"] = str(report_path) if report_path else None
    return result


def _parse_total_goals_from_score_text(score_text: str) -> int | None:
    text = str(score_text or "").strip()
    if "-" not in text:
        return None
    try:
        home_goals, away_goals = [int(part) for part in text.split("-", 1)]
    except Exception:
        return None
    return home_goals + away_goals


_REGULAR_SCORELINE_SET = {
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


def _scoreline_bucket(score_text: str | None) -> str:
    text = str(score_text or "").strip()
    if not text or "-" not in text:
        return "volatile"
    if text in _REGULAR_SCORELINE_SET:
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


def _merge_scoreline_model_outputs(
    base_output: dict | None,
    volatile_output: dict | None,
) -> tuple[dict, bool]:
    base = dict(base_output) if isinstance(base_output, dict) else {}
    volatile = dict(volatile_output) if isinstance(volatile_output, dict) else {}
    base_label = str(base.get("label") or "").strip()
    volatile_label = str(volatile.get("label") or "").strip()
    base_conf = _safe_float(base.get("confidence"), default=0.0)
    volatile_conf = _safe_float(volatile.get("confidence"), default=0.0)
    if not volatile.get("model_ready") or not volatile_label or volatile_label == "OTHER":
        return base, False
    if _scoreline_bucket(volatile_label) != "volatile":
        return base, False
    if not base.get("model_ready") or not base_label or base_label == "OTHER":
        return base, False
    if _scoreline_bucket(base_label) != "volatile":
        return base, False
    if volatile_label != base_label:
        return base, False
    if volatile_conf >= max(base_conf, 0.08):
        candidate = dict(volatile)
        candidate["source_model"] = "volatile"
        return candidate, True
    return base, False


def _poisson_baseline_handicap_prediction(prediction: dict, handicap_line: float) -> str | None:
    poisson = prediction.get("poisson", {}) if isinstance(prediction, dict) else {}
    distribution = poisson.get("score_distribution", []) if isinstance(poisson, dict) else []
    probabilities = {"home": 0.0, "draw": 0.0, "away": 0.0}
    for item in distribution:
        score_text = str(item.get("score", ""))
        if "-" not in score_text:
            continue
        try:
            home_goals, away_goals = [int(part) for part in score_text.split("-", 1)]
        except Exception:
            continue
        key = _handicap_outcome_key(home_goals, away_goals, handicap_line)
        probabilities[key] += _safe_float(item.get("probability"), default=0.0)
    if max(probabilities.values()) <= 0.0:
        return None
    return _handicap_label_from_key(max(probabilities, key=probabilities.get))


def _record_play_backtest_hit(bucket: dict[str, float], predicted: object, actual: object) -> None:
    if predicted is None or actual is None:
        return
    bucket["total"] += 1
    if str(predicted) == str(actual):
        bucket["hits"] += 1


def _model_total_goals_pick(prediction: dict | None) -> int | None:
    if not isinstance(prediction, dict):
        return None
    model_output = prediction.get("total_goals_model")
    if not isinstance(model_output, dict) or not model_output.get("model_ready"):
        return None
    return _safe_int(model_output.get("label"))


def _model_scoreline_pick(prediction: dict | None) -> str | None:
    if not isinstance(prediction, dict):
        return None
    model_output = prediction.get("scoreline_model")
    if not isinstance(model_output, dict) or not model_output.get("model_ready"):
        return None
    label = str(model_output.get("label", "")).strip()
    if not label or label == "OTHER":
        return None
    return label


def _prediction_recommendation_key(prediction: dict | None) -> str | None:
    if not isinstance(prediction, dict):
        return None
    recommendation = str(prediction.get("recommendation", "")).strip()
    mapping = {
        "主胜": "home",
        "涓昏儨": "home",
        "home": "home",
        "平局": "draw",
        "骞冲眬": "draw",
        "draw": "draw",
        "客胜": "away",
        "瀹㈣儨": "away",
        "away": "away",
    }
    return mapping.get(recommendation)


def _scoreline_policy_thresholds(scoreline_policy: dict | None, bucket: str) -> dict[str, float | bool]:
    defaults = DEFAULT_PLAY_MODEL_POLICY.get("scoreline", {})
    policy = scoreline_policy if isinstance(scoreline_policy, dict) else {}
    prefix = "regular" if bucket == "regular" else "volatile"
    legacy_same = _safe_float(
        policy.get("same_outcome_min_confidence"),
        default=_safe_float(defaults.get(f"{prefix}_same_outcome_min_confidence"), default=0.09),
    )
    legacy_cross_enabled = bool(policy.get("cross_outcome_enabled", defaults.get(f"{prefix}_cross_outcome_enabled", False)))
    legacy_cross = _safe_float(
        policy.get("cross_outcome_min_confidence"),
        default=_safe_float(defaults.get(f"{prefix}_cross_outcome_min_confidence"), default=0.14),
    )
    return {
        "bucket": prefix,
        "same_outcome_min_confidence": _safe_float(
            policy.get(f"{prefix}_same_outcome_min_confidence"),
            default=legacy_same,
        ),
        "cross_outcome_enabled": bool(
            policy.get(f"{prefix}_cross_outcome_enabled", legacy_cross_enabled)
        ),
        "cross_outcome_min_confidence": _safe_float(
            policy.get(f"{prefix}_cross_outcome_min_confidence"),
            default=legacy_cross,
        ),
    }


def _scoreline_takeover_decision(
    label: str | None,
    confidence: float,
    recommendation_key: str | None,
    scoreline_policy: dict | None,
) -> tuple[bool, str | None, float, str]:
    if not label:
        return False, None, 0.0, "volatile"
    bucket = _scoreline_bucket(label)
    thresholds = _scoreline_policy_thresholds(scoreline_policy, bucket)
    label_outcome_key = _score_outcome_key(label)
    if recommendation_key and label_outcome_key == recommendation_key:
        if confidence < _safe_float(thresholds.get("same_outcome_min_confidence"), default=0.09):
            return False, label, confidence, bucket
        return True, label, confidence, bucket
    if not bool(thresholds.get("cross_outcome_enabled", False)):
        return False, label, confidence, bucket
    if confidence < _safe_float(thresholds.get("cross_outcome_min_confidence"), default=0.14):
        return False, label, confidence, bucket
    return True, label, confidence, bucket


def _scoreline_takeover_allowed(
    prediction: dict | None,
    scoreline_policy: dict | None,
) -> tuple[bool, str | None, float, str]:
    if not isinstance(prediction, dict):
        return False, None, 0.0, "volatile"
    label = _model_scoreline_pick(prediction)
    if not label:
        return False, None, 0.0, "volatile"
    model_output = prediction.get("scoreline_model", {})
    confidence = _safe_float(model_output.get("confidence"), default=0.0) if isinstance(model_output, dict) else 0.0
    recommendation_key = _prediction_recommendation_key(prediction)
    return _scoreline_takeover_decision(
        label=label,
        confidence=confidence,
        recommendation_key=recommendation_key,
        scoreline_policy=scoreline_policy,
    )


def _simulate_play_model_policy(
    prediction: dict | None,
    policy: dict | None,
) -> dict[str, object]:
    if not isinstance(prediction, dict):
        return {
            "total_goals_value": None,
            "score_recommendation": None,
            "total_goals_model_takeover": False,
            "scoreline_model_takeover": False,
        }
    normalized_policy = json.loads(json.dumps(DEFAULT_PLAY_MODEL_POLICY))
    if isinstance(policy, dict):
        for key, value in policy.items():
            if key in normalized_policy and isinstance(value, dict):
                normalized_policy[key].update(value)

    recommendation_key = _prediction_recommendation_key(prediction)
    score_distribution = (prediction.get("poisson") or {}).get("score_distribution", [])
    total_goals_value = _safe_int(prediction.get("pre_play_model_total_goals_value"))
    total_goals_confidence = _safe_float(prediction.get("pre_play_model_total_goals_confidence"), default=0.0)
    score_recommendation = str(prediction.get("pre_play_model_score_recommendation") or "").strip() or None
    score_confidence = _safe_float(prediction.get("pre_play_model_score_confidence"), default=0.0)

    total_goals_policy = normalized_policy.get("total_goals", {})
    total_goals_model_pick = _model_total_goals_pick(prediction)
    total_goals_model_output = prediction.get("total_goals_model", {})
    total_goals_model_confidence = _safe_float(
        total_goals_model_output.get("confidence"),
        default=0.0,
    ) if isinstance(total_goals_model_output, dict) else 0.0
    total_goals_takeover = bool(
        bool(total_goals_policy.get("takeover_enabled"))
        and total_goals_model_pick is not None
        and total_goals_model_confidence >= _safe_float(total_goals_policy.get("min_confidence"), default=0.24)
    )
    if total_goals_takeover and total_goals_model_pick is not None:
        total_goals_value = int(total_goals_model_pick)
        total_goals_confidence = total_goals_model_confidence
        aligned_score = _best_score_for_total_goals(
            score_distribution,
            total_goals=total_goals_value,
            outcome_key=recommendation_key,
        )
        if isinstance(aligned_score, dict):
            score_recommendation = str(aligned_score.get("score", "")).strip() or score_recommendation
            score_confidence = _safe_float(aligned_score.get("probability"), default=score_confidence)

    scoreline_policy = normalized_policy.get("scoreline", {})
    scoreline_takeover, scoreline_label, scoreline_confidence, _ = _scoreline_takeover_allowed(
        prediction,
        scoreline_policy=scoreline_policy,
    )
    if scoreline_takeover and scoreline_label:
        parsed_total_goals = _parse_total_goals_from_score_text(scoreline_label)
        if not total_goals_takeover or parsed_total_goals == total_goals_value:
            score_recommendation = scoreline_label
            score_confidence = scoreline_confidence
            if parsed_total_goals is not None:
                total_goals_value = parsed_total_goals
                total_goals_confidence = max(total_goals_confidence, scoreline_confidence)
        else:
            scoreline_takeover = False

    return {
        "total_goals_value": total_goals_value,
        "total_goals_confidence": total_goals_confidence,
        "score_recommendation": score_recommendation,
        "score_confidence": score_confidence,
        "total_goals_model_takeover": total_goals_takeover,
        "scoreline_model_takeover": scoreline_takeover,
    }


def _finalize_play_backtest_bucket(bucket: dict[str, float]) -> dict[str, float | int]:
    total = int(bucket.get("total", 0) or 0)
    hits = int(bucket.get("hits", 0) or 0)
    return {
        "hits": hits,
        "total": total,
        "accuracy": round(hits / max(total, 1), 6),
    }


def _split_play_model_policy_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    if len(rows) < PLAY_MODEL_POLICY_MIN_HOLDOUT_ROWS * 2:
        return list(rows), []
    holdout_count = int(len(rows) * PLAY_MODEL_POLICY_HOLDOUT_RATIO)
    holdout_count = max(PLAY_MODEL_POLICY_MIN_HOLDOUT_ROWS, holdout_count)
    holdout_count = min(holdout_count, len(rows) // 2)
    if holdout_count <= 0:
        return list(rows), []
    return list(rows[:-holdout_count]), list(rows[-holdout_count:])


def _play_model_policy_metrics(rows: list[dict], policy: dict | None) -> dict[str, float | int]:
    score_hits = 0
    score_total = 0
    total_goals_hits = 0
    total_goals_total = 0
    for row in rows:
        output = _simulate_play_model_policy(row.get("prediction"), policy)
        total_goals_pick = _safe_int(output.get("total_goals_value"))
        score_pick = str(output.get("score_recommendation") or "").strip() or None
        if total_goals_pick is not None:
            total_goals_total += 1
            if int(total_goals_pick) == int(row.get("actual_total_goals", -1)):
                total_goals_hits += 1
        if score_pick:
            score_total += 1
            if score_pick == row.get("actual_score"):
                score_hits += 1
    return {
        "score_hits": score_hits,
        "score_total": score_total,
        "score_accuracy": round(score_hits / max(score_total, 1), 6),
        "total_goals_hits": total_goals_hits,
        "total_goals_total": total_goals_total,
        "total_goals_accuracy": round(total_goals_hits / max(total_goals_total, 1), 6),
    }


def calibrate_play_model_policy_now(
    validation_ratio: float = 0.20,
    min_validation_samples: int = 1000,
    max_validation_samples: int | None = 800,
    search_profile: str = "fast",
) -> dict:
    previous_policy_report = _load_play_model_policy_report()
    train_items, validation_items = _validation_split_samples(
        validation_ratio=validation_ratio,
        min_validation_samples=min_validation_samples,
    )
    if not validation_items:
        return {"calibrated": False, "reason": "insufficient_validation_split"}
    original_validation_count = len(validation_items)
    if max_validation_samples is not None and max_validation_samples > 0 and len(validation_items) > max_validation_samples:
        validation_items = validation_items[-int(max_validation_samples):]

    rows: list[dict] = []
    for item in validation_items:
        prediction = _sample_item_prediction(item)
        meta = item.get("meta", {}) if isinstance(item.get("meta"), dict) else {}
        if not isinstance(prediction, dict) or not isinstance(meta, dict):
            continue
        home_goals = _safe_int(meta.get("home_goals"))
        away_goals = _safe_int(meta.get("away_goals"))
        if home_goals is None or away_goals is None:
            continue
        rows.append(
            {
                "prediction": prediction,
                "actual_score": f"{int(home_goals)}-{int(away_goals)}",
                "actual_total_goals": int(home_goals) + int(away_goals),
            }
        )
    if not rows:
        return {"calibrated": False, "reason": "no_valid_rows"}

    tuning_rows, holdout_rows = _split_play_model_policy_rows(rows)
    current_policy = _current_play_model_policy(effective=False)
    current_metrics = _play_model_policy_metrics(tuning_rows, current_policy)
    current_score_hits = int(current_metrics.get("score_hits", 0) or 0)
    current_score_total = int(current_metrics.get("score_total", 0) or 0)
    current_total_goals_hits = int(current_metrics.get("total_goals_hits", 0) or 0)
    current_total_goals_total = int(current_metrics.get("total_goals_total", 0) or 0)

    candidates: list[dict] = []
    if str(search_profile).strip().lower() == "full":
        regular_same_candidates = [0.05, 0.07, 0.09]
        regular_cross_candidates = [0.05, 0.07, 0.09, 0.11]
        volatile_same_candidates = [0.05, 0.07, 0.09, 0.11, 0.13]
        volatile_cross_candidates = [0.05, 0.07, 0.09, 0.11, 0.13]
        total_goal_threshold_candidates = [0.18, 0.22, 0.26]
        resolved_search_profile = "full"
    else:
        regular_same_candidates = [0.05, 0.07, 0.09]
        regular_cross_candidates = [0.07, 0.09, 0.11]
        volatile_same_candidates = [0.09, 0.11, 0.13]
        volatile_cross_candidates = [0.11, 0.13]
        total_goal_threshold_candidates = [0.22, 0.26]
        resolved_search_profile = "fast"
    for regular_same_threshold in regular_same_candidates:
        for regular_cross_enabled in (False, True):
            for regular_cross_threshold in regular_cross_candidates:
                for volatile_same_threshold in volatile_same_candidates:
                    for volatile_cross_enabled in (False, True):
                        for volatile_cross_threshold in volatile_cross_candidates:
                            for total_goals_enabled in (False, True):
                                for total_goal_threshold in total_goal_threshold_candidates:
                                    candidate_policy = {
                                        "total_goals": {
                                            "takeover_enabled": total_goals_enabled,
                                            "min_confidence": round(total_goal_threshold, 2),
                                        },
                                        "scoreline": {
                                            "takeover_enabled": True,
                                            "regular_same_outcome_min_confidence": round(regular_same_threshold, 2),
                                            "regular_cross_outcome_enabled": regular_cross_enabled,
                                            "regular_cross_outcome_min_confidence": round(regular_cross_threshold, 2),
                                            "volatile_same_outcome_min_confidence": round(volatile_same_threshold, 2),
                                            "volatile_cross_outcome_enabled": volatile_cross_enabled,
                                            "volatile_cross_outcome_min_confidence": round(volatile_cross_threshold, 2),
                                        },
                                    }
                                    score_hits = 0
                                    score_covered = 0
                                    total_goals_hits = 0
                                    total_goals_covered = 0
                                    for row in tuning_rows:
                                        output = _simulate_play_model_policy(row.get("prediction"), candidate_policy)
                                        total_goals_pick = _safe_int(output.get("total_goals_value"))
                                        score_pick = str(output.get("score_recommendation") or "").strip() or None
                                        if total_goals_pick is not None:
                                            total_goals_covered += 1
                                            if int(total_goals_pick) == int(row.get("actual_total_goals", -1)):
                                                total_goals_hits += 1
                                        if score_pick:
                                            score_covered += 1
                                            if score_pick == row.get("actual_score"):
                                                score_hits += 1
                                    score_accuracy = score_hits / max(score_covered, 1)
                                    total_goals_accuracy = total_goals_hits / max(total_goals_covered, 1)
                                    combined_hits = score_hits + total_goals_hits
                                    candidates.append(
                                        {
                                            "regular_same_outcome_min_confidence": round(regular_same_threshold, 2),
                                            "regular_cross_outcome_enabled": regular_cross_enabled,
                                            "regular_cross_outcome_min_confidence": round(regular_cross_threshold, 2),
                                            "volatile_same_outcome_min_confidence": round(volatile_same_threshold, 2),
                                            "volatile_cross_outcome_enabled": volatile_cross_enabled,
                                            "volatile_cross_outcome_min_confidence": round(volatile_cross_threshold, 2),
                                            "total_goals_takeover_enabled": total_goals_enabled,
                                            "total_goals_min_confidence": round(total_goal_threshold, 2),
                                            "score_hits": score_hits,
                                            "score_covered": score_covered,
                                            "score_accuracy": round(score_accuracy, 6),
                                            "total_goals_hits": total_goals_hits,
                                            "total_goals_covered": total_goals_covered,
                                            "total_goals_accuracy": round(total_goals_accuracy, 6),
                                            "combined_hits": combined_hits,
                                            "objective": combined_hits,
                                        }
                                    )

    best = max(
        candidates,
        key=lambda item: (
            int(item.get("combined_hits", 0)),
            int(item.get("score_hits", 0)),
            int(item.get("total_goals_hits", 0)),
            float(item.get("score_accuracy", 0.0)),
            float(item.get("total_goals_accuracy", 0.0)),
            -float(item.get("regular_same_outcome_min_confidence", 0.0)),
            -float(item.get("volatile_same_outcome_min_confidence", 0.0)),
            -float(item.get("regular_cross_outcome_min_confidence", 0.0)),
            -float(item.get("volatile_cross_outcome_min_confidence", 0.0)),
        ),
    )
    policy = json.loads(json.dumps(DEFAULT_PLAY_MODEL_POLICY))
    best_total_goals = {
        "min_confidence": float(best.get("total_goals_min_confidence", 0.24)),
        "hits": int(best.get("total_goals_hits", 0)),
        "covered": int(best.get("total_goals_covered", 0)),
        "accuracy": float(best.get("total_goals_accuracy", 0.0)),
        "takeover_enabled": bool(best.get("total_goals_takeover_enabled", False)),
    }
    policy["total_goals"]["min_confidence"] = float(best.get("total_goals_min_confidence", 0.24))
    policy["scoreline"]["takeover_enabled"] = True
    policy["scoreline"]["regular_same_outcome_min_confidence"] = float(best.get("regular_same_outcome_min_confidence", 0.07))
    policy["scoreline"]["regular_cross_outcome_enabled"] = bool(best.get("regular_cross_outcome_enabled", True))
    policy["scoreline"]["regular_cross_outcome_min_confidence"] = float(best.get("regular_cross_outcome_min_confidence", 0.11))
    policy["scoreline"]["volatile_same_outcome_min_confidence"] = float(best.get("volatile_same_outcome_min_confidence", 0.13))
    policy["scoreline"]["volatile_cross_outcome_enabled"] = bool(best.get("volatile_cross_outcome_enabled", False))
    policy["scoreline"]["volatile_cross_outcome_min_confidence"] = float(best.get("volatile_cross_outcome_min_confidence", 0.17))

    candidate_policy = json.loads(json.dumps(policy))
    candidate_policy["total_goals"]["takeover_enabled"] = bool(best_total_goals["takeover_enabled"])
    candidate_holdout_metrics = _play_model_policy_metrics(holdout_rows, candidate_policy) if holdout_rows else {}
    current_holdout_metrics = _play_model_policy_metrics(holdout_rows, current_policy) if holdout_rows else {}
    holdout_total_goals_uplift = (
        float(candidate_holdout_metrics.get("total_goals_accuracy", 0) or 0)
        - float(current_holdout_metrics.get("total_goals_accuracy", 0) or 0)
    ) if holdout_rows else None
    holdout_scoreline_delta = (
        float(candidate_holdout_metrics.get("score_accuracy", 0) or 0)
        - float(current_holdout_metrics.get("score_accuracy", 0) or 0)
    ) if holdout_rows else None
    current_total_goals_accuracy = current_total_goals_hits / max(current_total_goals_total, 1)
    total_goals_uplift = float(best_total_goals["accuracy"]) - current_total_goals_accuracy
    holdout_total_goals_passed = (
        True
        if holdout_total_goals_uplift is None
        else holdout_total_goals_uplift >= PLAY_MODEL_TOTAL_GOALS_MIN_HOLDOUT_UPLIFT
    )
    total_goals_takeover_allowed = bool(
        best_total_goals["takeover_enabled"]
        and int(best_total_goals["covered"]) > 0
        and current_total_goals_total > 0
        and total_goals_uplift >= PLAY_MODEL_TOTAL_GOALS_MIN_CALIBRATION_UPLIFT
        and holdout_total_goals_passed
    )
    if not bool(best_total_goals["takeover_enabled"]):
        total_goals_policy_reason = "candidate_disabled"
    elif not holdout_total_goals_passed:
        total_goals_policy_reason = "holdout_regression"
    elif total_goals_takeover_allowed:
        total_goals_policy_reason = "calibration_uplift_passed"
    else:
        total_goals_policy_reason = "insufficient_calibration_uplift"
    policy["total_goals"]["takeover_enabled"] = total_goals_takeover_allowed
    scoreline_holdout_passed = (
        True
        if holdout_scoreline_delta is None
        else holdout_scoreline_delta >= -PLAY_MODEL_SCORELINE_MAX_HOLDOUT_REGRESSION
    )
    policy["scoreline"]["takeover_enabled"] = bool(scoreline_holdout_passed)
    scoreline_policy_reason = "holdout_passed" if scoreline_holdout_passed else "holdout_regression"

    sample_dates = [
        normalize_text(item.get("meta", {}).get("match_date", ""))
        for item in validation_items
        if isinstance(item.get("meta"), dict)
    ]
    sample_dates = [item for item in sample_dates if item]
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history_items = _load_play_model_policy_history_entries()
    version_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(history_items) + 1:04d}"
    report = {
        "updated_at": updated_at,
        "version_id": version_id,
        "mode": "calibrated",
        "policy": policy,
        "previous_policy": previous_policy_report.get("policy", json.loads(json.dumps(DEFAULT_PLAY_MODEL_POLICY))),
        "validation": {
            "sample_count": len(rows),
            "tuning_sample_count": len(tuning_rows),
            "holdout_sample_count": len(holdout_rows),
            "date_start": min(sample_dates) if sample_dates else None,
            "date_end": max(sample_dates) if sample_dates else None,
            "ratio": round(len(validation_items) / max(len(train_items) + original_validation_count, 1), 4),
            "original_validation_count": original_validation_count,
            "max_validation_samples": max_validation_samples,
            "search_profile": resolved_search_profile,
            "candidate_count": len(candidates),
        },
        "metrics": {
            "scoreline_best": best,
            "scoreline_top_candidates": sorted(
                candidates,
                key=lambda item: (
                    -int(item.get("combined_hits", 0)),
                    -int(item.get("score_hits", 0)),
                    -int(item.get("total_goals_hits", 0)),
                ),
            )[:5],
            "scoreline": {
                "takeover_enabled": bool(policy["scoreline"]["takeover_enabled"]),
                "reason": scoreline_policy_reason,
                "holdout_delta": round(holdout_scoreline_delta, 6) if holdout_scoreline_delta is not None else None,
                "max_allowed_holdout_regression": PLAY_MODEL_SCORELINE_MAX_HOLDOUT_REGRESSION,
            },
            "holdout": {
                "sample_count": len(holdout_rows),
                "current": current_holdout_metrics,
                "candidate": candidate_holdout_metrics,
                "total_goals_uplift": round(holdout_total_goals_uplift, 6) if holdout_total_goals_uplift is not None else None,
                "scoreline_delta": round(holdout_scoreline_delta, 6) if holdout_scoreline_delta is not None else None,
            },
            "total_goals": {
                "current_hits": current_total_goals_hits,
                "current_total": current_total_goals_total,
                "current_accuracy": round(current_total_goals_accuracy, 6),
                "score_current_hits": current_score_hits,
                "score_current_total": current_score_total,
                "score_current_accuracy": round(current_score_hits / max(current_score_total, 1), 6),
                "best": best_total_goals,
                "takeover_enabled": bool(policy["total_goals"]["takeover_enabled"]),
                "uplift": round(total_goals_uplift, 6),
                "min_required_uplift": PLAY_MODEL_TOTAL_GOALS_MIN_CALIBRATION_UPLIFT,
                "holdout_uplift": round(holdout_total_goals_uplift, 6) if holdout_total_goals_uplift is not None else None,
                "min_required_holdout_uplift": PLAY_MODEL_TOTAL_GOALS_MIN_HOLDOUT_UPLIFT,
                "reason": total_goals_policy_reason,
            },
        },
    }
    _save_play_model_policy_report(report)
    _append_play_model_policy_history_entry(report, previous_policy_report, source="calibration")
    return {
        "calibrated": True,
        "reason": "ok",
        "version_id": version_id,
        "policy": policy,
        "validation": report["validation"],
        "metrics": report["metrics"],
        "status": get_play_model_policy_status(),
    }


def run_play_model_backtest(
    validation_ratio: float = 0.20,
    min_validation_samples: int = 1000,
    max_validation_samples: int = 1000,
    write_report: bool = True,
) -> dict:
    train_items, validation_items = _validation_split_samples(
        validation_ratio=validation_ratio,
        min_validation_samples=min_validation_samples,
    )
    if not validation_items:
        result = {
            "ok": False,
            "reason": "insufficient_validation_split",
            "validation": {"sample_count": 0},
            "improvement": {},
        }
        result["takeover_gate"] = evaluate_play_model_takeover_gate(result)
        return result
    original_validation_count = len(validation_items)
    if max_validation_samples > 0 and len(validation_items) > int(max_validation_samples):
        validation_items = validation_items[-int(max_validation_samples):]

    metrics = {
        "handicap_baseline": {"hits": 0, "total": 0},
        "handicap_current": {"hits": 0, "total": 0},
        "handicap_shadow": {"hits": 0, "total": 0},
        "total_goals_baseline": {"hits": 0, "total": 0},
        "total_goals_current": {"hits": 0, "total": 0},
        "total_goals_shadow": {"hits": 0, "total": 0},
        "total_goals_model": {"hits": 0, "total": 0},
        "score_baseline": {"hits": 0, "total": 0},
        "score_current": {"hits": 0, "total": 0},
        "score_shadow": {"hits": 0, "total": 0},
        "score_model": {"hits": 0, "total": 0},
        "score_volatile_model": {"hits": 0, "total": 0},
        "score_current_regular": {"hits": 0, "total": 0},
        "score_current_volatile": {"hits": 0, "total": 0},
        "score_model_regular": {"hits": 0, "total": 0},
        "score_model_volatile": {"hits": 0, "total": 0},
        "score_volatile_model_volatile": {"hits": 0, "total": 0},
    }

    for item in validation_items:
        prediction = _sample_item_prediction(item)
        meta = item.get("meta", {}) if isinstance(item.get("meta"), dict) else {}
        if not isinstance(prediction, dict) or not isinstance(meta, dict):
            continue
        home_goals = _safe_int(meta.get("home_goals"))
        away_goals = _safe_int(meta.get("away_goals"))
        if home_goals is None or away_goals is None:
            continue
        actual_score = f"{int(home_goals)}-{int(away_goals)}"
        actual_total_goals = int(home_goals) + int(away_goals)
        handicap_line = _safe_float(meta.get("handicap_line"), default=0.0)
        actual_handicap = _handicap_label_from_key(_handicap_outcome_key(int(home_goals), int(away_goals), handicap_line))

        baseline_handicap = _poisson_baseline_handicap_prediction(prediction, handicap_line)
        current_handicap = str(prediction.get("handicap_recommendation", "")).strip() or None
        shadow_handicap_probs = prediction.get("handicap_specialist_probabilities", {})
        shadow_handicap = None
        if isinstance(shadow_handicap_probs, dict) and shadow_handicap_probs:
            shadow_key = max(
                ("home", "draw", "away"),
                key=lambda key: _safe_float(shadow_handicap_probs.get(key), default=0.0),
            )
            shadow_handicap = _handicap_label_from_key(shadow_key)

        poisson = prediction.get("poisson", {}) if isinstance(prediction.get("poisson"), dict) else {}
        top_total_goals = poisson.get("top_total_goals", [])
        baseline_total_goals = None
        if isinstance(top_total_goals, list) and top_total_goals:
            baseline_total_goals = _safe_int(top_total_goals[0].get("goals"))
        _, current_total_goals, _ = _extract_total_goals_prediction(prediction)
        shadow_total_goals = _parse_total_goals_from_score_text(prediction.get("score_specialist_candidate"))
        model_total_goals = _model_total_goals_pick(prediction)

        top_scores = poisson.get("top_scores", [])
        baseline_score = None
        if isinstance(top_scores, list) and top_scores:
            baseline_score = str(top_scores[0].get("score", "")).strip() or None
        current_score, _ = _extract_score_prediction(prediction)
        shadow_score = str(prediction.get("score_specialist_candidate", "")).strip() or None
        model_score = _model_scoreline_pick(prediction)
        volatile_model_output = prediction.get("volatile_scoreline_model", {}) if isinstance(prediction, dict) else {}
        volatile_model_score = None
        if isinstance(volatile_model_output, dict) and volatile_model_output.get("model_ready"):
            candidate_label = str(volatile_model_output.get("label", "")).strip()
            if candidate_label and candidate_label != "OTHER":
                volatile_model_score = candidate_label

        _record_play_backtest_hit(metrics["handicap_baseline"], baseline_handicap, actual_handicap)
        _record_play_backtest_hit(metrics["handicap_current"], current_handicap, actual_handicap)
        _record_play_backtest_hit(metrics["handicap_shadow"], shadow_handicap, actual_handicap)
        _record_play_backtest_hit(metrics["total_goals_baseline"], baseline_total_goals, actual_total_goals)
        _record_play_backtest_hit(metrics["total_goals_current"], current_total_goals, actual_total_goals)
        _record_play_backtest_hit(metrics["total_goals_shadow"], shadow_total_goals, actual_total_goals)
        _record_play_backtest_hit(metrics["total_goals_model"], model_total_goals, actual_total_goals)
        _record_play_backtest_hit(metrics["score_baseline"], baseline_score, actual_score)
        _record_play_backtest_hit(metrics["score_current"], current_score, actual_score)
        _record_play_backtest_hit(metrics["score_shadow"], shadow_score, actual_score)
        _record_play_backtest_hit(metrics["score_model"], model_score, actual_score)
        _record_play_backtest_hit(metrics["score_volatile_model"], volatile_model_score, actual_score)
        if current_score:
            _record_play_backtest_hit(
                metrics[f"score_current_{_scoreline_bucket(current_score)}"],
                current_score,
                actual_score,
            )
        if model_score:
            _record_play_backtest_hit(
                metrics[f"score_model_{_scoreline_bucket(model_score)}"],
                model_score,
                actual_score,
            )
        if volatile_model_score and _scoreline_bucket(volatile_model_score) == "volatile":
            _record_play_backtest_hit(
                metrics["score_volatile_model_volatile"],
                volatile_model_score,
                actual_score,
            )

    finalized = {key: _finalize_play_backtest_bucket(value) for key, value in metrics.items()}
    improvement = {
        "handicap_shadow_delta": round(
            float(finalized["handicap_shadow"]["accuracy"]) - float(finalized["handicap_current"]["accuracy"]),
            6,
        ),
        "total_goals_shadow_delta": round(
            float(finalized["total_goals_shadow"]["accuracy"]) - float(finalized["total_goals_current"]["accuracy"]),
            6,
        ),
        "total_goals_model_delta": round(
            float(finalized["total_goals_model"]["accuracy"]) - float(finalized["total_goals_current"]["accuracy"]),
            6,
        ),
        "score_shadow_delta": round(
            float(finalized["score_shadow"]["accuracy"]) - float(finalized["score_current"]["accuracy"]),
            6,
        ),
        "score_model_delta": round(
            float(finalized["score_model"]["accuracy"]) - float(finalized["score_current"]["accuracy"]),
            6,
        ),
    }
    dates = [
        normalize_text(item.get("meta", {}).get("match_date", ""))
        for item in validation_items
        if isinstance(item.get("meta"), dict)
    ]
    dates = [item for item in dates if item]
    result = {
        "ok": True,
        "reason": "ok",
        "validation": {
            "sample_count": len(validation_items),
            "original_sample_count": original_validation_count,
            "max_validation_samples": int(max_validation_samples),
            "truncated": len(validation_items) < original_validation_count,
            "date_start": min(dates) if dates else None,
            "date_end": max(dates) if dates else None,
            "ratio": round(len(validation_items) / max(len(train_items) + original_validation_count, 1), 4),
        },
        "metrics": finalized,
        "improvement": improvement,
    }
    result["takeover_gate"] = evaluate_play_model_takeover_gate(result)

    report_path = None
    if write_report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = REPORT_DIR / f"play_model_backtest_{timestamp}.md"
        result["report_path"] = str(report_path)
        takeover_gate = result.get("takeover_gate", {}) if isinstance(result.get("takeover_gate"), dict) else {}
        takeover_gate_metrics = takeover_gate.get("metrics", {}) if isinstance(takeover_gate.get("metrics"), dict) else {}
        takeover_gate_issues = takeover_gate.get("issues", []) if isinstance(takeover_gate.get("issues"), list) else []
        lines = [
            "# Play Model Backtest Report",
            "",
            f"- Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- Validation Samples: {result['validation']['sample_count']}",
            f"- Validation Window: {result['validation']['date_start']} -> {result['validation']['date_end']}",
            "",
            "| Play | Scheme | Hits | Total | Accuracy |",
            "|---|---|---:|---:|---:|",
        ]
        for play_name, prefix in (("Handicap", "handicap"), ("Total Goals", "total_goals"), ("Score", "score")):
            scheme_rows = [("Baseline", f"{prefix}_baseline"), ("Current", f"{prefix}_current"), ("Shadow", f"{prefix}_shadow")]
            if prefix in {"total_goals", "score"}:
                scheme_rows.append(("Model", f"{prefix}_model"))
            if prefix == "score":
                scheme_rows.append(("Volatile Model", "score_volatile_model"))
            for scheme_name, key in scheme_rows:
                item = finalized.get(key, {})
                lines.append(
                    f"| {play_name} | {scheme_name} | {int(item.get('hits', 0) or 0)} | {int(item.get('total', 0) or 0)} | {float(item.get('accuracy', 0) or 0):.2%} |"
                )
        lines.extend(
            [
                "",
                "## Shadow Delta",
                "",
                f"- Handicap Shadow - Current: {improvement['handicap_shadow_delta']:+.2%}",
                f"- Total Goals Shadow - Current: {improvement['total_goals_shadow_delta']:+.2%}",
                f"- Total Goals Model - Current: {improvement['total_goals_model_delta']:+.2%}",
                f"- Score Shadow - Current: {improvement['score_shadow_delta']:+.2%}",
                f"- Score Model - Current: {improvement['score_model_delta']:+.2%}",
                "",
                "## Takeover Gate",
                "",
                f"- Status: {takeover_gate.get('status') or '-'}",
                f"- Mode: {takeover_gate.get('mode') or '-'}",
                f"- Policy Impact: {takeover_gate.get('policy_impact') or '-'}",
                f"- Training Gate: {takeover_gate_metrics.get('training_gate_status') or '-'}",
                f"- Validation Samples: {takeover_gate_metrics.get('validation_sample_count', 0)}/{takeover_gate_metrics.get('min_validation_samples', 0)}",
                f"- Total Goals Delta: {float(takeover_gate_metrics.get('total_goals_model_delta', 0) or 0):+.2%}",
                f"- Score Model Delta: {float(takeover_gate_metrics.get('score_model_delta', 0) or 0):+.2%}",
                f"- Recommendation: {takeover_gate.get('recommendation') or '-'}",
                "",
                "| Severity | Code | Message |",
                "|---|---|---|",
                *[
                    f"| {item.get('severity', '-')} | {item.get('code', '-')} | {item.get('message', '-')} |"
                    for item in takeover_gate_issues[:5]
                    if isinstance(item, dict)
                ],
                "",
                "## Scoreline Buckets",
                "",
                f"- Current Regular: {int(finalized['score_current_regular']['hits'])}/{int(finalized['score_current_regular']['total'])} ({float(finalized['score_current_regular']['accuracy']):.2%})",
                f"- Current Volatile: {int(finalized['score_current_volatile']['hits'])}/{int(finalized['score_current_volatile']['total'])} ({float(finalized['score_current_volatile']['accuracy']):.2%})",
                f"- Model Regular: {int(finalized['score_model_regular']['hits'])}/{int(finalized['score_model_regular']['total'])} ({float(finalized['score_model_regular']['accuracy']):.2%})",
                f"- Model Volatile: {int(finalized['score_model_volatile']['hits'])}/{int(finalized['score_model_volatile']['total'])} ({float(finalized['score_model_volatile']['accuracy']):.2%})",
                f"- Volatile Model Volatile: {int(finalized['score_volatile_model_volatile']['hits'])}/{int(finalized['score_volatile_model_volatile']['total'])} ({float(finalized['score_volatile_model_volatile']['accuracy']):.2%})",
            ]
        )
        report_path.write_text("\n".join(lines), encoding="utf-8")
        _save_play_model_takeover_gate_snapshot(takeover_gate, result)
    result["report_path"] = str(report_path) if report_path else None
    return result


def _draw_prediction_key(prediction: dict | None) -> str | None:
    key = _prediction_recommendation_key(prediction)
    if key in {"home", "draw", "away"}:
        return key
    if not isinstance(prediction, dict):
        return None
    recommendation = normalize_text(prediction.get("recommendation", "")).lower()
    if recommendation in {"draw", "平局", "骞冲眬"} or "平" in recommendation:
        return "draw"
    if recommendation in {"home", "主胜", "涓昏儨"} or "主" in recommendation:
        return "home"
    if recommendation in {"away", "客胜", "瀹㈣儨"} or "客" in recommendation:
        return "away"
    return None


def _draw_score_bucket(score: object) -> str:
    value = _safe_float(score, default=0.0)
    if value >= 0.72:
        return ">=0.72 博平"
    if value >= 0.58:
        return "0.58-0.72 防平"
    if value >= 0.50:
        return "0.50-0.58 观察"
    return "<0.50 弱信号"


def _draw_odds_bucket(value: object) -> str:
    odds = _safe_float(value, default=0.0)
    if odds <= 0.0:
        return "unknown"
    if odds <= 3.00:
        return "<=3.00"
    if odds <= 3.30:
        return "3.01-3.30"
    if odds <= 3.70:
        return "3.31-3.70"
    if odds <= 4.20:
        return "3.71-4.20"
    return ">4.20"


def _draw_handicap_bucket(value: object) -> str:
    line = abs(_safe_float(value, default=0.0))
    if line <= 0.05:
        return "平手"
    if line <= 0.25:
        return "<=0.25"
    if line <= 0.75:
        return "0.50-0.75"
    return ">=1.00"


def _draw_expected_goals_bucket(value: object) -> str:
    goals = _safe_float(value, default=0.0)
    if goals <= 0.0:
        return "unknown"
    if goals <= 2.20:
        return "<=2.20"
    if goals <= 2.60:
        return "2.21-2.60"
    if goals <= 3.00:
        return "2.61-3.00"
    return ">3.00"


def _draw_market_balance_bucket(value: object) -> str:
    score = _safe_float(value, default=0.0)
    if score >= 0.80:
        return ">=0.80 均衡"
    if score >= 0.65:
        return "0.65-0.80"
    if score >= 0.45:
        return "0.45-0.65"
    return "<0.45 倾斜"


def _normalize_draw_release_guard_policy(policy: dict | None) -> dict[str, object]:
    raw = policy if isinstance(policy, dict) else {}
    normalized = json.loads(json.dumps(DEFAULT_DRAW_RELEASE_GUARD_POLICY))
    if "enabled" in raw:
        normalized["enabled"] = bool(raw.get("enabled"))
    if raw.get("min_score") is not None:
        normalized["min_score"] = round(min(0.85, max(0.50, _safe_float(raw.get("min_score"), default=0.58))), 2)
    if isinstance(raw.get("weak_odds_buckets"), dict):
        buckets: dict[str, dict[str, object]] = {}
        for bucket, evidence in raw.get("weak_odds_buckets", {}).items():
            if not isinstance(evidence, dict):
                continue
            key = normalize_text(bucket)
            if key:
                buckets[key] = dict(evidence)
        normalized["weak_odds_buckets"] = buckets
    return normalized


def _current_draw_release_guard_policy() -> dict[str, object]:
    try:
        mtime = DRAW_RELEASE_GUARD_POLICY_FILE.stat().st_mtime
    except FileNotFoundError:
        _DRAW_RELEASE_GUARD_POLICY_CACHE["mtime"] = None
        _DRAW_RELEASE_GUARD_POLICY_CACHE["policy"] = json.loads(json.dumps(DEFAULT_DRAW_RELEASE_GUARD_POLICY))
        _DRAW_RELEASE_GUARD_POLICY_CACHE["report"] = {"mode": "default", "reason": "missing_policy_file"}
        return json.loads(json.dumps(DEFAULT_DRAW_RELEASE_GUARD_POLICY))
    except OSError as exc:
        _DRAW_RELEASE_GUARD_POLICY_CACHE["report"] = {"mode": "default", "reason": str(exc)}
        return json.loads(json.dumps(DEFAULT_DRAW_RELEASE_GUARD_POLICY))
    if _DRAW_RELEASE_GUARD_POLICY_CACHE.get("mtime") == mtime:
        return json.loads(json.dumps(_DRAW_RELEASE_GUARD_POLICY_CACHE.get("policy") or DEFAULT_DRAW_RELEASE_GUARD_POLICY))
    try:
        raw = json.loads(DRAW_RELEASE_GUARD_POLICY_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        _DRAW_RELEASE_GUARD_POLICY_CACHE["mtime"] = mtime
        _DRAW_RELEASE_GUARD_POLICY_CACHE["policy"] = json.loads(json.dumps(DEFAULT_DRAW_RELEASE_GUARD_POLICY))
        _DRAW_RELEASE_GUARD_POLICY_CACHE["report"] = {"mode": "default", "reason": str(exc)}
        return json.loads(json.dumps(DEFAULT_DRAW_RELEASE_GUARD_POLICY))
    policy = json.loads(json.dumps(DEFAULT_DRAW_RELEASE_GUARD_POLICY))
    if isinstance(raw, dict):
        raw_policy = raw.get("policy") if isinstance(raw.get("policy"), dict) else raw
        if isinstance(raw_policy, dict):
            policy = _normalize_draw_release_guard_policy(raw_policy)
    _DRAW_RELEASE_GUARD_POLICY_CACHE["mtime"] = mtime
    _DRAW_RELEASE_GUARD_POLICY_CACHE["policy"] = json.loads(json.dumps(policy))
    _DRAW_RELEASE_GUARD_POLICY_CACHE["report"] = raw if isinstance(raw, dict) else {}
    return policy


def get_draw_release_guard_policy_status() -> dict:
    policy = _current_draw_release_guard_policy()
    report = _DRAW_RELEASE_GUARD_POLICY_CACHE.get("report")
    report = report if isinstance(report, dict) else {}
    return {
        "enabled": bool(policy.get("enabled", True)),
        "active": bool(policy.get("enabled", True)),
        "status": "active" if bool(policy.get("enabled", True)) else "disabled",
        "mode": str(report.get("mode") or ("file" if DRAW_RELEASE_GUARD_POLICY_FILE.exists() else "default")),
        "updated_at": report.get("updated_at"),
        "version_id": report.get("version_id"),
        "reason": report.get("reason") or report.get("source") or "-",
        "source": str(DRAW_RELEASE_GUARD_POLICY_FILE),
        "policy": json.loads(json.dumps(policy)),
        "previous_policy": report.get("previous_policy", {}) if isinstance(report.get("previous_policy"), dict) else {},
    }


def _load_draw_release_guard_policy_history_entries() -> list[dict]:
    if not DRAW_RELEASE_GUARD_POLICY_HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(DRAW_RELEASE_GUARD_POLICY_HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items if isinstance(item, dict)]


def _write_draw_release_guard_policy_history_entries(items: list[dict]) -> None:
    DRAW_RELEASE_GUARD_POLICY_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": items[-200:],
    }
    DRAW_RELEASE_GUARD_POLICY_HISTORY_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_draw_release_guard_policy_history(*, limit: int = 20) -> list[dict]:
    items = _load_draw_release_guard_policy_history_entries()
    items.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("version_id") or "")), reverse=True)
    if limit <= 0:
        return items
    return items[: max(0, int(limit))]


def apply_draw_release_guard_policy_update(update: dict, *, source: str = "draw_release_guard_tuning") -> dict:
    current = get_draw_release_guard_policy_status()
    policy = dict(current.get("policy") if isinstance(current.get("policy"), dict) else DEFAULT_DRAW_RELEASE_GUARD_POLICY)
    raw_update = update.get("policy") if isinstance(update, dict) and isinstance(update.get("policy"), dict) else update
    if isinstance(raw_update, dict):
        policy.update(raw_update)
    normalized = _normalize_draw_release_guard_policy(policy)
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history_items = _load_draw_release_guard_policy_history_entries()
    version_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(history_items) + 1:04d}"
    report = {
        "enabled": True,
        "active": bool(normalized.get("enabled", True)),
        "status": "active" if bool(normalized.get("enabled", True)) else "disabled",
        "mode": "manual",
        "updated_at": updated_at,
        "version_id": version_id,
        "reason": str(source or "draw_release_guard_tuning"),
        "source": str(source or "draw_release_guard_tuning"),
        "policy": normalized,
        "previous_policy": current.get("policy", {}),
        "update": dict(raw_update) if isinstance(raw_update, dict) else {},
    }
    DRAW_RELEASE_GUARD_POLICY_FILE.parent.mkdir(parents=True, exist_ok=True)
    DRAW_RELEASE_GUARD_POLICY_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    history_items.append(
        {
            "version_id": version_id,
            "updated_at": updated_at,
            "source": str(source or "draw_release_guard_tuning"),
            "policy": normalized,
            "previous_policy": current.get("policy", {}),
            "update": dict(raw_update) if isinstance(raw_update, dict) else {},
        }
    )
    _write_draw_release_guard_policy_history_entries(history_items)
    try:
        _DRAW_RELEASE_GUARD_POLICY_CACHE["mtime"] = DRAW_RELEASE_GUARD_POLICY_FILE.stat().st_mtime
    except OSError:
        _DRAW_RELEASE_GUARD_POLICY_CACHE["mtime"] = None
    _DRAW_RELEASE_GUARD_POLICY_CACHE["policy"] = json.loads(json.dumps(normalized))
    _DRAW_RELEASE_GUARD_POLICY_CACHE["report"] = dict(report)
    return get_draw_release_guard_policy_status()


def rollback_draw_release_guard_policy(*, version_id: str | None = None, source: str = "draw_guard_policy_rollback") -> dict:
    history_items = get_draw_release_guard_policy_history(limit=0)
    if not history_items:
        return get_draw_release_guard_policy_status()
    target: dict | None = None
    rollback_source = str(source or "draw_guard_policy_rollback")
    if version_id:
        target_entry = next((item for item in history_items if str(item.get("version_id") or "") == str(version_id)), None)
        if isinstance(target_entry, dict):
            policy = target_entry.get("policy")
            if isinstance(policy, dict):
                target = dict(policy)
                rollback_source = f"{rollback_source}:{version_id}"
    else:
        latest = history_items[0]
        previous = latest.get("previous_policy")
        if isinstance(previous, dict):
            target = dict(previous)
            rollback_source = f"{rollback_source}:{latest.get('version_id', '-')}"
    if not target:
        return get_draw_release_guard_policy_status()
    return apply_draw_release_guard_policy_update(target, source=rollback_source)


def _draw_release_guard(match: AppMatch, draw_score: object, *, base_takeover: bool = False) -> dict[str, object]:
    policy = _current_draw_release_guard_policy()
    min_score = _safe_float(policy.get("min_score"), default=0.58)
    weak_odds_buckets = policy.get("weak_odds_buckets") if isinstance(policy.get("weak_odds_buckets"), dict) else {}
    odds_bucket = _draw_odds_bucket(getattr(match, "odds_draw", 0.0))
    evidence = weak_odds_buckets.get(odds_bucket) if bool(policy.get("enabled", True)) else None
    evidence = evidence if isinstance(evidence, dict) else {}
    weak_score = bool(evidence and _safe_float(draw_score, default=0.0) >= min_score)
    blocked = bool(base_takeover and weak_score)
    return {
        "blocked": blocked,
        "reason": "weak_draw_odds_bucket" if blocked else "ok",
        "weak_score": weak_score,
        "base_takeover": bool(base_takeover),
        "odds_bucket": odds_bucket,
        "odds_draw": round(_safe_float(getattr(match, "odds_draw", 0.0), default=0.0), 3),
        "min_score": min_score,
        "evidence": dict(evidence or {}),
    }


def _draw_takeover_decision(
    match: AppMatch,
    *,
    probabilities: dict[str, float],
    draw_score: object,
    draw_signals: dict[str, float],
) -> tuple[bool, dict[str, object]]:
    score = _safe_float(draw_score, default=0.0)
    base_takeover = bool(
        score >= 0.54
        and (
            probabilities["draw"] >= max(probabilities["home"], probabilities["away"]) - 0.08
            or (
                probabilities["draw"] >= 0.28
                and draw_signals.get("market_balance", 0.0) >= 0.72
                and draw_signals.get("low_goal", 0.0) >= 0.55
            )
        )
    )
    guard = _draw_release_guard(match, score, base_takeover=base_takeover)
    if base_takeover and guard.get("blocked"):
        return False, guard
    return base_takeover, guard


def _draw_bucket_template() -> dict[str, int]:
    return {
        "sample_count": 0,
        "actual_draw_count": 0,
        "predicted_draw_count": 0,
        "draw_hit_count": 0,
        "false_positive_count": 0,
        "missed_draw_count": 0,
    }


def _draw_bucket_record(bucket: dict[str, int], *, actual_draw: bool, predicted_draw: bool) -> None:
    bucket["sample_count"] += 1
    if actual_draw:
        bucket["actual_draw_count"] += 1
    if predicted_draw:
        bucket["predicted_draw_count"] += 1
    if actual_draw and predicted_draw:
        bucket["draw_hit_count"] += 1
    elif predicted_draw and not actual_draw:
        bucket["false_positive_count"] += 1
    elif actual_draw and not predicted_draw:
        bucket["missed_draw_count"] += 1


def _finalize_draw_bucket(name: str, bucket: dict[str, int], *, baseline_draw_rate: float) -> dict[str, object]:
    sample_count = int(bucket.get("sample_count", 0) or 0)
    actual_draw_count = int(bucket.get("actual_draw_count", 0) or 0)
    predicted_draw_count = int(bucket.get("predicted_draw_count", 0) or 0)
    draw_hit_count = int(bucket.get("draw_hit_count", 0) or 0)
    precision = draw_hit_count / predicted_draw_count if predicted_draw_count else None
    recall = draw_hit_count / actual_draw_count if actual_draw_count else None
    draw_rate = actual_draw_count / sample_count if sample_count else None
    lift = (draw_rate - baseline_draw_rate) if draw_rate is not None else None
    return {
        "bucket": name,
        "sample_count": sample_count,
        "actual_draw_count": actual_draw_count,
        "predicted_draw_count": predicted_draw_count,
        "draw_hit_count": draw_hit_count,
        "false_positive_count": int(bucket.get("false_positive_count", 0) or 0),
        "missed_draw_count": int(bucket.get("missed_draw_count", 0) or 0),
        "precision": round(precision, 6) if precision is not None else None,
        "precision_text": f"{precision:.1%}" if precision is not None else "-",
        "recall": round(recall, 6) if recall is not None else None,
        "recall_text": f"{recall:.1%}" if recall is not None else "-",
        "draw_rate": round(draw_rate, 6) if draw_rate is not None else None,
        "draw_rate_text": f"{draw_rate:.1%}" if draw_rate is not None else "-",
        "lift": round(lift, 6) if lift is not None else None,
        "lift_text": f"{lift:+.1%}" if lift is not None else "-",
    }


def _draw_bucket_rows(buckets: dict[str, dict[str, int]], *, baseline_draw_rate: float, limit: int = 12) -> list[dict[str, object]]:
    rows = [
        _finalize_draw_bucket(name, bucket, baseline_draw_rate=baseline_draw_rate)
        for name, bucket in buckets.items()
    ]
    rows.sort(
        key=lambda item: (
            -int(item.get("sample_count", 0) or 0),
            -_safe_float(item.get("lift"), default=-9.0),
            str(item.get("bucket") or ""),
        )
    )
    return rows[: max(0, int(limit))]


def _draw_sample_row(
    item: dict,
    prediction: dict,
    *,
    actual_key: str,
    predicted_key: str | None,
) -> dict[str, object]:
    meta = item.get("meta", {}) if isinstance(item.get("meta"), dict) else {}
    probabilities = prediction.get("probabilities", {}) if isinstance(prediction.get("probabilities"), dict) else {}
    draw_signals = prediction.get("draw_signals", {}) if isinstance(prediction.get("draw_signals"), dict) else {}
    return {
        "match_id": str(item.get("match_id") or ""),
        "match_date": normalize_text(meta.get("match_date", "")),
        "league": normalize_text(meta.get("league", "")) or "-",
        "home_team": normalize_text(meta.get("home_team", "")) or "-",
        "away_team": normalize_text(meta.get("away_team", "")) or "-",
        "score": f"{_safe_int(meta.get('home_goals'), 0)}-{_safe_int(meta.get('away_goals'), 0)}",
        "actual": actual_key,
        "predicted": predicted_key or "-",
        "draw_score": round(_safe_float(prediction.get("draw_score"), default=0.0), 4),
        "draw_probability": round(_safe_float(probabilities.get("draw"), default=0.0), 4),
        "market_balance": round(_safe_float(draw_signals.get("market_balance"), default=0.0), 4),
        "expected_goals": round(_safe_float(prediction.get("expected_goals"), default=0.0), 3),
        "draw_grade": prediction.get("draw_grade", "-"),
        "draw_takeover": bool(prediction.get("draw_takeover")),
    }


def _save_draw_specialist_backtest_report(report: dict) -> None:
    DRAW_SPECIALIST_BACKTEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    DRAW_SPECIALIST_BACKTEST_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def get_draw_specialist_backtest_status() -> dict:
    if not DRAW_SPECIALIST_BACKTEST_FILE.exists():
        return {"ok": False, "reason": "not_run", "updated_at": None, "validation": {}, "summary": {}, "source": str(DRAW_SPECIALIST_BACKTEST_FILE)}
    try:
        payload = json.loads(DRAW_SPECIALIST_BACKTEST_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"ok": False, "reason": "invalid_report", "updated_at": None, "validation": {}, "summary": {}, "source": str(DRAW_SPECIALIST_BACKTEST_FILE)}
    if not isinstance(payload, dict):
        payload = {}
    payload["source"] = str(DRAW_SPECIALIST_BACKTEST_FILE)
    return payload


def _write_draw_specialist_backtest_markdown(result: dict) -> str | None:
    if not result.get("ok"):
        return None
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"draw_specialist_backtest_{timestamp}.md"
    summary = result.get("summary", {}) if isinstance(result.get("summary"), dict) else {}
    validation = result.get("validation", {}) if isinstance(result.get("validation"), dict) else {}
    guard_policy = result.get("draw_release_guard_policy") if isinstance(result.get("draw_release_guard_policy"), dict) else {}
    if not guard_policy and isinstance(summary.get("draw_release_guard_policy"), dict):
        guard_policy = summary.get("draw_release_guard_policy", {})
    weak_odds_buckets = guard_policy.get("weak_odds_buckets") if isinstance(guard_policy.get("weak_odds_buckets"), dict) else {}
    lines = [
        "# Draw Specialist Backtest",
        "",
        f"- Generated At: {result.get('updated_at') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Samples: {validation.get('sample_count', 0)}",
        f"- Window: {validation.get('date_start') or '-'} -> {validation.get('date_end') or '-'}",
        f"- Actual Draw Rate: {summary.get('actual_draw_rate_text', '-')}",
        f"- Draw Precision: {summary.get('precision_text', '-')}",
        f"- Draw Recall: {summary.get('recall_text', '-')}",
        f"- Recommendation: {summary.get('recommendation', '-')}",
        f"- Draw Release Guard: active={bool(guard_policy.get('enabled', True))}, score_floor={_safe_float(guard_policy.get('min_score'), 0.0):.2f}, blocked_odds={', '.join(sorted(str(key) for key in weak_odds_buckets)) or '-'}",
        "",
        "## Score Buckets",
        "",
        "| Bucket | Samples | Draw Rate | Lift | Pred Draw | Precision | Recall |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    score_buckets = result.get("score_buckets", []) if isinstance(result.get("score_buckets"), list) else []
    for row in score_buckets:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"| {row.get('bucket', '-')} | {row.get('sample_count', 0)} | {row.get('draw_rate_text', '-')} | "
            f"{row.get('lift_text', '-')} | {row.get('predicted_draw_count', 0)} | {row.get('precision_text', '-')} | {row.get('recall_text', '-')} |"
        )
    lines.extend(["", "## Missed Draw Samples", ""])
    for row in result.get("missed_draw_rows", []) if isinstance(result.get("missed_draw_rows"), list) else []:
        if isinstance(row, dict):
            lines.append(
                f"- {row.get('match_date', '-')} {row.get('league', '-')} {row.get('home_team', '-')} vs {row.get('away_team', '-')}: "
                f"pred={row.get('predicted', '-')} draw_score={row.get('draw_score', '-')}, draw_prob={row.get('draw_probability', '-')}"
            )
    lines.extend(["", "## False Positive Draw Samples", ""])
    for row in result.get("false_positive_rows", []) if isinstance(result.get("false_positive_rows"), list) else []:
        if isinstance(row, dict):
            lines.append(
                f"- {row.get('match_date', '-')} {row.get('league', '-')} {row.get('home_team', '-')} vs {row.get('away_team', '-')}: "
                f"score={row.get('score', '-')} draw_score={row.get('draw_score', '-')}, draw_prob={row.get('draw_probability', '-')}"
            )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return str(report_path)


def run_draw_specialist_backtest(
    validation_ratio: float = 0.20,
    min_validation_samples: int = 300,
    max_validation_samples: int = 300,
    write_report: bool = True,
) -> dict:
    train_items, validation_items = _validation_split_samples(
        validation_ratio=validation_ratio,
        min_validation_samples=min_validation_samples,
    )
    if not validation_items:
        return {"ok": False, "reason": "insufficient_validation_split", "validation": {}, "summary": {}}
    original_validation_count = len(validation_items)
    if max_validation_samples > 0 and len(validation_items) > int(max_validation_samples):
        validation_items = validation_items[-int(max_validation_samples):]

    draw_release_guard_policy = _current_draw_release_guard_policy()
    draw_guard_min_score = _safe_float(draw_release_guard_policy.get("min_score"), default=0.58)
    totals = _draw_bucket_template()
    guard_bucket = _draw_bucket_template()
    takeover_bucket = _draw_bucket_template()
    score_buckets: dict[str, dict[str, int]] = defaultdict(_draw_bucket_template)
    odds_buckets: dict[str, dict[str, int]] = defaultdict(_draw_bucket_template)
    handicap_buckets: dict[str, dict[str, int]] = defaultdict(_draw_bucket_template)
    expected_goal_buckets: dict[str, dict[str, int]] = defaultdict(_draw_bucket_template)
    market_balance_buckets: dict[str, dict[str, int]] = defaultdict(_draw_bucket_template)
    missed_draw_rows: list[dict[str, object]] = []
    false_positive_rows: list[dict[str, object]] = []
    skipped = 0
    dates: list[str] = []

    for item in validation_items:
        prediction = _sample_item_prediction(item)
        meta = item.get("meta", {}) if isinstance(item.get("meta"), dict) else {}
        features = item.get("features", {}) if isinstance(item.get("features"), dict) else {}
        if not isinstance(prediction, dict) or not isinstance(meta, dict):
            skipped += 1
            continue
        home_goals = _safe_int(meta.get("home_goals"))
        away_goals = _safe_int(meta.get("away_goals"))
        if home_goals is None or away_goals is None:
            skipped += 1
            continue
        match_date = normalize_text(meta.get("match_date", ""))
        if match_date:
            dates.append(match_date)
        actual_key = "draw" if int(home_goals) == int(away_goals) else "home" if int(home_goals) > int(away_goals) else "away"
        predicted_key = _draw_prediction_key(prediction)
        actual_draw = actual_key == "draw"
        predicted_draw = predicted_key == "draw"
        draw_score = _safe_float(prediction.get("draw_score"), default=0.0)
        draw_signals = prediction.get("draw_signals", {}) if isinstance(prediction.get("draw_signals"), dict) else {}
        expected_goals = _safe_float(prediction.get("expected_goals"), default=0.0)
        market_balance = _safe_float(draw_signals.get("market_balance"), default=0.0)

        _draw_bucket_record(totals, actual_draw=actual_draw, predicted_draw=predicted_draw)
        if draw_score >= draw_guard_min_score:
            _draw_bucket_record(guard_bucket, actual_draw=actual_draw, predicted_draw=predicted_draw)
        if bool(prediction.get("draw_takeover")):
            _draw_bucket_record(takeover_bucket, actual_draw=actual_draw, predicted_draw=predicted_draw)
        bucket_keys = {
            "score": _draw_score_bucket(draw_score),
            "odds": _draw_odds_bucket(features.get("odds_draw", meta.get("odds_draw"))),
            "handicap": _draw_handicap_bucket(meta.get("handicap_line", features.get("handicap_line"))),
            "expected_goals": _draw_expected_goals_bucket(expected_goals),
            "market_balance": _draw_market_balance_bucket(market_balance),
        }
        _draw_bucket_record(score_buckets[bucket_keys["score"]], actual_draw=actual_draw, predicted_draw=predicted_draw)
        _draw_bucket_record(odds_buckets[bucket_keys["odds"]], actual_draw=actual_draw, predicted_draw=predicted_draw)
        _draw_bucket_record(handicap_buckets[bucket_keys["handicap"]], actual_draw=actual_draw, predicted_draw=predicted_draw)
        _draw_bucket_record(expected_goal_buckets[bucket_keys["expected_goals"]], actual_draw=actual_draw, predicted_draw=predicted_draw)
        _draw_bucket_record(market_balance_buckets[bucket_keys["market_balance"]], actual_draw=actual_draw, predicted_draw=predicted_draw)
        if actual_draw and not predicted_draw:
            missed_draw_rows.append(_draw_sample_row(item, prediction, actual_key=actual_key, predicted_key=predicted_key))
        elif predicted_draw and not actual_draw:
            false_positive_rows.append(_draw_sample_row(item, prediction, actual_key=actual_key, predicted_key=predicted_key))

    sample_count = int(totals.get("sample_count", 0) or 0)
    actual_draw_count = int(totals.get("actual_draw_count", 0) or 0)
    predicted_draw_count = int(totals.get("predicted_draw_count", 0) or 0)
    draw_hit_count = int(totals.get("draw_hit_count", 0) or 0)
    precision = draw_hit_count / predicted_draw_count if predicted_draw_count else None
    recall = draw_hit_count / actual_draw_count if actual_draw_count else None
    actual_draw_rate = actual_draw_count / sample_count if sample_count else None
    baseline_draw_rate = actual_draw_rate or 0.0
    guard = _finalize_draw_bucket(f"draw_score>={draw_guard_min_score:.2f}", guard_bucket, baseline_draw_rate=baseline_draw_rate)
    takeover = _finalize_draw_bucket("draw_takeover", takeover_bucket, baseline_draw_rate=baseline_draw_rate)

    recommendation = "collecting"
    recommendation_text = "平局专项样本仍需积累，先继续观察。"
    if sample_count >= 100 and predicted_draw_count >= 8 and precision is not None:
        if precision >= max(0.34, baseline_draw_rate + 0.08):
            recommendation = "enable_draw_watch"
            recommendation_text = "平局正式推荐精确率高于基准，可保留博平；同时将 draw_score>=0.58 作为防平提示。"
        elif precision < max(0.22, baseline_draw_rate - 0.03):
            recommendation = "tighten_draw_takeover"
            recommendation_text = "平局正式推荐误报偏多，建议提高 draw_takeover 门槛，保留防平不直接博平。"
        else:
            recommendation = "watch_draw_guard"
            recommendation_text = "平局推荐暂未形成稳定优势，优先把高 draw_score 作为防平风险提示。"
    elif sample_count >= 100 and int(guard.get("sample_count", 0) or 0) >= 20:
        recommendation = "watch_draw_guard"
        recommendation_text = "正式平局推荐样本少，但防平信号已有覆盖，可先观察 draw_score 分层命中。"

    summary = {
        "sample_count": sample_count,
        "actual_draw_count": actual_draw_count,
        "actual_draw_rate": round(actual_draw_rate, 6) if actual_draw_rate is not None else None,
        "actual_draw_rate_text": f"{actual_draw_rate:.1%}" if actual_draw_rate is not None else "-",
        "predicted_draw_count": predicted_draw_count,
        "draw_hit_count": draw_hit_count,
        "precision": round(precision, 6) if precision is not None else None,
        "precision_text": f"{precision:.1%}" if precision is not None else "-",
        "recall": round(recall, 6) if recall is not None else None,
        "recall_text": f"{recall:.1%}" if recall is not None else "-",
        "false_positive_count": int(totals.get("false_positive_count", 0) or 0),
        "missed_draw_count": int(totals.get("missed_draw_count", 0) or 0),
        "guard": guard,
        "takeover": takeover,
        "recommendation": recommendation,
        "recommendation_text": recommendation_text,
        "draw_release_guard_policy": json.loads(json.dumps(draw_release_guard_policy)),
    }
    missed_draw_rows.sort(key=lambda row: (-_safe_float(row.get("draw_score"), default=0.0), str(row.get("match_date") or "")))
    false_positive_rows.sort(key=lambda row: (-_safe_float(row.get("draw_score"), default=0.0), str(row.get("match_date") or "")))
    result = {
        "ok": True,
        "reason": "ok",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "validation": {
            "sample_count": sample_count,
            "original_sample_count": original_validation_count,
            "max_validation_samples": int(max_validation_samples),
            "truncated": len(validation_items) < original_validation_count,
            "skipped": skipped,
            "date_start": min(dates) if dates else None,
            "date_end": max(dates) if dates else None,
            "ratio": round(len(validation_items) / max(len(train_items) + original_validation_count, 1), 4),
        },
        "summary": summary,
        "draw_release_guard_policy": json.loads(json.dumps(draw_release_guard_policy)),
        "score_buckets": _draw_bucket_rows(score_buckets, baseline_draw_rate=baseline_draw_rate),
        "odds_buckets": _draw_bucket_rows(odds_buckets, baseline_draw_rate=baseline_draw_rate),
        "handicap_buckets": _draw_bucket_rows(handicap_buckets, baseline_draw_rate=baseline_draw_rate),
        "expected_goal_buckets": _draw_bucket_rows(expected_goal_buckets, baseline_draw_rate=baseline_draw_rate),
        "market_balance_buckets": _draw_bucket_rows(market_balance_buckets, baseline_draw_rate=baseline_draw_rate),
        "missed_draw_rows": missed_draw_rows[:10],
        "false_positive_rows": false_positive_rows[:10],
    }
    result["report_path"] = _write_draw_specialist_backtest_markdown(result) if write_report else None
    _save_draw_specialist_backtest_report(result)
    return result


def _base_market_probs(match: AppMatch) -> tuple[float, float, float]:
    market_home = 1.0 / max(match.odds_home, 1.01)
    market_draw = 1.0 / max(match.odds_draw, 1.01)
    market_away = 1.0 / max(match.odds_away, 1.01)
    return _normalize_probs(market_home, market_draw, market_away)


def _draw_market_score(
    match: AppMatch,
    probabilities: dict[str, float],
    market_probabilities: dict[str, float],
    poisson_probabilities: dict[str, float],
    recent_form_features: dict[str, float],
    home_rating: float,
    away_rating: float,
    expected_goals: float,
) -> tuple[float, dict[str, float], str]:
    rating_balance = _clamp(1.0 - abs(home_rating - away_rating) / 220.0)
    market_balance = _clamp(1.0 - abs(probabilities.get("home", 0.0) - probabilities.get("away", 0.0)) / 0.22)
    market_draw_signal = _clamp((market_probabilities.get("draw", 0.0) - 0.22) / 0.12)
    ensemble_draw_signal = _clamp((probabilities.get("draw", 0.0) - 0.22) / 0.12)
    poisson_draw_signal = _clamp((poisson_probabilities.get("draw", 0.0) - 0.20) / 0.12)
    low_goal_signal = _clamp((2.85 - expected_goals) / 1.35)
    handicap_balance = _clamp(1.0 - abs(_safe_float(match.handicap_line, default=0.0)) / 1.25)
    recent_points_gap = abs(
        _safe_float(recent_form_features.get("home_recent_points_pg"), default=0.0)
        - _safe_float(recent_form_features.get("away_recent_points_pg"), default=0.0)
    )
    recent_goal_gap = abs(
        _safe_float(recent_form_features.get("home_recent_goal_diff_pg"), default=0.0)
        - _safe_float(recent_form_features.get("away_recent_goal_diff_pg"), default=0.0)
    )
    recent_balance = _clamp(1.0 - recent_points_gap / 1.6) * 0.6 + _clamp(1.0 - recent_goal_gap / 1.6) * 0.4
    recent_balance = _clamp(recent_balance)

    return_rate = _safe_float(match.return_rate, default=0.0)
    if return_rate <= 0.0:
        implied_total = sum(1.0 / max(value, 1.01) for value in (match.odds_home, match.odds_draw, match.odds_away))
        return_rate = 1.0 / max(implied_total, 1e-9)
    return_rate_signal = _clamp((return_rate - 0.88) / 0.10)

    opening_draw = _safe_float(match.opening_odds_draw, default=0.0)
    current_draw = _safe_float(match.odds_draw, default=0.0)
    draw_odds_drop = 0.0
    if opening_draw > 1.0 and current_draw > 1.0:
        draw_odds_drop = _clamp((opening_draw - current_draw) / 0.45)

    kelly_home = _safe_float(match.kelly_home, default=0.0)
    kelly_draw = _safe_float(match.kelly_draw, default=0.0)
    kelly_away = _safe_float(match.kelly_away, default=0.0)
    kelly_draw_signal = 0.0
    if min(kelly_home, kelly_draw, kelly_away) > 0.0:
        peer_average = (kelly_home + kelly_away) / 2.0
        kelly_draw_signal = _clamp((peer_average - kelly_draw) / 0.10 + 0.5)

    signal_weights = {
        "ensemble_draw": 0.24,
        "market_draw": 0.16,
        "poisson_draw": 0.14,
        "rating_balance": 0.14,
        "market_balance": 0.10,
        "low_goal": 0.08,
        "handicap_balance": 0.05,
        "recent_balance": 0.05,
        "return_rate": 0.03,
        "draw_odds_drop": 0.03,
        "kelly_draw": 0.08,
    }
    draw_signals = {
        "ensemble_draw": round(ensemble_draw_signal, 4),
        "market_draw": round(market_draw_signal, 4),
        "poisson_draw": round(poisson_draw_signal, 4),
        "rating_balance": round(rating_balance, 4),
        "market_balance": round(market_balance, 4),
        "low_goal": round(low_goal_signal, 4),
        "handicap_balance": round(handicap_balance, 4),
        "recent_balance": round(recent_balance, 4),
        "return_rate": round(return_rate_signal, 4),
        "draw_odds_drop": round(draw_odds_drop, 4),
        "kelly_draw": round(kelly_draw_signal, 4),
    }
    draw_score = _clamp(
        sum(_safe_float(draw_signals.get(key), default=0.0) * weight for key, weight in signal_weights.items())
        + 0.02
    )
    if draw_score >= 0.72:
        draw_grade = "博平"
    elif draw_score >= 0.58:
        draw_grade = "防平"
    else:
        draw_grade = "不防平"
    return round(draw_score, 4), draw_signals, draw_grade


def _side_market_score(
    side: str,
    match: AppMatch,
    base_probabilities: dict[str, float],
    market_probabilities: dict[str, float],
    xgb_probabilities: dict[str, float],
    recent_form_features: dict[str, float],
    home_rating: float,
    away_rating: float,
    expected_goals: float,
) -> tuple[float, dict[str, float]]:
    is_home = side == "home"
    current_side_odds = _safe_float(match.odds_home if is_home else match.odds_away, default=0.0)
    opening_side_odds = _safe_float(match.opening_odds_home if is_home else match.opening_odds_away, default=0.0)
    side_kelly = _safe_float(match.kelly_home if is_home else match.kelly_away, default=0.0)
    peer_kelly_a = _safe_float(match.kelly_draw, default=0.0)
    peer_kelly_b = _safe_float(match.kelly_away if is_home else match.kelly_home, default=0.0)

    rating_diff = home_rating - away_rating
    points_diff = _safe_float(recent_form_features.get("recent_points_diff"), default=0.0)
    goal_diff = _safe_float(recent_form_features.get("recent_goal_diff_diff"), default=0.0)
    handicap_line = _safe_float(match.handicap_line, default=0.0)
    direction = 1.0 if is_home else -1.0

    rating_signal = _clamp(0.5 + (rating_diff * direction) / 220.0)
    recent_signal = _clamp(0.5 + (points_diff * direction) / 2.4 + (goal_diff * direction) / 3.6)
    base_signal = _clamp((_safe_float(base_probabilities.get(side), default=0.0) - 0.26) / 0.22)
    market_signal = _clamp((_safe_float(market_probabilities.get(side), default=0.0) - 0.26) / 0.22)
    xgb_signal = _clamp((_safe_float(xgb_probabilities.get(side), default=0.0) - 0.26) / 0.22)

    odds_drop_signal = 0.0
    if opening_side_odds > 1.0 and current_side_odds > 1.0:
        odds_drop_signal = _clamp((opening_side_odds - current_side_odds) / 0.65)

    kelly_signal = 0.0
    if min(side_kelly, peer_kelly_a, peer_kelly_b) > 0.0:
        peer_average = (peer_kelly_a + peer_kelly_b) / 2.0
        kelly_signal = _clamp((peer_average - side_kelly) / 0.10 + 0.5)

    handicap_signal = (
        _clamp((0.30 - handicap_line) / 1.8)
        if is_home
        else _clamp((handicap_line + 0.30) / 1.8)
    )
    goal_signal = _clamp((expected_goals - 2.2) / 1.2)

    signals = {
        "base": round(base_signal, 4),
        "market": round(market_signal, 4),
        "xgb": round(xgb_signal, 4),
        "rating": round(rating_signal, 4),
        "recent": round(recent_signal, 4),
        "odds_drop": round(odds_drop_signal, 4),
        "kelly": round(kelly_signal, 4),
        "handicap": round(handicap_signal, 4),
        "goal": round(goal_signal, 4),
    }
    weights = {
        "base": 0.20,
        "market": 0.12,
        "xgb": 0.16,
        "rating": 0.15,
        "recent": 0.12,
        "odds_drop": 0.08,
        "kelly": 0.08,
        "handicap": 0.06,
        "goal": 0.03,
    }
    score = _clamp(sum(signals[key] * weights[key] for key in weights))
    return round(score, 4), signals


def _specialist_probability_fusion(
    match: AppMatch,
    base_probabilities: dict[str, float],
    market_probabilities: dict[str, float],
    poisson_probabilities: dict[str, float],
    xgb_probabilities: dict[str, float],
    recent_form_features: dict[str, float],
    home_rating: float,
    away_rating: float,
    expected_goals: float,
) -> dict[str, object]:
    draw_score, draw_signals, draw_grade = _draw_market_score(
        match=match,
        probabilities=base_probabilities,
        market_probabilities=market_probabilities,
        poisson_probabilities=poisson_probabilities,
        recent_form_features=recent_form_features,
        home_rating=home_rating,
        away_rating=away_rating,
        expected_goals=expected_goals,
    )
    home_score, home_signals = _side_market_score(
        "home",
        match=match,
        base_probabilities=base_probabilities,
        market_probabilities=market_probabilities,
        xgb_probabilities=xgb_probabilities,
        recent_form_features=recent_form_features,
        home_rating=home_rating,
        away_rating=away_rating,
        expected_goals=expected_goals,
    )
    away_score, away_signals = _side_market_score(
        "away",
        match=match,
        base_probabilities=base_probabilities,
        market_probabilities=market_probabilities,
        xgb_probabilities=xgb_probabilities,
        recent_form_features=recent_form_features,
        home_rating=home_rating,
        away_rating=away_rating,
        expected_goals=expected_goals,
    )

    specialist_probs = _normalize_probs(
        max(home_score, 0.05),
        max(draw_score, 0.05),
        max(away_score, 0.05),
    )
    specialist_probabilities = {
        "home": round(specialist_probs[0], 4),
        "draw": round(specialist_probs[1], 4),
        "away": round(specialist_probs[2], 4),
    }
    specialist_peak = max(specialist_probabilities.values())
    disagreement = max(
        abs(specialist_probabilities[key] - _safe_float(base_probabilities.get(key), default=0.0))
        for key in ("home", "draw", "away")
    )
    fusion_alpha = _clamp(0.06 + max(0.0, specialist_peak - 0.42) * 0.22 + disagreement * 0.18, 0.06, 0.22)
    fused_probs = _normalize_probs(
        (1.0 - fusion_alpha) * _safe_float(base_probabilities.get("home"), default=0.0)
        + fusion_alpha * specialist_probabilities["home"],
        (1.0 - fusion_alpha) * _safe_float(base_probabilities.get("draw"), default=0.0)
        + fusion_alpha * specialist_probabilities["draw"],
        (1.0 - fusion_alpha) * _safe_float(base_probabilities.get("away"), default=0.0)
        + fusion_alpha * specialist_probabilities["away"],
    )
    return {
        "draw_score": draw_score,
        "draw_signals": draw_signals,
        "draw_grade": draw_grade,
        "specialist_scores": {"home": home_score, "draw": draw_score, "away": away_score},
        "specialist_signals": {"home": home_signals, "draw": draw_signals, "away": away_signals},
        "specialist_probabilities": specialist_probabilities,
        "fusion_alpha": round(fusion_alpha, 4),
        "fused_probabilities": {
            "home": round(fused_probs[0], 4),
            "draw": round(fused_probs[1], 4),
            "away": round(fused_probs[2], 4),
        },
    }


def _handicap_specialist_blend(
    handicap_probabilities: dict[str, float],
    specialist_scores: dict[str, float],
    handicap_line: float,
    expected_goals: float,
) -> dict[str, object]:
    home_score = _safe_float(specialist_scores.get("home"), default=0.0)
    draw_score = _safe_float(specialist_scores.get("draw"), default=0.0)
    away_score = _safe_float(specialist_scores.get("away"), default=0.0)
    line_balance = _clamp(1.0 - abs(handicap_line) / 1.25)
    home_bonus = _clamp((0.30 - handicap_line) / 1.8)
    away_bonus = _clamp((handicap_line + 0.30) / 1.8)
    draw_bonus = line_balance * _clamp((3.0 - expected_goals) / 1.8)
    specialist_probs = _normalize_probs(
        max(home_score * (0.78 + 0.22 * home_bonus), 0.05),
        max(draw_score * (0.68 + 0.32 * draw_bonus), 0.05),
        max(away_score * (0.78 + 0.22 * away_bonus), 0.05),
    )
    fusion_alpha = _clamp(0.08 + abs(handicap_line) * 0.04 + max(specialist_probs) * 0.08, 0.10, 0.22)
    fused = _normalize_probs(
        (1.0 - fusion_alpha) * _safe_float(handicap_probabilities.get("home"), default=0.0)
        + fusion_alpha * specialist_probs[0],
        (1.0 - fusion_alpha) * _safe_float(handicap_probabilities.get("draw"), default=0.0)
        + fusion_alpha * specialist_probs[1],
        (1.0 - fusion_alpha) * _safe_float(handicap_probabilities.get("away"), default=0.0)
        + fusion_alpha * specialist_probs[2],
    )
    return {
        "probabilities": {
            "home": round(fused[0], 4),
            "draw": round(fused[1], 4),
            "away": round(fused[2], 4),
        },
        "specialist_probabilities": {
            "home": round(specialist_probs[0], 4),
            "draw": round(specialist_probs[1], 4),
            "away": round(specialist_probs[2], 4),
        },
        "fusion_alpha": round(fusion_alpha, 4),
    }


def _select_score_with_specialist_bias(
    score_distribution: list[dict],
    recommendation_key: str,
    specialist_scores: dict[str, float],
    expected_goals: float,
) -> tuple[dict, float]:
    low_goal_index = _clamp((2.8 - expected_goals) / 1.5)
    if not score_distribution:
        return {"score": "-", "probability": 0.0}, round(low_goal_index, 4)
    home_score = _safe_float(specialist_scores.get("home"), default=0.0)
    draw_score = _safe_float(specialist_scores.get("draw"), default=0.0)
    away_score = _safe_float(specialist_scores.get("away"), default=0.0)
    ranked: list[tuple[float, dict]] = []
    for item in score_distribution[:18]:
        score_text = str(item.get("score", ""))
        if "-" not in score_text:
            continue
        try:
            home_goals, away_goals = [int(part) for part in score_text.split("-", 1)]
        except Exception:
            continue
        base_prob = _safe_float(item.get("probability"), default=0.0)
        total_goals = home_goals + away_goals
        bonus = 0.0
        outcome_key = _score_outcome_key(score_text)
        if outcome_key == recommendation_key:
            bonus += 0.024
        if home_goals == away_goals:
            bonus += draw_score * 0.05
        elif home_goals > away_goals:
            bonus += home_score * 0.04
        else:
            bonus += away_score * 0.04
        if total_goals <= 2:
            bonus += low_goal_index * 0.05
        elif total_goals >= 4:
            bonus -= low_goal_index * 0.02
        ranked.append((base_prob + bonus, item))
    ranked.sort(key=lambda pair: (-pair[0], str(pair[1].get("score", ""))))
    if not ranked:
        return score_distribution[0], round(low_goal_index, 4)
    return ranked[0][1], round(low_goal_index, 4)


def _resolved_ratings(
    match: AppMatch,
    ratings_map: dict[str, float],
) -> tuple[float, float, dict[str, float]]:
    market_home, market_draw, market_away = _base_market_probs(match)
    league_strength = LEAGUE_STRENGTH.get(match.league, 0.92)
    seeded = ELO_ENGINE.from_market(market_home, market_draw, market_away, league_strength)

    home_rating = ratings_map.get(match.home_team)
    away_rating = ratings_map.get(match.away_team)

    if home_rating is None and away_rating is None:
        home_rating = seeded.home_rating
        away_rating = seeded.away_rating
    elif home_rating is None:
        home_rating = ELO_ENGINE.base_rating + (seeded.home_rating - seeded.away_rating) * 0.35
    elif away_rating is None:
        away_rating = ELO_ENGINE.base_rating - (seeded.home_rating - seeded.away_rating) * 0.35

    ratings_map.setdefault(match.home_team, float(home_rating))
    ratings_map.setdefault(match.away_team, float(away_rating))
    return float(home_rating), float(away_rating), ratings_map


def _recent_form_cache_path() -> Path:
    state_dir = getattr(STATE_STORE, "state_dir", PROJECT_DIR / "data" / "state")
    try:
        resolved_state_dir = state_dir if isinstance(state_dir, Path) else Path(str(state_dir))
    except Exception:
        resolved_state_dir = PROJECT_DIR / "data" / "state"
    return resolved_state_dir / "recent_form_team_histories.json"


def _recent_form_state_file_signature(attribute: str) -> dict[str, object]:
    path = getattr(STATE_STORE, attribute, None)
    if path is None:
        return {"source_file": "", "mtime_ns": 0, "size_bytes": 0}
    if isinstance(path, Path):
        signature = _state_file_signature(path)
        return {"source_file": str(path), **signature}
    try:
        resolved_path = Path(str(path))
        signature = _state_file_signature(resolved_path)
        return {"source_file": str(resolved_path), **signature}
    except Exception:
        return {"source_file": str(path), "mtime_ns": 0, "size_bytes": 0}


def _recent_form_state_signature() -> dict[str, object]:
    return {
        "version": _RECENT_FORM_CACHE_VERSION,
        "xgb_samples": _recent_form_state_file_signature("xgb_samples_file"),
        "settlements": _recent_form_state_file_signature("settlements_file"),
    }


def _normalize_recent_form_team_histories(payload: object) -> dict[str, list[dict]] | None:
    if not isinstance(payload, dict):
        return None
    normalized: dict[str, list[dict]] = {}
    for team_name, entries in payload.items():
        if not isinstance(entries, list):
            continue
        normalized[str(team_name)] = [dict(item) for item in entries if isinstance(item, dict)]
    return normalized


def _load_recent_form_team_histories_cache(signature: dict[str, object]) -> dict[str, list[dict]] | None:
    cache_path = _recent_form_cache_path()
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict) or payload.get("source_signature") != signature:
        return None
    return _normalize_recent_form_team_histories(payload.get("team_histories"))


def _save_recent_form_team_histories_cache(signature: dict[str, object], team_histories: dict[str, list[dict]]) -> None:
    cache_path = _recent_form_cache_path()
    history_entry_count = sum(len(entries) for entries in team_histories.values() if isinstance(entries, list))
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_signature": signature,
        "team_count": len(team_histories),
        "history_entry_count": history_entry_count,
        "team_histories": team_histories,
    }
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = cache_path.with_name(f"{cache_path.name}.tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        tmp_path.replace(cache_path)
    except Exception:
        pass


def _recent_form_team_histories() -> dict[str, list[dict]]:
    with _RECENT_FORM_CACHE_LOCK:
        signature = _recent_form_state_signature()
        cached_signature = _RECENT_FORM_CACHE.get("signature")
        cached_histories = _RECENT_FORM_CACHE.get("team_histories")
        if cached_signature == signature and isinstance(cached_histories, dict):
            return cached_histories

        cached_file_histories = _load_recent_form_team_histories_cache(signature)
        if cached_file_histories is not None:
            _RECENT_FORM_CACHE["signature"] = signature
            _RECENT_FORM_CACHE["team_histories"] = cached_file_histories
            return cached_file_histories

        team_histories = build_team_histories_from_state(
            sample_items=STATE_STORE.load_xgb_samples(),
            settlement_items=STATE_STORE.load_settlements(),
        )
        _save_recent_form_team_histories_cache(signature, team_histories)
        _RECENT_FORM_CACHE["signature"] = signature
        _RECENT_FORM_CACHE["team_histories"] = team_histories
        return team_histories


def _recent_form_features_for_match(match: AppMatch) -> dict[str, float]:
    return build_recent_form_feature_map(
        team_histories=_recent_form_team_histories(),
        home_team=match.home_team,
        away_team=match.away_team,
        cutoff_date=match.match_date,
        cutoff_time=match.match_time,
        match_id=match.match_id,
    )


def _predict_match_with_inputs(
    match: AppMatch,
    home_rating: float,
    away_rating: float,
    league_strength: float,
    recent_form_features: dict[str, float],
) -> dict:
    market_home, market_draw, market_away = _base_market_probs(match)
    market_probs = (market_home, market_draw, market_away)
    market_probabilities = {"home": round(market_home, 4), "draw": round(market_draw, 4), "away": round(market_away, 4)}
    context = EnsembleContext(
        market_probs=market_probs,
        home_rating=home_rating,
        away_rating=away_rating,
        market_draw_prob=market_draw,
        league_strength=league_strength,
        metadata={
            "match_id": match.match_id,
            "match_date": match.match_date,
            "match_time": match.match_time,
            "league": match.league,
            "home_team": match.home_team,
            "away_team": match.away_team,
            "odds_home": match.odds_home,
            "odds_draw": match.odds_draw,
            "odds_away": match.odds_away,
            "opening_odds_home": match.opening_odds_home,
            "opening_odds_draw": match.opening_odds_draw,
            "opening_odds_away": match.opening_odds_away,
            "return_rate": match.return_rate,
            "kelly_home": match.kelly_home,
            "kelly_draw": match.kelly_draw,
            "kelly_away": match.kelly_away,
            **recent_form_features,
        },
    )

    current_weights = _ensemble_weights_for_league(match.league)
    ENSEMBLE_ENGINE.set_weights(current_weights)
    ensemble_result = ENSEMBLE_ENGINE.predict(
        context=context,
        models=[MARKET_MODEL, ELO_MODEL, POISSON_MODEL, XGBOOST_MODEL],
    )
    components = ensemble_result.components

    market_probs = components.get("market", None).probabilities if components.get("market") else market_probs
    elo_probs = components.get("elo", None).probabilities if components.get("elo") else market_probs
    poisson_probs = components.get("poisson", None).probabilities if components.get("poisson") else market_probs
    xgb_probs = components.get("xgboost", None).probabilities if components.get("xgboost") else market_probs

    market_probabilities = {"home": round(market_probs[0], 4), "draw": round(market_probs[1], 4), "away": round(market_probs[2], 4)}
    elo_probabilities = {"home": round(elo_probs[0], 4), "draw": round(elo_probs[1], 4), "away": round(elo_probs[2], 4)}
    poisson_probabilities = {
        "home": round(poisson_probs[0], 4),
        "draw": round(poisson_probs[1], 4),
        "away": round(poisson_probs[2], 4),
    }
    xgb_probabilities = {
        "home": round(xgb_probs[0], 4),
        "draw": round(xgb_probs[1], 4),
        "away": round(xgb_probs[2], 4),
    }
    xgb_component = components.get("xgboost")
    xgb_features = xgb_component.metadata.get("xgb_features", {}) if xgb_component else {}
    xgb_fallback = bool(xgb_component.metadata.get("xgb_fallback", True)) if xgb_component else True
    xgb_model_ready = bool(xgb_component.metadata.get("xgb_model_ready", False)) if xgb_component else False
    total_goals_model_output = TOTAL_GOALS_MODEL.predict_from_features(xgb_features if isinstance(xgb_features, dict) else {})
    base_scoreline_model_output = SCORELINE_MODEL.predict_from_features(xgb_features if isinstance(xgb_features, dict) else {})
    volatile_scoreline_model_output = VOLATILE_SCORELINE_MODEL.predict_from_features(xgb_features if isinstance(xgb_features, dict) else {})
    scoreline_model_output, volatile_scoreline_override = _merge_scoreline_model_outputs(
        base_output=base_scoreline_model_output,
        volatile_output=volatile_scoreline_model_output,
    )

    poisson_output = components.get("poisson")
    poisson = get_poisson_outcome(poisson_output) if poisson_output else None
    if poisson is None:
        poisson = POISSON_ENGINE.predict(
            home_rating=home_rating,
            away_rating=away_rating,
            market_draw_prob=market_draw,
            league_strength=league_strength,
        )
        poisson_probs = (poisson.home_win, poisson.draw, poisson.away_win)
        poisson_probabilities = {
            "home": round(poisson.home_win, 4),
            "draw": round(poisson.draw, 4),
            "away": round(poisson.away_win, 4),
        }

    ou_probabilities = {
        "over_2_5": round(poisson.over_2_5, 4),
        "under_2_5": round(poisson.under_2_5, 4),
    }
    ou_recommendation = "大2.5" if poisson.over_2_5 >= poisson.under_2_5 else "小2.5"
    ou_confidence = max(poisson.over_2_5, poisson.under_2_5)
    top_score = poisson.top_scores[0] if poisson.top_scores else {"score": "-", "probability": 0.0}
    top_total_goals = poisson.top_total_goals[0] if poisson.top_total_goals else {"goals": 0, "probability": 0.0}
    top_htft = poisson.htft_top[0] if poisson.htft_top else {"label": "-", "probability": 0.0}
    handicap_line = _safe_float(match.handicap_line, default=0.0)
    handicap_probabilities_raw = {"home": 0.0, "draw": 0.0, "away": 0.0}
    for item in poisson.score_distribution:
        score_text = str(item.get("score", ""))
        if "-" not in score_text:
            continue
        try:
            score_home, score_away = [int(part) for part in score_text.split("-", 1)]
        except Exception:
            continue
        handicap_key = _handicap_outcome_key(score_home, score_away, handicap_line)
        handicap_probabilities_raw[handicap_key] += _safe_float(item.get("probability"), default=0.0)
    handicap_total = max(sum(handicap_probabilities_raw.values()), 1e-9)
    handicap_probabilities = {
        key: round(value / handicap_total, 4) for key, value in handicap_probabilities_raw.items()
    }
    handicap_pick_key = max(handicap_probabilities, key=handicap_probabilities.get)
    handicap_recommendation = _handicap_label_from_key(handicap_pick_key)
    handicap_display = _format_handicap_display(handicap_line, handicap_pick_key)
    handicap_confidence = handicap_probabilities[handicap_pick_key]

    blend_home, blend_draw, blend_away = ensemble_result.probabilities
    ensemble_probabilities = {
        "home": round(blend_home, 4),
        "draw": round(blend_draw, 4),
        "away": round(blend_away, 4),
    }
    specialist_result = _specialist_probability_fusion(
        match=match,
        base_probabilities=ensemble_probabilities,
        market_probabilities=market_probabilities,
        poisson_probabilities=poisson_probabilities,
        xgb_probabilities=xgb_probabilities,
        recent_form_features=recent_form_features,
        home_rating=home_rating,
        away_rating=away_rating,
        expected_goals=poisson.home_lambda + poisson.away_lambda,
    )
    handicap_specialist = _handicap_specialist_blend(
        handicap_probabilities=handicap_probabilities,
        specialist_scores=specialist_result.get("specialist_scores", {}),
        handicap_line=handicap_line,
        expected_goals=poisson.home_lambda + poisson.away_lambda,
    )
    pre_bayes_probabilities = dict(specialist_result.get("fused_probabilities", ensemble_probabilities))
    bayes_status = get_bayes_calibration_status()
    bayes_overrides = bayes_status.get("league_overrides", {}) if isinstance(bayes_status, dict) else {}
    bayes_league_key = normalize_text(match.league)
    bayes_override_active = bool(
        isinstance(bayes_overrides, dict)
        and isinstance(bayes_overrides.get(bayes_league_key), dict)
        and bayes_overrides.get(bayes_league_key, {}).get("enabled")
    )
    bayes_config = _current_bayes_calibration_config(match.league)
    probabilities, bayes_calibration = calibrate_three_way_probabilities(
        model_probabilities=pre_bayes_probabilities,
        market_probabilities=market_probabilities,
        config=bayes_config,
    )
    if isinstance(bayes_calibration, dict):
        bayes_calibration["config_scope"] = "league_override" if bayes_override_active else "global"
        bayes_calibration["league_key"] = bayes_league_key
    bayes_probabilities = dict(probabilities)
    final_probs = (
        _safe_float(probabilities.get("home"), default=0.0),
        _safe_float(probabilities.get("draw"), default=0.0),
        _safe_float(probabilities.get("away"), default=0.0),
    )

    model_top_key = max(probabilities, key=probabilities.get)
    recommendation = {"home": "主胜", "draw": "平局", "away": "客胜"}[model_top_key]
    model_top_prob = probabilities[model_top_key]
    ordered = sorted(probabilities.values(), reverse=True)
    margin = ordered[0] - ordered[1]
    aligned_score = top_score
    for item in poisson.score_distribution:
        if _score_outcome_key(str(item.get("score", ""))) == model_top_key:
            aligned_score = item
            break

    low_goal_index = 0.0
    aligned_total_goals_value = int(top_total_goals.get("goals", 0))
    aligned_total_goals_prob = _safe_float(top_total_goals.get("probability"), default=0.0)
    aligned_score_text = str(aligned_score.get("score", "-"))
    if "-" in aligned_score_text:
        try:
            aligned_total_goals_value = sum(int(part) for part in aligned_score_text.split("-", 1))
        except Exception:
            aligned_total_goals_value = int(top_total_goals.get("goals", 0))
        for total_item in poisson.total_goals_distribution:
            try:
                if int(total_item.get("goals", -1)) == aligned_total_goals_value:
                    aligned_total_goals_prob = _safe_float(total_item.get("probability"), default=0.0)
                    break
            except Exception:
                continue
    aligned_htft = top_htft
    htft_candidates = sorted(
        (
            {
                "key": key,
                "label": _htft_label_from_key(key),
                "probability": _safe_float(probability, default=0.0),
            }
            for key, probability in poisson.htft_probabilities.items()
            if key.split("_", 1)[1] == model_top_key
        ),
        key=lambda item: (-item["probability"], item["key"]),
    )
    if htft_candidates:
        aligned_htft = htft_candidates[0]

    total_goals_model_pick = _safe_int(total_goals_model_output.get("label"))
    total_goals_model_confidence = _safe_float(total_goals_model_output.get("confidence"), default=0.0)
    scoreline_model_pick = str(scoreline_model_output.get("label") or "").strip()
    scoreline_model_confidence = _safe_float(scoreline_model_output.get("confidence"), default=0.0)
    scoreline_model_bucket = _scoreline_bucket(scoreline_model_pick) if scoreline_model_pick else None

    dist_market_elo = _model_distance(market_probs, elo_probs)
    dist_market_poisson = _model_distance(market_probs, poisson_probs)
    dist_elo_poisson = _model_distance(elo_probs, poisson_probs)
    consistency = _clamp(1.0 - (dist_market_elo + dist_market_poisson + dist_elo_poisson) / 3.0)

    entropy = _distribution_entropy(final_probs)
    volatility = _model_distance(final_probs, market_probs)
    poisson_peak = poisson.top_scores[0]["probability"] if poisson.top_scores else 0.0

    market_top_key = max(market_probabilities, key=market_probabilities.get)
    direction_shift = 0.20 if model_top_key != market_top_key else 0.0

    upset_index = _clamp(
        0.24
        + direction_shift
        + volatility * 0.50
        + (1.0 - model_top_prob) * 0.26
        + (0.20 - min(poisson_peak, 0.20)) * 0.40
    )
    stability_index = _clamp(
        0.24 + consistency * 0.38 + model_top_prob * 0.24 + poisson_peak * 0.90 - entropy * 0.20
    )
    confidence_index = _clamp(0.20 + model_top_prob * 0.42 + margin * 0.42 + consistency * 0.16)
    draw_score = _safe_float(specialist_result.get("draw_score"), default=0.0)
    draw_signals = specialist_result.get("draw_signals", {})
    draw_grade = str(specialist_result.get("draw_grade", "-"))
    draw_takeover, draw_release_guard = _draw_takeover_decision(
        match,
        probabilities=probabilities,
        draw_score=draw_score,
        draw_signals=draw_signals,
    )
    recommendation_key = "draw" if draw_takeover else model_top_key
    recommendation = {"home": "主胜", "draw": "平局", "away": "客胜"}[recommendation_key]
    recommendation_confidence_raw = _clamp(
        max(confidence_index, draw_score) if recommendation_key == "draw" else confidence_index
    )
    recommendation_confidence, recommendation_confidence_calibration = _calibrate_recommendation_confidence(
        recommendation_confidence_raw
    )
    score_specialist_candidate, low_goal_index = _select_score_with_specialist_bias(
        poisson.score_distribution,
        recommendation_key=recommendation_key,
        specialist_scores=specialist_result.get("specialist_scores", {}),
        expected_goals=poisson.home_lambda + poisson.away_lambda,
    )
    aligned_score = top_score
    for item in poisson.score_distribution:
        if _score_outcome_key(str(item.get("score", ""))) == recommendation_key:
            aligned_score = item
            break

    aligned_total_goals_value = int(top_total_goals.get("goals", 0))
    aligned_total_goals_prob = _safe_float(top_total_goals.get("probability"), default=0.0)
    aligned_score_text = str(aligned_score.get("score", "-"))
    if "-" in aligned_score_text:
        try:
            aligned_total_goals_value = sum(int(part) for part in aligned_score_text.split("-", 1))
        except Exception:
            aligned_total_goals_value = int(top_total_goals.get("goals", 0))
        for total_item in poisson.total_goals_distribution:
            try:
                if int(total_item.get("goals", -1)) == aligned_total_goals_value:
                    aligned_total_goals_prob = _safe_float(total_item.get("probability"), default=0.0)
                    break
            except Exception:
                continue

    aligned_htft = top_htft
    htft_candidates = sorted(
        (
            {
                "key": key,
                "label": _htft_label_from_key(key),
                "probability": _safe_float(probability, default=0.0),
            }
            for key, probability in poisson.htft_probabilities.items()
            if key.split("_", 1)[1] == recommendation_key
        ),
        key=lambda item: (-item["probability"], item["key"]),
    )
    if htft_candidates:
        aligned_htft = htft_candidates[0]

    pre_play_model_total_goals_value = aligned_total_goals_value
    pre_play_model_total_goals_confidence = aligned_total_goals_prob
    pre_play_model_score_recommendation = aligned_score_text
    pre_play_model_score_confidence = _safe_float(aligned_score.get("probability"), default=0.0)

    play_model_policy = _current_play_model_policy()
    total_goals_policy = play_model_policy.get("total_goals", {}) if isinstance(play_model_policy, dict) else {}
    scoreline_policy = play_model_policy.get("scoreline", {}) if isinstance(play_model_policy, dict) else {}

    total_goals_model_takeover = bool(
        bool(total_goals_policy.get("takeover_enabled"))
        and total_goals_model_output.get("model_ready")
        and total_goals_model_pick is not None
        and total_goals_model_confidence >= _safe_float(total_goals_policy.get("min_confidence"), default=0.24)
    )
    if total_goals_model_takeover and total_goals_model_pick is not None:
        aligned_total_goals_value = int(total_goals_model_pick)
        aligned_total_goals_prob = total_goals_model_confidence
        aligned_score_from_total = _best_score_for_total_goals(
            poisson.score_distribution,
            total_goals=aligned_total_goals_value,
            outcome_key=recommendation_key,
        )
        if isinstance(aligned_score_from_total, dict):
            aligned_score = aligned_score_from_total
            aligned_score_text = str(aligned_score.get("score", "-"))

    scoreline_model_takeover, _, _, scoreline_takeover_bucket = _scoreline_takeover_decision(
        label=scoreline_model_pick if scoreline_model_pick != "OTHER" else None,
        confidence=scoreline_model_confidence,
        recommendation_key=recommendation_key,
        scoreline_policy=scoreline_policy,
    )
    scoreline_model_takeover = bool(
        bool(scoreline_policy.get("takeover_enabled", True))
        and scoreline_model_output.get("model_ready")
        and scoreline_model_takeover
        and (
            not total_goals_model_takeover
            or _parse_total_goals_from_score_text(scoreline_model_pick) == aligned_total_goals_value
        )
    )
    if scoreline_model_takeover:
        aligned_score_text = scoreline_model_pick
        aligned_score = {
            "score": aligned_score_text,
            "probability": scoreline_model_confidence,
        }
        aligned_total_goals_from_score = _parse_total_goals_from_score_text(aligned_score_text)
        if aligned_total_goals_from_score is not None:
            aligned_total_goals_value = aligned_total_goals_from_score
            aligned_total_goals_prob = max(aligned_total_goals_prob, scoreline_model_confidence)

    strength = {
        "home_rating": round(home_rating, 1),
        "away_rating": round(away_rating, 1),
        "rating_diff": round(home_rating - away_rating, 1),
        "home_score": round(_strength_score(home_rating), 1),
        "away_score": round(_strength_score(away_rating), 1),
    }
    model_margin_goals = _safe_float(poisson.home_lambda, default=0.0) - _safe_float(poisson.away_lambda, default=0.0)
    handicap_margin_consistency = build_handicap_margin_consistency_signal(
        match,
        model_margin_goals=model_margin_goals,
        probabilities=probabilities,
        handicap_probabilities=handicap_probabilities,
        recommendation_key=recommendation_key,
        handicap_pick_key=handicap_pick_key,
    )

    indices = {
        "upset_index": round(upset_index, 4),
        "stability_index": round(stability_index, 4),
        "confidence_index": round(confidence_index, 4),
        "draw_index": round(draw_score, 4),
        "specialist_index": round(_safe_float(specialist_result.get("fusion_alpha"), default=0.0), 4),
    }
    market_entropy = build_market_entropy_signal(
        match,
        recommendation_key=recommendation_key,
        recommendation_confidence=recommendation_confidence,
        history_points=_market_snapshot_history_for_match(match),
    )
    indices["market_entropy_index"] = round(_safe_float(market_entropy.get("score"), default=0.0), 4)
    indices["handicap_margin_consistency_index"] = round(
        _safe_float(handicap_margin_consistency.get("score"), default=0.0),
        4,
    )
    play_thresholds_base = _current_play_thresholds()
    play_thresholds, play_threshold_adjustment = _runtime_dynamic_play_thresholds(play_thresholds_base)
    play_confidences = {
        "1x2": round(recommendation_confidence, 4),
        "handicap": round(handicap_confidence, 4),
        "total_goals": round(aligned_total_goals_prob, 4),
        "score": round(_safe_float(aligned_score.get("probability"), default=0.0), 4),
        "htft": round(_safe_float(aligned_htft.get("probability"), default=0.0), 4),
    }
    play_pass: dict[str, bool] = {}
    layered_filter_meta: dict[str, dict] = {}
    effective_play_thresholds = dict(play_thresholds)
    for play_name, confidence_value in play_confidences.items():
        passed, effective_threshold, gate_meta = _layered_gate_for_play(
            match=match,
            play_type=play_name,
            confidence=confidence_value,
            threshold=_safe_float(play_thresholds.get(play_name), default=0.0),
        )
        play_pass[play_name] = bool(passed)
        effective_play_thresholds[play_name] = effective_threshold
        if gate_meta:
            layered_filter_meta[play_name] = gate_meta
    play_policy = _current_play_policy()
    play_catalog = {
        "1x2": {
            "play_type": "1x2",
            "pick": recommendation,
            "confidence": round(recommendation_confidence, 4),
            "passed": bool(play_pass.get("1x2")),
        },
        "handicap": {
            "play_type": "handicap",
            "pick": handicap_display,
            "confidence": round(handicap_confidence, 4),
            "passed": bool(play_pass.get("handicap")),
        },
        "total_goals": {
            "play_type": "total_goals",
            "pick": _format_total_goals_label(aligned_total_goals_value),
            "confidence": round(aligned_total_goals_prob, 4),
            "passed": bool(play_pass.get("total_goals")),
        },
        "htft": {
            "play_type": "htft",
            "pick": str(aligned_htft.get("label", "-")),
            "confidence": round(_safe_float(aligned_htft.get("probability"), default=0.0), 4),
            "passed": bool(play_pass.get("htft")),
        },
        "score": {
            "play_type": "score",
            "pick": aligned_score_text,
            "confidence": round(_safe_float(aligned_score.get("probability"), default=0.0), 4),
            "passed": bool(play_pass.get("score")),
        },
    }
    display_plays: list[dict] = []
    single_play_recommendations: list[dict] = []
    parlay_eligible_plays: list[dict] = []
    blocked_plays: list[dict] = []
    for play_type, policy in sorted(play_policy.items(), key=lambda item: int(item[1].get("priority", 99))):
        item = dict(play_catalog.get(play_type, {"play_type": play_type, "pick": "-", "confidence": 0.0, "passed": False}))
        item["single_enabled"] = bool(policy.get("single_enabled"))
        item["parlay_enabled"] = bool(policy.get("parlay_enabled"))
        item["display_enabled"] = bool(policy.get("display_enabled", True))
        item["priority"] = int(policy.get("priority", 99))
        if item["display_enabled"]:
            display_plays.append(dict(item))
        if item["passed"] and item["single_enabled"]:
            single_play_recommendations.append(dict(item))
        elif item["display_enabled"]:
            blocked_plays.append(dict(item))
        if item["passed"] and item["parlay_enabled"]:
            parlay_eligible_plays.append(dict(item))
    play_strategy = {
        "single": single_play_recommendations,
        "parlay": parlay_eligible_plays,
        "display_only": [
            dict(item)
            for item in display_plays
            if not item.get("single_enabled") and not item.get("parlay_enabled")
        ],
        "blocked": blocked_plays,
    }
    risk_level_base = _risk_level_from_upset(upset_index)
    market_entropy_risk = _market_entropy_risk_overlay(risk_level_base, market_entropy)
    risk_level = market_entropy_risk.get("adjusted_risk_level", risk_level_base)
    replay_agent_names: list[str] = []
    replay_actions: list[str] = []
    entropy_level_for_replay = normalize_text(market_entropy.get("level")).upper()
    handicap_margin_level_for_replay = normalize_text(handicap_margin_consistency.get("level")).upper()
    if entropy_level_for_replay in {"HIGH", "MEDIUM"}:
        replay_agent_names.append("MarketEntropy")
        replay_actions.append("manual_market_review" if entropy_level_for_replay == "HIGH" else "watch_market_movement")
    if handicap_margin_level_for_replay in {"HIGH", "MEDIUM"}:
        replay_agent_names.append("RiskGuardian")
        replay_actions.append(
            "review_handicap_margin_consistency"
            if handicap_margin_level_for_replay == "HIGH"
            else "downgrade_handicap_watch"
        )
    if _risk_bucket_from_label(risk_level) in {"high", "medium"} and "RiskGuardian" not in replay_agent_names:
        replay_agent_names.append("RiskGuardian")
        replay_actions.append("keep_observation")
    high_accuracy_strategy = _high_accuracy_strategy_match(
        match,
        {
            "play_strategy": play_strategy,
            "ou_recommendation": ou_recommendation,
            "ou_confidence": round(ou_confidence, 4),
            "market_probabilities": market_probabilities,
        },
        play_catalog,
    )
    strategy_admission = _strategy_admission_gate(
        risk_level=risk_level,
        confidence=recommendation_confidence,
        high_strategy=high_accuracy_strategy,
        play_strategy=play_strategy,
        agent_replay_context={"agent_names": replay_agent_names, "actions": replay_actions},
    )
    supervisor = build_supervisor_orchestration(
        match=match,
        prediction_context={
            "recommendation": recommendation,
            "confidence": round(recommendation_confidence, 4),
            "risk_level": risk_level,
            "risk_level_base": risk_level_base,
            "market_entropy": market_entropy,
            "market_entropy_risk": market_entropy_risk,
            "handicap_margin_consistency": handicap_margin_consistency,
            "probabilities": probabilities,
            "expected_goals": round(poisson.home_lambda + poisson.away_lambda, 2),
            "model": "V24-Stage5(Ensemble+Specialists+Bayes:Market+ELO+Poisson+XGBv0)",
            "strategy_admission": strategy_admission,
        },
    )

    return {
        "match_id": match.match_id,
        "recommendation": recommendation,
        "confidence": round(recommendation_confidence, 4),
        "confidence_raw": round(recommendation_confidence_raw, 4),
        "confidence_calibration": recommendation_confidence_calibration,
        "risk_level": risk_level,
        "risk_level_base": risk_level_base,
        "market_entropy": market_entropy,
        "market_entropy_risk": market_entropy_risk,
        "handicap_margin_consistency": handicap_margin_consistency,
        "supervisor": supervisor,
        "probabilities": {key: round(_safe_float(probabilities.get(key), default=0.0), 4) for key in ("home", "draw", "away")},
        "pre_bayes_probabilities": {
            key: round(_safe_float(pre_bayes_probabilities.get(key), default=0.0), 4) for key in ("home", "draw", "away")
        },
        "bayes_probabilities": {
            key: round(_safe_float(bayes_probabilities.get(key), default=0.0), 4) for key in ("home", "draw", "away")
        },
        "bayes_calibration": bayes_calibration,
        "ensemble_probabilities": ensemble_probabilities,
        "market_probabilities": market_probabilities,
        "elo_probabilities": elo_probabilities,
        "poisson_probabilities": poisson_probabilities,
        "xgb_probabilities": xgb_probabilities,
        "specialist_probabilities": specialist_result.get("specialist_probabilities", {}),
        "specialist_scores": specialist_result.get("specialist_scores", {}),
        "specialist_signals": specialist_result.get("specialist_signals", {}),
        "fusion_alpha": _safe_float(specialist_result.get("fusion_alpha"), default=0.0),
        "handicap_specialist_probabilities": handicap_specialist.get("specialist_probabilities", {}),
        "handicap_fusion_alpha": _safe_float(handicap_specialist.get("fusion_alpha"), default=0.0),
        "low_goal_index": round(low_goal_index, 4),
        "score_specialist_candidate": str(score_specialist_candidate.get("score", "-")) if isinstance(score_specialist_candidate, dict) else "-",
        "score_specialist_confidence": round(_safe_float((score_specialist_candidate or {}).get("probability"), default=0.0), 4) if isinstance(score_specialist_candidate, dict) else 0.0,
        "xgb_features": xgb_features,
        "xgb_fallback": xgb_fallback,
        "xgb_model_ready": xgb_model_ready,
        "total_goals_model": total_goals_model_output,
        "scoreline_model_base": base_scoreline_model_output,
        "scoreline_model": scoreline_model_output,
        "volatile_scoreline_model": volatile_scoreline_model_output,
        "volatile_scoreline_override": volatile_scoreline_override,
        "scoreline_model_bucket": scoreline_model_bucket,
        "play_model_policy": play_model_policy,
        "pre_play_model_total_goals_value": pre_play_model_total_goals_value,
        "pre_play_model_total_goals_confidence": round(pre_play_model_total_goals_confidence, 4),
        "pre_play_model_score_recommendation": pre_play_model_score_recommendation,
        "pre_play_model_score_confidence": round(pre_play_model_score_confidence, 4),
        "total_goals_model_takeover": total_goals_model_takeover,
        "scoreline_model_takeover": scoreline_model_takeover,
        "scoreline_model_takeover_bucket": scoreline_takeover_bucket if scoreline_model_takeover else None,
        "recent_form_features": recent_form_features,
        "ensemble_weights": ensemble_result.effective_weights,
        "play_thresholds": effective_play_thresholds,
        "play_thresholds_base": play_thresholds_base,
        "play_thresholds_runtime": play_thresholds,
        "play_threshold_adjustment": play_threshold_adjustment,
        "layered_filter": layered_filter_meta,
        "play_policy": play_policy,
        "play_pass": play_pass,
        "high_accuracy_strategy": high_accuracy_strategy,
        "strategy_admission": strategy_admission,
        "draw_score": round(draw_score, 4),
        "draw_signals": draw_signals,
        "draw_grade": draw_grade,
        "draw_takeover": draw_takeover,
        "draw_release_guard": draw_release_guard,
        "play_strategy": play_strategy,
        "single_play_recommendations": single_play_recommendations,
        "parlay_eligible_plays": parlay_eligible_plays,
        "display_plays": display_plays,
        "blocked_plays": blocked_plays,
        "ou_probabilities": ou_probabilities,
        "ou_recommendation": ou_recommendation,
        "ou_confidence": round(ou_confidence, 4),
        "handicap_line": round(handicap_line, 2),
        "handicap_probabilities": handicap_probabilities,
        "handicap_recommendation": handicap_recommendation,
        "handicap_display": handicap_display,
        "handicap_confidence": round(handicap_confidence, 4),
        "total_goals_value": aligned_total_goals_value,
        "total_goals_recommendation": _format_total_goals_label(aligned_total_goals_value),
        "total_goals_confidence": round(aligned_total_goals_prob, 4),
        "score_recommendation": aligned_score_text,
        "score_confidence": round(_safe_float(aligned_score.get("probability"), default=0.0), 4),
        "htft_recommendation": str(aligned_htft.get("label", "-")),
        "htft_confidence": round(_safe_float(aligned_htft.get("probability"), default=0.0), 4),
        "expected_goals": round(poisson.home_lambda + poisson.away_lambda, 2),
        "source": match.source,
        "model": "V24-Stage5(Ensemble+Specialists+Bayes:Market+ELO+Poisson+XGBv0)",
        "elo": strength,
        "indices": indices,
        "poisson": {
            "home_lambda": round(poisson.home_lambda, 3),
            "away_lambda": round(poisson.away_lambda, 3),
            "over_2_5": round(poisson.over_2_5, 4),
            "under_2_5": round(poisson.under_2_5, 4),
            "btts_yes": round(poisson.btts_yes, 4),
            "btts_no": round(poisson.btts_no, 4),
            "score_distribution": poisson.score_distribution,
            "top_scores": poisson.top_scores,
            "total_goals_distribution": poisson.total_goals_distribution,
            "top_total_goals": poisson.top_total_goals,
            "best_total_goals": poisson.best_total_goals,
            "best_total_goals_prob": round(poisson.best_total_goals_prob, 4),
            "halftime_probabilities": {
                key: round(value, 4) for key, value in poisson.halftime_probabilities.items()
            },
            "htft_probabilities": {key: round(value, 4) for key, value in poisson.htft_probabilities.items()},
            "htft_top": poisson.htft_top,
            "best_htft": poisson.best_htft,
            "best_htft_prob": round(poisson.best_htft_prob, 4),
        },
    }


def predict_match(match: AppMatch) -> dict:
    started_at = datetime.now()
    started_perf = time.perf_counter()
    ratings_map = _load_match_ratings(match)
    had_home = match.home_team in ratings_map
    had_away = match.away_team in ratings_map
    home_rating, away_rating, ratings_map = _resolved_ratings(match, ratings_map)
    if not (had_home and had_away):
        _save_match_ratings(match, ratings_map)

    league_strength = LEAGUE_STRENGTH.get(match.league, 0.92)
    recent_form_features = _recent_form_features_for_match(match)
    prediction = _predict_match_with_inputs(
        match=match,
        home_rating=home_rating,
        away_rating=away_rating,
        league_strength=league_strength,
        recent_form_features=recent_form_features,
    )
    prediction["rating_pool"] = _rating_pool_name(match)
    prediction = _apply_world_cup_overlay(match, prediction)
    _ensure_prediction_trace(match, prediction, started_at=started_at, latency_ms=(time.perf_counter() - started_perf) * 1000.0)
    return prediction


def _ensure_prediction_trace(
    match: AppMatch,
    prediction: dict,
    *,
    started_at: datetime | None = None,
    latency_ms: float | int | None = None,
) -> dict:
    if not isinstance(prediction, dict):
        return {}
    trace = prediction.get("trace")
    fact_refs = trace.get("fact_refs") if isinstance(trace, dict) else []
    if isinstance(trace, dict) and trace.get("trace_id") and isinstance(fact_refs, list) and fact_refs:
        return trace
    trace = build_prediction_trace_envelope(
        match=match,
        prediction=prediction,
        started_at=started_at,
        latency_ms=latency_ms,
    )
    prediction["trace"] = trace
    return trace


def _snapshot_record_match(record: dict, fallback_match_id: str = "") -> AppMatch | None:
    match_payload = record.get("match") if isinstance(record, dict) else None
    if not isinstance(match_payload, dict):
        return None
    source = normalize_text(match_payload.get("source", "")) or "snapshot:analysis"
    app_match = _app_match_from_payload(match_payload, source=source)
    if app_match is not None:
        return app_match
    try:
        home_team = normalize_text(match_payload.get("home_team", ""))
        away_team = normalize_text(match_payload.get("away_team", ""))
        league = normalize_text(match_payload.get("league", ""))
        match_time = normalize_text(match_payload.get("match_time", "")) or "00:00"
        match_date = normalize_text(match_payload.get("match_date", ""))
        if home_team and away_team and league and _looks_like_match_time(match_time) and _looks_like_date(match_date):
            return AppMatch(
                home_team=home_team,
                away_team=away_team,
                league=league,
                match_time=match_time,
                match_date=match_date,
                odds_home=_safe_float(match_payload.get("odds_home"), default=2.20),
                odds_draw=_safe_float(match_payload.get("odds_draw"), default=3.10),
                odds_away=_safe_float(match_payload.get("odds_away"), default=2.80),
                handicap_line=_safe_float(match_payload.get("handicap_line"), default=0.0),
                opening_odds_home=_safe_float(match_payload.get("opening_odds_home"), default=0.0),
                opening_odds_draw=_safe_float(match_payload.get("opening_odds_draw"), default=0.0),
                opening_odds_away=_safe_float(match_payload.get("opening_odds_away"), default=0.0),
                return_rate=_safe_float(match_payload.get("return_rate"), default=0.0),
                kelly_home=_safe_float(match_payload.get("kelly_home"), default=0.0),
                kelly_draw=_safe_float(match_payload.get("kelly_draw"), default=0.0),
                kelly_away=_safe_float(match_payload.get("kelly_away"), default=0.0),
                source=source,
                source_id=normalize_text(match_payload.get("source_id", "")),
                competition_group=normalize_text(match_payload.get("competition_group", "")),
                group_round=_optional_int(match_payload.get("group_round")) or 0,
                home_points=_optional_int(match_payload.get("home_points")),
                away_points=_optional_int(match_payload.get("away_points")),
                home_goal_diff=_optional_int(match_payload.get("home_goal_diff")),
                away_goal_diff=_optional_int(match_payload.get("away_goal_diff")),
                home_group_rank=_optional_int(match_payload.get("home_group_rank")),
                away_group_rank=_optional_int(match_payload.get("away_group_rank")),
            )
    except Exception:
        pass
    if fallback_match_id and "|" in str(fallback_match_id):
        parts = str(fallback_match_id).split("|")
        if len(parts) >= 4:
            fallback_payload = dict(match_payload)
            fallback_payload.setdefault("match_date", parts[0])
            fallback_payload.setdefault("league", parts[1])
            fallback_payload.setdefault("home_team", parts[2])
            fallback_payload.setdefault("away_team", parts[3])
            fallback_payload.setdefault("match_time", "00:00")
            return _app_match_from_payload(fallback_payload, source=source)
    return None


def backfill_prediction_snapshot_trace_fact_refs(max_records: int = 5000) -> dict:
    limit = max(1, int(max_records))
    snapshots = STATE_STORE.load_prediction_snapshots()
    report = {
        "checked": 0,
        "updated": 0,
        "already_ready": 0,
        "missing_prediction": 0,
        "invalid_match": 0,
        "skipped_limit": 0,
        "fact_ref_kinds": {},
        "updated_items": [],
    }
    if not isinstance(snapshots, dict) or not snapshots:
        return report

    changed = False
    for match_id, record in snapshots.items():
        if report["checked"] >= limit:
            report["skipped_limit"] = max(0, len(snapshots) - int(report["checked"]))
            break
        if not isinstance(record, dict):
            continue
        report["checked"] += 1
        prediction = record.get("prediction")
        if not isinstance(prediction, dict):
            report["missing_prediction"] += 1
            continue
        trace = prediction.get("trace") if isinstance(prediction.get("trace"), dict) else record.get("trace")
        fact_refs = trace.get("fact_refs") if isinstance(trace, dict) else []
        if isinstance(trace, dict) and trace.get("trace_id") and isinstance(fact_refs, list) and fact_refs:
            report["already_ready"] += 1
            continue
        app_match = _snapshot_record_match(record, fallback_match_id=match_id)
        if app_match is None:
            report["invalid_match"] += 1
            continue

        stored_prediction = dict(prediction)
        if isinstance(record.get("trace"), dict) and not isinstance(stored_prediction.get("trace"), dict):
            stored_prediction["trace"] = dict(record["trace"])
        trace = _ensure_prediction_trace(app_match, stored_prediction)
        record["prediction"] = stored_prediction
        if trace:
            record["trace"] = dict(trace)
            for item in trace.get("fact_refs", []) if isinstance(trace.get("fact_refs"), list) else []:
                if not isinstance(item, dict):
                    continue
                kind = str(item.get("kind") or "-")
                fact_counts = report["fact_ref_kinds"]
                if isinstance(fact_counts, dict):
                    fact_counts[kind] = int(fact_counts.get(kind, 0) or 0) + 1
        record["trace_backfilled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        snapshots[match_id] = record
        report["updated"] += 1
        if len(report["updated_items"]) < 20:
            report["updated_items"].append(
                {
                    "match_id": match_id,
                    "trace_id": trace.get("trace_id") if isinstance(trace, dict) else "",
                    "fact_ref_count": len(trace.get("fact_refs", [])) if isinstance(trace, dict) and isinstance(trace.get("fact_refs"), list) else 0,
                }
            )
        changed = True

    if changed:
        STATE_STORE.save_prediction_snapshots(snapshots)
    return report


def _strategy_allowlist_marker(
    match: AppMatch,
    prediction: dict,
    *,
    allowlist_file: str,
    exported_at: str,
) -> dict:
    admission = prediction.get("strategy_admission") if isinstance(prediction, dict) else {}
    if not isinstance(admission, dict) or str(admission.get("decision") or "") != "allow":
        return {}
    return {
        "status": "pending_settlement",
        "decision": "allow",
        "label": str(admission.get("label") or "\u6b63\u5f0f\u653e\u884c"),
        "exported_at": exported_at,
        "file": str(allowlist_file or ""),
        "match_id": match.match_id,
        "recommendation": prediction.get("recommendation"),
        "confidence": round(_safe_float(prediction.get("confidence"), 0.0), 4),
        "risk_level": prediction.get("risk_level"),
        "active_count": int(_safe_int(admission.get("active_count"), 0) or 0),
        "shadow_count": int(_safe_int(admission.get("shadow_count"), 0) or 0),
        "single_play_count": int(_safe_int(admission.get("single_play_count"), 0) or 0),
        "top_play": admission.get("top_play"),
        "top_pick": admission.get("top_pick"),
        "top_confidence": round(_safe_float(admission.get("top_confidence"), 0.0), 4),
        "reasons": admission.get("reasons") if isinstance(admission.get("reasons"), list) else [],
    }


def _existing_strategy_allowlist_marker(record: dict | None) -> dict:
    if not isinstance(record, dict):
        return {}
    marker = record.get("strategy_allowlist")
    if isinstance(marker, dict):
        return dict(marker)
    prediction = record.get("prediction")
    if isinstance(prediction, dict) and isinstance(prediction.get("strategy_allowlist"), dict):
        return dict(prediction["strategy_allowlist"])
    return {}


def _attach_strategy_allowlist_marker(record: dict, marker: dict) -> dict:
    if not marker:
        return record
    updated = dict(record)
    updated["strategy_allowlist"] = dict(marker)
    prediction = dict(updated.get("prediction") or {})
    prediction["strategy_allowlist"] = dict(marker)
    updated["prediction"] = prediction
    return updated


def mark_strategy_allowlist_snapshots(
    items: Iterable[tuple[AppMatch, dict]],
    *,
    allowlist_file: str,
    exported_at: datetime | str | None = None,
) -> dict:
    timestamp = (
        exported_at.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(exported_at, datetime)
        else str(exported_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    snapshots = STATE_STORE.load_prediction_snapshots()
    summary = {"marked": 0, "skipped": 0, "items": []}
    for match, prediction in items:
        if not isinstance(match, AppMatch) or not isinstance(prediction, dict):
            summary["skipped"] += 1
            continue
        marker = _strategy_allowlist_marker(match, prediction, allowlist_file=allowlist_file, exported_at=timestamp)
        if not marker:
            summary["skipped"] += 1
            continue
        prediction["strategy_allowlist"] = dict(marker)
        trace = _ensure_prediction_trace(match, prediction)
        existing = snapshots.get(match.match_id) if isinstance(snapshots, dict) else None
        record = dict(existing) if isinstance(existing, dict) else {}
        record.update(
            {
                "saved_at": record.get("saved_at") or timestamp,
                "match": serialize_match(match),
                "prediction": dict(prediction),
                "market_snapshot": record.get("market_snapshot") if isinstance(record.get("market_snapshot"), dict) else _market_snapshot_fields_from_match(match),
            }
        )
        if trace:
            record["trace"] = dict(trace)
        record = _attach_strategy_allowlist_marker(record, marker)
        STATE_STORE.upsert_prediction_snapshot(match.match_id, record)
        STATE_STORE.upsert_analysis_history(match.match_id, record)
        persist_market_snapshot(match)
        snapshots[match.match_id] = record
        summary["marked"] += 1
        if len(summary["items"]) < 20:
            summary["items"].append(
                {
                    "match_id": match.match_id,
                    "match_date": match.match_date,
                    "league": match.league,
                    "home_team": match.home_team,
                    "away_team": match.away_team,
                    "file": marker.get("file"),
                }
            )
    return summary


def _strategy_allowlist_settlement_fields(prediction: dict | None) -> dict:
    marker = prediction.get("strategy_allowlist") if isinstance(prediction, dict) else {}
    if not isinstance(marker, dict) or str(marker.get("decision") or "") != "allow":
        return {
            "strategy_allowlist_status": "",
            "strategy_allowlist_file": "",
            "strategy_allowlist_exported_at": "",
            "strategy_allowlist_decision": "",
            "strategy_allowlist_label": "",
        }
    return {
        "strategy_allowlist_status": "settled",
        "strategy_allowlist_file": str(marker.get("file") or ""),
        "strategy_allowlist_exported_at": str(marker.get("exported_at") or ""),
        "strategy_allowlist_decision": str(marker.get("decision") or ""),
        "strategy_allowlist_label": str(marker.get("label") or ""),
    }


def _strategy_admission_settlement_fields(prediction: dict | None) -> dict:
    admission = prediction.get("strategy_admission") if isinstance(prediction, dict) else {}
    if not isinstance(admission, dict):
        admission = {}
    guard = admission.get("agent_replay_guard") if isinstance(admission.get("agent_replay_guard"), dict) else {}
    reasons = admission.get("reasons") if isinstance(admission.get("reasons"), list) else []
    actions = guard.get("actions") if isinstance(guard.get("actions"), list) else []
    return {
        "strategy_admission_decision": str(admission.get("decision") or ""),
        "strategy_admission_label": str(admission.get("label") or ""),
        "strategy_admission_release_allowed": bool(admission.get("release_allowed")),
        "strategy_admission_reasons": [str(item) for item in reasons if item],
        "agent_replay_guard_applied": bool(guard.get("applied")),
        "agent_replay_guard_top_agent": str(guard.get("top_agent") or ""),
        "agent_replay_guard_prediction_miss_rate": (
            round(_safe_float(guard.get("top_prediction_miss_rate"), 0.0), 4)
            if guard.get("top_prediction_miss_rate") is not None
            else None
        ),
        "agent_replay_guard_handicap_miss_rate": (
            round(_safe_float(guard.get("top_handicap_miss_rate"), 0.0), 4)
            if guard.get("top_handicap_miss_rate") is not None
            else None
        ),
        "agent_replay_guard_actions": [str(item) for item in actions if item],
    }


def _market_entropy_settlement_fields(prediction: dict | None) -> dict:
    entropy = prediction.get("market_entropy") if isinstance(prediction, dict) else {}
    if not isinstance(entropy, dict):
        entropy = {}
    risk = prediction.get("market_entropy_risk") if isinstance(prediction, dict) else {}
    if not isinstance(risk, dict):
        risk = {}
    sequence = entropy.get("sequence") if isinstance(entropy.get("sequence"), dict) else {}
    signals = entropy.get("signals") if isinstance(entropy.get("signals"), list) else []
    supervisor = prediction.get("supervisor") if isinstance(prediction, dict) else {}
    if not isinstance(supervisor, dict):
        supervisor = {}
    next_actions = supervisor.get("next_actions") if isinstance(supervisor.get("next_actions"), list) else []
    return {
        "market_entropy_level": str(entropy.get("level") or ""),
        "market_entropy_score": round(_safe_float(entropy.get("score"), 0.0), 4) if entropy else None,
        "market_entropy_signals": [str(item) for item in signals if item],
        "market_entropy_max_step_change": round(_safe_float(sequence.get("max_step_change"), 0.0), 4) if sequence else None,
        "market_entropy_max_velocity": round(_safe_float(sequence.get("max_abs_velocity_per_minute"), 0.0), 5) if sequence else None,
        "market_entropy_history_samples": int(_safe_int(sequence.get("sample_count"), 0) or 0) if sequence else 0,
        "market_entropy_kelly_span": round(_safe_float(entropy.get("kelly_span"), 0.0), 4) if entropy else None,
        "market_entropy_pick_kelly_gap": round(_safe_float(entropy.get("pick_kelly_gap"), 0.0), 4) if entropy else None,
        "market_entropy_risk_applied": bool(risk.get("applied")),
        "market_entropy_risk_reason": str(risk.get("reason") or ""),
        "supervisor_status": str(supervisor.get("status") or ""),
        "supervisor_next_actions": [str(item) for item in next_actions if item],
    }


def _handicap_margin_settlement_fields(prediction: dict | None) -> dict:
    signal = prediction.get("handicap_margin_consistency") if isinstance(prediction, dict) else {}
    if not isinstance(signal, dict):
        signal = {}
    signals = signal.get("signals") if isinstance(signal.get("signals"), list) else []
    return {
        "handicap_margin_level": str(signal.get("level") or ""),
        "handicap_margin_score": round(_safe_float(signal.get("score"), 0.0), 4) if signal else None,
        "handicap_margin_signals": [str(item) for item in signals if item],
        "handicap_margin_line": round(_safe_float(signal.get("handicap_line"), 0.0), 4) if signal else None,
        "handicap_margin_model_goals": round(_safe_float(signal.get("model_margin_goals"), 0.0), 4) if signal else None,
        "handicap_margin_market_side": str(signal.get("market_side") or ""),
        "handicap_margin_model_side": str(signal.get("model_side") or ""),
        "handicap_margin_depth_gap": round(_safe_float(signal.get("depth_gap"), 0.0), 4) if signal else None,
        "handicap_margin_pick_side": str(signal.get("handicap_pick_side") or ""),
    }


def _draw_release_guard_settlement_fields(prediction: dict | None) -> dict:
    guard = prediction.get("draw_release_guard") if isinstance(prediction, dict) else {}
    if not isinstance(guard, dict):
        guard = {}
    evidence = guard.get("evidence") if isinstance(guard.get("evidence"), dict) else {}
    blocked = bool(guard.get("blocked"))
    base_takeover = bool(guard.get("base_takeover"))
    weak_score = bool(guard.get("weak_score"))
    if blocked:
        status = "blocked"
    elif base_takeover:
        status = "allowed"
    elif weak_score:
        status = "watch"
    elif guard:
        status = "idle"
    else:
        status = ""
    return {
        "draw_score": round(_safe_float(prediction.get("draw_score"), 0.0), 4) if isinstance(prediction, dict) and prediction.get("draw_score") is not None else None,
        "draw_grade": str(prediction.get("draw_grade") or "") if isinstance(prediction, dict) else "",
        "draw_takeover": bool(prediction.get("draw_takeover")) if isinstance(prediction, dict) and "draw_takeover" in prediction else None,
        "draw_release_guard_status": status,
        "draw_release_guard_blocked": blocked if guard else False,
        "draw_release_guard_reason": str(guard.get("reason") or ""),
        "draw_release_guard_odds_bucket": str(guard.get("odds_bucket") or ""),
        "draw_release_guard_odds_draw": round(_safe_float(guard.get("odds_draw"), 0.0), 4) if guard.get("odds_draw") is not None else None,
        "draw_release_guard_min_score": round(_safe_float(guard.get("min_score"), 0.0), 4) if guard.get("min_score") is not None else None,
        "draw_release_guard_base_takeover": base_takeover if guard else False,
        "draw_release_guard_weak_score": weak_score if guard else False,
        "draw_release_guard_evidence_source": str(evidence.get("source") or ""),
        "draw_release_guard_evidence_precision": round(_safe_float(evidence.get("precision"), 0.0), 6) if evidence.get("precision") is not None else None,
        "draw_release_guard_evidence_draw_rate": round(_safe_float(evidence.get("draw_rate"), 0.0), 6) if evidence.get("draw_rate") is not None else None,
        "draw_release_guard_evidence_lift": round(_safe_float(evidence.get("lift"), 0.0), 6) if evidence.get("lift") is not None else None,
    }


def _agent_trace_settlement_fields(prediction: dict | None) -> dict:
    supervisor = prediction.get("supervisor") if isinstance(prediction, dict) else {}
    if not isinstance(supervisor, dict):
        supervisor = {}
    trace = prediction.get("trace") if isinstance(prediction, dict) else {}
    if not isinstance(trace, dict):
        trace = {}
    agents = supervisor.get("agents") if isinstance(supervisor.get("agents"), list) else []
    agent_statuses: dict[str, str] = {}
    agent_actions: list[str] = []
    alert_agents: list[str] = []
    watch_agents: list[str] = []
    blocked_agents: list[str] = []
    agent_rationales: dict[str, str] = {}
    for item in agents:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        status = str(item.get("status") or "").strip().lower()
        agent_statuses[name] = status
        if status == "alert":
            alert_agents.append(name)
        elif status == "watch":
            watch_agents.append(name)
        elif status == "blocked":
            blocked_agents.append(name)
        rationale = str(item.get("rationale") or "").strip()
        if rationale:
            agent_rationales[name] = rationale
        actions = item.get("actions") if isinstance(item.get("actions"), list) else []
        for action in actions:
            action_text = str(action or "").strip()
            if action_text and action_text not in agent_actions:
                agent_actions.append(action_text)
    return {
        "trace_id": str(trace.get("trace_id") or ""),
        "trace_version": str(trace.get("trace_version") or ""),
        "prompt_version": str(trace.get("prompt_version") or ""),
        "supervisor_agent_statuses": agent_statuses,
        "supervisor_alert_agents": alert_agents,
        "supervisor_watch_agents": watch_agents,
        "supervisor_blocked_agents": blocked_agents,
        "supervisor_agent_actions": agent_actions,
        "supervisor_agent_rationales": agent_rationales,
    }


def persist_prediction_snapshot(match: AppMatch, prediction: dict) -> None:
    if not isinstance(prediction, dict):
        return
    snapshots = STATE_STORE.load_prediction_snapshots()
    existing = snapshots.get(match.match_id) if isinstance(snapshots, dict) else None
    marker = _existing_strategy_allowlist_marker(existing)
    stored_prediction = dict(prediction)
    trace = _ensure_prediction_trace(match, stored_prediction)
    if trace:
        prediction["trace"] = dict(trace)
    if marker:
        stored_prediction["strategy_allowlist"] = dict(marker)
        prediction["strategy_allowlist"] = dict(marker)
    market_snapshot = _market_snapshot_fields_from_match(match)
    record = {
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "match": serialize_match(match),
        "prediction": stored_prediction,
        "market_snapshot": market_snapshot,
    }
    if trace:
        record["trace"] = dict(trace)
    record = _attach_strategy_allowlist_marker(record, marker)
    STATE_STORE.upsert_prediction_snapshot(match.match_id, record)
    STATE_STORE.upsert_analysis_history(match.match_id, record)
    persist_market_snapshot(match)


def persist_prediction_snapshots(items: Iterable[tuple[AppMatch, dict]]) -> dict[str, int]:
    pairs = [
        (match, prediction)
        for match, prediction in items
        if isinstance(match, AppMatch) and isinstance(prediction, dict)
    ]
    if not pairs:
        return {"snapshot_count": 0, "analysis_count": 0, "market_snapshot_count": 0}

    snapshots = STATE_STORE.load_prediction_snapshots()
    if not isinstance(snapshots, dict):
        snapshots = {}
    history = STATE_STORE.load_analysis_history()
    if not isinstance(history, dict):
        history = {}
    market_snapshots = STATE_STORE.load_market_snapshots()
    if not isinstance(market_snapshots, dict):
        market_snapshots = {}

    saved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    snapshot_count = 0
    analysis_count = 0
    market_snapshot_count = 0

    for match, prediction in pairs:
        existing = snapshots.get(match.match_id) if isinstance(snapshots, dict) else None
        marker = _existing_strategy_allowlist_marker(existing)
        stored_prediction = dict(prediction)
        trace = _ensure_prediction_trace(match, stored_prediction)
        if trace:
            prediction["trace"] = dict(trace)
        if marker:
            stored_prediction["strategy_allowlist"] = dict(marker)
            prediction["strategy_allowlist"] = dict(marker)
        record = {
            "saved_at": saved_at,
            "match": serialize_match(match),
            "prediction": stored_prediction,
            "market_snapshot": _market_snapshot_fields_from_match(match),
        }
        if trace:
            record["trace"] = dict(trace)
        record = _attach_strategy_allowlist_marker(record, marker)
        _ordered_upsert(snapshots, match.match_id, record, limit=3000)
        _ordered_upsert(history, match.match_id, record, limit=5000)
        snapshot_count += 1
        analysis_count += 1

        if not _has_market_snapshot_fields(match):
            continue
        market_record = _market_snapshot_record_for_match(match, saved_at=saved_at)
        for snapshot_id in _market_snapshot_keys_for_match(match):
            merged_market_record = _merge_market_snapshot_record(market_snapshots.get(snapshot_id), market_record)
            _ordered_upsert(market_snapshots, snapshot_id, merged_market_record, limit=5000)
            market_snapshot_count += 1

    STATE_STORE.save_prediction_snapshots(snapshots)
    STATE_STORE.save_analysis_history(history)
    if market_snapshot_count:
        STATE_STORE.save_market_snapshots(market_snapshots)
        _MARKET_SNAPSHOT_RECORD_CACHE["signature"] = _state_store_path_signature("market_snapshots_file")
        _MARKET_SNAPSHOT_RECORD_CACHE["items"] = market_snapshots

    return {
        "snapshot_count": snapshot_count,
        "analysis_count": analysis_count,
        "market_snapshot_count": market_snapshot_count,
    }


def backfill_analysis_history_from_prediction_snapshots(max_backfilled: int = 5000) -> dict:
    snapshots = STATE_STORE.load_prediction_snapshots()
    history = STATE_STORE.load_analysis_history()
    backfilled = 0
    for match_id, record in snapshots.items():
        if backfilled >= max(1, int(max_backfilled)):
            break
        if match_id in history or not isinstance(record, dict):
            continue
        prediction = record.get("prediction")
        match_payload = record.get("match")
        if not isinstance(prediction, dict) or not isinstance(match_payload, dict):
            continue
        history_record = dict(record)
        history_record["backfilled_from"] = "prediction_snapshots"
        history_record["backfilled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE_STORE.upsert_analysis_history(match_id, history_record)
        backfilled += 1
    return {
        "snapshot_count": len(snapshots),
        "history_count": len(history) + backfilled,
        "backfilled": backfilled,
    }


def backfill_analysis_history_trace_fact_refs(max_records: int = 5000) -> dict:
    limit = max(1, int(max_records))
    history = STATE_STORE.load_analysis_history()
    report = {
        "checked": 0,
        "updated": 0,
        "already_ready": 0,
        "missing_prediction": 0,
        "invalid_match": 0,
        "skipped_limit": 0,
        "fact_ref_kinds": {},
        "updated_items": [],
    }
    if not isinstance(history, dict) or not history:
        return report

    changed = False
    for match_id, record in reversed(list(history.items())):
        if report["checked"] >= limit:
            report["skipped_limit"] = max(0, len(history) - int(report["checked"]))
            break
        if not isinstance(record, dict):
            continue
        report["checked"] += 1
        prediction = record.get("prediction")
        if not isinstance(prediction, dict):
            report["missing_prediction"] += 1
            continue
        trace = prediction.get("trace") if isinstance(prediction.get("trace"), dict) else record.get("trace")
        fact_refs = trace.get("fact_refs") if isinstance(trace, dict) else []
        if isinstance(trace, dict) and trace.get("trace_id") and isinstance(fact_refs, list) and fact_refs:
            report["already_ready"] += 1
            continue

        app_match = _snapshot_record_match(record, fallback_match_id=match_id)
        if app_match is None:
            report["invalid_match"] += 1
            continue

        stored_prediction = dict(prediction)
        if isinstance(record.get("trace"), dict) and not isinstance(stored_prediction.get("trace"), dict):
            stored_prediction["trace"] = dict(record["trace"])
        trace = _ensure_prediction_trace(app_match, stored_prediction)
        record["prediction"] = stored_prediction
        if trace:
            record["trace"] = dict(trace)
            for item in trace.get("fact_refs", []) if isinstance(trace.get("fact_refs"), list) else []:
                if not isinstance(item, dict):
                    continue
                kind = str(item.get("kind") or "-")
                fact_counts = report["fact_ref_kinds"]
                if isinstance(fact_counts, dict):
                    fact_counts[kind] = int(fact_counts.get(kind, 0) or 0) + 1
        record["trace_backfilled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history[match_id] = record
        report["updated"] += 1
        changed = True
        if len(report["updated_items"]) < 20:
            report["updated_items"].append(
                {
                    "match_id": match_id,
                    "trace_id": trace.get("trace_id") if isinstance(trace, dict) else "",
                    "fact_ref_count": len(trace.get("fact_refs", [])) if isinstance(trace, dict) and isinstance(trace.get("fact_refs"), list) else 0,
                }
            )

    if changed:
        STATE_STORE.save_analysis_history(history)
    return report


def repair_prediction_snapshots_from_analysis_history(
    lookback_days: int = 3,
    max_restored: int = 100,
) -> dict:
    lookback_days = max(0, min(int(lookback_days), 14))
    max_restored = max(1, int(max_restored))
    history_trace_backfill = backfill_analysis_history_trace_fact_refs()
    snapshots = STATE_STORE.load_prediction_snapshots()
    history = STATE_STORE.load_analysis_history()
    settled_ids = {str(item.get("match_id", "")) for item in STATE_STORE.load_settlements() if item.get("match_id")}
    today = datetime.now().date()
    restored = 0
    checked = 0
    skipped_settled = 0
    skipped_existing = 0
    skipped_out_of_window = 0
    restored_items: list[dict] = []

    for match_id, record in reversed(list(history.items())):
        if restored >= max_restored:
            break
        checked += 1
        if match_id in snapshots:
            skipped_existing += 1
            continue
        if match_id in settled_ids:
            skipped_settled += 1
            continue
        if not isinstance(record, dict) or not isinstance(record.get("prediction"), dict):
            continue
        match_payload = record.get("match")
        app_match = _app_match_from_payload(match_payload, source="analysis_history")
        if app_match is None:
            continue
        try:
            match_date = datetime.strptime(app_match.match_date, "%Y-%m-%d").date()
        except Exception:
            continue
        age_days = (today - match_date).days
        if age_days < 0 or age_days > lookback_days:
            skipped_out_of_window += 1
            continue
        restored_record = dict(record)
        restored_record["restored_from"] = "analysis_history"
        restored_record["restored_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE_STORE.upsert_prediction_snapshot(match_id, restored_record)
        snapshots[match_id] = restored_record
        restored += 1
        if len(restored_items) < 10:
            restored_items.append(
                {
                    "match_id": match_id,
                    "match_date": app_match.match_date,
                    "league": app_match.league,
                    "home_team": app_match.home_team,
                    "away_team": app_match.away_team,
                }
            )

    return {
        "checked": checked,
        "restored": restored,
        "skipped_existing": skipped_existing,
        "skipped_settled": skipped_settled,
        "skipped_out_of_window": skipped_out_of_window,
        "lookback_days": lookback_days,
        "items": restored_items,
        "history_trace_fact_ref_backfill": history_trace_backfill,
    }


def load_prediction_snapshot_cache() -> dict[str, dict]:
    snapshots = STATE_STORE.load_prediction_snapshots()
    cache: dict[str, dict] = {}
    for match_id, record in snapshots.items():
        if not isinstance(record, dict):
            continue
        prediction = record.get("prediction")
        if isinstance(prediction, dict):
            cache[match_id] = prediction
    return cache


def build_result_recovery_snapshot_audit(
    snapshot_records: dict[str, dict],
    settlements: list[dict],
    *,
    lookback_days: int = 2,
    now: datetime | None = None,
    item_limit: int = 20,
) -> dict[str, object]:
    lookback_days = max(0, min(int(lookback_days), 14))
    current_date = (now or datetime.now()).date()
    settled_ids = {str(item.get("match_id", "")) for item in settlements if isinstance(item, dict) and item.get("match_id")}
    audit: dict[str, object] = {
        "total_snapshots": 0,
        "already_settled": 0,
        "pending": 0,
        "in_window": 0,
        "out_of_window": 0,
        "future": 0,
        "invalid": 0,
        "recoverable_schedule_id": 0,
        "recoverable_titan": 0,
        "recoverable_cache_source": 0,
        "missing_source_id": 0,
        "non_titan_source": 0,
        "missing_prediction": 0,
        "lookback_days": lookback_days,
        "items": [],
    }
    items: list[dict[str, object]] = []
    for match_id, record in snapshot_records.items():
        if not isinstance(record, dict):
            audit["invalid"] = int(audit["invalid"]) + 1
            continue
        audit["total_snapshots"] = int(audit["total_snapshots"]) + 1
        if match_id in settled_ids:
            audit["already_settled"] = int(audit["already_settled"]) + 1
            continue
        match_payload = record.get("match")
        if not isinstance(match_payload, dict):
            audit["invalid"] = int(audit["invalid"]) + 1
            continue
        app_match = _app_match_from_payload(match_payload, source=str(match_payload.get("source") or "snapshot_audit"))
        if app_match is None:
            audit["invalid"] = int(audit["invalid"]) + 1
            continue
        try:
            match_date = datetime.strptime(app_match.match_date, "%Y-%m-%d").date()
        except Exception:
            audit["invalid"] = int(audit["invalid"]) + 1
            continue
        age_days = (current_date - match_date).days
        if age_days < 0:
            audit["future"] = int(audit["future"]) + 1
            continue
        if age_days > lookback_days:
            audit["out_of_window"] = int(audit["out_of_window"]) + 1
            continue
        audit["pending"] = int(audit["pending"]) + 1
        audit["in_window"] = int(audit["in_window"]) + 1
        prediction = record.get("prediction")
        if not isinstance(prediction, dict):
            audit["missing_prediction"] = int(audit["missing_prediction"]) + 1
        source = normalize_text(match_payload.get("source", ""))
        source_id = normalize_text(match_payload.get("source_id", ""))
        schedule_id = _snapshot_result_schedule_id(source, source_id)
        source_key = source.lower()
        if not source_id:
            audit["missing_source_id"] = int(audit["missing_source_id"]) + 1
            status = "missing_source_id"
        elif schedule_id:
            audit["recoverable_schedule_id"] = int(audit["recoverable_schedule_id"]) + 1
            if "titan" in source_key:
                audit["recoverable_titan"] = int(audit["recoverable_titan"]) + 1
                status = "recoverable_titan"
            else:
                audit["recoverable_cache_source"] = int(audit["recoverable_cache_source"]) + 1
                status = "recoverable_cache_schedule"
        else:
            audit["non_titan_source"] = int(audit["non_titan_source"]) + 1
            status = "non_titan_source"
        if len(items) < max(0, int(item_limit)):
            items.append(
                {
                    "match_id": match_id,
                    "match_date": app_match.match_date,
                    "league": app_match.league,
                    "home_team": app_match.home_team,
                    "away_team": app_match.away_team,
                    "source": source or "-",
                    "source_id": source_id,
                    "age_days": age_days,
                    "status": status,
                }
            )
    audit["items"] = items
    return audit


def get_prediction_snapshot_migration_report() -> dict:
    return STATE_STORE.load_snapshot_migration_report()


def _load_video_review_items() -> list[dict]:
    if not VIDEO_REVIEW_FILE.exists():
        return []
    try:
        payload = json.loads(VIDEO_REVIEW_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = payload.get("items") if isinstance(payload, dict) else payload
    return [dict(item) for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _save_video_review_items(items: list[dict], limit: int = 500) -> None:
    VIDEO_REVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": items[-max(1, int(limit)):],
    }
    VIDEO_REVIEW_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_video_reviews(limit: int = 50) -> list[dict]:
    items = _load_video_review_items()
    items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    if limit <= 0:
        return items
    return items[: max(0, int(limit))]


def get_video_review_for_match(match_id: str | object) -> dict:
    resolved_id = str(match_id or "")
    for item in get_video_reviews(limit=0):
        if str(item.get("match_id") or "") == resolved_id:
            return dict(item)
    return {}


def _video_file_metadata(video_path: Path) -> dict:
    stat = video_path.stat()
    payload: dict[str, object] = {
        "path": str(video_path),
        "filename": video_path.name,
        "size_bytes": int(stat.st_size),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
    }
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        payload["probe_status"] = "ffprobe_unavailable"
        return payload
    command = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,duration,avg_frame_rate",
        "-of",
        "json",
        str(video_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
        data = json.loads(result.stdout or "{}")
        stream = data.get("streams", [{}])[0] if isinstance(data.get("streams"), list) and data.get("streams") else {}
        payload.update(
            {
                "probe_status": "ok" if result.returncode == 0 else "ffprobe_failed",
                "width": _safe_int(stream.get("width")),
                "height": _safe_int(stream.get("height")),
                "duration_seconds": round(_safe_float(stream.get("duration"), default=0.0), 2),
                "avg_frame_rate": str(stream.get("avg_frame_rate") or ""),
            }
        )
    except Exception as exc:
        payload["probe_status"] = "probe_error"
        payload["probe_error"] = str(exc)
    return payload


def _video_review_frame_plan(duration_seconds: float | int | None, *, interval_seconds: int, max_frames: int) -> list[dict]:
    interval = max(1, int(interval_seconds))
    limit = max(1, int(max_frames))
    duration = max(0.0, _safe_float(duration_seconds, default=0.0))
    if duration <= 0:
        return [{"index": index + 1, "timestamp_seconds": index * interval} for index in range(min(limit, 6))]
    timestamps: list[int] = []
    current = 0
    while current <= int(duration) and len(timestamps) < limit:
        timestamps.append(current)
        current += interval
    if timestamps and timestamps[-1] < int(duration) and len(timestamps) < limit:
        timestamps.append(int(duration))
    return [{"index": index + 1, "timestamp_seconds": stamp} for index, stamp in enumerate(timestamps[:limit])]


def _extract_video_review_frames(video_path: Path, review_id: str, *, interval_seconds: int, max_frames: int) -> tuple[list[dict], dict]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return [], {"status": "skipped", "reason": "ffmpeg_unavailable"}
    frame_dir = VIDEO_REVIEW_DIR / review_id / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    interval = max(1, int(interval_seconds))
    limit = max(1, int(max_frames))
    output_pattern = str(frame_dir / "frame_%04d.jpg")
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps=1/{interval}",
        "-frames:v",
        str(limit),
        output_pattern,
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    except Exception as exc:
        return [], {"status": "failed", "reason": str(exc)}
    frames = sorted(frame_dir.glob("frame_*.jpg"))
    frame_items = [
        {
            "index": index + 1,
            "path": str(path),
            "timestamp_seconds": index * interval,
        }
        for index, path in enumerate(frames)
    ]
    return frame_items, {
        "status": "ok" if result.returncode == 0 and frame_items else "failed",
        "returncode": result.returncode,
        "frame_count": len(frame_items),
        "stderr_tail": (result.stderr or "")[-500:],
    }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _video_review_frame_visual_analysis(frames: list[dict]) -> dict:
    if not frames:
        return {
            "status": "no_frames",
            "frame_count": 0,
            "summary_text": "no key frames available for visual analysis",
            "frame_rows": [],
            "tags": [],
        }
    try:
        from PIL import Image, ImageChops, ImageFilter, ImageStat
    except Exception as exc:
        return {
            "status": "vision_library_unavailable",
            "frame_count": len(frames),
            "summary_text": f"Pillow unavailable: {exc}",
            "frame_rows": [],
            "tags": ["vision_dependency_missing"],
        }

    rows: list[dict] = []
    previous = None
    for frame in frames:
        path = Path(str(frame.get("path") or ""))
        if not path.exists() or not path.is_file():
            rows.append(
                {
                    "index": _safe_int(frame.get("index")),
                    "timestamp_seconds": _safe_int(frame.get("timestamp_seconds")),
                    "status": "missing_file",
                    "path": str(path),
                }
            )
            continue
        try:
            with Image.open(path) as image:
                gray = image.convert("L").resize((160, 90))
                stat = ImageStat.Stat(gray)
                brightness = float(stat.mean[0])
                contrast = float(stat.stddev[0])
                edge = gray.filter(ImageFilter.FIND_EDGES)
                edge_score = float(ImageStat.Stat(edge).mean[0])
                motion_score = 0.0
                if previous is not None:
                    diff = ImageChops.difference(gray, previous)
                    motion_score = float(ImageStat.Stat(diff).mean[0])
                previous = gray.copy()
        except Exception as exc:
            rows.append(
                {
                    "index": _safe_int(frame.get("index")),
                    "timestamp_seconds": _safe_int(frame.get("timestamp_seconds")),
                    "status": "read_failed",
                    "path": str(path),
                    "error": str(exc),
                }
            )
            continue
        quality = "good"
        if brightness < 35 or brightness > 225:
            quality = "exposure_risk"
        elif contrast < 18 or edge_score < 4:
            quality = "low_detail"
        rows.append(
            {
                "index": _safe_int(frame.get("index")),
                "timestamp_seconds": _safe_int(frame.get("timestamp_seconds")),
                "status": "ok",
                "path": str(path),
                "brightness": round(brightness, 2),
                "contrast": round(contrast, 2),
                "edge_score": round(edge_score, 2),
                "motion_score": round(motion_score, 2),
                "quality": quality,
            }
        )

    ok_rows = [row for row in rows if row.get("status") == "ok"]
    brightness_values = [_safe_float(row.get("brightness")) for row in ok_rows]
    contrast_values = [_safe_float(row.get("contrast")) for row in ok_rows]
    edge_values = [_safe_float(row.get("edge_score")) for row in ok_rows]
    motion_values = [_safe_float(row.get("motion_score")) for row in ok_rows[1:]]
    tags: list[str] = []
    avg_brightness = _mean(brightness_values)
    avg_contrast = _mean(contrast_values)
    avg_edge = _mean(edge_values)
    avg_motion = _mean(motion_values)
    if avg_brightness < 45:
        tags.append("low_light_evidence")
    elif avg_brightness > 215:
        tags.append("overexposed_evidence")
    if avg_contrast < 22 or avg_edge < 5:
        tags.append("low_detail_frames")
    if avg_motion >= 18:
        tags.append("high_scene_change")
    elif ok_rows and avg_motion < 4:
        tags.append("low_motion_evidence")
    usable_count = len(ok_rows)
    status = "ready" if usable_count else "no_readable_frames"
    top_frames = sorted(
        ok_rows,
        key=lambda row: (
            -(_safe_float(row.get("motion_score")) + _safe_float(row.get("edge_score")) + _safe_float(row.get("contrast")) / 4.0),
            _safe_int(row.get("index")),
        ),
    )[:5]
    if not tags and usable_count:
        tags.append("visual_evidence_available")
    return {
        "status": status,
        "frame_count": len(frames),
        "usable_frame_count": usable_count,
        "avg_brightness": round(avg_brightness, 2),
        "avg_contrast": round(avg_contrast, 2),
        "avg_edge_score": round(avg_edge, 2),
        "avg_motion_score": round(avg_motion, 2),
        "summary_text": (
            f"frames {usable_count}/{len(frames)} | brightness {avg_brightness:.1f} | "
            f"contrast {avg_contrast:.1f} | motion {avg_motion:.1f}"
        ),
        "tags": tags,
        "key_frames": [
            {
                "index": row.get("index"),
                "timestamp_seconds": row.get("timestamp_seconds"),
                "quality": row.get("quality"),
                "motion_score": row.get("motion_score"),
                "edge_score": row.get("edge_score"),
                "path": row.get("path"),
            }
            for row in top_frames
        ],
        "frame_rows": rows[:80],
    }


def _video_review_evidence_score(visual_analysis: dict, settlement: dict, error_causes: list[str]) -> dict:
    visual = visual_analysis if isinstance(visual_analysis, dict) else {}
    tags = {str(tag) for tag in visual.get("tags", []) if str(tag)} if isinstance(visual.get("tags"), list) else set()
    status = str(visual.get("status") or "")
    frame_count = int(_safe_int(visual.get("frame_count"), 0) or 0)
    usable_count = int(_safe_int(visual.get("usable_frame_count"), 0) or 0)
    avg_motion = _safe_float(visual.get("avg_motion_score"), 0.0)
    avg_edge = _safe_float(visual.get("avg_edge_score"), 0.0)
    avg_contrast = _safe_float(visual.get("avg_contrast"), 0.0)
    model_miss_count = len([tag for tag in error_causes if str(tag).endswith("_miss") or tag == "prediction_direction_miss"])
    if status != "ready" or usable_count <= 0:
        return {
            "score": 0.0,
            "level": "low",
            "review_confidence": 0.0,
            "frame_count": frame_count,
            "usable_frame_count": usable_count,
            "components": {
                "sample": 0.0,
                "motion": 0.0,
                "edge": 0.0,
                "contrast": 0.0,
                "model_miss_count": model_miss_count,
            },
            "quality_flags": sorted(tags),
            "reason": "no_readable_visual_evidence",
        }

    sample_signal = min(1.0, usable_count / 6.0)
    motion_signal = min(1.0, avg_motion / 18.0)
    edge_signal = min(1.0, avg_edge / 8.0)
    contrast_signal = min(1.0, avg_contrast / 32.0)
    penalty = 0.0
    if "low_detail_frames" in tags:
        penalty += 0.16
    if "low_light_evidence" in tags or "overexposed_evidence" in tags:
        penalty += 0.14
    if "low_motion_evidence" in tags and model_miss_count:
        penalty += 0.10
    score = max(
        0.0,
        min(
            1.0,
            sample_signal * 0.34
            + motion_signal * 0.26
            + edge_signal * 0.22
            + contrast_signal * 0.18
            - penalty,
        ),
    )
    level = "high" if score >= 0.72 else "medium" if score >= 0.45 else "low"
    return {
        "score": round(score, 2),
        "level": level,
        "review_confidence": round(score, 2),
        "frame_count": frame_count,
        "usable_frame_count": usable_count,
        "components": {
            "sample": round(sample_signal, 2),
            "motion": round(motion_signal, 2),
            "edge": round(edge_signal, 2),
            "contrast": round(contrast_signal, 2),
            "penalty": round(penalty, 2),
            "model_miss_count": model_miss_count,
        },
        "quality_flags": sorted(tags),
        "reason": "visual_evidence_scored",
    }


def _video_review_event_hypotheses(
    settlement: dict,
    visual_analysis: dict,
    error_causes: list[str],
    evidence_score: dict | None = None,
) -> list[dict]:
    visual = visual_analysis if isinstance(visual_analysis, dict) else {}
    tags = {str(tag) for tag in error_causes if str(tag)}
    visual_tags = {str(tag) for tag in visual.get("tags", []) if str(tag)} if isinstance(visual.get("tags"), list) else set()
    evidence = evidence_score if isinstance(evidence_score, dict) else _video_review_evidence_score(visual, settlement, error_causes)
    score = _safe_float(evidence.get("score"), 0.0)
    level = str(evidence.get("level") or "low")
    avg_motion = _safe_float(visual.get("avg_motion_score"), 0.0)
    avg_edge = _safe_float(visual.get("avg_edge_score"), 0.0)
    key_frames = visual.get("key_frames") if isinstance(visual.get("key_frames"), list) else []
    key_frame_indexes = [str(row.get("index")) for row in key_frames[:5] if isinstance(row, dict) and row.get("index") is not None]
    hypotheses: list[dict] = []

    def add(code: str, title: str, confidence: float, evidence_text: str, recommendation: str) -> None:
        hypotheses.append(
            {
                "code": code,
                "title": title,
                "confidence": round(max(0.0, min(1.0, confidence)), 2),
                "evidence": evidence_text,
                "recommendation": recommendation,
            }
        )

    if level == "low" or str(visual.get("status") or "") != "ready":
        add(
            "low_quality_video_evidence",
            "Video evidence is not strong enough",
            max(0.15, score),
            f"usable_frames={evidence.get('usable_frame_count', 0)}/{evidence.get('frame_count', 0)} | tags={','.join(sorted(visual_tags)) or '-'}",
            "Increase frame density, import a clearer replay, or add manual event annotations before changing model weights.",
        )
        return hypotheses

    if "tempo_or_total_goals_miss" in tags and (avg_motion >= 12 or "high_scene_change" in visual_tags):
        add(
            "tempo_shift",
            "Match tempo or transition rhythm likely shifted",
            max(score, min(0.9, avg_motion / 24.0)),
            f"avg_motion={avg_motion:.1f} | key_frames={','.join(key_frame_indexes) or '-'}",
            "Mark fast-transition periods and compare them with the total-goals pre-match assumptions.",
        )
    if "scoreline_path_miss" in tags or ("prediction_direction_miss" in tags and avg_motion < 12):
        add(
            "finishing_variance",
            "Scoreline path may be driven by finishing variance",
            max(0.35, score * 0.85),
            f"score={settlement.get('home_goals', '-')}-{settlement.get('away_goals', '-')} | key_frames={','.join(key_frame_indexes) or '-'}",
            "Review shot quality and goal timing before treating the miss as a direction-model failure.",
        )
    if ("handicap_margin_miss" in tags or "prediction_direction_miss" in tags) and (avg_motion >= 8 or avg_edge >= 7):
        add(
            "set_piece_or_transition_risk",
            "Set-piece or transition risk may explain margin deviation",
            max(0.4, score),
            f"avg_motion={avg_motion:.1f} | avg_edge={avg_edge:.1f} | key_frames={','.join(key_frame_indexes) or '-'}",
            "Tag goals, big chances, set pieces, and defensive transition failures for Evaluation Agent memory.",
        )
    if "no_obvious_model_error" in tags and not hypotheses:
        add(
            "model_alignment_evidence",
            "Video evidence does not contradict the model outcome",
            max(0.45, score),
            f"visual_level={level} | key_frames={','.join(key_frame_indexes) or '-'}",
            "Keep this sample as positive review evidence and use it during stability validation.",
        )
    if not hypotheses:
        add(
            "manual_tactical_review_needed",
            "Visual evidence is usable but not decisive",
            max(0.3, score * 0.75),
            f"visual_level={level} | key_frames={','.join(key_frame_indexes) or '-'}",
            "Review key frames manually and attach tactical labels before updating model assumptions.",
        )
    return sorted(hypotheses, key=lambda item: _safe_float(item.get("confidence"), 0.0), reverse=True)[:5]


def _video_review_recommended_followup(evidence_score: dict, hypotheses: list[dict], error_causes: list[str]) -> dict:
    level = str(evidence_score.get("level") or "low") if isinstance(evidence_score, dict) else "low"
    codes = [str(item.get("code") or "") for item in hypotheses if isinstance(item, dict)]
    if level == "low" or "low_quality_video_evidence" in codes:
        return {
            "code": "collect_more_video_evidence",
            "message": "补充更密集抽帧、清晰回放或人工事件标注后，再进入 Evaluation Agent 复盘记忆。",
        }
    if "tempo_shift" in codes:
        return {
            "code": "annotate_tempo_turning_points",
            "message": "优先标注节奏拐点和转换进攻，再交给 Evaluation Agent 更新大小球复盘记忆。",
        }
    if "set_piece_or_transition_risk" in codes:
        return {
            "code": "annotate_margin_risk_events",
            "message": "优先标注定位球、反击和防线失位，再交给 Evaluation Agent 修正让球/胜差一致性记忆。",
        }
    if "finishing_variance" in codes:
        return {
            "code": "review_finishing_variance",
            "message": "复核射门质量与进球时间线，再交给 Evaluation Agent 判断是否写入方向模型。",
        }
    return {
        "code": "feed_video_findings_into_evaluation_agent",
        "message": "视频证据可用，进入 Evaluation Agent 复盘记忆并等待更多样本验证。",
    }


VIDEO_REVIEW_MANUAL_EVENT_LABELS = {
    "goal": "进球",
    "red_card": "红牌",
    "set_piece": "定位球",
    "counter_attack": "反击",
    "tempo_shift": "节奏拐点",
    "penalty": "点球",
    "injury": "伤停",
    "tactical_shift": "战术变化",
    "defensive_error": "防线失位",
    "shot_quality": "射门质量",
}

VIDEO_REVIEW_MANUAL_EVENT_HYPOTHESES = {
    "goal": "finishing_variance",
    "shot_quality": "finishing_variance",
    "set_piece": "set_piece_or_transition_risk",
    "counter_attack": "set_piece_or_transition_risk",
    "defensive_error": "set_piece_or_transition_risk",
    "tempo_shift": "tempo_shift",
    "tactical_shift": "tempo_shift",
    "red_card": "manual_tactical_review_needed",
    "injury": "manual_tactical_review_needed",
    "penalty": "manual_tactical_review_needed",
}


def _video_review_manual_annotation_hypothesis(annotation: dict) -> dict:
    event_type = str(annotation.get("event_type") or "").strip()
    mapped_code = VIDEO_REVIEW_MANUAL_EVENT_HYPOTHESES.get(event_type, "manual_tactical_review_needed")
    label = VIDEO_REVIEW_MANUAL_EVENT_LABELS.get(event_type, event_type or "manual")
    frame_index = annotation.get("frame_index")
    timestamp = annotation.get("timestamp_seconds")
    note = str(annotation.get("note") or "").strip()
    evidence_bits = [f"event={event_type or '-'}"]
    if frame_index not in (None, ""):
        evidence_bits.append(f"frame={frame_index}")
    if timestamp not in (None, ""):
        evidence_bits.append(f"time={_safe_float(timestamp):.0f}s")
    if note:
        evidence_bits.append(f"note={note[:80]}")
    return {
        "code": mapped_code,
        "title": f"Manual annotation: {label}",
        "confidence": round(max(0.35, min(1.0, _safe_float(annotation.get("confidence"), 0.78))), 2),
        "evidence": " | ".join(evidence_bits),
        "recommendation": "Feed the manual video annotation into Evaluation Agent post-match memory.",
        "source": "manual_annotation",
        "annotation_id": annotation.get("annotation_id"),
        "event_type": event_type,
    }


def _apply_video_review_manual_annotations(review: dict, agent_review: dict) -> dict:
    annotations = [dict(item) for item in review.get("manual_annotations", []) if isinstance(item, dict)]
    if not annotations:
        return agent_review
    updated = dict(agent_review)
    existing = [
        dict(item)
        for item in updated.get("event_hypotheses", [])
        if isinstance(item, dict) and str(item.get("source") or "") != "manual_annotation"
    ]
    manual_hypotheses = [_video_review_manual_annotation_hypothesis(item) for item in annotations]
    merged = sorted(
        existing + manual_hypotheses,
        key=lambda item: (-_safe_float(item.get("confidence"), 0.0), str(item.get("code") or "")),
    )
    event_tags: list[str] = []
    for item in annotations:
        event_type = str(item.get("event_type") or "").strip()
        if event_type and event_type not in event_tags:
            event_tags.append(event_type)
    updated["event_hypotheses"] = merged[:8]
    updated["manual_annotation_count"] = len(annotations)
    updated["manual_event_tags"] = event_tags
    updated["last_manual_annotation_at"] = annotations[-1].get("created_at")
    updated["recommended_followup"] = {
        "code": "feed_manual_video_annotations_into_evaluation_agent",
        "message": "已补充人工事件标注，进入 Evaluation Agent 赛后复盘记忆并用于后续错因归类。",
    }
    narrative = dict(updated.get("narrative_review") or {})
    narrative["manual_annotation_count"] = len(annotations)
    narrative["manual_annotations"] = annotations[-5:]
    narrative["event_hypotheses"] = merged[:3]
    narrative["recommendation"] = updated["recommended_followup"]["message"]
    updated["narrative_review"] = narrative
    next_actions = [str(action) for action in updated.get("next_actions", []) if str(action)]
    if "review_manual_video_annotations" not in next_actions:
        next_actions.append("review_manual_video_annotations")
    updated["next_actions"] = next_actions
    return updated


def _video_review_narrative(settlement: dict, visual_analysis: dict, error_causes: list[str]) -> dict:
    match_title = f"{settlement.get('home_team') or '-'} vs {settlement.get('away_team') or '-'}"
    score = f"{settlement.get('home_goals', '-')}-{settlement.get('away_goals', '-')}"
    visual = visual_analysis if isinstance(visual_analysis, dict) else {}
    tags = [str(tag) for tag in error_causes if str(tag)]
    key_frames = [row for row in visual.get("key_frames", []) if isinstance(row, dict)] if isinstance(visual.get("key_frames"), list) else []
    findings: list[str] = []
    if "prediction_direction_miss" in tags:
        findings.append("赛果方向与赛前判断不一致，需要复核模型对强弱方向、临场状态和盘口风险的处理。")
    if "handicap_margin_miss" in tags:
        findings.append("让球判断未命中，重点检查模型胜差与让球线的一致性。")
    if "tempo_or_total_goals_miss" in tags:
        findings.append("大小球判断未命中，重点复核比赛节奏、转换频率和射门质量估计。")
    if "scoreline_path_miss" in tags:
        findings.append("比分路径偏差较大，后续应对进球时间段和比分演化做单独归因。")
    if "high_scene_change" in tags:
        findings.append("关键帧之间画面变化较高，录像可能包含多段攻防转换或镜头切换，适合优先抽取转折点。")
    if "low_motion_evidence" in tags:
        findings.append("关键帧变化较低，当前抽帧更像静态片段，建议补充更密集抽帧或人工标注关键回合。")
    if "low_detail_frames" in tags:
        findings.append("部分帧细节不足，视觉证据适合作为辅助线索，不宜单独作为战术结论。")
    if "low_light_evidence" in tags or "overexposed_evidence" in tags:
        findings.append("画面曝光存在风险，复盘时需要谨慎解释球员站位和局部对抗。")
    if not findings:
        findings.append("当前视频证据未显示明显异常，优先作为赛后复盘补充材料。")

    evidence_lines = [
        f"视觉摘要: {visual.get('summary_text') or '-'}",
        f"可读关键帧: {visual.get('usable_frame_count', 0)}/{visual.get('frame_count', 0)}",
        f"关键帧索引: {', '.join(str(row.get('index')) for row in key_frames[:5]) if key_frames else '-'}",
    ]
    recommendation = "进入 Evaluation Agent 复盘记忆"
    if "low_motion_evidence" in tags or "low_detail_frames" in tags:
        recommendation = "先补充抽帧或人工标注，再进入 Evaluation Agent 复盘记忆"
    return {
        "status": "ready" if visual.get("status") == "ready" else "needs_more_evidence",
        "summary_text": f"{match_title} {score} | {findings[0]}",
        "findings": findings[:8],
        "evidence": evidence_lines,
        "recommendation": recommendation,
    }


def _video_review_ai_summary(settlement: dict, *, frame_count: int, notes: str, visual_analysis: dict | None = None) -> dict:
    tags: list[str] = []
    if settlement.get("is_correct") is False:
        tags.append("prediction_direction_miss")
    if settlement.get("ou_is_correct") is False:
        tags.append("tempo_or_total_goals_miss")
    if settlement.get("handicap_is_correct") is False:
        tags.append("handicap_margin_miss")
    if settlement.get("score_is_correct") is False:
        tags.append("scoreline_path_miss")
    if not tags:
        tags.append("no_obvious_model_error")
    visual = visual_analysis if isinstance(visual_analysis, dict) else {}
    visual_tags = [str(tag) for tag in visual.get("tags", [])] if isinstance(visual.get("tags"), list) else []
    if visual_tags:
        for tag in visual_tags:
            if tag not in tags:
                tags.append(tag)
    visual_status = str(visual.get("status") or "")
    vision_model_status = "offline_visual_evidence_ready" if visual_status == "ready" else "pending_manual_or_llm_vision_review"
    evidence_score = _video_review_evidence_score(visual, settlement, tags)
    event_hypotheses = _video_review_event_hypotheses(settlement, visual, tags, evidence_score)
    recommended_followup = _video_review_recommended_followup(evidence_score, event_hypotheses, tags)
    narrative = _video_review_narrative(settlement, visual, tags)
    narrative = dict(narrative)
    narrative["evidence_score"] = evidence_score.get("score")
    narrative["evidence_level"] = evidence_score.get("level")
    narrative["event_hypotheses"] = event_hypotheses[:3]
    if recommended_followup.get("message"):
        narrative["recommendation"] = recommended_followup["message"]
    return {
        "agent": "VideoReview Agent",
        "status": "visual_review_ready" if visual_status == "ready" else "frames_ready" if frame_count else "metadata_ready",
        "vision_model_status": vision_model_status,
        "frame_count": frame_count,
        "visual_summary": visual.get("summary_text") or "-",
        "key_frame_count": len(visual.get("key_frames") or []) if isinstance(visual.get("key_frames"), list) else 0,
        "evidence_score": evidence_score.get("score"),
        "evidence_level": evidence_score.get("level"),
        "review_confidence": evidence_score.get("review_confidence"),
        "evidence_quality": evidence_score,
        "event_hypotheses": event_hypotheses,
        "recommended_followup": recommended_followup,
        "narrative_review": narrative,
        "narrative_summary": narrative.get("summary_text") or "-",
        "prediction_alignment": "aligned" if settlement.get("is_correct") is True else "needs_review" if settlement.get("is_correct") is False else "unknown",
        "error_causes": tags,
        "operator_notes": notes,
        "next_actions": [
            "review_key_frames",
            "mark_tactical_turning_points",
            "feed_video_findings_into_evaluation_agent",
        ],
    }


def create_video_review(
    match_id: str,
    video_path: str | Path,
    *,
    notes: str = "",
    extract_frames: bool = False,
    interval_seconds: int = 10,
    max_frames: int = 36,
) -> dict:
    resolved_match_id = str(match_id or "").strip()
    path = Path(video_path).expanduser()
    if not resolved_match_id:
        return {"ok": False, "reason": "missing_match_id"}
    if not path.exists() or not path.is_file():
        return {"ok": False, "reason": "video_file_not_found", "path": str(path)}
    settlement = next(
        (item for item in STATE_STORE.load_settlements() if isinstance(item, dict) and str(item.get("match_id") or "") == resolved_match_id),
        {},
    )
    if not settlement:
        return {"ok": False, "reason": "settlement_not_found", "match_id": resolved_match_id}

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    review_seed = f"{resolved_match_id}|{path.resolve()}|{created_at}"
    review_id = hashlib.sha1(review_seed.encode("utf-8")).hexdigest()[:16]
    metadata = _video_file_metadata(path)
    frame_plan = _video_review_frame_plan(
        metadata.get("duration_seconds"),
        interval_seconds=interval_seconds,
        max_frames=max_frames,
    )
    frames: list[dict] = []
    extraction = {"status": "not_requested", "reason": "metadata_only"}
    if extract_frames:
        frames, extraction = _extract_video_review_frames(
            path,
            review_id,
            interval_seconds=interval_seconds,
            max_frames=max_frames,
        )
    visual_analysis = _video_review_frame_visual_analysis(frames)
    agent_review = _video_review_ai_summary(
        settlement,
        frame_count=len(frames),
        notes=str(notes or ""),
        visual_analysis=visual_analysis,
    )
    item = {
        "review_id": review_id,
        "created_at": created_at,
        "match_id": resolved_match_id,
        "match": {
            "match_date": settlement.get("match_date"),
            "league": settlement.get("league"),
            "home_team": settlement.get("home_team"),
            "away_team": settlement.get("away_team"),
            "score": f"{settlement.get('home_goals', '-')}-{settlement.get('away_goals', '-')}",
            "result": settlement.get("result"),
        },
        "video": metadata,
        "frame_interval_seconds": max(1, int(interval_seconds)),
        "max_frames": max(1, int(max_frames)),
        "frame_plan": frame_plan,
        "frames": frames,
        "extraction": extraction,
        "visual_analysis": visual_analysis,
        "agent_review": agent_review,
    }
    items = _load_video_review_items()
    items = [existing for existing in items if not (isinstance(existing, dict) and str(existing.get("review_id") or "") == review_id)]
    items.append(item)
    _save_video_review_items(items)
    return {"ok": True, "reason": "ok", "review": item}


def create_video_review_reference(
    match_id: str,
    video_url: str,
    *,
    source_name: str = "FIFA+ Archive",
    notes: str = "",
) -> dict:
    resolved_match_id = str(match_id or "").strip()
    resolved_url = str(video_url or "").strip()
    resolved_source = str(source_name or "").strip() or "External replay"
    if not resolved_match_id:
        return {"ok": False, "reason": "missing_match_id"}
    if not resolved_url.startswith(("http://", "https://")):
        return {"ok": False, "reason": "invalid_video_url", "url": resolved_url}
    settlement = next(
        (item for item in STATE_STORE.load_settlements() if isinstance(item, dict) and str(item.get("match_id") or "") == resolved_match_id),
        {},
    )
    if not settlement:
        return {"ok": False, "reason": "settlement_not_found", "match_id": resolved_match_id}

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    review_seed = f"{resolved_match_id}|{resolved_url}|{created_at}"
    review_id = hashlib.sha1(review_seed.encode("utf-8")).hexdigest()[:16]
    visual_analysis = _video_review_frame_visual_analysis([])
    agent_review = _video_review_ai_summary(
        settlement,
        frame_count=0,
        notes=str(notes or f"external replay reference: {resolved_source}"),
        visual_analysis=visual_analysis,
    )
    item = {
        "review_id": review_id,
        "created_at": created_at,
        "match_id": resolved_match_id,
        "match": {
            "match_date": settlement.get("match_date"),
            "league": settlement.get("league"),
            "home_team": settlement.get("home_team"),
            "away_team": settlement.get("away_team"),
            "score": f"{settlement.get('home_goals', '-')}-{settlement.get('away_goals', '-')}",
            "result": settlement.get("result"),
        },
        "video": {
            "source_type": "external_reference",
            "source_name": resolved_source,
            "url": resolved_url,
            "filename": resolved_source,
            "path": "",
            "size_bytes": 0,
            "probe_status": "external_reference",
            "duration_seconds": None,
            "can_extract_frames": False,
            "copyright_note": "Reference-only replay URL. Do not auto-download or redistribute video.",
        },
        "source_policy": {
            "mode": "reference_only",
            "recommended_scope": "world_cup_public_archive" if "fifa" in resolved_source.lower() else "external_replay_reference",
            "fallback": "manual_timestamp_annotation",
            "leakage_note": "External replay evidence is post-match review material only.",
        },
        "frame_interval_seconds": 0,
        "max_frames": 0,
        "frame_plan": [],
        "frames": [],
        "extraction": {"status": "not_available", "reason": "external_reference_no_local_file"},
        "visual_analysis": visual_analysis,
        "agent_review": agent_review,
        "manual_annotations": [],
    }
    items = _load_video_review_items()
    items = [existing for existing in items if not (isinstance(existing, dict) and str(existing.get("review_id") or "") == review_id)]
    items.append(item)
    _save_video_review_items(items)
    return {"ok": True, "reason": "ok", "review": item}


def extract_video_review_frames_now(
    review_id: str,
    *,
    interval_seconds: int | None = None,
    max_frames: int | None = None,
) -> dict:
    resolved_id = str(review_id or "").strip()
    if not resolved_id:
        return {"ok": False, "reason": "missing_review_id"}
    items = _load_video_review_items()
    target_index = next(
        (index for index, item in enumerate(items) if isinstance(item, dict) and str(item.get("review_id") or "") == resolved_id),
        None,
    )
    if target_index is None:
        return {"ok": False, "reason": "review_not_found", "review_id": resolved_id}
    review = dict(items[target_index])
    video = review.get("video") if isinstance(review.get("video"), dict) else {}
    path = Path(str(video.get("path") or ""))
    if not path.exists() or not path.is_file():
        extraction = {"status": "failed", "reason": "video_file_not_found"}
        review["extraction"] = extraction
        review["extracted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        items[target_index] = review
        _save_video_review_items(items)
        return {"ok": False, "reason": "video_file_not_found", "review": review}

    interval = max(1, int(interval_seconds or review.get("frame_interval_seconds") or 10))
    limit = max(1, int(max_frames or review.get("max_frames") or 36))
    frames, extraction = _extract_video_review_frames(
        path,
        resolved_id,
        interval_seconds=interval,
        max_frames=limit,
    )
    review["frame_interval_seconds"] = interval
    review["max_frames"] = limit
    review["frames"] = frames
    review["extraction"] = extraction
    review["extracted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    visual_analysis = _video_review_frame_visual_analysis(frames)
    review["visual_analysis"] = visual_analysis

    settlement = next(
        (
            item
            for item in STATE_STORE.load_settlements()
            if isinstance(item, dict) and str(item.get("match_id") or "") == str(review.get("match_id") or "")
        ),
        {},
    )
    if settlement:
        agent_review = _video_review_ai_summary(
            settlement,
            frame_count=len(frames),
            notes=str((review.get("agent_review") or {}).get("operator_notes") or "") if isinstance(review.get("agent_review"), dict) else "",
            visual_analysis=visual_analysis,
        )
        review["agent_review"] = _apply_video_review_manual_annotations(review, agent_review)
    elif isinstance(review.get("agent_review"), dict):
        agent_review = dict(review["agent_review"])
        agent_review["frame_count"] = len(frames)
        agent_review["status"] = "frames_ready" if frames else "metadata_ready"
        review["agent_review"] = _apply_video_review_manual_annotations(review, agent_review)

    items[target_index] = review
    _save_video_review_items(items)
    return {
        "ok": bool(extraction.get("status") == "ok"),
        "reason": str(extraction.get("reason") or extraction.get("status") or "-"),
        "review_id": resolved_id,
        "frame_count": len(frames),
        "extraction": extraction,
        "review": review,
        "summary_text": f"video_review={resolved_id} | frames={len(frames)} | status={extraction.get('status', '-')}",
    }


def add_video_review_annotation(
    review_id: str,
    *,
    event_type: str,
    timestamp_seconds: float | int | None = None,
    frame_index: int | None = None,
    note: str = "",
    confidence: float = 0.78,
    created_by: str = "operator",
) -> dict:
    resolved_id = str(review_id or "").strip()
    if not resolved_id:
        return {"ok": False, "reason": "missing_review_id"}
    resolved_type = str(event_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not resolved_type:
        return {"ok": False, "reason": "missing_event_type"}
    if resolved_type not in VIDEO_REVIEW_MANUAL_EVENT_LABELS:
        return {
            "ok": False,
            "reason": "unsupported_event_type",
            "supported_event_types": sorted(VIDEO_REVIEW_MANUAL_EVENT_LABELS),
        }
    items = _load_video_review_items()
    target_index = next(
        (index for index, item in enumerate(items) if isinstance(item, dict) and str(item.get("review_id") or "") == resolved_id),
        None,
    )
    if target_index is None:
        return {"ok": False, "reason": "review_not_found", "review_id": resolved_id}

    review = dict(items[target_index])
    annotations = [dict(item) for item in review.get("manual_annotations", []) if isinstance(item, dict)]
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    annotation_seed = f"{resolved_id}|{created_at}|{len(annotations)}|{resolved_type}|{note}"
    annotation = {
        "annotation_id": hashlib.sha1(annotation_seed.encode("utf-8")).hexdigest()[:14],
        "created_at": created_at,
        "created_by": str(created_by or "operator"),
        "event_type": resolved_type,
        "event_label": VIDEO_REVIEW_MANUAL_EVENT_LABELS[resolved_type],
        "timestamp_seconds": round(_safe_float(timestamp_seconds), 2) if timestamp_seconds not in (None, "") else None,
        "frame_index": _safe_int(frame_index) if frame_index not in (None, "") else None,
        "confidence": round(max(0.35, min(1.0, _safe_float(confidence, 0.78))), 2),
        "note": str(note or "").strip(),
        "source": "manual",
    }
    annotations.append(annotation)
    review["manual_annotations"] = annotations[-100:]
    review["manual_annotation_count"] = len(review["manual_annotations"])
    agent_review = dict(review.get("agent_review") or {})
    review["agent_review"] = _apply_video_review_manual_annotations(review, agent_review)
    review["updated_at"] = created_at
    items[target_index] = review
    _save_video_review_items(items)
    return {
        "ok": True,
        "reason": "ok",
        "review_id": resolved_id,
        "annotation": annotation,
        "review": review,
        "summary_text": f"video_review={resolved_id} | manual_annotations={len(review['manual_annotations'])}",
    }


def export_video_review_fewshot_samples_now(*, limit: int = 80) -> dict:
    result = export_video_review_fewshot_samples(
        PROJECT_DIR,
        get_video_reviews(limit=0),
        output_path=VIDEO_REVIEW_FEWSHOT_FILE,
        limit=limit,
    )
    invalidate_statsbomb_state_cache(VIDEO_REVIEW_FEWSHOT_FILE)
    return result


def load_c1_comparison_marks_cache() -> dict[str, dict]:
    return STATE_STORE.load_c1_comparison_marks()


def save_c1_comparison_marks_cache(items: dict[str, dict]) -> None:
    STATE_STORE.save_c1_comparison_marks(items)


def migrate_prediction_snapshots(max_unresolved: int = 50) -> dict:
    report = {
        "total_snapshots": 0,
        "already_bound": 0,
        "resolved": 0,
        "resolved_exact": 0,
        "resolved_team_only": 0,
        "skipped_non_titan": 0,
        "invalid_records": 0,
        "unresolved": 0,
        "unresolved_items": [],
    }

    snapshots = STATE_STORE.load_prediction_snapshots()
    report["total_snapshots"] = len(snapshots)
    if not snapshots or MatchFetcherTitan is None:
        report["trace_fact_ref_backfill"] = backfill_prediction_snapshot_trace_fact_refs()
        report["analysis_history_trace_fact_ref_backfill"] = backfill_analysis_history_trace_fact_refs()
        STATE_STORE.save_snapshot_migration_report(report)
        return report

    try:
        titan_items = MatchFetcherTitan(debug=False)._load_schedule_matches()
    except Exception:
        titan_items = []

    exact_map: dict[tuple[str, str, str, str], list[str]] = {}
    team_map: dict[tuple[str, str, str], list[str]] = {}
    candidate_payload: dict[str, dict] = {}
    for item in titan_items:
        source_id = normalize_text(getattr(item, "match_id", ""))
        if not source_id:
            continue
        match_date = normalize_text(getattr(item, "match_date", ""))
        league = normalize_text(getattr(item, "league", ""))
        home_team = normalize_text(getattr(item, "home_team", ""))
        away_team = normalize_text(getattr(item, "away_team", ""))
        exact_map.setdefault(_snapshot_lookup_key(match_date, league, home_team, away_team), []).append(source_id)
        team_map.setdefault(_snapshot_lookup_team_key(match_date, home_team, away_team), []).append(source_id)
        candidate_payload[source_id] = {
            "match_date": match_date,
            "league": league,
            "home_team": home_team,
            "away_team": away_team,
        }

    changed = False
    for snapshot_match_id, snapshot_record in snapshots.items():
        if not isinstance(snapshot_record, dict):
            report["invalid_records"] += 1
            continue
        snapshot_match = snapshot_record.get("match")
        if not isinstance(snapshot_match, dict):
            report["invalid_records"] += 1
            continue

        snapshot_source = normalize_text(snapshot_match.get("source", ""))
        if snapshot_source and "titan" not in snapshot_source.lower():
            report["skipped_non_titan"] += 1
            continue

        source_id = normalize_text(snapshot_match.get("source_id", ""))
        if source_id:
            report["already_bound"] += 1
            continue

        app_match = _app_match_from_payload(snapshot_match, source=snapshot_source or "snapshot:titan")
        if app_match is None:
            report["invalid_records"] += 1
            continue

        exact_ids = exact_map.get(
            _snapshot_lookup_key(app_match.match_date, app_match.league, app_match.home_team, app_match.away_team),
            [],
        )
        team_ids = team_map.get(
            _snapshot_lookup_team_key(app_match.match_date, app_match.home_team, app_match.away_team),
            [],
        )

        resolved_id = ""
        resolved_strategy = ""
        if len(exact_ids) == 1:
            resolved_id = exact_ids[0]
            resolved_strategy = "exact"
            report["resolved_exact"] += 1
        elif len(team_ids) == 1:
            resolved_id = team_ids[0]
            resolved_strategy = "team_only"
            report["resolved_team_only"] += 1

        if resolved_id:
            snapshot_match["source_id"] = resolved_id
            snapshot_record["match"] = snapshot_match
            snapshot_record["migration"] = {
                "status": "resolved",
                "strategy": resolved_strategy,
                "resolved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "candidate": candidate_payload.get(resolved_id, {}),
            }
            snapshots[snapshot_match_id] = snapshot_record
            report["resolved"] += 1
            changed = True
            continue

        report["unresolved"] += 1
        snapshot_record["migration"] = {
            "status": "unresolved",
            "resolved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        snapshots[snapshot_match_id] = snapshot_record
        changed = True
        if len(report["unresolved_items"]) < max_unresolved:
            report["unresolved_items"].append(
                {
                    "match_id": snapshot_match_id,
                    "match_date": app_match.match_date,
                    "league": app_match.league,
                    "home_team": app_match.home_team,
                    "away_team": app_match.away_team,
                }
            )

    if changed:
        STATE_STORE.save_prediction_snapshots(snapshots)
    report["trace_fact_ref_backfill"] = backfill_prediction_snapshot_trace_fact_refs()
    report["analysis_history_trace_fact_ref_backfill"] = backfill_analysis_history_trace_fact_refs()
    STATE_STORE.save_snapshot_migration_report(report)
    return report


def settle_match_result(
    match: AppMatch,
    home_goals: int,
    away_goals: int,
    prediction: dict | None = None,
) -> dict:
    existing_settlements = STATE_STORE.load_settlements()
    for item in reversed(existing_settlements):
        if isinstance(item, dict) and str(item.get("match_id") or "") == match.match_id:
            existing = dict(item)
            existing["duplicate_skipped"] = True
            existing["duplicate_checked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            STATE_STORE.pop_prediction_snapshot(match.match_id)
            auto_settle_pending_parlays()
            return existing

    enrich_match_from_market_snapshot_store(match)
    ratings_map = _load_match_ratings(match)
    home_rating, away_rating, ratings_map = _resolved_ratings(match, ratings_map)

    league_strength = LEAGUE_STRENGTH.get(match.league, 0.92)
    update = ELO_ENGINE.update_from_result(
        home_rating=home_rating,
        away_rating=away_rating,
        home_goals=home_goals,
        away_goals=away_goals,
        league_strength=league_strength,
    )

    ratings_map[match.home_team] = round(update.home_after, 4)
    ratings_map[match.away_team] = round(update.away_after, 4)
    _save_match_ratings(match, ratings_map)

    result = _result_label(home_goals, away_goals)
    predicted = prediction.get("recommendation") if prediction else None
    is_correct = bool(predicted == result) if predicted else None
    total_goals = int(home_goals) + int(away_goals)
    predicted_total_goals, predicted_total_goals_value, total_goals_confidence = _extract_total_goals_prediction(
        prediction
    )
    total_goals_is_correct = bool(predicted_total_goals_value == total_goals) if predicted_total_goals_value is not None else None
    predicted_score, score_confidence = _extract_score_prediction(prediction)
    actual_score = f"{int(home_goals)}-{int(away_goals)}"
    score_is_correct = bool(predicted_score == actual_score) if predicted_score else None
    predicted_htft, htft_confidence = _extract_htft_prediction(prediction)
    handicap_line = _safe_float(match.handicap_line, default=0.0)
    handicap_result_key = _handicap_outcome_key(home_goals, away_goals, handicap_line)
    handicap_result = _format_handicap_display(handicap_line, handicap_result_key)
    predicted_handicap_display, predicted_handicap_label, handicap_confidence = _extract_handicap_prediction(prediction)
    handicap_is_correct = bool(predicted_handicap_label == _handicap_label_from_key(handicap_result_key)) if predicted_handicap_label else None
    ou_line = 2.5
    ou_result = _ou_result_label(total_goals, line=ou_line)
    predicted_ou, ou_confidence = _extract_ou_prediction(prediction, line=ou_line)
    ou_is_correct = bool(predicted_ou == ou_result) if predicted_ou else None
    high_accuracy_strategy_settlement = _settle_high_accuracy_strategy_results(
        prediction,
        result=result,
        total_goals=total_goals,
        actual_score=actual_score,
        handicap_result=handicap_result,
        ou_result=ou_result,
    )

    settlement = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "match_id": match.match_id,
        "match_date": match.match_date,
        "match_time": match.match_time,
        "league": match.league,
        "competition_group": match.competition_group,
        "group_round": match.group_round,
        "home_points": match.home_points,
        "away_points": match.away_points,
        "home_goal_diff": match.home_goal_diff,
        "away_goal_diff": match.away_goal_diff,
        "home_group_rank": match.home_group_rank,
        "away_group_rank": match.away_group_rank,
        "home_team": match.home_team,
        "away_team": match.away_team,
        "home_goals": int(home_goals),
        "away_goals": int(away_goals),
        "result": result,
        "predicted": predicted,
        "is_correct": is_correct,
        "prediction_confidence": round(_safe_float(prediction.get("confidence"), 0.0), 4) if prediction else None,
        "total_goals": total_goals,
        "predicted_total_goals": predicted_total_goals,
        "total_goals_confidence": round(total_goals_confidence, 4) if total_goals_confidence is not None else None,
        "total_goals_is_correct": total_goals_is_correct,
        "predicted_score": predicted_score,
        "score_confidence": round(score_confidence, 4) if score_confidence is not None else None,
        "score_is_correct": score_is_correct,
        "predicted_htft": predicted_htft,
        "htft_confidence": round(htft_confidence, 4) if htft_confidence is not None else None,
        "handicap_line": round(handicap_line, 2),
        "handicap_result": handicap_result,
        "predicted_handicap": predicted_handicap_display,
        "handicap_confidence": round(handicap_confidence, 4) if handicap_confidence is not None else None,
        "handicap_is_correct": handicap_is_correct,
        "ou_line": ou_line,
        "ou_result": ou_result,
        "predicted_ou": predicted_ou,
        "ou_confidence": round(ou_confidence, 4) if ou_confidence is not None else None,
        "ou_is_correct": ou_is_correct,
        "high_accuracy_strategy_active_count": high_accuracy_strategy_settlement["active_count"],
        "high_accuracy_strategy_hit_count": high_accuracy_strategy_settlement["hit_count"],
        "high_accuracy_strategy_shadow_count": high_accuracy_strategy_settlement.get("shadow_count", 0),
        "high_accuracy_strategy_shadow_hit_count": high_accuracy_strategy_settlement.get("shadow_hit_count", 0),
        "high_accuracy_strategy_shadow_summary": high_accuracy_strategy_settlement.get("shadow_summary", "-"),
        "high_accuracy_strategy_summary": high_accuracy_strategy_settlement["summary"],
        "high_accuracy_strategy_items": high_accuracy_strategy_settlement["items"],
        **_strategy_allowlist_settlement_fields(prediction),
        **_strategy_admission_settlement_fields(prediction),
        **_market_entropy_settlement_fields(prediction),
        **_handicap_margin_settlement_fields(prediction),
        **_draw_release_guard_settlement_fields(prediction),
        **_agent_trace_settlement_fields(prediction),
        "opening_odds_home": round(_safe_float(match.opening_odds_home, 0.0), 4),
        "opening_odds_draw": round(_safe_float(match.opening_odds_draw, 0.0), 4),
        "opening_odds_away": round(_safe_float(match.opening_odds_away, 0.0), 4),
        "return_rate": round(_safe_float(match.return_rate, 0.0), 4),
        "kelly_home": round(_safe_float(match.kelly_home, 0.0), 4),
        "kelly_draw": round(_safe_float(match.kelly_draw, 0.0), 4),
        "kelly_away": round(_safe_float(match.kelly_away, 0.0), 4),
        "home_rating_before": round(update.home_before, 2),
        "away_rating_before": round(update.away_before, 2),
        "home_rating_after": round(update.home_after, 2),
        "away_rating_after": round(update.away_after, 2),
        "home_delta": round(update.delta_home, 2),
        "away_delta": round(update.delta_away, 2),
        "rating_pool": _rating_pool_name(match),
    }
    STATE_STORE.append_settlement(settlement)

    if prediction:
        xgb_features = prediction.get("xgb_features")
        result_label = _result_to_label(result)
        if isinstance(xgb_features, dict) and result_label is not None:
            STATE_STORE.append_xgb_sample(
                {
                    "timestamp": settlement["timestamp"],
                    "match_id": match.match_id,
                    "features": xgb_features,
                    "label": result_label,
                    "meta": {
                        "source": "live_settlement",
                        "match_date": match.match_date,
                        "match_time": match.match_time,
                        "league": match.league,
                        "home_team": match.home_team,
                        "away_team": match.away_team,
                        "home_goals": int(home_goals),
                        "away_goals": int(away_goals),
                        "handicap_line": round(handicap_line, 2),
                        "opening_odds_home": round(_safe_float(match.opening_odds_home, 0.0), 4),
                        "opening_odds_draw": round(_safe_float(match.opening_odds_draw, 0.0), 4),
                        "opening_odds_away": round(_safe_float(match.opening_odds_away, 0.0), 4),
                        "return_rate": round(_safe_float(match.return_rate, 0.0), 4),
                        "kelly_home": round(_safe_float(match.kelly_home, 0.0), 4),
                        "kelly_draw": round(_safe_float(match.kelly_draw, 0.0), 4),
                        "kelly_away": round(_safe_float(match.kelly_away, 0.0), 4),
                    },
                }
            )

    # 结算完成后移除待结算快照，避免重复占用状态空间。
    STATE_STORE.pop_prediction_snapshot(match.match_id)
    auto_settle_pending_parlays()

    return settlement


def _statsbomb_key(*parts: object) -> str:
    return "|".join(normalize_text(part).lower() for part in parts if normalize_text(part))


def _load_statsbomb_event_summary_index() -> dict[str, dict]:
    if not STATSBOMB_EVENT_SUMMARIES_FILE.exists():
        return {}
    try:
        payload = json.loads(STATSBOMB_EVENT_SUMMARIES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    items = payload.get("items", []) if isinstance(payload, dict) else []
    if not isinstance(items, list):
        return {}
    index: dict[str, dict] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        keys = [
            _statsbomb_key(item.get("match_id")),
            _statsbomb_key(item.get("source_match_id")),
            _statsbomb_key(item.get("match_date"), item.get("home_team"), item.get("away_team")),
            _statsbomb_key(item.get("match_date"), item.get("league"), item.get("home_team"), item.get("away_team")),
        ]
        for key in keys:
            if key and key not in index:
                index[key] = item
    return index


def _statsbomb_coverage_audit_exact_keys(item: dict) -> set[str]:
    keys = {
        _statsbomb_key(item.get("match_id")),
        _statsbomb_key(item.get("source_match_id")),
        _statsbomb_key(item.get("match_date"), item.get("home_team"), item.get("away_team")),
        _statsbomb_key(item.get("match_date"), item.get("league"), item.get("home_team"), item.get("away_team")),
    }
    return {key for key in keys if key}


def _statsbomb_coverage_candidate_score(settlement: dict, statsbomb: dict) -> float:
    def similarity(left: object, right: object) -> float:
        left_text = re.sub(r"\s+", " ", normalize_text(left).lower()).strip()
        right_text = re.sub(r"\s+", " ", normalize_text(right).lower()).strip()
        if not left_text or not right_text:
            return 0.0
        ratio = SequenceMatcher(None, left_text, right_text).ratio()
        left_tokens = set(left_text.split())
        right_tokens = set(right_text.split())
        overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
        return max(ratio, overlap)

    direct = (similarity(settlement.get("home_team"), statsbomb.get("home_team")) + similarity(settlement.get("away_team"), statsbomb.get("away_team"))) / 2.0
    swapped = (similarity(settlement.get("home_team"), statsbomb.get("away_team")) + similarity(settlement.get("away_team"), statsbomb.get("home_team"))) / 2.0
    return round(max(direct, swapped), 4)


def _build_statsbomb_coverage_audit(
    settlements: list[dict],
    statsbomb_items: list[dict],
    *,
    candidate_limit: int = 30,
    min_candidate_score: float = 0.55,
) -> dict[str, object]:
    statsbomb_index: dict[str, dict] = {}
    statsbomb_by_date: dict[str, list[dict]] = {}
    for item in statsbomb_items:
        if not isinstance(item, dict):
            continue
        for key in _statsbomb_coverage_audit_exact_keys(item):
            statsbomb_index.setdefault(key, item)
        date_key = normalize_text(item.get("match_date", "")).lower().strip()
        if date_key:
            statsbomb_by_date.setdefault(date_key, []).append(item)

    exact_rows: list[dict[str, object]] = []
    candidate_rows: list[dict[str, object]] = []
    no_same_date = 0
    settlement_items = [item for item in settlements if isinstance(item, dict)]
    for settlement in settlement_items:
        matched = None
        for key in _statsbomb_coverage_audit_exact_keys(settlement):
            if key in statsbomb_index:
                matched = statsbomb_index[key]
                break
        if matched is not None:
            exact_rows.append(
                {
                    "match_id": settlement.get("match_id"),
                    "statsbomb_source_match_id": matched.get("source_match_id"),
                    "match_date": settlement.get("match_date"),
                    "home_team": settlement.get("home_team"),
                    "away_team": settlement.get("away_team"),
                }
            )
            continue

        same_date = statsbomb_by_date.get(normalize_text(settlement.get("match_date", "")).lower().strip(), [])
        if not same_date:
            no_same_date += 1
            continue
        scored = [(_statsbomb_coverage_candidate_score(settlement, item), item) for item in same_date]
        scored.sort(key=lambda item: (-float(item[0] or 0.0), str(item[1].get("home_team") or "")))
        for score, item in scored[:3]:
            if score < float(min_candidate_score):
                continue
            candidate_rows.append(
                {
                    "score": score,
                    "settlement": {
                        "match_id": settlement.get("match_id"),
                        "match_date": settlement.get("match_date"),
                        "league": settlement.get("league"),
                        "home_team": settlement.get("home_team"),
                        "away_team": settlement.get("away_team"),
                    },
                    "statsbomb": {
                        "source_match_id": item.get("source_match_id"),
                        "match_date": item.get("match_date"),
                        "league": item.get("league"),
                        "home_team": item.get("home_team"),
                        "away_team": item.get("away_team"),
                    },
                }
            )

    candidate_rows.sort(key=lambda item: (-float(item.get("score") or 0.0), str(item.get("settlement", {}).get("match_id") or "")))
    settlement_count = len(settlement_items)
    exact_count = len(exact_rows)
    candidate_count = len(candidate_rows)
    coverage_gap_count = max(0, settlement_count - exact_count)
    same_date_unmatched_count = max(0, settlement_count - exact_count - no_same_date)
    recommendation = (
        "expand_statsbomb_import"
        if no_same_date >= max(1, settlement_count - exact_count)
        else "review_team_aliases"
        if candidate_count
        else "collect_more_overlap"
    )
    return {
        "settlement_count": settlement_count,
        "statsbomb_match_count": len(statsbomb_items),
        "exact_match_count": exact_count,
        "exact_match_rate": round(exact_count / settlement_count, 4) if settlement_count else 0.0,
        "candidate_count": candidate_count,
        "coverage_gap_count": coverage_gap_count,
        "no_same_date_count": no_same_date,
        "same_date_unmatched_count": same_date_unmatched_count,
        "exact_rows": exact_rows[: max(0, int(candidate_limit))],
        "candidate_rows": candidate_rows[: max(0, int(candidate_limit))],
        "recommendation": recommendation,
    }


def _match_statsbomb_event_summary(settlement: dict, index: dict[str, dict]) -> dict | None:
    if not index:
        return None
    keys = [
        _statsbomb_key(settlement.get("match_id")),
        _statsbomb_key(settlement.get("statsbomb_source_match_id")),
        _statsbomb_key(settlement.get("match_date"), settlement.get("home_team"), settlement.get("away_team")),
        _statsbomb_key(settlement.get("match_date"), settlement.get("league"), settlement.get("home_team"), settlement.get("away_team")),
    ]
    for key in keys:
        if key and key in index:
            return index[key]
    return None


def get_recent_settlements(limit: int = 20) -> list[dict]:
    try:
        resolved_limit = int(limit)
    except Exception:
        resolved_limit = 20
    cache_key = _recent_settlements_signature(resolved_limit)
    if cache_key is not None:
        cached = _RECENT_SETTLEMENTS_CACHE.get(cache_key)
        if isinstance(cached, list):
            return _copy_dict_rows(cached)

    items = STATE_STORE.load_settlements()
    video_reviews_by_match: dict[str, dict] = {}
    try:
        for review in get_video_reviews(limit=0):
            match_id = str(review.get("match_id") or "")
            if match_id and match_id not in video_reviews_by_match:
                video_reviews_by_match[match_id] = review
    except Exception:
        video_reviews_by_match = {}
    try:
        history = STATE_STORE.load_analysis_history()
    except Exception:
        history = {}
    statsbomb_by_match = _load_statsbomb_event_summary_index()
    if isinstance(history, dict) or video_reviews_by_match or statsbomb_by_match:
        enriched: list[dict] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            record = dict(item)
            history_record = history.get(str(record.get("match_id") or ""))
            prediction = history_record.get("prediction") if isinstance(history_record, dict) else None
            if isinstance(prediction, dict):
                if record.get("market_entropy_score") is None:
                    for key, value in _market_entropy_settlement_fields(prediction).items():
                        if record.get(key) in (None, "", []):
                            record[key] = value
                if record.get("handicap_margin_score") is None:
                    for key, value in _handicap_margin_settlement_fields(prediction).items():
                        if record.get(key) in (None, "", []):
                            record[key] = value
                if record.get("draw_release_guard_status") in (None, ""):
                    for key, value in _draw_release_guard_settlement_fields(prediction).items():
                        if record.get(key) in (None, "", [], {}):
                            record[key] = value
                if record.get("strategy_admission_decision") in (None, ""):
                    for key, value in _strategy_admission_settlement_fields(prediction).items():
                        if record.get(key) in (None, "", [], {}):
                            record[key] = value
                if not record.get("supervisor_agent_statuses"):
                    for key, value in _agent_trace_settlement_fields(prediction).items():
                        if record.get(key) in (None, "", [], {}):
                            record[key] = value
            video_review = video_reviews_by_match.get(str(record.get("match_id") or ""))
            if isinstance(video_review, dict) and video_review:
                record["video_review"] = video_review
                record["video_review_status"] = (video_review.get("agent_review") or {}).get("status") if isinstance(video_review.get("agent_review"), dict) else "ready"
            statsbomb_record = _match_statsbomb_event_summary(record, statsbomb_by_match)
            if isinstance(statsbomb_record, dict) and statsbomb_record:
                summary = statsbomb_record.get("event_summary")
                if isinstance(summary, dict):
                    record["statsbomb_event_summary"] = summary
                    record["statsbomb_source_match_id"] = statsbomb_record.get("source_match_id")
                    record["statsbomb_source_url"] = statsbomb_record.get("source_url")
            enriched.append(record)
        items = enriched
    result = items if resolved_limit <= 0 else items[-resolved_limit:]
    if cache_key is not None:
        if len(_RECENT_SETTLEMENTS_CACHE) > 16:
            _RECENT_SETTLEMENTS_CACHE.clear()
        _RECENT_SETTLEMENTS_CACHE[cache_key] = _copy_dict_rows(result)
    return _copy_dict_rows(result)


def get_result_recovery_runs(limit: int = 50) -> list[dict]:
    items = STATE_STORE.load_result_recovery_runs()
    if limit <= 0:
        return items
    return items[-limit:]


def record_result_recovery_run(record: dict, limit: int = 300) -> None:
    STATE_STORE.upsert_result_recovery_run(record, limit=limit)


def classify_snapshot_result_lookup(result: object) -> dict[str, object]:
    if not isinstance(result, dict):
        return {
            "is_finished": False,
            "reason": "no_result",
            "state_code": "",
            "home_goals": None,
            "away_goals": None,
        }

    home_goals = result.get("home_goals")
    away_goals = result.get("away_goals")
    state_code = normalize_text(result.get("state_code", ""))
    if result.get("is_finished") and home_goals is not None and away_goals is not None:
        return {
            "is_finished": True,
            "reason": "finished",
            "state_code": state_code,
            "home_goals": home_goals,
            "away_goals": away_goals,
        }

    if home_goals is None or away_goals is None:
        reason = "missing_score"
    elif state_code:
        reason = "state_not_finished"
    else:
        reason = "not_finished"
    return {
        "is_finished": False,
        "reason": reason,
        "state_code": state_code,
        "home_goals": home_goals,
        "away_goals": away_goals,
    }


def auto_settle_finished_matches(
    prediction_cache: dict[str, dict] | None = None,
    lookback_days: int = 2,
) -> dict:
    history_backfill = backfill_analysis_history_from_prediction_snapshots()
    repair_report = repair_prediction_snapshots_from_analysis_history(lookback_days=max(3, int(lookback_days)))
    migrate_prediction_snapshots()
    lookback_days = max(0, min(int(lookback_days), 14))
    summary = {
        "fetched_finished": 0,
        "already_settled": 0,
        "new_settled": 0,
        "new_parlay_settled": 0,
        "skipped": 0,
        "snapshot_predictions": 0,
        "snapshot_result_hits": 0,
        "snapshot_checked": 0,
        "snapshot_result_misses": 0,
        "snapshot_result_miss_reasons": {},
        "snapshot_result_miss_items": [],
        "lookback_days": lookback_days,
        "restored_snapshots": int(repair_report.get("restored", 0) or 0),
        "snapshot_repair": repair_report,
        "analysis_history_backfill": history_backfill,
        "analysis_history_trace_fact_ref_backfill": repair_report.get("history_trace_fact_ref_backfill", {}),
        "source": "none",
        "messages": [],
        "items": [],
        "parlay_items": [],
        "gate": {},
    }

    if MatchFetcherTitan is None:
        summary["messages"].append("Titan 抓取器不可用，无法自动回收赛果。")
        return summary

    try:
        fetcher = MatchFetcherTitan(debug=False)
        if hasattr(fetcher, "get_recent_finished_matches"):
            finished_matches = fetcher.get_recent_finished_matches(lookback_days=lookback_days)
        else:
            finished_matches = fetcher.get_today_finished_matches()
    except Exception as exc:
        summary["messages"].append(f"自动回收赛果失败: {exc}")
        return summary

    summary["fetched_finished"] = len(finished_matches)
    summary["source"] = "live:titan"

    settlements = STATE_STORE.load_settlements()
    settled_ids = {str(item.get("match_id", "")) for item in settlements if item.get("match_id")}
    snapshot_records = STATE_STORE.load_prediction_snapshots()
    snapshot_audit = build_result_recovery_snapshot_audit(
        snapshot_records,
        settlements,
        lookback_days=lookback_days,
    )
    summary["snapshot_audit"] = snapshot_audit
    summary["snapshot_recoverable"] = int(snapshot_audit.get("recoverable_schedule_id", 0) or 0)
    summary["snapshot_recoverable_titan"] = int(snapshot_audit.get("recoverable_titan", 0) or 0)
    summary["snapshot_recoverable_cache_source"] = int(snapshot_audit.get("recoverable_cache_source", 0) or 0)
    summary["snapshot_missing_source_id"] = int(snapshot_audit.get("missing_source_id", 0) or 0)
    summary["snapshot_out_of_window"] = int(snapshot_audit.get("out_of_window", 0) or 0)
    summary["snapshot_non_titan_source"] = int(snapshot_audit.get("non_titan_source", 0) or 0)
    candidate_ids: set[str] = set()
    candidates: list[tuple[AppMatch, int, int, dict | None]] = []

    def in_lookback_window(match_date: str) -> bool:
        try:
            dt = datetime.strptime(match_date, "%Y-%m-%d").date()
        except Exception:
            return False
        today = datetime.now().date()
        return (today - dt).days in range(0, lookback_days + 1)

    def append_candidate(
        app_match: AppMatch,
        home_goals: int | None,
        away_goals: int | None,
        snapshot_record: dict | None,
    ) -> None:
        if app_match.match_id in settled_ids:
            summary["already_settled"] += 1
            return
        if app_match.match_id in candidate_ids:
            return
        if home_goals is None or away_goals is None:
            summary["skipped"] += 1
            return
        candidates.append((app_match, int(home_goals), int(away_goals), snapshot_record))
        candidate_ids.add(app_match.match_id)

    for item in finished_matches:
        app_match = AppMatch(
            home_team=item.home_team,
            away_team=item.away_team,
            league=item.league,
            match_time=item.match_time,
            match_date=item.match_date,
            odds_home=item.odds_home,
            odds_draw=item.odds_draw,
            odds_away=item.odds_away,
            handicap_line=_safe_float(getattr(item, "handicap_line", 0.0), default=0.0),
            source="live:titan:result",
            source_id=item.match_id,
        )
        snapshot_record = snapshot_records.get(app_match.match_id)
        if isinstance(snapshot_record, dict):
            snapshot_match = snapshot_record.get("match")
            if isinstance(snapshot_match, dict):
                # 完场赔率可能为空，优先回填赛前快照里的赔率与开赛时间。
                app_match.odds_home = _safe_float(snapshot_match.get("odds_home"), app_match.odds_home)
                app_match.odds_draw = _safe_float(snapshot_match.get("odds_draw"), app_match.odds_draw)
                app_match.odds_away = _safe_float(snapshot_match.get("odds_away"), app_match.odds_away)
                app_match.handicap_line = _safe_float(snapshot_match.get("handicap_line"), app_match.handicap_line)
                match_time = normalize_text(snapshot_match.get("match_time", ""))
                if match_time:
                    app_match.match_time = match_time
        append_candidate(app_match, item.home_goals, item.away_goals, snapshot_record)

    # 兜底: 对重启后丢失于主赛事流中的比赛，按快照保存的 Titan schedule_id 回查赛果。
    for snapshot_match_id, snapshot_record in snapshot_records.items():
        if snapshot_match_id in settled_ids or snapshot_match_id in candidate_ids:
            continue
        if not isinstance(snapshot_record, dict):
            continue
        snapshot_match = snapshot_record.get("match")
        app_match = _app_match_from_payload(snapshot_match, source="snapshot:titan:result")
        if app_match is None or not in_lookback_window(app_match.match_date):
            continue
        snapshot_source = normalize_text(snapshot_match.get("source", "") if isinstance(snapshot_match, dict) else "")
        schedule_id = _snapshot_result_schedule_id(
            snapshot_source,
            snapshot_match.get("source_id", "") if isinstance(snapshot_match, dict) else "",
        )
        if not schedule_id or not hasattr(fetcher, "get_result_by_schedule_id"):
            continue
        summary["snapshot_checked"] += 1
        result = fetcher.get_result_by_schedule_id(schedule_id)
        lookup = classify_snapshot_result_lookup(result)
        if not lookup.get("is_finished"):
            reason = str(lookup.get("reason") or "unknown")
            summary["snapshot_result_misses"] += 1
            miss_reasons = summary["snapshot_result_miss_reasons"]
            if isinstance(miss_reasons, dict):
                miss_reasons[reason] = int(miss_reasons.get(reason, 0) or 0) + 1
            miss_items = summary["snapshot_result_miss_items"]
            if isinstance(miss_items, list) and len(miss_items) < 20:
                miss_items.append(
                    {
                        "match_id": app_match.match_id,
                        "match_date": app_match.match_date,
                        "league": app_match.league,
                        "home_team": app_match.home_team,
                        "away_team": app_match.away_team,
                        "schedule_id": schedule_id,
                        "reason": reason,
                        "state_code": lookup.get("state_code", ""),
                        "home_goals": lookup.get("home_goals"),
                        "away_goals": lookup.get("away_goals"),
                    }
                )
            continue
        app_match.source = (
            "snapshot:titan:analysisheader"
            if "titan" in snapshot_source.lower()
            else "snapshot:cache:analysisheader"
        )
        app_match.source_id = schedule_id
        append_candidate(app_match, lookup.get("home_goals"), lookup.get("away_goals"), snapshot_record)
        summary["snapshot_result_hits"] += 1

    if not candidates:
        parlay_summary = auto_settle_pending_parlays()
        summary["new_parlay_settled"] = parlay_summary.get("new_settled", 0)
        summary["parlay_items"] = parlay_summary.get("items", [])
        summary["gate"] = get_gate_metrics(window=20)
        summary["messages"].append(
            f"最近 {lookback_days} 天未发现可自动结算的新完场比赛（修复快照 {summary['restored_snapshots']} 场，快照回查 {summary['snapshot_checked']} 场，命中 {summary['snapshot_result_hits']} 场）。"
        )
        summary["messages"].append(
            "快照审计: 待回收 {pending} 场，可自动回查 {recoverable} 场，缺 source_id {missing} 场，不可回查来源 {non_titan} 场，超出窗口 {out_window} 场。".format(
                pending=int(snapshot_audit.get("pending", 0) or 0),
                recoverable=int(snapshot_audit.get("recoverable_schedule_id", 0) or 0),
                missing=int(snapshot_audit.get("missing_source_id", 0) or 0),
                non_titan=int(snapshot_audit.get("non_titan_source", 0) or 0),
                out_window=int(snapshot_audit.get("out_of_window", 0) or 0),
            )
        )
        return summary

    prediction_bank: dict[str, dict] = {}
    for app_match, _home_goals, _away_goals, snapshot_record in candidates:
        cached = prediction_cache.get(app_match.match_id) if prediction_cache else None
        if isinstance(cached, dict):
            prediction_bank[app_match.match_id] = cached
            continue
        snapshot_prediction = snapshot_record.get("prediction") if isinstance(snapshot_record, dict) else None
        if isinstance(snapshot_prediction, dict):
            prediction_bank[app_match.match_id] = snapshot_prediction
            summary["snapshot_predictions"] += 1
            continue
        prediction_bank[app_match.match_id] = predict_match(app_match)

    for app_match, home_goals, away_goals, _snapshot_record in candidates:
        prediction = prediction_bank.get(app_match.match_id)
        settlement = settle_match_result(
            match=app_match,
            home_goals=home_goals,
            away_goals=away_goals,
            prediction=prediction,
        )
        if settlement.get("duplicate_skipped"):
            summary["already_settled"] += 1
            continue
        summary["items"].append(settlement)
        summary["new_settled"] += 1

    parlay_summary = auto_settle_pending_parlays()
    summary["new_parlay_settled"] = parlay_summary.get("new_settled", 0)
    summary["parlay_items"] = parlay_summary.get("items", [])
    summary["gate"] = get_gate_metrics(window=20)

    summary["messages"].append(
        f"自动回收完成(近{lookback_days}天): 主源完场 {summary['fetched_finished']} 场, 修复快照 {summary['restored_snapshots']} 场, 快照回查命中 {summary['snapshot_result_hits']} 场, 新增单场结算 {summary['new_settled']} 场, 新增二串一结算 {summary['new_parlay_settled']} 场, 预测快照命中 {summary['snapshot_predictions']} 场。"
    )
    summary["messages"].append(
        "快照审计: 待回收 {pending} 场，可自动回查 {recoverable} 场，缺 source_id {missing} 场，不可回查来源 {non_titan} 场，超出窗口 {out_window} 场。".format(
            pending=int(snapshot_audit.get("pending", 0) or 0),
            recoverable=int(snapshot_audit.get("recoverable_schedule_id", 0) or 0),
            missing=int(snapshot_audit.get("missing_source_id", 0) or 0),
            non_titan=int(snapshot_audit.get("non_titan_source", 0) or 0),
            out_window=int(snapshot_audit.get("out_of_window", 0) or 0),
        )
    )
    return summary


def get_xgb_training_status() -> dict:
    return XGBOOST_MODEL.get_training_status()


def train_xgb_v0_now(force_min_samples: int | None = None) -> dict:
    return XGBOOST_MODEL.train_now(force_min_samples=force_min_samples)


def _prediction_model_warmup_targets() -> list[tuple[str, object]]:
    return [
        ("xgb_outcome", XGBOOST_MODEL),
        ("total_goals", TOTAL_GOALS_MODEL),
        ("scoreline", SCORELINE_MODEL),
        ("volatile_scoreline", VOLATILE_SCORELINE_MODEL),
    ]


def _warmup_recent_form_cache() -> dict:
    histories = _recent_form_team_histories()
    return {
        "team_count": len(histories),
        "history_entry_count": sum(len(entries) for entries in histories.values() if isinstance(entries, list)),
    }


def _warmup_dynamic_play_thresholds() -> dict:
    thresholds, meta = _runtime_dynamic_play_thresholds(_current_play_thresholds())
    return {
        "threshold_count": len(thresholds),
        "adjustment_reason": meta.get("reason") if isinstance(meta, dict) else "",
    }


def _warmup_market_snapshot_cache() -> dict:
    signature = _state_store_path_signature("market_snapshots_file")
    if signature is not None and _MARKET_SNAPSHOT_RECORD_CACHE.get("signature") == signature:
        items = _MARKET_SNAPSHOT_RECORD_CACHE.get("items", {})
    else:
        items = STATE_STORE.load_market_snapshots()
        _MARKET_SNAPSHOT_RECORD_CACHE["signature"] = signature
        _MARKET_SNAPSHOT_RECORD_CACHE["items"] = items
    return {"snapshot_count": len(items) if isinstance(items, dict) else 0}


def _prediction_runtime_warmup_targets() -> list[tuple[str, object]]:
    return [
        ("recent_form", _warmup_recent_form_cache),
        ("market_snapshots", _warmup_market_snapshot_cache),
        ("play_thresholds", get_play_threshold_status),
        ("dynamic_play_thresholds", _warmup_dynamic_play_thresholds),
        ("bayes_calibration", get_bayes_calibration_status),
        ("play_model_policy", get_play_model_policy_status),
        ("strategy_admission_policy", get_strategy_admission_policy_status),
        ("high_accuracy_strategy", get_high_accuracy_strategy_status),
    ]


def warmup_prediction_models(*, include_runtime_caches: bool = True) -> dict:
    started = time.perf_counter()
    items: list[dict] = []
    ready_count = 0
    for name, model in _prediction_model_warmup_targets():
        item_started = time.perf_counter()
        model_file = getattr(model, "model_file", None)
        model_exists = bool(isinstance(model_file, Path) and model_file.exists())
        item = {
            "model": name,
            "model_exists": model_exists,
            "ready": False,
            "status": "missing_model" if not model_exists else "pending",
        }
        try:
            loader = getattr(model, "_load_model", None)
            if callable(loader):
                loader()
            ready = bool(getattr(model, "_model_ready", False))
            item["ready"] = ready
            item["status"] = "ready" if ready else ("missing_model" if not model_exists else "not_ready")
            if ready:
                ready_count += 1
        except Exception as exc:
            item["status"] = "error"
            item["error"] = str(exc)
        item["elapsed_seconds"] = round(time.perf_counter() - item_started, 4)
        item["kind"] = "model"
        items.append(item)

    if include_runtime_caches:
        for name, loader in _prediction_runtime_warmup_targets():
            item_started = time.perf_counter()
            item = {
                "model": name,
                "kind": "runtime_cache",
                "model_exists": True,
                "ready": False,
                "status": "pending",
            }
            try:
                payload = loader() if callable(loader) else {}
                item["ready"] = True
                item["status"] = "ready"
                if isinstance(payload, dict):
                    item["summary"] = payload
                ready_count += 1
            except Exception as exc:
                item["status"] = "error"
                item["error"] = str(exc)
            item["elapsed_seconds"] = round(time.perf_counter() - item_started, 4)
            items.append(item)

    total = len(items)
    if ready_count == total and total > 0:
        status = "ready"
    elif any(item.get("status") == "error" for item in items):
        status = "error"
    elif ready_count > 0:
        status = "partial"
    else:
        status = "not_ready"
    return {
        "status": status,
        "ready_count": ready_count,
        "total_count": total,
        "items": items,
        "elapsed_seconds": round(time.perf_counter() - started, 4),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_play_model_training_status() -> dict:
    return {
        "total_goals": TOTAL_GOALS_MODEL.get_training_status(),
        "scoreline": SCORELINE_MODEL.get_training_status(),
        "volatile_scoreline": VOLATILE_SCORELINE_MODEL.get_training_status(),
    }


def train_play_models_now(force_min_samples: int | None = None) -> dict:
    total_goals = TOTAL_GOALS_MODEL.train_now(force_min_samples=force_min_samples)
    scoreline = SCORELINE_MODEL.train_now(force_min_samples=force_min_samples)
    volatile_scoreline = VOLATILE_SCORELINE_MODEL.train_now(force_min_samples=force_min_samples)
    return {
        "trained": bool(total_goals.get("trained")) or bool(scoreline.get("trained")) or bool(volatile_scoreline.get("trained")),
        "reason": "ok" if bool(total_goals.get("trained")) or bool(scoreline.get("trained")) or bool(volatile_scoreline.get("trained")) else "no_model_trained",
        "total_goals": total_goals,
        "scoreline": scoreline,
        "volatile_scoreline": volatile_scoreline,
        "status": get_play_model_training_status(),
    }


def _training_gate_report_lines(title: str, gate: dict | None) -> list[str]:
    resolved = gate if isinstance(gate, dict) else {}
    xgb = resolved.get("xgb", {}) if isinstance(resolved.get("xgb"), dict) else {}
    play = resolved.get("play_models", {}) if isinstance(resolved.get("play_models"), dict) else {}
    lines = [
        f"## {title}",
        "",
        f"- Status: {resolved.get('status') or '-'}",
        f"- Recommended Action: {resolved.get('recommended_action') or '-'}",
        f"- Recommendation: {resolved.get('recommendation') or '-'}",
        f"- XGB: trainable={bool(xgb.get('trainable'))} | ready={bool(xgb.get('model_ready'))} | samples={xgb.get('sample_count', 0)}/{xgb.get('min_sample_count', 0)} | features={xgb.get('valid_feature_count', 0)}/{xgb.get('min_valid_feature_count', 0)}",
        f"- Play Models: trainable={play.get('trainable_count', 0)}/{play.get('total_count', 0)} | ready={play.get('ready_count', 0)}/{play.get('total_count', 0)}",
    ]
    for item in play.get("items", []) if isinstance(play.get("items"), list) else []:
        if not isinstance(item, dict):
            continue
        lines.append(
            f"  - {item.get('label') or item.get('key')}: usable={item.get('usable_count', 0)}/{item.get('min_train_samples', 0)} | ready={bool(item.get('model_ready'))}"
        )
    return lines


def write_training_followup_report(
    *,
    train_kind: str,
    train_result: dict,
    before_gate: dict | None,
    after_gate: dict | None,
    auto_backtest: dict | None = None,
) -> str:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    kind = normalize_text(train_kind) or "training"
    report_path = REPORT_DIR / f"training_followup_{kind}_{timestamp}.md"
    backtest = auto_backtest if isinstance(auto_backtest, dict) else {"executed": False}
    validation = backtest.get("validation", {}) if isinstance(backtest.get("validation"), dict) else {}
    improvement = backtest.get("improvement", {}) if isinstance(backtest.get("improvement"), dict) else {}
    takeover_gate = backtest.get("takeover_gate", {}) if isinstance(backtest.get("takeover_gate"), dict) else {}
    takeover_gate_metrics = takeover_gate.get("metrics", {}) if isinstance(takeover_gate.get("metrics"), dict) else {}
    takeover_gate_issues = takeover_gate.get("issues", []) if isinstance(takeover_gate.get("issues"), list) else []
    lines = [
        "# Training Follow-up Report",
        "",
        f"- Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Train Kind: {kind}",
        f"- Trained: {bool(train_result.get('trained'))}",
        f"- Reason: {train_result.get('reason') or '-'}",
        "",
        "## Training Result",
        "",
        f"- XGB Samples: {train_result.get('sample_count', '-')}",
        f"- Total Goals: {train_result.get('total_goals', {}).get('reason', '-') if isinstance(train_result.get('total_goals'), dict) else '-'}",
        f"- Scoreline: {train_result.get('scoreline', {}).get('reason', '-') if isinstance(train_result.get('scoreline'), dict) else '-'}",
        f"- Volatile Scoreline: {train_result.get('volatile_scoreline', {}).get('reason', '-') if isinstance(train_result.get('volatile_scoreline'), dict) else '-'}",
        "",
        *_training_gate_report_lines("Training Gate Before", before_gate),
        "",
        *_training_gate_report_lines("Training Gate After", after_gate),
        "",
        "## Auto Backtest",
        "",
        f"- Executed: {bool(backtest.get('executed'))}",
        f"- OK: {bool(backtest.get('ok'))}",
        f"- Reason: {backtest.get('reason') or '-'}",
        f"- Validation Samples: {validation.get('sample_count', '-')}",
        f"- Validation Window: {validation.get('date_start') or '-'} -> {validation.get('date_end') or '-'}",
        f"- Total Goals Model Delta: {float(improvement.get('total_goals_model_delta', 0) or 0):+.2%}",
        f"- Score Model Delta: {float(improvement.get('score_model_delta', 0) or 0):+.2%}",
        f"- Backtest Report: {backtest.get('report_path') or '-'}",
        "",
        "## Takeover Gate",
        "",
        f"- Status: {takeover_gate.get('status') or '-'}",
        f"- Mode: {takeover_gate.get('mode') or '-'}",
        f"- Policy Impact: {takeover_gate.get('policy_impact') or '-'}",
        f"- Training Gate: {takeover_gate_metrics.get('training_gate_status') or '-'}",
        f"- Validation Samples: {takeover_gate_metrics.get('validation_sample_count', '-')}/{takeover_gate_metrics.get('min_validation_samples', '-')}",
        f"- Total Goals Delta: {float(takeover_gate_metrics.get('total_goals_model_delta', 0) or 0):+.2%}",
        f"- Score Model Delta: {float(takeover_gate_metrics.get('score_model_delta', 0) or 0):+.2%}",
        f"- Recommendation: {takeover_gate.get('recommendation') or '-'}",
        f"- Top Issues: {', '.join(str(item.get('code') or '-') for item in takeover_gate_issues[:3] if isinstance(item, dict)) or '-'}",
        "",
        "## Next Step",
        "",
        f"- {(after_gate or {}).get('recommendation') or '-'}",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return str(report_path)


def run_training_postcheck(
    train_kind: str,
    train_result: dict,
    *,
    before_gate: dict | None = None,
    auto_backtest: dict | None = None,
    write_report: bool = True,
) -> dict:
    after_gate = get_training_model_gate_status()
    backtest = dict(auto_backtest) if isinstance(auto_backtest, dict) else {"executed": False, "reason": "not_requested"}
    existing_takeover_gate = backtest.get("takeover_gate")
    if bool(backtest.get("executed")) and (
        not isinstance(existing_takeover_gate, dict) or not existing_takeover_gate.get("status")
    ):
        gate_input = backtest.get("result") if isinstance(backtest.get("result"), dict) else backtest
        takeover_gate = evaluate_play_model_takeover_gate(gate_input, training_gate=after_gate)
        backtest["takeover_gate"] = takeover_gate
        if isinstance(backtest.get("result"), dict):
            nested_result = dict(backtest["result"])
            nested_result["takeover_gate"] = takeover_gate
            backtest["result"] = nested_result
    report_path = None
    if write_report:
        report_path = write_training_followup_report(
            train_kind=train_kind,
            train_result=train_result,
            before_gate=before_gate,
            after_gate=after_gate,
            auto_backtest=backtest,
        )
    return {
        "status": after_gate.get("status"),
        "recommended_action": after_gate.get("recommended_action"),
        "recommendation": after_gate.get("recommendation"),
        "training_gate_before": before_gate or {},
        "training_gate_after": after_gate,
        "auto_backtest": backtest,
        "report_path": report_path,
    }


def train_xgb_v0_with_postcheck_now(force_min_samples: int | None = None) -> dict:
    before_gate = get_training_model_gate_status()
    result = train_xgb_v0_now(force_min_samples=force_min_samples)
    auto_backtest = {"executed": False, "reason": "xgb_training_only"}
    postcheck = run_training_postcheck(
        "xgb",
        result,
        before_gate=before_gate,
        auto_backtest=auto_backtest,
    )
    return {
        **result,
        "training_gate_before": before_gate,
        "training_gate_after": postcheck.get("training_gate_after", {}),
        "postcheck": postcheck,
        "auto_backtest": postcheck.get("auto_backtest", auto_backtest),
    }


def train_play_models_with_backtest_now(
    force_min_samples: int | None = None,
    max_validation_samples: int = 1000,
) -> dict:
    before_gate = get_training_model_gate_status()
    result = train_play_models_now(force_min_samples=force_min_samples)
    if bool(result.get("trained")):
        try:
            backtest_result = run_play_model_backtest(max_validation_samples=max_validation_samples, write_report=True)
            auto_backtest = {
                "executed": True,
                "ok": bool(backtest_result.get("ok")),
                "reason": backtest_result.get("reason"),
                "report_path": backtest_result.get("report_path"),
                "validation": backtest_result.get("validation", {}),
                "improvement": backtest_result.get("improvement", {}),
                "takeover_gate": backtest_result.get("takeover_gate", {}),
                "result": backtest_result,
            }
        except Exception as exc:
            auto_backtest = {
                "executed": True,
                "ok": False,
                "reason": f"backtest_failed:{exc}",
                "report_path": None,
            }
    else:
        auto_backtest = {
            "executed": False,
            "ok": False,
            "reason": "training_not_completed",
            "report_path": None,
        }
    postcheck = run_training_postcheck(
        "play_models",
        result,
        before_gate=before_gate,
        auto_backtest=auto_backtest,
    )
    return {
        **result,
        "training_gate_before": before_gate,
        "training_gate_after": postcheck.get("training_gate_after", {}),
        "postcheck": postcheck,
        "auto_backtest": postcheck.get("auto_backtest", auto_backtest),
    }


def _export_report_v2(matches: list[AppMatch], predictions: dict[str, dict]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"recommendation_report_{timestamp}.md"

    lines = [
        "# V24 瓒崇悆鎺ㄨ崘鎶ュ憡",
        "",
        f"- 鐢熸垚鏃堕棿: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 鍦烘鏁伴噺: {len(matches)}",
        "",
        "| 鏃ユ湡 | 鏃堕棿 | 鑱旇禌 | 瀵归樀 | 鎺ㄨ崘 | 鎬昏繘鐞冮娴? | 鍗婂叏鍦洪娴? | 姣斿垎棰勬祴 | 缃俊搴? | 鍐烽棬鎸囨暟 |",
        "|---|---|---|---|---|---|---|---|---:|---:|",
    ]

    for match in matches:
        prediction = predictions.get(match.match_id) or predict_match(match)
        total_goals_pick, _, _ = _extract_total_goals_prediction(prediction)
        score_pick, _ = _extract_score_prediction(prediction)
        htft_pick, _ = _extract_htft_prediction(prediction)
        lines.append(
            f"| {match.match_date} | {match.match_time} | {match.league} | "
            f"{match.home_team} vs {match.away_team} | {prediction['recommendation']} | "
            f"{total_goals_pick or '-'} | "
            f"{htft_pick or '-'} | "
            f"{score_pick or '-'} | "
            f"{prediction['confidence']:.1%} | {prediction.get('indices', {}).get('upset_index', 0):.1%} |"
        )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def export_report(matches: list[AppMatch], predictions: dict[str, dict]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"recommendation_report_{timestamp}.md"

    lines = [
        "# V24 足球推荐报告",
        "",
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 场次数量: {len(matches)}",
        "",
        "| 日期 | 时间 | 联赛 | 对阵 | 推荐 | O/U推荐 | 置信度 | 最可能比分 | 大2.5概率 | 冷门指数 |",
        "|---|---|---|---|---|---|---:|---|---:|---:|",
    ]

    for match in matches:
        prediction = predictions.get(match.match_id) or predict_match(match)
        poisson = prediction.get("poisson", {})
        top_scores = poisson.get("top_scores", [])
        best_score = top_scores[0]["score"] if top_scores else "-"
        lines.append(
            f"| {match.match_date} | {match.match_time} | {match.league} | "
            f"{match.home_team} vs {match.away_team} | {prediction['recommendation']} | "
            f"{prediction.get('ou_recommendation', '-')} | "
            f"{prediction['confidence']:.1%} | {best_score} | "
            f"{poisson.get('over_2_5', 0):.1%} | {prediction.get('indices', {}).get('upset_index', 0):.1%} |"
        )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _export_report_v3(matches: list[AppMatch], predictions: dict[str, dict]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"recommendation_report_{timestamp}.md"

    lines = [
        "# V24 Recommendation Report",
        "",
        f"- Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Match Count: {len(matches)}",
        "",
        "| Date | Time | League | Match | 1X2 | Handicap | Total Goals | HT/FT | Score | Confidence | Upset |",
        "|---|---|---|---|---|---|---|---|---|---:|---:|",
    ]

    for match in matches:
        prediction = predictions.get(match.match_id) or predict_match(match)
        handicap_pick = prediction.get("handicap_display") or prediction.get("handicap_recommendation") or "-"
        total_goals_pick, _, _ = _extract_total_goals_prediction(prediction)
        score_pick, _ = _extract_score_prediction(prediction)
        htft_pick, _ = _extract_htft_prediction(prediction)
        lines.append(
            f"| {match.match_date} | {match.match_time} | {match.league} | "
            f"{match.home_team} vs {match.away_team} | {prediction['recommendation']} | "
            f"{handicap_pick} | "
            f"{total_goals_pick or '-'} | "
            f"{htft_pick or '-'} | "
            f"{score_pick or '-'} | "
            f"{prediction['confidence']:.1%} | {prediction.get('indices', {}).get('upset_index', 0):.1%} |"
        )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def serialize_match(match: AppMatch) -> dict:
    return asdict(match)


export_report = _export_report_v3
