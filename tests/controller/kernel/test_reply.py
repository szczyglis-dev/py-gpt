#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.23 15:00:00                  #
# ================================================== #
import json
import pytest
from unittest.mock import MagicMock
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.events import KernelEvent, RenderEvent
from pygpt_net.core.types import MODE_LLAMA_INDEX
from pygpt_net.controller.kernel.reply import Reply  # adjust to your module name if needed

# Fixture for a Reply instance with a mocked window tree.
@pytest.fixture
def reply_instance():
    window = MagicMock()
    window.core = MagicMock()
    window.core.debug = MagicMock()
    window.core.debug.info = MagicMock()
    window.core.debug.debug = MagicMock()
    window.core.debug.enabled.return_value = True
    window.core.config = MagicMock()
    window.core.config.get.side_effect = lambda key, default=None: {
         "ctx.use_extra": True,
         "mode": "normal_mode",
         "llama.idx.react": False,
         "log.events": True
    }.get(key, default)
    window.core.config.has.side_effect = lambda key: key == "log.events"
    window.update_status = MagicMock()
    window.dispatch = MagicMock()
    window.controller = MagicMock()
    window.controller.kernel = MagicMock()
    window.controller.kernel.async_allowed.return_value = False
    window.controller.kernel.is_threaded.return_value = False
    window.controller.agent = MagicMock()
    legacy = MagicMock()
    legacy.enabled.return_value = False
    window.controller.agent.legacy = legacy
    window.controller.files = MagicMock()
    window.controller.files.update_explorer = MagicMock()
    window.core.ctx = MagicMock()
    window.core.ctx.as_previous.return_value = "previous_ctx"
    window.core.ctx.update_item = MagicMock()

    reply = Reply(window)
    return reply, window

# Helper to create a fake context item.
def create_fake_ctx(agent_call=False, reply=True, results=None, pid=1,
                      internal=False, extra_ctx="extra", sub_call=False, meta_id=999):
    ctx = MagicMock()
    ctx.agent_call = agent_call
    ctx.reply = reply
    ctx.results = results if results is not None else [{"result": "ok"}]
    ctx.pid = pid
    ctx.internal = internal
    ctx.extra_ctx = extra_ctx
    ctx.sub_call = sub_call
    fake_meta = MagicMock()
    fake_meta.id = meta_id
    ctx.meta = fake_meta
    return ctx

# Test add when context.ctx is None.
def test_add_none_context(reply_instance):
    reply, window = reply_instance
    context = BridgeContext()
    context.ctx = None
    res = reply.add(context, extra={})
    assert res == []

# Test add with agent_call True.
def test_add_with_agent_call(reply_instance):
    reply, window = reply_instance
    fake_ctx = create_fake_ctx(agent_call=True, results=[{"result": "agent"}])
    context = BridgeContext()
    context.ctx = fake_ctx
    res = reply.add(context, extra={})
    # Should immediately return results for agent calls.
    assert res == [{"result": "agent"}]
    assert reply.reply_stack == []

# Test add with reply True and flush requested.
def test_add_with_reply_and_flush(reply_instance):
    reply, window = reply_instance
    fake_ctx = create_fake_ctx(agent_call=False, reply=True, pid=2,
                               results=[{"result": "reply"}], sub_call=True)
    context = BridgeContext()
    context.ctx = fake_ctx
    res = reply.add(context, extra={"flush": True})
    # After appending, results are cleared.
    assert res == []
    # flush should clear the stack
    assert reply.reply_stack == []
    assert reply.reply_ctx is None
    # flush dispatches two events (RenderEvent and KernelEvent)
    assert window.dispatch.call_count == 2
    # update_status is called twice: first with "" then with "..."
    assert window.update_status.call_count == 2

# Test add without flush (flush not triggered if async_allowed is False and flush flag missing).
def test_add_without_flush(reply_instance):
    reply, window = reply_instance
    fake_ctx = create_fake_ctx(agent_call=False, reply=True, pid=3, results=[{"result": "noflush"}])
    context = BridgeContext()
    context.ctx = fake_ctx
    res = reply.add(context, extra={})
    # After append, results are cleared.
    assert res == []
    # The reply_stack remains pending until flush is called.
    assert reply.reply_stack != []
    reply.clear()

# Test that flush does nothing if there is no pending context.
def test_flush_no_action(reply_instance):
    reply, window = reply_instance
    reply.reply_ctx = None
    reply.reply_stack = []
    reply.flush()
    window.dispatch.assert_not_called()

# Test flush when internal is True and legacy agent is enabled.
def test_flush_internal_legacy(reply_instance):
    reply, window = reply_instance
    fake_ctx = create_fake_ctx(internal=True)
    reply.reply_ctx = fake_ctx
    reply.reply_stack = [[{"result": "legacy"}]]
    window.controller.agent.legacy.enabled.return_value = True
    reply.flush()
    # Two dispatch events are expected.
    assert window.dispatch.call_count == 2

# Test flush branch with LlamaIndex agent.
def test_flush_mode_llama_index(reply_instance):
    reply, window = reply_instance
    fake_ctx = create_fake_ctx()
    reply.reply_ctx = fake_ctx
    reply.reply_stack = [[{"result": "llama"}]]
    # Override config to simulate LlamaIndex ReAct mode.
    window.core.config.get.side_effect = lambda key, default=None: {
         "ctx.use_extra": True,
         "mode": MODE_LLAMA_INDEX,
         "llama.idx.react": True,
         "log.events": True
    }.get(key, default)
    reply.flush()
    # Only the RenderEvent dispatch should occur.
    assert window.dispatch.call_count == 1

# Test on_post_response triggering file explorer update.
def test_on_post_response_update(reply_instance):
    reply, window = reply_instance
    fake_ctx = create_fake_ctx(agent_call=False)
    reply.on_post_response(fake_ctx, extra_data={"post_update": ["file_explorer"]})
    window.controller.files.update_explorer.assert_called_once()
    window.controller.files.update_explorer.reset_mock()
    # Passing extra data without "file_explorer" should not trigger update.
    reply.on_post_response(fake_ctx, extra_data={"post_update": ["other"]})
    window.controller.files.update_explorer.assert_not_called()

# Test clear method.
def test_clear(reply_instance):
    reply, window = reply_instance
    fake_ctx = create_fake_ctx()
    reply.reply_ctx = fake_ctx
    reply.reply_stack = [[{"result": "clear"}]]
    reply.clear()
    assert reply.reply_ctx is None
    assert reply.reply_stack == []

# Test is_log based on configuration.
def test_is_log(reply_instance):
    reply, window = reply_instance
    # By default, returns True.
    assert reply.is_log() is True
    # Simulate disabled logging.
    window.core.config.get.side_effect = lambda key, default=None: {
         "log.events": False
    }.get(key, default)
    assert reply.is_log() is False

# Test append method.
def test_append(reply_instance):
    reply, window = reply_instance
    fake_ctx = create_fake_ctx(results=[{"result": "append"}])
    reply.append(fake_ctx)
    # The original results should be added to the stack and then cleared.
    assert fake_ctx.results == []
    assert reply.reply_stack[-1] == [{"result": "append"}]
    assert reply.reply_ctx == fake_ctx