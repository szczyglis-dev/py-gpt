#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.21 02:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, call

from tests.mocks import mock_window
from pygpt_net.controller import Audio


def test_setup(mock_window):
    """Test setup"""
    audio = Audio(mock_window)
    audio.update = MagicMock()
    audio.setup()
    audio.update.assert_called_once()


def test_toggle_input(mock_window):
    """Test toggle input"""
    audio = Audio(mock_window)
    audio.window.dispatch = MagicMock()
    audio.toggle_input(True)
    audio.window.dispatch.assert_called_once()


def test_toggle_output(mock_window):
    """Test toggle output"""
    audio = Audio(mock_window)
    audio.enable_output = MagicMock()
    audio.disable_output = MagicMock()
    audio.window.controller.plugins.is_enabled = MagicMock(return_value=True)
    audio.toggle_output()
    audio.disable_output.assert_called_once()
    audio.window.controller.plugins.is_enabled = MagicMock(return_value=False)
    audio.toggle_output()
    audio.enable_output.assert_called_once()


def test_enable_output(mock_window):
    """Test enable output"""
    audio = Audio(mock_window)
    audio.window.controller.plugins.enable = MagicMock()
    audio.window.controller.plugins.is_enabled = MagicMock(return_value=True)
    audio.window.core.config.save = MagicMock()
    audio.update = MagicMock()
    audio.enable_output()
    audio.window.controller.plugins.enable.assert_called_once()


def test_disable_output(mock_window):
    """Test disable output"""
    audio = Audio(mock_window)
    audio.window.controller.plugins.disable = MagicMock()
    audio.window.core.config.save = MagicMock()
    audio.update = MagicMock()
    audio.disable_output()
    audio.window.controller.plugins.disable.assert_called_once()


def test_disable_input(mock_window):
    """Test disable input"""
    audio = Audio(mock_window)
    audio.window.controller.plugins.disable = MagicMock()
    audio.window.core.config.save = MagicMock()
    audio.update = MagicMock()
    audio.disable_input()
    audio.window.controller.plugins.disable.assert_called_once()


def test_stop_input(mock_window):
    """Test stop input"""
    audio = Audio(mock_window)
    audio.window.dispatch = MagicMock()
    audio.stop_input()
    audio.window.dispatch.assert_called_once()


def test_stop_output(mock_window):
    """Test stop output"""
    audio = Audio(mock_window)
    audio.window.dispatch = MagicMock()
    audio.stop_output()
    audio.window.dispatch.assert_called_once()


def test_update(mock_window):
    """Test update"""
    audio = Audio(mock_window)
    audio.update_listeners = MagicMock()
    audio.update_menu = MagicMock()
    audio.update()
    audio.update_listeners.assert_called_once()
    audio.update_menu.assert_called_once()


def test_is_output_enabled(mock_window):
    """Test is output enabled"""
    audio = Audio(mock_window)
    audio.window.controller.plugins.is_enabled = MagicMock(return_value=True)
    assert audio.is_output_enabled()
    audio.window.controller.plugins.is_enabled = MagicMock(return_value=False)
    assert not audio.is_output_enabled()


def test_update_listeners(mock_window):
    """Test update listeners"""
    audio = Audio(mock_window)
    audio.stop_output = MagicMock()
    audio.window.controller.plugins.is_enabled = MagicMock(return_value=False)
    audio.update_listeners()
    audio.stop_output.assert_called_once()


def test_update_menu(mock_window):
    """Test update menu"""
    audio = Audio(mock_window)
    audio.window.controller.plugins.is_enabled = MagicMock(return_value=False)
    audio.window.ui.menu['audio.output.azure'].setChecked = MagicMock()
    audio.window.ui.menu['audio.output.tts'].setChecked = MagicMock()
    audio.window.ui.menu['audio.input.whisper'].setChecked = MagicMock()
    audio.update_menu()
    audio.window.ui.menu['audio.output.azure'].setChecked.assert_called()
    audio.window.ui.menu['audio.output.tts'].setChecked.assert_called()
    audio.window.ui.menu['audio.input.whisper'].setChecked.assert_called()


def test_read_text(mock_window):
    """Test read text"""
    audio = Audio(mock_window)
    audio.window.dispatch = MagicMock()
    audio.read_text('test')
    audio.window.dispatch.assert_called_once()
