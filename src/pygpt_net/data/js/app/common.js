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
