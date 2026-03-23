"""Tests for CVTailor and format_hints_text — mocks LLM, no API calls."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent.cv.tailor import CVTailor, format_hints_text, _fallback, _FALLBACK_ORDER
from agent.llm_client import LLMClient, LLMQuotaError


GOOD_JSON = """{
    "headline_suggestion": "Emphasise your NLP publications",
    "skills_to_highlight": ["Python", "PyTorch", "HuggingFace"],
    "experience_to_emphasize": ["LLM fine-tuning at ETH"],
    "research_alignment": "Strong overlap with low-resource NLP research.",
    "keywords_to_add": ["low-resource", "multilingual"],
    "suggested_order": ["Education", "Publications", "Skills", "Experience"]
}"""

JOB = {"title": "PhD in NLP", "institution": "MIT", "type": "phd",
       "description": "Low-resource NLP research position."}
PROFILE = "Alice Rossi, NLP researcher, 2 ACL publications."


def _make_tailor(response: str | Exception) -> CVTailor:
    llm = MagicMock(spec=LLMClient)
    if isinstance(response, Exception):
        llm.generate.side_effect = response
    else:
        llm.generate.return_value = response
    return CVTailor(llm)


# ---------------------------------------------------------------------------
# CVTailor.generate()
# ---------------------------------------------------------------------------

class TestGenerate:
    def test_good_json_returns_hints(self):
        tailor = _make_tailor(GOOD_JSON)
        hints = tailor.generate(JOB, PROFILE)
        assert hints["headline_suggestion"] == "Emphasise your NLP publications"
        assert "Python" in hints["skills_to_highlight"]

    def test_experience_to_emphasize_populated(self):
        tailor = _make_tailor(GOOD_JSON)
        hints = tailor.generate(JOB, PROFILE)
        assert "LLM fine-tuning at ETH" in hints["experience_to_emphasize"]

    def test_keywords_to_add_populated(self):
        tailor = _make_tailor(GOOD_JSON)
        hints = tailor.generate(JOB, PROFILE)
        assert "low-resource" in hints["keywords_to_add"]

    def test_research_alignment_populated(self):
        tailor = _make_tailor(GOOD_JSON)
        hints = tailor.generate(JOB, PROFILE)
        assert "NLP" in hints["research_alignment"]

    def test_llm_failure_returns_fallback(self):
        tailor = _make_tailor(RuntimeError("connection error"))
        hints = tailor.generate(JOB, PROFILE)
        assert hints["skills_to_highlight"] == []
        assert hints["suggested_order"] == _FALLBACK_ORDER
        assert "headline_suggestion" in hints

    def test_invalid_json_returns_fallback(self):
        tailor = _make_tailor("this is not valid json")
        hints = tailor.generate(JOB, PROFILE)
        assert hints["suggested_order"] == _FALLBACK_ORDER

    def test_quota_error_propagates(self):
        tailor = _make_tailor(LLMQuotaError("Quota exceeded"))
        with pytest.raises(LLMQuotaError):
            tailor.generate(JOB, PROFILE)

    def test_partial_json_fills_missing_with_defaults(self):
        partial = '{"headline_suggestion": "Focus on ML", "skills_to_highlight": ["Python"]}'
        tailor = _make_tailor(partial)
        hints = tailor.generate(JOB, PROFILE)
        # Missing keys should be defaulted
        assert hints["experience_to_emphasize"] == []
        assert hints["keywords_to_add"] == []
        assert hints["suggested_order"] == _FALLBACK_ORDER
        assert hints["research_alignment"] == ""

    def test_all_required_keys_always_present(self):
        tailor = _make_tailor(GOOD_JSON)
        hints = tailor.generate(JOB, PROFILE)
        for key in ("headline_suggestion", "skills_to_highlight", "experience_to_emphasize",
                    "research_alignment", "keywords_to_add", "suggested_order"):
            assert key in hints, f"Missing key: {key}"

    def test_empty_job_no_crash(self):
        tailor = _make_tailor(GOOD_JSON)
        hints = tailor.generate({}, PROFILE)
        assert isinstance(hints, dict)


# ---------------------------------------------------------------------------
# _fallback()
# ---------------------------------------------------------------------------

class TestFallback:
    def test_returns_dict_with_all_keys(self):
        fb = _fallback("test reason")
        for key in ("headline_suggestion", "skills_to_highlight", "experience_to_emphasize",
                    "research_alignment", "keywords_to_add", "suggested_order"):
            assert key in fb

    def test_reason_in_headline(self):
        fb = _fallback("connection timeout")
        assert "connection timeout" in fb["headline_suggestion"]

    def test_lists_are_empty(self):
        fb = _fallback("error")
        assert fb["skills_to_highlight"] == []
        assert fb["experience_to_emphasize"] == []
        assert fb["keywords_to_add"] == []

    def test_suggested_order_is_fallback(self):
        fb = _fallback("error")
        assert fb["suggested_order"] == _FALLBACK_ORDER


# ---------------------------------------------------------------------------
# format_hints_text()
# ---------------------------------------------------------------------------

class TestFormatHintsText:
    def _full_hints(self):
        return {
            "headline_suggestion": "Emphasise NLP publications",
            "skills_to_highlight": ["Python", "PyTorch"],
            "experience_to_emphasize": ["LLM research at ETH"],
            "research_alignment": "Strong overlap with low-resource NLP.",
            "keywords_to_add": ["multilingual", "low-resource"],
            "suggested_order": ["Education", "Publications", "Skills"],
        }

    def test_header_present(self):
        text = format_hints_text(self._full_hints())
        assert "CV TAILORING HINTS" in text

    def test_headline_section(self):
        text = format_hints_text(self._full_hints())
        assert "Emphasise NLP publications" in text

    def test_skills_listed(self):
        text = format_hints_text(self._full_hints())
        assert "Python" in text
        assert "PyTorch" in text

    def test_experience_listed(self):
        text = format_hints_text(self._full_hints())
        assert "LLM research at ETH" in text

    def test_keywords_listed(self):
        text = format_hints_text(self._full_hints())
        assert "multilingual" in text

    def test_suggested_order_listed(self):
        text = format_hints_text(self._full_hints())
        assert "Education" in text
        assert "Publications" in text

    def test_empty_hints_no_crash(self):
        text = format_hints_text({})
        assert isinstance(text, str)

    def test_returns_string(self):
        text = format_hints_text(self._full_hints())
        assert isinstance(text, str)
        assert len(text) > 0
