from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from c1.data.availability_store import C1AvailabilityStore


class C1AvailabilityBridgeTests(unittest.TestCase):
    def test_resolve_with_source_bridge(self) -> None:
        root = PROJECT_ROOT / "data" / f"tmp_test_c1_bridge_{uuid4().hex}"
        try:
            store = C1AvailabilityStore(root)
            store.import_rows(
                [
                    {
                        "source_id": "api_123",
                        "match_date": "2026-04-05",
                        "league": "Serie A",
                        "home_team": "Hellas Verona",
                        "away_team": "Fiorentina",
                        "lineup_known": False,
                    }
                ],
                replace=True,
            )
            bridge_payload = {
                "updated_at": "2026-04-05 01:00:00",
                "source_id_map": {"titan_456": "api_123"},
            }
            store.source_bridge_file.write_text(json.dumps(bridge_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            resolved = store.resolve_for_match(
                {
                    "source_id": "titan_456",
                    "match_date": "2026-04-05",
                    "league": "意甲",
                    "home_team": "维罗纳",
                    "away_team": "佛罗伦萨",
                }
            )
            self.assertEqual(str(resolved.get("source_id")), "api_123")
        finally:
            if root.exists():
                shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
