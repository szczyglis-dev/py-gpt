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
import asyncio
import threading
import time

import pytest
from unittest.mock import MagicMock
from PySide6.QtCore import QObject

# Use original event constants
from pygpt_net.core.events import KernelEvent, RenderEvent

# Dummy event and context classes
class DummyEvent:
    def __init__(self, name, data=None):
        self.name = name
        self.data = data if data is not None else {}

class DummyContext:
    def __init__(self, reply_context=None, agent_call=False):
        self.reply_context = reply_context
        self.agent_call = agent_call

# Minimal fake UI and components
class FakeTray:
    def __init__(self):
        self.icon = None
    def set_icon(self, icon):
        self.icon = icon

class FakeUI:
    def __init__(self):
        self.status_text = ""
        self._tray = FakeTray()
    def status(self, status):
        self.status_text = status
    def hide_loading(self):
        self.loading_hidden = True
    @property
    def tray(self):
        return self._tray

class FakeChatInput:
    def send(self, ctx, extra):
        return "input_sent"

class FakeChatResponse:
    def handle(self, ctx, extra, success):
        return f"response_handled_{success}"
    def failed(self, ctx, extra):
        return "response_failed"
    def begin(self, ctx, extra):
        return "append_begin"
    def append(self, ctx, extra):
        return "append_data"
    def end(self, ctx, extra):
        return "append_end"
    def live_append(self, ctx, extra):
        return "live_append"
    def live_clear(self, ctx, extra):
        return "live_clear"

class FakeChatCommon:
    def stop(self, exit):
        self.stopped = True

class FakeAgentLegacy:
    def enabled(self):
        return False

class FakeAgentExperts:
    def enabled(self):
        return False

class FakeAgent:
    def __init__(self):
        self.legacy = FakeAgentLegacy()
        self.experts = FakeAgentExperts()

class FakePlugins:
    def destroy(self):
        self.destroyed = True

class FakeAudio:
    def stop_audio(self):
        self.audio_stopped = True

class FakeController:
    def __init__(self):
        self.chat = type("FakeChat", (), {})()
        self.chat.input = FakeChatInput()
        self.chat.response = FakeChatResponse()
        self.chat.common = FakeChatCommon()
        self.agent = FakeAgent()
        self.audio = FakeAudio()
        self.plugins = FakePlugins()

class FakeBridge:
    def request(self, ctx, extra):
        return "requested"
    def request_next(self, ctx, extra):
        return "request_next"
    def call(self, ctx, extra):
        return "called"

class FakeCore:
    def __init__(self):
        self.bridge = FakeBridge()
        self.config = {"mode": "normal"}

# FakeWindow as a QObject subclass
class FakeWindow(QObject):
    def __init__(self):
        super().__init__(None)
        self.events = []
        self.ui = FakeUI()
        self.controller = FakeController()
        self.core = FakeCore()
    def dispatch(self, event):
        self.events.append(event)

# Helper for event equality comparisons
class AnyEvent:
    def __init__(self, name):
        self.name = name
    def __eq__(self, other):
        return hasattr(other, "name") and other.name == self.name

# Fixtures
@pytest.fixture
def fake_window():
    return FakeWindow()

@pytest.fixture
def kernel(fake_window):
    from pygpt_net.controller.kernel import Kernel  # Assumes Kernel class is defined in module "kernel"
    return Kernel(window=fake_window)

# Tests
def test_init(kernel):
    kernel.last_stack = ["dummy"]
    kernel.halt = True
    kernel.busy = True
    kernel.status = "old"
    kernel.init()
    assert kernel.last_stack == []
    assert kernel.halt is False
    assert kernel.busy is False
    assert kernel.status == ""
    assert kernel.state == kernel.STATE_IDLE

def test_listener_not_stopped(kernel, fake_window):
    kernel.halt = False
    event = DummyEvent("something")
    fake_window.events = []
    kernel.listener(event)
    assert fake_window.events[-1] == event

def test_listener_stopped(kernel, fake_window):
    kernel.halt = True
    fake_window.events = []
    event = DummyEvent("other_event")
    kernel.listener(event)
    assert fake_window.events == []
    # INPUT_USER is allowed even when halted.
    event2 = DummyEvent(KernelEvent.INPUT_USER)
    kernel.listener(event2)
    assert fake_window.events[-1] == event2

def test_handle_input(kernel, fake_window):
    ctx = DummyContext()
    extra = {"data": 123}
    event = DummyEvent(KernelEvent.INPUT_USER, {"context": ctx, "extra": extra})
    kernel.halt = False
    kernel.handle(event)
    assert event.data.get("response") == "input_sent"

def test_handle_queue_request_next(kernel, fake_window):
    ctx = DummyContext()
    extra = {"info": "next"}
    event = DummyEvent(KernelEvent.REQUEST_NEXT, {"context": ctx, "extra": extra})
    kernel.halt = False
    kernel.handle(event)
    assert event.data.get("response") == "request_next"

@pytest.mark.parametrize("evt_name,expected", [
    (KernelEvent.CALL, "called"),
    (KernelEvent.FORCE_CALL, "called")
])
def test_handle_call(kernel, fake_window, evt_name, expected):
    ctx = DummyContext()
    extra = {"info": "call"}
    event = DummyEvent(evt_name, {"context": ctx, "extra": extra})
    kernel.halt = False
    kernel.handle(event)
    assert event.data.get("response") == expected

def test_reply_add(kernel, fake_window):
    ctx = DummyContext()
    extra = {"reply": "data"}
    event = DummyEvent(KernelEvent.REPLY_ADD, {"context": ctx, "extra": extra})
    kernel.halt = False
    kernel.replies.add = MagicMock(return_value="reply_added")
    kernel.handle(event)
    assert event.data.get("response") == "reply_added"

def test_reply_return(kernel, fake_window):
    ctx = DummyContext()
    extra = {"reply": "data"}
    event = DummyEvent(KernelEvent.REPLY_RETURN, {"context": ctx, "extra": extra})
    kernel.halt = False


@pytest.mark.parametrize("evt_name,expected", [
    (KernelEvent.RESPONSE_OK, "response_handled_True"),
    (KernelEvent.RESPONSE_ERROR, "response_handled_False"),
    (KernelEvent.RESPONSE_FAILED, "response_failed"),
    (KernelEvent.APPEND_BEGIN, "append_begin"),
    (KernelEvent.APPEND_DATA, "append_data"),
    (KernelEvent.APPEND_END, "append_end"),
    (KernelEvent.LIVE_APPEND, "live_append"),
    (KernelEvent.LIVE_CLEAR, "live_clear")
])
def test_output(kernel, fake_window, evt_name, expected):
    ctx = DummyContext()
    extra = {"out": "value"}
    event = DummyEvent(evt_name, {"context": ctx, "extra": extra})
    kernel.halt = False
    resp = kernel.output(ctx, extra, event)
    assert resp == expected

def test_restart(kernel, fake_window):
    kernel.last_stack = ["dummy"]
    fake_window.events.clear()
    kernel.restart()
    names = [e.name for e in fake_window.events]
    assert KernelEvent.RESTART in names
    assert kernel.last_stack == []
    assert kernel.halt is False

def test_terminate(kernel, fake_window):
    fake_window.dispatch = MagicMock()
    fake_window.ui.hide_loading = MagicMock()
    fake_window.controller.plugins.destroy = MagicMock()
    fake_window.controller.chat.common.stop = MagicMock()
    fake_window.controller.audio.stop_audio = MagicMock()
    kernel.terminate()
    fake_window.dispatch.assert_called_with(AnyEvent(KernelEvent.TERMINATE))
#    fake_window.ui.hide_loading.assert_called_once()
    fake_window.controller.plugins.destroy.assert_called_once()
    fake_window.controller.chat.common.stop.assert_called_once()
    fake_window.controller.audio.stop_audio.assert_called_once()

def test_stop(kernel, fake_window):
    fake_window.dispatch = MagicMock()
    fake_window.controller.chat.common.stop = MagicMock()
    fake_window.controller.audio.stop_audio = MagicMock()
    from pygpt_net import utils
    original_trans = utils.trans
    utils.trans = lambda msg: msg
    kernel.stop(exit=False)
    assert kernel.halt is True
    fake_window.controller.chat.common.stop.assert_called_with(exit=False)
    fake_window.controller.audio.stop_audio.assert_called_once()
    dispatched = [e.name for e in fake_window.events]
    #assert KernelEvent.STOP in dispatched
    utils.trans = original_trans

def test_set_state_busy(kernel, fake_window):
    event = DummyEvent(KernelEvent.STATE_BUSY, {"msg": "busy msg"})
    fake_window.events.clear()
    kernel.set_state(event)
    assert kernel.busy is True
    assert kernel.state == kernel.STATE_BUSY
    assert fake_window.ui.tray.icon == kernel.STATE_BUSY
    names = [e.name for e in fake_window.events]
    assert RenderEvent.STATE_BUSY in names
    assert kernel.status == "busy msg"

def test_set_state_idle(kernel, fake_window):
    event = DummyEvent(KernelEvent.STATE_IDLE, {})
    fake_window.events.clear()
    kernel.set_state(event)
    assert kernel.busy is False
    assert kernel.state == kernel.STATE_IDLE
    assert fake_window.ui.tray.icon == kernel.STATE_IDLE
    names = [e.name for e in fake_window.events]
    assert RenderEvent.STATE_IDLE in names

def test_set_state_error(kernel, fake_window):
    event = DummyEvent(KernelEvent.STATE_ERROR, {"msg": "error occurred"})
    fake_window.events.clear()
    kernel.set_state(event)
    assert kernel.busy is False
    assert kernel.state == kernel.STATE_ERROR
    assert fake_window.ui.tray.icon == kernel.STATE_ERROR
    names = [e.name for e in fake_window.events]
    assert RenderEvent.STATE_ERROR in names
    assert kernel.status == "error occurred"

def test_set_status(kernel, fake_window):
    kernel.set_status("new status")
    assert kernel.status == "new status"
    assert fake_window.ui.status_text == "new status"

def test_resume_and_stopped(kernel):
    kernel.halt = True
    kernel.resume()
    assert kernel.halt is False
    assert kernel.stopped() is False

def test_async_allowed(kernel, fake_window):
    ctx = DummyContext(agent_call=False)
    fake_window.core.config["mode"] = "normal"
    allowed = kernel.async_allowed(ctx)
    assert allowed is True
    ctx.agent_call = True
    allowed = kernel.async_allowed(ctx)
    assert allowed is False
    ctx.agent_call = False
    fake_window.core.config["mode"] = "agent"
    allowed = kernel.async_allowed(ctx)
    assert allowed is False
    fake_window.core.config["mode"] = "normal"
    fake_window.controller.agent.legacy.enabled = lambda: True
    allowed = kernel.async_allowed(ctx)
    assert allowed is False
    fake_window.controller.agent.legacy.enabled = lambda: False
    fake_window.controller.agent.experts.enabled = lambda: True
    allowed = kernel.async_allowed(ctx)
    assert allowed is False

def test_is_threaded(kernel, fake_window):
    fake_window.core.config["mode"] = "agent_llama"
    assert kernel.is_threaded() is True
    fake_window.core.config["mode"] = "normal"
    assert kernel.is_threaded() is False

def test_is_main_thread(kernel):
    assert kernel.is_main_thread() is True