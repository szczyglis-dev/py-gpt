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

from packaging.version import parse as parse_version, Version
from unittest.mock import MagicMock, patch

from pygpt_net.item.model import ModelItem
from tests.mocks import mock_window
from pygpt_net.core.models import Models
from pygpt_net.core.types import MODE_CHAT


def test_install(mock_window):
    """Test install"""
    models = Models(mock_window)
    models.provider = MagicMock()
    models.install()
    models.provider.install.assert_called_once()


def test_patch(mock_window):
    """Test patch"""
    models = Models(mock_window)
    models.provider = MagicMock()
    models.patch(parse_version("1.0.0"))
    models.provider.patch.assert_called_once()


def test_get(mock_window):
    """Test get"""
    model = ModelItem()
    models = Models(mock_window)
    models.items = {"test": model}
    assert models.get("test") == model


def test_get_by_idx(mock_window):
    """Test get by idx"""
    model = ModelItem()
    model.mode = ["chat"]
    models = Models(mock_window)
    models.items = {"gpt-5": model}
    assert models.get_by_idx(0, "chat") == "gpt-5"


def test_get_by_mode(mock_window):
    """Test get by mode"""
    model = ModelItem()
    model.mode = ["chat"]
    models = Models(mock_window)
    models.items = {"gpt-5": model}
    assert models.get_by_mode("chat") == {"gpt-5": model}


def test_has_model(mock_window):
    """Test has model"""
    model = ModelItem()
    model.mode = ["chat"]
    models = Models(mock_window)
    models.items = {"gpt-5": model}
    assert models.has_model("chat", "gpt-5")
    assert not models.has_model("chat", "gpt-6")


def test_get_default(mock_window):
    """Test get default"""
    model = ModelItem()
    model.mode = ["chat"]
    models = Models(mock_window)
    models.items = {"gpt-5": model}
    assert models.get_default("chat") == "gpt-5"
    assert models.get_default("test") is None


def test_get_tokens(mock_window):
    """Test get tokens"""
    model = ModelItem()
    model.tokens = 100
    models = Models(mock_window)
    models.items = {"gpt-5": model}
    assert models.get_tokens("gpt-5") == 100
    assert models.get_tokens("gpt-6") == 1


def test_get_num_ctx(mock_window):
    """Test get num ctx"""
    model = ModelItem()
    model.name = "gpt-5"
    model.ctx = 100
    models = Models(mock_window)
    models.items = {"gpt-5": model}
    assert models.get_num_ctx("gpt-5") == 100
    assert models.get_num_ctx("gpt-6") == 4096


def test_load(mock_window):
    """Test load"""
    model = ModelItem()
    model.name = "gpt-5"
    model.ctx = 100
    models = Models(mock_window)
    models.provider = MagicMock()
    models.provider.load.return_value = {"gpt-5": model}
    models.load()
    assert models.items == {"gpt-5": model}


def test_save(mock_window):
    """Test save"""
    model = ModelItem()
    model.name = "gpt-5"
    model.ctx = 100
    models = Models(mock_window)
    models.provider = MagicMock()
    models.items = {"gpt-5": model}
    models.save()
    models.provider.save.assert_called_once_with({"gpt-5": model})


def test_get_version(mock_window):
    """Test get version"""
    models = Models(mock_window)
    models.provider = MagicMock()
    models.provider.get_version.return_value = "1.0.0"
    assert models.get_version() == "1.0.0"


def test_prepare_client_args_runtime_custom_provider(mock_window):
    models = Models(mock_window)
    provider = MagicMock()
    provider.is_runtime_custom = True
    provider.name = "My API"
    provider.api_base = "https://custom.example/v1"
    provider.get_api_key.return_value = "CUSTOM-KEY"

    mock_window.core.llm.is_custom_provider = MagicMock(return_value=True)
    mock_window.core.llm.get = MagicMock(return_value=provider)

    model = ModelItem("custom-model")
    model.provider = "custom_my_api_12345678"

    args = models.prepare_client_args(MODE_CHAT, model)

    assert args["api_key"] == "CUSTOM-KEY"
    assert args["base_url"] == "https://custom.example/v1"
    assert "organization" not in args
    provider.get_api_key.assert_called_once_with()


def test_prepare_client_args_runtime_custom_provider_model_override_has_priority(mock_window):
    models = Models(mock_window)
    provider = MagicMock()
    provider.is_runtime_custom = True
    provider.name = "My API"
    provider.api_base = "https://provider.example/v1"
    provider.get_api_key.return_value = "PROVIDER-KEY"

    mock_window.core.llm.is_custom_provider = MagicMock(return_value=True)
    mock_window.core.llm.get = MagicMock(return_value=provider)

    model = ModelItem("custom-model")
    model.provider = "custom_my_api_12345678"
    model.custom_api_key = "MODEL-KEY"
    model.custom_api_endpoint = "https://model.example/v1"

    args = models.prepare_client_args(MODE_CHAT, model)

    assert args["api_key"] == "MODEL-KEY"
    assert args["base_url"] == "https://model.example/v1"


def test_prepare_client_args_missing_runtime_custom_provider_raises(mock_window):
    models = Models(mock_window)
    mock_window.core.llm.is_custom_provider = MagicMock(return_value=True)
    mock_window.core.llm.get = MagicMock(return_value=None)

    model = ModelItem("custom-model")
    model.provider = "custom_missing_12345678"

    try:
        models.prepare_client_args(MODE_CHAT, model)
    except RuntimeError as exc:
        assert "Custom provider is not configured" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for missing custom provider")
