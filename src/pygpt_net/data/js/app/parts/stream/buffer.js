// StreamBuffer owns buffer behavior and state.
class StreamBuffer {

	// ========================================
	// Composition
	// ========================================

	constructor(cfg, debug = () => {}) {
		this.debug = debug;
		// Rope-like buffer: streamBuf holds the materialized prefix; _sbParts keeps recent tail parts; _sbLen tracks their length.
		this.streamBuf = '';
		this._sbParts = [];
		this._sbLen = 0;

		// NOTE: materialize tail only when it grows large, to avoid frequent huge string copies.
		this._tailMaterializeAt = ((cfg && cfg.STREAM && (cfg.STREAM.MATERIALIZE_TAIL_AT_LEN | 0)) || 262144); // 256 KiB

	}

	// ========================================
	// Buffer storage
	// ========================================

	// Append incoming chunk to the lightweight tail buffer.
	append(s) {
		if (!s) return;
		// DEBUG
		this.debug('chunk.append', {
			len: s.length,
			nl: Utils.countNewlines(s),
			head: String(s).slice(0, 160),
			tail: String(s).slice(-160),
			hasAngle: /[<>]/.test(String(s)),
			hasFenceToken: /```|~~~/.test(String(s))
		});
		// Store piece and increase length counter; join later to avoid frequent string copies.
		this._sbParts.push(s);
		this._sbLen += s.length;

		// NOTE: materialize tail only when it grows beyond the threshold to keep part count bounded.
		if (this._sbLen >= this._tailMaterializeAt) {
			this.materialize();
		}
	}

	// NOTE: materialize current tail parts into streamBuf only on demand (threshold/finish).
	materialize() {
		// DEBUG
		this.debug('tail.materialize', {
			streamBufLen: this.streamBuf.length,
			parts: this._sbParts.length,
			sbLen: this._sbLen
		});
		if (this._sbLen > 0) {
			this.streamBuf += (this._sbParts.length === 1 ? this._sbParts[0] : this._sbParts.join(''));
			this._sbParts.length = 0;
			this._sbLen = 0;
		}
	}

	// Return the current total streamed length (materialized + tail parts).
	getStreamLength() {
		return (this.streamBuf.length + this._sbLen);
	}

	// NOTE: Zero-copy: return full text without forcing a permanent concatenation into streamBuf.
	getStreamText() {
		// Join tail on the fly for the caller only.
		if (this._sbLen > 0) {
			return this.streamBuf + (this._sbParts.length === 1 ? this._sbParts[0] : this._sbParts.join(''));
		}
		return this.streamBuf;
	}

	// Compute delta since prevLen without materializing the whole buffer.
	// This avoids building large temporary strings when we only need the tail slice.
	getDeltaSince(prevLen) {
		// Fast bail-outs
		const total = this.getStreamLength();
		if (prevLen >= total) return '';
		const bufLen = this.streamBuf.length;

		// If prevLen is at or before the materialized prefix, delta is the whole current tail.
		if (prevLen <= bufLen) {
			if (this._sbLen === 0) return '';
			const out = (this._sbParts.length === 1 ? this._sbParts[0] : this._sbParts.join(''));
			// DEBUG (only if interesting)
			if (/[<>]/.test(out)) this.debug('delta.since', {
				prevLen,
				deltaLen: out.length,
				head: out.slice(0, 80),
				tail: out.slice(-80)
			});
			return out;
		}

		// Otherwise delta starts inside the tail parts.
		let off = prevLen - bufLen;
		let out = null; // lazy array to minimize allocations
		for (let i = 0; i < this._sbParts.length; i++) {
			const p = this._sbParts[i];
			const plen = p.length;
			if (off >= plen) {
				off -= plen;
				continue;
			}
			const slice = off > 0 ? p.slice(off) : p;
			if (out === null) out = [slice];
			else out.push(slice);
			off = 0;
		}
		if (!out) return '';
		const ret = (out.length === 1 ? out[0] : out.join(''));
		// DEBUG (only if interesting)
		if (/[<>]/.test(ret)) this.debug('delta.since', {
			prevLen,
			deltaLen: ret.length,
			head: ret.slice(0, 80),
			tail: ret.slice(-80)
		});
		return ret;
	}

	// Drop all buffers (materialized and tail).
	clear() {
		// DEBUG
		this.debug('buf.clear', {
			streamBufLen: this.streamBuf.length,
			parts: this._sbParts.length,
			sbLen: this._sbLen
		});
		this.streamBuf = '';
		this._sbParts.length = 0;
		this._sbLen = 0;
	}

}
