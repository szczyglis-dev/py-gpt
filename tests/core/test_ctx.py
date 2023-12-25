#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

import pytest
from unittest.mock import MagicMock, mock_open, patch
from PySide6.QtWidgets import QMainWindow

from pygpt_net.config import Config
from pygpt_net.core.ctx import Ctx
from pygpt_net.item.ctx import CtxItem, CtxMeta


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.app = MagicMock()
    window.app.config = MagicMock(spec=Config)
    window.app.config.path = 'test_path'
    return window


def mock_get(key):
    if key == "mode":
        return "test_mode"
    elif key == "context_threshold":
        return 200

def test_update(mock_window):
    """
    Test update context data
    """
    ctx = Ctx(mock_window)
    ctx.window.app.config.get.side_effect = mock_get
    ctx.current = 'test_ctx'
    ctx.mode = 'test_mode'

    item = CtxMeta()
    item.mode = 'test_mode'
    ctx.meta = {
        'test_ctx': item,
    }
    ctx.save = MagicMock()  # prevent dump context
    ctx.update()
    assert ctx.current == 'test_ctx'
    assert ctx.mode == 'test_mode'
    assert ctx.meta['test_ctx'].mode == 'test_mode'
    ctx.save.assert_called_once_with('test_ctx')


def test_post_update(mock_window):
    """
    Test post update context data
    """
    ctx = Ctx(mock_window)
    ctx.window.app.config.get.side_effect = mock_get
    ctx.current = 'test_ctx'
    ctx.mode = 'test_mode'

    item = CtxMeta()
    item.mode = 'test_mode'
    ctx.meta = {
        'test_ctx': item,
    }
    ctx.save = MagicMock()  # prevent dump context
    ctx.post_update('test_mode')
    assert ctx.current == 'test_ctx'
    assert ctx.mode == 'test_mode'
    assert ctx.meta['test_ctx'].mode == 'test_mode'
    ctx.save.assert_called_once_with('test_ctx')


def test_create_id(mock_window):
    """
    Test create context ID
    """
    ctx = Ctx(mock_window)
    ctx.create_id = MagicMock(return_value='test_id')
    assert ctx.create_id() == 'test_id'


def test_is_empty(mock_window):
    """
    Test is_empty
    """
    ctx = Ctx(mock_window)
    assert ctx.is_empty() is True
    ctx.current = 'test_ctx'
    assert ctx.is_empty() is True
    ctx.items = [1]
    assert ctx.is_empty() is False


def test_new(mock_window):
    """
    Test new context
    """
    ctx = Ctx(mock_window)
    ctx.create_id = MagicMock(return_value='test_id')
    ctx.window.app.config.get.side_effect = mock_get
    ctx.current = 'test_ctx'
    ctx.mode = 'test_mode'

    item = CtxMeta()
    item.id = 'test_ctx'
    item.mode = 'test_mode'
    ctx.save = MagicMock()  # prevent dump context
    ctx.create = MagicMock(return_value=item)
    assert ctx.new() == item
    assert ctx.current == 'test_ctx'
    assert ctx.mode == 'test_mode'
    assert ctx.meta['test_ctx'].mode == 'test_mode'
    ctx.save.assert_called_once_with('test_ctx')


def test_is_initialized(mock_window):
    """
    Test is_initialized
    """
    ctx = Ctx(mock_window)
    ctx.current = 'test_ctx'

    item = CtxMeta()
    item.initialized = True

    ctx.meta = {
        'test_ctx': item,
    }
    assert ctx.is_initialized() is True

    item = CtxMeta()
    item.initialized = False
    ctx.meta = {
        'test_ctx': item,
    }
    assert ctx.is_initialized() is False
    ctx.meta = {
        'test_ctx': CtxMeta()
    }
    assert ctx.is_initialized() is False
    ctx.current = None
    assert ctx.is_initialized() is None

def test_set_initialized(mock_window):
    """
    Test set_initialized
    """
    ctx = Ctx(mock_window)
    ctx.current = 'test_ctx'

    item = CtxMeta()
    item.initialized = False
    ctx.meta = {
        'test_ctx': item,
    }
    ctx.save = MagicMock()  # prevent dump context
    ctx.set_initialized()
    assert ctx.meta['test_ctx'].initialized is True
    ctx.save.assert_called_once_with('test_ctx')
    ctx.current = None
    ctx.set_initialized()
    ctx.save.assert_called_once_with('test_ctx')


def test_append_thread(mock_window):
    """
    Test append_thread
    """
    ctx = Ctx(mock_window)
    ctx.current = 'test_ctx'
    ctx.thread = 'test_thread'

    item = CtxMeta()
    item.thread = 'test_thread'
    ctx.meta = {
        'test_ctx': item
    }

    ctx.save = MagicMock()  # prevent dump context
    ctx.append_thread('test_thread')
    assert ctx.meta['test_ctx'].thread == 'test_thread'
    ctx.save.assert_called_once_with('test_ctx')
    ctx.current = None
    ctx.append_thread('test_thread')
    ctx.save.assert_called_once_with('test_ctx')


def test_append_run(mock_window):
    """
    Test append_run
    """
    ctx = Ctx(mock_window)
    ctx.current = 'test_ctx'
    ctx.run = 'test_run'

    item = CtxMeta()
    item.run = 'test_run'
    ctx.meta = {
        'test_ctx': item
    }
    ctx.save = MagicMock()  # prevent dump context
    ctx.append_run('test_run')
    assert ctx.meta['test_ctx'].run == 'test_run'
    ctx.save.assert_called_once_with('test_ctx')
    ctx.current = None
    ctx.append_run('test_run')
    ctx.save.assert_called_once_with('test_ctx')


def test_append_status(mock_window):
    """
    Test append_status
    """
    ctx = Ctx(mock_window)
    ctx.current = 'test_ctx'
    ctx.status = 'test_status'

    item = CtxMeta()
    item.status = 'test_status'
    ctx.meta = {
        'test_ctx': item
    }
    ctx.save = MagicMock()  # prevent dump context
    ctx.append_status('test_status')
    assert ctx.meta['test_ctx'].status == 'test_status'
    ctx.save.assert_called_once_with('test_ctx')
    ctx.current = None
    ctx.append_status('test_status')
    ctx.save.assert_called_once_with('test_ctx')


def test_get_meta(mock_window):
    """
    Test list
    """
    ctx = Ctx(mock_window)
    ctx.current = 'test_ctx'

    item1 = CtxMeta()
    item1.mode = 'test_mode'
    item2 = CtxMeta()
    item2.mode = 'test_mode2'

    ctx.meta = {
        'test_ctx20221204': item1,
        'test_ctx20221207': item2,
    }
    assert ctx.get_meta() == {
        'test_ctx20221204': item1,
        'test_ctx20221207': item2,
    }


def test_get_id_by_idx(mock_window):
    """
    Test get_id_by_idx
    """
    ctx = Ctx(mock_window)
    ctx.current = 'test_ctx'
    item1 = CtxMeta()
    item1.mode = 'test_mode'
    item2 = CtxMeta()
    item2.mode = 'test_mode2'
    ctx.meta = {
        'test_ctx20221204': item1,
        'test_ctx20221207': item2,
    }

    # WARNING: list is sorted: get_meta() sorts items before returning!
    assert ctx.get_id_by_idx(0) == 'test_ctx20221207'
    assert ctx.get_id_by_idx(1) == 'test_ctx20221204'
    assert ctx.get_id_by_idx(2) is None


def test_get_idx_by_id(mock_window):
    """
    Test get_idx_by_id
    """
    ctx = Ctx(mock_window)
    ctx.current = 'test_ctx'

    item1 = CtxMeta()
    item1.mode = 'test_mode'
    item2 = CtxMeta()
    item2.mode = 'test_mode2'
    ctx.meta = {
        'test_ctx20221204': item1,
        'test_ctx20221207': item2,
    }

    # WARNING: list is sorted: get_meta() sorts items before returning!
    assert ctx.get_idx_by_id('test_ctx20221207') == 0
    assert ctx.get_idx_by_id('test_ctx20221204') == 1
    assert ctx.get_idx_by_id('test_ctx20221205') is None


def test_get_first(mock_window):
    """
    Test get_first_ctx
    """
    ctx = Ctx(mock_window)
    ctx.current = 'test_ctx'

    item1 = CtxMeta()
    item1.mode = 'test_mode'
    item2 = CtxMeta()
    item2.mode = 'test_mode2'
    ctx.meta = {
        'test_ctx20221204': item1,
        'test_ctx20221207': item2,
    }

    # WARNING: list is sorted: get_meta() sorts items before returning!
    assert ctx.get_first() == 'test_ctx20221207'
    ctx.meta = {}
    assert ctx.get_first() is None


def test_get_meta_by_id(mock_window):
    """
    Test get_meta_by_id
    """
    ctx = Ctx(mock_window)
    ctx.current = 'test_ctx'

    item1 = CtxMeta()
    item1.mode = 'test_mode'
    item2 = CtxMeta()
    item2.mode = 'test_mode2'
    ctx.meta = {
        'test_ctx20221204': item1,
        'test_ctx20221207': item2,
    }

    # WARNING: list is sorted: get_meta() sorts items before returning!
    assert ctx.get_meta_by_id('test_ctx20221207') == item2
    assert ctx.get_meta_by_id('test_ctx20221204') == item1
    assert ctx.get_meta_by_id('test_ctx20221205') is None


def test_remove_ctx(mock_window):
    """
    Test remove_ctx
    """
    ctx = Ctx(mock_window)
    ctx.current = 'test_ctx'
    ctx.meta = {
        'test_ctx20221204': {
            'mode': 'test_mode'
        },
        'test_ctx20221207': {
            'mode': 'test_mode2'
        }
    }
    ctx.save = MagicMock()  # prevent dump context
    ctx.remove('test_ctx20221207')
    assert ctx.meta == {
        'test_ctx20221204': {
            'mode': 'test_mode'
        }
    }
    ctx.current = None
    ctx.remove('test_ctx20221204')


def test_prepare(mock_window):
    """
    Test prepare
    """
    ctx = Ctx(mock_window)
    ctx.current = 'test_ctx'
    ctx.meta = {}
    ctx.new = MagicMock()  # prevent dump context
    ctx.prepare()
    ctx.new.assert_called_once_with()


def test_get_all_items(mock_window):
    """
    Test get_all_items
    """
    ctx = Ctx(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    assert ctx.get_all_items() == [
        'item1',
        'item2'
    ]


def test_clear(mock_window):
    """
    Test clear
    """
    ctx = Ctx(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    ctx.clear()
    assert ctx.items == []


def test_select(mock_window):
    """
    Test select
    """
    ctx = Ctx(mock_window)
    ctx.current = 'test_ctx'

    item1 = CtxMeta()
    item1.mode = 'test_mode'

    item2 = CtxMeta()
    item2.mode = 'test_mode2'

    ctx.meta = {
        'test_ctx20221204': item1,
        'test_ctx20221207': item2,
    }
    ctx.load = MagicMock()  # prevent load
    ctx.select('test_ctx20221207')
    assert ctx.current == 'test_ctx20221207'
    ctx.load.assert_called_once_with('test_ctx20221207')


def test_add(mock_window):
    """
    Test add
    """
    item = CtxItem()

    ctx = Ctx(mock_window)
    ctx.meta = []
    ctx.store = MagicMock()  # prevent store
    ctx.add(item)
    assert ctx.items == [item]
    ctx.store.assert_called_once_with()


def test_store(mock_window):
    """
    Test store
    """
    ctx = Ctx(mock_window)
    ctx.current = 'test_ctx20221204'
    ctx.meta = {
        'test_ctx20221204': {
            'mode': 'test_mode'
        },
        'test_ctx20221207': {
            'mode': 'test_mode2'
        }
    }
    ctx.save = MagicMock()  # prevent dump context
    ctx.store()
    ctx.save.assert_called_once_with('test_ctx20221204')


def test_get_total_tokens(mock_window):
    """
    Test get_total_tokens
    """
    last_item = CtxItem()
    last_item.total_tokens = 66
    ctx = Ctx(mock_window)
    ctx.get_last = MagicMock()
    ctx.get_last.return_value = last_item

    assert ctx.get_total_tokens() == 66


def test_count(mock_window):
    """
    Test count
    """
    ctx = Ctx(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    assert ctx.count() == 2


def test_all(mock_window):
    """
    Test all
    """
    ctx = Ctx(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    assert ctx.all() == [
        'item1',
        'item2'
    ]


def test_get(mock_window):
    """
    Test get
    """
    ctx = Ctx(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    assert ctx.get(0) == 'item1'
    assert ctx.get(1) == 'item2'
    assert ctx.get(2) is None


def test_get_last(mock_window):
    """
    Test get_last
    """
    ctx = Ctx(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    assert ctx.get_last() == 'item2'
    ctx.items = []
    assert ctx.get_last() is None


def test_get_tokens_left(mock_window):
    """
    Test get_tokens_left
    """
    ctx = Ctx(mock_window)
    ctx.get_total_tokens = MagicMock()
    ctx.get_total_tokens.return_value = 10
    assert ctx.get_tokens_left(20) == 10
    ctx.get_total_tokens.return_value = 20
    assert ctx.get_tokens_left(20) == 0


def test_check(mock_window):
    """
    Test check
    """
    ctx = Ctx(mock_window)
    ctx.get_tokens_left = MagicMock()
    ctx.get_tokens_left.return_value = 10
    ctx.remove_first = MagicMock()
    ctx.check(5, 20)
    ctx.remove_first.assert_not_called()
    ctx.check(10, 20)
    ctx.remove_first.assert_called_once_with()


def test_remove_last(mock_window):
    """
    Test remove_last
    """
    ctx = Ctx(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    ctx.remove_last()
    assert ctx.items == [
        'item1'
    ]
    ctx.items = []
    ctx.remove_last()
    assert ctx.items == []


def test_remove_first(mock_window):
    """
    Test remove_first
    """
    ctx = Ctx(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    ctx.remove_first()
    assert ctx.items == [
        'item2'
    ]
    ctx.items = []
    ctx.remove_first()
    assert ctx.items == []


def test_get_last_tokens(mock_window):
    """
    Test get_last_tokens
    """
    ctx = Ctx(mock_window)
    ctx.get_last = MagicMock()
    ctx.get_last.return_value = CtxItem()
    ctx.get_last().total_tokens = 10
    assert ctx.get_last_tokens() == 10
    ctx.get_last.return_value = None
    assert ctx.get_last_tokens() == 0