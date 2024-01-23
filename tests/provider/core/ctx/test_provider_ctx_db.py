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

from pygpt_net.item.ctx import CtxItem, CtxMeta
from tests.mocks import mock_window
from pygpt_net.provider.core.ctx.db_sqlite import DbSqliteProvider


def test_create(mock_window):
    """Test create"""
    provider = DbSqliteProvider(mock_window)
    provider.storage = MagicMock()
    provider.storage.insert_meta = MagicMock(return_value=2)
    ctx = CtxMeta()
    ctx.id = None
    assert provider.create(ctx) == 2


def test_get_meta(mock_window):
    """Test get_meta"""
    provider = DbSqliteProvider(mock_window)
    provider.storage = MagicMock()
    provider.storage.get_meta = MagicMock(return_value={})
    assert provider.get_meta() == {}


def test_load(mock_window):
    """Test load"""
    provider = DbSqliteProvider(mock_window)
    provider.storage = MagicMock()
    provider.storage.get_items = MagicMock(return_value={})
    assert provider.load(1) == {}


def test_append_item(mock_window):
    """Test append_item"""
    provider = DbSqliteProvider(mock_window)
    provider.storage = MagicMock()
    provider.storage.insert_item = MagicMock(return_value=2)
    ctx = CtxItem()
    ctx.id = None
    meta = CtxMeta()
    meta.id = 2
    assert provider.append_item(meta, ctx) is True


def test_update_item(mock_window):
    """Test update_item"""
    provider = DbSqliteProvider(mock_window)
    provider.storage = MagicMock()
    provider.storage.update_item = MagicMock(return_value=2)
    ctx = CtxItem()
    ctx.id = 2
    meta = CtxMeta()
    meta.id = 2
    assert provider.update_item(ctx) is True


def test_save(mock_window):
    """Test save"""
    provider = DbSqliteProvider(mock_window)
    provider.storage = MagicMock()
    provider.storage.update_meta = MagicMock(return_value=2)
    meta = CtxMeta()
    meta.id = 2
    items = [CtxItem()]
    assert provider.save(2, meta, items) is True


def test_remove(mock_window):
    """Test remove"""
    provider = DbSqliteProvider(mock_window)
    provider.storage = MagicMock()
    provider.storage.delete_meta_by_id = MagicMock(return_value=True)
    assert provider.remove(2) is True


def test_truncate(mock_window):
    """Test truncate"""
    provider = DbSqliteProvider(mock_window)
    provider.storage = MagicMock()
    provider.storage.truncate_all = MagicMock(return_value=True)
    assert provider.truncate() is True
