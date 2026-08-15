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
				const bn = this._esc(it.basename || '');
				if (it.is_video) {
					const src = (it.ext === '.webm' || !it.webm_path) ? path : this._esc(it.webm_path);
					const ext = (src.endsWith('.webm') ? 'webm' : (path.split('.').pop() || 'mp4'));
					parts.push(
						`<div class="extra-src-video-box" title="${url}">` +
						`<video class="video-player" controls>` +
						`<source src="${src}" type="video/${ext}">` +
						`</video>` +
						`<p><a href="bridge://play_video/${url}" class="title">${this._escapeHtml(bn)}</a></p>` +
						`</div>`
					);
				} else {
					parts.push(
						`<div class="extra-src-img-box" title="${url}">` +
						`<div class="img-outer"><div class="img-wrapper"><a href="bridge://open_image/${path}"><img src="${path}" class="image"></a></div>` +
						`<a href="${url}" class="title">${this._escapeHtml(bn)}</a></div>` +
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
				const path = this._esc(it.path);
				const icon = (typeof window !== 'undefined' && window.ICON_ATTACHMENTS) ? `<img src="${window.ICON_ATTACHMENTS}" class="extra-src-icon">` : '';
				rows.push(`${icon} <b> [${k}] </b> <a href="${url}">${path}</a>`);
			});
			if (rows.length) parts.push(`<div>${rows.join("<br/>")}</div>`);
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
			if (rows.length) parts.push(`<div>${rows.join("<br/>")}</div>`);
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

		// Backward-compatible HTML-ready result. New blocks also carry the raw
		// result so it can be escaped here instead of being injected as HTML.
		const legacyToolOutput = (extra.tool_output != null) ? String(extra.tool_output) : '';
		const resultHtml = (extra.tool_result != null)
			? this._escapeHtml(String(extra.tool_result))
			: legacyToolOutput;

		// A tool request itself makes the wrapper visible immediately. The result
		// can arrive later through ToolOutput.update().
		const wrapperDisplay = (extra.tool_output_visible === true || hasToolCalls) ? '' : 'display:none';

		const toggleTitle = (typeof trans !== 'undefined' && trans) ? trans('action.cmd.expand') : 'Expand';
		const expIcon = (typeof window !== 'undefined' && window.ICON_EXPAND) ? window.ICON_EXPAND : '';
		const toolIcon = (typeof window !== 'undefined' && window.ICON_TOOL) ? window.ICON_TOOL : '';
		const toolLabel = (typeof window !== 'undefined' && window.LOCALE_TOOL) ? window.LOCALE_TOOL : 'Tool';
		const requestLabel = (typeof window !== 'undefined' && window.LOCALE_TOOL_REQUEST) ? window.LOCALE_TOOL_REQUEST : 'Request';
		const responseLabel = (typeof window !== 'undefined' && window.LOCALE_TOOL_RESPONSE) ? window.LOCALE_TOOL_RESPONSE : 'Response';

		let titleHtml = '';
		let contentHtml = legacyToolOutput;
		if (hasToolCalls) {
			const names = toolCalls.map((call) => this._escapeHtml(String(call.name || 'tool')));
			const requests = toolCalls
				.map((call) => this._escapeHtml(String(call.request || '')))
				.join('\n\n');

			const iconHtml = toolIcon ? `<img src='${this._esc(toolIcon)}' class='tool-output-icon' alt=''>` : '';
			const arrowHtml = `<img src='${this._esc(expIcon)}' class='tool-output-arrow' width='25' height='25' alt=''>`;
			titleHtml =
				`<button type='button' class='tool-output-toggle' onclick='toggleToolOutput(${this._esc(block.id)});' ` +
				`title='${this._escapeHtml(toggleTitle)}' aria-expanded='false'>` +
				`${iconHtml}<span class='tool-output-label'><b>${this._escapeHtml(toolLabel)}:</b>&nbsp;</span>` +
				`<span class='tool-output-name'>${names.join(', ')}</span>${arrowHtml}` +
				`</button>`;
			contentHtml =
				`<div class='tool-output-section'>` +
				`<b>${this._escapeHtml(requestLabel)}:</b>` +
				`<div class='tool-output-data tool-output-request-data'>${requests}</div>` +
				`</div>` +
				`<div class='tool-output-section'>` +
				`<b>${this._escapeHtml(responseLabel)}:</b>` +
				`<div class='tool-output-data tool-output-result-data'>${resultHtml}</div>` +
				`</div>`;
		}

		const legacyToggleHtml = hasToolCalls ? '' :
			`<span class='toggle-cmd-output' onclick='toggleToolOutput(${this._esc(block.id)});' ` +
			`title='${this._escapeHtml(toggleTitle)}' role='button'>` +
			`<img src='${this._esc(expIcon)}' width='25' height='25' valign='middle'>` +
			`</span>`;

		return (
			`<div class='tool-output' style='${wrapperDisplay}'>` +
			`${titleHtml}${legacyToggleHtml}` +
			`<div class='content' style='display:none' data-trusted='1'>${contentHtml}</div>` +
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

		return (
			`<div class='msg-box msg-bot' id='${msgId}'>` +
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