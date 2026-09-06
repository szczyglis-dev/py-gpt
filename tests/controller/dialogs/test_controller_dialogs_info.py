from unittest.mock import MagicMock, patch

from pygpt_net.controller.dialogs.info import Info


def _window():
    window = MagicMock()
    window.ui.menu = {}
    window.meta = {
        "website": "https://example.test",
        "docs": "https://docs.example.test",
        "pypi": "https://pypi.example.test",
        "github": "https://github.example.test",
        "snap": "https://snap.example.test",
        "ms_store": "https://store.example.test",
        "donate": "https://donate.example.test",
        "discord": "https://discord.example.test",
        "report": "https://report.example.test",
        "donate_coffee": "https://coffee.example.test",
        "donate_paypal": "https://paypal.example.test",
        "donate_github": "https://sponsor.example.test",
    }
    window.core.config.get = MagicMock(return_value=False)
    return window


def test_info_initial_state_contains_known_dialog_ids():
    info = Info(_window())

    assert info.ids == ["about", "changelog", "license"]
    assert info.active == {"about": False, "changelog": False, "license": False}


def test_info_toggle_opens_about_and_prepares_content():
    window = _window()
    info = Info(window)
    info.update_menu = MagicMock()

    info.toggle("about", width=640, height=480)

    window.ui.dialogs.about.prepare.assert_called_once_with()
    window.ui.dialogs.open.assert_called_once_with("info.about", width=640, height=480)
    assert info.active["about"] is True
    info.update_menu.assert_called_once_with()


def test_info_toggle_closes_active_dialog():
    window = _window()
    info = Info(window)
    info.active["license"] = True
    info.update_menu = MagicMock()

    info.toggle("license")

    window.ui.dialogs.close.assert_called_once_with("info.license")
    assert info.active["license"] is False
    info.update_menu.assert_called_once_with()


def test_info_open_url_uses_internal_browser_when_enabled():
    window = _window()
    window.core.config.get.return_value = True
    browser = MagicMock()
    window.tools.get.return_value = browser
    info = Info(window)

    info.open_url("https://internal.example.test")

    window.tools.get.assert_any_call("web_browser")
    browser.set_url.assert_called_once_with("https://internal.example.test")
    browser.auto_open.assert_called_once_with(load=False)


def test_info_open_url_uses_desktop_service_when_internal_browser_disabled():
    window = _window()
    info = Info(window)

    with patch("pygpt_net.controller.dialogs.info.QUrl", side_effect=lambda value: ("url", value)) as qurl, \
            patch("pygpt_net.controller.dialogs.info.QDesktopServices.openUrl") as open_url:
        info.open_url("https://external.example.test")

    qurl.assert_called_once_with("https://external.example.test")
    open_url.assert_called_once_with(("url", "https://external.example.test"))


def test_info_open_url_ignores_empty_value():
    window = _window()
    info = Info(window)

    with patch("pygpt_net.controller.dialogs.info.QDesktopServices.openUrl") as open_url:
        info.open_url("")

    open_url.assert_not_called()
    window.tools.get.assert_not_called()


def test_info_navigation_helpers_delegate_meta_urls():
    window = _window()
    info = Info(window)
    info.open_url = MagicMock()

    helpers = {
        "goto_website": "website",
        "goto_docs": "docs",
        "goto_pypi": "pypi",
        "goto_github": "github",
        "goto_snap": "snap",
        "goto_ms_store": "ms_store",
        "goto_update": "website",
        "goto_donate": "donate",
        "goto_discord": "discord",
        "goto_report": "report",
    }
    for method_name, meta_key in helpers.items():
        info.open_url.reset_mock()
        getattr(info, method_name)()
        info.open_url.assert_called_once_with(window.meta[meta_key])


def test_info_donate_routes_supported_providers_and_ignores_unknown():
    window = _window()
    info = Info(window)
    info.open_url = MagicMock()

    for donate_id, meta_key in (
        ("coffee", "donate_coffee"),
        ("paypal", "donate_paypal"),
        ("github", "donate_github"),
    ):
        info.open_url.reset_mock()
        info.donate(donate_id)
        info.open_url.assert_called_once_with(window.meta[meta_key])

    info.open_url.reset_mock()
    info.donate("unknown")
    info.open_url.assert_not_called()


def test_info_update_menu_sets_checked_state_only_for_existing_items():
    window = _window()
    window.ui.menu = {
        "info.about": MagicMock(),
        "info.license": MagicMock(),
    }
    info = Info(window)
    info.active["about"] = True
    info.active["license"] = False

    info.update_menu()

    window.ui.menu["info.about"].setChecked.assert_called_once_with(True)
    window.ui.menu["info.license"].setChecked.assert_called_once_with(False)
