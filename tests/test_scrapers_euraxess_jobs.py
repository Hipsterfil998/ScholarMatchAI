"""Tests for EuraxessScraper and JobsAcUkScraper — no real HTTP."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup

from agent.search.scrapers.euraxess import EuraxessScraper
from agent.search.scrapers.jobs_ac_uk import JobsAcUkScraper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_fetch(html: str):
    def _fetch(url, **kwargs):
        return BeautifulSoup(html, "lxml")
    return _fetch


def _null_fetch(url, **kwargs):
    return None


# ---------------------------------------------------------------------------
# Euraxess HTML fixture
# ---------------------------------------------------------------------------

_EURAXESS_HTML = """
<html><body>
<article class="ecl-content-item">
  <h3 class="ecl-content-block__title">
    <a href="/jobs/12345/phd-machine-learning">PhD in Machine Learning</a>
  </h3>
  <ul>
    <li class="ecl-content-block__primary-meta-item">TU Berlin</li>
    <li class="ecl-content-block__primary-meta-item">Posted on: 10 January 2026</li>
  </ul>
  <div class="ecl-content-block__description">
    <p>Deep learning research position in computer vision.</p>
  </div>
  <div class="id-Work-Locations">
    <span class="ecl-text-standard">Number of offers 1, Germany, Europe</span>
  </div>
  <div class="id-Application-Deadline">
    <span class="ecl-text-standard">30 June 2026</span>
  </div>
</article>
<article class="ecl-content-item">
  <h3 class="ecl-content-block__title">
    <a href="/jobs/67890/postdoc-nlp">Postdoc in NLP</a>
  </h3>
  <ul>
    <li class="ecl-content-block__primary-meta-item">CNRS</li>
    <li class="ecl-content-block__primary-meta-item">Posted on: 5 February 2026</li>
  </ul>
  <div class="ecl-content-block__description">
    <p>Natural language processing postdoctoral position.</p>
  </div>
  <div class="id-Work-Locations">
    <span class="ecl-text-standard">Number of offers 1, France, Europe</span>
  </div>
  <div class="id-Application-Deadline">
    <span class="ecl-text-standard">31 July 2026</span>
  </div>
</article>
</body></html>
"""


class TestEuraxessScraper:
    def _scrape(self, location="", html=_EURAXESS_HTML):
        s = EuraxessScraper()
        with patch.object(s, "_fetch", side_effect=_mock_fetch(html)):
            return s.scrape("machine learning", location, "any")

    def test_parses_title(self):
        results = self._scrape("")
        titles = [r["title"] for r in results]
        assert "PhD in Machine Learning" in titles

    def test_parses_institution(self):
        results = self._scrape("")
        assert any(r["institution"] == "TU Berlin" for r in results)

    def test_parses_posted_date(self):
        results = self._scrape("")
        berlin = next(r for r in results if "Berlin" in r.get("institution", ""))
        assert berlin["posted"] == "10 January 2026"

    def test_parses_deadline(self):
        results = self._scrape("")
        berlin = next(r for r in results if "Berlin" in r.get("institution", ""))
        assert berlin["deadline"] == "30 June 2026"

    def test_parses_description(self):
        results = self._scrape("")
        assert any("deep learning" in r["description"].lower() for r in results)

    def test_url_is_absolute(self):
        results = self._scrape("")
        for r in results:
            assert r["url"].startswith("https://euraxess.ec.europa.eu")

    def test_source_name(self):
        results = self._scrape("")
        assert all(r["source"] == "euraxess" for r in results)

    def test_type_detected_phd(self):
        results = self._scrape("")
        phd = next(r for r in results if "PhD" in r["title"])
        assert phd["type"] == "phd"

    def test_type_detected_postdoc(self):
        results = self._scrape("")
        postdoc = next(r for r in results if "Postdoc" in r["title"])
        assert postdoc["type"] == "postdoc"

    def test_country_filter_germany_only(self):
        results = self._scrape("Germany")
        assert len(results) == 1
        assert "Germany" in results[0]["location"]

    def test_country_filter_france_only(self):
        results = self._scrape("France")
        assert len(results) == 1
        assert "France" in results[0]["location"]

    def test_europe_keeps_all(self):
        results = self._scrape("Europe")
        assert len(results) == 2

    def test_worldwide_keeps_all(self):
        results = self._scrape("")
        assert len(results) == 2

    def test_fetch_failure_returns_empty(self):
        s = EuraxessScraper()
        with patch.object(s, "_fetch", side_effect=_null_fetch):
            results = s.scrape("ML", "Germany", "any")
        assert results == []

    def test_known_country_builds_country_id_url(self):
        """Germany should produce a URL containing job_country[]=794."""
        s = EuraxessScraper()
        called_urls = []
        def _fake_fetch(url, **kwargs):
            called_urls.append(url)
            return BeautifulSoup(_EURAXESS_HTML, "lxml")
        with patch.object(s, "_fetch", side_effect=_fake_fetch):
            s.scrape("NLP", "Germany", "any")
        assert any("job_country%5B%5D=794" in u or "job_country[]=794" in u
                   for u in called_urls)


# ---------------------------------------------------------------------------
# jobs.ac.uk HTML fixture
# ---------------------------------------------------------------------------

_JOBS_AC_UK_HTML = """
<html><body>
<div data-advert-id="1001" class="j-search-result__result">
  <h2 class="j-search-result__text">
    <a href="/jobs/research/phd-ml-oxford">PhD Studentship in Machine Learning</a>
  </h2>
  <span class="j-search-result__department">Department of Computer Science</span>
  <span class="j-search-result__employer"><b>University of Oxford</b></span>
  <span class="j-search-result__date--blue">Closes 30 Jun 2026</span>
  <div>Location: Oxford, UK</div>
</div>
<div data-advert-id="1002" class="j-search-result__result">
  <h2 class="j-search-result__text">
    <a href="/jobs/research/postdoc-nlp-ucl">Postdoctoral Research Fellow in NLP</a>
  </h2>
  <span class="j-search-result__employer"><b>University College London</b></span>
  <span class="j-search-result__date--blue">Closes 15 Jul 2026</span>
  <div>Location: London, UK</div>
</div>
</body></html>
"""


class TestJobsAcUkScraper:
    def _scrape(self, field="machine learning", location="UK",
                position_type="any", html=_JOBS_AC_UK_HTML):
        s = JobsAcUkScraper()
        with patch.object(s, "_fetch", side_effect=_mock_fetch(html)):
            return s.scrape(field, location, position_type)

    def test_parses_title(self):
        results = self._scrape()
        titles = [r["title"] for r in results]
        assert any("Machine Learning" in t for t in titles)

    def test_parses_institution(self):
        results = self._scrape()
        assert any("Oxford" in r["institution"] for r in results)

    def test_parses_deadline(self):
        results = self._scrape()
        oxford = next(r for r in results if "Oxford" in r["institution"])
        assert "30 Jun 2026" in oxford["deadline"]

    def test_url_is_absolute(self):
        results = self._scrape()
        for r in results:
            assert r["url"].startswith("https://www.jobs.ac.uk")

    def test_source_name(self):
        results = self._scrape()
        assert all(r["source"] == "jobs.ac.uk" for r in results)

    def test_type_detected_phd(self):
        results = self._scrape()
        phd = next(r for r in results if "PhD" in r["title"])
        assert phd["type"] == "phd"

    def test_type_detected_postdoc(self):
        results = self._scrape()
        postdoc = next(r for r in results if "Postdoctoral" in r["title"])
        assert postdoc["type"] == "postdoc"

    def test_phd_position_type_adds_facet_to_url(self):
        s = JobsAcUkScraper()
        called_urls = []
        def _fake_fetch(url, **kwargs):
            called_urls.append(url)
            return BeautifulSoup(_JOBS_AC_UK_HTML, "lxml")
        with patch.object(s, "_fake_fetch" if False else "_fetch", side_effect=_fake_fetch):
            s.scrape("ML", "UK", "phd")
        assert any("jobTypeFacet" in u and "phd" in u for u in called_urls)

    def test_postdoc_type_appends_keyword(self):
        s = JobsAcUkScraper()
        called_urls = []
        def _fake_fetch(url, **kwargs):
            called_urls.append(url)
            return BeautifulSoup(_JOBS_AC_UK_HTML, "lxml")
        with patch.object(s, "_fetch", side_effect=_fake_fetch):
            s.scrape("NLP", "UK", "postdoc")
        assert any("postdoc" in u.lower() for u in called_urls)

    def test_fetch_failure_returns_empty(self):
        s = JobsAcUkScraper()
        with patch.object(s, "_fetch", side_effect=_null_fetch):
            results = s.scrape("ML", "UK", "any")
        assert results == []

    def test_two_results_returned(self):
        results = self._scrape()
        assert len(results) == 2

    def test_location_in_result(self):
        results = self._scrape()
        oxford = next(r for r in results if "Oxford" in r["institution"])
        assert "Oxford" in oxford["location"] or "UK" in oxford["location"]


# ---------------------------------------------------------------------------
# keyword_search flag
# ---------------------------------------------------------------------------

class TestKeywordSearchFlags:
    def test_euraxess_is_keyword_search(self):
        assert EuraxessScraper.keyword_search is True

    def test_jobs_ac_uk_is_keyword_search(self):
        assert JobsAcUkScraper.keyword_search is True

