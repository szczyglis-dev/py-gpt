from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt

from pygpt_net.tools.html_canvas.ui.widgets import AddressLineEdit, ToolWidget


def _widget():
    history = SimpleNamespace(
        canGoBack=MagicMock(return_value=True),
        canGoForward=MagicMock(return_value=False),
    )
    output = MagicMock()
    output.history.return_value = history
    return SimpleNamespace(
        tool=SimpleNamespace(
            signals=SimpleNamespace(
                update=SimpleNamespace(disconnect=MagicMock()),
                reload=SimpleNamespace(disconnect=MagicMock()),
                url=SimpleNamespace(disconnect=MagicMock()),
            )
        ),
        output=output,
        edit=MagicMock(),
        nav_bar=MagicMock(),
        address_bar=MagicMock(),
        btn_back=MagicMock(),
        btn_next=MagicMock(),
        btn_reload=MagicMock(),
        _update_nav_controls=MagicMock(),
        _show_navbar=MagicMock(),
        open_url=MagicMock(),
        set_output=MagicMock(),
        load_output=MagicMock(),
    )


def test_html_canvas_widget_on_delete_disconnects_signals_and_output():
    obj = _widget()

    ToolWidget.on_delete(obj)

    obj.tool.signals.update.disconnect.assert_called_once_with(obj.set_output)
    obj.tool.signals.reload.disconnect.assert_called_once_with(obj.load_output)
    obj.tool.signals.url.disconnect.assert_called_once_with(obj.open_url)
    obj.output.on_delete.assert_called_once_with()


def test_html_canvas_widget_set_tab_routes_to_output_and_editor():
    obj = _widget()
    tab = object()

    ToolWidget.set_tab(obj, tab)

    obj.output.set_tab.assert_called_once_with(tab)
    obj.edit.set_tab.assert_called_once_with(tab)


def test_html_canvas_widget_open_url_sets_address_and_qurl():
    obj = _widget()
    qurl = object()

    with patch("pygpt_net.tools.html_canvas.ui.widgets.QUrl", return_value=qurl):
        ToolWidget.open_url(obj, "https://example.com")

    obj._show_navbar.assert_called_once_with(True)
    obj.address_bar.setText.assert_called_once_with("https://example.com")
    obj.output.setUrl.assert_called_once_with(qurl)
    obj._update_nav_controls.assert_called_once_with()


def test_html_canvas_widget_navbar_and_navigation_actions():
    obj = _widget()
    obj._update_nav_controls = MagicMock()

    ToolWidget._show_navbar(obj, True)
    obj.nav_bar.setVisible.assert_called_once_with(True)
    obj._update_nav_controls.assert_called_once_with()

    obj._update_nav_controls.reset_mock()
    ToolWidget._navigate(obj, "back")
    obj.output.back.assert_called_once_with()
    obj._update_nav_controls.assert_called_once_with()

    obj._update_nav_controls.reset_mock()
    ToolWidget._navigate(obj, "forward")
    obj.output.forward.assert_called_once_with()
    obj._update_nav_controls.assert_called_once_with()

    obj._update_nav_controls.reset_mock()
    ToolWidget._navigate(obj, "reload")
    obj.output.reload.assert_called_once_with()
    obj._update_nav_controls.assert_called_once_with()


def test_html_canvas_widget_address_enter_ignores_blank_and_loads_valid_url():
    obj = _widget()
    obj.address_bar.text.return_value = "   "
    ToolWidget._on_address_enter(obj)
    obj.output.setUrl.assert_not_called()

    obj.address_bar.text.return_value = " example.com "
    fake_url = SimpleNamespace(isValid=MagicMock(return_value=True))
    with patch("pygpt_net.tools.html_canvas.ui.widgets.QUrl.fromUserInput", return_value=fake_url):
        ToolWidget._on_address_enter(obj)

    obj._show_navbar.assert_called_once_with(True)
    obj.output.setUrl.assert_called_once_with(fake_url)
    obj._update_nav_controls.assert_called_once_with()


def test_html_canvas_widget_url_change_and_history_controls():
    obj = _widget()
    url = SimpleNamespace(toString=MagicMock(return_value="https://example.com/path"))

    ToolWidget._on_url_changed(obj, url)
    obj.address_bar.setText.assert_called_once_with("https://example.com/path")
    obj._update_nav_controls.assert_called_once_with()

    obj._update_nav_controls = ToolWidget._update_nav_controls.__get__(obj, ToolWidget)
    ToolWidget._update_nav_controls(obj)
    obj.btn_reload.setEnabled.assert_called_once_with(True)
    obj.btn_back.setEnabled.assert_called_once_with(True)
    obj.btn_next.setEnabled.assert_called_once_with(False)


def test_html_canvas_widget_history_failure_disables_navigation():
    obj = _widget()
    obj.output.history.side_effect = RuntimeError("gone")

    ToolWidget._update_nav_controls(obj)

    obj.btn_back.setEnabled.assert_called_once_with(False)
    obj.btn_next.setEnabled.assert_called_once_with(False)


def test_html_canvas_address_line_edit_enter_invokes_callback_and_accepts_event():
    callback = MagicMock()
    event = SimpleNamespace(
        key=MagicMock(return_value=Qt.Key_Return),
        accept=MagicMock(),
    )
    obj = SimpleNamespace(_on_return_callback=callback)

    AddressLineEdit.keyPressEvent(obj, event)

    callback.assert_called_once_with()
    event.accept.assert_called_once_with()
