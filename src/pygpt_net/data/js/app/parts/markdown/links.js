class MarkdownLinkPolicy {

	// ========================================
	// Links
	// ========================================

	install(md) {
		// Patch validateLink to allow additional safe schemes in this app
		const orig = (md && typeof md.validateLink === 'function') ? md.validateLink.bind(md) : null;
		md.validateLink = (url) => {
			try {
				const s = String(url || '').trim().toLowerCase();
				if (s.startsWith('file:')) return true; // local files
				if (s.startsWith('qrc:')) return true; // Qt resources
				if (s.startsWith('bridge:')) return true; // app bridge scheme
				if (s.startsWith('blob:')) return true; // blobs
				if (s.startsWith('data:image/')) return true; // inline images
			} catch (_) {}
			return orig ? orig(url) : true;
		};
	}

}
