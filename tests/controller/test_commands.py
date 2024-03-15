#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.15 10:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, call, patch

import PySide6

from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.controller import Command


def test_dispatch(mock_window):
    """Test dispatch sync"""
    command = Command(mock_window)
    mock_window.core.dispatcher.apply = MagicMock()
    mock_window.core.plugins.get_ids = MagicMock(return_value=['test'])
    mock_window.controller.plugins.is_enabled = MagicMock(return_value=True)
    command.handle_finished = MagicMock()

    event = Event('test')
    command.dispatch(event)
    mock_window.core.dispatcher.apply.assert_called()


def test_worker(mock_window):
    """Test worker"""
    command = Command(mock_window)
    mock_window.core.plugins.get_ids = MagicMock(return_value=['test'])
    mock_window.controller.plugins.is_enabled = MagicMock(return_value=True)
    mock_window.controller.command.is_stop = MagicMock(return_value=False)
    event = Event('test')
    command.worker(event, mock_window, MagicMock())
    mock_window.core.dispatcher.apply.assert_called()


def test_is_stop(mock_window):
    """Test is_stop"""
    command = Command(mock_window)
    command.stop = True
    assert command.is_stop() is True
    command.stop = False
    assert command.is_stop() is False


def test_handle_debug(mock_window):
    """Test handle_debug"""
    command = Command(mock_window)
    mock_window.core.debug.info = MagicMock()
    command.handle_debug('test')
    mock_window.core.debug.info.assert_called_once_with('test')


def test_handle_finished(mock_window):
    """Test handle_finished"""
    command = Command(mock_window)
    mock_window.ui.status = MagicMock()
    mock_window.controller.chat.input.send = MagicMock()
    event = Event('test')
    ctx = CtxItem()
    ctx.reply = True
    ctx.results = {'test': 'test'}
    event.ctx = ctx
    command.handle_finished(event)
    mock_window.ui.status.assert_called_once_with('')
