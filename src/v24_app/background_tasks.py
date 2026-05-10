from __future__ import annotations

import itertools
import threading
import time
import traceback
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Literal


TaskMode = Literal["thread", "process"]
TaskStatus = Literal["queued", "running", "success", "failed", "cancelled"]


@dataclass
class BackgroundTaskRecord:
    task_id: str
    key: str
    label: str
    mode: TaskMode
    status: TaskStatus = "queued"
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
            "status": self.status,
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
    ) -> None:
        self._thread_pool = ThreadPoolExecutor(max_workers=max(1, int(max_thread_workers)))
        self._process_pool: ProcessPoolExecutor | None = None
        self._max_process_workers = max(1, int(max_process_workers))
        self._dispatcher = dispatcher or (lambda callback: callback())
        self._history_limit = max(10, int(history_limit))
        self._counter = itertools.count(1)
        self._lock = threading.RLock()
        self._records: dict[str, BackgroundTaskRecord] = {}
        self._order: list[str] = []
        self._active_keys: set[str] = set()

    def submit(
        self,
        *,
        key: str,
        label: str,
        func: Callable[..., Any],
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        mode: TaskMode = "thread",
        allow_duplicate: bool = False,
        metadata: dict[str, Any] | None = None,
        on_success: Callable[[Any, BackgroundTaskRecord], None] | None = None,
        on_error: Callable[[BaseException, BackgroundTaskRecord], None] | None = None,
    ) -> BackgroundTaskRecord | None:
        resolved_key = str(key or "task")
        with self._lock:
            if not allow_duplicate and resolved_key in self._active_keys:
                return None
            task_id = f"task-{next(self._counter):06d}"
            record = BackgroundTaskRecord(
                task_id=task_id,
                key=resolved_key,
                label=str(label or resolved_key),
                mode=mode,
                status="running",
                started_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                metadata=dict(metadata or {}),
            )
            self._records[task_id] = record
            self._order.insert(0, task_id)
            self._active_keys.add(resolved_key)
            self._trim_locked()

        call_kwargs = dict(kwargs or {})
        executor = self._thread_pool if mode == "thread" else self._process_executor()
        future = executor.submit(_run_task_callable, func, args, call_kwargs)
        future.add_done_callback(
            lambda completed: self._complete_future(
                completed,
                task_id=task_id,
                on_success=on_success,
                on_error=on_error,
            )
        )
        return record

    def snapshot(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        with self._lock:
            task_ids = list(self._order)
            if limit is not None:
                task_ids = task_ids[: max(0, int(limit))]
            return [self._records[task_id].as_dict() for task_id in task_ids if task_id in self._records]

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for record in self._records.values() if record.status in {"queued", "running"})

    def shutdown(self) -> None:
        self._thread_pool.shutdown(wait=False, cancel_futures=True)
        if self._process_pool is not None:
            self._process_pool.shutdown(wait=False, cancel_futures=True)

    def _process_executor(self) -> ProcessPoolExecutor:
        if self._process_pool is None:
            self._process_pool = ProcessPoolExecutor(max_workers=self._max_process_workers)
        return self._process_pool

    def _complete_future(
        self,
        future: Future,
        *,
        task_id: str,
        on_success: Callable[[Any, BackgroundTaskRecord], None] | None,
        on_error: Callable[[BaseException, BackgroundTaskRecord], None] | None,
    ) -> None:
        try:
            result, elapsed = future.result()
        except BaseException as exc:
            with self._lock:
                record = self._records[task_id]
                record.status = "failed"
                record.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record.error = str(exc)
                record.metadata["traceback"] = traceback.format_exc(limit=6)
                self._active_keys.discard(record.key)
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
            self._active_keys.discard(record.key)
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
