#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.16 12:00:00                  #
# ================================================== #

"""Autonomous agent plugin package.

Keep package initialization lightweight. Some bootstrap code imports the
prompt definitions before the application/plugin stack is fully initialized.
Eagerly importing ``.plugin`` here would pull in bridge/text/utils again and
create a circular import during application startup.
"""

__all__ = ["Plugin"]


def __getattr__(name):
    """Lazily expose the plugin class without importing it for submodules."""
    if name == "Plugin":
        from .plugin import Plugin
        return Plugin
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
