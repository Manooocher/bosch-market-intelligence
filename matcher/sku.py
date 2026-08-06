"""Bosch model number (SKU) extraction from product titles.

Uses a JSON prefix dictionary instead of hardcoded prefixes.
Extracts canonical Bosch SKUs like SMS46MI20M, BGL8ALL5, KGN86AI304.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from matcher.normalize import normalize_sku_text

# ── Load prefix dictionary ──────────────────────────────────────────────────

_DICT_PATH = Path(__file__).resolve().parent.parent / "data" / "bosch_prefixes.json"


def _load_prefix_dict() -> tuple[list[str], dict[str, dict]]:
    """Load prefix dictionary from JSON file.

    Returns (prefix_list, prefix_info_map).
    """
    with open(_DICT_PATH, encoding="utf-8") as f:
        data = json.load(f)

    prefixes = []
    info_map = {}
    for entry in data.get("prefixes", []):
        if entry.get("status") == "active":
            p = entry["prefix"]
            prefixes.append(p)
            info_map[p] = entry

    return prefixes, info_map


_BOSCH_PREFIXES, _PREFIX_INFO = _load_prefix_dict()
_PREFIX_SET = set(_BOSCH_PREFIXES)
_PREFIX_PATTERN = "|".join(re.escape(p) for p in _BOSCH_PREFIXES)

# ── Main extraction regex ───────────────────────────────────────────────────

_SKU_REGEX = re.compile(
    rf"(?:^|\s|/)({_PREFIX_PATTERN})"
    r"[0-9]{1,4}"
    r"[A-Z]{1,6}"
    r"[0-9]{0,4}"
    r"[A-Z]{0,3}"
    r"(?=\s|/|$|,|؛|;|-|\)|\]|>|\"|\\\\|،)",
    re.IGNORECASE,
)

_SKU_FALLBACK = re.compile(
    rf"(?:^|\s)({_PREFIX_PATTERN})"
    r"[0-9A-Z]{2,12}"
    r"(?=\s|/|$|,|؛|;|-|\)|\]|>|\"|\\\\|،)",
    re.IGNORECASE,
)

# ── Known invalid patterns ──────────────────────────────────────────────────

_BLACKLIST: set[str] = {
    "BOSCH", "BOSCH",
    "HP", "CANON", "RICOH", "SHARP", "TOSHIBA", "XEROX",
    "KYOCERA", "BROTHER", "LEXMARK", "EPSON", "KONICA",
    "SAMSUNG", "PHILIPS", "PANASONIC", "LG",
    "SAN", "ACE", "PROTECHNIC",
}


@dataclass
class ExtractionResult:
    """Result of SKU extraction from a title."""
    raw_text: str
    canonical_skus: list[str] = field(default_factory=list)
    all_candidates: list[str] = field(default_factory=list)
    is_valid: bool = False
    extraction_method: str = "none"
    prefix: str = ""
    notes: str = ""


def _canonicalize_sku(raw: str) -> str:
    """Convert raw matched text to canonical SKU form."""
    sku = raw.upper().strip()
    sku = sku.replace(" ", "").replace("-", "").replace(".", "")

    known_suffixes = ["/B", "/W", "/S", "/GR", "/SI", "/IN", "/EU", "/TR", "-01", "-02", "-03"]
    for suffix in known_suffixes:
        if sku.endswith(suffix):
            sku = sku[: -len(suffix)]
            break

    return sku


def _validate_sku(sku: str) -> tuple[bool, str]:
    """Validate a candidate SKU against known rules."""
    if len(sku) < 6 or len(sku) > 16:
        return False, f"invalid_length_{len(sku)}"

    if sku in _BLACKLIST:
        return False, "blacklisted"

    prefix = ""
    for p in _BOSCH_PREFIXES:
        if sku.startswith(p):
            prefix = p
            break
    if not prefix:
        return False, "unknown_prefix"

    rest = sku[len(prefix):]
    if not any(c.isdigit() for c in rest):
        return False, "no_digit_after_prefix"

    digit_ratio = sum(1 for c in sku if c.isdigit()) / len(sku)
    if digit_ratio < 0.2:
        return False, f"low_digit_ratio_{digit_ratio:.2f}"

    return True, "ok"


def get_prefix_info(sku: str) -> dict | None:
    """Get prefix dictionary info for a validated SKU."""
    for p in _BOSCH_PREFIXES:
        if sku.startswith(p):
            return _PREFIX_INFO.get(p)
    return None


def extract_skus(title: str) -> ExtractionResult:
    """Extract all Bosch model numbers from a product title."""
    result = ExtractionResult(raw_text=title)
    normalized = normalize_sku_text(title)

    candidates: list[str] = []

    # Try primary regex
    for m in _SKU_REGEX.finditer(normalized):
        candidates.append(m.group())

    if not candidates:
        for m in _SKU_FALLBACK.finditer(normalized):
            candidates.append(m.group())

    result.all_candidates = candidates

    seen: set[str] = set()
    for raw in candidates:
        canonical = _canonicalize_sku(raw)
        if canonical in seen:
            continue
        seen.add(canonical)

        is_valid, reason = _validate_sku(canonical)
        if is_valid:
            result.canonical_skus.append(canonical)
            result.is_valid = True
            result.extraction_method = "regex"
            if not result.prefix:
                for p in _BOSCH_PREFIXES:
                    if canonical.startswith(p):
                        result.prefix = p
                        break
        else:
            result.notes += f"rejected({canonical}:{reason}); "

    if not result.canonical_skus and title:
        url_sku = _extract_from_url_pattern(normalized)
        if url_sku:
            is_valid, reason = _validate_sku(url_sku)
            if is_valid:
                result.canonical_skus.append(url_sku)
                result.is_valid = True
                result.extraction_method = "url_pattern"
                for p in _BOSCH_PREFIXES:
                    if url_sku.startswith(p):
                        result.prefix = p
                        break

    if not result.canonical_skus:
        result.notes = result.notes or "no_sku_found"

    return result


def _extract_from_url_pattern(text: str) -> str | None:
    """Try to extract SKU from URL-slug-like patterns."""
    for prefix in _BOSCH_PREFIXES:
        pattern = re.compile(
            rf"{prefix}[0-9]{{1,4}}[A-Z]{{1,6}}[0-9]{{0,4}}[A-Z]{{0,3}}",
            re.IGNORECASE,
        )
        m = pattern.search(text)
        if m:
            return _canonicalize_sku(m.group())
    return None


def extract_sku_from_url(url: str) -> str | None:
    """Extract a Bosch model number directly from a product URL."""
    normalized = url.lower().replace("-", "").replace("/", "").replace(".", "")
    for prefix in _BOSCH_PREFIXES:
        pattern = re.compile(
            rf"{prefix.lower()}[0-9]{{1,4}}[a-z]{{1,6}}[0-9]{{0,4}}[a-z]{{0,3}}",
        )
        m = pattern.search(normalized)
        if m:
            return m.group().upper()
    return None
