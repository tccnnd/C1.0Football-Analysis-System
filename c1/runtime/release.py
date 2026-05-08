from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from c1.audit import C1AuditStore
from c1.runtime.shadow import C1ShadowRunResult, C1ShadowRunner


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "release_cfg.yaml"


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _side_to_1x2_selection(side: str) -> str | None:
    mapping = {
        "home": "HOME_WIN",
        "draw": "DRAW",
        "away": "AWAY_WIN",
    }
    return mapping.get(str(side).strip().lower())


def load_release_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid release config: {config_path}")
    return payload


@dataclass(slots=True)
class C1ReleaseCandidate:
    play: str
    selection: str
    line: float | None
    confidence: float
    status: str
    rationale: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class C1ReleaseDecision:
    match_id: str
    release_action: str
    release_allowed: bool
    governance_action: str
    primary_reason_code: str | None
    candidates: list[C1ReleaseCandidate] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class C1ReleaseManager:
    def __init__(
        self,
        project_root: str | Path,
        *,
        audit_dir: str | Path | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.audit = C1AuditStore(self.project_root, audit_dir=audit_dir)
        self.config = config or load_release_config()

    def _build_fallback_candidates(
        self,
        *,
        shadow_result: C1ShadowRunResult,
        min_confidence: float,
    ) -> list[C1ReleaseCandidate]:
        fallback_cfg = self.config.get("fallback", {}) if isinstance(self.config, dict) else {}
        if not isinstance(fallback_cfg, dict) or not bool(fallback_cfg.get("enabled", False)):
            return []
        allowed_fallback_plays = [
            str(item).strip()
            for item in fallback_cfg.get("allowed_plays", ["1x2", "handicap"])
            if str(item).strip()
        ]
        if not allowed_fallback_plays:
            return []

        min_conf = max(min_confidence, _safe_float(fallback_cfg.get("min_confidence"), 0.30))
        min_ev = _safe_float(fallback_cfg.get("min_ev"), -0.25)
        inference = shadow_result.inference_result
        fields = shadow_result.feature_snapshot.fields if isinstance(shadow_result.feature_snapshot.fields, dict) else {}
        probs = inference.raw_probabilities if isinstance(inference.raw_probabilities, dict) else {}
        predicted_side = str(inference.predicted_side).strip().lower()
        confidence = _safe_float(inference.confidence, 0.0)
        predicted_ev = _safe_float(inference.ev_by_side.get(predicted_side), 0.0) if isinstance(inference.ev_by_side, dict) else 0.0

        candidates: list[C1ReleaseCandidate] = []
        if "1x2" in allowed_fallback_plays:
            selection = _side_to_1x2_selection(predicted_side)
            if selection is not None and confidence >= min_conf and predicted_ev >= min_ev:
                candidates.append(
                    C1ReleaseCandidate(
                        play="1x2",
                        selection=selection,
                        line=None,
                        confidence=confidence,
                        status="ACTIVE",
                        rationale=["fallback_from_inference", "fallback_1x2_conf_ev_pass"],
                        evidence={
                            "predicted_side": predicted_side,
                            "predicted_ev": round(predicted_ev, 6),
                            "probabilities": dict(probs),
                        },
                        tags=["fallback", "release_fallback"],
                    )
                )

        if "handicap" in allowed_fallback_plays:
            draw_prob = _safe_float(probs.get("draw"), 0.0)
            home_prob = _safe_float(probs.get("home"), 0.0)
            away_prob = _safe_float(probs.get("away"), 0.0)
            handicap_line = _safe_float(fields.get("handicap_line"), _safe_float(fields.get("goal"), 0.0))
            side_gap = home_prob - away_prob
            min_side_gap = _safe_float(fallback_cfg.get("handicap_min_side_gap"), 0.06)
            max_draw_prob = _safe_float(fallback_cfg.get("handicap_max_draw_prob"), 0.34)
            handicap_selection: str | None = None
            if confidence >= min_conf and draw_prob <= max_draw_prob and predicted_ev >= min_ev:
                if predicted_side == "home" and side_gap >= min_side_gap:
                    handicap_selection = "HOME_HANDICAP"
                elif predicted_side == "away" and (-side_gap) >= min_side_gap:
                    handicap_selection = "AWAY_HANDICAP"
            if handicap_selection is not None:
                candidates.append(
                    C1ReleaseCandidate(
                        play="handicap",
                        selection=handicap_selection,
                        line=round(handicap_line, 3),
                        confidence=confidence,
                        status="ACTIVE",
                        rationale=["fallback_from_inference", "fallback_handicap_side_gap_pass"],
                        evidence={
                            "predicted_side": predicted_side,
                            "predicted_ev": round(predicted_ev, 6),
                            "side_gap": round(side_gap, 6),
                            "draw_probability": round(draw_prob, 6),
                            "probabilities": dict(probs),
                        },
                        tags=["fallback", "release_fallback"],
                    )
                )
        return candidates

    def decide(self, shadow_result: C1ShadowRunResult, *, created_at: str | None = None) -> C1ReleaseDecision:
        release_time = created_at or _now_text()
        governance_action = str(shadow_result.governance_decision.action)
        allowed_actions = {str(item) for item in self.config.get("allowed_governance_actions", ["APPROVE"])}
        candidate_plays = {str(item) for item in self.config.get("allowed_plays", ["1x2", "totals"])}
        min_confidence = _safe_float(self.config.get("min_confidence"), 0.0)

        candidates: list[C1ReleaseCandidate] = []
        for item in shadow_result.translation_result.items:
            if item.play not in candidate_plays:
                continue
            if item.selection in (None, ""):
                continue
            if float(item.confidence) < min_confidence:
                continue
            if str(item.status).upper() in {"BLOCKED", "SHADOW"}:
                continue
            candidates.append(
                C1ReleaseCandidate(
                    play=item.play,
                    selection=str(item.selection),
                    line=item.line,
                    confidence=float(item.confidence),
                    status=str(item.status),
                    rationale=list(item.rationale),
                    evidence=dict(item.evidence),
                    tags=list(item.tags),
                )
            )

        fallback_used = False
        if governance_action in allowed_actions and not candidates:
            fallback_candidates = self._build_fallback_candidates(
                shadow_result=shadow_result,
                min_confidence=min_confidence,
            )
            if fallback_candidates:
                candidates.extend(fallback_candidates)
                fallback_used = True

        release_allowed = governance_action in allowed_actions and bool(candidates)
        release_action = "APPROVE_RELEASE_FALLBACK" if (release_allowed and fallback_used) else ("APPROVE_RELEASE" if release_allowed else "HOLD")
        if governance_action not in allowed_actions:
            release_action = "GOVERNANCE_HOLD"
        elif not candidates:
            release_action = "NO_CANDIDATE"

        decision = C1ReleaseDecision(
            match_id=shadow_result.match_id,
            release_action=release_action,
            release_allowed=release_allowed,
            governance_action=governance_action,
            primary_reason_code=(shadow_result.governance_decision.reason_codes[0] if shadow_result.governance_decision.reason_codes else None),
            candidates=candidates,
            tags=["release", "c1", "shadow_candidate", *([] if not fallback_used else ["fallback_candidate"])],
            metadata={
                "created_at": release_time,
                "allowed_governance_actions": sorted(allowed_actions),
                "allowed_plays": sorted(candidate_plays),
                "min_confidence": min_confidence,
                "fallback_used": fallback_used,
                "translation_governance_action": shadow_result.translation_result.governance_action,
                "audit_metadata": dict(shadow_result.audit_metadata),
            },
        )
        self.audit.record_release_decision(
            match_id=shadow_result.match_id,
            feature_snapshot=shadow_result.feature_snapshot,
            prediction_snapshot=shadow_result.prediction_snapshot,
            governance_decision=shadow_result.governance_decision,
            translation_result=shadow_result.translation_result,
            release_decision=decision,
            attribution_tags=["release", "c1"],
            metadata={"run_mode": "controlled_release"},
        )
        return decision


class C1ReleaseRunner:
    def __init__(
        self,
        project_root: str | Path,
        *,
        audit_dir: str | Path | None = None,
        governance_config: dict[str, Any] | None = None,
        translation_config: dict[str, Any] | None = None,
        release_config: dict[str, Any] | None = None,
    ) -> None:
        self.shadow = C1ShadowRunner(
            project_root,
            audit_dir=audit_dir,
            governance_config=governance_config,
            translation_config=translation_config,
        )
        self.release = C1ReleaseManager(
            project_root,
            audit_dir=audit_dir,
            config=release_config,
        )

    def run_match(self, **kwargs: Any) -> tuple[C1ShadowRunResult, C1ReleaseDecision]:
        shadow_result = self.shadow.run_match(**kwargs)
        release_decision = self.release.decide(shadow_result)
        return shadow_result, release_decision
