from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt

from pygpt_net.tools.media_player.ui.widgets import VideoPlayerWidget


def test_video_player_format_time_handles_hours_minutes_seconds():
    widget = SimpleNamespace()
    assert VideoPlayerWidget.format_time(widget, 0) == "00:00:00"
    assert VideoPlayerWidget.format_time(widget, 3_661_000) == "01:01:01"
    assert VideoPlayerWidget.format_time(widget, 90_000) == "00:01:30"


def test_video_player_duration_and_slider_value_update_labels():
    widget = SimpleNamespace(
        slider=MagicMock(), label_duration=MagicMock(), label_time=MagicMock(), seeking=True,
        format_time=lambda ms: f"T{ms}",
    )
    VideoPlayerWidget.duration_changed(widget, 1200)
    widget.slider.setRange.assert_called_once_with(0, 1200)
    widget.label_duration.setText.assert_called_once_with("T1200")

    VideoPlayerWidget.on_slider_value_changed(widget, 500)
    widget.label_time.setText.assert_called_once_with("T500")


def test_video_player_set_muted_updates_audio_and_config():
    audio = MagicMock(); config = MagicMock()
    widget = SimpleNamespace(audio=audio, window=SimpleNamespace(core=SimpleNamespace(config=config)))
    VideoPlayerWidget.set_muted(widget, True)
    audio.setMuted.assert_called_once_with(True)
    config.set.assert_called_once_with("video.player.volume.mute", True)


def test_video_player_set_position_pauses_playing_player_then_sets_position():
    player = MagicMock(); media = MagicMock()
    media.PlayingState = object(); player.playbackState.return_value = media.PlayingState
    widget = SimpleNamespace(player=player, _QMediaPlayer=media, _waiting_position_set=False)
    VideoPlayerWidget.set_position(widget, 123)
    player.pause.assert_called_once_with()
    player.setPosition.assert_called_once_with(123)
    assert widget._waiting_position_set is True


def test_video_player_slider_press_release_and_position_changed():
    player = MagicMock(); slider = MagicMock(); slider.value.return_value = 777
    label = MagicMock(); media = MagicMock(); media.PausedState = object()
    player.playbackState.return_value = media.PausedState
    widget = SimpleNamespace(
        seeking=False, _waiting_position_set=False, player=player, slider=slider,
        update_audio=MagicMock(), _QMediaPlayer=media, _last_position=0,
        label_time=label, format_time=lambda ms: str(ms),
    )

    VideoPlayerWidget.on_slider_pressed(widget)
    assert widget.seeking is True
    player.pause.assert_called_once_with()

    with patch("pygpt_net.tools.media_player.ui.widgets.QTimer.singleShot") as timer:
        VideoPlayerWidget.on_slider_released(widget)
    player.setPosition.assert_called_with(777)
    widget.update_audio.assert_called_once_with()
    timer.assert_called_once()
    assert widget.seeking is False

    widget._waiting_position_set = True
    player.reset_mock(); player.playbackState.return_value = media.PausedState
    with patch("pygpt_net.tools.media_player.ui.widgets.QTimer.singleShot") as timer:
        VideoPlayerWidget.position_changed(widget, 900)
    assert widget._waiting_position_set is False
    timer.assert_called_once()
    slider.setValue.assert_called_with(900)
    label.setText.assert_called_with("900")


def test_video_player_update_label_path_and_audio_reassignment():
    label = MagicMock(); player = MagicMock(); audio = object()
    player.audioOutput.return_value = object()
    widget = SimpleNamespace(path="/tmp/movie.mp4", label_path=label, player=player, audio=audio)
    VideoPlayerWidget.update_label_path(widget)
    label.setText.assert_called_once_with("movie.mp4")
    VideoPlayerWidget.update_audio(widget)
    player.setAudioOutput.assert_called_once_with(audio)

    widget.path = None
    VideoPlayerWidget.update_label_path(widget)
    label.setText.assert_called_with("")


def test_video_player_mute_and_volume_ui_updates_block_signals():
    audio = MagicMock(); mute = MagicMock(); volume = MagicMock()
    audio.isMuted.return_value = True
    mute.isChecked.return_value = False
    mute.blockSignals.return_value = "old"
    audio.volume.return_value = 0.42
    volume.value.return_value = 10
    volume.blockSignals.return_value = "old-volume"
    widget = SimpleNamespace(audio=audio, btn_mute=mute, volume_slider=volume)

    VideoPlayerWidget.update_mute_icon(widget)
    mute.setChecked.assert_called_once_with(True)
    assert mute.blockSignals.call_args_list[-1].args == ("old",)

    VideoPlayerWidget.update_volume_slider(widget)
    volume.setValue.assert_called_once_with(42)
    assert volume.blockSignals.call_args_list[-1].args == ("old-volume",)


def test_video_player_update_ui_only_changes_when_position_changes_and_not_seeking():
    player = MagicMock(); player.position.return_value = 100
    slider = MagicMock(); label = MagicMock()
    widget = SimpleNamespace(
        player=player, seeking=False, _last_position=0,
        slider=slider, label_time=label, format_time=lambda ms: f"{ms}",
    )
    VideoPlayerWidget.update_ui(widget)
    assert widget._last_position == 100
    slider.setValue.assert_called_once_with(100)
    label.setText.assert_called_once_with("100")

    slider.reset_mock(); widget.seeking = True; player.position.return_value = 200
    VideoPlayerWidget.update_ui(widget)
    slider.setValue.assert_not_called()


def test_video_player_adjust_volume_persists_percent_and_updates_audio():
    audio = MagicMock()
    config = MagicMock()
    widget = SimpleNamespace(audio=audio, window=SimpleNamespace(core=SimpleNamespace(config=config)))

    VideoPlayerWidget.adjust_volume(widget, 25)

    config.set.assert_called_once_with("video.player.volume", 25)
    audio.setVolume.assert_called_once_with(0.25)


def test_video_player_enable_stop_and_reset_manage_controls_and_state():
    player = MagicMock()
    player.source.return_value = object()
    slider = MagicMock()
    label = MagicMock()
    timer = MagicMock()
    play_btn = MagicMock()
    stop_btn = MagicMock()
    icon = object()
    widget = SimpleNamespace(
        player=player,
        btn_play_pause=play_btn,
        btn_stop=stop_btn,
        slider=slider,
        label_time=label,
        update_timer=timer,
        _icon_play=icon,
        format_time=lambda ms: f"T{ms}",
        seeking=True,
        loaded=True,
        stopped=False,
        _waiting_position_set=True,
        _last_position=100,
    )

    VideoPlayerWidget.enable(widget)
    play_btn.setEnabled.assert_called_once_with(True)
    stop_btn.setEnabled.assert_called_once_with(True)

    VideoPlayerWidget.stop_video(widget)
    player.stop.assert_called_once_with()
    assert widget.stopped is True
    slider.setValue.assert_called_with(0)
    label.setText.assert_called_once_with("T0")
    play_btn.setIcon.assert_called_with(icon)
    timer.stop.assert_called_once_with()

    player.reset_mock(); slider.reset_mock(); timer.reset_mock(); play_btn.reset_mock()
    with patch("pygpt_net.tools.media_player.ui.widgets.QUrl", return_value="empty-url"):
        VideoPlayerWidget.reset(widget)
    player.stop.assert_called_once_with()
    player.setSource.assert_called_once_with("empty-url")
    assert widget.seeking is False
    assert widget.loaded is False
    assert widget._waiting_position_set is False
    assert widget._last_position == -1


def test_video_player_play_video_reopens_unloaded_path_or_plays_loaded_media():
    widget = SimpleNamespace(
        loaded=False,
        path="/tmp/a.mp4",
        stopped=True,
        open=MagicMock(),
        _ensure_multimedia=MagicMock(),
        update_audio=MagicMock(),
        player=MagicMock(),
    )
    VideoPlayerWidget.play_video(widget)
    assert widget.stopped is False
    widget.open.assert_called_once_with("/tmp/a.mp4")
    widget.player.play.assert_not_called()

    widget.open.reset_mock(); widget.loaded = True
    VideoPlayerWidget.play_video(widget)
    widget._ensure_multimedia.assert_called_once_with()
    widget.update_audio.assert_called_once_with()
    widget.player.play.assert_called_once_with()


def test_video_player_toggle_play_pause_pauses_playing_or_delegates_play():
    media = SimpleNamespace(PlayingState="playing")
    player = MagicMock()
    widget = SimpleNamespace(
        player=player,
        _QMediaPlayer=media,
        play_video=MagicMock(),
        on_playback_state_changed=MagicMock(),
    )
    player.playbackState.return_value = "playing"
    VideoPlayerWidget.toggle_play_pause(widget)
    player.pause.assert_called_once_with()
    widget.play_video.assert_not_called()

    player.pause.reset_mock(); player.playbackState.return_value = "paused"
    VideoPlayerWidget.toggle_play_pause(widget)
    widget.play_video.assert_called_once_with()
    widget.on_playback_state_changed.assert_called_with()


def test_video_player_use_frame_as_attachment_or_image():
    player_tool = MagicMock()
    player_tool.grab_frame.return_value = "/tmp/frame.png"
    tools = MagicMock(); tools.get.return_value = player_tool
    files = MagicMock(); painter = MagicMock()
    widget = SimpleNamespace(
        window=SimpleNamespace(
            tools=tools,
            controller=SimpleNamespace(files=files, painter=painter),
        )
    )

    VideoPlayerWidget.use_as_attachment(widget)
    files.use_attachment.assert_called_once_with("/tmp/frame.png")
    VideoPlayerWidget.use_as_image(widget)
    painter.open_external.assert_called_once_with("/tmp/frame.png")


def test_video_player_toggle_fullscreen_switches_dialog_state():
    dialog = MagicMock()
    widget = SimpleNamespace(window=SimpleNamespace(ui=SimpleNamespace(dialog={"video_player": dialog})))
    dialog.isFullScreen.return_value = True
    VideoPlayerWidget.toggle_fullscreen(widget)
    dialog.showNormal.assert_called_once_with()

    dialog.reset_mock(); dialog.isFullScreen.return_value = False
    VideoPlayerWidget.toggle_fullscreen(widget)
    dialog.showFullScreen.assert_called_once_with()


def test_video_player_media_status_handles_loaded_and_invalid_states():
    media = SimpleNamespace(LoadedMedia="loaded", InvalidMedia="invalid")
    dialogs = MagicMock()
    widget = SimpleNamespace(
        _QMediaPlayer=media,
        loaded=False,
        force_resize=MagicMock(),
        window=SimpleNamespace(ui=SimpleNamespace(dialogs=dialogs)),
    )

    VideoPlayerWidget.media_status_changed(widget, "loaded")
    assert widget.loaded is True
    widget.force_resize.assert_called_once_with()

    widget.force_resize.reset_mock()
    VideoPlayerWidget.media_status_changed(widget, "invalid")
    assert widget.loaded is False
    dialogs.alert.assert_called_once()


def test_video_player_after_loaded_starts_paused_media_and_resizes():
    media = SimpleNamespace(LoadedMedia="loaded", PlayingState="playing")
    player = MagicMock()
    player.mediaStatus.return_value = "loaded"
    player.playbackState.return_value = "paused"
    widget = SimpleNamespace(
        player=player,
        _QMediaPlayer=media,
        loaded=False,
        toggle_play_pause=MagicMock(),
        force_resize=MagicMock(),
    )

    VideoPlayerWidget.after_loaded(widget)

    assert widget.loaded is True
    widget.toggle_play_pause.assert_called_once_with()
    widget.force_resize.assert_called_once_with()


def test_video_player_clicked_toggles_only_loaded_left_click():
    widget = SimpleNamespace(loaded=True, toggle_play_pause=MagicMock())
    event = SimpleNamespace(button=MagicMock(return_value=Qt.LeftButton))
    VideoPlayerWidget.video_widget_clicked(widget, event)
    widget.toggle_play_pause.assert_called_once_with()

    widget.toggle_play_pause.reset_mock(); widget.loaded = False
    VideoPlayerWidget.video_widget_clicked(widget, event)
    widget.toggle_play_pause.assert_not_called()


def test_video_player_update_play_pause_icon_tracks_playback_and_timer():
    media = SimpleNamespace(PlayingState="playing")
    player = MagicMock(); button = MagicMock(); timer = MagicMock()
    timer.isActive.return_value = False
    widget = SimpleNamespace(
        player=player,
        _QMediaPlayer=media,
        btn_play_pause=button,
        _icon_pause="pause-icon",
        _icon_play="play-icon",
        update_timer=timer,
    )

    player.playbackState.return_value = "playing"
    VideoPlayerWidget.update_play_pause_icon(widget)
    button.setIcon.assert_called_with("pause-icon")
    timer.start.assert_called_once_with()

    button.reset_mock(); timer.reset_mock(); timer.isActive.return_value = True
    player.playbackState.return_value = "paused"
    VideoPlayerWidget.update_play_pause_icon(widget)
    button.setIcon.assert_called_with("play-icon")
    timer.stop.assert_called_once_with()
