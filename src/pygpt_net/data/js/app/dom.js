// ==========================================================================
// DOM references (memory-aware, leak-safe, with safe header HTML)
// ==========================================================================

class DOMRefs {

  // Caches DOM elements by ID and keeps ephemeral references weak.
  constructor() {
    // Strong cache for fixed, top-level nodes by id (safe to keep for app lifetime).
    this.els = Object.create(null);

    // Ephemeral references are stored as WeakRef to avoid retaining large subtrees.
    this._domOutputStreamRef = null; // WeakRef<HTMLDivElement> for '_append_output_'
    this._domStreamMsgRef = null;    // WeakRef<HTMLDivElement> for current '.msg'
    this._domStreamBoxRef = null;    // WeakRef<HTMLDivElement> for current '.msg-box'
  }

  // Cache frequently used elements by id (strong refs to fixed layout nodes).
  init() {
    const ids = [
      'container', '_nodes_', '_append_input_', '_append_output_before_', '_append_output_',
      '_append_live_', '_footer_', '_loader_', 'tips', 'scrollFab', 'scrollFabIcon'
    ];
    for (let i = 0; i < ids.length; i++) {
      const id = ids[i];
      const el = document.getElementById(id);
      if (el) this.els[id] = el;
    }
  }

  // Returns a strong cached element by id (and updates cache if it was not present).
  get(id) {
    let el = this.els[id];
    if (el && el.isConnected) return el;
    el = document.getElementById(id);
    if (el) this.els[id] = el;
    return el || null;
  }

  // Reset ephemeral pointers (used during stream).
  resetEphemeral() {
    this._domStreamMsgRef = null;
    this._domStreamBoxRef = null;
  }

  // Release refs and restore default scroll behavior.
  cleanup() {
    this.resetEphemeral();
    this._domOutputStreamRef = null;
    this.els = Object.create(null);
    try { history.scrollRestoration = "auto"; } catch (_) {}
  }

  // Dereference a WeakRef safely.
  _deref(ref) {
    if (!ref || typeof ref.deref !== 'function') return null;
    try {
      const el = ref.deref();
      return (el && el.isConnected) ? el : null;
    } catch (_) {
      return null;
    }
  }

  // Replace content of a container quickly (no innerHTML, minimal GC pressure).
  fastClear(id) {
    const el = this.get(id);
    if (!el) return null;
    if (el.firstChild) {
      if (typeof el.replaceChildren === 'function') el.replaceChildren();
      else el.textContent = '';
    }
    return el;
  }

  // Clear and ensure paint on next frame (await before reading layout).
  async fastClearAndPaint(id) {
    const el = this.fastClear(id);
    if (!el) return null;
    try {
      if (typeof runtime !== 'undefined' && runtime.raf && typeof runtime.raf.nextFrame === 'function') {
        await runtime.raf.nextFrame();
      } else if (typeof requestAnimationFrame === 'function') {
        await new Promise(res => requestAnimationFrame(() => res()));
      } else {
        await new Promise(res => setTimeout(res, 16));
      }
    } catch (_) {}
    return el;
  }

  // Hard clear by temporarily hiding element to avoid intermediate paints.
  fastClearHidden(id) {
    const el = this.get(id);
    if (!el) return null;
    const prevDisplay = el.style.display;
    el.style.display = 'none'; // pause paints
    if (typeof el.replaceChildren === 'function') el.replaceChildren();
    else el.textContent = '';
    el.style.display = prevDisplay; // resume paints
    return el;
  }

  // Replace element node by a shallow clone (drops children).
  hardReplaceByClone(id) {
    const el = this.get(id);
    if (!el || !el.parentNode) return null;
    const clone = el.cloneNode(false);
    try {
      el.replaceWith(clone);
    } catch (_) {
      el.textContent = '';
      return el;
    }
    this.els[id] = clone;
    if (id === '_append_output_') {
      this._domOutputStreamRef = (typeof WeakRef !== 'undefined') ? new WeakRef(clone) : null;
    }
    return clone;
  }

  // Clear streaming containers and transient state.
  hardResetStreamContainers() {
    this.resetEphemeral();
    this._domOutputStreamRef = null;
    this.fastClearHidden('_append_output_before_');
    this.fastClearHidden('_append_output_');
  }

  // Return output stream container, caching a weak reference.
  getStreamContainer() {
    let el = this._deref(this._domOutputStreamRef);
    if (el) return el;
    el = this.get('_append_output_');
    if (el) this._domOutputStreamRef = (typeof WeakRef !== 'undefined') ? new WeakRef(el) : null;
    return el;
  }

  // Allow-list sanitizer for header fragment (keeps img/span/strong/em, strips others).
  _sanitizeHeaderFragment(root) {
    const ALLOWED = new Set(['IMG', 'SPAN', 'STRONG', 'EM']);
    const ALLOWED_ATTR = {
      IMG: new Set(['src', 'alt', 'class', 'width', 'height', 'loading', 'decoding']),
      SPAN: new Set(['class']),
      STRONG: new Set([]),
      EM: new Set([])
    };
    const isAllowedSrc = (src) => {
      if (!src || typeof src !== 'string') return false;
      const s = src.trim().toLowerCase();
      // Allow typical local/embedded schemes used in this app and safe web protocols.
      if (s.startsWith('file:')) return true;
      if (s.startsWith('qrc:')) return true;
      if (s.startsWith('bridge:')) return true;
      if (s.startsWith('blob:')) return true;
      if (s.startsWith('data:image/')) return true;
      if (s.startsWith('http:')) return true;
      if (s.startsWith('https:')) return true;
      // Allow relative paths
      if (!/^[a-z0-9.+-]+:/.test(s)) return true;
      return false;
    };

    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT, null);
    const toRemove = [];
    while (walker.nextNode()) {
      const el = walker.currentNode;
      const tag = el.tagName;
      if (!ALLOWED.has(tag)) {
        toRemove.push(el);
        continue;
      }
      // Prune attributes
      const allowAttrs = ALLOWED_ATTR[tag];
      for (let i = el.attributes.length - 1; i >= 0; i--) {
        const a = el.attributes[i];
        if (!allowAttrs.has(a.name)) el.removeAttribute(a.name);
      }
      if (tag === 'IMG') {
        const src = el.getAttribute('src') || '';
        if (!isAllowedSrc(src)) {
          toRemove.push(el);
          continue;
        }
        // Add safe defaults
        if (!el.hasAttribute('loading')) el.setAttribute('loading', 'lazy');
        if (!el.hasAttribute('decoding')) el.setAttribute('decoding', 'async');
      }
    }
    // Replace stripped elements with their textContent to preserve readable header if any.
    for (const el of toRemove) {
      const txt = el.textContent || '';
      const tn = document.createTextNode(txt);
      try { el.replaceWith(tn); } catch (_) {}
    }
  }

  // Safely set header HTML (allows only minimal inline markup including <img>).
  _setHeaderHTML(container, html) {
    if (!container) return;
    const s = String(html || '');
    // Fast path: no tags => plain text
    if (s.indexOf('<') === -1 && s.indexOf('&') === -1) {
      container.textContent = s;
      return;
    }
    const tpl = document.createElement('template');
    tpl.innerHTML = s;
    const frag = tpl.content;
    try {
      this._sanitizeHeaderFragment(frag);
      container.replaceChildren(frag);
    } catch (_) {
      // Fallback to plain text for absolute safety.
      container.textContent = s.replace(/<[^>]*>/g, '');
    }
  }

  // Get or create current streaming message container (.msg-box > .msg > .md-snapshot-root).
  getStreamMsg(create, name_header) {
    const container = this.getStreamContainer();
    if (!container) return null;

    // Fast path: return cached current message if still connected.
    let msg = this._deref(this._domStreamMsgRef);
    if (msg) return msg;

    // Try known current box first (if any).
    let box = this._deref(this._domStreamBoxRef);

    // If no current box is known, locate an existing one.
    if (!box) {
      try { box = container.querySelector('.msg-box'); } catch (_) { box = null; }
    }

    // Create a new streaming box if none is present and requested by 'create'.
    if (!box && create) {
      const frag = document.createDocumentFragment();

      const newBox = document.createElement('div');
      newBox.classList.add('msg-box', 'msg-bot');

      if (name_header) {
        const name = document.createElement('div');
        name.classList.add('name-header', 'name-bot');
        // Safe header HTML (keeps <img> and simple inline tags).
        this._setHeaderHTML(name, name_header);
        newBox.appendChild(name);
      }

      const newMsg = document.createElement('div');
      newMsg.classList.add('msg');

      const snap = document.createElement('div');
      snap.className = 'md-snapshot-root';
      newMsg.appendChild(snap);

      newBox.appendChild(newMsg);
      frag.appendChild(newBox);
      container.appendChild(frag);

      this._domStreamBoxRef = (typeof WeakRef !== 'undefined') ? new WeakRef(newBox) : null;
      this._domStreamMsgRef = (typeof WeakRef !== 'undefined') ? new WeakRef(newMsg) : null;

      return newMsg;
    }

    // If a box exists but has no .msg or .md-snapshot-root, ensure it.
    if (box) {
      try { msg = box.querySelector('.msg'); } catch (_) { msg = null; }
      if (!msg) {
        msg = document.createElement('div');
        msg.classList.add('msg');
        box.appendChild(msg);
      }
      if (!msg.querySelector('.md-snapshot-root')) {
        const snap = document.createElement('div');
        snap.className = 'md-snapshot-root';
        msg.appendChild(snap);
      }
      this._domStreamBoxRef = (typeof WeakRef !== 'undefined') ? new WeakRef(box) : null;
      this._domStreamMsgRef = (typeof WeakRef !== 'undefined') ? new WeakRef(msg) : null;
    }

    return msg || null;
  }

  // Clear the "before" area (older messages area).
  clearStreamBefore() {
    try {
      if (typeof window.hideTips === 'function') window.hideTips();
    } catch (_) {}
    this.fastClearHidden('_append_output_before_');
  }

  // Clear output stream area.
  clearOutput() {
    this.hardResetStreamContainers();
  }

  // Clear messages list and reset state.
  clearNodes() {
    this.clearStreamBefore();
    const el = this.fastClearHidden('_nodes_');
    if (el) el.classList.add('empty_list');
    this.resetEphemeral();
  }

  // Clear input area.
  clearInput() {
    this.fastClearHidden('_append_input_');
  }

  // Clear live area and hide it.
  clearLive() {
    const el = this.fastClearHidden('_append_live_');
    if (!el) return;
    el.classList.remove('visible');
    el.classList.add('hidden');
    this.resetEphemeral();
  }
}