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

from v24_app.storage.state_store import StateStore


class StateStoreRecoveryRunTests(unittest.TestCase):
    def test_upsert_result_recovery_run_updates_existing_record(self) -> None:
        root = PROJECT_ROOT / "data" / f"tmp_test_recovery_runs_{uuid4().hex}"
        try:
            store = StateStore(root)
            store.upsert_result_recovery_run(
                {
                    "run_id": "run-1",
                    "status": "running",
                    "started_at": "2026-05-09 20:00:00",
                }
            )
            store.upsert_result_recovery_run(
                {
                    "run_id": "run-1",
                    "status": "success",
                    "finished_at": "2026-05-09 20:00:02",
                    "new_settled": 2,
                }
            )

            items = store.load_result_recovery_runs()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["status"], "success")
            self.assertEqual(items[0]["started_at"], "2026-05-09 20:00:00")
            self.assertEqual(items[0]["new_settled"], 2)

            payload = json.loads(store.result_recovery_runs_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["items"][0]["run_id"], "run-1")
        finally:
            if root.exists():
                shutil.rmtree(root, ignore_errors=True)

    def test_save_result_recovery_runs_applies_limit(self) -> None:
        root = PROJECT_ROOT / "data" / f"tmp_test_recovery_runs_{uuid4().hex}"
        try:
            store = StateStore(root)
            store.save_result_recovery_runs(
                [{"run_id": f"run-{index}", "status": "success"} for index in range(5)],
                limit=3,
            )
            self.assertEqual(
                [item["run_id"] for item in store.load_result_recovery_runs()],
                ["run-2", "run-3", "run-4"],
            )
        finally:
            if root.exists():
                shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
