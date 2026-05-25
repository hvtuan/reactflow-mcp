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
    - reactflow_list_recipes          — list OSS recipes that clone Pro patterns
    - reactflow_get_recipe            — full copy-paste TSX for a specific recipe
    - reactflow_scaffold_flow         — generate a full working TSX app from a node/edge spec
    - reactflow_scaffold_workflow_app — full Vite or Next.js starter project (Pro template clone)
    - reactflow_render_flow           — render a flow JSON to Mermaid or ASCII tree
    - reactflow_explain_change        — explain a NodeChange / EdgeChange dispatch

Prompts:
    - review_flow_spec, migrate_v11_to_v12, clone_pro_feature, pick_layout_algorithm

Resource:
    - reactflow://deep-dive           — full deep-dive markdown brief
"""

from __future__ import annotations

import json
import os
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
from reactflow_mcp.data.recipes import RECIPES, get_recipe, list_recipes
from reactflow_mcp.data.svelte_equivalents import IDENTICAL as SVELTE_IDENTICAL
from reactflow_mcp.data.svelte_equivalents import PORTING_NOTES, RENAMED as SVELTE_RENAMED
from reactflow_mcp.data.svelte_equivalents import SVELTE_ONLY, lookup as svelte_lookup
from reactflow_mcp.prompts import clone_pro_feature, migrate_v11_to_v12, pick_layout_algorithm, review_flow_spec
from reactflow_mcp.renderers import explain_change, render_ascii, render_mermaid
from reactflow_mcp.scaffolders import scaffold_custom_edge, scaffold_custom_node, scaffold_flow
from reactflow_mcp.templates import scaffold_workflow_app
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

# Construct the server with HTTP-transport-friendly defaults read from env.
# When running over stdio the host/port/path settings are simply ignored.
mcp = FastMCP(
    SERVER_NAME,
    host=os.environ.get("MCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("MCP_PORT", "8000")),
    streamable_http_path=os.environ.get("MCP_HTTP_PATH", "/mcp"),
    # Stateless + json_response are friendlier for load-balanced HTTP deploys
    # (Coolify / Traefik etc.) — no per-session state to pin to a pod, and
    # the response is a plain JSON-RPC body instead of an SSE stream.
    stateless_http=os.environ.get("MCP_STATELESS_HTTP", "true").lower() == "true",
    json_response=os.environ.get("MCP_JSON_RESPONSE", "true").lower() == "true",
)


# ─────────── tool 1: search_docs ───────────


def _score(section: dict, query_lc: str) -> float:
    """Score a section against a query.

    Earlier version summed match counts, which made huge "cheat-sheet"
    sections beat smaller, topical ones. v2 normalizes by sqrt(body_size)
    so a small, on-topic section outranks a giant catch-all section that
    happens to mention the query token many times.
    """
    import math
    title = section["title"].lower()
    body = section["body"].lower()
    anchor = section.get("anchor", "")

    raw = 0.0
    # exact-substring title match is highest signal
    if query_lc in title:
        raw += 20
    if query_lc.replace(" ", "-") == anchor or query_lc == anchor.split("/")[-1]:
        raw += 30   # anchor exact match (e.g. query 'edge-labels' hits the section anchor)
    # body substring matches
    raw += body.count(query_lc) * 2
    # token-level
    tokens = [t for t in query_lc.split() if len(t) >= 3]
    for token in tokens:
        if token in title:
            raw += 5
        raw += body.count(token) * 0.5

    # H3 sub-sections (more specific) get a bonus
    if section.get("level") == 3:
        raw += 3

    # normalize by sqrt size — big sections dominated v1
    size_penalty = math.sqrt(max(1, len(body)) / 200)   # 200 chars = 1.0, 5000 chars ≈ 5x penalty
    return raw / size_penalty


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

    **When to use:**
    - User asks a conceptual "how do I…" / "what does X mean" question.
    - You need quick context on perf, SSR, multiplayer, computing-flows, theming,
      v11→v12 migration, Pro layer, troubleshooting, or gotchas.
    - Multiple symbols may be involved and you want orientation before drilling in.

    **Don't use when:**
    - User wants a SINGLE API symbol's signature → use `reactflow_get_api`.
    - User has a v11 symbol and wants the v12 equivalent → use `reactflow_lookup_v11_v12`.
    - User wants ready-to-paste code for a known pattern (auto-layout, undo-redo, …)
      → use `reactflow_get_recipe` (covers ~13 Pro-equivalent patterns).

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

    Returns kind (component/hook/util/type/enum/callback), signature, props/params,
    notes, deprecation status, OSS/Pro flag.

    **When to use:**
    - User asks "what does `useReactFlow` return?" / "what props does `<Handle>` take?".
    - You're about to write code and need the exact signature of an API.
    - You suspect a symbol is deprecated and want to confirm + get the replacement.
    - 113 React Flow symbols covered (components, hooks, utils, types, enums, callbacks).

    **Don't use when:**
    - You don't know the symbol name → use `reactflow_search_docs` with a topic keyword.
    - You're looking for a recipe / code pattern → use `reactflow_get_recipe`.
    - You have a v11 symbol → `reactflow_lookup_v11_v12` (returns the v12 name).

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

    **When to use:**
    - You see (or are about to emit) v11 code: imports from `reactflow`, uses
      `parentNode`, `xPos`/`yPos`, `onEdgeUpdate`, `project()`, `nodeInternals`,
      `useHandleConnections`, etc.
    - User asks "how do I migrate from v11 to v12?".
    - A symbol you remembered doesn't exist in v12 catalog — try here before
      assuming deprecation.

    **Don't use when:**
    - Symbol already exists in v12 catalog (use `reactflow_get_api`).
    - User wants the full migration overview — return the full v12 behavior-change
      list (this tool always includes it) but also point to `reactflow_search_docs`
      with `section='v11 → v12 migration'`.

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


# ─────────── tool 9: list_recipes ───────────


@mcp.tool(
    name="reactflow_list_recipes",
    annotations={
        "title": "List OSS recipes that clone Pro patterns",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def reactflow_list_recipes(
    category: Annotated[Optional[str], Field(
        default=None,
        description="Filter by category: 'layout' | 'history' | 'interaction' | 'nodes' | 'grouping' | 'edges' | 'misc'.",
    )] = None,
    response_format: Annotated[ResponseFormat, Field(
        default=ResponseFormat.MARKDOWN,
        description="markdown | json",
    )] = ResponseFormat.MARKDOWN,
) -> str:
    """List copy-paste OSS recipes that replicate React Flow Pro examples.

    Each recipe covers a Pro-paid pattern (auto-layout, undo/redo,
    copy/paste, helper lines, expand/collapse, force layout, editable edge,
    shapes node, selection grouping, server-side image, node position
    animation, remove attribution) using only the free `@xyflow/react` v12
    library plus widely-available npm packages (dagre, elkjs, d3-force).

    Use this BEFORE recommending a Pro subscription — most users can ship
    these patterns themselves from the recipe code.

    Returns JSON schema:
        {
          "filter": {"category": str?},
          "count": int,
          "recipes": [
            {"name": str, "title": str, "category": str, "clones_pro": str?,
             "summary": str, "deps": [str], "files": [str]}
          ]
        }
    """
    items = list_recipes(category=category)
    payload = {
        "filter": {"category": category},
        "count": len(items),
        "recipes": items,
    }

    def to_md(p: dict) -> str:
        lines = ["# React Flow OSS recipes (Pro-pattern alternatives)"]
        if p["filter"]["category"]:
            lines.append(f"_filter: category=`{p['filter']['category']}`_")
        lines.append(f"\n**{p['count']} recipe(s).**\n")
        by_cat: dict[str, list] = {}
        for r in p["recipes"]:
            by_cat.setdefault(r["category"], []).append(r)
        for cat, rs in by_cat.items():
            lines.append(f"## {cat}")
            for r in rs:
                pro = f" _(clones Pro: **{r['clones_pro']}**)_" if r.get("clones_pro") else ""
                deps = ", ".join(r["deps"]) if r["deps"] else "_none_"
                lines.append(f"- **`{r['name']}`** — {r['title']}{pro}")
                lines.append(f"  - {r['summary']}")
                lines.append(f"  - deps: {deps} · files: {', '.join(f'`{f}`' for f in r['files'])}")
            lines.append("")
        lines.append("Fetch full code via `reactflow_get_recipe(name=...)`.")
        return "\n".join(lines)

    return _format_response(payload, response_format, to_md)


# ─────────── tool 10: get_recipe ───────────


@mcp.tool(
    name="reactflow_get_recipe",
    annotations={
        "title": "Get a full OSS recipe",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def reactflow_get_recipe(
    name: Annotated[str, Field(
        min_length=1, max_length=80,
        description="Recipe slug (snake_case). Examples: 'auto_layout_dagre', 'undo_redo', 'copy_paste', 'helper_lines', 'expand_collapse', 'force_layout', 'editable_edge', 'shapes_node', 'selection_grouping', 'node_position_animation', 'server_side_image', 'remove_attribution'. List all via `reactflow_list_recipes`.",
    )],
    response_format: Annotated[ResponseFormat, Field(
        default=ResponseFormat.MARKDOWN,
        description="markdown | json",
    )] = ResponseFormat.MARKDOWN,
) -> str:
    """Fetch the full copy-paste TSX recipe for an OSS Pro-pattern clone.

    Returns the problem statement, high-level approach, list of @xyflow/react
    APIs used, npm dependencies needed, one or more full source files
    (TSX/TS), known gotchas, and reference URLs.

    **When to use:**
    - User asks "how do I add auto-layout / undo/redo / copy-paste / helper lines
      / expand-collapse / force layout / shapes / editable edges / server-side
      image / freehand draw to my flow?".
    - User is considering React Flow Pro for a specific example — this MCP
      gives them the OSS implementation instead. (Project mission: replace Pro,
      not recommend it.)
    - You need production-tested boilerplate, not a hand-written attempt.

    **Don't use when:**
    - You don't know the recipe slug → call `reactflow_list_recipes` first.
    - User wants the underlying API doc, not a recipe → `reactflow_get_api`.

    Returns JSON schema:
        {
          "name": str, "found": bool,
          "title": str?, "category": str?, "clones_pro": str?,
          "summary": str?, "problem": str?, "approach": str?,
          "apis_used": [str]?, "deps": [str]?,
          "files": {filename: source}?,
          "gotchas": [str]?, "references": [str]?,
          "suggestions": [str]?    // if not found
        }
    """
    recipe = get_recipe(name)
    if recipe is None:
        all_names = sorted(RECIPES.keys())
        q = name.lower()
        suggestions = [n for n in all_names if q in n.lower() or n.lower() in q][:8]
        payload = {"name": name, "found": False, "suggestions": suggestions or all_names}

        def to_md_miss(p: dict) -> str:
            lines = [f"# Recipe `{p['name']}` — not found"]
            lines.append("\nAvailable recipes:")
            lines.extend(f"- `{s}`" for s in p["suggestions"])
            return "\n".join(lines)

        return _format_response(payload, response_format, to_md_miss)

    payload = {"found": True, **recipe}

    def to_md(p: dict) -> str:
        lines = [f"# `{p['name']}` — {p['title']}"]
        if p.get("clones_pro"):
            lines.append(f"\n_Clones React Flow Pro example: **{p['clones_pro']}**_")
        lines.append(f"\n**Summary.** {p['summary']}")
        lines.append(f"\n**Problem.** {p['problem']}")
        lines.append(f"\n**Approach.** {p['approach']}")
        if p.get("apis_used"):
            lines.append(f"\n**APIs used:** " + ", ".join(f"`{a}`" for a in p["apis_used"]))
        if p.get("deps"):
            deps_str = ", ".join(f"`{d}`" for d in p["deps"]) if p["deps"] else "_(none)_"
            lines.append(f"\n**npm deps (besides `@xyflow/react`):** {deps_str}")
        if p.get("files"):
            lines.append("\n## Code")
            for fname, src in p["files"].items():
                # infer language from extension
                ext = fname.rsplit(".", 1)[-1] if "." in fname else "txt"
                lang_map = {"tsx": "tsx", "ts": "ts", "css": "css", "snippet": "tsx"}
                # handle .tsx.snippet style
                if fname.endswith(".snippet"):
                    inner_ext = fname[:-len(".snippet")].rsplit(".", 1)[-1]
                    lang = lang_map.get(inner_ext, "txt")
                else:
                    lang = lang_map.get(ext, "txt")
                lines.append(f"\n### `{fname}`\n\n```{lang}\n{src.rstrip()}\n```")
        if p.get("gotchas"):
            lines.append("\n## Gotchas")
            lines.extend(f"- {g}" for g in p["gotchas"])
        if p.get("references"):
            lines.append("\n## References")
            lines.extend(f"- {r}" for r in p["references"])
        return "\n".join(lines)

    return _format_response(payload, response_format, to_md)


# ─────────── tool 11: scaffold_flow ───────────


@mcp.tool(
    name="reactflow_scaffold_flow",
    annotations={
        "title": "Scaffold a full React Flow TSX app",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def reactflow_scaffold_flow(
    nodes: Annotated[Optional[list[dict]], Field(
        default=None,
        description="List of nodes: [{id, type?: 'input'|'output'|'default'|'group'|custom, label?, position?:{x,y}, data?:{...}}]. Default = 3-node linear flow.",
    )] = None,
    edges: Annotated[Optional[list[dict]], Field(
        default=None,
        description="List of edges: [{id?, source, target, type?: 'default'|'smoothstep'|'step'|'straight'|'simplebezier'|custom, label?}]. Source/target must reference node ids.",
    )] = None,
    interactive: Annotated[bool, Field(
        default=True,
        description="If true, use useNodesState/useEdgesState + onConnect (editable). If false, use defaultNodes/defaultEdges (read-only).",
    )] = True,
    layout: Annotated[str, Field(
        default="none",
        description="Auto-layout strategy: 'none' (use provided positions) | 'dagre-tb' (top-down tree) | 'dagre-lr' (left-right tree). dagre layouts inject useAutoLayout hook + wrap in ReactFlowProvider.",
    )] = "none",
    with_minimap: Annotated[bool, Field(default=True, description="Include <MiniMap />.")] = True,
    with_controls: Annotated[bool, Field(default=True, description="Include <Controls />.")] = True,
    with_background: Annotated[bool, Field(default=True, description="Include <Background />.")] = True,
    background_variant: Annotated[str, Field(
        default="dots",
        description="Background pattern: 'dots' | 'lines' | 'cross'.",
    )] = "dots",
    color_mode: Annotated[str, Field(
        default="system",
        description="Theme: 'light' | 'dark' | 'system'.",
    )] = "system",
    fit_view: Annotated[bool, Field(default=True, description="Auto-fit viewport on mount.")] = True,
    hide_attribution: Annotated[bool, Field(
        default=False,
        description="Hide bottom-right attribution badge (proOptions.hideAttribution).",
    )] = False,
    response_format: Annotated[ResponseFormat, Field(
        default=ResponseFormat.MARKDOWN,
        description="markdown | json",
    )] = ResponseFormat.MARKDOWN,
) -> str:
    """Generate a complete working TSX file for a React Flow app from a spec.

    Produces a single `App.tsx` ready to drop into a Vite/Next.js project,
    including imports, initial state, optional auto-layout hook (dagre),
    Background / Controls / MiniMap children, and color-mode/fitView config.

    Returns JSON schema:
        {
          "app": str,            // full TSX source
          "deps": [str],         // npm packages to install
          "warnings": [str]
        }
    """
    try:
        result = scaffold_flow(
            nodes=nodes,
            edges=edges,
            interactive=interactive,
            layout=layout,
            with_minimap=with_minimap,
            with_controls=with_controls,
            with_background=with_background,
            background_variant=background_variant,
            color_mode=color_mode,
            fit_view=fit_view,
            hide_attribution=hide_attribution,
        )
    except ValueError as e:
        return f"Error: {e}"

    def to_md(p: dict) -> str:
        lines = ["# Scaffolded React Flow app"]
        for w in p["warnings"]:
            lines.append(f"\n> ⚠️ {w}")
        deps_str = " ".join(p["deps"])
        lines.append(f"\n**Install:**\n\n```bash\nnpm install {deps_str}\n```")
        lines.append(f"\n## `App.tsx`\n\n```tsx\n{p['app'].rstrip()}\n```")
        return "\n".join(lines)

    return _format_response(result, response_format, to_md)


# ─────────── tool 12: scaffold_workflow_app ───────────


@mcp.tool(
    name="reactflow_scaffold_workflow_app",
    annotations={
        "title": "Scaffold a full workflow-editor app (Pro template clone)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def reactflow_scaffold_workflow_app(
    name: Annotated[str, Field(
        default="my-workflow-editor", min_length=1, max_length=64,
        description="Project directory name (safe identifier, no slashes/spaces).",
    )] = "my-workflow-editor",
    stack: Annotated[str, Field(
        default="vite",
        description="'vite' (React + Vite, simpler) | 'nextjs' (Next.js 15 App Router, has built-in /api/chat route for AI).",
    )] = "vite",
    with_ai: Annotated[bool, Field(
        default=False,
        description="Add an AI side-panel (Vercel AI SDK `useChat`) that takes the current flow as context and can return JSON patches the user applies. Clones the Pro 'AI Workflow Editor' template.",
    )] = False,
    persist: Annotated[str, Field(
        default="localstorage",
        description="State persistence: 'localstorage' (zundo-style via Zustand persist), 'supabase' (commented placeholders + schema TODO), 'none'.",
    )] = "localstorage",
    with_sidebar: Annotated[bool, Field(
        default=True,
        description="Include drag-and-drop node-palette sidebar.",
    )] = True,
    response_format: Annotated[ResponseFormat, Field(
        default=ResponseFormat.MARKDOWN,
        description="markdown | json",
    )] = ResponseFormat.MARKDOWN,
) -> str:
    """Generate a complete workflow-editor starter app (Pro template clone).

    Produces a multi-file project: package.json + tsconfig + vite/next config +
    entry point + `<Flow>` with Zustand store + custom TaskNode (todo/doing/done)
    + drag-drop sidebar palette + undo/redo + export JSON toolbar.
    With `with_ai=true`, adds an `<AiPanel>` driven by Vercel AI SDK.

    Replaces the paid React Flow Pro "Workflow Editor" + "AI Workflow Editor"
    templates with an OSS equivalent.

    Returns JSON schema:
        {
          "name": str,
          "stack": "vite" | "nextjs",
          "files": {path: source},   // write each at <name>/<path>
          "deps": [str],
          "next_steps": [str]
        }
    """
    try:
        result = scaffold_workflow_app(
            name=name,
            stack=stack,
            with_ai=with_ai,
            persist=persist,
            with_sidebar=with_sidebar,
        )
    except ValueError as e:
        return f"Error: {e}"

    def to_md(p: dict) -> str:
        lines = [f"# Workflow editor scaffold — `{p['name']}` ({p['stack']})"]
        lines.append(f"\n**Files** ({len(p['files'])}):")
        for path in sorted(p["files"]):
            lines.append(f"- `{path}`")
        lines.append("\n**Dependencies (informational):**")
        lines.append("```bash\nnpm install " + " ".join(p["deps"]) + "\n```")
        lines.append("\n**Next steps:**")
        for i, step in enumerate(p["next_steps"], 1):
            lines.append(f"{i}. {step}")
        lines.append("\n## File contents")
        for path, src in p["files"].items():
            ext = path.rsplit(".", 1)[-1] if "." in path else "txt"
            lang_map = {"tsx": "tsx", "ts": "ts", "json": "json", "html": "html", "js": "js", "md": "markdown"}
            lang = lang_map.get(ext, "txt")
            lines.append(f"\n### `{path}`\n\n```{lang}\n{src.rstrip()}\n```")
        return "\n".join(lines)

    return _format_response(result, response_format, to_md)


# ─────────── tool 13: render_flow ───────────


@mcp.tool(
    name="reactflow_render_flow",
    annotations={
        "title": "Render a flow JSON to Mermaid or ASCII",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def reactflow_render_flow(
    flow_json: Annotated[str, Field(
        min_length=2,
        description="JSON string of the flow object: `{nodes, edges}`.",
    )],
    format: Annotated[str, Field(
        default="mermaid",
        description="Output format: 'mermaid' (renders in any markdown viewer / GitHub) | 'ascii' (text outline tree).",
    )] = "mermaid",
    direction: Annotated[str, Field(
        default="TB",
        description="Mermaid layout direction: 'TB' (top-down) | 'BT' (bottom-up) | 'LR' (left-right) | 'RL' (right-left). Ignored for ascii.",
    )] = "TB",
    response_format: Annotated[ResponseFormat, Field(
        default=ResponseFormat.MARKDOWN,
        description="markdown | json",
    )] = ResponseFormat.MARKDOWN,
) -> str:
    """Render a React Flow JSON to a visual preview (Mermaid or ASCII tree).

    **When to use:**
    - LLM just generated a flow JSON and wants to sanity-check structure without
      asking the user to spin up a React app.
    - Document a flow inside a markdown doc / PR description (Mermaid renders in GitHub).
    - Quick visual check of cycles / branching during debugging.

    Returns JSON schema:
        { "format": str, "direction": str?, "output": str }
    """
    import json as _json
    try:
        flow = _json.loads(flow_json)
    except _json.JSONDecodeError as e:
        return f"Error: invalid JSON — {e.msg} at line {e.lineno} col {e.colno}."
    try:
        if format == "mermaid":
            out = render_mermaid(flow, direction=direction)
        elif format == "ascii":
            out = render_ascii(flow)
        else:
            return f"Error: format must be 'mermaid' or 'ascii', got {format!r}."
    except ValueError as e:
        return f"Error: {e}"

    payload = {"format": format, "direction": direction if format == "mermaid" else None, "output": out}

    def to_md(p: dict) -> str:
        if p["format"] == "mermaid":
            return f"# Flow preview (Mermaid)\n\n```mermaid\n{p['output']}\n```"
        return f"# Flow preview (ASCII tree)\n\n```\n{p['output']}\n```"

    return _format_response(payload, response_format, to_md)


# ─────────── tool 14: explain_change ───────────


@mcp.tool(
    name="reactflow_explain_change",
    annotations={
        "title": "Explain a NodeChange / EdgeChange dispatch",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def reactflow_explain_change(
    change_json: Annotated[str, Field(
        min_length=2,
        description="JSON string of a single NodeChange or EdgeChange object — what RF passes into your onNodesChange/onEdgesChange handler.",
    )],
    response_format: Annotated[ResponseFormat, Field(
        default=ResponseFormat.MARKDOWN,
        description="markdown | json",
    )] = ResponseFormat.MARKDOWN,
) -> str:
    """Explain a single React Flow NodeChange or EdgeChange in plain English.

    **When to use:**
    - You're staring at a `console.log(changes)` dump and don't know what each
      change type means or when it fires.
    - You're writing an undo/redo, history, or analytics layer and need to know
      which change types are safe to snapshot (`dragging=true` position changes
      = no, `dragStop` / `add` / `remove` = yes).

    Returns JSON schema:
        {
          "ok": bool,
          "type": str,        // 'add' | 'remove' | 'replace' | 'position' | 'dimensions' | 'select'
          "kind": str,        // 'node' | 'edge' | 'node-or-edge' | 'unknown'
          "explanation": str,
          "recipe_hint": str? // pointer to relevant recipe (e.g. undo_redo)
        }
    """
    import json as _json
    try:
        change = _json.loads(change_json)
    except _json.JSONDecodeError as e:
        return f"Error: invalid JSON — {e.msg}."
    result = explain_change(change)

    def to_md(p: dict) -> str:
        lines = [f"# Change explainer — `{p.get('type', '?')}` ({p.get('kind', '?')})"]
        if not p.get("ok"):
            lines.append(f"\n⚠️ {p.get('error') or p.get('explanation')}")
            return "\n".join(lines)
        lines.append(f"\n{p['explanation']}")
        if p.get("recipe_hint"):
            lines.append(f"\n**Hint:** {p['recipe_hint']}")
        return "\n".join(lines)

    return _format_response(result, response_format, to_md)


# ─────────── prompts ───────────


@mcp.prompt(
    name="review_flow_spec",
    title="Review a React Flow JSON spec",
    description="Structured walkthrough that validates a flow JSON, surfaces v11 leftovers, cycles, and produces a code-review-style verdict.",
)
def _prompt_review_flow_spec(flow_json: str) -> str:
    """Args: flow_json (str) — JSON string of {nodes, edges}."""
    return review_flow_spec(flow_json)


@mcp.prompt(
    name="migrate_v11_to_v12",
    title="Migrate React Flow v11 → v12",
    description="Walks the LLM through every rename, immutability change, and dim-semantic shift between v11 (reactflow) and v12 (@xyflow/react).",
)
def _prompt_migrate_v11_to_v12(code_snippet: str) -> str:
    """Args: code_snippet (str) — a TSX/TS snippet using v11 React Flow."""
    return migrate_v11_to_v12(code_snippet)


@mcp.prompt(
    name="clone_pro_feature",
    title="Clone a React Flow Pro example with OSS recipes",
    description="Orchestrate list_recipes + get_recipe + search_docs to deliver the OSS implementation of a Pro example — never recommends buying Pro.",
)
def _prompt_clone_pro_feature(feature: str) -> str:
    """Args: feature (str) — Pro example name (e.g. 'Auto Layout', 'Undo/Redo', 'Helper Lines', 'Editable Edge')."""
    return clone_pro_feature(feature)


@mcp.prompt(
    name="pick_layout_algorithm",
    title="Pick the right auto-layout for a graph",
    description="Given graph size, edge density, and topology shape, picks dagre vs elkjs vs d3-force and delivers the recipe.",
)
def _prompt_pick_layout_algorithm(node_count: int, edge_density: str, shape: str) -> str:
    """Args:
        node_count (int) — number of nodes (e.g. 5, 50, 500).
        edge_density (str) — 'sparse' | 'dense'.
        shape (str) — 'hierarchical' | 'organic' | 'directed-acyclic' | 'cyclic'.
    """
    return pick_layout_algorithm(node_count, edge_density, shape)


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
            "reactflow_list_recipes",
            "reactflow_get_recipe",
            "reactflow_scaffold_flow",
            "reactflow_scaffold_workflow_app",
            "reactflow_render_flow",
            "reactflow_explain_change",
        ],
        "recipes": len(RECIPES),
        "prompts": [
            "review_flow_spec",
            "migrate_v11_to_v12",
            "clone_pro_feature",
            "pick_layout_algorithm",
        ],
        "resources": [DEEP_DIVE_URI],
    }
