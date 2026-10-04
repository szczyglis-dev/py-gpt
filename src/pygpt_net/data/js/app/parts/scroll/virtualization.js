class MessageVirtualization {

	// ========================================
	// Composition
	// ========================================

	constructor(cfg, dom, raf) {
		this.cfg = cfg;
		this.dom = dom;
		this.raf = raf;
		this.messageSizeObserver = null;
		this.messageVirtualObserved = new Set();
		this.messageVirtualRefreshScheduled = false;
		this.messageSizeObserverPending = new Map();
	}

	// ========================================
	// Virtualization
	// ========================================

	refreshMessageVirtualization() {
		this.messageVirtualRefreshScheduled = false;
		const boxes = this._topLevelBotMessages();
		if (!boxes.length) return;
		const keep = Math.max(1, Number((this.cfg.UI && this.cfg.UI.MESSAGE_VIRTUAL_KEEP_RECENT) || 2) | 0);
		const realFrom = Math.max(0, boxes.length - keep);
		const toReal = [];
		const toVirtual = [];

		for (let i = 0; i < boxes.length; i++) {
			const box = boxes[i];
			this._observeVirtualMessage(box);
			if (i >= realFrom || this._isLiveMessageBox(box)) toReal.push(box);
			else toVirtual.push(box);
		}

		// Phase 1: make the recent/live tail real. This is normally a no-op; when
		// a context changes, doing all class removals together avoids interleaving
		// layout writes with the height reads below.
		for (const box of toReal) this._devirtualizeMessageBox(box);

		// Phase 2: collect every required geometry read before writing CSS/classes.
		// On a huge initial history load this prevents N forced reflow cycles.
		const measured = [];
		for (const box of toReal) {
			const h = this._measureMessageContentHeight(box);
			if (h > 0) measured.push([box, h]);
		}
		for (const box of toVirtual) {
			if (box.dataset.pygptVirtualHeight) continue;
			const h = this._measureMessageContentHeight(box);
			if (h > 0) measured.push([box, h]);
		}

		// Phase 3: writes only. Old rows now have an exact fallback before
		// content-visibility:auto is enabled.
		for (const [box, h] of measured) this._storeMessageVirtualHeight(box, h);
		for (const box of toVirtual) {
			if (box.dataset.pygptVirtualHeight) {
				try { box.classList.add('msg-virtualized'); } catch (_) {}
			}
		}

		// Avoid retaining removed DOM nodes in the bookkeeping Set.
		for (const box of Array.from(this.messageVirtualObserved)) {
			if (box && box.isConnected) continue;
			try { if (this.messageSizeObserver) this.messageSizeObserver.unobserve(box); } catch (_) {}
			this.messageVirtualObserved.delete(box);
		}
	}

	scheduleMessageVirtualizationRefresh() {
		if (this.messageVirtualRefreshScheduled) return;
		this.messageVirtualRefreshScheduled = true;
		this.raf.schedule('SM:virtualizeMessages', () => {
			this.refreshMessageVirtualization();
		}, 'ScrollManager', 2);
	}

	beginMessageMutation(box) {
		if (!box) return;
		try {
			if (box.classList.contains('msg-virtualized')) {
				box.dataset.pygptRevirtualize = '1';
				box.classList.remove('msg-virtualized');
			}
		} catch (_) {}
	}

	endMessageMutation(box) {
		if (!box) return;
		this._captureMessageVirtualHeight(box);
		try { delete box.dataset.pygptRevirtualize; } catch (_) {}
		this.scheduleMessageVirtualizationRefresh();
	}

	disconnectMessageVirtualization() {
		if (this.messageSizeObserver) {
			try { this.messageSizeObserver.disconnect(); } catch (_) {}
		}
		this.messageSizeObserver = null;
		this.messageVirtualObserved.clear();
		this.messageVirtualRefreshScheduled = false;
		this.messageSizeObserverPending.clear();
		try { this.raf.cancel('SM:messageSizeObserver'); } catch (_) {}
		try { this.raf.cancel('SM:virtualizeMessages'); } catch (_) {}
	}

	// ========================================
	// Virtualization internals
	// ========================================

	_messageVirtualRoot() {
		return this.dom.get('_nodes_');
	}

	_topLevelBotMessages() {
		const root = this._messageVirtualRoot();
		if (!root) return [];
		let nodes = [];
		try { nodes = Array.from(root.querySelectorAll('.msg-box.msg-bot')); } catch (_) { return []; }
		return nodes.filter((box) => {
			if (!box || !box.isConnected) return false;
			// Tool groups may contain nested .msg-bot rows. Virtualize only the
			// outer message/group box; nesting content-visibility containers makes
			// intrinsic-size accounting unnecessarily fragile.
			try {
				const parentBot = box.parentElement && box.parentElement.closest
					? box.parentElement.closest('.msg-box.msg-bot') : null;
				if (parentBot) return false;
			} catch (_) {}
			return true;
		});
	}

	_isLiveMessageBox(box) {
		if (!box || !box.isConnected) return false;
		try {
			if (box.closest('#_append_output_, #_append_output_before_')) return true;
			if (box.classList.contains('msg-live')) return true;
			if (box.querySelector('[data-live-part="1"], [data-_active_stream="1"]')) return true;
		} catch (_) {}
		return false;
	}

	_measureMessageContentHeight(box, entry = null) {
		if (!box || !box.isConnected) return 0;
		try {
			if (entry) {
				const cbs = entry.contentBoxSize;
				if (cbs) {
					const item = Array.isArray(cbs) ? cbs[0] : cbs;
					const block = item && Number(item.blockSize);
					if (Number.isFinite(block) && block > 0) return block;
				}
				const cr = entry.contentRect;
				const eh = cr && Number(cr.height);
				if (Number.isFinite(eh) && eh > 0) return eh;
			}

			// getBoundingClientRect() is border-box. Convert it to the content-box
			// size expected by contain-intrinsic-block-size.
			const rect = box.getBoundingClientRect();
			let h = Number(rect.height || 0);
			const cs = getComputedStyle(box);
			const n = (v) => Number.parseFloat(v || '0') || 0;
			h -= n(cs.paddingTop) + n(cs.paddingBottom) + n(cs.borderTopWidth) + n(cs.borderBottomWidth);
			return Number.isFinite(h) ? Math.max(1, h) : 0;
		} catch (_) {
			return 0;
		}
	}

	_storeMessageVirtualHeight(box, height) {
		const h = Number(height || 0);
		if (!box || !Number.isFinite(h) || h <= 0) return false;
		// Round only to hundredths; integer rounding can accumulate visible error
		// over hundreds of virtualized messages.
		const value = Math.max(1, Math.round(h * 100) / 100);
		try {
			box.style.setProperty('--pygpt-msg-virtual-height', `${value}px`);
			box.dataset.pygptVirtualHeight = String(value);
			return true;
		} catch (_) {
			return false;
		}
	}

	_captureMessageVirtualHeight(box) {
		return this._storeMessageVirtualHeight(box, this._measureMessageContentHeight(box));
	}

	_installMessageSizeObserver() {
		if (this.messageSizeObserver || typeof ResizeObserver === 'undefined') return;
		try {
			this.messageSizeObserver = new ResizeObserver((entries) => {
				// Read observer data now, but defer DOM/style writes until the next
				// frame so those writes cannot recursively participate in the same
				// ResizeObserver notification cycle.
				for (const entry of entries || []) {
					const box = entry && entry.target;
					if (!box || !box.isConnected) continue;
					if (this._isLiveMessageBox(box)) {
						this.messageSizeObserverPending.set(box, null);
						continue;
					}
					const h = this._measureMessageContentHeight(box, entry);
					if (h > 0) this.messageSizeObserverPending.set(box, h);
				}
				this.raf.schedule('SM:messageSizeObserver', () => {
					const pending = this.messageSizeObserverPending;
					this.messageSizeObserverPending = new Map();
					pending.forEach((height, box) => {
						if (!box || !box.isConnected) return;
						if (height === null || this._isLiveMessageBox(box)) {
							box.classList.remove('msg-virtualized');
							return;
						}
						this._storeMessageVirtualHeight(box, height);
					});
				}, 'ScrollManager', 0);
			});
		} catch (_) {
			this.messageSizeObserver = null;
		}
	}

	_observeVirtualMessage(box) {
		if (!box || !box.isConnected) return;
		this._installMessageSizeObserver();
		if (!this.messageSizeObserver || this.messageVirtualObserved.has(box)) return;
		try {
			this.messageSizeObserver.observe(box);
			this.messageVirtualObserved.add(box);
		} catch (_) {}
	}

	_virtualizeMessageBox(box) {
		if (!box || !box.isConnected || this._isLiveMessageBox(box)) return;
		this._observeVirtualMessage(box);
		if (!box.dataset.pygptVirtualHeight) this._captureMessageVirtualHeight(box);
		try { box.classList.add('msg-virtualized'); } catch (_) {}
	}

	_devirtualizeMessageBox(box) {
		if (!box) return;
		try { box.classList.remove('msg-virtualized'); } catch (_) {}
	}

}
