# QaAI Legal Assistant System

A comprehensive Harvey-style, DIFC-focused legal AI demo system with React frontend, FastAPI backend, LangGraph orchestration, and comprehensive RAG capabilities.

> **A production-ready legal AI assistant for DIFC jurisdiction with visible thinking states and streaming responses.**

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd QaAI-DIFC-Main

# 2. Set up Python virtual environment
python3 -m venv venv_linux
source venv_linux/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration

# 5. Initialize database and vector store
python -m apps.api.scripts.init_db
python -m apps.api.scripts.ingest_corpus examples/sample_corpus/

# 6. Start the backend
cd apps/api
python -m uvicorn main:app --reload --port 8000

# 7. Install frontend dependencies (in a new terminal)
cd apps/web
npm install

# 8. Start the frontend
npm run dev

# 9. Open http://localhost:3000 to access the application
```

## 📚 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [DIFC Corpus Setup](#difc-corpus-setup)
- [Sharing for Internal Testing](#sharing-for-internal-testing)
- [Development](#development)

## 🔗 Sharing for Internal Testing

Need to share the app with your team for testing? Here are two easy options:

### Option 1: Public Internet Access (Recommended)

Uses ngrok to create a secure tunnel accessible from anywhere:

```bash
# Install ngrok first
brew install ngrok  # macOS
# or snap install ngrok  # Linux
# or download from https://ngrok.com/download

# Run the sharing script
./scripts/share-local.sh
```

This will:
- Start both API and web servers
- Create a public HTTPS URL (e.g., `https://abc123.ngrok.io`)
- Allow anyone with the URL to test the app
- Keep running until you press Ctrl+C

### Option 2: Local Network Access

Share with team members on the same WiFi network:

```bash
./scripts/run-local-network.sh
```

This will:
- Start servers accessible on your local network
- Show URLs like `http://192.168.1.100:5173`
- Allow team members on same WiFi to access the app
- More secure (local network only)

### Manual Setup

If you prefer to run servers manually:

```bash
# Terminal 1: Start API
source venv_linux/bin/activate
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start Web App  
cd apps/web
npm run dev -- --host 0.0.0.0 --port 5173
```

Then share the appropriate URL with your team.

## 💻 Development

## Features

### Core Capabilities
- **Harvey-style Legal AI**: Comprehensive legal assistance specifically tailored for DIFC jurisdiction
- **Three Primary Interfaces**: Assistant (Assist/Draft modes), Vault (document management), Workflows (agentic processes)
- **Real-time Streaming**: Server-Sent Events (SSE) for visible thinking states and progressive responses
- **DIFC-First Architecture**: Prioritizes DIFC Laws, Regulations, Court Rules, and DFSA Rulebook in all operations
- **Multi-Model Support**: OpenAI (GPT-4.1, o1, o3) and Anthropic (Claude-3.7-Sonnet) with intelligent routing
- **Citation Verification**: Binary match validation with Jaccard similarity for accurate legal references

### Technical Features
- **LangGraph Orchestration**: Deterministic, inspectable workflow graphs for complex legal processes
- **Hybrid RAG System**: FAISS vector search combined with BM25 for optimal retrieval accuracy
- **Async Architecture**: FastAPI backend with async SQLite and proper session management
- **Design System Integration**: JSON-driven design profiles ensuring consistent UI/UX
- **Comprehensive Testing**: 100+ test scenarios covering API endpoints, workflows, and RAG systems

## Architecture

```
qaai-system/
├── .env.example                       # Environment variables template
├── requirements.txt                   # Python dependencies
├── venv_linux/                        # Virtual environment (use for all commands)
├── apps/
│   ├── api/                           # FastAPI backend
│   │   ├── main.py                    # FastAPI app with SSE endpoints
│   │   ├── agents/                    # LangGraph agents and orchestration
│   │   │   ├── graph.py               # LangGraph composition
│   │   │   ├── nodes.py               # Node implementations
│   │   │   ├── prompts.py             # DIFC-focused system prompts
│   │   │   └── router.py              # Model selection per step
│   │   ├── api/                       # API route definitions
│   │   │   ├── assistant.py           # Assistant endpoints (SSE streaming)
│   │   │   ├── vault.py               # Vault project management
│   │   │   ├── workflows.py           # Workflow execution
│   │   │   └── ingest.py              # Document ingestion
│   │   ├── core/                      # Core business logic
│   │   │   ├── config.py              # Settings and environment
│   │   │   ├── models.py              # Pydantic models
│   │   │   ├── database.py            # Async SQLite management
│   │   │   └── storage.py             # File system storage
│   │   ├── rag/                       # RAG implementation
│   │   │   ├── vector_store.py        # FAISS vector operations
│   │   │   ├── retrievers.py          # DIFC-first retrieval logic
│   │   │   ├── embeddings.py          # Embedding generation
│   │   │   └── citations.py           # Citation verification
│   │   ├── services/                  # External service integrations
│   │   │   ├── openai_client.py       # OpenAI API client
│   │   │   └── anthropic_client.py    # Anthropic API client
│   │   └── tests/                     # Comprehensive test suite
│   └── web/                           # React frontend
│       ├── package.json               # Node.js dependencies
│       ├── tailwind.config.js         # Tailwind v4 configuration
│       ├── src/
│       │   ├── components/            # UI components (shadcn/ui)
│       │   │   ├── assistant/         # Assistant interface
│       │   │   ├── vault/             # Document management
│       │   │   └── workflows/         # Workflow execution
│       │   ├── hooks/                 # React hooks for API and state
│       │   ├── services/              # API client and SSE handling
│       │   └── types/                 # TypeScript definitions
├── data/                              # Local storage
│   ├── files/                         # Uploaded documents
│   ├── index/                         # FAISS index files
│   └── qaai.db                        # SQLite database
├── examples/                          # Implementation patterns and samples
│   ├── design/                        # UI design profiles (single source of truth)
│   └── sample_corpus/                 # Sample DIFC documents
└── docs/                              # Documentation
    └── API.md                         # Complete API documentation
```

## Requirements

### System Requirements
- **Python**: 3.8+ (tested with Python 3.9-3.11)
- **Node.js**: 16+ (tested with Node.js 18-20)
- **Memory**: 4GB+ RAM (8GB+ recommended for FAISS operations)
- **Storage**: 5GB+ free space (for vector indices and documents)

### API Keys Required
- **OpenAI API Key**: For GPT-4.1, o1, and o3 models
- **Anthropic API Key**: For Claude-3.7-Sonnet model
- **Optional**: Sentence Transformers for local embeddings (no API key needed)

## Installation

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd QaAI-DIFC-Main

# Create and activate virtual environment
python3 -m venv venv_linux
source venv_linux/bin/activate  # On Windows: venv_linux\Scripts\activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd apps/web

# Install Node.js dependencies
npm install

# Return to project root
cd ../..
```

### 3. Database Initialization

```bash
# Ensure virtual environment is activated
source venv_linux/bin/activate

# Create data directories
mkdir -p data/files data/index

# Initialize SQLite database
python -c "
from apps.api.core.database import init_db
import asyncio
asyncio.run(init_db())
print('Database initialized successfully')
"
```

## Configuration

### Environment Variables

Copy the `.env.example` file to create your environment configuration:

```bash
cp .env.example .env
```

Edit `.env` with your specific configuration:

```bash
# Model Providers
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=claude-your-anthropic-key-here

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
APP_ENV=development
LOG_LEVEL=INFO
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```

### Model Configuration

The system supports multiple AI models with intelligent routing:

- **Planner Model** (default: o1): For complex reasoning and workflow planning
- **Drafter Model** (default: gpt-4.1): For document drafting and content generation
- **Verifier Model** (default: claude-3.7-sonnet): For long-context verification and citation checking

## DIFC Corpus Setup

### Sample Corpus

The system includes sample DIFC documents in `examples/sample_corpus/`. To set up the full corpus:

```bash
# Ensure virtual environment is activated
source venv_linux/bin/activate

# Ingest sample corpus
python examples/rag_ingest.py examples/sample_corpus/

# Verify ingestion
python -c "
from apps.api.rag.vector_store import VectorStore
vs = VectorStore()
count = vs.get_document_count()
print(f'Ingested {count} documents successfully')
"
```

### Adding Your Own Documents

1. **Supported Formats**: PDF, DOCX, TXT, MD
2. **Document Structure**: Follow DIFC legal document conventions
3. **Metadata Requirements**: Include jurisdiction, instrument type, and effective dates

```bash
# Add documents to a directory
mkdir -p my_difc_documents/
# Copy your documents to this directory

# Ingest new documents
python examples/rag_ingest.py my_difc_documents/
```

### Document Metadata Schema

Each document should include metadata for optimal retrieval:

```json
{
  "jurisdiction": "DIFC",
  "instrument_type": "Law|Regulation|CourtRule|Rulebook|Notice",
  "title": "Document Title",
  "effective_date": "2023-01-01",
  "section_references": ["Section 1", "Article 2"]
}
```

## Development

### Running the Application

#### Backend (FastAPI)

```bash
# Ensure virtual environment is activated
source venv_linux/bin/activate

# Navigate to API directory
cd apps/api

# Start development server with hot reload
python -m uvicorn main:app --reload --port 8000

# API will be available at: http://localhost:8000
# Interactive docs at: http://localhost:8000/docs
```

#### Frontend (React)

```bash
# In a new terminal, navigate to web directory
cd apps/web

# Start development server
npm run dev

# Frontend will be available at: http://localhost:3000
```

### Development Commands

```bash
# Backend linting and formatting
cd apps/api && source ../../venv_linux/bin/activate
ruff check . --fix              # Auto-fix style issues
black . --check                 # Code formatting validation
mypy . --ignore-missing-imports # Type checking

# Frontend linting and building
cd apps/web
npm run lint                    # ESLint validation
npm run type-check              # TypeScript validation
npm run build                   # Production build
```

### Key Development Files

- **CLAUDE.md**: Project-wide development rules and conventions
- **TASK.md**: Current task progress and planning
- **examples/design/**: UI design profiles (single source of truth for styling)
- **examples/**: Code patterns and implementation examples

## API Documentation

See [docs/API.md](docs/API.md) for comprehensive API documentation including:

- Authentication and rate limiting
- SSE streaming event formats
- Complete endpoint reference
- Error handling and response codes
- WebSocket integration patterns

### Quick API Reference

#### Assistant API
```bash
# Stream Assistant response
curl -N -X POST http://localhost:8000/api/assistant/query \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "assist",
    "prompt": "Explain DIFC Employment Law basics",
    "knowledge": {"jurisdiction": "DIFC"}
  }'
```

#### Vault API
```bash
# Create project
curl -X POST http://localhost:8000/api/vault/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Contract Review", "visibility": "private"}'

# Upload document
curl -X POST http://localhost:8000/api/vault/projects/{project_id}/upload \
  -F "file=@contract.pdf"
```

#### Workflows API
```bash
# Execute workflow
curl -N -X POST http://localhost:8000/api/workflows/draft-from-template \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Draft employment contract",
    "jurisdiction": "DIFC",
    "template_doc_id": "template-123"
  }'
```

## Testing

### Backend Testing

The system includes comprehensive test coverage:

```bash
# Ensure virtual environment is activated
source venv_linux/bin/activate

# Run all tests
cd apps/api && pytest tests/ -v

# Run specific test categories
pytest tests/test_api/ -v --cov=api           # API endpoint tests
pytest tests/test_agents/ -v --cov=agents    # LangGraph workflow tests
pytest tests/test_rag/ -v --cov=rag          # RAG system tests

# Run tests with coverage report
pytest tests/ -v --cov=. --cov-report=html
```

### Test Categories

1. **API Tests** (`tests/test_api/`): FastAPI endpoints, SSE streaming, error handling
2. **Agent Tests** (`tests/test_agents/`): LangGraph workflows, thinking states, model routing
3. **RAG Tests** (`tests/test_rag/`): Vector operations, DIFC-first retrieval, citation verification
4. **Integration Tests**: End-to-end workflows combining multiple components

### Frontend Testing

```bash
cd apps/web

# Run unit tests
npm test

# Run tests with coverage
npm run test:coverage

# Run end-to-end tests (requires running backend)
npm run test:e2e
```

## Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Run in production mode
docker-compose -f docker-compose.prod.yml up -d
```

### Manual Production Deployment

```bash
# Backend deployment
source venv_linux/bin/activate
cd apps/api
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Frontend deployment
cd apps/web
npm run build
# Serve dist/ with your preferred web server (nginx, apache, etc.)
```

### Environment-Specific Configuration

- **Development**: Uses SQLite, local file storage, debug logging
- **Production**: Supports PostgreSQL, cloud storage, structured logging
- **Testing**: Uses in-memory databases, mock external services

## Troubleshooting

### Common Issues

1. **FAISS Installation**: If FAISS installation fails, try `pip install faiss-cpu`
2. **Vector Store Errors**: Ensure `data/index/` directory exists and is writable
3. **API Key Issues**: Verify API keys in `.env` file have correct prefixes
4. **Port Conflicts**: Backend runs on :8000, frontend on :3000 by default

### Performance Optimization

- **Memory Usage**: FAISS indices are loaded into memory; 8GB+ RAM recommended
- **Query Speed**: Hybrid retrieval (BM25 + FAISS) optimizes for both speed and accuracy
- **Rate Limiting**: Built-in exponential backoff for API providers

### Support

- **Documentation**: Check `docs/` directory for detailed guides
- **Examples**: Review `examples/` for implementation patterns
- **Issues**: Report bugs and feature requests via project issues
- **Development**: See `CLAUDE.md` for development guidelines