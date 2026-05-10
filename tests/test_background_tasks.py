from __future__ import annotations

import json
import os
import sys
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.background_tasks import BackgroundTaskCenter, summarize_task_result
from v24_app.ui_modules import build_background_task_detail_lines, build_background_task_rows, build_background_task_summary


def _sample_process_task(value: int) -> dict[str, object]:
    return {"ok": True, "value": value, "pid": os.getpid(), "summary_text": f"value={value}"}


class BackgroundTaskCenterTests(unittest.TestCase):
    def test_thread_task_records_success_and_summary(self) -> None:
        completed = threading.Event()
        payloads: list[dict[str, object]] = []
        center = BackgroundTaskCenter(dispatcher=lambda callback: callback())
        try:
            record = center.submit(
                key="sample",
                label="Sample",
                func=lambda: {"ok": True, "new_settled": 2},
                on_success=lambda result, _record: (payloads.append(result), completed.set()),
            )

            self.assertIsNotNone(record)
            self.assertTrue(completed.wait(5))
            snapshot = center.snapshot()
            self.assertEqual(snapshot[0]["status"], "success")
            self.assertIn("new_settled=2", snapshot[0]["result_summary"])
            self.assertEqual(payloads[0]["new_settled"], 2)
        finally:
            center.shutdown()

    def test_duplicate_key_is_rejected_while_running(self) -> None:
        release = threading.Event()
        center = BackgroundTaskCenter(dispatcher=lambda callback: callback())
        try:
            first = center.submit(key="same", label="Same", func=lambda: release.wait(5))
            second = center.submit(key="same", label="Same Again", func=lambda: True)

            self.assertIsNotNone(first)
            self.assertIsNone(second)
            release.set()
        finally:
            center.shutdown()

    def test_cancel_queued_task_marks_cancelled(self) -> None:
        release = threading.Event()
        center = BackgroundTaskCenter(dispatcher=lambda callback: callback(), max_thread_workers=1)
        try:
            first = center.submit(key="first", label="First", func=lambda: release.wait(5))
            second = center.submit(key="second", label="Second", func=lambda: True)
            self.assertIsNotNone(first)
            self.assertIsNotNone(second)
            second_snapshot = next(item for item in center.snapshot() if item["task_id"] == second.task_id)
            self.assertEqual(second_snapshot["status"], "queued")

            cancelled = center.cancel_task(second.task_id)

            self.assertIsNotNone(cancelled)
            self.assertEqual(cancelled["status"], "cancelled")
            self.assertEqual(cancelled["error"], "cancelled_by_user")
            release.set()
        finally:
            center.shutdown()

    def test_priority_dispatches_higher_priority_before_older_queued_task(self) -> None:
        release = threading.Event()
        completed = threading.Event()
        executed: list[str] = []
        center = BackgroundTaskCenter(dispatcher=lambda callback: callback(), max_thread_workers=1)

        def blocked() -> bool:
            executed.append("first")
            return release.wait(5)

        def marker(name: str) -> str:
            executed.append(name)
            if len(executed) >= 3:
                completed.set()
            return name

        try:
            first = center.submit(key="first", label="First", func=blocked, priority=100)
            low = center.submit(key="low", label="Low", func=marker, args=("low",), priority=200)
            high = center.submit(key="high", label="High", func=marker, args=("high",), priority=10)
            self.assertIsNotNone(first)
            self.assertIsNotNone(low)
            self.assertIsNotNone(high)

            release.set()

            self.assertTrue(completed.wait(5))
            self.assertEqual(executed[:3], ["first", "high", "low"])
        finally:
            center.shutdown()

    def test_group_limit_keeps_same_group_queued_while_other_group_runs(self) -> None:
        first_started = threading.Event()
        release = threading.Event()
        other_started = threading.Event()
        center = BackgroundTaskCenter(
            dispatcher=lambda callback: callback(),
            max_thread_workers=2,
            group_limits={"model": 1},
        )

        def first_model() -> bool:
            first_started.set()
            return release.wait(5)

        def second_model() -> bool:
            return True

        def other_group() -> bool:
            other_started.set()
            return True

        try:
            first = center.submit(key="model-1", label="Model 1", func=first_model, group="model")
            second = center.submit(key="model-2", label="Model 2", func=second_model, group="model")
            other = center.submit(key="other", label="Other", func=other_group, group="default")
            self.assertIsNotNone(first)
            self.assertIsNotNone(second)
            self.assertIsNotNone(other)
            self.assertTrue(first_started.wait(5))
            self.assertTrue(other_started.wait(5))

            snapshot = {item["task_id"]: item for item in center.snapshot()}
            self.assertEqual(snapshot[second.task_id]["status"], "queued")
            release.set()
        finally:
            center.shutdown()

    def test_cancel_running_task_records_request_without_force_stop(self) -> None:
        started = threading.Event()
        release = threading.Event()

        def worker() -> bool:
            started.set()
            return release.wait(5)

        center = BackgroundTaskCenter(dispatcher=lambda callback: callback(), max_thread_workers=1)
        try:
            record = center.submit(key="running", label="Running", func=worker)
            self.assertIsNotNone(record)
            self.assertTrue(started.wait(5))

            requested = center.cancel_task(record.task_id)

            self.assertIsNotNone(requested)
            self.assertEqual(requested["status"], "running")
            self.assertTrue(requested["metadata"]["cancel_requested"])
            self.assertEqual(requested["error"], "cancel_requested_running_task_cannot_be_stopped")
            release.set()
        finally:
            center.shutdown()

    def test_process_task_uses_process_mode(self) -> None:
        completed = threading.Event()
        payloads: list[dict[str, object]] = []
        center = BackgroundTaskCenter(dispatcher=lambda callback: callback(), max_process_workers=1)
        try:
            record = center.submit(
                key="process_sample",
                label="Process Sample",
                func=_sample_process_task,
                args=(7,),
                mode="process",
                on_success=lambda result, _record: (payloads.append(result), completed.set()),
            )

            self.assertIsNotNone(record)
            self.assertTrue(completed.wait(15))
            self.assertEqual(payloads[0]["value"], 7)
            self.assertEqual(center.snapshot()[0]["mode"], "process")
        finally:
            center.shutdown()

    def test_ui_task_rows_and_summary(self) -> None:
        tasks = [
            {
                "task_id": "t1",
                "label": "A",
                "mode": "thread",
                "group": "recovery",
                "priority": 20,
                "status": "running",
                "started_at": "2026-05-10 10:00:00",
            },
            {
                "task_id": "t2",
                "label": "B",
                "mode": "process",
                "group": "model",
                "priority": 160,
                "status": "failed",
                "error": "boom",
                "elapsed_seconds": 1.2,
            },
        ]

        summary = build_background_task_summary(tasks)
        rows = build_background_task_rows(tasks)

        self.assertEqual(summary["running"], 1)
        self.assertEqual(summary["failed"], 1)
        self.assertIn("运行中", rows[0]["title"])
        self.assertEqual(rows[0]["task_id"], "t1")
        self.assertTrue(rows[0]["can_cancel"])
        self.assertIn("赛果回收", rows[0]["body"])
        self.assertIn("P20", rows[0]["body"])
        self.assertIn("进程", rows[1]["body"])
        self.assertIn("boom", rows[1]["body"])

    def test_build_background_task_detail_lines_includes_metadata_and_traceback(self) -> None:
        lines = build_background_task_detail_lines(
            {
                "task_id": "t9",
                "key": "sample",
                "label": "Sample",
                "mode": "process",
                "group": "model",
                "priority": 160,
                "status": "failed",
                "queued_at": "2026-05-10 09:59:59",
                "started_at": "2026-05-10 10:00:00",
                "finished_at": "2026-05-10 10:00:03",
                "elapsed_seconds": 3.25,
                "error": "boom",
                "result_summary": "-",
                "metadata": {"trigger": "manual", "traceback": "Traceback line"},
            }
        )
        text = "\n".join(lines)
        self.assertIn("后台任务详情", text)
        self.assertIn("任务ID: t9", text)
        self.assertIn("进程", text)
        self.assertIn("模型任务", text)
        self.assertIn("P160", text)
        self.assertIn("入队时间", text)
        self.assertIn("boom", text)
        self.assertIn("manual", text)
        self.assertIn("Traceback line", text)

    def test_summarize_task_result_prefers_known_fields(self) -> None:
        self.assertEqual(summarize_task_result({"summary_text": "done", "ok": True}), "done")
        self.assertIn("ok=True", summarize_task_result({"ok": True, "record_count": 3}))

    def test_task_history_persists_across_centers(self) -> None:
        completed = threading.Event()
        with TemporaryDirectory() as tmp_dir:
            history_path = Path(tmp_dir) / "background_tasks.json"
            center = BackgroundTaskCenter(dispatcher=lambda callback: callback(), history_path=history_path)
            try:
                center.submit(
                    key="persisted",
                    label="Persisted",
                    func=lambda: {"summary_text": "stored"},
                    on_success=lambda _result, _record: completed.set(),
                )
                self.assertTrue(completed.wait(5))
            finally:
                center.shutdown()

            reloaded = BackgroundTaskCenter(dispatcher=lambda callback: callback(), history_path=history_path)
            try:
                snapshot = reloaded.snapshot()
                self.assertEqual(snapshot[0]["key"], "persisted")
                self.assertEqual(snapshot[0]["status"], "success")
                self.assertEqual(snapshot[0]["result_summary"], "stored")
            finally:
                reloaded.shutdown()

    def test_running_history_is_marked_cancelled_on_restart(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            history_path = Path(tmp_dir) / "background_tasks.json"
            history_path.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "task_id": "task-000009",
                                "key": "stale",
                                "label": "Stale",
                                "mode": "process",
                                "status": "running",
                                "started_at": "2026-05-10 10:00:00",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            center = BackgroundTaskCenter(dispatcher=lambda callback: callback(), history_path=history_path)
            try:
                snapshot = center.snapshot()
                self.assertEqual(snapshot[0]["status"], "cancelled")
                self.assertEqual(snapshot[0]["error"], "interrupted_by_app_restart")
            finally:
                center.shutdown()


if __name__ == "__main__":
    unittest.main()
