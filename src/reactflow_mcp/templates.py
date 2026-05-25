"""Full-app project templates that clone React Flow Pro paid templates.

Pro sells "Workflow Editor" + "AI Workflow Editor" starter projects to
subscribers. These are full Next.js applications; this module produces
equivalent OSS starters as multi-file project structures.

Returns a `files` dict mapping relative path → source content. Caller
materializes by writing each path under a fresh project directory.
"""

from __future__ import annotations

VALID_STACKS = {"vite", "nextjs"}
VALID_PERSIST = {"localstorage", "supabase", "none"}


def _vite_files(*, name: str, with_ai: bool, persist: str, with_sidebar: bool) -> dict[str, str]:
    deps_lines = [
        '    "@xyflow/react": "^12.10.0",',
        '    "react": "^18.3.1",',
        '    "react-dom": "^18.3.1",',
        '    "zustand": "^4.5.0",',
    ]
    if with_ai:
        deps_lines.append('    "ai": "^3.4.0",')
    if persist == "supabase":
        deps_lines.append('    "@supabase/supabase-js": "^2.45.0",')
    deps_block = "\n".join(deps_lines).rstrip(",")

    package_json = f"""{{
  "name": "{name}",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{
{deps_block}
  }},
  "devDependencies": {{
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.0",
    "vite": "^5.4.0"
  }}
}}
"""

    tsconfig = """{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "skipLibCheck": true,
    "noEmit": true,
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true
  },
  "include": ["src"]
}
"""

    vite_config = """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
});
"""

    index_html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{name}</title>
  </head>
  <body>
    <div id="root" style="width:100vw;height:100vh;margin:0"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""

    main_tsx = """import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import '@xyflow/react/dist/style.css';

createRoot(document.getElementById('root')!).render(<App />);
"""

    store_ts = _store_ts(persist=persist)
    flow_tsx = _flow_tsx(with_sidebar=with_sidebar)
    sidebar_tsx = _sidebar_tsx() if with_sidebar else None
    toolbar_tsx = _toolbar_tsx(persist=persist)
    custom_node_tsx = _custom_node_tsx()

    app_tsx = """import React from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { Flow } from './Flow';

export default function App() {
  return (
    <ReactFlowProvider>
      <div style={{ width: '100%', height: '100%', display: 'flex' }}>
        <Flow />
      </div>
    </ReactFlowProvider>
  );
}
"""

    files = {
        "package.json": package_json,
        "tsconfig.json": tsconfig,
        "vite.config.ts": vite_config,
        "index.html": index_html,
        "src/main.tsx": main_tsx,
        "src/App.tsx": app_tsx,
        "src/Flow.tsx": flow_tsx,
        "src/store.ts": store_ts,
        "src/Toolbar.tsx": toolbar_tsx,
        "src/nodes/TaskNode.tsx": custom_node_tsx,
    }
    if with_sidebar:
        files["src/Sidebar.tsx"] = sidebar_tsx
    if with_ai:
        files["src/AiPanel.tsx"] = _ai_panel_tsx()
        files["src/api/chat.example.md"] = _ai_backend_readme()
    return files


def _store_ts(*, persist: str) -> str:
    persist_imports = ""
    persist_setup = "  "
    persist_actions = ""
    if persist == "localstorage":
        persist_imports = "import { persist } from 'zustand/middleware';\n"
        persist_setup = """const useFlowStore = create<FlowState>()(
  persist(
    (set, get) => ({
"""
        persist_actions = """    }),
    { name: 'flow-state', partialize: (s) => ({ nodes: s.nodes, edges: s.edges }) },
  ),
);

export default useFlowStore;
"""
    elif persist == "supabase":
        persist_imports = "// import { createClient } from '@supabase/supabase-js';\n// const supabase = createClient(import.meta.env.VITE_SUPABASE_URL, import.meta.env.VITE_SUPABASE_ANON_KEY);\n"
        persist_setup = """const useFlowStore = create<FlowState>()((set, get) => ({
"""
        persist_actions = """}));

// TODO: hook save/load to Supabase table `flows` — see README for schema.

export default useFlowStore;
"""
    else:
        persist_setup = """const useFlowStore = create<FlowState>()((set, get) => ({
"""
        persist_actions = """}));

export default useFlowStore;
"""

    return f"""import {{ create }} from 'zustand';
{persist_imports}import {{
  type Node, type Edge, type Connection,
  type NodeChange, type EdgeChange,
  applyNodeChanges, applyEdgeChanges, addEdge,
}} from '@xyflow/react';

type Snapshot = {{ nodes: Node[]; edges: Edge[] }};

type FlowState = {{
  nodes: Node[];
  edges: Edge[];
  past: Snapshot[];
  future: Snapshot[];

  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  addNode: (node: Node) => void;
  takeSnapshot: () => void;
  undo: () => void;
  redo: () => void;
}};

const MAX_HISTORY = 100;

{persist_setup}      nodes: [
        {{ id: '1', type: 'task', position: {{ x: 100, y: 100 }}, data: {{ label: 'Start' }} }},
      ],
      edges: [],
      past: [],
      future: [],

      setNodes: (nodes) => set({{ nodes }}),
      setEdges: (edges) => set({{ edges }}),
      onNodesChange: (changes) => set({{ nodes: applyNodeChanges(changes, get().nodes) }}),
      onEdgesChange: (changes) => set({{ edges: applyEdgeChanges(changes, get().edges) }}),
      onConnect: (c) => set({{ edges: addEdge(c, get().edges) }}),
      addNode: (node) => {{
        get().takeSnapshot();
        set({{ nodes: [...get().nodes, node] }});
      }},
      takeSnapshot: () => set((s) => {{
        const next = [...s.past, {{ nodes: s.nodes, edges: s.edges }}];
        if (next.length > MAX_HISTORY) next.shift();
        return {{ past: next, future: [] }};
      }}),
      undo: () => set((s) => {{
        const prev = s.past[s.past.length - 1];
        if (!prev) return {{}};
        return {{
          past: s.past.slice(0, -1),
          future: [...s.future, {{ nodes: s.nodes, edges: s.edges }}],
          nodes: prev.nodes, edges: prev.edges,
        }};
      }}),
      redo: () => set((s) => {{
        const next = s.future[s.future.length - 1];
        if (!next) return {{}};
        return {{
          future: s.future.slice(0, -1),
          past: [...s.past, {{ nodes: s.nodes, edges: s.edges }}],
          nodes: next.nodes, edges: next.edges,
        }};
      }}),
{persist_actions}"""


def _flow_tsx(*, with_sidebar: bool) -> str:
    sidebar_import = "import { Sidebar } from './Sidebar';\n" if with_sidebar else ""
    sidebar_render = "      <Sidebar />\n" if with_sidebar else ""
    return f"""import React, {{ useCallback }} from 'react';
import {{
  ReactFlow, Background, Controls, MiniMap, useReactFlow,
}} from '@xyflow/react';
import useFlowStore from './store';
import {{ Toolbar }} from './Toolbar';
{sidebar_import}import {{ TaskNode }} from './nodes/TaskNode';

const nodeTypes = {{ task: TaskNode }};

export function Flow() {{
  const {{ nodes, edges, onNodesChange, onEdgesChange, onConnect, addNode, takeSnapshot }} = useFlowStore();
  const {{ screenToFlowPosition }} = useReactFlow();

  const onDrop = useCallback((event: React.DragEvent) => {{
    event.preventDefault();
    const type = event.dataTransfer.getData('application/reactflow');
    if (!type) return;
    const position = screenToFlowPosition({{ x: event.clientX, y: event.clientY }});
    addNode({{
      id: `n-${{Date.now()}}`,
      type,
      position,
      data: {{ label: type[0].toUpperCase() + type.slice(1) }},
    }});
  }}, [addNode, screenToFlowPosition]);

  const onDragOver = useCallback((event: React.DragEvent) => {{
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }}, []);

  return (
    <>
{sidebar_render}      <div style={{{{ flex: 1, height: '100%' }}}} onDrop={{onDrop}} onDragOver={{onDragOver}}>
        <ReactFlow
          nodes={{nodes}}
          edges={{edges}}
          onNodesChange={{onNodesChange}}
          onEdgesChange={{onEdgesChange}}
          onConnect={{onConnect}}
          onNodeDragStart={{takeSnapshot}}
          nodeTypes={{nodeTypes}}
          fitView
          colorMode="system"
        >
          <Background variant="dots" />
          <Controls />
          <MiniMap pannable zoomable />
          <Toolbar />
        </ReactFlow>
      </div>
    </>
  );
}}
"""


def _sidebar_tsx() -> str:
    return """import React from 'react';

const NODE_TYPES = [
  { type: 'task', label: 'Task' },
  { type: 'input', label: 'Input' },
  { type: 'output', label: 'Output' },
];

export function Sidebar() {
  const onDragStart = (event: React.DragEvent, type: string) => {
    event.dataTransfer.setData('application/reactflow', type);
    event.dataTransfer.effectAllowed = 'move';
  };
  return (
    <aside style={{ width: 180, padding: 12, borderRight: '1px solid #e5e7eb', background: '#fafafa' }}>
      <div style={{ fontWeight: 600, marginBottom: 12 }}>Drag to canvas</div>
      {NODE_TYPES.map((n) => (
        <div
          key={n.type}
          draggable
          onDragStart={(e) => onDragStart(e, n.type)}
          style={{
            padding: '8px 12px', marginBottom: 6, border: '1px solid #cbd5e1',
            borderRadius: 6, cursor: 'grab', background: 'white', fontSize: 13,
          }}
        >
          {n.label}
        </div>
      ))}
    </aside>
  );
}
"""


def _toolbar_tsx(*, persist: str) -> str:
    save_btn = ""
    if persist == "supabase":
        save_btn = """      <button onClick={() => console.warn('TODO: implement Supabase save in store.ts')}>💾 Save</button>
"""
    return f"""import React from 'react';
import {{ Panel, useReactFlow }} from '@xyflow/react';
import useFlowStore from './store';

export function Toolbar() {{
  const {{ undo, redo, past, future, nodes, edges }} = useFlowStore();
  const {{ fitView }} = useReactFlow();

  const exportJson = () => {{
    const blob = new Blob([JSON.stringify({{ nodes, edges }}, null, 2)], {{ type: 'application/json' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'flow.json'; a.click();
    URL.revokeObjectURL(url);
  }};

  return (
    <Panel position="top-right" style={{{{ display: 'flex', gap: 6 }}}}>
      <button onClick={{undo}} disabled={{past.length === 0}}>↶ Undo</button>
      <button onClick={{redo}} disabled={{future.length === 0}}>↷ Redo</button>
      <button onClick={{() => fitView({{ padding: 0.2 }})}}>⊡ Fit</button>
      <button onClick={{exportJson}}>⬇ Export</button>
{save_btn}    </Panel>
  );
}}
"""


def _custom_node_tsx() -> str:
    return """import React from 'react';
import { Handle, Position, useReactFlow, type NodeProps } from '@xyflow/react';

type TaskData = { label: string; status?: 'todo' | 'doing' | 'done' };

const STATUS_COLOR: Record<string, string> = {
  todo: '#94a3b8',
  doing: '#3b82f6',
  done: '#10b981',
};

export function TaskNode({ id, data, selected }: NodeProps<{ data: TaskData; type: 'task' }>) {
  const { updateNodeData } = useReactFlow();
  const status = data.status ?? 'todo';
  return (
    <div style={{
      minWidth: 160,
      padding: '8px 12px',
      borderRadius: 8,
      background: 'white',
      border: `2px solid ${selected ? '#3b82f6' : '#cbd5e1'}`,
      boxShadow: selected ? '0 0 0 3px rgba(59,130,246,0.15)' : '0 1px 2px rgba(0,0,0,0.06)',
    }}>
      <Handle type="target" position={Position.Top} />
      <input
        className="nodrag"
        value={data.label}
        onChange={(e) => updateNodeData(id, { label: e.target.value })}
        style={{ width: '100%', border: 'none', outline: 'none', fontSize: 13, background: 'transparent' }}
      />
      <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
        {(['todo', 'doing', 'done'] as const).map((s) => (
          <button
            key={s}
            className="nodrag"
            onClick={() => updateNodeData(id, { status: s })}
            style={{
              flex: 1, fontSize: 10, padding: '2px 4px',
              border: 'none', borderRadius: 4, cursor: 'pointer',
              background: status === s ? STATUS_COLOR[s] : '#f1f5f9',
              color: status === s ? 'white' : '#475569',
            }}
          >{s}</button>
        ))}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
"""


def _ai_panel_tsx() -> str:
    return """import React, { useState } from 'react';
import { useChat } from 'ai/react';
import { Panel, useReactFlow } from '@xyflow/react';
import useFlowStore from './store';

/**
 * AI-assisted flow editor side panel.
 * Uses Vercel AI SDK `useChat` against a /api/chat backend (see src/api/chat.example.md).
 * Sends current flow JSON as system context; expects the model to return either
 * natural language or a JSON patch the user can apply.
 */
export function AiPanel() {
  const { nodes, edges, setNodes, setEdges, takeSnapshot } = useFlowStore();
  const { fitView } = useReactFlow();
  const [open, setOpen] = useState(true);

  const { messages, input, handleInputChange, handleSubmit } = useChat({
    api: import.meta.env.VITE_CHAT_ENDPOINT ?? '/api/chat',
    body: { flow: { nodes, edges } },
  });

  const applyLastAsFlow = () => {
    const last = messages[messages.length - 1];
    if (!last || last.role !== 'assistant') return;
    try {
      const m = last.content.match(/```json\\s*({[\\s\\S]+?})\\s*```/);
      if (!m) return alert('No JSON block in last reply');
      const flow = JSON.parse(m[1]);
      takeSnapshot();
      setNodes(flow.nodes ?? []);
      setEdges(flow.edges ?? []);
      requestAnimationFrame(() => fitView({ padding: 0.2 }));
    } catch (e) {
      alert('Failed to parse flow JSON: ' + e);
    }
  };

  if (!open) {
    return (
      <Panel position="bottom-right">
        <button onClick={() => setOpen(true)}>🤖 AI</button>
      </Panel>
    );
  }

  return (
    <Panel position="bottom-right" style={{
      width: 340, height: 420, background: 'white', borderRadius: 8,
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)', display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ padding: 8, borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between' }}>
        <strong>AI assistant</strong>
        <button onClick={() => setOpen(false)}>×</button>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: 8 }}>
        {messages.map((m) => (
          <div key={m.id} style={{ marginBottom: 8, fontSize: 12 }}>
            <div style={{ color: m.role === 'user' ? '#3b82f6' : '#10b981', fontWeight: 600 }}>{m.role}</div>
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{m.content}</pre>
          </div>
        ))}
      </div>
      <form onSubmit={handleSubmit} style={{ padding: 8, borderTop: '1px solid #e5e7eb', display: 'flex', gap: 4 }}>
        <input
          value={input}
          onChange={handleInputChange}
          placeholder="Ask the model to modify the flow…"
          style={{ flex: 1, padding: 6, fontSize: 12 }}
        />
        <button type="submit">Send</button>
        <button type="button" onClick={applyLastAsFlow}>Apply</button>
      </form>
    </Panel>
  );
}
"""


def _ai_backend_readme() -> str:
    return """# AI chat backend

The `<AiPanel />` calls `/api/chat` (override with `VITE_CHAT_ENDPOINT`).
Vite doesn't ship API routes — host a small backend separately.

## Minimal Node/Express example

```ts
// server.ts (run separately, e.g. on port 3001)
import express from 'express';
import cors from 'cors';
import { streamText } from 'ai';
import { anthropic } from '@ai-sdk/anthropic';

const app = express();
app.use(cors());
app.use(express.json());

const SYSTEM = `You are a React Flow assistant. The user is editing a flow
diagram. Help them modify it. When suggesting a new flow state, output a
fenced \\`\\`\\`json block with shape {"nodes":[...], "edges":[...]}.`;

app.post('/api/chat', async (req, res) => {
  const { messages, flow } = req.body;
  const result = await streamText({
    model: anthropic('claude-sonnet-4-6'),
    system: SYSTEM,
    messages: [
      { role: 'system', content: `Current flow:\\n\\`\\`\\`json\\n${JSON.stringify(flow)}\\n\\`\\`\\`` },
      ...messages,
    ],
  });
  result.pipeDataStreamToResponse(res);
});

app.listen(3001);
```

Set `VITE_CHAT_ENDPOINT=http://localhost:3001/api/chat` in `.env.local`.

## Or use Next.js

If you don't want a separate server, rerun the scaffolder with
`stack='nextjs'` — the AI route ships in `app/api/chat/route.ts`.
"""


def _nextjs_files(*, name: str, with_ai: bool, persist: str, with_sidebar: bool) -> dict[str, str]:
    # Reuse vite component files where possible; differ in entry + API routes.
    vite_files = _vite_files(name=name, with_ai=False, persist=persist, with_sidebar=with_sidebar)
    files: dict[str, str] = {}

    files["package.json"] = f"""{{
  "name": "{name}",
  "private": true,
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  }},
  "dependencies": {{
    "next": "^15.0.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "@xyflow/react": "^12.10.0",
    "zustand": "^4.5.0"{',' if with_ai else ''}
{'    "ai": "^3.4.0",' if with_ai else ''}
{'    "@ai-sdk/anthropic": "^0.0.50"' if with_ai else ''}
  }},
  "devDependencies": {{
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@types/node": "^22.0.0",
    "typescript": "^5.5.0"
  }}
}}
"""

    files["next.config.js"] = "module.exports = { reactStrictMode: true };\n"
    files["tsconfig.json"] = vite_files["tsconfig.json"].replace('"include": ["src"]', '"include": ["app", "components", "lib"]')

    files["app/layout.tsx"] = """import '@xyflow/react/dist/style.css';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, height: '100vh', width: '100vw' }}>{children}</body>
    </html>
  );
}
"""
    files["app/page.tsx"] = """'use client';
import { ReactFlowProvider } from '@xyflow/react';
import { Flow } from '../components/Flow';

export default function Page() {
  return (
    <ReactFlowProvider>
      <div style={{ display: 'flex', height: '100%' }}>
        <Flow />
      </div>
    </ReactFlowProvider>
  );
}
"""

    # rebuild Flow.tsx with @/ aliases adjusted to relative paths
    files["components/Flow.tsx"] = vite_files["src/Flow.tsx"].replace("'./Toolbar'", "'./Toolbar'").replace("'./Sidebar'", "'./Sidebar'").replace("'./nodes/TaskNode'", "'./nodes/TaskNode'").replace("'./store'", "'../lib/store'")
    files["components/Toolbar.tsx"] = vite_files["src/Toolbar.tsx"].replace("'./store'", "'../lib/store'")
    if with_sidebar:
        files["components/Sidebar.tsx"] = vite_files["src/Sidebar.tsx"]
    files["components/nodes/TaskNode.tsx"] = vite_files["src/nodes/TaskNode.tsx"]
    files["lib/store.ts"] = vite_files["src/store.ts"]

    if with_ai:
        files["components/AiPanel.tsx"] = vite_files.get("src/AiPanel.tsx") or _ai_panel_tsx()
        files["app/api/chat/route.ts"] = """import { anthropic } from '@ai-sdk/anthropic';
import { streamText } from 'ai';

export const runtime = 'edge';

const SYSTEM = `You are a React Flow assistant. The user is editing a flow
diagram. Help them modify it. When suggesting a new flow state, output a
fenced \\`\\`\\`json block with shape {"nodes":[...], "edges":[...]}.`;

export async function POST(req: Request) {
  const { messages, flow } = await req.json();
  const result = await streamText({
    model: anthropic('claude-sonnet-4-6'),
    system: SYSTEM,
    messages: [
      { role: 'system', content: `Current flow:\\n\\`\\`\\`json\\n${JSON.stringify(flow)}\\n\\`\\`\\`` },
      ...messages,
    ],
  });
  return result.toDataStreamResponse();
}
"""

    return files


def scaffold_workflow_app(
    *,
    name: str = "my-workflow-editor",
    stack: str = "vite",
    with_ai: bool = False,
    persist: str = "localstorage",
    with_sidebar: bool = True,
) -> dict:
    """Generate a complete workflow-editor app project.

    Returns:
        {
          "name": str,
          "stack": "vite" | "nextjs",
          "files": {path: source},
          "deps": [str],          # npm packages used (informational)
          "next_steps": [str],
        }
    """
    if stack not in VALID_STACKS:
        raise ValueError(f"stack must be one of {sorted(VALID_STACKS)}")
    if persist not in VALID_PERSIST:
        raise ValueError(f"persist must be one of {sorted(VALID_PERSIST)}")
    if not name or "/" in name or " " in name:
        raise ValueError("name must be a safe directory name (no slashes/spaces)")

    if stack == "vite":
        files = _vite_files(name=name, with_ai=with_ai, persist=persist, with_sidebar=with_sidebar)
    else:
        files = _nextjs_files(name=name, with_ai=with_ai, persist=persist, with_sidebar=with_sidebar)

    deps = ["@xyflow/react", "react", "react-dom", "zustand"]
    if with_ai:
        deps += (["ai", "@ai-sdk/anthropic"] if stack == "nextjs" else ["ai"])
    if persist == "supabase":
        deps.append("@supabase/supabase-js")

    next_steps = [
        f"mkdir {name} && cd {name}",
        "Write each file from the `files` map at its given path.",
        "npm install",
        "npm run dev" + ("" if stack == "vite" else " (then open http://localhost:3000)"),
    ]
    if with_ai and stack == "vite":
        next_steps.append("Stand up a separate chat backend (see src/api/chat.example.md). Set VITE_CHAT_ENDPOINT.")
    if with_ai and stack == "nextjs":
        next_steps.append("export ANTHROPIC_API_KEY=… before npm run dev (or use any model the ai SDK supports).")
    if persist == "supabase":
        next_steps.append("Create a `flows` table in Supabase + wire src/store.ts save/load (TODO comments inside).")

    return {
        "name": name,
        "stack": stack,
        "files": files,
        "deps": deps,
        "next_steps": next_steps,
    }
