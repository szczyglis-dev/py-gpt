#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.31 20:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock

from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.controller.agent import Agent


def test_setup(mock_window):
    """Test setup"""
    agent = Agent(mock_window)
    mock_window.ui.add_hook = MagicMock()
    agent.setup()
    mock_window.ui.add_hook.assert_called_once()


def test_hook_update(mock_window):
    """Test hook_update"""
    agent = Agent(mock_window)
    agent.update = MagicMock()
    agent.hook_update("agent.iterations", 3, None)
    agent.update.assert_called_once()


def test_is_agent_inline(mock_window):
    """Test is_agent_inline"""
    agent = Agent(mock_window)
    mock_window.controller.plugins.is_type_enabled = MagicMock(return_value=True)
    assert agent.is_agent_inline() is True
    mock_window.controller.plugins.is_type_enabled = MagicMock(return_value=False)
    assert agent.is_agent_inline() is False


def test_toggle_status(mock_window):
    """Test toggle_status"""
    mock_window.core.config.set("mode", "agent")
    agent = Agent(mock_window)
    agent.is_agent_inline = MagicMock(return_value=False)
    agent.show_status = MagicMock()
    agent.hide_status = MagicMock()

    agent.toggle_status()
    agent.show_status.assert_called_once()

    mock_window.core.config.set("mode", "chat")
    agent.toggle_status()
    agent.hide_status.assert_called_once()


def test_enable_auto_stop(mock_window):
    """Test enable_auto_stop"""
    mock_window.core.config = MagicMock()
    agent = Agent(mock_window)
    agent.enable_auto_stop()
    mock_window.core.config.set.assert_called_once()


def test_disable_auto_stop(mock_window):
    """Test disable_auto_stop"""
    mock_window.core.config = MagicMock()
    agent = Agent(mock_window)
    agent.disable_auto_stop()
    mock_window.core.config.set.assert_called_once()


def test_update(mock_window):
    """Test update"""
    agent = Agent(mock_window)
    agent.toggle_status = MagicMock()
    agent.update()
    agent.toggle_status.assert_called_once()


def test_show_status(mock_window):
    """Test show_status"""
    agent = Agent(mock_window)
    mock_window.ui.nodes['status.agent'] = MagicMock()
    agent.show_status()
    mock_window.ui.nodes['status.agent'].setVisible.assert_called_once()


def test_hide_status(mock_window):
    """Test hide_status"""
    agent = Agent(mock_window)
    mock_window.ui.nodes['status.agent'] = MagicMock()
    agent.hide_status()
    mock_window.ui.nodes['status.agent'].setVisible.assert_called_once()


def test_toggle_auto_stop(mock_window):
    """Test toggle_auto_stop"""
    agent = Agent(mock_window)
    agent.enable_auto_stop = MagicMock()
    agent.disable_auto_stop = MagicMock()
    agent.toggle_auto_stop(True)
    agent.enable_auto_stop.assert_called_once()
    agent.disable_auto_stop.assert_not_called()
    agent.toggle_auto_stop(False)
    agent.enable_auto_stop.assert_called_once()
    agent.disable_auto_stop.assert_called_once()
