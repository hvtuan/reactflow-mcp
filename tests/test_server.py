"""Integration smoke test: server imports cleanly, _self_check returns sane counts."""

from reactflow_mcp.server import _self_check


def test_self_check_basic_shape():
    check = _self_check()
    assert check["server"] == "reactflow_mcp"
    assert isinstance(check["tools"], list) and len(check["tools"]) == 11
    assert check["resources"] == ["reactflow://deep-dive"]
    assert check["recipes"] >= 10


def test_self_check_data_counts_lower_bounds():
    check = _self_check()
    assert check["deep_dive_chars"] > 20_000
    assert check["sections"] >= 25
    assert check["api_catalog_entries"] >= 110   # post-Tier-A expansion
    assert check["migration_entries"] >= 10
    assert check["pro_examples"] >= 20
    assert check["svelte_renamed"] >= 4
    assert check["svelte_identical"] >= 50
    assert check["svelte_only"] >= 1
    assert check["recipes"] >= 10
    assert len(check["prompts"]) >= 4


def test_all_expected_tools_registered():
    expected = {
        "reactflow_search_docs",
        "reactflow_get_api",
        "reactflow_lookup_v11_v12",
        "reactflow_list_pro_examples",
        "reactflow_scaffold_custom_node",
        "reactflow_scaffold_custom_edge",
        "reactflow_validate_flow",
        "reactflow_svelte_equivalent",
        "reactflow_list_recipes",
        "reactflow_get_recipe",
        "reactflow_scaffold_flow",
    }
    assert set(_self_check()["tools"]) == expected
