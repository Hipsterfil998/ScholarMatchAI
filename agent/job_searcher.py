"""Job searcher: finds PhD / postdoc / research positions from free public sources.

Sources used (all free, no API keys required unless noted):
  1. DuckDuckGo text search  — general web coverage
  2. Euraxess               — European research positions (public JSON API)
  3. jobs.ac.uk             — UK & international academic jobs (RSS feed)
  4. FindAPhD               — PhD-specific listings (scraped HTML)
  5. Academic Positions     — global academic jobs (scraped HTML)

All scrapers are wrapped in try/except — if one source is down the rest continue.
"""

from __future__ import annotations

import re
import time
from typing import Any, TypedDict
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Type definition
# ---------------------------------------------------------------------------

class JobListing(TypedDict, total=False):
    title: str
    institution: str
    location: str
    url: str
    description: str
    deadline: str | None
    email: str | None
    source: str   # "euraxess" | "jobs.ac.uk" | "findaphd" | "academicpositions" | "ddg"
    type: str     # "phd" | "postdoc" | "fellowship" | "research_staff" | "other"


# ---------------------------------------------------------------------------
# Position-type detection
# ---------------------------------------------------------------------------

_TYPE_KEYWORDS: dict[str, list[str]] = {
    "phd": ["phd", "ph.d", "doctoral", "doctorate", "phd student", "phd candidate",
            "phd position", "phd fellowship", "graduate student"],
    "postdoc": ["postdoc", "post-doc", "post doc", "postdoctoral", "research associate",
                "research fellow"],
    "fellowship": ["fellowship", "stipend", "marie curie", "marie skłodowska",
                   "horizon europe", "erc", "scholarship"],
    "research_staff": ["researcher", "research scientist", "research engineer",
                       "staff scientist", "principal investigator", "pi position"],
}


def _detect_type(title: str, description: str) -> str:
    """Classify a position into one of the known types."""
    combined = (title + " " + description).lower()
    for pos_type, keywords in _TYPE_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return pos_type
    return "other"


def _extract_email(text: str) -> str | None:
    """Extract the first email address found in a text block."""
    match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    return match.group() if match else None


def _deduplicate(listings: list[dict]) -> list[dict]:
    """Remove duplicate listings (same URL). Preserves insertion order."""
    seen: set[str] = set()
    result: list[dict] = []
    for item in listings:
        url = (item.get("url") or "").strip().rstrip("/")
        if url and url not in seen:
            seen.add(url)
            result.append(item)
        elif not url:
            result.append(item)  # keep listings without URL rather than silently dropping them
    return result


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# Polite delay between HTTP requests (seconds)
_REQUEST_DELAY = 1.0


# ---------------------------------------------------------------------------
# Source 1: DuckDuckGo
# ---------------------------------------------------------------------------

def _search_duckduckgo(field: str, location: str) -> list[dict]:
    """Search DuckDuckGo with several PhD/postdoc query templates."""
    try:
        from duckduckgo_search import DDGS  # type: ignore
    except ImportError:
        return []

    queries = [
        f"PhD position {field} {location} 2025 site:euraxess.ec.europa.eu",
        f"postdoc {field} {location} 2025 fellowship",
        f"research position {field} {location} university",
        f"PhD fellowship {field} site:findaphd.com",
        f"academic jobs {field} site:jobs.ac.uk",
    ]

    raw: list[dict] = []
    ddgs = DDGS()

    for query in queries:
        try:
            results = ddgs.text(query, max_results=10)
            if results:
                raw.extend(results)
            time.sleep(_REQUEST_DELAY)
        except Exception:
            # DuckDuckGo can rate-limit — silently skip failures
            continue

    listings: list[dict] = []
    for r in raw:
        title = r.get("title", "")
        url = r.get("href", "")
        body = r.get("body", "")
        listing: dict[str, Any] = {
            "title": title,
            "institution": "",
            "location": location,
            "url": url,
            "description": body,
            "deadline": None,
            "email": _extract_email(body),
            "source": "ddg",
            "type": _detect_type(title, body),
        }
        listings.append(listing)

    return listings


# ---------------------------------------------------------------------------
# Source 2: Euraxess (European research positions — public JSON API)
# ---------------------------------------------------------------------------

def _search_euraxess(field: str, location: str) -> list[dict]:
    """Query the Euraxess public API for research positions."""
    # The API path may change — wrapped in try/except
    url = "https://euraxess.ec.europa.eu/api/v1/jobs/search"
    params: dict[str, Any] = {
        "keywords": field,
        "page": 1,
        "per_page": 20,
    }
    # Add country filter if location looks like a country name
    if location and location.lower() not in ("europe", "anywhere", "worldwide", ""):
        params["country"] = location

    try:
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=15)
        if resp.status_code != 200:
            return []

        data = resp.json()
        # The response structure may be a dict with a 'jobs' key or a raw list
        jobs_raw = data if isinstance(data, list) else data.get("jobs", data.get("data", []))
        if not isinstance(jobs_raw, list):
            return []

        listings: list[dict] = []
        for job in jobs_raw:
            title = job.get("title") or job.get("name") or ""
            institution = (
                job.get("organisation") or
                job.get("institution") or
                job.get("employer") or ""
            )
            loc = (
                job.get("location") or
                job.get("country") or
                job.get("city") or
                location
            )
            job_url = job.get("url") or job.get("link") or ""
            desc = job.get("description") or job.get("body") or ""
            deadline = job.get("application_deadline") or job.get("deadline") or None

            listings.append({
                "title": title,
                "institution": institution,
                "location": loc,
                "url": job_url,
                "description": desc,
                "deadline": deadline,
                "email": _extract_email(desc),
                "source": "euraxess",
                "type": _detect_type(title, desc),
            })

        return listings

    except Exception:
        return []


# ---------------------------------------------------------------------------
# Source 3: jobs.ac.uk RSS feed
# ---------------------------------------------------------------------------

def _search_jobs_ac_uk(field: str, location: str) -> list[dict]:
    """Parse the jobs.ac.uk RSS feed for academic positions."""
    try:
        import feedparser  # type: ignore
    except ImportError:
        return []

    rss_url = (
        f"https://www.jobs.ac.uk/search/?keywords={quote_plus(field)}"
        f"&location={quote_plus(location)}&rss=1"
    )

    try:
        feed = feedparser.parse(rss_url)
        listings: list[dict] = []
        for entry in feed.entries[:20]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")
            # jobs.ac.uk uses <author> or <dc_source> for institution
            institution = (
                entry.get("author") or
                entry.get("dc_source") or
                entry.get("tags", [{}])[0].get("term", "") if entry.get("tags") else ""
            )
            deadline = entry.get("published") or None

            listings.append({
                "title": title,
                "institution": institution,
                "location": location,
                "url": link,
                "description": summary,
                "deadline": deadline,
                "email": _extract_email(summary),
                "source": "jobs.ac.uk",
                "type": _detect_type(title, summary),
            })

        return listings

    except Exception:
        return []


# ---------------------------------------------------------------------------
# Source 4: FindAPhD (scrape search results page)
# ---------------------------------------------------------------------------

def _search_findaphd(field: str, location: str) -> list[dict]:
    """Scrape FindAPhD search results for PhD listings."""
    url = (
        f"https://www.findaphd.com/phds/?"
        f"Keywords={quote_plus(field)}&Location={quote_plus(location)}"
    )

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        listings: list[dict] = []

        # FindAPhD wraps each result in a div with class "phd-result"
        for card in soup.select(".phd-result, .row.phd-result, article.phd-result")[:20]:
            # Title
            title_el = card.select_one("h3 a, h2 a, .phd-result__title a")
            title = title_el.get_text(strip=True) if title_el else ""
            href = title_el.get("href", "") if title_el else ""
            full_url = ("https://www.findaphd.com" + href) if href.startswith("/") else href

            # Institution
            inst_el = card.select_one(".phd-result__dept, .phd-result__uni, .uni-link")
            institution = inst_el.get_text(strip=True) if inst_el else ""

            # Description / funding info
            desc_el = card.select_one(".phd-result__description, .project-description, p")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            # Deadline
            deadline_el = card.select_one(".deadline, .closing-date, time")
            deadline = deadline_el.get_text(strip=True) if deadline_el else None

            if title:
                listings.append({
                    "title": title,
                    "institution": institution,
                    "location": location,
                    "url": full_url,
                    "description": desc,
                    "deadline": deadline,
                    "email": _extract_email(desc),
                    "source": "findaphd",
                    "type": "phd",
                })

        return listings

    except Exception:
        return []


# ---------------------------------------------------------------------------
# Source 5: Academic Positions (scrape search results)
# ---------------------------------------------------------------------------

def _search_academic_positions(field: str, location: str) -> list[dict]:
    """Scrape Academic Positions for research/faculty positions."""
    url = (
        f"https://academicpositions.com/find-jobs/?"
        f"query={quote_plus(field)}&location={quote_plus(location)}"
    )

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        listings: list[dict] = []

        # Academic Positions uses article tags or divs with job-item class
        for card in soup.select("article.job, .job-item, li.job-listing, .vacancy-item")[:20]:
            title_el = card.select_one("h2 a, h3 a, .job-title a, a.job-link")
            title = title_el.get_text(strip=True) if title_el else ""
            href = title_el.get("href", "") if title_el else ""
            if href and not href.startswith("http"):
                href = "https://academicpositions.com" + href

            inst_el = card.select_one(".employer, .institution, .university")
            institution = inst_el.get_text(strip=True) if inst_el else ""

            loc_el = card.select_one(".location, .job-location")
            loc = loc_el.get_text(strip=True) if loc_el else location

            desc_el = card.select_one(".description, .job-description, p")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            deadline_el = card.select_one(".deadline, .closing, time")
            deadline = deadline_el.get_text(strip=True) if deadline_el else None

            if title:
                listings.append({
                    "title": title,
                    "institution": institution,
                    "location": loc,
                    "url": href,
                    "description": desc,
                    "deadline": deadline,
                    "email": _extract_email(desc),
                    "source": "academicpositions",
                    "type": _detect_type(title, desc),
                })

        return listings

    except Exception:
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_jobs(
    field: str,
    location: str = "Europe",
    position_type: str = "any",
    console=None,
) -> list[dict]:
    """Search for research/PhD positions across all available free sources.

    Args:
        field:         Research field (e.g. "machine learning", "molecular biology").
        location:      Preferred location (e.g. "Europe", "UK", "Germany").
        position_type: Filter by type: "phd", "postdoc", "fellowship", "research_staff",
                       "other", or "any" (no filter).
        console:       Optional rich Console for progress messages.

    Returns:
        Deduplicated list of JobListing dicts, sorted with richer entries first.
    """

    def _log(msg: str) -> None:
        if console:
            console.print(msg)

    all_listings: list[dict] = []
    source_counts: dict[str, int] = {}

    # --- DuckDuckGo ---
    _log("[cyan]  Searching DuckDuckGo...[/cyan]")
    try:
        ddg = _search_duckduckgo(field, location)
        all_listings.extend(ddg)
        source_counts["DuckDuckGo"] = len(ddg)
        _log(f"    [green]{len(ddg)} results[/green]")
    except Exception as exc:
        _log(f"    [yellow]DuckDuckGo failed: {exc}[/yellow]")

    time.sleep(_REQUEST_DELAY)

    # --- Euraxess ---
    _log("[cyan]  Searching Euraxess...[/cyan]")
    try:
        eur = _search_euraxess(field, location)
        all_listings.extend(eur)
        source_counts["Euraxess"] = len(eur)
        _log(f"    [green]{len(eur)} results[/green]")
    except Exception as exc:
        _log(f"    [yellow]Euraxess failed: {exc}[/yellow]")

    time.sleep(_REQUEST_DELAY)

    # --- jobs.ac.uk ---
    _log("[cyan]  Searching jobs.ac.uk...[/cyan]")
    try:
        jac = _search_jobs_ac_uk(field, location)
        all_listings.extend(jac)
        source_counts["jobs.ac.uk"] = len(jac)
        _log(f"    [green]{len(jac)} results[/green]")
    except Exception as exc:
        _log(f"    [yellow]jobs.ac.uk failed: {exc}[/yellow]")

    time.sleep(_REQUEST_DELAY)

    # --- FindAPhD ---
    _log("[cyan]  Searching FindAPhD...[/cyan]")
    try:
        fap = _search_findaphd(field, location)
        all_listings.extend(fap)
        source_counts["FindAPhD"] = len(fap)
        _log(f"    [green]{len(fap)} results[/green]")
    except Exception as exc:
        _log(f"    [yellow]FindAPhD failed: {exc}[/yellow]")

    time.sleep(_REQUEST_DELAY)

    # --- Academic Positions ---
    _log("[cyan]  Searching Academic Positions...[/cyan]")
    try:
        acp = _search_academic_positions(field, location)
        all_listings.extend(acp)
        source_counts["AcademicPositions"] = len(acp)
        _log(f"    [green]{len(acp)} results[/green]")
    except Exception as exc:
        _log(f"    [yellow]Academic Positions failed: {exc}[/yellow]")

    # De-duplicate by URL
    all_listings = _deduplicate(all_listings)

    # Filter by position type if requested
    if position_type and position_type.lower() != "any":
        all_listings = [j for j in all_listings if j.get("type") == position_type.lower()]

    # Sort: listings with descriptions first (more useful for downstream scoring)
    all_listings.sort(key=lambda j: len(j.get("description") or ""), reverse=True)

    if console:
        total = sum(source_counts.values())
        console.print(
            f"\n[bold]Total found:[/bold] {total} raw → "
            f"[bold]{len(all_listings)}[/bold] after deduplication"
        )
        for src, count in source_counts.items():
            console.print(f"  {src}: {count}")

    return all_listings
