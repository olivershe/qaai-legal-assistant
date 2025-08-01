name: "QaAI Legal Assistant System - Complete Implementation"
description: |

## Purpose
Implement a complete Harvey-style, DIFC-focused legal AI demo system with React frontend, FastAPI backend, LangGraph orchestration, and comprehensive RAG capabilities. This PRP provides all necessary context for implementing a production-ready legal AI assistant with Assistant, Vault, and Workflow surfaces.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

## Mandatory Files to Read
- INITIAL.md — feature requirements (this file)
- CLAUDE.md — project rules (naming, tests, limits, style)
- examples/design/*.profile.json — canonical UI design tokens (Assistant/Vault/Workflow)

---

## Goal
Build a comprehensive legal AI assistant system with:
- **Assistant surface** (Assist/Draft modes) with visible thinking states and SSE streaming
- **Vault** for document management and review tables
- **Workflows** for agentic processes like "Draft from Template (DIFC)"
- **LangGraph orchestration** with deterministic, inspectable graphs
- **Multi-model routing** (OpenAI/Anthropic) with manual override
- **RAG system** using local FS, SQLite, and FAISS with DIFC-first retrieval
- **Citation verification** with binary match validation
- **React UI** following JSON design profiles as single source of truth

## Why
- **Business value**: Provides comprehensive legal AI assistance specifically for DIFC jurisdiction
- **Integration**: Demonstrates modern AI application architecture with proper separation of concerns
- **Problems solved**: Creates a complete legal research and drafting environment for legal professionals

## What
A full-stack legal AI application with:
- Frontend: React + Tailwind + shadcn/ui consuming JSON design profiles
- Backend: FastAPI with async endpoints and SSE streaming
- AI Orchestration: LangGraph for complex workflows
- Storage: Local filesystem + SQLite + FAISS vectors
- Models: OpenAI (gpt-4.1, o1, o3) + Anthropic (claude-3.7-sonnet)

### Success Criteria
- [ ] Assistant modes (Assist/Draft) with streaming thinking states
- [ ] Vault project management with document upload and search
- [ ] LangGraph workflow execution with proper state management
- [ ] RAG retrieval with DIFC-first filtering and citations
- [ ] Multi-model routing with manual override capability
- [ ] Full UI implementation following design profiles exactly
- [ ] Comprehensive test coverage with validation gates
- [ ] Production-ready deployment configuration


## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window

# LangChain/LangGraph
- url: https://python.langchain.com/docs/concepts/
  why: Core concepts for agent architecture and state management
  
- url: https://langchain-ai.github.io/langgraph/concepts/why-langgraph/
  why: LangGraph fundamentals for deterministic workflow orchestration
  
- url: https://langchain-ai.github.io/langgraph/how-tos/
  why: Practical implementation patterns for nodes, edges, and state

# FastAPI & SSE Streaming
- url: https://fastapi.tiangolo.com/
  why: FastAPI fundamentals for async API development
  
- url: https://pypi.org/project/fastapi-sse/
  why: Server-sent events implementation for streaming responses
  
- url: https://www.softgrade.org/sse-with-fastapi-react-langgraph/
  why: Complete SSE integration pattern with React and LangGraph

# React & UI
- url: https://ui.shadcn.com/
  why: shadcn/ui component library and design system patterns
  
- url: https://ui.shadcn.com/docs/tailwind-v4
  why: Tailwind v4 integration and theming best practices

# AI APIs
- url: https://platform.openai.com/docs/
  why: OpenAI API integration, rate limiting, and model routing
  
- url: https://docs.anthropic.com/en/api/rate-limits
  why: Anthropic API rate limiting and token management
  
- url: https://support.anthropic.com/en/articles/8243635-our-approach-to-api-rate-limits
  why: Token bucket algorithm and retry strategies

# Vector Search & RAG
- url: https://www.visionnlp.com/blog/Practical-Implementation-of-FAISS-Vector-Database-for-RAG-35362
  why: FAISS implementation patterns for RAG systems
  
- url: https://www.chitika.com/hybrid-retrieval-rag/
  why: Hybrid retrieval combining BM25 and FAISS for better precision

# Database & Async
- url: https://medium.com/@tclaitken/setting-up-a-fastapi-app-with-async-sqlalchemy-2-0-pydantic-v2-e6c540be4308
  why: Async SQLAlchemy 2.0 with FastAPI best practices

# Existing Examples (CRITICAL)
- file: examples/assistant_run.py
  why: SSE streaming pattern for Assistant API calls
  
- file: examples/workflow_draft_from_template.graph.py
  why: LangGraph structure for DIFC-focused workflows
  
- file: examples/rag_ingest.py
  why: FAISS indexing and SQLite metadata patterns
  
- file: examples/citations_check.py
  why: Binary match verification for citation validation
  
- file: examples/design/assistant.profile.json
  why: Complete UI design tokens and component specifications
  
- file: examples/design/vault.profile.json
  why: Vault-specific UI patterns and layout structure
  
- file: examples/design/workflow.draft-from-template.profile.json
  why: Workflow UI patterns and step-by-step visualization
```

### Current Codebase tree
```bash
Context-Engineering-Intro/
├── CLAUDE.md                          # Project rules and conventions
├── INITIAL.md                         # Feature requirements specification  
├── examples/                          # Implementation patterns and references
│   ├── README.md                      # Example explanations and usage
│   ├── assistant_run.py               # SSE streaming for Assistant API
│   ├── workflow_draft_from_template.graph.py  # LangGraph workflow structure
│   ├── rag_ingest.py                  # FAISS + SQLite indexing
│   ├── citations_check.py             # Binary match citation verification
│   ├── design/                        # UI design profiles (SINGLE SOURCE OF TRUTH)
│   │   ├── README.md                  # Design token usage patterns
│   │   ├── assistant.profile.json     # Assistant UI specification
│   │   ├── vault.profile.json         # Vault UI specification
│   │   └── workflow.draft-from-template.profile.json  # Workflow UI
│   └── sample_corpus/                 # Sample DIFC documents for testing
├── PRPs/                              # Project Requirements Prompts
│   └── templates/
│       └── prp_base.md               # PRP template structure
└── use-cases/                         # Related implementation examples
```

### Desired Codebase tree with files to be added
```bash
qaai-system/
├── .env.example                       # Environment variables template
├── requirements.txt                   # Python dependencies
├── README.md                          # Comprehensive setup documentation
├── venv_linux/                        # Virtual environment (use for all commands)
├── apps/
│   ├── api/                           # FastAPI backend
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app with SSE endpoints
│   │   ├── agents/                    # LangGraph agents and orchestration
│   │   │   ├── __init__.py
│   │   │   ├── graph.py               # LangGraph composition (nodes/edges/routing)
│   │   │   ├── nodes.py               # Node implementations (preflight/plan/retrieve/draft/verify)
│   │   │   ├── prompts.py             # DIFC-first system prompts and templates
│   │   │   └── router.py              # Model selection per step
│   │   ├── api/                       # API route definitions
│   │   │   ├── __init__.py
│   │   │   ├── assistant.py           # Assistant endpoints (query with SSE)
│   │   │   ├── vault.py               # Vault project management endpoints
│   │   │   ├── workflows.py           # Workflow execution endpoints
│   │   │   └── ingest.py              # Document ingestion endpoints
│   │   ├── core/                      # Core business logic
│   │   │   ├── __init__.py
│   │   │   ├── config.py              # Settings and environment management
│   │   │   ├── models.py              # Pydantic models for API
│   │   │   ├── database.py            # Async SQLite connection management
│   │   │   └── storage.py             # File system storage management
│   │   ├── rag/                       # RAG implementation
│   │   │   ├── __init__.py
│   │   │   ├── vector_store.py        # FAISS vector operations
│   │   │   ├── retrievers.py          # DIFC-first retrieval logic
│   │   │   ├── embeddings.py          # Embedding generation
│   │   │   └── citations.py           # Citation verification (binary match)
│   │   ├── services/                  # External service integrations
│   │   │   ├── __init__.py
│   │   │   ├── openai_client.py       # OpenAI API client with rate limiting
│   │   │   └── anthropic_client.py    # Anthropic API client with rate limiting
│   │   └── tests/                     # Comprehensive test suite
│   │       ├── __init__.py
│   │       ├── test_api/              # API endpoint tests
│   │       ├── test_agents/           # LangGraph workflow tests
│   │       ├── test_rag/              # RAG system tests
│   │       └── fixtures/              # Test data and mocks
│   └── web/                           # React frontend
│       ├── package.json               # Node.js dependencies
│       ├── tailwind.config.js         # Tailwind v4 configuration
│       ├── vite.config.ts             # Vite build configuration
│       ├── src/
│       │   ├── main.tsx               # React app entry point
│       │   ├── App.tsx                # Main app component with routing
│       │   ├── components/            # UI components following design profiles
│       │   │   ├── ui/                # shadcn/ui base components
│       │   │   ├── layout/            # Layout components (AppSidebar, PageHeader)
│       │   │   ├── assistant/         # Assistant-specific components
│       │   │   ├── vault/             # Vault-specific components
│       │   │   └── workflows/         # Workflow-specific components
│       │   ├── hooks/                 # React hooks for API and state
│       │   ├── services/              # API client and SSE handling
│       │   ├── types/                 # TypeScript type definitions
│       │   ├── utils/                 # Utility functions and helpers
│       │   └── styles/                # CSS variables from design profiles
│       └── public/                    # Static assets
├── data/                              # Local storage
│   ├── files/                         # Uploaded documents
│   ├── index/                         # FAISS index files
│   └── qaai.db                        # SQLite database
└── docs/                              # Documentation
    ├── API.md                         # API documentation
    ├── DEPLOYMENT.md                  # Deployment instructions
    └── SOURCES.md                     # DIFC/DFSA source documentation
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: FastAPI + AsyncIO
# FastAPI requires async functions for endpoints that do I/O
# Never mix sync and async database operations

# CRITICAL: LangGraph State Management  
# State must be TypedDict with total=False for partial updates
# All node functions must return state updates, not modify in place
# Use emit() pattern for thinking states as shown in examples

# CRITICAL: SSE Streaming
# Use fastapi-sse or StreamingResponse for proper SSE formatting
# Always include proper CORS headers for browser compatibility
# Handle client disconnections gracefully

# CRITICAL: FAISS Vector Operations
# Use normalize_embeddings=True for consistent similarity scoring
# IndexFlatIP for small datasets, IndexIVFFlat for scale
# Always use consistent embedding models between index and query

# CRITICAL: OpenAI/Anthropic Rate Limiting
# Implement exponential backoff with jitter
# Honor Retry-After headers from 429 responses
# Use token bucket approach for proactive rate limiting

# CRITICAL: SQLite + AsyncIO
# Use aiosqlite driver: sqlite+aiosqlite:///./data/qaai.db
# Set expire_on_commit=False for async sessions
# Use proper session management with dependency injection

# CRITICAL: React + Design Profiles
# JSON profiles in examples/design/ are SINGLE SOURCE OF TRUTH
# Map tokens to CSS variables at runtime or build time
# Never hardcode colors, spacing, or typography

# CRITICAL: Citation Verification
# Binary match is lightweight proxy for production LLM verification
# Use Jaccard similarity with threshold >= 0.25
# Always include section references in citations

# CRITICAL: DIFC-First Filtering
# Boost DIFC Laws, Regulations, Court Rules, DFSA Rulebook in retrieval
# Include jurisdiction metadata in all document ingestion
# Default knowledge source picker to DIFC sources

# CRITICAL: Virtual Environment
# ALWAYS use venv_linux for all Python commands including tests
# Never install packages globally or outside venv
```

## Implementation Blueprint

### Data models and structure

```python
# core/models.py - Core data structures following examples
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from enum import Enum

class JurisdictionType(str, Enum):
    DIFC = "DIFC"
    DFSA = "DFSA" 
    UAE = "UAE"
    OTHER = "OTHER"

class InstrumentType(str, Enum):
    LAW = "Law"
    REGULATION = "Regulation"
    COURT_RULE = "CourtRule"
    RULEBOOK = "Rulebook"
    NOTICE = "Notice"
    OTHER = "Other"

class AssistantMode(str, Enum):
    ASSIST = "assist"
    DRAFT = "draft"

# Assistant API Models
class KnowledgeFilter(BaseModel):
    jurisdiction: JurisdictionType = JurisdictionType.DIFC
    sources: List[str] = ["DIFC_LAWS", "DFSA_RULEBOOK", "DIFC_COURTS_RULES", "VAULT"]

class AssistantQuery(BaseModel):
    mode: AssistantMode
    prompt: str = Field(..., min_length=1)
    knowledge: KnowledgeFilter = Field(default_factory=KnowledgeFilter)
    vault_project_id: Optional[str] = None
    attachments: List[str] = Field(default_factory=list)

class ThinkingState(BaseModel):
    type: Literal["thinking_state"] = "thinking_state"
    label: str
    timestamp: datetime = Field(default_factory=datetime.now)

class TextChunk(BaseModel):
    type: Literal["chunk"] = "chunk"
    text: str

class Citation(BaseModel):
    type: Literal["citation"] = "citation"
    title: str
    section: Optional[str] = None
    url: Optional[str] = None
    instrument_type: InstrumentType
    jurisdiction: JurisdictionType

class StreamDone(BaseModel):
    type: Literal["done"] = "done"
    final_response: str
    citations: List[Citation]

# Vault Models
class VaultProject(BaseModel):
    id: str
    name: str
    visibility: Literal["private", "shared"] = "private"
    document_count: int = 0
    created_at: datetime
    updated_at: datetime
    owner: str

class DocumentMetadata(BaseModel):
    id: str
    project_id: str
    filename: str
    title: str
    file_path: str
    content_type: str
    size_bytes: int
    jurisdiction: JurisdictionType
    instrument_type: InstrumentType
    upload_date: datetime

# LangGraph State (following examples/workflow_draft_from_template.graph.py)
class WorkflowState(TypedDict, total=False):
    prompt: str
    template_doc_id: Optional[str]
    reference_doc_ids: List[str]
    jurisdiction: JurisdictionType
    plan: str
    retrieved_context: List[Dict[str, Any]]
    citations: List[Citation]
    draft: str
    thinking: List[str]
    error: Optional[str]
    model_override: Optional[str]

# RAG Models
class EmbeddingDocument(BaseModel):
    id: str
    content: str
    metadata: DocumentMetadata
    
class RetrievalResult(BaseModel):
    document: EmbeddingDocument
    score: float
    chunk_index: int
```

### List of tasks to be completed

```yaml
Task 1: Setup Core Infrastructure
CREATE .env.example:
  - PATTERN: Follow examples structure with comprehensive variable documentation
  - Include OpenAI/Anthropic keys, storage paths, database URLs
  - Add DIFC-specific configuration variables

CREATE apps/api/core/config.py:
  - PATTERN: Use pydantic-settings like CLAUDE.md specifies
  - Load environment variables with DIFC-first defaults
  - Include model routing configuration

CREATE apps/api/core/database.py:
  - PATTERN: Follow async SQLite patterns from research
  - Use sqlite+aiosqlite:///./data/qaai.db
  - Implement proper session management with dependency injection

Task 2: Implement RAG System Foundation
CREATE apps/api/rag/vector_store.py:
  - PATTERN: Mirror examples/rag_ingest.py structure
  - Use FAISS IndexFlatIP for demo, IndexIVFFlat for scale
  - Implement hybrid retrieval (BM25 + FAISS) for 2025 best practices

CREATE apps/api/rag/embeddings.py:
  - PATTERN: Support both sentence-transformers and OpenAI embeddings
  - Use normalize_embeddings=True for consistent scoring
  - Include proper error handling and rate limiting

CREATE apps/api/rag/citations.py:
  - PATTERN: Extend examples/citations_check.py binary match
  - Implement Jaccard similarity with 0.25 threshold
  - Add jurisdiction-aware citation verification

Task 3: Build LangGraph Orchestration
CREATE apps/api/agents/graph.py:
  - PATTERN: Follow examples/workflow_draft_from_template.graph.py structure
  - Implement deterministic graph: preflight → plan → retrieve → draft → verify → export
  - Add proper error handling and retry policies

CREATE apps/api/agents/nodes.py:
  - PATTERN: Use emit() pattern for thinking states
  - Implement per-step model routing (reasoning vs drafting vs verification)
  - Include DIFC-first retrieval with jurisdiction boosting

CREATE apps/api/agents/prompts.py:
  - PATTERN: Create DIFC-focused system prompts
  - Include templates for planner, drafter, verifier roles
  - Add non-legal-advice disclaimers to all outputs

CREATE apps/api/agents/router.py:
  - PATTERN: Implement model selection logic
  - Route: o1 for planning, gpt-4.1 for drafting, claude-3.7-sonnet for long-context
  - Support manual model override from UI

Task 4: Implement FastAPI Backend with SSE
CREATE apps/api/main.py:
  - PATTERN: Follow FastAPI async patterns with proper CORS
  - Include lifespan events for database initialization
  - Set up proper error handling and logging

CREATE apps/api/api/assistant.py:
  - PATTERN: Mirror examples/assistant_run.py SSE streaming
  - Use fastapi-sse for proper SSE event formatting
  - Stream thinking states, text chunks, citations, and done events

CREATE apps/api/api/vault.py:
  - PATTERN: Implement CRUD operations for projects and documents
  - Support file upload with metadata extraction
  - Include search functionality with RAG integration

CREATE apps/api/api/workflows.py:
  - PATTERN: Execute LangGraph workflows with SSE streaming
  - Support "Draft from Template (DIFC)" workflow
  - Return status, artifacts, and thinking states

Task 5: Build React Frontend with Design Profiles
CREATE apps/web/src/services/design-profiles.ts:
  - PATTERN: Runtime loading of examples/design/*.json profiles
  - Map tokens to CSS variables following examples/design/README.md
  - Support theme switching and profile inheritance

CREATE apps/web/src/components/layout/AppSidebar.tsx:
  - PATTERN: Follow assistant.profile.json specifications exactly
  - Implement navigation with active states and context selector
  - Use semantic colors and spacing from design profiles

CREATE apps/web/src/components/assistant/AssistantPromptArea.tsx:
  - PATTERN: Follow assistant.profile.json prompt area specification
  - Implement file upload dropzone and knowledge source picker
  - Include proper accessibility patterns from design profiles

CREATE apps/web/src/hooks/useSSEStream.ts:
  - PATTERN: Handle SSE events from backend
  - Support thinking states, text chunks, citations, and completion
  - Implement proper reconnection and error handling

Task 6: Implement Vault Interface
CREATE apps/web/src/components/vault/ProjectGrid.tsx:
  - PATTERN: Follow vault.profile.json grid specifications
  - Implement NewProjectCard and ProjectCard components
  - Support drag-and-drop file uploads with progress indication

CREATE apps/web/src/components/vault/ToolbarFilters.tsx:
  - PATTERN: Implement segmented controls and search from vault profile
  - Support All/Private/Shared filtering
  - Include proper keyboard navigation and accessibility

Task 7: Build Workflow Interface
CREATE apps/web/src/components/workflows/WorkflowRunner.tsx:
  - PATTERN: Follow workflow.draft-from-template.profile.json
  - Display step-by-step progress with thinking states
  - Support template upload and reference document selection

CREATE apps/web/src/components/workflows/WorkflowGallery.tsx:
  - PATTERN: Implement gallery cards from assistant profile
  - Support "For General Work" and "For Transactional Work" groupings
  - Include proper metadata display (steps, duration estimates)

Task 8: Implement Comprehensive Testing
CREATE apps/api/tests/test_api/:
  - PATTERN: Mirror existing test structure from use-cases
  - Test all endpoints with proper mocking of external APIs
  - Include SSE streaming tests and error handling

CREATE apps/api/tests/test_agents/:
  - PATTERN: Test LangGraph workflows with mock dependencies
  - Verify thinking state emission and proper state management
  - Test model routing and fallback mechanisms

CREATE apps/api/tests/test_rag/:
  - PATTERN: Test vector operations and citation verification
  - Include DIFC-first retrieval and jurisdiction filtering
  - Test hybrid retrieval accuracy and performance

Task 9: Production Configuration and Deployment
CREATE requirements.txt:
  - PATTERN: Include all dependencies with pinned versions
  - Add fastapi-sse, aiosqlite, faiss-cpu, sentence-transformers
  - Include development dependencies for testing and linting

CREATE README.md:
  - PATTERN: Comprehensive setup documentation
  - Include DIFC corpus setup and API key configuration
  - Add deployment instructions and architecture overview

CREATE docs/API.md:
  - PATTERN: Full API documentation with examples
  - Document SSE event formats and error responses
  - Include rate limiting and authentication details
```

### Integration Points
```yaml
ENVIRONMENT:
  - file: .env.example
  - vars: |
      # Model Providers
      OPENAI_API_KEY=sk-...
      ANTHROPIC_API_KEY=claude-...
      
      # Default Model Configuration
      DEFAULT_PLANNER_MODEL=o1
      DEFAULT_DRAFTER_MODEL=gpt-4.1
      DEFAULT_VERIFIER_MODEL=claude-3.7-sonnet
      
      # Storage & Database
      STORAGE_PATH=./data/files
      DB_URL=sqlite+aiosqlite:///./data/qaai.db
      VECTOR_STORE=faiss
      INDEX_DIR=./data/index
      
      # RAG Configuration
      EMBEDDINGS_BACKEND=sentence-transformers
      EMBEDDINGS_MODEL=all-MiniLM-L6-v2
      CHUNK_SIZE=800
      CHUNK_OVERLAP=120
      
      # DIFC Configuration
      DEFAULT_JURISDICTION=DIFC
      CITATION_THRESHOLD=0.25
      
      # Application
      APP_ENV=dev
      LOG_LEVEL=INFO
      BACKEND_URL=http://localhost:8000
      
DATABASE_SCHEMA:
  - migration: |
      CREATE TABLE documents (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        path TEXT NOT NULL,
        jurisdiction TEXT NOT NULL,
        instrument_type TEXT NOT NULL,
        url TEXT,
        enactment_date TEXT,
        commencement_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
      
      CREATE TABLE vault_projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        visibility TEXT DEFAULT 'private',
        document_count INTEGER DEFAULT 0,
        owner TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
      
      CREATE TABLE chunks (
        id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        section_ref TEXT,
        FOREIGN KEY(doc_id) REFERENCES documents(id)
      );

FRONTEND_BUILD:
  - build_command: "npm run build"
  - dependencies: |
      {
        "dependencies": {
          "react": "^18.2.0",
          "react-dom": "^18.2.0",
          "react-router-dom": "^6.8.0",
          "@tailwindcss/forms": "^0.5.7",
          "tailwindcss": "^4.0.0",
          "@types/react": "^18.2.0",
          "typescript": "^5.0.0",
          "vite": "^5.0.0"
        }
      }
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Backend validation (run in venv_linux)
cd apps/api && source ../../venv_linux/bin/activate
ruff check . --fix              # Auto-fix style issues
mypy . --ignore-missing-imports # Type checking
black . --check                 # Code formatting validation

# Frontend validation
cd apps/web
npm run lint                    # ESLint validation
npm run type-check              # TypeScript validation
npm run build                   # Build validation

# Expected: No errors. If errors, READ error messages and fix systematically.
```

### Level 2: Unit Tests
```bash
# Backend tests (use venv_linux)
cd apps/api && source ../../venv_linux/bin/activate
pytest tests/test_api/ -v --cov=api
pytest tests/test_agents/ -v --cov=agents  
pytest tests/test_rag/ -v --cov=rag

# Key test patterns:
# - Mock external API calls (OpenAI/Anthropic)
# - Test SSE streaming with async test clients
# - Verify LangGraph state transitions
# - Test DIFC-first retrieval filtering
# - Validate citation verification accuracy

# Frontend tests
cd apps/web
npm test                        # Jest/Vitest unit tests
npm run test:e2e               # Playwright E2E tests

# Expected: >80% test coverage, all tests passing
```

### Level 3: Integration Test
```bash
# Start backend (use venv_linux)
cd apps/api && source ../../venv_linux/bin/activate
python -m uvicorn main:app --reload --port 8000

# Start frontend
cd apps/web
npm run dev

# Manual testing checklist:
# 1. Assistant Assist mode with SSE streaming
curl -N -X POST http://localhost:8000/api/assistant/query \
  -H "Content-Type: application/json" \
  -d '{"mode":"assist","prompt":"Explain DIFC Employment Law basics with citations","knowledge":{"jurisdiction":"DIFC"}}'

# Expected: Stream of thinking_state, chunk, citation, and done events

# 2. Vault project creation and file upload
# Navigate to http://localhost:3000/vault
# Create new project, upload sample DIFC documents
# Verify search functionality works

# 3. Workflow execution
# Navigate to http://localhost:3000/workflows
# Execute "Draft from Template (DIFC)" workflow
# Verify thinking states display and final artifact generation

# 4. Design profile consistency
# Verify UI matches examples/design/*.json specifications exactly
# Test dark/light mode if implemented
# Validate accessibility with screen reader
```

### Level 4: RAG and Citation Validation
```bash
# Test document ingestion (use venv_linux)
cd apps/api && source ../../venv_linux/bin/activate
python -c "
from rag.vector_store import build_index
from core.config import settings
import os

# Ingest sample DIFC corpus
os.makedirs('../../examples/sample_corpus', exist_ok=True)
# Add sample DIFC documents to corpus directory
build_index('../../examples/sample_corpus')
print('Index built successfully')
"

# Test retrieval accuracy
python -c "
from rag.retrievers import retrieve_with_citations
from rag.citations import verify_citations

query = 'DIFC employment law minimum leave requirements'
results = retrieve_with_citations(query, jurisdiction='DIFC', limit=5)
verified = verify_citations(query, results)
print(f'Retrieved {len(results)} results, {len(verified)} verified citations')
"

# Expected: Relevant DIFC documents retrieved with high confidence citations
```

## Final Validation Checklist
- [ ] All tests pass: `pytest apps/api/tests/ -v && npm test --prefix apps/web`
- [ ] No linting errors: `ruff check apps/api/ && npm run lint --prefix apps/web`
- [ ] No type errors: `mypy apps/api/ && npm run type-check --prefix apps/web`
- [ ] SSE streaming works with proper event formatting
- [ ] LangGraph workflows execute with visible thinking states
- [ ] DIFC-first retrieval returns relevant legal documents
- [ ] Citation verification filters invalid references
- [ ] UI exactly matches design profile specifications
- [ ] File upload and vault management functional
- [ ] Model routing works with manual override capability
- [ ] Rate limiting handles API errors gracefully
- [ ] Virtual environment (venv_linux) used for all Python operations
- [ ] Documentation includes clear setup and usage instructions

---

## Anti-Patterns to Avoid
- ❌ Don't hardcode design tokens - always use JSON profiles
- ❌ Don't skip virtual environment usage for Python operations
- ❌ Don't ignore rate limiting - implement proper backoff strategies
- ❌ Don't mix sync and async database operations
- ❌ Don't skip citation verification - accuracy is critical for legal AI
- ❌ Don't ignore DIFC-first filtering - jurisdiction focus is key requirement
- ❌ Don't forget thinking state emission - transparency is essential
- ❌ Don't skip comprehensive testing - quality gates prevent production issues
- ❌ Don't commit secrets or API keys - use environment variables
- ❌ Don't assume libraries exist - verify all dependencies in requirements.txt

## Confidence Score: 9/10

High confidence due to:
- Comprehensive examples provided in the codebase
- Well-documented external APIs and libraries  
- Clear design specifications in JSON profiles
- Proven patterns from similar implementations
- Detailed validation gates at multiple levels
- DIFC legal domain expertise embedded in examples

Minor uncertainty around:
- Specific DIFC document corpus structure and availability
- Production deployment configuration details
- Real-world performance characteristics of hybrid retrieval

The extensive context, examples, and validation loops provide strong foundation for successful one-pass implementation.