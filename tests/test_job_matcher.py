"""Tests for JobMatcher — mocks LLM to test scoring logic without API calls."""

import json
from unittest.mock import MagicMock
import pytest
from agent.matching.matcher import JobMatcher, _fallback, _phd_status
from agent.llm_client import LLMClient, LLMQuotaError


def _make_matcher(llm_response: str | Exception) -> JobMatcher:
    """Return a JobMatcher whose LLM always returns the given response."""
    llm = MagicMock(spec=LLMClient)
    if isinstance(llm_response, Exception):
        llm.generate.side_effect = llm_response
    else:
        llm.generate.return_value = llm_response
    return JobMatcher(llm)


GOOD_JSON = """{
    "match_score": 82,
    "recommendation": "apply",
    "matching_areas": ["machine learning", "NLP"],
    "missing_requirements": [],
    "why_good_fit": "Strong ML background.",
    "concerns": ""
}"""

LOW_JSON = """{
    "match_score": 20,
    "recommendation": "skip",
    "matching_areas": [],
    "missing_requirements": ["wet lab experience"],
    "why_good_fit": "",
    "concerns": "Very different field."
}"""

JOB = {"title": "PhD in ML", "institution": "MIT", "location": "USA",
       "type": "phd", "description": "Machine learning research position."}
PROFILE = "Researcher with 3 years ML experience, 2 NeurIPS papers."


class TestScore:
    def test_good_match(self):
        matcher = _make_matcher(GOOD_JSON)
        result = matcher.score(JOB, PROFILE)
        assert result["match_score"] == 82
        assert result["recommendation"] == "apply"
        assert "machine learning" in result["matching_areas"]

    def test_low_match(self):
        matcher = _make_matcher(LOW_JSON)
        result = matcher.score(JOB, PROFILE)
        assert result["match_score"] == 20
        assert result["recommendation"] == "skip"

    def test_score_clamped_to_100(self):
        matcher = _make_matcher('{"match_score": 150, "recommendation": "apply", '
                                '"matching_areas": [], "missing_requirements": [], '
                                '"why_good_fit": "", "concerns": ""}')
        result = matcher.score(JOB, PROFILE)
        assert result["match_score"] == 100

    def test_score_clamped_to_0(self):
        matcher = _make_matcher('{"match_score": -10, "recommendation": "skip", '
                                '"matching_areas": [], "missing_requirements": [], '
                                '"why_good_fit": "", "concerns": ""}')
        result = matcher.score(JOB, PROFILE)
        assert result["match_score"] == 0

    def test_llm_error_surfaces_message(self):
        matcher = _make_matcher(RuntimeError("Groq inference failed: 401 Unauthorized"))
        result = matcher.score(JOB, PROFILE)
        assert result["match_score"] == 0
        assert "Groq inference failed" in result["concerns"]

    def test_invalid_json_returns_fallback(self):
        matcher = _make_matcher("this is not json at all")
        result = matcher.score(JOB, PROFILE)
        assert result["match_score"] == 0
        assert result["recommendation"] == "skip"

    def test_quota_error_propagates(self):
        matcher = _make_matcher(LLMQuotaError("Quota exceeded"))
        with pytest.raises(LLMQuotaError):
            matcher.score(JOB, PROFILE)

    def test_recommendation_inferred_when_missing(self):
        # LLM returns invalid recommendation — should be inferred from score
        matcher = _make_matcher('{"match_score": 75, "recommendation": "maybe", '
                                '"matching_areas": [], "missing_requirements": [], '
                                '"why_good_fit": "", "concerns": ""}')
        result = matcher.score(JOB, PROFILE)
        assert result["recommendation"] == "apply"  # score >= 70


class TestScoreAll:
    def test_sorted_by_score_descending(self):
        responses = [GOOD_JSON, LOW_JSON, GOOD_JSON]
        call_count = [0]
        llm = MagicMock(spec=LLMClient)
        def side_effect(*args, **kwargs):
            r = responses[call_count[0]]
            call_count[0] += 1
            return r
        llm.generate.side_effect = side_effect
        matcher = JobMatcher(llm)
        jobs = [JOB, JOB, JOB]
        scored = matcher.score_all(jobs, PROFILE)
        scores = [j["match"]["match_score"] for j in scored]
        assert scores == sorted(scores, reverse=True)


class TestPhDStatus:
    def test_completed_phd(self):
        assert _phd_status("Researcher with a PhD in Computer Science.") == "completed"

    def test_completed_phd_variant(self):
        assert _phd_status("She holds a Ph.D. from MIT.") == "completed"

    def test_completed_doctorate(self):
        assert _phd_status("Awarded doctoral degree in 2020.") == "completed"

    def test_in_progress_candidate(self):
        assert _phd_status("Currently a PhD candidate at ETH Zurich.") == "in_progress"

    def test_in_progress_student(self):
        assert _phd_status("PhD student in NLP, expected 2026.") == "in_progress"

    def test_in_progress_pursuing(self):
        assert _phd_status("Pursuing a doctorate at Cambridge.") == "in_progress"

    def test_in_progress_beats_completed(self):
        # "PhD candidate" should not be downgraded just because "PhD" also appears
        assert _phd_status("PhD candidate (Ph.D. expected 2027)") == "in_progress"

    def test_none(self):
        assert _phd_status("Master's student in ML, 3 years experience.") == "none"

    def test_empty_string(self):
        assert _phd_status("") == "none"


POSTDOC_JOB = {"title": "Postdoc in ML", "institution": "MIT", "location": "USA",
               "type": "postdoc", "description": "Postdoctoral research position."}
FELLOWSHIP_JOB = {**POSTDOC_JOB, "type": "fellowship"}


class TestEligibilityCap:
    def test_no_phd_postdoc_capped_at_30(self):
        # LLM gives 80 but candidate has no PhD — must be capped at 30
        matcher = _make_matcher(
            '{"match_score": 80, "recommendation": "apply", '
            '"matching_areas": ["ML"], "missing_requirements": [], '
            '"why_good_fit": "Great.", "concerns": ""}'
        )
        no_phd_profile = "Master student in ML with 2 years experience."
        result = matcher.score(POSTDOC_JOB, no_phd_profile)
        assert result["match_score"] == 30
        assert result["recommendation"] == "skip"
        assert "PhD" in result["concerns"] or "doctoral" in result["concerns"].lower()

    def test_no_phd_fellowship_capped_at_30(self):
        matcher = _make_matcher(
            '{"match_score": 75, "recommendation": "apply", '
            '"matching_areas": [], "missing_requirements": [], '
            '"why_good_fit": "", "concerns": ""}'
        )
        result = matcher.score(FELLOWSHIP_JOB, "Master's graduate, ML researcher.")
        assert result["match_score"] == 30

    def test_no_phd_already_low_score_unchanged(self):
        # Score ≤ 30 already — cap must NOT raise it
        matcher = _make_matcher(
            '{"match_score": 20, "recommendation": "skip", '
            '"matching_areas": [], "missing_requirements": [], '
            '"why_good_fit": "", "concerns": "Poor fit."}'
        )
        result = matcher.score(POSTDOC_JOB, "No PhD here.")
        assert result["match_score"] == 20  # unchanged

    def test_phd_in_progress_postdoc_capped_at_65(self):
        matcher = _make_matcher(
            '{"match_score": 85, "recommendation": "apply", '
            '"matching_areas": ["ML"], "missing_requirements": [], '
            '"why_good_fit": "Strong.", "concerns": ""}'
        )
        result = matcher.score(POSTDOC_JOB, "PhD candidate at Stanford, expected 2026.")
        assert result["match_score"] == 65

    def test_phd_in_progress_below_65_unchanged(self):
        matcher = _make_matcher(
            '{"match_score": 55, "recommendation": "consider", '
            '"matching_areas": [], "missing_requirements": [], '
            '"why_good_fit": "", "concerns": ""}'
        )
        result = matcher.score(POSTDOC_JOB, "Pursuing a PhD in NLP.")
        assert result["match_score"] == 55  # not capped

    def test_completed_phd_postdoc_no_cap(self):
        matcher = _make_matcher(
            '{"match_score": 90, "recommendation": "apply", '
            '"matching_areas": ["ML"], "missing_requirements": [], '
            '"why_good_fit": "Excellent.", "concerns": ""}'
        )
        result = matcher.score(POSTDOC_JOB, "Researcher with a PhD in Computer Science.")
        assert result["match_score"] == 90

    def test_phd_position_no_cap_regardless(self):
        # PhD positions should not cap regardless of candidate's PhD status
        matcher = _make_matcher(
            '{"match_score": 85, "recommendation": "apply", '
            '"matching_areas": ["ML"], "missing_requirements": [], '
            '"why_good_fit": "Good.", "concerns": ""}'
        )
        phd_job = {**JOB, "type": "phd"}
        result = matcher.score(phd_job, "Master student with strong ML background.")
        assert result["match_score"] == 85


class TestFallback:
    def test_fallback_structure(self):
        fb = _fallback("test error")
        assert fb["match_score"] == 0
        assert fb["recommendation"] == "skip"
        assert "test error" in fb["concerns"]
        assert isinstance(fb["matching_areas"], list)


class TestScoringFailureIsDistinguishable:
    """A rate-limited position must not look like a genuine 0% match: the UI
    filters on match_score, so without a flag it vanished without a trace."""

    def test_llm_failure_sets_the_flag(self):
        matcher = _make_matcher(RuntimeError("Groq inference failed: 429"))
        result = matcher.score(JOB, PROFILE)
        assert result["scoring_failed"] is True
        assert result["match_score"] == 0

    def test_malformed_json_sets_the_flag(self):
        matcher = _make_matcher("not json at all")
        result = matcher.score(JOB, PROFILE)
        assert result["scoring_failed"] is True

    def test_successful_score_does_not_set_the_flag(self):
        matcher = _make_matcher(json.dumps(
            {"match_score": 0, "recommendation": "skip"}
        ))
        result = matcher.score(JOB, PROFILE)
        assert not result.get("scoring_failed")
