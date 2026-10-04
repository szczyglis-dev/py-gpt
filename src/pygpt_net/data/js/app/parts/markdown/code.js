const MARKDOWN_LANGUAGE_ALIASES = {
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

class MarkdownCodeRules {

	// ========================================
	// Composition
	// ========================================

	constructor(renderer, mode) {
		this.renderer = renderer;
		this.mode = mode;
		this._codeIndex = 1;
	}

	// ========================================
	// Code
	// ========================================

	install(md) {
		md.renderer.rules.fence = (tokens, idx, options, env) => this._renderFence(tokens[idx], env);
		md.renderer.rules.code_block = (tokens, idx, options, env) => this._renderFence({info: "", content: tokens[idx].content || ""}, env);
	}

	// ========================================
	// Code internals
	// ========================================

	_normLang(s) {
		if (!s) return '';
		const v = String(s).trim().toLowerCase();
		return MARKDOWN_LANGUAGE_ALIASES[v] || v;
	}

	_isSupportedByHLJS(lang) {
		try {
			return !!(window.hljs && hljs.getLanguage && hljs.getLanguage(lang));
		} catch (_) {
			return false;
		}
	}

	_classForHighlight(lang) {
		if (!lang) return 'plaintext';
		return this._isSupportedByHLJS(lang) ? lang : 'plaintext';
	}

	_stripBOM(s) {
		return (s && s.charCodeAt(0) === 0xFEFF) ? s.slice(1) : s;
	}

	_normForFP(s) {
		if (!s) return '';
		let t = String(s);
		if (t.charCodeAt(0) === 0xFEFF) t = t.slice(1);
		t = t.replace(/\r\n?/g, '\n');
		if (t.endsWith('\n')) t = t.slice(0, -1);
		return t;
	}

	_hash32FNV(str) {
		let h = 0x811c9dc5 >>> 0;
		for (let i = 0; i < str.length; i++) {
			h ^= str.charCodeAt(i);
			h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
		}
		return ('00000000' + h.toString(16)).slice(-8);
	}

	_makeStableFP(langToken, rawContent) {
		const norm = this._normForFP(rawContent || '');
		return `${langToken || 'plaintext'}|${norm.length}|${this._hash32FNV(norm)}`;
	}

	_detectFromFirstLine(raw, rid) {
		if (!raw) return {
			lang: '',
			content: raw,
			isOutput: false
		};
		const lines = raw.split(/\r?\n/);
		if (!lines.length) return {
			lang: '',
			content: raw,
			isOutput: false
		};
		let i = 0;
		while (i < lines.length && !lines[i].trim()) i++;
		if (i >= lines.length) return {
			lang: '',
			content: raw,
			isOutput: false
		};
		let first = this._stripBOM(lines[i]).trim();
		first = first.replace(/^\s*lang(?:uage)?\s*[:=]\s*/i, '').trim();
		let token = first.split(/\s+/)[0].replace(/:$/, '');
		if (!/^[A-Za-z][\w#+\-\.]{0,30}$/.test(token)) return {
			lang: '',
			content: raw,
			isOutput: false
		};
		let cand = this._normLang(token);
		if (cand === 'output') {
			const content = lines.slice(i + 1).join('\n');
			return {
				lang: 'python',
				headerLabel: 'output',
				content,
				isOutput: true
			};
		}
		const rest = lines.slice(i + 1).join('\n');
		if (!rest.trim()) return {
			lang: '',
			content: raw,
			isOutput: false
		};
		return {
			lang: cand,
			headerLabel: cand,
			content: rest,
			isOutput: false
		};
	}

	_resolveLanguageAndContent(info, raw, rid) {
		const infoLangRaw = (info || '').trim().split(/\s+/)[0] || '';
		let cand = this._normLang(infoLangRaw);

		// Treat too-short/unsupported tokens as unreliable; ignore and fall back.
		const shortOrUnsupported = !cand || cand.length < 3 || !this._isSupportedByHLJS(cand);

		if (cand === 'output') {
			return {
				lang: 'python',
				headerLabel: 'output',
				content: raw,
				isOutput: true
			};
		}
		if (!shortOrUnsupported) {
			return {
				lang: cand,
				headerLabel: cand,
				content: raw,
				isOutput: false
			};
		}

		// Fallback: try to detect from first code line (directive like "python" etc.)
		const det = this._detectFromFirstLine(raw, rid);
		if (det && (det.lang || det.isOutput)) return det;

		// Last resort
		return {
			lang: '',
			headerLabel: 'code',
			content: raw,
			isOutput: false
		};
	}

	_renderFence(token, env) {
		const rendererRef = this.renderer;
		const cfg = this.renderer.cfg;
		const raw = token.content || '';
		const toolCode = !!(env && env.__toolCode);
		const highlightAttrs = toolCode ? ' data-highlighted="yes"' : '';
		const rid = String(this._codeIndex + '');

		const res = this._resolveLanguageAndContent(token.info || '', raw, rid);
		const isOutput = !!res.isOutput;
		const rawToken = (res.lang || '').trim();
		const langClass = isOutput ? 'python' : this._classForHighlight(rawToken);

		let headerLabel = isOutput ? 'output' : (res.headerLabel || (rawToken || 'code'));
		if (!isOutput) {
			if (rawToken && !this._isSupportedByHLJS(rawToken) && rawToken.length < 3) headerLabel = 'code';
		}
		const customHeaderLabel = env && env.__codeHeaderLabel ? String(env.__codeHeaderLabel) : '';
		if (customHeaderLabel) headerLabel = customHeaderLabel;

		const content = res.content || '';
		const len = content.length;
		const head = content.slice(0, 64);
		const tail = content.slice(-64);
		const headEsc = Utils.escapeHtml(head);
		const tailEsc = Utils.escapeHtml(tail);
		const nl = Utils.countNewlines(content);
		const fpStable = this._makeStableFP(langClass, content);

		const idxLocal = this._codeIndex++;

		let actions = '';
		if (!(env && env.__toolCode) && langClass === 'html') {
			actions += `<a href="empty:${idxLocal}" class="code-header-action code-header-preview"><img src="${cfg.ICONS.CODE_PREVIEW}" class="action-img" data-id="${idxLocal}"><span>${Utils.escapeHtml(cfg.LOCALE.PREVIEW)}</span></a>`;
		} else if (!(env && env.__toolCode) && langClass === 'python' && headerLabel !== 'output') {
			actions += `<a href="empty:${idxLocal}" class="code-header-action code-header-run"><img src="${cfg.ICONS.CODE_RUN}" class="action-img" data-id="${idxLocal}"><span>${Utils.escapeHtml(cfg.LOCALE.RUN)}</span></a>`;
		}
		if (env && env.__toolToggle) {
			const rawView = document.documentElement.dataset.toolView === 'raw';
			actions += `<button type="button" class="code-header-tool-view" onclick="toggleToolPayloadView(this);" title="${Utils.escapeHtml(rawView ? cfg.LOCALE.TOOL_VIEW_PLAIN : cfg.LOCALE.TOOL_VIEW_RAW)}" aria-label="${Utils.escapeHtml(rawView ? cfg.LOCALE.TOOL_VIEW_PLAIN : cfg.LOCALE.TOOL_VIEW_RAW)}" aria-pressed="${rawView}">&lt;&gt;</button>`;
		}
		actions += `<a href="empty:${idxLocal}" class="code-header-action code-header-collapse" title="${Utils.escapeHtml(cfg.LOCALE.COLLAPSE)}"><img src="${cfg.ICONS.CODE_MENU}" class="action-img" data-id="${idxLocal}"></a>`;
                actions += `<a href="empty:${idxLocal}" class="code-header-action code-header-copy" title="${Utils.escapeHtml(cfg.LOCALE.COPY)}"><img src="${cfg.ICONS.CODE_COPY}" class="action-img" data-id="${idxLocal}"></a>`;

		const canUseRegistry = !!(rendererRef && typeof rendererRef.registerCode === 'function' && env);
		if (canUseRegistry) {
			const codeId = rendererRef.registerCode(env, content);
			// DEBUG
			rendererRef.debug && rendererRef.debug(`fence.${this.mode}`, {
				idxLocal,
				lang: langClass,
				headerLabel,
				len
			});
			return (
				`<div class="code-wrapper highlight" data-index="${idxLocal}"` +
				` data-code-lang="${Utils.escapeHtml(res.lang || '')}"` +
				` data-code-len="${String(len)}" data-code-head="${headEsc}" data-code-tail="${tailEsc}" data-code-nl="${String(nl)}"` +
				` data-fp="${Utils.escapeHtml(fpStable)}"` +
				` data-locale-collapse="${Utils.escapeHtml(cfg.LOCALE.COLLAPSE)}" data-locale-expand="${Utils.escapeHtml(cfg.LOCALE.EXPAND)}"` +
				` data-locale-copy="${Utils.escapeHtml(cfg.LOCALE.COPY)}" data-locale-copied="${Utils.escapeHtml(cfg.LOCALE.COPIED)}" data-style="${Utils.escapeHtml(cfg.CODE_STYLE)}">` +
				`<p class="code-header-wrapper"><span><span class="code-header-lang">${Utils.escapeHtml(headerLabel)}   </span>${actions}</span></p>` +
				`<pre><code class="language-${Utils.escapeHtml(langClass)} hljs${toolCode ? ' no-highlight' : ''}"${highlightAttrs} data-code-id="${String(codeId)}"></code></pre>` +
				`</div>`
			);
		}

		// Fallback
		rendererRef && rendererRef.debug && rendererRef.debug(`fence.${this.mode}.fallback`, {
			idxLocal,
			lang: langClass,
			len
		});
		return (
			`<div class="code-wrapper highlight" data-index="${idxLocal}"` +
			` data-code-lang="${Utils.escapeHtml(res.lang || '')}"` +
			` data-code-len="${String(len)}" data-code-head="${headEsc}" data-code-tail="${tailEsc}" data-code-nl="${String(nl)}"` +
			` data-fp="${Utils.escapeHtml(fpStable)}"` +
			` data-locale-collapse="${Utils.escapeHtml(cfg.LOCALE.COLLAPSE)}" data-locale-expand="${Utils.escapeHtml(cfg.LOCALE.EXPAND)}"` +
			` data-locale-copy="${Utils.escapeHtml(cfg.LOCALE.COPY)}" data-locale-copied="${Utils.escapeHtml(cfg.LOCALE.COPIED)}" data-style="${Utils.escapeHtml(cfg.CODE_STYLE)}">` +
			`<p class="code-header-wrapper"><span><span class="code-header-lang">${Utils.escapeHtml(headerLabel)}   </span>${actions}</span></p>` +
			`<pre><code class="language-${Utils.escapeHtml(langClass)} hljs${toolCode ? ' no-highlight' : ''}"${highlightAttrs}>${Utils.escapeHtml(content)}</code></pre>` +
			`</div>`
		);
	}

}
