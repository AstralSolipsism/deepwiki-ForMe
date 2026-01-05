from __future__ import annotations

import asyncio
from typing import Any

from mcp.types import CallToolResult, TextContent
from pydantic import ValidationError

from deepwiki_mcp.rag_backend import get_rag_manager
from deepwiki_mcp.schemas import (
    DocumentMeta,
    ErrorOutput,
    RetrieveContextInput,
    RetrieveContextOutput,
    RetrievedDocument,
)


def _to_retrieved_document(document: Any) -> RetrievedDocument:
    meta_data = getattr(document, "meta_data", None) or {}
    file_path = meta_data.get("file_path") or "unknown"
    text = getattr(document, "text", "") or ""
    meta = DocumentMeta(
        type=meta_data.get("type"),
        is_code=meta_data.get("is_code"),
        is_implementation=meta_data.get("is_implementation"),
        title=meta_data.get("title"),
        token_count=meta_data.get("token_count"),
    )
    return RetrievedDocument(file_path=str(file_path), text=str(text), meta=meta)


async def retrieve_context(
    repo_url_or_path: str,
    query: str,
    repo_type: str = "github",
    token: str | None = None,
    file_path: str | None = None,
    excluded_dirs: list[str] | None = None,
    excluded_files: list[str] | None = None,
    included_dirs: list[str] | None = None,
    included_files: list[str] | None = None,
    max_results: int = 8,
) -> CallToolResult:
    """Retrieve local RAG context for a repository and query."""
    try:
        tool_input = RetrieveContextInput.model_validate(
            {
                "repo_url_or_path": repo_url_or_path,
                "repo_type": repo_type,
                "token": token,
                "query": query,
                "file_path": file_path,
                "excluded_dirs": excluded_dirs,
                "excluded_files": excluded_files,
                "included_dirs": included_dirs,
                "included_files": included_files,
                "max_results": max_results,
            }
        )
    except ValidationError as exc:
        error_text = f"Invalid retrieve_context input: {exc}"
        return CallToolResult(
            content=[TextContent(type="text", text=error_text)],
            structuredContent=ErrorOutput(error=error_text, detail=exc.errors()).model_dump(),
            isError=True,
        )

    manager = get_rag_manager()
    try:
        effective_query, docs = await asyncio.to_thread(
            manager.retrieve,
            repo_url_or_path=tool_input.repo_url_or_path,
            repo_type=tool_input.repo_type,
            query=tool_input.query,
            token=tool_input.token,
            file_path=tool_input.file_path,
            excluded_dirs=tool_input.excluded_dirs,
            excluded_files=tool_input.excluded_files,
            included_dirs=tool_input.included_dirs,
            included_files=tool_input.included_files,
            max_results=tool_input.max_results,
        )
    except Exception as exc:
        error_text = f"Error retrieving context: {exc}"
        return CallToolResult(
            content=[TextContent(type="text", text=error_text)],
            structuredContent=ErrorOutput(error=error_text).model_dump(),
            isError=True,
        )

    documents = [_to_retrieved_document(doc) for doc in docs]
    tool_output = RetrieveContextOutput(query=effective_query, documents=documents)

    if documents:
        parts: list[str] = []
        for idx, doc in enumerate(documents, start=1):
            parts.append(f"{idx}. {doc.file_path}\n{doc.text}")
        content_text = "\n\n".join(parts)
    else:
        content_text = "No documents retrieved from RAG."

    return CallToolResult(
        content=[TextContent(type="text", text=content_text)],
        structuredContent=tool_output.model_dump(),
    )