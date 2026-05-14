from __future__ import annotations

import json
import os
import sys
import tempfile
import time
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


class CoreStatsBombStateCacheTests(unittest.TestCase):
    def tearDown(self) -> None:
        core.invalidate_statsbomb_state_cache()

    def test_statsbomb_event_baseline_uses_mtime_cache_and_reloads_on_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "statsbomb_event_baseline.json"
            path.write_text(json.dumps({"items": [{"match_id": "a"}]}), encoding="utf-8")
            with patch.object(core, "STATSBOMB_EVENT_BASELINE_FILE", path):
                first = core.get_statsbomb_event_baseline()
                second = core.get_statsbomb_event_baseline()

                self.assertIs(first, second)
                self.assertEqual(second["items"][0]["match_id"], "a")

                path.write_text(json.dumps({"items": [{"match_id": "b"}]}), encoding="utf-8")
                new_time = time.time() + 5
                os.utime(path, (new_time, new_time))

                changed = core.get_statsbomb_event_baseline()

                self.assertIsNot(changed, first)
                self.assertEqual(changed["items"][0]["match_id"], "b")

    def test_statsbomb_fewshot_memory_cache_can_be_invalidated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "statsbomb_sandbox_fewshot_samples.json"
            path.write_text(json.dumps({"items": [{"id": "old"}]}), encoding="utf-8")
            with patch.object(core, "STATSBOMB_SANDBOX_FEWSHOT_FILE", path):
                first = core.get_statsbomb_sandbox_fewshot_memory()
                path.write_text(json.dumps({"items": [{"id": "new"}]}), encoding="utf-8")
                core.invalidate_statsbomb_state_cache(path)

                changed = core.get_statsbomb_sandbox_fewshot_memory()

                self.assertIsNot(changed, first)
                self.assertEqual(changed["items"][0]["id"], "new")

    def test_statsbomb_review_training_samples_uses_shared_state_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "statsbomb_review_training_samples.json"
            path.write_text(json.dumps({"summary": {"sample_count": 2}, "items": [{"match_id": "m1"}]}), encoding="utf-8")
            with patch.object(core, "STATSBOMB_REVIEW_TRAINING_FILE", path):
                first = core.get_statsbomb_review_training_samples()
                second = core.get_statsbomb_review_training_samples()

                self.assertIs(first, second)
                self.assertEqual(second["summary"]["sample_count"], 2)

    def test_statsbomb_state_cache_returns_empty_for_missing_or_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            with patch.object(core, "STATSBOMB_EVENT_BASELINE_FILE", path):
                self.assertEqual(core.get_statsbomb_event_baseline(), {})

            path.write_text("[1, 2, 3]", encoding="utf-8")
            with patch.object(core, "STATSBOMB_EVENT_BASELINE_FILE", path):
                self.assertEqual(core.get_statsbomb_event_baseline(), {})


if __name__ == "__main__":
    unittest.main()
