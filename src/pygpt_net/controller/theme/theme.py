#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 22:05:00                  #
# ================================================== #

import os
from typing import Any

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
        """Setup theme."""
        stored_style = self.window.core.config.get("theme.style")
        normalized_style = self.common.normalize_style(stored_style)
        if normalized_style != stored_style:
            self.window.core.config.set("theme.style", normalized_style)
            self.window.core.config.save()

        current_theme = self.window.core.config.get("theme")
        normalized_theme = self.common.normalize_theme(current_theme)
        if normalized_theme != current_theme:
            self.window.core.config.set("theme", normalized_theme)
            self.window.core.config.save()

        self.markdown.load()
        self.menu.setup_list()
        self.menu.setup_density()
        self.menu.setup_syntax()
        self.common.toggle_tooltips()
        self.reload(force=False)

    def toggle_theme_by_menu(self, name):
        """Toggle theme by menu action."""
        current = self.window.core.config.get("theme")
        if name == current:
            return
        self.window.update_status(trans("status.reloading"))
        QApplication.processEvents()
        with freeze_updates(self.window):
            self.toggle(name, force=True)
        self.window.update_status("")

    def toggle_option_by_menu(self, name: str, value: Any = None):
        """Toggle theme option by menu action."""
        self.window.update_status(trans("status.reloading"))
        QApplication.processEvents()
        self.toggle_option(name, value)
        self.window.update_status("")

    def toggle(self, name: str, force: bool = True):
        """Toggle theme by ID."""
        name = self.common.normalize_theme(name)
        self.current_theme = name
        window = self.window
        core = window.core
        controller = window.controller

        if force:
            controller.ui.store_state()

        core.config.set("theme", name)
        core.config.save()

        material_signature = self._get_material_signature(name)

        # qt-material is applied first, then app.css layers are appended. This
        # keeps the global stylesheet as the base and theme/profile CSS as
        # increasingly specific overrides.
        self.apply(name)
        self.nodes.apply_all(dispatch_theme=False)
        self.markdown.update(force=False)
        self.menu.setup_list()  # also discovers newly added workdir themes
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
        """Toggle chat layout style (Standard/Wide)."""
        name = self.common.normalize_style(name)
        styles_list = self.common.get_styles_list()
        if name not in styles_list:
            name = self.common.STYLE_STANDARD
        QApplication.processEvents()
        core = self.window.core
        core.config.set("theme.style", name)
        core.config.save()

        self.markdown.update(force=False)
        self.menu.update_list()
        self._sync_chat_input_width()
        self._remember_state(markdown_signature=self._get_markdown_signature())

    def toggle_option(self, name: str, value: Any = None):
        """Toggle theme menu option."""
        QApplication.processEvents()
        window = self.window
        core = window.core
        cfg = core.config

        if name == "layout.tooltips":
            state = not bool(cfg.get(name))
            cfg.set(name, state)
            window.controller.config.checkbox.apply(
                "config", "layout.tooltips", {"value": state}
            )
            self.common.toggle_tooltips()
            self.current_tooltips = state
        elif name == "layout.density":
            val = int(value)
            cfg.set(name, val)
            window.controller.config.slider.apply(
                "config", "layout.density", {"value": val}
            )
            self.reload()
            self.menu.update_density()
        elif name == "render.blocks":
            state = not bool(cfg.get(name))
            cfg.set(name, state)
            event = RenderEvent(RenderEvent.ON_THEME_CHANGE)
            window.dispatch(event)
            self.reload()

        cfg.save()
        self.nodes.apply_all()

    def toggle_syntax(self, name: str, update_menu: bool = False):
        """Toggle syntax highlight style."""
        core = self.window.core
        core.config.set("render.code_syntax", name)
        core.config.save()
        event = RenderEvent(RenderEvent.ON_THEME_CHANGE)
        self.window.dispatch(event)
        if update_menu:
            self.menu.update_syntax()

    def update_style(self):
        """Update chat style."""
        self.toggle_style(self.window.core.config.get("theme.style"))

    def update_theme(self, force: bool = True):
        """Update current theme."""
        self.current_theme = self.window.core.config.get("theme")
        self.toggle(self.current_theme, force=force)

    def update_syntax(self):
        """Update syntax menu."""
        self.toggle_syntax(
            self.window.core.config.get("render.code_syntax"),
            update_menu=True,
        )

    def reload(self, force: bool = True):
        """Reload current theme."""
        self.update_theme(force=force)

    @staticmethod
    def _read_file(path: str) -> str:
        """Read a UTF-8 stylesheet, returning an empty string on failure."""
        try:
            with open(path, "r", encoding="utf-8") as file:
                return file.read()
        except OSError:
            return ""

    def apply(
            self,
            theme: str = "dark",
            custom=None,
            is_custom: bool = False,
    ):
        """
        Apply the material XML palette and native application CSS layers.

        ``custom`` and ``is_custom`` are retained only for call compatibility
        with older controller/tests; asset discovery now comes from theme
        directories.

        Layer order for ``app.css`` is:
        1. bundled ``data/css/app.css`` (always the global base),
        2. bundled ``data/css/<theme-id>/app.css``,
        3. profile ``%workdir%/css/app.css`` when present,
        4. profile ``%workdir%/css/<theme-id>/app.css`` when present.

        ``app.xml`` is resolved from the profile theme first, then the bundled
        theme. A completely custom theme without XML falls back to the bundled
        Light/Dark XML selected by its runtime compatibility type.
        """
        window = self.window
        core = window.core
        cfg = core.config
        name = self.common.normalize_theme(
            os.path.splitext(os.path.basename(str(theme or "dark")))[0]
        )
        is_light = self.common.is_light_theme_id(name)
        extra = {
            "density_scale": cfg.get("layout.density"),
            "pyside6": True,
        }

        material_theme = self.common.get_material_theme_path(name)
        if material_theme is None:
            # Defensive fallback for damaged installations. Normally bundled
            # data/css/dark/app.xml is always available.
            material_theme = "dark_teal.xml"

        window.apply_stylesheet(
            window,
            material_theme,
            invert_secondary=is_light,
            extra=extra,
        )

        content_parts = [
            self._read_file(path)
            for path in self.common.get_theme_asset_paths(name, "app.css")
        ]

        if core.platforms.is_windows() and not cfg.is_compiled():
            content_parts.append(self.common.get_windows_fix())

        if core.platforms.is_windows():
            fix_css = "fix_windows.light.css" if is_light else "fix_windows.dark.css"
            path = os.path.join(self.common.get_builtin_css_dir(), fix_css)
            if os.path.isfile(path):
                content_parts.append(self._read_file(path))

        content = "".join(part for part in content_parts if part)
        if content:
            stylesheet = window.styleSheet()
            window.setStyleSheet(stylesheet + self.common.format_css(content))

    @staticmethod
    def _file_signature(path: str):
        """Return a cheap signature for a theme/CSS file."""
        try:
            stat = os.stat(path)
            return path, stat.st_mtime_ns, stat.st_size
        except (OSError, TypeError):
            return None

    def _get_material_signature(self, name: str):
        """Build a change signature for the native Qt theme."""
        cfg = self.window.core.config
        core = self.window.core
        is_light = self.common.is_light_theme_id(name)
        material_path = self.common.get_material_theme_path(name)
        parts = [
            str(name),
            cfg.get("layout.density"),
            bool(is_light),
            self._file_signature(material_path) if material_path else None,
        ]

        for path in self.common.get_theme_asset_paths(name, "app.css"):
            parts.append(self._file_signature(path))

        if core.platforms.is_windows():
            parts.append(
                self._file_signature(
                    os.path.join(
                        self.common.get_builtin_css_dir(),
                        "fix_windows.light.css" if is_light else "fix_windows.dark.css",
                    )
                )
            )
            if not cfg.is_compiled():
                svg_supported = bool(core.platforms.is_svg_supported())
                parts.append(("svg_supported", svg_supported))
                if not svg_supported:
                    parts.append(
                        self._file_signature(
                            os.path.join(
                                self.common.get_builtin_css_dir(),
                                "fix_windows.css",
                            )
                        )
                    )

        return tuple(parts)

    def _get_markdown_signature(self):
        """Build a signature for renderer CSS used by the active profile."""
        cfg = self.window.core.config
        theme = self.common.normalize_theme(cfg.get("theme"))
        web_style = self.common.normalize_style(
            cfg.get("theme.style", self.common.STYLE_STANDARD)
        )

        paths = list(self.common.get_theme_asset_paths(theme, "chat.css"))
        if web_style == self.common.STYLE_WIDE:
            paths.extend(self.common.get_global_asset_paths("chat.wide.css"))

        files = [self._file_signature(path) for path in paths]
        return theme, web_style, tuple(files)

    def _remember_state(self, material_signature=None, markdown_signature=None):
        """Remember active theme state for cheap profile synchronization."""
        cfg = self.window.core.config
        self.current_theme = cfg.get("theme")
        self.current_tooltips = bool(cfg.get("layout.tooltips"))
        if material_signature is not None:
            self._current_material_signature = material_signature
        if markdown_signature is not None:
            self._current_markdown_signature = markdown_signature

    def _sync_chat_input_width(self):
        """Refresh Qt composer geometry after Standard/Wide changes."""
        node = self.window.ui.nodes.get("input.container")
        if node is not None and hasattr(node, "sync_width"):
            node.sync_width()

    def style(self, element: str) -> str:
        """Return CSS style for an element (alias)."""
        return self.common.get_style(element)

    def reload_all(self):
        """Synchronize theme state after a profile/workdir reload."""
        cfg = self.window.core.config

        stored_style = cfg.get("theme.style")
        normalized_style = self.common.normalize_style(stored_style)
        if normalized_style != stored_style:
            cfg.set("theme.style", normalized_style)
            cfg.save()

        stored_name = cfg.get("theme")
        name = self.common.normalize_theme(stored_name)
        if name != stored_name:
            cfg.set("theme", name)
            cfg.save()

        # Profile switching can change %workdir%/css and therefore the available
        # theme menu entries even when the selected theme itself did not change.
        self.menu.setup_list()

        material_signature = self._get_material_signature(name)
        markdown_signature = self._get_markdown_signature()

        material_changed = material_signature != self._current_material_signature
        markdown_changed = (
            material_changed
            or markdown_signature != self._current_markdown_signature
        )
        tooltips = bool(cfg.get("layout.tooltips"))
        tooltips_changed = tooltips != self.current_tooltips

        if material_changed:
            self.current_theme = name
            self.apply(name)
            self.nodes.apply_all(dispatch_theme=False)

        if markdown_changed:
            self.markdown.update(force=False)
        else:
            self.window.dispatch(RenderEvent(RenderEvent.ON_THEME_CHANGE))

        if tooltips_changed:
            self.common.toggle_tooltips()

        self.menu.update_list()
        self.menu.update_density()
        self.menu.update_syntax()
        self._sync_chat_input_width()
        self._remember_state(
            material_signature=material_signature,
            markdown_signature=markdown_signature,
        )

    def is_dark_theme(self) -> bool:
        """Return True when the current theme uses dark-mode behavior."""
        return not self.common.is_light_theme()
