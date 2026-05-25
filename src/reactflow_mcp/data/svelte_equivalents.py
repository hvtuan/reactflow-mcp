"""React Flow → Svelte Flow symbol equivalents.

Most symbols are identically named — only the package import path differs
(`@xyflow/react` → `@xyflow/svelte`). A handful have different names or
non-trivial API differences worth flagging. Plus a porting-notes section
that captures cross-cutting architecture differences (state model,
component flavor, Svelte 5 requirement).

Source: https://svelteflow.dev/api-reference + /learn (snapshot 2026-05-25).
"""

from __future__ import annotations

# Symbols with different names in Svelte Flow.
RENAMED: dict[str, dict] = {
    "ReactFlow": {
        "svelte": "SvelteFlow",
        "kind": "component",
        "note": "Root component renamed. Same prop surface but state is `bind:nodes bind:edges` instead of controlled `nodes={…}` + `onNodesChange={…}`.",
    },
    "ReactFlowProvider": {
        "svelte": "SvelteFlowProvider",
        "kind": "component",
        "note": "Same role — required when hooks are used outside <SvelteFlow> or for multiple flows on a page.",
    },
    "useReactFlow": {
        "svelte": "useSvelteFlow",
        "kind": "hook",
        "note": "Returns an imperative instance with the same set of methods (setNodes, addNodes, fitView, screenToFlowPosition, etc.). In Svelte it's a function call, not a React hook subject to rules-of-hooks.",
    },
    "EdgeLabelRenderer": {
        "svelte": "EdgeLabel",
        "kind": "component",
        "note": "Different name. Same purpose: HTML overlay portal above SVG for interactive edge labels.",
    },
}

# Symbols that exist in Svelte Flow with the exact same name.
# (Just the import path changes: `@xyflow/react` → `@xyflow/svelte`.)
IDENTICAL = {
    # components
    "Background", "BaseEdge", "Controls", "ControlButton",
    "Handle", "Panel", "MiniMap",
    "NodeToolbar", "NodeResizer", "NodeResizeControl",
    "EdgeToolbar", "ViewportPortal",
    # hooks
    "useConnection", "useEdges", "useNodes", "useStore",
    "useNodeConnections", "useNodesData", "useNodesInitialized",
    "useOnSelectionChange", "useUpdateNodeInternals", "useInternalNode",
    "useViewport",
    # utils
    "addEdge", "applyNodeChanges", "applyEdgeChanges", "reconnectEdge",
    "getConnectedEdges", "getIncomers", "getOutgoers",
    "getBezierPath", "getSmoothStepPath", "getStraightPath", "getSimpleBezierPath",
    "getNodesBounds", "getViewportForBounds",
    "isNode", "isEdge",
    # types
    "Node", "Edge", "Connection", "Viewport",
    "NodeChange", "EdgeChange", "FitViewOptions",
    # enums
    "Position", "ConnectionMode", "ConnectionLineType",
    "MarkerType", "BackgroundVariant", "PanelPosition",
    "PanOnScrollMode", "SelectionMode", "ColorMode",
}

# Svelte-only symbols (no direct React Flow equivalent).
SVELTE_ONLY: dict[str, dict] = {
    "EdgeReconnectAnchor": {
        "kind": "component",
        "note": "Svelte Flow's reconnection anchor primitive. React Flow handles reconnection via the `onReconnect*` callbacks + the global `edgesReconnectable` prop instead.",
    },
}

PORTING_NOTES = {
    "state_model": "React Flow → useState + applyNodeChanges/applyEdgeChanges + onConnect. Svelte Flow → `let nodes = $state.raw([…])` (raw, NOT deep) + `bind:nodes bind:edges` on `<SvelteFlow>`. Svelte writes back directly through the binding; you do NOT call applyNodeChanges yourself.",
    "custom_components": "React: function components returning JSX. Svelte: `.svelte` SFCs. Both receive a `data` prop; for state mutation Svelte uses `useSvelteFlow().updateNodeData(id, patch)` exactly like React.",
    "imports": "Replace `from \"@xyflow/react\"` with `from \"@xyflow/svelte\"`. Replace CSS import `@xyflow/react/dist/style.css` with `@xyflow/svelte/dist/style.css`.",
    "svelte_version": "Svelte Flow requires **Svelte 5** (^5.25.0). Svelte 4 users are stuck on older Svelte Flow versions — no v1 backport.",
    "hooks_return_shape": "Svelte hooks return Svelte stores / reactive values rather than React snapshot values. Read them with `$store` syntax inside `.svelte` files.",
    "pro_examples_subset": "Pro example coverage is SMALLER for Svelte Flow. Missing: Collaborative, Helper Lines, Editable Edge, Dynamic Grouping, Dynamic Layouting, libavoid Edge Routing, Workflow Editor templates. (As of 2026-05-25.)",
    "release_train": "Both packages release together via Changesets. As of 2026-05-25: @xyflow/react@12.10.2 ⇄ @xyflow/svelte@1.5.2 ⇄ @xyflow/system@0.0.76.",
}


def lookup(symbol: str) -> dict:
    """Resolve a React Flow symbol to its Svelte Flow equivalent.

    Returns a dict:
        {
          "react_symbol": str,
          "found": bool,
          "svelte_symbol": str?,
          "status": "renamed" | "identical" | "svelte_only" | "unknown",
          "kind": str?,
          "note": str?,
          "react_import": str?,        # @xyflow/react
          "svelte_import": str?,       # @xyflow/svelte
          "suggestions": [str]?        # if unknown
        }
    """
    # exact-name match in RENAMED
    if symbol in RENAMED:
        entry = RENAMED[symbol]
        return {
            "react_symbol": symbol,
            "svelte_symbol": entry["svelte"],
            "found": True,
            "status": "renamed",
            "kind": entry.get("kind"),
            "note": entry.get("note"),
            "react_import": "@xyflow/react",
            "svelte_import": "@xyflow/svelte",
        }

    # identical names
    if symbol in IDENTICAL:
        return {
            "react_symbol": symbol,
            "svelte_symbol": symbol,
            "found": True,
            "status": "identical",
            "note": "Same name — just change the import path.",
            "react_import": "@xyflow/react",
            "svelte_import": "@xyflow/svelte",
        }

    # case-insensitive retry
    lower = symbol.lower()
    for key, entry in RENAMED.items():
        if key.lower() == lower:
            return {
                "react_symbol": key,
                "svelte_symbol": entry["svelte"],
                "found": True,
                "status": "renamed",
                "kind": entry.get("kind"),
                "note": entry.get("note"),
                "react_import": "@xyflow/react",
                "svelte_import": "@xyflow/svelte",
            }
    for name in IDENTICAL:
        if name.lower() == lower:
            return {
                "react_symbol": name,
                "svelte_symbol": name,
                "found": True,
                "status": "identical",
                "note": "Same name — just change the import path.",
                "react_import": "@xyflow/react",
                "svelte_import": "@xyflow/svelte",
            }

    # is it a Svelte-only symbol that the user typed?
    if symbol in SVELTE_ONLY:
        entry = SVELTE_ONLY[symbol]
        return {
            "react_symbol": None,
            "svelte_symbol": symbol,
            "found": True,
            "status": "svelte_only",
            "kind": entry.get("kind"),
            "note": entry.get("note"),
            "svelte_import": "@xyflow/svelte",
        }

    # not found — suggest near matches
    pool = list(RENAMED.keys()) + list(IDENTICAL) + list(SVELTE_ONLY.keys())
    suggestions = sorted(
        (n for n in pool if lower in n.lower() or n.lower() in lower),
        key=lambda n: (abs(len(n) - len(symbol)), n.lower()),
    )[:8]
    return {
        "react_symbol": symbol,
        "svelte_symbol": None,
        "found": False,
        "status": "unknown",
        "suggestions": suggestions,
    }
