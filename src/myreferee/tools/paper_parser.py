"""
Paper Parser Tool
Extracts text and structure from PDF, Word, and LaTeX files.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# PDF parsing
try:
    import pdfplumber
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Word parsing
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# LaTeX parsing
try:
    from pylatexenc.latex2text import LatexNodes2Text
    LATEX_AVAILABLE = True
except ImportError:
    LATEX_AVAILABLE = False


@dataclass
class ParsedPaper:
    """Structured representation of a parsed academic paper."""
    title: str
    abstract: str
    sections: Dict[str, str]
    full_text: str
    metadata: Dict[str, any]
    word_count: int
    page_count: int
    source_format: str
    file_path: str
    
    def get_section(self, section_name: str) -> Optional[str]:
        """Get a section by name (case-insensitive partial match)."""
        section_lower = section_name.lower()
        for name, content in self.sections.items():
            if section_lower in name.lower():
                return content
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "abstract": self.abstract,
            "sections": self.sections,
            "word_count": self.word_count,
            "page_count": self.page_count,
            "source_format": self.source_format,
            "metadata": self.metadata
        }


class PaperParser:
    """
    Multi-format academic paper parser.
    Supports PDF, Word (.docx), and LaTeX (.tex) files.
    """
    
    # Common section headers in economics/finance papers
    SECTION_PATTERNS = [
        r'^(?:I{1,3}V?|[1-9])\.\s*(.+)$',  # Roman numerals or numbers
        r'^(?:Chapter|Section)\s+\d+[.:]\s*(.+)$',
        r'^([A-Z][A-Za-z\s]+)$',  # All-caps or title case headers
    ]
    
    COMMON_SECTIONS = [
        "introduction", "literature", "review", "background",
        "data", "methodology", "method", "model", "empirical",
        "results", "findings", "analysis", "discussion",
        "conclusion", "references", "appendix", "tables", "figures"
    ]
    
    def __init__(self, max_size_mb: int = 50):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check which parsing libraries are available."""
        self.capabilities = {
            "pdf": PDF_AVAILABLE,
            "docx": DOCX_AVAILABLE,
            "latex": LATEX_AVAILABLE
        }
    
    def parse(self, file_path: str) -> ParsedPaper:
        """
        Parse a paper file and extract structured content.
        
        Args:
            file_path: Path to the paper file
            
        Returns:
            ParsedPaper object with extracted content
            
        Raises:
            ValueError: If file format not supported or file too large
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if path.stat().st_size > self.max_size_bytes:
            raise ValueError(f"File too large (max {self.max_size_bytes // (1024*1024)} MB)")
        
        suffix = path.suffix.lower()
        
        if suffix == ".pdf":
            return self._parse_pdf(path)
        elif suffix in [".docx", ".doc"]:
            return self._parse_docx(path)
        elif suffix == ".tex":
            return self._parse_latex(path)
        else:
            raise ValueError(f"Unsupported format: {suffix}")
    
    def _parse_pdf(self, path: Path) -> ParsedPaper:
        """Parse a PDF file."""
        if not PDF_AVAILABLE:
            raise ImportError("PDF parsing requires: pip install pdfplumber pypdf")
        
        full_text = []
        page_count = 0
        
        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text.append(text)
        
        combined_text = "\n\n".join(full_text)
        
        # Extract structure
        title = self._extract_title(combined_text)
        abstract = self._extract_abstract(combined_text)
        sections = self._extract_sections(combined_text)
        
        # Get metadata from pypdf
        metadata = {}
        try:
            reader = PdfReader(path)
            if reader.metadata:
                metadata = {
                    "author": reader.metadata.get("/Author", ""),
                    "subject": reader.metadata.get("/Subject", ""),
                    "keywords": reader.metadata.get("/Keywords", ""),
                }
        except:
            pass
        
        return ParsedPaper(
            title=title,
            abstract=abstract,
            sections=sections,
            full_text=combined_text,
            metadata=metadata,
            word_count=len(combined_text.split()),
            page_count=page_count,
            source_format="pdf",
            file_path=str(path)
        )
    
    def _parse_docx(self, path: Path) -> ParsedPaper:
        """Parse a Word document."""
        if not DOCX_AVAILABLE:
            raise ImportError("Word parsing requires: pip install python-docx")
        
        doc = DocxDocument(path)
        
        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text)
        
        combined_text = "\n\n".join(paragraphs)
        
        # Extract structure
        title = self._extract_title(combined_text)
        abstract = self._extract_abstract(combined_text)
        sections = self._extract_sections(combined_text)
        
        # Estimate page count (rough: ~500 words per page)
        word_count = len(combined_text.split())
        page_count = max(1, word_count // 500)
        
        # Get metadata
        metadata = {}
        try:
            core_props = doc.core_properties
            metadata = {
                "author": core_props.author or "",
                "subject": core_props.subject or "",
                "keywords": core_props.keywords or "",
            }
        except:
            pass
        
        return ParsedPaper(
            title=title,
            abstract=abstract,
            sections=sections,
            full_text=combined_text,
            metadata=metadata,
            word_count=word_count,
            page_count=page_count,
            source_format="docx",
            file_path=str(path)
        )
    
    def _parse_latex(self, path: Path) -> ParsedPaper:
        """Parse a LaTeX file."""
        if not LATEX_AVAILABLE:
            raise ImportError("LaTeX parsing requires: pip install pylatexenc")
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            latex_content = f.read()
        
        # Convert LaTeX to plain text
        converter = LatexNodes2Text()
        plain_text = converter.latex_to_text(latex_content)
        
        # Also extract from raw LaTeX for better structure detection
        title = self._extract_latex_title(latex_content) or self._extract_title(plain_text)
        abstract = self._extract_latex_abstract(latex_content) or self._extract_abstract(plain_text)
        sections = self._extract_latex_sections(latex_content, plain_text)
        
        # Get metadata from LaTeX commands
        metadata = self._extract_latex_metadata(latex_content)
        
        word_count = len(plain_text.split())
        page_count = max(1, word_count // 500)
        
        return ParsedPaper(
            title=title,
            abstract=abstract,
            sections=sections,
            full_text=plain_text,
            metadata=metadata,
            word_count=word_count,
            page_count=page_count,
            source_format="latex",
            file_path=str(path)
        )
    
    def _extract_title(self, text: str) -> str:
        """Extract title from the beginning of the document."""
        lines = text.strip().split('\n')
        
        # Usually the title is in the first few non-empty lines
        for line in lines[:10]:
            line = line.strip()
            if len(line) > 10 and len(line) < 300:
                # Skip obvious non-titles
                if not any(skip in line.lower() for skip in 
                          ['abstract', 'keywords', 'jel', 'email', '@', 'university']):
                    return line
        
        return "Untitled Paper"
    
    def _extract_abstract(self, text: str) -> str:
        """Extract abstract from the document."""
        # Look for explicit abstract section
        patterns = [
            r'(?:^|\n)\s*Abstract[:\s]*\n(.*?)(?=\n\s*(?:Keywords|JEL|Introduction|1\.|I\.))',
            r'(?:^|\n)\s*ABSTRACT[:\s]*\n(.*?)(?=\n\s*(?:KEYWORDS|JEL|INTRODUCTION|1\.|I\.))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                # Clean up and limit length
                abstract = re.sub(r'\s+', ' ', abstract)
                return abstract[:2000] if len(abstract) > 2000 else abstract
        
        return ""
    
    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract sections from the document."""
        sections = {}
        
        # Split by common section patterns
        section_pattern = r'\n\s*(?:(?:I{1,3}V?|[1-9])\.\s+)?([A-Z][A-Za-z\s]+)\s*\n'
        
        matches = list(re.finditer(section_pattern, text))
        
        for i, match in enumerate(matches):
            section_name = match.group(1).strip()
            
            # Check if it's a real section
            if any(common in section_name.lower() for common in self.COMMON_SECTIONS):
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                content = text[start:end].strip()
                
                # Limit section length for processing
                if len(content) > 15000:
                    content = content[:15000] + "\n[... truncated ...]"
                
                sections[section_name] = content
        
        return sections
    
    def _extract_latex_title(self, latex: str) -> Optional[str]:
        """Extract title from LaTeX \\title{} command."""
        match = re.search(r'\\title\{([^}]+)\}', latex)
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_latex_abstract(self, latex: str) -> Optional[str]:
        """Extract abstract from LaTeX abstract environment."""
        match = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', latex, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_latex_sections(self, latex: str, plain_text: str) -> Dict[str, str]:
        """Extract sections from LaTeX \\section{} commands."""
        sections = {}
        
        # Find all \section commands
        pattern = r'\\section\{([^}]+)\}'
        matches = list(re.finditer(pattern, latex))
        
        for i, match in enumerate(matches):
            section_name = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(latex)
            
            # Convert section content to plain text
            content_latex = latex[start:end]
            converter = LatexNodes2Text()
            content = converter.latex_to_text(content_latex).strip()
            
            if len(content) > 15000:
                content = content[:15000] + "\n[... truncated ...]"
            
            sections[section_name] = content
        
        # Fallback to plain text extraction if no LaTeX sections found
        if not sections:
            sections = self._extract_sections(plain_text)
        
        return sections
    
    def _extract_latex_metadata(self, latex: str) -> Dict[str, str]:
        """Extract metadata from LaTeX commands."""
        metadata = {}
        
        # Author
        author_match = re.search(r'\\author\{([^}]+)\}', latex)
        if author_match:
            metadata["author"] = author_match.group(1).strip()
        
        # Keywords
        keywords_match = re.search(r'\\keywords\{([^}]+)\}', latex)
        if keywords_match:
            metadata["keywords"] = keywords_match.group(1).strip()
        
        # JEL codes
        jel_match = re.search(r'(?:JEL|jel)[:\s]*([A-Z]\d{2}(?:,\s*[A-Z]\d{2})*)', latex)
        if jel_match:
            metadata["jel_codes"] = jel_match.group(1).strip()
        
        return metadata


def parse_paper(file_path: str) -> ParsedPaper:
    """
    Convenience function to parse a paper file.
    
    Args:
        file_path: Path to the paper (PDF, Word, or LaTeX)
        
    Returns:
        ParsedPaper object
    """
    parser = PaperParser()
    return parser.parse(file_path)


# For use as a Claude Agent SDK tool
async def paper_parser_tool(file_path: str) -> dict:
    """
    Tool function for Claude Agent SDK integration.
    
    Args:
        file_path: Path to the paper file
        
    Returns:
        Dictionary with parsed paper content
    """
    try:
        paper = parse_paper(file_path)
        return {
            "success": True,
            "paper": paper.to_dict()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
