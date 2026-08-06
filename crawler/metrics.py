"""Central metrics collector.

Tracks all crawler statistics.
No business logic.
"""

import json
import logging
import time
from collections import defaultdict
from pathlib import Path

from crawler.config import METRICS_FILE

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and exposes crawler metrics."""

    def __init__(self):
        self._counters = defaultdict(int)
        self._timers = defaultdict(list)
        self._start_time = time.time()

    def record_request(self, mode: str, status: int, duration_ms: int,
                       proxy_session: str = "", retry_count: int = 0) -> None:
        self._counters[f"requests_total"] += 1
        self._counters[f"requests_mode_{mode}"] += 1
        self._counters[f"status_{status}"] += 1

        if status == 200:
            self._counters["success"] += 1
        elif status == 490:
            self._counters["error_490"] += 1
        elif status == 429:
            self._counters["error_429"] += 1
        elif status >= 500:
            self._counters["error_5xx"] += 1

        if retry_count > 0:
            self._counters["retries"] += retry_count

        self._timers[f"latency_{mode}"].append(duration_ms)

    def record_proxy_rotation(self, reason: str) -> None:
        self._counters["proxy_rotations"] += 1
        self._counters[f"rotation_reason_{reason}"] += 1

    def record_batch(self, mode: str, duration_ms: int, items: int) -> None:
        self._counters[f"batches_{mode}"] += 1
        self._timers[f"batch_duration_{mode}"].append(duration_ms)

    def get_summary(self) -> dict:
        elapsed = time.time() - self._start_time
        latency_by_mode = {}
        for key, values in self._timers.items():
            if key.startswith("latency_") and values:
                mode = key.replace("latency_", "")
                latency_by_mode[mode] = {
                    "count": len(values),
                    "avg_ms": int(sum(values) / len(values)),
                    "max_ms": max(values),
                    "min_ms": min(values),
                }

        return {
            "elapsed_seconds": int(elapsed),
            "requests": dict(self._counters),
            "latency": latency_by_mode,
        }

    def write_to_file(self) -> None:
        """Persist metrics to disk."""
        try:
            with open(METRICS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.get_summary(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to write metrics: {e}")

    def write_final_summary(self, mode: str) -> None:
        """Write end-of-run summary."""
        summary = self.get_summary()
        summary["mode"] = mode
        logger.info(f"Run complete: {json.dumps(summary, indent=2)}")
        self.write_to_file()
