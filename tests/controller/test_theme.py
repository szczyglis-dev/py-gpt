#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.03 16:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch, mock_open

from tests.mocks import mock_window
from pygpt_net.controller import Theme


def test_setup(mock_window):
    """Test setup"""
    theme = Theme(mock_window)
    theme.load_markdown = MagicMock()
    theme.get_themes_list = MagicMock(return_value=[])
    theme.reload = MagicMock()
    theme.setup()
    theme.load_markdown.assert_called_once()
    theme.reload.assert_called_once()


def test_update_menu(mock_window):
    """Test update menu"""
    theme = Theme(mock_window)
    mock_window.core.config.data['theme'] = 'test'
    mock_window.ui.menu = {'theme': {'test': MagicMock()}}
    theme.update_menu()
    theme.window.ui.menu['theme']['test'].setChecked.assert_called()


def test_toggle(mock_window):
    """Test toggle"""
    theme = Theme(mock_window)
    theme.window.controller.ui.store_state = MagicMock()
    theme.window.controller.ui.restore_state = MagicMock()
    theme.window.core.config.set = MagicMock()
    theme.window.core.config.save = MagicMock()
    theme.apply_nodes = MagicMock()
    theme.apply_window = MagicMock()
    theme.update_markdown = MagicMock()
    theme.update_menu = MagicMock()
    theme.toggle('test')
    theme.window.controller.ui.store_state.assert_called()
    theme.window.core.config.set.assert_called()
    theme.window.core.config.save.assert_called()
    theme.apply_nodes.assert_called()
    theme.apply_window.assert_called()
    theme.update_markdown.assert_called()
    theme.update_menu.assert_called()
    theme.window.controller.ui.restore_state.assert_called()


def test_update_markdown(mock_window):
    """Test update markdown"""
    theme = Theme(mock_window)
    theme.window.controller.ui.store_state = MagicMock()
    theme.window.controller.ui.restore_state = MagicMock()
    theme.window.core.config.get = MagicMock(return_value=True)
    theme.load_markdown = MagicMock()
    theme.set_default_markdown = MagicMock()
    theme.apply_markdown = MagicMock()
    theme.update_markdown(force=True)
    theme.window.controller.ui.store_state.assert_called()
    theme.window.core.config.get.assert_called()
    theme.load_markdown.assert_called()
    theme.set_default_markdown.assert_not_called()
    theme.apply_markdown.assert_called()
    theme.window.controller.ui.restore_state.assert_called()


def test_reload(mock_window):
    """Test reload"""
    theme = Theme(mock_window)
    theme.toggle = MagicMock()
    theme.reload(force=True)
    theme.toggle.assert_called()


def test_get_css(mock_window):
    """Test get CSS"""
    theme = Theme(mock_window)
    theme.css = {'test': {'test': 'test'}}
    assert theme.get_css('test') == {'test': 'test'}
    assert theme.get_css('test2') == {}


def test_apply_node(mock_window):
    """Test apply node"""
    theme = Theme(mock_window)
    mock_window.ui.nodes = {'test': MagicMock()}
    mock_window.ui.nodes['test'].setStyleSheet = MagicMock()
    theme.get_style = MagicMock(return_value='test')
    theme.apply_node('test', 'toolbox')
    mock_window.ui.nodes['test'].setStyleSheet.assert_called_with('test')
    theme.get_style.assert_called_with('toolbox')


def test_apply_nodes(mock_window):
    """Test apply nodes"""
    theme = Theme(mock_window)
    theme.apply_node = MagicMock()
    mock_window.controller.notepad.get_num_notepads = MagicMock(return_value=1)
    theme.apply_nodes()
    theme.apply_node.assert_called()


def test_get_style(mock_window):
    """Test get style"""
    theme = Theme(mock_window)
    mock_window.core.config.data['theme'] = 'test'
    mock_window.core.config.data['font_size'] = 12
    mock_window.core.config.data['font_size.input'] = 12
    mock_window.core.config.data['font_size.ctx'] = 12
    mock_window.core.config.data['font_size.toolbox'] = 12
    assert theme.get_style('chat_output') == 'font-size: 12px;'
    assert theme.get_style('chat_input') == 'font-size: 12px;'
    assert theme.get_style('ctx.list') == 'font-size: 12px;'
    assert theme.get_style('toolbox') == 'font-size: 12px;'
    assert theme.get_style('text_bold') == 'font-weight: bold;'
    assert theme.get_style('text_small') == ''
    assert theme.get_style('text_faded') == 'color: #999;'
    mock_window.core.config.data['theme'] = 'light'
    assert theme.get_style('text_faded') == 'color: #414141;'
    mock_window.core.config.data['theme'] = 'dark'
    assert theme.get_style('text_faded') == 'color: #999;'


def test_get_default_markdown(mock_window):
    """Test get default markdown"""
    mock_window.core.config.data['theme'] = 'light'
    theme = Theme(mock_window)
    assert theme.get_default_markdown() is not None


def test_set_default_markdown(mock_window):
    """Test set default markdown"""
    mock_window.core.config.data['theme'] = 'light'
    theme = Theme(mock_window)
    theme.css['markdown'] = {}
    theme.set_default_markdown()
    assert theme.css['markdown'] is not None


def test_apply_markdown(mock_window):
    """Test apply markdown"""
    mock_window.core.config.data['theme'] = 'light'
    theme = Theme(mock_window)
    mock_window.ui.nodes = {'output': MagicMock()}
    mock_window.controller.chat.render.reload()
    mock_window.ui.nodes['output'].document().setDefaultStyleSheet = MagicMock()
    mock_window.ui.nodes['output'].document().setMarkdown = MagicMock()
    theme.css['markdown'] = {}
    theme.apply_markdown()
    mock_window.ui.nodes['output'].document().setDefaultStyleSheet.assert_called()
    mock_window.ui.nodes['output'].document().setMarkdown.assert_called()
    mock_window.controller.chat.render.reload.assert_called()


def test_load_markdown(mock_window):
    """Test load markdown"""
    mock_window.core.config.data['theme'] = 'light'
    with patch('os.path.exists') as os_path_exists, \
        patch('os.path.join') as os_path_join:
        os_path_exists.return_value=True
        os_path_join.return_value='test'
        theme = Theme(mock_window)

        with patch('builtins.open', mock_open(read_data='test')) as mock_file:
            theme.load_markdown()
            mock_file.assert_called_with('test', 'r')
            assert theme.css['markdown'] is not None


def test_apply_window(mock_window):
    """Test apply window"""
    mock_window.core.config.data['theme'] = 'light'
    theme = Theme(mock_window)
    mock_window.apply_stylesheet = MagicMock()
    theme.apply_window()
    mock_window.apply_stylesheet.assert_called()


def test_get_custom_css(mock_window):
    """Test get custom css"""
    mock_window.core.config.data['theme'] = 'dark_teal'
    theme = Theme(mock_window)
    with patch('os.path.exists') as os_path_exists, \
        patch('os.path.join') as os_path_join:
        os_path_exists.return_value=True
        os_path_join.return_value='test'
        assert theme.get_custom_css('dark_teal') == 'style.dark.css'


def test_trans_theme(mock_window):
    name = 'dark_teal'
    theme = Theme(mock_window)
    assert theme.trans_theme(name) == 'Dark: Teal'


def test_get_themes_list(mock_window):
    theme = Theme(mock_window)
    assert type(theme.get_themes_list()) == list
