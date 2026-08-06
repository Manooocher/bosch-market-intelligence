"""Browser fingerprint management.

Single source of truth for all HTTP headers.
Every consumer must use this module for headers.
Never hardcode headers in crawler modules.
"""

import logging
import random
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── User-Agent Pool ─────────────────────────────────────────────────────────

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# Map Chrome version to Sec-Ch-Ua
VERSION_SEC_CH = {
    "128": '"Chromium";v="128", "Google Chrome";v="128", "Not=A?Brand";v="24"',
    "127": '"Chromium";v="127", "Google Chrome";v="127", "Not=A?Brand";v="24"',
    "126": '"Chromium";v="126", "Google Chrome";v="126", "Not=A?Brand";v="24"',
    "125": '"Chromium";v="125", "Google Chrome";v="125", "Not=A?Brand";v="24"',
    "124": '"Chromium";v="124", "Google Chrome";v="124", "Not=A?Brand";v="24"',
}


@dataclass
class BrowserProfile:
    """Complete browser fingerprint for one session."""
    user_agent: str
    sec_ch_ua: str
    sec_ch_ua_mobile: str = "?0"
    sec_ch_ua_platform: str = '"Windows"'
    accept: str = "application/json, text/plain, */*"
    accept_language: str = "fa-IR,fa;q=0.9,en;q=0.8"
    accept_encoding: str = "gzip, deflate, br"
    connection: str = "keep-alive"
    origin: str = "https://torob.com"
    referer: str = "https://torob.com/"
    sec_fetch_dest: str = "empty"
    sec_fetch_mode: str = "cors"
    sec_fetch_site: str = "same-site"


class FingerprintManager:
    """Centralized browser identity provider.

    Generates consistent header sets for each session.
    Rotates identity when called (on proxy rotation).
    """

    def __init__(self):
        self._current_ua_index = random.randint(0, len(USER_AGENTS) - 1)
        self._profile = self._build_profile()

    def _build_profile(self) -> BrowserProfile:
        ua = USER_AGENTS[self._current_ua_index]
        version = ua.split("Chrome/")[1].split(".")[0] if "Chrome/" in ua else "128"
        sec_ch_ua = VERSION_SEC_CH.get(version, VERSION_SEC_CH["128"])
        return BrowserProfile(user_agent=ua, sec_ch_ua=sec_ch_ua)

    def get_headers(self) -> dict:
        """Return complete header set for current profile."""
        p = self._profile
        return {
            "Accept": p.accept,
            "Accept-Encoding": p.accept_encoding,
            "Accept-Language": p.accept_language,
            "Connection": p.connection,
            "Origin": p.origin,
            "Referer": p.referer,
            "Sec-Ch-Ua": p.sec_ch_ua,
            "Sec-Ch-Ua-Mobile": p.sec_ch_ua_mobile,
            "Sec-Ch-Ua-Platform": p.sec_ch_ua_platform,
            "Sec-Fetch-Dest": p.sec_fetch_dest,
            "Sec-Fetch-Mode": p.sec_fetch_mode,
            "Sec-Fetch-Site": p.sec_fetch_site,
            "User-Agent": p.user_agent,
        }

    def rotate_identity(self):
        """Select a new browser identity. Called on proxy rotation."""
        old_index = self._current_ua_index
        while self._current_ua_index == old_index and len(USER_AGENTS) > 1:
            self._current_ua_index = random.randint(0, len(USER_AGENTS) - 1)
        self._profile = self._build_profile()
        logger.info(f"Rotated fingerprint to Chrome {self._profile.user_agent.split('Chrome/')[1].split(' ')[0]}")
