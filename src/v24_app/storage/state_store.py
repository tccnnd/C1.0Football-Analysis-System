from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class StateStore:
    def __init__(self, project_dir: Path) -> None:
        self.state_dir = project_dir / "data" / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.xgb_sample_limit = 50000
        self.ratings_file = self.state_dir / "elo_ratings.json"
        self.settlements_file = self.state_dir / "settlements.json"
        self.parlay_tickets_file = self.state_dir / "parlay_tickets.json"
        self.xgb_samples_file = self.state_dir / "xgb_training_samples.json"
        self.prediction_snapshots_file = self.state_dir / "prediction_snapshots.json"
        self.market_snapshots_file = self.state_dir / "market_snapshots.json"
        self.snapshot_migration_report_file = self.state_dir / "prediction_snapshot_migration.json"
        self.c1_comparison_marks_file = self.state_dir / "c1_comparison_marks.json"

    def load_ratings(self) -> dict[str, float]:
        if not self.ratings_file.exists():
            return {}
        try:
            payload = json.loads(self.ratings_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
        ratings = payload.get("ratings", {})
        return {str(team): float(value) for team, value in ratings.items()}

    def save_ratings(self, ratings: dict[str, float]) -> None:
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ratings": ratings,
        }
        self.ratings_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_settlements(self) -> list[dict]:
        if not self.settlements_file.exists():
            return []
        try:
            payload = json.loads(self.settlements_file.read_text(encoding="utf-8"))
        except Exception:
            return []
        items = payload.get("items", [])
        return items if isinstance(items, list) else []

    def append_settlement(self, record: dict, limit: int = 500) -> None:
        current = self.load_settlements()
        current.append(record)
        if len(current) > limit:
            current = current[-limit:]
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": current,
        }
        self.settlements_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_parlay_tickets(self) -> list[dict]:
        if not self.parlay_tickets_file.exists():
            return []
        try:
            payload = json.loads(self.parlay_tickets_file.read_text(encoding="utf-8"))
        except Exception:
            return []
        items = payload.get("items", [])
        return items if isinstance(items, list) else []

    def save_parlay_tickets(self, items: list[dict], limit: int = 1000) -> None:
        normalized = items[-limit:] if len(items) > limit else items
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": normalized,
        }
        self.parlay_tickets_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_xgb_samples(self) -> list[dict]:
        if not self.xgb_samples_file.exists():
            return []
        try:
            payload = json.loads(self.xgb_samples_file.read_text(encoding="utf-8"))
        except Exception:
            return []
        items = payload.get("items", [])
        return items if isinstance(items, list) else []

    def save_xgb_samples(self, items: list[dict], limit: int | None = None) -> None:
        effective_limit = self.xgb_sample_limit if limit is None else max(1, int(limit))
        normalized = items[-effective_limit:] if len(items) > effective_limit else items
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": normalized,
        }
        self.xgb_samples_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def append_xgb_sample(self, sample: dict, limit: int | None = None) -> None:
        current = self.load_xgb_samples()
        current.append(sample)
        self.save_xgb_samples(current, limit=limit)

    def load_prediction_snapshots(self) -> dict[str, dict]:
        if not self.prediction_snapshots_file.exists():
            return {}
        try:
            payload = json.loads(self.prediction_snapshots_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
        items = payload.get("items", {})
        if not isinstance(items, dict):
            return {}
        normalized: dict[str, dict] = {}
        for match_id, record in items.items():
            if not isinstance(match_id, str) or not isinstance(record, dict):
                continue
            normalized[match_id] = record
        return normalized

    def save_prediction_snapshots(self, items: dict[str, dict]) -> None:
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": items,
        }
        self.prediction_snapshots_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert_prediction_snapshot(self, match_id: str, record: dict, limit: int = 3000) -> None:
        if not match_id or not isinstance(record, dict):
            return
        items = self.load_prediction_snapshots()
        # 先删后插，保持该键在有序字典尾部，便于超限时淘汰最旧项。
        if match_id in items:
            del items[match_id]
        items[match_id] = record
        if len(items) > limit:
            overflow = len(items) - limit
            stale_keys = list(items.keys())[:overflow]
            for key in stale_keys:
                items.pop(key, None)
        self.save_prediction_snapshots(items)

    def pop_prediction_snapshot(self, match_id: str) -> dict | None:
        if not match_id:
            return None
        items = self.load_prediction_snapshots()
        if match_id not in items:
            return None
        record = items.pop(match_id)
        self.save_prediction_snapshots(items)
        return record if isinstance(record, dict) else None

    def load_market_snapshots(self) -> dict[str, dict]:
        if not self.market_snapshots_file.exists():
            return {}
        try:
            payload = json.loads(self.market_snapshots_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
        items = payload.get("items", {})
        if not isinstance(items, dict):
            return {}
        normalized: dict[str, dict] = {}
        for snapshot_id, record in items.items():
            if isinstance(snapshot_id, str) and isinstance(record, dict):
                normalized[snapshot_id] = record
        return normalized

    def save_market_snapshots(self, items: dict[str, dict]) -> None:
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": items,
        }
        self.market_snapshots_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert_market_snapshot(self, snapshot_id: str, record: dict, limit: int = 5000) -> None:
        if not snapshot_id or not isinstance(record, dict):
            return
        items = self.load_market_snapshots()
        if snapshot_id in items:
            del items[snapshot_id]
        items[snapshot_id] = record
        if len(items) > limit:
            overflow = len(items) - limit
            stale_keys = list(items.keys())[:overflow]
            for key in stale_keys:
                items.pop(key, None)
        self.save_market_snapshots(items)

    def load_snapshot_migration_report(self) -> dict:
        if not self.snapshot_migration_report_file.exists():
            return {}
        try:
            payload = json.loads(self.snapshot_migration_report_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    def save_snapshot_migration_report(self, report: dict) -> None:
        if not isinstance(report, dict):
            return
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **report,
        }
        self.snapshot_migration_report_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_c1_comparison_marks(self) -> dict[str, dict]:
        if not self.c1_comparison_marks_file.exists():
            return {}
        try:
            payload = json.loads(self.c1_comparison_marks_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
        items = payload.get("items", {})
        if not isinstance(items, dict):
            return {}
        normalized: dict[str, dict] = {}
        for match_id, record in items.items():
            if not isinstance(match_id, str) or not isinstance(record, dict):
                continue
            normalized[match_id] = record
        return normalized

    def save_c1_comparison_marks(self, items: dict[str, dict], limit: int = 3000) -> None:
        normalized: dict[str, dict] = {}
        for match_id, record in items.items():
            if not isinstance(match_id, str) or not isinstance(record, dict):
                continue
            normalized[match_id] = record
        if len(normalized) > limit:
            overflow = len(normalized) - limit
            stale_keys = list(normalized.keys())[:overflow]
            for key in stale_keys:
                normalized.pop(key, None)
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": normalized,
        }
        self.c1_comparison_marks_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
