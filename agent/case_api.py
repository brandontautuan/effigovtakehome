import logging
import os
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class CaseApiError(Exception):
    """Raised when the FastAPI case service cannot complete a request."""


class CaseApiClient:
    """Small HTTP client for the existing FastAPI case endpoints."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("BACKEND_URL", "http://127.0.0.1:8000")).rstrip(
            "/"
        )

    async def create_case(
        self, name: str, phone: str, issue_type: str, description: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/cases",
            json={
                "name": name,
                "phone": phone,
                "issue_type": issue_type,
                "description": description,
                "source": "voice_agent",
            },
        )

    async def lookup_case(
        self, case_number: str | None = None, phone: str | None = None
    ) -> list[dict[str, Any]]:
        params = {
            key: value
            for key, value in {"case_number": case_number, "phone": phone}.items()
            if value
        }
        response = await self._request("GET", "/cases/lookup", params=params)
        if not isinstance(response, list):
            raise CaseApiError("The case service returned an unexpected lookup response.")
        return response

    async def update_case(self, case_id: int, updates: dict[str, str]) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/cases/{case_id}",
            json={**updates, "source": "voice_agent"},
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
                response = await client.request(method, path, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as error:
            logger.warning(
                "Case API returned status %s for %s %s",
                error.response.status_code,
                method,
                path,
            )
            raise CaseApiError("The case service could not complete that request.") from error
        except httpx.HTTPError as error:
            logger.warning("Case API request failed for %s %s: %s", method, path, error)
            raise CaseApiError("The case service is unavailable right now.") from error
