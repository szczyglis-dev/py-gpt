// RuntimeMessages owns messages behavior and state.
class RuntimeMessages {

	// ========================================
	// Composition
	// ========================================

	constructor(runtime) {
		this.runtime = runtime;
	}

	// ========================================
	// History
	// ========================================

	// API: append/replace messages (non-streaming).
	appendNode = (payload) => {
		const mutation = this.runtime.mutations.parseRenderMutation(payload);
		if (mutation && this.runtime.mutations.applyMutation(mutation)) return;
		this.runtime.streaming.resetStreamState('appendNode');
		this.runtime.data.append(payload);
		this.runtime.scrollMgr.scheduleScroll();
	};

	replaceNodes = (payload) => {
		this.runtime.workflows.clearAgentWorking();
		this.runtime.partials.clearPartialStreamState();
		this.runtime.streaming.resetStreamState('replaceNodes', {
			clearMsg: true,
			forceHeavy: true
		});
		// A full context rebuild makes the durable nodes authoritative. Clear every
		// transient turn container and replace history in this same JS task so the
		// browser never gets a chance to paint an empty intermediate frame. This is
		// most noticeable after the first streamed turn, when no older nodes exist.
		this.runtime.dom.clearInput();
		try {
			const input = this.runtime.dom.get('_append_input_');
			if (input && input.dataset) delete input.dataset.renderMsgId;
		} catch (_) {}
		this.runtime.dom.clearOutput();
		this.runtime.dom.clearNodes();
		this.runtime.data.replace(payload);
	};

	// ========================================
	// User input
	// ========================================

	// API: append to input area.
	appendToInput = (payload) => {
		// Tag the transient input with the same message id used by durable mutations.
		// This makes late cross-turn syncs harmless instead of relying on focus/time.
		try {
			const prefix = '__PYGPT_INPUT_V1__';
			const raw = String(payload || '');
			if (raw.startsWith(prefix)) {
				const data = JSON.parse(raw.slice(prefix.length));
				const input = this.runtime.dom.get('_append_input_');
				if (input && input.dataset && data && data.msg_id != null) {
					input.dataset.renderMsgId = String(data.msg_id);
				}
			}
		} catch (_) {}
		this.runtime.nodes.appendToInput(payload);
		// The transient input row is now materialized. If SEND_INIT armed the
		// loader, this reserves its footprint after the input (never before it)
		// and lets the 500 ms visibility gate complete independently.
		try { this.runtime.loading.inputReady(); } catch (_) {}

		// A newly sent turn explicitly returns ownership to FOLLOW. Enable the
		// permanent bottom anchor now; the forced non-live snap below establishes it.
		this.runtime.scrollMgr.resumeAutoFollow(false);

		// Keep lastScrollTop in sync to avoid misclassification in the next onscroll handler.
		try {
			this.runtime.scrollMgr.lastScrollTop = Utils.SE.scrollTop | 0;
		} catch (_) {}

		// Non-live scroll to bottom right away, independent of autoFollow state.
		this.runtime.scrollMgr.scheduleScroll(false, true);
		// NOTE: No resetStreamState() here to avoid flicker/reflow issues while previewing user input.
	};

	// API: clear input area.
	clearInput = () => {
		this.runtime.streaming.resetStreamState('clearInput', {
			forceHeavy: true
		});
		this.runtime.dom.clearInput();
		try {
			const input = this.runtime.dom.get('_append_input_');
			if (input && input.dataset) delete input.dataset.renderMsgId;
		} catch (_) {}
	};

	// ========================================
	// Clearing transient content
	// ========================================

	// API: clear messages list.
	clearNodes = () => {
		this.runtime.workflows.clearAgentWorking();
		this.runtime.partials.clearPartialStreamState();
		this.runtime.dom.clearNodes();
		this.runtime.streaming.resetStreamState('clearNodes', {
			clearMsg: true,
			forceHeavy: true
		});
	};

	// API: clear output area.
	clearOutput = () => {
		this.runtime.dom.clearOutput();
		this.runtime.streaming.resetStreamState('clearOutput', {
			clearMsg: true,
			forceHeavy: true
		});
	};

	// API: clear live area.
	clearLive = () => {
		this.runtime.dom.clearLive();
		this.runtime.streaming.resetStreamState('clearLive', {
			forceHeavy: true
		});
	};

	// ========================================
	// Live content
	// ========================================

	// API: append extra content to a bot message.

	// API: remove one message by id.

	// API: remove all messages starting from id.

	// API: replace live area content (with local post-processing).
	replaceLive = (content) => {
		const el = this.runtime.dom.get('_append_live_');
		if (!el) return;
		if (el.classList.contains('hidden')) {
			el.classList.remove('hidden');
			el.classList.add('visible');
		}
		el.innerHTML = content;

		try {
			const maybePromise = this.runtime.renderer.renderPendingMarkdown(el);

			const post = () => {
				try {
					this.runtime.highlighter.observeNewCode(el, {
						deferLastIfStreaming: true,
						minLinesForLast: this.runtime.cfg.PROFILE_CODE.minLinesForHL,
						minCharsForLast: this.runtime.cfg.PROFILE_CODE.minCharsForHL
					}, this.runtime.stream.code.activeCode);

					this.runtime.highlighter.observeMsgBoxes(el, (box) => {
						this.runtime.highlighter.observeNewCode(box, {
							deferLastIfStreaming: true,
							minLinesForLast: this.runtime.cfg.PROFILE_CODE.minLinesForHL,
							minCharsForLast: this.runtime.cfg.PROFILE_CODE.minCharsForHL
						}, this.runtime.stream.code.activeCode);
						this.runtime.codeScroll.initScrollableBlocks(box);
					});
				} catch (_) {}

				try {
					const mm = getMathMode();
					// In finalize-only we must force now; otherwise normal schedule is fine.
					if (mm === 'finalize-only') this.runtime.math.schedule(el, 0, true);
					else this.runtime.math.schedule(el);
				} catch (_) {}

				this.runtime.scrollMgr.scheduleScroll();
			};

			if (maybePromise && typeof maybePromise.then === 'function') {
				maybePromise.then(post);
			} else {
				post();
			}
		} catch (_) {
			// Worst-case: keep UX responsive even if something throws before post-processing
			this.runtime.scrollMgr.scheduleScroll();
		}
	};

}
