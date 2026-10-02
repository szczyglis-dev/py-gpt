// RuntimeTurns owns turns behavior and state.
class RuntimeTurns {

	// ========================================
	// Composition
	// ========================================

	constructor(runtime) {
		this.runtime = runtime;
		this.activeTurnIds = new Set();
	}

	// ========================================
	// Turn lifecycle and action visibility
	// ========================================

	turnId = (value) => {
		if (value == null) return '';
		return String(value).trim();
	};

	markTurnActive = (msgId) => {
		const id = this.turnId(msgId);
		if (!id) return;
		this.activeTurnIds.add(id);
		this._setMessageActionsPending(document.getElementById(`msg-bot-${id}`), true);
		try {
			const live = this.runtime.dom.getStreamContainer();
			const box = live && live.querySelector('.msg-box.msg-bot');
			if (box && this.streamBoxOwner(box) === id) this._setMessageActionsPending(box, true);
		} catch (_) {}
	};

	syncMessageActionVisibility = (target, block) => {
		if (!target || !block) return;
		const id = this.turnId(block.id);
		const ctxExtra = block.extra && block.extra.ctx_extra;
		const interrupted = !!(ctxExtra && ctxExtra.response_interrupted === true);
		if (interrupted && id) this.activeTurnIds.delete(id);
		if (ctxExtra && (interrupted || ctxExtra.response_final === true)) this.runtime.workflows.clearAgentWorking(id);
		this._setMessageActionsPending(target, !!(id && this.activeTurnIds.has(id) && !interrupted));
	};

	streamBoxOwner = (box) => {
		if (!box) return '';
		const explicit = box.dataset ? String(box.dataset.workflowParentId || '') : '';
		if (explicit) return explicit;
		const id = String(box.id || '');
		return id.startsWith('msg-bot-') ? id.slice('msg-bot-'.length) : '';
	};

	// API: begin/end. A new visible turn gets a fresh status session so
	// transient Tool/Agents-v2 rows can never attach to the previous turn.
	// Action buttons are hidden by visibility (not display), preserving the
	// permanent footer footprint until the exact turn reaches END/STOP.
	begin = (msgId = '') => {
		this.markTurnActive(msgId);
	};

	end = (msgId = '') => {
		this._markTurnEnded(msgId);
		this.runtime.scrollMgr.forceScrollToBottomImmediateAtEnd();
	}

	// ========================================
	// Turn lifecycle and action visibility internals
	// ========================================

	_messageActionSlot = (target, create = false) => {
		if (!target) return null;
		let msg = null;
		try { msg = target.querySelector(':scope > .msg') || target.querySelector('.msg'); }
		catch (_) { try { msg = target.querySelector('.msg'); } catch (__) {} }
		if (!msg) return null;
		let actions = null;
		try { actions = msg.querySelector(':scope > .action-icons'); }
		catch (_) { try { actions = msg.querySelector('.action-icons'); } catch (__) {} }
		if (!actions && create && this.runtime.dom && typeof this.runtime.dom.ensureStreamFooterPlaceholder === 'function') {
			actions = this.runtime.dom.ensureStreamFooterPlaceholder(msg);
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

	_markTurnEnded = (msgId) => {
		this.runtime.workflows.clearAgentWorking(msgId || null);
		const id = this.turnId(msgId);
		if (id) {
			this.activeTurnIds.delete(id);
			this._setMessageActionsPending(document.getElementById(`msg-bot-${id}`), false);
			try {
				const live = this.runtime.dom.getStreamContainer();
				const box = live && live.querySelector('.msg-box.msg-bot');
				if (box && this.streamBoxOwner(box) === id) this._setMessageActionsPending(box, false);
			} catch (_) {}
			return;
		}
		// Compatibility path for legacy END callers without a message id.
		for (const actions of Array.from(document.querySelectorAll('.action-icons[data-runtime-pending="1"]'))) {
			delete actions.dataset.runtimePending;
			if (String(actions.dataset.streamFooterPlaceholder || '') !== '1') actions.removeAttribute('aria-hidden');
		}
		this.activeTurnIds.clear();
	};

}
