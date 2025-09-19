// ==========================================================================
// Bridge manager
// ==========================================================================

class BridgeManager {

	// Manages the connection to the bridge
	constructor(cfg, logger) {
		this.cfg = cfg;
		this.logger = logger || new Logger(cfg);
		this.bridge = null;
		this.connected = false;
	}

	// Log messages to the bridge
	log(text) {
		try {
			if (this.bridge && this.bridge.log) this.bridge.log(text);
		} catch (_) {}
	}

	// Connect to the bridge
	connect(onChunk, onNode, onNodeReplace, onNodeInput) {
		if (!this.bridge) return false;
		if (this.connected) return true;
		try {
			if (this.bridge.chunk) this.bridge.chunk.connect((name, chunk, type) => onChunk(name, chunk, type));
			if (this.bridge.node) this.bridge.node.connect(onNode);
			if (this.bridge.nodeReplace) this.bridge.nodeReplace.connect(onNodeReplace);
			if (this.bridge.nodeInput) this.bridge.nodeInput.connect(onNodeInput);
			this.connected = true;
			return true;
		} catch (e) {
			this.log(e);
			return false;
		}
	}

	// Disconnect from the bridge
	disconnect() {
		if (!this.bridge) return false;
		if (!this.connected) return true;
		try {
			if (this.bridge.chunk) this.bridge.chunk.disconnect();
			if (this.bridge.node) this.bridge.node.disconnect();
			if (this.bridge.nodeReplace) this.bridge.nodeReplace.disconnect();
			if (this.bridge.nodeInput) this.bridge.nodeInput.disconnect();
		} catch (_) {}
		this.connected = false;
		return true;
	}

	// Initialize the QWebChannel
	initQWebChannel(pid, onReady) {
		try {
			new QWebChannel(qt.webChannelTransport, (channel) => {
				this.bridge = channel.objects.bridge;
				try {
					this.logger.bindBridge(this.bridge);
				} catch (_) {}
				onReady && onReady(this.bridge);
				if (this.bridge && this.bridge.js_ready) this.bridge.js_ready(pid);
			});
		} catch (e) {
			/* swallow */
		}
	}

	// Copy code to the bridge
	copyCode(text) {
		if (this.bridge && this.bridge.copy_text) this.bridge.copy_text(text);
	}

	// Preview code in the bridge
	previewCode(text) {
		if (this.bridge && this.bridge.preview_text) this.bridge.preview_text(text);
	}

	// Run code in the bridge
	runCode(text) {
		if (this.bridge && this.bridge.run_text) this.bridge.run_text(text);
	}

	// Update the scroll position in the bridge
	updateScrollPosition(pos) {
		if (this.bridge && this.bridge.update_scroll_position) this.bridge.update_scroll_position(pos);
	}
}