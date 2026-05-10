from __future__ import annotations

import itertools
import json
import threading
import time
import traceback
from concurrent.futures import CancelledError, Future, ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal, Mapping


TaskMode = Literal["thread", "process"]
TaskStatus = Literal["queued", "running", "success", "failed", "cancelled"]


@dataclass
class BackgroundTaskRecord:
    task_id: str
    key: str
    label: str
    mode: TaskMode
    group: str = "default"
    priority: int = 100
    status: TaskStatus = "queued"
    queued_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    elapsed_seconds: float | None = None
    error: str = ""
    result_summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "key": self.key,
            "label": self.label,
            "mode": self.mode,
            "group": self.group,
            "priority": self.priority,
            "status": self.status,
            "queued_at": self.queued_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "elapsed_seconds": self.elapsed_seconds,
            "error": self.error,
            "result_summary": self.result_summary,
            "metadata": dict(self.metadata),
        }


def summarize_task_result(result: object) -> str:
    if isinstance(result, dict):
        for key in ("summary_text", "message", "status", "reason"):
            value = result.get(key)
            if value:
                return str(value)
        pairs: list[str] = []
        for key in ("ok", "new_settled", "new_parlay_settled", "fetched_finished", "record_count", "sample_count"):
            if key in result:
                pairs.append(f"{key}={result.get(key)}")
        if pairs:
            return " | ".join(pairs)
        return f"dict({len(result)})"
    if isinstance(result, (list, tuple, set)):
        return f"{type(result).__name__}({len(result)})"
    if result is None:
        return "-"
    return str(result)[:160]


def _run_task_callable(func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[Any, float]:
    started = time.perf_counter()
    result = func(*args, **kwargs)
    return result, time.perf_counter() - started


class BackgroundTaskCenter:
    def __init__(
        self,
        *,
        max_thread_workers: int = 4,
        max_process_workers: int = 2,
        dispatcher: Callable[[Callable[[], None]], None] | None = None,
        history_limit: int = 80,
        history_path: Path | str | None = None,
        group_limits: Mapping[str, int] | None = None,
    ) -> None:
        self._max_thread_workers = max(1, int(max_thread_workers))
        self._thread_pool = ThreadPoolExecutor(max_workers=self._max_thread_workers)
        self._process_pool: ProcessPoolExecutor | None = None
        self._max_process_workers = max(1, int(max_process_workers))
        self._group_limits = {
            str(group): max(1, int(limit))
            for group, limit in (group_limits or {}).items()
            if str(group)
        }
        self._default_group_limit = self._max_thread_workers + self._max_process_workers
        self._dispatcher = dispatcher or (lambda callback: callback())
        self._history_limit = max(10, int(history_limit))
        self._history_path = Path(history_path) if history_path is not None else None
        self._counter = itertools.count(1)
        self._lock = threading.RLock()
        self._records: dict[str, BackgroundTaskRecord] = {}
        self._order: list[str] = []
        self._queue: list[str] = []
        self._active_keys: set[str] = set()
        self._futures: dict[str, Future] = {}
        self._pending: dict[str, dict[str, Any]] = {}
        self._running_by_mode: dict[TaskMode, int] = {"thread": 0, "process": 0}
        self._running_by_group: dict[str, int] = {}
        self._shutdown = False
        self._load_history()

    def submit(
        self,
        *,
        key: str,
        label: str,
        func: Callable[..., Any],
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        mode: TaskMode = "thread",
        group: str = "default",
        priority: int = 100,
        allow_duplicate: bool = False,
        metadata: dict[str, Any] | None = None,
        on_success: Callable[[Any, BackgroundTaskRecord], None] | None = None,
        on_error: Callable[[BaseException, BackgroundTaskRecord], None] | None = None,
    ) -> BackgroundTaskRecord | None:
        resolved_key = str(key or "task")
        resolved_mode: TaskMode = "process" if mode == "process" else "thread"
        resolved_group = str(group or "default")
        with self._lock:
            if self._shutdown:
                return None
            if not allow_duplicate and resolved_key in self._active_keys:
                return None
            task_id = f"task-{next(self._counter):06d}"
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record = BackgroundTaskRecord(
                task_id=task_id,
                key=resolved_key,
                label=str(label or resolved_key),
                mode=resolved_mode,
                group=resolved_group,
                priority=int(priority),
                status="queued",
                queued_at=now,
                metadata=dict(metadata or {}),
            )
            self._records[task_id] = record
            self._order.insert(0, task_id)
            self._queue.append(task_id)
            self._active_keys.add(resolved_key)
            self._pending[task_id] = {
                "func": func,
                "args": tuple(args),
                "kwargs": dict(kwargs or {}),
                "on_success": on_success,
                "on_error": on_error,
            }
            self._trim_locked()
            self._schedule_locked()
            self._persist_locked()
        return record

    def cancel_task(self, task_id: str | object, *, reason: str = "cancelled_by_user") -> dict[str, Any] | None:
        resolved_id = str(task_id or "")
        with self._lock:
            record = self._records.get(resolved_id)
            if record is None:
                return None
            if record.status not in {"queued", "running"}:
                return record.as_dict()
            if record.status == "queued":
                if resolved_id in self._queue:
                    self._queue.remove(resolved_id)
                self._pending.pop(resolved_id, None)
                record.status = "cancelled"
                record.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record.error = reason
                record.metadata["cancelled_at"] = record.finished_at
                self._active_keys.discard(record.key)
                self._persist_locked()
                return record.as_dict()
            future = self._futures.get(resolved_id)
            if future is not None and future.cancel():
                record.status = "cancelled"
                record.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record.error = reason
                record.metadata["cancelled_at"] = record.finished_at
                self._active_keys.discard(record.key)
                self._futures.pop(resolved_id, None)
                self._release_running_slot_locked(record)
                self._schedule_locked()
                self._persist_locked()
                return record.as_dict()
            record.metadata["cancel_requested"] = True
            record.metadata["cancel_requested_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record.error = "cancel_requested_running_task_cannot_be_stopped"
            self._persist_locked()
            return record.as_dict()

    def snapshot(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        with self._lock:
            task_ids = list(self._order)
            if limit is not None:
                task_ids = task_ids[: max(0, int(limit))]
            return [self._records[task_id].as_dict() for task_id in task_ids if task_id in self._records]

    def queue_state(self) -> dict[str, Any]:
        with self._lock:
            groups = sorted({*self._group_limits.keys(), *(record.group for record in self._records.values())})
            group_rows: list[dict[str, Any]] = []
            for group in groups:
                records = [record for record in self._records.values() if record.group == group]
                running = sum(1 for record in records if record.status == "running")
                queued = sum(1 for record in records if record.status == "queued")
                success = sum(1 for record in records if record.status == "success")
                failed = sum(1 for record in records if record.status == "failed")
                cancelled = sum(1 for record in records if record.status == "cancelled")
                latest = max(records, key=lambda record: record.queued_at or record.started_at or record.task_id) if records else None
                group_rows.append(
                    {
                        "group": group,
                        "limit": self._group_limits.get(group, self._default_group_limit),
                        "running": running,
                        "queued": queued,
                        "active": running + queued,
                        "success": success,
                        "failed": failed,
                        "cancelled": cancelled,
                        "latest_label": latest.label if latest is not None else "-",
                        "latest_status": latest.status if latest is not None else "-",
                    }
                )
            group_rows.sort(key=lambda row: (int(row["active"]) == 0, str(row["group"])))
            return {
                "thread_running": self._running_by_mode.get("thread", 0),
                "thread_limit": self._max_thread_workers,
                "process_running": self._running_by_mode.get("process", 0),
                "process_limit": self._max_process_workers,
                "groups": group_rows,
                "shutdown": self._shutdown,
            }

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for record in self._records.values() if record.status in {"queued", "running"})

    def shutdown(self) -> None:
        with self._lock:
            self._shutdown = True
            for task_id in list(self._queue):
                record = self._records.get(task_id)
                if record is None:
                    continue
                record.status = "cancelled"
                record.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record.error = record.error or "shutdown_before_dispatch"
                self._active_keys.discard(record.key)
                self._pending.pop(task_id, None)
            self._queue.clear()
            self._persist_locked()
        self._thread_pool.shutdown(wait=False, cancel_futures=True)
        if self._process_pool is not None:
            self._process_pool.shutdown(wait=False, cancel_futures=True)

    def _process_executor(self) -> ProcessPoolExecutor:
        if self._process_pool is None:
            self._process_pool = ProcessPoolExecutor(max_workers=self._max_process_workers)
        return self._process_pool

    def _schedule_locked(self) -> None:
        if self._shutdown:
            return
        while True:
            dispatchable = [
                task_id
                for task_id in self._queue
                if task_id in self._records and self._can_dispatch_locked(self._records[task_id])
            ]
            if not dispatchable:
                return
            task_id = min(
                dispatchable,
                key=lambda item: (
                    int(self._records[item].priority),
                    self._order.index(item) * -1 if item in self._order else 0,
                    item,
                ),
            )
            self._dispatch_locked(task_id)

    def _can_dispatch_locked(self, record: BackgroundTaskRecord) -> bool:
        if record.mode == "process":
            if self._running_by_mode["process"] >= self._max_process_workers:
                return False
        elif self._running_by_mode["thread"] >= self._max_thread_workers:
            return False
        group_limit = self._group_limits.get(record.group, self._default_group_limit)
        return self._running_by_group.get(record.group, 0) < group_limit

    def _dispatch_locked(self, task_id: str) -> None:
        record = self._records.get(task_id)
        pending = self._pending.pop(task_id, None)
        if record is None or pending is None:
            if task_id in self._queue:
                self._queue.remove(task_id)
            return
        if task_id in self._queue:
            self._queue.remove(task_id)
        record.status = "running"
        record.started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._running_by_mode[record.mode] = self._running_by_mode.get(record.mode, 0) + 1
        self._running_by_group[record.group] = self._running_by_group.get(record.group, 0) + 1
        executor = self._thread_pool if record.mode == "thread" else self._process_executor()
        future = executor.submit(_run_task_callable, pending["func"], pending["args"], pending["kwargs"])
        self._futures[task_id] = future
        future.add_done_callback(
            lambda completed: self._complete_future(
                completed,
                task_id=task_id,
                on_success=pending["on_success"],
                on_error=pending["on_error"],
            )
        )

    def _release_running_slot_locked(self, record: BackgroundTaskRecord) -> None:
        self._running_by_mode[record.mode] = max(0, self._running_by_mode.get(record.mode, 0) - 1)
        if record.group in self._running_by_group:
            self._running_by_group[record.group] = max(0, self._running_by_group.get(record.group, 0) - 1)
            if self._running_by_group[record.group] <= 0:
                self._running_by_group.pop(record.group, None)

    def _complete_future(
        self,
        future: Future,
        *,
        task_id: str,
        on_success: Callable[[Any, BackgroundTaskRecord], None] | None,
        on_error: Callable[[BaseException, BackgroundTaskRecord], None] | None,
    ) -> None:
        if future.cancelled():
            with self._lock:
                record = self._records[task_id]
                record.status = "cancelled"
                record.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record.error = record.error or "cancelled"
                self._active_keys.discard(record.key)
                self._futures.pop(task_id, None)
                self._release_running_slot_locked(record)
                self._schedule_locked()
                self._persist_locked()
            return
        try:
            result, elapsed = future.result()
        except CancelledError:
            with self._lock:
                record = self._records[task_id]
                record.status = "cancelled"
                record.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record.error = record.error or "cancelled"
                self._active_keys.discard(record.key)
                self._futures.pop(task_id, None)
                self._release_running_slot_locked(record)
                self._schedule_locked()
                self._persist_locked()
            return
        except BaseException as exc:
            with self._lock:
                record = self._records[task_id]
                record.status = "failed"
                record.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record.error = str(exc)
                record.metadata["traceback"] = traceback.format_exc(limit=6)
                self._active_keys.discard(record.key)
                self._futures.pop(task_id, None)
                self._release_running_slot_locked(record)
                self._schedule_locked()
                self._persist_locked()
                callback_record = BackgroundTaskRecord(**record.as_dict())
            if on_error is not None:
                self._dispatcher(lambda exc=exc, record=callback_record: on_error(exc, record))
            return

        with self._lock:
            record = self._records[task_id]
            record.status = "success"
            record.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record.elapsed_seconds = round(float(elapsed), 4)
            record.result_summary = summarize_task_result(result)
            if record.metadata.get("cancel_requested"):
                record.metadata["cancel_request_completed"] = True
            self._active_keys.discard(record.key)
            self._futures.pop(task_id, None)
            self._release_running_slot_locked(record)
            self._schedule_locked()
            self._persist_locked()
            callback_record = BackgroundTaskRecord(**record.as_dict())
        if on_success is not None:
            self._dispatcher(lambda result=result, record=callback_record: on_success(result, record))

    def _trim_locked(self) -> None:
        if len(self._order) <= self._history_limit:
            return
        removable = self._order[self._history_limit :]
        self._order = self._order[: self._history_limit]
        for task_id in removable:
            record = self._records.get(task_id)
            if record is not None and record.status not in {"queued", "running"}:
                self._records.pop(task_id, None)

    def _load_history(self) -> None:
        if self._history_path is None or not self._history_path.exists():
            return
        try:
            payload = json.loads(self._history_path.read_text(encoding="utf-8"))
        except Exception:
            return
        items = payload.get("items", []) if isinstance(payload, dict) else []
        if not isinstance(items, list):
            return
        loaded: list[BackgroundTaskRecord] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                record = BackgroundTaskRecord(
                    task_id=str(item.get("task_id") or ""),
                    key=str(item.get("key") or "task"),
                    label=str(item.get("label") or item.get("key") or "task"),
                    mode="process" if str(item.get("mode") or "") == "process" else "thread",
                    group=str(item.get("group") or "default"),
                    priority=int(item.get("priority") or 100),
                    status=str(item.get("status") or "queued"),  # type: ignore[arg-type]
                    queued_at=str(item.get("queued_at") or ""),
                    started_at=str(item.get("started_at") or ""),
                    finished_at=str(item.get("finished_at") or ""),
                    elapsed_seconds=float(item["elapsed_seconds"]) if item.get("elapsed_seconds") is not None else None,
                    error=str(item.get("error") or ""),
                    result_summary=str(item.get("result_summary") or ""),
                    metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
                )
            except Exception:
                continue
            if not record.task_id:
                continue
            if record.status in {"queued", "running"}:
                record.status = "cancelled"
                record.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record.error = "interrupted_by_app_restart"
            loaded.append(record)
        with self._lock:
            for record in loaded[: self._history_limit]:
                self._records[record.task_id] = record
                self._order.append(record.task_id)
            self._sync_counter_from_records_locked()
            self._persist_locked()

    def _sync_counter_from_records_locked(self) -> None:
        max_seen = 0
        for task_id in self._records:
            if not task_id.startswith("task-"):
                continue
            try:
                max_seen = max(max_seen, int(task_id.split("-", 1)[1]))
            except Exception:
                continue
        self._counter = itertools.count(max_seen + 1)

    def _persist_locked(self) -> None:
        if self._history_path is None:
            return
        try:
            self._history_path.parent.mkdir(parents=True, exist_ok=True)
            items = [self._records[task_id].as_dict() for task_id in self._order if task_id in self._records]
            payload = {
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "items": items[: self._history_limit],
            }
            tmp_path = self._history_path.with_suffix(self._history_path.suffix + ".tmp")
            tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(self._history_path)
        except Exception:
            return
