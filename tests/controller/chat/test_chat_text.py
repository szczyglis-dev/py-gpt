#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.21 02:00:00                  #
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
    mock_window.core.openai.call = MagicMock(return_value=result)
    #mock_window.core.chain.call = MagicMock(return_value=result)
    mock_window.controller.plugins.is_type_enabled = MagicMock(return_value=False)
    mock_window.controller.agent.enabled = MagicMock(return_value=False)
    mock_window.controller.agent.experts.enabled = MagicMock(return_value=False)

    model = ModelItem()
    mock_window.core.models.get = MagicMock(return_value=model)
    mock_window.core.prompt.prepare_sys_prompt = MagicMock()

    with patch('PySide6.QtWidgets.QApplication.processEvents') as mock_process_events:

        ctx = text.send('message')

        mock_window.core.prompt.prepare_sys_prompt.assert_called_once()  # should append cmd syntax

        mock_window.core.ctx.add.assert_called_once()  # should add ctx to DB
        mock_window.controller.ctx.update.assert_called_once_with(reload=True, all=False)  # should update ctx list
        mock_window.controller.chat.common.lock_input.assert_called_once()  # should lock input
        mock_window.dispatch.assert_called()


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
    mock_window.core.openai.call = MagicMock(return_value=result)
    #mock_window.core.chain.call = MagicMock(return_value=result)
    mock_window.controller.plugins.is_type_enabled = MagicMock(return_value=False)
    mock_window.controller.agent.enabled = MagicMock(return_value=False)

    with patch('PySide6.QtWidgets.QApplication.processEvents') as mock_process_events:

        ctx = text.send('message')

        mock_window.core.ctx.add.assert_called_once()  # should add ctx to DB
        mock_window.controller.ctx.update.assert_called_once_with(reload=True, all=False)  # should update ctx list
        mock_window.controller.chat.common.lock_input.assert_called_once()  # should lock input
        mock_window.dispatch.assert_called()


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
    mock_window.core.openai.call = MagicMock(return_value=result)
    #mock_window.core.chain.call = MagicMock(return_value=result)

    with patch('PySide6.QtWidgets.QApplication.processEvents') as mock_process_events:

        ctx = text.send('message')

        mock_window.controller.assistant.begin.assert_called_once()  # should upload files
        mock_window.core.ctx.add.assert_called_once()  # should add ctx to DB
        mock_window.controller.ctx.update.assert_called_once_with(reload=True, all=False)  # should update ctx list
        mock_window.controller.chat.common.lock_input.assert_called_once()  # should lock input
        mock_window.dispatch.assert_called()
