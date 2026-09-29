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

import os
from unittest.mock import MagicMock, patch, mock_open

from tests.mocks import mock_window
from pygpt_net.controller import Theme


def test_setup(mock_window):
    """Test setup"""
    theme = Theme(mock_window)
    theme.markdown = MagicMock()
    theme.common = MagicMock()
    theme.menu = MagicMock()

    theme.markdown.load = MagicMock()
    theme.common.get_themes_list = MagicMock(return_value=[])
    theme.reload = MagicMock()
    theme.setup()
    theme.markdown.load.assert_called_once()
    theme.reload.assert_called_once()


def test_toggle(mock_window):
    """Test toggle"""
    theme = Theme(mock_window)
    theme.window.controller.ui.store_state = MagicMock()
    theme.window.controller.ui.restore_state = MagicMock()
    theme.window.core.config.set = MagicMock()
    theme.window.core.config.save = MagicMock()
    theme.common.normalize_theme = MagicMock(return_value='test')
    theme.nodes.apply_all = MagicMock()
    theme.apply = MagicMock()
    theme.markdown.update = MagicMock()
    theme.menu.setup_list = MagicMock()
    theme.menu.update_list = MagicMock()
    theme.menu.update_density = MagicMock()
    theme.menu.update_syntax = MagicMock()
    theme._get_material_signature = MagicMock(return_value=('material',))
    theme._get_markdown_signature = MagicMock(return_value=('markdown',))
    theme._remember_state = MagicMock()

    theme.toggle('test')

    theme.window.controller.ui.store_state.assert_called_once_with()
    theme.window.core.config.set.assert_called_once_with('theme', 'test')
    theme.window.core.config.save.assert_called_once_with()
    theme.apply.assert_called_once_with('test')
    theme.nodes.apply_all.assert_called_once_with(dispatch_theme=False)
    theme.markdown.update.assert_called_once_with(force=False)
    theme.menu.setup_list.assert_called_once_with()
    theme.menu.update_list.assert_called_once_with()
    theme.menu.update_density.assert_called_once_with()
    theme.menu.update_syntax.assert_called_once_with()
    theme.window.controller.ui.restore_state.assert_called_once_with()


def test_reload(mock_window):
    """Test reload"""
    theme = Theme(mock_window)
    theme.toggle = MagicMock()
    theme.reload(force=True)
    theme.toggle.assert_called()


def test_apply(mock_window):
    """Test apply window"""
    mock_window.core.config.data['theme'] = 'light'
    theme = Theme(mock_window)
    mock_window.apply_stylesheet = MagicMock()
    theme.apply()
    mock_window.apply_stylesheet.assert_called()


def test_style(mock_window):
    """Test get style"""
    theme = Theme(mock_window)
    mock_window.core.config.data['theme'] = 'test'
    mock_window.core.config.data['font_size'] = 12
    mock_window.core.config.data['font_size.input'] = 12
    mock_window.core.config.data['font_size.ctx'] = 12
    mock_window.core.config.data['font_size.toolbox'] = 12
    assert theme.style('font.chat.output') == 'QTextEdit { font-size: 12px; }'
    assert theme.style('font.chat.input') == 'QTextEdit { font-size: 12px; }'
    assert theme.style('font.ctx.list') == 'font-size: 12px;'
    assert theme.style('font.toolbox') == 'font-size: 12px;'
