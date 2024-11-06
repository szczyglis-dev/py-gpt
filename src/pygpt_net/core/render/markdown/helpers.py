#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
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
        pattern = r"~###~(.*?)~###~"
        replacement = r'<p class="cmd">\1</p>'
        return re.sub(pattern, replacement, text)

    def pre_format_text(self, text: str) -> str:
        """
        Pre-format text

        :param text: text to format
        :return: formatted text
        """
        text = text.strip()
        text = text.replace("#~###~", "~###~")  # fix for #~###~ in text (previous versions)
        text = text.replace("# ~###~", "~###~")  # fix for # ~###~ in text (previous versions)

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
        return text.strip()

    def format_user_text(self, text: str) -> str:
        """
        Post-format user text

        :param text: text to format
        :return: formatted text
        """
        text = html.escape(text).replace("\n", "<br>")

        # append cmd tags if response from command detected
        if text.strip().startswith("&gt; [") and text.strip().endswith("]"):
            text = '<div class="cmd">&gt; {}</div><br/>'.format(text)
        return text

    def format_chunk(self, text: str) -> str:
        """
        Format chunk

        :param text: text to format
        :return: formatted text
        """
        return text
