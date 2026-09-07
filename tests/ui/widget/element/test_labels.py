from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.widget.element.labels import UrlLabel, CmdLabel


def test_url_label_update_url_formats_optional_prefix():
    widget = SimpleNamespace(text="Docs", url="https://example.test", setText=MagicMock())
    UrlLabel.update_url(widget)
    widget.setText.assert_called_once_with("Docs: https://example.test")

    widget = SimpleNamespace(text="", url="https://example.test", setText=MagicMock())
    UrlLabel.update_url(widget)
    widget.setText.assert_called_once_with("https://example.test")


def test_url_label_click_uses_application_dialog_controller_when_available():
    info = MagicMock()
    widget = SimpleNamespace(
        url="https://example.test",
        window=SimpleNamespace(controller=SimpleNamespace(dialogs=SimpleNamespace(info=info))),
    )

    UrlLabel.mousePressEvent(widget, MagicMock())
    info.open_url.assert_called_once_with("https://example.test")


def test_url_label_click_falls_back_to_desktop_services():
    widget = SimpleNamespace(url="https://example.test", window=None)

    with patch("pygpt_net.ui.widget.element.labels.QDesktopServices.openUrl") as open_url:
        UrlLabel.mousePressEvent(widget, MagicMock())

    assert open_url.call_count == 1
    assert open_url.call_args.args[0].toString() == "https://example.test"


def test_cmd_label_reset_icon_sets_copy_icon():
    widget = SimpleNamespace(action=MagicMock())
    with patch("pygpt_net.ui.widget.element.labels.QIcon", side_effect=lambda path: path):
        CmdLabel.reset_icon(widget)
    widget.action.setIcon.assert_called_once_with(":/icons/copy.svg")
