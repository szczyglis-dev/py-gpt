#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.21 20:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock

from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.controller.agent import Common


def test_toggle_status(mock_window):
    """Test toggle_status"""
    mock_window.core.config.set("mode", "agent")
    mock_window.controller.agent.legacy.is_inline = MagicMock(return_value=False)
    common = Common(mock_window)
    common.show_status = MagicMock()
    common.hide_status = MagicMock()

    common.toggle_status()
    common.show_status.assert_called_once()

    mock_window.core.config.set("mode", "chat")
    common.toggle_status()
    common.hide_status.assert_called_once()


def test_enable_auto_stop(mock_window):
    """Test enable_auto_stop"""
    mock_window.core.config = MagicMock()
    common = Common(mock_window)
    common.enable_auto_stop()
    mock_window.core.config.set.assert_called_once()


def test_disable_auto_stop(mock_window):
    """Test disable_auto_stop"""
    mock_window.core.config = MagicMock()
    common = Common(mock_window)
    common.disable_auto_stop()
    mock_window.core.config.set.assert_called_once()


def test_show_status(mock_window):
    """Test show_status"""
    common = Common(mock_window)
    mock_window.ui.nodes['status.agent'] = MagicMock()
    common.show_status()
    mock_window.ui.nodes['status.agent'].setVisible.assert_called_once()


def test_hide_status(mock_window):
    """Test hide_status"""
    common = Common(mock_window)
    mock_window.ui.nodes['status.agent'] = MagicMock()
    common.hide_status()
    mock_window.ui.nodes['status.agent'].setVisible.assert_called_once()


def test_toggle_auto_stop(mock_window):
    """Test toggle_auto_stop"""
    common = Common(mock_window)
    common.enable_auto_stop = MagicMock()
    common.disable_auto_stop = MagicMock()
    common.toggle_auto_stop(True)
    common.enable_auto_stop.assert_called_once()
    common.disable_auto_stop.assert_not_called()
    common.toggle_auto_stop(False)
    common.enable_auto_stop.assert_called_once()
    common.disable_auto_stop.assert_called_once()
