// ==========================================================================
// Stream engine
// ==========================================================================

// Precompiled, module-scoped regexes to avoid per-call allocations in hot paths.
const RE_SAFE_BREAK = /\s|[.,;:!?()\[\]{}'"«»„”“—–\-…>]/;
const RE_STRUCT_BOUNDARY = /\n(\n|[-*]\s|\d+\.\s|#{1,6}\s|>\s)/;
const RE_MD_INLINE_TRIGGER = /(\*\*|__|[_`]|~~|\[[^\]]+\]\([^)]+\))/;
const RE_LINE_END = /[\n\r]$/;

// StreamEngine manages streaming text and code rendering in the UI.
class StreamEngine {

	// Constructor: wire dependencies and initialize all streaming state.
	constructor(cfg, dom, renderer, math, highlighter, codeScroll, scrollMgr, raf, asyncer, logger) {
		// Store collaborators
		this.cfg = cfg;
		this.dom = dom;
		this.renderer = renderer;
		this.math = math;
		this.highlighter = highlighter;
		this.codeScroll = codeScroll;
		this.scrollMgr = scrollMgr;
		this.raf = raf;
		this.asyncer = asyncer;
		this.logger = logger || new Logger(cfg);

		// Rope-like buffer: streamBuf holds the materialized prefix; _sbParts keeps recent tail parts; _sbLen tracks their length.
		this.streamBuf = '';
		this._sbParts = [];
		this._sbLen = 0;

		// NOTE: materialize tail only when it grows large, to avoid frequent huge string copies.
		this._tailMaterializeAt = ((this.cfg && this.cfg.STREAM && (this.cfg.STREAM.MATERIALIZE_TAIL_AT_LEN | 0)) || 262144); // 256 KiB

		// Fence (code block) parsing state
		this.fenceOpen = false;
		this.fenceMark = '`';
		this.fenceLen = 3;
		this.fenceTail = '';
		this.fenceBuf = '';
		this.lastSnapshotTs = 0;
		this.nextSnapshotStep = cfg.PROFILE_TEXT.base;
		this.snapshotScheduled = false;
		this.snapshotRAF = 0;

		// Simple counters for currently open code stream
		this.codeStream = {
			open: false,
			lines: 0,
			chars: 0
		};
		this.activeCode = null;

		// Flags that control post-processing
		this.suppressPostFinalizePass = false;

		this._promoteScheduled = false;

		// Ensure first fence-open is materialized immediately when stream starts with code.
		this._firstCodeOpenSnapDone = false;

		// Streaming mode flag.
		this.isStreaming = false;

		// Tracks whether renderSnapshot injected a one-off synthetic EOL for parsing an open fence.
		this._lastInjectedEOL = false;

		this._customFenceSpecs = [];
		this._fenceCustom = null;

		// Plain streaming state for non-code text
		this.plain = {
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

		// Precompiled quick markdown detector (inline + common block markers)
		this._mdQuickRe = /(\*\*|__|~~|`|!\[|\[[^\]]+\]\([^)]+\)|^> |\n> |\n#{1,6}\s|\n[-*+]\s|\n\d+\.\s)/m;

		// Reuse compiled regex in hot paths (GC friendly).
		this._reSafeBreak = RE_SAFE_BREAK;
		this._reStructBoundary = RE_STRUCT_BOUNDARY;
		this._reMDInlineTrigger = RE_MD_INLINE_TRIGGER;
		this._reLineEnd = RE_LINE_END;

		// Reusable <template> for parsing small HTML snippets (avoids creating many templates).
		// Note: a single template is safe here because operations on it are serialized.
		this._tpl = (typeof document !== 'undefined') ? document.createElement('template') : null;

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
			return this._reSafeBreak.test(ch);
		};

		// DEBUG
		this._d('init', {
			materializeTailAt: this._tailMaterializeAt,
			hasTpl: !!this._tpl
		});
	}

	// Debug helper: write structured log lines for the stream engine.
	_d(tag, data) {
		try {
			const lg = this.logger || (this.cfg && this.cfg.logger) || (window.runtime && runtime.logger) || null;
			if (!lg || typeof lg.debug !== 'function') return;
			lg.debug_obj("STREAM", tag, data);
		} catch (_) {}
	}

	// Register custom fence (code block) open/close tokens.
	setCustomFenceSpecs(specs) {
		// Keep a shallow copy to avoid external mutation.
		this._customFenceSpecs = Array.isArray(specs) ? specs.slice() : [];
		// DEBUG
		this._d('customFence.set', {
			count: (this._customFenceSpecs || []).length
		});
	}

	// Append incoming chunk to the lightweight tail buffer.
	_appendChunk(s) {
		if (!s) return;
		// DEBUG
		this._d('chunk.append', {
			len: s.length,
			nl: Utils.countNewlines(s),
			head: String(s).slice(0, 160),
			tail: String(s).slice(-160),
			hasAngle: /[<>]/.test(String(s)),
			hasFenceToken: /```|~~~/.test(String(s))
		});
		// Store piece and increase length counter; join later to avoid frequent string copies.
		this._sbParts.push(s);
		this._sbLen += s.length;

		// NOTE: materialize tail only when it grows beyond the threshold to keep part count bounded.
		if (this._sbLen >= this._tailMaterializeAt) {
			this._materializeTail();
		}
	}

	// NOTE: materialize current tail parts into streamBuf only on demand (threshold/finish).
	_materializeTail() {
		// DEBUG
		this._d('tail.materialize', {
			streamBufLen: this.streamBuf.length,
			parts: this._sbParts.length,
			sbLen: this._sbLen
		});
		if (this._sbLen > 0) {
			this.streamBuf += (this._sbParts.length === 1 ? this._sbParts[0] : this._sbParts.join(''));
			this._sbParts.length = 0;
			this._sbLen = 0;
		}
	}

	// Return the current total streamed length (materialized + tail parts).
	getStreamLength() {
		return (this.streamBuf.length + this._sbLen);
	}

	// NOTE: Zero-copy: return full text without forcing a permanent concatenation into streamBuf.
	getStreamText() {
		// Join tail on the fly for the caller only.
		if (this._sbLen > 0) {
			return this.streamBuf + (this._sbParts.length === 1 ? this._sbParts[0] : this._sbParts.join(''));
		}
		return this.streamBuf;
	}

	// Compute delta since prevLen without materializing the whole buffer.
	// This avoids building large temporary strings when we only need the tail slice.
	getDeltaSince(prevLen) {
		// Fast bail-outs
		const total = this.getStreamLength();
		if (prevLen >= total) return '';
		const bufLen = this.streamBuf.length;

		// If prevLen is at or before the materialized prefix, delta is the whole current tail.
		if (prevLen <= bufLen) {
			if (this._sbLen === 0) return '';
			const out = (this._sbParts.length === 1 ? this._sbParts[0] : this._sbParts.join(''));
			// DEBUG (only if interesting)
			if (/[<>]/.test(out)) this._d('delta.since', {
				prevLen,
				deltaLen: out.length,
				head: out.slice(0, 80),
				tail: out.slice(-80)
			});
			return out;
		}

		// Otherwise delta starts inside the tail parts.
		let off = prevLen - bufLen;
		let out = null; // lazy array to minimize allocations
		for (let i = 0; i < this._sbParts.length; i++) {
			const p = this._sbParts[i];
			const plen = p.length;
			if (off >= plen) {
				off -= plen;
				continue;
			}
			const slice = off > 0 ? p.slice(off) : p;
			if (out === null) out = [slice];
			else out.push(slice);
			off = 0;
		}
		if (!out) return '';
		const ret = (out.length === 1 ? out[0] : out.join(''));
		// DEBUG (only if interesting)
		if (/[<>]/.test(ret)) this._d('delta.since', {
			prevLen,
			deltaLen: ret.length,
			head: ret.slice(0, 80),
			tail: ret.slice(-80)
		});
		return ret;
	}

	// Drop all buffers (materialized and tail).
	_clearStreamBuffer() {
		// DEBUG
		this._d('buf.clear', {
			streamBufLen: this.streamBuf.length,
			parts: this._sbParts.length,
			sbLen: this._sbLen
		});
		this.streamBuf = '';
		this._sbParts.length = 0;
		this._sbLen = 0;
	}

	// Plain helpers

	// Compute threshold (lines without Markdown) required to enable plain-text mode.
	_plainThreshold() {
		const STREAM = (this.cfg && this.cfg.STREAM) ? this.cfg.STREAM : {};
		const thr = (STREAM.PLAIN_ACTIVATE_AFTER_LINES != null) ? STREAM.PLAIN_ACTIVATE_AFTER_LINES : 10;
		return Math.max(1, thr | 0);
	}

	// Reset "plain text streaming" state.
	_plainReset() {
		this.plain.active = false;
		this.plain.container = null;
		this.plain.anchor = null;
		this.plain.lastMDTs = 0;
		this.plain.noMdNL = 0;
		this.plain.suppressInline = false;
		this.plain.forceFullMDOnce = false;
		this.plain.enabled = false;
		this.plain._carry = '';
		// DEBUG
		this._d('plain.reset', {});
	}

    // Ensure the plain text streaming host container is present and correctly placed.
	_plainEnsureContainer(snap) {
		// Reuse the existing container when still attached.
		if (this.plain.container && this.plain.container.isConnected && this.plain.anchor && this.plain.anchor.parentNode === this.plain.container) {
			// Ensure parent is correct (inside pending wrapper if any)
			const needParent = this._choosePlainParent(snap);
			if (needParent && this.plain.container.parentNode !== needParent) {
				try {
					needParent.appendChild(this.plain.container);
				} catch (_) {}
			}
			return this.plain.container;
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

		this.plain.container = host;
		this.plain.anchor = anchor;
		this.plain.active = true;

		this._d('plain.ensureHost', {
			created: true
		});
		return host;
	}

	// Compute a safe flush index for appending into DOM: keep trailing partial word out of DOM until a safe break.
	_findSafeFlushIndex(text) {
		if (!text) return 0;
		// Newline → always flush whole slice, but still avoid splitting an angle-like token
		if (text.indexOf('\n') !== -1 || text.indexOf('\r') !== -1) {
			if (/[<>]/.test(text)) this._d('plain.flushIdx.nl', {
				textLen: text.length
			});
			return this._retractIfInsideAngleToken(text, text.length);
		}

		const PLAIN = (this.cfg && this.cfg.STREAM && this.cfg.STREAM.PLAIN) ? this.cfg.STREAM.PLAIN : {};
		const LOOKBACK = (PLAIN.COHESION_LOOKBACK != null) ? PLAIN.COHESION_LOOKBACK : 96;
		const STICKY = (PLAIN.COHESION_STICKY_TAIL != null) ? PLAIN.COHESION_STICKY_TAIL : 8;
		const FLUSH_AT = (PLAIN.COHESION_FLUSH_AT_LEN != null) ? PLAIN.COHESION_FLUSH_AT_LEN : 512;

		if (text.length >= FLUSH_AT) {
			const at = Math.max(0, text.length - STICKY);
			if (/[<>]/.test(text)) this._d('plain.flushIdx.hard', {
				textLen: text.length,
				at
			});
			return this._retractIfInsideAngleToken(text, at);
		}

		const start = Math.max(0, text.length - LOOKBACK);
		for (let i = text.length - 1; i >= start; i--) {
			const ch = text[i];
			if (this._isSafeBreakChar(ch)) {
				if (/[<>]/.test(text)) this._d('plain.flushIdx.safe', {
					textLen: text.length,
					i,
					ch
				});
				return this._retractIfInsideAngleToken(text, i + 1);
			}
		}
		const at = Math.max(0, text.length - STICKY);
		if (/[<>]/.test(text)) this._d('plain.flushIdx.sticky', {
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
		const PLAIN = (this.cfg && this.cfg.STREAM && this.cfg.STREAM.PLAIN) ? this.cfg.STREAM.PLAIN : {};
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

    // Append a delta string into the plain text streaming host, managing safe boundaries and inline MD promotion.
	_plainAppendDelta(snap, delta) {
		if (!delta) return;
		const host = this._plainEnsureContainer(snap);

		let combined = (this.plain._carry || '') + String(delta);
		if (!combined) return;

		const flushIdx = this._findSafeFlushIndex(combined);
		let toAppend = combined.slice(0, flushIdx);
		let carryRemainder = combined.slice(flushIdx);

		// Do not push very short, unsafe heads that would split a word (no NL, 1–2 chars).
		const PLAIN = (this.cfg && this.cfg.STREAM && this.cfg.STREAM.PLAIN) ? this.cfg.STREAM.PLAIN : {};
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
			this.plain._carry = toAppend + carryRemainder;
			return;
		}

		this.plain._carry = carryRemainder;
		if (!toAppend) return;

		// Append into tail text node inside current host
		let tn = this.plain.anchor ? this.plain.anchor.previousSibling : null;
		if (!tn || tn.nodeType !== Node.TEXT_NODE || tn.parentNode !== host) {
			tn = document.createTextNode('');
			try {
				host.insertBefore(tn, this.plain.anchor);
			} catch (_) {
				host.appendChild(tn);
			}
		}
		tn.appendData(toAppend);

		// Let custom markup see the delta on the whole snapshot root (finalize closers fast).
		try {
			const CM = this.renderer && this.renderer.customMarkup;
			const MDinline = this.renderer ? (this.renderer.MD_STREAM || this.renderer.MD || null) : null;
			if (CM && typeof CM.maybeApplyStreamOnDelta === 'function') {
				CM.maybeApplyStreamOnDelta(snap, toAppend, MDinline);
			}
		} catch (_) {}

		this._plainMaybeInlineMarkdown(toAppend, false);
		this.scrollMgr.scheduleScroll(true);
	}

	// Promote markdown inline in the tail when small and cheap; skip during long plain streaks.
	_plainMaybeInlineMarkdown(delta, force) {
		if (!this.plain.active || !this.plain.container || !this.plain.anchor) return;
		if (this.plain.suppressInline && !force) {
			// DEBUG
			this._d('plain.inline.skip.suppressed', {
				force
			});
			return;
		}

		// Read tuning knobs for plain streaming inline parsing.
		const PLAIN = (this.cfg && this.cfg.STREAM && this.cfg.STREAM.PLAIN) ? this.cfg.STREAM.PLAIN : {};
		const MIN_INTERVAL = (PLAIN.MD_MIN_INTERVAL_MS != null) ? PLAIN.MD_MIN_INTERVAL_MS : 120;
		const MIN_TAIL = (PLAIN.INLINE_MIN_CHARS != null) ? PLAIN.INLINE_MIN_CHARS : 64;
		const WINDOW_MAX = (PLAIN.WINDOW_MAX_CHARS != null) ? PLAIN.WINDOW_MAX_CHARS : 2048;
		const RESERVE_TAIL = (PLAIN.RESERVE_TAIL_CHARS != null) ? PLAIN.RESERVE_TAIL_CHARS : 256;

		const now = Utils.now();
		// Throttle how often we try to parse inline.
		if (!force && (now - (this.plain.lastMDTs || 0)) < MIN_INTERVAL) {
			// DEBUG
			this._d('plain.inline.skip.throttle', {
				since: (now - (this.plain.lastMDTs || 0)),
				MIN_INTERVAL
			});
			return;
		}

		// Take the tail text node and inspect it.
		const tn = this.plain.anchor.previousSibling;
		if (!tn || tn.nodeType !== Node.TEXT_NODE) return;
		const text = tn.nodeValue || '';
		if (!text) return;

		// If "force" is set due to markdown+newline heuristic, we let full MD snapshot handle promotion.
		if (force) {
			this._d('plain.inline.skip.forceFull', {});
			return;
		}

		// If tail is too small and no newline, skip to save work.
		if (text.length < MIN_TAIL && (!delta || delta.indexOf('\n') === -1)) {
			// DEBUG
			this._d('plain.inline.skip.small', {
				textLen: text.length,
				MIN_TAIL
			});
			return;
		}

		// Quick trigger: only attempt if there is a known inline marker (precompiled).
		const candidate = (delta && this._reMDInlineTrigger.test(delta)) || this._reMDInlineTrigger.test(text);
		if (!candidate) {
			// DEBUG
			this._d('plain.inline.skip.noCandidate', {
				deltaHas: !!(delta && this._reMDInlineTrigger.test(delta))
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
			if (this.renderer && typeof this.renderer.renderInlineStreaming === 'function') {
				html = this.renderer.renderInlineStreaming(head);
			} else if (this.renderer && this.renderer.MD_STREAM && typeof this.renderer.MD_STREAM.renderInline === 'function') {
				html = this.renderer.MD_STREAM.renderInline(head);
			} else {
				html = Utils.escapeHtml(head);
			}
		} catch (_) {
			html = Utils.escapeHtml(head);
		}

		// DEBUG
		this._d('plain.inline.promote', {
			headLen: head.length,
			restLen: rest.length,
			htmlLen: html.length
		});

		// Replace the head text by its HTML while keeping the remaining tail as raw text.
		try {
			// Reuse a single template to avoid many allocations.
			if (this._tpl) {
				this._tpl.innerHTML = html;
				const frag = document.createDocumentFragment();
				while (this._tpl.content.firstChild) frag.appendChild(this._tpl.content.firstChild);
				const host = this.plain.container;
				host.insertBefore(frag, tn);
				tn.nodeValue = rest;
			} else {
				// Fallback if document/template is not available.
				const tpl = document.createElement('template');
				tpl.innerHTML = html;
				const frag = tpl.content;
				const host = this.plain.container;
				host.insertBefore(frag, tn);
				tn.nodeValue = rest;
			}
		} catch (_) {}

		this.plain.lastMDTs = now;
	}

	// Reset most of the engine state for a brand new stream.
	reset() {
		// DEBUG
		this._d('reset', {});
		this._clearStreamBuffer();
		this.fenceOpen = false;
		this.fenceMark = '`';
		this.fenceLen = 3;
		this.fenceTail = '';
		this.fenceBuf = '';
		this.lastSnapshotTs = 0;
		this.nextSnapshotStep = this.profile().base;
		this.snapshotScheduled = false;
		this.snapshotRAF = 0;
		this.codeStream = {
			open: false,
			lines: 0,
			chars: 0
		};
		this.activeCode = null;
		this.suppressPostFinalizePass = false;
		this._promoteScheduled = false;
		this._firstCodeOpenSnapDone = false;

		this._lastInjectedEOL = false;
		this._fenceCustom = null;

		this._plainReset();
	}

	// Convert active highlighted block back to plain text (when aborting).
	defuseActiveToPlain() {
		if (!this.activeCode || !this.activeCode.codeEl || !this.activeCode.codeEl.isConnected) return;
		const codeEl = this.activeCode.codeEl;
		// Merge frozen + tail into a single plain text content.
		const fullText = (this.activeCode.frozenEl?.textContent || '') + (this.activeCode.tailEl?.textContent || '');
		// DEBUG
		this._d('code.defuseActive', {
			fullLen: fullText.length
		});
		try {
			codeEl.textContent = fullText;
			codeEl.removeAttribute('data-highlighted');
			codeEl.classList.remove('hljs');
			codeEl.dataset._active_stream = '0';
			// Stop auto-follow on this code block.
			const st = this.codeScroll.state(codeEl);
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
					this.codeScroll.attachHandlers(codeEl);
				} catch (_) {}
				n++;
			});
			// DEBUG
			if (n) this._d('code.defuseOrphans', {
				count: n
			});
		} catch (e) {}
	}

	// Abort the current stream and reset state; optionally finalize code, clear buffers/UI, etc.
	abortAndReset(opts) {
		// Merge options with defaults.
		const o = Object.assign({
			finalizeActive: true,
			clearBuffer: true,
			clearMsg: false,
			defuseOrphans: true,
			reason: '',
			suppressLog: false
		}, (opts || {}));

		// DEBUG
		this._d('abort', o);

		// Cancel scheduled RAF tasks for this engine.
		try {
			this.raf.cancelGroup('StreamEngine');
		} catch (_) {}
		try {
			this.raf.cancel('SE:snapshot');
		} catch (_) {}
		this.snapshotScheduled = false;
		this.snapshotRAF = 0;

		// Finalize or defuse active code block if any.
		const hadActive = !!this.activeCode;
		try {
			if (this.activeCode) {
				if (o.finalizeActive === true) this.finalizeActiveCode();
				else this.defuseActiveToPlain();
			}
		} catch (e) {}

		// Clean up any orphan "active" blocks in the DOM.
		if (o.defuseOrphans) {
			try {
				this.defuseOrphanActiveBlocks();
			} catch (e) {}
		}

		// Optionally clear buffers and reset fence state.
		if (o.clearBuffer) {
			this._clearStreamBuffer();
			this.fenceOpen = false;
			this.fenceMark = '`';
			this.fenceLen = 3;
			this.fenceTail = '';
			this.fenceBuf = '';
			this.codeStream.open = false;
			this.codeStream.lines = 0;
			this.codeStream.chars = 0;
			window.__lastSnapshotLen = 0;
		}
		// Optionally clear current message UI.
		if (o.clearMsg === true) {
			try {
				this.dom.resetEphemeral();
			} catch (_) {}
		}

		this._plainReset();
	}

	// Return the active performance profile depending on whether code fence is open.
	profile() {
		return this.fenceOpen ? this.cfg.PROFILE_CODE : this.cfg.PROFILE_TEXT;
	}

	// Reset the adaptive budget/step for snapshots.
	resetBudget() {
		this.nextSnapshotStep = this.profile().base;
		// DEBUG
		this._d('budget.reset', {
			step: this.nextSnapshotStep
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
		let atLineStart = (preLen === 0) ? true : this._reLineEnd.test(prev);

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
							this._d('fence.open.custom', {
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
						this._d('fence.close.custom', {
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
							this._d('fence.open.std', {
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
								this._d('fence.close.std', {
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
		if (opened || closed) this._d('fence.state', {
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

	// Get or create the DOM root for message snapshots.
	getMsgSnapshotRoot(msg) {
		if (!msg) return null;
		let snap = msg.querySelector('.md-snapshot-root');
		if (!snap) {
			snap = document.createElement('div');
			snap.className = 'md-snapshot-root';
			msg.appendChild(snap);
			// DEBUG
			this._d('snapshot.root.create', {});
		}
		return snap;
	}

	// Quick check: does chunk contain a structural boundary worth snapshotting on?
	hasStructuralBoundary(chunk) {
		if (!chunk) return false;
		// New paragraph or common block marker means we may want to render now.
		return this._reStructBoundary.test(chunk);
	}

	// Decide whether we should schedule a snapshot for this chunk.
	shouldSnapshotOnChunk(chunk, chunkHasNL, hasBoundary) {
		const prof = this.profile();
		const now = Utils.now();
		// Avoid snapshots too frequently.
		if (this.activeCode && this.fenceOpen) return false;
		if ((now - this.lastSnapshotTs) < prof.minInterval) return false;
		if (hasBoundary) return true;

		const delta = Math.max(0, this.getStreamLength() - (window.__lastSnapshotLen || 0));
		if (this.fenceOpen) {
			// For code, prefer lines-based cadence.
			if (chunkHasNL && delta >= this.nextSnapshotStep) return true;
			return false;
		}
		// For text, snapshot when enough new content accumulated.
		if (delta >= this.nextSnapshotStep) return true;
		return false;
	}

	// If it's been long enough, schedule a "soft" (soon) snapshot.
	maybeScheduleSoftSnapshot(msg, chunkHasNL) {
		const prof = this.profile();
		if (this.activeCode && this.fenceOpen) return;
		if (this.fenceOpen && this.codeStream.lines < 1 && !chunkHasNL) return;
		const now = Utils.now();
		if ((now - this.lastSnapshotTs) >= prof.softLatency) {
			this._d('snapshot.soft.schedule', {
				latency: (now - this.lastSnapshotTs),
				soft: prof.softLatency
			});
			this.scheduleSnapshot(msg);
		}
	}

	// Schedule a snapshot render on the next frame (or force immediately).
	scheduleSnapshot(msg, force = false) {
		// Keep internal "scheduled" flag in sync with RAF scheduler.
		if (this.snapshotScheduled && !this.raf.isScheduled('SE:snapshot')) this.snapshotScheduled = false;
		if (!force) {
			if (this.snapshotScheduled) {
				this._d('snapshot.schedule.skip', {
					reason: 'alreadyScheduled'
				});
				return;
			}
			if (this.activeCode && this.fenceOpen) {
				this._d('snapshot.schedule.skip', {
					reason: 'activeCodeFenceOpen'
				});
				return;
			}
		} else {
			if (this.snapshotScheduled && this.raf.isScheduled('SE:snapshot')) {
				this._d('snapshot.schedule.skip', {
					reason: 'alreadyScheduled(forceCollide)'
				});
				return;
			}
		}
		this.snapshotScheduled = true;
		this._d('snapshot.schedule', {
			force,
			fenceOpen: this.fenceOpen,
			isStreaming: this.isStreaming
		});
		this.raf.schedule('SE:snapshot', () => {
			this.snapshotScheduled = false;
			const msg = this.getMsg(false, '');
			if (msg) this.renderSnapshot(msg);
		}, 'StreamEngine', 0);
	}

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
		this._d('code.ensureSplit', {
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
		if (this._lastInjectedEOL && parts.tailEl && parts.tailEl.textContent && parts.tailEl.textContent.endsWith('\n')) {
			parts.tailEl.textContent = parts.tailEl.textContent.slice(0, -1);
			this._lastInjectedEOL = false;
		}

		// Enable auto-follow scrolling for the active code block.
		const st = this.codeScroll.state(parts.codeEl);
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
		this._d('code.active.set', {
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
			this._d('code.rehydrate.plain', {
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
		this._d('code.rehydrate', {
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
			this._d('code.tail.append', {
				len: text.length,
				nl,
				head: text.slice(0, 80),
				tail: text.slice(-80)
			});
		}

		// Keep the viewport following the code tail.
		this.codeScroll.scheduleScroll(this.activeCode.codeEl, true, false);
	}

	// Apply budgets/limits and switch to plain streaming when too big or too long.
	enforceHLStopBudget() {
		if (!this.activeCode) return;
		// Global kill-switch.
		if (this.cfg.HL.DISABLE_ALL) {
			this.activeCode.haltHL = true;
			this.activeCode.plainStream = true;
			return;
		}
		const stop = (this.cfg.PROFILE_CODE.stopAfterLines | 0);
		const streamPlainLines = (this.cfg.PROFILE_CODE.streamPlainAfterLines | 0);
		const streamPlainChars = (this.cfg.PROFILE_CODE.streamPlainAfterChars | 0);
		const maxFrozenChars = (this.cfg.PROFILE_CODE.maxFrozenChars | 0);

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
			this._d('code.hl.budget.stop', {
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
			this._d('code.hl.budget.hardStop', {
				totalLines,
				stop
			});
		}
	}

	// Map common language aliases to canonical highlight.js language ids.
	_aliasLang(token) {
		const v = String(token || '').trim().toLowerCase();
		return this.highlighter.ALIAS[v] || v;
	}

	// Check if highlight.js knows this language.
	_isHLJSSupported(lang) {
		try {
			return !!(window.hljs && hljs.getLanguage && hljs.getLanguage(lang));
		} catch (_) {
			return false;
		}
	}

	// Detect language directive from the very first non-empty line (e.g., "language: python").
	_detectDirectiveLangFromText(text) {
		if (!text) return null;
		let s = String(text);
		// Strip BOM if present.
		if (s.charCodeAt(0) === 0xFEFF) s = s.slice(1);
		const lines = s.split(/\r?\n/);
		let i = 0;
		// Skip leading blank lines.
		while (i < lines.length && !lines[i].trim()) i++;
		if (i >= lines.length) return null;
		let first = lines[i].trim();
		// Normalize common directive forms.
		first = first.replace(/^\s*lang(?:uage)?\s*[:=]\s*/i, '').trim();
		let token = first.split(/\s+/)[0].replace(/:$/, '');
		if (!/^[A-Za-z][\w#+\-\.]{0,30}$/.test(token)) return null;

		let cand = this._aliasLang(token);
		const rest = lines.slice(i + 1).join('\n');
		if (!rest.trim()) return null;

		// Compute deletion range up to (and including) that directive line.
		let pos = 0,
			seen = 0;
		while (seen < i && pos < s.length) {
			const nl = s.indexOf('\n', pos);
			if (nl === -1) return null;
			pos = nl + 1;
			seen++;
		}
		let end = s.indexOf('\n', pos);
		if (end === -1) end = s.length;
		else end = end + 1;
		// DEBUG
		this._d('code.lang.directive.detect', {
			lang: cand,
			deleteUpto: end
		});
		return {
			lang: cand,
			deleteUpto: end
		};
	}

	// Update language class on code element.
	_updateCodeLangClass(codeEl, newLang) {
		try {
			Array.from(codeEl.classList).forEach(c => {
				if (c.startsWith('language-')) codeEl.classList.remove(c);
			});
		} catch (_) {}
		try {
			codeEl.classList.add('language-' + (newLang || 'plaintext'));
		} catch (_) {}
	}

	// Update code header label (if present in wrapper).
	_updateCodeHeaderLabel(codeEl, newLabel, newLangToken) {
		try {
			const wrap = codeEl.closest('.code-wrapper');
			if (!wrap) return;
			const span = wrap.querySelector('.code-header-lang');
			if (span) span.textContent = newLabel || (newLangToken || 'code');
			wrap.setAttribute('data-code-lang', newLangToken || '');
		} catch (_) {}
	}

	// If first line contains a "language:" directive, switch the block to that language immediately.
	maybePromoteLanguageFromDirective() {
		if (!this.activeCode || !this.activeCode.codeEl) return;
		if (this.activeCode.lang && this.activeCode.lang !== 'plaintext') return;

		// Combine frozen + tail to inspect early lines.
		const frozenTxt = this.activeCode.frozenEl ? this.activeCode.frozenEl.textContent : '';
		const tailTxt = this.activeCode.tailEl ? this.activeCode.tailEl.textContent : '';
		const combined = frozenTxt + tailTxt;
		if (!combined) return;

		// Detect and extract language directive.
		const det = this._detectDirectiveLangFromText(combined);
		if (!det || !det.lang) return;

		const newLang = det.lang;
		const newCombined = combined.slice(det.deleteUpto);

		try {
			// Rebuild split spans with directive removed.
			const codeEl = this.activeCode.codeEl;
			codeEl.innerHTML = '';
			const frozen = document.createElement('span');
			frozen.className = 'hl-frozen';
			const tail = document.createElement('span');
			tail.className = 'hl-tail';
			tail.textContent = newCombined;
			codeEl.appendChild(frozen);
			codeEl.appendChild(tail);
			this.activeCode.frozenEl = frozen;
			this.activeCode.tailEl = tail;
			this.activeCode.frozenLen = 0;
			this.activeCode.tailLines = Utils.countNewlines(newCombined);
			this.activeCode.linesSincePromote = 0;

			// Update language label/classes.
			this.activeCode.lang = newLang;
			this._updateCodeLangClass(codeEl, newLang);
			this._updateCodeHeaderLabel(codeEl, newLang, newLang);

			// Trigger immediate promotion so highlighting catches up.
			this._d('code.lang.directive.promote', {
				newLang,
				tailLen: newCombined.length
			});
			this.schedulePromoteTail(true);
		} catch (e) {}
	}

	// Convert a code text delta to highlighted HTML using hljs (or escape as fallback).
	highlightDeltaText(lang, text) {
		if (this.cfg.HL.DISABLE_ALL) return Utils.escapeHtml(text);
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
	schedulePromoteTail(force = false) {
		if (!this.activeCode || !this.activeCode.tailEl) return;
		if (this.activeCode.plainStream === true) return;
		if (this._promoteScheduled) return;
		this._promoteScheduled = true;
		this._d('code.promote.schedule', {
			force
		});
		this.raf.schedule('SE:promoteTail', () => {
			this._promoteScheduled = false;
			this._promoteTailWork(force);
		}, 'StreamEngine', 1);
	}

	// Worker: move a safe chunk of tail into frozen (highlighted) area.
	async _promoteTailWork(force = false) {
		if (!this.activeCode || !this.activeCode.tailEl) return;
		if (this.activeCode.plainStream === true) return;

		const now = Utils.now();
		const prof = this.cfg.PROFILE_CODE;
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
		const usePlain = this.activeCode.haltHL || this.activeCode.plainStream || !this._isHLJSSupported(this.activeCode.lang);
		let cut = -1;

		if (idx >= 0) cut = idx + 1;
		else if (usePlain) {
			// If highlighting is off, we can move big plain chunks even without newline.
			const PLAIN_PROMOTE_CHARS = this.cfg.PROFILE_CODE.minPlainPromoteChars || 8192;
			if (tailText0.length >= PLAIN_PROMOTE_CHARS || force) cut = tailText0.length;
		}

		if (cut <= 0) return;
		const delta = tailText0.slice(0, cut);
		if (!delta) return;

		// Enforce budgets before doing heavy work.
		this.enforceHLStopBudget();

		// Yield to keep UI responsive if we plan to run hljs.
		if (!usePlain) await this.asyncer.yield();

		// Verify the tail still starts with the expected delta (not changed by new chunks).
		if (!this.activeCode || !this.activeCode.tailEl) return;
		const tailNow = this.activeCode.tailEl.textContent || '';
		if (!tailNow.startsWith(delta)) {
			// Tail changed; try again later.
			this._d('code.promote.tailChanged', {
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
			if (this._tpl) {
				this._tpl.innerHTML = html;
				while (this._tpl.content.firstChild) this.activeCode.frozenEl.appendChild(this._tpl.content.firstChild);
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
		this._d('code.promote.done', {
			plain: usePlain,
			deltaLen: delta.length,
			promotedLines,
			frozenLen: this.activeCode.frozenLen,
			tailLenNow: (this.activeCode.tailEl.textContent || '').length
		});
	}

	// Normalize text for stable fingerprint: unify EOLs, drop single trailing newline, strip BOM.
	_normTextForFP(s) {
		if (!s) return '';
		let t = String(s);
		if (t.charCodeAt(0) === 0xFEFF) t = t.slice(1);
		t = t.replace(/\r\n?/g, '\n');
		if (t.endsWith('\n')) t = t.slice(0, -1);
		return t;
	}

	// Lightweight FNV-1a 32-bit hash for short keys.
	_hash32FNV(str) {
		let h = 0x811c9dc5 >>> 0;
		for (let i = 0; i < str.length; i++) {
			h ^= str.charCodeAt(i);
			h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
		}
		return ('00000000' + h.toString(16)).slice(-8);
	}

	// Extract canonical language token from code element class.
	_codeLangFromEl(codeEl) {
		try {
			const cls = Array.from(codeEl.classList).find(c => c.startsWith('language-')) || 'language-plaintext';
			return (cls.replace('language-', '') || 'plaintext');
		} catch (_) {
			return 'plaintext';
		}
	}

	// Build stable fp key from element (lang | normLen | hash(normText)).
	_fpKeyFromCodeEl(codeEl) {
		try {
			const lang = this._codeLangFromEl(codeEl);
			const norm = this._normTextForFP(codeEl.textContent || '');
			return `${lang}|${norm.length}|${this._hash32FNV(norm)}`;
		} catch (_) {
			return '';
		}
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
		this._d('code.finalize.begin', {
			lang: ac.lang,
			frozenLen: ac.frozenLen,
			tailLen: (ac.tailEl ? (ac.tailEl.textContent || '').length : 0),
			plainStream: !!ac.plainStream
		});

		// Preserve current scroll position relative to bottom
		const fromBottomBefore = Math.max(0, codeEl.scrollHeight - codeEl.clientHeight - codeEl.scrollTop);
		const wasNearBottom = this.codeScroll.isNearBottomEl(codeEl, this.cfg.CODE_SCROLL.NEAR_MARGIN_PX);

		// Gather only what we really need; DO NOT serialize large frozen HTML to string
		const tailTXT = ac.tailEl ? (ac.tailEl.textContent || '') : '';

		// Decide final rendering mode
		const canHL = !this.cfg.HL.DISABLE_ALL && !ac.plainStream && this._isHLJSSupported(ac.lang);

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
					if (this._tpl) {
						this._tpl.innerHTML = tailHTML;
						while (this._tpl.content.firstChild) frag.appendChild(this._tpl.content.firstChild);
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
		const st = this.codeScroll.state(codeEl);
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
		this.codeScroll.scheduleScroll(codeEl, false, true);

		// We already produced a final highlighted block when possible – no need to enqueue hljs again.
		// Keep a suppression flag for math and other post passes consistent with previous behavior.
		this.suppressPostFinalizePass = true;

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
		this._d('code.finalize.end', {});
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
			const limit = (this.cfg.STREAM && this.cfg.STREAM.PRESERVE_CODES_MAX) || 200;
			if (newCodesPre.length > limit || oldCodes.length > limit) return;

			// DEBUG
			this._d('codes.preserve.scan', {
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
				if (this.activeCode && el === this.activeCode.codeEl) continue;
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
								this.codeScroll.attachHandlers(oldEl);
								if (!oldEl.getAttribute('data-highlighted')) oldEl.setAttribute('data-highlighted', 'yes');
								const st = this.codeScroll.state(oldEl);
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
							this.codeScroll.attachHandlers(oldEl);
							if (!oldEl.getAttribute('data-highlighted')) oldEl.setAttribute('data-highlighted', 'yes');
							const st = this.codeScroll.state(oldEl);
							st.autoFollow = false;
						} catch (_) {}
					}
					if (!arr2.length) map.delete(attrKey);
				}
			}
		} catch (e) {}
	}

	// Ensure "just finalized" code blocks snap to bottom once scrolling finishes.
	_ensureSplitContainers(codeEl) {
		try {
			const scope = codeEl || document;
			const nodes = scope.querySelectorAll('pre code[data-just-finalized="1"]');
			if (!nodes || !nodes.length) return;
			nodes.forEach((codeEl) => {
				this.codeScroll.scheduleScroll(codeEl, false, true);
				// NOTE: use a primitive key; do not capture DOM in scheduler key object
				const wrap = codeEl.closest('.code-wrapper');
				const idx = wrap ? (wrap.getAttribute('data-index') || '') : '';
				const key = `JF:forceBottom#${idx}`;
				this.raf.schedule(key, () => {
					this.codeScroll.scrollToBottom(codeEl, false, true);
					try {
						codeEl.dataset.justFinalized = '0';
					} catch (_) {}
				}, 'CodeScroll', 2);
			});
		} catch (_) {}
	}

	// Similar helper: ensure finalized blocks end up at bottom (variant used after patching).
	_ensureBottomForJustFinalized(root) {
		try {
			const scope = root || document;
			const nodes = scope.querySelectorAll('pre code[data-just-finalized="1"]');
			if (!nodes || !nodes.length) return;
			nodes.forEach((codeEl) => {
				// NOTE: use a primitive key; do not capture DOM in scheduler key object
				const wrap = codeEl.closest('.code-wrapper');
				const idx = wrap ? (wrap.getAttribute('data-index') || '') : '';
				const key = `JF:ensureBottom#${idx}`;
				this.codeScroll.scheduleScroll(codeEl, false, true);
				this.raf.schedule(key, () => {
					this.codeScroll.scrollToBottom(codeEl, false, true);
					try {
						codeEl.dataset.justFinalized = '0';
					} catch (_) {}
				}, 'CodeScroll', 2);
			});
		} catch (_) {}
	}

	// Kick the engine when tab becomes visible again or layout changed.
	kickVisibility() {
		const msg = this.getMsg(false, '');
		if (!msg) return;
		// If code is open but activeCode got lost, force a snapshot to recover.
		if (this.codeStream.open && !this.activeCode) {
			this._d('kick.visibility', {
				reason: 'codeStreamOpenNoActive'
			});
			this.scheduleSnapshot(msg, true);
			return;
		}
		// If we have unseen data in buffer, render it now.
		const needSnap = (this.getStreamLength() !== (window.__lastSnapshotLen || 0));
		if (needSnap) {
			this._d('kick.visibility', {
				reason: 'bufferDelta'
			});
			this.scheduleSnapshot(msg, true);
		}
		// If code is active, keep promoting/highlighting.
		if (this.activeCode && this.activeCode.codeEl) {
			this.codeScroll.scheduleScroll(this.activeCode.codeEl, true, false);
			this.schedulePromoteTail(true);
		}
	}

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

			const valid = (t) => !!t && t !== 'plaintext' && this._isHLJSSupported(t);

			// Prefer current explicit token, else previous language, else sticky fallback.
			let finalTok = '';
			if (valid(tokNow)) finalTok = tokNow;
			else if (valid(prev)) finalTok = prev;
			else if (valid(sticky)) finalTok = sticky;

			if (finalTok) {
				this._updateCodeLangClass(newAC.codeEl, finalTok);
				this._updateCodeHeaderLabel(newAC.codeEl, finalTok, finalTok);
				try {
					wrap.setAttribute('data-code-lang', finalTok);
				} catch (_) {}
				try {
					wrap.setAttribute('data-lang-sticky', finalTok);
				} catch (_) {}
				newAC.lang = finalTok;
				// DEBUG
				this._d('code.header.stabilize', {
					finalTok
				});
			} else {
				// Avoid super short labels like "c" if we can't validate them.
				if (span && curLabel && curLabel.length < 3) span.textContent = 'code';
			}
		} catch (_) {}
	}

	// Patch the snapshot root with minimal DOM changes (preserve stable nodes).
	_patchSnapshotRoot(snap, frag) {
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
				this._d('snapshot.patch.first', {
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
			this._d('snapshot.patch', {
				oldCount: aLen,
				newCount: bLen,
				removed: (removeEnd - removeStart),
				inserted: (bLen - j - i)
			});

		} catch (_) {
			// Fallback: replace everything.
			try {
				snap.replaceChildren(frag);
				this._d('snapshot.patch.replaceAll', {});
			} catch (__) {}
		}
	}

	// Quick MD detectors

	// Check if a chunk likely contains inline or block markdown markers.
	_chunkHasMarkdown(s) {
		try {
			return this._mdQuickRe.test(String(s || ''));
		} catch (_) {
			return false;
		}
	}

	// Ask custom markup if there are any stream open tokens in the chunk.
	_chunkHasCustomOpeners(s) {
		try {
			const CM = this.renderer && this.renderer.customMarkup;
			if (!CM || typeof CM.hasAnyStreamOpenToken !== 'function') return false;
			return CM.hasAnyStreamOpenToken(String(s || ''));
		} catch (_) {
			return false;
		}
	}

	// Render a snapshot of the current buffer: either plain streaming or full markdown.
	renderSnapshot(msg) {
		const streaming = !!this.isStreaming;
		const snap = this.getMsgSnapshotRoot(msg);
		if (!snap) return;

		// If nothing changed and no open code, just update timestamps and return.
		const prevLen = (window.__lastSnapshotLen || 0);
		const curLen = this.getStreamLength();
		if (!this.fenceOpen && !this.activeCode && curLen === prevLen) {
			this.lastSnapshotTs = Utils.now();
			return;
		}

		// Decide plain vs full-MD path before materializing big strings.
		const forceFull = !!this.plain.forceFullMDOnce;
		// IMPORTANT: use plain path only after threshold and only when enabled
		const streamingPlain = streaming && !this.fenceOpen && !forceFull && this.plain.enabled;

		// DEBUG
		this._d('snapshot.begin', {
			streaming,
			fenceOpen: this.fenceOpen,
			streamingPlain,
			forceFull,
			prevLen,
			curLen
		});

		if (streamingPlain) {
			// Fast path: compute delta without materializing the full buffer.
			const delta = this.getDeltaSince(prevLen);
			this._plainAppendDelta(snap, delta);

			// Bookkeeping for pacing and next snapshot.
			window.__lastSnapshotLen = curLen;
			this.lastSnapshotTs = Utils.now();

			const prof = this.profile();
			if (prof.adaptiveStep) {
				const maxStep = this.cfg.STREAM.SNAPSHOT_MAX_STEP || 8000;
				this.nextSnapshotStep = Math.min(Math.ceil(this.nextSnapshotStep * prof.growth), maxStep);
			} else {
				this.nextSnapshotStep = prof.base;
			}

			this.scrollMgr.scheduleScroll(true);
			this.scrollMgr.fabFreezeUntil = Utils.now() + this.cfg.FAB.TOGGLE_DEBOUNCE_MS;
			this.scrollMgr.scheduleScrollFabUpdate();

			this._d('snapshot.end.plain', {
				nextStep: this.nextSnapshotStep
			});
			return;
		}

		// Non-plain (full MD streaming or final)
		if (forceFull) this.plain.forceFullMDOnce = false;

		// Materialize buffer for rendering (zero-copy: see getStreamText()).
		let allText = this.getStreamText();

		// When switching away from plain streaming, drop any pending carry (full snapshot re-renders everything).
		this.plain._carry = '';

		// If a code fence is open, but buffer ends without EOL, append synthetic EOL so parser sees the line.
		const needSyntheticEOL = (this.fenceOpen && !/[\r\n]$/.test(allText));
		this._lastInjectedEOL = !!needSyntheticEOL;
		let src = needSyntheticEOL ? (allText + '\n') : allText;

		// DEBUG (only if interesting)
		if (/[<>]/.test(src)) this._d('snapshot.full.src', {
			len: src.length,
			head: src.slice(0, 120),
			tail: src.slice(-120),
			injectedEOL: needSyntheticEOL
		});

		// Produce a DOM fragment from renderer (stream or final flavor).
		let frag = null;
		if (streaming) frag = this.renderer.renderStreamingSnapshotFragment(src);
		else frag = this.renderer.renderFinalSnapshotFragment(src);

		// Let custom markup post-process the fragment if enabled.
		try {
			if (this.renderer && this.renderer.customMarkup && this.renderer.customMarkup.hasStreamRules()) {
				const MDinline = this.renderer.MD_STREAM || this.renderer.MD || null;
				this.renderer.customMarkup.applyStream(frag, MDinline);
			}
		} catch (_) {}

		// Try to reuse stable code blocks to reduce flicker/work.
		this.preserveStableClosedCodes(snap, frag, this.fenceOpen === true);
		// Minimal DOM patch to update only changed middle section.
		this._patchSnapshotRoot(snap, frag);

		// Micro highlight: highlight one small visible code block immediately to avoid a plain-text flash.
		try {
			if (this.highlighter && typeof this.highlighter.microHighlightNow === 'function') {
				this.highlighter.microHighlightNow(snap, {
					maxCount: 1,
					budgetMs: 4
				}, this.activeCode);
			}
		} catch (_) {}

		// Restore any collapsed code UI and ensure finalized blocks are scrolled properly.
		this.renderer.restoreCollapsedCode(snap);
		this._ensureBottomForJustFinalized(snap);

		// If code fence is open, re-create active streaming code target.
		const prevAC = this.activeCode;
		if (this.fenceOpen) {
			const newAC = this.setupActiveCodeFromSnapshot(snap);
			if (prevAC && newAC) this.rehydrateActiveCode(prevAC, newAC);
			// Run stabilization even for the first snapshot (prevAC may be null).
			this.stabilizeHeaderLabel(prevAC || null, newAC || null);
			this.activeCode = newAC || null;
		} else {
			this.activeCode = null;
		}

		// Initialize scroll handlers for code blocks when outside of code streaming.
		if (!this.fenceOpen) {
			this.codeScroll.initScrollableBlocks(snap);
		}

		// Observe new code blocks for highlighting; defer the last one while streaming.
		this.highlighter.observeNewCode(
			snap, {
				deferLastIfStreaming: true,
				minLinesForLast: this.cfg.PROFILE_CODE.minLinesForHL,
				minCharsForLast: this.cfg.PROFILE_CODE.minCharsForHL
			},
			this.activeCode
		);

		// Also watch code inside message boxes that may appear.
		this.highlighter.observeMsgBoxes(snap, (box) => {
			this.highlighter.observeNewCode(
				box, {
					deferLastIfStreaming: true,
					minLinesForLast: this.cfg.PROFILE_CODE.minLinesForHL,
					minCharsForLast: this.cfg.PROFILE_CODE.minCharsForHL
				},
				this.activeCode
			);
			this.codeScroll.initScrollableBlocks(box);
		});

		// Schedule math rendering depending on math mode.
		const mm = getMathMode();
		if (!this.suppressPostFinalizePass) {
			if (mm === 'idle') this.math.schedule(snap);
			else if (mm === 'always') this.math.schedule(snap, 0, true);
		}

		// If we are streaming code, attach scroll handlers and keep following.
		if (this.fenceOpen && this.activeCode && this.activeCode.codeEl) {
			this.codeScroll.attachHandlers(this.activeCode.codeEl);
			this.codeScroll.scheduleScroll(this.activeCode.codeEl, true, false);
		} else if (!this.fenceOpen) {
			this.codeScroll.initScrollableBlocks(snap);
		}

		// Update counters and adaptive step.
		window.__lastSnapshotLen = this.getStreamLength();
		this.lastSnapshotTs = Utils.now();

		const prof = this.profile();
		if (prof.adaptiveStep) {
			const maxStep = this.cfg.STREAM.SNAPSHOT_MAX_STEP || 8000;
			this.nextSnapshotStep = Math.min(Math.ceil(this.nextSnapshotStep * prof.growth), maxStep);
		} else {
			this.nextSnapshotStep = prof.base;
		}

		// Keep the viewport and FAB updated.
		this.scrollMgr.scheduleScroll(true);
		this.scrollMgr.fabFreezeUntil = Utils.now() + this.cfg.FAB.TOGGLE_DEBOUNCE_MS;
		this.scrollMgr.scheduleScrollFabUpdate();

		// Clear one-time suppression flag if set.
		if (this.suppressPostFinalizePass) this.suppressPostFinalizePass = false;

		// NOTE: drop local big references ASAP
		frag = null;
		src = null;
		allText = null;

		// DEBUG
		this._d('snapshot.end.full', {
			nextStep: this.nextSnapshotStep,
			fenceOpen: this.fenceOpen,
			hasActiveCode: !!this.activeCode
		});
	}

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

			const lang = this._codeLangFromEl(codeEl);
			wrap.setAttribute('data-code-lang', lang);

			const norm = this._normTextForFP(txt);
			const fp = `${lang}|${norm.length}|${this._hash32FNV(norm)}`;
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
				this._updateCodeLangClass(codeEl, langTok);
			}
			// Do not recompute data-fp or head/tail here to avoid serializing the whole code.
			// Existing attributes remain valid enough for reuse + scanning.
		} catch (_) {}
	}

	// Get or create the message element used for streaming output.
	getMsg(create, name_header) {
		return this.dom.getStreamMsg(create, name_header);
	}

	// Start a new stream: clear output, reset state, and scroll to bottom.
	beginStream(chunk = false) {
		this.isStreaming = true;
		// DEBUG
		this._d('stream.begin', {
			chunk
		});
		// Hide loading spinner if this call corresponds to first chunk.
		if (chunk) {
		    try {
		        runtime.loading.hide();
		    } catch (_) {}
		}
		this.scrollMgr.userInteracted = false;
		this.dom.clearOutput();
		this.reset();
		this.scrollMgr.forceScrollToBottomImmediate();
		this.scrollMgr.scheduleScroll();
	}

	// Finish the stream: render final snapshot, finalize code, flush highlighting, and clean up.
	endStream() {
		this.isStreaming = false;
		const msg = this.getMsg(false, '');
		if (msg) this.renderSnapshot(msg);

		// Cancel any scheduled tasks related to streaming.
		this.snapshotScheduled = false;
		try {
			this.raf.cancel('SE:snapshot');
		} catch (_) {}
		try {
			this.raf.cancelGroup('StreamEngine');
		} catch (_) {}
		try {
			this.raf.cancelGroup('CodeScroll');
		} catch (_) {}
		try {
			this.raf.cancelGroup('ScrollMgr');
		} catch (_) {}

		this.snapshotRAF = 0;

		// If there was an active code block, finalize it now.
		const hadActive = !!this.activeCode;
		if (this.activeCode) this.finalizeActiveCode();

		// If not, flush any remaining highlight queue and render math once.
		if (!hadActive) {
			if (this.highlighter.hlQueue && this.highlighter.hlQueue.length) {
				this.highlighter.flush(this.activeCode);
			}
			const snap = msg ? this.getMsgSnapshotRoot(msg) : null;
			if (snap) this.math.renderAsync(snap);
		}

		// Reset buffers and flags.
		this._clearStreamBuffer();

		this.fenceOpen = false;
		this.codeStream.open = false;
		this.activeCode = null;
		this.lastSnapshotTs = Utils.now();
		this.suppressPostFinalizePass = false;

		// Reset plain state to default for next sessions.
		this._plainReset();

		// DEBUG
		this._d('stream.end', {
			hadActive
		});
	}

	// If custom markup has openers in the chunk (especially at start), trigger early snapshot.
	_maybeEagerSnapshotForCustomOpeners(msg, chunkStr) {
		try {
			const CM = this.renderer && this.renderer.customMarkup;
			if (!CM || !CM.hasStreamRules()) return;
			if (this.fenceOpen || this.codeStream.open) return;

			// For the very first snapshot, check if the buffered head already starts with an opener.
			const isFirstSnapshot = ((window.__lastSnapshotLen || 0) === 0);

			if (isFirstSnapshot) {
				let head;
				try {
					head = this.getStreamText();
				} catch (_) {
					head = String(chunkStr || '');
				}
				if (CM.hasStreamOpenerAtStart(head)) {
					this._d('snapshot.eager.custom', {
						reason: 'headHasOpener'
					});
					this.scheduleSnapshot(msg, true);
					return;
				}
			}

			// Otherwise, check current chunk for any open token.
			const rules = (CM.getRules() || []).filter(r => r && r.stream && typeof r.open === 'string');
			if (rules.length && CM.hasAnyOpenToken(String(chunkStr || ''), rules)) {
				this._d('snapshot.eager.custom', {
					reason: 'chunkHasOpener'
				});
				this.scheduleSnapshot(msg);
			}
		} catch (_) {}
	}

	// Main entry: accept a chunk for a given "name_header" and update the view incrementally.
	applyStream(name_header, chunk, alreadyBuffered = false) {
		// If there is no active code and fences are closed, defuse any stray active blocks in DOM.
		if (!this.activeCode && !this.fenceOpen) {
			try {
				if (document.querySelector('pre code[data-_active_stream="1"]')) this.defuseOrphanActiveBlocks();
			} catch (_) {}
		}
		// Re-sync scheduled flag with RAF state.
		if (this.snapshotScheduled && !this.raf.isScheduled('SE:snapshot')) this.snapshotScheduled = false;

		const msg = this.getMsg(true, name_header);
		if (!msg || !chunk) return;
		const s = String(chunk);

		// DEBUG (only if interesting)
		if (/[<>]/.test(s)) {
			this._d('apply.chunk', {
				len: s.length,
				nl: Utils.countNewlines(s),
				head: s.slice(0, 120),
				tail: s.slice(-120)
			});
		}

		// Buffer the chunk unless caller says it's already buffered (recursive tail call case).
		if (!alreadyBuffered) this._appendChunk(s);

		// Update fence state based on the new text.
		const change = this.updateFenceHeuristic(s);
		const nlCount = Utils.countNewlines(s);
		const chunkHasNL = nlCount > 0;

		// If no fence opened and we are outside code, check if custom openers request early snapshot.
		if (!change.opened && !this.fenceOpen) {
			this._maybeEagerSnapshotForCustomOpeners(msg, s);
		}

		// Plain vs full-MD decision management (non-code)
		if (!this.fenceOpen && !this.codeStream.open) {
			const mdPresent = this._chunkHasMarkdown(s) || this._chunkHasCustomOpeners(s) || change.opened;
			const thr = this._plainThreshold();

			if (mdPresent) {
				// Markdown seen → reset counters and exit plain mode if active.
				if (this.plain.noMdNL !== 0) {
					this._d('apply.plain.resetOnMD', { noMdNL: this.plain.noMdNL });
				}
				this.plain.noMdNL = 0;

				if (this.plain.enabled) {
					// Leave plain mode and force one full snapshot to "re-sync" elegant rendering.
					this.plain.enabled = false;
					this.plain.suppressInline = false;
					this.plain.forceFullMDOnce = true;
					this._d('apply.plain.disableOnMD', {});
					this.scheduleSnapshot(msg, true);
				}
			} else if (chunkHasNL) {
				// No markdown in this chunk and we got newlines → count "plain lines"
				this.plain.noMdNL += nlCount;

				if (!this.plain.enabled && this.plain.noMdNL >= thr) {
					// Threshold reached → enter fully plain-text mode
					this.plain.enabled = true;
					this.plain.suppressInline = true; // fully plain-text (no inline markdown upgrades)
					this._d('apply.plain.enable', { noMdNL: this.plain.noMdNL, thr });
					// Switch to plain path soon
					this.scheduleSnapshot(msg);
				}
			}
		}

		// Track if we just materialized the first code-open snapshot synchronously.
		let didImmediateOpenSnap = false;

		// If a fence opened in this chunk, mark code stream active and try to snapshot soon.
		if (change.opened) {
			this.codeStream.open = true;
			this.codeStream.lines = 0;
			this.codeStream.chars = 0;
			this.resetBudget();
			this._d('code.open', {});
			this.scheduleSnapshot(msg);

			// Special case: if the message is empty and we just opened, render immediately once.
			if (!this._firstCodeOpenSnapDone && !this.activeCode && ((window.__lastSnapshotLen || 0) === 0)) {
				try {
					this.renderSnapshot(msg);
					try {
						this.raf.cancel('SE:snapshot');
					} catch (_) {}
					this.snapshotScheduled = false;
					this._firstCodeOpenSnapDone = true;
					didImmediateOpenSnap = true;
					this._d('code.open.immediateSnap', {});
				} catch (_) {}
			}
		}

		// If we are inside a code block stream, feed text into the active code tail or wait for a snapshot.
		if (this.codeStream.open) {
			this.codeStream.lines += nlCount;
			this.codeStream.chars += s.length;

			if (this.activeCode && this.activeCode.codeEl && this.activeCode.codeEl.isConnected) {
				// Split current chunk if it also contains the closing fence.
				let partForCode = s;
				let remainder = '';

				if (didImmediateOpenSnap) partForCode = '';
				else if (change.closed && change.splitAt >= 0 && change.splitAt <= s.length) {
					partForCode = s.slice(0, change.splitAt);
					remainder = s.slice(change.splitAt);
				}

				// Append code text to the tail and update counters/promotions.
				if (partForCode) {
					this.appendToActiveTail(partForCode);
					this.activeCode.lines += Utils.countNewlines(partForCode);

					this.maybePromoteLanguageFromDirective();
					this.enforceHLStopBudget();

					const tailLenNow = (this.activeCode.tailEl.textContent || '').length;
					const hasNL = partForCode.indexOf('\n') >= 0;

					// Schedule promotion when we have a newline or enough chars.
					if (!this.activeCode.plainStream) {
						const HL_MIN = this.cfg.PROFILE_CODE.minCharsForHL;
						if (hasNL || tailLenNow >= HL_MIN) this.schedulePromoteTail(false);
					}
				}
				// Keep viewport and FAB updated while streaming code.
				this.scrollMgr.scrollFabUpdateScheduled = false;
				this.scrollMgr.scheduleScroll(true);
				this.scrollMgr.fabFreezeUntil = Utils.now() + this.cfg.FAB.TOGGLE_DEBOUNCE_MS;
				this.scrollMgr.scheduleScrollFabUpdate();

				// If this chunk closed the fence, finalize code and process any remainder as normal text.
				if (change.closed) {
					this._d('code.close', {
						remainderLen: remainder.length
					});
					this.finalizeActiveCode();
					this.codeStream.open = false;
					this.resetBudget();
					// Force immediate full snapshot to avoid any transient plain rendering
					this.plain.forceFullMDOnce = true;
					this.scheduleSnapshot(msg, true);
					if (remainder && remainder.length) {
						this.applyStream(name_header, remainder, true);
					}
				}
				return;
			} else {
				// If code just opened but we have not created activeCode yet, force a snapshot once enough content arrives.
				if (!this.activeCode && (this.codeStream.lines >= 2 || this.codeStream.chars >= 80)) {
					this._d('code.awaitActive.forceSnap', {
						lines: this.codeStream.lines,
						chars: this.codeStream.chars
					});
					this.scheduleSnapshot(msg, true);
					return;
				}
				// If code closed without an active code element (rare), schedule a snapshot to reflect closure.
				// Outside code streaming
				if (change.closed) {
					this.codeStream.open = false;
					this.resetBudget();
					this._d('code.closed.outside', {});
					this.plain.forceFullMDOnce = true;
					this.scheduleSnapshot(msg, true);
				} else {
					const boundary = this.hasStructuralBoundary(s);
					if (this.shouldSnapshotOnChunk(s, chunkHasNL, boundary)) {
						this._d('snapshot.decide', {
							reason: 'boundary/step'
						});
						this.scheduleSnapshot(msg);
					} else {
						this.maybeScheduleSoftSnapshot(msg, chunkHasNL);
					}
				}
				return;
			}
		}

		// Outside code streaming: consider snapshotting or soft scheduling based on boundaries/size.
		if (change.closed) {
			this.codeStream.open = false;
			this.resetBudget();
			this._d('code.closed.outside', {});
			this.scheduleSnapshot(msg);
		} else {
			const boundary = this.hasStructuralBoundary(s);
			if (this.shouldSnapshotOnChunk(s, chunkHasNL, boundary)) {
				this._d('snapshot.decide', {
					reason: 'boundary/step'
				});
				this.scheduleSnapshot(msg);
			} else {
				this.maybeScheduleSoftSnapshot(msg, chunkHasNL);
			}
		}
	}
}