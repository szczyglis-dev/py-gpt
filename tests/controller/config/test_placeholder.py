#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 19:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.config.placeholder import Placeholder


def test_apply_combo(mock_window):
    """Test apply"""
    placeholder = Placeholder(mock_window)
    option = {
        "type": "combo",
        "use": "models",
    }
    data = [{
        "name": "item1",
    }]
    placeholder.get_models = MagicMock(return_value=data)
    placeholder.apply(option)
    placeholder.get_models.assert_called_once()
    assert option["keys"] == data


def test_apply_dict(mock_window):
    """Test apply"""
    placeholder = Placeholder(mock_window)
    option = {
        "type": "dict",
        "keys": {
            "model": {
                "type": "combo",
                "use": "models",
            }
        }
    }
    data = [{
        "name": "item1",
    }]
    placeholder.get_models = MagicMock(return_value=data)
    placeholder.apply(option)
    placeholder.get_models.assert_called_once()
    assert option["keys"]["model"]["keys"] == data


def test_apply_models(mock_window):
    """Test apply"""
    placeholder = Placeholder(mock_window)
    option = {
        "type": "combo",
        "use": "models",
    }
    data = [{
        "name": "item1",
    }]
    placeholder.get_models = MagicMock(return_value=data)
    placeholder.apply(option)
    placeholder.get_models.assert_called_once()
    assert option["keys"] == data


def test_apply_presets(mock_window):
    """Test apply"""
    placeholder = Placeholder(mock_window)
    option = {
        "type": "combo",
        "use": "presets",
    }
    data = [{
        "name": "item1",
    }]
    placeholder.get_presets = MagicMock(return_value=data)
    placeholder.apply(option)
    placeholder.get_presets.assert_called_once()
    assert option["keys"] == data


def test_apply_langchain_providers(mock_window):
    """Test apply"""
    placeholder = Placeholder(mock_window)
    option = {
        "type": "combo",
        "use": "langchain_providers",
    }
    data = [{
        "name": "item1",
    }]
    placeholder.get_langchain_providers = MagicMock(return_value=data)
    placeholder.apply(option)
    placeholder.get_langchain_providers.assert_called_once()
    assert option["keys"] == data


def test_apply_llama_index_providers(mock_window):
    """Test apply"""
    placeholder = Placeholder(mock_window)
    option = {
        "type": "combo",
        "use": "llama_index_providers",
    }
    data = [{
        "name": "item1",
    }]
    placeholder.get_llama_index_providers = MagicMock(return_value=data)
    placeholder.apply(option)
    placeholder.get_llama_index_providers.assert_called_once()
    assert option["keys"] == data


def test_apply_vector_storage(mock_window):
    """Test apply"""
    placeholder = Placeholder(mock_window)
    option = {
        "type": "combo",
        "use": "vector_storage",
    }
    data = [{
        "name": "item1",
    }]
    placeholder.get_vector_storage = MagicMock(return_value=data)
    placeholder.apply(option)
    placeholder.get_vector_storage.assert_called_once()
    assert option["keys"] == data


def test_var_types(mock_window):
    """Test apply"""
    placeholder = Placeholder(mock_window)
    option = {
        "type": "combo",
        "use": "var_types",
    }
    data = [{
        "name": "item1",
    }]
    placeholder.get_var_types = MagicMock(return_value=data)
    placeholder.apply(option)
    placeholder.get_var_types.assert_called_once()
    assert option["keys"] == data


def test_get_llama_index_auto_index_policy(mock_window):
    """Conversation auto-index mode is exposed as a three-value enum."""
    placeholder = Placeholder(mock_window)

    data = placeholder.get_llama_index_auto_index_policy()

    assert [next(iter(item)) for item in data] == ["off", "all", "projects"]


def test_get_idx_injects_current_project_runtime_entry(mock_window):
    """Index placeholders expose __project__ only while a project is active."""
    placeholder = Placeholder(mock_window)
    mock_window.core.idx.get_idx_ids = MagicMock(return_value=[{"base": "Base"}])
    mock_window.core.idx.project.get_current_group_id = MagicMock(return_value=9)
    mock_window.core.idx.project.VIRTUAL_ID = "__project__"

    data = placeholder.get_idx({"none": False})

    assert next(iter(data[0])) == "__project__"
    assert "__project__" not in next(iter(data[0].values()))
    assert data[1] == {"base": "Base"}


def test_get_idx_can_explicitly_exclude_project_runtime_entry(mock_window):
    """Global-only settings do not receive the virtual project index."""
    placeholder = Placeholder(mock_window)
    mock_window.core.idx.get_idx_ids = MagicMock(return_value=[{"base": "Base"}])
    mock_window.core.idx.project.get_current_group_id = MagicMock(return_value=9)
    mock_window.core.idx.project.VIRTUAL_ID = "__project__"

    data = placeholder.get_idx({"none": False, "project": False})

    assert data == [{"base": "Base"}]
