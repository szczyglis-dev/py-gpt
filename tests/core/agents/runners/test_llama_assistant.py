#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.03 14:00:00                  #
# ================================================== #

import pytest
from unittest.mock import MagicMock
from pygpt_net.core.events import KernelEvent
from pygpt_net.core.agents.runners.llama_assistant import LlamaAssistant

# Test when runner is stopped initially
def test_run_stopped_initial(monkeypatch):
    runner = LlamaAssistant(window=None)
    monkeypatch.setattr(runner, "is_stopped", lambda: True)

    fake_agent = MagicMock()
    fake_agent.thread_id = "thread1"
    fake_agent.assistant = MagicMock(id="assistant1", model="model1")
    fake_ctx = MagicMock()
    fake_ctx.meta = type("DummyMeta", (), {})()  # dummy meta attribute
    fake_ctx.input = "test input"
    fake_signals = MagicMock()

    result = runner.run(fake_agent, fake_ctx, "prompt", fake_signals, verbose=False)
    assert result is True
    fake_agent.chat.assert_not_called()


# Test normal run (no stop)
def test_run_normal(monkeypatch):
    runner = LlamaAssistant(window=None)
    monkeypatch.setattr(runner, "is_stopped", lambda: False)
    monkeypatch.setattr(runner, "prepare_input", lambda prompt: "prepared " + prompt)

    # Use a fake response context with an extra dict
    fake_response_ctx = MagicMock()
    fake_response_ctx.extra = {}
    monkeypatch.setattr(runner, "add_ctx", lambda ctx: fake_response_ctx)

    busy_called = False
    def fake_set_busy(signals):
        nonlocal busy_called
        busy_called = True
    monkeypatch.setattr(runner, "set_busy", fake_set_busy)

    sent_response = []
    def fake_send_response(ctx, signals, event):
        sent_response.append((ctx, signals, event))
    monkeypatch.setattr(runner, "send_response", fake_send_response)

    fake_agent = MagicMock()
    fake_agent.thread_id = "thread42"
    fake_agent.assistant = MagicMock(id="assistant42", model="gpt42")
    fake_agent.chat.return_value = "agent response"

    class DummyMeta:
        pass
    dummy_meta = DummyMeta()
    setattr(dummy_meta, "thread", None)
    setattr(dummy_meta, "assistant", None)

    fake_ctx = MagicMock()
    fake_ctx.meta = dummy_meta
    fake_ctx.input = "user input"
    fake_ctx.thread = None

    fake_signals = MagicMock()
    result = runner.run(fake_agent, fake_ctx, "original prompt", fake_signals, verbose=True)

    assert result is True
    assert fake_ctx.meta.thread == "thread42"
    assert fake_ctx.meta.assistant == "assistant42"
    assert fake_ctx.thread == "thread42"
    fake_agent.chat.assert_called_with("prepared original prompt")
    fake_response_ctx.set_input.assert_called_with("Assistant")
    fake_response_ctx.set_output.assert_called_with("agent response")
    assert fake_response_ctx.extra.get("agent_output") is True
    assert fake_response_ctx.extra.get("agent_finish") is True

    assert busy_called is True
    assert len(sent_response) == 1
    ctx_sent, signals_sent, event = sent_response[0]
    assert ctx_sent == fake_response_ctx
    assert signals_sent == fake_signals
    assert event == KernelEvent.APPEND_DATA


# Test when runner is stopped after setting metadata
def test_run_stopped_after_meta(monkeypatch):
    runner = LlamaAssistant(window=None)
    call_count = 0
    def fake_is_stopped():
        nonlocal call_count
        call_count += 1
        return call_count > 1
    monkeypatch.setattr(runner, "is_stopped", fake_is_stopped)

    fake_agent = MagicMock()
    fake_agent.thread_id = "threadX"
    fake_agent.assistant = MagicMock(id="assistantX", model="modelX")

    class DummyMeta:
        pass
    dummy_meta = DummyMeta()
    setattr(dummy_meta, "thread", None)
    setattr(dummy_meta, "assistant", None)

    fake_ctx = MagicMock()
    fake_ctx.meta = dummy_meta
    fake_ctx.input = "input text"
    fake_ctx.thread = None

    fake_signals = MagicMock()
    result = runner.run(fake_agent, fake_ctx, "some prompt", fake_signals, verbose=False)

    assert result is True
    fake_agent.chat.assert_not_called()