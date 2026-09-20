#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from unittest.mock import patch

import pytest

from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_VISION,
    MULTIMODAL_AUDIO,
    MULTIMODAL_IMAGE,
    MULTIMODAL_VIDEO,
)
from pygpt_net.item.model import ModelItem


def test_model_item_integrity():
    item = ModelItem()
    assert item.id is None
    assert item.name is None
    assert item.mode == ["chat"]
    assert item.input == ["text"]
    assert item.output == ["text"]
    assert item.multimodal == ["text"]
    assert item.langchain == {}
    assert item.llama_index == {}
    assert item.ctx == 0
    assert item.tokens == 0
    assert item.custom_api_endpoint == ""
    assert item.custom_api_key == ""
    assert item.default is False
    assert item.imported is False
    assert item.is_hidden is False
    assert item.provider == "openai"
    assert item.tool_calls is False


def test_model_from_dict_parses_csv_and_normalizes_optional_credentials():
    item = ModelItem("old")
    item.from_dict({
        "id": "m1",
        "name": "Model",
        "mode": "chat, vision, audio",
        "input": "text, image, audio",
        "output": "text, video",
        "ctx": 128000,
        "tokens": 4096,
        "custom_api_endpoint": None,
        "custom_api_key": None,
        "default": True,
        "extra": {"x": 1},
        "imported": True,
        "is_hidden": True,
        "provider": "custom_abc",
        "tool_calls": True,
        "llama_index.provider": "ollama",
        "llama_index.args": [{"name": "model", "value": "llama3"}],
        "llama_index.env": [{"name": "A", "value": "B"}],
    })

    assert item.id == "m1"
    assert item.mode == ["chat", "vision", "audio"]
    assert item.input == ["text", "image", "audio"]
    assert item.output == ["text", "video"]
    assert item.custom_api_endpoint == ""
    assert item.custom_api_key == ""
    assert item.provider == "custom_abc"
    assert item.llama_index["provider"] == "ollama"
    assert item.llama_index["args"][0]["value"] == "llama3"
    assert item.llama_index["env"][0]["name"] == "A"


def test_model_to_dict_converts_legacy_llama_index_dicts():
    item = ModelItem("m1")
    item.name = "Model"
    item.mode = ["chat", "vision"]
    item.input = ["text", "image"]
    item.output = ["text", "audio"]
    item.llama_index = {
        "args": {"model": "llama3", "temperature": 0.2},
        "env": {"TOKEN": "secret"},
    }

    data = item.to_dict()
    assert data["mode"] == "chat,vision"
    assert data["input"] == "text,image"
    assert data["output"] == "text,audio"
    assert {tuple(sorted(x.items())) for x in data["llama_index.args"]} == {
        tuple(sorted({"name": "model", "value": "llama3", "type": "str"}.items())),
        tuple(sorted({"name": "temperature", "value": 0.2, "type": "str"}.items())),
    }
    assert data["llama_index.env"] == [{"name": "TOKEN", "value": "secret"}]


def test_model_to_dict_preserves_llama_index_lists():
    args = [{"name": "model", "value": "x"}]
    env = [{"name": "A", "value": "1"}]
    item = ModelItem("m1")
    item.llama_index = {"args": args, "env": env}
    data = item.to_dict()
    assert data["llama_index.args"] is args
    assert data["llama_index.env"] is env


def test_runtime_custom_provider_is_openai_compatible():
    item = ModelItem("custom-model")
    item.provider = "custom_my_api_12345678"
    item.mode = ["chat", "llama_index"]
    assert item.is_openai_supported() is True
    assert item.is_supported(MODE_CHAT) is True


def test_non_compatible_unknown_provider_is_not_supported_in_chat_but_other_modes_follow_list():
    item = ModelItem("unknown-model")
    item.provider = "unknown_provider"
    item.mode = ["chat", "vision"]
    assert item.is_openai_supported() is False
    assert item.is_supported(MODE_CHAT) is False
    assert item.is_supported(MODE_VISION) is True


@pytest.mark.parametrize("model_id", [
    "gpt-5",
    "chatgpt-test",
    "o1-mini",
    "o3-mini",
    "o4-mini",
    "o5-test",
    "codex-mini",
    "computer-use-preview",
])
def test_is_gpt_accepts_supported_openai_response_families(model_id):
    item = ModelItem(model_id)
    item.provider = "openai"
    assert item.is_gpt() is True


def test_is_gpt_rejects_wrong_provider_gpt_oss_and_unknown_id():
    item = ModelItem("gpt-5")
    item.provider = "anthropic"
    assert item.is_gpt() is False

    item.provider = "openai"
    item.id = "gpt-oss-20b"
    assert item.is_gpt() is False

    item.id = "legacy-model"
    assert item.is_gpt() is False

    item.provider = "azure_openai"
    item.id = "gpt-4.1"
    assert item.is_gpt() is True


def test_ollama_detection_and_model_resolution():
    item = ModelItem("  fallback-model  ")
    item.provider = "ollama"
    assert item.is_ollama() is True
    assert item.get_ollama_model() == "fallback-model"

    item.provider = "openai"
    item.llama_index = None
    assert item.is_ollama() is False

    item.llama_index = {}
    assert item.is_ollama() is False

    item.llama_index = {"provider": "llama_index_ollama", "args": [
        {"name": "temperature", "value": 0.1},
        {"name": "model", "value": "  qwen3  "},
    ]}
    assert item.is_ollama() is True
    assert item.get_ollama_model() == "qwen3"

    item.llama_index = {"provider": "x", "args": [{"name": "model", "value": ""}]}
    assert item.get_ollama_model() == "fallback-model"


def test_mode_management_and_provider_accessor():
    item = ModelItem("m")
    assert item.get_provider() == "openai"
    assert item.has_mode("chat") is True

    item.add_mode("vision")
    item.add_mode("vision")
    assert item.mode.count("vision") == 1

    item.remove_mode("vision")
    item.remove_mode("missing")
    assert item.has_mode("vision") is False


def test_multimodal_capability_helpers():
    item = ModelItem("m")
    item.multimodal = []
    assert item.is_multimodal() is False
    item.multimodal = ["text"]
    assert item.is_multimodal() is True

    item.input = ["text", MULTIMODAL_IMAGE, MULTIMODAL_AUDIO, MULTIMODAL_VIDEO]
    item.output = ["text", MULTIMODAL_IMAGE, MULTIMODAL_AUDIO, MULTIMODAL_VIDEO]
    assert item.is_image_input() is True
    assert item.is_image_output() is True
    assert item.is_audio_input() is True
    assert item.is_audio_output() is True
    assert item.is_video_input() is True
    assert item.is_video_output() is True
    assert item.is_music_output() is True

    item.output = ["text"]
    item.mode = [MODE_VISION]
    assert item.is_image_output() is True
    assert item.is_audio_output() is False
    assert item.is_video_output() is False
    assert item.is_music_output() is False


def test_model_dump_str_and_serialization_error():
    item = ModelItem("m1")
    assert json.loads(item.dump())["id"] == "m1"
    assert str(item) == item.dump()

    with patch("pygpt_net.item.model.json.dumps", side_effect=TypeError):
        assert item.dump() == ""
