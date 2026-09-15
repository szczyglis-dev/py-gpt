#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.context_manager.budget import ContextBudget


def make_window(values):
    window = SimpleNamespace(core=SimpleNamespace(config=MagicMock()))
    window.core.config.get.side_effect = lambda key: values.get(key)
    return window


def test_budget_uses_lower_model_or_application_context_limit():
    window = make_window({
        "max_total_tokens": 8000,
        "max_output_tokens": 1000,
        "context_threshold": 100,
        "context.advanced.threshold": 75,
        "context.advanced.target": 45,
    })
    model = SimpleNamespace(ctx=10000)

    budget = ContextBudget.build(window, model)

    assert budget.model_limit == 10000
    assert budget.app_limit == 8000
    assert budget.effective_limit == 8000
    assert budget.reserve_tokens == 1240  # 1000 output + 3% safety
    assert budget.input_limit == 6760
    assert budget.checkpoint_tokens == 5070
    assert budget.target_tail_tokens == 3042


def test_budget_uses_automatic_output_reserve_when_configured_zero():
    window = make_window({
        "max_total_tokens": 16000,
        "max_output_tokens": 0,
        "context_threshold": 0,
        "context.advanced.threshold": 75,
        "context.advanced.target": 45,
    })

    budget = ContextBudget.build(window, SimpleNamespace(ctx=16000))

    # 8% of 16k = 1280, safety = 3% = 480.
    assert budget.reserve_tokens == 1760
    assert budget.input_limit == 14240


def test_budget_caps_explicit_output_reserve_to_35_percent():
    window = make_window({
        "max_total_tokens": 10000,
        "max_output_tokens": 9000,
        "context_threshold": 0,
        "context.advanced.threshold": 99,
        "context.advanced.target": 99,
    })

    budget = ContextBudget.build(window, SimpleNamespace(ctx=10000))

    assert budget.reserve_tokens == 3800  # 3500 output + 300 safety
    assert budget.input_limit == 6200
    assert budget.checkpoint_tokens <= budget.input_limit
    assert budget.target_tail_tokens <= budget.checkpoint_tokens
    # Threshold/target are clamped to 95 and threshold - 5.
    assert budget.checkpoint_tokens == 5890
    assert budget.target_tail_tokens == 5580


def test_budget_supports_model_only_app_only_and_unbounded_cases():
    common = {
        "max_output_tokens": 0,
        "context_threshold": 0,
        "context.advanced.threshold": 75,
        "context.advanced.target": 45,
    }

    model_only = ContextBudget.build(
        make_window({**common, "max_total_tokens": 0}),
        SimpleNamespace(ctx=4096),
    )
    app_only = ContextBudget.build(
        make_window({**common, "max_total_tokens": 4096}),
        SimpleNamespace(ctx=0),
    )
    unbounded = ContextBudget.build(
        make_window({**common, "max_total_tokens": 0}),
        SimpleNamespace(ctx=0),
    )

    assert model_only.effective_limit == 4096
    assert app_only.effective_limit == 4096
    assert unbounded == ContextBudget(0, 0, 0, 0, 0, 0, 0)
