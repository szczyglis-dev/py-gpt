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
	api_beginStream = (chunk = false) => {
		this._agentsV2FinalActive = false;
		this._turnSession += 1;
		this.tips && this.tips.hide();
		this.resetStreamState('beginStream', {
			clearMsg: true,
			finalizeActive: false,
			forceHeavy: true
		});
		this.stream.beginStream(chunk);
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
		this.scrollMgr.scheduleScroll();
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
			this.customMarkup.apply(state.root, this.renderer.MD_STREAM || this.renderer.MD);
		} catch (_) {}
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
				if (!state || !state.fallback) this.api_beginStream(true);
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
		state.text += value;
		this._renderPartialStream(state);
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
		return status;
	};

	_setWorkflowStatus = (parentId, statusId, kind, labelText, active = true) => {
		let status = this._findWorkflowStatus(statusId);
		if (!status) status = this._createWorkflowStatus(parentId, statusId, kind);
		if (!status) return null;
		status.dataset.statusKind = String(kind || 'agent');
		if (statusId) status.dataset.workflowStatusId = String(statusId);
		if (active) status.classList.add('agents-v2-status--active');
		else status.classList.remove('agents-v2-status--active');
		let label = status.querySelector('.agents-v2-status__text');
		if (!label) {
			label = document.createElement('span');
			label.className = 'agents-v2-status__text';
			status.appendChild(label);
		}
		label.textContent = String(labelText || '');
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
		this.scrollMgr.scheduleScroll();
	};

	api_clearAgentStatus = (parentId = null) => {
		this.api_freezeWorkflowStatus(parentId);
	};

	api_setToolStatus = (names, parentId = null, statusId = null) => {
		const values = Array.isArray(names) ? names.filter(Boolean).map(v => String(v)) : [];
		if (this._agentsV2FinalActive) {
			this.api_freezeWorkflowStatus(parentId, 'tool');
			return;
		}
		if (!values.length) {
			this.api_freezeWorkflowStatus(parentId, 'tool');
			return;
		}

		this.api_freezeWorkflowStatus(parentId);
		this._setWorkflowStatus(parentId, statusId, 'tool', this._toolStatusLabel(values), true);
		this.scrollMgr.scheduleScroll();
	};

	api_clearToolStatus = (parentId = null) => {
		this.api_freezeWorkflowStatus(parentId, 'tool');
	};

	// After beginStream() clears the transient output area, recreate the id-bound
	// stream shell and restore UI-only status history before the first text chunk.
	// This prevents "Planning/Using tool" rows from disappearing at stream start.
	api_bindWorkflowStream = (parentId, nameHeader = '', records = []) => {
		const value = String(parentId || '');
		if (!value) return;
		const msg = this.dom.getStreamMsg(true, String(nameHeader || ''));
		if (!msg) return;
		const box = msg.closest ? msg.closest('.msg-box.msg-bot') : null;
		if (box) {
			box.id = `msg-bot-${value}`;
			box.dataset.workflowParentId = value;
		}
		const timeline = (this.dom && typeof this.dom.getMsgTimeline === 'function')
			? this.dom.getMsgTimeline(msg, true)
			: msg;
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
			this._setWorkflowStatus(value, sid, kind, label, !!record.active);
		}
	};

	// API: append/replace messages (non-streaming).
	api_appendNode = (payload) => {
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
		// A full context rebuild makes the durable nodes authoritative. Leaving
		// _append_output_ alive here produced a second copy of the just-finished
		// workflow below the message footer (exactly the duplicated status rows
		// seen after RELOAD). Drop the transient stream DOM before replacing nodes.
		this.dom.clearOutput();
		this.dom.clearNodes();
		this.data.replace(payload);
	};

	// API: append to input area.
	api_appendToInput = (payload) => {
		this.nodes.appendToInput(payload);

		// Ensure initial auto-follow is ON for the next stream that will start right after user input.
		// Rationale: previously, if the user had scrolled up, autoFollow could remain false and the
		// live stream would not follow even though we just sent a new input.
		this.scrollMgr.autoFollow = true; // explicitly re-enable page auto-follow
		this.scrollMgr.userInteracted = false; // Reset interaction so live scroll is allowed

		// Keep lastScrollTop in sync to avoid misclassification in the next onscroll handler.
		try {
			this.scrollMgr.lastScrollTop = Utils.SE.scrollTop | 0;
		} catch (_) {}

		// Non-live scroll to bottom right away, independent of autoFollow state.
		this.scrollMgr.scheduleScroll();
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
	api_beginToolOutput = () => this.toolOutput.begin();
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
			window.scrollTo(0, pos);
			this.scrollMgr.prevScroll = parseInt(pos);
		} catch (_) {}
	};

	// API: show/hide loading overlay.
	api_showLoading = () => this.loading.show();
	api_hideLoading = () => this.loading.hide();

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
	api_begin = () => { this._turnSession += 1; };
	api_end = () => {
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
			this.renderer.renderPendingMarkdown(document);
		} catch (_) {}

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

window.beginStream = (chunk) => runtime.api_beginStream(chunk);
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
window.clearToolStatus = (parentId) => runtime.api_clearToolStatus(parentId);
window.freezeWorkflowStatus = (parentId, kind) => runtime.api_freezeWorkflowStatus(parentId, kind);

window.begin = () => runtime.api_begin();
window.end = () => runtime.api_end();

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
window.hideLoading = () => runtime.api_hideLoading();

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