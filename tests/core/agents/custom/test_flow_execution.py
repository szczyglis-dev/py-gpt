import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from pygpt_net.core.agents.custom.flow_execution import FlowStepExecution
from pygpt_net.core.agents.custom.flow_navigation import FlowNavigation
from pygpt_net.core.agents.custom.flow_types import DebugConfig, PreparedStep
import pygpt_net.core.agents.custom.flow_execution as execution_module


@pytest.mark.parametrize("multi,stream,mode", [
    (False, False, "off"), (False, True, "off"),
    (True, False, "off"), (True, True, "off"),
    (True, True, "delayed"), (True, True, "realtime"),
])
@pytest.mark.parametrize("partial", [False, True])
def test_all_presentation_paths_keep_answer_response_id_and_route(monkeypatch, multi, stream, mode, partial):
    raw = '{"route":"next","content":"answer"}' if multi else "answer"
    ctx = SimpleNamespace(stream="")
    bridge = MagicMock()
    bridge.stopped.return_value = False
    handler = MagicMock()
    handler.buffer = "answer"
    handler.handle.return_value = ("answer", "response-id")

    class Stream:
        async def stream_events(self):
            yield object()

    sdk = SimpleNamespace(
        run=AsyncMock(return_value=SimpleNamespace(final_output=raw, last_response_id="response-id")),
        run_streamed=MagicMock(return_value=Stream()),
    )
    collector = MagicMock()
    collector.buffer = raw
    collector.last_response_id = "response-id"
    collector.handle_event.return_value = ("", "response-id")
    monkeypatch.setattr(execution_module, "Runner", sdk)
    monkeypatch.setattr(execution_module, "DelayedRouterStreamer", lambda *args: collector)
    monkeypatch.setattr(execution_module, "RealtimeRouterStreamer", lambda **kwargs: collector)
    prepared = PreparedStep(
        SimpleNamespace(instance=object(), multi_output=multi, allowed_routes=["next", "end"]),
        {"input": [{"role": "user", "content": "question"}]}, "question", None,
    )
    options = SimpleNamespace(stream=stream, router_stream_mode=mode, use_partial_ctx=partial)
    result = asyncio.run(FlowStepExecution(None, MagicMock(), bridge, handler, options).execute(prepared, ctx, "old"))
    assert result.text == "answer"
    assert result.response_id == "response-id"
    if multi:
        assert result.decision.valid
        assert result.decision.route == "next"
    else:
        assert result.decision is None
    materialized = not stream or (multi and mode != "realtime")
    assert bridge.on_step.call_count == int(materialized)
    assert handler.to_buffer.call_count == int(materialized and not partial)


def test_invalid_route_falls_back_then_resolves_end_node():
    graph = SimpleNamespace(first_connected_end=lambda _: "finish", end_nodes=["finish"])
    log = MagicMock()
    navigation = FlowNavigation(graph, log, DebugConfig())
    prepared = SimpleNamespace(built=SimpleNamespace(allowed_routes=["end", "other"]))
    output = SimpleNamespace(decision=SimpleNamespace(valid=False, error="bad JSON"), router_mode="delayed")
    route = navigation.next_route("router", prepared, output)
    assert route == "end"
    assert navigation.advance("router", route) == ["finish"]
    log.warning.assert_called_once()


@pytest.mark.parametrize("mode", ["answer", "delayed", "realtime"])
def test_stop_cancels_stream_before_consuming_another_delta(monkeypatch, mode):
    class Stream:
        cancel = MagicMock()

        async def stream_events(self):
            yield object()
            raise AssertionError("Read after stop")

    stream = Stream()
    monkeypatch.setattr(execution_module, "Runner", SimpleNamespace(run_streamed=lambda *args, **kwargs: stream))
    collector = MagicMock(buffer="", last_response_id=None)
    monkeypatch.setattr(execution_module, "DelayedRouterStreamer", lambda *args: collector)
    monkeypatch.setattr(execution_module, "RealtimeRouterStreamer", lambda **kwargs: collector)
    bridge = MagicMock()
    bridge.stopped.return_value = True
    handler = MagicMock(buffer="")
    options = SimpleNamespace(stream=True, router_stream_mode=mode, use_partial_ctx=False)
    prepared = PreparedStep(SimpleNamespace(instance=object(), multi_output=mode != "answer", allowed_routes=[]), {}, "", None)
    ctx = object()
    result = asyncio.run(FlowStepExecution(None, MagicMock(), bridge, handler, options).execute(prepared, ctx, "old"))
    stream.cancel.assert_called_once()
    bridge.on_stop.assert_called_once_with(ctx)
    assert result.response_id == "old"
    handler.handle.assert_not_called()
    collector.handle_event.assert_not_called()
