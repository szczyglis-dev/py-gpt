// Message templates compose tool, artifact and workflow templates.
class NodeTemplateEngine {

	// ========================================
	// Composition
	// ========================================

	// JS-side templates for nodes rendered from JSON payload (RenderBlock).
	constructor(cfg, logger) {
		this.cfg = cfg || {};
		this.logger = logger || {
			debug: () => {}
		};
		this.tools = new NodeToolsTemplate(this);
		this.artifacts = new NodeArtifactsTemplate(this);
		this.timeline = new NodeTimelineTemplate(this);

	}

	// ========================================
	// Messages and shared escaping
	// ========================================

	// Escapes a string for safe HTML rendering.
	esc(s) {
		return (s == null) ? '' : String(s);
	}

	// Escapes a string for safe HTML rendering.
	escapeHtml(s) {
		return (typeof Utils !== 'undefined') ? Utils.escapeHtml(s) : String(s).replace(/[&<>"']/g, m => ({
			'&': '&amp;',
			'<': '&lt;',
			'>': '&gt;',
			'"': '&quot;',
			"'": '&#039;'
		} [m]));
	}

	// Render one RenderBlock into HTML (may produce 1 or 2 messages – input and/or output)
	renderNode(block) {
		const parts = [];
		if (block && block.input && block.input.text) parts.push(this._renderUser(block));
		if (block && block.output) {
			const extra = block.extra || {};
			const hasToolCalls = Array.isArray(extra.tool_calls) && extra.tool_calls.length > 0;
			const hasTimeline = Array.isArray(extra.partial_timeline) && extra.partial_timeline.length > 0;
			const hasCollapsedWorkflow = !!(extra.collapsed_workflow
				&& Array.isArray(extra.collapsed_workflow.timeline)
				&& extra.collapsed_workflow.timeline.length > 0);
			if (block.output.text || hasToolCalls || hasTimeline || hasCollapsedWorkflow || extra.tool_output_visible === true) {
				parts.push(this._renderBot(block));
			}
		}
		return parts.join('');
	}

	// Render array of blocks
	renderNodes(blocks) {
		if (!Array.isArray(blocks)) return '';
		const out = [];
		for (let i = 0; i < blocks.length; i++) {
			const b = blocks[i] || null;
			if (!b) continue;
			out.push(this.renderNode(b));
		}
		return out.join('');
	}

	// ========================================
	// Messages and shared escaping internals
	// ========================================

	// Render name header given role
	_nameHeader(role, name, avatarUrl) {
		if (!name && !avatarUrl) return '';
		const cls = (role === 'user') ? 'name-user' : 'name-bot';
		const img = avatarUrl ? `<img src="${this.esc(avatarUrl)}" class="avatar"> ` : '';
		return `<div class="name-header ${cls}">${img}${this.esc(name || '')}</div>`;
	}

	// Render user message block
	_renderUser(block) {
		const id = block.id;
		const inp = block.input || {};
		const msgId = `msg-user-${id}`;

		// NOTE: timestamps intentionally disabled on frontend
		// let ts = '';
		// if (inp.timestamp) { ... }

		const personalize = !!(block && block.extra && block.extra.personalize === true);
		const nameHeader = personalize ? this._nameHeader('user', inp.name || '', inp.avatar_img || null) : '';
		const dateLabel = inp.date_label
			? `<div class="msg-date-separator">${this.escapeHtml(inp.date_label)}</div>`
			: '';

		const content = (typeof Utils !== 'undefined' && Utils.renderMentionText) ? Utils.renderMentionText(inp.text || '') : this.escapeHtml(inp.text || '').replace(/\r?\n/g, '<br>');

		// Use existing copy icon and locale strings to keep public API stable.
		const I = (this.cfg && this.cfg.ICONS) || {};
		const L = (this.cfg && this.cfg.LOCALE) || {};
		const copyIcon = I.CODE_COPY || '';
		const copyTitle = L.COPY || 'Copy';

		// Single icon, no label; positioned via CSS; visible on hover.
		const copyBtn = `<a href="empty:${this.esc(id)}" class="msg-copy-btn" data-id="${this.esc(id)}" data-tip="${this.escapeHtml(copyTitle)}" title="${this.escapeHtml(copyTitle)}" aria-label="${this.escapeHtml(copyTitle)}" role="button"><img src="${this.esc(copyIcon)}" class="copy-img" alt="${this.escapeHtml(copyTitle)}" data-id="${this.esc(id)}"></a>`;

		return `${dateLabel}<div class="msg-box msg-user" id="${msgId}">${nameHeader}<div class="msg">${copyBtn}<p style="margin:0">${content}</p></div></div>`;
	}

	// Render message-level actions
	_renderActions(block) {
		const extra = block.extra || {};
		const actions = extra.actions || [];
		if (!actions || !actions.length) return '';
		const parts = actions.map((a) => {
			const href = this.esc(a.href || '#');
			const title = this.esc(a.title || '');
			const icon = this.esc(a.icon || '');
			const id = this.esc(a.id || block.id);
			return `<a href="${href}" class="action-icon" data-id="${id}" role="button"><span class="cmd"><img src="${icon}" class="action-img" title="${title}" alt="${title}" data-id="${id}"></span></a>`;
		});
		return `<div class="action-icons" data-id="${this.esc(block.id)}">${parts.join('')}</div>`;
	}

	// Render bot message block (md-block-markdown)
	_renderBot(block) {
		const id = block.id;
		const out = block.output || {};
		const msgId = `msg-bot-${id}`;

		// timestamps intentionally disabled on frontend
		// let ts = '';
		// if (out.timestamp) { ... }

		const personalize = !!(block && block.extra && block.extra.personalize === true);
		const nameHeader = personalize ? this._nameHeader('bot', out.name || '', out.avatar_img || null) : '';

		const mdText = this.escapeHtml(out.text || '');
		const timelineHtml = this.timeline.renderPartialTimeline(block);
		const agentName = String(out.agent_name_prefix || '').trim();
		const agentPrefix = (!timelineHtml && mdText && agentName)
			? `<span class='agent-name-prefix'>${this.escapeHtml(agentName)}</span>`
			: '';
		const mdBlock = timelineHtml ? '' : (mdText ? `${agentPrefix}<div class='md-block' md-block-markdown='1'>${mdText}</div>` : '');
		const collapsedWorkflowHtml = timelineHtml ? '' : this.timeline.renderCollapsedWorkflow(block);
		const primaryHtml = timelineHtml || `${collapsedWorkflowHtml}${mdBlock}`;
		const toolWrap = timelineHtml ? '' : this.tools.renderToolOutputWrapper(block);
		const extras = this.artifacts.renderExtras(block);
		const actions = (block.extra && block.extra.footer_icons) ? this._renderActions(block) : '';
		const debug = (block.extra && block.extra.debug_html) ? String(block.extra.debug_html) : '';
		const toolCalls = Array.isArray(block.extra && block.extra.tool_calls)
			? block.extra.tool_calls.filter(Boolean)
			: [];
		const hasToolCalls = toolCalls.length > 0;
		// A tool-chain item may still carry invisible/auxiliary extras (tool_extra_html,
		// files, actions, debug wrappers, etc.).  Those must not prevent grouping.
		// The decisive condition is that after stripping the tool call there is no
		// normal assistant text.  Keep the continuation marker on every tool-call
		// message so the DOM grouping pass can use the exact persisted chain edge.
		const toolOnly = hasToolCalls && !mdText;
		const chainContinuation = !!(block.extra && block.extra.tool_chain_continuation === true);
		const toolChainAttrs = hasToolCalls
			? ` data-tool-only='${toolOnly ? '1' : '0'}' data-tool-chain-continuation='${chainContinuation ? '1' : '0'}'`
			: '';

		return (
			`<div class='msg-box msg-bot' id='${msgId}'${toolChainAttrs}>` +
			`${nameHeader}` +
			`<div class='msg'>` +
			`<div class='msg-timeline'>${primaryHtml}${toolWrap}</div>` +
			`<div class='msg-tool-extra'></div>` +
			`<div class='msg-extra'>${extras}</div>` +
			`${actions}${debug}` +
			`</div>` +
			`</div>`
		);
	}

}
