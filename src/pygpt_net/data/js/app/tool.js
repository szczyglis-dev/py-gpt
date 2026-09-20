// ==========================================================================
// Tool output
// ==========================================================================

class ToolOutput {

	constructor() {
		this._groupSeq = 0;
	}

	// Return direct child matching selector without relying on :scope support.
	_directChild(parent, selector) {
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

	// Extract raw tool names from a rendered tool-output wrapper.
	_toolNames(outputEl) {
		if (!outputEl) return [];
		const raw = outputEl.getAttribute('data-tool-names') || '';
		if (raw) {
			try {
				const parsed = JSON.parse(raw);
				if (Array.isArray(parsed)) return parsed.map(v => String(v || 'tool'));
			} catch (_) {}
		}
		const nameEl = outputEl.querySelector('.tool-output-name');
		if (!nameEl) return [];
		const text = String(nameEl.textContent || '').trim();
		return text ? [text] : [];
	}

	// Build the compact parent label: "Tools: a, b … and N more".
	_groupSummary(groupEl) {
		if (!groupEl) return;
		const names = [];
		const content = this._directChild(groupEl, '.tool-group-content');
		if (content) {
			const outputs = content.querySelectorAll('.tool-output:not(.tool-output-group)');
			outputs.forEach(el => names.push(...this._toolNames(el)));
		}

		const namesEl = this._directChild(
			this._directChild(groupEl, '.tool-output-toggle.tool-group-toggle'),
			'.tool-output-name.tool-group-names'
		);
		if (!namesEl) return;

		// Parent summary only: show the newest tools first. The expanded
		// group content itself keeps the original chronological order.
		const shown = names.slice().reverse().slice(0, 2);
		let label = shown.join(', ');
		const remaining = Math.max(0, names.length - shown.length);
		if (remaining > 0) {
			const tpl = (typeof window !== 'undefined' && window.LOCALE_TOOL_MORE)
				? String(window.LOCALE_TOOL_MORE)
				: 'and {count} more';
			const more = tpl.split('{count}').join(String(remaining));
			label += `${label ? ' … ' : ''}${more}`;
		}
		namesEl.textContent = label || 'tool';
	}

	// Return metadata for a direct message box that can participate in grouping.
	_groupCandidate(box) {
		if (!box || !box.classList || !box.classList.contains('msg-bot')) return null;

		if (box.classList.contains('tool-group-box')) {
			const msg = this._directChild(box, '.msg');
			const group = this._directChild(msg, '.tool-output-group');
			return (msg && group) ? {box, msg, group} : null;
		}

		const msg = this._directChild(box, '.msg');
		const output = this._directChild(msg, '.tool-output:not(.tool-output-group)');
		if (!msg || !output) return null;

		let toolOnly = box.getAttribute('data-tool-only');
		if (toolOnly == null) {
			// Backward/alternate render-path fallback.  A named tool-output with no
			// markdown response is the same "tool-only" shape used by the template.
			const hasNamedTool = !!output.getAttribute('data-tool-names');
			const hasAssistantText = !!this._directChild(msg, '.md-block');
			toolOnly = (hasNamedTool && !hasAssistantText) ? '1' : '0';
		}
		if (toolOnly !== '1') return null;
		return {box, msg, output, group: null};
	}

	// Create a parent tool group around two consecutive tool-only messages.
	_createGroup(first, second) {
		if (!first || !second || !first.box || !second.box) return first;
		const parent = document.createElement('div');
		parent.className = 'msg-box msg-bot tool-group-box';
		parent.setAttribute('data-tool-only', '1');

		const firstHeader = this._directChild(first.box, '.name-header');
		if (firstHeader) parent.appendChild(firstHeader);

		const msg = document.createElement('div');
		msg.className = 'msg';
		const group = document.createElement('div');
		group.className = 'tool-output tool-output-group';
		const firstId = first.box.id || `runtime-${++this._groupSeq}`;
		const groupId = `tool-group-${firstId}`;
		group.id = groupId;

		const toggle = document.createElement('button');
		toggle.type = 'button';
		toggle.className = 'tool-output-toggle tool-group-toggle';
		toggle.setAttribute('aria-expanded', 'false');
		const expandTitle = (typeof trans !== 'undefined' && trans) ? trans('action.cmd.expand') : 'Expand';
		toggle.setAttribute('title', expandTitle);
		toggle.addEventListener('click', () => this.toggleGroup(groupId));

		const label = document.createElement('span');
		label.className = 'tool-output-label';
		const strong = document.createElement('b');
		strong.textContent = (typeof window !== 'undefined' && window.LOCALE_TOOLS)
			? String(window.LOCALE_TOOLS)
			: 'Tools';
		label.appendChild(strong);
		label.appendChild(document.createTextNode(':\u00a0'));

		const names = document.createElement('span');
		names.className = 'tool-output-name tool-group-names';

		const arrow = document.createElement('img');
		arrow.className = 'tool-output-arrow tool-group-arrow';
		arrow.width = 25;
		arrow.height = 25;
		arrow.alt = '';
		if (typeof window !== 'undefined' && window.ICON_EXPAND) arrow.src = window.ICON_EXPAND;

		toggle.appendChild(label);
		toggle.appendChild(names);
		toggle.appendChild(arrow);

		const content = document.createElement('div');
		content.className = 'tool-group-content';
		content.style.display = 'none';

		group.appendChild(toggle);
		group.appendChild(content);
		msg.appendChild(group);
		parent.appendChild(msg);

		first.box.parentNode.insertBefore(parent, first.box);
		content.appendChild(first.box);
		content.appendChild(second.box);
		this._groupSummary(group);
		return {box: parent, msg, group};
	}

	// Append another consecutive tool-only message to an existing parent group.
	_appendToGroup(groupCandidate, next) {
		if (!groupCandidate || !groupCandidate.group || !next || !next.box) return groupCandidate;
		const content = this._directChild(groupCandidate.group, '.tool-group-content');
		if (!content) return groupCandidate;
		content.appendChild(next.box);
		this._groupSummary(groupCandidate.group);
		return groupCandidate;
	}

	// Group only explicit continuation edges. This runs after both full-history
	// rendering and incremental appends, so behavior stays identical in real time.
	groupConsecutive(root) {
		if (!root || !root.children) return;
		const boxes = Array.from(root.children);
		let anchor = null;

		for (let i = 0; i < boxes.length; i++) {
			const box = boxes[i];
			const candidate = this._groupCandidate(box);
			if (!candidate) {
				anchor = null;
				continue;
			}

			if (!anchor) {
				anchor = candidate;
				continue;
			}

			// An already-built group may absorb the next explicit continuation.
			// A fresh tool message joins the preceding one only when Python marked
			// it as the internal continuation of that exact tool request.
			const isContinuation = box.getAttribute('data-tool-chain-continuation') === '1';
			if (!isContinuation) {
				anchor = candidate;
				continue;
			}

			if (anchor.group) anchor = this._appendToGroup(anchor, candidate);
			else anchor = this._createGroup(anchor, candidate);
		}
	}

	// Toggle a parent tool group. Individual tools remain independently collapsed.
	toggleGroup(id) {
		const groupEl = document.getElementById(String(id || ''));
		if (!groupEl) return;
		const content = this._directChild(groupEl, '.tool-group-content');
		if (!content) return;
		const expanded = content.style.display === 'none';
		content.style.display = expanded ? 'block' : 'none';

		const header = this._directChild(groupEl, '.tool-output-toggle.tool-group-toggle');
		if (header) header.setAttribute('aria-expanded', expanded ? 'true' : 'false');
		const arrow = header ? header.querySelector('.tool-group-arrow') : null;
		if (arrow) arrow.classList.toggle('toggle-expanded', expanded);
	}

	// Return the collapsible body while keeping compatibility with HTML produced
	// by older frontend bundles that used the generic `.content` class.
	_content(outputEl) {
		if (!outputEl) return null;
		return outputEl.querySelector('.tool-output-content, .content');
	}

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
		md.textContent = this._codeMarkdown(raw);
		resultEl.appendChild(md);

		try {
			const renderer = (typeof runtime !== 'undefined' && runtime) ? runtime.renderer : null;
			if (renderer && typeof renderer.renderPendingMarkdown === 'function') {
				const pending = renderer.renderPendingMarkdown(resultEl);
				if (pending && typeof pending.catch === 'function') pending.catch(() => {});
			}
		} catch (_) {}
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
		const els = document.querySelectorAll('.tool-output');
		if (els.length) els[els.length - 1].style.display = 'block';
	}

	// Disables the tool output area.
	disable() {
		const els = document.querySelectorAll('.tool-output');
		if (els.length) els[els.length - 1].style.display = 'none';
	}

	// Append tool output. Structured tool blocks keep the request intact and
	// append only to the Result section; legacy blocks keep the old HTML path.
	append(content) {
		this.hideLoader();
		this.enable();
		const els = document.querySelectorAll('.tool-output');
		if (els.length) {
			const contentEl = this._content(els[els.length - 1]);
			if (!contentEl) return;
			const resultEl = contentEl.querySelector('.tool-output-result-data');
			if (resultEl) {
				const next = this._resultRaw(resultEl) + (content == null ? '' : String(content));
				this._renderStructuredResult(resultEl, next);
			} else {
				contentEl.insertAdjacentHTML('beforeend', content == null ? '' : String(content));
			}
		}
	}

	// Replace tool output. Structured tool blocks replace only Result, keeping
	// the Tool request visible after expansion.
	update(content) {
		this.hideLoader();
		this.enable();
		const els = document.querySelectorAll('.tool-output');
		if (els.length) {
			const contentEl = this._content(els[els.length - 1]);
			if (!contentEl) return;
			const resultEl = contentEl.querySelector('.tool-output-result-data');
			if (resultEl) {
				this._renderStructuredResult(resultEl, content);
			} else {
				contentEl.innerHTML = content == null ? '' : String(content);
			}
		}
	}

	// Clear only Result in structured tool blocks; legacy blocks are cleared
	// without changing wrapper visibility. In particular, STOP/ESC may emit a
	// clear even when no tool was used, so revealing the hidden legacy wrapper
	// here would leave an empty expand arrow in the message.
	clear() {
		this.hideLoader();
		const els = document.querySelectorAll('.tool-output');
		if (els.length) {
			const contentEl = this._content(els[els.length - 1]);
			if (!contentEl) return;
			const resultEl = contentEl.querySelector('.tool-output-result-data');
			if (resultEl) this._renderStructuredResult(resultEl, '');
			else contentEl.replaceChildren();
		}
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

		const expanded = contentEl.style.display === 'none';
		contentEl.style.display = expanded ? 'block' : 'none';

		const headerEl = outputEl.querySelector('.tool-output-toggle');
		if (headerEl) headerEl.setAttribute('aria-expanded', expanded ? 'true' : 'false');

		const arrowEl = outputEl.querySelector('.tool-output-arrow') || outputEl.querySelector('.toggle-cmd-output img');
		if (arrowEl) arrowEl.classList.toggle('toggle-expanded', expanded);
	}
}