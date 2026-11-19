"""Disk benchmark safety tests."""

import threading

from hardinfo.collectors import run_disk_benchmark


def test_benchmark_writes_and_cleans_up():
    result = run_disk_benchmark(1)
    assert result.cancelled is False
    assert result.write_mbps > 0
    assert result.read_mbps > 0
    assert "Запись" in result.summary


def test_benchmark_cancellation_stops_immediately():
    event = threading.Event()
    event.set()
    result = run_disk_benchmark(512, event)
    assert result.cancelled is True
    assert result.write_mbps == 0
    assert result.read_mbps == 0
