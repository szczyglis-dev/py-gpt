#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.10 02:00:00                  #
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
    notepad.update_name.assert_called_once_with(1, 'test', False)


def test_reload_tab_names(mock_window):
    """Test reload_tab_names"""
    notepad = Notepad(mock_window)
    items = {}
    item = NotepadItem()
    item.id = 1
    item.idx = 1
    item.title = 'test'
    item.initialized = True
    items[1] = item
    mock_window.core.notepad.get_all = MagicMock(return_value=items)
    notepad.update_name = MagicMock()

    notepad.reload_tab_names()
    notepad.update_name.assert_called_once_with(1, 'test', False)


def test_update_name(mock_window):
    """Test update_name"""
    notepad = Notepad(mock_window)
    mock_window.ui.tabs = {'output': MagicMock()}
    mock_window.core.notepad.get_by_id = MagicMock(return_value=None)
    mock_window.core.notepad.update = MagicMock()
    notepad.update_name(1, 'test')
    mock_window.ui.tabs['output'].setTabText.assert_called_once_with(4, 'test')
    mock_window.core.notepad.update.assert_called_once()


def test_save(mock_window):
    """Test save"""
    notepad = Notepad(mock_window)
    mock_window.ui.notepad = {1: MagicMock()}
    mock_window.core.notepad.get_by_id = MagicMock(return_value=None)
    mock_window.core.notepad.update = MagicMock()
    notepad.save(1)
    mock_window.core.notepad.update.assert_called_once()


def test_save_all(mock_window):
    """Test save_all"""
    notepad = Notepad(mock_window)
    mock_window.ui.notepad = {1: MagicMock()}
    mock_window.core.notepad.get_all = MagicMock(return_value={1: MagicMock()})
    mock_window.core.notepad.update = MagicMock()
    notepad.save_all()
    mock_window.core.notepad.update.assert_called_once()


def test_setup(mock_window):
    """Test setup"""
    notepad = Notepad(mock_window)
    notepad.load = MagicMock()
    notepad.setup_tabs = MagicMock()
    notepad.setup()
    notepad.load.assert_called_once()


def test_get_num_notepads(mock_window):
    """Test get_num_notepads"""
    notepad = Notepad(mock_window)
    mock_window.core.config.data['notepad.num'] = 1
    assert notepad.get_num_notepads() == 1


def test_rename_upd(mock_window):
    """Test rename_upd"""
    notepad = Notepad(mock_window)
    mock_window.core.notepad.get_by_id = MagicMock(return_value=None)
    mock_window.core.notepad.update = MagicMock()
    notepad.update = MagicMock()
    notepad.rename_upd(1, 'test')
    notepad.update.assert_called_once()
    mock_window.core.notepad.update.assert_called_once()
