#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pygpt_net.core.agents_v2.runner as runner_module
from pygpt_net.core.agents_v2.agents import AgentsV2
from pygpt_net.core.agents_v2.runner import Runner


class FakeEmitter:
    instances = []

    def __init__(self, context, extra, signals):
        self.context = context
        self.extra = extra
        self.signals = signals
        self.finished = []
        self.clear_count = 0
        FakeEmitter.instances.append(self)

    def clear_status(self):
        self.clear_count += 1

    def finish(self, final_answer=None):
        self.finished.append(final_answer)


def test_agents_v2_wrapper_constructs_runner_with_same_window():
    window = object()
    agents = AgentsV2(window)

    assert agents.window is window
    assert agents.runner.window is window


def test_agents_v2_runner_call_success_returns_true_and_clears_previous_error(monkeypatch):
    runner = Runner(SimpleNamespace())
    runner.last_error = RuntimeError("old")
    runner._run = AsyncMock(return_value=None)

    result = runner.call(SimpleNamespace(), {}, SimpleNamespace())

    assert result is True
    assert runner.get_error() is None
    runner._run.assert_awaited_once()


def test_agents_v2_runner_call_treats_cancelled_error_as_normal_control_flow(monkeypatch):
    FakeEmitter.instances.clear()
    monkeypatch.setattr(runner_module, "RuntimeEmitter", FakeEmitter)
    runner = Runner(SimpleNamespace())
    runner._run = AsyncMock(side_effect=asyncio.CancelledError())

    result = runner.call(SimpleNamespace(), {}, SimpleNamespace())

    emitter = FakeEmitter.instances[-1]
    assert result is True
    assert runner.get_error() is None
    assert emitter.clear_count == 1
    assert emitter.finished == [None]


def test_agents_v2_runner_call_logs_error_and_finishes_visible_response(monkeypatch):
    FakeEmitter.instances.clear()
    monkeypatch.setattr(runner_module, "RuntimeEmitter", FakeEmitter)
    window = MagicMock()
    runner = Runner(window)
    runner._run = AsyncMock(side_effect=RuntimeError("boom"))

    result = runner.call(SimpleNamespace(), {}, SimpleNamespace())

    emitter = FakeEmitter.instances[-1]
    assert result is True
    assert isinstance(runner.get_error(), RuntimeError)
    window.core.debug.log.assert_called_once()
    assert emitter.clear_count == 1
    assert emitter.finished == ["Agents v2: boom"]
