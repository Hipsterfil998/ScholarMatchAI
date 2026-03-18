---
title: Research Job Agent
emoji: 🎓
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: "5.9.0"
app_file: app.py
pinned: false
license: mit
---

# Research Job Agent 🎓

AI-powered PhD / postdoc / fellowship search agent.

Parses your CV, searches free research job boards (Euraxess, FindAPhD, jobs.ac.uk, Academic Positions, DuckDuckGo), scores positions against your profile, and helps you write personalized cover letters.

## How to use
1. Upload your CV (PDF, DOCX, or TXT)
2. Enter your research field and location preferences
3. Provide your free HuggingFace API token (get one at huggingface.co/settings/tokens)
4. Click "Search" and wait (~2-3 minutes)
5. Review each position, edit the cover letter draft, and approve
6. Download all your application materials as a ZIP

## Models
Uses free HuggingFace Inference API models — no paid subscription required.
Recommended: `mistralai/Mistral-7B-Instruct-v0.3`
