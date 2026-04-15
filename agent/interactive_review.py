"""Interactive human-in-the-loop review component.

For each qualifying position the agent has analysed, this module:
  1. Displays full position details
  2. Shows tailoring hints as a checklist
  3. Shows the cover letter draft
  4. Prompts the user to Approve / Edit / Regenerate / Skip / Quit

If the user chooses Edit, the cover letter is opened in $EDITOR (falling back to
nano on Linux/Mac or notepad on Windows).  If no editor is available, inline
text entry is offered as a last resort.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Any, TypedDict

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box


# ---------------------------------------------------------------------------
# Type definitions
# ---------------------------------------------------------------------------

class ReviewResult(TypedDict):
    decision: str      # "approved" | "skipped" | "quit"
    cover_letter: str  # final (possibly edited) cover letter
    notes: str         # optional user notes


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _score_color(score: int) -> str:
    if score >= 80:
        return "green"
    elif score >= 60:
        return "yellow"
    return "red"


def _rec_color(rec: str) -> str:
    return {"apply": "green", "consider": "yellow", "skip": "red"}.get(rec, "white")


def _show_position_panel(job: dict[str, Any], match: dict[str, Any], console: Console) -> None:
    """Render a rich panel with the position details and match analysis."""
    score = match.get("match_score", 0)
    rec = match.get("recommendation", "")

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    table.add_row("Title", job.get("title") or "N/A")
    table.add_row("Institution", job.get("institution", job.get("company", "N/A")))
    table.add_row("Location", job.get("location") or "N/A")
    table.add_row("Type", job.get("type") or "N/A")
    table.add_row("Deadline", job.get("deadline") or "Not specified")
    table.add_row("URL", job.get("url") or "N/A")
    table.add_row("Source", job.get("source") or "N/A")
    if job.get("email"):
        table.add_row("Contact email", job["email"])
    table.add_row(
        "Match score",
        f"[{_score_color(score)}]{score}/100[/{_score_color(score)}]",
    )
    table.add_row(
        "Recommendation",
        f"[{_rec_color(rec)}]{rec.upper()}[/{_rec_color(rec)}]",
    )

    if match.get("why_good_fit"):
        table.add_row("Why good fit", match["why_good_fit"])
    if match.get("concerns"):
        table.add_row("Concerns", f"[yellow]{match['concerns']}[/yellow]")

    matching = match.get("matching_areas") or []
    if matching:
        table.add_row("Matching areas", ", ".join(matching))

    missing = match.get("missing_requirements") or []
    if missing:
        table.add_row("Missing", "[red]" + ", ".join(missing) + "[/red]")

    console.print(Panel(table, title="[bold]Position Details[/bold]", border_style="blue"))


def _show_tailoring_panel(hints: dict[str, Any], console: Console) -> None:
    """Render CV tailoring hints as a checklist panel."""
    lines: list[str] = []

    if hints.get("headline_suggestion"):
        lines.append("[bold cyan]Profile summary tweak:[/bold cyan]")
        lines.append(f"  {hints['headline_suggestion']}")
        lines.append("")

    if hints.get("research_alignment"):
        lines.append("[bold cyan]How to frame your research interests:[/bold cyan]")
        lines.append(f"  {hints['research_alignment']}")
        lines.append("")

    skills = hints.get("skills_to_highlight") or []
    if skills:
        lines.append("[bold cyan]Skills to emphasise:[/bold cyan]")
        for s in skills:
            lines.append(f"  [ ] {s}")
        lines.append("")

    experience = hints.get("experience_to_emphasize") or []
    if experience:
        lines.append("[bold cyan]Experience entries to highlight:[/bold cyan]")
        for e in experience:
            lines.append(f"  [ ] {e}")
        lines.append("")

    keywords = hints.get("keywords_to_add") or []
    if keywords:
        lines.append("[bold cyan]Keywords to add to your CV:[/bold cyan]")
        lines.append("  " + ", ".join(keywords))
        lines.append("")

    order = hints.get("suggested_order") or []
    if order:
        lines.append("[bold cyan]Suggested CV section order:[/bold cyan]")
        lines.append("  " + " → ".join(order))

    content = "\n".join(lines) if lines else "[dim]No tailoring hints generated.[/dim]"
    console.print(Panel(content, title="[bold]CV Tailoring Hints[/bold]", border_style="yellow"))


def _show_cover_letter_panel(cover_letter: str, console: Console) -> None:
    """Render the cover letter draft in a panel."""
    # Try to render as Markdown for nicer display
    try:
        rendered: Any = Markdown(cover_letter)
    except Exception:
        rendered = cover_letter
    console.print(Panel(rendered, title="[bold]Cover Letter Draft[/bold]", border_style="green"))


# ---------------------------------------------------------------------------
# Editor helper
# ---------------------------------------------------------------------------

def _open_in_editor(content: str, console: Console) -> str:
    """Open content in the user's $EDITOR and return the edited text.

    Falls back to nano → vi → notepad (Windows).
    If no editor is found, offers inline text entry.
    """
    # Determine editor
    editor = os.environ.get("EDITOR", "")
    if not editor:
        # Try common fallbacks
        for fallback in ("nano", "vi", "notepad"):
            if _command_exists(fallback):
                editor = fallback
                break

    if editor:
        # Write to temp file, open editor, read back
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".txt", mode="w", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(content)
                tmpfile = tmp.name

            console.print(
                f"[dim]Opening in {editor} — save and close the editor to continue.[/dim]"
            )
            subprocess.call([editor, tmpfile])

            with open(tmpfile, encoding="utf-8") as f:
                edited = f.read()

            os.unlink(tmpfile)
            return edited
        except Exception as exc:
            console.print(f"[yellow]Editor launch failed: {exc}. Falling back to inline entry.[/yellow]")

    # Inline fallback: show the text, then ask for a replacement
    console.print("\n[yellow]No editor available. Current cover letter:[/yellow]")
    console.print(content)
    console.print(
        "\n[yellow]Paste your edited version below. "
        "Enter a single dot '.' on a blank line when done:[/yellow]"
    )
    typed_lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == ".":
            break
        typed_lines.append(line)

    inline_text = "\n".join(typed_lines).strip()
    return inline_text if inline_text else content


def _command_exists(cmd: str) -> bool:
    """Return True if a command is available on PATH."""
    import shutil
    return shutil.which(cmd) is not None


# ---------------------------------------------------------------------------
# Main review session
# ---------------------------------------------------------------------------

class ReviewSession:
    """Manages the interactive review of a single job application."""

    def __init__(self, llm_model: str | None = None) -> None:
        # Store the model so we can regenerate cover letters
        self._model = llm_model

    def review_position(
        self,
        job: dict[str, Any],
        match: dict[str, Any],
        tailoring_hints: dict[str, Any],
        cover_letter: str,
        console: Console,
    ) -> ReviewResult:
        """Display position details, hints, and cover letter; collect user decision.

        Args:
            job:              Job listing dict.
            match:            MatchResult dict.
            tailoring_hints:  TailoringHints dict.
            cover_letter:     Generated cover letter draft.
            console:          Rich Console for output.

        Returns:
            ReviewResult with decision ("approved" | "skipped" | "quit"),
            final cover letter, and optional notes.
        """
        # --- Display phase ---
        console.rule(
            f"[bold]{job.get('title', 'Unknown')} "
            f"@ {job.get('institution', job.get('company', 'Unknown'))}[/bold]"
        )
        _show_position_panel(job, match, console)
        _show_tailoring_panel(tailoring_hints, console)
        _show_cover_letter_panel(cover_letter, console)

        current_letter = cover_letter

        # --- Decision loop ---
        while True:
            console.print("")
            console.print(
                "  [green]\\[A]pprove[/green]  "
                "[yellow]\\[E]dit cover letter[/yellow]  "
                "[blue]\\[R]egenerate[/blue]  "
                "[dim]\\[S]kip[/dim]  "
                "[red]\\[Q]uit[/red]"
            )
            choice = Prompt.ask(
                "[bold cyan]Action[/bold cyan]",
                choices=["a", "e", "r", "s", "q"],
                default="s",
                show_choices=False,
                show_default=False,
                console=console,
            ).lower()

            if choice == "a":
                notes = Prompt.ask(
                    "Optional notes (press Enter to skip)",
                    default="",
                    console=console,
                )
                return ReviewResult(
                    decision="approved",
                    cover_letter=current_letter,
                    notes=notes,
                )

            elif choice == "e":
                console.print("[dim]Opening editor...[/dim]")
                current_letter = _open_in_editor(current_letter, console)
                console.print("[green]Cover letter updated.[/green]")
                _show_cover_letter_panel(current_letter, console)

            elif choice == "r":
                console.print("[dim]Regenerating cover letter...[/dim]")
                current_letter = self._regenerate(job, cover_letter, console)
                _show_cover_letter_panel(current_letter, console)

            elif choice == "s":
                return ReviewResult(
                    decision="skipped",
                    cover_letter=current_letter,
                    notes="",
                )

            elif choice == "q":
                return ReviewResult(
                    decision="quit",
                    cover_letter=current_letter,
                    notes="",
                )

    def _regenerate(
        self,
        job: dict[str, Any],
        original_letter: str,
        console: Console,
    ) -> str:
        try:
            from agent.llm_client import LLMClient
            from agent.cv.cover_letter import CoverLetterWriter

            profile_text = getattr(self, "_profile_text", "")
            llm = LLMClient(model=self._model)
            new_letter = CoverLetterWriter(llm).generate(job, profile_text, regenerate=True)
            return new_letter
        except Exception as exc:
            console.print(f"[red]Regeneration failed: {exc}[/red]")
            return original_letter

    def set_profile(self, profile_text: str) -> None:
        """Provide the CV profile text for regeneration use."""
        self._profile_text = profile_text
