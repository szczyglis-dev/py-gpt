#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch

from tests.mocks import mock_window
from pygpt_net.controller.painter import Painter


def test_setup(mock_window):
    """Test setup"""
    painter = Painter(mock_window)
    painter.restore = MagicMock()
    painter.common.change_canvas_size = MagicMock()
    painter.setup()
    painter.restore.assert_called_once()
    painter.common.change_canvas_size.assert_called_once()


def test_open(mock_window):
    """Test open"""
    painter = Painter(mock_window)
    painter.window.ui.painter.open_image = MagicMock()
    painter.open('test.png')
    painter.window.ui.painter.open_image.assert_called_once_with('test.png')


def test_save(mock_window):
    """Test save"""
    painter = Painter(mock_window)
    painter.window.ui.painter.image.save = MagicMock()
    painter.save()
    painter.window.ui.painter.image.save.assert_called_once()


def test_save_all(mock_window):
    """Test save all"""
    painter = Painter(mock_window)
    painter.save = MagicMock()
    painter.save_all()
    painter.save.assert_called_once()


def test_restore(mock_window):
    """Test restore"""
    painter = Painter(mock_window)
    with patch('os.path.exists', return_value=True):
        painter.window.ui.painter.image.load = MagicMock()
        painter.window.ui.painter.update = MagicMock()
        painter.restore()
        painter.window.ui.painter.update.assert_called_once()
