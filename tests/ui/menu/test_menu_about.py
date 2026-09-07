from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.menu.about import About


def _action():
    action = MagicMock()
    action.triggered = MagicMock()
    action.triggered.connect = MagicMock()
    return action


def test_setup_registers_info_and_donate_actions_and_menus():
    info = MagicMock()
    launcher = MagicMock()
    about_menu = MagicMock()
    donate_menu = MagicMock()
    about_menu.addMenu.return_value = donate_menu
    window = SimpleNamespace(
        ui=SimpleNamespace(menu={}),
        controller=SimpleNamespace(dialogs=SimpleNamespace(info=info), launcher=launcher),
        menuBar=MagicMock(),
    )
    window.menuBar.return_value.addMenu.return_value = about_menu
    actions = [_action() for _ in range(15)]

    with patch("pygpt_net.ui.menu.about.QAction", side_effect=actions) as action_cls, \
         patch("pygpt_net.ui.menu.about.QIcon", return_value=MagicMock()), \
         patch("pygpt_net.ui.menu.about.trans", side_effect=lambda key: key):
        # Preserve the enum access after QAction is patched.
        action_cls.MenuRole.NoRole = "NO_ROLE"
        About(window).setup()

    expected = {
        "info.about", "info.changelog", "info.updates", "info.report", "info.website", "info.docs",
        "info.pypi", "info.snap", "info.ms_store", "info.github", "info.discord", "info.license",
        "donate.coffee", "donate.paypal", "donate.github", "menu.about", "menu.donate",
    }
    assert expected <= set(window.ui.menu)
    assert window.ui.menu["menu.about"] is about_menu
    assert window.ui.menu["menu.donate"] is donate_menu
    about_menu.addActions.assert_called_once()
    donate_menu.addActions.assert_called_once()


def test_setup_callbacks_dispatch_to_info_controller_and_launcher():
    info = MagicMock(); launcher = MagicMock(); about_menu = MagicMock(); donate_menu = MagicMock()
    about_menu.addMenu.return_value = donate_menu
    window = SimpleNamespace(
        ui=SimpleNamespace(menu={}),
        controller=SimpleNamespace(dialogs=SimpleNamespace(info=info), launcher=launcher),
        menuBar=MagicMock(),
    )
    window.menuBar.return_value.addMenu.return_value = about_menu
    actions = [_action() for _ in range(15)]
    with patch("pygpt_net.ui.menu.about.QAction", side_effect=actions) as action_cls, \
         patch("pygpt_net.ui.menu.about.QIcon", return_value=MagicMock()), \
         patch("pygpt_net.ui.menu.about.trans", side_effect=lambda key: key):
        action_cls.MenuRole.NoRole = "NO_ROLE"
        About(window).setup()

    def fire(key):
        callback = window.ui.menu[key].triggered.connect.call_args.args[0]
        callback(False)

    fire("info.about")
    fire("info.license")
    fire("info.updates")
    fire("info.docs")
    fire("donate.github")

    info.toggle.assert_any_call("about", width=400, height=500)
    info.toggle.assert_any_call("license", width=500, height=480)
    launcher.check_updates.assert_called_once()
    info.goto_docs.assert_called_once()
    info.donate.assert_called_once_with("github")
