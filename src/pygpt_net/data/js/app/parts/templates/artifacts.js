// NodeArtifactsTemplate owns artifacts behavior and state.
class NodeArtifactsTemplate {

	// ========================================
	// Composition
	// ========================================

	constructor(templates) {
		this.templates = templates;
	}

	// ========================================
	// Artifacts
	// ========================================

	// Render extra blocks (images/files/urls/docs/tool-extra)
	renderExtras(block) {
		const parts = [];

		// images
		const images = block.images || {};
		const keysI = Object.keys(images);
		if (keysI.length) {
			keysI.forEach((k) => {
				const it = images[k];
				if (!it) return;
				const url = this.templates.esc(it.url);
				const path = this.templates.esc(it.path);
				if (it.is_video) {
					const src = (it.ext === '.webm' || !it.webm_path) ? path : this.templates.esc(it.webm_path);
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
				const url = this.templates.esc(it.url);
				const name = this.templates.esc(it.basename || it.path || '');
				const icon = (typeof window !== 'undefined' && window.ICON_ATTACHMENTS) ? `<img src="${window.ICON_ATTACHMENTS}" class="extra-src-icon">` : '';
				rows.push(`${icon} <a href="${url}">${this.templates.escapeHtml(name)}</a> <b> [${k}] </b>`);
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
				const url = this.templates.esc(it.url);
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
				const entries = Object.keys(meta).map(k => `<b>${this.templates.escapeHtml(k)}:</b> ${this.templates.escapeHtml(String(meta[k]))}`).join(', ');
				rows.push(`<p><small>[${i + 1}] ${this.templates.escapeHtml(d.uuid)}: ${entries}</small></p>`);
			}
			if (rows.length) {
				parts.push(`<p>${icon}<small><b>${this.templates.escapeHtml(prefix)}:</b></small></p>`);
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

	// ========================================
	// Artifacts internals
	// ========================================

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
			? `<img src="${this.templates.esc(expIcon)}" class="extra-items-toggle-arrow" alt="">`
			: '';

		return (
			`<div class="extra-items-list">` +
			`<div class="extra-items-visible">${visible}</div>` +
			`<div class="extra-items-hidden" style="display:none">${hidden}</div>` +
			`<button type="button" class="extra-items-toggle" onclick="toggleExtraItems(this);" ` +
			`title="${this.templates.escapeHtml(expandTitle)}" aria-expanded="false">` +
			`<span class="extra-items-toggle-label">${this.templates.escapeHtml(label)}</span>${arrow}` +
			`</button>` +
			`</div>`
		);
	}

}
