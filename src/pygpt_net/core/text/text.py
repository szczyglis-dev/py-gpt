#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.08 05:00:00                  #
# ================================================== #
import os


class Text:
    def __init__(self, window=None):
        """
        Text helpers

        :param window: Window instance
        """
        self.window = window

    def get_language_choices(self) -> list:
        """
        Get available language choices

        :return: list of dictionaries with language codes and names
        """
        choices = []
        choices.append({"-": "--- AUTO DETECT ---"})
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