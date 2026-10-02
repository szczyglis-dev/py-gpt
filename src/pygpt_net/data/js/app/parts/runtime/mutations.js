// RuntimeMutations owns mutations behavior and state.
class RuntimeMutations {

	// ========================================
	// Composition
	// ========================================

	constructor(runtime) {
		this.runtime = runtime;
	}

	// ========================================
	// Mutation transport and postprocessing
	// ========================================

	// ------------------------------------------------------------------
	// Unified renderer mutation transport.
	// ------------------------------------------------------------------
	parseRenderMutation = (payload) => {
		let obj = payload;
		if (typeof obj === 'string') {
			const text = obj.trim();
			if (!text || text[0] !== '{') return null;
			try { obj = JSON.parse(text); } catch (_) { return null; }
		}
		if (!obj || typeof obj !== 'object' || !obj.mutation || typeof obj.mutation !== 'object') return null;
		return obj.mutation;
	};

    _syncUserAttachments = (block) => {
        if (!block || !block.extra || !block.extra.user_attachments) return;
        const bubble = document.getElementById(`msg-user-${block.id}`);
        const region = bubble && bubble.closest('.msg-user-region');
        if (!region) return;
        const html = this.runtime.templates.artifacts.renderUserAttachments(block.extra.user_attachments);
        const current = region.querySelector('.user-attachments');
        if (current && current.outerHTML === html) return;
        if (current) current.outerHTML = html;
        else bubble.insertAdjacentHTML('beforebegin', html);
        this._postMutation(region);
    };

	applyMutation = (mutation) => {
		if (!mutation || typeof mutation !== 'object') return false;
		const op = String(mutation.op || '');
		const block = mutation.block || null;
		this._syncUserAttachments(block);
		switch (op) {
			case 'finalize_output':
				this._finalizeOutputMutation(mutation);
				return true;
			case 'sync_output':
				this._syncOutputMutation(mutation);
				return true;
			case 'replace_output':
				this._syncOutputMutation(Object.assign({}, mutation, {replace_text: true}));
				return true;
			case 'replace_input':
				this._replaceInputMutation(mutation);
				return true;
			case 'append_input':
				this._appendDurableInput(block);
				return true;
			case 'append_output':
				this._syncOutputMutation(Object.assign({}, mutation, {replace_text: true}));
				return true;
			case 'append_artifact':
			case 'append_artifacts':
				this._appendArtifactsMutation(mutation);
				return true;
			case 'replace_artifacts':
				this._syncOutputMutation(Object.assign({}, mutation, {replace_text: false}));
				return true;
			case 'remove_message':
				this.runtime.nodes.removeNode(mutation.msg_id, this.runtime.scrollMgr);
				return true;
			case 'remove_from':
				this.runtime.nodes.removeNodesFromId(mutation.msg_id, this.runtime.scrollMgr);
				return true;
			default:
				return false;
		}
	};

	// ========================================
	// Mutation transport and postprocessing internals
	// ========================================

	_mutationElement = (block, role) => {
		if (!block) return null;
		try {
			const html = this.runtime.templates.renderNode(block);
			const tmp = document.createElement('div');
			tmp.innerHTML = html;
			return tmp.querySelector(role === 'user' ? '.msg-user-region' : '.msg-box.msg-bot');
		} catch (_) { return null; }
	};

	_postMutation = (root) => {
		if (!root) return;
		try {
			const maybe = this.runtime.renderer.renderPendingMarkdown(root);
			const done = () => {
				try { this.runtime.nodes.processBox(root); } catch (_) {}
				try { this.runtime.nodes.refreshToolGroups(this.runtime.dom.get('_nodes_')); } catch (_) {}
				try { this.runtime.scrollMgr.virtualization.endMessageMutation(root); } catch (_) {}
				try { this.runtime.scrollMgr.syncBottomNowIfFollowing(); } catch (_) {}
				this.runtime.scrollMgr.virtualization.scheduleMessageVirtualizationRefresh();
				this.runtime.scrollMgr.scheduleScroll(true);
			};
			if (maybe && typeof maybe.then === 'function') maybe.then(done); else done();
		} catch (_) {
			try { this.runtime.scrollMgr.virtualization.endMessageMutation(root); } catch (__) {}
		}
	};

	// ========================================
	// User input mutations internals
	// ========================================

	_appendDurableInput = (block) => {
		if (!block || !block.input || !block.input.text) return;
		const id = String(block.id == null ? '' : block.id);
		if (!id) return;
		if (document.getElementById(`msg-user-${id}`)) {
			try { this.runtime.loading.inputReady(); } catch (_) {}
			return;
		}
		const nodes = this.runtime.dom.get('_nodes_');
		if (!nodes) return;
		try {
			const inputOnly = Object.assign({}, block, {output: null});
			const html = this.runtime.templates.renderNode(inputOnly);
			nodes.insertAdjacentHTML('beforeend', html);
			nodes.classList.remove('empty_list');
			this.runtime.nodes.materializeUserMdAsPlainText(nodes);
			this.runtime.nodes.userCollapse.apply(nodes);
			this.runtime.nodes.ensureUserCopyIcons(nodes);
			// SEND_INIT may have armed a delayed loader that is gated on the
			// user row. Reserve/show it only now, after the input is in DOM.
			try { this.runtime.loading.inputReady(); } catch (_) {}
		} catch (_) {}

		// Input is transient too. Never let a late sync for an older turn clear
		// the input row that already belongs to a newer request.
		try {
			const input = this.runtime.dom.get('_append_input_');
			const owner = input && input.dataset ? String(input.dataset.renderMsgId || '') : '';
			if (!owner || owner === id) {
				this.runtime.dom.clearInput();
				if (input && input.dataset) delete input.dataset.renderMsgId;
			}
		} catch (_) {}
	};

	_replaceInputMutation = (mutation) => {
		const block = mutation.block || null;
		if (!block) return;
		const id = String(mutation.msg_id != null ? mutation.msg_id : (block.id != null ? block.id : ''));
		if (!id) return;
		const target = document.getElementById(`msg-user-${id}`);
		const desired = this._mutationElement(block, 'user');
		if (!desired) return;
		if (target) (target.closest('.msg-user-region') || target).replaceWith(desired);
		else {
			const nodes = this.runtime.dom.get('_nodes_');
			if (!nodes) return;
			nodes.appendChild(desired);
			nodes.classList.remove('empty_list');
		}
		try {
			this.runtime.nodes.materializeUserMdAsPlainText(desired.parentNode || desired);
			this.runtime.nodes.userCollapse.apply(desired.parentNode || desired);
			this.runtime.nodes.ensureUserCopyIcons(desired.parentNode || desired);
		} catch (_) {}
	};

	// ========================================
	// Assistant message mutations internals
	// ========================================

	_patchBotMutation = (target, block, replaceText = false) => {
		if (!target || !block) return target;
		try { this.runtime.scrollMgr.virtualization.beginMessageMutation(target); } catch (_) {}
		const desired = this._mutationElement(block, 'bot');
		if (!desired) {
			try { this.runtime.scrollMgr.virtualization.endMessageMutation(target); } catch (_) {}
			return target;
		}

		try {
			for (const attr of ['data-tool-only', 'data-tool-chain-continuation']) {
				if (desired.hasAttribute(attr)) target.setAttribute(attr, desired.getAttribute(attr));
				else target.removeAttribute(attr);
			}
		} catch (_) {}

		try {
			const oldHeader = target.querySelector(':scope > .name-header');
			const newHeader = desired.querySelector(':scope > .name-header');
			if (newHeader) {
				if (oldHeader) oldHeader.replaceWith(newHeader.cloneNode(true));
				else target.insertBefore(newHeader.cloneNode(true), target.firstChild || null);
			} else if (oldHeader) oldHeader.remove();
		} catch (_) {}

		let msg = null;
		let desiredMsg = null;
		try { msg = target.querySelector(':scope > .msg') || target.querySelector('.msg'); } catch (_) { msg = target.querySelector('.msg'); }
		try { desiredMsg = desired.querySelector(':scope > .msg') || desired.querySelector('.msg'); } catch (_) { desiredMsg = desired.querySelector('.msg'); }
		if (!msg || !desiredMsg) {
			try { this.runtime.scrollMgr.virtualization.endMessageMutation(target); } catch (_) {}
			return target;
		}

		const timeline = this.runtime.dom.getMsgTimeline(msg, true);
		const desiredTimeline = this.runtime.dom.getMsgTimeline(desiredMsg, true);
		if (replaceText && timeline && desiredTimeline) {
			const replacements = Array.from(desiredTimeline.childNodes).map(n => n.cloneNode(true));
			for (const node of replacements) {
				if (!node.querySelectorAll) continue;
				const outputs = node.matches('.tool-output[data-tool-keys]') ? [node] : Array.from(node.querySelectorAll('.tool-output[data-tool-keys]'));
				for (const output of outputs) {
					const reconciled = this.runtime.toolOutput.reconcile(timeline, output);
					if (output === node) replacements[replacements.indexOf(node)] = reconciled;
					else output.replaceWith(reconciled);
				}
			}
			timeline.replaceChildren(...replacements);
		} else if (timeline && desiredTimeline) {
			// Preserve token-streamed prose. Structural rows are reconciled around it.
			// Completed Agents v2 turns get a dedicated transition so their final
			// streamed node remains untouched while preceding work folds away.
			const collapsingWorkflow = this.runtime.timeline.collapseCompletedWorkflow(
				target, timeline, desiredTimeline, block
			);
			if (!collapsingWorkflow) this.runtime.timeline.syncTimelineStructuralNodes(timeline, desiredTimeline);
		}

		for (const selector of ['.msg-tool-extra', '.msg-extra']) {
			try {
				const dst = msg.querySelector(`:scope > ${selector}`) || msg.querySelector(selector);
				const src = desiredMsg.querySelector(`:scope > ${selector}`) || desiredMsg.querySelector(selector);
				if (!src) {
					if (dst) dst.remove();
					continue;
				}
				const clone = src.cloneNode(true);
				if (dst) dst.replaceWith(clone);
				else {
					const actions = msg.querySelector(':scope > .action-icons');
					if (actions) msg.insertBefore(clone, actions);
					else msg.appendChild(clone);
				}
			} catch (_) {}
		}

		try {
			let oldActions = msg.querySelector(':scope > .action-icons');
			const newActions = desiredMsg.querySelector(':scope > .action-icons');
			if (!oldActions && this.runtime.dom && typeof this.runtime.dom.ensureStreamFooterPlaceholder === 'function') {
				oldActions = this.runtime.dom.ensureStreamFooterPlaceholder(msg);
			}
			if (oldActions && newActions) {
				// Reconcile in place. Replacing the whole footer node caused a visible
				// disappear/reappear cycle in Autonomous continuations. Keeping the slot
				// node stable means only its contents/visibility change, never its height.
				oldActions.replaceChildren(...Array.from(newActions.childNodes).map(n => n.cloneNode(true)));
				oldActions.dataset.footerSlot = '1';
				delete oldActions.dataset.streamFooterPlaceholder;
				const dataId = newActions.getAttribute('data-id');
				if (dataId != null) oldActions.setAttribute('data-id', dataId);
				else oldActions.removeAttribute('data-id');
			} else if (oldActions && !newActions && !this.runtime.turns.activeTurnIds.has(this.runtime.turns.turnId(block.id))) {
				// No actions in an authoritative completed snapshot: keep the footer
				// footprint, but return it to an invisible placeholder.
				if (this.runtime.dom && typeof this.runtime.dom.setActionFooterPlaceholder === 'function') {
					this.runtime.dom.setActionFooterPlaceholder(oldActions);
				}
			}
		} catch (_) {}
		this.runtime.turns.syncMessageActionVisibility(target, block);

		// Finalize stream-only markers without reconstructing the prose DOM. This is
		// especially important for inline post-tool/Agents v2 partial streams.
		this.runtime.partials.finalizePartialDom(block.id, target, desired);
		this._postMutation(target);
		return target;
	};

	_finalizeOutputMutation = (mutation) => {
		const block = mutation.block || null;
		if (!block) return;
		const id = String(mutation.msg_id != null ? mutation.msg_id : (block.id != null ? block.id : ''));
		if (!id) return;

		const nodes = this.runtime.dom.get('_nodes_');
		const before = this.runtime.dom.get('_append_output_before_');
		const streamContainer = this.runtime.dom.getStreamContainer();
		let liveBox = null;
		try { liveBox = streamContainer && streamContainer.querySelector('.msg-box.msg-bot'); } catch (_) {}
		const ownsLive = !!(liveBox && this.runtime.turns.streamBoxOwner(liveBox) === id);

		let beforeBoxes = [];
		try { beforeBoxes = before ? Array.from(before.querySelectorAll('.msg-box.msg-bot')) : []; } catch (_) {}
		const ownsBefore = beforeBoxes.length > 0 && beforeBoxes.every((box) => this.runtime.turns.streamBoxOwner(box) === id);

		// High-frequency stream state is global to this WebView, so touch it only
		// when the live node is owned by this mutation. A stale finalization may
		// legitimately arrive after the next request has already begun.
		if (ownsLive) {
			this.runtime.streaming.flushStreamQueueNow();
			try { if (this.runtime.stream && this.runtime.stream.isStreaming) this.runtime.stream.endStream(); } catch (_) {}
		}

		this._appendDurableInput(block);

		let target = document.getElementById(`msg-bot-${id}`);
		let targetIsDurable = !!(target && nodes && nodes.contains(target));

		if (!targetIsDurable && ownsLive && !ownsBefore && liveBox && nodes) {
			liveBox.id = `msg-bot-${id}`;
			nodes.appendChild(liveBox); // move, do not clone: preserve streamed DOM exactly
			nodes.classList.remove('empty_list');
			target = liveBox;
			targetIsDurable = true;
		} else if (!targetIsDurable && ownsBefore) {
			// ``nextStream`` produced multiple transient boxes. No single live node can
			// represent the durable message, so use the explicit replacement fallback.
			target = null;
		}

		// If there is no promotable node (multi-segment legacy stream, non-stream
		// snapshot, or a stale final whose transient node is already gone), render
		// this one message from its authoritative snapshot. Never rebuild the chat.
		if (!target && nodes) {
			const desired = this._mutationElement(block, 'bot');
			if (desired) {
				nodes.appendChild(desired);
				nodes.classList.remove('empty_list');
				target = desired;
				mutation.replace_text = true;
			}
		}

		if (ownsBefore) {
			try { this.runtime.dom.fastClearHidden('_append_output_before_'); } catch (_) {}
		}
		if (ownsLive) {
			try { this.runtime.dom.fastClearHidden('_append_output_'); } catch (_) {}
			try { this.runtime.dom.resetEphemeral(); } catch (_) {}
		}
		if (target) this._patchBotMutation(target, block, !!mutation.replace_text);
	};

	_syncOutputMutation = (mutation) => {
		const block = mutation.block || null;
		if (!block) return;
		this._appendDurableInput(block);
		const id = String(mutation.msg_id != null ? mutation.msg_id : (block.id != null ? block.id : ''));
		if (!id) return;
		let target = document.getElementById(`msg-bot-${id}`);
		const nodes = this.runtime.dom.get('_nodes_');
		const targetIsDurable = !!(target && nodes && nodes.contains(target));
		if (!targetIsDurable) {
			// A live stream box already carries the message id. Promote that exact DOM
			// only when it belongs to this message; a newer stream may already exist.
			const live = this.runtime.dom.getStreamContainer();
			let liveBox = null;
			try { liveBox = live && live.querySelector('.msg-box.msg-bot'); } catch (_) {}
			if (liveBox && this.runtime.turns.streamBoxOwner(liveBox) === id && (!target || target === liveBox)) {
				this._finalizeOutputMutation(Object.assign({}, mutation, {replace_text: false}));
				target = document.getElementById(`msg-bot-${id}`);
			}
		}
		if (!target) {
			const nodes = this.runtime.dom.get('_nodes_');
			const desired = this._mutationElement(block, 'bot');
			if (nodes && desired) {
				nodes.appendChild(desired);
				nodes.classList.remove('empty_list');
				target = desired;
			}
		}
		if (target) this._patchBotMutation(target, block, !!mutation.replace_text);
	};

	// ========================================
	// Artifact mutations internals
	// ========================================

	_appendArtifactsMutation = (mutation) => {
		const extra = mutation.extra || {};
		const html = String(extra.html || '');
		const id = mutation.msg_id;
		if (html && id != null) {
			this.runtime.nodes.appendExtra(id, html, this.runtime.scrollMgr);
			return;
		}
		if (mutation.block) this._syncOutputMutation(Object.assign({}, mutation, {replace_text: false}));
	};

}
