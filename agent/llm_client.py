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
        elif self.backend == "huggingface":
            return self._generate_hf(system, user)
        else:
            raise RuntimeError(
                f"Unknown LLM backend: '{self.backend}'. "
                "Set LLM_BACKEND=ollama or LLM_BACKEND=huggingface in your .env."
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
    # HuggingFace implementation (via InferenceClient)
    # ------------------------------------------------------------------

    def _generate_hf(self, system: str, user: str) -> str:
        client = self._get_hf_client()
        prompt = self._format_hf_prompt(system, user, self.model)
        try:
            result = client.text_generation(
                prompt,
                max_new_tokens=config.max_tokens,
                do_sample=True,
                temperature=0.7,
            )
            # InferenceClient returns the generated text as a string
            return result if isinstance(result, str) else str(result)
        except Exception as exc:
            raise RuntimeError(
                f"HuggingFace inference failed: {exc}\n"
                "Check your HF_API_KEY and that the model is accessible."
            ) from exc

    def _stream_hf(self, system: str, user: str) -> Iterator[str]:
        client = self._get_hf_client()
        prompt = self._format_hf_prompt(system, user, self.model)
        try:
            for token in client.text_generation(
                prompt,
                max_new_tokens=config.max_tokens,
                stream=True,
                do_sample=True,
                temperature=0.7,
            ):
                # Each yielded item is a TextGenerationStreamOutput or plain str
                if hasattr(token, "token"):
                    yield token.token.text
                else:
                    yield str(token)
        except Exception as exc:
            raise RuntimeError(
                f"HuggingFace streaming failed: {exc}"
            ) from exc
