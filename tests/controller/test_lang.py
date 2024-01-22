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

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller import Lang


def test_setup(mock_window):
    """Test setup"""
    lang = Lang(mock_window)
    mock_window.core.config.get_available_langs = MagicMock(return_value=[])
    lang.update = MagicMock()
    lang.setup()
    lang.update.assert_called_once()


def test_update(mock_window):
    """Test update"""
    lang = Lang(mock_window)
    mock_window.core.config.data['lang'] = 'en'
    mock_window.ui.menu = {}
    mock_window.ui.menu['lang'] = {'en': MagicMock()}
    lang.update()
    mock_window.ui.menu['lang']['en'].setChecked.assert_called()


def test_toggle(mock_window):
    """Test toggle"""
    lang = Lang(mock_window)
    lang.update = MagicMock()
    mock_window.controller.plugins.update_info = MagicMock()
    mock_window.controller.notepad.get_num_notepads = MagicMock(return_value=0)
    lang.plugins.apply = MagicMock()
    mock_window.controller.ctx.common.update_label_by_current = MagicMock()
    mock_window.controller.ctx.update = MagicMock()
    mock_window.controller.ui.update = MagicMock()
    mock_window.settings = MagicMock()
    lang.toggle('en')
    assert mock_window.core.config.data['lang'] == 'en'
    lang.update.assert_called_once()
    lang.plugins.apply.assert_called_once()
    mock_window.controller.ctx.common.update_label_by_current.assert_called_once()
    mock_window.controller.ctx.update.assert_called_once()
    mock_window.controller.ui.update.assert_called_once()


def test_toggle_plugins(mock_window):
    """Test toggle plugins"""
    lang = Lang(mock_window)
    mock_window.plugin_settings = MagicMock()
    mock_window.core.plugins.plugins = {}
    mock_window.plugin_settings.update_list = MagicMock()
    mock_window.controller.plugins.set_by_tab = MagicMock()
    lang.plugins.apply()
    mock_window.plugin_settings.update_list.assert_called_once()
    mock_window.controller.plugins.set_by_tab.assert_called_once()


def test_update_settings_dialogs(mock_window):
    """Test update settings dialogs"""
    lang = Lang(mock_window)
    mock_window.settings = MagicMock()
    mock_window.controller.settings.editor.initialized = False
    mock_window.controller.settings.editor.load_config_options = MagicMock()
    lang.settings.apply()
    mock_window.controller.settings.editor.load_config_options.assert_called_once()
    mock_window.controller.settings.editor.initialized = True
