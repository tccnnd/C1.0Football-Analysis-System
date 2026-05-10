from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app import core


class _StatsBombStore:
    def load_settlements(self) -> list[dict]:
        return [
            {
                "match_id": "2024-04-14|1. Bundesliga|Bayer Leverkusen|Werder Bremen",
                "match_date": "2024-04-14",
                "league": "1. Bundesliga",
                "home_team": "Bayer Leverkusen",
                "away_team": "Werder Bremen",
                "is_correct": False,
            }
        ]

    def load_analysis_history(self) -> dict:
        return {}


class CoreStatsBombEnrichmentTests(unittest.TestCase):
    def test_recent_settlements_attach_statsbomb_event_summary_by_match_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statsbomb_file = Path(temp_dir) / "statsbomb_event_summaries.json"
            statsbomb_file.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "match_id": "statsbomb:3895302",
                                "source_match_id": 3895302,
                                "match_date": "2024-04-14",
                                "league": "1. Bundesliga",
                                "home_team": "Bayer Leverkusen",
                                "away_team": "Werder Bremen",
                                "source_url": "https://github.com/statsbomb/open-data",
                                "event_summary": {
                                    "event_count": 4223,
                                    "team_stats": {
                                        "Bayer Leverkusen": {"xg": 4.02, "shots": 19, "goals": 5},
                                        "Werder Bremen": {"xg": 0.28, "shots": 8, "goals": 0},
                                    },
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(core, "STATE_STORE", _StatsBombStore()):
                with patch.object(core, "STATSBOMB_EVENT_SUMMARIES_FILE", statsbomb_file):
                    rows = core.get_recent_settlements(limit=10)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["statsbomb_source_match_id"], 3895302)
        self.assertEqual(rows[0]["statsbomb_event_summary"]["event_count"], 4223)
        self.assertEqual(rows[0]["statsbomb_event_summary"]["team_stats"]["Bayer Leverkusen"]["xg"], 4.02)


if __name__ == "__main__":
    unittest.main()
