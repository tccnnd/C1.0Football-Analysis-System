from __future__ import annotations

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


class _VideoReviewStore:
    def __init__(self, settlement: dict) -> None:
        self.settlement = settlement

    def load_settlements(self) -> list[dict]:
        return [dict(self.settlement)]

    def load_analysis_history(self) -> dict:
        return {}


class CoreVideoReviewTests(unittest.TestCase):
    def test_create_video_review_records_metadata_and_agent_summary(self) -> None:
        settlement = {
            "match_id": "m-1",
            "match_date": "2026-05-10",
            "league": "Test League",
            "home_team": "Alpha",
            "away_team": "Bravo",
            "home_goals": 1,
            "away_goals": 1,
            "result": "平局",
            "is_correct": False,
            "ou_is_correct": False,
            "handicap_is_correct": True,
            "score_is_correct": False,
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            video_path = root / "replay.mp4"
            video_path.write_bytes(b"fake-video")
            review_file = root / "video_reviews.json"
            review_dir = root / "video_review_frames"

            with patch.object(core, "STATE_STORE", _VideoReviewStore(settlement)):
                with patch.object(core, "VIDEO_REVIEW_FILE", review_file):
                    with patch.object(core, "VIDEO_REVIEW_DIR", review_dir):
                        with patch("v24_app.core.shutil.which", return_value=None):
                            result = core.create_video_review("m-1", video_path, notes="manual import")
                            reviews = core.get_video_reviews(limit=10)
                            enriched = core.get_recent_settlements(limit=10)

        self.assertTrue(result["ok"])
        review = result["review"]
        self.assertEqual(review["match_id"], "m-1")
        self.assertEqual(review["video"]["filename"], "replay.mp4")
        self.assertEqual(review["video"]["probe_status"], "ffprobe_unavailable")
        self.assertEqual(review["extraction"]["status"], "not_requested")
        self.assertGreater(len(review["frame_plan"]), 0)
        self.assertEqual(review["agent_review"]["agent"], "VideoReview Agent")
        self.assertEqual(review["agent_review"]["prediction_alignment"], "needs_review")
        self.assertIn("tempo_or_total_goals_miss", review["agent_review"]["error_causes"])
        self.assertEqual(len(reviews), 1)
        self.assertEqual(enriched[0]["video_review"]["review_id"], review["review_id"])
        self.assertEqual(enriched[0]["video_review_status"], "metadata_ready")

    def test_create_video_review_requires_existing_settlement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            video_path = Path(tmp_dir) / "replay.mp4"
            video_path.write_bytes(b"fake-video")
            with patch.object(core, "STATE_STORE", _VideoReviewStore({"match_id": "other"})):
                result = core.create_video_review("missing", video_path)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "settlement_not_found")

    def test_extract_video_review_frames_updates_existing_review(self) -> None:
        settlement = {
            "match_id": "m-2",
            "home_team": "Alpha",
            "away_team": "Bravo",
            "home_goals": 2,
            "away_goals": 0,
            "result": "主胜",
            "is_correct": True,
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            video_path = root / "replay.mp4"
            video_path.write_bytes(b"fake-video")
            review_file = root / "video_reviews.json"
            review_dir = root / "video_review_frames"

            with patch.object(core, "STATE_STORE", _VideoReviewStore(settlement)):
                with patch.object(core, "VIDEO_REVIEW_FILE", review_file):
                    with patch.object(core, "VIDEO_REVIEW_DIR", review_dir):
                        with patch("v24_app.core.shutil.which", return_value=None):
                            created = core.create_video_review("m-2", video_path)
                            result = core.extract_video_review_frames_now(created["review"]["review_id"])
                            review = core.get_video_review_for_match("m-2")

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "ffmpeg_unavailable")
        self.assertEqual(review["extraction"]["status"], "skipped")
        self.assertEqual(review["agent_review"]["status"], "metadata_ready")
        self.assertEqual(review["agent_review"]["frame_count"], 0)


if __name__ == "__main__":
    unittest.main()
