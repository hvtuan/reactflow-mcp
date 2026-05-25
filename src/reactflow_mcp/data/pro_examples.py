"""React Flow Pro examples catalog (paid).

Source: https://reactflow.dev/pro/examples + https://pro-examples.reactflow.dev (snapshot 2026-05-25).

Pro examples are gated behind a subscription. Listing them helps the LLM
suggest "this exists as a Pro example" rather than fabricating one.
"""

from __future__ import annotations

PRO_EXAMPLES: list[dict] = [
    # Layout
    {"name": "Auto Layout", "category": "layout", "frameworks": ["react", "svelte"],
     "summary": "Automatic layouting after adding new nodes; variants for dagre, elkjs, d3-force."},
    {"name": "Dynamic Layouting", "category": "layout", "frameworks": ["react"],
     "summary": "Vertical tree flow with auto-arranged placeholder nodes; dagre variant available."},
    {"name": "Expand and Collapse", "category": "layout", "frameworks": ["react", "svelte"],
     "summary": "Hierarchical flow with collapsible subtrees; d3 variant available."},
    {"name": "Force Layout", "category": "layout", "frameworks": ["react", "svelte"],
     "summary": "d3-force-based positioning that prevents node overlap."},
    {"name": "libavoid Edge Routing", "category": "layout", "frameworks": ["react"],
     "summary": "Orthogonal edge routing via libavoid for clean schematic-style diagrams."},

    # Interaction
    {"name": "Helper Lines", "category": "interaction", "frameworks": ["react"],
     "summary": "Alignment guides that snap nodes when sides align (Figma-style)."},
    {"name": "Collaborative", "category": "interaction", "frameworks": ["react"],
     "summary": "Real-time multi-user editing with Yjs cursors + shared state."},
    {"name": "Copy and Paste", "category": "interaction", "frameworks": ["react", "svelte"],
     "summary": "Duplicate selected nodes/edges."},
    {"name": "Undo and Redo", "category": "interaction", "frameworks": ["react", "svelte"],
     "summary": "Undo/redo for add, delete, connect, position operations."},
    {"name": "Node Position Animation", "category": "interaction", "frameworks": ["react", "svelte"],
     "summary": "Animated transitions between node positions."},

    # Edges
    {"name": "Editable Edge", "category": "edges", "frameworks": ["react"],
     "summary": "Custom edge with draggable bezier/linear control points."},

    # Nodes
    {"name": "Shapes", "category": "nodes", "frameworks": ["react", "svelte"],
     "summary": "SVG flowchart shapes — diamond, circle, cylinder, etc."},
    {"name": "Resize and Rotate", "category": "nodes", "frameworks": ["react"],
     "summary": "Custom resizable + rotatable node. DEPRECATED — superseded by NodeResizer OSS component."},

    # Grouping
    {"name": "Parent/Child Relation", "category": "grouping", "frameworks": ["react", "svelte"],
     "summary": "Drag-into-container grouping with detach toolbar."},
    {"name": "Dynamic Grouping", "category": "grouping", "frameworks": ["react"],
     "summary": "Group nodes by dragging them into a shared container."},
    {"name": "Selection Grouping", "category": "grouping", "frameworks": ["react", "svelte"],
     "summary": "Group via selection box with ungroup toolbar."},

    # Whiteboard / drawing
    {"name": "Freehand Draw", "category": "whiteboard", "frameworks": ["react", "svelte"],
     "summary": "Drawing-mode tool that emits selectable, resizable freehand-shape nodes."},

    # Misc
    {"name": "Server-Side Image Creation", "category": "misc", "frameworks": ["react", "svelte"],
     "summary": "Backend flow-to-PNG/SVG generation."},
    {"name": "Remove Attribution", "category": "misc", "frameworks": ["react", "svelte"],
     "summary": "Recipe for hiding the corner attribution badge (technically just `proOptions.hideAttribution: true`)."},
    {"name": "Workflow Editor", "category": "template", "frameworks": ["react"],
     "summary": "Next.js workflow-editor starter template (delivered as private repo)."},
    {"name": "AI Workflow Editor", "category": "template", "frameworks": ["react"],
     "summary": "Next.js + Vercel AI SDK + Zustand + shadcn template for AI image-generation workflows."},
]

PRICING_TIERS = [
    {
        "name": "Starter",
        "seats": 1,
        "includes": [
            "Pro Examples + Pro Templates access",
            "Prioritized GitHub issues",
            "Funds OSS maintenance",
        ],
        "price_note": "Exact price rendered client-side on reactflow.dev/pro/pricing — not extractable via scraping (snapshot 2026-05-25).",
    },
    {
        "name": "Professional",
        "seats": 5,
        "includes": [
            "Everything in Starter",
            "Up to 1 hr/month email support",
            "1:1 intro call with a React Flow creator",
        ],
        "price_note": "See pricing page.",
    },
    {
        "name": "Enterprise",
        "seats": 10,
        "includes": [
            "Everything in Professional",
            "Perpetual access to ALL future Pro content",
            "Voice/video support 1 hr/month",
            "Custom procurement / payment terms",
        ],
        "price_note": "Custom quote — reactflow.dev/pro/quote-request.",
    },
]

LICENSE_NOTES = {
    "core": "Core React Flow (`@xyflow/react`), Svelte Flow (`@xyflow/svelte`), and `@xyflow/system` are MIT — permanently free.",
    "ui_kit": "React Flow UI shadcn registry at reactflow.dev/ui is also MIT — install via `npx shadcn@latest add https://ui.reactflow.dev/<component>`. NOT Pro-gated.",
    "perpetual": "Cancel a Starter/Professional sub → keep what you already downloaded forever, lose access to new content. Enterprise tier grants perpetual access to future content too.",
    "redistribution": "Cannot republish Pro examples/templates as a standalone library or competing product.",
    "seats": "Subscription sold in seat bundles (1/5/10). Per-seat vs per-project granularity not explicitly stated; seat-bundle model implies per-developer-within-one-org.",
    "attribution": "`proOptions.hideAttribution: true` is technically usable by anyone — official guidance treats it as a moral/funding ask, not a license obligation. Personal projects: free to remove. Commercial: please subscribe or sponsor.",
}
