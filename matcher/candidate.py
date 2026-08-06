"""Candidate generation — finds potential Torob matches for each Nabkade product.

Two-phase strategy:
  Phase 1: SKU index lookup (high precision)
  Phase 2: Category + token filter (fallback for SKU-less products)
"""

import logging
from dataclasses import dataclass, field

from matcher.index import MatchIndex, NabkadeProduct

logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    """A candidate match for a Nabkade product."""
    torob_product_id: str
    match_source: str  # "sku_exact" | "sku_prefix" | "token_overlap" | "category"
    overlap_tokens: list[str] = field(default_factory=list)
    overlap_count: int = 0


def generate_candidates(
    nabkade: NabkadeProduct,
    index: MatchIndex,
    max_candidates: int = 20,
) -> list[Candidate]:
    """Generate candidate Torob products for a Nabkade product.

    Strategy:
    1. If SKU found → look up SKU index
    2. If SKU found but no index match → try SKU prefix matching
    3. If no SKU → use category + token overlap
    """
    candidates: list[Candidate] = []
    seen: set[str] = set()

    # Phase 1: SKU-based matching
    if nabkade.canonical_skus:
        for sku in nabkade.canonical_skus:
            # Exact SKU match
            torob_ids = index.get_sku_candidates(sku)
            for pid in torob_ids:
                if pid not in seen:
                    candidates.append(Candidate(
                        torob_product_id=pid,
                        match_source="sku_exact",
                    ))
                    seen.add(pid)

            # SKU prefix match (first 5 chars)
            if len(sku) >= 5:
                prefix = sku[:5]
                for other_sku, pids in index.sku_index.items():
                    if other_sku != sku and other_sku.startswith(prefix):
                        for pid in pids:
                            if pid not in seen:
                                candidates.append(Candidate(
                                    torob_product_id=pid,
                                    match_source="sku_prefix",
                                ))
                                seen.add(pid)

    # Phase 2: Category + token overlap (fallback)
    if not candidates and nabkade.tokens:
        # Get category-matched products
        cat_candidates = set(index.get_category_candidates(nabkade.normalized_category))

        # Get token-overlap products
        token_overlap = index.get_token_candidates(nabkade.tokens, min_overlap=2)

        # Combine: prefer products in both category AND token overlap
        for pid, overlap in token_overlap.items():
            if pid not in seen:
                source = "token_overlap"
                if pid in cat_candidates:
                    source = "category_token"
                candidates.append(Candidate(
                    torob_product_id=pid,
                    match_source=source,
                    overlap_count=overlap,
                ))
                seen.add(pid)

        # Also add category-only candidates (up to 10)
        cat_only_count = 0
        for pid in cat_candidates:
            if pid not in seen and cat_only_count < 10:
                candidates.append(Candidate(
                    torob_product_id=pid,
                    match_source="category",
                ))
                seen.add(pid)
                cat_only_count += 1

    # Limit candidates
    if len(candidates) > max_candidates:
        # Prioritize: sku_exact > sku_prefix > category_token > token_overlap > category
        priority = {
            "sku_exact": 0,
            "sku_prefix": 1,
            "category_token": 2,
            "token_overlap": 3,
            "category": 4,
        }
        candidates.sort(key=lambda c: (priority.get(c.match_source, 99), -c.overlap_count))
        candidates = candidates[:max_candidates]

    logger.debug(
        "Nabkade %s (SKUs=%s): %d candidates generated",
        nabkade.product_id, nabkade.canonical_skus, len(candidates),
    )

    return candidates
