"""FastAPI backend for ScholarMatchAI — replaces Gradio app.py."""

from __future__ import annotations

import json
import os
import tempfile
import zipfile
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agent import JobAgent
from agent.utils import job_institution, sanitize_filename
from config import config

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="ScholarMatchAI API", version="1.0.0")

_ORIGINS = [
    "https://scholarmatchai.com",
    "https://www.scholarmatchai.com",
    "http://localhost:5173",   # Vite dev server
    "http://localhost:4173",   # Vite preview
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
_HF_TOKEN = os.environ.get("HF_TOKEN", "")

if _GROQ_KEY:
    _BACKEND, _API_KEY = "groq", _GROQ_KEY
else:
    _BACKEND, _API_KEY = "huggingface", _HF_TOKEN

_MODEL = config.default_model


def _agent() -> JobAgent:
    return JobAgent(model=_MODEL, backend=_BACKEND, api_key=_API_KEY)


def _check_key() -> None:
    if not _API_KEY and _BACKEND != "ollama":
        raise HTTPException(400, "No API key configured. Set GROQ_API_KEY as an environment variable.")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "backend": _BACKEND}


# ---------------------------------------------------------------------------
# Step 1 — Parse CV
# ---------------------------------------------------------------------------

@app.post("/api/parse-cv")
async def parse_cv(cv: UploadFile = File(...), _: None = Depends(_check_key)) -> dict:
    suffix = os.path.splitext(cv.filename or "cv.pdf")[1] or ".pdf"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(await cv.read())
        cv_path = f.name
    try:
        profile, profile_text = _agent().parse_cv(cv_path)
        return {"profile": profile, "profile_text": profile_text}
    finally:
        os.unlink(cv_path)


# ---------------------------------------------------------------------------
# Step 2 — Search job boards
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    field: str
    location: str = "Europe"
    position_type: str = "any"


@app.post("/api/search-jobs")
def search_jobs(req: SearchRequest) -> dict:
    jobs = _agent().search_jobs(req.field, req.location, req.position_type)
    return {"jobs": jobs}


# ---------------------------------------------------------------------------
# Step 3 — Score jobs with AI
# ---------------------------------------------------------------------------

class ScoreRequest(BaseModel):
    jobs: list[dict[str, Any]]
    profile_text: str


@app.post("/api/score-jobs")
def score_jobs(req: ScoreRequest, _: None = Depends(_check_key)) -> dict:
    if not req.jobs:
        return {"scored_jobs": []}
    scored = _agent().score_jobs(req.jobs, req.profile_text)
    return {"scored_jobs": scored}


# ---------------------------------------------------------------------------
# Load position — hints + cover letter
# ---------------------------------------------------------------------------

class PrepareRequest(BaseModel):
    job: dict[str, Any]
    profile_text: str


@app.post("/api/prepare")
def prepare(req: PrepareRequest, _: None = Depends(_check_key)) -> dict:
    hints, cover_letter = _agent().prepare_application(req.job, req.profile_text)
    return {"hints": hints, "cover_letter": cover_letter}


@app.post("/api/regenerate")
def regenerate(req: PrepareRequest, _: None = Depends(_check_key)) -> dict:
    letter = _agent().regenerate_letter(req.job, req.profile_text)
    return {"cover_letter": letter}


# ---------------------------------------------------------------------------
# Export ZIP
# ---------------------------------------------------------------------------

class ExportRequest(BaseModel):
    approved: list[dict[str, Any]]


@app.post("/api/export")
def export_zip(req: ExportRequest) -> FileResponse:
    if not req.approved:
        raise HTTPException(400, "No approved applications to export.")

    tmp = tempfile.mkdtemp()
    zip_path = os.path.join(tmp, "applications.zip")
    summary = []

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for entry in req.approved:
            job = entry.get("job") or {}
            title = job.get("title", "Unknown")
            institution = job_institution(job) or "Unknown"
            safe = sanitize_filename(f"{institution}_{title}")
            d = f"applications/{safe}"
            if entry.get("cover_letter"):
                zf.writestr(f"{d}/cover_letter_draft.txt", entry["cover_letter"])
            if entry.get("notes"):
                zf.writestr(f"{d}/my_notes.txt", entry["notes"])
            match: dict = job.get("match") or {}
            zf.writestr(f"{d}/position_details.json", json.dumps({
                "title": title,
                "institution": institution,
                "location": job.get("location", ""),
                "type": job.get("type", ""),
                "source": job.get("source", ""),
                "url": job.get("url", ""),
                "deadline": job.get("deadline"),
                "description": job.get("description", ""),
                "match_score": match.get("match_score", 0),
                "recommendation": match.get("recommendation", ""),
                "why_good_fit": match.get("why_good_fit", ""),
            }, indent=2, ensure_ascii=False))
            summary.append({
                "title": title,
                "institution": institution,
                "match_score": match.get("match_score", 0),
                "url": job.get("url", ""),
                "approved_at": entry.get("approved_at", ""),
            })
        zf.writestr("summary.json", json.dumps(summary, indent=2, ensure_ascii=False))

    return FileResponse(zip_path, media_type="application/zip", filename="applications.zip")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
