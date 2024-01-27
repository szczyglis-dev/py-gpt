#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 11:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller import Theme


def test_apply(mock_window):
    """Test apply"""
    theme = Theme(mock_window)
    mock_window.ui.nodes = {'test': MagicMock()}
    mock_window.ui.nodes['test'].setStyleSheet = MagicMock()
    mock_window.controller.theme.style = MagicMock(return_value='test')
    theme.nodes.apply('test', 'font.toolbox')
    mock_window.ui.nodes['test'].setStyleSheet.assert_called_with('test')
    mock_window.controller.theme.style.assert_called_with('toolbox')


def test_apply_all(mock_window):
    """Test apply all"""
    theme = Theme(mock_window)
    theme.nodes.apply_all = MagicMock()
    mock_window.controller.notepad.get_num_notepads = MagicMock(return_value=1)
    theme.nodes.apply_all()
    theme.nodes.apply_all.assert_called()
