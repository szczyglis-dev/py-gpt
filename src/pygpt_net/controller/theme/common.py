#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.14 12:00:00                  #
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
        """Return the bundled application stylesheet for a theme."""
        theme = self.normalize_theme(name)
        return 'style.light.css' if theme == 'light' else 'style.dark.css'

    def normalize_theme(self, theme: str) -> str:
        """
        Normalize legacy theme names to one of the two supported themes.

        :param theme: stored theme name
        :return: ``dark`` or ``light``
        """
        name = str(theme or '').lower()
        if name.startswith('light'):
            return 'light'
        return 'dark'

    def is_light_theme(self) -> bool:
        """
        Check if current theme is light

        :return: True if light theme, False otherwise
        """
        return self.normalize_theme(self.window.core.config.get('theme')) == 'light'

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
                    try:
                        self.window.ui.nodes[node].setVisible(True)
                    except Exception:
                        pass
        else:
            for node in nodes:
                if node in self.window.ui.nodes:
                    try:
                        self.window.ui.nodes[node].setVisible(False)
                    except Exception:
                        pass

        self.window.ui.menu['theme.tooltips'].setChecked(state)

    def translate(self, theme: str) -> str:
        """
        Translate theme name

        :param theme: theme name
        :return: translated theme name
        """
        theme = self.normalize_theme(theme)
        if theme == 'light':
            return trans('theme.light')
        return trans('theme.dark')

    def get_style(self, element: str) -> str:
        """
        Return CSS style for element

        :param element: type of element
        :return: CSS style for element
        """
        # get font size
        if element == "font.chat.output":
            return 'QTextEdit {{ font-size: {}px; }}'.format(self.window.core.config.get('font_size'))
        elif element == "font.chat.input":
            return 'QTextEdit {{ font-size: {}px; }}'.format(self.window.core.config.get('font_size.input'))
        elif element == "font.ctx.list":
            return 'font-size: {}px;'.format(self.window.core.config.get('font_size.ctx'))
        elif element == "font.toolbox":
            return 'font-size: {}px;'.format(self.window.core.config.get('font_size.toolbox'))

    def get_themes_list(self) -> List[str]:
        """
        Return a list of available themes

        :return: list of themes names
        """
        return ['light', 'dark']

    def get_custom_themes_list(self) -> List[str]:
        """
        Return local theme assets used by the two supported themes.

        :return: list of theme names
        """
        directory = os.path.join(self.window.core.config.get_app_path(), 'data', 'themes')
        return [
            name for name in ('dark', 'light')
            if os.path.exists(os.path.join(directory, name + '.xml'))
        ]

    def get_windows_fix(self) -> str:
        """
        Return Windows checkbox button + radio button fix

        :return: stylesheet with fix
        """
        # abort if SVG is supported (no need to fix missing DLLs)
        if self.window.core.platforms.is_svg_supported():
            return ''

        path = os.path.join(
            self.window.core.config.get_app_path(), 'data', 'css', 'fix_windows.css'
        )
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as file:
                return file.read()
        return ''

    def get_styles_list(self) -> List[str]:
        """
        Return a list of available styles

        :return: list of styles names
        """
        styles = []
        app_dir = os.path.join(self.window.core.config.get_app_path(), 'data', 'css')
        if not os.path.exists(app_dir):
            return styles
        for filename in os.listdir(app_dir):
            if not filename.startswith("web-") or not filename.endswith('.css'):
                continue
            if filename.endswith('.darkest.css'):
                continue
            file = filename
            to_replace = ['web-', '.css', '.light', '.dark']
            for item in to_replace:
                file = file.replace(item, '')
            # 'blocks' is a retired web style; old profiles fall back to chatgpt.
            if file == 'blocks':
                continue
            if file not in styles:
                styles.append(file)
        return sorted(styles)
