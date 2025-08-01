"""
Anthropic API client with rate limiting and error handling.

Following 2025 best practices:
- Token bucket algorithm implementation
- Cache-aware rate limits support
- Proper retry strategies with exponential backoff
"""

from __future__ import annotations
import asyncio
import time
import random
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from core.config import settings


class AnthropicRateLimiter:
    """
    Token bucket rate limiter for Anthropic API.
    
    Supports different rate limits for different model classes.
    """
    
    def __init__(self):
        # Conservative limits based on Anthropic documentation
        self.limits = {
            "claude-3-haiku": {"rpm": 100, "tpm": 50000},
            "claude-3-sonnet": {"rpm": 50, "tpm": 40000},
            "claude-3.7-sonnet": {"rpm": 50, "tpm": 40000},
            "claude-3-opus": {"rpm": 20, "tpm": 30000}
        }
        
        self.buckets = {}
        self.lock = asyncio.Lock()
    
    def _get_bucket(self, model: str, limit_type: str):
        """Get or create rate limit bucket for model and limit type."""
        key = f"{model}_{limit_type}"
        
        if key not in self.buckets:
            if model in self.limits:
                limit = self.limits[model][limit_type]
            else:
                # Default limits for unknown models
                limit = 20 if limit_type == "rpm" else 20000
            
            self.buckets[key] = {
                "tokens": limit,
                "max_tokens": limit,
                "last_refill": time.time(),
                "refill_rate": limit / 60.0 if limit_type == "rpm" else limit / 60.0
            }
        
        return self.buckets[key]
    
    async def acquire(self, model: str, estimated_tokens: int = 1000) -> bool:
        """Acquire permission to make request."""
        async with self.lock:
            # Check both RPM and TPM limits
            rpm_bucket = self._get_bucket(model, "rpm")
            tpm_bucket = self._get_bucket(model, "tpm")
            
            now = time.time()
            
            # Refill RPM bucket
            elapsed = now - rpm_bucket["last_refill"]
            tokens_to_add = elapsed * rpm_bucket["refill_rate"]
            rpm_bucket["tokens"] = min(rpm_bucket["max_tokens"], rpm_bucket["tokens"] + tokens_to_add)
            rpm_bucket["last_refill"] = now
            
            # Refill TPM bucket
            elapsed = now - tpm_bucket["last_refill"]
            tokens_to_add = elapsed * tpm_bucket["refill_rate"]
            tpm_bucket["tokens"] = min(tpm_bucket["max_tokens"], tpm_bucket["tokens"] + tokens_to_add)
            tpm_bucket["last_refill"] = now
            
            # Check if we can proceed
            if rpm_bucket["tokens"] >= 1 and tpm_bucket["tokens"] >= estimated_tokens:
                rpm_bucket["tokens"] -= 1
                tpm_bucket["tokens"] -= estimated_tokens
                return True
            
            return False
    
    async def wait_time(self, model: str, estimated_tokens: int = 1000) -> float:
        """Calculate wait time for next available request."""
        async with self.lock:
            rpm_bucket = self._get_bucket(model, "rpm")
            tpm_bucket = self._get_bucket(model, "tpm")
            
            rpm_wait = 0.0
            tpm_wait = 0.0
            
            if rpm_bucket["tokens"] < 1:
                rpm_wait = (1 - rpm_bucket["tokens"]) / rpm_bucket["refill_rate"]
            
            if tpm_bucket["tokens"] < estimated_tokens:
                tokens_needed = estimated_tokens - tpm_bucket["tokens"]
                tpm_wait = tokens_needed / tpm_bucket["refill_rate"]
            
            return max(rpm_wait, tpm_wait)


class AnthropicClient:
    """
    Anthropic API client with comprehensive error handling and rate limiting.
    
    Implements token bucket approach and cache-aware optimizations.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.anthropic_api_key
        self._client = None
        self.rate_limiter = AnthropicRateLimiter()
        
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
    
    def _get_client(self):
        """Lazy load Anthropic client."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic library not installed. Run: pip install anthropic")
        return self._client
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation for rate limiting."""
        # Anthropic uses approximately 4 characters per token
        return max(1, len(text) // 4)
    
    async def _make_request_with_retry(
        self,
        request_func,
        model: str,
        estimated_tokens: int = 1000,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> Dict[str, Any]:
        """Make request with exponential backoff retry."""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # Check rate limiting
                if not await self.rate_limiter.acquire(model, estimated_tokens):
                    wait_time = await self.rate_limiter.wait_time(model, estimated_tokens)
                    if wait_time > 0:
                        await asyncio.sleep(min(wait_time, 60))  # Cap wait time
                        if not await self.rate_limiter.acquire(model, estimated_tokens):
                            continue
                
                # Make the request
                response = await request_func()
                return self._format_response(response)
                
            except Exception as e:
                last_exception = e
                
                if attempt == max_retries:
                    break
                
                # Check for specific error types
                delay = base_delay * (2 ** attempt)
                
                if hasattr(e, 'status_code'):
                    if e.status_code == 429:
                        # Rate limited - honor Retry-After if present
                        retry_after = getattr(e, 'retry_after', None)
                        if retry_after:
                            try:
                                delay = float(retry_after)
                            except (ValueError, TypeError):
                                pass
                    elif e.status_code >= 500:
                        # Server error - use exponential backoff
                        pass
                    elif 400 <= e.status_code < 500:
                        # Client error - don't retry most cases
                        if e.status_code not in [408, 429]:  # Timeout and rate limit are retryable
                            break
                
                # Add jitter
                jitter = random.uniform(0, 0.1) * delay
                await asyncio.sleep(delay + jitter)
        
        raise last_exception or Exception("Max retries exceeded")
    
    def _format_response(self, response) -> Dict[str, Any]:
        """Format Anthropic response to standard format."""
        if hasattr(response, 'content') and response.content:
            # Handle new Anthropic API format
            content_blocks = response.content
            
            if content_blocks and len(content_blocks) > 0:
                content = content_blocks[0].text if hasattr(content_blocks[0], 'text') else str(content_blocks[0])
            else:
                content = ""
            
            return {
                "content": content,
                "model": getattr(response, 'model', 'unknown'),
                "usage": {
                    "prompt_tokens": getattr(response.usage, 'input_tokens', 0) if hasattr(response, 'usage') else 0,
                    "completion_tokens": getattr(response.usage, 'output_tokens', 0) if hasattr(response, 'usage') else 0,
                    "total_tokens": (
                        getattr(response.usage, 'input_tokens', 0) + 
                        getattr(response.usage, 'output_tokens', 0)
                    ) if hasattr(response, 'usage') else 0
                },
                "finish_reason": getattr(response, 'stop_reason', 'unknown')
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
        """Generate completion using Anthropic models."""
        client = self._get_client()
        
        # Estimate tokens for rate limiting
        estimated_tokens = self._estimate_tokens(prompt + (system_prompt or "")) + max_tokens
        
        # Prepare messages
        messages = [{"role": "user", "content": prompt}]
        
        async def make_request():
            kwargs = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "timeout": 60.0
            }
            
            if system_prompt:
                kwargs["system"] = system_prompt
            
            return await client.messages.create(**kwargs)
        
        return await self._make_request_with_retry(
            make_request,
            model,
            estimated_tokens
        )
    
    async def stream_complete(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ):
        """Stream completion using Anthropic models."""
        client = self._get_client()
        
        # Estimate tokens for rate limiting
        estimated_tokens = self._estimate_tokens(prompt + (system_prompt or "")) + max_tokens
        
        # Check rate limiting
        if not await self.rate_limiter.acquire(model, estimated_tokens):
            wait_time = await self.rate_limiter.wait_time(model, estimated_tokens)
            if wait_time > 0:
                await asyncio.sleep(min(wait_time, 60))
        
        # Prepare messages
        messages = [{"role": "user", "content": prompt}]
        
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
                "timeout": 60.0
            }
            
            if system_prompt:
                kwargs["system"] = system_prompt
            
            async with client.messages.stream(**kwargs) as stream:
                async for event in stream:
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, 'text'):
                            yield {
                                "type": "chunk",
                                "content": event.delta.text,
                                "model": model,
                                "finish_reason": None
                            }
                    elif event.type == "message_stop":
                        yield {
                            "type": "done",
                            "content": "",
                            "model": model,
                            "finish_reason": "stop"
                        }
                        
        except Exception as e:
            yield {
                "type": "error",
                "content": f"Streaming error: {str(e)}",
                "model": model
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Anthropic API health and connectivity."""
        try:
            client = self._get_client()
            
            # Simple test request
            response = await client.messages.create(
                model="claude-3-haiku-20240307",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
                timeout=10.0
            )
            
            return {
                "healthy": True,
                "api_key_valid": True,
                "test_model": "claude-3-haiku-20240307",
                "response_time": "< 10s"
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "api_key_valid": False,
                "error": str(e),
                "test_model": "claude-3-haiku-20240307"
            }


# Global Anthropic client instance
anthropic_client = AnthropicClient()