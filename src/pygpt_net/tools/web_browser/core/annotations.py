#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #
from PySide6.QtCore import QTimer


class CanvasAnnotations:
    """Bridge browser selections and annotation rendering."""

    def __init__(self, runtime):
        self.runtime = runtime

    def selection_text(self, backend=None):
        runtime = self.runtime
        backend = backend or runtime.backend
        script = "(() => (window.getSelection && window.getSelection().toString() || '').trim().slice(0, 4000))()"
        try:
            if backend == "playwright":
                runtime.playwright.ensure()
                return str(runtime.pw_page.evaluate(script) or "")
            return str(runtime.qt.js(script) or "")
        except Exception as exc:
            try:
                runtime.window.core.debug.log(exc)
            except Exception:
                pass
            return ""


    def selection_descriptor(self, backend=None):
        runtime = self.runtime
        script = r"""(() => {
          const sel = window.getSelection && window.getSelection();
          if (!sel || sel.rangeCount < 1 || sel.isCollapsed) return null;
          const range = sel.getRangeAt(0);
          const rr = range.getBoundingClientRect();
          let node = range.commonAncestorContainer;
          let el = node && node.nodeType === Node.ELEMENT_NODE ? node : node && node.parentElement;
          if (!el) return null;
          const tr = el.getBoundingClientRect();
          let ref = el.getAttribute('data-pygpt-ref');
          if (!ref) {
            ref = 'a' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
            el.setAttribute('data-pygpt-ref', ref);
          }
          return {
            tag: el.tagName.toLowerCase(), id: el.id || '', className: String(el.className || ''),
            selector: '[data-pygpt-ref="' + ref + '"]',
            text: (el.innerText || el.value || '').trim().slice(0, 500),
            x: Math.round(tr.x), y: Math.round(tr.y), width: Math.round(tr.width), height: Math.round(tr.height),
            selectionRect: {
              dx: Math.round(rr.x - tr.x), dy: Math.round(rr.y - tr.y),
              width: Math.max(2, Math.round(rr.width)), height: Math.max(2, Math.round(rr.height))
            }
          };
        })()"""
        if backend == "playwright":
            runtime.playwright.ensure()
            return runtime.pw_page.evaluate(script)
        return runtime.qt.js(script)

    def element_at(self, x, y, backend):
        runtime = self.runtime
        script = f"""(() => {{ const e=document.elementFromPoint({int(x)},{int(y)}); if(!e)return null; const r=e.getBoundingClientRect(); let ref=e.getAttribute('data-pygpt-ref'); if(!ref){{ref='a'+Date.now().toString(36)+Math.random().toString(36).slice(2,6);e.setAttribute('data-pygpt-ref',ref);}} return {{tag:e.tagName.toLowerCase(),id:e.id||'',className:String(e.className||''),selector:'[data-pygpt-ref="'+ref+'"]',text:(e.innerText||e.value||'').trim().slice(0,500),outerHTML:e.outerHTML.slice(0,1500),selection:(window.getSelection()?.toString()||'').trim().slice(0,2000),x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)}}; }})()"""
        if backend == "playwright":
            runtime.playwright.ensure()
            return runtime.pw_page.evaluate(script)
        return runtime.qt.js(script)

    def remove_binding(self, source, annotation_id):
        runtime = self.runtime
        try:
            annotation_id = int(annotation_id)
        except Exception:
            return False
        # Binding callbacks run from Playwright. Defer mutation/rendering to the
        # Qt turn so no nested Playwright call is made inside the callback.
        QTimer.singleShot(0, lambda aid=annotation_id: runtime._remove_annotation(aid))
        return True

    def add_binding(self, source, payload):
        runtime = self.runtime
        if not isinstance(payload, dict):
            return False
        data = {
            "selection": str(payload.get("selection") or ""),
            "element": payload.get("element") if isinstance(payload.get("element"), dict) else {},
            "note": str(payload.get("note") or ""),
        }
        QTimer.singleShot(0, lambda item=data: runtime.add_annotation(
            selection=item["selection"], element=item["element"], note=item["note"]
        ))
        return True

