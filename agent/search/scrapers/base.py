"""Abstract base class and shared utilities for all job board scrapers."""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import ClassVar

import requests
from bs4 import BeautifulSoup

from config import config


_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

_DELAY = config.scraper_delay      # polite delay between HTTP requests (seconds)
_MAX_RESULTS = config.max_results_per_source  # cap on listings taken per board

# ISO 3166-1 alpha-2 → normalised country name (lowercase, matches location strings)
_CC_COUNTRY: dict[str, str] = {
    "AT": "austria", "BE": "belgium", "BG": "bulgaria", "HR": "croatia",
    "CY": "cyprus", "CZ": "czech republic", "DK": "denmark", "EE": "estonia",
    "FI": "finland", "FR": "france", "DE": "germany", "GR": "greece",
    "HU": "hungary", "IE": "ireland", "IT": "italy", "LV": "latvia",
    "LT": "lithuania", "LU": "luxembourg", "MT": "malta", "NL": "netherlands",
    "PL": "poland", "PT": "portugal", "RO": "romania", "SK": "slovakia",
    "SI": "slovenia", "ES": "spain", "SE": "sweden", "GB": "united kingdom",
    "IS": "iceland", "NO": "norway", "CH": "switzerland", "TR": "turkey",
    "RS": "serbia", "US": "united states", "CA": "canada", "AU": "australia",
    "JP": "japan", "KR": "south korea", "CN": "china", "SG": "singapore",
    "IN": "india", "NZ": "new zealand", "ZA": "south africa", "IL": "israel",
    "BR": "brazil",
}

_UK_ALIASES: frozenset[str] = frozenset({"uk", "united kingdom", "great britain", "england", "scotland", "wales"})

_EUROPEAN_CC: frozenset[str] = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE", "GB", "IS", "NO", "CH", "TR", "RS",
})

_EUROPEAN_COUNTRIES: frozenset[str] = frozenset(
    _CC_COUNTRY[cc] for cc in _EUROPEAN_CC if cc in _CC_COUNTRY
)


_TYPE_KEYWORDS: dict[str, list[str]] = {
    "predoctoral": [
        "predoctoral", "pre-doctoral", "pre doctoral",
        "master student", "master's student", "msc student",
        "junior researcher", "research trainee", "research internship",
        "early-stage researcher", "early stage researcher", "esr",
    ],
    # postdoc must be checked before phd: "postdoctoral" contains "doctoral"
    "postdoc": [
        "postdoc", "post-doc", "post doc", "postdoctoral",
        "research associate", "research fellow",
    ],
    "phd": [
        "phd", "ph.d", "doctoral", "doctorate",
        "phd student", "phd candidate", "phd position",
        "phd fellowship", "graduate student", "studentship",
    ],
    "fellowship": [
        "fellowship", "stipend", "marie curie", "marie skłodowska",
        "horizon europe", "erc", "scholarship", "grant",
    ],
    "research_staff": [
        "researcher", "research scientist", "research engineer",
        "staff scientist", "principal investigator", "pi position",
        "lecturer", "professor", "faculty",
    ],
}


class BaseScraper(ABC):
    """Abstract base for all job board scrapers.

    Subclasses implement ``scrape()`` and declare a ``name`` class variable.
    Shared helpers (``_fetch``, ``_sleep``, ``_detect_type``, ``_extract_email``)
    are available to all subclasses.
    """

    name: ClassVar[str] = ""
    keyword_search: ClassVar[bool] = True  # True = board's own engine filters by keyword

    @abstractmethod
    def scrape(self, field: str, location: str, position_type: str) -> list[dict]:
        """Return a list of job listing dicts for the given search parameters."""
        ...

    # ------------------------------------------------------------------
    # Protected helpers
    # ------------------------------------------------------------------

    def _fetch(self, url: str, timeout: int = 15) -> BeautifulSoup | None:
        """GET ``url`` and return a parsed ``BeautifulSoup``, or ``None`` on failure."""
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=timeout)
            if resp.status_code != 200:
                return None
            return BeautifulSoup(resp.text, "lxml")
        except Exception:
            return None

    def _fetch_json(self, url: str, timeout: int = 15):
        """GET ``url`` and return the decoded JSON body, or ``None`` on failure."""
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=timeout)
            if resp.status_code != 200:
                return None
            return resp.json()
        except Exception:
            return None

    def _sleep(self) -> None:
        """Polite delay between requests."""
        time.sleep(_DELAY)

    @staticmethod
    def _detect_type(title: str, description: str) -> str:
        """Infer position type from title and description text."""
        combined = (title + " " + description).lower()
        for pos_type, keywords in _TYPE_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                return pos_type
        return "other"

    @staticmethod
    def _matches_type(title: str, description: str, position_type: str) -> bool:
        """Return True if the listing plausibly matches ``position_type``.

        ``_detect_type`` must pick a single winning label, so a PhD studentship
        described as a "research scholarship" gets labelled ``fellowship`` and
        would be dropped by an equality filter.  This checks the requested
        type's keywords directly, so a listing can match more than one type.
        """
        if position_type in ("", "any"):
            return True
        keywords = _TYPE_KEYWORDS.get(position_type)
        if not keywords:
            return True
        combined = (title + " " + description).lower()
        return any(kw in combined for kw in keywords)

    @staticmethod
    def _extract_email(text: str) -> str | None:
        """Extract the first email address found in ``text``, or ``None``."""
        m = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
        return m.group() if m else None

    @staticmethod
    def _parse_date(text: str | None) -> datetime | None:
        """Parse a free-form date string into a ``datetime``, or ``None`` on failure.

        Handles formats produced by Euraxess, jobs.ac.uk, jobRxiv, and the
        Madgex boards (relative dates):
        - ISO: ``2025-03-15`` or ``2025-03-15T10:00:00``
        - ``15 March 2025`` / ``15 Mar 2025``
        - ``March 15, 2025`` / ``Mar 15, 2025``
        - ``15/03/2025``
        - Relative: ``2 days ago``, ``about 3 hours ago``, ``1 month ago``
        Leading prefixes ("Posted on:", "Closes", "Deadline:", …) are stripped.
        """
        if not text:
            return None
        # Strip common prefixes
        text = re.sub(
            r"^(posted\s+on\s*:?|closes?\s*:?|deadline\s*:?|closing\s+date\s*:?)\s*",
            "", text.strip(), flags=re.IGNORECASE,
        ).strip()
        # Relative dates: "about 3 hours ago", "2 days ago", "1 month ago", etc.
        m = re.search(
            r"(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago",
            text, re.IGNORECASE,
        )
        if m:
            n, unit = int(m.group(1)), m.group(2).lower()
            from datetime import timedelta
            now = datetime.now()
            delta_map = {
                "second": timedelta(seconds=n),
                "minute": timedelta(minutes=n),
                "hour":   timedelta(hours=n),
                "day":    timedelta(days=n),
                "week":   timedelta(weeks=n),
                "month":  timedelta(days=n * 30),
                "year":   timedelta(days=n * 365),
            }
            return now - delta_map[unit]
        # ISO format
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                pass
        # DD/MM/YYYY
        m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if m:
            try:
                return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except ValueError:
                pass
        # DD Month YYYY  or  Month DD, YYYY
        m = re.match(
            r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})"
            r"|([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", text,
        )
        if m:
            try:
                if m.group(1):
                    day, month_str, year = int(m.group(1)), m.group(2).lower()[:3], int(m.group(3))
                else:
                    month_str, day, year = m.group(4).lower()[:3], int(m.group(5)), int(m.group(6))
                month = _MONTH_MAP.get(month_str)
                if month:
                    return datetime(year, month, day)
            except ValueError:
                pass
        return None
