// Groups consecutive durable tool messages using explicit continuation edges.
class ToolGroups {

	// ========================================
	// Composition
	// ========================================

	constructor(output) {
		this.output = output;
		this._groupSeq = 0;
	}

	// ========================================
	// Groups
	// ========================================

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

	// ========================================
	// Groups internals
	// ========================================

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
		const content = this.output.directChild(groupEl, '.tool-group-content');
		if (content) {
			const outputs = content.querySelectorAll('.tool-output:not(.tool-output-group)');
			outputs.forEach(el => names.push(...this._toolNames(el)));
		}

		const namesEl = this.output.directChild(
			this.output.directChild(groupEl, '.tool-output-toggle.tool-group-toggle'),
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
			const msg = this.output.directChild(box, '.msg');
			const group = this.output.directChild(msg, '.tool-output-group');
			return (msg && group) ? {box, msg, group} : null;
		}

		const msg = this.output.directChild(box, '.msg');
		if (!msg) return null;
		// Tool wrappers live inside .msg-timeline in the current renderer. Keep
		// the fallback to .msg for older/special render paths so grouping works
		// identically for history rebuilds and incremental mutations.
		const timeline = this.output.directChild(msg, '.msg-timeline') || msg;
		const output = this.output.directChild(timeline, '.tool-output:not(.tool-output-group)');
		if (!output) return null;

		let toolOnly = box.getAttribute('data-tool-only');
		if (toolOnly == null) {
			// Backward/alternate render-path fallback. A named tool-output with no
			// markdown response is the same "tool-only" shape used by the template.
			const hasNamedTool = !!output.getAttribute('data-tool-names');
			let hasAssistantText = false;
			try {
				hasAssistantText = !!timeline.querySelector(':scope > .md-block, :scope > .msg-part .md-block');
			} catch (_) {
				hasAssistantText = !!timeline.querySelector('.md-block');
			}
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

		const firstHeader = this.output.directChild(first.box, '.name-header');
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
		toggle.addEventListener('click', () => this.output.toggleGroup(groupId));

		const label = document.createElement('span');
		label.className = 'tool-output-label';
		label.textContent = ((typeof window !== 'undefined' && window.LOCALE_TOOLS)
			? String(window.LOCALE_TOOLS)
			: 'Tools') + ':\u00a0';

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
		const content = this.output.directChild(groupCandidate.group, '.tool-group-content');
		if (!content) return groupCandidate;
		const inner = this.output.directChild(content, '.tool-collapse-inner');
		const body = inner ? this.output.directChild(inner, '.tool-collapse-body') : null;
		(body || inner || content).appendChild(next.box);
		this._groupSummary(groupCandidate.group);
		return groupCandidate;
	}

}
