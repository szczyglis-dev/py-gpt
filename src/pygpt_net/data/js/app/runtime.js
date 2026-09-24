// ==========================================================================
// Runtime
// ==========================================================================

class Runtime {

	// Main runtime manager for the application.
	constructor() {
		this.cfg = new Config();
		this.logger = new Logger(this.cfg);

		this.dom = new DOMRefs();
		this.customMarkup = new CustomMarkup(this.cfg, this.logger);
		this.raf = new RafManager(this.cfg);

		// Ensure logger uses central RafManager for its internal tick pump.
		try {
			this.logger.bindRaf(this.raf);
		} catch (_) {}

		this.async = new AsyncRunner(this.cfg, this.raf);
		this.renderer = new MarkdownRenderer(this.cfg, this.customMarkup, this.logger, this.async, this.raf);

		this.math = new MathRenderer(this.cfg, this.raf, this.async);
		this.codeScroll = new CodeScrollState(this.cfg, this.raf);
		this.highlighter = new Highlighter(this.cfg, this.codeScroll, this.raf);
		this.scrollMgr = new ScrollManager(this.cfg, this.dom, this.raf);
		this.toolOutput = new ToolOutput();
		this.loading = new Loading(this.dom);
		this.nodes = new NodesManager(this.dom, this.renderer, this.highlighter, this.math, this.toolOutput);
		this.bridge = new BridgeManager(this.cfg, this.logger);
		this.ui = new UIManager();
		this.stream = new StreamEngine(this.cfg, this.dom, this.renderer, this.math, this.highlighter, this.codeScroll, this.scrollMgr, this.raf, this.async, this.logger);
		this.streamQ = new StreamQueue(this.cfg, this.stream, this.scrollMgr, this.raf);
		this.events = new EventManager(this.cfg, this.dom, this.scrollMgr, this.highlighter, this.codeScroll, this.toolOutput, this.bridge);

		try {
			this.stream.setCustomFenceSpecs(this.customMarkup.getSourceFenceSpecs());
		} catch (_) {}

		this.templates = new NodeTemplateEngine(this.cfg, this.logger);
		this.data = new DataReceiver(this.cfg, this.templates, this.nodes, this.scrollMgr);

		this.tips = null;
		this._lastHeavyResetMs = 0;
		this._turnSession = 0;
		this._agentsV2FinalActive = false;
		this._workflowCollapseSeq = 0;
		// Message ids whose response lifecycle is still active. Action buttons for
		// these messages stay invisible while their footer slot remains in layout.
		this._activeTurnIds = new Set();
		// Live post-tool prose is rendered as a nested partial of an existing
		// durable bot message, never as a second msg-box / CtxItem row.
		this._partialStreams = new Map();

		this.renderer.hooks.observeNewCode = (root, opts) => this.highlighter.observeNewCode(root, opts, this.stream.activeCode);
		this.renderer.hooks.observeMsgBoxes = (root) => this.highlighter.observeMsgBoxes(root, (box) => {
			this.highlighter.observeNewCode(box, {
				deferLastIfStreaming: true,
				minLinesForLast: this.cfg.PROFILE_CODE.minLinesForHL,
				minCharsForLast: this.cfg.PROFILE_CODE.minCharsForHL
			}, this.stream.activeCode);
			this.codeScroll.initScrollableBlocks(box);
		});
		this.renderer.hooks.scheduleMathRender = (root) => {
			const mm = getMathMode();
			if (mm === 'idle') this.math.schedule(root);
			else if (mm === 'always') this.math.schedule(root, 0, true);
		};
		this.renderer.hooks.codeScrollInit = (root) => this.codeScroll.initScrollableBlocks(root);
	}

	// Reset stream state and optionally perform a heavy reset of schedulers and observers.
	resetStreamState(origin, opts) {
		try {
			this.streamQ.clear();
		} catch (_) {}

		const def = Object.assign({
			finalizeActive: true,
			clearBuffer: true,
			clearMsg: false,
			defuseOrphans: true,
			forceHeavy: false,
			reason: String(origin || 'external-op')
		}, (opts || {}));

		const now = Utils.now();
		const withinDebounce = (now - (this._lastHeavyResetMs || 0)) <= (this.cfg.RESET.HEAVY_DEBOUNCE_MS || 24);
		const mustHeavyByOrigin =
			def.forceHeavy === true || def.clearMsg === true ||
			origin === 'beginStream' || origin === 'nextStream' ||
			origin === 'clearStream' || origin === 'replaceNodes' ||
			origin === 'clearNodes' || origin === 'clearOutput' ||
			origin === 'clearLive' || origin === 'clearInput';
		const shouldHeavy = mustHeavyByOrigin || !withinDebounce;
		const suppressLog = withinDebounce && origin !== 'beginStream';

		try {
			this.stream.abortAndReset({
				...def,
				suppressLog
			});
		} catch (_) {}

		if (shouldHeavy) {
			try {
				this.highlighter.cleanup();
			} catch (_) {}
			try {
				this.math.cleanup();
			} catch (_) {}
			try {
				this.codeScroll.cancelAllScrolls();
			} catch (_) {}
			try {
				this.scrollMgr.cancelPendingScroll();
			} catch (_) {}
			try {
				this.raf.cancelAll();
			} catch (_) {}
			this._lastHeavyResetMs = now;
		} else {
			try {
				this.raf.cancelGroup('StreamQueue');
			} catch (_) {}
		}

		try {
			this.tips && this.tips.hide();
		} catch (_) {}
	}

	// API: handle incoming chunk (from bridge).
	api_onChunk = (name, chunk, type) => {
		const t = String(type || 'text_delta');
		if (t === 'text_delta') {
			this.api_appendStream(name, chunk);
			return;
		}
		if (t === 'final_reset') {
			try { this.loading.hide(false); } catch (_) {}
			// Keep the already materialized durable CtxItem and clear only the
			// transient global stream/status area. Final prose will be appended via
			// appendPartialStream() into the same msg-bot element.
			this.api_clearAgentStatus();
			this.api_clearStream();
			// A late queued tool/status event must not reappear during final prose.
			this._agentsV2FinalActive = true;
			return;
		}
		// Future-proof: add other chunk types here (attachments, status, etc.)
		// No-op for unknown types to keep current behavior.
		this.logger.debug('STREAM', 'IGNORED_NON_TEXT_CHUNK', {
			type: t,
			len: (chunk ? String(chunk).length : 0)
		});
	};

	// API: begin stream.
	api_beginStream = (chunk = false, preserveParentId = null) => {
		this._agentsV2FinalActive = false;
		this._turnSession += 1;
		this.tips && this.tips.hide();

		// Consecutive tool-only continuations belong to one visual turn. If the
		// id-bound workflow host already exists, preserve it instead of clearing
		// and recreating the same Tool row on every provider round. This removes
		// the otherwise visible vertical jump between tools.
		const parentKey = String(preserveParentId || '');
		// STREAM_BEGIN always carries the durable owner id when available. This is
		// the reliable ownership point for freshly-created contexts whose BEGIN may
		// have fired before ctx.id was allocated.
		if (parentKey) this._markTurnActive(parentKey);
		const existingWorkflowHost = parentKey ? this._statusMessageHost(parentKey, false) : null;
		const streamContainer = this.dom.getStreamContainer();
		const preserveWorkflowHost = !!(
			existingWorkflowHost && streamContainer &&
			streamContainer.contains(existingWorkflowHost.box)
		);
		this.resetStreamState('beginStream', {
			clearMsg: !preserveWorkflowHost,
			finalizeActive: false,
			forceHeavy: !preserveWorkflowHost
		});
		this.stream.beginStream(chunk, !preserveWorkflowHost);
	};

	// API: end stream.
	api_endStream = () => {
		this.stream.endStream();
	};

	// API: apply chunk.
	api_applyStream = (name, chunk) => {
		this.stream.applyStream(name, chunk);
	};

	// API: enqueue chunk (drained on rAF).
	api_appendStream = (name, chunk) => {
		this.streamQ.enqueue(name, chunk);
	};

	// API: move current output to "before" area and prepare for next stream.
	api_nextStream = () => {
		this.tips && this.tips.hide();
		const element = this.dom.get('_append_output_');
		const before = this.dom.get('_append_output_before_');
		if (element && before) {
			const frag = document.createDocumentFragment();
			while (element.firstChild) frag.appendChild(element.firstChild);
			before.appendChild(frag);
		}
		this.resetStreamState('nextStream', {
			clearMsg: true,
			finalizeActive: false,
			forceHeavy: true
		});
		this.scrollMgr.scheduleScroll(true);
	};

	// API: clear streaming output area entirely.
	api_clearStream = () => {
		this.tips && this.tips.hide();
		this.resetStreamState('clearStream', {
			clearMsg: true,
			forceHeavy: true
		});
		const el = this.dom.getStreamContainer();
		if (!el) return;
		el.replaceChildren();
	};

	_partialStreamKey = (parentId, partId) => `${String(parentId)}::${String(partId)}`;

	_clearPartialStreamState = () => {
		this._partialStreams.clear();
	};

	_workflowMessageHost = (parentId, create = false, nameHeader = '') => {
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
			const container = this.dom.getStreamContainer();
			if (!container) return null;
			try {
				box = container.querySelector(`.msg-box.msg-bot[data-workflow-parent-id="${value.replace(/"/g, '\\"')}"]`);
			} catch (_) { box = null; }
			if (!box) {
				msg = this.dom.getStreamMsg(true, nameHeader || '');
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
		const timeline = (this.dom && typeof this.dom.getMsgTimeline === 'function')
			? this.dom.getMsgTimeline(msg, true)
			: msg;
		return { box, msg, timeline };
	};

	_findPartialStreamHost = (parentId, partId, create = false) => {
		const host = this._workflowMessageHost(parentId, create);
		if (!host || !host.timeline) return null;

		const pid = String(partId);
		let part = null;
		for (const node of host.timeline.querySelectorAll('.msg-part[data-live-part="1"]')) {
			if (String(node.dataset.partId || '') === pid) { part = node; break; }
		}
		if (!part && !create) return null;
		if (!part) {
			part = document.createElement('div');
			part.className = 'msg-part msg-part-live';
			part.dataset.livePart = '1';
			part.dataset.partId = pid;
			const root = document.createElement('div');
			root.className = 'md-snapshot-root';
			part.appendChild(root);

			// getStreamMsg() creates one direct md-snapshot-root as a placeholder for
			// the initial generic stream. Once the workflow switches to explicit
			// inline partials that placeholder is no longer a chronological segment.
			// Leaving it behind made later status rows think that no text had been
			// rendered yet and insert themselves *before* prose that already lived in
			// a msg-part. Remove only a truly empty direct placeholder; never touch a
			// root that already contains streamed text.
			let placeholder = null;
			try { placeholder = host.timeline.querySelector(':scope > .md-snapshot-root'); }
			catch (_) { placeholder = null; }
			if (placeholder) {
				const hasText = !!String(placeholder.textContent || '').trim();
				const hasElements = placeholder.children && placeholder.children.length > 0;
				if (!hasText && !hasElements) {
					try { placeholder.remove(); } catch (_) {}
				}
			}

			// Timeline children are append-only. Every new prose/tool/status segment
			// lands after what was already shown.
			host.timeline.appendChild(part);
		}
		let root = part.querySelector('.md-snapshot-root');
		if (!root) {
			root = document.createElement('div');
			root.className = 'md-snapshot-root';
			part.appendChild(root);
		}
		return { ...host, part, root };
	};

	_renderPartialStream = (state) => {
		if (!state || !state.root || !state.root.isConnected) return false;
		let frag = null;
		try {
			frag = this.renderer.renderStreamingSnapshotFragment(state.text || '');
		} catch (_) {
			frag = document.createDocumentFragment();
			frag.appendChild(document.createTextNode(state.text || ''));
		}
		state.root.replaceChildren(frag);

		try {
			// Streaming custom markup must also materialize an opener that has no
			// closer yet. This makes <think> become a CSS reasoning block from the
			// very first tag, including post-tool inline partials.
			this.customMarkup.applyStream(state.root, this.renderer.MD_STREAM || this.renderer.MD);
		} catch (_) {}
		try { this.stream._syncReasoningVisibility(state.root); } catch (_) {}
		try {
			this.highlighter.observeNewCode(state.root, {
				deferLastIfStreaming: true,
				minLinesForLast: this.cfg.PROFILE_CODE.minLinesForHL,
				minCharsForLast: this.cfg.PROFILE_CODE.minCharsForHL
			}, this.stream.activeCode);
			this.highlighter.scanVisibleCodesInRoot(state.root, this.stream.activeCode || null);
		} catch (_) {}
		try { this.codeScroll.initScrollableBlocks(state.root); } catch (_) {}
		try {
			const mm = getMathMode();
			if (mm === 'idle') this.math.schedule(state.root);
			else if (mm === 'always') this.math.schedule(state.root, 0, true);
		} catch (_) {}
		this.scrollMgr.scheduleScroll(true);
		return true;
	};

	// Append streamed Markdown into a nested partial of an existing assistant
	// turn. A missing durable node gets a provisional id-bound stream host; it is
	// never rendered as an unrelated second message.
	api_appendPartialStream = (parentId, partId, chunk, begin = false) => {
		const key = this._partialStreamKey(parentId, partId);
		let state = this._partialStreams.get(key) || null;
		if (begin || !state || (state.root && !state.root.isConnected)) {
			const host = this._findPartialStreamHost(parentId, partId, true);
			if (!host) {
				const finalLatch = this._agentsV2FinalActive;
				// Python owns loader visibility and knows whether this is hidden
				// reasoning or actual response text. Do not hide the loader here.
				if (!state || !state.fallback) this.api_beginStream(false);
				this._agentsV2FinalActive = finalLatch;
				state = { fallback: true, text: '' };
				this._partialStreams.set(key, state);
			} else {
				state = { ...host, text: '' };
				this._partialStreams.set(key, state);
			}
		}

		const value = String(chunk || '');
		if (!value) return;
		if (state.fallback) {
			this.api_appendStream('', value);
			return;
		}
		let reasoningState = null;
		try { reasoningState = this.stream._updateReasoningVisibilityFromChunk(value); } catch (_) {}
		state.text += value;
		this._renderPartialStream(state);
		try {
			if (reasoningState && reasoningState.hasResponseText && !this.stream.reasoningThinking) {
				this.stream._scheduleReasoningHide(state.msg || null, state.root || null);
			}
		} catch (_) {}
	};

	_statusMessageHost = (parentId, create = false) => this._workflowMessageHost(parentId, create);

	_findWorkflowStatus = (statusId) => {
		const sid = String(statusId || '');
		if (!sid) return null;
		for (const node of document.querySelectorAll('[data-workflow-status-id]')) {
			if (String(node.dataset.workflowStatusId || '') === sid) return node;
		}
		return null;
	};

	_createWorkflowStatus = (parentId, statusId, kind) => {
		const host = this._statusMessageHost(parentId, true);
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
			host.timeline.insertBefore(part, streamRoot);
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
			const host = this._statusMessageHost(parentId, false);
			if (host) this._placeWorkflowStatus(host, status);
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

	_toolStatusLabel = (values) => {
		const names = Array.isArray(values) ? values.filter(Boolean).map(v => String(v)) : [];
		if (!names.length) return '';
		const prefix = names.length > 1
			? ((typeof window !== 'undefined' && window.LOCALE_TOOLS) ? String(window.LOCALE_TOOLS) : 'Tools')
			: ((typeof window !== 'undefined' && window.LOCALE_TOOL) ? String(window.LOCALE_TOOL) : 'Tool');
		return `${prefix}: ${names.join(', ')}...`;
	};

	api_freezeWorkflowStatus = (parentId = null, kind = null) => {
		const wantedParent = String(parentId || '');
		const host = wantedParent ? this._statusMessageHost(wantedParent, false) : null;
		if (wantedParent && !host) return;
		const root = host ? host.timeline : document;
		for (const node of root.querySelectorAll('.agents-v2-status--active')) {
			if (kind && String(node.dataset.statusKind || '') !== String(kind)) continue;
			node.classList.remove('agents-v2-status--active');
		}
	};

	api_setAgentStatus = (text, parentId = null, statusId = null) => {
		const value = String(text || '').trim();
		if (this._agentsV2FinalActive) {
			this.api_freezeWorkflowStatus(parentId);
			return;
		}
		if (!value) {
			this.api_freezeWorkflowStatus(parentId);
			return;
		}

		// One global chronological sequence: a new event freezes whatever was
		// active and is appended after the previous text/tool/status segment.
		this.api_freezeWorkflowStatus(parentId);
		this._setWorkflowStatus(parentId, statusId, 'agent', value, true);
		this.scrollMgr.scheduleScroll(true);
	};

	api_clearAgentStatus = (parentId = null) => {
		this.api_freezeWorkflowStatus(parentId);
	};

	_hideReasoningForToolCall = (parentId = null) => {
		if (!this.stream || typeof this.stream.hideReasoningForToolCall !== 'function') return;
		let root = null;
		if (parentId != null && String(parentId || '') !== '') {
			const host = this._statusMessageHost(parentId, false);
			if (host && host.timeline) root = host.timeline;
		}
		this.stream.hideReasoningForToolCall(root);
	};

	api_setToolStatus = (names, parentId = null, statusId = null) => {
		const values = Array.isArray(names) ? names.filter(Boolean).map(v => String(v)) : [];
		if (values.length) this._hideReasoningForToolCall(parentId);
		if (this._agentsV2FinalActive) {
			this.api_freezeWorkflowStatus(parentId, 'tool');
			return;
		}
		if (!values.length) {
			this.api_freezeWorkflowStatus(parentId, 'tool');
			return;
		}

		// A tool call replaces the label of the existing tool row. Freeze only
		// the previous agent-status row; never toggle the active class on the tool
		// row itself, otherwise the continuous shimmer can visibly restart.
		this.api_freezeWorkflowStatus(parentId, 'agent');
		this._setWorkflowStatus(
			parentId,
			statusId,
			'tool',
			this._toolStatusLabel(values),
			true,
			{ moveExisting: false }
		);
		this.scrollMgr.scheduleScroll(true);
	};

	api_clearToolStatus = (parentId = null, immediate = true) => {
		// Called only when the consecutive tool series reaches a real boundary.
		// The live Tool row intentionally stays active between individual results.
		// With a durable Tool/Tools block ready we remove it atomically; compact
		// status mode freezes it here. STOP/error paths remove it immediately.
		if (!immediate) {
			this.api_freezeWorkflowStatus(parentId, 'tool');
			return;
		}
		const wantedParent = String(parentId || '');
		const host = wantedParent ? this._statusMessageHost(wantedParent, false) : null;
		if (wantedParent && !host) return;
		const root = host ? host.timeline : document;
		for (const node of Array.from(root.querySelectorAll('.workflow-status'))) {
			if (String(node.dataset.statusKind || '') !== 'tool') continue;
			const part = node.closest ? node.closest('.msg-part-status') : null;
			if (part) part.remove();
			else node.remove();
		}
	};

	// After beginStream() clears the transient output area, recreate the id-bound
	// stream shell and restore UI-only status history before the first text chunk.
	// This prevents "Planning/Using tool" rows from disappearing at stream start.
	api_bindWorkflowStream = (parentId, nameHeader = '', records = []) => {
		const value = String(parentId || '');
		if (!value) return;

		// Reuse the already visible workflow message whenever possible. Creating a
		// fresh empty stream box while the durable parent already exists changes
		// document height for one frame and makes the Tool row/loading indicator
		// jump between consecutive calls. A provisional box is needed only before
		// the parent message has been materialized anywhere.
		let host = this._statusMessageHost(value, false);
		let msg = host ? host.msg : null;
		let box = host ? host.box : null;
		let timeline = host ? host.timeline : null;
		if (!msg || !box || !timeline) {
			msg = this.dom.getStreamMsg(true, String(nameHeader || ''));
			if (!msg) return;
			box = msg.closest ? msg.closest('.msg-box.msg-bot') : null;
			if (box) {
				box.id = `msg-bot-${value}`;
				box.dataset.workflowParentId = value;
			}
			timeline = (this.dom && typeof this.dom.getMsgTimeline === 'function')
				? this.dom.getMsgTimeline(msg, true)
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
				{ moveExisting: false }
			);
		}
	};

	// ------------------------------------------------------------------
	// Unified renderer mutation transport.
	// ------------------------------------------------------------------
	_parseRenderMutation = (payload) => {
		let obj = payload;
		if (typeof obj === 'string') {
			const text = obj.trim();
			if (!text || text[0] !== '{') return null;
			try { obj = JSON.parse(text); } catch (_) { return null; }
		}
		if (!obj || typeof obj !== 'object' || !obj.mutation || typeof obj.mutation !== 'object') return null;
		return obj.mutation;
	};

	_flushStreamQueueNow = () => {
		try {
			let guard = 0;
			while (this.streamQ && this.streamQ._qCount && this.streamQ._qCount() > 0 && guard++ < 10000) {
				this.streamQ.drain();
			}
		} catch (_) {}
	};

	_mutationElement = (block, role) => {
		if (!block) return null;
		try {
			const html = this.templates.renderNode(block);
			const tmp = document.createElement('div');
			tmp.innerHTML = html;
			return tmp.querySelector(role === 'user' ? '.msg-box.msg-user' : '.msg-box.msg-bot');
		} catch (_) { return null; }
	};

	_appendDurableInput = (block) => {
		if (!block || !block.input || !block.input.text) return;
		const id = String(block.id == null ? '' : block.id);
		if (!id || document.getElementById(`msg-user-${id}`)) return;
		const nodes = this.dom.get('_nodes_');
		if (!nodes) return;
		try {
			const inputOnly = Object.assign({}, block, {output: null});
			const html = this.templates.renderNode(inputOnly);
			nodes.insertAdjacentHTML('beforeend', html);
			nodes.classList.remove('empty_list');
			this.nodes._materializeUserMdAsPlainText(nodes);
			this.nodes._userCollapse.apply(nodes);
			this.nodes._ensureUserCopyIcons(nodes);
		} catch (_) {}

		// Input is transient too. Never let a late sync for an older turn clear
		// the input row that already belongs to a newer request.
		try {
			const input = this.dom.get('_append_input_');
			const owner = input && input.dataset ? String(input.dataset.renderMsgId || '') : '';
			if (!owner || owner === id) {
				this.dom.clearInput();
				if (input && input.dataset) delete input.dataset.renderMsgId;
			}
		} catch (_) {}
	};

	_replaceInputMutation = (mutation) => {
		const block = mutation.block || null;
		if (!block) return;
		const id = String(mutation.msg_id != null ? mutation.msg_id : (block.id != null ? block.id : ''));
		if (!id) return;
		const target = document.getElementById(`msg-user-${id}`);
		const desired = this._mutationElement(block, 'user');
		if (!desired) return;
		if (target) target.replaceWith(desired);
		else {
			const nodes = this.dom.get('_nodes_');
			if (!nodes) return;
			nodes.appendChild(desired);
			nodes.classList.remove('empty_list');
		}
		try {
			this.nodes._materializeUserMdAsPlainText(desired.parentNode || desired);
			this.nodes._userCollapse.apply(desired.parentNode || desired);
			this.nodes._ensureUserCopyIcons(desired.parentNode || desired);
		} catch (_) {}
	};

	_postMutation = (root) => {
		if (!root) return;
		try {
			const maybe = this.renderer.renderPendingMarkdown(root);
			const done = () => {
				try { this.nodes._onBox(root); } catch (_) {}
				try { this.nodes._refreshToolGroups(this.dom.get('_nodes_')); } catch (_) {}
				try { this.scrollMgr.endMessageMutation(root); } catch (_) {}
				try { this.scrollMgr.syncBottomNowIfFollowing(); } catch (_) {}
				this.scrollMgr.scheduleMessageVirtualizationRefresh();
				this.scrollMgr.scheduleScroll(true);
			};
			if (maybe && typeof maybe.then === 'function') maybe.then(done); else done();
		} catch (_) {
			try { this.scrollMgr.endMessageMutation(root); } catch (__) {}
		}
	};

	_directTimelineChild = (timeline, predicate) => {
		if (!timeline || !timeline.children || typeof predicate !== 'function') return null;
		for (const child of Array.from(timeline.children)) {
			try { if (predicate(child)) return child; } catch (_) {}
		}
		return null;
	};

	_timelinePartById = (timeline, partId, kind = '') => {
		const value = String(partId || '');
		if (!timeline || !value) return null;
		return this._directTimelineChild(timeline, (el) => {
			if (!el.classList || !el.classList.contains('msg-part')) return false;
			if (String((el.dataset && el.dataset.partId) || '') !== value) return false;
			if (kind === 'inline') return el.classList.contains('msg-part-inline');
			if (kind === 'content') {
				return !el.classList.contains('msg-part-inline')
					&& !el.classList.contains('msg-part-status');
			}
			return true;
		});
	};

	_syncTimelineStructuralNodes = (timeline, desiredTimeline) => {
		if (!timeline || !desiredTimeline) return;

		// Inline Autonomous/judge messages are part of the currently followed turn.
		// Remember FOLLOW ownership before changing geometry: if the user did not
		// manually stop following, materializing a new inline row must immediately
		// move the viewport behind that row instead of waiting for async Markdown
		// post-processing or for the next stream chunk.
		const followInlineInsert = !!(this.scrollMgr && this.scrollMgr.autoFollow === true);
		let inlineInserted = false;

		// Block-level tool output is structural: update it from the authoritative
		// snapshot, but never touch neighboring streamed prose.
		try {
			Array.from(timeline.children).forEach((el) => {
				if (el.classList && el.classList.contains('tool-output')
						&& !el.classList.contains('agent-workflow-output')) el.remove();
			});
			for (const el of Array.from(desiredTimeline.children)) {
				if (el.classList && el.classList.contains('tool-output')
						&& !el.classList.contains('agent-workflow-output')) {
					timeline.appendChild(el.cloneNode(true));
				}
			}
		} catch (_) {}

		// Partial timelines are incremental. Add only structural rows that cannot
		// be produced by token streaming: Autonomous inline messages and tool-only
		// partials. Text-bearing partials are deliberately left untouched.
		try {
			for (const desiredPart of Array.from(desiredTimeline.children)) {
				if (!desiredPart.classList || !desiredPart.classList.contains('msg-part')) continue;
				const partId = String((desiredPart.dataset && desiredPart.dataset.partId) || '');
				const isInline = desiredPart.classList.contains('msg-part-inline');
				const hasText = !!desiredPart.querySelector('.md-block');
				const hasTool = !!desiredPart.querySelector('.tool-output');
				if (!isInline && (!hasTool || hasText)) continue;

				let existing = partId ? this._timelinePartById(timeline, partId, isInline ? 'inline' : 'content') : null;
				if (!existing) {
					timeline.appendChild(desiredPart.cloneNode(true));
					if (isInline) inlineInserted = true;
					continue;
				}
				if (isInline) continue;

				// A tool result may become UI-ready after the partial itself already
				// exists. Reconcile only its tool controls, preserving prose nodes.
				Array.from(existing.children).forEach((child) => {
					if (child.classList && child.classList.contains('tool-output')) child.remove();
				});
				for (const child of Array.from(desiredPart.children)) {
					if (child.classList && child.classList.contains('tool-output')) {
						existing.appendChild(child.cloneNode(true));
					}
				}
			}
		} catch (_) {}

		if (inlineInserted && followInlineInsert) {
			try {
				// Reassert FOLLOW synchronously after the DOM insertion. This is not a
				// forced user scroll: it only runs when FOLLOW already owned the viewport.
				// resumeAutoFollow(true) also marks the resulting scroll as programmatic,
				// so the scroll listener cannot misclassify it as manual upward movement.
				this.scrollMgr.resumeAutoFollow(true);
			} catch (_) {}
		}
	};

	_insertCollapsedWorkflowSummary = (timeline, desiredSummary, finalNode, token, target) => {
		if (!timeline || !desiredSummary) return;
		if (target && target.dataset && String(target.dataset.workflowCollapseToken || '') !== String(token)) return;
		let existing = this._directTimelineChild(timeline, (el) =>
			el.classList && el.classList.contains('agent-workflow-output')
		);
		if (existing) existing.remove();

		const summary = desiredSummary.cloneNode(true);
		try {
			if (finalNode && finalNode.parentNode === timeline) timeline.insertBefore(summary, finalNode);
			else timeline.insertBefore(summary, timeline.firstChild || null);
		} catch (_) { return; }

		try {
			const reduced = typeof window !== 'undefined' && window.matchMedia
				&& window.matchMedia('(prefers-reduced-motion: reduce)').matches;
			if (!reduced && typeof summary.animate === 'function') {
				summary.animate(
					[{opacity: 0, transform: 'translateY(-3px)'}, {opacity: 1, transform: 'translateY(0)'}],
					{duration: 140, easing: 'ease-out'}
				);
			}
		} catch (_) {}

		try {
			const maybe = this.renderer.renderPendingMarkdown(summary);
			const done = () => {
				try { this.nodes._onBox(target || summary); } catch (_) {}
				try { this.scrollMgr.scheduleMessageVirtualizationRefresh(); } catch (_) {}
				try { this.scrollMgr.scheduleScroll(true); } catch (_) {}
			};
			if (maybe && typeof maybe.then === 'function') maybe.then(done); else done();
		} catch (_) {}
	};

	_collapseCompletedWorkflow = (target, timeline, desiredTimeline, block) => {
		if (!target || !timeline || !desiredTimeline || !block) return false;
		const workflow = block.extra && block.extra.collapsed_workflow;
		const compactFinal = block.extra && block.extra.agents_v2_compact_final;
		const workflowSteps = compactFinal ? Number(compactFinal.workflow_steps || 0) : 0;
		// Compact-final is a collapse command, not merely a marker that a final
		// response exists. A one-shot Agents v2 answer has no preceding workflow
		// and must never enter the fold/remove path.
		if (!workflow && (!compactFinal || workflowSteps <= 0)) return false;
		const desiredSummary = this._directTimelineChild(desiredTimeline, (el) =>
			el.classList && el.classList.contains('agent-workflow-output')
		);

		const already = this._directTimelineChild(timeline, (el) =>
			el.classList && el.classList.contains('agent-workflow-output')
		);
		if (already) return true;

		const finalPartId = String((compactFinal && compactFinal.final_part_id) || (workflow && workflow.final_part_id) || '');
		let finalNode = finalPartId ? this._timelinePartById(timeline, finalPartId, 'content') : null;
		if (!finalNode) {
			const textNodes = Array.from(timeline.children || []).filter((el) => {
				if (!el || !el.classList) return false;
				if (el.classList.contains('msg-part-inline') || el.classList.contains('msg-part-status')) return false;
				try { return !!el.querySelector('.md-block') || el.classList.contains('md-block'); }
				catch (_) { return false; }
			});
			finalNode = textNodes.length ? textNodes[textNodes.length - 1] : null;
		}

		const stale = Array.from(timeline.children || []).filter((el) =>
			el !== finalNode && !(el.classList && el.classList.contains('agent-workflow-output'))
		);
		const token = String(++this._workflowCollapseSeq);
		if (target.dataset) target.dataset.workflowCollapseToken = token;

		if (!stale.length) {
			if (desiredSummary) {
				this._insertCollapsedWorkflowSummary(timeline, desiredSummary, finalNode, token, target);
			}
			return true;
		}

		let reduced = false;
		try {
			reduced = typeof window !== 'undefined' && window.matchMedia
				&& window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		} catch (_) {}
		const duration = reduced ? 0 : 180;
		const animations = [];
		for (const el of stale) {
			if (!el) continue;
			if (duration <= 0 || typeof el.animate !== 'function') continue;
			try {
				const rect = el.getBoundingClientRect();
				const style = window.getComputedStyle ? window.getComputedStyle(el) : null;
				const fromMarginTop = style ? style.marginTop : '0px';
				const fromMarginBottom = style ? style.marginBottom : '0px';
				const animation = el.animate([
					{opacity: 1, height: `${Math.max(0, rect.height)}px`, marginTop: fromMarginTop, marginBottom: fromMarginBottom, overflow: 'hidden'},
					{opacity: 0, height: '0px', marginTop: '0px', marginBottom: '0px', overflow: 'hidden'}
				], {duration, easing: 'ease-in-out', fill: 'forwards'});
				animations.push(animation.finished.catch(() => {}));
			} catch (_) {}
		}

		const finish = () => {
			if (target.dataset && String(target.dataset.workflowCollapseToken || '') !== token) return;
			for (const el of stale) {
				try { if (el && el.parentNode === timeline) el.remove(); } catch (_) {}
			}
			if (desiredSummary) {
				this._insertCollapsedWorkflowSummary(timeline, desiredSummary, finalNode, token, target);
			}
		};
		if (!animations.length) finish();
		else Promise.all(animations).then(finish).catch(finish);
		return true;
	};

	_turnId = (value) => {
		if (value == null) return '';
		return String(value).trim();
	};

	_messageActionSlot = (target, create = false) => {
		if (!target) return null;
		let msg = null;
		try { msg = target.querySelector(':scope > .msg') || target.querySelector('.msg'); }
		catch (_) { try { msg = target.querySelector('.msg'); } catch (__) {} }
		if (!msg) return null;
		let actions = null;
		try { actions = msg.querySelector(':scope > .action-icons'); }
		catch (_) { try { actions = msg.querySelector('.action-icons'); } catch (__) {} }
		if (!actions && create && this.dom && typeof this.dom._ensureStreamFooterPlaceholder === 'function') {
			actions = this.dom._ensureStreamFooterPlaceholder(msg);
		}
		return actions || null;
	};

	_setMessageActionsPending = (target, pending) => {
		const actions = this._messageActionSlot(target, true);
		if (!actions) return;
		if (pending) {
			actions.dataset.runtimePending = '1';
			actions.setAttribute('aria-hidden', 'true');
		} else {
			delete actions.dataset.runtimePending;
			if (String(actions.dataset.streamFooterPlaceholder || '') === '1') {
				actions.setAttribute('aria-hidden', 'true');
			} else {
				actions.removeAttribute('aria-hidden');
			}
		}
	};

	_markTurnActive = (msgId) => {
		const id = this._turnId(msgId);
		if (!id) return;
		this._activeTurnIds.add(id);
		this._setMessageActionsPending(document.getElementById(`msg-bot-${id}`), true);
		try {
			const live = this.dom.getStreamContainer();
			const box = live && live.querySelector('.msg-box.msg-bot');
			if (box && this._streamBoxOwner(box) === id) this._setMessageActionsPending(box, true);
		} catch (_) {}
	};

	_markTurnEnded = (msgId) => {
		const id = this._turnId(msgId);
		if (id) {
			this._activeTurnIds.delete(id);
			this._setMessageActionsPending(document.getElementById(`msg-bot-${id}`), false);
			try {
				const live = this.dom.getStreamContainer();
				const box = live && live.querySelector('.msg-box.msg-bot');
				if (box && this._streamBoxOwner(box) === id) this._setMessageActionsPending(box, false);
			} catch (_) {}
			return;
		}
		// Compatibility path for legacy END callers without a message id.
		for (const actions of Array.from(document.querySelectorAll('.action-icons[data-runtime-pending="1"]'))) {
			delete actions.dataset.runtimePending;
			if (String(actions.dataset.streamFooterPlaceholder || '') !== '1') actions.removeAttribute('aria-hidden');
		}
		this._activeTurnIds.clear();
	};

	_syncMessageActionVisibility = (target, block) => {
		if (!target || !block) return;
		const id = this._turnId(block.id);
		const ctxExtra = block.extra && block.extra.ctx_extra;
		const interrupted = !!(ctxExtra && ctxExtra.response_interrupted === true);
		if (interrupted && id) this._activeTurnIds.delete(id);
		this._setMessageActionsPending(target, !!(id && this._activeTurnIds.has(id) && !interrupted));
	};

	_patchBotMutation = (target, block, replaceText = false) => {
		if (!target || !block) return target;
		try { this.scrollMgr.beginMessageMutation(target); } catch (_) {}
		const desired = this._mutationElement(block, 'bot');
		if (!desired) {
			try { this.scrollMgr.endMessageMutation(target); } catch (_) {}
			return target;
		}

		try {
			for (const attr of ['data-tool-only', 'data-tool-chain-continuation']) {
				if (desired.hasAttribute(attr)) target.setAttribute(attr, desired.getAttribute(attr));
				else target.removeAttribute(attr);
			}
		} catch (_) {}

		try {
			const oldHeader = target.querySelector(':scope > .name-header');
			const newHeader = desired.querySelector(':scope > .name-header');
			if (newHeader) {
				if (oldHeader) oldHeader.replaceWith(newHeader.cloneNode(true));
				else target.insertBefore(newHeader.cloneNode(true), target.firstChild || null);
			} else if (oldHeader) oldHeader.remove();
		} catch (_) {}

		let msg = null;
		let desiredMsg = null;
		try { msg = target.querySelector(':scope > .msg') || target.querySelector('.msg'); } catch (_) { msg = target.querySelector('.msg'); }
		try { desiredMsg = desired.querySelector(':scope > .msg') || desired.querySelector('.msg'); } catch (_) { desiredMsg = desired.querySelector('.msg'); }
		if (!msg || !desiredMsg) {
			try { this.scrollMgr.endMessageMutation(target); } catch (_) {}
			return target;
		}

		const timeline = this.dom.getMsgTimeline(msg, true);
		const desiredTimeline = this.dom.getMsgTimeline(desiredMsg, true);
		if (replaceText && timeline && desiredTimeline) {
			timeline.replaceChildren(...Array.from(desiredTimeline.childNodes).map(n => n.cloneNode(true)));
		} else if (timeline && desiredTimeline) {
			// Preserve token-streamed prose. Structural rows are reconciled around it.
			// Completed Agents v2 turns get a dedicated transition so their final
			// streamed node remains untouched while preceding work folds away.
			const collapsingWorkflow = this._collapseCompletedWorkflow(
				target, timeline, desiredTimeline, block
			);
			if (!collapsingWorkflow) this._syncTimelineStructuralNodes(timeline, desiredTimeline);
		}

		for (const selector of ['.msg-tool-extra', '.msg-extra']) {
			try {
				const dst = msg.querySelector(`:scope > ${selector}`) || msg.querySelector(selector);
				const src = desiredMsg.querySelector(`:scope > ${selector}`) || desiredMsg.querySelector(selector);
				if (!src) {
					if (dst) dst.remove();
					continue;
				}
				const clone = src.cloneNode(true);
				if (dst) dst.replaceWith(clone);
				else {
					const actions = msg.querySelector(':scope > .action-icons');
					if (actions) msg.insertBefore(clone, actions);
					else msg.appendChild(clone);
				}
			} catch (_) {}
		}

		try {
			let oldActions = msg.querySelector(':scope > .action-icons');
			const newActions = desiredMsg.querySelector(':scope > .action-icons');
			if (!oldActions && this.dom && typeof this.dom._ensureStreamFooterPlaceholder === 'function') {
				oldActions = this.dom._ensureStreamFooterPlaceholder(msg);
			}
			if (oldActions && newActions) {
				// Reconcile in place. Replacing the whole footer node caused a visible
				// disappear/reappear cycle in Autonomous continuations. Keeping the slot
				// node stable means only its contents/visibility change, never its height.
				oldActions.replaceChildren(...Array.from(newActions.childNodes).map(n => n.cloneNode(true)));
				oldActions.dataset.footerSlot = '1';
				delete oldActions.dataset.streamFooterPlaceholder;
				const dataId = newActions.getAttribute('data-id');
				if (dataId != null) oldActions.setAttribute('data-id', dataId);
				else oldActions.removeAttribute('data-id');
			} else if (oldActions && !newActions && !this._activeTurnIds.has(this._turnId(block.id))) {
				// No actions in an authoritative completed snapshot: keep the footer
				// footprint, but return it to an invisible placeholder.
				if (this.dom && typeof this.dom._setActionFooterPlaceholder === 'function') {
					this.dom._setActionFooterPlaceholder(oldActions);
				}
			}
		} catch (_) {}
		this._syncMessageActionVisibility(target, block);

		// Finalize stream-only markers without reconstructing the prose DOM. This is
		// especially important for inline post-tool/Agents v2 partial streams.
		this._finalizePartialDom(block.id, target, desired);
		this._postMutation(target);
		return target;
	};

	_streamBoxOwner = (box) => {
		if (!box) return '';
		const explicit = box.dataset ? String(box.dataset.workflowParentId || '') : '';
		if (explicit) return explicit;
		const id = String(box.id || '');
		return id.startsWith('msg-bot-') ? id.slice('msg-bot-'.length) : '';
	};

	_finalizePartialDom = (msgId, target, desired = null) => {
		if (!target) return;
		const prefix = `${String(msgId)}::`;
		for (const key of Array.from(this._partialStreams.keys())) {
			if (String(key).startsWith(prefix)) this._partialStreams.delete(key);
		}

		let desiredParts = null;
		try {
			desiredParts = desired ? desired.querySelectorAll('.msg-part[data-part-id]') : [];
		} catch (_) { desiredParts = []; }
		const desiredById = new Map();
		for (const part of Array.from(desiredParts || [])) {
			desiredById.set(String(part.dataset.partId || ''), part);
		}

		try {
			for (const part of Array.from(target.querySelectorAll('.msg-part[data-live-part="1"]'))) {
				const partId = String(part.dataset.partId || '');
				const snapshot = desiredById.get(partId) || null;
				part.removeAttribute('data-live-part');
				part.classList.remove('msg-part-live');
				if (snapshot && snapshot.className) part.className = snapshot.className;
			}
		} catch (_) {}
		try { this.stream.defuseOrphanActiveBlocks(target); } catch (_) {}
	};

	_finalizeOutputMutation = (mutation) => {
		const block = mutation.block || null;
		if (!block) return;
		const id = String(mutation.msg_id != null ? mutation.msg_id : (block.id != null ? block.id : ''));
		if (!id) return;

		const nodes = this.dom.get('_nodes_');
		const before = this.dom.get('_append_output_before_');
		const streamContainer = this.dom.getStreamContainer();
		let liveBox = null;
		try { liveBox = streamContainer && streamContainer.querySelector('.msg-box.msg-bot'); } catch (_) {}
		const ownsLive = !!(liveBox && this._streamBoxOwner(liveBox) === id);

		let beforeBoxes = [];
		try { beforeBoxes = before ? Array.from(before.querySelectorAll('.msg-box.msg-bot')) : []; } catch (_) {}
		const ownsBefore = beforeBoxes.length > 0 && beforeBoxes.every((box) => this._streamBoxOwner(box) === id);

		// High-frequency stream state is global to this WebView, so touch it only
		// when the live node is owned by this mutation. A stale finalization may
		// legitimately arrive after the next request has already begun.
		if (ownsLive) {
			this._flushStreamQueueNow();
			try { if (this.stream && this.stream.isStreaming) this.stream.endStream(); } catch (_) {}
		}

		this._appendDurableInput(block);

		let target = document.getElementById(`msg-bot-${id}`);
		let targetIsDurable = !!(target && nodes && nodes.contains(target));

		if (!targetIsDurable && ownsLive && !ownsBefore && liveBox && nodes) {
			liveBox.id = `msg-bot-${id}`;
			nodes.appendChild(liveBox); // move, do not clone: preserve streamed DOM exactly
			nodes.classList.remove('empty_list');
			target = liveBox;
			targetIsDurable = true;
		} else if (!targetIsDurable && ownsBefore) {
			// ``nextStream`` produced multiple transient boxes. No single live node can
			// represent the durable message, so use the explicit replacement fallback.
			target = null;
		}

		// If there is no promotable node (multi-segment legacy stream, non-stream
		// snapshot, or a stale final whose transient node is already gone), render
		// this one message from its authoritative snapshot. Never rebuild the chat.
		if (!target && nodes) {
			const desired = this._mutationElement(block, 'bot');
			if (desired) {
				nodes.appendChild(desired);
				nodes.classList.remove('empty_list');
				target = desired;
				mutation.replace_text = true;
			}
		}

		if (ownsBefore) {
			try { this.dom.fastClearHidden('_append_output_before_'); } catch (_) {}
		}
		if (ownsLive) {
			try { this.dom.fastClearHidden('_append_output_'); } catch (_) {}
			try { this.dom.resetEphemeral(); } catch (_) {}
		}
		if (target) this._patchBotMutation(target, block, !!mutation.replace_text);
	};

	_appendArtifactsMutation = (mutation) => {
		const extra = mutation.extra || {};
		const html = String(extra.html || '');
		const id = mutation.msg_id;
		if (html && id != null) {
			this.nodes.appendExtra(id, html, this.scrollMgr);
			return;
		}
		if (mutation.block) this._syncOutputMutation(Object.assign({}, mutation, {replace_text: false}));
	};

	_syncOutputMutation = (mutation) => {
		const block = mutation.block || null;
		if (!block) return;
		this._appendDurableInput(block);
		const id = String(mutation.msg_id != null ? mutation.msg_id : (block.id != null ? block.id : ''));
		if (!id) return;
		let target = document.getElementById(`msg-bot-${id}`);
		const nodes = this.dom.get('_nodes_');
		const targetIsDurable = !!(target && nodes && nodes.contains(target));
		if (!targetIsDurable) {
			// A live stream box already carries the message id. Promote that exact DOM
			// only when it belongs to this message; a newer stream may already exist.
			const live = this.dom.getStreamContainer();
			let liveBox = null;
			try { liveBox = live && live.querySelector('.msg-box.msg-bot'); } catch (_) {}
			if (liveBox && this._streamBoxOwner(liveBox) === id && (!target || target === liveBox)) {
				this._finalizeOutputMutation(Object.assign({}, mutation, {replace_text: false}));
				target = document.getElementById(`msg-bot-${id}`);
			}
		}
		if (!target) {
			const nodes = this.dom.get('_nodes_');
			const desired = this._mutationElement(block, 'bot');
			if (nodes && desired) {
				nodes.appendChild(desired);
				nodes.classList.remove('empty_list');
				target = desired;
			}
		}
		if (target) this._patchBotMutation(target, block, !!mutation.replace_text);
	};

	api_applyMutation = (mutation) => {
		if (!mutation || typeof mutation !== 'object') return false;
		const op = String(mutation.op || '');
		const block = mutation.block || null;
		switch (op) {
			case 'finalize_output':
				this._finalizeOutputMutation(mutation);
				return true;
			case 'sync_output':
				this._syncOutputMutation(mutation);
				return true;
			case 'replace_output':
				this._syncOutputMutation(Object.assign({}, mutation, {replace_text: true}));
				return true;
			case 'replace_input':
				this._replaceInputMutation(mutation);
				return true;
			case 'append_input':
				this._appendDurableInput(block);
				return true;
			case 'append_output':
				this._syncOutputMutation(Object.assign({}, mutation, {replace_text: true}));
				return true;
			case 'append_artifact':
			case 'append_artifacts':
				this._appendArtifactsMutation(mutation);
				return true;
			case 'replace_artifacts':
				this._syncOutputMutation(Object.assign({}, mutation, {replace_text: false}));
				return true;
			case 'remove_message':
				this.nodes.removeNode(mutation.msg_id, this.scrollMgr);
				return true;
			case 'remove_from':
				this.nodes.removeNodesFromId(mutation.msg_id, this.scrollMgr);
				return true;
			default:
				return false;
		}
	};

	// API: append/replace messages (non-streaming).
	api_appendNode = (payload) => {
		const mutation = this._parseRenderMutation(payload);
		if (mutation && this.api_applyMutation(mutation)) return;
		this.resetStreamState('appendNode');
		this.data.append(payload);
		this.scrollMgr.scheduleScroll();
	};

	api_replaceNodes = (payload) => {
		this._clearPartialStreamState();
		this.resetStreamState('replaceNodes', {
			clearMsg: true,
			forceHeavy: true
		});
		// A full context rebuild makes the durable nodes authoritative. Clear every
		// transient turn container and replace history in this same JS task so the
		// browser never gets a chance to paint an empty intermediate frame. This is
		// most noticeable after the first streamed turn, when no older nodes exist.
		this.dom.clearInput();
		try {
			const input = this.dom.get('_append_input_');
			if (input && input.dataset) delete input.dataset.renderMsgId;
		} catch (_) {}
		this.dom.clearOutput();
		this.dom.clearNodes();
		this.data.replace(payload);
	};

	// API: append to input area.
	api_appendToInput = (payload) => {
		// Tag the transient input with the same message id used by durable mutations.
		// This makes late cross-turn syncs harmless instead of relying on focus/time.
		try {
			const prefix = '__PYGPT_INPUT_V1__';
			const raw = String(payload || '');
			if (raw.startsWith(prefix)) {
				const data = JSON.parse(raw.slice(prefix.length));
				const input = this.dom.get('_append_input_');
				if (input && input.dataset && data && data.msg_id != null) {
					input.dataset.renderMsgId = String(data.msg_id);
				}
			}
		} catch (_) {}
		this.nodes.appendToInput(payload);

		// A newly sent turn explicitly returns ownership to FOLLOW. Enable the
		// permanent bottom anchor now; the forced non-live snap below establishes it.
		this.scrollMgr.resumeAutoFollow(false);

		// Keep lastScrollTop in sync to avoid misclassification in the next onscroll handler.
		try {
			this.scrollMgr.lastScrollTop = Utils.SE.scrollTop | 0;
		} catch (_) {}

		// Non-live scroll to bottom right away, independent of autoFollow state.
		this.scrollMgr.scheduleScroll(false, true);
		// NOTE: No resetStreamState() here to avoid flicker/reflow issues while previewing user input.
	};

	// API: clear messages list.
	api_clearNodes = () => {
		this._clearPartialStreamState();
		this.dom.clearNodes();
		this.resetStreamState('clearNodes', {
			clearMsg: true,
			forceHeavy: true
		});
	};

	// API: clear input area.
	api_clearInput = () => {
		this.resetStreamState('clearInput', {
			forceHeavy: true
		});
		this.dom.clearInput();
		try {
			const input = this.dom.get('_append_input_');
			if (input && input.dataset) delete input.dataset.renderMsgId;
		} catch (_) {}
	};

	// API: clear output area.
	api_clearOutput = () => {
		this.dom.clearOutput();
		this.resetStreamState('clearOutput', {
			clearMsg: true,
			forceHeavy: true
		});
	};

	// API: clear live area.
	api_clearLive = () => {
		this.dom.clearLive();
		this.resetStreamState('clearLive', {
			forceHeavy: true
		});
	};

	// API: tool output helpers.
	api_appendToolOutput = (c) => this.toolOutput.append(c);
	api_updateToolOutput = (c) => this.toolOutput.update(c);
	api_clearToolOutput = () => this.toolOutput.clear();
	api_beginToolOutput = () => {
		this._hideReasoningForToolCall();
		this.toolOutput.begin();
	};
	api_endToolOutput = () => this.toolOutput.end();
	api_enableToolOutput = () => this.toolOutput.enable();
	api_disableToolOutput = () => this.toolOutput.disable();
	api_toggleToolOutput = (id) => this.toolOutput.toggle(id);
	api_toggleToolGroup = (id) => this.toolOutput.toggleGroup(id);

	// API: toggle collapsed file/URL extras.
	api_toggleExtraItems = (button) => this.ui.toggleExtraItems(button);

	// API: append extra content to a bot message.
	api_appendExtra = (id, c) => this.nodes.appendExtra(id, c, this.scrollMgr);

	// API: remove one message by id.
	api_removeNode = (id) => this.nodes.removeNode(id, this.scrollMgr);

	// API: remove all messages starting from id.
	api_removeNodesFromId = (id) => this.nodes.removeNodesFromId(id, this.scrollMgr);

	// API: replace live area content (with local post-processing).
	api_replaceLive = (content) => {
		const el = this.dom.get('_append_live_');
		if (!el) return;
		if (el.classList.contains('hidden')) {
			el.classList.remove('hidden');
			el.classList.add('visible');
		}
		el.innerHTML = content;

		try {
			const maybePromise = this.renderer.renderPendingMarkdown(el);

			const post = () => {
				try {
					this.highlighter.observeNewCode(el, {
						deferLastIfStreaming: true,
						minLinesForLast: this.cfg.PROFILE_CODE.minLinesForHL,
						minCharsForLast: this.cfg.PROFILE_CODE.minCharsForHL
					}, this.stream.activeCode);

					this.highlighter.observeMsgBoxes(el, (box) => {
						this.highlighter.observeNewCode(box, {
							deferLastIfStreaming: true,
							minLinesForLast: this.cfg.PROFILE_CODE.minLinesForHL,
							minCharsForLast: this.cfg.PROFILE_CODE.minCharsForHL
						}, this.stream.activeCode);
						this.codeScroll.initScrollableBlocks(box);
					});
				} catch (_) {}

				try {
					const mm = getMathMode();
					// In finalize-only we must force now; otherwise normal schedule is fine.
					if (mm === 'finalize-only') this.math.schedule(el, 0, true);
					else this.math.schedule(el);
				} catch (_) {}

				this.scrollMgr.scheduleScroll();
			};

			if (maybePromise && typeof maybePromise.then === 'function') {
				maybePromise.then(post);
			} else {
				post();
			}
		} catch (_) {
			// Worst-case: keep UX responsive even if something throws before post-processing
			this.scrollMgr.scheduleScroll();
		}
	};

	// API: update footer content.
	api_updateFooter = (html) => {
		const el = this.dom.get('_footer_');
		if (el) el.innerHTML = html;
	};

	// API: toggle UI features.
	api_enableEditIcons = () => this.ui.enableEditIcons();
	api_disableEditIcons = () => this.ui.disableEditIcons();
	api_enableTimestamp = () => this.ui.enableTimestamp();
	api_disableTimestamp = () => this.ui.disableTimestamp();
	api_enableBlocks = () => this.ui.enableBlocks();
	api_disableBlocks = () => this.ui.disableBlocks();
	api_updateCSS = (styles) => this.ui.updateCSS(styles);

	// API: sync scroll position with host.
	api_getScrollPosition = () => {
		this.bridge.updateScrollPosition(window.scrollY);
	};
	api_setScrollPosition = (pos) => {
		try {
			const top = Math.max(0, Number(pos) || 0);
			this.scrollMgr.markProgrammaticScroll(top);
			window.scrollTo(0, top);
			this.scrollMgr.prevScroll = top;
			this.scrollMgr.lastScrollTop = Utils.SE.scrollTop;
		} catch (_) {}
	};

	// API: show/hide loading overlay.
	api_showLoading = () => this.loading.show();
	api_hideLoading = (reserveSpace = false) => this.loading.hide(reserveSpace);

	// API: restore collapsed state of codes in a given root.
	api_restoreCollapsedCode = (root) => this.renderer.restoreCollapsedCode(root);

	// API: user-triggered page scroll.
	api_scrollToTopUser = () => this.scrollMgr.scrollToTopUser();
	api_scrollToBottomUser = () => this.scrollMgr.scrollToBottomUser();

	// API: tips visibility control.
	api_showTips = () => this.tips.show();
	api_hideTips = () => this.tips.hide();

	// API: begin/end. A new visible turn gets a fresh status session so
	// transient Tool/Agents-v2 rows can never attach to the previous turn.
	// Action buttons are hidden by visibility (not display), preserving the
	// permanent footer footprint until the exact turn reaches END/STOP.
	api_begin = (msgId = '') => {
		this._turnSession += 1;
		this._markTurnActive(msgId);
	};
	api_end = (msgId = '') => {
		this._markTurnEnded(msgId);
		this.scrollMgr.forceScrollToBottomImmediateAtEnd();
	}

	// API: custom markup rules control.
	api_getCustomMarkupRules = () => this.customMarkup.getRules();
	api_setCustomMarkupRules = (rules) => {
		this.customMarkup.setRules(rules);
		// Keep StreamEngine in sync with rules producing fenced code
		try {
			this.stream.setCustomFenceSpecs(this.customMarkup.getSourceFenceSpecs());
		} catch (_) {}
	};

	// Initialize runtime (called on DOMContentLoaded).
	init() {
		this.highlighter.initHLJS();
		this.dom.init();
		this.ui.ensureStickyHeaderStyle();

		this.tips = new TipsManager(this.dom);
		this.events.install();

		this.bridge.initQWebChannel(this.cfg.PID, (bridge) => {
			const onChunk = (name, chunk, type) => this.api_onChunk(name, chunk, type);
			const onNode = (payload) => this.api_appendNode(payload);
			const onNodeReplace = (payload) => this.api_replaceNodes(payload);
			const onNodeInput = (html) => this.api_appendToInput(html);
			this.bridge.connect(onChunk, onNode, onNodeReplace, onNodeInput);
			try {
				this.logger.bindBridge(this.bridge.bridge || this.bridge);
			} catch (_) {}
		});

		this.renderer.init();
		try {
			const pendingMarkdown = this.renderer.renderPendingMarkdown(document);
			const virtualize = () => {
				try { this.scrollMgr.scheduleMessageVirtualizationRefresh(); } catch (_) {}
			};
			if (pendingMarkdown && typeof pendingMarkdown.then === 'function') pendingMarkdown.then(virtualize);
			else virtualize();
		} catch (_) {
			try { this.scrollMgr.scheduleMessageVirtualizationRefresh(); } catch (__) {}
		}

		this.highlighter.observeMsgBoxes(document, (box) => {
			this.highlighter.observeNewCode(box, {
				deferLastIfStreaming: true,
				minLinesForLast: this.cfg.PROFILE_CODE.minLinesForHL,
				minCharsForLast: this.cfg.PROFILE_CODE.minCharsForHL
			}, this.stream.activeCode);
			this.codeScroll.initScrollableBlocks(box);
		});
		this.highlighter.observeNewCode(document, {
			deferLastIfStreaming: true,
			minLinesForLast: this.cfg.PROFILE_CODE.minLinesForHL,
			minCharsForLast: this.cfg.PROFILE_CODE.minCharsForHL
		}, this.stream.activeCode);
		this.highlighter.scheduleScanVisibleCodes(this.stream.activeCode);

		this.tips.cycle();
		this.scrollMgr.updateScrollFab(true);
	}

	// Cleanup runtime and detach from DOM/bridge.
	cleanup() {
		this.tips.cleanup();
		try {
			this.bridge.disconnect();
		} catch (_) {}
		this.events.cleanup();
		this.highlighter.cleanup();
		this.math.cleanup();
		this.streamQ.clear();
		this.dom.cleanup();
	}
}

// Ensure RafManager.cancel uses the correct group key cleanup.
if (typeof RafManager !== 'undefined' && RafManager.prototype && typeof RafManager.prototype.cancel === 'function') {
	RafManager.prototype.cancel = function(key) {
		const t = this.tasks.get(key);
		if (!t) return;
		this.tasks.delete(key);
		if (t.group) {
			const set = this.groups.get(t.group);
			if (set) {
				set.delete(key);
				if (set.size === 0) this.groups.delete(t.group);
			}
		}
	};
}

window.__collapsed_idx = window.__collapsed_idx || [];

const runtime = new Runtime();

document.addEventListener('DOMContentLoaded', () => runtime.init());

Object.defineProperty(window, 'SE', {
	get() {
		return Utils.SE;
	}
});

window.beginStream = (chunk, preserveParentId = null) => runtime.api_beginStream(chunk, preserveParentId);
window.endStream = () => runtime.api_endStream();
window.applyStream = (name, chunk) => runtime.api_applyStream(name, chunk);
window.appendStream = (name, chunk) => runtime.api_appendStream(name, chunk);
window.appendStreamTyped = (type, name, chunk) => runtime.api_onChunk(name, chunk, type);
window.nextStream = () => runtime.api_nextStream();
window.clearStream = () => runtime.api_clearStream();
window.appendPartialStream = (parentId, partId, chunk, begin) => runtime.api_appendPartialStream(parentId, partId, chunk, begin);
window.bindWorkflowStream = (parentId, nameHeader, records) => runtime.api_bindWorkflowStream(parentId, nameHeader, records);
window.setAgentStatus = (text, parentId, statusId) => runtime.api_setAgentStatus(text, parentId, statusId);
window.clearAgentStatus = (parentId) => runtime.api_clearAgentStatus(parentId);
window.setToolStatus = (names, parentId, statusId) => runtime.api_setToolStatus(names, parentId, statusId);
window.clearToolStatus = (parentId, immediate = true) => runtime.api_clearToolStatus(parentId, immediate);
window.freezeWorkflowStatus = (parentId, kind) => runtime.api_freezeWorkflowStatus(parentId, kind);

window.begin = (msgId = '') => runtime.api_begin(msgId);
window.end = (msgId = '') => runtime.api_end(msgId);

window.appendNode = (payload) => runtime.api_appendNode(payload);
window.replaceNodes = (payload) => runtime.api_replaceNodes(payload);
window.appendToInput = (html) => runtime.api_appendToInput(html);

window.clearNodes = () => runtime.api_clearNodes();
window.clearInput = () => runtime.api_clearInput();
window.clearOutput = () => runtime.api_clearOutput();
window.clearLive = () => runtime.api_clearLive();

window.appendToolOutput = (c) => runtime.api_appendToolOutput(c);
window.updateToolOutput = (c) => runtime.api_updateToolOutput(c);
window.clearToolOutput = () => runtime.api_clearToolOutput();
window.beginToolOutput = () => runtime.api_beginToolOutput();
window.endToolOutput = () => runtime.api_endToolOutput();
window.enableToolOutput = () => runtime.api_enableToolOutput();
window.disableToolOutput = () => runtime.api_disableToolOutput();
window.toggleToolOutput = (id) => runtime.api_toggleToolOutput(id);
window.toggleToolGroup = (id) => runtime.api_toggleToolGroup(id);
window.toggleExtraItems = (button) => runtime.api_toggleExtraItems(button);

window.appendExtra = (id, c) => runtime.api_appendExtra(id, c);
window.removeNode = (id) => runtime.api_removeNode(id);
window.removeNodesFromId = (id) => runtime.api_removeNodesFromId(id);

window.replaceLive = (c) => runtime.api_replaceLive(c);
window.updateFooter = (c) => runtime.api_updateFooter(c);

window.enableEditIcons = () => runtime.api_enableEditIcons();
window.disableEditIcons = () => runtime.api_disableEditIcons();
window.enableTimestamp = () => runtime.api_enableTimestamp();
window.disableTimestamp = () => runtime.api_disableTimestamp();
window.enableBlocks = () => runtime.api_enableBlocks();
window.disableBlocks = () => runtime.api_disableBlocks();
window.updateCSS = (s) => runtime.api_updateCSS(s);

window.getScrollPosition = () => runtime.api_getScrollPosition();
window.setScrollPosition = (pos) => runtime.api_setScrollPosition(pos);

window.showLoading = () => runtime.api_showLoading();
window.hideLoading = (reserveSpace = false) => runtime.api_hideLoading(reserveSpace);

window.restoreCollapsedCode = (root) => runtime.api_restoreCollapsedCode(root);
window.scrollToTopUser = () => runtime.api_scrollToTopUser();
window.scrollToBottomUser = () => runtime.api_scrollToBottomUser();

window.showTips = () => runtime.api_showTips();
window.hideTips = () => runtime.api_hideTips();

window.getCustomMarkupRules = () => runtime.api_getCustomMarkupRules();
window.setCustomMarkupRules = (rules) => runtime.api_setCustomMarkupRules(rules);

window.__pygpt_cleanup = () => runtime.cleanup();


RafManager.prototype.stats = function() {
  const byGroup = new Map();
  for (const [key, t] of this.tasks) {
    const g = t.group || 'default';
    byGroup.set(g, (byGroup.get(g) || 0) + 1);
  }
  return {
    tasks: this.tasks.size,
    groups: Array.from(byGroup, ([group, count]) => ({ group, count }))
      .sort((a,b) => b.count - a.count)
  };
};

RafManager.prototype.dumpHotGroups = function(label='') {
  const s = this.stats();
  console.log('[RAF]', label, 'tasks=', s.tasks, 'byGroup=', s.groups.slice(0,8));
};
RafManager.prototype.findDomTasks = function() {
  const out = [];
  for (const [key, t] of this.tasks) {
    let el = null;
    if (key && key.nodeType === 1) el = key;
    else if (key && key.el && key.el.nodeType === 1) el = key.el;
    if (el) out.push({ group: t.group, tag: el.tagName, connected: el.isConnected });
  }
  return out;
};
// setInterval(() => runtime.raf.dumpHotGroups('tick'), 1000);

function gaugeSE(se) {
  const ropeLen = (se.streamBuf.length + se._sbLen);
  const ac = se.activeCode;
  const domFrozen = ac?.frozenEl?.textContent?.length || 0;
  const domTail = ac?.tailEl?.textContent?.length || 0;
  const domLen = domFrozen + domTail;
  return {
    ropeLen,
    domLen,
    totalChars: ropeLen + domLen,
    ratioRopeToDom: (domLen ? (ropeLen / domLen).toFixed(2) : 'n/a'),
    fenceOpen: se.fenceOpen,
    codeOpen: se.codeStream?.open
  };
}

/*
setInterval(() => {
  const g = gaugeSE(runtime.stream);
  console.log('[SE gauge]', g);
}, 2000);*/