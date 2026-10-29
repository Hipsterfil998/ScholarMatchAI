"""Job matcher — scores research positions against a CV profile."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, TypedDict

from agent.base_service import BaseLLMService
from agent.prompts import JOB_MATCHER_SYSTEM, JOB_MATCHER_PROMPT
from agent.utils import job_description, job_institution


class MatchResult(TypedDict, total=False):
    scoring_failed: bool              # True when the LLM call failed, not a real 0
    match_score: int
    recommendation: str               # "apply" | "consider" | "skip"
    matching_areas: list[str]
    missing_requirements: list[str]
    why_good_fit: str
    concerns: str




_PHD_COMPLETED = re.compile(
    r"\b(ph\.?d\.?|doctorate|doctoral degree)\b", re.IGNORECASE
)
_PHD_IN_PROGRESS = re.compile(
    r"\b(phd (candidate|student|fellow)|doctoral (candidate|student)|"
    r"phd (in progress|expected|ongoing)|pursuing (a |the )?(ph\.?d|doctorate))\b",
    re.IGNORECASE,
)


def _phd_status(profile_text: str) -> str:
    """Return 'completed', 'in_progress', or 'none' based on the profile summary.

    Heuristic: looks for PhD/doctorate keywords in the text the LLM produced
    from the candidate's CV.  False negatives (PhD not detected) are possible
    for very terse profiles — the LLM prompt rule acts as the primary gate.
    """
    if _PHD_IN_PROGRESS.search(profile_text):
        return "in_progress"
    if _PHD_COMPLETED.search(profile_text):
        return "completed"
    return "none"


# Marks a MatchResult as "scoring failed" rather than "scored 0". The UI
# filters on match_score, so without this flag a rate-limited position was
# indistinguishable from a genuine 0% match and disappeared silently.
SCORING_FAILED = "scoring_failed"


def _fallback(reason: str) -> MatchResult:
    return {
        "match_score": 0,
        "recommendation": "skip",
        "matching_areas": [],
        "missing_requirements": [],
        "why_good_fit": "",
        "concerns": f"Could not score position: {reason[:200]}",
        SCORING_FAILED: True,
    }


class JobMatcher(BaseLLMService):
    """Scores job listings against a CV profile using an LLM."""

    _SYSTEM = JOB_MATCHER_SYSTEM

    def score(self, job: dict[str, Any], profile_text: str) -> MatchResult:
        """Score a single job listing against a CV profile summary."""
        prompt = JOB_MATCHER_PROMPT.format(
            profile=profile_text,
            title=job.get("title", "Unknown"),
            institution=job_institution(job) or "Unknown",
            location=job.get("location", "Unknown"),
            pos_type=job.get("type", "unknown"),
            description=job_description(job),
        )

        result = self._generate_json(prompt)
        if result is None:
            return _fallback("Response was not valid JSON")
        if "_llm_error" in result:
            return _fallback(result["_llm_error"])

        try:
            result["match_score"] = max(0, min(100, int(result.get("match_score", 0))))
        except (TypeError, ValueError):
            result["match_score"] = 0

        # Hard eligibility cap — safety net in case the LLM ignores the prompt rule.
        pos_type = job.get("type", "")
        if pos_type in ("postdoc", "fellowship"):
            phd_status = _phd_status(profile_text)
            if phd_status == "none" and result["match_score"] > 30:
                result["match_score"] = 30
                result["recommendation"] = "skip"
                existing = result.get("concerns") or ""
                result["concerns"] = (
                    "Eligibility: no completed or in-progress PhD found in the candidate "
                    "profile. Postdoc/fellowship positions require a doctoral degree. "
                    + existing
                ).strip()
            elif phd_status == "in_progress" and result["match_score"] > 65:
                result["match_score"] = 65  # PhD in progress: eligible but capped

        if result.get("recommendation") not in ("apply", "consider", "skip"):
            score = result.get("match_score", 0)
            result["recommendation"] = (
                "apply" if score >= 70 else ("consider" if score >= 50 else "skip")
            )

        return result

    def score_all(
        self,
        jobs: list[dict[str, Any]],
        profile_text: str,
        max_workers: int = 4,
    ) -> list[dict[str, Any]]:
        """Score all jobs in parallel and return them sorted by score (highest first).

        Throughput is capped by the backend's tokens-per-minute budget, not by
        concurrency, so a high worker count buys nothing and just turns the
        rate limit into a retry storm.
        """
        scored: list[dict[str, Any]] = [{}] * len(jobs)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.score, job, profile_text): i
                for i, job in enumerate(jobs)
            }
            for future in as_completed(futures):
                i = futures[future]
                scored[i] = {**jobs[i], "match": future.result()}
        scored.sort(key=lambda j: j["match"].get("match_score", 0), reverse=True)
        return scored
