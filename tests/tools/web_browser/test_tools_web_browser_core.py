from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.tools.web_browser.tool import WebBrowser


def _tool():
    tool = WebBrowser()
    tabs = MagicMock()
    tabs.column_idx = 0
    plugin = MagicMock()
    plugin.get_option_value.return_value = None
    core_tabs = MagicMock()
    core_tabs.get_max_idx_by_column.return_value = 0
    window = SimpleNamespace(
        controller=SimpleNamespace(
            ui=SimpleNamespace(tabs=tabs),
            chat=SimpleNamespace(common=MagicMock()),
            kernel=SimpleNamespace(busy=False),
        ),
        core=SimpleNamespace(
            plugins=SimpleNamespace(get=MagicMock(return_value=plugin)),
            tabs=core_tabs,
        ),
        ui=SimpleNamespace(
            dialogs=MagicMock(),
            nodes={"icon.web_browser": MagicMock()},
            splitters={},
        ),
        state="idle",
        STATE_BUSY="busy",
    )
    tool.window = window
    return tool


def test_web_browser_defaults_setup_reload_and_dialog_id():
    tool = _tool()
    tool.update = MagicMock()

    tool.setup()

    tool.update.assert_called_once_with()
    assert tool.id == "web_browser"
    assert tool.has_tab is True
    assert tool.single_instance is True
    assert tool.get_dialog_id() == "web_browser"

    tool.update.reset_mock()
    tool.on_reload()
    tool.update.assert_called_once_with()


def test_web_browser_set_url_routes_to_canvas_runtime():
    tool = _tool()
    tool.runtime_call = MagicMock()

    tool.set_url("https://example.com")

    tool.runtime_call.assert_called_once_with(
        "canvas_open",
        {"url": "https://example.com", "__ui": True},
    )


def test_web_browser_open_creates_singleton_in_second_column_and_focuses_it():
    tool = _tool()
    tabs = tool.window.controller.ui.tabs
    tab = SimpleNamespace(idx=7, column_idx=1)
    tabs.get_first_tab_by_tool.side_effect = [None, tab]
    tabs.is_split_screen_enabled.return_value = False
    tool.window.core.tabs.get_max_idx_by_column.return_value = 4
    tool._ensure_surface = MagicMock()

    result = tool.open()

    assert result is tab
    tabs.append.assert_called_once_with(
        type=Tab.TAB_TOOL,
        tool_id="web_browser",
        idx=4,
        column_idx=1,
    )
    tabs.enable_split_screen.assert_called_once_with(update_switch=True)
    tabs.switch_tab_by_idx.assert_called_once_with(7, 1)


def test_web_browser_open_reuses_existing_singleton():
    tool = _tool()
    tabs = tool.window.controller.ui.tabs
    tab = SimpleNamespace(idx=3, column_idx=1)
    tabs.get_first_tab_by_tool.return_value = tab
    tabs.is_split_screen_enabled.return_value = True
    tool._ensure_surface = MagicMock()

    assert tool.open() is tab

    tabs.append.assert_not_called()
    tabs.enable_split_screen.assert_not_called()
    tabs.switch_tab_by_idx.assert_called_once_with(3, 1)


def test_web_browser_toggle_is_an_opener_not_dialog_state_toggle():
    tool = _tool()
    tool.open = MagicMock(return_value="tab")

    assert tool.toggle() == "tab"
    tool.open.assert_called_once_with()


def test_web_browser_close_surface_preserves_runtime_and_hides_ui():
    tool = _tool()
    tabs = tool.window.controller.ui.tabs
    tab = SimpleNamespace(idx=3, column_idx=1)
    tabs.get_first_tab_by_tool.return_value = tab
    tabs.is_split_screen_enabled.return_value = True

    assert tool.close() == {"closed": "split_screen", "session_alive": True}
    tabs.disable_split_screen.assert_called_once_with()
    tabs.close.assert_not_called()

    tabs.disable_split_screen.reset_mock()
    tabs.is_split_screen_enabled.return_value = False
    assert tool.close() == {"closed": "tab", "session_alive": True}
    tabs.close.assert_called_once_with(3, 1)

    tabs.get_first_tab_by_tool.return_value = None
    tool.detach_surface = MagicMock()
    assert tool.close() == {"closed": "none", "session_alive": True}
    tool.detach_surface.assert_called_once_with()


def test_web_browser_auto_open_existing_second_column_reveals_once_without_focus_steal():
    tool = _tool()
    tabs = tool.window.controller.ui.tabs
    tab = SimpleNamespace(idx=3, column_idx=1)
    tabs.get_first_tab_by_tool.return_value = tab
    tabs.is_split_screen_enabled.return_value = False
    tool._ensure_surface = MagicMock()

    assert tool.auto_open(load=False) is None
    assert tool.split_auto_expanded is True
    tabs.enable_split_screen.assert_called_once_with(update_switch=True)
    tabs.switch_tab_by_idx.assert_not_called()
    tabs.append.assert_not_called()

    tool.auto_open(load=False)
    assert tabs.enable_split_screen.call_count == 1
    tabs.switch_tab_by_idx.assert_not_called()


def test_web_browser_auto_open_respects_existing_legacy_primary_column_tab():
    tool = _tool()
    tabs = tool.window.controller.ui.tabs
    tabs.get_first_tab_by_tool.return_value = SimpleNamespace(idx=2, column_idx=0)
    tool._ensure_surface = MagicMock()

    tool.auto_open(load=False)

    assert tool.split_auto_expanded is True
    tabs.enable_split_screen.assert_not_called()
    tabs.switch_tab_by_idx.assert_not_called()
    tabs.append.assert_not_called()


def test_web_browser_auto_open_creates_missing_tab_without_switching_focus():
    tool = _tool()
    tabs = tool.window.controller.ui.tabs
    tabs.get_first_tab_by_tool.return_value = None
    tabs.is_split_screen_enabled.return_value = False
    tool.window.core.tabs.get_max_idx_by_column.return_value = 5
    tool._ensure_surface = MagicMock()

    tool.auto_open(load=False)

    tabs.enable_split_screen.assert_called_once_with(update_switch=True)
    tabs.append.assert_called_once_with(
        type=Tab.TAB_TOOL,
        tool_id="web_browser",
        idx=5,
        column_idx=1,
    )
    tabs.switch_tab_by_idx.assert_not_called()


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
    tool.open = MagicMock()
    tool.close = MagicMock()

    tool.show_hide(True)
    tool.show_hide(False)

    tool.open.assert_called_once_with()
    tool.close.assert_called_once_with()
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

    tool.dialog = MagicMock()
    tool.setup_dialogs()
    assert tool.dialog is None


def test_web_browser_lang_mappings_use_canvas_menu_label():
    tool = _tool()
    assert tool.get_lang_mappings() == {
        "menu.text": {"tools.web_browser": "menu.tools.canvas_html"}
    }
