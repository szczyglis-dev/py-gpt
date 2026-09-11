#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest
from unittest.mock import MagicMock

from pygpt_net.core.experts import Experts
from pygpt_net.core.experts.worker import ExpertWorker
from pygpt_net.core.agents_v2.expert import ExpertAgentBridge
from pygpt_net.core.types import MODE_AGENT, MODE_EXPERT, TOOL_EXPERT_CALL_NAME
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.preset import PresetItem


@pytest.fixture
def fake_window():
    win = MagicMock()
    config_values = {
        "prompt.expert": "Default prompt with presets {presets}",
        "preset": None,
        "mode": "chat",
        "assistant": "Assistant",
        "llama.idx.mode": "default",
        "max_output_tokens": 100,
    }
    win.core.config.get.side_effect = lambda key, default=None: config_values.get(key, default)
    win.core.presets.has.return_value = False
    win.core.presets.get_by_id.return_value = None
    win.core.presets.get_by_mode.return_value = {}
    win.core.presets.get_by_uuid.return_value = None
    win.controller.agent.legacy.enabled.return_value = False
    win.controller.kernel.stopped.return_value = False
    win.core.debug.log = MagicMock()
    return win


def test_agent_enabled(fake_window):
    experts = Experts(window=fake_window)
    fake_window.controller.agent.legacy.enabled.return_value = True
    assert experts.agent_enabled() is True
    fake_window.controller.agent.legacy.enabled.return_value = False
    assert experts.agent_enabled() is False


def test_exists(fake_window):
    experts = Experts(window=fake_window)
    fake_window.core.presets.has.return_value = True
    assert experts.exists("exp1") is True
    fake_window.core.presets.has.assert_called_with(MODE_EXPERT, "exp1")


def test_get_expert(fake_window):
    preset = PresetItem()
    preset.filename = "exp1"
    preset.name = "Expert 1"
    fake_window.core.presets.get_by_id.return_value = preset

    experts = Experts(window=fake_window)
    assert experts.get_expert("exp1") is preset
    fake_window.core.presets.get_by_id.assert_called_once_with(MODE_EXPERT, "exp1")


def test_get_experts_agent_branch(fake_window):
    fake_window.controller.agent.legacy.enabled.return_value = True
    agent = MagicMock(experts=["uuid1"])
    fake_window.core.presets.get_by_mode.side_effect = lambda mode: {
        MODE_AGENT: {"agent1": agent},
        MODE_EXPERT: {},
    }.get(mode, {})
    fake_window.core.config.get.side_effect = lambda key, default=None: (
        "agent1" if key == "preset" else default
    )

    expert = PresetItem()
    expert.filename = "expA"
    expert.name = "Expert A"
    fake_window.core.presets.get_by_uuid.return_value = expert

    assert Experts(window=fake_window).get_experts() == {"expA": expert}


def test_get_experts_filters_disabled_and_current_presets(fake_window):
    enabled = PresetItem()
    enabled.enabled = True
    enabled.name = "Expert B"

    disabled = PresetItem()
    disabled.enabled = False
    disabled.name = "Expert Disabled"

    current = PresetItem()
    current.enabled = True
    current.name = "Current Expert"

    presets = {
        "expB": enabled,
        "expDisabled": disabled,
        "current.expC": current,
    }
    fake_window.core.presets.get_by_mode.side_effect = lambda mode: (
        presets if mode == MODE_EXPERT else {}
    )

    assert Experts(window=fake_window).get_experts() == {"expB": enabled}


def test_get_expert_name_by_id(fake_window):
    expert = PresetItem()
    expert.enabled = True
    expert.name = "Expert X"
    experts = Experts(window=fake_window)
    experts.get_experts = MagicMock(return_value={"expX": expert})

    assert experts.get_expert_name_by_id("expX") == "Expert X"
    assert experts.get_expert_name_by_id("missing") is None


def test_count_experts(fake_window):
    agent = MagicMock(experts=["uuid1", "uuid2", "missing"])
    fake_window.core.presets.get_by_mode.side_effect = lambda mode: (
        {"agent1": agent} if mode == MODE_AGENT else {}
    )
    fake_window.core.presets.get_by_uuid.side_effect = lambda uuid: (
        object() if uuid in {"uuid1", "uuid2"} else None
    )

    assert Experts(window=fake_window).count_experts("agent1") == 2
    assert Experts(window=fake_window).count_experts("missing") == 0


def test_get_prompt(fake_window):
    described = PresetItem()
    described.enabled = True
    described.name = "Expert Prompt"
    described.description = "Does useful work"

    plain = PresetItem()
    plain.enabled = True
    plain.name = "Plain Expert"
    plain.description = ""

    experts = Experts(window=fake_window)
    experts.get_experts = MagicMock(return_value={"expP": described, "expQ": plain})

    prompt = experts.get_prompt()
    assert "expP: Expert Prompt (Does useful work)" in prompt
    assert "expQ: Plain Expert" in prompt
    assert "{presets}" not in prompt


def test_get_functions_exposes_standard_expert_call_schema(fake_window):
    funcs = Experts(window=fake_window).get_functions()

    assert len(funcs) == 1
    func = funcs[0]
    assert func["cmd"] == TOOL_EXPERT_CALL_NAME
    params = {item["name"]: item for item in func["params"]}
    assert params["id"]["required"] is True
    assert params["instruction"]["required"] is True
    assert params["system_prompt"]["required"] is False


def test_expert_agent_bridge_composes_optional_system_prompt():
    assert ExpertAgentBridge.compose_system_prompt("Preset prompt") == "Preset prompt"
    assert ExpertAgentBridge.compose_system_prompt("", "Caller prompt") == "Caller prompt"
    assert ExpertAgentBridge.compose_system_prompt("Preset prompt", "Caller prompt") == (
        "Caller prompt\n\n<additional_user_system_instruction>\n"
        "Preset prompt\n</additional_user_system_instruction>"
    )


def test_expert_worker_run_collects_regular_tool_response(fake_window):
    worker = ExpertWorker()
    worker.window = fake_window
    worker.ctx = CtxItem()
    worker.cmds = [
        {
            "cmd": TOOL_EXPERT_CALL_NAME,
            "params": {"id": "exp1", "instruction": "Do it"},
        }
    ]
    worker._call_expert = MagicMock(return_value="Expert result")
    worker.reply_more = MagicMock()

    worker.run()

    worker._call_expert.assert_called_once_with({"id": "exp1", "instruction": "Do it"})
    responses = worker.reply_more.call_args.args[0]
    assert responses == [
        {
            "request": {
                "cmd": TOOL_EXPERT_CALL_NAME,
                "params": {"id": "exp1", "instruction": "Do it"},
            },
            "result": "Expert result",
        }
    ]
    assert worker.signals is None


def test_expert_worker_run_converts_expert_error_to_tool_result(fake_window):
    worker = ExpertWorker()
    worker.window = fake_window
    worker.ctx = CtxItem()
    worker.cmds = [
        {
            "cmd": TOOL_EXPERT_CALL_NAME,
            "params": {"id": "expError", "instruction": "Fail"},
        }
    ]
    worker._call_expert = MagicMock(side_effect=RuntimeError("Test error"))
    worker.reply_more = MagicMock()

    worker.run()

    fake_window.core.debug.log.assert_called_once()
    responses = worker.reply_more.call_args.args[0]
    assert len(responses) == 1
    assert responses[0]["request"]["params"]["id"] == "expError"
    assert "Test error" in responses[0]["result"]
    assert worker.signals is None


def test_expert_worker_skips_non_expert_commands(fake_window):
    worker = ExpertWorker()
    worker.window = fake_window
    worker.ctx = CtxItem()
    worker.cmds = [{"cmd": "other", "params": {}}]
    worker._call_expert = MagicMock()
    worker.reply_more = MagicMock()

    worker.run()

    worker._call_expert.assert_not_called()
    worker.reply_more.assert_not_called()
    assert worker.signals is None
