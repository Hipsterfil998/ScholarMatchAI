"""nature.com/careers scraper — multidisciplinary global academic job board."""

from __future__ import annotations

import re
from typing import ClassVar
from urllib.parse import quote_plus

from agent.search.scrapers.base import (
    BaseScraper,
    _CC_COUNTRY,
    _EUROPEAN_CC,
    _MAX_RESULTS,
    _UK_ALIASES,
)


class NatureCareersScraper(BaseScraper):
    """Scrapes nature.com/careers with keyword search and client-side location filter.

    The parsing below is generic to the Madgex job-board platform
    (``li.lister__item`` cards).  Other boards on the same platform only need
    to override ``name``, ``_ORIGIN`` and ``_SEARCH_URL`` — see
    :class:`~agent.search.scrapers.science_careers.ScienceCareersScraper`.
    """

    name = "nature.com/careers"

    _ORIGIN: ClassVar[str] = "https://www.nature.com"
    _SEARCH_URL: ClassVar[str] = (
        "https://www.nature.com/naturecareers/jobs/search/?q={q}&pageSize={n}"
    )

    def scrape(self, field: str, location: str, position_type: str) -> list[dict]:
        url = self._SEARCH_URL.format(q=quote_plus(field), n=_MAX_RESULTS)
        soup = self._fetch(url)
        if soup is None:
            return []

        loc_lower = location.lower()
        is_worldwide = loc_lower in ("worldwide", "")
        is_europe = loc_lower in ("europe", "europe (all)")
        # Resolve UK aliases to a single canonical string for matching
        canonical_loc = "united kingdom" if loc_lower in _UK_ALIASES else loc_lower

        listings: list[dict] = []
        for item in soup.select("li.lister__item")[:_MAX_RESULTS]:
            title_el = item.select_one("h3.lister__header a")
            if not title_el:
                continue

            href = title_el.get("href", "").strip()
            if not href:
                continue
            full_url = (self._ORIGIN + href) if href.startswith("/") else href

            loc_el = item.select_one(".lister__meta-item--location")
            loc_text = loc_el.get_text(strip=True) if loc_el else ""

            # Extract ISO 2-letter country code from e.g. "Berlin (DE)"
            cc_match = re.search(r"\(([A-Z]{2})\)\s*$", loc_text)
            cc = cc_match.group(1) if cc_match else ""
            country_name = _CC_COUNTRY.get(cc, "")

            # Location filtering
            if not is_worldwide:
                if is_europe:
                    if cc and cc not in _EUROPEAN_CC:
                        continue
                else:
                    # Specific country: match via country code → name, or direct text
                    if cc:
                        if country_name != canonical_loc:
                            continue
                    elif canonical_loc not in loc_text.lower():
                        continue

            employer_el = item.select_one(".lister__meta-item--recruiter")
            institution = employer_el.get_text(strip=True) if employer_el else ""

            desc_el = item.select_one("p:not(.badge)")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            # "New" badge means posted within last 2 days; no exact date available
            is_new = bool(item.select_one(".badge--green"))
            posted = "1 day ago" if is_new else None

            title_text = re.sub(r"\s+", " ", title_el.get_text(" ", strip=True)).strip()
            listings.append({
                "title": title_text,
                "institution": institution,
                "location": loc_text,
                "url": full_url,
                "description": desc,
                "deadline": None,
                "posted": posted,
                "email": self._extract_email(desc),
                "source": self.name,
                "type": self._detect_type(title_text, desc),
            })

        return listings
