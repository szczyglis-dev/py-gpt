// ==========================================================================
// Loading indicator
// ==========================================================================

class Loading {

	// Loading indicator spinner
	constructor(dom) {
		this.dom = dom;
		this._showFrame = null;
		this._showDelayTimer = null;
		this._pendingShow = null;
		this._hideTimer = null;
		this._hideHandler = null;
		this._transitionToken = 0;
	}

	// Cancel any pending visibility transition callbacks.
	_cancelPending(el) {
		this._transitionToken += 1;
		if (this._showFrame !== null) {
			try { cancelAnimationFrame(this._showFrame); } catch (_) {}
			this._showFrame = null;
		}
		if (this._showDelayTimer !== null) {
			try { clearTimeout(this._showDelayTimer); } catch (_) {}
			this._showDelayTimer = null;
		}
		this._pendingShow = null;
		if (this._hideTimer !== null) {
			try { clearTimeout(this._hideTimer); } catch (_) {}
			this._hideTimer = null;
		}
		if (el && this._hideHandler) {
			try { el.removeEventListener('transitionend', this._hideHandler); } catch (_) {}
		}
		this._hideHandler = null;
	}

	// Keep the loader footprint stable once the user row exists.  This reserves
	// the final spinner slot while it is still transparent, so the later fade-in
	// cannot change document height or move the viewport.
	_reserve(el, token) {
		if (!el || token !== this._transitionToken) return;
		el.classList.remove('hidden', 'visible');
		el.classList.add('reserved');
	}

	// Commit a pending show only after both gates have opened: the optional
	// delay and, for manual sends, materialization of the input row.
	_tryShowPending() {
		const pending = this._pendingShow;
		if (!pending || pending.token !== this._transitionToken) return;
		if (!pending.delayReady || !pending.inputReady) return;

		const el = this.dom.get('_loader_');
		if (!el) return;
		this._reserve(el, pending.token);
		this._pendingShow = null;
		if (this._showDelayTimer !== null) {
			try { clearTimeout(this._showDelayTimer); } catch (_) {}
			this._showDelayTimer = null;
		}

		// Force the opacity:0 state to be committed before enabling .visible.
		void el.offsetWidth;
		const token = this._transitionToken;
		this._showFrame = requestAnimationFrame(() => {
			this._showFrame = null;
			if (token !== this._transitionToken) return;
			el.classList.remove('reserved');
			el.classList.add('visible');
		});
	}

	// Notify the loader that the current user input row now exists in the DOM.
	// If the 500 ms delay already elapsed, the spinner fades in on the next
	// frame; otherwise its invisible slot is reserved now and only opacity
	// changes when the delay expires.
	inputReady() {
		const pending = this._pendingShow;
		if (!pending || !pending.waitForInput || pending.token !== this._transitionToken) return;
		pending.inputReady = true;
		const el = this.dom.get('_loader_');
		if (el) this._reserve(el, pending.token);
		this._tryShowPending();
	}

	// Show loader with an optional delay.  waitForInput is used only for a
	// manual SEND_INIT: the spinner is never allowed to enter layout before the
	// user row, which removes the input-vs-spinner vertical jump.
	show(delayMs = 0, waitForInput = false) {
		if (typeof window.hideTips === 'function') {
			window.hideTips();
		}
		const el = this.dom.get('_loader_');
		if (!el) return;
		if (el.classList.contains('visible')) return;

		this._cancelPending(el);
		const token = this._transitionToken;
		const delay = Math.max(0, Number(delayMs) || 0);
		this._pendingShow = {
			token,
			waitForInput: !!waitForInput,
			inputReady: !waitForInput,
			delayReady: delay <= 0,
		};

		// Non-gated delayed callers may reserve immediately.  A SEND_INIT gated
		// by input waits until inputReady(), so the loader can never precede it.
		if (!waitForInput) this._reserve(el, token);

		if (delay > 0) {
			this._showDelayTimer = setTimeout(() => {
				this._showDelayTimer = null;
				const current = this._pendingShow;
				if (!current || current.token !== this._transitionToken) return;
				current.delayReady = true;
				this._tryShowPending();
			}, delay);
		}
		this._tryShowPending();
	}

	// Hide loader with a CSS fade-out. When reserveSpace is true, keep the
	// invisible layout slot after the fade; otherwise switch to display:none
	// only after the opacity transition has completed.
	hide(reserveSpace = false) {
		const el = this.dom.get('_loader_');
		if (!el) return;

		const wasVisible = el.classList.contains('visible');
		const wasReserved = el.classList.contains('reserved');
		this._cancelPending(el);
		const token = this._transitionToken;

		if (el.classList.contains('hidden')) return;

		el.classList.remove('visible', 'hidden');
		el.classList.add('reserved');

		if (reserveSpace) return;

		const finish = () => {
			if (token !== this._transitionToken) return;
			if (this._hideTimer !== null) {
				try { clearTimeout(this._hideTimer); } catch (_) {}
				this._hideTimer = null;
			}
			if (this._hideHandler) {
				try { el.removeEventListener('transitionend', this._hideHandler); } catch (_) {}
				this._hideHandler = null;
			}
			if (!el.classList.contains('visible')) {
				el.classList.remove('reserved');
				el.classList.add('hidden');
			}
		};

		// If it is already fully transparent, there is nothing left to animate.
		if (!wasVisible && wasReserved) {
			finish();
			return;
		}

		this._hideHandler = (event) => {
			if (event.target !== el || event.propertyName !== 'opacity') return;
			finish();
		};
		el.addEventListener('transitionend', this._hideHandler);
		// Fallback for WebEngine cases where transitionend is skipped.
		this._hideTimer = setTimeout(finish, 400);
	}
}

// ==========================================================================
// Tips manager
// ==========================================================================

class TipsManager {

	// Lightweight tips rotator that works with your CSS (.tips/.visible)
	// and is backward-compatible with legacy `let tips = [...]` injection.
	constructor(dom) {
		this.dom = dom;
		this.hidden = false;
		this._timers = [];
		this._running = false;
		this._idx = 0;
	}

	// Resolve tips list from multiple legacy/new sources.
	_getList() {
		// New preferred: window.TIPS (array)
		const upper = (typeof window !== 'undefined') ? window.TIPS : undefined;
		if (Array.isArray(upper) && upper.length) return upper;

		// Legacy inline: window.tips (array or JSON string)
		const lower = (typeof window !== 'undefined') ? window.tips : undefined;
		if (Array.isArray(lower) && lower.length) return lower;
		if (typeof lower === 'string' && lower.trim().length) {
			try {
				const arr = JSON.parse(lower);
				if (Array.isArray(arr)) return arr;
			} catch (_) {}
		}

		// Optional: data-tips='["...","..."]' on #tips
		const host = this._host();
		if (host && host.dataset && typeof host.dataset.tips === 'string') {
			try {
				const arr = JSON.parse(host.dataset.tips);
				if (Array.isArray(arr)) return arr;
			} catch (_) {}
		}

		return [];
	}

	// Get the tips container element.
	_host() {
		return this.dom.get('tips') || document.getElementById('tips');
	}

	// Clear all timers.
	_clearTimers() {
		for (const t of this._timers) {
			try {
				clearTimeout(t);
			} catch (_) {}
		}
		this._timers.length = 0;
	}

	// Stop any running rotation timers.
	stopTimers() {
		this._clearTimers();
		this._running = false;
	}

	// Apply base styles to the tips container.
	_applyBaseStyle(el) {
		if (!el) return;
		// Keep your flex layout and sizing; do not overwrite width/height.
		// Ensure it renders above other layers.
		const z = (typeof window !== 'undefined' && typeof window.TIPS_ZINDEX !== 'undefined') ?
			String(window.TIPS_ZINDEX) : '2147483000';
		el.style.zIndex = z;
	}

	// Hide tips layer and stop rotation.
	hide() {
		if (this.hidden) return;
		this.stopTimers();
		const el = this._host();
		if (el) {
			// Remove visibility class and hide hard (used when stream starts etc.)
			el.classList.remove('visible');
			el.classList.remove('hidden'); // in case it was set elsewhere
			el.style.display = 'none';
		}
		this.hidden = true;
	}

	// Show tips layer (does not start rotation).
	show() {
		const list = this._getList();
		if (!list.length) return;
		const el = this._host();
		if (!el) return;

		this.hidden = false;
		this._applyBaseStyle(el);
		el.classList.remove('hidden');
		el.style.display = 'block'; // CSS handles opacity via .tips/.visible
		// Do not add 'visible' yet – cycle() takes care of fade-in steps.
	}

	// Show one tip (by index) and fade it in next frame.
	_showOne(idx) {
		const list = this._getList();
		if (!list.length) return;
		const el = this._host();
		if (!el || this.hidden) return;

		this._applyBaseStyle(el);
		el.innerHTML = list[idx % list.length];

		// Centralize "next-frame" visibility toggle through RafManager to guarantee CSS transition.
		try {
			if (typeof runtime !== 'undefined' && runtime.raf && typeof runtime.raf.schedule === 'function') {
				const key = {
					t: 'Tips:show',
					el,
					i: Math.random()
				};
				runtime.raf.schedule(key, () => {
					if (this.hidden || !el.isConnected) return;
					el.classList.add('visible');
				}, 'Tips', 2);
			} else {
				// Fallback: no frame delay – still functional, transition may not play.
				el.classList.add('visible');
			}
		} catch (_) {
			el.classList.add('visible');
		}
	}

	// Internal loop: show, wait, hide, wait fade, next.
	_cycleLoop() {
		if (this.hidden) return;
		const el = this._host();
		if (!el) return;

		const VISIBLE_MS = (typeof window !== 'undefined' && window.TIPS_VISIBLE_MS) ? window.TIPS_VISIBLE_MS : 15000;
		const FADE_MS = (typeof window !== 'undefined' && window.TIPS_FADE_MS) ? window.TIPS_FADE_MS : 1000;

		this._showOne(this._idx);

		// Sequence: visible -> wait -> remove 'visible' -> wait fade -> next
		this._timers.push(setTimeout(() => {
			if (this.hidden) return;
			el.classList.remove('visible');
			this._timers.push(setTimeout(() => {
				if (this.hidden) return;
				const list = this._getList();
				if (!list.length) return;
				this._idx = (this._idx + 1) % list.length;
				this._cycleLoop();
			}, FADE_MS));
		}, VISIBLE_MS));
	}

	// Start rotation with initial delay.
	cycle() {
		const list = this._getList();
		if (!list.length || this._running) return;
		this._running = true;
		this._idx = 0;
		this.show(); // make sure the host is visible and centered

		const INIT_DELAY = (typeof window !== 'undefined' && window.TIPS_INIT_DELAY_MS) ? window.TIPS_INIT_DELAY_MS : 10000;
		this._timers.push(setTimeout(() => {
			if (this.hidden) return;
			this._cycleLoop();
		}, Math.max(0, INIT_DELAY)));
	}

	// Stop and reset.
	cleanup() {
		this.stopTimers();
		const el = this._host();
		if (el) el.classList.remove('visible');
	}
}