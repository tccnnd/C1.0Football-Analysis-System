from __future__ import annotations

import json
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from c1.core.schema import FeatureSnapshot, GovernanceDecision, PredictionSnapshot

if TYPE_CHECKING:
    from c1.translation.schema import TranslationResult


class C1AuditStore:
    def __init__(self, project_root: str | Path, audit_dir: str | Path | None = None) -> None:
        self.project_root = Path(project_root)
        self.audit_dir = Path(audit_dir) if audit_dir is not None else (self.project_root / "data" / "c1_audit")
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.feature_vectors_file = self.audit_dir / "feature_vectors.jsonl"
        self.predictions_file = self.audit_dir / "predictions.jsonl"
        self.governance_decisions_file = self.audit_dir / "governance_decisions.jsonl"
        self.translation_outputs_file = self.audit_dir / "translation_outputs.jsonl"
        self.release_decisions_file = self.audit_dir / "release_decisions.jsonl"
        self.market_snapshots_file = self.audit_dir / "market_snapshots.jsonl"

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _normalize(self, value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if is_dataclass(value):
            return self._normalize(asdict(value))
        if isinstance(value, dict):
            return {str(key): self._normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._normalize(item) for item in value]
        if isinstance(value, tuple):
            return [self._normalize(item) for item in value]
        return value

    def _append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _read_jsonl(self, path: Path, limit: int | None = None) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        items: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                try:
                    payload = json.loads(text)
                except Exception:
                    continue
                if isinstance(payload, dict):
                    items.append(payload)
        if limit is not None and limit > 0:
            return items[-limit:]
        return items

    def record_feature_vector(
        self,
        *,
        snapshot: FeatureSnapshot,
        attribution_tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "record_id": str(uuid.uuid4()),
            "record_type": "feature_vector",
            "recorded_at": self._now(),
            "match_id": snapshot.match_id,
            "attribution_tags": attribution_tags or [],
            "metadata": metadata or {},
            "feature_snapshot": self._normalize(snapshot),
        }
        self._append_jsonl(self.feature_vectors_file, record)
        return record

    def record_prediction(
        self,
        *,
        match_id: str,
        feature_snapshot: FeatureSnapshot,
        prediction_snapshot: PredictionSnapshot,
        attribution_tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "record_id": str(uuid.uuid4()),
            "record_type": "prediction",
            "recorded_at": self._now(),
            "match_id": match_id,
            "attribution_tags": attribution_tags or [],
            "metadata": metadata or {},
            "feature_snapshot": self._normalize(feature_snapshot),
            "prediction_snapshot": self._normalize(prediction_snapshot),
        }
        self._append_jsonl(self.predictions_file, record)
        return record

    def record_governance_decision(
        self,
        *,
        match_id: str,
        feature_snapshot: FeatureSnapshot,
        prediction_snapshot: PredictionSnapshot,
        governance_decision: GovernanceDecision,
        attribution_tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "record_id": str(uuid.uuid4()),
            "record_type": "governance_decision",
            "recorded_at": self._now(),
            "match_id": match_id,
            "attribution_tags": attribution_tags or [],
            "metadata": metadata or {},
            "feature_snapshot": self._normalize(feature_snapshot),
            "prediction_snapshot": self._normalize(prediction_snapshot),
            "governance_decision": self._normalize(governance_decision),
        }
        self._append_jsonl(self.governance_decisions_file, record)
        return record

    def read_feature_vectors(self, limit: int | None = None) -> list[dict[str, Any]]:
        return self._read_jsonl(self.feature_vectors_file, limit=limit)

    def read_predictions(self, limit: int | None = None) -> list[dict[str, Any]]:
        return self._read_jsonl(self.predictions_file, limit=limit)

    def read_governance_decisions(self, limit: int | None = None) -> list[dict[str, Any]]:
        return self._read_jsonl(self.governance_decisions_file, limit=limit)

    def record_translation_output(
        self,
        *,
        match_id: str,
        feature_snapshot: FeatureSnapshot,
        prediction_snapshot: PredictionSnapshot,
        governance_decision: GovernanceDecision,
        translation_result: "TranslationResult",
        attribution_tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "record_id": str(uuid.uuid4()),
            "record_type": "translation_output",
            "recorded_at": self._now(),
            "match_id": match_id,
            "attribution_tags": attribution_tags or [],
            "metadata": metadata or {},
            "feature_snapshot": self._normalize(feature_snapshot),
            "prediction_snapshot": self._normalize(prediction_snapshot),
            "governance_decision": self._normalize(governance_decision),
            "translation_result": self._normalize(translation_result),
        }
        self._append_jsonl(self.translation_outputs_file, record)
        return record

    def read_translation_outputs(self, limit: int | None = None) -> list[dict[str, Any]]:
        return self._read_jsonl(self.translation_outputs_file, limit=limit)

    def record_release_decision(
        self,
        *,
        match_id: str,
        feature_snapshot: FeatureSnapshot,
        prediction_snapshot: PredictionSnapshot,
        governance_decision: GovernanceDecision,
        translation_result: "TranslationResult",
        release_decision: Any,
        attribution_tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "record_id": str(uuid.uuid4()),
            "record_type": "release_decision",
            "recorded_at": self._now(),
            "match_id": match_id,
            "attribution_tags": attribution_tags or [],
            "metadata": metadata or {},
            "feature_snapshot": self._normalize(feature_snapshot),
            "prediction_snapshot": self._normalize(prediction_snapshot),
            "governance_decision": self._normalize(governance_decision),
            "translation_result": self._normalize(translation_result),
            "release_decision": self._normalize(release_decision),
        }
        self._append_jsonl(self.release_decisions_file, record)
        return record

    def read_release_decisions(self, limit: int | None = None) -> list[dict[str, Any]]:
        return self._read_jsonl(self.release_decisions_file, limit=limit)

    def record_market_snapshot(
        self,
        *,
        match_id: str,
        phase: str,
        snapshot: dict[str, Any],
        attribution_tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "record_id": str(uuid.uuid4()),
            "record_type": "market_snapshot",
            "recorded_at": self._now(),
            "match_id": match_id,
            "phase": str(phase),
            "attribution_tags": attribution_tags or [],
            "metadata": metadata or {},
            "snapshot": self._normalize(snapshot),
        }
        self._append_jsonl(self.market_snapshots_file, record)
        return record

    def read_market_snapshots(self, limit: int | None = None) -> list[dict[str, Any]]:
        return self._read_jsonl(self.market_snapshots_file, limit=limit)
