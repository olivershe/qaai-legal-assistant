"""
Model selection and routing for QaAI agents.

Following PRP specifications:
- o1 for planning/reasoning tasks
- gpt-4.1 for drafting and generation
- claude-3.7-sonnet for long-context and verification
- Support for manual model override from UI
"""

from __future__ import annotations
from typing import Optional, Dict, Any, Literal
from enum import Enum

from core.config import settings
from core.models import JurisdictionType


class ModelProvider(str, Enum):
    """Available model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ModelCapability(str, Enum):
    """Model capability categories."""
    REASONING = "reasoning"  # Complex analysis, planning
    GENERATION = "generation"  # Content creation, drafting
    VERIFICATION = "verification"  # Review, fact-checking
    LONG_CONTEXT = "long_context"  # Large document processing


class ModelRouter:
    """
    Routes tasks to appropriate models based on capability requirements.
    
    Implements the PRP routing strategy with fallbacks and manual overrides.
    """
    
    # Default model assignments based on PRP specifications
    DEFAULT_MODELS = {
        ModelCapability.REASONING: "o1",
        ModelCapability.GENERATION: "gpt-4.1", 
        ModelCapability.VERIFICATION: "claude-3.7-sonnet",
        ModelCapability.LONG_CONTEXT: "claude-3.7-sonnet"
    }
    
    # Model provider mapping
    MODEL_PROVIDERS = {
        "o1": ModelProvider.OPENAI,
        "o3": ModelProvider.OPENAI,
        "gpt-4.1": ModelProvider.OPENAI,
        "gpt-4-turbo": ModelProvider.OPENAI,
        "claude-3.7-sonnet": ModelProvider.ANTHROPIC,
        "claude-3-opus": ModelProvider.ANTHROPIC,
        "claude-3-haiku": ModelProvider.ANTHROPIC
    }
    
    # Fallback models if primary choice unavailable
    FALLBACK_MODELS = {
        "o1": ["gpt-4.1", "claude-3.7-sonnet"],
        "gpt-4.1": ["gpt-4-turbo", "claude-3.7-sonnet"],
        "claude-3.7-sonnet": ["claude-3-opus", "gpt-4.1"],
        "o3": ["o1", "gpt-4.1"],
        "claude-3-opus": ["claude-3.7-sonnet", "gpt-4.1"]
    }
    
    def __init__(self):
        self.override_model: Optional[str] = None
        self._available_models = self._get_available_models()
    
    def _get_available_models(self) -> Dict[str, bool]:
        """Check which models are available based on API keys."""
        available = {}
        
        # Check OpenAI models
        if settings.openai_api_key:
            openai_models = ["o1", "o3", "gpt-4.1", "gpt-4-turbo"]
            for model in openai_models:
                available[model] = True
        
        # Check Anthropic models  
        if settings.anthropic_api_key:
            anthropic_models = ["claude-3.7-sonnet", "claude-3-opus", "claude-3-haiku"]
            for model in anthropic_models:
                available[model] = True
        
        return available
    
    def set_manual_override(self, model: Optional[str]):
        """Set manual model override from UI."""
        if model and model in self._available_models:
            self.override_model = model
        else:
            self.override_model = None
    
    def get_model_for_capability(
        self,
        capability: ModelCapability,
        context_length: Optional[int] = None,
        jurisdiction: JurisdictionType = JurisdictionType.DIFC
    ) -> tuple[str, ModelProvider]:
        """
        Get the best model for a specific capability.
        
        Args:
            capability: The required model capability
            context_length: Estimated context length for the task
            jurisdiction: Legal jurisdiction (may influence model choice)
            
        Returns:
            tuple[str, ModelProvider]: (model_name, provider)
        """
        # Check for manual override first
        if self.override_model:
            provider = self.MODEL_PROVIDERS.get(self.override_model, ModelProvider.OPENAI)
            return self.override_model, provider
        
        # Special case for long context tasks
        if context_length and context_length > 32000:
            capability = ModelCapability.LONG_CONTEXT
        
        # Get primary model choice
        primary_model = self.DEFAULT_MODELS.get(capability, "gpt-4.1")
        
        # Check if primary model is available
        if primary_model in self._available_models:
            provider = self.MODEL_PROVIDERS.get(primary_model, ModelProvider.OPENAI)
            return primary_model, provider
        
        # Try fallback models
        fallbacks = self.FALLBACK_MODELS.get(primary_model, [])
        for fallback in fallbacks:
            if fallback in self._available_models:
                provider = self.MODEL_PROVIDERS.get(fallback, ModelProvider.OPENAI)
                return fallback, provider
        
        # Last resort: return any available model
        for model in self._available_models:
            if self._available_models[model]:
                provider = self.MODEL_PROVIDERS.get(model, ModelProvider.OPENAI)
                return model, provider
        
        raise ValueError("No models available - check API key configuration")
    
    def get_planner_model(self) -> tuple[str, ModelProvider]:
        """Get model for planning/reasoning tasks."""
        return self.get_model_for_capability(ModelCapability.REASONING)
    
    def get_drafter_model(self, context_length: Optional[int] = None) -> tuple[str, ModelProvider]:
        """Get model for content generation/drafting."""
        if context_length and context_length > 32000:
            return self.get_model_for_capability(ModelCapability.LONG_CONTEXT)
        return self.get_model_for_capability(ModelCapability.GENERATION)
    
    def get_verifier_model(self) -> tuple[str, ModelProvider]:
        """Get model for verification/review tasks."""
        return self.get_model_for_capability(ModelCapability.VERIFICATION)
    
    def get_assistant_model(
        self,
        mode: Literal["assist", "draft"],
        context_length: Optional[int] = None
    ) -> tuple[str, ModelProvider]:
        """Get model for direct assistant queries."""
        if mode == "assist":
            # Quick responses - use generation model
            return self.get_model_for_capability(ModelCapability.GENERATION)
        elif mode == "draft":
            # Structured documents - use reasoning for planning + generation
            if context_length and context_length > 32000:
                return self.get_model_for_capability(ModelCapability.LONG_CONTEXT)
            return self.get_model_for_capability(ModelCapability.REASONING)
        else:
            return self.get_model_for_capability(ModelCapability.GENERATION)
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information about a specific model."""
        provider = self.MODEL_PROVIDERS.get(model_name, ModelProvider.OPENAI)
        available = self._available_models.get(model_name, False)
        
        # Determine capabilities
        capabilities = []
        for capability, default_model in self.DEFAULT_MODELS.items():
            if default_model == model_name:
                capabilities.append(capability.value)
        
        # Add as fallback capability
        for primary, fallbacks in self.FALLBACK_MODELS.items():
            if model_name in fallbacks:
                for capability, default_model in self.DEFAULT_MODELS.items():
                    if default_model == primary and capability.value not in capabilities:
                        capabilities.append(f"fallback_{capability.value}")
        
        return {
            "name": model_name,
            "provider": provider.value,
            "available": available,
            "capabilities": capabilities,
            "is_default": model_name in self.DEFAULT_MODELS.values(),
            "context_limit": self._get_context_limit(model_name)
        }
    
    def _get_context_limit(self, model_name: str) -> int:
        """Get approximate context limit for model."""
        limits = {
            "o1": 128000,
            "o3": 128000,
            "gpt-4.1": 128000,
            "gpt-4-turbo": 128000,
            "claude-3.7-sonnet": 200000,
            "claude-3-opus": 200000,
            "claude-3-haiku": 200000
        }
        return limits.get(model_name, 32000)
    
    def get_routing_status(self) -> Dict[str, Any]:
        """Get current routing configuration and status."""
        return {
            "available_models": {
                name: available for name, available in self._available_models.items()
            },
            "default_routing": {
                capability.value: model for capability, model in self.DEFAULT_MODELS.items()
            },
            "manual_override": self.override_model,
            "model_info": {
                name: self.get_model_info(name) 
                for name in self._available_models.keys()
            }
        }
    
    def validate_model_availability(self) -> Dict[str, Any]:
        """Validate that required models are available."""
        issues = []
        warnings = []
        
        # Check if we have at least one model from each provider
        has_openai = any(
            self.MODEL_PROVIDERS.get(model) == ModelProvider.OPENAI and available
            for model, available in self._available_models.items()
        )
        has_anthropic = any(
            self.MODEL_PROVIDERS.get(model) == ModelProvider.ANTHROPIC and available  
            for model, available in self._available_models.items()
        )
        
        if not has_openai and not has_anthropic:
            issues.append("No models available - check API key configuration")
        elif not has_openai:
            warnings.append("OpenAI models unavailable - limited to Anthropic models")
        elif not has_anthropic:
            warnings.append("Anthropic models unavailable - limited to OpenAI models")
        
        # Check primary model availability
        for capability, model in self.DEFAULT_MODELS.items():
            if not self._available_models.get(model, False):
                fallbacks = self.FALLBACK_MODELS.get(model, [])
                has_fallback = any(
                    self._available_models.get(fb, False) for fb in fallbacks
                )
                if not has_fallback:
                    issues.append(f"No available model for {capability.value} capability")
                else:
                    warnings.append(f"Primary {capability.value} model ({model}) unavailable, using fallback")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "available_count": sum(self._available_models.values()),
            "total_count": len(self._available_models)
        }


# Global router instance
model_router = ModelRouter()