#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.26 23:00:00                  #
# ================================================== #

from .field.checkbox import Checkbox
from .field.combo import Combo
from .field.cmd import Cmd
from .field.dictionary import Dictionary
from .field.input import Input
from .field.slider import Slider
from .field.textarea import Textarea
from .placeholder import Placeholder


class Config:
    def __init__(self, window=None):
        """
        Configuration controller

        :param window: Window instance
        """
        self.window = window
        self.checkbox = Checkbox(window)
        self.combo = Combo(window)
        self.cmd = Cmd(window)
        self.dictionary = Dictionary(window)
        self.input = Input(window)
        self.placeholder = Placeholder(window)
        self.slider = Slider(window)
        self.textarea = Textarea(window)

    def load_options(self, parent_id: str, options: dict):
        """
        Load options

        :param parent_id: Parent ID
        :param options: Options dict
        """
        for key in options:
            option = options[key]
            self.apply(parent_id, key, option)

    def apply(self, parent_id: str, key: str, option: dict):
        """
        Apply option to field handler based on type

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option dict
        """
        if option['type'] == 'int' or option['type'] == 'float':
            if 'slider' in option and option['slider']:
                self.slider.apply(parent_id, key, option)
            else:
                self.input.apply(parent_id, key, option)
        elif option['type'] == 'text':
            self.input.apply(parent_id, key, option)
        elif option['type'] == 'textarea':
            self.textarea.apply(parent_id, key, option)
        elif option['type'] == 'bool':
            self.checkbox.apply(parent_id, key, option)
        elif option['type'] == 'dict':
            self.dictionary.apply(parent_id, key, option)
        elif option['type'] == 'combo':
            self.combo.apply(parent_id, key, option)
        elif option['type'] == 'cmd':
            self.cmd.apply(parent_id, key, option)

    def apply_value(self, parent_id: str, key: str, option: dict, value):
        """
        Apply value to option

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option dict
        :param value: Option value
        """
        option['value'] = value
        self.apply(parent_id, key, option)

    def get_value(self, parent_id: str, key: str, option: dict, idx: bool = False) -> any:
        """
        Get value from field handler based on type

        :param parent_id: Parent ID
        :param key: Option key
        :param option: Option dict
        :param idx: return selected idx, not the value
        :return: Option value
        """
        if option['type'] == 'int' or option['type'] == 'float':
            if 'slider' in option and option['slider']:
                return self.slider.get_value(parent_id, key, option)
            else:
                return self.input.get_value(parent_id, key, option)
        elif option['type'] == 'text':
            return self.input.get_value(parent_id, key, option)
        elif option['type'] == 'textarea':
            return self.textarea.get_value(parent_id, key, option)
        elif option['type'] == 'bool':
            return self.checkbox.get_value(parent_id, key, option)
        elif option['type'] == 'dict':
            return self.dictionary.get_value(parent_id, key, option)
        elif option['type'] == 'combo':
            return self.combo.get_value(parent_id, key, option, idx)
        elif option['type'] == 'cmd':
            return self.cmd.get_value(parent_id, key, option)

    def update_combo(self, parent_id: str, key: str, items: dict):
        """
        Update combo items

        :param parent_id: Parent ID
        :param key: Option key
        :param items: Items dict
        """
        self.combo.update_list(parent_id, key, items)
