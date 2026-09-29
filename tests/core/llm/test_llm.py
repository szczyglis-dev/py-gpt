#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.05 12:30:00                  #
# ================================================== #

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.core.llm import LLM
from pygpt_net.core.types import MODE_LLAMA_INDEX


class DummyCustomLLM:
    def __init__(self, provider_id, name, api_base, api_key=""):
        self.id = provider_id
        self.name = name
        self.api_base = api_base
        self.api_key = api_key
        self.type = [MODE_LLAMA_INDEX]
        self.is_runtime_custom = True


def _patch_custom_llm():
    module = ModuleType("pygpt_net.provider.llms.custom.provider")
    module.CustomLLM = DummyCustomLLM
    return patch.dict(sys.modules, {"pygpt_net.provider.llms.custom.provider": module})


def _make_manager(rows):
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: rows if key == "api_custom_providers" else default
    window = SimpleNamespace(core=SimpleNamespace(config=config))
    return LLM(window), config


def test_make_custom_provider_id_is_stable_and_case_insensitive():
    first = LLM.make_custom_provider_id("My Local API")
    second = LLM.make_custom_provider_id("my local api")

    assert first == second
    assert first.startswith("custom_my_local_api_")
    assert len(first.rsplit("_", 1)[-1]) == 8
    assert LLM.is_custom_provider(first) is True
    assert LLM.is_custom_provider("openai") is False


def test_sync_custom_adds_valid_runtime_providers_and_keeps_builtin():
    rows = [
        {"name": "My API", "api_base": "https://api.example/v1", "api_key": "KEY"},
        {"name": "", "api_base": "https://ignored.example/v1", "api_key": "X"},
        {"name": "No URL", "api_base": "", "api_key": "Y"},
        "invalid-row",
    ]
    manager, _ = _make_manager(rows)
    builtin = MagicMock(name="builtin")
    builtin.name = "OpenAI"
    builtin.type = [MODE_LLAMA_INDEX]
    manager.register("openai", builtin)

    with _patch_custom_llm():
        manager.sync_custom(force=True)

    provider_id = manager.make_custom_provider_id("My API")
    provider = manager.get(provider_id)

    assert manager.get("openai") is builtin
    assert isinstance(provider, DummyCustomLLM)
    assert provider.name == "My API"
    assert provider.api_base == "https://api.example/v1"
    assert provider.api_key == "KEY"
    assert provider_id in manager.get_ids()
    assert provider_id in manager.get_ids(MODE_LLAMA_INDEX)
    assert manager.get_provider_name(provider_id) == "My API"


def test_sync_custom_updates_and_removes_runtime_provider_without_touching_builtin():
    rows = [{"name": "Runtime", "api_base": "https://one.example/v1", "api_key": "ONE"}]
    manager, config = _make_manager(rows)
    builtin = MagicMock(name="builtin")
    builtin.name = "OpenAI"
    builtin.type = [MODE_LLAMA_INDEX]
    manager.register("openai", builtin)

    with _patch_custom_llm():
        manager.sync_custom(force=True)
        provider_id = manager.make_custom_provider_id("Runtime")
        first = manager.get(provider_id)
        assert first.api_base == "https://one.example/v1"

        rows[:] = [{"name": "Runtime", "api_base": "https://two.example/v1", "api_key": "TWO"}]
        manager.sync_custom()
        second = manager.get(provider_id)
        assert second is not first
        assert second.api_base == "https://two.example/v1"
        assert second.api_key == "TWO"

        rows[:] = []
        manager.sync_custom()

    assert manager.get(provider_id) is None
    assert manager.get("openai") is builtin
    assert config.get.call_count > 0


def test_sync_custom_does_not_overwrite_provider_registered_by_code_with_same_id():
    rows = [{"name": "Collision", "api_base": "https://runtime.example/v1", "api_key": "KEY"}]
    manager, _ = _make_manager(rows)
    provider_id = manager.make_custom_provider_id("Collision")
    registered = MagicMock(name="registered")
    registered.name = "Registered provider"
    registered.type = [MODE_LLAMA_INDEX]
    manager.register(provider_id, registered)

    with _patch_custom_llm():
        manager.sync_custom(force=True)

    assert manager.get(provider_id) is registered
    assert provider_id not in manager._runtime_custom_ids


def test_get_choices_includes_runtime_custom_provider_and_sorts_by_name():
    rows = [
        {"name": "Zulu API", "api_base": "https://z.example/v1", "api_key": ""},
        {"name": "Alpha API", "api_base": "https://a.example/v1", "api_key": ""},
    ]
    manager, _ = _make_manager(rows)

    with _patch_custom_llm():
        choices = manager.get_choices()

    assert list(choices.values()) == ["Alpha API", "Zulu API"]
