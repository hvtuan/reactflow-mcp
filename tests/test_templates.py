import pytest

from reactflow_mcp.templates import scaffold_workflow_app


def test_vite_default():
    r = scaffold_workflow_app()
    assert r["stack"] == "vite"
    assert "package.json" in r["files"]
    assert "vite.config.ts" in r["files"]
    assert "src/Flow.tsx" in r["files"]
    assert "src/store.ts" in r["files"]
    assert "src/Sidebar.tsx" in r["files"]
    assert "src/nodes/TaskNode.tsx" in r["files"]


def test_vite_no_sidebar():
    r = scaffold_workflow_app(with_sidebar=False)
    assert "src/Sidebar.tsx" not in r["files"]


def test_vite_with_ai():
    r = scaffold_workflow_app(with_ai=True)
    assert "src/AiPanel.tsx" in r["files"]
    assert "src/api/chat.example.md" in r["files"]
    assert "ai" in r["deps"]


def test_nextjs_with_ai_has_api_route():
    r = scaffold_workflow_app(stack="nextjs", with_ai=True)
    assert r["stack"] == "nextjs"
    assert "app/api/chat/route.ts" in r["files"]
    assert "next.config.js" in r["files"]
    assert "lib/store.ts" in r["files"]
    assert "components/Flow.tsx" in r["files"]


def test_persist_localstorage_uses_persist_middleware():
    r = scaffold_workflow_app(persist="localstorage")
    assert "import { persist } from 'zustand/middleware';" in r["files"]["src/store.ts"]


def test_persist_supabase_pulls_dep():
    r = scaffold_workflow_app(persist="supabase")
    assert "@supabase/supabase-js" in r["deps"]


def test_persist_none_no_middleware():
    r = scaffold_workflow_app(persist="none")
    assert "zustand/middleware" not in r["files"]["src/store.ts"]


def test_invalid_stack_rejected():
    with pytest.raises(ValueError, match="stack"):
        scaffold_workflow_app(stack="remix")


def test_invalid_name_rejected():
    with pytest.raises(ValueError, match="name"):
        scaffold_workflow_app(name="bad name with spaces")


def test_store_includes_undo_redo():
    r = scaffold_workflow_app()
    src = r["files"]["src/store.ts"]
    assert "undo:" in src and "redo:" in src and "takeSnapshot" in src


def test_task_node_uses_updateNodeData():
    r = scaffold_workflow_app()
    src = r["files"]["src/nodes/TaskNode.tsx"]
    assert "updateNodeData" in src
    assert "nodrag" in src   # input must not drag the node
