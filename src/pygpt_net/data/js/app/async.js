// ==========================================================================
// Async runner (cooperative yielding for heavy tasks)
// ==========================================================================

class AsyncRunner {

  // Cooperative scheduler (rAF-based) for CPU-heavy tasks (keeps UI responsive).
  constructor(cfg, raf) {
    this.cfg = cfg || {};
    this.raf = raf || null;

    const A = this.cfg.ASYNC || {};
    // Base time budget for a slice when the page is visible.
    this.SLICE_MS = Utils.g('ASYNC_SLICE_MS', A.SLICE_MS ?? 12);
    // Optional hidden-page tighter budget (yield more aggressively when tab is hidden).
    this.SLICE_HIDDEN_MS = Utils.g('ASYNC_SLICE_HIDDEN_MS', A.SLICE_HIDDEN_MS ?? Math.min(this.SLICE_MS, 6));
    // Kept only for config compatibility (no-op in logic).
    this.MIN_YIELD_MS = Utils.g('ASYNC_MIN_YIELD_MS', A.MIN_YIELD_MS ?? 0);

    // Per-label operation generations (lets us cancel superseded passes cooperatively).
    this._opGen = new Map(); // label -> number
  }

  // Returns true if we should yield control (input pending or time budget exceeded).
  shouldYield(startTs) {
    // If the browser has pending input, yield immediately.
    try {
      const s = navigator && navigator.scheduling;
      if (s && s.isInputPending && s.isInputPending({ includeContinuous: true })) return true;
    } catch (_) {}

    const now = Utils.now();
    const hidden = (typeof document !== 'undefined' && document.visibilityState === 'hidden');
    const budget = hidden ? this.SLICE_HIDDEN_MS : this.SLICE_MS;
    return (now - startTs) >= budget;
  }

  // Yield cooperatively to the next frame (rAF). Falls back to rAF or a minimal timer.
  async yield() {
    // Prefer the shared RafManager to avoid extra tasks and to coalesce with the app's rAF pump.
    if (this.raf && typeof this.raf.nextFrame === 'function') {
      await this.raf.nextFrame();
      return;
    }
    // Fallback to plain requestAnimationFrame if available.
    if (typeof requestAnimationFrame === 'function') {
      await new Promise(res => {
        try { requestAnimationFrame(() => res()); }
        catch (_) { setTimeout(res, 16); }
      });
      return;
    }
    // Final fallback (should not generally happen in QWebEngine).
    await new Promise(res => setTimeout(res, 16));
  }

  // Optional: yield to idle. Uses requestIdleCallback if available, falls back to yield().
  async yieldIdle(timeoutMs = 100) {
    if (typeof requestIdleCallback === 'function') {
      await new Promise(res => {
        try { requestIdleCallback(() => res(), { timeout: timeoutMs }); }
        catch (_) { res(); }
      });
      return;
    }
    await this.yield();
  }

  // Internal: start a new generation for a label; future calls with a higher gen supersede older loops.
  _beginOp(label) {
    if (!label) return 0;
    const g = (this._opGen.get(label) || 0) + 1;
    this._opGen.set(label, g);
    return g;
  }

  // Internal: check if a label/gen pair is still the latest (not superseded).
  _isLatest(label, gen) {
    if (!label) return true;
    return (this._opGen.get(label) === gen);
  }

  // Cancel all in-flight loops for a given label (cooperative; next yield will abort them).
  cancel(label) {
    if (!label) return;
    const g = (this._opGen.get(label) || 0) + 1;
    this._opGen.set(label, g);
  }

  // Process an array in small slices with periodic yields.
  // Options (4th param OR instead of label):
  //   { batch=1, release=false, signal, onProgress }:
  //     - batch: process N items per inner loop before checking shouldYield()
  //     - release: if true, set arr[i] = undefined after processing (helps GC for very large arrays)
  //     - signal: AbortSignal to cancel early
  //     - onProgress: callback({ index, total }) invoked after each processed item (throttled by batch)
  async forEachChunk(arr, fn, labelOrOpts) {
    if (!arr || !arr.length) return;

    // Parse args for back-compat: label (string) or options object.
    let label = (typeof labelOrOpts === 'string') ? labelOrOpts : (labelOrOpts && labelOrOpts.label) || undefined;
    const opts = (label && typeof labelOrOpts === 'object')
      ? { ...labelOrOpts, label }
      : (typeof labelOrOpts === 'object' ? labelOrOpts : {});

    const batch = Math.max(1, opts.batch | 0 || 1);
    const release = !!opts.release;
    const signal = opts.signal;
    const onProgress = (typeof opts.onProgress === 'function') ? opts.onProgress : null;

    const gen = this._beginOp(label);
    const total = arr.length;
    let start = Utils.now();
    let processedInBatch = 0;

    for (let i = 0; i < total; i++) {
      // Cancellation via AbortSignal or superseded generation (e.g., new render pass started).
      if ((signal && signal.aborted) || !this._isLatest(label, gen)) break;

      await fn(arr[i], i);

      if (release) {
        // Clear strong reference to the processed item to help GC on massive arrays.
        try { arr[i] = undefined; } catch (_) {}
      }

      processedInBatch++;
      if (onProgress) {
        // Call progress hook at most once per item (cheap); caller may throttle if needed.
        try { onProgress({ index: i + 1, total }); } catch (_) {}
      }

      if (processedInBatch >= batch || this.shouldYield(start)) {
        processedInBatch = 0;
        await this.yield();
        start = Utils.now();
      }
    }
  }

  // Chunked map with cooperative yielding. Returns a new array of results.
  // Options same as forEachChunk; accepts AbortSignal/label/batch/release/onProgress.
  async mapChunked(arr, mapper, labelOrOpts) {
    if (!arr || !arr.length) return [];
    const out = new Array(arr.length);
    let idx = 0;
    await this.forEachChunk(
      arr,
      async (v, i) => { out[i] = await mapper(v, i); idx = i; },
      labelOrOpts
    );
    return out;
  }

  // Chunked reduce with cooperative yielding.
  // reducer(acc, value, index) -> acc
  async reduceChunked(arr, reducer, initial, labelOrOpts) {
    let acc = initial;
    await this.forEachChunk(
      arr,
      async (v, i) => { acc = await reducer(acc, v, i); },
      labelOrOpts
    );
    return acc;
  }
}