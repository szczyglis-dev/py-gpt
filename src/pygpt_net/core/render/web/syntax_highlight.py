#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 14:00:00                  #
# ================================================== #

import os
import re


class SyntaxHighlight:
    def __init__(self, window=None):
        self.window = window

    def exists(self, style: str) -> bool:
        """
        Check if style exists
        :param style: Style name
        :return: True if exists
        """
        return os.path.exists(os.path.join(self.window.core.config.get_app_path(), "data", "js", "highlight", "styles",
                                           f"{style}.min.css"))

    def get_style(self) -> str:
        """
        Get current style
        :return: Style name
        """
        current = self.window.core.config.get("render.code_syntax")
        if current == "-":
            current = "material-darker" if self.window.controller.theme.is_dark_theme() else "github"
        if not self.exists(current):
            current = "default"
        return current

    def get_style_defs(self) -> str:
        """
        Get style definitions
        :return: Style definitions
        """
        style = self.get_style()
        path = os.path.join(self.window.core.config.get_app_path(), "data", "js", "highlight", "styles",
                            f"{style}.min.css")
        with open(path, "r") as f:
            css = f.read()
        # Headers share the code theme's background, including custom themes.
        backgrounds = []
        for rule in re.finditer(r"(?<![\w-])\.hljs\s*\{([^}]+)\}", css):
            backgrounds.extend(
                declaration.strip() for declaration in rule.group(1).split(";")
                if declaration.strip().split(":", 1)[0].strip().startswith("background")
            )
        if backgrounds:
            selectors = [".tool-output-pair .tool-output-result-data .code-header-wrapper",
                         ".code-wrapper .code-header-wrapper"]
            css += "\n" + ",".join(selectors) + " {" + ";".join(backgrounds) + ";}"
        if not self.window.controller.theme.is_dark_theme():
            css += "\n.code-wrapper {border-color: #e8e8e8;}"
            css += "\n.code-wrapper .code-header-wrapper {border-bottom: 0 !important; box-shadow: none !important;}"
            css += "\n.code-wrapper .code-header-lang {color: #999;}"
        return css

    def get_styles(self) -> list:
        """
        Get available styles
        :return: Styles list
        """
        dir = os.path.join(self.window.core.config.get_app_path(), "data", "js", "highlight", "styles")
        styles = [f.replace(".min.css", "").replace(".css", "") for f in os.listdir(dir) if f.endswith(".css")]
        styles = list(dict.fromkeys(styles))
        styles.sort()
        return ["-"] + styles
