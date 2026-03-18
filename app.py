"""Gradio web interface for the Research Job Agent.

Deployable on HuggingFace Spaces (free tier).
LLM: HuggingFace Inference API (requires a free HF account).
Job sources: Euraxess, FindAPhD, jobs.ac.uk, Academic Positions, DuckDuckGo.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import zipfile
from datetime import datetime
from typing import Any

import gradio as gr


# ---------------------------------------------------------------------------
# Formatting helpers  (pure functions — no LLM dependency)
# ---------------------------------------------------------------------------

def _fmt_profile(profile: dict) -> str:
    if not profile:
        return "*No profile loaded.*"
    lines: list[str] = [f"## {profile.get('name') or 'Unknown'}"]
    contact: dict = profile.get("contact") or {}
    for key, label in [("email", "Email"), ("linkedin", "LinkedIn"), ("github", "GitHub")]:
        if contact.get(key):
            lines.append(f"**{label}:** {contact[key]}")
    if profile.get("summary"):
        lines.append(f"\n**Summary:** {profile['summary']}")
    for interest in (profile.get("research_interests") or []):
        lines.append(f"- {interest}")
    for e in (profile.get("education") or []):
        thesis = f" — *Thesis: {e['thesis_topic']}*" if e.get("thesis_topic") else ""
        lines.append(
            f"- **{e.get('degree', '')}** in {e.get('field', '')} "
            f"— {e.get('institution', '')} ({e.get('year', '')}){thesis}"
        )
    pubs = profile.get("publications") or []
    if pubs:
        lines.append(f"\n**Publications ({len(pubs)} — first 3):**")
        for p in pubs[:3]:
            lines.append(f"- \"{p.get('title', '')}\" — {p.get('venue', '')} {p.get('year', '')}")
    skills: dict = profile.get("skills") or {}
    all_skills = (skills.get("programming") or []) + (skills.get("tools") or [])
    if all_skills:
        lines.append(f"\n**Technical Skills:** {', '.join(all_skills[:20])}")
    return "\n".join(lines)


def _fmt_jobs_table(jobs: list) -> list[list]:
    return [
        [i, j.get("title", ""), j.get("institution", j.get("company", "")),
         j.get("location", ""), j.get("type", ""), j.get("source", ""),
         j.get("deadline") or "—"]
        for i, j in enumerate(jobs, 1)
    ]


def _fmt_scored_table(jobs: list) -> list[list]:
    icons = {"apply": "✅ apply", "consider": "🟡 consider", "skip": "❌ skip"}
    rows = []
    for i, job in enumerate(jobs, 1):
        m: dict = job.get("match") or {}
        why = m.get("why_good_fit") or ""
        rows.append([
            i, m.get("match_score", 0), job.get("title", ""),
            job.get("institution", job.get("company", "")), job.get("type", ""),
            icons.get(m.get("recommendation", ""), ""),
            why[:60] + "..." if len(why) > 60 else why,
        ])
    return rows


def _fmt_job_details(job: dict, match: dict) -> str:
    score = match.get("match_score", 0)
    bar = "🟩" * round(score / 10) + "⬜" * (10 - round(score / 10))
    rec = match.get("recommendation", "")
    rec_icon = {"apply": "✅ **Apply**", "consider": "🟡 **Consider**", "skip": "❌ **Skip**"}.get(rec, rec)
    url = job.get("url", "")
    lines = [
        f"## {job.get('title', 'Unknown')}",
        f"**{job.get('institution', job.get('company', 'Unknown'))}** — {job.get('location', '')}",
        "",
        f"**Type:** {job.get('type', '')}  |  **Deadline:** {job.get('deadline') or 'N/A'}",
    ]
    if url:
        lines.append(f"**URL:** [{url}]({url})")
    lines += [
        "", "---", "### Match Analysis",
        f"**Score:** {score}/100 {bar}",
        f"**Recommendation:** {rec_icon}", "",
    ]
    if match.get("why_good_fit"):
        lines += [f"**Why a good fit:** {match['why_good_fit']}", ""]
    if match.get("concerns"):
        lines += [f"**Concerns:** {match['concerns']}", ""]
    if match.get("matching_areas"):
        lines.append("**Matching areas:**")
        lines += [f"- {a}" for a in match["matching_areas"]]
    if match.get("missing_requirements"):
        lines.append("**Missing requirements:**")
        lines += [f"- {r}" for r in match["missing_requirements"]]
    if job.get("description"):
        lines.append(f"\n<details><summary>📄 Full description</summary>\n\n{job['description']}\n\n</details>")
    return "\n".join(lines)


def _fmt_hints(hints: dict) -> str:
    if not hints:
        return "*No tailoring hints available.*"
    lines = ["### CV Tailoring Hints", ""]
    if hints.get("headline_suggestion"):
        lines += ["**Profile summary tweak:**", f"> {hints['headline_suggestion']}", ""]
    if hints.get("research_alignment"):
        lines += ["**Research alignment:**", f"> {hints['research_alignment']}", ""]
    if hints.get("skills_to_highlight"):
        lines.append("**Skills to highlight:**")
        lines += [f"- [ ] {s}" for s in hints["skills_to_highlight"]]
        lines.append("")
    if hints.get("experience_to_emphasize"):
        lines.append("**Experience to highlight:**")
        lines += [f"- [ ] {e}" for e in hints["experience_to_emphasize"]]
        lines.append("")
    if hints.get("keywords_to_add"):
        lines += ["**Keywords to add:**", ", ".join(f"`{k}`" for k in hints["keywords_to_add"]), ""]
    if hints.get("suggested_order"):
        lines.append("**Suggested section order:**")
        lines += [f"{i}. {s}" for i, s in enumerate(hints["suggested_order"], 1)]
    return "\n".join(lines)


def _position_choices(scored_jobs: list) -> list[str]:
    return [
        f"[{(j.get('match') or {}).get('match_score', 0)}] "
        f"{j.get('institution', j.get('company', 'Unknown'))} — {j.get('title', 'Unknown')}"
        for j in scored_jobs
    ]


# ---------------------------------------------------------------------------
# Gradio event handlers
# ---------------------------------------------------------------------------

def run_search(
    cv_file,
    field: str,
    location: str,
    pos_type: str,
    min_score: int,
    model_name: str,
    progress=gr.Progress(track_tqdm=True),
) -> tuple:
    """Parse CV, search job boards, score positions. Returns 9 outputs."""

    def _err(msg: str) -> tuple:
        return (
            "*Error — see status message.*", [], [], f"❌ {msg}",
            None, "", [], [], gr.update(choices=[], value=None),
        )

    if cv_file is None:
        return _err("Please upload a CV file first.")
    if not field or not field.strip():
        return _err("Please enter a research field.")
    if not _SHARED_TOKEN:
        return _err("No HF_TOKEN configured. Set it as a Space secret.")

    try:
        from agent.pipeline import JobAgent

        agent = JobAgent(token=_SHARED_TOKEN, model=model_name)
        cv_path = cv_file if isinstance(cv_file, str) else cv_file.name

        progress(0, desc="Parsing CV...")
        profile, profile_text = agent.parse_cv(cv_path)

        progress(0.2, desc="Searching job boards (~60s)...")
        jobs = agent.search_jobs(
            field=field.strip(),
            location=location.strip() or "Europe",
            position_type=pos_type or "any",
        )

        if not jobs:
            return (
                _fmt_profile(profile), [], [], "⚠️ No positions found.",
                profile, profile_text, [], [], gr.update(choices=[], value=None),
            )

        progress(0.6, desc="Scoring positions...")
        scored = agent.score_jobs(jobs, profile_text, min_score)

        progress(1.0, desc="Done!")
        status = (
            f"✅ Found **{len(jobs)}** positions, "
            f"**{len(scored)}** meet your minimum score of {min_score}."
        )
        return (
            _fmt_profile(profile),
            _fmt_jobs_table(jobs),
            _fmt_scored_table(scored),
            status,
            profile,
            profile_text,
            jobs,
            scored,
            gr.update(choices=_position_choices(scored), value=None),
        )

    except Exception as exc:
        import traceback
        return _err(f"{exc}\n\n{traceback.format_exc()}")


def load_position(
    choice: str,
    scored_jobs: list,
    profile_text: str,
    model_name: str,
    progress=gr.Progress(),
) -> tuple:
    """Generate tailoring hints and cover letter for a selected position. Returns 5 outputs."""
    if not choice or not scored_jobs:
        return "*No position selected.*", "*No hints.*", "", "*Select a position and click Load.*", -1
    if not profile_text:
        return "*Run a search first.*", "*Run a search first.*", "", "❌ No profile found.", -1

    try:
        choices = _position_choices(scored_jobs)
        idx = choices.index(choice) if choice in choices else 0
        job = scored_jobs[idx]
        match: dict = job.get("match") or {}

        from agent.pipeline import JobAgent
        agent = JobAgent(token=_SHARED_TOKEN, model=model_name)

        progress(0.3, desc="Generating tailoring hints...")
        hints, cover_letter = agent.prepare_application(job, profile_text)

        progress(1.0, desc="Done!")
        status = f"✅ Loaded: **{job.get('title', '')}** @ {job.get('institution', job.get('company', ''))}"
        return _fmt_job_details(job, match), _fmt_hints(hints), cover_letter, status, idx

    except Exception as exc:
        return f"*Error: {exc}*", "*Error.*", "", f"❌ {exc}", -1


def regenerate_letter(
    current_idx: int,
    scored_jobs: list,
    profile_text: str,
    model_name: str,
    progress=gr.Progress(),
) -> str:
    if current_idx < 0 or not scored_jobs or current_idx >= len(scored_jobs):
        return "*No position loaded.*"
    try:
        from agent.pipeline import JobAgent
        agent = JobAgent(token=_SHARED_TOKEN, model=model_name)
        progress(0.3, desc="Regenerating cover letter...")
        result = agent.regenerate_letter(scored_jobs[current_idx], profile_text)
        progress(1.0)
        return result
    except Exception as exc:
        return f"[DRAFT — GENERATION FAILED]\n\nError: {exc}"


def approve_position(
    current_idx: int,
    cover_letter_text: str,
    notes: str,
    scored_jobs: list,
    approved: list,
) -> tuple:
    if current_idx < 0 or not scored_jobs or current_idx >= len(scored_jobs):
        return approved, "❌ No position loaded."
    job = scored_jobs[current_idx]
    title, institution = job.get("title", "Unknown"), job.get("institution", job.get("company", "Unknown"))
    if any(a["job"].get("title") == title and a["job"].get("institution") == institution for a in approved):
        return approved, f"⚠️ **{title}** @ {institution} already approved."
    new_approved = list(approved) + [{
        "job": job, "cover_letter": cover_letter_text,
        "notes": notes or "", "approved_at": datetime.now().isoformat(),
    }]
    return new_approved, f"✅ Approved: **{title}** @ {institution} ({len(new_approved)} total)"


def skip_position(current_idx: int, scored_jobs: list) -> str:
    if current_idx < 0 or not scored_jobs or current_idx >= len(scored_jobs):
        return "⏭ Skipped."
    job = scored_jobs[current_idx]
    return f"⏭ Skipped: **{job.get('title', '')}** @ {job.get('institution', job.get('company', ''))}"


def approved_display(approved: list) -> str:
    if not approved:
        return "*No applications approved yet.*"
    lines = [f"### Approved Applications ({len(approved)})", "",
             "| # | Title | Institution | Approved At |",
             "|---|-------|-------------|-------------|"]
    for i, entry in enumerate(approved, 1):
        job = entry.get("job") or {}
        ts = entry.get("approved_at", "")
        try:
            ts = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            pass
        lines.append(f"| {i} | {job.get('title', '')} | {job.get('institution', '')} | {ts} |")
    return "\n".join(lines)


def export_zip(approved: list) -> tuple:
    if not approved:
        return None, "⚠️ No approved applications to export."
    try:
        tmp = tempfile.mkdtemp()
        zip_path = os.path.join(tmp, "applications.zip")
        summary = []
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for entry in approved:
                job = entry.get("job") or {}
                title = job.get("title", "Unknown")
                institution = job.get("institution", job.get("company", "Unknown"))
                safe = (
                    f"{institution}_{title}"
                    .replace(" ", "_").replace("/", "-").replace("\\", "-")
                    .replace(":", "-").replace("*", "").replace("?", "")
                    .replace('"', "").replace("<", "").replace(">", "").replace("|", "")
                )[:80]
                d = f"applications/{safe}"
                if entry.get("cover_letter"):
                    zf.writestr(f"{d}/cover_letter_draft.txt", entry["cover_letter"])
                if entry.get("notes"):
                    zf.writestr(f"{d}/my_notes.txt", entry["notes"])
                match: dict = job.get("match") or {}
                zf.writestr(f"{d}/position_details.json", json.dumps({
                    "title": title, "institution": institution,
                    "location": job.get("location", ""), "type": job.get("type", ""),
                    "source": job.get("source", ""), "url": job.get("url", ""),
                    "deadline": job.get("deadline"), "description": job.get("description", ""),
                    "match_score": match.get("match_score", 0),
                    "recommendation": match.get("recommendation", ""),
                    "why_good_fit": match.get("why_good_fit", ""),
                }, indent=2, ensure_ascii=False))
                summary.append({
                    "title": title, "institution": institution,
                    "match_score": match.get("match_score", 0),
                    "url": job.get("url", ""),
                    "approved_at": entry.get("approved_at", ""),
                })
            zf.writestr("summary.json", json.dumps(summary, indent=2, ensure_ascii=False))
        return zip_path, f"✅ ZIP created with {len(approved)} application(s)."
    except Exception as exc:
        return None, f"❌ Export failed: {exc}"


# ---------------------------------------------------------------------------
# Gradio Blocks layout
# ---------------------------------------------------------------------------

MODELS = [
    "mistralai/Mistral-7B-Instruct-v0.3",
    "HuggingFaceH4/zephyr-7b-beta",
    "Qwen/Qwen2.5-7B-Instruct",
    "microsoft/Phi-3-mini-4k-instruct",
]

# If a shared token is configured via Space Secrets, users don't need to provide one.
_SHARED_TOKEN = os.environ.get("HF_TOKEN", "")

with gr.Blocks(
    theme=gr.themes.Soft(primary_hue="blue", secondary_hue="purple"),
    title="Research Job Agent",
) as demo:
    # ---- Session state ----
    profile_state = gr.State(None)
    profile_text_state = gr.State("")
    jobs_state = gr.State([])
    scored_state = gr.State([])
    approved_state = gr.State([])
    current_idx_state = gr.State(-1)

    gr.Markdown("""
    # Research Job Agent 🎓
    *AI-powered search for PhD positions, postdocs, and research fellowships*

    Searches **Euraxess**, **FindAPhD**, **jobs.ac.uk**, **Academic Positions** and the web.
    Powered by free HuggingFace models — no paid subscription required.
    """)

    with gr.Tabs() as tabs:

        # ── Tab 1: Setup ──────────────────────────────────────────────────
        with gr.Tab("Setup & Search", id=0):
            gr.Markdown("### 1. Configure your search")
            with gr.Row():
                with gr.Column(scale=2):
                    cv_file = gr.File(
                        label="Upload your CV",
                        file_types=[".pdf", ".docx", ".txt"],
                        type="filepath",
                    )
                    field_input = gr.Textbox(
                        label="Research field",
                        placeholder="e.g. machine learning, computational neuroscience, molecular biology",
                    )
                    location_input = gr.Textbox(
                        label="Location preference",
                        placeholder="e.g. Europe, Germany, UK",
                        value="Europe",
                    )
                    with gr.Row():
                        pos_type = gr.Dropdown(
                            label="Position type",
                            choices=["any", "phd", "postdoc", "fellowship", "research_staff"],
                            value="any",
                        )
                        min_score = gr.Slider(
                            label="Minimum match score",
                            minimum=30, maximum=90, value=60, step=5,
                        )
                with gr.Column(scale=1):
                    gr.Markdown("### LLM Settings")
                    model_dropdown = gr.Dropdown(
                        label="Model",
                        choices=MODELS,
                        value=MODELS[0],
                        info="All are free via HF Inference API",
                    )
            search_btn = gr.Button("Parse CV & Search Positions", variant="primary", size="lg")
            search_status = gr.Markdown("*Ready. Fill in the form and click Search.*")

        # ── Tab 2: Results ────────────────────────────────────────────────
        with gr.Tab("Results", id=1):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Your CV Profile")
                    profile_display = gr.Markdown("*Run a search first.*")
                with gr.Column(scale=2):
                    gr.Markdown("### Positions Found")
                    jobs_df = gr.Dataframe(
                        headers=["#", "Title", "Institution", "Location", "Type", "Source", "Deadline"],
                        interactive=False, wrap=True,
                    )
            gr.Markdown("### Qualifying Positions (above minimum score)")
            scored_df = gr.Dataframe(
                headers=["#", "Score", "Title", "Institution", "Type", "Rec.", "Why good fit"],
                interactive=False, wrap=True,
            )
            go_review_btn = gr.Button("Go to Review →", variant="secondary")

        # ── Tab 3: Review ─────────────────────────────────────────────────
        with gr.Tab("Review & Edit", id=2):
            gr.Markdown("### Review positions and edit cover letters")
            with gr.Row():
                position_selector = gr.Dropdown(
                    label="Select position to review",
                    choices=[], value=None,
                    info="Sorted by match score (highest first)",
                    scale=3,
                )
                load_btn = gr.Button("Load Position", variant="primary", scale=1)
            review_status = gr.Markdown("*Select a position and click Load.*")
            with gr.Row():
                with gr.Column(scale=1):
                    position_details_display = gr.Markdown("*Position details will appear here.*")
                with gr.Column(scale=1):
                    hints_display = gr.Markdown("*CV tailoring hints will appear here.*")
            gr.Markdown("### Cover Letter Draft")
            gr.Markdown("*Edit below before approving. Remove the DRAFT header before sending.*")
            cover_letter_box = gr.Textbox(
                label="Cover letter (editable)",
                lines=20, max_lines=40, interactive=True,
                placeholder="Cover letter will be generated here...",
            )
            notes_box = gr.Textbox(
                label="Your notes (optional)",
                placeholder="Personal notes about this application...",
                lines=2,
            )
            with gr.Row():
                approve_btn = gr.Button("✅ Approve & Save", variant="primary")
                regen_btn = gr.Button("🔄 Regenerate Letter", variant="secondary")
                skip_btn = gr.Button("⏭ Skip", variant="stop")
            approve_status = gr.Markdown("")

        # ── Tab 4: Export ─────────────────────────────────────────────────
        with gr.Tab("Export", id=3):
            gr.Markdown("### Your approved applications")
            approved_md = gr.Markdown("*No applications approved yet.*")
            with gr.Row():
                refresh_btn = gr.Button("Refresh list")
                export_btn = gr.Button("Download as ZIP", variant="primary")
            download_file = gr.File(label="Download", visible=False)
            export_status = gr.Markdown("")

    # ── Event wiring ──────────────────────────────────────────────────────

    search_btn.click(
        fn=run_search,
        inputs=[cv_file, field_input, location_input, pos_type, min_score, model_dropdown],
        outputs=[profile_display, jobs_df, scored_df, search_status,
                 profile_state, profile_text_state, jobs_state, scored_state, position_selector],
    )

    go_review_btn.click(fn=lambda: gr.update(selected=2), outputs=tabs)

    load_btn.click(
        fn=load_position,
        inputs=[position_selector, scored_state, profile_text_state, model_dropdown],
        outputs=[position_details_display, hints_display, cover_letter_box,
                 review_status, current_idx_state],
    )

    regen_btn.click(
        fn=regenerate_letter,
        inputs=[current_idx_state, scored_state, profile_text_state, model_dropdown],
        outputs=[cover_letter_box],
    )

    approve_btn.click(
        fn=approve_position,
        inputs=[current_idx_state, cover_letter_box, notes_box, scored_state, approved_state],
        outputs=[approved_state, approve_status],
    )

    skip_btn.click(
        fn=skip_position,
        inputs=[current_idx_state, scored_state],
        outputs=[approve_status],
    )

    refresh_btn.click(
        fn=approved_display,
        inputs=[approved_state],
        outputs=[approved_md],
    )

    export_btn.click(
        fn=export_zip,
        inputs=[approved_state],
        outputs=[download_file, export_status],
    ).then(
        fn=lambda f: gr.update(visible=f is not None),
        inputs=[download_file],
        outputs=[download_file],
    )


demo.launch(server_name="0.0.0.0")
