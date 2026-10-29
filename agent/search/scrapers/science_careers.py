"""Science Careers (AAAS) scraper — global STEM academic and industry research jobs."""

from __future__ import annotations

from typing import ClassVar

from agent.search.scrapers.nature_careers import NatureCareersScraper


class ScienceCareersScraper(NatureCareersScraper):
    """Scrapes jobs.sciencecareers.org.

    Runs on the same Madgex platform as nature.com/careers, so the card
    parsing and location filtering are inherited unchanged — only the search
    endpoint differs.  The board is US-dominated and its location strings
    often omit the ``(CC)`` country code, so ``JobSearcher`` only enables it
    for worldwide and non-European searches.
    """

    name = "sciencecareers"

    _ORIGIN: ClassVar[str] = "https://jobs.sciencecareers.org"
    _SEARCH_URL: ClassVar[str] = (
        "https://jobs.sciencecareers.org/jobs/?keywords={q}&PageSize={n}"
    )
