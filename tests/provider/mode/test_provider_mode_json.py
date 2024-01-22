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

from pygpt_net.item.mode import ModeItem
from tests.mocks import mock_window
from pygpt_net.provider.mode.json_file import JsonFileProvider


def test_get_version(mock_window):
    """Test get version"""
    provider = JsonFileProvider(mock_window)
    assert provider.get_version() is not None


def test_load(mock_window):
    provider = JsonFileProvider(mock_window)
    data = {
        "items": {
            "chat": {
                "id": "chat",
                "name": "chat",
                "label": "mode.chat",
                "default": True,
            },
        }
    }
    json_data = json.dumps(data)
    with patch("os.path.exists") as os_path_exists:
        with patch('builtins.open', mock_open(read_data=json_data)) as mock_file:
            os_path_exists.return_value = True
            items = provider.load()
            assert len(items) == 1
            assert "chat" in items


def test_save(mock_window):
    """Test save"""
    provider = JsonFileProvider(mock_window)
    item = ModeItem()
    item.id = "chat"
    item.name = "chat"
    item.label = "mode.chat"
    item.default = True
    items = {
        "chat": item
    }
    path = os.path.join(mock_window.core.config.get_app_path(), 'data', 'config', provider.config_file)
    data = {}
    ary = {}

    for id in items:
        mode = items[id]
        ary[id] = provider.serialize(mode)

    data['__meta__'] = mock_window.core.config.append_meta()
    data['items'] = ary
    dump = json.dumps(data, indent=4)
    with patch('builtins.open', mock_open()) as mocked_file:
        with patch('json.dumps', return_value=dump) as mock_json_dumps:
            provider.save(items)
            mock_json_dumps.assert_called_once_with(data, indent=4)
            mocked_file.assert_called_once_with(path, 'w', encoding="utf-8")
            mocked_file().write.assert_called_once_with(dump)


def test_serialize(mock_window):
    """Test serialize"""
    provider = JsonFileProvider(mock_window)
    item = ModeItem()
    item.id = "chat"
    item.name = "chat"
    item.label = "mode.chat"
    data = provider.serialize(item)
    assert data['id'] == item.id
    assert data['name'] == item.name
    assert data['label'] == item.label


def test_deserialize(mock_window):
    """Test deserialize"""
    provider = JsonFileProvider(mock_window)
    data = {
        "id": "chat",
        "name": "chat",
        "label": "mode.chat",
    }
    item = ModeItem()
    provider.deserialize(data, item)
    assert item.id == data['id']
    assert item.name == data['name']
    assert item.label == data['label']
