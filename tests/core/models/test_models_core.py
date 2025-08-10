#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.29 18:00:00                  #
# ================================================== #

from packaging.version import parse as parse_version, Version
from unittest.mock import MagicMock, patch

from pygpt_net.item.model import ModelItem
from tests.mocks import mock_window
from pygpt_net.core.models import Models


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
