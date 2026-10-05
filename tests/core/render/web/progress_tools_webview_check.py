"""Run with the project Python to exercise live accordions in Qt WebEngine.

QTWEBENGINE_DISABLE_SANDBOX=1 QT_QUICK_BACKEND=software python this_file.py
"""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QTWEBENGINE_CHROMIUM_FLAGS']='--no-sandbox --disable-gpu'
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtCore import QTimer
app=QApplication([])
page=QWebEnginePage()
root = Path(__file__).resolve().parents[4]
source='\n'.join((root / ('src/pygpt_net/data/js/app/'+f)).read_text() for f in [
    'parts/templates/tools.js', 'parts/templates/artifacts.js', 'parts/templates/timeline.js',
    'parts/tools/groups.js', 'template.js', 'tool.js', 'parts/runtime/workflows.js'
])

test='''
const timeline = document.createElement('div'); document.body.append(timeline);
const runtime = {templates: new NodeTemplateEngine(), renderer: {renderPendingMarkdown() {}}, scrollMgr: {scheduleScroll() {}}};
runtime.toolOutput = new ToolOutput(null, {templates:runtime.templates, renderer:runtime.renderer});
runtime.workflows = new RuntimeWorkflows(runtime);
runtime.workflows.workflowMessageHost = () => ({timeline});
window.toggleToolOutput = id => runtime.toolOutput.toggle(id);
const hierarchy = {group_tools:true,calls:[{call_id:'a', name:'fs_read_file', request:'{}'}],workers:[{id:'w1',name:'Worker',status:'running',text:'Reading',calls:[{call_id:'b',name:'search',request:'{}'}]}]};
runtime.workflows.setAgentStatus('Working','7','progress-p1',{hierarchy});
const status=timeline.querySelector('.workflow-status');
const outer=status.querySelector('details'); outer.open=true;
const worker=status.querySelector('.progress-worker'); worker.open=true;
const tool=status.querySelector('.tool-output[id]'); tool.querySelector('button').click();
if(tool.querySelector('button').getAttribute('aria-expanded')!=='true') throw Error('tool did not open');
hierarchy.calls[0].response='done'; hierarchy.calls.push({call_id:'c',name:'write_file',request:'{}'});
runtime.workflows.setAgentStatus('Checking','7','progress-p1',{hierarchy});
if(status!==timeline.querySelector('.workflow-status')) throw Error('status replaced');
if(outer!==status.querySelector('details') || !outer.open) throw Error('outer expansion lost');
if(worker!==status.querySelector('.progress-worker') || !worker.open) throw Error('worker expansion lost');
if(tool!==status.querySelector('.tool-output[id]') || tool.querySelector('button').getAttribute('aria-expanded')!=='true') throw Error('tool expansion lost');
if(!tool.textContent.includes('done')) throw Error('missing output');
if(status.querySelectorAll('.tool-output[id]').length!==2) throw Error('missing tools');
const history=runtime.templates.tools.renderProgress('Checking',hierarchy,'progress-p1');
const replay=document.createElement('div'); replay.innerHTML=history;
if(replay.querySelectorAll('.tool-output[id]').length!==2 || !replay.querySelector('.progress-worker')) throw Error('history hierarchy lost');
'OK';
'''
def loaded(ok):
 page.runJavaScript(source+'\ntry { '+test+' } catch(e) { e.stack; }', lambda result: (print(result), app.exit(0 if result=='OK' else 1)))
page.loadFinished.connect(loaded)
page.setHtml('<html><body></body></html>')
QTimer.singleShot(15000,lambda:app.exit(2))
raise SystemExit(app.exec())
