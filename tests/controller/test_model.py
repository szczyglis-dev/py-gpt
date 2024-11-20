#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.20 03:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller import Model
from pygpt_net.core.events import Event
from pygpt_net.item.model import ModelItem


def test_select(mock_window):
    """Test select model"""
    model = Model(mock_window)
    mock_window.core.config.data['mode'] = 'chat'
    mock_window.core.models.get_by_idx = MagicMock(return_value='gpt-4')
    event = Event('model.select', {
        'value': 'gpt-4',
    })
    mock_window.core.dispatcher.dispatch = MagicMock(return_value=(['test'], event))

    model.change_locked = MagicMock()
    model.change_locked.return_value = False

    model.select('gpt-4')  # idx on list
    mock_window.core.dispatcher.dispatch.assert_called()  # must dispatch event: model.select

    # must update rest of elements
    mock_window.controller.ui.update()

    assert mock_window.core.config.get('model') == 'gpt-4'
    assert mock_window.core.config.get('current_model') == {'chat': 'gpt-4'}


def test_set(mock_window):
    """Test set model"""
    model = Model(mock_window)
    model.set('chat', 'gpt-4')

    assert mock_window.core.config.get('model') == 'gpt-4'
    assert mock_window.core.config.get('current_model') == {'chat': 'gpt-4'}


def test_set_by_idx(mock_window):
    """Test select model"""
    model = Model(mock_window)
    mock_window.core.config.data['mode'] = 'chat'
    mock_window.core.models.get_by_idx = MagicMock(return_value='gpt-4')
    event = Event('model.select', {
        'value': 'gpt-4',
    })
    mock_window.core.dispatcher.dispatch = MagicMock(return_value=(['test'], event))

    model.change_locked = MagicMock()
    model.change_locked.return_value = False

    model.set_by_idx('chat', 0)  # idx on list
    mock_window.core.dispatcher.dispatch.assert_called_once()  # must dispatch event: model.select

    assert mock_window.core.config.get('model') == 'gpt-4'
    assert mock_window.core.config.get('current_model') == {'chat': 'gpt-4'}


def test_select_current(mock_window):
    """Select current mode on the list"""
    model = Model(mock_window)
    model.select_on_list = MagicMock()
    mock_window.core.config.data['mode'] = 'chat'
    mock_window.core.config.data['model'] = 'gpt-4'

    items = {
        'gpt-4': ModelItem(),
        'gpt-5': ModelItem(),
    }
    mock_window.core.models.get_by_mode = MagicMock(return_value=items)

    mock_window.ui.models['prompt.model'].index = MagicMock()
    mock_window.ui.models['prompt.model'].index.return_value = 0

    model.select_current()
    model.select_on_list.assert_called_once()


def test_select_default_from_current(mock_window):
    """Set default mode"""
    mock_window.core.config.data['model'] = None
    mock_window.core.config.data['mode'] = 'chat'
    current = {
        'chat': 'gpt-4',
    }
    mock_window.core.config.data['current_model'] = current
    items = {
        'gpt-4': ModelItem(),
        'gpt-5': ModelItem(),
    }
    mock_window.core.models.get_by_mode = MagicMock(return_value=items)

    # mock_window.core.modes.get_default = MagicMock(return_value='chat')  # not used here
    model = Model(mock_window)
    model.select_default()
    assert mock_window.core.config.get('model') == 'gpt-4'


def test_select_default_from_default(mock_window):
    """Set default mode"""
    mock_window.core.config.data['model'] = None
    mock_window.core.config.data['mode'] = 'chat'
    mock_window.core.config.data['current_model'] = {}  # no current model
    items = {
        'gpt-8': ModelItem(),
    }
    mock_window.core.models.get_by_mode = MagicMock(items)  # will return empty list
    mock_window.core.models.get_default = MagicMock(return_value='gpt-4')  # this will be used
    model = Model(mock_window)
    model.select_default()
    assert mock_window.core.config.get('model') == 'gpt-4'


def test_update(mock_window):
    """Update models list"""
    model = Model(mock_window)
    model.select_current = MagicMock()
    mock_window.core.config.data['model'] = None
    mock_window.core.config.data['mode'] = 'chat'
    current = {
        'chat': 'gpt-4',
    }
    mock_window.core.config.data['current_model'] = current
    items = {
        'gpt-4': ModelItem(),
        'gpt-5': ModelItem(),
    }
    mock_window.core.models.get_by_mode = MagicMock(return_value=items)
    model.update()
    model.select_current.assert_called_once()


def test_change_locked(mock_window):
    """Check if mode can be changed"""
    model = Model(mock_window)
    mock_window.controller.chat.input.generating = True
    assert model.change_locked() is True

    mock_window.controller.chat.input.generating = False
    mock_window.controller.chat.input.generating = True
