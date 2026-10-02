// StreamReasoning owns reasoning behavior and state.
class StreamReasoning {

	// ========================================
	// Composition
	// ========================================

	constructor(engine) {
		this.engine = engine;
		// Live provider reasoning visibility. Provider reasoning is streamed through
		// <think>...</think> only when explicitly enabled by the user. Python uses
		// the same setting to decide whether readable reasoning is requested/stored.
		const reasoningCfg = (engine.cfg && engine.cfg.REASONING) ? engine.cfg.REASONING : {};
		this.reasoningEnabled = reasoningCfg.SHOW_REALTIME === true;
		this.reasoningHideAfterResponse = reasoningCfg.HIDE_AFTER_RESPONSE !== false;
		this.reasoningThinking = false;
		this.reasoningVisible = false;
		this.reasoningHasResponseText = false;
		this.reasoningFadeOutDelay = Math.max(0, Number(reasoningCfg.FADE_OUT_DELAY_MS) || 0);
		this.reasoningFadeDuration = Math.max(0, Number(reasoningCfg.FADE_DURATION_MS) || 0);
		this.reasoningFadeInStartedAt = 0;
		this.reasoningFadeOutStartedAt = 0;
		this.reasoningHideDelayTimer = 0;
		this.reasoningFadeOutTimer = 0;

	}

	// ========================================
	// Reasoning visibility and timers
	// ========================================

	reset() {
		this.reasoningThinking = false;
		this.reasoningVisible = false;
		this.reasoningHasResponseText = false;
		this.reasoningFadeInStartedAt = 0;
		this.reasoningFadeOutStartedAt = 0;
		this.cancelReasoningTimers();
	}

	// Cancel pending reasoning hide/fade timers. A new thinking block always wins
	// over a previously scheduled hide from an earlier answer token.
	cancelReasoningTimers() {
		try {
			if (this.reasoningHideDelayTimer) clearTimeout(this.reasoningHideDelayTimer);
			if (this.reasoningFadeOutTimer) clearTimeout(this.reasoningFadeOutTimer);
		} catch (_) {}
		this.reasoningHideDelayTimer = 0;
		this.reasoningFadeOutTimer = 0;
	}

	// Track provider <think> boundaries and detect *actual answer text* outside
	// those tags. Closing </think> alone is not enough to hide the block: the
	// delay starts only when the first non-whitespace response token arrives.
	updateReasoningVisibilityFromChunk(chunk) {
		const s = String(chunk || '');
		if (!s) return { changed: false, hasResponseText: false };

		const beforeThinking = !!this.reasoningThinking;
		let thinking = beforeThinking;
		let hasResponseText = false;
		let pos = 0;

		while (pos < s.length) {
			const openAt = s.indexOf('<think>', pos);
			const closeAt = s.indexOf('</think>', pos);
			let nextAt = -1;
			let isOpen = false;

			if (openAt !== -1 && (closeAt === -1 || openAt < closeAt)) {
				nextAt = openAt;
				isOpen = true;
			} else if (closeAt !== -1) {
				nextAt = closeAt;
			}

			if (nextAt === -1) {
				if (!thinking && s.slice(pos).trim() !== '') hasResponseText = true;
				break;
			}

			if (!thinking && s.slice(pos, nextAt).trim() !== '') hasResponseText = true;
			if (isOpen) {
				thinking = true;
				pos = nextAt + 7;
			} else {
				thinking = false;
				pos = nextAt + 8;
			}
		}

		this.reasoningThinking = thinking;
		if (hasResponseText) this.reasoningHasResponseText = true;

		// New thinking immediately cancels a pending hide and makes only the latest
		// reasoning block visible. The first block gets a fade-in; a block that starts
		// during the grace period simply stays visible without flashing.
		if (!beforeThinking && thinking) {
			this.cancelReasoningTimers();
			this.reasoningFadeOutStartedAt = 0;
			if (this.reasoningEnabled) {
				const now = (typeof performance !== 'undefined' && typeof performance.now === 'function')
					? performance.now() : Date.now();
				if (!this.reasoningVisible) this.reasoningFadeInStartedAt = now;
				this.reasoningVisible = true;
			} else {
				this.reasoningVisible = false;
			}
		}

		return {
			changed: beforeThinking !== thinking,
			hasResponseText: hasResponseText
		};
	}

	// Start hiding the current reasoning block after the configured grace period.
	// Repeated answer tokens do not restart the delay. If thinking resumes first,
	// _updateReasoningVisibilityFromChunk() cancels both timers. rootOverride lets
	// non-text events (for example a tool call) target the current workflow host.
	scheduleReasoningHide(msg, rootOverride = null) {
		if (!this.reasoningEnabled || !this.reasoningHideAfterResponse || !this.reasoningVisible || this.reasoningThinking) return;
		if (this.reasoningHideDelayTimer || this.reasoningFadeOutTimer || this.reasoningFadeOutStartedAt > 0) return;

		const getRoot = () => rootOverride || this.engine.snapshots.getMsgSnapshotRoot(msg);
		const startFade = () => {
			this.reasoningHideDelayTimer = 0;
			if (this.reasoningThinking || !this.reasoningVisible) return;

			const duration = Math.max(0, Number(this.reasoningFadeDuration) || 0);
			this.reasoningVisible = false;
			this.reasoningFadeInStartedAt = 0;
			this.reasoningFadeOutStartedAt = (typeof performance !== 'undefined' && typeof performance.now === 'function')
				? performance.now() : Date.now();

			this.syncReasoningVisibility(getRoot());

			if (duration <= 0) {
				this.reasoningFadeOutStartedAt = 0;
				this.syncReasoningVisibility(getRoot());
				return;
			}

			this.reasoningFadeOutTimer = setTimeout(() => {
				this.reasoningFadeOutTimer = 0;
				if (this.reasoningThinking) return;
				this.reasoningFadeOutStartedAt = 0;
				this.syncReasoningVisibility(getRoot());
			}, duration + 24);
		};

		const delay = Math.max(0, Number(this.reasoningFadeOutDelay) || 0);
		if (delay <= 0) startFade();
		else this.reasoningHideDelayTimer = setTimeout(startFade, delay);
	}

	// A tool call is also an output boundary. Providers may finish reasoning and
	// immediately request a tool without emitting any normal assistant text, so
	// treat the tool call like the first response token for reasoning auto-hide.
	hideReasoningForToolCall(root = null) {
		if (!this.reasoningEnabled || !this.reasoningHideAfterResponse || !this.reasoningVisible) return;

		// A tool call ends the current reasoning phase even when the provider did
		// not emit an explicit closing </think> token before the call. This also
		// allows a later <think> block to become visible normally.
		this.reasoningThinking = false;

		const msg = this.engine.getMsg(false, '');
		if (!msg && !root) return;
		this.scheduleReasoningHide(msg, root);
	}

	// Apply the current live-reasoning state to rendered <think> nodes. The newest
	// block is the only one eligible for display. A disabled setting is a hard UI
	// switch; Python also avoids requesting/persisting readable provider reasoning.
	// Showing still uses a subtle fade-in, while hiding uses a real layout slide-up
	// (height -> 0), so the answer below moves upward together with the reasoning.
	syncReasoningVisibility(root) {
		try {
			if (!root || typeof root.querySelectorAll !== 'function') return;
			const nodes = root.querySelectorAll('think');
			if (!nodes || !nodes.length) return;

			if (!this.reasoningEnabled) {
				for (const el of nodes) {
					if (!el || !el.style) continue;
					if (el.dataset) el.dataset.streamReasoningHidden = '1';
					el.style.removeProperty('height');
					el.style.removeProperty('overflow');
					el.style.removeProperty('transition');
					el.style.setProperty('opacity', '0');
					el.style.setProperty('display', 'none', 'important');
				}
				return;
			}

			const now = (typeof performance !== 'undefined' && typeof performance.now === 'function')
				? performance.now() : Date.now();
			const duration = Math.max(0, Number(this.reasoningFadeDuration) || 0);
			const activeIndex = this.reasoningVisible ? (nodes.length - 1) : -1;
			const latestIndex = nodes.length - 1;
			const hideElapsed = this.reasoningFadeOutStartedAt > 0
				? Math.max(0, now - this.reasoningFadeOutStartedAt) : duration;
			const slideUpActive = duration > 0 && !this.reasoningVisible
				&& this.reasoningFadeOutStartedAt > 0 && hideElapsed < duration;

			for (let i = 0; i < nodes.length; i++) {
				const el = nodes[i];
				if (!el || !el.style) continue;

				if (i === activeIndex) {
					if (el.dataset) {
						delete el.dataset.streamReasoningHidden;
						delete el.dataset.streamReasoningSliding;
					}
					el.style.removeProperty('display');
					el.style.removeProperty('height');
					el.style.removeProperty('overflow');

					const elapsed = this.reasoningFadeInStartedAt > 0
						? Math.max(0, now - this.reasoningFadeInStartedAt) : duration;
					if (duration > 0 && elapsed < duration) {
						const remaining = Math.max(1, duration - elapsed);
						const opacity = Math.min(1, Math.max(0, elapsed / duration));
						el.style.setProperty('opacity', String(opacity));
						el.style.setProperty('transition', `opacity ${remaining}ms ease`);
						requestAnimationFrame(() => {
							try {
								if (this.reasoningVisible && el.isConnected) el.style.setProperty('opacity', '1');
							} catch (_) {}
						});
					} else {
						el.style.setProperty('opacity', '1');
						el.style.removeProperty('transition');
					}
				} else if (i === latestIndex && slideUpActive) {
					if (el.dataset) el.dataset.streamReasoningHidden = 'sliding';
					el.style.removeProperty('display');
					el.style.setProperty('opacity', '1');

					// Start the slide only once. Snapshot patches keep THINK nodes stable, so
					// subsequent response tokens do not restart the transition.
					if (!el.dataset || el.dataset.streamReasoningSliding !== '1') {
						const remaining = Math.max(1, duration - hideElapsed);
						let height = 0;
						try {
							height = Math.max(0, el.getBoundingClientRect().height || el.scrollHeight || 0);
						} catch (_) {}
						if (el.dataset) el.dataset.streamReasoningSliding = '1';
						el.style.setProperty('overflow', 'hidden');
						el.style.setProperty('height', `${height}px`);
						el.style.setProperty('transition', 'none');
						// Force the explicit start height to be committed before collapsing.
						void el.offsetHeight;
						requestAnimationFrame(() => {
							try {
								if (this.reasoningVisible || !el.isConnected) return;
								el.style.setProperty('transition', `height ${remaining}ms ease`);
								el.style.setProperty('height', '0px');
							} catch (_) {}
						});
					}
				} else {
					if (el.dataset) {
						el.dataset.streamReasoningHidden = '1';
						delete el.dataset.streamReasoningSliding;
					}
					el.style.removeProperty('height');
					el.style.removeProperty('overflow');
					el.style.removeProperty('transition');
					el.style.setProperty('opacity', '0');
					el.style.setProperty('display', 'none', 'important');
				}
			}
		} catch (_) {}
	}

}
