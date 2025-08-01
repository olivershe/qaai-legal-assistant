"""
Tests for RAG retrieval systems with DIFC-first filtering.

Following PRP requirements:
- Test vector operations and citation verification
- Include DIFC-first retrieval and jurisdiction filtering
- Test hybrid retrieval accuracy and performance
- Test retrieval context and metadata handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np
from typing import List, Dict, Any

from core.models import JurisdictionType, Citation
from rag.retrievers import DIFCRetriever, RetrievalContext
try:
    from rag.retrievers import HybridRetriever
except ImportError:
    HybridRetriever = None


class TestDIFCRetriever:
    """Test DIFC-first retrieval system."""
    
    @pytest.fixture
    def sample_retrieval_context(self) -> RetrievalContext:
        """Sample retrieval context for testing."""
        return RetrievalContext(
            query="employment law minimum notice period",
            jurisdiction=JurisdictionType.DIFC,
            boost_difc=True,
            max_results=10,
            min_similarity=0.7
        )
    
    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store with sample documents."""
        with patch('rag.vector_store.FAISSVectorStore') as mock_store:
            # Mock search results with DIFC and non-DIFC documents
            mock_store.return_value.similarity_search.return_value = [
                {
                    "content": "DIFC Employment Law requires 30 days notice for termination",
                    "metadata": {
                        "title": "DIFC Employment Law No. 2 of 2019",
                        "jurisdiction": "DIFC",
                        "section": "Part 4",
                        "instrument_type": "Law"
                    },
                    "score": 0.95
                },
                {
                    "content": "UAE Federal Labour Law states different termination requirements",
                    "metadata": {
                        "title": "UAE Federal Labour Law No. 8 of 1980",
                        "jurisdiction": "UAE", 
                        "section": "Article 120",
                        "instrument_type": "Law"
                    },
                    "score": 0.92
                },
                {
                    "content": "DFSA employment regulations for financial sector employees",
                    "metadata": {
                        "title": "DFSA General Rulebook",
                        "jurisdiction": "DFSA",
                        "section": "Chapter 8",
                        "instrument_type": "Rulebook"
                    },
                    "score": 0.88
                }
            ]
            yield mock_store
    
    def test_difc_retriever_initialization(self):
        """Test DIFC retriever initializes correctly."""
        retriever = DIFCRetriever()
        
        assert retriever is not None
        assert hasattr(retriever, 'vector_store')
        assert hasattr(retriever, 'citation_verifier')
    
    def test_retrieve_with_difc_first_ranking(self, sample_retrieval_context, mock_vector_store):
        """Test retrieval prioritizes DIFC sources."""
        retriever = DIFCRetriever()
        
        results, citations = retriever.retrieve_with_citations(sample_retrieval_context)
        
        # Should have retrieved results
        assert len(results) > 0
        assert len(citations) > 0
        
        # DIFC documents should be ranked higher
        difc_results = [r for r in results if r["metadata"]["jurisdiction"] == "DIFC"]
        assert len(difc_results) > 0
        
        # First result should be DIFC due to boosting
        assert results[0]["metadata"]["jurisdiction"] == "DIFC"
        
        # Verify citations include DIFC sources
        difc_citations = [c for c in citations if c.jurisdiction == JurisdictionType.DIFC]
        assert len(difc_citations) > 0
    
    def test_retrieve_with_jurisdiction_filtering(self, mock_vector_store):
        """Test retrieval with specific jurisdiction filtering."""
        retriever = DIFCRetriever()
        
        # Filter only DIFC documents
        context = RetrievalContext(
            query="employment standards",
            jurisdiction=JurisdictionType.DIFC,
            jurisdiction_filter="DIFC_ONLY",
            boost_difc=True
        )
        
        with patch.object(retriever, '_filter_by_jurisdiction') as mock_filter:
            mock_filter.return_value = [
                {
                    "content": "DIFC-only content",
                    "metadata": {"jurisdiction": "DIFC", "title": "DIFC Law"},
                    "score": 0.95
                }
            ]
            
            results, citations = retriever.retrieve_with_citations(context)
            
            # Should only return DIFC documents
            for result in results:
                assert result["metadata"]["jurisdiction"] == "DIFC"
    
    def test_retrieve_with_similarity_threshold(self, sample_retrieval_context, mock_vector_store):
        """Test retrieval respects similarity threshold."""
        retriever = DIFCRetriever()
        
        # Set high similarity threshold
        high_threshold_context = sample_retrieval_context
        high_threshold_context.min_similarity = 0.98
        
        with patch.object(retriever.vector_store, 'similarity_search') as mock_search:
            # Return results with varying similarity scores
            mock_search.return_value = [
                {"content": "Highly relevant", "metadata": {"jurisdiction": "DIFC"}, "score": 0.99},
                {"content": "Less relevant", "metadata": {"jurisdiction": "DIFC"}, "score": 0.85},
                {"content": "Not relevant", "metadata": {"jurisdiction": "UAE"}, "score": 0.60}
            ]
            
            results, citations = retriever.retrieve_with_citations(high_threshold_context)
            
            # Should only return high-similarity results
            for result in results:
                assert result["score"] >= 0.98
    
    def test_retrieve_with_max_results_limit(self, sample_retrieval_context, mock_vector_store):
        """Test retrieval respects max results limit."""
        retriever = DIFCRetriever()
        
        # Set low max results limit
        limited_context = sample_retrieval_context
        limited_context.max_results = 2
        
        results, citations = retriever.retrieve_with_citations(limited_context)
        
        # Should not exceed max results
        assert len(results) <= 2
        assert len(citations) <= 2
    
    def test_retrieve_empty_query_handling(self, mock_vector_store):
        """Test handling of empty query."""
        retriever = DIFCRetriever()
        
        empty_context = RetrievalContext(
            query="",
            jurisdiction=JurisdictionType.DIFC
        )
        
        results, citations = retriever.retrieve_with_citations(empty_context)
        
        # Should handle gracefully
        assert isinstance(results, list)
        assert isinstance(citations, list)
    
    def test_retrieve_no_results_found(self, mock_vector_store):
        """Test handling when no results match criteria."""
        retriever = DIFCRetriever()
        
        with patch.object(retriever.vector_store, 'similarity_search') as mock_search:
            mock_search.return_value = []  # No results
            
            context = RetrievalContext(
                query="nonexistent topic",
                jurisdiction=JurisdictionType.DIFC
            )
            
            results, citations = retriever.retrieve_with_citations(context)
            
            assert results == []
            assert citations == []


@pytest.mark.skip(reason="HybridRetriever not yet implemented")
class TestHybridRetriever:
    """Test hybrid retrieval combining multiple strategies."""
    
    @pytest.fixture
    def hybrid_retriever(self):
        """Hybrid retriever instance for testing."""
        return HybridRetriever()
    
    def test_hybrid_retriever_initialization(self, hybrid_retriever):
        """Test hybrid retriever initializes with multiple strategies."""
        assert hybrid_retriever is not None
        assert hasattr(hybrid_retriever, 'vector_retriever')
        assert hasattr(hybrid_retriever, 'keyword_retriever')
        assert hasattr(hybrid_retriever, 'fusion_weights')
    
    def test_hybrid_search_vector_keyword_fusion(self, hybrid_retriever):
        """Test hybrid search combines vector and keyword results."""
        context = RetrievalContext(
            query="DIFC employment law notice period",
            jurisdiction=JurisdictionType.DIFC,
            use_hybrid=True
        )
        
        with patch.object(hybrid_retriever.vector_retriever, 'retrieve_with_citations') as mock_vector, \
             patch.object(hybrid_retriever.keyword_retriever, 'retrieve_with_citations') as mock_keyword:
            
            # Mock vector results
            mock_vector.return_value = (
                [{
                    "content": "Vector-based result about DIFC employment",
                    "metadata": {"title": "DIFC Employment Law", "jurisdiction": "DIFC"},
                    "score": 0.95,
                    "source": "vector"
                }],
                [Citation(title="DIFC Employment Law", jurisdiction=JurisdictionType.DIFC, instrument_type="Law")]
            )
            
            # Mock keyword results
            mock_keyword.return_value = (
                [{
                    "content": "Keyword-based result about notice period",
                    "metadata": {"title": "DIFC Notice Requirements", "jurisdiction": "DIFC"},
                    "score": 0.88,
                    "source": "keyword"
                }],
                [Citation(title="DIFC Notice Requirements", jurisdiction=JurisdictionType.DIFC, instrument_type="Regulation")]
            )
            
            results, citations = hybrid_retriever.retrieve_with_citations(context)
            
            # Should combine results from both strategies
            assert len(results) > 0
            assert len(citations) > 0
            
            # Should have results from both sources
            sources = [r.get("source") for r in results]
            assert "vector" in sources or "keyword" in sources
    
    def test_hybrid_search_score_fusion(self, hybrid_retriever):
        """Test hybrid search properly fuses similarity scores."""
        context = RetrievalContext(
            query="employment termination",
            jurisdiction=JurisdictionType.DIFC,
            use_hybrid=True
        )
        
        with patch.object(hybrid_retriever, '_fuse_results') as mock_fusion:
            mock_fusion.return_value = [
                {
                    "content": "Fused result",
                    "metadata": {"jurisdiction": "DIFC"},
                    "fused_score": 0.92,
                    "vector_score": 0.89,
                    "keyword_score": 0.95
                }
            ]
            
            results, citations = hybrid_retriever.retrieve_with_citations(context)
            
            # Should call fusion method
            mock_fusion.assert_called_once()
            
            # Results should have fused scores
            for result in results:
                assert "fused_score" in result
    
    def test_hybrid_search_difc_priority_maintained(self, hybrid_retriever):
        """Test hybrid search maintains DIFC priority."""
        context = RetrievalContext(
            query="legal standards",
            jurisdiction=JurisdictionType.DIFC,
            boost_difc=True,
            use_hybrid=True
        )
        
        with patch.object(hybrid_retriever.vector_retriever, 'retrieve_with_citations') as mock_vector:
            mock_vector.return_value = (
                [
                    {"content": "DIFC content", "metadata": {"jurisdiction": "DIFC"}, "score": 0.85},
                    {"content": "UAE content", "metadata": {"jurisdiction": "UAE"}, "score": 0.90}
                ],
                [
                    Citation(title="DIFC Law", jurisdiction=JurisdictionType.DIFC, instrument_type="Law"),
                    Citation(title="UAE Law", jurisdiction=JurisdictionType.UAE, instrument_type="Law")
                ]
            )
            
            results, citations = hybrid_retriever.retrieve_with_citations(context)
            
            # DIFC results should be boosted and rank higher
            if len(results) >= 2:
                difc_results = [r for r in results if r["metadata"]["jurisdiction"] == "DIFC"]
                non_difc_results = [r for r in results if r["metadata"]["jurisdiction"] != "DIFC"]
                
                if difc_results and non_difc_results:
                    # DIFC should rank higher due to boosting
                    difc_rank = results.index(difc_results[0])
                    non_difc_rank = results.index(non_difc_results[0])
                    assert difc_rank < non_difc_rank


class TestCitationVerification:
    """Test citation verification and validation."""
    
    def test_verify_citations_with_vector_lookup(self):
        """Test citation verification using vector similarity."""
        from rag.citations import verify_citations_with_fallback
        
        draft_content = "This references DIFC Employment Law No. 2 of 2019, Part 4."
        citations = [
            Citation(
                title="DIFC Employment Law No. 2 of 2019",
                section="Part 4",
                jurisdiction=JurisdictionType.DIFC,
                instrument_type="Law"
            )
        ]
        
        with patch('rag.vector_store.FAISSVectorStore') as mock_store:
            mock_store.return_value.similarity_search.return_value = [
                {
                    "content": "DIFC Employment Law No. 2 of 2019 Part 4 contains employment standards",
                    "metadata": {
                        "title": "DIFC Employment Law No. 2 of 2019",
                        "section": "Part 4"
                    },
                    "score": 0.98
                }
            ]
            
            verified_citations = verify_citations_with_fallback(draft_content, citations)
            
            assert len(verified_citations) > 0
            assert verified_citations[0]["verified"] is True
            assert verified_citations[0]["confidence"] > 0.9
    
    def test_verify_citations_fuzzy_matching(self):
        """Test citation verification with fuzzy matching fallback."""
        from rag.citations import verify_citations_with_fallback
        
        draft_content = "References DIFC Employment Law 2019 Part Four."
        citations = [
            Citation(
                title="DIFC Employment Law No. 2 of 2019",
                section="Part 4",
                jurisdiction=JurisdictionType.DIFC,
                instrument_type="Law"
            )
        ]
        
        with patch('rag.vector_store.FAISSVectorStore') as mock_store:
            # No exact match found
            mock_store.return_value.similarity_search.return_value = []
            
            with patch('rag.citations.fuzzy_match_citation') as mock_fuzzy:
                mock_fuzzy.return_value = {
                    "verified": True,
                    "confidence": 0.82,
                    "match_type": "fuzzy",
                    "matched_title": "DIFC Employment Law No. 2 of 2019"
                }
                
                verified_citations = verify_citations_with_fallback(draft_content, citations)
                
                assert len(verified_citations) > 0
                assert verified_citations[0]["verified"] is True
                assert verified_citations[0]["match_type"] == "fuzzy"
    
    def test_verify_citations_invalid_reference(self):
        """Test verification of invalid citations."""
        from rag.citations import verify_citations_with_fallback
        
        draft_content = "References Non-existent Law No. 999 of 2025."
        citations = [
            Citation(
                title="Non-existent Law No. 999 of 2025",
                section="Unknown",
                jurisdiction=JurisdictionType.DIFC,
                instrument_type="Law"
            )
        ]
        
        with patch('rag.vector_store.FAISSVectorStore') as mock_store:
            mock_store.return_value.similarity_search.return_value = []  # No matches
            
            with patch('rag.citations.fuzzy_match_citation') as mock_fuzzy:
                mock_fuzzy.return_value = {
                    "verified": False,
                    "confidence": 0.1,
                    "error": "Citation not found in knowledge base"
                }
                
                verified_citations = verify_citations_with_fallback(draft_content, citations)
                
                assert len(verified_citations) > 0
                assert verified_citations[0]["verified"] is False
                assert "not found" in verified_citations[0]["error"]


class TestRetrievalPerformance:
    """Test retrieval system performance and optimization."""
    
    def test_retrieval_caching(self):
        """Test retrieval result caching."""
        retriever = DIFCRetriever()
        
        context = RetrievalContext(
            query="employment law",
            jurisdiction=JurisdictionType.DIFC
        )
        
        with patch.object(retriever, '_get_cached_results') as mock_cache:
            mock_cache.return_value = None  # No cache hit
            
            with patch.object(retriever, '_cache_results') as mock_cache_store:
                results, citations = retriever.retrieve_with_citations(context)
                
                # Should attempt to cache results
                mock_cache_store.assert_called_once()
    
    def test_retrieval_batch_processing(self):
        """Test batch processing of multiple queries."""
        retriever = DIFCRetriever()
        
        contexts = [
            RetrievalContext(query="employment law", jurisdiction=JurisdictionType.DIFC),
            RetrievalContext(query="contract law", jurisdiction=JurisdictionType.DIFC),
            RetrievalContext(query="corporate governance", jurisdiction=JurisdictionType.DFSA)
        ]
        
        with patch.object(retriever, 'retrieve_with_citations') as mock_retrieve:
            mock_retrieve.return_value = ([], [])
            
            batch_results = retriever.batch_retrieve(contexts)
            
            assert len(batch_results) == len(contexts)
            assert mock_retrieve.call_count == len(contexts)
    
    @pytest.mark.slow
    def test_retrieval_performance_benchmarks(self):
        """Test retrieval system meets performance benchmarks."""
        retriever = DIFCRetriever()
        
        context = RetrievalContext(
            query="comprehensive employment law analysis",
            jurisdiction=JurisdictionType.DIFC,
            max_results=20
        )
        
        import time
        
        with patch.object(retriever.vector_store, 'similarity_search') as mock_search:
            # Simulate realistic search time
            def slow_search(*args, **kwargs):
                time.sleep(0.1)  # 100ms simulation
                return [{"content": "test", "metadata": {"jurisdiction": "DIFC"}, "score": 0.9}]
            
            mock_search.side_effect = slow_search
            
            start_time = time.time()
            results, citations = retriever.retrieve_with_citations(context)
            end_time = time.time()
            
            # Should complete within reasonable time (2 seconds)
            execution_time = end_time - start_time
            assert execution_time < 2.0


@pytest.mark.integration
class TestRetrievalIntegration:
    """Integration tests for retrieval system."""
    
    def test_end_to_end_retrieval_workflow(self):
        """Test complete retrieval workflow with real components."""
        # This would test actual integration with vector store, models, etc.
        # Using mocks here but would use real components in full integration test
        
        retriever = DIFCRetriever()
        
        context = RetrievalContext(
            query="DIFC employment law minimum notice period requirements",
            jurisdiction=JurisdictionType.DIFC,
            boost_difc=True,
            max_results=5,
            min_similarity=0.7
        )
        
        with patch('rag.vector_store.FAISSVectorStore') as mock_store, \
             patch('rag.citations.verify_citations_with_fallback') as mock_verify:
            
            # Mock realistic retrieval results
            mock_store.return_value.similarity_search.return_value = [
                {
                    "content": "DIFC Employment Law No. 2 of 2019 requires minimum 30 days notice",
                    "metadata": {
                        "title": "DIFC Employment Law No. 2 of 2019",
                        "jurisdiction": "DIFC",
                        "section": "Part 4",
                        "instrument_type": "Law"
                    },
                    "score": 0.95
                }
            ]
            
            mock_verify.return_value = [
                {"title": "DIFC Employment Law No. 2 of 2019", "verified": True, "confidence": 0.95}
            ]
            
            results, citations = retriever.retrieve_with_citations(context)
            
            # Verify end-to-end workflow
            assert len(results) > 0
            assert len(citations) > 0
            assert results[0]["metadata"]["jurisdiction"] == "DIFC"
            assert citations[0].jurisdiction == JurisdictionType.DIFC
    
    def test_retrieval_with_multiple_jurisdictions(self):
        """Test retrieval across multiple jurisdictions with proper ranking."""
        retriever = DIFCRetriever()
        
        context = RetrievalContext(
            query="employment standards comparison",
            jurisdiction=JurisdictionType.DIFC,
            include_related_jurisdictions=True,
            boost_difc=True
        )
        
        with patch('rag.vector_store.FAISSVectorStore') as mock_store:
            mock_store.return_value.similarity_search.return_value = [
                {"content": "DIFC standards", "metadata": {"jurisdiction": "DIFC"}, "score": 0.85},
                {"content": "DFSA standards", "metadata": {"jurisdiction": "DFSA"}, "score": 0.90},
                {"content": "UAE standards", "metadata": {"jurisdiction": "UAE"}, "score": 0.92}
            ]
            
            results, citations = retriever.retrieve_with_citations(context)
            
            # Should include multiple jurisdictions but prioritize DIFC
            jurisdictions = [r["metadata"]["jurisdiction"] for r in results]
            assert "DIFC" in jurisdictions
            
            # DIFC should rank first due to boosting
            assert results[0]["metadata"]["jurisdiction"] == "DIFC"