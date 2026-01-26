"""
Report Generator Tool
Produces structured Markdown referee reports.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import json
import re


@dataclass
class ReviewContent:
    """Container for all review content components."""
    # Paper info
    paper_title: str
    paper_word_count: int
    paper_page_count: int
    
    # Journal info
    journal_name: str
    submission_type: str  # "first_submission" or "r_and_r"
    
    # Review components
    summary: str = ""
    contribution: str = ""
    fit_assessment: str = ""
    comparison_to_recent: str = ""
    
    major_concerns: List[Dict[str, str]] = field(default_factory=list)
    minor_concerns: List[Dict[str, str]] = field(default_factory=list)
    
    robustness_checklist: List[Dict[str, any]] = field(default_factory=list)
    
    section_analysis: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    positioning_strengths: List[str] = field(default_factory=list)
    positioning_gaps: List[str] = field(default_factory=list)
    
    editor_note: str = ""
    
    todo_items: List[Dict[str, any]] = field(default_factory=list)
    
    # Metadata
    articles_analyzed: int = 0
    sources_used: List[str] = field(default_factory=list)


class ReportGenerator:
    """
    Generates structured Markdown referee reports.
    """
    
    def __init__(self, output_dir: str = "data/reviews"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(self, content: ReviewContent) -> str:
        """
        Generate a complete referee report in Markdown format.
        
        Args:
            content: ReviewContent object with all review components
            
        Returns:
            Markdown string of the complete report
        """
        report_parts = []
        
        # Header
        report_parts.append(self._generate_header(content))
        
        # Summary
        report_parts.append(self._generate_summary_section(content))
        
        # Contribution & Fit
        report_parts.append(self._generate_contribution_section(content))
        
        # Major Concerns
        report_parts.append(self._generate_major_concerns_section(content))
        
        # Minor Concerns
        report_parts.append(self._generate_minor_concerns_section(content))
        
        # Robustness Checklist
        report_parts.append(self._generate_robustness_section(content))
        
        # Section Analysis
        report_parts.append(self._generate_section_analysis(content))
        
        # Positioning
        report_parts.append(self._generate_positioning_section(content))
        
        # Editor Note
        report_parts.append(self._generate_editor_note_section(content))
        
        # To-Do List
        report_parts.append(self._generate_todo_section(content))
        
        # Footer
        report_parts.append(self._generate_footer(content))
        
        return "\n\n".join(filter(None, report_parts))
    
    def save_report(
        self,
        content: ReviewContent,
        filename: Optional[str] = None
    ) -> str:
        """
        Generate and save a referee report.
        
        Args:
            content: ReviewContent object
            filename: Optional custom filename (without extension)
            
        Returns:
            Path to saved report
        """
        report = self.generate_report(content)
        
        if not filename:
            # Generate filename from paper title and date
            safe_title = self._sanitize_filename(content.paper_title[:50])
            safe_journal = self._sanitize_filename(content.journal_name[:30])
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"{safe_journal}_{safe_title}_{date_str}"
        
        filepath = self.output_dir / f"{filename}.md"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return str(filepath)
    
    def _sanitize_filename(self, name: str) -> str:
        """Convert a string to a safe filename."""
        # Remove or replace invalid characters
        safe = re.sub(r'[<>:"/\\|?*]', '', name)
        safe = re.sub(r'\s+', '_', safe)
        safe = re.sub(r'[^\w\-_]', '', safe)
        return safe.lower()
    
    def _generate_header(self, content: ReviewContent) -> str:
        """Generate report header."""
        submission_type = (
            "First Submission" if content.submission_type == "first_submission"
            else "Revise & Resubmit"
        )
        
        return f"""# Referee Report

**Paper:** {content.paper_title}  
**Target Journal:** {content.journal_name}  
**Submission Type:** {submission_type}  
**Review Date:** {datetime.now().strftime("%B %d, %Y")}  
**Paper Length:** {content.paper_page_count} pages (~{content.paper_word_count:,} words)

---"""
    
    def _generate_summary_section(self, content: ReviewContent) -> str:
        """Generate summary section."""
        if not content.summary:
            return ""
        
        return f"""## 1. Summary

{content.summary}"""
    
    def _generate_contribution_section(self, content: ReviewContent) -> str:
        """Generate contribution and fit section."""
        parts = ["## 2. Contribution & Journal Fit"]
        
        if content.contribution:
            parts.append(f"""### Main Contribution

{content.contribution}""")
        
        if content.fit_assessment:
            parts.append(f"""### Journal Fit Assessment

{content.fit_assessment}""")
        
        if content.comparison_to_recent:
            parts.append(f"""### Comparison to Recent Publications

{content.comparison_to_recent}""")
        
        return "\n\n".join(parts)
    
    def _generate_major_concerns_section(self, content: ReviewContent) -> str:
        """Generate major concerns section."""
        if not content.major_concerns:
            return """## 3. Major Concerns

No major concerns identified."""
        
        parts = ["## 3. Major Concerns (Deal-Breakers)"]
        
        for i, concern in enumerate(content.major_concerns, 1):
            severity = concern.get("severity", "Critical")
            issue = concern.get("issue", "")
            explanation = concern.get("explanation", "")
            suggested_fix = concern.get("suggested_fix", "")
            
            concern_text = f"""### {i}. {issue}

**Severity:** {severity}

{explanation}"""
            
            if suggested_fix:
                concern_text += f"""

**Suggested Fix:** {suggested_fix}"""
            
            parts.append(concern_text)
        
        return "\n\n".join(parts)
    
    def _generate_minor_concerns_section(self, content: ReviewContent) -> str:
        """Generate minor concerns section."""
        if not content.minor_concerns:
            return """## 4. Minor Concerns

No minor concerns identified."""
        
        parts = ["## 4. Minor Concerns"]
        
        for i, concern in enumerate(content.minor_concerns, 1):
            issue = concern.get("issue", "")
            explanation = concern.get("explanation", "")
            suggested_fix = concern.get("suggested_fix", "")
            
            concern_text = f"**{i}. {issue}**"
            
            if explanation:
                concern_text += f"\n\n{explanation}"
            
            if suggested_fix:
                concern_text += f"\n\n*Suggestion:* {suggested_fix}"
            
            parts.append(concern_text)
        
        return "\n\n".join(parts)
    
    def _generate_robustness_section(self, content: ReviewContent) -> str:
        """Generate robustness checklist section."""
        parts = [f"## 5. Robustness/Diagnostics Checklist\n\nBased on **{content.journal_name}** standards:"]
        
        if not content.robustness_checklist:
            parts.append("\n*Standard robustness checks recommended based on methodology.*")
            return "\n".join(parts)
        
        for item in content.robustness_checklist:
            check = item.get("check", "")
            status = item.get("status", "needed")  # "present", "partial", "needed"
            note = item.get("note", "")
            
            if status == "present":
                checkbox = "[x]"
            elif status == "partial":
                checkbox = "[~]"
            else:
                checkbox = "[ ]"
            
            line = f"- {checkbox} {check}"
            if note:
                line += f" — *{note}*"
            
            parts.append(line)
        
        return "\n".join(parts)
    
    def _generate_section_analysis(self, content: ReviewContent) -> str:
        """Generate section-by-section analysis."""
        if not content.section_analysis:
            return ""
        
        parts = ["## 6. Section-by-Section Analysis"]
        
        section_order = [
            "Introduction", "Literature Review", "Data", 
            "Methodology", "Results", "Discussion", "Conclusion"
        ]
        
        # First add sections in standard order
        for section_name in section_order:
            if section_name in content.section_analysis:
                parts.append(self._format_section_feedback(
                    section_name, 
                    content.section_analysis[section_name]
                ))
        
        # Then add any remaining sections
        for section_name, feedback in content.section_analysis.items():
            if section_name not in section_order:
                parts.append(self._format_section_feedback(section_name, feedback))
        
        return "\n\n".join(parts)
    
    def _format_section_feedback(self, name: str, feedback: Dict[str, str]) -> str:
        """Format feedback for a single section."""
        parts = [f"### {name}"]
        
        if feedback.get("strengths"):
            parts.append(f"**Strengths:** {feedback['strengths']}")
        
        if feedback.get("weaknesses"):
            parts.append(f"**Needs Improvement:** {feedback['weaknesses']}")
        
        if feedback.get("suggestions"):
            parts.append(f"**Suggestions:** {feedback['suggestions']}")
        
        return "\n\n".join(parts)
    
    def _generate_positioning_section(self, content: ReviewContent) -> str:
        """Generate positioning analysis section."""
        parts = ["## 7. Positioning vs. Journal Benchmarks"]
        
        if content.positioning_strengths:
            parts.append("### Strengths Relative to Recent Publications")
            for strength in content.positioning_strengths:
                parts.append(f"- {strength}")
        
        if content.positioning_gaps:
            parts.append("\n### Gaps Relative to Recent Publications")
            for gap in content.positioning_gaps:
                parts.append(f"- {gap}")
        
        if not content.positioning_strengths and not content.positioning_gaps:
            parts.append("\n*Positioning analysis based on comparison with recent accepted papers.*")
        
        return "\n".join(parts)
    
    def _generate_editor_note_section(self, content: ReviewContent) -> str:
        """Generate editor cover note section."""
        if not content.editor_note:
            return ""
        
        return f"""---

## Editor Cover Note

{content.editor_note}"""
    
    def _generate_todo_section(self, content: ReviewContent) -> str:
        """Generate prioritized to-do list."""
        parts = ["---\n\n## Prioritized To-Do List"]
        
        if not content.todo_items:
            parts.append("\n*To-do list will be generated based on the concerns above.*")
            return "\n".join(parts)
        
        # Group by priority
        critical = [t for t in content.todo_items if t.get("priority") == "critical"]
        high = [t for t in content.todo_items if t.get("priority") == "high"]
        medium = [t for t in content.todo_items if t.get("priority") == "medium"]
        low = [t for t in content.todo_items if t.get("priority") == "low"]
        
        if critical:
            parts.append("\n### 🔴 Critical (Must Fix)")
            for item in critical:
                effort = item.get("effort", "")
                effort_str = f" [{effort}]" if effort else ""
                parts.append(f"1. {item['task']}{effort_str}")
        
        if high:
            parts.append("\n### 🟠 High Priority")
            for item in high:
                effort = item.get("effort", "")
                effort_str = f" [{effort}]" if effort else ""
                parts.append(f"1. {item['task']}{effort_str}")
        
        if medium:
            parts.append("\n### 🟡 Medium Priority")
            for item in medium:
                effort = item.get("effort", "")
                effort_str = f" [{effort}]" if effort else ""
                parts.append(f"1. {item['task']}{effort_str}")
        
        if low:
            parts.append("\n### 🟢 Low Priority (Nice to Have)")
            for item in low:
                effort = item.get("effort", "")
                effort_str = f" [{effort}]" if effort else ""
                parts.append(f"1. {item['task']}{effort_str}")
        
        return "\n".join(parts)
    
    def _generate_footer(self, content: ReviewContent) -> str:
        """Generate report footer with metadata."""
        sources = ", ".join(content.sources_used) if content.sources_used else "Web search, Scopus"
        
        return f"""---

*Generated by Academic Referee Agent*  
*Journal analysis based on {content.articles_analyzed} recent publications*  
*Sources: {sources}*"""


def generate_report_tool(content_dict: dict, output_dir: str = "data/reviews") -> dict:
    """
    Tool function for Claude Agent SDK integration.
    
    Args:
        content_dict: Dictionary with review content
        output_dir: Directory to save report
        
    Returns:
        Dictionary with report path and content
    """
    try:
        # Convert dict to ReviewContent
        content = ReviewContent(
            paper_title=content_dict.get("paper_title", "Untitled"),
            paper_word_count=content_dict.get("paper_word_count", 0),
            paper_page_count=content_dict.get("paper_page_count", 0),
            journal_name=content_dict.get("journal_name", "Unknown Journal"),
            submission_type=content_dict.get("submission_type", "first_submission"),
            summary=content_dict.get("summary", ""),
            contribution=content_dict.get("contribution", ""),
            fit_assessment=content_dict.get("fit_assessment", ""),
            comparison_to_recent=content_dict.get("comparison_to_recent", ""),
            major_concerns=content_dict.get("major_concerns", []),
            minor_concerns=content_dict.get("minor_concerns", []),
            robustness_checklist=content_dict.get("robustness_checklist", []),
            section_analysis=content_dict.get("section_analysis", {}),
            positioning_strengths=content_dict.get("positioning_strengths", []),
            positioning_gaps=content_dict.get("positioning_gaps", []),
            editor_note=content_dict.get("editor_note", ""),
            todo_items=content_dict.get("todo_items", []),
            articles_analyzed=content_dict.get("articles_analyzed", 0),
            sources_used=content_dict.get("sources_used", [])
        )
        
        generator = ReportGenerator(output_dir)
        report_path = generator.save_report(content)
        report_content = generator.generate_report(content)
        
        return {
            "success": True,
            "path": report_path,
            "content": report_content
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
