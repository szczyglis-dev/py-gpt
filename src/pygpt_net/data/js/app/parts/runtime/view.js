// RuntimeView owns view behavior and state.
class RuntimeView {

	// ========================================
	// Composition
	// ========================================

	constructor(runtime) {
		this.runtime = runtime;
	}

	// ========================================
	// Tool output lifecycle
	// ========================================

	beginToolOutput = () => {
		this.runtime.workflows.hideReasoningForToolCall();
		this.runtime.toolOutput.begin();
	};

	// ========================================
	// Footer
	// ========================================

	updateFooter = (html) => {
		const el = this.runtime.dom.get('_footer_');
		if (el) el.innerHTML = html;
	};

	// ========================================
	// Scroll position
	// ========================================

	getScrollPosition = () => {
		this.runtime.bridge.updateScrollPosition(window.scrollY);
	};

	setScrollPosition = (pos) => {
		try {
			const top = Math.max(0, Number(pos) || 0);
			this.runtime.scrollMgr.markProgrammaticScroll(top);
			window.scrollTo(0, top);
			this.runtime.scrollMgr.prevScroll = top;
			this.runtime.scrollMgr.lastScrollTop = Utils.SE.scrollTop;
		} catch (_) {}
	};

	// ========================================
	// Markup configuration
	// ========================================

	setCustomMarkupRules = (rules) => {
		this.runtime.customMarkup.setRules(rules);
		// Keep StreamEngine in sync with rules producing fenced code
		try {
			this.runtime.stream.fences.setCustomFenceSpecs(this.runtime.customMarkup.getSourceFenceSpecs());
		} catch (_) {}
	};

}
