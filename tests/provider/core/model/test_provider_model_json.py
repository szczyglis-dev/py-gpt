#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.04 13:00:00                  #
# ================================================== #

import json
import os
from unittest.mock import MagicMock, patch, mock_open

from pygpt_net.item.model import ModelItem
from tests.mocks import mock_window
from pygpt_net.provider.core.model.json_file import JsonFileProvider


def test_install(mock_window):
    """Test install"""
    provider = JsonFileProvider(mock_window)
    with patch('os.path.exists') as os_path_exists:
        os_path_exists.return_value = True
        provider.install()
        os_path_exists.assert_called_once()


def test_get_version(mock_window):
    """Test get version"""
    provider = JsonFileProvider(mock_window)
    provider.path = mock_window.core.config.get_path()
    assert provider.get_version() is not None


def test_load(mock_window):
    provider = JsonFileProvider(mock_window)
    data = {
        "items": {
            "gpt-3.5-turbo": {
                "id": "gpt-3.5-turbo",
                "name": "gpt-3.5-turbo",
                "mode": [
                    "chat",
                    "assistant",
                    "langchain"
                ],
                "langchain": {
                    "provider": "openai",
                    "mode": [
                        "chat"
                    ],
                    "args": {
                        "model_name": "gpt-3.5-turbo"
                    }
                },
                "ctx": 4096,
                "tokens": 4096,
                "default": False
            },
        }
    }
    json_data = json.dumps(data)
    with patch("os.path.exists") as os_path_exists:
        with patch('builtins.open', mock_open(read_data=json_data)) as mock_file:
            os_path_exists.return_value = True
            items = provider.load()
            assert len(items) == 1
            assert "gpt-3.5-turbo" in items


def test_save(mock_window):
    """Test save"""
    provider = JsonFileProvider(mock_window)
    item = ModelItem()
    item.id = "gpt-3.5-turbo"
    item.name = "gpt-3.5-turbo"
    item.mode = ["chat", "assistant", "langchain"]
    item.langchain = {
        "provider": "openai",
        "mode": ["chat"],
        "args": {
            "model_name": "gpt-3.5-turbo"
        }
    }
    item.ctx = 4096
    item.tokens = 4096
    item.default = False
    items = {
        "gpt-3.5-turbo": item
    }
    path = os.path.join(mock_window.core.config.path, provider.config_file)
    data = {}
    ary = {}

    for id in items:
        model = items[id]
        ary[id] = provider.serialize(model)

    data['__meta__'] = mock_window.core.config.append_meta()
    data['items'] = ary
    dump = json.dumps(data, indent=4)
    with patch('builtins.open', mock_open()) as mocked_file:
        with patch('json.dumps', return_value=dump) as mock_json_dumps:
            provider.save(items)
            mock_json_dumps.assert_called_once_with(data, indent=4)
            mocked_file.assert_called_once_with(path, 'w', encoding="utf-8")
            mocked_file().write.assert_called_once_with(dump)
