from reactflow_mcp.prompts import (
    clone_pro_feature,
    migrate_v11_to_v12,
    pick_layout_algorithm,
    review_flow_spec,
)


def test_review_flow_spec_includes_validate_call():
    out = review_flow_spec('{"nodes":[],"edges":[]}')
    assert "reactflow_validate_flow" in out
    assert "reactflow_lookup_v11_v12" in out


def test_migrate_v11_to_v12_includes_lookup():
    out = migrate_v11_to_v12("import ReactFlow from 'reactflow'")
    assert "reactflow_lookup_v11_v12" in out
    assert "@xyflow/react" in out


def test_clone_pro_feature_carries_mission_statement():
    """Project mission: clone_pro_feature MUST tell the LLM not to recommend Pro."""
    out = clone_pro_feature("Auto Layout")
    assert "Don't recommend buying Pro" in out or "replace Pro" in out
    assert "reactflow_list_recipes" in out
    assert "reactflow_get_recipe" in out


def test_pick_layout_algorithm_branches_on_inputs():
    sparse_hier = pick_layout_algorithm(50, "sparse", "hierarchical")
    assert "dagre" in sparse_hier.lower()
    dense_organic = pick_layout_algorithm(80, "dense", "organic")
    assert "force" in dense_organic.lower()


def test_api_catalog_has_handler_types():
    """Tier A: callback/handler types must be in the catalog so LLMs can look them up."""
    from reactflow_mcp.data.api_catalog import API_CATALOG
    expected_types = {
        "OnConnect", "OnConnectStart", "OnConnectEnd",
        "OnNodesChange", "OnEdgesChange",
        "OnDelete", "OnBeforeDelete", "OnInit",
        "NodeMouseHandler", "EdgeMouseHandler",
        "ConnectionState", "ConnectionLineComponent",
        "ReactFlowInstance", "ReactFlowJsonObject",
        "NodeTypes", "EdgeTypes", "DefaultEdgeOptions",
        "EdgeMarker", "NodeHandle", "InternalNode",
        "XyPosition", "Rect", "CoordinateExtent", "NodeOrigin", "KeyCode",
    }
    missing = expected_types - set(API_CATALOG)
    assert not missing, f"Tier-A handler/type catalog gaps: {sorted(missing)}"
