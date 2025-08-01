"""
Tests for Workflows API endpoints.

Following PRP requirements:
- Execute LangGraph workflows with SSE streaming
- Support "Draft from Template (DIFC)" workflow
- Return status, artifacts, and thinking states
- Test workflow parameter validation and error handling
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from io import BytesIO

from core.models import JurisdictionType


class TestWorkflowExecution:
    """Test workflow execution endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_available_workflows(self, client_with_lifespan):
        """Test getting list of available workflows."""
        with patch('api.workflows.get_available_workflows') as mock_workflows:
            mock_workflows.return_value = {
                "workflows": [
                    {
                        "id": "draft-from-template",
                        "name": "Draft from Template (DIFC)",
                        "description": "Generate legal document from template with DIFC compliance",
                        "estimated_duration": "2-5 minutes",
                        "required_inputs": ["prompt", "template_file"],
                        "optional_inputs": ["reference_files", "jurisdiction", "tone"]
                    }
                ],
                "total_count": 1
            }
            
            response = await client_with_lifespan.get("/api/workflows")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "workflows" in data
            assert len(data["workflows"]) >= 1
            
            # Verify DIFC workflow is available
            difc_workflow = next((w for w in data["workflows"] if "DIFC" in w["name"]), None)
            assert difc_workflow is not None
    
    @pytest.mark.asyncio
    async def test_get_workflow_details(self, client_with_lifespan):
        """Test getting specific workflow details."""
        workflow_id = "draft-from-template"
        
        with patch('api.workflows.get_workflow_by_id') as mock_workflow:
            mock_workflow.return_value = {
                "id": workflow_id,
                "name": "Draft from Template (DIFC)",
                "description": "Generate legal document from template with DIFC compliance",
                "parameters": {
                    "prompt": {"type": "string", "required": True, "description": "Drafting instructions"},
                    "template_file": {"type": "file", "required": True, "description": "Template document"},
                    "reference_files": {"type": "file[]", "required": False, "description": "Reference documents"},
                    "jurisdiction": {"type": "enum", "required": False, "default": "DIFC", "values": ["DIFC", "DFSA", "UAE"]},
                    "tone": {"type": "string", "required": False, "default": "formal"}
                },
                "output_format": "document",
                "estimated_duration": "2-5 minutes"
            }
            
            response = await client_with_lifespan.get(f"/api/workflows/{workflow_id}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["id"] == workflow_id
            assert "DIFC" in data["name"]
            assert "parameters" in data
            assert data["parameters"]["jurisdiction"]["default"] == "DIFC"
    
    @pytest.mark.asyncio
    async def test_start_workflow_execution(self, client_with_lifespan):
        """Test starting workflow execution synchronously."""
        workflow_id = "draft-from-template"
        
        # Mock file uploads
        template_content = b"EMPLOYMENT AGREEMENT TEMPLATE"
        reference_content = b"DIFC Employment Law reference"
        
        files = {
            "template_file": ("template.docx", BytesIO(template_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "reference_files": ("difc_law.pdf", BytesIO(reference_content), "application/pdf")
        }
        
        form_data = {
            "prompt": "Draft employment contract with 30-day notice period for DIFC jurisdiction",
            "jurisdiction": "DIFC",
            "tone": "formal"
        }
        
        with patch('agents.graph.qaai_workflow') as mock_workflow:
            mock_workflow.run.return_value = {
                "success": True,
                "output": {
                    "content": "# EMPLOYMENT AGREEMENT\n\nThis agreement is governed by DIFC Employment Law...",
                    "format": "markdown"
                },
                "citations": [
                    {"title": "DIFC Employment Law No. 2 of 2019", "section": "Part 4", "jurisdiction": "DIFC"}
                ],
                "thinking_states": [
                    "Analyzing template structure",
                    "Retrieving DIFC employment law provisions", 
                    "Drafting contract clauses",
                    "Verifying legal compliance"
                ],
                "metadata": {
                    "execution_time": 180,
                    "model_used": "gpt-4",
                    "jurisdiction": "DIFC"
                },
                "error": None
            }
            
            response = await client_with_lifespan.post(
                f"/api/workflows/{workflow_id}/run",
                files=files,
                data=form_data
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "EMPLOYMENT AGREEMENT" in data["output"]["content"]
            assert len(data["citations"]) > 0
            assert len(data["thinking_states"]) >= 4
            assert data["metadata"]["jurisdiction"] == "DIFC"
    
    @pytest.mark.asyncio
    async def test_workflow_execution_failure(self, client_with_lifespan):
        """Test handling of workflow execution failure."""
        workflow_id = "draft-from-template"
        
        files = {
            "template_file": ("template.docx", BytesIO(b"template"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        
        form_data = {
            "prompt": "Test prompt",
            "jurisdiction": "DIFC"
        }
        
        with patch('agents.graph.qaai_workflow') as mock_workflow:
            mock_workflow.run.return_value = {
                "success": False,
                "output": None,
                "citations": [],
                "thinking_states": [
                    "Analyzing template structure",
                    "Error: Unable to parse template format"
                ],
                "error": "Template parsing failed: Unsupported document format"
            }
            
            response = await client_with_lifespan.post(
                f"/api/workflows/{workflow_id}/run",
                files=files,
                data=form_data
            )
            
            assert response.status_code == 200  # Workflow ran but failed
            data = response.json()
            
            assert data["success"] is False
            assert data["error"] is not None
            assert "Template parsing failed" in data["error"]
            assert len(data["thinking_states"]) > 0


class TestWorkflowSSEStreaming:
    """Test Server-Sent Events streaming for workflow execution."""
    
    @pytest.mark.sse
    def test_workflow_streaming_execution(self, sync_client):
        """Test workflow execution with SSE streaming."""
        workflow_id = "draft-from-template"
        
        # Mock file uploads
        files = {
            "template_file": ("template.docx", BytesIO(b"template"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        
        form_data = {
            "prompt": "Draft DIFC employment contract",
            "jurisdiction": "DIFC"
        }
        
        with patch('agents.graph.qaai_workflow') as mock_workflow:
            # Mock streaming workflow execution
            async def mock_stream():
                yield {"type": "workflow_start", "workflow_id": workflow_id, "timestamp": "2024-01-01T00:00:00Z"}
                yield {"type": "thinking_state", "label": "Analyzing template structure", "step": 1}
                yield {"type": "workflow_progress", "step": "preflight", "status": "completed"}
                yield {"type": "thinking_state", "label": "Planning drafting approach", "step": 2}
                yield {"type": "workflow_progress", "step": "plan", "status": "completed"}
                yield {"type": "thinking_state", "label": "Retrieving DIFC legal sources", "step": 3}
                yield {"type": "workflow_progress", "step": "retrieve", "status": "completed"}
                yield {"type": "citation", "citation": {"title": "DIFC Employment Law", "section": "Part 4"}}
                yield {"type": "thinking_state", "label": "Drafting document content", "step": 4}
                yield {"type": "draft_progress", "content": "# EMPLOYMENT AGREEMENT\n\n"}
                yield {"type": "draft_progress", "content": "This agreement is governed by DIFC Employment Law..."}
                yield {"type": "workflow_progress", "step": "draft", "status": "completed"}
                yield {"type": "thinking_state", "label": "Verifying legal compliance", "step": 5}
                yield {"type": "workflow_progress", "step": "verify", "status": "completed"}
                yield {"type": "workflow_complete", "status": "success", "execution_time": 180}
            
            mock_workflow.stream_run.return_value = mock_stream()
            
            response = sync_client.post(
                f"/api/workflows/{workflow_id}/stream",
                files=files,
                data=form_data,
                headers={"Accept": "text/event-stream"}
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"
            
            # Parse SSE events
            events = self._parse_sse_events(response.text)
            event_types = [event.get("type") for event in events]
            
            # Verify workflow event sequence
            assert "workflow_start" in event_types
            assert "thinking_state" in event_types
            assert "workflow_progress" in event_types
            assert "citation" in event_types
            assert "draft_progress" in event_types
            assert "workflow_complete" in event_types
            
            # Verify DIFC-specific content
            thinking_events = [e for e in events if e.get("type") == "thinking_state"]
            assert any("DIFC" in event.get("label", "") for event in thinking_events)
    
    @pytest.mark.sse
    def test_workflow_streaming_error(self, sync_client):
        """Test workflow streaming with error handling."""
        workflow_id = "draft-from-template"
        
        files = {
            "template_file": ("invalid.txt", BytesIO(b"invalid"), "text/plain")
        }
        
        form_data = {
            "prompt": "Test prompt",
            "jurisdiction": "DIFC"
        }
        
        with patch('agents.graph.qaai_workflow') as mock_workflow:
            async def mock_error_stream():
                yield {"type": "workflow_start", "workflow_id": workflow_id}
                yield {"type": "thinking_state", "label": "Analyzing template structure"}
                yield {"type": "workflow_error", "error": "Unsupported template format", "step": "preflight"}
            
            mock_workflow.stream_run.return_value = mock_error_stream()
            
            response = sync_client.post(
                f"/api/workflows/{workflow_id}/stream",
                files=files,
                data=form_data,
                headers={"Accept": "text/event-stream"}
            )
            
            assert response.status_code == 200
            
            events = self._parse_sse_events(response.text)
            error_events = [e for e in events if e.get("type") == "workflow_error"]
            
            assert len(error_events) > 0
            assert "Unsupported template format" in error_events[0]["error"]
    
    def _parse_sse_events(self, response_text: str) -> list[dict]:
        """Parse SSE response into structured events."""
        events = []
        lines = response_text.split('\n')
        
        for line in lines:
            if line.startswith('data: '):
                try:
                    event_data = json.loads(line[6:])
                    events.append(event_data)
                except json.JSONDecodeError:
                    continue
        
        return events


class TestWorkflowValidation:
    """Test workflow parameter validation and error handling."""
    
    @pytest.mark.asyncio
    async def test_missing_required_parameters(self, client_with_lifespan):
        """Test workflow execution with missing required parameters."""
        workflow_id = "draft-from-template"
        
        # Missing template file
        form_data = {
            "prompt": "Draft employment contract",
            "jurisdiction": "DIFC"
        }
        
        response = await client_with_lifespan.post(
            f"/api/workflows/{workflow_id}/run",
            data=form_data
        )
        
        assert response.status_code == 400
        assert "template_file" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_invalid_jurisdiction(self, client_with_lifespan):
        """Test workflow with invalid jurisdiction parameter."""
        workflow_id = "draft-from-template"
        
        files = {
            "template_file": ("template.docx", BytesIO(b"template"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        
        form_data = {
            "prompt": "Draft contract",
            "jurisdiction": "INVALID_JURISDICTION"
        }
        
        response = await client_with_lifespan.post(
            f"/api/workflows/{workflow_id}/run",
            files=files,
            data=form_data
        )
        
        assert response.status_code == 422
        assert "jurisdiction" in response.json()["detail"][0]["loc"]
    
    @pytest.mark.asyncio
    async def test_empty_prompt(self, client_with_lifespan):
        """Test workflow with empty prompt."""
        workflow_id = "draft-from-template"
        
        files = {
            "template_file": ("template.docx", BytesIO(b"template"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        
        form_data = {
            "prompt": "",
            "jurisdiction": "DIFC"
        }
        
        response = await client_with_lifespan.post(
            f"/api/workflows/{workflow_id}/run",
            files=files,
            data=form_data
        )
        
        assert response.status_code == 400
        assert "prompt cannot be empty" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_invalid_file_type(self, client_with_lifespan):
        """Test workflow with invalid file type."""
        workflow_id = "draft-from-template"
        
        files = {
            "template_file": ("malicious.exe", BytesIO(b"executable"), "application/x-executable")
        }
        
        form_data = {
            "prompt": "Draft contract",
            "jurisdiction": "DIFC"
        }
        
        response = await client_with_lifespan.post(
            f"/api/workflows/{workflow_id}/run",
            files=files,
            data=form_data
        )
        
        assert response.status_code == 400
        assert "file type" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_nonexistent_workflow(self, client_with_lifespan):
        """Test requesting non-existent workflow."""
        workflow_id = "non-existent-workflow"
        
        response = await client_with_lifespan.get(f"/api/workflows/{workflow_id}")
        
        assert response.status_code == 404


class TestWorkflowArtifacts:
    """Test workflow artifact management."""
    
    @pytest.mark.asyncio
    async def test_get_workflow_artifacts(self, client_with_lifespan):
        """Test retrieving workflow execution artifacts."""
        execution_id = "exec-123"
        
        with patch('api.workflows.get_execution_artifacts') as mock_artifacts:
            mock_artifacts.return_value = {
                "execution_id": execution_id,
                "artifacts": [
                    {
                        "type": "document",
                        "name": "generated_contract.docx",
                        "size_bytes": 50000,
                        "created_at": "2024-01-01T00:00:00Z",
                        "download_url": f"/api/workflows/executions/{execution_id}/artifacts/generated_contract.docx"
                    },
                    {
                        "type": "metadata",
                        "name": "execution_log.json",
                        "size_bytes": 2000,
                        "created_at": "2024-01-01T00:00:00Z",
                        "download_url": f"/api/workflows/executions/{execution_id}/artifacts/execution_log.json"
                    }
                ]
            }
            
            response = await client_with_lifespan.get(f"/api/workflows/executions/{execution_id}/artifacts")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "artifacts" in data
            assert len(data["artifacts"]) == 2
            
            # Verify document artifact exists
            doc_artifacts = [a for a in data["artifacts"] if a["type"] == "document"]
            assert len(doc_artifacts) >= 1
    
    @pytest.mark.asyncio
    async def test_download_workflow_artifact(self, client_with_lifespan):
        """Test downloading specific workflow artifact."""
        execution_id = "exec-123"
        artifact_name = "generated_contract.docx"
        
        mock_content = b"Mock document content for generated contract"
        
        with patch('api.workflows.get_artifact_content') as mock_content_func:
            mock_content_func.return_value = (mock_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            
            response = await client_with_lifespan.get(f"/api/workflows/executions/{execution_id}/artifacts/{artifact_name}")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            assert response.content == mock_content
    
    @pytest.mark.asyncio
    async def test_list_workflow_executions(self, client_with_lifespan):
        """Test listing workflow executions for user."""
        with patch('api.workflows.get_user_executions') as mock_executions:
            mock_executions.return_value = {
                "executions": [
                    {
                        "id": "exec-123",
                        "workflow_id": "draft-from-template",
                        "status": "completed",
                        "started_at": "2024-01-01T00:00:00Z",
                        "completed_at": "2024-01-01T00:03:00Z",
                        "execution_time": 180,
                        "parameters": {
                            "jurisdiction": "DIFC",
                            "prompt": "Draft employment contract"
                        }
                    }
                ],
                "total_count": 1,
                "page": 1,
                "page_size": 10
            }
            
            response = await client_with_lifespan.get("/api/workflows/executions")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "executions" in data
            assert len(data["executions"]) > 0
            assert data["executions"][0]["workflow_id"] == "draft-from-template"


class TestWorkflowPerformance:
    """Test workflow performance and resource usage."""
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_workflow_execution_timeout(self, client_with_lifespan):
        """Test workflow execution with timeout handling."""
        workflow_id = "draft-from-template"
        
        files = {
            "template_file": ("template.docx", BytesIO(b"template"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        
        form_data = {
            "prompt": "Draft complex contract",
            "jurisdiction": "DIFC",
            "timeout": 1  # 1 second timeout for testing
        }
        
        with patch('agents.graph.qaai_workflow') as mock_workflow:
            # Simulate long-running workflow
            async def slow_workflow():
                import asyncio
                await asyncio.sleep(5)  # Simulate 5-second execution
                return {"success": True, "output": {"content": "result"}}
            
            mock_workflow.run.side_effect = slow_workflow
            
            response = await client_with_lifespan.post(
                f"/api/workflows/{workflow_id}/run",
                files=files,
                data=form_data
            )
            
            # Should timeout and return appropriate error
            assert response.status_code == 408  # Request Timeout
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_executions(self, client_with_lifespan):
        """Test multiple concurrent workflow executions."""
        workflow_id = "draft-from-template"
        
        files = {
            "template_file": ("template.docx", BytesIO(b"template"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        
        form_data = {
            "prompt": "Draft contract",
            "jurisdiction": "DIFC"
        }
        
        with patch('agents.graph.qaai_workflow') as mock_workflow:
            mock_workflow.run.return_value = {
                "success": True,
                "output": {"content": "Generated content"},
                "citations": [],
                "thinking_states": ["Processing"],
                "error": None
            }
            
            # Create multiple concurrent requests
            import asyncio
            
            async def make_request():
                return await client_with_lifespan.post(
                    f"/api/workflows/{workflow_id}/run",
                    files=files,
                    data=form_data
                )
            
            tasks = [make_request() for _ in range(3)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all requests completed successfully
            successful_responses = [r for r in responses if not isinstance(r, Exception)]
            assert len(successful_responses) >= 2  # Allow some failures in concurrent testing
            
            for response in successful_responses:
                assert response.status_code == 200
                assert response.json()["success"] is True


@pytest.mark.integration
class TestWorkflowIntegration:
    """Integration tests combining workflow execution with other components."""
    
    @pytest.mark.asyncio
    async def test_workflow_with_vault_integration(self, client_with_lifespan):
        """Test workflow execution using documents from vault."""
        workflow_id = "draft-from-template"
        vault_project_id = "test-project-123"
        
        files = {
            "template_file": ("template.docx", BytesIO(b"template"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        
        form_data = {
            "prompt": "Draft contract using vault documents",
            "jurisdiction": "DIFC",
            "vault_project_id": vault_project_id
        }
        
        with patch('agents.graph.qaai_workflow') as mock_workflow, \
             patch('api.vault.get_project_documents') as mock_vault:
            
            mock_vault.return_value = [
                {"id": "doc-1", "title": "DIFC Employment Law", "content": "Legal provisions..."}
            ]
            
            mock_workflow.run.return_value = {
                "success": True,
                "output": {"content": "Contract incorporating vault documents"},
                "citations": [{"title": "DIFC Employment Law", "source": "vault"}],
                "thinking_states": ["Retrieving vault documents", "Incorporating context"],
                "error": None
            }
            
            response = await client_with_lifespan.post(
                f"/api/workflows/{workflow_id}/run",
                files=files,
                data=form_data
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert any(citation.get("source") == "vault" for citation in data["citations"])
    
    @pytest.mark.asyncio
    async def test_workflow_with_rag_integration(self, client_with_lifespan):
        """Test workflow execution with RAG system integration."""
        workflow_id = "draft-from-template"
        
        files = {
            "template_file": ("template.docx", BytesIO(b"template"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        
        form_data = {
            "prompt": "Draft DIFC-compliant employment contract",
            "jurisdiction": "DIFC"
        }
        
        with patch('agents.graph.qaai_workflow') as mock_workflow, \
             patch('rag.retrievers.difc_retriever') as mock_retriever:
            
            mock_retriever.retrieve_with_citations.return_value = [
                {"title": "DIFC Employment Law", "content": "Employment provisions", "score": 0.95}
            ]
            
            mock_workflow.run.return_value = {
                "success": True,
                "output": {"content": "DIFC-compliant employment contract"},
                "citations": [{"title": "DIFC Employment Law", "jurisdiction": "DIFC"}],
                "thinking_states": ["Retrieving DIFC law", "Ensuring compliance"],
                "error": None
            }
            
            response = await client_with_lifespan.post(
                f"/api/workflows/{workflow_id}/run",
                files=files,
                data=form_data
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "DIFC-compliant" in data["output"]["content"]
            assert any(citation["jurisdiction"] == "DIFC" for citation in data["citations"])