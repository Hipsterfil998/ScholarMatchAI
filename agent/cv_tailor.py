"""CV tailoring hints generator.

Given a job listing and a CV profile, generates actionable, position-specific
hints for the user to apply manually to their CV — NOT a full rewrite.

The output (TailoringHints) tells the user:
  - Which sections / entries to emphasise
  - Keywords missing from their CV that appear in the job description
  - How to frame their research interests for this specific position
  - A suggested section order for maximum impact
"""

from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from agent.llm_client import LLMClient


# ---------------------------------------------------------------------------
# Type definition
# ---------------------------------------------------------------------------

class TailoringHints(TypedDict, total=False):
    headline_suggestion: str            # suggested tweak to the profile summary
    skills_to_highlight: list[str]      # which skills to move to top / emphasise
    experience_to_emphasize: list[str]  # which experience entries are most relevant
    research_alignment: str             # how to frame research interests for this role
    keywords_to_add: list[str]          # keywords from JD absent from CV
    suggested_order: list[str]          # suggested CV section order for this role


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_TAILOR_SYSTEM = (
    "You are an expert academic career advisor helping a researcher tailor their CV "
    "for a specific PhD / postdoc / fellowship application. "
    "Give concrete, actionable hints — do NOT rewrite the CV. "
    "Respond only with valid JSON."
)

_TAILOR_PROMPT = """The researcher is applying for the following position:

POSITION:
Title: {title}
Institution: {institution}
Location: {location}
Type: {pos_type}
Description:
{description}

CANDIDATE CV PROFILE:
{profile}

Produce a JSON object with EXACTLY these keys:
{{
  "headline_suggestion": "One sentence suggestion for tweaking the profile summary to emphasise fit with this role",
  "skills_to_highlight": ["skill1 (why: relevance note)", "skill2 (why: ...)"],
  "experience_to_emphasize": ["Experience entry 1 — brief note on which aspect to highlight", "..."],
  "research_alignment": "2-3 sentences explaining how to frame the candidate's research interests to align with this group's work",
  "keywords_to_add": ["keyword1", "keyword2"],
  "suggested_order": ["Research Interests", "Publications", "Education", "Experience", "Skills", "Awards"]
}}

Rules:
- Be specific: reference actual CV entries and job requirements
- keywords_to_add: only terms genuinely present in the job description but absent from the CV
- suggested_order: tailor to whether this role values research output, lab skills, teaching, etc.
- Do NOT suggest fabricating experience or qualifications
- Keep each hint to 1-2 sentences — actionable and concise"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_fences(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _fallback_hints(reason: str) -> TailoringHints:
    return {
        "headline_suggestion": f"Could not generate hints: {reason}",
        "skills_to_highlight": [],
        "experience_to_emphasize": [],
        "research_alignment": "",
        "keywords_to_add": [],
        "suggested_order": ["Education", "Research Interests", "Publications",
                            "Experience", "Skills", "Awards"],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_tailoring_hints(
    job: dict[str, Any],
    profile: dict[str, Any],
    profile_text: str,
    model: str | None = None,
    console=None,
) -> TailoringHints:
    """Generate per-position CV tailoring hints.

    Args:
        job:          Job listing dict (from job_searcher).
        profile:      Structured CVProfile dict (from cv_parser).
        profile_text: Compact text summary of the CV.
        model:        Optional LLM model override.
        console:      Optional rich Console for progress messages.

    Returns:
        TailoringHints dict with actionable suggestions.
    """
    client = LLMClient(model=model)

    prompt = _TAILOR_PROMPT.format(
        title=job.get("title", "Unknown"),
        institution=job.get("institution", job.get("company", "Unknown")),
        location=job.get("location", "Unknown"),
        pos_type=job.get("type", "unknown"),
        description=(job.get("description") or "No description provided.")[:3000],
        profile=profile_text,
    )

    try:
        raw = client.generate(system=_TAILOR_SYSTEM, user=prompt, json_mode=True)
    except RuntimeError as exc:
        if console:
            console.print(f"[red]LLM error during CV tailoring: {exc}[/red]")
        return _fallback_hints(str(exc))

    raw = _strip_fences(raw)

    try:
        hints: TailoringHints = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                hints = json.loads(m.group())
            except json.JSONDecodeError:
                return _fallback_hints("JSON parse error")
        else:
            return _fallback_hints("no JSON found in response")

    # Ensure all expected keys exist with sensible defaults
    hints.setdefault("headline_suggestion", "")
    hints.setdefault("skills_to_highlight", [])
    hints.setdefault("experience_to_emphasize", [])
    hints.setdefault("research_alignment", "")
    hints.setdefault("keywords_to_add", [])
    hints.setdefault("suggested_order", [])

    return hints


def format_hints_text(hints: TailoringHints) -> str:
    """Render TailoringHints as a human-readable plain-text block.

    Used when saving tailoring_hints.txt to disk.
    """
    lines: list[str] = ["CV TAILORING HINTS", "==================", ""]

    if hints.get("headline_suggestion"):
        lines += ["PROFILE SUMMARY TWEAK:", f"  {hints['headline_suggestion']}", ""]

    if hints.get("research_alignment"):
        lines += ["HOW TO FRAME YOUR RESEARCH INTERESTS:", f"  {hints['research_alignment']}", ""]

    if hints.get("skills_to_highlight"):
        lines += ["SKILLS TO EMPHASISE:"]
        for s in hints["skills_to_highlight"]:
            lines.append(f"  - {s}")
        lines.append("")

    if hints.get("experience_to_emphasize"):
        lines += ["EXPERIENCE ENTRIES TO HIGHLIGHT:"]
        for e in hints["experience_to_emphasize"]:
            lines.append(f"  - {e}")
        lines.append("")

    if hints.get("keywords_to_add"):
        lines += ["KEYWORDS TO ADD (from job description):"]
        lines.append("  " + ", ".join(hints["keywords_to_add"]))
        lines.append("")

    if hints.get("suggested_order"):
        lines += ["SUGGESTED CV SECTION ORDER:"]
        for i, section in enumerate(hints["suggested_order"], 1):
            lines.append(f"  {i}. {section}")
        lines.append("")

    return "\n".join(lines)
