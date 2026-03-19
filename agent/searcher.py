"""JobSearcher: orchestrates scrapers and post-filters results."""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import TypedDict

from agent.scrapers import (
    EuraxessScraper,
    JobsAcUkScraper,
    MLScientistScraper,
)
from agent.scrapers.base import BaseScraper, _DELAY


class JobListing(TypedDict, total=False):
    title: str
    institution: str
    location: str
    url: str
    description: str
    deadline: str | None
    posted: str | None
    email: str | None
    source: str
    type: str


_UK_LOCATIONS = {"uk", "united kingdom", "great britain", "england", "scotland", "wales"}
_WORLDWIDE_LOCATIONS = {"worldwide", "anywhere", "any", "global", ""}


class JobSearcher:
    """Searches for research/PhD positions across all configured job sources.

    Sources
    -------
    - Euraxess — EU/worldwide research portal
    - mlscientist.com — ML/AI academic positions
    - jobs.ac.uk — UK academic jobs (only when UK/worldwide location is selected)

    All scrapers are fault-tolerant: if one source is down the rest continue.
    """

    def search(
        self,
        field: str,
        location: str = "Europe",
        position_type: str = "any",
    ) -> list[dict]:
        """Search all sources and return deduplicated, field-filtered listings.

        Args:
            field:         Research field (e.g. "machine learning").
            location:      Preferred location (e.g. "Europe", "UK", "Germany").
            position_type: One of "phd", "postdoc", "fellowship", "research_staff",
                           "predoctoral", or "any".

        Returns:
            Deduplicated list of :class:`JobListing` dicts, richer entries first.
        """
        pt = (position_type or "phd").lower()
        location = self._normalize_location(location)

        all_listings: list[dict] = []
        for scraper in self._build_scrapers(location):
            try:
                all_listings.extend(scraper.scrape(field, location, pt))
            except Exception:
                pass
            time.sleep(_DELAY)

        all_listings = self._deduplicate(all_listings)

        _stop = {"and", "the", "for", "with", "from", "into", "using", "based", "applied"}
        phrases = [p.strip().lower() for p in re.split(r"[,/]", field) if p.strip()]
        all_listings = [j for j in all_listings if self._field_matches(j, phrases, _stop)]

        if pt != "any":
            all_listings = [
                j for j in all_listings
                if j.get("type") == pt or j.get("type") == "other"
            ]

        all_listings.sort(key=self._sort_key, reverse=True)
        return all_listings

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_location(location: str) -> str:
        return {"Europe (all)": "Europe", "Worldwide": ""}.get(location, location)

    @staticmethod
    def _build_scrapers(location: str) -> list[BaseScraper]:
        scrapers: list[BaseScraper] = [
            EuraxessScraper(),
            MLScientistScraper(),
        ]
        if location.lower() in _UK_LOCATIONS or location.lower() in _WORLDWIDE_LOCATIONS:
            scrapers.insert(0, JobsAcUkScraper())
        return scrapers

    @staticmethod
    def _sort_key(job: dict) -> tuple:
        """Sort key: (has_date, posted_datetime, description_length).

        Jobs with a known posting date are ranked first, most recent first.
        Within the same date (or when no date is available), longer descriptions rank higher.
        """
        from agent.scrapers.base import BaseScraper
        posted = BaseScraper._parse_date(job.get("posted"))
        has_date = posted is not None
        dt = posted or datetime.min
        return (has_date, dt, len(job.get("description") or ""))

    @staticmethod
    def _deduplicate(listings: list[dict]) -> list[dict]:
        seen: set[str] = set()
        result: list[dict] = []
        for item in listings:
            url = (item.get("url") or "").strip().rstrip("/")
            if url and url not in seen:
                seen.add(url)
                result.append(item)
            elif not url:
                result.append(item)
        return result

    @staticmethod
    def _field_matches(listing: dict, phrases: list[str], stop: set[str]) -> bool:
        title = (listing.get("title") or "").lower()
        desc = (listing.get("description") or "").lower()
        for phrase in phrases:
            if phrase in title:
                return True
            words = [w for w in re.split(r"\s+", phrase) if len(w) >= 4 and w not in stop]
            if words and all(w in title for w in words):
                return True
            if words and all(w in desc for w in words):
                return True
        return False
