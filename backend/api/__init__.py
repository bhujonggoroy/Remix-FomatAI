"""FormatAI API Layer.
Contains FastAPI route definitions and HTTP endpoint controllers.
"""
from backend.api.routes.health import router as health_router

__all__ = ["health_router"]
