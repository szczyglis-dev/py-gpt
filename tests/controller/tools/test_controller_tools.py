from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.tools.tools import Tools
from pygpt_net.core.tabs.tab import Tab


def test_tools_open_tab_switches_to_first_tab_of_requested_type():
    window = MagicMock()
    window.core.tabs.get_min_idx_by_type.return_value = 4
    tools = Tools(window)

    tools.open_tab(99)

    window.core.tabs.get_min_idx_by_type.assert_called_once_with(99)
    window.controller.ui.tabs.switch_tab_by_idx.assert_called_once_with(4)


def test_tools_open_tab_does_nothing_when_type_has_no_tab():
    window = MagicMock()
    window.core.tabs.get_min_idx_by_type.return_value = None
    tools = Tools(window)

    tools.open_tab(99)

    window.controller.ui.tabs.switch_tab_by_idx.assert_not_called()


def test_tools_get_tab_tools_returns_controller_mapping():
    tools = Tools(MagicMock())

    result = tools.get_tab_tools()

    assert result is tools.tab_tools
    assert "tools.files" in result
    assert "tools.calendar" in result
    assert "tools.notepad" in result
    assert "tools.painter" in result


def test_tools_append_tab_menu_adds_only_tools_with_tabs():
    window = MagicMock()
    window.tools.get_all.return_value = {
        "terminal": SimpleNamespace(has_tab=True, tab_icon=":/terminal.svg", tab_title="tool.terminal"),
        "hidden": SimpleNamespace(has_tab=False, tab_icon=":/hidden.svg", tab_title="tool.hidden"),
    }
    tools = Tools(window)
    parent = MagicMock()
    parent.add_tab = MagicMock()
    menu = MagicMock()
    submenu = MagicMock()
    menu.addMenu.return_value = submenu
    action = MagicMock()

    with patch("pygpt_net.controller.tools.tools.QAction", return_value=action) as action_cls, \
            patch("pygpt_net.controller.tools.tools.QIcon", side_effect=lambda value: value), \
            patch("pygpt_net.controller.tools.tools.trans", side_effect=lambda value: f"tr:{value}"):
        result = tools.append_tab_menu(parent, menu, idx=2, column_idx=1)

    assert result is submenu
    action_cls.assert_called_once_with(":/terminal.svg", "tr:tool.terminal", parent)
    submenu.addAction.assert_called_once_with(action)
    assert action.triggered.connect.call_count == 1

    callback = action.triggered.connect.call_args.args[0]
    callback()
    parent.add_tab.assert_called_once_with(2, 1, Tab.TAB_TOOL, "terminal")
