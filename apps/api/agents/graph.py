"""
LangGraph composition for QaAI workflows.

Following examples/workflow_draft_from_template.graph.py patterns:
- Deterministic graph: preflight → plan → retrieve → draft → verify → export  
- Proper error handling and retry policies
- State management with TypedDict
"""

from __future__ import annotations
from typing import Dict, Any, Optional, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from core.models import WorkflowState, JurisdictionType
from .nodes import (
    preflight,
    plan, 
    retrieve,
    draft,
    verify_citations,
    human_review,
    export,
    NODE_REGISTRY
)


class QaAIWorkflowGraph:
    """
    QaAI workflow orchestration using LangGraph.
    
    Implements the deterministic, inspectable graph pattern from PRP requirements.
    """
    
    def __init__(self):
        self.graph = None
        self.app = None
        self.checkpointer = MemorySaver()
        self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph workflow."""
        # Create state graph
        self.graph = StateGraph(WorkflowState)
        
        # Add nodes
        self.graph.add_node("preflight", preflight)
        self.graph.add_node("plan", plan)
        self.graph.add_node("retrieve", retrieve)
        self.graph.add_node("draft", draft)
        self.graph.add_node("verify_citations", verify_citations)
        self.graph.add_node("human_review", human_review)
        self.graph.add_node("export", export)
        
        # Set entry point
        self.graph.set_entry_point("preflight")
        
        # Add edges - deterministic flow
        self.graph.add_edge("preflight", "plan")
        self.graph.add_edge("plan", "retrieve")
        self.graph.add_edge("retrieve", "draft")
        self.graph.add_edge("draft", "verify_citations")
        self.graph.add_edge("verify_citations", "human_review")
        self.graph.add_edge("human_review", "export")
        self.graph.add_edge("export", END)
        
        # Add conditional edges for error handling
        self.graph.add_conditional_edges(
            "preflight",
            self._should_continue,
            {
                "continue": "plan",
                "end": END
            }
        )
        
        self.graph.add_conditional_edges(
            "plan",
            self._should_continue,
            {
                "continue": "retrieve", 
                "end": END
            }
        )
        
        self.graph.add_conditional_edges(
            "retrieve",
            self._should_continue,
            {
                "continue": "draft",
                "end": END
            }
        )
        
        self.graph.add_conditional_edges(
            "draft",
            self._should_continue,
            {
                "continue": "verify_citations",
                "end": END
            }
        )
        
        # Compile the graph
        self.app = self.graph.compile(checkpointer=self.checkpointer)
    
    def _should_continue(self, state: WorkflowState) -> Literal["continue", "end"]:
        """Conditional logic for error handling."""
        if state.get("error"):
            return "end"
        return "continue"
    
    async def run(
        self,
        prompt: str,
        jurisdiction: JurisdictionType = JurisdictionType.DIFC,
        template_doc_id: Optional[str] = None,
        reference_doc_ids: Optional[list] = None,
        model_override: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run the complete workflow.
        
        Args:
            prompt: User query/instruction
            jurisdiction: Legal jurisdiction focus
            template_doc_id: Template document ID for workflows
            reference_doc_ids: Reference document IDs
            model_override: Manual model override
            config: Additional configuration
            
        Returns:
            Dict containing final output and metadata
        """
        # Prepare initial state
        initial_state: WorkflowState = {
            "prompt": prompt,
            "jurisdiction": jurisdiction,
            "template_doc_id": template_doc_id,
            "reference_doc_ids": reference_doc_ids or [],
            "model_override": model_override,
            "thinking": [],
            "citations": []
        }
        
        # Run configuration
        run_config = {
            "configurable": {
                "thread_id": "qaai_workflow",
                "checkpoint_id": None
            }
        }
        
        if config:
            run_config.update(config)
        
        try:
            # Execute workflow
            result = await self.app.ainvoke(initial_state, run_config)
            
            return {
                "success": True,
                "output": result.get("export_data", result),
                "thinking_states": result.get("thinking", []),
                "error": result.get("error"),
                "verification_passed": result.get("verification_passed", False),
                "citations": result.get("citations", []),
                "metadata": {
                    "jurisdiction": jurisdiction.value if hasattr(jurisdiction, 'value') else str(jurisdiction),
                    "nodes_executed": len(result.get("thinking", [])),
                    "has_error": bool(result.get("error"))
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "output": None,
                "thinking_states": [],
                "error": f"Workflow execution error: {str(e)}",
                "verification_passed": False,
                "citations": [],
                "metadata": {
                    "jurisdiction": jurisdiction.value if hasattr(jurisdiction, 'value') else str(jurisdiction),
                    "nodes_executed": 0,
                    "has_error": True
                }
            }
    
    async def stream_run(
        self,
        prompt: str,
        jurisdiction: JurisdictionType = JurisdictionType.DIFC,
        template_doc_id: Optional[str] = None,
        reference_doc_ids: Optional[list] = None,
        model_override: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Stream workflow execution with thinking states.
        
        Yields thinking states and progress updates as they occur.
        """
        # Prepare initial state
        initial_state: WorkflowState = {
            "prompt": prompt,
            "jurisdiction": jurisdiction,
            "template_doc_id": template_doc_id,
            "reference_doc_ids": reference_doc_ids or [],
            "model_override": model_override,
            "thinking": [],
            "citations": []
        }
        
        # Run configuration
        run_config = {
            "configurable": {
                "thread_id": f"qaai_stream_{id(initial_state)}",
                "checkpoint_id": None
            }
        }
        
        if config:
            run_config.update(config)
        
        try:
            # Stream workflow execution
            async for event in self.app.astream(initial_state, run_config):
                # Extract thinking states and progress
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        # Emit thinking states
                        thinking_states = node_output.get("thinking", [])
                        if thinking_states:
                            # Get new thinking states since last emission
                            for thinking_state in thinking_states[-1:]:  # Just the latest
                                yield {
                                    "type": "thinking_state",
                                    "node": node_name,
                                    "label": thinking_state,
                                    "timestamp": None
                                }
                        
                        # Emit progress updates
                        if node_name == "draft" and "draft" in node_output:
                            yield {
                                "type": "draft_progress",
                                "node": node_name,
                                "content": node_output["draft"][:200] + "...",
                                "complete": False
                            }
                        
                        # Emit citations when available
                        if "citations" in node_output and node_output["citations"]:
                            for citation in node_output["citations"]:
                                yield {
                                    "type": "citation",
                                    "citation": citation
                                }
                        
                        # Emit errors
                        if "error" in node_output and node_output["error"]:
                            yield {
                                "type": "error",
                                "node": node_name,
                                "error": node_output["error"]
                            }
                            return
            
            # Final completion event
            yield {
                "type": "done",
                "message": "Workflow completed successfully"
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "node": "workflow",
                "error": f"Workflow streaming error: {str(e)}"
            }
    
    def get_graph_visualization(self) -> Dict[str, Any]:
        """Get graph structure for visualization."""
        if not self.graph:
            return {}
        
        # Extract nodes and edges for visualization
        nodes = []
        edges = []
        
        # Get nodes
        for node_name in self.graph.nodes:
            if node_name != "__start__" and node_name != "__end__":
                nodes.append({
                    "id": node_name,
                    "label": node_name.replace("_", " ").title(),
                    "type": "process"
                })
        
        # Add start and end nodes
        nodes.extend([
            {"id": "start", "label": "Start", "type": "start"},
            {"id": "end", "label": "End", "type": "end"}
        ])
        
        # Get edges (simplified)
        edge_list = [
            ("start", "preflight"),
            ("preflight", "plan"),
            ("plan", "retrieve"),
            ("retrieve", "draft"),
            ("draft", "verify_citations"),
            ("verify_citations", "human_review"),
            ("human_review", "export"),
            ("export", "end")
        ]
        
        for source, target in edge_list:
            edges.append({
                "source": source,
                "target": target,
                "label": ""
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "layout": "hierarchical",
            "description": "DIFC-focused legal workflow with deterministic processing steps"
        }


class SimpleAssistantGraph:
    """
    Simplified graph for direct assistant queries (non-workflow mode).
    
    Handles assist and draft modes without full workflow orchestration.
    """
    
    def __init__(self):
        self.graph = None
        self.app = None
        self._build_simple_graph()
    
    def _build_simple_graph(self):
        """Build simplified assistant graph."""
        from .nodes import retrieve, draft as draft_node
        
        async def simple_assistant(state: WorkflowState) -> WorkflowState:
            """Combined node for simple assistant operations."""
            # Get retrieval context
            retrieval_state = await retrieve(state)
            if retrieval_state.get("error"):
                return retrieval_state
            
            # Generate response
            draft_state = await draft_node(retrieval_state)
            return draft_state
        
        # Create simple graph
        self.graph = StateGraph(WorkflowState)
        self.graph.add_node("assistant", simple_assistant)
        self.graph.set_entry_point("assistant")
        self.graph.add_edge("assistant", END)
        
        self.app = self.graph.compile()
    
    async def run(
        self,
        prompt: str,
        mode: Literal["assist", "draft"] = "assist",
        jurisdiction: JurisdictionType = JurisdictionType.DIFC,
        vault_project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run simple assistant query."""
        initial_state: WorkflowState = {
            "prompt": prompt,
            "jurisdiction": jurisdiction,
            "thinking": [],
            "citations": []
        }
        
        try:
            result = await self.app.ainvoke(initial_state)
            
            return {
                "success": True,
                "content": result.get("draft", ""),
                "citations": result.get("citations", []),
                "error": result.get("error"),
                "thinking_states": result.get("thinking", [])
            }
            
        except Exception as e:
            return {
                "success": False,
                "content": "",
                "citations": [],
                "error": f"Assistant error: {str(e)}",
                "thinking_states": []
            }


# Global workflow instances
qaai_workflow = QaAIWorkflowGraph()
simple_assistant = SimpleAssistantGraph()