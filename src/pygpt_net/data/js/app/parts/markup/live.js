// CustomMarkupLive owns live behavior and state.
class CustomMarkupLive {

	// ========================================
	// Composition
	// ========================================

	constructor(markup) {
		this.markup = markup;
	}

	// ========================================
	// Live
	// ========================================

    // Apply to stream if the delta text contains any known opener.
	maybeApplyStreamOnDelta(root, deltaText, MD) {
		try {
			this.markup.ensureCompiled();
			if (!this.markup.streamRulesAvailable) return;
			const t = String(deltaText || '');

			// If the delta contains any known stream opener, run full stream pass quickly.
			if (t && this.markup.hasAnyStreamOpenToken(t)) {
				this.markup.debug('cm.stream.delta', { len: t.length, head: t.slice(0, 64) });
				this.applyStream(root, MD);
				return;
			}

			// If there are pending wrappers in the snapshot root and the delta likely carries closers,
			// finalize them immediately (cheap pass limited to pending subtrees).
			if (root && root.querySelector && root.querySelector('[data-cm-pending="1"]')) {
				if (t.indexOf('>') !== -1 || t.indexOf(']') !== -1) {
					this.applyStreamFinalizeClosers(root, this.markup.streamRules);
					this.markup.debug('cm.stream.delta.finalize', {});
				}
			}
		} catch (_) { return; }
	}

    // Apply stream processing to the given subtree
	applyStream(root, MD) {
		this.markup.ensureCompiled();
		if (!this.markup.streamRulesAvailable) return;
		const rules = this.markup.streamRules;
		if (!rules || !rules.length) return;

		this.markup.html.applyRules(root, MD, rules);

		try {
			this.applyStreamPartialOpeners(root, MD, this.markup.streamWrapRules);
		} catch (_) {}

		try {
			this.applyStreamFinalizeClosers(root, rules);
		} catch (_) {}
	}

    // Handle partial openers that lack a closer in the current subtree
	applyStreamPartialOpeners(root, MD, rules) {
		if (!root) return;
		rules = (rules || this.markup.streamWrapRules || []).slice();
		if (!rules.length) return;

		const scope = (root.nodeType === 1 || root.nodeType === 11) ? root : document;
		const self = this;

		const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT, {
			acceptNode(node) {
			 const val = node && node.nodeValue ? node.nodeValue : '';
			 if (!val || !self.hasAnyOpenToken(val, rules)) return NodeFilter.FILTER_SKIP;
			 if (self.isInsideForbiddenContext(node)) return NodeFilter.FILTER_REJECT;
			 return NodeFilter.FILTER_ACCEPT;
			}
		});

		let node;
		while ((node = walker.nextNode())) {
			const text = node.nodeValue || '';
			if (!text) continue;

			let best = null; // { rule, start }
			for (let i = 0; i < rules.length; i++) {
				const r = rules[i];
				if (!r || !r.open || !r.close) continue;

				const idx = text.lastIndexOf(r.open);
				if (idx === -1) continue;

				const after = text.indexOf(r.close, idx + r.open.length);
				if (after !== -1) continue;

				if (!best || idx > best.start) best = { rule: r, start: idx };
			}

			if (!best) continue;

			const r = best.rule;
			const start = best.start;
			const openLen = r.open.length;
			const prefixText = text.slice(0, start);
			const fromOffset = start + openLen;

			try {
				const range = document.createRange();
				range.setStart(node, Math.min(fromOffset, node.nodeValue.length));

				let endNode = root;
				try {
					endNode = (root.nodeType === 11 || root.nodeType === 1) ? root : node.parentNode;
					while (endNode && endNode.lastChild) endNode = endNode.lastChild;
				} catch (_) {}
				if (endNode && endNode.nodeType === 3) range.setEnd(endNode, endNode.nodeValue.length);
				else if (endNode) range.setEndAfter(endNode);
				else range.setEndAfter(node);

				const remainder = range.extractContents();

				const outTag = (r.tag && typeof r.tag === 'string') ? r.tag.toLowerCase() : 'span';
				const hostTag = (outTag === 'p') ? 'span' : outTag;
				const el = document.createElement(hostTag);
				if (r.className) el.className = r.className;
				el.setAttribute('data-cm', r.name);
				el.setAttribute('data-cm-pending', '1');

				el.appendChild(remainder);
				range.insertNode(el);
				range.detach();

				try { node.nodeValue = prefixText; } catch (_) {}
				this.markup.debug('cm.stream.open.pending', { name: r.name });
				return;
			} catch (err) {
				try {
					const tail = text.slice(start + r.open.length);
					const frag = document.createDocumentFragment();

					if (prefixText) frag.appendChild(document.createTextNode(prefixText));

					const el = document.createElement((r.tag === 'p') ? 'span' : r.tag);
					if (r.className) el.className = r.className;
					el.setAttribute('data-cm', r.name);
					el.setAttribute('data-cm-pending', '1');

					this.markup.html.setInnerByMode(el, r.innerMode, tail, MD, !!r.decodeEntities, r);
					frag.appendChild(el);

					node.parentNode.replaceChild(frag, node);
					this.markup.debug('cm.stream.open.pending.fallback', { name: r.name });
					return;
				} catch (_) {}
			}
		}
	}

    // Finalize any pending openers if their closer token is found in the subtree
	applyStreamFinalizeClosers(root, rulesAll) {
		if (!root) return;

		const scope = (root.nodeType === 1 || root.nodeType === 11) ? root : document;
		const pending = scope.querySelectorAll('[data-cm][data-cm-pending="1"]');
		if (!pending || !pending.length) return;

		const rulesByName = new Map();
		(rulesAll || []).forEach(r => { if (r && r.name) rulesByName.set(r.name, r); });

		for (let i = 0; i < pending.length; i++) {
			const el = pending[i];
			const name = el.getAttribute('data-cm') || '';
			const rule = rulesByName.get(name);
			if (!rule || !rule.close) continue;

			const self = this;
			const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
				acceptNode(node) {
					const val = node && node.nodeValue ? node.nodeValue : '';
					if (!val || val.indexOf(rule.close) === -1) return NodeFilter.FILTER_SKIP;
					if (self.isInsideForbiddenContext(node)) return NodeFilter.FILTER_REJECT;
					return NodeFilter.FILTER_ACCEPT;
				}
			});

			let nodeWithClose = null;
			let idxInNode = -1;
			let tn;
			while ((tn = walker.nextNode())) {
				const idx = tn.nodeValue.indexOf(rule.close);
				if (idx !== -1) {
					nodeWithClose = tn;
					idxInNode = idx;
					break;
				}
			}
			if (!nodeWithClose) continue;

			try {
				const tokenLen = rule.close.length;

				const afterRange = document.createRange();
				afterRange.setStart(nodeWithClose, idxInNode + tokenLen);
				let endNode = el;
				while (endNode && endNode.lastChild) endNode = endNode.lastChild;
				if (endNode && endNode.nodeType === 3) afterRange.setEnd(endNode, endNode.nodeValue.length);
				else afterRange.setEndAfter(el.lastChild || el);

				const tail = afterRange.extractContents();
				afterRange.detach();

				const tok = document.createRange();
				tok.setStart(nodeWithClose, idxInNode);
				tok.setEnd(nodeWithClose, idxInNode + tokenLen);
				tok.deleteContents();
				tok.detach();

				if (el.parentNode && tail && tail.childNodes.length) {
					el.parentNode.insertBefore(tail, el.nextSibling);
				}

				el.removeAttribute('data-cm-pending');
				this.markup.debug('cm.stream.close.finalize', { name });
			} catch (err) {}
		}
	}

}
