#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #

import os
import re
from xml.etree import ElementTree
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
        # It is rebuilt from bundled, global Add-on and profile theme directories.
        self.theme_types = {}

    def get_builtin_css_dir(self) -> str:
        """Return the bundled CSS/theme root."""
        return os.path.join(
            self.window.core.config.get_app_path(),
            "data",
            "css",
        )

    def get_base_css_dir(self) -> str:
        """Return the application-wide custom CSS/theme root."""
        return os.path.join(
            self.window.core.config.get_base_workdir(),
            "css",
        )

    def get_addon_themes_dir(self) -> str:
        """Return the application-wide Theme Add-ons root."""
        return os.path.join(
            self.window.core.config.get_base_workdir(),
            "addons",
            "themes",
        )

    def get_user_css_dir(self) -> str:
        """Return the active profile CSS/theme root."""
        return os.path.join(
            self.window.core.config.get_user_path(),
            "css",
        )

    @staticmethod
    def _unique_roots(*roots: str) -> List[str]:
        """Return path roots once, preserving precedence/order."""
        result = []
        seen = set()
        for root in roots:
            if not root:
                continue
            key = os.path.normcase(os.path.realpath(root))
            if key in seen:
                continue
            seen.add(key)
            result.append(root)
        return result

    def _get_addon_theme_dir(self, theme: str) -> Optional[str]:
        """Resolve a Theme Add-on payload directory by Add-on/theme ID."""
        package = self._find_theme_dir(self.get_addon_themes_dir(), theme)
        if package is None:
            return None
        nested = os.path.join(package, "theme")
        payload = nested if os.path.isdir(nested) else package
        if any(os.path.isfile(os.path.join(payload, name)) for name in self.THEME_FILES):
            return payload
        return None

    def _discover_addon_themes(self) -> List[str]:
        """Return IDs of valid application-wide Theme Add-ons."""
        root = self.get_addon_themes_dir()
        if not os.path.isdir(root):
            return []
        result = []
        try:
            entries = list(os.scandir(root))
        except OSError:
            return []
        for entry in entries:
            if entry.name.startswith("."):
                continue
            try:
                if not entry.is_dir() or entry.is_symlink():
                    continue
            except OSError:
                continue
            if self._get_addon_theme_dir(entry.name) is not None:
                result.append(entry.name)
        return sorted(result, key=str.casefold)

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
        """Return global/Add-on/profile custom theme IDs."""
        result = []
        known = set()
        sources = [
            self._discover_theme_dirs(self.get_base_css_dir()),
            self._discover_addon_themes(),
            self._discover_theme_dirs(self.get_user_css_dir()),
        ]
        for themes in sources:
            for theme in themes:
                key = theme.casefold()
                if key in known:
                    continue
                known.add(key)
                result.append(theme)
        return result

    def get_themes_list(self) -> List[str]:
        """
        Return all available theme IDs and rebuild runtime compatibility types.

        Bundled themes keep their normal order. Application-base themes, Theme
        Add-ons, and active-profile themes are then discovered without duplicate
        menu entries. A custom theme with the same ID as a bundled theme extends
        or overrides that bundled theme's assets.
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

        Precedence is bundled -> application-base custom CSS -> Theme Add-on ->
        active-profile CSS. Missing files are skipped and equal base/profile
        paths are de-duplicated.
        """
        name = self.normalize_theme(theme)
        builtin_root = self.get_builtin_css_dir()
        base_root = self.get_base_css_dir()
        user_root = self.get_user_css_dir()
        paths = []

        def append_file(path: str):
            if os.path.isfile(path) and path not in paths:
                paths.append(path)

        append_file(os.path.join(builtin_root, filename))

        bundled_dir = self._find_theme_dir(builtin_root, name)
        if bundled_dir is None:
            fallback_id = "light" if self.is_light_theme_id(name) else "dark"
            bundled_dir = self._find_theme_dir(builtin_root, fallback_id)
        if bundled_dir is not None:
            append_file(os.path.join(bundled_dir, filename))

        # Application-wide manually installed/custom CSS.
        append_file(os.path.join(base_root, filename))
        base_dir = self._find_theme_dir(base_root, name)
        if base_dir is not None:
            append_file(os.path.join(base_dir, filename))

        # Static Theme Add-ons are read directly from their package.
        addon_dir = self._get_addon_theme_dir(name)
        if addon_dir is not None:
            append_file(os.path.join(addon_dir, filename))

        # Profile-local CSS remains the last, explicit override layer.
        if os.path.normcase(os.path.realpath(user_root)) != os.path.normcase(os.path.realpath(base_root)):
            append_file(os.path.join(user_root, filename))
            user_dir = self._find_theme_dir(user_root, name)
            if user_dir is not None:
                append_file(os.path.join(user_dir, filename))

        return paths

    def get_global_asset_paths(self, filename: str) -> List[str]:
        """Return bundled, application-base, then profile global CSS assets."""
        paths = []
        for root in self._unique_roots(
                self.get_builtin_css_dir(),
                self.get_base_css_dir(),
                self.get_user_css_dir(),
        ):
            path = os.path.join(root, filename)
            if os.path.isfile(path):
                paths.append(path)
        return paths

    def get_material_theme_path(self, theme: str) -> Optional[str]:
        """Resolve the highest-precedence ``app.xml`` for a theme."""
        name = self.normalize_theme(theme)

        # Profile-local override is explicit and wins over the global Add-on.
        user_root = self.get_user_css_dir()
        base_root = self.get_base_css_dir()
        user_dir = self._find_theme_dir(user_root, name)
        if user_dir is not None:
            path = os.path.join(user_dir, "app.xml")
            if os.path.isfile(path):
                return path

        # Application-wide Theme Add-on overrides the manually shared base CSS.
        addon_dir = self._get_addon_theme_dir(name)
        if addon_dir is not None:
            path = os.path.join(addon_dir, "app.xml")
            if os.path.isfile(path):
                return path

        if os.path.normcase(os.path.realpath(base_root)) != os.path.normcase(os.path.realpath(user_root)):
            base_dir = self._find_theme_dir(base_root, name)
            if base_dir is not None:
                path = os.path.join(base_dir, "app.xml")
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


    def get_css_variables(self, theme: str) -> dict:
        """Resolve a fresh palette for each theme, including legacy profile XMLs.

        APP_* tokens never come from the process environment: a theme switch
        must not retain values exported by a previously loaded material theme.
        """
        root = self.get_builtin_css_dir()
        fallback = "light" if self.is_light_theme_id(theme) else "dark"
        paths = [
            os.path.join(root, "app.xml"),
            os.path.join(root, fallback, "app.xml"),
            os.path.join(root, theme, "app.xml"),
            self.get_material_theme_path(theme),
        ]
        values = {}
        for path in dict.fromkeys(path for path in paths if path):
            if not os.path.isfile(path):
                continue
            for node in ElementTree.parse(path).getroot():
                name = node.get("name", "")
                if name.startswith("app") and node.text:
                    token = re.sub(r"(?<!^)(?=[A-Z])", "_", name).upper()
                    values[token] = node.text.strip()
        return values

    @staticmethod
    def format_css(content: str, variables: Optional[dict] = None) -> str:
        """Expand Qt-material environment placeholders without requiring normal CSS braces to be escaped."""
        if not content:
            return ""

        open_token = "\x00PYGPT_OPEN_BRACE\x00"
        close_token = "\x00PYGPT_CLOSE_BRACE\x00"
        value = content.replace("{{", open_token).replace("}}", close_token)

        pattern = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")
        value = pattern.sub(
            lambda match: (variables or {}).get(
                match.group(1),
                match.group(0) if match.group(1).startswith("APP_")
                else os.environ.get(match.group(1), match.group(0)),
            ),
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
