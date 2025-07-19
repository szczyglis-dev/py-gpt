#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.19 17:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.ctx import Ctx
from pygpt_net.item.ctx import CtxMeta, CtxItem


def test_setup(mock_window):
    """Test setup ctx"""
    ctx = Ctx(mock_window)

    mock_window.core.ctx.count_meta = MagicMock(return_value=4)  # fake have 4 ctx metas
    mock_window.core.config.data['ctx'] = 3  # fake last ctx is 3
    mock_window.core.ctx.has = MagicMock(return_value=True)  # fake ctx 3 exists

    ctx.load = MagicMock()
    ctx.search_string_change = MagicMock()
    ctx.select_by_current = MagicMock()
    mock_window.core.ctx.get_current = MagicMock(return_value=3)

    # fake search string
    mock_window.core.config.data["ctx.search.string"] = "test"

    ctx.setup()
    mock_window.core.ctx.count_meta.assert_called_once()

    # ctx.load.assert_called_once()


def test_setup_new(mock_window):
    """Test setup ctx"""
    ctx = Ctx(mock_window)

    # no ctx metas
    mock_window.core.ctx.count_meta = MagicMock(return_value=0)  # no ctx metas
    mock_window.core.config.data['ctx'] = None
    mock_window.core.ctx.has = MagicMock(return_value=False)

    ctx.load = MagicMock()
    ctx.new = MagicMock()
    ctx.search_string_change = MagicMock()
    ctx.select_by_current = MagicMock()

    # fake search string
    mock_window.core.config.data["ctx.search.string"] = "test"

    ctx.setup()
    mock_window.core.ctx.count_meta.assert_called_once()

    ctx.new.assert_called_once()  # new ctx should be created
    # ctx.load.assert_called_once()  # new ctx should be loaded


def test_update(mock_window):
    """Test update ctx"""
    ctx = Ctx(mock_window)

    ctx.update_list = MagicMock()
    ctx.select_by_current = MagicMock()
    mock_window.controller.ui.update = MagicMock()

    mock_window.core.ctx.get_current = MagicMock(return_value=3)
    mock_window.core.ctx.get_thread = MagicMock(return_value='th_123')

    ctx.update(reload=True, all=True)

    ctx.update_list.assert_called_once()  # reload
    ctx.select_by_current.assert_called_once()  # reload
    mock_window.controller.ui.update.assert_called_once()  # all
    mock_window.core.config.save.assert_called_once()  # save config with ctx and thread id (mocked here)

    assert mock_window.core.config.data['ctx'] == 3
    assert mock_window.core.config.data['assistant_thread'] == 'th_123'


def test_select(mock_window):
    """Test select ctx"""
    ctx = Ctx(mock_window)

    ctx.load = MagicMock()
    ctx.common = MagicMock()
    ctx.common.focus_chat = MagicMock()

    ctx.select(3)

    ctx.load.assert_called_once_with(3)
    ctx.common.focus_chat.assert_called_once()


def test_select_by_idx(mock_window):
    """Test select ctx by index"""
    ctx = Ctx(mock_window)

    ctx.context_change_locked = MagicMock(return_value=False)
    mock_window.core.ctx.get_id_by_idx = MagicMock(return_value=3)
    ctx.select = MagicMock()

    ctx.select_by_idx(3)

    mock_window.core.ctx.get_id_by_idx.assert_called_once_with(3)
    ctx.select.assert_called_once_with(3)


def test_select_by_current(mock_window):
    """Test select ctx by current"""
    ctx = Ctx(mock_window)
    meta = {
        1: CtxMeta(),
        2: CtxMeta(),
        3: CtxMeta(),  # current
    }
    mock_window.core.ctx.current = 3
    mock_window.core.ctx.get_meta = MagicMock(return_value=meta)
    mock_window.core.ctx.get_idx_by_id = MagicMock(return_value=2)  # idx = 2
    mock_window.ui.models['ctx.list'].index = MagicMock(return_value=2)  # index = 2

    ctx.select_index_by_id = MagicMock()
    ctx.select_by_current()
    mock_window.core.ctx.get_meta.assert_called_once()


def test_new(mock_window):
    """Test new ctx"""
    ctx = Ctx(mock_window)
    ctx.context_change_locked = MagicMock(return_value=False)

    ctx.common = MagicMock()
    ctx.common.update_label = MagicMock()
    ctx.update = MagicMock()
    ctx.select = MagicMock()

    mock_window.core.ctx.mode = 'assistant'  # mode from ctx is used to update ctx label
    mock_window.core.config.data['assistant'] = 'as_123'  # fake assistant id
    mock_window.core.ctx.get_mode = MagicMock(return_value='assistant')
    mock_window.core.ctx.get_assistant = MagicMock(return_value='as_123')

    ctx.new()
    assert mock_window.core.config.get('assistant_thread') is None  # reseted assistant thread id
    mock_window.core.ctx.new.assert_called_once()
    ctx.update.assert_called_once()

    mock_window.controller.chat.common.unlock_input.assert_called_once()

    ctx.common.update_label.assert_called_once_with('assistant', 'as_123')


def test_add(mock_window):
    """Test add ctx item"""
    ctx = Ctx(mock_window)
    ctx.update = MagicMock()

    ctx.add(CtxItem())
    ctx.update.assert_called_once()


def test_update_list(mock_window):
    """Test update_list"""
    ctx = Ctx(mock_window)
    ctx.update = MagicMock()
    meta = {
        1: CtxMeta(),
        2: CtxMeta(),
        3: CtxMeta(),  # current
    }
    mock_window.core.ctx.get_meta = MagicMock(return_value=meta)

    ctx.update_list()
    mock_window.ui.contexts.ctx_list.update.assert_called_once_with('ctx.list', meta)


def test_refresh(mock_window):
    """Test refresh ctx"""
    ctx = Ctx(mock_window)
    ctx.load = MagicMock()
    mock_window.core.ctx.get_current = MagicMock(return_value=3)

    ctx.refresh()
    ctx.load.assert_called_once_with(3, True)


def test_refresh_output(mock_window):
    """Test refresh output"""
    ctx = Ctx(mock_window)
    mock_window.controller.chat.render.append_context = MagicMock()

    ctx.refresh_output()

    mock_window.dispatch.assert_called()


def test_load(mock_window):
    """Test load ctx"""
    ctx = Ctx(mock_window)
    ctx.update = MagicMock()
    ctx.common = MagicMock()
    ctx.common.update_label = MagicMock()
    mock_window.controller.chat.render.reset = MagicMock()
    mock_window.core.ctx.select = MagicMock()

    mock_window.core.models.has_model = MagicMock(return_value=True)

    mock_window.core.ctx.get_thread = MagicMock(return_value='th_123')
    mock_window.core.ctx.get_mode = MagicMock(return_value='assistant')
    mock_window.core.ctx.get_model = MagicMock(return_value='gpt-4')
    mock_window.core.ctx.get_assistant = MagicMock(return_value='as_123')
    mock_window.core.ctx.get_preset = MagicMock(return_value='preset_123')

    ctx.load(3)

    mock_window.core.ctx.select.assert_called_once_with(3, restore_model=True)
    mock_window.controller.mode.set.assert_called_once_with('assistant')
    mock_window.controller.presets.set.assert_called_once_with('assistant', 'preset_123')
    mock_window.controller.presets.refresh.assert_called_once()

    ctx.update.assert_called_once()
    ctx.common.update_label.assert_called_once_with('assistant', 'as_123')

    # assistant mode only:
    mock_window.controller.assistant.select_by_id.assert_called_once_with('as_123')
    mock_window.controller.model.set.assert_called_once_with('assistant', 'gpt-4')

    assert mock_window.core.config.get('assistant_thread') == 'th_123'


def test_update_ctx(mock_window):
    """Test update ctx"""
    ctx = Ctx(mock_window)
    ctx.common = MagicMock()
    ctx.common.update_label = MagicMock()
    mock_window.core.config.data['mode'] = 'assistant'
    mock_window.core.config.data['assistant'] = 'as_123'

    mock_window.core.ctx.get_mode = MagicMock(return_value='assistant')
    mock_window.core.ctx.get_assistant = MagicMock(return_value='as_123')
    mock_window.core.ctx.is_allowed_for_mode = MagicMock(return_value=True)

    ctx.update_ctx()
    mock_window.core.ctx.update.assert_called_once()
    ctx.common.update_label.assert_called_once_with('assistant', 'as_123')  # from core.ctx.assistant


def test_delete(mock_window):
    """Test delete ctx"""
    ctx = Ctx(mock_window)
    ctx.update = MagicMock()
    mock_window.core.ctx.get_current = MagicMock(return_value=3)

    mock_window.ui.dialogs.confirm = MagicMock()
    mock_window.core.ctx.get_id_by_idx = MagicMock(return_value=3)
    mock_window.core.ctx.remove = MagicMock()

    ctx.delete(3, True)
    mock_window.core.ctx.remove.assert_called_once_with(3)
    ctx.update.assert_called_once()

    # current
    mock_window.dispatch.assert_called()


def test_delete_history(mock_window):
    """Test delete ctx history"""
    ctx = Ctx(mock_window)
    ctx.update = MagicMock()
    mock_window.core.ctx.truncate = MagicMock()

    mock_window.ui.dialogs.confirm = MagicMock()
    ctx.delete_history(True)
    mock_window.core.ctx.truncate.assert_called_once()
    ctx.update.assert_called_once()


def test_rename(mock_window):
    """Test rename ctx"""
    ctx = Ctx(mock_window)
    ctx.update = MagicMock()

    meta = CtxMeta()
    meta.name = 'new_name'

    mock_window.ui.dialogs.confirm = MagicMock()
    mock_window.ui.dialog['rename'] = MagicMock()
    mock_window.core.ctx.get_id_by_idx = MagicMock(return_value=3)
    mock_window.core.ctx.get_meta_by_id = MagicMock(return_value=meta)

    ctx.rename(2)
    assert mock_window.ui.dialog['rename'].id == 'ctx'
    mock_window.ui.dialog['rename'].input.setText.assert_called_once_with('new_name')
    assert mock_window.ui.dialog['rename'].current == 2
    mock_window.ui.dialog['rename'].show.assert_called_once()


def test_update_name(mock_window):
    """Test update name"""
    ctx = Ctx(mock_window)
    meta = {
        1: CtxMeta(),
        2: CtxMeta(),
        3: CtxMeta(),  # current
    }
    mock_window.core.ctx.get_meta = MagicMock(return_value=meta)
    ctx.update = MagicMock()
    ctx.update_name(3, 'new_name', True)

    assert mock_window.core.ctx.meta[3].name == 'new_name'
    mock_window.core.ctx.get_meta.assert_called_once()
    mock_window.core.ctx.set_initialized.assert_called_once()
    mock_window.core.ctx.save.assert_called_once_with(3)
    mock_window.ui.dialog['rename'].close.assert_called_once()
    ctx.update.assert_called_once()


def test_handle_allowed_no(mock_window):
    """Test handle allowed no"""
    ctx = Ctx(mock_window)
    ctx.new = MagicMock()
    mock_window.core.ctx.is_allowed_for_mode = MagicMock(return_value=False)

    assert ctx.handle_allowed('assistant') is False
    ctx.new.assert_called_once_with(True)


def test_handle_allowed_yes(mock_window):
    """Test handle allowed yes"""
    ctx = Ctx(mock_window)
    ctx.new = MagicMock()
    mock_window.core.ctx.is_allowed_for_mode = MagicMock(return_value=True)
    assert ctx.handle_allowed('assistant') is True


def test_selection_change(mock_window):
    """Test selection change"""
    ctx = Ctx(mock_window)
    ctx.selection_change()
    mock_window.ui.nodes['ctx.list'].lockSelection.assert_called_once()


def test_search_string_change(mock_window):
    """Test search string change"""
    ctx = Ctx(mock_window)
    ctx.update = MagicMock()
    ctx.window.core.ctx.get_search_string = MagicMock(return_value='new_string')
    ctx.search_string_change('new_string')
    assert ctx.window.core.ctx.get_search_string() == 'new_string'
    assert mock_window.core.config.get('ctx.search.string') == 'new_string'
    ctx.update.assert_called_once()


def test_prepare_name(mock_window):
    """Test prepare name"""
    ctx = Ctx(mock_window)
    ctx.summarizer = MagicMock()
    mock_window.core.ctx.is_initialized = MagicMock(return_value=False)
    mock_window.core.ctx.get_current = MagicMock(return_value=3)

    item = CtxItem()
    item.id = 3

    mock_window.core.ctx.current = 3
    ctx.prepare_name(item)
    ctx.summarizer.summarize.assert_called_once_with(3, item)


def test_context_change_locked(mock_window):
    """Test is context change locked"""
    ctx = Ctx(mock_window)
    mock_window.controller.chat.input.generating = True
    assert ctx.context_change_locked() is True
    mock_window.controller.chat.input.generating = False
    assert ctx.context_change_locked() is False
