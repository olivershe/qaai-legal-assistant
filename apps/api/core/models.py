"""
Pydantic models for QaAI API.

Following the PRP data model specifications and examples patterns.
Includes all models for Assistant, Vault, RAG, and LangGraph workflow state.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any, TypedDict
from datetime import datetime
from enum import Enum


class JurisdictionType(str, Enum):
    """Legal jurisdictions with DIFC-first focus."""
    DIFC = "DIFC"
    DFSA = "DFSA" 
    UAE = "UAE"
    OTHER = "OTHER"


class InstrumentType(str, Enum):
    """Legal instrument types for document classification."""
    LAW = "Law"
    REGULATION = "Regulation"
    COURT_RULE = "CourtRule"
    RULEBOOK = "Rulebook"
    NOTICE = "Notice"
    OTHER = "Other"


class AssistantMode(str, Enum):
    """Assistant operation modes as specified in requirements."""
    ASSIST = "assist"  # Quick answers, Q&A, summaries
    DRAFT = "draft"    # Structured outputs with draft editor


# Assistant API Models
class KnowledgeFilter(BaseModel):
    """Knowledge source filtering with DIFC-first defaults."""
    jurisdiction: JurisdictionType = JurisdictionType.DIFC
    sources: List[str] = Field(
        default=["DIFC_LAWS", "DFSA_RULEBOOK", "DIFC_COURTS_RULES", "VAULT"],
        description="Knowledge sources to query"
    )


class AssistantQuery(BaseModel):
    """Assistant query request following examples/assistant_run.py pattern."""
    mode: AssistantMode
    prompt: str = Field(..., min_length=1, description="User query or instruction")
    knowledge: KnowledgeFilter = Field(default_factory=KnowledgeFilter)
    vault_project_id: Optional[str] = Field(None, description="Specific Vault project to query")
    attachments: List[str] = Field(default_factory=list, description="File IDs to include in context")


# SSE Stream Event Models (following examples/assistant_run.py)
class ThinkingState(BaseModel):
    """Thinking state emission for transparency."""
    type: Literal["thinking_state"] = "thinking_state"
    label: str = Field(..., description="Human-readable thinking step")
    timestamp: datetime = Field(default_factory=datetime.now)


class TextChunk(BaseModel):
    """Streaming text chunk for real-time response."""
    type: Literal["chunk"] = "chunk"
    text: str = Field(..., description="Partial response text")


class Citation(BaseModel):
    """Legal citation with verification metadata."""
    type: Literal["citation"] = "citation"
    title: str = Field(..., description="Document title")
    section: Optional[str] = Field(None, description="Specific section reference")
    url: Optional[str] = Field(None, description="Document URL if available")
    instrument_type: InstrumentType = Field(..., description="Type of legal instrument")
    jurisdiction: JurisdictionType = Field(..., description="Legal jurisdiction")


class StreamDone(BaseModel):
    """Final event indicating stream completion."""
    type: Literal["done"] = "done"
    final_response: str = Field(..., description="Complete response text")
    citations: List[Citation] = Field(default_factory=list)


# Vault Models
class VaultProject(BaseModel):
    """Vault project for document organization."""
    id: str
    name: str = Field(..., min_length=1)
    visibility: Literal["private", "shared"] = "private"
    document_count: int = Field(0, ge=0)
    created_at: datetime
    updated_at: datetime
    owner: str = Field(..., description="Project owner identifier")


class DocumentMetadata(BaseModel):
    """Document metadata for storage and retrieval."""
    id: str
    project_id: str
    filename: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    file_path: str = Field(..., description="Relative path to stored file")
    content_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., ge=0)
    jurisdiction: JurisdictionType = Field(JurisdictionType.DIFC)
    instrument_type: InstrumentType = Field(InstrumentType.OTHER)
    upload_date: datetime


# LangGraph State (following examples/workflow_draft_from_template.graph.py)
class WorkflowState(TypedDict, total=False):
    """
    LangGraph state for workflow orchestration.
    
    Using TypedDict with total=False for partial updates as specified in gotchas.
    All node functions must return state updates, not modify in place.
    """
    prompt: str
    template_doc_id: Optional[str]
    reference_doc_ids: List[str]
    jurisdiction: JurisdictionType
    plan: str
    retrieved_context: List[Dict[str, Any]]
    citations: List[Citation]
    draft: str
    thinking: List[str]  # For emit() pattern
    error: Optional[str]
    model_override: Optional[str]  # Manual model selection


# RAG Models
class EmbeddingDocument(BaseModel):
    """Document with embedding for vector search."""
    id: str
    content: str = Field(..., description="Document text content")
    metadata: DocumentMetadata


class RetrievalResult(BaseModel):
    """Vector search result with similarity score."""
    document: EmbeddingDocument
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    chunk_index: int = Field(..., ge=0, description="Chunk position in document")


class CitationVerificationResult(BaseModel):
    """Result of binary match citation verification."""
    passed: bool = Field(..., description="Whether citation meets threshold")
    score: float = Field(..., ge=0.0, le=1.0, description="Jaccard similarity score")
    best_match: Optional[Dict[str, Any]] = Field(None, description="Best matching candidate")


# Workflow Models
class WorkflowRunStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowRun(BaseModel):
    """Workflow execution tracking."""
    id: str
    workflow_type: str = Field(..., description="Workflow identifier")
    status: WorkflowRunStatus = WorkflowRunStatus.PENDING
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    thinking_states: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


# Request/Response Models for API endpoints
class CreateProjectRequest(BaseModel):
    """Request to create new Vault project."""
    name: str = Field(..., min_length=1, max_length=255)
    visibility: Literal["private", "shared"] = "private"


class ProjectResponse(BaseModel):
    """Response containing project information."""
    project: VaultProject
    success: bool = True
    message: Optional[str] = None


class UploadResponse(BaseModel):
    """Response for file upload operations."""
    document: DocumentMetadata
    success: bool = True
    message: Optional[str] = None


class SearchRequest(BaseModel):
    """Request for document search within project."""
    query: str = Field(..., min_length=1)
    project_id: Optional[str] = Field(None, description="Limit search to specific project")
    jurisdiction: Optional[JurisdictionType] = None
    limit: int = Field(10, ge=1, le=50)


class SearchResponse(BaseModel):
    """Response containing search results."""
    results: List[RetrievalResult]
    total_count: int = Field(..., ge=0)
    query: str
    success: bool = True


# Ingestion Models
class IngestionStatus(str, Enum):
    """Document ingestion job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionJob(BaseModel):
    """Document ingestion job tracking."""
    id: str
    status: IngestionStatus = IngestionStatus.PENDING
    file_count: int = Field(..., ge=1)
    processed_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    document_ids: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    jurisdiction: JurisdictionType = JurisdictionType.DIFC
    instrument_type: InstrumentType = InstrumentType.OTHER
    project_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None