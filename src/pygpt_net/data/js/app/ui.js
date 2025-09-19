// ==========================================================================
// UI manager
// ==========================================================================

class UIManager {

	// Replace or insert app-level CSS in a <style> tag.
	updateCSS(styles) {
		let style = document.getElementById('app-style');
		if (!style) {
			style = document.createElement('style');
			style.id = 'app-style';
			document.head.appendChild(style);
		}
		style.textContent = styles;
	}

	// Ensure base styles for code header sticky behavior exist.
	ensureStickyHeaderStyle() {
		let style = document.getElementById('code-sticky-style');
		if (style) return;
		style = document.createElement('style');
		style.id = 'code-sticky-style';
		style.textContent = [
			'.code-wrapper { position: relative; }',
			'.code-wrapper .code-header-wrapper { position: sticky; top: var(--code-header-sticky-top, -2px); z-index: 2; box-shadow: 0 1px 0 rgba(0,0,0,.06); }',
			'.code-wrapper pre { overflow: visible; margin-top: 0; }',
			'.code-wrapper pre code { display: block; white-space: pre; max-height: 100dvh; overflow: auto;',
			'  overscroll-behavior: contain; -webkit-overflow-scrolling: touch; overflow-anchor: none; scrollbar-gutter: stable both-edges; scroll-behavior: auto; }',
			'#_loader_.hidden { display: none !important; visibility: hidden !important; }',
			'#_loader_.visible { display: block; visibility: visible; }',

			/* User message collapse (uc-*) */
			'.msg-box.msg-user .msg { position: relative; }',
			'.msg-box.msg-user .msg > .uc-content { display: block; overflow: visible; }',
			'.msg-box.msg-user .msg > .uc-content.uc-collapsed { max-height: 1000px; overflow: hidden; }',
			'.msg-box.msg-user .msg > .uc-toggle { display: none; margin-top: 8px; text-align: center; cursor: pointer; user-select: none; }',
			'.msg-box.msg-user .msg > .uc-toggle.visible { display: block; }',

			/* Increased toggle icon size to a comfortable/default size.
			   Overridable via CSS var --uc-toggle-icon-size to keep host-level control. */
			'.msg-box.msg-user .msg > .uc-toggle img { width: var(--uc-toggle-icon-size, 26px); height: var(--uc-toggle-icon-size, 26px); opacity: .8; }',
			'.msg-box.msg-user .msg > .uc-toggle:hover img { opacity: 1; }',

			/* User copy icon – single icon, top-right, visible on hover/focus */
			'.msg-box.msg-user .msg .msg-copy-btn { position: absolute; top: 2px; right: 0px; z-index: 3;',
			'  opacity: 0; pointer-events: none; transition: opacity .15s ease, transform .15s ease, background-color .15s ease, border-color .15s ease;',
			'  border-radius: 6px; padding: 4px; line-height: 0; border: 1px solid transparent; background: transparent; }',
			'.msg-box.msg-user:hover .msg .msg-copy-btn, .msg-box.msg-user .msg:focus-within .msg-copy-btn { opacity: 1; pointer-events: auto; }',
			'.msg-box.msg-user .msg .msg-copy-btn:hover { transform: scale(1.06); background: var(--copy-btn-bg-hover, rgba(0,0,0,.86)); border-color: var(--copy-btn-border, rgba(0,0,0,.08)); }',
			'.msg-box.msg-user .msg .msg-copy-btn.copied { background: var(--copy-btn-bg-copied, rgba(150,150,150,.12)); border-color: var(--copy-btn-border-copied, rgba(150,150,150,.35)); animation: msg-copy-pop .25s ease; }',
			'.msg-box.msg-user .msg .msg-copy-btn img { display: block; width: 18px; height: 18px; }',

			/* Code header action hover and click feedback (icon-only, bot messages/code blocks) */
			'.code-wrapper .code-header-action.code-header-copy,',
			'.code-wrapper .code-header-action.code-header-collapse { display: inline-flex; align-items: center; border-radius: 6px; padding: 2px; line-height: 0; border: 1px solid transparent; transition: transform .15s ease, background-color .15s ease, border-color .15s ease; }',
			'.code-wrapper .code-header-action.code-header-copy:hover,',
			'.code-wrapper .code-header-action.code-header-collapse:hover { transform: scale(1.06); background: var(--copy-btn-bg-hover, rgba(0,0,0,.76)); border-color: var(--copy-btn-border, rgba(0,0,0,.08)); }',
			'.code-wrapper .code-header-action.copied { background: var(--copy-btn-bg-copied, rgba(150,150,150,.12)); border-color: var(--copy-btn-border-copied, rgba(150,150,150,.35)); animation: msg-copy-pop .25s ease; }',

			/* Small scale pop when copied */
			'@keyframes msg-copy-pop { 0%{ transform: scale(1); } 60%{ transform: scale(1.1); } 100%{ transform: scale(1); } }'
		].join('\n');
		document.head.appendChild(style);
	}
	
	// Toggle classes controlling optional UI features.
	enableEditIcons() {
		document.body && document.body.classList.add('display-edit-icons');
	}
	disableEditIcons() {
		document.body && document.body.classList.remove('display-edit-icons');
	}
	enableTimestamp() {
		document.body && document.body.classList.add('display-timestamp');
	}
	disableTimestamp() {
		document.body && document.body.classList.remove('display-timestamp');
	}
	enableBlocks() {
		document.body && document.body.classList.add('display-blocks');
	}
	disableBlocks() {
		document.body && document.body.classList.remove('display-blocks');
	}
}