from reactflow_mcp.data.recipes import RECIPES, get_recipe, list_recipes


def test_recipes_non_empty():
    assert len(RECIPES) >= 10


def test_each_recipe_well_formed():
    valid_categories = {"layout", "history", "interaction", "nodes", "grouping", "edges", "misc"}
    for name, r in RECIPES.items():
        assert {"title", "category", "summary", "problem", "approach", "apis_used", "files"} <= set(r.keys())
        assert r["category"] in valid_categories, f"{name} has bad category"
        assert isinstance(r["files"], dict) and r["files"], f"{name} has empty files"
        for fname, src in r["files"].items():
            assert src.strip(), f"{name}/{fname} empty source"


def test_get_recipe_known():
    r = get_recipe("auto_layout_dagre")
    assert r is not None
    assert r["category"] == "layout"
    assert "useReactFlow" in r["apis_used"]
    assert "@dagrejs/dagre" in r["deps"]


def test_get_recipe_case_insensitive():
    assert get_recipe("UNDO_REDO") is not None
    assert get_recipe("Undo_Redo") is not None


def test_get_recipe_unknown():
    assert get_recipe("ThisRecipeDoesNotExist") is None


def test_list_recipes_filter_category():
    layout_recipes = list_recipes(category="layout")
    assert all(r["category"] == "layout" for r in layout_recipes)
    assert len(layout_recipes) >= 3   # dagre + elk + force


def test_expected_recipes_present():
    expected = {
        "auto_layout_dagre", "auto_layout_elkjs", "force_layout",
        "undo_redo", "copy_paste", "helper_lines", "node_position_animation",
        "expand_collapse", "selection_grouping", "shapes_node",
        "editable_edge", "server_side_image", "remove_attribution",
    }
    assert expected <= set(RECIPES.keys())


def test_node_position_animation_uses_d3_timer_not_css():
    """Regression: CSS transition does NOT work — must use d3-timer per-frame interpolation."""
    r = RECIPES["node_position_animation"]
    assert "d3-timer" in r["deps"]
    # ensure no recipe pretends CSS transition works
    for src in r["files"].values():
        assert "transition: transform" not in src or "does NOT work" in src or "doesn't work" in src.lower()
