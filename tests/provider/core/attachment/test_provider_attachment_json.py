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

from pygpt_net.item.attachment import AttachmentItem
from tests.mocks import mock_window
from pygpt_net.provider.core.attachment.json_file import JsonFileProvider


def test_create_id(mock_window):
    """Test create id"""
    provider = JsonFileProvider(mock_window)
    assert provider.create_id() is not None


def test_create(mock_window):
    """Test create"""
    provider = JsonFileProvider(mock_window)
    attachment = AttachmentItem()
    assert provider.create(attachment) is not None


def test_load(mock_window):
    """Test load"""
    provider = JsonFileProvider(mock_window)
    data = {
        "items": {
            "chat": {
                "9ebf4a35-fd11-417f-8874-0fa5dd5306ed": {
                    "id": "9ebf4a35-fd11-417f-8874-0fa5dd5306ed",
                    "name": ".env",
                    "path": "/home/path/file",
                    "remote": None,
                    "send": False
                }
            }
        }
    }
    json_data = json.dumps(data)
    with patch("os.path.exists") as os_path_exists:
        with patch('builtins.open', mock_open(read_data=json_data)) as mock_file:
            os_path_exists.return_value = True
            items = provider.load()
            assert len(items) == 1
            assert "9ebf4a35-fd11-417f-8874-0fa5dd5306ed" in items['chat']


def test_save(mock_window):
    """Test save"""
    provider = JsonFileProvider(mock_window)
    item = AttachmentItem()
    item.id = "9ebf4a35-fd11-417f-8874-0fa5dd5306ed"
    item.name = "test.txt"
    items = {
        "chat": {
            "9ebf4a35-fd11-417f-8874-0fa5dd5306ed": item
        }
    }
    path = os.path.join(mock_window.core.config.path, provider.config_file)
    data = {}
    ary = {}
    for mode in items:
        ary[mode] = {}
        for id in items[mode]:
            attachment = items[mode][id]
            ary[mode][id] = provider.serialize(attachment)

    data['__meta__'] = mock_window.core.config.append_meta()
    data['items'] = ary
    dump = json.dumps(data, indent=4)

    with patch('builtins.open', mock_open()) as mocked_file:
        with patch('json.dumps', return_value=dump) as mock_json_dumps:
            provider.save(items)
            mock_json_dumps.assert_called_once_with(data, indent=4)
            mocked_file.assert_called_once_with(path, 'w', encoding="utf-8")
            mocked_file().write.assert_called_once_with(dump)


def test_truncate(mock_window):
    """Test truncate"""
    provider = JsonFileProvider(mock_window)
    path = os.path.join(mock_window.core.config.path, provider.config_file)
    data = {'__meta__': mock_window.core.config.append_meta(), 'items': {}}
    dump = json.dumps(data, indent=4)

    with patch('builtins.open', mock_open()) as mocked_file:
        with patch('json.dumps', return_value=dump) as mock_json_dumps:
            provider.truncate('chat')
            mock_json_dumps.assert_called_once_with(data, indent=4)
            mocked_file.assert_called_once_with(path, 'w', encoding="utf-8")
            mocked_file().write.assert_called_once_with(dump)


def test_serialize(mock_window):
    """Test serialize"""
    provider = JsonFileProvider(mock_window)
    item = AttachmentItem()
    item.id = "9ebf4a35-fd11-417f-8874-0fa5dd5306ed"
    item.name = "test.txt"
    item.path = "/home/path/file"
    item.remote = None
    item.send = False
    data = provider.serialize(item)
    assert data['id'] == item.id
    assert data['name'] == item.name
    assert data['path'] == item.path
    assert data['remote'] == item.remote
    assert data['send'] == item.send


def test_deserialize(mock_window):
    """Test deserialize"""
    provider = JsonFileProvider(mock_window)
    data = {
        "id": "9ebf4a35-fd11-417f-8874-0fa5dd5306ed",
        "name": "test.txt",
        "path": "/home/path/file",
        "remote": None,
        "send": False
    }
    item = AttachmentItem()
    provider.deserialize(data, item)
    assert item.id == data['id']
    assert item.name == data['name']
    assert item.path == data['path']
    assert item.remote == data['remote']
    assert item.send == data['send']
