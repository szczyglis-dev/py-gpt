// StreamPlain owns plain behavior and state.
class StreamPlain {

	// ========================================
	// Composition
	// ========================================

	constructor(engine) {
		this.engine = engine;
		// Plain streaming state for non-code text
		this.state = {
			active: false,
			container: null,
			anchor: null,
			lastMDTs: 0, // last inline-parse ts
			noMdNL: 0, // number of consecutive newlines with no markdown markers (acts as "plain lines")
			suppressInline: false, // disables inline parsing during long text streaks or when fully plain
			forceFullMDOnce: false, // request one full MD snapshot after markdown detected
			enabled: false, // plain-text mode is enabled only after threshold of "no markdown lines"
			_carry: '' // trailing carry used to keep partial last word out of DOM until a safe break
		};

		// Fast character classifiers used for safe-boundary decisions (kept stable and GC-friendly).
		this._isWordChar = (ch) => {
			if (!ch) return false;
			const c = ch.charCodeAt(0);
			// ASCII letters/digits
			if ((c >= 48 && c <= 57) || (c >= 65 && c <= 90) || (c >= 97 && c <= 122)) return true;
			// Latin-1 + Latin Extended (covers most European diacritics)
			if (c >= 0x00C0 && c <= 0x02AF) return true;
			return false;
		};
		this._isSafeBreakChar = (ch) => {
			if (!ch) return false;
			// Reuse precompiled regex to avoid per-call RegExp allocations.
			return this.engine._reSafeBreak.test(ch);
		};

	}

	// ========================================
	// Plain text streaming
	// ========================================

	// Plain helpers

	// Compute threshold (lines without Markdown) required to enable plain-text mode.
	threshold() {
		const STREAM = (this.engine.cfg && this.engine.cfg.STREAM) ? this.engine.cfg.STREAM : {};
		const thr = (STREAM.PLAIN_ACTIVATE_AFTER_LINES != null) ? STREAM.PLAIN_ACTIVATE_AFTER_LINES : 10;
		return Math.max(1, thr | 0);
	}

	// Reset "plain text streaming" state.
	reset() {
		this.state.active = false;
		this.state.container = null;
		this.state.anchor = null;
		this.state.lastMDTs = 0;
		this.state.noMdNL = 0;
		this.state.suppressInline = false;
		this.state.forceFullMDOnce = false;
		this.state.enabled = false;
		this.state._carry = '';
		// DEBUG
		this.engine.debug('plain.reset', {});
	}

    // Append a delta string into the plain text streaming host, managing safe boundaries and inline MD promotion.
	appendDelta(snap, delta) {
		if (!delta) return;
		const host = this._ensureContainer(snap);

		let combined = (this.state._carry || '') + String(delta);
		if (!combined) return;

		const flushIdx = this._findSafeFlushIndex(combined);
		let toAppend = combined.slice(0, flushIdx);
		let carryRemainder = combined.slice(flushIdx);

		// Do not push very short, unsafe heads that would split a word (no NL, 1–2 chars).
		const PLAIN = (this.engine.cfg && this.engine.cfg.STREAM && this.engine.cfg.STREAM.PLAIN) ? this.engine.cfg.STREAM.PLAIN : {};
		const MIN_ATOMIC = (PLAIN.MIN_ATOMIC_CHARS != null) ? PLAIN.MIN_ATOMIC_CHARS : 3;

		const isWord = (ch) => {
			if (!ch) return false;
			const c = ch.charCodeAt(0);
			if ((c >= 48 && c <= 57) || (c >= 65 && c <= 90) || (c >= 97 && c <= 122)) return true;
			return (c >= 0x00C0 && c <= 0x02AF);
		};
		const lastA = toAppend ? toAppend.charAt(toAppend.length - 1) : '';
		const firstB = carryRemainder ? carryRemainder.charAt(0) : '';
		const looksUnsafeSplit = (!/\r|\n/.test(toAppend)) && isWord(lastA) && isWord(firstB);

		if (toAppend && looksUnsafeSplit && toAppend.length < MIN_ATOMIC) {
			// Hold until we get a safer boundary
			this.state._carry = toAppend + carryRemainder;
			return;
		}

		this.state._carry = carryRemainder;
		if (!toAppend) return;

		// Append into tail text node inside current host
		let tn = this.state.anchor ? this.state.anchor.previousSibling : null;
		if (!tn || tn.nodeType !== Node.TEXT_NODE || tn.parentNode !== host) {
			tn = document.createTextNode('');
			try {
				host.insertBefore(tn, this.state.anchor);
			} catch (_) {
				host.appendChild(tn);
			}
		}
		tn.appendData(toAppend);

		// Let custom markup see the delta on the whole snapshot root (finalize closers fast).
		try {
			const CM = this.engine.renderer && this.engine.renderer.customMarkup;
			const MDinline = this.engine.renderer ? (this.engine.renderer.MD_STREAM || this.engine.renderer.MD || null) : null;
			if (CM && typeof CM.maybeApplyStreamOnDelta === 'function') {
				CM.maybeApplyStreamOnDelta(snap, toAppend, MDinline);
			}
		} catch (_) {}

		this._plainMaybeInlineMarkdown(toAppend, false);
		this.engine.scrollMgr.scheduleScroll(true);
	}

	// ========================================
	// Plain text streaming internals
	// ========================================

    // Ensure the plain text streaming host container is present and correctly placed.
	_ensureContainer(snap) {
		// Reuse the existing container when still attached.
		if (this.state.container && this.state.container.isConnected && this.state.anchor && this.state.anchor.parentNode === this.state.container) {
			// Ensure parent is correct (inside pending wrapper if any)
			const needParent = this._choosePlainParent(snap);
			if (needParent && this.state.container.parentNode !== needParent) {
				try {
					needParent.appendChild(this.state.container);
				} catch (_) {}
			}
			return this.state.container;
		}

		// Decide where to place the host (pending wrapper if present; else root)
		const parent = this._choosePlainParent(snap) || snap;

		// Inline host to avoid layout line breaks between consecutive hosts.
		const host = document.createElement('span');
		host.setAttribute('data-plain-stream', '1');
		host.style.whiteSpace = 'pre-wrap';
		host.style.display = 'inline';
		host.style.wordBreak = 'normal';
		host.style.overflowWrap = 'normal';

		// Text node acts as the visible tail; comment is a stable anchor.
		const tail = document.createTextNode('');
		const anchor = document.createComment('ps-tail');
		host.appendChild(tail);
		host.appendChild(anchor);

		try {
			parent.appendChild(host);
		} catch (_) {
			snap.appendChild(host);
		}

		this.state.container = host;
		this.state.anchor = anchor;
		this.state.active = true;

		this.engine.debug('plain.ensureHost', {
			created: true
		});
		return host;
	}

	// Compute a safe flush index for appending into DOM: keep trailing partial word out of DOM until a safe break.
	_findSafeFlushIndex(text) {
		if (!text) return 0;
		// Newline → always flush whole slice, but still avoid splitting an angle-like token
		if (text.indexOf('\n') !== -1 || text.indexOf('\r') !== -1) {
			if (/[<>]/.test(text)) this.engine.debug('plain.flushIdx.nl', {
				textLen: text.length
			});
			return this._retractIfInsideAngleToken(text, text.length);
		}

		const PLAIN = (this.engine.cfg && this.engine.cfg.STREAM && this.engine.cfg.STREAM.PLAIN) ? this.engine.cfg.STREAM.PLAIN : {};
		const LOOKBACK = (PLAIN.COHESION_LOOKBACK != null) ? PLAIN.COHESION_LOOKBACK : 96;
		const STICKY = (PLAIN.COHESION_STICKY_TAIL != null) ? PLAIN.COHESION_STICKY_TAIL : 8;
		const FLUSH_AT = (PLAIN.COHESION_FLUSH_AT_LEN != null) ? PLAIN.COHESION_FLUSH_AT_LEN : 512;

		if (text.length >= FLUSH_AT) {
			const at = Math.max(0, text.length - STICKY);
			if (/[<>]/.test(text)) this.engine.debug('plain.flushIdx.hard', {
				textLen: text.length,
				at
			});
			return this._retractIfInsideAngleToken(text, at);
		}

		const start = Math.max(0, text.length - LOOKBACK);
		for (let i = text.length - 1; i >= start; i--) {
			const ch = text[i];
			if (this._isSafeBreakChar(ch)) {
				if (/[<>]/.test(text)) this.engine.debug('plain.flushIdx.safe', {
					textLen: text.length,
					i,
					ch
				});
				return this._retractIfInsideAngleToken(text, i + 1);
			}
		}
		const at = Math.max(0, text.length - STICKY);
		if (/[<>]/.test(text)) this.engine.debug('plain.flushIdx.sticky', {
			textLen: text.length,
			at
		});
		return this._retractIfInsideAngleToken(text, at);
	}

	// Pick the proper parent for the plain streaming host:
	// - if there is a pending custom-markup wrapper, append inside it,
	// - otherwise append directly to the snapshot root.
	_choosePlainParent(snap) {
		try {
			if (!snap || !snap.querySelectorAll) return snap;
			const pending = snap.querySelectorAll('[data-cm][data-cm-pending="1"]');
			if (pending && pending.length) return pending[pending.length - 1];
		} catch (_) {}
		return snap;
	}

	// Prevent splitting inside angle-bracketed tokens like <think>, <tool>, </…>, <!…>, <?…>
	_retractIfInsideAngleToken(text, flushIdx) {
		const PLAIN = (this.engine.cfg && this.engine.cfg.STREAM && this.engine.cfg.STREAM.PLAIN) ? this.engine.cfg.STREAM.PLAIN : {};
		const ENABLED = (PLAIN.PROTECT_ANGLE_TOKENS !== false);
		if (!ENABLED) return flushIdx;
		if (!text || flushIdx <= 0 || flushIdx > text.length) return flushIdx;

		const LOOK = (PLAIN.ANGLE_LOOKBACK != null) ? PLAIN.ANGLE_LOOKBACK : 128;
		const from = Math.max(0, flushIdx - LOOK);
		const seg = text.slice(from, flushIdx);

		// Last '<' without a following '>' means we are still inside an opener like <think
		const lt = seg.lastIndexOf('<');
		if (lt !== -1 && seg.indexOf('>', lt + 1) === -1) {
			const next = seg.charAt(lt + 1);
			const looksLikeTag = !!next && (
				(next >= 'A' && next <= 'Z') ||
				(next >= 'a' && next <= 'z') ||
				next === '!' || next === '/' || next === '?'
			);
			if (looksLikeTag) return from + lt; // retract to '<'
		}

		// If the next char at flushIdx would start a '<X' opener, keep it in carry anyway
		if (flushIdx < text.length) {
			const ch = text.charAt(flushIdx),
				ch2 = text.charAt(flushIdx + 1);
			if (ch === '<' && ch2 && (
					(ch2 >= 'A' && ch2 <= 'Z') ||
					(ch2 >= 'a' && ch2 <= 'z') ||
					ch2 === '!' || ch2 === '/' || ch2 === '?'
				)) return flushIdx;
		}
		return flushIdx;
	}

	// Promote markdown inline in the tail when small and cheap; skip during long plain streaks.
	_plainMaybeInlineMarkdown(delta, force) {
		if (!this.state.active || !this.state.container || !this.state.anchor) return;
		if (this.state.suppressInline && !force) {
			// DEBUG
			this.engine.debug('plain.inline.skip.suppressed', {
				force
			});
			return;
		}

		// Read tuning knobs for plain streaming inline parsing.
		const PLAIN = (this.engine.cfg && this.engine.cfg.STREAM && this.engine.cfg.STREAM.PLAIN) ? this.engine.cfg.STREAM.PLAIN : {};
		const MIN_INTERVAL = (PLAIN.MD_MIN_INTERVAL_MS != null) ? PLAIN.MD_MIN_INTERVAL_MS : 120;
		const MIN_TAIL = (PLAIN.INLINE_MIN_CHARS != null) ? PLAIN.INLINE_MIN_CHARS : 64;
		const WINDOW_MAX = (PLAIN.WINDOW_MAX_CHARS != null) ? PLAIN.WINDOW_MAX_CHARS : 2048;
		const RESERVE_TAIL = (PLAIN.RESERVE_TAIL_CHARS != null) ? PLAIN.RESERVE_TAIL_CHARS : 256;

		const now = Utils.now();
		// Throttle how often we try to parse inline.
		if (!force && (now - (this.state.lastMDTs || 0)) < MIN_INTERVAL) {
			// DEBUG
			this.engine.debug('plain.inline.skip.throttle', {
				since: (now - (this.state.lastMDTs || 0)),
				MIN_INTERVAL
			});
			return;
		}

		// Take the tail text node and inspect it.
		const tn = this.state.anchor.previousSibling;
		if (!tn || tn.nodeType !== Node.TEXT_NODE) return;
		const text = tn.nodeValue || '';
		if (!text) return;

		// If "force" is set due to markdown+newline heuristic, we let full MD snapshot handle promotion.
		if (force) {
			this.engine.debug('plain.inline.skip.forceFull', {});
			return;
		}

		// If tail is too small and no newline, skip to save work.
		if (text.length < MIN_TAIL && (!delta || delta.indexOf('\n') === -1)) {
			// DEBUG
			this.engine.debug('plain.inline.skip.small', {
				textLen: text.length,
				MIN_TAIL
			});
			return;
		}

		// Quick trigger: only attempt if there is a known inline marker (precompiled).
		const candidate = (delta && this.engine._reMDInlineTrigger.test(delta)) || this.engine._reMDInlineTrigger.test(text);
		if (!candidate) {
			// DEBUG
			this.engine.debug('plain.inline.skip.noCandidate', {
				deltaHas: !!(delta && this.engine._reMDInlineTrigger.test(delta))
			});
			return;
		}

		// Keep the last part as raw tail, only promote the head to HTML.
		let cut = text.length;
		if (text.length > WINDOW_MAX) {
			const target = text.length - RESERVE_TAIL;
			const nl = text.lastIndexOf('\n', Math.max(0, target));
			if (nl >= 32) cut = nl + 1;
			else cut = Math.max(WINDOW_MAX, text.length - RESERVE_TAIL);
		}

		let head = text.slice(0, cut);
		let rest = text.slice(cut);

		// Avoid splitting in the middle of a word: if head ends with a word-char and rest starts with a word-char,
		// pull back to the last safe break char inside head.
		if (head && rest) {
			const last = head[head.length - 1];
			const first = rest[0];
			if (this._isWordChar(last) && this._isWordChar(first)) {
				let backCut = -1;
				const LOOKBACK = 96;
				const start = Math.max(0, head.length - LOOKBACK);
				for (let i = head.length - 1; i >= start; i--) {
					if (this._isSafeBreakChar(head[i])) {
						backCut = i + 1;
						break;
					}
				}
				if (backCut >= 0 && backCut < head.length) {
					rest = head.slice(backCut) + rest;
					head = head.slice(0, backCut);
				}
			}
		}

		// Render inline MD to HTML (fallback to escaping).
		let html = '';
		try {
			if (this.engine.renderer && typeof this.engine.renderer.renderInlineStreaming === 'function') {
				html = this.engine.renderer.renderInlineStreaming(head);
			} else if (this.engine.renderer && this.engine.renderer.MD_STREAM && typeof this.engine.renderer.MD_STREAM.renderInline === 'function') {
				html = this.engine.renderer.MD_STREAM.renderInline(head);
			} else {
				html = Utils.escapeHtml(head);
			}
		} catch (_) {
			html = Utils.escapeHtml(head);
		}

		// DEBUG
		this.engine.debug('plain.inline.promote', {
			headLen: head.length,
			restLen: rest.length,
			htmlLen: html.length
		});

		// Replace the head text by its HTML while keeping the remaining tail as raw text.
		try {
			// Reuse a single template to avoid many allocations.
			if (this.engine._tpl) {
				this.engine._tpl.innerHTML = html;
				const frag = document.createDocumentFragment();
				while (this.engine._tpl.content.firstChild) frag.appendChild(this.engine._tpl.content.firstChild);
				const host = this.state.container;
				host.insertBefore(frag, tn);
				tn.nodeValue = rest;
			} else {
				// Fallback if document/template is not available.
				const tpl = document.createElement('template');
				tpl.innerHTML = html;
				const frag = tpl.content;
				const host = this.state.container;
				host.insertBefore(frag, tn);
				tn.nodeValue = rest;
			}
		} catch (_) {}

		this.state.lastMDTs = now;
	}

}
