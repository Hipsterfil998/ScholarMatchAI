---
title: Research Job Agent
emoji: 🎓
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: "5.25.0"
app_file: app.py
pinned: false
license: mit
---

# Research Job Agent 🎓

AI-powered search agent for PhD positions, postdocs, research fellowships, and academic staff roles.

Upload your CV, specify a research field and country, and the agent will:
- Search multiple academic job boards for open positions
- Score each position against your profile (0–100)
- Generate a personalized cover letter draft for every position you select
- Export all application materials as a ZIP

## Job sources

| Source | Coverage |
|--------|----------|
| [Euraxess](https://euraxess.ec.europa.eu/jobs/search) | Europe and worldwide — official EU research portal |
| [mlscientist.com](https://mlscientist.com) | ML / AI academic positions worldwide |
| [jobs.ac.uk](https://www.jobs.ac.uk) | UK academic jobs (queried only when UK is selected) |
| DuckDuckGo web search | Targeted queries for open calls by field, country, and position type |

## How to use
1. Upload your CV (PDF, DOCX, or TXT)
2. Enter your research field (e.g. "machine learning", "computational biology")
3. Select a country or region from the dropdown (40+ options, or type a custom value)
4. Choose the position type and minimum match score
5. Click **Parse CV & Search Positions** and wait (~2–3 minutes)
6. In the **Results** tab, review all found positions and their scores
7. In the **Review & Edit** tab, load each position, read the tailoring hints, and edit the cover letter
8. Click **Approve & Save** for positions you want to apply to
9. In the **Export** tab, download all approved applications as a ZIP

## Models
Powered by free [HuggingFace Inference API](https://huggingface.co/inference-api) models — no paid subscription required.

Available models:
- `Qwen/Qwen2.5-7B-Instruct` (default, recommended)
- `meta-llama/Llama-3.2-3B-Instruct`
- `microsoft/Phi-3.5-mini-instruct`
- `mistralai/Mistral-Nemo-Instruct-2407`
- `google/gemma-2-9b-it`
