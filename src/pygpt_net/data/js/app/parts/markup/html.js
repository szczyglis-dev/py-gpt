// CustomMarkupHtml owns html behavior and state.
class CustomMarkupHtml {

	// ========================================
	// Composition
	// ========================================

	constructor(markup) {
		this.markup = markup;
	}

	// ========================================
	// Html
	// ========================================

	// Decode HTML entities once using a <textarea> trick
	decodeEntitiesOnce(s) {
		if (!s || !s.indexOf || s.indexOf('&') === -1) return String(s || '');
		const ta = CustomMarkup._decTA || (CustomMarkup._decTA = document.createElement('textarea'));
		ta.innerHTML = s;
		return ta.value;
	}

    // Finalize any openers that lack a closer in the current subtree
	isInsideForbiddenContext(node) {
		const p = node.parentElement;
		if (!p) return true;
		return !!p.closest('pre, code, kbd, samp, var, script, style, textarea, .math-pending, .hljs, .code-wrapper, ul, ol, li, dl, dt, dd');
	}

    // Check if an element is inside a forbidden element
	isInsideForbiddenElement(el) {
		if (!el) return true;
		return !!el.closest('pre, code, kbd, samp, var, script, style, textarea, .math-pending, .hljs, .code-wrapper, ul, ol, li, dl, dt, dd');
	}

    // Find all source fence ranges in the text
	findNextMatch(text, from, rules) {
		let best = null;
		for (const rule of rules) {
			rule.re.lastIndex = from;
			const m = rule.re.exec(text);
			if (m) {
				const start = m.index, end = rule.re.lastIndex;
				if (!best || start < best.start) best = { rule, start, end, inner: m[1] || '' };
			}
		}
		return best;
	}

    // Find a full match that spans the entire text
	findFullMatch(text, rules) {
		for (const rule of rules) {
			if (rule.reFull) {
				const m = rule.reFull.exec(text);
				if (m) return { rule, inner: m[1] || '' };
			} else {
				rule.re.lastIndex = 0;
				const m = rule.re.exec(text);
				if (m && m.index === 0 && (rule.re.lastIndex === text.length)) {
					const m2 = rule.re.exec(text);
					if (!m2) return { rule, inner: m[1] || '' };
				}
			}
		}
		return null;
	}

    // Set inner content of an element according to mode and rule options
	setInnerByMode(el, mode, text, MD, decodeEntities = false, rule = null) {
		let payload = String(text || '');
		const wantsBr = !!(rule && (rule.nl2br || rule.allowBr));

		if (decodeEntities && payload && payload.indexOf('&') !== -1) {
			try {
				payload = this.decodeEntitiesOnce(payload);
			} catch (_) {}
		}

		if (wantsBr) {
			el.innerHTML = this._escapeHtmlAllowBr(payload, { convertNewlines: !!(rule && rule.nl2br) });
			return;
		}

		if (mode === 'markdown-inline' && MD && typeof MD.renderInline === 'function') {
			try {
				el.innerHTML = MD.renderInline(payload);
				return;
			} catch (_) {}
		}
		el.textContent = payload;
	}

    // Finalize any openers that lack a closer in the current subtree
	applyRules(root, MD, rules) {
		if (!root || !rules || !rules.length) return;

		const scope = (root.nodeType === 1 || root.nodeType === 11) ? root : document;

		try {
			const paragraphs = (typeof scope.querySelectorAll === 'function') ? scope.querySelectorAll('p') : [];
			if (paragraphs && paragraphs.length) {
				for (let i = 0; i < paragraphs.length; i++) {
					const p = paragraphs[i];
					if (p && p.getAttribute && p.getAttribute('data-cm')) continue;
					const tc = p && (p.textContent || '');
					if (!tc || !this.markup.hasAnyOpenToken(tc, rules)) continue;
					if (this.isInsideForbiddenElement(p)) continue;
					this._tryReplaceFullParagraph(p, rules, MD);
				}
			}
		} catch (e) {}

		const self = this;
		const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
			acceptNode: (node) => {
				const val = node && node.nodeValue ? node.nodeValue : '';
				if (!val || !self.hasAnyOpenToken(val, rules)) return NodeFilter.FILTER_SKIP;
				if (self.isInsideForbiddenContext(node)) return NodeFilter.FILTER_REJECT;
				return NodeFilter.FILTER_ACCEPT;
			}
		});

		let node;
		while ((node = walker.nextNode())) {
			const text = node.nodeValue;
			if (!text || !this.markup.hasAnyOpenToken(text, rules)) continue;
			const parent = node.parentElement;

			if (parent && parent.tagName === 'P' && parent.childNodes.length === 1) {
				const fm = this.findFullMatch(text, rules);
				if (fm) {
					if ((fm.rule.phase === 'html' || fm.rule.phase === 'both') && (fm.rule.openReplace || fm.rule.closeReplace)) {
						const innerHTML = this._materializeInnerHTML(fm.rule, fm.inner, MD);
						const html = String(fm.rule.openReplace || '') + innerHTML + String(fm.rule.closeReplace || '');
						this._replaceElementWithHTML(parent, html);
						this.markup.debug('cm.replace.inlineFull', { name: fm.rule.name });
						continue;
					}
					if (fm.rule.tag === 'p') {
						const out = document.createElement('p');
						if (fm.rule.className) out.className = fm.rule.className;
						out.setAttribute('data-cm', fm.rule.name);
						this.setInnerByMode(out, fm.rule.innerMode, fm.inner, MD, !!fm.rule.decodeEntities, fm.rule);
						try {
							parent.replaceWith(out);
						} catch (_) {
							const par = parent.parentNode;
							if (par) par.replaceChild(out, parent);
						}
						this.markup.debug('cm.wrap.paragraph', { name: fm.rule.name });
						continue;
					}
				}
			}

			let i = 0;
			let didReplace = false;
			const frag = document.createDocumentFragment();

			while (i < text.length) {
				const m = this.findNextMatch(text, i, rules);
				if (!m) break;

				if (m.start > i) {
					frag.appendChild(document.createTextNode(text.slice(i, m.start)));
				}

				if ((m.rule.openReplace || m.rule.closeReplace) && (m.rule.phase === 'html' || m.rule.phase === 'both')) {
					const innerHTML = this._materializeInnerHTML(m.rule, m.inner, MD);
					const html = String(m.rule.openReplace || '') + innerHTML + String(m.rule.closeReplace || '');
					const part = this._fragmentFromHTML(html);
					frag.appendChild(part);
					i = m.end;
					didReplace = true;
					this.markup.debug('cm.replace.inline', { name: m.rule.name });
					continue;
				}

				if (m.rule.openReplace || m.rule.closeReplace) {
					frag.appendChild(document.createTextNode(text.slice(m.start, m.end)));
					i = m.end;
					didReplace = true;
					continue;
				}

				const tag = (m.rule.tag === 'p') ? 'span' : m.rule.tag;
				const el = document.createElement(tag);
				if (m.rule.className) el.className = m.rule.className;
				el.setAttribute('data-cm', m.rule.name);
				this.setInnerByMode(el, m.rule.innerMode, m.inner, MD, !!m.rule.decodeEntities, m.rule);
				frag.appendChild(el);
				this.markup.debug('cm.wrap.inline', { name: m.rule.name });

				i = m.end;
				didReplace = true;
			}

			if (!didReplace) continue;
			if (i < text.length) frag.appendChild(document.createTextNode(text.slice(i)));
			const parentNode = node.parentNode;
			if (parentNode) {
				parentNode.replaceChild(frag, node);
			}
		}
	}

    // Apply all rules to the given subtree
	apply(root, MD) {
		this.markup.ensureCompiled();
		this.applyRules(root, MD, this.markup.compiledRules);
	}

	// ========================================
	// Html internals
	// ========================================

	// Escape HTML safely (fallback if Utils.escapeHtml is missing)
	_escHtml(s) {
		try {
			return Utils.escapeHtml(s);
		} catch (_) {
			return String(s || '').replace(/[&<>"']/g, m => ({
				'&': '&amp;',
				'<': '&lt;',
				'>': '&gt;',
				'"': '&quot;',
				"'": '&#039;'
			} [m]));
		}
	}

	// Escape HTML but preserve <br> and optionally convert newlines to <br>
	_escapeHtmlAllowBr(text, { convertNewlines = true } = {}) {
		const PLACEHOLDER = '\u0001__BR__\u0001';
		let s = String(text || '');
		s = s.replace(/<br\s*\/?>/gi, PLACEHOLDER);
		s = this._escHtml(s);
		if (convertNewlines) s = s.replace(/\r\n|\r|\n/g, '<br>');
		s = s.replaceAll(PLACEHOLDER, '<br>');
		return s;
	}

	// Convert inner text to HTML depending on rule options and Markdown renderer
	_materializeInnerHTML(rule, text, MD) {
		let payload = String(text || '');
		const wantsBr = !!(rule && (rule.nl2br || rule.allowBr));
		if (rule && rule.decodeEntities && payload && payload.indexOf('&') !== -1) {
			try { payload = this.decodeEntitiesOnce(payload); } catch (_) {}
		}
		if (wantsBr) {
			try {
				return this._escapeHtmlAllowBr(payload, { convertNewlines: !!rule.nl2br });
			} catch (_) {
				return this._escHtml(payload);
			}
		}
		if (rule && rule.innerMode === 'markdown-inline' && MD && typeof MD.renderInline === 'function') {
			try {
				return MD.renderInline(payload);
			} catch (_) {
				return this._escHtml(payload);
			}
		}
		return this._escHtml(payload);
	}

    // Get a DocumentFragment from HTML string
	_fragmentFromHTML(html) {
		const tpl = document.createElement('template');
		tpl.innerHTML = String(html || '');
		return tpl.content;
	}

    // Replace an element with HTML content
	_replaceElementWithHTML(el, html) {
		if (!el || !el.parentNode) return;
		const parent = el.parentNode;
		const frag = this._fragmentFromHTML(html);
		parent.insertBefore(frag, el);
		parent.removeChild(el);
	}

    // Finalize any openers that lack a closer in the current subtree
	_tryReplaceFullParagraph(el, rules, MD) {
		if (!el || el.tagName !== 'P') return false;
		if (this.isInsideForbiddenElement(el)) {
			return false;
		}
		const t = el.textContent || '';
		if (!this.markup.hasAnyOpenToken(t, rules)) return false;

		for (const rule of rules) {
			if (!rule) continue;
			const m = rule.reFullTrim ? rule.reFullTrim.exec(t) : null;
			if (!m) continue;

			const innerText = m[1] || '';
			if (rule.phase !== 'html' && rule.phase !== 'both') continue;

			if (rule.openReplace || rule.closeReplace) {
				const innerHTML = this._materializeInnerHTML(rule, innerText, MD);
				const html = String(rule.openReplace || '') + innerHTML + String(rule.closeReplace || '');
				this._replaceElementWithHTML(el, html);
				this.markup.debug('cm.replace.full', { name: rule.name });
				return true;
			}

			const outTag = (rule.tag && typeof rule.tag === 'string') ? rule.tag.toLowerCase() : 'span';
			const out = document.createElement(outTag === 'p' ? 'p' : outTag);
			if (rule.className) out.className = rule.className;
			out.setAttribute('data-cm', rule.name);
			this.setInnerByMode(out, rule.innerMode, innerText, MD, !!rule.decodeEntities, rule);

			try {
				el.replaceWith(out);
			} catch (_) {
				const par = el.parentNode;
				if (par) par.replaceChild(out, el);
			}
			this.markup.debug('cm.wrap.full', { name: rule.name });
			return true;
		}
		return false;
	}

}
