#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.13 06:05:00                  #
# ================================================== #

import os
from json import dumps as _json_dumps
from random import shuffle as _shuffle

from typing import Optional, List, Dict, Tuple

from pygpt_net.core.text.utils import elide_filename
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans

from .syntax_highlight import SyntaxHighlight

import pygpt_net.js_rc
import pygpt_net.css_rc
import pygpt_net.fonts_rc


class Body:

    NUM_TIPS = 13

    _HTML_P0 = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    """

    _HTML_P1 = """
                </style>
                <link rel="stylesheet" href="qrc:///css/katex.min.css">
                <script type="text/javascript" src="qrc:///qtwebchannel/qwebchannel.js"></script>
                <script type="text/javascript" src="qrc:///js/markdown-it.min.js"></script>
                <script type="text/javascript" src="qrc:///js/markdown-it-katex.min.js"></script>
                <script type="text/javascript" src="qrc:///js/highlight.min.js"></script>                
                <script type="text/javascript" src="qrc:///js/auto-render.min.js"></script>
                <script type="text/javascript" src="qrc:///js/katex.min.js"></script>
                <!-- Config -->
                <script>
                    // window.STREAM_DEBUG = true; /* debug stream */
                    // window.MD_LANG_DEBUG = true; /* debug markdown language detection */
                    // window.CM_DEBUG = true; /* debug custom markup processor */
                    window.PID = """

    _HTML_P2 = """;
                    // icons
                    """

    _HTML_P3 = """
                    // translations
                    """

    _HTML_P4 = """
                    // highlight options
                    """

    _HTML_P5 = """
                    // tips
                    """

    _HTML_P6 = """
                </script>            
                <script type="text/javascript" src="qrc:///js/app.js"></script>
            </head>
            <body """

    _HTML_P7 = """>
            <div id="container">
                <div id="_nodes_" class="nodes empty_list"></div>
                <div id="_append_input_" class="append_input"></div>
                <div id="_append_output_before_" class="append_output"></div>
                <div id="_append_output_" class="append_output"></div>
                <div id="_append_live_" class="append_live hidden"></div>
                <div id="_footer_" class="footer"></div>
                <div id="_loader_" class="loader-global hidden">
                    <div class="lds-ring"><div></div><div></div><div></div><div></div></div>
                </div>
                <div id="tips" class="tips"></div>
            </div>
            <button id="scrollFab" class="scroll-fab" type="button" title="Go to top" aria-label="Go to top">
                <img id="scrollFabIcon" src="" alt="Scroll">
            </button>
            </body>
            </html>
            """

    _SPINNER = """
        .lds-ring {
          color: #1c4c5b;
        }
        .lds-ring,
        .lds-ring div {
          box-sizing: border-box;
        }
        .lds-ring {
          display: inline-block;
          position: relative;
          width: 80px;
          height: 80px;
        }
        .lds-ring div {
          box-sizing: border-box;
          display: block;
          position: absolute;
          width: 64px;
          height: 64px;
          margin: 8px;
          border: 8px solid currentColor;
          border-radius: 50%;
          animation: lds-ring 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
          border-color: currentColor transparent transparent transparent;
        }
        .lds-ring div:nth-child(1) {
          animation-delay: -0.45s;
        }
        .lds-ring div:nth-child(2) {
          animation-delay: -0.3s;
        }
        .lds-ring div:nth-child(3) {
          animation-delay: -0.15s;
        }
        @keyframes lds-ring {
          0% {
            transform: rotate(0deg);
          }
          100% {
            transform: rotate(360deg);
          }
        }
        """

    _SCROLL_FAB_CSS = """
        #scrollFab.scroll-fab {
            position: fixed;
            right: 16px;
            bottom: 16px;
            width: 40px;
            height: 40px;
            border: none;
            background: transparent;
            padding: 0;
            margin: 0;
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 2147483647;
            cursor: pointer;
            opacity: .65;
            transition: opacity .5s ease, transform .5s ease;
            will-change: transform, opacity;
            pointer-events: auto;
            -webkit-tap-highlight-color: transparent;
            user-select: none;
            -webkit-user-select: none;
        }
        #scrollFab.scroll-fab.visible {
            display: inline-flex;
        }
        #scrollFab.scroll-fab:hover {
            opacity: 1;
        }
        #scrollFab.scroll-fab img {
            width: 100%;
            height: 100%;
            display: block;
            pointer-events: none;
        }
        @media (prefers-reduced-motion: reduce) {
            #scrollFab.scroll-fab {
                transition: none;
            }
        }
    """

    _PERFORMANCE_CSS = """
        #container, #_nodes_, #_append_output_, #_append_output_before_ {
            contain: layout paint;
            overscroll-behavior: contain;
            backface-visibility: hidden;
            transform: translateZ(0);
        }
        .msg-bot {
            contain: layout paint style;
            contain-intrinsic-size: 1px 600px;
            box-shadow: none !important;
            filter: none !important;
        }
        .msg-bot:not(:last-child) {
            content-visibility: auto;
        }
        .msg {
            text-rendering: optimizeSpeed;
        }
        """

    def __init__(self, window=None):
        """
        Initialize Body with reference to main window and syntax highlighter.

        :param window: Window reference
        """
        self.window = window
        self.highlight = SyntaxHighlight(window)
        self._tip_keys = tuple(f"output.tips.{i}" for i in range(1, self.NUM_TIPS + 1))
        self._syntax_dark = (
            "dracula", "fruity", "github-dark", "gruvbox-dark", "inkpot", "material",
            "monokai", "native", "nord", "nord-darker", "one-dark", "paraiso-dark",
            "rrt", "solarized-dark", "stata-dark", "vim", "zenburn",
        )

    def is_timestamp_enabled(self) -> bool:
        """
        Check if timestamp display is enabled in config.

        :return: True if enabled, False otherwise.
        """
        return self.window.core.config.get('output_timestamp')

    def prepare_styles(self) -> str:
        """
        Prepare combined CSS styles for the web view.

        :return: Combined CSS string.
        """
        cfg = self.window.core.config
        fonts_path = os.path.join(cfg.get_app_path(), "data", "fonts").replace("\\", "/")
        syntax_style = self.window.core.config.get("render.code_syntax") or "default"
        theme_css = self.window.controller.theme.markdown.get_web_css().replace('%fonts%', fonts_path)
        parts = [
            self._SPINNER,
            self._SCROLL_FAB_CSS,
            theme_css,
            "pre { color: #fff; }" if syntax_style in self._syntax_dark else "pre { color: #000; }",
            self.highlight.get_style_defs(),
            self._PERFORMANCE_CSS
        ]
        return "\n".join(parts)

    def prepare_action_icons(self, ctx: CtxItem) -> str:
        """
        Prepare HTML for message-level action icons.

        :param ctx: CtxItem
        :return: HTML string or empty if no icons.
        """
        icons_html = "".join(self.get_action_icons(ctx, all=True))
        if icons_html:
            return f'<div class="action-icons" data-id="{ctx.id}">{icons_html}</div>'
        return ""

    def get_action_icons(self, ctx: CtxItem, all: bool = False) -> List[str]:
        """
        Return HTML snippets for message-level action icons.

        :param ctx: CtxItem
        :param all: If True, return all icons; otherwise, return only available ones.
        :return: List of HTML strings for icons.
        """
        icons: List[str] = []
        if ctx.output:
            cid = ctx.id
            t = trans
            icons.append(
                f'<a href="extra-audio-read:{cid}" class="action-icon" data-id="{cid}" role="button"><span class="cmd">{self.get_icon("volume", t("ctx.extra.audio"), ctx)}</span></a>')
            icons.append(
                f'<a href="extra-copy:{cid}" class="action-icon" data-id="{cid}" role="button"><span class="cmd">{self.get_icon("copy", t("ctx.extra.copy"), ctx)}</span></a>')
            icons.append(
                f'<a href="extra-replay:{cid}" class="action-icon" data-id="{cid}" role="button"><span class="cmd">{self.get_icon("reload", t("ctx.extra.reply"), ctx)}</span></a>')
            icons.append(
                f'<a href="extra-edit:{cid}" class="action-icon edit-icon" data-id="{cid}" role="button"><span class="cmd">{self.get_icon("edit", t("ctx.extra.edit"), ctx)}</span></a>')
            icons.append(
                f'<a href="extra-delete:{cid}" class="action-icon edit-icon" data-id="{cid}" role="button"><span class="cmd">{self.get_icon("delete", t("ctx.extra.delete"), ctx)}</span></a>')
            if not self.window.core.ctx.is_first_item(cid):
                icons.append(
                    f'<a href="extra-join:{cid}" class="action-icon edit-icon" data-id="{cid}" role="button"><span class="cmd">{self.get_icon("playlist_add", t("ctx.extra.join"), ctx)}</span></a>')
        return icons

    def get_action_icon_data(self, ctx: CtxItem) -> List[Dict]:
        """
        Return raw data for message-level action icons (href/title/icon path).
        This allows JS templates to render actions without Python-side HTML.

        1. extra-audio-read
        2. extra-copy
        3. extra-replay
        4. extra-edit
        5. extra-delete
        6. extra-join (if not the first item)
        7. (future actions...)

        :param ctx: CtxItem
        :return: List of action dicts
        """
        items: List[Dict] = []
        if ctx.output:
            cid = ctx.id
            t = trans
            app_path = self.window.core.config.get_app_path()
            def icon_path(name: str) -> str:
                return os.path.join(app_path, "data", "icons", f"{name}.svg").replace("\\", "/")

            items.append({"href": f"extra-audio-read:{cid}", "title": t("ctx.extra.audio"), "icon": f"file://{icon_path('volume')}", "id": cid})
            items.append({"href": f"extra-copy:{cid}", "title": t("ctx.extra.copy"), "icon": f"file://{icon_path('copy')}", "id": cid})
            items.append({"href": f"extra-replay:{cid}", "title": t("ctx.extra.reply"), "icon": f"file://{icon_path('reload')}", "id": cid})
            items.append({"href": f"extra-edit:{cid}", "title": t("ctx.extra.edit"), "icon": f"file://{icon_path('edit')}", "id": cid})
            items.append({"href": f"extra-delete:{cid}", "title": t("ctx.extra.delete"), "icon": f"file://{icon_path('delete')}", "id": cid})
            if not self.window.core.ctx.is_first_item(cid):
                items.append({"href": f"extra-join:{cid}", "title": t("ctx.extra.join"), "icon": f"file://{icon_path('playlist_add')}", "id": cid})
        return items

    def get_icon(
            self,
            icon: str,
            title: Optional[str] = None,
            item: Optional[CtxItem] = None
    ) -> str:
        """
        Get HTML for an icon image with title and optional data-id.

        :param icon: Icon name (without extension)
        :param title: Icon title (tooltip)
        :param item: Optional CtxItem to get data-id from
        :return: HTML string
        """
        app_path = self.window.core.config.get_app_path()
        icon_path = os.path.join(app_path, "data", "icons", f"{icon}.svg")
        return f'<img src="file://{icon_path}" class="action-img" title="{title}" alt="{title}" data-id="{item.id}">'

    def get_image_html(
            self,
            url: str,
            num: Optional[int] = None,
            num_all: Optional[int] = None
    ) -> str:
        """
        Get HTML for an image or video link with optional numbering.

        :param url: Image or video URL
        :param num: Optional index (1-based)
        :param num_all: Optional total number of images/videos
        :return: HTML string
        """
        url, path = self.window.core.filesystem.extract_local_url(url)
        basename = os.path.basename(path)
        ext = os.path.splitext(basename)[1].lower()
        video_exts = (".mp4", ".webm", ".ogg", ".mov", ".avi", ".mkv")
        if ext in video_exts:
            if ext != ".webm":
                webm_path = os.path.splitext(path)[0] + ".webm"
                if os.path.exists(webm_path):
                    path = webm_path
                    ext = ".webm"
            return f'''
            <div class="extra-src-video-box" title="{url}">
                <video class="video-player" controls>
                    <source src="{path}" type="video/{ext[1:]}">
                </video>
                <p><a href="bridge://play_video/{url}" class="title">{elide_filename(basename)}</a></p>
            </div>
            '''
        return f'<div class="extra-src-img-box" title="{url}"><div class="img-outer"><div class="img-wrapper"><a href="{url}"><img src="{path}" class="image"></a></div><a href="{url}" class="title">{elide_filename(basename)}</a></div></div><br/>'

    def get_url_html(
            self,
            url: str,
            num: Optional[int] = None,
            num_all: Optional[int] = None
    ) -> str:
        """
        Get HTML for a URL link with icon and optional numbering.

        :param url: URL string
        :param num: Optional index (1-based)
        :param num_all: Optional total number of URLs
        :return: HTML string
        """
        app_path = self.window.core.config.get_app_path()
        icon_path = os.path.join(app_path, "data", "icons", "url.svg").replace("\\", "/")
        icon = f'<img src="file://{icon_path}" class="extra-src-icon">'
        num_str = f" [{num}]" if (num is not None and num_all is not None and num_all > 1) else ""
        return f'{icon}<a href="{url}" title="{url}">{url}</a> <small>{num_str}</small>'

    def get_docs_html(self, docs: List[Dict]) -> str:
        """
        Get HTML for document references.

        :param docs: List of document dicts {uuid: {meta_dict}}
        :return: HTML string or empty if no docs.
        """
        html_parts: List[str] = []
        src_parts: List[str] = []
        num = 1
        limit = 3

        try:
            for item in docs:
                for uuid, doc_json in item.items():
                    entries = ", ".join(f"<b>{k}:</b> {doc_json[k]}" for k in doc_json)
                    src_parts.append(f"<p><small>[{num}] {uuid}: {entries}</small></p>")
                    num += 1
                    if num >= limit:
                        break
                if num >= limit:
                    break
        except Exception:
            pass

        if src_parts:
            app_path = self.window.core.config.get_app_path()
            icon_path = os.path.join(app_path, "data", "icons", "db.svg").replace("\\", "/")
            icon = f'<img src="file://{icon_path}" class="extra-src-icon">'
            html_parts.append(f'<p>{icon}<small><b>{trans("chat.prefix.doc")}:</b></small></p>')
            html_parts.append('<div class="cmd">')
            html_parts.append(f"<p>{''.join(src_parts)}</p>")
            html_parts.append("</div> ")

        return "".join(html_parts)

    def get_file_html(
            self,
            url: str,
            num: Optional[int] = None,
            num_all: Optional[int] = None
    ) -> str:
        """
        Get HTML for a file link with icon and optional numbering.

        :param url: File URL
        :param num: Optional file index (1-based)
        :param num_all: Optional total number of files
        :return: HTML string
        """
        app_path = self.window.core.config.get_app_path()
        icon_path = os.path.join(app_path, "data", "icons", "attachments.svg").replace("\\", "/")
        icon = f'<img src="file://{icon_path}" class="extra-src-icon">'
        num_str = f" [{num}]" if (num is not None and num_all is not None and num_all > 1) else ""
        url, path = self.window.core.filesystem.extract_local_url(url)
        return f'{icon} <b>{num_str}</b> <a href="{url}">{path}</a>'

    def prepare_tool_extra(self, ctx: CtxItem) -> str:
        """
        Prepare extra HTML for tool/plugin output.

        :param ctx: CtxItem
        :return: HTML string or empty if no extra.
        """
        extra = ctx.extra
        if not extra:
            return ""

        parts: List[str] = ['<div class="msg-extra">']

        if "plugin" in extra:
            event = Event(Event.TOOL_OUTPUT_RENDER, {
                'tool': extra["plugin"],
                'html': '',
                'multiple': False,
                'content': extra,
            })
            event.ctx = ctx
            self.window.dispatch(event, all=True)
            if event.data['html']:
                parts.append(f'<div class="tool-output-block">{event.data["html"]}</div>')

        elif "tool_output" in extra and isinstance(extra["tool_output"], list):
            for tool in extra["tool_output"]:
                if "plugin" not in tool:
                    continue
                event = Event(Event.TOOL_OUTPUT_RENDER, {
                    'tool': tool["plugin"],
                    'html': '',
                    'multiple': True,
                    'content': tool,
                })
                event.ctx = ctx
                self.window.dispatch(event, all=True)
                if event.data['html']:
                    parts.append(f'<div class="tool-output-block">{event.data["html"]}</div>')

        parts.append("</div>")
        return "".join(parts)

    def get_all_tips(self) -> str:
        """
        Get all tips as a JSON array string.

        :return: JSON array string of tips or "[]" if disabled.
        """
        if not self.window.core.config.get("layout.tooltips", False):
            return "[]"

        _trans = trans
        prefix = _trans("output.tips.prefix")
        keys = self._tip_keys if hasattr(self, "_tip_keys") and len(self._tip_keys) == self.NUM_TIPS \
            else tuple(f"output.tips.{i}" for i in range(1, self.NUM_TIPS + 1))

        tips = [f"<p><b>{prefix}</b>: {_trans(k)}</p>" for k in keys]
        _shuffle(tips)
        return _json_dumps(tips)

    def _extract_local_url(self, url: str) -> Tuple[str, str]:
        """
        Extract local URL and path using filesystem helper.

        On failure, return (url, url).

        :param url: URL to extract.
        :return: Tuple of (url, path).
        """
        try:
            return self.window.core.filesystem.extract_local_url(url)
        except Exception:
            return url, url

    def build_extras_dicts(self, ctx: CtxItem, pid: int) -> Tuple[dict, dict, dict, dict]:
        """
        Build images/files/urls raw dicts to be rendered by JS templates.

        1-based indexing for keys as strings: "1", "2", ...
        0-based indexing is inconvenient in JS templates.
        1-based indexing allows to show [n/m] in titles.

        1. images_dict = { "1": {url, path, basename, ext, is_video, webm_path}, ... }
        2. files_dict = { "1": {url, path}, ... }
        3. urls_dict = { "1": {url}, ... }
        4. actions_dict = { "actions": [ {href, title, icon, id}, ... ] }  # message-level actions

        :param ctx: CtxItem
        :param pid: Process ID
        :return: Tuple of (images_dict, files_dict, urls_dict, actions_dict)
        """
        images = {}
        files = {}
        urls = {}

        # images
        if ctx.images:
            video_exts = (".mp4", ".webm", ".ogg", ".mov", ".avi", ".mkv")
            n = 1
            for img in ctx.images:
                if img is None:
                    continue
                try:
                    url, path = self._extract_local_url(img)
                    basename = os.path.basename(path)
                    ext = os.path.splitext(basename)[1].lower()
                    is_video = ext in video_exts
                    webm_path = ""
                    if is_video and ext != ".webm":
                        wp = os.path.splitext(path)[0] + ".webm"
                        if os.path.exists(wp):
                            webm_path = wp
                    images[str(n)] = {
                        "url": url,
                        "path": path,
                        "basename": basename,
                        "ext": ext,
                        "is_video": is_video,
                        "webm_path": webm_path,
                    }
                    n += 1
                except Exception:
                    pass

        # files
        if ctx.files:
            n = 1
            for f in ctx.files:
                try:
                    url, path = self._extract_local_url(f)
                    files[str(n)] = {
                        "url": url,
                        "path": path,
                    }
                    n += 1
                except Exception:
                    pass

        # urls
        if ctx.urls:
            n = 1
            for u in ctx.urls:
                try:
                    urls[str(n)] = {"url": u}
                    n += 1
                except Exception:
                    pass

        # actions (message-level) – raw data for icons (href/title/icon)
        actions = self.get_action_icon_data(ctx)

        return images, files, urls, {"actions": actions}

    def normalize_docs(self, doc_ids) -> list[dict]:
        """
        Normalize ctx.doc_ids into a list of {"uuid": str, "meta": dict}.
        Accepts original shape: List[Dict[uuid -> meta_dict]] or already normalized.

        Returns empty list on failure.

        Example input:
        [
            {"123e4567-e89b-12d3-a456-426614174000": {"title": "Document 1", "source": "file1.txt"}},
            {"123e4567-e89b-12d3-a456-426614174001": {"title": "Document 2", "source": "file2.txt"}}
        ]
        Example output:
        [
            {"uuid": "123e4567-e89b-12d3-a456-426614174000", "meta": {"title": "Document 1", "source": "file1.txt"}},
            {"uuid": "123e4567-e89b-12d3-a456-426614174001", "meta": {"title": "Document 2", "source": "file2.txt"}}
        ]

        :param doc_ids: List of document IDs in original or normalized shape.
        :return: List of normalized document dicts.
        """
        normalized = []
        try:
            for item in doc_ids or []:
                if isinstance(item, dict):
                    # Already normalized?
                    if 'uuid' in item and 'meta' in item and isinstance(item['meta'], dict):
                        normalized.append({
                            "uuid": str(item['uuid']),
                            "meta": dict(item['meta']),
                        })
                        continue
                    # Original shape: { uuid: { ... } }
                    keys = list(item.keys())
                    if len(keys) == 1:
                        uuid = str(keys[0])
                        meta = item[uuid]
                        if isinstance(meta, dict):
                            normalized.append({"uuid": uuid, "meta": dict(meta)})
        except Exception:
            pass
        return normalized

    def get_html(self, pid: int) -> str:
        """
        Build full HTML for the web view body.

        :param pid: Process ID to embed in JS.
        :return: Full HTML string.
        """
        cfg_get = self.window.core.config.get
        style = cfg_get("theme.style", "blocks")
        classes = ["theme-" + style]
        if cfg_get('render.blocks'):
            classes.append("display-blocks")
        if cfg_get('ctx.edit_icons'):
            classes.append("display-edit-icons")
        if self.is_timestamp_enabled():
            classes.append("display-timestamp")
        classes_str = f' class="{" ".join(classes)}"' if classes else ""
        styles_css = self.prepare_styles()
        tips_json = self.get_all_tips()

        app_path = self.window.core.config.get_app_path().replace("\\", "/")
        expand_path = os.path.join(app_path, "data", "icons", "expand.svg").replace("\\", "/")
        collapse_path = os.path.join(app_path, "data", "icons", "collapse.svg").replace("\\", "/")

        copy_path = os.path.join(app_path, "data", "icons", "copy.svg").replace("\\", "/")
        preview_path = os.path.join(app_path, "data", "icons", "view.svg").replace("\\", "/")
        run_path = os.path.join(app_path, "data", "icons", "play.svg").replace("\\", "/")
        menu_path = os.path.join(app_path, "data", "icons", "menu.svg").replace("\\", "/")

        url_path = os.path.join(app_path, "data", "icons", "url.svg").replace("\\", "/")
        attach_path = os.path.join(app_path, "data", "icons", "attachments.svg").replace("\\", "/")
        db_path = os.path.join(app_path, "data", "icons", "db.svg").replace("\\", "/")

        icons_js = (
            f'window.ICON_EXPAND="file://{expand_path}";'
            f'window.ICON_COLLAPSE="file://{collapse_path}";'
            f'window.ICON_CODE_COPY="file://{copy_path}";'
            f'window.ICON_CODE_PREVIEW="file://{preview_path}";'
            f'window.ICON_CODE_RUN="file://{run_path}";'
            f'window.ICON_CODE_MENU="file://{menu_path}";'
            f'window.ICON_URL="file://{url_path}";'
            f'window.ICON_ATTACHMENTS="file://{attach_path}";'
            f'window.ICON_DB="file://{db_path}";'
        )

        t_copy = trans('ctx.extra.copy_code')
        t_collapse = trans('ctx.extra.collapse')
        t_expand = trans('ctx.extra.expand')
        t_copied = trans('ctx.extra.copied')
        t_preview = trans('ctx.extra.preview')
        t_run = trans('ctx.extra.run')
        t_doc_prefix = trans("chat.prefix.doc")

        locales_js = (
            f'window.LOCALE_COPY={_json_dumps(t_copy)};'
            f'window.LOCALE_COPIED={_json_dumps(t_copied)};'
            f'window.LOCALE_PREVIEW={_json_dumps(t_preview)};'
            f'window.LOCALE_RUN={_json_dumps(t_run)};'
            f'window.LOCALE_COLLAPSE={_json_dumps(t_collapse)};'
            f'window.LOCALE_EXPAND={_json_dumps(t_expand)};'
            f'window.LOCALE_DOC_PREFIX={_json_dumps(t_doc_prefix)};'
        )

        syntax_style = cfg_get("render.code_syntax") or "default"
        style_js = (
            f'window.CODE_SYNTAX_STYLE={_json_dumps(syntax_style)};'
            f'window.PROFILE_CODE_HL_N_LINE={int(cfg_get("render.code_syntax.stream_n_line", 25))};'
            f'window.PROFILE_CODE_HL_N_CHARS={int(cfg_get("render.code_syntax.stream_n_chars", 5000))};'
            f'window.PROFILE_CODE_STOP_HL_AFTER_LINES={int(cfg_get("render.code_syntax.stream_max_lines", 300))};'
            f'window.PROFILE_CODE_FINAL_HL_MAX_LINES={int(cfg_get("render.code_syntax.final_max_lines", 1500))};'
            f'window.PROFILE_CODE_FINAL_HL_MAX_CHARS={int(cfg_get("render.code_syntax.final_max_chars", 350000))};'
            f'window.DISABLE_SYNTAX_HIGHLIGHT={int(cfg_get("render.code_syntax.disabled", 0))};'
            f'window.USER_MSG_COLLAPSE_HEIGHT_PX={int(cfg_get("render.msg.user.collapse.px", 1500))};'
        )

        tips_js = f'window.TIPS={tips_json};'

        return ''.join((
            self._HTML_P0,
            styles_css,
            self._HTML_P1,
            str(pid),
            self._HTML_P2,
            icons_js,
            self._HTML_P3,
            locales_js,
            self._HTML_P4,
            style_js,
            self._HTML_P5,
            tips_js,
            self._HTML_P6,
            classes_str,
            self._HTML_P7,
        ))