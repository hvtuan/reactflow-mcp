from reactflow_mcp.validators import validate_flow


def _ok_flow():
    return {
        "nodes": [
            {"id": "a", "position": {"x": 0, "y": 0}, "data": {}, "type": "input"},
            {"id": "b", "position": {"x": 100, "y": 100}, "data": {}},
        ],
        "edges": [{"id": "a-b", "source": "a", "target": "b"}],
    }


def test_clean_flow_passes():
    r = validate_flow(_ok_flow())
    assert r["ok"] is True
    assert r["errors"] == []
    assert r["stats"]["nodes"] == 2
    assert r["stats"]["edges"] == 1


def test_root_and_leaf_detection():
    r = validate_flow(_ok_flow())
    assert r["stats"]["root_nodes"] == ["a"]
    assert r["stats"]["leaf_nodes"] == ["b"]


def test_non_object_input():
    r = validate_flow("not a dict")  # type: ignore[arg-type]
    assert r["ok"] is False
    assert any(e["code"] == "E_SHAPE" for e in r["errors"])


def test_duplicate_node_id():
    flow = _ok_flow()
    flow["nodes"].append({"id": "a", "position": {"x": 0, "y": 0}, "data": {}})
    r = validate_flow(flow)
    assert any(e["code"] == "E_NODE_DUP" for e in r["errors"])


def test_duplicate_edge_id():
    flow = _ok_flow()
    flow["edges"].append({"id": "a-b", "source": "a", "target": "b"})
    r = validate_flow(flow)
    assert any(e["code"] == "E_EDGE_DUP_ID" for e in r["errors"])


def test_missing_edge_endpoint():
    flow = _ok_flow()
    flow["edges"].append({"id": "x", "source": "a", "target": "ghost"})
    r = validate_flow(flow)
    assert any(e["code"] == "E_EDGE_TGT_MISSING" for e in r["errors"])


def test_v11_node_fields_flagged():
    flow = _ok_flow()
    flow["nodes"][0]["parentNode"] = "x"
    flow["nodes"][0]["xPos"] = 1
    r = validate_flow(flow)
    codes = [e["code"] for e in r["errors"]]
    assert codes.count("E_NODE_V11_FIELD") == 2


def test_v11_edge_field_flagged():
    flow = _ok_flow()
    flow["edges"][0]["updatable"] = True
    r = validate_flow(flow)
    assert any(e["code"] == "E_EDGE_V11_FIELD" for e in r["errors"])


def test_parent_after_child():
    flow = {
        "nodes": [
            {"id": "child", "position": {"x": 0, "y": 0}, "data": {}, "parentId": "parent"},
            {"id": "parent", "position": {"x": 0, "y": 0}, "data": {}},
        ],
        "edges": [],
    }
    r = validate_flow(flow)
    assert any(e["code"] == "E_PARENT_ORDER" for e in r["errors"])


def test_parent_missing():
    flow = {
        "nodes": [
            {"id": "child", "position": {"x": 0, "y": 0}, "data": {}, "parentId": "ghost"},
        ],
        "edges": [],
    }
    r = validate_flow(flow)
    assert any(e["code"] == "E_PARENT_MISSING" for e in r["errors"])


def test_cycle_detection():
    flow = {
        "nodes": [
            {"id": "a", "position": {"x": 0, "y": 0}, "data": {}},
            {"id": "b", "position": {"x": 0, "y": 0}, "data": {}},
            {"id": "c", "position": {"x": 0, "y": 0}, "data": {}},
        ],
        "edges": [
            {"id": "e1", "source": "a", "target": "b"},
            {"id": "e2", "source": "b", "target": "c"},
            {"id": "e3", "source": "c", "target": "a"},
        ],
    }
    r = validate_flow(flow)
    assert any(w["code"] == "W_CYCLE" for w in r["warnings"])
    cycles = r["stats"]["cycles"]
    assert len(cycles) == 1
    # canonical rotation starts at lex-smallest id ('a')
    assert cycles[0][0] == "a"


def test_no_cycle_when_only_path_through_missing_node():
    flow = {
        "nodes": [{"id": "a", "position": {"x": 0, "y": 0}, "data": {}}],
        "edges": [{"id": "e", "source": "a", "target": "ghost"}],
    }
    r = validate_flow(flow)
    # error from missing target, but no crash + no cycle
    assert r["stats"]["cycles"] == []


def test_parallel_edge_warning():
    flow = _ok_flow()
    flow["edges"].append({"id": "a-b-2", "source": "a", "target": "b"})
    r = validate_flow(flow)
    assert any(w["code"] == "W_EDGE_DUP_PARALLEL" for w in r["warnings"])


def test_handle_id_mismatch_warning():
    flow = {
        "nodes": [
            {"id": "a", "position": {"x": 0, "y": 0}, "data": {}, "handles": [{"id": "out", "type": "source", "position": "right"}]},
            {"id": "b", "position": {"x": 0, "y": 0}, "data": {}},
        ],
        "edges": [{"id": "e", "source": "a", "target": "b", "sourceHandle": "nope"}],
    }
    r = validate_flow(flow)
    assert any(w["code"] == "W_EDGE_SRC_HANDLE_MISMATCH" for w in r["warnings"])


def test_width_height_v12_warning():
    flow = _ok_flow()
    flow["nodes"][0]["width"] = 200
    r = validate_flow(flow)
    assert any(w["code"] == "W_V12_WIDTH_HEIGHT" for w in r["warnings"])


def test_runtime_field_warning():
    flow = _ok_flow()
    flow["nodes"][0]["positionAbsoluteX"] = 10
    r = validate_flow(flow)
    assert any(w["code"] == "W_RUNTIME_FIELD" for w in r["warnings"])


def test_stats_node_types_histogram():
    flow = _ok_flow()
    flow["nodes"][1]["type"] = "input"
    r = validate_flow(flow)
    assert r["stats"]["node_types"] == {"input": 2}
