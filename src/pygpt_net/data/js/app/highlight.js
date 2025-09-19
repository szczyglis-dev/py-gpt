// ==========================================================================
// Highlighter (hljs) + rAF viewport scan
// ==========================================================================

class Highlighter {

    // Constructor: store config/scroll/RAF, init queues and scan budget
    constructor(cfg, codeScroll, raf) {
        this.cfg = cfg;
        this.codeScroll = codeScroll;
        this.raf = raf;

        this.hlScheduled = false;
        this.hlQueue = [];
        this.hlQueueSet = new WeakSet();

        this.scanScheduled = false;

        this._activeCodeEl = null;

        this._globalScanState = null;

        this.ALIAS = {
			txt: 'plaintext',
			text: 'plaintext',
			plaintext: 'plaintext',
			sh: 'bash',
			shell: 'bash',
			zsh: 'bash',
			'shell-session': 'bash',
			py: 'python',
			python3: 'python',
			py3: 'python',
			js: 'javascript',
			node: 'javascript',
			nodejs: 'javascript',
			ts: 'typescript',
			'ts-node': 'typescript',
			yml: 'yaml',
			kt: 'kotlin',
			rs: 'rust',
			csharp: 'csharp',
			'c#': 'csharp',
			'c++': 'cpp',
			ps: 'powershell',
			ps1: 'powershell',
			pwsh: 'powershell',
			powershell7: 'powershell',
			docker: 'dockerfile'
		};

        const hint = (cfg && cfg.RAF && cfg.RAF.FLUSH_BUDGET_MS) ? cfg.RAF.FLUSH_BUDGET_MS : 7;
        this.SCAN_STEP_BUDGET_MS = Math.max(3, Math.min(12, hint));
    }

    // Debug helper: write structured log lines for the stream engine.
    _d(tag, data) {
        try {
            const lg = this.logger || (this.cfg && this.cfg.logger) || (window.runtime && runtime.logger) || null;
            if (!lg || typeof lg.debug !== 'function') return;
            lg.debug_obj("HL", tag, data);
        } catch (_) {}
    }

    // Decodes HTML entities in a string, handling nested entities up to a specified number of passes.
    _decodeEntitiesDeep(text, maxPasses = 2) {
        if (!text || text.indexOf('&') === -1) return text || '';
        const ta = Highlighter._decTA || (Highlighter._decTA = document.createElement('textarea'));
        const decodeOnce = (s) => {
            ta.innerHTML = s;
            return ta.value;
        };
        let prev = String(text),
            cur = decodeOnce(prev),
            passes = 1;
        while (passes < maxPasses && cur !== prev) {
            prev = cur;
            cur = decodeOnce(prev);
            passes++;
        }
        return cur;
    }

    // Check if highlighting is globally disabled via configuration.
    isDisabled() {
        return !!this.cfg.HL.DISABLE_ALL;
    }

    // Initializes the Highlight.js library with specific configuration settings.
    initHLJS() {
        if (this.isDisabled()) return;
        if (typeof hljs !== 'undefined' && hljs) {
            try {
                hljs.configure({
                    ignoreUnescapedHTML: true
                });
            } catch (_) {}
        }
    }

    // Returns true if the element is within (or near) the viewport,
    // using a preload margin to start work slightly before it becomes visible.
    _nearViewport(el) {
        const preload = this.cfg.SCAN.PRELOAD_PX;
        const vh = window.innerHeight || Utils.SE.clientHeight || 800;
        const r = el.getBoundingClientRect();
        return r.bottom >= -preload && r.top <= (vh + preload);
    }

    // Queue a code element for highlighting. Avoids duplicates, respects
    // "active" code being streamed, and schedules a flush via rAF.
    queue(codeEl, activeCode) {
        if (this.isDisabled()) return;
        if (!codeEl || !codeEl.isConnected) return;

        // Track the currently streaming code block to avoid highlighting it mid-stream.
        if (activeCode && activeCode.codeEl) this._activeCodeEl = activeCode.codeEl;

        // Skip: the currently active element, already highlighted, or explicitly suspended.
        if (this._activeCodeEl && codeEl === this._activeCodeEl) return;
        if (codeEl.getAttribute('data-highlighted') === 'yes') return;
        if (codeEl.dataset && (codeEl.dataset.hlStreamSuspended === '1' || codeEl.dataset.finalHlSkip === '1')) return;
        // We only highlight bot messages; user code blocks are ignored here.
        if (!codeEl.closest('.msg-box.msg-bot')) return;

        // De-duplicate with a WeakSet (handles disconnected nodes GC-safe).
        if (!this.hlQueueSet.has(codeEl)) {
            this.hlQueueSet.add(codeEl);
            this.hlQueue.push(codeEl);
        }

        // Coalesce flush requests into a single rAF task.
        if (!this.hlScheduled) {
            this.hlScheduled = true;
            this.raf.schedule('HL:flush', () => this.flush(), 'Highlighter', 1);
        }

        // DEBUG (avoid heavy reads)
        try {
            const wrap = codeEl.closest('.code-wrapper');
            const len = wrap ? parseInt(wrap.getAttribute('data-code-len') || '0', 10) : NaN;
            this._d('queue', {
                len,
                hasWrap: !!wrap
            });
        } catch (_) {}
    }

    // Flush the highlight queue. Processes up to HL.PER_FRAME items per frame.
    // Yields early if the browser reports pending input for responsiveness.
    flush() {
        if (this.isDisabled()) {
            this.hlScheduled = false;
            this.hlQueueSet.clear();
            this.hlQueue.length = 0;
            return;
        }

        this.hlScheduled = false;

        const activeEl = this._activeCodeEl;

        let count = 0;
        while (this.hlQueue.length && count < this.cfg.HL.PER_FRAME) {
            const el = this.hlQueue.shift();
            if (el && el.isConnected) this.safeHighlight(el, activeEl);
            if (el) this.hlQueueSet.delete(el);
            count++;

            // Cooperative yield if there's pending input to keep the UI responsive.
            try {
                const sched = (navigator && navigator.scheduling && navigator.scheduling.isInputPending) ? navigator.scheduling : null;
                if (sched && sched.isInputPending({
                        includeContinuous: true
                    })) {
                    if (this.hlQueue.length) {
                        this.hlScheduled = true;
                        this.raf.schedule('HL:flush', () => this.flush(), 'Highlighter', 1);
                    }
                    this._d('flush.yield', {
                        processed: count,
                        remaining: this.hlQueue.length
                    });
                    return;
                }
            } catch (_) {}
        }

        // If there are still items, schedule another frame.
        if (this.hlQueue.length) {
            this.hlScheduled = true;
            this.raf.schedule('HL:flush', () => this.flush(), 'Highlighter', 1);
        }
        this._d('flush.done', {
            processed: count,
            remaining: this.hlQueue.length
        });
    }

    // Fast check: does the text contain any entity markers that might need decoding?
    _needsDeepDecode(text) {
        if (!text) return false;
        const s = String(text);
        return (s.indexOf('&') !== -1) || (s.indexOf('&#') !== -1);
    }

    // Cheap, single-pass entity decoder for common entities.
    _decodeEntitiesCheap(s) {
        return s
            .replaceAll('&amp;', '&')
            .replaceAll('&lt;', '<')
            .replaceAll('&gt;', '>')
            .replaceAll('&quot;', '"')
            .replaceAll('&#39;', "'");
    }

    // If the code block is finalized, detach scroll handlers to avoid unnecessary work.
    detachHandlersIfFinal(el) {
        if (this.isFinalizedCode(el)) this.detachHandlers(el);
    }

    // Opportunistically highlight a small number of near-viewport code blocks immediately,
    // within a tiny time budget, to improve perceived responsiveness.
    microHighlightNow(root, opts, activeCode) {
        if (this.isDisabled()) return;
        const scope = root || document;
        const options = Object.assign({
            maxCount: 1,
            budgetMs: 4
        }, opts || {});
        const activeEl = activeCode && activeCode.codeEl ? activeCode.codeEl : null;

        // Clamp micro limits to avoid expensive work on large snippets.
        const maxLines = (this.cfg.HL && this.cfg.HL.MICRO_MAX_LINES) || Math.min(80, this.cfg.PROFILE_CODE.finalHighlightMaxLines || 200);
        const maxChars = (this.cfg.HL && this.cfg.HL.MICRO_MAX_CHARS) || Math.min(4000, this.cfg.PROFILE_CODE.finalHighlightMaxChars || 20000);

        const nodes = scope.querySelectorAll('.msg-box.msg-bot pre code:not([data-highlighted="yes"])');
        const start = Utils.now();
        let done = 0;

        for (let i = 0; i < nodes.length && done < options.maxCount; i++) {
            const el = nodes[i];
            if (!el || !el.isConnected) continue;
            if (activeEl && el === activeEl) continue;
            if (!this._nearViewport(el)) continue;

            // Use precomputed size hints if available; otherwise stay conservative.
            let lines = NaN,
                chars = NaN;
            const wrap = el.closest('.code-wrapper');
            if (wrap) {
                const nlAttr = wrap.getAttribute('data-code-nl');
                const lenAttr = wrap.getAttribute('data-code-len');
                if (nlAttr) lines = parseInt(nlAttr, 10);
                if (lenAttr) chars = parseInt(lenAttr, 10);
            }
            if ((Number.isFinite(lines) && lines > maxLines) || (Number.isFinite(chars) && chars > maxChars)) continue;

            // Highlight immediately and attach scrolling handlers.
            try {
                if (window.hljs) {
                    hljs.highlightElement(el);
                    el.setAttribute('data-highlighted', 'yes');
                    this.codeScroll.attachHandlers(el);
                }
            } catch (_) {}
            done++;
            // Stop if we exceeded our small budget.
            if ((Utils.now() - start) >= options.budgetMs) break;
        }
        if (done) this._d('micro.now', {
            done
        });
    }

    // Safely highlight a code element. Respects size caps and preserves scroll state.
    safeHighlight(codeEl, activeEl) {
        if (this.isDisabled()) return;
        if (!window.hljs || !codeEl || !codeEl.isConnected) return;
        if (!codeEl.closest('.msg-box.msg-bot')) return;
        if (codeEl.getAttribute('data-highlighted') === 'yes') return;
        if (activeEl && codeEl === activeEl) return;

        // Size guard: skip very large blocks and mark them as finalized without styling overhead.
        try {
            const wrap = codeEl.closest('.code-wrapper');
            const maxLines = this.cfg.PROFILE_CODE.finalHighlightMaxLines | 0;
            const maxChars = this.cfg.PROFILE_CODE.finalHighlightMaxChars | 0;

            let lines = NaN,
                chars = NaN;

            if (wrap) {
                const nlAttr = wrap.getAttribute('data-code-nl');
                const lenAttr = wrap.getAttribute('data-code-len');
                if (nlAttr) lines = parseInt(nlAttr, 10);
                if (lenAttr) chars = parseInt(lenAttr, 10);
            }

            if ((Number.isFinite(lines) && maxLines > 0 && lines > maxLines) ||
                (Number.isFinite(chars) && maxChars > 0 && chars > maxChars)) {
                // Apply minimal hljs class for baseline styling, mark as skipped to avoid rework.
                codeEl.classList.add('hljs');
                codeEl.setAttribute('data-highlighted', 'yes');
                codeEl.dataset.finalHlSkip = '1';
                try {
                    this.codeScroll.attachHandlers(codeEl);
                } catch (_) {}
                // Keep auto-follow behavior for incoming content.
                this.codeScroll.scheduleScroll(codeEl, false, false);
                this._d('hl.skip.size', {
                    lines,
                    chars,
                    maxLines,
                    maxChars
                });
                return;
            }
        } catch (_) {}

        // Preserve scroll-follow behavior if the user is near the bottom.
        const wasNearBottom = this.codeScroll.isNearBottomEl(codeEl, 16);
        const st = this.codeScroll.state(codeEl);
        const shouldAutoScrollAfter = (st.autoFollow === true) || wasNearBottom;

        try {
            hljs.highlightElement(codeEl);
            codeEl.setAttribute('data-highlighted', 'yes');
        } catch (_) {
            // Fallback: ensure baseline styling even if highlighting throws.
            if (!codeEl.classList.contains('hljs')) codeEl.classList.add('hljs');
        } finally {
            // Always ensure handlers are attached at least once, then optionally scroll.
            try {
                this.codeScroll.attachHandlers(codeEl);
            } catch (_) {}
            const needInitForce = (codeEl.dataset && (codeEl.dataset.csInitBtm === '1' || codeEl.dataset.justFinalized === '1'));
            const mustScroll = shouldAutoScrollAfter || needInitForce;
            if (mustScroll) this.codeScroll.scheduleScroll(codeEl, false, !!needInitForce);
            this.codeScroll.detachHandlers(codeEl);
            if (codeEl.dataset) {
                if (codeEl.dataset.csInitBtm === '1') codeEl.dataset.csInitBtm = '0';
                if (codeEl.dataset.justFinalized === '1') codeEl.dataset.justFinalized = '0';
            }
            this._d('hl.done', {
                autoScroll: mustScroll
            });
        }
    }

    // Initialize a global, time-sliced scan over all candidate code blocks,
    // enqueuing those that fall within an expanded viewport.
    _startGlobalScan(activeCode) {
        if (this.isDisabled()) return;

        this._activeCodeEl = (activeCode && activeCode.codeEl) ? activeCode.codeEl : this._activeCodeEl;

        const preload = this.cfg.SCAN_PRELOAD_PX || this.cfg.SCAN.PRELOAD_PX;
        const vh = window.innerHeight || Utils.SE.clientHeight || 800;
        const rectTop = 0 - preload,
            rectBottom = vh + preload;

        const nodes = document.querySelectorAll('.msg-box.msg-bot pre code:not([data-highlighted="yes"])');

        this._globalScanState = {
            nodes,
            idx: 0,
            rectTop,
            rectBottom,
            activeCodeEl: this._activeCodeEl || null
        };

        this._d('scan.start', {
            candidates: nodes.length
        });
        this._scanGlobalStep();
    }

    // Perform one incremental scan step, respecting SCAN_STEP_BUDGET_MS
    // to keep main thread responsive. Queues elements near the viewport.
    _scanGlobalStep() {
        const state = this._globalScanState;
        if (!state || !state.nodes || state.idx >= state.nodes.length) {
            this._globalScanState = null;
            this._d('scan.done', {});
            return;
        }

        const start = Utils.now();

        while (state.idx < state.nodes.length) {
            const code = state.nodes[state.idx++];
            if (!code || !code.isConnected) continue;
            if (state.activeCodeEl && code === state.activeCodeEl) continue;

            try {
                const r = code.getBoundingClientRect();
                if (r.bottom >= state.rectTop && r.top <= state.rectBottom) this.queue(code, null);
            } catch (_) {}

            // Time-slice the scan to avoid long tasks.
            if ((Utils.now() - start) >= this.SCAN_STEP_BUDGET_MS) {
                this.raf.schedule('HL:scanStep', () => this._scanGlobalStep(), 'Highlighter', 2);
                return;
            }
        }

        this._globalScanState = null;
        this._d('scan.step.end', {});
    }

    // Discover code nodes in the provided root and conditionally queue them.
    // Attaches scroll handlers immediately; defers highlighting of the last streaming block if requested.
    observeNewCode(root, opts, activeCode) {
        const scope = root || document;

        let nodes;
        if (scope.nodeType === 1 && scope.closest && scope.closest('.msg-box.msg-bot')) nodes = scope.querySelectorAll('pre code');
        else nodes = document.querySelectorAll('.msg-box.msg-bot pre code');
        if (!nodes || !nodes.length) return;

        const options = Object.assign({
            deferLastIfStreaming: false,
            minLinesForLast: 2,
            minCharsForLast: 120
        }, (opts || {}));

        nodes.forEach((code) => {
            if (!code.closest('.msg-box.msg-bot')) return;
            // Ensure scroll behavior works even before highlighting.
            this.codeScroll.attachHandlers(code);
            if (this.isDisabled()) return;
            if (activeCode && code === activeCode.codeEl) return;
            // Optionally defer highlighting if the last block is still very short (still streaming).
            if (options.deferLastIfStreaming && activeCode && code === activeCode.codeEl) {
                const tailLen = (activeCode.tailEl && activeCode.tailEl.textContent) ? activeCode.tailEl.textContent.length : 0;
                const tailLines = (typeof activeCode.tailLines === 'number') ? activeCode.tailLines : 0;
                if (tailLines < options.minLinesForLast && tailLen < options.minCharsForLast) return;
            }
            if (this._nearViewport(code)) this.queue(code, activeCode);
        });

        this._d('observe.codes', {
            count: nodes.length
        });
    }

    // Schedule a global scan for visible code blocks. Coalesces repeated calls and
    // resumes an in-flight scan if one is already running.
    scheduleScanVisibleCodes(activeCode) {
        if (this.isDisabled()) return;

        // Quick existence check to avoid scheduling work when nothing is pending.
        try {
            const anyCandidate = document.querySelector('.msg-box.msg-bot pre code:not([data-highlighted="yes"])');
            const hasActive = !!(activeCode && activeCode.codeEl && activeCode.codeEl.isConnected);
            if (!anyCandidate && !hasActive) return;
        } catch (_) {}

        this._activeCodeEl = (activeCode && activeCode.codeEl) ? activeCode.codeEl : this._activeCodeEl;

        if (this._globalScanState) {
            // Continue the current incremental scan.
            this.raf.schedule('HL:scanStep', () => this._scanGlobalStep(), 'Highlighter', 2);
            return;
        }
        if (this.scanScheduled) return;

        // Coalesce multiple requests into a single scheduled scan.
        this.scanScheduled = true;
        this.raf.schedule('HL:scan', () => {
            this.scanScheduled = false;
            this._startGlobalScan(activeCode || null);
        }, 'Highlighter', 2);
        this._d('scan.scheduled', {});
    }

    // Immediately perform a global scan (no coalescing). Primarily for imperative calls.
    scanVisibleCodes(activeCode) {
        this._startGlobalScan(activeCode || null);
    }

    // Scan only within a specific root element for visible code blocks and queue them.
    scanVisibleCodesInRoot(root, activeCode) {
        if (this.isDisabled()) return;

        const preload = this.cfg.SCAN_PRELOAD_PX || this.cfg.SCAN.PRELOAD_PX;
        const vh = window.innerHeight || Utils.SE.clientHeight || 800;
        const rectTop = 0 - preload,
            rectBottom = vh + preload;

        const scope = root || document;
        const nodes = scope.querySelectorAll('.msg-box.msg-bot pre code:not([data-highlighted="yes"])');

        nodes.forEach((code) => {
            if (!code.isConnected) return;
            if (activeCode && code === activeCode.codeEl) return;
            const r = code.getBoundingClientRect();
            if (r.bottom >= rectTop && r.top <= rectBottom) this.queue(code, activeCode);
        });

        this._d('scan.root', {
            count: nodes.length
        });
    }

    // Placeholder for an IntersectionObserver-based optimization. Intentionally empty.
    installBoxObserver() {
        /* no-op */
    }

    // Iterate all bot message boxes within root and invoke the supplied callback.
    observeMsgBoxes(root, onBoxIntersect) {
        const scope = root || document;

        let boxes;
        if (scope.nodeType === 1) boxes = scope.querySelectorAll('.msg-box.msg-bot');
        else boxes = document.querySelectorAll('.msg-box.msg-bot');

        boxes.forEach((box) => {
            onBoxIntersect && onBoxIntersect(box);
        });
        this._d('observe.boxes', {
            count: boxes.length
        });
    }


    // Cancel all scheduled tasks and clear internal state/queues.
    cleanup() {
        try {
            this.raf.cancelGroup('Highlighter');
        } catch (_) {}
        this.hlScheduled = false;
        this.scanScheduled = false;
        this._globalScanState = null;
        this._activeCodeEl = null;
        this.hlQueueSet.clear();
        this.hlQueue.length = 0;
        this._d('cleanup', {});
    }
}