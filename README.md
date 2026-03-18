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
  Live demo on HuggingFace Spaces: <a href="https://huggingface.co/spaces/HipFil98/research-job-agent">HipFil98/research-job-agent</a>
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
| DuckDuckGo web search | Targeted queries for open calls by field, country, and position type |

---

## How to use

1. Upload your CV (PDF, DOCX, or TXT)
2. Enter your research field (e.g. `machine learning`, `computational biology`)
3. Select a country or region from the dropdown (40+ options, or type a custom value)
4. Choose the position type (`PhD`, `postdoc`, `fellowship`, `predoctoral`, `research staff`)
5. Set a minimum match score (used as a recommendation threshold — all positions are reviewable)
6. Click **Parse CV & Search Positions** and wait (~2–3 minutes)
7. In the **Results** tab, browse all found positions and the recommended shortlist
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
LLM_BACKEND=huggingface
HF_API_KEY=your_huggingface_token
```

Then run:

```bash
python app.py
```

The app will be available at `http://localhost:7860`.

---

## Project structure

```
PhDScout/
├── app.py                  # Gradio web interface
├── config.py               # Configuration (env vars, defaults)
├── requirements.txt
├── agent/
│   ├── pipeline.py         # JobAgent orchestrator
│   ├── job_searcher.py     # Multi-source job scraper
│   ├── cv_parser.py        # CV text extraction + LLM parsing
│   ├── job_matcher.py      # LLM-based position scoring
│   ├── cv_tailor.py        # CV tailoring hints generator
│   ├── cover_letter.py     # Cover letter generator
│   ├── llm_client.py       # Unified LLM client (Ollama / HuggingFace)
│   └── utils.py            # Shared utilities
```

---

## Models

Powered by free [HuggingFace Inference API](https://huggingface.co/inference-api) models — no paid subscription required.

| Model | Notes |
|-------|-------|
| `Qwen/Qwen2.5-7B-Instruct` | Default, recommended |
| `meta-llama/Llama-3.2-3B-Instruct` | Lightweight |
| `microsoft/Phi-3.5-mini-instruct` | Fast |
| `mistralai/Mistral-Nemo-Instruct-2407` | Good instruction following |
| `google/gemma-2-9b-it` | Strong reasoning |

For local use, the app also supports **Ollama** — set `LLM_BACKEND=ollama` in `.env`.

---

## License

MIT
