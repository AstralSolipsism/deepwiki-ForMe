from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any, Iterable, Optional


logger = logging.getLogger(__name__)


def _ensure_api_importable() -> None:
    """Ensure repo root is on sys.path so `import api.*` works."""
    try:
        repo_root = Path(__file__).resolve().parents[2]
    except Exception:
        return

    api_dir = repo_root / "api"
    if not api_dir.is_dir():
        return

    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


@lru_cache(maxsize=1)
def _get_rag_class() -> Any:
    """Lazily import api.rag.RAG to avoid hard import-time failures."""
    _ensure_api_importable()
    try:
        from api.rag import RAG  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"无法导入 `api.rag.RAG`（可能缺少依赖，例如 {exc.name}）：{exc}"
        ) from exc
    return RAG


def _normalize_repo_identifier(repo_url_or_path: str) -> str:
    value = (repo_url_or_path or "").strip()
    if value.startswith(("http://", "https://")):
        return value.rstrip("/")
    return os.path.normcase(os.path.abspath(value))


def _normalize_filter(values: Optional[Iterable[str]]) -> tuple[str, ...]:
    if not values:
        return ()
    normalized = sorted({str(item).strip() for item in values if str(item).strip()})
    return tuple(normalized)


RetrieverCacheKey = tuple[
    str,  # repo_url_or_path (normalized)
    str,  # repo_type
    tuple[str, ...],  # excluded_dirs
    tuple[str, ...],  # excluded_files
    tuple[str, ...],  # included_dirs
    tuple[str, ...],  # included_files
]


@dataclass(slots=True)
class RAGManager:
    """Create and cache prepared RAG retrievers.

    Cache key includes:
        - repo_url_or_path + repo_type
        - file filter params (excluded/included dirs/files)
    """

    _cache: dict[RetrieverCacheKey, Any] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def _make_cache_key(
        self,
        repo_url_or_path: str,
        repo_type: str,
        excluded_dirs: Optional[Iterable[str]] = None,
        excluded_files: Optional[Iterable[str]] = None,
        included_dirs: Optional[Iterable[str]] = None,
        included_files: Optional[Iterable[str]] = None,
    ) -> RetrieverCacheKey:
        return (
            _normalize_repo_identifier(repo_url_or_path),
            (repo_type or "github").strip().lower(),
            _normalize_filter(excluded_dirs),
            _normalize_filter(excluded_files),
            _normalize_filter(included_dirs),
            _normalize_filter(included_files),
        )

    def get_or_create_retriever(
        self,
        repo_url_or_path: str,
        repo_type: str = "github",
        token: str | None = None,
        excluded_dirs: Optional[Iterable[str]] = None,
        excluded_files: Optional[Iterable[str]] = None,
        included_dirs: Optional[Iterable[str]] = None,
        included_files: Optional[Iterable[str]] = None,
    ) -> Any:
        key = self._make_cache_key(
            repo_url_or_path,
            repo_type,
            excluded_dirs=excluded_dirs,
            excluded_files=excluded_files,
            included_dirs=included_dirs,
            included_files=included_files,
        )

        with self._lock:
            cached = self._cache.get(key)
        if cached is not None:
            return cached

        rag_class = _get_rag_class()
        rag = rag_class()

        rag.prepare_retriever(
            repo_url_or_path,
            repo_type,
            token or "",
            list(excluded_dirs) if excluded_dirs else [],
            list(excluded_files) if excluded_files else [],
            list(included_dirs) if included_dirs else [],
            list(included_files) if included_files else [],
        )

        with self._lock:
            existing = self._cache.get(key)
            if existing is not None:
                return existing
            self._cache[key] = rag

        logger.info("Prepared and cached RAG retriever for %s", repo_url_or_path)
        return rag

    def retrieve(
        self,
        repo_url_or_path: str,
        repo_type: str,
        query: str,
        token: str | None = None,
        file_path: str | None = None,
        excluded_dirs: Optional[Iterable[str]] = None,
        excluded_files: Optional[Iterable[str]] = None,
        included_dirs: Optional[Iterable[str]] = None,
        included_files: Optional[Iterable[str]] = None,
        max_results: int = 8,
    ) -> tuple[str, list[Any]]:
        effective_query = query
        if file_path:
            effective_query = f"Contexts related to {file_path}"

        rag = self.get_or_create_retriever(
            repo_url_or_path=repo_url_or_path,
            repo_type=repo_type,
            token=token,
            excluded_dirs=excluded_dirs,
            excluded_files=excluded_files,
            included_dirs=included_dirs,
            included_files=included_files,
        )

        result = rag(effective_query)

        # RAG.call(): success -> list-like retriever output; error -> (error_response, []) tuple.
        if isinstance(result, tuple) and len(result) == 2:
            error_obj = result[0]
            message = (
                getattr(error_obj, "answer", None)
                or getattr(error_obj, "rationale", None)
                or str(error_obj)
            )
            raise ValueError(message)

        documents: list[Any] = []
        try:
            if result and getattr(result[0], "documents", None):
                documents = list(result[0].documents)
        except Exception as exc:
            raise ValueError(f"Unexpected RAG result format: {exc}") from exc

        if max_results > 0:
            documents = documents[:max_results]

        return effective_query, documents

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


@lru_cache(maxsize=1)
def get_rag_manager() -> RAGManager:
    return RAGManager()