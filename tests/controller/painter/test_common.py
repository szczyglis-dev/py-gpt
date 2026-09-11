#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.03 20:31:00                  #
# ================================================== #

from unittest.mock import MagicMock

from PySide6.QtGui import QColor

from tests.mocks import mock_window
from pygpt_net.controller.painter.common import Common
from pygpt_net.ui.widget.draw.modes import DrawMode


def test_convert_to_size(mock_window):
    """Test convert to size"""
    common = Common(mock_window)
    assert common.convert_to_size('800x600') == (800, 600)


def test_set_canvas_size(mock_window):
    """Test set canvas size"""
    common = Common(mock_window)
    mock_window.ui.painter.setFixedSize = MagicMock()
    common.set_canvas_size(800, 600)
#    mock_window.ui.painter.setFixedSize.assert_called_once()


def test_set_brush_mode(mock_window):
    """Test set brush mode"""
    common = Common(mock_window)
    mock_window.ui.nodes['painter.select.brush.color'].setCurrentText = MagicMock()
    mock_window.ui.painter.set_brush_color = MagicMock()
    common.set_brush_mode(True)


def test_set_erase_mode(mock_window):
    """Test set erase mode"""
    common = Common(mock_window)
    mock_window.ui.nodes['painter.select.brush.color'].setCurrentText = MagicMock()
    mock_window.ui.painter.set_brush_color = MagicMock()
    common.set_erase_mode(True)


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
    mock_window.core.filesystem.get_runtime_dir = MagicMock(return_value='/tmp/pygpt/capture')
    assert common.get_capture_dir() == '/tmp/pygpt/capture'
    mock_window.core.filesystem.get_runtime_dir.assert_called_once_with('capture')


def test_get_draw_modes(mock_window):
    """Test available drawing modes and their stable order."""
    common = Common(mock_window)
    assert common.get_draw_modes() == (
        DrawMode.FREE,
        DrawMode.ARROW,
        DrawMode.RECTANGLE,
        DrawMode.CIRCLE,
        DrawMode.LINE,
    )


def test_change_draw_mode(mock_window):
    """Test drawing mode change synchronizes painter, combo and config."""
    combo = MagicMock()
    combo.findData.return_value = 1
    combo.currentIndex.return_value = 0
    mock_window.ui.nodes = {'painter.select.draw.mode': combo}
    mock_window.ui.painter.set_draw_mode = MagicMock()

    common = Common(mock_window)
    common.change_draw_mode('arrow')

    mock_window.ui.painter.set_draw_mode.assert_called_once_with(DrawMode.ARROW)
    combo.setCurrentIndex.assert_called_once_with(1)
    assert mock_window.core.config.get('painter.draw.mode') == 'arrow'
    mock_window.core.config.save.assert_called()


def test_change_draw_mode_from_combo(mock_window):
    """Test drawing mode can be read directly from toolbar combo data."""
    combo = MagicMock()
    combo.currentData.return_value = 'rectangle'
    combo.findData.return_value = 2
    combo.currentIndex.return_value = 2
    mock_window.ui.nodes = {'painter.select.draw.mode': combo}
    mock_window.ui.painter.set_draw_mode = MagicMock()

    common = Common(mock_window)
    common.change_draw_mode()

    mock_window.ui.painter.set_draw_mode.assert_called_once_with(DrawMode.RECTANGLE)
    combo.setCurrentIndex.assert_not_called()
    assert mock_window.core.config.get('painter.draw.mode') == 'rectangle'


def test_change_draw_mode_invalid_falls_back_to_free(mock_window):
    """Test invalid persisted/selected drawing mode falls back to Free."""
    combo = MagicMock()
    combo.findData.return_value = 0
    combo.currentIndex.return_value = 0
    mock_window.ui.nodes = {'painter.select.draw.mode': combo}
    mock_window.ui.painter.set_draw_mode = MagicMock()

    common = Common(mock_window)
    common.change_draw_mode('invalid-mode')

    mock_window.ui.painter.set_draw_mode.assert_called_once_with(DrawMode.FREE)
    assert mock_window.core.config.get('painter.draw.mode') == 'free'


def test_restore_draw_mode(mock_window):
    """Test drawing mode is restored from config."""
    mock_window.core.config.set('painter.draw.mode', 'circle')
    common = Common(mock_window)
    common.change_draw_mode = MagicMock()

    common.restore_draw_mode()

    common.change_draw_mode.assert_called_once_with('circle')


def test_restore_draw_mode_defaults_to_free(mock_window):
    """Test missing drawing mode config restores Free."""
    mock_window.core.config.data.pop('painter.draw.mode', None)
    common = Common(mock_window)
    common.change_draw_mode = MagicMock()

    common.restore_draw_mode()

    common.change_draw_mode.assert_called_once_with('free')


def test_step_brush_size_up_syncs_combo(mock_window):
    """Test wheel-size step moves to the next brush size via combo."""
    combo = MagicMock()
    combo.findText.return_value = 4
    mock_window.ui.nodes = {'painter.select.brush.size': combo}
    mock_window.ui.painter.brushSize = 3

    common = Common(mock_window)
    common.step_brush_size(1)

    combo.findText.assert_called_once_with('5')
    combo.setCurrentIndex.assert_called_once_with(4)


def test_step_brush_size_down_syncs_combo(mock_window):
    """Test wheel-size step moves to the previous configured brush size."""
    combo = MagicMock()
    combo.findText.return_value = 1
    mock_window.ui.nodes = {'painter.select.brush.size': combo}
    mock_window.ui.painter.brushSize = 3

    common = Common(mock_window)
    common.step_brush_size(-1)

    combo.findText.assert_called_once_with('2')
    combo.setCurrentIndex.assert_called_once_with(1)


def test_step_brush_size_falls_back_when_combo_item_missing(mock_window):
    """Test wheel-size step still applies when combo has no matching item."""
    combo = MagicMock()
    combo.findText.return_value = -1
    mock_window.ui.nodes = {'painter.select.brush.size': combo}
    mock_window.ui.painter.brushSize = 3

    common = Common(mock_window)
    common.change_brush_size = MagicMock()
    common.step_brush_size(1)

    common.change_brush_size.assert_called_once_with(5)


def test_restore_brush_settings_restores_draw_mode(mock_window):
    """Test brush settings restoration also restores the selected draw mode."""
    mock_window.ui.nodes = {
        'painter.select.brush.size': MagicMock(),
        'painter.select.brush.color': MagicMock(),
        'painter.btn.brush': MagicMock(),
        'painter.btn.erase': MagicMock(),
    }
    common = Common(mock_window)
    common.restore_draw_mode = MagicMock()

    common.restore_brush_settings()

    common.restore_draw_mode.assert_called_once()
