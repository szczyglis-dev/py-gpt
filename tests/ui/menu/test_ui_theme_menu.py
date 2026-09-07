from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.menu.theme import Theme


def test_theme_callbacks_delegate_to_controllers():
    window = MagicMock()
    widget = SimpleNamespace(window=window)

    Theme._on_toggle_tooltips(widget, True)
    Theme._open_settings(widget, True)

    window.controller.theme.toggle_option.assert_called_once_with("layout.tooltips")
    window.controller.settings.open_section.assert_called_once_with("layout")


def test_theme_setup_builds_menu_tree_and_marks_loaded():
    ui_menu = {}
    window = SimpleNamespace(
        ui=SimpleNamespace(menu=ui_menu),
        core=SimpleNamespace(config=MagicMock()),
    )
    window.core.config.get.return_value = True
    widget = SimpleNamespace(window=window, _loaded=False, _on_toggle_tooltips=MagicMock(), _open_settings=MagicMock())

    menus = []
    actions = []

    def make_menu(*args, **kwargs):
        obj = MagicMock()
        menus.append(obj)
        return obj

    def make_action(*args, **kwargs):
        obj = MagicMock()
        actions.append(obj)
        return obj

    with patch("pygpt_net.ui.menu.theme.QMenu", side_effect=make_menu), \
            patch("pygpt_net.ui.menu.theme.QAction", side_effect=make_action) as action_cls, \
            patch("pygpt_net.ui.menu.theme.trans", side_effect=lambda key: key):
        action_cls.MenuRole.NoRole = "no-role"
        Theme.setup(widget)

    assert widget._loaded is True
    assert set((
        "menu.theme", "theme.style", "theme.dark", "theme.light", "theme.syntax",
        "theme.density", "theme.tooltips", "theme.settings"
    )).issubset(ui_menu)
    ui_menu["theme.tooltips"].setChecked.assert_called_once_with(True)
    ui_menu["theme.settings"].setMenuRole.assert_called_once_with("no-role")
    assert ui_menu["menu.theme"].addMenu.call_count == 5
    assert ui_menu["menu.theme"].addAction.call_count == 2


def test_theme_setup_when_loaded_only_refreshes_tooltip_check_state(qapp):
    from PySide6.QtGui import QAction

    action = QAction("tooltips")
    config = MagicMock()
    config.get.return_value = False
    window = SimpleNamespace(ui=SimpleNamespace(menu={"theme.tooltips": action}), core=SimpleNamespace(config=config))
    widget = SimpleNamespace(window=window, _loaded=True)

    Theme.setup(widget)

    assert action.isChecked() is False
    config.get.assert_called_once_with("layout.tooltips")
