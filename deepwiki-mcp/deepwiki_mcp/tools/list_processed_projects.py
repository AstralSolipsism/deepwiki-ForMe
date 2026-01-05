from __future__ import annotations

from mcp.types import CallToolResult, TextContent
from pydantic import ValidationError

from deepwiki_mcp.http_backend import DeepWikiAPIError, DeepWikiHTTPBackend
from deepwiki_mcp.schemas import ErrorOutput, ListProcessedProjectsOutput, ProcessedProjectEntry


async def list_processed_projects() -> CallToolResult:
    """List processed projects from DeepWiki backend cache via HTTP."""
    try:
        async with DeepWikiHTTPBackend() as backend:
            payload = await backend.get_processed_projects()
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

    if not isinstance(payload, list):
        error_text = (
            "Unexpected response type from /api/processed_projects (expected JSON array)."
        )
        return CallToolResult(
            content=[TextContent(type="text", text=error_text)],
            structuredContent=ErrorOutput(error=error_text, detail={"response": payload}).model_dump(),
            isError=True,
        )

    try:
        projects = [ProcessedProjectEntry.model_validate(item) for item in payload]
    except ValidationError as exc:
        error_text = f"Invalid processed project entry: {exc}"
        return CallToolResult(
            content=[TextContent(type="text", text=error_text)],
            structuredContent=ErrorOutput(error=error_text, detail=exc.errors()).model_dump(),
            isError=True,
        )

    tool_output = ListProcessedProjectsOutput(projects=projects)

    if projects:
        lines: list[str] = []
        for idx, project in enumerate(projects, start=1):
            lines.append(
                f"{idx}. {project.name} ({project.repo_type}, {project.language}) - {project.submittedAt}"
            )
        content_text = "\n".join(lines)
    else:
        content_text = "No processed projects returned from backend."

    return CallToolResult(
        content=[TextContent(type="text", text=content_text)],
        structuredContent=tool_output.model_dump(),
    )