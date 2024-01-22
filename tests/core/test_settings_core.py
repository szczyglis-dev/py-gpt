#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.03 19:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch, mock_open

from tests.mocks import mock_window
from pygpt_net.core.settings import Settings


def test_get_options(mock_window):
    """Test get options"""
    settings = Settings(mock_window)
    settings.load = MagicMock()
    settings.options = {
        'test1': {
            'option1': 'value1',
            'option2': 'value2',
        },
        'test2': {
            'option1': 'value1',
            'option2': 'value2',
        },
    }
    assert settings.get_options() == settings.options
    assert settings.get_options('test1') == settings.options['test1']
    assert settings.get_options('test2') == settings.options['test2']


def test_get_persist_options(mock_window):
    """Test get persist options"""
    settings = Settings(mock_window)
    settings.load = MagicMock()
    settings.options = {
        'test1': {
            'option1': 'value1',
            'option2': 'value2',
        },
        'test2': {
            'option1': 'value1',
            'option2': 'value2',
            'persist': True,
        },
    }
    assert settings.get_persist_options() == ['test2']


def test_load(mock_window):
    """Test load settings"""
    settings = Settings(mock_window)
    mock_window.core.config.get_options = MagicMock(return_value={
        'test1': {
            'option1': 'value1',
            'option2': 'value2',
        },
        'test2': {
            'option1': 'value1',
            'option2': 'value2',
        },
    })
    settings.load()
    assert settings.options == {
        'test1': {
            'option1': 'value1',
            'option2': 'value2',
        },
        'test2': {
            'option1': 'value1',
            'option2': 'value2',
        },
    }
    assert settings.initialized is True


def test_load_user_settings(mock_window):
    """Test load user settings"""
    settings = Settings(mock_window)
    mock_window.core.config.load_config = MagicMock()
    settings.load_user_settings()
    mock_window.core.config.load_config.assert_called_once()


def test_load_app_settings(mock_window):
    """Test load app settings"""
    settings = Settings(mock_window)
    mock_window.core.config.from_base_config = MagicMock()
    mock_window.core.config.save = MagicMock()
    settings.get_persist_options = MagicMock(return_value=['test1', 'test2'])
    mock_window.core.config.data['test1'] = 'value1'
    mock_window.core.config.data['test2'] = 'value2'
    settings.load_app_settings()
    mock_window.core.config.from_base_config.assert_called_once()
    mock_window.core.config.save.assert_called_once_with('config.backup.json')
    assert mock_window.core.config.data['test1'] == 'value1'
    assert mock_window.core.config.data['test2'] == 'value2'


def test_load_default_editor(mock_window):
    """Test load default editor"""
    settings = Settings(mock_window)
    settings.load_editor = MagicMock()
    mock_window.core.config.from_file = MagicMock()
    settings.load_default_editor()
    settings.load_editor.assert_called_once()


def test_load_editor(mock_window):
    """Test load editor"""
    settings = Settings(mock_window)
    with patch('builtins.open', mock_open(read_data='test')) as mock_file:
        settings.load_editor('test.json')
        mock_file.assert_called_once_with(
            os.path.join(mock_window.core.config.path, 'test.json'),
            'r',
            encoding='utf-8'
        )
        assert mock_window.ui.dialog['config.editor'].file == 'test.json'


def test_save_editor(mock_window):
    """Test save editor"""
    settings = Settings(mock_window)
    json_data = '{"test": "test"}'
    mock_window.ui.editor['config'].toPlainText = MagicMock(return_value= json_data)
    mock_window.core.config.path = 'test'
    mock_window.ui.dialog['config.editor'].file = 'test.json'
    with patch('shutil.copyfile', 'copy'), \
            patch('builtins.open', mock_open()) as mock_file:
        settings.save_editor()
        mock_file.assert_called_once_with(
            os.path.join('test', 'test.json'),
            'w',
            encoding='utf-8'
        )
