// CustomMarkupSource owns source behavior and state.
class CustomMarkupSource {

	// ========================================
	// Composition
	// ========================================

	constructor(markup) {
		this.markup = markup;
	}

	// ========================================
	// Source
	// ========================================

    // Transform source text by applying source-phase rules outside fenced code blocks
	transformSource(src, opts) {
		let s = String(src || '');
		this.markup.ensureCompiled();
		const rules = this.markup.compiledRules;
		if (!rules || !rules.length) return s;

		const candidates = [];
		for (let i = 0; i < rules.length; i++) {
			const r = rules[i];
			if (!r) continue;
			if ((r.phase === 'source' || r.phase === 'both') && (r.openReplace || r.closeReplace)) candidates.push(r);
		}
		if (!candidates.length) return s;

		const fences = this._findFenceRanges(s);
		let result = '';
		if (!fences.length) {
			result = this._applySourceReplacementsInChunk(s, s, 0, candidates);
		} else {
			let out = '', last = 0;
			for (let k = 0; k < fences.length; k++) {
				const [a, b] = fences[k];
				if (a > last) {
					const chunk = s.slice(last, a);
					out += this._applySourceReplacementsInChunk(s, chunk, last, candidates);
				}
				out += s.slice(a, b);
				last = b;
			}
			if (last < s.length) {
				const tail = s.slice(last);
				out += this._applySourceReplacementsInChunk(s, tail, last, candidates);
			}
			result = out;
		}

		if (opts && opts.streaming === true) {
			const fenceRules = candidates.filter(r => !!r.isSourceFence);
			if (fenceRules.length) result = this._injectUnmatchedSourceOpeners(result, fenceRules);
		}

		if (result !== src) this.markup.debug('cm.transformSource', { streaming: !!(opts && opts.streaming), delta: result.length - String(src || '').length });
		return result;
	}

	// ========================================
	// Source internals
	// ========================================

    // Find all fenced code block ranges in source text
	_findFenceRanges(s) {
		const ranges = [];
		const n = s.length;
		let i = 0;
		let inFence = false;
		let fenceMark = '';
		let fenceLen = 0;
		let startLineStart = 0;

		while (i < n) {
			const lineStart = i;
			let j = lineStart;
			while (j < n && s.charCodeAt(j) !== 10 && s.charCodeAt(j) !== 13) j++;
			const lineEnd = j;
			let nl = 0;
			if (j < n) {
				if (s.charCodeAt(j) === 13 && j + 1 < n && s.charCodeAt(j + 1) === 10) nl = 2;
				else nl = 1;
			}

			let k = lineStart;
			let indent = 0;
			while (k < lineEnd) {
				const c = s.charCodeAt(k);
				if (c === 32) {
					indent++;
					if (indent > 3) break;
					k++;
				} else if (c === 9) {
					indent++;
					if (indent > 3) break;
					k++;
				} else break;
			}

			if (!inFence) {
				if (indent <= 3 && k < lineEnd) {
					const ch = s.charCodeAt(k);
					if (ch === 0x60 || ch === 0x7E) {
						const mark = String.fromCharCode(ch);
						let m = k;
						while (m < lineEnd && s.charCodeAt(m) === ch) m++;
						const run = m - k;
						if (run >= 3) {
							inFence = true;
							fenceMark = mark;
							fenceLen = run;
							startLineStart = lineStart;
						}
					}
				}
			} else {
				if (indent <= 3 && k < lineEnd && s.charCodeAt(k) === fenceMark.charCodeAt(0)) {
					let m = k;
					while (m < lineEnd && s.charCodeAt(m) === fenceMark.charCodeAt(0)) m++;
					const run = m - k;
					if (run >= fenceLen) {
						let onlyWS = true;
						for (let t = m; t < lineEnd; t++) {
							const cc = s.charCodeAt(t);
							if (cc !== 32 && cc !== 9) { onlyWS = false; break; }
						}
						if (onlyWS) {
							const endIdx = lineEnd + nl;
							ranges.push([startLineStart, endIdx]);
							inFence = false;
							fenceMark = '';
							fenceLen = 0;
							startLineStart = 0;
						}
					}
				}
			}
			i = lineEnd + nl;
		}
		if (inFence) ranges.push([startLineStart, n]);
		return ranges;
	}

    // Check if a given absolute index in source text is at top-level line (not indented >3, not in list/quote)
	_isTopLevelLineInSource(s, absIdx) {
		let ls = absIdx;
		while (ls > 0) {
			const ch = s.charCodeAt(ls - 1);
			if (ch === 10 || ch === 13) break;
			ls--;
		}
		const prefix = s.slice(ls, absIdx);
		let i = 0, indent = 0;
		while (i < prefix.length) {
			const c = prefix.charCodeAt(i);
			if (c === 32) { indent++; if (indent > 3) break; i++; }
			else if (c === 9) { indent++; if (indent > 3) break; i++; }
			else break;
		}
		if (indent > 3) return false;
		const rest = prefix.slice(i);
		if (/^>\s?/.test(rest)) return false;
		if (/^[-+*]\s/.test(rest)) return false;
		if (/^\d+[.)]\s/.test(rest)) return false;
		if (rest.trim().length > 0) return false;
		return true;
	}

    // Apply source replacements in a given chunk of text, checking line starts against full text
	_applySourceReplacementsInChunk(full, chunk, baseOffset, rules) {
		let t = chunk;
		for (let i = 0; i < rules.length; i++) {
			const r = rules[i];
			if (!r || !(r.openReplace || r.closeReplace)) continue;
			try {
				r.re.lastIndex = 0;
				t = t.replace(r.re, (match, inner, offset) => {
					const abs = baseOffset + (offset | 0);
					if (!this._isTopLevelLineInSource(full, abs)) return match;
					const open = r.openReplace || '';
					const close = r.closeReplace || '';
					return open + (inner || '') + close;
				});
			} catch (_) {}
		}
		return t;
	}

    // In streaming mode, if there is any unmatched opener at the end of the text,
	_injectUnmatchedSourceOpeners(text, fenceRules) {
		let s = String(text || '');
		if (!s || !fenceRules || !fenceRules.length) return s;

		let best = null; // { r, idx }
		for (let i = 0; i < fenceRules.length; i++) {
			const r = fenceRules[i];
			if (!r || !r.open || !r.close || !r.openReplace) continue;

			const idx = s.lastIndexOf(r.open);
			if (idx === -1) continue;

			if (!this._isTopLevelLineInSource(s, idx)) continue;

			const after = s.indexOf(r.close, idx + r.open.length);
			if (after !== -1) continue;

			if (!best || idx > best.idx) best = { r, idx };
		}

		if (!best) return s;

		const r = best.r, i = best.idx;
		const before = s.slice(0, i);
		const after = s.slice(i + r.open.length);
		const injected = String(r.openReplace || '');
		this.markup.debug('cm.inject.open', { name: r.name });
		return before + injected + after;
	}

}
