"""Confidence classification for scored product matches.

Conservative thresholds:
- HIGH: SKU exact + category exact + brand exact → auto-accept
- MEDIUM: SKU exact, category mismatch → auto-accept + flag
- LOW: No SKU, strong token overlap → manual review
- NONE: No reliable evidence → no match
"""

import logging
from dataclasses import dataclass
from enum import Enum

from matcher.scorer import ScoredMatch
from matcher.index import NabkadeProduct, TorobProduct, MatchIndex

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence levels for match classification."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


@dataclass
class ConfidenceResult:
    """Result of confidence classification."""
    level: ConfidenceLevel
    score: float
    preferred_torob_id: str | None
    all_torob_ids: list[str]
    match_count: int
    reason: str
    needs_review: bool


# ── Configurable thresholds ─────────────────────────────────────────────────

HIGH_THRESHOLD: float = 0.80
MEDIUM_THRESHOLD: float = 0.60
LOW_THRESHOLD: float = 0.35
TOKEN_OVERLAP_FOR_LOW: int = 2


def classify_confidence(
    scored_matches: list[ScoredMatch],
    nabkade: NabkadeProduct,
    index: MatchIndex,
) -> ConfidenceResult:
    """Classify the confidence level for a set of scored matches.

    Conservative approach:
    - HIGH only when SKU exact + category exact + brand exact
    - MEDIUM when SKU exact but category or brand differs
    - LOW when no SKU but token overlap is strong
    - NONE otherwise
    """
    if not scored_matches:
        return ConfidenceResult(
            level=ConfidenceLevel.NONE,
            score=0.0,
            preferred_torob_id=None,
            all_torob_ids=[],
            match_count=0,
            reason="no_candidates",
            needs_review=False,
        )

    best = scored_matches[0]
    torob = index.torob_products.get(best.torob_product_id)

    # Collect all Torob IDs
    all_ids = [m.torob_product_id for m in scored_matches]

    # Check conditions
    has_sku_match = best.match_source in ("sku_exact", "sku_prefix")
    sku_exact = best.match_source == "sku_exact"

    category_match = False
    brand_match = False
    if torob:
        nab_cat = nabkade.normalized_category.lower()
        tor_cat = torob.normalized_category.lower()
        category_match = nab_cat == tor_cat or (nab_cat and tor_cat and (nab_cat in tor_cat or tor_cat in nab_cat))

        nab_brand = nabkade.brand.strip().lower()
        tor_brand = torob.brand.strip().lower()
        if nab_brand and tor_brand:
            brand_match = nab_brand == tor_brand

    # Classify
    if sku_exact and category_match and brand_match:
        level = ConfidenceLevel.HIGH
        reason = "sku_exact+category+brand"
        needs_review = False
    elif sku_exact and category_match:
        level = ConfidenceLevel.HIGH
        reason = "sku_exact+category"
        needs_review = False
    elif sku_exact and not category_match:
        level = ConfidenceLevel.MEDIUM
        reason = "sku_exact_category_mismatch"
        needs_review = False
    elif has_sku_match and not category_match:
        level = ConfidenceLevel.MEDIUM
        reason = "sku_prefix_category_mismatch"
        needs_review = False
    elif has_sku_match and category_match:
        level = ConfidenceLevel.HIGH
        reason = "sku_prefix+category"
        needs_review = False
    elif best.score >= MEDIUM_THRESHOLD:
        level = ConfidenceLevel.MEDIUM
        reason = f"score_{best.score:.2f}"
        needs_review = True
    elif best.score >= LOW_THRESHOLD:
        level = ConfidenceLevel.LOW
        reason = f"low_score_{best.score:.2f}"
        needs_review = True
    else:
        level = ConfidenceLevel.NONE
        reason = f"very_low_score_{best.score:.2f}"
        needs_review = True

    return ConfidenceResult(
        level=level,
        score=best.score,
        preferred_torob_id=best.torob_product_id,
        all_torob_ids=all_ids,
        match_count=len(scored_matches),
        reason=reason,
        needs_review=needs_review,
    )
