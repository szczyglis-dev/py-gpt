from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.widget.dialog.update import UpdateDialog


def _dialog(
        *,
        is_snap=False,
        compiled=False,
        windows=False,
        linux=False,
        appimage=False,
        store=False,
        auto_type=None,
        auto_available=False,
):
    platforms = MagicMock()
    platforms.is_snap.return_value = is_snap
    platforms.is_windows.return_value = windows
    platforms.is_linux.return_value = linux
    platforms.is_appimage.return_value = appimage
    platforms.is_ms_store.return_value = store

    config = MagicMock()
    config.is_compiled.return_value = compiled

    updater = MagicMock()
    if auto_type is None:
        if is_snap:
            auto_type = "snap"
        elif appimage:
            auto_type = "appimage"
        elif compiled and windows:
            auto_type = "windows"
        elif compiled and linux:
            auto_type = "linux"
        else:
            auto_type = "pip"
    updater.get_auto_update_type.return_value = auto_type
    updater.can_auto_update.return_value = auto_available

    window = SimpleNamespace(
        meta={"version": "2.8.4"},
        core=SimpleNamespace(platforms=platforms, config=config, updater=updater),
        controller=MagicMock(),
    )
    return SimpleNamespace(
        window=window,
        info=MagicMock(),
        changelog=MagicMock(),
        message=MagicMock(),
        info_upgrade=MagicMock(),
        update_now=MagicMock(),
        www=MagicMock(),
        github=MagicMock(),
        cmd=MagicMock(),
        download_file=MagicMock(),
        download_link="",
        update_payload={},
        cmd_snap="snap cmd",
        cmd_appimage="appimage cmd",
        cmd_source="source cmd",
        cmd_pip="pip cmd",
    )


def _set(widget, is_new=True):
    with patch("pygpt_net.ui.widget.dialog.update.trans", side_effect=lambda key: key):
        UpdateDialog.set_data(
            widget, is_new, "3.0", "2026-09-07", "changes",
            download_windows="win", download_linux="linux", download_appimage="appimage"
        )


def test_start_download_opens_current_download_link():
    widget = _dialog()
    widget.download_link = "https://download.test/file"
    UpdateDialog.start_download(widget)
    widget.window.controller.dialogs.info.open_url.assert_called_once_with(widget.download_link)


def test_start_auto_update_forwards_current_payload():
    widget = _dialog(auto_available=True)
    widget.update_payload = {
        "version": "3.0",
        "build": "2026-09-07",
        "changelog": "changes",
        "download_windows": "win",
        "download_linux": "linux",
        "download_appimage": "appimage",
    }

    UpdateDialog.start_auto_update(widget)

    widget.window.core.updater.start_auto_update.assert_called_once_with(**widget.update_payload)


def test_set_data_no_update_hides_upgrade_and_download_controls():
    widget = _dialog()
    _set(widget, is_new=False)

    widget.info.setText.assert_called_once_with("update.info.none")
    widget.changelog.setPlainText.assert_called_once_with("changes")
    widget.info_upgrade.setVisible.assert_called_with(False)
    widget.update_now.setVisible.assert_called_with(False)
    widget.update_now.setEnabled.assert_called_with(False)
    widget.cmd.setVisible.assert_called_once_with(False)
    widget.download_file.setVisible.assert_called_once_with(False)
    widget.www.setVisible.assert_called_with(True)
    widget.github.setVisible.assert_called_with(True)


def test_set_data_auto_update_shows_update_now_and_hides_generic_links():
    widget = _dialog(auto_available=True)

    _set(widget)

    widget.update_now.setVisible.assert_called_with(True)
    widget.update_now.setEnabled.assert_called_with(True)
    widget.info_upgrade.setVisible.assert_called_with(False)
    widget.www.setVisible.assert_called_with(False)
    widget.github.setVisible.assert_called_with(False)


def test_set_data_snap_uses_snap_command():
    widget = _dialog(is_snap=True)
    _set(widget)
    widget.cmd.setText.assert_called_once_with("snap cmd")
    widget.cmd.setCursorPosition.assert_called_once_with(0)
    widget.cmd.setVisible.assert_called_with(True)


def test_set_data_compiled_windows_configures_msi_download():
    widget = _dialog(compiled=True, windows=True)
    _set(widget)
    assert widget.download_link == "win"
    widget.download_file.setText.assert_called_once_with("action.download .msi (3.0)")
    widget.download_file.setVisible.assert_called_with(True)
    widget.www.setVisible.assert_called_with(False)


def test_set_data_ms_store_hides_external_upgrade_controls():
    widget = _dialog(compiled=True, windows=True, store=True)
    _set(widget)
    widget.download_file.setVisible.assert_called_with(False)
    widget.info_upgrade.setVisible.assert_called_with(False)
    widget.update_now.setVisible.assert_called_with(False)
    widget.www.setVisible.assert_called_with(False)


def test_set_data_compiled_linux_configures_zip_download():
    widget = _dialog(compiled=True, linux=True)
    _set(widget)
    assert widget.download_link == "linux"
    widget.download_file.setText.assert_called_once_with("action.download .zip (3.0)")
    widget.download_file.setVisible.assert_called_with(True)


def test_set_data_appimage_uses_appimage_command_and_download():
    widget = _dialog(appimage=True)
    _set(widget)
    widget.cmd.setText.assert_called_once_with("appimage cmd")
    widget.cmd.setCursorPosition.assert_called_once_with(0)
    widget.cmd.setVisible.assert_called_with(True)
    assert widget.download_link == "appimage"
    widget.download_file.setText.assert_called_once_with("action.download .AppImage (3.0)")


def test_set_data_git_source_uses_source_command():
    widget = _dialog(auto_type="source")
    _set(widget)
    widget.cmd.setText.assert_called_once_with("source cmd")
    widget.cmd.setCursorPosition.assert_called_once_with(0)
    widget.cmd.setVisible.assert_called_with(True)


def test_set_data_python_package_uses_pip_command():
    widget = _dialog(auto_type="pip")
    _set(widget)
    widget.cmd.setText.assert_called_once_with("pip cmd")
    widget.cmd.setCursorPosition.assert_called_once_with(0)
    widget.cmd.setVisible.assert_called_with(True)


def test_set_data_manual_source_uses_source_zip_and_does_not_suggest_pip():
    widget = _dialog(auto_type="source_manual")

    with patch("pygpt_net.ui.widget.dialog.update.AUTO_UPDATER_ENABLED", True):
        _set(widget)

    widget.cmd.setText.assert_not_called()
    widget.cmd.setVisible.assert_called_once_with(False)
    assert widget.download_link == (
        "https://github.com/szczyglis-dev/py-gpt/"
        "archive/refs/tags/v3.0.zip"
    )
    widget.download_file.setText.assert_called_once_with("action.download .zip (3.0)")
    widget.download_file.setVisible.assert_called_with(True)
    widget.info_upgrade.setText.assert_called_with("update.info.upgrade")
    widget.info_upgrade.setVisible.assert_called_with(True)


def test_set_data_manual_source_auto_update_hides_generic_links():
    widget = _dialog(auto_type="source_manual", auto_available=True)

    _set(widget)

    widget.update_now.setVisible.assert_called_with(True)
    widget.update_now.setEnabled.assert_called_with(True)
    widget.www.setVisible.assert_called_with(False)
    widget.github.setVisible.assert_called_with(False)
