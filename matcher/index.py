"""Inverted indexes for candidate generation.

Builds:
- SKU index: canonical_sku → list of product IDs
- Token index: normalized_token → list of product IDs
- Category index: normalized_category → list of product IDs
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from matcher.normalize import normalize_title_for_matching, remove_stop_words
from matcher.sku import extract_skus

logger = logging.getLogger(__name__)


@dataclass
class TorobProduct:
    """Lightweight Torob product record for indexing."""
    product_id: str
    title: str
    category: str
    brand: str
    normalized_title: str = ""
    normalized_category: str = ""
    canonical_skus: list[str] = field(default_factory=list)
    tokens: list[str] = field(default_factory=list)


@dataclass
class NabkadeProduct:
    """Lightweight Nabkade product record for indexing."""
    product_id: str
    title: str
    category: str
    brand: str
    price: str
    product_url: str
    image_url: str
    normalized_title: str = ""
    normalized_category: str = ""
    canonical_skus: list[str] = field(default_factory=list)
    tokens: list[str] = field(default_factory=list)


class MatchIndex:
    """Combined indexes for product matching."""

    def __init__(self) -> None:
        self.sku_index: dict[str, list[str]] = defaultdict(list)
        self.token_index: dict[str, list[str]] = defaultdict(list)
        self.category_index: dict[str, list[str]] = defaultdict(list)
        self.torob_products: dict[str, TorobProduct] = {}
        self.nabkade_products: dict[str, NabkadeProduct] = {}
        self.stats: dict[str, int] = defaultdict(int)

    def build_torob_index(self, products: list[dict]) -> None:
        """Build indexes from Torob product data."""
        logger.info("Building Torob index for %d products...", len(products))

        for p in products:
            pid = p.get("product_id", "")
            title = p.get("title", "")
            category = p.get("category", "")
            brand = p.get("brand", "")

            norm_title = normalize_title_for_matching(title)
            norm_cat = normalize_title_for_matching(category)
            no_stop = remove_stop_words(norm_title)

            tp = TorobProduct(
                product_id=pid,
                title=title,
                category=category,
                brand=brand,
                normalized_title=norm_title,
                normalized_category=norm_cat,
            )

            # Extract SKUs
            result = extract_skus(title)
            tp.canonical_skus = result.canonical_skus
            for sku in result.canonical_skus:
                self.sku_index[sku].append(pid)
                self.stats["sku_index_entries"] += 1

            # Extract tokens
            tp.tokens = no_stop.split()
            for token in tp.tokens:
                if len(token) >= 2:
                    self.token_index[token].append(pid)
                    self.stats["token_index_entries"] += 1

            # Category index
            if norm_cat:
                self.category_index[norm_cat].append(pid)
                self.stats["category_index_entries"] += 1

            self.torob_products[pid] = tp

        logger.info(
            "Torob index built: %d SKUs, %d tokens, %d categories",
            len(self.sku_index), len(self.token_index), len(self.category_index),
        )

    def build_nabkade_index(self, products: list[dict]) -> None:
        """Index Nabkade products."""
        logger.info("Indexing %d Nabkade products...", len(products))

        for p in products:
            pid = str(p.get("product_id", ""))
            title = p.get("title", "")
            category = p.get("category", "")
            brand = p.get("brand", "")
            price = p.get("price", "")
            url = p.get("product_url", "")
            image = p.get("image_url", "")

            norm_title = normalize_title_for_matching(title)
            norm_cat = normalize_title_for_matching(category)

            np = NabkadeProduct(
                product_id=pid,
                title=title,
                category=category,
                brand=brand,
                price=price,
                product_url=url,
                image_url=image,
                normalized_title=norm_title,
                normalized_category=norm_cat,
            )

            result = extract_skus(title)
            np.canonical_skus = result.canonical_skus

            # Also try extracting SKU from URL
            if not np.canonical_skus:
                from matcher.sku import extract_sku_from_url
                url_sku = extract_sku_from_url(url)
                if url_sku:
                    np.canonical_skus.append(url_sku)

            no_stop = remove_stop_words(norm_title)
            np.tokens = no_stop.split()

            self.nabkade_products[pid] = np
            self.stats["nabkade_products_indexed"] += 1

        logger.info(
            "Nabkade index built: %d products, %d with SKUs",
            self.stats["nabkade_products_indexed"],
            sum(1 for p in self.nabkade_products.values() if p.canonical_skus),
        )

    def get_sku_candidates(self, sku: str) -> list[str]:
        """Get Torob product IDs matching a canonical SKU."""
        return list(self.sku_index.get(sku, []))

    def get_token_candidates(self, tokens: list[str], min_overlap: int = 2) -> dict[str, int]:
        """Get Torob product IDs with token overlap.

        Returns dict of product_id → overlap count.
        """
        counts: dict[str, int] = defaultdict(int)
        for token in tokens:
            if len(token) < 2:
                continue
            for pid in self.token_index.get(token, []):
                counts[pid] += 1
        return {pid: c for pid, c in counts.items() if c >= min_overlap}

    def get_category_candidates(self, category: str) -> list[str]:
        """Get Torob product IDs in a matching category."""
        return list(self.category_index.get(category, []))
