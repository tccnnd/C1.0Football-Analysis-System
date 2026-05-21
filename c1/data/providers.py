from __future__ import annotations

import csv
import io
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit
from urllib.request import Request, urlopen

import yaml
from bs4 import BeautifulSoup

from .availability_store import C1AvailabilityStore, load_rows_from_file
from .provider_normalizers import normalize_provider_rows


DEFAULT_PROVIDER_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "availability_sources.yaml"


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _availability_quality_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row_count = len(rows)
    if row_count <= 0:
        return {
            "quality_gate": "fail",
            "quality_score": 0.0,
            "row_count": 0,
            "keyable_rate": 0.0,
            "availability_known_rate": 0.0,
            "avg_team_availability_quality": 0.0,
            "quality_issues": ["no_rows"],
        }
    keyable = 0
    known = 0
    quality_values: list[float] = []
    freshness_known = 0
    provider_kinds: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        match_id = _text(row.get("match_id"))
        source_id = _text(row.get("source_id"))
        match_date = _text(row.get("match_date"))
        league = _text(row.get("league"))
        home_team = _text(row.get("home_team"))
        away_team = _text(row.get("away_team"))
        if match_id or source_id or (match_date and home_team and away_team) or (match_date and league and home_team and away_team):
            keyable += 1
        if _safe_bool(row.get("lineup_known")) or _safe_bool(row.get("home_availability_known")) or _safe_bool(row.get("away_availability_known")):
            known += 1
        if row.get("team_availability_quality") not in (None, ""):
            quality_values.append(_safe_float(row.get("team_availability_quality")))
        if _text(row.get("lineup_updated_at")):
            freshness_known += 1
        provider_kind = _text(row.get("provider_kind"))
        if provider_kind:
            provider_kinds.add(provider_kind)
    keyable_rate = keyable / row_count
    known_rate = known / row_count
    avg_quality = sum(quality_values) / len(quality_values) if quality_values else 0.0
    freshness_rate = freshness_known / row_count
    issues: list[str] = []
    if keyable_rate < 0.95:
        issues.append("key_completeness_low")
    if known_rate < 0.25:
        issues.append("availability_known_low")
    if quality_values and avg_quality < 0.35:
        issues.append("availability_quality_low")
    if freshness_rate < 0.25:
        issues.append("freshness_missing")
    score = round(keyable_rate * 0.45 + known_rate * 0.30 + _clip(avg_quality) * 0.20 + freshness_rate * 0.05, 4)
    gate = "pass"
    if keyable_rate < 0.75:
        gate = "fail"
    elif issues:
        gate = "warn"
    return {
        "quality_gate": gate,
        "quality_score": score,
        "row_count": row_count,
        "keyable_rows": keyable,
        "keyable_rate": round(keyable_rate, 4),
        "availability_known_rows": known,
        "availability_known_rate": round(known_rate, 4),
        "avg_team_availability_quality": round(avg_quality, 4),
        "freshness_known_rate": round(freshness_rate, 4),
        "provider_kinds": sorted(provider_kinds),
        "quality_issues": issues,
    }


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _retry_delay_ms(base_delay_ms: int, attempt_index: int, max_delay_ms: int) -> int:
    base = max(0, int(base_delay_ms))
    if base <= 0:
        return 0
    step = max(0, int(attempt_index))
    delay = base * (2**step)
    return max(0, min(int(max_delay_ms), int(delay)))


def _provider_signal_issues(item: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []

    def _append(value: str) -> None:
        text = _text(value)
        if text and text not in issues:
            issues.append(text)

    attempt_errors = item.get("attempt_errors")
    if isinstance(attempt_errors, list):
        for value in attempt_errors:
            text = _text(value)
            if text:
                _append(f"attempt_error:{text}")

    fixtures_errors = item.get("fixtures_errors")
    if isinstance(fixtures_errors, list):
        for value in fixtures_errors:
            text = _text(value)
            if text:
                _append(f"fixtures_error:{text}")

    detail_errors = item.get("detail_errors")
    if isinstance(detail_errors, list):
        for value in detail_errors:
            text = _text(value)
            if text:
                _append(f"detail_error:{text}")

    if _safe_bool(item.get("fixtures_upstream_error")):
        _append("fixtures_upstream_error")
    if _safe_bool(item.get("fixtures_account_suspended")):
        _append("fixtures_account_suspended")
    if _safe_bool(item.get("recovered_after_retry")):
        _append("recovered_after_retry")
    if _safe_bool(item.get("retry_exhausted")):
        _append("retry_exhausted")

    detail_error_count = _safe_int(item.get("detail_error_count"), 0)
    if detail_error_count > 0:
        _append(f"detail_error_count={detail_error_count}")

    return issues


def _provider_failure_reason(item: Mapping[str, Any]) -> dict[str, Any] | None:
    status = _text(item.get("status")).lower()
    quality_gate = _text(item.get("quality_gate")).lower()
    signal_issues = _provider_signal_issues(item)

    severity = ""
    code = ""
    if status == "error":
        severity = "error"
        code = _text(item.get("reason")) or "provider_error"
    elif quality_gate == "fail":
        severity = "error"
        code = "quality_gate_failed"
    elif _safe_bool(item.get("retry_exhausted")) or _safe_bool(item.get("fixtures_account_suspended")):
        severity = "error"
        code = "provider_retry_exhausted"
    elif quality_gate == "warn" or signal_issues:
        severity = "warning"
        code = "quality_gate_warning" if quality_gate == "warn" else "provider_warning"

    if not severity:
        return None

    provider_name = _text(item.get("provider_name")) or "-"
    reason = _text(item.get("reason"))
    error = _text(item.get("error"))
    message_parts: list[str] = []
    if reason:
        message_parts.append(reason)
    if error and error not in message_parts:
        message_parts.append(error)
    quality_issues = item.get("quality_issues")
    if isinstance(quality_issues, list) and quality_issues:
        message_parts.append("quality=" + ",".join(_text(issue) for issue in quality_issues if _text(issue)))
    if signal_issues:
        message_parts.append("signals=" + ",".join(signal_issues))
    attempt_count = _safe_int(item.get("attempt_count"), 0)
    retry_count = _safe_int(item.get("retry_count"), 0)
    if attempt_count > 0 or retry_count > 0:
        message_parts.append(f"attempts={attempt_count} retries={retry_count}")

    recommendation = "Keep release review blocked until the provider is healthy."
    if severity == "warning":
        recommendation = "Monitor the provider and re-run sync before release review."
    if code == "quality_gate_failed":
        recommendation = "Repair the imported rows or loosen the gate only after validating coverage loss."
    elif code == "provider_retry_exhausted":
        recommendation = "Retry later with backoff or switch to a fallback source."

    return {
        "provider_name": provider_name,
        "severity": severity,
        "code": code,
        "status": status or "-",
        "quality_gate": quality_gate or "-",
        "reason": reason or "-",
        "error": error or "-",
        "message": " | ".join(message_parts) if message_parts else provider_name,
        "recommendation": recommendation,
        "attempt_count": attempt_count,
        "retry_count": retry_count,
        "attempt_errors": [str(value) for value in (item.get("attempt_errors") if isinstance(item.get("attempt_errors"), list) else []) if str(value).strip()],
        "quality_issues": [str(value) for value in (quality_issues if isinstance(quality_issues, list) else []) if str(value).strip()],
        "signal_issues": signal_issues,
    }


def _render_url_template(url: str) -> str:
    text = str(url or "").strip()
    if not text:
        return text
    today = datetime.now().strftime("%Y-%m-%d")
    return text.replace("{today}", today)


def load_availability_provider_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path is not None else DEFAULT_PROVIDER_CONFIG_PATH
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid availability provider config: {config_path}")
    return payload


def _load_rows_from_text(
    payload_text: str,
    *,
    source_format: str,
    items_key: str | None = None,
    provider_kind: str = "generic",
) -> list[dict[str, Any]]:
    normalized_format = source_format.lower().strip()
    if normalized_format == "json":
        payload = json.loads(payload_text)
        if isinstance(payload, list):
            return normalize_provider_rows(provider_kind, payload)
        if isinstance(payload, dict):
            if items_key:
                payload = payload.get(items_key)
                if isinstance(payload, list):
                    return normalize_provider_rows(provider_kind, payload)
            items = payload.get("items")
            if isinstance(items, list):
                return normalize_provider_rows(provider_kind, items)
            if provider_kind == "sportmonks":
                items = payload.get("data")
                if isinstance(items, list):
                    return normalize_provider_rows(provider_kind, items)
            if provider_kind == "api_football":
                items = payload.get("response")
                if isinstance(items, list):
                    return normalize_provider_rows(provider_kind, items)
        return []
    if normalized_format == "jsonl":
        rows: list[dict[str, Any]] = []
        for line in payload_text.splitlines():
            text = line.strip()
            if not text:
                continue
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                rows.append(dict(parsed))
        return rows
    if normalized_format == "csv":
        handle = io.StringIO(payload_text)
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]
    raise ValueError(f"Unsupported provider payload format: {source_format}")


@dataclass(slots=True)
class AvailabilityProviderResult:
    provider_name: str
    record: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class AvailabilityProvider:
    provider_name = "base"
    resolve_enabled = True
    sync_enabled = True

    def load_rows(self) -> list[dict[str, Any]]:
        return []

    def resolve_for_match(self, match: Any) -> AvailabilityProviderResult:
        raise NotImplementedError

    def status(self) -> dict[str, Any]:
        return {"provider_name": self.provider_name, "resolve_enabled": self.resolve_enabled}

    def sync_report(self) -> dict[str, Any]:
        return {}

    def _resolve_from_rows(self, rows: list[dict[str, Any]], match: Any, *, metadata: dict[str, Any]) -> AvailabilityProviderResult:
        if not rows:
            return AvailabilityProviderResult(provider_name=self.provider_name, record={}, metadata=metadata)
        temp_root = Path.cwd() / ".c1_provider_cache"
        temp_store = C1AvailabilityStore(temp_root, state_dir=temp_root / self.provider_name)
        temp_store.import_rows(rows, replace=True)
        record = temp_store.resolve_for_match(match)
        return AvailabilityProviderResult(
            provider_name=self.provider_name,
            record=record,
            metadata=metadata,
        )


class StoredAvailabilityProvider(AvailabilityProvider):
    provider_name = "stored_snapshots"
    sync_enabled = False

    def __init__(self, project_root: str | Path) -> None:
        self.store = C1AvailabilityStore(project_root)

    def resolve_for_match(self, match: Any) -> AvailabilityProviderResult:
        record = self.store.resolve_for_match(match)
        return AvailabilityProviderResult(
            provider_name=self.provider_name,
            record=record,
            metadata={"snapshot_file": str(self.store.snapshot_file)},
        )

    def status(self) -> dict[str, Any]:
        payload = self.store.load()
        items = payload.get("items", {})
        return {
            "provider_name": self.provider_name,
            "status": "ready",
            "items": len(items) if isinstance(items, dict) else 0,
            "snapshot_file": str(self.store.snapshot_file),
        }


class FileAvailabilityProvider(AvailabilityProvider):
    provider_name = "file_source"

    def __init__(self, *, source_path: str | Path, provider_name: str | None = None) -> None:
        self.source_path = Path(source_path)
        if provider_name:
            self.provider_name = provider_name

    def load_rows(self) -> list[dict[str, Any]]:
        if not self.source_path.exists():
            return []
        return load_rows_from_file(self.source_path)

    def resolve_for_match(self, match: Any) -> AvailabilityProviderResult:
        if not self.source_path.exists():
            return AvailabilityProviderResult(
                provider_name=self.provider_name,
                record={},
                metadata={"status": "missing", "source_path": str(self.source_path)},
            )
        rows = self.load_rows()
        return self._resolve_from_rows(
            rows,
            match,
            metadata={"status": "loaded", "source_path": str(self.source_path), "rows": len(rows)},
        )

    def status(self) -> dict[str, Any]:
        exists = self.source_path.exists()
        return {
            "provider_name": self.provider_name,
            "status": "ready" if exists else "missing",
            "source_path": str(self.source_path),
            "rows": len(self.load_rows()) if exists else 0,
        }


class HttpAvailabilityProvider(AvailabilityProvider):
    provider_name = "http_source"

    def __init__(
        self,
        *,
        url: str,
        provider_name: str | None = None,
        source_format: str = "json",
        items_key: str | None = None,
        timeout_seconds: int = 15,
        provider_kind: str = "generic",
        resolve_direct: bool = True,
        headers: Mapping[str, Any] | None = None,
    ) -> None:
        self.url = str(url)
        self.source_format = source_format
        self.items_key = items_key
        self.timeout_seconds = max(3, timeout_seconds)
        self.provider_kind = _text(provider_kind).lower() or "generic"
        self.resolve_enabled = bool(resolve_direct)
        self.headers = {str(key): str(value) for key, value in dict(headers or {}).items()}
        if provider_name:
            self.provider_name = provider_name

    def load_rows(self) -> list[dict[str, Any]]:
        request = Request(_render_url_template(self.url), headers=self.headers)
        with urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
        text = raw.decode(charset, errors="replace")
        return _load_rows_from_text(
            text,
            source_format=self.source_format,
            items_key=self.items_key,
            provider_kind=self.provider_kind,
        )

    def resolve_for_match(self, match: Any) -> AvailabilityProviderResult:
        try:
            rows = self.load_rows()
        except Exception as exc:
            return AvailabilityProviderResult(
                provider_name=self.provider_name,
                record={},
                metadata={"status": "error", "url": self.url, "error": str(exc)},
            )
        return self._resolve_from_rows(
            rows,
            match,
            metadata={
                "status": "loaded",
                "url": self.url,
                "rows": len(rows),
                "format": self.source_format,
                "provider_kind": self.provider_kind,
            },
        )

    def status(self) -> dict[str, Any]:
        parsed = urlparse(self.url)
        try:
            rows = self.load_rows()
            return {
                "provider_name": self.provider_name,
                "status": "ready",
                "url": self.url,
                "host": parsed.netloc,
                "rows": len(rows),
                "format": self.source_format,
                "provider_kind": self.provider_kind,
                "resolve_enabled": self.resolve_enabled,
            }
        except Exception as exc:
            return {
                "provider_name": self.provider_name,
                "status": "error",
                "url": self.url,
                "host": parsed.netloc,
                "format": self.source_format,
                "provider_kind": self.provider_kind,
                "resolve_enabled": self.resolve_enabled,
                "error": str(exc),
            }


class ApiFootballAvailabilityProvider(AvailabilityProvider):
    provider_name = "api_football_source"

    def __init__(
        self,
        *,
        fixtures_url: str,
        provider_name: str | None = None,
        lineups_url_template: str | None = None,
        injuries_url_template: str | None = None,
        timeout_seconds: int = 15,
        resolve_direct: bool = False,
        headers: Mapping[str, Any] | None = None,
        max_fixtures: int = 60,
        request_delay_ms: int = 0,
    ) -> None:
        self.fixtures_url = str(fixtures_url)
        self.lineups_url_template = str(lineups_url_template or "https://v3.football.api-sports.io/fixtures/lineups?fixture={fixture_id}")
        self.injuries_url_template = str(injuries_url_template or "https://v3.football.api-sports.io/injuries?fixture={fixture_id}")
        self.timeout_seconds = max(3, timeout_seconds)
        self.resolve_enabled = bool(resolve_direct)
        self.headers = {str(key): str(value) for key, value in dict(headers or {}).items()}
        self.max_fixtures = max(0, min(int(max_fixtures), 500))
        self.request_delay_ms = max(0, int(request_delay_ms))
        self._last_load_meta: dict[str, Any] = {}
        if provider_name:
            self.provider_name = provider_name

    def _fetch_json(self, url: str) -> Any:
        request = Request(_render_url_template(url), headers=self.headers)
        with urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
        text = raw.decode(charset, errors="replace")
        return json.loads(text)

    def _build_fixtures_url_for_date(self, date_text: str) -> str:
        base = str(self.fixtures_url or "").strip()
        if not base:
            return base
        if "{today}" in base:
            return base.replace("{today}", date_text)
        if "{date}" in base:
            return base.replace("{date}", date_text)

        rendered = _render_url_template(base)
        parts = urlsplit(rendered)
        query_pairs = parse_qsl(parts.query, keep_blank_values=True)
        has_date = False
        patched_pairs: list[tuple[str, str]] = []
        for key, value in query_pairs:
            if key.lower() == "date":
                patched_pairs.append((key, date_text))
                has_date = True
            else:
                patched_pairs.append((key, value))
        if not has_date:
            patched_pairs.append(("date", date_text))
        query = urlencode(patched_pairs, doseq=True)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))

    @staticmethod
    def _flatten_payload_errors(payload: Any) -> list[str]:
        if not isinstance(payload, Mapping):
            return []
        errors = payload.get("errors")
        if not errors:
            return []
        result: list[str] = []
        if isinstance(errors, Mapping):
            for key, value in errors.items():
                left = _text(key)
                right = _text(value)
                if left and right:
                    result.append(f"{left}: {right}")
                elif left:
                    result.append(left)
                elif right:
                    result.append(right)
            return result
        if isinstance(errors, list):
            for item in errors:
                if isinstance(item, Mapping):
                    left = _text(item.get("code") or item.get("field") or item.get("type"))
                    right = _text(item.get("message") or item.get("detail") or item.get("reason"))
                    if left and right:
                        result.append(f"{left}: {right}")
                    elif left:
                        result.append(left)
                    elif right:
                        result.append(right)
                else:
                    text = _text(item)
                    if text:
                        result.append(text)
            return result
        text = _text(errors)
        return [text] if text else []

    @staticmethod
    def _payload_results(payload: Any, response_count: int) -> int:
        if isinstance(payload, Mapping):
            return _safe_int(payload.get("results"), response_count)
        return int(response_count)

    def _issue_window_dates(self) -> list[str]:
        issue_start, issue_end = self._issue_window(datetime.now())
        dates: list[str] = []
        cursor = issue_start.date()
        end_date = issue_end.date()
        while cursor <= end_date:
            dates.append(cursor.strftime("%Y-%m-%d"))
            cursor += timedelta(days=1)
        if not dates:
            dates.append(datetime.now().strftime("%Y-%m-%d"))
        deduped: list[str] = []
        seen: set[str] = set()
        for value in dates:
            if value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        return deduped

    def _fetch_fixtures(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        date_queries = self._issue_window_dates()
        merged: dict[str, dict[str, Any]] = {}
        query_reports: list[dict[str, Any]] = []
        combined_errors: list[str] = []
        fetched_any = False
        failed_all = True
        total_api_results = 0
        total_response_items = 0

        for date_text in date_queries:
            fixtures_url = self._build_fixtures_url_for_date(date_text)
            try:
                payload = self._fetch_json(fixtures_url)
                fetched_any = True
                failed_all = False
            except Exception as exc:
                error_text = str(exc)
                combined_errors.append(f"{date_text}: {error_text}")
                query_reports.append(
                    {
                        "date": date_text,
                        "url": fixtures_url,
                        "status": "error",
                        "results": 0,
                        "response_items": 0,
                        "errors": [error_text],
                    }
                )
                continue

            fixture_items = self._response_items(payload)
            response_items = len(fixture_items)
            api_results = self._payload_results(payload, response_items)
            api_errors = self._flatten_payload_errors(payload)
            if api_errors:
                combined_errors.extend(f"{date_text}: {msg}" for msg in api_errors)
            query_reports.append(
                {
                    "date": date_text,
                    "url": fixtures_url,
                    "status": "ok",
                    "results": int(api_results),
                    "response_items": int(response_items),
                    "errors": list(api_errors),
                }
            )
            total_api_results += int(api_results)
            total_response_items += int(response_items)
            for item in fixture_items:
                fixture = item.get("fixture") if isinstance(item.get("fixture"), Mapping) else {}
                fixture_id = _text((fixture or {}).get("id"))
                if fixture_id:
                    merged[fixture_id] = dict(item)
                    continue
                fallback_key = f"{date_text}:{len(merged)}"
                merged[fallback_key] = dict(item)

        if failed_all and date_queries:
            error_preview = "; ".join(combined_errors[:3]) if combined_errors else "unknown"
            raise RuntimeError(f"fixtures_fetch_failed_all_dates: {error_preview}")

        meta = {
            "fixtures_date_queries": list(date_queries),
            "fixtures_query_count": int(len(date_queries)),
            "fixtures_query_reports": query_reports,
            "fixtures_results_total": int(total_api_results),
            "fixtures_response_total": int(total_response_items),
            "fixtures_errors": list(combined_errors),
            "fixtures_upstream_error": bool(combined_errors),
            "fixtures_account_suspended": any("suspended" in str(item).lower() for item in combined_errors),
            "fixtures_fetch_ok": bool(fetched_any),
        }
        return list(merged.values()), meta

    @staticmethod
    def _response_items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict):
            response = payload.get("response")
            if isinstance(response, list):
                return [dict(item) for item in response if isinstance(item, Mapping)]
        if isinstance(payload, list):
            return [dict(item) for item in payload if isinstance(item, Mapping)]
        return []

    @staticmethod
    def _fixture_team_map(fixture_item: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        teams = fixture_item.get("teams") if isinstance(fixture_item.get("teams"), Mapping) else {}
        mapped: dict[str, dict[str, Any]] = {}
        for side in ("home", "away"):
            team = teams.get(side) if isinstance(teams, Mapping) else None
            if isinstance(team, Mapping):
                mapped[side] = dict(team)
        return mapped

    @staticmethod
    def _team_id(team: Mapping[str, Any] | None) -> str:
        if not isinstance(team, Mapping):
            return ""
        return _text(team.get("id"))

    def _fixture_side(self, fixture_item: Mapping[str, Any], team: Mapping[str, Any]) -> str:
        mapped = self._fixture_team_map(fixture_item)
        team_id = self._team_id(team)
        if team_id:
            for side in ("home", "away"):
                if self._team_id(mapped.get(side)) == team_id:
                    return side
        team_name = _text(team.get("name")).lower()
        if team_name:
            for side in ("home", "away"):
                if _text((mapped.get(side) or {}).get("name")).lower() == team_name:
                    return side
        return ""

    @staticmethod
    def _injury_team_id(item: Mapping[str, Any]) -> str:
        if isinstance(item.get("team"), Mapping):
            return _text((item.get("team") or {}).get("id"))
        return _text(item.get("team_id"))

    def _collect_injuries_by_team(self, injury_items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in injury_items:
            team_id = self._injury_team_id(item)
            if not team_id:
                continue
            grouped.setdefault(team_id, []).append(dict(item))
        return grouped

    @staticmethod
    def _parse_fixture_datetime(value: Any) -> datetime | None:
        text = _text(value)
        if not text:
            return None
        iso = text.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(iso)
        except Exception:
            return None
        if dt.tzinfo is not None:
            try:
                return dt.astimezone().replace(tzinfo=None)
            except Exception:
                return dt.replace(tzinfo=None)
        return dt

    @staticmethod
    def _issue_window(now: datetime) -> tuple[datetime, datetime]:
        start = now.replace(hour=11, minute=0, second=0, microsecond=0)
        if now < start:
            start -= timedelta(days=1)
        return start, start + timedelta(days=1)

    def _effective_fixture_limit(self, fixtures: list[dict[str, Any]]) -> tuple[int, int]:
        total = len(fixtures)
        if total <= 0:
            return 0, 0
        now = datetime.now()
        issue_start, issue_end = self._issue_window(now)
        rolling_end = now + timedelta(days=1)
        issue_count = 0
        for item in fixtures:
            fixture = item.get("fixture") if isinstance(item.get("fixture"), Mapping) else {}
            dt = self._parse_fixture_datetime((fixture or {}).get("date"))
            if dt is None:
                continue
            if issue_start <= dt < issue_end or now <= dt < rolling_end:
                issue_count += 1
        base_limit = self.max_fixtures if self.max_fixtures > 0 else total
        dynamic_target = issue_count + 40 if issue_count > 0 else base_limit
        effective_limit = min(total, max(base_limit, dynamic_target))
        return effective_limit, issue_count

    def load_rows(self) -> list[dict[str, Any]]:
        try:
            fixtures, fixtures_meta = self._fetch_fixtures()
        except Exception as exc:
            self._last_load_meta = {
                "fixture_total": 0,
                "fixture_issue_count": 0,
                "fixture_limit": 0,
                "lineups_calls": 0,
                "injuries_calls": 0,
                "fixtures_errors": [str(exc)],
            }
            raise
        if not fixtures:
            self._last_load_meta = {
                "fixture_total": 0,
                "fixture_issue_count": 0,
                "fixture_limit": 0,
                "lineups_calls": 0,
                "injuries_calls": 0,
                **fixtures_meta,
            }
            return []

        effective_limit, issue_count = self._effective_fixture_limit(fixtures)
        rows_payload: list[dict[str, Any]] = []
        lineups_calls = 0
        injuries_calls = 0
        for fixture_item in fixtures[:effective_limit]:
            fixture = fixture_item.get("fixture") if isinstance(fixture_item.get("fixture"), Mapping) else {}
            league = fixture_item.get("league") if isinstance(fixture_item.get("league"), Mapping) else {}
            fixture_id = _text((fixture or {}).get("id"))
            if not fixture_id:
                continue

            lineups: list[dict[str, Any]] = []
            injuries: list[dict[str, Any]] = []

            try:
                lineups_payload = self._fetch_json(self.lineups_url_template.format(fixture_id=fixture_id))
                lineups = self._response_items(lineups_payload)
                lineups_calls += 1
            except Exception:
                lineups = []
            if self.request_delay_ms > 0:
                time.sleep(self.request_delay_ms / 1000.0)

            try:
                injuries_payload = self._fetch_json(self.injuries_url_template.format(fixture_id=fixture_id))
                injuries = self._response_items(injuries_payload)
                injuries_calls += 1
            except Exception:
                injuries = []
            if self.request_delay_ms > 0:
                time.sleep(self.request_delay_ms / 1000.0)

            injuries_by_team = self._collect_injuries_by_team(injuries)
            fixture_teams = self._fixture_team_map(fixture_item)
            side_map: dict[str, dict[str, Any]] = {}
            for lineup in lineups:
                team = lineup.get("team") if isinstance(lineup.get("team"), Mapping) else {}
                side = self._fixture_side(fixture_item, team if isinstance(team, Mapping) else {})
                if side not in {"home", "away"}:
                    continue
                side_map[side] = dict(lineup)

            for side in ("home", "away"):
                team = fixture_teams.get(side, {})
                lineup_item = side_map.get(side, {})
                team_id = self._team_id(team)
                missing_players = injuries_by_team.get(team_id, [])
                rows_payload.append(
                    {
                        "fixture": dict(fixture),
                        "league": dict(league),
                        "team": dict(lineup_item.get("team") if isinstance(lineup_item.get("team"), Mapping) else team),
                        "teams": dict(fixture_item.get("teams") if isinstance(fixture_item.get("teams"), Mapping) else {}),
                        "startXI": lineup_item.get("startXI") if isinstance(lineup_item.get("startXI"), list) else [],
                        "formation": lineup_item.get("formation"),
                        "missing_players": [dict(item) for item in missing_players],
                        "injuries": [dict(item) for item in missing_players],
                        "update": lineup_item.get("update") or fixture.get("date"),
                        "meta": {"location": side},
                    }
                )
        self._last_load_meta = {
            "fixture_total": len(fixtures),
            "fixture_issue_count": int(issue_count),
            "fixture_limit": int(effective_limit),
            "lineups_calls": int(lineups_calls),
            "injuries_calls": int(injuries_calls),
            **fixtures_meta,
        }
        return normalize_provider_rows("api_football", rows_payload)

    def resolve_for_match(self, match: Any) -> AvailabilityProviderResult:
        try:
            rows = self.load_rows()
        except Exception as exc:
            return AvailabilityProviderResult(
                provider_name=self.provider_name,
                record={},
                metadata={"status": "error", "url": self.fixtures_url, "error": str(exc)},
            )
        return self._resolve_from_rows(
            rows,
            match,
            metadata={
                "status": "loaded",
                "url": self.fixtures_url,
                "rows": len(rows),
                "provider_kind": "api_football",
                "lineups_url_template": self.lineups_url_template,
                "injuries_url_template": self.injuries_url_template,
            },
        )

    def status(self) -> dict[str, Any]:
        parsed = urlparse(self.fixtures_url)
        try:
            rows = self.load_rows()
            return {
                "provider_name": self.provider_name,
                "status": "ready",
                "url": self.fixtures_url,
                "host": parsed.netloc,
                "rows": len(rows),
                "provider_kind": "api_football",
                "resolve_enabled": self.resolve_enabled,
                **self.sync_report(),
            }
        except Exception as exc:
            return {
                "provider_name": self.provider_name,
                "status": "error",
                "url": self.fixtures_url,
                "host": parsed.netloc,
                "provider_kind": "api_football",
                "resolve_enabled": self.resolve_enabled,
                "error": str(exc),
                **self.sync_report(),
            }

    def sync_report(self) -> dict[str, Any]:
        if not isinstance(self._last_load_meta, dict):
            return {}
        return dict(self._last_load_meta)


class TitanDetailAvailabilityProvider(AvailabilityProvider):
    provider_name = "titan_detail_source"

    def __init__(
        self,
        *,
        provider_name: str | None = None,
        base_url: str = "https://live.titan007.com",
        timeout_seconds: int = 15,
        resolve_direct: bool = False,
        max_matches: int = 80,
        request_delay_ms: int = 0,
        headers: Mapping[str, Any] | None = None,
    ) -> None:
        self.base_url = str(base_url or "https://live.titan007.com").rstrip("/")
        self.timeout_seconds = max(3, int(timeout_seconds))
        self.resolve_enabled = bool(resolve_direct)
        self.max_matches = max(1, min(int(max_matches), 300))
        self.request_delay_ms = max(0, int(request_delay_ms))
        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,*/*",
            **{str(key): str(value) for key, value in dict(headers or {}).items()},
        }
        self._last_load_meta: dict[str, Any] = {}
        if provider_name:
            self.provider_name = provider_name

    @staticmethod
    def _availability_score(absent_count: int, key_absent_count: int, lineup_known: bool) -> float:
        base = 1.0 if lineup_known else 0.72
        penalty = int(absent_count) * 0.08 + int(key_absent_count) * 0.14
        return round(_clip(base - penalty), 4)

    def _detail_url(self, schedule_id: str) -> str:
        sid = "".join(ch for ch in str(schedule_id or "") if ch.isdigit())
        return f"{self.base_url}/detail/{sid}cn.htm"

    def _fetch_detail_html(self, schedule_id: str) -> str:
        url = self._detail_url(schedule_id)
        request = Request(url, headers={**self.headers, "Referer": f"{self.base_url}/index.aspx"})
        with urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read()
        return raw.decode("utf-8", errors="ignore")

    def _load_titan_matches(self) -> list[Any]:
        try:
            from v24_app.data_sources.match_fetcher_titan import MatchFetcherTitan
        except Exception:
            return []
        fetcher = MatchFetcherTitan(debug=False)
        try:
            return list(fetcher.get_today_matches())
        except Exception:
            return []

    @staticmethod
    def _parse_lineup_counts(soup: BeautifulSoup) -> tuple[int, int, int, int]:
        lineup_box = soup.select_one("#matchBox2")
        home_box = len(lineup_box.select(".home .play")) if lineup_box else 0
        away_box = len(lineup_box.select(".guest .play")) if lineup_box else 0
        backup_box = soup.select_one(".backupPlay.backupPlay2")
        backup_home = len(backup_box.select(".home .play")) if backup_box else 0
        backup_away = len(backup_box.select(".guest .play")) if backup_box else 0

        if backup_home > 0 or backup_away > 0:
            start_home = max(home_box - backup_home, 0)
            start_away = max(away_box - backup_away, 0)
        else:
            start_home = min(home_box, 11) if home_box > 0 else 0
            start_away = min(away_box, 11) if away_box > 0 else 0
        return start_home, start_away, backup_home, backup_away

    @staticmethod
    def _parse_absence_counts(soup: BeautifulSoup) -> tuple[int, int]:
        injury_box = soup.select_one(".backupPlay.hurtPlay")
        home_abs = len(injury_box.select(".home .play")) if injury_box else 0
        away_abs = len(injury_box.select(".guest .play")) if injury_box else 0
        return home_abs, away_abs

    def _build_row_from_match(self, match: Any, html: str) -> dict[str, Any]:
        soup = BeautifulSoup(html or "", "html.parser")
        start_home, start_away, backup_home, backup_away = self._parse_lineup_counts(soup)
        home_absent, away_absent = self._parse_absence_counts(soup)

        home_lineup_known = start_home >= 11
        away_lineup_known = start_away >= 11
        lineup_known = home_lineup_known and away_lineup_known
        home_known = bool(start_home > 0 or home_absent > 0)
        away_known = bool(start_away > 0 or away_absent > 0)

        if lineup_known:
            quality = 1.0
        elif home_known or away_known:
            quality = 0.82
        else:
            quality = 0.0

        injury_conflict_score = round(
            _clip(abs(int(home_absent) - int(away_absent)) * 0.12),
            4,
        )
        source_id = _text(getattr(match, "match_id", ""))
        match_date = _text(getattr(match, "match_date", ""))
        league = _text(getattr(match, "league", ""))
        home_team = _text(getattr(match, "home_team", ""))
        away_team = _text(getattr(match, "away_team", ""))
        row = {
            "source_id": source_id,
            "match_date": match_date,
            "league": league,
            "home_team": home_team,
            "away_team": away_team,
            "lineup_known": lineup_known,
            "lineup_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "team_availability_quality": round(float(quality), 4),
            "injury_conflict_score": injury_conflict_score,
            "home_availability_known": home_known,
            "away_availability_known": away_known,
            "home_absent_count": int(home_absent),
            "away_absent_count": int(away_absent),
            "home_key_absent_count": 0,
            "away_key_absent_count": 0,
            "home_availability_score": self._availability_score(home_absent, 0, home_lineup_known),
            "away_availability_score": self._availability_score(away_absent, 0, away_lineup_known),
            "provider_kind": "titan_detail",
            "home_start_count": int(start_home),
            "away_start_count": int(start_away),
            "home_backup_count": int(backup_home),
            "away_backup_count": int(backup_away),
        }
        return row

    def load_rows(self) -> list[dict[str, Any]]:
        matches = self._load_titan_matches()
        total_matches = len(matches)
        if total_matches <= 0:
            self._last_load_meta = {
                "match_total": 0,
                "match_limit": 0,
                "detail_calls": 0,
                "detail_success": 0,
                "lineup_known_matches": 0,
                "injury_matches": 0,
                "provider_kind": "titan_detail",
            }
            return []

        rows: list[dict[str, Any]] = []
        detail_calls = 0
        detail_success = 0
        lineup_known_matches = 0
        injury_matches = 0
        errors: list[str] = []

        for match in matches[: self.max_matches]:
            source_id = _text(getattr(match, "match_id", ""))
            if not source_id:
                continue
            detail_calls += 1
            try:
                html = self._fetch_detail_html(source_id)
                row = self._build_row_from_match(match, html)
                rows.append(row)
                detail_success += 1
                if bool(row.get("lineup_known")):
                    lineup_known_matches += 1
                if int(row.get("home_absent_count", 0) or 0) + int(row.get("away_absent_count", 0) or 0) > 0:
                    injury_matches += 1
            except Exception as exc:
                errors.append(f"{source_id}: {exc}")
            if self.request_delay_ms > 0:
                time.sleep(self.request_delay_ms / 1000.0)

        self._last_load_meta = {
            "match_total": int(total_matches),
            "match_limit": int(min(total_matches, self.max_matches)),
            "detail_calls": int(detail_calls),
            "detail_success": int(detail_success),
            "lineup_known_matches": int(lineup_known_matches),
            "injury_matches": int(injury_matches),
            "provider_kind": "titan_detail",
            "detail_errors": errors[:20],
            "detail_error_count": int(len(errors)),
        }
        return rows

    def resolve_for_match(self, match: Any) -> AvailabilityProviderResult:
        try:
            rows = self.load_rows()
        except Exception as exc:
            return AvailabilityProviderResult(
                provider_name=self.provider_name,
                record={},
                metadata={"status": "error", "provider_kind": "titan_detail", "error": str(exc)},
            )
        return self._resolve_from_rows(
            rows,
            match,
            metadata={
                "status": "loaded",
                "provider_kind": "titan_detail",
                "rows": len(rows),
                **self.sync_report(),
            },
        )

    def status(self) -> dict[str, Any]:
        try:
            rows = self.load_rows()
            return {
                "provider_name": self.provider_name,
                "status": "ready",
                "rows": len(rows),
                "provider_kind": "titan_detail",
                "resolve_enabled": self.resolve_enabled,
                **self.sync_report(),
            }
        except Exception as exc:
            return {
                "provider_name": self.provider_name,
                "status": "error",
                "rows": 0,
                "provider_kind": "titan_detail",
                "resolve_enabled": self.resolve_enabled,
                "error": str(exc),
                **self.sync_report(),
            }

    def sync_report(self) -> dict[str, Any]:
        if not isinstance(self._last_load_meta, dict):
            return {}
        return dict(self._last_load_meta)


def _extract_crawler_payload(payload_text: str, *, parser_kind: str, payload_pattern: str | None = None) -> str:
    kind = _text(parser_kind).lower() or "embedded_json"
    if kind == "raw_json":
        return payload_text

    patterns: list[str] = []
    if payload_pattern:
        patterns.append(payload_pattern)
    if kind == "embedded_json":
        patterns.extend(
            [
                r"<script[^>]+id=[\"']__NEXT_DATA__[\"'][^>]*>\s*(?P<payload>\{.*?\})\s*</script>",
                r"<script[^>]+type=[\"']application/json[\"'][^>]*>\s*(?P<payload>\{.*?\}|\[.*?\])\s*</script>",
                r"window\.__INITIAL_STATE__\s*=\s*(?P<payload>\{.*?\})\s*;",
                r"window\.__DATA__\s*=\s*(?P<payload>\{.*?\})\s*;",
            ]
        )
    for pattern in patterns:
        match = re.search(pattern, payload_text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        if "payload" in match.groupdict():
            return match.group("payload")
        if match.lastindex:
            return match.group(1)
        return match.group(0)
    raise ValueError(f"Unsupported crawler payload or pattern miss: {parser_kind}")


class CrawlerAvailabilityProvider(AvailabilityProvider):
    provider_name = "crawler_source"

    def __init__(
        self,
        *,
        url: str,
        provider_name: str | None = None,
        source_format: str = "json",
        items_key: str | None = None,
        parser_kind: str = "embedded_json",
        payload_pattern: str | None = None,
        timeout_seconds: int = 15,
        provider_kind: str = "generic",
        resolve_direct: bool = False,
        headers: Mapping[str, Any] | None = None,
    ) -> None:
        self.url = str(url)
        self.source_format = source_format
        self.items_key = items_key
        self.parser_kind = parser_kind
        self.payload_pattern = payload_pattern
        self.timeout_seconds = max(3, timeout_seconds)
        self.provider_kind = _text(provider_kind).lower() or "generic"
        self.resolve_enabled = bool(resolve_direct)
        self.headers = {str(key): str(value) for key, value in dict(headers or {}).items()}
        if provider_name:
            self.provider_name = provider_name

    def load_rows(self) -> list[dict[str, Any]]:
        request = Request(self.url, headers=self.headers)
        with urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
        text = raw.decode(charset, errors="replace")
        extracted = _extract_crawler_payload(
            text,
            parser_kind=self.parser_kind,
            payload_pattern=self.payload_pattern,
        )
        return _load_rows_from_text(
            extracted,
            source_format=self.source_format,
            items_key=self.items_key,
            provider_kind=self.provider_kind,
        )

    def resolve_for_match(self, match: Any) -> AvailabilityProviderResult:
        try:
            rows = self.load_rows()
        except Exception as exc:
            return AvailabilityProviderResult(
                provider_name=self.provider_name,
                record={},
                metadata={"status": "error", "url": self.url, "error": str(exc)},
            )
        return self._resolve_from_rows(
            rows,
            match,
            metadata={
                "status": "loaded",
                "url": self.url,
                "rows": len(rows),
                "format": self.source_format,
                "provider_kind": self.provider_kind,
                "parser_kind": self.parser_kind,
            },
        )

    def status(self) -> dict[str, Any]:
        parsed = urlparse(self.url)
        try:
            rows = self.load_rows()
            return {
                "provider_name": self.provider_name,
                "status": "ready",
                "url": self.url,
                "host": parsed.netloc,
                "rows": len(rows),
                "format": self.source_format,
                "provider_kind": self.provider_kind,
                "parser_kind": self.parser_kind,
                "resolve_enabled": self.resolve_enabled,
            }
        except Exception as exc:
            return {
                "provider_name": self.provider_name,
                "status": "error",
                "url": self.url,
                "host": parsed.netloc,
                "format": self.source_format,
                "provider_kind": self.provider_kind,
                "parser_kind": self.parser_kind,
                "resolve_enabled": self.resolve_enabled,
                "error": str(exc),
            }


class AvailabilityProviderChain:
    def __init__(self, providers: Iterable[AvailabilityProvider]) -> None:
        self.providers = list(providers)

    @staticmethod
    def _provider_retry_attempts(provider: AvailabilityProvider, default: int) -> int:
        value = getattr(provider, "sync_retry_attempts", default)
        return max(0, _safe_int(value, default))

    @staticmethod
    def _provider_retry_backoff_ms(provider: AvailabilityProvider, default: int) -> int:
        value = getattr(provider, "sync_retry_backoff_ms", default)
        return max(0, _safe_int(value, default))

    @staticmethod
    def _provider_retry_max_backoff_ms(provider: AvailabilityProvider, default: int) -> int:
        value = getattr(provider, "sync_retry_max_backoff_ms", default)
        return max(0, _safe_int(value, default))

    @staticmethod
    def _load_rows_with_retry(
        provider: AvailabilityProvider,
        *,
        retry_attempts: int,
        retry_backoff_ms: int,
        max_retry_backoff_ms: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        attempts = max(0, int(retry_attempts))
        attempt_errors: list[str] = []
        retry_delays_ms: list[int] = []
        last_error: str = ""
        attempt_count = 0

        for attempt_index in range(attempts + 1):
            attempt_count = attempt_index + 1
            try:
                rows = provider.load_rows()
                if not isinstance(rows, list):
                    rows = list(rows) if isinstance(rows, tuple) else []
                meta = {
                    "attempt_count": int(attempt_count),
                    "retry_count": int(max(attempt_count - 1, 0)),
                    "retry_attempts": int(attempts),
                    "retry_backoff_ms": int(retry_backoff_ms),
                    "retry_max_backoff_ms": int(max_retry_backoff_ms),
                    "attempt_errors": list(attempt_errors),
                    "retry_delays_ms": list(retry_delays_ms),
                    "recovered_after_retry": bool(attempt_index > 0),
                    "retry_exhausted": False,
                    "last_error": "",
                }
                return rows, meta
            except Exception as exc:
                last_error = str(exc)
                attempt_errors.append(last_error)
                if attempt_index < attempts:
                    delay_ms = _retry_delay_ms(retry_backoff_ms, attempt_index, max_retry_backoff_ms)
                    retry_delays_ms.append(delay_ms)
                    if delay_ms > 0:
                        time.sleep(delay_ms / 1000.0)

        meta = {
            "attempt_count": int(attempt_count),
            "retry_count": int(max(attempt_count - 1, 0)),
            "retry_attempts": int(attempts),
            "retry_backoff_ms": int(retry_backoff_ms),
            "retry_max_backoff_ms": int(max_retry_backoff_ms),
            "attempt_errors": list(attempt_errors),
            "retry_delays_ms": list(retry_delays_ms),
            "recovered_after_retry": False,
            "retry_exhausted": bool(attempts > 0),
            "last_error": last_error,
        }
        return [], meta

    def resolve_for_match(self, match: Any) -> AvailabilityProviderResult:
        attempts: list[dict[str, Any]] = []
        for provider in self.providers:
            if not getattr(provider, "resolve_enabled", True):
                attempts.append(
                    {
                        "provider_name": provider.provider_name,
                        "matched": False,
                        "metadata": {"status": "resolve_skipped"},
                    }
                )
                continue
            result = provider.resolve_for_match(match)
            attempts.append(
                {
                    "provider_name": result.provider_name,
                    "matched": bool(result.record),
                    "metadata": dict(result.metadata),
                }
            )
            if result.record:
                merged_metadata = dict(result.metadata)
                merged_metadata["attempts"] = attempts
                return AvailabilityProviderResult(
                    provider_name=result.provider_name,
                    record=result.record,
                    metadata=merged_metadata,
                )
        return AvailabilityProviderResult(provider_name="none", record={}, metadata={"attempts": attempts})

    def sync_to_store(
        self,
        project_root: str | Path,
        *,
        replace: bool = False,
        retry_attempts: int = 1,
        retry_backoff_ms: int = 250,
        max_retry_backoff_ms: int = 2000,
    ) -> dict[str, Any]:
        store = C1AvailabilityStore(project_root)
        provider_reports: list[dict[str, Any]] = []
        total_rows = 0
        total_keys = 0
        first_write = True
        for provider in self.providers:
            provider_meta = provider.sync_report() if hasattr(provider, "sync_report") else {}
            provider_retry_attempts = self._provider_retry_attempts(provider, retry_attempts)
            provider_retry_backoff_ms = self._provider_retry_backoff_ms(provider, retry_backoff_ms)
            provider_retry_max_backoff_ms = self._provider_retry_max_backoff_ms(provider, max_retry_backoff_ms)
            if not getattr(provider, "sync_enabled", True):
                row = {
                    "provider_name": provider.provider_name,
                    "status": "sync_skipped",
                    "reason": "sync_not_supported",
                    "rows": 0,
                    "written_keys": 0,
                    "attempt_count": 0,
                    "retry_count": 0,
                    "retry_attempts": 0,
                    "retry_backoff_ms": provider_retry_backoff_ms,
                    "retry_max_backoff_ms": provider_retry_max_backoff_ms,
                    "attempt_errors": [],
                    "retry_delays_ms": [],
                    "recovered_after_retry": False,
                    "retry_exhausted": False,
                }
                if isinstance(provider_meta, Mapping):
                    row.update(dict(provider_meta))
                provider_reports.append(row)
                continue
            try:
                rows, attempt_meta = self._load_rows_with_retry(
                    provider,
                    retry_attempts=provider_retry_attempts,
                    retry_backoff_ms=provider_retry_backoff_ms,
                    max_retry_backoff_ms=provider_retry_max_backoff_ms,
                )
            except Exception as exc:
                row = {
                    "provider_name": provider.provider_name,
                    "status": "error",
                    "reason": "load_failed",
                    "error": str(exc),
                    "rows": 0,
                    "written_keys": 0,
                    "attempt_count": 0,
                    "retry_count": 0,
                    "retry_attempts": provider_retry_attempts,
                    "retry_backoff_ms": provider_retry_backoff_ms,
                    "retry_max_backoff_ms": provider_retry_max_backoff_ms,
                    "attempt_errors": [str(exc)],
                    "retry_delays_ms": [],
                    "recovered_after_retry": False,
                    "retry_exhausted": bool(provider_retry_attempts > 0),
                }
                provider_meta = provider.sync_report() if hasattr(provider, "sync_report") else {}
                if isinstance(provider_meta, Mapping):
                    row.update(dict(provider_meta))
                row["quality_gate"] = "fail"
                row["quality_issues"] = ["load_failed"]
                signal_issues = _provider_signal_issues(row)
                row["signal_issues"] = signal_issues
                provider_reports.append(row)
                continue
            if not rows:
                provider_meta = provider.sync_report() if hasattr(provider, "sync_report") else {}
                upstream_error = False
                if isinstance(provider_meta, Mapping):
                    upstream_error = bool(provider_meta.get("fixtures_upstream_error"))
                load_failed = bool(attempt_meta.get("attempt_errors")) or bool(attempt_meta.get("retry_exhausted"))
                row = {
                    "provider_name": provider.provider_name,
                    "status": "error" if (upstream_error or load_failed) else "empty",
                    "reason": "upstream_error" if upstream_error else ("load_failed" if load_failed else "no_rows"),
                    "rows": 0,
                    "written_keys": 0,
                    "attempt_count": attempt_meta.get("attempt_count", 0),
                    "retry_count": attempt_meta.get("retry_count", 0),
                    "retry_attempts": attempt_meta.get("retry_attempts", provider_retry_attempts),
                    "retry_backoff_ms": attempt_meta.get("retry_backoff_ms", provider_retry_backoff_ms),
                    "retry_max_backoff_ms": attempt_meta.get("retry_max_backoff_ms", provider_retry_max_backoff_ms),
                    "attempt_errors": attempt_meta.get("attempt_errors", []),
                    "retry_delays_ms": attempt_meta.get("retry_delays_ms", []),
                    "recovered_after_retry": bool(attempt_meta.get("recovered_after_retry")),
                    "retry_exhausted": bool(attempt_meta.get("retry_exhausted")),
                    "last_error": attempt_meta.get("last_error", ""),
                }
                if isinstance(provider_meta, Mapping):
                    row.update(dict(provider_meta))
                row["quality_gate"] = "fail"
                row["quality_issues"] = ["upstream_error" if upstream_error else "no_rows"]
                row["signal_issues"] = _provider_signal_issues(row)
                provider_reports.append(row)
                continue
            quality = _availability_quality_report(rows)
            result = store.import_rows(rows, replace=replace and first_write)
            first_write = False
            row = {
                "provider_name": provider.provider_name,
                "status": "imported",
                "rows": int(result.get("imported_rows", 0)),
                "written_keys": int(result.get("written_keys", 0)),
                "attempt_count": attempt_meta.get("attempt_count", 0),
                "retry_count": attempt_meta.get("retry_count", 0),
                "retry_attempts": attempt_meta.get("retry_attempts", provider_retry_attempts),
                "retry_backoff_ms": attempt_meta.get("retry_backoff_ms", provider_retry_backoff_ms),
                "retry_max_backoff_ms": attempt_meta.get("retry_max_backoff_ms", provider_retry_max_backoff_ms),
                "attempt_errors": attempt_meta.get("attempt_errors", []),
                "retry_delays_ms": attempt_meta.get("retry_delays_ms", []),
                "recovered_after_retry": bool(attempt_meta.get("recovered_after_retry")),
                "retry_exhausted": bool(attempt_meta.get("retry_exhausted")),
                "last_error": attempt_meta.get("last_error", ""),
            }
            row.update(quality)
            provider_meta = provider.sync_report() if hasattr(provider, "sync_report") else {}
            if isinstance(provider_meta, Mapping):
                row.update(dict(provider_meta))
            signal_issues = _provider_signal_issues(row)
            row["signal_issues"] = signal_issues
            provider_reports.append(row)
            total_rows += int(result.get("imported_rows", 0))
            total_keys += int(result.get("written_keys", 0))
        failed_providers = sum(1 for item in provider_reports if str(item.get("status")) == "error")
        imported_providers = sum(1 for item in provider_reports if str(item.get("status")) == "imported")
        quality_failures = sum(1 for item in provider_reports if str(item.get("quality_gate")) == "fail")
        quality_warnings = sum(1 for item in provider_reports if str(item.get("quality_gate")) == "warn")
        retry_recovered_providers = sum(1 for item in provider_reports if bool(item.get("recovered_after_retry")))
        retry_exhausted_providers = sum(1 for item in provider_reports if bool(item.get("retry_exhausted")))
        provider_failure_reasons = []
        for item in provider_reports:
            failure_reason = _provider_failure_reason(item)
            if not failure_reason:
                continue
            provider_failure_reasons.append(failure_reason)
        provider_signal_errors = sum(1 for item in provider_failure_reasons if item.get("severity") == "error")
        provider_signal_warnings = sum(1 for item in provider_failure_reasons if item.get("severity") == "warning")
        smoke_status = "pass"
        smoke_issues: list[str] = []
        if imported_providers <= 0 or total_rows <= 0 or total_keys <= 0:
            smoke_status = "fail"
            smoke_issues.append("no_imported_availability_rows")
        if quality_failures > 0 or provider_signal_errors > 0:
            smoke_status = "fail"
            smoke_issues.append("provider_quality_gate_failed")
        elif (quality_warnings > 0 or provider_signal_warnings > 0 or retry_recovered_providers > 0) and smoke_status == "pass":
            smoke_status = "warn"
            smoke_issues.append("provider_quality_gate_warning")
        if failed_providers > 0 and smoke_status == "pass":
            smoke_status = "warn"
            smoke_issues.append("provider_errors_present")
        sync_report = {
            "provider_reports": provider_reports,
            "total_rows": total_rows,
            "total_keys": total_keys,
            "failed_providers": failed_providers,
            "imported_providers": imported_providers,
            "quality_failures": quality_failures,
            "quality_warnings": quality_warnings,
            "retry_recovered_providers": retry_recovered_providers,
            "retry_exhausted_providers": retry_exhausted_providers,
            "provider_signal_errors": provider_signal_errors,
            "provider_signal_warnings": provider_signal_warnings,
            "provider_failure_reasons": provider_failure_reasons,
            "retry_policy": {
                "default_attempts": int(max(0, retry_attempts)),
                "default_backoff_ms": int(max(0, retry_backoff_ms)),
                "default_max_backoff_ms": int(max(0, max_retry_backoff_ms)),
            },
            "smoke_check": {
                "status": smoke_status,
                "issues": smoke_issues,
                "release_review_allowed": smoke_status != "fail",
            },
            "snapshot_file": str(store.snapshot_file),
            "last_sync_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        store.save_sync_status(sync_report)
        return sync_report

    def provider_statuses(self) -> list[dict[str, Any]]:
        return [provider.status() for provider in self.providers]

    @classmethod
    def from_project_root(
        cls,
        project_root: str | Path,
        *,
        config: Mapping[str, Any] | None = None,
    ) -> "AvailabilityProviderChain":
        root = Path(project_root)
        provider_config = dict(config or load_availability_provider_config())
        providers: list[AvailabilityProvider] = []

        def _apply_retry_policy(provider: AvailabilityProvider, item: Mapping[str, Any]) -> AvailabilityProvider:
            provider.sync_retry_attempts = _safe_int(item.get("retry_attempts"), 1)  # type: ignore[attr-defined]
            provider.sync_retry_backoff_ms = _safe_int(item.get("retry_backoff_ms"), 250)  # type: ignore[attr-defined]
            provider.sync_retry_max_backoff_ms = _safe_int(item.get("retry_max_backoff_ms"), 2000)  # type: ignore[attr-defined]
            return provider

        for item in provider_config.get("providers", []):
            if not isinstance(item, Mapping):
                continue
            provider_type = _text(item.get("type"))
            enabled = bool(item.get("enabled", True))
            if not enabled:
                continue
            if provider_type == "stored_snapshots":
                providers.append(_apply_retry_policy(StoredAvailabilityProvider(root), item))
            elif provider_type == "file_source":
                source_path = _text(item.get("path"))
                if not source_path:
                    continue
                path = Path(source_path)
                if not path.is_absolute():
                    path = root / path
                providers.append(
                    _apply_retry_policy(
                        FileAvailabilityProvider(
                            source_path=path,
                            provider_name=_text(item.get("name")) or "file_source",
                        ),
                        item,
                    )
                )
            elif provider_type == "http_source":
                url = _text(item.get("url"))
                if not url:
                    continue
                providers.append(
                    _apply_retry_policy(
                        HttpAvailabilityProvider(
                            url=url,
                            provider_name=_text(item.get("name")) or "http_source",
                            source_format=_text(item.get("format")) or "json",
                            items_key=_text(item.get("items_key")) or None,
                            timeout_seconds=_safe_int(item.get("timeout_seconds"), 15),
                            provider_kind=_text(item.get("provider_kind")) or "generic",
                            resolve_direct=bool(item.get("resolve_direct", True)),
                            headers=item.get("headers") if isinstance(item.get("headers"), Mapping) else None,
                        ),
                        item,
                    )
                )
            elif provider_type == "api_football_source":
                fixtures_url = _text(item.get("url"))
                if not fixtures_url:
                    continue
                providers.append(
                    _apply_retry_policy(
                        ApiFootballAvailabilityProvider(
                            fixtures_url=fixtures_url,
                            provider_name=_text(item.get("name")) or "api_football_source",
                            lineups_url_template=_text(item.get("lineups_url_template")) or None,
                            injuries_url_template=_text(item.get("injuries_url_template")) or None,
                            timeout_seconds=_safe_int(item.get("timeout_seconds"), 15),
                            resolve_direct=bool(item.get("resolve_direct", False)),
                            headers=item.get("headers") if isinstance(item.get("headers"), Mapping) else None,
                            max_fixtures=_safe_int(item.get("max_fixtures"), 60),
                            request_delay_ms=_safe_int(item.get("request_delay_ms"), 0),
                        ),
                        item,
                    )
                )
            elif provider_type == "titan_detail_source":
                providers.append(
                    _apply_retry_policy(
                        TitanDetailAvailabilityProvider(
                            provider_name=_text(item.get("name")) or "titan_detail_source",
                            base_url=_text(item.get("base_url")) or "https://live.titan007.com",
                            timeout_seconds=_safe_int(item.get("timeout_seconds"), 15),
                            resolve_direct=bool(item.get("resolve_direct", False)),
                            max_matches=_safe_int(item.get("max_matches"), 80),
                            request_delay_ms=_safe_int(item.get("request_delay_ms"), 0),
                            headers=item.get("headers") if isinstance(item.get("headers"), Mapping) else None,
                        ),
                        item,
                    )
                )
            elif provider_type == "crawler_source":
                url = _text(item.get("url"))
                if not url:
                    continue
                providers.append(
                    _apply_retry_policy(
                        CrawlerAvailabilityProvider(
                            url=url,
                            provider_name=_text(item.get("name")) or "crawler_source",
                            source_format=_text(item.get("format")) or "json",
                            items_key=_text(item.get("items_key")) or None,
                            parser_kind=_text(item.get("parser_kind")) or "embedded_json",
                            payload_pattern=_text(item.get("payload_pattern")) or None,
                            timeout_seconds=_safe_int(item.get("timeout_seconds"), 15),
                            provider_kind=_text(item.get("provider_kind")) or "generic",
                            resolve_direct=bool(item.get("resolve_direct", False)),
                            headers=item.get("headers") if isinstance(item.get("headers"), Mapping) else None,
                        ),
                        item,
                    )
                )
        if not providers:
            providers.append(StoredAvailabilityProvider(root))
        return cls(providers)
