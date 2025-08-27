#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.28 00:00:00                  #
# ================================================== #

import pytest
from types import SimpleNamespace

from pygpt_net.core.agents.runners.loop import Loop
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.model import ModelItem


class ModelItemStub(ModelItem):
    def __init__(self, name="stub"):
        self.name = name

    def to_dict(self):
        return {"name": self.name}


class FakeModels:
    def __init__(self):
        self.get_calls = []

    def get(self, name):
        self.get_calls.append(name)
        return ModelItemStub(name=name)


class FakeEvaluation:
    def __init__(self, tools=None):
        self.tools = tools or ["tool1"]
        self.score_prompt = None
        self.complete_prompt = None
        self.score_history = None
        self.complete_history = None
        self.get_tools_calls = 0

    def get_tools(self):
        self.get_tools_calls += 1
        return self.tools

    def get_prompt_score(self, history):
        self.score_history = history
        return self.score_prompt or "SCORE_PROMPT"

    def get_prompt_complete(self, history):
        self.complete_history = history
        return self.complete_prompt or "COMPLETE_PROMPT"


class FakeRunner:
    def __init__(self):
        self.last_call_once = None
        self.call_once_return = None
        self.last_call = None
        self.call_return = True

    def call_once(self, context, extra, signals=None):
        self.last_call_once = {"context": context, "extra": extra, "signals": signals}
        return self.call_once_return

    def call(self, context, extra, signals):
        self.last_call = {"context": context, "extra": extra, "signals": signals}
        return self.call_return


class FakeCtxAPI:
    def __init__(self):
        self.all_calls = []

    def all(self, meta_id):
        self.all_calls.append(meta_id)
        return ["HISTORY1", "HISTORY2"]


class FakeConfig:
    def __init__(self, data=None):
        self.data = dict(data or {})
        self.get_calls = []

    def get(self, key, default=None):
        self.get_calls.append((key, default))
        return self.data.get(key, default)


class FakeAgents:
    def __init__(self, runner, evaluation):
        self.runner = runner
        self.observer = SimpleNamespace(evaluation=evaluation)


class FakeCore:
    def __init__(self, config, models, agents, ctx):
        self.config = config
        self.models = models
        self.agents = agents
        self.ctx = ctx


class FakePreset:
    def __init__(self, idx=1, agent_provider="llama", agent_openai=False, agent_provider_openai="openai"):
        self.idx = idx
        self.agent_provider = agent_provider
        self.agent_openai = agent_openai
        self.agent_provider_openai = agent_provider_openai


class FakePresetsController:
    def __init__(self, preset):
        self._preset = preset

    def get_current(self):
        return self._preset


class FakeWindow:
    def __init__(self, core, controller):
        self.core = core
        self.controller = controller


class FakeCtx:
    def __init__(self, meta_id="MID", model="eval-model"):
        self.meta = SimpleNamespace(id=meta_id)
        self.model = model
        self.extra = {}
        self.internal = None
        self.results = None
        self.input = None
        self.output = None

    def set_input(self, text):
        self.input = text

    def set_output(self, text):
        self.output = text


class FakeResponseCtx:
    def __init__(self, output):
        self.output = output


@pytest.fixture
def default_config():
    return FakeConfig(
        {
            "agent.llama.loop.mode": "score",
            "agent.llama.verbose": False,
            "agent.llama.loop.score": 75,
            "model": "default-model",
        }
    )


@pytest.fixture
def eval_stub():
    return FakeEvaluation()


@pytest.fixture
def runner_stub():
    return FakeRunner()


@pytest.fixture
def window(default_config, eval_stub, runner_stub):
    models = FakeModels()
    agents = FakeAgents(runner_stub, eval_stub)
    ctx_api = FakeCtxAPI()
    core = FakeCore(default_config, models, agents, ctx_api)
    preset = FakePreset(idx=7, agent_provider="llama", agent_openai=False, agent_provider_openai="openai")
    controller = SimpleNamespace(presets=FakePresetsController(preset))
    return FakeWindow(core, controller)


@pytest.fixture
def loop(window):
    lp = Loop.__new__(Loop)
    lp.window = window
    lp.next_instruction = ""
    lp.prev_score = -1
    lp.is_stopped = lambda: False
    lp.prepare_input = lambda s: f"PREP:{s}"
    lp.set_busy_calls = []
    lp.set_busy = lambda signals=None: lp.set_busy_calls.append(signals)
    lp.set_idle_calls = []
    lp.set_idle = lambda signals=None: lp.set_idle_calls.append(signals)
    lp.set_status_calls = []
    lp.set_status = lambda signals, msg: lp.set_status_calls.append((signals, msg))
    lp.send_response_calls = []
    lp.send_response = lambda ctx, signals, event, msg=None: lp.send_response_calls.append(
        (ctx, signals, event, msg)
    )
    lp.add_ctx = lambda ctx: FakeCtx(meta_id=ctx.meta.id, model=ctx.model)
    return lp


@pytest.fixture
def signals():
    return SimpleNamespace(name="signals")


def test_run_once_returns_output(loop, window):
    tools = ["t1", "t2"]
    window.core.agents.runner.call_once_return = FakeResponseCtx("Hello!")
    res = loop.run_once("Hi", tools, model_name="mA")
    assert res == "Hello!"
    assert window.core.models.get_calls[-1] == "mA"
    assert window.core.agents.runner.last_call_once is not None
    ctx = window.core.agents.runner.last_call_once["context"]
    extra = window.core.agents.runner.last_call_once["extra"]
    assert ctx.prompt == "PREP:Hi"
    assert extra["agent_provider"] == "react"
    assert extra["agent_tools"] == tools


def test_run_once_returns_no_response(loop, window):
    tools = ["t1"]
    window.core.agents.runner.call_once_return = None
    res = loop.run_once("X", tools, model_name="mB")
    assert res == "No response from evaluator."
    assert window.core.agents.runner.last_call_once is not None


def test_run_once_aborts_when_stopped(loop, window):
    tools = ["t1"]
    loop.is_stopped = lambda: True
    prev_models_calls = len(window.core.models.get_calls)
    prev_runner_calls = window.core.agents.runner.last_call_once
    res = loop.run_once("Y", tools, model_name="mC")
    assert res == ""
    assert len(window.core.models.get_calls) == prev_models_calls
    assert window.core.agents.runner.last_call_once == prev_runner_calls


def test_run_next_aborts_when_stopped(loop, signals):
    loop.is_stopped = lambda: True
    ctx = FakeCtx()
    context = SimpleNamespace(ctx=ctx, history=["H"], model=None, prompt=None)
    ret = loop.run_next(context, extra={}, signals=signals)
    assert ret is True
    assert loop.send_response_calls == []
    assert loop.set_busy_calls == []


def test_run_next_score_mode_uses_prompt_and_default_eval_model(loop, window, signals):
    window.core.config.data["agent.llama.loop.mode"] = "score"
    window.core.agents.observer.evaluation.score_prompt = "SCORE-P"
    captured = {}

    def run_once_stub(prompt, tools, model_name):
        captured["prompt"] = prompt
        captured["tools"] = tools
        captured["model_name"] = model_name
        loop.next_instruction = "NEXT_INSTR"
        loop.prev_score = 66
        return "ignored"

    loop.run_once = run_once_stub
    he_captured = {}

    def he_stub(ctx, instruction, score, sig):
        he_captured["ctx"] = ctx
        he_captured["instruction"] = instruction
        he_captured["score"] = score
        he_captured["signals"] = sig
        return "HE_RES"

    loop.handle_evaluation = he_stub
    ctx = FakeCtx(meta_id="CTX1", model="eval-model-123")
    history = ["H1", "H2"]
    context = SimpleNamespace(ctx=ctx, history=history, model=None, prompt=None)
    ret = loop.run_next(context, extra={}, signals=signals)
    assert ret == "HE_RES"
    assert loop.send_response_calls[0][2] == KernelEvent.APPEND_BEGIN
    assert len(loop.set_busy_calls) == 1
    assert window.core.agents.observer.evaluation.get_tools_calls == 1
    assert window.core.agents.observer.evaluation.score_history == history
    assert captured["prompt"] == "SCORE-P"
    assert captured["tools"] == window.core.agents.observer.evaluation.tools
    assert captured["model_name"] == "eval-model-123"
    assert he_captured["ctx"] is ctx
    assert he_captured["instruction"] == "NEXT_INSTR"
    assert he_captured["score"] == 66
    assert he_captured["signals"] is signals


def test_run_next_complete_mode_uses_prompt(loop, window, signals):
    window.core.config.data["agent.llama.loop.mode"] = "complete"
    window.core.agents.observer.evaluation.complete_prompt = "COMPLETE-P"
    captured = {}

    def run_once_stub(prompt, tools, model_name):
        captured["prompt"] = prompt
        captured["tools"] = tools
        captured["model_name"] = model_name
        loop.next_instruction = "DO"
        loop.prev_score = 10
        return "ignored"

    loop.run_once = run_once_stub
    loop.handle_evaluation = lambda ctx, instruction, score, sig: True
    ctx = FakeCtx()
    context = SimpleNamespace(ctx=ctx, history=["H"], model=None, prompt=None)
    ret = loop.run_next(context, extra={}, signals=signals)
    assert ret is True
    assert captured["prompt"] == "COMPLETE-P"


def test_run_next_uses_custom_eval_model_override(loop, window, signals):
    window.core.config.data["agent.llama.eval_model"] = "CUSTOM-M"
    captured = {}

    def run_once_stub(prompt, tools, model_name):
        captured["model_name"] = model_name
        loop.next_instruction = "X"
        loop.prev_score = 1
        return "ignored"

    loop.run_once = run_once_stub
    loop.handle_evaluation = lambda *args, **kwargs: True
    ctx = FakeCtx(model="SHOULD_NOT_USE")
    context = SimpleNamespace(ctx=ctx, history=[], model=None, prompt=None)
    loop.run_next(context, extra={}, signals=signals)
    assert captured["model_name"] == "CUSTOM-M"


def test_handle_evaluation_aborts_when_stopped(loop, signals):
    loop.is_stopped = lambda: True
    res = loop.handle_evaluation(FakeCtx(), "instr", 50, signals)
    assert res is True
    assert loop.send_response_calls == []
    assert loop.set_status_calls == []
    assert loop.set_idle_calls == []


def test_handle_evaluation_score_negative(loop, signals):
    loop.is_stopped = lambda: False
    ctx = FakeCtx()
    res = loop.handle_evaluation(ctx, "ignored", -1, signals)
    assert res is True
    assert loop.set_status_calls and loop.set_status_calls[-1][1].endswith("-1%")
    assert loop.send_response_calls[-1][2] == KernelEvent.APPEND_END
    assert len(loop.set_idle_calls) == 1


def test_handle_evaluation_finished_when_score_good(loop, window, signals):
    loop.is_stopped = lambda: False
    ctx = FakeCtx()
    res = loop.handle_evaluation(ctx, "ignored", 80, signals)
    assert res is True
    assert ctx.extra.get("agent_eval_finish") is True
    last_send = loop.send_response_calls[-1]
    assert last_send[2] == KernelEvent.APPEND_END
    assert "80%" in (last_send[3] or "")
    assert len(loop.set_idle_calls) >= 1


def test_handle_evaluation_proceeds_next_step_non_openai(loop, window, signals):
    loop.is_stopped = lambda: False
    window.controller.presets = FakePresetsController(
        FakePreset(idx=3, agent_provider="llama", agent_openai=False, agent_provider_openai="ignored")
    )
    window.core.agents.runner.call_return = "CALL_OK"
    ctx = FakeCtx(meta_id="CTX1", model="eval-m")
    instruction = "Please do X"
    score = 50
    res = loop.handle_evaluation(ctx, instruction, score, signals)
    assert res == "CALL_OK"
    assert loop.send_response_calls[-1][2] == KernelEvent.APPEND_DATA
    last_call = window.core.agents.runner.last_call
    assert last_call is not None
    call_ctx = last_call["context"]
    call_extra = last_call["extra"]
    step_ctx = call_ctx.ctx
    assert isinstance(step_ctx, FakeCtx)
    assert step_ctx.input == instruction
    assert step_ctx.output == ""
    assert step_ctx.internal is False
    assert step_ctx.results == [{"loop": {"score": score}}]
    assert step_ctx.extra.get("agent_input") is True
    assert step_ctx.extra.get("agent_evaluate") is True
    assert step_ctx.extra.get("footer") == f"Score: {score}%"
    assert window.core.ctx.all_calls[-1] == "CTX1"
    assert call_ctx.history == ["HISTORY1", "HISTORY2"]
    preset = window.controller.presets.get_current()
    assert call_ctx.preset is preset
    assert call_extra == {"agent_idx": preset.idx, "agent_provider": preset.agent_provider}
    assert isinstance(call_ctx.model, ModelItem)
    assert getattr(call_ctx.model, "name", None) == "default-model"
    assert loop.set_status_calls and loop.set_status_calls[-1][1].endswith("50%")


def test_handle_evaluation_proceeds_next_step_openai(loop, window, signals):
    loop.is_stopped = lambda: False
    window.controller.presets = FakePresetsController(
        FakePreset(idx=9, agent_provider="llama", agent_openai=True, agent_provider_openai="openai-prov")
    )
    ctx = FakeCtx(meta_id="M2", model="m")
    instruction = "Next step"
    score = 10
    _ = loop.handle_evaluation(ctx, instruction, score, signals)
    call_extra = window.core.agents.runner.last_call["extra"]
    assert call_extra["agent_provider"] == "openai-prov"


def test_handle_evaluation_does_not_finish_when_good_score_is_zero(loop, window, signals):
    loop.is_stopped = lambda: False
    window.core.config.data["agent.llama.loop.score"] = 0
    ctx = FakeCtx(meta_id="M3", model="m")
    instruction = "Continue"
    score = 100
    _ = loop.handle_evaluation(ctx, instruction, score, signals)
    assert window.core.agents.runner.last_call is not None


def test_is_verbose_reads_config(loop, window):
    assert loop.is_verbose() is False
    window.core.config.data["agent.llama.verbose"] = True
    assert loop.is_verbose() is True