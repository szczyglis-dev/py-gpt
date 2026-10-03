"""Preview service tests without starting Qt WebEngine or a browser process."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.tools.web_browser.core.preview import PreviewServer, _PreviewHandler


def test_preview_reuses_root_and_releases_server_on_stop(tmp_path):
    runtime = SimpleNamespace(server=None, server_root=None, server_url=None,
                              server_thread=None, runtime_html='<p>first</p>')
    preview = PreviewServer(runtime)
    runtime.preview = preview
    server = MagicMock()
    server.server_address = ('127.0.0.1', 12345)
    with patch('pygpt_net.tools.web_browser.core.preview.ThreadingHTTPServer',
               return_value=server) as factory, \
            patch('pygpt_net.tools.web_browser.core.preview.threading.Thread') as thread:
        assert preview.start(tmp_path) == 'http://127.0.0.1:12345/'
        handler = factory.call_args.args[1]
        runtime.runtime_html = '<p>updated</p>'
        assert handler.keywords['runtime_html_getter']() == '<p>updated</p>'
        assert preview.start(tmp_path, 12345) == runtime.server_url
        factory.assert_called_once()
        thread.return_value.start.assert_called_once_with()
        preview.stop()
        preview.stop()
    server.shutdown.assert_called_once_with()
    server.server_close.assert_called_once_with()
    assert preview.state() == {'running': False, 'root': None, 'url': None}


def test_preview_cannot_resolve_symlink_outside_root(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    outside = tmp_path / 'outside.html'
    outside.write_text('private', encoding='utf-8')
    (root / 'escape.html').symlink_to(outside)
    handler = object.__new__(_PreviewHandler)
    handler.directory = str(root)
    assert handler.translate_path('/escape.html') == str(root / '.__pygpt_forbidden__')
    assert handler.translate_path('/index.html') == str(root / 'index.html')


def test_preview_runtime_document_route_handles_query_and_empty_html():
    handler = object.__new__(_PreviewHandler)
    handler.path = '/__pygpt_runtime__.html?reload=1'
    handler.runtime_html_getter = lambda: None
    assert handler._runtime_html() == ''
    handler.runtime_html_getter = lambda: '<h1>Canvas</h1>'
    assert handler._runtime_html() == '<h1>Canvas</h1>'
    handler.path = '/index.html'
    assert handler._runtime_html() is None
