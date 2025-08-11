#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.11 18:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, call, patch

import PySide6

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.controller import Debug


def test_update(mock_window):
    """Test update"""
    debug = Debug(mock_window)
    debug.update_menu = MagicMock()

    debug.update()
    debug.update_menu.assert_called_once()


def test_update_menu(mock_window):
    """Test update menu"""
    debug = Debug(mock_window)
    debug.is_logger = True
    mock_window.ui.menu = MagicMock()
    mock_window.ui.menu = MagicMock()
    mock_window.controller.dialogs.debug.get_ids = MagicMock(return_value=['test'])
    mock_window.controller.dialogs.debug.is_active = MagicMock(return_value=True)

    debug.update_menu()
    mock_window.ui.menu['debug.test'].setChecked.assert_called()
    mock_window.ui.menu['debug.logger'].setChecked.assert_called()


def test_on_update(mock_window):
    """Test on update"""
    debug = Debug(mock_window)
    debug.update_worker = MagicMock()
    mock_window.controller.dialogs.debug.get_ids = MagicMock(return_value=['test'])
    mock_window.controller.dialogs.debug.is_active = MagicMock(return_value=True)
    mock_window.controller.dialogs.debug.update_worker = MagicMock()

    debug.on_post_update(all=True)
    mock_window.controller.dialogs.debug.update_worker.assert_called()


def test_open_logger(mock_window):
    """Test open logger"""
    debug = Debug(mock_window)
    mock_window.ui.dialogs.open = MagicMock()
    mock_window.console = MagicMock()
    debug.window.ui.dialogs = mock_window.ui.dialogs

    debug.open_logger()
    mock_window.ui.dialogs.open.assert_called_once_with('logger', width=800, height=600)
    assert debug.is_logger is True


def test_close_logger(mock_window):
    """Test close logger"""
    debug = Debug(mock_window)
    mock_window.ui.dialogs.close = MagicMock()
    debug.window.ui.dialogs = mock_window.ui.dialogs

    debug.close_logger()
    mock_window.ui.dialogs.close.assert_called_once_with('logger')
    assert debug.is_logger is False


def test_toggle_logger(mock_window):
    """Test toggle logger"""
    debug = Debug(mock_window)
    debug.open_logger = MagicMock()
    debug.close_logger = MagicMock()

    debug.is_logger = False
    debug.toggle_logger()
    debug.open_logger.assert_called_once()
    debug.close_logger.assert_not_called()

    debug.is_logger = True
    debug.toggle_logger()
    debug.open_logger.assert_called_once()
    debug.close_logger.assert_called_once()


def test_clear_logger(mock_window):
    """Test clear logger"""
    debug = Debug(mock_window)
    mock_window.logger = MagicMock()
    mock_window.logger.clear = MagicMock()
    debug.window.logger = mock_window.logger

    debug.clear_logger()
    mock_window.logger.clear.assert_called_once()


def test_toggle(mock_window):
    """Test toggle"""
    debug = Debug(mock_window)
    debug.window.controller.dialogs.debug.show = MagicMock()
    debug.window.controller.dialogs.debug.hide = MagicMock()
    debug.on_post_update = MagicMock()
    debug.log = MagicMock()
    debug.update = MagicMock()
    debug.window.controller.dialogs.debug.is_active = MagicMock(return_value=False)

    debug.toggle('test')
    debug.window.controller.dialogs.debug.show.assert_called_once_with('test')
    debug.on_post_update.assert_called_once_with(True)
    debug.log.assert_called_once()
    debug.update.assert_called_once()

    debug.window.controller.dialogs.debug.is_active = MagicMock(return_value=True)
    debug.toggle('test')
    debug.window.controller.dialogs.debug.hide.assert_called_once_with('test')
    debug.on_post_update.assert_called_with(True)
    debug.log.assert_called_with('debug.test toggled')
    debug.update.assert_called_with()
