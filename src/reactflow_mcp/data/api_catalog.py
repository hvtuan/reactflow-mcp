"""Structured catalog of React Flow (`@xyflow/react` v12) public API symbols.

Each entry shape:
    {
      "kind": "component" | "hook" | "util" | "type" | "enum" | "prop",
      "category": str,
      "summary": str,
      "signature": str,             # TS-flavored signature
      "params": list[dict] | None,  # for hooks/utils
      "props": list[dict] | None,   # for components
      "notes": str | None,
      "since": str | None,          # e.g. "v12.0.0"
      "pro": bool,
      "deprecated": bool,
      "replacement": str | None,
    }

Only the most frequently looked-up symbols are listed; the deep-dive markdown
resource carries the rest.
"""

from __future__ import annotations

API_CATALOG: dict[str, dict] = {
    # ───────────────────────── core component ─────────────────────────
    "ReactFlow": {
        "kind": "component",
        "category": "core",
        "summary": "Root canvas component. Wrap with <ReactFlowProvider> when using hooks outside its subtree.",
        "signature": "<ReactFlow nodes edges onNodesChange onEdgesChange onConnect …>",
        "props": [
            {"name": "nodes", "type": "Node[]", "purpose": "controlled nodes"},
            {"name": "edges", "type": "Edge[]", "purpose": "controlled edges"},
            {"name": "defaultNodes", "type": "Node[]", "purpose": "uncontrolled initial nodes"},
            {"name": "defaultEdges", "type": "Edge[]", "purpose": "uncontrolled initial edges"},
            {"name": "nodeTypes", "type": "NodeTypes", "purpose": "{ typeName: Component } — declare OUTSIDE component or memoize"},
            {"name": "edgeTypes", "type": "EdgeTypes", "purpose": "{ typeName: Component } — same memo rule"},
            {"name": "defaultEdgeOptions", "type": "DefaultEdgeOptions", "purpose": "defaults applied to new edges"},
            {"name": "fitView", "type": "boolean", "purpose": "auto-fit viewport on mount"},
            {"name": "fitViewOptions", "type": "FitViewOptions", "purpose": "padding/duration/ease/nodes"},
            {"name": "minZoom", "type": "number", "purpose": "lower zoom bound"},
            {"name": "maxZoom", "type": "number", "purpose": "upper zoom bound"},
            {"name": "snapToGrid", "type": "boolean", "purpose": "snap nodes to grid"},
            {"name": "snapGrid", "type": "[number, number]", "purpose": "grid spacing"},
            {"name": "translateExtent", "type": "CoordinateExtent", "purpose": "pan bounds"},
            {"name": "nodeExtent", "type": "CoordinateExtent", "purpose": "node placement bounds"},
            {"name": "onlyRenderVisibleElements", "type": "boolean", "purpose": "cull off-screen elements for perf"},
            {"name": "panOnDrag", "type": "boolean | number[]", "purpose": "drag-to-pan; array limits mouse buttons"},
            {"name": "panOnScroll", "type": "boolean", "purpose": "scroll-wheel pan"},
            {"name": "panOnScrollMode", "type": "PanOnScrollMode", "purpose": "Free | Horizontal | Vertical"},
            {"name": "zoomOnScroll", "type": "boolean", "purpose": "scroll-wheel zoom"},
            {"name": "zoomOnPinch", "type": "boolean", "purpose": "pinch zoom"},
            {"name": "zoomOnDoubleClick", "type": "boolean", "purpose": "double-click zoom"},
            {"name": "selectionOnDrag", "type": "boolean", "purpose": "box-select without modifier"},
            {"name": "selectionMode", "type": "SelectionMode", "purpose": "Full | Partial"},
            {"name": "connectionMode", "type": "ConnectionMode", "purpose": "Strict (source→target only) | Loose"},
            {"name": "connectionLineType", "type": "ConnectionLineType", "purpose": "Bezier | Straight | Step | SmoothStep | SimpleBezier"},
            {"name": "connectionLineComponent", "type": "ConnectionLineComponent", "purpose": "custom in-progress connection visual"},
            {"name": "connectionRadius", "type": "number", "purpose": "handle snap radius"},
            {"name": "isValidConnection", "type": "(c: Connection) => boolean", "purpose": "global connection validator"},
            {"name": "edgesReconnectable", "type": "boolean", "purpose": "allow edge endpoint reconnection"},
            {"name": "nodeDragThreshold", "type": "number", "purpose": "pixels before drag starts"},
            {"name": "deleteKeyCode", "type": "KeyCode | null", "purpose": "delete shortcut (default Backspace)"},
            {"name": "selectionKeyCode", "type": "KeyCode | null", "purpose": "box-select modifier"},
            {"name": "multiSelectionKeyCode", "type": "KeyCode | null", "purpose": "multi-select modifier"},
            {"name": "colorMode", "type": "'light' | 'dark' | 'system'", "purpose": "theme toggle"},
            {"name": "ariaLabelConfig", "type": "Partial<AriaLabelConfig>", "purpose": "a11y label overrides"},
            {"name": "proOptions", "type": "{ hideAttribution?: boolean; account?: string }", "purpose": "hide attribution badge (moral ask)"},
            {"name": "onInit", "type": "(instance) => void", "purpose": "lifecycle: instance ready"},
            {"name": "onBeforeDelete", "type": "({ nodes, edges }) => boolean | Promise<boolean>", "purpose": "abort delete by returning false"},
        ],
        "since": "v12.0.0",
    },

    # ───────────────────────── built-in components ─────────────────────────
    "Background": {
        "kind": "component", "category": "built-in",
        "summary": "Canvas background pattern.",
        "signature": "<Background variant='dots'|'lines'|'cross' gap size color … />",
        "props": [
            {"name": "variant", "type": "BackgroundVariant", "purpose": "Dots | Lines | Cross"},
            {"name": "gap", "type": "number | [n, n]", "purpose": "spacing"},
            {"name": "size", "type": "number"},
            {"name": "color", "type": "string"},
            {"name": "lineWidth", "type": "number"},
        ],
    },
    "Controls": {
        "kind": "component", "category": "built-in",
        "summary": "Zoom/fit/lock button cluster.",
        "signature": "<Controls showZoom showFitView showInteractive position … />",
        "props": [
            {"name": "showZoom", "type": "boolean"},
            {"name": "showFitView", "type": "boolean"},
            {"name": "showInteractive", "type": "boolean"},
            {"name": "position", "type": "PanelPosition"},
            {"name": "orientation", "type": "'horizontal' | 'vertical'"},
        ],
        "notes": "Compose custom buttons via <ControlButton> as children.",
    },
    "ControlButton": {
        "kind": "component", "category": "built-in",
        "summary": "Custom button inside <Controls>.",
        "signature": "<ControlButton onClick={…}>icon</ControlButton>",
    },
    "MiniMap": {
        "kind": "component", "category": "built-in",
        "summary": "Bird's-eye nav overlay.",
        "signature": "<MiniMap pannable zoomable nodeColor maskColor … />",
        "props": [
            {"name": "pannable", "type": "boolean"},
            {"name": "zoomable", "type": "boolean"},
            {"name": "nodeColor", "type": "string | (node) => string"},
            {"name": "nodeStrokeColor", "type": "string | (node) => string"},
            {"name": "nodeClassName", "type": "string | (node) => string"},
            {"name": "maskColor", "type": "string"},
            {"name": "onClick", "type": "(event, position) => void"},
            {"name": "onNodeClick", "type": "(event, node) => void"},
        ],
    },
    "Panel": {
        "kind": "component", "category": "built-in",
        "summary": "Viewport-fixed floating <div> (toolbars, titles).",
        "signature": "<Panel position='top-left'|…>children</Panel>",
        "props": [
            {"name": "position", "type": "PanelPosition", "purpose": "top-left | top-center | top-right | center-left | center-right | bottom-left | bottom-center | bottom-right"},
        ],
    },
    "Handle": {
        "kind": "component", "category": "built-in",
        "summary": "Connection port on a node. Multiple handles need unique id.",
        "signature": "<Handle type='source'|'target' position={Position.Top|…} id? isConnectable? isValidConnection? />",
        "props": [
            {"name": "type", "type": "'source' | 'target'"},
            {"name": "position", "type": "Position", "purpose": "Top | Right | Bottom | Left"},
            {"name": "id", "type": "string"},
            {"name": "isConnectable", "type": "boolean"},
            {"name": "isConnectableStart", "type": "boolean"},
            {"name": "isConnectableEnd", "type": "boolean"},
            {"name": "isValidConnection", "type": "(c) => boolean"},
            {"name": "onConnect", "type": "(c: Connection) => void"},
        ],
        "notes": "Hide via visibility:hidden, NEVER display:none (breaks dim math). CSS classes during drag: connecting, connectingto, connectingfrom, valid.",
    },
    "NodeToolbar": {
        "kind": "component", "category": "built-in",
        "summary": "Toolbar attached to selected node(s).",
        "signature": "<NodeToolbar nodeId? isVisible? position align offset>…</NodeToolbar>",
        "props": [
            {"name": "nodeId", "type": "string | string[]"},
            {"name": "isVisible", "type": "boolean"},
            {"name": "position", "type": "Position"},
            {"name": "align", "type": "'start' | 'center' | 'end'"},
            {"name": "offset", "type": "number (px)"},
        ],
        "notes": "Shows only when node selected unless isVisible overrides.",
    },
    "NodeResizer": {
        "kind": "component", "category": "built-in",
        "summary": "Resize handles around a node.",
        "signature": "<NodeResizer color keepAspectRatio min/max{Width,Height} onResize… />",
        "props": [
            {"name": "color", "type": "string"},
            {"name": "isVisible", "type": "boolean"},
            {"name": "keepAspectRatio", "type": "boolean"},
            {"name": "autoScale", "type": "boolean"},
            {"name": "minWidth", "type": "number"},
            {"name": "minHeight", "type": "number"},
            {"name": "maxWidth", "type": "number"},
            {"name": "maxHeight", "type": "number"},
            {"name": "onResize", "type": "(event, params) => void"},
            {"name": "shouldResize", "type": "(event, params) => boolean"},
        ],
    },
    "NodeResizeControl": {
        "kind": "component", "category": "built-in",
        "summary": "Lower-level single-handle resizer for fully custom resize UI.",
        "signature": "<NodeResizeControl position variant resizeDirection>icon</NodeResizeControl>",
    },
    "EdgeText": {
        "kind": "component", "category": "built-in",
        "summary": "SVG label primitive used inside SVG edges.",
        "signature": "<EdgeText x y label labelStyle labelShowBg labelBg* … />",
    },
    "BaseEdge": {
        "kind": "component", "category": "built-in",
        "summary": "SVG <path> wrapper — use to make custom edge selectable + interactive.",
        "signature": "<BaseEdge path={d} markerEnd interactionWidth labelX labelY label />",
        "notes": "Raw <path> is NOT interactive — always wrap with <BaseEdge> in custom edges.",
    },
    "EdgeLabelRenderer": {
        "kind": "component", "category": "built-in",
        "summary": "HTML portal above SVG — required for interactive (clickable) edge labels.",
        "signature": "<EdgeLabelRenderer>…</EdgeLabelRenderer>",
        "notes": "Position labels with translate(-50%,-50%) translate(${labelX}px,${labelY}px). Add pointer-events:all + 'nodrag nopan' classes for clicks.",
    },
    "EdgeToolbar": {
        "kind": "component", "category": "built-in",
        "summary": "Non-scaling toolbar attached to an edge.",
        "signature": "<EdgeToolbar edgeId x y isVisible alignX alignY />",
    },
    "ViewportPortal": {
        "kind": "component", "category": "built-in",
        "summary": "Render HTML children inside the transformed viewport coord space (pans/zooms with flow).",
        "signature": "<ViewportPortal>children</ViewportPortal>",
    },
    "ReactFlowProvider": {
        "kind": "component", "category": "core",
        "summary": "Context wrapper. Required when hooks used outside <ReactFlow>, when multiple flows on a page, or for SSR.",
        "signature": "<ReactFlowProvider initialNodes? initialEdges? initialWidth? initialHeight? fitView?>…</ReactFlowProvider>",
    },

    # ───────────────────────── hooks ─────────────────────────
    "useReactFlow": {
        "kind": "hook", "category": "instance",
        "summary": "Returns the imperative ReactFlowInstance.",
        "signature": "useReactFlow<NodeType, EdgeType>(): ReactFlowInstance",
        "notes": "Instance methods: getNodes/setNodes/addNodes/getNode/updateNode/updateNodeData, getEdges/setEdges/addEdges/getEdge/updateEdge/updateEdgeData, getZoom/zoomIn/zoomOut/zoomTo/setViewport/setCenter/fitView/fitBounds, screenToFlowPosition/flowToScreenPosition, getIntersectingNodes/isNodeIntersecting, getNodeConnections/getHandleConnections, deleteElements, toObject.",
    },
    "useNodes": {"kind": "hook", "category": "reactive", "summary": "Reactive nodes[]. Re-renders on any change — prefer useStore selector for perf paths.", "signature": "useNodes(): Node[]"},
    "useEdges": {"kind": "hook", "category": "reactive", "summary": "Reactive edges[].", "signature": "useEdges(): Edge[]"},
    "useNodesState": {
        "kind": "hook", "category": "state",
        "summary": "Prototyping shortcut — bundles state + change handler.",
        "signature": "useNodesState(initial): [nodes, setNodes, onNodesChange]",
        "notes": "For prod, lift into a dedicated store (Zustand).",
    },
    "useEdgesState": {
        "kind": "hook", "category": "state",
        "summary": "Prototyping shortcut for edges.",
        "signature": "useEdgesState(initial): [edges, setEdges, onEdgesChange]",
    },
    "useStore": {
        "kind": "hook", "category": "low-level",
        "summary": "Zustand-style narrow store subscription.",
        "signature": "useStore<T>(selector: (s) => T, equalityFn?): T",
    },
    "useStoreApi": {
        "kind": "hook", "category": "low-level",
        "summary": "Imperative store access — no re-render.",
        "signature": "useStoreApi(): { getState, setState, subscribe }",
    },
    "useViewport": {"kind": "hook", "category": "reactive", "summary": "Reactive viewport.", "signature": "useViewport(): { x: number; y: number; zoom: number }"},
    "useKeyPress": {
        "kind": "hook", "category": "input",
        "summary": "Reactive boolean for keyboard shortcuts. Works outside RF context.",
        "signature": "useKeyPress(keyCode: string | string[], options?: { target?; actInsideInputWithModifier?; preventDefault? }): boolean",
    },
    "useUpdateNodeInternals": {
        "kind": "hook", "category": "imperative",
        "summary": "Call after dynamically adding/removing handles or changing handle position so RF re-measures.",
        "signature": "useUpdateNodeInternals(): (id: string | string[]) => void",
    },
    "useOnSelectionChange": {
        "kind": "hook", "category": "events",
        "summary": "Subscribe to selection changes without prop wiring.",
        "signature": "useOnSelectionChange({ onChange }): void",
        "notes": "onChange MUST be useCallback-memoized or the hook silently breaks.",
    },
    "useOnViewportChange": {
        "kind": "hook", "category": "events",
        "summary": "Phased viewport callbacks.",
        "signature": "useOnViewportChange({ onStart?, onChange?, onEnd? }): void",
        "notes": "All callbacks MUST be useCallback-memoized.",
    },
    "useNodeId": {"kind": "hook", "category": "context", "summary": "Get current node id inside a custom node component.", "signature": "useNodeId(): string | null"},
    "useNodesData": {
        "kind": "hook", "category": "reactive",
        "summary": "Subscribe to only the data slice of one or many nodes — narrower than useNodes.",
        "signature": "useNodesData<T>(id | id[]): T | T[]",
    },
    "useConnection": {
        "kind": "hook", "category": "reactive",
        "summary": "Active in-progress connection state, null when idle. Use for handle styling during drag.",
        "signature": "useConnection<T>(selector?): ConnectionState | null",
    },
    "useNodeConnections": {
        "kind": "hook", "category": "reactive",
        "summary": "Reactive list of connections on a node/handle. `id` auto-fills inside custom node.",
        "signature": "useNodeConnections({ id?, handleType?, handleId?, onConnect?, onDisconnect? }): NodeConnection[]",
    },
    "useHandleConnections": {
        "kind": "hook", "category": "reactive",
        "summary": "DEPRECATED — use useNodeConnections.",
        "signature": "useHandleConnections({ type, id?, nodeId?, … })",
        "deprecated": True, "replacement": "useNodeConnections",
    },
    "useInternalNode": {
        "kind": "hook", "category": "reactive",
        "summary": "Internal node with absolute position + measured dimensions. Re-renders on any node change.",
        "signature": "useInternalNode<T>(id): InternalNode<T> | undefined",
    },
    "useNodesInitialized": {
        "kind": "hook", "category": "reactive",
        "summary": "True once all nodes are measured. Gate auto-layout / fitView on it.",
        "signature": "useNodesInitialized(options?: { includeHiddenNodes?: boolean }): boolean",
    },

    # ───────────────────────── utils ─────────────────────────
    "addEdge": {"kind": "util", "category": "edges", "summary": "Append edge, dedupe by source/target/handles.", "signature": "addEdge(params: Connection | Edge, edges: Edge[]): Edge[]"},
    "applyNodeChanges": {"kind": "util", "category": "nodes", "summary": "Reducer for onNodesChange.", "signature": "applyNodeChanges(changes: NodeChange[], nodes: Node[]): Node[]"},
    "applyEdgeChanges": {"kind": "util", "category": "edges", "summary": "Reducer for onEdgesChange.", "signature": "applyEdgeChanges(changes: EdgeChange[], edges: Edge[]): Edge[]"},
    "reconnectEdge": {"kind": "util", "category": "edges", "summary": "Rewire an edge's source/target.", "signature": "reconnectEdge(oldEdge: Edge, newConnection: Connection, edges: Edge[], options?): Edge[]"},
    "getConnectedEdges": {"kind": "util", "category": "graph", "summary": "Edges touching given nodes.", "signature": "getConnectedEdges(nodes: Node[], edges: Edge[]): Edge[]"},
    "getIncomers": {"kind": "util", "category": "graph", "summary": "Upstream source nodes.", "signature": "getIncomers(node, nodes, edges): Node[]"},
    "getOutgoers": {"kind": "util", "category": "graph", "summary": "Downstream target nodes.", "signature": "getOutgoers(node, nodes, edges): Node[]"},
    "getNodesBounds": {"kind": "util", "category": "geometry", "summary": "Bounding rect of node set.", "signature": "getNodesBounds(nodes, { nodeOrigin?, nodeLookup? }?): Rect"},
    "getViewportForBounds": {"kind": "util", "category": "geometry", "summary": "Compute viewport that fits given bounds — SSR-safe.", "signature": "getViewportForBounds(bounds, w, h, minZoom, maxZoom, padding?): Viewport"},
    "isNode": {"kind": "util", "category": "guard", "summary": "Type guard.", "signature": "isNode(x: unknown): x is Node"},
    "isEdge": {"kind": "util", "category": "guard", "summary": "Type guard.", "signature": "isEdge(x: unknown): x is Edge"},
    "getBezierPath": {
        "kind": "util", "category": "edge-path",
        "summary": "Bezier path builder for custom edges.",
        "signature": "getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition, curvature?=0.25 }): [path, labelX, labelY, offsetX, offsetY]",
    },
    "getSmoothStepPath": {
        "kind": "util", "category": "edge-path",
        "summary": "Smooth-step path builder. Set borderRadius:0 for sharp 'step'.",
        "signature": "getSmoothStepPath({ …, borderRadius?=5, stepPosition?=0.5, offset?, centerX?, centerY? }): [path, labelX, labelY, offsetX, offsetY]",
    },
    "getStraightPath": {"kind": "util", "category": "edge-path", "summary": "Straight path.", "signature": "getStraightPath({ sourceX, sourceY, targetX, targetY }): [path, labelX, labelY, offsetX, offsetY]"},
    "getSimpleBezierPath": {"kind": "util", "category": "edge-path", "summary": "Simpler bezier without bias.", "signature": "getSimpleBezierPath({ … }): [path, labelX, labelY, offsetX, offsetY]"},

    # ───────────────────────── types ─────────────────────────
    "Node": {
        "kind": "type", "category": "data",
        "summary": "Node object shape.",
        "signature": "Node<DataShape = any, TypeName extends string = string>",
        "notes": "Fields: id, position, data, type?, hidden?, selected?, dragging?, draggable?, selectable?, connectable?, deletable?, focusable?, dragHandle? (CSS selector), width?, height? (read-only measured — see node.measured.width/height in v12), initialWidth?, initialHeight?, parentId?, zIndex?, extent? (CoordinateExtent | 'parent' | null), expandParent?, origin?: NodeOrigin, handles?: NodeHandle[], measured?, ariaLabel?, ariaRole?, style?, className?.",
    },
    "Edge": {
        "kind": "type", "category": "data",
        "summary": "Edge object shape.",
        "signature": "Edge<DataShape = any, TypeName extends string = string>",
        "notes": "Fields: id, source, target, sourceHandle?, targetHandle?, type?, data?, animated?, hidden?, selected?, selectable?, deletable?, focusable?, reconnectable? (boolean | 'source' | 'target'), zIndex?, markerStart?: EdgeMarker, markerEnd?: EdgeMarker, label?, labelStyle?, labelShowBg?, labelBgStyle?, labelBgPadding?, labelBgBorderRadius?, interactionWidth?, style?, className?.",
    },
    "NodeProps": {
        "kind": "type", "category": "data",
        "summary": "Props injected into custom node components.",
        "signature": "NodeProps<NodeType = Node>",
        "notes": "Fields: id, type, data, selected, dragging, draggable, selectable, deletable, isConnectable, sourcePosition, targetPosition, dragHandle, parentId, zIndex, width, height, positionAbsoluteX, positionAbsoluteY.",
    },
    "EdgeProps": {
        "kind": "type", "category": "data",
        "summary": "Props injected into custom edge components.",
        "signature": "EdgeProps<EdgeType = Edge>",
        "notes": "Fields: id, type, source, target, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, sourceHandleId, targetHandleId, selected, selectable, deletable, animated, data, style, markerStart, markerEnd, interactionWidth, pathOptions, label, labelStyle, labelShowBg, labelBgStyle, labelBgPadding, labelBgBorderRadius.",
    },
    "Connection": {
        "kind": "type", "category": "data",
        "summary": "Payload of onConnect.",
        "signature": "{ source: string; target: string; sourceHandle: string | null; targetHandle: string | null }",
    },
    "Viewport": {"kind": "type", "category": "data", "summary": "Viewport state.", "signature": "{ x: number; y: number; zoom: number }"},
    "NodeChange": {"kind": "type", "category": "events", "summary": "Discriminated union.", "signature": "NodeAddChange | NodeRemoveChange | NodeReplaceChange | NodePositionChange | NodeDimensionChange | NodeSelectionChange"},
    "EdgeChange": {"kind": "type", "category": "events", "summary": "Discriminated union.", "signature": "EdgeAddChange | EdgeRemoveChange | EdgeReplaceChange | EdgeSelectionChange"},
    "FitViewOptions": {"kind": "type", "category": "viewport", "summary": "fitView config.", "signature": "{ padding?; includeHiddenNodes?; minZoom?; maxZoom?; duration?; ease?; interpolate?: 'smooth' | 'linear'; nodes?: Node[] | { id: string }[] }"},
    "ProOptions": {
        "kind": "type", "category": "pro",
        "summary": "Pro-related runtime config — ONLY runtime touchpoint marked Pro.",
        "signature": "{ account?: string; hideAttribution?: boolean }",
        "notes": "hideAttribution is a moral ask, not a technical block. See deep-dive doc.",
    },

    # ───────────────────────── enums ─────────────────────────
    "Position": {"kind": "enum", "category": "geometry", "summary": "Handle/side position.", "signature": "'left' | 'top' | 'right' | 'bottom'"},
    "ConnectionMode": {"kind": "enum", "category": "connection", "summary": "Strict = source→target only; Loose = any handle.", "signature": "'strict' | 'loose'"},
    "ConnectionLineType": {"kind": "enum", "category": "connection", "summary": "Connection-line variant.", "signature": "'default' (Bezier) | 'straight' | 'step' | 'smoothstep' | 'simplebezier'"},
    "MarkerType": {"kind": "enum", "category": "edges", "summary": "Edge end-marker.", "signature": "'arrow' | 'arrowclosed'"},
    "BackgroundVariant": {"kind": "enum", "category": "built-in", "summary": "Background pattern.", "signature": "'dots' | 'lines' | 'cross'"},
    "PanelPosition": {"kind": "enum", "category": "built-in", "summary": "Panel anchor.", "signature": "'top-left' | 'top-center' | 'top-right' | 'center-left' | 'center-right' | 'bottom-left' | 'bottom-center' | 'bottom-right'"},
    "PanOnScrollMode": {"kind": "enum", "category": "viewport", "summary": "Scroll-pan axis lock.", "signature": "'free' | 'horizontal' | 'vertical'"},
    "SelectionMode": {"kind": "enum", "category": "selection", "summary": "Partial = select when overlap; Full = require full enclosure.", "signature": "'full' | 'partial'"},
    "ColorMode": {"kind": "enum", "category": "theme", "summary": "Theme.", "signature": "'light' | 'dark' | 'system'"},
}


def list_symbols(*, kind: str | None = None, category: str | None = None) -> list[str]:
    """Return symbol names, optionally filtered by kind/category."""
    return [
        name
        for name, entry in API_CATALOG.items()
        if (kind is None or entry.get("kind") == kind)
        and (category is None or entry.get("category") == category)
    ]


def get_symbol(name: str) -> dict | None:
    """Case-insensitive lookup."""
    if name in API_CATALOG:
        return API_CATALOG[name]
    lower = name.lower()
    for key, entry in API_CATALOG.items():
        if key.lower() == lower:
            return entry
    return None
