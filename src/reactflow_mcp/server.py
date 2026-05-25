"""reactflow_mcp — FastMCP server exposing React Flow knowledge to LLMs.

Tools:
    - reactflow_search_docs       — full-text search across the deep-dive doc
    - reactflow_get_api           — structured lookup of a public API symbol
    - reactflow_lookup_v11_v12    — v11/v10 → v12 migration map
    - reactflow_list_pro_examples — Pro paid examples catalog (+ filtering)

Resource:
    - reactflow://deep-dive       — full deep-dive markdown brief
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
        "tools": [
            "reactflow_search_docs",
            "reactflow_get_api",
            "reactflow_lookup_v11_v12",
            "reactflow_list_pro_examples",
        ],
        "resources": [DEEP_DIVE_URI],
    }
