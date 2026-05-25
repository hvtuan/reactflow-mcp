# React Flow / xyflow — Deep-Dive Brief

> Snapshot: 2026-05-25. Sources: reactflow.dev/learn, reactflow.dev/api-reference, reactflow.dev/pro, github.com/xyflow/xyflow.

---

## 0. TL;DR

- **Vendor:** xyflow GmbH (Berlin, ex-webkid). MIT core, paid Pro layer.
- **Packages** (all from monorepo, all MIT, Changesets-released together):
  - `@xyflow/react@12.10.2` — React 17+, depends on Zustand 4 + classcat + `@xyflow/system`.
  - `@xyflow/svelte@1.5.2` — Svelte **5 only**.
  - `@xyflow/system@0.0.76` — framework-agnostic core (d3-drag/zoom/selection/interpolate). Both framework packages are thin adapters around it.
- **Legacy:** `reactflow` v11 still maintained on `v11` branch (no new features).
- **Stars:** ~36.7k. License: MIT throughout. Release cadence: every 4–8 weeks, coordinated across all 3 pkgs.
- **Pro:** subscription product; gates *advanced code examples + templates + priority support*, **not** library features. Core stays MIT forever.

---

## 1. Mental model

```
ReactFlowProvider              ← context (auto when using <ReactFlow/>)
└─ <ReactFlow nodes edges …>   ← viewport + canvas
   ├─ <Background />           ← dots/lines/cross
   ├─ <Controls />             ← zoom/fit/lock buttons
   ├─ <MiniMap />              ← birds-eye
   └─ <Panel position="…" />   ← floating UI (toolbars, titles)
```

- **Node** = `{ id, position:{x,y}, data, type? }` rendered by component from `nodeTypes[type]`.
- **Edge** = `{ id, source, target, sourceHandle?, targetHandle?, type? }` rendered by `edgeTypes[type]` (defaults: `default` bezier, `straight`, `step`, `smoothstep`).
- **Handle** = connection port on a node; React `<Handle type="source|target" position={Position.Top|Bottom|Left|Right} id?/>`.
- **Viewport** = `{x, y, zoom}` — pan/zoom transforms the SVG layer.

State pattern (the canonical one):
```tsx
const [nodes, setNodes, onNodesChange] = useNodesState(initial);
const [edges, setEdges, onEdgesChange] = useEdgesState(initial);
const onConnect = useCallback((c) => setEdges((es) => addEdge(c, es)), []);
```
For prod / multi-component: lift into Zustand store (RF already uses Zustand internally, recommended in docs).

---

## 2. Free / OSS features — full surface

### 2.1 Concepts
- **Adding interactivity**: controlled flow via `applyNodeChanges` / `applyEdgeChanges` reducers; `useCallback([])` handlers to avoid child re-renders; use functional setters to dodge stale closures. Uncontrolled flow via `defaultNodes`/`defaultEdges`.
- **Viewport**: `panOnDrag`, `panOnScroll`, `zoomOnScroll`, `zoomOnPinch`, `minZoom/maxZoom`, `selectionOnDrag`, `selectionMode`. Figma preset = `panOnDrag:false + panOnScroll:true + selectionOnDrag:true`. Programmatic via `useReactFlow().{setViewport, zoomIn/Out, fitView}`. Cursor↔flow: `screenToFlowPosition` (new — old `project()` is gone).
- **Built-in components**: `Background`, `Controls`, `MiniMap`, `Panel`, `NodeToolbar`, `NodeResizer`, `NodeResizeControl`. All MIT, no Pro gating.

### 2.2 Customization
- **Handles**: multi-handle nodes need unique `id`. After dynamic handle changes call `useUpdateNodeInternals(id)` or edges desync. Hide handles with `visibility:hidden` (never `display:none`). CSS classes added during drag: `connecting`, `connectingto`, `connectingfrom`, `valid`. `connectionMode="Loose"` for typeless connections.
- **Custom nodes**: define component → register `nodeTypes` **outside** component (or `useMemo`). Add `nodrag` class on inputs/buttons inside the node.
- **Custom edges**: register `edgeTypes` likewise. Path utils: `getBezierPath`, `getSmoothStepPath`, `getStraightPath`, `getSimpleBezierPath` — all return `[path, labelX, labelY, offsetX, offsetY]`. Wrap with `<BaseEdge path={d} markerEnd={m}/>` for free selection/events. Raw `<path>` is not interactive.
- **Edge labels**: edges are SVG — use `<EdgeLabelRenderer>` portal to render HTML labels. Position with `translate(-50%,-50%) translate(${labelX}px,${labelY}px)`. Add `pointer-events:all` + `nodrag nopan` classes for clickable labels.
- **Utility classes**: `nodrag` (block node drag), `nopan` (block canvas pan), `nowheel` (block zoom — pair with `overflow:auto` for scrollable node content).
- **Theming**: import `@xyflow/react/dist/style.css` first (or `base.css` for raw foundation). CSS vars `--xy-*` on `.react-flow`. `colorMode="light|dark|system"` prop toggles theme. Tailwind works inside custom nodes without setup.

### 2.3 Layouting
- **Approaches**: dagre (drop-in trees), d3-hierarchy (uniform sizes), d3-force (physics, needs rect collision), elkjs (most powerful, async), entitree-flex (variable sizes). Pattern: compute positions in pure fn → `setNodes(ns => ns.map(n => ({...n, position: layout[n.id]})))`. **Gate on `useNodesInitialized()`** so nodes are measured first.
- **Sub-flows**: `parentId` (string id; old `parentNode` is **deprecated**). `extent:'parent'` clamps. Child `position` is **relative to parent top-left**. Parents must come **before** children in array. `type:'group'` = convenience handle-less node.

### 2.4 Advanced use
- **Hooks-providers**: `<ReactFlowProvider>` needed when hooks used outside `<ReactFlow>`, multiple flows on one page, or client routing. Each flow = its own provider, otherwise stores collide.
- **Accessibility**: Tab cycles nodes/edges; Enter/Space select; arrows move (Shift = faster). Props: `nodesFocusable`, `edgesFocusable`, `disableKeyboardA11y`, `autoPanOnNodeFocus`, `ariaLabelConfig` (i18n). Per-node `ariaRole`/`domAttributes`. Aims WCAG 2.1 AA.
- **Testing**: Cypress/Playwright = native (use those, repo itself uses Playwright for E2E). Jest needs polyfills for `ResizeObserver`, `DOMMatrixReadOnly`, `offsetWidth/Height`, `getBBox()`. Helper `mockReactFlow()` in `setupTests.ts`. Disable `nodesDraggable`/`panOnDrag` in Jest (d3-drag doesn't run without browser).
- **TypeScript**: `Node<DataShape, 'typeStringLiteral'>`. Discriminated union pattern: `type AppNode = NumberNode | TextNode`. Hooks accept generics: `useReactFlow<AppNode, AppEdge>()`. Custom node: `function MyNode({data}: NodeProps<MyNodeType>)`.
- **Uncontrolled flow**: `defaultNodes`/`defaultEdges` only, no change handlers. RF owns state internally — less boilerplate, fewer re-renders. Mutate via `useReactFlow()`. Requires `<ReactFlowProvider>` or `onInit` capture.
- **Performance** (the important one):
  - Declare `nodeTypes`/`edgeTypes` **outside** component (recreating triggers warnings + full re-renders).
  - `React.memo` custom node/edge components.
  - `useCallback` handlers, `useMemo` objects like `defaultEdgeOptions`.
  - Subscribe narrowly via `useStore(selector)`, not full `useNodes()`.
  - Keep `selectedIds` in separate state so nodes array doesn't churn.
  - `onlyRenderVisibleElements` prop for huge graphs (slight pan cost).
  - `hidden:true` on nodes for collapsed/lazy trees.
  - Avoid shadows/blurs/gradients/transitions in large flows.
  - Never call `getNodes()` in drag/pan/zoom-frequency callbacks.
- **Computing flows** (the data-flow story): keep inputs in `node.data`; mutate via `updateNodeData(id, patch)` (merges; `{replace:true}` overwrites). Use `useNodeConnections({id, handleType, handleId})` + `useNodesData(ids)` to read upstream data reactively. Branch on `handleId` for multi-output. Keep local UI state (cursor) separate from `node.data` to avoid jumps.
- **SSR/SSG**: RF only renders nodes that have `width`/`height`. Set fixed `node.width/height`, or `initialWidth/initialHeight` for content-driven (hydrated on client). Edges need pre-computed `node.handles` array on server. Pass `width`/`height` to `<ReactFlow>` for server fitView. `<ReactFlowProvider initialNodes initialEdges initialWidth initialHeight fitView>` for SSR. Works with `renderToStaticMarkup` for OG images / static docs.
- **Devtools/debugging**: no official package — recipes in docs. **ViewportLogger** = `useStore(s=>s.transform)` in a `<Panel>`. **NodeInspector** = `useNodes()` + `<ViewportPortal>` overlaying ids/dims. **ChangeLogger** = wrap change handlers, log `NodeChange`/`EdgeChange` discriminated unions.
- **Multiplayer**: two paths.
  - **CRDT** (Yjs, Automerge) — offline-first, auto merge, manual DB adapter.
  - **Server-authoritative** (Liveblocks has a dedicated React Flow SDK; Velt; Supabase Realtime) — easier persistence, needs net.
  - Sync only durable fields: `id, type, data, position, dimensions`. **Never** sync `selected/dragging/measured`. Awareness channel for cursors/viewport/in-progress connections; `perfect-cursors` for smooth remote pointers.
- **Whiteboard**: recipe-style page. Free patterns: lasso, eraser (collision), rectangle draw, mode-toggle state machine. **Freehand draw example is Pro-only**.

### 2.5 Troubleshooting / common errors
- **#001** zustand provider missing → wrap with `<ReactFlowProvider>` or duplicate `@xyflow/react` install.
- **#002** duplicate package → nuke `node_modules` + lockfile, reinstall.
- **#003** `nodeTypes/edgeTypes` recreated → declare outside or `useMemo`.
- **#004** "Node type not found" → `type` string mismatch (case-sensitive) with `nodeTypes` key.
- **#005** "parent needs width/height" → wrapper div needs explicit height (`100vh`, fixed px, or flex/grid).
- **#006** "child needs parent extent" → drop `extent:'parent'` or set `parentId`.
- **#007** edge missing source/target → validate edge ids.
- **#008** handle id mismatch → call `useUpdateNodeInternals()` after programmatic handle changes.
- **#009** styles missing → `import '@xyflow/react/dist/style.css'` at entry.
- **#013** Webpack 4 → add `@babel/preset-env` + optional-chaining plugin.

### 2.6 v11 → v12 migration (biggest gotcha if upgrading)
- Package rename: `reactflow` → `@xyflow/react`. Default export gone — named imports only.
- React **18+** required (uses concurrent features internally).
- `node.width/height` now SET inline styles (fixed size). **Measured** values moved to `node.measured.{width,height}`.
- `parentNode` → `parentId` (string id, not ref).
- Custom node props: `xPos/yPos` → `positionAbsoluteX/positionAbsoluteY`.
- Edge reconnection rename: `onEdgeUpdate` → `onReconnect`; `edgesUpdatable` → `edgesReconnectable`; all `*EdgeUpdate*` callbacks → `*Reconnect*`.
- **Immutability enforced** — never mutate nodes/edges in place.
- Handle classes: `react-flow__handle-connecting` → `connectingto/connectingfrom`; `react-flow__handle-valid` → `valid`.
- Store internal rename: `nodeInternals` → `nodeLookup`.
- New features unlocked: SSR/SSG, `colorMode` dark mode, computing-flows (`updateNodeData`, `useNodesData`, `useNodeConnections`), `useNodesInitialized`.

---

## 3. API cheat-sheet

### 3.1 `<ReactFlow />` prop groups (just headers — full table in agent log)
- **Data**: `nodes`, `edges`, `defaultNodes`, `defaultEdges`, `nodeTypes`, `edgeTypes`, `defaultEdgeOptions`, `nodeOrigin`, `width`, `height`.
- **Viewport**: `defaultViewport`, `viewport`, `onViewportChange`, `fitView`, `fitViewOptions`, `minZoom`, `maxZoom`, `snapToGrid`, `snapGrid`, `translateExtent`, `nodeExtent`, `onlyRenderVisibleElements`, `preventScrolling`.
- **Interaction**: `nodesDraggable`, `nodesConnectable`, `nodesFocusable`, `edgesFocusable`, `elementsSelectable`, `selectNodesOnDrag`, `elevateNodesOnSelect`, `elevateEdgesOnSelect`, `panOnDrag`, `panOnScroll`, `panOnScrollSpeed`, `panOnScrollMode`, `zoomOnScroll`, `zoomOnPinch`, `zoomOnDoubleClick`, `selectionOnDrag`, `selectionMode`, `connectionMode`, `connectionLineType/Style/ContainerStyle`, `connectionLineComponent`, `connectionRadius`, `connectOnClick`, `isValidConnection`, `reconnectRadius`, `edgesReconnectable`, `nodeDragThreshold`, `connectionDragThreshold`, `nodeClickDistance`, `paneClickDistance`, `autoPanOnConnect/NodeDrag/NodeFocus`, `autoPanSpeed`, `zIndexMode`.
- **Keyboard**: `deleteKeyCode`, `selectionKeyCode`, `multiSelectionKeyCode`, `zoomActivationKeyCode`, `panActivationKeyCode`, `disableKeyboardA11y`, `noPanClassName`, `noDragClassName`, `noWheelClassName`.
- **Style/a11y/debug**: `colorMode`, `ariaLabelConfig`, `defaultMarkerColor`, `attributionPosition`, `proOptions`, `debug`.
- **Events** (60+): nodes (`onNodeClick/DoubleClick/Mouse{Enter,Move,Leave}/ContextMenu/Drag{Start,,Stop}/Change/Delete`), edges (`onEdge{Click,DoubleClick,Mouse*,ContextMenu,Change,Delete,Reconnect{,Start,End}}`), connect (`onConnect{,Start,End}`, `onClickConnect{Start,End}`), pane (`onPane{Click,ContextMenu,Scroll,Mouse{Move,Enter,Leave}}`), selection (`onSelection{Change,Start,End,Drag{,Start,Stop},ContextMenu}`), lifecycle (`onInit`, `onMove{,Start,End}`, `onDelete`, `onBeforeDelete` ← return false to abort, `onError`).

### 3.2 Components
- `<Background>` — `variant: dots|lines|cross`, `gap`, `size`, `color`, `lineWidth`, etc.
- `<Controls>` — `showZoom/FitView/Interactive`, `orientation`, custom buttons via `<ControlButton>`.
- `<MiniMap>` — `pannable`, `zoomable`, `nodeColor/StrokeColor/ClassName` as fn or string, `maskColor`, `onClick`, `onNodeClick`.
- `<Panel>` — floating div, `position: top-left | top-center | ... | bottom-right`.
- `<Handle>` — `type`, `position`, `id`, `isConnectable{,Start,End}`, `isValidConnection`, `onConnect`.
- `<NodeToolbar>` — `nodeId(string|string[])`, `isVisible`, `position`, `align`, `offset`. Shows only when node selected unless overridden.
- `<NodeResizer>` — `color`, `keepAspectRatio`, `autoScale`, `min/max{Width,Height}`, `should/onResize{,Start,End}`. Lower-level: `<NodeResizeControl>`.
- `<EdgeText>` (SVG) — `label`, `labelStyle`, `labelShowBg`, `labelBgStyle/Padding/BorderRadius`.
- `<BaseEdge>` — SVG `<path>` wrapper with `path`, `markerStart/End`, `interactionWidth`, `labelX/Y` + all label* props.
- `<EdgeLabelRenderer>` — HTML portal above SVG for interactive labels (see Customization).
- `<EdgeToolbar>` — `edgeId`, `x/y`, `isVisible`, `alignX/Y`. Non-scaling.
- `<ViewportPortal>` — render children inside transformed viewport coord space (pans/zooms with flow).
- `<ReactFlowProvider>` — context, with optional init props for SSR.

### 3.3 Hooks
- `useReactFlow<N,E>()` → instance (getNodes/setNodes/addNodes/updateNode/updateNodeData/fitView/screenToFlowPosition/flowToScreenPosition/getIntersectingNodes/deleteElements/toObject…).
- `useNodes()`, `useEdges()` — reactive arrays (re-render on any change). Use selectors via `useStore` for perf.
- `useNodesState(init)`, `useEdgesState(init)` → `[items, set, onChange]` tuple (prototyping shortcut).
- `useStore(selector, eq?)` — Zustand-style narrow subscription.
- `useStoreApi()` — `{getState, setState, subscribe}` imperative, no re-render.
- `useViewport()` → `{x,y,zoom}`.
- `useKeyPress(keyCode | string[], options?)` — kbd booleans; works outside RF context.
- `useUpdateNodeInternals()` → call with id(s) after dynamic handle/position changes.
- `useOnSelectionChange({onChange})` — **callback MUST be `useCallback`-memoized**, else silently breaks.
- `useOnViewportChange({onStart, onChange, onEnd})` — same memo caveat.
- `useNodeId()` — current node id when inside custom node component.
- `useNodesData(id | id[])` — subscribe to only `data` slice (narrower than `useNodes`).
- `useConnection(selector?)` — active in-progress connection state, null when idle.
- `useNodeConnections({id?, handleType?, handleId?, onConnect?, onDisconnect?})` → connections list.
- `useHandleConnections(...)` — **deprecated**, use `useNodeConnections`.
- `useInternalNode<T>(id)` — internal node with absolute position + measured dims.
- `useNodesInitialized({includeHiddenNodes?})` — true once all measured. Gate layout on it.

### 3.4 Utils
- `addEdge(params, edges)`, `applyNodeChanges(changes, nodes)`, `applyEdgeChanges(changes, edges)`, `reconnectEdge(old, newConn, edges, opts?)`.
- `getConnectedEdges(nodes, edges)`, `getIncomers(node, nodes, edges)`, `getOutgoers(node, nodes, edges)`.
- `getNodesBounds(nodes, opts?)`, `getViewportForBounds(bounds, w, h, minZ, maxZ, padding?)` — SSR-safe viewport calc.
- `isNode(x)`, `isEdge(x)` — type guards.
- Path builders (all return `[path, labelX, labelY, offsetX, offsetY]`): `getBezierPath`, `getSmoothStepPath` (set `borderRadius:0` for sharp `step`), `getStraightPath`, `getSimpleBezierPath`.

### 3.5 Types
- `Node`, `Edge` — full field list in agent log; key fields: `id, position, data, type, hidden, selected, draggable, selectable, connectable, deletable, dragHandle (CSS selector), parentId, extent, zIndex, measured, handles, style, className`.
- `NodeProps<N>` (custom node injected): `id, type, data, selected, dragging, draggable, isConnectable, sourcePosition, targetPosition, dragHandle, parentId, zIndex, width, height, positionAbsoluteX/Y`.
- `EdgeProps<E>`: `id, type, source, target, sourceX/Y, targetX/Y, sourcePosition, targetPosition, sourceHandleId, targetHandleId, selected, animated, data, markerStart/End, interactionWidth, pathOptions, label*`.
- `Connection`: `{source, target, sourceHandle, targetHandle}` — payload of `onConnect`.
- `Viewport`: `{x, y, zoom}`.
- `NodeChange` union: Add/Remove/Replace/Position/Dimension/Selection.
- `EdgeChange` union: Add/Remove/Replace/Selection.
- Enums: `Position`, `ConnectionMode (Strict|Loose)`, `ConnectionLineType (Bezier|Straight|Step|SmoothStep|SimpleBezier)`, `MarkerType (Arrow|ArrowClosed)`, `BackgroundVariant (Dots|Lines|Cross)`, `PanelPosition` (8 corners/midpoints), `PanOnScrollMode (Free|Horizontal|Vertical)`, `SelectionMode (Full|Partial)`, `ColorMode (light|dark|system)`, `ZIndexMode`.
- `FitViewOptions`: `padding, includeHiddenNodes, minZoom, maxZoom, duration, ease, interpolate (smooth|linear), nodes`.
- `ProOptions`: `{account?, hideAttribution?}` — **only `[PRO]` runtime config in the entire API**.

---

## 4. Pro (paid) layer

**Important framing:** Pro gates *code examples + templates + support*, not library features. The `<ReactFlow>` API is identical for OSS and Pro users. `proOptions.hideAttribution` is the lone "Pro" runtime flag — and technically anyone can flip it (it's a moral/funding ask, not a license obligation).

### 4.1 Pricing (3 tiers, monthly/yearly toggle)
Pricing numbers are rendered client-side and **not extractable via WebFetch/cached snippets**. Unverified secondary mention: "from ~€129/mo Starter". Confirm by opening reactflow.dev/pro/pricing with JS on.

| Tier | Seats | Includes |
|---|---|---|
| **Starter** | 1 invited | Pro Examples + Pro Templates access; prioritized GitHub issues |
| **Professional** | 5 invited | + up to 1 hr/mo email support + 1:1 intro call with a creator |
| **Enterprise** | 10 invited | + **perpetual** access to future Pro content + voice/video support 1 hr/mo + custom procurement |

### 4.2 Pro Examples (full current list, from pro-examples.reactflow.dev)

**Layout**: Auto Layout (dagre/elkjs/d3-force variants), Dynamic Layouting (+ dagre variant), Expand & Collapse (+ d3 variant), Force Layout, libavoid Edge Routing.

**Interaction**: Helper Lines (snap guides), Collaborative (yjs cursors + shared state), Copy & Paste, Undo & Redo (add/delete/connect/position), Node Position Animation.

**Edges**: Editable Edge (draggable control points).

**Nodes**: Shapes (SVG flowchart shapes), Resize & Rotate (deprecated).

**Grouping**: Parent/Child Relation (drag-into-container), Dynamic Grouping, Selection Grouping.

**Whiteboard**: Freehand Draw.

**Misc**: Server-Side Image Creation (PNG/SVG export), Remove Attribution (recipe), Workflow Editor (Next.js starter), AI Workflow Editor (Next.js + AI SDK + Zustand + shadcn).

Svelte Flow Pro subset is smaller: Auto Layout, Copy/Paste, Expand-Collapse, Force Layout, Freehand, Node Animation, Parent-Child, Remove Attribution, Selection Grouping, Server-Side Image, Shapes, Undo-Redo.

### 4.3 Pro Templates (vs free UI components)
- **Pro Templates** (subscription, private repo delivery): **Workflow Editor**, **AI Workflow Editor**.
- **React Flow UI** at reactflow.dev/ui = shadcn-style copy-paste registry: Base Node, Status Indicator, Tooltip, Database Schema Node, Placeholder Node, Labeled Group, Base/Labeled/Button Handles, Edge-with-Button, Edge-with-Node-Data, Animated SVG Edge, Node Search, Zoom Slider, Zoom Select, DevTools. **This is FREE / MIT — not Pro.** Install: `npx shadcn@latest add https://ui.reactflow.dev/<component>`.

### 4.4 Pro License (xyflow.com/pro-license)
- Perpetual, worldwide, non-exclusive, non-transferable right to use Pro content in commercial + non-commercial apps **while subscription is active**.
- **Cancel → keep using what you already downloaded**, lose access to new content/updates. Enterprise tier extends perpetual access to all future content.
- Cannot republish Pro examples as a competing template/lib.
- Per-seat-vs-per-project granularity is **not explicitly stated**; seat bundles 1/5/10 imply per-developer. Email info@xyflow.com for higher-tier clarification.
- **Core MIT license unchanged.** Pro revenue funds OSS.

### 4.5 Attribution badge (`proOptions.hideAttribution`)
- Bottom-right "React Flow" link.
- Technically anyone can set `proOptions={{hideAttribution: true}}`. It's a **moral ask, not enforced**.
- Official position (`/learn/troubleshooting/remove-attribution`): personal projects = go ahead. Commercial = please subscribe to Pro or sponsor on GitHub.

### 4.6 Support tiers
| Tier | Channels | Volume |
|---|---|---|
| Starter | Prioritized GitHub issues | — |
| Professional | + email | 1 hr/mo + intro call |
| Enterprise | + voice/video | 1 hr/mo + intro call + custom procurement |
No public SLA on response time / uptime.

### 4.7 OSS vs Pro at a glance

| Feature | OSS (MIT, free) | Pro (paid) |
|---|---|---|
| Core React Flow / Svelte Flow library | ✅ | ✅ |
| All built-in components (Bg, Controls, MiniMap, Panel, Resizer, Toolbar) | ✅ | ✅ |
| React Flow UI shadcn registry | ✅ | ✅ |
| Basic examples (`/examples` non-pro) | ✅ | ✅ |
| Hide attribution | technically ✅ (moral ask only) | ✅ encouraged |
| Advanced examples (collab, copy/paste, undo/redo, autolayout, force, expand, helper lines, shapes, freehand, dynamic groups, editable edges, server-side image, libavoid) | ❌ | ✅ |
| Pro Templates (Workflow Editor, AI Workflow Editor) | ❌ | ✅ |
| Prioritized GitHub issues | ❌ | ✅ all tiers |
| Email 1:1 support | ❌ | Pro + Enterprise |
| Voice/video support | ❌ | Enterprise only |
| Intro call with creator | ❌ | Pro + Enterprise |
| Custom procurement / contract | ❌ | Enterprise only |
| Perpetual access to future Pro content | ❌ | Enterprise only |
| Team seats | n/a | 1 / 5 / 10 |

---

## 5. Ecosystem / xyflow org

- **`xyflow/xyflow`** — main monorepo (3 packages above + tooling configs + examples + Playwright E2E). pnpm workspaces + Turborepo + Changesets.
- **`xyflow/web`** — docs sites for reactflow.dev / svelteflow.dev / xyflow.com (MDX). Where doc PRs land.
- **`xyflow/pro-platform`** — public source of the Pro subscriber portal (Next.js + Nhost + Stripe + shadcn). MIT. Pro examples themselves live in a **separate private repo**.
- **Starter kits**: `vite-react-flow-template`, `vite-svelte-flow-template`.
- **Tutorial apps**: `react-flow-mindmap-app`, `react-flow-web-audio`, `react-flow-slide-show`, `react-flow-example-apps` (CRA/Next/Remix integrations).
- **Lists**: `awesome-node-based-uis` (3.5k+ stars curated list).
- **Case-study customers named**: Carto, DoubleLoop, Hubql, OneSignal, Stripe, Typeform.

**Contribution philosophy**: explicitly "cathedral" — core team gatekeeps features, discuss in Discussions/Discord before opening feature PRs. Bug fixes + docs PRs are the preferred contribution path.

---

## 6. Recurring gotchas (the "you'll hit these" list)

1. Declare `nodeTypes` / `edgeTypes` **outside** component or `useMemo` — recreating them every render warns + tanks perf.
2. After dynamic handle changes → `useUpdateNodeInternals(id)`.
3. `useOnSelectionChange` / `useOnViewportChange` handlers MUST be `useCallback`-memoized.
4. Inside custom nodes, add `nodrag` to inputs/buttons; inside edge labels, add `nodrag nopan` + `pointer-events:all`.
5. Hide handles with `visibility:hidden` (never `display:none`).
6. Parent nodes must appear **before** children in array; child `position` is **relative to parent**.
7. `parentNode` → `parentId`; `onEdgeUpdate` → `onReconnect`; `xPos/yPos` → `positionAbsoluteX/Y`; `useHandleConnections` → `useNodeConnections`.
8. `node.width/height` in v12 = inline style; measured dims live at `node.measured.{width,height}`.
9. SSR requires explicit `node.width/height` (or initial*) + pre-computed `node.handles[]` array for edges.
10. In Jest, polyfill `ResizeObserver/DOMMatrixReadOnly/offsetWidth-Height/getBBox` and disable drag/pan.
11. Use `screenToFlowPosition` (not the dead `project()`).
12. Wrap custom edge paths with `<BaseEdge>` for free selection + events.
13. Single duplicate install of `@xyflow/react` will break the Zustand store (error #002).
14. The wrapper `<div>` around `<ReactFlow>` MUST have explicit `width`/`height` (error #005).

---

## 7. When to reach for Pro vs roll-your-own

- **Reach for Pro** if you need: collaborative editing, undo/redo, copy/paste, expand/collapse trees, helper lines, force layout, dynamic grouping, freehand drawing, server-side image export, or a starter workflow editor — and time-to-ship matters more than €129+/mo.
- **Roll your own (OSS only)** if: you're prototyping, your editor is single-user with simple state, you have time/expertise to implement undo/copy-paste/layout yourself, or you're allergic to subscriptions. The OSS surface is feature-complete for building most flow editors — Pro accelerates the "everyone re-implements this" patterns.
