# reactflow-mcp

MCP server giving LLMs first-class knowledge of **React Flow** (`@xyflow/react` v12).
Closes the gap between training-data drift and the current API: surfaces hooks/components/utils/types, v11→v12 migrations, Pro feature catalog, and a searchable deep-dive.

> Status: **v0.1.0** — 4 tools + 1 resource, stdio transport, MIT licensed.

## What's inside

| | |
|---|---|
| Tools (4) | `reactflow_search_docs` · `reactflow_get_api` · `reactflow_lookup_v11_v12` · `reactflow_list_pro_examples` |
| Resource (1) | `reactflow://deep-dive` — full bundled markdown brief |
| Source data | 27 doc sections · 69 API symbols · 16 migration mappings · 21 Pro examples |

## Why

Out-of-the-box, LLMs hallucinate stale React Flow APIs — `parentNode` instead of `parentId`, `project()` instead of `screenToFlowPosition()`, the dead `reactflow` package instead of `@xyflow/react`, Pro examples that don't exist. This MCP makes those lookups 1-tool-call deep.

## Install

```bash
git clone https://github.com/hvtuan/reactflow-mcp.git
cd reactflow-mcp
python3 -m venv .venv
.venv/bin/pip install -e .
```

Requires Python ≥ 3.10.

## Run

```bash
.venv/bin/python -m reactflow_mcp        # or the console script:
.venv/bin/reactflow-mcp
```

The server speaks **stdio MCP** — wire it into any MCP-aware client.

### Claude Code

```json
{
  "mcpServers": {
    "reactflow": {
      "command": "/abs/path/to/reactflow-mcp/.venv/bin/python",
      "args": ["-m", "reactflow_mcp"]
    }
  }
}
```

## Tools

### `reactflow_search_docs(query, section?, max_results=5, snippet_chars=600, response_format='markdown')`
Full-text search over the deep-dive doc. Scores title hits high, body hits lower; supports optional section filter.

### `reactflow_get_api(symbol, response_format='markdown')`
Structured lookup for a single API symbol. Returns `kind` (component/hook/util/type/enum), `signature`, `props`/`params`, deprecation, OSS/Pro flag. Case-insensitive. Unknown symbols return nearest-name suggestions.

### `reactflow_lookup_v11_v12(symbol, response_format='markdown')`
Maps v10/v11 → v12 names: `parentNode` → `parentId`, `project` → `screenToFlowPosition`, `onEdgeUpdate` → `onReconnect`, `node.width` → `node.measured.width`, package `reactflow` → `@xyflow/react`, etc. Always returns the v12 global behavior-change list as context.

### `reactflow_list_pro_examples(category?, framework?, include_pricing=True, response_format='markdown')`
Pro paid examples catalog (collab, undo/redo, helper lines, expand/collapse, force layout, freehand draw, server-side image, Pro templates, …) + pricing tiers + license notes. Filter by category or framework.

## Resource

### `reactflow://deep-dive` (`text/markdown`)
Full 25k-char deep-dive brief: OSS Learn surface, API cheat-sheet, Pro layer, monorepo map, gotchas, v11→v12 migration. The tools above index into this.

## Project layout

```
reactflow-mcp/
├── pyproject.toml
├── src/reactflow_mcp/
│   ├── __init__.py
│   ├── __main__.py            # entrypoint: python -m reactflow_mcp
│   ├── server.py              # FastMCP server + tool/resource registration
│   └── data/
│       ├── deep_dive.md       # bundled deep-dive doc
│       ├── api_catalog.py     # 69 API symbols structured
│       ├── migration.py       # v11/v10 → v12 map
│       └── pro_examples.py    # Pro catalog + pricing + license
```

## Smoke test

```bash
.venv/bin/python -c "from reactflow_mcp.server import _self_check; import json; print(json.dumps(_self_check(), indent=2))"
```

Should print counts: 27 sections, 69 API entries, 16 migrations, 21 Pro examples, 4 tools, 1 resource.

## Roadmap

- Tune `search_docs` scoring (currently favors large sections)
- Add `reactflow_scaffold_custom_node(spec)` / `reactflow_scaffold_custom_edge(spec)` code-gen tools
- Add `reactflow_validate_flow(json)` schema + handle-id + cycle checker
- Cover Svelte Flow (`@xyflow/svelte`) symbols
- Auto-refresh data layer from upstream docs on a cron

## License

MIT
