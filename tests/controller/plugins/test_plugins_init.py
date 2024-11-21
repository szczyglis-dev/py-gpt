#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.21 02:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.base.plugin import BasePlugin
from tests.mocks import mock_window
from pygpt_net.controller import Plugins


def test_setup(mock_window):
    """Test setup plugins"""
    plugins = Plugins(mock_window)
    plugins.setup_menu = MagicMock()
    plugins.setup_ui = MagicMock()
    plugins.setup_config = MagicMock()
    plugins.update = MagicMock()

    plugins.setup()

    plugins.setup_menu.assert_called_once()
    plugins.setup_ui.assert_called_once()
    plugins.setup_config.assert_called_once()
    plugins.update.assert_called_once()


def test_setup_ui(mock_window):
    """Test setup plugins UI"""
    plugin = BasePlugin()
    plugin.setup_ui = MagicMock()

    plugins = Plugins(mock_window)
    plugins.window.core.plugins.get_ids = MagicMock(return_value=['test'])
    plugins.window.core.plugins.get = MagicMock(return_value=plugin)
    plugins.handle_types = MagicMock()

    plugins.setup_ui()

    plugins.window.core.plugins.get_ids.assert_called_once()
    plugins.window.core.plugins.get.assert_called_once_with('test')
    plugins.handle_types.assert_called_once()
    plugin.setup_ui.assert_called_once()


def setup_menu(mock_window):
    """Test setup plugins menu"""
    plugin = BasePlugin()
    plugin.setup_ui = MagicMock()
    plugins = Plugins(mock_window)
    mock_window.core.plugins.get_ids = MagicMock(return_value=['test'])
    mock_window.core.plugins.get = MagicMock(return_value=plugin)
    plugins.setup_menu()
    mock_window.core.plugins.get_ids.assert_called_once()
    mock_window.core.plugins.get.assert_called()


def test_setup_config(mock_window):
    """Test setup plugins config"""
    plugins = Plugins(mock_window)
    mock_window.core.plugins = MagicMock()
    mock_window.core.plugins.get_ids = MagicMock(return_value=['test'])
    mock_window.core.config.data['plugins_enabled'] = {'test': True}
    plugins.enable = MagicMock()
    plugins.setup_config()
    plugins.enable.assert_called_once_with('test')


def test_update(mock_window):
    """Test update plugins"""
    plugins = Plugins(mock_window)
    mock_window.ui.menu['plugins'] = {'test': MagicMock()}
    mock_window.controller.ui.mode.update = MagicMock()
    mock_window.controller.ui.vision.update = MagicMock()
    plugins.enabled = {'test': True}
    plugins.update()
    mock_window.ui.menu['plugins']['test'].setChecked.assert_called_once_with(True)
    mock_window.controller.ui.mode.update.assert_called_once()
    mock_window.controller.ui.vision.update.assert_called_once()


def test_enable(mock_window):
    """Test enable plugin"""
    plugins = Plugins(mock_window)
    mock_window.core.plugins.is_registered = MagicMock(return_value=True)
    mock_window.core.plugins.enable = MagicMock()
    mock_window.dispatch = MagicMock()
    mock_window.controller.audio.update = MagicMock()
    plugins.has_type = MagicMock(return_value=True)
    plugins.update_info = MagicMock()
    plugins.update = MagicMock()
    plugins.enable('test')
    mock_window.core.plugins.is_registered.assert_called_once_with('test')
    mock_window.core.plugins.enable.assert_called_once_with('test')
    mock_window.dispatch.assert_called_once()
    mock_window.controller.audio.update.assert_called_once()
    plugins.update_info.assert_called_once()
    plugins.update.assert_called_once()


def test_disable(mock_window):
    """Test disable plugin"""
    plugins = Plugins(mock_window)
    mock_window.core.plugins.is_registered = MagicMock(return_value=True)
    mock_window.core.plugins.disable = MagicMock()
    mock_window.dispatch = MagicMock()
    mock_window.controller.audio.update = MagicMock()
    plugins.has_type = MagicMock(return_value=True)
    plugins.update_info = MagicMock()
    plugins.update = MagicMock()
    plugins.disable('test')
    mock_window.core.plugins.is_registered.assert_called_once_with('test')
    mock_window.core.plugins.disable.assert_called_once_with('test')
    mock_window.dispatch.assert_called_once()
    mock_window.controller.audio.update.assert_called_once()
    plugins.update_info.assert_called_once()
    plugins.update.assert_called_once()


def test_is_enabled(mock_window):
    """Test is enabled plugin"""
    plugins = Plugins(mock_window)
    mock_window.core.plugins.is_registered = MagicMock(return_value=True)
    plugins.enabled = {'test': True}
    plugins.is_enabled('test')
    mock_window.core.plugins.is_registered.assert_called_once_with('test')


def test_toggle(mock_window):
    """Test toggle plugin"""
    plugins = Plugins(mock_window)
    mock_window.core.plugins.is_registered = MagicMock(return_value=True)
    plugins.is_enabled = MagicMock(return_value=True)
    plugins.disable = MagicMock()
    plugins.handle_types = MagicMock()
    mock_window.controller.ui.update_tokens = MagicMock()
    mock_window.controller.ui.mode.update = MagicMock()
    mock_window.controller.ui.vision.update = MagicMock()
    mock_window.controller.attachment.update = MagicMock()
    plugins.toggle('test')
    mock_window.core.plugins.is_registered.assert_called_once_with('test')
    plugins.is_enabled.assert_called_once_with('test')
    plugins.disable.assert_called_once_with('test')
    plugins.handle_types.assert_called_once()
    mock_window.controller.ui.update_tokens.assert_called_once()
    mock_window.controller.ui.mode.update.assert_called_once()
    mock_window.controller.ui.vision.update.assert_called_once()
    mock_window.controller.attachment.update.assert_called_once()


def test_set_by_tab(mock_window):
    """Test set current plugin by tab index"""
    plugins = Plugins(mock_window)
    mock_window.core.plugins.get_ids = MagicMock(return_value=['test'])
    mock_window.core.plugins.has_options = MagicMock(return_value=True)
    mock_window.ui.models['plugin.list'] = MagicMock()
    mock_window.ui.nodes['plugin.list'] = MagicMock()
    plugins.settings.current_plugin = 'test'
    plugins.set_by_tab(0)
    mock_window.core.plugins.get_ids.assert_called_once()
    mock_window.core.plugins.has_options.assert_called_once_with('test')
    mock_window.ui.models['plugin.list'].index.assert_called_once_with(0, 0)
    mock_window.ui.nodes['plugin.list'].setCurrentIndex.assert_called_once()


def test_get_tab_idx(mock_window):
    """Test get plugin tab index"""
    plugins = Plugins(mock_window)
    mock_window.core.plugins.get_ids = MagicMock(return_value=['test'])
    plugins.get_tab_idx('test')
    mock_window.core.plugins.get_ids.assert_called_once()


def test_unregister(mock_window):
    """Test unregister plugin"""
    plugins = Plugins(mock_window)
    plugins.enabled = {'test': True}
    mock_window.core.plugins.unregister = MagicMock()
    plugins.unregister('test')
    mock_window.core.plugins.unregister.assert_called_once_with('test')
    assert 'test' not in plugins.enabled


def test_destroy(mock_window):
    """Test destroy plugins workers"""
    plugins = Plugins(mock_window)
    mock_window.core.plugins.get_ids = MagicMock(return_value=['test'])
    mock_window.core.plugins.destroy = MagicMock()
    plugins.destroy()
    mock_window.core.plugins.get_ids.assert_called_once()
    mock_window.core.plugins.destroy.assert_called_once_with('test')


def test_has_type(mock_window):
    """Test has type"""
    plugins = Plugins(mock_window)
    plugin = BasePlugin()
    plugin.type = ['test']
    mock_window.core.plugins.is_registered = MagicMock(return_value=True)
    mock_window.core.plugins.get = MagicMock(return_value=plugin)
    assert plugins.has_type('test_plugin', 'test') is True
    mock_window.core.plugins.is_registered.assert_called_once_with('test_plugin')
    mock_window.core.plugins.get.assert_called_once_with('test_plugin')


def test_is_type_enabled(mock_window):
    """Test is type enabled"""
    plugins = Plugins(mock_window)
    mock_window.core.plugins.get_ids = MagicMock(return_value=['test'])
    mock_window.core.plugins.get = MagicMock()
    mock_window.core.plugins.get.return_value.type = ['test']
    plugins.is_enabled = MagicMock(return_value=True)
    assert plugins.is_type_enabled('test') is True
    mock_window.core.plugins.get_ids.assert_called_once()
    mock_window.core.plugins.get.assert_called_once_with('test')
    plugins.is_enabled.assert_called_once_with('test')


def test_handle_types(mock_window):
    """Test handle plugin type"""
    plugins = Plugins(mock_window)
    mock_window.core.plugins.allowed_types = ['audio.input']
    plugins.is_type_enabled = MagicMock(return_value=True)
    mock_window.ui.plugin_addon = {
        'audio.input': MagicMock(),
        'audio.input.btn': MagicMock()
    }
    plugins.handle_types()
    plugins.is_type_enabled.assert_called_once_with('audio.input')


def test_update_info(mock_window):
    """Test update plugins info"""
    plugins = Plugins(mock_window)
    plugin = BasePlugin()
    plugin.name = 'test'
    mock_window.core.plugins.get_ids = MagicMock(return_value=['test'])
    mock_window.core.plugins.get = MagicMock(return_value=plugin)
    plugins.is_enabled = MagicMock(return_value=True)
    plugins.window.ui.nodes['chat.plugins'] = MagicMock()
    plugins.update_info()
    mock_window.core.plugins.get_ids.assert_called()
    mock_window.ui.nodes['chat.plugins'].setToolTip.assert_called_once_with('test')


def test_apply_cmds(mock_window):
    """Test apply commands"""
    plugins = Plugins(mock_window)
    ctx = CtxItem()
    cmds = [
        {
            'cmd': 'test',
            'params': {
                'status': 'finished'
            }
        }
    ]
    mock_window.core.command.from_commands = MagicMock(return_value=cmds)
    mock_window.controller.command.dispatch = MagicMock()
    plugins.apply_cmds(ctx, [{'cmd': 'test'}])
    mock_window.controller.command.dispatch.assert_called_once()


def test_apply_cmds_inline(mock_window):
    """Test apply commands only (inline)"""
    plugins = Plugins(mock_window)
    ctx = CtxItem()
    cmds = [
        {
            'cmd': 'test',
            'params': {
                'status': 'finished'
            }
        }
    ]
    mock_window.core.command.from_commands = MagicMock(return_value=cmds)
    mock_window.controller.command.dispatch = MagicMock()
    plugins.apply_cmds_inline(ctx, [{'cmd': 'test'}])
    mock_window.controller.command.dispatch.assert_called_once()
