"""Unified LLM client supporting Ollama (local) and HuggingFace backends.

Usage
-----
from agent.llm_client import LLMClient

client = LLMClient()
response = client.generate(system="You are helpful.", user="What is a PhD?")

# Streaming
for token in client.stream_generate(system="...", user="..."):
    print(token, end="", flush=True)
"""

from __future__ import annotations

from typing import Iterator

from config import config


class LLMQuotaError(RuntimeError):
    """Raised when the HuggingFace free-tier quota is exhausted (HTTP 402)."""


class LLMClient:
    """Unified LLM client supporting Ollama and HuggingFace backends.

    Backend is selected at instantiation time from config.llm_backend.
    An explicit `model` argument overrides the config default.
    """

    def __init__(self, model: str | None = None, backend: str | None = None, token: str | None = None) -> None:
        self.backend = backend or config.llm_backend
        # Resolve model: explicit arg > config
        if model:
            self.model = model
        elif self.backend == "ollama":
            self.model = config.ollama_model
        else:
            self.model = model or config.hf_model

        # Token override (used when backend == "huggingface")
        self._token_override = token

        # Lazily initialised clients
        self._openai_client = None
        self._hf_client = None
        self._groq_client = None

    # ------------------------------------------------------------------
    # Internal: backend initialisation
    # ------------------------------------------------------------------

    def _get_openai_client(self):
        """Return (and cache) an openai.OpenAI client pointed at Ollama."""
        if self._openai_client is None:
            try:
                from openai import OpenAI  # type: ignore
            except ImportError as exc:
                raise ImportError(
                    "The 'openai' package is required for the Ollama backend.\n"
                    "Install it with:  pip install openai>=1.0.0"
                ) from exc
            self._openai_client = OpenAI(
                base_url=config.ollama_base_url,
                api_key="ollama",  # Ollama ignores the key — any non-empty string works
            )
        return self._openai_client

    def _get_groq_client(self):
        """Return (and cache) an openai.OpenAI client pointed at Groq."""
        if self._groq_client is None:
            try:
                from openai import OpenAI  # type: ignore
            except ImportError as exc:
                raise ImportError(
                    "The 'openai' package is required for the Groq backend.\n"
                    "Install it with:  pip install openai>=1.0.0"
                ) from exc
            api_key = self._token_override or config.groq_api_key
            self._groq_client = OpenAI(
                base_url=config.groq_base_url,
                api_key=api_key,
                # Groq's free tier is tokens-per-minute bound, so a batch of
                # jobs inevitably hits 429 part-way through. The SDK retries
                # with backoff and honours Retry-After; its default of 2 tries
                # is far too few to ride out a full TPM window.
                max_retries=config.llm_max_retries,
                timeout=config.llm_timeout,
            )
        return self._groq_client

    def _get_hf_client(self):
        """Return (and cache) a huggingface_hub.InferenceClient."""
        if self._hf_client is None:
            try:
                from huggingface_hub import InferenceClient  # type: ignore
            except ImportError as exc:
                raise ImportError(
                    "The 'huggingface_hub' package is required for the HuggingFace backend.\n"
                    "Install it with:  pip install huggingface_hub>=0.20.0"
                ) from exc
            token = self._token_override or (config.hf_api_key if config.hf_api_key else None)
            self._hf_client = InferenceClient(model=self.model, token=token)
        return self._hf_client

    # ------------------------------------------------------------------
    # Internal: prompt formatting for HuggingFace
    # ------------------------------------------------------------------

    @staticmethod
    def _format_hf_prompt(system: str, user: str, model: str) -> str:
        """Format a system+user prompt into the template expected by common models.

        Mistral-style models use [INST]...[/INST].
        Most other chat-tuned models (Llama, Falcon, etc.) use <|user|> tags.
        """
        model_lower = model.lower()
        if "mistral" in model_lower or "mixtral" in model_lower:
            # Mistral Instruct format
            # System prompt is prepended inside the user turn for Mistral v0.x
            return f"[INST] {system}\n\n{user} [/INST]"
        elif "llama" in model_lower:
            # Llama 3 chat template
            return (
                "<|begin_of_text|>"
                f"<|start_header_id|>system<|end_header_id|>\n{system}<|eot_id|>"
                f"<|start_header_id|>user<|end_header_id|>\n{user}<|eot_id|>"
                "<|start_header_id|>assistant<|end_header_id|>\n"
            )
        else:
            # Generic fallback — works for many instruction-tuned models
            return f"<|system|>\n{system}\n<|user|>\n{user}\n<|assistant|>\n"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, system: str, user: str, json_mode: bool = False) -> str:
        """Generate a complete response from the LLM.

        Args:
            system: System/instruction prompt.
            user:   User message.
            json_mode: If True, hint the model to respond only with valid JSON.
                       For Ollama this also sets response_format={"type":"json_object"}.

        Returns:
            The model's response as a plain string.

        Raises:
            RuntimeError: If the backend call fails (with a helpful message).
        """
        if json_mode:
            system = "Respond only with valid JSON. " + system

        if self.backend == "ollama":
            return self._generate_ollama(system, user, json_mode=json_mode)
        elif self.backend == "groq":
            return self._generate_groq(system, user, json_mode=json_mode)
        elif self.backend == "huggingface":
            return self._generate_hf(system, user)
        else:
            raise RuntimeError(
                f"Unknown LLM backend: '{self.backend}'. "
                "Set LLM_BACKEND=ollama, groq, or huggingface in your .env."
            )

    def stream_generate(self, system: str, user: str) -> Iterator[str]:
        """Stream response tokens one by one.

        Args:
            system: System/instruction prompt.
            user:   User message.

        Yields:
            Individual text tokens/chunks as strings.
        """
        if self.backend == "ollama":
            yield from self._stream_ollama(system, user)
        elif self.backend == "groq":
            yield from self._stream_groq(system, user)
        elif self.backend == "huggingface":
            yield from self._stream_hf(system, user)
        else:
            raise RuntimeError(
                f"Unknown LLM backend: '{self.backend}'."
            )

    # ------------------------------------------------------------------
    # Ollama implementation (via openai-compatible REST API)
    # ------------------------------------------------------------------

    def _generate_ollama(self, system: str, user: str, json_mode: bool = False) -> str:
        client = self._get_openai_client()
        kwargs: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": config.max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as exc:
            # Provide a helpful error message distinguishing connection failures
            err_str = str(exc)
            if "connection" in err_str.lower() or "connect" in err_str.lower():
                raise RuntimeError(
                    f"Cannot connect to Ollama at {config.ollama_base_url}.\n"
                    "Make sure Ollama is running:  ollama serve\n"
                    f"And the model is available:  ollama pull {self.model}"
                ) from exc
            raise RuntimeError(f"Ollama generation failed: {exc}") from exc

    def _stream_ollama(self, system: str, user: str) -> Iterator[str]:
        client = self._get_openai_client()
        try:
            stream = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=config.max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except Exception as exc:
            err_str = str(exc)
            if "connection" in err_str.lower() or "connect" in err_str.lower():
                raise RuntimeError(
                    f"Cannot connect to Ollama at {config.ollama_base_url}.\n"
                    "Start Ollama with:  ollama serve"
                ) from exc
            raise RuntimeError(f"Ollama streaming failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Groq implementation (OpenAI-compatible API)
    # ------------------------------------------------------------------

    def _generate_groq(self, system: str, user: str, json_mode: bool = False) -> str:
        client = self._get_groq_client()
        kwargs: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": config.max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise RuntimeError(f"Groq inference failed: {exc}") from exc

    def _stream_groq(self, system: str, user: str) -> Iterator[str]:
        client = self._get_groq_client()
        try:
            stream = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=config.max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except Exception as exc:
            raise RuntimeError(f"Groq streaming failed: {exc}") from exc

    # ------------------------------------------------------------------
    # HuggingFace implementation (via InferenceClient)
    # ------------------------------------------------------------------

    def _generate_hf(self, system: str, user: str) -> str:
        client = self._get_hf_client()
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                result = client.chat_completion(
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=config.max_tokens,
                    temperature=0.7,
                )
                return result.choices[0].message.content or ""
            except Exception as exc:
                last_exc = exc
                err_str = str(exc)
                if "402" in err_str:
                    raise LLMQuotaError(
                        "HuggingFace quota exceeded (402 Payment Required).\n"
                        "Switch to a different model in the LLM Settings panel, "
                        "or wait for your free-tier quota to reset."
                    ) from exc
                if "503" in err_str or "502" in err_str or "529" in err_str:
                    import time as _time
                    _time.sleep(2 ** attempt)  # 1s, 2s, 4s
                    continue
                break
        raise RuntimeError(
            f"HuggingFace inference failed: {last_exc}\n"
            "Check your HF_API_KEY and that the model is accessible."
        ) from last_exc

    def _stream_hf(self, system: str, user: str) -> Iterator[str]:
        client = self._get_hf_client()
        try:
            stream = client.chat_completion(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=config.max_tokens,
                temperature=0.7,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:
            raise RuntimeError(
                f"HuggingFace streaming failed: {exc}"
            ) from exc
