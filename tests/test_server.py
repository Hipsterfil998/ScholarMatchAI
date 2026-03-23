"""Tests for server.py FastAPI endpoints — mocks JobAgent, no real LLM or HTTP."""

from __future__ import annotations

import io
import json
import os
import zipfile
from unittest.mock import MagicMock, patch

import pytest

# Ensure a fake key is present before the server module is imported, so that
# the module-level _API_KEY is non-empty and _check_key() does not raise.
os.environ.setdefault("GROQ_API_KEY", "test-key")

from fastapi.testclient import TestClient
from server import app

client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _mock_agent(**overrides):
    """Return a MagicMock configured with sensible default return values."""
    agent = MagicMock()
    agent.parse_cv.return_value = (
        {"name": "Alice", "research_interests": ["NLP"]},
        "Alice, NLP researcher.",
    )
    agent.search_jobs.return_value = [
        {"title": "PhD in ML", "institution": "MIT", "location": "USA",
         "type": "phd", "url": "https://example.com/1", "description": "ML research",
         "posted": None, "deadline": None, "source": "test", "email": None},
    ]
    agent.score_jobs.return_value = [
        {"title": "PhD in ML", "institution": "MIT", "location": "USA",
         "type": "phd", "url": "https://example.com/1", "description": "ML research",
         "posted": None, "deadline": None, "source": "test", "email": None,
         "match": {"match_score": 85, "recommendation": "apply",
                   "matching_areas": ["ML"], "missing_requirements": [],
                   "why_good_fit": "Great fit.", "concerns": ""}},
    ]
    agent.prepare_application.return_value = (
        {"headline_suggestion": "Emphasise NLP", "skills_to_highlight": ["Python"]},
        "Dear Professor,\n\nI am writing to apply.",
    )
    agent.regenerate_letter.return_value = "Dear Professor,\n\nUpdated letter."
    for k, v in overrides.items():
        setattr(agent, k, v)
    return agent


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "backend" in data


# ---------------------------------------------------------------------------
# /api/search-jobs
# ---------------------------------------------------------------------------

class TestSearchJobs:
    def _post(self, payload, agent=None):
        mock = agent or _mock_agent()
        with patch("server._agent", return_value=mock):
            return client.post("/api/search-jobs", json=payload)

    def test_returns_jobs_list(self):
        resp = self._post({"field": "machine learning", "location": "Europe"})
        assert resp.status_code == 200
        assert "jobs" in resp.json()
        assert isinstance(resp.json()["jobs"], list)

    def test_passes_field_and_location(self):
        mock = _mock_agent()
        self._post({"field": "NLP", "location": "Germany"}, agent=mock)
        mock.search_jobs.assert_called_once_with("NLP", "Germany", "any")

    def test_passes_position_type(self):
        mock = _mock_agent()
        self._post({"field": "NLP", "location": "Germany", "position_type": "phd"}, agent=mock)
        mock.search_jobs.assert_called_once_with("NLP", "Germany", "phd")

    def test_missing_field_returns_422(self):
        resp = client.post("/api/search-jobs", json={"location": "Europe"})
        assert resp.status_code == 422

    def test_defaults_location_to_europe(self):
        mock = _mock_agent()
        self._post({"field": "ML"}, agent=mock)
        args = mock.search_jobs.call_args[0]
        assert args[1] == "Europe"


# ---------------------------------------------------------------------------
# /api/score-jobs
# ---------------------------------------------------------------------------

class TestScoreJobs:
    def _post(self, payload, agent=None):
        mock = agent or _mock_agent()
        with patch("server._agent", return_value=mock):
            return client.post("/api/score-jobs", json=payload)

    def test_returns_scored_jobs(self):
        jobs = [{"title": "PhD", "description": "ML"}]
        resp = self._post({"jobs": jobs, "profile_text": "Alice, ML researcher."})
        assert resp.status_code == 200
        assert "scored_jobs" in resp.json()

    def test_empty_jobs_returns_empty_without_calling_agent(self):
        mock = _mock_agent()
        resp = self._post({"jobs": [], "profile_text": "Alice"}, agent=mock)
        assert resp.status_code == 200
        assert resp.json()["scored_jobs"] == []
        mock.score_jobs.assert_not_called()

    def test_passes_profile_text(self):
        mock = _mock_agent()
        jobs = [{"title": "PhD"}]
        self._post({"jobs": jobs, "profile_text": "My profile"}, agent=mock)
        _, profile_arg = mock.score_jobs.call_args[0]
        assert profile_arg == "My profile"

    def test_missing_profile_text_returns_422(self):
        resp = client.post("/api/score-jobs", json={"jobs": []})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /api/prepare
# ---------------------------------------------------------------------------

class TestPrepare:
    def _post(self, payload, agent=None):
        mock = agent or _mock_agent()
        with patch("server._agent", return_value=mock):
            return client.post("/api/prepare", json=payload)

    def test_returns_hints_and_cover_letter(self):
        payload = {
            "job": {"title": "PhD in ML", "institution": "MIT"},
            "profile_text": "Alice, researcher.",
        }
        resp = self._post(payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "hints" in data
        assert "cover_letter" in data

    def test_passes_job_and_profile(self):
        mock = _mock_agent()
        job = {"title": "PhD in ML", "institution": "MIT"}
        self._post({"job": job, "profile_text": "My profile"}, agent=mock)
        mock.prepare_application.assert_called_once_with(job, "My profile")

    def test_missing_job_returns_422(self):
        resp = client.post("/api/prepare", json={"profile_text": "Alice"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /api/regenerate
# ---------------------------------------------------------------------------

class TestRegenerate:
    def _post(self, payload, agent=None):
        mock = agent or _mock_agent()
        with patch("server._agent", return_value=mock):
            return client.post("/api/regenerate", json=payload)

    def test_returns_cover_letter(self):
        payload = {"job": {"title": "PhD"}, "profile_text": "Alice"}
        resp = self._post(payload)
        assert resp.status_code == 200
        assert "cover_letter" in resp.json()
        assert "Updated letter" in resp.json()["cover_letter"]

    def test_passes_job_and_profile(self):
        mock = _mock_agent()
        job = {"title": "Postdoc", "institution": "ETH"}
        self._post({"job": job, "profile_text": "Bob"}, agent=mock)
        mock.regenerate_letter.assert_called_once_with(job, "Bob")


# ---------------------------------------------------------------------------
# /api/export
# ---------------------------------------------------------------------------

_APPROVED = [
    {
        "job": {
            "title": "PhD in Machine Learning",
            "institution": "MIT",
            "location": "USA",
            "type": "phd",
            "source": "test",
            "url": "https://example.com/1",
            "deadline": "30 June 2026",
            "description": "ML research position.",
            "match": {
                "match_score": 85,
                "recommendation": "apply",
                "why_good_fit": "Strong ML background.",
            },
        },
        "cover_letter": "Dear Professor,\n\nI am writing to apply.",
        "notes": "Remember to include reference letter.",
        "approved_at": "2026-03-20T10:00:00",
    }
]


class TestExportZip:
    def test_empty_approved_returns_400(self):
        resp = client.post("/api/export", json={"approved": []})
        assert resp.status_code == 400

    def test_returns_zip_content_type(self):
        resp = client.post("/api/export", json={"approved": _APPROVED})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"

    def test_zip_contains_cover_letter(self):
        resp = client.post("/api/export", json={"approved": _APPROVED})
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = zf.namelist()
        assert any("cover_letter_draft.txt" in n for n in names)

    def test_zip_contains_position_details(self):
        resp = client.post("/api/export", json={"approved": _APPROVED})
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = zf.namelist()
        assert any("position_details.json" in n for n in names)

    def test_zip_contains_notes(self):
        resp = client.post("/api/export", json={"approved": _APPROVED})
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = zf.namelist()
        assert any("my_notes.txt" in n for n in names)

    def test_zip_contains_summary_json(self):
        resp = client.post("/api/export", json={"approved": _APPROVED})
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        assert "summary.json" in zf.namelist()

    def test_summary_json_structure(self):
        resp = client.post("/api/export", json={"approved": _APPROVED})
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        summary = json.loads(zf.read("summary.json"))
        assert isinstance(summary, list)
        assert len(summary) == 1
        assert summary[0]["title"] == "PhD in Machine Learning"
        assert summary[0]["match_score"] == 85

    def test_position_details_json_structure(self):
        resp = client.post("/api/export", json={"approved": _APPROVED})
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        details_name = next(n for n in zf.namelist() if "position_details" in n)
        details = json.loads(zf.read(details_name))
        assert details["title"] == "PhD in Machine Learning"
        assert details["institution"] == "MIT"
        assert details["match_score"] == 85

    def test_cover_letter_content(self):
        resp = client.post("/api/export", json={"approved": _APPROVED})
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        cl_name = next(n for n in zf.namelist() if "cover_letter" in n)
        content = zf.read(cl_name).decode()
        assert "Dear Professor" in content

    def test_safe_filename_strips_special_chars(self):
        """Characters like : / * ? should be removed from folder names."""
        entry = {
            "job": {
                "title": 'PhD: "Machine*Learning?"',
                "institution": "MIT/Lab",
                "match": {},
            },
            "cover_letter": "Test",
        }
        resp = client.post("/api/export", json={"approved": [entry]})
        assert resp.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        # None of the folder names should contain the forbidden chars
        for name in zf.namelist():
            for ch in (':', '*', '?', '"', '/applications/'):
                # forward slash is the path separator in ZipFile — only check
                # that the folder segment itself has no disallowed chars
                pass
            folder = name.split("/")[1] if "/" in name else name
            for ch in (':', '*', '?', '"', '<', '>'):
                assert ch not in folder, f"Char {ch!r} found in folder {folder!r}"

    def test_entry_without_cover_letter_still_exports(self):
        entry = {
            "job": {"title": "Postdoc", "institution": "ETH", "match": {}},
        }
        resp = client.post("/api/export", json={"approved": [entry]})
        assert resp.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        assert any("position_details.json" in n for n in zf.namelist())

    def test_multiple_entries_in_zip(self):
        approved = [
            {"job": {"title": f"Job {i}", "institution": f"Inst {i}",
                     "match": {"match_score": i * 10}},
             "cover_letter": f"Letter {i}"}
            for i in range(3)
        ]
        resp = client.post("/api/export", json={"approved": approved})
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        summary = json.loads(zf.read("summary.json"))
        assert len(summary) == 3


# ---------------------------------------------------------------------------
# /api/parse-cv
# ---------------------------------------------------------------------------

class TestParseCV:
    def test_returns_profile_and_text(self):
        mock = _mock_agent()
        with patch("server._agent", return_value=mock):
            resp = client.post(
                "/api/parse-cv",
                files={"cv": ("cv.txt", b"My research CV content", "text/plain")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "profile" in data
        assert "profile_text" in data

    def test_no_api_key_returns_400(self):
        with patch("server._API_KEY", ""):
            resp = client.post(
                "/api/parse-cv",
                files={"cv": ("cv.txt", b"content", "text/plain")},
            )
        assert resp.status_code == 400

    def test_agent_called_with_temp_file(self):
        mock = _mock_agent()
        with patch("server._agent", return_value=mock):
            client.post(
                "/api/parse-cv",
                files={"cv": ("cv.pdf", b"%PDF fake", "application/pdf")},
            )
        mock.parse_cv.assert_called_once()
        # Verify the temp file path ends with .pdf
        called_path = mock.parse_cv.call_args[0][0]
        assert called_path.endswith(".pdf")
