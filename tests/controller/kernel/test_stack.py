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
from qasync import QApplication

from pygpt_net.controller.kernel.stack import Stack
from pygpt_net.core.ctx.reply import ReplyContext
from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge.context import BridgeContext

# Set dummy constant values if not already defined
if not hasattr(ReplyContext, "EXPERT_CALL"):
    ReplyContext.EXPERT_CALL = "EXPERT_CALL"
if not hasattr(ReplyContext, "CMD_EXECUTE"):
    ReplyContext.CMD_EXECUTE = "CMD_EXECUTE"
if not hasattr(ReplyContext, "CMD_EXECUTE_FORCE"):
    ReplyContext.CMD_EXECUTE_FORCE = "CMD_EXECUTE_FORCE"
if not hasattr(ReplyContext, "CMD_EXECUTE_INLINE"):
    ReplyContext.CMD_EXECUTE_INLINE = "CMD_EXECUTE_INLINE"
if not hasattr(ReplyContext, "AGENT_CONTINUE"):
    ReplyContext.AGENT_CONTINUE = "AGENT_CONTINUE"


class DummyReplyContext:
    def __init__(self, type, ctx="ctx", input="input", parent_id="pid", cmds=None):
        self.type = type
        self.ctx = ctx
        self.input = input
        self.parent_id = parent_id
        self.cmds = cmds if cmds is not None else ["cmd"]


@pytest.fixture
def dummy_window():
    window = MagicMock()
    window.core = MagicMock()
    window.core.experts = MagicMock()
    window.core.experts.call = MagicMock()
    window.core.debug = MagicMock()
    window.core.debug.info = MagicMock()
    window.controller = MagicMock()
    window.controller.plugins = MagicMock()
    window.controller.plugins.apply_cmds = MagicMock()
    window.controller.plugins.apply_cmds_inline = MagicMock()
    window.controller.kernel = MagicMock()
    window.controller.kernel.stopped = MagicMock(return_value=False)
    window.dispatch = MagicMock()
    return window


def test_add_and_has(dummy_window):
    stack = Stack(dummy_window)
    dummy_ctx = DummyReplyContext(ReplyContext.EXPERT_CALL)
    assert not stack.has()
    stack.add(dummy_ctx)
    assert stack.current == dummy_ctx
    assert stack.has()
    assert not stack.is_locked()


def test_clear(dummy_window):
    stack = Stack(dummy_window)
    dummy_ctx = DummyReplyContext(ReplyContext.CMD_EXECUTE)
    stack.add(dummy_ctx)
    stack.lock()
    stack.clear()
    assert not stack.has()
    assert not stack.is_locked()


def test_lock_unlock(dummy_window):
    stack = Stack(dummy_window)
    stack.lock()
    assert stack.is_locked()
    stack.unlock()
    assert not stack.is_locked()


def test_execute_expert_call(dummy_window):
    stack = Stack(dummy_window)
    dummy_ctx = DummyReplyContext(ReplyContext.EXPERT_CALL, ctx="ctx_val", input="query", parent_id="exp_id")
    stack.execute(dummy_ctx)
    dummy_window.core.experts.call.assert_called_once_with("ctx_val", "exp_id", "query")


def test_execute_cmd_execute(dummy_window):
    stack = Stack(dummy_window)
    dummy_ctx = DummyReplyContext(ReplyContext.CMD_EXECUTE, ctx="ctx_val", cmds=["cmd1"])
    stack.execute(dummy_ctx)
    dummy_window.controller.plugins.apply_cmds.assert_called_once_with("ctx_val", ["cmd1"])


def test_execute_cmd_execute_force(dummy_window):
    stack = Stack(dummy_window)
    dummy_ctx = DummyReplyContext(ReplyContext.CMD_EXECUTE_FORCE, ctx="ctx_val", cmds=["cmd1"])
    stack.execute(dummy_ctx)
    dummy_window.controller.plugins.apply_cmds.assert_called_once_with("ctx_val", ["cmd1"], all=True)


def test_execute_cmd_execute_inline(dummy_window):
    stack = Stack(dummy_window)
    dummy_ctx = DummyReplyContext(ReplyContext.CMD_EXECUTE_INLINE, ctx="ctx_val", cmds=["cmd1"])
    stack.execute(dummy_ctx)
    dummy_window.controller.plugins.apply_cmds_inline.assert_called_once_with("ctx_val", ["cmd1"])


def test_execute_agent_continue(dummy_window):
    stack = Stack(dummy_window)
    dummy_ctx = DummyReplyContext(ReplyContext.AGENT_CONTINUE, ctx="ctx_val", input="prompt")
    stack.execute(dummy_ctx)
    dummy_window.dispatch.assert_called_once()
    args, _ = dummy_window.dispatch.call_args
    event = args[0]
    assert isinstance(event, KernelEvent)
    assert event.name == KernelEvent.INPUT_SYSTEM
    expected_extra = {"force": True, "internal": True}
    assert event.data.get("extra") == expected_extra
    bridge_context = event.data.get("context")
    assert isinstance(bridge_context, BridgeContext)
    assert bridge_context.ctx == "ctx_val"
    assert bridge_context.prompt == "prompt"


def test_execute_none(dummy_window):
    stack = Stack(dummy_window)
    stack.execute(None)
    dummy_window.core.experts.call.assert_not_called()
    dummy_window.controller.plugins.apply_cmds.assert_not_called()
    dummy_window.controller.plugins.apply_cmds_inline.assert_not_called()
    dummy_window.dispatch.assert_not_called()


def test_handle_kernel_stopped(dummy_window):
    dummy_window.controller.kernel.stopped.return_value = True
    stack = Stack(dummy_window)
    dummy_ctx = DummyReplyContext(ReplyContext.CMD_EXECUTE, cmds=["cmd1"])
    stack.add(dummy_ctx)
    stack.handle()
    assert not stack.has()


def test_handle_waiting(dummy_window, monkeypatch):
    dummy_window.controller.kernel.stopped.return_value = False
    stack = Stack(dummy_window)
    dummy_ctx = DummyReplyContext(ReplyContext.CMD_EXECUTE, ctx="ctx_val", cmds=["cmd1"])
    stack.add(dummy_ctx)
    flag = False

    def fake_process_events():
        nonlocal flag
        flag = True

    monkeypatch.setattr(QApplication, "processEvents", fake_process_events)
    stack.handle()
    assert stack.processed is True
    assert flag is True
    assert stack.is_locked()


def test_log(dummy_window):
    stack = Stack(dummy_window)
    stack.log("debug message")
    dummy_window.core.debug.info.assert_called_once_with("debug message")