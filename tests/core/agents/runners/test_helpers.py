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

import pytest
from unittest.mock import MagicMock, patch

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.agents.runners.loop import Loop
from llama_index.core.tools import FunctionTool

# Dummy CtxItem-like object for tests
class DummyCtx:
    def __init__(self):
        self.meta = MagicMock()
        self.meta.id = "test_meta_id"
        self.extra = {}

    def set_input(self, text):
        pass

    def set_output(self, text):
        pass


# Fixture for a dummy window with required attributes
@pytest.fixture
def dummy_window():
    win = MagicMock()

    # core.config.get returns different configuration values
    config_values = {
        "agent.llama.verbose": True,
        "agent.llama.loop.mode": "score",
        "agent.llama.loop.score": 75,
        "model": "dummy_model",
    }
    win.core.config.get.side_effect = lambda key, default=None: config_values.get(key, default)

    win.core.models.get.return_value = "dummy_model_obj"
    win.core.idx.llm.get.return_value = "dummy_llm"

    # Setup provider and agent for run_once
    dummy_provider = MagicMock()
    dummy_agent = MagicMock()
    dummy_agent.chat.return_value = "agent response"
    dummy_provider.get_agent.return_value = dummy_agent
    win.core.agents.provider.get.return_value = dummy_provider

    # Setup evaluation tools and prompts
    win.core.agents.observer.evaluation.get_tools.return_value = [MagicMock(spec=FunctionTool)]
    win.core.agents.observer.evaluation.get_prompt_score.return_value = "score prompt"
    win.core.agents.observer.evaluation.get_prompt_complete.return_value = "complete prompt"

    # Runner call returns a dummy result
    win.core.agents.runner.call.return_value = "runner call result"
    win.core.ctx.all.return_value = ["history_item"]

    # Controller preset
    preset = MagicMock()
    preset.idx = "preset_idx"
    preset.agent_provider = "dummy_provider"
    win.controller.presets.get_current.return_value = preset

    return win


# Fixture tworząca instancję Loop z dummy_window
@pytest.fixture
def loop_instance(dummy_window):
    loop = Loop(window=dummy_window)
    # Override methods from BaseRunner
    loop.is_stopped = MagicMock(return_value=False)
    loop.prepare_input = MagicMock(side_effect=lambda x: x)
    loop.send_response = MagicMock()
    loop.set_busy = MagicMock()
    loop.set_status = MagicMock()
    # add_ctx returns a dummy context item (simulating a CtxItem)
    dummy_ctx_item = MagicMock()
    dummy_ctx_item.set_input = MagicMock()
    dummy_ctx_item.set_output = MagicMock()
    loop.add_ctx = MagicMock(return_value=dummy_ctx_item)
    return loop


# Fixture dla dummy BridgeContext-like object
@pytest.fixture
def dummy_context():
    context = MagicMock()
    dummy_ctx = DummyCtx()
    context.ctx = dummy_ctx
    context.history = ["dummy history"]
    return context


# Fixture dla dummy sygnałów
@pytest.fixture
def dummy_signals():
    return MagicMock()


def test_run_once_stopped(loop_instance):
    # When stopped, run_once should return an empty string
    loop_instance.is_stopped.return_value = True
    result = loop_instance.run_once("any input", [])
    assert result == ""


def test_run_next_stopped(loop_instance, dummy_context, dummy_signals):
    # run_next should return True immediately when stopped
    loop_instance.is_stopped.return_value = True
    result = loop_instance.run_next(dummy_context, {}, dummy_signals)
    assert result is True


def test_handle_evaluation_negative(loop_instance, dummy_signals):
    # For negative score, handle_evaluation should set status, send response and return True
    with patch("pygpt_net.utils.trans", lambda x: x):
        dummy_ctx = DummyCtx()
        result = loop_instance.handle_evaluation(dummy_ctx, "instruction", -1, dummy_signals)
        loop_instance.set_status.assert_called()
        loop_instance.send_response.assert_called_with(dummy_ctx, dummy_signals, KernelEvent.APPEND_END)
        assert result is True


def test_handle_evaluation_good_score(loop_instance, dummy_signals):
    # For a score equal or higher than good_score, handle_evaluation sends a finished message and returns True
    with patch("pygpt_net.utils.trans", lambda x: x):
        dummy_ctx = DummyCtx()
        result = loop_instance.handle_evaluation(dummy_ctx, "instruction", 80, dummy_signals)
        loop_instance.set_status.assert_called()
        # Check that send_response was called with a message containing "status.finished"
        args, kwargs = loop_instance.send_response.call_args
        assert "Finished. Score: 80%" in kwargs.get("msg", "")
        assert result is True


def test_handle_evaluation_else(loop_instance, dummy_signals):
    # For scores lower than good_score but non-negative, handle_evaluation proceeds to call next run
    with patch("pygpt_net.utils.trans", lambda x: x):
        dummy_ctx = DummyCtx()
        dummy_ctx.meta.id = "test_id"
        dummy_step = MagicMock()
        dummy_step.set_input = MagicMock()
        dummy_step.set_output = MagicMock()
        loop_instance.add_ctx.return_value = dummy_step

        result = loop_instance.handle_evaluation(dummy_ctx, "instruction", 50, dummy_signals)
        loop_instance.set_status.assert_called()
        loop_instance.set_busy.assert_called_with(dummy_signals)
        dummy_step.set_input.assert_called_with("instruction")
        loop_instance.window.core.agents.runner.call.assert_called()
        assert result == "runner call result"