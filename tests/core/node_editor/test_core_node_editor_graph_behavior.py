from pygpt_net.core.node_editor.graph import NodeGraph
from pygpt_net.core.node_editor.models import ConnectionModel, NodeModel, PropertyModel
from pygpt_net.core.node_editor.types import NodeTypeRegistry, NodeTypeSpec, PropertySpec


def registry():
    r = NodeTypeRegistry(empty=True)
    r.register(NodeTypeSpec(
        type_name="Flow/Agent", title="Agent", display_name="Agent", base_id="agent", export_kind="agent",
        properties=[
            PropertySpec(id="prompt", type="str", value="hello"),
            PropertySpec(id="out", type="slot", allowed_outputs=1),
            PropertySpec(id="help", type="HelpLabel", value="hidden"),
        ],
    ))
    r.register(NodeTypeSpec(
        type_name="Flow/End", title="End", base_id="end", export_kind="end",
        properties=[PropertySpec(id="in", type="slot", allowed_inputs=1)],
    ))
    r.register(NodeTypeSpec(type_name="Plain/Value", title="Value", properties=[]))
    return r


def test_create_node_uses_friendly_ids_base_property_and_generic_counter():
    graph = NodeGraph(registry())
    a1 = graph.create_node_from_type("Flow/Agent")
    a2 = graph.create_node_from_type("Flow/Agent", "Custom name")
    plain = graph.create_node_from_type("Plain/Value")
    assert (a1.id, a2.id, plain.id) == ("agent_1", "agent_2", "Node-1")
    assert a1.properties["base_id"].value == "agent"
    assert a1.properties["base_id"].editable is False
    assert a2.name == "Custom name"


def test_create_unknown_type_raises():
    graph = NodeGraph(registry())
    try:
        graph.create_node_from_type("Missing")
    except ValueError as exc:
        assert "Unknown node type" in str(exc)
    else:
        raise AssertionError("ValueError expected")


def test_add_remove_node_and_connection_lifecycle():
    graph = NodeGraph(registry())
    src = graph.create_node_from_type("Flow/Agent")
    dst = graph.create_node_from_type("Flow/End")
    graph.add_node(src); graph.add_node(dst)
    ok, reason, conn = graph.connect((src.uuid, "out"), (dst.uuid, "in"))
    assert ok is True and reason == "" and conn is not None
    assert conn.uuid in graph.connections
    graph.remove_node(src.uuid)
    assert src.uuid not in graph.nodes
    assert graph.connections == {}


def test_can_connect_reports_validation_errors_and_limits():
    graph = NodeGraph(registry())
    src = graph.create_node_from_type("Flow/Agent")
    dst = graph.create_node_from_type("Flow/End")
    graph.add_node(src); graph.add_node(dst)
    assert graph.can_connect(("missing", "out"), (dst.uuid, "in"))[1] == "Node not found."
    assert graph.can_connect((src.uuid, "missing"), (dst.uuid, "in"))[1] == "Property not found."
    assert graph.can_connect((src.uuid, "prompt"), (dst.uuid, "in"))[1] == "Source has no outputs."
    src.properties["out"].type = "str"
    assert graph.can_connect((src.uuid, "out"), (dst.uuid, "in"))[1].startswith("Type mismatch")
    src.properties["out"].type = "slot"
    assert graph.connect((src.uuid, "out"), (dst.uuid, "in"))[0] is True
    assert graph.can_connect((src.uuid, "out"), (dst.uuid, "in"))[1] in {
        "Destination input limit reached.", "Source output limit reached."
    }


def test_duplicate_connection_is_rejected_when_ports_unlimited():
    graph = NodeGraph(registry())
    src = graph.create_node_from_type("Flow/Agent"); dst = graph.create_node_from_type("Flow/End")
    src.properties["out"].allowed_outputs = -1; dst.properties["in"].allowed_inputs = -1
    graph.add_node(src); graph.add_node(dst)
    conn = ConnectionModel(uuid="c1", src_node=src.uuid, src_prop="out", dst_node=dst.uuid, dst_prop="in")
    assert graph.add_connection(conn) == (True, "")
    dup = ConnectionModel(uuid="c2", src_node=src.uuid, src_prop="out", dst_node=dst.uuid, dst_prop="in")
    assert graph.add_connection(dup) == (False, "Connection already exists.")
    graph.remove_connection("c1")
    assert graph.connections == {}


def test_set_property_value_respects_editable_flag():
    graph = NodeGraph(registry())
    node = graph.create_node_from_type("Flow/Agent"); graph.add_node(node)
    graph.set_property_value(node.uuid, "prompt", "changed")
    assert node.properties["prompt"].value == "changed"
    graph.set_property_value(node.uuid, "base_id", "bad")
    assert node.properties["base_id"].value == "agent"
    graph.set_property_value("missing", "prompt", "ignored")


def test_schema_serialization_and_round_trip_preserve_connections_and_counters():
    graph = NodeGraph(registry())
    src = graph.create_node_from_type("Flow/Agent"); dst = graph.create_node_from_type("Flow/End")
    src.properties["out"].allowed_outputs = -1; dst.properties["in"].allowed_inputs = -1
    graph.add_node(src); graph.add_node(dst); graph.connect((src.uuid, "out"), (dst.uuid, "in"))
    schema = graph.to_schema()
    assert schema["nodes"][src.uuid]["values"]["prompt"] == "hello"
    assert "help" not in schema["nodes"][src.uuid]["values"]
    list_schema = graph.to_list_schema()
    agent = next(x for x in list_schema if x["id"] == src.id)
    assert agent["type"] == "agent"
    assert agent["slots"]["prompt"] == "hello"
    assert agent["slots"]["out"]["out"] == [dst.id]
    assert "base_id" not in agent["slots"] and "help" not in agent["slots"]

    raw = graph.to_dict()
    restored = NodeGraph(registry())
    restored.from_dict(raw)
    assert restored.to_dict() == raw
    restored.clear()
    assert restored.nodes == {} and restored.connections == {}
    assert restored.create_node_from_type("Flow/Agent").id == "agent_1"


def test_from_dict_seeds_missing_friendly_counters():
    graph = NodeGraph(registry())
    node = graph.create_node_from_type("Flow/Agent")
    node.id = "agent_7"
    graph.add_node(node)
    raw = graph.to_dict(); raw["_id_counters"] = {}
    restored = NodeGraph(registry()); restored.from_dict(raw)
    assert restored.create_node_from_type("Flow/Agent").id == "agent_8"
