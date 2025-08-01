"""
Embedding generation for QaAI RAG system.

Following 2025 best practices:
- Support both sentence-transformers and OpenAI embeddings  
- Use normalize_embeddings=True for consistent scoring
- Include proper error handling and rate limiting
"""

from __future__ import annotations
import asyncio
import time
from typing import List, Optional, Union
from abc import ABC, abstractmethod

from core.config import settings


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for list of texts."""
        pass
    
    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for single query."""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding dimension size."""
        pass


class SentenceTransformerProvider(EmbeddingProvider):
    """
    Local sentence-transformers provider.
    
    Uses free models with normalization for consistent similarity scoring.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.embeddings_model
        self._model = None
        self._dimension = None
    
    def _load_model(self):
        """Lazy load the model to avoid import issues."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                # Test embedding to get dimension
                test_embedding = self._model.encode(["test"], normalize_embeddings=True)
                self._dimension = len(test_embedding[0])
            except ImportError:
                raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings with normalization."""
        if not texts:
            return []
        
        self._load_model()
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self._model.encode(texts, normalize_embeddings=True)
        )
        
        return embeddings.tolist()
    
    async def embed_query(self, query: str) -> List[float]:
        """Generate single query embedding."""
        results = await self.embed_texts([query])
        return results[0] if results else []
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._dimension is None:
            self._load_model()
        return self._dimension


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embeddings provider with rate limiting.
    
    Implements exponential backoff and honors rate limits.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key or settings.openai_api_key
        self.model = model
        self._client = None
        self._dimension = None
        
        if not self.api_key:
            raise ValueError("OpenAI API key required for OpenAI embeddings")
    
    def _get_client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai not installed. Run: pip install openai")
        return self._client
    
    async def _embed_with_retry(
        self,
        texts: List[str],
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> List[List[float]]:
        """Embed texts with exponential backoff retry."""
        client = self._get_client()
        
        for attempt in range(max_retries + 1):
            try:
                response = await client.embeddings.create(
                    model=self.model,
                    input=texts
                )
                
                embeddings = [item.embedding for item in response.data]
                
                # Cache dimension on first successful call
                if self._dimension is None and embeddings:
                    self._dimension = len(embeddings[0])
                
                return embeddings
                
            except Exception as e:
                if attempt == max_retries:
                    raise e
                
                # Exponential backoff with jitter
                delay = base_delay * (2 ** attempt) + (asyncio.get_event_loop().time() % 1)
                
                # Check for rate limit response
                if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                    retry_after = e.response.headers.get('Retry-After')
                    if retry_after:
                        delay = float(retry_after)
                
                await asyncio.sleep(delay)
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings with batching for large inputs."""
        if not texts:
            return []
        
        # Batch texts to avoid hitting token limits
        batch_size = 100  # Conservative batch size
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = await self._embed_with_retry(batch)
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    async def embed_query(self, query: str) -> List[float]:
        """Generate single query embedding."""
        results = await self.embed_texts([query])
        return results[0] if results else []
    
    @property 
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._dimension is None:
            # Default dimensions for common models
            dimensions = {
                "text-embedding-3-small": 1536,
                "text-embedding-3-large": 3072,
                "text-embedding-ada-002": 1536
            }
            self._dimension = dimensions.get(self.model, 1536)
        return self._dimension


class EmbeddingManager:
    """
    Manages embedding providers and provides unified interface.
    
    Automatically selects provider based on configuration.
    """
    
    def __init__(self):
        self._provider: Optional[EmbeddingProvider] = None
    
    def _get_provider(self) -> EmbeddingProvider:
        """Get or create embedding provider based on settings."""
        if self._provider is None:
            if settings.embeddings_backend == "openai" and settings.openai_api_key:
                self._provider = OpenAIEmbeddingProvider()
            else:
                self._provider = SentenceTransformerProvider()
        
        return self._provider
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        provider = self._get_provider()
        return await provider.embed_texts(texts)
    
    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for single query."""
        provider = self._get_provider()
        return await provider.embed_query(query)
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        provider = self._get_provider()
        return provider.dimension
    
    def get_provider_info(self) -> dict:
        """Get information about current provider."""
        provider = self._get_provider()
        return {
            "backend": settings.embeddings_backend,
            "model": getattr(provider, 'model_name', None) or getattr(provider, 'model', None),
            "dimension": provider.dimension,
            "provider_class": provider.__class__.__name__
        }


# Global embedding manager instance
embeddings = EmbeddingManager()