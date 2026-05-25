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
    "Align": {"kind": "enum", "category": "geometry", "summary": "Anchor alignment for toolbars / labels.", "signature": "'start' | 'center' | 'end'"},
    "ZIndexMode": {"kind": "enum", "category": "viewport", "summary": "Strategy RF uses to assign zIndex to elements.", "signature": "'auto' | 'manual'"},

    # ───────────────────────── handler / callback types ─────────────────────────
    "OnConnect": {
        "kind": "type", "category": "callback",
        "summary": "Signature for the `onConnect` prop. Fires when a user completes a connection drag.",
        "signature": "(connection: Connection) => void",
    },
    "OnConnectStart": {
        "kind": "type", "category": "callback",
        "summary": "Fired when a connection drag begins.",
        "signature": "(event, params: { nodeId: string | null; handleId: string | null; handleType: 'source' | 'target' | null }) => void",
    },
    "OnConnectEnd": {
        "kind": "type", "category": "callback",
        "summary": "Fired when a connection drag ends — connected OR cancelled. Use to detect connection-to-empty for 'new node from connection' UX.",
        "signature": "(event, connectionState: ConnectionState) => void",
    },
    "OnNodesChange": {
        "kind": "type", "category": "callback",
        "summary": "Signature for the `onNodesChange` prop. Receives an array of NodeChange events to be applied via applyNodeChanges.",
        "signature": "(changes: NodeChange[]) => void",
    },
    "OnEdgesChange": {
        "kind": "type", "category": "callback",
        "summary": "Signature for the `onEdgesChange` prop.",
        "signature": "(changes: EdgeChange[]) => void",
    },
    "OnNodesDelete": {
        "kind": "type", "category": "callback",
        "summary": "Fires after one or more nodes are removed (post-delete-key, post-deleteElements).",
        "signature": "(nodes: Node[]) => void",
    },
    "OnEdgesDelete": {
        "kind": "type", "category": "callback",
        "summary": "Fires after one or more edges are removed.",
        "signature": "(edges: Edge[]) => void",
    },
    "OnDelete": {
        "kind": "type", "category": "callback",
        "summary": "Combined post-delete handler — fires once with all deleted nodes + edges.",
        "signature": "(params: { nodes: Node[]; edges: Edge[] }) => void",
    },
    "OnBeforeDelete": {
        "kind": "type", "category": "callback",
        "summary": "Pre-delete gate. Return false / Promise<false> to abort the deletion (e.g., show a confirm dialog).",
        "signature": "(params: { nodes: Node[]; edges: Edge[] }) => boolean | Promise<boolean>",
    },
    "OnInit": {
        "kind": "type", "category": "callback",
        "summary": "Fires once with the imperative ReactFlowInstance when the flow is ready.",
        "signature": "(instance: ReactFlowInstance) => void",
    },
    "OnMove": {
        "kind": "type", "category": "callback",
        "summary": "Fires during pan/zoom with the new viewport.",
        "signature": "(event: MouseEvent | TouchEvent | null, viewport: Viewport) => void",
    },
    "OnNodeDrag": {
        "kind": "type", "category": "callback",
        "summary": "Per-node drag callback — onNodeDragStart / onNodeDrag / onNodeDragStop share this signature.",
        "signature": "(event, node: Node, nodes: Node[]) => void",
    },
    "OnReconnect": {
        "kind": "type", "category": "callback",
        "summary": "Edge endpoint reconnection. (Replaces v11 `onEdgeUpdate`.)",
        "signature": "(oldEdge: Edge, newConnection: Connection) => void",
    },
    "OnError": {
        "kind": "type", "category": "callback",
        "summary": "Custom error reporter. RF emits warnings via console.warn by default; override to integrate with Sentry etc.",
        "signature": "(code: string, message: string) => void",
    },
    "OnSelectionChangeFunc": {
        "kind": "type", "category": "callback",
        "summary": "Selection-change handler. Receives all selected nodes + edges (not the delta).",
        "signature": "(params: { nodes: Node[]; edges: Edge[] }) => void",
    },
    "SelectionDragHandler": {
        "kind": "type", "category": "callback",
        "summary": "onSelectionDragStart / onSelectionDrag / onSelectionDragStop signature.",
        "signature": "(event, nodes: Node[]) => void",
    },
    "NodeMouseHandler": {
        "kind": "type", "category": "callback",
        "summary": "onNodeClick / onNodeDoubleClick / onNodeMouseEnter / onNodeMouseMove / onNodeMouseLeave / onNodeContextMenu signature.",
        "signature": "(event, node: Node) => void",
    },
    "EdgeMouseHandler": {
        "kind": "type", "category": "callback",
        "summary": "onEdgeClick / onEdgeDoubleClick / onEdgeMouse* / onEdgeContextMenu signature.",
        "signature": "(event, edge: Edge) => void",
    },

    # ───────────────────────── support types ─────────────────────────
    "ConnectionState": {
        "kind": "type", "category": "data",
        "summary": "State of an in-progress connection drag (returned by useConnection).",
        "signature": "{ inProgress: boolean; isValid: boolean | null; fromNode: Node | null; fromHandle: NodeHandle | null; fromPosition: Position | null; toNode: Node | null; toHandle: NodeHandle | null; toPosition: Position | null; from: XYPosition | null; to: XYPosition | null }",
    },
    "ConnectionLineComponent": {
        "kind": "type", "category": "data",
        "summary": "Custom connection-line component type.",
        "signature": "React.ComponentType<ConnectionLineComponentProps>",
    },
    "ConnectionLineComponentProps": {
        "kind": "type", "category": "data",
        "summary": "Props injected into a custom connection-line component during drag.",
        "signature": "{ fromX: number; fromY: number; toX: number; toY: number; fromPosition: Position; toPosition: Position; connectionLineType: ConnectionLineType; connectionLineStyle?: CSSProperties; fromNode?: Node; fromHandle?: NodeHandle }",
    },
    "NodeTypes": {
        "kind": "type", "category": "data",
        "summary": "Map of custom node type name → component. Declare OUTSIDE component or wrap in useMemo.",
        "signature": "Record<string, React.ComponentType<NodeProps>>",
    },
    "EdgeTypes": {
        "kind": "type", "category": "data",
        "summary": "Map of custom edge type name → component. Same memo rule as NodeTypes.",
        "signature": "Record<string, React.ComponentType<EdgeProps>>",
    },
    "DefaultEdgeOptions": {
        "kind": "type", "category": "data",
        "summary": "Defaults applied to every newly-created edge (from onConnect or addEdges).",
        "signature": "{ type?: string; animated?: boolean; hidden?: boolean; deletable?: boolean; selectable?: boolean; markerStart?: EdgeMarker; markerEnd?: EdgeMarker; style?: CSSProperties; data?: any; zIndex?: number; pathOptions?: any }",
    },
    "EdgeMarker": {
        "kind": "type", "category": "data",
        "summary": "Edge end marker (arrowhead) config.",
        "signature": "{ type: 'arrow' | 'arrowclosed'; color?: string; width?: number; height?: number; orient?: string; strokeWidth?: number }",
    },
    "NodeHandle": {
        "kind": "type", "category": "data",
        "summary": "Single handle entry on a node's handles[] array. Required for SSR edge rendering.",
        "signature": "{ id: string | null; type: 'source' | 'target'; position: Position; x?: number; y?: number; width?: number; height?: number }",
    },
    "NodeConnection": {
        "kind": "type", "category": "data",
        "summary": "Connection entry returned by useNodeConnections / instance.getNodeConnections.",
        "signature": "{ source: string; target: string; sourceHandle: string | null; targetHandle: string | null; edgeId: string }",
    },
    "HandleConnection": {
        "kind": "type", "category": "data",
        "summary": "Alias for NodeConnection — same shape, returned by useHandleConnections (deprecated).",
        "signature": "NodeConnection",
        "deprecated": True, "replacement": "NodeConnection",
    },
    "InternalNode": {
        "kind": "type", "category": "data",
        "summary": "Internal node representation with computed absolute position + measured dims. Returned by useInternalNode / instance.getInternalNode.",
        "signature": "Node<DataShape> & { internals: { positionAbsolute: XYPosition; handleBounds?: { source?: NodeHandle[]; target?: NodeHandle[] }; userNode: Node } }",
    },
    "ReactFlowInstance": {
        "kind": "type", "category": "data",
        "summary": "Imperative API returned by useReactFlow(). Full method list in `useReactFlow` notes.",
        "signature": "{ getNodes, setNodes, addNodes, getNode, updateNode, updateNodeData, getEdges, setEdges, addEdges, getEdge, updateEdge, updateEdgeData, getZoom, zoomIn, zoomOut, zoomTo, getViewport, setViewport, setCenter, fitView, fitBounds, screenToFlowPosition, flowToScreenPosition, getIntersectingNodes, isNodeIntersecting, getNodeConnections, getHandleConnections, getNodesBounds, deleteElements, toObject, viewportInitialized }",
    },
    "ReactFlowJsonObject": {
        "kind": "type", "category": "data",
        "summary": "Serialized flow shape returned by instance.toObject() — nodes + edges + viewport.",
        "signature": "{ nodes: Node[]; edges: Edge[]; viewport: Viewport }",
    },
    "IsValidConnection": {
        "kind": "type", "category": "callback",
        "summary": "Per-flow or per-handle validator — return false to block the connection mid-drag.",
        "signature": "(connection: Connection | Edge) => boolean",
    },
    "DeleteElements": {
        "kind": "type", "category": "callback",
        "summary": "Type of instance.deleteElements method.",
        "signature": "(params: { nodes?: { id: string }[] | Node[]; edges?: { id: string }[] | Edge[] }) => Promise<{ deletedNodes: Node[]; deletedEdges: Edge[] }>",
    },
    "MiniMapNodeProps": {
        "kind": "type", "category": "data",
        "summary": "Props injected into a custom MiniMap node renderer (passed as nodeComponent prop).",
        "signature": "{ id: string; x: number; y: number; width: number; height: number; borderRadius: number; color: string; strokeColor: string; strokeWidth: number; className?: string; selected: boolean; shapeRendering: 'auto' | 'crispEdges' | 'geometricPrecision' | 'optimizeSpeed' }",
    },
    "ResizeParams": {
        "kind": "type", "category": "data",
        "summary": "Argument passed to NodeResizer onResize / onResizeStart / onResizeEnd callbacks.",
        "signature": "{ x: number; y: number; width: number; height: number }",
    },
    "AriaLabelConfig": {
        "kind": "type", "category": "data",
        "summary": "Override built-in ARIA labels (i18n / customization). Each key is a function returning the label string.",
        "signature": "{ 'node.a11yDescription.default': () => string; 'node.a11yDescription.keyboardDisabled': () => string; 'edge.a11yDescription.default': () => string; 'controls.zoomIn': () => string; … many more }",
    },

    # ───────────────────────── geometry / config types ─────────────────────────
    "XyPosition": {
        "kind": "type", "category": "geometry",
        "summary": "2D coordinate pair used throughout RF.",
        "signature": "{ x: number; y: number }",
    },
    "Rect": {
        "kind": "type", "category": "geometry",
        "summary": "Bounding rectangle.",
        "signature": "{ x: number; y: number; width: number; height: number }",
    },
    "CoordinateExtent": {
        "kind": "type", "category": "geometry",
        "summary": "Min/max bounds for pan or node placement. `[[minX, minY], [maxX, maxY]]`.",
        "signature": "[[number, number], [number, number]]",
    },
    "NodeOrigin": {
        "kind": "type", "category": "geometry",
        "summary": "Origin point used for node positioning. [0,0]=top-left (default); [0.5,0.5]=center.",
        "signature": "[number, number]",
    },
    "SnapGrid": {
        "kind": "type", "category": "geometry",
        "summary": "Snap-to-grid spacing.",
        "signature": "[number, number]",
    },
    "KeyCode": {
        "kind": "type", "category": "input",
        "summary": "Keyboard binding spec. String for single key, array for multi-key (any-matches), '+' for modifiers.",
        "signature": "string | string[]   // e.g. 'Backspace', ['Meta+z','Control+z']",
    },
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
