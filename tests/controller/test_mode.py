#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.03 12:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller import Mode
from pygpt_net.core.dispatcher import Event


def test_select(mock_window):
    """Test select mode"""
    mode = Mode(mock_window)

    mock_window.core.modes.get_by_idx = MagicMock(return_value='chat')

    event = Event('mode.select', {
        'value': 'chat',
    })
    mock_window.core.dispatcher.dispatch = MagicMock(return_value=(['test'], event))

    mode.change_locked = MagicMock()
    mode.change_locked.return_value = False

    mode.select(1)
    mock_window.core.dispatcher.dispatch.assert_called()  # must dispatch event: mode.select

    # must update rest of elements
    mock_window.controller.attachment.update.assert_called()
    mock_window.controller.ctx.update_ctx.assert_called_once()
    mock_window.controller.ui.update.assert_called_once()
    mock_window.ui.status.assert_called_once()

    assert mock_window.core.config.get('mode') == 'chat'
    assert mock_window.core.config.get('preset') == ''
    assert mock_window.core.config.get('model') == ''


def test_select_assistant(mock_window):
    """Test select mode"""
    mode = Mode(mock_window)

    mock_window.core.modes.get_by_idx = MagicMock(return_value='assistant')

    event = Event('mode.select', {
        'value': 'assistant',
    })
    mock_window.core.dispatcher.dispatch = MagicMock(return_value=(['test'], event))

    mode.change_locked = MagicMock()
    mode.change_locked.return_value = False

    # only if assistant is selected
    mock_window.core.ctx = MagicMock()
    mock_window.core.ctx.current = 1  # must have selected some context
    mock_window.core.ctx.assistant = 'test'

    mode.select(1)
    mock_window.core.dispatcher.dispatch.assert_called()  # must dispatch event: mode.select

    # must update rest of elements
    mock_window.controller.attachment.update.assert_called()
    mock_window.controller.ctx.update_ctx.assert_called_once()
    mock_window.controller.ui.update.assert_called_once()
    mock_window.ui.status.assert_called_once()

    mock_window.controller.assistant.select_by_id.assert_called_once_with('test')
    mock_window.controller.ctx.common.update_label_by_current.assert_called_once()

    assert mock_window.core.config.get('mode') == 'assistant'
    assert mock_window.core.config.get('preset') == ''
    assert mock_window.core.config.get('model') == ''


def test_select_current(mock_window):
    """Select current mode on the list"""
    mode = Mode(mock_window)
    mock_window.core.config.data['mode'] = 'chat'
    mock_window.ui.models['prompt.mode'].index = MagicMock()
    mock_window.ui.models['prompt.mode'].index.return_value = 0

    mode.select_current()
    mock_window.core.modes.get_idx_by_name.assert_called_once_with('chat')
    mock_window.ui.nodes['prompt.mode'].setCurrentIndex.assert_called_once_with(0)  # select idx = 0 on list


def test_select_default(mock_window):
    """Set default mode"""
    mock_window.core.config.data['mode'] = None
    mock_window.core.modes.get_default = MagicMock(return_value='chat')
    mode = Mode(mock_window)
    mode.select_default()
    assert mock_window.core.config.get('mode') == 'chat'


def test_default_all(mock_window):
    """Set default mode, model and preset"""
    mode = Mode(mock_window)
    mode.default_all()

    # must select default mode, model and preset
    mock_window.controller.model.select_default.assert_called_once()
    mock_window.controller.presets.select_default.assert_called_once()
    mock_window.controller.assistant.select_default.assert_called_once()


def test_update_list(mock_window):
    """Update modes list"""
    mode = Mode(mock_window)
    mock_window.core.modes.get_all = MagicMock(return_value=['test1', 'test2'])

    mode.update_list()
    mock_window.ui.toolbox.mode.update.assert_called_once_with(['test1', 'test2'])


def test_update_temperature(mock_window):
    """Update temperature"""
    mode = Mode(mock_window)
    mode.update_temperature(1.5)
    # mock_window.controller.config.slider.on_update.assert_called_once()


def test_update_mode(mock_window):
    """Update mode"""
    mock_window.core.config.data['mode'] = None
    mock_window.core.modes.get_default = MagicMock(return_value='chat')
    mode = Mode(mock_window)
    mode.update_mode()

    assert mock_window.core.config.get('mode') == 'chat'
    mock_window.ui.toolbox.mode.update.assert_called_once()
    mock_window.core.modes.get_idx_by_name.assert_called_once()


def test_reset_current(mock_window):
    """Reset current setup"""
    mode = Mode(mock_window)
    mode.reset_current()

    assert mock_window.core.config.get('prompt') is None
    assert mock_window.core.config.get('ai_name') is None
    assert mock_window.core.config.get('user_name') is None


def test_change_locked(mock_window):
    """Check if mode can be changed"""
    mode = Mode(mock_window)
    mock_window.controller.chat.input.generating = True
    assert mode.change_locked() is True

    mock_window.controller.chat.input.generating = False
    mock_window.controller.chat.input.generating = True

