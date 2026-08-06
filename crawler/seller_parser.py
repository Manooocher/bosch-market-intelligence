"""Seller data parser.

Normalizes Torob seller data into a structured format.
Pure parsing — no I/O, no HTTP.
"""

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

    Torob formats prices as: "12,300,000 تومان" or "۱۲,۳۰۰,۰۰۰ تومان"
    Sometimes also: "12300000" or "۱۲۳۰۰۰۰۰"
    """
    if not price_str:
        return 0

    # Remove common prefixes/suffixes
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

    # Remove commas and spaces
    cleaned = cleaned.replace(",", "").replace(" ", "")

    # Extract numeric value
    match = re.search(r"(\d+)", cleaned)
    if match:
        return int(match.group(1))
    return 0


def parse_sellers(product_data: dict, torob_product_id: str) -> SellerParseResult:
    """Parse seller data from a Torob product API response.

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
    """Parse a single seller entry."""
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
