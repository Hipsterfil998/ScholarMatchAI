"""Job matcher: scores research/PhD positions against a CV profile using the local LLM.

Scoring is research-aware: it checks alignment of research interests, supervisor/lab
fit, methodological overlap, and publication relevance — not just keyword matching.
"""

from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from agent.llm_client import LLMClient


# ---------------------------------------------------------------------------
# Type definitions
# ---------------------------------------------------------------------------

class MatchResult(TypedDict, total=False):
    match_score: int                  # 0–100
    recommendation: str               # "apply" | "consider" | "skip"
    matching_areas: list[str]         # research areas that match
    missing_requirements: list[str]   # requirements the candidate lacks
    why_good_fit: str                 # short explanation of strengths
    concerns: str                     # gaps or potential issues


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_MATCH_SYSTEM = (
    "You are an expert academic recruiter specialising in PhD and postdoc placements. "
    "Evaluate how well a candidate's research profile fits a given position. "
    "Respond only with valid JSON — no markdown, no commentary."
)

_MATCH_PROMPT = """Evaluate how well this candidate fits the research position below.

CANDIDATE PROFILE:
{profile}

POSITION:
Title: {title}
Institution: {institution}
Location: {location}
Type: {pos_type}
Description:
{description}

Return a JSON object with exactly these keys:
{{
  "match_score": <integer 0-100>,
  "recommendation": "apply" | "consider" | "skip",
  "matching_areas": ["list of research areas / skills that align"],
  "missing_requirements": ["gaps between candidate and requirements"],
  "why_good_fit": "2-3 sentence explanation of the main strengths",
  "concerns": "1-2 sentence summary of gaps or concerns (empty string if none)"
}}

Scoring guide (research-specific):
  85-100: Excellent match — research interests closely aligned, strong publication/thesis fit
  70-84:  Good match — clear research overlap, candidate has most required skills
  55-69:  Partial match — some research overlap but gaps in methodology or field
  35-54:  Weak match — limited overlap, significant methodological or domain gaps
  0-34:   Poor match — very different research areas or missing critical qualifications

Consider: research interest alignment, thesis/project relevance, methodological overlap,
publication track record, technical/lab skills, language requirements, career stage fit.
Be realistic and honest."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_fences(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _fallback_result(raw: str) -> MatchResult:
    return {
        "match_score": 0,
        "recommendation": "skip",
        "matching_areas": [],
        "missing_requirements": [],
        "why_good_fit": "",
        "concerns": f"Could not parse match result. Raw output: {raw[:300]}",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_job(
    job: dict[str, Any],
    profile: dict[str, Any],
    profile_text: str,
    model: str | None = None,
    console=None,
) -> MatchResult:
    """Score a single job listing against a CV profile.

    Args:
        job:          Job listing dict (from job_searcher).
        profile:      Structured CVProfile dict (from cv_parser).
        profile_text: Compact text summary of the profile (for the prompt).
        model:        Optional LLM model override.
        console:      Optional rich Console for debug output.

    Returns:
        MatchResult with score, recommendation, and analysis.
    """
    client = LLMClient(model=model)

    prompt = _MATCH_PROMPT.format(
        profile=profile_text,
        title=job.get("title", "Unknown"),
        institution=job.get("institution", job.get("company", "Unknown")),
        location=job.get("location", "Unknown"),
        pos_type=job.get("type", "unknown"),
        description=(job.get("description") or "No description provided.")[:3000],
    )

    try:
        raw_json = client.generate(
            system=_MATCH_SYSTEM,
            user=prompt,
            json_mode=True,
        )
    except RuntimeError as exc:
        if console:
            console.print(f"[red]LLM error during scoring: {exc}[/red]")
        return _fallback_result(str(exc))

    raw_json = _strip_fences(raw_json)

    try:
        result: MatchResult = json.loads(raw_json)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw_json, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group())
            except json.JSONDecodeError:
                return _fallback_result(raw_json)
        else:
            return _fallback_result(raw_json)

    # Clamp match_score to [0, 100]
    try:
        result["match_score"] = max(0, min(100, int(result.get("match_score", 0))))
    except (TypeError, ValueError):
        result["match_score"] = 0

    # Ensure recommendation is valid
    if result.get("recommendation") not in ("apply", "consider", "skip"):
        score = result.get("match_score", 0)
        result["recommendation"] = "apply" if score >= 70 else ("consider" if score >= 50 else "skip")

    return result


def score_jobs(
    jobs: list[dict[str, Any]],
    profile: dict[str, Any],
    profile_text: str,
    min_score: int = 60,
    model: str | None = None,
    console=None,
) -> list[dict[str, Any]]:
    """Score all job listings and return those meeting the minimum score.

    Args:
        jobs:         List of job listing dicts.
        profile:      Structured CVProfile.
        profile_text: Compact text CV summary.
        min_score:    Minimum match_score to keep (0-100).
        model:        Optional LLM model override.
        console:      Optional rich Console for progress output.

    Returns:
        Filtered and sorted list of job dicts (each with an added 'match' key).
    """
    scored: list[dict[str, Any]] = []

    for i, job in enumerate(jobs, start=1):
        title = job.get("title", "Unknown")
        institution = job.get("institution", job.get("company", "Unknown"))
        if console:
            console.print(
                f"[dim]  [{i}/{len(jobs)}] Scoring: {title} @ {institution}[/dim]"
            )

        match = score_job(job, profile, profile_text, model=model, console=console)
        scored.append({**job, "match": match})

    # Sort highest first
    scored.sort(key=lambda j: j["match"].get("match_score", 0), reverse=True)

    # Filter by minimum score
    filtered = [j for j in scored if j["match"].get("match_score", 0) >= min_score]

    if console:
        console.print(
            f"[green]{len(filtered)} / {len(scored)} positions meet "
            f"the minimum score of {min_score}.[/green]"
        )

    return filtered
