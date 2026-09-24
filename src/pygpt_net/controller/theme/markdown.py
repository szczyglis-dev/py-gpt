#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 22:10:00                  #
# ================================================== #

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
        """Apply WebEngine renderer theme styles."""
        event = RenderEvent(RenderEvent.ON_THEME_CHANGE)
        self.window.dispatch(event)

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
        """Load chat renderer CSS layers."""
        common = self.window.controller.theme.common
        theme = common.normalize_theme(self.window.core.config.get("theme"))
        web_style = common.normalize_style(
            self.window.core.config.get("theme.style", common.STYLE_STANDARD)
        )
        self.web_style = web_style

        # chat.css is the base for both Standard and Wide. The Wide style only
        # appends the small, theme-independent chat.wide.css override.
        paths = list(common.get_theme_asset_paths(theme, "chat.css"))
        if web_style == common.STYLE_WIDE:
            paths.extend(common.get_global_asset_paths("chat.wide.css"))

        content_parts = []
        for path in paths:
            try:
                with open(path, "r", encoding="utf-8") as file:
                    content_parts.append(file.read())
            except OSError:
                pass

        self.css["web"] = common.format_css("".join(content_parts))
