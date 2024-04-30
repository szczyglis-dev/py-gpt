#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.30 15:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch

from pygpt_net.item.model import ModelItem
from tests.mocks import mock_window
from pygpt_net.controller.chat.text import Text


def test_send(mock_window):
    """Test handle text"""
    text = Text(mock_window)

    mock_window.core.config.data['mode'] = 'chat'
    mock_window.core.config.data['model'] = 'gpt-4'
    mock_window.core.config.data['user_name'] = 'User'
    mock_window.core.config.data['ai_name'] = 'AI'
    mock_window.core.config.data['prompt'] = 'You are a bot'
    mock_window.core.config.data['stream'] = False
    mock_window.core.config.data['ctx.auto_summary'] = True
    mock_window.core.config.data['store_history'] = True

    mock_window.core.config.data['cmd'] = True

    result = True
    mock_window.core.gpt.call = MagicMock(return_value=result)
    mock_window.core.chain.call = MagicMock(return_value=result)
    mock_window.controller.plugins.is_type_enabled = MagicMock(return_value=False)
    mock_window.controller.agent.enabled = MagicMock(return_value=False)

    model = ModelItem()
    mock_window.core.models.get = MagicMock(return_value=model)

    with patch('PySide6.QtWidgets.QApplication.processEvents') as mock_process_events:

        ctx = text.send('message')

        mock_window.controller.chat.files.upload.assert_called_once_with('chat')  # should upload files
        mock_window.core.history.append.assert_called_once()  # should append to history

        mock_window.core.command.append_syntax.assert_called_once()  # should append cmd syntax

        mock_window.controller.chat.render.append_input.assert_called_once()  # should append input
        mock_window.core.ctx.add.assert_called_once()  # should add ctx to DB
        mock_window.controller.ctx.update.assert_called_once_with(reload=True, all=False)  # should update ctx list
        mock_window.controller.chat.common.lock_input.assert_called_once()  # should lock input
        mock_window.core.bridge.call.assert_called_once()  # should call gpt
        mock_window.core.ctx.update_item.assert_called()  # should update ctx item
        mock_window.controller.chat.output.handle.assert_called_once()  # should handle output
        mock_window.controller.chat.output.handle_cmd.assert_called_once()  # should handle cmds
        mock_window.controller.chat.render.reload.assert_not_called()  # should not reload output (if not stream)
        mock_window.controller.chat.common.unlock_input.assert_called_once()  # should unlock input
        mock_window.controller.ctx.prepare_name.assert_called_once()  # should prepare name for ctx

        assert ctx.input_name == 'User'  # should have input name
        assert ctx.output_name == 'AI'  # should have output name
        assert ctx.input == 'message'  # should have input text


def test_send_stream(mock_window):
    """Test handle text: stream"""
    text = Text(mock_window)

    mock_window.core.config.data['mode'] = 'chat'
    mock_window.core.config.data['model'] = 'gpt-4'
    mock_window.core.config.data['user_name'] = 'User'
    mock_window.core.config.data['ai_name'] = 'AI'
    mock_window.core.config.data['prompt'] = 'You are a bot'
    mock_window.core.config.data['stream'] = True
    mock_window.core.config.data['ctx.auto_summary'] = True
    mock_window.core.config.data['store_history'] = True

    model = ModelItem()
    mock_window.core.models.get = MagicMock(return_value=model)

    result = True
    mock_window.core.gpt.call = MagicMock(return_value=result)
    mock_window.core.chain.call = MagicMock(return_value=result)
    mock_window.controller.plugins.is_type_enabled = MagicMock(return_value=False)
    mock_window.controller.agent.enabled = MagicMock(return_value=False)

    with patch('PySide6.QtWidgets.QApplication.processEvents') as mock_process_events:

        ctx = text.send('message')

        mock_window.controller.chat.files.upload.assert_called_once_with('chat')  # should upload files
        mock_window.core.history.append.assert_called_once()  # should append to history
        mock_window.controller.chat.render.append_input.assert_called_once()  # should append input
        mock_window.core.ctx.add.assert_called_once()  # should add ctx to DB
        mock_window.controller.ctx.update.assert_called_once_with(reload=True, all=False)  # should update ctx list
        mock_window.controller.chat.common.lock_input.assert_called_once()  # should lock input
        mock_window.core.bridge.call.assert_called_once()  # should call bridge
        mock_window.core.ctx.update_item.assert_called()  # should update ctx item
        mock_window.controller.chat.output.handle.assert_called_once()  # should handle output
        mock_window.controller.chat.output.handle_cmd.assert_called_once()  # should handle cmds
        mock_window.controller.chat.render.end.assert_called_once()  # should not reload output (if not stream)
        mock_window.controller.chat.common.unlock_input.assert_called_once()  # should unlock input
        mock_window.controller.ctx.prepare_name.assert_called_once()  # should prepare name for ctx

        assert ctx.input_name == 'User'  # should have input name
        assert ctx.output_name == 'AI'  # should have output name
        assert ctx.input == 'message'  # should have input text


def test_send_assistant(mock_window):
    """Test handle text: assistant mode"""
    text = Text(mock_window)

    mock_window.core.config.data['mode'] = 'assistant'
    mock_window.core.config.data['model'] = 'gpt-4'
    mock_window.core.config.data['user_name'] = 'User'
    mock_window.core.config.data['ai_name'] = 'AI'
    mock_window.core.config.data['prompt'] = 'You are a bot'
    mock_window.core.config.data['stream'] = False
    mock_window.core.config.data['ctx.auto_summary'] = True
    mock_window.core.config.data['store_history'] = True
    mock_window.core.config.data['assistant_thread'] = 'th_123'

    model = ModelItem()
    mock_window.core.models.get = MagicMock(return_value=model)

    result = True
    mock_window.core.gpt.call = MagicMock(return_value=result)
    mock_window.core.chain.call = MagicMock(return_value=result)

    with patch('PySide6.QtWidgets.QApplication.processEvents') as mock_process_events:

        ctx = text.send('message')

        mock_window.controller.chat.files.upload.assert_called_once_with('assistant')  # should upload files
        mock_window.core.history.append.assert_called_once()  # should append to history
        mock_window.controller.assistant.prepare.assert_called_once()  # should prepare assistant
        mock_window.controller.chat.render.append_input.assert_called_once()  # should append input
        mock_window.core.ctx.add.assert_called_once()  # should add ctx to DB
        mock_window.controller.ctx.update.assert_called_once_with(reload=True, all=False)  # should update ctx list
        mock_window.controller.chat.common.lock_input.assert_called_once()  # should lock input
        mock_window.core.bridge.call.assert_called_once()  # should call gpt

        mock_window.core.ctx.update_item.assert_called()  # should update ctx item

        mock_window.controller.chat.output.handle.assert_not_called()  # should NOT handle output (if assistant)
        mock_window.controller.chat.output.handle_cmd.assert_not_called()  # should NOT handle cmds (if assistant)

        mock_window.controller.chat.render.reload.assert_not_called()  # should not reload output (if not stream)
        mock_window.controller.chat.common.unlock_input.assert_not_called()  # should not unlock input
        mock_window.controller.ctx.prepare_name.assert_called_once()  # should prepare name for ctx

        assert ctx.input_name == 'User'  # should have input name
        assert ctx.output_name == 'AI'  # should have output name
        assert ctx.input == 'message'  # should have input text
        assert ctx.thread == 'th_123'  # should have thread id


def test_log(mock_window):
    """Test log"""
    text = Text(mock_window)
    text.log('msg')
    mock_window.core.debug.info.assert_called_once_with('msg')
