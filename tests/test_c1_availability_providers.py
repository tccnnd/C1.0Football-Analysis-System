from __future__ import annotations

import csv
import json
import shutil
import sys
import threading
import unittest
import uuid
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from c1.data import AvailabilityProviderChain, C1AvailabilityStore
from c1.data.providers import ApiFootballAvailabilityProvider, TitanDetailAvailabilityProvider
from v24_app.core import AppMatch


class C1AvailabilityProviderTests(unittest.TestCase):
    def make_test_root(self) -> Path:
        base_dir = PROJECT_ROOT / "data" / "tmp_c1_provider_tests"
        base_dir.mkdir(parents=True, exist_ok=True)
        path = base_dir / f"case_{uuid.uuid4().hex}"
        path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def sample_match(self) -> AppMatch:
        return AppMatch(
            home_team="A",
            away_team="B",
            league="Friendly",
            match_time="19:35",
            match_date="2026-04-03",
            odds_home=1.88,
            odds_draw=3.35,
            odds_away=4.1,
            handicap_line=-0.5,
            source="live:titan",
            source_id="2965321",
        )

    def test_provider_chain_resolves_from_stored_snapshots(self) -> None:
        root = self.make_test_root()
        store = C1AvailabilityStore(root)
        store.import_rows(
            [
                {
                    "source_id": "2965321",
                    "match_date": "2026-04-03",
                    "league": "Friendly",
                    "home_team": "A",
                    "away_team": "B",
                    "lineup_known": True,
                    "lineup_freshness_hours": 1,
                }
            ]
        )
        chain = AvailabilityProviderChain.from_project_root(root, config={"providers": [{"type": "stored_snapshots", "enabled": True}]})
        result = chain.resolve_for_match(self.sample_match())
        self.assertEqual(result.provider_name, "stored_snapshots")
        self.assertTrue(result.record.get("lineup_known"))

    def test_provider_chain_resolves_from_file_provider(self) -> None:
        root = self.make_test_root()
        source = root / "availability_external.csv"
        with source.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["source_id", "match_date", "league", "home_team", "away_team", "lineup_known", "lineup_freshness_hours"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "source_id": "2965321",
                    "match_date": "2026-04-03",
                    "league": "Friendly",
                    "home_team": "A",
                    "away_team": "B",
                    "lineup_known": "true",
                    "lineup_freshness_hours": "2",
                }
            )
        chain = AvailabilityProviderChain.from_project_root(
            root,
            config={
                "providers": [
                    {"type": "stored_snapshots", "enabled": False},
                    {"type": "file_source", "enabled": True, "name": "external_csv", "path": str(source)},
                ]
            },
        )
        result = chain.resolve_for_match(self.sample_match())
        self.assertEqual(result.provider_name, "external_csv")
        self.assertEqual(result.metadata.get("status"), "loaded")
        self.assertEqual(result.record.get("source_id"), "2965321")

    def test_provider_chain_resolves_from_http_provider(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                body = json.dumps(
                    {
                        "items": [
                            {
                                "source_id": "2965321",
                                "match_date": "2026-04-03",
                                "league": "Friendly",
                                "home_team": "A",
                                "away_team": "B",
                                "lineup_known": True,
                                "lineup_freshness_hours": 1,
                            }
                        ]
                    }
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), thread.join(timeout=2), server.server_close()))
        root = self.make_test_root()
        chain = AvailabilityProviderChain.from_project_root(
            root,
            config={
                "providers": [
                    {"type": "stored_snapshots", "enabled": False},
                    {
                        "type": "http_source",
                        "enabled": True,
                        "name": "external_http",
                        "url": f"http://127.0.0.1:{server.server_port}/availability",
                        "format": "json",
                        "items_key": "items",
                        "timeout_seconds": 5,
                    },
                ]
            },
        )
        result = chain.resolve_for_match(self.sample_match())
        self.assertEqual(result.provider_name, "external_http")
        self.assertEqual(result.metadata.get("status"), "loaded")
        self.assertTrue(result.record.get("lineup_known"))

    def test_provider_chain_normalizes_sportmonks_payload(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                body = json.dumps(
                    {
                        "data": [
                            {
                                "id": 2965321,
                                "starting_at": "2026-04-03T19:35:00+08:00",
                                "league": {"name": "Friendly"},
                                "participants": [
                                    {"id": 11, "name": "A", "meta": {"location": "home"}},
                                    {"id": 12, "name": "B", "meta": {"location": "away"}},
                                ],
                                "lineups": {"data": [{"id": 1}]},
                                "sidelined": {
                                    "data": [
                                        {"id": 100, "participant_id": 11, "is_key": True},
                                        {"id": 101, "participant_id": 12, "is_key": False},
                                    ]
                                },
                            }
                        ]
                    }
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), thread.join(timeout=2), server.server_close()))
        root = self.make_test_root()
        chain = AvailabilityProviderChain.from_project_root(
            root,
            config={
                "providers": [
                    {"type": "stored_snapshots", "enabled": False},
                    {
                        "type": "http_source",
                        "enabled": True,
                        "name": "sportmonks_primary",
                        "provider_kind": "sportmonks",
                        "url": f"http://127.0.0.1:{server.server_port}/fixtures",
                        "format": "json",
                        "items_key": "data",
                        "timeout_seconds": 5,
                    },
                ]
            },
        )
        result = chain.resolve_for_match(self.sample_match())
        self.assertEqual(result.provider_name, "sportmonks_primary")
        self.assertEqual(result.record.get("provider_kind"), "sportmonks")
        self.assertEqual(result.record.get("source_id"), "2965321")
        self.assertEqual(result.record.get("home_absent_count"), 1)
        self.assertEqual(result.record.get("away_absent_count"), 1)
        self.assertEqual(result.record.get("home_key_absent_count"), 1)

    def test_provider_chain_normalizes_api_football_payload(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                body = json.dumps(
                    {
                        "response": [
                            {
                                "fixture": {"id": 2965321, "date": "2026-04-03T19:35:00+08:00"},
                                "league": {"name": "Friendly"},
                                "team": {"id": 11, "name": "A"},
                                "startXI": [{"player": {"id": 1}}],
                                "missing_players": [{"player": {"id": 3}, "is_key": True}],
                                "meta": {"location": "home"},
                            },
                            {
                                "fixture": {"id": 2965321, "date": "2026-04-03T19:35:00+08:00"},
                                "league": {"name": "Friendly"},
                                "team": {"id": 12, "name": "B"},
                                "startXI": [{"player": {"id": 2}}],
                                "missing_players": [{"player": {"id": 4}, "is_key": False}],
                                "meta": {"location": "away"},
                            },
                        ]
                    }
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), thread.join(timeout=2), server.server_close()))
        root = self.make_test_root()
        chain = AvailabilityProviderChain.from_project_root(
            root,
            config={
                "providers": [
                    {"type": "stored_snapshots", "enabled": False},
                    {
                        "type": "http_source",
                        "enabled": True,
                        "name": "api_football_fallback",
                        "provider_kind": "api_football",
                        "url": f"http://127.0.0.1:{server.server_port}/lineups",
                        "format": "json",
                        "items_key": "response",
                        "timeout_seconds": 5,
                    },
                ]
            },
        )
        result = chain.resolve_for_match(self.sample_match())
        self.assertEqual(result.provider_name, "api_football_fallback")
        self.assertEqual(result.record.get("provider_kind"), "api_football")
        self.assertTrue(result.record.get("lineup_known"))
        self.assertEqual(result.record.get("home_key_absent_count"), 1)
        self.assertEqual(result.record.get("away_absent_count"), 1)

    def test_provider_chain_respects_resolve_direct_false(self) -> None:
        root = self.make_test_root()
        store = C1AvailabilityStore(root)
        store.import_rows(
            [
                {
                    "source_id": "2965321",
                    "match_date": "2026-04-03",
                    "league": "Friendly",
                    "home_team": "A",
                    "away_team": "B",
                    "lineup_known": True,
                    "provider_kind": "stored",
                }
            ]
        )
        chain = AvailabilityProviderChain.from_project_root(
            root,
            config={
                "providers": [
                    {
                        "type": "http_source",
                        "enabled": True,
                        "name": "api_football_primary",
                        "provider_kind": "api_football",
                        "url": "http://127.0.0.1:9/does-not-matter",
                        "format": "json",
                        "items_key": "response",
                        "resolve_direct": False,
                    },
                    {"type": "stored_snapshots", "enabled": True},
                ]
            },
        )
        result = chain.resolve_for_match(self.sample_match())
        self.assertEqual(result.provider_name, "stored_snapshots")
        attempts = result.metadata.get("attempts") or []
        self.assertEqual(attempts[0]["provider_name"], "api_football_primary")
        self.assertEqual(attempts[0]["metadata"].get("status"), "resolve_skipped")

    def test_crawler_provider_extracts_embedded_json(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                body = """
                <html><head></head><body>
                <script id="__NEXT_DATA__" type="application/json">
                {"items":[{"source_id":"2965321","match_date":"2026-04-03","league":"Friendly","home_team":"A","away_team":"B","lineup_known":true,"provider_kind":"crawler"}]}
                </script>
                </body></html>
                """.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), thread.join(timeout=2), server.server_close()))
        root = self.make_test_root()
        chain = AvailabilityProviderChain.from_project_root(
            root,
            config={
                "providers": [
                    {
                        "type": "crawler_source",
                        "enabled": True,
                        "name": "crawler_fallback",
                        "provider_kind": "generic",
                        "url": f"http://127.0.0.1:{server.server_port}/page",
                        "parser_kind": "embedded_json",
                        "format": "json",
                        "items_key": "items",
                        "resolve_direct": True,
                    }
                ]
            },
        )
        result = chain.resolve_for_match(self.sample_match())
        self.assertEqual(result.provider_name, "crawler_fallback")
        self.assertEqual(result.record.get("provider_kind"), "crawler")
        self.assertTrue(result.record.get("lineup_known"))

    def test_provider_chain_resolves_from_api_football_source(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                if self.path.startswith("/fixtures"):
                    body = json.dumps(
                        {
                            "response": [
                                {
                                    "fixture": {"id": 2965321, "date": "2026-04-03T19:35:00+08:00"},
                                    "league": {"name": "Friendly"},
                                    "teams": {
                                        "home": {"id": 11, "name": "A"},
                                        "away": {"id": 12, "name": "B"},
                                    },
                                }
                            ]
                        }
                    ).encode("utf-8")
                elif self.path.startswith("/lineups"):
                    body = json.dumps(
                        {
                            "response": [
                                {
                                    "team": {"id": 11, "name": "A"},
                                    "startXI": [{"player": {"id": 1}}],
                                    "formation": "4-4-2",
                                    "update": "2026-04-03T18:35:00+08:00",
                                },
                                {
                                    "team": {"id": 12, "name": "B"},
                                    "startXI": [{"player": {"id": 2}}],
                                    "formation": "4-3-3",
                                    "update": "2026-04-03T18:36:00+08:00",
                                },
                            ]
                        }
                    ).encode("utf-8")
                elif self.path.startswith("/injuries"):
                    body = json.dumps(
                        {
                            "response": [
                                {"team": {"id": 11, "name": "A"}, "player": {"id": 3, "name": "HX"}},
                                {"team": {"id": 12, "name": "B"}, "player": {"id": 4, "name": "AY"}},
                            ]
                        }
                    ).encode("utf-8")
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), thread.join(timeout=2), server.server_close()))
        root = self.make_test_root()
        chain = AvailabilityProviderChain.from_project_root(
            root,
            config={
                "providers": [
                    {
                        "type": "api_football_source",
                        "enabled": True,
                        "name": "api_football_primary",
                        "url": f"http://127.0.0.1:{server.server_port}/fixtures?date={{today}}",
                        "lineups_url_template": f"http://127.0.0.1:{server.server_port}/lineups?fixture={{fixture_id}}",
                        "injuries_url_template": f"http://127.0.0.1:{server.server_port}/injuries?fixture={{fixture_id}}",
                        "timeout_seconds": 5,
                        "resolve_direct": True,
                    }
                ]
            },
        )
        result = chain.resolve_for_match(self.sample_match())
        self.assertEqual(result.provider_name, "api_football_primary")
        self.assertEqual(result.record.get("provider_kind"), "api_football")
        self.assertTrue(result.record.get("lineup_known"))
        self.assertEqual(result.record.get("home_absent_count"), 1)
        self.assertEqual(result.record.get("away_absent_count"), 1)

    def test_api_football_source_uses_multi_date_fixture_queries(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            lineups_calls = 0
            injuries_calls = 0

            def do_GET(self):  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path == "/fixtures":
                    date_text = parse_qs(parsed.query).get("date", [""])[0]
                    if date_text == "2026-04-08":
                        body = json.dumps(
                            {
                                "results": 1,
                                "errors": [],
                                "response": [
                                    {
                                        "fixture": {"id": 2965321, "date": "2026-04-08T01:35:00+08:00"},
                                        "league": {"name": "Friendly"},
                                        "teams": {
                                            "home": {"id": 11, "name": "A"},
                                            "away": {"id": 12, "name": "B"},
                                        },
                                    }
                                ],
                            }
                        ).encode("utf-8")
                    else:
                        body = json.dumps({"results": 0, "errors": [], "response": []}).encode("utf-8")
                elif parsed.path == "/lineups":
                    Handler.lineups_calls += 1
                    body = json.dumps(
                        {
                            "response": [
                                {
                                    "team": {"id": 11, "name": "A"},
                                    "startXI": [{"player": {"id": 1}}],
                                    "formation": "4-4-2",
                                },
                                {
                                    "team": {"id": 12, "name": "B"},
                                    "startXI": [{"player": {"id": 2}}],
                                    "formation": "4-3-3",
                                },
                            ]
                        }
                    ).encode("utf-8")
                elif parsed.path == "/injuries":
                    Handler.injuries_calls += 1
                    body = json.dumps({"response": []}).encode("utf-8")
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), thread.join(timeout=2), server.server_close()))

        provider = ApiFootballAvailabilityProvider(
            fixtures_url=f"http://127.0.0.1:{server.server_port}/fixtures?date={{today}}",
            lineups_url_template=f"http://127.0.0.1:{server.server_port}/lineups?fixture={{fixture_id}}",
            injuries_url_template=f"http://127.0.0.1:{server.server_port}/injuries?fixture={{fixture_id}}",
            timeout_seconds=5,
            max_fixtures=20,
            request_delay_ms=0,
        )
        provider._issue_window = lambda _now: (datetime(2026, 4, 7, 11, 0, 0), datetime(2026, 4, 8, 11, 0, 0))  # type: ignore[attr-defined]

        rows = provider.load_rows()
        meta = provider.sync_report()
        self.assertGreaterEqual(len(rows), 1)
        self.assertEqual(int(meta.get("fixture_total", 0)), 1)
        self.assertEqual(meta.get("fixtures_date_queries"), ["2026-04-07", "2026-04-08"])
        self.assertEqual(int(meta.get("lineups_calls", 0)), 1)
        self.assertEqual(int(meta.get("injuries_calls", 0)), 1)
        self.assertEqual(Handler.lineups_calls, 1)
        self.assertEqual(Handler.injuries_calls, 1)

    def test_sync_to_store_continues_after_provider_error(self) -> None:
        root = self.make_test_root()
        source = root / "availability_external.csv"
        with source.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["source_id", "match_date", "league", "home_team", "away_team", "lineup_known", "lineup_freshness_hours"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "source_id": "2965321",
                    "match_date": "2026-04-03",
                    "league": "Friendly",
                    "home_team": "A",
                    "away_team": "B",
                    "lineup_known": "true",
                    "lineup_freshness_hours": "2",
                }
            )

        chain = AvailabilityProviderChain.from_project_root(
            root,
            config={
                "providers": [
                    {
                        "type": "http_source",
                        "enabled": True,
                        "name": "api_football_primary",
                        "provider_kind": "api_football",
                        "url": "http://127.0.0.1:9/blocked",
                        "format": "json",
                        "items_key": "response",
                        "timeout_seconds": 1,
                    },
                    {"type": "file_source", "enabled": True, "name": "external_csv", "path": str(source)},
                    {"type": "stored_snapshots", "enabled": True},
                ]
            },
        )

        report = chain.sync_to_store(root, replace=False, retry_backoff_ms=0)
        self.assertEqual(int(report.get("failed_providers", 0)), 1)
        self.assertEqual(int(report.get("imported_providers", 0)), 1)
        self.assertGreater(int(report.get("total_rows", 0)), 0)
        provider_reports = report.get("provider_reports") or []
        self.assertEqual(provider_reports[0].get("status"), "error")
        self.assertEqual(provider_reports[1].get("status"), "imported")
        self.assertEqual(provider_reports[2].get("status"), "sync_skipped")
        self.assertEqual(int(provider_reports[0].get("attempt_count", 0)), 2)
        self.assertEqual(int(provider_reports[0].get("retry_count", 0)), 1)
        self.assertTrue(bool(provider_reports[0].get("retry_exhausted")))
        self.assertEqual(provider_reports[0].get("quality_gate"), "fail")
        self.assertIn(provider_reports[1].get("quality_gate"), {"pass", "warn"})
        self.assertGreaterEqual(int(report.get("quality_failures", 0)), 1)
        self.assertIn("smoke_check", report)
        self.assertFalse(bool(report["smoke_check"]["release_review_allowed"]))

    def test_sync_to_store_records_retry_recovery_and_persists_status(self) -> None:
        root = self.make_test_root()

        class FlakyProvider:
            provider_name = "flaky_source"
            sync_enabled = True
            resolve_enabled = False

            def __init__(self) -> None:
                self.calls = 0

            def load_rows(self) -> list[dict[str, object]]:
                self.calls += 1
                if self.calls < 2:
                    raise RuntimeError("temporary upstream timeout")
                return [
                    {
                        "source_id": "2965321",
                        "match_date": "2026-04-03",
                        "league": "Friendly",
                        "home_team": "A",
                        "away_team": "B",
                        "lineup_known": True,
                        "lineup_updated_at": "2026-04-03 18:00:00",
                        "lineup_freshness_hours": 2,
                    }
                ]

            def sync_report(self) -> dict[str, object]:
                return {"provider_kind": "flaky"}

        chain = AvailabilityProviderChain([FlakyProvider()])
        report = chain.sync_to_store(root, replace=True, retry_backoff_ms=0)

        self.assertEqual(int(report.get("failed_providers", 0)), 0)
        self.assertEqual(int(report.get("imported_providers", 0)), 1)
        self.assertEqual(int(report.get("retry_recovered_providers", 0)), 1)
        self.assertEqual(report["smoke_check"]["status"], "warn")
        self.assertTrue(bool(report["smoke_check"]["release_review_allowed"]))

        provider_report = report.get("provider_reports", [{}])[0]
        self.assertEqual(provider_report.get("status"), "imported")
        self.assertEqual(int(provider_report.get("attempt_count", 0)), 2)
        self.assertEqual(int(provider_report.get("retry_count", 0)), 1)
        self.assertTrue(bool(provider_report.get("recovered_after_retry")))
        self.assertEqual(provider_report.get("attempt_errors"), ["temporary upstream timeout"])
        self.assertIn("recovered_after_retry", provider_report.get("signal_issues", []))

        persisted = C1AvailabilityStore(root).load_sync_status()
        persisted_report = persisted.get("provider_reports", [{}])[0]
        self.assertEqual(int(persisted_report.get("attempt_count", 0)), 2)
        self.assertEqual(int(persisted_report.get("retry_count", 0)), 1)
        self.assertTrue(bool(persisted_report.get("recovered_after_retry")))
        failure_reasons = persisted.get("provider_failure_reasons") or []
        self.assertTrue(any(reason.get("code") == "provider_warning" for reason in failure_reasons if isinstance(reason, dict)))

    def test_api_football_dynamic_fixture_limit(self) -> None:
        provider = ApiFootballAvailabilityProvider(
            fixtures_url="http://127.0.0.1/fixtures",
            max_fixtures=80,
            request_delay_ms=0,
        )
        now = datetime.now()
        issue_fixtures = []
        for idx in range(120):
            dt = now + timedelta(minutes=idx + 1)
            issue_fixtures.append({"fixture": {"id": idx + 1, "date": dt.isoformat()}})
        extra_fixtures = []
        for idx in range(30):
            dt = now + timedelta(days=5, minutes=idx + 1)
            extra_fixtures.append({"fixture": {"id": 1000 + idx, "date": dt.isoformat()}})
        fixtures = issue_fixtures + extra_fixtures
        effective_limit, issue_count = provider._effective_fixture_limit(fixtures)
        self.assertGreaterEqual(issue_count, 100)
        self.assertEqual(effective_limit, len(fixtures))

    def test_sync_marks_api_football_upstream_errors_as_error(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path == "/fixtures":
                    body = json.dumps(
                        {
                            "results": 0,
                            "errors": {"access": "Your account is suspended, check on https://dashboard.api-football.com."},
                            "response": [],
                        }
                    ).encode("utf-8")
                elif parsed.path in {"/lineups", "/injuries"}:
                    body = json.dumps({"response": []}).encode("utf-8")
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), thread.join(timeout=2), server.server_close()))
        root = self.make_test_root()
        chain = AvailabilityProviderChain.from_project_root(
            root,
            config={
                "providers": [
                    {
                        "type": "api_football_source",
                        "enabled": True,
                        "name": "api_football_primary",
                        "url": f"http://127.0.0.1:{server.server_port}/fixtures?date={{today}}",
                        "lineups_url_template": f"http://127.0.0.1:{server.server_port}/lineups?fixture={{fixture_id}}",
                        "injuries_url_template": f"http://127.0.0.1:{server.server_port}/injuries?fixture={{fixture_id}}",
                        "timeout_seconds": 5,
                        "resolve_direct": False,
                    },
                    {"type": "stored_snapshots", "enabled": True},
                ]
            },
        )
        report = chain.sync_to_store(root, replace=False)
        provider_reports = report.get("provider_reports") or []
        self.assertGreaterEqual(len(provider_reports), 1)
        first = provider_reports[0]
        self.assertEqual(first.get("provider_name"), "api_football_primary")
        self.assertEqual(first.get("status"), "error")
        self.assertEqual(first.get("reason"), "upstream_error")
        self.assertTrue(bool(first.get("fixtures_upstream_error")))
        self.assertTrue(bool(first.get("fixtures_account_suspended")))
        self.assertEqual(first.get("quality_gate"), "fail")
        self.assertIn("upstream_error", first.get("quality_issues", []))

    def test_titan_detail_provider_parses_lineup_and_injury(self) -> None:
        provider = TitanDetailAvailabilityProvider(resolve_direct=False, max_matches=5, request_delay_ms=0)
        fake_match = SimpleNamespace(
            match_id="2871746",
            match_date="2026-04-07",
            league="澳超",
            home_team="墨尔本城",
            away_team="中央海岸水手",
        )
        html = """
        <html><body>
          <div id="matchBox2">
            <div class="home">
              <div class="play"></div><div class="play"></div><div class="play"></div><div class="play"></div><div class="play"></div>
              <div class="play"></div><div class="play"></div><div class="play"></div><div class="play"></div><div class="play"></div>
              <div class="play"></div><div class="play"></div><div class="play"></div>
            </div>
            <div class="guest">
              <div class="play"></div><div class="play"></div><div class="play"></div><div class="play"></div><div class="play"></div>
              <div class="play"></div><div class="play"></div><div class="play"></div><div class="play"></div><div class="play"></div>
              <div class="play"></div><div class="play"></div>
            </div>
          </div>
          <div class="backupPlay backupPlay2">
            <div class="home"><div class="play"></div><div class="play"></div></div>
            <div class="guest"><div class="play"></div></div>
          </div>
          <div class="backupPlay hurtPlay">
            <div class="home"><div class="play"></div></div>
            <div class="guest"><div class="play"></div><div class="play"></div><div class="play"></div></div>
          </div>
        </body></html>
        """
        provider._load_titan_matches = lambda: [fake_match]  # type: ignore[method-assign]
        provider._fetch_detail_html = lambda schedule_id: html  # type: ignore[method-assign]

        rows = provider.load_rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertTrue(bool(row.get("lineup_known")))
        self.assertEqual(int(row.get("home_start_count", 0)), 11)
        self.assertEqual(int(row.get("away_start_count", 0)), 11)
        self.assertEqual(int(row.get("home_absent_count", 0)), 1)
        self.assertEqual(int(row.get("away_absent_count", 0)), 3)
        self.assertEqual(str(row.get("provider_kind")), "titan_detail")

    def test_chain_accepts_titan_detail_source_provider(self) -> None:
        root = self.make_test_root()
        chain = AvailabilityProviderChain.from_project_root(
            root,
            config={
                "providers": [
                    {"type": "titan_detail_source", "enabled": True, "name": "titan_detail_primary", "resolve_direct": False}
                ]
            },
        )
        self.assertEqual(len(chain.providers), 1)
        self.assertIsInstance(chain.providers[0], TitanDetailAvailabilityProvider)
        self.assertEqual(chain.providers[0].provider_name, "titan_detail_primary")


if __name__ == "__main__":
    unittest.main()
