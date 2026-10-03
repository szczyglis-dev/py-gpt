"""Manual Qt WebEngine integration: update an annotated animation, then reload.

Run with QT_QPA_PLATFORM=offscreen and QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox
when a headless environment requires them. A temporary PYGPT_WORKDIR is recommended.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView

import pygpt_net.icons_rc  # noqa: F401
from pygpt_net.tools.web_browser.tool import WebBrowser
from pygpt_net.tools.web_browser.ui.widgets import BrowserOutput, BrowserPage


class View(QWebEngineView):
    # Exercise the production page replacement without unrelated tool chrome.
    reset_runtime_page = BrowserOutput.reset_runtime_page
    _detach_gl_event_filter = BrowserOutput._detach_gl_event_filter


def animation(version, color):
    return f'''<!doctype html><html><body style="background:#eee">
<canvas id="cat" width="100" height="100"></canvas>
<script>
const canvas = document.getElementById('cat');
const ctx = canvas.getContext('2d');
window.version = '{version}';
window.frames = 0;
function draw() {{
  ctx.fillStyle = '{color}'; ctx.fillRect(0,0,40,40);
  window.frames++; requestAnimationFrame(draw);
}}
draw();
</script></body></html>'''


def main():
    app = QApplication.instance() or QApplication([])
    runtime = WebBrowser()
    runtime.auto_open_enabled = lambda: False
    runtime.sandbox_enabled = lambda: False
    runtime._opt = lambda key, default=None: default
    runtime.window = SimpleNamespace(
        core=SimpleNamespace(debug=MagicMock()),
        controller=SimpleNamespace(theme=SimpleNamespace(is_dark_theme=lambda: True)),
        update_status=MagicMock(),
    )
    web = View()
    web.tool = runtime
    web.setPage(BrowserPage(runtime, parent=web))
    source = []
    runtime.surface = SimpleNamespace(
        web=web, _source_visible=False,
        show_source=lambda html, base_url='': source.append(html),
    )
    web.loadFinished.connect(runtime.qt.on_load_finished)
    web.resize(300, 200)
    web.show()
    try:
        original = animation('cat', '#ff0000')
        updated = animation('cat-with-hat', '#00ff00')
        runtime.commands.set_html({'html': original})
        # The model may inspect the page using the same local name as its code.
        assert runtime.qt.eval("const canvas = document.getElementById('cat'); canvas.id") == 'cat'
        assert runtime.qt.eval("const canvas = document.getElementById('cat'); canvas.id") == 'cat'
        runtime.add_annotation(element={'selector': '#cat'}, note='add a hat')
        runtime.qt.delay(.05)
        assert runtime.qt.js("document.querySelectorAll('.__pygpt_annotation_card').length") == 1
        previous_page = web.page()
        runtime.commands.set_html({'html': updated})
        assert web.page() is not previous_page
        runtime.qt.delay(.05)
        assert runtime.qt.js('window.version') == 'cat-with-hat'
        assert runtime.qt.js('window.frames') > 0
        assert runtime.qt.js('JSON.stringify(Array.from(ctx.getImageData(1,1,1,1).data))') == '[0,255,0,255]'
        runtime.document.show_source()
        assert source[-1] == updated
        runtime.commands.reload({})
        runtime.qt.delay(.05)
        assert runtime.qt.js('window.version') == 'cat-with-hat'
        assert runtime.qt.js('JSON.stringify(Array.from(ctx.getImageData(1,1,1,1).data))') == '[0,255,0,255]'
        assert runtime.qt.js("document.querySelectorAll('.__pygpt_annotation_card').length") == 1
        runtime.qt.js("document.querySelector('.__pygpt_annotation_card button').click(); true")
        runtime.qt.delay(.05)
        assert runtime.annotations == []
        assert not [entry for entry in runtime.console if 'SyntaxError' in entry['message']]
        print('PASS: annotated animation updated, latest source/reload retained, close button works, no redeclaration error')
    finally:
        web.close()
        app.processEvents()


if __name__ == '__main__':
    main()
