from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from pygpt_net.ui.widget.textarea.create import CreateInput


def _window():
    dialog = SimpleNamespace(id="preset", current="parent")
    return SimpleNamespace(
        controller=SimpleNamespace(dialogs=SimpleNamespace(confirm=SimpleNamespace(accept_create=MagicMock()))),
        ui=SimpleNamespace(dialog={"create": dialog}),
    )


def test_enter_accepts_create_with_current_dialog_context(qapp):
    window = _window()
    widget = CreateInput(None, "create")
    widget.window = window
    widget.setText("new item")
    event = QKeyEvent(QEvent.KeyPress, Qt.Key_Enter, Qt.NoModifier)
    widget.keyPressEvent(event)
    window.controller.dialogs.confirm.accept_create.assert_called_once_with("preset", "parent", "new item")


def test_non_enter_does_not_accept_create(qapp):
    window = _window()
    widget = CreateInput(None, "create")
    widget.window = window
    event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    widget.keyPressEvent(event)
    window.controller.dialogs.confirm.accept_create.assert_not_called()
