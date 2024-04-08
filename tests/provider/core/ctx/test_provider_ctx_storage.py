#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.08 21:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch, mock_open, Mock

from pygpt_net.item.ctx import CtxItem, CtxMeta
from tests.mocks import mock_window
from pygpt_net.provider.core.ctx.db_sqlite.storage import Storage
from pygpt_net.provider.core.ctx.db_sqlite.utils import *

def test_get_meta(mock_window):
    """Test get meta"""
    storage = Storage(mock_window)
    fake_row = Mock()
    fake_row._asdict.return_value = {
        'id': 1,
        'external_id': 1,
        'uuid': 'test',
        'created_ts': 1483228800,
        'updated_ts': 1483228800,
        'name': 'test',
        'mode': 'test',
        'model': 'test',
        'last_mode': 'test',
        'last_model': 'test',
        'thread_id': 1,
        'assistant_id': 1,
        'preset_id': 1,
        'run_id': 1,
        'status': 'test',
        'extra': 'test',
        'is_initialized': 1,
        'is_deleted': 0,
        'is_important': 0,
        'is_archived': 0,
        'label': 0,
        'indexed_ts': 0,
        'indexes_json': {},
        'group_id': 1,
    }
    conn = Mock()
    conn.execute.return_value = [fake_row]
    with patch('pygpt_net.core.db.Database.get_db') as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        mock_get_db.return_value.connect.return_value.__enter__.return_value = conn
        result = storage.get_meta()

    assert type(result) == dict
    assert len(result) == 1
    assert type(result[1]) == CtxMeta
    assert result[1].id == 1
    assert result[1].external_id == 1
    assert result[1].uuid == 'test'
    assert result[1].created == 1483228800
    assert result[1].updated == 1483228800
    assert result[1].name == 'test'
    assert result[1].mode == 'test'
    assert result[1].model == 'test'
    assert result[1].last_mode == 'test'
    assert result[1].last_model == 'test'
    assert result[1].thread == 1
    assert result[1].assistant == 1
    assert result[1].preset == 1
    assert result[1].run == 1
    assert result[1].status == 'test'
    assert result[1].extra == 'test'
    assert result[1].initialized is True
    assert result[1].deleted is False
    assert result[1].important is False
    assert result[1].archived is False
    assert result[1].label == 0
    assert result[1].group_id == 1


def test_get_items(mock_window):
    """Test get items"""
    storage = Storage(mock_window)
    fake_row = Mock()
    fake_row._asdict.return_value = {
        'id': 1,
        'meta_id': 1,
        'external_id': 1,
        'input': 'test',
        'output': 'test',
        'input_name': 'test',
        'output_name': 'test',
        'input_ts': 1483228800,
        'output_ts': 1483228800,
        'mode': 'test',
        'model': 'test',
        'thread_id': 1,
        'msg_id': 1,
        'run_id': 1,
        'cmds_json': None,
        'results_json': None,
        'urls_json': None,
        'images_json': None,
        'files_json': None,
        'attachments_json': None,
        'extra': 'test',
        'input_tokens': 1,
        'output_tokens': 1,
        'total_tokens': 1,
        'is_internal': 0,
        'is_vision': 0,
        'docs_json': None,
    }
    conn = Mock()
    conn.execute.return_value = [fake_row]
    with patch('pygpt_net.core.db.Database.get_db') as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        mock_get_db.return_value.connect.return_value.__enter__.return_value = conn
        result = storage.get_items(1)

    assert type(result) == list
    assert len(result) == 1
    assert type(result[0]) == CtxItem
    assert result[0].id == 1
    assert result[0].meta_id == 1
    assert result[0].external_id == 1
    assert result[0].input == 'test'
    assert result[0].output == 'test'
    assert result[0].input_name == 'test'
    assert result[0].output_name == 'test'
    assert result[0].input_timestamp == 1483228800
    assert result[0].output_timestamp == 1483228800
    assert result[0].mode == 'test'
    assert result[0].model == 'test'
    assert result[0].thread == 1
    assert result[0].msg_id == 1
    assert result[0].run_id == 1
    assert result[0].cmds is None
    assert result[0].results is None
    assert result[0].urls is None
    assert result[0].images is None
    assert result[0].files is None
    assert result[0].attachments is None
    assert result[0].extra == 'test'
    assert result[0].input_tokens == 1
    assert result[0].output_tokens == 1
    assert result[0].total_tokens == 1
    assert result[0].internal is False


def test_truncate_all(mock_window):
    """Test truncate all"""
    storage = Storage(mock_window)
    conn = Mock()
    with patch('pygpt_net.core.db.Database.get_db') as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        mock_get_db.return_value.begin.return_value.__enter__.return_value = conn
        result = storage.truncate_all()

    assert result is True


def test_delete_items_by_meta_id(mock_window):
    """Test delete items by meta id"""
    storage = Storage(mock_window)
    conn = Mock()
    with patch('pygpt_net.core.db.Database.get_db') as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        mock_get_db.return_value.begin.return_value.__enter__.return_value = conn
        result = storage.delete_items_by_meta_id(1)

    assert result is True


def test_delete_meta_by_id(mock_window):
    """Test delete meta by idx"""
    storage = Storage(mock_window)
    conn = Mock()
    with patch('pygpt_net.core.db.Database.get_db') as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        mock_get_db.return_value.begin.return_value.__enter__.return_value = conn
        result = storage.delete_meta_by_id(1)

    assert result is True


def test_update_meta(mock_window):
    """Test update meta"""
    storage = Storage(mock_window)
    conn = Mock()
    item = CtxMeta()
    with patch('pygpt_net.core.db.Database.get_db') as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        mock_get_db.return_value.begin.return_value.__enter__.return_value = conn
        storage.update_meta(item)

    assert conn.execute.called_once()


def test_update_meta_ts(mock_window):
    """Test update meta ts"""
    storage = Storage(mock_window)
    conn = Mock()
    with patch('pygpt_net.core.db.Database.get_db') as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        mock_get_db.return_value.begin.return_value.__enter__.return_value = conn
        storage.update_meta_ts(1)

    assert conn.execute.called_once()


def test_update_item(mock_window):
    """Test update item"""
    storage = Storage(mock_window)
    conn = Mock()
    item = CtxItem()
    with patch('pygpt_net.core.db.Database.get_db') as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        mock_get_db.return_value.begin.return_value.__enter__.return_value = conn
        storage.update_item(item)

    assert conn.execute.called_once()


def test_insert_meta(mock_window):
    """Test insert meta"""
    storage = Storage(mock_window)
    db_result = MagicMock()
    db_result.lastrowid = 1
    item = CtxMeta()
    conn = MagicMock()
    conn.execute.return_value = db_result
    mock_db = MagicMock()
    mock_db.begin.return_value.__enter__.return_value = conn
    with patch('pygpt_net.core.db.Database.get_db', return_value=mock_db) as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        result = storage.insert_meta(item)

    assert result == 1


def test_insert_item(mock_window):
    """Test insert item"""
    storage = Storage(mock_window)
    db_result = MagicMock()
    db_result.lastrowid = 1
    meta = CtxMeta()
    item = CtxItem()
    meta.id = 1
    conn = MagicMock()
    conn.execute.return_value = db_result
    mock_db = MagicMock()
    mock_db.begin.return_value.__enter__.return_value = conn
    with patch('pygpt_net.core.db.Database.get_db', return_value=mock_db) as mock_get_db:
        mock_window.core.db.get_db = mock_get_db
        result = storage.insert_item(meta, item)

    assert result == 1


def test_unpack_meta(mock_window):
    """Test unpack meta"""
    storage = Storage(mock_window)
    row = {
        'id': 1,
        'external_id': 'external_id',
        'uuid': 'uuid',
        'created_ts': 1,
        'updated_ts': 1,
        'name': 'name',
        'mode': 'mode',
        'model': 'model',
        'last_mode': 'last_mode',
        'last_model': 'last_model',
        'thread_id': 'thread_id',
        'assistant_id': 'assistant_id',
        'preset_id': 'preset_id',
        'run_id': 'run_id',
        'status': 'status',
        'extra': 'extra',
        'is_initialized': 1,
        'is_deleted': 1,
        'is_important': 1,
        'is_archived': 1,
        'label': 0,
        'indexed_ts': 0,
        'indexes_json': {},
        'group_id': 1,
    }
    meta = CtxMeta()
    unpack_meta(meta, row)
    assert meta.id == 1
    assert meta.external_id == 'external_id'
    assert meta.uuid == 'uuid'
    assert meta.created == 1
    assert meta.updated == 1
    assert meta.name == 'name'
    assert meta.mode == 'mode'
    assert meta.model == 'model'
    assert meta.last_mode == 'last_mode'
    assert meta.last_model == 'last_model'
    assert meta.thread == 'thread_id'
    assert meta.assistant == 'assistant_id'
    assert meta.preset == 'preset_id'
    assert meta.run == 'run_id'
    assert meta.status == 'status'
    assert meta.extra == 'extra'
    assert meta.initialized is True
    assert meta.deleted is True
    assert meta.important is True
    assert meta.archived is True
    assert meta.label == 0
    assert meta.group_id == 1


def test_unpack_item(mock_window):
    """Test unpack item"""
    storage = Storage(mock_window)
    row = {
        'id': 1,
        'meta_id': 1,
        'external_id': 'external_id',
        'input': 'input',
        'output': 'output',
        'input_name': 'input_name',
        'output_name': 'output_name',
        'input_ts': 1,
        'output_ts': 1,
        'mode': 'mode',
        'model': 'model',
        'thread_id': 'thread_id',
        'msg_id': 'msg_id',
        'run_id': 'run_id',
        'cmds_json': None,
        'results_json': None,
        'urls_json': None,
        'images_json': None,
        'files_json': None,
        'attachments_json': None,
        'extra': None,
        'input_tokens': 1,
        'output_tokens': 1,
        'total_tokens': 1,
        'is_internal': 1,
        'is_vision': 1,
        'docs_json': None,
    }
    item = CtxItem()
    unpack_item(item, row)
    assert item.id == 1
    assert item.meta_id == 1
    assert item.external_id == 'external_id'
    assert item.input == 'input'
    assert item.output == 'output'
    assert item.input_name == 'input_name'
    assert item.output_name == 'output_name'
    assert item.input_timestamp == 1
    assert item.output_timestamp == 1
    assert item.mode == 'mode'
    assert item.model == 'model'
    assert item.thread == 'thread_id'
    assert item.msg_id == 'msg_id'
    assert item.run_id == 'run_id'
    assert item.cmds is None
    assert item.results is None
    assert item.urls is None
    assert item.images is None
    assert item.files is None
    assert item.attachments is None
    assert item.extra is None
    assert item.input_tokens == 1
    assert item.output_tokens == 1
    assert item.total_tokens == 1
    assert item.internal is True


def test_pack_item_value():
    """Test pack item value"""
    storage = Storage()
    assert pack_item_value(None) is None
    assert pack_item_value(1) == 1
    assert pack_item_value('1') == '1'
    assert pack_item_value([1, 2, 3]) == '[1, 2, 3]'
    assert pack_item_value({'a': 1, 'b': 2}) == '{"a": 1, "b": 2}'


def test_unpack_item_value():
    """Test unpack item value"""
    storage = Storage()
    assert unpack_item_value(None) is None
    assert unpack_item_value(1) == 1
    assert unpack_item_value('1') == 1
    assert unpack_item_value('[1, 2, 3]') == [1, 2, 3]
    assert unpack_item_value('{"a": 1, "b": 2}') == {'a': 1, 'b': 2}
