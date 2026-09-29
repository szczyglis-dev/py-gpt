from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from pygpt_net.ui.widget.textarea.rename import RenameInput


def _window():
    dialog = SimpleNamespace(id="ctx", current="old")
    return SimpleNamespace(
        controller=SimpleNamespace(dialogs=SimpleNamespace(confirm=SimpleNamespace(accept_rename=MagicMock()))),
        ui=SimpleNamespace(dialog={"rename": dialog}),
    )


def test_enter_accepts_rename_with_current_dialog_context(qapp):
    window = _window()
    widget = RenameInput(None, "rename")
    widget.window = window
    widget.setText("new name")
    event = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier)
    widget.keyPressEvent(event)
    window.controller.dialogs.confirm.accept_rename.assert_called_once_with("ctx", "old", "new name")


def test_non_enter_does_not_accept_rename(qapp):
    window = _window()
    widget = RenameInput(None, "rename")
    widget.window = window
    event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    widget.keyPressEvent(event)
    window.controller.dialogs.confirm.accept_rename.assert_not_called()
