#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.25 20:00:00                  #
# ================================================== #

import os
from typing import Any, Optional

from PySide6.QtWidgets import QApplication

from pygpt_net.core.events import RenderEvent
from pygpt_net.utils import trans

from .common import Common
from .markdown import Markdown
from .menu import Menu
from .nodes import Nodes

class Theme:
    def __init__(self, window=None):
        """
        Theme controller

        :param window: Window instance
        """
        self.window = window
        self.common = Common(window)
        self.markdown = Markdown(window)
        self.menu = Menu(window)
        self.nodes = Nodes(window)

    def setup(self):
        """Setup theme"""
        self.markdown.load()
        self.menu.setup_list()
        self.menu.setup_density()
        self.menu.setup_syntax()
        self.common.toggle_tooltips()
        self.reload(force=False)

    def toggle_theme_by_menu(self, name):
        """
        Toggle theme by menu action

        :param name: theme name
        """
        self.window.update_status(trans("status.reloading"))
        QApplication.processEvents()
        self.toggle(name, force=True)
        self.window.update_status("")

    def toggle_option_by_menu(self, name: str, value: Any = None):
        """
        Toggle theme option by menu action

        :param name: option name
        :param value: option value
        """
        self.window.update_status(trans("status.reloading"))
        QApplication.processEvents()
        self.toggle_option(name, value)
        self.window.update_status("")

    def toggle(
            self,
            name: str,
            force: bool = True
    ):
        """
        Toggle theme by name

        :param name: theme name
        :param force: force theme change (manual trigger)
        """
        window = self.window
        core = window.core
        controller = window.controller

        if force:
            controller.ui.store_state()

        core.config.set('theme', name)
        core.config.save()
        self.nodes.apply_all()

        custom_themes = controller.theme.common.get_custom_themes_list()
        is_custom = name in custom_themes

        self.apply(
            f'{name}.xml',
            self.common.get_extra_css(name),
            is_custom=is_custom,
        )

        self.markdown.update(force=False)
        self.menu.update_list()
        self.menu.update_syntax()

        if force:
            controller.ui.restore_state()

    def toggle_style(self, name: str):
        """
        Toggle theme style (web)

        :param name: web style name
        """
        QApplication.processEvents()
        core = self.window.core
        core.config.set('theme.style', name)
        core.config.save()
        event = RenderEvent(RenderEvent.ON_THEME_CHANGE)
        self.window.dispatch(event)
        self.reload()

    def toggle_option(
            self,
            name: str,
            value: Any = None
    ):
        """
        Toggle theme menu option

        :param name: option name
        :param value: option value
        """
        QApplication.processEvents()
        window = self.window
        core = window.core
        cfg = core.config

        if name == 'layout.tooltips':
            state = not bool(cfg.get(name))
            cfg.set(name, state)
            window.controller.config.checkbox.apply('config', 'layout.tooltips', {'value': state})
            self.common.toggle_tooltips()
        elif name == 'layout.density':
            val = int(value)
            cfg.set(name, val)
            window.controller.config.slider.apply('config', 'layout.density', {'value': val})
            self.reload()
            self.menu.update_density()
        elif name == 'render.blocks':
            state = not bool(cfg.get(name))
            cfg.set(name, state)
            event = RenderEvent(RenderEvent.ON_THEME_CHANGE)
            window.dispatch(event)
            self.reload()

        cfg.save()
        self.nodes.apply_all()

    def toggle_syntax(
            self,
            name: str,
            update_menu: bool = False
    ):
        """
        Toggle syntax highlight

        :param name: syntax style name
        :param update_menu: update menu
        """
        core = self.window.core
        core.config.set("render.code_syntax", name)
        core.config.save()
        event = RenderEvent(RenderEvent.ON_THEME_CHANGE)
        self.window.dispatch(event)
        if update_menu:
            self.menu.update_syntax()

    def update_style(self):
        """Update style"""
        self.toggle_style(self.window.core.config.get('theme.style'))

    def update_theme(self, force: bool = True):
        """
        Update theme

        :param force: force theme change (manual trigger)
        """
        self.toggle(self.window.core.config.get('theme'), force=force)

    def update_syntax(self):
        """Update syntax menu"""
        self.toggle_syntax(self.window.core.config.get('render.code_syntax'), update_menu=True)

    def reload(self, force: bool = True):
        """
        Reload current theme

        :param force: force theme change (manual trigger)
        """
        self.update_theme(force=force)

    def apply(
            self,
            theme: str = 'dark_teal.xml',
            custom: Optional[str] = None,
            is_custom: bool = False
    ):
        """
        Update material theme and apply custom CSS

        :param theme: material theme filename (e.g. dark_teal.xml)
        :param custom: additional stylesheet filename (e.g. style.css)
        :param is_custom: is custom base theme
        """
        window = self.window
        core = window.core
        cfg = core.config

        base_name = os.path.splitext(os.path.basename(theme))[0]
        is_light = base_name.startswith('light')
        extra = {
            'density_scale': cfg.get('layout.density'),
            'pyside6': True,
        }

        if is_custom:
            theme = os.path.join(cfg.get_app_path(), 'data', 'themes', theme)

        window.apply_stylesheet(window, theme, invert_secondary=is_light, extra=extra)

        content_parts = []
        if custom is not None:
            app_css = os.path.join(cfg.get_app_path(), 'data', 'css', custom)
            user_css = os.path.join(cfg.get_user_path(), 'css', custom)

            if os.path.exists(app_css):
                with open(app_css, 'r', encoding='utf-8') as file:
                    content_parts.append(file.read())
            if os.path.exists(user_css):
                with open(user_css, 'r', encoding='utf-8') as file:
                    content_parts.append(file.read())

            if core.platforms.is_windows() and not cfg.is_compiled():
                content_parts.append(self.common.get_windows_fix())

        if is_custom:
            theme_css = os.path.join(cfg.get_app_path(), 'data', 'themes', f'{base_name}.css')
            if os.path.exists(theme_css):
                with open(theme_css, 'r', encoding='utf-8') as file:
                    content_parts.append(file.read())

        if core.platforms.is_windows():
            fix_css = 'fix_windows.light.css' if is_light else 'fix_windows.dark.css'
            path = os.path.join(cfg.get_app_path(), 'data', 'css', fix_css)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as file:
                    content_parts.append(file.read())

        if custom is not None or is_custom:
            if content_parts:
                try:
                    stylesheet = window.styleSheet()
                    window.setStyleSheet(stylesheet + ''.join(content_parts).format(**os.environ))
                except KeyError:
                    pass

    def style(self, element: str) -> str:
        """
        Return CSS style for element (alias)

        :param element: type of element
        :return: CSS style for element
        """
        return self.common.get_style(element)

    def reload_all(self, prev_theme: Optional[str] = None):
        """
        Reload all

        :param prev_theme: previous theme name
        """
        if not prev_theme or prev_theme != self.window.core.config.get('theme'):
            self.setup()
            self.update_style()
        self.update_syntax()