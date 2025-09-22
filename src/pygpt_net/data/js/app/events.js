// ==========================================================================
// Event manager
// ==========================================================================

class EventManager {

	// Initializes the event manager.
	constructor(cfg, dom, scrollMgr, highlighter, codeScroll, toolOutput, bridge) {
		this.cfg = cfg;
		this.dom = dom;
		this.scrollMgr = scrollMgr;
		this.highlighter = highlighter;
		this.codeScroll = codeScroll;
		this.toolOutput = toolOutput;
		this.bridge = bridge;
		this.handlers = {
			wheel: null,
			scroll: null,
			resize: null,
			fabClick: null,
			mouseover: null,
			mouseout: null,
			click: null,
			keydown: null,
			docClickFocus: null,
			visibility: null,
			focus: null,
			pageshow: null
		};
	}

	// Finds the closest code wrapper element.
	_findWrapper(target) {
		if (!target || typeof target.closest !== 'function') return null;
		return target.closest('.code-wrapper');
	}

	// Gets the code element inside a wrapper.
	_getCodeEl(wrapper) {
		if (!wrapper) return null;
		return wrapper.querySelector('pre > code');
	}

	// Collects the text content from a code element.
	_collectCodeText(codeEl) {
		if (!codeEl) return '';
		const frozen = codeEl.querySelector('.hl-frozen');
		const tail = codeEl.querySelector('.hl-tail');
		if (frozen || tail) return (frozen?.textContent || '') + (tail?.textContent || '');
		return codeEl.textContent || '';
	}

	// Collect plain text from a user message, ignoring helper UI (ellipsis/toggle/icon).
	_collectUserText(msgBox) {
		if (!msgBox) return '';
		const msg = msgBox.querySelector('.msg');
		if (!msg) return '';
		// Prefer the content container if present.
		const root = msg.querySelector('.uc-content') || msg;

		let out = '';
		const walker = document.createTreeWalker(
			root,
			NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
			{
				acceptNode: (node) => {
					if (node.nodeType === Node.ELEMENT_NODE) {
						const el = node;
						// Skip helper UI and prune subtree.
						if (el.matches('.uc-ellipsis,[data-copy-ignore="1"],.msg-copy-btn,.uc-toggle')) {
							return NodeFilter.FILTER_REJECT;
						}
						// Convert <br> into newlines.
						if (el.tagName === 'BR') {
							out += '\n';
							return NodeFilter.FILTER_SKIP;
						}
					}
					if (node.nodeType === Node.TEXT_NODE) {
						return NodeFilter.FILTER_ACCEPT;
					}
					return NodeFilter.FILTER_SKIP;
				}
			},
			false
		);

		let n;
		while ((n = walker.nextNode())) {
			out += n.nodeValue;
		}
		return String(out || '').replace(/\r\n?/g, '\n');
	}

	// Copy to clipboard via bridge if available, otherwise use browser APIs.
	async _copyTextRobust(text) {
		try {
			if (this.bridge && typeof this.bridge.copyCode === 'function') {
				this.bridge.copyCode(text);
				return true;
			}
		} catch (_) {}
		try {
			if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
				await navigator.clipboard.writeText(text);
				return true;
			}
		} catch (_) {}
		try {
			const ta = document.createElement('textarea');
			ta.value = text;
			ta.setAttribute('readonly', '');
			ta.style.position = 'fixed';
			ta.style.top = '-9999px';
			ta.style.opacity = '0';
			document.body.appendChild(ta);
			ta.select();
			const ok = document.execCommand && document.execCommand('copy');
			document.body.removeChild(ta);
			return !!ok;
		} catch (_) {
			return false;
		}
	}

	// Flash "Copied" feedback on the copy button.
    _flashCopied(btn, wrapper) {
        if (!btn) return;
        const DUR = 1200;

        // Try to find an icon to swap (works for both code-header and msg copy buttons)
        const img = btn.querySelector('img.copy-img') || btn.querySelector('img.action-img') || btn.querySelector('img');

        // Clear pending timers to avoid races on rapid clicks
        try { if (btn.__copyTimer) { clearTimeout(btn.__copyTimer); btn.__copyTimer = 0; } } catch (_) {}
        try { if (btn.__iconTimer) { clearTimeout(btn.__iconTimer); btn.__iconTimer = 0; } } catch (_) {}

        // Icon swap to success (window.ICON_DONE), then restore
        if (typeof window !== 'undefined' && window.ICON_DONE && img) {
            // Cache original icon once
            if (!btn.__origIconSrc) {
                try { btn.__origIconSrc = img.getAttribute('src') || ''; } catch (_) { btn.__origIconSrc = ''; }
            }
            try { img.setAttribute('src', String(window.ICON_DONE)); } catch (_) {}
            btn.__iconTimer = setTimeout(() => {
                try {
                    const orig = btn.__origIconSrc || '';
                    if (orig) img.setAttribute('src', orig);
                } catch (_) {}
                btn.__iconTimer = 0;
            }, DUR);
        }

        const span = btn.querySelector('span');
        // Icon-only fallback (no label)
        if (!span) {
            btn.classList.add('copied');
            btn.__copyTimer = setTimeout(() => {
                try { btn.classList.remove('copied'); } catch (_) {}
                btn.__copyTimer = 0;
            }, DUR);
            return;
        }

        const L_COPY = (wrapper && wrapper.getAttribute('data-locale-copy')) || 'Copy';
        const L_COPIED = (wrapper && wrapper.getAttribute('data-locale-copied')) || 'Copied';
        span.textContent = L_COPIED;
        btn.classList.add('copied');
        btn.__copyTimer = setTimeout(() => {
            try {
                span.textContent = L_COPY;
                btn.classList.remove('copied');
            } catch (_) {}
            btn.__copyTimer = 0;
        }, DUR);
    }

	// Toggle code collapse/expand and remember collapsed indices.
    _toggleCollapse(wrapper) {
        if (!wrapper) return;
        const codeEl = this._getCodeEl(wrapper);
        if (!codeEl) return;
        const btn = wrapper.querySelector('.code-header-collapse');
        const span = btn ? btn.querySelector('span') : null;
        const L_COLLAPSE = wrapper.getAttribute('data-locale-collapse') || 'Collapse';
        const L_EXPAND = wrapper.getAttribute('data-locale-expand') || 'Expand';
        const idx = String(wrapper.getAttribute('data-index') || '');
        const arr = window.__collapsed_idx || (window.__collapsed_idx = []);
        const isHidden = (codeEl.style.display === 'none');

        if (isHidden) {
            codeEl.style.display = 'block';
            if (span) span.textContent = L_COLLAPSE;
            const p = arr.indexOf(idx);
            if (p !== -1) arr.splice(p, 1);
            if (btn) btn.setAttribute('title', L_COLLAPSE);
        } else {
            codeEl.style.display = 'none';
            if (span) span.textContent = L_EXPAND;
            if (!arr.includes(idx)) arr.push(idx);
            if (btn) btn.setAttribute('title', L_EXPAND);
        }

        // Click feedback (same "pop" effect as input)
        if (btn) {
            try { if (btn.__popTimer) { clearTimeout(btn.__popTimer); btn.__popTimer = 0; } } catch (_) {}
            btn.classList.add('copied');
            btn.__popTimer = setTimeout(() => {
                try { btn.classList.remove('copied'); } catch (_) {}
                btn.__popTimer = 0;
            }, 1200);
        }
    }

	// Attach global UI event handlers and container-level interactions.
	install() {
		try {
			history.scrollRestoration = "manual";
		} catch (_) {}

		this.handlers.keydown = (event) => {
			if (event.ctrlKey && event.key === 'f') {
				window.location.href = 'bridge://open_find:' + runtime.cfg.PID;
				event.preventDefault();
			}
			if (event.key === 'Escape') {
				window.location.href = 'bridge://escape';
				event.preventDefault();
			}
		};
		document.addEventListener('keydown', this.handlers.keydown, { passive: false });

		// Removed global click-to-focus navigation and visibility/focus wakeups to keep the pump rAF-only and click-agnostic.

		const container = this.dom.get('container');
		const inputArea = this.dom.get('_append_input_');

		const addClassToMsg = (id, className) => {
			const el = document.getElementById('msg-bot-' + id);
			if (el) el.classList.add(className);
		};
		const removeClassFromMsg = (id, className) => {
			const el = document.getElementById('msg-bot-' + id);
			if (el) el.classList.remove(className);
		};

		this.handlers.mouseover = (event) => {
			if (event.target.classList.contains('action-img')) {
				const id = event.target.getAttribute('data-id');
				addClassToMsg(id, 'msg-highlight');
			}
		};
		this.handlers.mouseout = (event) => {
			if (event.target.classList.contains('action-img')) {
				const id = event.target.getAttribute('data-id');
				const el = document.getElementById('msg-bot-' + id);
				if (el) el.classList.remove('msg-highlight');
			}
		};
		if (container) {
			container.addEventListener('mouseover', this.handlers.mouseover, { passive: true });
			container.addEventListener('mouseout', this.handlers.mouseout, { passive: true });
		}

		this.handlers.click = async (ev) => {
			// Code block header actions
			const aCode = ev.target && (ev.target.closest ? ev.target.closest('a.code-header-action') : null) || null;
			// User message copy action
			const aUserCopy = ev.target && (ev.target.closest ? ev.target.closest('a.msg-copy-btn') : null) || null;

			if (!aCode && !aUserCopy) return;

			ev.preventDefault();
			ev.stopPropagation();

			// Handle code header actions first (unchanged behavior)
			if (aCode) {
				const wrapper = this._findWrapper(aCode);
				if (!wrapper) return;

				const isCopy = aCode.classList.contains('code-header-copy');
				const isCollapse = aCode.classList.contains('code-header-collapse');
				const isRun = aCode.classList.contains('code-header-run');
				const isPreview = aCode.classList.contains('code-header-preview');

				let codeEl = null, text = '';
				if (isCopy || isRun || isPreview) {
					codeEl = this._getCodeEl(wrapper);
					text = this._collectCodeText(codeEl);
				}

				try {
					if (isCopy) {
						const ok = await this._copyTextRobust(text);
						if (ok) this._flashCopied(aCode, wrapper);
					} else if (isCollapse) {
						this._toggleCollapse(wrapper);
					} else if (isRun) {
						if (this.bridge && typeof this.bridge.runCode === 'function') this.bridge.runCode(text);
					} else if (isPreview) {
						if (this.bridge && typeof this.bridge.previewCode === 'function') this.bridge.previewCode(text);
					}
				} catch (_) {
					/* swallow */
				}
				return;
			}

			// Handle user message copy button (icon-only)
			if (aUserCopy) {
				try {
					const msgBox = aUserCopy.closest('.msg-box.msg-user');
					const text = this._collectUserText(msgBox);
					const ok = await this._copyTextRobust(text);

					// Localized tooltip swap and visual feedback
					const L = (this.cfg && this.cfg.LOCALE) || {};
					const L_COPY = L.COPY || 'Copy';
					const L_COPIED = L.COPIED || 'Copied';

					// Visual feedback only (no tooltip) + temporary icon swap handled centrally
					if (ok) {
						this._flashCopied(aUserCopy, null);
					}
				} catch (_) {
					/* swallow */
				}
			}
		};

		// Delegate clicks from both main container and input area to support copy icons everywhere.
		if (container) container.addEventListener('click', this.handlers.click, { passive: false });
		if (inputArea) inputArea.addEventListener('click', this.handlers.click, { passive: false });

		this.handlers.wheel = (ev) => {
			runtime.scrollMgr.userInteracted = true;
			if (ev.deltaY < 0) runtime.scrollMgr.autoFollow = false;
			else runtime.scrollMgr.maybeEnableAutoFollowByProximity();
			this.highlighter.scheduleScanVisibleCodes(runtime.stream.activeCode);
		};
		document.addEventListener('wheel', this.handlers.wheel, { passive: true });

		this.handlers.scroll = () => {
			const el = Utils.SE;
			const top = el.scrollTop;
			if (top + 1 < runtime.scrollMgr.lastScrollTop) runtime.scrollMgr.autoFollow = false;
			runtime.scrollMgr.maybeEnableAutoFollowByProximity();
			runtime.scrollMgr.lastScrollTop = top;
			const action = runtime.scrollMgr.computeFabAction();
			if (action !== runtime.scrollMgr.currentFabAction) runtime.scrollMgr.updateScrollFab(false, action, true);
			this.highlighter.scheduleScanVisibleCodes(runtime.stream.activeCode);
		};
		window.addEventListener('scroll', this.handlers.scroll, { passive: true });

		const fab = this.dom.get('scrollFab');
		if (fab) {
			this.handlers.fabClick = (ev) => {
				ev.preventDefault();
				ev.stopPropagation();
				const action = runtime.scrollMgr.computeFabAction();
				if (action === 'up') runtime.scrollMgr.scrollToTopUser();
				else if (action === 'down') runtime.scrollMgr.scrollToBottomUser();
				runtime.scrollMgr.fabFreezeUntil = Utils.now() + this.cfg.FAB.TOGGLE_DEBOUNCE_MS;
				runtime.scrollMgr.updateScrollFab(true);
			};
			fab.addEventListener('click', this.handlers.fabClick, { passive: false });
		}

		this.handlers.resize = () => {
			runtime.scrollMgr.maybeEnableAutoFollowByProximity();
			runtime.scrollMgr.scheduleScrollFabUpdate();
			this.highlighter.scheduleScanVisibleCodes(runtime.stream.activeCode);
		};
		window.addEventListener('resize', this.handlers.resize, { passive: true });

		// Note: visibility/focus/pageshow kickers removed intentionally.
	}

	// Detach all installed handlers and reset local refs.
	cleanup() {
		const container = this.dom.get('container');
		const inputArea = this.dom.get('_append_input_');

		if (this.handlers.wheel) document.removeEventListener('wheel', this.handlers.wheel);
		if (this.handlers.scroll) window.removeEventListener('scroll', this.handlers.scroll);
		if (this.handlers.resize) window.removeEventListener('resize', this.handlers.resize);
		const fab = this.dom.get('scrollFab');
		if (fab && this.handlers.fabClick) fab.removeEventListener('click', this.handlers.fabClick);
		if (container && this.handlers.mouseover) container.removeEventListener('mouseover', this.handlers.mouseover);
		if (container && this.handlers.mouseout) container.removeEventListener('mouseout', this.handlers.mouseout);
		if (container && this.handlers.click) container.removeEventListener('click', this.handlers.click);
		if (inputArea && this.handlers.click) inputArea.removeEventListener('click', this.handlers.click);
		if (this.handlers.keydown) document.removeEventListener('keydown', this.handlers.keydown);
		if (this.handlers.docClickFocus) document.removeEventListener('click', this.handlers.docClickFocus);
		if (this.handlers.visibility) document.removeEventListener('visibilitychange', this.handlers.visibility);
		if (this.handlers.focus) window.removeEventListener('focus', this.handlers.focus);
		if (this.handlers.pageshow) window.removeEventListener('pageshow', this.handlers.pageshow);
		this.handlers = {};
	}
}