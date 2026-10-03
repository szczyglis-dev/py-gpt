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
"""Default Canvas documents and browser scripts shared by the backends."""

BLANK_CANVAS_HTML_LIGHT = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
html, body {
    width: 100%;
    min-height: 100%;
    margin: 0;
}
body {
    min-height: 100vh;
    background-color: #f5f5f5;
    background-image:
        linear-gradient(rgba(255, 255, 255, 0.55) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.55) 1px, transparent 1px);
    background-size: 18px 18px;
}
</style>
</head>
<body></body>
</html>"""

BLANK_CANVAS_HTML_DARK = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
html, body {
    width: 100%;
    min-height: 100%;
    margin: 0;
}
body {
    min-height: 100vh;
    background-color: #1b1c1f;
    background-image:
        linear-gradient(#16171a 1px, transparent 1px),
        linear-gradient(90deg, #16171a 1px, transparent 1px);
    background-size: 18px 18px;
}
</style>
</head>
<body></body>
</html>"""

BLANK_CANVAS_HTML = BLANK_CANVAS_HTML_LIGHT

JS_SERIALIZE_HTML = r"""(() => {
      const root = document.documentElement.cloneNode(true);
      const cursor = root.querySelector('#__pygpt_virtual_cursor');
      if (cursor) cursor.remove();
      const annotations = root.querySelector('#__pygpt_annotations_root');
      if (annotations) annotations.remove();
      const annotationEditor = root.querySelector('#__pygpt_annotation_editor');
      if (annotationEditor) annotationEditor.remove();
      root.querySelectorAll('[data-pygpt-ref]').forEach(el => el.removeAttribute('data-pygpt-ref'));
      const dt = document.doctype ? '<!DOCTYPE ' + document.doctype.name + '>' : '';
      return dt + root.outerHTML;
    })()"""

JS_INSPECT = r"""
(() => {
  const selector = %s;
  const limit = %d;
  const nodes = selector ? Array.from(document.querySelectorAll(selector)) : Array.from(document.querySelectorAll(
    'a,button,input,textarea,select,summary,[role="button"],[role="link"],[contenteditable="true"],[onclick]'
  ));
  const out = [];
  window.__pygpt_ref_seq = Number(window.__pygpt_ref_seq || 0);
  for (const el of nodes) {
    if (out.length >= limit) break;
    const r = el.getBoundingClientRect();
    const st = getComputedStyle(el);
    if (r.width <= 0 || r.height <= 0 || st.visibility === 'hidden' || st.display === 'none') continue;
    let ref = el.getAttribute('data-pygpt-ref');
    if (!ref) {
      ref = 'e' + (++window.__pygpt_ref_seq);
      el.setAttribute('data-pygpt-ref', ref);
    }
    out.push({
      ref,
      selector: `[data-pygpt-ref="${ref}"]`,
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      role: el.getAttribute('role') || '',
      text: (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim().slice(0, 500),
      href: el.href || '',
      disabled: !!el.disabled,
      checked: !!el.checked,
      x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height)
    });
  }
  return out;
})()
"""
