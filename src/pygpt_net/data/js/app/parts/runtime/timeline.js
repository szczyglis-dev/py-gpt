// RuntimeTimeline owns timeline behavior and state.
class RuntimeTimeline {

	// ========================================
	// Composition
	// ========================================

	constructor(runtime) {
		this.runtime = runtime;
		this._workflowCollapseSeq = 0;
	}

	// ========================================
	// Timeline reconciliation and workflow collapse
	// ========================================

	syncTimelineStructuralNodes = (timeline, desiredTimeline) => {
		if (!timeline || !desiredTimeline) return;

		// Inline Autonomous/judge messages are part of the currently followed turn.
		// Remember FOLLOW ownership before changing geometry: if the user did not
		// manually stop following, materializing a new inline row must immediately
		// move the viewport behind that row instead of waiting for async Markdown
		// post-processing or for the next stream chunk.
		const followInlineInsert = !!(this.runtime.scrollMgr && this.runtime.scrollMgr.autoFollow === true);
		let inlineInserted = false;

		// Block-level tool output is structural: update it from the authoritative
		// snapshot, but never touch neighboring streamed prose.
		try {
			for (const el of Array.from(timeline.children)) {
				if (el.classList.contains('tool-output') && !el.hasAttribute('data-tool-keys')
						&& !el.classList.contains('agent-workflow-output')) el.remove();
			}
			for (const el of Array.from(desiredTimeline.children)) {
				if (el.classList.contains('tool-output') && !el.classList.contains('agent-workflow-output')) {
					timeline.appendChild(this.runtime.toolOutput.reconcile(timeline, el));
				}
			}
		} catch (_) {}

		// Partial timelines are incremental. Add only structural rows that cannot
		// be produced by token streaming: Autonomous inline messages and tool-only
		// partials. Text-bearing partials are deliberately left untouched.
		try {
			for (const desiredPart of Array.from(desiredTimeline.children)) {
				if (!desiredPart.classList || !desiredPart.classList.contains('msg-part')) continue;
				// Runtime status records are restored by bindWorkflowStream. Their
				// embedded live tools must not create a second structural message.
				if (desiredPart.classList.contains('msg-part-status')) continue;
				const partId = String((desiredPart.dataset && desiredPart.dataset.partId) || '');
				const isInline = desiredPart.classList.contains('msg-part-inline');
				const hasText = !!desiredPart.querySelector('.md-block');
				const hasTool = !!desiredPart.querySelector('.tool-output');
				if (!isInline && (!hasTool || hasText)) continue;

				let existing = partId ? this._timelinePartById(timeline, partId, isInline ? 'inline' : 'content') : null;
				if (!existing) {
					const clone = desiredPart.cloneNode(true);
					let liveSlot = null;
					for (const output of Array.from(clone.querySelectorAll('.tool-output[data-tool-keys]'))) {
						const reconciled = this.runtime.toolOutput.reconcile(timeline, output);
						if (!liveSlot && reconciled.closest) liveSlot = reconciled.closest('.msg-part-status');
						output.replaceWith(reconciled);
					}
					if (liveSlot && liveSlot.parentNode === timeline) timeline.insertBefore(clone, liveSlot);
					else timeline.appendChild(clone);
					if (isInline) inlineInserted = true;
					continue;
				}
				if (isInline) continue;

				// A tool result may become UI-ready after the partial itself already
				// exists. Reconcile only its tool controls, preserving prose nodes.
				for (const child of Array.from(desiredPart.children)) {
					if (child.classList.contains('tool-output')) {
						existing.appendChild(this.runtime.toolOutput.reconcile(timeline, child));
					}
				}
			}
		} catch (_) {}

		this.runtime.workflows.groupAgentNames(timeline);
		if (inlineInserted && followInlineInsert) {
			try {
				// Reassert FOLLOW synchronously after the DOM insertion. This is not a
				// forced user scroll: it only runs when FOLLOW already owned the viewport.
				// resumeAutoFollow(true) also marks the resulting scroll as programmatic,
				// so the scroll listener cannot misclassify it as manual upward movement.
				this.runtime.scrollMgr.resumeAutoFollow(true);
			} catch (_) {}
		}
	};

	collapseCompletedWorkflow = (target, timeline, desiredTimeline, block) => {
		if (!target || !timeline || !desiredTimeline || !block) return false;
		const workflow = block.extra && block.extra.collapsed_workflow;
		const compactFinal = block.extra && block.extra.agents_v2_compact_final;
		const workflowSteps = compactFinal ? Number(compactFinal.workflow_steps || 0) : 0;
		// Compact-final is a collapse command, not merely a marker that a final
		// response exists. A one-shot Agents v2 answer has no preceding workflow
		// and must never enter the fold/remove path.
		if (!workflow && (!compactFinal || workflowSteps <= 0)) return false;
		const desiredSummary = this._directTimelineChild(desiredTimeline, (el) =>
			el.classList && el.classList.contains('agent-workflow-output')
		);
		// Never remove live partials/tool/status rows unless the authoritative
		// snapshot contains the Processed accordion that will replace them. This
		// also protects against backend/frontend version skew where compact-final
		// metadata exists but no collapsed workflow was rendered.
		if (!desiredSummary) return false;

		const already = this._directTimelineChild(timeline, (el) =>
			el.classList && el.classList.contains('agent-workflow-output')
		);
		if (already) return true;

		const finalPartId = String((compactFinal && compactFinal.final_part_id) || (workflow && workflow.final_part_id) || '');
		const finalNodes = [];
		let finalNode = finalPartId ? this._timelinePartById(timeline, finalPartId, 'content') : null;
		if (finalNode) finalNodes.push(finalNode);

		// Legacy LlamaIndex agents can reach their first visible prose only after a
		// tool call. In that case AGENT_V2_BEGIN sees the already-created final part
		// as the active part, so the prose is streamed through the main
		// .md-snapshot-root instead of a nested .msg-part. bindWorkflowStream() still
		// tags the UI-only agent prefix with the durable part id; use that tag to keep
		// the prefix + streamed root together as the authoritative final response.
		if (!finalNodes.length && finalPartId) {
			let streamPrefix = null;
			try {
				streamPrefix = this._directTimelineChild(timeline, (el) =>
					el.classList && el.classList.contains('agent-name-prefix')
					&& String((el.dataset && el.dataset.partId) || '') === finalPartId
				);
			} catch (_) {}
			if (streamPrefix) {
				finalNodes.push(streamPrefix);
				const root = streamPrefix.nextElementSibling;
				if (root && root.classList && root.classList.contains('md-snapshot-root')) {
					finalNodes.push(root);
					finalNode = root;
				} else {
					finalNode = streamPrefix;
				}
			}
		}

		if (!finalNodes.length) {
			const textNodes = Array.from(timeline.children || []).filter((el) => {
				if (!el || !el.classList) return false;
				if (el.classList.contains('msg-part-inline') || el.classList.contains('msg-part-status')) return false;
				if (el.classList.contains('md-snapshot-root')) {
					return !!(String(el.textContent || '').trim() || (el.children && el.children.length));
				}
				try { return !!el.querySelector('.md-block') || el.classList.contains('md-block'); }
				catch (_) { return false; }
			});
			finalNode = textNodes.length ? textNodes[textNodes.length - 1] : null;
			if (finalNode) {
				const previous = finalNode.previousElementSibling;
				if (finalNode.classList.contains('md-snapshot-root') && previous
						&& previous.classList && previous.classList.contains('agent-name-prefix')) {
					finalNodes.push(previous);
				}
				finalNodes.push(finalNode);
			}
		}

		// If a version/race mismatch left no recognizable live final node, restore
		// only the authoritative final body from the desired snapshot. This is a
		// narrow fallback: normal streams keep their exact DOM and never get rebuilt.
		if (!finalNodes.length) {
			const desiredFinal = Array.from(desiredTimeline.children || []).filter((el) =>
				el && el.classList && (el.classList.contains('agent-name-prefix') || el.classList.contains('md-block'))
			);
			for (const source of desiredFinal) {
				const clone = source.cloneNode(true);
				timeline.appendChild(clone);
				finalNodes.push(clone);
			}
			finalNode = finalNodes.length ? finalNodes[0] : null;
		}

		const finalAnchor = finalNodes.length ? finalNodes[0] : finalNode;
		const keepFinal = new Set(finalNodes);
		const stale = Array.from(timeline.children || []).filter((el) =>
			!keepFinal.has(el) && !(el.classList && el.classList.contains('agent-workflow-output'))
		);
		const token = String(++this._workflowCollapseSeq);
		if (target.dataset) target.dataset.workflowCollapseToken = token;

		if (!stale.length) {
			if (desiredSummary) {
				this._insertCollapsedWorkflowSummary(timeline, desiredSummary, finalAnchor, token, target);
			}
			return true;
		}

		let reduced = false;
		try {
			reduced = typeof window !== 'undefined' && window.matchMedia
				&& window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		} catch (_) {}
		const duration = reduced || (workflow && workflow.expanded === true) ? 0 : 180;
		const animations = [];
		for (const el of stale) {
			if (!el) continue;
			if (duration <= 0 || typeof el.animate !== 'function') continue;
			try {
				const rect = el.getBoundingClientRect();
				const style = window.getComputedStyle ? window.getComputedStyle(el) : null;
				const fromMarginTop = style ? style.marginTop : '0px';
				const fromMarginBottom = style ? style.marginBottom : '0px';
				const animation = el.animate([
					{opacity: 1, height: `${Math.max(0, rect.height)}px`, marginTop: fromMarginTop, marginBottom: fromMarginBottom, overflow: 'hidden'},
					{opacity: 0, height: '0px', marginTop: '0px', marginBottom: '0px', overflow: 'hidden'}
				], {duration, easing: 'ease-in-out', fill: 'forwards'});
				animations.push(animation.finished.catch(() => {}));
			} catch (_) {}
		}

		const finish = () => {
			if (target.dataset && String(target.dataset.workflowCollapseToken || '') !== token) return;
			for (const el of stale) {
				try { if (el && el.parentNode === timeline) el.remove(); } catch (_) {}
			}
			if (desiredSummary) {
				this._insertCollapsedWorkflowSummary(timeline, desiredSummary, finalAnchor, token, target);
			}
		};
		if (!animations.length) finish();
		else Promise.all(animations).then(finish).catch(finish);
		return true;
	};

	// ========================================
	// Timeline reconciliation and workflow collapse internals
	// ========================================

	_directTimelineChild = (timeline, predicate) => {
		if (!timeline || !timeline.children || typeof predicate !== 'function') return null;
		for (const child of Array.from(timeline.children)) {
			try { if (predicate(child)) return child; } catch (_) {}
		}
		return null;
	};

	_timelinePartById = (timeline, partId, kind = '') => {
		const value = String(partId || '');
		if (!timeline || !value) return null;
		return this._directTimelineChild(timeline, (el) => {
			if (!el.classList || !el.classList.contains('msg-part')) return false;
			if (String((el.dataset && el.dataset.partId) || '') !== value) return false;
			if (kind === 'inline') return el.classList.contains('msg-part-inline');
			if (kind === 'content') {
				return !el.classList.contains('msg-part-inline')
					&& !el.classList.contains('msg-part-status');
			}
			return true;
		});
	};

	_insertCollapsedWorkflowSummary = (timeline, desiredSummary, finalNode, token, target) => {
		if (!timeline || !desiredSummary) return;
		if (target && target.dataset && String(target.dataset.workflowCollapseToken || '') !== String(token)) return;
		let existing = this._directTimelineChild(timeline, (el) =>
			el.classList && el.classList.contains('agent-workflow-output')
		);
		if (existing) existing.remove();

		const summary = desiredSummary.cloneNode(true);
		try {
			if (finalNode && finalNode.parentNode === timeline) timeline.insertBefore(summary, finalNode);
			else timeline.insertBefore(summary, timeline.firstChild || null);
		} catch (_) { return; }

		try {
			const reduced = typeof window !== 'undefined' && window.matchMedia
				&& window.matchMedia('(prefers-reduced-motion: reduce)').matches;
			if (!reduced && typeof summary.animate === 'function') {
				summary.animate(
					[{opacity: 0, transform: 'translateY(-3px)'}, {opacity: 1, transform: 'translateY(0)'}],
					{duration: 140, easing: 'ease-out'}
				);
			}
		} catch (_) {}

		try {
			const maybe = this.runtime.renderer.renderPendingMarkdown(summary);
			const done = () => {
				try { this.runtime.nodes.processBox(target || summary); } catch (_) {}
				try { this.runtime.scrollMgr.virtualization.scheduleMessageVirtualizationRefresh(); } catch (_) {}
				try { this.runtime.scrollMgr.scheduleScroll(true); } catch (_) {}
			};
			if (maybe && typeof maybe.then === 'function') maybe.then(done); else done();
		} catch (_) {}
	};

}
