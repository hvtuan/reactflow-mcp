import pytest

from reactflow_mcp.scaffolders import scaffold_custom_edge, scaffold_custom_node, scaffold_flow


# ─── node ───


def test_node_defaults():
    r = scaffold_custom_node(name="DefaultNode")
    assert r["component_name"] == "DefaultNode"
    assert r["type_name"] == "defaultNode"
    assert 'from "@xyflow/react"' in r["component"]
    assert "Handle" in r["component"]
    assert "Position.Left" in r["component"]
    assert "Position.Right" in r["component"]
    assert "nodeTypes" in r["registration"]


def test_node_pascalcase_normalization():
    r = scaffold_custom_node(name="my_node")
    assert r["component_name"] == "MyNode"
    assert any("normalized" in w for w in r["warnings"])


def test_node_with_data_fields():
    r = scaffold_custom_node(
        name="TextNode",
        data_fields=[{"name": "label", "type": "string", "default": "Hello"}],
        editable=True,
    )
    assert "TextNodeData" in r["component"]
    assert "label: string;" in r["component"]
    assert "updateNodeData" in r["component"]
    assert "label: 'Hello'" in r["usage"]


def test_node_with_resizer_and_toolbar():
    r = scaffold_custom_node(name="N", with_resizer=True, with_toolbar=True)
    assert "NodeResizer" in r["component"]
    assert "NodeToolbar" in r["component"]
    assert "deleteNode" in r["component"]


def test_node_handle_validation():
    with pytest.raises(ValueError, match="handle position"):
        scaffold_custom_node(name="N", handles=[{"kind": "source", "position": "diagonal"}])
    with pytest.raises(ValueError, match="handle kind"):
        scaffold_custom_node(name="N", handles=[{"kind": "spout", "position": "top"}])


def test_node_style_validation():
    with pytest.raises(ValueError, match="style"):
        scaffold_custom_node(name="N", style="comic-sans")


def test_node_editable_without_string_warns():
    r = scaffold_custom_node(name="N", data_fields=[{"name": "count", "type": "number"}], editable=True)
    assert any("no string-typed" in w for w in r["warnings"])


def test_node_inline_style():
    r = scaffold_custom_node(name="N", style="inline")
    assert "style={{" in r["component"]
    # The only className that may still appear in inline mode is the `nodrag` utility on inputs.
    for line in r["component"].splitlines():
        if "className=" in line:
            assert "nodrag" in line, f"unexpected className in inline-mode output: {line}"


def test_node_inline_style_editable_uses_inline_styles():
    r = scaffold_custom_node(
        name="N",
        style="inline",
        data_fields=[{"name": "label", "type": "string"}],
        editable=True,
    )
    # body field should use inline styles, not tailwind classes
    assert "flexDirection" in r["component"]
    assert "text-xs" not in r["component"]


# ─── edge ───


def test_edge_defaults():
    r = scaffold_custom_edge(name="MyEdge")
    assert r["component_name"] == "MyEdge"
    assert r["type_name"] == "myEdge"
    assert "BaseEdge" in r["component"]
    assert "getBezierPath" in r["component"]


def test_edge_path_types():
    r = scaffold_custom_edge(name="E", path_type="smoothstep")
    assert "getSmoothStepPath" in r["component"]

    r = scaffold_custom_edge(name="E", path_type="straight")
    assert "getStraightPath" in r["component"]

    r = scaffold_custom_edge(name="E", path_type="step")
    assert "borderRadius: 0" in r["component"]


def test_edge_delete_button_forces_renderer():
    r = scaffold_custom_edge(name="E", with_delete_button=True, with_label_renderer=False)
    assert "EdgeLabelRenderer" in r["component"]
    assert any("forces with_label_renderer" in w for w in r["warnings"])


def test_edge_label_with_renderer():
    r = scaffold_custom_edge(name="E", with_label=True, with_label_renderer=True)
    assert "EdgeLabelRenderer" in r["component"]
    assert "label" in r["component"]


def test_edge_path_type_validation():
    with pytest.raises(ValueError, match="path_type"):
        scaffold_custom_edge(name="E", path_type="zigzag")


# ─── full flow scaffolder ───


def test_flow_defaults():
    r = scaffold_flow()
    assert "@xyflow/react" in r["deps"]
    assert "import { ReactFlow" in r["app"]
    assert "initialNodes" in r["app"] and "initialEdges" in r["app"]
    assert "useNodesState" in r["app"]
    assert "<Background" in r["app"]
    assert "<Controls" in r["app"]
    assert "<MiniMap" in r["app"]


def test_flow_interactive_off():
    r = scaffold_flow(interactive=False)
    assert "useNodesState" not in r["app"]
    assert "defaultNodes" in r["app"]


def test_flow_layout_dagre_tb():
    r = scaffold_flow(layout="dagre-tb")
    assert "@dagrejs/dagre" in r["deps"]
    assert "ReactFlowProvider" in r["app"]
    assert "useNodesInitialized" in r["app"]
    assert "rankdir: 'TB'" in r["app"]


def test_flow_layout_dagre_lr():
    r = scaffold_flow(layout="dagre-lr")
    assert "rankdir: 'LR'" in r["app"]


def test_flow_no_chrome():
    r = scaffold_flow(with_minimap=False, with_controls=False, with_background=False)
    assert "<MiniMap" not in r["app"]
    assert "<Controls" not in r["app"]
    assert "<Background" not in r["app"]


def test_flow_validation_dup_node_id():
    with pytest.raises(ValueError, match="duplicate node id"):
        scaffold_flow(nodes=[{"id": "a"}, {"id": "a"}], edges=[])


def test_flow_validation_edge_unknown_target():
    with pytest.raises(ValueError, match="references unknown node"):
        scaffold_flow(
            nodes=[{"id": "a"}],
            edges=[{"source": "a", "target": "ghost"}],
        )


def test_flow_custom_node_type_warns():
    r = scaffold_flow(
        nodes=[{"id": "a", "type": "shape"}, {"id": "b"}],
        edges=[{"source": "a", "target": "b"}],
    )
    assert any("nodeTypes registration" in w for w in r["warnings"])


def test_flow_hide_attribution():
    r = scaffold_flow(hide_attribution=True)
    assert "proOptions" in r["app"]
    assert "hideAttribution" in r["app"]


def test_flow_color_mode_dark():
    r = scaffold_flow(color_mode="dark")
    assert 'colorMode="dark"' in r["app"]


def test_flow_layout_validation():
    with pytest.raises(ValueError, match="layout must be"):
        scaffold_flow(layout="quantum-fluid")
