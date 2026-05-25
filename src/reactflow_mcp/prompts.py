"""MCP prompts — templated workflows MCP clients can surface to users.

Prompts are pre-filled task instructions that LLMs can request from the server
(e.g., via Claude Code's `/<prompt-name>` slash menu). Each prompt below
orchestrates the reactflow-mcp tools toward a high-value workflow.
"""

from __future__ import annotations


def review_flow_spec(flow_json: str) -> str:
    """Structured code-review walkthrough for a React Flow JSON spec.

    Args:
        flow_json: JSON string of `{nodes, edges}` (same shape as
            `useReactFlow().toObject()`).
    """
    return f"""\
Review the following React Flow v12 flow spec and produce a structured report.

```json
{flow_json}
```

Run these steps **in order**, using the reactflow-mcp tools:

1. Call `reactflow_validate_flow` with the JSON above to surface hard errors,
   warnings, cycles, and topology stats.

2. For every error code returned, look up the v12 fix:
   - `E_NODE_V11_FIELD` / `E_EDGE_V11_FIELD` → call `reactflow_lookup_v11_v12`
     with the offending field name to get the correct v12 replacement.
   - `E_PARENT_ORDER` → cite the v12 rule (parent must come before child).
   - `E_EDGE_*_MISSING` → list which referenced node ids don't exist.

3. For every warning, decide if it's a real issue:
   - `W_V12_WIDTH_HEIGHT` — recommend `initialWidth/initialHeight` if content-driven.
   - `W_EDGE_DUP_PARALLEL` — recommend `multi-edge` pattern or dedupe.
   - `W_CYCLE` — note which downstream tools (auto-layout, dataflow) break.

4. Summarize in this format:

   ## Verdict
   - **Status:** OK / NEEDS FIXES / BROKEN
   - **Critical fixes** (numbered): ...
   - **Recommended improvements**: ...
   - **Architectural notes** (e.g., suggest auto-layout recipe if many nodes without positions): ...
"""


def migrate_v11_to_v12(code_snippet: str) -> str:
    """Walk an LLM through migrating a v11 React Flow code snippet to v12.

    Args:
        code_snippet: A snippet of React Flow v11 TSX/TS code.
    """
    # Use plain string + .replace to avoid f-string brace escaping hell
    # (the procedure body contains literal JS/TS braces).
    body = """\
Migrate this React Flow v11 snippet to @xyflow/react v12.

```tsx
__SNIPPET__
```

Procedure:

1. **Imports.** Replace `from 'reactflow'` with named imports from `@xyflow/react`.
   Default export is gone — convert any `import ReactFlow from 'reactflow'` to
   `import { ReactFlow } from '@xyflow/react'`. Update CSS import to
   `@xyflow/react/dist/style.css`.

2. **For every identifier in the snippet,** call `reactflow_lookup_v11_v12` with
   that symbol name. If it returns `found: true`, apply the rename.
   Common ones to scan for: `parentNode`, `xPos`, `yPos`, `onEdgeUpdate`,
   `edgesUpdatable`, `project`, `nodeInternals`, `useHandleConnections`,
   `node.width`, `node.height`.

3. **Immutability check.** v12 requires fresh objects — search for in-place
   mutations like `node.position.x = …` or `nodes[i].data.x = …` and rewrite
   with spread (`{...node, position: {...node.position, x} }`).

4. **Custom-node props.** Look for `function MyNode({ xPos, yPos, ... })` and
   rename to `positionAbsoluteX` / `positionAbsoluteY`.

5. **Width/height semantics.** If the code reads `node.width` / `node.height`
   expecting measured values, change to `node.measured?.width` / `.measured?.height`.

6. After migration, validate the rewritten code mentally against
   `reactflow_search_docs(query='v11 → v12 migration')` for any patterns you
   might have missed.

Output: the migrated snippet + a bullet list of every change you made + a note
about any v12 features the user can now adopt (SSR, colorMode dark mode,
computing-flows hooks).
"""
    return body.replace("__SNIPPET__", code_snippet)


def clone_pro_feature(feature: str) -> str:
    """Walk an LLM through cloning a React Flow Pro example using the OSS recipes.

    Args:
        feature: Name of the Pro example (e.g., "Auto Layout", "Undo/Redo",
            "Helper Lines", "Collaborative", "Editable Edge").
    """
    return f"""\
The user wants to add **{feature}** to their React Flow app, equivalent to the
paid React Flow Pro example of the same name. Implement it using ONLY free
OSS code. Don't recommend buying Pro — this MCP server exists precisely to
replace Pro.

Procedure:

1. Call `reactflow_list_recipes` to see if there's a ready recipe whose
   `clones_pro` field matches "{feature}". If yes, call `reactflow_get_recipe`
   with the slug and deliver the full code + gotchas to the user.

2. If no direct recipe exists, decompose the feature:
   - Call `reactflow_list_pro_examples` with the relevant category to confirm
     what's in scope (and what the Pro Example actually delivers).
   - Call `reactflow_search_docs` with key terms to find related concepts.
   - Use `reactflow_get_api` to look up the specific hooks/components you need.
   - Compose them into a recipe-style solution.

3. After writing code, run `reactflow_validate_flow` on any sample flow JSON
   you produce to catch v12-correctness issues.

4. Cite the recipe slug (or your composed approach) at the end so the user can
   come back later.
"""


def pick_layout_algorithm(node_count: int, edge_density: str, shape: str) -> str:
    """Recommend dagre / elkjs / d3-force / none based on graph characteristics.

    Args:
        node_count: Approximate number of nodes (e.g., 5, 50, 500).
        edge_density: "sparse" | "dense" — sparse ≈ tree-like; dense ≈ graph-like.
        shape: "hierarchical" (clear parent → child) | "organic" (no clear hierarchy) |
            "directed-acyclic" | "cyclic".
    """
    return f"""\
The user has ~{node_count} nodes, **{edge_density}** edges, and a **{shape}**
topology. Pick the right auto-layout algorithm and deliver a working recipe.

Decision rules:
- {shape} = 'hierarchical' or 'directed-acyclic' → `auto_layout_dagre`
  (top-down or left-right, fast, deterministic).
- {shape} = 'directed-acyclic' AND {node_count} > 200 → `auto_layout_elkjs`
  (layered, async, handles bigger graphs cleanly).
- {shape} = 'organic' / 'cyclic' AND {edge_density} = 'dense' → `force_layout`
  (d3-force physics, prevents overlap, looks natural).
- {shape} = 'hierarchical' AND user needs port-aware routing → `auto_layout_elkjs`
  with `elk.algorithm=layered` + port constraints.
- {edge_density} = 'dense' AND user wants orthogonal lines → recommend the
  `libavoid` route (recipe coming) or pair force layout with smoothstep edges.

Procedure:
1. State your pick + why (1 sentence).
2. Call `reactflow_get_recipe(name='<chosen_slug>')` and deliver the code.
3. Mention the key gotcha for that recipe (use `useNodesInitialized`, read
   `measured.width/height`, etc.).
4. Suggest pairing with the `node_position_animation` recipe so the re-layout
   animates smoothly instead of snapping.
"""
