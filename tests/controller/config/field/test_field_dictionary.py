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

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.config.field.dictionary import Dictionary


def test_apply(mock_window):
    """Test apply"""
    field = Dictionary(mock_window)
    widget = MagicMock()
    widget.items = []
    widget.model.updateData = MagicMock()
    mock_window.ui.config = {
        'parent_id': {
            'key': widget
        }
    }
    option = {
        "type": "dict",
        "value": [],
    }
    field.apply('parent_id', 'key', option)
    mock_window.ui.config['parent_id']['key'].model.updateData.assert_called_once()


def test_apply_row(mock_window):
    """Test on update"""
    field = Dictionary(mock_window)
    widget = MagicMock()
    widget.items = []
    widget.update_item = MagicMock()
    mock_window.ui.config = {
        'parent_id': {
            'key': widget
        }
    }
    values = {
        "key": "value"
    }
    field.apply_row('parent_id', 'key', values, 2)
    mock_window.ui.config['parent_id']['key'].update_item.assert_called_once_with(2, values)


def test_get_value(mock_window):
    """Test get value"""
    field = Dictionary(mock_window)
    values = [{
        "key": "value"
    }]
    option = {
        "type": "dict",
        "value": values,
    }
    widget = MagicMock()
    widget.model.items = values
    mock_window.ui.config = {
        'parent_id': {
            'key': widget
        }
    }
    value = field.get_value('parent_id', 'key', option)
    assert value == values


def test_delete_item(mock_window):
    """Test delete item"""
    field = Dictionary(mock_window)
    parent = MagicMock()
    parent.delete_item_execute = MagicMock()
    field.delete_item(parent, 'id', True, False)
    parent.delete_item_execute.assert_called_once_with('id')


def test_to_options(mock_window):
    """Test to options"""
    field = Dictionary(mock_window)
    values = [
        {
            "key": "value"
        }
    ]
    option = {
        "type": "dict",
        "keys": {"key": "text"},
        "value": values,
    }
    options = field.to_options("parent_id", option)
    assert options == {'key': {'label': 'parent_id.key', 'type': 'text'}}


def test_append_editor(mock_window):
    """Test append editor"""
    field = Dictionary(mock_window)
    values = [
        {
            "key": "value"
        }
    ]
    option = {
        "type": "dict",
        "keys": {"key": "text"},
        "value": values,
    }
    mock_window.controller.config.apply = MagicMock()
    field.append_editor('id', option, {'key': 'value'})
    mock_window.controller.config.apply.assert_called_once_with('dictionary.id',
                                                                'key',
                                                                {'label': 'id.key', 'type': 'text', 'value': 'value'})


def test_save_editor(mock_window):
    """Test save editor"""
    field = Dictionary(mock_window)
    mock_window.controller.config.apply_row = MagicMock()
    mock_window.controller.config.get_value = MagicMock()
    mock_window.controller.config.get_value.return_value = 'value'
    field.apply_row = MagicMock()
    editor = MagicMock()
    editor.idx = 0
    mock_window.ui.dialog = {
        'editor.dictionary.parent_id.id': editor
    }
    fields = {
        'key': 'value'
    }
    values = {
        'key': 'value'
    }
    field.save_editor('id', 'parent_id', fields, False)
    field.apply_row.assert_called_once_with('parent_id', 'id', values, 0)