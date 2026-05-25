from reactflow_mcp.data.pro_examples import LICENSE_NOTES, PRICING_TIERS, PRO_EXAMPLES


def test_examples_non_empty():
    assert len(PRO_EXAMPLES) >= 20


def test_each_example_well_formed():
    valid_categories = {"layout", "interaction", "edges", "nodes", "grouping", "whiteboard", "misc", "template"}
    valid_frameworks = {"react", "svelte"}
    for ex in PRO_EXAMPLES:
        assert {"name", "category", "frameworks", "summary"} <= set(ex.keys())
        assert ex["category"] in valid_categories, f"bad category for {ex['name']}: {ex['category']}"
        assert all(fw in valid_frameworks for fw in ex["frameworks"]), f"bad frameworks for {ex['name']}"
        assert ex["summary"]


def test_pricing_tiers():
    assert len(PRICING_TIERS) == 3
    names = {t["name"] for t in PRICING_TIERS}
    assert names == {"Starter", "Professional", "Enterprise"}
    for t in PRICING_TIERS:
        assert isinstance(t["seats"], int) and t["seats"] >= 1
        assert isinstance(t["includes"], list) and t["includes"]


def test_license_notes_keys():
    assert {"core", "ui_kit", "perpetual", "redistribution", "seats", "attribution"} <= set(LICENSE_NOTES.keys())


def test_collaborative_only_react():
    collab = [e for e in PRO_EXAMPLES if e["name"] == "Collaborative"]
    assert collab and "svelte" not in collab[0]["frameworks"]


def test_shapes_both_frameworks():
    shapes = [e for e in PRO_EXAMPLES if e["name"] == "Shapes"]
    assert shapes
    assert "react" in shapes[0]["frameworks"] and "svelte" in shapes[0]["frameworks"]
