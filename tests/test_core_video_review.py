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
        self.assertEqual(review["agent_review"]["evidence_level"], "low")
        self.assertEqual(review["agent_review"]["event_hypotheses"][0]["code"], "low_quality_video_evidence")
        self.assertEqual(review["agent_review"]["recommended_followup"]["code"], "collect_more_video_evidence")
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
        self.assertGreater(review["agent_review"]["evidence_score"], 0)
        self.assertIn(review["agent_review"]["evidence_level"], {"low", "medium", "high"})
        hypothesis_codes = {item["code"] for item in review["agent_review"]["event_hypotheses"]}
        self.assertIn("set_piece_or_transition_risk", hypothesis_codes)
        self.assertIn("recommended_followup", review["agent_review"])
        self.assertTrue(set(review["visual_analysis"]["tags"]) & set(review["agent_review"]["error_causes"]))
        narrative = review["agent_review"]["narrative_review"]
        self.assertEqual(narrative["status"], "ready")
        self.assertTrue(narrative["findings"])
        self.assertIn("event_hypotheses", narrative)
        self.assertIn("Evaluation Agent", narrative["recommendation"])
        self.assertIn("Alpha vs Bravo", narrative["summary_text"])

    def test_video_review_ai_summary_generates_tempo_hypothesis(self) -> None:
        settlement = {
            "match_id": "m-4",
            "home_team": "Alpha",
            "away_team": "Bravo",
            "home_goals": 3,
            "away_goals": 2,
            "result": "主胜",
            "is_correct": False,
            "ou_is_correct": False,
        }
        visual_analysis = {
            "status": "ready",
            "frame_count": 8,
            "usable_frame_count": 8,
            "avg_brightness": 112.0,
            "avg_contrast": 38.0,
            "avg_edge_score": 9.0,
            "avg_motion_score": 21.0,
            "summary_text": "frames 8/8 | brightness 112.0 | contrast 38.0 | motion 21.0",
            "tags": ["high_scene_change"],
            "key_frames": [
                {"index": 2, "timestamp_seconds": 30, "quality": "good", "motion_score": 24.0, "edge_score": 9.5},
                {"index": 5, "timestamp_seconds": 75, "quality": "good", "motion_score": 19.0, "edge_score": 8.2},
            ],
        }

        summary = core._video_review_ai_summary(
            settlement,
            frame_count=8,
            notes="tempo review",
            visual_analysis=visual_analysis,
        )

        hypothesis_codes = {item["code"] for item in summary["event_hypotheses"]}
        self.assertIn("tempo_shift", hypothesis_codes)
        self.assertGreaterEqual(summary["review_confidence"], 0.7)
        self.assertEqual(summary["recommended_followup"]["code"], "annotate_tempo_turning_points")
        self.assertEqual(summary["narrative_review"]["evidence_level"], summary["evidence_level"])

    def test_add_video_review_annotation_updates_agent_memory(self) -> None:
        settlement = {
            "match_id": "m-5",
            "match_date": "2026-05-14",
            "league": "Test League",
            "home_team": "Alpha",
            "away_team": "Bravo",
            "home_goals": 1,
            "away_goals": 0,
            "result": "主胜",
            "is_correct": False,
            "handicap_is_correct": False,
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
                            created = core.create_video_review("m-5", video_path)
                        result = core.add_video_review_annotation(
                            created["review"]["review_id"],
                            event_type="counter_attack",
                            frame_index=3,
                            timestamp_seconds=75,
                            note="fast break before the goal",
                        )
                        review = core.get_video_review_for_match("m-5")

        self.assertTrue(result["ok"])
        self.assertEqual(result["annotation"]["event_type"], "counter_attack")
        self.assertEqual(review["manual_annotation_count"], 1)
        self.assertEqual(review["manual_annotations"][0]["frame_index"], 3)
        agent_review = review["agent_review"]
        self.assertEqual(agent_review["manual_annotation_count"], 1)
        self.assertIn("counter_attack", agent_review["manual_event_tags"])
        hypothesis_codes = {item["code"] for item in agent_review["event_hypotheses"]}
        self.assertIn("set_piece_or_transition_risk", hypothesis_codes)
        self.assertEqual(agent_review["recommended_followup"]["code"], "feed_manual_video_annotations_into_evaluation_agent")
        self.assertIn("review_manual_video_annotations", agent_review["next_actions"])

    def test_export_video_review_fewshot_samples_uses_saved_reviews(self) -> None:
        settlement = {
            "match_id": "m-6",
            "match_date": "2026-05-14",
            "league": "Test League",
            "home_team": "Alpha",
            "away_team": "Bravo",
            "home_goals": 2,
            "away_goals": 2,
            "result": "平局",
            "is_correct": False,
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            video_path = root / "replay.mp4"
            video_path.write_bytes(b"fake-video")
            review_file = root / "video_reviews.json"
            review_dir = root / "video_review_frames"
            fewshot_file = root / "video_review_fewshot_samples.json"

            with patch.object(core, "STATE_STORE", _VideoReviewStore(settlement)):
                with patch.object(core, "VIDEO_REVIEW_FILE", review_file):
                    with patch.object(core, "VIDEO_REVIEW_DIR", review_dir):
                        with patch.object(core, "VIDEO_REVIEW_FEWSHOT_FILE", fewshot_file):
                            with patch("v24_app.core.shutil.which", return_value=None):
                                created = core.create_video_review("m-6", video_path)
                            core.add_video_review_annotation(
                                created["review"]["review_id"],
                                event_type="tempo_shift",
                                timestamp_seconds=58,
                                note="pace changed after substitution",
                            )
                            result = core.export_video_review_fewshot_samples_now(limit=10)

            payload = json.loads(fewshot_file.read_text(encoding="utf-8"))

        self.assertEqual(result["sample_count"], 1)
        self.assertEqual(payload["purpose"], "evaluation_agent_video_fewshot_post_match_review")
        self.assertIn("video_tempo_shift", payload["items"][0]["labels"]["tags"])


if __name__ == "__main__":
    unittest.main()
