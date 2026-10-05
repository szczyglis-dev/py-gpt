// ==========================================================================
// Nodes manager
// ==========================================================================

class NodesManager {

	// Nodes manager for handling message nodes.
	constructor(dom, renderer, highlighter, math, toolOutput, templates) {
		this.dom = dom;
		this.renderer = renderer;
		this.highlighter = highlighter;
		this.math = math;
		this.toolOutput = toolOutput || null;
        this.templates = templates || null;
		// User message collapse manager
		this.userCollapse = new UserCollapseManager(this.renderer.cfg);
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
	materializeUserMdAsPlainText(scopeEl) {
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
	ensureUserCopyIcons(root) {
        // User actions are rendered below the bubble by the message template.
        for (const button of (root || document).querySelectorAll('.msg-user .msg .msg-copy-btn')) button.remove();
    }

	// Append HTML/text into the message input container.
	// If plain text is provided, wrap it into a minimal msg-user box to keep layout consistent.
	appendToInput(content) {
		const el = this.dom.get('_append_input_');
		if (!el) return;

		let html = String(content || '');
		let dateLabel = '';
        let attachments = null;
		const inputEnvelopePrefix = '__PYGPT_INPUT_V1__';
		if (html.startsWith(inputEnvelopePrefix)) {
			try {
				const payload = JSON.parse(html.slice(inputEnvelopePrefix.length));
				html = String((payload && payload.text) || '');
				dateLabel = String((payload && payload.date_label) || '');
                attachments = payload && payload.user_attachments;
			} catch (_) {
				// Keep backward-compatible plain-text behavior if the envelope is malformed.
			}
		}
		const trimmed = html.trim();

		// If already a full msg-user wrapper, append as-is; otherwise wrap the plain text.
		const isWrapped = (trimmed.startsWith('<div') && /class=["']msg-box msg-user["']/.test(trimmed));
		if (!isWrapped) {
			// Treat incoming payload as plain text (escape + convert newlines to <br>).
			const body = (typeof Utils !== 'undefined' && Utils.renderMentionText) ?
				Utils.renderMentionText(html) :
				((typeof Utils !== 'undefined' && Utils.escapeHtml) ?
					Utils.escapeHtml(html) :
					String(html).replace(/[&<>"']/g, m => ({
						'&': '&amp;',
						'<': '&lt;',
						'>': '&gt;',
						'"': '&quot;',
						"'": '&#039;'
					} [m])).replace(/\r?\n/g, '<br>'));
			// Minimal, margin-less user message (no empty msg-extra to avoid extra spacing).
			html = trimmed ? `<div class="msg-box msg-user"><div class="msg"><p style="margin:0">${body}</p></div></div>` : '';
		}

        const attachmentHtml = attachments && this.templates
            ? this.templates.artifacts.renderUserAttachments(attachments) : '';
        // Durable input has a permanent action row. Reserve its footprint now
        // as well, so replacing this preview cannot shift the streamed reply.
        html = `<div class="msg-user-region input-live-arrival">${attachmentHtml}${html}<div class="user-message-actions" aria-hidden="true"></div></div>`;

		if (dateLabel) {
			const safeDateLabel = (typeof Utils !== 'undefined' && Utils.escapeHtml) ?
				Utils.escapeHtml(dateLabel) :
				String(dateLabel).replace(/[&<>"']/g, m => ({
					'&': '&amp;',
					'<': '&lt;',
					'>': '&gt;',
					'"': '&quot;',
					"'": '&#039;'
				} [m]));
			html = `<div class="msg-date-separator input-live-date">${safeDateLabel}</div>${html}`;
		}

		// Synchronous DOM update.
		el.insertAdjacentHTML('beforeend', html);

		// Apply collapse to any user messages in input area (now or later).
		try {
			this.userCollapse.apply(el);
		} catch (_) {}

		// Ensure copy icons exist (inject or reposition outside uc-content).
		try {
			this.ensureUserCopyIcons(el);
		} catch (_) {}
	}

	// Group consecutive tool-only messages after DOM insertion. The grouping engine
	// uses explicit continuation metadata, so a reload and real-time append follow
	// exactly the same path.
	refreshToolGroups(root) {
		try {
			if (this.toolOutput && typeof this.toolOutput.groups.groupConsecutive === 'function') {
				this.toolOutput.groups.groupConsecutive(root);
			}
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
			this.materializeUserMdAsPlainText(el);
			// Collapse before scrolling to ensure final height is used for scroll computations.
			try {
				this.userCollapse.apply(el);
			} catch (_) {}
			// Ensure copy icons exist for user messages.
			try {
				this.ensureUserCopyIcons(el);
			} catch (_) {}

			scrollMgr.scrollToBottom(false);
			scrollMgr.scheduleScrollFabUpdate();
			scrollMgr.virtualization.scheduleMessageVirtualizationRefresh();
			return;
		}

		el.insertAdjacentHTML('beforeend', content);
		this.refreshToolGroups(el);

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
					this.userCollapse.apply(el);
				} catch (_) {}

				// Ensure copy icons exist for user messages.
				try {
					this.ensureUserCopyIcons(el);
				} catch (_) {}

				// Only now scroll to bottom and update FAB – uses post-collapse heights.
				scrollMgr.scrollToBottom(false);
				scrollMgr.scheduleScrollFabUpdate();
				scrollMgr.virtualization.scheduleMessageVirtualizationRefresh();
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
			scrollMgr.virtualization.scheduleMessageVirtualizationRefresh();
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
			this.materializeUserMdAsPlainText(el);
			// Collapse before scrolling to ensure final height is used for scroll computations.
			try {
				this.userCollapse.apply(el);
			} catch (_) {}
			// Ensure copy icons exist for user messages.
			try {
				this.ensureUserCopyIcons(el);
			} catch (_) {}

			scrollMgr.scrollToBottom(false, true);
			scrollMgr.scheduleScrollFabUpdate();
			scrollMgr.virtualization.scheduleMessageVirtualizationRefresh();
			return;
		}

		el.insertAdjacentHTML('beforeend', content);
		this.refreshToolGroups(el);

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
					this.userCollapse.apply(el);
				} catch (_) {}

				// Ensure copy icons exist for user messages.
				try {
					this.ensureUserCopyIcons(el);
				} catch (_) {}

				// Now scroll and update FAB using the collapsed layout.
				scrollMgr.scrollToBottom(false, true);
				scrollMgr.scheduleScrollFabUpdate();
				scrollMgr.virtualization.scheduleMessageVirtualizationRefresh();
			};

			if (maybePromise && typeof maybePromise.then === 'function') {
				maybePromise.then(post);
			} else {
				post();
			}
		} catch (_) {
			scrollMgr.scrollToBottom(false, true);
			scrollMgr.scheduleScrollFabUpdate();
			scrollMgr.virtualization.scheduleMessageVirtualizationRefresh();
		}
	}

	// Append "extra" content into a specific bot message and post-process locally.
	appendExtra(id, content, scrollMgr) {
		const el = document.getElementById('msg-bot-' + id);
		if (!el) return;
		const extra = el.querySelector('.msg-extra');
		if (!extra) return;

		// A delayed extra may target a history row that is currently virtualized.
		// Materialize it first, mutate/render, then re-measure before it can return
		// to the virtual pool.
		try { scrollMgr.virtualization.beginMessageMutation(el); } catch (_) {}
		extra.insertAdjacentHTML('beforeend', content);

		// Extras live below the streaming timeline. If FOLLOW owns the viewport,
		// reconcile to the real bottom in the same JS turn; ResizeObserver then
		// catches later async height changes (Markdown, images, fonts/icons).
		try { scrollMgr.syncBottomNowIfFollowing(); } catch (_) {}

		try {
			const maybePromise = this.renderer.renderPendingMarkdown(extra);

			const post = () => {
				const activeCode = (typeof runtime !== 'undefined' && runtime.stream) ? runtime.stream.code.activeCode : null;

				// Attach observers after Markdown produced the nodes
				try {
					this.highlighter.observeNewCode(extra, {
						deferLastIfStreaming: true,
						minLinesForLast: this.renderer.cfg.PROFILE_CODE.minLinesForHL,
						minCharsForLast: this.renderer.cfg.PROFILE_CODE.minCharsForHL
					}, activeCode);
					this.highlighter.observeMsgBoxes(extra, (box) => this.processBox(box));
				} catch (_) {}

				// KaTeX: honor stream mode; in finalize-only force immediate schedule
				try {
					const mm = getMathMode();
					if (mm === 'finalize-only') this.math.schedule(extra, 0, true);
					else this.math.schedule(extra);
				} catch (_) {}

				// Markdown conversion can change line wrapping/height after insertion.
				try { scrollMgr.virtualization.endMessageMutation(el); } catch (_) {}
				try { scrollMgr.syncBottomNowIfFollowing(); } catch (_) {}
			};

			if (maybePromise && typeof maybePromise.then === 'function') {
				maybePromise.then(post);
			} else {
				post();
			}
		} catch (_) {
			try { scrollMgr.virtualization.endMessageMutation(el); } catch (__) {}
		}

		scrollMgr.scheduleScroll(true);
	}

	// When a new message box appears, hook up code/highlight handlers.
	processBox(box) {
		const activeCode = (typeof runtime !== 'undefined' && runtime.stream) ? runtime.stream.code.activeCode : null;
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
		if (el) (el.closest('.msg-user-region') || el).remove();
		el = document.getElementById('msg-bot-' + id);
		if (el) el.remove();
		this.dom.resetEphemeral();
		try {
			this.renderer.renderPendingMarkdown();
		} catch (_) {}
		scrollMgr.virtualization.scheduleMessageVirtualizationRefresh();
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
			if (remove) (element.closest('.msg-user-region') || element).remove();
		});
		this.dom.resetEphemeral();
		try {
			this.renderer.renderPendingMarkdown(container);
		} catch (_) {}
		scrollMgr.virtualization.scheduleMessageVirtualizationRefresh();
		scrollMgr.scheduleScroll(true);
	}
}
