// RuntimePartials owns partials behavior and state.
class RuntimePartials {

	// ========================================
	// Composition
	// ========================================

	constructor(runtime) {
		this.runtime = runtime;
		this._partialStreams = new Map();
	}

	// ========================================
	// Partial responses
	// ========================================

	clearPartialStreamState = () => {
		this._partialStreams.clear();
	};

	// Append streamed Markdown into a nested partial of an existing assistant
	// turn. A missing durable node gets a provisional id-bound stream host; it is
	// never rendered as an unrelated second message.
	appendPartialStream = (parentId, partId, chunk, begin = false, agentName = '') => {
		const key = this._partialStreamKey(parentId, partId);
		let state = this._partialStreams.get(key) || null;
		if (begin || !state || (state.root && !state.root.isConnected)) {
			const host = this._findPartialStreamHost(parentId, partId, true, agentName);
			if (!host) {
				const finalLatch = this.runtime.workflows.finalActive;
				// Python owns loader visibility and knows whether this is hidden
				// reasoning or actual response text. Do not hide the loader here.
				if (!state || !state.fallback) this.runtime.streaming.beginStream(false);
				this.runtime.workflows.finalActive = finalLatch;
				state = { fallback: true, text: '' };
				this._partialStreams.set(key, state);
			} else {
				state = { ...host, text: '' };
				this._partialStreams.set(key, state);
			}
		}

		if (state && !state.fallback && agentName) {
			this.runtime.workflows.setAgentNamePrefix(state.part, agentName, state.root || null);
		}

		const value = String(chunk || '');
		if (!value) return;
		if (state.fallback) {
			this.runtime.streaming.appendStream('', value);
			return;
		}
		let reasoningState = null;
		try { reasoningState = this.runtime.stream.reasoning.updateReasoningVisibilityFromChunk(value); } catch (_) {}
		state.text += value;
		this._renderPartialStream(state);
		try {
			if (reasoningState && reasoningState.hasResponseText && !this.runtime.stream.reasoning.reasoningThinking) {
				this.runtime.stream.reasoning.scheduleReasoningHide(state.msg || null, state.root || null);
			}
		} catch (_) {}
	};

	finalizePartialDom = (msgId, target, desired = null) => {
		if (!target) return;
		const prefix = `${String(msgId)}::`;
		for (const key of Array.from(this._partialStreams.keys())) {
			if (String(key).startsWith(prefix)) this._partialStreams.delete(key);
		}

		let desiredParts = null;
		try {
			desiredParts = desired ? desired.querySelectorAll('.msg-part[data-part-id]') : [];
		} catch (_) { desiredParts = []; }
		const desiredById = new Map();
		for (const part of Array.from(desiredParts || [])) {
			desiredById.set(String(part.dataset.partId || ''), part);
		}

		try {
			for (const part of Array.from(target.querySelectorAll('.msg-part[data-live-part="1"]'))) {
				const partId = String(part.dataset.partId || '');
				const snapshot = desiredById.get(partId) || null;
				part.removeAttribute('data-live-part');
				part.classList.remove('msg-part-live');
				if (snapshot && snapshot.className) part.className = snapshot.className;
			}
		} catch (_) {}
		try { this.runtime.stream.code.defuseOrphanActiveBlocks(target); } catch (_) {}
	};

	// ========================================
	// Partial responses internals
	// ========================================

	_partialStreamKey = (parentId, partId) => `${String(parentId)}::${String(partId)}`;

	_findPartialStreamHost = (parentId, partId, create = false, agentName = '') => {
		const host = this.runtime.workflows.workflowMessageHost(parentId, create);
		if (!host || !host.timeline) return null;

		const pid = String(partId);
		let part = null;
		for (const node of host.timeline.querySelectorAll('.msg-part[data-live-part="1"]')) {
			if (String(node.dataset.partId || '') === pid) { part = node; break; }
		}
		if (!part && !create) return null;
		if (!part) {
			part = document.createElement('div');
			part.className = 'msg-part msg-part-live';
			part.dataset.livePart = '1';
			part.dataset.partId = pid;
			const root = document.createElement('div');
			root.className = 'md-snapshot-root';
			part.appendChild(root);

			// getStreamMsg() creates one direct md-snapshot-root as a placeholder for
			// the initial generic stream. Once the workflow switches to explicit
			// inline partials that placeholder is no longer a chronological segment.
			// Leaving it behind made later status rows think that no text had been
			// rendered yet and insert themselves *before* prose that already lived in
			// a msg-part. Remove only a truly empty direct placeholder; never touch a
			// root that already contains streamed text.
			let placeholder = null;
			try { placeholder = host.timeline.querySelector(':scope > .md-snapshot-root'); }
			catch (_) { placeholder = null; }
			if (placeholder) {
				const hasText = !!String(placeholder.textContent || '').trim();
				const hasElements = placeholder.children && placeholder.children.length > 0;
				if (!hasText && !hasElements) {
					try { placeholder.remove(); } catch (_) {}
				}
			}

			// Timeline children are append-only. Every new prose/tool/status segment
			// lands after what was already shown.
			host.timeline.appendChild(part);
		}
		let root = part.querySelector('.md-snapshot-root');
		if (!root) {
			root = document.createElement('div');
			root.className = 'md-snapshot-root';
			part.appendChild(root);
		}
		this.runtime.workflows.setAgentNamePrefix(part, agentName, root);
		return { ...host, part, root };
	};

	_renderPartialStream = (state) => {
		if (!state || !state.root || !state.root.isConnected) return false;
		let frag = null;
		try {
			frag = this.runtime.renderer.renderStreamingSnapshotFragment(state.text || '');
		} catch (_) {
			frag = document.createDocumentFragment();
			frag.appendChild(document.createTextNode(state.text || ''));
		}
		state.root.replaceChildren(frag);

		try {
			// Streaming custom markup must also materialize an opener that has no
			// closer yet. This makes <think> become a CSS reasoning block from the
			// very first tag, including post-tool inline partials.
			this.runtime.customMarkup.live.applyStream(state.root, this.runtime.renderer.MD_STREAM || this.runtime.renderer.MD);
		} catch (_) {}
		try { this.runtime.stream.reasoning.syncReasoningVisibility(state.root); } catch (_) {}
		try {
			this.runtime.highlighter.observeNewCode(state.root, {
				deferLastIfStreaming: true,
				minLinesForLast: this.runtime.cfg.PROFILE_CODE.minLinesForHL,
				minCharsForLast: this.runtime.cfg.PROFILE_CODE.minCharsForHL
			}, this.runtime.stream.code.activeCode);
			this.runtime.highlighter.scanVisibleCodesInRoot(state.root, this.runtime.stream.code.activeCode || null);
		} catch (_) {}
		try { this.runtime.codeScroll.initScrollableBlocks(state.root); } catch (_) {}
		try {
			const mm = getMathMode();
			if (mm === 'idle') this.runtime.math.schedule(state.root);
			else if (mm === 'always') this.runtime.math.schedule(state.root, 0, true);
		} catch (_) {}
		this.runtime.scrollMgr.scheduleScroll(true);
		return true;
	};

}
