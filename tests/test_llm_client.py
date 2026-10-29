"""Tests for LLMClient backend wiring — no real network calls."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.llm_client import LLMClient, LLMQuotaError
from config import config


class TestGroqClientConfiguration:
    """Groq's free tier is tokens-per-minute bound, so a batch of jobs will
    hit 429 part-way through. The SDK retries and honours Retry-After, but
    its default of 2 attempts is nowhere near a full TPM window."""

    def _build(self):
        client = LLMClient(model="openai/gpt-oss-120b", backend="groq", token="k")
        with patch("openai.OpenAI") as ctor:
            client._get_groq_client()
        return ctor.call_args.kwargs

    def test_retry_budget_is_wired_from_config(self):
        assert self._build()["max_retries"] == config.llm_max_retries

    def test_retry_budget_survives_a_tpm_window(self):
        """A one-minute TPM window needs more than the SDK's default 2 tries."""
        assert config.llm_max_retries >= 5

    def test_request_timeout_is_set(self):
        assert self._build()["timeout"] == config.llm_timeout

    def test_points_at_groq(self):
        kwargs = self._build()
        assert kwargs["base_url"] == config.groq_base_url
        assert kwargs["api_key"] == "k"

    def test_client_is_cached(self):
        client = LLMClient(model="m", backend="groq", token="k")
        with patch("openai.OpenAI") as ctor:
            client._get_groq_client()
            client._get_groq_client()
        assert ctor.call_count == 1


class TestBackendDispatch:
    def test_unknown_backend_raises(self):
        with pytest.raises(RuntimeError, match="Unknown LLM backend"):
            LLMClient(model="m", backend="nope").generate("s", "u")

    def test_quota_error_is_a_runtime_error(self):
        """server.py routes both through one handler — quota must stay a
        RuntimeError subclass or it would escape as a bare 500."""
        assert issubclass(LLMQuotaError, RuntimeError)
