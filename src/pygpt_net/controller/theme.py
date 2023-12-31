#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
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
        self.css = {}  # external custom rules

    def setup(self):
        """Setup theme"""
        # load highlighter CSS rules
        self.load_highlighter()

        # setup themes menu
        themes = self.get_themes_list()
        for theme in themes:
            name = self.trans_theme(theme)
            self.window.ui.menu['theme'][theme] = QAction(name, self.window, checkable=True)
            self.window.ui.menu['theme'][theme].triggered.connect(
                lambda checked=None, theme=theme: self.window.controller.theme.toggle(theme))
            self.window.ui.menu['menu.theme'].addAction(self.window.ui.menu['theme'][theme])

        # apply current theme to nodes
        self.reload(force=False)

    def update_menu(self):
        """Update theme menu"""
        for theme in self.window.ui.menu['theme']:
            self.window.ui.menu['theme'][theme].setChecked(False)
        current = self.window.core.config.get('theme')
        if current in self.window.ui.menu['theme']:
            self.window.ui.menu['theme'][current].setChecked(True)

    def toggle(self, name: str, force: bool = True):
        """
        Toggle theme by name

        :param name: theme name
        :param force: force theme change (manual toggle)
        """
        if force:
            self.window.controller.ui.store_state()  # store state before theme change

        self.window.core.config.set('theme', name)
        self.window.core.config.save()
        self.load_highlighter()
        self.apply_nodes()
        self.apply_window(name + '.xml', self.get_custom_css(name))  # style.css = additional custom stylesheet
        self.update_menu()

        if force:
            self.window.controller.ui.restore_state()  # restore state after theme change

    def reload(self, force: bool = True):
        """
        Reload current theme

        :param force: force theme change (manual)
        """
        self.toggle(self.window.core.config.get('theme'), force=force)

    def get_css(self, name: str) -> dict:
        """
        Return CSS rules for element

        :param name: css element name
        :return: dictionary with css rules
        """
        if name in self.css:
            return self.css[name]
        return {}

    def apply_node(self, key: str, type: str):
        """
        Apply stylesheet to node

        :param key: UI node key
        :param type: stylesheet type
        """
        if key not in self.window.ui.nodes:
            return

        if type == 'toolbox':
            self.window.ui.nodes[key].setStyleSheet(self.get_style('toolbox'))
        elif type == 'chat_output':
            self.window.ui.nodes[key].setStyleSheet(self.get_style('chat_output'))
        elif type == 'chat_input':
            self.window.ui.nodes[key].setStyleSheet(self.get_style('chat_input'))
        elif type == 'ctx.list':
            self.window.ui.nodes[key].setStyleSheet(self.get_style('ctx.list'))
        elif type == 'text_faded':
            self.window.ui.nodes[key].setStyleSheet(self.get_style('text_faded'))

    def apply_nodes(self, all: bool = True):
        """
        Apply stylesheets to nodes

        :param all: apply also to highlighter
        """
        nodes = {
            'chat_input': [
                'input',
            ],
            'chat_output': [
                'output',
            ],
            'ctx.list': [
                'ctx.list',
            ],
            'toolbox': [
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
            ],
            'text_faded': [
                'input.label',
                'input.counter',
                'prompt.context',
                'chat.label',
                'chat.model',
            ],
        }

        # apply to nodes
        for type in nodes:
            for key in nodes[type]:
                self.apply_node(key, type)

        # apply to notepads
        num_notepads = self.window.controller.notepad.get_num_notepads()
        if num_notepads > 0:
            for id in range(1, num_notepads + 1):
                if id in self.window.ui.notepad:
                    self.window.ui.notepad[id].setStyleSheet(self.get_style('chat_output'))

        # apply CSS to syntax highlighter
        if all:
            self.apply_highlighter()

    def get_style(self, element: str) -> str:
        """
        Return CSS style for element

        :param element: type of element
        :return: CSS style for element
        """
        theme = self.window.core.config.get('theme')
        # get theme element style
        if element == "chat_output":
            return 'font-size: {}px;'.format(self.window.core.config.get('font_size'))
        elif element == "chat_input":
            return 'font-size: {}px;'.format(self.window.core.config.get('font_size.input'))
        elif element == "ctx.list":
            return 'font-size: {}px;'.format(self.window.core.config.get('font_size.ctx'))
        elif element == "toolbox":
            return 'font-size: {}px;'.format(self.window.core.config.get('font_size.toolbox'))
        elif element == "text_bold":
            return "font-weight: bold;"
        elif element == "text_small":
            return ""
            # return "font-size: 8px;"  <-- too small on big screens
        elif element == "text_faded":
            if theme.startswith('light'):
                return "color: #414141;"
            else:
                return "color: #999;"
            # return "font-size: 8px; color: #999;"  <-- too small on big screens

    def apply_highlighter(self):
        """Apply CSS to syntax highlight"""
        self.window.ui.nodes['output_highlighter'].setTheme(self.get_css('highlighter'))

    def load_highlighter(self):
        """Load syntax highlighter CSS from json file"""
        theme = self.window.core.config.get('theme')

        base_name = 'highlighter'

        # check in user directory first
        path = os.path.join(self.window.core.config.get_user_path(), 'css', base_name + '.' + theme + '.json')
        if not os.path.exists(path):
            path = os.path.join(self.window.core.config.get_user_path(), 'css', base_name + '.json')

        # check in app directory
        if not os.path.exists(path):
            path = os.path.join(self.window.core.config.get_app_path(), 'data', 'css', base_name + '.' + theme + '.json')
            if not os.path.exists(path):
                path = os.path.join(self.window.core.config.get_app_path(), 'data', 'css', base_name + '.json')

        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    self.css['highlighter'] = json.load(f)
            except Exception as e:
                self.window.core.debug.log(e)

    def apply_window(self, theme: str = 'dark_teal.xml', custom: str = None):
        """
        Update material theme and apply custom CSS

        :param theme: material theme filename (e.g. dark_teal.xml)
        :param custom: additional custom CSS filename
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
        if custom is not None:
            stylesheet = self.window.styleSheet()
            # check for override in user directory
            path = os.path.join(self.window.core.config.get_user_path(), 'css', custom)
            if not os.path.exists(path):
                # check in app directory
                path = os.path.join(self.window.core.config.get_app_path(), 'data', 'css', custom)
            if os.path.exists(path):
                with open(path) as file:
                    self.window.setStyleSheet(stylesheet + file.read().format(**os.environ))

    def get_custom_css(self, name: str) -> str:
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
                # check for override in user directory
                path = os.path.join(self.window.core.config.get_user_path(), 'css', tmp)
                if not os.path.exists(path):
                    # check in app directory
                    path = os.path.join(self.window.core.config.get_app_path(), 'data', 'css', tmp)
                if os.path.exists(path):
                    filename = tmp

                # per theme name
                tmp = name + '.css'
                # check for override in user directory
                path = os.path.join(self.window.core.config.get_user_path(), 'css', tmp)
                if not os.path.exists(path):
                    # check in app directory
                    path = os.path.join(self.window.core.config.get_app_path(), 'data', 'css', tmp)
                if os.path.exists(path):
                    filename = tmp

        return filename

    def trans_theme(self, theme: str) -> str:
        """
        Translate theme name

        :param theme: theme name
        :return: translated theme name
        """
        return theme \
            .replace('_', ' ').title() \
            .replace('Dark ', trans('theme.dark') + ': ') \
            .replace('Light ', trans('theme.light') + ': ')

    def get_themes_list(self) -> list:
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
            'light_yellow'
        ]
