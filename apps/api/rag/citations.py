"""
Citation verification using binary match approach.

Extends examples/citations_check.py with:
- Jaccard similarity with 0.25 threshold
- Jurisdiction-aware citation verification
- Support for multiple citation candidates
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from core.models import Citation, JurisdictionType, InstrumentType


@dataclass
class CitationCandidate:
    """Candidate source for citation verification."""
    title: str
    section: Optional[str] = None
    url: Optional[str] = None
    jurisdiction: JurisdictionType = JurisdictionType.DIFC
    instrument_type: InstrumentType = InstrumentType.OTHER
    content_snippet: Optional[str] = None


@dataclass 
class VerificationResult:
    """Result of citation verification."""
    passed: bool
    score: float
    best_candidate: Optional[CitationCandidate]
    all_scores: List[tuple[CitationCandidate, float]]


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.
    
    Following examples/citations_check.py pattern with enhancements.
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation and special characters
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    
    return text


def jaccard_similarity(text1: str, text2: str) -> float:
    """
    Calculate Jaccard similarity between two texts.
    
    Following examples/citations_check.py implementation.
    """
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    
    if not norm1 or not norm2:
        return 0.0
    
    set1 = set(norm1.split())
    set2 = set(norm2.split())
    
    if not set1 or not set2:
        return 0.0
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0


def extract_legal_terms(text: str) -> set[str]:
    """Extract legal terms and phrases for enhanced matching."""
    legal_patterns = [
        r'\b(article|section|part|chapter|clause|paragraph|subsection)\s+\d+[a-z]?\b',
        r'\b(law|regulation|rule|act|code|statute|ordinance)\b',
        r'\b(difc|dfsa|uae|dubai|emirates)\b',
        r'\b(employment|data\s+protection|commercial|corporate|financial)\b',
        r'\b(shall|must|may|required|prohibited|permitted)\b'
    ]
    
    terms = set()
    text_lower = text.lower()
    
    for pattern in legal_patterns:
        matches = re.findall(pattern, text_lower)
        terms.update(matches)
    
    return terms


def enhanced_similarity(claim: str, candidate: CitationCandidate) -> float:
    """
    Enhanced similarity calculation with legal term weighting.
    
    Combines Jaccard similarity with legal term matching for better accuracy.
    """
    if not claim or not candidate.title:
        return 0.0
    
    # Basic Jaccard similarities
    title_score = jaccard_similarity(claim, candidate.title)
    section_score = jaccard_similarity(claim, candidate.section or "") if candidate.section else 0.0
    combined_score = jaccard_similarity(claim, f"{candidate.title} {candidate.section or ''}")
    
    # Legal term matching bonus
    claim_terms = extract_legal_terms(claim)
    candidate_terms = extract_legal_terms(f"{candidate.title} {candidate.section or ''}")
    
    term_overlap = len(claim_terms & candidate_terms) / len(claim_terms | candidate_terms) if claim_terms or candidate_terms else 0.0
    
    # Weighted combination
    base_score = max(title_score, section_score, combined_score)
    enhanced_score = base_score * 0.7 + term_overlap * 0.3
    
    return min(enhanced_score, 1.0)


def verify_citation(
    claim: str,
    candidates: List[CitationCandidate],
    threshold: float = 0.25,
    jurisdiction_boost: float = 0.1
) -> VerificationResult:
    """
    Verify citation against candidate sources.
    
    Args:
        claim: The claim text to verify
        candidates: List of potential source documents
        threshold: Minimum similarity score to pass verification
        jurisdiction_boost: Score boost for matching jurisdiction
    
    Returns:
        VerificationResult with best match and scores
    """
    if not claim or not candidates:
        return VerificationResult(
            passed=False,
            score=0.0,
            best_candidate=None,
            all_scores=[]
        )
    
    scored_candidates = []
    
    for candidate in candidates:
        # Calculate base similarity
        base_score = enhanced_similarity(claim, candidate)
        
        # Apply jurisdiction boost for DIFC sources (DIFC-first approach)
        final_score = base_score
        if candidate.jurisdiction == JurisdictionType.DIFC:
            final_score += jurisdiction_boost
        
        # Cap at 1.0
        final_score = min(final_score, 1.0)
        
        scored_candidates.append((candidate, final_score))
    
    # Sort by score descending
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    
    best_candidate, best_score = scored_candidates[0] if scored_candidates else (None, 0.0)
    
    return VerificationResult(
        passed=best_score >= threshold,
        score=round(best_score, 3),
        best_candidate=best_candidate,
        all_scores=[(cand, round(score, 3)) for cand, score in scored_candidates]
    )


def batch_verify_citations(
    claims: List[str],
    candidates: List[CitationCandidate],
    threshold: float = 0.25
) -> List[VerificationResult]:
    """Verify multiple citations efficiently."""
    return [
        verify_citation(claim, candidates, threshold)
        for claim in claims
    ]


def create_verified_citation(
    claim: str,
    verification_result: VerificationResult
) -> Optional[Citation]:
    """
    Create Citation object from verification result.
    
    Only creates citation if verification passed.
    """
    if not verification_result.passed or not verification_result.best_candidate:
        return None
    
    candidate = verification_result.best_candidate
    
    return Citation(
        title=candidate.title,
        section=candidate.section,
        url=candidate.url,
        instrument_type=candidate.instrument_type,
        jurisdiction=candidate.jurisdiction
    )


class CitationVerifier:
    """
    Citation verification service with caching and batch processing.
    """
    
    def __init__(self, threshold: float = None):
        self.threshold = threshold or 0.25
        self._verification_cache: Dict[str, VerificationResult] = {}
    
    def verify(
        self,
        claim: str,
        candidates: List[CitationCandidate],
        use_cache: bool = True
    ) -> VerificationResult:
        """Verify single citation with optional caching."""
        cache_key = f"{hash(claim)}_{hash(tuple(c.title for c in candidates))}"
        
        if use_cache and cache_key in self._verification_cache:
            return self._verification_cache[cache_key]
        
        result = verify_citation(claim, candidates, self.threshold)
        
        if use_cache:
            self._verification_cache[cache_key] = result
        
        return result
    
    def verify_batch(
        self,
        claims: List[str],
        candidates: List[CitationCandidate]
    ) -> List[VerificationResult]:
        """Verify multiple citations."""
        return batch_verify_citations(claims, candidates, self.threshold)
    
    def filter_valid_citations(
        self,
        claims: List[str],
        candidates: List[CitationCandidate]
    ) -> List[Citation]:
        """Return only citations that pass verification."""
        results = self.verify_batch(claims, candidates)
        
        valid_citations = []
        for claim, result in zip(claims, results):
            citation = create_verified_citation(claim, result)
            if citation:
                valid_citations.append(citation)
        
        return valid_citations
    
    def get_stats(self) -> Dict[str, Any]:
        """Get verification statistics."""
        return {
            "threshold": self.threshold,
            "cache_size": len(self._verification_cache),
            "total_verifications": len(self._verification_cache)
        }
    
    def clear_cache(self):
        """Clear verification cache."""
        self._verification_cache.clear()


# Global verifier instance
citation_verifier = CitationVerifier(threshold=0.25)