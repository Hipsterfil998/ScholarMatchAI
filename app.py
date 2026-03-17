"""
Gradio web interface for the Research Job Agent.
Deployable on HuggingFace Spaces (free tier).

LLM: HuggingFace Inference API (free, requires free HF account)
Job sources: Euraxess, FindAPhD, jobs.ac.uk, AcademicPositions, DuckDuckGo
"""

import gradio as gr
import json
import zipfile
import io
import tempfile
import os
from pathlib import Path
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def format_profile_md(profile: dict) -> str:
    """Format CVProfile as Markdown for display."""
    if not profile:
        return "*No profile loaded.*"

    lines: list[str] = []

    name = profile.get("name") or "Unknown"
    lines.append(f"## {name}")

    contact: dict = profile.get("contact") or {}
    if contact.get("email"):
        lines.append(f"**Email:** {contact['email']}")
    if contact.get("linkedin"):
        lines.append(f"**LinkedIn:** {contact['linkedin']}")
    if contact.get("github"):
        lines.append(f"**GitHub:** {contact['github']}")

    if profile.get("summary"):
        lines.append(f"\n**Summary:** {profile['summary']}")

    research = profile.get("research_interests") or []
    if research:
        lines.append("\n**Research Interests:**")
        for interest in research:
            lines.append(f"- {interest}")

    edu = profile.get("education") or []
    if edu:
        lines.append("\n**Education:**")
        for e in edu:
            thesis = f" — *Thesis: {e['thesis_topic']}*" if e.get("thesis_topic") else ""
            lines.append(
                f"- **{e.get('degree', '')}** in {e.get('field', '')} "
                f"— {e.get('institution', '')} ({e.get('year', '')}){thesis}"
            )

    pubs = profile.get("publications") or []
    if pubs:
        lines.append(f"\n**Publications ({len(pubs)} total — first 3):**")
        for p in pubs[:3]:
            lines.append(f"- \"{p.get('title', '')}\" — {p.get('venue', '')} {p.get('year', '')}")

    skills: dict = profile.get("skills") or {}
    prog = skills.get("programming") or []
    tools = skills.get("tools") or []
    lab = skills.get("lab_techniques") or []
    all_skills = prog + tools
    if all_skills:
        lines.append(f"\n**Technical Skills:** {', '.join(all_skills[:20])}")
    if lab:
        lines.append(f"**Lab Techniques:** {', '.join(lab[:10])}")

    return "\n".join(lines)


def format_jobs_table(jobs: list) -> list[list]:
    """Convert jobs list to rows for gr.Dataframe.

    Columns: #, Title, Institution, Location, Type, Source, Deadline
    """
    rows = []
    for i, job in enumerate(jobs, start=1):
        rows.append([
            i,
            job.get("title", ""),
            job.get("institution", job.get("company", "")),
            job.get("location", ""),
            job.get("type", ""),
            job.get("source", ""),
            job.get("deadline") or "—",
        ])
    return rows


def format_scored_table(jobs: list) -> list[list]:
    """Convert scored jobs list to rows for gr.Dataframe.

    Columns: #, Score, Title, Institution, Type, Rec., Why good fit
    """
    rows = []
    for i, job in enumerate(jobs, start=1):
        match: dict = job.get("match") or {}
        why = match.get("why_good_fit") or ""
        why_short = why[:60] + "..." if len(why) > 60 else why
        rec = match.get("recommendation", "")
        rec_icon = {"apply": "✅ apply", "consider": "🟡 consider", "skip": "❌ skip"}.get(rec, rec)
        rows.append([
            i,
            match.get("match_score", 0),
            job.get("title", ""),
            job.get("institution", job.get("company", "")),
            job.get("type", ""),
            rec_icon,
            why_short,
        ])
    return rows


def format_job_details_md(job: dict, match: dict) -> str:
    """Render full position details + match analysis as Markdown."""
    title = job.get("title", "Unknown Position")
    institution = job.get("institution", job.get("company", "Unknown"))
    location = job.get("location", "Unknown")
    pos_type = job.get("type", "")
    source = job.get("source", "")
    url = job.get("url", "")
    deadline = job.get("deadline") or "Not specified"
    description = job.get("description") or ""

    score = match.get("match_score", 0)
    filled = round(score / 10)
    bar = "🟩" * filled + "⬜" * (10 - filled)
    rec = match.get("recommendation", "")
    rec_icon = {"apply": "✅ **Apply**", "consider": "🟡 **Consider**", "skip": "❌ **Skip**"}.get(rec, rec)

    matching_areas = match.get("matching_areas") or []
    missing_reqs = match.get("missing_requirements") or []
    why_good = match.get("why_good_fit") or ""
    concerns = match.get("concerns") or ""

    lines: list[str] = [
        f"## {title}",
        f"**{institution}** — {location}",
        "",
        f"**Type:** {pos_type}  |  **Source:** {source}  |  **Deadline:** {deadline}",
    ]

    if url:
        lines.append(f"**URL:** [{url}]({url})")

    lines += [
        "",
        "---",
        f"### Match Analysis",
        f"**Score:** {score}/100 {bar}",
        f"**Recommendation:** {rec_icon}",
        "",
    ]

    if why_good:
        lines.append(f"**Why a good fit:** {why_good}")
        lines.append("")

    if concerns:
        lines.append(f"**Concerns:** {concerns}")
        lines.append("")

    if matching_areas:
        lines.append("**Matching areas:**")
        for area in matching_areas:
            lines.append(f"- {area}")
        lines.append("")

    if missing_reqs:
        lines.append("**Missing requirements:**")
        for req in missing_reqs:
            lines.append(f"- {req}")
        lines.append("")

    if description:
        lines.append(
            f"\n<details><summary>📄 Full description</summary>\n\n{description}\n\n</details>"
        )

    return "\n".join(lines)


def format_hints_md(hints: dict) -> str:
    """Render TailoringHints as Markdown checklist."""
    if not hints:
        return "*No tailoring hints available.*"

    lines: list[str] = ["### CV Tailoring Hints", ""]

    if hints.get("headline_suggestion"):
        lines += ["**Profile summary tweak:**", f"> {hints['headline_suggestion']}", ""]

    if hints.get("research_alignment"):
        lines += ["**Research alignment:**", f"> {hints['research_alignment']}", ""]

    if hints.get("skills_to_highlight"):
        lines.append("**Skills to highlight:**")
        for skill in hints["skills_to_highlight"]:
            lines.append(f"- [ ] {skill}")
        lines.append("")

    if hints.get("experience_to_emphasize"):
        lines.append("**Experience to highlight:**")
        for exp in hints["experience_to_emphasize"]:
            lines.append(f"- [ ] {exp}")
        lines.append("")

    if hints.get("keywords_to_add"):
        kws = ", ".join(f"`{kw}`" for kw in hints["keywords_to_add"])
        lines += ["**Keywords to add:**", kws, ""]

    if hints.get("suggested_order"):
        lines.append("**Suggested CV section order:**")
        for i, section in enumerate(hints["suggested_order"], 1):
            lines.append(f"{i}. {section}")
        lines.append("")

    return "\n".join(lines)


def make_position_choices(scored_jobs: list) -> list[str]:
    """Build dropdown choices like '[85] MIT — PhD Machine Learning'."""
    choices = []
    for job in scored_jobs:
        match: dict = job.get("match") or {}
        score = match.get("match_score", 0)
        institution = job.get("institution", job.get("company", "Unknown"))
        title = job.get("title", "Unknown")
        choices.append(f"[{score}] {institution} — {title}")
    return choices


# ---------------------------------------------------------------------------
# Main event handler functions
# ---------------------------------------------------------------------------

def run_search(
    cv_file,
    field: str,
    location: str,
    pos_type: str,
    min_score: int,
    hf_token: str,
    model_name: str,
    progress=gr.Progress(track_tqdm=True),
) -> tuple:
    """Parse CV, search job boards, score positions."""

    # Default / error return tuple (9 outputs)
    def _error_return(msg: str) -> tuple:
        return (
            "*Error — see status message.*",  # profile_display
            [],                                # jobs_df
            [],                                # scored_df
            f"❌ {msg}",                       # search_status
            None,                              # profile_state
            "",                               # profile_text_state
            [],                               # jobs_state
            [],                               # scored_state
            gr.update(choices=[], value=None), # position_selector
        )

    # Validate inputs
    if cv_file is None:
        return _error_return("Please upload a CV file first.")
    if not field or not field.strip():
        return _error_return("Please enter a research field.")
    if not hf_token or not hf_token.strip():
        return _error_return("Please provide a HuggingFace API token.")

    try:
        # Configure global config for HuggingFace backend
        from config import config as app_config
        app_config.llm_backend = "huggingface"
        app_config.hf_api_key = hf_token.strip()
        app_config.hf_model = model_name

        # Step 1: Parse CV
        progress(0, desc="Parsing CV...")
        from agent.cv_parser import extract_profile, profile_summary

        cv_path = cv_file if isinstance(cv_file, str) else cv_file.name
        profile = extract_profile(cv_path, model=model_name)
        profile_text = profile_summary(profile)
        profile_md = format_profile_md(profile)

        # Step 2: Search job boards
        progress(0.2, desc="Searching job boards (this takes ~60s)...")
        from agent.job_searcher import search_jobs

        jobs = search_jobs(
            field=field.strip(),
            location=location.strip() if location else "Europe",
            position_type=pos_type if pos_type else "any",
        )

        if not jobs:
            return (
                profile_md,
                [],
                [],
                "⚠️ No positions found. Try a broader field or different location.",
                profile,
                profile_text,
                [],
                [],
                gr.update(choices=[], value=None),
            )

        jobs_df = format_jobs_table(jobs)

        # Step 3: Score positions
        progress(0.6, desc="Scoring positions against your profile...")
        from agent.job_matcher import score_job

        scored_with_all: list[dict] = []
        for i, job in enumerate(jobs):
            frac = 0.6 + 0.38 * (i / max(len(jobs), 1))
            progress(frac, desc=f"Scoring {i+1}/{len(jobs)}: {job.get('title', '')[:40]}...")
            match = score_job(job, profile, profile_text, model=model_name)
            scored_with_all.append({**job, "match": match})

        # Sort highest first
        scored_with_all.sort(key=lambda j: j["match"].get("match_score", 0), reverse=True)

        # Filter by minimum score
        scored = [j for j in scored_with_all if j["match"].get("match_score", 0) >= min_score]

        scored_df = format_scored_table(scored)
        choices = make_position_choices(scored)

        progress(1.0, desc="Done!")

        status = (
            f"✅ Found **{len(jobs)}** positions, "
            f"**{len(scored)}** meet your minimum score of {min_score}."
        )

        return (
            profile_md,
            jobs_df,
            scored_df,
            status,
            profile,
            profile_text,
            jobs,
            scored,
            gr.update(choices=choices, value=None),
        )

    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        return _error_return(f"{exc}\n\nTraceback:\n{tb}")


def load_position_for_review(
    choice: str,
    scored_jobs: list,
    profile: dict,
    profile_text: str,
    hf_token: str,
    model_name: str,
    progress=gr.Progress(),
) -> tuple:
    """Load a selected position: generate tailoring hints and cover letter."""

    if not choice or not scored_jobs:
        return (
            "*No position selected.*",
            "*No hints available.*",
            "",
            "*Select a position and click Load.*",
            -1,
        )

    if not profile:
        return (
            "*Run a search first.*",
            "*Run a search first.*",
            "",
            "❌ No profile found. Please run a search first.",
            -1,
        )

    # Ensure config is set
    from config import config as app_config
    app_config.llm_backend = "huggingface"
    if hf_token:
        app_config.hf_api_key = hf_token.strip()
    if model_name:
        app_config.hf_model = model_name

    # Find position index
    choices = make_position_choices(scored_jobs)
    try:
        idx = choices.index(choice)
    except ValueError:
        idx = 0

    job = scored_jobs[idx]
    match: dict = job.get("match") or {}

    details_md = format_job_details_md(job, match)

    # Generate tailoring hints
    try:
        progress(0.3, desc="Generating CV tailoring hints...")
        from agent.cv_tailor import generate_tailoring_hints

        hints = generate_tailoring_hints(job, profile, profile_text, model=model_name)
        hints_md = format_hints_md(hints)
    except Exception as exc:
        hints_md = f"*Could not generate hints: {exc}*"

    # Generate cover letter
    try:
        progress(0.7, desc="Generating cover letter draft...")
        from agent.cover_letter import generate_cover_letter

        cover_letter = generate_cover_letter(job, profile, profile_text, model=model_name)
    except Exception as exc:
        cover_letter = f"[DRAFT — GENERATION FAILED]\n\nError: {exc}\n\nPlease write your cover letter manually."

    progress(1.0, desc="Done!")

    status_msg = f"✅ Loaded: **{job.get('title', '')}** @ {job.get('institution', job.get('company', ''))}"

    return details_md, hints_md, cover_letter, status_msg, idx


def regenerate_cover_letter(
    current_idx: int,
    scored_jobs: list,
    profile: dict,
    profile_text: str,
    hf_token: str,
    model_name: str,
    progress=gr.Progress(),
) -> str:
    """Regenerate a different version of the cover letter."""

    if current_idx < 0 or not scored_jobs or current_idx >= len(scored_jobs):
        return "*No position loaded. Load a position first.*"

    if not profile:
        return "*No profile found. Run a search first.*"

    from config import config as app_config
    app_config.llm_backend = "huggingface"
    if hf_token:
        app_config.hf_api_key = hf_token.strip()
    if model_name:
        app_config.hf_model = model_name

    job = scored_jobs[current_idx]

    try:
        progress(0.3, desc="Regenerating cover letter...")
        from agent.cover_letter import generate_cover_letter

        cover_letter = generate_cover_letter(
            job, profile, profile_text, model=model_name, regenerate=True
        )
        progress(1.0, desc="Done!")
        return cover_letter
    except Exception as exc:
        return f"[DRAFT — GENERATION FAILED]\n\nError: {exc}\n\nPlease write your cover letter manually."


def approve_position(
    current_idx: int,
    cover_letter_text: str,
    notes: str,
    scored_jobs: list,
    approved: list,
) -> tuple:
    """Save an approved position with its cover letter."""

    if current_idx < 0 or not scored_jobs or current_idx >= len(scored_jobs):
        return approved, "❌ No position loaded. Load a position first."

    job = scored_jobs[current_idx]
    title = job.get("title", "Unknown")
    institution = job.get("institution", job.get("company", "Unknown"))

    # Check for duplicates
    existing_keys = {(a["job"].get("title", ""), a["job"].get("institution", "")) for a in approved}
    if (title, institution) in existing_keys:
        return approved, f"⚠️ **{title}** @ {institution} is already approved."

    new_approved = list(approved) + [{
        "job": job,
        "cover_letter": cover_letter_text,
        "notes": notes or "",
        "approved_at": datetime.now().isoformat(),
    }]

    status = f"✅ Approved: **{title}** @ {institution} ({len(new_approved)} total approved)"
    return new_approved, status


def skip_position(
    current_idx: int,
    scored_jobs: list,
) -> str:
    """Skip the current position."""

    if current_idx < 0 or not scored_jobs or current_idx >= len(scored_jobs):
        return "⏭ Skipped. (No position was loaded.)"

    job = scored_jobs[current_idx]
    title = job.get("title", "Unknown")
    institution = job.get("institution", job.get("company", "Unknown"))
    return f"⏭ Skipped: **{title}** @ {institution}"


def update_approved_display(approved: list) -> str:
    """Build a Markdown table of all approved positions."""

    if not approved:
        return "*No applications approved yet.*"

    lines: list[str] = [
        f"### Approved Applications ({len(approved)})",
        "",
        "| # | Title | Institution | Approved At |",
        "|---|-------|-------------|-------------|",
    ]

    for i, entry in enumerate(approved, start=1):
        job = entry.get("job") or {}
        title = job.get("title", "Unknown")
        institution = job.get("institution", job.get("company", "Unknown"))
        approved_at = entry.get("approved_at", "")
        if approved_at:
            try:
                dt = datetime.fromisoformat(approved_at)
                approved_at = dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                pass
        lines.append(f"| {i} | {title} | {institution} | {approved_at} |")

    return "\n".join(lines)


def export_zip(approved: list) -> tuple:
    """Create a ZIP archive of all approved applications."""

    if not approved:
        return None, "⚠️ No approved applications to export."

    try:
        tmp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(tmp_dir, "applications.zip")

        summary_data: list[dict] = []

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for entry in approved:
                job = entry.get("job") or {}
                cover_letter = entry.get("cover_letter") or ""
                notes = entry.get("notes") or ""
                approved_at = entry.get("approved_at") or ""

                title = job.get("title", "Unknown")
                institution = job.get("institution", job.get("company", "Unknown"))

                # Build a safe directory name
                safe_name = (
                    f"{institution}_{title}"
                    .replace(" ", "_")
                    .replace("/", "-")
                    .replace("\\", "-")
                    .replace(":", "-")
                    .replace("*", "")
                    .replace("?", "")
                    .replace('"', "")
                    .replace("<", "")
                    .replace(">", "")
                    .replace("|", "")
                )
                # Truncate to reasonable length
                safe_name = safe_name[:80]
                dir_name = f"applications/{safe_name}"

                # Cover letter
                if cover_letter:
                    zf.writestr(f"{dir_name}/cover_letter_draft.txt", cover_letter)

                # Position details JSON
                match: dict = job.get("match") or {}
                position_info = {
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
                    "concerns": match.get("concerns", ""),
                }
                zf.writestr(
                    f"{dir_name}/position_details.json",
                    json.dumps(position_info, indent=2, ensure_ascii=False),
                )

                # Notes / tailoring hints as plain text
                if notes:
                    zf.writestr(f"{dir_name}/my_notes.txt", notes)

                summary_data.append({
                    "title": title,
                    "institution": institution,
                    "match_score": match.get("match_score", 0),
                    "recommendation": match.get("recommendation", ""),
                    "approved_at": approved_at,
                    "url": job.get("url", ""),
                })

            # Summary JSON at root of ZIP
            zf.writestr(
                "summary.json",
                json.dumps(summary_data, indent=2, ensure_ascii=False),
            )

        return zip_path, f"✅ ZIP created with {len(approved)} application(s). Click the file below to download."

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

with gr.Blocks(
    theme=gr.themes.Soft(primary_hue="blue", secondary_hue="purple"),
    title="Research Job Agent",
) as demo:
    # ---- State ----
    profile_state = gr.State(None)
    profile_text_state = gr.State("")
    jobs_state = gr.State([])
    scored_state = gr.State([])
    approved_state = gr.State([])
    current_idx_state = gr.State(-1)

    # ---- Header ----
    gr.Markdown("""
    # Research Job Agent
    *AI-powered search for PhD positions, postdocs, and research fellowships*

    Searches **Euraxess**, **FindAPhD**, **jobs.ac.uk**, **Academic Positions** and the web.
    Powered by free HuggingFace models — no paid subscription required.
    """)

    with gr.Tabs() as tabs:
        # ========== TAB 1: SETUP ==========
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
                        value="",
                    )
                    location_input = gr.Textbox(
                        label="Location preference",
                        placeholder="e.g. Europe, Germany, UK, Italy",
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
                            minimum=30,
                            maximum=90,
                            value=60,
                            step=5,
                        )
                with gr.Column(scale=1):
                    gr.Markdown("### LLM Settings")
                    hf_token = gr.Textbox(
                        label="HuggingFace API Token",
                        placeholder="hf_...",
                        type="password",
                        info="Free token from huggingface.co/settings/tokens",
                    )
                    model_dropdown = gr.Dropdown(
                        label="Model",
                        choices=MODELS,
                        value=MODELS[0],
                        info="All are free via HF Inference API",
                    )
                    gr.Markdown("""
                    **Get a free HF token:**
                    1. Sign up at [huggingface.co](https://huggingface.co)
                    2. Go to Settings → Access Tokens
                    3. Create a new token (read access is enough)
                    """)

            search_btn = gr.Button("Parse CV & Search Positions", variant="primary", size="lg")
            search_status = gr.Markdown("*Ready. Fill in the form and click Search.*")

        # ========== TAB 2: RESULTS ==========
        with gr.Tab("Results", id=1):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Your CV Profile")
                    profile_display = gr.Markdown("*Run a search first.*")
                with gr.Column(scale=2):
                    gr.Markdown("### Positions Found")
                    jobs_df = gr.Dataframe(
                        headers=["#", "Title", "Institution", "Location", "Type", "Source", "Deadline"],
                        label="All found positions",
                        wrap=True,
                        interactive=False,
                    )

            gr.Markdown("### Qualifying Positions (above minimum score)")
            scored_df = gr.Dataframe(
                headers=["#", "Score", "Title", "Institution", "Type", "Rec.", "Why good fit"],
                label="Scored positions",
                wrap=True,
                interactive=False,
            )
            go_review_btn = gr.Button("Go to Review", variant="secondary")

        # ========== TAB 3: REVIEW ==========
        with gr.Tab("Review & Edit", id=2):
            gr.Markdown("### Review positions and edit cover letters")

            with gr.Row():
                position_selector = gr.Dropdown(
                    label="Select position to review",
                    choices=[],
                    value=None,
                    info="Positions sorted by match score (highest first)",
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
            gr.Markdown("*Edit the cover letter below before approving. The header `DRAFT —` line will be included — remove it before sending.*")

            cover_letter_box = gr.Textbox(
                label="Cover letter (editable)",
                lines=20,
                max_lines=40,
                interactive=True,
                placeholder="Cover letter will be generated here...",
            )

            notes_box = gr.Textbox(
                label="Your notes (optional)",
                placeholder="Personal notes about this application...",
                lines=2,
            )

            with gr.Row():
                approve_btn = gr.Button("Approve & Save", variant="primary")
                regen_btn = gr.Button("Regenerate Letter", variant="secondary")
                skip_btn = gr.Button("Skip", variant="stop")

            approve_status = gr.Markdown("")

        # ========== TAB 4: EXPORT ==========
        with gr.Tab("Export", id=3):
            gr.Markdown("### Your approved applications")
            approved_display = gr.Markdown("*No applications approved yet.*")

            with gr.Row():
                refresh_btn = gr.Button("Refresh list")
                export_btn = gr.Button("Download as ZIP", variant="primary")

            download_file = gr.File(label="Download", visible=False)
            export_status = gr.Markdown("")

    # ---- Event handlers ----

    # Search button
    search_btn.click(
        fn=run_search,
        inputs=[cv_file, field_input, location_input, pos_type, min_score, hf_token, model_dropdown],
        outputs=[
            profile_display,
            jobs_df,
            scored_df,
            search_status,
            profile_state,
            profile_text_state,
            jobs_state,
            scored_state,
            position_selector,
        ],
    )

    # Go to review button
    go_review_btn.click(fn=lambda: gr.update(selected=2), outputs=tabs)

    # Load position
    load_btn.click(
        fn=load_position_for_review,
        inputs=[position_selector, scored_state, profile_state, profile_text_state, hf_token, model_dropdown],
        outputs=[position_details_display, hints_display, cover_letter_box, review_status, current_idx_state],
    )

    # Regenerate cover letter
    regen_btn.click(
        fn=regenerate_cover_letter,
        inputs=[current_idx_state, scored_state, profile_state, profile_text_state, hf_token, model_dropdown],
        outputs=[cover_letter_box],
    )

    # Approve position
    approve_btn.click(
        fn=approve_position,
        inputs=[current_idx_state, cover_letter_box, notes_box, scored_state, approved_state],
        outputs=[approved_state, approve_status],
    )

    # Skip position
    skip_btn.click(
        fn=skip_position,
        inputs=[current_idx_state, scored_state],
        outputs=[approve_status],
    )

    # Refresh approved list
    refresh_btn.click(
        fn=update_approved_display,
        inputs=[approved_state],
        outputs=[approved_display],
    )

    # Export ZIP
    export_btn.click(
        fn=export_zip,
        inputs=[approved_state],
        outputs=[download_file, export_status],
    ).then(
        fn=lambda f: gr.update(visible=f is not None),
        inputs=[download_file],
        outputs=[download_file],
    )


if __name__ == "__main__":
    demo.launch()
