// ==========================================================================
// Scroll manager
// ==========================================================================

class ScrollManager {

	// Scroll management
	constructor(cfg, dom, raf) {
		this.cfg = cfg;
		this.dom = dom;
		this.raf = raf;
		this.autoFollow = true;
		this.userInteracted = false;
		this.lastScrollTop = 0;
		this.prevScroll = 0;
		this.currentFabAction = 'none';
		this.fabFreezeUntil = 0;
		this.scrollScheduled = false;
		this.scrollFabUpdateScheduled = false;
		this.scrollRAF = 0;
		this.scrollFabRAF = 0;
	}

	// Is page near the bottom by given margin?
	isNearBottom(marginPx = 100) {
		const el = Utils.SE;
		const distance = el.scrollHeight - el.clientHeight - el.scrollTop;
		return distance <= marginPx;
	}

	// Schedule a page scroll to bottom if auto-follow allows it.
	scheduleScroll(live = false) {
		if (live === true && this.autoFollow !== true) return;
		if (this.scrollScheduled) return;
		this.scrollScheduled = true;
		this.raf.schedule('SM:scroll', () => {
			this.scrollScheduled = false;
			this.scrollToBottom(live);
			this.scheduleScrollFabUpdate();
		}, 'ScrollManager', 1);
	}

	// Cancel any pending page scroll.
	cancelPendingScroll() {
		try {
			this.raf.cancelGroup('ScrollManager');
		} catch (_) {}
		this.scrollScheduled = false;
		this.scrollFabUpdateScheduled = false;
		this.scrollRAF = 0;
		this.scrollFabRAF = 0;
	}

	// Jump to bottom immediately (no smooth behavior).
	forceScrollToBottomImmediate() {
		const el = Utils.SE;
		el.scrollTop = el.scrollHeight;
		this.prevScroll = el.scrollHeight;
	}

	// Jump to bottom immediately (no smooth behavior).
	forceScrollToBottomImmediateAtEnd() {
	    if (this.userInteracted === true || !this.isNearBottom(200)) return;
		const el = Utils.SE;
		setTimeout(() => {
            el.scrollTo({
                top: el.scrollHeight,
                behavior: 'instant'
            });
            this.lastScrollTop = el.scrollTop;
		    this.prevScroll = el.scrollHeight;
        }, 100);
	}

	// Scroll window to bottom based on auto-follow and margins.
	scrollToBottom(live = false, force = false) {
		const el = Utils.SE;
		const marginPx = this.cfg.UI.SCROLL_NEAR_MARGIN_PX;
		const behavior = 'instant';
		const h = el.scrollHeight;
		if (live === true && this.autoFollow !== true) {
			this.prevScroll = h;
			return;
		}
		if ((live === true && this.userInteracted === false) || this.isNearBottom(marginPx) || live === false || force) {
			try {
				el.scrollTo({
					top: h,
					behavior
				});
			} catch (_) {
				el.scrollTop = h;
			}
		}
		this.prevScroll = el.scrollHeight;
	}

	// Check if window has vertical scroll bar.
	hasVerticalScroll() {
		const el = Utils.SE;
		return (el.scrollHeight - el.clientHeight) > 1;
	}

	// Compute the current FAB action (none/up/down).
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

	// Update FAB to show correct direction and label.
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
				btn.title = "Go to top";
			} else {
				if (icon.dataset.dir !== 'down') {
					icon.src = this.cfg.ICONS.EXPAND;
					icon.dataset.dir = 'down';
				}
				btn.title = "Go to bottom";
			}
			btn.setAttribute('aria-label', btn.title);
			this.currentFabAction = action;
			btn.classList.add('visible');
		} else if (!btn.classList.contains('visible')) btn.classList.add('visible');
	}

	// Schedule a FAB state refresh.
	scheduleScrollFabUpdate() {
		if (this.scrollFabUpdateScheduled) return;
		this.scrollFabUpdateScheduled = true;
		this.raf.schedule('SM:fab', () => {
			this.scrollFabUpdateScheduled = false;
			const action = this.computeFabAction();
			if (action !== this.currentFabAction) this.updateScrollFab(false, action);
		}, 'ScrollManager', 2);
	}

	// If user is near bottom, enable auto-follow again.
	maybeEnableAutoFollowByProximity() {
		const el = Utils.SE;
		if (!this.autoFollow) {
			const dist = el.scrollHeight - el.clientHeight - el.scrollTop;
			if (dist <= this.cfg.UI.AUTO_FOLLOW_REENABLE_PX) this.autoFollow = true;
		}
	}

	// User-triggered scroll to top; disables auto-follow.
	scrollToTopUser() {
		this.userInteracted = true;
		this.autoFollow = false;
		try {
			const el = Utils.SE;
			el.scrollTo({
				top: 0,
				behavior: 'instant'
			});
			this.lastScrollTop = el.scrollTop;
		} catch (_) {
			const el = Utils.SE;
			el.scrollTop = 0;
			this.lastScrollTop = 0;
		}
	}

	// User-triggered scroll to bottom; may re-enable auto-follow if near bottom.
	scrollToBottomUser() {
		this.userInteracted = true;
		this.autoFollow = false;
		try {
			const el = Utils.SE;
			el.scrollTo({
				top: el.scrollHeight,
				behavior: 'instant'
			});
			this.lastScrollTop = el.scrollTop;
		} catch (_) {
			const el = Utils.SE;
			el.scrollTop = el.scrollHeight;
			this.lastScrollTop = el.scrollTop;
		}
		this.maybeEnableAutoFollowByProximity();
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