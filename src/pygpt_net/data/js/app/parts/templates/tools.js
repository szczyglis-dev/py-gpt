// NodeToolsTemplate owns tools behavior and state.
class NodeToolsTemplate {

	// ========================================
	// Composition
	// ========================================

	constructor(templates) {
		this.templates = templates;
	}

	// ========================================
	// Tools
	// ========================================

	renderProgress(label, hierarchy, id) {
        const esc = value => this.templates.escapeHtml(String(value || ''));
        const arrow = `<img src='${this.templates.esc(window.ICON_EXPAND || '')}' class='tool-output-arrow' width='25' height='25' alt=''>`;
        const tools = (calls, prefix) => hierarchy.group_tools && (calls || []).length > 1
            ? this.renderToolOutputWrapper({id: `${prefix}-group`, extra: {tool_calls: calls, tool_output_visible: true}})
            : (calls || []).map(call =>
            this.renderToolOutputWrapper({id: `${prefix}-${call.call_id}`, extra: {tool_calls: [call], tool_output_visible: true}})
        ).join('');
        const workers = (hierarchy.workers || []).map(worker =>
            `<details class='tool-output progress-worker' data-progress-key='${esc(worker.id)}'><summary class='tool-output-toggle'><span>${esc(worker.name)}: ${esc(worker.status)} ${esc(worker.text)}</span>${arrow}</summary><div class='progress-content'>${tools(worker.calls, `${id}-${worker.id}`)}</div></details>`
        ).join('');
        return `<details class='tool-output progress-details' data-progress-key='${esc(id)}'><summary class='tool-output-toggle'><span class='agents-v2-status__text'>${esc(label)}</span>${arrow}</summary><div class='progress-content'>${tools(hierarchy.calls, id)}${workers}</div></details>`;
    }

	// Render tool output wrapper (always collapsed by default; wrapper visibility depends on flag)
	// Inside class NodeTemplateEngine
	renderToolOutputWrapper(block) {
		const extra = block.extra || {};
		const toolCalls = Array.isArray(extra.tool_calls) ? extra.tool_calls.filter(Boolean) : [];
		const hasToolCalls = toolCalls.length > 0;

		// Keep the legacy HTML-ready payload only for old non-structured blocks.
		// Structured tool calls use the raw display result as Markdown JSON code.
		const legacyToolOutput = (extra.tool_output != null) ? String(extra.tool_output) : '';
		const toolResult = (extra.tool_result != null) ? String(extra.tool_result) : '';

		// A tool request itself makes the wrapper visible immediately. The result
		// can arrive later through ToolOutput.update().
		const wrapperDisplay = (extra.tool_output_visible === true || hasToolCalls) ? '' : 'display:none';

		const toggleTitle = (typeof trans !== 'undefined' && trans) ? trans('action.cmd.expand') : 'Expand';
		const expIcon = (typeof window !== 'undefined' && window.ICON_EXPAND) ? window.ICON_EXPAND : '';
		const toolLabel = (typeof window !== 'undefined' && window.LOCALE_TOOL) ? window.LOCALE_TOOL : 'Tool';
		const requestLabel = (typeof window !== 'undefined' && window.LOCALE_TOOL_REQUEST) ? window.LOCALE_TOOL_REQUEST : 'Input';
		const responseLabel = (typeof window !== 'undefined' && window.LOCALE_TOOL_RESPONSE) ? window.LOCALE_TOOL_RESPONSE : 'Output';

		let titleHtml = '';
		let contentHtml = legacyToolOutput;
		let toolNamesAttr = '';
		if (hasToolCalls) {
			const rawNames = toolCalls.map((call) => String(call.name || 'tool'));
			const hasPerCallResponses = toolCalls.every(call => call.call_id) || toolCalls.some((call) =>
				call && Object.prototype.hasOwnProperty.call(call, 'response')
			);
			// A persisted Agents v2 workflow can contain several executed tools on one
			// final message. Mirror the normal cross-message grouping UI: one outer
			// "Tools" accordion, then one independently collapsible "Tool" row per call.
			const groupedInMessage = hasPerCallResponses && rawNames.length > 1;
			let displayNames = rawNames;
			if (groupedInMessage) {
				const shown = rawNames.slice().reverse().slice(0, 2);
				const remaining = rawNames.length - shown.length;
				let summary = shown.join(', ');
				if (remaining > 0) {
					const tpl = (typeof window !== 'undefined' && window.LOCALE_TOOL_MORE)
						? String(window.LOCALE_TOOL_MORE)
						: 'and {count} more';
					const more = tpl.split('{count}').join(String(remaining));
					summary += `${summary ? ' … ' : ''}${more}`;
				}
				displayNames = [summary];
			}
			const names = displayNames.map((name) => this.templates.escapeHtml(name));
			toolNamesAttr = this.templates.escapeHtml(JSON.stringify(rawNames));
			const resultCode = this._renderToolCode(toolResult, responseLabel, extra.tool_result_friendly);

			const arrowHtml = `<img src='${this.templates.esc(expIcon)}' class='tool-output-arrow' width='25' height='25' alt=''>`;
			const titleLabel = groupedInMessage && typeof window !== 'undefined' && window.LOCALE_TOOLS
				? String(window.LOCALE_TOOLS)
				: toolLabel;
			titleHtml =
				`<button type='button' class='tool-output-toggle' onclick='toggleToolOutput(${this.templates.escapeHtml(JSON.stringify(block.id))});' ` +
				`title='${this.templates.escapeHtml(toggleTitle)}' aria-expanded='false'>` +
				`<span class='tool-output-label'>${this.templates.escapeHtml(titleLabel)}:&nbsp;</span>` +
				`<span class='tool-output-name'>${names.join(', ')}</span>${arrowHtml}` +
				`</button>`;

			if (hasPerCallResponses) {
				const renderPair = (call) => {
					const requestCode = this._renderToolCode(call && call.request, requestLabel, call.request_friendly, true);
					const hasResponse = !!call && Object.prototype.hasOwnProperty.call(call, 'response');
					const responseCode = hasResponse ? this._renderToolCode(call.response, responseLabel, call.response_friendly) : '';
					const responseDisplay = hasResponse ? '' : 'display:none';
					return (
						`<div class='tool-output-pair' data-tool-key='${this.templates.escapeHtml(String(call.call_id || call.request || ""))}'>` +
						`<div class='tool-output-section'>` +
						`<div class='tool-output-data tool-output-request-data'>${requestCode}</div>` +
						`</div>` +
						`<div class='tool-output-section tool-output-response-section' style='${responseDisplay}'>` +
						`<div class='tool-output-data tool-output-result-data'>${responseCode}</div>` +
						`</div>` +
						`</div>`
					);
				};

				if (groupedInMessage) {
					contentHtml = toolCalls.map((call, index) => {
						const callName = this.templates.escapeHtml(String((call && call.name) || 'tool'));
						const itemId = `tool-call-${this.templates.esc(block.id)}-${index}`;
						const itemArrow = `<img src='${this.templates.esc(expIcon)}' class='tool-output-arrow tool-group-arrow' width='25' height='25' alt=''>`;
						return (
							`<div class='tool-output-group tool-output-item' id='${itemId}'>` +
							`<button type='button' class='tool-output-toggle tool-group-toggle' ` +
							`onclick="toggleToolGroup('${itemId}');" ` +
							`title='${this.templates.escapeHtml(toggleTitle)}' aria-expanded='false'>` +
							`<span class='tool-output-label'>${this.templates.escapeHtml(toolLabel)}:&nbsp;</span>` +
							`<span class='tool-output-name'>${callName}</span>${itemArrow}` +
							`</button>` +
							`<div class='tool-group-content' style='display:none'>${renderPair(call)}</div>` +
							`</div>`
						);
					}).join('');
				} else {
					contentHtml = renderPair(toolCalls[0]);
				}
			} else {
				// Legacy/single-turn tool rendering keeps its existing common response
				// section, including incremental ToolOutput.update() behavior.
				const requests = toolCalls
					.map((call) => this._renderToolCode(call.request, requestLabel, call.request_friendly, true))
					.join('');
				const responseDisplay = resultCode ? '' : 'display:none';
				contentHtml =
					`<div class='tool-output-pair'><div class='tool-output-section'>` +
					`<div class='tool-output-data tool-output-request-data'>${requests}</div>` +
					`</div>` +
					`<div class='tool-output-section tool-output-response-section' style='${responseDisplay}'>` +
					`<div class='tool-output-data tool-output-result-data'>${resultCode}</div>` +
					`</div></div>`;
			}

		}

		const legacyToggleHtml = hasToolCalls ? '' :
			`<span class='toggle-cmd-output' onclick='toggleToolOutput(${this.templates.escapeHtml(JSON.stringify(block.id))});' ` +
			`title='${this.templates.escapeHtml(toggleTitle)}' role='button'>` +
			`<img src='${this.templates.esc(expIcon)}' width='25' height='25' valign='middle'>` +
			`</span>`;

		const toolAttrs = hasToolCalls
			? ` id='tool-output-${this.templates.esc(block.id)}' data-tool-names='${toolNamesAttr}' data-tool-keys='${this.templates.escapeHtml(JSON.stringify(toolCalls.map(call => call.call_id || call.request)))}'`
			: '';

		const contentClass = hasToolCalls ? 'tool-output-content' : 'content';

		return (
			`<div class='tool-output'${toolAttrs} style='${wrapperDisplay}'>` +
			`${titleHtml}${legacyToggleHtml}` +
			`<div class='${contentClass}' style='display:none' data-trusted='1'>${contentHtml}</div>` +
			`</div>`
		);
	}

	// ========================================
	// Tools internals
	// ========================================

	// Pretty-print JSON-like tool payloads while preserving non-JSON text.
	_formatToolPayload(value) {
		if (value == null) return '';

		let parsed = value;
		if (typeof value === 'string') {
			const raw = value.trim();
			if (!raw) return '';
			try {
				parsed = JSON.parse(raw);
			} catch (_) {
				return value;
			}
		}

		if (typeof parsed === 'object') {
			try {
				return JSON.stringify(parsed, null, 2);
			} catch (_) {}
		}
		return String(value);
	}

	// Build a fenced JSON Markdown block for tool request/response payloads.
	_toolCodeMarkdown(value) {
		const text = this._formatToolPayload(value);
		if (!text) return '';

		// Use a fence longer than any backtick run contained in the payload so
		// arbitrary JSON string values cannot close the block accidentally.
		let maxTicks = 0;
		const runs = text.match(/`+/g);
		if (runs) runs.forEach(run => { maxTicks = Math.max(maxTicks, run.length); });
		const fence = '`'.repeat(Math.max(3, maxTicks + 1));
		return `${fence}json\n${text}\n${fence}`;
	}

	// Emit a normal Markdown placeholder so the standard renderer creates the
	// same code wrapper/copy UI as code fenced in assistant text, without highlighting.
	_renderToolCode(value, headerLabel = '', friendly = null, showToggle = false) {
		const rawMd = this._toolCodeMarkdown(value);
		if (!rawMd) return '';
		const esc = text => this.templates.escapeHtml(String(text));
		const placeholder = (md, label, toggle = false) =>
			`<div class='tool-output-markdown' md-block-markdown='1' data-tool-code='1' data-tool-toggle='${toggle ? '1' : '0'}' data-code-header='${esc(label)}'>${esc(md)}</div>`;
		if (!Array.isArray(friendly) || !friendly.length) return placeholder(rawMd, headerLabel, showToggle);
		const readable = friendly.map((part, index) => {
			const text = String(part.text == null ? '' : part.text);
			const runs = text.match(/`+/g) || [];
			const fence = '`'.repeat(Math.max(3, ...runs.map(run => run.length + 1)));
			return placeholder(`${fence}${part.language || 'text'}\n${text}\n${fence}`, part.label || headerLabel, showToggle && index === 0);
		}).join('');
		return `<div class='tool-payload' data-tool-raw='${esc(this._formatToolPayload(value))}'>` +
			`<div class='tool-view-raw'>${placeholder(rawMd, headerLabel, showToggle)}</div>` +
			`<div class='tool-view-friendly'>${readable}</div></div>`;
	}

}

// One preference for all tool blocks in this WebView, retained across reloads.
if (typeof window !== 'undefined' && typeof document !== 'undefined') {
	window.applyToolPayloadView = (mode, button = null) => {
		const mutate = () => {
			document.documentElement.dataset.toolView = mode;
			try { sessionStorage.setItem('pygpt.toolView', mode); } catch (_) {}
			document.querySelectorAll('.code-header-tool-view').forEach(control => {
				control.setAttribute('aria-pressed', String(mode === 'raw'));
				control.title = mode === 'raw'
					? Utils.g('LOCALE_TOOL_VIEW_PLAIN', 'Plain text')
					: Utils.g('LOCALE_TOOL_VIEW_RAW', 'Raw JSON');
				control.setAttribute('aria-label', control.title);
			});
		};
		if (document.documentElement.dataset.toolView === mode) { mutate(); return; }
		// Both variants change visibility, so anchor their shared, persistent input
		// container rather than the clicked button, which is about to be hidden.
		let anchor = button && button.closest('.tool-output-request-data');
		if (!anchor) {
			anchor = Array.from(document.querySelectorAll('.tool-output-request-data')).find(el => {
				const rect = el.getBoundingClientRect();
				return rect.height > 0 && rect.bottom > 0 && rect.top < window.innerHeight;
			});
		}
		if (typeof runtime !== 'undefined' && runtime.toolOutput) {
			runtime.toolOutput._withViewportAnchor(anchor, mutate);
		} else mutate();
	};
	window.toggleToolPayloadView = button => {
		const mode = document.documentElement.dataset.toolView === 'raw' ? 'friendly' : 'raw';
		window.applyToolPayloadView(mode, button);
		if (window.toolPayloadBridge && window.toolPayloadBridge.set_tool_view) window.toolPayloadBridge.set_tool_view(mode);
	};
	try { document.documentElement.dataset.toolView = sessionStorage.getItem('pygpt.toolView') || 'friendly'; }
	catch (_) { document.documentElement.dataset.toolView = 'friendly'; }
}
