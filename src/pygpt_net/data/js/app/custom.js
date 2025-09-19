// custom.js


// ==========================================================================
// Custom Markup Processor
// ==========================================================================

class CustomMarkup {

	// Constructor: set config, logger and initialize internal caches/flags
	constructor(cfg, logger) {
		this.cfg = cfg || {
			CUSTOM_MARKUP_RULES: []
		};
		this.logger = logger || new Logger(cfg);

		// Compiled state
		this.__compiled = null; // all rules
		this.__streamRules = null; // subset of stream rules (cache)
		this.__streamWrapRules = null; // subset: stream + html-phase, without open/closeReplace (cache)
		this.__hasStreamRules = false; // quick flag

		// Quick tests for the presence of "open" (avoid O(N*M) indexOf on hot path)
		this.__openReAll = null; // RegExp for all html-phase/both
		this.__openReStream = null; // RegExp for stream html-phase/both
	}

	// Debug helper: write structured log lines for the stream engine.
	_d(tag, data) {
        try {
            const lg = this.logger || (this.cfg && this.cfg.logger) || (window.runtime && runtime.logger) || null;
            if (!lg || typeof lg.debug !== 'function') return;
            lg.debug_obj("CM", tag, data);
        } catch (_) {}
    }

	// Decode HTML entities once using a <textarea> trick
	decodeEntitiesOnce(s) {
		if (!s || !s.indexOf || s.indexOf('&') === -1) return String(s || '');
		const ta = CustomMarkup._decTA || (CustomMarkup._decTA = document.createElement('textarea'));
		ta.innerHTML = s;
		return ta.value;
	}

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

	// Fast check if any "open" token from rules exists in text
	hasAnyOpenToken(text, rules) {
		if (!text || !rules || !rules.length) return false;
		if (rules === this.__compiled && this.__openReAll) {
			return this.__openReAll.test(text);
		}
		if (rules === this.__streamRules && this.__openReStream) {
			return this.__openReStream.test(text);
		}
		for (let i = 0; i < rules.length; i++) {
			const r = rules[i];
			if (!r || !r.open) continue;
			if (text.indexOf(r.open) !== -1) return true;
		}
		return false;
	}

	// fast check against stream rules’ open tokens
	hasAnyStreamOpenToken(text) {
		this.ensureCompiled();
		if (!this.__hasStreamRules) return false;
		const t = String(text || '');
		if (this.__openReStream) return this.__openReStream.test(t);
		const rules = this.__streamRules || [];
		return this.hasAnyOpenToken(t, rules);
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

    // Build a RegExp that matches any of the "open" tokens in the given rules
	_buildOpenRegex(rules) {
		if (!rules || !rules.length) return null;
		const tokens = [];
		let patternLen = 0;
		const LIMIT_TOKENS = 200;
		const LIMIT_PATTERN_LEN = 4000;

		for (const r of rules) {
			if (!r || !r.open) continue;
			const esc = Utils.reEscape(r.open);
			tokens.push(esc);
			patternLen += esc.length + 1;
			if (tokens.length > LIMIT_TOKENS || patternLen > LIMIT_PATTERN_LEN) return null;
		}
		if (!tokens.length) return null;
		tokens.sort((a, b) => b.length - a.length);
		try {
			return new RegExp('(?:' + tokens.join('|') + ')');
		} catch (_) {
			return null;
		}
	}

    // Compile rules from given array or config/global override
	compile(rules) {
		const src = Array.isArray(rules) ? rules :
			(window.CUSTOM_MARKUP_RULES || this.cfg.CUSTOM_MARKUP_RULES || []);
		const compiled = [];
		let hasStream = false;

		for (const r of src) {
			if (!r || typeof r.open !== 'string' || typeof r.close !== 'string') continue;

			const tag = (r.tag || 'span').toLowerCase();
			const className = (r.className || r.class || '').trim();
			const innerMode = (r.innerMode === 'markdown-inline' || r.innerMode === 'text') ? r.innerMode : 'text';

			const stream = !!(r.stream === true);
			const openReplace = String((r.openReplace != null ? r.openReplace : (r.openReplace || '')) || '');
			const closeReplace = String((r.closeReplace != null ? r.closeReplace : (r.closeReplace || '')) || '');

			const decodeEntities = (typeof r.decodeEntities === 'boolean') ?
				r.decodeEntities :
				((r.name || '').toLowerCase() === 'cmd' || className === 'cmd');

			let phaseRaw = (typeof r.phase === 'string') ? r.phase.toLowerCase() : '';
			if (phaseRaw !== 'source' && phaseRaw !== 'html' && phaseRaw !== 'both') phaseRaw = '';
			const looksLikeFence = (openReplace.indexOf('```') !== -1) || (closeReplace.indexOf('```') !== -1);
			const phase = phaseRaw || (looksLikeFence ? 'source' : 'html');

			const re = new RegExp(Utils.reEscape(r.open) + '([\\s\\S]*?)' + Utils.reEscape(r.close), 'g');
			const reFull = new RegExp('^' + Utils.reEscape(r.open) + '([\\s\\S]*?)' + Utils.reEscape(r.close) + '$');
			const reFullTrim = new RegExp('^\\s*' + Utils.reEscape(r.open) + '([\\s\\S]*?)' + Utils.reEscape(r.close) + '\\s*$');

			const nl2br = !!r.nl2br;
			const allowBr = !!r.allowBr;

			const item = {
				name: r.name || tag,
				tag,
				className,
				innerMode,
				open: r.open,
				close: r.close,
				decodeEntities,
				re,
				reFull,
				reFullTrim,
				stream,
				openReplace,
				closeReplace,
				phase,
				isSourceFence: looksLikeFence,
				nl2br,
				allowBr
			};
			compiled.push(item);
			if (stream) hasStream = true;
		}

		if (compiled.length === 0) {
			const open = '[!cmd]', close = '[/!cmd]';
			const item = {
				name: 'cmd',
				tag: 'p',
				className: 'cmd',
				innerMode: 'text',
				open,
				close,
				decodeEntities: true,
				re: new RegExp(Utils.reEscape(open) + '([\\s\\S]*?)' + Utils.reEscape(close), 'g'),
				reFull: new RegExp('^' + Utils.reEscape(open) + '([\\s\\S]*?)' + Utils.reEscape(close) + '$'),
				reFullTrim: new RegExp('^\\s*' + Utils.reEscape(open) + '([\\s\\S]*?)' + Utils.reEscape(close) + '\\s*$'),
				stream: false,
				openReplace: '',
				closeReplace: '',
				phase: 'html',
				isSourceFence: false,
				nl2br: false,
				allowBr: false
			};
			compiled.push(item);
		}

		this.__compiled = compiled;
		this.__hasStreamRules = hasStream;
		this.__streamRules = compiled.filter(r => !!r.stream);
		this.__streamWrapRules = this.__streamRules.filter(
			r => (r.phase === 'html' || r.phase === 'both') && !(r.openReplace || r.closeReplace) && r.open && r.close
		);

		const htmlPhaseAll = compiled.filter(r => (r.phase === 'html' || r.phase === 'both'));
		const htmlPhaseStream = this.__streamRules.filter(r => (r.phase === 'html' || r.phase === 'both'));
		this.__openReAll = this._buildOpenRegex(htmlPhaseAll);
		this.__openReStream = this._buildOpenRegex(htmlPhaseStream);

		this._d('cm.compile', { rules: compiled.length, streamRules: this.__streamRules.length });
		return compiled;
	}

    // Transform source text by applying source-phase rules outside fenced code blocks
	transformSource(src, opts) {
		let s = String(src || '');
		this.ensureCompiled();
		const rules = this.__compiled;
		if (!rules || !rules.length) return s;

		const candidates = [];
		for (let i = 0; i < rules.length; i++) {
			const r = rules[i];
			if (!r) continue;
			if ((r.phase === 'source' || r.phase === 'both') && (r.openReplace || r.closeReplace)) candidates.push(r);
		}
		if (!candidates.length) return s;

		const fences = this._findFenceRanges(s);
		let result = '';
		if (!fences.length) {
			result = this._applySourceReplacementsInChunk(s, s, 0, candidates);
		} else {
			let out = '', last = 0;
			for (let k = 0; k < fences.length; k++) {
				const [a, b] = fences[k];
				if (a > last) {
					const chunk = s.slice(last, a);
					out += this._applySourceReplacementsInChunk(s, chunk, last, candidates);
				}
				out += s.slice(a, b);
				last = b;
			}
			if (last < s.length) {
				const tail = s.slice(last);
				out += this._applySourceReplacementsInChunk(s, tail, last, candidates);
			}
			result = out;
		}

		if (opts && opts.streaming === true) {
			const fenceRules = candidates.filter(r => !!r.isSourceFence);
			if (fenceRules.length) result = this._injectUnmatchedSourceOpeners(result, fenceRules);
		}

		if (result !== src) this._d('cm.transformSource', { streaming: !!(opts && opts.streaming), delta: result.length - String(src || '').length });
		return result;
	}

    // Get specs of all source fence rules
	getSourceFenceSpecs() {
		this.ensureCompiled();
		const rules = this.__compiled || [];
		const out = [];
		for (let i = 0; i < rules.length; i++) {
			const r = rules[i];
			if (!r || !r.isSourceFence) continue;
			if (r.phase !== 'source' && r.phase !== 'both') continue;
			out.push({ open: r.open, close: r.close });
		}
		return out;
	}

    // Ensure the rules are compiled (from global override or config)
	ensureCompiled() {
		if (!this.__compiled) {
			this.compile(window.CUSTOM_MARKUP_RULES || this.cfg.CUSTOM_MARKUP_RULES);
		}
		return this.__compiled;
	}

    // Set a new set of rules (overrides global and config)
	setRules(rules) {
		this.compile(rules);
		window.CUSTOM_MARKUP_RULES = Array.isArray(rules) ? rules.slice() :
			(this.cfg.CUSTOM_MARKUP_RULES || []).slice();
		this._d('cm.setRules', { count: (window.CUSTOM_MARKUP_RULES || []).length });
	}

    // Get the current set of rules (from global override or config)
	getRules() {
		const list = (window.CUSTOM_MARKUP_RULES ? window.CUSTOM_MARKUP_RULES.slice() :
			(this.cfg.CUSTOM_MARKUP_RULES || []).slice());
		return list;
	}

    // Quick check if any stream rules are defined
	hasStreamRules() {
		this.ensureCompiled();
		return !!this.__hasStreamRules;
	}

    // Quick check if text starts with any known stream opener
	hasStreamOpenerAtStart(text) {
		if (!text) return false;
		this.ensureCompiled();
		if (!this.__hasStreamRules) return false;
		const rules = this.__streamRules || [];
		if (!rules.length) return false;
		const t = String(text).trimStart();
		for (let i = 0; i < rules.length; i++) {
			const r = rules[i];
			if (!r || !r.open) continue;
			if (t.startsWith(r.open)) return true;
		}
		return false;
	}

    // Apply to stream if the delta text contains any known opener.
	maybeApplyStreamOnDelta(root, deltaText, MD) {
		try {
			this.ensureCompiled();
			if (!this.__hasStreamRules) return;
			const t = String(deltaText || '');

			// If the delta contains any known stream opener, run full stream pass quickly.
			if (t && this.hasAnyStreamOpenToken(t)) {
				this._d('cm.stream.delta', { len: t.length, head: t.slice(0, 64) });
				this.applyStream(root, MD);
				return;
			}

			// If there are pending wrappers in the snapshot root and the delta likely carries closers,
			// finalize them immediately (cheap pass limited to pending subtrees).
			if (root && root.querySelector && root.querySelector('[data-cm-pending="1"]')) {
				if (t.indexOf('>') !== -1 || t.indexOf(']') !== -1) {
					this.applyStreamFinalizeClosers(root, this.__streamRules);
					this._d('cm.stream.delta.finalize', {});
				}
			}
		} catch (_) { return; }
	}

    // Apply stream processing to the given subtree
	applyStream(root, MD) {
		this.ensureCompiled();
		if (!this.__hasStreamRules) return;
		const rules = this.__streamRules;
		if (!rules || !rules.length) return;

		this.applyRules(root, MD, rules);

		try {
			this.applyStreamPartialOpeners(root, MD, this.__streamWrapRules);
		} catch (_) {}

		try {
			this.applyStreamFinalizeClosers(root, rules);
		} catch (_) {}
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
	_tryReplaceFullParagraph(el, rules, MD) {
		if (!el || el.tagName !== 'P') return false;
		if (this.isInsideForbiddenElement(el)) {
			return false;
		}
		const t = el.textContent || '';
		if (!this.hasAnyOpenToken(t, rules)) return false;

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
				this._d('cm.replace.full', { name: rule.name });
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
			this._d('cm.wrap.full', { name: rule.name });
			return true;
		}
		return false;
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
					if (!tc || !this.hasAnyOpenToken(tc, rules)) continue;
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
			if (!text || !this.hasAnyOpenToken(text, rules)) continue;
			const parent = node.parentElement;

			if (parent && parent.tagName === 'P' && parent.childNodes.length === 1) {
				const fm = this.findFullMatch(text, rules);
				if (fm) {
					if ((fm.rule.phase === 'html' || fm.rule.phase === 'both') && (fm.rule.openReplace || fm.rule.closeReplace)) {
						const innerHTML = this._materializeInnerHTML(fm.rule, fm.inner, MD);
						const html = String(fm.rule.openReplace || '') + innerHTML + String(fm.rule.closeReplace || '');
						this._replaceElementWithHTML(parent, html);
						this._d('cm.replace.inlineFull', { name: fm.rule.name });
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
						this._d('cm.wrap.paragraph', { name: fm.rule.name });
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
					this._d('cm.replace.inline', { name: m.rule.name });
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
				this._d('cm.wrap.inline', { name: m.rule.name });

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
		this.ensureCompiled();
		this.applyRules(root, MD, this.__compiled);
	}

    // Handle partial openers that lack a closer in the current subtree
	applyStreamPartialOpeners(root, MD, rules) {
		if (!root) return;
		rules = (rules || this.__streamWrapRules || []).slice();
		if (!rules.length) return;

		const scope = (root.nodeType === 1 || root.nodeType === 11) ? root : document;
		const self = this;

		const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT, {
			acceptNode(node) {
			 const val = node && node.nodeValue ? node.nodeValue : '';
			 if (!val || !self.hasAnyOpenToken(val, rules)) return NodeFilter.FILTER_SKIP;
			 if (self.isInsideForbiddenContext(node)) return NodeFilter.FILTER_REJECT;
			 return NodeFilter.FILTER_ACCEPT;
			}
		});

		let node;
		while ((node = walker.nextNode())) {
			const text = node.nodeValue || '';
			if (!text) continue;

			let best = null; // { rule, start }
			for (let i = 0; i < rules.length; i++) {
				const r = rules[i];
				if (!r || !r.open || !r.close) continue;

				const idx = text.lastIndexOf(r.open);
				if (idx === -1) continue;

				const after = text.indexOf(r.close, idx + r.open.length);
				if (after !== -1) continue;

				if (!best || idx > best.start) best = { rule: r, start: idx };
			}

			if (!best) continue;

			const r = best.rule;
			const start = best.start;
			const openLen = r.open.length;
			const prefixText = text.slice(0, start);
			const fromOffset = start + openLen;

			try {
				const range = document.createRange();
				range.setStart(node, Math.min(fromOffset, node.nodeValue.length));

				let endNode = root;
				try {
					endNode = (root.nodeType === 11 || root.nodeType === 1) ? root : node.parentNode;
					while (endNode && endNode.lastChild) endNode = endNode.lastChild;
				} catch (_) {}
				if (endNode && endNode.nodeType === 3) range.setEnd(endNode, endNode.nodeValue.length);
				else if (endNode) range.setEndAfter(endNode);
				else range.setEndAfter(node);

				const remainder = range.extractContents();

				const outTag = (r.tag && typeof r.tag === 'string') ? r.tag.toLowerCase() : 'span';
				const hostTag = (outTag === 'p') ? 'span' : outTag;
				const el = document.createElement(hostTag);
				if (r.className) el.className = r.className;
				el.setAttribute('data-cm', r.name);
				el.setAttribute('data-cm-pending', '1');

				el.appendChild(remainder);
				range.insertNode(el);
				range.detach();

				try { node.nodeValue = prefixText; } catch (_) {}
				this._d('cm.stream.open.pending', { name: r.name });
				return;
			} catch (err) {
				try {
					const tail = text.slice(start + r.open.length);
					const frag = document.createDocumentFragment();

					if (prefixText) frag.appendChild(document.createTextNode(prefixText));

					const el = document.createElement((r.tag === 'p') ? 'span' : r.tag);
					if (r.className) el.className = r.className;
					el.setAttribute('data-cm', r.name);
					el.setAttribute('data-cm-pending', '1');

					this.setInnerByMode(el, r.innerMode, tail, MD, !!r.decodeEntities, r);
					frag.appendChild(el);

					node.parentNode.replaceChild(frag, node);
					this._d('cm.stream.open.pending.fallback', { name: r.name });
					return;
				} catch (_) {}
			}
		}
	}

    // Finalize any pending openers if their closer token is found in the subtree
	applyStreamFinalizeClosers(root, rulesAll) {
		if (!root) return;

		const scope = (root.nodeType === 1 || root.nodeType === 11) ? root : document;
		const pending = scope.querySelectorAll('[data-cm][data-cm-pending="1"]');
		if (!pending || !pending.length) return;

		const rulesByName = new Map();
		(rulesAll || []).forEach(r => { if (r && r.name) rulesByName.set(r.name, r); });

		for (let i = 0; i < pending.length; i++) {
			const el = pending[i];
			const name = el.getAttribute('data-cm') || '';
			const rule = rulesByName.get(name);
			if (!rule || !rule.close) continue;

			const self = this;
			const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
				acceptNode(node) {
					const val = node && node.nodeValue ? node.nodeValue : '';
					if (!val || val.indexOf(rule.close) === -1) return NodeFilter.FILTER_SKIP;
					if (self.isInsideForbiddenContext(node)) return NodeFilter.FILTER_REJECT;
					return NodeFilter.FILTER_ACCEPT;
				}
			});

			let nodeWithClose = null;
			let idxInNode = -1;
			let tn;
			while ((tn = walker.nextNode())) {
				const idx = tn.nodeValue.indexOf(rule.close);
				if (idx !== -1) {
					nodeWithClose = tn;
					idxInNode = idx;
					break;
				}
			}
			if (!nodeWithClose) continue;

			try {
				const tokenLen = rule.close.length;

				const afterRange = document.createRange();
				afterRange.setStart(nodeWithClose, idxInNode + tokenLen);
				let endNode = el;
				while (endNode && endNode.lastChild) endNode = endNode.lastChild;
				if (endNode && endNode.nodeType === 3) afterRange.setEnd(endNode, endNode.nodeValue.length);
				else afterRange.setEndAfter(el.lastChild || el);

				const tail = afterRange.extractContents();
				afterRange.detach();

				const tok = document.createRange();
				tok.setStart(nodeWithClose, idxInNode);
				tok.setEnd(nodeWithClose, idxInNode + tokenLen);
				tok.deleteContents();
				tok.detach();

				if (el.parentNode && tail && tail.childNodes.length) {
					el.parentNode.insertBefore(tail, el.nextSibling);
				}

				el.removeAttribute('data-cm-pending');
				this._d('cm.stream.close.finalize', { name });
			} catch (err) {}
		}
	}

    // Find all fenced code block ranges in source text
	_findFenceRanges(s) {
		const ranges = [];
		const n = s.length;
		let i = 0;
		let inFence = false;
		let fenceMark = '';
		let fenceLen = 0;
		let startLineStart = 0;

		while (i < n) {
			const lineStart = i;
			let j = lineStart;
			while (j < n && s.charCodeAt(j) !== 10 && s.charCodeAt(j) !== 13) j++;
			const lineEnd = j;
			let nl = 0;
			if (j < n) {
				if (s.charCodeAt(j) === 13 && j + 1 < n && s.charCodeAt(j + 1) === 10) nl = 2;
				else nl = 1;
			}

			let k = lineStart;
			let indent = 0;
			while (k < lineEnd) {
				const c = s.charCodeAt(k);
				if (c === 32) {
					indent++;
					if (indent > 3) break;
					k++;
				} else if (c === 9) {
					indent++;
					if (indent > 3) break;
					k++;
				} else break;
			}

			if (!inFence) {
				if (indent <= 3 && k < lineEnd) {
					const ch = s.charCodeAt(k);
					if (ch === 0x60 || ch === 0x7E) {
						const mark = String.fromCharCode(ch);
						let m = k;
						while (m < lineEnd && s.charCodeAt(m) === ch) m++;
						const run = m - k;
						if (run >= 3) {
							inFence = true;
							fenceMark = mark;
							fenceLen = run;
							startLineStart = lineStart;
						}
					}
				}
			} else {
				if (indent <= 3 && k < lineEnd && s.charCodeAt(k) === fenceMark.charCodeAt(0)) {
					let m = k;
					while (m < lineEnd && s.charCodeAt(m) === fenceMark.charCodeAt(0)) m++;
					const run = m - k;
					if (run >= fenceLen) {
						let onlyWS = true;
						for (let t = m; t < lineEnd; t++) {
							const cc = s.charCodeAt(t);
							if (cc !== 32 && cc !== 9) { onlyWS = false; break; }
						}
						if (onlyWS) {
							const endIdx = lineEnd + nl;
							ranges.push([startLineStart, endIdx]);
							inFence = false;
							fenceMark = '';
							fenceLen = 0;
							startLineStart = 0;
						}
					}
				}
			}
			i = lineEnd + nl;
		}
		if (inFence) ranges.push([startLineStart, n]);
		return ranges;
	}

    // Check if a given absolute index in source text is at top-level line (not indented >3, not in list/quote)
	_isTopLevelLineInSource(s, absIdx) {
		let ls = absIdx;
		while (ls > 0) {
			const ch = s.charCodeAt(ls - 1);
			if (ch === 10 || ch === 13) break;
			ls--;
		}
		const prefix = s.slice(ls, absIdx);
		let i = 0, indent = 0;
		while (i < prefix.length) {
			const c = prefix.charCodeAt(i);
			if (c === 32) { indent++; if (indent > 3) break; i++; }
			else if (c === 9) { indent++; if (indent > 3) break; i++; }
			else break;
		}
		if (indent > 3) return false;
		const rest = prefix.slice(i);
		if (/^>\s?/.test(rest)) return false;
		if (/^[-+*]\s/.test(rest)) return false;
		if (/^\d+[.)]\s/.test(rest)) return false;
		if (rest.trim().length > 0) return false;
		return true;
	}

    // Apply source replacements in a given chunk of text, checking line starts against full text
	_applySourceReplacementsInChunk(full, chunk, baseOffset, rules) {
		let t = chunk;
		for (let i = 0; i < rules.length; i++) {
			const r = rules[i];
			if (!r || !(r.openReplace || r.closeReplace)) continue;
			try {
				r.re.lastIndex = 0;
				t = t.replace(r.re, (match, inner, offset) => {
					const abs = baseOffset + (offset | 0);
					if (!this._isTopLevelLineInSource(full, abs)) return match;
					const open = r.openReplace || '';
					const close = r.closeReplace || '';
					return open + (inner || '') + close;
				});
			} catch (_) {}
		}
		return t;
	}

    // In streaming mode, if there is any unmatched opener at the end of the text,
	_injectUnmatchedSourceOpeners(text, fenceRules) {
		let s = String(text || '');
		if (!s || !fenceRules || !fenceRules.length) return s;

		let best = null; // { r, idx }
		for (let i = 0; i < fenceRules.length; i++) {
			const r = fenceRules[i];
			if (!r || !r.open || !r.close || !r.openReplace) continue;

			const idx = s.lastIndexOf(r.open);
			if (idx === -1) continue;

			if (!this._isTopLevelLineInSource(s, idx)) continue;

			const after = s.indexOf(r.close, idx + r.open.length);
			if (after !== -1) continue;

			if (!best || idx > best.idx) best = { r, idx };
		}

		if (!best) return s;

		const r = best.r, i = best.idx;
		const before = s.slice(0, i);
		const after = s.slice(i + r.open.length);
		const injected = String(r.openReplace || '');
		this._d('cm.inject.open', { name: r.name });
		return before + injected + after;
	}
}