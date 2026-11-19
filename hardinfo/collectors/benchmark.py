"""Cancellable disk speed benchmark with a hard size limit."""

import logging
import os
import tempfile
import threading
import time

from PySide6.QtCore import QThread, Signal

from hardinfo.constants import (
    DISK_BENCHMARK_BLOCK_BYTES,
    DISK_BENCHMARK_MAX_SIZE_MB,
    DISK_BENCHMARK_SIZE_MB,
)
from hardinfo.models.health import DiskBenchmarkResult


def run_disk_benchmark(
    size_mb: int = DISK_BENCHMARK_SIZE_MB,
    cancel_event: threading.Event | None = None,
    block_bytes: int = DISK_BENCHMARK_BLOCK_BYTES,
) -> DiskBenchmarkResult:
    """Write and read a temporary file, deleting it in every exit path."""
    size_mb = max(1, min(int(size_mb), DISK_BENCHMARK_MAX_SIZE_MB))
    cancel_event = cancel_event or threading.Event()
    block_bytes = max(1024, int(block_bytes))
    blocks = (size_mb * 1024 * 1024) // block_bytes
    payload = os.urandom(block_bytes)
    path = ""
    started = time.perf_counter()
    written = 0
    read = 0

    try:
        with tempfile.NamedTemporaryFile(prefix="hardinfo_bench_", delete=False) as handle:
            path = handle.name
            for _ in range(blocks):
                if cancel_event.is_set():
                    break
                handle.write(payload)
                written += len(payload)

        if not cancel_event.is_set():
            with open(path, "rb", buffering=0) as handle:
                while True:
                    if cancel_event.is_set():
                        break
                    chunk = handle.read(block_bytes)
                    if not chunk:
                        break
                    read += len(chunk)

        duration = max(time.perf_counter() - started, 0.001)
        return DiskBenchmarkResult(
            size_mb=size_mb,
            read_mbps=read / (1024**2) / duration,
            write_mbps=written / (1024**2) / duration,
            duration_seconds=duration,
            cancelled=cancel_event.is_set(),
        )
    finally:
        if path:
            try:
                os.remove(path)
            except OSError as exc:
                logging.debug("[SYSTEM] Benchmark temp file not removed: %s", exc)


class DiskBenchmarkThread(QThread):
    """Runs the benchmark off the GUI thread and supports cancellation."""

    progress_signal = Signal(int)
    finished_signal = Signal(object)
    error_signal = Signal(str)

    def __init__(self, size_mb: int = DISK_BENCHMARK_SIZE_MB):
        super().__init__()
        self.size_mb = size_mb
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def run(self) -> None:
        try:
            self.progress_signal.emit(10)
            result = run_disk_benchmark(self.size_mb, self._cancel)
            self.progress_signal.emit(100)
            self.finished_signal.emit(result)
        except Exception as exc:  # pragma: no cover - defensive GUI guard
            logging.error("[ERROR] disk benchmark failed: %s", exc)
            self.error_signal.emit(str(exc))
