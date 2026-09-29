from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.ui.widget.node_editor.editor import NodeEditor


def _editor(**overrides):
    values = dict(
        _base_id_max={},
        graph=SimpleNamespace(nodes={}, registry=None),
    )
    values.update(overrides)
    obj = SimpleNamespace(**values)
    obj._split_base_suffix = lambda text: NodeEditor._split_base_suffix(obj, text)
    obj._bump_base_counter = lambda prop_id, base, suffix: NodeEditor._bump_base_counter(obj, prop_id, base, suffix)
    obj._current_max_suffix_in_graph = lambda prop_id, base: NodeEditor._current_max_suffix_in_graph(obj, prop_id, base)
    obj._is_base_id_pid = lambda pid, pm: NodeEditor._is_base_id_pid(obj, pid, pm)
    obj._normalize_node_dict = lambda uuid_key, nd: NodeEditor._normalize_node_dict(obj, uuid_key, nd)
    obj._extract_values_from_properties_block = lambda nd: NodeEditor._extract_values_from_properties_block(obj, nd)
    obj._normalize_conn_dict = lambda cuuid, cd: NodeEditor._normalize_conn_dict(obj, cuuid, cd)
    return obj


@pytest.mark.parametrize(
    "pid, name, flag, expected",
    [
        ("base_id", "Anything", False, True),
        ("other", "Base ID", False, True),
        ("id_base", "Other", False, True),
        ("other", "Other", True, True),
        ("other", "Other", False, False),
    ],
)
def test_base_id_detection(pid, name, flag, expected):
    pm = SimpleNamespace(name=name, is_base_id=flag)
    assert NodeEditor._is_base_id_pid(SimpleNamespace(), pid, pm) is expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("agent_12", ("agent", 12)),
        ("agent", ("agent", None)),
        ("agent_x", ("agent_x", None)),
        (17, ("17", None)),
        ("a_b_003", ("a_b", 3)),
    ],
)
def test_split_base_suffix(value, expected):
    assert NodeEditor._split_base_suffix(SimpleNamespace(), value) == expected


def test_base_counter_only_moves_forward():
    editor = _editor()
    NodeEditor._bump_base_counter(editor, "base_id", "agent", 3)
    NodeEditor._bump_base_counter(editor, "base_id", "agent", 2)
    NodeEditor._bump_base_counter(editor, "base_id", "agent", 8)
    assert editor._base_id_max == {"base_id": {"agent": 8}}


def test_current_max_suffix_scans_live_graph_only_for_matching_base():
    editor = _editor()
    editor.graph.nodes = {
        "a": SimpleNamespace(properties={"base_id": SimpleNamespace(value="agent_2")}),
        "b": SimpleNamespace(properties={"base_id": SimpleNamespace(value="agent_9")}),
        "c": SimpleNamespace(properties={"base_id": SimpleNamespace(value="worker_20")}),
        "d": SimpleNamespace(properties={"base_id": SimpleNamespace(value="agent")}),
    }
    assert NodeEditor._current_max_suffix_in_graph(editor, "base_id", "agent") == 9
    assert NodeEditor._current_max_suffix_in_graph(editor, "base_id", "worker") == 20
    assert NodeEditor._current_max_suffix_in_graph(editor, "base_id", "") == 0


def test_next_suffix_uses_live_graph_and_updates_cache():
    editor = _editor()
    editor.graph.nodes = {
        "a": SimpleNamespace(properties={"base_id": SimpleNamespace(value="agent_4")}),
    }
    assert NodeEditor._next_suffix_for_base(editor, "base_id", "agent") == 5
    assert editor._base_id_max["base_id"]["agent"] == 4


def test_prepare_new_node_defaults_assigns_next_local_suffix():
    editor = _editor()
    editor.graph.nodes = {
        "a": SimpleNamespace(properties={"base_id": SimpleNamespace(value="agent_1")}),
        "b": SimpleNamespace(properties={"base_id": SimpleNamespace(value="agent_3")}),
    }
    pm = SimpleNamespace(value="agent", name="Base ID", is_base_id=True)
    node = SimpleNamespace(properties={"base_id": pm})
    editor._next_suffix_for_base = lambda prop_id, base: NodeEditor._next_suffix_for_base(editor, prop_id, base)

    NodeEditor._prepare_new_node_defaults(editor, node)

    assert pm.value == "agent_4"
    assert editor._base_id_max["base_id"]["agent"] == 4


@pytest.mark.parametrize(
    "ptype, value, expected",
    [
        ("int", "12", 12),
        ("float", "1.25", 1.25),
        ("bool", "YES", True),
        ("bool", "off", False),
        ("bool", 0, False),
        ("combo", 17, "17"),
        ("str", None, ""),
        ("text", 5, "5"),
        ("custom", {"x": 1}, {"x": 1}),
    ],
)
def test_coerce_value_for_property(ptype, value, expected):
    pm = SimpleNamespace(type=ptype)
    assert NodeEditor._coerce_value_for_property(SimpleNamespace(), pm, value) == expected


def test_coerce_value_returns_original_on_failed_cast():
    pm = SimpleNamespace(type="int")
    value = object()
    assert NodeEditor._coerce_value_for_property(SimpleNamespace(), pm, value) is value


@pytest.mark.parametrize(
    "block, expected",
    [
        ({"a": 1, "b": {"value": 2}, "c": {"val": 3}}, {"a": 1, "b": 2, "c": 3}),
        ({"a": {"default": 4}, "b": {"data": 5}, "c": {}}, {"a": 4, "b": 5, "c": None}),
        ([{"id": "a", "value": 1}, {"key": "b", "val": 2}, {"name": "c", "default": 3}], {"a": 1, "b": 2, "c": 3}),
        ([], {}),
    ],
)
def test_extract_values_from_properties_block(block, expected):
    editor = _editor()
    assert NodeEditor._extract_values_from_properties_block(editor, {"properties": block}) == expected


def test_extract_values_accepts_props_and_fields_aliases():
    editor = _editor()
    assert NodeEditor._extract_values_from_properties_block(editor, {"props": {"a": 1}}) == {"a": 1}
    assert NodeEditor._extract_values_from_properties_block(editor, {"fields": {"b": 2}}) == {"b": 2}


def test_normalize_node_dict_uses_aliases_and_preserves_friendly_id():
    editor = _editor()
    result = NodeEditor._normalize_node_dict(
        editor,
        "uuid-key",
        {"id": "friendly", "type_name": "Agent", "title": "My node", "properties": {"x": {"value": 2}}},
    )
    assert result == {
        "uuid": "uuid-key",
        "type": "Agent",
        "name": "My node",
        "values": {"x": 2},
        "id": "friendly",
    }


def test_normalize_node_dict_rejects_invalid_shapes():
    editor = _editor()
    assert NodeEditor._normalize_node_dict(editor, None, None) is None
    assert NodeEditor._normalize_node_dict(editor, None, {"type": "Agent"}) is None
    assert NodeEditor._normalize_node_dict(editor, "u", {"name": "No type"}) is None


@pytest.mark.parametrize(
    "conn, expected",
    [
        (
            {"src_node": "a", "src_prop": "out", "dst_node": "b", "dst_prop": "in"},
            {"uuid": "c", "src_node": "a", "src_prop": "out", "dst_node": "b", "dst_prop": "in"},
        ),
        (
            {"source": "a", "out": "out", "target": "b", "in": "in"},
            {"uuid": "c", "src_node": "a", "src_prop": "out", "dst_node": "b", "dst_prop": "in"},
        ),
        (
            {"src": {"node": "a", "port": "out"}, "dst": {"uuid": "b", "id": "in"}},
            {"uuid": "c", "src_node": "a", "src_prop": "out", "dst_node": "b", "dst_prop": "in"},
        ),
    ],
)
def test_normalize_connection_dict(conn, expected):
    editor = _editor()
    assert NodeEditor._normalize_conn_dict(editor, "c", conn) == expected


def test_normalize_connection_dict_rejects_incomplete_data():
    editor = _editor()
    assert NodeEditor._normalize_conn_dict(editor, "c", {}) is None
    assert NodeEditor._normalize_conn_dict(editor, "c", "bad") is None


def test_extract_view_state_supports_top_level_and_nested_aliases():
    editor = _editor()
    assert NodeEditor._extract_view_state(editor, {"view": {"zoom": "1.5", "h": "2", "v": "3"}}) == {
        "zoom": 1.5,
        "h": 2,
        "v": 3,
    }
    assert NodeEditor._extract_view_state(editor, {"ui": {"camera": {"scale": 2, "x": 7, "y": 8}}}) == {
        "zoom": 2.0,
        "h": 7,
        "v": 8,
    }


def test_extract_view_state_ignores_invalid_values_and_missing_blocks():
    editor = _editor()
    assert NodeEditor._extract_view_state(editor, {"view": {"zoom": "bad", "h": "x", "v": 4}}) == {"v": 4}
    assert NodeEditor._extract_view_state(editor, {}) is None
    assert NodeEditor._extract_view_state(editor, []) is None


def test_registry_prop_spec_finds_list_and_dict_collections():
    prop_a = SimpleNamespace(id="a")
    prop_b = object()
    spec = SimpleNamespace(properties=[prop_a], props={"b": prop_b})
    editor = _editor(graph=SimpleNamespace(nodes={}, registry=SimpleNamespace(get=MagicMock(return_value=spec))))
    assert NodeEditor._registry_prop_spec(editor, "Agent", "a") is prop_a
    assert NodeEditor._registry_prop_spec(editor, "Agent", "b") is prop_b
    assert NodeEditor._registry_prop_spec(editor, "Agent", "missing") is None
