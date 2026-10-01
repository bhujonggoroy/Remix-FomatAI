"""Pydantic schemas for AI providers, models, and adapter validation."""

from typing import List, Optional
from pydantic import BaseModel, Field


class AIModelInfo(BaseModel):
    """Information regarding a specific AI model."""

    id: str = Field(..., description="Unique model identifier")
    name: str = Field(..., description="Human-readable model name")
    context_window: Optional[int] = Field(default=None, description="Context window size in tokens")
    supports_formatting: bool = Field(default=True, description="Whether model supports document formatting")
    description: Optional[str] = Field(default=None, description="Brief description or recommended usage")
    is_discovered: bool = Field(default=False, description="Whether dynamically discovered from upstream API")


class AIProviderInfo(BaseModel):
    """Metadata regarding an integrated AI provider adapter."""

    id: str = Field(..., description="Provider identifier (e.g. 'gemini', 'groq', 'openai')")
    name: str = Field(..., description="Provider display name")
    is_available: bool = Field(default=False, description="Whether valid API configuration exists")
    is_enabled: bool = Field(default=True, description="Whether provider is enabled for generation requests")
    default_model: str = Field(..., description="Default model ID for this provider")
    supported_models: List[AIModelInfo] = Field(default_factory=list, description="Supported or discovered models")
    supports_model_discovery: bool = Field(default=True, description="Whether provider supports dynamic discovery")
    requires_base_url: bool = Field(default=False, description="Whether provider requires an endpoint base URL")
    base_url: Optional[str] = Field(default=None, description="Active or configured endpoint base URL")


class ProviderValidationRequest(BaseModel):
    """Payload to validate configuration or credentials for a provider."""

    api_key: Optional[str] = Field(default=None, description="Optional override API key to validate")
    base_url: Optional[str] = Field(default=None, description="Optional custom endpoint base URL")


class ProviderValidationResult(BaseModel):
    """Response detailing provider configuration and connectivity validity."""

    provider_id: str = Field(..., description="Target provider identifier")
    is_valid: bool = Field(..., description="Whether credentials and connection are functional")
    message: str = Field(..., description="Validation outcome description or safe error detail")
    latency_ms: Optional[float] = Field(default=None, description="Round-trip response latency in milliseconds")
    discovered_models_count: Optional[int] = Field(default=None, description="Number of models discovered")


class ProviderToggleRequest(BaseModel):
    """Request payload to enable or disable an AI provider."""

    enabled: bool = Field(..., description="True to enable provider, False to disable")
