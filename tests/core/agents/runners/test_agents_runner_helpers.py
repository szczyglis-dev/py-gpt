from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.agents.runners.helpers as helpers_module
from pygpt_net.core.agents.runners.helpers import Helpers
from pygpt_net.core.events import KernelEvent, RenderEvent


def make_source_ctx():
    return SimpleNamespace(
        meta=object(),
        mode="agent_llama",
        model="model-x",
        images=["img"],
        urls=["url"],
        attachments={"a": 1},
        files=["f"],
        cmds={"tool": {"x": 1}},
        results={"tool": {"y": 2}},
        extra={"tool_output": {"nested": [1]}, "other": "value"},
    )


def test_agents_runner_helpers_add_ctx_copies_runtime_fields_and_tool_outputs():
    helper = Helpers()
    source = make_source_ctx()

    ctx = helper.add_ctx(source, with_tool_outputs=True)

    assert ctx.meta is source.meta
    assert ctx.internal is True
    assert ctx.current is True
    assert ctx.live is True
    assert ctx.mode == source.mode
    assert ctx.model == source.model
    assert ctx.prev_ctx is source
    assert ctx.images is source.images
    assert ctx.urls is source.urls
    assert ctx.attachments is source.attachments
    assert ctx.files is source.files
    assert ctx.cmds == source.cmds and ctx.cmds is not source.cmds
    assert ctx.results == source.results and ctx.results is not source.results
    assert ctx.extra["tool_output"] == source.extra["tool_output"]
    assert ctx.extra["tool_output"] is not source.extra["tool_output"]


def test_agents_runner_helpers_add_next_ctx_copies_extra_without_aliasing(monkeypatch):
    helper = Helpers()
    source = make_source_ctx()
    monkeypatch.setattr(helpers_module.time, "time", lambda: 123.9)

    ctx = helper.add_next_ctx(source)

    assert ctx.meta is source.meta
    assert ctx.mode == source.mode
    assert ctx.model == source.model
    assert ctx.prev_ctx is source
    assert ctx.extra == source.extra
    assert ctx.extra is not source.extra
    assert ctx.output_timestamp == 123


def test_agents_runner_helpers_stream_events_use_safe_emit(monkeypatch):
    helper = Helpers()
    ctx = SimpleNamespace(meta=object(), stream="before<execute>x</execute>after")
    signals = object()
    emitted = []
    monkeypatch.setattr(helpers_module, "safe_emit", lambda source, name, event: emitted.append((source, name, event)) or True)

    helper.send_stream(ctx, signals, begin=True)
    helper.next_stream(ctx, signals)
    helper.end_stream(ctx, signals)

    assert [item[2].name for item in emitted] == [
        RenderEvent.STREAM_APPEND,
        RenderEvent.STREAM_NEXT,
        RenderEvent.STREAM_END,
    ]
    assert emitted[0][2].data["chunk"] == "before\n```python\nx\n```\nafter"
    assert emitted[0][2].data["begin"] is True


def test_agents_runner_helpers_kernel_events_and_status(monkeypatch):
    window = SimpleNamespace(
        core=SimpleNamespace(
            debug=SimpleNamespace(error=MagicMock()),
            agents=SimpleNamespace(runner=SimpleNamespace(last_error=None)),
        ),
        controller=SimpleNamespace(kernel=SimpleNamespace(stopped=MagicMock(return_value=True))),
        dispatch=MagicMock(),
    )
    helper = Helpers(window)
    signals = object()
    emitted = []
    monkeypatch.setattr(helpers_module, "safe_emit", lambda source, name, event: emitted.append(event) or True)
    monkeypatch.setattr(helpers_module, "trans", lambda key: "reasoning" if key == "status.agent.reasoning" else key)

    ctx = SimpleNamespace(meta=object())
    helper.send_response(ctx, signals, KernelEvent.APPEND_END, key="value")
    helper.set_busy(signals, extra=True)
    helper.set_idle(signals, extra=True)
    helper.set_status(signals, "working")

    assert [event.name for event in emitted] == [
        KernelEvent.APPEND_END,
        KernelEvent.STATE_BUSY,
        KernelEvent.STATE_IDLE,
        KernelEvent.STATUS,
    ]
    assert emitted[0].data["context"].ctx is ctx
    assert emitted[0].data["extra"] == {"key": "value"}
    assert emitted[1].data == {"id": "agent", "msg": "reasoning", "extra": True}
    assert emitted[2].data == {"id": "agent", "extra": True}
    assert emitted[3].data == {"status": "working"}
    assert helper.is_stopped() is True

    error = RuntimeError("bad")
    helper.set_error(error)
    assert helper.get_error() is error
    window.core.debug.error.assert_called_once_with(error)


def test_agents_runner_helpers_prepare_input_uses_mutated_dispatch_value():
    def dispatch(event):
        event.data["value"] = event.data["value"].upper()

    helper = Helpers(SimpleNamespace(dispatch=dispatch))
    assert helper.prepare_input("hello") == "HELLO"


def test_agents_runner_helpers_extract_final_response():
    helper = Helpers()
    thought, answer = helper.extract_final_response("Thought: think\nAnswer: final")
    assert thought == "think"
    assert answer == "final"
    assert helper.extract_final_response("plain text") == ("", "")
