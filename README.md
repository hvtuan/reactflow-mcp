# reactflow-mcp

MCP server giving LLMs first-class knowledge of **React Flow** (`@xyflow/react` v12) and **Svelte Flow** (`@xyflow/svelte`).
Closes the gap between training-data drift and the current API: surfaces hooks/components/utils/types, v11→v12 migrations, Pro feature catalog, cross-framework symbol mapping, code generators, and a flow JSON linter.

> Status: **v0.2.0** — 8 tools + 1 resource, stdio transport, MIT licensed.

## What's inside

| | |
|---|---|
| Knowledge tools | `reactflow_search_docs` · `reactflow_get_api` · `reactflow_lookup_v11_v12` · `reactflow_list_pro_examples` · `reactflow_svelte_equivalent` |
| Codegen tools | `reactflow_scaffold_custom_node` · `reactflow_scaffold_custom_edge` |
| Validation tool | `reactflow_validate_flow` |
| Resource | `reactflow://deep-dive` — full bundled markdown brief (~25k chars) |
| Bundled data | 27 doc sections · 69 API symbols · 16 v11→v12 maps · 21 Pro examples · 4 renamed + 54 identical Svelte symbols |

## Why

Out-of-the-box, LLMs hallucinate stale React Flow APIs — `parentNode` instead of `parentId`, `project()` instead of `screenToFlowPosition()`, the dead `reactflow` package instead of `@xyflow/react`, Pro examples that don't exist, broken handle ids. This MCP makes those lookups 1-tool-call deep, generates ready-to-paste TSX, and lints flow JSON.

## Install

```bash
pip install reactflow-mcp                    # once published to PyPI
```

Or from source:

```bash
git clone https://github.com/hvtuan/reactflow-mcp.git
cd reactflow-mcp
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"            # add [dev] to also get pytest
```

Requires Python ≥ 3.10.

## Run

```bash
.venv/bin/python -m reactflow_mcp        # or the console script:
.venv/bin/reactflow-mcp
```

Speaks **stdio MCP** — wire into any MCP-aware client.

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

### Knowledge

#### `reactflow_search_docs(query, section?, max_results=5, snippet_chars=600, response_format='markdown')`
Scored full-text search over the deep-dive doc. Title hits weight 10× body hits; optional section title filter narrows the search space.

#### `reactflow_get_api(symbol, response_format='markdown')`
Structured lookup for a single API symbol. Returns `kind` (component/hook/util/type/enum), `signature`, `props`/`params`, deprecation, OSS/Pro flag. Case-insensitive; unknown symbols return nearest-name suggestions.

#### `reactflow_lookup_v11_v12(symbol, response_format='markdown')`
Maps v10/v11 → v12 names: `parentNode` → `parentId`, `project` → `screenToFlowPosition`, `onEdgeUpdate` → `onReconnect`, `node.width` → `node.measured.width`, package `reactflow` → `@xyflow/react`, etc. Always returns the v12 global behavior-change list as context.

#### `reactflow_list_pro_examples(category?, framework?, include_pricing=True, response_format='markdown')`
Pro paid examples catalog (collab, undo/redo, helper lines, expand/collapse, force layout, freehand draw, server-side image, Pro templates…) + pricing tiers + license notes. Filter by category or framework (`react` | `svelte`).

#### `reactflow_svelte_equivalent(symbol, include_porting_notes=True, response_format='markdown')`
Maps React Flow symbol → Svelte Flow (`@xyflow/svelte`) equivalent. Most names are identical (just change the import path); a handful renamed (`<ReactFlow>`→`<SvelteFlow>`, `useReactFlow`→`useSvelteFlow`, `EdgeLabelRenderer`→`EdgeLabel`). Optionally appends porting notes (state model, custom-component flavor, Svelte 5 requirement, Pro example subset).

### Codegen

#### `reactflow_scaffold_custom_node(name, data_fields?, handles?, editable=False, with_resizer=False, with_toolbar=False, style='tailwind', response_format='markdown')`
Generates ready-to-paste TSX for a custom node component. Output: component TSX + `nodeTypes` registration + Node factory snippet. Targets `@xyflow/react` v12 / React 18+. Auto-adds `nodrag` on inputs so they don't drag the node.

#### `reactflow_scaffold_custom_edge(name, path_type='bezier', with_label=False, with_delete_button=False, with_label_renderer=False, style='tailwind', response_format='markdown')`
Generates ready-to-paste TSX for a custom edge component. `path_type`: `bezier` | `smoothstep` | `step` | `straight` | `simplebezier`. `with_delete_button` auto-forces `with_label_renderer` (button needs HTML overlay). Wraps `<BaseEdge>` for free selection + events.

### Validation

#### `reactflow_validate_flow(flow_json, response_format='markdown')`
Lints a JSON-stringified `{nodes, edges}` flow object for v12 correctness.

Hard errors include: missing/duplicate node or edge ids, edge endpoints pointing to non-existent nodes, malformed positions, v11 leftover fields (`parentNode`, `xPos`, `yPos`, `edge.updatable`), parent appearing after child in the array.

Warnings include: cycles, parallel/duplicate edges, edge handle ids not in node `handles[]`, `node.width`/`height` as numbers (sets inline styles in v12), runtime-only fields persisted (`positionAbsoluteX/Y`).

Returns stats: counts, node/edge type histograms, root/leaf nodes, cycle list.

## Resource

### `reactflow://deep-dive` (`text/markdown`)
Full 25k-char brief: OSS Learn surface, API cheat-sheet, Pro layer, monorepo map, gotchas, v11→v12 migration. Tools index into this.

## Project layout

```
reactflow-mcp/
├── pyproject.toml
├── src/reactflow_mcp/
│   ├── __init__.py
│   ├── __main__.py             # entrypoint: python -m reactflow_mcp
│   ├── server.py               # FastMCP server + tool/resource registration
│   ├── scaffolders.py          # pure-function code generators
│   ├── validators.py           # pure-function flow JSON linter
│   └── data/
│       ├── deep_dive.md        # bundled deep-dive doc
│       ├── api_catalog.py      # 69 React Flow API symbols structured
│       ├── migration.py        # v11/v10 → v12 map
│       ├── pro_examples.py     # Pro catalog + pricing + license
│       └── svelte_equivalents.py  # React → Svelte symbol map + porting notes
```

## Smoke test

```bash
.venv/bin/python -c "from reactflow_mcp.server import _self_check; import json; print(json.dumps(_self_check(), indent=2))"
```

Should print counts: 27 sections, 69 API entries, 16 migrations, 21 Pro examples, 4 Svelte-renamed symbols, 54 Svelte-identical, 1 Svelte-only, 8 tools, 1 resource.

## Release process

1. Bump `version` in `pyproject.toml` and `src/reactflow_mcp/__init__.py`.
2. Commit + tag: `git tag v0.X.Y && git push --tags`.
3. `.github/workflows/release.yml` builds + publishes to PyPI via OIDC trusted publishing — no API token required.

First-time PyPI setup: register the trusted publisher on PyPI (`Publishing → Add a new pending publisher`) with:
- Owner: `hvtuan`
- Repository: `reactflow-mcp`
- Workflow: `release.yml`
- Environment: `pypi`

## Drift detection

`scripts/refresh_data.py` compares the bundled API catalog / Pro examples / Svelte data against `reactflow.dev` and `svelteflow.dev` sitemaps and emits a markdown report. Exits non-zero when drift is detected.

`.github/workflows/refresh-data.yml` runs the script weekly (Monday 06:00 UTC) and opens / refreshes a `data-drift` labelled issue when new upstream symbols appear. Manual trigger via `Actions → Data drift check → Run workflow`.

Run locally:

```bash
python scripts/refresh_data.py                  # stdout
python scripts/refresh_data.py --out report.md  # write to file
```

## Roadmap

- Tune `search_docs` scoring (currently favors large sections over targeted matches)
- Expand `api_catalog.py` with the ~40 handler/util types the drift check flagged (OnConnect, NodeMouseHandler, ReactFlowInstance, …)
- Add `reactflow_scaffold_flow(spec)` — full mini-flow from a higher-level description
- Add `reactflow_visualize_flow(flow_json)` — render mermaid/ascii preview
- Cover more Svelte Flow edge cases (per-symbol prop differences, not just naming)
- Publish to MCP marketplaces (Smithery, mcp-registry) once PyPI-released

## License

MIT
