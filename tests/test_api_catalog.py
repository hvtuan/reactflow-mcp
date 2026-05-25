from reactflow_mcp.data.api_catalog import API_CATALOG, get_symbol, list_symbols


def test_catalog_non_empty():
    assert len(API_CATALOG) > 50


def test_every_entry_has_required_keys():
    for name, entry in API_CATALOG.items():
        assert "kind" in entry, f"{name} missing kind"
        assert "category" in entry, f"{name} missing category"
        assert "summary" in entry, f"{name} missing summary"
        assert entry["kind"] in {"component", "hook", "util", "type", "enum", "prop"}


def test_get_symbol_case_insensitive():
    assert get_symbol("useReactFlow") is not None
    assert get_symbol("usereactflow") is not None
    assert get_symbol("USEREACTFLOW") is not None
    assert get_symbol("Handle") is not None
    assert get_symbol("handle") is not None


def test_get_symbol_unknown_returns_none():
    assert get_symbol("ThisDoesNotExist") is None


def test_list_symbols_filters():
    hooks = list_symbols(kind="hook")
    assert "useReactFlow" in hooks
    assert "Handle" not in hooks  # component
    components = list_symbols(kind="component")
    assert "Handle" in components
    assert "useReactFlow" not in components


def test_deprecated_useHandleConnections_flagged():
    entry = get_symbol("useHandleConnections")
    assert entry is not None
    assert entry.get("deprecated") is True
    assert entry.get("replacement") == "useNodeConnections"
