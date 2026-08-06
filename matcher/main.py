"""Product Matcher — main orchestrator.

Loads datasets, runs the matching pipeline, stores results, generates reports.

Usage:
    python -m matcher.main
"""

import csv
import json
import logging
import sys
import time
from pathlib import Path

from matcher.candidate import generate_candidates
from matcher.confidence import classify_confidence
from matcher.index import MatchIndex
from matcher.qa import generate_qa_report
from matcher.review import export_review_queue
from matcher.scorer import score_all_candidates
from matcher.store import WatchListStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("matcher.main")

# ── Paths ───────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
TOROB_CSV = BASE_DIR / "data" / "bosch_products_links.final.csv"
NABKADE_CSV = BASE_DIR / "nabkade_products.csv"
DB_PATH = BASE_DIR / "data" / "watch_list.db"
REVIEW_CSV = BASE_DIR / "data" / "review_queue.csv"
QA_REPORT = BASE_DIR / "data" / "matcher_qa_report.md"


def load_csv(path: Path) -> list[dict]:
    """Load a CSV file into a list of dicts."""
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def run() -> None:
    """Execute the full matching pipeline."""
    start = time.time()
    logger.info("=" * 60)
    logger.info("PRODUCT MATCHER — STARTING")
    logger.info("=" * 60)

    # ── Load data ───────────────────────────────────────────────────────

    logger.info("Loading Torob data from %s...", TOROB_CSV)
    torob_data = load_csv(TOROB_CSV)
    logger.info("  Loaded %d Torob products", len(torob_data))

    logger.info("Loading Nabkade data from %s...", NABKADE_CSV)
    nabkade_data = load_csv(NABKADE_CSV)
    logger.info("  Loaded %d Nabkade products", len(nabkade_data))

    # ── Build index ─────────────────────────────────────────────────────

    logger.info("Building indexes...")
    index = MatchIndex()
    index.build_torob_index(torob_data)
    index.build_nabkade_index(nabkade_data)

    # ── Open store ──────────────────────────────────────────────────────

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    store = WatchListStore(str(DB_PATH))

    # ── Matching loop ───────────────────────────────────────────────────

    logger.info("Starting matching pipeline...")
    matched_count = 0
    no_match_count = 0

    for i, nabkade_record in enumerate(nabkade_data):
        nabkade_id = str(nabkade_record.get("product_id", ""))
        nabkade = index.nabkade_products.get(nabkade_id)

        if not nabkade:
            logger.warning("Nabkade product %s not found in index, skipping", nabkade_id)
            continue

        # Generate candidates
        candidates = generate_candidates(nabkade, index)

        # Score candidates
        scored = score_all_candidates(nabkade, candidates, index)

        # Classify confidence
        confidence = classify_confidence(scored, nabkade, index)

        # Get preferred match details
        best_match = scored[0] if scored else None
        torob_url = ""
        torob_title = ""
        if confidence.preferred_torob_id:
            torob = index.torob_products.get(confidence.preferred_torob_id)
            if torob:
                torob_url = torob.title  # We'll use title as placeholder; URL needs lookup
                torob_title = torob.title

        # Store results
        store.upsert_watch_list(nabkade, confidence, best_match, torob_url, torob_title)
        store.insert_candidates(nabkade_id, scored)

        if confidence.level.value in ("high", "medium"):
            matched_count += 1
        else:
            no_match_count += 1

        # Add to review queue if needed
        if confidence.needs_review:
            candidates_text = json.dumps([
                {
                    "torob_id": m.torob_product_id,
                    "score": m.score,
                    "source": m.match_source,
                    "torob_title": index.torob_products.get(m.torob_product_id, None) and
                                   index.torob_products[m.torob_product_id].title,
                }
                for m in scored[:5]
            ], ensure_ascii=False)
            store.insert_review(nabkade, confidence, candidates_text)

        # Log
        store.log(nabkade_id, "match", json.dumps({
            "confidence": confidence.level.value,
            "score": confidence.score,
            "match_count": confidence.match_count,
            "reason": confidence.reason,
        }, ensure_ascii=False))

        if (i + 1) % 50 == 0:
            logger.info("  Progress: %d/%d (%d matched, %d no match)",
                        i + 1, len(nabkade_data), matched_count, no_match_count)

    elapsed = time.time() - start
    logger.info("Matching complete in %.1fs", elapsed)
    logger.info("  Matched: %d, No match: %d", matched_count, no_match_count)

    # ── Export review queue ─────────────────────────────────────────────

    export_review_queue(store, REVIEW_CSV)

    # ── Generate QA report ──────────────────────────────────────────────

    generate_qa_report(store, QA_REPORT, execution_time_seconds=elapsed)

    # ── Print stats ─────────────────────────────────────────────────────

    stats = store.get_stats()
    logger.info("=" * 60)
    logger.info("FINAL STATISTICS")
    logger.info("=" * 60)
    for k, v in sorted(stats.items()):
        logger.info("  %s: %s", k, v)

    store.close()
    logger.info("=" * 60)
    logger.info("PRODUCT MATCHER — DONE")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
