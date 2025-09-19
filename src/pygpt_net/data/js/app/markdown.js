// ==========================================================================
// Markdown runtime (markdown-it + code wrapper + math placeholders)
// ==========================================================================

class MarkdownRenderer {

	// Markdown renderer for text, code blocks and math placeholders.
	constructor(cfg, customMarkup, logger, asyncer, raf) {
		// Store configuration and dependencies
		this.cfg = cfg;
		this.customMarkup = customMarkup;
		this.MD = null;

		// Logger instance (fallback to default Logger)
		this.logger = logger || new Logger(cfg);

		// Cooperative async utilities available in renderer for heavy decode/render paths
		this.asyncer = asyncer || new AsyncRunner(cfg, raf);
		this.raf = raf || null;

		// Fast-path streaming renderer without linkify to reduce regex work on hot path.
		this.MD_STREAM = null;

		// Default hook callbacks used by outside runtime (can be overridden)
		this.hooks = {
			observeNewCode: () => {},
			observeMsgBoxes: () => {},
			scheduleMathRender: () => {},
			codeScrollInit: () => {}
		};

		// Registry for FULL and STREAM render (env -> id -> string)
		this._codeByEnv = new WeakMap();
		this._codeSeq = 0;

		// Internal flag: was init() already called?
		this._inited = false;
	}

	// Debug helper: write structured log lines for the stream engine.
	_d(tag, data) {
		try {
			const lg = this.logger || (this.cfg && this.cfg.logger) || (window.runtime && runtime.logger) || null;
			if (!lg || typeof lg.debug !== 'function') return;
			lg.debug_obj("MD", tag, data);
		} catch (_) {}
	}

	// --- Registry (placeholders) ---

	// Register code content for later resolution in the given env.
	_regCode(env, content) {
		// Use temporary env if none was provided
		if (!env) env = (this._tmpEnv || (this._tmpEnv = {}));
		// Get or create per-env map
		let m = this._codeByEnv.get(env);
		if (!m) {
			m = new Map();
			this._codeByEnv.set(env, m);
		}
		// Generate simple increasing id and store content
		const id = `c${++this._codeSeq}`;
		m.set(id, content);
		// DEBUG
		this._d('code.reg', {
			id,
			len: (content || '').length
		});
		return id;
	}

	// Resolve registered code content in the given root element for the given env.
	_resolveCodesIn(root, env) {
		const m = this._codeByEnv.get(env);
		if (!m || !root) return;
		let count = 0;
		root.querySelectorAll('code[data-code-id]').forEach(el => {
			const id = el.getAttribute('data-code-id');
			const s = m.get(id);
			if (s != null) {
				if (!el.firstChild) el.textContent = s; // minimal allocation
				el.removeAttribute('data-code-id');
				m.delete(id);
				count++;
			}
		});
		// DEBUG
		if (count) this._d('code.resolve', {
			count
		});
	}

	// Release all registered code content for the given env.
	_releaseEnvCodes(env) {
		this._codeByEnv.delete(env);
	}

	// Initialize markdown-it instances and plugins.
	init() {
		// Guard against double init
		if (this._inited) return;
		if (!window.markdownit) {
			this._d('init.skip', {
				reason: 'no-markdownit'
			});
			return;
		}
		this._inited = true;

		// Full renderer (used for non-hot paths, final results)
		this.MD = window.markdownit({
			html: false,
			linkify: true,
			breaks: true,
			highlight: () => ''
		});
		// Streaming renderer (no linkify) – hot path
		this.MD_STREAM = window.markdownit({
			html: false,
			linkify: false,
			breaks: true,
			highlight: () => ''
		});

		// Allow local file-like schemes in links/images (markdown-it blocks file:// by default).
		const installLinkValidator = (md) => {
			// Patch validateLink to allow additional safe schemes in this app
			const orig = (md && typeof md.validateLink === 'function') ? md.validateLink.bind(md) : null;
			md.validateLink = (url) => {
				try {
					const s = String(url || '').trim().toLowerCase();
					if (s.startsWith('file:')) return true; // local files
					if (s.startsWith('qrc:')) return true; // Qt resources
					if (s.startsWith('bridge:')) return true; // app bridge scheme
					if (s.startsWith('blob:')) return true; // blobs
					if (s.startsWith('data:image/')) return true; // inline images
				} catch (_) {}
				return orig ? orig(url) : true;
			};
		};

		// Install relaxed link validators on both engines
		installLinkValidator(this.MD);
		installLinkValidator(this.MD_STREAM);

		// SAFETY: disable CommonMark "indented code blocks" unless explicitly enabled.
		if (!this.cfg.MD || this.cfg.MD.ALLOW_INDENTED_CODE !== true) {
			try {
				this.MD.block.ruler.disable('code');
			} catch (_) {}
			try {
				this.MD_STREAM.block.ruler.disable('code');
			} catch (_) {}
		}

		const escapeHtml = Utils.escapeHtml;

		// ------------------ Math (placeholders) ------------------
		// Plugin that recognizes $...$ and $$...$$ and emits safe placeholders
		const mathDollarPlaceholderPlugin = (md) => {
			function notEscaped(src, pos) {
				let back = 0;
				while (pos - back - 1 >= 0 && src.charCodeAt(pos - back - 1) === 0x5C) back++;
				return (back % 2) === 0;
			}

			function math_block_dollar(state, startLine, endLine, silent) {
				const pos = state.bMarks[startLine] + state.tShift[startLine];
				const max = state.eMarks[startLine];
				if (pos + 1 >= max) return false;
				if (state.src.charCodeAt(pos) !== 0x24 || state.src.charCodeAt(pos + 1) !== 0x24) return false;
				let nextLine = startLine + 1,
					found = false;
				for (; nextLine < endLine; nextLine++) {
					let p = state.bMarks[nextLine] + state.tShift[nextLine];
					const pe = state.eMarks[nextLine];
					if (p + 1 < pe && state.src.charCodeAt(p) === 0x24 && state.src.charCodeAt(p + 1) === 0x24) {
						found = true;
						break;
					}
				}
				if (!found) return false;
				if (silent) return true;
				const contentStart = state.bMarks[startLine] + state.tShift[startLine] + 2;
				const contentEndLine = nextLine - 1;
				let content = '';
				if (contentEndLine >= startLine + 1) {
					const startIdx = state.bMarks[startLine + 1];
					const endIdx = state.eMarks[contentEndLine];
					content = state.src.slice(startIdx, endIdx);
				}
				const token = state.push('math_block_dollar', '', 0);
				token.block = true;
				token.content = content;
				state.line = nextLine + 1;
				return true;
			}

			function math_inline_dollar(state, silent) {
				const pos = state.pos,
					src = state.src,
					max = state.posMax;
				if (pos >= max) return false;
				if (src.charCodeAt(pos) !== 0x24) return false;
				if (pos + 1 < max && src.charCodeAt(pos + 1) === 0x24) return false;
				const after = pos + 1 < max ? src.charCodeAt(pos + 1) : 0;
				if (after === 0x20 || after === 0x0A || after === 0x0D) return false;
				let i = pos + 1;
				while (i < max) {
					const ch = src.charCodeAt(i);
					if (ch === 0x24 && notEscaped(src, i)) {
						const before = i - 1 >= 0 ? src.charCodeAt(i - 1) : 0;
						if (before === 0x20 || before === 0x0A || before === 0x0D) {
							i++;
							continue;
						}
						break;
					}
					i++;
				}
				if (i >= max || src.charCodeAt(i) !== 0x24) return false;
				if (!silent) {
					const token = state.push('math_inline_dollar', '', 0);
					token.block = false;
					token.content = src.slice(pos + 1, i);
				}
				state.pos = i + 1;
				return true;
			}
			md.block.ruler.before('fence', 'math_block_dollar', math_block_dollar, {
				alt: ['paragraph', 'reference', 'blockquote', 'list']
			});
			md.inline.ruler.before('escape', 'math_inline_dollar', math_inline_dollar);
			md.renderer.rules.math_inline_dollar = (tokens, idx) => {
				const tex = tokens[idx].content || '';
				return `<span class="math-pending" data-display="0"><span class="math-fallback">$${escapeHtml(tex)}$</span><script type="math/tex">${escapeHtml(tex)}</script></span>`;
			};
			md.renderer.rules.math_block_dollar = (tokens, idx) => {
				const tex = tokens[idx].content || '';
				return `<div class="math-pending" data-display="1"><div class="math-fallback">$$${escapeHtml(tex)}$$</div><script type="math/tex; mode=display">${escapeHtml(tex)}</script></div>`;
			};
		};

		// \( ... \) and \[ ... \] math delimiters (TeX style)
		const mathBracketsPlaceholderPlugin = (md) => {
			function math_brackets(state, silent) {
				const src = state.src,
					pos = state.pos,
					max = state.posMax;
				if (pos + 1 >= max || src.charCodeAt(pos) !== 0x5C) return false;
				const next = src.charCodeAt(pos + 1);
				if (next !== 0x28 && next !== 0x5B) return false;
				const isInline = (next === 0x28);
				const close = isInline ? '\\)' : '\\]';
				const start = pos + 2;
				const end = src.indexOf(close, start);
				if (end < 0) return false;
				const content = src.slice(start, end);
				if (!silent) {
					const t = state.push(isInline ? 'math_inline_bracket' : 'math_block_bracket', '', 0);
					t.content = content;
					t.block = !isInline;
				}
				state.pos = end + 2;
				return true;
			}
			md.inline.ruler.before('escape', 'math_brackets', math_brackets);
			md.renderer.rules.math_inline_bracket = (tokens, idx) => {
				const tex = tokens[idx].content || '';
				return `<span class="math-pending" data-display="0"><span class="math-fallback">\\(${escapeHtml(tex)}\\)</span><script type="math/tex">${escapeHtml(tex)}</script></span>`;
			};
			md.renderer.rules.math_block_bracket = (tokens, idx) => {
				const tex = tokens[idx].content || '';
				return `<div class="math-pending" data-display="1"><div class="math-fallback">\\${'['}${escapeHtml(tex)}\\${']'}</div><script type="math/tex; mode=display">${escapeHtml(tex)}</script></div>`;
			};
		};

		// Enable math placeholders for both renderers
		this.MD.use(mathDollarPlaceholderPlugin);
		this.MD.use(mathBracketsPlaceholderPlugin);
		this.MD_STREAM.use(mathDollarPlaceholderPlugin);
		this.MD_STREAM.use(mathBracketsPlaceholderPlugin);

		const cfg = this.cfg;
		const logger = this.logger;

		// ------------------ STREAMING wrapper plugin (hot path; inline) ------------------
		(function codeWrapperPlugin(md, logger, renderer) {
			let CODE_IDX = 1;
			const ALIAS = {
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

			function normLang(s) {
				if (!s) return '';
				const v = String(s).trim().toLowerCase();
				return ALIAS[v] || v;
			}

			function isSupportedByHLJS(lang) {
				try {
					return !!(window.hljs && hljs.getLanguage && hljs.getLanguage(lang));
				} catch (_) {
					return false;
				}
			}

			function classForHighlight(lang) {
				if (!lang) return 'plaintext';
				return isSupportedByHLJS(lang) ? lang : 'plaintext';
			}

			function stripBOM(s) {
				return (s && s.charCodeAt(0) === 0xFEFF) ? s.slice(1) : s;
			}

			function normForFP(s) {
				if (!s) return '';
				let t = String(s);
				if (t.charCodeAt(0) === 0xFEFF) t = t.slice(1);
				t = t.replace(/\r\n?/g, '\n');
				if (t.endsWith('\n')) t = t.slice(0, -1);
				return t;
			}

			function hash32FNV(str) {
				let h = 0x811c9dc5 >>> 0;
				for (let i = 0; i < str.length; i++) {
					h ^= str.charCodeAt(i);
					h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
				}
				return ('00000000' + h.toString(16)).slice(-8);
			}

			function makeStableFP(langToken, rawContent) {
				const norm = normForFP(rawContent || '');
				return `${langToken || 'plaintext'}|${norm.length}|${hash32FNV(norm)}`;
			}

			function detectFromFirstLine(raw, rid) {
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
				let first = stripBOM(lines[i]).trim();
				first = first.replace(/^\s*lang(?:uage)?\s*[:=]\s*/i, '').trim();
				let token = first.split(/\s+/)[0].replace(/:$/, '');
				if (!/^[A-Za-z][\w#+\-\.]{0,30}$/.test(token)) return {
					lang: '',
					content: raw,
					isOutput: false
				};
				let cand = normLang(token);
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

			function resolveLanguageAndContent(info, raw, rid) {
				const infoLangRaw = (info || '').trim().split(/\s+/)[0] || '';
				let cand = normLang(infoLangRaw);

				// Treat too-short/unsupported tokens as unreliable; ignore and fall back.
				const shortOrUnsupported = !cand || cand.length < 3 || !isSupportedByHLJS(cand);

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
				const det = detectFromFirstLine(raw, rid);
				if (det && (det.lang || det.isOutput)) return det;

				// Last resort
				return {
					lang: '',
					headerLabel: 'code',
					content: raw,
					isOutput: false
				};
			}

			md.renderer.rules.fence = (tokens, idx, options, env) => renderFence(tokens[idx], env);
			md.renderer.rules.code_block = (tokens, idx, options, env) => renderFence({
				info: '',
				content: tokens[idx].content || ''
			}, env);

			function renderFence(token, env) {
				const rendererRef = renderer || (window.runtime && window.runtime.renderer) || null;
				const raw = token.content || '';
				const rid = String(CODE_IDX + '');

				const res = resolveLanguageAndContent(token.info || '', raw, rid);
				const isOutput = !!res.isOutput;
				const rawToken = (res.lang || '').trim();
				const langClass = isOutput ? 'python' : classForHighlight(rawToken);

				let headerLabel = isOutput ? 'output' : (res.headerLabel || (rawToken || 'code'));
				if (!isOutput) {
					if (rawToken && !isSupportedByHLJS(rawToken) && rawToken.length < 3) headerLabel = 'code';
				}

				const content = res.content || '';
				const len = content.length;
				const head = content.slice(0, 64);
				const tail = content.slice(-64);
				const headEsc = Utils.escapeHtml(head);
				const tailEsc = Utils.escapeHtml(tail);
				const nl = Utils.countNewlines(content);
				const fpStable = makeStableFP(langClass, content);

				const idxLocal = CODE_IDX++;

				let actions = '';
				if (langClass === 'html') {
					actions += `<a href="empty:${idxLocal}" class="code-header-action code-header-preview"><img src="${cfg.ICONS.CODE_PREVIEW}" class="action-img" data-id="${idxLocal}"><span>${Utils.escapeHtml(cfg.LOCALE.PREVIEW)}</span></a>`;
				} else if (langClass === 'python' && headerLabel !== 'output') {
					actions += `<a href="empty:${idxLocal}" class="code-header-action code-header-run"><img src="${cfg.ICONS.CODE_RUN}" class="action-img" data-id="${idxLocal}"><span>${Utils.escapeHtml(cfg.LOCALE.RUN)}</span></a>`;
				}
				actions += `<a href="empty:${idxLocal}" class="code-header-action code-header-collapse" title="${Utils.escapeHtml(cfg.LOCALE.COLLAPSE)}"><img src="${cfg.ICONS.CODE_MENU}" class="action-img" data-id="${idxLocal}"></a>`;
                actions += `<a href="empty:${idxLocal}" class="code-header-action code-header-copy" title="${Utils.escapeHtml(cfg.LOCALE.COPY)}"><img src="${cfg.ICONS.CODE_COPY}" class="action-img" data-id="${idxLocal}"></a>`;

				const canUseRegistry = !!(rendererRef && typeof rendererRef._regCode === 'function' && env);
				if (canUseRegistry) {
					const codeId = rendererRef._regCode(env, content);
					// DEBUG
					rendererRef._d && rendererRef._d('fence.stream', {
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
						`<pre><code class="language-${Utils.escapeHtml(langClass)} hljs" data-code-id="${String(codeId)}"></code></pre>` +
						`</div>`
					);
				}

				// Fallback
				rendererRef && rendererRef._d && rendererRef._d('fence.stream.fallback', {
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
					`<pre><code class="language-${Utils.escapeHtml(langClass)} hljs">${Utils.escapeHtml(content)}</code></pre>` +
					`</div>`
				);
			}
		})(this.MD_STREAM, this.logger, this);

		// ---------------- FULL renderer wrapper plugin ----------------
		(function codeWrapperPlugin(md, logger, renderer) {
			let CODE_IDX = 1;
			const ALIAS = {
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

			function normLang(s) {
				if (!s) return '';
				const v = String(s).trim().toLowerCase();
				return ALIAS[v] || v;
			}

			function isSupportedByHLJS(lang) {
				try {
					return !!(window.hljs && hljs.getLanguage && hljs.getLanguage(lang));
				} catch (_) {
					return false;
				}
			}

			function classForHighlight(lang) {
				if (!lang) return 'plaintext';
				return isSupportedByHLJS(lang) ? lang : 'plaintext';
			}

			function stripBOM(s) {
				return (s && s.charCodeAt(0) === 0xFEFF) ? s.slice(1) : s;
			}

			function normForFP(s) {
				if (!s) return '';
				let t = String(s);
				if (t.charCodeAt(0) === 0xFEFF) t = t.slice(1);
				t = t.replace(/\r\n?/g, '\n');
				if (t.endsWith('\n')) t = t.slice(0, -1);
				return t;
			}

			function hash32FNV(str) {
				let h = 0x811c9dc5 >>> 0;
				for (let i = 0; i < str.length; i++) {
					h ^= str.charCodeAt(i);
					h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
				}
				return ('00000000' + h.toString(16)).slice(-8);
			}

			function makeStableFP(langToken, rawContent) {
				const norm = normForFP(rawContent || '');
				return `${langToken || 'plaintext'}|${norm.length}|${hash32FNV(norm)}`;
			}

			function detectFromFirstLine(raw, rid) {
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
				let first = stripBOM(lines[i]).trim();
				first = first.replace(/^\s*lang(?:uage)?\s*[:=]\s*/i, '').trim();
				let token = first.split(/\s+/)[0].replace(/:$/, '');
				if (!/^[A-Za-z][\w#+\-\.]{0,30}$/.test(token)) return {
					lang: '',
					content: raw,
					isOutput: false
				};
				let cand = normLang(token);
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

			function resolveLanguageAndContent(info, raw, rid) {
				const infoLangRaw = (info || '').trim().split(/\s+/)[0] || '';
				let cand = normLang(infoLangRaw);

				// Treat too-short/unsupported tokens as unreliable; ignore and fall back.
				const shortOrUnsupported = !cand || cand.length < 3 || !isSupportedByHLJS(cand);

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
				const det = detectFromFirstLine(raw, rid);
				if (det && (det.lang || det.isOutput)) return det;

				// Last resort
				return {
					lang: '',
					headerLabel: 'code',
					content: raw,
					isOutput: false
				};
			}

			md.renderer.rules.fence = (tokens, idx, options, env, slf) => renderFence(tokens[idx], env);
			md.renderer.rules.code_block = (tokens, idx, options, env, slf) => renderFence({
				info: '',
				content: tokens[idx].content || ''
			}, env);

			function renderFence(token, env) {
				const rendererRef = renderer || (window.runtime && window.runtime.renderer) || null;
				const raw = token.content || '';
				const rid = String(CODE_IDX + '');
				const res = resolveLanguageAndContent(token.info || '', raw, rid);
				const isOutput = !!res.isOutput;
				const rawToken = (res.lang || '').trim();
				const langClass = isOutput ? 'python' : classForHighlight(rawToken);
				let headerLabel = isOutput ? 'output' : (res.headerLabel || (rawToken || 'code'));
				if (!isOutput) {
					if (rawToken && !isSupportedByHLJS(rawToken) && rawToken.length < 3) headerLabel = 'code';
				}

				const content = res.content || '';
				const len = content.length;
				const head = content.slice(0, 64);
				const tail = content.slice(-64);
				const headEsc = Utils.escapeHtml(head);
				const tailEsc = Utils.escapeHtml(tail);
				const nl = Utils.countNewlines(content);
				const fpStable = makeStableFP(langClass, content);

				const idxLocal = CODE_IDX++;

				let actions = '';
				if (langClass === 'html') {
					actions += `<a href="empty:${idxLocal}" class="code-header-action code-header-preview"><img src="${cfg.ICONS.CODE_PREVIEW}" class="action-img" data-id="${idxLocal}"><span>${Utils.escapeHtml(cfg.LOCALE.PREVIEW)}</span></a>`;
				} else if (langClass === 'python' && headerLabel !== 'output') {
					actions += `<a href="empty:${idxLocal}" class="code-header-action code-header-run"><img src="${cfg.ICONS.CODE_RUN}" class="action-img" data-id="${idxLocal}"><span>${Utils.escapeHtml(cfg.LOCALE.RUN)}</span></a>`;
				}
				// icon-only (no label) + title
                actions += `<a href="empty:${idxLocal}" class="code-header-action code-header-collapse" title="${Utils.escapeHtml(cfg.LOCALE.COLLAPSE)}"><img src="${cfg.ICONS.CODE_MENU}" class="action-img" data-id="${idxLocal}"></a>`;
                actions += `<a href="empty:${idxLocal}" class="code-header-action code-header-copy" title="${Utils.escapeHtml(cfg.LOCALE.COPY)}"><img src="${cfg.ICONS.CODE_COPY}" class="action-img" data-id="${idxLocal}"></a>`;

				const canUseRegistry = !!(rendererRef && typeof rendererRef._regCode === 'function' && env);
				if (canUseRegistry) {
					const codeId = rendererRef._regCode(env, content);
					rendererRef._d && rendererRef._d('fence.full', {
						idxLocal,
						lang: langClass,
						headerLabel,
						len
					});
					return (
						`<div class="code-wrapper highlight" data-index="${idxLocal}"` +
						` data-code-lang="${Utils.escapeHtml(res.lang || '')}"` +
						` data-code-len="${String(len)}" data-code-head="${headEsc}" data-code-tail="${tailEsc}" data-code-nl="${String(nl)}" data-fp="${Utils.escapeHtml(fpStable)}"` +
						` data-locale-collapse="${Utils.escapeHtml(cfg.LOCALE.COLLAPSE)}" data-locale-expand="${Utils.escapeHtml(cfg.LOCALE.EXPAND)}"` +
						` data-locale-copy="${Utils.escapeHtml(cfg.LOCALE.COPY)}" data-locale-copied="${Utils.escapeHtml(cfg.LOCALE.COPIED)}" data-style="${Utils.escapeHtml(cfg.CODE_STYLE)}">` +
						`<p class="code-header-wrapper"><span><span class="code-header-lang">${Utils.escapeHtml(headerLabel)}   </span>${actions}</span></p>` +
						`<pre><code class="language-${Utils.escapeHtml(langClass)} hljs" data-code-id="${String(codeId)}"></code></pre>` +
						`</div>`
					);
				}

				rendererRef && rendererRef._d && rendererRef._d('fence.full.fallback', {
					idxLocal,
					lang: langClass,
					len
				});
				const inner = Utils.escapeHtml(content);
				return (
					`<div class="code-wrapper highlight" data-index="${idxLocal}"` +
					` data-code-lang="${Utils.escapeHtml(res.lang || '')}"` +
					` data-code-len="${String(len)}" data-code-head="${headEsc}" data-code-tail="${tailEsc}" data-code-nl="${String(nl)}" data-fp="${Utils.escapeHtml(fpStable)}"` +
					` data-locale-collapse="${Utils.escapeHtml(cfg.LOCALE.COLLAPSE)}" data-locale-expand="${Utils.escapeHtml(cfg.LOCALE.EXPAND)}"` +
					` data-locale-copy="${Utils.escapeHtml(cfg.LOCALE.COPY)}" data-locale-copied="${Utils.escapeHtml(cfg.LOCALE.COPIED)}" data-style="${Utils.escapeHtml(cfg.CODE_STYLE)}">` +
					`<p class="code-header-wrapper"><span><span class="code-header-lang">${Utils.escapeHtml(headerLabel)}   </span>${actions}</span></p>` +
					`<pre><code class="language-${Utils.escapeHtml(langClass)} hljs">${inner}</code></pre>` +
					`</div>`
				);
			}
		})(this.MD, this.logger, this);

		this._d('init.done', {});
	}

	// Replace "sandbox:" links with file:// in markdown source (host policy).
	preprocessMD(s) {
		const out = (s || '').replace(/\]\(sandbox:/g, '](file://');
		if (out !== s) this._d('md.preprocess', {
			replaced: true
		});
		return out;
	}

	// Decode base64 UTF-8 to string (shared TextDecoder).
	b64ToUtf8(b64) {
		const bin = atob(b64);
		const bytes = new Uint8Array(bin.length);
		for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
		return Utils.utf8Decode(bytes);
	}

	// Apply custom markup for bot messages only (method name kept for API).
	applyCustomMarkupForBots(root) {
		const MD = this.MD;
		try {
			const scope = root || document;
			const targets = [];

			if (scope && scope.nodeType === 1 && scope.classList && scope.classList.contains('msg-box') &&
				scope.classList.contains('msg-bot')) {
				targets.push(scope);
			}
			if (scope && typeof scope.querySelectorAll === 'function') {
				const list = scope.querySelectorAll('.msg-box.msg-bot');
				for (let i = 0; i < list.length; i++) targets.push(list[i]);
			}
			if (scope && scope.nodeType === 1 && typeof scope.closest === 'function') {
				const closestMsg = scope.closest('.msg-box.msg-bot');
				if (closestMsg) targets.push(closestMsg);
			}

			const seen = new Set();
			for (const el of targets) {
				if (!el || !el.isConnected || seen.has(el)) continue;
				seen.add(el);
				this.customMarkup.apply(el, MD);
			}
			this._d('cm.applyBots', {
				count: seen.size
			});
		} catch (_) {}
	}

	// Helper: choose renderer (hot vs full) for snapshot use.
	_md(streamingHint) {
		return streamingHint ? (this.MD_STREAM || this.MD) : (this.MD || this.MD_STREAM);
	}

	// Async, batched processing of [data-md64] / [md-block-markdown] to keep UI responsive on heavy loads.
	async renderPendingMarkdown(root) {
		const MD = this.MD;
		if (!MD) return;

		const scope = root || document;
		const nodes = Array.from(scope.querySelectorAll('[data-md64], [md-block-markdown]'));
		if (nodes.length === 0) {
			try {
				const hasBots = !!(scope && scope.querySelector && scope.querySelector('.msg-box.msg-bot'));
				const hasWrappers = !!(scope && scope.querySelector && scope.querySelector('.code-wrapper'));
				const hasCodes = !!(scope && scope.querySelector && scope.querySelector('.msg-box.msg-bot pre code'));
				const hasUnhighlighted = !!(scope && scope.querySelector && scope.querySelector('.msg-box.msg-bot pre code:not([data-highlighted="yes"])'));
				const hasMath = !!(scope && scope.querySelector && scope.querySelector('script[type^="math/tex"]'));

				if (hasBots) this.applyCustomMarkupForBots(scope);
				if (hasWrappers) this.restoreCollapsedCode(scope);
				this.hooks.codeScrollInit(scope);

				if (hasCodes) {
					this.hooks.observeMsgBoxes(scope);
					this.hooks.observeNewCode(scope, {
						deferLastIfStreaming: true,
						minLinesForLast: this.cfg.PROFILE_CODE.minLinesForHL,
						minCharsForLast: this.cfg.PROFILE_CODE.minCharsForHL
					});
					if (hasUnhighlighted && typeof runtime !== 'undefined' && runtime.highlighter) {
						runtime.highlighter.scanVisibleCodesInRoot(scope, runtime.stream.activeCode || null);
					}
				}

				if (hasMath) this.hooks.scheduleMathRender(scope);
			} catch (_) {}
			return;
		}

		this._d('md.pending.start', {
			nodes: nodes.length
		});

		const touchedBoxes = new Set();
		const perSlice = (this.cfg.ASYNC && this.cfg.ASYNC.MD_NODES_PER_SLICE) || 12;
		let sliceCount = 0;
		let startedAt = Utils.now();

		for (let j = 0; j < nodes.length; j++) {
			const el = nodes[j];
			if (!el || !el.isConnected) continue;

			let md = '';
			const isNative = el.hasAttribute('md-block-markdown');
			const msgBox = (el.closest && el.closest('.msg-box.msg-bot, .msg-box.msg-user')) || null;
			const isUserMsg = !!(msgBox && msgBox.classList.contains('msg-user'));
			const isBotMsg = !!(msgBox && msgBox.classList.contains('msg-bot'));

			if (isNative) {
				try {
					md = isUserMsg ? (el.textContent || '') : this.preprocessMD(el.textContent || '');
				} catch (_) {
					md = '';
				}
				try {
					el.removeAttribute('md-block-markdown');
				} catch (_) {}
			} else {
				const b64 = el.getAttribute('data-md64');
				if (!b64) continue;
				try {
					md = this.b64ToUtf8(b64);
				} catch (_) {
					md = '';
				}
				el.removeAttribute('data-md64');
				if (!isUserMsg) {
					try {
						md = this.preprocessMD(md);
					} catch (_) {}
				}
			}

			if (isUserMsg) {
				const span = document.createElement('span');
				span.textContent = md;
				el.replaceWith(span);
			} else if (isBotMsg) {
				let html = '';
				const env = {
					__box: msgBox
				};
				try {
					let src = md;
					if (this.customMarkup && typeof this.customMarkup.transformSource === 'function') {
						src = this.customMarkup.transformSource(src, {
							streaming: false
						});
					}
					html = this.MD.render(src, env);
				} catch (_) {
					html = Utils.escapeHtml(md);
				}
				const tpl = document.createElement('template');
				tpl.innerHTML = html;
				const frag = tpl.content;
				try {
					this._resolveCodesIn(frag, env);
					this._releaseEnvCodes(env);
				} catch (_) {}
				el.replaceWith(frag);
				touchedBoxes.add(msgBox);
			} else {
				const span = document.createElement('span');
				span.textContent = md;
				el.replaceWith(span);
			}

			sliceCount++;
			if (sliceCount >= perSlice || this.asyncer.shouldYield(startedAt)) {
				await this.asyncer.yield();
				startedAt = Utils.now();
				sliceCount = 0;
			}
		}

		try {
			touchedBoxes.forEach(box => {
				try {
					this.customMarkup.apply(box, this.MD);
				} catch (_) {}
			});
		} catch (_) {}

		this.restoreCollapsedCode(scope);
		this.hooks.observeNewCode(scope, {
			deferLastIfStreaming: true,
			minLinesForLast: this.cfg.PROFILE_CODE.minLinesForHL,
			minCharsForLast: this.cfg.PROFILE_CODE.minCharsForHL
		});
		this.hooks.observeMsgBoxes(scope);
		this.hooks.scheduleMathRender(scope);
		this.hooks.codeScrollInit(scope);

		if (typeof runtime !== 'undefined' && runtime.highlighter) {
			runtime.highlighter.scanVisibleCodesInRoot(scope, runtime.stream.activeCode || null);
		}

		this._d('md.pending.end', {
			boxes: touchedBoxes.size
		});
	}

	// Render streaming snapshot (string).
	renderStreamingSnapshot(src) {
		const md = this._md(true);
		if (!md) return '';
		try {
			let s = String(src || '');
			if (this.customMarkup && typeof this.customMarkup.transformSource === 'function') {
				s = this.customMarkup.transformSource(s, {
					streaming: true
				});
			}
			return md.render(s, {}); // env present in fragment variant
		} catch (_) {
			return Utils.escapeHtml(src);
		}
	}

	// Render streaming snapshot as DocumentFragment (GC-friendly for callers).
	renderStreamingSnapshotFragment(src) {
		const md = this._md(true);
		if (!md) {
			const tpl0 = document.createElement('template');
			tpl0.innerHTML = '';
			return tpl0.content;
		}
		let html = '';
		const env = {};
		try {
			let s = String(src || '');
			if (this.customMarkup && typeof this.customMarkup.transformSource === 'function') {
				s = this.customMarkup.transformSource(s, {
					streaming: true
				});
			}
			html = md.render(s, env);
		} catch (_) {
			html = Utils.escapeHtml(src || '');
		}
		const tpl = document.createElement('template');
		tpl.innerHTML = html;
		const frag = tpl.content;

		try {
			this._resolveCodesIn(frag, env);
			this._releaseEnvCodes(env);
		} catch (_) {}
		this._d('md.render.stream.frag', {
			srcLen: (src || '').length,
			htmlLen: html.length
		});
		return frag;
	}

	// fast inline-only renderer (used by plain streaming incremental MD) ===
	renderInlineStreaming(src) {
		const md = this._md(true);
		if (!md || typeof md.renderInline !== 'function') return Utils.escapeHtml(src || '');
		try {
			const s = String(src || '');
			return md.renderInline(s);
		} catch (_) {
			return Utils.escapeHtml(src || '');
		}
	}

	// Render final snapshot (string).
	renderFinalSnapshot(src) {
		const md = this._md(false);
		if (!md) return '';
		try {
			let s = String(src || '');
			if (this.customMarkup && typeof this.customMarkup.transformSource === 'function') {
				s = this.customMarkup.transformSource(s, {
					streaming: false
				});
			}
			return md.render(s);
		} catch (_) {
			return Utils.escapeHtml(src);
		}
	}

	// Render final snapshot as DocumentFragment (GC-friendly for callers).
	renderFinalSnapshotFragment(src) {
		const md = this._md(false);
		if (!md) {
			const tpl0 = document.createElement('template');
			tpl0.innerHTML = '';
			return tpl0.content;
		}
		let html = '';
		const env = {};
		try {
			let s = String(src || '');
			if (this.customMarkup && typeof this.customMarkup.transformSource === 'function') {
				s = this.customMarkup.transformSource(s, {
					streaming: false
				});
			}
			html = md.render(s, env);
		} catch (_) {
			html = Utils.escapeHtml(src);
		}
		const tpl = document.createElement('template');
		tpl.innerHTML = html;
		const frag = tpl.content;

		try {
			this._resolveCodesIn(frag, env);
			this._releaseEnvCodes(env);
		} catch (_) {}
		this._d('md.render.final.frag', {
			srcLen: (src || '').length,
			htmlLen: html.length
		});
		return frag;
	}

	// Restore collapse/expand state of code blocks after DOM updates.
    restoreCollapsedCode(root) {
        const scope = root || document;
        const wrappers = scope.querySelectorAll('.code-wrapper');
        wrappers.forEach((wrapper) => {
            const index = wrapper.getAttribute('data-index');
            const localeCollapse = wrapper.getAttribute('data-locale-collapse');
            const localeExpand = wrapper.getAttribute('data-locale-expand');
            const source = wrapper.querySelector('code');
            const isCollapsed = (window.__collapsed_idx || []).includes(index);
            if (!source) return;
            const btn = wrapper.querySelector('.code-header-collapse');
            if (isCollapsed) {
                source.style.display = 'none';
                if (btn) {
                    const span = btn.querySelector('span');
                    if (span) span.textContent = localeExpand;
                    btn.setAttribute('title', localeExpand || 'Expand');
                }
            } else {
                source.style.display = 'block';
                if (btn) {
                    const span = btn.querySelector('span');
                    if (span) span.textContent = localeCollapse;
                    btn.setAttribute('title', localeCollapse || 'Collapse');
                }
            }
        });
    }
}