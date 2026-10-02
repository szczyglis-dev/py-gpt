// Runtime constructs collaborators and manages application lifetime.
class Runtime {

	// ========================================
	// Composition
	// ========================================

	// Main runtime manager for the application.
	constructor() {
		this.cfg = new Config();
		this.logger = new Logger(this.cfg);

		this.dom = new DOMRefs();
		this.customMarkup = new CustomMarkup(this.cfg, this.logger);
		this.raf = new RafManager(this.cfg);

		// Ensure logger uses central RafManager for its internal tick pump.
		try {
			this.logger.bindRaf(this.raf);
		} catch (_) {}

		this.async = new AsyncRunner(this.cfg, this.raf);
		this.renderer = new MarkdownRenderer(this.cfg, this.customMarkup, this.logger, this.async, this.raf);

		this.math = new MathRenderer(this.cfg, this.raf, this.async);
		this.codeScroll = new CodeScrollState(this.cfg, this.raf);
		this.highlighter = new Highlighter(this.cfg, this.codeScroll, this.raf);
		this.scrollMgr = new ScrollManager(this.cfg, this.dom, this.raf);
		this.templates = new NodeTemplateEngine(this.cfg, this.logger);
		this.toolOutput = new ToolOutput(this.scrollMgr, {
			templates: this.templates,
			renderer: this.renderer,
			findStatusHost: (parentId, create) => this.workflows.workflowMessageHost(parentId, create)
		});
		this.loading = new Loading(this.dom);
		this.nodes = new NodesManager(this.dom, this.renderer, this.highlighter, this.math, this.toolOutput);
		this.bridge = new BridgeManager(this.cfg, this.logger);
		this.ui = new UIManager();
		this.stream = new StreamEngine(this.cfg, this.dom, this.renderer, this.math, this.highlighter, this.codeScroll, this.scrollMgr, this.raf, this.async, this.logger);
		this.streamQ = new StreamQueue(this.cfg, this.stream, this.scrollMgr, this.raf);
		this.events = new EventManager(this.cfg, this.dom, this.scrollMgr, this.highlighter, this.codeScroll, this.toolOutput, this.bridge, () => this.stream.code.activeCode);

		try {
			this.stream.fences.setCustomFenceSpecs(this.customMarkup.getSourceFenceSpecs());
		} catch (_) {}

		this.data = new DataReceiver(this.cfg, this.templates, this.nodes, this.scrollMgr);

		this.tips = null;
		this.streaming = new RuntimeStreaming(this);
		this.workflows = new RuntimeWorkflows(this);
		this.partials = new RuntimePartials(this);
		this.timeline = new RuntimeTimeline(this);
		this.turns = new RuntimeTurns(this);
		this.mutations = new RuntimeMutations(this);
		this.messages = new RuntimeMessages(this);
		this.view = new RuntimeView(this);

		this.renderer.hooks.observeNewCode = (root, opts) => this.highlighter.observeNewCode(root, opts, this.stream.code.activeCode);
		this.renderer.hooks.observeMsgBoxes = (root) => this.highlighter.observeMsgBoxes(root, (box) => {
			this.highlighter.observeNewCode(box, {
				deferLastIfStreaming: true,
				minLinesForLast: this.cfg.PROFILE_CODE.minLinesForHL,
				minCharsForLast: this.cfg.PROFILE_CODE.minCharsForHL
			}, this.stream.code.activeCode);
			this.codeScroll.initScrollableBlocks(box);
		});
		this.renderer.hooks.scheduleMathRender = (root) => {
			const mm = getMathMode();
			if (mm === 'idle') this.math.schedule(root);
			else if (mm === 'always') this.math.schedule(root, 0, true);
		};
		this.renderer.hooks.scanVisibleCodes = (root) => this.highlighter.scanVisibleCodesInRoot(root, this.stream.code.activeCode || null);
		this.renderer.hooks.codeScrollInit = (root) => this.codeScroll.initScrollableBlocks(root);
	}

	// ========================================
	// Application lifecycle
	// ========================================

	// Initialize runtime (called on DOMContentLoaded).
	init() {
		this.highlighter.initHLJS();
		this.dom.init();
		this.ui.ensureStickyHeaderStyle();

		this.tips = new TipsManager(this.dom);
		this.events.install();

		this.bridge.initQWebChannel(this.cfg.PID, (bridge) => {
			const onChunk = (name, chunk, type) => this.streaming.onChunk(name, chunk, type);
			const onNode = (payload) => this.messages.appendNode(payload);
			const onNodeReplace = (payload) => this.messages.replaceNodes(payload);
			const onNodeInput = (html) => this.messages.appendToInput(html);
			this.bridge.connect(onChunk, onNode, onNodeReplace, onNodeInput);
			try {
				this.logger.bindBridge(this.bridge.bridge || this.bridge);
			} catch (_) {}
		});

		this.renderer.init();
		try {
			const pendingMarkdown = this.renderer.renderPendingMarkdown(document);
			const virtualize = () => {
				try { this.scrollMgr.virtualization.scheduleMessageVirtualizationRefresh(); } catch (_) {}
			};
			if (pendingMarkdown && typeof pendingMarkdown.then === 'function') pendingMarkdown.then(virtualize);
			else virtualize();
		} catch (_) {
			try { this.scrollMgr.virtualization.scheduleMessageVirtualizationRefresh(); } catch (__) {}
		}

		this.highlighter.observeMsgBoxes(document, (box) => {
			this.highlighter.observeNewCode(box, {
				deferLastIfStreaming: true,
				minLinesForLast: this.cfg.PROFILE_CODE.minLinesForHL,
				minCharsForLast: this.cfg.PROFILE_CODE.minCharsForHL
			}, this.stream.code.activeCode);
			this.codeScroll.initScrollableBlocks(box);
		});
		this.highlighter.observeNewCode(document, {
			deferLastIfStreaming: true,
			minLinesForLast: this.cfg.PROFILE_CODE.minLinesForHL,
			minCharsForLast: this.cfg.PROFILE_CODE.minCharsForHL
		}, this.stream.code.activeCode);
		this.highlighter.scheduleScanVisibleCodes(this.stream.code.activeCode);

		this.tips.cycle();
		this.scrollMgr.updateScrollFab(true);
	}

	// Cleanup runtime and detach from DOM/bridge.
	cleanup() {
		this.tips.cleanup();
		try {
			this.bridge.disconnect();
		} catch (_) {}
		this.events.cleanup();
		this.highlighter.cleanup();
		this.math.cleanup();
		this.streamQ.clear();
		this.dom.cleanup();
	}

}
