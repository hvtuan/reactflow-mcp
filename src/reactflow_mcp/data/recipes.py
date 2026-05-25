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

    "collaborative_yjs": {
        "title": "Collaborative editing (Yjs)",
        "category": "interaction",
        "clones_pro": "Collaborative",
        "summary": "Real-time multi-user flow editing — shared nodes/edges via Yjs CRDT + presence cursors via awareness.",
        "problem": "Multiple users edit the same flow simultaneously; need conflict-free merge + see each other's cursors.",
        "approach": "Mirror Y.Array<Y.Map> ↔ React Flow state. On local change → write to Y. On Y observe → setNodes/setEdges. Use y-websocket (self-host) or y-webrtc. Awareness API broadcasts ephemeral cursor positions.",
        "apis_used": ["useReactFlow", "useOnSelectionChange", "Panel"],
        "deps": ["yjs", "y-websocket", "y-protocols"],
        "files": {
            "useYflow.ts": """\
import { useEffect, useState } from 'react';
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import type { Node, Edge } from '@xyflow/react';

const doc = new Y.Doc();
export const provider = new WebsocketProvider(
  import.meta.env.VITE_YJS_URL ?? 'ws://localhost:1234',
  'reactflow-room',
  doc,
);

const yNodes = doc.getArray<Y.Map<any>>('nodes');
const yEdges = doc.getArray<Y.Map<any>>('edges');

function yMapToObject<T>(m: Y.Map<any>): T {
  const o: any = {};
  m.forEach((v, k) => (o[k] = v instanceof Y.Map ? yMapToObject(v) : v));
  return o as T;
}

function objectToYMap(o: any): Y.Map<any> {
  const m = new Y.Map();
  for (const [k, v] of Object.entries(o)) {
    m.set(k, v && typeof v === 'object' && !Array.isArray(v) ? objectToYMap(v) : v);
  }
  return m;
}

export function useSharedFlow(): {
  nodes: Node[]; edges: Edge[];
  setNodes: (ns: Node[]) => void; setEdges: (es: Edge[]) => void;
} {
  const [nodes, setNodes] = useState<Node[]>(() => yNodes.toArray().map((m) => yMapToObject<Node>(m)));
  const [edges, setEdges] = useState<Edge[]>(() => yEdges.toArray().map((m) => yMapToObject<Edge>(m)));

  useEffect(() => {
    const onNodes = () => setNodes(yNodes.toArray().map((m) => yMapToObject<Node>(m)));
    const onEdges = () => setEdges(yEdges.toArray().map((m) => yMapToObject<Edge>(m)));
    yNodes.observeDeep(onNodes);
    yEdges.observeDeep(onEdges);
    return () => {
      yNodes.unobserveDeep(onNodes);
      yEdges.unobserveDeep(onEdges);
    };
  }, []);

  const writeNodes = (next: Node[]) => {
    doc.transact(() => {
      yNodes.delete(0, yNodes.length);
      yNodes.push(next.map(objectToYMap));
    });
  };
  const writeEdges = (next: Edge[]) => {
    doc.transact(() => {
      yEdges.delete(0, yEdges.length);
      yEdges.push(next.map(objectToYMap));
    });
  };

  return { nodes, edges, setNodes: writeNodes, setEdges: writeEdges };
}
""",
            "Cursors.tsx": """\
import { useEffect, useState } from 'react';
import { useReactFlow } from '@xyflow/react';
import { provider } from './useYflow';

type Cursor = { clientId: number; user: { name: string; color: string }; x: number; y: number };

export function Cursors() {
  const { flowToScreenPosition } = useReactFlow();
  const [cursors, setCursors] = useState<Cursor[]>([]);

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      provider.awareness.setLocalStateField('cursor', { x: e.clientX, y: e.clientY });
    };
    window.addEventListener('pointermove', onMove);

    const update = () => {
      const states = Array.from(provider.awareness.getStates().entries());
      setCursors(states
        .filter(([id]) => id !== provider.awareness.clientID)
        .map(([clientId, s]: any) => ({ clientId, ...s.cursor, user: s.user ?? { name: 'anon', color: '#888' } }))
        .filter((c) => typeof c.x === 'number'),
      );
    };
    provider.awareness.on('change', update);
    update();
    return () => {
      window.removeEventListener('pointermove', onMove);
      provider.awareness.off('change', update);
    };
  }, []);

  return (
    <>
      {cursors.map((c) => (
        <div key={c.clientId} style={{
          position: 'fixed', left: c.x, top: c.y, pointerEvents: 'none', zIndex: 9999,
          transform: 'translate(2px, 2px)',
        }}>
          <svg width="12" height="18" viewBox="0 0 12 18"><path d="M0 0 L0 14 L4 11 L7 17 L9 16 L6 10 L11 10 Z" fill={c.user.color} stroke="white" /></svg>
          <div style={{ background: c.user.color, color: 'white', fontSize: 10, padding: '2px 6px', borderRadius: 4, marginTop: 2 }}>{c.user.name}</div>
        </div>
      ))}
    </>
  );
}
""",
            "App.tsx.snippet": """\
function Flow() {
  const { nodes, edges, setNodes, setEdges } = useSharedFlow();
  // ... wire onNodesChange / onEdgesChange / onConnect to setNodes/setEdges
  return (
    <>
      <ReactFlow nodes={nodes} edges={edges} onNodesChange={...}>
        <Background /><Controls />
      </ReactFlow>
      <Cursors />
    </>
  );
}
""",
        },
        "gotchas": [
            "Self-host y-websocket: `npx y-websocket` for dev, or run `y-websocket-server` in production (Docker image exists). Persist to disk with `--persist`.",
            "DON'T sync ephemeral fields (`selected`, `dragging`, `measured`) — they flap and create huge undo histories. Filter before writing to Y.",
            "Awareness state is per-tab. Set unique color + name on connect (e.g. via Liveblocks-style randomColor()).",
            "For large flows: switch from `yNodes.delete + push` (full sync) to per-node Y.Map updates to avoid O(n) writes per change.",
        ],
        "references": [
            "https://docs.yjs.dev/",
            "https://github.com/yjs/y-websocket",
        ],
    },

    "libavoid_orthogonal_routing": {
        "title": "Orthogonal edge routing (libavoid)",
        "category": "edges",
        "clones_pro": "libavoid Edge Routing",
        "summary": "Smart orthogonal/right-angle edge routing that avoids node overlaps — like draw.io / lucidchart connectors.",
        "problem": "smoothstep edges go through other nodes when graph is dense; need true obstacle-avoiding orthogonal paths.",
        "approach": "Use `libavoid-js` (WASM port of Adaptagrams libavoid). Build a Router, register each node as a ShapeRef, register each edge as a ConnRef with endpoint connection-pins, call router.processTransaction(). Convert resulting checkpoint list back to SVG path. Custom edge component renders that path via <BaseEdge>.",
        "apis_used": ["BaseEdge", "EdgeProps", "useReactFlow", "useNodesInitialized"],
        "deps": ["libavoid-js"],
        "files": {
            "useLibavoidRouter.ts": """\
import { useEffect, useRef } from 'react';
import { useReactFlow, useNodesInitialized, type Node, type Edge } from '@xyflow/react';
// @ts-expect-error libavoid-js has no bundled types
import { AvoidLib } from 'libavoid-js';

type Path = { id: string; d: string };

const routes = new Map<string, string>();
let router: any = null;
let Avoid: any = null;

async function ensureAvoid() {
  if (Avoid) return Avoid;
  await AvoidLib.load();
  Avoid = AvoidLib.getInstance();
  router = new Avoid.Router(Avoid.OrthogonalRouting);
  router.setRoutingParameter(Avoid.idealNudgingDistance, 10);
  return Avoid;
}

export async function reroute(nodes: Node[], edges: Edge[]): Promise<Path[]> {
  await ensureAvoid();
  // Clear previous transaction state
  for (const obj of router.objectsByID.values()) router.deleteObject(obj);

  const shapes = new Map<string, any>();
  for (const n of nodes) {
    const w = n.measured?.width ?? 150;
    const h = n.measured?.height ?? 40;
    const rect = new Avoid.Rectangle(
      new Avoid.Point(n.position.x, n.position.y),
      new Avoid.Point(n.position.x + w, n.position.y + h),
    );
    const shape = new Avoid.ShapeRef(router, rect);
    shapes.set(n.id, { shape, w, h, pos: n.position });
  }

  const conns: any[] = [];
  for (const e of edges) {
    const s = shapes.get(e.source), t = shapes.get(e.target);
    if (!s || !t) continue;
    const srcPin = new Avoid.ConnEnd(
      new Avoid.Point(s.pos.x + s.w / 2, s.pos.y + s.h),
    );
    const tgtPin = new Avoid.ConnEnd(
      new Avoid.Point(t.pos.x + t.w / 2, t.pos.y),
    );
    const conn = new Avoid.ConnRef(router, srcPin, tgtPin);
    conns.push({ id: e.id, conn });
  }

  router.processTransaction();

  return conns.map(({ id, conn }) => {
    const route = conn.displayRoute();
    let d = '';
    for (let i = 0; i < route.size(); i++) {
      const p = route.get_ps(i);
      d += (i === 0 ? 'M ' : 'L ') + p.x + ' ' + p.y + ' ';
    }
    return { id, d: d.trim() };
  });
}

export function useLibavoidRouting() {
  const { getNodes, getEdges, setEdges } = useReactFlow();
  const initialized = useNodesInitialized();
  const dirty = useRef(0);

  useEffect(() => {
    if (!initialized) return;
    dirty.current++;
    const my = dirty.current;
    reroute(getNodes(), getEdges()).then((paths) => {
      if (my !== dirty.current) return;
      paths.forEach((p) => routes.set(p.id, p.d));
      setEdges((es) => es.map((e) => ({ ...e, data: { ...e.data, libavoidD: routes.get(e.id) } })));
    });
  }, [initialized, getNodes, getEdges, setEdges]);
}

export function getLibavoidPath(edgeId: string): string | undefined {
  return routes.get(edgeId);
}
""",
            "LibavoidEdge.tsx": """\
import { BaseEdge, type EdgeProps } from '@xyflow/react';
import { getLibavoidPath } from './useLibavoidRouter';

export function LibavoidEdge({ id, data, sourceX, sourceY, targetX, targetY, markerEnd }: EdgeProps<{ data?: { libavoidD?: string } }>) {
  const d = data?.libavoidD ?? `M ${sourceX} ${sourceY} L ${targetX} ${targetY}`;
  return <BaseEdge id={id} path={d} markerEnd={markerEnd} />;
}
""",
        },
        "gotchas": [
            "libavoid-js is a WASM bundle (~250kb gzipped) — load lazily; first call triggers WASM init.",
            "Re-run reroute() after every node move/add/delete (not just initial). Throttle to e.g. onNodeDragStop to avoid recompute per pixel.",
            "ConnEnd pin locations: choose top/bottom/left/right midpoints based on handle positions, not center, or routes will start inside nodes.",
            "Memory: libavoid objects must be deleted (router.deleteObject) between transactions or memory leaks per re-route.",
        ],
        "references": [
            "https://github.com/Aksem/libavoid-js",
            "https://www.adaptagrams.org/documentation/libavoid.html",
        ],
    },

    "dynamic_layouting": {
        "title": "Dynamic layouting with placeholder nodes",
        "category": "layout",
        "clones_pro": "Dynamic Layouting",
        "summary": "Vertical tree flow that auto-arranges around dashed 'placeholder' nodes — clicking a placeholder replaces it with a real node.",
        "problem": "Need a 'click + to add node here' UX where the placeholders show valid insertion points and the tree re-layouts on insert.",
        "approach": "Each real node has implicit `+` placeholder children at each empty handle. Render placeholders as dashed nodes (custom node type). On click, replace the placeholder with a real node + spawn new placeholders. Re-run dagre after each mutation.",
        "apis_used": ["useReactFlow", "useNodesInitialized", "useNodesState", "useEdgesState"],
        "deps": ["@dagrejs/dagre"],
        "files": {
            "PlaceholderNode.tsx": """\
import { Handle, Position, useReactFlow, type NodeProps } from '@xyflow/react';

export function PlaceholderNode({ id, data }: NodeProps<{ data: { parentId: string } }>) {
  const { setNodes, setEdges } = useReactFlow();
  const onClick = () => {
    const newId = `n-${Date.now()}`;
    setNodes((ns) => [
      ...ns.filter((n) => n.id !== id),
      { id: newId, type: 'default', position: { x: 0, y: 0 }, data: { label: 'New node' } },
      // spawn fresh placeholder under the new node
      { id: `${newId}-ph`, type: 'placeholder', position: { x: 0, y: 0 }, data: { parentId: newId } },
    ]);
    setEdges((es) => [
      ...es.filter((e) => e.target !== id),
      { id: `${data.parentId}-${newId}`, source: data.parentId, target: newId },
      { id: `${newId}-${newId}-ph`, source: newId, target: `${newId}-ph`, style: { strokeDasharray: '4 4' } },
    ]);
  };
  return (
    <div onClick={onClick} style={{
      width: 100, height: 30,
      border: '2px dashed #94a3b8', borderRadius: 6,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 18, color: '#64748b', cursor: 'pointer', background: 'white',
    }}>+
      <Handle type="target" position={Position.Top} />
    </div>
  );
}
""",
            "App.tsx.snippet": """\
import { useAutoLayout } from './useAutoLayout';   // from auto_layout_dagre recipe
import { PlaceholderNode } from './PlaceholderNode';

const nodeTypes = { placeholder: PlaceholderNode };
const initialNodes = [
  { id: 'root', type: 'input', position: { x: 0, y: 0 }, data: { label: 'Start' } },
  { id: 'root-ph', type: 'placeholder', position: { x: 0, y: 100 }, data: { parentId: 'root' } },
];
const initialEdges = [
  { id: 'root-ph-edge', source: 'root', target: 'root-ph', style: { strokeDasharray: '4 4' } },
];

function Flow() {
  useAutoLayout('TB');
  // ... standard useNodesState / useEdgesState wiring
}

export default function App() {
  return <ReactFlowProvider><Flow /></ReactFlowProvider>;
}
""",
        },
        "gotchas": [
            "Placeholder edges should be visually distinct (dashed). Easiest: `style={{ strokeDasharray: '4 4' }}` on the edge.",
            "Don't include placeholders in graph-export (toObject()) — filter by `n.type !== 'placeholder'` before serializing.",
            "After insert, re-layout runs via useAutoLayout's `useNodesInitialized` flip — but you may need to force re-run with a layout trigger ref if the dependency array doesn't re-fire.",
        ],
        "references": [],
    },

    "dynamic_grouping": {
        "title": "Dynamic grouping (drag-into-container)",
        "category": "grouping",
        "clones_pro": "Dynamic Grouping",
        "summary": "Drag a node into a group node and it auto-becomes a child (parentId set + position rebased); drag out and it detaches.",
        "problem": "Selection-grouping (shortcut) is fine but users also want intuitive drag-in / drag-out semantics like Figma frames.",
        "approach": "Listen `onNodeDragStop`. Use `getIntersectingNodes` to find the deepest group node the dragged node now overlaps. If different from current parent → reparent (rewrite parentId + relative position). If dragged outside any group → null parentId + absolute position.",
        "apis_used": ["useReactFlow", "getIntersectingNodes"],
        "deps": [],
        "files": {
            "useDragIntoGroup.ts": """\
import { useCallback } from 'react';
import { useReactFlow, type Node } from '@xyflow/react';

export function useDragIntoGroup() {
  const { getNodes, setNodes, getIntersectingNodes } = useReactFlow();

  return useCallback((_e: React.MouseEvent, dragged: Node) => {
    // exclude self + non-groups
    const overlaps = getIntersectingNodes(dragged).filter((n) => n.type === 'group' && n.id !== dragged.id);
    const newParent = overlaps[overlaps.length - 1];   // deepest = last in array
    const currentParentId = dragged.parentId ?? null;
    const targetParentId = newParent?.id ?? null;
    if (currentParentId === targetParentId) return;

    setNodes((ns) => {
      const oldParent = currentParentId ? ns.find((n) => n.id === currentParentId) : null;
      const next = ns.map((n) => {
        if (n.id !== dragged.id) return n;
        if (targetParentId && newParent) {
          // moving INTO group: convert absolute → relative
          const absX = (oldParent ? oldParent.position.x : 0) + dragged.position.x;
          const absY = (oldParent ? oldParent.position.y : 0) + dragged.position.y;
          return {
            ...n,
            parentId: targetParentId,
            extent: 'parent' as const,
            position: { x: absX - newParent.position.x, y: absY - newParent.position.y },
          };
        }
        // moving OUT of group: convert relative → absolute
        const absX = (oldParent ? oldParent.position.x : 0) + dragged.position.x;
        const absY = (oldParent ? oldParent.position.y : 0) + dragged.position.y;
        return { ...n, parentId: undefined, extent: undefined, position: { x: absX, y: absY } };
      });

      // re-sort to keep parents before children
      const groups = next.filter((n) => n.type === 'group');
      const others = next.filter((n) => n.type !== 'group');
      return [...groups, ...others];
    });
  }, [getNodes, setNodes, getIntersectingNodes]);
}
""",
            "App.tsx.snippet": """\
function Flow() {
  const onNodeDragStop = useDragIntoGroup();
  return <ReactFlow nodes={nodes} edges={edges} onNodeDragStop={onNodeDragStop} … />;
}
""",
        },
        "gotchas": [
            "getIntersectingNodes uses BBOX — for non-rect group shapes you need a custom hit test.",
            "After re-sorting (parents first), node order changes — pair with stable React keys (Node already has `id`).",
            "Don't allow nesting groups inside themselves (filter `n.id !== dragged.id` AND walk parentId chain to detect ancestor cycles).",
        ],
        "references": [],
    },

    "freehand_draw": {
        "title": "Freehand draw mode",
        "category": "interaction",
        "clones_pro": "Freehand Draw",
        "summary": "Toggle 'draw' mode in toolbar; pointer-drag on empty canvas creates a freehand-shape node (smoothed SVG path).",
        "problem": "Whiteboard-style annotation — want users to sketch arrows / circles / highlights directly on the canvas without dragging nodes.",
        "approach": "Mode state (draw vs select). In draw mode, `<ReactFlow panOnDrag={false}>` so canvas doesn't pan. On pointer down/move on the `<Pane>`, collect points. On up, smooth points (perfect-freehand or Catmull-Rom-to-Bezier) and create a custom 'freehand' node whose data is the path.",
        "apis_used": ["ReactFlow.panOnDrag", "useReactFlow", "Panel", "NodeProps", "Handle"],
        "deps": ["perfect-freehand"],
        "files": {
            "FreehandNode.tsx": """\
import { type NodeProps } from '@xyflow/react';
import { getStroke } from 'perfect-freehand';

type Data = { points: number[][]; color: string };

export function FreehandNode({ data, selected }: NodeProps<{ data: Data }>) {
  const stroke = getStroke(data.points, { size: 4, smoothing: 0.5, thinning: 0.5 });
  const d = stroke.length
    ? 'M ' + stroke.map(([x, y]) => `${x} ${y}`).join(' L ') + ' Z'
    : '';
  // bbox to set node width/height
  const xs = data.points.map((p) => p[0]);
  const ys = data.points.map((p) => p[1]);
  const minX = Math.min(...xs), minY = Math.min(...ys);
  const maxX = Math.max(...xs), maxY = Math.max(...ys);
  return (
    <svg
      width={maxX - minX} height={maxY - minY}
      viewBox={`${minX} ${minY} ${maxX - minX} ${maxY - minY}`}
      style={{ overflow: 'visible' }}
    >
      <path d={d} fill={data.color} stroke={selected ? '#3b82f6' : 'transparent'} strokeWidth={1} />
    </svg>
  );
}
""",
            "useDrawMode.ts": """\
import { useCallback, useRef, useState } from 'react';
import { useReactFlow, type Node } from '@xyflow/react';

export type Mode = 'select' | 'draw';

export function useDrawMode(initial: Mode = 'select') {
  const [mode, setMode] = useState<Mode>(initial);
  const { addNodes, screenToFlowPosition } = useReactFlow();
  const points = useRef<number[][]>([]);
  const drawing = useRef(false);

  const onPaneMouseDown = useCallback((e: React.PointerEvent) => {
    if (mode !== 'draw') return;
    drawing.current = true;
    points.current = [];
    const p = screenToFlowPosition({ x: e.clientX, y: e.clientY });
    points.current.push([p.x, p.y, e.pressure || 0.5]);
  }, [mode, screenToFlowPosition]);

  const onPaneMouseMove = useCallback((e: React.PointerEvent) => {
    if (!drawing.current) return;
    const p = screenToFlowPosition({ x: e.clientX, y: e.clientY });
    points.current.push([p.x, p.y, e.pressure || 0.5]);
  }, [screenToFlowPosition]);

  const onPaneMouseUp = useCallback(() => {
    if (!drawing.current || points.current.length < 3) {
      drawing.current = false;
      return;
    }
    drawing.current = false;
    const xs = points.current.map((p) => p[0]);
    const ys = points.current.map((p) => p[1]);
    const node: Node = {
      id: `draw-${Date.now()}`,
      type: 'freehand',
      position: { x: Math.min(...xs), y: Math.min(...ys) },
      data: { points: points.current.slice(), color: '#1e293b' },
      selectable: true,
    };
    addNodes([node]);
    points.current = [];
  }, [addNodes]);

  return { mode, setMode, onPaneMouseDown, onPaneMouseMove, onPaneMouseUp };
}
""",
            "App.tsx.snippet": """\
function Flow() {
  const draw = useDrawMode('select');
  return (
    <ReactFlow
      nodes={nodes} edges={edges}
      nodeTypes={{ freehand: FreehandNode }}
      panOnDrag={draw.mode === 'select'}
      onPaneMouseMove={draw.onPaneMouseMove}
      onPaneMouseUp={draw.onPaneMouseUp}
      // onPaneMouseDown is not a built-in prop — attach to wrapper div instead
    >
      <Panel position="top-left">
        <button onClick={() => draw.setMode(draw.mode === 'draw' ? 'select' : 'draw')}>
          {draw.mode === 'draw' ? '✎ drawing' : '☝ select'}
        </button>
      </Panel>
    </ReactFlow>
  );
}
""",
        },
        "gotchas": [
            "React Flow has no `onPaneMouseDown` — attach pointerdown to a wrapper div around <ReactFlow> instead.",
            "Toggle `panOnDrag={false}` while in draw mode so drag-on-pane doesn't pan the canvas.",
            "Convert ALL pointer coords with `screenToFlowPosition` — using raw clientX/Y drifts on pan/zoom.",
            "Freehand nodes interfere with edge connection drags. Either disable `connectable` on freehand nodes or render them BEHIND the rest (`zIndex: -1`).",
        ],
        "references": [
            "https://github.com/steveruizok/perfect-freehand",
        ],
    },

    "helper_lines_advanced": {
        "title": "Helper lines v2 (viewport-aware)",
        "category": "interaction",
        "clones_pro": "Helper Lines (advanced)",
        "summary": "Upgrade of the basic helper_lines recipe — lines render in the transformed viewport (pan/zoom correct) and threshold scales inversely with zoom.",
        "problem": "Basic helper_lines recipe renders guide lines at fixed screen coords — they drift when the user pans or zooms. Also snap threshold feels off at extreme zooms.",
        "approach": "Same snap math as helper_lines, but render guide lines inside `<ViewportPortal>` (which is part of the transformed flow space). Threshold = `SNAP_PX / zoom` so a 5px snap stays 5 screen pixels regardless of zoom.",
        "apis_used": ["NodeChange", "applyNodeChanges", "ViewportPortal", "useStore"],
        "deps": [],
        "files": {
            "helperLinesV2.ts": """\
import type { Node, NodePositionChange, XYPosition } from '@xyflow/react';

const SNAP_PX_SCREEN = 5;

export type HelperLines = { x: number | null; y: number | null };

export function getHelperLinesV2(
  change: NodePositionChange,
  nodes: Node[],
  zoom: number,
): { lines: HelperLines; snap: XYPosition } {
  const target = nodes.find((n) => n.id === change.id);
  if (!target || !change.position) return { lines: { x: null, y: null }, snap: change.position ?? { x: 0, y: 0 } };

  const threshold = SNAP_PX_SCREEN / zoom;   // flow-units that look like 5px on screen
  const tw = target.measured?.width ?? 0;
  const th = target.measured?.height ?? 0;
  const targetLefts = [change.position.x, change.position.x + tw / 2, change.position.x + tw];
  const targetTops = [change.position.y, change.position.y + th / 2, change.position.y + th];

  let snapX = change.position.x, snapY = change.position.y;
  let lineX: number | null = null, lineY: number | null = null;
  let bestDx = threshold, bestDy = threshold;

  for (const n of nodes) {
    if (n.id === target.id) continue;
    const w = n.measured?.width ?? 0;
    const h = n.measured?.height ?? 0;
    const otherLefts = [n.position.x, n.position.x + w / 2, n.position.x + w];
    const otherTops = [n.position.y, n.position.y + h / 2, n.position.y + h];
    for (let i = 0; i < 3; i++) {
      for (let j = 0; j < 3; j++) {
        const dx = Math.abs(targetLefts[i] - otherLefts[j]);
        if (dx < bestDx) { bestDx = dx; snapX = otherLefts[j] - [0, tw / 2, tw][i]; lineX = otherLefts[j]; }
        const dy = Math.abs(targetTops[i] - otherTops[j]);
        if (dy < bestDy) { bestDy = dy; snapY = otherTops[j] - [0, th / 2, th][i]; lineY = otherTops[j]; }
      }
    }
  }

  return { lines: { x: lineX, y: lineY }, snap: { x: snapX, y: snapY } };
}
""",
            "App.tsx.snippet": """\
import { ReactFlow, applyNodeChanges, ViewportPortal, useStore, useNodesState } from '@xyflow/react';
import { useState, useCallback } from 'react';
import { getHelperLinesV2 } from './helperLinesV2';

function Flow() {
  const [nodes, setNodes] = useNodesState(initialNodes);
  const [lines, setLines] = useState({ x: null, y: null });
  const zoom = useStore((s) => s.transform[2]);

  const onNodesChange = useCallback((changes) => {
    let next = { x: null, y: null };
    const patched = changes.map((c) => {
      if (c.type === 'position' && c.dragging && c.position) {
        const { lines, snap } = getHelperLinesV2(c, nodes, zoom);
        next = lines;
        return { ...c, position: snap };
      }
      return c;
    });
    setLines(next);
    setNodes((ns) => applyNodeChanges(patched, ns));
  }, [nodes, zoom]);

  return (
    <ReactFlow nodes={nodes} onNodesChange={onNodesChange} fitView>
      <ViewportPortal>
        {lines.x !== null && (
          <div style={{ position: 'absolute', left: lines.x, top: -100000, width: 1 / zoom, height: 200000, background: '#3b82f6' }} />
        )}
        {lines.y !== null && (
          <div style={{ position: 'absolute', top: lines.y, left: -100000, height: 1 / zoom, width: 200000, background: '#3b82f6' }} />
        )}
      </ViewportPortal>
    </ReactFlow>
  );
}
""",
        },
        "gotchas": [
            "Lines inside <ViewportPortal> are in FLOW coordinates — multiply width/height by `1/zoom` so they stay 1px on screen at any zoom.",
            "Use VERY large extents (`-100000` to `+100000`) for line length — viewport portal clips at flow bounds, not viewport bounds.",
            "Read zoom from useStore selector (`s.transform[2]`) — `useViewport().zoom` also works but causes more re-renders.",
            "Snap threshold scales by 1/zoom so 5 screen-pixels stays 5 screen-pixels regardless of zoom level.",
        ],
        "references": [],
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
            "The xyflow team treats this as a moral/funding ask, not a license obligation — `proOptions.hideAttribution: true` works for anyone. If you appreciate the OSS work, sponsor via GitHub Sponsors.",
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
