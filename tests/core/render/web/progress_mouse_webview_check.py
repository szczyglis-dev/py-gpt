"""Exercise real mouse input with embedded scripts and the application's CSS."""
import json
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--no-sandbox --disable-gpu'
from pathlib import Path
from PySide6.QtCore import QFile, QIODevice, QPoint, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
import pygpt_net.js_rc

app = QApplication([])
view = QWebEngineView()
view.resize(1000, 700)
view.show()
class TestPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, source):
        print(message, line)
page = TestPage(view)
view.setPage(page)
root = Path(__file__).resolve().parents[4]
css = (root / 'src/pygpt_net/data/css/chat.css').read_text().replace('{{', '{').replace('}}', '}')
source = []
for name in ['app-parts-templates-tools.js', 'app-parts-templates-artifacts.js',
             'app-parts-templates-timeline.js', 'app-parts-tools-groups.js',
             'app-template.js', 'app-tool.js', 'app-parts-runtime-workflows.js']:
    resource = QFile(':/js/' + name)
    assert resource.open(QIODevice.ReadOnly), name
    source.append(bytes(resource.readAll()).decode())
setup = '''
const timeline = document.createElement('div'); document.body.append(timeline);
const runtime = {templates:new NodeTemplateEngine(),renderer:{renderPendingMarkdown(){}},scrollMgr:{scheduleScroll(){}}};
runtime.toolOutput = new ToolOutput(null,{templates:runtime.templates,renderer:runtime.renderer});
runtime.workflows = new RuntimeWorkflows(runtime);
runtime.workflows.workflowMessageHost = () => ({timeline});
window.toggleToolOutput = id => runtime.toolOutput.toggle(id);
const hierarchy={calls:[{call_id:'c1',name:'fs_read_file',request:'{}',response:'done'}],workers:[]};
runtime.workflows.setAgentStatus('Working','42','progress-p1',{hierarchy});
const status=timeline.querySelector('.workflow-status');
const summary=status.querySelector('.progress-details > summary');
const arrow=summary.querySelector('.tool-output-arrow');
const rect=summary.getBoundingClientRect();
JSON.stringify({x:rect.x+rect.width/2,y:rect.y+rect.height/2,pointer:getComputedStyle(summary).pointerEvents,arrow:getComputedStyle(arrow).visibility});
'''


def finish(result):
    print(result)
    app.exit(0 if result == 'OK' else 1)


def clicked():
    page.runJavaScript("status.querySelector('.progress-details').open ? (status.getBoundingClientRect().width >= timeline.getBoundingClientRect().width - 25 ? 'OK' : 'progress block does not fill message width') : 'mouse click did not expand status'", finish)


def hovered(result):
    if result != 'visible':
        finish('hover did not reveal arrow: ' + str(result))
        return
    QTest.mouseClick(view.focusProxy(), Qt.LeftButton, Qt.NoModifier, position)
    QTimer.singleShot(150, clicked)


def ready(result):
    global position
    result = json.loads(result) if result else None
    if not isinstance(result, dict) or result.get('pointer') != 'auto' or result.get('arrow') != 'hidden':
        finish('invalid mouse target: ' + str(result))
        return
    position = QPoint(round(result['x']), round(result['y']))
    QTest.mouseMove(view.focusProxy(), position)
    QTimer.singleShot(150, lambda: page.runJavaScript('getComputedStyle(arrow).visibility', hovered))


def loaded(ok):
    page.runJavaScript('\n'.join(source) + '\n' + setup, ready)

page.loadFinished.connect(loaded)
page.setHtml('<html><head><style>' + css + '</style></head><body></body></html>')
QTimer.singleShot(15000, lambda: app.exit(2))
raise SystemExit(app.exec())
