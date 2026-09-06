// ==========================================================================
// Template engine for JSON nodes
// ==========================================================================

class NodeTemplateEngine {

	// JS-side templates for nodes rendered from JSON payload (RenderBlock).
	constructor(cfg, logger) {
		this.cfg = cfg || {};
		this.logger = logger || {
			debug: () => {}
		};
	}

	// Escapes a string for safe HTML rendering.
	_esc(s) {
		return (s == null) ? '' : String(s);
	}

	// Escapes a string for safe HTML rendering.
	_escapeHtml(s) {
		return (typeof Utils !== 'undefined') ? Utils.escapeHtml(s) : String(s).replace(/[&<>"']/g, m => ({
			'&': '&amp;',
			'<': '&lt;',
			'>': '&gt;',
			'"': '&quot;',
			"'": '&#039;'
		} [m]));
	}

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
	// same code wrapper/highlighting/copy UI as code fenced in assistant text.
	_renderToolCode(value) {
		const md = this._toolCodeMarkdown(value);
		if (!md) return '';
		return `<div class='tool-output-markdown' md-block-markdown='1'>${this._escapeHtml(md)}</div>`;
	}

	// Render name header given role
	_nameHeader(role, name, avatarUrl) {
		if (!name && !avatarUrl) return '';
		const cls = (role === 'user') ? 'name-user' : 'name-bot';
		const img = avatarUrl ? `<img src="${this._esc(avatarUrl)}" class="avatar"> ` : '';
		return `<div class="name-header ${cls}">${img}${this._esc(name || '')}</div>`;
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

		const content = this._escapeHtml(inp.text || '').replace(/\r?\n/g, '<br>');

		// Use existing copy icon and locale strings to keep public API stable.
		const I = (this.cfg && this.cfg.ICONS) || {};
		const L = (this.cfg && this.cfg.LOCALE) || {};
		const copyIcon = I.CODE_COPY || '';
		const copyTitle = L.COPY || 'Copy';

		// Single icon, no label; positioned via CSS; visible on hover.
		const copyBtn = `<a href="empty:${this._esc(id)}" class="msg-copy-btn" data-id="${this._esc(id)}" data-tip="${this._escapeHtml(copyTitle)}" title="${this._escapeHtml(copyTitle)}" aria-label="${this._escapeHtml(copyTitle)}" role="button"><img src="${this._esc(copyIcon)}" class="copy-img" alt="${this._escapeHtml(copyTitle)}" data-id="${this._esc(id)}"></a>`;

		return `<div class="msg-box msg-user" id="${msgId}">${nameHeader}<div class="msg">${copyBtn}<p style="margin:0">${content}</p></div></div>`;
	}

	// Render a list of file/URL rows with an optional collapsed tail.
	_renderCollapsibleExtraRows(rows) {
		if (!Array.isArray(rows) || !rows.length) return '';

		let limit = 5;
		try {
			const configured = Number((typeof window !== 'undefined') ? window.EXTRA_ITEMS_VISIBLE_LIMIT : limit);
			if (Number.isFinite(configured)) limit = Math.floor(configured);
		} catch (_) {}

		if (limit <= 0 || rows.length <= limit) {
			return `<div class="extra-items-list">${rows.join("<br/>")}</div>`;
		}

		const visible = rows.slice(0, limit).join("<br/>");
		const hidden = rows.slice(limit).join("<br/>");
		const remaining = rows.length - limit;
		const labelTpl = (typeof window !== 'undefined' && window.LOCALE_MORE_ITEMS)
			? String(window.LOCALE_MORE_ITEMS)
			: '+ {count} more items';
		const label = labelTpl.split('{count}').join(String(remaining));
		const expandTitle = (typeof window !== 'undefined' && window.LOCALE_EXPAND)
			? String(window.LOCALE_EXPAND)
			: 'Expand';
		const expIcon = (typeof window !== 'undefined' && window.ICON_EXPAND)
			? String(window.ICON_EXPAND)
			: '';
		const arrow = expIcon
			? `<img src="${this._esc(expIcon)}" class="extra-items-toggle-arrow" alt="">`
			: '';

		return (
			`<div class="extra-items-list">` +
			`<div class="extra-items-visible">${visible}</div>` +
			`<div class="extra-items-hidden" style="display:none">${hidden}</div>` +
			`<button type="button" class="extra-items-toggle" onclick="toggleExtraItems(this);" ` +
			`title="${this._escapeHtml(expandTitle)}" aria-expanded="false">` +
			`<span class="extra-items-toggle-label">${this._escapeHtml(label)}</span>${arrow}` +
			`</button>` +
			`</div>`
		);
	}

	// Render extra blocks (images/files/urls/docs/tool-extra)
	_renderExtras(block) {
		const parts = [];

		// images
		const images = block.images || {};
		const keysI = Object.keys(images);
		if (keysI.length) {
			keysI.forEach((k) => {
				const it = images[k];
				if (!it) return;
				const url = this._esc(it.url);
				const path = this._esc(it.path);
				if (it.is_video) {
					const src = (it.ext === '.webm' || !it.webm_path) ? path : this._esc(it.webm_path);
					const ext = (src.endsWith('.webm') ? 'webm' : (path.split('.').pop() || 'mp4'));
					parts.push(
						`<div class="extra-src-video-box" title="${url}">` +
						`<video class="video-player" controls>` +
						`<source src="${src}" type="video/${ext}">` +
						`</video>` +
						`</div>`
					);
				} else {
					parts.push(
						`<div class="extra-src-img-box" title="${url}">` +
						`<div class="img-outer"><div class="img-wrapper"><a href="bridge://open_image/${path}"><img src="${path}" class="image"></a></div></div>` +
						`</div><br/>`
					);
				}
			});
		}

		// files
		const files = block.files || {};
		const kF = Object.keys(files);
		if (kF.length) {
			const rows = [];
			kF.forEach((k) => {
				const it = files[k];
				if (!it) return;
				const url = this._esc(it.url);
				const name = this._esc(it.basename || it.path || '');
				const icon = (typeof window !== 'undefined' && window.ICON_ATTACHMENTS) ? `<img src="${window.ICON_ATTACHMENTS}" class="extra-src-icon">` : '';
				rows.push(`${icon} <a href="${url}">${this._escapeHtml(name)}</a> <b> [${k}] </b>`);
			});
			if (rows.length) parts.push(this._renderCollapsibleExtraRows(rows));
		}

		// urls
		const urls = block.urls || {};
		const kU = Object.keys(urls);
		if (kU.length) {
			const rows = [];
			kU.forEach((k) => {
				const it = urls[k];
				if (!it) return;
				const url = this._esc(it.url);
				const icon = (typeof window !== 'undefined' && window.ICON_URL) ? `<img src="${window.ICON_URL}" class="extra-src-icon">` : '';
				rows.push(`${icon}<a href="${url}" title="${url}">${url}</a> <small> [${k}] </small>`);
			});
			if (rows.length) parts.push(this._renderCollapsibleExtraRows(rows));
		}

		// docs (render on JS) or fallback to docs_html
		const extra = block.extra || {};
		const docsRaw = Array.isArray(extra.docs) ? extra.docs : null;

		if (docsRaw && docsRaw.length) {
			const icon = (typeof window !== 'undefined' && window.ICON_DB) ? `<img src="${window.ICON_DB}" class="extra-src-icon">` : '';
			const prefix = (typeof window !== 'undefined' && window.LOCALE_DOC_PREFIX) ? String(window.LOCALE_DOC_PREFIX) : 'Doc:';
			const limit = 3;

			// normalize: [{uuid, meta}] OR [{ uuid: {...} }]
			const normalized = [];
			docsRaw.forEach((it) => {
				if (!it || typeof it !== 'object') return;
				if ('uuid' in it && 'meta' in it && typeof it.meta === 'object') {
					normalized.push({
						uuid: String(it.uuid),
						meta: it.meta || {}
					});
				} else {
					const keys = Object.keys(it);
					if (keys.length === 1) {
						const uuid = keys[0];
						const meta = it[uuid];
						if (meta && typeof meta === 'object') {
							normalized.push({
								uuid: String(uuid),
								meta
							});
						}
					}
				}
			});

			const rows = [];
			for (let i = 0; i < Math.min(limit, normalized.length); i++) {
				const d = normalized[i];
				const meta = d.meta || {};
				const entries = Object.keys(meta).map(k => `<b>${this._escapeHtml(k)}:</b> ${this._escapeHtml(String(meta[k]))}`).join(', ');
				rows.push(`<p><small>[${i + 1}] ${this._escapeHtml(d.uuid)}: ${entries}</small></p>`);
			}
			if (rows.length) {
				parts.push(`<p>${icon}<small><b>${this._escapeHtml(prefix)}:</b></small></p>`);
				parts.push(`<div class="cmd"><p>${rows.join('')}</p></div>`);
			}
		} else {
			// backward compat
			const docs_html = extra && extra.docs_html ? String(extra.docs_html) : '';
			if (docs_html) parts.push(docs_html);
		}

		// plugin-driven tool extra HTML
		const tool_extra_html = extra && extra.tool_extra_html ? String(extra.tool_extra_html) : '';
		if (tool_extra_html) parts.push(`<div class="msg-extra">${tool_extra_html}</div>`);

		return parts.join('');
	}

	// Render message-level actions
	_renderActions(block) {
		const extra = block.extra || {};
		const actions = extra.actions || [];
		if (!actions || !actions.length) return '';
		const parts = actions.map((a) => {
			const href = this._esc(a.href || '#');
			const title = this._esc(a.title || '');
			const icon = this._esc(a.icon || '');
			const id = this._esc(a.id || block.id);
			return `<a href="${href}" class="action-icon" data-id="${id}" role="button"><span class="cmd"><img src="${icon}" class="action-img" title="${title}" alt="${title}" data-id="${id}"></span></a>`;
		});
		return `<div class="action-icons" data-id="${this._esc(block.id)}">${parts.join('')}</div>`;
	}

	// Render tool output wrapper (always collapsed by default; wrapper visibility depends on flag)
	// Inside class NodeTemplateEngine
	_renderToolOutputWrapper(block) {
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
		const requestLabel = (typeof window !== 'undefined' && window.LOCALE_TOOL_REQUEST) ? window.LOCALE_TOOL_REQUEST : 'Request';
		const responseLabel = (typeof window !== 'undefined' && window.LOCALE_TOOL_RESPONSE) ? window.LOCALE_TOOL_RESPONSE : 'Response';

		let titleHtml = '';
		let contentHtml = legacyToolOutput;
		let toolNamesAttr = '';
		if (hasToolCalls) {
			const rawNames = toolCalls.map((call) => String(call.name || 'tool'));
			const hasPerCallResponses = toolCalls.some((call) =>
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
			const names = displayNames.map((name) => this._escapeHtml(name));
			toolNamesAttr = this._escapeHtml(JSON.stringify(rawNames));
			const resultCode = this._renderToolCode(toolResult);

			const arrowHtml = `<img src='${this._esc(expIcon)}' class='tool-output-arrow' width='25' height='25' alt=''>`;
			const titleLabel = groupedInMessage && typeof window !== 'undefined' && window.LOCALE_TOOLS
				? String(window.LOCALE_TOOLS)
				: toolLabel;
			titleHtml =
				`<button type='button' class='tool-output-toggle' onclick='toggleToolOutput(${this._esc(block.id)});' ` +
				`title='${this._escapeHtml(toggleTitle)}' aria-expanded='false'>` +
				`<span class='tool-output-label'><b>${this._escapeHtml(titleLabel)}:</b>&nbsp;</span>` +
				`<span class='tool-output-name'>${names.join(', ')}</span>${arrowHtml}` +
				`</button>`;

			if (hasPerCallResponses) {
				const renderPair = (call) => {
					const requestCode = this._renderToolCode(call && call.request);
					const hasResponse = !!call && Object.prototype.hasOwnProperty.call(call, 'response');
					const responseCode = hasResponse ? this._renderToolCode(call.response) : '';
					const responseDisplay = hasResponse ? '' : 'display:none';
					return (
						`<div class='tool-output-pair'>` +
						`<div class='tool-output-section'>` +
						`<div class='tool-output-header'>${this._escapeHtml(requestLabel)}</div>` +
						`<div class='tool-output-data tool-output-request-data'>${requestCode}</div>` +
						`</div>` +
						`<div class='tool-output-section tool-output-response-section' style='${responseDisplay}'>` +
						`<div class='tool-output-header'>${this._escapeHtml(responseLabel)}</div>` +
						`<div class='tool-output-data tool-output-result-data'>${responseCode}</div>` +
						`</div>` +
						`</div>`
					);
				};

				if (groupedInMessage) {
					contentHtml = toolCalls.map((call, index) => {
						const callName = this._escapeHtml(String((call && call.name) || 'tool'));
						const itemId = `tool-call-${this._esc(block.id)}-${index}`;
						const itemArrow = `<img src='${this._esc(expIcon)}' class='tool-output-arrow tool-group-arrow' width='25' height='25' alt=''>`;
						return (
							`<div class='tool-output-group tool-output-item' id='${itemId}'>` +
							`<button type='button' class='tool-output-toggle tool-group-toggle' ` +
							`onclick="toggleToolGroup('${itemId}');" ` +
							`title='${this._escapeHtml(toggleTitle)}' aria-expanded='false'>` +
							`<span class='tool-output-label'><b>${this._escapeHtml(toolLabel)}:</b>&nbsp;</span>` +
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
					.map((call) => this._renderToolCode(call.request))
					.join('');
				const responseDisplay = resultCode ? '' : 'display:none';
				contentHtml =
					`<div class='tool-output-section'>` +
					`<div class='tool-output-header'>${this._escapeHtml(requestLabel)}</div>` +
					`<div class='tool-output-data tool-output-request-data'>${requests}</div>` +
					`</div>` +
					`<div class='tool-output-section tool-output-response-section' style='${responseDisplay}'>` +
					`<div class='tool-output-header'>${this._escapeHtml(responseLabel)}</div>` +
					`<div class='tool-output-data tool-output-result-data'>${resultCode}</div>` +
					`</div>`;
			}

		}

		const legacyToggleHtml = hasToolCalls ? '' :
			`<span class='toggle-cmd-output' onclick='toggleToolOutput(${this._esc(block.id)});' ` +
			`title='${this._escapeHtml(toggleTitle)}' role='button'>` +
			`<img src='${this._esc(expIcon)}' width='25' height='25' valign='middle'>` +
			`</span>`;

		const toolAttrs = hasToolCalls
			? ` id='tool-output-${this._esc(block.id)}' data-tool-names='${toolNamesAttr}'`
			: '';

		const contentClass = hasToolCalls ? 'tool-output-content' : 'content';

		return (
			`<div class='tool-output'${toolAttrs} style='${wrapperDisplay}'>` +
			`${titleHtml}${legacyToggleHtml}` +
			`<div class='${contentClass}' style='display:none' data-trusted='1'>${contentHtml}</div>` +
			`</div>`
		);
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

		const mdText = this._escapeHtml(out.text || '');
		const mdBlock = mdText ? `<div class='md-block' md-block-markdown='1'>${mdText}</div>` : '';
		const toolWrap = this._renderToolOutputWrapper(block);
		const extras = this._renderExtras(block);
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
			`${mdBlock}` +
			`<div class='msg-tool-extra'></div>` +
			`${toolWrap}` +
			`<div class='msg-extra'>${extras}</div>` +
			`${actions}${debug}` +
			`</div>` +
			`</div>`
		);
	}

	// Render one RenderBlock into HTML (may produce 1 or 2 messages – input and/or output)
	renderNode(block) {
		const parts = [];
		if (block && block.input && block.input.text) parts.push(this._renderUser(block));
		if (block && block.output) {
			const extra = block.extra || {};
			const hasToolCalls = Array.isArray(extra.tool_calls) && extra.tool_calls.length > 0;
			if (block.output.text || hasToolCalls || extra.tool_output_visible === true) {
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
}