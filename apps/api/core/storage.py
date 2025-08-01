"""
File system storage management for QaAI.

Handles file uploads, organization, and retrieval following
the local-first approach specified in requirements.
"""

from __future__ import annotations
import asyncio
import hashlib
import shutil
from pathlib import Path
from typing import Optional, BinaryIO, AsyncGenerator, Union
from datetime import datetime
from uuid import uuid4

from .config import settings


class StorageManager:
    """
    Local filesystem storage manager.
    
    Organizes files by project and type, handles deduplication,
    and provides secure file operations.
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or settings.storage_path
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file for deduplication."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _get_project_path(self, project_id: str) -> Path:
        """Get storage path for project."""
        project_path = self.base_path / "projects" / project_id
        project_path.mkdir(parents=True, exist_ok=True)
        return project_path
    
    def _get_temp_path(self) -> Path:
        """Get temporary storage path."""
        temp_path = self.base_path / "temp"
        temp_path.mkdir(parents=True, exist_ok=True)
        return temp_path
    
    async def store_file(
        self,
        file_content: Union[bytes, BinaryIO],
        filename: str,
        project_id: str,
        content_type: str = "application/octet-stream"
    ) -> tuple[str, Path]:
        """
        Store file in project directory.
        
        Returns:
            tuple[str, Path]: (file_id, stored_path)
        """
        # Generate unique file ID
        file_id = str(uuid4())
        
        # Get project storage path
        project_path = self._get_project_path(project_id)
        
        # Create safe filename
        safe_filename = self._sanitize_filename(filename)
        stored_path = project_path / f"{file_id}_{safe_filename}"
        
        # Write file content
        if isinstance(file_content, bytes):
            stored_path.write_bytes(file_content)
        else:
            # Handle file-like object
            with open(stored_path, 'wb') as dest:
                if hasattr(file_content, 'read'):
                    while chunk := file_content.read(8192):
                        dest.write(chunk)
                else:
                    dest.write(file_content)
        
        return file_id, stored_path
    
    async def store_upload(
        self,
        upload_file,  # FastAPI UploadFile
        project_id: str
    ) -> tuple[str, Path, dict]:
        """
        Store uploaded file with metadata extraction.
        
        Returns:
            tuple[str, Path, dict]: (file_id, stored_path, metadata)
        """
        # Read file content
        content = await upload_file.read()
        await upload_file.seek(0)  # Reset for potential re-reading
        
        # Store file
        file_id, stored_path = await self.store_file(
            content,
            upload_file.filename,
            project_id,
            upload_file.content_type or "application/octet-stream"
        )
        
        # Extract metadata
        metadata = {
            "filename": upload_file.filename,
            "content_type": upload_file.content_type,
            "size_bytes": len(content),
            "file_hash": hashlib.sha256(content).hexdigest(),
            "stored_path": stored_path.relative_to(self.base_path).as_posix()
        }
        
        return file_id, stored_path, metadata
    
    def get_file_path(self, file_id: str, project_id: str) -> Optional[Path]:
        """Get path to stored file."""
        project_path = self._get_project_path(project_id)
        
        # Find file by ID prefix
        for file_path in project_path.iterdir():
            if file_path.name.startswith(f"{file_id}_"):
                return file_path
        
        return None
    
    async def read_file(self, file_id: str, project_id: str) -> Optional[bytes]:
        """Read file content by ID."""
        file_path = self.get_file_path(file_id, project_id)
        if file_path and file_path.exists():
            return file_path.read_bytes()
        return None
    
    async def read_file_text(
        self,
        file_id: str,
        project_id: str,
        encoding: str = "utf-8"
    ) -> Optional[str]:
        """Read file content as text."""
        content = await self.read_file(file_id, project_id)
        if content:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                # Try common encodings
                for enc in ["latin-1", "cp1252", "utf-16"]:
                    try:
                        return content.decode(enc)
                    except UnicodeDecodeError:
                        continue
        return None
    
    async def delete_file(self, file_id: str, project_id: str) -> bool:
        """Delete stored file."""
        file_path = self.get_file_path(file_id, project_id)
        if file_path and file_path.exists():
            file_path.unlink()
            return True
        return False
    
    async def list_project_files(self, project_id: str) -> list[dict]:
        """List all files in project."""
        project_path = self._get_project_path(project_id)
        files = []
        
        for file_path in project_path.iterdir():
            if file_path.is_file() and "_" in file_path.name:
                # Extract file ID from filename
                file_id = file_path.name.split("_", 1)[0]
                files.append({
                    "file_id": file_id,
                    "filename": file_path.name.split("_", 1)[1],
                    "size_bytes": file_path.stat().st_size,
                    "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime)
                })
        
        return sorted(files, key=lambda x: x["modified_at"], reverse=True)
    
    async def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """Clean up temporary files older than specified age."""
        temp_path = self._get_temp_path()
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        deleted_count = 0
        
        for file_path in temp_path.iterdir():
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                deleted_count += 1
        
        return deleted_count
    
    def get_storage_stats(self) -> dict:
        """Get storage usage statistics."""
        total_size = 0
        file_count = 0
        
        for file_path in self.base_path.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1
        
        return {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
            "base_path": str(self.base_path)
        }
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Create safe filename by removing/replacing problematic characters."""
        import re
        
        # Remove path components
        filename = Path(filename).name
        
        # Replace problematic characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Limit length
        name, ext = Path(filename).stem, Path(filename).suffix
        if len(name) > 200:
            name = name[:200]
        
        return f"{name}{ext}" if ext else name


# Global storage manager instance
storage = StorageManager()