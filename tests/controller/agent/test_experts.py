#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest
from unittest.mock import MagicMock

from pygpt_net.controller.agent.experts import Experts
from pygpt_net.core.types import MODE_AGENT, MODE_EXPERT


@pytest.fixture
def dummy_window():
    win = MagicMock()
    win.core.config.get.side_effect = lambda key, default=None: {
        "mode": MODE_EXPERT,
        "agent.auto_stop": True,
    }.get(key, default)
    win.core.prompt.get.return_value = "Instruction"
    win.core.experts.get_prompt.return_value = "ExpertPrompt"
    win.controller.plugins.is_type_enabled.return_value = False
    win.controller.agent.legacy.enabled.return_value = False
    win.controller.agent.legacy.normalize_instruction_prompt.side_effect = (
        lambda prompt: str(prompt or "").strip()
    )
    win.controller.agent.legacy.on_system_prompt.side_effect = (
        lambda sys_prompt, append_prompt, auto_stop: "ModifiedPrompt"
    )
    return win


@pytest.fixture
def experts(dummy_window):
    return Experts(window=dummy_window)


def test_stop_and_unlock(experts):
    assert experts.stopped() is False
    experts.stop()
    assert experts.stopped() is True
    experts.unlock()
    assert experts.stopped() is False


def test_enabled_expert_mode(dummy_window):
    exp = Experts(window=dummy_window)
    assert exp.enabled() is True
    assert exp.enabled(check_inline=False) is True


def test_enabled_non_expert_and_inline_plugin(dummy_window):
    dummy_window.core.config.get.side_effect = lambda key, default=None: {
        "mode": "chat",
        "agent.auto_stop": True,
    }.get(key, default)
    exp = Experts(window=dummy_window)

    dummy_window.controller.plugins.is_type_enabled.return_value = False
    assert exp.enabled() is False
    assert exp.enabled(check_inline=False) is False

    dummy_window.controller.plugins.is_type_enabled.return_value = True
    assert exp.enabled() is True
    assert exp.enabled(check_inline=False) is False


def test_append_prompts_agent_enabled(dummy_window):
    dummy_window.controller.agent.legacy.enabled.return_value = True
    exp = Experts(window=dummy_window)

    assert exp.append_prompts(MODE_AGENT, "Sys") == "ModifiedPrompt"
    assert exp.append_prompts("other", "Sys") == "Instruction\n\nSys\n\nExpertPrompt"


def test_append_prompts_expert_without_agent(dummy_window):
    exp = Experts(window=dummy_window)
    assert exp.append_prompts("other", "Sys") == "ExpertPrompt"
    assert exp.append_prompts(MODE_AGENT, "Sys") == "ModifiedPrompt"


def test_append_prompts_leaves_plain_chat_unchanged(dummy_window):
    dummy_window.core.config.get.side_effect = lambda key, default=None: {
        "mode": "chat",
        "agent.auto_stop": True,
    }.get(key, default)
    dummy_window.controller.plugins.is_type_enabled.return_value = False
    dummy_window.controller.agent.legacy.enabled.return_value = False

    exp = Experts(window=dummy_window)
    assert exp.append_prompts("chat", "Sys") == "Sys"


def test_log(experts, dummy_window):
    experts.log("test message")
    dummy_window.core.debug.info.assert_called_once_with("test message")
