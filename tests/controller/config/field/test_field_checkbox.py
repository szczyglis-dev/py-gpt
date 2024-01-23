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
from pygpt_net.controller.config.field.checkbox import Checkbox


def test_apply(mock_window):
    """Test apply"""

    field = Checkbox(mock_window)
    mock_window.ui.config = {
        "parent_id": {
            "key": MagicMock()
        }
    }
    field.apply('parent_id', 'key', {'value': True})
    mock_window.ui.config['parent_id']['key'].box.setChecked.assert_called_once_with(True)


def test_on_update(mock_window):
    """Test on update"""
    field = Checkbox(mock_window)
    mock_window.ui.has_hook = MagicMock(return_value=True)
    mock_window.ui.get_hook = MagicMock()
    field.on_update('parent_id', 'key', {'value': True}, True)
    mock_window.ui.get_hook.assert_called_once_with('update.parent_id.key')


def test_get_value(mock_window):
    """Test get value"""
    field = Checkbox(mock_window)
    option = {
        "type": "bool",
        "value": True
    }
    mock_window.ui.config = {
        "parent_id": {
            "key": MagicMock()
        }
    }
    field.get_value('parent_id', 'key', option)
    mock_window.ui.config['parent_id']['key'].box.isChecked.assert_called_once()
