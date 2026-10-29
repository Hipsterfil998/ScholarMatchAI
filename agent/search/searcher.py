"""JobSearcher: orchestrates scrapers and post-filters results."""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import TypedDict

from agent.search.scrapers import (
    EuraxessScraper,
    JobRxivScraper,
    JobsAcUkScraper,
    NatureCareersScraper,
    ScienceCareersScraper,
)
from agent.search.scrapers.base import (
    BaseScraper,
    _DELAY,
    _EUROPEAN_COUNTRIES,
    _UK_ALIASES,
)


from config import config as _cfg
_RECENT_DAYS = _cfg.recent_days
_DEADLINE_WARN_DAYS = _cfg.deadline_warn_days
_STALE_DAYS = _cfg.stale_days

_log = logging.getLogger(__name__)


class JobListing(TypedDict, total=False):
    title: str
    institution: str
    location: str
    url: str
    description: str
    deadline: str | None
    posted: str | None
    freshness: str        # "🟢 Recent" | "🟡 Older" | "🔴 Closing soon" | ""
    email: str | None
    source: str
    type: str


_UK_LOCATIONS = _UK_ALIASES
_WORLDWIDE_LOCATIONS = {"worldwide", "anywhere", "any", "global", ""}
_EUROPEAN_LOCATIONS = _EUROPEAN_COUNTRIES | {"europe", "europe (all)"}


class JobSearcher:
    """Searches for research/PhD positions across all configured job sources.

    Sources
    -------
    - Euraxess — EU/worldwide research portal
    - jobRxiv — global research board, read through its REST API
    - nature.com/careers — multidisciplinary global board
    - jobs.ac.uk — UK academic jobs (only for UK/worldwide searches)
    - Science Careers — US-dominated STEM board (only for non-European searches)

    All scrapers are fault-tolerant: if one source is down the rest continue,
    and the names of the failed sources are reported in ``failed_sources``.
    """

    def __init__(self) -> None:
        self.failed_sources: list[str] = []

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
            Sources that raised are recorded in :attr:`failed_sources`.
        """
        self.failed_sources = []
        pt = (position_type or "phd").lower()
        location = self._normalize_location(location)

        scrapers = self._build_scrapers(location)
        keyword_sources = {s.name for s in scrapers if s.keyword_search}

        all_listings: list[dict] = []
        for scraper in scrapers:
            try:
                found = scraper.scrape(field, location, pt)
            except Exception as exc:
                # One dead board must not fail the whole search, but it must
                # not vanish either: a silent `pass` here made every scraper
                # outage look like "no positions found".
                self.failed_sources.append(scraper.name)
                _log.warning("Scraper %s failed: %s", scraper.name, exc)
            else:
                if not found:
                    _log.info("Scraper %s returned no listings", scraper.name)
                all_listings.extend(found)
            time.sleep(_DELAY)

        all_listings = self._deduplicate(all_listings)

        _stop = {"and", "the", "for", "with", "from", "into", "using", "based", "applied"}
        phrases = [p.strip().lower() for p in re.split(r"[,/]", field) if p.strip()]
        all_listings = [
            j for j in all_listings
            if j.get("source") in keyword_sources or self._field_matches(j, phrases, _stop)
        ]

        if pt != "any":
            all_listings = [
                j for j in all_listings
                if j.get("type") == pt
                or BaseScraper._matches_type(
                    j.get("title") or "", j.get("description") or "", pt
                )
            ]

        now = datetime.now()
        all_listings = [j for j in all_listings if not self._is_stale(j, now)]
        for j in all_listings:
            j["freshness"] = self._freshness_label(j, now)

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
            JobRxivScraper(),
            NatureCareersScraper(),
        ]
        loc = location.lower()
        if loc in _UK_LOCATIONS or loc in _WORLDWIDE_LOCATIONS:
            scrapers.insert(0, JobsAcUkScraper())
        # "uk"/"england"/… are European but are not country names themselves
        if loc in _UK_LOCATIONS:
            loc = "united kingdom"
        # Science Careers is US-dominated and often omits the country code its
        # location filter needs, so it would leak US results into a European
        # search. Enable it only where its catalogue is actually relevant.
        if loc in _WORLDWIDE_LOCATIONS or loc not in _EUROPEAN_LOCATIONS:
            scrapers.append(ScienceCareersScraper())
        return scrapers

    @staticmethod
    def _is_stale(job: dict, now: datetime) -> bool:
        """Return True if the job is clearly outdated and should be excluded.

        A job is stale if:
        - Its posting date is parsed and is more than ``stale_days`` old, OR
        - Its deadline is parsed and has already passed.
        Jobs with no date information are kept (benefit of the doubt).

        The age is measured in days rather than calendar years: comparing years
        dropped every still-open position from December as soon as January began.
        """
        posted = BaseScraper._parse_date(job.get("posted"))
        if posted is not None and (now.date() - posted.date()).days > _STALE_DAYS:
            return True
        deadline = BaseScraper._parse_date(job.get("deadline"))
        if deadline is not None and deadline.date() < now.date():
            return True
        return False

    @staticmethod
    def _freshness_label(job: dict, now: datetime) -> str:
        """Return a human-readable freshness indicator for the job.

        Priority:
        1. 🔴 Closing soon — deadline within _DEADLINE_WARN_DAYS days
        2. 🟢 Recent       — posted within _RECENT_DAYS days
        3. 🟡 Older        — has date info but outside the above windows
        4. ""              — no date information available
        """
        deadline = BaseScraper._parse_date(job.get("deadline"))
        if deadline is not None:
            days_left = (deadline.date() - now.date()).days
            if 0 <= days_left <= _DEADLINE_WARN_DAYS:
                return "🔴 Closing soon"

        posted = BaseScraper._parse_date(job.get("posted"))
        if posted is not None:
            days_ago = (now.date() - posted.date()).days
            if days_ago <= _RECENT_DAYS:
                return "🟢 Recent"
            return "🟡 Older"

        if deadline is not None:
            return "🟡 Older"

        return ""

    @staticmethod
    def _sort_key(job: dict) -> tuple:
        """Sort key: (has_date, posted_datetime, description_length).

        Jobs with a known posting date are ranked first, most recent first.
        Within the same date (or when no date is available), longer descriptions rank higher.
        """
        from agent.search.scrapers.base import BaseScraper
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
