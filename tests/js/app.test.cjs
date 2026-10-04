// Run with: node --test tests/js/app.test.cjs
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const app = path.resolve(__dirname, '../../src/pygpt_net/data/js/app');
function environment() {
    const context = vm.createContext({console, Map, Set, WeakMap, TextDecoder, TextEncoder,
        performance: {now: () => 100}, setTimeout, clearTimeout, setInterval, clearInterval,
        document: {createElement: () => ({
            content: {querySelectorAll: () => []},
            set textContent(value) {this._text=value;},
            get innerHTML() {return String(this._text || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
        })},
        navigator: {userAgent: ''}});
    vm.runInContext('window = globalThis; self = globalThis;', context);
    const files = JSON.parse(fs.readFileSync(path.join(app,'manifest.json'), 'utf8'));
    for (const file of files.filter(f => f !== 'bootstrap.js')) {
        vm.runInContext(fs.readFileSync(path.join(app, file), 'utf8'), context, {filename: file});
    }
    const vendor = path.resolve(app, '../markdown-it/markdown-it.min.js');
    vm.runInContext(fs.readFileSync(vendor, 'utf8'), context);
    vm.runInContext(`
        const cfg = new Config();
        cfg.REASONING.SHOW_REALTIME = true;
        const logger = {debug(){},debug_obj(){}};
        const markup = new CustomMarkup(cfg, logger);
        const renderer = new MarkdownRenderer(cfg, markup, logger, {}, {});
        renderer.init();
        const engine = new StreamEngine(cfg, {}, renderer, {}, {}, {}, {}, {}, {}, logger);
        globalThis.subject = {engine, renderer, markup, cfg};
    `, context);
    return context;
}
function run(context, source) {return JSON.parse(vm.runInContext(`JSON.stringify(${source})`,context));}

test('manifest includes every source once and boots last', () => {
    const files=JSON.parse(fs.readFileSync(path.join(app,'manifest.json'),'utf8'));
    assert.equal(new Set(files).size,files.length);
    const sources=fs.readdirSync(app,{recursive:true}).filter(f=>f.endsWith('.js')).sort();
    assert.deepEqual([...files].sort(),sources);
    assert.equal(files.at(-1),'bootstrap.js');
    const resource=fs.readFileSync(path.resolve(app,'../../../js.qrc'),'utf8');
    const resourceFiles=[...resource.matchAll(/>data\/js\/app\/([^<]+)<\/file>/g)].map(match=>match[1]);
    assert.deepEqual(resourceFiles,files);
    const bundle=fs.readFileSync(path.resolve(app,'../app.min.js'),'utf8');
    const bundledFiles=[...bundle.matchAll(/\/\* data\/js\/app\/(.+?) \*\//g)].map(match=>match[1]);
    assert.deepEqual(bundledFiles,files);
});
test('buffer preserves chunk order, deltas, materialization and reset', () => {
    const c=environment();
    vm.runInContext(`subject.engine.buffer.append('alpha'); subject.engine.buffer.append(' βeta');`,c);
    assert.equal(run(c,'subject.engine.buffer.getStreamText()'),'alpha βeta');
    assert.equal(run(c,'subject.engine.buffer.getDeltaSince(7)'),'eta');
    vm.runInContext('subject.engine.buffer.materialize(); subject.engine.buffer.append("!");',c);
    assert.equal(run(c,'subject.engine.buffer.getStreamLength()'),11);
    assert.equal(run(c,'subject.engine.buffer.getStreamText()'),'alpha βeta!');
    vm.runInContext('subject.engine.reset()',c);
    assert.equal(run(c,'subject.engine.buffer.getStreamText()'),'');
});
test('fences recognize fragmented openers, nested markers and custom delimiters', () => {
    const c=environment();
    for(const chunk of ['```py','thon\n','print(1)\n']) vm.runInContext(`subject.engine.fences.updateFenceHeuristic(${JSON.stringify(chunk)})`,c);
    assert.equal(run(c,'subject.engine.fences.fenceOpen'),true);
    vm.runInContext('subject.engine.fences.updateFenceHeuristic("```\\n")',c);
    assert.equal(run(c,'subject.engine.fences.fenceOpen'),false);
    vm.runInContext('subject.engine.reset(); subject.engine.fences.updateFenceHeuristic("> ```js\\nconst x=1;\\n")',c);
    assert.equal(run(c,'subject.engine.fences.fenceOpen'),true);
    vm.runInContext('subject.engine.fences.updateFenceHeuristic("```\\n")',c);
    assert.equal(run(c,'subject.engine.fences.fenceOpen'),false);
    vm.runInContext('subject.engine.reset(); subject.engine.fences.setCustomFenceSpecs([{open:"<code>",close:"</code>"}]); subject.engine.fences.updateFenceHeuristic("<code>hello\\n")',c);
    assert.equal(run(c,'subject.engine.fences.fenceOpen'),true);
    vm.runInContext('subject.engine.fences.updateFenceHeuristic("</code>")',c);
    assert.equal(run(c,'subject.engine.fences.fenceOpen'),false);
});
test('reasoning distinguishes thinking, closing tags and actual response text', () => {
    const c=environment();
    const update=s=>run(c,`subject.engine.reasoning.updateReasoningVisibilityFromChunk(${JSON.stringify(s)})`);
    update('<think>analysis');
    assert.equal(run(c,'subject.engine.reasoning.reasoningThinking'),true);
    assert.equal(update('</think>').hasResponseText,false);
    assert.equal(update('  ').hasResponseText,false);
    assert.equal(update('Answer').hasResponseText,true);
    update('<think>again');
    assert.equal(run(c,'subject.engine.reasoning.reasoningThinking'),true);
    vm.runInContext('subject.engine.reset()',c);
    assert.equal(run(c,'subject.engine.reasoning.reasoningVisible'),false);
});
test('Markdown keeps math, links, fenced code, escaping and independent code counters', () => {
    const c=environment();
    const render=(s,final=false)=>run(c,`subject.renderer.${final?'renderFinalSnapshot':'renderStreamingSnapshot'}(${JSON.stringify(s)})`);
    assert.match(render('$x$ and \\(y\\)'),/math-pending/);
    assert.match(render('[local](file:///tmp/test.txt)'),/href="file:\/\/\/tmp\/test.txt"/);
    assert.doesNotMatch(render('[bad](javascript:alert(1))'),/href="javascript:/);
    const first=render('```output\n<&>\n```',true);
    assert.match(first,/data-index="1"/);
    assert.match(first,/language-python/);
    assert.match(run(c, 'subject.renderer.MD.renderer.rules.fence([{info:"output",content:"<&>"}], 0, {}, null)'), /&lt;&amp;&gt;/);
    assert.doesNotMatch(first,/code-header-run/);
    const streaming=render('```output\nhello\n```');
    assert.match(streaming,/data-index="1"/);
    assert.match(render('```output\nagain\n```',true),/data-index="3"/);
});
test('source markup respects fenced code and streaming delimiters', () => {
    const c=environment();
    vm.runInContext(`subject.markup.setRules([{name:'reasoning',open:'<think>',close:'</think>',phase:'source',openReplace:'**',closeReplace:'**'}]);`,c);
    assert.equal(run(c,'subject.markup.source.transformSource("<think>text</think>")'),'**text**');
    assert.equal(run(c,'subject.markup.source.transformSource("```\\n<think>text</think>\\n```")'),'```\n<think>text</think>\n```');
});
