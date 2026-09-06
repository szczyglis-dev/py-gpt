#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
from pathlib import Path
from types import SimpleNamespace


def _load_module():
    path = Path(__file__).resolve().parents[3] / "src" / "pygpt_net" / "provider" / "api" / "google" / "utils.py"
    spec = importlib.util.spec_from_file_location("pygpt_google_utils_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


utils = _load_module()


def test_safe_get_supports_dict_attributes_and_sequence_indexes():
    obj = SimpleNamespace(data={"items": [SimpleNamespace(value="ok")]})

    assert utils.safe_get(obj, "data.items.0.value") == "ok"
    assert utils.safe_get(obj, "data.items.9.value") is None
    assert utils.safe_get(obj, "missing.value") is None


def test_as_int_handles_integral_float_text_and_invalid_values():
    assert utils.as_int("12") == 12
    assert utils.as_int("12.9") == 12
    assert utils.as_int(None) is None
    assert utils.as_int("invalid") is None


def test_capture_google_usage_prefers_total_minus_prompt_and_tracks_reasoning():
    state = SimpleNamespace(usage_vendor=None, usage_payload=None)
    usage = {
        "prompt_token_count": "10",
        "candidates_token_count": 3,
        "thoughts_token_count": "2",
        "total_token_count": 17,
    }

    utils.capture_google_usage(state, usage)

    assert state.usage_vendor == "google"
    assert state.usage_payload == {"in": 10, "out": 7, "reasoning": 2, "total": 17}


def test_capture_google_usage_falls_back_to_candidate_count_without_total():
    state = SimpleNamespace(usage_vendor=None, usage_payload=None)

    utils.capture_google_usage(state, {"input_tokens": 5, "output_tokens": 8})

    assert state.usage_payload == {"in": 5, "out": 8, "reasoning": 0, "total": None}


def test_capture_google_usage_ignores_empty_metadata():
    state = SimpleNamespace(usage_vendor="unchanged", usage_payload={"old": True})

    utils.capture_google_usage(state, None)

    assert state.usage_vendor == "unchanged"
    assert state.usage_payload == {"old": True}


def test_extract_google_urls_collects_modern_grounding_citations_and_annotations_once():
    payload = {
        "candidates": [{
            "grounding_metadata": {
                "grounding_chunks": [
                    {"web": {"uri": " https://example.com/a "}},
                    {"retrieved_context": {"url": "https://example.com/b"}},
                    {"web": {"url": "ftp://ignored.example"}},
                ],
                "search_entry_point": {"url": "https://example.com/c"},
            },
            "citation_metadata": {
                "citation_sources": [
                    {"uri": "https://example.com/a"},
                    {"url": "https://example.com/d"},
                ]
            },
        }],
        "output": [{"annotations": [{"type": "url_citation", "url": "https://example.com/e"}]}],
    }

    assert utils.extract_google_urls(payload) == [
        "https://example.com/e",
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
        "https://example.com/d",
    ]


def test_extract_google_urls_treats_candidate_shaped_raw_dict_as_candidate():
    raw = {
        "groundingMetadata": {
            "groundingChunks": [{"web": {"uri": "https://example.com/raw"}}]
        }
    }

    assert utils.extract_google_urls(raw) == ["https://example.com/raw"]


def test_collect_google_citations_updates_state_and_context_without_duplicates():
    ctx = SimpleNamespace(urls=None)
    state = SimpleNamespace(citations=None)
    chunk = SimpleNamespace(candidates=[{
        "grounding_metadata": {
            "grounding_chunks": [
                {"web": {"uri": "https://example.com/one"}},
                {"web": {"uri": "https://example.com/one"}},
            ]
        },
        "citation_metadata": {
            "citation_sources": [{"url": "https://example.com/two"}]
        },
    }])

    utils.collect_google_citations(ctx, state, chunk)

    assert state.citations == ["https://example.com/one", "https://example.com/two"]
    assert ctx.urls == ["https://example.com/one", "https://example.com/two"]
