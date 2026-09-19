#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 12:00:00                  #
# ================================================== #

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

# Themes that should use Dark-specific behavior.
DARK_COMPATIBLE_THEMES = tuple(
    theme for theme in BUILTIN_THEMES
    if theme not in LIGHT_COMPATIBLE_THEMES
)

# Bundled qt-material XML assets. Order only affects discovery/debug output.
THEME_MATERIAL_ASSETS = (
    'dark',
    'matrix',
    'flare',
    'retro',
    'ocean',
    'sun',
    'gray',
    'mint',
    'light',
)
