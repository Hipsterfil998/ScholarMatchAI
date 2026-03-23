"""Configuration module — loads settings from environment / .env file.

All runtime settings are exposed through the singleton `config` instance.
"""

import os
from dataclasses import dataclass, field

import requests
from dotenv import load_dotenv

load_dotenv()


@dataclass
class EmailConfig:
    """SMTP email configuration (optional — used only if you want to send applications)."""

    smtp_host: str = field(default_factory=lambda: os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("EMAIL_SMTP_PORT", "587")))
    email_from: str = field(default_factory=lambda: os.getenv("EMAIL_FROM", ""))
    email_password: str = field(default_factory=lambda: os.getenv("EMAIL_PASSWORD", ""))

    def is_configured(self) -> bool:
        """Return True if SMTP credentials are fully set."""
        return bool(self.email_from and self.email_password)


@dataclass
class AppConfig:
    """Main application configuration for the research job agent."""

    # LLM backend selection
    llm_backend: str = field(default_factory=lambda: os.getenv("LLM_BACKEND", "ollama"))

    # Ollama settings
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    )

    # HuggingFace settings (alternative backend)
    hf_api_key: str = field(default_factory=lambda: os.getenv("HF_API_KEY", ""))
    hf_model: str = field(
        default_factory=lambda: os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
    )

    # Groq settings (recommended free cloud backend)
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Generation settings
    max_tokens: int = 4096
    default_model: str = field(
        default_factory=lambda: os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    )

    # Scraper behaviour
    scraper_delay: float = 1.5     # polite delay between HTTP requests (seconds)
    max_results_per_source: int = 20  # max listings fetched from each job board

    # Freshness thresholds (used to label and filter results)
    recent_days: int = 30          # posted within N days → "Recent"
    deadline_warn_days: int = 14   # deadline within N days → "Closing soon"

    # UI defaults
    min_score_default: int = 60    # default minimum match score slider value

    # Output directory for saved applications
    output_dir: str = field(default_factory=lambda: os.getenv("OUTPUT_DIR", "./output"))

    # Email config (optional)
    email: EmailConfig = field(default_factory=EmailConfig)

    def validate(self) -> None:
        """
        Check that the selected backend is available.

        For Ollama: performs a quick GET to http://localhost:11434 and warns
        if the server is not reachable (does not raise — just prints a warning).

        For HuggingFace: warns if HF_API_KEY is empty.
        """
        if self.llm_backend == "ollama":
            # Strip /v1 suffix to get the base health-check URL
            base = self.ollama_base_url.rstrip("/")
            if base.endswith("/v1"):
                base = base[:-3]
            try:
                resp = requests.get(base, timeout=3)
                # Ollama returns 200 with "Ollama is running" on the root path
                if resp.status_code != 200:
                    print(
                        f"[WARNING] Ollama responded with HTTP {resp.status_code}. "
                        "It may not be running correctly."
                    )
            except requests.exceptions.ConnectionError:
                print(
                    "\n[WARNING] Cannot reach Ollama at "
                    f"{base}.\n"
                    "         Start it with:  ollama serve\n"
                    "         Then pull a model: ollama pull llama3.1:8b\n"
                )
            except requests.exceptions.Timeout:
                print(f"[WARNING] Ollama health-check timed out at {base}.")

        elif self.llm_backend == "huggingface":
            if not self.hf_api_key:
                print(
                    "[WARNING] HF_API_KEY is not set. "
                    "Free HuggingFace inference may be rate-limited or unavailable. "
                    "Get a free key at https://huggingface.co/settings/tokens"
                )
        elif self.llm_backend == "groq":
            if not self.groq_api_key:
                print(
                    "[WARNING] GROQ_API_KEY is not set. "
                    "Get a free key at https://console.groq.com/keys"
                )
        else:
            print(
                f"[WARNING] Unknown LLM_BACKEND '{self.llm_backend}'. "
                "Supported values: 'ollama', 'huggingface', 'groq'."
            )


# Singleton config instance — import this everywhere
config = AppConfig()
