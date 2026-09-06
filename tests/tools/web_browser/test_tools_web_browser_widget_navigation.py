from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt

from pygpt_net.tools.web_browser.ui.widgets import AddressLineEdit, ToolWidget


def _widget():
    history = SimpleNamespace(
        canGoBack=MagicMock(return_value=False),
        canGoForward=MagicMock(return_value=True),
    )
    output = MagicMock()
    output.history.return_value = history
    output.tab = SimpleNamespace(idx=4)
    tool = SimpleNamespace(
        signals=SimpleNamespace(
            url=SimpleNamespace(disconnect=MagicMock()),
        )
    )
    window = SimpleNamespace(
        controller=SimpleNamespace(
            ui=SimpleNamespace(tabs=MagicMock()),
        )
    )
    return SimpleNamespace(
        tool=tool,
        window=window,
        output=output,
        nav_bar=MagicMock(),
        address_bar=MagicMock(),
        btn_back=MagicMock(),
        btn_next=MagicMock(),
        btn_reload=MagicMock(),
        _update_nav_controls=MagicMock(),
        _show_navbar=MagicMock(),
        open_url=MagicMock(),
        on_update_title=MagicMock(),
    )


def test_web_browser_widget_on_delete_disconnects_url_title_and_output():
    obj = _widget()
    obj.output.titleChanged = SimpleNamespace(disconnect=MagicMock())

    ToolWidget.on_delete(obj)

    obj.tool.signals.url.disconnect.assert_called_once_with(obj.open_url)
    obj.output.titleChanged.disconnect.assert_called_once_with(obj.on_update_title)
    obj.output.on_delete.assert_called_once_with()


def test_web_browser_widget_set_tab_and_open_url():
    obj = _widget()
    tab = object()
    ToolWidget.set_tab(obj, tab)
    obj.output.set_tab.assert_called_once_with(tab)

    qurl = object()
    with patch("pygpt_net.tools.web_browser.ui.widgets.QUrl", return_value=qurl):
        ToolWidget.open_url(obj, "https://example.com")
    obj.address_bar.setText.assert_called_once_with("https://example.com")
    obj.output.setUrl.assert_called_once_with(qurl)
    obj._update_nav_controls.assert_called_once_with()


def test_web_browser_widget_navbar_navigation_and_history_controls():
    obj = _widget()
    ToolWidget._show_navbar(obj, False)
    obj.nav_bar.setVisible.assert_called_once_with(False)
    obj._update_nav_controls.assert_called_once_with()

    obj._update_nav_controls.reset_mock()
    ToolWidget._navigate(obj, "back")
    obj.output.back.assert_called_once_with()
    ToolWidget._navigate(obj, "forward")
    obj.output.forward.assert_called_once_with()
    ToolWidget._navigate(obj, "reload")
    obj.output.reload.assert_called_once_with()
    assert obj._update_nav_controls.call_count == 3

    obj._update_nav_controls = ToolWidget._update_nav_controls.__get__(obj, ToolWidget)
    ToolWidget._update_nav_controls(obj)
    obj.btn_reload.setEnabled.assert_called_once_with(True)
    obj.btn_back.setEnabled.assert_called_once_with(False)
    obj.btn_next.setEnabled.assert_called_once_with(True)


def test_web_browser_widget_address_enter_and_url_change():
    obj = _widget()
    obj.address_bar.text.return_value = "example.com"
    fake_url = SimpleNamespace(isValid=MagicMock(return_value=True))
    with patch("pygpt_net.tools.web_browser.ui.widgets.QUrl.fromUserInput", return_value=fake_url):
        ToolWidget._on_address_enter(obj)
    obj._show_navbar.assert_called_once_with(True)
    obj.output.setUrl.assert_called_once_with(fake_url)

    obj._update_nav_controls.reset_mock()
    changed = SimpleNamespace(toString=MagicMock(return_value="https://changed.example"))
    ToolWidget._on_url_changed(obj, changed)
    obj.address_bar.setText.assert_called_with("https://changed.example")
    obj._update_nav_controls.assert_called_once_with()


def test_web_browser_widget_update_title_requires_output_tab_and_real_title():
    obj = _widget()
    ToolWidget.on_update_title(obj, "Example")
    obj.window.controller.ui.tabs.update_title_by_tab.assert_called_once_with(obj.output.tab, "Example")

    obj.window.controller.ui.tabs.update_title_by_tab.reset_mock()
    ToolWidget.on_update_title(obj, "about:blank")
    ToolWidget.on_update_title(obj, "   ")
    obj.window.controller.ui.tabs.update_title_by_tab.assert_not_called()

    obj.output.tab = None
    ToolWidget.on_update_title(obj, "Ignored")
    obj.window.controller.ui.tabs.update_title_by_tab.assert_not_called()


def test_web_browser_address_line_edit_enter_invokes_callback_and_accepts_event():
    callback = MagicMock()
    event = SimpleNamespace(key=MagicMock(return_value=Qt.Key_Enter), accept=MagicMock())
    obj = SimpleNamespace(_on_return_callback=callback)

    AddressLineEdit.keyPressEvent(obj, event)

    callback.assert_called_once_with()
    event.accept.assert_called_once_with()
