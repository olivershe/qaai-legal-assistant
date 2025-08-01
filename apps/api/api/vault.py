"""
Vault API endpoints for project and document management.

Following PRP requirements:
- CRUD operations for projects and documents
- File upload with metadata extraction
- Search functionality with RAG integration
"""

from __future__ import annotations
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete

from core.models import (
    VaultProject,
    CreateProjectRequest, 
    ProjectResponse,
    DocumentMetadata,
    UploadResponse,
    SearchRequest,
    SearchResponse,
    JurisdictionType
)
from core.database import get_db, VaultProject as VaultProjectDB
from core.storage import storage
from rag.retrievers import difc_retriever


router = APIRouter()


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new Vault project."""
    try:
        # Generate project ID
        project_id = str(uuid.uuid4())
        
        # Create project in database
        db_project = VaultProjectDB(
            id=project_id,
            name=request.name,
            visibility=request.visibility,
            document_count=0,
            owner="default_user",  # In production, get from auth
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(db_project)
        await db.commit()
        await db.refresh(db_project)
        
        # Convert to response model
        project = VaultProject(
            id=db_project.id,
            name=db_project.name,
            visibility=db_project.visibility,
            document_count=db_project.document_count,
            created_at=db_project.created_at,
            updated_at=db_project.updated_at,
            owner=db_project.owner
        )
        
        return ProjectResponse(
            project=project,
            success=True,
            message="Project created successfully"
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Project creation error: {str(e)}")


@router.get("/projects")
async def list_projects(
    limit: int = 20,
    offset: int = 0,
    visibility: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List Vault projects with pagination."""
    try:
        # Build query
        query = select(VaultProjectDB)
        
        if visibility:
            query = query.where(VaultProjectDB.visibility == visibility)
        
        # Apply pagination
        query = query.offset(offset).limit(limit).order_by(VaultProjectDB.updated_at.desc())
        
        # Execute query
        result = await db.execute(query)
        db_projects = result.scalars().all()
        
        # Get total count
        count_query = select(func.count(VaultProjectDB.id))
        if visibility:
            count_query = count_query.where(VaultProjectDB.visibility == visibility)
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0
        
        # Convert to response models
        projects = []
        for db_project in db_projects:
            project = VaultProject(
                id=db_project.id,
                name=db_project.name,
                visibility=db_project.visibility,
                document_count=db_project.document_count,
                created_at=db_project.created_at,
                updated_at=db_project.updated_at,
                owner=db_project.owner
            )
            projects.append(project)
        
        return {
            "projects": projects,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Project listing error: {str(e)}")


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific project by ID."""
    try:
        # Query project
        query = select(VaultProjectDB).where(VaultProjectDB.id == project_id)
        result = await db.execute(query)
        db_project = result.scalar_one_or_none()
        
        if not db_project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Convert to response model
        project = VaultProject(
            id=db_project.id,
            name=db_project.name,
            visibility=db_project.visibility,
            document_count=db_project.document_count,
            created_at=db_project.created_at,
            updated_at=db_project.updated_at,
            owner=db_project.owner
        )
        
        return {"project": project}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Project retrieval error: {str(e)}")


@router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    request: CreateProjectRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update a project."""
    try:
        # Check if project exists
        query = select(VaultProjectDB).where(VaultProjectDB.id == project_id)
        result = await db.execute(query)
        db_project = result.scalar_one_or_none()
        
        if not db_project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Update project
        update_query = (
            update(VaultProjectDB)
            .where(VaultProjectDB.id == project_id)
            .values(
                name=request.name,
                visibility=request.visibility,
                updated_at=datetime.now()
            )
        )
        
        await db.execute(update_query)
        await db.commit()
        
        # Get updated project
        result = await db.execute(query)
        updated_project = result.scalar_one()
        
        project = VaultProject(
            id=updated_project.id,
            name=updated_project.name,
            visibility=updated_project.visibility,
            document_count=updated_project.document_count,
            created_at=updated_project.created_at,
            updated_at=updated_project.updated_at,
            owner=updated_project.owner
        )
        
        return ProjectResponse(
            project=project,
            success=True,
            message="Project updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Project update error: {str(e)}")


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a project and all its documents."""
    try:
        # Check if project exists
        query = select(VaultProjectDB).where(VaultProjectDB.id == project_id)
        result = await db.execute(query)
        db_project = result.scalar_one_or_none()
        
        if not db_project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Delete project files from storage
        try:
            files = await storage.list_project_files(project_id)
            for file_info in files:
                await storage.delete_file(file_info["file_id"], project_id)
        except Exception as e:
            # Log but don't fail on storage cleanup errors
            print(f"Storage cleanup warning: {e}")
        
        # Delete project from database
        delete_query = delete(VaultProjectDB).where(VaultProjectDB.id == project_id)
        await db.execute(delete_query)
        await db.commit()
        
        return {
            "success": True,
            "message": "Project deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Project deletion error: {str(e)}")


@router.post("/projects/{project_id}/upload", response_model=UploadResponse)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    jurisdiction: Optional[str] = Form("DIFC"),
    instrument_type: Optional[str] = Form("OTHER"),
    db: AsyncSession = Depends(get_db)
):
    """Upload a document to a project."""
    try:
        # Verify project exists
        query = select(VaultProjectDB).where(VaultProjectDB.id == project_id)
        result = await db.execute(query)
        db_project = result.scalar_one_or_none()
        
        if not db_project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Store file
        file_id, stored_path, metadata = await storage.store_upload(file, project_id)
        
        # Create document metadata
        document = DocumentMetadata(
            id=file_id,
            project_id=project_id,
            filename=metadata["filename"],
            title=metadata["filename"].rsplit('.', 1)[0].replace('_', ' ').title(),
            file_path=metadata["stored_path"],
            content_type=metadata["content_type"],
            size_bytes=metadata["size_bytes"],
            jurisdiction=JurisdictionType(jurisdiction),
            instrument_type=getattr(__import__('..core.models', fromlist=['InstrumentType']).InstrumentType, instrument_type, 
                                  __import__('..core.models', fromlist=['InstrumentType']).InstrumentType.OTHER),
            upload_date=datetime.now()
        )
        
        # Update project document count
        update_query = (
            update(VaultProjectDB)
            .where(VaultProjectDB.id == project_id)
            .values(
                document_count=VaultProjectDB.document_count + 1,
                updated_at=datetime.now()
            )
        )
        await db.execute(update_query)
        await db.commit()
        
        return UploadResponse(
            document=document,
            success=True,
            message="Document uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")


@router.get("/projects/{project_id}/documents")
async def list_documents(
    project_id: str,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List documents in a project."""
    try:
        # Verify project exists
        query = select(VaultProjectDB).where(VaultProjectDB.id == project_id)
        result = await db.execute(query)
        db_project = result.scalar_one_or_none()
        
        if not db_project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get documents from storage
        files = await storage.list_project_files(project_id)
        
        # Apply pagination
        total_count = len(files)
        paginated_files = files[offset:offset + limit]
        
        return {
            "documents": paginated_files,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document listing error: {str(e)}")


@router.post("/projects/{project_id}/search", response_model=SearchResponse)
async def search_project(
    project_id: str,
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Search documents within a project using RAG."""
    try:
        # Verify project exists
        query = select(VaultProjectDB).where(VaultProjectDB.id == project_id)
        result = await db.execute(query)
        db_project = result.scalar_one_or_none()
        
        if not db_project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Perform search using RAG retriever
        matches = await difc_retriever.search_vault_project(
            query=request.query,
            project_id=project_id,
            limit=request.limit
        )
        
        # Convert matches to retrieval results
        results = []
        for match in matches:
            from core.models import RetrievalResult, EmbeddingDocument
            
            result = RetrievalResult(
                document=EmbeddingDocument(
                    id=match.chunk.id,
                    content=match.chunk.content,
                    metadata=DocumentMetadata(
                        id=match.chunk.doc_id,
                        project_id=project_id,
                        filename=match.chunk.metadata.get("filename", "Unknown") if match.chunk.metadata else "Unknown",
                        title=match.chunk.metadata.get("title", "Unknown") if match.chunk.metadata else "Unknown",
                        file_path=match.chunk.metadata.get("file_path", "") if match.chunk.metadata else "",
                        content_type=match.chunk.metadata.get("content_type", "") if match.chunk.metadata else "",
                        size_bytes=match.chunk.metadata.get("size_bytes", 0) if match.chunk.metadata else 0,
                        jurisdiction=JurisdictionType.DIFC,
                        instrument_type=getattr(__import__('..core.models', fromlist=['InstrumentType']).InstrumentType, 'OTHER'),
                        upload_date=datetime.now()
                    )
                ),
                score=match.score,
                chunk_index=match.chunk.chunk_index
            )
            results.append(result)
        
        return SearchResponse(
            results=results,
            total_count=len(results),
            query=request.query,
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.get("/projects/{project_id}/stats")
async def get_project_stats(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get project statistics."""
    try:
        # Verify project exists
        query = select(VaultProjectDB).where(VaultProjectDB.id == project_id)
        result = await db.execute(query)
        db_project = result.scalar_one_or_none()
        
        if not db_project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get storage statistics
        storage_stats = storage.get_storage_stats()
        files = await storage.list_project_files(project_id)
        
        project_size = sum(f.get("size_bytes", 0) for f in files)
        
        return {
            "project_id": project_id,
            "document_count": len(files),
            "total_size_bytes": project_size,
            "total_size_mb": round(project_size / (1024 * 1024), 2),
            "created_at": db_project.created_at.isoformat(),
            "updated_at": db_project.updated_at.isoformat(),
            "visibility": db_project.visibility
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")