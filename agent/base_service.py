"""Base class for all LLM-backed agent services."""

from __future__ import annotations

from typing import Any

from agent.llm_client import LLMClient, LLMQuotaError
from agent.utils import parse_json


class BaseLLMService:
    """Base for every service that wraps an LLM call.

    Subclasses declare ``_SYSTEM`` as a class-level string and call either
    ``_generate()`` (prose) or ``_generate_json()`` (structured JSON).

    Error policy
    ------------
    - ``LLMQuotaError`` always propagates to the caller — it is a user-facing
      error (quota exhausted) that must be surfaced in the UI.
    - Other ``RuntimeError`` from the LLM backend are absorbed by
      ``_generate_json()`` which returns ``None``; callers substitute a fallback.
    - ``_generate()`` propagates everything — the caller decides how to handle.
    """

    _SYSTEM: str = ""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    # ------------------------------------------------------------------
    # Protected helpers
    # ------------------------------------------------------------------

    def _generate(self, prompt: str, json_mode: bool = False) -> str:
        """Raw LLM call — all exceptions propagate unchecked."""
        return self.llm.generate(system=self._SYSTEM, user=prompt, json_mode=json_mode)

    def _generate_json(self, prompt: str) -> dict[str, Any] | None:
        """LLM call expecting a JSON response.

        Returns:
            Parsed dict, or ``None`` if the LLM call fails or JSON is malformed.

        Raises:
            LLMQuotaError: always re-raised — the UI must show it to the user.
        """
        try:
            raw = self.llm.generate(system=self._SYSTEM, user=prompt, json_mode=True)
        except LLMQuotaError:
            raise
        except RuntimeError as exc:
            # Preserve the error message so callers can surface it to the user
            # instead of silently returning score=0.
            return {"_llm_error": str(exc)}
        return parse_json(raw)
