"""
Tests for Document Ingestion API endpoints.

Following PRP requirements:
- Test document ingestion endpoints
- Test metadata extraction and validation
- Test vector indexing integration
- Test DIFC-first processing and categorization
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from io import BytesIO

from core.models import JurisdictionType, DocumentMetadata


class TestDocumentIngestion:
    """Test document ingestion and processing endpoints."""
    
    @pytest.mark.asyncio
    async def test_ingest_single_document(self, client_with_lifespan):
        """Test ingesting a single document."""
        # Mock PDF file
        file_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\nTest DIFC Employment Law document content"
        
        files = {
            "file": ("difc_employment_law.pdf", BytesIO(file_content), "application/pdf")
        }
        
        metadata = {
            "title": "DIFC Employment Law No. 2 of 2019",
            "jurisdiction": "DIFC",
            "instrument_type": "Law"
        }
        
        with patch('api.ingest.process_document') as mock_process, \
             patch('api.ingest.extract_document_text') as mock_extract, \
             patch('api.ingest.generate_embeddings') as mock_embed, \
             patch('api.ingest.store_in_vector_db') as mock_store:
            
            mock_extract.return_value = "DIFC Employment Law provisions and requirements..."
            mock_embed.return_value = [0.1, 0.2, 0.3] * 384  # Mock embedding vector
            mock_process.return_value = DocumentMetadata(
                id="doc-ingest-123",
                project_id="system",
                filename="difc_employment_law.pdf",
                title="DIFC Employment Law No. 2 of 2019",
                file_path="/data/files/difc_employment_law.pdf",
                content_type="application/pdf",
                size_bytes=len(file_content),
                jurisdiction=JurisdictionType.DIFC,
                instrument_type="Law",
                upload_date="2024-01-01T00:00:00Z"
            )
            
            response = await client_with_lifespan.post(
                "/api/ingest/document",
                files=files,
                data=metadata
            )
            
            assert response.status_code == 201
            data = response.json()
            
            assert data["id"] == "doc-ingest-123"
            assert data["title"] == "DIFC Employment Law No. 2 of 2019"
            assert data["jurisdiction"] == "DIFC"
            assert data["instrument_type"] == "Law"
            
            # Verify processing pipeline was called
            mock_extract.assert_called_once()
            mock_embed.assert_called_once()
            mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ingest_batch_documents(self, client_with_lifespan):
        """Test batch ingestion of multiple documents."""
        # Mock multiple files
        files = [
            ("file1", ("difc_law.pdf", BytesIO(b"DIFC law content"), "application/pdf")),
            ("file2", ("dfsa_rules.pdf", BytesIO(b"DFSA rules content"), "application/pdf")),
            ("file3", ("uae_regulation.pdf", BytesIO(b"UAE regulation content"), "application/pdf"))
        ]
        
        batch_metadata = {
            "default_jurisdiction": "DIFC",
            "auto_categorize": True,
            "extract_citations": True
        }
        
        with patch('api.ingest.process_batch_documents') as mock_batch:
            mock_batch.return_value = {
                "processed_count": 3,
                "success_count": 3,
                "failed_count": 0,
                "documents": [
                    {"id": "doc-1", "title": "DIFC Law", "jurisdiction": "DIFC", "status": "success"},
                    {"id": "doc-2", "title": "DFSA Rules", "jurisdiction": "DFSA", "status": "success"},
                    {"id": "doc-3", "title": "UAE Regulation", "jurisdiction": "UAE", "status": "success"}
                ],
                "processing_time": 45.2
            }
            
            response = await client_with_lifespan.post(
                "/api/ingest/batch",
                files=files,
                data=batch_metadata
            )
            
            assert response.status_code == 201
            data = response.json()
            
            assert data["processed_count"] == 3
            assert data["success_count"] == 3
            assert data["failed_count"] == 0
            assert len(data["documents"]) == 3
            
            # Verify DIFC document is processed first (DIFC-first approach)
            difc_doc = next(doc for doc in data["documents"] if doc["jurisdiction"] == "DIFC")
            assert difc_doc["id"] == "doc-1"
    
    @pytest.mark.asyncio
    async def test_ingest_with_auto_categorization(self, client_with_lifespan):
        """Test document ingestion with automatic categorization."""
        file_content = b"EMPLOYMENT AGREEMENT\n\nThis agreement governs employment terms under DIFC jurisdiction..."
        
        files = {
            "file": ("contract.pdf", BytesIO(file_content), "application/pdf")
        }
        
        # Don't specify jurisdiction/type - let auto-categorization handle it
        metadata = {
            "auto_categorize": True
        }
        
        with patch('api.ingest.auto_categorize_document') as mock_categorize, \
             patch('api.ingest.process_document') as mock_process:
            
            mock_categorize.return_value = {
                "jurisdiction": JurisdictionType.DIFC,
                "instrument_type": "Contract",
                "confidence": 0.92,
                "extracted_title": "Employment Agreement - DIFC Jurisdiction"
            }
            
            mock_process.return_value = DocumentMetadata(
                id="doc-auto-123",
                project_id="system",
                filename="contract.pdf",
                title="Employment Agreement - DIFC Jurisdiction",
                file_path="/data/files/contract.pdf",
                content_type="application/pdf",
                size_bytes=len(file_content),
                jurisdiction=JurisdictionType.DIFC,
                instrument_type="Contract",
                upload_date="2024-01-01T00:00:00Z"
            )
            
            response = await client_with_lifespan.post(
                "/api/ingest/document",
                files=files,
                data=metadata
            )
            
            assert response.status_code == 201
            data = response.json()
            
            assert data["jurisdiction"] == "DIFC"
            assert data["instrument_type"] == "Contract"
            assert "Employment Agreement" in data["title"]
            
            # Verify auto-categorization was called
            mock_categorize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ingest_invalid_file_type(self, client_with_lifespan):
        """Test ingestion rejection of invalid file types."""
        # Try to upload executable file
        file_content = b"MZ\x90\x00"  # Windows executable header
        
        files = {
            "file": ("malicious.exe", BytesIO(file_content), "application/x-executable")
        }
        
        metadata = {
            "title": "Test Document",
            "jurisdiction": "DIFC"
        }
        
        response = await client_with_lifespan.post(
            "/api/ingest/document",
            files=files,
            data=metadata
        )
        
        assert response.status_code == 400
        assert "file type not allowed" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_ingest_file_too_large(self, client_with_lifespan):
        """Test ingestion rejection of oversized files."""
        # Create file larger than limit (assume 50MB limit)
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        
        files = {
            "file": ("large_document.pdf", BytesIO(large_content), "application/pdf")
        }
        
        metadata = {
            "title": "Large Document",
            "jurisdiction": "DIFC"
        }
        
        response = await client_with_lifespan.post(
            "/api/ingest/document",
            files=files,
            data=metadata
        )
        
        assert response.status_code == 413  # Request Entity Too Large
    
    @pytest.mark.asyncio
    async def test_ingest_malformed_pdf(self, client_with_lifespan):
        """Test handling of corrupted/malformed documents."""
        # Malformed PDF content
        file_content = b"This is not a valid PDF file"
        
        files = {
            "file": ("invalid.pdf", BytesIO(file_content), "application/pdf")
        }
        
        metadata = {
            "title": "Invalid PDF",
            "jurisdiction": "DIFC"
        }
        
        with patch('api.ingest.extract_document_text') as mock_extract:
            mock_extract.side_effect = Exception("Unable to parse PDF: Invalid format")
            
            response = await client_with_lifespan.post(
                "/api/ingest/document",
                files=files,
                data=metadata
            )
            
            assert response.status_code == 422  # Unprocessable Entity
            assert "unable to parse" in response.json()["detail"].lower()


class TestMetadataExtraction:
    """Test document metadata extraction and enrichment."""
    
    @pytest.mark.asyncio
    async def test_extract_metadata_endpoint(self, client_with_lifespan):
        """Test metadata extraction without full ingestion."""
        file_content = b"DIFC EMPLOYMENT LAW NO. 2 OF 2019\n\nSection 1: General Provisions..."
        
        files = {
            "file": ("difc_law.pdf", BytesIO(file_content), "application/pdf")
        }
        
        with patch('api.ingest.extract_document_metadata') as mock_extract:
            mock_extract.return_value = {
                "extracted_title": "DIFC Employment Law No. 2 of 2019",
                "detected_jurisdiction": "DIFC",
                "detected_instrument_type": "Law",
                "confidence_scores": {
                    "jurisdiction": 0.98,
                    "instrument_type": 0.95,
                    "title": 0.92
                },
                "extracted_sections": [
                    {"title": "General Provisions", "page": 1},
                    {"title": "Employment Standards", "page": 5},
                    {"title": "Termination Procedures", "page": 12}
                ],
                "detected_language": "en",
                "estimated_processing_time": 2.5
            }
            
            response = await client_with_lifespan.post(
                "/api/ingest/extract-metadata",
                files=files
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["detected_jurisdiction"] == "DIFC"
            assert data["detected_instrument_type"] == "Law"
            assert "DIFC Employment Law" in data["extracted_title"]
            assert len(data["extracted_sections"]) == 3
            assert data["confidence_scores"]["jurisdiction"] > 0.9
    
    @pytest.mark.asyncio
    async def test_extract_citations_from_document(self, client_with_lifespan):
        """Test extracting citations from document content."""
        file_content = b"This regulation refers to DIFC Law No. 2 of 2019 and DFSA General Rulebook Section 3.2..."
        
        files = {
            "file": ("regulation.pdf", BytesIO(file_content), "application/pdf")
        }
        
        with patch('api.ingest.extract_citations') as mock_citations:
            mock_citations.return_value = {
                "citations": [
                    {
                        "text": "DIFC Law No. 2 of 2019",
                        "type": "law_reference",
                        "jurisdiction": "DIFC",
                        "confidence": 0.95
                    },
                    {
                        "text": "DFSA General Rulebook Section 3.2",
                        "type": "rulebook_reference",
                        "jurisdiction": "DFSA",
                        "confidence": 0.88
                    }
                ],
                "total_citations": 2,
                "unique_sources": 2
            }
            
            response = await client_with_lifespan.post(
                "/api/ingest/extract-citations",
                files=files
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_citations"] == 2
            assert len(data["citations"]) == 2
            
            # Verify DIFC citation is present
            difc_citations = [c for c in data["citations"] if c["jurisdiction"] == "DIFC"]
            assert len(difc_citations) >= 1
    
    @pytest.mark.asyncio
    async def test_enrich_document_metadata(self, client_with_lifespan):
        """Test enriching existing document metadata."""
        document_id = "doc-123"
        
        enrichment_data = {
            "extract_sections": True,
            "extract_citations": True,
            "validate_references": True,
            "update_jurisdiction": True
        }
        
        with patch('api.ingest.enrich_document') as mock_enrich:
            mock_enrich.return_value = {
                "document_id": document_id,
                "enrichment_applied": True,
                "updates": {
                    "sections_extracted": 8,
                    "citations_found": 12,
                    "references_validated": 10,
                    "jurisdiction_confirmed": True
                },
                "processing_time": 15.3
            }
            
            response = await client_with_lifespan.post(
                f"/api/ingest/documents/{document_id}/enrich",
                json=enrichment_data
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["enrichment_applied"] is True
            assert data["updates"]["sections_extracted"] > 0
            assert data["updates"]["citations_found"] > 0


class TestVectorIndexing:
    """Test vector indexing and search integration."""
    
    @pytest.mark.asyncio
    async def test_reindex_document_collection(self, client_with_lifespan):
        """Test reindexing document collection in vector store."""
        reindex_params = {
            "jurisdiction_filter": "DIFC",
            "force_reindex": False,
            "update_embeddings": True
        }
        
        with patch('api.ingest.reindex_documents') as mock_reindex:
            mock_reindex.return_value = {
                "reindex_started": True,
                "job_id": "reindex-job-123",
                "estimated_time": "10-15 minutes",
                "documents_to_process": 250,
                "status_endpoint": "/api/ingest/reindex/status/reindex-job-123"
            }
            
            response = await client_with_lifespan.post(
                "/api/ingest/reindex",
                json=reindex_params
            )
            
            assert response.status_code == 202  # Accepted
            data = response.json()
            
            assert data["reindex_started"] is True
            assert "job_id" in data
            assert data["documents_to_process"] > 0
    
    @pytest.mark.asyncio
    async def test_check_reindex_status(self, client_with_lifespan):
        """Test checking reindex job status."""
        job_id = "reindex-job-123"
        
        with patch('api.ingest.get_reindex_status') as mock_status:
            mock_status.return_value = {
                "job_id": job_id,
                "status": "in_progress",
                "progress_percentage": 65,
                "documents_processed": 162,
                "documents_total": 250,
                "estimated_completion": "2024-01-01T00:08:00Z",
                "errors_count": 2,
                "current_phase": "generating_embeddings"
            }
            
            response = await client_with_lifespan.get(f"/api/ingest/reindex/status/{job_id}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "in_progress"
            assert data["progress_percentage"] == 65
            assert data["documents_processed"] < data["documents_total"]
    
    @pytest.mark.asyncio
    async def test_optimize_vector_index(self, client_with_lifespan):
        """Test optimizing vector index for better performance."""
        optimization_params = {
            "rebuild_index": False,
            "optimize_retrieval": True,
            "cleanup_deleted": True
        }
        
        with patch('api.ingest.optimize_vector_index') as mock_optimize:
            mock_optimize.return_value = {
                "optimization_completed": True,
                "index_size_before": "2.1GB",
                "index_size_after": "1.8GB",
                "space_saved": "300MB",
                "retrieval_speed_improvement": "15%",
                "deleted_vectors_cleaned": 1250
            }
            
            response = await client_with_lifespan.post(
                "/api/ingest/optimize-index",
                json=optimization_params
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["optimization_completed"] is True
            assert "space_saved" in data
            assert "retrieval_speed_improvement" in data


class TestIngestionQuality:
    """Test ingestion quality control and validation."""
    
    @pytest.mark.asyncio
    async def test_validate_document_quality(self, client_with_lifespan):
        """Test document quality validation before ingestion."""
        file_content = b"High quality DIFC legal document with clear structure and references..."
        
        files = {
            "file": ("quality_doc.pdf", BytesIO(file_content), "application/pdf")
        }
        
        with patch('api.ingest.validate_document_quality') as mock_validate:
            mock_validate.return_value = {
                "quality_score": 0.92,
                "quality_checks": {
                    "text_extractability": "high",
                    "structure_clarity": "high", 
                    "language_quality": "high",
                    "citation_consistency": "medium",
                    "jurisdiction_clarity": "high"
                },
                "recommendations": [
                    "Consider standardizing citation format",
                    "Document is suitable for ingestion"
                ],
                "suitable_for_ingestion": True
            }
            
            response = await client_with_lifespan.post(
                "/api/ingest/validate-quality",
                files=files
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["quality_score"] > 0.9
            assert data["suitable_for_ingestion"] is True
            assert len(data["quality_checks"]) >= 5
    
    @pytest.mark.asyncio
    async def test_detect_duplicate_documents(self, client_with_lifespan):
        """Test duplicate document detection."""
        file_content = b"This document may already exist in the system..."
        
        files = {
            "file": ("potential_duplicate.pdf", BytesIO(file_content), "application/pdf")
        }
        
        with patch('api.ingest.detect_duplicates') as mock_duplicates:
            mock_duplicates.return_value = {
                "duplicates_found": True,
                "potential_duplicates": [
                    {
                        "document_id": "existing-doc-456",
                        "title": "Similar DIFC Document",
                        "similarity_score": 0.87,
                        "match_type": "content_similarity"
                    }
                ],
                "recommendations": [
                    "Review existing document before proceeding with ingestion",
                    "Consider merging or updating existing document"
                ]
            }
            
            response = await client_with_lifespan.post(
                "/api/ingest/detect-duplicates",
                files=files
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["duplicates_found"] is True
            assert len(data["potential_duplicates"]) > 0
            assert data["potential_duplicates"][0]["similarity_score"] > 0.8
    
    @pytest.mark.asyncio
    async def test_preview_ingestion_results(self, client_with_lifespan):
        """Test previewing what would happen during ingestion."""
        file_content = b"Sample DIFC regulation document for preview..."
        
        files = {
            "file": ("preview_doc.pdf", BytesIO(file_content), "application/pdf")
        }
        
        preview_params = {
            "dry_run": True,
            "extract_metadata": True,
            "check_duplicates": True,
            "validate_quality": True
        }
        
        with patch('api.ingest.preview_ingestion') as mock_preview:
            mock_preview.return_value = {
                "preview_mode": True,
                "would_ingest": True,
                "predicted_metadata": {
                    "title": "DIFC Regulation - Financial Services",
                    "jurisdiction": "DIFC",
                    "instrument_type": "Regulation",
                    "confidence": 0.91
                },
                "quality_assessment": {
                    "score": 0.89,
                    "suitable": True
                },
                "duplicate_check": {
                    "duplicates_found": False
                },
                "estimated_processing_time": "30-45 seconds",
                "vector_dimensions": 384,
                "predicted_chunks": 12
            }
            
            response = await client_with_lifespan.post(
                "/api/ingest/preview",
                files=files,
                data=preview_params
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["preview_mode"] is True
            assert data["would_ingest"] is True
            assert data["predicted_metadata"]["jurisdiction"] == "DIFC"
            assert data["quality_assessment"]["suitable"] is True


class TestIngestionAnalytics:
    """Test ingestion analytics and reporting."""
    
    @pytest.mark.asyncio
    async def test_get_ingestion_statistics(self, client_with_lifespan):
        """Test retrieving ingestion statistics."""
        with patch('api.ingest.get_ingestion_stats') as mock_stats:
            mock_stats.return_value = {
                "total_documents": 1500,
                "documents_by_jurisdiction": {
                    "DIFC": 800,
                    "DFSA": 400,
                    "UAE": 200,
                    "OTHER": 100
                },
                "documents_by_type": {
                    "Law": 300,
                    "Regulation": 500,
                    "Rulebook": 400,
                    "Contract": 200,
                    "Other": 100
                },
                "ingestion_volume_last_30_days": 150,
                "average_processing_time": "45 seconds",
                "total_storage_size": "12.5GB",
                "vector_index_size": "850MB"
            }
            
            response = await client_with_lifespan.get("/api/ingest/statistics")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_documents"] > 0
            assert "documents_by_jurisdiction" in data
            assert "documents_by_type" in data
            
            # Verify DIFC has the most documents (DIFC-first approach)
            jurisdictions = data["documents_by_jurisdiction"]
            assert jurisdictions["DIFC"] >= jurisdictions["DFSA"]
    
    @pytest.mark.asyncio
    async def test_get_recent_ingestion_activity(self, client_with_lifespan):
        """Test retrieving recent ingestion activity."""
        with patch('api.ingest.get_recent_activity') as mock_activity:
            mock_activity.return_value = {
                "recent_ingestions": [
                    {
                        "document_id": "doc-latest-1",
                        "title": "DIFC Amendment Law 2024",
                        "jurisdiction": "DIFC",
                        "ingested_at": "2024-01-15T10:30:00Z",
                        "processing_time": 42,
                        "status": "success"
                    },
                    {
                        "document_id": "doc-latest-2", 
                        "title": "DFSA Consultation Paper",
                        "jurisdiction": "DFSA",
                        "ingested_at": "2024-01-15T09:15:00Z",
                        "processing_time": 38,
                        "status": "success"
                    }
                ],
                "failed_ingestions": [],
                "processing_queue_size": 0,
                "average_daily_volume": 12
            }
            
            response = await client_with_lifespan.get("/api/ingest/activity")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "recent_ingestions" in data
            assert len(data["recent_ingestions"]) > 0
            assert data["processing_queue_size"] >= 0


@pytest.mark.integration
class TestIngestionIntegration:
    """Integration tests for complete ingestion pipeline."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_ingestion_pipeline(self, client_with_lifespan):
        """Test complete ingestion pipeline from upload to search."""
        # 1. Upload and ingest document
        file_content = b"DIFC EMPLOYMENT LAW AMENDMENT 2024\n\nThis amendment modifies employment standards..."
        
        files = {
            "file": ("difc_amendment_2024.pdf", BytesIO(file_content), "application/pdf")
        }
        
        metadata = {
            "title": "DIFC Employment Law Amendment 2024",
            "jurisdiction": "DIFC",
            "instrument_type": "Law"
        }
        
        with patch('api.ingest.process_document') as mock_process, \
             patch('rag.vector_store.add_document') as mock_add_vector, \
             patch('rag.retrievers.difc_retriever') as mock_retriever:
            
            # Mock successful ingestion
            mock_process.return_value = DocumentMetadata(
                id="doc-e2e-123",
                project_id="system",
                filename="difc_amendment_2024.pdf",
                title="DIFC Employment Law Amendment 2024",
                file_path="/data/files/difc_amendment_2024.pdf",
                content_type="application/pdf",
                size_bytes=len(file_content),
                jurisdiction=JurisdictionType.DIFC,
                instrument_type="Law",
                upload_date="2024-01-01T00:00:00Z"
            )
            
            ingest_response = await client_with_lifespan.post(
                "/api/ingest/document",
                files=files,
                data=metadata
            )
            
            assert ingest_response.status_code == 201
            document_id = ingest_response.json()["id"]
            
            # 2. Verify document is searchable
            mock_retriever.search.return_value = [
                {
                    "document_id": document_id,
                    "title": "DIFC Employment Law Amendment 2024",
                    "content": "Employment standards modification...",
                    "jurisdiction": "DIFC",
                    "score": 0.95
                }
            ]
            
            # Mock search through assistant API (which uses RAG)
            from core.models import AssistantQuery, AssistantMode
            
            search_query = AssistantQuery(
                mode=AssistantMode.ASSIST,
                prompt="What are the changes in DIFC employment law 2024?",
                knowledge={"jurisdiction": JurisdictionType.DIFC}
            )
            
            with patch('agents.graph.simple_assistant') as mock_assistant:
                mock_assistant.run.return_value = {
                    "success": True,
                    "content": "The DIFC Employment Law Amendment 2024 introduces new employment standards...",
                    "citations": [{"title": "DIFC Employment Law Amendment 2024", "document_id": document_id}]
                }
                
                search_response = await client_with_lifespan.post(
                    "/api/assistant/query-sync",
                    json=search_query.dict()
                )
                
                assert search_response.status_code == 200
                search_data = search_response.json()
                
                assert search_data["success"] is True
                assert "2024" in search_data["content"]
                assert any(citation.get("document_id") == document_id for citation in search_data["citations"])
            
            # Verify vector indexing was called
            mock_add_vector.assert_called_once()
    
    @pytest.mark.slow
    @pytest.mark.asyncio 
    async def test_bulk_ingestion_performance(self, client_with_lifespan):
        """Test performance of bulk document ingestion."""
        # Create multiple test documents
        documents = []
        for i in range(10):
            file_content = f"DIFC Document {i}\n\nThis is test document number {i} for bulk ingestion testing...".encode()
            documents.append(
                ("file" + str(i), (f"test_doc_{i}.pdf", BytesIO(file_content), "application/pdf"))
            )
        
        batch_metadata = {
            "default_jurisdiction": "DIFC",
            "auto_categorize": True,
            "parallel_processing": True
        }
        
        with patch('api.ingest.process_batch_documents') as mock_batch:
            mock_batch.return_value = {
                "processed_count": 10,
                "success_count": 10,
                "failed_count": 0,
                "processing_time": 125.5,
                "average_time_per_document": 12.6,
                "documents": [{"id": f"doc-bulk-{i}", "status": "success"} for i in range(10)]
            }
            
            import time
            start_time = time.time()
            
            response = await client_with_lifespan.post(
                "/api/ingest/batch",
                files=documents,
                data=batch_metadata
            )
            
            end_time = time.time()
            request_time = end_time - start_time
            
            assert response.status_code == 201
            data = response.json()
            
            assert data["success_count"] == 10
            assert data["failed_count"] == 0
            assert request_time < 30  # Should complete within 30 seconds for test
            assert data["average_time_per_document"] < 20  # Reasonable processing time per document