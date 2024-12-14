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
from typing import List

from pygpt_net.utils import trans


class Common:
    def __init__(self, window=None):
        """
        Theme common controller

        :param window: Window instance
        """
        self.window = window

    def get_extra_css(self, name: str) -> str:
        """
        Return custom css filename for specified theme

        :param name: theme name
        :return: custom css filename (e.g. style.dark.css)
        """
        # check per theme style css
        filename = 'style.css'
        if filename is not None:
            # per theme mode (light / dark)
            tmp = None
            if name.startswith('light_'):
                tmp = 'style.light.css'
            elif name.startswith('dark_'):
                tmp = 'style.dark.css'
            if tmp is not None:
                paths = []
                paths.append(os.path.join(self.window.core.config.get_user_path(), 'css', name + '.css'))
                paths.append(os.path.join(self.window.core.config.get_app_path(), 'data', 'css', name + '.css'))
                paths.append(os.path.join(self.window.core.config.get_user_path(), 'css', tmp))
                paths.append(os.path.join(self.window.core.config.get_app_path(), 'data', 'css', tmp))
                for path in paths:
                    if os.path.exists(path):
                        filename = tmp
                        break
        return filename

    def toggle_tooltips(self):
        """Toggle visibility of static tooltips"""
        nodes = [
            'tip.input.attachments',
            'tip.input.attachments.uploaded',
            'tip.output.tab.calendar',
            'tip.output.tab.draw',
            'tip.output.tab.files',
            'tip.output.tab.notepad',
            'tip.toolbox.assistants',
            'tip.toolbox.ctx',
            # 'tip.toolbox.indexes',
            'tip.toolbox.mode',
            'tip.toolbox.presets',
            'tip.toolbox.prompt',
        ]
        state = self.window.core.config.get('layout.tooltips')
        if state:
            for node in nodes:
                if node in self.window.ui.nodes:
                    self.window.ui.nodes[node].setVisible(True)
        else:
            for node in nodes:
                if node in self.window.ui.nodes:
                    self.window.ui.nodes[node].setVisible(False)

        self.window.ui.menu['theme.tooltips'].setChecked(state)

    def translate(self, theme: str) -> str:
        """
        Translate theme name

        :param theme: theme name
        :return: translated theme name
        """
        return theme \
            .replace('_', ' ').title() \
            .replace('Dark ', trans('theme.dark') + ': ') \
            .replace('Light ', trans('theme.light') + ': ')

    def get_style(self, element: str) -> str:
        """
        Return CSS style for element

        :param element: type of element
        :return: CSS style for element
        """
        # get font size
        if element == "font.chat.output":
            return 'font-size: {}px;'.format(self.window.core.config.get('font_size'))
        elif element == "font.chat.input":
            return 'font-size: {}px;'.format(self.window.core.config.get('font_size.input'))
        elif element == "font.ctx.list":
            return 'font-size: {}px;'.format(self.window.core.config.get('font_size.ctx'))
        elif element == "font.toolbox":
            return 'font-size: {}px;'.format(self.window.core.config.get('font_size.toolbox'))

    def get_themes_list(self) -> List[str]:
        """
        Return a list of available themes

        :return: list of themes names
        """
        return [
            'dark_amber',
            'dark_blue',
            'dark_cyan',
            'dark_lightgreen',
            'dark_pink',
            'dark_purple',
            'dark_red',
            'dark_teal',
            'dark_yellow',
            'light_amber',
            'light_blue',
            'light_cyan',
            'light_cyan_500',
            'light_lightgreen',
            'light_pink',
            'light_purple',
            'light_red',
            'light_teal',
            'light_yellow',
        ]

    def get_windows_fix(self) -> str:
        """
        Return Windows checkbox button + radio button fix

        :return: stylesheet with fix
        """
        # abort if SVG is supported (no need to fix missing DLLs)
        if self.window.core.platforms.is_svg_supported():
            return ''

        filename = 'fix_windows.css'
        paths = []
        paths.append(os.path.join(self.window.core.config.get_app_path(), 'data', 'css', filename))
        paths.append(os.path.join(self.window.core.config.get_user_path(), 'css', filename))
        content = ''
        for path in paths:
            if os.path.exists(path):
                with open(path) as file:
                    content += file.read()
        return content

    def get_styles_list(self) -> List[str]:
        """
        Return a list of available styles

        :return: list of styles names
        """
        styles = []
        app_dir = os.path.join(self.window.core.config.get_app_path(), 'data', 'css')
        user_dir = os.path.join(self.window.core.config.path, 'css')
        for path in [app_dir, user_dir]:
            if not os.path.exists(path):
                continue
            for file in os.listdir(path):
                if file.startswith("web-") and file.endswith('.css'):
                    to_replace = ['web-', '.css', '.light', '.dark']
                    for item in to_replace:
                        file = file.replace(item, '')
                    if file not in styles:
                        styles.append(file)
        return sorted(styles)
