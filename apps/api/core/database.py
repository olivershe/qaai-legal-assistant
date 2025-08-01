"""
Async SQLite database management for QaAI.

Following 2025 best practices:
- Use aiosqlite driver for async operations
- Proper session management with dependency injection
- expire_on_commit=False for async sessions
- Prevent sync/async mixing as specified in gotchas
"""

from __future__ import annotations
import sqlite3
import aiosqlite
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.sql import func

from .config import settings

# SQLAlchemy Base
Base = declarative_base()


class Document(Base):
    """Document metadata table."""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    path = Column(String, nullable=False)
    jurisdiction = Column(String, nullable=False)
    instrument_type = Column(String, nullable=False)
    url = Column(String, nullable=True)
    enactment_date = Column(String, nullable=True)
    commencement_date = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())


class VaultProject(Base):
    """Vault project table."""
    __tablename__ = "vault_projects"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    visibility = Column(String, default="private")
    document_count = Column(Integer, default=0)
    owner = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Chunk(Base):
    """Document chunk table for RAG."""
    __tablename__ = "chunks"
    
    id = Column(String, primary_key=True)
    doc_id = Column(String, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    section_ref = Column(String, nullable=True)


# Async engine and session factory
engine = create_async_engine(
    settings.db_url,
    echo=settings.app_env == "dev",  # Log SQL in development
    future=True
)

# Session factory with expire_on_commit=False for async compatibility
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Critical for async operations
    autocommit=False,
    autoflush=False
)


async def init_database():
    """
    Initialize database tables.
    
    Creates all tables if they don't exist. Safe for repeated calls.
    """
    # Ensure database directory exists
    db_path = settings.database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection for database sessions.
    
    Provides clean session management with proper cleanup.
    Use this in FastAPI route dependencies.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.
    
    Use this for direct database operations outside of FastAPI routes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def health_check() -> bool:
    """
    Check database connectivity.
    
    Returns True if database is accessible, False otherwise.
    Following production best practices from research.
    """
    try:
        async with get_db_session() as session:
            # Simple query to test connection
            result = await session.execute("SELECT 1")
            return bool(result.scalar())
    except Exception:
        return False


# Raw SQLite operations for specific use cases
class SQLiteManager:
    """
    Direct SQLite operations for cases requiring raw SQL.
    
    Use sparingly - prefer SQLAlchemy for most operations.
    """
    
    @staticmethod
    async def execute_raw(query: str, params: Optional[tuple] = None) -> list:
        """Execute raw SQL query with parameters."""
        db_path = settings.database_path
        
        async with aiosqlite.connect(db_path) as conn:
            cursor = await conn.execute(query, params or ())
            results = await cursor.fetchall()
            await conn.commit()
            return results
    
    @staticmethod
    async def backup_database(backup_path: Path) -> bool:
        """Create database backup."""
        try:
            db_path = settings.database_path
            
            async with aiosqlite.connect(db_path) as source:
                async with aiosqlite.connect(backup_path) as backup:
                    await source.backup(backup)
            return True
        except Exception:
            return False


# Database migration utilities
async def migrate_database():
    """
    Handle database migrations.
    
    Placeholder for future migration logic.
    Currently just ensures tables exist.
    """
    await init_database()


# Cleanup function for application shutdown
async def close_database():
    """Clean shutdown of database connections."""
    await engine.dispose()