"""Exercise both frontend loaders in real Qt WebEngine.

Run with QTWEBENGINE_DISABLE_SANDBOX=1 QT_QUICK_BACKEND=software and project Python.
"""
import json
import os
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--no-sandbox --disable-gpu')

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage
import pygpt_net.js_rc  # Register actual resources used by the application.

ROOT = Path(__file__).resolve().parents[4]
APP = ROOT / 'src/pygpt_net/data/js/app'

TEST = r"""
(async () => {
    const expect = (value, message) => { if (!value) throw Error(message); };
    const settle = () => new Promise(resolve => setTimeout(resolve, 80));
    const node = (id, text, extra={}) => ({id,input:{text:'Question'},output:{text},extra});
    const mutate = (op, block, options={}) => appendNode(JSON.stringify({mutation:{op,block,...options}}));
    expect(typeof beginStream === 'function' && typeof syncLiveTools === 'function', 'host API missing');
    expect(runtime.renderer.MD && runtime.templates, 'runtime did not initialize');
    appendNode(JSON.stringify(node(1,'Old **answer**')));
    await settle();
    expect(document.querySelector('#msg-bot-1 strong')?.textContent==='answer','history markdown');
    begin('2');
    beginStream(false,'2');
    bindStreamOwner('2');
    appendStream('', 'Hello **world**\n\n');
    runtime.streamQ.drain();
    runtime.raf.flush();
    await settle();
    expect(document.getElementById('msg-bot-2')?.textContent.includes('Hello'),'text stream missing');
    setAgentStatus('Planning','2','agent-2');
    setToolStatus(['search'],'2','tool-2');
    syncLiveTools('2',[{call_id:'a',name:'search',request:'query'}]);
    expect(document.querySelector('[data-live-tools]'),'live tools missing');
    toggleToolOutput('live-2');
    expect(document.querySelector('[data-live-tools] button').getAttribute('aria-expanded')==='true','tool toggle');
    mutate('finalize_output',node(2,'Hello **world**'));
    end('2');
    await settle();
    expect(document.querySelectorAll('#msg-bot-2').length===1,'duplicate durable turn');
    expect(document.querySelector('#_nodes_ #msg-bot-2'),'turn not promoted to history');
    appendPartialStream('2','part-1','Extra **answer**',true,'Agent');
    await settle();
    expect(document.querySelector('#msg-bot-2 [data-live-part] strong')?.textContent==='answer','partial markdown');
    mutate('append_artifact',null,{msg_id:2,extra:{html:'<span id="artifact-check">file</span>'}});
    expect(document.getElementById('artifact-check'),'artifact missing');
    beginStream(false,'3');
    bindStreamOwner('3');
    applyStream('', '```python\nprint(1)\n');
    runtime.raf.flush();
    runtime.stream.code.schedulePromoteTail(true);
    runtime.raf.flush();
    await settle();
    applyStream('', 'print(2)\n```\n');
    runtime.raf.flush();
    await settle();
    endStream();
    expect(document.querySelector('#msg-bot-3 pre code')?.textContent.includes('print(2)'),'code stream missing');
    setCustomMarkupRules([{name:'strong',open:'<stronger>',close:'</stronger>',phase:'source',openReplace:'**',closeReplace:'**'}]);
    expect(runtime.renderer.renderFinalSnapshot('<stronger>x</stronger>').includes('<strong>x</strong>'),'custom markup rules');
    replaceNodes(JSON.stringify([node(4,'New history')]));
    await settle();
    expect(!document.getElementById('msg-bot-1') && document.querySelector('#_nodes_ #msg-bot-4'),'history replacement');
    expect(!document.querySelector('[data-live-part]'),'partial state retained after replace');
    appendNode(JSON.stringify({id:5,output:{text:''},extra:{tool_calls:[{call_id:'one',name:'search',request:'a'}]}}));
    appendNode(JSON.stringify({id:6,output:{text:''},extra:{tool_chain_continuation:true,tool_calls:[{call_id:'two',name:'search',request:'b'}]}}));
    await settle();
    const group = document.querySelector('.tool-output-group');
    expect(group && group.querySelectorAll('.msg-box.msg-bot').length===2,'consecutive tool grouping');
    toggleToolGroup(group.id);
    expect(group.querySelector('button').getAttribute('aria-expanded')==='true','group toggle');
    for (let id=7; id<11; id++) appendNode(JSON.stringify({id,output:{text:'Historical answer '+id},extra:{}}));
    await settle();
    runtime.scrollMgr.virtualization.refreshMessageVirtualization();
    expect(document.querySelector('.msg-virtualized'),'history virtualization');
    clearNodes();
    clearInput(); clearOutput(); clearLive();
    expect(!document.querySelector('#_nodes_ .msg-box'),'clear history');
    __pygpt_cleanup();
    return 'OK';
})().then(result => window.__testResult=result).catch(error => window.__testResult=error.stack);
"""


class Page(QWebEnginePage):
    def __init__(self):
        super().__init__()
        self.errors = []

    def javaScriptConsoleMessage(self, level, message, line, source):
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            self.errors.append(f'{source}:{line}: {message}')


def html(production):
    vendors = ['markdown-it.min.js', 'highlight.min.js', 'katex.min.js', 'auto-render.min.js']
    files = ['app.min.js'] if production else [
        'app-' + name.replace('/', '-') for name in json.loads((APP / 'manifest.json').read_text())
    ]
    scripts = '\n'.join(f'<script src="qrc:///js/{name}"></script>' for name in vendors + files)
    return '<!doctype html><html><head>' + scripts + '</head><body><div id="container">' + ''.join(
        f'<div id="{name}"></div>' for name in [
            '_nodes_', '_append_input_', '_append_output_before_', '_append_output_',
            '_append_live_', '_footer_', '_loader_', 'tips'
        ]
    ) + '</div><button id="scrollFab"><img id="scrollFabIcon"></button></body></html>'


application = QApplication([])
page = Page()
modes = iter([False, True])
current_mode = False


def start_next():
    global current_mode
    try:
        current_mode = next(modes)
    except StopIteration:
        print('OK: development and production frontend')
        application.exit(0)
        return
    page.errors.clear()
    page.setHtml(html(current_mode), QUrl('qrc:///'))


def loaded(success):
    if not success:
        print('FAIL: resource load')
        application.exit(1)
        return
    page.runJavaScript(TEST)
    QTimer.singleShot(150, check)


def check():
    def result(value):
        if not value:
            QTimer.singleShot(100, check)
        elif value != 'OK' or page.errors:
            print('FAIL:', 'production' if current_mode else 'development', value, page.errors)
            application.exit(1)
        else:
            QTimer.singleShot(0, start_next)
    page.runJavaScript('window.__testResult || null', result)


page.loadFinished.connect(loaded)
QTimer.singleShot(20000, lambda: application.exit(2))
start_next()
raise SystemExit(application.exec())
