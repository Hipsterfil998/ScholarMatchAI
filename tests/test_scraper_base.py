"""Tests for BaseScraper static helpers — no HTTP calls needed."""

from datetime import datetime
import pytest
from agent.search.scrapers.base import BaseScraper


class TestParseDate:
    def _p(self, text):
        return BaseScraper._parse_date(text)

    def test_none_returns_none(self):
        assert self._p(None) is None

    def test_empty_returns_none(self):
        assert self._p("") is None

    def test_garbage_returns_none(self):
        assert self._p("no date here") is None

    def test_iso_date(self):
        assert self._p("2025-03-15") == datetime(2025, 3, 15)

    def test_iso_datetime(self):
        assert self._p("2025-11-01T10:30:00") == datetime(2025, 11, 1)

    def test_dd_month_yyyy_full(self):
        assert self._p("15 March 2025") == datetime(2025, 3, 15)

    def test_dd_month_yyyy_abbrev(self):
        assert self._p("3 Apr 2026") == datetime(2026, 4, 3)

    def test_month_dd_yyyy(self):
        assert self._p("March 15, 2025") == datetime(2025, 3, 15)

    def test_month_dd_yyyy_no_comma(self):
        assert self._p("January 5 2026") == datetime(2026, 1, 5)

    def test_dd_mm_yyyy_slash(self):
        assert self._p("15/03/2025") == datetime(2025, 3, 15)

    def test_strips_posted_on_prefix(self):
        assert self._p("Posted on: 15 March 2025") == datetime(2025, 3, 15)

    def test_strips_closes_prefix(self):
        assert self._p("Closes 3 Apr 2026") == datetime(2026, 4, 3)

    def test_strips_deadline_prefix(self):
        assert self._p("Deadline: 01/06/2026") == datetime(2026, 6, 1)

    def test_case_insensitive_prefix(self):
        assert self._p("POSTED ON: 10 January 2026") == datetime(2026, 1, 10)

    # -- relative dates (jobRxiv / nature.com format) --------------------------

    def test_relative_hours_ago(self):
        result = self._p("about 3 hours ago")
        assert result is not None
        delta = (datetime.now() - result).total_seconds()
        assert 0 <= delta < 4 * 3600  # within 4 h of now

    def test_relative_days_ago(self):
        result = self._p("5 days ago")
        assert result is not None
        delta_days = (datetime.now() - result).days
        assert 4 <= delta_days <= 6

    def test_relative_weeks_ago(self):
        result = self._p("2 weeks ago")
        assert result is not None
        delta_days = (datetime.now() - result).days
        assert 13 <= delta_days <= 15

    def test_relative_months_ago(self):
        result = self._p("about 1 month ago")
        assert result is not None
        delta_days = (datetime.now() - result).days
        assert 28 <= delta_days <= 32

    def test_relative_years_ago(self):
        result = self._p("1 year ago")
        assert result is not None
        delta_days = (datetime.now() - result).days
        assert 363 <= delta_days <= 367

    def test_relative_minutes_ago(self):
        result = self._p("10 minutes ago")
        assert result is not None
        delta = (datetime.now() - result).total_seconds()
        assert 0 <= delta < 11 * 60


class TestDetectType:
    def _d(self, title, desc=""):
        return BaseScraper._detect_type(title, desc)

    def test_phd_in_title(self):
        assert self._d("PhD Position in Machine Learning") == "phd"

    def test_postdoc_in_title(self):
        assert self._d("Postdoctoral Researcher in NLP") == "postdoc"

    def test_fellowship_in_desc(self):
        assert self._d("Research Position", "Marie Curie fellowship available") == "fellowship"

    def test_predoctoral_in_title(self):
        assert self._d("Predoctoral Researcher") == "predoctoral"

    def test_research_staff(self):
        assert self._d("Research Scientist at DeepMind") == "research_staff"

    def test_unknown_returns_other(self):
        assert self._d("Open Position", "Some vague description") == "other"


class TestExtractEmail:
    def _e(self, text):
        return BaseScraper._extract_email(text)

    def test_extracts_simple_email(self):
        assert self._e("Contact us at jobs@mit.edu for details") == "jobs@mit.edu"

    def test_no_email_returns_none(self):
        assert self._e("No contact information provided") is None

    def test_extracts_first_of_multiple(self):
        result = self._e("Email a@x.com or b@y.org")
        assert result == "a@x.com"
