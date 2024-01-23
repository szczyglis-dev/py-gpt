#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.05 03:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch, mock_open, Mock

from pygpt_net.item.notepad import NotepadItem
from tests.mocks import mock_window
from pygpt_net.provider.core.notepad.db_sqlite.storage import Storage


def test_unpack(mock_window):
    """Test unpack"""
    storage = Storage(mock_window)
    notepad = NotepadItem()
    row = {
        'id': 1,
        'idx': 2,
        'uuid': 'test',
        'created_ts': 1234567890,
        'updated_ts': 1234567890,
        'title': 'test',
        'content': 'test content',
        'is_deleted': 0,
        'is_initialized': 0,
    }
    storage.unpack(notepad, row)

    assert notepad.id == 1
    assert notepad.idx == 2
    assert notepad.uuid == 'test'
    assert notepad.created == 1234567890
    assert notepad.updated == 1234567890
    assert notepad.title == 'test'
    assert notepad.content == 'test content'
    assert notepad.deleted is False
    assert notepad.initialized is False


def test_get_all(mock_window):
    """Test get all"""
    storage = Storage(mock_window)
    fake_row = Mock()
    fake_row._asdict.return_value = {
        'id': 1,
        'idx': 1,
        'uuid': 'test',
        'created_ts': 1234567890,
        'updated_ts': 1234567890,
        'title': 'Title 1',
        'content': 'Content 1',
        'is_deleted': 0,
        'is_initialized': 0,
    }
    conn = Mock()
    conn.execute.return_value = [fake_row]
    with patch('pygpt_net.core.db.Database.get_db') as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        mock_get_db.return_value.connect.return_value.__enter__.return_value = conn
        result = storage.get_all()

    assert type(result) == dict
    assert len(result) == 1
    assert type(result[1]) == NotepadItem
    assert result[1].id == 1
    assert result[1].title == 'Title 1'
    assert result[1].content == 'Content 1'


def test_get_by_idx(mock_window):
    """Test get by idx"""
    storage = Storage(mock_window)
    fake_row = Mock()
    fake_row._asdict.return_value = {
        'id': 1,
        'idx': 1,
        'uuid': 'test',
        'created_ts': 1234567890,
        'updated_ts': 1234567890,
        'title': 'Title 1',
        'content': 'Content 1',
        'is_deleted': 0,
        'is_initialized': 0,
    }
    conn = Mock()
    conn.execute.return_value = [fake_row]
    with patch('pygpt_net.core.db.Database.get_db') as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        mock_get_db.return_value.connect.return_value.__enter__.return_value = conn
        result = storage.get_by_idx(1)

    assert type(result) == NotepadItem
    assert result.id == 1
    assert result.title == 'Title 1'
    assert result.content == 'Content 1'


def test_truncate_all(mock_window):
    """Test truncate all"""
    storage = Storage(mock_window)
    conn = Mock()
    with patch('pygpt_net.core.db.Database.get_db') as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        mock_get_db.return_value.begin.return_value.__enter__.return_value = conn
        result = storage.truncate_all()

    assert result is True


def test_delete_by_idx(mock_window):
    """Test delete by idx"""
    storage = Storage(mock_window)
    conn = Mock()
    with patch('pygpt_net.core.db.Database.get_db') as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        mock_get_db.return_value.begin.return_value.__enter__.return_value = conn
        result = storage.delete_by_idx(1)

    assert result is True


def test_save(mock_window):
    """Test save"""
    storage = Storage(mock_window)
    conn = Mock()
    item = NotepadItem()
    with patch('pygpt_net.core.db.Database.get_db') as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        mock_get_db.return_value.begin.return_value.__enter__.return_value = conn
        storage.save(item)

    assert conn.execute.called_once()


def test_insert(mock_window):
    """Test insert"""
    storage = Storage(mock_window)
    db_result = MagicMock()
    db_result.lastrowid = 1
    item = NotepadItem()
    conn = MagicMock()
    conn.execute.return_value = db_result
    mock_db = MagicMock()
    mock_db.begin.return_value.__enter__.return_value = conn
    with patch('pygpt_net.core.db.Database.get_db', return_value=mock_db) as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        result = storage.insert(item)

    assert result == 1
