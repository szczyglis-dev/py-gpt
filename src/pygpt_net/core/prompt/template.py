#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.25 04:00:00                  #
# ================================================== #

import os
import csv

from PySide6.QtGui import QAction
from pygpt_net.utils import trans


class Template:
    def __init__(self, window=None):
        """
        Prompt templates

        :param window: Window instance
        """
        self.window = window
        self.prompts = {}
        self.loaded = False

    def init(self):
        """Init prompt templates"""
        self.load()

    def load(self):
        """Load prompt templates"""
        if self.loaded:
            return
        try:
            self.load_from_csv()
        except Exception as e:
            self.window.core.debug.log(e)
        self.loaded = True

    def load_from_csv(self):
        """Load prompt templates from CSV"""
        # CSV file is given from: https://github.com/f/awesome-chatgpt-prompts
        path = os.path.join(self.window.core.config.get_app_path(), "data", "prompts.csv")
        self.prompts = {}
        i = 0
        with open(path, newline='', encoding='utf-8') as f:
            data = csv.reader(f, delimiter=',')
            for row in data:
                if i == 0:
                    i += 1
                    continue
                self.prompts[i] = {
                    "name": row[0],
                    "prompt": row[1]
                }
                i += 1
        # sort by name
        self.prompts = dict(sorted(self.prompts.items(), key=lambda item: item[1]['name']))

    def to_menu_options(self, menu, parent: str = "global"):
        """Convert prompts to menu options"""
        self.init()
        menu.addSeparator()
        submenu = menu.addMenu(trans("preset.prompt.paste_template"))
        letter_submenus = {}

        # add submenus for each letter
        for key, value in self.prompts.items():
            letter = value['name'][0].upper()
            if letter not in letter_submenus:
                letter_submenus[letter] = submenu.addMenu(letter)

        # add prompts to letter submenus
        for key, value in self.prompts.items():
            letter = value['name'][0].upper()
            action = QAction(value['name'], menu)
            action.triggered.connect(lambda checked=False, key=key: self.window.controller.presets.paste_prompt(key, parent))
            action.setToolTip(value['prompt'])
            letter_submenus[letter].addAction(action)

    def get_by_id(self, id: int) -> dict or None:
        """
        Get prompt by id

        :param id: Prompt ID
        """
        self.init()
        return self.prompts.get(id, None)

    def get_all(self) -> dict:
        """
        Get all prompt templates

        :return: Prompt templates
        """
        self.init()
        return self.prompts
