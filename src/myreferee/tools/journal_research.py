"""
Journal Research Tool
Integrates with Scopus and ScienceDirect APIs for journal analysis.
Also uses web search for aims & scope and editorial guidelines.
"""

import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json
import re
from urllib.parse import quote


@dataclass
class JournalArticle:
    """Represents a journal article from Scopus/ScienceDirect."""
    title: str
    authors: List[str]
    abstract: str
    publication_date: str
    doi: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    citation_count: int = 0
    methodology_keywords: List[str] = field(default_factory=list)


@dataclass
class JournalProfile:
    """Comprehensive profile of a journal based on research."""
    name: str
    issn: Optional[str] = None
    aims_scope: str = ""
    editorial_guidelines: str = ""
    recent_articles: List[JournalArticle] = field(default_factory=list)
    
    # Inferred referee priors
    typical_methods: List[str] = field(default_factory=list)
    contribution_framing: str = ""
    robustness_expectations: str = ""
    common_concerns: List[str] = field(default_factory=list)
    writing_style: str = ""
    
    # Metadata
    articles_analyzed: int = 0
    research_date: str = ""
    sources_used: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "issn": self.issn,
            "aims_scope": self.aims_scope,
            "editorial_guidelines": self.editorial_guidelines,
            "recent_articles": [
                {
                    "title": a.title,
                    "authors": a.authors,
                    "abstract": a.abstract[:500] + "..." if len(a.abstract) > 500 else a.abstract,
                    "date": a.publication_date,
                    "keywords": a.keywords
                }
                for a in self.recent_articles[:10]  # Limit for serialization
            ],
            "referee_priors": {
                "typical_methods": self.typical_methods,
                "contribution_framing": self.contribution_framing,
                "robustness_expectations": self.robustness_expectations,
                "common_concerns": self.common_concerns,
                "writing_style": self.writing_style
            },
            "articles_analyzed": self.articles_analyzed,
            "research_date": self.research_date,
            "sources_used": self.sources_used
        }


class ElsevierAPIClient:
    """Client for Scopus and ScienceDirect APIs."""
    
    SCOPUS_BASE = "https://api.elsevier.com/content/search/scopus"
    SCIDIR_BASE = "https://api.elsevier.com/content/search/sciencedirect"
    
    # Common econometric/empirical methods in economics/finance
    METHOD_KEYWORDS = [
        "difference-in-differences", "diff-in-diff", "DID",
        "instrumental variable", "IV", "2SLS", "two-stage",
        "regression discontinuity", "RDD", "RD design",
        "panel data", "fixed effects", "random effects",
        "GMM", "generalized method of moments",
        "propensity score", "matching",
        "event study", "abnormal returns",
        "DSGE", "dynamic stochastic",
        "VAR", "vector autoregression",
        "structural estimation", "maximum likelihood",
        "Bayesian", "MCMC",
        "machine learning", "LASSO", "random forest",
        "natural experiment", "quasi-experiment",
        "synthetic control",
        "bunching", "kink",
        "triple difference", "DDD"
    ]
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "X-ELS-APIKey": api_key,
            "Accept": "application/json"
        }
    
    async def search_scopus(
        self,
        journal_name: str,
        years_back: int = 5,
        max_results: int = 30
    ) -> List[JournalArticle]:
        """
        Search Scopus for recent articles in a journal.
        
        Args:
            journal_name: Name of the journal
            years_back: How many years back to search
            max_results: Maximum number of results
            
        Returns:
            List of JournalArticle objects
        """
        articles = []
        
        # Build date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years_back * 365)
        
        # Build query
        query = f'SRCTITLE("{journal_name}") AND PUBYEAR > {start_date.year - 1}'
        
        params = {
            "query": query,
            "count": min(max_results, 25),  # Scopus limit per request
            "sort": "-coverDate",  # Most recent first
            "field": "dc:title,dc:creator,prism:coverDate,dc:description,authkeywords,citedby-count,prism:doi"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    self.SCOPUS_BASE,
                    headers=self.headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("search-results", {}).get("entry", [])
                        
                        for entry in results:
                            article = self._parse_scopus_entry(entry)
                            if article:
                                articles.append(article)
                    else:
                        # Log error but don't fail
                        error_text = await response.text()
                        print(f"Scopus API error {response.status}: {error_text[:200]}")
                        
            except Exception as e:
                print(f"Scopus search error: {e}")
        
        return articles
    
    def _parse_scopus_entry(self, entry: dict) -> Optional[JournalArticle]:
        """Parse a Scopus search result entry."""
        try:
            title = entry.get("dc:title", "")
            if not title:
                return None
            
            # Parse authors
            authors = []
            creator = entry.get("dc:creator", "")
            if creator:
                authors = [creator]
            
            # Parse keywords
            keywords = []
            auth_keywords = entry.get("authkeywords", "")
            if auth_keywords:
                keywords = [k.strip() for k in auth_keywords.split("|")]
            
            # Parse abstract
            abstract = entry.get("dc:description", "")
            
            # Identify methodology keywords
            full_text = f"{title} {abstract} {' '.join(keywords)}".lower()
            methodology = [
                method for method in self.METHOD_KEYWORDS
                if method.lower() in full_text
            ]
            
            return JournalArticle(
                title=title,
                authors=authors,
                abstract=abstract,
                publication_date=entry.get("prism:coverDate", ""),
                doi=entry.get("prism:doi"),
                keywords=keywords,
                citation_count=int(entry.get("citedby-count", 0)),
                methodology_keywords=methodology
            )
        except Exception as e:
            print(f"Error parsing Scopus entry: {e}")
            return None
    
    async def get_journal_metrics(self, journal_name: str) -> dict:
        """Get journal-level metrics if available."""
        # Note: Full journal metrics require Scopus Source API
        # This is a simplified version using search results
        return {
            "name": journal_name,
            "note": "Full metrics require Scopus Source API subscription"
        }


class JournalResearcher:
    """
    Comprehensive journal research combining API data and web search.
    """
    
    def __init__(self, elsevier_api_key: str):
        self.elsevier_client = ElsevierAPIClient(elsevier_api_key)
    
    async def research_journal(
        self,
        journal_name: str,
        years_back: int = 5,
        min_articles: int = 20,
        max_articles: int = 40
    ) -> JournalProfile:
        """
        Conduct comprehensive research on a journal.
        
        Args:
            journal_name: Name of the target journal
            years_back: How many years of articles to analyze
            min_articles: Minimum articles needed for analysis
            max_articles: Maximum articles to retrieve
            
        Returns:
            JournalProfile with aims, articles, and inferred referee priors
        """
        profile = JournalProfile(
            name=journal_name,
            research_date=datetime.now().isoformat()
        )
        
        # 1. Get recent articles from Scopus
        articles = await self.elsevier_client.search_scopus(
            journal_name,
            years_back=years_back,
            max_results=max_articles
        )
        
        profile.recent_articles = articles
        profile.articles_analyzed = len(articles)
        profile.sources_used.append("Scopus")
        
        # 2. Infer referee priors from articles
        if articles:
            profile = self._infer_referee_priors(profile, articles)
        
        return profile
    
    def _infer_referee_priors(
        self,
        profile: JournalProfile,
        articles: List[JournalArticle]
    ) -> JournalProfile:
        """Infer referee priors from the article corpus."""
        
        # Count methodology occurrences
        method_counts = {}
        all_keywords = []
        
        for article in articles:
            for method in article.methodology_keywords:
                method_counts[method] = method_counts.get(method, 0) + 1
            all_keywords.extend(article.keywords)
        
        # Sort methods by frequency
        sorted_methods = sorted(
            method_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        profile.typical_methods = [m[0] for m in sorted_methods[:10]]
        
        # Infer contribution framing from titles and abstracts
        framing_patterns = self._analyze_framing(articles)
        profile.contribution_framing = framing_patterns
        
        # Infer robustness expectations
        profile.robustness_expectations = self._infer_robustness(articles)
        
        # Infer common concerns (based on typical patterns)
        profile.common_concerns = self._infer_concerns(profile.typical_methods)
        
        # Analyze writing style
        profile.writing_style = self._analyze_style(articles)
        
        return profile
    
    def _analyze_framing(self, articles: List[JournalArticle]) -> str:
        """Analyze how contributions are framed in titles/abstracts."""
        framing_indicators = {
            "causal": ["effect of", "impact of", "causes", "causal"],
            "descriptive": ["patterns", "trends", "documenting", "evidence on"],
            "theoretical": ["model of", "theory of", "framework for"],
            "policy": ["policy implications", "welfare", "regulation"],
            "methodological": ["new method", "estimation", "identification"]
        }
        
        counts = {k: 0 for k in framing_indicators}
        
        for article in articles:
            text = f"{article.title} {article.abstract}".lower()
            for category, keywords in framing_indicators.items():
                if any(kw in text for kw in keywords):
                    counts[category] += 1
        
        # Build framing summary
        total = len(articles) or 1
        framing_parts = []
        for category, count in sorted(counts.items(), key=lambda x: -x[1]):
            if count > 0:
                pct = (count / total) * 100
                framing_parts.append(f"{category} ({pct:.0f}%)")
        
        return "Contribution framing: " + ", ".join(framing_parts[:4])
    
    def _infer_robustness(self, articles: List[JournalArticle]) -> str:
        """Infer expected robustness checks."""
        robustness_keywords = {
            "placebo tests": ["placebo", "falsification"],
            "sensitivity analysis": ["sensitivity", "robustness"],
            "alternative specifications": ["alternative", "specification"],
            "subsample analysis": ["subsample", "heterogeneity"],
            "instrument validity": ["overidentification", "weak instrument", "first stage"],
            "parallel trends": ["parallel trend", "pre-trend"],
            "bootstrap": ["bootstrap", "clustered standard errors"]
        }
        
        found_robustness = []
        for article in articles:
            text = f"{article.title} {article.abstract}".lower()
            for check, keywords in robustness_keywords.items():
                if any(kw in text for kw in keywords):
                    if check not in found_robustness:
                        found_robustness.append(check)
        
        if found_robustness:
            return f"Commonly expected: {', '.join(found_robustness)}"
        return "Standard robustness checks expected"
    
    def _infer_concerns(self, typical_methods: List[str]) -> List[str]:
        """Infer common referee concerns based on methods used."""
        concerns_by_method = {
            "instrumental variable": [
                "Exclusion restriction validity",
                "First-stage strength (F > 10)",
                "Instrument relevance"
            ],
            "difference-in-differences": [
                "Parallel trends assumption",
                "Treatment timing variation",
                "Anticipation effects"
            ],
            "regression discontinuity": [
                "Manipulation at cutoff",
                "Bandwidth sensitivity",
                "Local randomization"
            ],
            "panel data": [
                "Unobserved heterogeneity",
                "Serial correlation",
                "Cluster-robust standard errors"
            ],
            "event study": [
                "Event timing precision",
                "Confounding events",
                "Pre-event trends"
            ]
        }
        
        concerns = []
        for method in typical_methods:
            method_lower = method.lower()
            for key, method_concerns in concerns_by_method.items():
                if key in method_lower:
                    concerns.extend(method_concerns)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_concerns = []
        for c in concerns:
            if c not in seen:
                seen.add(c)
                unique_concerns.append(c)
        
        return unique_concerns[:8]  # Top concerns
    
    def _analyze_style(self, articles: List[JournalArticle]) -> str:
        """Analyze writing style from abstracts."""
        if not articles:
            return "Standard academic style"
        
        # Analyze abstract lengths
        abstract_lengths = [len(a.abstract.split()) for a in articles if a.abstract]
        avg_length = sum(abstract_lengths) / len(abstract_lengths) if abstract_lengths else 0
        
        # Check for common patterns
        uses_first_person = sum(
            1 for a in articles 
            if any(p in a.abstract.lower() for p in [" we ", " our ", " i "])
        )
        first_person_pct = (uses_first_person / len(articles)) * 100 if articles else 0
        
        style_notes = []
        
        if avg_length < 150:
            style_notes.append("concise abstracts")
        elif avg_length > 250:
            style_notes.append("detailed abstracts")
        
        if first_person_pct > 70:
            style_notes.append("first person common")
        elif first_person_pct < 30:
            style_notes.append("passive voice preferred")
        
        return ", ".join(style_notes) if style_notes else "Standard academic style"


async def research_journal_tool(
    journal_name: str,
    elsevier_api_key: str,
    years_back: int = 5,
    max_articles: int = 30
) -> dict:
    """
    Tool function for Claude Agent SDK integration.
    
    Args:
        journal_name: Name of the target journal
        elsevier_api_key: Elsevier API key
        years_back: Years of history to analyze
        max_articles: Maximum articles to retrieve
        
    Returns:
        Dictionary with journal profile
    """
    try:
        researcher = JournalResearcher(elsevier_api_key)
        profile = await researcher.research_journal(
            journal_name,
            years_back=years_back,
            max_articles=max_articles
        )
        return {
            "success": True,
            "profile": profile.to_dict()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
