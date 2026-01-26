"""
Academic Referee Agent
Core agent implementation using Claude CLI for review generation.
"""

import asyncio
import json
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

from myreferee.tools.paper_parser import PaperParser, ParsedPaper
from myreferee.tools.journal_research import JournalResearcher, JournalProfile
from myreferee.tools.report_generator import ReportGenerator, ReviewContent
from myreferee.prompts.system_prompt import SYSTEM_PROMPT, CHECKPOINT_PROMPTS
from myreferee.config import settings


@dataclass
class AgentState:
    """Tracks the current state of the agent workflow."""

    stage: str = "init"
    target_journal: Optional[str] = None
    candidate_journals: List[str] = field(default_factory=list)
    submission_type: str = "first_submission"
    previous_concerns: Optional[str] = None
    journal_profile: Optional[Dict] = None
    paper_path: Optional[str] = None
    parsed_paper: Optional[Dict] = None
    review_content: Optional[Dict] = None
    report_path: Optional[str] = None
    session_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentState":
        return cls(**data)


class SessionManager:
    """Manages persistent sessions for R&R tracking."""

    def __init__(self, sessions_dir: Optional[Path] = None):
        self.sessions_dir = sessions_dir or settings.sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, state: AgentState) -> str:
        if not state.session_id:
            state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        state.updated_at = datetime.now().isoformat()
        filepath = self.sessions_dir / f"{state.session_id}.json"
        with open(filepath, "w") as f:
            json.dump(state.to_dict(), f, indent=2)
        return state.session_id

    def load_session(self, session_id: str) -> Optional[AgentState]:
        filepath = self.sessions_dir / f"{session_id}.json"
        if not filepath.exists():
            return None
        with open(filepath, "r") as f:
            data = json.load(f)
        return AgentState.from_dict(data)

    def list_sessions(self) -> List[Dict]:
        sessions = []
        for filepath in self.sessions_dir.glob("*.json"):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                sessions.append(
                    {
                        "session_id": data.get("session_id"),
                        "journal": data.get("target_journal"),
                        "paper_title": data.get("parsed_paper", {}).get(
                            "title", "Unknown"
                        ),
                        "stage": data.get("stage"),
                        "updated_at": data.get("updated_at"),
                    }
                )
            except Exception:
                pass
        return sorted(sessions, key=lambda x: x.get("updated_at", ""), reverse=True)


class ClaudeRunner:
    """Runs prompts through Claude CLI."""

    @staticmethod
    def is_available() -> bool:
        """Check if claude CLI is available."""
        return shutil.which("claude") is not None

    @staticmethod
    def run_prompt(prompt: str, stream: bool = True) -> str:
        """
        Run a prompt through Claude CLI.

        Args:
            prompt: The prompt to send to Claude
            stream: Whether to stream output (not currently used)

        Returns:
            Claude's response text
        """
        if not ClaudeRunner.is_available():
            raise RuntimeError(
                "Claude CLI not found. Please install Claude Code: "
                "https://claude.ai/code"
            )

        # Run claude with the prompt
        # Using -p for print mode (non-interactive)
        result = subprocess.run(
            [
                "claude",
                "-p",
                prompt,
                "--allowedTools",
                "WebSearch,WebFetch",
            ],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout for long reviews
        )

        if result.returncode != 0:
            error_msg = result.stderr or "Unknown error"
            raise RuntimeError(f"Claude CLI error: {error_msg}")

        return result.stdout

    @staticmethod
    async def run_prompt_async(prompt: str) -> str:
        """Async wrapper for run_prompt."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, ClaudeRunner.run_prompt, prompt)


class AcademicRefereeAgent:
    """Main agent implementing the referee workflow."""

    def __init__(
        self,
        output_dir: Optional[str] = None,
        sessions_dir: Optional[str] = None,
    ):
        self.output_dir = Path(output_dir) if output_dir else settings.reviews_dir
        sessions_path = Path(sessions_dir) if sessions_dir else settings.sessions_dir

        self.paper_parser = PaperParser()
        self.journal_researcher = (
            JournalResearcher(settings.elsevier_api_key)
            if settings.elsevier_api_key
            else None
        )
        self.report_generator = ReportGenerator(str(self.output_dir))
        self.session_manager = SessionManager(sessions_path)
        self.state = AgentState()
        self.claude_runner = ClaudeRunner()

    def get_initial_prompt(self) -> str:
        """Get the initial prompt to display to the user."""
        return CHECKPOINT_PROMPTS["journal_selection"]["initial"]

    async def research_journal(self, journal_name: str) -> Dict:
        """Research a journal using Scopus and web search."""
        profile_data = {
            "name": journal_name,
            "articles_analyzed": 0,
            "sources_used": [],
        }

        if self.journal_researcher:
            try:
                profile = await self.journal_researcher.research_journal(
                    journal_name, years_back=5, max_articles=30
                )
                profile_data = profile.to_dict()
            except Exception as e:
                profile_data["error"] = str(e)

        return profile_data

    def parse_paper(self, file_path: str) -> Dict:
        """Parse a paper file and return structured content."""
        parsed = self.paper_parser.parse(file_path)
        return parsed.to_dict()

    def generate_review_prompt(self) -> str:
        """Generate the comprehensive review prompt for Claude."""
        paper = self.state.parsed_paper
        journal = self.state.journal_profile

        return f"""{SYSTEM_PROMPT}

---

## CURRENT TASK

Review the following paper for **{self.state.target_journal}**.

### Journal Profile
{json.dumps(journal, indent=2) if journal else "Journal research pending."}

### Paper to Review
**Title:** {paper.get('title', 'Unknown')}
**Word Count:** {paper.get('word_count', 'Unknown')}
**Page Count:** {paper.get('page_count', 'Unknown')}

**Abstract:**
{paper.get('abstract', 'Not available')}

**Sections:**
{chr(10).join(f"- {name}" for name in paper.get('sections', {}).keys())}

**Full Text (truncated):**
{paper.get('full_text', '')[:30000]}

---

Now provide a complete referee report following the structure in your instructions:
1. Summary (2-3 sentences)
2. Contribution & Journal Fit
3. Major Concerns (deal-breakers)
4. Minor Concerns
5. Robustness/Diagnostics Checklist
6. Section-by-Section Analysis
7. Positioning vs. Journal Benchmarks
8. Editor Cover Note
9. Prioritized To-Do List

Be specific, cite evidence from the paper, and calibrate to {self.state.target_journal}'s standards."""

    async def run_review(self) -> str:
        """Run the review using Claude CLI."""
        prompt = self.generate_review_prompt()

        if not ClaudeRunner.is_available():
            raise RuntimeError(
                "Claude CLI not found. Please install Claude Code first."
            )

        return await ClaudeRunner.run_prompt_async(prompt)

    def save_report(self, content: str, paper_title: str) -> str:
        """Save the review report to disk."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        safe_title = "".join(
            c if c.isalnum() or c in "- _" else "_" for c in paper_title[:50]
        )
        safe_journal = "".join(
            c if c.isalnum() or c in "- _" else "_"
            for c in (self.state.target_journal or "unknown")[:30]
        )
        date_str = datetime.now().strftime("%Y%m%d")

        filename = f"{safe_journal}_{safe_title}_{date_str}.md"
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        self.state.report_path = str(filepath)
        return str(filepath)

    def update_state(self, **kwargs):
        """Update agent state with provided values."""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
        self.session_manager.save_session(self.state)

    def get_state_summary(self) -> str:
        """Get a summary of current agent state."""
        paper_title = (
            self.state.parsed_paper.get("title", "Not uploaded")
            if self.state.parsed_paper
            else "Not uploaded"
        )
        return f"""Current State:
- Stage: {self.state.stage}
- Target Journal: {self.state.target_journal or 'Not selected'}
- Submission Type: {self.state.submission_type}
- Paper: {paper_title}
- Session ID: {self.state.session_id or 'Not saved'}"""
