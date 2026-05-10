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
        self.assertIn("narrative_review", review["agent_review"])
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

    def test_extract_video_review_frames_adds_offline_visual_analysis(self) -> None:
        from PIL import Image, ImageDraw

        settlement = {
            "match_id": "m-3",
            "home_team": "Alpha",
            "away_team": "Bravo",
            "home_goals": 0,
            "away_goals": 1,
            "result": "客胜",
            "is_correct": False,
            "handicap_is_correct": False,
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            video_path = root / "replay.mp4"
            video_path.write_bytes(b"fake-video")
            review_file = root / "video_reviews.json"
            review_dir = root / "video_review_frames"
            frame_dir = review_dir / "frames_source"
            frame_dir.mkdir(parents=True)
            frame_paths: list[Path] = []
            for index, color in enumerate((40, 110, 210), start=1):
                frame_path = frame_dir / f"frame_{index:04d}.jpg"
                image = Image.new("RGB", (180, 100), (color, color, color))
                draw = ImageDraw.Draw(image)
                draw.rectangle((20 + index * 8, 20, 120, 70), outline=(255 - color, 80, 40), width=4)
                draw.text((10, 8), f"{index}", fill=(255, 255, 255))
                image.save(frame_path)
                frame_paths.append(frame_path)

            def fake_extract(_video_path: Path, _review_id: str, *, interval_seconds: int, max_frames: int):
                frames = [
                    {"index": index, "path": str(path), "timestamp_seconds": (index - 1) * interval_seconds}
                    for index, path in enumerate(frame_paths, start=1)
                ]
                return frames, {"status": "ok", "frame_count": len(frames)}

            with patch.object(core, "STATE_STORE", _VideoReviewStore(settlement)):
                with patch.object(core, "VIDEO_REVIEW_FILE", review_file):
                    with patch.object(core, "VIDEO_REVIEW_DIR", review_dir):
                        with patch("v24_app.core.shutil.which", return_value=None):
                            created = core.create_video_review("m-3", video_path)
                        with patch("v24_app.core._extract_video_review_frames", side_effect=fake_extract):
                            result = core.extract_video_review_frames_now(created["review"]["review_id"], interval_seconds=5)
                            review = core.get_video_review_for_match("m-3")

        self.assertTrue(result["ok"])
        self.assertEqual(review["visual_analysis"]["status"], "ready")
        self.assertEqual(review["visual_analysis"]["usable_frame_count"], 3)
        self.assertGreater(review["visual_analysis"]["avg_motion_score"], 0)
        self.assertGreater(len(review["visual_analysis"]["key_frames"]), 0)
        self.assertEqual(review["agent_review"]["status"], "visual_review_ready")
        self.assertEqual(review["agent_review"]["vision_model_status"], "offline_visual_evidence_ready")
        self.assertTrue(set(review["visual_analysis"]["tags"]) & set(review["agent_review"]["error_causes"]))
        narrative = review["agent_review"]["narrative_review"]
        self.assertEqual(narrative["status"], "ready")
        self.assertTrue(narrative["findings"])
        self.assertIn("Evaluation Agent", narrative["recommendation"])
        self.assertIn("Alpha vs Bravo", narrative["summary_text"])


if __name__ == "__main__":
    unittest.main()
