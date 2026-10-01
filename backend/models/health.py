"""Pydantic models for health check and root endpoints."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response contract matching exact requirements."""
    status: str = Field(..., description="Operational status, e.g. 'ok'")
    service: str = Field(..., description="Service identifier, e.g. 'FormatAI'")
    backend: str = Field(..., description="Backend technology indicator, e.g. 'python'")


class RootResponse(BaseModel):
    """Root endpoint response contract."""
    status: str
    service: str
    backend: str
    message: str
    docs_url: str
    version: str
