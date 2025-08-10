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

import pytest
from types import SimpleNamespace
from unittest.mock import Mock
from pygpt_net.core.bridge import BridgeWorker
from pygpt_net.core.types import (
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_ASSISTANT,
)
from pygpt_net.core.events import KernelEvent, Event


class CtxObj:
    def __init__(self, reply=False, meta=None):
        self.reply = reply
        self.meta = meta
        self.hidden_input = None


class ContextObj:
    def __init__(self):
        self.mode = None
        self.ctx = CtxObj()
        self.system_prompt = ""
        self.prompt = ""
        self.history = []


class AttachmentStub:
    def __init__(self, has_context=True, context_value="", mode_value="query"):
        self._has = has_context
        self._context = context_value
        self._mode = mode_value
        self.MODE_QUERY_CONTEXT = "query"
    def has_context(self, meta):
        return self._has
    def get_context(self, ctx, history):
        return self._context
    def get_mode(self):
        return self._mode


def test_init_defaults():
    w = BridgeWorker(1, 2, key="v")
    assert w.args == (1, 2)
    assert w.kwargs == {"key": "v"}
    assert w.window is None
    assert w.context is None
    assert w.extra is None
    assert w.mode is None


def test_handle_post_prompt_async_and_end():
    worker = BridgeWorker()
    window = SimpleNamespace()
    def dispatch_capture(event):
        event.data["value"] = "modified"
        window.last_event = event
    window.dispatch = dispatch_capture
    ctx = ContextObj()
    ctx.mode = "m"
    ctx.ctx.reply = True
    ctx.system_prompt = "orig"
    worker.window = window
    worker.context = ctx
    worker.handle_post_prompt_async()
    assert worker.context.system_prompt == "modified"
    assert hasattr(window, "last_event")
    assert window.last_event.name == Event.POST_PROMPT_ASYNC
    worker.context.system_prompt = "orig2"
    worker.handle_post_prompt_end()
    assert worker.context.system_prompt == "modified"
    assert window.last_event.name == Event.POST_PROMPT_END


def test_handle_additional_context_no_ctx():
    worker = BridgeWorker()
    worker.window = SimpleNamespace(controller=SimpleNamespace(chat=SimpleNamespace(attachment=AttachmentStub())))
    ctx = ContextObj()
    ctx.ctx = None
    ctx.prompt = "p"
    worker.context = ctx
    worker.handle_additional_context()
    assert worker.context.prompt == "p"


def test_handle_additional_context_meta_none():
    worker = BridgeWorker()
    attachment = AttachmentStub(has_context=True, context_value="CTX", mode_value="query")
    worker.window = SimpleNamespace(controller=SimpleNamespace(chat=SimpleNamespace(attachment=attachment)))
    ctx = ContextObj()
    ctx.ctx.meta = None
    ctx.prompt = "p"
    worker.context = ctx
    worker.handle_additional_context()
    assert worker.context.prompt == "p"
    assert ctx.ctx.hidden_input is None


def test_handle_additional_context_has_no_context():
    worker = BridgeWorker()
    attachment = AttachmentStub(has_context=False)
    worker.window = SimpleNamespace(controller=SimpleNamespace(chat=SimpleNamespace(attachment=attachment)))
    ctx = ContextObj()
    ctx.ctx.meta = "m"
    ctx.prompt = "p"
    worker.context = ctx
    worker.handle_additional_context()
    assert worker.context.prompt == "p"
    assert ctx.ctx.hidden_input is None


def test_handle_additional_context_empty_ad_context():
    worker = BridgeWorker()
    attachment = AttachmentStub(has_context=True, context_value="", mode_value="query")
    worker.window = SimpleNamespace(controller=SimpleNamespace(chat=SimpleNamespace(attachment=attachment)))
    ctx = ContextObj()
    ctx.ctx.meta = "m"
    ctx.prompt = "p"
    worker.context = ctx
    worker.handle_additional_context()
    assert worker.context.prompt == "p"
    assert ctx.ctx.hidden_input is None


def test_handle_additional_context_query_mode_sets_hidden_input():
    worker = BridgeWorker()
    attachment = AttachmentStub(has_context=True, context_value="ADCTX", mode_value="query")
    worker.window = SimpleNamespace(controller=SimpleNamespace(chat=SimpleNamespace(attachment=attachment)))
    ctx = ContextObj()
    ctx.ctx.meta = "m"
    ctx.prompt = "p"
    worker.context = ctx
    worker.handle_additional_context()
    assert worker.context.prompt.endswith("\n\nADCTX")
    assert ctx.ctx.hidden_input == "ADCTX"


def test_handle_additional_context_agent_mode_sets_hidden_input():
    worker = BridgeWorker()
    attachment = AttachmentStub(has_context=True, context_value="ADCTX", mode_value="full")
    worker.window = SimpleNamespace(controller=SimpleNamespace(chat=SimpleNamespace(attachment=attachment)))
    ctx = ContextObj()
    ctx.ctx.meta = "m"
    ctx.prompt = "p"
    worker.context = ctx
    worker.mode = MODE_AGENT_LLAMA
    worker.handle_additional_context()
    assert worker.context.prompt.endswith("\n\nADCTX")
    assert ctx.ctx.hidden_input == "ADCTX"


def test_handle_additional_context_full_mode_no_hidden_input():
    worker = BridgeWorker()
    attachment = AttachmentStub(has_context=True, context_value="ADCTX", mode_value="full")
    worker.window = SimpleNamespace(controller=SimpleNamespace(chat=SimpleNamespace(attachment=attachment)))
    ctx = ContextObj()
    ctx.ctx.meta = "m"
    ctx.prompt = "p"
    worker.context = ctx
    worker.mode = None
    worker.handle_additional_context()
    assert worker.context.prompt.endswith("\n\nADCTX")
    assert ctx.ctx.hidden_input is None


def test_cleanup_disconnect_and_reset():
    worker = BridgeWorker()
    mock_response = Mock()
    worker.signals = SimpleNamespace(response=mock_response)
    worker.window = object()
    worker.context = object()
    worker.extra = {"a": 1}
    worker.args = (1,)
    worker.kwargs = {"k": 2}
    worker.cleanup()
    assert worker.window is None
    assert worker.context is None
    assert worker.extra is None
    assert worker.args is None
    assert worker.kwargs is None


def test_run_langchain_emits_failed():
    worker = BridgeWorker()
    worker.mode = MODE_LANGCHAIN
    worker.window = SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(info=Mock())))
    worker.context = ContextObj()
    worker.extra = {}
    mock_response = Mock()
    worker.signals = SimpleNamespace(response=mock_response)
    worker.handle_post_prompt_async = Mock()
    worker.handle_additional_context = Mock()
    worker.handle_post_prompt_end = Mock()
    worker.run()
    mock_response.emit.assert_called_once()
    event = mock_response.emit.call_args[0][0]
    assert isinstance(event, KernelEvent)
    assert event.name == KernelEvent.RESPONSE_FAILED
    assert isinstance(event.data["extra"]["error"], Exception)


def test_run_llama_index_emits_ok():
    worker = BridgeWorker()
    worker.mode = MODE_LLAMA_INDEX
    worker.window = SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(info=Mock()),
                                                      idx=SimpleNamespace(chat=SimpleNamespace(call=Mock(return_value=True)))))
    worker.context = ContextObj()
    worker.extra = {}
    mock_response = Mock()
    mock_response.disconnect = Mock()
    worker.signals = SimpleNamespace(response=mock_response)
    worker.handle_post_prompt_async = Mock()
    worker.handle_additional_context = Mock()
    worker.handle_post_prompt_end = Mock()
    worker.run()
    mock_response.emit.assert_called_once()
    event = mock_response.emit.call_args[0][0]
    assert isinstance(event, KernelEvent)
    assert event.name == KernelEvent.RESPONSE_OK


def test_run_agent_runner_true_no_emit():
    worker = BridgeWorker()
    worker.mode = MODE_AGENT_LLAMA
    runner = SimpleNamespace(call=Mock(return_value=True), get_error=Mock(return_value="err"))
    worker.window = SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(info=Mock()),
                                                        agents=SimpleNamespace(runner=runner)))
    worker.context = ContextObj()
    worker.extra = {}
    mock_response = Mock()
    mock_response.disconnect = Mock()
    worker.signals = SimpleNamespace(response=mock_response)
    worker.handle_post_prompt_async = Mock()
    worker.handle_additional_context = Mock()
    worker.handle_post_prompt_end = Mock()
    worker.run()
    mock_response.emit.assert_not_called()
    assert worker.window is None


def test_run_agent_runner_false_emits_error():
    worker = BridgeWorker()
    worker.mode = MODE_AGENT_OPENAI
    runner = SimpleNamespace(call=Mock(return_value=False), get_error=Mock(return_value="agent error"))
    worker.window = SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(info=Mock()),
                                                        agents=SimpleNamespace(runner=runner)))
    worker.context = ContextObj()
    worker.extra = {}
    mock_response = Mock()
    mock_response.disconnect = Mock()
    worker.signals = SimpleNamespace(response=mock_response)
    worker.handle_post_prompt_async = Mock()
    worker.handle_additional_context = Mock()
    worker.handle_post_prompt_end = Mock()
    worker.run()
    mock_response.emit.assert_called_once()
    event = mock_response.emit.call_args[0][0]
    assert isinstance(event, KernelEvent)
    assert event.name == KernelEvent.RESPONSE_ERROR
    assert event.data["extra"]["error"] == "agent error"


def test_run_loop_next_true_no_emit():
    worker = BridgeWorker()
    worker.mode = "loop_next"
    loop = SimpleNamespace(run_next=Mock(return_value=True))
    runner = SimpleNamespace(loop=loop, get_error=Mock(return_value="err"))
    worker.window = SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(info=Mock()),
                                                        agents=SimpleNamespace(runner=runner)))
    worker.context = ContextObj()
    worker.extra = {}
    mock_response = Mock()
    mock_response.disconnect = Mock()
    worker.signals = SimpleNamespace(response=mock_response)
    worker.handle_post_prompt_async = Mock()
    worker.handle_additional_context = Mock()
    worker.handle_post_prompt_end = Mock()
    worker.run()
    mock_response.emit.assert_not_called()


def test_run_gpt_call_exception_emits_failed():
    worker = BridgeWorker()
    worker.mode = "other"
    def raise_err(context, extra):
        raise ValueError("boom")
    worker.window = SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(info=Mock()),
                                                      gpt=SimpleNamespace(call=raise_err)))
    worker.context = ContextObj()
    worker.extra = {}
    mock_response = Mock()
    mock_response.disconnect = Mock()
    worker.signals = SimpleNamespace(response=mock_response)
    worker.handle_post_prompt_async = Mock()
    worker.handle_additional_context = Mock()
    worker.handle_post_prompt_end = Mock()
    worker.run()
    mock_response.emit.assert_called_once()
    event = mock_response.emit.call_args[0][0]
    assert isinstance(event, KernelEvent)
    assert event.name == KernelEvent.RESPONSE_FAILED
    assert isinstance(event.data["extra"]["error"], ValueError)


def test_run_gpt_call_result_emits_ok_or_error():
    worker = BridgeWorker()
    worker.mode = "other"
    worker.window = SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(info=Mock()),
                                                      gpt=SimpleNamespace(call=Mock(return_value=False))))
    worker.context = ContextObj()
    worker.extra = {}
    mock_response = Mock()
    mock_response.disconnect = Mock()
    worker.signals = SimpleNamespace(response=mock_response)
    worker.handle_post_prompt_async = Mock()
    worker.handle_additional_context = Mock()
    worker.handle_post_prompt_end = Mock()
    worker.run()
    event = mock_response.emit.call_args[0][0]
    assert isinstance(event, KernelEvent)
    assert event.name == KernelEvent.RESPONSE_ERROR
    mock_response.reset_mock()