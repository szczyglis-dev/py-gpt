// ==========================================================================
// Utils
// ==========================================================================

class Utils {

	// Gets a global variable or returns a default value.
	static g(name, dflt) {
		return (typeof window[name] !== 'undefined') ? window[name] : dflt;
	}

	// Gets the current timestamp.
	static now() {
		return (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
	}

	// reuse a single detached element to reduce allocations on hot path.
	static escapeHtml(s) {
		const d = Utils._escDiv || (Utils._escDiv = document.createElement('div'));
		d.textContent = String(s ?? '');
		return d.innerHTML;
	}

	// Counts the number of newline characters in a string.
	static countNewlines(s) {
		if (!s) return 0;
		let c = 0,
			i = -1;
		while ((i = s.indexOf('\n', i + 1)) !== -1) c++;
		return c;
	}

	// Re-escapes a string for safe HTML rendering.
	static reEscape(s) {
		return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
	}

	// Schedule a function in idle time (falls back to setTimeout).
	static idle(fn, timeout) {
		if ('requestIdleCallback' in window) return requestIdleCallback(fn, {
			timeout: timeout || 800
		});
		return setTimeout(fn, 50);
	}

	// Cancel idle callback if possible (safe for fallback).
	static cancelIdle(id) {
		try {
			if ('cancelIdleCallback' in window) cancelIdleCallback(id);
			else clearTimeout(id);
		} catch (_) {}
	}

	// Gets the scrolling element for the document.
	static get SE() {
		return document.scrollingElement || document.documentElement;
	}

	// shared UTF-8 decoder to avoid per-call allocations.
	static utf8Decode(bytes) {
		if (!Utils._td) Utils._td = new TextDecoder('utf-8');
		return Utils._td.decode(bytes);
	}
}