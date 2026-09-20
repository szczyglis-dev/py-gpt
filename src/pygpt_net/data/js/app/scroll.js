// ==========================================================================
// Scroll manager
// ==========================================================================

class ScrollManager {

	constructor(cfg, dom, raf) {
		this.cfg = cfg;
		this.dom = dom;
		this.raf = raf;

		// Page scrolling has one owner at a time:
		// FOLLOW - layout changes keep the viewport at the real physical bottom.
		// MANUAL - user owns the viewport and DOM growth never moves it.
		this.autoFollow = true;
		this.userInteracted = false;
		this.manualResumeCandidate = false;
		this.manualResumeTimer = 0;
		this.manualResumeSeq = 0;
		this.userScrollDirection = 0;
		this.pointerScrollActive = false;

		this.lastScrollTop = 0;
		this.prevScroll = 0;
		this.currentFabAction = 'none';
		this.fabFreezeUntil = 0;
		this.scrollScheduled = false;
		this.scrollFabUpdateScheduled = false;
		this.scrollRAF = 0;
		this.scrollFabRAF = 0;

		// Programmatic page movement must never be interpreted as user intent.
		this.programmaticScrollPending = false;
		this.programmaticScrollTarget = null;

		// The real fix for streaming layout changes. ResizeObserver runs after
		// layout and before paint, so FOLLOW can be corrected to the *actual*
		// document bottom without a visible one-frame jump. This also catches
		// async extras/images/Markdown that change height outside the token path.
		this.contentObserver = null;
		this.contentObserverTarget = null;
		this.contentObserverActive = false;

		// Hybrid message virtualization. Only old/finalized history is allowed to
		// use content-visibility:auto. The exact content-box height is measured
		// first and stored as contain-intrinsic-block-size fallback, so virtualizing
		// history does not change the physical document bottom.
		this.messageSizeObserver = null;
		this.messageVirtualObserved = new Set();
		this.messageVirtualRefreshScheduled = false;
	}

	_cancelScheduledPageScroll() {
		try { this.raf.cancel('SM:scroll'); } catch (_) {}
		this.scrollScheduled = false;
	}

	_clearManualResume() {
		this.manualResumeCandidate = false;
		this.manualResumeSeq += 1;
		if (this.manualResumeTimer) {
			clearTimeout(this.manualResumeTimer);
			this.manualResumeTimer = 0;
		}
	}

	_maxScrollTop() {
		const el = Utils.SE;
		return Math.max(0, el.scrollHeight - el.clientHeight);
	}

	// Set the viewport to the real bottom synchronously. Reading scrollHeight
	// forces current layout, so this never uses a stale/estimated target.
	_syncToPhysicalBottom(force = false) {
		if (!force && this.autoFollow !== true) return false;
		if (!force && this.pointerScrollActive) return false;

		const el = Utils.SE;
		const target = this._maxScrollTop();
		const current = Number(el.scrollTop || 0);
		this.prevScroll = el.scrollHeight;

		if (Math.abs(current - target) <= 0.5) {
			this.lastScrollTop = current;
			return false;
		}

		this.markProgrammaticScroll(target);
		try { el.scrollTop = target; } catch (_) {
			try { el.scrollTo({ top: target, behavior: 'instant' }); } catch (__) {}
		}
		this.lastScrollTop = Number(el.scrollTop || target);
		this.prevScroll = el.scrollHeight;
		return true;
	}

	// Public hook used after known geometry-changing operations (notably extra
	// links). ResizeObserver is still the authoritative async fallback.
	syncBottomNowIfFollowing() {
		if (this.autoFollow !== true) return false;
		const moved = this._syncToPhysicalBottom(false);
		this.scheduleScrollFabUpdate();
		return moved;
	}

	installContentObserver(target = null) {
		this.disconnectContentObserver();
		const host = target || this.dom.get('container');
		if (!host || typeof ResizeObserver === 'undefined') return false;

		try {
			this.contentObserver = new ResizeObserver(() => {
				if (this.autoFollow === true && !this.pointerScrollActive) {
					this._syncToPhysicalBottom(false);
				}
				this.scheduleScrollFabUpdate();
			});
			this.contentObserver.observe(host);
			this.contentObserverTarget = host;
			this.contentObserverActive = true;
			return true;
		} catch (_) {
			this.contentObserver = null;
			this.contentObserverTarget = null;
			this.contentObserverActive = false;
			return false;
		}
	}

	disconnectContentObserver() {
		if (this.contentObserver) {
			try { this.contentObserver.disconnect(); } catch (_) {}
		}
		this.contentObserver = null;
		this.contentObserverTarget = null;
		this.contentObserverActive = false;
	}


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
				for (const entry of entries || []) {
					const box = entry && entry.target;
					if (!box || !box.isConnected) continue;
					if (this._isLiveMessageBox(box)) {
						box.classList.remove('msg-virtualized');
						continue;
					}
					const h = this._measureMessageContentHeight(box, entry);
					if (h > 0) this._storeMessageVirtualHeight(box, h);
				}
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
		try { this.raf.cancel('SM:virtualizeMessages'); } catch (_) {}
	}

	suspendAutoFollow() {
		this._cancelScheduledPageScroll();
		this._clearManualResume();
		this.autoFollow = false;
		this.userInteracted = true;
		this.userScrollDirection = -1;
	}

	resumeAutoFollow(snapToBottom = true) {
		this._clearManualResume();
		this.autoFollow = true;
		this.userInteracted = false;
		this.userScrollDirection = 0;
		if (snapToBottom) this._syncToPhysicalBottom(true);
		this.scheduleScrollFabUpdate();
	}

	noteUserScroll(deltaY = 0) {
		const dir = deltaY < 0 ? -1 : (deltaY > 0 ? 1 : 0);
		if (dir < 0) {
			this.suspendAutoFollow();
			return;
		}
		if (dir > 0 && !this.autoFollow) {
			this._cancelScheduledPageScroll();
			this.userInteracted = true;
			this.userScrollDirection = 1;
			if (this.isAtBottom()) this.armManualResume();
		}
	}

	noteObservedUserScroll(deltaTop = 0) {
		if (deltaTop < -0.5) {
			this.suspendAutoFollow();
			return;
		}
		if (deltaTop > 0.5 && !this.autoFollow) {
			this._cancelScheduledPageScroll();
			this.userInteracted = true;
			this.userScrollDirection = 1;
			if (this.isAtBottom()) this.armManualResume();
			else this._clearManualResume();
		}
	}

	armManualResume(delayMs = 90) {
		if (this.autoFollow || this.userScrollDirection < 0) return;
		this.manualResumeCandidate = true;
		const seq = ++this.manualResumeSeq;
		if (this.manualResumeTimer) clearTimeout(this.manualResumeTimer);
		this.manualResumeTimer = setTimeout(() => {
			this.manualResumeTimer = 0;
			if (seq !== this.manualResumeSeq) return;
			if (!this.manualResumeCandidate || this.autoFollow) return;
			if (this.userScrollDirection < 0) return;
			if (this.pointerScrollActive) {
				this.armManualResume(delayMs);
				return;
			}
			this.resumeAutoFollow(true);
		}, Math.max(0, delayMs | 0));
	}

	setPointerScrollActive(active) {
		this.pointerScrollActive = !!active;
		if (this.pointerScrollActive) return;
		if (this.manualResumeCandidate && !this.autoFollow) {
			this.armManualResume(0);
			return;
		}
		// Content may have grown while the scrollbar thumb was held. If the user
		// never left FOLLOW, catch up exactly once after releasing it.
		if (this.autoFollow) this._syncToPhysicalBottom(false);
	}

	markProgrammaticScroll(targetTop = null) {
		this.programmaticScrollPending = true;
		this.programmaticScrollTarget = Number.isFinite(targetTop) ? targetTop : null;
	}

	isProgrammaticScroll(top) {
		if (!this.programmaticScrollPending) return false;
		const target = this.programmaticScrollTarget;
		const match = target == null || Math.abs(Number(top || 0) - target) <= 4;
		this.programmaticScrollPending = false;
		this.programmaticScrollTarget = null;
		return match;
	}

	isUserScrollingUp() {
		return !this.autoFollow && this.userScrollDirection < 0;
	}

	shouldFollowOnStreamStart() {
		return this.autoFollow === true;
	}

	isNearBottom(marginPx = 100) {
		const el = Utils.SE;
		return (el.scrollHeight - el.clientHeight - el.scrollTop) <= marginPx;
	}

	isAtBottom() {
		const el = Utils.SE;
		const distance = el.scrollHeight - el.clientHeight - el.scrollTop;
		const threshold = Math.max(1, Math.min(Number(this.cfg.UI.AUTO_FOLLOW_REENABLE_PX || 2), 2));
		return distance <= threshold;
	}

	// Live calls become geometry notifications while ResizeObserver is active.
	// There is no token-by-token rAF scroll anymore.
	scheduleScroll(live = false, force = false) {
		if (!force && this.autoFollow !== true) return;

		if (this.contentObserverActive) {
			if (force || live === false) this._syncToPhysicalBottom(!!force);
			this.scheduleScrollFabUpdate();
			return;
		}

		// Fallback for engines without ResizeObserver.
		if (this.scrollScheduled) return;
		this.scrollScheduled = true;
		this.raf.schedule('SM:scroll', () => {
			this.scrollScheduled = false;
			this.scrollToBottom(live, force);
			this.scheduleScrollFabUpdate();
		}, 'ScrollManager', 1);
	}

	cancelPendingScroll() {
		try { this.raf.cancelGroup('ScrollManager'); } catch (_) {}
		this.scrollScheduled = false;
		this.scrollFabUpdateScheduled = false;
		this.scrollRAF = 0;
		this.scrollFabRAF = 0;
		this.programmaticScrollPending = false;
		this.programmaticScrollTarget = null;
		this.messageVirtualRefreshScheduled = false;
	}

	forceScrollToBottomImmediate() {
		this._syncToPhysicalBottom(true);
	}

	forceScrollToBottomImmediateAtEnd() {
		if (!this.autoFollow) return;
		this._syncToPhysicalBottom(false);
		this.scheduleScrollFabUpdate();
	}

	scrollToBottom(live = false, force = false) {
		if (!force && this.autoFollow !== true) {
			this.prevScroll = Utils.SE.scrollHeight;
			return;
		}
		this._syncToPhysicalBottom(!!force);
	}

	hasVerticalScroll() {
		const el = Utils.SE;
		return (el.scrollHeight - el.clientHeight) > 1;
	}

	computeFabAction() {
		const el = Utils.SE;
		const h = el.scrollHeight;
		const c = el.clientHeight;
		const hasScroll = (h - c) > 1;
		if (!hasScroll) return 'none';
		const dist = h - c - el.scrollTop;
		if (dist <= 2) return 'up';
		if (dist >= this.cfg.FAB.SHOW_DOWN_THRESHOLD_PX) return 'down';
		return 'none';
	}

	updateScrollFab(force = false, actionOverride = null, bypassFreeze = false) {
		const btn = this.dom.get('scrollFab');
		const icon = this.dom.get('scrollFabIcon');
		if (!btn || !icon) return;
		const now = Utils.now();
		const action = actionOverride || this.computeFabAction();
		if (!force && !bypassFreeze && now < this.fabFreezeUntil && action !== this.currentFabAction) return;
		if (action === 'none') {
			if (this.currentFabAction !== 'none' || force) {
				btn.classList.remove('visible');
				this.currentFabAction = 'none';
			}
			return;
		}
		if (action !== this.currentFabAction || force) {
			if (action === 'up') {
				if (icon.dataset.dir !== 'up') {
					icon.src = this.cfg.ICONS.COLLAPSE;
					icon.dataset.dir = 'up';
				}
				btn.title = 'Go to top';
			} else {
				if (icon.dataset.dir !== 'down') {
					icon.src = this.cfg.ICONS.EXPAND;
					icon.dataset.dir = 'down';
				}
				btn.title = 'Go to bottom';
			}
			btn.setAttribute('aria-label', btn.title);
			this.currentFabAction = action;
			btn.classList.add('visible');
		} else if (!btn.classList.contains('visible')) btn.classList.add('visible');
	}

	scheduleScrollFabUpdate() {
		if (this.scrollFabUpdateScheduled) return;
		this.scrollFabUpdateScheduled = true;
		this.raf.schedule('SM:fab', () => {
			this.scrollFabUpdateScheduled = false;
			const action = this.computeFabAction();
			if (action !== this.currentFabAction) this.updateScrollFab(false, action);
		}, 'ScrollManager', 2);
	}

	maybeEnableAutoFollowByProximity() {
		if (!this.autoFollow && this.manualResumeCandidate) this.armManualResume();
	}

	scrollToTopUser() {
		this.suspendAutoFollow();
		const el = Utils.SE;
		this.markProgrammaticScroll(0);
		try { el.scrollTop = 0; } catch (_) {
			try { el.scrollTo({ top: 0, behavior: 'instant' }); } catch (__) {}
		}
		this.lastScrollTop = Number(el.scrollTop || 0);
	}

	scrollToBottomUser() {
		this.resumeAutoFollow(true);
	}
}

// ==========================================================================
// Code scroll state manager
// ==========================================================================

class CodeScrollState {

	// Code scroll state manager for tracking scroll positions and interactions.
	constructor(cfg, raf) {
		this.cfg = cfg;
		this.raf = raf;
		this.map = new WeakMap();
		this.rafMap = new WeakMap();
		this.rafIds = new Set(); // legacy
		this.rafKeyMap = new WeakMap();
	}

	// Get or create per-code element state.
	state(el) {
		let s = this.map.get(el);
		if (!s) {
			s = {
				autoFollow: false,
				lastScrollTop: 0,
				userInteracted: false,
				freezeUntil: 0,
				listeners: null, // { onScroll, onWheel, onTouchStart }
			};
			this.map.set(el, s);
		}
		return s;
	}

	// Check if code block is already finalized (not streaming).
	isFinalizedCode(el) {
		if (!el || el.tagName !== 'CODE') return false;
		if (el.dataset && el.dataset._active_stream === '1') return false;
		const highlighted = (el.getAttribute('data-highlighted') === 'yes') || el.classList.contains('hljs');
		return highlighted;
	}

	// Is element scrolled close to the bottom by a margin?
	isNearBottomEl(el, margin = 100) {
		if (!el) return true;
		const distance = el.scrollHeight - el.clientHeight - el.scrollTop;
		return distance <= margin;
	}

	// Scroll code element to the bottom respecting interaction state.
	scrollToBottom(el, live = false, force = false) {
		if (!el || !el.isConnected) return;
		if (!force && this.isFinalizedCode(el)) return;

		const st = this.state(el);
		const now = Utils.now();
		if (!force && st.freezeUntil && now < st.freezeUntil) return;

		const distNow = el.scrollHeight - el.clientHeight - el.scrollTop;
		if (!force && distNow <= 1) {
			st.lastScrollTop = el.scrollTop;
			return;
		}

		const marginPx = live ? 96 : this.cfg.CODE_SCROLL.NEAR_MARGIN_PX;
		const behavior = 'instant';

		if (!force) {
			if (live && st.autoFollow !== true) return;
			if (!live && !(st.autoFollow === true || this.isNearBottomEl(el, marginPx) || !st.userInteracted)) return;
		}

		try {
			el.scrollTo({
				top: el.scrollHeight,
				behavior
			});
		} catch (_) {
			el.scrollTop = el.scrollHeight;
		}
		st.lastScrollTop = el.scrollTop;
	}

	// Schedule bottom scroll in rAF (coalesces multiple calls).
	scheduleScroll(el, live = false, force = false) {
		if (!el || !el.isConnected) return;
		if (!force && this.isFinalizedCode(el)) return;
		if (this.rafMap.get(el)) return;
		this.rafMap.set(el, true);

		let key = this.rafKeyMap.get(el);
		if (!key) {
			key = Symbol('codeScroll');
			this.rafKeyMap.set(el, key);
		}

		this.raf.schedule(key, () => {
			this.rafMap.delete(el);
			this.scrollToBottom(el, live, force);
		}, 'CodeScroll', 0);
	}

	// Attach scroll/wheel/touch handlers to manage auto-follow state.
	attachHandlers(codeEl) {
		if (!codeEl || codeEl.dataset.csListeners === '1') return;
		if (codeEl.dataset._active_stream !== '1') return;
		codeEl.dataset.csListeners = '1';
		const st = this.state(codeEl);

		const onScroll = (ev) => {
			const top = codeEl.scrollTop;
			const isUser = !!(ev && ev.isTrusted === true);
			const now = Utils.now();

			if (this.isFinalizedCode(codeEl)) {
				if (isUser) st.userInteracted = true;
				st.autoFollow = false;
				st.lastScrollTop = top;
				return;
			}

			if (isUser) {
				if (top + 1 < st.lastScrollTop) {
					st.autoFollow = false;
					st.userInteracted = true;
					st.freezeUntil = now + 1000;
				} else if (this.isNearBottomEl(codeEl, this.cfg.CODE_SCROLL.AUTO_FOLLOW_REENABLE_PX)) {
					st.autoFollow = true;
				}
			} else {
				if (this.isNearBottomEl(codeEl, this.cfg.CODE_SCROLL.AUTO_FOLLOW_REENABLE_PX)) st.autoFollow = true;
			}
			st.lastScrollTop = top;
		};

		const onWheel = (ev) => {
			st.userInteracted = true;
			const now = Utils.now();

			if (this.isFinalizedCode(codeEl)) {
				st.autoFollow = false;
				return;
			}

			if (ev.deltaY < 0) {
				st.autoFollow = false;
				st.freezeUntil = now + 1000;
			} else if (this.isNearBottomEl(codeEl, this.cfg.CODE_SCROLL.AUTO_FOLLOW_REENABLE_PX)) {
				st.autoFollow = true;
			}
		};

		const onTouchStart = () => {
			st.userInteracted = true;
		};

		codeEl.addEventListener('scroll', onScroll, {
			passive: true
		});
		codeEl.addEventListener('wheel', onWheel, {
			passive: true
		});
		codeEl.addEventListener('touchstart', onTouchStart, {
			passive: true
		});
		st.listeners = {
			onScroll,
			onWheel,
			onTouchStart
		};
	}

    // Detach event handlers from code element.
	detachHandlers(codeEl) {
		if (!codeEl) return;
		const st = this.map.get(codeEl);
		const h = st && st.listeners;
		if (!h) {
			codeEl.dataset.csListeners = '0';
			return;
		}
		try {
			codeEl.removeEventListener('scroll', h.onScroll);
		} catch (_) {}
		try {
			codeEl.removeEventListener('wheel', h.onWheel);
		} catch (_) {}
		try {
			codeEl.removeEventListener('touchstart', h.onTouchStart);
		} catch (_) {}
		st.listeners = null;
		codeEl.dataset.csListeners = '0';
	}

	// Attach handlers to all bot code blocks under root (or document).
	// IMPORTANT: We intentionally do NOT auto-scroll finalized/static code blocks to the bottom.
	// Only actively streaming code blocks (data-_active_stream="1") are auto-followed live.
	initScrollableBlocks(root) {
		const scope = root || document;
		let nodes = [];
		if (scope.nodeType === 1 && scope.closest && scope.closest('.msg-box.msg-bot')) {
			nodes = scope.querySelectorAll('pre code');
		} else {
			nodes = document.querySelectorAll('.msg-box.msg-bot pre code');
		}
		if (!nodes.length) return;

		nodes.forEach((code) => {
			if (code.dataset._active_stream === '1') {
				this.attachHandlers(code); // only attach to streaming code blocks
				const st = this.state(code);
				st.autoFollow = true;
				this.scheduleScroll(code, true, false);
			} else {
				this.detachHandlers(code);
			}
		});
	}

	// Transfer stored scroll state between elements (after replace).
	transfer(oldEl, newEl) {
		if (!oldEl || !newEl || oldEl === newEl) return;
		const oldState = this.map.get(oldEl);
		if (oldState) this.map.set(newEl, {
			...oldState
		});
		this.detachHandlers(oldEl);
		this.attachHandlers(newEl);
	}

	// Cancel any scheduled scroll tasks for code blocks.
	cancelAllScrolls() {
		try {
			this.raf.cancelGroup('CodeScroll');
		} catch (_) {}
		this.rafMap = new WeakMap();
		this.rafIds.clear();
		this.rafKeyMap = new WeakMap();
	}
}