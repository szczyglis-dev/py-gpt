#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 21:00:00                  #
# ================================================== #

from tests.mocks import mock_window_conf
from pygpt_net.core.plugins import Plugins
from pygpt_net.plugin.base.plugin import BasePlugin


def mock_get(key):
    if key == "img_prompt":
        return 'test'
    elif key == "img_raw":
        return True


def mock_has(key):
    """
    Mock has
    """
    if key == "img_prompt":
        return True


def test_is_registered(mock_window_conf):
    """
    Test is registered
    """
    plugins = Plugins(mock_window_conf)
    plugins.window.core.config.get = mock_get
    plugins.window.core.config.has = mock_has
    plugin = BasePlugin()
    plugin.id = 'test'
    plugins.register(plugin)

    assert plugins.is_registered('test') is True


def test_register(mock_window_conf):
    """
    Test register
    """
    plugins = Plugins(mock_window_conf)
    plugins.window.core.config.get = mock_get
    plugins.window.core.config.has = mock_has
    plugin = BasePlugin()
    plugin.id = 'test'
    plugins.register(plugin)

    assert plugins.plugins['test'] == plugin


def test_restore_options(mock_window_conf):
    """
    Test restore options
    """
    plugins = Plugins(mock_window_conf)
    plugins.window.core.config.get = mock_get
    plugins.window.core.config.has = mock_has
    plugin = BasePlugin()
    plugin.id = 'test'
    plugins.register(plugin)
    plugins.plugins['test'].options = {'test': {'value': 'test'}}
    plugins.restore_options('test')
    assert plugins.plugins['test'].options == plugin.options
