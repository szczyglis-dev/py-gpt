#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.bridge import BridgeWorker
from pygpt_net.core.events import KernelEvent
from pygpt_net.core.types import MODE_AGENT_V2


def make_context():
    return SimpleNamespace(
        mode=MODE_AGENT_V2,
        model=SimpleNamespace(provider="openai"),
        parent_mode=None,
        preset=None,
        ctx=SimpleNamespace(reply=False, meta=None, hidden_input=None),
        system_prompt="",
        prompt="hello",
        history=[],
    )


def make_worker(call_result=True, error="agent error"):
    worker = BridgeWorker()
    worker.mode = MODE_AGENT_V2
    runner = SimpleNamespace(
        call=MagicMock(return_value=call_result),
        get_error=MagicMock(return_value=error),
    )
    worker.window = SimpleNamespace(
        core=SimpleNamespace(
            debug=SimpleNamespace(info=MagicMock()),
            agents_v2=SimpleNamespace(runner=runner),
        )
    )
    worker.context = make_context()
    worker.extra = {}
    response = MagicMock()
    response.disconnect = MagicMock()
    worker.signals = SimpleNamespace(response=response, deleteLater=MagicMock())
    worker.handle_post_prompt_async = MagicMock()
    worker.handle_additional_context = MagicMock()
    worker.handle_post_prompt_end = MagicMock()
    return worker, runner, response


def test_agents_v2_bridge_routes_mode_to_agents_v2_runner_without_legacy_response_event():
    worker, runner, response = make_worker(call_result=True)

    worker.run()

    runner.call.assert_called_once()
    kwargs = runner.call.call_args.kwargs
    assert kwargs["context"] is worker.context
    assert kwargs["extra"] is worker.extra
    response.emit.assert_not_called()
    assert worker.signals is None


def test_agents_v2_bridge_runner_failure_exposes_error_and_emits_response_error():
    worker, runner, response = make_worker(call_result=False, error="v2 failed")
    context = worker.context
    extra = worker.extra

    worker.run()

    runner.get_error.assert_called_once()
    assert extra["error"] == "v2 failed"
    event = response.emit.call_args.args[0]
    assert event.name == KernelEvent.RESPONSE_ERROR
    assert event.data["context"] is context
    assert event.data["extra"] is extra
