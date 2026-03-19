"""Abstract base class and shared utilities for all job board scrapers."""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import ClassVar

import requests
from bs4 import BeautifulSoup


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

_DELAY = 1.5  # polite delay between HTTP requests (seconds)

_TYPE_KEYWORDS: dict[str, list[str]] = {
    "predoctoral": [
        "predoctoral", "pre-doctoral", "pre doctoral",
        "master student", "master's student", "msc student",
        "junior researcher", "research trainee", "research internship",
        "early-stage researcher", "early stage researcher", "esr",
    ],
    "phd": [
        "phd", "ph.d", "doctoral", "doctorate",
        "phd student", "phd candidate", "phd position",
        "phd fellowship", "graduate student", "studentship",
    ],
    "postdoc": [
        "postdoc", "post-doc", "post doc", "postdoctoral",
        "research associate", "research fellow",
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
    def _extract_email(text: str) -> str | None:
        """Extract the first email address found in ``text``, or ``None``."""
        m = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
        return m.group() if m else None

    @staticmethod
    def _parse_date(text: str | None) -> datetime | None:
        """Parse a free-form date string into a ``datetime``, or ``None`` on failure.

        Handles formats produced by Euraxess, mlscientist, and jobs.ac.uk:
        - ISO: ``2025-03-15`` or ``2025-03-15T10:00:00``
        - ``15 March 2025`` / ``15 Mar 2025``
        - ``March 15, 2025`` / ``Mar 15, 2025``
        - ``15/03/2025``
        Leading prefixes ("Posted on:", "Closes", "Deadline:", …) are stripped.
        """
        if not text:
            return None
        # Strip common prefixes
        text = re.sub(
            r"^(posted\s+on\s*:?|closes?\s*:?|deadline\s*:?|closing\s+date\s*:?)\s*",
            "", text.strip(), flags=re.IGNORECASE,
        ).strip()
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
