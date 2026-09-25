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


def test_run_startup_checks(mock_window):
    """Test deferred startup checks."""
    launcher = Launcher(mock_window)
    mock_window.core.config.data['updater.check.launch'] = True
    mock_window.core.banners.run_load = MagicMock()
    mock_window.core.updater.run_check = MagicMock()

    launcher._run_startup_checks()

    mock_window.core.banners.run_load.assert_called_once_with()
    mock_window.core.updater.run_check.assert_called_once_with(
        force=True,
        event="launch",
    )

    # The app-ready signal may fire more than once; checks are intentionally one-shot.
    launcher._run_startup_checks()
    mock_window.core.banners.run_load.assert_called_once_with()
    mock_window.core.updater.run_check.assert_called_once_with(
        force=True,
        event="launch",
    )


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
