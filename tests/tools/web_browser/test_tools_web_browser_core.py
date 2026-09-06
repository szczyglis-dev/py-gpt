from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.tools.web_browser.tool import WebBrowser


def _tool():
    tool = WebBrowser()
    tabs = MagicMock()
    tabs.column_idx = 0
    window = SimpleNamespace(
        controller=SimpleNamespace(
            ui=SimpleNamespace(tabs=tabs),
            chat=SimpleNamespace(common=MagicMock()),
        ),
        ui=SimpleNamespace(dialogs=MagicMock(), nodes={"icon.web_browser": MagicMock()}),
    )
    tool.window = window
    tool.dialog = SimpleNamespace(widget=MagicMock())
    tool.signals = SimpleNamespace(
        url=SimpleNamespace(emit=MagicMock()),
        closed=SimpleNamespace(emit=MagicMock()),
    )
    return tool


def test_web_browser_defaults_setup_reload_and_dialog_id():
    tool = _tool()
    tool.update = MagicMock()
    tool.setup()
    tool.update.assert_called_once_with()
    assert tool.id == "web_browser"
    assert tool.has_tab is True
    assert tool.get_dialog_id() == "web_browser"

    with patch.object(tool, "setup") as setup:
        tool.on_reload()
    setup.assert_called_once_with()


def test_web_browser_set_url_emits_signal():
    tool = _tool()
    tool.set_url("https://example.com")
    tool.signals.url.emit.assert_called_once_with("https://example.com")


def test_web_browser_open_close_and_toggle():
    tool = _tool()
    tool.update = MagicMock()
    tool.open()
    assert tool.opened is True
    assert tool.auto_opened is False
    tool.window.ui.dialogs.open.assert_called_once_with("web_browser", width=800, height=600)
    tool.dialog.widget.on_open.assert_called_once_with()

    tool.open()
    assert tool.window.ui.dialogs.open.call_count == 1

    tool.close()
    assert tool.opened is False
    tool.signals.closed.emit.assert_called_once_with()
    tool.window.ui.dialogs.close.assert_called_once_with("web_browser")

    tool.open = MagicMock(); tool.close = MagicMock(); tool.opened = False
    tool.toggle(); tool.open.assert_called_once_with()
    tool.opened = True; tool.toggle(); tool.close.assert_called_once_with()


def test_web_browser_auto_open_handles_current_tab_split_screen():
    tool = _tool()
    tabs = tool.window.controller.ui.tabs
    tabs.is_current_tool.return_value = True
    tabs.get_tool_column.return_value = 1
    tabs.column_idx = 0
    tool.open = MagicMock()

    tool.auto_open(load=False)

    tabs.enable_split_screen.assert_called_once_with(True)
    tool.open.assert_not_called()


def test_web_browser_auto_open_switches_existing_tool_tab():
    tool = _tool()
    tabs = tool.window.controller.ui.tabs
    tabs.is_current_tool.return_value = False
    tabs.is_tool.return_value = True
    tabs.get_first_tab_by_tool.return_value = SimpleNamespace(idx=3, column_idx=1)
    tabs.column_idx = 0
    tool.open = MagicMock()

    tool.auto_open(load=False)

    tabs.switch_tab_by_idx.assert_called_once_with(3, 1)
    tabs.enable_split_screen.assert_called_once_with(True)
    tool.open.assert_not_called()


def test_web_browser_auto_open_opens_once_when_not_in_tab():
    tool = _tool()
    tabs = tool.window.controller.ui.tabs
    tabs.is_current_tool.return_value = False
    tabs.is_tool.return_value = False
    tool.open = MagicMock()

    tool.auto_open(load=False)
    assert tool.auto_opened is True
    tool.open.assert_called_once_with(load=False)

    tool.auto_open(load=False)
    assert tool.open.call_count == 1


def test_web_browser_handle_save_as_cleans_and_defers_to_chat_save():
    tool = _tool()

    def immediately(_delay, callback):
        callback()

    with patch("pygpt_net.tools.web_browser.tool.output_clean_html", return_value="clean") as clean, \
            patch("pygpt_net.tools.web_browser.tool.output_html2text", return_value="plain") as plain, \
            patch("pygpt_net.tools.web_browser.tool.QTimer.singleShot", side_effect=immediately):
        tool.handle_save_as("<p>x</p>", "html")
        clean.assert_called_once_with("<p>x</p>")
        tool.window.controller.chat.common.save_text.assert_called_with("clean", "html")

        tool.handle_save_as("<p>x</p>", "txt")
        plain.assert_called_once_with("<p>x</p>")
        tool.window.controller.chat.common.save_text.assert_called_with("plain", "txt")


def test_web_browser_show_hide_toolbar_icon_and_toggle_icon():
    tool = _tool()
    tool.open = MagicMock(); tool.close = MagicMock()
    tool.show_hide(True); tool.show_hide(False)
    tool.open.assert_called_once_with(); tool.close.assert_called_once_with()

    icon = tool.get_toolbar_icon()
    assert icon is tool.window.ui.nodes["icon.web_browser"]
    tool.toggle_icon(False)
    icon.setVisible.assert_called_once_with(False)


def test_web_browser_as_tab_and_setup_dialogs():
    tool = _tool()
    tab = object()
    dialog_tool = MagicMock()
    inner = MagicMock()
    dialog_tool.as_tab.return_value = inner
    tab_widget = MagicMock()

    with patch("pygpt_net.tools.web_browser.tool.Tool", return_value=dialog_tool), \
            patch("pygpt_net.tools.web_browser.tool.TabWidget", return_value=tab_widget):
        result = tool.as_tab(tab)

    assert result is tab_widget
    tab_widget.from_tool.assert_called_once_with(inner)
    tab_widget.setup.assert_called_once_with()
    dialog_tool.set_tab.assert_called_once_with(tab)

    dialog = MagicMock()
    with patch("pygpt_net.tools.web_browser.tool.Tool", return_value=dialog):
        tool.setup_dialogs()
    assert tool.dialog is dialog
    dialog.setup.assert_called_once_with()


def test_web_browser_lang_mappings():
    tool = _tool()
    assert tool.get_lang_mappings() == {
        "menu.text": {"tools.web_browser": "menu.tools.web_browser"}
    }
