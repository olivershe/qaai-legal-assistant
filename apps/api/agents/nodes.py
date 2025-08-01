"""
LangGraph node implementations for QaAI workflows.

Following examples/workflow_draft_from_template.graph.py patterns:
- Use emit() pattern for thinking states
- Per-step model routing (reasoning vs drafting vs verification)
- DIFC-first retrieval with jurisdiction boosting
- Return state updates, not modify in place
"""

from __future__ import annotations
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.models import WorkflowState, JurisdictionType, Citation
from rag.retrievers import difc_retriever, RetrievalContext
from services.openai_client import openai_client
from services.anthropic_client import anthropic_client
from agents.router import model_router, ModelProvider
from agents.prompts import DIFCPrompts, get_disclaimer_for_topic


def emit(state: WorkflowState, label: str) -> WorkflowState:
    """
    Emit thinking state following examples pattern.
    
    Critical: Returns state updates, doesn't modify in place.
    """
    thinking = state.get("thinking", [])
    thinking_updated = thinking.copy()
    thinking_updated.append(f"[{datetime.now().strftime('%H:%M:%S')}] {label}")
    
    return {**state, "thinking": thinking_updated}


async def preflight(state: WorkflowState) -> WorkflowState:
    """
    Validate inputs and setup workflow context.
    
    Following examples/workflow_draft_from_template.graph.py pattern.
    """
    state = emit(state, "Validating workflow inputs")
    
    # Check required inputs
    if not state.get("prompt"):
        return {**state, "error": "Missing user prompt"}
    
    # Set defaults
    if "jurisdiction" not in state:
        state = {**state, "jurisdiction": JurisdictionType.DIFC}
    
    if "thinking" not in state:
        state = {**state, "thinking": []}
    
    if "citations" not in state:
        state = {**state, "citations": []}
    
    # Validate model routing
    try:
        validation = model_router.validate_model_availability()
        if not validation["valid"]:
            return {**state, "error": f"Model availability issues: {validation['issues']}"}
    except Exception as e:
        return {**state, "error": f"Model routing error: {str(e)}"}
    
    state = emit(state, "Preflight validation completed")
    return state


async def plan(state: WorkflowState) -> WorkflowState:
    """
    Create research and drafting plan using reasoning model.
    
    Uses o1 or similar reasoning model for complex analysis.
    """
    state = emit(state, "Creating workflow plan")
    
    if state.get("error"):
        return state
    
    try:
        # Get planning model
        model_name, provider = model_router.get_planner_model()
        state = emit(state, f"Using {model_name} for planning")
        
        # Generate planning prompt
        prompt = DIFCPrompts.get_planner_prompt(
            query=state["prompt"],
            jurisdiction=state.get("jurisdiction", JurisdictionType.DIFC),
            context={
                "template_doc_id": state.get("template_doc_id"),
                "reference_doc_ids": state.get("reference_doc_ids", []),
                "model_override": state.get("model_override")
            }
        )
        
        # Call appropriate model
        if provider == ModelProvider.OPENAI:
            plan_response = await openai_client.complete(
                model=model_name,
                prompt=prompt,
                max_tokens=2000,
                temperature=0.1
            )
        else:
            plan_response = await anthropic_client.complete(
                model=model_name,
                prompt=prompt,
                max_tokens=2000,
                temperature=0.1
            )
        
        if not plan_response or not plan_response.get("content"):
            return {**state, "error": "Failed to generate plan"}
        
        plan_content = plan_response["content"]
        state = emit(state, "Plan generation completed")
        
        return {**state, "plan": plan_content}
        
    except Exception as e:
        return {**state, "error": f"Planning error: {str(e)}"}


async def retrieve(state: WorkflowState) -> WorkflowState:
    """
    Retrieve relevant context using DIFC-first approach.
    
    Implements jurisdiction boosting and citation verification.
    """
    state = emit(state, "Retrieving DIFC sources and context")
    
    if state.get("error"):
        return state
    
    try:
        # Create retrieval context
        retrieval_context = RetrievalContext(
            query=state["prompt"],
            jurisdiction=state.get("jurisdiction", JurisdictionType.DIFC),
            max_results=10,
            include_citations=True,
            boost_difc=True,
            hybrid_search=True
        )
        
        # Perform retrieval with citations
        matches, citations = await difc_retriever.retrieve_with_citations(retrieval_context)
        
        state = emit(state, f"Retrieved {len(matches)} relevant documents")
        
        # Format retrieved context
        retrieved_docs = []
        for match in matches:
            doc_info = {
                "title": match.chunk.metadata.get("title", "Unknown") if match.chunk.metadata else "Unknown",
                "content": match.chunk.content,
                "score": match.score,
                "jurisdiction": match.chunk.metadata.get("jurisdiction") if match.chunk.metadata else "Unknown",
                "instrument_type": match.chunk.metadata.get("instrument_type") if match.chunk.metadata else "Unknown",
                "section_ref": match.chunk.section_ref
            }
            retrieved_docs.append(doc_info)
        
        state = emit(state, f"Generated {len(citations)} verified citations")
        
        return {
            **state,
            "retrieved_context": retrieved_docs,
            "citations": [citation.dict() if hasattr(citation, 'dict') else citation for citation in citations]
        }
        
    except Exception as e:
        return {**state, "error": f"Retrieval error: {str(e)}"}


async def draft(state: WorkflowState) -> WorkflowState:
    """
    Generate draft content using generation model.
    
    Uses gpt-4.1 or claude-3.7-sonnet for content creation.
    """
    state = emit(state, "Drafting content with DIFC legal analysis")
    
    if state.get("error"):
        return state
    
    try:
        # Estimate context length for model selection
        context_length = len(str(state.get("plan", ""))) + len(str(state.get("retrieved_context", [])))
        
        # Get drafting model
        model_name, provider = model_router.get_drafter_model(context_length)
        state = emit(state, f"Using {model_name} for drafting")
        
        # Format retrieved context for prompt
        context_text = ""
        if state.get("retrieved_context"):
            context_text = "\\n\\n".join([
                f"**{doc['title']}** (Score: {doc['score']:.3f})\\n{doc['content'][:500]}..."
                for doc in state["retrieved_context"][:5]  # Limit context
            ])
        
        # Generate drafting prompt
        prompt = DIFCPrompts.get_drafter_prompt(
            plan=state.get("plan", "No plan provided"),
            retrieved_context=context_text,
            jurisdiction=state.get("jurisdiction", JurisdictionType.DIFC)
        )
        
        # Call appropriate model
        if provider == ModelProvider.OPENAI:
            draft_response = await openai_client.complete(
                model=model_name,
                prompt=prompt,
                max_tokens=4000,
                temperature=0.2
            )
        else:
            draft_response = await anthropic_client.complete(
                model=model_name,
                prompt=prompt,
                max_tokens=4000,
                temperature=0.2
            )
        
        if not draft_response or not draft_response.get("content"):
            return {**state, "error": "Failed to generate draft"}
        
        draft_content = draft_response["content"]
        
        # Add appropriate legal disclaimer
        disclaimer = get_disclaimer_for_topic(state["prompt"])
        draft_with_disclaimer = f"{draft_content}\\n\\n{disclaimer}"
        
        state = emit(state, "Draft generation completed")
        
        return {**state, "draft": draft_with_disclaimer}
        
    except Exception as e:
        return {**state, "error": f"Drafting error: {str(e)}"}


async def verify_citations(state: WorkflowState) -> WorkflowState:
    """
    Verify citations and content accuracy using verification model.
    
    Uses claude-3.7-sonnet for detailed verification.
    """
    state = emit(state, "Verifying citations and content accuracy")
    
    if state.get("error"):
        return state
    
    try:
        # Get verification model
        model_name, provider = model_router.get_verifier_model()
        state = emit(state, f"Using {model_name} for verification")
        
        # Generate verification prompt
        prompt = DIFCPrompts.get_verifier_prompt(
            draft_content=state.get("draft", ""),
            citations=state.get("citations", [])
        )
        
        # Call verification model
        if provider == ModelProvider.OPENAI:
            verify_response = await openai_client.complete(
                model=model_name,
                prompt=prompt,
                max_tokens=2000,
                temperature=0.0  # Low temperature for accuracy
            )
        else:
            verify_response = await anthropic_client.complete(
                model=model_name,
                prompt=prompt,
                max_tokens=2000,
                temperature=0.0
            )
        
        if not verify_response or not verify_response.get("content"):
            return {**state, "error": "Failed to verify content"}
        
        verification_result = verify_response["content"]
        
        # Simple verification status check
        verification_passed = "approved" in verification_result.lower() or "verified" in verification_result.lower()
        
        if verification_passed:
            state = emit(state, "Citation verification passed")
        else:
            state = emit(state, "Citation verification flagged issues")
            # In production, this could trigger revision loop
        
        return {
            **state,
            "verification_result": verification_result,
            "verification_passed": verification_passed
        }
        
    except Exception as e:
        return {**state, "error": f"Verification error: {str(e)}"}


async def human_review(state: WorkflowState) -> WorkflowState:
    """
    Prepare content for human review.
    
    Formats output and provides review metadata.
    """
    state = emit(state, "Preparing content for review")
    
    # Compile final output
    final_output = {
        "draft": state.get("draft", ""),
        "plan": state.get("plan", ""),
        "citations": state.get("citations", []),
        "verification_result": state.get("verification_result", ""),
        "verification_passed": state.get("verification_passed", False),
        "retrieved_context_count": len(state.get("retrieved_context", [])),
        "model_info": {
            "planner": model_router.get_planner_model()[0],
            "drafter": model_router.get_drafter_model()[0],
            "verifier": model_router.get_verifier_model()[0]
        },
        "thinking_states": state.get("thinking", []),
        "jurisdiction": state.get("jurisdiction", JurisdictionType.DIFC).value if hasattr(state.get("jurisdiction"), 'value') else str(state.get("jurisdiction", "DIFC"))
    }
    
    state = emit(state, "Content prepared for human review")
    
    return {**state, "final_output": final_output}


async def export(state: WorkflowState) -> WorkflowState:
    """
    Export final content in requested format.
    
    Handles different output formats and metadata.
    """
    state = emit(state, "Exporting final content")
    
    if state.get("error"):
        return state
    
    # Create export package
    export_data = {
        "content": state.get("draft", ""),
        "metadata": {
            "prompt": state.get("prompt", ""),
            "jurisdiction": state.get("jurisdiction", JurisdictionType.DIFC).value if hasattr(state.get("jurisdiction"), 'value') else str(state.get("jurisdiction", "DIFC")),
            "citations_count": len(state.get("citations", [])),
            "verification_passed": state.get("verification_passed", False),
            "generated_at": datetime.now().isoformat(),
            "models_used": {
                "planner": model_router.get_planner_model()[0],
                "drafter": model_router.get_drafter_model()[0], 
                "verifier": model_router.get_verifier_model()[0]
            }
        },
        "citations": state.get("citations", []),
        "thinking_states": state.get("thinking", [])
    }
    
    state = emit(state, "Export completed")
    
    return {**state, "export_data": export_data}


# Node registry for dynamic workflow construction
NODE_REGISTRY = {
    "preflight": preflight,
    "plan": plan,
    "retrieve": retrieve,
    "draft": draft,
    "verify_citations": verify_citations,
    "human_review": human_review,
    "export": export
}