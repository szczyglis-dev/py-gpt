#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 22:45:00                  #
# ================================================== #


THEME_TYPE_DARK = "dark"
THEME_TYPE_LIGHT = "light"

# Built-in themes in menu/display order. Keep compatibility classification
# here so adding a new color theme does not require touching theme controllers.
BUILTIN_THEMES = (
    'light',
    'mint',
    'gray',
    'dark',
    'matrix',
    'flare',
    'retro',
    'ocean',
    'sun',
)

# Themes that should use Light-specific behavior (Qt inversion, Windows fixes,
# widget behavior, etc.).
LIGHT_COMPATIBLE_THEMES = (
    'light',
    'mint',
)

# Static compatibility metadata for bundled themes. Custom/profile themes are
# added to an equivalent runtime registry by the theme controller.
BUILTIN_THEME_TYPES = {
    theme: (THEME_TYPE_LIGHT if theme in LIGHT_COMPATIBLE_THEMES else THEME_TYPE_DARK)
    for theme in BUILTIN_THEMES
}

# Suffixes used to classify new profile themes. The suffix is part of the
# persistent theme ID, but is omitted from the normal menu title.
CUSTOM_THEME_TYPE_SUFFIXES = {
    "-dark": THEME_TYPE_DARK,
    "-light": THEME_TYPE_LIGHT,
}

# Themes that should use Dark-specific behavior.
DARK_COMPATIBLE_THEMES = tuple(
    theme for theme in BUILTIN_THEMES
    if theme not in LIGHT_COMPATIBLE_THEMES
)
