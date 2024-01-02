#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.02 02:00:00                  #
# ================================================== #

import os

import pytest
from unittest.mock import MagicMock, mock_open, patch

from PySide6.QtWidgets import QMainWindow

from pygpt_net.config import Config
from pygpt_net.controller.chat.text import Text


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.core = MagicMock()
    window.core.config = Config(window)  # real config object
    window.core.config.initialized = True  # prevent initializing config
    window.core.config.init = MagicMock()  # mock init method to prevent init
    window.core.config.load = MagicMock()  # mock load method to prevent loading
    window.core.config.save = MagicMock()  # mock save method to prevent saving
    window.controller = MagicMock()
    window.ui = MagicMock()
    return window


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

    with patch('PySide6.QtWidgets.QApplication.processEvents') as mock_process_events:

        ctx = text.send('message')

        mock_window.controller.chat.files.upload.assert_called_once_with('chat')  # should upload files
        mock_window.core.history.append.assert_called_once()  # should append to history

        mock_window.core.command.get_prompt.assert_called_once()  # should get cmd prompt
        mock_window.core.command.append_syntax.assert_called_once()  # should append cmd syntax

        mock_window.controller.chat.render.append_input.assert_called_once()  # should append input
        mock_window.core.ctx.add.assert_called_once()  # should add ctx to DB
        mock_window.controller.ctx.update.assert_called_once_with(reload=True, all=False)  # should update ctx list
        mock_window.controller.chat.common.lock_input.assert_called_once()  # should lock input
        mock_window.core.gpt.call.assert_called_once()  # should call gpt
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

    result = True
    mock_window.core.gpt.call = MagicMock(return_value=result)
    mock_window.core.chain.call = MagicMock(return_value=result)

    with patch('PySide6.QtWidgets.QApplication.processEvents') as mock_process_events:

        ctx = text.send('message')

        mock_window.controller.chat.files.upload.assert_called_once_with('chat')  # should upload files
        mock_window.core.history.append.assert_called_once()  # should append to history
        mock_window.controller.chat.render.append_input.assert_called_once()  # should append input
        mock_window.core.ctx.add.assert_called_once()  # should add ctx to DB
        mock_window.controller.ctx.update.assert_called_once_with(reload=True, all=False)  # should update ctx list
        mock_window.controller.chat.common.lock_input.assert_called_once()  # should lock input
        mock_window.core.gpt.call.assert_called_once()  # should call gpt
        mock_window.core.ctx.update_item.assert_called()  # should update ctx item
        mock_window.controller.chat.output.handle.assert_called_once()  # should handle output
        mock_window.controller.chat.output.handle_cmd.assert_called_once()  # should handle cmds
        mock_window.controller.chat.render.reload.assert_called_once()  # should not reload output (if not stream)
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
        mock_window.core.gpt.call.assert_called_once()  # should call gpt

        mock_window.core.ctx.update_item.assert_called()  # should update ctx item

        # if assistant
        mock_window.core.ctx.append_run.assert_called_once()  # should append run ID to ctx
        mock_window.controller.assistant.threads.handle_run.assert_called_once()  # should handle run

        mock_window.controller.chat.output.handle.assert_not_called()  # should NOT handle output (if assistant)
        mock_window.controller.chat.output.handle_cmd.assert_not_called()  # should NOT handle cmds (if assistant)

        mock_window.controller.chat.render.reload.assert_not_called()  # should not reload output (if not stream)
        mock_window.controller.chat.common.unlock_input.assert_called_once()  # should unlock input
        mock_window.controller.ctx.prepare_name.assert_called_once()  # should prepare name for ctx

        assert ctx.input_name == 'User'  # should have input name
        assert ctx.output_name == 'AI'  # should have output name
        assert ctx.input == 'message'  # should have input text
        assert ctx.thread == 'th_123'  # should have thread id


def test_log(mock_window):
    """Test log"""
    text = Text(mock_window)
    text.log('msg')
    mock_window.controller.debug.log.assert_called_once_with('msg', True)
