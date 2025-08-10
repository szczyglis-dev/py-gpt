#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller import Layout


def test_setup(mock_window):
    """Test setup"""
    layout = Layout(mock_window)
    mock_window.controller.theme.setup = MagicMock()

    layout.setup()
    mock_window.controller.theme.setup.assert_called_once()


def test_post_setup(mock_window):
    """Test post setup"""
    layout = Layout(mock_window)
    layout.text_nodes_restore = MagicMock()
    layout.state_restore = MagicMock()
    layout.splitters_restore = MagicMock()
    layout.groups_restore = MagicMock()
    layout.scroll_restore = MagicMock()
    layout.window.controller.plugins.set_by_tab = MagicMock()
    layout.window.controller.ui.update_tokens = MagicMock()

    layout.post_setup()
    layout.text_nodes_restore.assert_called_once()
    layout.state_restore.assert_called_once()
    layout.splitters_restore.assert_called_once()
    layout.groups_restore.assert_called_once()
    layout.scroll_restore.assert_called_once()
    layout.window.controller.plugins.set_by_tab.assert_called_once()
    layout.window.controller.ui.update_tokens.assert_called_once()


def test_save(mock_window):
    """Test save"""
    layout = Layout(mock_window)
    layout.text_nodes_save = MagicMock()
    layout.splitters_save = MagicMock()
    layout.tabs_save = MagicMock()
    layout.groups_save = MagicMock()
    layout.scroll_save = MagicMock()
    layout.state_save = MagicMock()

    layout.save()
    layout.text_nodes_save.assert_called_once()
    layout.splitters_save.assert_called_once()
    layout.tabs_save.assert_called_once()
    layout.groups_save.assert_called_once()
    layout.scroll_save.assert_called_once()
    layout.state_save.assert_called_once()
