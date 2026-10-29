"""Tests for config.py — checks defaults and types."""

from config import config


class TestAppConfigDefaults:
    def test_default_model(self):
        # Groq decommissioned the Llama models this app used to default to.
        assert config.default_model == "openai/gpt-oss-120b"

    def test_max_tokens_positive(self):
        assert config.max_tokens > 0

    def test_groq_base_url(self):
        assert "groq.com" in config.groq_base_url

    def test_scraper_delay_positive(self):
        assert config.scraper_delay > 0

    def test_recent_days_positive(self):
        assert config.recent_days > 0

    def test_deadline_warn_days_positive(self):
        assert config.deadline_warn_days > 0

    def test_stale_days_positive(self):
        assert config.stale_days > 0

    def test_max_results_per_source_positive(self):
        assert config.max_results_per_source > 0
