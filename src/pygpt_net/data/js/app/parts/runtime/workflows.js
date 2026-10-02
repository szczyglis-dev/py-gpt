// RuntimeWorkflows owns workflows behavior and state.
class RuntimeWorkflows {

	// ========================================
	// Composition
	// ========================================

	constructor(runtime) {
		this.runtime = runtime;
		this.finalActive = false;
		this._agentWorking = null;
	}

	// ========================================
	// Message hosts and agent names
	// ========================================

	workflowMessageHost = (parentId, create = false, nameHeader = '') => {
		const value = String(parentId || '');
		if (!value) return null;

		let box = document.getElementById(`msg-bot-${value}`);
		let msg = null;
		if (box) {
			try { msg = box.querySelector(':scope > .msg') || box.querySelector('.msg'); }
			catch (_) { msg = box.querySelector('.msg'); }
		}

		// Before the durable item is materialized, statuses/text live in the
		// stream area. Create an id-bound provisional message there so every live
		// event still has one chronological parent instead of becoming a sibling
		// after the footer of the previous message.
		if ((!box || !msg) && create) {
			const container = this.runtime.dom.getStreamContainer();
			if (!container) return null;
			try {
				box = container.querySelector(`.msg-box.msg-bot[data-workflow-parent-id="${value.replace(/"/g, '\\"')}"]`);
			} catch (_) { box = null; }
			if (!box) {
				msg = this.runtime.dom.getStreamMsg(true, nameHeader || '');
				box = msg && msg.closest ? msg.closest('.msg-box.msg-bot') : null;
			} else {
				try { msg = box.querySelector(':scope > .msg') || box.querySelector('.msg'); }
				catch (_) { msg = box.querySelector('.msg'); }
			}
			if (box) {
				box.dataset.workflowParentId = value;
				// Stream boxes have no durable id by default. Giving the live box the
				// final id lets subsequent status/partial events resolve the same host.
				if (!box.id || box.id === `msg-bot-${value}`) box.id = `msg-bot-${value}`;
			}
		}

		if (!box || !msg) return null;
		const timeline = (this.runtime.dom && typeof this.runtime.dom.getMsgTimeline === 'function')
			? this.runtime.dom.getMsgTimeline(msg, true)
			: msg;
		return { box, msg, timeline };
	};

	setAgentNamePrefix = (container, agentName, beforeNode = null) => {
		if (!container) return null;
		const name = String(agentName || '').trim();
		if (!name) return null;

		let prefix = null;
		try { prefix = container.querySelector(':scope > .agent-name-prefix'); }
		catch (_) { prefix = null; }
		if (!prefix) {
			prefix = document.createElement('span');
			prefix.className = 'agent-name-prefix';
			container.insertBefore(prefix, beforeNode || container.firstChild || null);
		}
		prefix.textContent = name;
		const timeline = container.closest ? container.closest('.msg-timeline') : null;
		this.groupAgentNames(timeline || container);
		return prefix;
	};

	groupAgentNames = (timeline) => {
		if (!timeline) return;
		let previous = '';
		for (const prefix of timeline.querySelectorAll('.agent-name-prefix')) {
			const name = String(prefix.textContent || '').trim();
			const duplicate = !!name && name === previous;
			// Keep the node so reconciliation/removal of earlier segments can
			// reveal the group's new first heading without recreating streamed text.
			prefix.hidden = duplicate;
			prefix.style.display = duplicate ? 'none' : '';
			if (name) previous = name;
		}
	};

	// ========================================
	// Workflow status and stream binding
	// ========================================

	freezeWorkflowStatus = (parentId = null, kind = null) => {
		const wantedParent = String(parentId || '');
		const host = wantedParent ? this.workflowMessageHost(wantedParent, false) : null;
		if (wantedParent && !host) return;
		const root = host ? host.timeline : document;
		for (const node of root.querySelectorAll('.agents-v2-status--active')) {
			if (node.classList.contains('agent-working')) continue;
			if (kind && String(node.dataset.statusKind || '') !== String(kind)) continue;
			node.classList.remove('agents-v2-status--active');
		}
	};

	// After beginStream() clears the transient output area, recreate the id-bound
	// stream shell and restore UI-only status history before the first text chunk.
	// This prevents "Planning/Using tool" rows from disappearing at stream start.
	bindWorkflowStream = (parentId, nameHeader = '', records = [], partId = '', agentName = '') => {
		const value = String(parentId || '');
		if (!value) return;

		// Reuse the already visible workflow message whenever possible. Creating a
		// fresh empty stream box while the durable parent already exists changes
		// document height for one frame and makes the Tool row/loading indicator
		// jump between consecutive calls. A provisional box is needed only before
		// the parent message has been materialized anywhere.
		let host = this.workflowMessageHost(value, false);
		let msg = host ? host.msg : null;
		let box = host ? host.box : null;
		let timeline = host ? host.timeline : null;
		if (!msg || !box || !timeline) {
			msg = this.runtime.dom.getStreamMsg(true, String(nameHeader || ''));
			if (!msg) return;
			box = msg.closest ? msg.closest('.msg-box.msg-bot') : null;
			if (box) {
				box.id = `msg-bot-${value}`;
				box.dataset.workflowParentId = value;
			}
			timeline = (this.runtime.dom && typeof this.runtime.dom.getMsgTimeline === 'function')
				? this.runtime.dom.getMsgTimeline(msg, true)
				: msg;
		}
		if (!timeline) return;

		const rows = Array.isArray(records) ? records.slice() : [];
		rows.sort((a, b) => Number((a && a.seq) || 0) - Number((b && b.seq) || 0));
		for (const record of rows) {
			if (!record) continue;
			const kind = String(record.kind || 'agent');
			const sid = String(record.id || '');
			let label = String(record.text || '');
			if (!label && kind === 'tool') label = this._toolStatusLabel(record.tool_names || []);
			if (!label) continue;
			this._setWorkflowStatus(
				value, sid, kind, label, !!record.active,
				{ moveExisting: false, owner: { part_uuid: record.part_uuid, agent_name: record.agent_name } }
			);
			if (kind === 'tool' && Array.isArray(record.live_tool_calls)) {
				this.runtime.toolOutput.syncLive(value, record.live_tool_calls);
			}
		}

		this._bindMainStreamAgentPrefix(timeline, partId, agentName);
	};

	// ========================================
	// Agent status
	// ========================================

	// One transient header per live response. Reuse the same label node so the
	// status shimmer is continuous while the elapsed text changes each second.
	setAgentWorking = (parentId, data) => {
		const id = String(parentId || '');
		if (!id || !data || this.finalActive) return;
		if (this._agentWorking && this._agentWorking.id === id) return;
		this.clearAgentWorking();
		const row = document.createElement('div');
		row.className = 'agent-working agents-v2-status agents-v2-status--active';
		const label = document.createElement('span');
		label.className = 'agents-v2-status__text';
		row.appendChild(label);
		const elapsed = Math.max(0, Date.now() / 1000 - Number(data.started || Date.now() / 1000));
		const started = performance.now();
		const units = Array.isArray(data.units) ? data.units : ['h', 'm', 's'];
		const tick = () => {
			const host = this.workflowMessageHost(id, false);
			if (host && host.msg && row.parentNode !== host.msg) {
				host.msg.insertBefore(row, host.msg.firstChild);
			}
			const seconds = Math.floor(elapsed + (performance.now() - started) / 1000);
			const values = [];
			if (seconds >= 3600) values.push(`${Math.floor(seconds / 3600)}${units[0]}`);
			if (seconds >= 60) values.push(`${Math.floor(seconds / 60) % 60}${units[1]}`);
			values.push(`${seconds % 60}${units[2]}`);
			label.textContent = String(data.label || 'Working for {duration}').replace('{duration}', values.join(' '));
		};
		this._agentWorking = {id, row, timer: setInterval(tick, 1000)};
		tick();
	};

	clearAgentWorking = (parentId = null) => {
		const state = this._agentWorking;
		if (!state || (parentId != null && String(parentId) !== state.id)) return;
		clearInterval(state.timer);
		state.row.remove();
		this._agentWorking = null;
	};

	setAgentStatus = (text, parentId = null, statusId = null, owner = null) => {
		const value = String(text || '').trim();
		if (this.finalActive) {
			this.freezeWorkflowStatus(parentId);
			return;
		}
		if (!value) {
			this.freezeWorkflowStatus(parentId);
			return;
		}

		// One global chronological sequence: a new event freezes whatever was
		// active and is appended after the previous text/tool/status segment.
		this.freezeWorkflowStatus(parentId);
		this._setWorkflowStatus(parentId, statusId, 'agent', value, true, { owner });
		this.runtime.scrollMgr.scheduleScroll(true);
	};

	clearAgentStatus = (parentId = null) => {
		this.freezeWorkflowStatus(parentId);
	};

	// ========================================
	// Tool status
	// ========================================

	hideReasoningForToolCall = (parentId = null) => {
		if (!this.runtime.stream || typeof this.runtime.stream.reasoning.hideReasoningForToolCall !== 'function') return;
		let root = null;
		if (parentId != null && String(parentId || '') !== '') {
			const host = this.workflowMessageHost(parentId, false);
			if (host && host.timeline) root = host.timeline;
		}
		this.runtime.stream.reasoning.hideReasoningForToolCall(root);
	};

	setToolStatus = (names, parentId = null, statusId = null) => {
		const values = Array.isArray(names) ? names.filter(Boolean).map(v => String(v)) : [];
		if (values.length) this.hideReasoningForToolCall(parentId);
		if (this.finalActive) {
			this.freezeWorkflowStatus(parentId, 'tool');
			return;
		}
		if (!values.length) {
			this.freezeWorkflowStatus(parentId, 'tool');
			return;
		}

		// A tool call replaces the label of the existing tool row. Freeze only
		// the previous agent-status row; never toggle the active class on the tool
		// row itself, otherwise the continuous shimmer can visibly restart.
		this.freezeWorkflowStatus(parentId, 'agent');
		this._setWorkflowStatus(
			parentId,
			statusId,
			'tool',
			this._toolStatusLabel(values),
			true,
			{ moveExisting: false }
		);
		this.runtime.scrollMgr.scheduleScroll(true);
	};

	clearToolStatus = (parentId = null, immediate = true) => {
		// Called only when the consecutive tool series reaches a real boundary.
		// The live Tool row intentionally stays active between individual results.
		// With a durable Tool/Tools block ready we remove it atomically; compact
		// status mode freezes it here. STOP/error paths remove it immediately.
		if (!immediate) {
			this.freezeWorkflowStatus(parentId, 'tool');
			return;
		}
		const wantedParent = String(parentId || '');
		const host = wantedParent ? this.workflowMessageHost(wantedParent, false) : null;
		if (wantedParent && !host) return;
		const root = host ? host.timeline : document;
		for (const live of Array.from(root.querySelectorAll('.tool-output[data-live-tools]'))) {
			if (live.closest('.workflow-status')) continue;
			live.removeAttribute('data-live-tools');
			live.classList.remove('tool-output-live');
		}
		for (const node of Array.from(root.querySelectorAll('.workflow-status'))) {
			if (String(node.dataset.statusKind || '') !== 'tool') continue;
			const part = node.closest ? node.closest('.msg-part-status') : null;
			const live = node.querySelector('.tool-output[data-live-tools]');
			if (live) {
				// STOP/error can precede promotion. Retain the inspected payload,
				// retiring only its running state rather than discarding results.
				live.removeAttribute('data-live-tools');
				live.classList.remove('tool-output-live');
				node.parentNode.insertBefore(live, node);
				node.remove();
				continue;
			}
			if (part) part.remove();
			else node.remove();
		}
	};

	// ========================================
	// Message hosts and agent names internals
	// ========================================

	_bindMainStreamAgentPrefix = (timeline, partId, agentName) => {
		const name = String(agentName || '').trim();
		if (!timeline || !name) return null;

		let root = null;
		try { root = timeline.querySelector(':scope > .md-snapshot-root'); }
		catch (_) { root = null; }
		if (!root) return null;

		const prefix = this.setAgentNamePrefix(timeline, name, root);
		if (prefix) {
			prefix.dataset.streamAgentPrefix = '1';
			if (partId) prefix.dataset.partId = String(partId);
			if (prefix.nextSibling !== root) timeline.insertBefore(prefix, root);
		}
		return prefix;
	};

	// ========================================
	// Workflow status and stream binding internals
	// ========================================

	_findWorkflowStatus = (statusId) => {
		const sid = String(statusId || '');
		if (!sid) return null;
		for (const node of document.querySelectorAll('[data-workflow-status-id]')) {
			if (String(node.dataset.workflowStatusId || '') === sid) return node;
		}
		return null;
	};

	_createWorkflowStatus = (parentId, statusId, kind) => {
		const host = this.workflowMessageHost(parentId, true);
		if (!host || !host.timeline) return null;

		const part = document.createElement('div');
		part.className = 'msg-part msg-part-status';
		part.dataset.statusPart = '1';

		const status = document.createElement('div');
		status.className = 'agents-v2-status workflow-status';
		status.dataset.statusKind = String(kind || 'agent');
		if (statusId) status.dataset.workflowStatusId = String(statusId);

		const label = document.createElement('span');
		label.className = 'agents-v2-status__text';
		status.appendChild(label);
		part.appendChild(status);
		this._placeWorkflowStatus(host, status);
		return status;
	};

	_placeWorkflowStatus = (host, status) => {
		if (!host || !host.timeline || !status) return;
		const part = status.closest ? status.closest('.msg-part-status') : null;
		if (!part) return;

		// A status that arrives before the very first text token must stay before
		// the empty generic-stream placeholder, because that placeholder will later
		// be filled with prose. But an empty placeholder is NOT proof that the whole
		// timeline is empty: after a tool boundary, prose may already live in a
		// nested msg-part while the obsolete direct root is still present. In that
		// case the new status must append after the existing prose.
		let streamRoot = null;
		try { streamRoot = host.timeline.querySelector(':scope > .md-snapshot-root'); }
		catch (_) { streamRoot = null; }
		const nodeHasPayload = (node) => {
			if (!node || node.nodeType !== Node.ELEMENT_NODE) return false;
			const el = node;
			if (el.classList && el.classList.contains('msg-part-status')) return false;
			if (el.classList && el.classList.contains('agent-name-prefix')) return false;
			if (el === streamRoot || (el.classList && el.classList.contains('md-snapshot-root'))) {
				return !!(String(el.textContent || '').trim() || (el.children && el.children.length > 0));
			}
			if (el.matches && el.matches('.md-block, .tool-output')) return true;
			if (el.querySelector && el.querySelector('.md-block, .tool-output')) return true;
			const nestedRoot = el.querySelector ? el.querySelector('.md-snapshot-root') : null;
			if (nestedRoot && (String(nestedRoot.textContent || '').trim() || nestedRoot.children.length > 0)) return true;
			return !!String(el.textContent || '').trim();
		};
		let hasEarlierPayload = false;
		for (const child of Array.from(host.timeline.children || [])) {
			if (child === part) continue;
			if (nodeHasPayload(child)) { hasEarlierPayload = true; break; }
		}
		const rootHasContent = !!(streamRoot && nodeHasPayload(streamRoot));
		if (streamRoot && !rootHasContent && !hasEarlierPayload) {
			let streamPrefix = null;
			try { streamPrefix = host.timeline.querySelector(':scope > .agent-name-prefix[data-stream-agent-prefix="1"]'); }
			catch (_) { streamPrefix = null; }
			host.timeline.insertBefore(part, streamPrefix || streamRoot);
		} else {
			host.timeline.appendChild(part);
		}
	};

	_setWorkflowStatus = (parentId, statusId, kind, labelText, active = true, options = null) => {
		const opts = Object.assign({
			moveExisting: true
		}, options || {});
		let status = this._findWorkflowStatus(statusId);
		const existed = !!status;
		if (!status) status = this._createWorkflowStatus(parentId, statusId, kind);
		if (!status) return null;
		if (existed && opts.moveExisting) {
			// Normal agent/status updates may advance to the newest chronological
			// slot. Tool-series updates explicitly opt out: one Tool row must keep
			// exactly the same DOM position for the whole consecutive tool round.
			const host = this.workflowMessageHost(parentId, false);
			if (host) this._placeWorkflowStatus(host, status);
		}
		if (opts.owner && opts.owner.agent_name) {
			const part = status.closest('.msg-part-status');
			if (part) {
				part.dataset.statusOwnerPartId = String(opts.owner.part_uuid || '');
				this.setAgentNamePrefix(part, String(opts.owner.agent_name), status);
			}
		}
		status.dataset.statusKind = String(kind || 'agent');
		if (statusId) status.dataset.workflowStatusId = String(statusId);
		let label = status.querySelector('.agents-v2-status__text');
		if (!label) {
			label = document.createElement('span');
			label.className = 'agents-v2-status__text';
			status.appendChild(label);
		}
		label.textContent = String(labelText || '');
		if (active) {
			// Keep an already-active node active. Consecutive tool calls only change
			// its label, so the shimmer continues without a CSS animation restart.
			status.classList.add('agents-v2-status--active');
		} else {
			status.classList.remove('agents-v2-status--active');
		}
		return status;
	};

	// ========================================
	// Tool status internals
	// ========================================

	_toolStatusLabel = (values) => {
		const names = Array.isArray(values) ? values.filter(Boolean).map(v => String(v)) : [];
		if (!names.length) return '';
		const prefix = names.length > 1
			? ((typeof window !== 'undefined' && window.LOCALE_TOOLS) ? String(window.LOCALE_TOOLS) : 'Tools')
			: ((typeof window !== 'undefined' && window.LOCALE_TOOL) ? String(window.LOCALE_TOOL) : 'Tool');
		return `${prefix}: ${names.join(', ')}...`;
	};

}
