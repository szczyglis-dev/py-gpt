#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.10 00:00:00                  #
# ================================================== #

import importlib
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

mod = importlib.import_module("pygpt_net.core.bridge")

Bridge = mod.Bridge

class DummyCtx:
    def __init__(self):
        self.input = None
        self.output = None

class DummyContext:
    def __init__(self, mode=None, model=None):
        self.ctx = DummyCtx()
        self.prompt = "hello"
        self.mode = mode
        self.model = model
        self.idx = None
        self.idx_mode = None
        self.stream = True
        self.force = False
        self.parent_mode = None
    def to_dict(self):
        return {"prompt": self.prompt}

def make_window():
    window = SimpleNamespace()
    window.STATE_BUSY = "BUSY"
    window.stateChanged = SimpleNamespace()
    window.stateChanged.emit = Mock()
    window.threadpool = SimpleNamespace()
    window.threadpool.start = Mock()
    window.controller = SimpleNamespace()
    window.controller.kernel = SimpleNamespace()
    window.controller.kernel.stopped = Mock(return_value=False)
    window.controller.kernel.listener = Mock()
    window.controller.mode = SimpleNamespace()
    window.controller.mode.switch_inline = Mock(side_effect=lambda mode, ctx, prompt: mode)
    window.controller.model = SimpleNamespace()
    window.controller.model.switch_inline = Mock(side_effect=lambda mode, model: model)
    window.core = SimpleNamespace()
    window.core.debug = SimpleNamespace()
    window.core.debug.info = Mock()
    window.core.debug.enabled = Mock(return_value=False)
    window.core.debug.debug = Mock()
    window.core.debug.error = Mock()
    window.core.config = SimpleNamespace()
    window.core.config.get = Mock(return_value=None)
    window.core.config.has = Mock(return_value=False)
    window.core.models = SimpleNamespace()
    window.core.models.get_supported_mode = Mock(return_value=None)
    window.core.idx = SimpleNamespace()
    window.core.idx.chat = SimpleNamespace()
    window.core.idx.chat.is_stream_allowed = Mock(return_value=True)
    window.core.idx.chat.chat = Mock(return_value=False)
    window.core.agents = SimpleNamespace()
    window.core.agents.legacy = SimpleNamespace()
    window.core.agents.legacy.get_mode = Mock(return_value=None)
    window.core.agents.legacy.get_idx = Mock(return_value=None)
    window.core.experts = SimpleNamespace()
    window.core.experts.get_mode = Mock(return_value=None)
    window.core.api = SimpleNamespace()
    window.core.api.openai = SimpleNamespace()
    window.core.api.openai.quick_call = Mock(return_value="quick_result")
    return window

def test_request_returns_false_when_kernel_stopped():
    window = make_window()
    window.controller.kernel.stopped = Mock(return_value=True)
    b = Bridge(window)
    ctx = DummyContext(mode=mod.MODE_CHAT)
    assert b.request(ctx) is False

def test_request_runs_worker_sync_when_mode_in_sync_modes(monkeypatch):
    window = make_window()
    window.core.debug.enabled = Mock(return_value=False)
    b = Bridge(window)
    ctx = DummyContext(mode=mod.MODE_ASSISTANT)
    worker = SimpleNamespace()
    worker.run = Mock()
    monkeypatch.setattr(mod.Bridge, "get_worker", lambda self: worker)
    monkeypatch.setattr(mod.Bridge, "apply_rate_limit", lambda self: None)
    res = b.request(ctx, extra={"a": 1})
    assert res is True
    worker.run.assert_called_once()
    assert b.last_context() is ctx

def test_request_starts_worker_async_when_mode_not_in_sync_modes(monkeypatch):
    window = make_window()
    window.core.debug.enabled = Mock(return_value=False)
    b = Bridge(window)
    ctx = DummyContext(mode=mod.MODE_CHAT)
    worker = SimpleNamespace()
    worker.run = Mock()
    monkeypatch.setattr(mod.Bridge, "get_worker", lambda self: worker)
    monkeypatch.setattr(mod.Bridge, "apply_rate_limit", lambda self: None)
    res = b.request(ctx, extra=None)
    assert res is True
    window.threadpool.start.assert_called_once_with(worker)

def test_request_agent_mode_uses_sub_mode_and_idx(monkeypatch):
    window = make_window()
    window.core.agents.legacy.get_mode = Mock(return_value=mod.MODE_LLAMA_INDEX)
    window.core.agents.legacy.get_idx = Mock(return_value="IDX123")
    b = Bridge(window)
    ctx = DummyContext(mode=mod.MODE_AGENT)
    worker = SimpleNamespace()
    monkeypatch.setattr(mod.Bridge, "get_worker", lambda self: worker)
    monkeypatch.setattr(mod.Bridge, "apply_rate_limit", lambda self: None)
    res = b.request(ctx)
    assert res is True
    assert ctx.parent_mode == mod.MODE_AGENT
    assert ctx.idx == "IDX123"
    assert ctx.idx_mode == mod.MODE_CHAT or ctx.idx_mode is None

def test_request_switches_model_when_not_supported(monkeypatch):
    window = make_window()
    class FakeModel:
        def is_supported(self, mode):
            return False
    fm = FakeModel()
    window.core.models.get_supported_mode = Mock(return_value=mod.MODE_LLAMA_INDEX)
    window.core.idx.chat.is_stream_allowed = Mock(return_value=False)
    b = Bridge(window)
    ctx = DummyContext(mode=mod.MODE_CHAT, model=fm)
    monkeypatch.setattr(mod.Bridge, "get_worker", lambda self: SimpleNamespace(run=Mock()))
    monkeypatch.setattr(mod.Bridge, "apply_rate_limit", lambda self: None)
    res = b.request(ctx)
    assert res is True
    assert ctx.idx is None
    assert ctx.stream is False

def test_request_next_stopped_and_started(monkeypatch):
    window = make_window()
    b = Bridge(window)
    ctx = DummyContext(mode=mod.MODE_CHAT)
    window.controller.kernel.stopped = Mock(return_value=True)
    assert b.request_next(ctx) is False
    window.controller.kernel.stopped = Mock(return_value=False)
    worker = SimpleNamespace()
    monkeypatch.setattr(mod.Bridge, "get_worker", lambda self: worker)
    res = b.request_next(ctx, extra=None)
    assert res is True
    assert worker.mode == "loop_next"
    window.threadpool.start.assert_called_once_with(worker)

def test_call_returns_empty_when_stopped_and_not_forced():
    window = make_window()
    b = Bridge(window)
    ctx = DummyContext()
    ctx.force = False
    window.controller.kernel.stopped = Mock(return_value=True)
    assert b.call(ctx) == ""

def test_call_uses_llama_index_quick_call(monkeypatch):
    window = make_window()
    class FakeModel:
        def is_supported(self, mode):
            if mode == mod.MODE_CHAT:
                return False
            if mode == mod.MODE_LLAMA_INDEX:
                return True
            return False
    fm = FakeModel()
    ctx = DummyContext(mode=mod.MODE_CHAT, model=fm)
    ctx.ctx.input = None
    ctx.ctx.output = "ANSWER"
    def fake_chat(context, extra, disable_cmd):
        context.ctx.output = "ANSWER"
        return True
    window.core.idx.chat.chat = Mock(side_effect=fake_chat)
    b = Bridge(window)
    res = b.call(ctx, extra={"k": "v"})
    assert res == "ANSWER"
    assert b.last_context_quick() is ctx
    assert ctx.stream is False

def test_call_switches_to_research_and_uses_quick_call(monkeypatch):
    window = make_window()
    class FakeModel:
        def is_supported(self, mode):
            if mode == mod.MODE_CHAT:
                return False
            if mode == mod.MODE_RESEARCH:
                return True
            return False
    fm = FakeModel()
    ctx = DummyContext(mode=None, model=fm)
    window.core.api.openai.quick_call = Mock(return_value="GPT_OK")
    b = Bridge(window)
    res = b.call(ctx, extra={})
    assert res == "GPT_OK"
    assert ctx.mode == mod.MODE_RESEARCH

def test_call_default_quick_call_invoked():
    window = make_window()
    b = Bridge(window)
    ctx = DummyContext(mode=mod.MODE_CHAT, model=None)
    window.core.api.openai.quick_call = Mock(return_value="DEFAULT")
    res = b.call(ctx, extra={"x": 1})
    assert res == "DEFAULT"
    assert b.last_context_quick() is ctx

def test_get_worker_connects_signals(monkeypatch):
    window = make_window()
    class DummyResponse:
        def __init__(self):
            self.connect = Mock()
    class DummyWorker:
        def __init__(self):
            self.signals = SimpleNamespace(response=DummyResponse())
            self.window = None
    monkeypatch.setattr(mod, "BridgeWorker", DummyWorker)
    b = Bridge(window)
    w = b.get_worker()
    assert w.window is window

def test_apply_rate_limit_no_limit(monkeypatch):
    window = make_window()
    window.core.config.has = Mock(return_value=False)
    b = Bridge(window)
    b.last_call = None
    called = []
    monkeypatch.setattr(mod.time, "sleep", Mock(side_effect=lambda s: called.append(s)))
    b.apply_rate_limit()
    assert called == []
    assert b.last_call is not None

def test_apply_rate_limit_with_sleep(monkeypatch):
    window = make_window()
    window.core.config.has = Mock(return_value=True)
    window.core.config.get = Mock(return_value="30")
    b = Bridge(window)
    now = mod.datetime.now()
    interval = mod.timedelta(minutes=1) / 30
    extra = mod.timedelta(seconds=0.5)
    b.last_call = now - interval + extra
    sleep_mock = Mock()
    monkeypatch.setattr(mod.time, "sleep", sleep_mock)
    window.core.debug.debug = Mock()
    b.apply_rate_limit()
    assert sleep_mock.call_count == 1
    sleep_arg = sleep_mock.call_args[0][0]
    assert sleep_arg == pytest.approx(extra.total_seconds(), rel=1e-3)
    window.core.debug.debug.assert_called()