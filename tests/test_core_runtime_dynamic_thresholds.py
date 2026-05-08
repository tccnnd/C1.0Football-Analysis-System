from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app import core


class CoreRuntimeDynamicThresholdTests(unittest.TestCase):
    def setUp(self) -> None:
        core._LIVE_PLAY_THRESHOLD_CACHE["cache_key"] = None
        core._LIVE_PLAY_THRESHOLD_CACHE["thresholds"] = {}
        core._LIVE_PLAY_THRESHOLD_CACHE["meta"] = {}

    def test_negative_ev_and_breaker_raise_thresholds(self) -> None:
        settlements = []
        for index in range(36):
            settlements.append(
                {
                    "timestamp": f"2026-04-10 1{index % 10}:00:00",
                    "is_correct": False,
                    "prediction_confidence": 0.68,
                    "handicap_is_correct": False,
                    "handicap_confidence": 0.67,
                    "total_goals_is_correct": bool(index % 2 == 0),
                    "total_goals_confidence": 0.20,
                    "score_is_correct": False,
                    "score_confidence": 0.12,
                }
            )
        base = dict(core.DEFAULT_PLAY_THRESHOLDS)
        with (
            patch("v24_app.core._settlement_mtime", return_value=101.0),
            patch("v24_app.core._play_thresholds_mtime", return_value=201.0),
            patch("v24_app.core.get_recent_settlements", return_value=settlements),
        ):
            adjusted, meta = core._runtime_dynamic_play_thresholds(base, window=120)

        self.assertGreater(adjusted["1x2"], base["1x2"])
        self.assertGreater(adjusted["handicap"], base["handicap"])
        self.assertTrue(meta["single_gate"]["breaker_on"])
        self.assertGreaterEqual(int(meta["single_gate"]["losing_streak"]), 5)

    def test_positive_ev_can_relax_thresholds(self) -> None:
        settlements = []
        for index in range(52):
            settlements.append(
                {
                    "timestamp": f"2026-04-12 1{index % 10}:00:00",
                    "is_correct": True,
                    "prediction_confidence": 0.58,
                    "handicap_is_correct": True,
                    "handicap_confidence": 0.58,
                    "total_goals_is_correct": bool(index % 3 != 0),
                    "total_goals_confidence": 0.22,
                    "score_is_correct": bool(index % 4 == 0),
                    "score_confidence": 0.11,
                }
            )
        base = dict(core.DEFAULT_PLAY_THRESHOLDS)
        with (
            patch("v24_app.core._settlement_mtime", return_value=102.0),
            patch("v24_app.core._play_thresholds_mtime", return_value=202.0),
            patch("v24_app.core.get_recent_settlements", return_value=settlements),
        ):
            adjusted, meta = core._runtime_dynamic_play_thresholds(base, window=120)

        self.assertLess(adjusted["1x2"], base["1x2"])
        self.assertLess(adjusted["handicap"], base["handicap"])
        self.assertFalse(meta["single_gate"]["breaker_on"])

    def test_runtime_threshold_cache_avoids_repeated_load(self) -> None:
        settlements = [
            {
                "timestamp": "2026-04-15 10:00:00",
                "is_correct": True,
                "prediction_confidence": 0.57,
                "handicap_is_correct": True,
                "handicap_confidence": 0.57,
            }
        ]
        base = dict(core.DEFAULT_PLAY_THRESHOLDS)
        with (
            patch("v24_app.core._settlement_mtime", return_value=103.0),
            patch("v24_app.core._play_thresholds_mtime", return_value=203.0),
            patch("v24_app.core.get_recent_settlements", return_value=settlements) as settlements_mock,
        ):
            core._runtime_dynamic_play_thresholds(base, window=120)
            core._runtime_dynamic_play_thresholds(base, window=120)

        self.assertEqual(settlements_mock.call_count, 1)


if __name__ == "__main__":
    unittest.main()

