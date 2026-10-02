// Stable window API consumed by Python and message controls.
window.__collapsed_idx = window.__collapsed_idx || [];

const runtime = new Runtime();

document.addEventListener('DOMContentLoaded', () => runtime.init());

Object.defineProperty(window, 'SE', {
	get() {
		return Utils.SE;
	}
});

window.beginStream = (chunk, preserveParentId = null) => runtime.streaming.beginStream(chunk, preserveParentId);
window.bindStreamOwner = (msgId) => runtime.streaming.bindStreamOwner(msgId);
window.endStream = () => runtime.streaming.endStream();
window.applyStream = (name, chunk) => runtime.streaming.applyStream(name, chunk);
window.appendStream = (name, chunk) => runtime.streaming.appendStream(name, chunk);
window.appendStreamTyped = (type, name, chunk) => runtime.streaming.onChunk(name, chunk, type);
window.nextStream = () => runtime.streaming.nextStream();
window.clearStream = () => runtime.streaming.clearStream();
window.appendPartialStream = (parentId, partId, chunk, begin, agentName) => runtime.partials.appendPartialStream(parentId, partId, chunk, begin, agentName);
window.bindWorkflowStream = (parentId, nameHeader, records, partId, agentName) => runtime.workflows.bindWorkflowStream(parentId, nameHeader, records, partId, agentName);
window.setAgentStatus = (text, parentId, statusId) => runtime.workflows.setAgentStatus(text, parentId, statusId);
window.clearAgentStatus = (parentId) => runtime.workflows.clearAgentStatus(parentId);
window.setToolStatus = (names, parentId, statusId) => runtime.workflows.setToolStatus(names, parentId, statusId);
window.clearToolStatus = (parentId, immediate = true) => runtime.workflows.clearToolStatus(parentId, immediate);
window.freezeWorkflowStatus = (parentId, kind) => runtime.workflows.freezeWorkflowStatus(parentId, kind);

window.begin = (msgId = '') => runtime.turns.begin(msgId);
window.end = (msgId = '') => runtime.turns.end(msgId);

window.appendNode = (payload) => runtime.messages.appendNode(payload);
window.replaceNodes = (payload) => runtime.messages.replaceNodes(payload);
window.appendToInput = (html) => runtime.messages.appendToInput(html);

window.clearNodes = () => runtime.messages.clearNodes();
window.clearInput = () => runtime.messages.clearInput();
window.clearOutput = () => runtime.messages.clearOutput();
window.clearLive = () => runtime.messages.clearLive();

window.appendToolOutput = (c) => runtime.toolOutput.append(c);
window.updateToolOutput = (c) => runtime.toolOutput.update(c);
window.clearToolOutput = () => runtime.toolOutput.clear();
window.beginToolOutput = () => runtime.view.beginToolOutput();
window.endToolOutput = () => runtime.toolOutput.end();
window.enableToolOutput = () => runtime.toolOutput.enable();
window.disableToolOutput = () => runtime.toolOutput.disable();
window.toggleToolOutput = (id) => runtime.toolOutput.toggle(id);
window.toggleToolGroup = (id) => runtime.toolOutput.toggleGroup(id);
window.toggleExtraItems = (button) => runtime.ui.toggleExtraItems(button);

window.appendExtra = (id, c) => runtime.nodes.appendExtra(id, c, runtime.scrollMgr);
window.removeNode = (id) => runtime.nodes.removeNode(id, runtime.scrollMgr);
window.removeNodesFromId = (id) => runtime.nodes.removeNodesFromId(id, runtime.scrollMgr);

window.replaceLive = (c) => runtime.messages.replaceLive(c);
window.updateFooter = (c) => runtime.view.updateFooter(c);

window.enableEditIcons = () => runtime.ui.enableEditIcons();
window.disableEditIcons = () => runtime.ui.disableEditIcons();
window.enableTimestamp = () => runtime.ui.enableTimestamp();
window.disableTimestamp = () => runtime.ui.disableTimestamp();
window.enableBlocks = () => runtime.ui.enableBlocks();
window.disableBlocks = () => runtime.ui.disableBlocks();
window.updateCSS = (s) => runtime.ui.updateCSS(s);

window.getScrollPosition = () => runtime.view.getScrollPosition();
window.setScrollPosition = (pos) => runtime.view.setScrollPosition(pos);

window.showLoading = (delayMs = 0, waitForInput = false) => runtime.loading.show(delayMs, waitForInput);
window.hideLoading = (reserveSpace = false) => runtime.loading.hide(reserveSpace);

window.restoreCollapsedCode = (root) => runtime.renderer.restoreCollapsedCode(root);
window.scrollToTopUser = () => runtime.scrollMgr.scrollToTopUser();
window.scrollToBottomUser = () => runtime.scrollMgr.scrollToBottomUser();

window.showTips = () => runtime.tips.show();
window.hideTips = () => runtime.tips.hide();

window.getCustomMarkupRules = () => runtime.customMarkup.getRules();
window.setCustomMarkupRules = (rules) => runtime.view.setCustomMarkupRules(rules);

window.__pygpt_cleanup = () => runtime.cleanup();
window.setAgentWorking = (parentId, data) => runtime.workflows.setAgentWorking(parentId, data);
window.clearAgentWorking = () => runtime.workflows.clearAgentWorking();

window.syncLiveTools = (parentId, calls) => runtime.toolOutput.syncLive(parentId, calls);
