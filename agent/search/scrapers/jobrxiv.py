"""jobRxiv scraper — global research job board (life sciences, CS, data)."""

from __future__ import annotations

import html
from typing import ClassVar
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from agent.search.scrapers.base import (
    BaseScraper,
    _EUROPEAN_COUNTRIES,
    _MAX_RESULTS,
    _UK_ALIASES,
)


# jobRxiv tags every listing with its own region and category taxonomy, exposed
# as CSS classes on the REST payload ("job_listing_region-united-kingdom").
# That is authoritative, so it is preferred over keyword guessing.
_EUROPEAN_SLUGS: frozenset[str] = frozenset(
    c.replace(" ", "-") for c in _EUROPEAN_COUNTRIES
) | frozenset({"europe"})

_CATEGORY_SLUGS: dict[str, tuple[str, ...]] = {
    "phd":            ("phd",),
    "postdoc":        ("postdoc",),
    "fellowship":     ("postdoc",),
    "predoctoral":    ("res-assis", "res-tech"),
    "research_staff": ("researcher", "scientist", "faculty", "pi", "group-leader", "hod"),
}

# Board category → the app's position_type label, for display.
_SLUG_TO_TYPE: dict[str, str] = {
    "phd": "phd", "postdoc": "postdoc", "res-assis": "predoctoral",
    "res-tech": "predoctoral", "researcher": "research_staff",
    "scientist": "research_staff", "faculty": "research_staff",
    "pi": "research_staff", "group-leader": "research_staff",
    "hod": "research_staff",
}


class JobRxivScraper(BaseScraper):
    """Reads jobRxiv through its WordPress REST API — JSON, no HTML scraping."""

    name = "jobrxiv"

    # WordPress caps per_page at 100; fetch a full page and filter locally so
    # that a narrow country filter still has enough candidates to return.
    _PAGE_SIZE: ClassVar[int] = 100
    _API: ClassVar[str] = (
        "https://jobrxiv.org/wp-json/wp/v2/job-listings"
        "?search={q}&per_page={n}&orderby=date"
    )

    def scrape(self, field: str, location: str, position_type: str) -> list[dict]:
        data = self._fetch_json(self._API.format(q=quote_plus(field), n=self._PAGE_SIZE))
        if not isinstance(data, list):
            return []

        loc_lower = location.lower()
        is_worldwide = loc_lower in ("worldwide", "")
        is_europe = loc_lower in ("europe", "europe (all)")
        wanted_region = (
            "united-kingdom" if loc_lower in _UK_ALIASES else loc_lower.replace(" ", "-")
        )
        wanted_cats = _CATEGORY_SLUGS.get(position_type, ())

        listings: list[dict] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            meta = item.get("meta") or {}
            if meta.get("_filled"):
                continue

            classes = item.get("class_list") or []
            regions = [c[len("job_listing_region-"):] for c in classes
                       if c.startswith("job_listing_region-")]
            cats = [c[len("job_listing_category-"):] for c in classes
                    if c.startswith("job_listing_category-")]

            # Location filter — the board's own region tags, when it has any.
            if regions and not is_worldwide:
                if is_europe:
                    if not any(r in _EUROPEAN_SLUGS for r in regions):
                        continue
                elif wanted_region not in regions:
                    continue

            # Type filter — only when the board tagged a category at all.
            if wanted_cats and cats and not any(c in wanted_cats for c in cats):
                continue

            title = html.unescape((item.get("title") or {}).get("rendered", "")).strip()
            if not title:
                continue
            desc = BeautifulSoup(
                (item.get("excerpt") or {}).get("rendered", ""), "lxml"
            ).get_text(" ", strip=True)

            pos_type = next(
                (_SLUG_TO_TYPE[c] for c in cats if c in _SLUG_TO_TYPE),
                self._detect_type(title, desc),
            )

            listings.append({
                "title": title,
                "institution": meta.get("_company_name") or "",
                "location": regions[0].replace("-", " ").title() if regions else "",
                "url": item.get("link") or "",
                "description": desc,
                "deadline": None,
                "posted": item.get("date"),
                "email": self._extract_email(desc),
                "source": self.name,
                "type": pos_type,
            })
            if len(listings) >= _MAX_RESULTS:
                break

        return listings
