"""Pure-function flow renderers for visual previews + change explainers."""

from __future__ import annotations

from typing import Any

MERMAID_DIRECTIONS = {"TB", "BT", "LR", "RL"}


def _node_shape(node: dict) -> tuple[str, str]:
    """Pick the mermaid node shape based on the node's type. Returns (open, close)."""
    t = (node.get("type") or "default").lower()
    if t == "input":
        return "([", "])"
    if t == "output":
        return "[/", "/]"
    if t == "group":
        return "[(", ")]"
    # custom shapes
    if "shape" in (node.get("data") or {}):
        s = node["data"]["shape"]
        return {
            "diamond": ("{", "}"),
            "ellipse": ("([", "])"),
            "hexagon": ("{{", "}}"),
            "cylinder": ("[(", ")]"),
        }.get(s, ("[", "]"))
    return ("[", "]")


def _node_label(node: dict) -> str:
    data = node.get("data") or {}
    label = data.get("label") or node.get("id")
    return str(label).replace('"', "&quot;").replace("\n", " ")


def render_mermaid(flow: dict, direction: str = "TB") -> str:
    """Render a flow JSON to Mermaid flowchart syntax."""
    if direction not in MERMAID_DIRECTIONS:
        raise ValueError(f"direction must be one of {sorted(MERMAID_DIRECTIONS)}")
    nodes = flow.get("nodes") or []
    edges = flow.get("edges") or []

    lines = [f"flowchart {direction}"]
    for n in nodes:
        if not isinstance(n, dict) or "id" not in n:
            continue
        if n.get("hidden"):
            continue
        nid = str(n["id"]).replace(" ", "_")
        open_, close_ = _node_shape(n)
        lines.append(f'  {nid}{open_}"{_node_label(n)}"{close_}')

    for e in edges:
        if not isinstance(e, dict) or "source" not in e or "target" not in e:
            continue
        if e.get("hidden"):
            continue
        src = str(e["source"]).replace(" ", "_")
        tgt = str(e["target"]).replace(" ", "_")
        label = e.get("label")
        arrow = "-.->" if e.get("animated") else "-->"
        if label:
            label_str = str(label).replace('"', "'")
            lines.append(f"  {src} {arrow}|{label_str}| {tgt}")
        else:
            lines.append(f"  {src} {arrow} {tgt}")

    return "\n".join(lines)


def render_ascii(flow: dict, max_width: int = 60) -> str:
    """Simple textual outline (not true ASCII art) — sources → targets per node."""
    nodes = {n["id"]: n for n in (flow.get("nodes") or []) if isinstance(n, dict) and "id" in n}
    edges = flow.get("edges") or []
    out_edges: dict[str, list[tuple[str, str | None]]] = {nid: [] for nid in nodes}
    in_degree: dict[str, int] = {nid: 0 for nid in nodes}
    for e in edges:
        s, t = e.get("source"), e.get("target")
        if s in out_edges and t in nodes:
            out_edges[s].append((t, e.get("label")))
            in_degree[t] = in_degree.get(t, 0) + 1

    roots = [nid for nid in nodes if in_degree.get(nid, 0) == 0]
    lines: list[str] = []
    visited: set[str] = set()

    def walk(nid: str, prefix: str = "", is_last: bool = True) -> None:
        if nid in visited:
            lines.append(f"{prefix}{'└── ' if is_last else '├── '}{nid} (cycle)")
            return
        visited.add(nid)
        n = nodes.get(nid)
        if not n:
            return
        label = _node_label(n)
        type_tag = f" [{n.get('type')}]" if n.get("type") else ""
        head = f"{prefix}{'└── ' if is_last else '├── '}" if prefix else ""
        line = f"{head}{nid}: {label}{type_tag}"
        lines.append(line[:max_width] + ("…" if len(line) > max_width else ""))
        children = out_edges.get(nid, [])
        new_prefix = prefix + ("    " if is_last else "│   ")
        for i, (cid, lbl) in enumerate(children):
            walk(cid, new_prefix, i == len(children) - 1)

    if not roots:
        # all nodes are in cycles or no nodes
        if nodes:
            lines.append("(no root nodes — all are in cycles or referenced by edges with missing sources)")
            for nid in nodes:
                walk(nid)
        else:
            lines.append("(empty flow)")
    else:
        for i, r in enumerate(roots):
            walk(r, "", i == len(roots) - 1)

    return "\n".join(lines)


# ───────────────────────── change explainer ─────────────────────────


def explain_change(change: dict) -> dict:
    """Explain a single React Flow NodeChange or EdgeChange dispatch."""
    if not isinstance(change, dict):
        return {"ok": False, "error": "change must be an object"}
    t = change.get("type")
    out: dict[str, Any] = {"ok": True, "type": t, "kind": "unknown"}

    NODE_TYPES = {"add", "remove", "replace", "position", "dimensions", "select"}
    EDGE_TYPES = {"add", "remove", "replace", "select"}

    # heuristic — node changes have 'item' or 'id' + position/dimensions; edge changes use 'item' or 'id'
    is_node = t in NODE_TYPES and ("position" in change or "dimensions" in change or change.get("item", {}).get("position") is not None)
    is_edge = t in EDGE_TYPES and not is_node

    if t == "add":
        out["kind"] = "node" if "position" in (change.get("item") or {}) else "edge"
        out["explanation"] = (
            f"Insert a new {out['kind']} into the flow. The reducer (applyNodeChanges / applyEdgeChanges) will append `change.item` "
            "to the state array. Triggered by addNodes/addEdges, paste, or programmatic insertion."
        )
    elif t == "remove":
        out["kind"] = "node" if change.get("id") in (change.get("idsContext") or []) else "node-or-edge"
        out["explanation"] = (
            f"Delete the {out['kind']} with id `{change.get('id')}`. The reducer removes it from the array. "
            "Triggered by Delete key, deleteElements, or user clicking a delete button."
        )
    elif t == "replace":
        out["kind"] = "node-or-edge"
        out["explanation"] = (
            f"Replace the existing {out['kind']} (id `{change.get('id')}`) with `change.item`. Used for full-object updates that aren't just position/dimensions."
        )
    elif t == "position":
        out["kind"] = "node"
        dragging = change.get("dragging")
        pos = change.get("position")
        out["explanation"] = (
            f"Move node `{change.get('id')}` to `{pos}`. `dragging={dragging}` — "
            + ("user is actively dragging; this fires per pixel; DO NOT snapshot history here" if dragging else "drag end / programmatic move; safe to snapshot in undo/redo")
            + "."
        )
    elif t == "dimensions":
        out["kind"] = "node"
        out["explanation"] = (
            f"Node `{change.get('id')}` was measured by RF. `change.dimensions` = {change.get('dimensions')}. "
            "Fires after DOM mount or NodeResizer change. Triggers re-layout passes."
        )
    elif t == "select":
        out["kind"] = "node-or-edge"
        out["explanation"] = (
            f"Selection state for `{change.get('id')}` is now `selected={change.get('selected')}`. "
            "Fires on click + multi-select + box-select."
        )
    else:
        out["explanation"] = f"Unknown change type `{t}` — not part of @xyflow/react v12 NodeChange/EdgeChange unions."
        out["ok"] = False

    out["recipe_hint"] = {
        "position": "If you wrap setNodes with undo/redo, snapshot ONLY on onNodeDragStart, not per position change. See recipe `undo_redo`.",
        "add":     "If you want history to capture programmatic adds, call takeSnapshot() before addNodes. See recipe `undo_redo`.",
        "remove":  "Use onBeforeDelete prop to gate deletion (e.g., confirm dialog). Signature: `(params) => boolean | Promise<boolean>`.",
        "dimensions": "Don't react to this in your own state — RF handles it internally. Useful for waiting on useNodesInitialized for layout.",
    }.get(t or "")

    return out
