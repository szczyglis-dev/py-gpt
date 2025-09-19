// ==========================================================================
// RafManager (rAF-only)
// ==========================================================================

class RafManager {

	// rAF-only task pump with soft budget per flush to prevent long frames.
	constructor(cfg) {
		this.cfg = cfg || {
			RAF: {},
			ASYNC: {}
		};
		this.tasks = new Map();
		this.groups = new Map();
		// rAF pump state
		this.tickId = 0;
		this._mode = 'raf';
		this.scheduled = false;
		this._flushInProgress = false;
		this._watchdogId = 0; // <-- init watchdog id
		this._weakKeyTokens = new WeakMap();

		const R = (this.cfg && this.cfg.RAF) || {};
		this.FLUSH_BUDGET_MS = Utils.g('RAF_FLUSH_BUDGET_MS', R.FLUSH_BUDGET_MS ?? 7);
		this.MAX_TASKS_PER_FLUSH = Utils.g('RAF_MAX_TASKS_PER_FLUSH', R.MAX_TASKS_PER_FLUSH ?? 120);
		this.SORT_THRESHOLD = Utils.g('RAF_SORT_THRESHOLD', R.SORT_THRESHOLD ?? 32);
		this.VISIBILITY_FALLBACK_MS = Utils.g('RAF_VISIBILITY_FALLBACK_MS', R.VISIBILITY_FALLBACK_MS ?? 300);
		this.USE_VISIBILITY_FALLBACK = (R.USE_VISIBILITY_FALLBACK ?? true);
	}

	// Normalize a key into a string/symbol/number/DOM token.
	_normalizeKey(key) {
		if (!key) return Symbol('raf:anon');
		const typ = typeof key;
		if (typ === 'string' || typ === 'symbol' || typ === 'number') return key;
		try {
			if (typeof Node !== 'undefined' && key instanceof Node) {
				let tok = this._weakKeyTokens.get(key);
				if (!tok) {
					tok = Symbol('raf:k');
					this._weakKeyTokens.set(key, tok);
				}
				return tok;
			}
		} catch (_) {}
		return key; // plain object key is ok
	}

	// Start the pumping loop if needed.
	_armPump() {
		if (this.scheduled) return;
		this.scheduled = true;

		const canRAF = typeof requestAnimationFrame === 'function';
		if (canRAF) {
			this._mode = 'raf';
			try {
				this.tickId = requestAnimationFrame(() => this.flush());
				if (this.USE_VISIBILITY_FALLBACK && !this._watchdogId) {
					this._watchdogId = setTimeout(() => {
						if (this.scheduled || this.tickId) {
							try {
								this.flush();
							} catch (_) {}
						}
					}, this.VISIBILITY_FALLBACK_MS);
				}
				return;
			} catch (_) {}
		}
		// Fallback without timers: schedule a microtask flush.
		this._mode = 'raf';
		Promise.resolve().then(() => this.flush());
	}

	// Schedule a function with an optional group and priority.
	schedule(key, fn, group = 'default', priority = 0) {
		if (!key) key = {
			k: 'anon'
		};
		key = this._normalizeKey(key);

		const prev = this.tasks.get(key);
		if (prev && prev.group && prev.group !== group) {
			const oldSet = this.groups.get(prev.group);
			if (oldSet) {
				oldSet.delete(key);
				if (oldSet.size === 0) this.groups.delete(prev.group);
			}
		}

		this.tasks.set(key, {
			fn,
			group,
			priority
		});

		if (group) {
			let set = this.groups.get(group);
			if (!set) {
				set = new Set();
				this.groups.set(group, set);
			}
			set.add(key);
		}
		this._armPump();
	}

	// Run pending tasks within a time and count budget.
	flush() {
		try {
			if (this.tickId) cancelAnimationFrame(this.tickId);
		} catch (_) {}
		this.tickId = 0;
		this.scheduled = false;
		if (this._watchdogId) {
			clearTimeout(this._watchdogId);
			this._watchdogId = 0;
		}

		// Snapshot + clear
		const list = [];
		this.tasks.forEach((v, key) => list.push({
			key,
			...v
		}));
		this.tasks.clear();

		if (list.length > 1 && list.length > this.SORT_THRESHOLD) {
			list.sort((a, b) => a.priority - b.priority);
		}

		const start = Utils.now();
		let processed = 0;

		for (let idx = 0; idx < list.length; idx++) {
			const t = list[idx];
			try {
				t.fn();
			} catch (_) {}
			processed++;

			if (t.group) {
				const set = this.groups.get(t.group);
				if (set) {
					set.delete(t.key);
					if (set.size === 0) this.groups.delete(t.group);
				}
			}

			const elapsed = Utils.now() - start;
			if (processed >= this.MAX_TASKS_PER_FLUSH || elapsed >= this.FLUSH_BUDGET_MS) {
				// requeue the rest
				for (let j = idx + 1; j < list.length; j++) {
					const r = list[j];
					this.tasks.set(r.key, {
						fn: r.fn,
						group: r.group,
						priority: r.priority
					});
					if (r.group) {
						let set = this.groups.get(r.group);
						if (!set) {
							set = new Set();
							this.groups.set(r.group, set);
						}
						set.add(r.key);
					}
				}
				this._armPump();
				return;
			}
		}

		if (this.tasks.size) this._armPump();
	}

	// Force immediate flush or schedule next frame.
	kick(forceImmediate = true) {
		if (forceImmediate && this.tasks.size) {
			if (this._flushInProgress) return;
			this._flushInProgress = true;
			try {
				this.scheduled = true;
				this.flush();
			} catch (_) {} finally {
				this._flushInProgress = false;
			}
			return;
		}
		this._armPump();
	}

	// Cancel a specific scheduled task by key.
	cancel(key) {
		key = this._normalizeKey(key);
		const t = this.tasks.get(key);
		if (!t) return;
		this.tasks.delete(key);
		if (t.group) {
			const set = this.groups.get(t.group);
			if (set) {
				set.delete(key);
				if (set.size === 0) this.groups.delete(t.group);
			}
		}
	}

	// Cancel all tasks in a group.
	cancelGroup(group) {
		const set = this.groups.get(group);
		if (!set) return;
		for (const key of set) this.tasks.delete(key);
		this.groups.delete(group);
	}

	// Cancel everything and reset the pump.
	cancelAll() {
		this.tasks.clear();
		this.groups.clear();
		try {
			if (this.tickId) cancelAnimationFrame(this.tickId);
		} catch (_) {}
		this.tickId = 0;
		this.scheduled = false;
		if (this._watchdogId) {
			clearTimeout(this._watchdogId);
			this._watchdogId = 0;
		}
	}

	// Checks if a task is scheduled.
	isScheduled(key) {
		return this.tasks.has(this._normalizeKey(key));
	}

	// Awaitable "next frame" helper – resolves on next flush.
	nextFrame() {
		return new Promise((resolve) => {
			const key = Symbol('raf:nextFrame');
			this.schedule(key, () => resolve(), 'RafNext', 0);
		});
	}
}

// Return math rendering policy from window.MATH_STREAM_MODE.
function getMathMode() {
	const v = String(window.MATH_STREAM_MODE || 'finalize-only').toLowerCase();
	return (v === 'idle' || v === 'always' || v === 'finalize-only') ? v : 'finalize-only';
}