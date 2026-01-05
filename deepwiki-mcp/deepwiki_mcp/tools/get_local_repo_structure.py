from __future__ import annotations

from mcp.types import CallToolResult, TextContent
from pydantic import ValidationError

from deepwiki_mcp.http_backend import DeepWikiAPIError, DeepWikiHTTPBackend
from deepwiki_mcp.schemas import (
    ErrorOutput,
    GetLocalRepoStructureInput,
    GetLocalRepoStructureOutput,
)


async def get_local_repo_structure(path: str) -> CallToolResult:
    """Get local repository structure (file tree + README) via DeepWiki backend."""
    try:
        tool_input = GetLocalRepoStructureInput.model_validate({"path": path})
    except ValidationError as exc:
        error_text = f"Invalid get_local_repo_structure input: {exc}"
        return CallToolResult(
            content=[TextContent(type="text", text=error_text)],
            structuredContent=ErrorOutput(error=error_text, detail=exc.errors()).model_dump(),
            isError=True,
        )

    if not tool_input.path.strip():
        error_text = "Invalid get_local_repo_structure input: path cannot be empty."
        return CallToolResult(
            content=[TextContent(type="text", text=error_text)],
            structuredContent=ErrorOutput(error=error_text).model_dump(),
            isError=True,
        )

    try:
        async with DeepWikiHTTPBackend() as backend:
            payload = await backend.get_local_repo_structure(tool_input.path)
    except DeepWikiAPIError as exc:
        error_text = str(exc)
        return CallToolResult(
            content=[TextContent(type="text", text=error_text)],
            structuredContent=ErrorOutput(
                error=error_text,
                detail={"status_code": exc.status_code, "response_text": exc.response_text},
            ).model_dump(),
            isError=True,
        )
    except Exception as exc:  # pragma: no cover
        error_text = f"Unexpected error calling backend: {exc}"
        return CallToolResult(
            content=[TextContent(type="text", text=error_text)],
            structuredContent=ErrorOutput(error=error_text).model_dump(),
            isError=True,
        )

    try:
        tool_output = GetLocalRepoStructureOutput.model_validate(payload)
    except ValidationError as exc:
        error_text = f"Invalid get_local_repo_structure backend response: {exc}"
        return CallToolResult(
            content=[TextContent(type="text", text=error_text)],
            structuredContent=ErrorOutput(error=error_text, detail=exc.errors()).model_dump(),
            isError=True,
        )

    parts: list[str] = []
    parts.append("File tree:\n" + (tool_output.file_tree or ""))
    if tool_output.readme and tool_output.readme.strip():
        parts.append("README:\n" + tool_output.readme)
    else:
        parts.append("README: (empty)")

    content_text = "\n\n".join(parts)

    return CallToolResult(
        content=[TextContent(type="text", text=content_text)],
        structuredContent=tool_output.model_dump(),
    )