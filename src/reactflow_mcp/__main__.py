"""Entry point: `python -m reactflow_mcp` or `reactflow-mcp`.

Transport selection via env:
    MCP_TRANSPORT=stdio              (default — Claude Code, Cursor, etc.)
    MCP_TRANSPORT=streamable-http    (HTTP/JSON-RPC, for Coolify/web deploy)
    MCP_TRANSPORT=sse                (legacy SSE — only if a client specifically requires it)

When using streamable-http, host/port come from MCP_HOST / MCP_PORT
(see server.py for full env list).
"""

from __future__ import annotations

import os
import sys

from reactflow_mcp.server import mcp

VALID_TRANSPORTS = {"stdio", "streamable-http", "sse"}


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    # tolerate underscore form
    if transport == "streamable_http":
        transport = "streamable-http"
    if transport not in VALID_TRANSPORTS:
        sys.stderr.write(
            f"ERROR: unknown MCP_TRANSPORT={transport!r}. "
            f"Use one of: {sorted(VALID_TRANSPORTS)}\n"
        )
        raise SystemExit(2)
    mcp.run(transport=transport)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
