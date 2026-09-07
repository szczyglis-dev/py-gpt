from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QPoint, QRect, Qt

from pygpt_net.ui.widget.screenshot import ScreenshotFlash, ScreenRegionSelector


def test_flash_show_closes_when_screen_or_geometry_missing():
    widget = SimpleNamespace(screen=None, screen_geometry=QRect(), close=MagicMock())
    ScreenshotFlash.show_flash(widget)
    widget.close.assert_called_once()


def test_flash_show_sets_geometry_and_schedules_fade_steps():
    geometry = QRect(10, 20, 100, 80)
    widget = SimpleNamespace(
        screen=object(), screen_geometry=geometry, setGeometry=MagicMock(), show=MagicMock(), raise_=MagicMock(),
        _set_alpha=MagicMock(), close=MagicMock(),
    )

    with patch("pygpt_net.ui.widget.screenshot.QTimer.singleShot") as single_shot:
        ScreenshotFlash.show_flash(widget)

    widget.setGeometry.assert_called_once_with(geometry)
    widget.show.assert_called_once()
    widget.raise_.assert_called_once()
    assert [call.args[0] for call in single_shot.call_args_list] == [45, 90, 140]


def test_flash_alpha_updates_only_while_visible():
    widget = SimpleNamespace(isVisible=MagicMock(return_value=False), _alpha=90, update=MagicMock())
    ScreenshotFlash._set_alpha(widget, 20)
    assert widget._alpha == 90
    widget.update.assert_not_called()

    widget.isVisible.return_value = True
    ScreenshotFlash._set_alpha(widget, 20)
    assert widget._alpha == 20
    widget.update.assert_called_once()


def test_region_clamp_limits_coordinates_to_widget_bounds():
    widget = SimpleNamespace(width=lambda: 100, height=lambda: 50)
    assert ScreenRegionSelector._clamp_point(widget, QPoint(-5, 60)) == QPoint(0, 49)
    assert ScreenRegionSelector._clamp_point(widget, QPoint(30, 20)) == QPoint(30, 20)


def test_finish_selection_cancels_tiny_region():
    widget = SimpleNamespace(
        _selection_rect=QRect(1, 1, 1, 20), rect=lambda: QRect(0, 0, 100, 100), _selecting=True,
        cancel=MagicMock(),
    )
    ScreenRegionSelector._finish_selection(widget)
    assert widget._selecting is False
    widget.cancel.assert_called_once()


def test_finish_selection_emits_global_rectangle_after_overlay_hidden():
    emitted = MagicMock()
    widget = SimpleNamespace(
        _selection_rect=QRect(QPoint(10, 10), QPoint(30, 25)),
        rect=lambda: QRect(0, 0, 100, 100),
        _selecting=True,
        mapToGlobal=MagicMock(return_value=QPoint(110, 210)),
        hide=MagicMock(), close=MagicMock(),
        region_selected=SimpleNamespace(emit=emitted),
    )

    with patch("pygpt_net.ui.widget.screenshot.QApplication.processEvents") as process_events:
        ScreenRegionSelector._finish_selection(widget)

    widget.hide.assert_called_once()
    process_events.assert_called_once()
    rect = emitted.call_args.args[0]
    assert rect.topLeft() == QPoint(110, 210)
    assert rect.size() == QRect(QPoint(10, 10), QPoint(30, 25)).normalized().size()
    widget.close.assert_called_once()


def test_cancel_releases_mouse_only_during_selection_and_emits_cancelled():
    emitted = MagicMock()
    widget = SimpleNamespace(
        _selecting=True, releaseMouse=MagicMock(), hide=MagicMock(), close=MagicMock(),
        cancelled=SimpleNamespace(emit=emitted),
    )
    with patch("pygpt_net.ui.widget.screenshot.QApplication.processEvents"):
        ScreenRegionSelector.cancel(widget)
    widget.releaseMouse.assert_called_once()
    assert widget._selecting is False
    emitted.assert_called_once()


def test_mouse_press_left_starts_selection_and_right_cancels():
    point = QPoint(5, 6)
    event = MagicMock()
    event.button.return_value = Qt.LeftButton
    event.position.return_value.toPoint.return_value = point
    widget = SimpleNamespace(
        _selecting=False, _selection_start=QPoint(), _selection_rect=QRect(),
        _clamp_point=MagicMock(return_value=point), grabMouse=MagicMock(), update=MagicMock(), cancel=MagicMock(),
    )

    ScreenRegionSelector.mousePressEvent(widget, event)
    assert widget._selecting is True
    assert widget._selection_start == point
    widget.grabMouse.assert_called_once()
    event.accept.assert_called_once()

    right = MagicMock()
    right.button.return_value = Qt.RightButton
    ScreenRegionSelector.mousePressEvent(widget, right)
    widget.cancel.assert_called_once()
    right.accept.assert_called_once()


def test_mouse_move_and_release_update_selection_when_dragging():
    start = QPoint(2, 3)
    current = QPoint(20, 30)
    widget = SimpleNamespace(
        _selecting=True, _selection_start=start, _selection_rect=QRect(),
        _clamp_point=MagicMock(return_value=current), update=MagicMock(),
        releaseMouse=MagicMock(), _finish_selection=MagicMock(),
    )
    move = MagicMock()
    move.buttons.return_value = Qt.LeftButton
    move.position.return_value.toPoint.return_value = current
    ScreenRegionSelector.mouseMoveEvent(widget, move)
    assert widget._selection_rect == QRect(start, current)
    move.accept.assert_called_once()

    release = MagicMock()
    release.button.return_value = Qt.LeftButton
    release.position.return_value.toPoint.return_value = current
    ScreenRegionSelector.mouseReleaseEvent(widget, release)
    widget.releaseMouse.assert_called_once()
    widget._finish_selection.assert_called_once()
    release.accept.assert_called_once()


def test_escape_key_cancels_selector():
    event = MagicMock()
    event.key.return_value = Qt.Key_Escape
    widget = SimpleNamespace(cancel=MagicMock())
    ScreenRegionSelector.keyPressEvent(widget, event)
    widget.cancel.assert_called_once()
    event.accept.assert_called_once()
