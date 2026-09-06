from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QLineEdit

from pygpt_net.ui.widget.option.input import OptionInputInline, PasswordInput, DirectoryInput


def _window():
    return SimpleNamespace(controller=SimpleNamespace(config=SimpleNamespace(
        slider=SimpleNamespace(on_update=MagicMock()),
        input=SimpleNamespace(on_update=MagicMock()),
    )))


def test_inline_input_updates_slider_even_when_not_realtime():
    window = _window()
    widget = SimpleNamespace(
        slider=True,
        real_time=False,
        window=window,
        parent_id="parent",
        id="id",
        option={"value": 1},
        text=lambda: "42",
    )

    OptionInputInline.handle_value_change(widget)

    window.controller.config.slider.on_update.assert_called_once_with(
        "parent", "id", {"value": 1}, "42", "input"
    )
    window.controller.config.input.on_update.assert_not_called()


def test_inline_input_realtime_updates_input_and_slider():
    window = _window()
    widget = SimpleNamespace(
        slider=True,
        real_time=True,
        window=window,
        parent_id="parent",
        id="id",
        option={},
        text=lambda: "7",
    )

    OptionInputInline.handle_value_change(widget)

    window.controller.config.slider.on_update.assert_called_once()
    window.controller.config.input.on_update.assert_called_once_with("parent", "id", {}, "7")


def test_password_visibility_toggles_echo_mode_and_marker():
    widget = SimpleNamespace(
        is_password_shown=False,
        setEchoMode=MagicMock(),
        toggle_password_action=MagicMock(),
    )

    PasswordInput.toggle_password_visibility(widget)
    assert widget.is_password_shown is True
    widget.setEchoMode.assert_called_with(QLineEdit.Normal)
    widget.toggle_password_action.setText.assert_called_with("-")

    PasswordInput.toggle_password_visibility(widget)
    assert widget.is_password_shown is False
    widget.setEchoMode.assert_called_with(QLineEdit.Password)
    widget.toggle_password_action.setText.assert_called_with("+")


def test_directory_input_clear_resets_text():
    widget = SimpleNamespace(setText=MagicMock())
    DirectoryInput.clear(widget)
    widget.setText.assert_called_once_with("")
