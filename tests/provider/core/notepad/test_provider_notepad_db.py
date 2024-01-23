#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.04 13:00:00                  #
# ================================================== #

import json
import os
from unittest.mock import MagicMock, patch, mock_open

from pygpt_net.item.notepad import NotepadItem
from tests.mocks import mock_window
from pygpt_net.provider.core.notepad.db_sqlite import DbSqliteProvider


def test_create(mock_window):
    """Test create"""
    provider = DbSqliteProvider(mock_window)
    provider.storage = MagicMock()
    provider.storage.insert = MagicMock(return_value=2)
    notepad = NotepadItem()
    notepad.id = None
    assert provider.create(notepad) == 2


def test_load_all(mock_window):
    """Test load_all"""
    provider = DbSqliteProvider(mock_window)
    provider.storage = MagicMock()
    provider.storage.get_all = MagicMock(return_value={})
    assert provider.load_all() == {}


def test_load(mock_window):
    """Test load"""
    provider = DbSqliteProvider(mock_window)
    provider.storage = MagicMock()
    provider.storage.get_by_idx = MagicMock(return_value={})
    assert provider.load(1) == {}


def test_save(mock_window):
    """Test save"""
    provider = DbSqliteProvider(mock_window)
    item = NotepadItem()
    item.id = 1
    provider.storage = MagicMock()
    provider.storage.save = MagicMock()
    provider.save(item)
    provider.storage.save.called_once()


def test_save_all(mock_window):
    """Test save_all"""
    provider = DbSqliteProvider(mock_window)
    item = NotepadItem()
    item.id = 1
    items = {
        1: item
    }
    provider.storage = MagicMock()
    provider.storage.save_all = MagicMock()
    provider.save_all(items)
    provider.storage.save_all.called_once()


def test_truncate(mock_window):
    """Test truncate"""
    provider = DbSqliteProvider(mock_window)
    provider.storage = MagicMock()
    provider.storage.truncate = MagicMock()
    provider.truncate()
    provider.storage.truncate.called_once()
