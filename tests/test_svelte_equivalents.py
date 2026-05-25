from reactflow_mcp.data.svelte_equivalents import IDENTICAL, RENAMED, SVELTE_ONLY, lookup


def test_renames_have_required_keys():
    assert "ReactFlow" in RENAMED
    assert RENAMED["ReactFlow"]["svelte"] == "SvelteFlow"
    assert RENAMED["useReactFlow"]["svelte"] == "useSvelteFlow"
    assert RENAMED["EdgeLabelRenderer"]["svelte"] == "EdgeLabel"
    assert RENAMED["ReactFlowProvider"]["svelte"] == "SvelteFlowProvider"


def test_renamed_status():
    r = lookup("ReactFlow")
    assert r["status"] == "renamed"
    assert r["svelte_symbol"] == "SvelteFlow"
    assert r["react_import"] == "@xyflow/react"
    assert r["svelte_import"] == "@xyflow/svelte"


def test_identical_status():
    r = lookup("Background")
    assert r["status"] == "identical"
    assert r["svelte_symbol"] == "Background"
    assert r["found"] is True


def test_identical_includes_common_symbols():
    expected = {"Background", "Handle", "Panel", "MiniMap", "addEdge", "useNodes", "useEdges", "getBezierPath", "Position"}
    assert expected <= IDENTICAL


def test_case_insensitive():
    assert lookup("reactflow")["svelte_symbol"] == "SvelteFlow"
    assert lookup("BACKGROUND")["svelte_symbol"] == "Background"


def test_svelte_only():
    assert "EdgeReconnectAnchor" in SVELTE_ONLY
    r = lookup("EdgeReconnectAnchor")
    assert r["status"] == "svelte_only"


def test_unknown_returns_suggestions():
    r = lookup("useReactRouterDom")
    assert r["found"] is False
    assert r["status"] == "unknown"
    assert "suggestions" in r
