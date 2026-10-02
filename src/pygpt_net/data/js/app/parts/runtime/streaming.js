// RuntimeStreaming owns streaming behavior and state.
class RuntimeStreaming {

	// ========================================
	// Composition
	// ========================================

	constructor(runtime) {
		this.runtime = runtime;
		this._lastHeavyResetMs = 0;
	}

	// ========================================
	// Stream lifecycle and transport
	// ========================================

	// Reset stream state and optionally perform a heavy reset of schedulers and observers.
	resetStreamState(origin, opts) {
		try {
			this.runtime.streamQ.clear();
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
		const withinDebounce = (now - (this._lastHeavyResetMs || 0)) <= (this.runtime.cfg.RESET.HEAVY_DEBOUNCE_MS || 24);
		const mustHeavyByOrigin =
			def.forceHeavy === true || def.clearMsg === true ||
			origin === 'beginStream' || origin === 'nextStream' ||
			origin === 'clearStream' || origin === 'replaceNodes' ||
			origin === 'clearNodes' || origin === 'clearOutput' ||
			origin === 'clearLive' || origin === 'clearInput';
		const shouldHeavy = mustHeavyByOrigin || !withinDebounce;
		const suppressLog = withinDebounce && origin !== 'beginStream';

		try {
			this.runtime.stream.abortAndReset({
				...def,
				suppressLog
			});
		} catch (_) {}

		if (shouldHeavy) {
			try {
				this.runtime.highlighter.cleanup();
			} catch (_) {}
			try {
				this.runtime.math.cleanup();
			} catch (_) {}
			try {
				this.runtime.codeScroll.cancelAllScrolls();
			} catch (_) {}
			try {
				this.runtime.scrollMgr.cancelPendingScroll();
			} catch (_) {}
			try {
				this.runtime.raf.cancelAll();
			} catch (_) {}
			this._lastHeavyResetMs = now;
		} else {
			try {
				this.runtime.raf.cancelGroup('StreamQueue');
			} catch (_) {}
		}

		try {
			this.runtime.tips && this.runtime.tips.hide();
		} catch (_) {}
	}

	// API: handle incoming chunk (from bridge).
	onChunk = (name, chunk, type) => {
		const t = String(type || 'text_delta');
		if (t === 'text_delta') {
			this.appendStream(name, chunk);
			return;
		}
		if (t === 'final_reset') {
			this.runtime.workflows.clearAgentWorking();
			try { this.runtime.loading.hide(false); } catch (_) {}
			// Keep the already materialized durable CtxItem and clear only the
			// transient global stream/status area. Final prose will be appended via
			// appendPartialStream() into the same msg-bot element.
			this.runtime.workflows.clearAgentStatus();
			this.clearStream();
			// A late queued tool/status event must not reappear during final prose.
			this.runtime.workflows.finalActive = true;
			return;
		}
		// Future-proof: add other chunk types here (attachments, status, etc.)
		// No-op for unknown types to keep current behavior.
		this.runtime.logger.debug('STREAM', 'IGNORED_NON_TEXT_CHUNK', {
			type: t,
			len: (chunk ? String(chunk).length : 0)
		});
	};

	// API: begin stream.
	beginStream = (chunk = false, preserveParentId = null) => {
		this.runtime.workflows.finalActive = false;
		this.runtime.tips && this.runtime.tips.hide();

		// Consecutive tool-only continuations belong to one visual turn. If the
		// id-bound workflow host already exists, preserve it instead of clearing
		// and recreating the same Tool row on every provider round. This removes
		// the otherwise visible vertical jump between tools.
		const parentKey = String(preserveParentId || '');
		// STREAM_BEGIN always carries the durable owner id when available. This is
		// the reliable ownership point for freshly-created contexts whose BEGIN may
		// have fired before ctx.id was allocated.
		if (parentKey) this.runtime.turns.markTurnActive(parentKey);
		const existingWorkflowHost = parentKey ? this.runtime.workflows.workflowMessageHost(parentKey, false) : null;
		const streamContainer = this.runtime.dom.getStreamContainer();
		const preserveWorkflowHost = !!(
			existingWorkflowHost && streamContainer &&
			streamContainer.contains(existingWorkflowHost.box)
		);
		this.resetStreamState('beginStream', {
			clearMsg: !preserveWorkflowHost,
			finalizeActive: false,
			forceHeavy: !preserveWorkflowHost
		});
		this.runtime.stream.beginStream(chunk, !preserveWorkflowHost);
		// beginStream() may clear/reset the transient containers, so install the
		// owner hint only afterwards. The actual box is usually created by the first
		// text delta and will claim this id lazily in DOMRefs.getStreamMsg().
		if (this.runtime.dom && typeof this.runtime.dom.setStreamOwnerHint === 'function') {
			this.runtime.dom.setStreamOwnerHint(parentKey);
		}
	};

	// Bind/refresh ownership when Python learns the durable ctx id after STREAM_BEGIN.
	// This is intentionally idempotent and refuses to steal a live box owned by
	// another turn.
	bindStreamOwner = (msgId) => {
		const id = String(msgId || '');
		if (!id) return false;
		this.runtime.turns.markTurnActive(id);
		if (!this.runtime.dom || typeof this.runtime.dom.setStreamOwnerHint !== 'function') return false;
		return !!this.runtime.dom.setStreamOwnerHint(id);
	};

	// API: end stream.
	endStream = () => {
		this.runtime.stream.endStream();
	};

	// API: apply chunk.
	applyStream = (name, chunk) => {
		this.runtime.stream.applyStream(name, chunk);
	};

	// API: enqueue chunk (drained on rAF).
	appendStream = (name, chunk) => {
		this.runtime.streamQ.enqueue(name, chunk);
	};

	// API: move current output to "before" area and prepare for next stream.
	nextStream = () => {
		this.runtime.tips && this.runtime.tips.hide();
		const element = this.runtime.dom.get('_append_output_');
		const before = this.runtime.dom.get('_append_output_before_');
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
		this.runtime.scrollMgr.scheduleScroll(true);
	};

	// API: clear streaming output area entirely.
	clearStream = () => {
		this.runtime.tips && this.runtime.tips.hide();
		this.resetStreamState('clearStream', {
			clearMsg: true,
			forceHeavy: true
		});
		const el = this.runtime.dom.getStreamContainer();
		if (!el) return;
		el.replaceChildren();
	};

	flushStreamQueueNow = () => {
		try {
			let guard = 0;
			while (this.runtime.streamQ && this.runtime.streamQ.count && this.runtime.streamQ.count() > 0 && guard++ < 10000) {
				this.runtime.streamQ.drain();
			}
		} catch (_) {}
	};

}
