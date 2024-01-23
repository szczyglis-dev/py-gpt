#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 19:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.calendar import Calendar


def test_setup(mock_window):
    """Test setup"""
    calendar = Calendar(mock_window)
    calendar.load = MagicMock()
    calendar.update = MagicMock()
    calendar.set_current = MagicMock()
    calendar.setup()
    calendar.load.assert_called_once()
    calendar.update.assert_called_once()
    calendar.set_current.assert_called_once()


def test_update(mock_window):
    """Test update"""
    calendar = Calendar(mock_window)
    calendar.on_page_changed = MagicMock()
    calendar.update()
    calendar.on_page_changed.assert_called_once()


def test_set_current(mock_window):
    """Test set current"""
    calendar = Calendar(mock_window)
    calendar.note.update_content = MagicMock()
    calendar.note.update_label = MagicMock()
    calendar.set_current()
    calendar.note.update_content.assert_called_once()
    calendar.note.update_label.assert_called_once()


def test_load(mock_window):
    """Test load"""
    calendar = Calendar(mock_window)
    mock_window.core.calendar.load_by_month = MagicMock()
    calendar.load()
    mock_window.core.calendar.load_by_month.assert_called_once()


def test_on_page_changed(mock_window):
    """Test on page changed"""
    calendar = Calendar(mock_window)
    calendar.load = MagicMock()
    calendar.note.refresh_ctx = MagicMock()
    calendar.note.refresh_num = MagicMock()
    calendar.on_page_changed(2021, 1)
    calendar.load.assert_called_once()
    calendar.note.refresh_ctx.assert_called_once()


def test_on_day_select(mock_window):
    """Test on day select"""
    calendar = Calendar(mock_window)
    calendar.note.update_content = MagicMock()
    calendar.note.update_label = MagicMock()
    calendar.on_day_select(2021, 1, 1)
    calendar.note.update_content.assert_called_once()
    calendar.note.update_label.assert_called_once()


def test_on_ctx_select(mock_window):
    """Test on context select"""
    calendar = Calendar(mock_window)
    mock_window.controller.ctx.append_search_string = MagicMock()
    calendar.on_ctx_select(2024, 1, 1)
    mock_window.controller.ctx.append_search_string.assert_called_once()
