from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject, QUrl, Signal

from pygpt_net.tools.web_browser.core.qt import QtBackend


@pytest.fixture(autouse=True)
def fake_event_loop(monkeypatch):
    # Completion signals are delivered directly; no native event loop is needed.
    monkeypatch.setattr('pygpt_net.tools.web_browser.core.qt.QEventLoop', MagicMock())
    monkeypatch.setattr('pygpt_net.tools.web_browser.core.qt.QTimer', MagicMock())


class Page(QObject):
    loadFinished = Signal(bool)


class Web:
    def __init__(self):
        self.current_page = Page()
        self.old_page = None
        self.submitted = None
        self.succeed = True

    def page(self):
        return self.current_page

    def reset_runtime_page(self):
        self.old_page = self.current_page
        self.current_page = Page()

    def setHtml(self, html, base_url):
        self.submitted = (html, base_url)
        # An interrupted load must not acknowledge the new document.
        self.current_page.loadFinished.emit(False)
        if self.succeed:
            self.current_page.loadFinished.emit(True)


def test_html_load_preserves_page_and_ignores_aborted_load(qapp):
    web = Web()
    backend = QtBackend(SimpleNamespace(surface=SimpleNamespace(web=web)))
    page = web.page()
    backend.load_html('<canvas>cat</canvas>', QUrl('about:blank'), timeout_ms=100)
    assert web.page() is page
    assert web.old_page is None
    assert web.submitted[0] == '<canvas>cat</canvas>'


def test_failed_html_load_does_not_report_success(qapp):
    web = Web()
    web.succeed = False
    backend = QtBackend(SimpleNamespace(surface=SimpleNamespace(web=web)))
    with pytest.raises(TimeoutError, match='did not finish loading'):
        backend.load_html('<canvas>cat</canvas>', QUrl('about:blank'), timeout_ms=20)
