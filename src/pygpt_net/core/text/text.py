#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.09 15:00:00                  #
# ================================================== #
import os

from pygpt_net.utils import trans


class Text:
    def __init__(self, window=None):
        """
        Text helpers

        :param window: Window instance
        """
        self.window = window
        self.lang_list = None  # cache for language choices

    def get_language_choices(self) -> list:
        """
        Get available language choices

        :return: list of dictionaries with language codes and names
        """
        if self.lang_list is not None:
            return self.lang_list  # return cached choices

        choices = []
        choices.append({"-": trans("translator.search.auto")})
        csv_path = os.path.join(self.window.core.config.get_app_path(), 'data', 'languages.csv')
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8') as file:
                for line in file.readlines()[1:]:
                    parts = line.strip().split(',')
                    if len(parts) >= 4:
                        lang_code = parts[0].strip()
                        lang_name = parts[3].strip()
                        lang_orig_name = parts[4].strip()
                        name = f"{lang_name} ({lang_orig_name})" if lang_orig_name else lang_name
                        name = name.replace("'", "").replace('"', "")
                        choices.append({lang_code: name})

        # sort choices by language name
        choices.sort(key=lambda x: list(x.values())[0].lower())

        self.lang_list = choices  # cache the choices for later use
        return choices

    def get_language_name(self, lang_code: str) -> str:
        """
        Get language name by code

        :param lang_code: language code
        :return: language name or empty string if not found
        """
        choices = self.get_language_choices()
        for choice in choices:
            if lang_code in choice:
                return choice[lang_code]
        return ""

    def find_lang_id_by_search_string(self, search_string: str) -> str:
        """
        Find language code by search string

        :param search_string: search string
        :return: language code or empty string if not found
        """
        choices = self.get_language_choices()
        to_search = search_string.strip().lower()
        for choice in choices:
            lang_code = list(choice.keys())[0]
            lang_name = choice[lang_code].strip().lower()
            if lang_name.startswith(to_search):
                return lang_code
        for choice in choices:
            lang_code = list(choice.keys())[0]
            lang_name = choice[lang_code].strip().lower()
            if to_search in lang_name:
                return lang_code
        return ""