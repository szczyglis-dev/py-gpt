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
		this.nodes = new NodesManager(this.dom, this.renderer, this.highlighter, this.math);
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
		// Future-proof: add other chunk types here (attachments, status, etc.)
		// No-op for unknown types to keep current behavior.
		this.logger.debug('STREAM', 'IGNORED_NON_TEXT_CHUNK', {
			type: t,
			len: (chunk ? String(chunk).length : 0)
		});
	};

	// API: begin stream.
	api_beginStream = (chunk = false) => {
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

	// API: append/replace messages (non-streaming).
	api_appendNode = (payload) => {
		this.resetStreamState('appendNode');
		this.data.append(payload);
	};

	api_replaceNodes = (payload) => {
		this.resetStreamState('replaceNodes', {
			clearMsg: true,
			forceHeavy: true
		});
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