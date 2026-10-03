from unittest.mock import MagicMock, patch

from pygpt_net.controller.audio.ui import UI


def _ui():
    window = MagicMock()
    window.ui.plugin_addon = {}
    window.ui.nodes = {'input': MagicMock()}
    return UI(window), window


def test_audio_ui_widget_getters_cache_widgets_and_handle_missing_nodes():
    ctrl, window = _ui()
    assert ctrl.get_input_bar() is None
    assert ctrl.get_output_bar() is None
    assert ctrl.get_input_btn() is None
    assert ctrl.get_input_control_btn() is None
    assert ctrl.get_output_btn() is None

    input_btn = MagicMock()
    output_bar = MagicMock()
    output_btn = MagicMock()
    control_btn = MagicMock()
    window.ui.plugin_addon.update({
        'audio.input.btn': input_btn,
        'audio.output.bar': output_bar,
        'audio.output': output_btn,
    })
    window.ui.nodes['voice.control.btn'] = control_btn

    assert ctrl.get_input_bar() is input_btn.bar
    assert ctrl.get_output_bar() is output_bar
    assert ctrl.get_input_btn() is input_btn
    assert ctrl.get_input_control_bar() is control_btn.bar
    assert ctrl.get_input_control_btn() is control_btn
    assert ctrl.get_output_btn() is output_btn

    window.ui.plugin_addon.clear()
    assert ctrl.get_input_btn() is input_btn
    assert ctrl.get_output_bar() is output_bar


def test_audio_ui_volume_updates_are_mocked_and_output_does_not_move_during_recording():
    ctrl, _ = _ui()
    input_bar = MagicMock()
    record_bar = MagicMock()
    output_bar = MagicMock()
    ctrl.get_input_bar = MagicMock(return_value=input_bar)
    ctrl.get_input_record_bar = MagicMock(return_value=record_bar)
    ctrl.get_output_bar = MagicMock(return_value=output_bar)

    ctrl.on_input_volume_change(37)
    input_bar.setLevel.assert_called_once_with(37)
    record_bar.setLevel.assert_called_once_with(37)
    output_bar.setLevel.assert_not_called()

    ctrl.recording = True
    ctrl.on_output_volume_change(80)
    output_bar.setLevel.assert_not_called()

    ctrl.recording = False
    ctrl.on_output_volume_change(80)
    output_bar.setLevel.assert_called_once_with(80)


def test_audio_ui_input_enable_disable_and_continuous_controls():
    ctrl, window = _ui()
    btn = MagicMock()
    ctrl.get_input_control_btn = MagicMock(return_value=btn)

    ctrl.on_input_enable('control')
    window.ui.nodes['input'].set_icon_visible.assert_called_with('mic', True)
    btn.setVisible.assert_called_with(True)

    ctrl.on_input_disable('control')
    window.ui.nodes['input'].set_icon_visible.assert_called_with('mic', False)
    btn.setVisible.assert_called_with(False)

    ctrl.on_input_continuous_enable(True, 'control')
    btn.notepad_footer.setVisible.assert_called_with(True)
    ctrl.on_input_continuous_disable('control')
    btn.notepad_footer.setVisible.assert_called_with(False)


def test_audio_ui_begin_end_input_lock_and_unlock_without_real_audio():
    ctrl, window = _ui()

    ctrl.on_input_begin('input')
    assert ctrl.recording is True
    window.ui.nodes['input'].set_icon_state.assert_called_with('mic', True)
    window.controller.chat.common.lock_input.assert_called_once_with()

    ctrl.on_input_end('realtime')
    assert ctrl.recording is False
    window.ui.nodes['input'].set_icon_state.assert_called_with('mic', False)
    window.controller.chat.common.unlock_input.assert_called_once_with()


def test_audio_ui_control_begin_end_updates_button_text_from_translation():
    ctrl, _ = _ui()
    btn = MagicMock()
    ctrl.get_input_control_btn = MagicMock(return_value=btn)
    with patch('pygpt_net.controller.audio.ui.trans', side_effect=lambda key: f'T:{key}'):
        ctrl.on_input_begin('control')
        btn.btn_toggle.setText.assert_called_with('T:audio.speak.btn.stop')
        btn.btn_toggle.setToolTip.assert_called_with('T:audio.speak.btn.stop.tooltip')

        ctrl.on_input_end('control')
        btn.btn_toggle.setText.assert_called_with('T:audio.speak.btn')
        btn.btn_toggle.setToolTip.assert_called_with('T:audio.speak.btn.tooltip')


def test_audio_ui_output_begin_delegates_to_audio_controller():
    ctrl, window = _ui()
    ctrl.on_output_begin()
    window.controller.audio.start_speaking.assert_called_once_with()


def test_audio_ui_noop_callbacks_are_safe():
    ctrl, _ = _ui()
    assert ctrl.on_input_device_change(1) is None
    assert ctrl.on_input_cancel() is None
    assert ctrl.on_output_device_change(1) is None
    assert ctrl.on_output_enable() is None
    assert ctrl.on_output_disable() is None
    assert ctrl.on_output_end() is None
    assert ctrl.on_output_cancel() is None


def test_ordinary_microphone_capture_shows_stop():
    from pygpt_net.controller.chat.common import Common

    ctrl, window = _ui()
    window.controller.realtime.is_enabled.return_value = False
    window.controller.realtime.is_response_active.return_value = False
    window.controller.chat.input.locked = False
    window.controller.chat.input.generating = False
    window.controller.ctx.extra.is_editing.return_value = False
    window.controller.tabs.is_chat_input_visible.return_value = True
    window.ui.nodes['input.send_btn'] = MagicMock()
    window.controller.chat.common = Common(window)

    ctrl.on_input_begin('input')

    assert ctrl.recording is True
    assert window.controller.chat.input.locked is True
    window.ui.nodes['input.send_btn'].setEnabled.assert_called_with(False)
    window.ui.nodes['input'].set_icon_visible.assert_any_call('send', False)
    window.ui.nodes['input'].set_icon_visible.assert_any_call('stop', True)


def test_recording_stays_in_originating_notepad_when_selection_changes():
    from types import SimpleNamespace
    ctrl, window = _ui()
    first, second = MagicMock(), MagicMock()
    window.tools.get('notepad').documents.widgets = {1: first, 2: second}
    window.controller.tabs.get_current_tab.return_value = SimpleNamespace(tool_id='notepad', data_id=2)
    ctrl.on_input_toggle_requested('input', notepad=first)
    first.set_record_pending.assert_called_once_with()
    second.set_record_pending.assert_not_called()
    ctrl.on_input_begin('input')
    ctrl.on_input_volume_change(42, 'input')
    first.set_recording_active.assert_called_once_with()
    first.set_record_level.assert_called_once_with(42)
    second.set_recording_active.assert_not_called()
    second.set_record_level.assert_not_called()
    second.set_mic_state.assert_called_with(False)
    assert ctrl.is_recording_in(first)
    assert not ctrl.is_recording_in(second)
    ctrl.on_input_end('input')
    assert not ctrl.is_recording_in(first)
    ctrl.on_input_toggle_requested('input', notepad=second)
    second.set_record_pending.assert_called_once_with()


def test_closed_notepad_is_not_replaced_by_another_during_capture_start():
    from types import SimpleNamespace
    ctrl, window = _ui()
    first, second = MagicMock(), MagicMock()
    window.tools.get('notepad').documents.widgets = {1: first, 2: second}
    ctrl.on_input_toggle_requested('input', notepad=first)
    window.tools.get('notepad').documents.widgets = {2: second}
    window.controller.tabs.get_current_tab.return_value = SimpleNamespace(tool_id='notepad', data_id=2)
    ctrl.on_input_begin('input')
    ctrl.on_input_volume_change(42, 'input')
    second.set_recording_active.assert_not_called()
    second.set_record_level.assert_not_called()
    assert not ctrl.is_recording_in(second)
    ctrl.on_input_abort('input')
    ctrl.on_input_toggle_requested('input')
    second.set_record_pending.assert_called_once_with()


def test_chat_capture_does_not_show_notepad_recording_bars():
    from types import SimpleNamespace
    ctrl, window = _ui()
    note = MagicMock()
    window.tools.get('notepad').documents.widgets = {1: note}
    window.controller.tabs.get_current_tab.return_value = SimpleNamespace(tool_id=None)
    ctrl.on_input_toggle_requested('input')
    ctrl.on_input_begin('input')
    ctrl.on_input_volume_change(42, 'input')
    note.set_record_pending.assert_not_called()
    note.set_recording_active.assert_not_called()
    note.set_record_level.assert_not_called()
