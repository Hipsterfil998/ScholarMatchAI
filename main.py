"""Main CLI entry point for the PhD/Research Job Agent.

Usage examples:
  python main.py --cv cv.pdf --field "machine learning" --location "Europe"
  python main.py --cv cv.pdf --field "molecular biology" --type phd --min-score 70
  python main.py --cv cv.pdf --field "NLP" --model mistral:7b --no-interactive
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from agent.utils import sanitize_filename
from config import config

console = Console()


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def _print_banner() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]Research Job Agent[/bold cyan]\n"
            "[dim]AI-powered PhD / postdoc / fellowship search\n"
            "Powered by Ollama (local LLM) — no API keys required[/dim]",
            border_style="cyan",
        )
    )


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _print_cv_profile(profile: dict[str, Any]) -> None:
    """Display the parsed CV profile in a formatted panel."""
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    table.add_row("Name", profile.get("name") or "N/A")

    contact: dict = profile.get("contact") or {}
    table.add_row("Email", contact.get("email") or "N/A")

    research = profile.get("research_interests") or []
    table.add_row(
        "Research interests",
        ", ".join(research[:6]) + (f" (+{len(research)-6} more)" if len(research) > 6 else "")
        if research else "N/A",
    )

    pubs = profile.get("publications") or []
    table.add_row("Publications", str(len(pubs)))

    edu = profile.get("education") or []
    if edu:
        latest = edu[0]
        thesis = f" — {latest['thesis_topic']}" if latest.get("thesis_topic") else ""
        table.add_row(
            "Highest degree",
            f"{latest.get('degree', '')} in {latest.get('field', '')} "
            f"({latest.get('institution', '')}){thesis}",
        )

    skills: dict = profile.get("skills") or {}
    prog = (skills.get("programming") or [])[:8]
    if prog:
        table.add_row("Programming", ", ".join(prog))

    awards = profile.get("awards") or []
    if awards:
        table.add_row("Awards", "; ".join(awards[:3]))

    console.print(Panel(table, title="[bold]Parsed CV Profile[/bold]", border_style="green"))


def _print_jobs_table(jobs: list[dict[str, Any]]) -> None:
    """Display found positions in a table."""
    table = Table(
        title=f"[bold]Found {len(jobs)} Research Positions[/bold]",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="bold white", max_width=30)
    table.add_column("Institution", style="cyan", max_width=25)
    table.add_column("Location", style="green", max_width=18)
    table.add_column("Type", style="magenta", max_width=12)
    table.add_column("Source", style="dim", max_width=16)

    for i, job in enumerate(jobs, start=1):
        table.add_row(
            str(i),
            job.get("title") or "N/A",
            job.get("institution", job.get("company", "N/A")),
            job.get("location") or "N/A",
            job.get("type") or "N/A",
            job.get("source") or "N/A",
        )
    console.print(table)


def _score_color(score: int) -> str:
    if score >= 80:
        return "green"
    elif score >= 60:
        return "yellow"
    return "red"


def _print_scored_table(jobs: list[dict[str, Any]]) -> None:
    """Display scored positions with match details."""
    table = Table(
        title=f"[bold]Scored Positions — {len(jobs)} qualifying[/bold]",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Score", width=7)
    table.add_column("Title", style="bold white", max_width=28)
    table.add_column("Institution", style="cyan", max_width=22)
    table.add_column("Rec.", max_width=10)
    table.add_column("Why good fit", style="dim", max_width=40)

    rec_colors = {"apply": "green", "consider": "yellow", "skip": "red"}

    for i, job in enumerate(jobs, start=1):
        match = job.get("match") or {}
        score = match.get("match_score", 0)
        rec = match.get("recommendation", "")
        why = match.get("why_good_fit") or ""
        c = _score_color(score)
        rc = rec_colors.get(rec, "white")

        table.add_row(
            str(i),
            f"[{c}]{score}[/{c}]",
            job.get("title") or "N/A",
            job.get("institution", job.get("company", "N/A")),
            f"[{rc}]{rec}[/{rc}]",
            (why[:60] + "…") if len(why) > 60 else why,
        )

    console.print(table)


def _print_final_summary(
    approved: list[dict[str, Any]],
    skipped: int,
    output_path: Path,
) -> None:
    """Print the final summary table."""
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold white")
    table.add_row("Approved applications", str(len(approved)))
    table.add_row("Skipped", str(skipped))
    table.add_row("Output directory", str(output_path))

    console.print(Panel(table, title="[bold]Session Summary[/bold]", border_style="cyan"))

    if approved:
        console.print("\n[bold]Approved positions:[/bold]")
        for item in approved:
            console.print(
                f"  [green]✓[/green] {item['title']} @ {item['institution']}  "
                f"(score: {item['score']})"
            )


# ---------------------------------------------------------------------------
# File saving helpers
# ---------------------------------------------------------------------------

def _save_application(
    job: dict[str, Any],
    match: dict[str, Any],
    tailoring_hints: dict[str, Any],
    cover_letter: str,
    notes: str,
    output_path: Path,
) -> Path:
    """Save all application materials to a dedicated subdirectory.

    Returns the path to the created directory.
    """
    from agent.cv.tailor import format_hints_text  # noqa: PLC0415

    institution = sanitize_filename(job.get("institution", job.get("company", "Unknown")), maxlen=40)
    title = sanitize_filename(job.get("title", "Position"), maxlen=40)
    dir_name = f"{institution}_{title}"
    app_dir = output_path / "applications" / dir_name
    app_dir.mkdir(parents=True, exist_ok=True)

    # cover_letter_draft.txt
    (app_dir / "cover_letter_draft.txt").write_text(cover_letter, encoding="utf-8")

    # tailoring_hints.txt
    hints_text = format_hints_text(tailoring_hints)
    (app_dir / "tailoring_hints.txt").write_text(hints_text, encoding="utf-8")

    # position_details.json — full listing + match score
    details = {
        "position": job,
        "match": match,
        "saved_at": datetime.now().isoformat(),
        "notes": notes,
    }
    (app_dir / "position_details.json").write_text(
        json.dumps(details, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return app_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option(
    "--cv",
    "cv_path",
    required=True,
    type=click.Path(exists=True),
    help="Path to your CV file (.pdf, .docx, or .txt).",
)
@click.option(
    "--field",
    required=True,
    help='Research field to search for (e.g. "machine learning", "molecular biology").',
)
@click.option(
    "--location",
    default="Europe",
    show_default=True,
    help="Preferred location (e.g. 'Europe', 'UK', 'Germany').",
)
@click.option(
    "--type",
    "position_type",
    default="any",
    show_default=True,
    type=click.Choice(["phd", "postdoc", "fellowship", "research_staff", "other", "any"]),
    help="Filter by position type.",
)
@click.option(
    "--min-score",
    default=60,
    show_default=True,
    type=int,
    help="Minimum match score (0-100) to include a position in the review queue.",
)
@click.option(
    "--max-positions",
    default=20,
    show_default=True,
    type=int,
    help="Maximum number of positions to score and evaluate.",
)
@click.option(
    "--output-dir",
    default="./output",
    show_default=True,
    help="Directory where approved application materials are saved.",
)
@click.option(
    "--model",
    default=None,
    help=(
        "Override the LLM model (e.g. 'mistral:7b', 'llama3:8b'). "
        "Defaults to OLLAMA_MODEL in .env."
    ),
)
@click.option(
    "--no-interactive",
    is_flag=True,
    default=False,
    help="Skip the review loop — automatically save all qualifying positions.",
)
def main(
    cv_path: str,
    field: str,
    location: str,
    position_type: str,
    min_score: int,
    max_positions: int,
    output_dir: str,
    model: str | None,
    no_interactive: bool,
) -> None:
    """PhD / postdoc / fellowship job agent — powered by local LLMs (Ollama).

    Parses your CV, searches free research job boards, scores each position
    against your profile, then runs an interactive review so you can approve,
    edit, or skip each cover letter before saving to disk.
    """
    _print_banner()

    # Apply model override to config if supplied
    if model:
        config.ollama_model = model

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "applications").mkdir(exist_ok=True)

    # -------------------------------------------------------------------------
    # Step 1: Check LLM backend
    # -------------------------------------------------------------------------
    console.rule("[bold cyan]Step 1: Checking LLM Backend[/bold cyan]")
    console.print(
        f"Backend: [bold]{config.llm_backend}[/bold]  "
        f"Model: [bold]{config.ollama_model if config.llm_backend == 'ollama' else config.hf_model}[/bold]"
    )
    config.validate()
    console.print("[green]Backend check complete.[/green]")

    # -------------------------------------------------------------------------
    # Step 2: Parse CV
    # -------------------------------------------------------------------------
    console.rule("[bold cyan]Step 2: Parsing CV[/bold cyan]")

    from agent.llm_client import LLMClient
    from agent.cv.parser import CVParser
    from agent.search.searcher import JobSearcher
    from agent.matching.matcher import JobMatcher

    llm = LLMClient(model=model)
    parser = CVParser(llm)
    searcher = JobSearcher()
    matcher = JobMatcher(llm)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("Parsing CV with LLM...", total=None)
        profile = parser.parse(cv_path)

    _print_cv_profile(profile)
    profile_text = parser.summarize(profile)

    # -------------------------------------------------------------------------
    # Step 3: Search for research positions
    # -------------------------------------------------------------------------
    console.rule("[bold cyan]Step 3: Searching for Research Positions[/bold cyan]")
    console.print(
        f"Field: [bold]{field}[/bold]  "
        f"Location: [bold]{location}[/bold]  "
        f"Type filter: [bold]{position_type}[/bold]"
    )

    jobs = searcher.search(field=field, location=location, position_type=position_type)

    if not jobs:
        console.print(
            "[bold red]No positions found. "
            "Try a different --field, --location, or --type.[/bold red]"
        )
        sys.exit(0)

    _print_jobs_table(jobs)

    # -------------------------------------------------------------------------
    # Step 4: Score positions
    # -------------------------------------------------------------------------
    console.rule("[bold cyan]Step 4: Scoring Positions[/bold cyan]")
    to_score = jobs[:max_positions]
    console.print(
        f"Evaluating [bold]{len(to_score)}[/bold] positions "
        f"(min score: {min_score})..."
    )

    scored: list[dict[str, Any]] = []

    with Progress(
        SpinnerColumn(),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Scoring...", total=len(to_score))
        for job in to_score:
            match = matcher.score(job, profile_text)
            scored.append({**job, "match": match})
            progress.advance(task)

    scored.sort(key=lambda j: j["match"].get("match_score", 0), reverse=True)
    qualifying = [j for j in scored if j["match"].get("match_score", 0) >= min_score]

    if not qualifying:
        console.print(
            f"[bold yellow]No positions scored above {min_score}. "
            "Try lowering --min-score or broadening --field / --location.[/bold yellow]"
        )
        sys.exit(0)

    _print_scored_table(qualifying)
    console.print(
        f"\n[bold]{len(qualifying)}[/bold] qualifying position(s) to review."
    )

    # -------------------------------------------------------------------------
    # Step 5: Interactive review (or batch save in --no-interactive mode)
    # -------------------------------------------------------------------------
    console.rule("[bold cyan]Step 5: Review & Save Applications[/bold cyan]")

    from agent.cv.cover_letter import CoverLetterWriter
    from agent.cv.tailor import CVTailor
    from agent.interactive_review import ReviewSession

    tailor = CVTailor(llm)
    writer = CoverLetterWriter(llm)

    review_session = ReviewSession(llm_model=model)
    review_session.set_profile(profile_text)

    approved_list: list[dict[str, Any]] = []
    skipped_count = 0
    summary_records: list[dict[str, Any]] = []

    for idx, job in enumerate(qualifying, start=1):
        match = job["match"]
        title = job.get("title", "Unknown")
        institution = job.get("institution", job.get("company", "Unknown"))
        score = match.get("match_score", 0)

        console.print(
            f"\n[bold dim][{idx}/{len(qualifying)}][/bold dim] "
            f"[bold]{title}[/bold] @ {institution} "
            f"(score: [{_score_color(score)}]{score}[/{_score_color(score)}])"
        )

        # Generate tailoring hints
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as p:
            p.add_task("Generating CV tailoring hints...", total=None)
            tailoring_hints = tailor.generate(job, profile_text)

        # Generate cover letter
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as p:
            p.add_task("Generating cover letter draft...", total=None)
            cover_letter = writer.generate(job, profile_text)

        if no_interactive:
            # Batch mode: save without prompting
            app_dir = _save_application(
                job=job,
                match=match,
                tailoring_hints=tailoring_hints,
                cover_letter=cover_letter,
                notes="[batch mode]",
                output_path=output_path,
            )
            console.print(f"  [green]Saved → {app_dir}[/green]")
            approved_list.append({
                "title": title,
                "institution": institution,
                "score": score,
                "app_dir": str(app_dir),
            })
            summary_records.append({
                "title": title,
                "institution": institution,
                "location": job.get("location"),
                "url": job.get("url"),
                "score": score,
                "recommendation": match.get("recommendation"),
                "decision": "approved",
                "notes": "[batch mode]",
                "app_dir": str(app_dir),
                "timestamp": datetime.now().isoformat(),
            })
            continue

        # Interactive review
        result = review_session.review_position(
            job=job,
            match=match,
            tailoring_hints=tailoring_hints,
            cover_letter=cover_letter,
            console=console,
        )

        decision = result["decision"]

        if decision == "approved":
            app_dir = _save_application(
                job=job,
                match=match,
                tailoring_hints=tailoring_hints,
                cover_letter=result["cover_letter"],
                notes=result.get("notes", ""),
                output_path=output_path,
            )
            console.print(f"  [green]Saved → {app_dir}[/green]")
            approved_list.append({
                "title": title,
                "institution": institution,
                "score": score,
                "app_dir": str(app_dir),
            })
            summary_records.append({
                "title": title,
                "institution": institution,
                "location": job.get("location"),
                "url": job.get("url"),
                "score": score,
                "recommendation": match.get("recommendation"),
                "decision": "approved",
                "notes": result.get("notes", ""),
                "app_dir": str(app_dir),
                "timestamp": datetime.now().isoformat(),
            })

        elif decision == "skipped":
            skipped_count += 1
            summary_records.append({
                "title": title,
                "institution": institution,
                "score": score,
                "decision": "skipped",
                "timestamp": datetime.now().isoformat(),
            })

        elif decision == "quit":
            console.print("[yellow]Quitting review loop.[/yellow]")
            summary_records.append({
                "title": title,
                "institution": institution,
                "score": score,
                "decision": "quit",
                "timestamp": datetime.now().isoformat(),
            })
            break

    # -------------------------------------------------------------------------
    # Step 6: Save summary and print final report
    # -------------------------------------------------------------------------
    console.rule("[bold cyan]Step 6: Summary[/bold cyan]")

    summary = {
        "generated_at": datetime.now().isoformat(),
        "search": {
            "field": field,
            "location": location,
            "position_type": position_type,
            "min_score": min_score,
            "llm_backend": config.llm_backend,
            "model": model or (
                config.ollama_model if config.llm_backend == "ollama" else config.hf_model
            ),
        },
        "totals": {
            "positions_found": len(jobs),
            "positions_scored": len(scored),
            "positions_qualifying": len(qualifying),
            "approved": len(approved_list),
            "skipped": skipped_count,
        },
        "applications": summary_records,
    }

    summary_path = output_path / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"[dim]Summary saved to {summary_path}[/dim]")

    _print_final_summary(approved_list, skipped_count, output_path)


if __name__ == "__main__":
    main()
