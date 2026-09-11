"""Async HTTP adapter between the LiveKit agent and the FastAPI case service."""

import logging
import os
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class CaseApiError(Exception):
    """Raised when the FastAPI case service cannot complete a request."""


class CaseApiClient:
    """Small HTTP client for the existing FastAPI case endpoints.

    Centralizing requests keeps backend URLs, timeouts, and safe user-facing
    failure messages out of the agent's conversational logic.
    """

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

    async def create_call(self) -> dict[str, Any]:
        return await self._request("POST", "/calls", json={})

    async def add_transcript(
        self, call_id: int, role: str, content: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/calls/{call_id}/transcript",
            json={"role": role, "content": content},
        )

    async def update_call(self, call_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        return await self._request("PATCH", f"/calls/{call_id}", json=updates)

    async def create_call_topic(
        self, call_id: int, topic: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request("POST", f"/calls/{call_id}/topics", json=topic)

    async def update_call_topic(
        self, topic_id: int, updates: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request("PATCH", f"/call-topics/{topic_id}", json=updates)

    async def create_service_request(
        self, call_id: int | None, description: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/service-requests",
            json={"call_id": call_id, "description": description},
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

    async def lookup_service_schedule(self, city: str) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
                response = await client.get("/service-info/schedule", params={"city": city})
                if response.status_code == 404:
                    return response.json()
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as error:
            logger.warning("Service schedule request failed for city %s: %s", city, error)
            raise CaseApiError("The service information is unavailable right now.") from error

    async def update_case(self, case_id: int, updates: dict[str, str]) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/cases/{case_id}",
            json={**updates, "source": "voice_agent"},
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make one bounded request without exposing backend details to residents."""
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
