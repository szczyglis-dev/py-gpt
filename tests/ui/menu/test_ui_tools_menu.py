from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.menu.tools import Tools


def test_tools_callbacks_delegate_to_matching_components():
    window = MagicMock()
    widget = SimpleNamespace(window=window)
    action = MagicMock()
    action.data.return_value = "calendar"
    window.sender.return_value = action
    interpreter_plugin = MagicMock()
    system_plugin = MagicMock()
    window.core.plugins.get.side_effect = lambda key: {
        "cmd_code_interpreter": interpreter_plugin,
        "cmd_system": system_plugin,
    }[key]

    Tools._open_tab_action(widget)
    Tools._toggle_remote_store(widget)
    Tools._rebuild_ipython(widget)
    Tools._rebuild_python_legacy(widget)
    Tools._rebuild_system(widget)

    window.controller.tools.open_tab.assert_called_once_with("calendar")
    window.controller.remote_store.toggle_editor.assert_called_once()
    assert window.core.plugins.get.call_count == 3
    window.core.plugins.get.assert_any_call("cmd_code_interpreter")
    window.core.plugins.get.assert_any_call("cmd_system")
    interpreter_plugin.builder.build_and_restart.assert_called_once()
    interpreter_plugin.docker.build_and_restart.assert_called_once()
    system_plugin.docker.build_and_restart.assert_called_once()


def _window(tab_tools, menu_actions):
    menu = MagicMock()
    menubar = MagicMock()
    menubar.addMenu.return_value = menu
    controller = MagicMock()
    controller.tools.get_tab_tools.return_value = tab_tools
    tools = MagicMock()
    tools.setup_menu_actions.return_value = menu_actions
    return SimpleNamespace(
        ui=SimpleNamespace(menu={}),
        controller=controller,
        tools=tools,
        menuBar=lambda: menubar,
        core=MagicMock(),
    ), menu


def test_tools_setup_adds_tab_actions_and_returns_early_without_plugin_actions():
    window, menu = _window({"tool.calendar": ("calendar", "calendar", "calendar")}, {})
    widget = SimpleNamespace(window=window)
    created = []

    def make_action(*args, **kwargs):
        action = MagicMock()
        created.append(action)
        return action

    with patch("pygpt_net.ui.menu.tools.QAction", side_effect=make_action), \
            patch("pygpt_net.ui.menu.tools.QIcon"), \
            patch("pygpt_net.ui.menu.tools.trans", side_effect=lambda key: key):
        Tools.setup(widget)

    assert "menu.tools" in window.ui.menu
    assert "tool.calendar" in window.ui.menu
    menu.addAction.assert_called_once_with(window.ui.menu["tool.calendar"])
    menu.addSeparator.assert_not_called()


def test_tools_setup_adds_plugin_remote_store_and_docker_actions():
    extra = MagicMock()
    window, menu = _window({}, {"tool.extra": extra})
    widget = SimpleNamespace(window=window, _toggle_remote_store=MagicMock(), _rebuild_ipython=MagicMock(),
                             _rebuild_python_legacy=MagicMock(), _rebuild_system=MagicMock())
    docker_menu = MagicMock()
    menu.addMenu.return_value = docker_menu

    def make_action(*args, **kwargs):
        return MagicMock()

    with patch("pygpt_net.ui.menu.tools.QAction", side_effect=make_action), \
            patch("pygpt_net.ui.menu.tools.QIcon"), \
            patch("pygpt_net.ui.menu.tools.trans", side_effect=lambda key: key):
        Tools.setup(widget)

    assert window.ui.menu["tool.extra"] is extra
    assert "menu.tools.remote_store" in window.ui.menu
    assert "menu.tools.docker" in window.ui.menu
    assert "menu.tools.ipython.rebuild" in window.ui.menu
    assert "menu.tools.python_legacy.rebuild" in window.ui.menu
    assert "menu.tools.system.rebuild" in window.ui.menu
    assert menu.addSeparator.call_count == 3
    assert docker_menu.addAction.call_count == 3
