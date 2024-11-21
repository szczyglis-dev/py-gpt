#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.27 10:00:00                  #
# ================================================== #

import webbrowser
from unittest.mock import MagicMock

from pygpt_net.item.assistant import AssistantItem
from tests.mocks import mock_window
from pygpt_net.controller.assistant import Assistant


def test_setup(mock_window):
    """Test setup assistant"""
    mock_window.controller.config.get_value = MagicMock(return_value=0)
    assistant = Assistant(mock_window)
    mock_window.core.assistants.load = MagicMock()
    assistant.update = MagicMock()
    assistant.setup()
    mock_window.core.assistants.load.assert_called_once()
    assistant.update.assert_called_once()


def test_update(mock_window):
    """Test update assistant"""
    assistant = Assistant(mock_window)
    assistant.files = MagicMock()
    assistant.update_list = MagicMock()
    assistant.select_current = MagicMock()
    assistant.files.update_list = MagicMock()
    assistant.update()
    assistant.update_list.assert_called_once()
    assistant.select_current.assert_called_once()
    assistant.files.update_list.assert_called_once()


def test_update_list(mock_window):
    """Test update assistant list"""
    assistant = Assistant(mock_window)
    mock_window.core.assistants.get_all = MagicMock()
    mock_window.ui.toolbox.assistants.update = MagicMock()
    assistant.update_list()
    mock_window.core.assistants.get_all.assert_called_once()
    mock_window.ui.toolbox.assistants.update.assert_called_once()


def test_prepare(mock_window):
    """Test prepare assistant"""
    assistant = Assistant(mock_window)
    mock_window.core.config.data['assistant_thread'] = None
    mock_window.ui.status = MagicMock()
    assistant.threads.create_thread = MagicMock()
    assistant.prepare()
    assistant.threads.create_thread.assert_called_once()
    assert mock_window.core.config.get('assistant_thread') == assistant.threads.create_thread.return_value


def test_refresh(mock_window):
    """Test refresh assistant"""
    assistant = Assistant(mock_window)
    assistant.select_default = MagicMock()
    assistant.refresh()
    assistant.select_default.assert_called_once()


def test_select(mock_window):
    """Test select assistant"""
    assistant = Assistant(mock_window)
    assistant.change_locked = MagicMock(return_value=False)
    mock_window.core.assistants.get_by_idx = MagicMock(return_value='assistant_id')
    assistant.select_by_id = MagicMock()
    assistant.select(1)
    assistant.select_by_id.assert_called_once_with('assistant_id')


def test_select_by_id(mock_window):
    """Test select assistant by id"""
    assistant = Assistant(mock_window)
    mock_window.core.config.data['current_model'] = {}
    mock_window.core.assistants.get_by_id = MagicMock(return_value=None)
    mock_window.controller.attachment.import_from_assistant = MagicMock()
    mock_window.controller.attachment.update = MagicMock()
    mock_window.controller.ctx.update_ctx = MagicMock()

    assistant.select_by_id('assistant_id')
    mock_window.controller.attachment.update.assert_called_once()
    mock_window.controller.ctx.update_ctx.assert_called_once()
    assert mock_window.core.config.get('assistant') == 'assistant_id'


def test_select_current(mock_window):
    """Test select current assistant"""
    assistant = Assistant(mock_window)
    item = AssistantItem()
    mock_window.core.config.get = MagicMock(return_value='assistant_id')
    mock_window.core.assistants.get_all = MagicMock(return_value={'assistant_id': item})
    mock_window.ui.models = {'assistants': MagicMock()}
    mock_window.ui.nodes = {'assistants': MagicMock()}
    mock_window.ui.models['assistants'].index = MagicMock(return_value='current')
    mock_window.ui.nodes['preset.prompt'] = MagicMock()
    assistant.select_current()
    mock_window.core.config.get.assert_called_once_with('assistant')
    mock_window.core.assistants.get_all.assert_called_once()
    mock_window.ui.models['assistants'].index.assert_called_once_with(0, 0)
    mock_window.ui.nodes['assistants'].setCurrentIndex.assert_called_once_with('current')


def test_select_default(mock_window):
    """Test select default assistant"""
    assistant = Assistant(mock_window)
    mock_window.core.config.data['mode'] = 'assistant'
    mock_window.core.config.data['assistant'] = None
    assistant.update = MagicMock()
    mock_window.core.assistants.get_default_assistant = MagicMock(return_value='assistant_id')

    assistant.select_default()
    assistant.update.assert_called_once()
    assert mock_window.core.config.get('assistant') == 'assistant_id'


def test_create(mock_window):
    """Test create assistant"""
    assistant = Assistant(mock_window)
    item = AssistantItem()
    mock_window.core.assistants.create = MagicMock(return_value=item)

    assistant.editor.assign_data = MagicMock()
    mock_window.core.gpt.assistants.create = MagicMock()

    assistant.create()
    mock_window.core.assistants.create.assert_called_once()
    assistant.editor.assign_data.assert_called_once_with(item)
    mock_window.core.gpt.assistants.create.assert_called_once()


def test_clear(mock_window):
    """Test clear assistant"""
    assistant = Assistant(mock_window)
    item = AssistantItem()
    item.id = 'assistant_id'
    mock_window.core.config.data['assistant'] = 'assistant_id'
    mock_window.core.assistants.get_by_id = MagicMock(return_value=item)
    mock_window.core.assistants.has = MagicMock(return_value=True)
    assistant.update = MagicMock()

    assistant.clear(force=True)
    assert item.id is None  # should be reset
    assistant.update.assert_called_once()


def test_delete(mock_window):
    """Test delete assistant"""
    assistant = Assistant(mock_window)
    item = AssistantItem()
    item.id = 'assistant_id'
    mock_window.core.config.data['assistant'] = 'assistant_id'
    mock_window.core.assistants.get_by_idx = MagicMock(return_value='assistant_id')
    mock_window.core.assistants.has = MagicMock(return_value=True)
    mock_window.core.gpt.assistants.delete = MagicMock()
    mock_window.core.assistants.delete = MagicMock()
    assistant.update = MagicMock()
    assistant.delete(1, force=True)

    # assert item.id is None  # ??
    assert mock_window.core.config.get('assistant') is None
    assert mock_window.core.config.get('assistant_thread') is None
    mock_window.core.gpt.assistants.delete.assert_called_once()
    mock_window.core.assistants.delete.assert_called_once()
    assistant.update.assert_called_once()


def test_goto_online(mock_window):
    """Test goto online assistant page"""
    assistant = Assistant(mock_window)
    webbrowser.open = MagicMock()
    assistant.goto_online()
    webbrowser.open.assert_called_once_with('https://platform.openai.com/assistants')


def test_change_locked(mock_window):
    """Test change locked"""
    assistant = Assistant(mock_window)
    mock_window.controller.chat.input.generating = True
    assert assistant.change_locked() is True
    mock_window.controller.chat.input.generating = False
    assert assistant.change_locked() is False
    