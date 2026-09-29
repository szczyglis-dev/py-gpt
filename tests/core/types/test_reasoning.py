#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace

from pygpt_net.core.types.reasoning import (
    choose_effort,
    get_google_thinking_kwargs,
    get_model_efforts,
    get_provider_efforts,
    legacy_base_key,
    legacy_key_parts,
    normalize_effort,
)


def test_provider_efforts_return_copy_and_unknown_provider_is_empty():
    first = get_provider_efforts("openai")
    second = get_provider_efforts("openai")

    assert first == ["none", "minimal", "low", "medium", "high", "xhigh", "max"]
    assert first is not second
    assert get_provider_efforts("unknown") == []


def test_model_efforts_require_opt_in_and_use_exact_bundled_capabilities():
    disabled = SimpleNamespace(reasoning_effort=False, provider="openai", id="gpt-5.6-sol")
    bundled = SimpleNamespace(reasoning_effort=True, provider="google", id="gemini-3-pro-preview")

    assert get_model_efforts(disabled) == []
    assert get_model_efforts(bundled) == ["low", "high"]


def test_custom_opted_in_model_falls_back_to_provider_vocabulary():
    model = SimpleNamespace(reasoning_effort=True, provider="x_ai", id="custom-grok")

    assert get_model_efforts(model) == ["none", "low", "medium", "high"]


def test_google_thinking_kwargs_maps_gemini_25_to_budgets_and_newer_models_to_levels():
    assert get_google_thinking_kwargs("gemini-2.5-flash", "medium") == {"thinking_budget": 8192}
    assert get_google_thinking_kwargs("models/gemini-2.5-pro", "high") == {"thinking_budget": 32768}
    assert get_google_thinking_kwargs("gemini-3-flash-preview", "minimal") == {"thinking_level": "minimal"}
    assert get_google_thinking_kwargs("gemini-3-flash-preview", "invalid") == {}


def test_legacy_reasoning_key_helpers_only_accept_historical_suffixes():
    assert legacy_key_parts("gpt-5.6-terra-high") == ("gpt-5.6-terra", "high")
    assert legacy_base_key("gpt-5.6-terra-xhigh") == "gpt-5.6-terra"
    assert legacy_key_parts("gpt-5.6-terra-max") == (None, None)
    assert legacy_base_key(None) is None


def test_normalize_effort_is_case_insensitive_and_rejects_unknown_values():
    assert normalize_effort(" HIGH ") == "high"
    assert normalize_effort("max") == "max"
    assert normalize_effort("turbo") is None
    assert normalize_effort(None) is None


def test_choose_effort_keeps_valid_value_and_uses_nearest_lower_on_tie():
    assert choose_effort("medium", ["low", "medium", "high"]) == "medium"
    # Default target is high; medium and max are equally distant, lower wins.
    assert choose_effort(None, ["medium", "max"]) == "medium"
    assert choose_effort("minimal", ["none", "low"]) == "none"
    assert choose_effort("high", []) is None


def test_choose_effort_falls_back_to_first_value_if_list_contains_only_unknown_levels():
    assert choose_effort("high", ["custom-a", "custom-b"]) == "custom-a"
