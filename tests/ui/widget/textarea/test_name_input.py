from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from pygpt_net.ui.widget.textarea.name import NameInput


def test_key_press_updates_tokens_and_preset_editor(qapp):
    window = MagicMock()
    widget = NameInput(None, "ai_name")
    widget.window = window
    widget.setText("Alice")
    event = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier)

    widget.keyPressEvent(event)

    window.controller.ui.update_tokens.assert_called_once()
    window.controller.presets.editor.update_from_global.assert_called_once_with("ai_name", "Alice")
