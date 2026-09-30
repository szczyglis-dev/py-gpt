from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QPushButton

from pygpt_net.controller.chat.common import Common
from pygpt_net.plugin.audio_input.simple import Simple
from pygpt_net.ui.layout.chat.input import Input


@pytest.mark.parametrize('realtime,recording', [(False, True), (False, False), (True, True)])
def test_send_button_submits_recording_outside_realtime(qapp, monkeypatch, realtime, recording):
    monkeypatch.setattr('pygpt_net.ui.layout.chat.input.trans', lambda key: key)
    window = MagicMock()
    composer = MagicMock()
    buttons = []

    def add_button(**kwargs):
        button = QPushButton()
        button.clicked.connect(kwargs['callback'])
        buttons.append(button)
        return button

    composer.add_right_icon.side_effect = add_button
    composer.add_right_button.side_effect = add_button
    window.ui.nodes = {'input': composer}
    window.controller.realtime.is_enabled.return_value = realtime
    window.controller.realtime.is_auto_turn.return_value = True
    window.controller.chat.common = Common(window)
    plugin = window.core.plugins.get.return_value
    plugin.window = window
    handler = Simple(plugin)
    handler.is_recording = recording
    plugin.handler_simple = handler
    window.core.audio.capture.has_source.return_value = True
    window.core.audio.capture.has_frames.return_value = True
    layout = Input.__new__(Input)
    layout.window = window
    layout.setup_buttons()

    window.ui.nodes['input.send_btn'].click()

    if recording and not realtime:
        window.core.audio.capture.stop.assert_called_once_with()
        plugin.handle_thread.assert_called_once_with(True)
        window.controller.chat.input.send_input.assert_not_called()
        window.controller.realtime.cancel_conversation.assert_not_called()
        assert handler.is_recording is False
    else:
        window.controller.chat.input.send_input.assert_called_once_with()
        window.core.audio.capture.stop.assert_not_called()
        plugin.handle_thread.assert_not_called()

    for button in buttons:
        button.close()
        button.deleteLater()
