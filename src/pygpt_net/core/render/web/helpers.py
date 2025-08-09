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

    def __init__(self, window=None):
        """
        Helpers

        :param window: Window instance
        """
        self.window = window

    def replace_code_tags(self, text: str) -> str:
        """
        Replace cmd code tags

        :param text:
        :return: replaced text
        """
        # tool tags
        pattern = r"&lt;tool&gt;(.*?)&lt;/tool&gt;"
        def repl(match):
            code = match.group(1)
            # restore tags first
            code = code.replace("&lt;", "<")
            code = code.replace("&gt;", ">")
            escaped_code = html.escape(code)
            return f'<p class="cmd">{escaped_code}</p>'
        text = re.sub(pattern, repl, text, flags=re.DOTALL)

        # fix math formula
        pattern = r"\\\((.*?)\\\)"
        def repl_math(match):
            code = match.group(1)
            code = code.replace("&lt;", "<")
            code = code.replace("&gt;", ">")
            return f"\\({code}\\)"
        text = re.sub(pattern, repl_math, text, flags=re.DOTALL)
        return text

    def pre_format_text(self, text: str) -> str:
        """
        Pre-format text

        :param text: text to format
        :return: formatted text
        """
        text = text.strip()
        #text = text.replace("#~###~", "~###~")  # fix for #~###~ in text (previous versions)
        #text = text.replace("# ~###~", "~###~")  # fix for # ~###~ in text (previous versions)

        # replace HTML tags
        text = text.replace("<think>", "{{{{think}}}}")
        text = text.replace("</think>", "{{{{/think}}}}")
        # text = text.replace("<", "&lt;")
        # text = text.replace(">", "&gt;")
        text = re.sub(
            r'(\\\[.*?\\\])|(<)|(>)',
            lambda m: m.group(1) if m.group(1)
            else "&lt;" if m.group(2)
            else "&gt;",
            text, flags=re.DOTALL
        )  # leave math formula tags
        text = text.replace("{{{{think}}}}", "<think>")
        text = text.replace("{{{{/think}}}}", "</think>")
        text = text.replace("<think>\n", "<think>")

        # replace cmd tags
        text = self.replace_code_tags(text)

        # replace %workdir% with current workdir
        local_prefix = self.window.core.filesystem.get_workdir_prefix()
        safe_local_prefix = local_prefix.replace('\\', '\\\\').replace('\\.', '\\\\.')  # windows fix
        replacement = f'({safe_local_prefix}\\1)'
        try:
            text = re.sub(r'\(%workdir%([^)]+)\)', replacement, text)
        except Exception as e:
            pass
        return text

    def post_format_text(self, text: str) -> str:
        """
        Post-format text

        :param text: text to format
        :return: formatted text
        """
        if self.window.core.config.get("llama.idx.chat.agent.render.all", False):
            text = text.replace("__agent_begin__", "<div class=\"msg-agent\">").replace("__agent_end__", "</div>")
        return text.strip()

    def format_user_text(self, text: str) -> str:
        """
        Post-format user text

        :param text: text to format
        :return: formatted text
        """
        text = html.escape(text).replace("\n", "<br>")
        # append cmd tags if response from command detected
        if (text.strip().startswith("[") or text.strip().startswith("&gt; [")) and text.strip().endswith("]"):
            text = '<div class="cmd">&gt; {}</div>'.format(text)
        return text

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
