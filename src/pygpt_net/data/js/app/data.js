// ==========================================================================
// Data receiver for append/replace nodes
// ==========================================================================

class DataReceiver {

	// Normalizes payload (HTML string or JSON) and delegates to NodesManager.
	constructor(cfg, templates, nodes, scrollMgr) {
		this.cfg = cfg || {};
		this.templates = templates;
		this.nodes = nodes;
		this.scrollMgr = scrollMgr;
	}

	// Tries to parse a JSON string.
	_tryParseJSON(s) {
		if (typeof s !== 'string') return s;
		const t = s.trim();
		if (!t) return null;
		// If it's like HTML, don't parse as JSON
		if (t[0] === '<') return null;
		try {
			return JSON.parse(t);
		} catch (_) {
			return null;
		}
	}

	// Normalizes the input object to an array of block nodes.
	_normalizeToBlocks(obj) {
		if (!obj) return [];
		if (Array.isArray(obj)) return obj;
		if (obj.node) return [obj.node];
		if (obj.nodes) return (Array.isArray(obj.nodes) ? obj.nodes : []);
		// single node-like object
		if (typeof obj === 'object' && (obj.input || obj.output || obj.id)) return [obj];
		return [];
	}

	// Appends a new payload to the nodes.
	append(payload) {
		// Legacy HTML string?
		if (typeof payload === 'string' && payload.trim().startsWith('<')) {
			this.nodes.appendNode(payload, this.scrollMgr);
			return;
		}
		// Try JSON
		const obj = this._tryParseJSON(payload);
		if (!obj) {
			// Not JSON – pass through
			this.nodes.appendNode(String(payload), this.scrollMgr);
			return;
		}
		const blocks = this._normalizeToBlocks(obj);
		if (!blocks.length) {
			this.nodes.appendNode('', this.scrollMgr);
			return;
		}
		const html = this.templates.renderNodes(blocks);
		this.nodes.appendNode(html, this.scrollMgr);
	}

	// Replaces the current nodes with a new payload.
	replace(payload) {
		// Legacy HTML string?
		if (typeof payload === 'string' && payload.trim().startsWith('<')) {
			this.nodes.replaceNodes(payload, this.scrollMgr);
			return;
		}
		// Try JSON
		const obj = this._tryParseJSON(payload);
		if (!obj) {
			this.nodes.replaceNodes(String(payload), this.scrollMgr);
			return;
		}
		const blocks = this._normalizeToBlocks(obj);
		if (!blocks.length) {
			this.nodes.replaceNodes('', this.scrollMgr);
			return;
		}
		const html = this.templates.renderNodes(blocks);
		this.nodes.replaceNodes(html, this.scrollMgr);
	}
}