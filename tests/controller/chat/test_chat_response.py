#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.14 01:00:00                  #
# ================================================== #

import importlib
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock
import pytest

response_mod = importlib.import_module("pygpt_net.controller.chat.response")
Response = response_mod.Response
from pygpt_net.core.types import MODE_AGENT_LLAMA, MODE_AGENT_OPENAI
from pygpt_net.core.events import RenderEvent, KernelEvent, AppEvent


def make_window():
    window = SimpleNamespace()
    window.update_status = Mock()
    window.dispatch = Mock()
    window.ui = SimpleNamespace()
    window.ui.dialogs = SimpleNamespace()
    window.ui.dialogs.alert = Mock()
    window.core = SimpleNamespace()
    window.core.ctx = MagicMock()
    window.core.presets = MagicMock()
    window.core.presets.update_and_save = Mock()
    window.core.config = MagicMock()
    window.controller = SimpleNamespace()
    window.controller.chat = MagicMock()
    window.controller.chat.log = Mock()
    window.controller.chat.log_ctx = Mock()
    window.controller.chat.output = MagicMock()
    window.controller.chat.output.not_stream_modes = []
    window.controller.chat.output.handle = Mock()
    window.controller.chat.output.post_handle = Mock()
    window.controller.chat.output.handle_end = Mock()
    window.controller.chat.handle_error = Mock()
    window.controller.chat.common = SimpleNamespace()
    window.controller.chat.common.lock_input = Mock()
    window.controller.chat.common.unlock_input = Mock()
    window.controller.kernel = Mock()
    window.controller.kernel.stopped = Mock(return_value=False)
    window.controller.ctx = MagicMock()
    window.controller.ctx.prepare_name = Mock()
    window.controller.ctx.update = Mock()
    window.controller.presets = MagicMock()
    window.controller.presets.get_current = Mock(return_value=None)
    window.controller.agent = MagicMock()
    window.controller.agent.llama = MagicMock()
    window.controller.agent.llama.on_finish = Mock()
    window.controller.agent.llama.on_end = Mock()
    window.core.ctx.update_item = Mock()
    window.core.ctx.add = Mock()
    window.core.ctx.set_last_item = Mock()
    window.core.ctx.replace = Mock()
    window.core.ctx.save = Mock()
    return window


class DummyCtx:
    def __init__(self):
        self.current = True
        self.output = ""
        self.msg_id = "mid"
        self.meta = None
        self.mode = "mode"
        self.reply = False
        self.internal = False
        self.prev_ctx = None
        self.extra = None
        self.from_previous = Mock()
        self.partial = False


def make_context_with_prev(prev_current=True):
    ctx = DummyCtx()
    prev = SimpleNamespace()
    prev.current = prev_current
    prev.mode = "prev_mode"
    prev.from_previous = Mock()
    prev.output = ""
    prev.msg_id = "prev_mid"
    prev.reply = False
    prev.internal = False
    prev.extra = None
    ctx.prev_ctx = prev
    return ctx


def test_init_sets_window():
    window = make_window()
    r = Response(window)
    assert r.window is window


def test_begin_locks_input_and_updates_status():
    window = make_window()
    r = Response(window)
    ctx = SimpleNamespace()
    extra = {"msg": "starting"}
    r.begin(ctx, extra)
    window.controller.chat.common.lock_input.assert_called_once()
    window.update_status.assert_called_once_with("starting")


def test_update_status_calls_update_status():
    window = make_window()
    r = Response(window)
    ctx = SimpleNamespace()
    extra = {"msg": "x"}
    r.update_status(ctx, extra)
    window.update_status.assert_called_once_with("x")


def test_live_append_dispatches_render_event():
    window = make_window()
    r = Response(window)
    ctx = DummyCtx()
    ctx.meta = {"id": "m"}
    context = SimpleNamespace(ctx=ctx)
    extra = {"chunk": "c", "begin": True}
    r.live_append(context, extra)
    assert window.dispatch.called
    ev = window.dispatch.call_args[0][0]
    assert isinstance(ev, RenderEvent)


def test_live_clear_dispatches_render_event():
    window = make_window()
    r = Response(window)
    ctx = DummyCtx()
    ctx.meta = {"id": "m2"}
    context = SimpleNamespace(ctx=ctx)
    extra = {}
    r.live_clear(context, extra)
    assert window.dispatch.called
    ev = window.dispatch.call_args[0][0]
    assert isinstance(ev, RenderEvent)


def test_handle_status_false_with_error(monkeypatch):
    window = make_window()
    r = Response(window)
    ctx = DummyCtx()
    ctx.current = True
    context = SimpleNamespace(ctx=ctx, stream=False)
    extra = {"error": "boom", "mode": "chat"}
    window.controller.kernel.stopped.return_value = False
    r.handle(context, extra, status=False)
    window.controller.chat.log.assert_any_call("Bridge response: ERROR")
    window.ui.dialogs.alert.assert_called_once_with("boom")
    window.update_status.assert_called_once_with("boom")
    window.core.ctx.update_item.assert_called_with(ctx)
    window.controller.chat.common.unlock_input.assert_called()


def test_handle_status_false_without_error_uses_trans(monkeypatch):
    window = make_window()
    r = Response(window)
    ctx = DummyCtx()
    context = SimpleNamespace(ctx=ctx, stream=False)
    monkeypatch.setattr(response_mod, "trans", lambda k: "TRANSLATED")
    window.controller.kernel.stopped.return_value = False
    extra = {"mode": "chat"}
    r.handle(context, extra, status=False)
    window.ui.dialogs.alert.assert_called_once_with("TRANSLATED")
    window.update_status.assert_called_once_with("TRANSLATED")
    window.core.ctx.update_item.assert_called_with(ctx)


def test_handle_true_returns_early_if_kernel_stopped():
    window = make_window()
    r = Response(window)
    ctx = DummyCtx()
    ctx.current = True
    context = SimpleNamespace(ctx=ctx, stream=False)
    window.controller.kernel.stopped.return_value = True
    extra = {"mode": "chat"}
    r.handle(context, extra, status=True)
    window.controller.chat.log_ctx.assert_called_once_with(ctx, "output")
    assert ctx.current is True
    window.core.ctx.update_item.assert_not_called()


def test_handle_calls_output_handle_and_post_handle(monkeypatch):
    window = make_window()
    r = Response(window)
    ctx = DummyCtx()
    ctx.from_previous = Mock()
    context = SimpleNamespace(ctx=ctx, stream=False)
    extra = {"mode": "not_assistant", "reply": True, "internal": True}
    called = []
    def fake_post_handle(*args, **kwargs):
        called.append(True)
    r.post_handle = Mock(side_effect=fake_post_handle)
    window.controller.chat.output.handle = Mock()
    r.handle(context, extra, status=True)
    window.controller.chat.log_ctx.assert_called_once_with(ctx, "output")
    ctx.from_previous.assert_called_once()
    window.controller.chat.output.handle.assert_called()
    r.post_handle.assert_called_once()


def test_handle_stream_returns_early_when_stream_and_mode_not_in_not_stream_modes():
    window = make_window()
    r = Response(window)
    ctx = DummyCtx()
    context = SimpleNamespace(ctx=ctx, stream=True)
    extra = {"mode": "m"}
    window.controller.chat.output.not_stream_modes = []
    r.post_handle = Mock()
    r.handle(context, extra, status=True)
    r.post_handle.assert_not_called()


def test_post_handle_calls_output_methods():
    window = make_window()
    r = Response(window)
    ctx = DummyCtx()
    r.window = window
    r.post_handle(ctx, "mode_x", True, False, True)
    window.controller.chat.output.post_handle.assert_called_once_with(ctx, "mode_x", True, False, True)
    window.controller.chat.output.handle_end.assert_called_once_with(ctx, "mode_x")


def test_append_kernel_stopped_adds_closing_code(monkeypatch):
    window = make_window()
    r = Response(window)
    ctx = DummyCtx()
    ctx.output = "some code"
    ctx.msg_id = "foo"
    context = SimpleNamespace(ctx=ctx)
    window.controller.kernel.stopped.return_value = True
    monkeypatch.setattr(response_mod, "has_unclosed_code_tag", lambda x: True)
    r.append(context, {})
    assert ctx.output.endswith("\n```")
    assert ctx.msg_id is None
    window.core.ctx.add.assert_called_with(ctx)
    window.controller.ctx.prepare_name.assert_called_with(ctx)
    assert window.dispatch.call_count >= 2


def test_append_handles_previous_context(monkeypatch):
    window = make_window()
    r = Response(window)
    ctx = make_context_with_prev(prev_current=True)
    ctx.mode = "cur_mode"
    ctx.reply = False
    ctx.internal = False
    context = SimpleNamespace(ctx=ctx)
    window.controller.kernel.stopped.return_value = False
    window.controller.chat.output.handle = Mock()
    r.append(context, {})
    prev = ctx.prev_ctx
    assert prev.current is False
    window.core.ctx.update_item.assert_called()
    prev.from_previous.assert_called_once()
    window.controller.chat.output.handle.assert_called()


def test_append_agent_mode_updates_presets_and_calls_on_finish(monkeypatch):
    window = make_window()
    r = Response(window)
    ctx = DummyCtx()
    ctx_prev = DummyCtx()
    ctx.prev_ctx = DummyCtx()
    class Meta:
        def __init__(self):
            self.id = "meta1"
            self.assistant = "assistant-id"
    ctx.meta = Meta()
    ctx.mode = MODE_AGENT_LLAMA
    ctx.extra = {"agent_finish": True}
    context = SimpleNamespace(ctx=ctx)
    window.controller.presets.get_current.return_value = SimpleNamespace(assistant_id=None)
    window.controller.kernel.stopped.return_value = False
    window.controller.chat.output.handle = Mock()
    r.append(context, {})
    window.core.ctx.replace.assert_called_with(ctx.meta)
    window.core.ctx.save.assert_called_with("meta1")
    window.core.presets.update_and_save.assert_called()
    #window.controller.agent.llama.on_finish.assert_called_with(ctx)


def test_append_handles_output_exception(monkeypatch):
    window = make_window()
    r = Response(window)
    ctx = DummyCtx()
    ctx.mode = "m"
    context = SimpleNamespace(ctx=ctx, config=Mock())
    window.controller.kernel.stopped.return_value = False
    def raise_err(*args, **kwargs):
        raise RuntimeError("boom")
    window.controller.chat.output.handle = Mock(side_effect=raise_err)
    r.append(context, {})
    window.controller.chat.log.assert_called()
    window.controller.chat.handle_error.assert_called()


def test_end_updates_status_and_calls_agent_and_unlocks():
    window = make_window()
    r = Response(window)
    ctx = SimpleNamespace()
    context = SimpleNamespace(ctx=ctx)
    extra = {"msg": "done"}
    r.end(context, extra)
    window.update_status.assert_called_once_with("done")
    window.controller.agent.llama.on_end.assert_called_once()
    window.controller.chat.common.unlock_input.assert_called_once()
    assert window.dispatch.called
    ev = window.dispatch.call_args[0][0]
    assert isinstance(ev, KernelEvent)


def test_failed_logs_handles_and_unlocks_and_dispatches_error():
    window = make_window()
    r = Response(window)
    ctx = SimpleNamespace()
    context = SimpleNamespace(ctx=ctx)
    err = ValueError("err")
    extra = {"error": err}
    r.failed(context, extra)
    window.controller.chat.log.assert_called()
    window.controller.chat.handle_error.assert_called_with(err)
    window.controller.chat.common.unlock_input.assert_called_once()
    assert window.dispatch.called
    ev = window.dispatch.call_args[0][0]
    assert isinstance(ev, KernelEvent)