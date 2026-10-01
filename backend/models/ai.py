"""Pydantic request and response models for AI text generation."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class AIGenerateRequest(BaseModel):
    """Payload for text generation request."""

    prompt: str = Field(
        ...,
        description="The input text or prompt to send to the AI provider.",
        min_length=1,
    )
    system_instruction: Optional[str] = Field(
        default=None,
        description="Optional system instruction / role guidance for the model.",
    )
    model: Optional[str] = Field(
        default=None,
        description="Specific model to use (e.g. 'gemini-3.8-flash'). Defaults to provider standard.",
    )
    provider: Optional[str] = Field(
        default="gemini",
        description="AI provider identifier (e.g. 'gemini', 'groq', 'openrouter', 'mistral', 'cohere', 'huggingface', 'openai', 'custom').",
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature.",
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Maximum tokens to generate.",
    )
    timeout: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=300.0,
        description="Timeout in seconds for this generation request.",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Optional per-request API key (never persisted, kept strictly in-memory for this request).",
    )
    base_url: Optional[str] = Field(
        default=None,
        description="Optional endpoint base URL (used for custom OpenAI-compatible endpoints).",
    )
    fallback_provider: Optional[str] = Field(
        default=None,
        description="Optional explicit fallback provider ID if the primary provider encounters an upstream/timeout failure.",
    )
    fallback_model: Optional[str] = Field(
        default=None,
        description="Optional model ID to use if falling back to the fallback provider.",
    )
    retries: Optional[int] = Field(
        default=None,
        ge=0,
        le=3,
        description="Optional override for retry attempts on transient upstream errors.",
    )

    @field_validator("prompt")
    @classmethod
    def validate_prompt_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Prompt cannot be empty or solely whitespace.")
        return stripped


class AIGenerateResponse(BaseModel):
    """Predictable response contract for successful AI generation."""

    success: bool = Field(default=True, description="Indicates request success.")
    provider: str = Field(..., description="Provider that processed the request.")
    model: str = Field(..., description="Exact model employed.")
    content: str = Field(..., description="Generated text content.")
    fallback_used: Optional[bool] = Field(default=None, description="Whether an explicit fallback provider was engaged.")
    original_provider: Optional[str] = Field(default=None, description="Original primary provider if fallback occurred.")
    usage: Optional[Dict[str, Any]] = Field(default=None, description="Optional token usage statistics.")


class AIErrorDetail(BaseModel):
    """Structured error descriptor."""

    code: str = Field(..., description="Machine-readable error code.")
    message: str = Field(..., description="Human-readable error description.")
    provider: Optional[str] = Field(default=None, description="Provider that raised the error.")


class AIErrorResponse(BaseModel):
    """Structured response contract for AI generation errors."""

    success: bool = Field(default=False, description="Always false on error.")
    error: AIErrorDetail
