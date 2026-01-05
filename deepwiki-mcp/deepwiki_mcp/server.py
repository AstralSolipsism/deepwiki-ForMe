from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from deepwiki_mcp.settings import get_settings
from deepwiki_mcp.tools import (
    ask_repo,
    get_local_repo_structure,
    list_processed_projects,
    retrieve_context,
)


def create_server() -> FastMCP:
    """Create and configure the DeepWiki MCP server (Streamable HTTP, stateless)."""
    settings = get_settings()

    mcp = FastMCP(
        "DeepWiki MCP",
        stateless_http=True,
        json_response=True,
        streamable_http_path=settings.mcp_path,
    )

    # Configure listen host/port (documented via ctx.fastmcp.settings.*)
    mcp.settings.host = settings.mcp_host
    mcp.settings.port = settings.mcp_port

    # Register tools (placeholders for now)
    mcp.tool()(ask_repo)
    mcp.tool()(retrieve_context)
    mcp.tool()(list_processed_projects)
    mcp.tool()(get_local_repo_structure)

    return mcp


def main() -> None:
    """CLI entry point."""
    mcp = create_server()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()