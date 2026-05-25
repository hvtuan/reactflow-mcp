from reactflow_mcp.data.migration import BEHAVIOR_CHANGES, PACKAGE_MIGRATION, SYMBOL_MIGRATION, lookup


def test_package_migration_exists():
    assert "reactflow" in PACKAGE_MIGRATION
    assert PACKAGE_MIGRATION["reactflow"]["replacement"] == "@xyflow/react"


def test_known_renames():
    assert lookup("parentNode")["replacement"] == "parentId"
    assert lookup("xPos")["replacement"] == "positionAbsoluteX"
    assert lookup("yPos")["replacement"] == "positionAbsoluteY"
    assert lookup("onEdgeUpdate")["replacement"] == "onReconnect"
    assert lookup("edgesUpdatable")["replacement"] == "edgesReconnectable"
    assert lookup("project")["replacement"] == "screenToFlowPosition"
    assert lookup("nodeInternals")["replacement"] == "nodeLookup"
    assert lookup("useHandleConnections")["replacement"] == "useNodeConnections"


def test_node_field_dotted_paths():
    assert lookup("node.width")["replacement"] == "node.measured.width"
    assert lookup("node.height")["replacement"] == "node.measured.height"


def test_case_insensitive():
    assert lookup("ParentNode")["replacement"] == "parentId"
    assert lookup("PARENTNODE")["replacement"] == "parentId"


def test_unknown_returns_none():
    assert lookup("unknownSymbol") is None


def test_behavior_changes_present():
    assert len(BEHAVIOR_CHANGES) > 0
    for bc in BEHAVIOR_CHANGES:
        assert "topic" in bc and "change" in bc


def test_all_migrations_have_replacement():
    for sym, entry in SYMBOL_MIGRATION.items():
        assert "replacement" in entry, f"{sym} missing replacement"
        assert "kind" in entry, f"{sym} missing kind"
