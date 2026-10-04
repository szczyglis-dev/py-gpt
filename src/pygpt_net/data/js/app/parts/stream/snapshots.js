class StreamSnapshots {

	// ========================================
	// Composition
	// ========================================

	constructor(engine) {
		this.engine = engine;
		this.lastSnapshotTs = 0;
		this.nextSnapshotStep = engine.cfg.PROFILE_TEXT.base;
		this.snapshotScheduled = false;
		this.snapshotRAF = 0;
	}

	// ========================================
	// Snapshot scheduling
	// ========================================

	reset() {
		this.lastSnapshotTs = 0;
		this.nextSnapshotStep = this.profile().base;
		this.snapshotScheduled = false;
		this.snapshotRAF = 0;
	}

	// Quick check: does chunk contain a structural boundary worth snapshotting on?
	hasStructuralBoundary(chunk) {
		if (!chunk) return false;
		// New paragraph or common block marker means we may want to render now.
		return this.engine._reStructBoundary.test(chunk);
	}

	// Decide whether we should schedule a snapshot for this chunk.
	shouldSnapshotOnChunk(chunk, chunkHasNL, hasBoundary) {
		const prof = this.profile();
		const now = Utils.now();
		// Avoid snapshots too frequently.
		if (this.engine.code.activeCode && this.engine.fences.fenceOpen) return false;
		if ((now - this.lastSnapshotTs) < prof.minInterval) return false;
		if (hasBoundary) return true;

		const delta = Math.max(0, this.engine.buffer.getStreamLength() - (window.__lastSnapshotLen || 0));
		if (this.engine.fences.fenceOpen) {
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
		if (this.engine.code.activeCode && this.engine.fences.fenceOpen) return;
		if (this.engine.fences.fenceOpen && this.engine.code.codeStream.lines < 1 && !chunkHasNL) return;
		const now = Utils.now();
		if ((now - this.lastSnapshotTs) >= prof.softLatency) {
			this.engine.debug('snapshot.soft.schedule', {
				latency: (now - this.lastSnapshotTs),
				soft: prof.softLatency
			});
			this.scheduleSnapshot(msg);
		}
	}

	// Schedule a snapshot render on the next frame (or force immediately).
	scheduleSnapshot(msg, force = false) {
		// Keep internal "scheduled" flag in sync with RAF scheduler.
		if (this.snapshotScheduled && !this.engine.raf.isScheduled('SE:snapshot')) this.snapshotScheduled = false;
		if (!force) {
			if (this.snapshotScheduled) {
				this.engine.debug('snapshot.schedule.skip', {
					reason: 'alreadyScheduled'
				});
				return;
			}
			if (this.engine.code.activeCode && this.engine.fences.fenceOpen) {
				this.engine.debug('snapshot.schedule.skip', {
					reason: 'activeCodeFenceOpen'
				});
				return;
			}
		} else {
			if (this.snapshotScheduled && this.engine.raf.isScheduled('SE:snapshot')) {
				this.engine.debug('snapshot.schedule.skip', {
					reason: 'alreadyScheduled(forceCollide)'
				});
				return;
			}
		}
		this.snapshotScheduled = true;
		this.engine.debug('snapshot.schedule', {
			force,
			fenceOpen: this.engine.fences.fenceOpen,
			isStreaming: this.engine.isStreaming
		});
		this.engine.raf.schedule('SE:snapshot', () => {
			this.snapshotScheduled = false;
			const msg = this.engine.getMsg(false, '');
			if (msg) this.renderSnapshot(msg);
		}, 'StreamEngine', 0);
	}

	// Return the active performance profile depending on whether code fence is open.
	profile() {
		return this.engine.fences.fenceOpen ? this.engine.cfg.PROFILE_CODE : this.engine.cfg.PROFILE_TEXT;
	}

	// Reset the adaptive budget/step for snapshots.
	resetBudget() {
		this.nextSnapshotStep = this.profile().base;
		// DEBUG
		this.engine.debug('budget.reset', {
			step: this.nextSnapshotStep
		});
	}

	// ========================================
	// Snapshot rendering
	// ========================================

	// Get or create the DOM root for message snapshots.
	getMsgSnapshotRoot(msg) {
		if (!msg) return null;
		let snap = msg.querySelector('.md-snapshot-root');
		if (!snap) {
			snap = document.createElement('div');
			snap.className = 'md-snapshot-root';
			msg.appendChild(snap);
			// DEBUG
			this.engine.debug('snapshot.root.create', {});
		}
		return snap;
	}

	// Render a snapshot of the current buffer: either plain streaming or full markdown.
	renderSnapshot(msg) {
		const streaming = !!this.engine.isStreaming;
		const snap = this.getMsgSnapshotRoot(msg);
		if (!snap) return;

		// If nothing changed and no open code, just update timestamps and return.
		const prevLen = (window.__lastSnapshotLen || 0);
		const curLen = this.engine.buffer.getStreamLength();
		if (!this.engine.fences.fenceOpen && !this.engine.code.activeCode && curLen === prevLen) {
			this.lastSnapshotTs = Utils.now();
			return;
		}

		// Decide plain vs full-MD path before materializing big strings.
		const forceFull = !!this.engine.plain.state.forceFullMDOnce;
		// IMPORTANT: use plain path only after threshold and only when enabled
		const streamingPlain = streaming && !this.engine.fences.fenceOpen && !forceFull && this.engine.plain.state.enabled;

		// DEBUG
		this.engine.debug('snapshot.begin', {
			streaming,
			fenceOpen: this.engine.fences.fenceOpen,
			streamingPlain,
			forceFull,
			prevLen,
			curLen
		});

		if (streamingPlain) {
			// Fast path: compute delta without materializing the full buffer.
			const delta = this.engine.buffer.getDeltaSince(prevLen);
			this.engine.plain.appendDelta(snap, delta);

			// Bookkeeping for pacing and next snapshot.
			window.__lastSnapshotLen = curLen;
			this.lastSnapshotTs = Utils.now();

			const prof = this.profile();
			if (prof.adaptiveStep) {
				const maxStep = this.engine.cfg.STREAM.SNAPSHOT_MAX_STEP || 8000;
				this.nextSnapshotStep = Math.min(Math.ceil(this.nextSnapshotStep * prof.growth), maxStep);
			} else {
				this.nextSnapshotStep = prof.base;
			}

			this.engine.scrollMgr.scheduleScroll(true);
			this.engine.scrollMgr.fabFreezeUntil = Utils.now() + this.engine.cfg.FAB.TOGGLE_DEBOUNCE_MS;
			this.engine.scrollMgr.scheduleScrollFabUpdate();

			this.engine.debug('snapshot.end.plain', {
				nextStep: this.nextSnapshotStep
			});
			return;
		}

		// Non-plain (full MD streaming or final)
		if (forceFull) this.engine.plain.state.forceFullMDOnce = false;

		// Materialize buffer for rendering (zero-copy: see getStreamText()).
		let allText = this.engine.buffer.getStreamText();

		// When switching away from plain streaming, drop any pending carry (full snapshot re-renders everything).
		this.engine.plain.state._carry = '';

		// If a code fence is open, but buffer ends without EOL, append synthetic EOL so parser sees the line.
		const needSyntheticEOL = (this.engine.fences.fenceOpen && !/[\r\n]$/.test(allText));
		this.engine._lastInjectedEOL = !!needSyntheticEOL;
		let src = needSyntheticEOL ? (allText + '\n') : allText;

		// DEBUG (only if interesting)
		if (/[<>]/.test(src)) this.engine.debug('snapshot.full.src', {
			len: src.length,
			head: src.slice(0, 120),
			tail: src.slice(-120),
			injectedEOL: needSyntheticEOL
		});

		// Produce a DOM fragment from renderer (stream or final flavor).
		let frag = null;
		if (streaming) frag = this.engine.renderer.renderStreamingSnapshotFragment(src);
		else frag = this.engine.renderer.renderFinalSnapshotFragment(src);

		// Let custom markup post-process the fragment if enabled.
		try {
			if (this.engine.renderer && this.engine.renderer.customMarkup && this.engine.renderer.customMarkup.hasStreamRules()) {
				const MDinline = this.engine.renderer.MD_STREAM || this.engine.renderer.MD || null;
				this.engine.renderer.customMarkup.live.applyStream(frag, MDinline);
			}
		} catch (_) {}

		// Try to reuse stable code blocks to reduce flicker/work.
		this.engine.stability.preserveStableClosedCodes(snap, frag, this.engine.fences.fenceOpen === true);
		// Minimal DOM patch to update only changed middle section.
		this.engine.stability.patchSnapshotRoot(snap, frag);

		// Snapshot rendering reconstructs all historical <think> nodes from the stream
		// buffer. Re-apply the live state after every patch so completed reasoning
		// stays hidden and only a currently active newest block is visible.
		this.engine.reasoning.syncReasoningVisibility(snap);

		// Micro highlight: highlight one small visible code block immediately to avoid a plain-text flash.
		try {
			if (this.engine.highlighter && typeof this.engine.highlighter.microHighlightNow === 'function') {
				this.engine.highlighter.microHighlightNow(snap, {
					maxCount: 1,
					budgetMs: 4
				}, this.engine.code.activeCode);
			}
		} catch (_) {}

		// Restore any collapsed code UI and ensure finalized blocks are scrolled properly.
		this.engine.renderer.restoreCollapsedCode(snap);
		this.engine.code.ensureBottomForJustFinalized(snap);

		// If code fence is open, re-create active streaming code target.
		const prevAC = this.engine.code.activeCode;
		if (this.engine.fences.fenceOpen) {
			const newAC = this.engine.code.setupActiveCodeFromSnapshot(snap);
			if (prevAC && newAC) this.engine.code.rehydrateActiveCode(prevAC, newAC);
			// Run stabilization even for the first snapshot (prevAC may be null).
			this.engine.code.stabilizeHeaderLabel(prevAC || null, newAC || null);
			this.engine.code.activeCode = newAC || null;
		} else {
			this.engine.code.activeCode = null;
		}

		// Initialize scroll handlers for code blocks when outside of code streaming.
		if (!this.engine.fences.fenceOpen) {
			this.engine.codeScroll.initScrollableBlocks(snap);
		}

		// Observe new code blocks for highlighting; defer the last one while streaming.
		this.engine.highlighter.observeNewCode(
			snap, {
				deferLastIfStreaming: true,
				minLinesForLast: this.engine.cfg.PROFILE_CODE.minLinesForHL,
				minCharsForLast: this.engine.cfg.PROFILE_CODE.minCharsForHL
			},
			this.engine.code.activeCode
		);

		// Also watch code inside message boxes that may appear.
		this.engine.highlighter.observeMsgBoxes(snap, (box) => {
			this.engine.highlighter.observeNewCode(
				box, {
					deferLastIfStreaming: true,
					minLinesForLast: this.engine.cfg.PROFILE_CODE.minLinesForHL,
					minCharsForLast: this.engine.cfg.PROFILE_CODE.minCharsForHL
				},
				this.engine.code.activeCode
			);
			this.engine.codeScroll.initScrollableBlocks(box);
		});

		// Schedule math rendering depending on math mode.
		const mm = getMathMode();
		if (!this.engine.suppressPostFinalizePass) {
			if (mm === 'idle') this.engine.math.schedule(snap);
			else if (mm === 'always') this.engine.math.schedule(snap, 0, true);
		}

		// If we are streaming code, attach scroll handlers and keep following.
		if (this.engine.fences.fenceOpen && this.engine.code.activeCode && this.engine.code.activeCode.codeEl) {
			this.engine.codeScroll.attachHandlers(this.engine.code.activeCode.codeEl);
			this.engine.codeScroll.scheduleScroll(this.engine.code.activeCode.codeEl, true, false);
		} else if (!this.engine.fences.fenceOpen) {
			this.engine.codeScroll.initScrollableBlocks(snap);
		}

		// Update counters and adaptive step.
		window.__lastSnapshotLen = this.engine.buffer.getStreamLength();
		this.lastSnapshotTs = Utils.now();

		const prof = this.profile();
		if (prof.adaptiveStep) {
			const maxStep = this.engine.cfg.STREAM.SNAPSHOT_MAX_STEP || 8000;
			this.nextSnapshotStep = Math.min(Math.ceil(this.nextSnapshotStep * prof.growth), maxStep);
		} else {
			this.nextSnapshotStep = prof.base;
		}

		// Keep the viewport and FAB updated.
		this.engine.scrollMgr.scheduleScroll(true);
		this.engine.scrollMgr.fabFreezeUntil = Utils.now() + this.engine.cfg.FAB.TOGGLE_DEBOUNCE_MS;
		this.engine.scrollMgr.scheduleScrollFabUpdate();

		// Clear one-time suppression flag if set.
		if (this.engine.suppressPostFinalizePass) this.engine.suppressPostFinalizePass = false;

		// NOTE: drop local big references ASAP
		frag = null;
		src = null;
		allText = null;

		// DEBUG
		this.engine.debug('snapshot.end.full', {
			nextStep: this.nextSnapshotStep,
			fenceOpen: this.engine.fences.fenceOpen,
			hasActiveCode: !!this.engine.code.activeCode
		});
	}

	// ========================================
	// Markdown and custom delimiters
	// ========================================

	// Quick MD detectors

	// Check if a chunk likely contains inline or block markdown markers.
	chunkHasMarkdown(s) {
		try {
			return this.engine._mdQuickRe.test(String(s || ''));
		} catch (_) {
			return false;
		}
	}

	// Ask custom markup if there are any stream open tokens in the chunk.
	chunkHasCustomOpeners(s) {
		try {
			const CM = this.engine.renderer && this.engine.renderer.customMarkup;
			if (!CM || typeof CM.hasAnyStreamOpenToken !== 'function') return false;
			return CM.hasAnyStreamOpenToken(String(s || ''));
		} catch (_) {
			return false;
		}
	}

	// If custom markup has openers in the chunk (especially at start), trigger early snapshot.
	maybeEagerSnapshotForCustomOpeners(msg, chunkStr) {
		try {
			const CM = this.engine.renderer && this.engine.renderer.customMarkup;
			if (!CM || !CM.hasStreamRules()) return;
			if (this.engine.fences.fenceOpen || this.engine.code.codeStream.open) return;

			// For the very first snapshot, check if the buffered head already starts with an opener.
			const isFirstSnapshot = ((window.__lastSnapshotLen || 0) === 0);

			if (isFirstSnapshot) {
				let head;
				try {
					head = this.engine.buffer.getStreamText();
				} catch (_) {
					head = String(chunkStr || '');
				}
				if (CM.hasStreamOpenerAtStart(head)) {
					this.engine.debug('snapshot.eager.custom', {
						reason: 'headHasOpener'
					});
					this.scheduleSnapshot(msg, true);
					return;
				}
			}

			// Otherwise, check current chunk for any open token.
			const rules = (CM.getRules() || []).filter(r => r && r.stream && typeof r.open === 'string');
			if (rules.length && CM.hasAnyOpenToken(String(chunkStr || ''), rules)) {
				this.engine.debug('snapshot.eager.custom', {
					reason: 'chunkHasOpener'
				});
				this.scheduleSnapshot(msg);
			}
		} catch (_) {}
	}

}
