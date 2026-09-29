from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.tray import Tray


def _tray():
    window = SimpleNamespace(
        restore=MagicMock(),
        controller=SimpleNamespace(
            ctx=MagicMock(), notepad=MagicMock(), plugins=MagicMock(), launcher=MagicMock(),
            painter=SimpleNamespace(capture=MagicMock()), chat=SimpleNamespace(common=MagicMock()),
        ),
        ui=SimpleNamespace(tray_menu={}),
    )
    return SimpleNamespace(
        window=window, is_tray=True, icon=MagicMock(), region_selector=None,
        screenshot_flash=None, REGION_CAPTURE_HIDE_DELAY_MS=75,
        show_capture_flash=MagicMock(), hide_schedule_menu=MagicMock(),
    )


def test_set_icon_and_show_message_ignore_disabled_tray():
    tray = _tray()
    tray.is_tray = False
    Tray.set_icon(tray, "busy")
    Tray.show_msg(tray, "Title", "Body")
    tray.icon.setIcon.assert_not_called()
    tray.icon.showMessage.assert_not_called()


def test_tray_commands_restore_then_delegate():
    tray = _tray()
    Tray.new_ctx(tray)
    tray.window.controller.ctx.new_ungrouped.assert_called_once_with()
    Tray.open_notepad(tray)
    tray.window.controller.notepad.open.assert_called_once_with()
    Tray.open_scheduled_tasks(tray)
    tray.window.controller.plugins.settings.open_plugin.assert_called_once_with("crontab")
    assert tray.window.restore.call_count == 3


def test_fullscreen_screenshot_flashes_only_on_success():
    tray = _tray()
    tray.window.controller.painter.capture.screenshot.return_value = "/tmp/a.png"
    Tray.make_screenshot(tray)
    tray.show_capture_flash.assert_called_once_with(0)
    tray.window.restore.assert_called_once_with()
    tray.window.controller.chat.common.focus_input.assert_called_once_with()


def test_region_capture_is_deferred():
    tray = _tray()
    region = object()
    geometry = object()
    tray._capture_region_screenshot = MagicMock()

    with patch("pygpt_net.ui.tray.QTimer.singleShot", create=True) as single:
        Tray.make_region_screenshot(tray, region, geometry, 2)

    assert tray.region_selector is None
    delay, callback = single.call_args.args
    assert delay == 75
    callback()
    tray._capture_region_screenshot.assert_called_once_with(region, geometry, 2)


def test_capture_region_restores_and_focuses_input():
    tray = _tray()
    tray.window.controller.painter.capture.screenshot_region.return_value = "/tmp/crop.png"
    region, geometry = object(), object()
    Tray._capture_region_screenshot(tray, region, geometry, 3)
    tray.window.controller.painter.capture.screenshot_region.assert_called_once_with(
        region, geometry, screen_index=3,
    )
    tray.show_capture_flash.assert_called_once_with(3)
    tray.window.restore.assert_called_once_with()
    tray.window.controller.chat.common.focus_input.assert_called_once_with()


def test_clear_capture_flash_does_not_clobber_newer_flash():
    tray = _tray()
    old = object()
    new = object()
    tray.screenshot_flash = new
    Tray._clear_capture_flash(tray, old)
    assert tray.screenshot_flash is new
    Tray._clear_capture_flash(tray, new)
    assert tray.screenshot_flash is None


def test_update_schedule_tasks_hides_when_schedule_plugin_disabled():
    tray = _tray()
    action = MagicMock()
    tray.window.ui.tray_menu["scheduled"] = action
    tray.window.controller.plugins.is_type_enabled.return_value = False
    Tray.update_schedule_tasks(tray, 5)
    tray.hide_schedule_menu.assert_called_once_with()
    action.setText.assert_not_called()


def test_update_schedule_tasks_normalizes_count_and_shows_action():
    tray = _tray()
    action = MagicMock()
    action.isVisible.return_value = False
    tray.window.ui.tray_menu["scheduled"] = action
    tray.window.controller.plugins.is_type_enabled.return_value = True

    with patch("pygpt_net.ui.tray.trans", return_value="Scheduled"):
        Tray.update_schedule_tasks(tray, "4")

    action.setText.assert_called_once_with("Scheduled (4)")
    action.setVisible.assert_called_once_with(True)
