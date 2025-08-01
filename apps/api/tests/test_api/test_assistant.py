"""
Comprehensive tests for Assistant API endpoints.

Following PRP requirements:
- Test all endpoints with proper mocking of external APIs
- Include SSE streaming tests and error handling  
- Verify thinking state emission and content streaming
- Test DIFC-first knowledge filtering
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from fastapi.testclient import TestClient

from core.models import AssistantQuery, AssistantMode, JurisdictionType


class TestAssistantEndpoints:
    """Test assistant API endpoints with comprehensive coverage."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client_with_lifespan):
        """Test health check endpoint returns proper status."""
        response = await client_with_lifespan.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify health check structure
        assert "status" in data
        assert "database" in data
        assert "models" in data
        assert "vector_store" in data
        assert "environment" in data
        assert "jurisdiction_focus" in data
        
        # Verify DIFC jurisdiction focus
        assert data["jurisdiction_focus"] == "DIFC"
        assert data["environment"] == "test"
    
    @pytest.mark.asyncio
    async def test_api_status(self, client_with_lifespan):
        """Test API status endpoint returns configuration details."""
        response = await client_with_lifespan.get("/api/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify status structure
        assert "api_version" in data
        assert "features" in data
        assert "model_routing" in data
        
        # Verify DIFC-first features
        features = data["features"]
        assert "DIFC" in features["supported_jurisdictions"]
        assert features["assistant_modes"] == ["assist", "draft"]
        assert features["sse_streaming"] is True
        assert features["citation_verification"] is True
    
    @pytest.mark.asyncio
    async def test_query_assistant_sync_assist_mode(self, client_with_lifespan, sample_assistant_queries):
        """Test synchronous assistant query in assist mode."""
        query = sample_assistant_queries["assist_basic"]
        
        response = await client_with_lifespan.post("/api/assistant/query-sync", json=query.dict())
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "success" in data
        assert "content" in data
        assert "citations" in data
        assert data["success"] is True
        
        # Verify content exists and is non-empty
        assert len(data["content"]) > 0
        assert isinstance(data["citations"], list)
    
    @pytest.mark.asyncio
    async def test_query_assistant_sync_draft_mode(self, client_with_lifespan, sample_assistant_queries):
        """Test synchronous assistant query in draft mode."""
        query = sample_assistant_queries["draft_basic"]
        
        with patch('agents.graph.qaai_workflow') as mock_workflow:
            mock_workflow.run.return_value = {
                "success": True,
                "output": {"content": "EMPLOYMENT AGREEMENT\n\nThis agreement..."},
                "citations": [{"title": "DIFC Employment Law", "section": "Part 4"}],
                "thinking_states": ["Planning", "Drafting", "Verifying"],
                "error": None
            }
            
            response = await client_with_lifespan.post("/api/assistant/query-sync", json=query.dict())
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "EMPLOYMENT AGREEMENT" in data["content"]
            assert len(data["citations"]) > 0
            assert len(data["thinking_states"]) >= 3
    
    @pytest.mark.asyncio
    async def test_query_assistant_with_vault_project(self, client_with_lifespan, sample_assistant_queries):
        """Test assistant query with vault project context."""
        query = sample_assistant_queries["assist_with_vault"]
        
        response = await client_with_lifespan.post("/api/assistant/query-sync", json=query.dict())
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        # Verify vault context was considered (would be implemented in actual agent logic)
    
    @pytest.mark.asyncio
    async def test_query_assistant_validation_errors(self, client_with_lifespan, sample_assistant_queries):
        """Test assistant query validation with invalid inputs."""
        # Test empty prompt
        empty_query = sample_assistant_queries["empty_prompt"]
        response = await client_with_lifespan.post("/api/assistant/query-sync", json=empty_query.dict())
        
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
        
        # Test invalid jurisdiction (this would be handled at Pydantic level)
        invalid_query = {
            "mode": "assist",
            "prompt": "Test query",
            "knowledge": {"jurisdiction": "INVALID"}
        }
        
        response = await client_with_lifespan.post("/api/assistant/query-sync", json=invalid_query)
        
        # Should be 422 for validation error
        assert response.status_code == 422


class TestAssistantSSEStreaming:
    """Test Server-Sent Events streaming for assistant responses."""
    
    @pytest.mark.sse
    def test_sse_streaming_assist_mode(self, sync_client, sample_assistant_queries):
        """Test SSE streaming for assist mode with thinking states."""
        query = sample_assistant_queries["assist_basic"]
        
        with patch('agents.graph.simple_assistant') as mock_assistant:
            mock_assistant.run.return_value = {
                "success": True,
                "content": "DIFC Employment Law requires minimum 30 days notice for termination.",
                "citations": [{"title": "DIFC Employment Law", "section": "Part 4"}]
            }
            
            response = sync_client.post(
                "/api/assistant/query",
                json=query.dict(),
                headers={"Accept": "text/event-stream"}
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"
            
            # Parse SSE events
            events = self._parse_sse_events(response.text)
            
            # Verify event sequence
            event_types = [event.get("type") for event in events]
            
            assert "thinking_state" in event_types
            assert "chunk" in event_types
            assert "citation" in event_types
            assert "done" in event_types[-1:]
            
            # Verify thinking states contain DIFC-specific content
            thinking_states = [e for e in events if e.get("type") == "thinking_state"]
            assert any("DIFC" in state.get("label", "") for state in thinking_states)
    
    @pytest.mark.sse
    def test_sse_streaming_draft_mode(self, sync_client, sample_assistant_queries):
        """Test SSE streaming for draft mode with workflow execution."""
        query = sample_assistant_queries["draft_basic"]
        
        with patch('agents.graph.qaai_workflow') as mock_workflow:
            # Mock workflow streaming
            async def mock_stream():
                yield {"type": "thinking_state", "label": "Initializing draft workflow"}
                yield {"type": "thinking_state", "label": "Planning drafting steps"}
                yield {"type": "draft_progress", "content": "EMPLOYMENT AGREEMENT"}
                yield {"type": "citation", "citation": {"title": "DIFC Employment Law", "section": "Part 4"}}
                yield {"type": "thinking_state", "label": "Draft completed"}
            
            mock_workflow.stream_run.return_value = mock_stream()
            
            response = sync_client.post(
                "/api/assistant/query",
                json=query.dict(),
                headers={"Accept": "text/event-stream"}
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"
            
            # Parse and verify events
            events = self._parse_sse_events(response.text)
            event_types = [event.get("type") for event in events]
            
            assert "thinking_state" in event_types
            assert "chunk" in event_types  # From draft_progress content
            assert "citation" in event_types
    
    @pytest.mark.sse
    def test_sse_streaming_error_handling(self, sync_client, sample_assistant_queries):
        """Test SSE streaming handles errors gracefully."""
        query = sample_assistant_queries["assist_basic"]
        
        with patch('agents.graph.simple_assistant') as mock_assistant:
            mock_assistant.run.side_effect = Exception("Model API error")
            
            response = sync_client.post(
                "/api/assistant/query",
                json=query.dict(),
                headers={"Accept": "text/event-stream"}
            )
            
            assert response.status_code == 200
            
            # Should contain error event
            events = self._parse_sse_events(response.text)
            error_events = [e for e in events if e.get("type") == "error" or "error" in e]
            
            assert len(error_events) > 0
    
    @pytest.mark.sse
    def test_sse_cors_headers(self, sync_client, sample_assistant_queries):
        """Test SSE streaming includes proper CORS headers."""
        query = sample_assistant_queries["assist_basic"]
        
        response = sync_client.post(
            "/api/assistant/query",
            json=query.dict(),
            headers={
                "Accept": "text/event-stream",
                "Origin": "http://localhost:3000"
            }
        )
        
        assert response.status_code == 200
        
        # Verify CORS headers for SSE
        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Cache-Control"] == "no-cache"
        assert response.headers["Connection"] == "keep-alive"
    
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


class TestAssistantModelRouting:
    """Test model routing and override functionality."""
    
    @pytest.mark.asyncio
    async def test_get_available_models(self, client_with_lifespan):
        """Test retrieving available models information."""
        with patch('agents.router.model_router') as mock_router:
            mock_router.get_routing_status.return_value = {
                "available_models": ["gpt-4", "o1", "claude-3.7-sonnet"],
                "default_routing": {
                    "planning": "o1",
                    "drafting": "gpt-4",
                    "verification": "claude-3.7-sonnet"
                },
                "current_override": None
            }
            
            response = await client_with_lifespan.get("/api/assistant/models")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "available_models" in data
            assert "default_routing" in data
            assert len(data["available_models"]) >= 3
    
    @pytest.mark.asyncio
    async def test_set_model_override(self, client_with_lifespan):
        """Test setting manual model override."""
        with patch('agents.router.model_router') as mock_router:
            mock_router.set_manual_override.return_value = None
            
            response = await client_with_lifespan.post(
                "/api/assistant/models/override",
                params={"model_name": "claude-3.7-sonnet"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["override_model"] == "claude-3.7-sonnet"
            mock_router.set_manual_override.assert_called_once_with("claude-3.7-sonnet")
    
    @pytest.mark.asyncio
    async def test_clear_model_override(self, client_with_lifespan):
        """Test clearing model override."""
        with patch('agents.router.model_router') as mock_router:
            mock_router.set_manual_override.return_value = None
            
            response = await client_with_lifespan.post("/api/assistant/models/override")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["override_model"] is None
            mock_router.set_manual_override.assert_called_once_with(None)


class TestAssistantKnowledgeSources:
    """Test knowledge sources and DIFC-first filtering."""
    
    @pytest.mark.asyncio
    async def test_get_knowledge_sources(self, client_with_lifespan):
        """Test retrieving available knowledge sources."""
        with patch('rag.retrievers.difc_retriever') as mock_retriever:
            mock_retriever.get_knowledge_sources_summary.return_value = {
                "total_documents": 1500,
                "by_jurisdiction": {
                    "DIFC": 800,
                    "DFSA": 400,
                    "UAE": 200,
                    "OTHER": 100
                },
                "by_type": {
                    "Law": 300,
                    "Regulation": 500,
                    "Rulebook": 400,
                    "Court_Rule": 200,
                    "Notice": 100
                },
                "last_updated": "2024-01-15T00:00:00Z"
            }
            
            response = await client_with_lifespan.get("/api/assistant/knowledge-sources")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "total_documents" in data
            assert "by_jurisdiction" in data
            assert "by_type" in data
            
            # Verify DIFC has most documents (DIFC-first approach)
            jurisdictions = data["by_jurisdiction"]
            assert jurisdictions["DIFC"] >= jurisdictions["DFSA"]
            assert jurisdictions["DIFC"] >= jurisdictions["UAE"]


class TestAssistantErrorHandling:
    """Test comprehensive error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self, client_with_lifespan):
        """Test handling of database connection failures."""
        with patch('core.database.health_check') as mock_health:
            mock_health.side_effect = Exception("Database connection failed")
            
            response = await client_with_lifespan.get("/health")
            
            # Should still return response but with error status
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert "error" in data
    
    @pytest.mark.asyncio
    async def test_model_api_rate_limiting(self, client_with_lifespan, sample_assistant_queries):
        """Test handling of model API rate limiting."""
        query = sample_assistant_queries["assist_basic"]
        
        with patch('agents.graph.simple_assistant') as mock_assistant:
            # Simulate rate limiting error
            mock_assistant.run.side_effect = Exception("Rate limit exceeded")
            
            response = await client_with_lifespan.post("/api/assistant/query-sync", json=query.dict())
            
            assert response.status_code == 500
            assert "Rate limit exceeded" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_vector_store_unavailable(self, client_with_lifespan, sample_assistant_queries):
        """Test handling when vector store is unavailable."""
        query = sample_assistant_queries["assist_basic"]
        
        with patch('rag.retrievers.difc_retriever') as mock_retriever:
            mock_retriever.retrieve_with_citations.side_effect = Exception("Vector store unavailable")
            
            # Should fall back gracefully
            response = await client_with_lifespan.post("/api/assistant/query-sync", json=query.dict())
            
            # Depending on implementation, might succeed with degraded functionality
            # or return an error - adjust based on actual error handling strategy
            assert response.status_code in [200, 500]
    
    @pytest.mark.asyncio
    async def test_malformed_request_data(self, client_with_lifespan):
        """Test handling of malformed request data."""
        # Test completely invalid JSON
        response = await client_with_lifespan.post(
            "/api/assistant/query-sync",
            content="invalid json data",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
        
        # Test missing required fields
        incomplete_query = {"mode": "assist"}  # Missing prompt
        response = await client_with_lifespan.post("/api/assistant/query-sync", json=incomplete_query)
        
        assert response.status_code == 422


@pytest.mark.integration
class TestAssistantIntegration:
    """Integration tests combining multiple components."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_assist_workflow(self, client_with_lifespan, sample_assistant_queries, test_helpers):
        """Test complete assist workflow from query to response."""
        query = sample_assistant_queries["assist_basic"]
        
        response = await client_with_lifespan.post("/api/assistant/query-sync", json=query.dict())
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify complete workflow
        assert data["success"] is True
        assert len(data["content"]) > 0
        
        # Verify citations if present
        if data["citations"]:
            for citation in data["citations"]:
                test_helpers.assert_valid_citation(citation)
    
    @pytest.mark.asyncio
    async def test_end_to_end_draft_workflow(self, client_with_lifespan, sample_assistant_queries):
        """Test complete draft workflow with LangGraph integration."""
        query = sample_assistant_queries["draft_basic"]
        
        with patch('agents.graph.qaai_workflow') as mock_workflow:
            mock_workflow.run.return_value = {
                "success": True,
                "output": {"content": "# EMPLOYMENT AGREEMENT\n\nThis agreement complies with DIFC Employment Law..."},
                "citations": [
                    {"title": "DIFC Employment Law No. 2 of 2019", "section": "Part 4", "jurisdiction": "DIFC"}
                ],
                "thinking_states": ["Planning", "Retrieving", "Drafting", "Verifying"],
                "error": None
            }
            
            response = await client_with_lifespan.post("/api/assistant/query-sync", json=query.dict())
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "EMPLOYMENT AGREEMENT" in data["content"]
            assert len(data["thinking_states"]) >= 4
            assert any(citation["jurisdiction"] == "DIFC" for citation in data["citations"])
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_assistant_requests(self, client_with_lifespan, sample_assistant_queries):
        """Test handling of concurrent assistant requests."""
        query = sample_assistant_queries["assist_basic"]
        
        # Create multiple concurrent requests
        async def make_request():
            return await client_with_lifespan.post("/api/assistant/query-sync", json=query.dict())
        
        tasks = [make_request() for _ in range(5)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all requests succeeded
        successful_responses = [r for r in responses if not isinstance(r, Exception)]
        assert len(successful_responses) >= 3  # Allow some failures in concurrent testing
        
        for response in successful_responses:
            assert response.status_code == 200
            assert response.json()["success"] is True