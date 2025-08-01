"""
FastAPI main application for QaAI.

Following PRP requirements:
- Async patterns with proper CORS
- Lifespan events for database initialization  
- Proper error handling and logging
- SSE endpoint support
"""

from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from core.config import settings
from core.database import init_database, close_database, health_check
from api.assistant import router as assistant_router
from api.vault import router as vault_router  
from api.workflows import router as workflows_router
from api.ingest import router as ingest_router
from agents.router import model_router
from rag.vector_store import vector_store


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan management.
    
    Handles startup and shutdown events for database and services.
    """
    # Startup
    logger.info("Starting QaAI application")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized")
        
        # Validate model availability
        validation = model_router.validate_model_availability()
        if not validation["valid"]:
            logger.warning(f"Model availability issues: {validation['issues']}")
        else:
            logger.info(f"Models available: {validation['available_count']}/{validation['total_count']}")
        
        # Check vector store
        vector_stats = vector_store.get_stats()
        logger.info(f"Vector store status: {vector_stats}")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down QaAI application")
    try:
        await close_database()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Create FastAPI application
app = FastAPI(
    title="QaAI - DIFC Legal Assistant API",
    description="Harvey-style legal AI assistant with DIFC focus",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env == "dev" else None,
    redoc_url="/redoc" if settings.app_env == "dev" else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "dev" else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check_endpoint():
    """Comprehensive health check for all services."""
    try:
        # Database health
        db_healthy = await health_check()
        
        # Model router health
        model_validation = model_router.validate_model_availability()
        
        # Vector store health
        vector_stats = vector_store.get_stats()
        
        return {
            "status": "healthy" if db_healthy and model_validation["valid"] else "degraded",
            "database": {"healthy": db_healthy},
            "models": {
                "healthy": model_validation["valid"],
                "available": model_validation["available_count"],
                "issues": model_validation.get("issues", [])
            },
            "vector_store": {
                "healthy": vector_stats.get("index_exists", False),
                "total_vectors": vector_stats.get("total_vectors", 0)
            },
            "environment": settings.app_env,
            "jurisdiction_focus": settings.default_jurisdiction
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# API status endpoint
@app.get("/api/status")
async def api_status():
    """Get detailed API status and configuration."""
    try:
        return {
            "api_version": "1.0.0",
            "environment": settings.app_env,
            "features": {
                "assistant_modes": ["assist", "draft"],
                "supported_jurisdictions": ["DIFC", "DFSA", "UAE", "OTHER"],
                "workflow_types": ["draft-from-template"],
                "sse_streaming": True,
                "citation_verification": True
            },
            "model_routing": model_router.get_routing_status(),
            "vector_store": vector_store.get_stats(),
            "rate_limits": {
                "openai": "50 requests/minute",
                "anthropic": "Variable by model",
                "note": "Actual limits depend on API tier"
            }
        }
        
    except Exception as e:
        logger.error(f"Status endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Include API routers
app.include_router(assistant_router, prefix="/api/assistant", tags=["Assistant"])
app.include_router(vault_router, prefix="/api/vault", tags=["Vault"]) 
app.include_router(workflows_router, prefix="/api/workflows", tags=["Workflows"])
app.include_router(ingest_router, prefix="/api/ingest", tags=["Ingestion"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.app_env == "dev" else "An unexpected error occurred",
            "type": type(exc).__name__
        }
    )


# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handler for HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "dev",
        log_level=settings.log_level.lower(),
        access_log=True
    )