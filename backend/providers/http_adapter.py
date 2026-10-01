"""Shared HTTP client utility for REST/OpenAI-compatible AI provider adapters.

Provides isolated connection management, timeouts, transient retries, and normalized error mapping.
Never leaks API keys or bearer tokens in errors or logs.
"""

import time
from typing import Any, Dict, List, Optional
import httpx
from backend.core.logging import logger
from backend.providers.base import (
    ProviderAuthError,
    ProviderConfigError,
    ProviderModelNotFoundError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUpstreamError,
    sanitize_credentials,
)


class ProviderHTTPClient:
    """Isolated HTTP client for an individual AI provider adapter."""

    def __init__(
        self,
        provider_id: str,
        base_url: str,
        api_key: Optional[str] = None,
        default_headers: Optional[Dict[str, str]] = None,
        auth_header_format: str = "Bearer {key}",
    ):
        self.provider_id = provider_id
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.auth_header_format = auth_header_format
        self._default_headers = default_headers or {}

    def _build_headers(self, override_key: Optional[str] = None) -> Dict[str, str]:
        headers = dict(self._default_headers)
        headers.setdefault("Content-Type", "application/json")
        headers.setdefault("Accept", "application/json")

        key = override_key or self.api_key
        if key:
            if "{key}" in self.auth_header_format:
                headers["Authorization"] = self.auth_header_format.format(key=key)
            else:
                headers["Authorization"] = f"Bearer {key}"

        return headers

    def _extract_error_message(self, response: httpx.Response) -> str:
        """Extracts human-readable message from JSON or text error response."""
        try:
            data = response.json()
            if isinstance(data, dict):
                # Common shapes: {"error": {"message": "..."}}, {"error": "..."}, {"message": "..."}, {"detail": "..."}
                err = data.get("error")
                if isinstance(err, dict) and "message" in err:
                    return str(err["message"])
                if isinstance(err, str):
                    return err
                if "message" in data:
                    return str(data["message"])
                if "detail" in data:
                    return str(data["detail"])
        except Exception:
            pass

        text = response.text.strip()
        if text:
            return text[:300]
        return f"HTTP {response.status_code}: {response.reason_phrase}"

    def request(
        self,
        method: str,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
        retries: int = 1,
        override_key: Optional[str] = None,
        override_base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes HTTP request with timeout, retries on transient errors, and normalized error mapping."""
        base = (override_base_url or self.base_url).rstrip("/")
        url = f"{base}/{path.lstrip('/')}"
        headers = self._build_headers(override_key=override_key)

        active_key = override_key or self.api_key
        sensitive_keys = [active_key] if active_key else []

        attempts = max(1, retries + 1)
        last_exception: Optional[Exception] = None

        for attempt in range(attempts):
            try:
                with httpx.Client(
                    timeout=httpx.Timeout(timeout, connect=min(10.0, timeout)),
                    follow_redirects=True,
                ) as client:
                    response = client.request(
                        method=method,
                        url=url,
                        json=json_body,
                        params=params,
                        headers=headers,
                    )

                # Check HTTP status
                if response.is_success:
                    try:
                        return response.json()
                    except Exception as json_err:
                        raise ProviderUpstreamError(
                            message=f"Invalid JSON response from {self.provider_id}: {json_err}",
                            provider=self.provider_id,
                        )

                # Upstream error handling
                status_code = response.status_code
                error_msg = self._extract_error_message(response)
                safe_msg = sanitize_credentials(error_msg, sensitive_keys)

                if status_code in (401, 403):
                    raise ProviderAuthError(
                        message=f"{self.provider_id} authentication failed: {safe_msg}",
                        provider=self.provider_id,
                    )
                elif status_code == 404:
                    raise ProviderModelNotFoundError(
                        message=f"{self.provider_id} resource/model not found: {safe_msg}",
                        provider=self.provider_id,
                    )
                elif status_code == 429:
                    raise ProviderRateLimitError(
                        message=f"{self.provider_id} rate limit exceeded: {safe_msg}",
                        provider=self.provider_id,
                    )
                elif status_code in (500, 502, 503, 504):
                    # Transient server error - eligible for retry if attempts remain
                    if attempt < attempts - 1:
                        sleep_time = 0.5 * (2**attempt)
                        logger.warning(
                            f"{self.provider_id} transient upstream error ({status_code}). Retrying in {sleep_time}s..."
                        )
                        time.sleep(sleep_time)
                        continue
                    raise ProviderUpstreamError(
                        message=f"{self.provider_id} upstream error ({status_code}): {safe_msg}",
                        provider=self.provider_id,
                    )
                else:
                    raise ProviderUpstreamError(
                        message=f"{self.provider_id} request failed with status {status_code}: {safe_msg}",
                        provider=self.provider_id,
                    )

            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as exc:
                if attempt < attempts - 1:
                    sleep_time = 0.5 * (2**attempt)
                    time.sleep(sleep_time)
                    continue
                raise ProviderTimeoutError(
                    message=f"{self.provider_id} request timed out after {timeout}s.",
                    provider=self.provider_id,
                ) from exc

            except (httpx.ConnectError, httpx.NetworkError) as exc:
                if attempt < attempts - 1:
                    sleep_time = 0.5 * (2**attempt)
                    time.sleep(sleep_time)
                    continue
                safe_exc = sanitize_credentials(str(exc), sensitive_keys)
                raise ProviderUpstreamError(
                    message=f"Failed to connect to {self.provider_id} at {base}: {safe_exc}",
                    provider=self.provider_id,
                ) from exc

            except (
                ProviderAuthError,
                ProviderModelNotFoundError,
                ProviderRateLimitError,
                ProviderConfigError,
                ProviderTimeoutError,
                ProviderUpstreamError,
            ):
                raise

            except Exception as exc:
                safe_exc = sanitize_credentials(str(exc), sensitive_keys)
                raise ProviderUpstreamError(
                    message=f"Unexpected error in {self.provider_id} client: {safe_exc}",
                    provider=self.provider_id,
                ) from exc

        # If loops terminates unexpectedly
        raise ProviderUpstreamError(
            message=f"{self.provider_id} call failed after {attempts} attempts.",
            provider=self.provider_id,
        )
