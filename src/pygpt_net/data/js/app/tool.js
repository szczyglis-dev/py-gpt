// ==========================================================================
// Tool output
// ==========================================================================

class ToolOutput {

	// Placeholder for loader show (can be extended by host).
	showLoader() {
		return;
	}

	// Hide spinner elements in bot messages.
	hideLoader() {
		const elements = document.querySelectorAll('.msg-bot');
		if (elements.length > 0) elements.forEach(el => {
			const s = el.querySelector('.spinner');
			if (s) s.style.display = 'none';
		});
	}

	// Begins a new tool session.
	begin() {
		this.showLoader();
	}

	// Ends the current tool session.
	end() {
		this.hideLoader();
	}

	// Enables the tool output area.
	enable() {
		const els = document.querySelectorAll('.tool-output');
		if (els.length) els[els.length - 1].style.display = 'block';
	}

	// Disables the tool output area.
	disable() {
		const els = document.querySelectorAll('.tool-output');
		if (els.length) els[els.length - 1].style.display = 'none';
	}

	// Append tool output. Structured tool blocks keep the request intact and
	// append only to the Result section; legacy blocks keep the old HTML path.
	append(content) {
		this.hideLoader();
		this.enable();
		const els = document.querySelectorAll('.tool-output');
		if (els.length) {
			const contentEl = els[els.length - 1].querySelector('.content');
			if (!contentEl) return;
			const resultEl = contentEl.querySelector('.tool-output-result-data');
			if (resultEl) {
				resultEl.insertAdjacentText('beforeend', content == null ? '' : String(content));
			} else {
				contentEl.insertAdjacentHTML('beforeend', content == null ? '' : String(content));
			}
		}
	}

	// Replace tool output. Structured tool blocks replace only Result, keeping
	// the Tool request visible after expansion.
	update(content) {
		this.hideLoader();
		this.enable();
		const els = document.querySelectorAll('.tool-output');
		if (els.length) {
			const contentEl = els[els.length - 1].querySelector('.content');
			if (!contentEl) return;
			const resultEl = contentEl.querySelector('.tool-output-result-data');
			if (resultEl) {
				resultEl.textContent = content == null ? '' : String(content);
			} else {
				contentEl.innerHTML = content == null ? '' : String(content);
			}
		}
	}

	// Clear only Result in structured tool blocks; legacy blocks are cleared
	// exactly as before.
	clear() {
		this.hideLoader();
		this.enable();
		const els = document.querySelectorAll('.tool-output');
		if (els.length) {
			const contentEl = els[els.length - 1].querySelector('.content');
			if (!contentEl) return;
			const resultEl = contentEl.querySelector('.tool-output-result-data');
			if (resultEl) resultEl.replaceChildren();
			else contentEl.replaceChildren();
		}
	}
	
	// Toggle visibility of a specific tool output block by message id.
	toggle(id) {
		const el = document.getElementById('msg-bot-' + id);
		if (!el) return;
		const outputEl = el.querySelector('.tool-output');
		if (!outputEl) return;
		const contentEl = outputEl.querySelector('.content');
		if (!contentEl) return;

		const expanded = contentEl.style.display === 'none';
		contentEl.style.display = expanded ? 'block' : 'none';

		const headerEl = outputEl.querySelector('.tool-output-toggle');
		if (headerEl) headerEl.setAttribute('aria-expanded', expanded ? 'true' : 'false');

		const arrowEl = outputEl.querySelector('.tool-output-arrow') || outputEl.querySelector('.toggle-cmd-output img');
		if (arrowEl) arrowEl.classList.toggle('toggle-expanded', expanded);
	}
}