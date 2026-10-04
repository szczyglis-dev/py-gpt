// ==========================================================================
// Scroll manager
// ==========================================================================

class ScrollManager {

	// ========================================
	// Composition
	// ========================================

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

		this.virtualization = new MessageVirtualization(cfg, dom, raf);
	}

	// ========================================
	// Scroll ownership and user interaction
	// ========================================

	// Public hook used after known geometry-changing operations (notably extra
	// links). ResizeObserver is still the authoritative async fallback.
	syncBottomNowIfFollowing() {
		if (this.autoFollow !== true) return false;
		const moved = this._syncToPhysicalBottom(false);
		this.scheduleScrollFabUpdate();
		return moved;
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
		// A scroll event is not proof of user input. Removing the request loader
		// can shrink the document and Chromium clamps scrollTop upward. Wheel and
		// keyboard intent is handled before scrolling by noteUserScroll(); only a
		// held scrollbar/touch pointer may transfer FOLLOW here.
		if (this.autoFollow && !this.pointerScrollActive) return;
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
		if (!active && this.pointerScrollActive) {
			// The final scroll event may arrive after pointerup. Observe the drag
			// before releasing it, otherwise catching up to bottom erases its intent.
			const top = Number(Utils.SE.scrollTop || 0);
			if (!this.isProgrammaticScroll(top)) this.noteObservedUserScroll(top - this.lastScrollTop);
			this.lastScrollTop = top;
		}
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

	// ========================================
	// Content observation
	// ========================================

	installContentObserver(target = null) {
		this.disconnectContentObserver();
		const host = target || this.dom.get('container');
		if (!host || typeof ResizeObserver === 'undefined') return false;

		try {
			this.contentObserver = new ResizeObserver(() => {
				// Do not mutate scroll/layout from inside the ResizeObserver delivery
				// cycle. Chromium reports "loop completed with undelivered
				// notifications" when observer callbacks synchronously trigger more
				// geometry work. Coalesce the reaction into the next animation frame.
				this.raf.schedule('SM:contentResizeObserver', () => {
					if (this.autoFollow === true && !this.pointerScrollActive) {
						this._syncToPhysicalBottom(false);
					}
					this.scheduleScrollFabUpdate();
				}, 'ScrollManager', 0);
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
		try { this.raf.cancel('SM:contentResizeObserver'); } catch (_) {}
	}

	// ========================================
	// Page scrolling
	// ========================================

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

	// ========================================
	// Scroll navigation button
	// ========================================

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

	// ========================================
	// Page scrolling internals
	// ========================================

	_cancelScheduledPageScroll() {
		try { this.raf.cancel('SM:scroll'); } catch (_) {}
		this.scrollScheduled = false;
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

	// ========================================
	// Scroll ownership and user interaction internals
	// ========================================

	_clearManualResume() {
		this.manualResumeCandidate = false;
		this.manualResumeSeq += 1;
		if (this.manualResumeTimer) {
			clearTimeout(this.manualResumeTimer);
			this.manualResumeTimer = 0;
		}
	}

}
