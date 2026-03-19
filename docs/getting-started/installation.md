# Installation

## Prerequisites

- **Python 3.10 or later** — PhdScout uses `str | None` union syntax and other modern Python features.
- **pip** — standard package manager (comes with Python).
- **Git** — to clone the repository.

Optionally, for local inference without any API key:

- **Ollama** — see [ollama.com](https://ollama.com) for installation instructions.

---

## 1. Clone the repository

```bash
git clone https://github.com/Hipsterfil998/PhDScout.git
cd PhDScout
```

---

## 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs:

| Package | Purpose |
|---|---|
| `openai>=1.0.0` | OpenAI-compatible client used for Groq and Ollama |
| `huggingface_hub>=0.20.0` | HuggingFace Serverless Inference client |
| `duckduckgo-search>=6.0.0` | Reserved — `WebSearchScraper` not active by default |
| `pdfplumber>=0.10.0` | PDF text extraction |
| `python-docx>=1.0.0` | DOCX text extraction |
| `click>=8.0.0` | CLI framework for `main.py` |
| `rich>=13.0.0` | Terminal output formatting |
| `python-dotenv>=1.0.0` | `.env` file loading |
| `requests>=2.31.0` | HTTP requests for scrapers |
| `beautifulsoup4>=4.12.0` | HTML parsing for scrapers |
| `lxml>=5.0.0` | Fast HTML/XML parser backend for BeautifulSoup |

!!! tip "Virtual environment"
    It is good practice to use a virtual environment to avoid dependency conflicts:
    ```bash
    python -m venv .venv
    source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```

---

## 3. Configure the LLM backend

PhdScout supports three LLM backends. Create a `.env` file in the project root with the appropriate settings for your chosen backend.

=== "Groq (recommended)"

    Groq provides a **free API** with fast inference and no usage limits for typical demo workloads. It is the default backend for the HuggingFace Space.

    1. Sign up at [console.groq.com](https://console.groq.com) (free, no credit card required).
    2. Create an API key at [console.groq.com/keys](https://console.groq.com/keys).
    3. Create `.env`:

    ```ini title=".env"
    LLM_BACKEND=groq
    GROQ_API_KEY=gsk_your_key_here
    ```

    Available models (set via `--model` CLI flag or `model_dropdown` in the UI):

    | Model | Speed | Quality |
    |---|---|---|
    | `llama-3.3-70b-versatile` | Medium | Highest (default) |
    | `llama-3.1-8b-instant` | Very fast | Good |

=== "HuggingFace Serverless"

    HuggingFace provides a free serverless inference API. It has **quota limits** — once exhausted (HTTP 402), PhdScout raises `LLMQuotaError` and shows an error in the UI.

    1. Create a free account at [huggingface.co](https://huggingface.co).
    2. Generate a token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
    3. Create `.env`:

    ```ini title=".env"
    LLM_BACKEND=huggingface
    HF_API_KEY=hf_your_token_here
    HF_MODEL=mistralai/Mistral-7B-Instruct-v0.3
    ```

    !!! warning "Quota limits"
        The free HuggingFace tier has a monthly quota. When it is exhausted, all LLM calls will fail with a quota error. Switching to Groq resolves this immediately.

=== "Ollama (local)"

    Ollama runs models locally — **no API key required**, completely private.

    1. Install Ollama from [ollama.com](https://ollama.com/download).
    2. Start the server:

    ```bash
    ollama serve
    ```

    3. Pull a model:

    ```bash
    ollama pull llama3.1:8b
    ```

    4. Create `.env`:

    ```ini title=".env"
    LLM_BACKEND=ollama
    OLLAMA_MODEL=llama3.1:8b
    OLLAMA_BASE_URL=http://localhost:11434/v1
    ```

    !!! note "Model quality"
        For best results with Ollama, use a model with at least 8B parameters. The `llama3.1:8b` model (4.7 GB) produces good cover letters and scoring. Larger models (70B, quantised) will produce better results but require significant RAM.

---

## 4. Verify the installation

Run a quick sanity check:

```bash
python -c "from agent import JobAgent, LLMQuotaError; print('OK')"
```

You should see `OK`. If you get an import error, check that all dependencies are installed and that you are in the correct virtual environment.

To verify the LLM connection:

```bash
python -c "
from config import config
config.validate()
print('Backend:', config.llm_backend)
"
```

For Groq and Ollama this will print a warning if the credentials or server are not reachable.

---

## 5. Optional: install Gradio for the web UI

Gradio is not listed in `requirements.txt` because it is pre-installed in the HuggingFace Spaces environment. To run the web UI locally:

```bash
pip install gradio>=4.0.0
python app.py
# Open http://localhost:7860 in your browser
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'openai'`**
: Run `pip install openai>=1.0.0`. This package is required for both Groq and Ollama backends.

**`Cannot connect to Ollama at http://localhost:11434`**
: Make sure Ollama is running with `ollama serve`. You can check with `curl http://localhost:11434`.

**`HuggingFace quota exceeded (402)`**
: Your free HF quota is exhausted. Switch to `LLM_BACKEND=groq` in your `.env` file.

**`lxml` build fails on Linux**
: Install the system library first: `sudo apt-get install libxml2-dev libxslt-dev`, then retry.
