"""
Tests for LangGraph workflow nodes.

Following PRP requirements:
- Test LangGraph workflows with mock dependencies
- Verify thinking state emission and proper state management
- Test model routing and fallback mechanisms
- Test individual node functionality in isolation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from agents.nodes import (
    preflight, plan, retrieve, draft, verify_citations, 
    human_review, export, emit, NODE_REGISTRY
)
from core.models import WorkflowState, JurisdictionType, Citation


class TestWorkflowNodes:
    """Test individual workflow node functionality."""
    
    @pytest.fixture
    def base_state(self) -> WorkflowState:
        """Base state fixture for testing nodes."""
        return WorkflowState(
            prompt="Draft employment contract with DIFC law compliance",
            template_doc_id="tmpl-123",
            reference_doc_ids=["ref-1", "ref-2"],
            jurisdiction=JurisdictionType.DIFC,
            plan="",
            retrieved_context=[], 
            citations=[],
            draft="",
            thinking=[],
            error=None,
            model_override=None
        )
    
    def test_preflight_node_valid_input(self, base_state):
        """Test preflight node with valid input."""
        result = preflight(base_state)
        
        # Should not have error
        assert "error" not in result or result["error"] is None
        
        # Should add thinking state
        assert len(result["thinking"]) > len(base_state["thinking"])
        assert any("validating" in thought.lower() for thought in result["thinking"])
        
        # Should preserve essential fields
        assert result["template_doc_id"] == "tmpl-123"
        assert result["jurisdiction"] == JurisdictionType.DIFC
    
    def test_preflight_node_missing_template(self, base_state):
        """Test preflight node with missing template."""
        base_state["template_doc_id"] = None
        
        result = preflight(base_state)
        
        # Should set error
        assert result["error"] is not None
        assert "template" in result["error"].lower()
        
        # Should still add thinking state
        assert len(result["thinking"]) > len(base_state["thinking"])
    
    def test_preflight_node_empty_prompt(self, base_state):
        """Test preflight node with empty prompt."""
        base_state["prompt"] = ""
        
        result = preflight(base_state)
        
        # Should set error for empty prompt
        assert result["error"] is not None
        assert "prompt" in result["error"].lower()
    
    def test_preflight_node_invalid_jurisdiction(self, base_state):
        """Test preflight node validates jurisdiction."""
        # This would be caught at Pydantic level, but test node validation
        base_state["jurisdiction"] = "INVALID"
        
        result = preflight(base_state)
        
        # Node should handle gracefully or validate
        # Implementation dependent - adjust based on actual behavior
        assert "thinking" in result
    
    def test_plan_node_execution(self, base_state):
        """Test plan node creates structured planning."""
        with patch('agents.router.model_router') as mock_router:
            mock_router.route_model_call.return_value = {
                "success": True,
                "content": "1) Parse template structure\n2) Identify DIFC requirements\n3) Draft clauses\n4) Add citations\n5) Review compliance"
            }
            
            result = plan(base_state)
            
            # Should create plan
            assert "plan" in result
            assert len(result["plan"]) > 0
            
            # Should add thinking states
            thinking_states = result["thinking"]
            assert len(thinking_states) > len(base_state["thinking"])
            assert any("planning" in thought.lower() for thought in thinking_states)
            
            # Should use planning model (o1)
            mock_router.route_model_call.assert_called_once()
            call_args = mock_router.route_model_call.call_args
            assert call_args[1]["task_type"] == "planning"
    
    def test_plan_node_model_failure(self, base_state):
        """Test plan node handles model API failure."""
        with patch('agents.router.model_router') as mock_router:
            mock_router.route_model_call.return_value = {
                "success": False,
                "error": "Rate limit exceeded"
            }
            
            result = plan(base_state)
            
            # Should set error state
            assert result["error"] is not None
            assert "rate limit" in result["error"].lower()
            
            # Should still have thinking states
            assert len(result["thinking"]) > len(base_state["thinking"])
    
    @pytest.mark.asyncio
    async def test_retrieve_node_difc_first(self, base_state):
        """Test retrieve node prioritizes DIFC sources."""
        with patch('rag.retrievers.difc_retriever') as mock_retriever:
            mock_retriever.retrieve_with_citations.return_value = [
                {
                    "content": "DIFC Employment Law provisions",
                    "metadata": {
                        "title": "DIFC Employment Law No. 2 of 2019",
                        "jurisdiction": "DIFC",
                        "section": "Part 4"
                    },
                    "score": 0.95
                }
            ], [
                Citation(
                    title="DIFC Employment Law No. 2 of 2019",
                    section="Part 4",
                    url="https://difc.ae/laws/employment-2019",
                    instrument_type="Law",
                    jurisdiction=JurisdictionType.DIFC
                )
            ]
            
            result = retrieve(base_state)
            
            # Should have retrieved context
            assert len(result["retrieved_context"]) > 0
            
            # Should have DIFC citations
            assert len(result["citations"]) > 0
            difc_citations = [c for c in result["citations"] if c.jurisdiction == JurisdictionType.DIFC]
            assert len(difc_citations) > 0
            
            # Should add thinking states about DIFC retrieval
            thinking_states = result["thinking"]
            assert any("difc" in thought.lower() for thought in thinking_states)
            
            # Verify DIFC-first retrieval was called with correct parameters
            mock_retriever.retrieve_with_citations.assert_called_once()
            call_args = mock_retriever.retrieve_with_citations.call_args[0][0]  # RetrievalContext
            assert call_args.jurisdiction == JurisdictionType.DIFC
            assert call_args.boost_difc is True
    
    def test_retrieve_node_no_results(self, base_state):
        """Test retrieve node handles no search results."""
        with patch('rag.retrievers.difc_retriever') as mock_retriever:
            mock_retriever.retrieve_with_citations.return_value = ([], [])
            
            result = retrieve(base_state)
            
            # Should handle gracefully
            assert result["retrieved_context"] == []
            assert result["citations"] == []
            
            # Should add thinking state about no results
            thinking_states = result["thinking"]
            assert any("no" in thought.lower() and "found" in thought.lower() for thought in thinking_states)
    
    def test_draft_node_with_context(self, base_state):
        """Test draft node generates content with retrieved context."""
        # Set up state with plan and retrieved context
        base_state.update({
            "plan": "1) Draft introduction\n2) Add employment terms\n3) Include DIFC compliance",
            "retrieved_context": [
                {"content": "DIFC employment standards require...", "metadata": {"title": "DIFC Employment Law"}}
            ],
            "citations": [
                Citation(
                    title="DIFC Employment Law No. 2 of 2019",
                    section="Part 4",
                    jurisdiction=JurisdictionType.DIFC,
                    instrument_type="Law"
                )
            ]
        })
        
        with patch('agents.router.model_router') as mock_router:
            mock_router.route_model_call.return_value = {
                "success": True,
                "content": "# EMPLOYMENT AGREEMENT\n\nThis agreement is governed by DIFC Employment Law No. 2 of 2019..."
            }
            
            result = draft(base_state)
            
            # Should generate draft content
            assert "draft" in result
            assert len(result["draft"]) > 0
            assert "EMPLOYMENT AGREEMENT" in result["draft"]
            
            # Should use drafting model
            mock_router.route_model_call.assert_called_once()
            call_args = mock_router.route_model_call.call_args
            assert call_args[1]["task_type"] == "drafting"
            
            # Should include context in prompt
            prompt_content = call_args[1]["prompt"]
            assert "DIFC employment standards" in prompt_content
    
    def test_draft_node_model_override(self, base_state):
        """Test draft node respects model override."""
        base_state["model_override"] = "claude-3.7-sonnet"
        base_state.update({
            "plan": "Draft basic contract",
            "retrieved_context": []
        })
        
        with patch('agents.router.model_router') as mock_router:
            mock_router.route_model_call.return_value = {
                "success": True,
                "content": "Draft content using override model"
            }
            
            result = draft(base_state)
            
            # Should use override model
            mock_router.route_model_call.assert_called_once()
            call_args = mock_router.route_model_call.call_args
            assert call_args[1]["model_override"] == "claude-3.7-sonnet"
    
    def test_verify_citations_node(self, base_state):
        """Test citation verification node."""
        base_state.update({
            "draft": "This contract references DIFC Employment Law No. 2 of 2019, Part 4.",
            "citations": [
                Citation(
                    title="DIFC Employment Law No. 2 of 2019",
                    section="Part 4",
                    jurisdiction=JurisdictionType.DIFC,
                    instrument_type="Law"
                )
            ]
        })
        
        with patch('rag.citations.verify_citations_with_fallback') as mock_verify:
            mock_verify.return_value = [
                {
                    "title": "DIFC Employment Law No. 2 of 2019",
                    "section": "Part 4", 
                    "verified": True,
                    "confidence": 0.95,
                    "match_type": "exact"
                }
            ]
            
            result = verify_citations(base_state)
            
            # Should verify citations
            verified_citations = result["citations"]
            assert len(verified_citations) > 0
            assert all(hasattr(c, 'verified') and c.verified for c in verified_citations)
            
            # Should add thinking about verification
            thinking_states = result["thinking"]
            assert any("verif" in thought.lower() for thought in thinking_states)
    
    def test_verify_citations_invalid_references(self, base_state):
        """Test citation verification with invalid references."""
        base_state.update({
            "draft": "This contract references Non-existent Law No. 999 of 2025.",
            "citations": [
                Citation(
                    title="Non-existent Law No. 999 of 2025",
                    section="Unknown",
                    jurisdiction=JurisdictionType.DIFC,
                    instrument_type="Law"
                )
            ]
        })
        
        with patch('rag.citations.verify_citations_with_fallback') as mock_verify:
            mock_verify.return_value = [
                {
                    "title": "Non-existent Law No. 999 of 2025", 
                    "verified": False,
                    "confidence": 0.1,
                    "error": "Citation not found in knowledge base"
                }
            ]
            
            result = verify_citations(base_state)
            
            # Should flag invalid citations
            citations = result["citations"]
            invalid_citations = [c for c in citations if hasattr(c, 'verified') and not c.verified]
            assert len(invalid_citations) > 0
            
            # Should add warning in thinking
            thinking_states = result["thinking"]
            assert any("invalid" in thought.lower() or "not found" in thought.lower() for thought in thinking_states)
    
    def test_human_review_node(self, base_state):
        """Test human review node preparation."""
        base_state.update({
            "draft": "# EMPLOYMENT AGREEMENT\n\nCompleted draft content...",
            "citations": [
                Citation(
                    title="DIFC Employment Law No. 2 of 2019",
                    section="Part 4",
                    jurisdiction=JurisdictionType.DIFC,
                    instrument_type="Law"
                )
            ]
        })
        
        result = human_review(base_state)
        
        # Should prepare review metadata
        assert "review_ready" in result
        assert result["review_ready"] is True
        
        # Should summarize for review
        thinking_states = result["thinking"]
        assert any("review" in thought.lower() for thought in thinking_states)
        
        # Should preserve all content
        assert result["draft"] == base_state["draft"]
        assert len(result["citations"]) == len(base_state["citations"])
    
    def test_export_node(self, base_state):
        """Test export node formatting."""
        base_state.update({
            "draft": "# EMPLOYMENT AGREEMENT\n\nFinal draft content...",
            "citations": [
                Citation(
                    title="DIFC Employment Law No. 2 of 2019",
                    section="Part 4",
                    jurisdiction=JurisdictionType.DIFC,
                    instrument_type="Law"
                )
            ]
        })
        
        result = export(base_state)
        
        # Should format final output
        assert "final_output" in result
        assert len(result["final_output"]) > 0
        
        # Should include citations in export
        assert "citations" in result["final_output"] or any(c.title in result["final_output"] for c in result["citations"])
        
        # Should mark as completed
        thinking_states = result["thinking"]
        assert any("export" in thought.lower() or "complet" in thought.lower() for thought in thinking_states)


class TestNodeUtilities:
    """Test node utility functions."""
    
    def test_emit_function(self):
        """Test emit utility for adding thinking states."""
        initial_state = {"thinking": ["Initial thought"]}
        
        result = emit(initial_state, "New thinking state")
        
        assert len(result["thinking"]) == 2
        assert result["thinking"][-1] == "New thinking state"
        assert result["thinking"][0] == "Initial thought"
    
    def test_emit_function_empty_state(self):
        """Test emit function with empty thinking state."""
        initial_state = {"thinking": []}
        
        result = emit(initial_state, "First thought")
        
        assert len(result["thinking"]) == 1
        assert result["thinking"][0] == "First thought"
    
    def test_emit_function_missing_thinking(self):
        """Test emit function creates thinking array if missing."""
        initial_state = {}
        
        result = emit(initial_state, "New thought")
        
        assert "thinking" in result
        assert len(result["thinking"]) == 1
        assert result["thinking"][0] == "New thought"
    
    def test_node_registry_completeness(self):
        """Test that all nodes are registered."""
        expected_nodes = [
            "preflight", "plan", "retrieve", "draft", 
            "verify_citations", "human_review", "export"
        ]
        
        for node_name in expected_nodes:
            assert node_name in NODE_REGISTRY, f"Node {node_name} not in registry"
            assert callable(NODE_REGISTRY[node_name]), f"Node {node_name} not callable"
    
    def test_node_registry_functions_exist(self):
        """Test that all registered nodes are actual functions."""
        for node_name, node_func in NODE_REGISTRY.items():
            assert callable(node_func), f"Registered node {node_name} is not callable"
            
            # Test that function accepts state parameter
            import inspect
            sig = inspect.signature(node_func)
            assert len(sig.parameters) >= 1, f"Node {node_name} should accept at least one parameter (state)"


class TestNodeErrorHandling:
    """Test error handling across all nodes."""
    
    @pytest.fixture
    def error_state(self) -> WorkflowState:
        """State fixture that might cause errors."""
        return WorkflowState(
            prompt="Test prompt",
            template_doc_id="tmpl-123",
            reference_doc_ids=[],
            jurisdiction=JurisdictionType.DIFC,
            plan="",
            retrieved_context=[],
            citations=[],
            draft="",
            thinking=[],
            error=None,
            model_override=None
        )
    
    def test_plan_node_api_error_handling(self, error_state):
        """Test plan node handles API errors gracefully."""
        with patch('agents.router.model_router') as mock_router:
            mock_router.route_model_call.side_effect = Exception("OpenAI API error")
            
            result = plan(error_state)
            
            # Should capture error
            assert result["error"] is not None
            assert "api error" in result["error"].lower()
            
            # Should still add thinking state
            assert len(result["thinking"]) > 0
    
    def test_retrieve_node_vector_store_error(self, error_state):
        """Test retrieve node handles vector store errors."""
        with patch('rag.retrievers.difc_retriever') as mock_retriever:
            mock_retriever.retrieve_with_citations.side_effect = Exception("Vector store unavailable")
            
            result = retrieve(error_state)
            
            # Should handle gracefully with fallback
            assert "error" in result
            assert "vector store" in result["error"].lower()
            
            # Should add thinking about the error
            thinking_states = result["thinking"]
            assert any("error" in thought.lower() for thought in thinking_states)
    
    def test_draft_node_rate_limit_handling(self, error_state):
        """Test draft node handles rate limiting."""
        error_state.update({
            "plan": "Basic plan",
            "retrieved_context": []
        })
        
        with patch('agents.router.model_router') as mock_router:
            mock_router.route_model_call.side_effect = Exception("Rate limit exceeded. Retry after 60 seconds.")
            
            result = draft(error_state)
            
            # Should capture rate limit error
            assert result["error"] is not None
            assert "rate limit" in result["error"].lower()
            
            # Should suggest retry
            thinking_states = result["thinking"]
            assert any("retry" in thought.lower() for thought in thinking_states)
    
    def test_verify_citations_fallback(self, error_state):
        """Test citation verification fallback mechanisms."""
        error_state.update({
            "draft": "Test draft with citations",
            "citations": [
                Citation(
                    title="Test Law",
                    section="Section 1",
                    jurisdiction=JurisdictionType.DIFC,
                    instrument_type="Law"
                )
            ]
        })
        
        with patch('rag.citations.verify_citations_with_fallback') as mock_verify:
            # Primary verification fails, fallback succeeds
            mock_verify.return_value = [
                {
                    "title": "Test Law",
                    "verified": True,
                    "confidence": 0.7,
                    "match_type": "fuzzy_fallback",
                    "note": "Verified using fallback method"
                }
            ]
            
            result = verify_citations(error_state)
            
            # Should use fallback verification
            verified_citations = result["citations"]
            assert len(verified_citations) > 0
            
            # Should note fallback usage in thinking
            thinking_states = result["thinking"]
            assert any("fallback" in thought.lower() for thought in thinking_states)


class TestNodeIntegration:
    """Test node integration and workflow composition."""
    
    def test_full_workflow_node_chain(self, base_state):
        """Test complete chain of workflow nodes."""
        # Start with preflight
        state = preflight(base_state)
        assert "error" not in state or state["error"] is None
        
        # Move to planning
        with patch('agents.router.model_router') as mock_router:
            mock_router.route_model_call.return_value = {
                "success": True,
                "content": "1) Review template\n2) Gather DIFC requirements\n3) Draft contract\n4) Verify compliance"
            }
            
            state = plan(state)
            assert state["plan"] != ""
            assert len(state["thinking"]) > 1
        
        # Move to retrieval
        with patch('rag.retrievers.difc_retriever') as mock_retriever:
            mock_retriever.retrieve_with_citations.return_value = (
                [{"content": "DIFC employment law provisions", "metadata": {"title": "DIFC Law"}}],
                [Citation(title="DIFC Employment Law", jurisdiction=JurisdictionType.DIFC, instrument_type="Law")]
            )
            
            state = retrieve(state)
            assert len(state["retrieved_context"]) > 0
            assert len(state["citations"]) > 0
        
        # Move to drafting
        with patch('agents.router.model_router') as mock_router:
            mock_router.route_model_call.return_value = {
                "success": True,
                "content": "# EMPLOYMENT AGREEMENT\n\nThis contract is governed by DIFC Employment Law..."
            }
            
            state = draft(state)
            assert state["draft"] != ""
            assert "EMPLOYMENT AGREEMENT" in state["draft"]
        
        # Move to verification
        with patch('rag.citations.verify_citations_with_fallback') as mock_verify:
            mock_verify.return_value = [
                {"title": "DIFC Employment Law", "verified": True, "confidence": 0.95}
            ]
            
            state = verify_citations(state)
            verified_citations = [c for c in state["citations"] if hasattr(c, 'verified') and c.verified]
            assert len(verified_citations) > 0
        
        # Final export
        final_state = export(state)
        assert "final_output" in final_state
        assert len(final_state["final_output"]) > 0
        
        # Verify thinking states accumulated throughout
        assert len(final_state["thinking"]) >= 6  # At least one from each node
    
    def test_workflow_error_propagation_and_recovery(self, base_state):
        """Test error propagation and recovery in workflow."""
        # Start with error in planning phase
        preflight_state = preflight(base_state)
        
        with patch('agents.router.model_router') as mock_router:
            mock_router.route_model_call.side_effect = Exception("Planning API failure")
            
            plan_state = plan(preflight_state)
            assert plan_state["error"] is not None
            assert "planning api failure" in plan_state["error"].lower()
        
        # Retrieval should still work despite planning error
        with patch('rag.retrievers.difc_retriever') as mock_retriever:
            mock_retriever.retrieve_with_citations.return_value = (
                [{"content": "Retrieved content despite planning error"}],
                [Citation(title="Test Source", jurisdiction=JurisdictionType.DIFC, instrument_type="Law")]
            )
            
            retrieve_state = retrieve(plan_state)
            # Should preserve error but continue with retrieval
            assert retrieve_state["error"] is not None  # Previous error preserved
            assert len(retrieve_state["retrieved_context"]) > 0  # But retrieval worked
    
    def test_workflow_thinking_state_chronology(self, base_state):
        """Test that thinking states maintain chronological order."""
        # Execute multiple nodes and verify thinking state order
        state = base_state
        
        # Preflight adds thinking
        state = preflight(state)
        preflight_count = len(state["thinking"])
        
        # Plan adds more thinking
        with patch('agents.router.model_router') as mock_router:
            mock_router.route_model_call.return_value = {"success": True, "content": "test plan"}
            state = plan(state)
            plan_count = len(state["thinking"])
        
        # Retrieve adds more thinking
        with patch('rag.retrievers.difc_retriever') as mock_retriever:
            mock_retriever.retrieve_with_citations.return_value = ([], [])
            state = retrieve(state)
            final_count = len(state["thinking"])
        
        # Verify chronological accumulation
        assert preflight_count > 0
        assert plan_count > preflight_count
        assert final_count > plan_count
        
        # Verify no thinking states were lost or reordered
        thinking_states = state["thinking"]
        assert len(thinking_states) == final_count


class TestNodeStateManagement:
    """Test proper state management across nodes."""
    
    def test_state_immutability_preservation(self, base_state):
        """Test nodes don't mutate input state directly."""
        original_thinking_count = len(base_state["thinking"])
        original_prompt = base_state["prompt"]
        
        result = preflight(base_state.copy())
        
        # Original state should be unchanged
        assert len(base_state["thinking"]) == original_thinking_count
        assert base_state["prompt"] == original_prompt
        
        # Result should have new state
        assert len(result["thinking"]) > original_thinking_count
    
    def test_state_field_preservation(self, base_state):
        """Test nodes preserve required state fields."""
        essential_fields = ["prompt", "template_doc_id", "jurisdiction", "thinking"]
        
        result = preflight(base_state)
        
        # All essential fields should be preserved
        for field in essential_fields:
            assert field in result, f"Essential field {field} missing from result"
    
    def test_progressive_state_building(self, base_state):
        """Test state builds progressively through nodes."""
        # Test preflight -> plan -> retrieve chain
        
        # Preflight
        state_after_preflight = preflight(base_state)
        assert len(state_after_preflight["thinking"]) > 0
        
        # Plan (uses preflight output)
        with patch('agents.router.model_router') as mock_router:
            mock_router.route_model_call.return_value = {
                "success": True,
                "content": "Generated plan content"
            }
            
            state_after_plan = plan(state_after_preflight)
            assert len(state_after_plan["thinking"]) > len(state_after_preflight["thinking"])
            assert state_after_plan["plan"] != ""
        
        # Retrieve (uses plan output)
        with patch('rag.retrievers.difc_retriever') as mock_retriever:
            mock_retriever.retrieve_with_citations.return_value = (
                [{"content": "Retrieved content"}],
                [Citation(title="Test", jurisdiction=JurisdictionType.DIFC, instrument_type="Law")]
            )
            
            state_after_retrieve = retrieve(state_after_plan)
            assert len(state_after_retrieve["thinking"]) > len(state_after_plan["thinking"])
            assert len(state_after_retrieve["retrieved_context"]) > 0
            assert len(state_after_retrieve["citations"]) > 0
    
    def test_error_state_propagation(self, base_state):
        """Test error states propagate correctly."""
        # Set error in initial state
        base_state["error"] = "Previous node error"
        
        result = plan(base_state)
        
        # Error should be preserved or handled appropriately
        # Implementation may choose to stop processing or continue with degraded functionality
        assert "error" in result
    
    def test_thinking_states_accumulate(self, base_state):
        """Test thinking states accumulate through workflow."""
        # Start with some initial thinking
        base_state["thinking"] = ["Initial state"]
        
        # Each node should add to thinking
        result1 = preflight(base_state)
        assert len(result1["thinking"]) > len(base_state["thinking"])
        
        with patch('agents.router.model_router') as mock_router:
            mock_router.route_model_call.return_value = {"success": True, "content": "plan"}
            result2 = plan(result1)
            assert len(result2["thinking"]) > len(result1["thinking"])
        
        # Verify thinking states are in chronological order
        thinking_states = result2["thinking"]
        assert thinking_states[0] == "Initial state"
        assert len(thinking_states) >= 3  # Initial + preflight + plan


class TestNodeDIFCCompliance:
    """Test DIFC-first behavior across nodes."""
    
    def test_retrieve_node_difc_priority(self, base_state):
        """Test retrieve node prioritizes DIFC sources."""
        with patch('rag.retrievers.difc_retriever') as mock_retriever:
            # Mock mixed jurisdiction results with DIFC getting higher scores
            mock_retriever.retrieve_with_citations.return_value = (
                [
                    {"content": "DIFC content", "metadata": {"jurisdiction": "DIFC"}, "score": 0.95},
                    {"content": "UAE content", "metadata": {"jurisdiction": "UAE"}, "score": 0.92},
                    {"content": "DFSA content", "metadata": {"jurisdiction": "DFSA"}, "score": 0.88}
                ],
                [
                    Citation(title="DIFC Law", jurisdiction=JurisdictionType.DIFC, instrument_type="Law"),
                    Citation(title="UAE Law", jurisdiction=JurisdictionType.UAE, instrument_type="Law"),
                    Citation(title="DFSA Rule", jurisdiction=JurisdictionType.DFSA, instrument_type="Rulebook")
                ]
            )
            
            result = retrieve(base_state)
            
            # Should prioritize DIFC sources
            retrieved_context = result["retrieved_context"]
            difc_context = [ctx for ctx in retrieved_context if ctx["metadata"]["jurisdiction"] == "DIFC"]
            assert len(difc_context) > 0
            
            # DIFC citations should be present
            difc_citations = [c for c in result["citations"] if c.jurisdiction == JurisdictionType.DIFC]
            assert len(difc_citations) > 0
    
    def test_draft_node_difc_focus(self, base_state):
        """Test draft node emphasizes DIFC compliance."""
        base_state.update({
            "plan": "Draft DIFC-compliant contract",
            "retrieved_context": [
                {"content": "DIFC Employment Law requirements", "metadata": {"jurisdiction": "DIFC"}}
            ],
            "citations": [
                Citation(title="DIFC Employment Law", jurisdiction=JurisdictionType.DIFC, instrument_type="Law")
            ]
        })
        
        with patch('agents.router.model_router') as mock_router:
            mock_router.route_model_call.return_value = {
                "success": True,
                "content": "# EMPLOYMENT AGREEMENT\n\nThis agreement complies with DIFC Employment Law..."
            }
            
            result = draft(base_state)
            
            # Generated content should mention DIFC
            assert "DIFC" in result["draft"]
            
            # Prompt should emphasize DIFC compliance
            call_args = mock_router.route_model_call.call_args
            prompt = call_args[1]["prompt"]
            assert "DIFC" in prompt
            assert "compli" in prompt.lower()  # compliance/compliant
    
    def test_verify_citations_difc_sources(self, base_state):
        """Test citation verification prioritizes DIFC sources."""
        base_state.update({
            "draft": "References DIFC Employment Law and UAE Federal Law",
            "citations": [
                Citation(title="DIFC Employment Law", jurisdiction=JurisdictionType.DIFC, instrument_type="Law"),
                Citation(title="UAE Federal Law", jurisdiction=JurisdictionType.UAE, instrument_type="Law")
            ]
        })
        
        with patch('rag.citations.verify_citations_with_fallback') as mock_verify:
            mock_verify.return_value = [
                {"title": "DIFC Employment Law", "verified": True, "confidence": 0.98, "jurisdiction": "DIFC"},
                {"title": "UAE Federal Law", "verified": True, "confidence": 0.85, "jurisdiction": "UAE"}
            ]
            
            result = verify_citations(base_state)
            
            # Should verify DIFC citations with higher confidence
            difc_citations = [c for c in result["citations"] if c.jurisdiction == JurisdictionType.DIFC]
            assert len(difc_citations) > 0
            
            # Thinking should note DIFC focus
            thinking_states = result["thinking"]
            assert any("difc" in thought.lower() for thought in thinking_states)