"""JobAgent: orchestrates the full research job application pipeline."""

from __future__ import annotations

from typing import Any

from agent.llm_client import LLMClient
from agent.cv.parser import CVParser, CVProfile
from agent.search.searcher import JobSearcher
from agent.matching.matcher import JobMatcher
from agent.cv.tailor import CVTailor, TailoringHints
from agent.cv.cover_letter import CoverLetterWriter


class JobAgent:
    """Orchestrates CV parsing, job search, scoring, and application generation.

    Each instance holds its own LLM client — safe to instantiate per-request.

    Args:
        model:    Model ID for the selected backend.
        backend:  "groq" | "huggingface" | "ollama"
        api_key:  API key for the selected backend (not needed for Ollama).
    """

    def __init__(self, model: str, backend: str = "groq", api_key: str = "") -> None:
        self.llm = LLMClient(model=model, backend=backend, token=api_key or None)
        self.parser = CVParser(self.llm)
        self.searcher = JobSearcher()
        self.matcher = JobMatcher(self.llm)
        self.tailor = CVTailor(self.llm)
        self.writer = CoverLetterWriter(self.llm)

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    def parse_cv(self, cv_path: str) -> tuple[CVProfile, str]:
        """Parse a CV file.

        Returns:
            (profile dict, compact text summary for use in prompts)
        """
        profile = self.parser.parse(cv_path)
        text = self.parser.summarize(profile)
        return profile, text

    def search_jobs(
        self,
        field: str,
        location: str = "Europe",
        position_type: str = "any",
    ) -> list[dict[str, Any]]:
        """Search all free job boards and return deduplicated listings.

        After the call, ``self.searcher.failed_sources`` lists the boards that
        raised, so the caller can tell the user which sources were skipped.
        """
        return self.searcher.search(field, location, position_type)

    def score_jobs(
        self,
        jobs: list[dict[str, Any]],
        profile_text: str,
    ) -> list[dict[str, Any]]:
        """Score all jobs and return them sorted by score (highest first)."""
        return self.matcher.score_all(jobs, profile_text)

    def prepare_application(
        self,
        job: dict[str, Any],
        profile_text: str,
    ) -> tuple[TailoringHints, str]:
        """Generate CV tailoring hints and a cover letter draft for one position.

        Returns:
            (tailoring_hints dict, cover_letter string)
        """
        hints = self.tailor.generate(job, profile_text)
        letter = self.writer.generate(job, profile_text)
        return hints, letter

    def regenerate_letter(
        self,
        job: dict[str, Any],
        profile_text: str,
    ) -> str:
        """Generate an alternative version of the cover letter."""
        return self.writer.generate(job, profile_text, regenerate=True)
