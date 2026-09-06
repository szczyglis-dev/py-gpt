from uuid import UUID

from pygpt_net.core.node_editor.models import ConnectionModel, NodeModel, PropertyModel
from pygpt_net.core.node_editor.types import NodeTypeRegistry, NodeTypeSpec, PropertySpec
from pygpt_net.core.node_editor.utils import gen_uuid


def test_gen_uuid_returns_unique_valid_uuid_strings():
    first, second = gen_uuid(), gen_uuid()
    assert first != second
    assert str(UUID(first)) == first
    assert str(UUID(second)) == second


def test_registry_defaults_register_get_types_and_display_name():
    registry = NodeTypeRegistry()
    assert "Value/Float" in registry.types()
    assert "Math/Add" in registry.types()
    custom = NodeTypeSpec(type_name="Agent/Worker", display_name="Worker", properties=[])
    registry.register(custom)
    assert registry.get("Agent/Worker") is custom
    assert registry.display_name("Agent/Worker") == "Worker"
    custom.display_name = "  "
    assert registry.display_name("Agent/Worker") == "Agent/Worker"
    assert registry.display_name("Missing") == "Missing"


def test_empty_registry_has_no_default_types():
    assert NodeTypeRegistry(empty=True).types() == []


def test_property_model_round_trip_and_defaults():
    model = PropertyModel(
        uuid="p1", id="value", type="combo", name="Value", editable=False,
        value="a", allowed_inputs=1, allowed_outputs=-1, options=["a", "b"],
        placeholder="choose", description="desc",
    )
    assert PropertyModel.from_dict(model.to_dict()) == model
    defaulted = PropertyModel.from_dict({"id": "x", "type": "str"})
    assert defaulted.name == "x"
    assert defaulted.editable is True
    assert defaulted.options is None
    UUID(defaulted.uuid)


def test_node_model_round_trip_converts_nested_properties():
    prop = PropertyModel(uuid="p", id="x", type="str", name="X", value="v")
    node = NodeModel(uuid="n", id="node_1", name="Node", type="Custom", properties={"x": prop})
    restored = NodeModel.from_dict(node.to_dict())
    assert restored == node
    defaulted = NodeModel.from_dict({"id": "node_2", "type": "Custom"})
    assert defaulted.name == "node_2"
    UUID(defaulted.uuid)


def test_connection_model_round_trip_and_generated_uuid():
    conn = ConnectionModel(uuid="c", src_node="a", src_prop="out", dst_node="b", dst_prop="in")
    assert ConnectionModel.from_dict(conn.to_dict()) == conn
    restored = ConnectionModel.from_dict({"src_node": "a", "src_prop": "out", "dst_node": "b", "dst_prop": "in"})
    UUID(restored.uuid)
