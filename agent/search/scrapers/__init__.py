"""Job board scrapers — public surface of the scrapers sub-package."""

from agent.search.scrapers.euraxess import EuraxessScraper
from agent.search.scrapers.jobrxiv import JobRxivScraper
from agent.search.scrapers.jobs_ac_uk import JobsAcUkScraper
from agent.search.scrapers.nature_careers import NatureCareersScraper
from agent.search.scrapers.science_careers import ScienceCareersScraper

__all__ = [
    "EuraxessScraper",
    "JobRxivScraper",
    "JobsAcUkScraper",
    "NatureCareersScraper",
    "ScienceCareersScraper",
]
