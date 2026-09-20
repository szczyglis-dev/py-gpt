import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.tools.audio_transcriber.tool import AudioTranscriber


def _tool(tmp_path):
    tool = AudioTranscriber()
    nodes = {
        "audio.transcribe.status": MagicMock(),
        "audio.transcribe.convert_video": MagicMock(),
    }
    editor = MagicMock()
    config = MagicMock()
    config.get_user_dir.side_effect = lambda kind: str(tmp_path)
    config.get_user_path.return_value = str(tmp_path)
    window = SimpleNamespace(
        ui=SimpleNamespace(nodes=nodes, editor={"audio.transcribe": editor}, dialogs=MagicMock()),
        core=SimpleNamespace(config=config, debug=MagicMock()),
        controller=SimpleNamespace(
            command=MagicMock(),
            chat=SimpleNamespace(common=MagicMock()),
        ),
    )
    tool.window = window
    return tool


def test_audio_transcriber_defaults_setup_and_video_detection(tmp_path):
    tool = _tool(tmp_path)
    tool.restore = MagicMock()
    tool.restore_auto_convert = MagicMock()

    tool.setup()
    tool.restore.assert_called_once_with()
    tool.restore_auto_convert.assert_called_once_with()
    assert tool.id == "transcriber"
    assert tool.is_video("movie.MP4") is True
    assert tool.is_video("track.mp3") is False


def test_audio_transcriber_open_file_transcribes_only_selected_path(tmp_path):
    tool = _tool(tmp_path)
    tool.transcribe = MagicMock()

    with patch("pygpt_net.tools.audio_transcriber.tool.QFileDialog.getOpenFileName", return_value=("/tmp/a.mp3", "")):
        tool.open_file()
    tool.transcribe.assert_called_once_with("/tmp/a.mp3")

    tool.transcribe.reset_mock()
    with patch("pygpt_net.tools.audio_transcriber.tool.QFileDialog.getOpenFileName", return_value=("", "")):
        tool.open_file()
    tool.transcribe.assert_not_called()


def test_audio_transcriber_save_as_file_delegates_plain_text(tmp_path):
    tool = _tool(tmp_path)
    tool.window.ui.editor["audio.transcribe"].toPlainText.return_value = "hello"
    tool.save_as_file()
    tool.window.controller.chat.common.save_text.assert_called_once_with("hello")


def test_audio_transcriber_from_file_opens_sets_basename_and_transcribes(tmp_path):
    tool = _tool(tmp_path)
    tool.open = MagicMock()
    tool.transcribe = MagicMock()

    with patch("pygpt_net.tools.audio_transcriber.tool.trans", return_value="selected {path}"):
        tool.from_file("/x/y/input.wav")

    tool.open.assert_called_once_with()
    tool.window.ui.nodes["audio.transcribe.status"].setText.assert_called_once_with("selected input.wav")
    tool.transcribe.assert_called_once_with("/x/y/input.wav")


def test_audio_transcriber_open_close_toggle_show_hide(tmp_path):
    tool = _tool(tmp_path)
    tool.update = MagicMock()

    tool.open()
    tool.window.ui.nodes["audio.transcribe.status"].setText.assert_called_with("")
    tool.window.ui.dialogs.open.assert_called_once_with("audio.transcribe", width=800, height=600)
    assert tool.opened is True

    tool.close()
    tool.window.ui.dialogs.close.assert_called_once_with("audio.transcribe")
    assert tool.opened is False

    tool.open = MagicMock(); tool.close = MagicMock(); tool.opened = False
    tool.toggle(); tool.open.assert_called_once_with()
    tool.opened = True; tool.toggle(); tool.close.assert_called_once_with()
    tool.open.reset_mock(); tool.close.reset_mock()
    tool.show_hide(True); tool.show_hide(False)
    tool.open.assert_called_once_with(); tool.close.assert_called_once_with()


def test_audio_transcriber_transcribe_requires_confirmation_without_force(tmp_path):
    tool = _tool(tmp_path)
    with patch("pygpt_net.tools.audio_transcriber.tool.trans", return_value="confirm"):
        tool.transcribe("/tmp/a.wav")
    tool.window.ui.dialogs.confirm.assert_called_once_with(type="audio.transcribe", id="/tmp/a.wav", msg="confirm")
    tool.window.controller.command.dispatch_only.assert_not_called()


def test_audio_transcriber_transcribe_dispatches_event_after_preparation(tmp_path):
    tool = _tool(tmp_path)
    tool.prepare_audio = MagicMock(return_value="/tmp/prepared.mp3")
    tool.clear = MagicMock()

    tool.transcribe("/tmp/video.mp4", force=True)

    tool.clear.assert_called_once_with(force=True)
    event = tool.window.controller.command.dispatch_only.call_args.args[0]
    assert event.data["path"] == "/tmp/prepared.mp3"
    assert event.ctx is not None
    tool.window.ui.nodes["audio.transcribe.status"].setText.assert_called_once_with(
        "Transcribing: prepared.mp3 ... Please wait..."
    )


def test_audio_transcriber_transcribe_aborts_when_prepare_audio_fails(tmp_path):
    tool = _tool(tmp_path)
    tool.prepare_audio = MagicMock(return_value=None)
    tool.transcribe("/tmp/video.mp4", force=True)
    tool.window.controller.command.dispatch_only.assert_not_called()


def test_audio_transcriber_on_transcribe_stores_and_updates_editor(tmp_path):
    tool = _tool(tmp_path)
    tool.store = MagicMock()
    with patch("pygpt_net.tools.audio_transcriber.tool.trans", return_value="finished {path}"):
        tool.on_transcribe("/tmp/a.wav", "text")
    tool.store.assert_called_once_with("text")
    tool.window.ui.nodes["audio.transcribe.status"].setText.assert_called_once_with("finished a.wav")
    tool.window.ui.editor["audio.transcribe"].setPlainText.assert_called_once_with("text")


def test_audio_transcriber_prepare_audio_returns_original_for_non_video_or_disabled(tmp_path):
    tool = _tool(tmp_path)
    tool.is_auto_convert = MagicMock(return_value=True)
    assert tool.prepare_audio("/tmp/a.wav") == "/tmp/a.wav"

    tool.is_auto_convert.return_value = False
    assert tool.prepare_audio("/tmp/a.mp4") == "/tmp/a.mp4"


def test_audio_transcriber_prepare_audio_mocks_pydub_and_replaces_existing_temp_file(tmp_path):
    tool = _tool(tmp_path)
    tool.is_auto_convert = MagicMock(return_value=True)
    target = tmp_path / "transcript.mp3"
    target.write_bytes(b"old")

    mono = MagicMock()
    video = MagicMock()
    video.split_to_mono.return_value = [mono]
    audio_segment = MagicMock()
    audio_segment.from_file.return_value = video

    with patch.dict(sys.modules, {"pydub": SimpleNamespace(AudioSegment=audio_segment)}):
        result = tool.prepare_audio("/tmp/movie.MP4")

    assert result == str(target)
    audio_segment.from_file.assert_called_once_with("/tmp/movie.MP4", format="mp4")
    mono.export.assert_called_once_with(str(target), format="mp3")
    assert not target.exists()  # old file was removed before mocked export


def test_audio_transcriber_prepare_audio_handles_conversion_exception(tmp_path):
    tool = _tool(tmp_path)
    tool.is_auto_convert = MagicMock(return_value=True)
    audio_segment = MagicMock()
    audio_segment.from_file.side_effect = RuntimeError("ffmpeg missing")

    with patch.dict(sys.modules, {"pydub": SimpleNamespace(AudioSegment=audio_segment)}):
        result = tool.prepare_audio("/tmp/movie.mp4")

    assert result is None
    tool.window.core.debug.log.assert_called_once()
    tool.window.ui.dialogs.alert.assert_called_once()
    status = tool.window.ui.nodes["audio.transcribe.status"].setText.call_args.args[0]
    assert "Can't convert video to mp3" in status


def test_audio_transcriber_auto_convert_setting_round_trip(tmp_path):
    tool = _tool(tmp_path)
    checkbox = tool.window.ui.nodes["audio.transcribe.convert_video"]
    checkbox.isChecked.return_value = True

    tool.toggle_auto_convert()
    tool.window.core.config.set.assert_called_once_with("audio.transcribe.convert_video", True)
    tool.window.core.config.save.assert_called_once_with()
    assert tool.is_auto_convert() is True

    tool.window.core.config.has.return_value = True
    tool.window.core.config.get.return_value = False
    tool.restore_auto_convert()
    checkbox.setChecked.assert_called_once_with(False)


def test_audio_transcriber_store_restore_and_store_current_use_tmp_dir(tmp_path):
    tool = _tool(tmp_path)
    tool.store("hello")
    path = tmp_path / "transcript.txt"
    assert path.read_text(encoding="utf-8") == "hello"

    tool.window.ui.editor["audio.transcribe"].toPlainText.return_value = "current"
    tool.store_current()
    assert path.read_text(encoding="utf-8") == "current"

    path.write_text("restored", encoding="utf-8")
    tool.restore()
    tool.window.ui.editor["audio.transcribe"].setPlainText.assert_called_with("restored")


def test_audio_transcriber_on_close_exit_and_clear(tmp_path):
    tool = _tool(tmp_path)
    tool.update = MagicMock()
    tool.on_close()
    assert tool.opened is False
    tool.update.assert_called_once_with()

    tool.store_current = MagicMock()
    tool.on_exit()
    tool.store_current.assert_called_once_with()

    with patch("pygpt_net.tools.audio_transcriber.tool.trans", return_value="confirm"):
        tool.clear()
    tool.window.ui.dialogs.confirm.assert_called_with(type="audio.transcribe.clear", id=0, msg="confirm")

    tool.store = MagicMock()
    tool.clear(force=True)
    tool.window.ui.editor["audio.transcribe"].clear.assert_called_once_with()
    tool.window.ui.nodes["audio.transcribe.status"].setText.assert_called_with("")
    tool.store.assert_called_once_with("")


def test_audio_transcriber_setup_dialogs_and_lang_mappings(tmp_path):
    tool = _tool(tmp_path)
    dialog = MagicMock()
    with patch("pygpt_net.tools.audio_transcriber.tool.AudioTranscribe", return_value=dialog):
        tool.setup_dialogs()
    assert tool.dialog is dialog
    dialog.setup.assert_called_once_with()
    assert tool.get_lang_mappings()["menu.text"]["tools.audio.transcribe"] == "menu.tools.audio.transcribe"
