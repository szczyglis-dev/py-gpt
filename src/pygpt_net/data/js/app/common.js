// ==========================================================================
// Loading indicator
// ==========================================================================

class Loading {

	// Loading indicator spinner
	constructor(dom) {
		this.dom = dom;
	}

	// Show loader element (and hide tips if visible).
	show() {
		if (typeof window.hideTips === 'function') {
			window.hideTips();
		}
		const el = this.dom.get('_loader_');
		if (!el) return;
		if (el.classList.contains('hidden')) el.classList.remove('hidden');
		el.classList.add('visible');
	}

	// Hide loader element.
	hide() {
		const el = this.dom.get('_loader_');
		if (!el) return;
		if (el.classList.contains('visible')) el.classList.remove('visible');
		el.classList.add('hidden');
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