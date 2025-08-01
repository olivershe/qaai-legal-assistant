"""
DIFC-first retrieval logic for QaAI RAG system.

Combines vector search with citation verification and jurisdiction filtering.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from core.models import JurisdictionType, InstrumentType, Citation
from rag.vector_store import vector_store, RetrievalMatch
from rag.citations import CitationCandidate, citation_verifier, create_verified_citation


@dataclass
class RetrievalContext:
    """Context for retrieval operations."""
    query: str
    jurisdiction: JurisdictionType = JurisdictionType.DIFC
    max_results: int = 10
    include_citations: bool = True
    boost_difc: bool = True
    hybrid_search: bool = True


class DIFCRetriever:
    """
    DIFC-focused retrieval system with citation verification.
    
    Implements the DIFC-first approach specified in requirements:
    - Boosts DIFC sources in retrieval
    - Verifies citations using binary match
    - Filters by jurisdiction when requested
    """
    
    def __init__(self):
        self.vector_store = vector_store
        self.citation_verifier = citation_verifier
    
    async def retrieve_with_citations(
        self,
        context: RetrievalContext
    ) -> tuple[List[RetrievalMatch], List[Citation]]:
        """
        Retrieve relevant documents and generate verified citations.
        
        Returns:
            tuple[List[RetrievalMatch], List[Citation]]: (matches, citations)
        """
        # Perform retrieval based on configuration
        if context.hybrid_search:
            matches = await self.vector_store.hybrid_search(
                query=context.query,
                limit=context.max_results
            )
        else:
            matches = await self.vector_store.search(
                query=context.query,
                limit=context.max_results,
                jurisdiction=context.jurisdiction,
                boost_difc=context.boost_difc
            )
        
        citations = []
        
        if context.include_citations and matches:
            # Convert matches to citation candidates
            candidates = []
            for match in matches:
                if match.chunk.metadata:
                    metadata = match.chunk.metadata
                    candidate = CitationCandidate(
                        title=metadata.get("title", "Unknown Document"),
                        section=match.chunk.section_ref,
                        url=metadata.get("url"),
                        jurisdiction=JurisdictionType(metadata.get("jurisdiction", "OTHER")),
                        instrument_type=InstrumentType(metadata.get("instrument_type", "OTHER")),
                        content_snippet=match.chunk.content[:200] + "..." if len(match.chunk.content) > 200 else match.chunk.content
                    )
                    candidates.append(candidate)
            
            # Verify citations
            if candidates:
                verification_results = self.citation_verifier.verify_batch(
                    [context.query] * len(candidates),
                    candidates
                )
                
                # Create verified citations
                for candidate, result in zip(candidates, verification_results):
                    if result.passed:
                        citation = create_verified_citation(context.query, result)
                        if citation:
                            citations.append(citation)
        
        return matches, citations
    
    async def search_vault_project(
        self,
        query: str,
        project_id: str,
        limit: int = 10
    ) -> List[RetrievalMatch]:
        """
        Search within specific Vault project.
        
        Filters results to only include documents from the specified project.
        """
        # Get all matches first
        matches = await self.vector_store.search(
            query=query,
            limit=limit * 2,  # Get more to account for filtering
            boost_difc=True
        )
        
        # Filter by project
        project_matches = []
        for match in matches:
            if match.chunk.metadata and match.chunk.metadata.get("project_id") == project_id:
                project_matches.append(match)
                if len(project_matches) >= limit:
                    break
        
        return project_matches
    
    async def get_related_documents(
        self,
        document_id: str,
        limit: int = 5
    ) -> List[RetrievalMatch]:
        """
        Find documents related to a specific document.
        
        Uses the document's content as a query to find similar documents.
        """
        # This would typically load the document and use its content as query
        # For now, return empty list as it requires document loading logic
        return []
    
    async def search_by_jurisdiction(
        self,
        query: str,
        jurisdiction: JurisdictionType,
        limit: int = 10
    ) -> List[RetrievalMatch]:
        """Search specifically within a jurisdiction."""
        return await self.vector_store.search(
            query=query,
            limit=limit,
            jurisdiction=jurisdiction,
            boost_difc=jurisdiction == JurisdictionType.DIFC
        )
    
    async def search_by_instrument_type(
        self,
        query: str,
        instrument_type: InstrumentType,
        jurisdiction: Optional[JurisdictionType] = None,
        limit: int = 10
    ) -> List[RetrievalMatch]:
        """
        Search within specific instrument type (Law, Regulation, etc.).
        
        Filters results by instrument type and optionally by jurisdiction.
        """
        matches = await self.vector_store.search(
            query=query,
            limit=limit * 2,
            jurisdiction=jurisdiction,
            boost_difc=True
        )
        
        # Filter by instrument type
        filtered_matches = []
        for match in matches:
            if match.chunk.metadata:
                chunk_instrument = match.chunk.metadata.get("instrument_type")
                if chunk_instrument == instrument_type.value:
                    filtered_matches.append(match)
                    if len(filtered_matches) >= limit:
                        break
        
        return filtered_matches
    
    def get_knowledge_sources_summary(self) -> Dict[str, Any]:
        """
        Get summary of available knowledge sources.
        
        Returns statistics about indexed documents by jurisdiction and type.
        """
        # This would query the database for statistics
        # For now, return basic vector store stats
        return {
            "vector_store_stats": self.vector_store.get_stats(),
            "citation_verifier_stats": self.citation_verifier.get_stats(),
            "default_sources": [
                "DIFC_LAWS",
                "DFSA_RULEBOOK", 
                "DIFC_COURTS_RULES",
                "VAULT"
            ]
        }


# Convenience functions for common operations
async def retrieve_with_citations(
    query: str,
    jurisdiction: JurisdictionType = JurisdictionType.DIFC,
    limit: int = 10
) -> tuple[List[RetrievalMatch], List[Citation]]:
    """Simple interface for retrieval with citations."""
    retriever = DIFCRetriever()
    context = RetrievalContext(
        query=query,
        jurisdiction=jurisdiction,
        max_results=limit
    )
    return await retriever.retrieve_with_citations(context)


async def search_difc_sources(
    query: str,
    limit: int = 10
) -> List[RetrievalMatch]:
    """Search specifically in DIFC sources with boosting."""
    retriever = DIFCRetriever()
    return await retriever.search_by_jurisdiction(
        query=query,
        jurisdiction=JurisdictionType.DIFC,
        limit=limit
    )


async def search_legal_instruments(
    query: str,
    instrument_types: List[InstrumentType],
    limit: int = 10
) -> List[RetrievalMatch]:
    """Search across multiple legal instrument types."""
    retriever = DIFCRetriever()
    all_matches = []
    
    for instrument_type in instrument_types:
        matches = await retriever.search_by_instrument_type(
            query=query,
            instrument_type=instrument_type,
            limit=limit // len(instrument_types) + 1
        )
        all_matches.extend(matches)
    
    # Sort by score and limit
    all_matches.sort(key=lambda x: x.score, reverse=True)
    return all_matches[:limit]


# Global retriever instance
difc_retriever = DIFCRetriever()