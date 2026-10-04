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
             'app-template.js', 'app-tool.js', 'app-events.js']:
    resource = QFile(':/js/' + name)
    assert resource.open(QIODevice.ReadOnly), name
    source.append(bytes(resource.readAll()).decode())
setup = '''
const templates=new NodeTemplateEngine();
const text='Pierwsza linia\\nDruga linia';
document.body.innerHTML=templates.renderNode({id:42,input:{text,time_label:'17:34',edit_title:'Edit',edit_icon:''}});
const region=document.querySelector('.msg-user-region');
const bar=region.querySelector('.user-message-actions');
const before=region.getBoundingClientRect().height;
window.copiedText='';
const events=new EventManager({}, {get:key=>key==='container'?document.body:null}, new Proxy({}, {get:()=>()=>{}}), null, null, null, {copyCode:text=>{window.copiedText=text;}});
events.install();
const rect=region.getBoundingClientRect();
JSON.stringify({x:rect.x+3,y:rect.y+rect.height/2,pointer:'auto',arrow:getComputedStyle(bar).visibility});
'''


def finish(result):
    if result == 'OK':
        QTest.mouseMove(view.focusProxy(), QPoint(5, 650))
        QTimer.singleShot(250, lambda: page.runJavaScript("getComputedStyle(bar).visibility === 'hidden' ? 'OK' : 'action bar remains visible after mouse leaves'", finished_leave))
        return
    print(result)
    app.exit(0 if result == 'OK' else 1)


def finished_leave(result):
    print(result)
    app.exit(0 if result == 'OK' else 1)


def clicked():
    page.runJavaScript("copiedText === text && region.getBoundingClientRect().height === before && !region.querySelector('.msg .msg-copy-btn') && bar.querySelector('time').textContent === '17:34' && bar.querySelector('.user-edit-btn').getAttribute('href') === 'extra-edit:42' ? 'OK' : 'copy, edit, timestamp or layout failure'", finish)


def copy_position(result):
    point = json.loads(result)
    QTest.mouseClick(view.focusProxy(), Qt.LeftButton, Qt.NoModifier, QPoint(round(point['x']),round(point['y'])))
    QTimer.singleShot(150, clicked)


def hovered(result):
    if result != 'visible':
        finish('hover did not reveal action bar: ' + str(result))
        return
    page.runJavaScript("JSON.stringify((()=>{const r=bar.querySelector('.msg-copy-btn').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})())", copy_position)


def ready(result):
    global position
    result = json.loads(result) if result else None
    if not isinstance(result, dict) or result.get('pointer') != 'auto' or result.get('arrow') != 'hidden':
        finish('invalid mouse target: ' + str(result))
        return
    position = QPoint(round(result['x']), round(result['y']))
    QTest.mouseMove(view.focusProxy(), position)
    QTimer.singleShot(150, lambda: page.runJavaScript('getComputedStyle(bar).visibility', hovered))


def loaded(ok):
    page.runJavaScript('\n'.join(source) + '\n' + setup, ready)

page.loadFinished.connect(loaded)
page.setHtml('<html><head><style>' + css + '</style></head><body></body></html>')
QTimer.singleShot(15000, lambda: app.exit(2))
raise SystemExit(app.exec())
