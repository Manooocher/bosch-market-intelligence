"""Request scheduler.

Decides WHEN requests happen. Batching, delays, rotation triggers.
No Torob logic. No HTTP logic.
"""

import logging
import random
import time
from dataclasses import dataclass, field

from crawler.config import RateProfile, SchedulerConfig
from crawler.proxy import ProxyManager

logger = logging.getLogger(__name__)


@dataclass
class WorkItem:
    """A single unit of work to be scheduled."""
    url: str
    params: dict = field(default_factory=dict)
    priority: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class BatchResult:
    """Result of processing one batch."""
    items_processed: int = 0
    items_succeeded: int = 0
    items_failed: int = 0
    duration_ms: int = 0
    proxy_rotated: bool = False


class RequestScheduler:
    """Schedules request execution with batching, delays, and rotation triggers.

    The scheduler decides timing. The caller handles actual execution.
    """

    def __init__(
        self,
        profile: RateProfile,
        proxy_manager: ProxyManager,
        config: SchedulerConfig | None = None,
    ):
        self.profile = profile
        self.proxy_manager = proxy_manager
        self.config = config or SchedulerConfig()
        self._items_since_rotation = 0
        self._batch_count = 0
        self._consecutive_errors = 0

    def get_delay(self) -> float:
        """Get delay between requests."""
        return random.uniform(self.profile.delay_min, self.profile.delay_max)

    def get_batch_pause(self) -> float:
        """Get pause duration between batches."""
        pause = random.uniform(
            self.profile.pause_between_batches_min,
            self.profile.pause_between_batches_max,
        )
        if self._batch_count > 0 and self._batch_count % self.profile.long_pause_interval == 0:
            pause += random.uniform(self.profile.long_pause_min, self.profile.long_pause_max)
            logger.info(f"Long pause after {self._batch_count} batches: +{pause:.1f}s")
        return pause

    def should_rotate(self) -> bool:
        """Check if proxy rotation is due."""
        return self.proxy_manager.should_rotate()

    def on_item_complete(self, success: bool) -> None:
        """Notify scheduler that an item completed."""
        self._items_since_rotation += 1
        if success:
            self._consecutive_errors = 0
        else:
            self._consecutive_errors += 1

    def on_batch_complete(self, items_processed: int, items_succeeded: int,
                          duration_ms: int) -> None:
        """Notify scheduler that a batch completed."""
        self._batch_count += 1
        self._items_since_rotation = 0
        logger.info(f"Batch {self._batch_count}: {items_succeeded}/{items_processed} "
                     f"succeeded in {duration_ms/1000:.1f}s")

    def should_slow_down(self) -> bool:
        """Check if adaptive slowdown is needed."""
        if not self.config.adaptive_slowdown_enabled:
            return False
        return self._consecutive_errors >= 3

    def create_batches(self, items: list, batch_size: int = None) -> list[list]:
        """Split items into batches."""
        size = batch_size or self.profile.requests_per_batch
        return [items[i:i + size] for i in range(0, len(items), size)]
