---
title: PhdScout
emoji: 🎓
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: "5.25.0"
app_file: app.py
pinned: false
license: mit
---

<h1 align="center">PhdScout 🎓</h1>

<p align="center">
  <strong>AI-powered search agent for PhD positions, postdocs, research fellowships, and academic staff roles.</strong>
</p>

<p align="center">
  🆓 <strong>100% free</strong> — no subscriptions, no API costs, no sign-up required.<br>
  Live demo on HuggingFace Spaces: <a href="https://huggingface.co/spaces/HipFil98/research-job-agent">HipFil98/research-job-agent</a><br>
  📖 <a href="https://hipsterfil998.github.io/PhDScout">Full documentation</a>
</p>

---

## What it does

Upload your CV, set a research field and country, and PhdScout will:

- **Search** multiple academic job boards for open positions
- **Score** each position against your profile (0–100 match score)
- **Rank** all results and highlight the best fits
- **Generate** a personalized cover letter draft for every position
- **Export** all approved applications as a ZIP (cover letters + position details)

---

## Job sources

| Source | Coverage |
|--------|----------|
| [Euraxess](https://euraxess.ec.europa.eu/jobs/search) | Europe and worldwide — official EU research portal |
| [mlscientist.com](https://mlscientist.com) | ML / AI academic positions worldwide |
| [jobs.ac.uk](https://www.jobs.ac.uk) | UK academic jobs (queried only when UK is selected) |

---

## How to use

1. Upload your CV (PDF, DOCX, or TXT)
2. Enter your research field (e.g. `machine learning`, `computational biology`)
3. Select a country or region from the dropdown (40+ options, or type a custom value)
4. Choose the position type (`PhD`, `postdoc`, `fellowship`, `predoctoral`, `research staff`)
5. Set a minimum match score (used as a recommendation threshold — all positions are reviewable)
6. Click **Parse CV & Search Positions** and wait (~2–3 minutes)
7. In the **Results** tab, browse all scored positions
8. In the **Review & Edit** tab, load any position, read CV tailoring hints, and edit the cover letter
9. Click **Approve & Save** for positions you want to apply to
10. In the **Export** tab, download all approved applications as a ZIP

---

## Running locally

```bash
git clone https://github.com/Hipsterfil998/PhDScout.git
cd PhDScout
pip install -r requirements.txt
```

Create a `.env` file:

```env
LLM_BACKEND=groq
GROQ_API_KEY=your_groq_api_key
```

Get a free Groq API key at [console.groq.com/keys](https://console.groq.com/keys).

Then run:

```bash
python app.py
```

The app will be available at `http://localhost:7860`.

---

## Project structure

```
PhDScout/
├── app.py                      # Gradio web interface
├── config.py                   # Runtime settings (model, thresholds, delays)
├── requirements.txt
└── agent/
    ├── __init__.py             # Public API: JobAgent, LLMQuotaError
    ├── pipeline.py             # JobAgent orchestrator
    ├── base_service.py         # BaseLLMService base class
    ├── llm_client.py           # Groq / HuggingFace / Ollama client
    ├── utils.py                # Shared utilities
    ├── prompts/                # LLM prompts — one file per service
    │   ├── cv_parser.py
    │   ├── job_matcher.py
    │   ├── cv_tailor.py
    │   └── cover_letter.py
    ├── cv/                     # CV-related services
    │   ├── parser.py           # CV extraction + LLM parsing
    │   ├── tailor.py           # Tailoring hints generator
    │   └── cover_letter.py     # Cover letter writer
    ├── matching/
    │   └── matcher.py          # LLM-based scoring + PhD eligibility cap
    └── search/
        ├── searcher.py         # JobSearcher (orchestrates scrapers)
        └── scrapers/
            ├── base.py         # BaseScraper ABC + shared helpers
            ├── euraxess.py
            ├── mlscientist.py
            └── jobs_ac_uk.py
```

---

## Model

Powered by [Groq](https://groq.com) free API — fast inference, no subscription required.
Uses `llama-3.1-8b-instant` by default. To change the model, edit `default_model` in `config.py`.

For local use, the app also supports **Ollama** — set `LLM_BACKEND=ollama` in `.env`.

---

## License

MIT
