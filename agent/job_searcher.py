"""Job searcher: finds PhD / postdoc / research positions from free public sources.

Sources:
- jobs.ac.uk (UK academic jobs) — HTML scraping with facet filters; only queried for UK/worldwide
- FindAPhD (worldwide PhD board) — HTML scraping; handles location filtering globally

All scrapers are wrapped in try/except — if one source is down the rest continue.
"""

from __future__ import annotations

import re
import time
from typing import TypedDict
from urllib.parse import quote_plus

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

# Position type → keywords appended to search query for sites without native facets
_TYPE_QUERY: dict[str, str] = {
    "predoctoral": "predoctoral OR \"early-stage researcher\" OR \"research trainee\"",
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

_UK_LOCATIONS = {"uk", "united kingdom", "great britain", "england", "scotland", "wales"}
_WORLDWIDE_LOCATIONS = {"worldwide", "anywhere", "any", "global", ""}

# mlscientist.com WordPress category slugs
_MLSCI_TYPE_SLUG: dict[str, str] = {
    "phd":            "phd-positions",
    "predoctoral":    "jobs",
    "postdoc":        "postdoc-positions",
    "fellowship":     "jobs",
    "research_staff": "jobs",
    "any":            "jobs",
}

# mlscientist.com country slug mapping (lowercase location → slug)
_MLSCI_COUNTRY_SLUG: dict[str, str] = {
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
    "canada": "canada",
    "united states": "united-states",
    "usa": "united-states",
    "spain": "spain",
}


def _is_uk_location(location: str) -> bool:
    return location.lower() in _UK_LOCATIONS


def _is_worldwide(location: str) -> bool:
    return location.lower() in _WORLDWIDE_LOCATIONS


def _search_mlscientist(field: str, location: str, position_type: str) -> list[dict]:
    """mlscientist.com — ML/AI academic job board, WordPress with category + search."""
    type_slug = _MLSCI_TYPE_SLUG.get(position_type, "jobs")
    country_slug = _MLSCI_COUNTRY_SLUG.get(location.lower(), "")

    # Build URLs to query: prefer intersection of type+country when available,
    # always include the type-category search as fallback.
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

    # Non-type category slugs to ignore when extracting country from CSS classes
    _MLSCI_NON_COUNTRY = {
        "jobs", "phd-positions", "postdoc-positions", "featured",
        "conference-calls", "mlnews",
    }

    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
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

                # Country from CSS category classes (e.g. category-germany)
                card_classes = card.get("class", [])
                country_cats = [
                    cl.replace("category-", "").replace("-", " ").title()
                    for cl in card_classes
                    if cl.startswith("category-") and cl.replace("category-", "") not in _MLSCI_NON_COUNTRY
                ]
                loc_text = country_cats[0] if country_cats else location

                # Filter by requested country when a specific one is set
                if (
                    location.lower() not in ("worldwide", "europe", "europe (all)", "")
                    and country_slug
                    and country_slug not in card_classes
                ):
                    continue

                # Extract deadline — stop at end of date (after year or ~25 chars)
                deadline_match = re.search(
                    r"deadline[:\s]+(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{4})",
                    excerpt, re.IGNORECASE,
                )
                deadline = deadline_match.group(1).strip() if deadline_match else None

                title_text = title_el.get_text(strip=True)
                listings.append({
                    "title": title_text,
                    "institution": "",
                    "location": loc_text,
                    "url": href,
                    "description": excerpt,
                    "deadline": deadline,
                    "email": _extract_email(excerpt),
                    "source": "mlscientist",
                    "type": _detect_type(title_text, excerpt),
                })
            time.sleep(_DELAY)
        except Exception:
            continue

    return listings


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


# Euraxess country name → numeric ID used in job_country[] filter
_EURAXESS_COUNTRY_ID: dict[str, str] = {
    "austria": "791", "belgium": "792", "bulgaria": "746", "croatia": "776",
    "cyprus": "777", "czech republic": "747", "denmark": "757", "estonia": "758",
    "finland": "760", "france": "793", "germany": "794", "greece": "779",
    "hungary": "748", "iceland": "762", "ireland": "763", "israel": "730",
    "italy": "781", "latvia": "766", "lithuania": "767", "luxembourg": "796",
    "malta": "782", "netherlands": "798", "norway": "768", "poland": "749",
    "portugal": "784", "romania": "751", "serbia": "786", "slovakia": "753",
    "slovenia": "787", "spain": "788", "sweden": "770", "switzerland": "799",
    "turkey": "739", "uk": "771", "united kingdom": "771",
    "australia": "802", "brazil": "668", "canada": "682", "china": "694",
    "india": "705", "japan": "698", "south korea": "700", "singapore": "720",
    "united states": "804", "usa": "804", "new zealand": "803",
    "south africa": "740",
}


def _search_euraxess(field: str, location: str, position_type: str) -> list[dict]:
    """Euraxess — EU academic & research job portal, HTML scraping with country filter."""
    params = [f"keywords={quote_plus(field)}"]

    country_id = _EURAXESS_COUNTRY_ID.get(location.lower(), "")
    if country_id:
        params.append(f"job_country[]={country_id}")

    url = "https://euraxess.ec.europa.eu/jobs/search?" + "&".join(params)
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        listings = []

        for card in soup.select("article.ecl-content-item")[:20]:
            title_el = card.select_one("h3.ecl-content-block__title a, h2.ecl-content-block__title a")
            if not title_el:
                continue
            href = title_el.get("href", "")
            full_url = ("https://euraxess.ec.europa.eu" + href) if href.startswith("/") else href

            # Institution: first primary-meta-item (before "Posted on:")
            meta_items = card.select(".ecl-content-block__primary-meta-item")
            institution = ""
            posted = None
            for mi in meta_items:
                txt = mi.get_text(strip=True)
                if txt.startswith("Posted on:"):
                    posted = txt.replace("Posted on:", "").strip()
                elif not institution:
                    institution = txt

            desc_el = card.select_one(".ecl-content-block__description p, .ecl-content-block__description")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            # Location from Work Locations block
            loc_el = card.select_one(".id-Work-Locations .ecl-text-standard")
            loc_text = location
            if loc_el:
                raw = loc_el.get_text(" ", strip=True)
                # "Number of offers: 1, Germany, ..." → extract country
                m = re.search(r"Number of offers[^,]+,\s*([^,]+),", raw)
                if m:
                    loc_text = m.group(1).strip()
                else:
                    loc_text = raw[:60]

            # Deadline: look for application deadline
            deadline_el = card.select_one(".id-Application-Deadline .ecl-text-standard, [class*=deadline]")
            deadline = deadline_el.get_text(strip=True) if deadline_el else posted

            # Always post-filter by country when a specific location is requested
            # (job_country[] param is ignored server-side by Euraxess)
            if location.lower() not in ("europe", "europe (all)", "worldwide", ""):
                if location.lower() not in loc_text.lower():
                    continue

            title_text = title_el.get_text(strip=True)
            listings.append({
                "title": title_text,
                "institution": institution,
                "location": loc_text,
                "url": full_url,
                "description": desc,
                "deadline": deadline,
                "email": _extract_email(desc),
                "source": "euraxess",
                "type": _detect_type(title_text, desc),
            })
        return listings
    except Exception:
        return []


_CURRENT_YEAR = "2026"

# Signals that a web result is actually an open job posting
_JOB_SIGNALS = [
    "open position", "open call", "call for applications", "we are recruiting",
    "we are hiring", "vacancy", "apply now", "applications are invited",
    "phd position", "phd studentship", "postdoc position", "postdoctoral position",
    "research fellowship", "funded position", "fully funded", "stipend",
    "deadline", "closing date", "how to apply",
]


def _looks_like_job_posting(title: str, body: str) -> bool:
    combined = (title + " " + body).lower()
    return any(sig in combined for sig in _JOB_SIGNALS)


def _search_web(field: str, location: str, position_type: str) -> list[dict]:
    """DuckDuckGo web search — targeted queries for open academic positions by field and country."""
    try:
        from duckduckgo_search import DDGS  # type: ignore
    except ImportError:
        return []

    loc = location.strip() if location.lower() not in ("worldwide", "anywhere", "") else ""
    yr = _CURRENT_YEAR

    # Build position-type labels for the query
    type_labels: dict[str, str] = {
        "predoctoral":    "predoctoral position OR \"early-stage researcher\"",
        "phd":            "PhD studentship",
        "postdoc":        "postdoctoral position",
        "fellowship":     "research fellowship",
        "research_staff": "research scientist",
        "any":            "PhD OR postdoc OR fellowship",
    }
    type_label = type_labels.get(position_type, "PhD OR postdoc OR fellowship")

    loc_part = f'"{loc}"' if loc else ""

    # Three complementary query strategies targeting active {yr} calls
    queries = [
        f'"{field}" {type_label} {loc_part} "call for applications" {yr}'.strip(),
        f'"{field}" {type_label} {loc_part} "open position" OR "vacancy" {yr} apply'.strip(),
        f'"{field}" {type_label} {loc_part} university funded {yr} deadline'.strip(),
    ]

    raw: list[dict] = []
    ddgs = DDGS()
    for query in queries:
        try:
            results = ddgs.text(query, max_results=8)
            if results:
                raw.extend(results)
            time.sleep(_DELAY)
        except Exception:
            continue

    listings = []
    for r in raw:
        title = r.get("title", "")
        body = r.get("body", "")
        combined = (title + " " + body).lower()

        # Keep only results that mention the current year and look like real job postings
        if yr not in combined:
            continue
        if not _looks_like_job_posting(title, body):
            continue

        listings.append({
            "title": title,
            "institution": "",
            "location": location,
            "url": r.get("href", ""),
            "description": body,
            "deadline": None,
            "email": _extract_email(body),
            "source": "web",
            "type": _detect_type(title, body),
        })
    return listings


# ---------------------------------------------------------------------------
# JobSearcher class
# ---------------------------------------------------------------------------

class JobSearcher:
    """Searches for research/PhD positions across academic sources and web.

    Sources: jobs.ac.uk (UK only), Euraxess (worldwide), mlscientist.com (ML/AI), DuckDuckGo (targeted web search).
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
        # Normalize UI display labels to query-friendly strings
        _normalize = {"Europe (all)": "Europe", "Worldwide": ""}
        location = _normalize.get(location, location)
        all_listings: list[dict] = []

        # jobs.ac.uk is UK-only: only query it when location is UK or worldwide
        scrapers = [
            lambda f, l: _search_euraxess(f, l, pt),
            lambda f, l: _search_mlscientist(f, l, pt),
            lambda f, l: _search_web(f, l, pt),
        ]
        if _is_uk_location(location) or _is_worldwide(location):
            scrapers.insert(0, lambda f, l: _search_jobs_ac_uk(f, l, pt))

        for scraper in scrapers:
            try:
                results = scraper(field, location)
                all_listings.extend(results)
            except Exception:
                pass
            time.sleep(_DELAY)

        all_listings = _deduplicate(all_listings)

        # Post-filter: keep only listings that mention the field in title or description.
        # For each comma/slash-separated phrase: match exact phrase OR require ALL
        # individual words ≥4 chars to appear (AND logic — avoids single-word false positives).
        _stop = {"and", "the", "for", "with", "from", "into", "using", "based", "applied"}
        phrases = [p.strip().lower() for p in re.split(r"[,/]", field) if p.strip()]

        def _field_matches(listing: dict) -> bool:
            # Check title first (most reliable); fall back to description for
            # sources whose server-side search may return short excerpts
            title = (listing.get("title") or "").lower()
            desc = (listing.get("description") or "").lower()
            for phrase in phrases:
                if phrase in title:
                    return True
                words = [w for w in re.split(r"\s+", phrase) if len(w) >= 4 and w not in _stop]
                # ALL words must appear in title OR all in description
                if words and all(w in title for w in words):
                    return True
                if words and all(w in desc for w in words):
                    return True
            return False

        all_listings = [j for j in all_listings if _field_matches(j)]

        # Post-filter by position_type if site didn't apply it natively
        if pt != "any":
            all_listings = [
                j for j in all_listings
                if j.get("type") == pt or j.get("type") == "other"
            ]

        all_listings.sort(key=lambda j: len(j.get("description") or ""), reverse=True)
        return all_listings
