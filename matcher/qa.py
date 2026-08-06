"""QA report generator for the Product Matcher.

Produces a comprehensive markdown report covering all matching statistics.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from matcher.store import WatchListStore

logger = logging.getLogger(__name__)


def generate_qa_report(
    store: WatchListStore,
    output_path: str | Path,
    execution_time_seconds: float = 0.0,
) -> str:
    """Generate a QA report and save to file.

    Returns the report text.
    """
    output_path = Path(output_path)
    stats = store.get_stats()
    watch_list = store.get_watch_list()

    # ── Calculate derived stats ─────────────────────────────────────────

    total = stats.get("total", 0)
    high = stats.get("confidence_high", 0)
    medium = stats.get("confidence_medium", 0)
    low = stats.get("confidence_low", 0)
    none = stats.get("confidence_none", 0)
    matched = stats.get("status_matched", 0)
    no_match = stats.get("status_no_match", 0)
    review_pending = stats.get("review_pending", 0)

    # Duplicate detection
    sku_counts: dict[str, int] = {}
    for row in watch_list:
        sku = row.get("canonical_sku", "")
        if sku:
            for s in sku.split(","):
                s = s.strip()
                if s:
                    sku_counts[s] = sku_counts.get(s, 0) + 1
    duplicate_skus = {k: v for k, v in sku_counts.items() if v > 1}

    # Multiple matches
    multi_match = [r for r in watch_list if (r.get("match_count", 0) or 0) > 1]

    # Category conflicts (SKU match but category mismatch)
    cat_conflicts = []
    for row in watch_list:
        if row.get("confidence_level") == "medium" and "category_mismatch" in (row.get("match_method", "") or ""):
            cat_conflicts.append(row)

    # Coverage
    coverage_pct = (matched / total * 100) if total > 0 else 0

    # ── Build report ────────────────────────────────────────────────────

    lines = [
        "=" * 60,
        "PRODUCT MATCHER — QA REPORT",
        "=" * 60,
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Execution time: {execution_time_seconds:.1f}s",
        "",
        "## Summary",
        f"  Total Nabkade products:       {total}",
        f"  Matched (status=matched):     {matched}",
        f"  No match (status=no_match):   {no_match}",
        f"  Coverage:                     {coverage_pct:.1f}%",
        "",
        "## Confidence Levels",
        f"  HIGH   (auto-accept):         {high}",
        f"  MEDIUM (auto-accept+flag):    {medium}",
        f"  LOW    (manual review):       {low}",
        f"  NONE   (no match):            {none}",
        "",
        "## Review Queue",
        f"  Pending review:               {review_pending}",
        "",
        "## Data Quality",
        f"  Total candidates scored:      {stats.get('total_candidates', 0)}",
        f"  Duplicate SKUs:               {len(duplicate_skus)}",
        f"  Multiple matches:             {len(multi_match)}",
        f"  Category conflicts:           {len(cat_conflicts)}",
        "",
    ]

    # ── Per-category breakdown ──────────────────────────────────────────

    lines.append("## Per-Category Breakdown")
    cat_stats: dict[str, dict[str, int]] = {}
    for row in watch_list:
        cat = row.get("nabkade_category", "Unknown") or "Unknown"
        level = row.get("confidence_level", "none") or "none"
        if cat not in cat_stats:
            cat_stats[cat] = {"total": 0, "high": 0, "medium": 0, "low": 0, "none": 0, "matched": 0}
        cat_stats[cat]["total"] += 1
        cat_stats[cat][level] = cat_stats[cat].get(level, 0) + 1
        if row.get("status") == "matched":
            cat_stats[cat]["matched"] += 1

    for cat in sorted(cat_stats.keys()):
        cs = cat_stats[cat]
        cov = (cs["matched"] / cs["total"] * 100) if cs["total"] > 0 else 0
        lines.append(f"  {cat}: {cs['total']} total, {cs['matched']} matched ({cov:.0f}%), "
                     f"H={cs['high']} M={cs['medium']} L={cs['low']} N={cs['none']}")

    # ── Duplicate SKUs ──────────────────────────────────────────────────

    if duplicate_skus:
        lines.append("")
        lines.append("## Duplicate SKUs (same SKU on multiple Nabkade products)")
        for sku, count in sorted(duplicate_skus.items(), key=lambda x: -x[1]):
            lines.append(f"  {sku}: {count} products")

    # ── Multiple matches ────────────────────────────────────────────────

    if multi_match:
        lines.append("")
        lines.append(f"## Multiple Matches ({len(multi_match)} products)")
        for row in multi_match[:20]:
            title = (row.get("nabkade_title") or "")[:50]
            count = row.get("match_count", 0)
            ids = row.get("all_torob_ids", "[]")
            try:
                id_list = json.loads(ids) if ids else []
            except (json.JSONDecodeError, TypeError):
                id_list = []
            lines.append(f"  [{row.get('nabkade_product_id')}] {title} → {count} Torob matches")

    # ── Category conflicts ──────────────────────────────────────────────

    if cat_conflicts:
        lines.append("")
        lines.append(f"## Category Conflicts ({len(cat_conflicts)} products)")
        for row in cat_conflicts[:20]:
            title = (row.get("nabkade_title") or "")[:50]
            lines.append(f"  [{row.get('nabkade_product_id')}] {title} "
                         f"(score={row.get('confidence_score', 0):.2f})")

    # ── Sample matches ──────────────────────────────────────────────────

    lines.append("")
    lines.append("## Sample HIGH Confidence Matches")
    high_matches = [r for r in watch_list if r.get("confidence_level") == "high"]
    for row in high_matches[:10]:
        nab_title = (row.get("nabkade_title") or "")[:40]
        tor_title = (row.get("preferred_torob_title") or "")[:40]
        lines.append(f"  {row.get('canonical_sku', 'N/A'):15s} | {nab_title:40s} → {tor_title}")

    lines.append("")
    lines.append("## Sample MEDIUM Confidence Matches")
    med_matches = [r for r in watch_list if r.get("confidence_level") == "medium"]
    for row in med_matches[:10]:
        nab_title = (row.get("nabkade_title") or "")[:40]
        tor_title = (row.get("preferred_torob_title") or "")[:40]
        score = row.get("confidence_score", 0)
        lines.append(f"  {row.get('canonical_sku', 'N/A'):15s} | {score:.2f} | {nab_title:40s} → {tor_title}")

    # ── End ─────────────────────────────────────────────────────────────

    lines.append("")
    lines.append("=" * 60)
    lines.append("END OF REPORT")
    lines.append("=" * 60)

    report = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info("QA report written to %s", output_path)
    return report
