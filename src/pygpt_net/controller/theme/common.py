#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 22:48:00                  #
# ================================================== #

import os
import re
from typing import List, Optional

from pygpt_net.core.types.theme import (
    BUILTIN_THEMES,
    BUILTIN_THEME_TYPES,
    CUSTOM_THEME_TYPE_SUFFIXES,
    THEME_TYPE_DARK,
    THEME_TYPE_LIGHT,
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
    THEME_FILES = (
        "app.css",
        "app.xml",
        "chat.css",
    )

    def __init__(self, window=None):
        """
        Theme common controller

        :param window: Window instance
        """
        self.window = window
        # Runtime equivalent of the static built-in compatibility metadata.
        # It is rebuilt from the active profile's discovered theme directories.
        self.theme_types = {}

    def get_builtin_css_dir(self) -> str:
        """Return the bundled CSS/theme root."""
        return os.path.join(
            self.window.core.config.get_app_path(),
            "data",
            "css",
        )

    def get_user_css_dir(self) -> str:
        """Return the active profile CSS/theme root."""
        return os.path.join(
            self.window.core.config.get_user_path(),
            "css",
        )

    def _discover_theme_dirs(self, root: str) -> List[str]:
        """Return theme directory IDs found below a CSS root."""
        if not os.path.isdir(root):
            return []

        themes = []
        try:
            entries = list(os.scandir(root))
        except OSError:
            return []

        for entry in entries:
            if entry.name.startswith("."):
                continue
            try:
                if not entry.is_dir():
                    continue
            except OSError:
                continue

            if any(
                os.path.isfile(os.path.join(entry.path, filename))
                for filename in self.THEME_FILES
            ):
                themes.append(entry.name)

        return sorted(themes, key=str.casefold)

    @staticmethod
    def _find_theme_dir(root: str, theme: str) -> Optional[str]:
        """Find an exact or case-insensitive theme directory."""
        if not root or not theme or not os.path.isdir(root):
            return None

        exact = os.path.join(root, theme)
        if os.path.isdir(exact):
            return exact

        wanted = str(theme).casefold()
        try:
            for entry in os.scandir(root):
                try:
                    is_dir = entry.is_dir()
                except OSError:
                    is_dir = False
                if is_dir and entry.name.casefold() == wanted:
                    return entry.path
        except OSError:
            pass
        return None

    def get_builtin_themes_list(self) -> List[str]:
        """Return bundled theme IDs, preserving the preferred menu order."""
        discovered = self._discover_theme_dirs(self.get_builtin_css_dir())
        by_key = {name.casefold(): name for name in discovered}

        ordered = []
        for theme in BUILTIN_THEMES:
            found = by_key.pop(theme.casefold(), None)
            if found is not None:
                ordered.append(found)
        ordered.extend(sorted(by_key.values(), key=str.casefold))
        return ordered

    def get_custom_themes_list(self) -> List[str]:
        """Return theme directory IDs supplied by the active profile."""
        return self._discover_theme_dirs(self.get_user_css_dir())

    def get_themes_list(self) -> List[str]:
        """
        Return all available theme IDs and rebuild runtime compatibility types.

        Bundled themes keep their normal order. User themes from
        ``%workdir%/css/<theme-id>/`` are appended alphabetically. A user theme
        with the same ID (case-insensitive) as a bundled theme overrides its
        assets instead of creating a duplicate menu entry.
        """
        themes = self.get_builtin_themes_list()
        known = {theme.casefold() for theme in themes}

        for theme in self.get_custom_themes_list():
            key = theme.casefold()
            if key in known:
                continue
            themes.append(theme)
            known.add(key)

        self._build_runtime_theme_types(themes)
        return themes

    @staticmethod
    def _get_custom_theme_suffix_type(theme: str) -> Optional[str]:
        """Return the explicit ``-dark``/``-light`` type for a custom ID."""
        key = str(theme or "").casefold()
        for suffix, theme_type in CUSTOM_THEME_TYPE_SUFFIXES.items():
            if key.endswith(suffix) and len(key) > len(suffix):
                return theme_type
        return None

    @staticmethod
    def _strip_custom_theme_type_suffix(theme: str) -> str:
        """Strip a custom compatibility suffix from a display-only theme name."""
        value = str(theme or "")
        key = value.casefold()
        for suffix in CUSTOM_THEME_TYPE_SUFFIXES:
            if key.endswith(suffix) and len(value) > len(suffix):
                return value[:-len(suffix)]
        return value

    def _build_runtime_theme_types(self, themes: List[str]):
        """
        Build compatibility metadata for the currently available theme IDs.

        Bundled IDs use the static mapping from ``core.types.theme``. New
        profile IDs are classified by ``-light`` / ``-dark`` suffix. Unsuffixed
        custom IDs default to Dark for backward compatibility.
        """
        builtin = {
            theme_id.casefold(): theme_type
            for theme_id, theme_type in BUILTIN_THEME_TYPES.items()
        }
        runtime = {}
        for theme in themes:
            key = theme.casefold()
            if key in builtin:
                runtime[theme] = builtin[key]
            else:
                runtime[theme] = (
                    self._get_custom_theme_suffix_type(theme)
                    or THEME_TYPE_DARK
                )
        self.theme_types = runtime

    def get_theme_types(self) -> dict:
        """Return runtime light/dark metadata for all available theme IDs."""
        self.get_themes_list()
        return dict(self.theme_types)

    def get_theme_type(self, theme: str) -> str:
        """Return the runtime compatibility type for a theme ID."""
        name = self.normalize_theme(theme)
        wanted = name.casefold()
        for theme_id, theme_type in self.theme_types.items():
            if theme_id.casefold() == wanted:
                return theme_type
        return THEME_TYPE_DARK

    def normalize_theme(self, theme: str) -> str:
        """
        Normalize a stored theme ID to an available theme.

        Exact custom theme IDs are resolved before legacy built-in aliases, so
        names such as ``dark_custom`` remain valid custom themes.
        """
        raw = str(theme or "").strip()
        available = self.get_themes_list()
        if not available:
            return "dark"

        if raw:
            wanted = raw.casefold()
            for candidate in available:
                if candidate.casefold() == wanted:
                    return candidate

            # Backward compatibility with older theme IDs such as dark_blue or
            # grey variants, but only after checking real theme directories.
            if wanted.startswith(("gray", "grey")):
                for candidate in available:
                    if candidate.casefold() == "gray":
                        return candidate
            for built_in in BUILTIN_THEMES:
                if wanted.startswith(built_in.casefold()):
                    for candidate in available:
                        if candidate.casefold() == built_in.casefold():
                            return candidate

        for candidate in available:
            if candidate.casefold() == "dark":
                return candidate
        return available[0]

    def normalize_style(self, style: str) -> str:
        """Normalize current and legacy chat style identifiers."""
        name = str(style or "").lower()
        name = self.LEGACY_STYLE_MAP.get(name, name)
        if name == self.STYLE_WIDE:
            return self.STYLE_WIDE
        return self.STYLE_STANDARD

    def _get_theme_base_title(self, theme: str) -> str:
        """Return a theme title without custom type disambiguation."""
        key = str(theme or "").casefold()
        if key in {name.casefold() for name in BUILTIN_THEMES}:
            return trans(f"theme.{key}")

        display_id = self._strip_custom_theme_type_suffix(theme)
        title = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", display_id)
        title = re.sub(r"[_\-]+", " ", title).strip()
        return title.title() if title else str(theme or "")

    def get_theme_title(self, theme: str) -> str:
        """
        Return a translated built-in name or a readable custom name.

        ``-dark`` / ``-light`` are compatibility metadata and are normally
        hidden from custom theme titles. If both variants would otherwise have
        the same menu title, the type is appended as ``(Dark)`` / ``(Light)``.
        """
        normalized = self.normalize_theme(theme)
        title = self._get_theme_base_title(normalized)
        suffix_type = self._get_custom_theme_suffix_type(normalized)
        if suffix_type is None:
            return title

        matches = [
            candidate
            for candidate in self.get_themes_list()
            if self._get_theme_base_title(candidate).casefold() == title.casefold()
        ]
        if len(matches) > 1:
            return f"{title} ({suffix_type.title()})"
        return title

    def translate(self, theme: str) -> str:
        """Return the display name for a theme."""
        return self.get_theme_title(theme)

    def get_theme_asset_paths(self, theme: str, filename: str) -> List[str]:
        """
        Return CSS layers for a theme asset in application order.

        Order is: bundled global file, bundled theme file, user global file,
        user theme file. Missing files are simply skipped.
        """
        name = self.normalize_theme(theme)
        builtin_root = self.get_builtin_css_dir()
        user_root = self.get_user_css_dir()
        paths = []

        bundled_global = os.path.join(builtin_root, filename)
        if os.path.isfile(bundled_global):
            paths.append(bundled_global)

        bundled_dir = self._find_theme_dir(builtin_root, name)
        if bundled_dir is None:
            # A new profile theme inherits a complete bundled compatibility
            # base. This makes partial custom themes useful: a directory may
            # contain only the files it actually wants to override.
            fallback_id = "light" if self.is_light_theme_id(name) else "dark"
            bundled_dir = self._find_theme_dir(builtin_root, fallback_id)
        if bundled_dir is not None:
            path = os.path.join(bundled_dir, filename)
            if os.path.isfile(path):
                paths.append(path)

        user_global = os.path.join(user_root, filename)
        if os.path.isfile(user_global):
            paths.append(user_global)

        user_dir = self._find_theme_dir(user_root, name)
        if user_dir is not None:
            path = os.path.join(user_dir, filename)
            if os.path.isfile(path):
                paths.append(path)

        return paths

    def get_global_asset_paths(self, filename: str) -> List[str]:
        """Return bundled then user profile paths for a global CSS asset."""
        paths = []
        for root in (self.get_builtin_css_dir(), self.get_user_css_dir()):
            path = os.path.join(root, filename)
            if os.path.isfile(path):
                paths.append(path)
        return paths

    def get_material_theme_path(self, theme: str) -> Optional[str]:
        """
        Resolve ``app.xml`` for a theme.

        A profile-level XML overrides the bundled XML with the same theme ID.
        A completely custom theme without ``app.xml`` falls back to the bundled
        Light or Dark material palette selected by its runtime compatibility
        type.
        """
        name = self.normalize_theme(theme)
        user_dir = self._find_theme_dir(self.get_user_css_dir(), name)
        if user_dir is not None:
            path = os.path.join(user_dir, "app.xml")
            if os.path.isfile(path):
                return path

        bundled_dir = self._find_theme_dir(self.get_builtin_css_dir(), name)
        if bundled_dir is not None:
            path = os.path.join(bundled_dir, "app.xml")
            if os.path.isfile(path):
                return path

        fallback_id = self.get_theme_type(name)
        fallback_dir = self._find_theme_dir(self.get_builtin_css_dir(), fallback_id)
        if fallback_dir is not None:
            path = os.path.join(fallback_dir, "app.xml")
            if os.path.isfile(path):
                return path
        return None

    def is_light_theme_id(self, theme: str) -> bool:
        """Return whether a theme should use light-mode runtime behavior."""
        return self.get_theme_type(theme) == THEME_TYPE_LIGHT

    def is_light_theme(self) -> bool:
        """Check if the current theme uses light-mode behavior."""
        return self.is_light_theme_id(self.window.core.config.get("theme"))

    def toggle_tooltips(self):
        """Toggle visibility of static tooltips"""
        nodes = [
            "tip.input.attachments",
            "tip.input.attachments.uploaded",
            "tip.output.tab.calendar",
            "tip.output.tab.draw",
            "tip.output.tab.files",
            "tip.output.tab.notepad",
            "tip.toolbox.assistants",
            "tip.toolbox.ctx",
            # "tip.toolbox.indexes",
            "tip.toolbox.mode",
            "tip.toolbox.presets",
            "tip.toolbox.prompt",
        ]
        state = self.window.core.config.get("layout.tooltips")
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

        self.window.ui.menu["theme.tooltips"].setChecked(state)

    def get_style(self, element: str) -> str:
        """
        Return CSS style for element

        :param element: type of element
        :return: CSS style for element
        """
        if element == "font.chat.output":
            return "QTextEdit {{ font-size: {}px; }}".format(
                self.window.core.config.get("font_size")
            )
        if element == "font.chat.input":
            return "QTextEdit {{ font-size: {}px; }}".format(
                self.window.core.config.get("font_size.input")
            )
        if element == "font.ctx.list":
            return "font-size: {}px;".format(
                self.window.core.config.get("font_size.ctx")
            )
        if element == "font.toolbox":
            return "font-size: {}px;".format(
                self.window.core.config.get("font_size.toolbox")
            )
        return ""


    @staticmethod
    def format_css(content: str) -> str:
        """Expand Qt-material environment placeholders without requiring normal CSS braces to be escaped."""
        if not content:
            return ""

        open_token = "\x00PYGPT_OPEN_BRACE\x00"
        close_token = "\x00PYGPT_CLOSE_BRACE\x00"
        value = content.replace("{{", open_token).replace("}}", close_token)

        pattern = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")
        value = pattern.sub(
            lambda match: os.environ.get(match.group(1), match.group(0)),
            value,
        )
        return value.replace(open_token, "{").replace(close_token, "}")

    def get_windows_fix(self) -> str:
        """
        Return Windows checkbox button + radio button fix

        :return: stylesheet with fix
        """
        if self.window.core.platforms.is_svg_supported():
            return ""

        path = os.path.join(self.get_builtin_css_dir(), "fix_windows.css")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as file:
                return file.read()
        return ""

    def get_styles_list(self) -> List[str]:
        """Return the built-in chat view styles."""
        return [self.STYLE_STANDARD, self.STYLE_WIDE]
