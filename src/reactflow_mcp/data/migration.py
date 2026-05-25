"""v10 / v11 → v12 migration map for React Flow.

Used by the `lookup_v11_v12` tool to auto-correct stale code suggestions.
Source: https://reactflow.dev/learn/troubleshooting/migrate-to-v12 (snapshot 2026-05-25).
"""

from __future__ import annotations

# package + entry-point renames
PACKAGE_MIGRATION = {
    "reactflow": {
        "replacement": "@xyflow/react",
        "kind": "package",
        "note": "Package renamed. Default export gone — use named imports only.",
    },
}

# symbol-level renames / removals
SYMBOL_MIGRATION: dict[str, dict] = {
    # node fields
    "parentNode": {
        "replacement": "parentId",
        "kind": "node-field",
        "since": "v12.0.0",
        "note": "Now a string id, not a ref. Deprecated since v11.11.0, removed in v12.",
    },
    # custom node props
    "xPos": {"replacement": "positionAbsoluteX", "kind": "custom-node-prop", "since": "v12.0.0"},
    "yPos": {"replacement": "positionAbsoluteY", "kind": "custom-node-prop", "since": "v12.0.0"},

    # node measured dimensions
    "node.width": {
        "replacement": "node.measured.width",
        "kind": "node-field",
        "since": "v12.0.0",
        "note": "In v12, node.width/height SET inline style (fixed size). Runtime measured values moved to node.measured.{width,height}.",
    },
    "node.height": {
        "replacement": "node.measured.height",
        "kind": "node-field",
        "since": "v12.0.0",
        "note": "See node.width.",
    },

    # edge reconnection rename
    "onEdgeUpdate": {"replacement": "onReconnect", "kind": "event", "since": "v12.0.0"},
    "onEdgeUpdateStart": {"replacement": "onReconnectStart", "kind": "event", "since": "v12.0.0"},
    "onEdgeUpdateEnd": {"replacement": "onReconnectEnd", "kind": "event", "since": "v12.0.0"},
    "edgesUpdatable": {"replacement": "edgesReconnectable", "kind": "prop", "since": "v12.0.0"},
    "edge.updatable": {"replacement": "edge.reconnectable", "kind": "edge-field", "since": "v12.0.0"},

    # coordinate conversion
    "project": {
        "replacement": "screenToFlowPosition",
        "kind": "instance-method",
        "since": "v12.0.0",
        "note": "instance.project() is removed. Use useReactFlow().screenToFlowPosition({x, y}).",
    },

    # store internals
    "nodeInternals": {
        "replacement": "nodeLookup",
        "kind": "store-field",
        "since": "v12.0.0",
        "note": "Internal store rename.",
    },

    # hooks
    "useHandleConnections": {
        "replacement": "useNodeConnections",
        "kind": "hook",
        "deprecated": True,
        "note": "Pass {id, handleType, handleId} to filter — id auto-fills inside custom node.",
    },

    # CSS classes
    "react-flow__handle-connecting": {
        "replacement": "connectingto / connectingfrom",
        "kind": "css-class",
        "since": "v12.0.0",
        "note": "Now two separate classes depending on direction.",
    },
    "react-flow__handle-valid": {
        "replacement": "valid",
        "kind": "css-class",
        "since": "v12.0.0",
    },
}

# global behavior changes that aren't a single symbol rename
BEHAVIOR_CHANGES = [
    {
        "topic": "React version",
        "change": "React 18+ required (uses concurrent features internally).",
    },
    {
        "topic": "Immutability",
        "change": "Mutating nodes/edges in place no longer works — always spread into new objects.",
    },
    {
        "topic": "Default export",
        "change": "<ReactFlow> default export removed — use named import `import { ReactFlow } from '@xyflow/react'`.",
    },
    {
        "topic": "TypeScript",
        "change": "Multi-shape nodes recommended as discriminated unions (`type AppNode = NumberNode | TextNode`) over generic params.",
    },
    {
        "topic": "Unlocked features (post-rewrite)",
        "change": "SSR/SSG with hydration, colorMode dark mode, computing-flows (updateNodeData/useNodesData/useNodeConnections), useNodesInitialized.",
    },
]


def lookup(symbol: str) -> dict | None:
    """Case-insensitive lookup of v11 → v12 migration."""
    if symbol in SYMBOL_MIGRATION:
        return {"symbol": symbol, **SYMBOL_MIGRATION[symbol]}
    if symbol in PACKAGE_MIGRATION:
        return {"symbol": symbol, **PACKAGE_MIGRATION[symbol]}
    lower = symbol.lower()
    for key, entry in SYMBOL_MIGRATION.items():
        if key.lower() == lower:
            return {"symbol": key, **entry}
    for key, entry in PACKAGE_MIGRATION.items():
        if key.lower() == lower:
            return {"symbol": key, **entry}
    return None
