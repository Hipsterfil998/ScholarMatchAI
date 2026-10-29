"""jobs.ac.uk scraper — UK academic job board."""

from __future__ import annotations

from urllib.parse import quote_plus

from agent.search.scrapers.base import BaseScraper, _MAX_RESULTS


class JobsAcUkScraper(BaseScraper):
    """Scrapes jobs.ac.uk with keyword and facet filters. UK only."""

    name = "jobs.ac.uk"

    def scrape(self, field: str, location: str, position_type: str) -> list[dict]:
        keywords = field
        params = [
            f"keywords={quote_plus(keywords)}",
            "sortOrder=2",
            f"pageSize={_MAX_RESULTS}",
        ]

        if position_type == "phd":
            params.append("jobTypeFacet[]=phds")
        elif position_type == "postdoc":
            params[0] = f"keywords={quote_plus(field + ' postdoc')}"
        elif position_type == "fellowship":
            params[0] = f"keywords={quote_plus(field + ' fellowship')}"
        elif position_type == "research_staff":
            params[0] = f"keywords={quote_plus(field + ' researcher')}"

        if location and location.lower() not in ("anywhere", "worldwide", ""):
            params.append(f"location={quote_plus(location)}")

        url = "https://www.jobs.ac.uk/search/?" + "&".join(params)
        soup = self._fetch(url)
        if soup is None:
            return []

        listings: list[dict] = []
        for card in soup.select("div[data-advert-id], .j-search-result__result")[:_MAX_RESULTS]:
            title_el = card.select_one(".j-search-result__text > a")
            if not title_el:
                continue

            href = title_el.get("href", "")
            full_url = ("https://www.jobs.ac.uk" + href) if href.startswith("/") else href

            dept_el = card.select_one(".j-search-result__department")
            employer_el = card.select_one(
                ".j-search-result__employer b, .j-search-result__employer"
            )
            date_el = card.select_one(".j-search-result__date--blue")
            salary_el = card.select_one(".j-search-result__info")

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

            title_text = title_el.get_text(strip=True)
            listings.append({
                "title": title_text,
                "institution": employer_el.get_text(strip=True) if employer_el else "",
                "location": loc_text,
                "url": full_url,
                "description": description,
                "deadline": date_el.get_text(strip=True) if date_el else None,
                "email": None,
                "source": self.name,
                "type": self._detect_type(title_text, description),
            })

        return listings
