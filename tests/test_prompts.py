"""Tests for agent/prompts.py — checks all prompts are present and well-formed."""

import pytest
from agent import prompts


PROMPT_PAIRS = [
    ("CV_PARSER_SYSTEM", "CV_PARSER_PROMPT"),
    ("JOB_MATCHER_SYSTEM", "JOB_MATCHER_PROMPT"),
    ("CV_TAILOR_SYSTEM", "CV_TAILOR_PROMPT"),
    ("COVER_LETTER_SYSTEM", "COVER_LETTER_PROMPT"),
]


class TestPromptsPresent:
    @pytest.mark.parametrize("name", [
        "CV_PARSER_SYSTEM", "CV_PARSER_PROMPT",
        "JOB_MATCHER_SYSTEM", "JOB_MATCHER_PROMPT",
        "CV_TAILOR_SYSTEM", "CV_TAILOR_PROMPT",
        "COVER_LETTER_SYSTEM", "COVER_LETTER_PROMPT",
        "COVER_LETTER_REGEN_NOTE", "COVER_LETTER_DRAFT_HEADER",
    ])
    def test_exists_and_nonempty(self, name):
        value = getattr(prompts, name)
        assert isinstance(value, str)
        assert len(value) > 20

    def test_cv_parser_prompt_has_placeholder(self):
        assert "{cv_text}" in prompts.CV_PARSER_PROMPT

    def test_job_matcher_prompt_placeholders(self):
        p = prompts.JOB_MATCHER_PROMPT
        for placeholder in ["{profile}", "{title}", "{institution}", "{location}",
                             "{pos_type}", "{description}"]:
            assert placeholder in p, f"Missing placeholder: {placeholder}"

    def test_cv_tailor_prompt_placeholders(self):
        p = prompts.CV_TAILOR_PROMPT
        for placeholder in ["{title}", "{institution}", "{pos_type}",
                             "{description}", "{profile}"]:
            assert placeholder in p, f"Missing placeholder: {placeholder}"

    def test_cover_letter_prompt_placeholders(self):
        p = prompts.COVER_LETTER_PROMPT
        for placeholder in ["{profile}", "{title}", "{institution}", "{location}",
                             "{pos_type}", "{description}", "{language}", "{regen_note}"]:
            assert placeholder in p, f"Missing placeholder: {placeholder}"

    def test_job_matcher_prompt_formats_without_error(self):
        formatted = prompts.JOB_MATCHER_PROMPT.format(
            profile="test profile",
            title="PhD in ML",
            institution="MIT",
            location="USA",
            pos_type="phd",
            description="Machine learning research",
        )
        assert "test profile" in formatted
        assert "PhD in ML" in formatted


class TestJobMatcherPromptBudget:
    """The matcher prompt is sent once per listing, so its fixed size is
    multiplied by the result count. On Groq's free tier the pipeline is bound
    by tokens per minute: when this prompt was 2833 chars, scoring 31 listings
    exhausted the budget and 20 of them came back unscored."""

    BUDGET_CHARS = 1600

    def test_fixed_overhead_stays_within_budget(self):
        overhead = len(prompts.JOB_MATCHER_SYSTEM) + len(prompts.JOB_MATCHER_PROMPT)
        assert overhead <= self.BUDGET_CHARS, (
            f"matcher prompt grew to {overhead} chars (budget {self.BUDGET_CHARS}); "
            "every extra char is paid once per job listing"
        )

    def test_still_states_the_output_contract(self):
        p = prompts.JOB_MATCHER_PROMPT
        for key in ("match_score", "recommendation", "matching_areas",
                    "missing_requirements", "why_good_fit", "concerns"):
            assert key in p

    def test_still_states_the_eligibility_rule(self):
        p = prompts.JOB_MATCHER_PROMPT.lower()
        assert "postdoc" in p and "phd" in p
        assert "30" in p and "65" in p

    def test_still_asks_for_semantic_matching(self):
        p = prompts.JOB_MATCHER_PROMPT.lower()
        assert "keyword" in p
        assert "natural language processing" in p
