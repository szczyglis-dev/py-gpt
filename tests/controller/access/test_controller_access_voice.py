from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.access.voice import Voice
from pygpt_net.core.events import AppEvent, ControlEvent


def _voice():
    ctrl = Voice.__new__(Voice)
    ctrl.window = MagicMock()
    ctrl.is_recording = False
    ctrl.timer = None
    ctrl.input_file = 'voice_control.wav'
    ctrl.thread_started = False
    ctrl.audio_disabled_events = [AppEvent.INPUT_CALL, AppEvent.VOICE_CONTROL_TOGGLE]
    ctrl.confirm_events = [ControlEvent.NOTEPAD_CLEAR, ControlEvent.CALENDAR_CLEAR]
    ctrl.pending_text = None
    ctrl.pending_event = None
    ctrl.play_timer = MagicMock()
    ctrl.window.ui.nodes = {'voice.control.btn': MagicMock()}
    return ctrl, ctrl.window


def test_voice_input_path_uses_configured_tmp_directory_not_cwd():
    ctrl, window = _voice()
    window.core.config.get_user_dir.return_value = '/tmp/pygpt'
    assert ctrl.get_input_path() == '/tmp/pygpt/voice_control.wav'


def test_voice_delayed_play_and_play_audio_use_timer_and_audio_controller():
    ctrl, window = _voice()
    event = AppEvent(AppEvent.APP_STARTED)
    ctrl.delayed_play('hello', event)
    ctrl.play_timer.start.assert_called_once_with(ctrl.PLAY_DELAY)
    ctrl.play_audio()
    ctrl.play_timer.stop.assert_called_once_with()
    window.controller.audio.play_event.assert_called_once_with('hello', event)
    assert ctrl.pending_text is None
    assert ctrl.pending_event is None


def test_voice_play_selected_context_uses_access_helper_and_delayed_speech():
    ctrl, window = _voice()
    window.core.config.get.side_effect = lambda key, *a: key == 'access.audio.event.speech'
    window.core.access.helpers.get_selected_ctx.return_value = 'Context 1'
    ctrl.delayed_play = MagicMock()
    event = AppEvent(AppEvent.CTX_SELECTED)
    ctrl.play(event)
    ctrl.delayed_play.assert_called_once_with('Context 1', event)


def test_voice_microphone_notification_uses_sound_without_speech():
    ctrl, window = _voice()
    values = {
        'access.microphone.notify': True,
        'access.audio.notify.execute': True,
        'access.audio.event.speech': False,
    }
    window.core.config.get.side_effect = lambda key, *args: values.get(key, False)
    ctrl.play(AppEvent(AppEvent.VOICE_CONTROL_STARTED))
    window.controller.audio.play_sound.assert_called_once_with('click_on.mp3')


def test_voice_update_and_enable_disable_toggle_configuration():
    ctrl, window = _voice()
    window.core.config.get.return_value = True
    ctrl.update()
    window.ui.nodes['voice.control.btn'].setVisible.assert_called_with(True)
    window.controller.audio.update.assert_called_once_with()

    ctrl.update = MagicMock()
    ctrl.enable_voice_control()
    window.core.config.set.assert_called_with('access.voice_control', True)
    window.core.config.save.assert_called()
    ctrl.update.assert_called()

    ctrl.update.reset_mock()
    ctrl.disable_voice_control()
    window.core.config.set.assert_called_with('access.voice_control', False)
    ctrl.update.assert_called()


def test_voice_toggle_recording_selects_start_or_stop():
    ctrl, _ = _voice()
    ctrl.start_recording = MagicMock()
    ctrl.stop_recording = MagicMock()
    ctrl.toggle_recording()
    ctrl.start_recording.assert_called_once_with()
    ctrl.is_recording = True
    ctrl.toggle_recording()
    ctrl.stop_recording.assert_called_once_with()


def test_voice_start_recording_mocks_qtimer_and_audio_capture():
    ctrl, window = _voice()
    window.core.config.get.side_effect = lambda key, default=None: {
        'audio.input.snap': True,
        'audio.input.timeout': 2,
    }.get(key, default)
    window.core.config.has.return_value = True
    window.core.platforms.is_snap.return_value = False
    window.core.audio.capture.check_audio_input.return_value = True
    timer = MagicMock()
    with patch('pygpt_net.controller.access.voice.QTimer', return_value=timer):
        ctrl.start_recording()
    assert ctrl.is_recording is True
    timer.start.assert_called_once_with(2000)
    window.core.audio.capture.set_mode.assert_called_once_with('control')
    window.core.audio.capture.start.assert_called_once_with()
    window.dispatch.assert_called_once()


def test_voice_start_recording_handles_capture_failure_without_throwing():
    ctrl, window = _voice()
    window.core.config.get.side_effect = lambda key, default=None: {
        'audio.input.snap': True,
        'audio.input.timeout': 0,
    }.get(key, default)
    window.core.config.has.return_value = True
    window.core.platforms.is_snap.return_value = False
    window.core.audio.capture.check_audio_input.return_value = False
    ctrl.start_recording()
    assert ctrl.is_recording is False
    window.core.debug.log.assert_called_once()
    window.ui.dialogs.alert.assert_called_once()


def test_voice_stop_recording_timeout_does_not_start_transcription():
    ctrl, window = _voice()
    window.core.config.get_user_dir.return_value = '/tmp'
    window.core.audio.capture.has_source.return_value = True
    ctrl.handle_thread = MagicMock()
    ctrl.stop_recording(timeout=True)
    window.core.audio.capture.stop.assert_called_once_with()
    ctrl.handle_thread.assert_not_called()
    window.dispatch.assert_called_once()


def test_voice_stop_recording_valid_frames_starts_mocked_transcription_worker_path():
    ctrl, window = _voice()
    window.core.config.get_user_dir.return_value = '/tmp'
    window.core.audio.capture.has_source.return_value = True
    window.core.audio.capture.has_frames.return_value = True
    window.core.audio.capture.has_min_frames.return_value = True
    ctrl.handle_thread = MagicMock()
    ctrl.stop_recording(False)
    ctrl.handle_thread.assert_called_once_with(True)


def test_voice_handle_thread_uses_control_worker_mock_not_real_audio_backend():
    ctrl, window = _voice()
    window.core.config.get_user_dir.return_value = '/tmp'
    worker = MagicMock()
    worker.signals = MagicMock()
    with patch('pygpt_net.controller.access.voice.ControlWorker', return_value=worker):
        ctrl.handle_thread(True)
    assert worker.window is window
    assert worker.path == '/tmp/voice_control.wav'
    window.threadpool.start.assert_called_once_with(worker)


def test_voice_handle_input_skips_blank_and_dispatches_recognized_commands():
    ctrl, window = _voice()
    ctrl.handle_commands = MagicMock()
    ctrl.handle_input('   ')
    ctrl.handle_commands.assert_not_called()
    window.core.access.voice.recognize_commands.return_value = [{'cmd': 'ctx.new'}]
    ctrl.handle_input('new chat')
    ctrl.handle_commands.assert_called_once_with([{'cmd': 'ctx.new'}])


def test_voice_handle_commands_dispatches_control_events_and_ok_sound():
    ctrl, window = _voice()
    window.core.config.get.return_value = True
    with patch('pygpt_net.controller.access.voice.QApplication.processEvents'), \
         patch('pygpt_net.controller.access.voice.trans', side_effect=lambda key: key):
        ctrl.handle_commands([{'cmd': 'ctx.new', 'params': 'x'}])
    event = window.dispatch.call_args.args[0]
    assert isinstance(event, ControlEvent)
    assert event.data == {'params': 'x'}
    window.controller.audio.play_sound.assert_called_once_with('ok.mp3')


def test_voice_thread_signal_helpers_update_flags_and_status():
    ctrl, window = _voice()
    ctrl.handle_started()
    assert ctrl.thread_started is True
    ctrl.handle_stop()
    assert ctrl.thread_started is False
    ctrl.handle_started()
    ctrl.handle_destroy()
    assert ctrl.thread_started is False
    ctrl.handle_error('err')
    ctrl.handle_status('status')
    assert window.update_status.call_args_list[-2].args == ('err',)
    assert window.update_status.call_args_list[-1].args == ('status',)


def test_voice_remaining_small_helpers_delegate():
    ctrl, window = _voice()
    ctrl.update = MagicMock()
    ctrl.setup()
    ctrl.update.assert_called_once_with()

    ctrl.enable_voice_control = MagicMock()
    ctrl.disable_voice_control = MagicMock()
    ctrl.is_voice_control_enabled = MagicMock(return_value=True)
    ctrl.toggle_voice_control()
    ctrl.disable_voice_control.assert_called_once_with()
    ctrl.is_voice_control_enabled.return_value = False
    ctrl.toggle_voice_control()
    ctrl.enable_voice_control.assert_called_once_with()

    window.core.config.get.return_value = True
    assert Voice.is_voice_control_enabled(ctrl) is True


def test_voice_button_and_timeout_helpers():
    ctrl, window = _voice()
    with patch('pygpt_net.controller.access.voice.trans', side_effect=lambda key: key):
        ctrl.switch_btn_stop()
        ctrl.switch_btn_start()
    btn = window.ui.nodes['voice.control.btn'].btn_toggle
    assert btn.setText.call_count == 2
    ctrl.stop_recording = MagicMock()
    ctrl.stop_timeout()
    ctrl.stop_recording.assert_called_once_with(timeout=True)


def test_voice_handle_transcribed_delegates_to_transcriber_tool():
    ctrl, window = _voice()
    transcriber = MagicMock()
    window.tools.get.return_value = transcriber
    ctrl.handle_transcribed('/tmp/a.wav', 'hello')
    transcriber.on_transcribe.assert_called_once_with('/tmp/a.wav', 'hello')
