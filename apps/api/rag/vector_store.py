"""
FAISS vector store implementation for QaAI RAG system.

Following examples/rag_ingest.py patterns with 2025 enhancements:
- IndexFlatIP for small datasets, IndexIVFFlat for scale
- Hybrid retrieval (BM25 + FAISS) for better precision
- DIFC-first retrieval with jurisdiction boosting
"""

from __future__ import annotations
import json
import os
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import sqlite3
import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime

from core.config import settings
from core.models import JurisdictionType, InstrumentType, DocumentMetadata
from rag.embeddings import embeddings


@dataclass
class DocumentChunk:
    """Document chunk for vector storage."""
    id: str
    doc_id: str
    content: str
    chunk_index: int
    section_ref: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RetrievalMatch:
    """Vector search result with metadata."""
    chunk: DocumentChunk
    score: float
    document_metadata: Optional[DocumentMetadata] = None


class VectorStore:
    """
    FAISS-based vector store with hybrid retrieval capabilities.
    
    Mirrors examples/rag_ingest.py structure with production enhancements.
    """
    
    def __init__(self, index_dir: Optional[Path] = None):
        self.index_dir = index_dir or settings.index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_path = self.index_dir / "qaai.faiss"
        self.metadata_path = self.index_dir / "metadata.json"
        
        self._index = None
        self._metadata = None
        self._chunks = {}  # chunk_id -> DocumentChunk mapping
    
    def _load_index(self):
        """Lazy load FAISS index."""
        if self._index is None and self.index_path.exists():
            try:
                import faiss
                self._index = faiss.read_index(str(self.index_path))
            except ImportError:
                raise ImportError("faiss-cpu not installed. Run: pip install faiss-cpu")
            except Exception as e:
                print(f"Error loading FAISS index: {e}")
                self._index = None
    
    def _load_metadata(self):
        """Load metadata and chunk mappings."""
        if self._metadata is None and self.metadata_path.exists():
            try:
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    self._metadata = json.load(f)
                
                # Build chunk mapping
                for vector_info in self._metadata.get("vectors", []):
                    chunk_id = vector_info.get("chunk_id")
                    if chunk_id:
                        # Create basic chunk info - full details loaded from database
                        self._chunks[chunk_id] = {
                            "doc_id": vector_info.get("doc_id"),
                            "chunk_index": vector_info.get("chunk_index", 0)
                        }
            except Exception as e:
                print(f"Error loading metadata: {e}")
                self._metadata = {}
    
    async def build_index(
        self,
        corpus_dir: Path,
        chunk_size: int = None,
        chunk_overlap: int = None
    ) -> bool:
        """
        Build FAISS index from document corpus.
        
        Following examples/rag_ingest.py pattern with async support.
        """
        chunk_size = chunk_size or settings.chunk_size
        chunk_overlap = chunk_overlap or settings.chunk_overlap
        
        try:
            import faiss
            import numpy as np
            from pypdf import PdfReader
        except ImportError as e:
            raise ImportError(f"Required library not installed: {e}")
        
        print(f"Building index from {corpus_dir}")
        
        # Collect documents
        documents = []
        for file_path in corpus_dir.rglob("*"):
            if file_path.suffix.lower() in {".pdf", ".txt", ".md", ".html"}:
                documents.append(file_path)
        
        if not documents:
            print(f"No documents found in {corpus_dir}")
            return False
        
        print(f"Processing {len(documents)} documents")
        
        # Process documents and create chunks
        all_chunks = []
        all_texts = []
        
        for doc_path in documents:
            doc_id = str(uuid.uuid4())
            
            # Extract text based on file type
            if doc_path.suffix.lower() == ".pdf":
                text = self._extract_pdf_text(doc_path)
            else:
                text = doc_path.read_text(encoding="utf-8", errors="ignore")
            
            # Create document metadata
            doc_metadata = DocumentMetadata(
                id=doc_id,
                project_id="corpus",  # Default project for corpus documents
                filename=doc_path.name,
                title=self._extract_title(doc_path.name),
                file_path=str(doc_path.relative_to(corpus_dir)),
                content_type=self._get_content_type(doc_path),
                size_bytes=doc_path.stat().st_size,
                jurisdiction=self._infer_jurisdiction(doc_path.name),
                instrument_type=self._infer_instrument_type(doc_path.name),
                upload_date=datetime.now()
            )
            
            # Split into chunks
            chunks = self._split_text(text, chunk_size, chunk_overlap)
            
            for i, chunk_text in enumerate(chunks):
                chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=chunk_text,
                    chunk_index=i,
                    metadata=asdict(doc_metadata)
                )
                all_chunks.append(chunk)
                all_texts.append(chunk_text)
        
        if not all_texts:
            print("No text content extracted")
            return False
        
        print(f"Generated {len(all_texts)} chunks, creating embeddings...")
        
        # Generate embeddings
        embedding_vectors = await embeddings.embed_texts(all_texts)
        
        if not embedding_vectors:
            print("Failed to generate embeddings")
            return False
        
        # Create FAISS index
        dimension = len(embedding_vectors[0])
        
        # Use IndexFlatIP for small datasets, IndexIVFFlat for larger ones
        if len(embedding_vectors) < 10000:
            index = faiss.IndexFlatIP(dimension)
        else:
            # Use IVF for larger datasets
            nlist = min(100, len(embedding_vectors) // 10)
            quantizer = faiss.IndexFlatIP(dimension)
            index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
            
            # Train the index
            train_vectors = np.array(embedding_vectors[:min(1000, len(embedding_vectors))], dtype='float32')
            index.train(train_vectors)
        
        # Add vectors to index
        vectors_array = np.array(embedding_vectors, dtype='float32')
        index.add(vectors_array)
        
        # Save index
        faiss.write_index(index, str(self.index_path))
        
        # Save metadata
        metadata = {
            "vectors": [
                {
                    "chunk_id": chunk.id,
                    "doc_id": chunk.doc_id,
                    "chunk_index": chunk.chunk_index
                }
                for chunk in all_chunks
            ],
            "build_info": {
                "total_documents": len(documents),
                "total_chunks": len(all_chunks),
                "dimension": dimension,
                "index_type": index.__class__.__name__,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap
            }
        }
        
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # Store chunks in database (simplified for demo)
        await self._store_chunks_in_db(all_chunks)
        
        print(f"Index built successfully: {len(embedding_vectors)} vectors")
        return True
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        jurisdiction: Optional[JurisdictionType] = None,
        boost_difc: bool = True
    ) -> List[RetrievalMatch]:
        """
        Search vector store with DIFC-first boosting.
        
        Args:
            query: Search query
            limit: Maximum results to return
            jurisdiction: Filter by jurisdiction
            boost_difc: Apply DIFC jurisdiction boosting
        """
        self._load_index()
        self._load_metadata()
        
        if not self._index or not self._metadata:
            return []
        
        try:
            # Generate query embedding
            query_vector = await embeddings.embed_query(query)
            
            if not query_vector:
                return []
            
            # Search FAISS index
            import numpy as np
            query_array = np.array([query_vector], dtype='float32')
            
            # Search with larger limit for filtering
            search_limit = min(limit * 3, self._index.ntotal)
            scores, indices = self._index.search(query_array, search_limit)
            
            # Process results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0:  # FAISS returns -1 for invalid indices
                    continue
                
                vector_info = self._metadata["vectors"][idx]
                chunk_id = vector_info["chunk_id"]
                
                # Load chunk details from database/cache
                chunk = await self._load_chunk(chunk_id)
                if not chunk:
                    continue
                
                # Apply jurisdiction filtering
                if jurisdiction and chunk.metadata:
                    chunk_jurisdiction = chunk.metadata.get("jurisdiction")
                    if chunk_jurisdiction != jurisdiction.value:
                        continue
                
                # Apply DIFC boosting
                adjusted_score = float(score)
                if boost_difc and chunk.metadata:
                    chunk_jurisdiction = chunk.metadata.get("jurisdiction")
                    if chunk_jurisdiction == JurisdictionType.DIFC.value:
                        adjusted_score *= 1.2  # 20% boost for DIFC sources
                
                results.append(RetrievalMatch(
                    chunk=chunk,
                    score=adjusted_score
                ))
            
            # Sort by adjusted score and limit
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:limit]
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    async def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[RetrievalMatch]:
        """
        Hybrid search combining FAISS vector search with BM25 keyword search.
        
        Following 2025 best practices for improved retrieval precision.
        """
        # Get vector search results
        vector_results = await self.search(query, limit * 2)
        
        # Get keyword search results (simplified BM25-like scoring)
        keyword_results = await self._keyword_search(query, limit * 2)
        
        # Combine and re-rank results
        combined_scores = {}
        
        # Add vector scores
        for result in vector_results:
            chunk_id = result.chunk.id
            combined_scores[chunk_id] = {
                "chunk": result.chunk,
                "vector_score": result.score,
                "keyword_score": 0.0
            }
        
        # Add keyword scores
        for result in keyword_results:
            chunk_id = result.chunk.id
            if chunk_id in combined_scores:
                combined_scores[chunk_id]["keyword_score"] = result.score
            else:
                combined_scores[chunk_id] = {
                    "chunk": result.chunk,
                    "vector_score": 0.0,
                    "keyword_score": result.score
                }
        
        # Calculate combined scores and sort
        final_results = []
        for chunk_id, scores in combined_scores.items():
            combined_score = (
                scores["vector_score"] * vector_weight +
                scores["keyword_score"] * keyword_weight
            )
            
            final_results.append(RetrievalMatch(
                chunk=scores["chunk"],
                score=combined_score
            ))
        
        final_results.sort(key=lambda x: x.score, reverse=True)
        return final_results[:limit]
    
    def _split_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into chunks following examples/rag_ingest.py pattern."""
        words = text.split()
        chunks = []
        i = 0
        
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))
            i += chunk_size - overlap
            if i <= 0:
                break
        
        return chunks
    
    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract text from PDF file."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            print(f"Error extracting PDF text from {pdf_path}: {e}")
            return ""
    
    def _extract_title(self, filename: str) -> str:
        """Extract title from filename."""
        return Path(filename).stem.replace("_", " ").title()
    
    def _get_content_type(self, file_path: Path) -> str:
        """Get MIME type from file extension."""
        content_types = {
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".html": "text/html"
        }
        return content_types.get(file_path.suffix.lower(), "application/octet-stream")
    
    def _infer_jurisdiction(self, filename: str) -> JurisdictionType:
        """Infer jurisdiction from filename."""
        filename_lower = filename.lower()
        if "difc" in filename_lower:
            return JurisdictionType.DIFC
        elif "dfsa" in filename_lower:
            return JurisdictionType.DFSA
        elif "uae" in filename_lower:
            return JurisdictionType.UAE
        return JurisdictionType.OTHER
    
    def _infer_instrument_type(self, filename: str) -> InstrumentType:
        """Infer instrument type from filename."""
        filename_lower = filename.lower()
        if "law" in filename_lower:
            return InstrumentType.LAW
        elif "regulation" in filename_lower:
            return InstrumentType.REGULATION
        elif "rule" in filename_lower:
            return InstrumentType.COURT_RULE
        elif "rulebook" in filename_lower:
            return InstrumentType.RULEBOOK
        return InstrumentType.OTHER
    
    async def _store_chunks_in_db(self, chunks: List[DocumentChunk]):
        """Store chunks in database (simplified implementation)."""
        # This would integrate with the database layer
        # For now, store in memory
        for chunk in chunks:
            self._chunks[chunk.id] = chunk
    
    async def _load_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        """Load chunk details from storage."""
        return self._chunks.get(chunk_id)
    
    async def _keyword_search(self, query: str, limit: int) -> List[RetrievalMatch]:
        """Simple keyword search implementation."""
        query_terms = set(query.lower().split())
        results = []
        
        for chunk in self._chunks.values():
            if isinstance(chunk, DocumentChunk):
                content_terms = set(chunk.content.lower().split())
                # Simple TF-like scoring
                overlap = len(query_terms & content_terms)
                if overlap > 0:
                    score = overlap / len(query_terms)
                    results.append(RetrievalMatch(chunk=chunk, score=score))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        self._load_index()
        self._load_metadata()
        
        stats = {
            "index_exists": self.index_path.exists(),
            "metadata_exists": self.metadata_path.exists(),
            "total_vectors": 0,
            "dimension": 0,
            "index_type": None
        }
        
        if self._index:
            stats["total_vectors"] = self._index.ntotal
            stats["dimension"] = self._index.d
            stats["index_type"] = self._index.__class__.__name__
        
        if self._metadata:
            stats.update(self._metadata.get("build_info", {}))
        
        return stats


# Global vector store instance
vector_store = VectorStore()