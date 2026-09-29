from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.tools.media_player.tool import MediaPlayer


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 6, 23, 45, 7)


def _tool():
    tool = MediaPlayer()
    config = MagicMock()
    filesystem = MagicMock()
    player = MagicMock()
    window = SimpleNamespace(
        core=SimpleNamespace(config=config, filesystem=filesystem),
        controller=SimpleNamespace(painter=SimpleNamespace(common=MagicMock())),
        ui=SimpleNamespace(dialogs=MagicMock()),
        video_player=player,
    )
    tool.window = window
    return tool


def test_media_player_defaults_and_lazy_setup_noop_when_initialized():
    tool = _tool()
    assert tool.id == "player"
    assert tool.initialized is False
    tool.initialized = True
    tool.lazy_setup()
    tool.window.core.config.has.assert_not_called()


def test_media_player_lazy_setup_restores_path_volume_mute_and_updates():
    tool = _tool()
    config = tool.window.core.config
    config.has.return_value = True
    config.get.side_effect = lambda key: {
        "video.player.path": "relative.mp4",
        "video.player.volume": 73,
        "video.player.volume.mute": True,
    }[key]
    tool.window.core.filesystem.to_workdir.return_value = "/work/relative.mp4"

    with patch("pygpt_net.tools.media_player.tool.os.path.exists", return_value=True):
        tool.lazy_setup()

    tool.window.video_player.set_path.assert_called_once_with("/work/relative.mp4")
    tool.window.video_player.adjust_volume.assert_called_once_with(73)
    tool.window.video_player.set_muted.assert_called_once_with(True)
    tool.window.video_player.update.assert_called_once_with()
    assert tool.initialized is True


def test_media_player_lazy_setup_skips_missing_stored_path():
    tool = _tool()
    config = tool.window.core.config
    config.has.side_effect = lambda key: key == "video.player.path"
    config.get.return_value = "missing.mp4"
    tool.window.core.filesystem.to_workdir.return_value = "/work/missing.mp4"
    with patch("pygpt_net.tools.media_player.tool.os.path.exists", return_value=False):
        tool.lazy_setup()
    tool.window.video_player.set_path.assert_not_called()
    tool.window.video_player.update.assert_called_once_with()


def test_media_player_update_delegates_menu_and_store_path_localizes():
    tool = _tool()
    tool.update_menu = MagicMock()
    tool.update()
    tool.update_menu.assert_called_once_with()

    tool.window.core.filesystem.make_local.return_value = "local/video.mp4"
    tool.store_path("/work/video.mp4")
    tool.window.core.config.set.assert_called_once_with("video.player.path", "local/video.mp4")


def test_media_player_play_open_file_and_open():
    tool = _tool()
    tool.update = MagicMock()
    tool.play("/tmp/a.mp4")
    tool.window.ui.dialogs.open.assert_called_once_with("video_player", width=800, height=600)
    tool.window.video_player.force_resize.assert_called_once_with()
    tool.window.video_player.open.assert_called_once_with("/tmp/a.mp4")
    assert tool.opened is True

    tool.open_file()
    tool.window.video_player.open_file.assert_called_once_with()

    tool.window.ui.dialogs.open.reset_mock(); tool.window.video_player.force_resize.reset_mock()
    tool.lazy_setup = MagicMock()
    tool.open()
    tool.lazy_setup.assert_called_once_with()
    tool.window.ui.dialogs.open.assert_called_once_with("video_player", width=800, height=600)
    tool.window.video_player.force_resize.assert_called_once_with()
    assert tool.opened is True


def test_media_player_grab_frame_uses_deterministic_timestamp():
    tool = _tool()
    tool.window.controller.painter.common.get_capture_dir.return_value = "/captures"
    with patch("pygpt_net.tools.media_player.tool.datetime.datetime", _FixedDateTime):
        path = tool.grab_frame()
    assert path.endswith("/captures/cap-2026-09-06_23-45-07.png")


def test_media_player_save_as_file_warns_without_video():
    tool = _tool()
    tool.window.video_player.path = None
    with patch("pygpt_net.tools.media_player.tool.QMessageBox.warning") as warning:
        tool.save_as_file()
    warning.assert_called_once_with(tool.window.video_player, "Save Error", "No video loaded.")


def test_media_player_save_as_file_copies_selected_path_and_reports_success():
    tool = _tool()
    tool.window.video_player.path = "/src/a.mp4"
    with patch("pygpt_net.tools.media_player.tool.QFileDialog.getSaveFileName", return_value=("/dst/b.mp4", "")), \
            patch("pygpt_net.tools.media_player.tool.shutil.copy2") as copy2, \
            patch("pygpt_net.tools.media_player.tool.QMessageBox.information") as info:
        tool.save_as_file()
    copy2.assert_called_once_with("/src/a.mp4", "/dst/b.mp4")
    info.assert_called_once()
    assert "/dst/b.mp4" in info.call_args.args[2]


def test_media_player_save_as_file_reports_copy_error():
    tool = _tool()
    tool.window.video_player.path = "/src/a.mp4"
    with patch("pygpt_net.tools.media_player.tool.QFileDialog.getSaveFileName", return_value=("/dst/b.mp4", "")), \
            patch("pygpt_net.tools.media_player.tool.shutil.copy2", side_effect=OSError("denied")), \
            patch("pygpt_net.tools.media_player.tool.QMessageBox.critical") as critical:
        tool.save_as_file()
    assert "denied" in critical.call_args.args[2]


def test_media_player_close_on_close_toggle_and_show_hide():
    tool = _tool()
    tool.update = MagicMock()
    tool.on_close = MagicMock()
    tool.opened = True
    tool.close()
    tool.on_close.assert_called_once_with()
    tool.window.ui.dialogs.close.assert_called_once_with("video_player")
    assert tool.opened is False

    tool.on_close = MediaPlayer.on_close.__get__(tool, MediaPlayer)
    tool.opened = True
    tool.on_close()
    assert tool.opened is False
    tool.window.video_player.on_close.assert_called_once_with()

    tool.open = MagicMock(); tool.close = MagicMock(); tool.opened = False
    tool.toggle(); tool.open.assert_called_once_with()
    tool.opened = True; tool.toggle(); tool.close.assert_called_once_with()
    tool.open.reset_mock(); tool.close.reset_mock()
    tool.show_hide(True); tool.show_hide(False)
    tool.open.assert_called_once_with(); tool.close.assert_called_once_with()


def test_media_player_setup_dialogs_and_lang_mappings():
    tool = _tool()
    dialog = MagicMock()
    with patch("pygpt_net.tools.media_player.tool.VideoPlayer", return_value=dialog):
        tool.setup_dialogs()
    assert tool.dialog is dialog
    dialog.setup.assert_called_once_with()
    assert tool.get_lang_mappings() == {
        "menu.text": {"tools.media.player": "menu.tools.media.player"}
    }
