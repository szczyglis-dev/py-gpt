// ==========================================================================
// Tool output
// ==========================================================================

class ToolOutput {

	// ========================================
	// Composition
	// ========================================

	constructor(scrollMgr = null, {templates = null, renderer = null, findStatusHost = () => null} = {}) {
		this.groups = new ToolGroups(this);
		this.scrollMgr = scrollMgr;
		this.templates = templates;
		this.renderer = renderer;
		this.findStatusHost = findStatusHost;
		this._viewportAnchorSeq = 0;
		this._viewportAnchorTimer = 0;
	}

	// ========================================
	// Live and durable tool reconciliation
	// ========================================

	// Reconcile authoritative snapshots by protocol identity. Keep the accordion
	// and unchanged payload nodes alive, including their selection and scroll.
	reconcile(parent, desired) {
		const wanted = JSON.parse(desired.getAttribute('data-tool-keys') || '[]');
		const sources = Array.from(parent.querySelectorAll('.tool-output[data-tool-keys]')).filter(el =>
			(!wanted.length && el.id === desired.id) || JSON.parse(el.getAttribute('data-tool-keys') || '[]').some(key => wanted.includes(key)));
		const existing = sources[0];
		if (!existing) return desired.cloneNode(true);
		const content = this._content(existing);
		const expanded = sources.some(el => {
			const body = this._content(el);
			return body && body.classList.contains('is-expanded');
		});
		const clone = desired.cloneNode(true);
		// Preserve each call's payload and nested expansion across growing groups.
		for (const pair of Array.from(clone.querySelectorAll('[data-tool-key]'))) {
			const old = sources.flatMap(source => Array.from(source.querySelectorAll('[data-tool-key]'))).find(el =>
				el.getAttribute('data-tool-key') === pair.getAttribute('data-tool-key'));
			if (!old) continue;
			for (const selector of ['.tool-output-request-data', '.tool-output-result-data']) {
				const nextData = pair.querySelector(selector), oldData = old.querySelector(selector);
				if (!nextData || !oldData) continue;
				const raw = el => {
					const pending = el.querySelector('[md-block-markdown]');
					if (pending) return pending.textContent;
					const code = el.querySelector('pre code');
					return code ? this._codeMarkdown(code.textContent) : '';
				};
				if (raw(nextData) === raw(oldData)) nextData.replaceWith(oldData);
			}
			const oldItem = old.closest('.tool-output-item'), nextItem = pair.closest('.tool-output-item');
			if (nextItem && ((oldItem && oldItem.querySelector('[aria-expanded="true"]')) || (!oldItem && expanded))) {
				this._setExpanded(nextItem.querySelector('.tool-group-content'), true);
				nextItem.querySelector('button').setAttribute('aria-expanded', 'true');
				nextItem.querySelector('.tool-output-arrow').classList.add('toggle-expanded');
			}
		}
		for (const attr of Array.from(existing.attributes)) existing.removeAttribute(attr.name);
		for (const attr of Array.from(clone.attributes)) existing.setAttribute(attr.name, attr.value);
		const oldHeader = this.directChild(existing, '.tool-output-toggle');
		const newHeader = this.directChild(clone, '.tool-output-toggle');
		if (oldHeader && newHeader) {
			oldHeader.onclick = null;
			for (const attr of Array.from(oldHeader.attributes)) oldHeader.removeAttribute(attr.name);
			for (const attr of Array.from(newHeader.attributes)) oldHeader.setAttribute(attr.name, attr.value);
			for (const child of Array.from(newHeader.children)) {
				const oldChild = Array.from(oldHeader.children).find(el => el.className === child.className);
				if (!oldChild) continue;
				if (oldChild.textContent !== child.textContent) oldChild.textContent = child.textContent;
				child.replaceWith(oldChild);
			}
			oldHeader.replaceChildren(...Array.from(newHeader.childNodes));
			newHeader.replaceWith(oldHeader);
		}
		const newContent = this._content(clone);
		if (content && newContent) {
			const body = this._contentBody(content);
			body.replaceChildren(...Array.from(this._contentBody(newContent).childNodes));
			newContent.replaceWith(content);
		}
		existing.replaceChildren(...Array.from(clone.childNodes));
		if (expanded) {
			this._setExpanded(this._content(existing), true);
			existing.querySelector('button').setAttribute('aria-expanded', 'true');
			existing.querySelector('.tool-output-arrow').classList.add('toggle-expanded');
		}
		for (const duplicate of sources.slice(1)) duplicate.remove();
		return existing;
	}

	syncLive(parentId, calls) {
		const host = this.findStatusHost(parentId, false);
		if (!host || !calls.length) return;
		const status = Array.from(host.timeline.querySelectorAll('.workflow-status')).reverse().find(el => el.dataset.statusKind === 'tool');
		if (!status) return;
		const shell = document.createElement('div');
		shell.innerHTML = this.templates.tools.renderToolOutputWrapper({id: `live-${parentId}`, extra: {tool_calls: calls, tool_output_visible: true}});
		const desired = shell.firstElementChild;
		desired.setAttribute('data-live-tools', '1');
		desired.classList.add('tool-output-live');
		const output = this.reconcile(host.timeline, desired);
		// Avoid interpolating nonnumeric live IDs into template onclick code.
		output.querySelector('button').onclick = () => this.toggle(`live-${parentId}`);
		status.classList.add('live-tool-status');
		// A provider continuation may already have promoted this series into a
		// timeline part. Update it in place instead of creating another status copy.
		if (!output.isConnected) status.appendChild(output);
		status.style.display = status.contains(output) ? '' : 'none';
		this.renderer.renderPendingMarkdown(output);
	}

	// ========================================
	// Tool output lifecycle
	// ========================================

	// Return direct child matching selector without relying on :scope support.
	directChild(parent, selector) {
		if (!parent || !parent.children) return null;
		const children = Array.from(parent.children);
		for (let i = 0; i < children.length; i++) {
			const child = children[i];
			try {
				if (child.matches(selector)) return child;
			} catch (_) {}
		}
		return null;
	}

	// Placeholder for loader show (can be extended by host).
	showLoader() {
		return;
	}

	// Hide spinner elements in bot messages.
	hideLoader() {
		const elements = document.querySelectorAll('.msg-bot');
		if (elements.length > 0) elements.forEach(el => {
			const s = el.querySelector('.spinner');
			if (s) s.style.display = 'none';
		});
	}

	// Begins a new tool session.
	begin() {
		this.showLoader();
	}

	// Ends the current tool session.
	end() {
		this.hideLoader();
	}

	// Enables the tool output area.
	enable() {
		const els = this._mutableOutputs();
		if (els.length) els[els.length - 1].style.display = 'block';
	}

	// Disables the tool output area.
	disable() {
		const els = this._mutableOutputs();
		if (els.length) els[els.length - 1].style.display = 'none';
	}

	// Append tool output. Structured tool blocks keep the request intact and
	// append only to the Result section; legacy blocks keep the old HTML path.
	append(content) {
		this.hideLoader();
		this.enable();
		const els = this._mutableOutputs();
		if (els.length) {
			const contentEl = this._content(els[els.length - 1]);
			if (!contentEl) return;
			const results = contentEl.querySelectorAll('.tool-output-result-data');
			const resultEl = results.length ? results[results.length - 1] : null;
			if (resultEl) {
				const next = this._resultRaw(resultEl) + (content == null ? '' : String(content));
				this._renderStructuredResult(resultEl, next);
			} else {
				this._contentBody(contentEl).insertAdjacentHTML('beforeend', content == null ? '' : String(content));
			}
		}
	}

	// Replace tool output. Structured tool blocks replace only Result, keeping
	// the Tool request visible after expansion.
	update(content) {
		this.hideLoader();
		this.enable();
		const els = this._mutableOutputs();
		if (els.length) {
			const contentEl = this._content(els[els.length - 1]);
			if (!contentEl) return;
			const results = contentEl.querySelectorAll('.tool-output-result-data');
			const resultEl = results.length ? results[results.length - 1] : null;
			if (resultEl) {
				this._renderStructuredResult(resultEl, content);
			} else {
				this._contentBody(contentEl).innerHTML = content == null ? '' : String(content);
			}
		}
	}

	// Clear only Result in structured tool blocks; legacy blocks are cleared
	// without changing wrapper visibility. In particular, STOP/ESC may emit a
	// clear even when no tool was used, so revealing the hidden legacy wrapper
	// here would leave an empty expand arrow in the message.
	clear() {
		this.hideLoader();
		const els = this._mutableOutputs();
		if (els.length) {
			const contentEl = this._content(els[els.length - 1]);
			if (!contentEl) return;
			const results = contentEl.querySelectorAll('.tool-output-result-data');
			const resultEl = results.length ? results[results.length - 1] : null;
			if (resultEl) this._renderStructuredResult(resultEl, '');
			else this._contentBody(contentEl).replaceChildren();
		}
	}

	// ========================================
	// Accordion interaction and viewport
	// ========================================

	// Toggle a parent tool group. Individual tools remain independently collapsed.
	toggleGroup(id) {
		const groupEl = document.getElementById(String(id || ''));
		if (!groupEl) return;
		const content = this.directChild(groupEl, '.tool-group-content');
		if (!content) return;
		const header = this.directChild(groupEl, '.tool-output-toggle.tool-group-toggle');
		const expanded = !content.classList.contains('is-expanded');

		this._withViewportAnchor(header || groupEl, () => {
			this._setExpanded(content, expanded);
			if (header) header.setAttribute('aria-expanded', expanded ? 'true' : 'false');
			const arrow = header ? header.querySelector('.tool-group-arrow') : null;
			if (arrow) arrow.classList.toggle('toggle-expanded', expanded);
		});
	}


	// Toggle visibility of a specific tool output block by message id.
	toggle(id) {
		let outputEl = document.getElementById('tool-output-' + id);
		if (!outputEl) {
			const el = document.getElementById('msg-bot-' + id);
			if (!el) return;
			outputEl = el.querySelector('.tool-output:not(.tool-output-group)');
		}
		if (!outputEl) return;
		const contentEl = this._content(outputEl);
		if (!contentEl) return;

		const headerEl = outputEl.querySelector('.tool-output-toggle');
		const expanded = !contentEl.classList.contains('is-expanded');

		this._withViewportAnchor(headerEl || outputEl, () => {
			this._setExpanded(contentEl, expanded);
			if (headerEl) headerEl.setAttribute('aria-expanded', expanded ? 'true' : 'false');

			const arrowEl = outputEl.querySelector('.tool-output-arrow') || outputEl.querySelector('.toggle-cmd-output img');
			if (arrowEl) arrowEl.classList.toggle('toggle-expanded', expanded);
		});
	}

	// ========================================
	// Accordion interaction and viewport internals
	// ========================================

	// Expanding/collapsing a tool/workflow block is an explicit viewport
	// interaction. Keep the clicked header at the same screen Y coordinate
	// instead of letting page auto-follow or Chromium scroll anchoring pin the
	// content below it (which makes the accordion appear to grow upward).
	_withViewportAnchor(anchorEl, mutate) {
		if (typeof mutate !== 'function') return;

		const anchor = anchorEl && anchorEl.isConnected ? anchorEl : null;
		const scroller = (typeof Utils !== 'undefined' && Utils.SE)
			? Utils.SE
			: (document.scrollingElement || document.documentElement);
		const beforeTop = anchor ? anchor.getBoundingClientRect().top : null;
		const scrollMgr = this.scrollMgr;

		// A click on an accordion means the user owns the viewport now. This also
		// prevents ResizeObserver FOLLOW corrections while the 0fr -> 1fr CSS
		// transition changes document height.
		if (scrollMgr && typeof scrollMgr.suspendAutoFollow === 'function') {
			scrollMgr.suspendAutoFollow();
		}

		const root = document.documentElement;
		if (root && root.classList) root.classList.add('tool-viewport-anchor-lock');

		mutate();

		const seq = ++this._viewportAnchorSeq;
		const correct = () => {
			if (seq !== this._viewportAnchorSeq || !anchor || !anchor.isConnected || beforeTop == null || !scroller) return;
			const delta = anchor.getBoundingClientRect().top - beforeTop;
			if (Math.abs(delta) <= 0.5) return;

			const maxTop = Math.max(0, Number(scroller.scrollHeight || 0) - Number(scroller.clientHeight || 0));
			const target = Math.max(0, Math.min(maxTop, Number(scroller.scrollTop || 0) + delta));
			if (scrollMgr && typeof scrollMgr.markProgrammaticScroll === 'function') {
				scrollMgr.markProgrammaticScroll(target);
			}
			try { scroller.scrollTop = target; } catch (_) {}
		};

		// Correct once after layout commits and once after the accordion transition
		// settles. The root lock disables Chromium's native anchor candidate while
		// the geometry is changing.
		try { requestAnimationFrame(correct); } catch (_) { correct(); }
		if (this._viewportAnchorTimer) clearTimeout(this._viewportAnchorTimer);
		this._viewportAnchorTimer = setTimeout(() => {
			if (seq !== this._viewportAnchorSeq) return;
			correct();
			if (root && root.classList) root.classList.remove('tool-viewport-anchor-lock');
			this._viewportAnchorTimer = 0;
			if (scrollMgr && typeof scrollMgr.scheduleScrollFabUpdate === 'function') {
				scrollMgr.scheduleScrollFabUpdate();
			}
		}, 280);
	}

	// Prepare a collapsible body for CSS-only height animation. A single inner
	// wrapper lets CSS interpolate grid-template-rows from 0fr to 1fr without
	// measuring dynamic tool/workflow content in JavaScript.
	_prepareCollapsible(contentEl) {
		if (!contentEl) return null;
		let inner = this.directChild(contentEl, '.tool-collapse-inner');
		let body = inner ? this.directChild(inner, '.tool-collapse-body') : null;
		if (!inner) {
			inner = document.createElement('div');
			inner.className = 'tool-collapse-inner';
			body = document.createElement('div');
			body.className = 'tool-collapse-body';
			while (contentEl.firstChild) body.appendChild(contentEl.firstChild);
			inner.appendChild(body);
			contentEl.appendChild(inner);
		} else if (!body) {
			body = document.createElement('div');
			body.className = 'tool-collapse-body';
			while (inner.firstChild) body.appendChild(inner.firstChild);
			inner.appendChild(body);
		}

		// Templates historically used inline display:none. Remove it once, then
		// let the CSS grid state own visibility for all subsequent toggles.
		if (contentEl.style && contentEl.style.display === 'none') {
			contentEl.style.removeProperty('display');
			// Commit the collapsed 0fr state before adding is-expanded so the very
			// first opening animates as well.
			void contentEl.offsetHeight;
		}
		return body;
	}

	_setExpanded(contentEl, expanded) {
		if (!contentEl) return;
		this._prepareCollapsible(contentEl);
		contentEl.classList.toggle('is-expanded', !!expanded);
	}

	// Return the collapsible body while keeping compatibility with HTML produced
	// by older frontend bundles that used the generic `.content` class.
	_content(outputEl) {
		if (!outputEl) return null;
		return outputEl.querySelector('.tool-output-content, .content');
	}

	_contentBody(contentEl) {
		if (!contentEl) return null;
		const inner = this.directChild(contentEl, '.tool-collapse-inner');
		return (inner && this.directChild(inner, '.tool-collapse-body')) || inner || contentEl;
	}

	// ========================================
	// Tool output lifecycle internals
	// ========================================

	// Return only mutable/live tool-output wrappers. Completed agent workflow
	// accordions deliberately reuse the generic .tool-output styling, but they
	// are durable history and must never be touched by live ToolOutput.clear(),
	// update(), append(), enable(), or disable() calls from a later turn.
	_mutableOutputs() {
		const outputs = Array.from(document.querySelectorAll('.tool-output'));
		return outputs.filter((el) => {
			if (!el || !el.classList) return false;
			if (el.classList.contains('agent-workflow-output')) return false;
			if (el.classList.contains('tool-output-group')) return false;
			try {
				if (el.closest('.agent-workflow-output')) return false;
			} catch (_) {}
			return true;
		});
	}

	// ========================================
	// Tool payload rendering internals
	// ========================================

	// Pretty-print valid JSON, preserving arbitrary non-JSON tool output as text.
	_formatPayload(value) {
		if (value == null) return '';
		const raw = String(value);
		const trimmed = raw.trim();
		if (!trimmed) return '';
		try {
			return JSON.stringify(JSON.parse(trimmed), null, 2);
		} catch (_) {
			return raw;
		}
	}

	// Build a robust JSON fence accepted by the same Markdown parser used for
	// regular assistant messages.
	_codeMarkdown(value) {
		const text = this._formatPayload(value);
		if (!text) return '';
		let maxTicks = 0;
		const runs = text.match(/`+/g);
		if (runs) runs.forEach(run => { maxTicks = Math.max(maxTicks, run.length); });
		const fence = '`'.repeat(Math.max(3, maxTicks + 1));
		return `${fence}json\n${text}\n${fence}`;
	}

	// Recover currently displayed structured result for append() calls.
	_resultRaw(resultEl) {
		if (!resultEl) return '';
		if (Object.prototype.hasOwnProperty.call(resultEl, '_toolRaw')) {
			return String(resultEl._toolRaw || '');
		}

		const code = resultEl.querySelector('.code-wrapper pre code');
		if (code) return code.textContent || '';

		const pending = resultEl.querySelector('[md-block-markdown]');
		if (pending) {
			const src = pending.textContent || '';
			const match = src.match(/^(`{3,})json[^\n]*\n([\s\S]*?)\n\1\s*$/i);
			if (match) return match[2];
			return src;
		}

		return resultEl.textContent || '';
	}

	// Rebuild the structured Result section as Markdown and let the regular
	// renderer create/highlight the code block. The outer container stays stable
	// so live tool updates can replace it repeatedly.
	_renderStructuredResult(resultEl, content) {
		if (!resultEl) return;
		const raw = content == null ? '' : String(content);
		const hasContent = raw.trim() !== '';
		resultEl._toolRaw = raw;

		const responseSection = resultEl.closest('.tool-output-response-section');
		if (responseSection) responseSection.style.display = hasContent ? '' : 'none';

		resultEl.replaceChildren();
		if (!hasContent) return;

		const md = document.createElement('div');
		md.className = 'tool-output-markdown';
		md.setAttribute('md-block-markdown', '1');
		const responseLabel = (typeof window !== 'undefined' && window.LOCALE_TOOL_RESPONSE)
			? String(window.LOCALE_TOOL_RESPONSE)
			: 'Output';
		md.setAttribute('data-code-header', responseLabel);
		md.textContent = this._codeMarkdown(raw);
		resultEl.appendChild(md);

		try {
			const renderer = this.renderer;
			if (renderer && typeof renderer.renderPendingMarkdown === 'function') {
				const pending = renderer.renderPendingMarkdown(resultEl);
				if (pending && typeof pending.catch === 'function') pending.catch(() => {});
			}
		} catch (_) {}
	}

}
