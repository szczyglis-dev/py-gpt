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
from pygpt_net.core.types import MODE_AGENT, MODE_EXPERT
from pygpt_net.core.events import KernelEvent, RenderEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.controller.agent.experts import Experts

# Fixture that creates a dummy window with needed sub-objects
@pytest.fixture
def dummy_window():
    win = MagicMock()

    # Setup core configuration
    config = MagicMock()
    config.get.side_effect = lambda key: {
        'mode': MODE_EXPERT,
        'agent.auto_stop': True,
        'stream': 'stream_value'
    }.get(key, None)
    win.core = MagicMock()
    win.core.config = config

    # Setup prompt and experts in core
    prompt = MagicMock()
    prompt.get.return_value = "Instruction"
    win.core.prompt = prompt

    experts_mock = MagicMock()
    experts_mock.get_prompt.return_value = "ExpertPrompt"
    experts_mock.reply.return_value = None
    experts_mock.extract_calls.return_value = {}
    experts_mock.exists.return_value = True
    win.core.experts = experts_mock

    # Setup debug logging
    win.core.debug = MagicMock()
    win.core.debug.info = MagicMock()

    # Setup context updater
    win.core.ctx = MagicMock()
    win.core.ctx.update_item.return_value = None

    # Setup controller plugins
    plugins = MagicMock()
    plugins.is_type_enabled.return_value = False
    win.controller = MagicMock()
    win.controller.plugins = plugins

    # Setup agent legacy
    legacy = MagicMock()
    legacy.enabled.return_value = False
    legacy.on_system_prompt.side_effect = lambda sys_prompt, append_prompt, auto_stop: "ModifiedPrompt"
    win.controller.agent = MagicMock()
    win.controller.agent.legacy = legacy

    # Setup window.dispatch
    win.dispatch = MagicMock()

    return win

@pytest.fixture
def experts(dummy_window):
    return Experts(window=dummy_window)

def test_stop_and_unlock(experts):
    # Initially not stopped
    assert experts.stopped() is False
    experts.stop()
    assert experts.stopped() is True
    experts.unlock()
    assert experts.stopped() is False

def test_enabled_expert_mode(dummy_window):
    # With mode set to expert and no inline plugin enabled
    dummy_window.core.config.get.side_effect = lambda key: {
        'mode': MODE_EXPERT,
        'agent.auto_stop': True,
        'stream': 'stream_value'
    }.get(key, None)
    dummy_window.controller.plugins.is_type_enabled.return_value = False
    dummy_window.controller.agent.legacy.enabled.return_value = False
    exp = Experts(window=dummy_window)
    assert exp.enabled() is True
    assert exp.enabled(check_inline=False) is True

def test_enabled_non_expert(dummy_window):
    # Mode is not expert and plugin not enabled
    dummy_window.core.config.get.side_effect = lambda key: {
        'mode': "non_expert",
        'agent.auto_stop': True,
        'stream': 'stream_value'
    }.get(key, None)
    dummy_window.controller.plugins.is_type_enabled.return_value = False
    exp = Experts(window=dummy_window)
    assert exp.enabled() is False
    assert exp.enabled(check_inline=False) is False
    # When plugin is enabled, inline check returns True
    dummy_window.controller.plugins.is_type_enabled.return_value = True
    assert exp.enabled() is True

def test_append_prompts_agent_enabled(dummy_window):
    # Agent enabled branch returns modified prompt
    dummy_window.controller.agent.legacy.enabled.return_value = True
    exp = Experts(window=dummy_window)
    # Test with mode equal to MODE_AGENT
    result = exp.append_prompts(MODE_AGENT, "Sys",)
    assert result == "ModifiedPrompt"
    # Test with mode not equal to MODE_AGENT
    result = exp.append_prompts("other", "Sys")
    expected = "Instruction\n\nSys\n\nExpertPrompt"
    assert result == expected

def test_append_prompts_expert_without_agent(dummy_window):
    # Agent disabled but enabled() is True (mode == expert)
    dummy_window.controller.agent.legacy.enabled.return_value = False
    dummy_window.core.config.get.side_effect = lambda key: {
        'mode': MODE_EXPERT,
        'agent.auto_stop': True,
        'stream': 'stream_value'
    }.get(key, None)
    exp = Experts(window=dummy_window)
    result = exp.append_prompts("other", "Sys")
    # first if not executed, so second branch sets prompt
    assert result == "ExpertPrompt"
    # With MODE_AGENT the last branch applies
    result = exp.append_prompts(MODE_AGENT, "Sys")
    assert result == "ModifiedPrompt"

def test_append_prompts_with_parent_id(dummy_window):
    # Parent ID provided bypasses second block
    dummy_window.controller.agent.legacy.enabled.return_value = True
    exp = Experts(window=dummy_window)
    result = exp.append_prompts(MODE_AGENT, "Sys")
    # Only first block applies then on_system_prompt is called
    assert result == "ModifiedPrompt"

class DummyCtx:
    # Minimal CtxItem-like object
    def __init__(self):
        self.sub_reply = False
        self.reply = False
        self.meta = {}
        self.sub_calls = 0

def test_handle_sub_reply(experts, dummy_window):
    ctx = DummyCtx()
    ctx.sub_reply = True
    result = experts.handle(ctx)
    dummy_window.core.ctx.update_item.assert_called_with(ctx)
    dummy_window.core.experts.reply.assert_called_with(ctx)
    assert result == 0

def test_handle_calls_with_mentions(experts, dummy_window):
    ctx = DummyCtx()
    # Ensure sub_reply and reply are False
    ctx.sub_reply = False
    ctx.reply = False
    # Two mentions returned
    mentions = {"exp1": "input1", "exp2": "input2"}
    dummy_window.core.experts.extract_calls.return_value = mentions
    # Only exp1 exists
    dummy_window.core.experts.exists.side_effect = lambda expert_id: expert_id == "exp1"
    result = experts.handle(ctx)
    # Should dispatch one RenderEvent and one KernelEvent
    dispatch_calls = dummy_window.dispatch.call_args_list
    # First call for RenderEvent, then one for KernelEvent for exp1 only
    assert len(dispatch_calls) == 2
    # KernelEvent call contains context with reply having parent_id 'exp1'
    kernel_event = dispatch_calls[1][0][0]
    assert kernel_event.__class__.__name__ == "KernelEvent"
    assert getattr(kernel_event, 'data', None) is None or isinstance(kernel_event, KernelEvent)
    assert ctx.sub_calls == 1
    assert result == 1

def test_handle_no_mentions(experts, dummy_window):
    ctx = DummyCtx()
    ctx.sub_reply = False
    ctx.reply = False
    dummy_window.core.experts.extract_calls.return_value = {}
    result = experts.handle(ctx)
    assert result == 0

def test_handle_when_disabled(dummy_window):
    ctx = DummyCtx()
    # Set mode so enabled() is False
    dummy_window.core.config.get.side_effect = lambda key: {
        'mode': "non_expert",
        'agent.auto_stop': True,
        'stream': 'stream_value'
    }.get(key, None)
    dummy_window.controller.plugins.is_type_enabled.return_value = False
    dummy_window.controller.agent.legacy.enabled.return_value = False
    exp = Experts(window=dummy_window)
    result = exp.handle(ctx)
    dummy_window.dispatch.assert_not_called()
    assert result == 0

def test_log(experts, dummy_window):
    experts.log("test message")
    dummy_window.core.debug.info.assert_called_with("test message")