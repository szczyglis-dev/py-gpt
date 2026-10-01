from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.menu.tools import Tools


def test_tools_callbacks_delegate_to_matching_components():
    window = MagicMock()
    widget = SimpleNamespace(window=window)
    action = MagicMock()
    action.data.return_value = "calendar"
    window.sender.return_value = action
    Tools._open_tab_action(widget)
    Tools._toggle_remote_store(widget)
    Tools._rebuild_ipython(widget)
    Tools._rebuild_python_legacy(widget)
    Tools._rebuild_system(widget)
    Tools._rebuild_python_builtin(widget)
    Tools._rebuild_system_builtin(widget)

    window.controller.tools.open_tab.assert_called_once_with("calendar")
    window.controller.remote_store.toggle_editor.assert_called_once()
    window.controller.tools.rebuild_ipython_docker.assert_called_once_with()
    window.controller.tools.rebuild_python_legacy_docker.assert_called_once_with()
    window.controller.tools.rebuild_system_docker.assert_called_once_with()
    window.controller.tools.rebuild_python_builtin.assert_called_once_with()
    window.controller.tools.rebuild_system_builtin.assert_called_once_with()


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


def test_tools_setup_adds_tab_and_builtin_actions_without_plugin_actions():
    window, menu = _window({"tool.calendar": ("calendar", "calendar", "calendar")}, {})
    widget = SimpleNamespace(
        window=window,
        _toggle_remote_store=MagicMock(),
        _rebuild_ipython=MagicMock(),
        _rebuild_python_legacy=MagicMock(),
        _rebuild_system=MagicMock(),
        _rebuild_python_builtin=MagicMock(),
        _rebuild_system_builtin=MagicMock(),
    )

    with patch("pygpt_net.ui.menu.tools.QAction", side_effect=lambda *args, **kwargs: MagicMock()), \
            patch("pygpt_net.ui.menu.tools.QIcon"), \
            patch("pygpt_net.ui.menu.tools.trans", side_effect=lambda key: key):
        Tools.setup(widget)

    assert "menu.tools" in window.ui.menu
    assert "tool.calendar" in window.ui.menu
    assert "menu.tools.remote_store" in window.ui.menu
    assert "menu.tools.docker" in window.ui.menu
    added = [call.args[0] for call in menu.addAction.call_args_list]
    assert window.ui.menu["tool.calendar"] in added
    assert window.ui.menu["menu.tools.remote_store"] in added
    assert menu.addSeparator.call_count == 2


def test_tools_setup_adds_plugin_remote_store_and_docker_actions():
    extra = MagicMock()
    window, menu = _window({}, {"tool.extra": extra})
    widget = SimpleNamespace(
        window=window,
        _toggle_remote_store=MagicMock(),
        _rebuild_ipython=MagicMock(),
        _rebuild_python_legacy=MagicMock(),
        _rebuild_system=MagicMock(),
        _rebuild_python_builtin=MagicMock(),
        _rebuild_system_builtin=MagicMock(),
    )
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
    assert "menu.tools.python_builtin.rebuild" in window.ui.menu
    assert "menu.tools.system_builtin.rebuild" in window.ui.menu
    assert menu.addSeparator.call_count == 3
    assert docker_menu.addAction.call_count == 5
