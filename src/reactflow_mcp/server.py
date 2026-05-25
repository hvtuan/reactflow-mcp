"""reactflow_mcp — FastMCP server exposing React Flow knowledge to LLMs.

Tools:
    - reactflow_search_docs           — full-text search across the deep-dive doc
    - reactflow_get_api               — structured lookup of a public API symbol
    - reactflow_lookup_v11_v12        — v11/v10 → v12 migration map
    - reactflow_list_pro_examples     — Pro paid examples catalog (+ filtering)
    - reactflow_scaffold_custom_node  — generate TSX for a custom node component
    - reactflow_scaffold_custom_edge  — generate TSX for a custom edge component
    - reactflow_validate_flow         — lint a flow JSON for v12 correctness
    - reactflow_svelte_equivalent     — map a React Flow symbol to Svelte Flow

Resource:
    - reactflow://deep-dive           — full deep-dive markdown brief
"""

from __future__ import annotations

import json
import re
from enum import Enum
from importlib import resources
from typing import Annotated, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from reactflow_mcp.data.api_catalog import API_CATALOG, get_symbol
from reactflow_mcp.data.migration import (
    BEHAVIOR_CHANGES,
    PACKAGE_MIGRATION,
    SYMBOL_MIGRATION,
    lookup as migration_lookup,
)
from reactflow_mcp.data.pro_examples import LICENSE_NOTES, PRICING_TIERS, PRO_EXAMPLES
from reactflow_mcp.data.svelte_equivalents import IDENTICAL as SVELTE_IDENTICAL
from reactflow_mcp.data.svelte_equivalents import PORTING_NOTES, RENAMED as SVELTE_RENAMED
from reactflow_mcp.data.svelte_equivalents import SVELTE_ONLY, lookup as svelte_lookup
from reactflow_mcp.scaffolders import scaffold_custom_edge, scaffold_custom_node
from reactflow_mcp.validators import validate_flow

# ───────────────────────── constants ─────────────────────────

SERVER_NAME = "reactflow_mcp"
CHARACTER_LIMIT = 25_000
DEEP_DIVE_URI = "reactflow://deep-dive"

# ───────────────────────── load deep-dive once ─────────────────────────

_DEEP_DIVE_TEXT: str = (
    resources.files("reactflow_mcp.data").joinpath("deep_dive.md").read_text(encoding="utf-8")
)


def _parse_sections(text: str) -> list[dict]:
    """Split deep-dive markdown into H2 sections + H3 sub-sections."""
    out: list[dict] = []

    parts = re.split(r"^## ", text, flags=re.MULTILINE)
    if parts and parts[0].strip():
        out.append({"title": "Preamble", "level": 0, "body": parts[0].strip(), "anchor": "preamble"})

    for chunk in parts[1:]:
        head, _, body = chunk.partition("\n")
        title = head.strip()
        body = body.strip()
        anchor = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        out.append({"title": title, "level": 2, "body": body, "anchor": anchor})

        sub_parts = re.split(r"^### ", body, flags=re.MULTILINE)
        for sub in sub_parts[1:]:
            sub_head, _, sub_body = sub.partition("\n")
            sub_title = sub_head.strip()
            sub_anchor = anchor + "/" + re.sub(r"[^a-z0-9]+", "-", sub_title.lower()).strip("-")
            out.append({
                "title": f"{title} / {sub_title}",
                "level": 3,
                "body": sub_body.strip(),
                "anchor": sub_anchor,
            })

    return out


_SECTIONS: list[dict] = _parse_sections(_DEEP_DIVE_TEXT)

# ───────────────────────── shared helpers ─────────────────────────


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


def _truncate(text: str) -> str:
    if len(text) <= CHARACTER_LIMIT:
        return text
    return text[:CHARACTER_LIMIT] + f"\n\n…(truncated at {CHARACTER_LIMIT} chars)"


def _format_response(payload: dict, fmt: ResponseFormat, markdown_renderer) -> str:
    if fmt is ResponseFormat.JSON:
        return _truncate(json.dumps(payload, indent=2, ensure_ascii=False))
    return _truncate(markdown_renderer(payload))


# ───────────────────────── MCP server ─────────────────────────

mcp = FastMCP(SERVER_NAME)


# ─────────── tool 1: search_docs ───────────


def _score(section: dict, query_lc: str) -> int:
    title = section["title"].lower()
    body = section["body"].lower()
    score = 0
    if query_lc in title:
        score += 10
    score += body.count(query_lc) * 2
    for token in query_lc.split():
        if len(token) < 3:
            continue
        if token in title:
            score += 4
        score += body.count(token)
    return score


@mcp.tool(
    name="reactflow_search_docs",
    annotations={
        "title": "Search React Flow deep-dive",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def reactflow_search_docs(
    query: Annotated[str, Field(
        min_length=2, max_length=200,
        description="Search string. Matches case-insensitively against section titles and bodies (e.g. 'custom edge', 'parentId', 'SSR', 'performance').",
    )],
    section: Annotated[Optional[str], Field(
        default=None,
        description="Optional top-level section title substring (e.g. 'API cheat-sheet', 'Pro layer', 'Troubleshooting').",
    )] = None,
    max_results: Annotated[int, Field(
        default=5, ge=1, le=20,
        description="Max matching sections to return.",
    )] = 5,
    snippet_chars: Annotated[int, Field(
        default=600, ge=120, le=3000,
        description="Per-result body excerpt length.",
    )] = 600,
    response_format: Annotated[ResponseFormat, Field(
        default=ResponseFormat.MARKDOWN,
        description="markdown | json",
    )] = ResponseFormat.MARKDOWN,
) -> str:
    """Search the bundled React Flow deep-dive doc for relevant sections.

    Use this for general "how do I..." or conceptual React Flow questions —
    covers Concepts, Customization, Layouting, Advanced Use (perf, SSR,
    multiplayer, computing-flows…), Troubleshooting, v11→v12 migration,
    API cheat-sheet, Pro layer, and gotchas.

    For a specific API symbol (e.g. 'useReactFlow', 'Handle', 'addEdge'),
    prefer `reactflow_get_api`.

    Returns JSON schema:
        {
          "query": str,
          "section_filter": str | null,
          "total_matches": int,
          "results": [
            {"title": str, "anchor": str, "level": int, "score": int, "excerpt": str}
          ]
        }
    """
    q = query.strip()
    if not q:
        return "Error: query cannot be empty."

    query_lc = q.lower()
    candidates = _SECTIONS
    if section:
        sec_lc = section.lower()
        candidates = [s for s in _SECTIONS if sec_lc in s["title"].lower()]

    scored = [(s, _score(s, query_lc)) for s in candidates]
    scored = [t for t in scored if t[1] > 0]
    scored.sort(key=lambda t: t[1], reverse=True)
    top = scored[:max_results]

    results = [
        {
            "title": s["title"],
            "anchor": s["anchor"],
            "level": s["level"],
            "score": score,
            "excerpt": s["body"][:snippet_chars] + ("…" if len(s["body"]) > snippet_chars else ""),
        }
        for s, score in top
    ]

    payload = {
        "query": q,
        "section_filter": section,
        "total_matches": len(scored),
        "results": results,
    }

    def to_md(p: dict) -> str:
        lines = [f"# React Flow doc search: '{p['query']}'"]
        if p["section_filter"]:
            lines.append(f"_section filter: `{p['section_filter']}`_")
        lines.append(f"\n_{p['total_matches']} matching section(s); showing top {len(p['results'])}._\n")
        if not p["results"]:
            lines.append("No matches. Try a broader query or use `reactflow_get_api` for a specific symbol.")
            return "\n".join(lines)
        for r in p["results"]:
            lines.append(f"## {r['title']}  \n`#{r['anchor']}` · score {r['score']}\n")
            lines.append(r["excerpt"])
            lines.append("")
        lines.append(f"\n_Full doc at resource `{DEEP_DIVE_URI}`._")
        return "\n".join(lines)

    return _format_response(payload, response_format, to_md)


# ─────────── tool 2: get_api ───────────


@mcp.tool(
    name="reactflow_get_api",
    annotations={
        "title": "Get React Flow API reference",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def reactflow_get_api(
    symbol: Annotated[str, Field(
        min_length=1, max_length=80,
        description="API symbol — hook ('useReactFlow'), component ('Handle', 'ReactFlow'), util ('addEdge'), type ('NodeProps'), enum ('Position'). Case-insensitive.",
    )],
    response_format: Annotated[ResponseFormat, Field(
        default=ResponseFormat.MARKDOWN,
        description="markdown | json",
    )] = ResponseFormat.MARKDOWN,
) -> str:
    """Look up React Flow v12 API reference for a single symbol.

    Returns kind (component/hook/util/type/enum), signature, props/params,
    notes, deprecation status, OSS/Pro flag.

    Returns JSON schema:
        {
          "symbol": str,
          "found": bool,
          "kind": str?, "category": str?, "summary": str?, "signature": str?,
          "props": [{"name": str, "type": str, "purpose": str?}]?,
          "params": [...]?,
          "notes": str?, "since": str?,
          "deprecated": bool?, "replacement": str?, "pro": bool?,
          "suggestions": [str]?  // only if not found
        }
    """
    entry = get_symbol(symbol)

    if entry is None:
        q = symbol.lower()
        suggestions = sorted(
            (n for n in API_CATALOG if q in n.lower() or n.lower() in q),
            key=lambda n: (abs(len(n) - len(symbol)), n.lower()),
        )[:8]
        payload = {"symbol": symbol, "found": False, "suggestions": suggestions}

        def to_md_miss(p: dict) -> str:
            lines = [f"# `{p['symbol']}` — not in catalog"]
            if p["suggestions"]:
                lines.append("\nDid you mean one of:")
                lines.extend(f"- `{s}`" for s in p["suggestions"])
            else:
                lines.append("\nNo close matches. Try `reactflow_search_docs` with a topic keyword.")
            return "\n".join(lines)

        return _format_response(payload, response_format, to_md_miss)

    canonical = next((k for k in API_CATALOG if k.lower() == symbol.lower()), symbol)
    payload = {"symbol": canonical, "found": True, **entry}

    def to_md(p: dict) -> str:
        lines = [f"# `{p['symbol']}` — {p.get('kind', 'unknown')} · _{p.get('category', '')}_"]
        if p.get("deprecated"):
            rep = p.get("replacement", "(no replacement)")
            lines.append(f"\n⚠️ **DEPRECATED** → use `{rep}` instead.")
        if p.get("pro"):
            lines.append("\n💰 **Pro/paid surface** — see `reactflow_list_pro_examples`.")
        if p.get("summary"):
            lines.append(f"\n{p['summary']}")
        if p.get("signature"):
            lines.append(f"\n```ts\n{p['signature']}\n```")
        if p.get("props"):
            lines.append("\n**Props:**\n")
            lines.append("| name | type | purpose |")
            lines.append("|---|---|---|")
            for prop in p["props"]:
                lines.append(f"| `{prop['name']}` | `{prop.get('type', '')}` | {prop.get('purpose', '')} |")
        if p.get("params"):
            lines.append("\n**Params:**\n")
            for param in p["params"]:
                lines.append(f"- `{param['name']}: {param.get('type', '')}` — {param.get('purpose', '')}")
        if p.get("notes"):
            lines.append(f"\n_{p['notes']}_")
        if p.get("since"):
            lines.append(f"\n*Since:* {p['since']}")
        return "\n".join(lines)

    return _format_response(payload, response_format, to_md)


# ─────────── tool 3: lookup_v11_v12 ───────────


@mcp.tool(
    name="reactflow_lookup_v11_v12",
    annotations={
        "title": "v11 → v12 migration lookup",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def reactflow_lookup_v11_v12(
    symbol: Annotated[str, Field(
        min_length=1, max_length=80,
        description="A v10/v11 symbol you want the v12 equivalent for. Examples: 'parentNode', 'xPos', 'onEdgeUpdate', 'project', 'nodeInternals', 'useHandleConnections', 'reactflow' (package), 'node.width'.",
    )],
    response_format: Annotated[ResponseFormat, Field(
        default=ResponseFormat.MARKDOWN,
        description="markdown | json",
    )] = ResponseFormat.MARKDOWN,
) -> str:
    """Translate a v10/v11 React Flow symbol to its v12 equivalent.

    Catches common LLM mistakes: `parentNode` → `parentId`,
    `project()` → `screenToFlowPosition()`, `onEdgeUpdate` → `onReconnect`,
    `node.width` → `node.measured.width`, package `reactflow` → `@xyflow/react`.

    Returns JSON schema:
        {
          "symbol": str,
          "found": bool,
          "replacement": str?,
          "kind": str?, "since": str?, "note": str?,
          "behavior_changes": [{"topic": str, "change": str}]
        }
    """
    hit = migration_lookup(symbol)
    payload: dict = {"symbol": symbol, "found": hit is not None}
    if hit:
        payload.update(hit)
    payload["behavior_changes"] = BEHAVIOR_CHANGES

    def to_md(p: dict) -> str:
        lines = [f"# `{p['symbol']}` — v11/v10 → v12"]
        if p.get("found"):
            lines.append(f"\n✅ Replace with: **`{p.get('replacement')}`**  ({p.get('kind', '')})")
            if p.get("since"):
                lines.append(f"  \n*Since:* {p['since']}")
            if p.get("note"):
                lines.append(f"\n> {p['note']}")
        else:
            lines.append("\n❌ Not in migration map — may already be a v12 symbol, or unchanged. Check `reactflow_get_api`.")
        lines.append("\n## v12 global behavior changes (still apply)")
        for bc in p["behavior_changes"]:
            lines.append(f"- **{bc['topic']}** — {bc['change']}")
        return "\n".join(lines)

    return _format_response(payload, response_format, to_md)


# ─────────── tool 4: list_pro_examples ───────────


@mcp.tool(
    name="reactflow_list_pro_examples",
    annotations={
        "title": "List React Flow Pro examples",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def reactflow_list_pro_examples(
    category: Annotated[Optional[str], Field(
        default=None,
        description="Filter by category: 'layout' | 'interaction' | 'edges' | 'nodes' | 'grouping' | 'whiteboard' | 'misc' | 'template'. Case-insensitive.",
    )] = None,
    framework: Annotated[Optional[str], Field(
        default=None,
        description="Filter by framework: 'react' | 'svelte'.",
    )] = None,
    include_pricing: Annotated[bool, Field(
        default=True,
        description="Include pricing tier + license notes.",
    )] = True,
    response_format: Annotated[ResponseFormat, Field(
        default=ResponseFormat.MARKDOWN,
        description="markdown | json",
    )] = ResponseFormat.MARKDOWN,
) -> str:
    """List React Flow Pro (paid) examples + pricing + license notes.

    Useful before re-implementing common patterns: auto-layout, collaborative
    editing, undo/redo, helper lines, copy/paste, expand/collapse, force
    layout, freehand draw, server-side image export, etc.

    Returns JSON schema:
        {
          "filter": {"category": str?, "framework": str?},
          "count": int,
          "examples": [{"name": str, "category": str, "frameworks": [str], "summary": str}],
          "pricing": [{"name": str, "seats": int, "includes": [str], "price_note": str}]?,
          "license_notes": {core, ui_kit, perpetual, redistribution, seats, attribution}?
        }
    """
    cat = category.lower() if category else None
    fw = framework.lower() if framework else None

    filtered = [
        ex for ex in PRO_EXAMPLES
        if (cat is None or ex["category"] == cat)
        and (fw is None or fw in ex["frameworks"])
    ]

    payload: dict = {
        "filter": {"category": category, "framework": framework},
        "count": len(filtered),
        "examples": filtered,
    }
    if include_pricing:
        payload["pricing"] = PRICING_TIERS
        payload["license_notes"] = LICENSE_NOTES

    def to_md(p: dict) -> str:
        lines = ["# React Flow Pro examples"]
        f = p["filter"]
        flt_bits = [f"category=`{f['category']}`" if f["category"] else "", f"framework=`{f['framework']}`" if f["framework"] else ""]
        flt_str = " · ".join(b for b in flt_bits if b)
        if flt_str:
            lines.append(f"_filter: {flt_str}_")
        lines.append(f"\n**{p['count']} example(s) match.**\n")
        if not p["examples"]:
            lines.append("No examples match this filter.")
        else:
            by_cat: dict[str, list] = {}
            for ex in p["examples"]:
                by_cat.setdefault(ex["category"], []).append(ex)
            for category_key, examples in by_cat.items():
                lines.append(f"## {category_key}")
                for ex in examples:
                    fws = ", ".join(ex["frameworks"])
                    lines.append(f"- **{ex['name']}** _(frameworks: {fws})_ — {ex['summary']}")
                lines.append("")

        if "pricing" in p:
            lines.append("## Pricing tiers")
            for tier in p["pricing"]:
                lines.append(f"### {tier['name']} — {tier['seats']} seat(s)")
                for item in tier["includes"]:
                    lines.append(f"- {item}")
                lines.append(f"_{tier['price_note']}_\n")
        if "license_notes" in p:
            lines.append("## License & attribution")
            for k, v in p["license_notes"].items():
                lines.append(f"- **{k}** — {v}")

        lines.append("\n_Pro examples are subscriber-gated. Catalog: https://reactflow.dev/pro/examples_")
        return "\n".join(lines)

    return _format_response(payload, response_format, to_md)


# ─────────── tool 5: scaffold_custom_node ───────────


def _render_scaffold_md(title: str, result: dict) -> str:
    lines = [f"# {title}: `{result['component_name']}`"]
    for w in result["warnings"]:
        lines.append(f"\n> ⚠️ {w}")
    lines.append("\n## Component (TSX)\n\n```tsx\n" + result["component"].rstrip() + "\n```")
    lines.append("\n## Registration\n\n```tsx\n" + result["registration"].rstrip() + "\n```")
    lines.append("\n## Usage / factory\n\n```tsx\n" + result["usage"].rstrip() + "\n```")
    return "\n".join(lines)


@mcp.tool(
    name="reactflow_scaffold_custom_node",
    annotations={
        "title": "Scaffold custom node TSX",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def reactflow_scaffold_custom_node(
    name: Annotated[str, Field(
        min_length=1, max_length=80,
        description="Component name (PascalCase preferred — auto-normalized otherwise). Example: 'TextInputNode'.",
    )],
    data_fields: Annotated[Optional[list[dict]], Field(
        default=None,
        description="List of {name: str, type?: str (TS type), default?: any}. Example: [{'name':'label','type':'string','default':'Hello'},{'name':'value','type':'number','default':0}]. Empty = no data fields.",
    )] = None,
    handles: Annotated[Optional[list[dict]], Field(
        default=None,
        description="List of {kind: 'source'|'target', position: 'top'|'right'|'bottom'|'left', id?: str}. Default = 1 target on left + 1 source on right.",
    )] = None,
    editable: Annotated[bool, Field(
        default=False,
        description="If true, render <input> bound to string-typed data fields with useReactFlow().updateNodeData(). Auto-adds `nodrag` class so inputs don't drag the node.",
    )] = False,
    with_resizer: Annotated[bool, Field(
        default=False,
        description="Include <NodeResizer> with min 120x60 (visible when selected).",
    )] = False,
    with_toolbar: Annotated[bool, Field(
        default=False,
        description="Include <NodeToolbar> with a Delete button (visible when selected).",
    )] = False,
    style: Annotated[str, Field(
        default="tailwind",
        description="Styling approach: 'tailwind' (default) | 'css-modules' | 'inline'.",
    )] = "tailwind",
    response_format: Annotated[ResponseFormat, Field(
        default=ResponseFormat.MARKDOWN,
        description="markdown | json",
    )] = ResponseFormat.MARKDOWN,
) -> str:
    """Generate ready-to-paste TSX for a custom React Flow node component.

    Output covers: the component file, the `nodeTypes` registration snippet,
    and a factory snippet for creating a Node object that uses it. Targets
    `@xyflow/react` v12 / React 18+. Handles default to one target (left)
    + one source (right). All Field metadata explained in the per-arg
    descriptions.

    Returns JSON schema:
        {
          "component_name": str,
          "type_name": str,         // camelCase key for nodeTypes
          "component": str,         // TSX file content
          "registration": str,      // nodeTypes snippet
          "usage": str,             // Node factory snippet
          "warnings": [str]
        }
    """
    try:
        result = scaffold_custom_node(
            name=name,
            data_fields=data_fields,
            handles=handles,
            editable=editable,
            with_resizer=with_resizer,
            with_toolbar=with_toolbar,
            style=style,
        )
    except ValueError as e:
        return f"Error: {e}"

    return _format_response(
        result,
        response_format,
        lambda r: _render_scaffold_md("Custom node", r),
    )


# ─────────── tool 6: scaffold_custom_edge ───────────


@mcp.tool(
    name="reactflow_scaffold_custom_edge",
    annotations={
        "title": "Scaffold custom edge TSX",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def reactflow_scaffold_custom_edge(
    name: Annotated[str, Field(
        min_length=1, max_length=80,
        description="Component name (PascalCase preferred). Example: 'DeletableEdge'.",
    )],
    path_type: Annotated[str, Field(
        default="bezier",
        description="Path builder: 'bezier' (default) | 'smoothstep' | 'step' | 'straight' | 'simplebezier'.",
    )] = "bezier",
    with_label: Annotated[bool, Field(
        default=False,
        description="Render the edge's `label` field. If with_label_renderer is also true, uses HTML overlay (clickable).",
    )] = False,
    with_delete_button: Annotated[bool, Field(
        default=False,
        description="Adds a small × button on the edge that removes it via useReactFlow().setEdges. Forces with_label_renderer=true.",
    )] = False,
    with_label_renderer: Annotated[bool, Field(
        default=False,
        description="Wrap label/button in <EdgeLabelRenderer> (HTML portal above SVG). Required for interactive labels.",
    )] = False,
    style: Annotated[str, Field(
        default="tailwind",
        description="Styling approach: 'tailwind' (default) | 'css-modules' | 'inline'.",
    )] = "tailwind",
    response_format: Annotated[ResponseFormat, Field(
        default=ResponseFormat.MARKDOWN,
        description="markdown | json",
    )] = ResponseFormat.MARKDOWN,
) -> str:
    """Generate ready-to-paste TSX for a custom React Flow edge component.

    Output covers: the component file (wrapping <BaseEdge> for interactivity),
    the `edgeTypes` registration snippet, and an Edge factory snippet.

    Returns JSON schema:
        {
          "component_name": str,
          "type_name": str,
          "component": str,
          "registration": str,
          "usage": str,
          "warnings": [str]
        }
    """
    try:
        result = scaffold_custom_edge(
            name=name,
            path_type=path_type,
            with_label=with_label,
            with_delete_button=with_delete_button,
            with_label_renderer=with_label_renderer,
            style=style,
        )
    except ValueError as e:
        return f"Error: {e}"

    return _format_response(
        result,
        response_format,
        lambda r: _render_scaffold_md("Custom edge", r),
    )


# ─────────── tool 7: validate_flow ───────────


@mcp.tool(
    name="reactflow_validate_flow",
    annotations={
        "title": "Validate a React Flow JSON",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def reactflow_validate_flow(
    flow_json: Annotated[str, Field(
        min_length=2,
        description="JSON string of the flow object: `{\"nodes\": [...], \"edges\": [...]}`. Same shape that `useReactFlow().toObject()` produces.",
    )],
    response_format: Annotated[ResponseFormat, Field(
        default=ResponseFormat.MARKDOWN,
        description="markdown | json",
    )] = ResponseFormat.MARKDOWN,
) -> str:
    """Lint a React Flow v12 flow object for common correctness issues.

    Hard errors include: missing/duplicate node or edge ids, edge endpoints
    pointing to non-existent nodes, malformed positions, v11 leftover fields
    (`parentNode`, `xPos`, `yPos`, `edge.updatable`), parent node appearing
    after its child (v12 requires parent-first ordering).

    Warnings include: cycles in the graph, parallel/duplicate edges,
    edge handle ids that don't match a node's `handles[]` array,
    `node.width`/`height` set as numbers (sets inline styles in v12),
    runtime-only fields (`positionAbsoluteX/Y`) persisted by mistake.

    Returns stats (counts, type histograms, root/leaf nodes, cycles) for
    quick orientation even when there are no issues.

    Returns JSON schema:
        {
          "ok": bool,
          "errors":   [{"code": str, "message": str, "ref": str?}],
          "warnings": [{"code": str, "message": str, "ref": str?}],
          "stats": {
            "nodes": int, "edges": int,
            "node_types": {str: int}, "edge_types": {str: int},
            "cycles": [[id, ...]],
            "root_nodes": [str], "leaf_nodes": [str]
          }
        }
    """
    try:
        parsed = json.loads(flow_json)
    except json.JSONDecodeError as e:
        return f"Error: invalid JSON — {e.msg} at line {e.lineno} col {e.colno}."

    report = validate_flow(parsed)

    def to_md(p: dict) -> str:
        s = p["stats"]
        lines = ["# React Flow validation report"]
        lines.append(f"\n**Status:** {'✅ OK' if p['ok'] else '❌ HAS ERRORS'}")
        lines.append(f"\n**Stats:** {s['nodes']} nodes, {s['edges']} edges")
        if s["node_types"]:
            lines.append(f"- Node types: " + ", ".join(f"`{k}`×{v}" for k, v in s["node_types"].items()))
        if s["edge_types"]:
            lines.append(f"- Edge types: " + ", ".join(f"`{k}`×{v}" for k, v in s["edge_types"].items()))
        if s["root_nodes"]:
            lines.append(f"- Roots (no incoming): {', '.join(f'`{x}`' for x in s['root_nodes'][:10])}" + (" …" if len(s["root_nodes"]) > 10 else ""))
        if s["leaf_nodes"]:
            lines.append(f"- Leaves (no outgoing): {', '.join(f'`{x}`' for x in s['leaf_nodes'][:10])}" + (" …" if len(s["leaf_nodes"]) > 10 else ""))
        if s["cycles"]:
            lines.append(f"- Cycles: {len(s['cycles'])}")
            for cy in s["cycles"][:5]:
                lines.append(f"  - {' → '.join(cy)}")

        if p["errors"]:
            lines.append("\n## ❌ Errors")
            for err in p["errors"]:
                ref = f" _({err['ref']})_" if err.get("ref") else ""
                lines.append(f"- `{err['code']}` — {err['message']}{ref}")
        if p["warnings"]:
            lines.append("\n## ⚠️ Warnings")
            for w in p["warnings"]:
                ref = f" _({w['ref']})_" if w.get("ref") else ""
                lines.append(f"- `{w['code']}` — {w['message']}{ref}")
        if not p["errors"] and not p["warnings"]:
            lines.append("\n_No issues found._")
        return "\n".join(lines)

    return _format_response(report, response_format, to_md)


# ─────────── tool 8: svelte_equivalent ───────────


@mcp.tool(
    name="reactflow_svelte_equivalent",
    annotations={
        "title": "React Flow → Svelte Flow symbol",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def reactflow_svelte_equivalent(
    symbol: Annotated[str, Field(
        min_length=1, max_length=80,
        description="React Flow symbol you want the Svelte Flow equivalent for. Examples: 'ReactFlow', 'useReactFlow', 'EdgeLabelRenderer', 'Background', 'addEdge', 'Handle'. Case-insensitive.",
    )],
    include_porting_notes: Annotated[bool, Field(
        default=True,
        description="Append the cross-cutting porting notes (state model, hooks shape, Svelte 5 requirement, Pro example subset).",
    )] = True,
    response_format: Annotated[ResponseFormat, Field(
        default=ResponseFormat.MARKDOWN,
        description="markdown | json",
    )] = ResponseFormat.MARKDOWN,
) -> str:
    """Map a React Flow symbol to its Svelte Flow (`@xyflow/svelte`) equivalent.

    Most symbols are identically named — only the import path changes.
    A handful are renamed: <ReactFlow>→<SvelteFlow>, <ReactFlowProvider>→
    <SvelteFlowProvider>, useReactFlow→useSvelteFlow, EdgeLabelRenderer→EdgeLabel.
    `EdgeReconnectAnchor` is Svelte-only.

    Returns JSON schema:
        {
          "react_symbol": str,
          "svelte_symbol": str | null,
          "found": bool,
          "status": "renamed" | "identical" | "svelte_only" | "unknown",
          "kind": str?, "note": str?,
          "react_import": "@xyflow/react",
          "svelte_import": "@xyflow/svelte",
          "suggestions": [str]?,
          "porting_notes": {state_model, custom_components, imports, svelte_version, hooks_return_shape, pro_examples_subset, release_train}?
        }
    """
    result = svelte_lookup(symbol)
    if include_porting_notes:
        result["porting_notes"] = PORTING_NOTES

    def to_md(p: dict) -> str:
        lines = [f"# `{p['react_symbol'] or symbol}` — React Flow → Svelte Flow"]
        status = p.get("status", "unknown")
        if status == "renamed":
            lines.append(f"\n🔄 **Renamed:** `{p['react_symbol']}` → **`{p['svelte_symbol']}`**  ({p.get('kind', '')})")
            lines.append(f"\nImport from `{p['svelte_import']}` (was `{p['react_import']}`).")
            if p.get("note"):
                lines.append(f"\n> {p['note']}")
        elif status == "identical":
            lines.append(f"\n✅ **Same name:** `{p['svelte_symbol']}` — just change the import path.")
            lines.append(f"\n```ts\n// React: import {{ {p['react_symbol']} }} from \"{p['react_import']}\";\n// Svelte: import {{ {p['svelte_symbol']} }} from \"{p['svelte_import']}\";\n```")
        elif status == "svelte_only":
            lines.append(f"\n🟣 **Svelte-only symbol** — no direct React Flow equivalent.")
            if p.get("note"):
                lines.append(f"\n> {p['note']}")
        else:  # unknown
            lines.append("\n❌ Not in mapping.")
            if p.get("suggestions"):
                lines.append("\nDid you mean:")
                lines.extend(f"- `{s}`" for s in p["suggestions"])

        if "porting_notes" in p:
            lines.append("\n## General porting notes")
            for k, v in p["porting_notes"].items():
                lines.append(f"- **{k}** — {v}")

        return "\n".join(lines)

    return _format_response(result, response_format, to_md)


# ─────────── resource: deep-dive doc ───────────


@mcp.resource(DEEP_DIVE_URI, name="React Flow deep-dive", mime_type="text/markdown")
async def deep_dive_resource() -> str:
    """Full bundled React Flow deep-dive markdown brief.

    Covers OSS Learn surface, API cheat-sheet, Pro paid layer, monorepo map,
    common gotchas, and v11→v12 migration. Canonical source the tools index into.
    """
    return _DEEP_DIVE_TEXT


# expose helpful aggregate for debugging / introspection from tests
def _self_check() -> dict:
    return {
        "server": SERVER_NAME,
        "deep_dive_chars": len(_DEEP_DIVE_TEXT),
        "sections": len(_SECTIONS),
        "api_catalog_entries": len(API_CATALOG),
        "migration_entries": len(SYMBOL_MIGRATION) + len(PACKAGE_MIGRATION),
        "pro_examples": len(PRO_EXAMPLES),
        "svelte_renamed": len(SVELTE_RENAMED),
        "svelte_identical": len(SVELTE_IDENTICAL),
        "svelte_only": len(SVELTE_ONLY),
        "tools": [
            "reactflow_search_docs",
            "reactflow_get_api",
            "reactflow_lookup_v11_v12",
            "reactflow_list_pro_examples",
            "reactflow_scaffold_custom_node",
            "reactflow_scaffold_custom_edge",
            "reactflow_validate_flow",
            "reactflow_svelte_equivalent",
        ],
        "resources": [DEEP_DIVE_URI],
    }
