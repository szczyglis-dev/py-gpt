// Verify immediate attachment rendering without waiting for an output mutation.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const path = require('path');
const root = path.resolve(__dirname, '../../../../src/pygpt_net/data/js/app');
for (const file of ['parts/templates/tools.js', 'parts/templates/artifacts.js', 'parts/templates/timeline.js', 'template.js', 'nodes.js']) {
    vm.runInThisContext(fs.readFileSync(path.join(root, file), 'utf8'));
}
global.UserCollapseManager = class { apply() {} };
let rendered = '';
const area = {insertAdjacentHTML: (_, html) => { rendered = html; }, querySelectorAll: () => []};
const templates = new NodeTemplateEngine();
const nodes = new NodesManager({get: () => area}, {cfg: {}}, null, null, null, templates);
nodes.appendToInput('__PYGPT_INPUT_V1__' + JSON.stringify({
    text: 'My prompt',
    user_attachments: {
        images: {1: {url: 'file:///image.png', path: 'file:///image.png'}},
        files: {1: {url: 'file:///file.pdf', basename: 'file.pdf', icon_url: 'qrc:///filetypes/pdf.svg'}}
    }
}));
assert(rendered.includes('bridge://open_image/file:///image.png'));
assert(rendered.includes('qrc:///filetypes/pdf.svg'));
assert(rendered.indexOf('user-attachment-files') < rendered.indexOf('user-attachment-images'));
assert(rendered.indexOf('user-attachments') < rendered.indexOf('msg-box msg-user'));
assert(rendered.includes('My prompt'));
assert(rendered.startsWith('<div class="msg-user-region input-live-arrival">'));
assert(rendered.includes('<div class="user-message-actions" aria-hidden="true"></div>'));
nodes.appendToInput('Legacy prompt');
assert(rendered.includes('Legacy prompt'));
assert(rendered.includes('user-message-actions'));
console.log('OK: immediate image/file attachment rendering and legacy input');
