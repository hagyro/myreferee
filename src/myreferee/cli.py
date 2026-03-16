#!/usr/bin/env python3
"""
Academic Referee Agent - CLI Entry Point
Provides a command-line interface for the referee workflow.
"""

import asyncio
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from dotenv import load_dotenv

from myreferee import __version__
from myreferee.agent import AcademicRefereeAgent, SessionManager, ClaudeRunner
from myreferee.prompts.system_prompt import CHECKPOINT_PROMPTS
from myreferee.config import settings

# Load environment variables from .env if present
load_dotenv()

console = Console()


def print_header():
    """Print the application header."""
    console.print(
        Panel.fit(
            f"[bold blue]Academic Referee Agent[/bold blue] v{__version__}\n"
            "[dim]Rigorous, journal-calibrated paper reviews[/dim]",
            border_style="blue",
        )
    )
    console.print()


def print_markdown(text: str):
    """Print text as formatted Markdown."""
    console.print(Markdown(text))


async def run_interactive_session(
    agent: AcademicRefereeAgent,
    resume_session: str = None,
    target_journal: str = None,
    non_interactive: bool = False,
):
    """Run the interactive agent session.

    Args:
        agent: The referee agent instance
        resume_session: Optional session ID to resume
        target_journal: Optional journal name (skips interactive selection)
        non_interactive: If True, skip all prompts and run end-to-end
    """

    # Pre-set journal if provided
    if target_journal and not agent.state.target_journal:
        agent.state.target_journal = target_journal
        agent.state.candidate_journals = [target_journal]
        console.print(f"[green]Target journal: {target_journal}[/green]\n")

    # Resume session if specified
    if resume_session:
        loaded = agent.session_manager.load_session(resume_session)
        if loaded:
            agent.state = loaded
            console.print(f"[green]Resumed session: {resume_session}[/green]")
            console.print(agent.get_state_summary())
            console.print()
        else:
            console.print(
                f"[yellow]Session {resume_session} not found. Starting new session.[/yellow]"
            )

    # Stage 1: Journal Selection
    if agent.state.stage in ["init", "journal_selection"]:
        agent.state.stage = "journal_selection"

        # Skip interactive selection if journal already set
        if not agent.state.target_journal:
            console.print(
                Panel(
                    CHECKPOINT_PROMPTS["journal_selection"]["initial"],
                    title="[bold]Step 1: Target Journal[/bold]",
                    border_style="cyan",
                )
            )

            while not agent.state.target_journal:
                user_input = Prompt.ask("\n[bold cyan]Your response[/bold cyan]")

                if not user_input.strip():
                    continue

                # Check for R&R
                if any(
                    term in user_input.lower() for term in ["r&r", "revise", "resubmit"]
                ):
                    agent.state.submission_type = "r_and_r"

                # Extract journal name
                agent.state.target_journal = user_input.strip()
                agent.state.candidate_journals = [user_input.strip()]

                console.print(
                    f"\n[green]Target journal: {agent.state.target_journal}[/green]"
                )

                if agent.state.submission_type == "r_and_r":
                    console.print(
                        Panel(
                            CHECKPOINT_PROMPTS["journal_selection"]["r_and_r_followup"],
                            border_style="yellow",
                        )
                    )
                    concerns = Prompt.ask(
                        "\n[bold cyan]Previous concerns (or press Enter to skip)[/bold cyan]"
                    )
                    if concerns.strip():
                        agent.state.previous_concerns = concerns

        agent.update_state(stage="journal_research")

    # Stage 2: Journal Research
    if agent.state.stage == "journal_research":
        console.print(
            Panel(
                f"Researching **{agent.state.target_journal}**...\n\n"
                "This includes:\n"
                "- Aims & scope analysis\n"
                "- Recent publications review (last 3-5 years)\n"
                "- Identifying typical methods and referee expectations",
                title="[bold]Step 2: Journal Research[/bold]",
                border_style="cyan",
            )
        )

        with console.status("[bold green]Searching Scopus and web...[/bold green]"):
            profile = await agent.research_journal(agent.state.target_journal)
            agent.state.journal_profile = profile

        # Display findings
        console.print("\n[bold green]Journal Analysis Complete[/bold green]\n")

        if profile.get("typical_methods"):
            console.print(
                f"[bold]Typical Methods:[/bold] {', '.join(profile['typical_methods'][:5])}"
            )

        if profile.get("referee_priors"):
            priors = profile["referee_priors"]
            if priors.get("common_concerns"):
                console.print(
                    f"[bold]Common Concerns:[/bold] {', '.join(priors['common_concerns'][:4])}"
                )
            if priors.get("robustness_expectations"):
                console.print(
                    f"[bold]Robustness Expected:[/bold] {priors['robustness_expectations']}"
                )

        console.print(
            f"\n[dim]Articles analyzed: {profile.get('articles_analyzed', 0)}[/dim]"
        )

        # Skip confirmation in non-interactive mode
        if non_interactive:
            agent.update_state(stage="paper_upload")
        else:
            proceed = Prompt.ask(
                "\n[bold cyan]Proceed to paper upload? (yes/no)[/bold cyan]", default="yes"
            )
            if proceed.lower() in ["yes", "y", ""]:
                agent.update_state(stage="paper_upload")

    # Stage 3: Paper Upload
    if agent.state.stage == "paper_upload":
        # Auto-parse if paper path already set
        if agent.state.paper_path and not agent.state.parsed_paper:
            try:
                with console.status("[bold green]Parsing paper...[/bold green]"):
                    parsed = agent.parse_paper(agent.state.paper_path)
                    agent.state.parsed_paper = parsed

                console.print(f"[green]Paper parsed successfully[/green]")
                console.print(f"[bold]Title:[/bold] {parsed.get('title', 'Unknown')}")
                console.print(
                    f"[bold]Pages:[/bold] {parsed.get('page_count', '?')} | "
                    f"[bold]Words:[/bold] {parsed.get('word_count', '?'):,}"
                )
                console.print(
                    f"[bold]Sections:[/bold] {', '.join(list(parsed.get('sections', {}).keys())[:5])}\n"
                )
            except Exception as e:
                console.print(f"[red]Error parsing paper: {e}[/red]")
                return

        # Interactive paper selection if not already set
        if not agent.state.parsed_paper:
            console.print(
                Panel(
                    CHECKPOINT_PROMPTS["paper_upload"]["request"],
                    title="[bold]Step 3: Paper Upload[/bold]",
                    border_style="cyan",
                )
            )

            while not agent.state.parsed_paper:
                file_path = Prompt.ask("\n[bold cyan]Paper file path[/bold cyan]")
                file_path = file_path.strip().strip('"').strip("'")

                # Expand user home directory
                file_path = os.path.expanduser(file_path)

                if not os.path.exists(file_path):
                    console.print(f"[red]File not found: {file_path}[/red]")
                    continue

                try:
                    with console.status("[bold green]Parsing paper...[/bold green]"):
                        parsed = agent.parse_paper(file_path)
                        agent.state.paper_path = file_path
                        agent.state.parsed_paper = parsed

                    console.print(f"\n[green]Paper parsed successfully[/green]")
                    console.print(f"[bold]Title:[/bold] {parsed.get('title', 'Unknown')}")
                    console.print(
                        f"[bold]Pages:[/bold] {parsed.get('page_count', '?')} | "
                        f"[bold]Words:[/bold] {parsed.get('word_count', '?'):,}"
                    )
                    console.print(
                        f"[bold]Sections:[/bold] {', '.join(list(parsed.get('sections', {}).keys())[:5])}"
                    )

                except Exception as e:
                    console.print(f"[red]Error parsing paper: {e}[/red]")

        agent.update_state(stage="reviewing")

    # Stage 4: Review
    if agent.state.stage == "reviewing":
        console.print(
            Panel(
                "Now conducting the comprehensive review.\n\n"
                "I will analyze:\n"
                "- Contribution and journal fit\n"
                "- Methodological rigor\n"
                "- Robustness requirements\n"
                "- Section-by-section improvements\n"
                "- Positioning vs. recent publications",
                title="[bold]Step 4: Conducting Review[/bold]",
                border_style="cyan",
            )
        )

        # Check Claude CLI availability
        if not ClaudeRunner.is_available():
            console.print("\n[red]Claude CLI not found.[/red]")
            console.print(
                "Please install Claude Code: https://claude.ai/code\n"
            )
            console.print(
                "Alternatively, the review prompt has been prepared. You can:\n"
                "1. Copy the prompt using: myreferee --show-prompt\n"
                "2. Paste it into Claude directly"
            )
            return

        console.print("\n[bold yellow]Starting Claude review...[/bold yellow]")
        console.print(
            "[dim]This may take several minutes for a thorough review.[/dim]\n"
        )

        try:
            review_content = await agent.run_review()

            # Save report
            paper_title = agent.state.parsed_paper.get("title", "untitled")
            report_path = agent.save_report(review_content, paper_title)

            console.print(f"\n\n[bold green]Review complete![/bold green]")
            console.print(f"[bold]Report saved to:[/bold] {report_path}")

            agent.update_state(stage="complete", report_path=report_path)

        except Exception as e:
            console.print(f"\n[red]Error during review: {e}[/red]")
            console.print(
                "\nThe review prompt has been prepared. You can:\n"
                "1. Run the review manually with: myreferee --show-prompt\n"
                "2. Or try again later"
            )
            return

    # Stage 5: Post-Review
    if agent.state.stage == "complete":
        console.print(
            Panel(
                f"Review complete!\n\n"
                f"**Report saved to:** {agent.state.report_path}\n\n"
                "You can now:\n"
                "- View the full report\n"
                "- Ask follow-up questions\n"
                "- Compare with another journal\n"
                "- Save session for R&R tracking",
                title="[bold]Review Complete[/bold]",
                border_style="green",
            )
        )

        # Exit immediately in non-interactive mode
        if non_interactive:
            console.print("[bold]Thank you for using Academic Referee Agent![/bold]")
            return

        while True:
            action = Prompt.ask(
                "\n[bold cyan]What would you like to do?[/bold cyan]\n"
                "[1] View report\n"
                "[2] Ask follow-up question\n"
                "[3] Save session\n"
                "[4] Exit\n"
                "Choice",
                default="4",
            )

            if action == "1":
                if agent.state.report_path and os.path.exists(agent.state.report_path):
                    with open(agent.state.report_path, "r") as f:
                        print_markdown(f.read())
                else:
                    console.print("[yellow]Report not found.[/yellow]")

            elif action == "2":
                question = Prompt.ask("[bold cyan]Your question[/bold cyan]")
                console.print(
                    "[dim]Follow-up questions will be implemented in a future version.[/dim]"
                )

            elif action == "3":
                session_id = agent.session_manager.save_session(agent.state)
                console.print(f"[green]Session saved: {session_id}[/green]")
                console.print(f"Resume later with: myreferee --resume {session_id}")

            elif action == "4":
                console.print("[bold]Thank you for using Academic Referee Agent![/bold]")
                break


@click.command()
@click.option("--paper", "-p", help="Path to paper file (PDF, Word, or LaTeX)")
@click.option("--journal", "-j", help="Target journal name (skips interactive selection)")
@click.option("--resume", "-r", help="Resume a previous session by ID")
@click.option("--list-reviews", "-l", is_flag=True, help="List past reviews")
@click.option("--list-sessions", "-s", is_flag=True, help="List saved sessions")
@click.option("--output-dir", "-o", help="Output directory for reports")
@click.option("--show-prompt", is_flag=True, help="Show the review prompt without running")
@click.option("--web", is_flag=True, help="Launch web interface on localhost")
@click.option("--port", default=5000, help="Port for web interface (default: 5000)")
@click.version_option(version=__version__)
def main(paper, journal, resume, list_reviews, list_sessions, output_dir, show_prompt, web, port):
    """Academic Referee Agent - Journal-calibrated paper reviews.

    Provides rigorous, journal-specific reviews of academic papers
    in economics and finance.

    Example usage:

        myreferee                    # Interactive mode

        myreferee -p paper.pdf       # Start with a paper

        myreferee -p paper.pdf -j "Journal of Finance"  # Non-interactive

        myreferee --resume SESSION   # Resume a previous session

        myreferee --list-sessions    # Show saved sessions
    """
    print_header()

    # Launch web interface if requested
    if web:
        from myreferee.web import run_server

        run_server(port=port)
        return

    # Check for Elsevier API key
    if not settings.elsevier_api_key:
        console.print("[yellow]Warning: ELSEVIER_API_KEY not set[/yellow]")
        console.print("Scopus integration will be limited.\n")

    # Determine output directory
    out_dir = output_dir if output_dir else str(settings.reviews_dir)

    # Initialize agent
    agent = AcademicRefereeAgent(output_dir=out_dir)

    # Handle list commands
    if list_sessions:
        sessions = agent.session_manager.list_sessions()
        if sessions:
            console.print("[bold]Saved Sessions:[/bold]\n")
            for s in sessions[:10]:
                console.print(
                    f"  {s['session_id']} | {s['journal']} | "
                    f"{s['paper_title'][:30]} | {s['stage']}"
                )
        else:
            console.print("No saved sessions found.")
        return

    if list_reviews:
        review_dir = Path(out_dir)
        if review_dir.exists():
            reviews = list(review_dir.glob("*.md"))
            if reviews:
                console.print("[bold]Past Reviews:[/bold]\n")
                for r in sorted(reviews, reverse=True)[:10]:
                    console.print(f"  {r.name}")
            else:
                console.print("No reviews found.")
        else:
            console.print("Review directory not found.")
        return

    # Pre-load paper if specified
    if paper:
        paper = os.path.expanduser(paper)
        if os.path.exists(paper):
            agent.state.paper_path = paper
            console.print(f"[green]Paper queued: {paper}[/green]\n")
        else:
            console.print(f"[red]File not found: {paper}[/red]")
            sys.exit(1)

    # Show prompt mode
    if show_prompt:
        if not agent.state.parsed_paper and paper:
            try:
                agent.state.parsed_paper = agent.parse_paper(paper)
            except Exception as e:
                console.print(f"[red]Error parsing paper: {e}[/red]")
                sys.exit(1)

        if agent.state.parsed_paper:
            prompt = agent.generate_review_prompt()
            console.print(Panel(prompt, title="Review Prompt", border_style="blue"))
        else:
            console.print("[yellow]No paper loaded. Use -p to specify a paper.[/yellow]")
        return

    # Determine if running non-interactively
    non_interactive = bool(paper and journal)

    # Run session
    try:
        asyncio.run(
            run_interactive_session(
                agent,
                resume_session=resume,
                target_journal=journal,
                non_interactive=non_interactive,
            )
        )
    except KeyboardInterrupt:
        console.print(
            "\n[yellow]Session interrupted. Your progress has been saved.[/yellow]"
        )
        agent.session_manager.save_session(agent.state)


if __name__ == "__main__":
    main()
