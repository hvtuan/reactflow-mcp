"""Validator for React Flow v12 flow JSON.

Pure function — no MCP / IO coupling. Input is a parsed dict shaped like
`{ "nodes": [...], "edges": [...] }`. Output is a structured report
{ ok, errors, warnings, stats }.

Checks are split into hard errors (will break the flow) and soft warnings
(likely-wrong, but the flow still renders). Includes a DFS cycle detector
and v11 leftover detection.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

# v11 → v12 leftovers to catch
V11_NODE_FIELDS = {
    "parentNode": "parentId",
    "xPos": "(computed; remove — use position.x)",
    "yPos": "(computed; remove — use position.y)",
}
V11_EDGE_FIELDS = {
    "updatable": "reconnectable",
}


def _is_object(x: Any) -> bool:
    return isinstance(x, dict)


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _detect_cycles(adj: dict[str, list[str]], all_nodes: list[str]) -> list[list[str]]:
    """Return list of cycles found. Each cycle is a list of node ids."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in all_nodes}
    parent: dict[str, str | None] = {n: None for n in all_nodes}
    cycles: list[list[str]] = []

    def dfs(start: str) -> None:
        # iterative DFS so we can extract cycles
        stack: list[tuple[str, int]] = [(start, 0)]
        path: list[str] = []
        while stack:
            node, idx = stack[-1]
            if idx == 0:
                node_color = color.get(node, BLACK)  # treat unknown ids as already-processed
                if node_color == GRAY:
                    # back-edge to ancestor on path → cycle
                    if node in path:
                        i = path.index(node)
                        cycles.append(path[i:] + [node])
                    stack.pop()
                    continue
                if node_color == BLACK:
                    stack.pop()
                    continue
                color[node] = GRAY
                path.append(node)
            neighbors = adj.get(node, [])
            if idx < len(neighbors):
                stack[-1] = (node, idx + 1)
                stack.append((neighbors[idx], 0))
            else:
                color[node] = BLACK
                if path and path[-1] == node:
                    path.pop()
                stack.pop()

    for n in all_nodes:
        if color[n] == WHITE:
            dfs(n)

    # de-dupe by rotated canonical form
    seen: set[tuple[str, ...]] = set()
    unique: list[list[str]] = []
    for c in cycles:
        body = c[:-1] if c and c[0] == c[-1] else c
        if not body:
            continue
        # rotate to start at the lexicographically smallest node
        rotation_start = body.index(min(body))
        canon = tuple(body[rotation_start:] + body[:rotation_start])
        if canon not in seen:
            seen.add(canon)
            unique.append(list(canon) + [canon[0]])
    return unique


def validate_flow(flow: dict) -> dict:
    """Validate a React Flow v12 flow object.

    Returns:
        {
          "ok": bool,
          "errors":   [{"code": str, "message": str, "ref": str?}],
          "warnings": [{"code": str, "message": str, "ref": str?}],
          "stats": {
            "nodes": int, "edges": int,
            "node_types": {type: count},
            "edge_types": {type: count},
            "cycles": [[id, id, …]],
            "root_nodes": [id, …],      # nodes with no incoming edges
            "leaf_nodes": [id, …],      # nodes with no outgoing edges
          }
        }
    """
    errors: list[dict] = []
    warnings: list[dict] = []

    if not _is_object(flow):
        return {
            "ok": False,
            "errors": [{"code": "E_SHAPE", "message": "flow must be an object with 'nodes' and 'edges' arrays."}],
            "warnings": [],
            "stats": {"nodes": 0, "edges": 0, "node_types": {}, "edge_types": {}, "cycles": [], "root_nodes": [], "leaf_nodes": []},
        }

    nodes = flow.get("nodes")
    edges = flow.get("edges")

    if not isinstance(nodes, list):
        errors.append({"code": "E_SHAPE", "message": "'nodes' must be an array."})
        nodes = []
    if not isinstance(edges, list):
        errors.append({"code": "E_SHAPE", "message": "'edges' must be an array."})
        edges = []

    # ── node validation ──
    node_ids_seen: set[str] = set()
    node_order: list[str] = []
    node_handles: dict[str, set[str]] = {}  # id → set of explicit handle ids
    node_types_count: dict[str, int] = defaultdict(int)
    nodes_by_id: dict[str, dict] = {}

    for i, n in enumerate(nodes):
        ref = f"nodes[{i}]"
        if not _is_object(n):
            errors.append({"code": "E_NODE_SHAPE", "message": "node must be an object.", "ref": ref})
            continue
        nid = n.get("id")
        if not isinstance(nid, str) or not nid:
            errors.append({"code": "E_NODE_ID", "message": "node 'id' must be a non-empty string.", "ref": ref})
            continue
        if nid in node_ids_seen:
            errors.append({"code": "E_NODE_DUP", "message": f"duplicate node id '{nid}'.", "ref": ref})
        node_ids_seen.add(nid)
        node_order.append(nid)
        nodes_by_id[nid] = n

        pos = n.get("position")
        if not _is_object(pos) or not _is_number(pos.get("x")) or not _is_number(pos.get("y")):
            errors.append({"code": "E_NODE_POSITION", "message": "node 'position' must be { x: number, y: number }.", "ref": f"{ref} (id={nid})"})

        if "data" in n and not _is_object(n["data"]):
            errors.append({"code": "E_NODE_DATA", "message": "node 'data' must be an object.", "ref": f"{ref} (id={nid})"})

        node_types_count[n.get("type") or "default"] += 1

        # v11 leftovers
        for bad, replacement in V11_NODE_FIELDS.items():
            if bad in n:
                errors.append({
                    "code": "E_NODE_V11_FIELD",
                    "message": f"node has v11 field '{bad}' — use '{replacement}' in v12.",
                    "ref": f"{ref} (id={nid})",
                })

        # positionAbsolute — runtime only
        for runtime_field in ("positionAbsoluteX", "positionAbsoluteY", "positionAbsolute"):
            if runtime_field in n:
                warnings.append({
                    "code": "W_RUNTIME_FIELD",
                    "message": f"node has runtime-computed field '{runtime_field}'; don't persist it.",
                    "ref": f"{ref} (id={nid})",
                })

        # width/height in v12 SETS inline style — likely meant initialWidth/Height
        if isinstance(n.get("width"), (int, float)) or isinstance(n.get("height"), (int, float)):
            warnings.append({
                "code": "W_V12_WIDTH_HEIGHT",
                "message": "in v12, node.width/height SET inline styles (fixed size). For SSR or content-driven sizing prefer initialWidth/initialHeight, and read measured dims via node.measured.{width,height}.",
                "ref": f"{ref} (id={nid})",
            })

        # explicit handles array — collect ids for edge handle ref check
        explicit_handles = n.get("handles")
        if isinstance(explicit_handles, list):
            ids = set()
            for h in explicit_handles:
                if _is_object(h) and isinstance(h.get("id"), str):
                    ids.add(h["id"])
            node_handles[nid] = ids

    # parent ordering + missing parent check (after we've collected all ids)
    for i, n in enumerate(nodes):
        if not _is_object(n):
            continue
        nid = n.get("id")
        parent_id = n.get("parentId")
        if parent_id is None:
            continue
        if parent_id not in node_ids_seen:
            errors.append({
                "code": "E_PARENT_MISSING",
                "message": f"node '{nid}' has parentId='{parent_id}' but that node is not in 'nodes'.",
                "ref": f"nodes[{i}]",
            })
        else:
            parent_index = node_order.index(parent_id) if parent_id in node_order else -1
            if parent_index >= 0 and parent_index > i:
                errors.append({
                    "code": "E_PARENT_ORDER",
                    "message": f"node '{nid}' (index {i}) has parentId='{parent_id}' which appears LATER in the array (index {parent_index}). v12 requires parent before child.",
                    "ref": f"nodes[{i}]",
                })

    # ── edge validation ──
    edge_ids_seen: set[str] = set()
    edge_signatures: dict[tuple[str, str, str | None, str | None], int] = defaultdict(int)
    edge_types_count: dict[str, int] = defaultdict(int)
    adj: dict[str, list[str]] = defaultdict(list)
    incoming_counts: dict[str, int] = defaultdict(int)
    outgoing_counts: dict[str, int] = defaultdict(int)

    for i, e in enumerate(edges):
        ref = f"edges[{i}]"
        if not _is_object(e):
            errors.append({"code": "E_EDGE_SHAPE", "message": "edge must be an object.", "ref": ref})
            continue
        eid = e.get("id")
        if not isinstance(eid, str) or not eid:
            errors.append({"code": "E_EDGE_ID", "message": "edge 'id' must be a non-empty string.", "ref": ref})
            continue
        if eid in edge_ids_seen:
            errors.append({"code": "E_EDGE_DUP_ID", "message": f"duplicate edge id '{eid}'.", "ref": ref})
        edge_ids_seen.add(eid)

        src = e.get("source")
        tgt = e.get("target")
        if not isinstance(src, str) or not isinstance(tgt, str):
            errors.append({"code": "E_EDGE_ENDPOINT", "message": "edge 'source' and 'target' must be strings.", "ref": f"{ref} (id={eid})"})
            continue
        if src not in node_ids_seen:
            errors.append({"code": "E_EDGE_SRC_MISSING", "message": f"edge source '{src}' references a non-existent node.", "ref": f"{ref} (id={eid})"})
        if tgt not in node_ids_seen:
            errors.append({"code": "E_EDGE_TGT_MISSING", "message": f"edge target '{tgt}' references a non-existent node.", "ref": f"{ref} (id={eid})"})

        sh = e.get("sourceHandle")
        th = e.get("targetHandle")

        if isinstance(sh, str) and src in node_handles and node_handles[src] and sh not in node_handles[src]:
            warnings.append({
                "code": "W_EDGE_SRC_HANDLE_MISMATCH",
                "message": f"edge sourceHandle '{sh}' not present in source node '{src}'.handles[]. May silently render against the default handle.",
                "ref": f"{ref} (id={eid})",
            })
        if isinstance(th, str) and tgt in node_handles and node_handles[tgt] and th not in node_handles[tgt]:
            warnings.append({
                "code": "W_EDGE_TGT_HANDLE_MISMATCH",
                "message": f"edge targetHandle '{th}' not present in target node '{tgt}'.handles[]. May silently render against the default handle.",
                "ref": f"{ref} (id={eid})",
            })

        # duplicate (parallel) edges
        sig = (src, tgt, sh if isinstance(sh, str) else None, th if isinstance(th, str) else None)
        edge_signatures[sig] += 1
        if edge_signatures[sig] == 2:
            warnings.append({
                "code": "W_EDGE_DUP_PARALLEL",
                "message": f"parallel edge: another edge already connects {src}{f'#{sh}' if sh else ''} → {tgt}{f'#{th}' if th else ''}. React Flow will render both stacked.",
                "ref": f"{ref} (id={eid})",
            })

        # v11 leftovers
        for bad, replacement in V11_EDGE_FIELDS.items():
            if bad in e:
                errors.append({
                    "code": "E_EDGE_V11_FIELD",
                    "message": f"edge has v11 field '{bad}' — use '{replacement}' in v12.",
                    "ref": f"{ref} (id={eid})",
                })

        edge_types_count[e.get("type") or "default"] += 1

        # adjacency for cycle / root / leaf — skip edges with missing endpoints
        if src in node_ids_seen and tgt in node_ids_seen:
            adj[src].append(tgt)
            outgoing_counts[src] += 1
            incoming_counts[tgt] += 1

    cycles = _detect_cycles(adj, node_order) if node_order else []
    if cycles:
        warnings.append({
            "code": "W_CYCLE",
            "message": f"graph contains {len(cycles)} cycle(s). React Flow allows cycles, but downstream tooling (auto-layout, dataflow) may not.",
            "ref": None,
        })

    root_nodes = [nid for nid in node_order if incoming_counts.get(nid, 0) == 0]
    leaf_nodes = [nid for nid in node_order if outgoing_counts.get(nid, 0) == 0]

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "nodes": len(node_order),
            "edges": len(edge_ids_seen),
            "node_types": dict(node_types_count),
            "edge_types": dict(edge_types_count),
            "cycles": cycles,
            "root_nodes": root_nodes,
            "leaf_nodes": leaf_nodes,
        },
    }
