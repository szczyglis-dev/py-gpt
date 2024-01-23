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
from packaging.version import parse as parse_version, Version

from tests.mocks import mock_window
from pygpt_net.provider.core.config.json_file import JsonFileProvider


def test_install(mock_window):
    """Test install"""
    provider = JsonFileProvider(mock_window)
    provider.path = mock_window.core.config.path
    with patch('os.path.exists') as os_path_exists:
        os_path_exists.return_value = True
        provider.install()
        os_path_exists.assert_called_once()


def test_get_version(mock_window):
    """Test get version"""
    provider = JsonFileProvider(mock_window)
    provider.path = mock_window.core.config.path
    assert provider.get_version() is not None


def test_load(mock_window):
    """Test load"""
    provider = JsonFileProvider(mock_window)
    provider.path = mock_window.core.config.path
    data = {
        "foo": "bar"
    }
    json_data = json.dumps(data)
    with patch("os.path.exists") as os_path_exists:
        with patch('builtins.open', mock_open(read_data=json_data)) as mock_file:
            os_path_exists.return_value = True
            items = provider.load()
            assert len(items) == 1
            assert "foo" in items


def test_load_base(mock_window):
    """Test load base"""
    provider = JsonFileProvider(mock_window)
    provider.path_app = mock_window.core.config.get_app_path()
    data = {
        "foo": "bar"
    }
    json_data = json.dumps(data)
    with patch("os.path.exists") as os_path_exists:
        with patch('builtins.open', mock_open(read_data=json_data)) as mock_file:
            os_path_exists.return_value = True
            items = provider.load_base()
            assert len(items) == 1
            assert "foo" in items


def test_save(mock_window):
    """Test save"""
    provider = JsonFileProvider(mock_window)
    provider.path = mock_window.core.config.path
    items = {
        "foo": "bar"
    }
    path = os.path.join(mock_window.core.config.path, provider.config_file)
    data = items
    data['__meta__'] = mock_window.core.config.append_meta()
    dump = json.dumps(data, indent=4)
    with patch('builtins.open', mock_open()) as mocked_file:
        with patch('json.dumps', return_value=dump) as mock_json_dumps:
            provider.save(items)
            mock_json_dumps.assert_called_once_with(data, indent=4)
            mocked_file.assert_called_once_with(path, 'w', encoding="utf-8")
            mocked_file().write.assert_called_once_with(dump)


def test_get_options(mock_window):
    """Test get options"""
    provider = JsonFileProvider(mock_window)
    provider.path_app = mock_window.core.config.get_app_path()
    data = {
        "foo": "bar"
    }
    json_data = json.dumps(data)
    with patch("os.path.exists") as os_path_exists:
        with patch('builtins.open', mock_open(read_data=json_data)) as mock_file:
            os_path_exists.return_value = True
            items = provider.get_options()
            assert len(items) == 1
            assert type(items) == dict


def test_patch(mock_window):
    """Test patch"""
    provider = JsonFileProvider(mock_window)
    mock_window.core.config.data["__meta__"] = {}
    mock_window.core.config.data["__meta__"]["version"] = "1.0.0"
    assert provider.patch(parse_version("1.0.0")) is False

