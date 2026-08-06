"""Configurable weighted scoring engine for product matching.

Combines multiple signals into a single match score [0.0, 1.0].
"""

import logging
from dataclasses import dataclass, field

from matcher.candidate import Candidate
from matcher.index import MatchIndex, NabkadeProduct, TorobProduct
from matcher.normalize import normalize_title_for_matching

logger = logging.getLogger(__name__)


# ── Default scoring weights ─────────────────────────────────────────────────

DEFAULT_WEIGHTS: dict[str, float] = {
    "sku_exact": 0.50,
    "sku_prefix": 0.20,
    "category_match": 0.15,
    "token_overlap": 0.10,
    "brand_match": 0.05,
}


@dataclass
class ScoredMatch:
    """A scored candidate match."""
    torob_product_id: str
    score: float
    signals: dict[str, float] = field(default_factory=dict)
    match_source: str = ""


def _token_overlap_score(tokens_a: list[str], tokens_b: list[str]) -> float:
    """Jaccard-like overlap score between two token lists."""
    if not tokens_a or not tokens_b:
        return 0.0
    set_a = set(t for t in tokens_a if len(t) >= 2)
    set_b = set(t for t in tokens_b if len(t) >= 2)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def score_candidate(
    nabkade: NabkadeProduct,
    candidate: Candidate,
    index: MatchIndex,
    weights: dict[str, float] | None = None,
) -> ScoredMatch:
    """Score a single candidate match.

    Returns ScoredMatch with total score and individual signal scores.
    """
    w = weights or DEFAULT_WEIGHTS
    torob = index.torob_products.get(candidate.torob_product_id)
    if not torob:
        return ScoredMatch(
            torob_product_id=candidate.torob_product_id,
            score=0.0,
            signals={"error": 1.0},
            match_source=candidate.match_source,
        )

    signals: dict[str, float] = {}

    # Signal 1: SKU exact match
    if candidate.match_source == "sku_exact":
        signals["sku_exact"] = 1.0
    elif candidate.match_source == "sku_prefix":
        signals["sku_prefix"] = 1.0
    else:
        signals["sku_exact"] = 0.0
        signals["sku_prefix"] = 0.0

    # Signal 2: Category match
    nab_cat = nabkade.normalized_category.lower()
    tor_cat = torob.normalized_category.lower()
    if nab_cat and tor_cat:
        if nab_cat == tor_cat:
            signals["category_match"] = 1.0
        elif nab_cat in tor_cat or tor_cat in nab_cat:
            signals["category_match"] = 0.5
        else:
            signals["category_match"] = 0.0
    else:
        signals["category_match"] = 0.0

    # Signal 3: Token overlap
    signals["token_overlap"] = _token_overlap_score(nabkade.tokens, torob.tokens)

    # Signal 4: Brand match
    nab_brand = nabkade.brand.strip().lower()
    tor_brand = torob.brand.strip().lower()
    if nab_brand and tor_brand:
        if nab_brand == tor_brand:
            signals["brand_match"] = 1.0
        elif nab_brand in tor_brand or tor_brand in nab_brand:
            signals["brand_match"] = 0.5
        else:
            signals["brand_match"] = 0.0
    elif not nab_brand or not tor_brand:
        signals["brand_match"] = 0.5  # Unknown brand, don't penalize
    else:
        signals["brand_match"] = 0.0

    # Calculate weighted score
    score = 0.0
    for signal_name, weight in w.items():
        score += weight * signals.get(signal_name, 0.0)

    return ScoredMatch(
        torob_product_id=candidate.torob_product_id,
        score=round(score, 4),
        signals=signals,
        match_source=candidate.match_source,
    )


def score_all_candidates(
    nabkade: NabkadeProduct,
    candidates: list[Candidate],
    index: MatchIndex,
    weights: dict[str, float] | None = None,
) -> list[ScoredMatch]:
    """Score all candidates for a Nabkade product and return sorted by score."""
    scored = [
        score_candidate(nabkade, c, index, weights)
        for c in candidates
    ]
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored
