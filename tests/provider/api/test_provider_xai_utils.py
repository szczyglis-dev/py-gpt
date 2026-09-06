#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
from pathlib import Path
from types import SimpleNamespace


def _load_module():
    path = Path(__file__).resolve().parents[3] / "src" / "pygpt_net" / "provider" / "api" / "x_ai" / "utils.py"
    spec = importlib.util.spec_from_file_location("pygpt_xai_utils_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


utils = _load_module()


def test_safe_get_and_as_int_cover_nested_and_invalid_values():
    obj = {"items": [SimpleNamespace(value="7")]}

    assert utils.safe_get(obj, "items.0.value") == "7"
    assert utils.safe_get(obj, "items.4.value") is None
    assert utils.as_int("7.8") == 7
    assert utils.as_int(object()) is None


def test_capture_openai_usage_includes_reasoning_in_output_total():
    state = SimpleNamespace(usage_vendor=None, usage_payload=None)
    usage = {
        "prompt_tokens": 11,
        "completion_tokens": 4,
        "total_tokens": 18,
        "completion_tokens_details": {"reasoning_tokens": 3},
    }

    utils.capture_openai_usage(state, usage)

    assert state.usage_vendor == "openai"
    assert state.usage_payload == {"in": 11, "out": 7, "reasoning": 3, "total": 18}


def test_capture_google_usage_uses_nonnegative_total_delta():
    state = SimpleNamespace(usage_vendor=None, usage_payload=None)

    utils.capture_google_usage(
        state,
        {
            "prompt_token_count": 10,
            "total_token_count": 7,
            "candidates_reasoning_token_count": 2,
        },
    )

    assert state.usage_vendor == "google"
    assert state.usage_payload == {"in": 10, "out": 0, "reasoning": 2, "total": 7}


def test_collect_google_citations_collects_legacy_shapes_and_deduplicates():
    ctx = SimpleNamespace(urls=None)
    state = SimpleNamespace(citations="not-a-list")
    chunk = SimpleNamespace(candidates=[{
        "grounding_metadata": {
            "grounding_attributions": [
                {"web": {"uri": " https://example.com/a "}},
                {"source": {"url": "https://example.com/b"}},
            ],
            "search_entry_point": {"url": "https://example.com/c"},
        },
        "citation_metadata": {
            "citation_sources": [
                {"url": "https://example.com/a"},
                {"url": "mailto:test@example.com"},
            ]
        },
        "content": {
            "parts": [{
                "citation_metadata": {
                    "citations": [{"uri": "https://example.com/d"}]
                }
            }]
        },
    }])

    utils.collect_google_citations(ctx, state, chunk)

    assert state.citations == [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
        "https://example.com/d",
    ]
    assert ctx.urls == state.citations


def test_capture_helpers_ignore_empty_usage():
    state = SimpleNamespace(usage_vendor="old", usage_payload={"keep": True})

    utils.capture_openai_usage(state, None)
    utils.capture_google_usage(state, {})

    assert state.usage_vendor == "old"
    assert state.usage_payload == {"keep": True}
