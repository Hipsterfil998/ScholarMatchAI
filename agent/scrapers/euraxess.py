"""Euraxess scraper — EU/worldwide research job portal."""

from __future__ import annotations

import re
from typing import ClassVar
from urllib.parse import quote_plus

from agent.scrapers.base import BaseScraper


class EuraxessScraper(BaseScraper):
    """Scrapes euraxess.ec.europa.eu with country and keyword filters."""

    name = "euraxess"

    _COUNTRY_ID: ClassVar[dict[str, str]] = {
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

    def scrape(self, field: str, location: str, position_type: str) -> list[dict]:
        params = [f"keywords={quote_plus(field)}"]
        country_id = self._COUNTRY_ID.get(location.lower(), "")
        if country_id:
            params.append(f"job_country[]={country_id}")

        url = "https://euraxess.ec.europa.eu/jobs/search?" + "&".join(params)
        soup = self._fetch(url)
        if soup is None:
            return []

        listings: list[dict] = []
        for card in soup.select("article.ecl-content-item")[:20]:
            title_el = card.select_one(
                "h3.ecl-content-block__title a, h2.ecl-content-block__title a"
            )
            if not title_el:
                continue

            href = title_el.get("href", "")
            full_url = (
                "https://euraxess.ec.europa.eu" + href
            ) if href.startswith("/") else href

            meta_items = card.select(".ecl-content-block__primary-meta-item")
            institution, posted = "", None
            for mi in meta_items:
                txt = mi.get_text(strip=True)
                if txt.startswith("Posted on:"):
                    posted = txt.replace("Posted on:", "").strip()
                elif not institution:
                    institution = txt

            desc_el = card.select_one(
                ".ecl-content-block__description p, .ecl-content-block__description"
            )
            desc = desc_el.get_text(strip=True) if desc_el else ""

            loc_el = card.select_one(".id-Work-Locations .ecl-text-standard")
            loc_text = location
            if loc_el:
                raw = loc_el.get_text(" ", strip=True)
                m = re.search(r"Number of offers[^,]+,\s*([^,]+),", raw)
                loc_text = m.group(1).strip() if m else raw[:60]

            deadline_el = card.select_one(
                ".id-Application-Deadline .ecl-text-standard, [class*=deadline]"
            )
            deadline = deadline_el.get_text(strip=True) if deadline_el else posted

            # Post-filter by country (Euraxess ignores job_country[] server-side)
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
                "posted": posted,
                "email": self._extract_email(desc),
                "source": self.name,
                "type": self._detect_type(title_text, desc),
            })

        return listings
