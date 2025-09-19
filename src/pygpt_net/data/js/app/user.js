// ==========================================================================
// User collapse manager
// ==========================================================================

class UserCollapseManager {

	// collapsible user messages (msg-box.msg-user)
	constructor(cfg) {
		this.cfg = cfg || {};
		// Collapse threshold in pixels (can be overridden via window.USER_MSG_COLLAPSE_HEIGHT_PX).
		this.threshold = Utils.g('USER_MSG_COLLAPSE_HEIGHT_PX', 1000);
		// Track processed .msg elements to allow cheap remeasure on resize if needed.
		this._processed = new Set();

		// Visual indicator attached while collapsed (does not modify original text).
		this.ellipsisText = ' [...]';
	}

	// Icon paths for the collapse/expand buttons.
	_icons() {
		const I = (this.cfg && this.cfg.ICONS) || {};
		return {
			expand: I.EXPAND || '',
			collapse: I.COLLAPSE || ''
		};
	}

	// Label texts for the collapse/expand buttons.
	_labels() {
		const L = (this.cfg && this.cfg.LOCALE) || {};
		return {
			expand: L.EXPAND || 'Expand',
			collapse: L.COLLAPSE || 'Collapse'
		};
	}

	// Schedule a function for next frame (ensures layout is up-to-date before scrolling).
	_afterLayout(fn) {
		try {
			if (typeof runtime !== 'undefined' && runtime.raf && typeof runtime.raf.schedule === 'function') {
				const key = {
					t: 'UC:afterLayout',
					i: Math.random()
				};
				runtime.raf.schedule(key, () => {
					try {
						fn && fn();
					} catch (_) {}
				}, 'UserCollapse', 0);
				return;
			}
		} catch (_) {}
		try {
			requestAnimationFrame(() => {
				try {
					fn && fn();
				} catch (_) {}
			});
		} catch (_) {
			setTimeout(() => {
				try {
					fn && fn();
				} catch (__) {}
			}, 0);
		}
	}

	// Bring toggle into view with minimal scroll (upwards if it moved above after collapse).
	_scrollToggleIntoView(toggleEl) {
		if (!toggleEl || !toggleEl.isConnected) return;
		try {
			if (runtime && runtime.scrollMgr) {
				runtime.scrollMgr.userInteracted = true;
				runtime.scrollMgr.autoFollow = false;
			}
		} catch (_) {}
		this._afterLayout(() => {
			try {
				if (toggleEl.scrollIntoView) {
					// Prefer minimal movement; keep behavior non-animated and predictable.
					try {
						toggleEl.scrollIntoView({
							block: 'nearest',
							inline: 'nearest',
							behavior: 'instant'
						});
					} catch (_) {
						toggleEl.scrollIntoView(false);
					}
				}
			} catch (_) {}
		});
	}

	// Ensure wrapper and toggle exist for a given .msg element.
	_ensureStructure(msg) {
		if (!msg || !msg.isConnected) return null;

		// Wrap all direct children into a dedicated content container to measure height accurately.
		let content = msg.querySelector('.uc-content');
		if (!content) {
			content = document.createElement('div');
			content.className = 'uc-content';
			const frag = document.createDocumentFragment();
			while (msg.firstChild) frag.appendChild(msg.firstChild);
			content.appendChild(frag);
			msg.appendChild(content);
		}

		// Ensure a single toggle exists (click and keyboard accessible).
		let toggle = msg.querySelector('.uc-toggle');
		if (!toggle) {
			const icons = this._icons();
			const labels = this._labels();

			toggle = document.createElement('div');
			toggle.className = 'uc-toggle';
			toggle.tabIndex = 0;
			toggle.setAttribute('role', 'button');
			toggle.setAttribute('aria-expanded', 'false');
			toggle.title = labels.expand;

			const img = document.createElement('img');
			img.className = 'uc-toggle-icon';
			img.alt = labels.expand;
			img.src = icons.expand;

			// Provide a sane default size even if CSS did not load yet (CSS will override when present).
			img.width = 26; // keep in sync with CSS fallback var(--uc-toggle-icon-size, 26px)
			img.height = 26; // ensures a consistent, non-tiny control from the first paint

			toggle.appendChild(img);

			// Attach local listeners (no global handler change; production-safe).
			toggle.addEventListener('click', (ev) => {
				ev.preventDefault();
				ev.stopPropagation();
				this.toggleFromToggle(toggle);
			});
			toggle.addEventListener('keydown', (ev) => {
				if (ev.key === 'Enter' || ev.key === ' ') {
					ev.preventDefault();
					ev.stopPropagation();
					this.toggleFromToggle(toggle);
				}
			}, {
				passive: false
			});

			msg.appendChild(toggle);
		}

		this._processed.add(msg);
		msg.dataset.ucInit = '1';
		return {
			content,
			toggle
		};
	}

	// Create or update the ellipsis indicator inside content (absolute in the bottom-right corner).
	_ensureEllipsisEl(msg, contentEl) {
		const content = contentEl || (msg && msg.querySelector('.uc-content'));
		if (!content) return null;

		// Ensure the content becomes a positioning context only when needed.
		if (getComputedStyle(content).position === 'static') {
			content.style.position = 'relative';
		}

		let dot = content.querySelector('.uc-ellipsis');
		if (!dot) {
			dot = document.createElement('span');
			dot.className = 'uc-ellipsis';
			dot.textContent = this.ellipsisText;
			// Inline, theme-agnostic styles; kept minimal and non-interactive.
			dot.style.position = 'absolute';
			dot.style.right = '0';
			dot.style.bottom = '0';
			dot.style.paddingLeft = '6px';
			dot.style.pointerEvents = 'none';
			dot.style.zIndex = '1';
			dot.style.fontWeight = '500';
			dot.style.opacity = '0.75';
			// Do not include in copy-to-clipboard.
			dot.setAttribute('aria-hidden', 'true');
			dot.setAttribute('data-copy-ignore', '1');

			content.appendChild(dot);
		}
		return dot;
	}

	// Show ellipsis only when there is hidden overflow (collapsed).
	_showEllipsis(msg, contentEl) {
		const dot = this._ensureEllipsisEl(msg, contentEl);
		if (dot) dot.style.display = 'inline';
	}
	
	// Hide and clean ellipsis when not needed (expanded or short content).
	_hideEllipsis(msg) {
		const content = msg && msg.querySelector('.uc-content');
		if (!content) return;
		const dot = content.querySelector('.uc-ellipsis');
		if (dot && dot.parentNode) {
			// Remove the indicator to avoid accidental copy/select and keep DOM lean.
			dot.parentNode.removeChild(dot);
		}
		// Drop positioning context when no indicator is present (keep styles minimal).
		try {
			if (content && content.style && content.querySelector('.uc-ellipsis') == null) {
				content.style.position = '';
			}
		} catch (_) {}
	}

	// Apply collapse to all user messages under root.
	apply(root) {
		const scope = root || document;
		let list;
		if (scope.nodeType === 1) list = scope.querySelectorAll('.msg-box.msg-user .msg');
		else list = document.querySelectorAll('.msg-box.msg-user .msg');
		if (!list || !list.length) return;

		for (let i = 0; i < list.length; i++) {
			const msg = list[i];
			const st = this._ensureStructure(msg);
			if (!st) continue;
			this._update(msg, st.content, st.toggle);
		}
	}

	// Update collapsed/expanded state depending on content height.
	_update(msg, contentEl, toggleEl) {
		const c = contentEl || (msg && msg.querySelector('.uc-content'));
		if (!msg || !c) return;

		// Special-case: when threshold = 0 (or '0'), auto-collapse is globally disabled.
		// We avoid any measurement, force the content to be fully expanded, and ensure the toggle is hidden.
		// This preserves public API while providing an explicit opt-out, without impacting existing behavior.
		if (this.threshold === 0 || this.threshold === '0') {
			const t = toggleEl || msg.querySelector('.uc-toggle');
			const labels = this._labels();

			// Ensure expanded state and remove any limiting classes.
			c.classList.remove('uc-collapsed');
			c.classList.remove('uc-expanded'); // No class => fully expanded by default CSS.
			msg.dataset.ucState = 'expanded';

			// Hide ellipsis in disabled mode.
			this._hideEllipsis(msg);

			// Hide toggle in disabled mode to avoid user interaction.
			if (t) {
				t.classList.remove('visible');
				t.setAttribute('aria-expanded', 'false');
				t.title = labels.expand;
				const img = t.querySelector('img');
				if (img) {
					img.alt = labels.expand;
				}
			}
			return; // Do not proceed with measuring or collapsing.
		}

		// Temporarily remove limiting classes for precise measurement.
		c.classList.remove('uc-collapsed');
		c.classList.remove('uc-expanded');

		const fullHeight = Math.ceil(c.scrollHeight);
		const labels = this._labels();
		const icons = this._icons();
		const t = toggleEl || msg.querySelector('.uc-toggle');

		if (fullHeight > this.threshold) {
			if (t) t.classList.add('visible');
			const desired = msg.dataset.ucState || 'collapsed';
			const expand = (desired === 'expanded');

			if (expand) {
				c.classList.add('uc-expanded');
				this._hideEllipsis(msg); // Expanded => no ellipsis
			} else {
				c.classList.add('uc-collapsed');
				this._showEllipsis(msg, c); // Collapsed => show ellipsis overlay
			}

			if (t) {
				const img = t.querySelector('img');
				if (img) {
					if (expand) {
						img.src = icons.collapse;
						img.alt = labels.collapse;
					} else {
						img.src = icons.expand;
						img.alt = labels.expand;
					}
				}
				t.setAttribute('aria-expanded', expand ? 'true' : 'false');
				t.title = expand ? labels.collapse : labels.expand;
			}
		} else {
			// Short content – ensure fully expanded and hide toggle + ellipsis.
			c.classList.remove('uc-collapsed');
			c.classList.remove('uc-expanded');
			msg.dataset.ucState = 'expanded';
			this._hideEllipsis(msg);
			if (t) {
				t.classList.remove('visible');
				t.setAttribute('aria-expanded', 'false');
				t.title = labels.expand;
			}
		}
	}

	// Toggle handler via the toggle element (div.uc-toggle).
	toggleFromToggle(toggleEl) {
		const msg = toggleEl && toggleEl.closest ? toggleEl.closest('.msg-box.msg-user .msg') : null;
		if (!msg) return;
		this.toggle(msg);
	}

	// Core toggle logic.
	toggle(msg) {
		if (!msg || !msg.isConnected) return;
		const c = msg.querySelector('.uc-content');
		if (!c) return;
		const t = msg.querySelector('.uc-toggle');
		const labels = this._labels();
		const icons = this._icons();

		const isCollapsed = c.classList.contains('uc-collapsed');
		if (isCollapsed) {
			// Expand – leave scroll as-is; remove ellipsis.
			c.classList.remove('uc-collapsed');
			c.classList.add('uc-expanded');
			msg.dataset.ucState = 'expanded';
			this._hideEllipsis(msg);
			if (t) {
				t.setAttribute('aria-expanded', 'true');
				t.title = labels.collapse;
				const img = t.querySelector('img');
				if (img) {
					img.src = icons.collapse;
					img.alt = labels.collapse;
				}
			}
		} else {
			// Collapse – apply classes, show ellipsis, then bring toggle into view (scroll up if needed).
			c.classList.remove('uc-expanded');
			c.classList.add('uc-collapsed');
			msg.dataset.ucState = 'collapsed';
			this._showEllipsis(msg, c);
			if (t) {
				t.setAttribute('aria-expanded', 'false');
				t.title = labels.expand;
				const img = t.querySelector('img');
				if (img) {
					img.src = icons.expand;
					img.alt = labels.expand;
				}
				// Follow the collapsing content upward – keep the toggle visible.
				this._scrollToggleIntoView(t);
			}
		}
	}

	// Optional public method to re-evaluate height after layout/resize.
	remeasureAll() {
		const arr = Array.from(this._processed || []);
		for (let i = 0; i < arr.length; i++) {
			const msg = arr[i];
			if (!msg || !msg.isConnected) {
				this._processed.delete(msg);
				continue;
			}
			this._update(msg);
		}
	}
}