<p align="center">
  <a href="https://github.com/Hipsterfil998/ScholarMatchAI">
    <img src="frontend/public/logo.svg" alt="ScholarMatchAI" width="80" />
  </a>
</p>

<h1 align="center">ScholarMatchAI</h1>

<p align="center">
  <strong>AI-powered search and application tool for PhD positions, postdocs, research fellowships, and academic staff roles.</strong>
</p>

<p align="center">
  🆓 <strong>100% free</strong> — no subscriptions, no API costs, no sign-up required.<br>
  📖 <a href="https://hipsterfil998.github.io/ScholarMatchAI">Full documentation</a>
</p>

---

## What it does

Upload your CV, set a research field and country, and ScholarMatchAI will:

- **Search** multiple academic job boards for open positions
- **Score** each position against your profile (0–100 match score)
- **Rank** all results and highlight the best fits
- **Generate** a personalized cover letter draft for every position
- **Export** all approved applications as a ZIP (cover letters + position details)

---

## How to use

1. Upload your CV (PDF, DOCX, or TXT)
2. Enter your research field (e.g. `machine learning`, `computational biology`)
3. Select a country or region from the dropdown (40+ options)
4. Choose the position type (`PhD`, `postdoc`, `fellowship`, `predoctoral`, `research staff`)
5. Set a minimum match score (used as a recommendation threshold — all positions are reviewable)
6. Click **Parse CV & Search Positions** and wait (~2–3 minutes)
7. In the **Results** tab, browse all scored positions
8. In the **Review** tab, load any position, read CV tailoring hints, and edit the cover letter
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
python server.py
```

The API will be available at `http://localhost:8000`. Start the frontend with:

```bash
cd frontend && npm install && npm run dev
```

---

## Project structure

```
ScholarMatchAI/
├── server.py                   # FastAPI backend
├── config.py                   # Runtime settings (model, thresholds, delays)
├── requirements.txt
├── frontend/                   # React + Vite + Tailwind frontend
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       ├── constants.js
│       └── components/
│           ├── SearchTab.jsx
│           ├── ResultsTab.jsx
│           ├── ReviewTab.jsx
│           └── ExportTab.jsx
└── agent/
    ├── __init__.py             # Public API: JobAgent, LLMQuotaError
    ├── pipeline.py             # JobAgent orchestrator
    ├── llm_client.py           # Groq / Ollama client
    ├── prompts/                # LLM prompts — one file per service
    ├── cv/                     # CV parsing, tailoring, cover letter
    ├── matching/               # LLM-based scoring
    └── search/                 # Scrapers (Euraxess, mlscientist, jobs.ac.uk, …)
```

---

## Model

Powered by [Groq](https://groq.com) free API — fast inference, no subscription required.
Uses `llama-3.3-70b-versatile` by default. For local use, set `LLM_BACKEND=ollama` in `.env`.

---

## Credits

Job data sourced from:
- [Euraxess](https://euraxess.ec.europa.eu) — European Commission portal for research careers
- [mlscientist.com](https://mlscientist.com) — ML & AI academic job board
- [jobs.ac.uk](https://www.jobs.ac.uk) — UK academic jobs portal
- [scholarshipdb.net](https://scholarshipdb.net) — Worldwide academic jobs and scholarships aggregator
- [nature.com/careers](https://www.nature.com/naturecareers) — Multidisciplinary global research job board

LLM inference powered by [Groq](https://groq.com) free API.

---

## Cite this work

If you use ScholarMatchAI in your research or project, please cite it as:

```bibtex
@software{pellegrino2026scholarmatchai,
  author  = {Pellegrhe ino, Filippo},
  title   = {{ScholarMatchAI}: an AI-powered search and application tool for academic positions},
  year    = {2026},
  url     = {https://github.com/Hipsterfil998/ScholarMatchAI},
  license = {AGPL-3.0}
}
```

---

## License

AGPL-3.0 — see [LICENSE](LICENSE) for details.
