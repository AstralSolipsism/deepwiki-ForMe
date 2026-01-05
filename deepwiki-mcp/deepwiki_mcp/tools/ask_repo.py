from __future__ import annotations

from typing import Any

from mcp.types import CallToolResult, TextContent
from pydantic import ValidationError

from deepwiki_mcp.http_backend import DeepWikiAPIError, DeepWikiHTTPBackend
from deepwiki_mcp.schemas import AskRepoInput, AskRepoOutput, ErrorOutput


def _join_lines(values: list[str] | None) -> str | None:
    if not values:
        return None
    items = [str(value).strip() for value in values if str(value).strip()]
    if not items:
        return None
    return "\n".join(items)


def _build_payload(tool_input: AskRepoInput) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "repo_url": tool_input.repo_url,
        "type": tool_input.repo_type,
        "messages": tool_input.messages,
        "provider": tool_input.provider,
        "language": tool_input.language,
    }

    if tool_input.token:
        payload["token"] = tool_input.token
    if tool_input.model:
        payload["model"] = tool_input.model
    if tool_input.file_path:
        payload["filePath"] = tool_input.file_path

    excluded_dirs = _join_lines(tool_input.excluded_dirs)
    if excluded_dirs is not None:
        payload["excluded_dirs"] = excluded_dirs

    excluded_files = _join_lines(tool_input.excluded_files)
    if excluded_files is not None:
        payload["excluded_files"] = excluded_files

    included_dirs = _join_lines(tool_input.included_dirs)
    if included_dirs is not None:
        payload["included_dirs"] = included_dirs

    included_files = _join_lines(tool_input.included_files)
    if included_files is not None:
        payload["included_files"] = included_files

    return payload


async def ask_repo(
    repo_url: str,
    messages: list[dict],
    repo_type: str = "github",
    token: str | None = None,
    file_path: str | None = None,
    provider: str = "google",
    model: str | None = None,
    language: str = "en",
    excluded_dirs: list[str] | None = None,
    excluded_files: list[str] | None = None,
    included_dirs: list[str] | None = None,
    included_files: list[str] | None = None,
) -> CallToolResult:
    """Ask questions about a repository via DeepWiki backend (stream -> full answer)."""
    try:
        tool_input = AskRepoInput(
            repo_url=repo_url,
            repo_type=repo_type,
            token=token,
            messages=messages,
            file_path=file_path,
            provider=provider,
            model=model,
            language=language,
            excluded_dirs=excluded_dirs,
            excluded_files=excluded_files,
            included_dirs=included_dirs,
            included_files=included_files,
        )
    except ValidationError as exc:
        error_text = f"Invalid ask_repo input: {exc}"
        return CallToolResult(
            content=[TextContent(type="text", text=error_text)],
            structuredContent=ErrorOutput(error=error_text, detail=exc.errors()).model_dump(),
            isError=True,
        )

    payload = _build_payload(tool_input)
    answer_parts: list[str] = []

    try:
        async with DeepWikiHTTPBackend() as backend:
            async for chunk in backend.stream_chat_completions(payload):
                answer_parts.append(chunk)
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

    answer = "".join(answer_parts)
    tool_output = AskRepoOutput(answer=answer)

    return CallToolResult(
        content=[TextContent(type="text", text=tool_output.answer)],
        structuredContent=tool_output.model_dump(),
    )