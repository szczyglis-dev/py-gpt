#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 19:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, call

from tests.mocks import mock_window
from pygpt_net.controller import UI


def test_setup(mock_window):
    """Test setup"""
    ui = UI(mock_window)

    ui.update_font_size = MagicMock()
    ui.update = MagicMock()

    ui.setup()

    ui.update_font_size.assert_called_once()
    ui.update.assert_called_once()


def test_update(mock_window):
    """Test update"""
    ui = UI(mock_window)

    ui.update_toolbox = MagicMock()
    ui.update_chat_label = MagicMock()
    ui.mode.update = MagicMock()
    ui.update_tokens = MagicMock()

    ui.update()

    ui.update_toolbox.assert_called_once()
    ui.update_chat_label.assert_called_once()
    ui.mode.update.assert_called_once()
    ui.update_tokens.assert_called_once()


def test_update_font_size(mock_window):
    """Test update font size"""
    ui = UI(mock_window)
    mock_window.controller.theme.nodes.apply_all = MagicMock()
    ui.update_font_size()
    mock_window.controller.theme.nodes.apply_all.assert_called_once_with(False)


def test_update_toolbox(mock_window):
    """Test update toolbox"""
    ui = UI(mock_window)
    mock_window.controller.mode.update_mode = MagicMock()
    mock_window.controller.model.update = MagicMock()
    mock_window.controller.presets.refresh = MagicMock()
    mock_window.controller.assistant.refresh = MagicMock()
    ui.update_toolbox()
    mock_window.controller.mode.update_mode.assert_called_once()
    mock_window.controller.model.update.assert_called_once()
    mock_window.controller.presets.refresh.assert_called_once()
    mock_window.controller.assistant.refresh.assert_called_once()


def test_update_tokens(mock_window):
    mock_window.ui.nodes['input.counter'] = MagicMock()
    mock_window.core.tokens.get_current = MagicMock(return_value=(133, 222, 35, 41, 53, 66, 71, 822, 91))
    ui = UI(mock_window)
    ui.update_tokens()
    mock_window.core.config.set("lang", "en")
    mock_window.ui.nodes['input.counter'].setText.assert_has_calls([
        call('53 / 66 - 41 tokens'),
        call('133 + 222 + 41 + 35 = 71 / 822')
    ])  # must have EN lang in config to pass!!!!!!!!


def test_store_state(mock_window):
    """Test store state"""
    ui = UI(mock_window)
    mock_window.controller.layout.scroll_save = MagicMock()
    ui.store_state()
    mock_window.controller.layout.scroll_save.assert_called()


def test_restore_state(mock_window):
    """Test restore state"""
    ui = UI(mock_window)
    mock_window.controller.layout.scroll_restore = MagicMock()
    ui.restore_state()
    mock_window.controller.layout.scroll_restore.assert_called()


def test_update_chat_label(mock_window):
    """Test update chat label"""
    ui = UI(mock_window)
    mock_window.core.config.data['mode'] = 'test_mode'
    mock_window.core.config.data['model'] = 'test_model'
    mock_window.ui.nodes['chat.model'].setText = MagicMock()
    ui.update_chat_label()
    mock_window.ui.nodes['chat.model'].setText.assert_called_with('test_model')


def test_update_ctx_label_allowed(mock_window):
    """Test update ctx label: allowed"""
    ui = UI(mock_window)
    mock_window.core.ctx.is_allowed_for_mode = MagicMock(return_value=True)
    mock_window.ui.nodes['chat.label'].setText = MagicMock()
    ui.update_ctx_label()
    mock_window.ui.nodes['chat.label'].setText.assert_called_with(' (+)')


def test_update_ctx_label_not_allowed(mock_window):
    """Test update ctx label: not allowed"""
    ui = UI(mock_window)
    mock_window.core.ctx.is_allowed_for_mode = MagicMock(return_value=False)
    mock_window.ui.nodes['chat.label'].setText = MagicMock()
    ui.update_ctx_label()
    mock_window.ui.nodes['chat.label'].setText.assert_called_with('')
