from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """DeepWiki MCP server settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mcp_host: str = Field(default="127.0.0.1", validation_alias="DEEPWIKI_MCP_HOST")
    mcp_port: int = Field(default=8000, validation_alias="DEEPWIKI_MCP_PORT")
    mcp_path: str = Field(default="/mcp", validation_alias="DEEPWIKI_MCP_PATH")

    api_base_url: str = Field(default="http://localhost:8001", validation_alias="DEEPWIKI_API_BASE_URL")
    api_timeout: int = Field(default=300, validation_alias="DEEPWIKI_API_TIMEOUT")

    @field_validator("mcp_path")
    @classmethod
    def _normalize_mcp_path(cls, value: str) -> str:
        value = value.strip()
        if not value:
            return "/mcp"
        if not value.startswith("/"):
            value = "/" + value
        if value != "/":
            value = value.rstrip("/")
        return value

    @field_validator("api_base_url")
    @classmethod
    def _normalize_api_base_url(cls, value: str) -> str:
        value = value.strip()
        return value.rstrip("/")

    @field_validator("api_timeout")
    @classmethod
    def _validate_api_timeout(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("DEEPWIKI_API_TIMEOUT must be a positive integer (seconds).")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()