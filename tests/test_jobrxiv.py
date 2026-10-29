"""Tests for JobRxivScraper — parses the REST payload, no real HTTP calls."""

from __future__ import annotations

from agent.search.scrapers.base import BaseScraper
from agent.search.scrapers.jobrxiv import JobRxivScraper


def _item(title, region, cats, company="Some Lab", filled=0, date="2026-10-01T09:00:00"):
    classes = [f"job_listing_region-{region}"] if region else []
    classes += [f"job_listing_category-{c}" for c in cats]
    return {
        "title": {"rendered": title},
        "excerpt": {"rendered": f"<p>About {title} &#8211; apply now.</p>"},
        "link": f"https://jobrxiv.org/job/{title.lower().replace(' ', '-')}/",
        "date": date,
        "class_list": classes,
        "meta": {"_company_name": company, "_filled": filled},
    }


_PAYLOAD = [
    _item("PhD in Machine Learning", "germany", ["phd"]),
    _item("Postdoc in Genomics", "united-kingdom", ["postdoc"]),
    _item("Staff Scientist", "united-states", ["scientist"]),
    _item("Filled PhD position", "germany", ["phd"], filled=1),
    _item("Untagged role", "", ["phd"]),
]


def _scrape(monkeypatch, location, position_type, payload=_PAYLOAD):
    monkeypatch.setattr(JobRxivScraper, "_fetch_json", lambda self, url, **kw: payload)
    return JobRxivScraper().scrape("machine learning", location, position_type)


class TestJobRxivScraper:
    def test_parses_core_fields(self, monkeypatch):
        r = _scrape(monkeypatch, "Germany", "phd", [_PAYLOAD[0]])
        assert len(r) == 1
        job = r[0]
        assert job["title"] == "PhD in Machine Learning"
        assert job["institution"] == "Some Lab"
        assert job["location"] == "Germany"
        assert job["source"] == "jobrxiv"
        assert job["type"] == "phd"
        assert job["url"].startswith("https://jobrxiv.org/job/")
        assert job["posted"] == "2026-10-01T09:00:00"

    def test_excerpt_html_and_entities_stripped(self, monkeypatch):
        r = _scrape(monkeypatch, "Germany", "phd", [_PAYLOAD[0]])
        assert "<p>" not in r[0]["description"]
        assert "&#8211;" not in r[0]["description"]
        assert "–" in r[0]["description"]

    def test_filled_positions_skipped(self, monkeypatch):
        titles = [j["title"] for j in _scrape(monkeypatch, "", "any")]
        assert "Filled PhD position" not in titles

    def test_europe_keeps_only_european_regions(self, monkeypatch):
        regions = {j["location"] for j in _scrape(monkeypatch, "Europe", "any")}
        # "" is the untagged listing, which is kept — see the test below.
        assert regions == {"Germany", "United Kingdom", ""}

    def test_uk_aliases_resolve_to_united_kingdom(self, monkeypatch):
        r = _scrape(monkeypatch, "England", "any", _PAYLOAD[:3])
        assert [j["title"] for j in r] == ["Postdoc in Genomics"]

    def test_worldwide_keeps_every_region(self, monkeypatch):
        assert len(_scrape(monkeypatch, "", "any")) == 4

    def test_board_category_drives_position_type(self, monkeypatch):
        r = _scrape(monkeypatch, "United States", "research_staff")
        assert [j["type"] for j in r] == ["research_staff"]

    def test_type_filter_uses_board_categories(self, monkeypatch):
        titles = [j["title"] for j in _scrape(monkeypatch, "", "postdoc", _PAYLOAD[:3])]
        assert titles == ["Postdoc in Genomics"]

    def test_untagged_region_is_kept(self, monkeypatch):
        """No region tag means unknown, not 'wrong country' — keep it."""
        titles = [j["title"] for j in _scrape(monkeypatch, "Germany", "phd", [_PAYLOAD[4]])]
        assert titles == ["Untagged role"]

    def test_fetch_failure_returns_empty(self, monkeypatch):
        monkeypatch.setattr(JobRxivScraper, "_fetch_json", lambda self, url, **kw: None)
        assert JobRxivScraper().scrape("ml", "Europe", "phd") == []

    def test_respects_result_cap(self, monkeypatch):
        from agent.search.scrapers.base import _MAX_RESULTS
        big = [_item(f"PhD number {i}", "germany", ["phd"]) for i in range(_MAX_RESULTS + 10)]
        assert len(_scrape(monkeypatch, "Germany", "phd", big)) == _MAX_RESULTS


class TestMatchesType:
    def test_any_matches_everything(self):
        assert BaseScraper._matches_type("Lab Manager", "", "any")

    def test_phd_mislabelled_by_detect_type_still_matches_phd(self):
        """Regression: `_detect_type` returns one winning label, so this PhD
        post is labelled `predoctoral` and an equality filter dropped it from
        every PhD search."""
        title = "Early-Stage Researcher (ESR) - PhD position"
        desc = "Marie Curie doctoral network."
        assert BaseScraper._detect_type(title, desc) == "predoctoral"
        assert BaseScraper._matches_type(title, desc, "phd")

    def test_unrelated_listing_does_not_match(self):
        assert not BaseScraper._matches_type("Marketing Manager", "Sell things.", "phd")

    def test_unknown_type_is_permissive(self):
        assert BaseScraper._matches_type("Anything", "", "not_a_type")
