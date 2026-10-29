"""Tests for JobSearcher — filtering, labelling, dedup, sorting. No HTTP."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import pytest
from agent.search.searcher import JobSearcher, _STALE_DAYS


TODAY = datetime.now()
YESTERDAY = TODAY - timedelta(days=1)
LONG_AGO = TODAY - timedelta(days=_STALE_DAYS + 1)
RECENT = TODAY - timedelta(days=10)
OLDER = TODAY - timedelta(days=60)
CLOSING_SOON = TODAY + timedelta(days=7)
FAR_DEADLINE = TODAY + timedelta(days=90)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%d %B %Y")


class TestIsStale:
    def test_posting_older_than_stale_days_filtered(self):
        job = {"posted": _fmt(LONG_AGO), "deadline": None}
        assert JobSearcher._is_stale(job, TODAY)

    def test_december_posting_kept_in_january(self):
        """Regression: the year-based check dropped every open December post
        the moment January started."""
        job = {"posted": "20 December 2025", "deadline": "31 January 2026"}
        assert not JobSearcher._is_stale(job, datetime(2026, 1, 5))

    def test_expired_deadline_filtered(self):
        job = {"posted": None, "deadline": _fmt(YESTERDAY)}
        assert JobSearcher._is_stale(job, TODAY)

    def test_current_year_posting_kept(self):
        job = {"posted": _fmt(RECENT), "deadline": None}
        assert not JobSearcher._is_stale(job, TODAY)

    def test_future_deadline_kept(self):
        job = {"posted": None, "deadline": _fmt(CLOSING_SOON)}
        assert not JobSearcher._is_stale(job, TODAY)

    def test_no_dates_kept(self):
        job = {"posted": None, "deadline": None}
        assert not JobSearcher._is_stale(job, TODAY)

    def test_old_posting_future_deadline_filtered_by_posting(self):
        # posted beyond the staleness window → stale even if deadline is future
        job = {"posted": _fmt(LONG_AGO), "deadline": _fmt(FAR_DEADLINE)}
        assert JobSearcher._is_stale(job, TODAY)


class TestFreshnessLabel:
    def test_recent(self):
        job = {"posted": _fmt(RECENT), "deadline": None}
        assert JobSearcher._freshness_label(job, TODAY) == "🟢 Recent"

    def test_older(self):
        job = {"posted": _fmt(OLDER), "deadline": _fmt(FAR_DEADLINE)}
        assert JobSearcher._freshness_label(job, TODAY) == "🟡 Older"

    def test_closing_soon_overrides_recent(self):
        job = {"posted": _fmt(RECENT), "deadline": _fmt(CLOSING_SOON)}
        assert JobSearcher._freshness_label(job, TODAY) == "🔴 Closing soon"

    def test_no_date_empty_label(self):
        job = {"posted": None, "deadline": None}
        assert JobSearcher._freshness_label(job, TODAY) == ""

    def test_only_far_deadline_no_posted(self):
        job = {"posted": None, "deadline": _fmt(FAR_DEADLINE)}
        assert JobSearcher._freshness_label(job, TODAY) == "🟡 Older"


class TestDeduplicate:
    def test_removes_duplicate_url(self):
        jobs = [
            {"url": "https://example.com/job/1", "title": "A"},
            {"url": "https://example.com/job/1", "title": "A duplicate"},
        ]
        result = JobSearcher._deduplicate(jobs)
        assert len(result) == 1

    def test_trailing_slash_dedup(self):
        jobs = [
            {"url": "https://example.com/job/1/", "title": "A"},
            {"url": "https://example.com/job/1", "title": "B"},
        ]
        assert len(JobSearcher._deduplicate(jobs)) == 1

    def test_different_urls_kept(self):
        jobs = [
            {"url": "https://example.com/job/1", "title": "A"},
            {"url": "https://example.com/job/2", "title": "B"},
        ]
        assert len(JobSearcher._deduplicate(jobs)) == 2

    def test_no_url_always_kept(self):
        jobs = [{"url": "", "title": "A"}, {"url": "", "title": "B"}]
        assert len(JobSearcher._deduplicate(jobs)) == 2


class TestFieldMatches:
    STOP = {"and", "the", "for", "with", "from"}

    def _match(self, listing, field):
        phrases = [p.strip().lower() for p in field.split(",") if p.strip()]
        return JobSearcher._field_matches(listing, phrases, self.STOP)

    def test_exact_phrase_in_title(self):
        job = {"title": "PhD in machine learning", "description": ""}
        assert self._match(job, "machine learning")

    def test_keywords_in_description(self):
        job = {"title": "Research Position", "description": "deep learning and neural networks"}
        assert self._match(job, "deep learning")

    def test_no_match(self):
        job = {"title": "Chemistry Lab Technician", "description": "wet lab experience"}
        assert not self._match(job, "machine learning")

    def test_multi_field_any_matches(self):
        job = {"title": "Postdoc in NLP", "description": ""}
        assert self._match(job, "computer vision, NLP")


class TestSortKey:
    def test_dated_before_undated(self):
        dated = {"posted": _fmt(OLDER), "deadline": None, "description": "x"}
        undated = {"posted": None, "deadline": None, "description": "x" * 1000}
        # dated should sort higher (has_date=True > False)
        assert JobSearcher._sort_key(dated) > JobSearcher._sort_key(undated)

    def test_newer_before_older(self):
        newer = {"posted": _fmt(RECENT), "deadline": None, "description": "x"}
        older = {"posted": _fmt(OLDER), "deadline": None, "description": "x"}
        assert JobSearcher._sort_key(newer) > JobSearcher._sort_key(older)

    def test_longer_desc_tiebreaker(self):
        a = {"posted": _fmt(RECENT), "deadline": None, "description": "x" * 100}
        b = {"posted": _fmt(RECENT), "deadline": None, "description": "x" * 50}
        assert JobSearcher._sort_key(a) > JobSearcher._sort_key(b)


class TestKeywordSearchFlag:
    """keyword_search flag controls whether the post-filter is skipped."""

    def _make_scraper(self, name, keyword_search, listings):
        s = MagicMock()
        s.name = name
        s.keyword_search = keyword_search
        s.scrape.return_value = listings
        return s

    def _run(self, scrapers, field="biomaterials"):
        searcher = JobSearcher()
        with patch.object(JobSearcher, "_build_scrapers", return_value=scrapers), \
             patch("agent.search.searcher.time.sleep"):
            return searcher.search(field, location="Europe", position_type="any")

    def test_keyword_scraper_passes_without_keyword_in_title_or_desc(self):
        """A listing from a keyword-search scraper must survive even if the
        keyword does not appear in the title or short description."""
        listing = {
            "title": "Research Associate",
            "description": "Join our multidisciplinary team.",
            "url": "https://example.com/job/1",
            "posted": None, "deadline": None, "type": "other", "source": "euraxess",
        }
        scraper = self._make_scraper("euraxess", keyword_search=True, listings=[listing])
        results = self._run([scraper])
        assert len(results) == 1

    def test_non_keyword_scraper_filters_out_unrelated_listing(self):
        """A listing from a non-keyword-search scraper must be removed when
        the keyword does not appear in the title or description."""
        listing = {
            "title": "Research Associate",
            "description": "Join our multidisciplinary team.",
            "url": "https://example.com/job/2",
            "posted": None, "deadline": None, "type": "other", "source": "otherboard",
        }
        scraper = self._make_scraper("otherboard", keyword_search=False, listings=[listing])
        results = self._run([scraper])
        assert len(results) == 0

    def test_non_keyword_scraper_keeps_listing_when_keyword_matches(self):
        """A listing from a non-keyword-search scraper is kept when the
        keyword appears in the title."""
        listing = {
            "title": "PhD in Biomaterials",
            "description": "Research on biomaterials.",
            "url": "https://example.com/job/3",
            "posted": None, "deadline": None, "type": "phd", "source": "otherboard",
        }
        scraper = self._make_scraper("otherboard", keyword_search=False, listings=[listing])
        results = self._run([scraper])
        assert len(results) == 1

    def test_mixed_scrapers_correct_filtering(self):
        """keyword-search listing survives; non-keyword off-topic listing is removed."""
        kw_listing = {
            "title": "Postdoc Position",
            "description": "Generic description.",
            "url": "https://example.com/job/4",
            "posted": None, "deadline": None, "type": "postdoc", "source": "euraxess",
        }
        non_kw_off_topic = {
            "title": "Machine Learning Researcher",
            "description": "Deep learning and NLP.",
            "url": "https://example.com/job/5",
            "posted": None, "deadline": None, "type": "research_staff", "source": "otherboard",
        }
        kw_scraper = self._make_scraper("euraxess", keyword_search=True, listings=[kw_listing])
        non_kw_scraper = self._make_scraper("otherboard", keyword_search=False, listings=[non_kw_off_topic])
        results = self._run([kw_scraper, non_kw_scraper])
        urls = [r["url"] for r in results]
        assert "https://example.com/job/4" in urls
        assert "https://example.com/job/5" not in urls
