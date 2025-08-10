#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.22 22:00:00                  #
# ================================================== #

import re
import html

class Helpers:

    _RE_HTML_ANGLE_OR_MATH = re.compile(r'(\\\[.*?\\\])|(<)|(>)', flags=re.DOTALL)
    _RE_WORKDIR_TOKEN = re.compile(r'\(%workdir%([^)]+)\)')

    _PLACEHOLDER_THINK_OPEN = "{{{{think}}}}"
    _PLACEHOLDER_THINK_CLOSE = "{{{{/think}}}}"

    _RE_TOOL_TAG = re.compile(r"&lt;tool&gt;(.*?)&lt;/tool&gt;", re.DOTALL)
    _RE_MATH_PARENS = re.compile(r"\\\((.*?)\\\)", re.DOTALL)

    def __init__(self, window=None):
        """
        Helpers

        :param window: Window instance
        """
        self.window = window

    def _html_escape_keep_math(self, m: re.Match) -> str:
        """
        Replaces < and > with &lt; / &gt;, leaving \\[ ... \\]

        :param m: regex match object
        :return: escaped string
        """
        g1 = m.group(1)
        if g1 is not None:
            return g1  # fragment of formula \[ ... \]
        return "&lt;" if m.group(2) is not None else "&gt;"

    def _unescape_lt_gt(self, s: str) -> str:
        """
        Unescape &lt; and &gt; in a string

        :param s: string to unescape
        :return: unescaped string
        """
        if "&lt;" not in s and "&gt;" not in s:
            return s
        if "&lt;" in s:
            s = s.replace("&lt;", "<")
        if "&gt;" in s:
            s = s.replace("&gt;", ">")
        return s

    def _repl_tool_cmd(self, m: re.Match) -> str:
        """
        Replace tool command tags with HTML paragraph

        :param m: regex match object
        :return: formatted HTML string
        """
        code = self._unescape_lt_gt(m.group(1))
        return f'<p class="cmd">{html.escape(code)}</p>'

    def _repl_math_fix(self, m: re.Match) -> str:
        """
        Fix math formula by replacing &lt; and &gt; with < and > inside \( ... \)

        :param m: regex match object
        :return: formatted math string
        """
        inner = m.group(1)
        if "&lt;" not in inner and "&gt;" not in inner:
            return m.group(0)
        inner = inner.replace("&lt;", "<").replace("&gt;", ">")
        return f"\\({inner}\\)"

    def replace_code_tags(self, text: str) -> str:
        """
        Replace cmd code tags

        :param text:
        :return: replaced text
        """
        s = text

        # --- tool tags ---
        if "&lt;tool&gt;" in s and "&lt;/tool&gt;" in s:
            s = self._RE_TOOL_TAG.sub(self._repl_tool_cmd, s)

        # --- fix math formula \( ... \) ---
        if "\\(" in s and "\\)" in s and ("&lt;" in s or "&gt;" in s):
            s = self._RE_MATH_PARENS.sub(self._repl_math_fix, s)

        return s

    def pre_format_text(self, text: str) -> str:
        """
        Pre-format text

        :param text: text to format
        :return: formatted text
        """
        s = text.strip()
        if "<" in s or ">" in s:
            had_think = ("<think>" in s) or ("</think>" in s)
            if had_think:
                s = s.replace("<think>", self._PLACEHOLDER_THINK_OPEN).replace("</think>", self._PLACEHOLDER_THINK_CLOSE)

            s = self._RE_HTML_ANGLE_OR_MATH.sub(self._html_escape_keep_math, s)

            if had_think:
                s = s.replace(self._PLACEHOLDER_THINK_OPEN, "<think>").replace(self._PLACEHOLDER_THINK_CLOSE, "</think>")
                if "<think>\n" in s:
                    s = s.replace("<think>\n", "<think>")

        # replace cmd tags
        s = self.replace_code_tags(s)
        if "%workdir%" in s:
            prefix = self.window.core.filesystem.get_workdir_prefix()
            s = self._RE_WORKDIR_TOKEN.sub(lambda m, p=prefix: f'({p}{m.group(1)})', s)

        return s

    def post_format_text(self, text: str) -> str:
        """
        Post-format text

        :param text: text to format
        :return: formatted text
        """
        s = text
        if self.window.core.config.get("llama.idx.chat.agent.render.all", False):
            if "__agent_begin__" in s or "__agent_end__" in s:
                s = s.replace("__agent_begin__", '<div class="msg-agent">').replace("__agent_end__", "</div>")
        return s.strip()

    def format_user_text(self, text: str) -> str:
        """
        Post-format user text

        :param text: text to format
        :return: formatted text
        """
        s = html.escape(text).replace("\n", "<br>")

        trimmed = s.strip()
        if trimmed.endswith("]") and (trimmed.startswith("[") or trimmed.startswith("&gt; [")):
            s = f'<div class="cmd">&gt; {s}</div>'
        return s

    def format_cmd_text(self, text: str) -> str:
        """
        Post-format cmd text

        :param text: text to format
        :return: formatted text
        """
        return html.escape(text)

    def format_chunk(self, text: str) -> str:
        """
        Format chunk

        :param text: text to format
        :return: formatted text
        """
        return text.replace("\n", "<br/>")
