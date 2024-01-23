#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 19:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.idx.common import Common


def test_setup(mock_window):
    """Test setup"""
    common = Common(mock_window)
    mock_window.ui.config['global']['llama.idx.raw'].setChecked = MagicMock()
    common.setup()
    mock_window.ui.config['global']['llama.idx.raw'].setChecked.assert_called_once()


def test_enable_raw(mock_window):
    """Test enable raw"""
    common = Common(mock_window)
    mock_window.core.config.set = MagicMock()
    mock_window.core.config.save = MagicMock()
    common.enable_raw()
    mock_window.core.config.set.assert_called_once()
    mock_window.core.config.save.assert_called_once()


def test_disable_raw(mock_window):
    """Test disable raw"""
    common = Common(mock_window)
    mock_window.core.config.set = MagicMock()
    mock_window.core.config.save = MagicMock()
    common.disable_raw()
    mock_window.core.config.set.assert_called_once()
    mock_window.core.config.save.assert_called_once()


def test_toggle_raw(mock_window):
    """Test toggle raw"""
    common = Common(mock_window)
    common.enable_raw = MagicMock()
    common.toggle_raw(True)
    common.enable_raw.assert_called_once()