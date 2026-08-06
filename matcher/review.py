"""Review queue management and export.

Generates CSV files for manual review of uncertain matches.
"""

import csv
import logging
from pathlib import Path

from matcher.store import WatchListStore

logger = logging.getLogger(__name__)


def export_review_queue(store: WatchListStore, output_path: str | Path) -> int:
    """Export pending review items to CSV.

    Returns the number of items exported.
    """
    output_path = Path(output_path)
    items = store.get_review_queue()

    if not items:
        logger.info("No pending review items to export.")
        return 0

    fieldnames = [
        "nabkade_product_id", "nabkade_title", "nabkade_url",
        "nabkade_price", "confidence_score", "confidence_level",
        "review_reason", "candidate_list", "status",
        "reviewer", "notes", "created_at",
    ]

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for item in items:
            writer.writerow(item)

    logger.info("Exported %d review items to %s", len(items), output_path)
    return len(items)
