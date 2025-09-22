// ==========================================================================
// Config
// ==========================================================================

class Config {
	
	constructor() {
		// Process identifier (passed from host).
		this.PID = Utils.g('PID', 0);

		// UI: scroll behavior and busy/zoom signalling thresholds (milliseconds / pixels).
		this.UI = {
			AUTO_FOLLOW_REENABLE_PX: Utils.g('AUTO_FOLLOW_REENABLE_PX', 8),
			SCROLL_NEAR_MARGIN_PX: Utils.g('SCROLL_NEAR_MARGIN_PX', 450),
			INTERACTION_BUSY_MS: Utils.g('UI_INTERACTION_BUSY_MS', 140),
			ZOOM_BUSY_MS: Utils.g('UI_ZOOM_BUSY_MS', 300)
		};

		// FAB (floating action button) visibility and debounce.
		this.FAB = {
			SHOW_DOWN_THRESHOLD_PX: Utils.g('SHOW_DOWN_THRESHOLD_PX', 0),
			TOGGLE_DEBOUNCE_MS: Utils.g('FAB_TOGGLE_DEBOUNCE_MS', 100)
		};

		// Highlighting controls and per-frame budget.
		this.HL = {
			PER_FRAME: Utils.g('HL_PER_FRAME', 2),
			DISABLE_ALL: Utils.g('DISABLE_SYNTAX_HIGHLIGHT', false)
		};

		// Intersection-like margins (we do our own scan, but these guide budgets).
		this.OBSERVER = {
			CODE_ROOT_MARGIN: Utils.g('CODE_ROOT_MARGIN', '1000px 0px 1000px 0px'),
			BOX_ROOT_MARGIN: Utils.g('BOX_ROOT_MARGIN', '1500px 0px 1500px 0px'),
			CODE_THRESHOLD: [0, 0.001],
			BOX_THRESHOLD: 0
		};

		// Viewport scan preload distance (in pixels).
		this.SCAN = {
			PRELOAD_PX: Utils.g('SCAN_PRELOAD_PX', 1000)
		};

		// Code scroll behavior (auto-follow re-enable margin and near-bottom margin).
		this.CODE_SCROLL = {
			AUTO_FOLLOW_REENABLE_PX: Utils.g('CODE_AUTO_FOLLOW_REENABLE_PX', 8),
			NEAR_MARGIN_PX: Utils.g('CODE_SCROLL_NEAR_MARGIN_PX', 48)
		};

		// Stream (snapshot) budgets and queue limits.
		this.STREAM = {
			MAX_PER_FRAME: Utils.g('STREAM_MAX_PER_FRAME', 8),
			EMERGENCY_COALESCE_LEN: Utils.g('STREAM_EMERGENCY_COALESCE_LEN', 300),
			COALESCE_MODE: Utils.g('STREAM_COALESCE_MODE', 'fixed'),
			SNAPSHOT_MAX_STEP: Utils.g('STREAM_SNAPSHOT_MAX_STEP', 8000),
			QUEUE_MAX_ITEMS: Utils.g('STREAM_QUEUE_MAX_ITEMS', 1200),
			PRESERVE_CODES_MAX: Utils.g('STREAM_PRESERVE_CODES_MAX', 120),

			// switch to plain text after this many lines without markdown tokens
			PLAIN_ACTIVATE_AFTER_LINES: Utils.g('STREAM_PLAIN_ACTIVATE_AFTER_LINES', 80),
		};

		// Math (KaTeX) idle batching and per-batch hint.
		this.MATH = {
			IDLE_TIMEOUT_MS: Utils.g('MATH_IDLE_TIMEOUT_MS', 800),
			BATCH_HINT: Utils.g('MATH_BATCH_HINT', 24)
		};

		// Icon URLs (provided by host app).
		this.ICONS = {
			EXPAND: Utils.g('ICON_EXPAND', ''),
			COLLAPSE: Utils.g('ICON_COLLAPSE', ''),
			CODE_MENU: Utils.g('ICON_CODE_MENU', ''),
			CODE_COPY: Utils.g('ICON_CODE_COPY', ''),
			CODE_RUN: Utils.g('ICON_CODE_RUN', ''),
			CODE_PREVIEW: Utils.g('ICON_CODE_PREVIEW', '')
		};

		// Localized UI strings.
		this.LOCALE = {
			PREVIEW: Utils.g('LOCALE_PREVIEW', 'Preview'),
			RUN: Utils.g('LOCALE_RUN', 'Run'),
			COLLAPSE: Utils.g('LOCALE_COLLAPSE', 'Collapse'),
			EXPAND: Utils.g('LOCALE_EXPAND', 'Expand'),
			COPY: Utils.g('LOCALE_COPY', 'Copy'),
			COPIED: Utils.g('LOCALE_COPIED', 'Copied')
		};

		// Code block styling theme (hljs theme key or custom).
		this.CODE_STYLE = Utils.g('CODE_SYNTAX_STYLE', 'default');

		// Adaptive snapshot profile for plain text.
		this.PROFILE_TEXT = {
			base: Utils.g('PROFILE_TEXT_BASE', 4),
			growth: Utils.g('PROFILE_TEXT_GROWTH', 1.28),
			minInterval: Utils.g('PROFILE_TEXT_MIN_INTERVAL', 4),
			softLatency: Utils.g('PROFILE_TEXT_SOFT_LATENCY', 60),
			adaptiveStep: Utils.g('PROFILE_TEXT_ADAPTIVE_STEP', false)
		};

		// Adaptive snapshot profile for code (line-aware).
		this.PROFILE_CODE = {
			base: 2048,
			growth: 2.6,
			minInterval: 500,
			softLatency: 1200,
			minLinesForHL: Utils.g('PROFILE_CODE_HL_N_LINE', 25),
			minCharsForHL: Utils.g('PROFILE_CODE_HL_N_CHARS', 5000),
			promoteMinInterval: 300,
			promoteMaxLatency: 800,
			promoteMinLines: Utils.g('PROFILE_CODE_HL_N_LINE', 25),
			adaptiveStep: Utils.g('PROFILE_CODE_ADAPTIVE_STEP', false),
			stopAfterLines: Utils.g('PROFILE_CODE_STOP_HL_AFTER_LINES', 300),
			streamPlainAfterLines: 0,
			streamPlainAfterChars: 0,
			maxFrozenChars: 32000, // max chars to freeze DOM nodes in .hl-freeze
			finalHighlightMaxLines: Utils.g('PROFILE_CODE_FINAL_HL_MAX_LINES', 1500),
			finalHighlightMaxChars: Utils.g('PROFILE_CODE_FINAL_HL_MAX_CHARS', 350000)
		};

		// Debounce for heavy resets (ms).
		this.RESET = {
			HEAVY_DEBOUNCE_MS: Utils.g('RESET_HEAVY_DEBOUNCE_MS', 24)
		};

		// Logging caps (used by Logger).
		this.LOG = {
			MAX_QUEUE: Utils.g('LOG_MAX_QUEUE', 400),
			MAX_BYTES: Utils.g('LOG_MAX_BYTES', 256 * 1024),
			BATCH_MAX: Utils.g('LOG_BATCH_MAX', 64),
			RATE_LIMIT_PER_SEC: Utils.g('LOG_RATE_LIMIT_PER_SEC', 0)
		};

		// Async tuning for background work.
		this.ASYNC = {
			SLICE_MS: Utils.g('ASYNC_SLICE_MS', 12),
			MIN_YIELD_MS: Utils.g('ASYNC_MIN_YIELD_MS', 0),
			MD_NODES_PER_SLICE: Utils.g('ASYNC_MD_NODES_PER_SLICE', 12)
		};

		// RAF pump tuning (budget per frame).
		this.RAF = {
			FLUSH_BUDGET_MS: Utils.g('RAF_FLUSH_BUDGET_MS', 7),
			MAX_TASKS_PER_FLUSH: Utils.g('RAF_MAX_TASKS_PER_FLUSH', 120)
		};

		// Markdown tuning – allow/disallow indented code blocks.
		this.MD = {
			ALLOW_INDENTED_CODE: Utils.g('MD_ALLOW_INDENTED_CODE', false)
		};

		// Custom markup rules for simple tags in text.
		// NOTE: added nl2br + allowBr for think rules; rest unchanged.
		this.CUSTOM_MARKUP_RULES = Utils.g('CUSTOM_MARKUP_RULES', [{
				name: 'cmd',
				open: '[!cmd]',
				close: '[/!cmd]',
				tag: 'div',
				className: 'cmd',
				innerMode: 'text'
			},

			// Think (Markdown-style) – convert newlines to <br>, allow real <br> tokens; safe-escape everything else.
			{
				name: 'think_md',
				open: '[!think]',
				close: '[/!think]',
				tag: 'think',
				className: '',
				innerMode: 'text',
				nl2br: true,
				allowBr: true
			},

			// Think (HTML-style, streaming-friendly)
			{
				name: 'think_html',
				open: '<think>',
				close: '</think>',
				tag: 'think',
				className: '',
				innerMode: 'text',
				stream: true,
				nl2br: true,
				allowBr: true
			},

			{
				name: 'tool',
				open: '<tool>',
				close: '</tool>',
				tag: 'div',
				className: 'cmd',
				innerMode: 'text',
				stream: true
			},

			// Streams+final: convert [!exec]... into fenced python code BEFORE markdown-it
			{
				name: 'exec_md',
				open: '[!exec]',
				close: '[/!exec]',
				innerMode: 'text',
				stream: true,
				openReplace: '```python\n',
				closeReplace: '\n```',
				phase: 'source'
			},

			// Streams+final: convert <execute>...</execute> into fenced python code BEFORE markdown-it
			{
				name: 'exec_html',
				open: '<execute>',
				close: '</execute>',
				innerMode: 'text',
				stream: true,
				openReplace: '```python\n',
				closeReplace: '\n```',
				phase: 'source'
			}
		]);
	}
}