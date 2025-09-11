#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.11 08:00:00                  #
# ================================================== #

import os
from json import dumps as _json_dumps
from random import shuffle as _shuffle

from typing import Optional, List, Dict

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
        self.window = window
        self.highlight = SyntaxHighlight(window)
        self._tip_keys = tuple(f"output.tips.{i}" for i in range(1, self.NUM_TIPS + 1))
        self._syntax_dark = (
            "dracula",
            "fruity",
            "github-dark",
            "gruvbox-dark",
            "inkpot",
            "material",
            "monokai",
            "native",
            "nord",
            "nord-darker",
            "one-dark",
            "paraiso-dark",
            "rrt",
            "solarized-dark",
            "stata-dark",
            "vim",
            "zenburn",
        )

    def is_timestamp_enabled(self) -> bool:
        return self.window.core.config.get('output_timestamp')

    def prepare_styles(self) -> str:
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
        icons_html = "".join(self.get_action_icons(ctx, all=True))
        if icons_html:
            return f'<div class="action-icons" data-id="{ctx.id}">{icons_html}</div>'
        return ""

    def get_action_icons(self, ctx: CtxItem, all: bool = False) -> List[str]:
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

    def get_icon(self, icon: str, title: Optional[str] = None, item: Optional[CtxItem] = None) -> str:
        app_path = self.window.core.config.get_app_path()
        icon_path = os.path.join(app_path, "data", "icons", f"{icon}.svg")
        return f'<img src="file://{icon_path}" class="action-img" title="{title}" alt="{title}" data-id="{item.id}">'

    def get_image_html(self, url: str, num: Optional[int] = None, num_all: Optional[int] = None) -> str:
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

    def get_url_html(self, url: str, num: Optional[int] = None, num_all: Optional[int] = None) -> str:
        app_path = self.window.core.config.get_app_path()
        icon_path = os.path.join(app_path, "data", "icons", "url.svg").replace("\\", "/")
        icon = f'<img src="file://{icon_path}" class="extra-src-icon">'
        num_str = f" [{num}]" if (num is not None and num_all is not None and num_all > 1) else ""
        return f'{icon}<a href="{url}" title="{url}">{url}</a> <small>{num_str}</small>'

    def get_docs_html(self, docs: List[Dict]) -> str:
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

    def get_file_html(self, url: str, num: Optional[int] = None, num_all: Optional[int] = None) -> str:
        app_path = self.window.core.config.get_app_path()
        icon_path = os.path.join(app_path, "data", "icons", "attachments.svg").replace("\\", "/")
        icon = f'<img src="file://{icon_path}" class="extra-src-icon">'
        num_str = f" [{num}]" if (num is not None and num_all is not None and num_all > 1) else ""
        url, path = self.window.core.filesystem.extract_local_url(url)
        return f'{icon} <b>{num_str}</b> <a href="{url}">{path}</a>'

    def prepare_tool_extra(self, ctx: CtxItem) -> str:
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
        if not self.window.core.config.get("layout.tooltips", False):
            return "[]"

        _trans = trans
        prefix = _trans("output.tips.prefix")
        keys = self._tip_keys if hasattr(self, "_tip_keys") and len(self._tip_keys) == self.NUM_TIPS \
            else tuple(f"output.tips.{i}" for i in range(1, self.NUM_TIPS + 1))

        tips = [f"<p><b>{prefix}</b>: {_trans(k)}</p>" for k in keys]
        _shuffle(tips)
        return _json_dumps(tips)

    def get_html(self, pid: int) -> str:
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

        icons_js = (
            f'window.ICON_EXPAND="file://{expand_path}";'
            f'window.ICON_COLLAPSE="file://{collapse_path}";'
            f'window.ICON_CODE_COPY="file://{copy_path}";'
            f'window.ICON_CODE_PREVIEW="file://{preview_path}";'
            f'window.ICON_CODE_RUN="file://{run_path}";'
            f'window.ICON_CODE_MENU="file://{menu_path}";'
        )

        t_copy = trans('ctx.extra.copy_code')
        t_collapse = trans('ctx.extra.collapse')
        t_expand = trans('ctx.extra.expand')
        t_copied = trans('ctx.extra.copied')
        t_preview = trans('ctx.extra.preview')
        t_run = trans('ctx.extra.run')

        locales_js = (
            f'window.LOCALE_COPY={_json_dumps(t_copy)};'
            f'window.LOCALE_COPIED={_json_dumps(t_copied)};'
            f'window.LOCALE_PREVIEW={_json_dumps(t_preview)};'
            f'window.LOCALE_RUN={_json_dumps(t_run)};'
            f'window.LOCALE_COLLAPSE={_json_dumps(t_collapse)};'
            f'window.LOCALE_EXPAND={_json_dumps(t_expand)};'
        )

        syntax_style = cfg_get("render.code_syntax") or "default"
        style_js = (
            f'window.CODE_SYNTAX_STYLE={_json_dumps(syntax_style)};'
            f'window.PROFILE_CODE_STOP_HL_AFTER_LINES={int(cfg_get("render.code_syntax.stream_max_lines", 300))};'
            f'window.PROFILE_CODE_FINAL_HL_MAX_LINES={int(cfg_get("render.code_syntax.final_max_lines", 1500))};'
            f'window.PROFILE_CODE_FINAL_HL_MAX_CHARS={int(cfg_get("render.code_syntax.final_max_chars", 350000))};'
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