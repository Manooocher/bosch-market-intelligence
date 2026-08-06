"""Deterministic text normalization for Persian/English product titles.

All normalization is pure string manipulation — no network calls, no randomness.
Identical input always produces identical output.
"""

import re
import unicodedata


# ── Arabic → Persian character map ──────────────────────────────────────────

_ARABIC_TO_PERSIAN: dict[str, str] = {
    "\u064a": "\u06cc",  # ي → ی
    "\u0643": "\u06a9",  # ك → ک
    "\u0629": "\u0647",  # ة → ه
    "\u0623": "\u0627",  # أ → ا
    "\u0621": "\u0627",  # ء → ا
    "\u0622": "\u0627",  # آ → ا
    "\u0649": "\u06cc",  # ى → ی
    "\u06c0": "\u0647",  # ۀ → ه
    "\u0626": "\u06cc",  # ئ → ی
    "\u0624": "\u0648",  # ؤ → و
}

# ── Persian digit → ASCII digit ─────────────────────────────────────────────

_FARSI_DIGITS: dict[str, str] = {
    "\u06f0": "0", "\u06f1": "1", "\u06f2": "2", "\u06f3": "3",
    "\u06f4": "4", "\u06f5": "5", "\u06f6": "6", "\u06f7": "7",
    "\u06f8": "8", "\u06f9": "9",
}

_ARABIC_INDIC_DIGITS: dict[str, str] = {
    "\u0660": "0", "\u0661": "1", "\u0662": "2", "\u0663": "3",
    "\u0664": "4", "\u0665": "5", "\u0666": "6", "\u0667": "7",
    "\u0668": "8", "\u0669": "9",
}

# ── Brand aliases → canonical form ──────────────────────────────────────────

BRAND_ALIASES: dict[str, str] = {
    "بوش": "بوش",
    "bosch": "بوش",
    "bosch": "بوش",
    "شارک": "شارک",
    "shark": "شارک",
    "نینجا": "نینجا",
    "ninja": "نینجا",
}

# ── Category mapping (Nabkade → canonical) ──────────────────────────────────

CATEGORY_MAP: dict[str, str] = {
    "ماشین ظرفشویی": "ماشین ظرفشویی",
    "dishwasher": "ماشین ظرفشویی",
    "ماشین لباسشویی": "ماشین لباسشویی",
    "washing-machine": "ماشین لباسشویی",
    "فر توکار": "فر توکار",
    "built-in-oven": "فر توکار",
    "ماکروویو توکار": "مایکروویو",
    "built-in-microwave": "مایکروویو",
    "ماکروویو": "مایکروویو",
    "microwave": "مایکروویو",
    "هود توکار": "هود",
    "built-in-hood": "هود",
    "هود": "هود",
    "hood": "هود",
    "یخچال و فریزر": "یخچال فریزر",
    "یخچال فریزر": "یخچال فریزر",
    "refrigerator-freezer": "یخچال فریزر",
    "یخچال توکار": "یخچال توکار",
    "built-in-fridge": "یخچال توکار",
    "فریزر توکار": "فریزر توکار",
    "built-in-freezer": "فریزر توکار",
    "فریزر": "فریزر",
    "یخچال": "یخچال",
    "جاروبرقی": "جاروبرقی",
    "vacuum-cleaner": "جاروبرقی",
    "جارو شارژی": "جاروشارژی",
    "cordless-vacuum-cleaner": "جاروشارژی",
    "خشک کن": "خشک کن",
    "dryer": "خشک کن",
    "اتو بخار": "اتو و بخارگر",
    "steam-iron": "اتو و بخارگر",
    "اتو مخزن دار": "اتو و بخارگر",
    "tank-iron": "اتو و بخارگر",
    "اتو": "اتو و بخارگر",
    "iron": "اتو و بخارگر",
    "سشوار": "سشوار و برس حرارتی",
    "sallary": "سشوار و برس حرارتی",
    "گوشت کوب": "گوشت کوب برقی",
    "electric-meat-grinder": "گوشت کوب برقی",
    "آبمیوه گیری": "آبمیوه گیری",
    "juicer": "آبمیوه گیری",
    "آب مرکبات گیری": "آبمیوه گیری",
    "citrus-juicer": "آبمیوه گیری",
    "آسیاب": "خردکن/آسیاب",
    "mill": "خردکن/آسیاب",
    "خرد‌ کن": "خردکن/آسیاب",
    "crusher": "خردکن/آسیاب",
    "چای ساز": "چای ساز",
    "tea-maker": "چای ساز",
    "قهوه ساز": "قهوه و اسپرسو ساز",
    "coffee-maker": "قهوه و اسپرسو ساز",
    "اسپرسو ساز": "قهوه و اسپرسو ساز",
    "espresso-maker": "قهوه و اسپرسو ساز",
    "اسپرسو ساز توکار": "قهوه و اسپرسو ساز",
    "built-in-espresso-maker": "قهوه و اسپرسو ساز",
    "کتری برقی": "چای ساز",
    "electric-kettle": "چای ساز",
    "همزن": "همزن برقی",
    "stirrer": "همزن برقی",
    "مخلوط کن": "غذا ساز",
    "mixer": "غذا ساز",
    "غذا ساز": "غذا ساز",
    "food-processor": "غذا ساز",
    "آماده سازی غذا": "غذا ساز",
    "food-preparation": "غذا ساز",
    "صبحانه ساز": "صبحانه ساز",
    "breakfast-maker": "صبحانه ساز",
    "توستر": "توستر",
    "toaster": "توستر",
    "چرخ گوشت": "چرخ گوشت",
    "meat-grinder": "چرخ گوشت",
    "اجاق گاز": "اجاق گاز",
    "gas-stove": "اجاق گاز",
    "صفحه گازی": "اجاق گاز/صفحه",
    "gas-plate": "اجاق گاز/صفحه",
    "صفحه برقی": "اجاق گاز/صفحه",
    "electric-plate": "اجاق گاز/صفحه",
    "پخت و پز": "اجاق گاز/صفحه",
    "cooking": "اجاق گاز/صفحه",
    "گریل": "گریل و ساندویچ ساز",
    "grill": "گریل و ساندویچ ساز",
    "گریل توکار": "گریل و ساندویچ ساز",
    "built-in-grill": "گریل و ساندویچ ساز",
    "سرخکن توکار": "سرخکن",
    "built-in-fryer": "سرخکن",
    "بخارپز توکار": "بخارپز",
    "built-in-steamer": "بخارپز",
    "کشو گرمکن": "کشو گرمکن",
    "warming-drawer": "کشو گرمکن",
    "گرمایش و سرمایش": "گرمایش و سرمایش",
    "heating-and-cooling": "گرمایش و سرمایش",
    "آبسردکن": "آب سردکن",
    "water-cooler": "آب سردکن",
    "پلوپز": "پلوپز",
    "rice-cooker": "پلوپز",
    "هواپز": "هواپز",
    "بستنی ساز": "بستنی ساز",
    "اسموتی ساز": "اسموتی ساز",
    "سوپرخ کن": "سرخکن",
    "لوازم جانبی فر": "لوازم جانبی",
    "لوازم جانبی هود": "لوازم جانبی",
    "لوازم جانبی جاروبرقی": "لوازم جانبی",
    "لوازم جانبی لباسشویی": "لوازم جانبی",
    "لوازم جانبی": "لوازم جانبی",
    "accessories": "لوازم جانبی",
    "built-in": "توکار",
    "free-standing": "آزاد",
    "available-products": "موجود",
    "cp": ".cp",
}

# ── Persian stop-words (for token filtering) ────────────────────────────────

PERSIAN_STOP_WORDS: set[str] = {
    "مدل", "برند", "نوع", "سایز", "ظرفیت", "قدرت", "توان", "رنگ", "ولت", "وات",
    "اصل", "اورجینال", "فابریک", "اصلی", "طرح", "سازگار", "مناسب",
    "بوش", "bosch",
    "ک", "ه", "و", "در", "با", "برای", "از", "به",
}

ENGLISH_STOP_WORDS: set[str] = {
    "model", "brand", "type", "size", "capacity", "power", "watt", "volt", "color",
    "original", "genuine", "compatible", "for", "the", "and", "with", "new",
    "bosch", "bosc",
}


def normalize_unicode(text: str) -> str:
    """NFKC unicode normalization."""
    return unicodedata.normalize("NFKC", text)


def normalize_arabic_to_persian(text: str) -> str:
    """Convert Arabic characters to Persian equivalents."""
    for arabic, persian in _ARABIC_TO_PERSIAN.items():
        text = text.replace(arabic, persian)
    return text


def normalize_digits(text: str) -> str:
    """Convert Persian and Arabic-Indic digits to ASCII digits."""
    for fd, ad in _FARSI_DIGITS.items():
        text = text.replace(fd, ad)
    for ad, ascii_d in _ARABIC_INDIC_DIGITS.items():
        text = text.replace(ad, ascii_d)
    return text


def normalize_whitespace(text: str) -> str:
    """Remove zero-width characters and collapse whitespace."""
    text = text.replace("\u200c", " ")  # ZWNJ
    text = text.replace("\u200b", " ")  # ZWSP
    text = text.replace("\ufeff", "")   # BOM
    text = text.replace("\u200d", " ")  # ZWJ
    text = text.replace("\u00a0", " ")  # NBSP
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_punctuation(text: str) -> str:
    """Normalize punctuation and hyphens."""
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace("−", "-")
    text = text.replace(";", ",")
    text = text.replace("؛", ",")
    text = text.replace("،", ",")
    return text


def normalize_brand(brand: str) -> str:
    """Normalize brand name to canonical form."""
    lower = brand.strip().lower()
    return BRAND_ALIASES.get(lower, brand.strip())


def normalize_category(category: str) -> str:
    """Map Nabkade/Torob category to canonical form."""
    trimmed = category.strip()
    lower = trimmed.lower()
    if lower in CATEGORY_MAP:
        return CATEGORY_MAP[lower]
    if trimmed in CATEGORY_MAP:
        return CATEGORY_MAP[trimmed]
    return trimmed


def remove_stop_words(text: str) -> str:
    """Remove Persian and English stop-words from text."""
    tokens = text.split()
    filtered = [
        t for t in tokens
        if t.lower() not in PERSIAN_STOP_WORDS
        and t.lower() not in ENGLISH_STOP_WORDS
    ]
    return " ".join(filtered)


def normalize_title(text: str) -> str:
    """Full normalization pipeline for a product title.

    Pipeline:
        1. Unicode NFKC
        2. Arabic → Persian
        3. Digit normalization
        4. Whitespace normalization
        5. Punctuation normalization
        6. Lowercase English (preserve uppercase for SKU extraction)
    """
    text = normalize_unicode(text)
    text = normalize_arabic_to_persian(text)
    text = normalize_digits(text)
    text = normalize_whitespace(text)
    text = normalize_punctuation(text)
    return text


def normalize_title_for_matching(text: str) -> str:
    """Full normalization plus lowercase for token-level matching."""
    text = normalize_title(text)
    return text.lower()


def normalize_sku_text(text: str) -> str:
    """Normalize text specifically for SKU extraction.

    Preserves case but removes interfering characters.
    """
    text = normalize_title(text)
    text = text.replace("-", "")
    text = text.replace(".", "")
    text = text.replace("/", "")
    text = re.sub(r"\s+", " ", text)
    return text
