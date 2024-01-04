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

from pygpt_net.item.assistant import AssistantItem
from tests.mocks import mock_window
from pygpt_net.provider.assistant.json_file import JsonFileProvider


def test_create_id(mock_window):
    provider = JsonFileProvider(mock_window)
    assert provider.create_id() is not None


def test_create(mock_window):
    provider = JsonFileProvider(mock_window)
    assistant = AssistantItem()
    assert provider.create(assistant) is not None


def test_load(mock_window):
    """Test load"""
    provider = JsonFileProvider(mock_window)
    data = {
        "items": {
            "asst_XXXX": {
                "id": "asst_XXXX",
                "name": "Test Assistant",
                "description": "",
                "instructions": "You are a test expert.",
                "model": "gpt-4-1106-preview",
                "meta": {},
                "attachments": {},
                "files": {
                    "file-XXXX": {
                        "id": "file-XXXX",
                        "name": "test.txt",
                        "path": "/home/path/test.txt"
                    },
                },
                "tools": {
                    "code_interpreter": True,
                    "retrieval": True,
                    "function": [
                        {
                            "name": "test",
                            "params": "{\"type\": \"object\", \"properties\": {}}",
                            "desc": "test desc"
                        }
                    ]
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
            assert "asst_XXXX" in items


def test_save(mock_window):
    """Test save"""
    provider = JsonFileProvider(mock_window)
    item = AssistantItem()
    item.id = "asst_XXXX"
    item.name = "Test Assistant"
    item.description = ""
    item.instructions = "You are a test expert."
    items = {
        "asst_XXXX": item,
    }
    path = os.path.join(mock_window.core.config.path, provider.config_file)
    data = {}
    ary = {}
    
    for id in items:
        assistant = items[id]
        ary[id] = provider.serialize(assistant)

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
    item = AssistantItem()
    item.id = "asst_XXXX"
    item.name = "Test Assistant"
    item.description = ""
    item.instructions = "You are a test expert."
    item.model = "gpt-4-1106-preview"
    item.meta = {}
    item.attachments = {}
    item.files = {
        "file-XXXX": {
            "id": "file-XXXX",
            "name": "test.txt",
            "path": "/home/path/test.txt"
        },
    }
    item.tools = {
        "code_interpreter": True,
        "retrieval": True,
        "function": [
            {
                "name": "test",
                "params": "{\"type\": \"object\", \"properties\": {}}",
                "desc": "test desc"
            }
        ]
    }
    data = provider.serialize(item)
    assert data['id'] == "asst_XXXX"
    assert data['name'] == "Test Assistant"
    assert data['description'] == ""
    assert data['instructions'] == "You are a test expert."
    assert data['model'] == "gpt-4-1106-preview"
    assert data['meta'] == {}
    assert data['attachments'] == {}
    assert data['files'] == {
        "file-XXXX": {
            "id": "file-XXXX",
            "name": "test.txt",
            "path": "/home/path/test.txt"
        },
    }
    assert data['tools'] == {
        "code_interpreter": True,
        "retrieval": True,
        "function": [
            {
                "name": "test",
                "params": "{\"type\": \"object\", \"properties\": {}}",
                "desc": "test desc"
            }
        ]
    }


def test_deserialize(mock_window):
    """Test deserialize"""
    provider = JsonFileProvider(mock_window)
    data = {
        "id": "asst_XXXX",
        "name": "Test Assistant",
        "description": "",
        "instructions": "You are a test expert.",
        "model": "gpt-4-1106-preview",
        "meta": {},
        "attachments": {},
        "files": {
            "file-XXXX": {
                "id": "file-XXXX",
                "name": "test.txt",
                "path": "/home/path/test.txt"
            },
        },
        "tools": {
            "code_interpreter": True,
            "retrieval": True,
            "function": [
                {
                    "name": "test",
                    "params": "{\"type\": \"object\", \"properties\": {}}",
                    "desc": "test desc"
                }
            ]
        }
    }
    item = AssistantItem()
    provider.deserialize(data, item)
    assert item.id == "asst_XXXX"
    assert item.name == "Test Assistant"
    assert item.description == ""
    assert item.instructions == "You are a test expert."
    assert item.model == "gpt-4-1106-preview"
    assert item.meta == {}
    assert item.attachments == {}
    assert item.files == {
        "file-XXXX": {
            "id": "file-XXXX",
            "name": "test.txt",
            "path": "/home/path/test.txt"
        },
    }
    assert item.tools == {
        "code_interpreter": True,
        "retrieval": True,
        "function": [
            {
                "name": "test",
                "params": "{\"type\": \"object\", \"properties\": {}}",
                "desc": "test desc"
            }
        ]
    }
