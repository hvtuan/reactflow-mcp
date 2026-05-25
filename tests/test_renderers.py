from reactflow_mcp.renderers import explain_change, render_ascii, render_mermaid


def _sample():
    return {
        "nodes": [
            {"id": "a", "type": "input", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}},
            {"id": "b", "position": {"x": 0, "y": 100}, "data": {"label": "Middle"}},
            {"id": "c", "type": "output", "position": {"x": 0, "y": 200}, "data": {"label": "End"}},
        ],
        "edges": [
            {"id": "ab", "source": "a", "target": "b"},
            {"id": "bc", "source": "b", "target": "c", "label": "next", "animated": True},
        ],
    }


def test_mermaid_basic():
    out = render_mermaid(_sample())
    assert out.startswith("flowchart TB")
    assert 'a(["Start"])' in out
    assert 'c[/"End"/]' in out      # output → trapezoid
    assert "a --> b" in out
    assert "-.->|next|" in out      # animated edge


def test_mermaid_direction_lr():
    out = render_mermaid(_sample(), direction="LR")
    assert out.startswith("flowchart LR")


def test_mermaid_skips_hidden():
    flow = _sample()
    flow["nodes"][1]["hidden"] = True
    out = render_mermaid(flow)
    assert '"Middle"' not in out


def test_ascii_basic():
    out = render_ascii(_sample())
    assert "a: Start" in out
    assert "b: Middle" in out
    assert "c: End" in out
    # tree shape
    assert "└──" in out or "├──" in out or out.startswith("a")


def test_ascii_cycle_handled():
    flow = {
        "nodes": [{"id": "a", "position": {"x": 0, "y": 0}, "data": {}}, {"id": "b", "position": {"x": 0, "y": 0}, "data": {}}],
        "edges": [{"id": "ab", "source": "a", "target": "b"}, {"id": "ba", "source": "b", "target": "a"}],
    }
    out = render_ascii(flow)
    # no infinite loop, mentions cycle
    assert "cycle" in out.lower() or "no root" in out.lower()


def test_explain_position_dragging():
    out = explain_change({"type": "position", "id": "n1", "dragging": True, "position": {"x": 10, "y": 20}})
    assert out["ok"]
    assert out["kind"] == "node"
    assert "actively dragging" in out["explanation"]
    assert "snapshot" in out.get("recipe_hint", "").lower()


def test_explain_position_drop():
    out = explain_change({"type": "position", "id": "n1", "dragging": False, "position": {"x": 10, "y": 20}})
    assert "snapshot" in out["explanation"].lower()


def test_explain_remove():
    out = explain_change({"type": "remove", "id": "edge-1"})
    assert "Delete" in out["explanation"]


def test_explain_unknown_type():
    out = explain_change({"type": "neverHeardOf"})
    assert not out["ok"]
