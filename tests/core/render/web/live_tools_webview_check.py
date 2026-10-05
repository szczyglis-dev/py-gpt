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
    'parts/tools/groups.js', 'template.js', 'tool.js', 'parts/runtime/timeline.js'
])

test=''' 
const timeline = document.createElement('div'); document.body.append(timeline);
const slot = document.createElement('div'); slot.className='msg-part msg-part-status'; timeline.append(slot);
const status = document.createElement('div'); status.className='workflow-status'; status.dataset.statusKind='tool'; slot.append(status);
const prose=document.createElement('div'); prose.textContent='Final answer'; timeline.append(prose);
globalThis.runtime = {templates: new NodeTemplateEngine(), workflows: {workflowMessageHost: () => ({timeline})}, renderer: {renderPendingMarkdown: () => {}}};
const tools = new ToolOutput(null, {templates:runtime.templates, renderer:runtime.renderer, findStatusHost:runtime.workflows.workflowMessageHost});
const timelineRenderer = new RuntimeTimeline({toolOutput:tools, scrollMgr:{}});
const structuralSync = timelineRenderer.syncTimelineStructuralNodes;
globalThis.toggleToolOutput = id => tools.toggle(id);
globalThis.toggleToolGroup = id => tools.toggleGroup(id);
let calls=[{call_id:'a',name:'search',request:'{"query":"one"}'}];
tools.syncLive('7',calls);
const live=status.querySelector('.tool-output');
tools.toggle('live-7');
if(live.querySelector('button').getAttribute('aria-expanded')!=='true') throw Error('opening failed');
const label=live.querySelector('.tool-output-name');
const request=live.querySelector('.tool-output-request-data');
const content=tools._content(live);
const header=live.querySelector('button');
calls=[{...calls[0],response:'{"result":1}'},{call_id:'b',name:'search',request:'{"query":"two"}'}];
tools.syncLive('7',calls);
if(live.querySelector('.tool-output-name')!==label) throw Error('animated label replaced');
if(tools._content(live)!==content || live.querySelector('button')!==header) throw Error('accordion controls replaced');
if(status.querySelector('.tool-output')!==live) throw Error('wrapper replaced');
if(live.querySelector('button').getAttribute('aria-expanded')!=='true') throw Error('expansion lost');
if(live.querySelector('.tool-output-request-data')!==request) throw Error('request replaced');
if(live.querySelectorAll('[data-tool-key]').length!==2) throw Error('repeated call lost');
const shell=document.createElement('div'); shell.innerHTML=runtime.templates.tools.renderToolOutputWrapper({id:-70001,extra:{tool_calls:calls,tool_output_visible:true}});
const desiredTimeline=document.createElement('div');
const desiredPart=document.createElement('div'); desiredPart.className='msg-part'; desiredPart.dataset.partId='p'; desiredPart.append(shell.firstElementChild); desiredTimeline.append(desiredPart);
structuralSync(timeline, desiredTimeline);
const durable=timeline.querySelector('#tool-output--70001'); slot.remove();
if(timeline.firstElementChild!==durable.parentNode || durable.parentNode.nextElementSibling!==prose) throw Error('handoff changed chronology');
if(durable!==live || durable.querySelector('button').getAttribute('aria-expanded')!=='true') throw Error('handoff lost expansion');
if(durable.hasAttribute('data-live-tools')) throw Error('handoff still running');
durable.querySelector('button').click();
if(durable.querySelector('button').getAttribute('aria-expanded')!=='false') throw Error('completed control stopped working');
// Simulate promotion before the next tool round, with a fresh status host.
const nextSlot=document.createElement('div'); nextSlot.className='msg-part msg-part-status'; timeline.append(nextSlot);
const nextStatus=document.createElement('div'); nextStatus.className='workflow-status'; nextStatus.dataset.statusKind='tool'; nextSlot.append(nextStatus);
const originalParent=durable.parentNode;
tools.toggle(-70001);
calls=[...calls,{call_id:'c',name:'fs_append_file',request:'{"text":"new"}'}];
tools.syncLive('7',calls);
if(timeline.querySelectorAll('.tool-output[data-tool-keys]').length!==1) throw Error('continuation created a duplicate');
if(durable.parentNode!==originalParent) throw Error('continuation moved existing series');
if(durable.querySelector('button').getAttribute('aria-expanded')!=='true') throw Error('continuation closed inspected series');
if(durable.querySelectorAll('[data-tool-key]').length!==3) throw Error('continuation lost earlier calls');
// Recover duplicate copies from interleaved snapshot/status events as well.
nextStatus.appendChild(durable.cloneNode(true));
tools.syncLive('7',calls);
if(timeline.querySelectorAll('.tool-output[data-tool-keys]').length!==1) throw Error('duplicate copies were not reconciled');
// A structural snapshot may include the same live status and the durable part.
const desiredStatus=nextSlot.cloneNode(true); desiredTimeline.insertBefore(desiredStatus,desiredPart);
shell.innerHTML=runtime.templates.tools.renderToolOutputWrapper({id:-70001,extra:{tool_calls:calls,tool_output_visible:true}});
desiredPart.replaceChildren(shell.firstElementChild);
structuralSync(timeline, desiredTimeline);
if(timeline.querySelectorAll('.tool-output[data-tool-keys]').length!==1) throw Error('status snapshot duplicated the series');
// A later independent series sharing a tool name must remain separate.
tools.syncLive('7',[{call_id:'separate',name:'search',request:'{}'}]);
if(timeline.querySelectorAll('.tool-output[data-tool-keys]').length!==2) throw Error('independent calls merged by name');
'OK';
'''
def loaded(ok):
 page.runJavaScript(source+'\ntry { '+test+' } catch(e) { e.stack; }', lambda result: (print(result), app.exit(0 if result=='OK' else 1)))
page.loadFinished.connect(loaded)
page.setHtml('<html><body></body></html>')
QTimer.singleShot(15000,lambda:app.exit(2))
raise SystemExit(app.exec())
