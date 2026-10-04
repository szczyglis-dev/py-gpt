// Verify status ownership through the real frontend API without a Qt WebView.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '../../../../src/pygpt_net/data/js/app');
const nodes = [];
class Element {
    constructor() {
        this.children = [];
        this.dataset = {};
        this.style = {};
        this.classList = { add() {}, remove() {} };
        nodes.push(this);
    }
    appendChild(child) { this.insertBefore(child, null); }
    insertBefore(child, before) {
        child.parentNode = this;
        const index = before ? this.children.indexOf(before) : this.children.length;
        this.children.splice(index, 0, child);
    }
    querySelector(selector) {
        const cls = selector.split('.').pop();
        return this.children.find(n => (n.className || '').split(' ').includes(cls)) || null;
    }
    querySelectorAll(selector) {
        const cls = selector.slice(1);
        const result = [];
        for (const child of this.children) {
            if ((child.className || '').split(' ').includes(cls)) result.push(child);
            result.push(...child.querySelectorAll(selector));
        }
        return result;
    }
    closest(selector) {
        let node = this;
        while (node) {
            if ((node.className || '').split(' ').includes(selector.slice(1))) return node;
            node = node.parentNode;
        }
        return null;
    }
}
const context = vm.createContext({
    document: {
        createElement: () => new Element(),
        querySelectorAll: () => nodes.filter(n => n.dataset.workflowStatusId),
    },
    window: {},
});
vm.runInContext(fs.readFileSync(path.join(root, 'parts/runtime/workflows.js'), 'utf8') +
    '\nglobalThis.RuntimeWorkflows = RuntimeWorkflows;', context);
const timeline = new Element();
timeline.className = "msg-timeline";
const workflows = new context.RuntimeWorkflows({ scrollMgr: { scheduleScroll() {} } });
workflows.workflowMessageHost = () => ({ timeline });
workflows.freezeWorkflowStatus = () => {};
workflows._placeWorkflowStatus = (host, status) => host.timeline.appendChild(status.parentNode);
context.runtime = { workflows };
// Exercise the published API as well as the component: dropping the fourth
// argument here would silently restore the original ownership bug.
const bootstrap = fs.readFileSync(path.join(root, 'bootstrap.js'), 'utf8');
vm.runInContext(bootstrap.split('\n').find(line => line.startsWith('window.setAgentStatus =')), context);
const owner = { part_uuid: 'worker-part', agent_name: 'Worker', placement: 'before' };
context.window.setAgentStatus('Using tool: read_file', '42', 'worker-status', owner);
const status = nodes.find(n => n.dataset.workflowStatusId === 'worker-status');
assert.equal(status.parentNode.dataset.statusOwnerPartId, 'worker-part');
assert.equal(status.parentNode.querySelector('.agent-name-prefix').textContent, 'Worker');
assert.equal(status.querySelector('.agents-v2-status__text').textContent, 'Using tool: read_file');
console.log('Frontend status ownership passed.');

const workerText = new Element();
timeline.appendChild(workerText);
const repeatedWorker = workflows.setAgentNamePrefix(workerText, 'Worker');
assert.equal(repeatedWorker.hidden, true);
const supervisorText = new Element();
timeline.appendChild(supervisorText);
assert.equal(workflows.setAgentNamePrefix(supervisorText, 'Supervisor').hidden, false);
const nextWorkerText = new Element();
timeline.appendChild(nextWorkerText);
assert.equal(workflows.setAgentNamePrefix(nextWorkerText, 'Worker').hidden, false);
console.log('Consecutive actor headings grouped.');
