#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.02 19:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock

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


def test_is_inline(mock_window):
    """Test is_inline"""
    agent = Agent(mock_window)
    mock_window.controller.plugins.is_type_enabled = MagicMock(return_value=True)
    assert agent.is_inline() is True
    mock_window.controller.plugins.is_type_enabled = MagicMock(return_value=False)
    assert agent.is_inline() is False

def test_update(mock_window):
    """Test update"""
    agent = Agent(mock_window)
    agent.common = MagicMock()
    agent.common.toggle_status = MagicMock()
    agent.update()
    agent.common.toggle_status.assert_called_once()
