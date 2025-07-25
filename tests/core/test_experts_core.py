#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.24 03:00:00                  #
# ================================================== #

import json
import pytest
from unittest.mock import MagicMock

from pygpt_net.core.experts import Experts, ExpertWorker, WorkerSignals
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.preset import PresetItem
from pygpt_net.core.events import KernelEvent, RenderEvent, Event
from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_EXPERT,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_AUDIO,
    MODE_RESEARCH,
)
from llama_index.core.base.llms.types import ChatMessage, MessageRole


# fixture for a fake window that mimics the nested structure needed
@pytest.fixture
def fake_window():
    win = MagicMock()

    # setup config.get to return default values as needed.
    config_values = {
        "experts.mode": None,
        "prompt.expert": "Default prompt with presets {presets}",
        "preset": None,
        "mode": MODE_CHAT,
        "max_output_tokens": 100,
        "stream": True,
        "agent.llama.verbose": False,
        "assistant": "Assistant",
        "llama.idx.mode": "default",
        "cmd": True,
        "experts.use_agent": False,
    }
    win.core.config.get.side_effect = lambda key, default=None: config_values.get(key, default)

    # presets mocks
    win.core.presets.has = MagicMock(return_value=False)
    win.core.presets.get_by_id = MagicMock(return_value=MagicMock(filename="exp1", name="Expert 1"))
    win.core.presets.get_by_mode = MagicMock(return_value={})
    win.core.presets.get_by_uuid = MagicMock(return_value=None)

    # command mocks
    win.core.command.is_native_enabled = MagicMock(return_value=False)
    win.core.command.extract_cmds = MagicMock(return_value=[])
    win.core.command.is_cmd = MagicMock(return_value=True)

    # controller mocks
    win.controller.kernel.stopped = MagicMock(return_value=False)
    win.controller.agent.legacy.enabled = MagicMock(return_value=False)
    win.controller.chat.output.handle = MagicMock()
    win.controller.chat.common.lock_input = MagicMock()
    win.controller.chat.command.handle = MagicMock()
    win.controller.kernel.stack.handle = MagicMock()

    # core ctx update
    win.core.ctx.update_item = MagicMock()
    win.dispatch = MagicMock()
    win.threadpool.start = MagicMock()

    # set up agents (needed for ExpertWorker.call_agent)
    win.core.agents = MagicMock()
    win.core.agents.memory.prepare = MagicMock(return_value=[])
    provider = MagicMock()
    provider.get_agent = MagicMock(return_value=MagicMock())
    win.core.agents.provider = MagicMock(get=MagicMock(return_value=provider))
    win.core.agents.runner = MagicMock(run_plan_once=MagicMock(return_value=None))
    win.core.models = MagicMock(get=MagicMock(return_value="model_data"))
    # set up idx so that ExpertWorker.run can obtain a chat index and LLM
    chat_index = MagicMock()
    chat_index.get_index = MagicMock(return_value=("index", "llm"))
    win.core.idx.chat = chat_index
    win.core.idx.llm = MagicMock(get=MagicMock(return_value="llm"))
    # prepare sys_prompt
    win.core.prompt = MagicMock(
        prepare_sys_prompt=MagicMock(
            side_effect=lambda mode, model_data, sys_prompt, ctx, reply, internal, is_expert: sys_prompt + " prepared"
        )
    )
    # debug log
    win.core.debug.log = MagicMock()

    return win


# ---------- Experts ----------

def test_get_mode_default(fake_window):
    # when there is no custom expert mode configured, default to MODE_CHAT.
    fake_window.core.config.get.side_effect = lambda key, default=None: {
        "experts.mode": None,
        "prompt.expert": "Default prompt with presets {presets}",
        "preset": None,
        "mode": MODE_CHAT,
        "max_output_tokens": 100,
        "stream": True,
        "agent.llama.verbose": False,
        "assistant": "Assistant",
        "llama.idx.mode": "default",
        "cmd": True,
        "experts.use_agent": False,
    }.get(key, default)
    experts = Experts(window=fake_window)
    mode = experts.get_mode()
    assert mode == MODE_CHAT


def test_get_mode_custom(fake_window):
    # when a valid allowed mode is configured, it should be returned.
    fake_window.core.config.get.side_effect = lambda key, default=None: {
        "experts.mode": MODE_COMPLETION,
        "prompt.expert": "Custom prompt with presets {presets}",
        "preset": None,
        "mode": MODE_CHAT,
        "max_output_tokens": 100,
        "stream": True,
        "agent.llama.verbose": False,
        "assistant": "Assistant",
        "llama.idx.mode": "default",
        "cmd": True,
        "experts.use_agent": False,
    }.get(key, default)
    experts = Experts(window=fake_window)
    mode = experts.get_mode()
    assert mode == MODE_COMPLETION


def test_stopped(fake_window):
    fake_window.controller.kernel.stopped.return_value = True
    experts = Experts(window=fake_window)
    assert experts.stopped() is True
    fake_window.controller.kernel.stopped.return_value = False
    assert experts.stopped() is False


def test_agent_enabled(fake_window):
    fake_window.controller.agent.legacy.enabled.return_value = True
    experts = Experts(window=fake_window)
    assert experts.agent_enabled() is True
    fake_window.controller.agent.legacy.enabled.return_value = False
    assert experts.agent_enabled() is False


def test_exists(fake_window):
    fake_window.core.presets.has.return_value = True
    experts = Experts(window=fake_window)
    assert experts.exists("exp1") is True
    fake_window.core.presets.has.return_value = False
    assert experts.exists("exp2") is False


def test_get_expert(fake_window):
    dummy_preset = PresetItem()
    dummy_preset.filename = "exp1"
    dummy_preset.name="Expert 1"
    fake_window.core.presets.get_by_id.return_value = dummy_preset
    experts = Experts(window=fake_window)
    preset = experts.get_expert("exp1")
    assert preset.filename == "exp1"
    assert preset.name == "Expert 1"


def test_get_experts_agent_branch(fake_window):
    # simulate agent mode by setting agent_enabled to True.
    fake_window.controller.agent.legacy.enabled.return_value = True
    # setup agent preset: an agent which has a list of experts.
    agent_obj = MagicMock()
    agent_obj.experts = ["uuid1"]
    fake_window.core.presets.get_by_mode.side_effect = lambda mode: {
        MODE_AGENT: {"agent1": agent_obj},
        MODE_EXPERT: {}
    }.get(mode, {})
    fake_window.core.config.get.side_effect = lambda key, default=None: {
        "preset": "agent1",
        "experts.mode": None,
        "prompt.expert": "Prompt {presets}",
        "mode": MODE_CHAT,
        "max_output_tokens": 100,
        "stream": True,
        "agent.llama.verbose": False,
        "assistant": "Assistant",
        "llama.idx.mode": "default",
        "cmd": True,
        "experts.use_agent": False,
    }.get(key, default)
    expert_obj = PresetItem()
    expert_obj.filename = "expA"
    expert_obj.name="Expert A"
    fake_window.core.presets.get_by_uuid.return_value = expert_obj
    experts = Experts(window=fake_window)
    result = experts.get_experts()
    assert result == {"expA": "Expert A"}


def test_get_experts_expert_branch(fake_window):
    # simulate non-agent mode so the expert branch is used.
    fake_window.controller.agent.legacy.enabled.return_value = False
    # setup expert presets – skip disabled experts and keys starting with "current."
    expert_enabled = MagicMock(enabled=True, name="Expert B")
    expert_disabled = MagicMock(enabled=False, name="Expert Disabled")
    expert_current = MagicMock(enabled=True, name="Current Expert")

    expert_enabled = PresetItem()
    expert_enabled.enabled = True
    expert_enabled.name = "Expert B"

    expert_disabled = PresetItem()
    expert_disabled.enabled = False
    expert_disabled.name = "Expert Disabled"

    expert_current = PresetItem()
    expert_current.enabled = True
    expert_current.name = "Current Expert"

    presets = {
        "expB": expert_enabled,
        "expDisabled": expert_disabled,
        "current.expC": expert_current,
    }
    fake_window.core.presets.get_by_mode.side_effect = lambda mode: {MODE_EXPERT: presets}.get(mode, {})
    experts = Experts(window=fake_window)
    result = experts.get_experts()
    # only "expB" should be returned.
    assert result == {"expB": "Expert B"}


def test_get_expert_name_by_id(fake_window):
    expert_dict = {"expX": "Expert X"}
    experts = Experts(window=fake_window)
    # override get_experts to return our dummy dict.
    experts.get_experts = MagicMock(return_value=expert_dict)
    name = experts.get_expert_name_by_id("expX")
    assert name == "Expert X"


def test_count_experts(fake_window):
    # prepare an agent preset with two expert UUIDs.
    agent_obj = MagicMock()
    agent_obj.experts = ["uuid1", "uuid2"]
    fake_window.core.presets.get_by_mode.side_effect = lambda mode: {MODE_AGENT: {"agent1": agent_obj}}.get(mode, {})
    # setup get_by_uuid to return non-None for each expert.
    fake_expert1 = MagicMock()
    fake_expert2 = MagicMock()
    calls = {"uuid1": fake_expert1, "uuid2": fake_expert2}
    fake_window.core.presets.get_by_uuid.side_effect = lambda uuid: calls.get(uuid)
    experts = Experts(window=fake_window)
    count = experts.count_experts("agent1")
    assert count == 2


def test_get_prompt(fake_window):
    # force native command enabled so the multiline expert prompt is used.
    fake_window.core.command.is_native_enabled.return_value = True
    # setup a preset so that get_experts returns one expert.
    expert_obj = PresetItem()
    expert_obj.enabled = True
    expert_obj.name = "Expert Prompt"

    presets = {"expP": expert_obj}
    fake_window.core.presets.get_by_mode.side_effect = lambda mode: {MODE_EXPERT: presets}.get(mode, {})
    experts = Experts(window=fake_window)
    prompt = experts.get_prompt()
    # check that the replaced {presets} part contains the expert details.
    assert "expP: Expert Prompt" in prompt


def test_extract_calls(fake_window):
    # prepare a preset so that "exp4" exists.
    expert_obj = MagicMock(enabled=True, name="Expert 4")
    fake_window.core.presets.get_by_mode.side_effect = lambda mode: {MODE_EXPERT: {"exp4": expert_obj}}.get(mode, {})
    # create a dummy command that should be extracted.
    cmd = {"cmd": "expert_call", "params": {"id": "exp4", "query": "Hello Expert"}}
    fake_window.core.command.extract_cmds.return_value = [cmd]
    fake_window.core.command.from_commands.return_value = [cmd]
    ctx = CtxItem()
    ctx.output = "dummy output"
    experts = Experts(window=fake_window)
    calls = experts.extract_calls(ctx)
    assert calls == {"exp4": "Hello Expert"}
    # test when no commands are found.
    fake_window.core.command.extract_cmds.return_value = []
    calls = experts.extract_calls(ctx)
    assert calls == {}


def test_reply(fake_window):
    # set up the context so that experts.reply sends a response.
    fake_window.controller.kernel.stopped.return_value = False
    fake_window.controller.agent.legacy.enabled.return_value = False
    ctx = CtxItem()
    ctx.output = "Expert response"
    ctx.meta = MagicMock(preset="expReply")
    ctx.sub_reply = False
    # dummy implementations for to_dict and from_dict
    ctx.to_dict = lambda: {"output": ctx.output, "meta": ctx.meta, "input": "Expert input"}
    ctx.from_dict = lambda data: None

    experts = Experts(window=fake_window)
    experts.reply(ctx)
    # we check that dispatch was called with an kernel.input.system event (as a string check)
    calls = fake_window.dispatch.call_args_list
    assert any("kernel.input.system" in str(call[0][0].__dict__) for call in calls)


def test_call(fake_window):
    fake_window.controller.kernel.stopped.return_value = False
    experts = Experts(window=fake_window)
    master_ctx = CtxItem()
    experts.call(master_ctx, "expCall", "Hello")
    # check that a worker was created and threadpool.start was called.
    fake_window.threadpool.start.assert_called_once()
    assert experts.worker is not None


def test_handle_output(fake_window):
    experts = Experts(window=fake_window)
    ctx = CtxItem()
    experts.handle_output(ctx, "test_mode")
    fake_window.controller.chat.output.handle.assert_called_with(ctx=ctx, mode="test_mode", stream_mode=False)


def test_handle_cmd(fake_window):
    fake_window.controller.kernel.stopped.return_value = False
    experts = Experts(window=fake_window)
    # create dummy context objects.
    ctx = CtxItem()
    master_ctx = CtxItem()
    ctx.reply = False
    ctx.output = "cmd result"
    ctx.input = "input text"
    ctx.cmds = []
    ctx.from_previous = lambda: None
    ctx.to_dict = lambda: {"output": ctx.output, "input": ctx.input}
    # override handle_response to capture the call.
    experts.handle_response = MagicMock()
    experts.handle_cmd(ctx, master_ctx, "expCmd", "Expert Cmd", "cmd result")
 #   fake_window.controller.chat.command.handle.assert_called_with(ctx)
 #   fake_window.controller.kernel.stack.handle.assert_called()
 #   fake_window.core.ctx.update_item.assert_called_with(ctx)
 #   experts.handle_response.assert_called()


def test_handle_input_locked(fake_window):
    experts = Experts(window=fake_window)
    fake_window.controller.kernel.stopped.return_value = False
    experts.handle_input_locked()
    fake_window.controller.chat.common.lock_input.assert_called_once()


def test_handle_event(fake_window):
    experts = Experts(window=fake_window)
    dummy_event = Event("dummy", {"key": "value"})
    fake_window.controller.kernel.stopped.return_value = False
    experts.handle_event(dummy_event)
    fake_window.dispatch.assert_called_with(dummy_event)


def test_handle_error_not_stopped(fake_window):
    fake_window.controller.kernel.stopped.return_value = False
    experts = Experts(window=fake_window)
    experts.handle_error("Error occurred")
    calls = fake_window.dispatch.call_args_list
    input_system_called = any(
        isinstance(call[0][0], KernelEvent) and call[0][0].name == KernelEvent.INPUT_SYSTEM
        for call in calls
    )
    idle_called = any(
        isinstance(call[0][0], KernelEvent) and call[0][0].name == KernelEvent.STATE_IDLE
        for call in calls
    )
    assert input_system_called
    assert idle_called


def test_handle_error_stopped(fake_window):
    fake_window.controller.kernel.stopped.return_value = True
    experts = Experts(window=fake_window)
    experts.handle_error("Error occurred")
    # if stopped, only an idle event is dispatched.
    calls = fake_window.dispatch.call_args_list
    idle_called = any(
        isinstance(call[0][0], KernelEvent) and call[0][0].name == KernelEvent.STATE_IDLE
        for call in calls
    )
    assert idle_called


def test_handle_finished(fake_window):
    experts = Experts(window=fake_window)
    experts.handle_finished()
    calls = fake_window.dispatch.call_args_list
    idle_called = any(
        isinstance(call[0][0], KernelEvent) and call[0][0].name == KernelEvent.STATE_IDLE
        for call in calls
    )
    assert idle_called


def test_handle_response(fake_window):
    fake_window.controller.kernel.stopped.return_value = False
    experts = Experts(window=fake_window)
    ctx = CtxItem()
    ctx.output = "Response Text"
    experts.handle_response(ctx, "expResponse")
    calls = fake_window.dispatch.call_args_list
    input_system_called = any(
        isinstance(call[0][0], KernelEvent) and call[0][0].name == KernelEvent.INPUT_SYSTEM
        for call in calls
    )
    idle_called = any(
        isinstance(call[0][0], KernelEvent) and call[0][0].name == KernelEvent.STATE_IDLE
        for call in calls
    )
    assert input_system_called
    assert idle_called


def test_get_functions(fake_window):
    experts = Experts(window=fake_window)
    funcs = experts.get_functions()
    assert isinstance(funcs, list)
    assert len(funcs) == 1
    assert funcs[0]["cmd"] == "expert_call"


def test_has_calls(fake_window):
    experts = Experts(window=fake_window)
    # when sub_reply or reply is True, it should return False.
    ctx = CtxItem()
    ctx.sub_reply = True
    ctx.reply = False
    assert experts.has_calls(ctx) is False
    ctx.sub_reply = False
    ctx.reply = True
    assert experts.has_calls(ctx) is False
    # normal case: simulate that extract_calls returns a command.
    ctx.sub_reply = False
    ctx.reply = False
    fake_experts = MagicMock()
    fake_experts.extract_calls.return_value = {"expH": "Query H"}
    fake_experts.exists.side_effect = lambda nid: True if nid == "expH" else False
    fake_window.core.experts = fake_experts
    result = experts.has_calls(ctx)
    assert result is True
    # when extract_calls returns empty, has_calls should return False.
    fake_experts.extract_calls.return_value = {}
    result = experts.has_calls(ctx)
    assert result is False


# ---------- ExpertWorker ----------

def test_expert_worker_run_error(fake_window):
    # force an exception within run() by making get_or_create_slave_meta raise an Exception.
    fake_window.core.ctx.get_or_create_slave_meta = MagicMock(side_effect=Exception("Test error"))
    fake_window.core.debug.log = MagicMock()
    master_ctx = CtxItem()
    worker = ExpertWorker(window=fake_window, master_ctx=master_ctx, expert_id="expError", query="error query")
    worker.signals = MagicMock()
    worker.signals.error.emit = MagicMock()
    worker.signals.finished.emit = MagicMock()
    worker.run()
    worker.signals.error.emit.assert_called_with("Test error")
    worker.signals.finished.emit.assert_called_once()


def test_call_agent_success(fake_window):
    # setup for a successful agent call.
    response_ctx = MagicMock()
    response_ctx.output = "Agent response"
    fake_window.core.agents.memory.prepare.return_value = []
    provider = MagicMock()
    provider.get_agent.return_value = MagicMock()
    fake_window.core.agents.provider.get.return_value = provider
    fake_window.core.agents.runner.run_plan_once.return_value = response_ctx
    worker = ExpertWorker(window=fake_window, master_ctx=CtxItem(), expert_id="expA", query="agent query")
    result = worker.call_agent(
        context=BridgeContext(),
        tools=[],
        ctx=CtxItem(),
        query="agent query",
        llm="llm",
        system_prompt="system prompt",
        verbose=False,
    )
    assert result == "Agent response"


def test_call_agent_no_response(fake_window):
    # setup so that the agent returns no response.
    fake_window.core.agents.memory.prepare.return_value = []
    provider = MagicMock()
    provider.get_agent.return_value = MagicMock()
    fake_window.core.agents.provider.get.return_value = provider
    fake_window.core.agents.runner.run_plan_once.return_value = None
    worker = ExpertWorker(window=fake_window, master_ctx=CtxItem(), expert_id="expA", query="agent query")
    result = worker.call_agent(
        context=BridgeContext(),
        tools=[],
        ctx=CtxItem(),
        query="agent query",
        llm="llm",
        system_prompt="system prompt",
        verbose=False,
    )
    assert result == "No response from expert."