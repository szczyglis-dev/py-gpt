from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt

from pygpt_net.ui.dialogs import Dialogs


def _widget(dialogs=None):
    window = SimpleNamespace(
        ui=SimpleNamespace(dialog=dialogs or {}),
        core=SimpleNamespace(debug=MagicMock()),
        controller=MagicMock(),
        tools=MagicMock(),
        screen=MagicMock(),
    )
    return SimpleNamespace(window=window)


def test_confirm_populates_and_shows_dialog():
    confirm = MagicMock()
    widget = _widget({"confirm": confirm})
    parent = object()

    Dialogs.confirm(widget, "delete", 5, "Sure?", parent)

    assert confirm.type == "delete"
    assert confirm.id == 5
    confirm.message.setText.assert_called_once_with("Sure?")
    assert confirm.parent_object is parent
    confirm.show.assert_called_once()


def test_alert_parses_message_and_shows_on_main_thread():
    alert = MagicMock()
    widget = _widget({"alert": alert})
    widget.window.core.debug.parse_alert.return_value = "parsed"

    Dialogs.alert(widget, {"message": "x"})

    alert.message.setPlainText.assert_called_once_with("parsed")
    alert.show.assert_called_once()


def test_alert_aborts_from_worker_thread():
    widget = _widget({"alert": MagicMock()})
    with patch("pygpt_net.ui.dialogs.threading.current_thread") as current, \
            patch("pygpt_net.ui.dialogs.threading.main_thread") as main:
        current.return_value = object()
        main.return_value = object()
        Dialogs.alert(widget, "x")
    widget.window.core.debug.parse_alert.assert_not_called()


def test_open_editor_sets_size_data_id_and_shows():
    dialog = MagicMock()
    widget = _widget({"editor": dialog})

    Dialogs.open_editor(widget, "editor", "data-1", 640, 480)

    dialog.resize.assert_called_once_with(640, 480)
    assert dialog.data_id == "data-1"
    dialog.show.assert_called_once()


def test_open_editor_ignores_unknown_id():
    widget = _widget({})
    assert Dialogs.open_editor(widget, "missing", "data") is None


def test_dictionary_editor_registers_data_and_shows():
    dialog = MagicMock()
    widget = _widget({"editor.dictionary.parent.key": dialog})
    option = {"keys": []}
    data = {"a": 1}

    Dialogs.open_dictionary_editor(widget, "parent.key", option, data, 3, 500, 400)

    widget.window.controller.config.dictionary.append_editor.assert_called_once_with("parent.key", option, data)
    dialog.resize.assert_called_once_with(500, 400)
    assert dialog.data is data
    assert dialog.idx == 3
    dialog.show.assert_called_once()


def test_register_dictionary_builds_combined_identifier():
    dictionary = MagicMock()
    widget = SimpleNamespace(dictionary=dictionary)
    option = {"x": 1}
    Dialogs.register_dictionary(widget, "key", "parent", option)
    dictionary.register.assert_called_once_with("parent.key", "key", "parent", option)


def test_close_closes_known_dialog_on_main_thread_and_ignores_unknown():
    dialog = MagicMock()
    widget = _widget({"known": dialog})
    Dialogs.close(widget, "missing")
    dialog.close.assert_not_called()
    Dialogs.close(widget, "known")
    dialog.close.assert_called_once()


def test_open_configures_dialog_geometry_and_focus():
    dialog = MagicMock()
    dialog.windowFlags.return_value = Qt.WindowType(0)
    geometry = MagicMock()
    dialog.frameGeometry.return_value = geometry
    center = object()
    screen = MagicMock()
    screen.availableGeometry.return_value.center.return_value = center
    widget = _widget({"known": dialog})
    widget.window.screen.return_value = screen

    Dialogs.open(widget, "known", 800, 600)

    dialog.resize.assert_called_once_with(800, 600)
    dialog.setSizeGripEnabled.assert_called_once_with(True)
    geometry.moveCenter.assert_called_once_with(center)
    dialog.move.assert_called_once_with(geometry.topLeft())
    dialog.show.assert_called_once()
    dialog.activateWindow.assert_called_once()
    dialog.setFocus.assert_called_once()


def test_open_instance_creates_missing_tool_instance_and_registers_it():
    dialog = MagicMock()
    geometry = MagicMock()
    dialog.frameGeometry.return_value = geometry
    screen = MagicMock()
    screen.availableGeometry.return_value.center.return_value = "center"
    widget = _widget({})
    widget.window.tools.get_instance.return_value = dialog
    widget.window.screen.return_value = screen

    Dialogs.open_instance(widget, "editor-1", 500, 300, type="text_editor")

    widget.window.tools.get_instance.assert_called_once_with("text_editor", "editor-1")
    assert widget.window.ui.dialog["editor-1"] is dialog
    dialog.resize.assert_called_once_with(500, 300)
    geometry.moveCenter.assert_called_once_with("center")
    dialog.show.assert_called_once()
