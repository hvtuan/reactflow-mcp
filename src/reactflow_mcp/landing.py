"""HTML landing page rendered from a markdown template.

Served on GET requests to the MCP endpoint (POST is the MCP protocol path).
Builds the URL dynamically from request headers so the same code works
when deployed at any path / behind any reverse proxy.
"""

from __future__ import annotations

from importlib import resources

from markdown_it import MarkdownIt
from starlette.requests import Request
from starlette.responses import HTMLResponse

from reactflow_mcp import __version__
from reactflow_mcp.data.api_catalog import API_CATALOG
from reactflow_mcp.data.pro_examples import PRO_EXAMPLES
from reactflow_mcp.data.recipes import RECIPES
from reactflow_mcp.data.svelte_equivalents import (
    IDENTICAL as SVELTE_IDENTICAL,
    RENAMED as SVELTE_RENAMED,
    SVELTE_ONLY,
)

_md = MarkdownIt("commonmark", {"html": False, "linkify": True, "typographer": True})

_PAGE_CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, "Helvetica Neue", sans-serif;
  max-width: 760px; margin: 0 auto; padding: 2.5rem 1.25rem 4rem; line-height: 1.55;
  color: #111; background: #fafafa;
}
@media (prefers-color-scheme: dark) {
  body { color: #e6e6e6; background: #0f1115; }
  code, pre { background: #1c1f26 !important; color: #e6e6e6; }
  a { color: #88b6ff; }
  hr { border-color: #2a2e36; }
  table th, table td { border-color: #2a2e36; }
}
h1, h2, h3 { line-height: 1.25; }
h1 { margin: 0 0 .25rem; font-size: 1.85rem; }
h2 { margin: 2.2rem 0 .8rem; font-size: 1.25rem; border-bottom: 1px solid #e3e3e3; padding-bottom: .35rem; }
h3 { margin: 1.6rem 0 .4rem; font-size: 1rem; }
p, ul, ol { margin: .6rem 0; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.92em;
  background: #f1f3f5; padding: 1px 5px; border-radius: 4px; }
pre {
  background: #f1f3f5; border-radius: 6px; padding: 12px 14px;
  overflow-x: auto; font-size: 0.88em;
}
pre code { background: transparent; padding: 0; }
hr { border: none; border-top: 1px solid #e3e3e3; margin: 2.5rem 0 1.5rem; }
table { border-collapse: collapse; margin: 1rem 0; width: 100%; font-size: 0.92em; }
th, td { border: 1px solid #e3e3e3; padding: 6px 10px; text-align: left; }
.tag { display: inline-block; background: #eef; color: #335; border-radius: 4px; padding: 1px 8px;
  font-size: 0.78em; margin-right: 4px; }
.muted { color: #888; font-size: 0.88em; }
"""


def _client_endpoint_url(request: Request) -> str:
    """Build the full external URL of this MCP endpoint from request headers.

    Honors X-Forwarded-* set by Traefik/Cloudflare so the rendered config
    block matches what the client actually hits, regardless of internal
    path-prefix stripping.
    """
    fwd_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    fwd_host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    # If a reverse proxy stripped a prefix (e.g. /reactflow), it usually sets
    # X-Forwarded-Prefix or X-Forwarded-Uri. Prefer the original URL the
    # client sees.
    fwd_prefix = request.headers.get("x-forwarded-prefix", "")
    path = fwd_prefix + (request.url.path if not fwd_prefix else "")
    if not path:
        path = "/"
    # Don't keep query string
    return f"{fwd_proto}://{fwd_host}{path}"


def _build_markdown(endpoint_url: str) -> str:
    tools = [
        ("reactflow_search_docs", "Scored full-text search over the bundled deep-dive doc."),
        ("reactflow_get_api", "Structured lookup of a single API symbol (113 covered)."),
        ("reactflow_lookup_v11_v12", "Translate v10/v11 symbol → v12 equivalent."),
        ("reactflow_list_pro_examples", "List Pro paid examples + pricing + license."),
        ("reactflow_svelte_equivalent", "Map React Flow symbol → Svelte Flow + porting notes."),
        ("reactflow_scaffold_custom_node", "TSX scaffold for a custom node component."),
        ("reactflow_scaffold_custom_edge", "TSX scaffold for a custom edge component."),
        ("reactflow_scaffold_flow", "TSX scaffold for a full single-file flow app."),
        ("reactflow_scaffold_workflow_app", "Multi-file Vite/Next.js starter (Pro template clone)."),
        ("reactflow_list_recipes", "Index of 19 OSS recipes cloning Pro examples."),
        ("reactflow_get_recipe", "Full copy-paste TSX for an OSS recipe."),
        ("reactflow_render_flow", "Render flow JSON to Mermaid or ASCII tree."),
        ("reactflow_explain_change", "Explain a NodeChange/EdgeChange in plain English."),
        ("reactflow_validate_flow", "Lint a flow JSON for v12 correctness."),
    ]
    tool_rows = "\n".join(f"| `{name}` | {desc} |" for name, desc in tools)

    svelte_total = len(SVELTE_IDENTICAL) + len(SVELTE_RENAMED) + len(SVELTE_ONLY)
    recipe_count = len(RECIPES)

    return f"""# reactflow-mcp · v{__version__}

MCP server giving LLMs first-class knowledge of **React Flow** (`@xyflow/react` v12) and **Svelte Flow** (`@xyflow/svelte`).
Closes the gap between training-data drift and the current API: surfaces hooks/components/utils/types, v11→v12 migrations, Pro feature catalog, cross-framework symbol mapping, code generators, and a flow JSON linter.

- **Endpoint** (POST JSON-RPC): `{endpoint_url}`
- **Health:** `GET /health` · **Version + stats:** `GET /version`
- **Transport:** streamable-HTTP (stateless, JSON body, no SSE)
- **Source:** [github.com/hvtuan/reactflow-mcp](https://github.com/hvtuan/reactflow-mcp) · MIT

---

## Add to your MCP client

### Claude Code / Cursor / other MCP-aware clients

```json
{{
  "mcpServers": {{
    "reactflow": {{
      "url": "{endpoint_url}"
    }}
  }}
}}
```

### Local stdio fallback (no HTTP)

```bash
pip install reactflow-mcp
reactflow-mcp                              # stdio by default
```

Then point your client to the local binary:

```json
{{
  "mcpServers": {{
    "reactflow": {{
      "command": "reactflow-mcp"
    }}
  }}
}}
```

---

## Tools ({len(tools)})

| name | what it does |
|---|---|
{tool_rows}

## Resource

- `reactflow://deep-dive` — full bundled deep-dive markdown brief (≈25k chars)

## Bundled data

- **{len(API_CATALOG)}** React Flow API symbols (catalog)
- **{len(PRO_EXAMPLES)}** Pro examples (catalog + pricing + license)
- **{svelte_total}** Svelte Flow symbol mappings ({len(SVELTE_RENAMED)} renamed · {len(SVELTE_IDENTICAL)} identical · {len(SVELTE_ONLY)} svelte-only)
- **{recipe_count}** OSS recipes cloning Pro patterns (auto-layout dagre/elkjs/force, undo-redo, copy-paste, helper lines, expand-collapse, editable edge, shapes, server-side image, ...)
- v11 → v12 migration map (covers `parentNode → parentId`, `project → screenToFlowPosition`, `node.width → node.measured.width`, etc.)

---

## Smoke test from your terminal

```bash
curl -X POST "{endpoint_url}" \\
  -H "Content-Type: application/json" \\
  -H "Accept: application/json, text/event-stream" \\
  -d '{{"jsonrpc":"2.0","id":1,"method":"tools/list"}}'
```

Should return all 8 tools.

---

<span class="muted">Built with FastMCP + Python · deployed via Coolify · path-routed under <code>mcp.huynhvantuan.net</code>.</span>
"""


def render_landing_html(request: Request) -> str:
    endpoint_url = _client_endpoint_url(request)
    body_html = _md.render(_build_markdown(endpoint_url))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>reactflow-mcp · v{__version__}</title>
  <style>{_PAGE_CSS}</style>
</head>
<body>
{body_html}
</body>
</html>
"""


async def landing(request: Request) -> HTMLResponse:
    return HTMLResponse(render_landing_html(request))
