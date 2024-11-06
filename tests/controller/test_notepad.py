#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from pygpt_net.item.notepad import NotepadItem
from tests.mocks import mock_window
from pygpt_net.controller import Notepad


def test_load(mock_window):
    """Test load"""
    notepad = Notepad(mock_window)
    items = {}
    item = NotepadItem()
    item.id = 1
    item.idx = 1
    item.title = 'test'
    item.initialized = True
    items[1] = item

    mock_window.ui.notepad = {1: MagicMock()}
    mock_window.core.notepad.load_all = MagicMock()
    mock_window.core.notepad.get_all = MagicMock(return_value=items)
    notepad.get_num_notepads = MagicMock(return_value=1)
    notepad.update_name = MagicMock()

    notepad.setup_tabs = MagicMock()

    notepad.setup()


def test_save(mock_window):
    """Test save"""
    notepad = Notepad(mock_window)
    mock_window.ui.notepad = {1: MagicMock()}
    mock_window.core.notepad.get_by_id = MagicMock(return_value=None)
    mock_window.core.notepad.update = MagicMock()
    notepad.save(1)
    mock_window.core.notepad.update.assert_called_once()


def test_setup(mock_window):
    """Test setup"""
    notepad = Notepad(mock_window)
    notepad.load = MagicMock()
    notepad.setup_tabs = MagicMock()
    notepad.setup()
    notepad.load.assert_called_once()
