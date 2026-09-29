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
    bar = MagicMock()
    ctrl.get_output_bar = MagicMock(return_value=bar)

    ctrl.on_input_volume_change(37)
    bar.setLevel.assert_called_once_with(37)

    ctrl.recording = True
    ctrl.on_output_volume_change(80)
    assert bar.setLevel.call_count == 1

    ctrl.recording = False
    ctrl.on_output_volume_change(80)
    bar.setLevel.assert_called_with(80)


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
