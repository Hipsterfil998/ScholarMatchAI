"""Cover letter generator for research/PhD/postdoc applications.

Generates a DRAFT cover letter tailored to the specific position and research group.
The letter uses an academic tone and follows a research-application structure:
  1. Opening — express interest in the specific group / PI
  2. Research fit — align your background with the group's work
  3. Key contributions — 2-3 most relevant publications / projects / skills
  4. Methodology — relevant technical skills and methods
  5. Closing — why this institution/group, timeline, enthusiasm

The output is explicitly marked as a DRAFT so the user remembers to personalise it.
"""

from __future__ import annotations

import re
from typing import Any

from agent.llm_client import LLMClient


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

# Italian keyword set — used to auto-detect when the job posting is in Italian
_ITALIAN_KEYWORDS = {
    "ricerca", "lavoro", "azienda", "esperienza", "candidato", "assunzione",
    "offerta", "contratto", "sede", "srl", "spa", "società", "università",
    "bando", "dottorato", "assegno di ricerca", "borsa", "ricercatore",
    "Milano", "Roma", "Torino", "Napoli", "Firenze", "Bologna", "Italia",
}


def _detect_language(job: dict[str, Any], preferred: str = "auto") -> str:
    """Return 'Italian' or 'English' based on preference or job content.

    Args:
        job:       Job listing dict.
        preferred: 'it', 'en', or 'auto'.
    """
    if preferred == "it":
        return "Italian"
    if preferred == "en":
        return "English"

    text = " ".join([
        job.get("title", ""),
        job.get("description", ""),
        job.get("location", ""),
        job.get("institution", job.get("company", "")),
    ]).lower()

    italian_hits = sum(1 for kw in _ITALIAN_KEYWORDS if kw.lower() in text)
    return "Italian" if italian_hits >= 2 else "English"


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_COVER_LETTER_SYSTEM = """You are an expert academic writing coach helping a researcher
write a cover letter for a PhD / postdoc / research fellowship application.
Write in a formal academic style. Be specific — reference the actual research group,
PI name (if available), and job description details.
Do NOT use generic phrases like "I am a hard worker" or "team player".
Do NOT invent qualifications or experience not present in the candidate profile.
The letter should be 400-600 words (3-4 paragraphs)."""

_COVER_LETTER_PROMPT = """Write a cover letter for the following application.

CANDIDATE PROFILE:
{profile}

POSITION:
Title: {title}
Institution: {institution}
Location: {location}
Type: {pos_type}
Description:
{description}

INSTRUCTIONS:
- Language: {language}
- Tone: formal academic, enthusiastic but professional
- Structure:
    Paragraph 1 (Opening): Express specific interest in the research group / lab.
      Mention the PI name or lab name if available in the description.
      State the position title and where you found it.
    Paragraph 2 (Research fit): Explain how your research background aligns
      with the group's work. Reference your thesis topic or key projects.
    Paragraph 3 (Key contributions): Highlight 2-3 most relevant publications,
      projects, or technical skills. Be specific — titles, venues, methods.
    Paragraph 4 (Closing): Explain why this specific institution/group, your
      timeline / availability, and express enthusiasm for an interview.

- If writing in Italian: use formal "Lei" form throughout.
- If a PI name is visible in the description: address the letter to them.
- Start the letter with "Dear [title/name]," or appropriate Italian equivalent.
- End with "Sincerely," / "Cordialmente," followed by the candidate's name.
- Do NOT add a subject line or email header.
{regen_note}"""

_REGEN_NOTE = (
    "\n- This is a REGENERATION request. "
    "Please produce a meaningfully different version — vary the opening hook, "
    "change which projects are highlighted, or adjust the framing.\n"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_pi_name(description: str) -> str | None:
    """Try to extract a PI name from a job description (heuristic)."""
    # Look for "Prof. Surname", "Dr. Surname", "Professor Surname", "PI: Surname"
    patterns = [
        r"\b(?:Prof\.?|Professor|Dr\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"PI[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"supervisor[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    ]
    for pattern in patterns:
        m = re.search(pattern, description or "")
        if m:
            return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_cover_letter(
    job: dict[str, Any],
    profile: dict[str, Any],
    profile_text: str,
    preferred_lang: str = "auto",
    regenerate: bool = False,
    model: str | None = None,
    console=None,
) -> str:
    """Generate a DRAFT cover letter for a research position.

    Args:
        job:           Job listing dict (from job_searcher).
        profile:       Structured CVProfile (from cv_parser).
        profile_text:  Compact text summary of the CV.
        preferred_lang: 'it', 'en', or 'auto'.
        regenerate:    If True, ask the model for a different version.
        model:         Optional LLM model override.
        console:       Optional rich Console for progress messages.

    Returns:
        The cover letter as a string, prefixed with a [DRAFT] notice.
    """
    language = _detect_language(job, preferred_lang)
    title = job.get("title", "Unknown Position")
    institution = job.get("institution", job.get("company", "Unknown Institution"))

    if console:
        console.print(
            f"[cyan]  Generating cover letter in {language} "
            f"for {title} @ {institution}...[/cyan]"
        )

    client = LLMClient(model=model)

    prompt = _COVER_LETTER_PROMPT.format(
        profile=profile_text,
        title=title,
        institution=institution,
        location=job.get("location", "Unknown"),
        pos_type=job.get("type", "research"),
        description=(job.get("description") or "No description provided.")[:3000],
        language=language,
        regen_note=_REGEN_NOTE if regenerate else "",
    )

    try:
        letter = client.generate(system=_COVER_LETTER_SYSTEM, user=prompt)
    except RuntimeError as exc:
        if console:
            console.print(f"[red]LLM error generating cover letter: {exc}[/red]")
        return (
            "[DRAFT — GENERATION FAILED]\n\n"
            f"Error: {exc}\n\n"
            "Please write your cover letter manually."
        )

    # Prepend a prominent draft notice so the user cannot accidentally send it as-is
    draft_header = (
        "========================================\n"
        "  DRAFT — Please review and personalise before sending.\n"
        "  This letter was generated by an AI and may contain errors.\n"
        "========================================\n\n"
    )

    return draft_header + letter.strip()
