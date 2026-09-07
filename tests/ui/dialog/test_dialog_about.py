from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.dialog.about import About


def _window():
    return SimpleNamespace(
        core=SimpleNamespace(
            updater=SimpleNamespace(get_fetch_thanks=MagicMock(return_value="Alice\nBob")),
            platforms=SimpleNamespace(get_as_string=MagicMock(return_value="Linux")),
            config=SimpleNamespace(get_app_path=MagicMock(return_value="/app")),
        ),
        meta={
            "version": "2.8.4", "build": "2026.09.07", "website": "web", "github": "git",
            "docs": "docs", "author": "Author", "email": "mail@example.com",
        },
        ui=SimpleNamespace(nodes={}, dialog={}),
        controller=MagicMock(),
    )


def test_get_thanks_delegates_to_updater():
    window = _window()
    assert About(window).get_thanks() == "Alice\nBob"
    window.core.updater.get_fetch_thanks.assert_called_once()


def test_build_versions_str_breaks_after_requested_library():
    about = About(_window())
    versions = {"Python": "3.12", "OpenAI": "2", "LlamaIndex": "0.14", "Anthropic": "1"}
    assert about.build_versions_str(versions) == "Python: 3.12, OpenAI: 2, LlamaIndex: 0.14\nAnthropic: 1"
    assert about.build_versions_str({}, break_after="X") == ""


def test_prepare_content_uses_metadata_platform_and_build_format():
    about = About(_window())
    with patch.object(about, "build_versions_str", return_value="LIBS"), \
         patch("pygpt_net.ui.dialog.about.trans", side_effect=lambda key: key):
        content = about.prepare_content()

    assert "dialog.about.version: 2.8.4, Linux" in content
    assert "dialog.about.build: 2026-09-07" in content
    assert "LIBS" in content
    assert "web" in content and "git" in content and "docs" in content
    assert "(c) 2026 Author" in content
    assert "mail@example.com" in content


def test_prepare_hides_empty_thanks_and_shows_nonempty():
    window = _window()
    title = MagicMock()
    content = MagicMock()
    window.ui.nodes["dialog.about.thanks"] = title
    window.ui.nodes["dialog.about.thanks.content"] = content
    about = About(window)

    with patch.object(about, "get_thanks", return_value=""):
        about.prepare()
    content.setPlainText.assert_called_with("")
    title.hide.assert_called_once()
    content.hide.assert_called_once()

    title.reset_mock(); content.reset_mock()
    with patch.object(about, "get_thanks", return_value="Alice"):
        about.prepare()
    content.setPlainText.assert_called_with("Alice")
    title.show.assert_called_once()
    content.show.assert_called_once()


def test_setup_registers_buttons_content_and_dialog():
    window = _window()
    labels = []
    buttons = []
    for _ in range(3):
        buttons.append(MagicMock())
    dialog = MagicMock()

    with patch("pygpt_net.ui.dialog.about.QPixmap", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.about.QLabel", side_effect=lambda *a, **k: labels.append(MagicMock()) or labels[-1]), \
         patch("pygpt_net.ui.dialog.about.QPushButton", side_effect=buttons), \
         patch("pygpt_net.ui.dialog.about.QHBoxLayout", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.about.QVBoxLayout", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.about.QPlainTextEdit", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.about.InfoDialog", return_value=dialog), \
         patch("pygpt_net.ui.dialog.about.trans", side_effect=lambda key: key), \
         patch.object(About, "prepare_content", return_value="CONTENT"):
        About(window).setup()

    assert set(k for k in window.ui.nodes if k.startswith("dialog.about.")) >= {
        "dialog.about.btn.website", "dialog.about.btn.github", "dialog.about.btn.support",
        "dialog.about.content", "dialog.about.thanks", "dialog.about.thanks.content",
    }
    assert window.ui.dialog["info.about"] is dialog
    dialog.setWindowTitle.assert_called_once_with("dialog.about.title")
    assert all(btn.clicked.connect.called for btn in buttons)
