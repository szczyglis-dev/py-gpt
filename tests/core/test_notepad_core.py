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

from unittest.mock import MagicMock, patch

from packaging.version import parse as parse_version, Version
from pygpt_net.item.notepad import NotepadItem
from tests.mocks import mock_window
from pygpt_net.core.notepad import Notepad


def test_install(mock_window):
    """Test install"""
    models = Notepad(mock_window)
    models.provider = MagicMock()
    models.install()
    models.provider.install.assert_called_once()


def test_patch(mock_window):
    """Test patch"""
    models = Notepad(mock_window)
    models.provider = MagicMock()
    models.patch(parse_version("1.0.0"))
    models.provider.patch.assert_called_once()


def test_get_by_id(mock_window):
    """Test get by id"""
    notepad = Notepad(mock_window)
    item = NotepadItem()
    notepad.items = {1: item}
    assert notepad.get_by_id(1) == item


def test_get_all(mock_window):
    """Test get all"""
    notepad = Notepad(mock_window)
    item = NotepadItem()
    notepad.items = {1: item}
    assert notepad.get_all() == {1: item}


def test_build(mock_window):
    """Test build"""
    notepad = Notepad(mock_window)
    item = notepad.build()
    assert isinstance(item, NotepadItem)


def test_add(mock_window):
    """Test add"""
    notepad = Notepad(mock_window)
    item = NotepadItem()
    notepad.provider.create = MagicMock(return_value=1)
    notepad.save = MagicMock()
    assert notepad.add(item)
    assert item.id == 1
    assert item.idx == 0
    assert notepad.items == {1: item}
    notepad.save.assert_called_once_with(1)


def test_update(mock_window):
    """Test update"""
    notepad = Notepad(mock_window)
    item = NotepadItem()
    item.idx = 1
    notepad.items = {1: item}
    notepad.provider.update = MagicMock(return_value=True)
    notepad.save = MagicMock()
    assert notepad.update(item)
    assert notepad.items == {1: item}
    notepad.save.assert_called_once_with(1)


def test_load(mock_window):
    """Test load"""
    notepad = Notepad(mock_window)
    item = NotepadItem()
    item.idx = 1
    notepad.items = {1: item}
    notepad.provider.load = MagicMock(return_value=item)
    notepad.load(1)
    assert notepad.items == {1: item}
    notepad.provider.load.assert_called_once_with(1)


def test_load_all(mock_window):
    """Test load all"""
    notepad = Notepad(mock_window)
    item = NotepadItem()
    item.idx = 1
    notepad.items = {1: item}
    notepad.provider.load_all = MagicMock(return_value={1: item})
    notepad.load_all()
    assert notepad.items == {1: item}
    notepad.provider.load_all.assert_called_once_with()


def test_save(mock_window):
    """Test save"""
    notepad = Notepad(mock_window)
    item = NotepadItem()
    item.idx = 1
    notepad.items = {1: item}
    notepad.provider.save = MagicMock()
    notepad.save(1)
    notepad.provider.save.assert_called_once_with(item)


def test_save_all(mock_window):
    """Test save all"""
    notepad = Notepad(mock_window)
    item = NotepadItem()
    item.idx = 1
    notepad.items = {1: item}
    notepad.provider.save_all = MagicMock()
    notepad.save_all()
    notepad.provider.save_all.assert_called_once_with({1: item})
