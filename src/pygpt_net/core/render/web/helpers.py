#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.07 05:00:00                  #
# ================================================== #

import json
import re
import html

class Helpers:

    _RE_HTML_ANGLE_OR_MATH = re.compile(r'(\\\[.*?\\\])|(<)|(>)', flags=re.DOTALL)
    _RE_WORKDIR_TOKEN = re.compile(r'\(%workdir%([^)]+)\)')
    _RE_APPDIR_TOKEN = re.compile(r'\(%appdir%([^)]+)\)')

    _PLACEHOLDER_THINK_OPEN = "{{{{think}}}}"
    _PLACEHOLDER_THINK_CLOSE = "{{{{/think}}}}"

    #_RE_TOOL_TAG = re.compile(r"&lt;tool&gt;(.*?)&lt;/tool&gt;", re.DOTALL)
    _RE_TOOL_TAG = re.compile(r"<tool>(.*?)</tool>", re.DOTALL)
    _RE_THINK_TAG = re.compile(r"<think>(.*?)</think>", re.DOTALL)
    _RE_EXECUTE_TAG = re.compile(r"<execute>(.*?)</execute>", re.DOTALL)
    #_RE_MATH_PARENS = re.compile(r"\\\((.*?)\\\)", re.DOTALL)

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
        return f'[!cmd]{html.escape(m.group(1))}[/!cmd]'

    def extract_tool_calls(self, text: str) -> list:
        """
        Extract tool calls from <tool>...</tool> tags.

        :param text: Raw assistant output
        :return: List of dicts with tool name and raw request JSON
        """
        if not text or "<tool>" not in text or "</tool>" not in text:
            return []

        calls = []
        for match in self._RE_TOOL_TAG.finditer(text):
            request = match.group(1).strip()
            name = ""
            try:
                data = json.loads(request)
                if isinstance(data, dict):
                    if data.get("cmd") is not None:
                        name = str(data.get("cmd")).strip()
                    request = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            except Exception:
                pass
            calls.append({
                "name": name or "tool",
                "request": request,
            })
        return calls

    def strip_tool_calls(self, text: str) -> str:
        """
        Remove <tool>...</tool> tags from assistant output used for visible markdown.

        Tool requests are rendered separately in the collapsible tool block.

        :param text: Raw assistant output
        :return: Output without tool call tags
        """
        if not text or "<tool>" not in text or "</tool>" not in text:
            return text
        return self._RE_TOOL_TAG.sub("", text).strip()

    def _repl_think(self, m: re.Match) -> str:
        """
        Replace think tags with HTML paragraph

        :param m: regex match object
        :return: formatted HTML string
        """
        g = m.group(1).replace("\n", "<br>")
        return f'[!think]{html.escape(g)}[/!think]'

    def _repl_execute(self, m: re.Match) -> str:
        """
        Replace execute tags with HTML paragraph

        :param m: regex match object
        :return: formatted HTML string
        """
        return f'[!exec]{html.escape(m.group(1))}[/!exec]'

    def _repl_math_fix(self, m: re.Match) -> str:
        """
        Fix math formula by replacing &lt; and &gt; with < and > inside \\( ... \\)

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
        if "<tool>" in s and "</tool>" in s:
            s = self._RE_TOOL_TAG.sub(self._repl_tool_cmd, s)

        # --- fix math formula \( ... \) ---
        #if "\\(" in s and "\\)" in s and ("&lt;" in s or "&gt;" in s):
            #s = self._RE_MATH_PARENS.sub(self._repl_math_fix, s)

        return s

    def replace_think_tags(self, text: str) -> str:
        """
        Replace think tags

        :param text:
        :return: replaced text
        """
        s = text

        # --- think tags ---
        if "<think>" in s and "</think>" in s:
            s = self._RE_THINK_TAG.sub(self._repl_think, s)

        return s

    def replace_execute_tags(self, text: str) -> str:
        """
        Replace execute tags

        :param text:
        :return: replaced text
        """
        s = text

        # --- execute tags ---
        if "<execute>" in s and "</execute>" in s:
            s = self._RE_EXECUTE_TAG.sub(self._repl_execute, s)

        return s

    def pre_format_text(self, text: str) -> str:
        """
        Pre-format text

        :param text: text to format
        :return: formatted text
        """
        """
        if "<" in s or ">" in s:
            had_think = ("<think>" in s) or ("</think>" in s)
            if had_think:
                s = s.replace("<think>", self._PLACEHOLDER_THINK_OPEN).replace("</think>", self._PLACEHOLDER_THINK_CLOSE)

            s = self._RE_HTML_ANGLE_OR_MATH.sub(self._html_escape_keep_math, s)

            if had_think:
                s = s.replace(self._PLACEHOLDER_THINK_OPEN, "<think>").replace(self._PLACEHOLDER_THINK_CLOSE, "</think>")
                if "<think>\n" in s:
                    s = s.replace("<think>\n", "<think>")
        """

        # replace tags with markdown placeholders (will be converted to HTML in JS runtime)
        s = self.replace_code_tags(text.strip())
        s = self.replace_think_tags(s)
        s = self.replace_execute_tags(s)

        # replace local path tokens with valid, encoded file URLs
        if "%workdir%" in s:
            fs = self.window.core.filesystem
            s = self._RE_WORKDIR_TOKEN.sub(
                lambda m: f'({fs.get_local_url("%workdir%" + m.group(1))})',
                s,
            )

        if "%appdir%" in s:
            fs = self.window.core.filesystem
            app_dir = self.window.core.config.get_app_path()
            s = self._RE_APPDIR_TOKEN.sub(
                lambda m: f'({fs.get_local_url(app_dir + m.group(1))})',
                s,
            )

        return s

    def post_format_text(self, text: str) -> str:
        """
        Post-format text

        :param text: text to format
        :return: formatted text
        """
        s = text
        if self.window.core.config.get("agent.output.render.all", False):
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

    def _normalize_json_display_value(self, value, unpack_string: bool = False):
        """
        Recursively normalize JSON values used by tool request/response display.

        Tool responses may be serialized more than once, e.g. an outer result
        list can contain ``request`` and ``result`` fields that are themselves
        JSON strings. A single json.loads/json.dumps pass leaves Unicode in
        those nested strings escaped as ``\\uXXXX``. Only known wrapper fields
        are unpacked, so a tool's actual text content is never reinterpreted
        merely because it happens to contain valid JSON.

        :param value: decoded JSON value
        :param unpack_string: allow this string value to be parsed as JSON
        :return: normalized display value
        """
        if isinstance(value, dict):
            normalized = {}
            for key, item in value.items():
                normalized[key] = self._normalize_json_display_value(
                    item,
                    unpack_string=(key in ("request", "result")),
                )
            return normalized

        if isinstance(value, list):
            return [self._normalize_json_display_value(item) for item in value]

        if unpack_string and isinstance(value, str):
            stripped = value.strip()
            if len(stripped) >= 2 and (
                    (stripped.startswith("{") and stripped.endswith("}"))
                    or (stripped.startswith("[") and stripped.endswith("]"))
            ):
                try:
                    nested = json.loads(stripped)
                except (TypeError, ValueError, json.JSONDecodeError):
                    return value
                if isinstance(nested, (dict, list)):
                    return self._normalize_json_display_value(nested)

        return value

    def format_cmd_data(self, text: str, indent: bool = False) -> str:
        """
        Format command/tool JSON for plain-text UI display.

        Nested JSON strings are unpacked recursively so escaped Unicode is
        displayed as real characters.  This method does not HTML-escape the
        result; callers that inject HTML must escape it separately.

        :param text: text to format
        :param indent: whether to pretty-print JSON
        :return: plain formatted text
        """
        if not text:
            return ""

        try:
            data = json.loads(text)
            data = self._normalize_json_display_value(data)
            if indent:
                return json.dumps(data, indent=2, ensure_ascii=False)
            return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            return str(text)

    def format_cmd_text(self, text: str, indent: bool = False) -> str:
        """
        Post-format cmd text for HTML output.

        :param text: text to format
        :param indent: whether to indent text
        :return: formatted and HTML-escaped text
        """
        return html.escape(self.format_cmd_data(text, indent=indent))


    def format_chunk(self, text: str) -> str:
        """
        Format chunk

        :param text: text to format
        :return: formatted text
        """
        return text
        # return text.replace("\n", "<br/>")
