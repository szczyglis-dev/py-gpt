// NodeTimelineTemplate owns timeline behavior and state.
class NodeTimelineTemplate {

	// ========================================
	// Composition
	// ========================================

	constructor(templates) {
		this.templates = templates;
	}

	// ========================================
	// Timeline
	// ========================================

	// Render chronological sub-items inside one durable assistant turn.
	renderPartialTimeline(block) {
		const extra = block.extra || {};
		const timeline = Array.isArray(extra.partial_timeline) ? extra.partial_timeline.filter(Boolean) : [];
		return this._renderTimelineSegments(block, timeline);
	}

	// Render the completed Agents v2 workflow as a tool-style accordion while
	// leaving the authoritative final response visible as the normal message body.
	renderCollapsedWorkflow(block) {
		const extra = block.extra || {};
		const workflow = extra.collapsed_workflow || null;
		const timeline = workflow && Array.isArray(workflow.timeline)
			? workflow.timeline.filter(Boolean)
			: [];
		if (!timeline.length) return '';

		const contentHtml = this._renderTimelineSegments(block, timeline);
		if (!contentHtml) return '';
		const expanded = workflow.expanded === true;
		const label = this.templates.escapeHtml(String(workflow.label || ''));
		const expIcon = (typeof window !== 'undefined' && window.ICON_EXPAND) ? window.ICON_EXPAND : '';
		const toggleTitle = (typeof window !== 'undefined' && window.LOCALE_EXPAND)
			? String(window.LOCALE_EXPAND)
			: 'Expand';
		const id = this.templates.esc(block.id);
		const arrowHtml = `<img src='${this.templates.esc(expIcon)}' class='tool-output-arrow agent-workflow-arrow${expanded ? ' toggle-expanded' : ''}' width='25' height='25' alt=''>`;

		return (
			`<div class='tool-output agent-workflow-output' id='tool-output-${id}'>` +
			`<button type='button' class='tool-output-toggle agent-workflow-toggle' ` +
			`onclick='toggleToolOutput(${id});' title='${this.templates.escapeHtml(toggleTitle)}' aria-expanded='${expanded}'>` +
			`<span class='tool-output-label agent-workflow-label'>${label}</span>${arrowHtml}` +
			`</button>` +
			`<div class='tool-output-content agent-workflow-content${expanded ? ' is-expanded' : ''}' ${expanded ? '' : "style='display:none'"} data-trusted='1'><div class='tool-collapse-inner'><div class='tool-collapse-body'>${contentHtml}</div></div></div>` +
			`</div>`
		);
	}

	// ========================================
	// Timeline internals
	// ========================================

	_renderTimelineSegments(block, timeline) {
		if (!Array.isArray(timeline) || !timeline.length) return '';

		const parts = [];
		for (let i = 0; i < timeline.length; i++) {
			const segment = timeline[i] || {};

			// Runtime-only workflow/status rows are rendered in the same timeline
			// as text and tools, before message extras/actions. They survive RELOAD
			// through Python renderer state but are intentionally not persisted in DB.
			const statusId = String(segment.status_id || '');
			const statusKind = String(segment.status_kind || '');
			if (statusId || statusKind) {
				let label = String(segment.status_text || '');
				const toolNames = Array.isArray(segment.status_tool_names)
					? segment.status_tool_names.filter(Boolean).map(v => String(v))
					: [];
				if (!label && statusKind === 'tool' && toolNames.length) {
					const prefix = toolNames.length > 1
						? ((typeof window !== 'undefined' && window.LOCALE_TOOLS) ? String(window.LOCALE_TOOLS) : 'Tools')
						: ((typeof window !== 'undefined' && window.LOCALE_TOOL) ? String(window.LOCALE_TOOL) : 'Tool');
					label = `${prefix}: ${toolNames.join(', ')}...`;
				}
				if (label) {
					const liveCalls = Array.isArray(segment.status_live_tool_calls) ? segment.status_live_tool_calls : [];
					let liveHtml = '';
					if (statusKind === 'tool' && liveCalls.length) {
						liveHtml = this.templates.tools.renderToolOutputWrapper({id: `live-${block.id}`, extra: {tool_calls: liveCalls, tool_output_visible: true}})
							.replace("class='tool-output'", "class='tool-output tool-output-live' data-live-tools='1'");
					}
					const activeClass = segment.status_active ? ' agents-v2-status--active' : '';
					const sid = this.templates.escapeHtml(statusId);
					const skind = this.templates.escapeHtml(statusKind || 'agent');
					parts.push(
						`<div class='msg-part msg-part-status' data-status-part='1'>` +
						(segment.agent_name_prefix ? `<span class='agent-name-prefix'>${this.templates.escapeHtml(segment.agent_name_prefix)}</span>` : '') +
						`<div class='agents-v2-status workflow-status${segment.status_hierarchy ? ' workflow-status-progress' : ''}${activeClass}${liveHtml ? ' live-tool-status' : ''}' ` +
						`data-workflow-status-id='${sid}' data-status-kind='${skind}'>` +
						(segment.status_hierarchy ? this.templates.tools.renderProgress(label, segment.status_hierarchy, statusId) : `<span class='agents-v2-status__text'>${this.templates.escapeHtml(label)}</span>${liveHtml}`) +
						`</div></div>`
					);
				}
				continue;
			}

			if (segment.inline_message === true) {
				const label = this.templates.escapeHtml(String(segment.inline_message_label || 'Message'));
				const content = this.templates.escapeHtml(String(segment.text || '')).replace(/\r?\n/g, '<br>');
				if (content) {
					const partId = this.templates.esc(segment.part_uuid || segment.part_id || i);
					parts.push(
						`<div class='msg-part msg-part-inline' data-part-id='${partId}'>` +
						`<div class='msg-box msg-user msg-inline'><div class='msg'>` +
						`<p style='margin:0'><strong>${label}:</strong> ${content}</p>` +
						`</div></div></div>`
					);
				}
				continue;
			}

			const mdText = this.templates.escapeHtml(segment.text || '');
			const agentName = String(segment.agent_name_prefix || '').trim();
			const agentPrefix = (agentName && (mdText || (Array.isArray(segment.tool_calls) && segment.tool_calls.length)))
				? `<span class='agent-name-prefix'>${this.templates.escapeHtml(agentName)}</span>`
				: '';
			const mdBlock = mdText ? `<div class='md-block' md-block-markdown='1'>${mdText}</div>` : '';
			const calls = Array.isArray(segment.tool_calls) ? segment.tool_calls.filter(Boolean) : [];
			let toolWrap = '';
			if (calls.length) {
				const toolBlock = {
					id: segment.render_id,
					extra: {
						tool_calls: calls,
						tool_output_visible: true,
						tool_result: '',
						tool_output: ''
					}
				};
				toolWrap = this.templates.tools.renderToolOutputWrapper(toolBlock);
			}
			if (!mdBlock && !toolWrap) continue;
			const partId = this.templates.esc(segment.part_uuid || segment.part_id || i);
			parts.push(`<div class='msg-part' data-part-id='${partId}'>${agentPrefix}${mdBlock}${toolWrap}</div>`);
		}
		return parts.join('');
	}

}
