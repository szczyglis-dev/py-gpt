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
    // Finalization can precede the first animation-frame drain of a short reply.
    begin('queued-final');
    beginStream(false,'queued-final');
    appendStream('', 'Short final answer');
    mutate('finalize_output',node('queued-final','Short final answer'));
    await settle();
    expect(document.querySelectorAll('#msg-bot-queued-final').length===1,'queued final duplicated');
    expect(!document.querySelector('#_append_output_ .msg-box.msg-bot'),'late stream copy survived finalization');
    expect(document.querySelector('#_nodes_ #msg-bot-queued-final')?.textContent.includes('Short final answer'),'queued final text lost');
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

    const raw = JSON.stringify({cmd:'read_file',result:[{path:'one.txt',content:'<script>unsafe</script>\n```'},{path:'two.txt',content:'second'}]});
    const friendly = [{label:'one.txt',text:'<script>unsafe</script>\n```',language:'text'},{label:'two.txt',text:'second',language:'text'}];
    appendNode(JSON.stringify(node(20,'',{tool_calls:[{call_id:'read',name:'read_file',request:'{"cmd":"read_file","params":{"path":["one.txt","two.txt"]}}',response:raw,response_friendly:friendly}]})));
    await settle();
    const tool = document.querySelector('#tool-output-20');
    expect(tool, 'friendly tool missing');
    const readable = tool.querySelector('.tool-view-friendly');
    expect(readable.querySelectorAll('.code-wrapper').length === 2, 'multiple files not separated');
    expect(readable.querySelector('.code-header-lang').textContent.trim() === 'one.txt', 'filename header lost');
    expect(readable.querySelector('pre code').textContent.includes('<script>unsafe</script>'), 'literal content lost');
    expect(!readable.querySelector('script'), 'tool text interpreted as HTML');
    expect(!readable.querySelector('.code-header-run'), 'tool payload acquired execute action');
    expect(!tool.querySelector('.tool-output-result-data .code-header-tool-view'),'output switch duplicated');
    const viewButton = tool.querySelector('.tool-output-request-data .code-header-tool-view');
    expect(viewButton && viewButton.nextElementSibling.classList.contains('code-header-collapse'), 'view action order');
    expect(viewButton.title === 'Surowy JSON', 'initial tooltip not translated');
    viewButton.click();
    expect(viewButton.title === 'Zwykły tekst', 'plain text tooltip not translated');
    expect(viewButton.getAttribute('aria-label') === 'Zwykły tekst', 'view action label not translated');
    expect(document.documentElement.dataset.toolView === 'raw', 'raw switch failed');
    expect(sessionStorage.getItem('pygpt.toolView') === 'raw', 'preference not saved');
    viewButton.click();
    expect(document.documentElement.dataset.toolView === 'friendly', 'friendly switch failed');
    const payload = tool.querySelector('.tool-payload');
    expect(JSON.parse(payload.getAttribute('data-tool-raw')).result.length === 2, 'raw response lost');

    for (const [id,language,code] of [[21,'python','print(1)'],[22,'bash','echo hi'],[23,'text','plain text']]) {
        appendNode(JSON.stringify(node(id,'',{tool_calls:[{call_id:'code-'+id,name:'example',request:'{"params":{}}',
            request_friendly:[{text:code,label:language,language}]}]})));
        await settle();
        const block = document.querySelector('#tool-output-'+id);
        expect(block.querySelector('.tool-view-friendly .code-header-lang').textContent.trim()===language,'native input header '+language);
        const expected = language==='text' ? 'plaintext' : language;
        expect(block.querySelector('.tool-view-friendly code').className.includes(expected),'native highlighting '+language);
        expect(block.querySelector('.tool-view-raw .code-header-lang').textContent.trim()==='Input','raw input header changed');
    }

    document.querySelectorAll('.tool-output-data pre code').forEach(code => {
        expect(code.classList.contains('no-highlight'), 'tool payload permits syntax highlighting');
        expect(code.getAttribute('data-highlighted') === 'yes', 'tool payload enters highlight queue');
        expect(!code.querySelector('span[class*="hljs-"]'), 'tool payload contains syntax colors');
    });

    // Changing every tool above the clicked input must preserve its viewport position.
    const fixture = document.createElement('div');
    fixture.innerHTML = `<style>
        .tool-view-raw {display:none}
        html[data-tool-view="raw"] .tool-view-raw {display:block}
        html[data-tool-view="raw"] .tool-view-friendly {display:none}
    </style><div class="tool-view-friendly" style="height:900px"></div>
    <div class="tool-view-raw" style="height:1600px"></div>
    <div class="tool-output-request-data"><button onclick="toggleToolPayloadView(this)">&lt;&gt;</button></div>
    <div style="height:2000px"></div>`;
    document.body.appendChild(fixture);
    runtime.scrollMgr.suspendAutoFollow();
    const input = fixture.querySelector('.tool-output-request-data');
    const switcher = input.querySelector('button');
    Utils.SE.scrollTop += input.getBoundingClientRect().top - 180;
    await settle();
    for (let i=0; i<2; i++) {
        const before = input.getBoundingClientRect().top;
        switcher.click();
        await new Promise(resolve => setTimeout(resolve, 350));
        expect(Math.abs(input.getBoundingClientRect().top-before)<2, 'tool view switch moved viewport');
    }
    fixture.remove();

    clearNodes();

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
    scripts = '<script>window.LOCALE_TOOL_VIEW_PLAIN="Zwykły tekst";window.LOCALE_TOOL_VIEW_RAW="Surowy JSON";</script>' + '\n'.join(f'<script src="qrc:///js/{name}"></script>' for name in vendors + files)
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
QTimer.singleShot(45000, lambda: (print("FAIL: WebView timeout", page.errors), application.exit(2)))
start_next()
raise SystemExit(application.exec())
