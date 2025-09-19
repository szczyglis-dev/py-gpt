// ==========================================================================
// Stream queue
// ==========================================================================

// StreamQueue batches and drains incoming chunks to the engine efficiently.
class StreamQueue {

	// Constructor: set up queue, pacing parameters, and raf handle.
	constructor(cfg, engine, scrollMgr, raf) {
		this.cfg = cfg;
		this.engine = engine;
		this.scrollMgr = scrollMgr;
		this.raf = raf;

		// Internal queue and read pointer.
		this.q = [];
		this.rd = 0;

		// State flags for draining and UI scrolling.
		this.drainScheduled = false;
		this.batching = false;
		this.needScroll = false;

		// Stable key for scheduling drain tasks.
		this.DRAIN_KEY = Symbol('SQ:drain');

		// Timing and coalescing knobs.
		const R = (this.cfg && this.cfg.RAF) || {};
		this.DRAIN_BUDGET_MS = (R.STREAM_DRAIN_BUDGET_MS != null) ? R.STREAM_DRAIN_BUDGET_MS : 4;
		this.COMPACT_SLICE_THRESHOLD = 1024;

		this._lastCompactRd = 0;
	}

	// Return number of pending entries not yet processed.
	_qCount() {
		return Math.max(0, this.q.length - this.rd);
	}

	// Compact adjacent queue entries with the same name by concatenating parts.
	_compactContiguousSameName() {
		const n = this._qCount();
		if (n < 2) return;

		const out = [];
		let prev = null;

		for (let i = this.rd; i < this.q.length; i++) {
			const cur = this.q[i];
			if (!cur) continue;

			if (prev && prev.name === cur.name) {
				// Merge current parts into previous bucket.
				if (cur.parts && cur.parts.length) {
					for (let k = 0; k < cur.parts.length; k++) prev.parts.push(cur.parts[k]);
				} else if (cur.chunk) {
					prev.parts.push(cur.chunk);
				}
				prev.len += (cur.len | 0);

				// Clear merged node.
				if (cur.parts) cur.parts.length = 0;
				cur.chunk = '';
				cur.len = 0;
				cur.name = '';

			} else {
				// Start a new bucket from this entry.
				// NOTE: move parts array instead of copying it to avoid duplicating references.
				const parts = cur.parts ? cur.parts : (cur.chunk ? [cur.chunk] : []);
				prev = {
					name: cur.name,
					parts: parts, // moved, not copied
					len: cur.len != null ? cur.len : (cur.chunk ? cur.chunk.length : 0)
				};
				out.push(prev);

				// Detach original node from its parts to help GC.
				if (cur.parts) cur.parts = [];
				cur.chunk = '';
				cur.len = 0;
				cur.name = '';
			}
		}

		// Replace queue with the compacted version and reset read pointer.
		this.q = out;
		this.rd = 0;
		this._lastCompactRd = 0;
	}

	// Maybe shrink the queue array by slicing off processed prefix.
	_maybeCompact() {
		if (this.rd === 0) return;
		const n = this._qCount();
		if (n === 0) {
			this.q = [];
			this.rd = 0;
			this._lastCompactRd = 0;
			return;
		}
		// If we advanced far, slice off processed items to keep arrays small.
		if (this.rd >= this.COMPACT_SLICE_THRESHOLD) {
			this.q = this.q.slice(this.rd);
			this.rd = 0;
			this._lastCompactRd = 0;
			return;
		}
		// Periodically compact when read pointer grows or passes half the queue.
		if (this.rd - this._lastCompactRd >= 128 || (this.rd > 64 && this.rd >= (this.q.length >> 1))) {
			this.q = this.q.slice(this.rd);
			this.rd = 0;
			this._lastCompactRd = 0;
		}
	}

	// Schedule a drain on RAF if not already scheduled.
	_scheduleDrain() {
		if (this.drainScheduled) return;
		this.drainScheduled = true;
		this.raf.schedule(this.DRAIN_KEY, () => this.drain(), 'StreamQueue', -5);
	}

	// Add a new chunk for a given stream "name" (header) to the queue.
	enqueue(name_header, chunk) {
		if (!chunk || chunk.length === 0) return;
		const name = name_header;

		// Coalesce with the last entry if it has the same name.
		const hasPending = this._qCount() > 0;
		const tail = hasPending ? this.q[this.q.length - 1] : null;

		if (tail && tail.name === name) {
			tail.parts.push(chunk);
			tail.len += chunk.length;
		} else {
			this.q.push({
				name,
				parts: [chunk],
				len: chunk.length
			});
		}

		// Apply emergency coalescing when queue grows too large.
		const cnt = this._qCount();
		if (cnt > (this.cfg.STREAM.EMERGENCY_COALESCE_LEN | 0)) this._compactContiguousSameName();
		else if (cnt > (this.cfg.STREAM.QUEUE_MAX_ITEMS | 0)) this._compactContiguousSameName();

		this._scheduleDrain();
	}

	// Process queued chunks within a time/amount budget and feed them to the engine.
	drain() {
		this.drainScheduled = false;

		// Adaptive mode increases per-frame quota when backlog grows.
		const adaptive = (this.cfg.STREAM.COALESCE_MODE === 'adaptive');
		const coalesceAggressive = adaptive && (this._qCount() >= (this.cfg.STREAM.EMERGENCY_COALESCE_LEN | 0));
		const basePerFrame = this.cfg.STREAM.MAX_PER_FRAME | 0;
		const perFrame = adaptive ?
			Math.min(basePerFrame + Math.floor(this._qCount() / 20), basePerFrame * 4) :
			basePerFrame;

		const start = Utils.now();
		// If available, use isInputPending to yield when user input is pending.
		const sched = (navigator && navigator.scheduling && navigator.scheduling.isInputPending) ? navigator.scheduling : null;

		this.batching = true;

		let processed = 0;
		while (this.rd < this.q.length && processed < perFrame) {
			const idx = this.rd++;
			const e = this.q[idx];
			if (!e) continue;

			// Aggressive in-while coalescing for same-name entries to cut overhead.
			if (coalesceAggressive) {
				while (this.rd < this.q.length && this.q[this.rd] && this.q[this.rd].name === e.name) {
					const n = this.q[this.rd++];
					if (n.parts && n.parts.length) {
						for (let k = 0; k < n.parts.length; k++) e.parts.push(n.parts[k]);
					} else if (n.chunk) {
						e.parts.push(n.chunk);
					}
					e.len += (n.len | 0);

					// Clear merged node to help GC.
					if (n.parts) n.parts.length = 0;
					n.chunk = '';
					n.len = 0;
					n.name = '';
					this.q[this.rd - 1] = null;
				}
			}

			// Join parts into a single payload string for the engine.
			let payload = '';
			if (!e.parts || e.parts.length === 0) payload = e.chunk || '';
			else if (e.parts.length === 1) payload = e.parts[0] || '';
			else payload = e.parts.join('');

			// Feed the engine (this may schedule snapshots).
			this.engine.applyStream(e.name, payload);
			processed++;

			// Clear consumed entry.
			if (e.parts) e.parts.length = 0;
			e.chunk = '';
			e.len = 0;
			e.name = '';
			this.q[idx] = null;
			payload = '';

			// Yield if user input is pending or if we exceeded the time budget.
			if (sched && sched.isInputPending({
					includeContinuous: true
				})) break;
			if ((Utils.now() - start) >= this.DRAIN_BUDGET_MS) break;
		}

		this.batching = false;

		// If a scroll was requested during batching, schedule it now.
		if (this.needScroll) {
			this.scrollMgr.scheduleScroll(true);
			this.needScroll = false;
		}

		// Keep the queue array compact.
		this._maybeCompact();

		// If there is more work, schedule another drain.
		if (this._qCount() > 0) this._scheduleDrain();
	}

	// Nudge the queue to keep draining (useful if external events pause RAF).
	kick() {
		if (this._qCount() || this.drainScheduled) this._scheduleDrain();
	}

	// Drop all queued entries and cancel scheduled tasks.
	clear() {
		for (let i = this.rd; i < this.q.length; i++) {
			const e = this.q[i];
			if (!e) continue;
			if (e.parts) e.parts.length = 0;
			e.chunk = '';
			e.len = 0;
			e.name = '';
			this.q[i] = null;
		}
		this.q = [];
		this.rd = 0;
		this._lastCompactRd = 0;
		try {
			this.raf.cancelGroup('StreamQueue');
		} catch (_) {}
		this.drainScheduled = false;
	}
}