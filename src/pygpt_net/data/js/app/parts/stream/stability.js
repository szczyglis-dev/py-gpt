// StreamStability owns snapshots behavior and state.
class StreamStability {

	// ========================================
	// Composition
	// ========================================

	constructor(engine) {
		this.engine = engine;
	}

	// ========================================
	// Stable code and snapshot reconciliation
	// ========================================

	// Normalize text for stable fingerprint: unify EOLs, drop single trailing newline, strip BOM.
	normTextForFP(s) {
		if (!s) return '';
		let t = String(s);
		if (t.charCodeAt(0) === 0xFEFF) t = t.slice(1);
		t = t.replace(/\r\n?/g, '\n');
		if (t.endsWith('\n')) t = t.slice(0, -1);
		return t;
	}

	// Lightweight FNV-1a 32-bit hash for short keys.
	hash32FNV(str) {
		let h = 0x811c9dc5 >>> 0;
		for (let i = 0; i < str.length; i++) {
			h ^= str.charCodeAt(i);
			h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
		}
		return ('00000000' + h.toString(16)).slice(-8);
	}

	// Extract canonical language token from code element class.
	codeLangFromEl(codeEl) {
		try {
			const cls = Array.from(codeEl.classList).find(c => c.startsWith('language-')) || 'language-plaintext';
			return (cls.replace('language-', '') || 'plaintext');
		} catch (_) {
			return 'plaintext';
		}
	}

	// Produce a simple fingerprint of a code block to detect unchanged ones across snapshots.
	codeFingerprint(codeEl) {
		const cls = Array.from(codeEl.classList).find(c => c.startsWith('language-')) || 'language-plaintext';
		const lang = cls.replace('language-', '') || 'plaintext';
		const t = codeEl.textContent || '';
		const len = t.length;
		const head = t.slice(0, 64);
		const tail = t.slice(-64);
		return `${lang}|${len}|${head}|${tail}`;
	}

	// Read precomputed fingerprint from code wrapper attributes if present.
	// Now validates attributes against the actual code text; falls back to null when stale.
	codeFingerprintFromWrapper(codeEl) {
		try {
			const wrap = codeEl.closest('.code-wrapper');
			if (!wrap) return null;

			// Prefer stable fp when present (handles small textual diffs across snapshots).
			const fpStable = wrap.getAttribute('data-fp');
			if (fpStable) return fpStable;

			// Legacy path with validation against actual text to avoid stale attrs.
			const cls = Array.from(codeEl.classList).find(c => c.startsWith('language-')) || 'language-plaintext';
			const lang = (cls.replace('language-', '') || 'plaintext');

			const lenAttr = wrap.getAttribute('data-code-len');
			const headAttr = wrap.getAttribute('data-code-head') || '';
			const tailAttr = wrap.getAttribute('data-code-tail') || '';
			if (!lenAttr) return null;

			const txt = codeEl.textContent || '';
			const lenNow = txt.length;
			const lenNum = parseInt(lenAttr, 10);
			if (!Number.isFinite(lenNum) || lenNum !== lenNow) return null;

			const headNowEsc = Utils.escapeHtml(txt.slice(0, 64));
			const tailNowEsc = Utils.escapeHtml(txt.slice(-64));
			if ((headAttr && headAttr !== headNowEsc) || (tailAttr && tailAttr !== tailNowEsc)) {
				return null;
			}

			return `${lang}|${lenAttr}|${headAttr}|${tailAttr}`;
		} catch (_) {
			return null;
		}
	}

	// Reuse old, closed code blocks that did not change between snapshots to avoid flicker/work.
	// Optimized: rely on wrapper-provided fingerprints/attributes; avoid reading textContent for big nodes.
	preserveStableClosedCodes(oldSnap, newRoot, skipLastIfStreaming) {
		try {
			const oldCodes = oldSnap.querySelectorAll('pre code');
			if (!oldCodes || !oldCodes.length) return;
			const newCodesPre = newRoot.querySelectorAll('pre code');
			if (!newCodesPre || !newCodesPre.length) return;
			const limit = (this.engine.cfg.STREAM && this.engine.cfg.STREAM.PRESERVE_CODES_MAX) || 200;
			if (newCodesPre.length > limit || oldCodes.length > limit) return;

			// DEBUG
			this.engine.debug('codes.preserve.scan', {
				old: oldCodes.length,
				anew: newCodesPre.length,
				skipLastIfStreaming
			});

			// Build maps keyed by full, stable fp key (data-fp) or by lightweight tuple from wrapper attrs.
			const map = new Map();
			const push = (key, el) => {
				if (!key) return;
				let arr = map.get(key);
				if (!arr) {
					arr = [];
					map.set(key, arr);
				}
				arr.push(el);
			};

			const makeAttrKey = (wrap) => {
				if (!wrap) return '';
				// Use only cheap attributes; do not read textContent.
				const lang = (wrap.getAttribute('data-code-lang') || 'plaintext');
				const len = (wrap.getAttribute('data-code-len') || '0');
				const head = (wrap.getAttribute('data-code-head') || '');
				const tail = (wrap.getAttribute('data-code-tail') || '');
				return `${lang}|${len}|${head}|${tail}`;
			};

			for (let idx = 0; idx < oldCodes.length; idx++) {
				const el = oldCodes[idx];
				// Skip streaming (split) blocks and the current active block.
				if (el.querySelector('.hl-frozen')) continue;
				if (this.engine.code.activeCode && el === this.engine.code.activeCode.codeEl) continue;
				const wrap = el.closest('.code-wrapper');
				const fpStable = wrap ? wrap.getAttribute('data-fp') : null;
				if (fpStable) {
					push(`S|${fpStable}`, el);
				} else {
					push(`A|${makeAttrKey(wrap)}`, el);
				}
			}

			// For each new code, try to swap with an old, identical one.
			const end = (skipLastIfStreaming && newCodesPre.length > 0) ? (newCodesPre.length - 1) : newCodesPre.length;
			for (let i = 0; i < end; i++) {
				const nc = newCodesPre[i];
				if (nc.getAttribute('data-highlighted') === 'yes') continue;

				const wrap = nc.closest('.code-wrapper');
				let swapped = false;

				const fpStableNew = wrap ? wrap.getAttribute('data-fp') : null;
				if (fpStableNew) {
					const arr = map.get(`S|${fpStableNew}`);
					if (arr && arr.length) {
						const oldEl = arr.pop();
						if (oldEl && oldEl.isConnected) {
							try {
								nc.replaceWith(oldEl);
								this.engine.codeScroll.attachHandlers(oldEl);
								if (!oldEl.getAttribute('data-highlighted')) oldEl.setAttribute('data-highlighted', 'yes');
								const st = this.engine.codeScroll.state(oldEl);
								st.autoFollow = false;
							} catch (_) {}
							swapped = true;
						}
						if (!arr.length) map.delete(`S|${fpStableNew}`);
					}
				}
				if (swapped) continue;

				const attrKey = `A|${makeAttrKey(wrap)}`;
				const arr2 = map.get(attrKey);
				if (arr2 && arr2.length) {
					const oldEl = arr2.pop();
					if (oldEl && oldEl.isConnected) {
						try {
							nc.replaceWith(oldEl);
							this.engine.codeScroll.attachHandlers(oldEl);
							if (!oldEl.getAttribute('data-highlighted')) oldEl.setAttribute('data-highlighted', 'yes');
							const st = this.engine.codeScroll.state(oldEl);
							st.autoFollow = false;
						} catch (_) {}
					}
					if (!arr2.length) map.delete(attrKey);
				}
			}
		} catch (e) {}
	}

	// Patch the snapshot root with minimal DOM changes (preserve stable nodes).
	patchSnapshotRoot(snap, frag) {
		try {
			// Snapshot current and new children (live NodeLists; avoid creating big arrays).
			const oldKids = snap.childNodes;
			const newKids = frag.childNodes;
			const aLen = oldKids.length;
			const bLen = newKids.length;

			// Fast path: nothing there yet.
			if (aLen === 0) {
				snap.appendChild(frag);
				// DEBUG
				this.engine.debug('snapshot.patch.first', {
					newCount: bLen
				});
				return;
			}

			// Compare up to MAX_CMP items from both ends to find common prefix/suffix.
			const MAX_CMP = 6;
			const eq = (a, b) => {
				try {
					if (!a || !b) return false;
					if (a.nodeType !== b.nodeType) return false;
					if (a.nodeType === 3 || a.nodeType === 8) return a.nodeValue === b.nodeValue;
					if (a.nodeType === 1) {
						const ae = a,
							be = b;
						if (ae.tagName !== be.tagName) return false;
						const acls = ae.className || '';
						if (acls !== (be.className || '')) return false;
						// Ignore transient stream-only style/data attributes on stable THINK nodes.
						// This keeps the same DOM node alive while the normal answer is appended,
						// allowing its fade-out transition to finish instead of being restarted.
						if (ae.tagName === 'THINK') return ae.textContent === be.textContent;
						return ae.isEqualNode(be);
					}
					return false;
				} catch (_) {
					return false;
				}
			};

			let i = 0,
				j = 0;
			const iMax = Math.min(aLen, bLen, MAX_CMP);
			while (i < iMax && eq(oldKids[i], newKids[i])) i++;
			const jMax = Math.min(aLen - i, bLen - i, MAX_CMP);
			while (j < jMax && eq(oldKids[aLen - 1 - j], newKids[bLen - 1 - j])) j++;

			// Remove the changed middle from old DOM.
			const removeStart = i;
			const removeEnd = aLen - j;
			for (let k = removeStart; k < removeEnd; k++) {
				const node = snap.childNodes[removeStart]; // always remove at the same index
				if (node) {
					try {
						snap.removeChild(node);
					} catch (_) {}
				}
			}

			// Insert the new middle chunk.
			const insStart = i,
				insEnd = bLen - j;
			if (insStart < insEnd) {
				const mid = document.createDocumentFragment();
				// Note: newKids is live; always grab at insStart index.
				for (let k = insStart; k < insEnd; k++) {
					if (newKids[insStart]) mid.appendChild(newKids[insStart]);
				}
				const ref = (i < snap.childNodes.length) ? snap.childNodes[i] : null;
				if (ref) snap.insertBefore(mid, ref);
				else snap.appendChild(mid);
			}

			// DEBUG
			this.engine.debug('snapshot.patch', {
				oldCount: aLen,
				newCount: bLen,
				removed: (removeEnd - removeStart),
				inserted: (bLen - j - i)
			});

		} catch (_) {
			// Fallback: replace everything.
			try {
				snap.replaceChildren(frag);
				this.engine.debug('snapshot.patch.replaceAll', {});
			} catch (__) {}
		}
	}

	// ========================================
	// Stable code and snapshot reconciliation internals
	// ========================================

	// Build stable fp key from element (lang | normLen | hash(normText)).
	_fpKeyFromCodeEl(codeEl) {
		try {
			const lang = this.codeLangFromEl(codeEl);
			const norm = this.normTextForFP(codeEl.textContent || '');
			return `${lang}|${norm.length}|${this.hash32FNV(norm)}`;
		} catch (_) {
			return '';
		}
	}

}
