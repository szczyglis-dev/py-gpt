// StreamCode owns code behavior and state.
class StreamCode {

	// ========================================
	// Composition
	// ========================================

	constructor(engine) {
		this.engine = engine;
		// Simple counters for currently open code stream
		this.codeStream = {
			open: false,
			lines: 0,
			chars: 0
		};
		this.activeCode = null;

		this._promoteScheduled = false;
		this._promoteTimer = 0;

	}

	// ========================================
	// Code lifecycle
	// ========================================

	reset() {
		this.codeStream = {open: false, lines: 0, chars: 0};
		this.activeCode = null;
		this._promoteScheduled = false;
		if (this._promoteTimer) clearTimeout(this._promoteTimer);
		this._promoteTimer = 0;
	}

	// Finish the active code block: merge tail+frozen, re-highlight once, and stop auto-follow..
	finalizeActiveCode() {
		if (!this.activeCode) return;
		const ac = this.activeCode;
		const codeEl = ac.codeEl;
		if (!codeEl || !codeEl.isConnected) {
			this.activeCode = null;
			return;
		}

		// DEBUG
		this.engine.debug('code.finalize.begin', {
			lang: ac.lang,
			frozenLen: ac.frozenLen,
			tailLen: (ac.tailEl ? (ac.tailEl.textContent || '').length : 0),
			plainStream: !!ac.plainStream
		});

		// Preserve current scroll position relative to bottom
		const fromBottomBefore = Math.max(0, codeEl.scrollHeight - codeEl.clientHeight - codeEl.scrollTop);
		const wasNearBottom = this.engine.codeScroll.isNearBottomEl(codeEl, this.engine.cfg.CODE_SCROLL.NEAR_MARGIN_PX);

		// Gather only what we really need; DO NOT serialize large frozen HTML to string
		const tailTXT = ac.tailEl ? (ac.tailEl.textContent || '') : '';

		// Decide final rendering mode
		const canHL = !this.engine.cfg.HL.DISABLE_ALL && !ac.plainStream && this.engine.language.isHLJSSupported(ac.lang);

		// Build the final code DOM without re-stringifying the whole block
		// PERF: move existing highlighted nodes instead of reading .innerHTML (huge string)
		const frag = document.createDocumentFragment();

		// Move all frozen children (already highlighted or plain text node)
		try {
			if (ac.frozenEl) {
				while (ac.frozenEl.firstChild) frag.appendChild(ac.frozenEl.firstChild);
			}
		} catch (_) {}

		// Append tail (highlighted if possible)
		try {
			if (tailTXT) {
				if (canHL) {
					let tailHTML = '';
					try {
						tailHTML = this.highlightDeltaText(ac.lang, tailTXT);
					} catch (_) {
						tailHTML = Utils.escapeHtml(tailTXT);
					}
					if (this.engine._tpl) {
						this.engine._tpl.innerHTML = tailHTML;
						while (this.engine._tpl.content.firstChild) frag.appendChild(this.engine._tpl.content.firstChild);
					} else {
						const tpl = document.createElement('template');
						tpl.innerHTML = tailHTML;
						frag.appendChild(tpl.content);
					}
				} else {
					frag.appendChild(document.createTextNode(tailTXT));
				}
			}
		} catch (_) {}

		// Replace split structure with the final content in minimal DOM writes
		try {
			codeEl.textContent = ''; // clear fast without creating a giant temp string
			codeEl.appendChild(frag);
			// Ensure hljs base styling is present and mark as already highlighted
			codeEl.classList.add('hljs');
			codeEl.setAttribute('data-highlighted', 'yes');
			// Explicitly clear streaming markers
			codeEl.dataset._active_stream = '0';
		} catch (_) {}

		// Sync wrapper metadata to keep reuse stable on next snapshots (fast path)
		try {
			const totalChars = (ac.frozenLen | 0) + (tailTXT ? tailTXT.length : 0);
			const totalLines = (ac.initialLines | 0) + (ac.lines | 0);
			this._updateCodeWrapperMetaFast(codeEl, totalChars, totalLines, ac.lang);
		} catch (_) {}

		// Disable auto-follow and restore scroll position relative to bottom
		const st = this.engine.codeScroll.state(codeEl);
		st.autoFollow = false;
		const maxScrollTop = Math.max(0, codeEl.scrollHeight - codeEl.clientHeight);
		const target = wasNearBottom ? maxScrollTop : Math.max(0, maxScrollTop - fromBottomBefore);
		try {
			codeEl.scrollTop = target;
		} catch (_) {}
		st.lastScrollTop = codeEl.scrollTop;

		// Mark as just finalized so helper can ensure bottom if needed
		try {
			codeEl.dataset.justFinalized = '1';
		} catch (_) {}
		this.engine.codeScroll.scheduleScroll(codeEl, false, true);

		// We already produced a final highlighted block when possible – no need to enqueue hljs again.
		// Keep a suppression flag for math and other post passes consistent with previous behavior.
		this.engine.suppressPostFinalizePass = true;

		// Drop active state and heavy refs to help GC
		try {
			ac._tailTextNode = null;
			ac._frozenTextNode = null;
			ac.frozenEl = null;
			ac.tailEl = null;
			ac.codeEl = null;
		} catch (_) {}
		this.activeCode = null;

		// DEBUG
		this.engine.debug('code.finalize.end', {});
	}

	// Similar helper: ensure finalized blocks end up at bottom (variant used after patching).
	ensureBottomForJustFinalized(root) {
		try {
			const scope = root || document;
			const nodes = scope.querySelectorAll('pre code[data-just-finalized="1"]');
			if (!nodes || !nodes.length) return;
			nodes.forEach((codeEl) => {
				// NOTE: use a primitive key; do not capture DOM in scheduler key object
				const wrap = codeEl.closest('.code-wrapper');
				const idx = wrap ? (wrap.getAttribute('data-index') || '') : '';
				const key = `JF:ensureBottom#${idx}`;
				this.engine.codeScroll.scheduleScroll(codeEl, false, true);
				this.engine.raf.schedule(key, () => {
					this.engine.codeScroll.scrollToBottom(codeEl, false, true);
					try {
						codeEl.dataset.justFinalized = '0';
					} catch (_) {}
				}, 'CodeScroll', 2);
			});
		} catch (_) {}
	}

	// Convert active highlighted block back to plain text (when aborting).
	defuseActiveToPlain() {
		if (!this.activeCode || !this.activeCode.codeEl || !this.activeCode.codeEl.isConnected) return;
		const codeEl = this.activeCode.codeEl;
		// Merge frozen + tail into a single plain text content.
		const fullText = (this.activeCode.frozenEl?.textContent || '') + (this.activeCode.tailEl?.textContent || '');
		// DEBUG
		this.engine.debug('code.defuseActive', {
			fullLen: fullText.length
		});
		try {
			codeEl.textContent = fullText;
			codeEl.removeAttribute('data-highlighted');
			codeEl.classList.remove('hljs');
			codeEl.dataset._active_stream = '0';
			// Stop auto-follow on this code block.
			const st = this.engine.codeScroll.state(codeEl);
			st.autoFollow = false;
		} catch (_) {}
		this.activeCode = null;
	}

	// Find any stray "active" code blocks and turn them into normal code blocks.
	defuseOrphanActiveBlocks(root) {
		try {
			const scope = root || document;
			const nodes = scope.querySelectorAll('pre code[data-_active_stream="1"]');
			let n = 0;
			nodes.forEach(codeEl => {
				if (!codeEl.isConnected) return;
				// Gather full text either from split spans or plain content.
				let text = '';
				const frozen = codeEl.querySelector('.hl-frozen');
				const tail = codeEl.querySelector('.hl-tail');
				if (frozen || tail) text = (frozen?.textContent || '') + (tail?.textContent || '');
				else text = codeEl.textContent || '';
				// Replace with plain text and reset flags/classes.
				codeEl.textContent = text;
				codeEl.removeAttribute('data-highlighted');
				codeEl.classList.remove('hljs');
				codeEl.dataset._active_stream = '0';
				try {
					this.engine.codeScroll.attachHandlers(codeEl);
				} catch (_) {}
				n++;
			});
			// DEBUG
			if (n) this.engine.debug('code.defuseOrphans', {
				count: n
			});
		} catch (e) {}
	}

	// ========================================
	// Code DOM and tail updates
	// ========================================

	// Prepare a code element to have separate "frozen" (highlighted) and "tail" (live) spans.
	ensureSplitCodeEl(codeEl) {
		if (!codeEl) return null;
		let frozen = codeEl.querySelector('.hl-frozen');
		let tail = codeEl.querySelector('.hl-tail');
		if (frozen && tail) return {
			codeEl,
			frozenEl: frozen,
			tailEl: tail
		};
		// If not split yet, create the structure and move existing text to tail.
		const text = codeEl.textContent || '';
		codeEl.innerHTML = '';
		frozen = document.createElement('span');
		frozen.className = 'hl-frozen';
		tail = document.createElement('span');
		tail.className = 'hl-tail';
		codeEl.appendChild(frozen);
		codeEl.appendChild(tail);
		if (text) tail.textContent = text;
		// DEBUG
		this.engine.debug('code.ensureSplit', {
			hadText: !!text,
			textLen: text.length
		});
		return {
			codeEl,
			frozenEl: frozen,
			tailEl: tail
		};
	}

	// Inspect the last code block in snapshot and set it as active streaming target.
	setupActiveCodeFromSnapshot(snap) {
		// Pick the last <pre><code> since it's most likely the open one.
		const codes = snap.querySelectorAll('pre code');
		if (!codes.length) return null;
		const last = codes[codes.length - 1];
		// Infer language from class or default to plaintext.
		const cls = Array.from(last.classList).find(c => c.startsWith('language-')) || 'language-plaintext';
		const lang = (cls.replace('language-', '') || 'plaintext');
		const parts = this.ensureSplitCodeEl(last);
		if (!parts) return null;

		// If we had injected a synthetic EOL for parsing, remove it from the tail text.
		if (this.engine._lastInjectedEOL && parts.tailEl && parts.tailEl.textContent && parts.tailEl.textContent.endsWith('\n')) {
			parts.tailEl.textContent = parts.tailEl.textContent.slice(0, -1);
			this.engine._lastInjectedEOL = false;
		}

		// Enable auto-follow scrolling for the active code block.
		const st = this.engine.codeScroll.state(parts.codeEl);
		st.autoFollow = true;
		st.userInteracted = false;
		parts.codeEl.dataset._active_stream = '1';
		const baseFrozenNL = Utils.countNewlines(parts.frozenEl.textContent || '');
		const baseTailNL = Utils.countNewlines(parts.tailEl.textContent || '');
		const ac = {
			codeEl: parts.codeEl,
			frozenEl: parts.frozenEl,
			tailEl: parts.tailEl,
			lang,
			frozenLen: parts.frozenEl.textContent.length,
			lastPromoteTs: 0,
			lines: 0,
			tailLines: baseTailNL,
			linesSincePromote: 0,
			initialLines: baseFrozenNL + baseTailNL,
			haltHL: false,
			plainStream: false
		};
		// DEBUG
		this.engine.debug('code.active.set', {
			lang,
			frozenLen: ac.frozenLen,
			tailNL: baseTailNL
		});
		return ac;
	}

	// Reconnect previous active code state to the newly rendered code element after a snapshot.
	rehydrateActiveCode(oldAC, newAC) {
		if (!oldAC || !newAC) return;
		const newFullText = newAC.codeEl.textContent || '';

		// If we switched to plain streaming for performance, rebuild as plain text node tail.
		if (oldAC.plainStream === true) {
			const prevText = oldAC.tailEl ? (oldAC.tailEl.textContent || '') : '';
			let delta = '';
			if (newFullText && newFullText.startsWith(prevText)) delta = newFullText.slice(prevText.length);
			else delta = newFullText;

			// Reuse/transfer the tail text node so appends stay cheap.
			while (newAC.tailEl.firstChild) newAC.tailEl.removeChild(newAC.tailEl.firstChild);

			let tn = null;
			if (oldAC._tailTextNode && oldAC._tailTextNode.parentNode === oldAC.tailEl && oldAC._tailTextNode.nodeType === Node.TEXT_NODE) {
				tn = oldAC._tailTextNode;
			} else if (oldAC.tailEl && oldAC.tailEl.firstChild && oldAC.tailEl.firstChild.nodeType === Node.TEXT_NODE) {
				tn = oldAC.tailEl.firstChild;
			} else {
				tn = document.createTextNode(prevText || '');
			}
			newAC.tailEl.appendChild(tn);
			newAC._tailTextNode = tn;

			if (delta && delta !== prevText) tn.appendData(delta);

			// Carry over counters/flags.
			newAC.frozenLen = 0;
			newAC.lang = oldAC.lang;
			newAC.lines = oldAC.lines;
			newAC.tailLines = Utils.countNewlines((prevText || '') + (delta && delta !== prevText ? delta : ''));
			newAC.lastPromoteTs = oldAC.lastPromoteTs;
			newAC.linesSincePromote = oldAC.linesSincePromote || 0;
			newAC.initialLines = oldAC.initialLines || 0;
			newAC.haltHL = !!oldAC.haltHL;
			newAC.plainStream = true;

			// Null out old references to help GC.
			try {
				oldAC.codeEl = null;
				oldAC.frozenEl = null;
				oldAC.tailEl = null;
			} catch (_) {}
			// DEBUG
			this.engine.debug('code.rehydrate.plain', {
				deltaLen: delta.length
			});
			return;
		}

		// Default path: frozen length stays, tail is replaced with the remainder.
		const remainder = newFullText.slice(oldAC.frozenLen);

		if (oldAC.frozenEl) {
			// Move DOM children from old frozen into new frozen to preserve highlighting.
			const src = oldAC.frozenEl;
			const dst = newAC.frozenEl;
			if (dst && src) {
				while (src.firstChild) dst.appendChild(src.firstChild);
			}
		}

		newAC.tailEl.textContent = remainder;

		// Carry over state so promotion cadence stays smooth.
		newAC.frozenLen = oldAC.frozenLen;
		newAC.lang = oldAC.lang;
		newAC.lines = oldAC.lines;
		newAC.tailLines = Utils.countNewlines(remainder);
		newAC.lastPromoteTs = oldAC.lastPromoteTs;
		newAC.linesSincePromote = oldAC.linesSincePromote || 0;
		newAC.initialLines = oldAC.initialLines || 0;
		newAC.haltHL = !!oldAC.haltHL;
		newAC.plainStream = !!oldAC.plainStream;

		try {
			oldAC.codeEl = null;
			oldAC.frozenEl = null;
			oldAC.tailEl = null;
		} catch (_) {}
		// DEBUG
		this.engine.debug('code.rehydrate', {
			remainderLen: remainder.length,
			frozenLen: newAC.frozenLen
		});
	}

	// Append new text to the active code tail quickly.
	appendToActiveTail(text) {
		if (!this.activeCode || !this.activeCode.tailEl || !text) return;

		// Keep a stable text node for cheap appends.
		let tn = this.activeCode._tailTextNode;
		if (!tn || tn.parentNode !== this.activeCode.tailEl || tn.nodeType !== Node.TEXT_NODE) {
			const t = this.activeCode.tailEl.textContent || '';
			this.activeCode.tailEl.textContent = t;
			tn = this.activeCode._tailTextNode = this.activeCode.tailEl.firstChild || document.createTextNode('');
			if (!tn.parentNode) this.activeCode.tailEl.appendChild(tn);
		}

		tn.appendData(text);

		// Update newline counters used for promotion cadence.
		const nl = Utils.countNewlines(text);
		this.activeCode.tailLines += nl;
		this.activeCode.linesSincePromote += nl;

		// Normalize occasionally to avoid too many text nodes.
		if (((this.activeCode._tailAppends = (this.activeCode._tailAppends | 0) + 1) % 200) === 0) {
			this.activeCode.tailEl.normalize();
			this.activeCode._tailTextNode = this.activeCode.tailEl.firstChild;
		}

		// DEBUG (only if interesting)
		if (/[<>]/.test(text)) {
			this.engine.debug('code.tail.append', {
				len: text.length,
				nl,
				head: text.slice(0, 80),
				tail: text.slice(-80)
			});
		}

		// Keep the viewport following the code tail.
		this.engine.codeScroll.scheduleScroll(this.activeCode.codeEl, true, false);
	}

	// Kick the engine when tab becomes visible again or layout changed.
	kickVisibility() {
		const msg = this.engine.getMsg(false, '');
		if (!msg) return;
		// If code is open but activeCode got lost, force a snapshot to recover.
		if (this.codeStream.open && !this.activeCode) {
			this.engine.debug('kick.visibility', {
				reason: 'codeStreamOpenNoActive'
			});
			this.engine.snapshots.scheduleSnapshot(msg, true);
			return;
		}
		// If we have unseen data in buffer, render it now.
		const needSnap = (this.engine.buffer.getStreamLength() !== (window.__lastSnapshotLen || 0));
		if (needSnap) {
			this.engine.debug('kick.visibility', {
				reason: 'bufferDelta'
			});
			this.engine.snapshots.scheduleSnapshot(msg, true);
		}
		// If code is active, keep promoting/highlighting.
		if (this.activeCode && this.activeCode.codeEl) {
			this.engine.codeScroll.scheduleScroll(this.activeCode.codeEl, true, false);
			this.schedulePromoteTail(true);
		}
	}

	// ========================================
	// Incremental highlighting
	// ========================================

	// Apply budgets/limits and switch to plain streaming when too big or too long.
	enforceHLStopBudget() {
		if (!this.activeCode) return;
		// Global kill-switch.
		if (this.engine.cfg.HL.DISABLE_ALL) {
			this.activeCode.haltHL = true;
			this.activeCode.plainStream = true;
			return;
		}
		const stop = (this.engine.cfg.PROFILE_CODE.stopAfterLines | 0);
		const streamPlainLines = (this.engine.cfg.PROFILE_CODE.streamPlainAfterLines | 0);
		const streamPlainChars = (this.engine.cfg.PROFILE_CODE.streamPlainAfterChars | 0);
		const maxFrozenChars = (this.engine.cfg.PROFILE_CODE.maxFrozenChars | 0);

		const totalLines = (this.activeCode.initialLines || 0) + (this.activeCode.lines || 0);
		const frozenChars = this.activeCode.frozenLen | 0;
		const tailChars = (this.activeCode.tailEl?.textContent || '').length | 0;
		const totalStreamedChars = frozenChars + tailChars;

		// If any threshold is exceeded, stop highlighting further and stream as plain.
		if ((streamPlainLines > 0 && totalLines >= streamPlainLines) ||
			(streamPlainChars > 0 && totalStreamedChars >= streamPlainChars) ||
			(maxFrozenChars > 0 && frozenChars >= maxFrozenChars)) {
			this.activeCode.haltHL = true;
			this.activeCode.plainStream = true;
			try {
				this.activeCode.codeEl.dataset.hlStreamSuspended = '1';
			} catch (_) {}
			// DEBUG
			this.engine.debug('code.hl.budget.stop', {
				totalLines,
				totalStreamedChars,
				frozenChars,
				streamPlainLines,
				streamPlainChars,
				maxFrozenChars
			});
			return;
		}

		// Hard stop after N lines if configured.
		if (stop > 0 && totalLines >= stop) {
			this.activeCode.haltHL = true;
			this.activeCode.plainStream = true;
			try {
				this.activeCode.codeEl.dataset.hlStreamSuspended = '1';
			} catch (_) {}
			// DEBUG
			this.engine.debug('code.hl.budget.hardStop', {
				totalLines,
				stop
			});
		}
	}

	// Convert a code text delta to highlighted HTML using hljs (or escape as fallback).
	highlightDeltaText(lang, text) {
		if (this.engine.cfg.HL.DISABLE_ALL) return Utils.escapeHtml(text);
		if (window.hljs && lang && hljs.getLanguage && hljs.getLanguage(lang)) {
			try {
				return hljs.highlight(text, {
					language: lang,
					ignoreIllegals: true
				}).value;
			} catch (_) {
				return Utils.escapeHtml(text);
			}
		}
		return Utils.escapeHtml(text);
	}

	// Schedule a background task to promote tail (move some tail to frozen).
	// The visible code still updates during streaming, but no more often than the
	// configured live-highlight cadence (300 ms by default).
	schedulePromoteTail(force = false) {
		if (!this.activeCode || !this.activeCode.tailEl) return;
		if (this.activeCode.plainStream === true) return;

		const throttle = Math.max(0, Number((this.engine.cfg.HL && this.engine.cfg.HL.STREAM_THROTTLE_MS) || 300) || 0);
		if (!force && throttle > 0) {
			const last = Number(this.activeCode.lastPromoteTs || 0);
			const wait = Math.max(0, throttle - (Utils.now() - last));
			if (wait > 0) {
				if (!this._promoteTimer) {
					this._promoteTimer = setTimeout(() => {
						this._promoteTimer = 0;
						this.schedulePromoteTail(false);
					}, wait);
				}
				return;
			}
		}

		if (force && this._promoteTimer) {
			clearTimeout(this._promoteTimer);
			this._promoteTimer = 0;
		}
		if (this._promoteScheduled) return;
		this._promoteScheduled = true;
		this.engine.debug('code.promote.schedule', { force, throttle });
		this.engine.raf.schedule('SE:promoteTail', () => {
			this._promoteScheduled = false;
			this._promoteTailWork(force);
		}, 'StreamEngine', 1);
	}

	// ========================================
	// Code metadata
	// ========================================

	// Stabilize the language header label across snapshots to avoid flicker.
	stabilizeHeaderLabel(prevAC, newAC) {
		try {
			if (!newAC || !newAC.codeEl || !newAC.codeEl.isConnected) return;

			const wrap = newAC.codeEl.closest('.code-wrapper');
			if (!wrap) return;

			const span = wrap.querySelector('.code-header-lang');
			const curLabel = (span && span.textContent ? span.textContent.trim() : '').toLowerCase();

			// If labeled "output", keep it as-is.
			if (curLabel === 'output') return;

			const tokNow = (wrap.getAttribute('data-code-lang') || '').trim().toLowerCase();
			const sticky = (wrap.getAttribute('data-lang-sticky') || '').trim().toLowerCase();
			const prev = (prevAC && prevAC.lang && prevAC.lang !== 'plaintext') ? prevAC.lang.toLowerCase() : '';

			const valid = (t) => !!t && t !== 'plaintext' && this.engine.language.isHLJSSupported(t);

			// Prefer current explicit token, else previous language, else sticky fallback.
			let finalTok = '';
			if (valid(tokNow)) finalTok = tokNow;
			else if (valid(prev)) finalTok = prev;
			else if (valid(sticky)) finalTok = sticky;

			if (finalTok) {
				this.engine.language.updateCodeLangClass(newAC.codeEl, finalTok);
				this.engine.language.updateCodeHeaderLabel(newAC.codeEl, finalTok, finalTok);
				try {
					wrap.setAttribute('data-code-lang', finalTok);
				} catch (_) {}
				try {
					wrap.setAttribute('data-lang-sticky', finalTok);
				} catch (_) {}
				newAC.lang = finalTok;
				// DEBUG
				this.engine.debug('code.header.stabilize', {
					finalTok
				});
			} else {
				// Avoid super short labels like "c" if we can't validate them.
				if (span && curLabel && curLabel.length < 3) span.textContent = 'code';
			}
		} catch (_) {}
	}

	// ========================================
	// Incremental highlighting internals
	// ========================================

	// Worker: move a safe chunk of tail into frozen (highlighted) area.
	async _promoteTailWork(force = false) {
		if (!this.activeCode || !this.activeCode.tailEl) return;
		if (this.activeCode.plainStream === true) return;

		const now = Utils.now();
		const prof = this.engine.cfg.PROFILE_CODE;
		const tailText0 = this.activeCode.tailEl.textContent || '';
		if (!tailText0) return;

		// Respect cadence: not too often, and only if enough lines/chars arrived unless forced.
		if (!force) {
			if ((now - this.activeCode.lastPromoteTs) < prof.promoteMinInterval) return;
			const enoughLines = (this.activeCode.linesSincePromote || 0) >= (prof.promoteMinLines || 10);
			const enoughChars = tailText0.length >= prof.minCharsForHL;
			if (!enoughLines && !enoughChars) return;
		}

		// Choose a safe cut position: up to last newline to avoid partial lines.
		const idx = tailText0.lastIndexOf('\n');
		const usePlain = this.activeCode.haltHL || this.activeCode.plainStream || !this.engine.language.isHLJSSupported(this.activeCode.lang);
		let cut = -1;

		if (idx >= 0) cut = idx + 1;
		else if (usePlain) {
			// If highlighting is off, we can move big plain chunks even without newline.
			const PLAIN_PROMOTE_CHARS = this.engine.cfg.PROFILE_CODE.minPlainPromoteChars || 8192;
			if (tailText0.length >= PLAIN_PROMOTE_CHARS || force) cut = tailText0.length;
		}

		if (cut <= 0) return;
		const delta = tailText0.slice(0, cut);
		if (!delta) return;

		// Enforce budgets before doing heavy work.
		this.enforceHLStopBudget();

		// Yield to keep UI responsive if we plan to run hljs.
		if (!usePlain) await this.engine.asyncer.yield();

		// Verify the tail still starts with the expected delta (not changed by new chunks).
		if (!this.activeCode || !this.activeCode.tailEl) return;
		const tailNow = this.activeCode.tailEl.textContent || '';
		if (!tailNow.startsWith(delta)) {
			// Tail changed; try again later.
			this.engine.debug('code.promote.tailChanged', {
				expectedLen: delta.length,
				tailNowLen: tailNow.length
			});
			this.schedulePromoteTail(false);
			return;
		}

		// Move delta from tail to frozen, highlighting if enabled.
		if (usePlain) {
			// PERF: append into a dedicated text node to avoid repeated string copies.
			let tn = this.activeCode._frozenTextNode;
			if (!tn || tn.parentNode !== this.activeCode.frozenEl) {
				tn = document.createTextNode('');
				this.activeCode.frozenEl.appendChild(tn);
				this.activeCode._frozenTextNode = tn;
			}
			tn.appendData(delta);
		} else {
			let html = Utils.escapeHtml(delta);
			try {
				html = this.highlightDeltaText(this.activeCode.lang, delta);
			} catch (_) {
				html = Utils.escapeHtml(delta);
			}
			// Reuse template to parse HTML into nodes without creating extra wrapper elements.
			if (this.engine._tpl) {
				this.engine._tpl.innerHTML = html;
				while (this.engine._tpl.content.firstChild) this.activeCode.frozenEl.appendChild(this.engine._tpl.content.firstChild);
			} else {
				this.activeCode.frozenEl.insertAdjacentHTML('beforeend', html);
			}
			html = null;
		}

		// Cut the promoted part from tail and update counters.
		this.activeCode.tailEl.textContent = tailNow.slice(delta.length);
		this.activeCode.frozenLen += delta.length;
		const promotedLines = Utils.countNewlines(delta);
		this.activeCode.tailLines = Math.max(0, (this.activeCode.tailLines || 0) - promotedLines);
		this.activeCode.linesSincePromote = Math.max(0, (this.activeCode.linesSincePromote || 0) - promotedLines);
		this.activeCode.lastPromoteTs = Utils.now();

		// DEBUG
		this.engine.debug('code.promote.done', {
			plain: usePlain,
			deltaLen: delta.length,
			promotedLines,
			frozenLen: this.activeCode.frozenLen,
			tailLenNow: (this.activeCode.tailEl.textContent || '').length
		});
	}

	// ========================================
	// Code DOM and tail updates internals
	// ========================================

	// Ensure "just finalized" code blocks snap to bottom once scrolling finishes.
	_ensureSplitContainers(codeEl) {
		try {
			const scope = codeEl || document;
			const nodes = scope.querySelectorAll('pre code[data-just-finalized="1"]');
			if (!nodes || !nodes.length) return;
			nodes.forEach((codeEl) => {
				this.engine.codeScroll.scheduleScroll(codeEl, false, true);
				// NOTE: use a primitive key; do not capture DOM in scheduler key object
				const wrap = codeEl.closest('.code-wrapper');
				const idx = wrap ? (wrap.getAttribute('data-index') || '') : '';
				const key = `JF:forceBottom#${idx}`;
				this.engine.raf.schedule(key, () => {
					this.engine.codeScroll.scrollToBottom(codeEl, false, true);
					try {
						codeEl.dataset.justFinalized = '0';
					} catch (_) {}
				}, 'CodeScroll', 2);
			});
		} catch (_) {}
	}

	// ========================================
	// Code metadata internals
	// ========================================

	// Keep wrapper metadata (len/head/tail/nl/lang/fp) in sync with actual code text.
	_updateCodeWrapperMeta(codeEl) {
		try {
			const wrap = codeEl.closest('.code-wrapper');
			if (!wrap) return;
			const txt = codeEl.textContent || '';
			wrap.setAttribute('data-code-len', String(txt.length));
			wrap.setAttribute('data-code-head', Utils.escapeHtml(txt.slice(0, 64)));
			wrap.setAttribute('data-code-tail', Utils.escapeHtml(txt.slice(-64)));
			wrap.setAttribute('data-code-nl', String(Utils.countNewlines(txt)));

			const lang = this.engine.stability.codeLangFromEl(codeEl);
			wrap.setAttribute('data-code-lang', lang);

			const norm = this.engine.stability.normTextForFP(txt);
			const fp = `${lang}|${norm.length}|${this.engine.stability.hash32FNV(norm)}`;
			wrap.setAttribute('data-fp', fp);
		} catch (_) {}
	}

	// Fast metadata update without reading full textContent (avoid huge string copies).
	_updateCodeWrapperMetaFast(codeEl, len, nl, langTok) {
		try {
			const wrap = codeEl.closest('.code-wrapper');
			if (!wrap) return;
			if (Number.isFinite(len)) wrap.setAttribute('data-code-len', String(len));
			if (Number.isFinite(nl)) wrap.setAttribute('data-code-nl', String(nl));
			if (langTok) {
				wrap.setAttribute('data-code-lang', String(langTok));
				this.engine.language.updateCodeLangClass(codeEl, langTok);
			}
			// Do not recompute data-fp or head/tail here to avoid serializing the whole code.
			// Existing attributes remain valid enough for reuse + scanning.
		} catch (_) {}
	}

}
