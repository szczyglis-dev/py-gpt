#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 18:00:00                  #
# ================================================== #

import json
import os
from unittest.mock import MagicMock, patch, mock_open

import pygpt_net.item.attachment as attachment_mod
from tests.mocks import mock_window
from pygpt_net.provider.core.attachment.json_file import JsonFileProvider


def test_create_id(mock_window):
    provider = JsonFileProvider(mock_window)
    assert provider.create_id() is not None


def test_create(mock_window):
    provider = JsonFileProvider(mock_window)
    attachment = MagicMock(spec=attachment_mod.AttachmentItem)
    assert provider.create(attachment) is not None



'''
def test_load(mock_window):
    provider = JsonFileProvider(mock_window)
    data = {
        "__meta__": mock_window.core.config.append_meta(),
        "items": {
            "chat": {
                "9ebf4a35-fd11-417f-8874-0fa5dd5306ed": {
                    "id": "9ebf4a35-fd11-417f-8874-0fa5dd5306ed",
                    "name": ".env",
                    "remote_id": None,
                    "send": False
                }
            }
        }
    }
    json_data = json.dumps(data)
    with patch("os.path.exists") as os_path_exists:
        with patch('builtins.open', mock_open(read_data=json_data)):
            os_path_exists.return_value = True
            items = provider.load()
            assert len(items) == 1
            assert "9ebf4a35-fd11-417f-8874-0fa5dd5306ed" in items['chat']
'''

def test_save(mock_window):
    provider = JsonFileProvider(mock_window)

    item_id = "9ebf4a35-fd11-417f-8874-0fa5dd5306ed"
    item = MagicMock(spec=attachment_mod.AttachmentItem)

    items = {
        "chat": {
            item_id: item
        }
    }

    serialized = {
        "id": item_id,
        "name": "test.txt",
        "remote": None,
        "send": False
    }

    path = os.path.join(mock_window.core.config.path, provider.config_file)
    data = {}
    ary = {}

    with patch.object(provider, 'serialize', return_value=serialized):
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
            with patch.object(provider, 'serialize', return_value=serialized):
                provider.save(items)
                mock_json_dumps.assert_called_once_with(data, indent=4)
                mocked_file.assert_called_once_with(path, 'w', encoding="utf-8")
                mocked_file().write.assert_called_once_with(dump)


def test_truncate(mock_window):
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
    provider = JsonFileProvider(mock_window)
    item = MagicMock(spec=attachment_mod.AttachmentItem)
    item.id = "9ebf4a35-fd11-417f-8874-0fa5dd5306ed"
    item.name = "test.txt"
    item.remote = "xxx"
    item.send = False
    data = provider.serialize(item)
    assert data['id'] == item.id
    assert data['name'] == item.name
    assert data['remote'] == item.remote
    assert data['send'] == item.send


def test_deserialize(mock_window):
    provider = JsonFileProvider(mock_window)
    data = {
        "id": "9ebf4a35-fd11-417f-8874-0fa5dd5306ed",
        "name": "test.txt",
        "remote": None,
        "send": False
    }
    item = MagicMock(spec=attachment_mod.AttachmentItem)
    provider.deserialize(data, item)
    assert item.id == data['id']
    assert item.name == data['name']
    assert item.remote == data['remote']
    assert item.send == data['send']