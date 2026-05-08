from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_record(row: Mapping[str, Any]) -> dict[str, Any]:
    aliases = {
        "match_id": ("match_id", "比赛ID"),
        "source_id": ("source_id", "schedule_id", "source_match_id", "比赛源ID"),
        "match_date": ("match_date", "date", "比赛日期"),
        "league": ("league", "赛事", "联赛"),
        "home_team": ("home_team", "home", "主队"),
        "away_team": ("away_team", "away", "客队"),
        "lineup_known": ("lineup_known", "阵容已知"),
        "lineup_updated_at": ("lineup_updated_at", "阵容更新时间"),
        "lineup_freshness_hours": ("lineup_freshness_hours", "阵容时效小时"),
        "team_availability_quality": ("team_availability_quality", "可用性质量"),
        "injury_conflict_score": ("injury_conflict_score", "伤停冲突分"),
        "schedule_pressure": ("schedule_pressure", "赛程压力"),
        "weather_risk": ("weather_risk", "天气风险"),
        "environment_safe": ("environment_safe", "环境安全"),
        "home_availability_known": ("home_availability_known", "home_known", "主队可用性已知"),
        "away_availability_known": ("away_availability_known", "away_known", "客队可用性已知"),
        "home_absent_count": ("home_absent_count", "主队缺阵数"),
        "away_absent_count": ("away_absent_count", "客队缺阵数"),
        "home_key_absent_count": ("home_key_absent_count", "主队关键缺阵数"),
        "away_key_absent_count": ("away_key_absent_count", "客队关键缺阵数"),
        "home_availability_score": ("home_availability_score", "主队可用性分"),
        "away_availability_score": ("away_availability_score", "客队可用性分"),
        "provider_kind": ("provider_kind", "provider"),
    }
    normalized: dict[str, Any] = {}
    for target, candidates in aliases.items():
        for candidate in candidates:
            if candidate in row and row[candidate] not in (None, ""):
                normalized[target] = row[candidate]
                break
    return normalized


def _match_key(match_id: str) -> str:
    return f"match|{_text(match_id)}"


def _source_key(source_id: str) -> str:
    return f"source|{_text(source_id)}"


def _exact_key(match_date: str, league: str, home_team: str, away_team: str) -> str:
    return f"exact|{_text(match_date)}|{_text(league)}|{_text(home_team)}|{_text(away_team)}"


def _team_key(match_date: str, home_team: str, away_team: str) -> str:
    return f"team|{_text(match_date)}|{_text(home_team)}|{_text(away_team)}"


class C1AvailabilityStore:
    def __init__(self, project_root: str | Path, state_dir: str | Path | None = None) -> None:
        self.project_root = Path(project_root)
        self.state_dir = Path(state_dir) if state_dir is not None else (self.project_root / "data" / "c1_state")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_file = self.state_dir / "availability_snapshots.json"
        self.sync_status_file = self.state_dir / "availability_sync_status.json"
        self.source_bridge_file = self.state_dir / "source_id_bridge.json"
        self._source_bridge_cache: dict[str, str] = {}
        self._source_bridge_mtime: float | None = None

    def _load_source_bridge_map(self) -> dict[str, str]:
        try:
            mtime = self.source_bridge_file.stat().st_mtime
        except Exception:
            self._source_bridge_cache = {}
            self._source_bridge_mtime = None
            return {}
        if self._source_bridge_mtime == mtime and self._source_bridge_cache:
            return dict(self._source_bridge_cache)
        try:
            payload = json.loads(self.source_bridge_file.read_text(encoding="utf-8"))
        except Exception:
            self._source_bridge_cache = {}
            self._source_bridge_mtime = mtime
            return {}
        source_map = payload.get("source_id_map", {}) if isinstance(payload, dict) else {}
        normalized: dict[str, str] = {}
        if isinstance(source_map, dict):
            for key, value in source_map.items():
                k = _text(key)
                v = _text(value)
                if k and v:
                    normalized[k] = v
        self._source_bridge_cache = normalized
        self._source_bridge_mtime = mtime
        return dict(normalized)

    def load(self) -> dict[str, Any]:
        if not self.snapshot_file.exists():
            return {"updated_at": "", "items": {}}
        try:
            payload = json.loads(self.snapshot_file.read_text(encoding="utf-8"))
        except Exception:
            return {"updated_at": "", "items": {}}
        if not isinstance(payload, dict):
            return {"updated_at": "", "items": {}}
        items = payload.get("items")
        if not isinstance(items, dict):
            payload["items"] = {}
        return payload

    def save(self, items: dict[str, dict]) -> None:
        payload = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": items,
        }
        self.snapshot_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def save_sync_status(self, payload: Mapping[str, Any]) -> None:
        body = {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sync": dict(payload),
        }
        self.sync_status_file.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_sync_status(self) -> dict[str, Any]:
        if not self.sync_status_file.exists():
            return {}
        try:
            payload = json.loads(self.sync_status_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(payload, dict):
            return {}
        sync = payload.get("sync")
        if not isinstance(sync, dict):
            return {}
        normalized = dict(sync)
        if "updated_at" not in normalized:
            normalized["updated_at"] = _text(payload.get("updated_at"))
        return normalized

    def upsert_snapshot(self, record: Mapping[str, Any]) -> list[str]:
        normalized = _normalize_record(record)
        match_id = _text(normalized.get("match_id"))
        source_id = _text(normalized.get("source_id"))
        match_date = _text(normalized.get("match_date"))
        league = _text(normalized.get("league"))
        home_team = _text(normalized.get("home_team"))
        away_team = _text(normalized.get("away_team"))

        items = self.load().get("items", {})
        if not isinstance(items, dict):
            items = {}
        keys: list[str] = []
        if match_id:
            keys.append(_match_key(match_id))
        if source_id:
            keys.append(_source_key(source_id))
        if match_date and league and home_team and away_team:
            keys.append(_exact_key(match_date, league, home_team, away_team))
        if match_date and home_team and away_team:
            keys.append(_team_key(match_date, home_team, away_team))
        for key in keys:
            items[key] = {
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "record": dict(normalized),
            }
        self.save(items)
        return keys

    def import_rows(self, rows: Iterable[Mapping[str, Any]], *, replace: bool = False) -> dict[str, Any]:
        items: dict[str, dict] = {} if replace else dict(self.load().get("items", {}))
        imported = 0
        keyed = 0
        for row in rows:
            normalized = _normalize_record(row)
            if not normalized:
                continue
            match_id = _text(normalized.get("match_id"))
            source_id = _text(normalized.get("source_id"))
            match_date = _text(normalized.get("match_date"))
            league = _text(normalized.get("league"))
            home_team = _text(normalized.get("home_team"))
            away_team = _text(normalized.get("away_team"))
            keys: list[str] = []
            if match_id:
                keys.append(_match_key(match_id))
            if source_id:
                keys.append(_source_key(source_id))
            if match_date and league and home_team and away_team:
                keys.append(_exact_key(match_date, league, home_team, away_team))
            if match_date and home_team and away_team:
                keys.append(_team_key(match_date, home_team, away_team))
            if not keys:
                continue
            for key in keys:
                items[key] = {
                    "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "record": dict(normalized),
                }
                keyed += 1
            imported += 1
        self.save(items)
        return {"imported_rows": imported, "written_keys": keyed, "snapshot_file": str(self.snapshot_file)}

    def resolve_for_match(self, match: Any) -> dict[str, Any]:
        items = self.load().get("items", {})
        if not isinstance(items, dict):
            return {}
        if isinstance(match, Mapping):
            match_id = _text(match.get("match_id"))
            source_id = _text(match.get("source_id"))
            match_date = _text(match.get("match_date"))
            league = _text(match.get("league"))
            home_team = _text(match.get("home_team"))
            away_team = _text(match.get("away_team"))
        else:
            match_id = _text(getattr(match, "match_id", None))
            source_id = _text(getattr(match, "source_id", None))
            match_date = _text(getattr(match, "match_date", None))
            league = _text(getattr(match, "league", None))
            home_team = _text(getattr(match, "home_team", None))
            away_team = _text(getattr(match, "away_team", None))
        candidates: list[str] = []
        if match_id:
            candidates.append(_match_key(match_id))
        if source_id:
            candidates.append(_source_key(source_id))
            bridge_map = self._load_source_bridge_map()
            mapped_source = _text(bridge_map.get(source_id))
            if mapped_source:
                candidates.append(_source_key(mapped_source))
        if match_date and league and home_team and away_team:
            candidates.append(_exact_key(match_date, league, home_team, away_team))
        if match_date and home_team and away_team:
            candidates.append(_team_key(match_date, home_team, away_team))
        for key in candidates:
            payload = items.get(key)
            if isinstance(payload, dict):
                record = payload.get("record")
                if isinstance(record, dict):
                    return dict(record)
        return {}


def load_rows_from_file(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [dict(item) for item in payload if isinstance(item, Mapping)]
        if isinstance(payload, dict):
            items = payload.get("items")
            if isinstance(items, list):
                return [dict(item) for item in items if isinstance(item, Mapping)]
        return []
    if suffix == ".jsonl":
        rows: list[dict[str, Any]] = []
        for line in file_path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if isinstance(payload, Mapping):
                rows.append(dict(payload))
        return rows
    if suffix == ".csv":
        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return [dict(row) for row in reader]
    raise ValueError(f"Unsupported availability file format: {file_path}")
