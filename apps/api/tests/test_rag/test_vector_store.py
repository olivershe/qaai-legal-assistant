"""
Tests for vector store operations and document indexing.

Following PRP requirements:
- Test vector operations and document indexing
- Test FAISS integration and similarity search
- Test document chunking and embedding generation
- Test vector store persistence and optimization
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from core.models import DocumentMetadata, JurisdictionType
from rag.vector_store import FAISSVectorStore, DocumentChunker


class TestFAISSVectorStore:
    """Test FAISS vector store operations."""
    
    @pytest.fixture
    def sample_documents(self) -> List[DocumentMetadata]:
        """Sample documents for testing."""
        return [
            DocumentMetadata(
                id="doc-difc-1",
                project_id="test-project",
                filename="difc_employment_law.pdf",
                title="DIFC Employment Law No. 2 of 2019",
                file_path="/data/files/difc_employment_law.pdf",
                content_type="application/pdf",
                size_bytes=50000,
                jurisdiction=JurisdictionType.DIFC,
                instrument_type="Law",
                upload_date="2024-01-01T00:00:00Z"
            ),
            DocumentMetadata(
                id="doc-dfsa-1",
                project_id="test-project",
                filename="dfsa_rulebook.pdf",
                title="DFSA General Rulebook",
                file_path="/data/files/dfsa_rulebook.pdf",
                content_type="application/pdf",
                size_bytes=75000,
                jurisdiction=JurisdictionType.DFSA,
                instrument_type="Rulebook",
                upload_date="2024-01-01T00:00:00Z"
            )
        ]
    
    @pytest.fixture
    def vector_store(self):
        """FAISS vector store instance for testing."""
        return FAISSVectorStore(dimension=384, index_type="flat")
    
    def test_vector_store_initialization(self, vector_store):
        """Test vector store initializes correctly."""
        assert vector_store is not None
        assert vector_store.dimension == 384
        assert vector_store.index_type == "flat"
        assert hasattr(vector_store, 'index')
        assert hasattr(vector_store, 'metadata_store')
    
    def test_add_document_to_vector_store(self, vector_store, sample_documents):
        """Test adding document to vector store."""
        document = sample_documents[0]
        
        # Mock document content and embeddings
        document_chunks = [
            {
                "content": "DIFC Employment Law requires minimum 30 days notice",
                "metadata": {
                    "document_id": document.id,
                    "chunk_id": 0,
                    "title": document.title,
                    "jurisdiction": document.jurisdiction.value,
                    "section": "Part 4"
                }
            }
        ]
        
        mock_embeddings = [np.random.random(384).tolist()]
        
        with patch.object(vector_store, '_chunk_document') as mock_chunk, \
             patch.object(vector_store, '_generate_embeddings') as mock_embed:
            
            mock_chunk.return_value = document_chunks
            mock_embed.return_value = mock_embeddings
            
            result = vector_store.add_document(document, "Document content here...")
            
            assert result["success"] is True
            assert result["chunks_added"] == 1
            assert result["document_id"] == document.id
            
            # Verify chunking and embedding were called
            mock_chunk.assert_called_once()
            mock_embed.assert_called_once()
    
    def test_similarity_search_basic(self, vector_store):
        """Test basic similarity search functionality."""
        query = "employment law notice period"
        
        # Mock search results
        mock_results = [
            {
                "content": "DIFC Employment Law requires 30 days notice",
                "metadata": {
                    "document_id": "doc-difc-1",
                    "title": "DIFC Employment Law",
                    "jurisdiction": "DIFC",
                    "section": "Part 4"
                },
                "score": 0.95
            }
        ]
        
        with patch.object(vector_store.index, 'search') as mock_search:
            # Mock FAISS search returning indices and distances
            mock_search.return_value = (
                np.array([[0.05]]),  # distances (lower = more similar)
                np.array([[0]])      # indices
            )
            
            with patch.object(vector_store, '_get_metadata_by_indices') as mock_metadata:
                mock_metadata.return_value = mock_results
                
                results = vector_store.similarity_search(query, k=5)
                
                assert len(results) > 0
                assert results[0]["score"] > 0.9
                assert results[0]["metadata"]["jurisdiction"] == "DIFC"
    
    def test_similarity_search_with_jurisdiction_filter(self, vector_store):
        """Test similarity search with jurisdiction filtering."""
        query = "legal standards"
        
        with patch.object(vector_store, '_generate_query_embedding') as mock_embed, \
             patch.object(vector_store.index, 'search') as mock_search:
            
            mock_embed.return_value = np.random.random(384)
            mock_search.return_value = (
                np.array([[0.05, 0.08, 0.12]]),
                np.array([[0, 1, 2]])
            )
            
            # Mock metadata with different jurisdictions
            with patch.object(vector_store, '_get_metadata_by_indices') as mock_metadata:
                mock_metadata.return_value = [
                    {"content": "DIFC content", "metadata": {"jurisdiction": "DIFC"}, "score": 0.95},
                    {"content": "UAE content", "metadata": {"jurisdiction": "UAE"}, "score": 0.92},
                    {"content": "DFSA content", "metadata": {"jurisdiction": "DFSA"}, "score": 0.88}
                ]
                
                # Filter for DIFC only
                results = vector_store.similarity_search(
                    query, 
                    k=10, 
                    filter_jurisdiction="DIFC"
                )
                
                # Should only return DIFC results
                for result in results:
                    assert result["metadata"]["jurisdiction"] == "DIFC"
    
    def test_similarity_search_with_score_threshold(self, vector_store):
        """Test similarity search with minimum score threshold."""
        query = "contract terms"
        
        with patch.object(vector_store, 'similarity_search') as mock_search:
            mock_search.return_value = [
                {"content": "High relevance", "score": 0.95},
                {"content": "Medium relevance", "score": 0.80},
                {"content": "Low relevance", "score": 0.60}
            ]
            
            # Apply high threshold
            filtered_results = vector_store.similarity_search(
                query, 
                k=10, 
                min_score=0.85
            )
            
            # Should only return high-scoring results
            for result in filtered_results:
                assert result["score"] >= 0.85
    
    def test_remove_document_from_vector_store(self, vector_store):
        """Test removing document from vector store."""
        document_id = "doc-difc-1"
        
        with patch.object(vector_store, '_get_document_indices') as mock_indices, \
             patch.object(vector_store.index, 'remove_ids') as mock_remove:
            
            mock_indices.return_value = [0, 1, 2]  # Chunk indices for document
            
            result = vector_store.remove_document(document_id)
            
            assert result["success"] is True
            assert result["chunks_removed"] == 3
            
            # Verify removal was called
            mock_remove.assert_called_once_with(np.array([0, 1, 2]))
    
    def test_update_document_in_vector_store(self, vector_store, sample_documents):
        """Test updating document in vector store."""
        document = sample_documents[0]
        new_content = "Updated DIFC Employment Law content..."
        
        with patch.object(vector_store, 'remove_document') as mock_remove, \
             patch.object(vector_store, 'add_document') as mock_add:
            
            mock_remove.return_value = {"success": True, "chunks_removed": 2}
            mock_add.return_value = {"success": True, "chunks_added": 3}
            
            result = vector_store.update_document(document, new_content)
            
            assert result["success"] is True
            assert "chunks_removed" in result
            assert "chunks_added" in result
            
            # Should remove old version and add new version
            mock_remove.assert_called_once_with(document.id)
            mock_add.assert_called_once_with(document, new_content)
    
    def test_vector_store_persistence(self, vector_store):
        """Test saving and loading vector store."""
        save_path = "/tmp/test_vector_store"
        
        with patch('faiss.write_index') as mock_write, \
             patch('pickle.dump') as mock_pickle:
            
            result = vector_store.save(save_path)
            
            assert result["success"] is True
            assert result["saved_path"] == save_path
            
            # Should save both index and metadata
            mock_write.assert_called_once()
            mock_pickle.assert_called_once()
    
    def test_vector_store_loading(self, vector_store):
        """Test loading vector store from file."""
        load_path = "/tmp/test_vector_store"
        
        with patch('faiss.read_index') as mock_read, \
             patch('pickle.load') as mock_pickle, \
             patch('builtins.open', mock_open=True):
            
            mock_read.return_value = MagicMock()  # Mock FAISS index
            mock_pickle.return_value = {}  # Mock metadata
            
            result = vector_store.load(load_path)
            
            assert result["success"] is True
            
            # Should load both index and metadata
            mock_read.assert_called_once()
            mock_pickle.assert_called_once()
    
    def test_vector_store_optimization(self, vector_store):
        """Test vector store index optimization."""
        with patch.object(vector_store.index, 'train') as mock_train:
            # Mock training data
            training_vectors = np.random.random((1000, 384))
            
            result = vector_store.optimize_index(training_vectors)
            
            assert result["success"] is True
            assert "optimization_time" in result
            
            # Should train index for optimization
            mock_train.assert_called_once()


class TestDocumentChunker:
    """Test document chunking strategies."""
    
    @pytest.fixture
    def chunker(self):
        """Document chunker instance for testing."""
        return DocumentChunker(
            chunk_size=500,
            chunk_overlap=50,
            preserve_sections=True
        )
    
    def test_chunker_initialization(self, chunker):
        """Test document chunker initializes correctly."""
        assert chunker.chunk_size == 500
        assert chunker.chunk_overlap == 50
        assert chunker.preserve_sections is True
    
    def test_chunk_document_basic(self, chunker):
        """Test basic document chunking."""
        document_content = """
        DIFC Employment Law No. 2 of 2019
        
        Part 1: General Provisions
        This part covers general employment provisions.
        
        Part 2: Employment Standards
        This part details minimum employment standards including notice periods.
        Employees must be given adequate notice before termination.
        
        Part 3: Termination Procedures
        This part outlines proper termination procedures.
        """
        
        document_metadata = {
            "document_id": "doc-difc-1",
            "title": "DIFC Employment Law No. 2 of 2019",
            "jurisdiction": "DIFC"
        }
        
        chunks = chunker.chunk_document(document_content, document_metadata)
        
        assert len(chunks) > 0
        
        # Verify chunk structure
        for i, chunk in enumerate(chunks):
            assert "content" in chunk
            assert "metadata" in chunk
            assert chunk["metadata"]["chunk_id"] == i
            assert chunk["metadata"]["document_id"] == "doc-difc-1"
            assert len(chunk["content"]) <= chunker.chunk_size + chunker.chunk_overlap
    
    def test_chunk_document_with_section_preservation(self, chunker):
        """Test chunking preserves section boundaries."""
        document_content = """
        # Section 1: Introduction
        This is the introduction section with important context.
        
        # Section 2: Main Content
        This is the main content section with detailed information.
        It contains multiple paragraphs of relevant information.
        
        # Section 3: Conclusion
        This is the conclusion section with final thoughts.
        """
        
        document_metadata = {"document_id": "doc-test", "title": "Test Document"}
        
        chunks = chunker.chunk_document(document_content, document_metadata)
        
        # Should preserve section headers
        section_chunks = [c for c in chunks if "Section" in c["content"]]
        assert len(section_chunks) >= 3
        
        # Verify section metadata
        for chunk in chunks:
            if "Section 1" in chunk["content"]:
                assert "section" in chunk["metadata"]
                assert "Introduction" in chunk["metadata"]["section"]
    
    def test_chunk_document_overlap_handling(self, chunker):
        """Test proper handling of chunk overlap."""
        # Long document that will require multiple chunks
        long_content = "This is a test sentence. " * 100  # Create long content
        
        document_metadata = {"document_id": "doc-long", "title": "Long Document"}
        
        chunks = chunker.chunk_document(long_content, document_metadata)
        
        assert len(chunks) > 1
        
        # Check overlap between consecutive chunks  
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]["content"]
            next_chunk = chunks[i + 1]["content"]
            
            # Should have some overlapping content
            current_words = current_chunk.split()
            next_words = next_chunk.split()
            
            # Check for word overlap (simple overlap detection)
            overlap_found = any(word in next_words[:10] for word in current_words[-10:])
            if chunker.chunk_overlap > 0:
                assert overlap_found, "Expected overlap between chunks"
    
    def test_chunk_document_empty_content(self, chunker):
        """Test handling of empty document content."""
        empty_content = ""
        document_metadata = {"document_id": "doc-empty", "title": "Empty Document"}
        
        chunks = chunker.chunk_document(empty_content, document_metadata)
        
        # Should handle gracefully
        assert isinstance(chunks, list)
        assert len(chunks) == 0
    
    def test_chunk_document_small_content(self, chunker):
        """Test handling of content smaller than chunk size."""
        small_content = "This is a very short document."
        document_metadata = {"document_id": "doc-small", "title": "Small Document"}
        
        chunks = chunker.chunk_document(small_content, document_metadata)
        
        # Should create single chunk
        assert len(chunks) == 1
        assert chunks[0]["content"] == small_content
        assert chunks[0]["metadata"]["chunk_id"] == 0


class TestVectorStoreIntegration:
    """Integration tests for vector store operations."""
    
    def test_document_indexing_pipeline(self, sample_documents):
        """Test complete document indexing pipeline."""
        vector_store = FAISSVectorStore(dimension=384)
        document = sample_documents[0]
        
        document_content = """
        DIFC Employment Law No. 2 of 2019
        
        Part 4: Notice Periods
        An employer may terminate an employee's contract by giving the employee 
        written notice of not less than 30 days if the employee has been employed 
        for more than 3 months but less than 5 years.
        """
        
        with patch.object(vector_store, '_generate_embeddings') as mock_embed:
            mock_embed.return_value = [np.random.random(384).tolist() for _ in range(2)]
            
            result = vector_store.add_document(document, document_content)
            
            assert result["success"] is True
            assert result["chunks_added"] > 0
            
            # Test search for indexed content
            with patch.object(vector_store.index, 'search') as mock_search:
                mock_search.return_value = (
                    np.array([[0.05]]),
                    np.array([[0]])
                )
                
                search_results = vector_store.similarity_search("notice period requirements")
                
                assert len(search_results) > 0
    
    def test_multi_document_indexing_and_search(self, sample_documents):
        """Test indexing multiple documents and cross-document search."""
        vector_store = FAISSVectorStore(dimension=384)
        
        documents_content = [
            "DIFC Employment Law contains notice period requirements",
            "DFSA Rulebook defines financial sector employment standards"
        ]
        
        with patch.object(vector_store, '_generate_embeddings') as mock_embed:
            # Mock embeddings for all chunks
            mock_embed.side_effect = [
                [np.random.random(384).tolist()],  # DIFC doc chunks
                [np.random.random(384).tolist()]   # DFSA doc chunks
            ]
            
            # Index both documents
            for doc, content in zip(sample_documents, documents_content):
                result = vector_store.add_document(doc, content)
                assert result["success"] is True
            
            # Test cross-document search
            with patch.object(vector_store.index, 'search') as mock_search:
                mock_search.return_value = (
                    np.array([[0.05, 0.08]]),
                    np.array([[0, 1]])
                )
                
                with patch.object(vector_store, '_get_metadata_by_indices') as mock_metadata:
                    mock_metadata.return_value = [
                        {
                            "content": "DIFC Employment Law contains notice period requirements",
                            "metadata": {"jurisdiction": "DIFC", "document_id": "doc-difc-1"},
                            "score": 0.95
                        },
                        {
                            "content": "DFSA Rulebook defines financial sector employment standards", 
                            "metadata": {"jurisdiction": "DFSA", "document_id": "doc-dfsa-1"},
                            "score": 0.92
                        }
                    ]
                    
                    results = vector_store.similarity_search("employment standards")
                    
                    # Should return results from both documents
                    assert len(results) == 2
                    jurisdictions = [r["metadata"]["jurisdiction"] for r in results]
                    assert "DIFC" in jurisdictions
                    assert "DFSA" in jurisdictions
    
    @pytest.mark.slow
    def test_vector_store_performance_large_dataset(self):
        """Test vector store performance with large dataset."""
        vector_store = FAISSVectorStore(dimension=384, index_type="IVF")
        
        # Simulate large dataset
        num_documents = 100
        
        with patch.object(vector_store, '_generate_embeddings') as mock_embed:
            # Mock embeddings for large dataset
            mock_embed.return_value = [np.random.random(384).tolist() for _ in range(5)]
            
            import time
            start_time = time.time()
            
            # Index multiple documents
            for i in range(num_documents):
                doc = DocumentMetadata(
                    id=f"doc-{i}",
                    project_id="perf-test",
                    filename=f"document_{i}.pdf",
                    title=f"Test Document {i}",
                    file_path=f"/data/files/document_{i}.pdf",
                    content_type="application/pdf",
                    size_bytes=10000,
                    jurisdiction=JurisdictionType.DIFC,
                    instrument_type="Law",
                    upload_date="2024-01-01T00:00:00Z"
                )
                
                result = vector_store.add_document(doc, f"Test content for document {i}")
                assert result["success"] is True
            
            indexing_time = time.time() - start_time
            
            # Should complete indexing within reasonable time (5 seconds for 100 docs)
            assert indexing_time < 5.0
            
            # Test search performance
            start_time = time.time()
            
            with patch.object(vector_store.index, 'search') as mock_search:
                mock_search.return_value = (
                    np.array([[0.05]]),
                    np.array([[0]])
                )
                
                results = vector_store.similarity_search("test query", k=10)
                
            search_time = time.time() - start_time
            
            # Search should be very fast (< 100ms)
            assert search_time < 0.1


@pytest.mark.integration
class TestVectorStoreRealWorld:
    """Real-world integration tests for vector store."""
    
    def test_difc_law_document_indexing(self):
        """Test indexing real DIFC law document structure."""
        vector_store = FAISSVectorStore(dimension=384)
        
        # Simulate real DIFC Employment Law structure
        difc_law_content = """
        DIFC EMPLOYMENT LAW NO. 2 OF 2019
        
        CHAPTER 1 - PRELIMINARY
        1. Short title and commencement
        2. Application
        3. Interpretation
        
        CHAPTER 2 - EMPLOYMENT STANDARDS
        4. Minimum wage
        5. Working hours
        6. Annual leave
        7. Sick leave
        8. Maternity leave
        
        CHAPTER 3 - TERMINATION OF EMPLOYMENT
        9. Termination by employer
        (1) An employer may terminate an employee's contract of employment by giving 
        the employee written notice as follows:
        (a) not less than 30 days if the employee has been employed for more than 
        3 months but less than 5 years;
        (b) not less than 90 days if the employee has been employed for 5 years or more.
        
        10. Termination by employee
        11. Termination without notice
        12. End of service gratuity
        """
        
        document = DocumentMetadata(
            id="difc-employment-law-2019",
            project_id="difc-laws",
            filename="difc_employment_law_2019.pdf",
            title="DIFC Employment Law No. 2 of 2019",
            file_path="/data/laws/difc_employment_law_2019.pdf",
            content_type="application/pdf",
            size_bytes=150000,
            jurisdiction=JurisdictionType.DIFC,
            instrument_type="Law",
            upload_date="2024-01-01T00:00:00Z"
        )
        
        with patch.object(vector_store, '_generate_embeddings') as mock_embed:
            # Mock embeddings for law sections
            mock_embed.return_value = [np.random.random(384).tolist() for _ in range(8)]
            
            result = vector_store.add_document(document, difc_law_content)
            
            assert result["success"] is True
            assert result["chunks_added"] >= 6  # Should create multiple chunks for different sections
            
            # Test searching for specific provisions  
            with patch.object(vector_store.index, 'search') as mock_search, \
                 patch.object(vector_store, '_get_metadata_by_indices') as mock_metadata:
                
                mock_search.return_value = (np.array([[0.05]]), np.array([[0]]))
                mock_metadata.return_value = [
                    {
                        "content": "An employer may terminate an employee's contract by giving written notice of not less than 30 days",
                        "metadata": {
                            "document_id": "difc-employment-law-2019",
                            "section": "CHAPTER 3 - TERMINATION OF EMPLOYMENT",
                            "jurisdiction": "DIFC",
                            "title": "DIFC Employment Law No. 2 of 2019"
                        },
                        "score": 0.95
                    }
                ]
                
                results = vector_store.similarity_search("notice period termination")
                
                assert len(results) > 0
                assert "30 days" in results[0]["content"]
                assert results[0]["metadata"]["section"] == "CHAPTER 3 - TERMINATION OF EMPLOYMENT"