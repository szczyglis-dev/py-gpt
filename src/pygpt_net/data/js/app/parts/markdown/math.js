class MarkdownMathRules {

	// ========================================
	// Math
	// ========================================

	install(md) {
		const escapeHtml = Utils.escapeHtml;
		// ------------------ Math (placeholders) ------------------
		// Plugin that recognizes $...$ and $$...$$ and emits safe placeholders
		const mathDollarPlaceholderPlugin = (md) => {
			function notEscaped(src, pos) {
				let back = 0;
				while (pos - back - 1 >= 0 && src.charCodeAt(pos - back - 1) === 0x5C) back++;
				return (back % 2) === 0;
			}

			function math_block_dollar(state, startLine, endLine, silent) {
				const pos = state.bMarks[startLine] + state.tShift[startLine];
				const max = state.eMarks[startLine];
				if (pos + 1 >= max) return false;
				if (state.src.charCodeAt(pos) !== 0x24 || state.src.charCodeAt(pos + 1) !== 0x24) return false;
				let nextLine = startLine + 1,
					found = false;
				for (; nextLine < endLine; nextLine++) {
					let p = state.bMarks[nextLine] + state.tShift[nextLine];
					const pe = state.eMarks[nextLine];
					if (p + 1 < pe && state.src.charCodeAt(p) === 0x24 && state.src.charCodeAt(p + 1) === 0x24) {
						found = true;
						break;
					}
				}
				if (!found) return false;
				if (silent) return true;
				const contentStart = state.bMarks[startLine] + state.tShift[startLine] + 2;
				const contentEndLine = nextLine - 1;
				let content = '';
				if (contentEndLine >= startLine + 1) {
					const startIdx = state.bMarks[startLine + 1];
					const endIdx = state.eMarks[contentEndLine];
					content = state.src.slice(startIdx, endIdx);
				}
				const token = state.push('math_block_dollar', '', 0);
				token.block = true;
				token.content = content;
				state.line = nextLine + 1;
				return true;
			}

			function math_inline_dollar(state, silent) {
				const pos = state.pos,
					src = state.src,
					max = state.posMax;
				if (pos >= max) return false;
				if (src.charCodeAt(pos) !== 0x24) return false;
				if (pos + 1 < max && src.charCodeAt(pos + 1) === 0x24) return false;
				const after = pos + 1 < max ? src.charCodeAt(pos + 1) : 0;
				if (after === 0x20 || after === 0x0A || after === 0x0D) return false;
				let i = pos + 1;
				while (i < max) {
					const ch = src.charCodeAt(i);
					if (ch === 0x24 && notEscaped(src, i)) {
						const before = i - 1 >= 0 ? src.charCodeAt(i - 1) : 0;
						if (before === 0x20 || before === 0x0A || before === 0x0D) {
							i++;
							continue;
						}
						break;
					}
					i++;
				}
				if (i >= max || src.charCodeAt(i) !== 0x24) return false;
				if (!silent) {
					const token = state.push('math_inline_dollar', '', 0);
					token.block = false;
					token.content = src.slice(pos + 1, i);
				}
				state.pos = i + 1;
				return true;
			}
			md.block.ruler.before('fence', 'math_block_dollar', math_block_dollar, {
				alt: ['paragraph', 'reference', 'blockquote', 'list']
			});
			md.inline.ruler.before('escape', 'math_inline_dollar', math_inline_dollar);
			md.renderer.rules.math_inline_dollar = (tokens, idx) => {
				const tex = tokens[idx].content || '';
				return `<span class="math-pending" data-display="0"><span class="math-fallback">$${escapeHtml(tex)}$</span><script type="math/tex">${escapeHtml(tex)}</script></span>`;
			};
			md.renderer.rules.math_block_dollar = (tokens, idx) => {
				const tex = tokens[idx].content || '';
				return `<div class="math-pending" data-display="1"><div class="math-fallback">$$${escapeHtml(tex)}$$</div><script type="math/tex; mode=display">${escapeHtml(tex)}</script></div>`;
			};
		};

		// \( ... \) and \[ ... \] math delimiters (TeX style)
		const mathBracketsPlaceholderPlugin = (md) => {
			function math_brackets(state, silent) {
				const src = state.src,
					pos = state.pos,
					max = state.posMax;
				if (pos + 1 >= max || src.charCodeAt(pos) !== 0x5C) return false;
				const next = src.charCodeAt(pos + 1);
				if (next !== 0x28 && next !== 0x5B) return false;
				const isInline = (next === 0x28);
				const close = isInline ? '\\)' : '\\]';
				const start = pos + 2;
				const end = src.indexOf(close, start);
				if (end < 0) return false;
				const content = src.slice(start, end);
				if (!silent) {
					const t = state.push(isInline ? 'math_inline_bracket' : 'math_block_bracket', '', 0);
					t.content = content;
					t.block = !isInline;
				}
				state.pos = end + 2;
				return true;
			}
			md.inline.ruler.before('escape', 'math_brackets', math_brackets);
			md.renderer.rules.math_inline_bracket = (tokens, idx) => {
				const tex = tokens[idx].content || '';
				return `<span class="math-pending" data-display="0"><span class="math-fallback">\\(${escapeHtml(tex)}\\)</span><script type="math/tex">${escapeHtml(tex)}</script></span>`;
			};
			md.renderer.rules.math_block_bracket = (tokens, idx) => {
				const tex = tokens[idx].content || '';
				return `<div class="math-pending" data-display="1"><div class="math-fallback">\\${'['}${escapeHtml(tex)}\\${']'}</div><script type="math/tex; mode=display">${escapeHtml(tex)}</script></div>`;
			};
		};

		md.use(mathDollarPlaceholderPlugin);
		md.use(mathBracketsPlaceholderPlugin);
	}

}
