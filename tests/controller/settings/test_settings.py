#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.03 16:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch, mock_open

from tests.mocks import mock_window
from pygpt_net.controller import Settings


def test_load(mock_window):
    """Test load"""
    settings = Settings(mock_window)
    settings.editor.load = MagicMock()
    settings.load()
    settings.editor.load.assert_called_once()


def test_save_all(mock_window):
    """Test save all"""
    settings = Settings(mock_window)
    mock_window.core.config.save = MagicMock()
    mock_window.core.presets.save_all = MagicMock()
    mock_window.controller.notepad.save_all = MagicMock()
    mock_window.ui.dialogs.alert = MagicMock()
    mock_window.ui.status = MagicMock()
    mock_window.controller.ui.update = MagicMock()
    settings.save_all()
    mock_window.core.config.save.assert_called_once()
    mock_window.core.presets.save_all.assert_called_once()
    mock_window.controller.notepad.save_all.assert_called_once()
    mock_window.ui.dialogs.alert.assert_called_once()
    mock_window.ui.status.assert_called_once()
    mock_window.controller.ui.update.assert_called_once()


def test_update(mock_window):
    """Test update"""
    settings = Settings(mock_window)
    settings.update_menu = MagicMock()
    settings.update()
    settings.update_menu.assert_called_once()


def test_update_menu(mock_window):
    """Test update menu"""
    settings = Settings(mock_window)
    mock_window.core.settings.ids = ['test']
    mock_window.core.settings.active = {'test': True}
    mock_window.ui.menu = {'config.test': MagicMock()}
    settings.update_menu()
    mock_window.ui.menu['config.test'].setChecked.assert_called_once_with(True)


def test_toggle_editor(mock_window):
    """Test toggle editor"""
    settings = Settings(mock_window)
    settings.close_window = MagicMock()
    settings.update = MagicMock()
    mock_window.core.settings.active = {'test': True}

    settings.toggle_editor('test')
    settings.close_window.assert_called_once_with('test')
    settings.update.assert_called_once()


def test_toggle_file_editor(mock_window):
    """Test toggle file editor"""
    settings = Settings(mock_window)
    mock_window.ui.dialog['config.editor'].file = 'test'
    mock_window.ui.dialogs.close = MagicMock()
    settings.update = MagicMock()
    mock_window.core.settings.active = {'editor': True}

    settings.toggle_file_editor('test')
    mock_window.ui.dialogs.close.assert_called_once_with('config.editor')
    settings.update.assert_called_once()
    assert mock_window.ui.dialog['config.editor'].file == 'test'


def test_close(mock_window):
    """Test close"""
    settings = Settings(mock_window)
    mock_window.ui.menu = {'test': MagicMock()}
    settings.close('test')
    mock_window.ui.menu['test'].setChecked.assert_called()


def test_close_window(mock_window):
    """Test close window"""
    settings = Settings(mock_window)
    mock_window.ui.dialogs.close = MagicMock()
    mock_window.core.settings.active = {'test': True}
    settings.close_window('test')
    mock_window.ui.dialogs.close.assert_called_once_with('config.test')
    assert mock_window.core.settings.active['test'] is False


def test_open_config_dir(mock_window):
    """Test open config dir"""
    settings = Settings(mock_window)
    mock_window.controller.files.open_dir = MagicMock()
    mock_window.core.config.path = 'test'
    settings.open_config_dir()
    mock_window.controller.files.open_dir.assert_called_once_with('test', True)


def test_welcome_settings(mock_window):
    """Test welcome settings"""
    settings = Settings(mock_window)
    settings.toggle_editor = MagicMock()
    mock_window.ui.dialogs.close = MagicMock()
    settings.welcome_settings()
    settings.toggle_editor.assert_called_once_with('settings')
    mock_window.ui.dialogs.close.assert_called_once_with('info.start')
