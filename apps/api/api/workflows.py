"""
Workflow API endpoints for agentic processes.

Following PRP requirements:
- Execute LangGraph workflows with SSE streaming
- Support "Draft from Template (DIFC)" workflow
- Return status, artifacts, and thinking states
"""

from __future__ import annotations
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Form, UploadFile, File
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from core.models import (
    WorkflowRunStatus,
    WorkflowRun,
    JurisdictionType
)
from agents.graph import qaai_workflow


router = APIRouter()


# In-memory workflow run storage (production would use database)
workflow_runs: Dict[str, WorkflowRun] = {}


async def stream_workflow_execution(
    run_id: str,
    workflow_type: str,
    input_data: Dict[str, Any]
):
    """
    Stream workflow execution with thinking states and progress.
    
    Following SSE patterns from assistant API.
    """
    try:
        # Update run status
        if run_id in workflow_runs:
            workflow_runs[run_id].status = WorkflowRunStatus.RUNNING
        
        # Emit initial status
        yield {
            "event": "message",
            "data": json.dumps({
                "type": "workflow_start",
                "run_id": run_id,
                "workflow_type": workflow_type,
                "timestamp": datetime.now().isoformat()
            })
        }
        
        # Execute workflow with streaming
        async for event in qaai_workflow.stream_run(
            prompt=input_data.get("prompt", ""),
            jurisdiction=JurisdictionType(input_data.get("jurisdiction", "DIFC")),
            template_doc_id=input_data.get("template_doc_id"),
            reference_doc_ids=input_data.get("reference_doc_ids", []),
            model_override=input_data.get("model_override")
        ):
            # Forward thinking states
            if event.get("type") == "thinking_state":
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "thinking_state",
                        "run_id": run_id,
                        "node": event.get("node", "unknown"),
                        "label": event.get("label", "Processing..."),
                        "timestamp": datetime.now().isoformat()
                    })
                }
                
                # Update run with thinking state
                if run_id in workflow_runs:
                    workflow_runs[run_id].thinking_states.append(event.get("label", ""))
            
            # Forward progress updates
            elif event.get("type") == "draft_progress":
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "progress",
                        "run_id": run_id,
                        "node": event.get("node", "unknown"),
                        "progress": "Drafting in progress...",
                        "timestamp": datetime.now().isoformat()
                    })
                }
            
            # Forward citations
            elif event.get("type") == "citation":
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "citation",
                        "run_id": run_id,
                        "citation": event.get("citation", {}),
                        "timestamp": datetime.now().isoformat()
                    })
                }
            
            # Handle errors
            elif event.get("type") == "error":
                if run_id in workflow_runs:
                    workflow_runs[run_id].status = WorkflowRunStatus.FAILED
                    workflow_runs[run_id].error_message = event.get("error", "Unknown error")
                
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "type": "error",
                        "run_id": run_id,
                        "error": event.get("error", "Unknown error"),
                        "node": event.get("node", "workflow"),
                        "timestamp": datetime.now().isoformat()
                    })
                }
                return
        
        # Execute full workflow for final result
        result = await qaai_workflow.run(
            prompt=input_data.get("prompt", ""),
            jurisdiction=JurisdictionType(input_data.get("jurisdiction", "DIFC")),
            template_doc_id=input_data.get("template_doc_id"),
            reference_doc_ids=input_data.get("reference_doc_ids", []),
            model_override=input_data.get("model_override")
        )
        
        # Update run with final result
        if run_id in workflow_runs:
            workflow_runs[run_id].status = WorkflowRunStatus.COMPLETED
            workflow_runs[run_id].output_data = result.get("output", {})
            workflow_runs[run_id].completed_at = datetime.now()
        
        # Emit completion
        yield {
            "event": "message",
            "data": json.dumps({
                "type": "workflow_complete",
                "run_id": run_id,
                "success": result.get("success", False),
                "output": result.get("output", {}),
                "citations": result.get("citations", []),
                "timestamp": datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        # Update run with error
        if run_id in workflow_runs:
            workflow_runs[run_id].status = WorkflowRunStatus.FAILED
            workflow_runs[run_id].error_message = str(e)
        
        yield {
            "event": "error",
            "data": json.dumps({
                "type": "error",
                "run_id": run_id,
                "error": f"Workflow execution error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
        }


@router.post("/draft-from-template/run")
async def run_draft_from_template(
    prompt: str = Form(...),
    jurisdiction: str = Form("DIFC"),
    template_file: Optional[UploadFile] = File(None),
    reference_files: Optional[list[UploadFile]] = File(None),
    model_override: Optional[str] = Form(None)
):
    """
    Execute "Draft from Template (DIFC)" workflow with SSE streaming.
    
    Supports template upload and reference document selection.
    """
    try:
        # Generate run ID
        run_id = str(uuid.uuid4())
        
        # Process uploaded files
        template_doc_id = None
        reference_doc_ids = []
        
        if template_file:
            # In production, would store file and get ID
            template_doc_id = f"template_{run_id}"
        
        if reference_files:
            # In production, would store files and get IDs
            reference_doc_ids = [f"ref_{i}_{run_id}" for i in range(len(reference_files))]
        
        # Create workflow run record
        workflow_run = WorkflowRun(
            id=run_id,
            workflow_type="draft-from-template",
            status=WorkflowRunStatus.PENDING,
            input_data={
                "prompt": prompt,
                "jurisdiction": jurisdiction,
                "template_doc_id": template_doc_id,
                "reference_doc_ids": reference_doc_ids,
                "model_override": model_override
            },
            thinking_states=[],
            created_at=datetime.now()
        )
        
        workflow_runs[run_id] = workflow_run
        
        # Return SSE stream
        return EventSourceResponse(
            stream_workflow_execution(
                run_id=run_id,
                workflow_type="draft-from-template",
                input_data=workflow_run.input_data
            ),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution error: {str(e)}")


@router.post("/draft-from-template/run-sync")
async def run_draft_from_template_sync(
    prompt: str = Form(...),
    jurisdiction: str = Form("DIFC"),
    template_file: Optional[UploadFile] = File(None),
    reference_files: Optional[list[UploadFile]] = File(None),
    model_override: Optional[str] = Form(None)
):
    """
    Synchronous version of draft from template workflow.
    
    Returns complete result without streaming.
    """
    try:
        # Generate run ID
        run_id = str(uuid.uuid4())
        
        # Process uploaded files (simplified)
        template_doc_id = f"template_{run_id}" if template_file else None
        reference_doc_ids = [f"ref_{i}_{run_id}" for i in range(len(reference_files))] if reference_files else []
        
        # Execute workflow
        result = await qaai_workflow.run(
            prompt=prompt,
            jurisdiction=JurisdictionType(jurisdiction),
            template_doc_id=template_doc_id,
            reference_doc_ids=reference_doc_ids,
            model_override=model_override
        )
        
        # Create workflow run record
        workflow_run = WorkflowRun(
            id=run_id,
            workflow_type="draft-from-template",
            status=WorkflowRunStatus.COMPLETED if result["success"] else WorkflowRunStatus.FAILED,
            input_data={
                "prompt": prompt,
                "jurisdiction": jurisdiction,
                "template_doc_id": template_doc_id,
                "reference_doc_ids": reference_doc_ids,
                "model_override": model_override
            },
            output_data=result.get("output", {}),
            thinking_states=result.get("thinking_states", []),
            error_message=result.get("error"),
            created_at=datetime.now(),
            completed_at=datetime.now() if result["success"] else None
        )
        
        workflow_runs[run_id] = workflow_run
        
        return {
            "run_id": run_id,
            "success": result["success"],
            "output": result["output"],
            "thinking_states": result["thinking_states"],
            "citations": result["citations"],
            "error": result["error"],
            "verification_passed": result["verification_passed"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution error: {str(e)}")


@router.get("/runs/{run_id}")
async def get_workflow_run(run_id: str):
    """Get workflow run status and results."""
    try:
        if run_id not in workflow_runs:
            raise HTTPException(status_code=404, detail="Workflow run not found")
        
        run = workflow_runs[run_id]
        
        return {
            "run_id": run.id,
            "workflow_type": run.workflow_type,
            "status": run.status.value,
            "input_data": run.input_data,
            "output_data": run.output_data,
            "thinking_states": run.thinking_states,
            "error_message": run.error_message,
            "created_at": run.created_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Run retrieval error: {str(e)}")


@router.get("/runs")
async def list_workflow_runs(
    limit: int = 20,
    offset: int = 0,
    workflow_type: Optional[str] = None,
    status: Optional[str] = None
):
    """List workflow runs with filtering and pagination."""
    try:
        # Filter runs
        filtered_runs = []
        for run in workflow_runs.values():
            if workflow_type and run.workflow_type != workflow_type:
                continue
            if status and run.status.value != status:
                continue
            filtered_runs.append(run)
        
        # Sort by creation time (newest first)
        filtered_runs.sort(key=lambda x: x.created_at, reverse=True)
        
        # Apply pagination
        total_count = len(filtered_runs)
        paginated_runs = filtered_runs[offset:offset + limit]
        
        # Convert to response format
        runs_data = []
        for run in paginated_runs:
            runs_data.append({
                "run_id": run.id,
                "workflow_type": run.workflow_type,
                "status": run.status.value,
                "created_at": run.created_at.isoformat(),
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "has_error": bool(run.error_message)
            })
        
        return {
            "runs": runs_data,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Run listing error: {str(e)}")


@router.get("/types")
async def get_workflow_types():
    """Get available workflow types and their descriptions."""
    return {
        "workflow_types": [
            {
                "id": "draft-from-template",
                "name": "Draft from Template (DIFC)",
                "description": "Upload template and references to generate DIFC-compliant draft with citations",
                "inputs": [
                    {"name": "prompt", "type": "text", "required": True, "description": "Drafting instructions"},
                    {"name": "jurisdiction", "type": "select", "required": False, "default": "DIFC", "options": ["DIFC", "DFSA", "UAE", "OTHER"]},
                    {"name": "template_file", "type": "file", "required": False, "description": "Template document"},
                    {"name": "reference_files", "type": "files", "required": False, "description": "Reference documents"},
                    {"name": "model_override", "type": "select", "required": False, "description": "Manual model selection"}
                ],
                "outputs": [
                    "Redlined draft document",
                    "Citation list with verification",
                    "Thinking states and process log"
                ],
                "estimated_duration": "2-5 minutes",
                "supports_streaming": True
            }
        ]
    }


@router.get("/graph")
async def get_workflow_graph():
    """Get workflow graph visualization data."""
    try:
        return qaai_workflow.get_graph_visualization()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph visualization error: {str(e)}")