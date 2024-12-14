#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
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

        if self.window.core.config.get('theme.markdown'):
            self.load()
        else:
            self.set_default()
        self.apply()

        if force:
            self.window.controller.ui.restore_state()  # restore state after theme change

    def set_default(self):
        """Set default markdown CSS"""
        self.css['markdown'] = self.get_default()

    def apply(self):
        """Apply CSS to renderers"""
        if 'output' in self.window.ui.nodes:
            for pid in self.window.ui.nodes['output']:
                self.window.ui.nodes['output'][pid].setStyleSheet(self.css['markdown'])  # plain text, always apply
        event = RenderEvent(RenderEvent.ON_THEME_CHANGE)
        self.window.dispatch(event)  # per current engine

    def get_web_css(self) -> str:
        """
        Get web CSS

        :return: stylesheet
        """
        web_style = self.window.core.config.get("theme.style", "blocks")
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
        """Load markdown styles"""
        parents = [
            "markdown",
            "web",
        ]
        web_style = self.window.core.config.get("theme.style", "blocks")
        for base_name in parents:
            suffix = ""
            if base_name == 'web':
                suffix = "-" + web_style
                self.web_style = web_style
            theme = self.window.core.config.get('theme')
            name = str(base_name)
            if theme.startswith('light'):
                color = '.light'
            else:
                color = '.dark'

            # load CSS, app + user
            file_base = name + suffix + '.css'
            file_color = name + suffix + color + '.css'
            paths = []
            paths.append(os.path.join(self.window.core.config.get_app_path(), 'data', 'css', file_base))
            paths.append(os.path.join(self.window.core.config.get_app_path(), 'data', 'css', file_color))
            paths.append(os.path.join(self.window.core.config.get_user_path(), 'css', file_base))
            paths.append(os.path.join(self.window.core.config.get_user_path(), 'css', file_color))
            content = ''
            for path in paths:
                if os.path.exists(path) and os.path.isfile(path):
                    with open(path, 'r') as file:
                        content += file.read()

            self.css[base_name] = content  # always append default raw in case of errors in env vars
            try:
                self.css[base_name] = content.format(**os.environ)  # replace env vars
            except KeyError as e:  # ignore missing env vars
                pass

    def get_default(self) -> str:
        """
        Set default markdown CSS

        :return: default CSS
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
            }
        }

        theme = self.window.core.config.get('theme')
        styles = colors['dark']
        if theme.startswith('light'):
            styles = colors['light']

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
