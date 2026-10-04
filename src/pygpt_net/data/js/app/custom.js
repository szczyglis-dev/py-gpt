// Compiles and selects rules; source and DOM transformations have separate owners.
class CustomMarkup {

	// ========================================
	// Composition
	// ========================================

	// Constructor: set config, logger and initialize internal caches/flags
	constructor(cfg, logger) {
		this.cfg = cfg || {
			CUSTOM_MARKUP_RULES: []
		};
		this.logger = logger || new Logger(cfg);

		// Compiled state
		this.compiledRules = null; // all rules
		this.streamRules = null; // subset of stream rules (cache)
		this.streamWrapRules = null; // subset: stream + html-phase, without open/closeReplace (cache)
		this.streamRulesAvailable = false; // quick flag

		// Quick tests for the presence of "open" (avoid O(N*M) indexOf on hot path)
		this._openReAll = null; // RegExp for all html-phase/both
		this._openReStream = null; // RegExp for stream html-phase/both
		this.source = new CustomMarkupSource(this);
		this.html = new CustomMarkupHtml(this);
		this.live = new CustomMarkupLive(this);

	}

	// ========================================
	// Markup rules and compilation
	// ========================================

	// Debug helper: write structured log lines for the stream engine.
	debug(tag, data) {
        try {
            const lg = this.logger || (this.cfg && this.cfg.logger) || (window.runtime && runtime.logger) || null;
            if (!lg || typeof lg.debug !== 'function') return;
            lg.debug_obj("CM", tag, data);
        } catch (_) {}
    }

	// Fast check if any "open" token from rules exists in text
	hasAnyOpenToken(text, rules) {
		if (!text || !rules || !rules.length) return false;
		if (rules === this.compiledRules && this._openReAll) {
			return this._openReAll.test(text);
		}
		if (rules === this.streamRules && this._openReStream) {
			return this._openReStream.test(text);
		}
		for (let i = 0; i < rules.length; i++) {
			const r = rules[i];
			if (!r || !r.open) continue;
			if (text.indexOf(r.open) !== -1) return true;
		}
		return false;
	}

	// fast check against stream rules’ open tokens
	hasAnyStreamOpenToken(text) {
		this.ensureCompiled();
		if (!this.streamRulesAvailable) return false;
		const t = String(text || '');
		if (this._openReStream) return this._openReStream.test(t);
		const rules = this.streamRules || [];
		return this.hasAnyOpenToken(t, rules);
	}

    // Compile rules from given array or config/global override
	compile(rules) {
		const src = Array.isArray(rules) ? rules :
			(window.CUSTOM_MARKUP_RULES || this.cfg.CUSTOM_MARKUP_RULES || []);
		const compiled = [];
		let hasStream = false;

		for (const r of src) {
			if (!r || typeof r.open !== 'string' || typeof r.close !== 'string') continue;

			const tag = (r.tag || 'span').toLowerCase();
			const className = (r.className || r.class || '').trim();
			const innerMode = (r.innerMode === 'markdown-inline' || r.innerMode === 'text') ? r.innerMode : 'text';

			const stream = !!(r.stream === true);
			const openReplace = String((r.openReplace != null ? r.openReplace : (r.openReplace || '')) || '');
			const closeReplace = String((r.closeReplace != null ? r.closeReplace : (r.closeReplace || '')) || '');

			const decodeEntities = (typeof r.decodeEntities === 'boolean') ?
				r.decodeEntities :
				((r.name || '').toLowerCase() === 'cmd' || className === 'cmd');

			let phaseRaw = (typeof r.phase === 'string') ? r.phase.toLowerCase() : '';
			if (phaseRaw !== 'source' && phaseRaw !== 'html' && phaseRaw !== 'both') phaseRaw = '';
			const looksLikeFence = (openReplace.indexOf('```') !== -1) || (closeReplace.indexOf('```') !== -1);
			const phase = phaseRaw || (looksLikeFence ? 'source' : 'html');

			const re = new RegExp(Utils.reEscape(r.open) + '([\\s\\S]*?)' + Utils.reEscape(r.close), 'g');
			const reFull = new RegExp('^' + Utils.reEscape(r.open) + '([\\s\\S]*?)' + Utils.reEscape(r.close) + '$');
			const reFullTrim = new RegExp('^\\s*' + Utils.reEscape(r.open) + '([\\s\\S]*?)' + Utils.reEscape(r.close) + '\\s*$');

			const nl2br = !!r.nl2br;
			const allowBr = !!r.allowBr;

			const item = {
				name: r.name || tag,
				tag,
				className,
				innerMode,
				open: r.open,
				close: r.close,
				decodeEntities,
				re,
				reFull,
				reFullTrim,
				stream,
				openReplace,
				closeReplace,
				phase,
				isSourceFence: looksLikeFence,
				nl2br,
				allowBr
			};
			compiled.push(item);
			if (stream) hasStream = true;
		}

		if (compiled.length === 0) {
			const open = '[!cmd]', close = '[/!cmd]';
			const item = {
				name: 'cmd',
				tag: 'p',
				className: 'cmd',
				innerMode: 'text',
				open,
				close,
				decodeEntities: true,
				re: new RegExp(Utils.reEscape(open) + '([\\s\\S]*?)' + Utils.reEscape(close), 'g'),
				reFull: new RegExp('^' + Utils.reEscape(open) + '([\\s\\S]*?)' + Utils.reEscape(close) + '$'),
				reFullTrim: new RegExp('^\\s*' + Utils.reEscape(open) + '([\\s\\S]*?)' + Utils.reEscape(close) + '\\s*$'),
				stream: false,
				openReplace: '',
				closeReplace: '',
				phase: 'html',
				isSourceFence: false,
				nl2br: false,
				allowBr: false
			};
			compiled.push(item);
		}

		this.compiledRules = compiled;
		this.streamRulesAvailable = hasStream;
		this.streamRules = compiled.filter(r => !!r.stream);
		this.streamWrapRules = this.streamRules.filter(
			r => (r.phase === 'html' || r.phase === 'both') && !(r.openReplace || r.closeReplace) && r.open && r.close
		);

		const htmlPhaseAll = compiled.filter(r => (r.phase === 'html' || r.phase === 'both'));
		const htmlPhaseStream = this.streamRules.filter(r => (r.phase === 'html' || r.phase === 'both'));
		this._openReAll = this._buildOpenRegex(htmlPhaseAll);
		this._openReStream = this._buildOpenRegex(htmlPhaseStream);

		this.debug('cm.compile', { rules: compiled.length, streamRules: this.streamRules.length });
		return compiled;
	}

    // Get specs of all source fence rules
	getSourceFenceSpecs() {
		this.ensureCompiled();
		const rules = this.compiledRules || [];
		const out = [];
		for (let i = 0; i < rules.length; i++) {
			const r = rules[i];
			if (!r || !r.isSourceFence) continue;
			if (r.phase !== 'source' && r.phase !== 'both') continue;
			out.push({ open: r.open, close: r.close });
		}
		return out;
	}

    // Ensure the rules are compiled (from global override or config)
	ensureCompiled() {
		if (!this.compiledRules) {
			this.compile(window.CUSTOM_MARKUP_RULES || this.cfg.CUSTOM_MARKUP_RULES);
		}
		return this.compiledRules;
	}

    // Set a new set of rules (overrides global and config)
	setRules(rules) {
		this.compile(rules);
		window.CUSTOM_MARKUP_RULES = Array.isArray(rules) ? rules.slice() :
			(this.cfg.CUSTOM_MARKUP_RULES || []).slice();
		this.debug('cm.setRules', { count: (window.CUSTOM_MARKUP_RULES || []).length });
	}

    // Get the current set of rules (from global override or config)
	getRules() {
		const list = (window.CUSTOM_MARKUP_RULES ? window.CUSTOM_MARKUP_RULES.slice() :
			(this.cfg.CUSTOM_MARKUP_RULES || []).slice());
		return list;
	}

    // Quick check if any stream rules are defined
	hasStreamRules() {
		this.ensureCompiled();
		return !!this.streamRulesAvailable;
	}

    // Quick check if text starts with any known stream opener
	hasStreamOpenerAtStart(text) {
		if (!text) return false;
		this.ensureCompiled();
		if (!this.streamRulesAvailable) return false;
		const rules = this.streamRules || [];
		if (!rules.length) return false;
		const t = String(text).trimStart();
		for (let i = 0; i < rules.length; i++) {
			const r = rules[i];
			if (!r || !r.open) continue;
			if (t.startsWith(r.open)) return true;
		}
		return false;
	}

	// ========================================
	// Markup rules and compilation internals
	// ========================================

    // Build a RegExp that matches any of the "open" tokens in the given rules
	_buildOpenRegex(rules) {
		if (!rules || !rules.length) return null;
		const tokens = [];
		let patternLen = 0;
		const LIMIT_TOKENS = 200;
		const LIMIT_PATTERN_LEN = 4000;

		for (const r of rules) {
			if (!r || !r.open) continue;
			const esc = Utils.reEscape(r.open);
			tokens.push(esc);
			patternLen += esc.length + 1;
			if (tokens.length > LIMIT_TOKENS || patternLen > LIMIT_PATTERN_LEN) return null;
		}
		if (!tokens.length) return null;
		tokens.sort((a, b) => b.length - a.length);
		try {
			return new RegExp('(?:' + tokens.join('|') + ')');
		} catch (_) {
			return null;
		}
	}

}
