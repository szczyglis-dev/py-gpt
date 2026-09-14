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
from typing import Any, Optional

from PySide6.QtWidgets import QApplication

from pygpt_net.core.events import RenderEvent
from pygpt_net.utils import trans, freeze_updates

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
        self.current_theme = None
        self.current_tooltips = None
        self._current_material_signature = None
        self._current_markdown_signature = None

    def setup(self):
        """Setup theme"""
        # Normalize the retired Blocks web style before any renderer CSS is loaded.
        if self.window.core.config.get("theme.style") == "blocks":
            self.window.core.config.set("theme.style", "chatgpt")
            self.window.core.config.save()
        current_theme = self.window.core.config.get('theme')
        normalized_theme = self.common.normalize_theme(current_theme)
        if normalized_theme != current_theme:
            self.window.core.config.set('theme', normalized_theme)
            self.window.core.config.save()
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
        current = self.window.core.config.get('theme')
        if name == current:
            return
        self.window.update_status(trans("status.reloading"))
        QApplication.processEvents()
        with freeze_updates(self.window):
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
        name = self.common.normalize_theme(name)
        self.current_theme = name
        window = self.window
        core = window.core
        controller = window.controller

        if force:
            controller.ui.store_state()

        core.config.set('theme', name)
        core.config.save()

        custom, is_custom = self._get_theme_assets(name)
        material_signature = self._get_material_signature(name, custom, is_custom)

        # Apply the expensive global Qt stylesheet only once.  Node-specific
        # styles are applied afterwards so they are not immediately overwritten
        # by qt-material.  Their web theme event is suppressed because
        # markdown.update() below emits the single renderer refresh we need.
        self.apply(
            f'{name}.xml',
            custom,
            is_custom=is_custom,
        )
        self.nodes.apply_all(dispatch_theme=False)
        self.markdown.update(force=False)
        self.menu.update_list()
        self.menu.update_density()
        self.menu.update_syntax()

        self._remember_state(
            material_signature=material_signature,
            markdown_signature=self._get_markdown_signature(),
        )

        if force:
            controller.ui.restore_state()

    def toggle_style(self, name: str):
        """
        Toggle theme style (web)

        :param name: web style name
        """
        # The legacy 'blocks' style was removed in 2.8.16. Keep a runtime
        # fallback for old profiles/custom calls that still reference it.
        if name == "blocks":
            name = "chatgpt"
        styles_list = self.common.get_styles_list()
        if name not in styles_list:
            name = "chatgpt"
        QApplication.processEvents()
        core = self.window.core
        core.config.set('theme.style', name)
        core.config.save()

        # A web style change only affects renderer CSS.  Re-applying the whole
        # qt-material theme here is unnecessary and is especially expensive in
        # profiles with many widgets/WebViews.
        self.markdown.update(force=False)
        self.menu.update_list()
        self._remember_state(markdown_signature=self._get_markdown_signature())

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
            self.current_tooltips = state
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
        self.current_theme = self.window.core.config.get('theme')
        self.toggle(self.current_theme, force=force)

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
            theme: str = 'dark.xml',
            custom: Optional[str] = None,
            is_custom: bool = False,
    ):
        """
        Update material theme and apply custom CSS.

        :param theme: material theme filename (e.g. dark.xml)
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

        material_theme = theme
        if is_custom:
            material_theme = os.path.join(cfg.get_app_path(), 'data', 'themes', theme)

        window.apply_stylesheet(
            window,
            material_theme,
            invert_secondary=is_light,
            extra=extra,
        )

        content_parts = []
        if custom is not None:
            app_css = os.path.join(cfg.get_app_path(), 'data', 'css', custom)
            if os.path.exists(app_css):
                with open(app_css, 'r', encoding='utf-8') as file:
                    content_parts.append(file.read())

            if core.platforms.is_windows() and not cfg.is_compiled():
                content_parts.append(self.common.get_windows_fix())


        if core.platforms.is_windows():
            fix_css = 'fix_windows.light.css' if is_light else 'fix_windows.dark.css'
            path = os.path.join(cfg.get_app_path(), 'data', 'css', fix_css)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as file:
                    content_parts.append(file.read())

        if (custom is not None or is_custom) and content_parts:
            try:
                stylesheet = window.styleSheet()
                window.setStyleSheet(stylesheet + ''.join(content_parts).format(**os.environ))
            except KeyError:
                pass

    @staticmethod
    def _file_signature(path: str):
        """Return a cheap signature for a theme/CSS file."""
        try:
            stat = os.stat(path)
            return path, stat.st_mtime_ns, stat.st_size
        except (OSError, TypeError):
            return None

    def _get_theme_assets(self, name: str):
        """Return extra CSS name and whether the base theme is custom."""
        custom = self.common.get_extra_css(name)
        is_custom = name in self.common.get_custom_themes_list()
        return custom, is_custom

    def _get_material_signature(
            self,
            name: str,
            custom: Optional[str],
            is_custom: bool,
    ):
        """Build a change signature for the native Qt theme."""
        cfg = self.window.core.config
        core = self.window.core
        app_path = cfg.get_app_path()
        is_light = str(name).startswith('light')
        parts = [
            str(name),
            cfg.get('layout.density'),
            bool(is_custom),
            custom,
        ]

        if custom is not None:
            parts.append(self._file_signature(os.path.join(app_path, 'data', 'css', custom)))

        if is_custom:
            parts.append(self._file_signature(
                os.path.join(app_path, 'data', 'themes', f'{name}.xml')
            ))

        if core.platforms.is_windows():
            parts.append(self._file_signature(os.path.join(
                app_path,
                'data',
                'css',
                'fix_windows.light.css' if is_light else 'fix_windows.dark.css',
            )))
            if custom is not None and not cfg.is_compiled():
                svg_supported = bool(core.platforms.is_svg_supported())
                parts.append(('svg_supported', svg_supported))
                if not svg_supported:
                    parts.append(self._file_signature(os.path.join(
                        app_path, 'data', 'css', 'fix_windows.css'
                    )))

        return tuple(parts)

    def _get_markdown_signature(self):
        """Build a signature for renderer CSS used by the active profile."""
        cfg = self.window.core.config
        app_path = cfg.get_app_path()
        theme = self.common.normalize_theme(cfg.get('theme'))
        web_style = str(cfg.get('theme.style', 'chatgpt'))
        if web_style == 'blocks':
            web_style = 'chatgpt'

        color = '.light' if theme == 'light' else '.dark'

        files = []
        for base_name, suffix in (('markdown', ''), ('web', '-' + web_style)):
            file_base = base_name + suffix + '.css'
            file_color = base_name + suffix + color + '.css'
            css_dir = os.path.join(app_path, 'data', 'css')
            files.append(self._file_signature(os.path.join(css_dir, file_base)))
            files.append(self._file_signature(os.path.join(css_dir, file_color)))

        return theme, web_style, tuple(files)

    def _remember_state(
            self,
            material_signature=None,
            markdown_signature=None,
    ):
        """Remember active theme state for cheap profile synchronization."""
        cfg = self.window.core.config
        self.current_theme = cfg.get('theme')
        self.current_tooltips = bool(cfg.get('layout.tooltips'))
        if material_signature is not None:
            self._current_material_signature = material_signature
        if markdown_signature is not None:
            self._current_markdown_signature = markdown_signature

    def style(self, element: str) -> str:
        """
        Return CSS style for element (alias)

        :param element: type of element
        :return: CSS style for element
        """
        return self.common.get_style(element)

    def reload_all(self):
        """
        Synchronize theme state after a profile/workdir reload.

        Profile switching already reloads the rest of the application.  Do not
        route it through setup() + update_style(), because that used to apply
        the global qt-material stylesheet twice and emit multiple renderer theme
        events for a single switch.
        """
        cfg = self.window.core.config

        if cfg.get('theme.style') == 'blocks':
            cfg.set('theme.style', 'chatgpt')
            cfg.save()

        stored_name = cfg.get('theme')
        name = self.common.normalize_theme(stored_name)
        if name != stored_name:
            cfg.set('theme', name)
            cfg.save()
        custom, is_custom = self._get_theme_assets(name)
        material_signature = self._get_material_signature(name, custom, is_custom)
        markdown_signature = self._get_markdown_signature()

        material_changed = material_signature != self._current_material_signature
        markdown_changed = (
            material_changed
            or markdown_signature != self._current_markdown_signature
        )
        tooltips = bool(cfg.get('layout.tooltips'))
        tooltips_changed = tooltips != self.current_tooltips

        if material_changed:
            self.current_theme = name
            self.apply(
                f'{name}.xml',
                custom,
                is_custom=is_custom,
            )
            self.nodes.apply_all(dispatch_theme=False)

        # Preserve the single renderer refresh that a profile reload needs for
        # profile-scoped render flags (syntax, blocks, etc.).  markdown.update()
        # already emits it when renderer CSS/native theme changed.
        if markdown_changed:
            self.markdown.update(force=False)
        else:
            self.window.dispatch(RenderEvent(RenderEvent.ON_THEME_CHANGE))

        if tooltips_changed:
            self.common.toggle_tooltips()

        self.menu.update_list()
        self.menu.update_density()
        self.menu.update_syntax()
        self._remember_state(
            material_signature=material_signature,
            markdown_signature=markdown_signature,
        )

    def is_dark_theme(self) -> bool:
        """
        Check if current theme is dark

        :return: True if dark theme, False otherwise
        """
        current = self.window.core.config.get('theme')
        return self.common.normalize_theme(current) == 'dark'