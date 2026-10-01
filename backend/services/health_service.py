"""Health check and diagnostics service logic."""

from backend.core.config import Settings
from backend.core.logging import logger
from backend.models.health import HealthResponse, RootResponse


class HealthService:
    """Encapsulates health verification and system status business logic."""

    def __init__(self, settings: Settings):
        self._settings = settings

    def get_health_status(self) -> HealthResponse:
        """Evaluates system health and returns formatted HealthResponse."""
        logger.debug("Executing health check verification.")
        return HealthResponse(
            status="ok",
            service=self._settings.APP_NAME,
            backend="python",
        )

    def get_root_status(self) -> RootResponse:
        """Returns root welcome and capability information."""
        return RootResponse(
            status="online",
            service=self._settings.APP_NAME,
            backend="Python FastAPI",
            message=f"{self._settings.APP_NAME} Python FastAPI Backend is running successfully.",
            docs_url="/docs",
            version=self._settings.APP_VERSION,
        )
