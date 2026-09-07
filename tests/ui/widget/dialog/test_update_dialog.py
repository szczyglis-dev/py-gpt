from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.widget.dialog.update import UpdateDialog


def _dialog(*, is_snap=False, compiled=False, windows=False, linux=False, appimage=False, store=False):
    platforms = MagicMock()
    platforms.is_snap.return_value = is_snap
    platforms.is_windows.return_value = windows
    platforms.is_linux.return_value = linux
    platforms.is_appimage.return_value = appimage
    platforms.is_ms_store.return_value = store
    config = MagicMock()
    config.is_compiled.return_value = compiled
    window = SimpleNamespace(
        meta={"version": "2.8.4"},
        core=SimpleNamespace(platforms=platforms, config=config),
        controller=MagicMock(),
    )
    return SimpleNamespace(
        window=window,
        info=MagicMock(), changelog=MagicMock(), message=MagicMock(), info_upgrade=MagicMock(),
        www=MagicMock(), cmd=MagicMock(), download_file=MagicMock(), download_link="",
        cmd_snap="snap cmd", cmd_appimage="appimage cmd", cmd_pip="pip cmd",
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


def test_set_data_no_update_hides_upgrade_and_download_controls():
    widget = _dialog()
    _set(widget, is_new=False)

    widget.info.setText.assert_called_once_with("update.info.none")
    widget.changelog.setPlainText.assert_called_once_with("changes")
    widget.info_upgrade.setVisible.assert_called_with(False)
    widget.cmd.setVisible.assert_called_once_with(False)
    widget.download_file.setVisible.assert_called_once_with(False)


def test_set_data_snap_uses_snap_command():
    widget = _dialog(is_snap=True)
    _set(widget)
    widget.cmd.setText.assert_called_once_with("snap cmd")
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
    widget.www.setVisible.assert_called_with(False)


def test_set_data_compiled_linux_configures_tarball_download():
    widget = _dialog(compiled=True, linux=True)
    _set(widget)
    assert widget.download_link == "linux"
    widget.download_file.setText.assert_called_once_with("action.download .tar.gz (3.0)")
    widget.download_file.setVisible.assert_called_with(True)


def test_set_data_appimage_uses_appimage_command_and_download():
    widget = _dialog(appimage=True)
    _set(widget)
    widget.cmd.setText.assert_called_once_with("appimage cmd")
    widget.cmd.setVisible.assert_called_with(True)
    assert widget.download_link == "appimage"
    widget.download_file.setText.assert_called_once_with("action.download .AppImage (3.0)")


def test_set_data_python_package_uses_pip_command():
    widget = _dialog()
    _set(widget)
    widget.cmd.setText.assert_called_once_with("pip cmd")
    widget.cmd.setVisible.assert_called_with(True)
