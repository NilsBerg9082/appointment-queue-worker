"""Rate-limited concurrent consumer for appointment workflow jobs."""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from typing import Any, Mapping

import infrai
from appointment_workflow import AppointmentJob, plan_notification


QUEUE_NAME = "appointments"


class RateLimiter:
    def __init__(self, operations_per_second: float) -> None:
        if operations_per_second <= 0:
            raise ValueError("operations_per_second must be positive")
        self._interval = 1.0 / operations_per_second
        self._next_slot = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_slot - now)
            self._next_slot = max(now, self._next_slot) + self._interval
        if delay:
            time.sleep(delay)


def process_message(message: Mapping[str, Any], limiter: RateLimiter) -> None:
    job = AppointmentJob.from_payload(message["payload"])
    limiter.wait()
    notification = plan_notification(job)
    print(json.dumps(asdict(notification), sort_keys=True), flush=True)
    infrai.queue.ack(queue=QUEUE_NAME, message_id=str(message["message_id"]))


def run_once(concurrency: int, operations_per_second: float) -> int:
    batch = infrai.queue.consume(
        queue=QUEUE_NAME,
        max_messages=concurrency,
        visibility_timeout=60,
    )
    messages = batch.get("messages", []) if isinstance(batch, dict) else []
    limiter = RateLimiter(operations_per_second)
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        list(pool.map(lambda item: process_message(item, limiter), messages))
    return len(messages)


def main() -> None:
    concurrency = int(os.environ.get("WORKER_CONCURRENCY", "4"))
    operations_per_second = float(os.environ.get("WORKER_RATE", "2"))
    processed = run_once(concurrency, operations_per_second)
    print(f"processed={processed}")


if __name__ == "__main__":
    main()
