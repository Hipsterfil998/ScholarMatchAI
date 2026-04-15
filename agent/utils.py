"""Shared utilities for parsing LLM responses."""

from __future__ import annotations

import json
import re
from typing import Any


def strip_fences(text: str) -> str:
    """Remove markdown code fences that models sometimes emit."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_json(raw: str) -> dict[str, Any] | None:
    """Parse JSON from a model response, tolerating fences and partial wrapping.

    Returns None if parsing fails entirely.
    """
    clean = strip_fences(raw)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", clean, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


def job_institution(job: dict) -> str:
    """Return the job's institution name, empty string if absent."""
    return job.get("institution") or ""


def job_description(job: dict, max_chars: int = 3000) -> str:
    """Return the job description truncated to max_chars."""
    return (job.get("description") or "No description provided.")[:max_chars]


def sanitize_filename(text: str, maxlen: int = 80) -> str:
    """Convert arbitrary text to a safe filename/directory component."""
    text = re.sub(r"[^\w\s\-]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text[:maxlen]
