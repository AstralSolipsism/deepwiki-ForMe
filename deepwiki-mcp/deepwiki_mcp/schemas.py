from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ToolInput(BaseModel):
    """Base class for MCP tool input schemas."""


class ToolOutput(BaseModel):
    """Base class for MCP tool output schemas."""


class ErrorOutput(ToolOutput):
    error: str = Field(..., description="Error message.")
    detail: Any | None = Field(default=None, description="Optional error details.")


class NotImplementedOutput(ToolOutput):
    message: str = Field(..., description="Not implemented message.")


class AskRepoInput(ToolInput):
    """Input schema for ask_repo tool."""

    repo_url: str = Field(..., description="仓库URL。")
    repo_type: str = Field(default="github", description="仓库类型：github/gitlab/bitbucket。")
    token: Optional[str] = Field(default=None, description="私有仓库 token（可选）。")
    messages: List[dict] = Field(
        ...,
        description='对话消息列表，格式示例：[{"role": "user", "content": "..."}]。',
    )

    file_path: Optional[str] = Field(default=None, description="可选：聚焦某文件路径。")
    provider: str = Field(
        default="google",
        description="模型提供商（例如 google/openai/openrouter/ollama）。",
    )
    model: Optional[str] = Field(default=None, description="模型名（可选）。")
    language: str = Field(default="en", description="语言（例如 en/zh/ja）。")

    excluded_dirs: Optional[List[str]] = Field(
        default=None, description="排除目录（数组，发送前转为换行分隔字符串）。"
    )
    excluded_files: Optional[List[str]] = Field(
        default=None, description="排除文件（数组，发送前转为换行分隔字符串）。"
    )
    included_dirs: Optional[List[str]] = Field(
        default=None, description="仅包含目录（数组，发送前转为换行分隔字符串）。"
    )
    included_files: Optional[List[str]] = Field(
        default=None, description="仅包含文件（数组，发送前转为换行分隔字符串）。"
    )


class AskRepoOutput(ToolOutput):
    """Output schema for ask_repo tool."""

    answer: str = Field(..., description="完整答案文本。")
    backend_endpoint: str = Field(
        default="POST /chat/completions/stream",
        description="DeepWiki 后端接口。",
    )


class RetrieveContextInput(ToolInput):
    """Input schema for retrieve_context tool."""

    repo_url_or_path: str = Field(..., description="仓库URL或本地路径。")
    repo_type: str = Field(default="github", description="仓库类型：github/gitlab/bitbucket。")
    token: Optional[str] = Field(default=None, description="私有仓库 token（可选）。")

    query: str = Field(..., description="检索查询。")
    file_path: Optional[str] = Field(default=None, description="可选：仅聚焦某文件路径。")

    excluded_dirs: Optional[List[str]] = Field(default=None, description="排除目录（数组）。")
    excluded_files: Optional[List[str]] = Field(default=None, description="排除文件（数组）。")
    included_dirs: Optional[List[str]] = Field(default=None, description="仅包含目录（数组）。")
    included_files: Optional[List[str]] = Field(default=None, description="仅包含文件（数组）。")

    max_results: int = Field(default=8, ge=1, description="最大返回结果数。")


class DocumentMeta(BaseModel):
    type: Optional[str] = Field(default=None, description="文档类型（例如 py/md 等）。")
    is_code: Optional[bool] = Field(default=None, description="是否为代码。")
    is_implementation: Optional[bool] = Field(default=None, description="是否为实现代码（非测试/示例等）。")
    title: Optional[str] = Field(default=None, description="文档标题。")
    token_count: Optional[int] = Field(default=None, description="token 数量估算。")


class RetrievedDocument(BaseModel):
    file_path: str = Field(..., description="仓库内相对路径。")
    text: str = Field(..., description="文档片段内容。")
    meta: DocumentMeta = Field(..., description="文档元数据。")


class RetrieveContextOutput(ToolOutput):
    """Output schema for retrieve_context tool."""

    query: str = Field(..., description="实际用于检索的查询。")
    documents: List[RetrievedDocument] = Field(
        default_factory=list, description="检索到的文档片段列表。"
    )


class ListProcessedProjectsInput(ToolInput):
    """Input schema for list_processed_projects tool."""

    pass


class ProcessedProjectEntry(BaseModel):
    id: str = Field(..., description="项目ID（缓存文件名）。")
    owner: str = Field(..., description="仓库 owner。")
    repo: str = Field(..., description="仓库 repo。")
    name: str = Field(..., description="展示名（通常为 owner/repo）。")
    repo_type: str = Field(..., description="仓库类型（github/gitlab/bitbucket 等）。")
    submittedAt: int = Field(..., description="提交时间戳（毫秒）。")
    language: str = Field(..., description="语言（从缓存文件名提取）。")


class ListProcessedProjectsOutput(ToolOutput):
    """Output schema for list_processed_projects tool."""

    projects: List[ProcessedProjectEntry] = Field(
        default_factory=list, description="已处理项目列表。"
    )


class GetLocalRepoStructureInput(ToolInput):
    """Input schema for get_local_repo_structure tool."""

    path: str = Field(..., description="本地仓库路径。")


class GetLocalRepoStructureOutput(ToolOutput):
    """Output schema for get_local_repo_structure tool output."""

    file_tree: str = Field(..., description="仓库文件树（文本）。")
    readme: str = Field(..., description="README 内容（若有）。")