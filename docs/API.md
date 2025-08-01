# QaAI Legal Assistant API Documentation

Complete API reference for the QaAI Legal Assistant System, including authentication, endpoints, SSE streaming, and error handling.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Server-Sent Events (SSE)](#server-sent-events-sse)
- [API Endpoints](#api-endpoints)
  - [Assistant API](#assistant-api)
  - [Vault API](#vault-api)
  - [Workflows API](#workflows-api)
  - [Ingestion API](#ingestion-api)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Examples](#examples)

## Overview

The QaAI Legal Assistant API is built on FastAPI with async architecture, providing real-time streaming responses through Server-Sent Events (SSE). The API is DIFC-focused and designed for legal professionals working with DIFC jurisdiction documents.

**Base URL**: `http://localhost:8000` (development)  
**API Version**: v1  
**Content Type**: `application/json`

### Key Features

- **DIFC-First**: All operations prioritize DIFC Laws, Regulations, Court Rules, and DFSA Rulebook
- **SSE Streaming**: Real-time thinking states and progressive responses
- **Multi-Model Routing**: Intelligent routing between OpenAI and Anthropic models
- **Citation Verification**: Binary match validation with Jaccard similarity
- **Async Architecture**: Full async/await support with proper error handling

## Authentication

Currently, the API uses a demo authentication system. In production, implement proper JWT-based authentication.

### Demo Authentication

```bash
# No authentication required for development
curl -X GET http://localhost:8000/api/health
```

### Production Authentication (Future)

```bash
# Include JWT token in Authorization header
curl -X GET http://localhost:8000/api/health \
  -H "Authorization: Bearer your-jwt-token"
```

## Rate Limiting

The API implements intelligent rate limiting with exponential backoff for external model providers.

### Rate Limits

- **OpenAI API**: Respects provider rate limits with exponential backoff
- **Anthropic API**: Token bucket algorithm with jitter
- **Local Operations**: No rate limiting for RAG/database operations

### Rate Limit Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
Retry-After: 30
```

## Server-Sent Events (SSE)

The API uses SSE for real-time streaming of AI responses, thinking states, and progress updates.

### SSE Connection

```bash
curl -N -X POST http://localhost:8000/api/assistant/query \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"mode": "assist", "prompt": "Your query here"}'
```

### SSE Event Types

#### 1. Thinking State Events

```
event: thinking_state
data: {"type": "thinking_state", "label": "Analyzing DIFC regulations", "timestamp": "2023-12-01T10:00:00Z"}
```

#### 2. Text Chunk Events

```
event: chunk
data: {"type": "chunk", "text": "Based on DIFC Law No. 2 of 2019..."}
```

#### 3. Citation Events

```
event: citation
data: {
  "type": "citation",
  "title": "DIFC Employment Law",
  "section": "Article 15",
  "url": "https://difc.ae/laws/employment-law",
  "instrument_type": "Law",
  "jurisdiction": "DIFC"
}
```

#### 4. Stream Done Events

```
event: done
data: {
  "type": "done",
  "final_response": "Complete response text",
  "citations": [...]
}
```

#### 5. Error Events

```
event: error
data: {"type": "error", "message": "Rate limit exceeded", "code": "RATE_LIMIT_EXCEEDED"}
```

### JavaScript SSE Client Example

```javascript
const eventSource = new EventSource('/api/assistant/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    mode: 'assist',
    prompt: 'Explain DIFC employment law basics'
  })
});

eventSource.addEventListener('thinking_state', (event) => {
  const data = JSON.parse(event.data);
  console.log('Thinking:', data.label);
});

eventSource.addEventListener('chunk', (event) => {
  const data = JSON.parse(event.data);
  console.log('Content:', data.text);
});

eventSource.addEventListener('citation', (event) => {
  const data = JSON.parse(event.data);
  console.log('Citation:', data.title);
});

eventSource.addEventListener('done', (event) => {
  const data = JSON.parse(event.data);
  console.log('Complete response:', data.final_response);
  eventSource.close();
});
```

## API Endpoints

### Assistant API

#### Query Assistant

**Endpoint**: `POST /api/assistant/query`  
**Description**: Stream AI assistant responses with thinking states and citations

**Request Body**:
```json
{
  "mode": "assist|draft",
  "prompt": "Your legal query or instruction",
  "knowledge": {
    "jurisdiction": "DIFC|DFSA|UAE|OTHER",
    "sources": ["DIFC_LAWS", "DFSA_RULEBOOK", "DIFC_COURTS_RULES", "VAULT"]
  },
  "vault_project_id": "optional-project-id",
  "attachments": ["file-id-1", "file-id-2"],
  "model_override": "gpt-4.1|o1|claude-3.7-sonnet"
}
```

**Response**: SSE stream with thinking states, chunks, citations, and final response

**Example**:
```bash
curl -N -X POST http://localhost:8000/api/assistant/query \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "assist",
    "prompt": "What are the minimum leave requirements under DIFC employment law?",
    "knowledge": {
      "jurisdiction": "DIFC",
      "sources": ["DIFC_LAWS", "DFSA_RULEBOOK"]
    }
  }'
```

#### Get Assistant History

**Endpoint**: `GET /api/assistant/history`  
**Description**: Retrieve recent assistant interactions

**Query Parameters**:
- `limit` (int, optional): Number of records to return (default: 50)
- `offset` (int, optional): Offset for pagination (default: 0)

**Response**:
```json
{
  "interactions": [
    {
      "id": "interaction-123",
      "mode": "assist",
      "prompt": "Query text",
      "response": "Assistant response",
      "citations": [...],
      "timestamp": "2023-12-01T10:00:00Z"
    }
  ],
  "total": 125,
  "has_more": true
}
```

### Vault API

#### List Projects

**Endpoint**: `GET /api/vault/projects`  
**Description**: List all vault projects for the current user

**Query Parameters**:
- `visibility` (string, optional): Filter by visibility (`private`, `shared`, or `all`)
- `search` (string, optional): Search projects by name
- `limit` (int, optional): Number of projects to return (default: 50)

**Response**:
```json
{
  "projects": [
    {
      "id": "project-123",
      "name": "Contract Review",
      "visibility": "private",
      "document_count": 15,
      "created_at": "2023-12-01T10:00:00Z",
      "updated_at": "2023-12-01T12:00:00Z",
      "owner": "user-456"
    }
  ],
  "total": 25
}
```

#### Create Project

**Endpoint**: `POST /api/vault/projects`  
**Description**: Create a new vault project

**Request Body**:
```json
{
  "name": "Project Name",
  "visibility": "private|shared"
}
```

**Response**:
```json
{
  "id": "project-123",
  "name": "Project Name",
  "visibility": "private",
  "document_count": 0,
  "created_at": "2023-12-01T10:00:00Z",
  "updated_at": "2023-12-01T10:00:00Z",
  "owner": "user-456"
}
```

#### Upload Document

**Endpoint**: `POST /api/vault/projects/{project_id}/upload`  
**Description**: Upload a document to a project

**Request**: Multipart form data
- `file`: Document file (PDF, DOCX, TXT, MD)
- `metadata` (optional): JSON metadata

**Response**:
```json
{
  "id": "doc-456",
  "project_id": "project-123",
  "filename": "contract.pdf",
  "title": "Employment Contract Template",
  "file_path": "/data/files/project-123/contract.pdf",
  "content_type": "application/pdf",
  "size_bytes": 245760,
  "jurisdiction": "DIFC",
  "instrument_type": "Other",
  "upload_date": "2023-12-01T10:00:00Z"
}
```

#### Search Documents

**Endpoint**: `GET /api/vault/projects/{project_id}/search`  
**Description**: Search documents within a project using RAG

**Query Parameters**:
- `q` (string, required): Search query
- `jurisdiction` (string, optional): Filter by jurisdiction
- `instrument_type` (string, optional): Filter by instrument type
- `limit` (int, optional): Number of results (default: 10)

**Response**:
```json
{
  "results": [
    {
      "document": {
        "id": "doc-456",
        "title": "DIFC Employment Law",
        "filename": "employment-law.pdf",
        "metadata": {...}
      },
      "score": 0.85,
      "chunk_index": 2,
      "snippet": "Relevant text snippet with highlighting..."
    }
  ],
  "total": 12
}
```

### Workflows API

#### List Workflows

**Endpoint**: `GET /api/workflows`  
**Description**: List available workflow templates

**Response**:
```json
{
  "workflows": [
    {
      "id": "draft-from-template",
      "name": "Draft from Template (DIFC)",
      "description": "Generate legal documents from DIFC-compliant templates",
      "category": "transactional",
      "steps": 6,
      "estimated_duration": "5-10 minutes"
    }
  ]
}
```

#### Execute Workflow

**Endpoint**: `POST /api/workflows/{workflow_id}/execute`  
**Description**: Execute a workflow with SSE streaming

**Request Body** (for draft-from-template):
```json
{
  "prompt": "Draft an employment contract for senior developer",
  "template_doc_id": "template-123",
  "reference_doc_ids": ["ref-456", "ref-789"],
  "jurisdiction": "DIFC",
  "tone": "formal|conversational",
  "instructions": "Include remote work provisions",
  "track_changes": true,
  "model_override": "gpt-4.1"
}
```

**Response**: SSE stream with workflow progress, thinking states, and final artifacts

**SSE Event Types**:
```
event: workflow_start
data: {"workflow_id": "execution-123", "steps": 6}

event: workflow_progress
data: {"step": 2, "step_name": "Document Retrieval", "progress": 33}

event: thinking_state
data: {"label": "Analyzing template structure", "step": "planning"}

event: workflow_complete
data: {
  "artifacts": {
    "draft": "Generated document content...",
    "tracked_changes": "Change log...",
    "citations": [...]
  },
  "duration": 420
}
```

#### Get Workflow Status

**Endpoint**: `GET /api/workflows/executions/{execution_id}`  
**Description**: Get the status of a workflow execution

**Response**:
```json
{
  "id": "execution-123",
  "workflow_id": "draft-from-template",
  "status": "running|completed|failed",
  "progress": 66,
  "current_step": "Document Review",
  "started_at": "2023-12-01T10:00:00Z",
  "completed_at": null,
  "artifacts": {...}
}
```

### Ingestion API

#### Ingest Documents

**Endpoint**: `POST /api/ingest/documents`  
**Description**: Ingest documents into the RAG system

**Request**: Multipart form data
- `files`: Multiple document files
- `jurisdiction` (optional): Default jurisdiction for all files
- `extract_metadata` (optional): Whether to extract metadata automatically

**Response**:
```json
{
  "ingested": [
    {
      "filename": "difc-law-2019.pdf",
      "document_id": "doc-789",
      "chunks_created": 45,
      "metadata_extracted": true
    }
  ],
  "failed": [],
  "total_chunks": 45
}
```

#### Get Ingestion Status

**Endpoint**: `GET /api/ingest/status/{job_id}`  
**Description**: Get the status of a document ingestion job

**Response**:
```json
{
  "job_id": "job-123",
  "status": "processing|completed|failed",
  "progress": 75,
  "documents_processed": 8,
  "total_documents": 10,
  "errors": []
}
```

## Data Models

### Core Enums

```python
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
```

### Request Models

#### AssistantQuery

```json
{
  "mode": "assist|draft",
  "prompt": "string (required, min_length=1)",
  "knowledge": {
    "jurisdiction": "DIFC|DFSA|UAE|OTHER",
    "sources": ["DIFC_LAWS", "DFSA_RULEBOOK", "DIFC_COURTS_RULES", "VAULT"]
  },
  "vault_project_id": "string (optional)",
  "attachments": ["string array (optional)"],
  "model_override": "string (optional)"
}
```

#### VaultProject

```json
{
  "name": "string (required)",
  "visibility": "private|shared (default: private)"
}
```

#### WorkflowExecution

```json
{
  "prompt": "string (required)",
  "template_doc_id": "string (optional)",
  "reference_doc_ids": ["string array (optional)"],
  "jurisdiction": "DIFC|DFSA|UAE|OTHER",
  "tone": "formal|conversational (optional)",
  "instructions": "string (optional)",
  "track_changes": "boolean (default: false)",
  "model_override": "string (optional)"
}
```

### Response Models

#### Citation

```json
{
  "type": "citation",
  "title": "string",
  "section": "string (optional)",
  "url": "string (optional)",
  "instrument_type": "Law|Regulation|CourtRule|Rulebook|Notice|Other",
  "jurisdiction": "DIFC|DFSA|UAE|OTHER"
}
```

#### DocumentMetadata

```json
{
  "id": "string",
  "project_id": "string",
  "filename": "string",
  "title": "string",
  "file_path": "string",
  "content_type": "string",
  "size_bytes": "integer",
  "jurisdiction": "DIFC|DFSA|UAE|OTHER",
  "instrument_type": "Law|Regulation|CourtRule|Rulebook|Notice|Other",
  "upload_date": "datetime"
}
```

## Error Handling

### HTTP Status Codes

- **200 OK**: Successful request
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **409 Conflict**: Resource conflict
- **422 Unprocessable Entity**: Validation error
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: External service unavailable

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data",
    "details": {
      "field": "prompt",
      "issue": "Field required"
    },
    "timestamp": "2023-12-01T10:00:00Z"
  }
}
```

### Common Error Codes

- `VALIDATION_ERROR`: Request validation failed
- `AUTHENTICATION_REQUIRED`: Missing or invalid authentication
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `MODEL_UNAVAILABLE`: AI model service unavailable
- `DOCUMENT_NOT_FOUND`: Requested document not found
- `PROJECT_NOT_FOUND`: Vault project not found
- `WORKFLOW_FAILED`: Workflow execution failed
- `INGESTION_FAILED`: Document ingestion failed

### SSE Error Handling

SSE streams can send error events:

```
event: error
data: {
  "type": "error",
  "code": "MODEL_TIMEOUT",
  "message": "AI model request timed out",
  "recoverable": true
}
```

## Examples

### Complete Assistant Query with Citations

```bash
curl -N -X POST http://localhost:8000/api/assistant/query \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "assist",
    "prompt": "What are the requirements for terminating an employee in DIFC? Include notice periods and severance pay.",
    "knowledge": {
      "jurisdiction": "DIFC",
      "sources": ["DIFC_LAWS", "DIFC_COURTS_RULES"]
    }
  }'
```

### Create Project and Upload Document

```bash
# Create project
PROJECT_ID=$(curl -X POST http://localhost:8000/api/vault/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Employment Contracts", "visibility": "private"}' \
  | jq -r '.id')

# Upload document
curl -X POST http://localhost:8000/api/vault/projects/${PROJECT_ID}/upload \
  -F "file=@employment-contract.pdf" \
  -F 'metadata={"jurisdiction": "DIFC", "instrument_type": "Other"}'
```

### Execute Workflow with Progress Tracking

```bash
curl -N -X POST http://localhost:8000/api/workflows/draft-from-template/execute \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Draft a software developer employment contract with remote work provisions",
    "jurisdiction": "DIFC",
    "tone": "formal",
    "instructions": "Include intellectual property clauses and confidentiality terms",
    "track_changes": true
  }'
```

### Search Vault Documents

```bash
curl -X GET "http://localhost:8000/api/vault/projects/${PROJECT_ID}/search?q=termination%20notice&jurisdiction=DIFC&limit=5" \
  -H "Accept: application/json"
```

### Batch Document Ingestion

```bash
curl -X POST http://localhost:8000/api/ingest/documents \
  -F "files=@difc-employment-law.pdf" \
  -F "files=@difc-company-law.pdf" \
  -F "files=@dfsa-rulebook.pdf" \
  -F "jurisdiction=DIFC" \
  -F "extract_metadata=true"
```

## Rate Limiting and Best Practices

### Rate Limiting Strategy

1. **Respect Provider Limits**: Built-in handling for OpenAI and Anthropic rate limits
2. **Exponential Backoff**: Automatic retry with increasing delays
3. **Circuit Breaker**: Temporary service disable on repeated failures
4. **Queue Management**: Request queuing during high load

### Best Practices

1. **Use SSE for Long Operations**: Always use SSE for assistant queries and workflows
2. **Handle Disconnections**: Implement proper SSE reconnection logic
3. **Batch Operations**: Use batch endpoints for multiple document operations
4. **Cache Responses**: Cache non-streaming responses when appropriate
5. **Monitor Rate Limits**: Check rate limit headers and implement client-side limiting
6. **Validate Input**: Always validate request data before sending
7. **Handle Errors Gracefully**: Implement proper error handling and user feedback

### Performance Recommendations

- **Concurrent Requests**: Limit to 5 concurrent streaming requests per client
- **File Upload Size**: Maximum 50MB per file
- **Query Length**: Keep prompts under 4000 characters for optimal performance
- **Citation Threshold**: Use default 0.25 threshold for citation verification
- **Embedding Models**: Prefer sentence-transformers for speed, OpenAI for accuracy

## Security Considerations

1. **Input Validation**: All inputs are validated against schemas
2. **File Type Validation**: Only approved file types allowed for upload
3. **Path Traversal Protection**: File paths are sanitized
4. **Content Scanning**: Uploaded files scanned for malicious content
5. **Rate Limiting**: Prevents abuse and DoS attacks
6. **CORS Configuration**: Properly configured for browser clients
7. **API Key Security**: Secure handling of external API keys

## Support and Documentation

- **OpenAPI Spec**: Available at `/docs` (Swagger UI)
- **ReDoc**: Available at `/redoc` (alternative documentation)
- **Health Check**: GET `/health` for service status
- **Metrics**: GET `/metrics` for Prometheus metrics
- **Version**: GET `/version` for API version information

For additional support and examples, see the main project documentation and examples in the `/examples` directory.