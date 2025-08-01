"""
Assistant API endpoints with SSE streaming.

Following examples/assistant_run.py patterns:
- SSE streaming for thinking states, text chunks, citations, and done events
- Support for both Assist and Draft modes
- DIFC-first knowledge filtering
"""

from __future__ import annotations
import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from core.models import (
    AssistantQuery, 
    ThinkingState, 
    TextChunk, 
    Citation, 
    StreamDone,
    JurisdictionType,
    AssistantMode
)
from core.database import get_db
from agents.graph import simple_assistant, qaai_workflow
from agents.router import model_router
from rag.retrievers import difc_retriever, RetrievalContext


router = APIRouter()


async def stream_assistant_response(query: AssistantQuery):
    """
    Stream assistant response with thinking states and content.
    
    Following examples/assistant_run.py SSE format.
    """
    try:
        # Emit initial thinking state
        yield {
            "event": "message",
            "data": json.dumps({
                "type": "thinking_state",
                "label": f"Processing {query.mode} request for {query.knowledge.jurisdiction.value}",
                "timestamp": datetime.now().isoformat()
            })
        }
        
        # Choose execution path based on mode
        if query.mode == AssistantMode.DRAFT:
            # Use full workflow for draft mode
            yield {
                "event": "message", 
                "data": json.dumps({
                    "type": "thinking_state",
                    "label": "Initializing draft workflow",
                    "timestamp": datetime.now().isoformat()
                })
            }
            
            # Stream workflow execution
            async for event in qaai_workflow.stream_run(
                prompt=query.prompt,
                jurisdiction=query.knowledge.jurisdiction,
                model_override=None  # Could be passed from query
            ):
                if event.get("type") == "thinking_state":
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "thinking_state", 
                            "label": event.get("label", "Processing..."),
                            "timestamp": datetime.now().isoformat()
                        })
                    }
                elif event.get("type") == "draft_progress":
                    # Stream draft content as it's generated
                    content = event.get("content", "")
                    for chunk in _chunk_text(content, 50):  # Stream in small chunks
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "chunk",
                                "text": chunk
                            })
                        }
                        await asyncio.sleep(0.1)  # Simulate streaming
                        
                elif event.get("type") == "citation":
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "citation",
                            **event.get("citation", {})
                        })
                    }
                elif event.get("type") == "error":
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "error": event.get("error", "Unknown error"),
                            "node": event.get("node", "unknown")
                        })
                    }
                    return
            
        else:
            # Use simple assistant for assist mode
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "thinking_state",
                    "label": "Retrieving relevant DIFC sources",
                    "timestamp": datetime.now().isoformat()
                })
            }
            
            # Get retrieval context
            retrieval_context = RetrievalContext(
                query=query.prompt,
                jurisdiction=query.knowledge.jurisdiction,
                max_results=5,
                include_citations=True,
                boost_difc=True,
                hybrid_search=True
            )
            
            # Perform retrieval
            matches, citations = await difc_retriever.retrieve_with_citations(retrieval_context)
            
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "thinking_state",
                    "label": f"Found {len(matches)} relevant documents",
                    "timestamp": datetime.now().isoformat()
                })
            }
            
            # Emit citations
            for citation in citations:
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "citation",
                        "title": citation.title,
                        "section": citation.section,
                        "url": citation.url,
                        "instrument_type": citation.instrument_type.value,
                        "jurisdiction": citation.jurisdiction.value
                    })
                }
            
            # Generate response
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "thinking_state",
                    "label": "Generating response with DIFC legal analysis",
                    "timestamp": datetime.now().isoformat()
                })
            }
            
            # Use simple assistant to generate response
            result = await simple_assistant.run(
                prompt=query.prompt,
                mode=query.mode,
                jurisdiction=query.knowledge.jurisdiction,
                vault_project_id=query.vault_project_id
            )
            
            if not result["success"]:
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": result["error"]
                    })
                }
                return
            
            # Stream the response content
            content = result.get("content") or result.get("draft", "No response generated")
            for chunk in _chunk_text(content, 100):
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "chunk",
                        "text": chunk
                    })
                }
                await asyncio.sleep(0.05)  # Simulate typing
        
        # Final done event
        yield {
            "event": "message",
            "data": json.dumps({
                "type": "done",
                "final_response": "Response completed",
                "citations": [c.dict() if hasattr(c, 'dict') else c for c in citations] if 'citations' in locals() else []
            })
        }
        
    except Exception as e:
        yield {
            "event": "error",
            "data": json.dumps({
                "error": f"Assistant error: {str(e)}"
            })
        }


def _chunk_text(text: str, chunk_size: int) -> list[str]:
    """Split text into chunks for streaming."""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size):
        chunk_words = words[i:i + chunk_size]
        chunks.append(" ".join(chunk_words))
    
    return chunks


@router.post("/query")
async def query_assistant(query: AssistantQuery):
    """
    Query the assistant with SSE streaming response.
    
    Supports both assist and draft modes with real-time thinking states.
    """
    try:
        # Validate input
        if not query.prompt or len(query.prompt.strip()) == 0:
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
        # Validate jurisdiction
        if query.knowledge.jurisdiction not in JurisdictionType:
            raise HTTPException(status_code=400, detail="Invalid jurisdiction")
        
        # Return SSE stream
        return EventSourceResponse(
            stream_assistant_response(query),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing error: {str(e)}")


@router.post("/query-sync") 
async def query_assistant_sync(query: AssistantQuery):
    """
    Synchronous assistant query for testing purposes.
    
    Returns complete response without streaming.
    """
    try:
        if query.mode == AssistantMode.DRAFT:
            # Use workflow
            result = await qaai_workflow.run(
                prompt=query.prompt,
                jurisdiction=query.knowledge.jurisdiction
            )
            
            return {
                "success": result["success"],
                "content": result["output"].get("content", "") if result["output"] else "",
                "citations": result["citations"],
                "thinking_states": result["thinking_states"],
                "error": result["error"]
            }
        else:
            # Use simple assistant
            result = await simple_assistant.run(
                prompt=query.prompt,
                mode=query.mode,
                jurisdiction=query.knowledge.jurisdiction,
                vault_project_id=query.vault_project_id
            )
            
            return result
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")


@router.get("/models")
async def get_available_models():
    """Get information about available models and routing."""
    try:
        return model_router.get_routing_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model info error: {str(e)}")


@router.post("/models/override")
async def set_model_override(model_name: Optional[str] = None):
    """Set manual model override."""
    try:
        model_router.set_manual_override(model_name)
        return {
            "success": True,
            "override_model": model_name,
            "message": f"Model override set to {model_name}" if model_name else "Model override cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model override error: {str(e)}")


@router.get("/knowledge-sources")
async def get_knowledge_sources():
    """Get available knowledge sources and statistics."""
    try:
        return difc_retriever.get_knowledge_sources_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Knowledge sources error: {str(e)}")