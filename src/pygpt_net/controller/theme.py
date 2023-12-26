#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

import json
import os

from PySide6.QtGui import QAction

from pygpt_net.utils import trans


class Theme:
    def __init__(self, window=None):
        """
        Theme controller

        :param window: Window instance
        """
        self.window = window
        self.css = {}

    def load_css(self):
        """Load CSS"""
        theme = self.window.core.config.get('theme')

        # user area
        path = os.path.join(self.window.core.config.get_user_path(), 'css', 'highlighter.' + theme + '.json')
        if not os.path.exists(path):
            path = os.path.join(self.window.core.config.get_user_path(), 'css', 'highlighter.json')

        # app area
        if not os.path.exists(path):
            path = os.path.join(self.window.core.config.get_root_path(), 'data', 'css', 'highlighter.' + theme + '.json')
            if not os.path.exists(path):
                path = os.path.join(self.window.core.config.get_root_path(), 'data', 'css', 'highlighter.json')

        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    self.css['highlighter'] = json.load(f)
                    f.close()
            except Exception as e:
                self.window.core.debug.log(e)

    def get_css(self, name):
        """
        Return CSS rules

        :param name: css name
        :return: css rules
        :rtype: dict
        """
        if name in self.css:
            return self.css[name]
        return {}

    def toggle(self, name):
        """
        Toggle theme

        :param name: theme name
        """
        # check per theme style css
        custom_css = 'style.css'
        if custom_css is not None:
            # per theme mode (light / dark)
            tmp_css = None
            if name.startswith('light_'):
                tmp_css = 'style.light.css'
            elif name.startswith('dark_'):
                tmp_css = 'style.dark.css'
            if tmp_css is not None:
                # check for override in user directory
                path = os.path.join(self.window.core.config.get_user_path(), 'css', tmp_css)
                if not os.path.exists(path):
                    # check in app directory
                    path = os.path.join(self.window.core.config.get_root_path(), 'data', 'css', tmp_css)
                if os.path.exists(path):
                    custom_css = tmp_css

                # per theme name
                tmp_css = name + '.css'
                # check for override in user directory
                path = os.path.join(self.window.core.config.get_user_path(), 'css', tmp_css)
                if not os.path.exists(path):
                    # check in app directory
                    path = os.path.join(self.window.core.config.get_root_path(), 'data', 'css', tmp_css)
                if os.path.exists(path):
                    custom_css = tmp_css

        self.window.core.config.set('theme', name)
        self.window.core.config.save()
        self.load_css()
        self.apply()
        self.set_theme(name + '.xml', custom_css)  # style.css = additional custom stylesheet
        self.update()

    def apply_common(self, key):
        """Apply common theme"""
        if key in self.window.ui.nodes:
            self.window.ui.nodes[key].setStyleSheet('font-size: {}px;'
                                                    .format(self.window.core.config.get('font_size.toolbox')))  # 12px

    def apply(self, all=True):
        """Apply theme"""
        common_nodes = [
            'assistants',
            'assistants.new',
            'assistants.import',
            'assistants.label',
            'cmd.enabled',
            'dalle.options',
            'img_variants.label',
            'preset.clear',
            'preset.presets',
            'preset.presets.label',
            'preset.presets.new',
            'preset.prompt',
            'preset.prompt.label',
            'preset.temperature.label',
            'preset.use',
            'prompt.label',
            'prompt.mode',
            'prompt.mode.label',
            'prompt.model',
            'prompt.model.label',
            'temperature.label',
            'toolbox.prompt.label',
            'toolbox.preset.ai_name.label',
            'toolbox.preset.user_name.label',
            'vision.capture.auto',
            'vision.capture.enable',
            'vision.capture.label',
            'vision.capture.options',
        ]
        for node in common_nodes:
            self.apply_common(node)

        # windows
        self.window.ui.nodes['output'].setStyleSheet(self.get_style('chat_output'))
        self.window.ui.nodes['input'].setStyleSheet(self.get_style('chat_input'))
        self.window.ui.nodes['ctx.list'].setStyleSheet(self.get_style('ctx.list'))

        # notepads
        num_notepads = self.window.controller.notepad.get_num_notepads()
        if num_notepads > 0:
            for id in range(1, num_notepads + 1):
                if id in self.window.ui.notepad:
                    self.window.ui.notepad[id].setStyleSheet(self.get_style('chat_output'))

        # apply to syntax highlighter
        if all:
            self.apply_syntax_highlighter(self.window.core.config.get('theme'))

    def get_style(self, element):
        """
        Return style for element

        :param element: element name
        :return: style for element
        :rtype: str
        """
        # get theme element style
        if element == "chat_output":
            return 'font-size: {}px;'.format(self.window.core.config.get('font_size'))
        elif element == "chat_input":
            return 'font-size: {}px;'.format(self.window.core.config.get('font_size.input'))
        elif element == "ctx.list":
            return 'font-size: {}px;'.format(self.window.core.config.get('font_size.ctx'))
        elif element == "text_bold":
            return "font-weight: bold;"
        elif element == "text_small":
            return "font-size: 0.5rem;"
        elif element == "text_faded":
            return "font-size: 0.5rem; color: #999;"

    def apply_syntax_highlighter(self, theme):
        """Apply syntax highlight"""
        self.window.ui.nodes['output_highlighter'].setTheme(self.get_css('highlighter'))

    def update(self):
        """Update theme menu"""
        for theme in self.window.ui.menu['theme']:
            self.window.ui.menu['theme'][theme].setChecked(False)
        current = self.window.core.config.get('theme')
        if current in self.window.ui.menu['theme']:
            self.window.ui.menu['theme'][current].setChecked(True)

    def get_themes_list(self):
        """
        Return list of themes

        :return: list of themes
        :rtype: list
        """
        return ['dark_amber',
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
                'light_yellow'
                ]

    def trans_theme(self, theme):
        """
        Translate theme name

        :param theme: theme name
        :return: translated theme name
        :rtype: str
        """
        return theme.replace('_', ' ').title().replace('Dark ', trans('theme.dark') + ': ').replace('Light ', trans(
            'theme.light') + ': ')

    def setup(self):
        """Setup theme"""
        # load css files
        self.load_css()

        # setup menu
        themes = self.get_themes_list()
        for theme in themes:
            name = self.trans_theme(theme)
            self.window.ui.menu['theme'][theme] = QAction(name, self.window, checkable=True)
            self.window.ui.menu['theme'][theme].triggered.connect(
                lambda checked=None, theme=theme: self.window.controller.theme.toggle(theme))
            self.window.ui.menu['menu.theme'].addAction(self.window.ui.menu['theme'][theme])

        # apply theme
        theme = self.window.core.config.get('theme')
        self.toggle(theme)

    def reload(self):
        """Reload theme"""
        theme = self.window.core.config.get('theme')
        self.toggle(theme)

    def set_theme(self, theme='dark_teal.xml', custom_css=None):
        """
        Update material theme and apply custom CSS

        :param theme: material theme name
        :param custom_css: custom CSS file
        """
        inverse = False
        if theme.startswith('light'):
            inverse = True
        extra = {
            'density_scale': self.window.core.config.get('layout.density'),
            'pyside6': True,
        }
        self.window.apply_stylesheet(self.window, theme, invert_secondary=inverse, extra=extra)

        # append custom CSS
        if custom_css is not None:
            stylesheet = self.window.styleSheet()
            # check for override in user directory
            path = os.path.join(self.window.core.config.get_user_path(), 'css', custom_css)
            if not os.path.exists(path):
                # check in app directory
                path = os.path.join(self.window.core.config.get_root_path(), 'data', 'css', custom_css)
            if os.path.exists(path):
                with open(path) as file:
                    self.window.setStyleSheet(stylesheet + file.read().format(**os.environ))
