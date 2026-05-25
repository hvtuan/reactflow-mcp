"""React Flow recipes — OSS implementations of Pro-paid example patterns.

Each recipe is a self-contained, copy-paste-ready code pattern that an LLM
can serve to a user as an alternative to subscribing to React Flow Pro.
Targets `@xyflow/react` v12 / React 18+.

Recipe shape:
    {
      "name": str,                # slug, snake_case
      "title": str,
      "category": str,            # "layout" | "interaction" | "history" | "edges" | "nodes" | "grouping" | "misc"
      "clones_pro": str | None,   # name of the Pro example this replaces
      "summary": str,             # 1-line
      "problem": str,             # what the user needs to solve
      "approach": str,            # high-level strategy
      "apis_used": list[str],     # @xyflow/react symbols (queryable via reactflow_get_api)
      "deps": list[str],          # npm packages required (besides @xyflow/react)
      "files": dict[str, str],    # filename → TSX/TS source
      "gotchas": list[str],       # subtle pitfalls
      "references": list[str],    # URLs to deeper docs / examples
    }
"""

from __future__ import annotations

RECIPES: dict[str, dict] = {

    # ──────────────────────── layout ────────────────────────

    "auto_layout_dagre": {
        "title": "Auto-layout with dagre",
        "category": "layout",
        "clones_pro": "Auto Layout",
        "summary": "Hierarchical (top-down / left-right) auto-layout that recomputes positions after nodes change.",
        "problem": "Nodes spawn at arbitrary positions and overlap. After add/remove you want a clean tree-like arrangement.",
        "approach": "Build a dagre graph mirroring your nodes/edges, run dagre.layout(), map results back to node positions. Gate on `useNodesInitialized` so node `measured.width/height` are available.",
        "apis_used": ["useReactFlow", "useNodesInitialized", "Position"],
        "deps": ["@dagrejs/dagre"],
        "files": {
            "useAutoLayout.ts": """\
import { useEffect } from 'react';
import { useReactFlow, useNodesInitialized, Position, type Node, type Edge } from '@xyflow/react';
import dagre from '@dagrejs/dagre';   // maintained fork; legacy `dagre` is unmaintained

const NODE_W = 180;
const NODE_H = 40;

export function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction: 'TB' | 'LR' = 'TB',
): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: direction, nodesep: 40, ranksep: 80 });

  const isHorizontal = direction === 'LR';
  nodes.forEach((n) => {
    g.setNode(n.id, {
      width: n.measured?.width ?? NODE_W,
      height: n.measured?.height ?? NODE_H,
    });
  });
  edges.forEach((e) => g.setEdge(e.source, e.target));

  dagre.layout(g);

  const laidOut = nodes.map((n) => {
    const { x, y } = g.node(n.id);
    return {
      ...n,
      targetPosition: isHorizontal ? Position.Left : Position.Top,
      sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
      position: { x: x - (n.measured?.width ?? NODE_W) / 2, y: y - (n.measured?.height ?? NODE_H) / 2 },
    };
  });

  return { nodes: laidOut, edges };
}

export function useAutoLayout(direction: 'TB' | 'LR' = 'TB') {
  const { getNodes, getEdges, setNodes, fitView } = useReactFlow();
  const initialized = useNodesInitialized();

  useEffect(() => {
    if (!initialized) return;
    const { nodes } = getLayoutedElements(getNodes(), getEdges(), direction);
    setNodes(nodes);
    // give React a tick to flush, then fit
    requestAnimationFrame(() => fitView({ padding: 0.2 }));
  }, [initialized, direction, getNodes, getEdges, setNodes, fitView]);
}
""",
            "App.tsx.snippet": """\
function Flow() {
  useAutoLayout('TB');   // call inside <ReactFlowProvider>
  return (
    <ReactFlow nodes={nodes} edges={edges} onNodesChange={...} onEdgesChange={...} fitView>
      <Background />
      <Controls />
    </ReactFlow>
  );
}

export default function App() {
  return <ReactFlowProvider><Flow /></ReactFlowProvider>;
}
""",
        },
        "gotchas": [
            "Must call `useAutoLayout` inside `<ReactFlowProvider>`.",
            "v12: read measured dims via `node.measured?.width` — NOT `node.width` (which sets inline style).",
            "Layout runs only once per `initialized` flip. Re-run manually after add/remove by calling getLayoutedElements yourself + setNodes.",
            "Dagre origin is the node center; you must offset by w/2, h/2.",
        ],
        "references": [
            "https://reactflow.dev/examples/layout/dagre",
            "https://reactflow.dev/learn/layouting/layouting",
            "https://github.com/dagrejs/dagre/wiki",
        ],
    },

    "auto_layout_elkjs": {
        "title": "Auto-layout with elkjs",
        "category": "layout",
        "clones_pro": "Auto Layout (elk variant)",
        "summary": "Async, much more configurable than dagre — supports radial, layered with port constraints, etc.",
        "problem": "Need a layout algorithm beyond what dagre offers (e.g., layered with edge routing, mrtree, radial).",
        "approach": "Same shape as dagre but elkjs is async. Build ELK graph, await elk.layout(), map results.",
        "apis_used": ["useReactFlow", "useNodesInitialized"],
        "deps": ["elkjs"],
        "files": {
            "useElkLayout.ts": """\
import { useEffect } from 'react';
import { useReactFlow, useNodesInitialized, type Node, type Edge } from '@xyflow/react';
import ELK, { type ElkNode } from 'elkjs/lib/elk.bundled.js';

const elk = new ELK();

const layoutOptions = {
  'elk.algorithm': 'layered',
  'elk.direction': 'DOWN',
  'elk.spacing.nodeNode': '40',
  'elk.layered.spacing.nodeNodeBetweenLayers': '80',
};

export async function elkLayout(nodes: Node[], edges: Edge[]): Promise<Node[]> {
  const graph: ElkNode = {
    id: 'root',
    layoutOptions,
    children: nodes.map((n) => ({
      id: n.id,
      width: n.measured?.width ?? 180,
      height: n.measured?.height ?? 40,
    })),
    edges: edges.map((e) => ({ id: e.id, sources: [e.source], targets: [e.target] })),
  };

  const laidOut = await elk.layout(graph);
  return nodes.map((n) => {
    const r = laidOut.children?.find((c) => c.id === n.id);
    return r ? { ...n, position: { x: r.x ?? 0, y: r.y ?? 0 } } : n;
  });
}

export function useElkLayout() {
  const { getNodes, getEdges, setNodes, fitView } = useReactFlow();
  const initialized = useNodesInitialized();
  useEffect(() => {
    if (!initialized) return;
    elkLayout(getNodes(), getEdges()).then((nodes) => {
      setNodes(nodes);
      requestAnimationFrame(() => fitView({ padding: 0.2 }));
    });
  }, [initialized, getNodes, getEdges, setNodes, fitView]);
}
""",
        },
        "gotchas": [
            "elk.layout() is async — handle with .then or await; useEffect can't be async directly.",
            "Use `elkjs/lib/elk.bundled.js` import for browser bundling (Webpack/Vite friendly).",
            "Layout options use string values even for numbers ('40' not 40).",
        ],
        "references": [
            "https://eclipse.dev/elk/reference/options.html",
            "https://github.com/kieler/elkjs",
        ],
    },

    "force_layout": {
        "title": "Force-directed layout (d3-force)",
        "category": "layout",
        "clones_pro": "Force Layout",
        "summary": "Physics-based positioning with collision detection that prevents overlap.",
        "problem": "Want organic graph-like arrangement instead of tree, with nodes that push each other apart.",
        "approach": "d3-force simulation tick → setNodes via useReactFlow. Use custom rectangular collision force (default d3 collision assumes circles).",
        "apis_used": ["useReactFlow", "useNodesInitialized"],
        "deps": ["d3-force"],
        "files": {
            "useForceLayout.ts": """\
import { useEffect, useRef } from 'react';
import { useReactFlow, useNodesInitialized, type Node, type Edge } from '@xyflow/react';
import {
  forceSimulation, forceManyBody, forceLink, forceCenter, forceCollide,
  type SimulationNodeDatum,
} from 'd3-force';

type SimNode = SimulationNodeDatum & { id: string; w: number; h: number };

export function useForceLayout(running: boolean = true) {
  const { getNodes, getEdges, setNodes } = useReactFlow();
  const initialized = useNodesInitialized();
  const rafRef = useRef<number>();

  useEffect(() => {
    if (!initialized || !running) return;
    const nodes = getNodes();
    const edges = getEdges();
    const simNodes: SimNode[] = nodes.map((n) => ({
      id: n.id,
      x: n.position.x,
      y: n.position.y,
      w: n.measured?.width ?? 150,
      h: n.measured?.height ?? 40,
    }));
    const simLinks = edges.map((e) => ({ source: e.source, target: e.target }));

    const sim = forceSimulation(simNodes)
      .force('link', forceLink(simLinks).id((d: any) => d.id).distance(120))
      .force('charge', forceManyBody().strength(-300))
      .force('center', forceCenter(0, 0))
      .force('collide', forceCollide<SimNode>().radius((d) => Math.hypot(d.w, d.h) / 2 + 10));

    const tick = () => {
      setNodes((prev) =>
        prev.map((n) => {
          const s = simNodes.find((x) => x.id === n.id);
          return s ? { ...n, position: { x: s.x ?? 0, y: s.y ?? 0 } } : n;
        }),
      );
      if (sim.alpha() > 0.01) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      sim.stop();
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [initialized, running, getNodes, getEdges, setNodes]);
}
""",
        },
        "gotchas": [
            "Default d3 collision is circular — `Math.hypot(w, h)/2` is a coarse rectangular approximation; for tight rects implement a real AABB collision.",
            "Don't run force layout while user is dragging — listen to onNodeDragStart/Stop to pause/resume.",
            "Large graphs (>200 nodes): throttle setNodes to every Nth tick to avoid React update floods.",
        ],
        "references": ["https://d3js.org/d3-force"],
    },

    # ──────────────────────── history ────────────────────────

    "undo_redo": {
        "title": "Undo / redo",
        "category": "history",
        "clones_pro": "Undo and Redo",
        "summary": "History stack capturing node + edge snapshots on each user change.",
        "problem": "User wants Cmd/Ctrl+Z / Shift+Cmd/Ctrl+Z to undo/redo node moves, adds, deletes, connections.",
        "approach": "Wrap setNodes/setEdges in a hook that pushes pre-state onto an undo stack. Listen to onNodesChange/onEdgesChange — record snapshot before applying. Use useKeyPress for shortcuts.",
        "apis_used": ["useReactFlow", "useKeyPress", "applyNodeChanges", "applyEdgeChanges"],
        "deps": [],
        "files": {
            "useUndoRedo.ts": """\
import { useCallback, useRef } from 'react';
import { useReactFlow, useKeyPress, type Node, type Edge } from '@xyflow/react';

type Snapshot = { nodes: Node[]; edges: Edge[] };
const MAX_HISTORY = 100;

export function useUndoRedo() {
  const { getNodes, getEdges, setNodes, setEdges } = useReactFlow();
  const past = useRef<Snapshot[]>([]);
  const future = useRef<Snapshot[]>([]);

  const takeSnapshot = useCallback(() => {
    past.current.push({ nodes: getNodes(), edges: getEdges() });
    if (past.current.length > MAX_HISTORY) past.current.shift();
    future.current = [];   // new action → clear redo stack
  }, [getNodes, getEdges]);

  const undo = useCallback(() => {
    const prev = past.current.pop();
    if (!prev) return;
    future.current.push({ nodes: getNodes(), edges: getEdges() });
    setNodes(prev.nodes);
    setEdges(prev.edges);
  }, [getNodes, getEdges, setNodes, setEdges]);

  const redo = useCallback(() => {
    const next = future.current.pop();
    if (!next) return;
    past.current.push({ nodes: getNodes(), edges: getEdges() });
    setNodes(next.nodes);
    setEdges(next.edges);
  }, [getNodes, getEdges, setNodes, setEdges]);

  const undoKey = useKeyPress(['Meta+z', 'Control+z']);
  const redoKey = useKeyPress(['Meta+Shift+z', 'Control+Shift+z', 'Meta+y', 'Control+y']);
  if (undoKey) undo();
  if (redoKey) redo();

  return { takeSnapshot, undo, redo, canUndo: past.current.length > 0, canRedo: future.current.length > 0 };
}
""",
            "usage.snippet": """\
function Flow() {
  const { takeSnapshot } = useUndoRedo();
  return (
    <ReactFlow
      nodes={nodes} edges={edges}
      onNodeDragStart={takeSnapshot}
      onSelectionDragStart={takeSnapshot}
      onNodesDelete={takeSnapshot}
      onEdgesDelete={takeSnapshot}
      onConnect={(c) => { takeSnapshot(); setEdges((es) => addEdge(c, es)); }}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
    />
  );
}
""",
        },
        "gotchas": [
            "Don't snapshot inside onNodesChange (fires per pixel of drag — would flood history). Snapshot on drag START + delete + connect.",
            "useKeyPress hooks must be at top level — calling undo/redo conditionally on the boolean is intentional and ok per React rules.",
            "If state is in Zustand, replace setNodes/setEdges with store setters and snapshot via store actions.",
        ],
        "references": [],
    },

    # ──────────────────────── interaction ────────────────────────

    "copy_paste": {
        "title": "Copy / paste with keyboard shortcuts",
        "category": "interaction",
        "clones_pro": "Copy and Paste",
        "summary": "Cmd/Ctrl+C copies selected nodes (+ edges between them); Cmd/Ctrl+V pastes at cursor offset.",
        "problem": "Need standard editor-style duplication of selected nodes preserving relative positions + internal edges.",
        "approach": "On copy, capture selected node ids → store nodes + filtered edges in ref. On paste, generate new ids, offset positions, append to flow.",
        "apis_used": ["useReactFlow", "useKeyPress", "useOnSelectionChange"],
        "deps": [],
        "files": {
            "useCopyPaste.ts": """\
import { useCallback, useRef } from 'react';
import { useReactFlow, useKeyPress, useOnSelectionChange, type Node, type Edge } from '@xyflow/react';

const OFFSET = { x: 40, y: 40 };

export function useCopyPaste() {
  const { addNodes, addEdges, getNodes, getEdges } = useReactFlow();
  const clipboard = useRef<{ nodes: Node[]; edges: Edge[] } | null>(null);
  const selectedIds = useRef<Set<string>>(new Set());

  useOnSelectionChange({
    onChange: useCallback(({ nodes }) => {
      selectedIds.current = new Set(nodes.map((n) => n.id));
    }, []),
  });

  const copy = useCallback(() => {
    const ids = selectedIds.current;
    if (ids.size === 0) return;
    const nodes = getNodes().filter((n) => ids.has(n.id));
    const edges = getEdges().filter((e) => ids.has(e.source) && ids.has(e.target));
    clipboard.current = { nodes, edges };
  }, [getNodes, getEdges]);

  const paste = useCallback(() => {
    if (!clipboard.current) return;
    const idMap = new Map<string, string>();
    const now = Date.now();
    const newNodes: Node[] = clipboard.current.nodes.map((n, i) => {
      const newId = `${n.id}-copy-${now}-${i}`;
      idMap.set(n.id, newId);
      return {
        ...n,
        id: newId,
        position: { x: n.position.x + OFFSET.x, y: n.position.y + OFFSET.y },
        selected: true,
      };
    });
    const newEdges: Edge[] = clipboard.current.edges.map((e, i) => ({
      ...e,
      id: `${e.id}-copy-${now}-${i}`,
      source: idMap.get(e.source)!,
      target: idMap.get(e.target)!,
    }));
    addNodes(newNodes);
    addEdges(newEdges);
  }, [addNodes, addEdges]);

  if (useKeyPress(['Meta+c', 'Control+c'])) copy();
  if (useKeyPress(['Meta+v', 'Control+v'])) paste();
}
""",
        },
        "gotchas": [
            "Default useKeyPress fires while pressed — useKeyPress is *reactive*, fires once per press transition. Don't wrap in useEffect or you'll multi-fire.",
            "Must rewrite edges with NEW source/target ids — naive copy leaves them pointing at the original nodes.",
            "If user has focused inputs (custom node editing), skip paste to avoid hijacking text paste. Use `actInsideInputWithModifier` option of useKeyPress.",
        ],
        "references": [],
    },

    "helper_lines": {
        "title": "Helper lines (alignment guides)",
        "category": "interaction",
        "clones_pro": "Helper Lines",
        "summary": "Figma-style snap guides that appear during node drag when sides/centers align with other nodes.",
        "problem": "User dragging a node should see horizontal/vertical guides when it aligns with another node's edge or center; node should snap to that line.",
        "approach": "Custom NodeChange handler: when type='position', compute candidate snap offsets against all other nodes' positions (left/center/right × top/middle/bottom). Apply small snap if within threshold; render guides as absolute-positioned <div>s in a <Panel>.",
        "apis_used": ["NodeChange", "applyNodeChanges", "Panel", "useStore"],
        "deps": [],
        "files": {
            "helperLines.ts": """\
import type { Node, NodePositionChange, XYPosition } from '@xyflow/react';

const SNAP_THRESHOLD = 5;

export type HelperLines = {
  horizontal: number | undefined;
  vertical: number | undefined;
};

/**
 * Given a position change for `target`, scan other nodes for aligned edges/centers
 * and (a) return the snapped position, (b) return the guide line positions to render.
 */
export function getHelperLines(
  change: NodePositionChange,
  nodes: Node[],
): HelperLines & { snap: XYPosition } {
  const target = nodes.find((n) => n.id === change.id);
  if (!target || !change.position) return { horizontal: undefined, vertical: undefined, snap: change.position ?? { x: 0, y: 0 } };

  const tw = target.measured?.width ?? 0;
  const th = target.measured?.height ?? 0;
  const targetLefts = [change.position.x, change.position.x + tw / 2, change.position.x + tw];
  const targetTops = [change.position.y, change.position.y + th / 2, change.position.y + th];

  let snapX = change.position.x;
  let snapY = change.position.y;
  let vertical: number | undefined;
  let horizontal: number | undefined;
  let bestDx = SNAP_THRESHOLD;
  let bestDy = SNAP_THRESHOLD;

  for (const n of nodes) {
    if (n.id === target.id) continue;
    const w = n.measured?.width ?? 0;
    const h = n.measured?.height ?? 0;
    const otherLefts = [n.position.x, n.position.x + w / 2, n.position.x + w];
    const otherTops = [n.position.y, n.position.y + h / 2, n.position.y + h];

    for (let i = 0; i < 3; i++) {
      for (let j = 0; j < 3; j++) {
        const dx = Math.abs(targetLefts[i] - otherLefts[j]);
        if (dx < bestDx) {
          bestDx = dx;
          snapX = otherLefts[j] - [0, tw / 2, tw][i];
          vertical = otherLefts[j];
        }
        const dy = Math.abs(targetTops[i] - otherTops[j]);
        if (dy < bestDy) {
          bestDy = dy;
          snapY = otherTops[j] - [0, th / 2, th][i];
          horizontal = otherTops[j];
        }
      }
    }
  }

  return { horizontal, vertical, snap: { x: snapX, y: snapY } };
}
""",
            "App.tsx.snippet": """\
import { useState, useCallback } from 'react';
import { ReactFlow, applyNodeChanges, Panel, useReactFlow } from '@xyflow/react';
import { getHelperLines, type HelperLines } from './helperLines';

function Flow() {
  const [nodes, setNodes] = useState(initialNodes);
  const [lines, setLines] = useState<HelperLines>({ horizontal: undefined, vertical: undefined });

  const onNodesChange = useCallback((changes) => {
    let newLines: HelperLines = { horizontal: undefined, vertical: undefined };
    const patched = changes.map((c) => {
      if (c.type === 'position' && c.dragging && c.position) {
        const { horizontal, vertical, snap } = getHelperLines(c, nodes);
        newLines = { horizontal, vertical };
        return { ...c, position: snap };
      }
      return c;
    });
    setLines(newLines);
    setNodes((ns) => applyNodeChanges(patched, ns));
  }, [nodes]);

  return (
    <ReactFlow nodes={nodes} onNodesChange={onNodesChange}>
      <Panel position="top-left" style={{ pointerEvents: 'none' }}>
        {lines.vertical !== undefined && (
          <div style={{ position: 'fixed', top: 0, bottom: 0, left: lines.vertical, width: 1, background: '#3b82f6' }} />
        )}
        {lines.horizontal !== undefined && (
          <div style={{ position: 'fixed', left: 0, right: 0, top: lines.horizontal, height: 1, background: '#3b82f6' }} />
        )}
      </Panel>
    </ReactFlow>
  );
}
""",
        },
        "gotchas": [
            "Guide line coordinates are in FLOW space — to render as fixed lines you'd want screen space. Use `useReactFlow().flowToScreenPosition` to convert before placing the line divs (sketch above uses fixed for simplicity).",
            "Only mutate change.position when dragging=true to avoid snapping during animations.",
            "9 alignment combinations (3 × 3) is the minimum — match left-to-left, center-to-center, right-to-right horizontally + top/middle/bottom vertically.",
        ],
        "references": [],
    },

    "node_position_animation": {
        "title": "Animated node position transitions",
        "category": "interaction",
        "clones_pro": "Node Position Animation",
        "summary": "Smooth tween (300ms ease) when a node moves programmatically — e.g., after auto-layout.",
        "problem": "Setting node.position abruptly snaps the node; want an animated transition. CSS transitions don't work here because React Flow re-applies inline transform every render.",
        "approach": "Wrap nodes in a `useAnimatedNodes(targetNodes, {duration})` hook. On each new target, kick a `d3-timer` that interpolates each node's position from previous → target per-frame, calling setAnimatedNodes each tick. Pass the animated array (not source) to `<ReactFlow>`.",
        "apis_used": ["Node"],
        "deps": ["d3-timer"],
        "files": {
            "useAnimatedNodes.ts": """\
import { useEffect, useRef, useState } from 'react';
import { timer } from 'd3-timer';
import type { Node, XYPosition } from '@xyflow/react';

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t);

/**
 * Returns a version of `nodes` whose positions are animated from their
 * previous values to the targets over `duration` ms.
 * Drop into `<ReactFlow nodes={animated} … />`.
 */
export function useAnimatedNodes(nodes: Node[], duration = 300): Node[] {
  const [animated, setAnimated] = useState<Node[]>(nodes);
  const prevById = useRef<Record<string, XYPosition>>({});

  useEffect(() => {
    const fromMap = { ...prevById.current };
    const targets = nodes.map((n) => ({ id: n.id, target: n.position, from: fromMap[n.id] ?? n.position }));

    const t = timer((elapsed) => {
      const k = Math.min(1, elapsed / duration);
      const eased = easeInOut(k);
      setAnimated((current) =>
        nodes.map((n) => {
          const tt = targets.find((x) => x.id === n.id)!;
          return {
            ...n,
            position: {
              x: lerp(tt.from.x, tt.target.x, eased),
              y: lerp(tt.from.y, tt.target.y, eased),
            },
          };
        }),
      );
      if (k === 1) t.stop();
    });

    // record target as previous for the NEXT change
    prevById.current = Object.fromEntries(nodes.map((n) => [n.id, n.position]));

    return () => t.stop();
  }, [nodes, duration]);

  return animated;
}
""",
            "usage.snippet": """\
function Flow() {
  const [nodes, setNodes] = useNodesState(initialNodes);
  const animated = useAnimatedNodes(nodes, 350);
  return <ReactFlow nodes={animated} onNodesChange={onNodesChange} …/>;
}
""",
        },
        "gotchas": [
            "CSS `transition: transform` on `.react-flow__node` does NOT work — React Flow imperatively sets transform each render, transitions get overwritten.",
            "During user drag, skip animation: bypass `useAnimatedNodes` (or detect `dragging` and pass through) so drag is direct, not lagged.",
            "On unmount or rapid successive changes, cancel the d3-timer (the hook's cleanup does this).",
        ],
        "references": [
            "https://github.com/xyflow/xyflow/discussions/2995",
        ],
    },

    # ──────────────────────── nodes / grouping ────────────────────────

    "expand_collapse": {
        "title": "Expand / collapse subtree",
        "category": "nodes",
        "clones_pro": "Expand and Collapse",
        "summary": "Toggle a node to hide/show its entire descendant subtree (and connecting edges).",
        "problem": "Tree flows get huge; want to collapse branches behind a toggle in the parent node.",
        "approach": "Mark each node with `hidden: bool` based on a Set of collapsed-parent ids. Walk down from each collapsed parent and hide descendants + their edges.",
        "apis_used": ["Node.hidden", "Edge.hidden", "useReactFlow"],
        "deps": [],
        "files": {
            "useExpandCollapse.ts": """\
import { useMemo } from 'react';
import type { Node, Edge } from '@xyflow/react';

export function getDescendants(rootId: string, edges: Edge[]): Set<string> {
  const out = new Set<string>();
  const stack = [rootId];
  while (stack.length) {
    const id = stack.pop()!;
    for (const e of edges) {
      if (e.source === id && !out.has(e.target)) {
        out.add(e.target);
        stack.push(e.target);
      }
    }
  }
  return out;
}

export function applyCollapse(nodes: Node[], edges: Edge[], collapsed: Set<string>) {
  const hidden = new Set<string>();
  for (const cid of collapsed) {
    for (const d of getDescendants(cid, edges)) hidden.add(d);
  }
  return {
    nodes: nodes.map((n) => ({ ...n, hidden: hidden.has(n.id) })),
    edges: edges.map((e) => ({ ...e, hidden: hidden.has(e.source) || hidden.has(e.target) })),
  };
}
""",
            "ToggleNode.tsx.snippet": """\
function GroupNode({ id, data }: NodeProps) {
  const { setNodes, setEdges, getNodes, getEdges } = useReactFlow();
  const toggle = () => {
    const collapsed = new Set<string>(data.collapsed ?? []);
    collapsed.has(id) ? collapsed.delete(id) : collapsed.add(id);
    const out = applyCollapse(getNodes(), getEdges(), collapsed);
    setNodes(out.nodes.map((n) => n.id === id ? { ...n, data: { ...n.data, collapsed: [...collapsed] } } : n));
    setEdges(out.edges);
  };
  return (
    <div className="rounded border px-3 py-2 bg-white">
      <button onClick={toggle}>{data.collapsed?.includes(id) ? '+' : '−'}</button> {data.label}
      <Handle type="source" position={Position.Bottom} />
      <Handle type="target" position={Position.Top} />
    </div>
  );
}
""",
        },
        "gotchas": [
            "Track the `collapsed` set in app-level state (or in one root node's data), not per-node — otherwise you can't undo collapse without losing the set.",
            "Hidden edges still occupy graph topology — auto-layout will still compute around them unless you filter beforehand.",
            "For very deep trees, memoize getDescendants with a graph adjacency map.",
        ],
        "references": [],
    },

    "selection_grouping": {
        "title": "Selection grouping (group selected nodes under a parent)",
        "category": "grouping",
        "clones_pro": "Selection Grouping",
        "summary": "Press shortcut → wrap currently selected nodes in a new group-type parent node with `parentId`.",
        "problem": "User box-selects a few nodes; wants to wrap them in a labeled container that moves together.",
        "approach": "On shortcut: compute bounding rect of selection, create a `group` node at that rect, then setNodes to reparent each selected node (set `parentId`, convert positions to relative).",
        "apis_used": ["useReactFlow", "useKeyPress", "getNodesBounds"],
        "deps": [],
        "files": {
            "useGroupSelected.ts": """\
import { useCallback } from 'react';
import { useReactFlow, useKeyPress, getNodesBounds, type Node } from '@xyflow/react';

const PADDING = 20;

export function useGroupSelected() {
  const { getNodes, setNodes, addNodes } = useReactFlow();

  const group = useCallback(() => {
    const selected = getNodes().filter((n) => n.selected && !n.parentId);
    if (selected.length < 2) return;
    const bounds = getNodesBounds(selected);
    const groupId = `group-${Date.now()}`;
    const groupNode: Node = {
      id: groupId,
      type: 'group',
      position: { x: bounds.x - PADDING, y: bounds.y - PADDING },
      data: { label: 'Group' },
      style: { width: bounds.width + 2 * PADDING, height: bounds.height + 2 * PADDING },
    };
    // parent MUST come before children in the array
    const newNodes = [
      groupNode,
      ...selected.map((n) => ({
        ...n,
        parentId: groupId,
        extent: 'parent' as const,
        position: { x: n.position.x - (bounds.x - PADDING), y: n.position.y - (bounds.y - PADDING) },
      })),
    ];
    const rest = getNodes().filter((n) => !selected.some((s) => s.id === n.id));
    setNodes([...rest.slice(0, 0), ...newNodes, ...rest]);  // group inserted before its children
    addNodes([]);  // noop to nudge re-render
  }, [getNodes, setNodes, addNodes]);

  if (useKeyPress(['Meta+g', 'Control+g'])) group();
}
""",
        },
        "gotchas": [
            "v12 REQUIRES parent before child in the nodes array. Re-insertion order matters.",
            "Child position becomes RELATIVE to parent top-left after reparenting — must subtract parent.position from each child.",
            "Setting `extent:'parent'` clamps child drag inside parent bounds.",
            "Use `parentId` (v12) not `parentNode` (v11).",
        ],
        "references": [
            "https://reactflow.dev/learn/layouting/sub-flows",
        ],
    },

    "shapes_node": {
        "title": "SVG flowchart shapes node",
        "category": "nodes",
        "clones_pro": "Shapes",
        "summary": "Custom node that renders as a diamond, ellipse, hexagon, or cylinder with handles on shape edges.",
        "problem": "Default rectangular nodes feel like wireframe — want classic flowchart shapes (decision diamond, terminal ellipse, etc.).",
        "approach": "Custom node renders an inline SVG `<path>` filling the bbox; absolute-positioned `<Handle>`s anchored to shape extremes.",
        "apis_used": ["NodeProps", "Handle", "Position", "NodeResizer"],
        "deps": [],
        "files": {
            "ShapeNode.tsx": """\
import { Handle, Position, NodeResizer, type NodeProps } from '@xyflow/react';

type Shape = 'diamond' | 'ellipse' | 'hexagon' | 'cylinder' | 'parallelogram';
type Data = { shape: Shape; label: string };

const shapePath = (shape: Shape, w: number, h: number): string => {
  switch (shape) {
    case 'diamond':
      return `M ${w/2} 0 L ${w} ${h/2} L ${w/2} ${h} L 0 ${h/2} Z`;
    case 'ellipse':
      return `M 0 ${h/2} A ${w/2} ${h/2} 0 1 0 ${w} ${h/2} A ${w/2} ${h/2} 0 1 0 0 ${h/2} Z`;
    case 'hexagon': {
      const x = w * 0.25;
      return `M ${x} 0 L ${w-x} 0 L ${w} ${h/2} L ${w-x} ${h} L ${x} ${h} L 0 ${h/2} Z`;
    }
    case 'cylinder': {
      const e = h * 0.15;
      return `M 0 ${e} A ${w/2} ${e} 0 1 1 ${w} ${e} L ${w} ${h-e} A ${w/2} ${e} 0 1 1 0 ${h-e} Z`;
    }
    case 'parallelogram': {
      const skew = w * 0.15;
      return `M ${skew} 0 L ${w} 0 L ${w-skew} ${h} L 0 ${h} Z`;
    }
  }
};

export function ShapeNode({ data, selected, width = 160, height = 80 }: NodeProps<{ data: Data }>) {
  return (
    <div style={{ position: 'relative', width, height }}>
      <NodeResizer isVisible={selected} minWidth={80} minHeight={50} />
      <svg width={width} height={height} style={{ overflow: 'visible' }}>
        <path
          d={shapePath(data.shape, width, height)}
          fill="white"
          stroke={selected ? '#3b82f6' : '#94a3b8'}
          strokeWidth={2}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0, display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        fontSize: 13, pointerEvents: 'none',
      }}>{data.label}</div>
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
""",
        },
        "gotchas": [
            "Handles position to bbox corners regardless of shape — for diamond they'll sit at the points, for ellipse they'll appear inside the curve. Customize per-shape if precise edge attachment matters.",
            "SVG `overflow: visible` lets resizer chrome bleed outside the shape — required for the resize handles to be grabbable.",
        ],
        "references": [],
    },

    # ──────────────────────── edges ────────────────────────

    "editable_edge": {
        "title": "Editable edge with draggable control points",
        "category": "edges",
        "clones_pro": "Editable Edge",
        "summary": "Custom bezier edge whose midpoint control(s) are draggable to reshape the curve.",
        "problem": "Default bezier is auto-curved; want to manually route an edge by dragging its control points like in Figma/draw.io.",
        "approach": "Store control points in `edge.data.controls`. Render path through control points via SVG `<path d='M ... C ... S ...'>`. Render draggable `<EdgeLabelRenderer>` HTML circles at control point positions; on drag, call useReactFlow().setEdges to update data.",
        "apis_used": ["EdgeProps", "BaseEdge", "EdgeLabelRenderer", "useReactFlow"],
        "deps": [],
        "files": {
            "EditableEdge.tsx": """\
import { useCallback, useMemo, useRef } from 'react';
import {
  BaseEdge, EdgeLabelRenderer, useReactFlow,
  type EdgeProps,
} from '@xyflow/react';

type Point = { x: number; y: number };
type Data = { controls?: Point[] };

const buildPath = (start: Point, end: Point, controls: Point[]): string => {
  const pts = [start, ...controls, end];
  if (pts.length === 2) return `M ${pts[0].x} ${pts[0].y} L ${pts[1].x} ${pts[1].y}`;
  let d = `M ${pts[0].x} ${pts[0].y}`;
  for (let i = 1; i < pts.length; i++) {
    const p = pts[i];
    const cp = pts[i - 1];
    d += ` Q ${cp.x} ${cp.y} ${(cp.x + p.x) / 2} ${(cp.y + p.y) / 2}`;
  }
  d += ` T ${pts[pts.length - 1].x} ${pts[pts.length - 1].y}`;
  return d;
};

export function EditableEdge({
  id, sourceX, sourceY, targetX, targetY, data, markerEnd,
}: EdgeProps<{ data: Data }>) {
  const { setEdges, screenToFlowPosition } = useReactFlow();
  const controls = useMemo(() => data?.controls ?? [{
    x: (sourceX + targetX) / 2, y: (sourceY + targetY) / 2,
  }], [data, sourceX, sourceY, targetX, targetY]);

  const d = buildPath({ x: sourceX, y: sourceY }, { x: targetX, y: targetY }, controls);

  const dragRef = useRef<number | null>(null);
  const onPointerDown = (idx: number) => (e: React.PointerEvent) => {
    dragRef.current = idx;
    (e.target as Element).setPointerCapture(e.pointerId);
  };
  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (dragRef.current === null) return;
    const flow = screenToFlowPosition({ x: e.clientX, y: e.clientY });
    setEdges((es) => es.map((edge) => {
      if (edge.id !== id) return edge;
      const next = [...(edge.data?.controls ?? [])];
      next[dragRef.current!] = flow;
      return { ...edge, data: { ...edge.data, controls: next } };
    }));
  }, [id, setEdges, screenToFlowPosition]);
  const onPointerUp = () => { dragRef.current = null; };

  return (
    <>
      <BaseEdge id={id} path={d} markerEnd={markerEnd} />
      <EdgeLabelRenderer>
        {controls.map((p, i) => (
          <div key={i}
            onPointerDown={onPointerDown(i)}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            className="nodrag nopan"
            style={{
              position: 'absolute',
              transform: `translate(-50%,-50%) translate(${p.x}px, ${p.y}px)`,
              pointerEvents: 'all', cursor: 'grab',
              width: 12, height: 12, borderRadius: 6,
              background: '#3b82f6', border: '2px solid white',
            }}
          />
        ))}
      </EdgeLabelRenderer>
    </>
  );
}
""",
        },
        "gotchas": [
            "Control points are in FLOW coords; convert pointer events with `screenToFlowPosition` before storing.",
            "Add `nodrag nopan` class + `pointerEvents:'all'` to control handle div — without these, drag pans the canvas.",
            "If you want multiple control points, surface an 'add point' UI (e.g., double-click on path) — start with 1 control midpoint for simplicity.",
        ],
        "references": [],
    },

    # ──────────────────────── misc ────────────────────────

    "server_side_image": {
        "title": "Server-side flow → PNG/SVG export",
        "category": "misc",
        "clones_pro": "Server-Side Image Creation",
        "summary": "Backend renders a flow JSON to a PNG/SVG without spinning up a browser.",
        "problem": "Need to email a flow snapshot, generate OG images, batch-export — can't run a headless browser per request.",
        "approach": "Use `getNodesBounds` + `getViewportForBounds` (SSR-safe utils from @xyflow/react) plus `renderToStaticMarkup` to produce an SVG string. Convert to PNG with sharp / resvg-js on Node.",
        "apis_used": ["getNodesBounds", "getViewportForBounds", "ReactFlowProvider", "ReactFlow"],
        "deps": ["react-dom/server", "@resvg/resvg-js"],
        "files": {
            "render.ts": """\
import { renderToStaticMarkup } from 'react-dom/server';
import {
  ReactFlow, ReactFlowProvider, Background,
  getNodesBounds, getViewportForBounds,
  type Node, type Edge,
} from '@xyflow/react';
import { Resvg } from '@resvg/resvg-js';

export async function flowToPng(nodes: Node[], edges: Edge[], width = 1200, height = 800): Promise<Buffer> {
  // Nodes need explicit width/height for SSR.
  const sized = nodes.map((n) => ({ ...n, width: n.width ?? 180, height: n.height ?? 40 }));
  const bounds = getNodesBounds(sized);
  const viewport = getViewportForBounds(bounds, width, height, 0.1, 2, 0.1);

  const svg = renderToStaticMarkup(
    <ReactFlowProvider initialNodes={sized} initialEdges={edges} initialWidth={width} initialHeight={height} fitView>
      <ReactFlow nodes={sized} edges={edges} viewport={viewport} width={width} height={height}>
        <Background />
      </ReactFlow>
    </ReactFlowProvider>
  );
  // renderToStaticMarkup returns HTML; for true SVG, render <svg> with the flow inside, or use react-flow's html-to-image approach offline.

  const resvg = new Resvg(svg, { fitTo: { mode: 'width', value: width } });
  return resvg.render().asPng();
}
""",
        },
        "gotchas": [
            "Each node MUST have `width` and `height` set numerically (or `initialWidth/initialHeight`) — without measured DOM, RF can't lay out otherwise.",
            "Edges require pre-computed handle positions for SSR; if you use the default centered handles, set `node.handles` explicitly or hand-render edges from `getBezierPath` for full control.",
            "For 100% fidelity, use puppeteer or playwright headless and screenshot — but only if your infra can run Chromium.",
        ],
        "references": [
            "https://reactflow.dev/learn/advanced-use/ssr-ssg-configuration",
        ],
    },

    "remove_attribution": {
        "title": "Remove attribution badge",
        "category": "misc",
        "clones_pro": "Remove Attribution",
        "summary": "Hide the bottom-right 'React Flow' badge.",
        "problem": "Want a clean canvas without the corner attribution.",
        "approach": "Pass `proOptions={{ hideAttribution: true }}` on `<ReactFlow>`. Technically anyone can — it's a moral/funding ask, not enforced.",
        "apis_used": ["ProOptions"],
        "deps": [],
        "files": {
            "snippet.tsx": """\
<ReactFlow
  nodes={nodes} edges={edges}
  proOptions={{ hideAttribution: true }}
>
  …
</ReactFlow>
""",
        },
        "gotchas": [
            "For commercial use the xyflow team requests you either keep the badge or subscribe to React Flow Pro / sponsor on GitHub to fund OSS maintenance.",
        ],
        "references": [
            "https://reactflow.dev/learn/troubleshooting/remove-attribution",
        ],
    },
}


def list_recipes(category: str | None = None) -> list[dict]:
    """Return slim index of recipes, optionally filtered by category."""
    items = []
    for name, r in RECIPES.items():
        if category and r["category"] != category:
            continue
        items.append({
            "name": name,
            "title": r["title"],
            "category": r["category"],
            "clones_pro": r.get("clones_pro"),
            "summary": r["summary"],
            "deps": r.get("deps", []),
            "files": list(r.get("files", {}).keys()),
        })
    return items


def get_recipe(name: str) -> dict | None:
    if name in RECIPES:
        return {"name": name, **RECIPES[name]}
    lower = name.lower()
    for k, r in RECIPES.items():
        if k.lower() == lower:
            return {"name": k, **r}
    return None
