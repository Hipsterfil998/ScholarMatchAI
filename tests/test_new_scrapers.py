"""Tests for NatureCareersScraper and ScienceCareersScraper — no real HTTP calls."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from agent.search.scrapers.nature_careers import NatureCareersScraper
from agent.search.scrapers.science_careers import ScienceCareersScraper


# ---------------------------------------------------------------------------
# Minimal HTML fixtures
# ---------------------------------------------------------------------------

_NATURE_HTML = """
<html><body><ul>
<li class="lister__item" id="item-111">
  <p class="badge badge--right badge--green">New</p>
  <div class="lister__details cf js-clickable">
    <h3 class="lister__header">
      <a class="js-clickable-area-link" href="/naturecareers/job/111/phd-ml/">
        <span>PhD position in Machine Learning</span>
      </a>
    </h3>
    <ul class="lister__meta">
      <li class="lister__meta-item lister__meta-item--location">Berlin (DE)</li>
      <li class="lister__meta-item lister__meta-item--recruiter">TU Berlin</li>
    </ul>
    <p>Join our ML group for cutting-edge deep learning research.</p>
  </div>
</li>
<li class="lister__item" id="item-222">
  <div class="lister__details cf js-clickable">
    <h3 class="lister__header">
      <a class="js-clickable-area-link" href="/naturecareers/job/222/postdoc-nlp/">
        <span>Postdoctoral researcher in NLP</span>
      </a>
    </h3>
    <ul class="lister__meta">
      <li class="lister__meta-item lister__meta-item--location">Paris (FR)</li>
      <li class="lister__meta-item lister__meta-item--recruiter">CNRS</li>
    </ul>
    <p>NLP postdoc at CNRS Paris.</p>
  </div>
</li>
</ul></body></html>
"""


def _mock_fetch(html: str):
    """Return a _fetch side_effect that always returns parsed HTML."""
    def _fetch(url, **kwargs):
        return BeautifulSoup(html, "lxml")
    return _fetch


# ---------------------------------------------------------------------------
# NatureCareersScraper
# ---------------------------------------------------------------------------

class TestNatureCareersScraper:
    def _scrape(self, location, html=_NATURE_HTML):
        s = NatureCareersScraper()
        with patch.object(s, "_fetch", side_effect=_mock_fetch(html)):
            return s.scrape("machine learning", location, "any")

    def test_parses_title(self):
        results = self._scrape("")
        titles = [r["title"] for r in results]
        assert "PhD position in Machine Learning" in titles

    def test_parses_institution(self):
        results = self._scrape("")
        assert any(r["institution"] == "TU Berlin" for r in results)

    def test_parses_location(self):
        results = self._scrape("")
        assert any(r["location"] == "Berlin (DE)" for r in results)

    def test_new_badge_sets_posted(self):
        results = self._scrape("")
        berlin = next(r for r in results if r["location"] == "Berlin (DE)")
        assert berlin["posted"] == "1 day ago"

    def test_no_badge_posted_is_none(self):
        results = self._scrape("")
        paris = next(r for r in results if r["location"] == "Paris (FR)")
        assert paris["posted"] is None

    def test_country_filter_germany_only(self):
        results = self._scrape("Germany")
        assert len(results) == 1
        assert results[0]["location"] == "Berlin (DE)"

    def test_country_filter_france_only(self):
        results = self._scrape("France")
        assert len(results) == 1
        assert results[0]["location"] == "Paris (FR)"

    def test_europe_keeps_both(self):
        results = self._scrape("Europe")
        assert len(results) == 2

    def test_worldwide_keeps_all(self):
        results = self._scrape("")
        assert len(results) == 2

    def test_url_is_absolute(self):
        results = self._scrape("")
        for r in results:
            assert r["url"].startswith("https://www.nature.com")

    def test_source_name(self):
        results = self._scrape("")
        assert all(r["source"] == "nature.com/careers" for r in results)

    def test_type_detected(self):
        results = self._scrape("")
        phd = next(r for r in results if "PhD" in r["title"])
        assert phd["type"] == "phd"
        postdoc = next(r for r in results if "Postdoctoral" in r["title"])
        assert postdoc["type"] == "postdoc"

    def test_uk_alias_resolves(self):
        """'UK' should match jobs with country code GB."""
        html = _NATURE_HTML.replace("Berlin (DE)", "London (GB)").replace(
            "TU Berlin", "UCL"
        )
        results = self._scrape("UK", html=html)
        assert len(results) == 1
        assert "GB" in results[0]["location"]


# ---------------------------------------------------------------------------
# keyword_search flag
# ---------------------------------------------------------------------------

class TestKeywordSearchFlags:
    def test_nature_careers_is_keyword_search(self):
        assert NatureCareersScraper.keyword_search is True

    def test_science_careers_is_keyword_search(self):
        assert ScienceCareersScraper.keyword_search is True


# ---------------------------------------------------------------------------
# ScienceCareersScraper — inherits the Madgex parsing from Nature
# ---------------------------------------------------------------------------

class TestScienceCareersScraper:
    def _scrape(self, location, html=_NATURE_HTML):
        s = ScienceCareersScraper()
        with patch.object(ScienceCareersScraper, "_fetch", side_effect=_mock_fetch(html)):
            return s.scrape("machine learning", location, "any")

    def test_parses_cards_with_inherited_logic(self):
        results = self._scrape("")
        assert len(results) == 2
        assert results[0]["title"] == "PhD position in Machine Learning"
        assert results[0]["institution"] == "TU Berlin"

    def test_uses_its_own_origin_for_relative_urls(self):
        results = self._scrape("")
        assert results[0]["url"].startswith("https://jobs.sciencecareers.org/")

    def test_tags_its_own_source_name(self):
        assert all(r["source"] == "sciencecareers" for r in self._scrape(""))

    def test_hits_its_own_search_endpoint(self):
        s = ScienceCareersScraper()
        with patch.object(
            ScienceCareersScraper, "_fetch", side_effect=_mock_fetch(_NATURE_HTML)
        ) as fetch:
            s.scrape("machine learning", "", "any")
        assert "jobs.sciencecareers.org" in fetch.call_args[0][0]

    def test_strips_whitespace_padded_hrefs(self):
        """Science Careers pads its hrefs with newlines and tabs."""
        html = _NATURE_HTML.replace(
            'href="/naturecareers/job/111/phd-ml/"',
            'href="\n\t/job/111/phd-ml/\n\n"',
        )
        results = self._scrape("", html=html)
        assert results[0]["url"] == "https://jobs.sciencecareers.org/job/111/phd-ml/"
