// StreamFences owns fences behavior and state.
class StreamFences {

	// ========================================
	// Composition
	// ========================================

	constructor(engine) {
		this.engine = engine;
		this.fenceOpen = false;
		this.fenceMark = '`';
		this.fenceLen = 3;
		this.fenceTail = '';
		this.fenceBuf = '';
		this._customFenceSpecs = [];
		this._fenceCustom = null;

	}

	// ========================================
	// Fence parsing
	// ========================================

	reset() {
		this.fenceOpen = false;
		this.fenceMark = '`';
		this.fenceLen = 3;
		this.fenceTail = '';
		this.fenceBuf = '';
		this._fenceCustom = null;
	}

	// Register custom fence (code block) open/close tokens.
	setCustomFenceSpecs(specs) {
		// Keep a shallow copy to avoid external mutation.
		this._customFenceSpecs = Array.isArray(specs) ? specs.slice() : [];
		// DEBUG
		this.engine.debug('customFence.set', {
			count: (this._customFenceSpecs || []).length
		});
	}

	// Utility: check if range s[from..end) has only spaces/tabs.
	onlyTrailingWhitespace(s, from, end) {
		for (let i = from; i < end; i++) {
			const c = s.charCodeAt(i);
			if (c !== 0x20 && c !== 0x09) return false;
		}
		return true;
	}

	// Update fence (code block) state based on a new chunk; returns open/close info and split point.
	updateFenceHeuristic(chunk) {
		// Combine previous tail buffer with new chunk to scan across boundaries.
		const prev = (this.fenceBuf || '');
		const s = prev + (chunk || '');
		const preLen = prev.length;
		const n = s.length;
		let i = 0;
		let opened = false;
		let closed = false;
		let splitAt = -1;
		let atLineStart = (preLen === 0) ? true : this.engine._reLineEnd.test(prev);

		// Helper: whether token starts in new chunk or crosses boundary.
		const inNewOrCrosses = (j, k) => (j >= preLen) || (k > preLen);

		// Scan line by line, looking for fence openers/closers.
		while (i < n) {
			const ch = s[i];
			if (ch === '\r' || ch === '\n') {
				atLineStart = true;
				i++;
				continue;
			}
			if (!atLineStart) {
				i++;
				continue;
			}
			atLineStart = false;

			// Trim list/quote markers at start so we can detect fences after them.
			let j = i;
			while (j < n) {
				let localSpaces = 0;
				while (j < n && (s[j] === ' ' || s[j] === '\t')) {
					localSpaces += (s[j] === '\t') ? 4 : 1;
					j++;
					if (localSpaces > 3) break;
				}
				if (j < n && s[j] === '>') {
					j++;
					if (j < n && s[j] === ' ') j++;
					continue;
				}

				let saved = j;
				if (j < n && (s[j] === '-' || s[j] === '*' || s[j] === '+')) {
					let jj = j + 1;
					if (jj < n && s[jj] === ' ') j = jj + 1;
					else j = saved;
				} else {
					let k2 = j;
					let hasDigit = false;
					while (k2 < n && s[k2] >= '0' && s[k2] <= '9') {
						hasDigit = true;
						k2++;
					}
					if (hasDigit && k2 < n && (s[k2] === '.' || s[k2] === ')')) {
						k2++;
						if (k2 < n && s[k2] === ' ') j = k2 + 1;
						else j = saved;
					} else j = saved;
				}
				break;
			}

			// Respect indentation rules for fenced code (ignore deeply indented).
			let indent = 0;
			while (j < n && (s[j] === ' ' || s[j] === '\t')) {
				indent += (s[j] === '\t') ? 4 : 1;
				j++;
				if (indent > 3) break;
			}
			if (indent > 3) {
				i = j;
				continue;
			}

			// 1) Custom fences
			if (!this.fenceOpen && this._customFenceSpecs && this._customFenceSpecs.length) {
				for (let ci = 0; ci < this._customFenceSpecs.length; ci++) {
					const spec = this._customFenceSpecs[ci];
					const open = spec && spec.open ? spec.open : '';
					if (!open) continue;
					const k = j + open.length;
					if (k <= n && s.slice(j, k) === open) {
						if (inNewOrCrosses(j, k)) {
							// Open a custom fence.
							this.fenceOpen = true;
							this._fenceCustom = spec;
							opened = true;
							// DEBUG
							this.engine.debug('fence.open.custom', {
								open,
								at: j
							});
							i = k;
							continue;
						}
					}
				}
			} else if (this.fenceOpen && this._fenceCustom && this._fenceCustom.close) {
				const close = this._fenceCustom.close;
				const k = j + close.length;
				if (k <= n && s.slice(j, k) === close) {
					// Check that only whitespace follows on this line.
					let eol = k;
					while (eol < n && s[eol] !== '\n' && s[eol] !== '\r') eol++;
					const onlyWS = this.onlyTrailingWhitespace(s, k, eol);
					if (onlyWS && inNewOrCrosses(j, k)) {
						// Close custom fence and compute split position inside the current chunk.
						this.fenceOpen = false;
						this._fenceCustom = null;
						closed = true;
						const endInS = k;
						const rel = endInS - preLen;
						const splitAt = Math.max(0, Math.min((chunk ? chunk.length : 0), rel));
						// DEBUG
						this.engine.debug('fence.close.custom', {
							close,
							splitAt
						});
						return {
							opened,
							closed,
							splitAt
						};
					}
				}
			}

			// 2) Standard fences (``` or ~~~)
			if (j < n && (s[j] === '`' || s[j] === '~')) {
				const mark = s[j];
				let k = j;
				while (k < n && s[k] === mark) k++;
				const run = k - j;

				if (!this.fenceOpen) {
					if (run >= 3) {
						if (inNewOrCrosses(j, k)) {
							// Open standard fence
							this.fenceOpen = true;
							this.fenceMark = mark;
							this.fenceLen = run;
							opened = true;
							// DEBUG
							this.engine.debug('fence.open.std', {
								mark,
								run
							});
							i = k;
							continue;
						} else {
							i = k;
							continue;
						}
					}
				} else if (!this._fenceCustom) {
					if (mark === this.fenceMark && run >= this.fenceLen) {
						if (inNewOrCrosses(j, k)) {
							// Only close fence if rest of line is whitespace.
							let eol = k;
							while (eol < n && s[eol] !== '\n' && s[eol] !== '\r') eol++;
							if (this.onlyTrailingWhitespace(s, k, eol)) {
								this.fenceOpen = false;
								closed = true;
								const endInS = k;
								const rel = endInS - preLen;
								const splitAt = Math.max(0, Math.min((chunk ? chunk.length : 0), rel));
								// DEBUG
								this.engine.debug('fence.close.std', {
									mark,
									run,
									splitAt
								});
								return {
									opened,
									closed,
									splitAt
								};
							}
						} else {
							i = k;
							continue;
						}
					}
				}
			}

			// Move to next char after we tried all checks at this line start.
			i = j + 1;
		}

		// Keep a small tail so next chunk can be checked across boundary.
		const MAX_TAIL = 512;
		this.fenceBuf = s.slice(-MAX_TAIL);
		this.fenceTail = s.slice(-3);
		// DEBUG
		if (opened || closed) this.engine.debug('fence.state', {
			opened,
			closed,
			fenceTail: this.fenceTail
		});
		return {
			opened,
			closed,
			splitAt: -1
		};
	}

}
