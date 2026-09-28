"""Shared in-page annotation editor, styling and overlay for canvas and chat."""
import json
import time
import weakref

from PySide6.QtCore import QTimer
from pygpt_net.utils import trans


CLEAR_ANNOTATION_CANVAS = False
CLEAR_ANNOTATION_CTX = True
CLEAR_ANNOTATION_FILE = True


def track_sent_annotations(ctx, owner, items):
    """Snapshot only annotations serialized into this request; do not clear yet."""
    if ctx is None or not items:
        return
    batches = getattr(ctx, '_sent_annotation_batches', None)
    if batches is None:
        batches = ctx._sent_annotation_batches = []
    batches.append((weakref.ref(owner), {(item['id'], item.get('time')) for item in items}))


def clear_sent_annotations(ctx):
    """Called on the UI thread after model output, including completed streams."""
    batches = getattr(ctx, '_sent_annotation_batches', None)
    if not isinstance(batches, list):
        return
    ctx._sent_annotation_batches = []
    for owner_ref, ids in batches:
        owner = owner_ref()
        if owner is not None:
            owner.clear_sent_annotations(ids)


class AnnotationMixin:
    annotation_source = "canvas_web"

    def clear_sent_annotations(self, ids):
        flags = {'canvas_web': CLEAR_ANNOTATION_CANVAS,
                 'chat': CLEAR_ANNOTATION_CTX, 'files': CLEAR_ANNOTATION_FILE}
        retained = [item for item in self.annotations
                    if (item['id'], item.get('time')) not in ids
                    or not flags.get(item.get('source', self.annotation_source), False)]
        if len(retained) != len(self.annotations):
            self.annotations = retained
            # Rebuild overlays as well: removed annotation cards must disappear.
            self._render_annotations()

    def annotate_selection(self, selected: str = "", position=None, backend=None):
        """Open the lightweight in-page annotation composer for current selection.

        QWebEngine JavaScript is deliberately asynchronous here. Context-menu
        actions run inside Chromium/Qt event handling, and nesting a QEventLoop
        while waiting for ``runJavaScript`` can stall for the full timeout.
        """
        x = int(position.x()) if position is not None else -1
        y = int(position.y()) if position is not None else -1
        self._show_annotation_editor(
            x=x,
            y=y,
            prefer_selection=True,
            selected_hint=str(selected or ""),
            backend=backend or self.backend,
        )

    def annotate_at(self, x: int, y: int, backend="qt"):
        """Open the in-page annotation composer for the element under (x, y)."""
        self._show_annotation_editor(
            x=int(x),
            y=int(y),
            prefer_selection=False,
            selected_hint="",
            backend=backend or self.backend,
        )

    def _annotation_editor_script(self, x: int, y: int, prefer_selection: bool, selected_hint: str, backend: str):
        """Return JS for the fast, non-modal annotation editor rendered in-page."""
        script = r"""(() => {
          const backend = __BACKEND__;
          const px = __X__, py = __Y__;
          const preferSelection = __PREFER_SELECTION__;
          const selectedHint = __SELECTED_HINT__;
          const old = document.getElementById('__pygpt_annotation_editor');
          if (old) old.remove();

          const ensureRef = (el) => {
            if (!el || el.nodeType !== Node.ELEMENT_NODE) return '';
            let ref = el.getAttribute('data-pygpt-ref');
            if (!ref) {
              ref = 'a' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
              el.setAttribute('data-pygpt-ref', ref);
            }
            return ref;
          };
          const descriptorFor = (el, rect, selectionRect) => {
            if (!el) return {};
            const r = rect || el.getBoundingClientRect();
            const ref = ensureRef(el);
            let stableSelector = '';
            if (backend === 'chat') {
              const path = [];
              for (let node = el; node && node.nodeType === Node.ELEMENT_NODE; node = node.parentElement) {
                if (node.id) {
                  path.unshift('#' + CSS.escape(node.id));
                  break;
                }
                const index = node.parentElement ? Array.from(node.parentElement.children).indexOf(node) + 1 : 1;
                path.unshift(node.tagName.toLowerCase() + ':nth-child(' + index + ')');
              }
              stableSelector = path.join(' > ');
            }
            const out = {
              tag: (el.tagName || '').toLowerCase(),
              id: el.id || '',
              className: String(el.className || ''),
              selector: ref ? '[data-pygpt-ref="' + ref + '"]' : '',
              stableSelector,
              text: (el.innerText || el.value || '').trim().slice(0, 500),
              x: Math.round(r.left || 0), y: Math.round(r.top || 0),
              width: Math.max(2, Math.round(r.width || 0)),
              height: Math.max(2, Math.round(r.height || 0))
            };
            if (selectionRect) out.selectionRect = selectionRect;
            return out;
          };

          let selection = '';
          let descriptor = {};
          let anchor = null;
          const sel = window.getSelection && window.getSelection();
          if (preferSelection && sel && sel.rangeCount > 0 && !sel.isCollapsed) {
            const range = sel.getRangeAt(0);
            const rr = range.getBoundingClientRect();
            let node = range.commonAncestorContainer;
            const el = node && node.nodeType === Node.ELEMENT_NODE ? node : node && node.parentElement;
            if (el && rr && (rr.width || rr.height)) {
              const tr = el.getBoundingClientRect();
              descriptor = descriptorFor(el, tr, {
                dx: Math.round(rr.left - tr.left), dy: Math.round(rr.top - tr.top),
                width: Math.max(2, Math.round(rr.width)), height: Math.max(2, Math.round(rr.height))
              });
              anchor = rr;
              selection = String(sel.toString() || selectedHint || '').trim().slice(0, 4000);
            }
          }
          if (!anchor) {
            const cx = px >= 0 ? px : Math.round(window.innerWidth / 2);
            const cy = py >= 0 ? py : Math.round(window.innerHeight / 2);
            const el = document.elementFromPoint(cx, cy) || document.body || document.documentElement;
            const r = el ? el.getBoundingClientRect() : {left:cx, top:cy, width:1, height:1, right:cx+1, bottom:cy+1};
            descriptor = descriptorFor(el, r, null);
            anchor = r;
            selection = String(selectedHint || '').trim().slice(0, 4000);
          }

          const editor = document.createElement('div');
          editor.id = '__pygpt_annotation_editor';
          editor.setAttribute('data-pygpt-ui', 'annotation-editor');
          Object.assign(editor.style, {
            position:'fixed', zIndex:'2147483647', width:'min(360px,calc(100vw - 20px))',
            boxSizing:'border-box', padding:'10px', background:'rgba(27,28,32,.98)',
            color:'#f7f7f8', border:'1px solid rgba(168,85,247,.9)', borderRadius:'10px',
            boxShadow:'0 12px 34px rgba(0,0,0,.38)', fontFamily:'system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
            fontSize:'12px', lineHeight:'1.35', pointerEvents:'auto'
          });
          const title = document.createElement('div');
          title.textContent = selection ? __TITLE_SELECTION__ : __TITLE_ELEMENT__;
          Object.assign(title.style, {fontWeight:'700', color:'#d8b4fe', margin:'0 0 7px 1px'});
          const textarea = document.createElement('textarea');
          textarea.placeholder = selection ? __PROMPT_SELECTION__ : __PROMPT_ELEMENT__;
          textarea.rows = 4;
          Object.assign(textarea.style, {
            display:'block', width:'100%', minHeight:'82px', maxHeight:'220px', resize:'vertical',
            boxSizing:'border-box', padding:'8px 9px', border:'1px solid rgba(255,255,255,.18)',
            borderRadius:'7px', outline:'none', background:'#17181b', color:'#fff',
            font:'12px/1.4 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'
          });
          const actions = document.createElement('div');
          Object.assign(actions.style, {display:'flex', justifyContent:'flex-end', gap:'7px', marginTop:'8px'});
          const button = (label, primary) => {
            const b = document.createElement('button');
            b.type = 'button'; b.textContent = label;
            Object.assign(b.style, {
              minWidth:'66px', height:'29px', padding:'0 10px', borderRadius:'6px', cursor:'pointer',
              border: primary ? '1px solid #8b5cf6' : '1px solid rgba(255,255,255,.18)',
              background: primary ? '#7c3aed' : '#2a2b30', color:'#fff', font:'600 12px system-ui,sans-serif'
            });
            return b;
          };
          const cancel = button(__CANCEL__, false);
          const add = button(__ADD__, true);
          actions.append(cancel, add);
          editor.append(title, textarea, actions);
          document.documentElement.appendChild(editor);

          const ew = Math.min(360, Math.max(240, window.innerWidth - 20));
          const eh = 178;
          let left = Math.max(10, Math.min(window.innerWidth - ew - 10, Number(anchor.left || 10)));
          let top = Number(anchor.bottom != null ? anchor.bottom : ((anchor.top || 10) + (anchor.height || 0))) + 10;
          if (top + eh > window.innerHeight - 10) top = Math.max(10, Number(anchor.top || 10) - eh - 10);
          editor.style.left = Math.round(left) + 'px';
          editor.style.top = Math.round(top) + 'px';

          const close = () => { if (editor.isConnected) editor.remove(); };
          cancel.onclick = (ev) => { ev.preventDefault(); ev.stopPropagation(); close(); };
          const submit = () => {
            const payload = {selection, element:descriptor, note:String(textarea.value || '')};
            close();
            try {
              if (backend === 'playwright' && typeof window.__pygpt_add_annotation === 'function') {
                window.__pygpt_add_annotation(payload);
              } else {
                console.info('__PYGPT_ANNOTATION_ADD__:' + JSON.stringify(payload));
              }
            } catch (_) {}
          };
          add.onclick = (ev) => { ev.preventDefault(); ev.stopPropagation(); submit(); };
          textarea.addEventListener('keydown', (ev) => {
            if ((ev.ctrlKey || ev.metaKey) && ev.key === 'Enter') { ev.preventDefault(); submit(); }
            else if (ev.key === 'Escape') { ev.preventDefault(); close(); }
          });
          setTimeout(() => textarea.focus({preventScroll:true}), 0);
          return true;
        })()"""
        return script.replace('__BACKEND__', json.dumps(str(backend or 'qt'))) \
            .replace('__X__', str(int(x))) \
            .replace('__Y__', str(int(y))) \
            .replace('__PREFER_SELECTION__', 'true' if prefer_selection else 'false') \
            .replace('__SELECTED_HINT__', json.dumps(str(selected_hint or ''), ensure_ascii=False)) \
            .replace('__TITLE_SELECTION__', json.dumps(trans('ui.annotate_selection', domain='plugin.canvas_web'), ensure_ascii=False)) \
            .replace('__TITLE_ELEMENT__', json.dumps(trans('ui.annotate_element', domain='plugin.canvas_web'), ensure_ascii=False)) \
            .replace('__PROMPT_SELECTION__', json.dumps(trans('ui.annotation_selection_prompt', domain='plugin.canvas_web'), ensure_ascii=False)) \
            .replace('__PROMPT_ELEMENT__', json.dumps(trans('ui.annotation_element_prompt', domain='plugin.canvas_web'), ensure_ascii=False)) \
            .replace('__CANCEL__', json.dumps(trans('ui.cancel', domain='plugin.canvas_web'), ensure_ascii=False)) \
            .replace('__ADD__', json.dumps(trans('ui.add', domain='plugin.canvas_web'), ensure_ascii=False))

    def add_annotation(self, selection=None, element=None, note=""):
        self.annotation_seq += 1
        item = {
            "id": self.annotation_seq, "time": time.time(), "url": self.current_url(),
            "source": self.annotation_source,
            "selection": selection or "", "element": element or {}, "note": str(note or ""),
        }
        self.annotations.append(item)
        max_items = max(1, int(self._opt("max_annotations", 30) or 30))
        if len(self.annotations) > max_items:
            del self.annotations[:-max_items]
        self._render_annotations()
        self.window.update_status(
            f"{trans('ui.annotation_added', domain='plugin.canvas_web')} #{self.annotation_seq}"
        )
        return item

    def handle_annotation_console(self, message):
        """Consume private QWebEngine JS bridge messages for annotation UI."""
        text = str(message or "")
        remove_prefix = "__PYGPT_ANNOTATION_REMOVE__:"
        add_prefix = "__PYGPT_ANNOTATION_ADD__:"

        if text.startswith(remove_prefix):
            try:
                annotation_id = int(text[len(remove_prefix):].strip())
            except Exception:
                return True
            QTimer.singleShot(0, lambda aid=annotation_id: self._remove_annotation(aid))
            return True

        if text.startswith(add_prefix):
            try:
                payload = json.loads(text[len(add_prefix):])
            except Exception:
                return True
            if not isinstance(payload, dict):
                return True
            data = {
                "selection": str(payload.get("selection") or ""),
                "element": payload.get("element") if isinstance(payload.get("element"), dict) else {},
                "note": str(payload.get("note") or ""),
            }
            QTimer.singleShot(0, lambda item=data: self.add_annotation(
                selection=item["selection"], element=item["element"], note=item["note"]
            ))
            return True

        return False

    def _remove_annotation(self, annotation_id: int):
        annotation_id = int(annotation_id)
        before = len(self.annotations)
        self.annotations = [x for x in self.annotations if int(x.get("id", -1)) != annotation_id]
        if len(self.annotations) == before:
            return False
        self._render_annotations()
        try:
            self.window.update_status(
                f"{trans('ui.annotation_removed', domain='plugin.canvas_web')} #{annotation_id}"
            )
        except Exception:
            pass
        return True

    def _annotation_overlay_script(self):
        payload = []
        current = str(self.current_url() or "")
        for item in self.annotations:
            if item.get('source') == 'files':
                continue
            # An annotation belongs to the page on which it was created. Runtime
            # documents may keep the same logical page under about:blank/base URL,
            # so only suppress a clearly different non-empty URL.
            item_url = str(item.get("url") or "")
            if item_url and current and item_url != current and item_url != "about:blank" and current != "about:blank":
                continue
            payload.append({
                "id": int(item.get("id", 0)),
                "note": str(item.get("note") or ""),
                "selection": str(item.get("selection") or ""),
                "element": item.get("element") if isinstance(item.get("element"), dict) else {},
            })
        data = json.dumps(payload, ensure_ascii=False)
        backend = json.dumps(self.backend)
        return r"""(() => {
          const items = __DATA__;
          const backend = __BACKEND__;
          try { if (typeof window.__pygptAnnotationCleanup === 'function') window.__pygptAnnotationCleanup(); } catch (_) {}
          window.__pygptAnnotationCleanup = null;
          let root = document.getElementById('__pygpt_annotations_root');
          if (root) root.remove();
          if (!items.length) return 0;

          root = document.createElement('div');
          root.id = '__pygpt_annotations_root';
          root.setAttribute('data-pygpt-ui', 'annotations');
          Object.assign(root.style, {position:'fixed', inset:'0', zIndex:'2147483645', pointerEvents:'none', fontFamily:'system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'});
          document.documentElement.appendChild(root);

          const esc = (v) => String(v == null ? '' : v);
          const place = (box, card, mark, item) => {
            const e = item.element || {};
            let target = null;
            try { if (e.selector) target = document.querySelector(e.selector); } catch (_) {}
            try { if (!target && e.stableSelector) target = document.querySelector(e.stableSelector); } catch (_) {}
            if (e.stableSelector) {
              const visible = target && target.getClientRects().length;
              for (const node of [box, card, mark]) node.style.display = visible ? '' : 'none';
              if (!visible) return;
            }
            let r = target ? target.getBoundingClientRect() : null;
            if (!r || (!r.width && !r.height)) {
              r = {x:Number(e.x||12), y:Number(e.y||12), width:Math.max(8,Number(e.width||24)), height:Math.max(8,Number(e.height||24)), left:Number(e.x||12), top:Number(e.y||12), right:Number(e.x||12)+Math.max(8,Number(e.width||24)), bottom:Number(e.y||12)+Math.max(8,Number(e.height||24))};
            }
            let hr = r;
            const sr = e.selectionRect;
            if (sr && target) {
              hr = {left:r.left+Number(sr.dx||0), top:r.top+Number(sr.dy||0), width:Math.max(3,Number(sr.width||3)), height:Math.max(3,Number(sr.height||3))};
              hr.right = hr.left + hr.width; hr.bottom = hr.top + hr.height;
            }
            Object.assign(box.style, {left:Math.round(hr.left-3)+'px', top:Math.round(hr.top-3)+'px', width:Math.round(Math.max(6,hr.width)+6)+'px', height:Math.round(Math.max(6,hr.height)+6)+'px'});
            const cardW = Math.min(330, Math.max(220, window.innerWidth - 24));
            let left = Math.min(window.innerWidth-cardW-10, Math.max(10, hr.left));
            let top = hr.bottom + 10;
            const estimated = Math.max(68, card.offsetHeight || 82);
            if (top + estimated > window.innerHeight - 10) top = Math.max(10, hr.top - estimated - 10);
            const offset = ((Number(item.id)||1)-1) % 4 * 7;
            left = Math.min(window.innerWidth-cardW-10, left + offset);
            top = Math.min(window.innerHeight-estimated-10, Math.max(10, top + offset));
            card.style.left = Math.round(left)+'px'; card.style.top = Math.round(top)+'px'; card.style.width = Math.round(cardW)+'px';
            mark.style.left = Math.round(Math.max(2, hr.left-10))+'px'; mark.style.top = Math.round(Math.max(2, hr.top-10))+'px';
          };

          for (const item of items) {
            const box = document.createElement('div');
            box.className = '__pygpt_annotation_box';
            Object.assign(box.style, {position:'fixed', border:'2px solid #a855f7', background:'rgba(168,85,247,.10)', borderRadius:'5px', boxSizing:'border-box', boxShadow:'0 0 0 2px rgba(168,85,247,.12)', pointerEvents:'none'});

            const mark = document.createElement('div');
            mark.textContent = String(item.id);
            Object.assign(mark.style, {position:'fixed', minWidth:'22px', height:'22px', padding:'0 5px', display:'flex', alignItems:'center', justifyContent:'center', background:'#7c3aed', color:'#fff', borderRadius:'11px', fontSize:'11px', fontWeight:'700', boxSizing:'border-box', boxShadow:'0 2px 8px rgba(0,0,0,.28)', pointerEvents:'none'});

            const card = document.createElement('div');
            card.className = '__pygpt_annotation_card';
            Object.assign(card.style, {position:'fixed', boxSizing:'border-box', padding:'10px 34px 10px 11px', background:'rgba(26,27,31,.96)', color:'#f7f7f8', border:'1px solid rgba(168,85,247,.85)', borderRadius:'9px', boxShadow:'0 8px 28px rgba(0,0,0,.32)', fontSize:'12px', lineHeight:'1.38', whiteSpace:'pre-wrap', overflowWrap:'anywhere', maxHeight:'min(280px,40vh)', overflowY:'auto', pointerEvents:'auto'});
            const title = document.createElement('div');
            title.textContent = __ANNOTATION_TITLE__ + ' #' + item.id;
            Object.assign(title.style, {fontWeight:'700', color:'#d8b4fe', marginBottom:'4px'});
            const body = document.createElement('div');
            body.textContent = esc(item.note || item.selection || __ANNOTATION_TITLE__);
            const close = document.createElement('button');
            close.type = 'button'; close.textContent = '×'; close.title = __REMOVE_ANNOTATION__;
            Object.assign(close.style, {position:'absolute', right:'6px', top:'5px', width:'24px', height:'24px', border:'0', borderRadius:'5px', background:'transparent', color:'#ddd', fontSize:'20px', lineHeight:'20px', cursor:'pointer', padding:'0'});
            close.onmouseenter = () => close.style.background='rgba(255,255,255,.10)';
            close.onmouseleave = () => close.style.background='transparent';
            close.onclick = (ev) => {
              ev.preventDefault(); ev.stopPropagation();
              box.remove(); mark.remove(); card.remove();
              try {
                if (backend === 'playwright' && typeof window.__pygpt_remove_annotation === 'function') {
                  window.__pygpt_remove_annotation(item.id);
                } else {
                  console.info('__PYGPT_ANNOTATION_REMOVE__:' + item.id);
                }
              } catch (_) {}
            };
            card.append(title, body, close);
            root.append(box, mark, card);
            const update = () => { if (box.isConnected) place(box, card, mark, item); };
            update();
            root.__pygptUpdates = root.__pygptUpdates || []; root.__pygptUpdates.push(update);
          }
          let raf = 0;
          const updateAll = () => { raf = 0; if (!root.isConnected) return; for (const fn of (root.__pygptUpdates||[])) fn(); };
          const schedule = () => { if (!raf) raf = requestAnimationFrame(updateAll); };
          window.addEventListener('scroll', schedule, true);
          window.addEventListener('resize', schedule, true);
          const observer = new MutationObserver(schedule);
          if (document.body) observer.observe(document.body, {childList:true, subtree:true, characterData:true});
          window.__pygptAnnotationCleanup = () => {
            observer.disconnect();
            window.removeEventListener('scroll', schedule, true);
            window.removeEventListener('resize', schedule, true);
            if (raf) cancelAnimationFrame(raf);
          };
          return items.length;
        })()""".replace('__DATA__', data) \
            .replace('__BACKEND__', backend) \
            .replace('__ANNOTATION_TITLE__', json.dumps(trans('ui.annotation_title', domain='plugin.canvas_web'), ensure_ascii=False)) \
            .replace('__REMOVE_ANNOTATION__', json.dumps(trans('ui.remove_annotation', domain='plugin.canvas_web'), ensure_ascii=False))

    def get_annotations(self):
        return list(self.annotations)


class ChatAnnotations(AnnotationMixin):
    """Runtime annotations owned by one conversation, independent of canvas plugins."""
    annotation_source = "chat"
    backend = "qt"

    def __init__(self, window, meta_id):
        self.window = window
        self.meta_id = meta_id
        self.annotations = []
        self.annotation_seq = 0
        self.views = weakref.WeakSet()

    def current_url(self):
        return f"chat:{self.meta_id}"

    def _opt(self, key, default=None):
        return default

    def show_editor(self, view, position, selected):
        zoom = view.zoomFactor() or 1
        script = self._annotation_editor_script(
            round(position.x() / zoom), round(position.y() / zoom),
            bool(selected), selected, "chat",
        )
        view.page().runJavaScript(self._scope_script(script))

    @staticmethod
    def _scope_script(script):
        return script.replace('__PYGPT_ANNOTATION_', '__PYGPT_CHAT_ANNOTATION_')

    def handle_annotation_console(self, message):
        if not str(message).startswith('__PYGPT_CHAT_ANNOTATION_'):
            return False
        return super().handle_annotation_console(
            str(message).replace('__PYGPT_CHAT_ANNOTATION_', '__PYGPT_ANNOTATION_', 1)
        )

    def _render_annotations(self):
        script = self._scope_script(self._annotation_overlay_script())
        for view in list(self.views):
            if getattr(getattr(view, 'meta', None), 'id', None) == self.meta_id:
                try:
                    view.page().runJavaScript(script)
                except RuntimeError:
                    self.views.discard(view)

    def prompt_block(self, ctx=None):
        if not self.annotations:
            return ""
        blocks = []
        instructions = {
            'chat': "These annotations refer to selected conversation text. Apply the feedback to your answer in chat.",
            'files': "These annotations refer to the specified files and line ranges; paths are relative to the workdir. Apply the feedback to those files using file tools when changes are requested.",
        }
        for source, title in (('chat', 'CHAT VIEW'), ('files', 'FILES PREVIEW')):
            items = [item for item in self.annotations if item.get('source', 'chat') == source]
            if items:
                track_sent_annotations(ctx, self, items[-20:])
                blocks.append(title + " USER ANNOTATIONS (source=" + source
                              + "; conversation=" + str(self.meta_id) + "):\n"
                              + instructions[source]
                              + " These are not canvas/web browser annotations. Do not call canvas_set_html or other canvas tools merely to handle them; use canvas only if the task independently requires it or the user explicitly requests it.\n"
                              + json.dumps(items[-20:], ensure_ascii=False))
        return "\n\n".join(blocks)

    def add_file_annotation(self, path, start_line, end_line, selection, note):
        """Keep file references in the conversation, including after closing Files."""
        if not note.strip():
            return
        self.annotation_seq += 1
        item = dict(id=self.annotation_seq, time=time.time(), source='files',
                    path=path, start_line=start_line, end_line=end_line,
                    selection=selection, note=note.strip())
        self.annotations.append(item)
        del self.annotations[:-30]
        return item
