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
    theme.markdown = MagicMock()
    theme.common = MagicMock()
    theme.menu = MagicMock()

    theme.markdown.load = MagicMock()
    theme.common.get_themes_list = MagicMock(return_value=[])
    theme.reload = MagicMock()
    theme.setup()
    theme.markdown.load.assert_called_once()
    theme.reload.assert_called_once()


def test_update_menu(mock_window):
    """Test update menu"""
    theme = Theme(mock_window)
    mock_window.core.config.data['theme'] = 'test'
    mock_window.ui.menu = {'theme': {'test': MagicMock()}}
    theme.menu.update_list()
    theme.window.ui.menu['theme']['test'].setChecked.assert_called()


def test_toggle(mock_window):
    """Test toggle"""
    theme = Theme(mock_window)
    theme.window.controller.ui.store_state = MagicMock()
    theme.window.controller.ui.restore_state = MagicMock()
    theme.window.core.config.set = MagicMock()
    theme.window.core.config.save = MagicMock()
    theme.nodes.apply_all = MagicMock()
    theme.apply = MagicMock()
    theme.markdown.update = MagicMock()
    theme.menu.update_list = MagicMock()
    theme.toggle('test')
    theme.window.controller.ui.store_state.assert_called()
    theme.window.core.config.set.assert_called()
    theme.window.core.config.save.assert_called()
    theme.nodes.apply_all.assert_called()
    theme.apply.assert_called()
    theme.markdown.update.assert_called()
    theme.menu.update_list.assert_called()
    theme.window.controller.ui.restore_state.assert_called()


def test_update_markdown(mock_window):
    """Test update markdown"""
    theme = Theme(mock_window)
    theme.window.controller.ui.store_state = MagicMock()
    theme.window.controller.ui.restore_state = MagicMock()
    theme.window.core.config.get = MagicMock(return_value=True)
    theme.markdown.load = MagicMock()
    theme.markdown.set_default = MagicMock()
    theme.markdown.apply = MagicMock()
    theme.markdown.update(force=True)
    theme.window.controller.ui.store_state.assert_called()
    theme.window.core.config.get.assert_called()
    theme.markdown.load.assert_called()
    theme.markdown.set_default.assert_not_called()
    theme.markdown.apply.assert_called()
    theme.window.controller.ui.restore_state.assert_called()


def test_reload(mock_window):
    """Test reload"""
    theme = Theme(mock_window)
    theme.toggle = MagicMock()
    theme.reload(force=True)
    theme.toggle.assert_called()


def test_apply_node(mock_window):
    """Test apply node"""
    theme = Theme(mock_window)
    mock_window.ui.nodes = {'test': MagicMock()}
    mock_window.ui.nodes['test'].setStyleSheet = MagicMock()
    mock_window.controller.theme.style = MagicMock(return_value='test')
    theme.nodes.apply('test', 'toolbox')
    mock_window.ui.nodes['test'].setStyleSheet.assert_called_with('test')
    mock_window.controller.theme.style.assert_called_with('toolbox')


def test_apply_nodes(mock_window):
    """Test apply nodes"""
    theme = Theme(mock_window)
    theme.nodes.apply_all = MagicMock()
    mock_window.controller.notepad.get_num_notepads = MagicMock(return_value=1)
    theme.nodes.apply_all()
    theme.nodes.apply_all.assert_called()


def teststyle(mock_window):
    """Test get style"""
    theme = Theme(mock_window)
    mock_window.core.config.data['theme'] = 'test'
    mock_window.core.config.data['font_size'] = 12
    mock_window.core.config.data['font_size.input'] = 12
    mock_window.core.config.data['font_size.ctx'] = 12
    mock_window.core.config.data['font_size.toolbox'] = 12
    assert theme.style('chat_output') == 'font-size: 12px;'
    assert theme.style('chat_input') == 'font-size: 12px;'
    assert theme.style('ctx.list') == 'font-size: 12px;'
    assert theme.style('toolbox') == 'font-size: 12px;'
    assert theme.style('text_bold') == 'font-weight: bold;'
    assert theme.style('text_small') == ''
    assert theme.style('text_faded') == 'color: #999;'
    mock_window.core.config.data['theme'] = 'light'
    assert theme.style('text_faded') == 'color: #414141;'
    mock_window.core.config.data['theme'] = 'dark'
    assert theme.style('text_faded') == 'color: #999;'


def test_get_default_markdown(mock_window):
    """Test get default markdown"""
    mock_window.core.config.data['theme'] = 'light'
    theme = Theme(mock_window)
    assert theme.markdown.get_default() is not None


def test_set_default_markdown(mock_window):
    """Test set default markdown"""
    mock_window.core.config.data['theme'] = 'light'
    theme = Theme(mock_window)
    theme.markdown.css['markdown'] = {}
    theme.markdown.set_default()
    assert theme.markdown.css['markdown'] is not None


def test_apply_markdown(mock_window):
    """Test apply markdown"""
    mock_window.core.config.data['theme'] = 'light'
    theme = Theme(mock_window)
    mock_window.ui.nodes = {'output': MagicMock()}
    mock_window.controller.chat.render.reload()
    mock_window.ui.nodes['output'].document().setDefaultStyleSheet = MagicMock()
    mock_window.ui.nodes['output'].document().setMarkdown = MagicMock()
    theme.markdown.css['markdown'] = {}
    theme.markdown.apply()
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
            theme.markdown.load()
            mock_file.assert_called_with('test', 'r')
            assert theme.markdown.css['markdown'] is not None


def test_apply(mock_window):
    """Test apply window"""
    mock_window.core.config.data['theme'] = 'light'
    theme = Theme(mock_window)
    mock_window.apply_stylesheet = MagicMock()
    theme.apply()
    mock_window.apply_stylesheet.assert_called()


def test_get_extra_css(mock_window):
    """Test get extra css"""
    mock_window.core.config.data['theme'] = 'dark_teal'
    theme = Theme(mock_window)
    with patch('os.path.exists') as os_path_exists, \
        patch('os.path.join') as os_path_join:
        os_path_exists.return_value=True
        os_path_join.return_value='test'
        assert theme.common.get_extra_css('dark_teal') == 'style.dark.css'


def test_translate(mock_window):
    name = 'dark_teal'
    theme = Theme(mock_window)
    mock_window.core.config.data['lang'] = 'en'
    assert theme.common.translate(name) == 'Dark: Teal'  # must have EN lang in config to pass!!!!!!!!


def test_get_themes_list(mock_window):
    theme = Theme(mock_window)
    assert type(theme.common.get_themes_list()) == list
