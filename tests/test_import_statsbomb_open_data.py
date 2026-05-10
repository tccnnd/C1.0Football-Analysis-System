from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import import_statsbomb_open_data as importer


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fake_match(match_id: int = 1001) -> dict:
    return {
        "match_id": match_id,
        "match_date": "2024-04-14",
        "kick_off": "17:30:00.000",
        "competition": {"competition_id": 9, "competition_name": "1. Bundesliga"},
        "season": {"season_id": 281, "season_name": "2023/2024"},
        "home_team": {"home_team_name": "Bayer Leverkusen"},
        "away_team": {"away_team_name": "Werder Bremen"},
        "home_score": 2,
        "away_score": 1,
        "match_status": "available",
        "match_status_360": "available",
        "competition_stage": {"name": "Regular Season"},
    }


def fake_events() -> list[dict]:
    return [
        {
            "type": {"name": "Shot"},
            "team": {"name": "Bayer Leverkusen"},
            "player": {"name": "Florian Wirtz"},
            "minute": 24,
            "shot": {"statsbomb_xg": 0.32, "outcome": {"name": "Goal"}},
        },
        {
            "type": {"name": "Shot"},
            "team": {"name": "Werder Bremen"},
            "player": {"name": "Marvin Ducksch"},
            "minute": 35,
            "shot": {"statsbomb_xg": 0.18, "outcome": {"name": "Saved"}},
        },
        {"type": {"name": "Pass"}, "team": {"name": "Bayer Leverkusen"}},
        {"type": {"name": "Pass"}, "team": {"name": "Bayer Leverkusen"}},
        {"type": {"name": "Carry"}, "team": {"name": "Werder Bremen"}},
        {"type": {"name": "Pressure"}, "team": {"name": "Werder Bremen"}},
        {
            "type": {"name": "Foul Committed"},
            "team": {"name": "Werder Bremen"},
            "foul_committed": {"card": {"name": "Yellow Card"}},
        },
        {
            "type": {"name": "Bad Behaviour"},
            "team": {"name": "Bayer Leverkusen"},
            "bad_behaviour": {"card": {"name": "Red Card"}},
        },
        {"type": {"name": "Substitution"}, "team": {"name": "Bayer Leverkusen"}},
    ]


class ImportStatsBombOpenDataTests(unittest.TestCase):
    def test_summarize_events_extracts_team_stats_and_goals(self) -> None:
        summary = importer.summarize_events(fake_match(), fake_events())

        home = summary["team_stats"]["Bayer Leverkusen"]
        away = summary["team_stats"]["Werder Bremen"]
        self.assertEqual(summary["event_count"], 9)
        self.assertEqual(home["shots"], 1)
        self.assertEqual(home["goals"], 1)
        self.assertEqual(home["passes"], 2)
        self.assertEqual(home["substitutions"], 1)
        self.assertEqual(home["red_cards"], 1)
        self.assertEqual(away["shots"], 1)
        self.assertEqual(away["shots_on_target"], 1)
        self.assertEqual(away["carries"], 1)
        self.assertEqual(away["pressures"], 1)
        self.assertEqual(away["yellow_cards"], 1)
        self.assertEqual(summary["first_goal_minute"], 24)
        self.assertEqual(summary["goals"][0]["player"], "Florian Wirtz")
        self.assertEqual(summary["top_shooters"][0]["player"], "Florian Wirtz")

    def test_convert_match_keeps_statsbomb_identity_and_score(self) -> None:
        converted = importer.convert_match(fake_match(), fake_events())

        self.assertEqual(converted["match_id"], "statsbomb:1001")
        self.assertEqual(converted["source_match_id"], 1001)
        self.assertEqual(converted["match_time"], "17:30")
        self.assertEqual(converted["league"], "1. Bundesliga")
        self.assertEqual(converted["home_team"], "Bayer Leverkusen")
        self.assertEqual(converted["away_goals"], 1)
        self.assertEqual(converted["event_summary"]["event_type_counts"]["Shot"], 2)

    def test_offline_import_writes_summary_and_audit_with_filters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            offline_dir = root / "offline"
            write_json(
                offline_dir / "competitions.json",
                [
                    {
                        "competition_id": 9,
                        "season_id": 281,
                        "competition_name": "1. Bundesliga",
                        "season_name": "2023/2024",
                    },
                    {
                        "competition_id": 2,
                        "season_id": 27,
                        "competition_name": "Premier League",
                        "season_name": "2015/2016",
                    },
                ],
            )
            write_json(offline_dir / "matches" / "9" / "281.json", [fake_match(1001), fake_match(1002)])
            write_json(offline_dir / "events" / "1001.json", fake_events())

            result = importer.import_statsbomb_open_data(
                project_root=root,
                offline_dir=offline_dir,
                competition_id=9,
                season_id=281,
                limit_matches=1,
            )

            self.assertEqual(result["records"], 1)
            self.assertEqual(result["failure_count"], 0)
            summary_path = root / "data" / "state" / "statsbomb_event_summaries.json"
            audit_path = root / "data" / "state" / "statsbomb_import_audit.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["source"], importer.SOURCE_NAME)
            self.assertEqual(len(summary["items"]), 1)
            self.assertEqual(summary["items"][0]["event_summary"]["event_count"], 9)
            self.assertEqual(audit["records"], 1)
            self.assertEqual(audit["total_events"], 9)
            self.assertEqual(audit["competition_counts"]["1. Bundesliga"], 1)


if __name__ == "__main__":
    unittest.main()
