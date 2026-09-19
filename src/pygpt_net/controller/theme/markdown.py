#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 11:40:00                  #
# ================================================== #

import os

from pygpt_net.core.events import RenderEvent


class Markdown:
    def __init__(self, window=None):
        """
        Markdown css controller

        :param window: Window instance
        """
        self.window = window
        self.css = {}  # external styles
        self.web_style = ""

    def update(self, force: bool = False):
        """
        Update markdown styles

        :param force: force theme change (manual trigger)
        """
        if force:
            self.window.controller.ui.store_state()  # store state before theme change
        
        self.load()
        self.apply()

        if force:
            self.window.controller.ui.restore_state()  # restore state after theme change

    def apply(self):
        """Apply renderer theme styles."""
        # The optional non-WebEngine renderer uses a small stylesheet generated
        # in Python. External markdown*.css assets are no longer used.
        legacy_css = self.get_legacy_css()
        if 'output' in self.window.ui.nodes:
            for pid in self.window.ui.nodes['output']:
                try:
                    self.window.ui.nodes['output'][pid].setStyleSheet(legacy_css)
                except Exception:
                    pass
        event = RenderEvent(RenderEvent.ON_THEME_CHANGE)
        self.window.dispatch(event)  # per current engine

    def get_web_css(self) -> str:
        """
        Get web CSS

        :return: stylesheet
        """
        web_style = self.window.controller.theme.common.normalize_style(
            self.window.core.config.get("theme.style", "standard")
        )
        if "web" not in self.css or self.web_style != web_style:
            self.load()
        if "web" in self.css:
            return self.css["web"]
        return ""

    def clear(self):
        """Clear CSS of markdown formatter"""
        meta = self.window.core.ctx.get_current_meta()
        event = RenderEvent(RenderEvent.CLEAR_ALL)
        self.window.dispatch(event)  # per current engine
        self.window.controller.ctx.refresh()
        self.window.controller.ctx.refresh_output()
        event = RenderEvent(RenderEvent.END, {
            "meta": meta,
        })
        self.window.dispatch(event)

    def load(self):
        """Load markdown styles."""
        theme = self.window.controller.theme.common.normalize_theme(
            self.window.core.config.get('theme')
        )
        color = f'.{theme}'
        css_dir = os.path.join(
            self.window.core.config.get_app_path(),
            'data',
            'css',
        )

        web_style = self.window.controller.theme.common.normalize_style(
            self.window.core.config.get("theme.style", "standard")
        )
        self.web_style = web_style

        # WebEngine owns the current chat rendering. Standard is always the
        # base; Wide only appends a tiny, theme-independent width override.
        filenames = [
            "web-standard.css",
            "web-standard" + color + ".css",
        ]
        if web_style == "wide":
            filenames.append("web-wide.css")

        content = ''
        for filename in filenames:
            path = os.path.join(css_dir, filename)
            if os.path.exists(path) and os.path.isfile(path):
                with open(path, 'r') as file:
                    content += file.read()

        self.css["web"] = content  # keep raw CSS if env expansion fails
        try:
            self.css["web"] = content.format(**os.environ)
        except KeyError:
            pass

    def get_legacy_css(self) -> str:
        """
        Return minimal stylesheet for the optional legacy renderer.

        :return: legacy renderer stylesheet
        """
        colors = {
            "dark": {
                "a": "#fff",
                "msg-user": "#d9d9d9",
                "msg-bot": "#fff",
                "cmd": "#4d4d4d",
                "ts": "#d0d0d0",
                "pre-bg": "#202225",
                "pre": "#fff",
                "code": "#fff",
            },
            "light": {
                "a": "#000",
                "msg-user": "#444444",
                "msg-bot": "#000",
                "cmd": "#4d4d4d",
                "ts": "#4d4d4d",
                "pre-bg": "#e9e9e9",
                "pre": "#000",
                "code": "#000",
            },
            "mint": {
                "a": "#27785a",
                "msg-user": "#355c4d",
                "msg-bot": "#17382d",
                "cmd": "#648074",
                "ts": "#648074",
                "pre-bg": "#e7f3ed",
                "pre": "#17382d",
                "code": "#17382d",
            },
            "gray": {
                "a": "#f1f3f4",
                "msg-user": "#d7d9df",
                "msg-bot": "#f1f3f4",
                "cmd": "#8b8e96",
                "ts": "#9aa0a6",
                "pre-bg": "#30323a",
                "pre": "#f1f3f4",
                "code": "#f1f3f4",
            },
            "matrix": {
                "a": "#66ff99",
                "msg-user": "#9bd8aa",
                "msg-bot": "#d8ffe3",
                "cmd": "#568465",
                "ts": "#6f987b",
                "pre-bg": "#0d1d13",
                "pre": "#b8ffca",
                "code": "#b8ffca",
            },
            "flare": {
                "a": "#ff6666",
                "msg-user": "#d89b9b",
                "msg-bot": "#ffd8d8",
                "cmd": "#845656",
                "ts": "#986f6f",
                "pre-bg": "#1d0d0d",
                "pre": "#ffb8b8",
                "code": "#ffb8b8",
            },
            "retro": {
                "a": "#39dfff",
                "msg-user": "#c7a7e8",
                "msg-bot": "#f4e9ff",
                "cmd": "#806497",
                "ts": "#9a80b2",
                "pre-bg": "#21142f",
                "pre": "#f4b7ff",
                "code": "#f4b7ff",
            },
            "ocean": {
                "a": "#66eaff",
                "msg-user": "#9bd7e8",
                "msg-bot": "#d9f7ff",
                "cmd": "#568ba0",
                "ts": "#7096a8",
                "pre-bg": "#0d2230",
                "pre": "#b8f4ff",
                "code": "#b8f4ff",
            }
        }

        theme = self.window.controller.theme.common.normalize_theme(
            self.window.core.config.get('theme')
        )
        styles = colors[theme]

        return """
        a {{
            color: {a};
        }}
        .msg-user {{
            color: {msg-user} !important;
            white-space: pre-wrap;
            width: 100%;
            max-width: 100%;
        }}
        .msg-bot {{
            color: {msg-bot} !important;
            white-space: pre-wrap;
            width: 100%;
            max-width: 100%;
        }}
        .cmd {{
            color: {cmd};
        }}
        .ts {{
            color: {ts};
        }}
        .list {{
        }}
        pre {{
            color: {pre};
            background-color: {pre-bg};
            font-family: 'Lato';
            display: block;
        }}
        code {{
            color: {pre};
        }}""".format_map(styles)
