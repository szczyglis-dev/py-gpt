// StreamLanguage owns language behavior and state.
class StreamLanguage {

	// ========================================
	// Composition
	// ========================================

	constructor(engine) {
		this.engine = engine;
	}

	// ========================================
	// Language detection and promotion
	// ========================================

	// Check if highlight.js knows this language.
	isHLJSSupported(lang) {
		try {
			return !!(window.hljs && hljs.getLanguage && hljs.getLanguage(lang));
		} catch (_) {
			return false;
		}
	}

	// Update language class on code element.
	updateCodeLangClass(codeEl, newLang) {
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
	updateCodeHeaderLabel(codeEl, newLabel, newLangToken) {
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
		if (!this.engine.code.activeCode || !this.engine.code.activeCode.codeEl) return;
		if (this.engine.code.activeCode.lang && this.engine.code.activeCode.lang !== 'plaintext') return;

		// Combine frozen + tail to inspect early lines.
		const frozenTxt = this.engine.code.activeCode.frozenEl ? this.engine.code.activeCode.frozenEl.textContent : '';
		const tailTxt = this.engine.code.activeCode.tailEl ? this.engine.code.activeCode.tailEl.textContent : '';
		const combined = frozenTxt + tailTxt;
		if (!combined) return;

		// Detect and extract language directive.
		const det = this._detectDirectiveLangFromText(combined);
		if (!det || !det.lang) return;

		const newLang = det.lang;
		const newCombined = combined.slice(det.deleteUpto);

		try {
			// Rebuild split spans with directive removed.
			const codeEl = this.engine.code.activeCode.codeEl;
			codeEl.innerHTML = '';
			const frozen = document.createElement('span');
			frozen.className = 'hl-frozen';
			const tail = document.createElement('span');
			tail.className = 'hl-tail';
			tail.textContent = newCombined;
			codeEl.appendChild(frozen);
			codeEl.appendChild(tail);
			this.engine.code.activeCode.frozenEl = frozen;
			this.engine.code.activeCode.tailEl = tail;
			this.engine.code.activeCode.frozenLen = 0;
			this.engine.code.activeCode.tailLines = Utils.countNewlines(newCombined);
			this.engine.code.activeCode.linesSincePromote = 0;

			// Update language label/classes.
			this.engine.code.activeCode.lang = newLang;
			this.updateCodeLangClass(codeEl, newLang);
			this.updateCodeHeaderLabel(codeEl, newLang, newLang);

			// Trigger immediate promotion so highlighting catches up.
			this.engine.debug('code.lang.directive.promote', {
				newLang,
				tailLen: newCombined.length
			});
			this.engine.code.schedulePromoteTail(true);
		} catch (e) {}
	}

	// ========================================
	// Language detection and promotion internals
	// ========================================

	// Map common language aliases to canonical highlight.js language ids.
	_aliasLang(token) {
		const v = String(token || '').trim().toLowerCase();
		return this.engine.highlighter.ALIAS[v] || v;
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
		this.engine.debug('code.lang.directive.detect', {
			lang: cand,
			deleteUpto: end
		});
		return {
			lang: cand,
			deleteUpto: end
		};
	}

}
