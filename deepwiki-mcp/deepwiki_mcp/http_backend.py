from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

import httpx

from deepwiki_mcp.settings import Settings, get_settings


@dataclass(slots=True)
class DeepWikiAPIError(RuntimeError):
    status_code: int | None
    message: str
    response_text: str | None = None

    def __str__(self) -> str:  # pragma: no cover
        base = self.message
        if self.status_code is not None:
            base = f"[{self.status_code}] {base}"
        return base


class DeepWikiHTTPBackend:
    """HTTP bridge to the existing DeepWiki FastAPI backend."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "DeepWikiHTTPBackend":
        self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    def _ensure_client(self) -> None:
        if self._client is not None:
            return

        timeout = httpx.Timeout(timeout=float(self._settings.api_timeout))
        self._client = httpx.AsyncClient(
            base_url=self._settings.api_base_url,
            timeout=timeout,
            headers={
                "Accept": "application/json, text/event-stream;q=0.9, */*;q=0.8",
            },
        )

    async def aclose(self) -> None:
        if self._client is None:
            return
        await self._client.aclose()
        self._client = None

    def _raise_for_status(self, response: httpx.Response, body_text: str | None) -> None:
        if 200 <= response.status_code < 300:
            return

        message = response.reason_phrase
        response_text = body_text

        try:
            payload = response.json()
            if isinstance(payload, dict):
                message = (
                    payload.get("detail")
                    or payload.get("error")
                    or payload.get("message")
                    or message
                )
        except Exception:
            pass

        raise DeepWikiAPIError(
            status_code=response.status_code,
            message=str(message),
            response_text=response_text,
        )

    async def stream_chat_completions(self, payload: dict[str, Any]) -> AsyncIterator[str]:
        """Stream text chunks from `/chat/completions/stream`."""
        self._ensure_client()
        assert self._client is not None

        async with self._client.stream(
            "POST",
            "/chat/completions/stream",
            json=payload,
        ) as response:
            if response.status_code >= 400:
                body = await response.aread()
                text = body.decode("utf-8", errors="replace")
                self._raise_for_status(response, text)

            async for chunk in response.aiter_text():
                if chunk:
                    yield chunk

    async def get_processed_projects(self) -> Any:
        """GET `/api/processed_projects`."""
        self._ensure_client()
        assert self._client is not None

        response = await self._client.get("/api/processed_projects")
        text = response.text if response.status_code >= 400 else None
        self._raise_for_status(response, text)
        return response.json()

    async def get_local_repo_structure(self, path: str) -> dict[str, Any]:
        """GET `/local_repo/structure?path=...`."""
        self._ensure_client()
        assert self._client is not None

        response = await self._client.get("/local_repo/structure", params={"path": path})
        text = response.text if response.status_code >= 400 else None
        self._raise_for_status(response, text)
        payload = response.json()
        if not isinstance(payload, dict):
            raise DeepWikiAPIError(
                status_code=response.status_code,
                message="Unexpected response type from /local_repo/structure (expected JSON object).",
                response_text=response.text,
            )
        return payload