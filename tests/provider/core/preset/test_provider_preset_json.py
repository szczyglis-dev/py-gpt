#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.28 16:00:00                  #
# ================================================== #

import json
import os
from unittest.mock import MagicMock, patch, mock_open
from packaging.version import parse as parse_version
from pygpt_net.item.preset import PresetItem
from tests.mocks import mock_window
from pygpt_net.provider.core.preset.json_file import JsonFileProvider


def test_install(mock_window):
    """Test install"""
    provider = JsonFileProvider(mock_window)
    with patch('os.path.exists') as os_path_exists:
        with patch('shutil.copytree') as copy_tree:
            os_path_exists.return_value = False
            provider.install()
            copy_tree.assert_called_once()


def test_load(mock_window):
    """Test load"""
    provider = JsonFileProvider(mock_window)
    data = {
        "name": "Test",
        "ai_name": "",
        "user_name": "",
        "prompt": "You are a helpful assistant.",
        "chat": True,
        "completion": False,
        "img": False,
        "vision": False,
        "langchain": False,
        "assistant": False,
        "temperature": 1.0,
        "filename": None
    }
    dump = json.dumps(data)
    with patch('os.path.exists') as os_path_exists:
        with patch('os.listdir') as os_listdir:
            with patch('builtins.open', mock_open(read_data=dump)) as m:
                os_path_exists.return_value = True
                os_listdir.return_value = ['test.json']
                items = provider.load()
                os_listdir.assert_called_once()
                m.assert_called_once()
                assert isinstance(items, dict)
                assert len(items) == 1
                assert isinstance(items['test'], PresetItem)
                assert items['test'].name == 'Test'


def test_save(mock_window):
    """Test save"""
    provider = JsonFileProvider(mock_window)
    item = PresetItem()
    item.name = 'Test'
    item.ai_name = ''
    item.user_name = ''
    item.prompt = 'You are a helpful assistant.'
    item.chat = True
    item.completion = False
    item.img = False
    item.vision = False
    item.langchain = False
    item.assistant = False
    item.temperature = 1.0
    item.filename = None

    path = os.path.join(mock_window.core.config.path, 'presets', 'test.json')
    data = provider.serialize(item)
    data['__meta__'] = mock_window.core.config.append_meta()
    dump = json.dumps(data, indent=4)
    with patch('builtins.open', mock_open()) as mocked_file:
        with patch('json.dumps', return_value=dump) as mock_json_dumps:
            provider.save('test', item)
            mock_json_dumps.assert_called_once_with(data, indent=4)
            mocked_file.assert_called_once_with(path, 'w', encoding="utf-8")
            mocked_file().write.assert_called_once_with(dump)


def test_save_all(mock_window):
    """Test save all"""
    provider = JsonFileProvider(mock_window)
    item = PresetItem()
    item.name = 'Test'
    item.ai_name = ''
    item.user_name = ''
    item.prompt = 'You are a helpful assistant.'
    item.chat = True
    item.completion = False
    item.img = False
    item.vision = False
    item.langchain = False
    item.assistant = False
    item.temperature = 1.0
    item.filename = None
    items = {
        'test': item
    }
    path = os.path.join(mock_window.core.config.path, 'presets', 'test.json')
    data = provider.serialize(item)
    data['__meta__'] = mock_window.core.config.append_meta()
    dump = json.dumps(data, indent=4)
    with patch('builtins.open', mock_open()) as mocked_file:
        with patch('json.dumps', return_value=dump) as mock_json_dumps:
            provider.save_all(items)
            mock_json_dumps.assert_called_once_with(data, indent=4)
            mocked_file.assert_called_once_with(path, 'w', encoding="utf-8")
            mocked_file().write.assert_called_once_with(dump)


def test_remove(mock_window):
    """Test remove"""
    provider = JsonFileProvider(mock_window)
    with patch('os.path.exists') as os_path_exists:
        with patch('os.remove') as os_remove:
            os_path_exists.return_value = True
            provider.remove('test')
            os_remove.assert_called_once()


def test_patch(mock_window):
    mock_window.core.presets.items = {}
    provider = JsonFileProvider(mock_window)
    assert provider.patch(parse_version("1.0.0")) is False


def test_serialize(mock_window):
    """Test serialize"""
    provider = JsonFileProvider(mock_window)
    item = PresetItem()
    item.name = 'Test'
    item.ai_name = ''
    item.user_name = ''
    item.prompt = 'You are a helpful assistant.'
    item.chat = True
    item.completion = False
    item.img = False
    item.vision = False
   # item.langchain = False
    item.assistant = False
    item.temperature = 1.0
    item.filename = None

    data = provider.serialize(item)
    assert isinstance(data, dict)
    assert data['name'] == 'Test'
    assert data['ai_name'] == ''
    assert data['user_name'] == ''
    assert data['prompt'] == 'You are a helpful assistant.'
    assert data['chat'] is True
    assert data['completion'] is False
    assert data['img'] is False
    assert data['vision'] is False
#    assert data['langchain'] is False
    assert data['assistant'] is False
    assert data['temperature'] == 1.0
    assert data['filename'] is None


def test_deserialize(mock_window):
    """Test deserialize"""
    provider = JsonFileProvider(mock_window)
    data = {
        "name": "Test",
        "ai_name": "",
        "user_name": "",
        "prompt": "You are a helpful assistant.",
        "chat": True,
        "completion": False,
        "img": False,
        "vision": False,
        #"langchain": False,
        "assistant": False,
        "temperature": 1.0,
        "filename": None
    }
    item = PresetItem()
    provider.deserialize(data, item)
    assert isinstance(item, PresetItem)
    assert item.name == 'Test'
    assert item.ai_name == ''
    assert item.user_name == ''
    assert item.prompt == 'You are a helpful assistant.'
    assert item.chat is True
    assert item.completion is False
    assert item.img is False
    assert item.vision is False
   # assert item.langchain is False
    assert item.assistant is False
    assert item.temperature == 1.0
    assert item.filename is None
