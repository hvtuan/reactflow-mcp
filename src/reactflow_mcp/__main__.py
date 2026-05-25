"""Entry point: `python -m reactflow_mcp` or `reactflow-mcp`.

Transport selection via env:
    MCP_TRANSPORT=stdio              (default — Claude Code, Cursor, etc.)
    MCP_TRANSPORT=streamable-http    (HTTP/JSON-RPC, for Coolify/web deploy)
    MCP_TRANSPORT=sse                (legacy SSE — only if a client specifically requires it)

When using streamable-http we wrap FastMCP's ASGI app with a method
dispatcher so GET requests render an HTML landing page (description,
tool list, MCP client config snippet) while POST / DELETE / OPTIONS
hit the MCP protocol handler underneath.
"""

from __future__ import annotations

import os
import sys

from reactflow_mcp.server import mcp

VALID_TRANSPORTS = {"stdio", "streamable-http", "sse"}


def _wrap_http_app_with_landing(mcp_app):
    """Return an ASGI app that serves GET → landing, others → mcp_app.

    Uses raw ASGI rather than Starlette routing because FastMCP's
    streamable_http endpoint is method-agnostic (Mount-like) and would
    swallow GET requests before any sibling Route handler could match.
    """
    from starlette.requests import Request
    from reactflow_mcp.landing import landing

    async def asgi_app(scope, receive, send):
        if (
            scope["type"] == "http"
            and scope["method"] in ("GET", "HEAD")
            and scope.get("path", "/") == "/"
        ):
            request = Request(scope, receive=receive)
            response = await landing(request)
            await response(scope, receive, send)
            return
        await mcp_app(scope, receive, send)

    return asgi_app


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "streamable_http":
        transport = "streamable-http"
    if transport not in VALID_TRANSPORTS:
        sys.stderr.write(
            f"ERROR: unknown MCP_TRANSPORT={transport!r}. "
            f"Use one of: {sorted(VALID_TRANSPORTS)}\n"
        )
        raise SystemExit(2)

    if transport == "streamable-http":
        import uvicorn

        mcp_app = mcp.streamable_http_app()
        wrapped = _wrap_http_app_with_landing(mcp_app)
        uvicorn.run(
            wrapped,
            host=mcp.settings.host,
            port=mcp.settings.port,
            log_level=mcp.settings.log_level.lower(),
        )
        return

    # stdio + sse: let FastMCP run its own server
    mcp.run(transport=transport)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
