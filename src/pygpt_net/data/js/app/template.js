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
			if (rows.length) parts.push(`<div>${rows.join("<br/><br/>")}</div>`);
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
			if (rows.length) parts.push(`<div>${rows.join("<br/><br/>")}</div>`);
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

		// IMPORTANT: keep initial tool output verbatim (HTML-ready).
		// Do NOT HTML-escape here – the host already provides a safe/HTML-ready string.
		// Escaping again would double-encode entities (e.g. " -> "), which
		// caused visible """ in the UI instead of quotes.
		const tool_output_html = (extra.tool_output != null) ? String(extra.tool_output) : '';

		// Wrapper visibility: show/hide based on tool_output_visible...
		const wrapperDisplay = (extra.tool_output_visible === true) ? '' : 'display:none';

		const toggleTitle = (typeof trans !== 'undefined' && trans) ? trans('action.cmd.expand') : 'Expand';
		const expIcon = (typeof window !== 'undefined' && window.ICON_EXPAND) ? window.ICON_EXPAND : '';

		return (
			`<div class='tool-output' style='${wrapperDisplay}'>` +
			`<span class='toggle-cmd-output' onclick='toggleToolOutput(${this._esc(block.id)});' ` +
			`title='${this._escapeHtml(toggleTitle)}' role='button'>` +
			`<img src='${this._esc(expIcon)}' width='25' height='25' valign='middle'>` +
			`</span>` +
			// Content is initially collapsed. We intentionally do NOT escape here,
			// to keep behavior consistent with ToolOutput.append/update (HTML-in).
			`<div class='content' style='display:none' data-trusted='1'>${tool_output_html}</div>` +
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
		const toolWrap = this._renderToolOutputWrapper(block);
		const extras = this._renderExtras(block);
		const actions = (block.extra && block.extra.footer_icons) ? this._renderActions(block) : '';
		const debug = (block.extra && block.extra.debug_html) ? String(block.extra.debug_html) : '';

		return (
			`<div class='msg-box msg-bot' id='${msgId}'>` +
			`${nameHeader}` +
			`<div class='msg'>` +
			`<div class='md-block' md-block-markdown='1'>${mdText}</div>` +
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
		if (block && block.output && block.output.text) parts.push(this._renderBot(block));
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