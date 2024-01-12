#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.04 03:00:00                  #
# ================================================== #

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
        self.css = {}  # external styles

    def setup(self):
        """Setup theme"""
        # load markdown CSS
        self.load_markdown()

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
        :param force: force theme change (manual trigger)
        """
        if force:
            self.window.controller.ui.store_state()  # store state before theme change

        self.window.core.config.set('theme', name)
        self.window.core.config.save()
        self.apply_nodes()
        self.apply_window(name + '.xml', self.get_custom_css(name))  # style.css = additional custom stylesheet

        # apply markdown CSS
        self.update_markdown(force=False)

        # update themes menu
        self.update_menu()

        if force:
            self.window.controller.ui.restore_state()  # restore state after theme change

    def update_markdown(self, force: bool = False):
        """
        Update markdown styles

        :param force: force theme change (manual trigger)
        """
        if force:
            self.window.controller.ui.store_state()  # store state before theme change

        if self.window.core.config.get('theme.markdown'):
            self.load_markdown()
        else:
            self.set_default_markdown()
        self.apply_markdown()

        if force:
            self.window.controller.ui.restore_state()  # restore state after theme change

    def reload(self, force: bool = True):
        """
        Reload current theme

        :param force: force theme change (manual trigger)
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

    def set_default_markdown(self):
        """Set default markdown CSS"""
        self.css['markdown'] = self.get_default_markdown()

    def apply_markdown(self):
        """Apply CSS to markdown formatter"""
        self.window.ui.nodes['output'].document().setDefaultStyleSheet(self.css['markdown'])
        self.window.ui.nodes['output'].document().setMarkdown(self.window.ui.nodes['output'].document().toMarkdown())
        self.window.controller.ctx.refresh_output()

    def clear_markdown(self):
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

    def load_markdown(self):
        """Load markdown styles"""
        theme = self.window.core.config.get('theme')
        name = 'markdown'
        color_name = 'markdown'
        if theme.startswith('light'):
            color_name += '.light'
        else:
            color_name += '.dark'

        paths = []
        paths.append(os.path.join(self.window.core.config.get_user_path(), 'css', color_name + '.css'))
        paths.append(os.path.join(self.window.core.config.get_user_path(), 'css', name + '.css'))
        paths.append(os.path.join(self.window.core.config.get_app_path(), 'data', 'css', color_name + '.css'))
        paths.append(os.path.join(self.window.core.config.get_app_path(), 'data', 'css', name + '.css'))
        for path in paths:
            if os.path.exists(path):
                with open(path, 'r') as file:
                    try:
                        self.css['markdown'] = file.read().format(**os.environ)
                    except KeyError as e:
                        pass  # ignore missing env vars
                break

    def apply_window(self, theme: str = 'dark_teal.xml', custom: str = None):
        """
        Update material theme and apply custom CSS

        :param theme: material theme filename (e.g. dark_teal.xml)
        :param custom: additional custom stylesheet filename (e.g. style.css)
        """
        inverse = False
        if theme.startswith('light'):
            inverse = True
        extra = {
            'density_scale': self.window.core.config.get('layout.density'),
            'pyside6': True,
        }
        self.window.apply_stylesheet(self.window, theme, invert_secondary=inverse, extra=extra)

        # append custom stylesheet
        if custom is not None:
            stylesheet = self.window.styleSheet()
            paths = []
            paths.append(os.path.join(self.window.core.config.get_user_path(), 'css', custom))
            paths.append(os.path.join(self.window.core.config.get_app_path(), 'data', 'css', custom))
            for path in paths:
                if os.path.exists(path):
                    with open(path) as file:
                        try:
                            content = file.read()
                            # windows checkbox + radio fix
                            if self.window.core.platforms.is_windows() and not self.window.core.config.is_compiled():
                                content += """
                                QCheckBox::indicator:checked {{
                                  background-color: {QTMATERIAL_PRIMARYCOLOR}; 
                                }}
                                QCheckBox::indicator:unchecked {{ 
                                  background-color: {QTMATERIAL_SECONDARYCOLOR}; 
                                }}
                                
                                QRadioButton::indicator:checked {{
                                  background-color: {QTMATERIAL_PRIMARYCOLOR}; 
                                }} 
                                QCheckBox::indicator:unchecked {{ 
                                  background-color: {QTMATERIAL_SECONDARYCOLOR}; 
                                }}
                                QRadioButton::indicator:unchecked {{
                                  background-color: {QTMATERIAL_SECONDARYCOLOR}; 
                                }}
                                
                                QMenu::indicator:checked {{ 
                                  background-color: {QTMATERIAL_PRIMARYCOLOR}; 
                                }} 
                                QMenu::indicator:unchecked {{ 
                                  background-color: {QTMATERIAL_SECONDARYCOLOR}; 
                                }}
                                """
                            self.window.setStyleSheet(stylesheet + content.format(**os.environ))
                        except KeyError as e:
                            pass  # ignore missing env variables
                    break

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

    def get_default_markdown(self):
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
                "a": "#fff",
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
