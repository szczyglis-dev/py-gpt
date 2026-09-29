from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.ui.widget.node_editor.node import NodeContentWidget, NodeItem


def _content(**overrides):
    node = SimpleNamespace(type="Agent", uuid="u1", properties={})
    graph = SimpleNamespace(nodes={"u1": node}, registry=None)
    editor = SimpleNamespace(_allowed_from_spec=MagicMock())
    values = dict(node=node, graph=graph, editor=editor)
    values.update(overrides)
    obj = SimpleNamespace(**values)
    obj._resolve_existing_suffix = lambda pid, base: NodeContentWidget._resolve_existing_suffix(obj, pid, base)
    obj._get_prop_spec = lambda pid: NodeContentWidget._get_prop_spec(obj, pid)
    return obj


@pytest.mark.parametrize(
    "pid, name, flag, expected",
    [
        ("base_id", "X", False, True),
        ("other", "Base Name", False, True),
        ("other", "X", True, True),
        ("other", "X", False, False),
    ],
)
def test_content_base_id_detection(pid, name, flag, expected):
    pm = SimpleNamespace(name=name, is_base_id=flag)
    assert NodeContentWidget._is_base_id_property(SimpleNamespace(), pid, pm) is expected


@pytest.mark.parametrize(
    "base, suffix, expected",
    [
        ("agent_4", None, "agent_4"),
        ("agent", 3, "agent_3"),
        ("agent", "_blue", "agent_blue"),
        ("agent", "", "agent"),
        (17, 2, "17_2"),
    ],
)
def test_compose_base_id_display(base, suffix, expected):
    widget = SimpleNamespace(_resolve_existing_suffix=MagicMock(return_value=suffix))
    assert NodeContentWidget._compose_base_id_display(widget, "base_id", base) == expected
    if isinstance(base, str) and base.endswith("_4"):
        widget._resolve_existing_suffix.assert_not_called()


def test_resolve_existing_suffix_prefers_sibling_property():
    node = SimpleNamespace(
        uuid="u1",
        properties={
            "base_id": SimpleNamespace(value="agent"),
            "suffix": SimpleNamespace(value=7),
        },
    )
    widget = _content(node=node, graph=SimpleNamespace(nodes={"u1": node}, registry=None))
    assert NodeContentWidget._resolve_existing_suffix(widget, "base_id", "agent") == 7


def test_resolve_existing_suffix_uses_node_attribute_then_metadata():
    node = SimpleNamespace(uuid="u1", properties={}, friendly_index=5, meta={"index": 9})
    widget = _content(node=node, graph=SimpleNamespace(nodes={"u1": node}, registry=None))
    assert NodeContentWidget._resolve_existing_suffix(widget, "base_id", "agent") == 5

    node.friendly_index = None
    assert NodeContentWidget._resolve_existing_suffix(widget, "base_id", "agent") == 9


def test_resolve_existing_suffix_falls_back_to_stable_graph_order():
    n1 = SimpleNamespace(uuid="a", properties={"base_id": SimpleNamespace(value="agent")})
    n2 = SimpleNamespace(uuid="b", properties={"base_id": SimpleNamespace(value="agent")})
    n3 = SimpleNamespace(uuid="c", properties={"base_id": SimpleNamespace(value="other")})
    graph = SimpleNamespace(nodes={"c": n3, "b": n2, "a": n1}, registry=None)
    widget = _content(node=n2, graph=graph)
    assert NodeContentWidget._resolve_existing_suffix(widget, "base_id", "agent") == 2


def test_display_name_prefers_registry_then_model_then_pid():
    prop = {"label": "Registry Label"}
    spec = SimpleNamespace(properties={"x": prop})
    graph = SimpleNamespace(registry=SimpleNamespace(get=MagicMock(return_value=spec)))
    widget = SimpleNamespace(graph=graph, node=SimpleNamespace(type="Agent"))
    pm = SimpleNamespace(name="Model Label")
    assert NodeContentWidget._display_name_for_property(widget, "x", pm) == "Registry Label"

    graph.registry.get.return_value = None
    assert NodeContentWidget._display_name_for_property(widget, "x", pm) == "Model Label"
    assert NodeContentWidget._display_name_for_property(widget, "x", SimpleNamespace(name="")) == "x"


def test_editable_from_spec_prefers_explicit_registry_flag():
    spec = SimpleNamespace(properties={"x": {"editable": False}})
    graph = SimpleNamespace(registry=SimpleNamespace(get=MagicMock(return_value=spec)))
    widget = SimpleNamespace(graph=graph, node=SimpleNamespace(type="Agent"))
    assert NodeContentWidget._editable_from_spec(widget, "x", SimpleNamespace(editable=True)) is False

    graph.registry.get.return_value = None
    assert NodeContentWidget._editable_from_spec(widget, "x", SimpleNamespace(editable=False)) is False
    assert NodeContentWidget._editable_from_spec(widget, "x", SimpleNamespace()) is True


@pytest.mark.parametrize(
    "allowed, expected",
    [
        ((2, 3), "3/2"),
        ((-1, 1), "1/∞"),
        ((0, 0), "-/-"),
        (("bad", None), "-/-"),
    ],
)
def test_capacity_text_uses_live_editor_limits(allowed, expected):
    editor = SimpleNamespace(_allowed_from_spec=MagicMock(return_value=allowed))
    widget = SimpleNamespace(editor=editor, node=SimpleNamespace())
    assert NodeContentWidget._capacity_text_for_property(widget, "x", SimpleNamespace()) == expected


def test_capacity_text_falls_back_to_property_model():
    editor = SimpleNamespace(_allowed_from_spec=MagicMock(side_effect=RuntimeError("no spec")))
    widget = SimpleNamespace(editor=editor, node=SimpleNamespace())
    pm = SimpleNamespace(allowed_outputs=4, allowed_inputs=-1)
    assert NodeContentWidget._capacity_text_for_property(widget, "x", pm) == "∞/4"


def test_spec_text_attr_supports_object_and_dict_and_ignores_empty():
    obj = SimpleNamespace(description="hello")
    widget = SimpleNamespace(_get_prop_spec=MagicMock(return_value=obj))
    assert NodeContentWidget._spec_text_attr(widget, "x", "description") == "hello"

    widget._get_prop_spec.return_value = {"placeholder": "type here"}
    assert NodeContentWidget._spec_text_attr(widget, "x", "placeholder") == "type here"

    widget._get_prop_spec.return_value = {"placeholder": ""}
    assert NodeContentWidget._spec_text_attr(widget, "x", "placeholder") is None


def _node_item(**overrides):
    values = dict(
        editor=SimpleNamespace(_resize_grip_margin=12.0, _resize_grip_hit_inset=5.0),
        node=SimpleNamespace(properties={}),
        graph=SimpleNamespace(registry=None),
    )
    values.update(overrides)
    obj = SimpleNamespace(**values)
    obj._get_prop_spec = lambda pid: NodeItem._get_prop_spec(obj, pid)
    obj._spec_int = lambda spec, key, default: NodeItem._spec_int(obj, spec, key, default)
    obj._pm_allowed = lambda pid, inputs: NodeItem._pm_allowed(obj, pid, inputs)
    obj._effective_hit_margin = lambda: NodeItem._effective_hit_margin(obj)
    return obj


@pytest.mark.parametrize(
    "obj, key, default, expected",
    [
        (SimpleNamespace(limit=3), "limit", 0, 3),
        ({"limit": 4}, "limit", 0, 4),
        ({"limit": "4"}, "limit", 9, 9),
        (None, "limit", 7, 7),
    ],
)
def test_spec_int(obj, key, default, expected):
    assert NodeItem._spec_int(SimpleNamespace(), obj, key, default) == expected


def test_pm_allowed_reads_input_and_output_limits():
    pm = SimpleNamespace(allowed_inputs=2, allowed_outputs=-1)
    widget = _node_item(node=SimpleNamespace(properties={"p": pm}))
    assert NodeItem._pm_allowed(widget, "p", True) == 2
    assert NodeItem._pm_allowed(widget, "p", False) == -1
    assert NodeItem._pm_allowed(widget, "missing", True) is None


def test_allowed_capacity_prefers_registry_spec_with_model_fallback():
    pm = SimpleNamespace(allowed_inputs=1, allowed_outputs=2)
    widget = _node_item(node=SimpleNamespace(properties={"p": pm}))
    widget._get_prop_spec = MagicMock(return_value={"allowed_inputs": 5, "allowed_outputs": 6})
    assert NodeItem.allowed_capacity_for_pid(widget, "p", "input") == 5
    assert NodeItem.allowed_capacity_for_pid(widget, "p", "output") == 6

    widget._get_prop_spec.return_value = None
    assert NodeItem.allowed_capacity_for_pid(widget, "p", "input") == 1
    assert NodeItem.allowed_capacity_for_pid(widget, "p", "output") == 2


@pytest.mark.parametrize(
    "margin, inset, expected",
    [(12, 5, 7.0), (5, 20, 4.0), (0, 0, 12.0), (20, 2, 18.0)],
)
def test_effective_hit_margin(margin, inset, expected):
    widget = _node_item(editor=SimpleNamespace(
        _resize_grip_margin=margin,
        _resize_grip_hit_inset=inset,
    ))
    assert NodeItem._effective_hit_margin(widget) == expected


@pytest.mark.parametrize(
    "x, y, expected",
    [
        (99, 49, "corner"),
        (99, 10, "right"),
        (10, 49, "bottom"),
        (10, 10, "none"),
    ],
)
def test_hit_resize_zone(x, y, expected):
    size = SimpleNamespace(width=lambda: 100, height=lambda: 50)
    pos = SimpleNamespace(x=lambda: x, y=lambda: y)
    widget = SimpleNamespace(size=lambda: size, _effective_hit_margin=lambda: 7.0)
    assert NodeItem._hit_resize_zone(widget, pos) == expected


def test_edge_tracking_is_idempotent():
    edge = object()
    widget = SimpleNamespace(_edges=[])
    NodeItem.add_edge(widget, edge)
    NodeItem.add_edge(widget, edge)
    assert widget._edges == [edge]
    NodeItem.remove_edge(widget, edge)
    assert widget._edges == []
    NodeItem.remove_edge(widget, edge)
    assert widget._edges == []


def test_mark_ready_for_scene_ops_sets_boolean_state():
    widget = SimpleNamespace(_ready_scene_ops=False)
    NodeItem.mark_ready_for_scene_ops(widget, True)
    assert widget._ready_scene_ops is True
    NodeItem.mark_ready_for_scene_ops(widget, 0)
    assert widget._ready_scene_ops is False
