import json

from pygpt_net.core.events import AppEvent, BaseEvent, ControlEvent, Event, KernelEvent, RealtimeEvent, RenderEvent


def test_base_event_normalizes_data_and_serializes_stable_fields():
    event = BaseEvent(name="x")
    assert event.data == {}
    assert event.to_dict() == {"name": "x", "data": {}, "stop": False, "internal": False}
    assert json.loads(event.dump()) == event.to_dict()
    assert str(event) == event.dump()


def test_full_name_uses_event_family_id():
    event = Event(name=Event.USER_SEND, data={"x": 1})
    assert event.full_name == f"Event: {Event.USER_SEND}"
    assert event.id == "Event"


def test_dump_returns_empty_string_for_non_json_serializable_data():
    event = Event(name="x", data={"bad": object()})
    assert event.dump() == ""


def test_event_families_expose_expected_ids_and_constants():
    assert AppEvent.id == "AppEvent"
    assert ControlEvent.id == "ControlEvent"
    assert KernelEvent.id == "KernelEvent"
    assert RealtimeEvent.id == "RealtimeEvent"
    assert RenderEvent.id == "RenderEvent"
    assert KernelEvent.AGENT_V2_TOOL_EXEC == "kernel.agent_v2.tool_exec"
    assert RealtimeEvent.RT_OUTPUT_TEXT_DELTA == "rt.output.text.delta"
    assert RenderEvent.TOOL_UPDATE == "render.tool.update"
