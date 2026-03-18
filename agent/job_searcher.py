"""Job searcher: finds PhD / postdoc / research positions from free public sources.

Sources:
- Euraxess (European Commission research portal) — RSS feed
- jobs.ac.uk (UK academic jobs) — HTML scraping with facet filters
- FindAPhD (PhD-specific) — HTML scraping

All scrapers are wrapped in try/except — if one source is down the rest continue.
"""

from __future__ import annotations

import re
import time
from typing import TypedDict
from urllib.parse import quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup


class JobListing(TypedDict, total=False):
    title: str
    institution: str
    location: str
    url: str
    description: str
    deadline: str | None
    email: str | None
    source: str
    type: str


_TYPE_KEYWORDS: dict[str, list[str]] = {
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

# Position type → keywords appended to search query for sites without native facets
_TYPE_QUERY: dict[str, str] = {
    "phd": "PhD",
    "postdoc": "postdoc OR \"research associate\" OR \"research fellow\"",
    "fellowship": "fellowship OR scholarship",
    "research_staff": "researcher OR lecturer OR professor",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

_DELAY = 1.5  # polite delay between HTTP requests (seconds)


def _detect_type(title: str, description: str) -> str:
    combined = (title + " " + description).lower()
    for pos_type, keywords in _TYPE_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return pos_type
    return "other"


def _extract_email(text: str) -> str | None:
    m = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    return m.group() if m else None


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


# ---------------------------------------------------------------------------
# Source scrapers
# ---------------------------------------------------------------------------

def _search_euraxess(field: str, location: str, position_type: str) -> list[dict]:
    """Euraxess RSS feed — European research portal (EC)."""
    query = field
    if position_type != "any" and position_type in _TYPE_QUERY:
        query = f"{field} {_TYPE_QUERY[position_type]}"

    rss_url = f"https://euraxess.ec.europa.eu/jobs/search/rss?query={quote_plus(query)}"

    # Some country codes Euraxess understands; pass through if specific country given
    if location and location.lower() not in ("europe", "anywhere", "worldwide", ""):
        rss_url += f"&country={quote_plus(location)}"

    try:
        feed = feedparser.parse(rss_url)
        listings = []
        for entry in feed.entries[:25]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            # Institution often appears as "author" or in tags
            institution = entry.get("author", "") or entry.get("dc_source", "")
            published = entry.get("published", "") or entry.get("updated", "")
            loc = entry.get("location", "") or location
            listings.append({
                "title": title,
                "institution": institution,
                "location": loc,
                "url": link,
                "description": summary,
                "deadline": published or None,
                "email": _extract_email(summary),
                "source": "euraxess",
                "type": _detect_type(title, summary),
            })
        return listings
    except Exception:
        return []


def _search_jobs_ac_uk(field: str, location: str, position_type: str) -> list[dict]:
    """jobs.ac.uk — UK academic jobs, HTML scraping with facet filters."""
    params = [
        f"keywords={quote_plus(field)}",
        "sortOrder=2",   # sort by closing date
        "pageSize=25",
    ]

    # Map position_type to jobs.ac.uk jobTypeFacet
    if position_type == "phd":
        params.append("jobTypeFacet[]=phds")
    elif position_type == "postdoc":
        # No native postdoc facet — append to keywords
        params[0] = f"keywords={quote_plus(field + ' postdoc')}"
    elif position_type == "fellowship":
        params[0] = f"keywords={quote_plus(field + ' fellowship')}"
    elif position_type == "research_staff":
        params[0] = f"keywords={quote_plus(field + ' researcher')}"

    if location and location.lower() not in ("anywhere", "worldwide", ""):
        params.append(f"location={quote_plus(location)}")

    url = "https://www.jobs.ac.uk/search/?" + "&".join(params)

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        listings = []

        for card in soup.select("div[data-advert-id], .j-search-result__result")[:25]:
            title_el = card.select_one(".j-search-result__text > a")
            if not title_el:
                continue
            href = title_el.get("href", "")
            full_url = ("https://www.jobs.ac.uk" + href) if href.startswith("/") else href

            dept_el = card.select_one(".j-search-result__department")
            employer_el = card.select_one(".j-search-result__employer b, .j-search-result__employer")
            date_el = card.select_one(".j-search-result__date--blue")
            salary_el = card.select_one(".j-search-result__info")

            # Location often in plain text div with "Location:" prefix
            loc_text = location
            for div in card.select("div"):
                t = div.get_text(strip=True)
                if t.startswith("Location:"):
                    loc_text = t.replace("Location:", "").strip()
                    break

            description = " | ".join(filter(None, [
                dept_el.get_text(strip=True) if dept_el else "",
                salary_el.get_text(strip=True) if salary_el else "",
            ]))

            listings.append({
                "title": title_el.get_text(strip=True),
                "institution": employer_el.get_text(strip=True) if employer_el else "",
                "location": loc_text,
                "url": full_url,
                "description": description,
                "deadline": date_el.get_text(strip=True) if date_el else None,
                "email": None,
                "source": "jobs.ac.uk",
                "type": _detect_type(title_el.get_text(strip=True), description),
            })
        return listings
    except Exception:
        return []


def _search_findaphd(field: str, location: str, position_type: str) -> list[dict]:
    """FindAPhD — PhD-focused academic job board."""
    # FindAPhD is only relevant for PhD positions
    if position_type not in ("any", "phd"):
        return []

    url = (
        f"https://www.findaphd.com/phds/"
        f"?Keywords={quote_plus(field)}&Location={quote_plus(location)}"
    )
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        listings = []
        for card in soup.select(".phd-result, .row.phd-result, article.phd-result")[:20]:
            title_el = card.select_one("h3 a, h2 a, .phd-result__title a")
            if not title_el:
                continue
            href = title_el.get("href", "")
            full_url = ("https://www.findaphd.com" + href) if href.startswith("/") else href
            inst_el = card.select_one(".phd-result__dept, .phd-result__uni, .uni-link")
            desc_el = card.select_one(".phd-result__description, .project-description, p")
            deadline_el = card.select_one(".deadline, .closing-date, time")
            desc = desc_el.get_text(strip=True) if desc_el else ""
            listings.append({
                "title": title_el.get_text(strip=True),
                "institution": inst_el.get_text(strip=True) if inst_el else "",
                "location": location,
                "url": full_url,
                "description": desc,
                "deadline": deadline_el.get_text(strip=True) if deadline_el else None,
                "email": _extract_email(desc),
                "source": "findaphd",
                "type": "phd",
            })
        return listings
    except Exception:
        return []


# ---------------------------------------------------------------------------
# JobSearcher class
# ---------------------------------------------------------------------------

class JobSearcher:
    """Searches for research/PhD positions across purely academic sources.

    Sources: Euraxess, jobs.ac.uk, FindAPhD.
    """

    def search(
        self,
        field: str,
        location: str = "Europe",
        position_type: str = "any",
    ) -> list[dict]:
        """Search all sources and return deduplicated listings.

        Args:
            field:         Research field (e.g. "machine learning").
            location:      Preferred location (e.g. "Europe", "UK", "Germany").
            position_type: Filter: "phd", "postdoc", "fellowship", "research_staff", "any".

        Returns:
            Deduplicated list of JobListing dicts, sorted with richer entries first.
        """
        pt = position_type.lower() if position_type else "any"
        all_listings: list[dict] = []

        for scraper in [
            lambda f, l: _search_euraxess(f, l, pt),
            lambda f, l: _search_jobs_ac_uk(f, l, pt),
            lambda f, l: _search_findaphd(f, l, pt),
        ]:
            try:
                results = scraper(field, location)
                all_listings.extend(results)
            except Exception:
                pass
            time.sleep(_DELAY)

        all_listings = _deduplicate(all_listings)

        # Post-filter by position_type if site didn't apply it natively
        if pt != "any":
            all_listings = [
                j for j in all_listings
                if j.get("type") == pt or j.get("type") == "other"
            ]

        all_listings.sort(key=lambda j: len(j.get("description") or ""), reverse=True)
        return all_listings
