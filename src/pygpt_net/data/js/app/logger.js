// ==========================================================================
// Logger (bridge-based; injected into classes)
// ==========================================================================

class Logger {

	// logger with queue, batch sending and soft caps.
	constructor(cfg) {
		this.cfg = cfg || {
			LOG: {}
		};
		// Queue holds strings waiting to be sent over QWebChannel to Python.
		this.queue = [];
		this.queueBytes = 0; // approximate UTF-16 bytes (chars * 2)
		this.armed = false;
		this.maxTries = 480; // ~8s @60fps
		this.tries = 0;
		this.bridge = null;
		this._idleId = 0; // idle-callback handle (backoff-friendly)
		this._lastFlushQueueBytes = 0; // last known bytes to detect progress

		// Centralized rAF manager handle (bound by runtime); falls back to microtasks until available.
		this.raf = null;
		this._rafScheduled = false;
		this._rafKey = {
			t: 'Logger:tick'
		};

		// Soft limits; tunable from window.* if desired.
		const L = this.cfg.LOG || {};
		this.MAX_QUEUE = Utils.g('LOG_MAX_QUEUE', L.MAX_QUEUE ?? 400);
		this.MAX_BYTES = Utils.g('LOG_MAX_BYTES', L.MAX_BYTES ?? 256 * 1024); // 256 KiB
		this.BATCH_MAX = Utils.g('LOG_BATCH_MAX', L.BATCH_MAX ?? 64);
		this.RATE_LIMIT_PER_SEC = Utils.g('LOG_RATE_LIMIT_PER_SEC', L.RATE_LIMIT_PER_SEC ?? 0); // 0 == off
		this._rlWindowMs = 1000;
		this._rlCount = 0;
		this._rlWindowStart = Utils.now();
	}

	// Connect a QWebChannel bridge and flush any pending messages.
	bindBridge(bridge) {
		this.bridge = bridge || null;
		// When bridge arrives, flush pending messages respecting caps.
		this.flush();
	}

	// Bind RafManager instance – ensures no direct requestAnimationFrame usage in Logger.
	bindRaf(raf) {
		this.raf = raf || null;
	}

	// Check if debug logging is enabled for a namespace.
	isEnabled(ns) {
		if (!ns) return !!(window.STREAM_DEBUG || window.MD_LANG_DEBUG);
		const key1 = ns + '_DEBUG';
		const key2 = ns.toUpperCase() + '_DEBUG';
		return !!(window[key1] || window[key2] || window.STREAM_DEBUG || window.MD_LANG_DEBUG);
	}

	// Pretty-view string (safe truncation for logs).
	pv(s, n = 120) {
		if (!s) return '';
		s = String(s);
		if (s.length <= n) return s.replace(/\n/g, '\\n');
		const k = Math.floor(n / 2);
		return (s.slice(0, k) + ' … ' + s.slice(-k)).replace(/\n/g, '\\n');
	}

	// Serializes an object to JSON.
	j(o) {
		try {
			return JSON.stringify(o);
		} catch (_) {
			try {
				return String(o);
			} catch (__) {
				return '[unserializable]';
			}
		}
	}

	// Emits a log message.
	_emit(msg) {
		// Attempt batch-capable sink if provided by the bridge
		try {
			if (this.bridge) {
				if (typeof this.bridge.log_batch === 'function') {
					this.bridge.log_batch([String(msg)]);
					return true;
				}
				if (typeof this.bridge.logBatch === 'function') {
					this.bridge.logBatch([String(msg)]);
					return true;
				}
				if (typeof this.bridge.log === 'function') {
					this.bridge.log(String(msg));
					return true;
				}
			}
			if (window.runtime && runtime.bridge && typeof runtime.bridge.log === 'function') {
				runtime.bridge.log(String(msg));
				return true;
			}
		} catch (_) {}
		return false;
	}

	// Emits a batch of log messages.
	_emitBatch(arr) {
		try {
			if (!arr || !arr.length) return 0;
			// Prefer batch API if present; otherwise fallback to per-line
			if (this.bridge && typeof this.bridge.log_batch === 'function') {
				this.bridge.log_batch(arr.map(String));
				return arr.length;
			}
			if (this.bridge && typeof this.bridge.logBatch === 'function') {
				this.bridge.logBatch(arr.map(String));
				return arr.length;
			}
			if (this.bridge && typeof this.bridge.log === 'function') {
				for (let i = 0; i < arr.length; i++) this.bridge.log(String(arr[i]));
				return arr.length;
			}
		} catch (_) {}
		return 0;
	}

	// Maybe drop logs for caps.
	_maybeDropForCaps(len) {
		// Hard cap queue size and memory to guard Python process via QWebChannel.
		if (this.queue.length <= this.MAX_QUEUE && this.queueBytes <= this.MAX_BYTES) return;
		const targetLen = Math.floor(this.MAX_QUEUE * 0.8);
		const targetBytes = Math.floor(this.MAX_BYTES * 0.8);
		// Drop oldest first; keep newest events
		while ((this.queue.length > targetLen || this.queueBytes > targetBytes) && this.queue.length) {
			const removed = this.queue.shift();
			this.queueBytes -= (removed ? removed.length * 2 : 0);
		}
		// Add one synthetic notice to indicate dropped logs (avoid recursion)
		const notice = '[LOGGER] queue trimmed due to caps';
		this.queue.unshift(notice);
		this.queueBytes += notice.length * 2;
	}

	// Checks if the logger is within the rate limit.
	_passRateLimit() {
		if (!this.RATE_LIMIT_PER_SEC || this.RATE_LIMIT_PER_SEC <= 0) return true;
		const now = Utils.now();
		if (now - this._rlWindowStart > this._rlWindowMs) {
			this._rlWindowStart = now;
			this._rlCount = 0;
		}
		if (this._rlCount >= this.RATE_LIMIT_PER_SEC) return false;
		return true;
	}

	// Push a log line; try immediate send, otherwise enqueue.
	log(text) {
		const msg = String(text);
		// If bridge is available, try immediate emit to avoid queueing overhead.
		if (this.bridge && (typeof this.bridge.log === 'function' || typeof this.bridge.log_batch === 'function' || typeof this.bridge.logBatch === 'function')) {
			if (this._passRateLimit()) {
				const ok = this._emit(msg);
				if (ok) return true;
			}
		}
		// Enqueue with caps; avoid unbounded growth
		this.queue.push(msg);
		this.queueBytes += msg.length * 2;
		this._maybeDropForCaps(msg.length);
		this._arm();
		return false;
	}

	// Debug wrapper respecting per-namespace switch.
	debug(ns, line, ctx) {
		if (!this.isEnabled(ns)) return false;
		let msg = `[${ns}] ${line || ''}`;
		if (typeof ctx !== 'undefined') msg += ' ' + this.j(ctx);
		return this.log(msg);
	}

    // Debug an object with safe serialization.
	debug_obj(ns, tag, data) {
        try {
            const lg = this.logger || (this.cfg && this.cfg.logger) || (window.runtime && runtime.logger) || null;
            if (!this.isEnabled(ns)) return false;
            const safeJson = (v) => {
                try {
                    const seen = new WeakSet();
                    const s = JSON.stringify(v, (k, val) => {
                        if (typeof val === 'object' && val !== null) {
                            if (val.nodeType) {
                                const nm = (val.nodeName || val.tagName || 'DOM').toString();
                                return `[DOM ${nm}]`;
                            }
                            if (seen.has(val)) return '[Circular]';
                            seen.add(val);
                        }
                        if (typeof val === 'string' && val.length > 800) return val.slice(0, 800) + '…';
                        return val;
                    });
                    return s;
                } catch (_) {
                    try { return String(v); } catch { return ''; }
                }
            };

            let line = String(tag || '');
            if (typeof data !== 'undefined') {
                const payload = safeJson(data);
                if (payload && payload !== '""') line += ' ' + payload;
            }
            this.debug(ns, line);
        } catch (_) {}
    }

	// Send a batch of lines if bridge is ready.
	flush(maxPerTick = this.BATCH_MAX) {
		// Centralized flush – no direct cancelAnimationFrame here; RafManager governs frames.
		if (!this.bridge && !(window.runtime && runtime.bridge && typeof runtime.bridge.log === 'function')) return 0;
		const n = Math.min(maxPerTick, this.queue.length);
		if (!n) return 0;
		const batch = this.queue.splice(0, n);
		// Update memory accounting before attempting emit to eagerly unlock memory
		let bytes = 0;
		for (let i = 0; i < batch.length; i++) bytes += batch[i].length * 2;
		this.queueBytes = Math.max(0, this.queueBytes - bytes);
		const sent = this._emitBatch(batch);

		// fix byte accounting for partial sends (re-queue remaining with accurate bytes).
		if (sent < batch.length) {
			const remain = batch.slice(sent);
			let remBytes = 0;
			for (let i = 0; i < remain.length; i++) remBytes += remain[i].length * 2;
			// Prepend remaining back to the queue preserving order
			for (let i = remain.length - 1; i >= 0; i--) this.queue.unshift(remain[i]);
			this.queueBytes += remBytes;
		}
		return sent;
	}

	// Schedules a tick for log flushing.
	_scheduleTick(tick) {
		// Prefer idle scheduling when bridge isn't available yet – avoids 60fps RAF churn.
		const preferIdle = !this.bridge;

		const scheduleIdle = () => {
			try {
				if (this._idleId) Utils.cancelIdle(this._idleId);
			} catch (_) {}
			// Use requestIdleCallback when available, fallback to small timeout. Keeps UI cold on idle.
			this._idleId = Utils.idle(() => {
				this._idleId = 0;
				tick();
			}, 800);
		};

		if (preferIdle) {
			scheduleIdle();
			return;
		}

		if (this._rafScheduled) return;
		this._rafScheduled = true;
		const run = () => {
			this._rafScheduled = false;
			tick();
		};
		try {
			if (this.raf && typeof this.raf.schedule === 'function') {
				this.raf.schedule(this._rafKey, run, 'Logger', 3);
			} else if (typeof runtime !== 'undefined' && runtime.raf && typeof runtime.raf.schedule === 'function') {
				runtime.raf.schedule(this._rafKey, run, 'Logger', 3);
			} else {
				Promise.resolve().then(run);
			}
		} catch (_) {
			Promise.resolve().then(run);
		}
	}

	// Arms the logger for flushing.
	_arm() {
		if (this.armed) return;
		this.armed = true;
		this.tries = 0;
		const tick = () => {
			if (!this.armed) return;
			this.flush();
			this.tries++;
			if (this.queue.length === 0 || this.tries > this.maxTries) {
				this.armed = false;
				try {
					if (this._idleId) Utils.cancelIdle(this._idleId);
				} catch (_) {}
				this._idleId = 0;
				return;
			}
			this._scheduleTick(tick);
		};
		this._scheduleTick(tick);
	}
}