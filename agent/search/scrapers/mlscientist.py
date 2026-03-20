"""mlscientist.com scraper — ML/AI academic job board."""

from __future__ import annotations

import re
from typing import ClassVar
from urllib.parse import quote_plus

from agent.search.scrapers.base import BaseScraper


class MLScientistScraper(BaseScraper):
    """Scrapes mlscientist.com (WordPress) using category + search."""

    name = "mlscientist"

    _TYPE_SLUG: ClassVar[dict[str, str]] = {
        "phd":            "phd-positions",
        "predoctoral":    "jobs",
        "postdoc":        "postdoc-positions",
        "fellowship":     "jobs",
        "research_staff": "jobs",
        "any":            "jobs",
    }

    _NON_COUNTRY: ClassVar[frozenset[str]] = frozenset({
        "jobs", "phd-positions", "postdoc-positions", "featured",
        "conference-calls", "mlnews",
    })

    _COUNTRY_SLUG: ClassVar[dict[str, str]] = {
        "uk": "united-kingdom",
        "united kingdom": "united-kingdom",
        "great britain": "united-kingdom",
        "england": "united-kingdom",
        "scotland": "united-kingdom",
        "wales": "united-kingdom",
        "germany": "germany",
        "netherlands": "netherlands",
        "denmark": "denmark",
        "france": "france",
        "norway": "norway",
        "austria": "austria",
        "ireland": "ireland",
        "italy": "italy",
        "united states": "united-states",
        "usa": "united-states",
        "spain": "spain",
    }

    def scrape(self, field: str, location: str, position_type: str) -> list[dict]:
        type_slug = self._TYPE_SLUG.get(position_type, "jobs")
        country_slug = self._COUNTRY_SLUG.get(location.lower(), "")

        urls_to_try: list[str] = []
        if country_slug:
            urls_to_try.append(
                f"https://mlscientist.com/category/{country_slug}/?s={quote_plus(field)}"
            )
        urls_to_try.append(
            f"https://mlscientist.com/category/{type_slug}/?s={quote_plus(field)}"
        )

        listings: list[dict] = []
        seen_urls: set[str] = set()

        for url in urls_to_try:
            soup = self._fetch(url)
            if soup is None:
                self._sleep()
                continue

            for card in soup.select("article.type-post")[:15]:
                title_el = card.select_one(".entry-title a, h3 a, h2 a, h1 a")
                if not title_el:
                    continue
                href = title_el.get("href", "")
                if not href or href in seen_urls:
                    continue
                seen_urls.add(href)

                excerpt_el = card.select_one(".entry-summary, .entry-content p, p")
                excerpt = excerpt_el.get_text(strip=True) if excerpt_el else ""

                card_classes = card.get("class", [])
                country_cats = [
                    cl.replace("category-", "").replace("-", " ").title()
                    for cl in card_classes
                    if cl.startswith("category-")
                    and cl.replace("category-", "") not in self._NON_COUNTRY
                ]
                loc_text = country_cats[0] if country_cats else ""

                # Filter by CSS class for mapped countries.
                if (
                    location.lower() not in ("worldwide", "europe", "europe (all)", "")
                    and country_slug
                    and f"category-{country_slug}" not in card_classes
                ):
                    continue

                # For unmapped countries: filter by extracted location text when available.
                if (
                    location.lower() not in ("worldwide", "europe", "europe (all)", "")
                    and not country_slug
                    and loc_text
                    and location.lower() not in loc_text.lower()
                ):
                    continue

                deadline_match = re.search(
                    r"deadline[:\s]+(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{4})",
                    excerpt, re.IGNORECASE,
                )
                deadline = deadline_match.group(1).strip() if deadline_match else None

                time_el = card.select_one("time.entry-date, time[datetime]")
                posted = (
                    time_el.get("datetime") or time_el.get_text(strip=True)
                ) if time_el else None

                title_text = title_el.get_text(strip=True)
                listings.append({
                    "title": title_text,
                    "institution": "",
                    "location": loc_text,
                    "url": href,
                    "description": excerpt,
                    "deadline": deadline,
                    "posted": posted,
                    "email": self._extract_email(excerpt),
                    "source": self.name,
                    "type": self._detect_type(title_text, excerpt),
                })

            self._sleep()

        return listings
