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

	// ========================================
	// Composition
	// ========================================

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

		// Fence (code block) parsing state

		// Flags that control post-processing
		this.suppressPostFinalizePass = false;

		// Ensure first fence-open is materialized immediately when stream starts with code.
		this._firstCodeOpenSnapDone = false;

		// Streaming mode flag.
		this.isStreaming = false;

		// Tracks whether renderSnapshot injected a one-off synthetic EOL for parsing an open fence.
		this._lastInjectedEOL = false;

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

		this.buffer = new StreamBuffer(this.cfg, (tag, data) => this.debug(tag, data));
		this.plain = new StreamPlain(this);
		this.reasoning = new StreamReasoning(this);
		this.fences = new StreamFences(this);
		this.code = new StreamCode(this);
		this.language = new StreamLanguage(this);
		this.stability = new StreamStability(this);
		this.snapshots = new StreamSnapshots(this);

		// DEBUG
		this.debug('init', {
			materializeTailAt: this.buffer._tailMaterializeAt,
			hasTpl: !!this._tpl
		});
	}

	// ========================================
	// Stream lifecycle
	// ========================================

	// Debug helper: write structured log lines for the stream engine.
	debug(tag, data) {
		try {
			const lg = this.logger || (this.cfg && this.cfg.logger) || (window.runtime && runtime.logger) || null;
			if (!lg || typeof lg.debug !== 'function') return;
			lg.debug_obj("STREAM", tag, data);
		} catch (_) {}
	}

	// Reset most of the engine state for a brand new stream.
	reset() {
		this.debug('reset', {});
		this.buffer.clear();
		this.fences.reset();
		this.snapshots.reset();
		this.code.reset();
		this.reasoning.reset();
		this.plain.reset();
		this.suppressPostFinalizePass = false;
		this._firstCodeOpenSnapDone = false;
		this._lastInjectedEOL = false;
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
		this.debug('abort', o);

		// Cancel scheduled RAF tasks for this engine.
		try {
			this.raf.cancelGroup('StreamEngine');
		} catch (_) {}
		try {
			this.raf.cancel('SE:snapshot');
		} catch (_) {}
		this.snapshots.snapshotScheduled = false;
		this.snapshots.snapshotRAF = 0;

		// Finalize or defuse active code block if any.
		const hadActive = !!this.code.activeCode;
		try {
			if (this.code.activeCode) {
				if (o.finalizeActive === true) this.code.finalizeActiveCode();
				else this.code.defuseActiveToPlain();
			}
		} catch (e) {}

		// Clean up any orphan "active" blocks in the DOM.
		if (o.defuseOrphans) {
			try {
				this.code.defuseOrphanActiveBlocks();
			} catch (e) {}
		}

		// Optionally clear buffers and reset fence state.
		if (o.clearBuffer) {
			this.buffer.clear();
			this.fences.fenceOpen = false;
			this.fences.fenceMark = '`';
			this.fences.fenceLen = 3;
			this.fences.fenceTail = '';
			this.fences.fenceBuf = '';
			this.code.codeStream.open = false;
			this.code.codeStream.lines = 0;
			this.code.codeStream.chars = 0;
			window.__lastSnapshotLen = 0;
		}
		// Optionally clear current message UI.
		if (o.clearMsg === true) {
			try {
				this.dom.resetEphemeral();
			} catch (_) {}
		}

		this.plain.reset();
	}

	// Get or create the message element used for streaming output.
	getMsg(create, name_header) {
		return this.dom.getStreamMsg(create, name_header);
	}

	// Start a new stream: clear output, reset state, and scroll to bottom.
	beginStream(chunk = false, clearOutput = true) {
		this.isStreaming = true;
		// DEBUG
		this.debug('stream.begin', {
			chunk,
			clearOutput
		});
		const follow = this.scrollMgr.shouldFollowOnStreamStart();
		// A visible final stream replaces the reserved request-loader slot. Hidden
		// reasoning keeps the loader/placeholder alive until real response text.
		if (chunk) {
			try {
				runtime.loading.hide(false);
			} catch (_) {}
		}
		// Tool-only continuations reuse one id-bound workflow host. Reset the
		// stream engine, but do not destroy/recreate that DOM subtree between calls.
		if (clearOutput) this.dom.clearOutput();
		this.reset();

		if (follow) {
			// Establish FOLLOW once. Native bottom anchoring keeps the viewport pinned
			// during subsequent DOM growth without per-token JS scroll corrections.
			this.scrollMgr.resumeAutoFollow(true);
		} else {
			// Keep the user's current viewport stable while new content grows below.
			this.scrollMgr.suspendAutoFollow();
			this.scrollMgr.scheduleScrollFabUpdate();
		}
	}

	// Finish the stream: render final snapshot, finalize code, flush highlighting, and clean up.
	endStream() {
		this.isStreaming = false;
		const msg = this.getMsg(false, '');
		if (msg) this.snapshots.renderSnapshot(msg);

		// With auto-hide disabled, keep reasoning visible for the whole generation,
		// then hide it at stream completion when a normal response exists. A
		// reasoning-only response stays visible as the fallback used by the renderer.
		if (!this.reasoning.reasoningHideAfterResponse && this.reasoning.reasoningHasResponseText) {
			this.reasoning.cancelReasoningTimers();
			this.reasoning.reasoningVisible = false;
			this.reasoning.reasoningFadeInStartedAt = 0;
			this.reasoning.reasoningFadeOutStartedAt = 0;
			if (msg) this.reasoning.syncReasoningVisibility(this.snapshots.getMsgSnapshotRoot(msg));
		}

		// Cancel any scheduled tasks related to streaming.
		this.snapshots.snapshotScheduled = false;
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
		if (this.code._promoteTimer) {
			clearTimeout(this.code._promoteTimer);
			this.code._promoteTimer = 0;
		}

		this.snapshots.snapshotRAF = 0;

		// If there was an active code block, finalize it now.
		const hadActive = !!this.code.activeCode;
		if (this.code.activeCode) this.code.finalizeActiveCode();

		// If not, flush any remaining highlight queue and render math once.
		if (!hadActive) {
			if (this.highlighter.hlQueue && this.highlighter.hlQueue.length) {
				this.highlighter.flush(this.code.activeCode);
			}
			const snap = msg ? this.snapshots.getMsgSnapshotRoot(msg) : null;
			if (snap) this.math.renderAsync(snap);
		}

		// Reset buffers and flags.
		this.buffer.clear();

		this.fences.fenceOpen = false;
		this.code.codeStream.open = false;
		this.code.activeCode = null;
		this.snapshots.lastSnapshotTs = Utils.now();
		this.suppressPostFinalizePass = false;

		// Reset plain state to default for next sessions.
		this.plain.reset();

		// DEBUG
		this.debug('stream.end', {
			hadActive
		});
	}

	// ========================================
	// Chunk rendering
	// ========================================

	// Main entry: accept a chunk for a given "name_header" and update the view incrementally.
	applyStream(name_header, chunk, alreadyBuffered = false) {
		// If there is no active code and fences are closed, defuse any stray active blocks in DOM.
		if (!this.code.activeCode && !this.fences.fenceOpen) {
			try {
				if (document.querySelector('pre code[data-_active_stream="1"]')) this.code.defuseOrphanActiveBlocks();
			} catch (_) {}
		}
		// Re-sync scheduled flag with RAF state.
		if (this.snapshots.snapshotScheduled && !this.raf.isScheduled('SE:snapshot')) this.snapshots.snapshotScheduled = false;

		const msg = this.getMsg(true, name_header);
		if (!msg || !chunk) return;
		const s = String(chunk);

		// Track think boundaries before rendering. The grace-period timer starts on
		// the first real response text outside <think>, not on </think> itself.
		const reasoningState = this.reasoning.updateReasoningVisibilityFromChunk(s);
		const reasoningOpened = reasoningState.changed && this.reasoning.reasoningThinking;
		if (reasoningState.hasResponseText && !this.reasoning.reasoningThinking) {
			this.reasoning.scheduleReasoningHide(msg);
		}

		// DEBUG (only if interesting)
		if (/[<>]/.test(s)) {
			this.debug('apply.chunk', {
				len: s.length,
				nl: Utils.countNewlines(s),
				head: s.slice(0, 120),
				tail: s.slice(-120)
			});
		}

		// Buffer the chunk unless caller says it's already buffered (recursive tail call case).
		if (!alreadyBuffered) this.buffer.append(s);

		// Materialize the reasoning wrapper synchronously as soon as <think> is
		// received. Waiting for the regular snapshot scheduler leaves the raw tag
		// briefly visible, especially after a hidden tool result.
		if (reasoningOpened && this.reasoning.reasoningEnabled && !this.fences.fenceOpen && !this.code.codeStream.open) {
			try {
				this.snapshots.renderSnapshot(msg);
				try { this.raf.cancel('SE:snapshot'); } catch (_) {}
				this.snapshots.snapshotScheduled = false;
			} catch (_) {}
		}

		// Update fence state based on the new text.
		const change = this.fences.updateFenceHeuristic(s);
		const nlCount = Utils.countNewlines(s);
		const chunkHasNL = nlCount > 0;

		// If no fence opened and we are outside code, check if custom openers request early snapshot.
		if (!change.opened && !this.fences.fenceOpen) {
			this.snapshots.maybeEagerSnapshotForCustomOpeners(msg, s);
		}

		// Plain vs full-MD decision management (non-code)
		if (!this.fences.fenceOpen && !this.code.codeStream.open) {
			const mdPresent = this.snapshots.chunkHasMarkdown(s) || this.snapshots.chunkHasCustomOpeners(s) || change.opened;
			const thr = this.plain.threshold();

			if (mdPresent) {
				// Markdown seen → reset counters and exit plain mode if active.
				if (this.plain.state.noMdNL !== 0) {
					this.debug('apply.plain.resetOnMD', { noMdNL: this.plain.state.noMdNL });
				}
				this.plain.state.noMdNL = 0;

				if (this.plain.state.enabled) {
					// Leave plain mode and force one full snapshot to "re-sync" elegant rendering.
					this.plain.state.enabled = false;
					this.plain.state.suppressInline = false;
					this.plain.state.forceFullMDOnce = true;
					this.debug('apply.plain.disableOnMD', {});
					this.snapshots.scheduleSnapshot(msg, true);
				}
			} else if (chunkHasNL) {
				// No markdown in this chunk and we got newlines → count "plain lines"
				this.plain.state.noMdNL += nlCount;

				if (!this.plain.state.enabled && this.plain.state.noMdNL >= thr) {
					// Threshold reached → enter fully plain-text mode
					this.plain.state.enabled = true;
					this.plain.state.suppressInline = true; // fully plain-text (no inline markdown upgrades)
					this.debug('apply.plain.enable', { noMdNL: this.plain.state.noMdNL, thr });
					// Switch to plain path soon
					this.snapshots.scheduleSnapshot(msg);
				}
			}
		}

		// Track if we just materialized the first code-open snapshot synchronously.
		let didImmediateOpenSnap = false;

		// If a fence opened in this chunk, mark code stream active and try to snapshot soon.
		if (change.opened) {
			this.code.codeStream.open = true;
			this.code.codeStream.lines = 0;
			this.code.codeStream.chars = 0;
			this.snapshots.resetBudget();
			this.debug('code.open', {});
			this.snapshots.scheduleSnapshot(msg);

			// Special case: if the message is empty and we just opened, render immediately once.
			if (!this._firstCodeOpenSnapDone && !this.code.activeCode && ((window.__lastSnapshotLen || 0) === 0)) {
				try {
					this.snapshots.renderSnapshot(msg);
					try {
						this.raf.cancel('SE:snapshot');
					} catch (_) {}
					this.snapshots.snapshotScheduled = false;
					this._firstCodeOpenSnapDone = true;
					didImmediateOpenSnap = true;
					this.debug('code.open.immediateSnap', {});
				} catch (_) {}
			}
		}

		// If we are inside a code block stream, feed text into the active code tail or wait for a snapshot.
		if (this.code.codeStream.open) {
			this.code.codeStream.lines += nlCount;
			this.code.codeStream.chars += s.length;

			if (this.code.activeCode && this.code.activeCode.codeEl && this.code.activeCode.codeEl.isConnected) {
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
					this.code.appendToActiveTail(partForCode);
					this.code.activeCode.lines += Utils.countNewlines(partForCode);

					this.language.maybePromoteLanguageFromDirective();
					this.code.enforceHLStopBudget();

					const tailLenNow = (this.code.activeCode.tailEl.textContent || '').length;
					const hasNL = partForCode.indexOf('\n') >= 0;

					// Schedule promotion when we have a newline or enough chars.
					if (!this.code.activeCode.plainStream) {
						const HL_MIN = this.cfg.PROFILE_CODE.minCharsForHL;
						if (hasNL || tailLenNow >= HL_MIN) this.code.schedulePromoteTail(false);
					}
				}
				// Keep viewport and FAB updated while streaming code.
				this.scrollMgr.scrollFabUpdateScheduled = false;
				this.scrollMgr.scheduleScroll(true);
				this.scrollMgr.fabFreezeUntil = Utils.now() + this.cfg.FAB.TOGGLE_DEBOUNCE_MS;
				this.scrollMgr.scheduleScrollFabUpdate();

				// If this chunk closed the fence, finalize code and process any remainder as normal text.
				if (change.closed) {
					this.debug('code.close', {
						remainderLen: remainder.length
					});
					this.code.finalizeActiveCode();
					this.code.codeStream.open = false;
					this.snapshots.resetBudget();
					// Force immediate full snapshot to avoid any transient plain rendering
					this.plain.state.forceFullMDOnce = true;
					this.snapshots.scheduleSnapshot(msg, true);
					if (remainder && remainder.length) {
						this.applyStream(name_header, remainder, true);
					}
				}
				return;
			} else {
				// If code just opened but we have not created activeCode yet, force a snapshot once enough content arrives.
				if (!this.code.activeCode && (this.code.codeStream.lines >= 2 || this.code.codeStream.chars >= 80)) {
					this.debug('code.awaitActive.forceSnap', {
						lines: this.code.codeStream.lines,
						chars: this.code.codeStream.chars
					});
					this.snapshots.scheduleSnapshot(msg, true);
					return;
				}
				// If code closed without an active code element (rare), schedule a snapshot to reflect closure.
				// Outside code streaming
				if (change.closed) {
					this.code.codeStream.open = false;
					this.snapshots.resetBudget();
					this.debug('code.closed.outside', {});
					this.plain.state.forceFullMDOnce = true;
					this.snapshots.scheduleSnapshot(msg, true);
				} else {
					const boundary = this.snapshots.hasStructuralBoundary(s);
					if (this.snapshots.shouldSnapshotOnChunk(s, chunkHasNL, boundary)) {
						this.debug('snapshot.decide', {
							reason: 'boundary/step'
						});
						this.snapshots.scheduleSnapshot(msg);
					} else {
						this.snapshots.maybeScheduleSoftSnapshot(msg, chunkHasNL);
					}
				}
				return;
			}
		}

		// Outside code streaming: consider snapshotting or soft scheduling based on boundaries/size.
		if (change.closed) {
			this.code.codeStream.open = false;
			this.snapshots.resetBudget();
			this.debug('code.closed.outside', {});
			this.snapshots.scheduleSnapshot(msg);
		} else {
			const boundary = this.snapshots.hasStructuralBoundary(s);
			if (this.snapshots.shouldSnapshotOnChunk(s, chunkHasNL, boundary)) {
				this.debug('snapshot.decide', {
					reason: 'boundary/step'
				});
				this.snapshots.scheduleSnapshot(msg);
			} else {
				this.snapshots.maybeScheduleSoftSnapshot(msg, chunkHasNL);
			}
		}
	}

}
