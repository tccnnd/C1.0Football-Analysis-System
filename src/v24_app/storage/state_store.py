from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class StateStore:
    def __init__(self, project_dir: Path, *, xgb_sample_limit: int | None = None) -> None:
        self.state_dir = project_dir / "data" / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.xgb_sample_limit = max(1, int(xgb_sample_limit if xgb_sample_limit is not None else 100000))
        self.ratings_file = self.state_dir / "elo_ratings.json"
        self.national_team_ratings_file = self.state_dir / "national_team_elo_ratings.json"
        self.settlements_file = self.state_dir / "settlements.json"
        self.parlay_tickets_file = self.state_dir / "parlay_tickets.json"
        self.xgb_samples_file = self.state_dir / "xgb_training_samples.json"
        self.xgb_samples_summary_file = self.state_dir / "xgb_training_samples_summary.json"
        self.analysis_history_file = self.state_dir / "analysis_history.json"
        self.prediction_snapshots_file = self.state_dir / "prediction_snapshots.json"
        self.market_snapshots_file = self.state_dir / "market_snapshots.json"
        self.result_recovery_runs_file = self.state_dir / "result_recovery_runs.json"
        self.snapshot_migration_report_file = self.state_dir / "prediction_snapshot_migration.json"
        self.c1_comparison_marks_file = self.state_dir / "c1_comparison_marks.json"
        # 结算账本：仅保存已结算 match_id，作为结算幂等性的权威来源。
        # 独立于可变且会被裁剪/清空的 settlements.json，避免快照被重复结算。
        self.settled_ledger_file = self.state_dir / "settled_ledger.json"

    def load_ratings(self) -> dict[str, float]:
        return self._load_rating_file(self.ratings_file)

    def save_ratings(self, ratings: dict[str, float]) -> None:
        self._save_rating_file(self.ratings_file, ratings)

    def load_national_team_ratings(self) -> dict[str, float]:
        return self._load_rating_file(self.national_team_ratings_file)

    def save_national_team_ratings(self, ratings: dict[str, float]) -> None:
        self._save_rating_file(self.national_team_ratings_file, ratings)

    def _load_rating_file(self, path: Path) -> dict[str, float]:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        ratings = payload.get("ratings", {})
        return {str(team): float(value) for team, value in ratings.items()}

    def _save_rating_file(self, path: Path, ratings: dict[str, float]) -> None:
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ratings": ratings,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

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
        # 记录到结算账本（权威幂等来源），独立于 settlements.json 的裁剪。
        match_id = str(record.get("match_id") or "")
        if match_id:
            self.mark_settled(match_id)

    def load_settled_ledger(self) -> set[str]:
        """加载已结算 match_id 集合（结算幂等性的权威来源）。"""
        if not self.settled_ledger_file.exists():
            return set()
        try:
            payload = json.loads(self.settled_ledger_file.read_text(encoding="utf-8"))
        except Exception:
            return set()
        ids = payload.get("settled_ids", [])
        if not isinstance(ids, list):
            return set()
        return {str(value) for value in ids if value}

    def mark_settled(self, match_id: str) -> None:
        """将 match_id 标记为已结算并持久化。幂等：重复标记无副作用。"""
        match_id = str(match_id or "")
        if not match_id:
            return
        ledger = self.load_settled_ledger()
        if match_id in ledger:
            return
        ledger.add(match_id)
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "settled_ids": sorted(ledger),
        }
        self.settled_ledger_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def is_settled(self, match_id: str) -> bool:
        """查询 match_id 是否已结算（基于权威账本）。"""
        match_id = str(match_id or "")
        if not match_id:
            return False
        return match_id in self.load_settled_ledger()

    def save_settlements(self, items: list[dict], limit: int = 500) -> None:
        normalized = items[-limit:] if len(items) > limit else items
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": normalized,
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
        self.save_xgb_samples_summary(normalized, updated_at=payload["updated_at"])

    def append_xgb_sample(self, sample: dict, limit: int | None = None) -> None:
        current = self.load_xgb_samples()
        current.append(sample)
        self.save_xgb_samples(current, limit=limit)

    def _xgb_samples_signature(self) -> dict[str, int]:
        try:
            stat = self.xgb_samples_file.stat()
        except OSError:
            return {"mtime_ns": 0, "size_bytes": 0}
        return {"mtime_ns": int(stat.st_mtime_ns), "size_bytes": int(stat.st_size)}

    def _build_xgb_samples_summary(self, items: list[dict], *, updated_at: str | None = None) -> dict:
        valid_feature_count = 0
        label_counts: dict[str, int] = {}
        dates: list[str] = []
        leagues: set[str] = set()
        sources: dict[str, int] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            features = item.get("features")
            if isinstance(features, dict):
                valid_feature_count += 1
            try:
                label = str(int(item.get("label")))
                label_counts[label] = label_counts.get(label, 0) + 1
            except Exception:
                pass
            meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
            if not isinstance(meta, dict):
                continue
            date_text = str(meta.get("match_date") or "").strip()
            if date_text:
                dates.append(date_text)
            league = str(meta.get("league") or "").strip()
            if league:
                leagues.add(league)
            source = str(meta.get("source") or "").strip() or "unknown"
            sources[source] = sources.get(source, 0) + 1
        league_examples = sorted(leagues)[:12]
        source_counts = dict(sorted(sources.items(), key=lambda row: (-row[1], row[0]))[:12])
        return {
            "updated_at": updated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_file": str(self.xgb_samples_file),
            "source_signature": self._xgb_samples_signature(),
            "sample_count": len(items),
            "valid_feature_count": valid_feature_count,
            "label_counts": label_counts,
            "date_start": min(dates) if dates else None,
            "date_end": max(dates) if dates else None,
            "league_count": len(leagues),
            "league_examples": league_examples,
            "source_counts": source_counts,
        }

    def save_xgb_samples_summary(self, items: list[dict], *, updated_at: str | None = None) -> dict:
        summary = self._build_xgb_samples_summary(items, updated_at=updated_at)
        self.xgb_samples_summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary

    def load_xgb_samples_summary(self, *, rebuild_if_stale: bool = True) -> dict:
        summary: dict = {}
        if self.xgb_samples_summary_file.exists():
            try:
                payload = json.loads(self.xgb_samples_summary_file.read_text(encoding="utf-8"))
                summary = payload if isinstance(payload, dict) else {}
            except Exception:
                summary = {}
        current_signature = self._xgb_samples_signature()
        if summary.get("source_signature") == current_signature:
            return summary
        if not rebuild_if_stale:
            return summary if summary else {"source_signature": current_signature, "sample_count": 0, "valid_feature_count": 0}
        samples = self.load_xgb_samples()
        return self.save_xgb_samples_summary(samples)

    def load_analysis_history(self) -> dict[str, dict]:
        if not self.analysis_history_file.exists():
            return {}
        try:
            payload = json.loads(self.analysis_history_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
        items = payload.get("items", {})
        if not isinstance(items, dict):
            return {}
        return {
            str(match_id): record
            for match_id, record in items.items()
            if isinstance(match_id, str) and isinstance(record, dict)
        }

    def save_analysis_history(self, items: dict[str, dict]) -> None:
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": items,
        }
        self.analysis_history_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert_analysis_history(self, match_id: str, record: dict, limit: int = 5000) -> None:
        if not match_id or not isinstance(record, dict):
            return
        items = self.load_analysis_history()
        if match_id in items:
            del items[match_id]
        items[match_id] = record
        if len(items) > limit:
            overflow = len(items) - limit
            stale_keys = list(items.keys())[:overflow]
            for key in stale_keys:
                items.pop(key, None)
        self.save_analysis_history(items)

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
        existing = items.get(snapshot_id)
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
        history = list(deduped.values())[-48:]
        record = dict(record)
        record["history"] = history
        if snapshot_id in items:
            del items[snapshot_id]
        items[snapshot_id] = record
        if len(items) > limit:
            overflow = len(items) - limit
            stale_keys = list(items.keys())[:overflow]
            for key in stale_keys:
                items.pop(key, None)
        self.save_market_snapshots(items)

    def load_result_recovery_runs(self) -> list[dict]:
        if not self.result_recovery_runs_file.exists():
            return []
        try:
            payload = json.loads(self.result_recovery_runs_file.read_text(encoding="utf-8"))
        except Exception:
            return []
        items = payload.get("items", [])
        return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []

    def save_result_recovery_runs(self, items: list[dict], limit: int = 300) -> None:
        normalized = [item for item in items if isinstance(item, dict)]
        if len(normalized) > limit:
            normalized = normalized[-limit:]
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": normalized,
        }
        self.result_recovery_runs_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def upsert_result_recovery_run(self, record: dict, limit: int = 300) -> None:
        if not isinstance(record, dict):
            return
        run_id = str(record.get("run_id") or "").strip()
        if not run_id:
            return
        items = self.load_result_recovery_runs()
        next_items: list[dict] = []
        merged = False
        for item in items:
            if str(item.get("run_id") or "") == run_id:
                updated = dict(item)
                updated.update(record)
                next_items.append(updated)
                merged = True
            else:
                next_items.append(item)
        if not merged:
            next_items.append(dict(record))
        self.save_result_recovery_runs(next_items, limit=limit)

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
