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

from PySide6.QtCore import Qt

from pygpt_net.ui.widget.draw.modes import DrawMode
from pygpt_net.ui.widget.draw.painter import PainterWidget


def _wheel_event(delta):
    event = MagicMock()
    event.angleDelta.return_value.y.return_value = delta
    return event


def test_wheel_during_drawing_increases_brush_size():
    """Test wheel-up while LMB drawing changes size instead of zooming."""
    widget = MagicMock()
    widget._mouseDown = True
    widget.drawing = True
    widget.has_active_text_edit.return_value = False
    widget.window.controller.painter.common.step_brush_size = MagicMock()
    event = _wheel_event(120)

    PainterWidget.wheelEvent(widget, event)

    widget.window.controller.painter.common.step_brush_size.assert_called_once_with(1)
    widget.update.assert_called_once()
    event.accept.assert_called_once()
    event.modifiers.assert_not_called()


def test_wheel_during_drawing_decreases_brush_size():
    """Test wheel-down while LMB drawing selects the previous brush size."""
    widget = MagicMock()
    widget._mouseDown = True
    widget.drawing = True
    widget.has_active_text_edit.return_value = False
    widget.window.controller.painter.common.step_brush_size = MagicMock()
    event = _wheel_event(-120)

    PainterWidget.wheelEvent(widget, event)

    widget.window.controller.painter.common.step_brush_size.assert_called_once_with(-1)
    event.accept.assert_called_once()


def test_escape_cancels_active_drawing():
    """Test ESC cancels an in-progress drawing gesture."""
    widget = MagicMock()
    widget.drawing = True
    widget.cropping = False
    widget._handle_painter_shortcut.return_value = False
    widget.has_active_text_edit.return_value = False
    event = MagicMock()
    event.key.return_value = Qt.Key_Escape

    PainterWidget.keyPressEvent(widget, event)

    widget.cancel_active_drawing.assert_called_once()
    widget.cancel_crop.assert_not_called()


def test_set_draw_mode_cancels_active_gesture():
    """Test changing draw mode during a gesture cancels the old gesture first."""
    widget = MagicMock()
    widget.drawing = True

    PainterWidget.set_draw_mode(widget, 'rectangle')

    widget.cancel_active_drawing.assert_called_once()
    assert widget._drawMode == DrawMode.RECTANGLE
    widget.sync_draw_mode_actions.assert_called_once()
    widget.update.assert_called_once()


def test_eraser_always_uses_freehand_handler():
    """Test eraser ignores shape mode and erases freehand on the shared layer."""
    free_handler = MagicMock()
    arrow_handler = MagicMock()
    widget = MagicMock()
    widget._mode = 'erase'
    widget._drawMode = DrawMode.ARROW
    widget._drawHandlers = {
        DrawMode.FREE: free_handler,
        DrawMode.ARROW: arrow_handler,
    }

    handler = PainterWidget._effective_draw_handler(widget)

    assert handler is free_handler


def test_paint_uses_selected_shape_handler():
    """Test brush mode dispatches to the selected drawing handler."""
    free_handler = MagicMock()
    line_handler = MagicMock()
    widget = MagicMock()
    widget._mode = 'brush'
    widget._drawMode = DrawMode.LINE
    widget._drawHandlers = {
        DrawMode.FREE: free_handler,
        DrawMode.LINE: line_handler,
    }

    handler = PainterWidget._effective_draw_handler(widget)

    assert handler is line_handler
