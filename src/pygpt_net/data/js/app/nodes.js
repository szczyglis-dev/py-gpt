// ==========================================================================
// Nodes manager
// ==========================================================================

class NodesManager {

	// Nodes manager for handling message nodes.
	constructor(dom, renderer, highlighter, math) {
		this.dom = dom;
		this.renderer = renderer;
		this.highlighter = highlighter;
		this.math = math;
		// User message collapse manager
		this._userCollapse = new UserCollapseManager(this.renderer.cfg);
	}

	// Check if HTML contains only user messages without any markdown or code features.
	_isUserOnlyContent(html) {
		try {
			const tmp = document.createElement('div');
			tmp.innerHTML = html;
			const hasBot = !!tmp.querySelector('.msg-box.msg-bot');
			const hasUser = !!tmp.querySelector('.msg-box.msg-user');
			const hasMD64 = !!tmp.querySelector('[data-md64]');
			const hasMDNative = !!tmp.querySelector('[md-block-markdown]');
			const hasCode = !!tmp.querySelector('pre code');
			const hasMath = !!tmp.querySelector('script[type^="math/tex"]');
			return hasUser && !hasBot && !hasMD64 && !hasMDNative && !hasCode && !hasMath;
		} catch (_) {
			return false;
		}
	}

	// Convert user markdown placeholders into plain text nodes.
	_materializeUserMdAsPlainText(scopeEl) {
		try {
			const nodes = scopeEl.querySelectorAll('.msg-box.msg-user [data-md64], .msg-box.msg-user [md-block-markdown]');
			nodes.forEach(el => {
				let txt = '';
				if (el.hasAttribute('data-md64')) {
					const b64 = el.getAttribute('data-md64') || '';
					el.removeAttribute('data-md64');
					try {
						txt = this.renderer.b64ToUtf8(b64);
					} catch (_) {
						txt = '';
					}
				} else {
					// Native Markdown block in user message: keep as plain text (no markdown-it)
					try {
						txt = el.textContent || '';
					} catch (_) {
						txt = '';
					}
					try {
						el.removeAttribute('md-block-markdown');
					} catch (_) {}
				}
				const span = document.createElement('span');
				span.textContent = txt;
				el.replaceWith(span);
			});
		} catch (_) {}
	}

	// Ensure user copy icon exists inside each user message (.msg) under root.
	_ensureUserCopyIcons(root) {
		try {
			const scope = root || document;
			const cfg = (this.renderer && this.renderer.cfg) || {};
			const I = cfg.ICONS || {};
			const L = cfg.LOCALE || {};
			const copyIcon = I.CODE_COPY || '';
			const copyTitle = L.COPY || 'Copy';

			const list = scope.querySelectorAll('.msg-box.msg-user .msg');
			for (let i = 0; i < list.length; i++) {
				const msg = list[i];
				if (!msg || !msg.isConnected) continue;

				// If exists but sits inside .uc-content, move it up to .msg for stable absolute positioning.
				const existing = msg.querySelector('.msg-copy-btn');
				if (existing) {
					try {
						const p = existing.parentElement;
						if (p && p.classList && p.classList.contains('uc-content')) {
							msg.insertAdjacentElement('afterbegin', existing);
						}
					} catch (_) {}
					continue;
				}

				const a = document.createElement('a');
				a.href = 'empty:0';
				a.className = 'msg-copy-btn';
				a.setAttribute('role', 'button');
				a.setAttribute('title', copyTitle);
				a.setAttribute('aria-label', copyTitle);
				a.setAttribute('data-tip', copyTitle);

				try {
					const box = msg.closest('.msg-box.msg-user');
					if (box && box.id && box.id.startsWith('msg-user-')) {
						const id = box.id.slice('msg-user-'.length);
						a.setAttribute('data-id', id);
					}
				} catch (_) {}

				const img = document.createElement('img');
				img.className = 'copy-img';
				img.src = copyIcon;
				img.alt = copyTitle;

				a.appendChild(img);

				try {
					msg.insertAdjacentElement('afterbegin', a);
				} catch (_) {
					try {
						msg.appendChild(a);
					} catch (__) {}
				}
			}
		} catch (_) {}
	}

	// Append HTML/text into the message input container.
	// If plain text is provided, wrap it into a minimal msg-user box to keep layout consistent.
	appendToInput(content) {
		const el = this.dom.get('_append_input_');
		if (!el) return;

		let html = String(content || '');
		const trimmed = html.trim();

		// If already a full msg-user wrapper, append as-is; otherwise wrap the plain text.
		const isWrapped = (trimmed.startsWith('<div') && /class=["']msg-box msg-user["']/.test(trimmed));
		if (!isWrapped) {
			// Treat incoming payload as plain text (escape + convert newlines to <br>).
			const safe = (typeof Utils !== 'undefined' && Utils.escapeHtml) ?
				Utils.escapeHtml(html) :
				String(html).replace(/[&<>"']/g, m => ({
					'&': '&amp;',
					'<': '&lt;',
					'>': '&gt;',
					'"': '&quot;',
					"'": '&#039;'
				} [m]));
			const body = safe.replace(/\r?\n/g, '<br>');
			// Minimal, margin-less user message (no empty msg-extra to avoid extra spacing).
			html = `<div class="msg-box msg-user"><div class="msg"><p style="margin:0">${body}</p></div></div>`;
		}

		// Synchronous DOM update.
		el.insertAdjacentHTML('beforeend', html);

		// Apply collapse to any user messages in input area (now or later).
		try {
			this._userCollapse.apply(el);
		} catch (_) {}

		// Ensure copy icons exist (inject or reposition outside uc-content).
		try {
			this._ensureUserCopyIcons(el);
		} catch (_) {}
	}

	// Append nodes into messages list and perform post-processing (markdown, code, math).
	appendNode(content, scrollMgr) {
		// Keep scroll behavior consistent with existing logic
		scrollMgr.userInteracted = false;
		scrollMgr.prevScroll = 0;
		this.dom.clearStreamBefore();

		const el = this.dom.get('_nodes_');
		if (!el) return;
		el.classList.remove('empty_list');

		const userOnly = this._isUserOnlyContent(content);
		if (userOnly) {
			el.insertAdjacentHTML('beforeend', content);
			this._materializeUserMdAsPlainText(el);
			// Collapse before scrolling to ensure final height is used for scroll computations.
			try {
				this._userCollapse.apply(el);
			} catch (_) {}
			// Ensure copy icons exist for user messages.
			try {
				this._ensureUserCopyIcons(el);
			} catch (_) {}

			scrollMgr.scrollToBottom(false);
			scrollMgr.scheduleScrollFabUpdate();
			return;
		}

		el.insertAdjacentHTML('beforeend', content);

		try {
			// Defer post-processing (highlight/math/collapse) and perform scroll AFTER collapse.
			const maybePromise = this.renderer.renderPendingMarkdown(el);
			const post = () => {
				// Viewport highlight scheduling
				try {
					this.highlighter.scheduleScanVisibleCodes(null);
				} catch (_) {}

				// In finalize-only mode we must explicitly schedule KaTeX
				try {
					if (getMathMode() === 'finalize-only') this.math.schedule(el, 0, true);
				} catch (_) {}

				// Collapse user messages now that DOM is materialized (ensures correct height).
				try {
					this._userCollapse.apply(el);
				} catch (_) {}

				// Ensure copy icons exist for user messages.
				try {
					this._ensureUserCopyIcons(el);
				} catch (_) {}

				// Only now scroll to bottom and update FAB – uses post-collapse heights.
				scrollMgr.scrollToBottom(false);
				scrollMgr.scheduleScrollFabUpdate();
			};

			if (maybePromise && typeof maybePromise.then === 'function') {
				maybePromise.then(post);
			} else {
				post();
			}
		} catch (_) {
			// In case of error, do a conservative scroll to keep UX responsive.
			scrollMgr.scrollToBottom(false);
			scrollMgr.scheduleScrollFabUpdate();
		}
	}

	// Replace messages list content entirely and re-run post-processing.
	replaceNodes(content, scrollMgr) {
		// Same semantics as appendNode, but using a hard clone reset
		scrollMgr.userInteracted = false;
		scrollMgr.prevScroll = 0;
		this.dom.clearStreamBefore();

		const el = this.dom.hardReplaceByClone('_nodes_');
		if (!el) return;
		el.classList.remove('empty_list');

		const userOnly = this._isUserOnlyContent(content);
		if (userOnly) {
			el.insertAdjacentHTML('beforeend', content);
			this._materializeUserMdAsPlainText(el);
			// Collapse before scrolling to ensure final height is used for scroll computations.
			try {
				this._userCollapse.apply(el);
			} catch (_) {}
			// Ensure copy icons exist for user messages.
			try {
				this._ensureUserCopyIcons(el);
			} catch (_) {}

			scrollMgr.scrollToBottom(false, true);
			scrollMgr.scheduleScrollFabUpdate();
			return;
		}

		el.insertAdjacentHTML('beforeend', content);

		try {
			// Defer KaTeX schedule to post-Markdown to avoid races and collapse before scroll.
			const maybePromise = this.renderer.renderPendingMarkdown(el);
			const post = () => {
				try {
					this.highlighter.scheduleScanVisibleCodes(null);
				} catch (_) {}
				try {
					if (getMathMode() === 'finalize-only') this.math.schedule(el, 0, true);
				} catch (_) {}

				// Collapse after materialization to compute final heights correctly.
				try {
					this._userCollapse.apply(el);
				} catch (_) {}

				// Ensure copy icons exist for user messages.
				try {
					this._ensureUserCopyIcons(el);
				} catch (_) {}

				// Now scroll and update FAB using the collapsed layout.
				scrollMgr.scrollToBottom(false, true);
				scrollMgr.scheduleScrollFabUpdate();
			};

			if (maybePromise && typeof maybePromise.then === 'function') {
				maybePromise.then(post);
			} else {
				post();
			}
		} catch (_) {
			scrollMgr.scrollToBottom(false, true);
			scrollMgr.scheduleScrollFabUpdate();
		}
	}

	// Append "extra" content into a specific bot message and post-process locally.
	appendExtra(id, content, scrollMgr) {
		const el = document.getElementById('msg-bot-' + id);
		if (!el) return;
		const extra = el.querySelector('.msg-extra');
		if (!extra) return;

		extra.insertAdjacentHTML('beforeend', content);

		try {
			const maybePromise = this.renderer.renderPendingMarkdown(extra);

			const post = () => {
				const activeCode = (typeof runtime !== 'undefined' && runtime.stream) ? runtime.stream.activeCode : null;

				// Attach observers after Markdown produced the nodes
				try {
					this.highlighter.observeNewCode(extra, {
						deferLastIfStreaming: true,
						minLinesForLast: this.renderer.cfg.PROFILE_CODE.minLinesForHL,
						minCharsForLast: this.renderer.cfg.PROFILE_CODE.minCharsForHL
					}, activeCode);
					this.highlighter.observeMsgBoxes(extra, (box) => this._onBox(box));
				} catch (_) {}

				// KaTeX: honor stream mode; in finalize-only force immediate schedule
				try {
					const mm = getMathMode();
					if (mm === 'finalize-only') this.math.schedule(extra, 0, true);
					else this.math.schedule(extra);
				} catch (_) {}
			};

			if (maybePromise && typeof maybePromise.then === 'function') {
				maybePromise.then(post);
			} else {
				post();
			}
		} catch (_) {
			/* swallow */
		}

		scrollMgr.scheduleScroll(true);
	}

	// When a new message box appears, hook up code/highlight handlers.
	_onBox(box) {
		const activeCode = (typeof runtime !== 'undefined' && runtime.stream) ? runtime.stream.activeCode : null;
		this.highlighter.observeNewCode(box, {
			deferLastIfStreaming: true,
			minLinesForLast: this.renderer.cfg.PROFILE_CODE.minLinesForHL,
			minCharsForLast: this.renderer.cfg.PROFILE_CODE.minCharsForHL
		}, activeCode);
		this.renderer.hooks.codeScrollInit(box);
	}

	// Remove message by id and keep scroll consistent.
	removeNode(id, scrollMgr) {
		scrollMgr.prevScroll = 0;
		let el = document.getElementById('msg-user-' + id);
		if (el) el.remove();
		el = document.getElementById('msg-bot-' + id);
		if (el) el.remove();
		this.dom.resetEphemeral();
		try {
			this.renderer.renderPendingMarkdown();
		} catch (_) {}
		scrollMgr.scheduleScroll(true);
	}

	// Remove all messages from (and including) a given message id.
	removeNodesFromId(id, scrollMgr) {
		scrollMgr.prevScroll = 0;
		const container = this.dom.get('_nodes_');
		if (!container) return;
		const elements = container.querySelectorAll('.msg-box');
		let remove = false;
		elements.forEach((element) => {
			if (element.id && element.id.endsWith('-' + id)) remove = true;
			if (remove) element.remove();
		});
		this.dom.resetEphemeral();
		try {
			this.renderer.renderPendingMarkdown(container);
		} catch (_) {}
		scrollMgr.scheduleScroll(true);
	}
}