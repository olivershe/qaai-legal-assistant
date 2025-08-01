"""
OpenAI API client with rate limiting and error handling.

Following 2025 best practices:
- Exponential backoff with jitter
- Honor Retry-After headers from 429 responses
- Token bucket approach for proactive rate limiting
"""

from __future__ import annotations
import asyncio
import time
import random
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from core.config import settings


class RateLimitTracker:
    """Track rate limits using token bucket approach."""
    
    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests = max_requests_per_minute
        self.tokens = max_requests_per_minute
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """Acquire permission to make request."""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            
            # Refill tokens based on elapsed time
            tokens_to_add = elapsed * (self.max_requests / 60.0)
            self.tokens = min(self.max_requests, self.tokens + tokens_to_add)
            self.last_refill = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False
    
    async def wait_for_capacity(self) -> float:
        """Calculate wait time for next available token."""
        async with self.lock:
            if self.tokens >= 1:
                return 0.0
            
            tokens_needed = 1 - self.tokens
            wait_time = tokens_needed * (60.0 / self.max_requests)
            return wait_time


class OpenAIClient:
    """
    OpenAI API client with comprehensive error handling and rate limiting.
    
    Implements exponential backoff, token management, and proper error recovery.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.openai_api_key
        self._client = None
        self.rate_limiter = RateLimitTracker(max_requests_per_minute=50)  # Conservative limit
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
    
    def _get_client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai library not installed. Run: pip install openai")
        return self._client
    
    async def _make_request_with_retry(
        self,
        request_func,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> Dict[str, Any]:
        """Make request with exponential backoff retry."""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # Check rate limiting
                if not await self.rate_limiter.acquire():
                    wait_time = await self.rate_limiter.wait_for_capacity()
                    if wait_time > 0:
                        await asyncio.sleep(wait_time)
                        if not await self.rate_limiter.acquire():
                            continue
                
                # Make the request
                response = await request_func()
                return self._format_response(response)
                
            except Exception as e:
                last_exception = e
                
                if attempt == max_retries:
                    break
                
                # Check for rate limit response
                delay = base_delay * (2 ** attempt)
                
                if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    if e.response.status_code == 429:
                        # Rate limited - check for Retry-After header
                        retry_after = e.response.headers.get('Retry-After')
                        if retry_after:
                            try:
                                delay = float(retry_after)
                            except (ValueError, TypeError):
                                pass
                    elif e.response.status_code >= 500:
                        # Server error - use exponential backoff
                        pass
                    elif 400 <= e.response.status_code < 500:
                        # Client error - don't retry
                        break
                
                # Add jitter to prevent thundering herd
                jitter = random.uniform(0, 0.1) * delay
                await asyncio.sleep(delay + jitter)
        
        raise last_exception or Exception("Max retries exceeded")
    
    def _format_response(self, response) -> Dict[str, Any]:
        """Format OpenAI response to standard format."""
        if hasattr(response, 'choices') and response.choices:
            choice = response.choices[0]
            
            # Handle different response types
            if hasattr(choice, 'message') and choice.message:
                content = choice.message.content
            elif hasattr(choice, 'text'):
                content = choice.text
            else:
                content = str(choice)
            
            return {
                "content": content,
                "model": getattr(response, 'model', 'unknown'),
                "usage": {
                    "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0) if hasattr(response, 'usage') else 0,
                    "completion_tokens": getattr(response.usage, 'completion_tokens', 0) if hasattr(response, 'usage') else 0,
                    "total_tokens": getattr(response.usage, 'total_tokens', 0) if hasattr(response, 'usage') else 0
                },
                "finish_reason": getattr(choice, 'finish_reason', 'unknown')
            }
        
        return {
            "content": str(response),
            "model": "unknown",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "finish_reason": "unknown"
        }
    
    async def complete(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate completion using OpenAI models."""
        client = self._get_client()
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        async def make_request():
            return await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=60.0
            )
        
        return await self._make_request_with_retry(make_request)
    
    async def stream_complete(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ):
        """Stream completion using OpenAI models."""
        client = self._get_client()
        
        # Check rate limiting
        if not await self.rate_limiter.acquire():
            wait_time = await self.rate_limiter.wait_for_capacity()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                timeout=60.0
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield {
                            "type": "chunk",
                            "content": delta.content,
                            "model": chunk.model,
                            "finish_reason": getattr(chunk.choices[0], 'finish_reason', None)
                        }
                        
        except Exception as e:
            yield {
                "type": "error",
                "content": f"Streaming error: {str(e)}",
                "model": model
            }
    
    async def create_embedding(
        self,
        text: str,
        model: str = "text-embedding-3-small"
    ) -> List[float]:
        """Create embedding using OpenAI embedding models."""
        client = self._get_client()
        
        async def make_request():
            return await client.embeddings.create(
                model=model,
                input=text
            )
        
        response = await self._make_request_with_retry(make_request)
        
        # Extract embedding from response
        if hasattr(response, 'data') and response.data:
            return response.data[0].embedding
        
        # Fallback for formatted response
        return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI API health and connectivity."""
        try:
            client = self._get_client()
            
            # Simple test request
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
                timeout=10.0
            )
            
            return {
                "healthy": True,
                "api_key_valid": True,
                "test_model": "gpt-3.5-turbo",
                "response_time": "< 10s"
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "api_key_valid": False,
                "error": str(e),
                "test_model": "gpt-3.5-turbo"
            }


# Global OpenAI client instance
openai_client = OpenAIClient()