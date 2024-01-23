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

from PySide6.QtGui import QColor

from tests.mocks import mock_window
from pygpt_net.controller.painter.common import Common


def test_convert_to_size(mock_window):
    """Test convert to size"""
    common = Common(mock_window)
    assert common.convert_to_size('800x600') == (800, 600)


def test_set_canvas_size(mock_window):
    """Test set canvas size"""
    common = Common(mock_window)
    mock_window.ui.painter.setFixedSize = MagicMock()
    common.set_canvas_size(800, 600)
    mock_window.ui.painter.setFixedSize.assert_called_once()


def test_set_brush_mode(mock_window):
    """Test set brush mode"""
    common = Common(mock_window)
    mock_window.ui.nodes['painter.select.brush.color'].setCurrentText = MagicMock()
    mock_window.ui.painter.set_brush_color = MagicMock()
    common.set_brush_mode(True)
    mock_window.ui.nodes['painter.select.brush.color'].setCurrentText.assert_called_once()
    mock_window.ui.painter.set_brush_color.assert_called_once()


def test_set_erase_mode(mock_window):
    """Test set erase mode"""
    common = Common(mock_window)
    mock_window.ui.nodes['painter.select.brush.color'].setCurrentText = MagicMock()
    mock_window.ui.painter.set_brush_color = MagicMock()
    common.set_erase_mode(True)
    mock_window.ui.nodes['painter.select.brush.color'].setCurrentText.assert_called_once()
    mock_window.ui.painter.set_brush_color.assert_called_once()


def test_change_canvas_size(mock_window):
    """Test change canvas size"""
    mock_window.ui.nodes['painter.select.canvas.size'].setCurrentText = MagicMock()
    mock_window.core.config.save()
    common = Common(mock_window)
    common.convert_to_size = MagicMock(return_value=(800, 600))
    common.set_canvas_size = MagicMock()
    common.change_canvas_size("800x600")
    assert mock_window.core.config.get('painter.canvas.size') == "800x600"


def test_change_brush_size(mock_window):
    """Test change brush size"""
    mock_window.ui.painter.set_brush_size = MagicMock()
    common = Common(mock_window)
    common.change_brush_size(10)
    mock_window.ui.painter.set_brush_size.assert_called_once_with(10)


def test_change_brush_color(mock_window):
    """Test change brush color"""
    mock_window.ui.nodes['painter.select.brush.color'].currentData = MagicMock(return_value=QColor(0, 0, 0))
    mock_window.ui.painter.set_brush_color = MagicMock()
    common = Common(mock_window)
    common.change_brush_color()
    mock_window.ui.painter.set_brush_color.assert_called_once_with(QColor(0, 0, 0))


def test_get_colors(mock_window):
    """Test get colors"""
    common = Common(mock_window)
    res = common.get_colors()
    assert isinstance(res, dict)
    assert len(res) > 0


def test_get_sizes(mock_window):
    """Test get sizes"""
    common = Common(mock_window)
    res = common.get_sizes()
    assert isinstance(res, list)
    assert len(res) > 0


def test_get_canvas_sizes(mock_window):
    """Test get canvas sizes"""
    common = Common(mock_window)
    res = common.get_canvas_sizes()
    assert isinstance(res, list)
    assert len(res) > 0


def test_get_capture_dir(mock_window):
    """Test get capture dir"""
    common = Common(mock_window)
    mock_window.core.config.get_user_dir = MagicMock(return_value='/tmp/pygpt/capture')
    assert common.get_capture_dir() == '/tmp/pygpt/capture'
