"""Job board scrapers — public surface of the scrapers sub-package."""

from agent.scrapers.euraxess import EuraxessScraper
from agent.scrapers.jobs_ac_uk import JobsAcUkScraper
from agent.scrapers.mlscientist import MLScientistScraper

__all__ = [
    "EuraxessScraper",
    "JobsAcUkScraper",
    "MLScientistScraper",
]
