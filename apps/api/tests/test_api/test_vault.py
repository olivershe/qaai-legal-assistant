"""
Comprehensive tests for Vault API endpoints.

Following PRP requirements:
- Test CRUD operations for projects and documents
- Test file upload with metadata extraction
- Test search functionality with RAG integration
- Test proper error handling and validation
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from io import BytesIO

from core.models import VaultProject, DocumentMetadata, JurisdictionType


class TestVaultProjects:
    """Test vault project management endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_project(self, client_with_lifespan):
        """Test creating a new vault project."""
        project_data = {
            "name": "DIFC Contract Review",
            "visibility": "private"
        }
        
        with patch('core.database.AsyncSession') as mock_session:
            # Mock successful project creation
            mock_project = VaultProject(
                id="test-project-123",
                name="DIFC Contract Review",
                visibility="private",
                document_count=0,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
                owner="test-user@example.com"
            )
            
            response = await client_with_lifespan.post("/api/vault/projects", json=project_data)
            
            assert response.status_code == 201
            data = response.json()
            
            assert data["name"] == "DIFC Contract Review"
            assert data["visibility"] == "private"
            assert data["document_count"] == 0
            assert "id" in data
            assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_list_projects(self, client_with_lifespan, sample_vault_project):
        """Test listing vault projects for user."""
        with patch('api.vault.get_user_projects') as mock_get_projects:
            mock_get_projects.return_value = [sample_vault_project]
            
            response = await client_with_lifespan.get("/api/vault/projects")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "projects" in data
            assert len(data["projects"]) == 1
            assert data["projects"][0]["name"] == "DIFC Contract Review"
    
    @pytest.mark.asyncio
    async def test_get_project_details(self, client_with_lifespan, sample_vault_project):
        """Test getting specific project details."""
        project_id = "test-project-123"
        
        with patch('api.vault.get_project_by_id') as mock_get_project:
            mock_get_project.return_value = sample_vault_project
            
            response = await client_with_lifespan.get(f"/api/vault/projects/{project_id}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["id"] == project_id
            assert data["name"] == "DIFC Contract Review"
            assert data["document_count"] == 5
    
    @pytest.mark.asyncio
    async def test_update_project(self, client_with_lifespan):
        """Test updating project details."""
        project_id = "test-project-123"
        update_data = {
            "name": "Updated DIFC Contract Review",
            "visibility": "shared"
        }
        
        with patch('api.vault.update_project') as mock_update:
            mock_update.return_value = {
                "id": project_id,
                "name": "Updated DIFC Contract Review",
                "visibility": "shared",
                "document_count": 5,
                "updated_at": "2024-01-15T00:00:00Z"
            }
            
            response = await client_with_lifespan.put(f"/api/vault/projects/{project_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["name"] == "Updated DIFC Contract Review"
            assert data["visibility"] == "shared"
    
    @pytest.mark.asyncio
    async def test_delete_project(self, client_with_lifespan):
        """Test deleting a project."""
        project_id = "test-project-123"
        
        with patch('api.vault.delete_project') as mock_delete:
            mock_delete.return_value = {"success": True}
            
            response = await client_with_lifespan.delete(f"/api/vault/projects/{project_id}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_project_not_found(self, client_with_lifespan):
        """Test handling of non-existent project."""
        project_id = "non-existent"
        
        with patch('api.vault.get_project_by_id') as mock_get_project:
            mock_get_project.return_value = None
            
            response = await client_with_lifespan.get(f"/api/vault/projects/{project_id}")
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_create_project_validation(self, client_with_lifespan):
        """Test project creation validation."""
        # Test empty name
        invalid_data = {"name": "", "visibility": "private"}
        response = await client_with_lifespan.post("/api/vault/projects", json=invalid_data)
        assert response.status_code == 422
        
        # Test invalid visibility
        invalid_data = {"name": "Test Project", "visibility": "invalid"}
        response = await client_with_lifespan.post("/api/vault/projects", json=invalid_data)
        assert response.status_code == 422


class TestVaultDocuments:
    """Test vault document management endpoints."""
    
    @pytest.mark.asyncio
    async def test_upload_document(self, client_with_lifespan):
        """Test uploading a document to a project."""
        project_id = "test-project-123"
        
        # Mock file upload
        file_content = b"This is a test PDF document content"
        files = {
            "file": ("test_document.pdf", BytesIO(file_content), "application/pdf")
        }
        
        document_metadata = {
            "title": "Test DIFC Employment Contract",
            "jurisdiction": "DIFC",
            "instrument_type": "Contract"
        }
        
        with patch('api.vault.save_uploaded_file') as mock_save, \
             patch('api.vault.extract_document_metadata') as mock_extract, \
             patch('api.vault.store_document_metadata') as mock_store:
            
            mock_save.return_value = "/data/files/test_document.pdf"
            mock_extract.return_value = {
                "title": "Test DIFC Employment Contract",
                "jurisdiction": JurisdictionType.DIFC,
                "instrument_type": "Contract"
            }
            mock_store.return_value = DocumentMetadata(
                id="doc-123",
                project_id=project_id,
                filename="test_document.pdf",
                title="Test DIFC Employment Contract",
                file_path="/data/files/test_document.pdf",
                content_type="application/pdf",
                size_bytes=len(file_content),
                jurisdiction=JurisdictionType.DIFC,
                instrument_type="Contract",
                upload_date="2024-01-01T00:00:00Z"
            )
            
            response = await client_with_lifespan.post(
                f"/api/vault/projects/{project_id}/documents",
                files=files,
                data=document_metadata
            )
            
            assert response.status_code == 201
            data = response.json()
            
            assert data["filename"] == "test_document.pdf"
            assert data["title"] == "Test DIFC Employment Contract"
            assert data["jurisdiction"] == "DIFC"
            assert data["project_id"] == project_id
    
    @pytest.mark.asyncio
    async def test_list_project_documents(self, client_with_lifespan, sample_documents):
        """Test listing documents in a project."""
        project_id = "test-project-123"
        
        with patch('api.vault.get_project_documents') as mock_get_docs:
            mock_get_docs.return_value = sample_documents
            
            response = await client_with_lifespan.get(f"/api/vault/projects/{project_id}/documents")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "documents" in data
            assert len(data["documents"]) == 2
            
            # Verify DIFC document is present
            difc_docs = [doc for doc in data["documents"] if doc["jurisdiction"] == "DIFC"]
            assert len(difc_docs) >= 1
    
    @pytest.mark.asyncio
    async def test_get_document_details(self, client_with_lifespan, sample_documents):
        """Test getting specific document details."""
        project_id = "test-project-123"
        document_id = "doc-1"
        
        with patch('api.vault.get_document_by_id') as mock_get_doc:
            mock_get_doc.return_value = sample_documents[0]
            
            response = await client_with_lifespan.get(f"/api/vault/projects/{project_id}/documents/{document_id}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["id"] == document_id
            assert data["title"] == "DIFC Employment Law No. 2 of 2019"
            assert data["jurisdiction"] == "DIFC"
    
    @pytest.mark.asyncio
    async def test_update_document_metadata(self, client_with_lifespan):
        """Test updating document metadata."""
        project_id = "test-project-123"
        document_id = "doc-1"
        
        update_data = {
            "title": "Updated DIFC Employment Law Title"
        }
        
        with patch('api.vault.update_document_metadata') as mock_update:
            mock_update.return_value = {
                "id": document_id,
                "title": "Updated DIFC Employment Law Title",
                "jurisdiction": "DIFC",
                "updated_at": "2024-01-15T00:00:00Z"
            }
            
            response = await client_with_lifespan.patch(
                f"/api/vault/projects/{project_id}/documents/{document_id}",
                json=update_data
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["title"] == "Updated DIFC Employment Law Title"
    
    @pytest.mark.asyncio
    async def test_delete_document(self, client_with_lifespan):
        """Test deleting a document."""
        project_id = "test-project-123"
        document_id = "doc-1"
        
        with patch('api.vault.delete_document') as mock_delete:
            mock_delete.return_value = {"success": True}
            
            response = await client_with_lifespan.delete(f"/api/vault/projects/{project_id}/documents/{document_id}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, client_with_lifespan):
        """Test uploading invalid file type."""
        project_id = "test-project-123"
        
        # Try to upload an executable file
        file_content = b"Invalid file content"
        files = {
            "file": ("malicious.exe", BytesIO(file_content), "application/x-executable")
        }
        
        response = await client_with_lifespan.post(
            f"/api/vault/projects/{project_id}/documents",
            files=files
        )
        
        assert response.status_code == 400
        assert "file type" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, client_with_lifespan):
        """Test uploading file that exceeds size limit."""
        project_id = "test-project-123"
        
        # Create a large file (simulate 100MB)
        large_content = b"x" * (100 * 1024 * 1024)
        files = {
            "file": ("large_document.pdf", BytesIO(large_content), "application/pdf")
        }
        
        response = await client_with_lifespan.post(
            f"/api/vault/projects/{project_id}/documents",
            files=files
        )
        
        assert response.status_code == 413  # Request Entity Too Large


class TestVaultSearch:
    """Test vault search functionality with RAG integration."""
    
    @pytest.mark.asyncio
    async def test_search_project_documents(self, client_with_lifespan):
        """Test searching documents within a project."""
        project_id = "test-project-123"
        search_query = "employment law minimum notice"
        
        with patch('rag.retrievers.difc_retriever') as mock_retriever:
            mock_retriever.search_project_documents.return_value = [
                {
                    "document_id": "doc-1",
                    "title": "DIFC Employment Law No. 2 of 2019",
                    "content": "Minimum notice period requirements...",
                    "score": 0.95,
                    "jurisdiction": "DIFC"
                }
            ]
            
            response = await client_with_lifespan.get(
                f"/api/vault/projects/{project_id}/search",
                params={"query": search_query}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "results" in data
            assert len(data["results"]) > 0
            assert data["results"][0]["jurisdiction"] == "DIFC"
            assert data["results"][0]["score"] > 0.9
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, client_with_lifespan):
        """Test searching with jurisdiction and document type filters."""
        project_id = "test-project-123"
        
        search_params = {
            "query": "employment standards",
            "jurisdiction": "DIFC",
            "document_type": "Law",
            "limit": 10
        }
        
        with patch('rag.retrievers.difc_retriever') as mock_retriever:
            mock_retriever.search_project_documents.return_value = [
                {
                    "document_id": "doc-1",
                    "title": "DIFC Employment Law No. 2 of 2019",
                    "jurisdiction": "DIFC",
                    "instrument_type": "Law",
                    "score": 0.98
                }
            ]
            
            response = await client_with_lifespan.get(
                f"/api/vault/projects/{project_id}/search",
                params=search_params
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify filtering worked
            for result in data["results"]:
                assert result["jurisdiction"] == "DIFC"
                assert result["instrument_type"] == "Law"
    
    @pytest.mark.asyncio
    async def test_search_empty_query(self, client_with_lifespan):
        """Test search with empty query."""
        project_id = "test-project-123"
        
        response = await client_with_lifespan.get(
            f"/api/vault/projects/{project_id}/search",
            params={"query": ""}
        )
        
        assert response.status_code == 400
        assert "query cannot be empty" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_search_no_results(self, client_with_lifespan):
        """Test search that returns no results."""
        project_id = "test-project-123"
        
        with patch('rag.retrievers.difc_retriever') as mock_retriever:
            mock_retriever.search_project_documents.return_value = []
            
            response = await client_with_lifespan.get(
                f"/api/vault/projects/{project_id}/search",
                params={"query": "nonexistent topic"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["results"] == []
            assert "total_results" in data
            assert data["total_results"] == 0


class TestVaultPermissions:
    """Test vault permission and access control."""
    
    @pytest.mark.asyncio
    async def test_access_private_project(self, client_with_lifespan):
        """Test accessing private project by unauthorized user."""
        project_id = "private-project-123"
        
        with patch('api.vault.check_project_access') as mock_check:
            mock_check.return_value = False  # Access denied
            
            response = await client_with_lifespan.get(f"/api/vault/projects/{project_id}")
            
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_access_shared_project(self, client_with_lifespan):
        """Test accessing shared project."""
        project_id = "shared-project-123"
        
        with patch('api.vault.check_project_access') as mock_check, \
             patch('api.vault.get_project_by_id') as mock_get:
            mock_check.return_value = True  # Access granted
            mock_get.return_value = VaultProject(
                id=project_id,
                name="Shared DIFC Project",
                visibility="shared",
                document_count=3,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
                owner="other-user@example.com"
            )
            
            response = await client_with_lifespan.get(f"/api/vault/projects/{project_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["visibility"] == "shared"
    
    @pytest.mark.asyncio
    async def test_modify_readonly_project(self, client_with_lifespan):
        """Test attempting to modify a read-only project."""
        project_id = "readonly-project-123"
        
        with patch('api.vault.check_project_write_access') as mock_check:
            mock_check.return_value = False  # No write access
            
            update_data = {"name": "Updated Name"}
            response = await client_with_lifespan.put(f"/api/vault/projects/{project_id}", json=update_data)
            
            assert response.status_code == 403


class TestVaultAnalytics:
    """Test vault analytics and statistics."""
    
    @pytest.mark.asyncio
    async def test_project_analytics(self, client_with_lifespan):
        """Test getting project analytics."""
        project_id = "test-project-123"
        
        with patch('api.vault.get_project_analytics') as mock_analytics:
            mock_analytics.return_value = {
                "total_documents": 15,
                "total_size_bytes": 50000000,
                "documents_by_jurisdiction": {
                    "DIFC": 10,
                    "DFSA": 3,
                    "UAE": 2
                },
                "documents_by_type": {
                    "Law": 5,
                    "Regulation": 4,
                    "Contract": 6
                },
                "recent_uploads": 3,
                "last_activity": "2024-01-15T00:00:00Z"
            }
            
            response = await client_with_lifespan.get(f"/api/vault/projects/{project_id}/analytics")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "total_documents" in data
            assert "documents_by_jurisdiction" in data
            assert data["documents_by_jurisdiction"]["DIFC"] >= data["documents_by_jurisdiction"]["DFSA"]
    
    @pytest.mark.asyncio
    async def test_user_vault_summary(self, client_with_lifespan):
        """Test getting user's vault summary."""
        with patch('api.vault.get_user_vault_summary') as mock_summary:
            mock_summary.return_value = {
                "total_projects": 5,
                "total_documents": 50,
                "storage_used_bytes": 150000000,
                "recent_projects": [
                    {"id": "proj-1", "name": "DIFC Contracts", "last_activity": "2024-01-15T00:00:00Z"},
                    {"id": "proj-2", "name": "DFSA Analysis", "last_activity": "2024-01-14T00:00:00Z"}
                ]
            }
            
            response = await client_with_lifespan.get("/api/vault/summary")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "total_projects" in data
            assert "recent_projects" in data
            assert len(data["recent_projects"]) <= 10  # Should limit recent projects


@pytest.mark.integration
class TestVaultIntegration:
    """Integration tests for vault functionality."""
    
    @pytest.mark.asyncio
    async def test_complete_project_workflow(self, client_with_lifespan):
        """Test complete workflow: create project, upload document, search, delete."""
        # 1. Create project
        project_data = {"name": "Integration Test Project", "visibility": "private"}
        
        with patch('api.vault.create_project') as mock_create, \
             patch('api.vault.save_uploaded_file') as mock_save, \
             patch('api.vault.store_document_metadata') as mock_store, \
             patch('rag.retrievers.difc_retriever') as mock_retriever, \
             patch('api.vault.delete_project') as mock_delete:
            
            # Mock project creation
            mock_create.return_value = VaultProject(
                id="integration-project",
                name="Integration Test Project",
                visibility="private",
                document_count=0,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
                owner="test-user@example.com"
            )
            
            create_response = await client_with_lifespan.post("/api/vault/projects", json=project_data)
            assert create_response.status_code == 201
            project_id = create_response.json()["id"]
            
            # 2. Upload document
            file_content = b"Test DIFC law document content"
            files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
            
            mock_save.return_value = "/data/files/test.pdf"
            mock_store.return_value = DocumentMetadata(
                id="test-doc",
                project_id=project_id,
                filename="test.pdf",
                title="Test Document",
                file_path="/data/files/test.pdf",
                content_type="application/pdf",
                size_bytes=len(file_content),
                jurisdiction=JurisdictionType.DIFC,
                instrument_type="Law",
                upload_date="2024-01-01T00:00:00Z"
            )
            
            upload_response = await client_with_lifespan.post(
                f"/api/vault/projects/{project_id}/documents",
                files=files
            )
            assert upload_response.status_code == 201
            
            # 3. Search documents
            mock_retriever.search_project_documents.return_value = [
                {"document_id": "test-doc", "title": "Test Document", "score": 0.9}
            ]
            
            search_response = await client_with_lifespan.get(
                f"/api/vault/projects/{project_id}/search",
                params={"query": "DIFC law"}
            )
            assert search_response.status_code == 200
            assert len(search_response.json()["results"]) > 0
            
            # 4. Delete project
            mock_delete.return_value = {"success": True}
            delete_response = await client_with_lifespan.delete(f"/api/vault/projects/{project_id}")
            assert delete_response.status_code == 200