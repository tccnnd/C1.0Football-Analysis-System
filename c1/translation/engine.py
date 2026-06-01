from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from c1.core.reason_codes import DecisionAction
from c1.translation.schema import TranslationItem, TranslationRequest, TranslationResult
from c1.translation.htft_translator import translate_htft
from c1.translation.scoreline_translator import translate_scoreline


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "translation_cfg.yaml"
TRANSLATOR_VERSION = "c1.phase5.translation"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def load_translation_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid translation config: {config_path}")
    return payload


class C1TranslationEngine:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_translation_config()

    def translate(self, request: TranslationRequest) -> TranslationResult:
        governance_status = self._status_from_action(request.governance_decision.action)
        items = [
            self._translate_one_x_two(request, governance_status),
            self._translate_handicap(request, governance_status),
            self._translate_totals(request, governance_status),
            self._translate_htft(request, governance_status),
            self._translate_scoreline(request, governance_status),
        ]
        return TranslationResult(
            match_id=request.match_id,
            translator_version=TRANSLATOR_VERSION,
            governance_action=str(request.governance_decision.action),
            items=items,
            metadata={
                "allow_output": request.governance_decision.allow_output,
                "shadow_mode": request.governance_decision.shadow_mode,
                "reason_codes": list(request.governance_decision.reason_codes),
            },
        )

    @staticmethod
    def _status_from_action(action: DecisionAction) -> str:
        mapping = {
            DecisionAction.APPROVE: "ACTIVE",
            DecisionAction.DOWNGRADE: "DOWNGRADED",
            DecisionAction.OBSERVE: "SHADOW",
            DecisionAction.BLOCK: "BLOCKED",
        }
        return mapping.get(action, "ACTIVE")

    def _translate_one_x_two(self, request: TranslationRequest, governance_status: str) -> TranslationItem:
        probabilities = request.inference_result.raw_probabilities
        predicted_side = str(request.inference_result.predicted_side)
        confidence = float(request.inference_result.confidence)
        ev = float(request.inference_result.ev_by_side.get(predicted_side, 0.0))
        draw_prob = float(probabilities.get("draw", 0.0))
        config = self.config.get("one_x_two", {})
        rationale: list[str] = []
        selection_map = {
            "home": "HOME_WIN",
            "draw": "DRAW",
            "away": "AWAY_WIN",
        }

        if governance_status == "BLOCKED":
            return TranslationItem(
                play="1x2",
                status=governance_status,
                confidence=round(confidence, 6),
                rationale=["governance_blocked_output"],
                evidence={"predicted_side": predicted_side, "ev": ev},
                tags=["blocked"],
            )

        if predicted_side == "draw" and draw_prob < _safe_float(config.get("draw_min_probability"), 0.30):
            rationale.append("draw_probability_below_threshold")
        if confidence < _safe_float(config.get("min_confidence"), 0.58):
            rationale.append("confidence_below_threshold")
        if ev < _safe_float(config.get("min_ev"), -0.02):
            rationale.append("ev_below_threshold")

        selection = selection_map.get(predicted_side)
        if rationale:
            selection = None
        else:
            rationale.append("raw_side_translation_pass")

        return TranslationItem(
            play="1x2",
            status=governance_status,
            selection=selection,
            confidence=round(confidence, 6),
            rationale=rationale,
            evidence={
                "predicted_side": predicted_side,
                "ev": round(ev, 6),
                "probabilities": dict(probabilities),
            },
            tags=["governance:" + governance_status.lower()],
        )

    def _translate_handicap(self, request: TranslationRequest, governance_status: str) -> TranslationItem:
        fields = request.feature_snapshot.fields
        probabilities = request.inference_result.raw_probabilities
        config = self.config.get("handicap", {})
        confidence = float(request.inference_result.confidence)
        line = _safe_float(
            fields.get("handicap_line"),
            default=_safe_float(fields.get("goal"), default=0.0),
        )
        rationale: list[str] = []

        if governance_status == "BLOCKED":
            return TranslationItem(
                play="handicap",
                status=governance_status,
                line=line,
                confidence=round(confidence, 6),
                rationale=["governance_blocked_output"],
                evidence={"handicap_line": line},
                tags=["blocked"],
            )

        if abs(line) > _safe_float(config.get("supported_line_abs_max"), 2.25):
            rationale.append("unsupported_handicap_line")

        home_prob = float(probabilities.get("home", 0.0))
        draw_prob = float(probabilities.get("draw", 0.0))
        away_prob = float(probabilities.get("away", 0.0))
        rating_diff = _safe_float(fields.get("home_rating"), 1500.0) - _safe_float(fields.get("away_rating"), 1500.0)

        rating_signal = _clamp(rating_diff / 400.0, -1.0, 1.0) * _safe_float(config.get("rating_diff_scale"), 0.55)
        side_strength = (home_prob - away_prob) * _safe_float(config.get("side_strength_scale"), 1.65)
        draw_drag = draw_prob * _safe_float(config.get("draw_drag_scale"), 0.75)
        estimated_goal_diff = side_strength + rating_signal - draw_drag

        home_cover_edge = estimated_goal_diff + line
        away_cover_edge = -(estimated_goal_diff + line)
        cover_threshold = _safe_float(config.get("min_cover_edge"), 0.28)
        side_gap_min = _safe_float(config.get("min_side_gap"), 0.05)

        selection: str | None = None
        if not rationale:
            if (
                home_cover_edge >= cover_threshold
                and (home_prob - away_prob) >= side_gap_min
                and draw_prob <= _safe_float(config.get("draw_prob_max_for_side"), 0.31)
            ):
                selection = "HOME_HANDICAP"
                rationale.append("handicap_home_cover_edge_pass")
            elif (
                away_cover_edge >= cover_threshold
                and (away_prob - home_prob) >= -side_gap_min
            ):
                selection = "AWAY_HANDICAP"
                rationale.append("handicap_away_cover_edge_pass")
            else:
                rationale.append("handicap_edge_below_threshold")

        return TranslationItem(
            play="handicap",
            status=governance_status,
            selection=selection,
            line=round(line, 3),
            confidence=round(confidence, 6),
            rationale=rationale,
            evidence={
                "estimated_goal_diff": round(estimated_goal_diff, 6),
                "home_cover_edge": round(home_cover_edge, 6),
                "away_cover_edge": round(away_cover_edge, 6),
                "probabilities": dict(probabilities),
            },
            tags=["independent_translation", "no_naive_1x2_mapping"],
        )

    def _translate_totals(self, request: TranslationRequest, governance_status: str) -> TranslationItem:
        fields = request.feature_snapshot.fields
        config = self.config.get("totals", {})
        confidence = float(request.inference_result.confidence)
        line = _safe_float(
            fields.get("total_goals_line"),
            default=_safe_float(fields.get("ou_line"), default=_safe_float(config.get("default_line"), 2.5)),
        )
        expected_goals = _safe_float(request.inference_result.metadata.get("expected_goals"), _safe_float(config.get("default_expected_goals"), 2.5))
        total_edge = expected_goals - line
        threshold = _safe_float(config.get("min_total_edge"), 0.22)
        rationale: list[str] = []

        if governance_status == "BLOCKED":
            return TranslationItem(
                play="totals",
                status=governance_status,
                line=line,
                confidence=round(confidence, 6),
                rationale=["governance_blocked_output"],
                evidence={"expected_goals": expected_goals, "line": line},
                tags=["blocked"],
            )

        selection: str | None = None
        if total_edge >= threshold:
            selection = "OVER"
            rationale.append("expected_goals_above_total_line")
        elif total_edge <= -threshold:
            selection = "UNDER"
            rationale.append("expected_goals_below_total_line")
        else:
            rationale.append("total_edge_below_threshold")

        return TranslationItem(
            play="totals",
            status=governance_status,
            selection=selection,
            line=round(line, 3),
            confidence=round(confidence, 6),
            rationale=rationale,
            evidence={
                "expected_goals": round(expected_goals, 6),
                "total_edge": round(total_edge, 6),
            },
            tags=["goal_total_translation"],
        )

    def _translate_htft(self, request: TranslationRequest, governance_status: str) -> TranslationItem:
        """Translate to HT/FT outcomes."""
        probabilities = request.inference_result.raw_probabilities
        confidence = float(request.inference_result.confidence)
        fields = request.feature_snapshot.fields
        home_rating = _safe_float(fields.get("home_rating"), 1500.0)
        away_rating = _safe_float(fields.get("away_rating"), 1500.0)
        config = self.config.get("htft", {})
        
        return translate_htft(
            raw_probabilities=probabilities,
            confidence=confidence,
            governance_status=governance_status,
            home_rating=home_rating,
            away_rating=away_rating,
            config=config,
        )

    def _translate_scoreline(self, request: TranslationRequest, governance_status: str) -> TranslationItem:
        """Translate to scoreline outcomes."""
        probabilities = request.inference_result.raw_probabilities
        confidence = float(request.inference_result.confidence)
        fields = request.feature_snapshot.fields
        home_rating = _safe_float(fields.get("home_rating"), 1500.0)
        away_rating = _safe_float(fields.get("away_rating"), 1500.0)
        config = self.config.get("scoreline", {})
        
        return translate_scoreline(
            raw_probabilities=probabilities,
            confidence=confidence,
            governance_status=governance_status,
            home_rating=home_rating,
            away_rating=away_rating,
            config=config,
        )
