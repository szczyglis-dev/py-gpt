// ==========================================================================
// Markdown runtime (markdown-it + code wrapper + math placeholders)
// ==========================================================================

class MarkdownRenderer {

	// ========================================
	// Composition
	// ========================================

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
			codeScrollInit: () => {},
			scanVisibleCodes: () => {}
		};

		// Registry for FULL and STREAM render (env -> id -> string)
		this._codeByEnv = new WeakMap();
		this._codeSeq = 0;

		// Internal flag: was init() already called?
		this._inited = false;
		this.mathRules = new MarkdownMathRules();
		this.linkPolicy = new MarkdownLinkPolicy();
		this.streamCodeRules = new MarkdownCodeRules(this, "stream");
		this.fullCodeRules = new MarkdownCodeRules(this, "full");
	}

	// ========================================
	// Markdown setup and decoding
	// ========================================

	// Debug helper: write structured log lines for the stream engine.
	debug(tag, data) {
		try {
			const lg = this.logger || (this.cfg && this.cfg.logger) || (window.runtime && runtime.logger) || null;
			if (!lg || typeof lg.debug !== 'function') return;
			lg.debug_obj("MD", tag, data);
		} catch (_) {}
	}

	// Initialize markdown-it instances and plugins.
	init() {
		// Guard against double init
		if (this._inited) return;
		if (!window.markdownit) {
			this.debug('init.skip', {
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

		this.linkPolicy.install(this.MD);
		this.linkPolicy.install(this.MD_STREAM);

		// SAFETY: disable CommonMark "indented code blocks" unless explicitly enabled.
		if (!this.cfg.MD || this.cfg.MD.ALLOW_INDENTED_CODE !== true) {
			try {
				this.MD.block.ruler.disable('code');
			} catch (_) {}
			try {
				this.MD_STREAM.block.ruler.disable('code');
			} catch (_) {}
		}

		this.mathRules.install(this.MD);
		this.mathRules.install(this.MD_STREAM);

		// ------------------ STREAMING wrapper plugin (hot path; inline) ------------------
		this.streamCodeRules.install(this.MD_STREAM);
		this.fullCodeRules.install(this.MD);

		this.debug('init.done', {});
	}

	// Replace "sandbox:" links with file:// in markdown source (host policy).
	preprocessMD(s) {
		const out = (s || '').replace(/\]\(sandbox:/g, '](file://');
		if (out !== s) this.debug('md.preprocess', {
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

	// ========================================
	// Code registry and collapsed state
	// ========================================

	// --- Registry (placeholders) ---

	// Register code content for later resolution in the given env.
	registerCode(env, content) {
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
		this.debug('code.reg', {
			id,
			len: (content || '').length
		});
		return id;
	}

	// Restore collapse/expand state of code blocks after DOM updates. Collapse
	// state is represented by a wrapper class so the CSS slide transition can be
	// used without removing the code element from layout via display:none.
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
            try { source.style.removeProperty('display'); } catch (_) {}
            wrapper.classList.toggle('code-collapsed', isCollapsed);
            wrapper.setAttribute('aria-expanded', isCollapsed ? 'false' : 'true');
            const btn = wrapper.querySelector('.code-header-collapse');
            if (btn) {
                const span = btn.querySelector('span');
                if (span) span.textContent = isCollapsed ? localeExpand : localeCollapse;
                btn.setAttribute('title', (isCollapsed ? localeExpand : localeCollapse) || (isCollapsed ? 'Expand' : 'Collapse'));
                btn.setAttribute('aria-expanded', isCollapsed ? 'false' : 'true');
            }
        });
    }

	// ========================================
	// DOM postprocessing
	// ========================================

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
				this.customMarkup.html.apply(el, MD);
			}
			this.debug('cm.applyBots', {
				count: seen.size
			});
		} catch (_) {}
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
					if (hasUnhighlighted) this.hooks.scanVisibleCodes(scope);
				}

				if (hasMath) this.hooks.scheduleMathRender(scope);
			} catch (_) {}
			return;
		}

		this.debug('md.pending.start', {
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
					__box: msgBox,
					__codeHeaderLabel: el.getAttribute('data-code-header') || '',
					__toolCode: el.getAttribute('data-tool-code') === '1',
					__toolToggle: el.getAttribute('data-tool-toggle') === '1'
				};
				try {
					let src = md;
					if (this.customMarkup && typeof this.customMarkup.source.transformSource === 'function') {
						src = this.customMarkup.source.transformSource(src, {
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
					this.customMarkup.html.apply(box, this.MD);
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

		this.hooks.scanVisibleCodes(scope);

		this.debug('md.pending.end', {
			boxes: touchedBoxes.size
		});
	}

	// ========================================
	// Snapshot rendering
	// ========================================

	// Render streaming snapshot (string).
	renderStreamingSnapshot(src) {
		const md = this._md(true);
		if (!md) return '';
		try {
			let s = String(src || '');
			if (this.customMarkup && typeof this.customMarkup.source.transformSource === 'function') {
				s = this.customMarkup.source.transformSource(s, {
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
			if (this.customMarkup && typeof this.customMarkup.source.transformSource === 'function') {
				s = this.customMarkup.source.transformSource(s, {
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
		this.debug('md.render.stream.frag', {
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
			if (this.customMarkup && typeof this.customMarkup.source.transformSource === 'function') {
				s = this.customMarkup.source.transformSource(s, {
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
			if (this.customMarkup && typeof this.customMarkup.source.transformSource === 'function') {
				s = this.customMarkup.source.transformSource(s, {
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
		this.debug('md.render.final.frag', {
			srcLen: (src || '').length,
			htmlLen: html.length
		});
		return frag;
	}

	// ========================================
	// Code registry and collapsed state internals
	// ========================================

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
		if (count) this.debug('code.resolve', {
			count
		});
	}

	// Release all registered code content for the given env.
	_releaseEnvCodes(env) {
		this._codeByEnv.delete(env);
	}

	// ========================================
	// Markdown setup and decoding internals
	// ========================================

	// Helper: choose renderer (hot vs full) for snapshot use.
	_md(streamingHint) {
		return streamingHint ? (this.MD_STREAM || this.MD) : (this.MD || this.MD_STREAM);
	}

}
