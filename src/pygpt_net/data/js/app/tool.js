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

	// Append HTML into the latest tool-output content area.
	append(content) {
		this.hideLoader();
		this.enable();
		const els = document.querySelectorAll('.tool-output');
		if (els.length) {
			const contentEl = els[els.length - 1].querySelector('.content');
			if (contentEl) contentEl.insertAdjacentHTML('beforeend', content);
		}
	}

	// Replace inner HTML for the latest tool-output content area.
	update(content) {
		this.hideLoader();
		this.enable();
		const els = document.querySelectorAll('.tool-output');
		if (els.length) {
			const contentEl = els[els.length - 1].querySelector('.content');
			if (contentEl) contentEl.innerHTML = content;
		}
	}

	// Remove children from the latest tool-output content area.
	clear() {
		this.hideLoader();
		this.enable();
		const els = document.querySelectorAll('.tool-output');
		if (els.length) {
			const contentEl = els[els.length - 1].querySelector('.content');
			if (contentEl) contentEl.replaceChildren();
		}
	}
	
	// Toggle visibility of a specific tool output block by message id.
	toggle(id) {
		const el = document.getElementById('msg-bot-' + id);
		if (!el) return;
		const outputEl = el.querySelector('.tool-output');
		if (!outputEl) return;
		const contentEl = outputEl.querySelector('.content');
		if (contentEl) contentEl.style.display = (contentEl.style.display === 'none') ? 'block' : 'none';
		const toggleEl = outputEl.querySelector('.toggle-cmd-output img');
		if (toggleEl) toggleEl.classList.toggle('toggle-expanded');
	}
}