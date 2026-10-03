from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtGui import QImage, QColor

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.tools.base import BaseTool
from pygpt_net.tools.painter import Painter


@pytest.fixture
def painter(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = QMainWindow()
    window.core = MagicMock()
    window.controller = MagicMock()
    window.tools = MagicMock()
    window.ui = MagicMock()
    window.update_status = MagicMock()
    window.core.config.has.return_value = False
    window.core.config.get.side_effect = lambda key, default=None: default
    window.core.filesystem.get_runtime_dir.return_value = str(tmp_path)
    tool = Painter()
    tool.attach(window)
    window.tools.get.return_value = tool
    yield tool
    if tool.frontend is not None:
        tool.frontend.on_delete()
    window.close()
    window.deleteLater()
    app.processEvents()


def test_painter_uses_tool_tab_policy_and_lazy_frontend(painter):
    assert isinstance(painter, BaseTool)
    assert painter.can_open_tab()
    assert not painter.can_open_dialog()
    assert not painter.allows_multiple_tabs()
    assert painter.canvas is None
    painter.open_tab()
    painter.window.controller.tabs.open_or_activate.assert_called_once_with(Tab.TAB_TOOL, 'painter')


def test_frontend_closing_and_reopening_restores_drawing(painter):
    tab = Tab()
    tab.type, tab.tool_id = Tab.TAB_TOOL, 'painter'
    frontend = painter.as_tab(tab)
    assert painter.canvas.document.size().width() == 800
    image = QImage(32, 24, QImage.Format_RGB32)
    image.fill(QColor('red'))
    painter.canvas.document.set_image(image)
    painter.canvas.document.compose()
    painter.window.controller.tabs.get_current_tab.return_value = tab
    assert painter.is_active()
    frontend.on_delete()
    frontend.deleteLater()
    assert painter.canvas is None
    assert painter._surfaces == []
    painter.as_tab(tab)
    painter.canvas.document.compose()
    assert painter.canvas.document.source_image.pixelColor(0, 0) == QColor('red')
    assert len(painter._surfaces) == 1


def test_reload_resets_history_and_restores_current_profile(painter):
    painter.ensure_canvas()
    painter.canvas.history.push()
    assert painter.canvas.history.can_undo()
    painter.on_reload()
    # Initial canvas-size restoration must not leak the old profile's undo history.
    assert not painter.canvas.history.can_redo()
    assert painter.canvas.document.source_image is None


def test_exit_without_opening_painter_does_not_create_frontend(painter):
    painter.on_exit()
    assert painter.canvas is None


def test_old_frontend_saves_to_its_profile_during_switch(painter, tmp_path):
    painter.ensure_canvas()
    image = QImage(16, 12, QImage.Format_RGB32)
    image.fill(QColor('blue'))
    painter.canvas.document.set_image(image)
    next_profile = tmp_path / 'next-profile'
    next_profile.mkdir()
    painter.window.core.filesystem.get_runtime_dir.return_value = str(next_profile)
    old_frontend = painter.frontend
    old_frontend.on_delete()
    assert (tmp_path / '_current.png').is_file()
    assert not (next_profile / '_current.png').exists()
    painter.ensure_canvas()
    assert painter.canvas.document.source_image is None
    old_frontend.on_delete()  # A delayed cleanup must not delete the new frontend.
    assert painter.canvas is not None


@pytest.mark.parametrize('mode', ['free', 'rectangle', 'line', 'arrow', 'circle'])
def test_drawing_zoom_and_history_preserve_logical_pixels(painter, mode):
    from PySide6.QtCore import QPoint, QSize
    from pygpt_net.tools.painter.core.modes import DrawMode
    canvas = painter.ensure_canvas()
    canvas.document.resize(64, 48)
    canvas.history.undo_stack.clear()
    canvas.set_brush_color(QColor('blue'))
    canvas.set_draw_mode(mode)
    handler = canvas._drawHandlers[DrawMode.from_value(mode)]
    handler.begin(canvas, QPoint(10, 10))
    handler.update(canvas, QPoint(40, 30))
    handler.release(canvas, QPoint(40, 30))
    canvas.document.compose()
    rendered = QImage(canvas.document.image)
    assert any(rendered.pixelColor(x, y) != QColor('white') for x in range(64) for y in range(48))
    canvas.viewport.set_percent(200)
    assert canvas.document.size() == QSize(64, 48)
    assert canvas.document.image == rendered
    canvas.history.undo()
    canvas.document.compose()
    assert canvas.document.image.pixelColor(10, 10) == QColor('white')
    canvas.history.redo()
    canvas.document.compose()
    assert canvas.document.image == rendered


def test_reverse_crop_and_undo_keep_layers_and_size(painter):
    from PySide6.QtCore import QPoint, QRect, QSize
    canvas = painter.ensure_canvas()
    painter.settings.change_canvas_size('64x48')
    canvas.history.undo_stack.clear()
    canvas.history.push()
    canvas.selection.start()
    canvas.selection.rect = QRect(QPoint(40, 30), QPoint(10, 10))
    expected = canvas.selection.rect.normalized().size()
    canvas.selection.finish()
    assert canvas.document.size() == expected
    canvas.history.undo()
    assert canvas.document.size() == QSize(64, 48)
    canvas.history.redo()
    assert canvas.document.size() == expected


def test_text_history_restores_editable_draft_and_committed_pixels(painter):
    from PySide6.QtCore import QPoint
    canvas = painter.ensure_canvas()
    painter.settings.change_canvas_size('200x100')
    canvas.history.undo_stack.clear()
    canvas.text.start_edit(canvas, QPoint(10, 10), text='Hello', font_size=14)
    assert canvas.text.commit(canvas)
    canvas.document.compose()
    committed = QImage(canvas.document.image)
    canvas.history.undo()
    assert canvas.text.has_active()
    assert canvas.text.reopened_from_undo()
    canvas.history.undo()
    assert not canvas.text.has_active()
    canvas.history.redo()
    assert canvas.text.has_active()
    canvas.history.redo()
    canvas.document.compose()
    assert not canvas.text.has_active()
    assert canvas.document.image == committed


def test_camera_can_create_painter_lazily(painter):
    import numpy as np
    painter.window.controller.camera.get_current_frame.return_value = np.zeros((12, 16, 3), dtype=np.uint8)
    assert painter.capture.camera(show_flash=False)
    assert painter.canvas.document.source_image.width() == 16
    painter.window.controller.tabs.open_or_activate.assert_not_called()


def test_canvas_plugin_captures_painter_via_tool_registry(painter, tmp_path):
    from pygpt_net.plugin.canvas_web.plugin import Plugin
    painter.ensure_canvas()
    painter.settings.change_canvas_size('64x48')
    painter.canvas.document.base.fill(QColor('green'))
    painter.canvas.document.mark_composite_dirty()
    painter.window.core.filesystem.get_runtime_artifacts_dir.return_value = str(tmp_path / 'runtime')
    plugin = Plugin()
    plugin.window = painter.window
    result = plugin.capture_user_painter_image()
    assert (result['width'], result['height']) == (64, 48)
    image = QImage(result['path'])
    assert image.pixelColor(0, 0) == QColor('green')
    painter.window.core.attachments.new.assert_not_called()
