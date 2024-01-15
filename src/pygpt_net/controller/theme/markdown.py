#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.15 10:00:00                  #
# ================================================== #

import os


class Markdown:
    def __init__(self, window=None):
        """
        Markdown css controller

        :param window: Window instance
        """
        self.window = window
        self.css = {}  # external styles

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
        """Apply CSS to markdown formatter"""
        self.window.ui.nodes['output'].document().setDefaultStyleSheet(self.css['markdown'])
        self.window.ui.nodes['output'].document().setMarkdown(self.window.ui.nodes['output'].document().toMarkdown())
        self.window.controller.ctx.refresh_output()

    def clear(self):
        """Clear CSS to markdown formatter"""
        self.window.ui.nodes['output'].clear()
        self.window.ui.nodes['output'].document().setDefaultStyleSheet("")
        self.window.ui.nodes['output'].setStyleSheet("")
        self.window.ui.nodes['output'].document().setMarkdown("")
        self.window.ui.nodes['output'].document().setHtml("")
        self.window.ui.nodes['output'].setPlainText("")
        self.window.controller.ctx.refresh()
        self.window.controller.ctx.refresh_output()
        self.window.controller.chat.render.end()

    def load(self):
        """Load markdown styles"""
        theme = self.window.core.config.get('theme')
        name = 'markdown'
        color_name = 'markdown'
        if theme.startswith('light'):
            color_name += '.light'
        else:
            color_name += '.dark'
        paths = []
        paths.append(os.path.join(self.window.core.config.get_app_path(), 'data', 'css', name + '.css'))
        paths.append(os.path.join(self.window.core.config.get_app_path(), 'data', 'css', color_name + '.css'))
        paths.append(os.path.join(self.window.core.config.get_user_path(), 'css', name + '.css'))
        paths.append(os.path.join(self.window.core.config.get_user_path(), 'css', color_name + '.css'))
        content = ''
        for path in paths:
            if os.path.exists(path):
                with open(path, 'r') as file:
                    content += file.read()
        try:
            self.css['markdown'] = content.format(**os.environ)
        except KeyError as e:
            pass  # ignore missing env vars

    def get_default(self):
        """Set default markdown CSS"""
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
