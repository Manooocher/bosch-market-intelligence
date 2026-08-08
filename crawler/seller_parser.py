"""Seller data parser.

Normalizes Torob seller data into a structured format.
Pure parsing — no I/O, no HTTP.

V2: Designed for the Torob details API which returns full seller arrays.
    Preserves backward compatibility with V1 for search API fallback.
"""

import json
import re
from dataclasses import dataclass, field


@dataclass
class Seller:
    """Normalized seller information."""
    seller_id: str
    seller_name: str
    price_rial: int
    original_price_rial: int = 0
    has_discount: bool = False
    in_stock: bool = True
    shipping_cost: int = 0
    offer_url: str = ""
    # ── New fields for details API ──
    seller_score: int = 0          # shop_score (1-5)
    seller_city: str = ""          # shop_name2
    warranty_info: str = ""        # name2
    is_promoted: bool = False      # is_adv
    extra_info_json: str = ""      # more_info serialized


@dataclass
class SellerParseResult:
    """Result of parsing sellers from a Torob product response."""
    product_id: str
    torob_product_id: str
    title: str
    sellers: list[Seller] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)


def _parse_rial_price(price_str: str) -> int:
    """Parse a Torob price string to integer Rial.

    Torob formats prices as: "12,300,000 تومان" or "۱۲,۳۰۰،۰۰۰"
    Sometimes also: "12300000" or "۱۲۳۰۰۰۰۰"
    The details API returns price as an integer directly.
    """
    if not price_str:
        return 0

    cleaned = str(price_str).strip()
    cleaned = re.sub(r"تومان|IRR|rial|Rials", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()

    # Convert Persian/Arabic digits to ASCII
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    ascii_digits = "0123456789"
    for p, a in zip(persian_digits, ascii_digits):
        cleaned = cleaned.replace(p, a)

    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    for a, d in zip(arabic_digits, ascii_digits):
        cleaned = cleaned.replace(a, d)

    cleaned = cleaned.replace(",", "").replace(" ", "")
    match = re.search(r"(\d+)", cleaned)
    if match:
        return int(match.group(1))
    return 0


def _safe_int(value, default: int = 0) -> int:
    """Safely convert a value to int."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _safe_str(value, default: str = "") -> str:
    """Safely convert a value to str."""
    if value is None:
        return default
    return str(value).strip()


def parse_sellers(product_data: dict, torob_product_id: str) -> SellerParseResult:
    """Parse seller data from a Torob product API response (V1 — backward compatible).

    Returns structured seller list ready for statistics calculation.
    """
    title = product_data.get("name1", "")
    result = SellerParseResult(
        product_id=torob_product_id,
        torob_product_id=torob_product_id,
        title=title,
    )

    sellers_data = product_data.get("sellers") or product_data.get("seller") or []

    if not sellers_data:
        result.parse_errors.append("no_sellers_data")
        return result

    seen_sellers = set()

    for seller_entry in sellers_data:
        try:
            seller = _parse_single_seller(seller_entry, torob_product_id)
            if seller and seller.seller_id not in seen_sellers:
                result.sellers.append(seller)
                seen_sellers.add(seller.seller_id)
        except Exception as e:
            result.parse_errors.append(f"parse_error: {str(e)}")

    return result


def _parse_single_seller(entry: dict, torob_product_id: str) -> Seller | None:
    """Parse a single seller entry (V1 — basic fields only)."""
    if not isinstance(entry, dict):
        return None

    seller_id = str(entry.get("shop_id", "") or entry.get("seller_id", "") or entry.get("id", ""))
    if not seller_id:
        seller_id = str(hash(str(entry)))[:12]

    seller_name = entry.get("shop_name", "") or entry.get("seller_name", "") or entry.get("name", "")
    price_str = entry.get("price", "") or entry.get("price_text", "") or entry.get("sell_price", "")
    price_rial = _parse_rial_price(str(price_str))

    original_price_str = entry.get("original_price", "") or entry.get("original_price_text", "")
    original_price_rial = _parse_rial_price(str(original_price_str))
    has_discount = original_price_rial > price_rial > 0 if original_price_rial > 0 else False

    in_stock = True
    if "status" in entry:
        in_stock = entry["status"] != "out_of_stock"
    if "availability" in entry:
        in_stock = entry["availability"] != "out_of_stock"

    shipping_str = entry.get("shipping_cost", "0")
    shipping_cost = _parse_rial_price(str(shipping_str))

    offer_url = entry.get("url", "") or entry.get("offer_url", "")

    if price_rial <= 0:
        return None

    return Seller(
        seller_id=seller_id,
        seller_name=seller_name,
        price_rial=price_rial,
        original_price_rial=original_price_rial,
        has_discount=has_discount,
        in_stock=in_stock,
        shipping_cost=shipping_cost,
        offer_url=offer_url,
    )


# ── V2: Details API Parser ─────────────────────────────────────────────────

def parse_sellers_v2(product_data: dict, torob_product_id: str) -> SellerParseResult:
    """Parse seller data from Torob details API response (V2).

    The details API returns a full seller array with structured fields:
      - shop_id (int)
      - shop_name (str)
      - shop_name2 (str) → seller_city
      - price (int) → price_rial (already in Rials)
      - shop_score (int, 1-5) → seller_score
      - name2 (str) → warranty_info
      - availability (bool) → in_stock
      - more_info (dict) → extra_info_json
      - is_adv (bool) → is_promoted
    """
    title = product_data.get("name1", "")
    result = SellerParseResult(
        product_id=torob_product_id,
        torob_product_id=torob_product_id,
        title=title,
    )

    sellers_data = product_data.get("sellers") or product_data.get("seller") or []

    if not sellers_data:
        result.parse_errors.append("no_sellers_data")
        return result

    seen_sellers = set()

    for entry in sellers_data:
        try:
            seller = _parse_single_seller_v2(entry, torob_product_id)
            if seller and seller.seller_id not in seen_sellers:
                result.sellers.append(seller)
                seen_sellers.add(seller.seller_id)
        except Exception as e:
            result.parse_errors.append(f"parse_error: {str(e)}")

    return result


def _parse_single_seller_v2(entry: dict, torob_product_id: str) -> Seller | None:
    """Parse a single seller from the details API response (V2 schema).

    Maps real Torob API fields:
      shop_id      → seller_id (cast to str)
      shop_name    → seller_name
      shop_name2   → seller_city
      price        → price_rial (already int, no parsing needed)
      shop_score   → seller_score (int, 1-5)
      name2        → warranty_info
      availability → in_stock (bool)
      more_info    → extra_info_json (dict → JSON string)
      is_adv       → is_promoted (bool)
    """
    if not isinstance(entry, dict):
        return None

    # seller_id: shop_id is an int in the details API
    raw_id = entry.get("shop_id", "") or entry.get("seller_id", "") or entry.get("id", "")
    if not raw_id:
        return None
    seller_id = str(raw_id)

    # seller_name
    seller_name = _safe_str(entry.get("shop_name", "") or entry.get("seller_name", ""))

    # price_rial: the details API returns price as an integer already in Rials
    price_rial = _safe_int(entry.get("price", 0))
    if price_rial <= 0:
        # Try price_text fallback (some products have text prices)
        price_text = entry.get("price_text", "")
        price_rial = _parse_rial_price(str(price_text))

    if price_rial <= 0:
        return None

    # original_price for discount detection
    original_price = _safe_int(entry.get("original_price", 0))
    has_discount = original_price > price_rial > 0

    # in_stock: availability is a boolean in the details API
    availability = entry.get("availability", True)
    in_stock = bool(availability) if availability is not None else True

    # seller_score: shop_score is an integer 1-5
    seller_score = _safe_int(entry.get("shop_score", 0))

    # seller_city: shop_name2 contains city info
    seller_city = _safe_str(entry.get("shop_name2", ""))

    # warranty_info: name2 contains warranty text
    warranty_info = _safe_str(entry.get("name2", ""))

    # is_promoted: is_adv boolean
    is_promoted = bool(entry.get("is_adv", False))

    # extra_info_json: serialize more_info dict
    more_info = entry.get("more_info", {})
    extra_info_json = json.dumps(more_info, ensure_ascii=False) if more_info else ""

    # shipping_cost
    shipping_cost = _safe_int(entry.get("shipping_cost", 0))

    # offer_url
    offer_url = _safe_str(entry.get("url", "") or entry.get("offer_url", ""))

    return Seller(
        seller_id=seller_id,
        seller_name=seller_name,
        price_rial=price_rial,
        original_price_rial=original_price,
        has_discount=has_discount,
        in_stock=in_stock,
        shipping_cost=shipping_cost,
        offer_url=offer_url,
        seller_score=seller_score,
        seller_city=seller_city,
        warranty_info=warranty_info,
        is_promoted=is_promoted,
        extra_info_json=extra_info_json,
    )
