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

from pygpt_net.core.types.theme import (
    BUILTIN_THEMES,
    LIGHT_COMPATIBLE_THEMES,
    THEME_MATERIAL_ASSETS,
)
from pygpt_net.utils import trans


class Common:
    STYLE_STANDARD = "standard"
    STYLE_WIDE = "wide"
    LEGACY_STYLE_MAP = {
        "blocks": STYLE_STANDARD,
        "chatgpt": STYLE_STANDARD,
        "chatgpt_wide": STYLE_WIDE,
    }

    def __init__(self, window=None):
        """
        Theme common controller

        :param window: Window instance
        """
        self.window = window

    def get_extra_css(self, name: str) -> str:
        """Return the bundled application stylesheet for a theme."""
        theme = self.normalize_theme(name)
        return f'style.{theme}.css'

    def normalize_theme(self, theme: str) -> str:
        """
        Normalize a stored theme name to a supported built-in theme.

        :param theme: stored theme name
        :return: normalized built-in theme name
        """
        name = str(theme or '').lower()
        if name.startswith(('gray', 'grey')):
            return 'gray'
        for built_in in BUILTIN_THEMES:
            if built_in == 'gray':
                continue
            if name.startswith(built_in):
                return built_in
        return 'dark'

    def normalize_style(self, style: str) -> str:
        """Normalize current and legacy chat style identifiers."""
        name = str(style or '').lower()
        name = self.LEGACY_STYLE_MAP.get(name, name)
        if name == self.STYLE_WIDE:
            return self.STYLE_WIDE
        return self.STYLE_STANDARD

    def is_light_theme(self) -> bool:
        """
        Check if current theme is light

        :return: True if light theme, False otherwise
        """
        return self.normalize_theme(self.window.core.config.get('theme')) in LIGHT_COMPATIBLE_THEMES

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
        Translate theme name.

        :param theme: theme name
        :return: translated theme name
        """
        theme = self.normalize_theme(theme)
        return trans(f'theme.{theme}')

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
        return list(BUILTIN_THEMES)

    def get_custom_themes_list(self) -> List[str]:
        """
        Return local theme assets used by the supported built-in themes.

        :return: list of theme names
        """
        directory = os.path.join(self.window.core.config.get_app_path(), 'data', 'themes')
        return [
            name for name in THEME_MATERIAL_ASSETS
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
        """Return the built-in chat view styles."""
        return [self.STYLE_STANDARD, self.STYLE_WIDE]
