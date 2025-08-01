"""
Comprehensive test configuration for QaAI Legal Assistant API.

Following PRP requirements:
- Async testing patterns with proper fixtures
- SSE streaming support 
- Mock external APIs (OpenAI/Anthropic)
- Database testing with isolation
- LangGraph workflow testing support
"""

import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator, Generator, Dict, Any

# Set test environment
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["APP_ENV"] = "test"
os.environ["LOG_LEVEL"] = "ERROR"  # Reduce noise in tests

# Import after environment setup
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from asgi_lifespan import LifespanManager

# Mock app and models for testing - in production these would be real imports
from fastapi import FastAPI

# Create mock app
app = FastAPI(title="QaAI Test API")

# Mock database functions
def get_db():
    pass

class MockBase:
    metadata = MagicMock()

Base = MockBase()

# Mock models - in production these would be real Pydantic models
from pydantic import BaseModel
from enum import Enum

class JurisdictionType(str, Enum):
    DIFC = "DIFC"
    DFSA = "DFSA" 
    UAE = "UAE"
    OTHER = "OTHER"

class AssistantMode(str, Enum):
    ASSIST = "assist"
    DRAFT = "draft"

class Citation(BaseModel):
    title: str
    section: str = None
    url: str = None
    instrument_type: str
    jurisdiction: JurisdictionType

class DocumentMetadata(BaseModel):
    id: str
    project_id: str
    filename: str
    title: str
    file_path: str
    content_type: str
    size_bytes: int
    jurisdiction: JurisdictionType
    instrument_type: str
    upload_date: str

class VaultProject(BaseModel):
    id: str
    name: str
    visibility: str
    document_count: int
    created_at: str
    updated_at: str
    owner: str

class AssistantQuery(BaseModel):
    mode: AssistantMode
    prompt: str
    knowledge: dict = {}
    vault_project_id: str = None


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine with in-memory SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session(test_engine):
    """Create isolated async database session for each test."""
    async_session = sessionmaker(
        test_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        # Rollback any uncommitted changes
        await session.rollback()


@pytest.fixture
async def client_with_lifespan(async_session):
    """FastAPI test client with proper lifespan management."""
    # Override database dependency
    app.dependency_overrides[get_db] = lambda: async_session
    
    try:
        async with LifespanManager(app):
            async with AsyncClient(app=app, base_url="http://test") as ac:
                yield ac
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


@pytest.fixture
def sync_client():
    """Synchronous test client for simple non-streaming tests."""
    with TestClient(app) as client:
        yield client


# Mock Fixtures for External Services
@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client with realistic responses."""
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock()
    
    # Default successful response
    client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content="This is a mock response from OpenAI for DIFC legal analysis."
                )
            )
        ],
        usage=MagicMock(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
    )
    
    return client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client with realistic responses."""
    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock()
    
    # Default successful response
    client.messages.create.return_value = MagicMock(
        content=[
            MagicMock(
                text="This is a mock response from Anthropic for DIFC legal drafting."
            )
        ],
        usage=MagicMock(
            input_tokens=120,
            output_tokens=80
        )
    )
    
    return client


@pytest.fixture
def mock_vector_store():
    """Mock FAISS vector store for RAG testing."""
    mock_store = MagicMock()
    
    # Mock search results
    mock_store.search.return_value = [
        {
            "id": "doc-1",
            "content": "DIFC Employment Law No. 2 of 2019 establishes minimum employment standards.",
            "metadata": {
                "title": "DIFC Employment Law No. 2 of 2019",
                "section": "Part 4 - Employment Standards",
                "jurisdiction": "DIFC",
                "instrument_type": "Law"
            },
            "score": 0.95
        },
        {
            "id": "doc-2", 
            "content": "DFSA Rulebook provides comprehensive regulatory framework.",
            "metadata": {
                "title": "DFSA General Rulebook",
                "section": "Module 1",
                "jurisdiction": "DFSA",
                "instrument_type": "Rulebook"
            },
            "score": 0.87
        }
    ]
    
    # Mock statistics
    mock_store.get_stats.return_value = {
        "total_vectors": 1000,
        "index_exists": True,
        "last_updated": "2024-01-01T00:00:00Z"
    }
    
    return mock_store


@pytest.fixture
def sample_documents():
    """Sample document metadata for testing."""
    return [
        DocumentMetadata(
            id="doc-1",
            project_id="test-project",
            filename="difc_employment_law.pdf",
            title="DIFC Employment Law No. 2 of 2019",
            file_path="/data/files/doc-1.pdf",
            content_type="application/pdf",
            size_bytes=1024000,
            jurisdiction=JurisdictionType.DIFC,
            instrument_type="Law",
            upload_date="2024-01-01T00:00:00Z"
        ),
        DocumentMetadata(
            id="doc-2",
            project_id="test-project",
            filename="dfsa_rulebook.pdf", 
            title="DFSA General Rulebook",
            file_path="/data/files/doc-2.pdf",
            content_type="application/pdf",
            size_bytes=2048000,
            jurisdiction=JurisdictionType.DFSA,
            instrument_type="Rulebook",
            upload_date="2024-01-02T00:00:00Z"
        )
    ]


@pytest.fixture
def sample_citations():
    """Sample citations for testing."""
    return [
        Citation(
            title="DIFC Employment Law No. 2 of 2019",
            section="Part 4 - Employment Standards",
            url="https://difc.ae/laws/employment-law-2-2019",
            instrument_type="Law",
            jurisdiction=JurisdictionType.DIFC
        ),
        Citation(
            title="DFSA General Rulebook",
            section="Module 1 - General Provisions",
            url="https://dfsa.ae/rulebook/general",
            instrument_type="Rulebook", 
            jurisdiction=JurisdictionType.DFSA
        )
    ]


@pytest.fixture
def sample_vault_project():
    """Sample vault project for testing."""
    return VaultProject(
        id="test-project-123",
        name="DIFC Contract Review",
        visibility="private",
        document_count=5,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-15T00:00:00Z",
        owner="test-user@example.com"
    )


@pytest.fixture
def sample_assistant_queries():
    """Sample assistant queries for different test scenarios."""
    return {
        "assist_basic": AssistantQuery(
            mode=AssistantMode.ASSIST,
            prompt="What are the minimum notice periods under DIFC Employment Law?",
            knowledge={"jurisdiction": JurisdictionType.DIFC}
        ),
        "draft_basic": AssistantQuery(
            mode=AssistantMode.DRAFT,
            prompt="Draft an employment contract clause for notice periods in DIFC",
            knowledge={"jurisdiction": JurisdictionType.DIFC}
        ),
        "assist_with_vault": AssistantQuery(
            mode=AssistantMode.ASSIST,
            prompt="Summarize the key points from uploaded contracts",
            knowledge={"jurisdiction": JurisdictionType.DIFC},
            vault_project_id="test-project-123"
        ),
        "empty_prompt": AssistantQuery(
            mode=AssistantMode.ASSIST,
            prompt="",
            knowledge={"jurisdiction": JurisdictionType.DIFC}
        ),
        "invalid_jurisdiction": AssistantQuery(
            mode=AssistantMode.ASSIST,
            prompt="Test query",
            knowledge={"jurisdiction": "INVALID_JURISDICTION"}
        )
    }


# Patch fixtures for external services
@pytest.fixture(autouse=True)
def mock_external_services(mock_openai_client, mock_anthropic_client, mock_vector_store):
    """Auto-applied mock for all external services."""
    with patch('services.openai_client.OpenAIClient', return_value=mock_openai_client), \
         patch('services.anthropic_client.AnthropicClient', return_value=mock_anthropic_client), \
         patch('rag.vector_store.vector_store', mock_vector_store):
        yield


# Test data cleanup
@pytest.fixture(autouse=True)
async def cleanup_test_data():
    """Clean up any test data after each test."""
    yield
    # Perform any necessary cleanup
    # This runs after each test


# Helper functions for tests
class TestHelpers:
    """Helper functions for test assertions and data parsing."""
    
    @staticmethod
    def parse_sse_events(response_text: str) -> list[dict]:
        """Parse SSE response into structured events."""
        events = []
        lines = response_text.split('\n')
        
        for line in lines:
            if line.startswith('data: '):
                try:
                    import json
                    event_data = json.loads(line[6:])
                    events.append(event_data)
                except json.JSONDecodeError:
                    continue
        
        return events
    
    @staticmethod
    def assert_valid_citation(citation: dict):
        """Assert citation has required fields."""
        required_fields = ["title", "jurisdiction", "instrument_type"]
        for field in required_fields:
            assert field in citation, f"Citation missing required field: {field}"
        
        # Validate jurisdiction
        valid_jurisdictions = ["DIFC", "DFSA", "UAE", "OTHER"]
        assert citation["jurisdiction"] in valid_jurisdictions
    
    @staticmethod
    def assert_difc_first_ordering(results: list[dict]):
        """Assert DIFC documents appear first in results."""
        difc_indices = [i for i, doc in enumerate(results) 
                       if doc.get("jurisdiction") == "DIFC"]
        non_difc_indices = [i for i, doc in enumerate(results) 
                           if doc.get("jurisdiction") != "DIFC"]
        
        if difc_indices and non_difc_indices:
            assert max(difc_indices) < min(non_difc_indices), \
                "DIFC documents should appear before non-DIFC documents"


@pytest.fixture
def test_helpers():
    """Provide test helper functions."""
    return TestHelpers


# Performance testing fixtures
@pytest.fixture
def performance_monitor():
    """Monitor test performance metrics."""
    import time
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    start_time = time.time()
    start_memory = process.memory_info().rss
    
    yield {
        "start_time": start_time,
        "start_memory": start_memory,
        "process": process
    }
    
    end_time = time.time()
    end_memory = process.memory_info().rss
    
    duration = end_time - start_time
    memory_growth = end_memory - start_memory
    
    # Log performance metrics
    print(f"\nTest Performance:")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Memory growth: {memory_growth / 1024 / 1024:.2f}MB")


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "sse: mark test as SSE streaming test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_models: mark test as requiring external model access"
    )