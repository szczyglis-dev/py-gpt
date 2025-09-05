#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 18:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch

from tests.mocks import mock_window_conf
from pygpt_net.core.ctx import Ctx
from pygpt_net.item.ctx import CtxItem, CtxMeta


def mock_get(key):
    if key == "mode":
        return "test_mode"
    elif key == "model":
        return "id_model"
    elif key == "thread":
        return "id_thread"
    elif key == "assistant":
        return "id_assistant"
    elif key == "preset":
        return "id_preset"
    elif key == "context_threshold":
        return 200


def test_install():
    """
    Test install
    """
    ctx = Ctx()
    ctx.provider = MagicMock()
    ctx.provider.install = MagicMock()
    ctx.install()
    ctx.provider.install.assert_called_once_with()


def test_patch():
    """
    Test patch
    """
    ctx = Ctx()
    ctx.provider = MagicMock()
    ctx.provider.patch = MagicMock()
    version = '1.0.0'
    ctx.patch(version)
    ctx.provider.patch.assert_called_once_with(version)


def test_select(mock_window_conf):
    """
    Test select
    """
    mock_window_conf.controller = MagicMock()
    ctx = Ctx(mock_window_conf)
    ctx.current = 2

    item1 = CtxMeta()
    item1.mode = 'test_mode'
    item1.thread = 'id_thread'
    item1.assistant = 'id_assistant'
    item1.preset = 'id_preset'
    item1.model = 'id_model'
    item1.last_model = 'id_last_model'

    item2 = CtxMeta()
    item2.mode = 'test_mode2'

    ctx.meta = {
        2: item1,
        18: item2,
    }
    ctx.window.core.models.has_model = MagicMock()
    ctx.window.core.models.has_model.return_value = True

    ctx.load = MagicMock()
    ctx.select(2)
    assert ctx.current == 2
    assert ctx.mode == 'test_mode'
    assert ctx.model == 'id_last_model'
    assert ctx.thread == 'id_thread'
    assert ctx.assistant == 'id_assistant'
    assert ctx.preset == 'id_preset'

    ctx.load.assert_called_once_with(2)


def test_new(mock_window_conf):
    """
    Test new context
    """
    ctx = Ctx(mock_window_conf)
    container = MagicMock()
    container.get_items = MagicMock(return_value=[])
    ctx.container = container

    ctx.create_id = MagicMock(return_value='test_id')
    ctx.window.core.config.get.side_effect = mock_get
    ctx.current = 4
    ctx.mode = 'test_mode'

    item = CtxMeta()
    item.id = 4
    item.mode = 'test_mode'

    ctx.save = MagicMock()
    ctx.create = MagicMock(return_value=item)

    assert ctx.new() == item
    assert ctx.get_current() == 4
    assert ctx.mode == 'test_mode'
    assert ctx.model == 'id_model'
    assert ctx.preset == 'id_preset'
    assert ctx.thread is None
    assert ctx.assistant is None
    assert ctx.meta[4] == item
    assert ctx.meta[4].mode == 'test_mode'
    assert ctx.get_items() == []

    ctx.create.assert_called_once()
    ctx.save.assert_called_once_with(4)


def test_build():
    """
    Test build new context
    """
    ctx = Ctx()
    ctx.window = MagicMock()
    ctx.window.core.config.get.side_effect = mock_get

    item = CtxMeta()
    item.initialized = False
    item.mode = 'test_mode'
    item.model = 'id_model'
    item.last_model = 'id_model'
    item.last_mode = 'test_mode'
    ctx.create = MagicMock(return_value=item)

    result = ctx.build()
    assert result.mode == 'test_mode'
    assert result.model == 'id_model'
    assert result.last_model == 'id_model'
    assert result.last_mode == 'test_mode'
    assert result.initialized is False


def test_create():
    """
    Test create new context
    """
    item = CtxMeta()
    ctx = Ctx()
    ctx.provider = MagicMock()
    ctx.provider.create = MagicMock(return_value='test_id')
    ctx.build = MagicMock(return_value=item)
    result = ctx.create()
    assert result == item
    assert result.id == 'test_id'
    ctx.provider.create.assert_called_once_with(item)


def test_add():
    with patch('pygpt_net.core.ctx.ctx.Ctx.store') as mock_store:
        ctx = Ctx()
        ctx.current = 5
        ctx.meta = {
            5: CtxMeta()
        }
        ctx.provider = MagicMock()
        ctx.provider.append_item = MagicMock(return_value=False)

        container = MagicMock()        

        item = CtxItem()
        item.id = 'test_id'
        container.get_items = MagicMock(return_value=[item])
        ctx.container = container        
        ctx.add(item)
        assert ctx.get_items()[0] == item
        mock_store.assert_called_once()


def test_update_item():
    """
    Test update item
    """
    ctx = Ctx()
    ctx.provider = MagicMock()
    ctx.provider.update_item = MagicMock()
    item = CtxItem()
    item.id = 'test_id'
    ctx.update_item(item)
    ctx.provider.update_item.assert_called_once_with(item)


def test_is_empty(mock_window_conf):
    """
    Test is_empty
    """
    mock_window_conf.controller = MagicMock()
    ctx = Ctx(mock_window_conf)
    assert ctx.is_empty() is True
    ctx.current = 5
    assert ctx.is_empty() is True
    container = MagicMock()        
    container.count_items = MagicMock(return_value=3)
    ctx.container = container      
    assert ctx.is_empty() is False


def test_update(mock_window_conf):
    """
    Test update context data
    """
    ctx = Ctx(mock_window_conf)
    ctx.window.core.config.get.side_effect = mock_get
    ctx.current = 6
    ctx.mode = 'test_mode'

    item = CtxMeta()
    item.mode = 'test_mode'
    ctx.meta = {
        6: item,
    }
    ctx.save = MagicMock()
    ctx.update()
    assert ctx.current == 6
    assert ctx.mode == 'test_mode'
    assert ctx.meta[6].mode == 'test_mode'
    ctx.save.assert_called_once_with(6)


def test_post_update(mock_window_conf):
    """
    Test post update context data
    """
    ctx = Ctx(mock_window_conf)
    ctx.window.core.config.get.side_effect = mock_get
    ctx.current = 5
    ctx.mode = 'test_mode'

    item = CtxMeta()
    item.mode = 'test_mode'
    ctx.meta = {
        5: item,
    }
    ctx.save = MagicMock()
    ctx.post_update('test_mode')
    assert ctx.current == 5
    assert ctx.mode == 'test_mode'
    assert ctx.meta[5].mode == 'test_mode'
    ctx.save.assert_called_once_with(5)


def test_is_initialized(mock_window_conf):
    """
    Test is_initialized
    """
    ctx = Ctx(mock_window_conf)
    ctx.current = 5

    item = CtxMeta()
    item.initialized = True

    ctx.meta = {
        5: item,
    }
    assert ctx.is_initialized() is True

    item = CtxMeta()
    item.initialized = False
    ctx.meta = {
        5: item,
    }
    assert ctx.is_initialized() is False
    ctx.meta = {
        5: CtxMeta()
    }
    assert ctx.is_initialized() is False
    ctx.current = None
    assert ctx.is_initialized() is False


def test_set_initialized(mock_window_conf):
    """
    Test set_initialized
    """
    ctx = Ctx(mock_window_conf)
    ctx.current = 4

    item = CtxMeta()
    item.initialized = False
    ctx.meta = {
        4: item,
    }
    ctx.save = MagicMock()
    ctx.set_initialized()
    assert ctx.meta[4].initialized is True
    ctx.save.assert_called_once_with(4)
    ctx.current = None
    ctx.set_initialized()
    ctx.save.assert_called_once_with(4)


def test_has():
    """
    Test has
    """
    ctx = Ctx()
    ctx.meta = {
        5: CtxMeta()
    }
    assert ctx.has(5) is True
    assert ctx.has(4) is False


def test_get():
    """
    Test get
    """
    ctx = Ctx()
    item1 = CtxItem()
    item2 = CtxItem()
    items = [
        item1,
        item2,
    ]
    container = MagicMock()        
    container.get_items = MagicMock(return_value=items)
    container.count_items = MagicMock(return_value=2)
    ctx.container = container      

    assert ctx.get(0) == item1
    assert ctx.get(1) == item2


def test_get_meta(mock_window_conf):
    """
    Test list
    """
    ctx = Ctx(mock_window_conf)
    ctx.current = 2

    item1 = CtxMeta()
    item1.mode = 'test_mode'
    item2 = CtxMeta()
    item2.mode = 'test_mode2'

    ctx.meta = {
        2: item1,
        1: item2,
    }
    assert ctx.get_meta() == {
        2: item1,
        1: item2,
    }


def test_get_id_by_idx(mock_window_conf):
    """
    Test get_id_by_idx
    """
    ctx = Ctx(mock_window_conf)
    ctx.current = 3
    item1 = CtxMeta()
    item1.mode = 'test_mode'
    item2 = CtxMeta()
    item2.mode = 'test_mode2'
    ctx.meta = {
        1: item1,
        2: item2,
    }

    assert ctx.get_id_by_idx(1) == 2
    assert ctx.get_id_by_idx(0) == 1
    assert ctx.get_id_by_idx(2) is None


def test_get_idx_by_id(mock_window_conf):
    """
    Test get_idx_by_id
    """
    ctx = Ctx(mock_window_conf)
    ctx.current = 3

    item1 = CtxMeta()
    item1.mode = 'test_mode'
    item2 = CtxMeta()
    item2.mode = 'test_mode2'
    ctx.meta = {
        1: item1,
        2: item2,
    }

    assert ctx.get_idx_by_id(2) == 1
    assert ctx.get_idx_by_id(1) == 0
    assert ctx.get_idx_by_id(6) is None


def test_get_first(mock_window_conf):
    """
    Test get_first_ctx
    """
    ctx = Ctx(mock_window_conf)
    ctx.current = 3

    item1 = CtxMeta()
    item1.mode = 'test_mode'
    item2 = CtxMeta()
    item2.mode = 'test_mode2'
    ctx.meta = {
        1: item1,
        2: item2,
    }

    assert ctx.get_first() == 1
    ctx.meta = {}
    assert ctx.get_first() is None


def test_get_meta_by_id(mock_window_conf):
    """
    Test get_meta_by_id
    """
    ctx = Ctx(mock_window_conf)
    ctx.current = 3

    item1 = CtxMeta()
    item1.mode = 'test_mode'
    item2 = CtxMeta()
    item2.mode = 'test_mode2'
    ctx.meta = {
        1: item1,
        2: item2,
    }

    assert ctx.get_meta_by_id(2) == item2
    assert ctx.get_meta_by_id(1) == item1
    assert ctx.get_meta_by_id(3) is None


def test_get_last():
    """
    Test get_last
    """
    ctx = Ctx()
    items = [
        CtxItem(),
        CtxItem(),
        CtxItem(),
    ]
    container = MagicMock()        
    container.get_items = MagicMock(return_value=items)
    container.count_items = MagicMock(return_value=3)
    ctx.container = container      

    assert ctx.get_last() == ctx.get_items()[-1]


def test_prepare():
    """
    Test prepare
    """
    ctx = Ctx()
    ctx.meta = {}
    ctx.new = MagicMock()
    ctx.prepare()
    ctx.new.assert_called_once_with()
    ctx.new = MagicMock()
    ctx.meta = {
        'test_ctx': CtxMeta()
    }
    ctx.prepare()
    ctx.new.assert_not_called()


def test_count():
    """
    Test count
    """
    ctx = Ctx()
    items = [
        CtxItem(),
        CtxItem(),
        CtxItem(),
    ]
    container = MagicMock()        
    container.get_items = MagicMock(return_value=items)
    container.count_items = MagicMock(return_value=3)
    ctx.container = container      

    assert ctx.count() == 3


def test_count_meta():
    """
    Test count_meta
    """
    ctx = Ctx()
    ctx.meta = {
        33: CtxMeta()
    }
    assert ctx.count_meta() == 1
    ctx.meta = {}
    assert ctx.count_meta() == 0


def test_all():
    """
    Test all
    """
    ctx = Ctx()
    items = [
        CtxItem(),
        CtxItem(),
        CtxItem(),
    ]
    container = MagicMock()        
    container.get_items = MagicMock(return_value=items)
    container.count_items = MagicMock(return_value=3)
    ctx.container = container

    assert ctx.all() == ctx.get_items()


def test_remove():
    """
    Test remove
    """
    ctx = Ctx()
    ctx.meta = {
        3: CtxMeta()
    }
    ctx.provider = MagicMock()
    ctx.remove(3)
    ctx.provider.remove.assert_called_once_with(3)
    ctx.provider = MagicMock()
    ctx.remove(2)
    ctx.provider.remove.assert_not_called()


def test_truncate():
    """
    Test truncate
    """
    ctx = Ctx()
    ctx.window = MagicMock()
    ctx.meta = {
        3: CtxMeta()
    }
    os = MagicMock()
    ctx.provider = MagicMock()
    ctx.truncate()
    ctx.provider.truncate.assert_called_once_with()


def test_clear():
    """
    Test clear
    """
    ctx = Ctx()
    ctx.items = [
        CtxItem(),
        CtxItem(),
        CtxItem(),
    ]
    container = MagicMock()        
    container.get_items = MagicMock(return_value=[])
    ctx.container = container

    ctx.clear()
    assert ctx.get_items() == []


def test_append_thread(mock_window_conf):
    """
    Test append_thread
    """
    ctx = Ctx(mock_window_conf)
    ctx.current = 1
    ctx.thread = 'test_thread'

    item = CtxMeta()
    item.thread = 'test_thread'
    ctx.meta = {
        1: item
    }

    ctx.save = MagicMock()
    ctx.append_thread('test_thread')
    assert ctx.meta[1].thread == 'test_thread'
    ctx.save.assert_called_once_with(1)
    ctx.current = None
    ctx.append_thread('test_thread')
    ctx.save.assert_called_once_with(1)


def test_append_run(mock_window_conf):
    """
    Test append_run
    """
    ctx = Ctx(mock_window_conf)
    ctx.current = 3
    ctx.run = 'test_run'

    item = CtxMeta()
    item.run = 'test_run'
    ctx.meta = {
        3: item
    }
    ctx.save = MagicMock()
    ctx.append_run('test_run')
    assert ctx.meta[3].run == 'test_run'
    ctx.save.assert_called_once_with(3)
    ctx.current = None
    ctx.append_run('test_run')
    ctx.save.assert_called_once_with(3)


def test_append_status(mock_window_conf):
    """
    Test append_status
    """
    ctx = Ctx(mock_window_conf)
    ctx.current = 2
    ctx.status = 'test_status'

    item = CtxMeta()
    item.status = 'test_status'
    ctx.meta = {
        2: item
    }
    ctx.save = MagicMock()
    ctx.append_status('test_status')
    assert ctx.meta[2].status == 'test_status'
    ctx.save.assert_called_once_with(2)
    ctx.current = None
    ctx.append_status('test_status')
    ctx.save.assert_called_once_with(2)


def test_count_prompt_items():
    """
    Test count_prompt_items
    """
    ctx = Ctx()
    ctx.window = MagicMock()
    ctx.window.core = MagicMock()
    ctx.window.core.tokens = MagicMock()
    ctx.window.core.tokens.from_ctx = MagicMock()

    items = [
        CtxItem(),
        CtxItem(),
        CtxItem(),
    ]

    container = MagicMock()        
    container.get_items = MagicMock(return_value=items)
    container.count_items = MagicMock(return_value=3)
    ctx.container = container

    ctx.window.core.tokens.from_ctx.return_value = 10
    assert ctx.count_prompt_items('test_model', 'test_mode', 100, 1000) == (3, 30)

    ctx.window.core.tokens.from_ctx.return_value = 30
    assert ctx.count_prompt_items('test_model', 'test_mode', 100, 1000) == (3, 90)

    ctx.window.core.tokens.from_ctx.return_value = 100
    assert ctx.count_prompt_items('test_model', 'test_mode', 100, 1000) == (3, 300)

    ctx.window.core.tokens.from_ctx.return_value = 1000
    assert ctx.count_prompt_items('test_model', 'test_mode', 100, 1000) == (0, 0)

    ctx.window.core.tokens.from_ctx.return_value = 1000
    assert ctx.count_prompt_items('test_model', 'test_mode', 100, 2000) == (1, 1000)

    ctx.window.core.tokens.from_ctx.return_value = 10000
    assert ctx.count_prompt_items('test_model', 'test_mode', 100, 1000) == (0, 0)


def test_get_prompt_items():
    """
    Test get_prompt_items
    """
    ctx = Ctx()
    ctx.window = MagicMock()
    ctx.window.core = MagicMock()
    ctx.window.core.tokens = MagicMock()
    ctx.window.core.tokens.from_ctx = MagicMock()

    item1 = CtxItem()
    item2 = CtxItem()
    item3 = CtxItem()

    items = [
        item1,
        item2,
        item3,
    ]

    container = MagicMock()        
    container.get_items = MagicMock(return_value=items)
    container.count_items = MagicMock(return_value=3)
    ctx.container = container

    ctx.window.core.tokens.from_ctx.return_value = 10
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000) == ctx.get_items()[:2]
    assert len(ctx.get_prompt_items('test_model', 'test_mode', 100, 1000)) == 2
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000)[0] == item1
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000)[1] == item2

    ctx.window.core.tokens.from_ctx.return_value = 30
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000) == ctx.get_items()[:2]

    ctx.window.core.tokens.from_ctx.return_value = 100
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000) == ctx.get_items()[:2]

    ctx.window.core.tokens.from_ctx.return_value = 1000
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000) == []

    ctx.window.core.tokens.from_ctx.return_value = 10000
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000) == []

    item1 = CtxItem()
    item2 = CtxItem()
    item3 = CtxItem()
    item4 = CtxItem()
    item5 = CtxItem()
    item6 = CtxItem()

    items = [
        item1,
        item2,
        item3,
        item4,
        item5,
        item6,
    ]

    container = MagicMock()        
    container.get_items = MagicMock(return_value=items)
    container.count_items = MagicMock(return_value=3)
    ctx.container = container

    ctx.window.core.tokens.from_ctx.return_value = 10
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000) == ctx.get_items()[:5]
    assert len(ctx.get_prompt_items('test_model', 'test_mode', 100, 1000)) == 5
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000)[0] == item1
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000)[1] == item2
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000)[2] == item3
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000)[3] == item4
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000)[4] == item5

    ctx.window.core.tokens.from_ctx.return_value = 30
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000) == ctx.get_items()[:5]

    ctx.window.core.tokens.from_ctx.return_value = 130
    assert len(ctx.get_prompt_items('test_model', 'test_mode', 1000, 1400)) == 3
    assert ctx.get_prompt_items('test_model', 'test_mode', 1000, 1400)[0] == item3
    assert ctx.get_prompt_items('test_model', 'test_mode', 1000, 1400)[1] == item4
    assert ctx.get_prompt_items('test_model', 'test_mode', 1000, 1400)[2] == item5

    ctx.window.core.tokens.from_ctx.return_value = 1000
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000) == []

    ctx.window.core.tokens.from_ctx.return_value = 10000
    assert ctx.get_prompt_items('test_model', 'test_mode', 100, 1000) == []


def test_get_all_items(mock_window_conf):
    """
    Test get_all_items
    """
    ctx = Ctx(mock_window_conf)
    item1 = CtxItem()
    item2 = CtxItem()
    items = [
        item1,
        item2
    ]
    container = MagicMock()        
    container.get_items = MagicMock(return_value=items)
    container.count_items = MagicMock(return_value=3)
    ctx.container = container

    assert ctx.get_all_items(False) == [
        item1,
        item2
    ]


def test_check(mock_window_conf):
    """
    Test check
    """
    ctx = Ctx(mock_window_conf)
    ctx.get_tokens_left = MagicMock()
    ctx.get_tokens_left.return_value = 10
    ctx.remove_first = MagicMock()
    ctx.check(5, 20)
    ctx.remove_first.assert_not_called()
    ctx.check(10, 20)
    ctx.remove_first.assert_called_once_with()


def test_get_tokens_left(mock_window_conf):
    """
    Test get_tokens_left
    """
    ctx = Ctx(mock_window_conf)
    ctx.get_total_tokens = MagicMock()
    ctx.get_total_tokens.return_value = 10
    assert ctx.get_tokens_left(20) == 10
    ctx.get_total_tokens.return_value = 20
    assert ctx.get_tokens_left(20) == 0


def test_get_total_tokens(mock_window_conf):
    """
    Test get_total_tokens
    """
    last_item = CtxItem()
    last_item.total_tokens = 66
    ctx = Ctx(mock_window_conf)
    ctx.get_last = MagicMock()
    ctx.get_last.return_value = last_item

    assert ctx.get_total_tokens() == 66


def test_get_last_tokens(mock_window_conf):
    """
    Test get_last_tokens
    """
    ctx = Ctx(mock_window_conf)
    ctx.get_last = MagicMock()
    ctx.get_last.return_value = CtxItem()
    ctx.get_last().total_tokens = 10
    assert ctx.get_last_tokens() == 10
    ctx.get_last.return_value = None
    assert ctx.get_last_tokens() == 0


def test_remove_last(mock_window_conf):
    """
    Test remove_last
    """
    ctx = Ctx(mock_window_conf)
    items = [
        'item1',
        'item2'
    ]
    container = MagicMock()        
    container.get_items = MagicMock(return_value=items)
    container.count_items = MagicMock(return_value=2)
    ctx.container = container

    ctx.remove_last()
    assert ctx.get_items() == [
        'item1'
    ]
    ctx.items = []
    ctx.remove_last()
    assert ctx.items == []


def test_remove_first(mock_window_conf):
    """
    Test remove_first
    """
    ctx = Ctx(mock_window_conf)
    items = [
        'item1',
        'item2'
    ]
    container = MagicMock()        
    container.get_items = MagicMock(return_value=items)
    container.count_items = MagicMock(return_value=2)
    ctx.container = container

    ctx.remove_first()
    assert ctx.get_items() == [
        'item2'
    ]
    ctx.items = []
    ctx.remove_first()
    assert ctx.items == []


def test_is_allowed_for_mode(mock_window_conf):
    """
    Test is_allowed_for_mode
    """
    ctx = Ctx(mock_window_conf)
    ctx.window = MagicMock()
    ctx.window.core.config.get.return_value = True
    ctx.allowed_modes = {
        'test_mode': [
            'test_mode'
        ],
        'test_mode2': [],
    }

    meta = CtxMeta()
    meta.id = 3
    meta.last_mode = 'test_mode'
    ctx.meta = {
        3: meta
    }
    items = [
        CtxItem(),
        CtxItem(),
    ]

    container = MagicMock()        
    container.get_items = MagicMock(return_value=items)
    container.count_items = MagicMock(return_value=2)
    ctx.container = container

    ctx.get_meta_by_id = MagicMock(return_value=meta)

    ctx.current = 3
    assert ctx.is_allowed_for_mode('test_mode') is True

    ctx.current = 3
    assert ctx.is_allowed_for_mode('test_mode') is True

    ctx.current = 3
    assert ctx.is_allowed_for_mode('test_mode2') is False


def test_load_meta(mock_window_conf):
    """
    Test load_meta
    """
    ctx = Ctx(mock_window_conf)
    ctx.window = MagicMock()
    ctx.window.core.config.has.return_value = True
    ctx.window.core.config.get.return_value = 1000
    ctx.provider = MagicMock()
    metas = {
        2: CtxMeta(),
        4: CtxMeta(),
    }
    ctx.provider.get_meta.return_value = metas
    ctx.search_string = 'abc'
    ctx.load_meta()
    assert ctx.meta == metas


def test_load(mock_window_conf):
    """
    Test load
    """
    ctx = Ctx(mock_window_conf)
    ctx.window = MagicMock()
    ctx.provider = MagicMock()
    items = [
        CtxItem(),
        CtxItem(),
    ]
    ctx.provider.load.return_value = items
    ctx.search_string = 'cba'
    res = ctx.load(3)
    assert res == items


def test_save(mock_window_conf):
    """
    Test save
    """
    ctx = Ctx(mock_window_conf)
    ctx.window = MagicMock()
    ctx.provider = MagicMock()
    ctx.meta = {
        3: CtxMeta()
    }
    items = [
        CtxItem(),
        CtxItem(),
    ]
    container = MagicMock()        
    container.get_items = MagicMock(return_value=items)
    container.count_items = MagicMock(return_value=2)
    ctx.container = container
    ctx.save(3)
    ctx.provider.save.assert_called_once_with(3, ctx.meta[3], ctx.get_items())


def test_store(mock_window_conf):
    """
    Test store
    """
    ctx = Ctx(mock_window_conf)
    ctx.current = 7
    ctx.meta = {
        7: CtxMeta(),
        8: CtxMeta(),
    }
    ctx.save = MagicMock()
    ctx.store()
    ctx.save.assert_called_once_with(7)