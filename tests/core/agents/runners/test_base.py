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
from pygpt_net.core.agents.runners.base import BaseRunner
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.bridge.worker import BridgeSignals

# Fixture to create a fake window with required helper chain.
@pytest.fixture
def fake_window():
    fake_helpers = MagicMock()
    fake_runner = MagicMock()
    fake_runner.helpers = fake_helpers
    fake_agents = MagicMock()
    fake_agents.runner = fake_runner
    fake_core = MagicMock()
    fake_core.agents = fake_agents
    fake_wnd = MagicMock()
    fake_wnd.core = fake_core
    return fake_wnd

def test_add_ctx(fake_window):
    ctx_item = MagicMock(spec=CtxItem)
    fake_window.core.agents.runner.helpers.add_ctx.return_value = ctx_item
    runner = BaseRunner(window=fake_window)
    result = runner.add_ctx(ctx_item, with_tool_outputs=True)
    fake_window.core.agents.runner.helpers.add_ctx.assert_called_once_with(
        from_ctx=ctx_item, with_tool_outputs=True
    )
    assert result == ctx_item

def test_add_next_ctx(fake_window):
    ctx_item = MagicMock(spec=CtxItem)
    fake_window.core.agents.runner.helpers.add_next_ctx.return_value = ctx_item
    runner = BaseRunner(window=fake_window)
    result = runner.add_next_ctx(ctx_item)
    fake_window.core.agents.runner.helpers.add_next_ctx.assert_called_once_with(
        from_ctx=ctx_item
    )
    assert result == ctx_item

def test_send_stream(fake_window):
    ctx = MagicMock(spec=CtxItem)
    signals = MagicMock(spec=BridgeSignals)
    runner = BaseRunner(window=fake_window)
    runner.send_stream(ctx, signals, begin=True)
    fake_window.core.agents.runner.helpers.send_stream.assert_called_once_with(
        ctx=ctx, signals=signals, begin=True
    )

def test_end_stream(fake_window):
    ctx = MagicMock(spec=CtxItem)
    signals = MagicMock(spec=BridgeSignals)
    runner = BaseRunner(window=fake_window)
    runner.end_stream(ctx, signals)
    fake_window.core.agents.runner.helpers.end_stream.assert_called_once_with(
        ctx=ctx, signals=signals
    )

def test_next_stream(fake_window):
    ctx = MagicMock(spec=CtxItem)
    signals = MagicMock(spec=BridgeSignals)
    runner = BaseRunner(window=fake_window)
    runner.next_stream(ctx, signals)
    fake_window.core.agents.runner.helpers.next_stream.assert_called_once_with(
        ctx=ctx, signals=signals
    )

def test_send_response(fake_window):
    ctx = MagicMock(spec=CtxItem)
    signals = MagicMock(spec=BridgeSignals)
    runner = BaseRunner(window=fake_window)
    runner.send_response(ctx, signals, event_name="event1", extra="data")
    fake_window.core.agents.runner.helpers.send_response.assert_called_once_with(
        ctx=ctx, signals=signals, event_name="event1", extra="data"
    )

def test_set_busy(fake_window):
    signals = MagicMock(spec=BridgeSignals)
    runner = BaseRunner(window=fake_window)
    runner.set_busy(signals, busy=True)
    fake_window.core.agents.runner.helpers.set_busy.assert_called_once_with(
        signals=signals, busy=True
    )

def test_set_idle(fake_window):
    signals = MagicMock(spec=BridgeSignals)
    runner = BaseRunner(window=fake_window)
    runner.set_idle(signals, idle=True)
    fake_window.core.agents.runner.helpers.set_idle.assert_called_once_with(
        signals=signals, idle=True
    )

def test_set_status(fake_window):
    signals = MagicMock(spec=BridgeSignals)
    runner = BaseRunner(window=fake_window)
    msg = "test status"
    runner.set_status(signals, msg)
    fake_window.core.agents.runner.helpers.set_status.assert_called_once_with(
        signals=signals, msg=msg
    )

def test_prepare_input(fake_window):
    runner = BaseRunner(window=fake_window)
    prompt = "hello"
    fake_window.core.agents.runner.helpers.prepare_input.return_value = "prepared"
    result = runner.prepare_input(prompt)
    fake_window.core.agents.runner.helpers.prepare_input.assert_called_once_with(
        prompt=prompt
    )
    assert result == "prepared"

def test_is_stopped(fake_window):
    runner = BaseRunner(window=fake_window)
    fake_window.core.agents.runner.helpers.is_stopped.return_value = True
    result = runner.is_stopped()
    fake_window.core.agents.runner.helpers.is_stopped.assert_called_once()
    assert result is True

def test_set_error(fake_window):
    runner = BaseRunner(window=fake_window)
    error = Exception("error")
    runner.set_error(error)
    fake_window.core.agents.runner.helpers.set_error.assert_called_once_with(
        error=error
    )

def test_get_error(fake_window):
    runner = BaseRunner(window=fake_window)
    error = Exception("error")
    fake_window.core.agents.runner.helpers.get_error.return_value = error
    result = runner.get_error()
    fake_window.core.agents.runner.helpers.get_error.assert_called_once()
    assert result == error

def test_extract_final_response(fake_window):
    runner = BaseRunner(window=fake_window)
    input_text = "response text"
    fake_window.core.agents.runner.helpers.extract_final_response.return_value = ("thought", "answer")
    thought, answer = runner.extract_final_response(input_text)
    fake_window.core.agents.runner.helpers.extract_final_response.assert_called_once_with(
        input_text=input_text
    )
    assert thought == "thought"
    assert answer == "answer"