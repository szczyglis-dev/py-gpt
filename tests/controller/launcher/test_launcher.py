#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.11 00:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller import Launcher


def test_post_setup(mock_window):
    """Test post setup"""
    launcher = Launcher(mock_window)
    mock_window.core.config.data['mode'] = 'chat'
    mock_window.core.config.data['api_key'] = None
    mock_window.core.config.data['updater.check.launch'] = True
    launcher.show_api_monit = MagicMock()
    mock_window.core.updater.run_check = MagicMock()

    launcher.post_setup()
#    launcher.show_api_monit.assert_called_once()
    mock_window.core.updater.run_check.assert_called_once()


def test_show_api_monit(mock_window):
    """Test show api monit"""
    launcher = Launcher(mock_window)
    mock_window.ui.dialogs.open = MagicMock()
    launcher.show_api_monit()
    mock_window.ui.dialogs.open.assert_called_once_with('info.start')


def test_check_updates(mock_window):
    """Test check updates"""
    launcher = Launcher(mock_window)
    mock_window.core.updater.check = MagicMock()
    launcher.check_updates()
    mock_window.core.updater.check.assert_called_once_with(True)
